"""Local and cloud dev-stack launcher for Concord IQ.

Guarantees:

* ``make dev`` always starts safe local mode. Stale shell variables or ``.env``
  cloud tokens are stripped and the safe defaults are forced (see
  :func:`build_runtime_environment`).
* Cloud modes acquire a short-lived token at runtime via
  :mod:`concord.cloud_auth` and pass it to the child backend through the
  environment only — never on a command line, never printed, never written.
* The launcher manages only the child processes it starts. ``stop`` terminates
  exactly those PIDs from a local state file; it never broadly kills ``vite`` or
  ``uvicorn`` processes it did not start.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from concord import cloud_auth

LOCAL = "local"
FOUNDRY = "foundry"
FABRIC = "fabric"
WORK_IQ = "work-iq"
MODES = (LOCAL, FOUNDRY, FABRIC, WORK_IQ)

# Cloud bearer-token variables that must never leak into a local-mode child and
# must be replaced (not inherited) for cloud modes.
CLOUD_TOKEN_VARS = (
    "FOUNDRY_ACCESS_TOKEN",
    "FOUNDRY_IQ_ACCESS_TOKEN",
    "FABRIC_IQ_ACCESS_TOKEN",
    "WORK_IQ_ACCESS_TOKEN",
)

STATE_PATH = Path(".concord-dev/state.json")
DOTENV_PATH = Path(".env")

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:5173"


def _load_dotenv(path: Path = DOTENV_PATH) -> dict[str, str]:
    """Parse stable ``key=value`` pairs from ``.env`` (never tokens we acquire).

    Values already present in the process environment win, so this only supplies
    stable configuration (endpoints, IDs, client/tenant) the launcher itself
    needs for cloud-mode gating. The child backend also reads ``.env`` directly.
    """
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


# --------------------------------------------------------------------------- #
# Environment construction (security-critical, pure, fully tested)
# --------------------------------------------------------------------------- #
def build_runtime_environment(
    mode: str,
    *,
    base_env: dict[str, str] | None = None,
    token: str | None = None,
) -> dict[str, str]:
    """Build the child-process environment for ``mode``.

    Local mode is forced safe regardless of inherited values. Cloud modes set an
    explicit provider, budget, and exactly one freshly acquired token.
    """
    env = dict(os.environ if base_env is None else base_env)

    # Always remove inherited cloud bearer tokens first. A local child must never
    # receive one, and a cloud child must only receive the one we just acquired.
    for var in CLOUD_TOKEN_VARS:
        env.pop(var, None)

    if mode == LOCAL:
        env.update(
            {
                "PROVIDER": "local",
                "ALLOW_CLOUD": "false",
                "MAX_CLOUD_CALLS": "0",
                "AGENT_WORKFLOW_MODE": "strict",
                "CONCORD_WORKFLOW_MODE": "strict",
            }
        )
        env.setdefault("LLM_PROVIDER", "disabled")
        return env

    if mode not in MODES:
        raise ValueError(f"Unknown dev mode: {mode!r}. Expected one of {MODES}.")
    if not token:
        raise ValueError(f"Cloud mode {mode!r} requires a non-empty access token.")

    env.update(
        {
            "ALLOW_CLOUD": "true",
            "AGENT_WORKFLOW_MODE": "strict",
            "CONCORD_WORKFLOW_MODE": "strict",
        }
    )
    if mode == FOUNDRY:
        env["PROVIDER"] = "foundry_hosted"
        env.setdefault("MAX_CLOUD_CALLS", "20")
        env["FOUNDRY_ACCESS_TOKEN"] = token
    elif mode == FABRIC:
        env["PROVIDER"] = "fabric_iq"
        env.setdefault("MAX_CLOUD_CALLS", "6")
        env["FABRIC_IQ_ACCESS_TOKEN"] = token
    elif mode == WORK_IQ:
        env["PROVIDER"] = "work_iq"
        env.setdefault("MAX_CLOUD_CALLS", "3")
        env["WORK_IQ_ACCESS_TOKEN"] = token
    return env


def _acquire_token(mode: str, env: dict[str, str]) -> str:
    """Acquire the runtime token for a cloud ``mode`` (never logged)."""
    if mode == FOUNDRY:
        return cloud_auth.get_foundry_access_token()
    if mode == FABRIC:
        if not all(
            env.get(name)
            for name in ("FABRIC_WORKSPACE_ID", "FABRIC_LAKEHOUSE_ID", "FABRIC_ONTOLOGY_ID")
        ):
            missing = [
                name
                for name in ("FABRIC_WORKSPACE_ID", "FABRIC_LAKEHOUSE_ID", "FABRIC_ONTOLOGY_ID")
                if not env.get(name)
            ]
            raise cloud_auth.CloudAuthError(
                "Fabric IQ mode needs these .env values: " + ", ".join(missing)
            )
        return cloud_auth.get_fabric_access_token()
    if mode == WORK_IQ:
        return cloud_auth.get_work_iq_access_token(
            client_id=env.get("WORK_IQ_CLIENT_ID"),
            tenant_id=env.get("WORK_IQ_TENANT_ID"),
        )
    raise ValueError(f"{mode!r} is not a cloud mode.")


# --------------------------------------------------------------------------- #
# Banner (never prints token values)
# --------------------------------------------------------------------------- #
_MODE_LABELS = {
    LOCAL: ("local", "disabled"),
    FOUNDRY: ("foundry_hosted", "enabled"),
    FABRIC: ("fabric_iq", "enabled"),
    WORK_IQ: ("work_iq", "enabled"),
}


def render_banner(mode: str) -> str:
    provider, cloud = _MODE_LABELS[mode]
    return (
        f"Concord IQ {mode} mode\n"
        f"Backend:  {BACKEND_URL}\n"
        f"Frontend: {FRONTEND_URL}\n"
        f"Provider: {provider}\n"
        f"Cloud:    {cloud}"
    )


# --------------------------------------------------------------------------- #
# Cold-open verification (dev-fresh safety check)
# --------------------------------------------------------------------------- #
EXPECTED_COLD_OPEN = "counts=1600/1500/1334"


def _run_demo_text() -> str:
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "concord.demo"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        env=build_runtime_environment(LOCAL),
    )
    return proc.stdout + proc.stderr


def verify_cold_open(demo_text: Callable[[], str] = _run_demo_text) -> tuple[bool, str]:
    """Confirm the reset demo shows the unresolved three-way conflict.

    Returns (ok, detail). A previously promoted canonical would collapse the
    Active Customer conflict, so this guards the recording cold open.
    """
    text = demo_text()
    if EXPECTED_COLD_OPEN in text and "proposal drafted" in text:
        return True, "Active Customer conflict 1600/1500/1334 confirmed"
    return False, (
        "Cold-open conflict not found. A canonical promotion may still be in force; "
        "expected 'Active Customer ... counts=1600/1500/1334 ... proposal drafted'."
    )


# --------------------------------------------------------------------------- #
# Child-process management (only our own PIDs)
# --------------------------------------------------------------------------- #
class ProcessLike:  # pragma: no cover - structural typing aid
    pid: int

    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def wait(self, timeout: float | None = None) -> int: ...


Spawner = Callable[[Sequence[str], dict[str, str]], ProcessLike]


def _default_spawner(args: Sequence[str], env: dict[str, str]) -> ProcessLike:
    return subprocess.Popen(list(args), env=env)  # noqa: S603


@dataclass(slots=True)
class DevStack:
    """Starts and cleanly stops exactly the backend + frontend it spawns."""

    mode: str
    env: dict[str, str]
    spawn: Spawner = _default_spawner
    state_path: Path = STATE_PATH
    backend_cmd: Sequence[str] = (
        sys.executable,
        "-m",
        "uvicorn",
        "concord.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    )
    frontend_cmd: Sequence[str] = ("pnpm", "--dir", "frontend", "dev")
    processes: list[ProcessLike] = field(default_factory=list)

    def start(self) -> None:
        backend = self.spawn(self.backend_cmd, self.env)
        # The frontend never needs cloud tokens; give it a stripped local env.
        frontend_env = build_runtime_environment(LOCAL, base_env=self.env)
        frontend = self.spawn(self.frontend_cmd, frontend_env)
        self.processes = [backend, frontend]
        self._write_state()

    def _write_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "mode": self.mode,
            "pids": [proc.pid for proc in self.processes],
        }
        self.state_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def shutdown(self) -> None:
        for proc in self.processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in self.processes:
            with contextlib.suppress(Exception):
                proc.wait(timeout=10)
        self.state_path.unlink(missing_ok=True)

    def wait(self) -> None:
        try:
            for proc in self.processes:
                proc.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()


def stop_dev_stack(
    *,
    state_path: Path = STATE_PATH,
    killer: Callable[[int], None] | None = None,
) -> list[int]:
    """Terminate exactly the PIDs recorded by a previous launcher run."""
    if not state_path.exists():
        return []
    try:
        document = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state_path.unlink(missing_ok=True)
        return []
    send = killer or (lambda pid: os.kill(pid, signal.SIGTERM))
    stopped: list[int] = []
    for pid in document.get("pids", []):
        try:
            send(int(pid))
            stopped.append(int(pid))
        except (ProcessLookupError, PermissionError, ValueError):
            continue
    state_path.unlink(missing_ok=True)
    return stopped


# --------------------------------------------------------------------------- #
# Health probe (cloud modes only)
# --------------------------------------------------------------------------- #
def _default_probe(url: str) -> bool:  # pragma: no cover - real network
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
            return 200 <= response.status < 300
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run_dev_stack(
    mode: str,
    *,
    reset: bool = False,
    spawn: Spawner = _default_spawner,
    emit: Callable[[str], None] = print,
    base_env: dict[str, str] | None = None,
) -> DevStack:
    """Acquire any needed token, start the stack, print the banner, and wait."""
    if mode not in MODES:
        raise ValueError(f"Unknown dev mode: {mode!r}.")

    if reset:
        ok, detail = verify_cold_open()
        if not ok:
            raise SystemExit(detail)
        emit(detail)

    source_env = {**_load_dotenv(), **os.environ} if base_env is None else dict(base_env)
    token = None if mode == LOCAL else _acquire_token(mode, source_env)
    env = build_runtime_environment(mode, base_env=source_env, token=token)

    stack = DevStack(mode=mode, env=env, spawn=spawn)
    stack.start()
    emit(render_banner(mode))
    stack.wait()
    return stack


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Concord IQ dev-stack launcher")
    parser.add_argument("--mode", choices=MODES, default=LOCAL)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Verify the cold-open conflict before starting (dev-fresh).",
    )
    parser.add_argument("--stop", action="store_true", help="Stop a running dev stack.")
    parser.add_argument(
        "--verify-cold-open",
        action="store_true",
        help="Only verify the demo cold open and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    if args.stop:
        stopped = stop_dev_stack()
        print(f"Stopped {len(stopped)} Concord IQ dev process(es).")
        return
    if args.verify_cold_open:
        ok, detail = verify_cold_open()
        print(detail)
        if not ok:
            raise SystemExit(1)
        return
    run_dev_stack(args.mode, reset=args.reset)


if __name__ == "__main__":
    main()
