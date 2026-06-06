"""Shared integration fixtures using isolated PostgreSQL and DuckDB data."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from concord.config import Settings
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import LocalProvider
from concord.seed.seed_duckdb import seed_duckdb
from concord.storage.models import Base
from concord.storage.repositories import ReconciliationRepository
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    """Create a disposable schema inside the Docker Compose PostgreSQL service."""
    database_url = Settings().database_url
    schema = f"concord_test_{uuid4().hex}"
    admin_engine = create_engine(database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    test_url = make_url(database_url).update_query_dict({"options": f"-csearch_path={schema}"})
    engine = create_engine(test_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture(scope="session")
def p2_local_provider(tmp_path_factory: pytest.TempPathFactory) -> LocalProvider:
    data_dir = tmp_path_factory.mktemp("p2-synthetic")
    database_path = data_dir / "concord-iq.duckdb"
    seed_duckdb(database_path=database_path, data_dir=data_dir / "csv")
    return LocalProvider(duckdb_path=database_path)


@pytest.fixture
def reconciliation_runner(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> ReconciliationRunner:
    repository = ReconciliationRepository(postgres_engine)
    return ReconciliationRunner(
        provider=p2_local_provider,
        repository=repository,
        settings=Settings(),
    )
