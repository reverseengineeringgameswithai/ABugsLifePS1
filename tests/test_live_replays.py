"""Opt-in `live` regression: replay a headline experiment via its tracked runner (GAP-0040).

This is the automated-replay path for the live headline findings. It is **excluded from
the safe suite** (`tools/run_safe_tests.py` filters the `live` marker) AND additionally
gated behind the ``ABL_LIVE`` env var + fixture presence, so it never runs in CI or
without owner setup — it can only skip there, never fail.

Operator usage (with the isolated DuckStation fork instance already up on the default
port/token and the spawn fixture present):

    ABL_LIVE=1 ABL_SPAWN_SAV=<level01-spawn>.sav python3 -m pytest -m live tests/test_live_replays.py

It invokes ``tools/trace_spawn_floor.py`` (identifies the visible spawn-floor render
source = LEVEL.DAT via fcn.80010000; it authenticates, asserts disc/fixture identity,
self-checks its verdict, and returns 0 only on success) and asserts exit 0. No media is
ever supplied to CI.
"""

from pathlib import Path
import os
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _savestate_dir() -> Path:
    return Path(
        os.environ.get(
            "ABL_SAVESTATES",
            os.path.expanduser("~/.local/share/duckstation/savestates"),
        )
    )


@pytest.mark.live
def test_spawn_floor_replay() -> None:
    if not os.environ.get("ABL_LIVE"):
        pytest.skip(
            "live replay is opt-in: set ABL_LIVE=1 with the isolated DuckStation "
            "instance running (port 23460) and the spawn fixture present"
        )
    # Numbered-slot fixtures were retired 2026-07-08; the live replay names its
    # LEVEL01 spawn state explicitly via ABL_SPAWN_SAV.
    save_env = os.environ.get("ABL_SPAWN_SAV")
    if not save_env:
        pytest.skip("set ABL_SPAWN_SAV to a LEVEL01 spawn .sav for the live replay")
    save = Path(save_env).expanduser()
    if not save.is_absolute():
        save = _savestate_dir() / save
    if not save.exists():
        pytest.skip(f"spawn fixture absent: {save}")

    proc = subprocess.run(
        [sys.executable, "tools/trace_spawn_floor.py", "--save", str(save)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, (
        f"trace_spawn_floor.py exited {proc.returncode} "
        f"(0 = spawn floor confirmed DAT-backed via fcn.80010000)\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
