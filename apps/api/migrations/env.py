"""Run migrations against the explicitly configured database."""

import os

from alembic import context
from sqlalchemy import create_engine, pool

from app.db.tables import metadata

config = context.config
url = config.get_main_option("sqlalchemy.url") or os.environ.get("DATABASE_URL")


def run():
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=metadata)
            with context.begin_transaction():
                context.run_migrations()
        engine.dispose()


run()
