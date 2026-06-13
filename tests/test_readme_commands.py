"""Guard that every `make <target>` named in the README is a real Makefile target."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"
README = REPO_ROOT / "README.md"


def _makefile_targets() -> set[str]:
    targets: set[str] = set()
    for line in MAKEFILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([a-zA-Z0-9_-]+):", line)
        if match:
            targets.add(match.group(1))
    return targets


def _code_spans(text: str) -> list[str]:
    """Return inline-code spans and fenced code blocks (prose excluded)."""
    spans = re.findall(r"`([^`\n]+)`", text)
    spans += re.findall(r"```[a-zA-Z]*\n(.*?)```", text, flags=re.DOTALL)
    return spans


def _readme_make_commands() -> set[str]:
    text = README.read_text(encoding="utf-8")
    found: set[str] = set()
    for span in _code_spans(text):
        found.update(re.findall(r"\bmake\s+([a-z][a-z0-9-]+)\b", span))
    return found


def test_every_readme_make_command_is_a_real_target() -> None:
    targets = _makefile_targets()
    commands = _readme_make_commands()
    assert commands, "expected the README to document make commands"
    missing = sorted(cmd for cmd in commands if cmd not in targets)
    assert not missing, f"README references undefined Makefile targets: {missing}"


def test_primary_commands_exist() -> None:
    targets = _makefile_targets()
    for command in (
        "help",
        "setup",
        "dev",
        "dev-local",
        "dev-fresh",
        "dev-foundry",
        "dev-fabric",
        "dev-work-iq",
        "stop",
        "foundry-hosted-deploy",
        "foundry-hosted-smoke",
        "judge-proof",
        "cloud-proof",
    ):
        assert command in targets, f"missing Makefile target: {command}"
