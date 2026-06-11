"""Deterministic tests for the dev-stack launcher.

No test starts a real server, Docker container, or network call. Process
spawning, signals, and cold-open verification are injected.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from concord import dev_launcher
from concord.dev_launcher import (
    DevStack,
    build_runtime_environment,
    render_banner,
    stop_dev_stack,
    verify_cold_open,
)

SECRET = "live-bearer-token-should-never-leak"

STALE_CLOUD_ENV = {
    "PROVIDER": "foundry_hosted",
    "ALLOW_CLOUD": "true",
    "MAX_CLOUD_CALLS": "20",
    "AGENT_WORKFLOW_MODE": "fast",
    "FOUNDRY_ACCESS_TOKEN": SECRET,
    "FABRIC_IQ_ACCESS_TOKEN": SECRET,
    "WORK_IQ_ACCESS_TOKEN": SECRET,
    "FOUNDRY_IQ_ACCESS_TOKEN": SECRET,
    "PATH": "/usr/bin",
}


# --------------------------------------------------------------------------- #
# build_runtime_environment — safe local mode
# --------------------------------------------------------------------------- #
def test_local_mode_overrides_stale_cloud_values() -> None:
    env = build_runtime_environment("local", base_env=dict(STALE_CLOUD_ENV))
    assert env["PROVIDER"] == "local"
    assert env["ALLOW_CLOUD"] == "false"
    assert env["MAX_CLOUD_CALLS"] == "0"
    assert env["AGENT_WORKFLOW_MODE"] == "strict"
    assert env["CONCORD_WORKFLOW_MODE"] == "strict"


def test_local_mode_strips_all_cloud_tokens() -> None:
    env = build_runtime_environment("local", base_env=dict(STALE_CLOUD_ENV))
    for var in dev_launcher.CLOUD_TOKEN_VARS:
        assert var not in env
    # Unrelated environment (PATH) is preserved.
    assert env["PATH"] == "/usr/bin"


# --------------------------------------------------------------------------- #
# build_runtime_environment — cloud child-process construction
# --------------------------------------------------------------------------- #
def test_foundry_mode_sets_provider_budget_and_single_token() -> None:
    env = build_runtime_environment("foundry", base_env={"PATH": "/x"}, token=SECRET)
    assert env["PROVIDER"] == "foundry_hosted"
    assert env["ALLOW_CLOUD"] == "true"
    assert int(env["MAX_CLOUD_CALLS"]) >= 1
    assert env["FOUNDRY_ACCESS_TOKEN"] == SECRET
    assert "FABRIC_IQ_ACCESS_TOKEN" not in env
    assert "WORK_IQ_ACCESS_TOKEN" not in env


def test_fabric_mode_sets_only_fabric_token() -> None:
    env = build_runtime_environment("fabric", base_env={}, token=SECRET)
    assert env["PROVIDER"] == "fabric_iq"
    assert env["FABRIC_IQ_ACCESS_TOKEN"] == SECRET
    assert "FOUNDRY_ACCESS_TOKEN" not in env


def test_work_iq_mode_sets_only_work_iq_token() -> None:
    env = build_runtime_environment("work-iq", base_env={}, token=SECRET)
    assert env["PROVIDER"] == "work_iq"
    assert env["WORK_IQ_ACCESS_TOKEN"] == SECRET


def test_cloud_mode_requires_token() -> None:
    with pytest.raises(ValueError):
        build_runtime_environment("foundry", base_env={}, token=None)


def test_unknown_mode_rejected() -> None:
    with pytest.raises(ValueError):
        build_runtime_environment("bogus", base_env={}, token="x")


# --------------------------------------------------------------------------- #
# Banner never prints token values
# --------------------------------------------------------------------------- #
def test_banner_has_no_token() -> None:
    banner = render_banner("foundry")
    assert "foundry_hosted" in banner
    assert "Cloud:    enabled" in banner
    assert SECRET not in banner
    assert render_banner("local").endswith("Cloud:    disabled")


# --------------------------------------------------------------------------- #
# Child-process lifecycle (cleanup on shutdown)
# --------------------------------------------------------------------------- #
class FakeProc:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.terminated = False
        self.waited = False
        self._alive = True

    def poll(self) -> int | None:
        return None if self._alive else 0

    def terminate(self) -> None:
        self.terminated = True
        self._alive = False

    def wait(self, timeout: float | None = None) -> int:
        self.waited = True
        return 0


def test_devstack_start_writes_state_and_shutdown_cleans_up(tmp_path: Path) -> None:
    spawned: list[FakeProc] = []

    def spawn(args: Sequence[str], env: dict[str, str]) -> FakeProc:
        proc = FakeProc(pid=4000 + len(spawned))
        spawned.append(proc)
        return proc

    state_path = tmp_path / "state.json"
    env = build_runtime_environment("local", base_env={"PATH": "/x"})
    stack = DevStack(mode="local", env=env, spawn=spawn, state_path=state_path)
    stack.start()

    assert state_path.exists()
    document = json.loads(state_path.read_text())
    assert document["mode"] == "local"
    assert document["pids"] == [proc.pid for proc in spawned]

    stack.shutdown()
    assert all(proc.terminated for proc in spawned)
    assert all(proc.waited for proc in spawned)
    assert not state_path.exists()


def test_frontend_child_never_receives_cloud_token(tmp_path: Path) -> None:
    captured: list[dict[str, str]] = []

    def spawn(args: Sequence[str], env: dict[str, str]) -> FakeProc:
        captured.append(env)
        return FakeProc(pid=10 + len(captured))

    cloud_env = build_runtime_environment("foundry", base_env={"PATH": "/x"}, token=SECRET)
    stack = DevStack(mode="foundry", env=cloud_env, spawn=spawn, state_path=tmp_path / "s.json")
    stack.start()

    backend_env, frontend_env = captured
    assert backend_env["FOUNDRY_ACCESS_TOKEN"] == SECRET
    assert "FOUNDRY_ACCESS_TOKEN" not in frontend_env
    assert frontend_env["PROVIDER"] == "local"


def test_wait_shuts_down_on_keyboard_interrupt(tmp_path: Path) -> None:
    class InterruptingProc(FakeProc):
        def wait(self, timeout: float | None = None) -> int:
            if timeout is None:
                raise KeyboardInterrupt
            return super().wait(timeout)

    proc = InterruptingProc(pid=1)
    stack = DevStack(
        mode="local",
        env={},
        spawn=lambda a, e: proc,
        state_path=tmp_path / "s.json",
    )
    stack.processes = [proc]
    stack._write_state()
    stack.wait()
    assert proc.terminated is True
    assert not (tmp_path / "s.json").exists()


# --------------------------------------------------------------------------- #
# stop — only our own recorded PIDs
# --------------------------------------------------------------------------- #
def test_stop_terminates_recorded_pids(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"mode": "local", "pids": [111, 222]}))
    killed: list[int] = []
    stopped = stop_dev_stack(state_path=state_path, killer=killed.append)
    assert stopped == [111, 222]
    assert killed == [111, 222]
    assert not state_path.exists()


def test_stop_with_no_state_is_noop(tmp_path: Path) -> None:
    assert stop_dev_stack(state_path=tmp_path / "missing.json", killer=lambda _: None) == []


def test_stop_skips_dead_pids(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"mode": "local", "pids": [111, 222]}))

    def killer(pid: int) -> None:
        if pid == 111:
            raise ProcessLookupError

    stopped = stop_dev_stack(state_path=state_path, killer=killer)
    assert stopped == [222]


# --------------------------------------------------------------------------- #
# dev-fresh cold-open verification
# --------------------------------------------------------------------------- #
def test_cold_open_passes_on_three_way_conflict() -> None:
    text = (
        "Active Customer: CONFLICT | counts=1600/1500/1334 | proposal drafted; "
        "human approval required\n"
    )
    ok, detail = verify_cold_open(demo_text=lambda: text)
    assert ok is True
    assert "1600/1500/1334" in detail


def test_cold_open_fails_when_canonical_already_promoted() -> None:
    text = "Active Customer: CONSISTENT | counts=1334/1334 | governed canonical v1\n"
    ok, detail = verify_cold_open(demo_text=lambda: text)
    assert ok is False
    assert "canonical" in detail.lower()


def test_run_dev_stack_aborts_when_cold_open_fails(tmp_path: Path) -> None:
    def spawn(args: Sequence[str], env: dict[str, str]) -> FakeProc:
        raise AssertionError("must not start servers when cold open fails")

    monkey = pytest.MonkeyPatch()
    monkey.setattr(dev_launcher, "verify_cold_open", lambda: (False, "canonical still in force"))
    try:
        with pytest.raises(SystemExit):
            dev_launcher.run_dev_stack("local", reset=True, spawn=spawn, base_env={})
    finally:
        monkey.undo()


# --------------------------------------------------------------------------- #
# .env loader (stable config only)
# --------------------------------------------------------------------------- #
def test_load_dotenv_parses_stable_values(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("# comment\nFABRIC_WORKSPACE_ID=abc\n\nWORK_IQ_CLIENT_ID=cid\nbad line\n")
    values = dev_launcher._load_dotenv(path)
    assert values["FABRIC_WORKSPACE_ID"] == "abc"
    assert values["WORK_IQ_CLIENT_ID"] == "cid"
    assert "bad line" not in values
