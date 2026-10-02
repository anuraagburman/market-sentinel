"""Relational constraints plus original documents for lossless wire round trips."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    UUID,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()
versions = Table(
    "portfolio_versions",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("tenant_id", UUID, nullable=False),
    Column("previous_version_id", UUID, ForeignKey("portfolio_versions.id")),
    Column("status", String, nullable=False),
    Column("imported_at", DateTime(timezone=True), nullable=False),
    Column("confirmed_at", DateTime(timezone=True), nullable=False),
    Column("document", JSONB, nullable=False),
    CheckConstraint("status = 'confirmed'", name="confirmed_status"),
    CheckConstraint("confirmed_at >= imported_at", name="timestamp_order"),
    UniqueConstraint(
        "tenant_id", "previous_version_id", name="linear_chain", postgresql_nulls_not_distinct=True
    ),
)
positions = Table(
    "positions",
    metadata,
    Column("portfolio_version_id", UUID, ForeignKey("portfolio_versions.id"), primary_key=True),
    Column("instrument_id", UUID, primary_key=True),
    Column("tenant_id", UUID, nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("quantity", Numeric, nullable=False),
    Column("cost_basis", Numeric),
    Column("document", JSONB, nullable=False),
)
confirmations = Table(
    "import_confirmations",
    metadata,
    Column("import_id", UUID, primary_key=True),
    Column("tenant_id", UUID, nullable=False),
    Column("idempotency_key", String, nullable=False, unique=True),
    Column("portfolio_version_id", UUID, ForeignKey("portfolio_versions.id"), nullable=False),
    Column("excluded_rows", JSONB, nullable=False),
    Column("document", JSONB, nullable=False),
)
heads = Table(
    "portfolio_heads",
    metadata,
    Column("tenant_id", UUID, primary_key=True),
    Column("version_id", UUID, ForeignKey("portfolio_versions.id")),
)
previews = Table(
    "import_previews",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("tenant_id", UUID, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("document", JSONB, nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
)
