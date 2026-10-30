#!/usr/bin/env python3
"""Regression checks for the Phase 5 rebuild integration wrapper.

This script writes only to a temporary directory for patched DAT and image
outputs. It temporarily stages REBUILD/files/LEVEL01/LEVEL.DAT through the
Phase 5 wrapper, which restores the staged file before returning.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLY_TOOL = ROOT / "tools" / "apply_level_placements.py"
REBUILD_TOOL = ROOT / "tools" / "rebuild_with_patched_dat.py"
STAGED_DAT = ROOT / "REBUILD" / "files" / "LEVEL01" / "LEVEL.DAT"
STAGED_ORIG = ROOT / "REBUILD" / "files" / "LEVEL01" / "LEVEL.DAT.orig"


def sha1_file(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


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
    if sha1_file(STAGED_DAT) != sha1_file(STAGED_ORIG):
        raise SystemExit(f"staged DAT is not pristine before regression: {STAGED_DAT}")

    python = sys.executable
    before_sha1 = sha1_file(STAGED_DAT)
    with tempfile.TemporaryDirectory(prefix="type3f_rebuild_regress_") as tmp:
        tmpdir = Path(tmp)
        spec = tmpdir / "level01_phase5_spec.yaml"
        patched = tmpdir / "level01_phase5_spec.DAT"
        patched_report = tmpdir / "level01_phase5_spec.md"
        out_bin = tmpdir / "level01_phase5_rebuild.bin"
        out_cue = tmpdir / "level01_phase5_rebuild.cue"
        rebuild_report = tmpdir / "level01_phase5_rebuild.md"

        spec.write_text(
            "\n".join(
                [
                    "level: LEVEL01",
                    "source_dat: DAT/LEVEL01_LEVEL.DAT",
                    "operations:",
                    "  - op: move",
                    "    entry: 56",
                    "    dx: 1",
                    "    dy: 0",
                    "    dz: 0",
                    "  - op: append_new",
                    "    kind: 0x29",
                    "    x: 4928",
                    "    y: -50",
                    "    z: -3655",
                    "",
                ]
            )
        )

        run([python, "-m", "py_compile", str(REBUILD_TOOL)])
        run(
            [
                python,
                str(APPLY_TOOL),
                str(spec),
                "--write",
                "--out",
                str(patched),
                "--report",
                str(patched_report),
            ]
        )
        patched_sha1 = sha1_file(patched)
        run(
            [
                python,
                str(REBUILD_TOOL),
                "--patched-dat",
                str(patched),
                "--out-bin",
                str(out_bin),
                "--out-cue",
                str(out_cue),
                "--expected-sha1",
                patched_sha1,
            ]
        )
        if out_bin.exists() or out_cue.exists():
            raise SystemExit("dry-run unexpectedly wrote rebuild outputs")
        run(
            [
                python,
                str(REBUILD_TOOL),
                "--patched-dat",
                str(patched),
                "--out-bin",
                str(out_bin),
                "--out-cue",
                str(out_cue),
                "--expected-sha1",
                patched_sha1,
                "--write",
                "--report",
                str(rebuild_report),
            ]
        )
        if not out_bin.exists() or not out_cue.exists():
            raise SystemExit("write run did not produce image outputs")
        if "embedded sha1" not in rebuild_report.read_text():
            raise SystemExit("rebuild report missing embedded sha1")

    after_sha1 = sha1_file(STAGED_DAT)
    if after_sha1 != before_sha1:
        raise SystemExit(f"staged DAT was not restored: {after_sha1} != {before_sha1}")

    print("rebuild integration regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
