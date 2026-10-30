#!/usr/bin/env python3
"""Run the M2 safe suite without emulator, GPU, or owner-supplied media."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "not gpu and not live and not local_media",
            "tests",
        ],
        cwd=ROOT,
        env=env,
    )


if __name__ == "__main__":
    raise SystemExit(main())
