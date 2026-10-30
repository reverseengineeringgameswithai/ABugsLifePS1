#!/usr/bin/env python3
"""Integrity checker for the project's critical, hard-to-regenerate inputs (GAP-0002).

Why: several inputs the verification layer depends on live outside easy reproduction
and one of them (the findings store) has a documented OVERWRITE hazard
(`findings.save` clobbers it). This tool hashes those inputs and compares against a
committed manifest so loss / corruption / an accidental overwrite is DETECTABLE.

Usage:
    python3 tools/verify_repro_inputs.py            # verify against the manifest
    python3 tools/verify_repro_inputs.py --write    # (re)baseline the manifest

Recommended guard around the DuckStation findings API:
    verify_repro_inputs.py            # before a session  -> baseline matches
    ... run experiments / findings.save ...
    verify_repro_inputs.py            # after  -> a CHANGED findings store is flagged,
                                      #   so an unintended overwrite cannot pass silently.

Exit code 0 = all present and matching; 1 = a mismatch or a missing declared
input. Host-local save fixtures (*.sav) remain advisory, but every assembly
source consumed by ``config/segments.yml`` is a required centrally pinned
external input for clean-checkout reconstruction.
"""
import hashlib
import os
import shutil
import sys

import yaml

ABL_DIR = os.environ.get("ABL_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(ABL_DIR, "tools", "repro_inputs.sha256")
OPERATOR_ROOT = os.environ.get(
    "ABL_OPERATOR_ROOT", os.path.join(os.path.expanduser("~"), "Downloads", "ABL"))
SEGMENTS = os.path.join(ABL_DIR, "config", "segments.yml")

# CORE = repo-relative, should be committed; a missing/changed CORE input fails the run.
CORE = [
    "src_re_geometry/re_findings_backup.yaml",   # the canonical findings store (overwrite hazard)
    "tools/raw_chunk0_compressed.bin",            # LEVEL.RAW codec oracle (in)  -- force-add to git
    "tools/raw_chunk0_decompressed.bin",          # LEVEL.RAW codec oracle (out) -- force-add to git
    "tools/LEVEL_RAW_decompressed/chunk_index.json",
    "tools/FORK_COMMIT.txt",                      # the pinned DuckStation fork hash
]
# FIXTURES = host-local save states (gitignored); advisory only.
FIXTURE_GLOB_DIR = ABL_DIR
# SUBSTRATE = matched hand-written asm (asm/hand_written/, LOCAL-ONLY by
# preservation policy — the assembled bytes equal the copyrighted original's).
# Contract: these bytes stay outside Git, but a closure checkout provisions the
# complete hash-pinned set before building. Missing is a failure, never a skip.
SUBSTRATE_DIR = os.path.join(ABL_DIR, "asm", "hand_written")


def _declared_substrate():
    doc = yaml.safe_load(open(SEGMENTS))
    rows = set()
    for item in doc.get("attempted") or []:
        source = item.get("source")
        if isinstance(source, str) and source.startswith("asm/hand_written/"):
            rows.add(source)
        for part in item.get("parts") or []:
            source = part.get("source")
            if isinstance(source, str) and source.startswith("asm/hand_written/"):
                rows.add(source)
    return sorted(rows)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def _fixtures():
    return sorted(f for f in os.listdir(FIXTURE_GLOB_DIR) if f.endswith(".sav"))


def write_manifest():
    lines = ["# Critical reproducibility inputs - SHA-256 (GAP-0002). Regenerate: verify_repro_inputs.py --write",
             "# CORE (commit these; oracles need `git add -f`):"]
    for rel in CORE:
        p = os.path.join(ABL_DIR, rel)
        if os.path.exists(p):
            lines.append(f"{_sha256(p)}  {rel}")
        else:
            lines.append(f"MISSING  {rel}")
    subs = _declared_substrate()
    if subs:
        lines.append("# SUBSTRATE (required external derived assembly; provision by exact hash):")
        for rel in subs:
            source = os.path.join(OPERATOR_ROOT, rel)
            if not os.path.isfile(source):
                raise SystemExit(f"operator substrate source missing: {source}")
            lines.append(f"{_sha256(source)}  {rel}")
    figs = _fixtures()
    lines.append(f"# FIXTURES: {len(figs)} host-local *.sav present (advisory; never committed).")
    lines.append("#   Headline replay-fixture hashes -> tools/fixtures.sha256 (tests/test_fixtures_manifest.py).")
    lines.append("#   Findings-store semantics    -> tools/check_findings_store.py (tests/test_findings_store.py).")
    with open(MANIFEST, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {MANIFEST}  ({sum(1 for r in CORE if os.path.exists(os.path.join(ABL_DIR, r)))}/{len(CORE)} core present, {len(figs)} fixtures)")


def provision():
    """Copy only centrally pinned derived sources from the operator root."""
    if not os.path.isfile(MANIFEST):
        print("no manifest; run with --write first", file=sys.stderr)
        return 1
    wanted = set(_declared_substrate())
    pinned = {}
    for line in open(MANIFEST):
        parts = line.split()
        if len(parts) == 2 and parts[1].startswith("asm/hand_written/"):
            pinned[parts[1]] = parts[0]
    if set(pinned) != wanted:
        print("substrate manifest/config source set mismatch", file=sys.stderr)
        return 1
    for rel in sorted(wanted):
        source = os.path.join(OPERATOR_ROOT, rel)
        target = os.path.join(ABL_DIR, rel)
        if not os.path.isfile(source) or _sha256(source) != pinned[rel]:
            print(f"operator source missing or mismatched: {rel}", file=sys.stderr)
            return 1
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if os.path.exists(target):
            if not os.path.isfile(target) or _sha256(target) != pinned[rel]:
                print(f"refusing to overwrite mismatched checkout source: {rel}",
                      file=sys.stderr)
                return 1
            continue
        shutil.copyfile(source, target)
        if _sha256(target) != pinned[rel]:
            print(f"provisioned copy failed verification: {rel}", file=sys.stderr)
            return 1
    print(f"provisioned {len(wanted)} hash-verified substrate sources from {OPERATOR_ROOT}")
    return verify()


def verify():
    if not os.path.exists(MANIFEST):
        print("no manifest; run with --write first", file=sys.stderr)
        return 1
    expected = {}
    for ln in open(MANIFEST):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        h, rel = ln.split(None, 1)
        expected[rel] = h
    bad = 0
    for rel, h in expected.items():
        p = os.path.join(ABL_DIR, rel)
        if not os.path.exists(p):
            print(f"MISSING  {rel}"); bad += 1; continue
        actual = _sha256(p)
        if h == "MISSING":
            print(f"NOW-PRESENT (rebaseline)  {rel}")
        elif actual != h:
            print(f"CHANGED  {rel}\n    expected {h}\n    actual   {actual}"); bad += 1
        else:
            print(f"ok  {rel}")
    figs = _fixtures()
    print(f"fixtures: {len(figs)} *.sav present (advisory, host-local)")
    if bad:
        print(f"\nFAIL: {bad} core input(s) missing or changed.", file=sys.stderr)
    else:
        print("\nOK: all core inputs present and matching.")
    return 1 if bad else 0


if __name__ == "__main__":
    if "--provision" in sys.argv:
        sys.exit(provision())
    elif "--write" in sys.argv:
        write_manifest()
    else:
        sys.exit(verify())
