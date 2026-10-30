"""Shared import path for tracked tools, without installing the project."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


import subprocess

import pytest


def require_git():
    """Skip when not running inside a git checkout (e.g. a source archive)."""
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"], cwd=ROOT,
                       capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("requires a git checkout (git metadata absent in archives)")
