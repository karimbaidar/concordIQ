"""P0 acceptance tests for deterministic synthetic data."""

from pathlib import Path

import duckdb
from concord.seed.seed_duckdb import seed_duckdb
from concord.seed.synthetic_data import TABLE_FIELDS

EXPECTED_DIGEST = "03cd1014ad79dc54a890228d01b15b534e819274447c01c0871887dd3932e8b3"


def _database_snapshot(database_path: Path) -> dict[str, list[tuple[object, ...]]]:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return {
            table_name: connection.execute(f'SELECT * FROM "{table_name}" ORDER BY 1').fetchall()
            for table_name in TABLE_FIELDS
        }


def test_synthetic_seed_is_deterministic(tmp_path: Path) -> None:
    first_manifest = seed_duckdb(
        database_path=tmp_path / "first.duckdb",
        data_dir=tmp_path / "first-data",
    )
    second_manifest = seed_duckdb(
        database_path=tmp_path / "second.duckdb",
        data_dir=tmp_path / "second-data",
    )

    assert first_manifest.seed == second_manifest.seed
    assert first_manifest.digest == second_manifest.digest
    assert first_manifest.digest == EXPECTED_DIGEST
    assert first_manifest.row_counts == second_manifest.row_counts
    assert _database_snapshot(first_manifest.database_path) == _database_snapshot(
        second_manifest.database_path
    )
    assert all(row_count > 0 for row_count in first_manifest.row_counts.values())
