"""Immutable portfolio chain and revisioned previews.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portfolio_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("previous_version_id", sa.UUID(), sa.ForeignKey("portfolio_versions.id")),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document", pg.JSONB(), nullable=False),
        sa.CheckConstraint("status = 'confirmed'", name="confirmed_status"),
        sa.CheckConstraint("confirmed_at >= imported_at", name="timestamp_order"),
        sa.UniqueConstraint(
            "tenant_id",
            "previous_version_id",
            name="linear_chain",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_table(
        "positions",
        sa.Column(
            "portfolio_version_id",
            sa.UUID(),
            sa.ForeignKey("portfolio_versions.id"),
            primary_key=True,
        ),
        sa.Column("instrument_id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("cost_basis", sa.Numeric()),
        sa.Column("document", pg.JSONB(), nullable=False),
    )
    op.create_table(
        "import_confirmations",
        sa.Column("import_id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False, unique=True),
        sa.Column(
            "portfolio_version_id",
            sa.UUID(),
            sa.ForeignKey("portfolio_versions.id"),
            nullable=False,
        ),
        sa.Column("excluded_rows", pg.JSONB(), nullable=False),
        sa.Column("document", pg.JSONB(), nullable=False),
    )
    op.create_table(
        "portfolio_heads",
        sa.Column("tenant_id", sa.UUID(), primary_key=True),
        sa.Column("version_id", sa.UUID(), sa.ForeignKey("portfolio_versions.id")),
    )
    op.create_table(
        "import_previews",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("document", pg.JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("""CREATE FUNCTION reject_confirmed_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'confirmed data is immutable'; END; $$""")
    for table in ("portfolio_versions", "positions", "import_confirmations"):
        op.execute(
            f"CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_confirmed_mutation()"
        )


def downgrade():
    for table in (
        "import_previews",
        "portfolio_heads",
        "import_confirmations",
        "positions",
        "portfolio_versions",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION reject_confirmed_mutation()")
