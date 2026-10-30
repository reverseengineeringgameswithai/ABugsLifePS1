#!/usr/bin/env python3
"""Regression checks for the Phase 6 cross-level validation tool.

This script writes only to a temporary directory for report outputs and
verifies that the pristine input DATs are not mutated by a validation run.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "validate_levels_phase6.py"
CANONICAL = [ROOT / "DAT" / f"LEVEL{n:02d}_LEVEL.DAT" for n in range(0, 11)]


def sha1_file(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def run(cmd: list[str], expect: int = 0) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        cmd, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(f"command exited {proc.returncode}, expected {expect}: {' '.join(cmd)}")
    return proc


def main() -> int:
    # 1) Tool compiles.
    run([sys.executable, "-m", "py_compile", str(TOOL)])

    present = [p for p in CANONICAL if p.exists()]
    if not present:
        raise SystemExit("no canonical LEVEL*_LEVEL.DAT inputs found")
    pre = {p: sha1_file(p) for p in present}

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "phase6.csv"
        md_path = Path(tmp) / "phase6.md"

        # 2) --no-write must not create reports.
        run([sys.executable, str(TOOL), "--no-write",
             "--csv", str(csv_path), "--md", str(md_path)])
        if csv_path.exists() or md_path.exists():
            raise SystemExit("--no-write produced report files")

        # 3) Default run writes reports to the temp paths.
        proc = run([sys.executable, str(TOOL), "--csv", str(csv_path), "--md", str(md_path)])
        if not csv_path.exists() or not md_path.exists():
            raise SystemExit("expected CSV and Markdown reports were not written")

        out = proc.stdout
        # 4) Known cross-level facts hold.
        checks = {
            "LEVEL00 has no type-0x3f": "LEVEL00_LEVEL.DAT,no,",
            "LEVEL01 baseline 70 / 1248 reloc sites": "LEVEL01_LEVEL.DAT,yes,0x000004,70,baseline,1248,yes",
            "LEVEL04 unusual count 47": "LEVEL04_LEVEL.DAT,yes,0x000004,47,-23,",
        }
        for label, needle in checks.items():
            if needle not in out:
                print(out)
                raise SystemExit(f"missing expected fact: {label}")

        # 5) At least one level reports the unknown 0x31 kind.
        if "0x31" not in out:
            raise SystemExit("expected unknown source kind 0x31 in at least one level")

        md_text = md_path.read_text()
        if "confirmed entry-index -> identity map is proven for LEVEL01 only" not in md_text:
            raise SystemExit("Markdown report missing LEVEL01-only standing caution")

    # 6) No input DAT was mutated.
    for p, before in pre.items():
        after = sha1_file(p)
        if before != after:
            raise SystemExit(f"input mutated: {p}")

    print("phase6 regression OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
