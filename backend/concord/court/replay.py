"""Replay a captured Semantic Court session with no cloud and no model.

The hosted app and judges run the court by replaying a previously captured transcript.
The replay is labeled honestly: the transcript-level mode becomes ``replayed`` while each
turn keeps the provenance it was captured with (a live turn stays marked generated). The
content digest is preserved, so a replay is verifiably the same debate that was captured.
"""

from __future__ import annotations

from pathlib import Path

from concord.court.transcript import DeliberationTranscript, TranscriptMode


class DeliberationReplayNotFound(RuntimeError):
    """Raised when no captured transcript exists at the configured path."""


class DeliberationReplayProvider:
    """Serve a captured court transcript deterministically as a replay."""

    def __init__(self, path: Path) -> None:
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise DeliberationReplayNotFound(
                f"Captured deliberation transcript not found: {path}"
            ) from error
        self._captured = DeliberationTranscript.model_validate_json(raw)

    @property
    def captured_mode(self) -> TranscriptMode:
        """How the transcript was originally produced (live or deterministic fallback)."""
        return self._captured.mode

    def transcript(self) -> DeliberationTranscript:
        """Return the captured debate, labeled as a replay."""
        return self._captured.model_copy(update={"mode": TranscriptMode.REPLAYED})
