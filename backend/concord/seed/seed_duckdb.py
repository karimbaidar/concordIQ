"""Seed DuckDB and committed CSV fixtures from deterministic synthetic data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import duckdb

from concord.seed.synthetic_data import (
    FIXED_SEED,
    TABLE_FIELDS,
    generate_synthetic_data,
    write_synthetic_csvs,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPOSITORY_ROOT / "data" / "synthetic"
DEFAULT_DATABASE_PATH = REPOSITORY_ROOT / "data" / "concord_iq.duckdb"


@dataclass(frozen=True)
class SeedManifest:
    """Stable facts emitted by a seed run."""

    seed: int
    digest: str
    row_counts: dict[str, int]
    database_path: Path
    data_dir: Path


def seed_duckdb(
    database_path: Path = DEFAULT_DATABASE_PATH,
    data_dir: Path = DEFAULT_DATA_DIR,
    seed: int = FIXED_SEED,
) -> SeedManifest:
    """Regenerate synthetic CSVs and load them into a DuckDB database."""
    dataset = generate_synthetic_data(seed)
    write_synthetic_csvs(dataset, data_dir)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(database_path)) as connection:
        for table_name in TABLE_FIELDS:
            connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            connection.read_csv(str(data_dir / f"{table_name}.csv"), header=True).create(table_name)

    return SeedManifest(
        seed=seed,
        digest=dataset.digest,
        row_counts=dataset.row_counts,
        database_path=database_path,
        data_dir=data_dir,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--seed", type=int, default=FIXED_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = seed_duckdb(args.database, args.data_dir, args.seed)
    counts = ", ".join(f"{name}={count}" for name, count in manifest.row_counts.items())
    print(f"Seeded DuckDB with seed={manifest.seed} digest={manifest.digest}")
    print(f"Rows: {counts}")
    print(f"Database: {manifest.database_path}")


if __name__ == "__main__":
    main()
