"""Lossless Postgres repositories with tenant-head serialization."""

from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.db.tables import confirmations, heads, positions as position_table, versions
from app.models.confirm import ConfirmationRecord
from app.models.valuation import PortfolioVersion, Position


def validate_confirmation(record, version, positions):
    record = ConfirmationRecord.model_validate(record.model_dump())
    version = PortfolioVersion.model_validate(version.model_dump(exclude_unset=True))
    positions = tuple(Position.model_validate(p.model_dump(exclude_unset=True)) for p in positions)
    if record.portfolio_version_id != version.id:
        raise ValueError("Invalid version identity")
    if version.status != "confirmed" or datetime.fromisoformat(
        version.confirmed_at
    ) < datetime.fromisoformat(version.imported_at):
        raise ValueError("Invalid confirmed version")
    if not positions or any(p.portfolio_version_id != version.id for p in positions):
        raise ValueError("Positions must belong to the confirmed version")
    if len({p.instrument_id for p in positions}) != len(positions):
        raise ValueError("Duplicate instrument")
    return record, version, positions


class PostgresPortfolioRepository:
    def __init__(self, engine, connection=None):
        self.engine = engine
        self.connection = connection

    @contextmanager
    def read(self):
        if self.connection is not None:
            yield self.connection
        else:
            with self.engine.connect() as connection:
                yield connection

    def document(self, table, predicate, model):
        with self.read() as connection:
            data = connection.execute(
                select(table.c.document).where(predicate)
            ).scalar_one_or_none()
            return model.model_validate(data) if data is not None else None

    def get(self, version_id):
        return self.document(versions, versions.c.id == version_id, PortfolioVersion)

    def positions(self, version_id):
        with self.read() as connection:
            documents = connection.execute(
                select(position_table.c.document)
                .where(position_table.c.portfolio_version_id == version_id)
                .order_by(position_table.c.ordinal)
            ).scalars()
            return tuple(Position.model_validate(data) for data in documents)

    def by_import(self, import_id):
        return self.document(
            confirmations, confirmations.c.import_id == import_id, ConfirmationRecord
        )

    def by_idempotency_key(self, key):
        return self.document(
            confirmations, confirmations.c.idempotency_key == key, ConfirmationRecord
        )

    def latest(self, tenant_id):
        with self.read() as connection:
            document = connection.execute(
                select(versions.c.document)
                .join(heads, heads.c.version_id == versions.c.id)
                .where(heads.c.tenant_id == tenant_id)
            ).scalar_one_or_none()
            return PortfolioVersion.model_validate(document) if document else None

    def lock_head(self, connection, tenant_id):
        connection.execute(insert(heads).values(tenant_id=tenant_id).on_conflict_do_nothing())
        return connection.execute(
            select(heads.c.version_id).where(heads.c.tenant_id == tenant_id).with_for_update()
        ).scalar_one()

    def insert_version(self, connection, version, positions, previous):
        if connection.execute(select(versions.c.id).where(versions.c.id == version.id)).scalar():
            raise ValueError("Existing version identity")
        version = version.model_copy(update={"previous_version_id": previous})
        connection.execute(
            insert(versions).values(
                id=version.id,
                tenant_id=version.tenant_id,
                previous_version_id=previous,
                status=version.status,
                imported_at=datetime.fromisoformat(version.imported_at),
                confirmed_at=datetime.fromisoformat(version.confirmed_at),
                document=version.model_dump(mode="json", exclude_unset=True),
            )
        )
        connection.execute(
            insert(position_table),
            [
                dict(
                    portfolio_version_id=version.id,
                    instrument_id=p.instrument_id,
                    tenant_id=version.tenant_id,
                    ordinal=index,
                    quantity=Decimal(p.quantity),
                    cost_basis=Decimal(p.cost_basis) if p.cost_basis is not None else None,
                    document=p.model_dump(mode="json", exclude_unset=True),
                )
                for index, p in enumerate(positions)
            ],
        )
        connection.execute(
            update(heads)
            .where(heads.c.tenant_id == version.tenant_id)
            .values(version_id=version.id)
        )

    def confirm_in_transaction(self, record, version, positions):
        record, version, positions = validate_confirmation(record, version, positions)
        connection = self.connection
        previous = self.lock_head(connection, version.tenant_id)
        existing = self.by_idempotency_key(record.idempotency_key) or self.by_import(
            record.import_id
        )
        if existing:
            return existing
        # A savepoint allows a globally shared key collision to leave the surrounding
        # preview transaction usable. The losing portfolio/head writes roll back too.
        try:
            with connection.begin_nested():
                self.insert_version(connection, version, positions, previous)
                connection.execute(
                    insert(confirmations).values(
                        import_id=record.import_id,
                        tenant_id=version.tenant_id,
                        idempotency_key=record.idempotency_key,
                        portfolio_version_id=version.id,
                        excluded_rows=[row.model_dump(mode="json") for row in record.excluded_rows],
                        document=record.model_dump(mode="json"),
                    )
                )
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) != "23505" or getattr(
                getattr(exc.orig, "diag", None), "constraint_name", None
            ) not in {"import_confirmations_pkey", "import_confirmations_idempotency_key_key"}:
                raise
            existing = self.by_idempotency_key(record.idempotency_key) or self.by_import(
                record.import_id
            )
            if existing is None:
                raise
            return existing
        return record.model_copy(deep=True)

    def confirm(self, record, version, positions):
        if self.connection is not None:
            return self.confirm_in_transaction(record, version, positions)
        validate_confirmation(record, version, positions)
        with self.engine.begin() as connection:
            return type(self)(self.engine, connection).confirm_in_transaction(
                record, version, positions
            )

    def seed(self, version, positions):
        """Explicit fixture insertion, no receipt; idempotent under the tenant lock."""
        with self.engine.begin() as connection:
            previous = self.lock_head(connection, version.tenant_id)
            if connection.execute(
                select(versions.c.id).where(versions.c.id == version.id)
            ).scalar():
                return
            self.insert_version(connection, version, positions, previous)
