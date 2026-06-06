"""PostgreSQL engine creation and schema initialization."""

from sqlalchemy import Engine, create_engine

from concord.config import Settings
from concord.storage.models import Base


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Create a PostgreSQL engine without opening a connection eagerly."""
    active_settings = settings or Settings()
    return create_engine(active_settings.database_url, pool_pre_ping=True)


def initialize_database(settings: Settings | None = None) -> None:
    """Create the P0 semantic registry tables."""
    engine = create_database_engine(settings)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    initialize_database()
    print("PostgreSQL schema initialized.")
