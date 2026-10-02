"""Explicit dev/test-only synthetic seed: python -m app.db.seed_fixture."""

import os

from app.db.engine import check_startup, dispose_engine, get_engine
from app.db.repositories import PostgresPortfolioRepository
from app.services.portfolios import FilePortfolioRepository


def main():
    if os.environ.get("MS_ENV") not in {"dev", "test"}:
        raise SystemExit("Fixture seed requires MS_ENV=dev or MS_ENV=test")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("Fixture seed requires DATABASE_URL")
    try:
        engine = get_engine()
        check_startup(engine)
        source = FilePortfolioRepository()
        PostgresPortfolioRepository(engine).seed(
            source.version, source.positions(source.version.id)
        )
    finally:
        dispose_engine()


if __name__ == "__main__":
    main()
