#!/usr/bin/env python3
"""Regression checks for the Phase 3 type-0x3f append wrapper.

This script writes only to a temporary directory. It does not mutate workspace
DAT/BIN/CUE files and does not build an ISO.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "insert_type3f_entries.py"
DEFAULT_DAT = ROOT / "DAT" / "LEVEL01_LEVEL.DAT"


def run(cmd: list[str], expect: int = 0) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(f"command exited {proc.returncode}, expected {expect}: {' '.join(cmd)}")
    return proc


def main() -> int:
    dat = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DAT
    if not dat.exists():
        raise SystemExit(f"input DAT not found: {dat}")

    python = sys.executable
    with tempfile.TemporaryDirectory(prefix="type3f_insert_regress_") as tmp:
        tmpdir = Path(tmp)
        out = tmpdir / "level01_type3f_append.DAT"
        report = tmpdir / "level01_type3f_append.md"

        run([python, "-m", "py_compile", str(TOOL)])
        run([python, str(TOOL), str(dat), "--entry-bytes", "00"], expect=1)
        run([python, str(TOOL), str(dat), "--append-new", "0x30:0:0:0"], expect=1)
        run(
            [
                python,
                str(TOOL),
                str(dat),
                "--append-clone",
                "64:512:0:0",
                "--append-new",
                "0x2a:5000:-50:-3600",
                "--entry-bytes",
                "40130000ceffffffb9f1ffff29000000",
            ]
        )
        run(
            [
                python,
                str(TOOL),
                str(dat),
                "--append-clone",
                "64:512:0:0",
                "--append-new",
                "0x2a:5000:-50:-3600",
                "--entry-bytes",
                "40130000ceffffffb9f1ffff29000000",
                "--write",
                "--out",
                str(out),
                "--report",
                str(report),
            ]
        )
        if not out.exists() or out.stat().st_size != dat.stat().st_size + 0x30:
            raise SystemExit("regression failed: output size was not input + 0x30")
        if not report.exists() or "final scan fields" not in report.read_text():
            raise SystemExit("regression failed: report did not include hardening fields")

    print("type-0x3f insert regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
