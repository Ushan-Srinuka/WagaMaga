"""Use deployment/migration credentials; never mutate schema on API startup."""

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import Settings
from app.db.base import Base
from app.modules.farms import models as farm_models  # noqa: F401
from app.modules.identity import models  # noqa: F401 - register migration metadata
from app.modules.notifications import models as notification_models  # noqa: F401
from app.modules.support import models as support_models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def run_migrations() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    settings = Settings()
    use_test = context.get_x_argument(as_dictionary=True).get("db") == "test"
    url = settings.test_migration_database_url if use_test else settings.migration_database_url
    if url is None:
        raise RuntimeError(
            "Configure the appropriate MIGRATION_DATABASE_URL before running Alembic"
        )
    if context.is_offline_mode():
        context.configure(
            url=url.get_secret_value(),
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(url.get_secret_value(), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations()
