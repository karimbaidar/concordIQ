"""PostgreSQL engine creation and schema initialization."""

from sqlalchemy import Engine, create_engine, inspect, text

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
    ensure_schema_compatibility(engine)


def ensure_schema_compatibility(engine: Engine) -> None:
    """Apply tiny additive upgrades for local pre-Alembic development databases."""
    inspector = inspect(engine)
    if "agent_trace_events" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("agent_trace_events")}
    if "deliberations" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE agent_trace_events ADD COLUMN deliberations JSON"))


if __name__ == "__main__":
    initialize_database()
    print("Concord IQ registry schema initialized.")
