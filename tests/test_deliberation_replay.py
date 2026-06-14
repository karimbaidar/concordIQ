"""Capturing and replaying a Semantic Court session — the agent-layer replay proof."""

import json
from pathlib import Path

import pytest
from concord.config import ScenarioPack, Settings
from concord.court import DeliberationReplayProvider, TranscriptMode
from concord.court.capture import capture_deliberation
from concord.court.deliberation_check import (
    DeliberationCheckError,
    validate_deliberation_artifact,
)
from concord.seed.seed_duckdb import seed_duckdb
from sqlalchemy import Engine


@pytest.fixture(scope="session")
def seeded_duckdb(tmp_path_factory: pytest.TempPathFactory) -> Path:
    data_dir = tmp_path_factory.mktemp("court-capture")
    database_path = data_dir / "concord-iq.duckdb"
    seed_duckdb(database_path=database_path, data_dir=data_dir / "csv")
    return database_path


def _settings(postgres_engine: Engine, seeded_duckdb: Path) -> Settings:
    return Settings(
        _env_file=None,
        provider="local",
        scenario_pack=ScenarioPack.LEARNING,
        database_url=postgres_engine.url.render_as_string(hide_password=False),
        duckdb_path=seeded_duckdb,
    )


@pytest.fixture
def captured_file(postgres_engine: Engine, seeded_duckdb: Path, tmp_path: Path) -> Path:
    output = tmp_path / "certification-ready.deliberation.json"
    capture_deliberation(_settings(postgres_engine, seeded_duckdb), output_path=output)
    return output


def test_capture_validate_and_replay_round_trip(
    postgres_engine: Engine,
    seeded_duckdb: Path,
    tmp_path: Path,
) -> None:
    output = tmp_path / "deliberation.json"
    captured = capture_deliberation(_settings(postgres_engine, seeded_duckdb), output_path=output)
    assert output.exists()
    assert captured.mode is TranscriptMode.DETERMINISTIC_FALLBACK

    validated = validate_deliberation_artifact(output)
    assert validated.content_digest == captured.content_digest
    assert len(validated.turns) == 16

    provider = DeliberationReplayProvider(output)
    replayed = provider.transcript()
    # Replays with no cloud and no model, honestly labeled, verifiably the same debate.
    assert replayed.mode is TranscriptMode.REPLAYED
    assert provider.captured_mode is TranscriptMode.DETERMINISTIC_FALLBACK
    assert replayed.content_digest == captured.content_digest
    assert tuple(t.content for t in replayed.turns) == tuple(t.content for t in captured.turns)
    assert replayed.verdict == "conflict"
    assert replayed.outcome == "proposal"


def test_validator_rejects_secret_shaped_text(captured_file: Path) -> None:
    text = captured_file.read_text(encoding="utf-8")
    captured_file.write_text(
        text.replace("The court is convened", "Bearer leaked-token", 1),
        encoding="utf-8",
    )
    with pytest.raises(DeliberationCheckError, match="secret-shaped"):
        validate_deliberation_artifact(captured_file)


def test_validator_rejects_edited_transcript(captured_file: Path) -> None:
    data = json.loads(captured_file.read_text(encoding="utf-8"))
    data["turns"][0]["content"] = "tampered after capture"
    captured_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(DeliberationCheckError, match="digest"):
        validate_deliberation_artifact(captured_file)


def test_validator_rejects_a_prereplayed_artifact(captured_file: Path) -> None:
    data = json.loads(captured_file.read_text(encoding="utf-8"))
    data["mode"] = "replayed"
    captured_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(DeliberationCheckError, match="live_captured or deterministic_fallback"):
        validate_deliberation_artifact(captured_file)
