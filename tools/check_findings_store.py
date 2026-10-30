#!/usr/bin/env python3
"""Semantic integrity guard for the findings store (GAP-0002).

`tools/verify_repro_inputs.py` makes the findings store *tamper-evident* at the
byte level (a hash mismatch is flagged).  This tool adds the missing layer: it
checks the *meaning* of `src_re_geometry/re_findings_backup.yaml`, so an
accidental `findings.save` overwrite that drops evidence is caught even if the
hash manifest is later re-baselined.

Invariants enforced (the M7 headline the project depends on):

  1. The YAML parses and has a non-empty ``findings:`` list.
  2. f13 is the SOLE ``CONFIRMED`` visible-floor answer
     (exactly one finding tagged ``visible-floor`` with confidence CONFIRMED,
     and it is f13) -- the GAP-0008 resolution.
  3. f5 and f10 are NOT current CONFIRMED visible-floor answers
     (they are the SUPERSEDED vertex-buffer / chunk-35 claims).
  4. f13 still carries its M7 evidence references
     (the spawn-floor + G29 Pass-3 replays and the collision sector-table hash).

Usage:
    python3 tools/check_findings_store.py             # verify (default)
    python3 tools/check_findings_store.py verify
    python3 tools/check_findings_store.py snapshot    # record "I loaded this" hash
    python3 tools/check_findings_store.py guard-save NEW.yaml [--force]

`snapshot` + `guard-save` implement a load-before-save guard for the *committed*
canonical store: ``guard-save`` refuses to overwrite the store from NEW unless
(a) the store is byte-identical to the last ``snapshot`` (nobody clobbered it
underneath you since you loaded), and (b) NEW passes the invariants above.
``--force`` overrides the hash gate.  This does NOT intercept the DuckStation
server-side ``findings.save`` (that lives in the fork); it guards the step where
a freshly exported store is promoted to the tracked backup.

Exit code 0 = all invariants hold; 1 = a violation (or a refused save).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys

ABL_DIR = os.environ.get(
    "ABL_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DEFAULT_STORE = os.path.join(ABL_DIR, "src_re_geometry", "re_findings_backup.yaml")

# The single CONFIRMED visible-floor answer, and the superseded former claims.
VISIBLE_FLOOR_ID = "f13"
VISIBLE_FLOOR_TAG = "visible-floor"
SUPERSEDED_IDS = ("f5", "f10")
# Concrete M7 evidence anchors that must survive any future save of the store.
M7_ANCHORS = (
    "trace_spawn_floor.py",          # GAP-0011 spawn-floor render-source replay
    "trace_g29_pass3_arm_b.py",      # GAP-0038 Pass-3 counterfactual replay
    "6b7d858f",                      # collision sector-table SHA-256 (must be byte-stable)
)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_findings(path: str = DEFAULT_STORE) -> dict:
    """Parse the findings store. Raises on a parse error (that *is* a failure)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - declared in tools/requirements.txt
        raise RuntimeError(
            "PyYAML is required (pip install -r tools/requirements.txt)"
        ) from exc
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("findings store is not a YAML mapping")
    return data


def _finding_text(finding: dict) -> str:
    """All searchable text of a finding (notes + every evidence_ref field)."""
    parts = [str(finding.get("notes", ""))]
    for ref in finding.get("evidence_refs") or []:
        if isinstance(ref, dict):
            parts.extend(str(ref.get(k, "")) for k in ("summary", "path", "note"))
    return "\n".join(parts)


def check_invariants(data: dict) -> list[str]:
    """Return a list of human-readable invariant violations (empty == OK)."""
    errors: list[str] = []
    findings = data.get("findings")
    if not isinstance(findings, list) or not findings:
        return ["findings store has no non-empty 'findings:' list"]

    by_id = {f.get("id"): f for f in findings if isinstance(f, dict)}

    def conf(fid: str):
        f = by_id.get(fid)
        return f.get("confidence") if f else None

    # (2) f13 is the sole CONFIRMED visible-floor answer.
    confirmed_visible = [
        f
        for f in findings
        if isinstance(f, dict)
        and f.get("confidence") == "CONFIRMED"
        and VISIBLE_FLOOR_TAG in (f.get("tags") or [])
    ]
    ids = sorted(f.get("id") for f in confirmed_visible)
    if ids != [VISIBLE_FLOOR_ID]:
        errors.append(
            "expected exactly one CONFIRMED '%s' answer (%s); found: %s"
            % (VISIBLE_FLOOR_TAG, VISIBLE_FLOOR_ID, ids or "none")
        )

    # (3) f5/f10 are NOT current CONFIRMED visible-floor answers.
    for fid in SUPERSEDED_IDS:
        if fid not in by_id:
            errors.append(f"{fid} missing from store (expected SUPERSEDED finding)")
            continue
        if conf(fid) == "CONFIRMED":
            errors.append(f"{fid} is CONFIRMED but must not be a current confirmed answer")
        if fid in {f.get("id") for f in confirmed_visible}:
            errors.append(f"{fid} is tagged as a CONFIRMED visible-floor answer")

    # (4) f13 retains its M7 evidence anchors.
    f13 = by_id.get(VISIBLE_FLOOR_ID)
    if f13 is None:
        errors.append(f"{VISIBLE_FLOOR_ID} (visible-floor answer) is missing")
    else:
        if f13.get("confidence") != "CONFIRMED":
            errors.append(f"{VISIBLE_FLOOR_ID} must be CONFIRMED")
        text = _finding_text(f13)
        for anchor in M7_ANCHORS:
            if anchor not in text:
                errors.append(f"{VISIBLE_FLOOR_ID} lost M7 evidence anchor: {anchor!r}")
    return errors


def cmd_verify(store: str) -> int:
    if not os.path.exists(store):
        print(f"MISSING findings store: {store}", file=sys.stderr)
        return 1
    try:
        data = load_findings(store)
    except Exception as exc:  # parse failure is a real failure
        print(f"PARSE FAILED: {exc}", file=sys.stderr)
        return 1
    errors = check_invariants(data)
    if errors:
        print("FINDINGS-STORE INTEGRITY FAIL:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"OK: findings store invariants hold ({store})")
    return 0


def _lock_path(store: str) -> str:
    return store + ".loadlock"


def cmd_snapshot(store: str) -> int:
    if not os.path.exists(store):
        print(f"MISSING findings store: {store}", file=sys.stderr)
        return 1
    digest = _sha256(store)
    with open(_lock_path(store), "w", encoding="utf-8") as f:
        f.write(digest + "\n")
    print(f"snapshot: {digest}  {store}")
    return 0


def cmd_guard_save(store: str, src: str, force: bool) -> int:
    if not os.path.exists(src):
        print(f"source not found: {src}", file=sys.stderr)
        return 1
    # (a) load-before-save / hash-change gate
    if os.path.exists(store):
        cur = _sha256(store)
        lock = _lock_path(store)
        locked = None
        if os.path.exists(lock):
            with open(lock, encoding="utf-8") as f:
                locked = f.read().strip()
        if locked is None:
            if not force:
                print(
                    "REFUSING: no snapshot — run 'snapshot' right after findings.load, "
                    "or pass --force.",
                    file=sys.stderr,
                )
                return 1
        elif locked != cur and not force:
            print(
                "REFUSING: store changed since snapshot (possible un-loaded overwrite).\n"
                f"    snapshot {locked}\n    current  {cur}\n"
                "    re-load + snapshot, or pass --force.",
                file=sys.stderr,
            )
            return 1
    # (b) invariants on the incoming store
    try:
        new_data = load_findings(src)
    except Exception as exc:
        print(f"REFUSING: source parse failed: {exc}", file=sys.stderr)
        return 1
    errors = check_invariants(new_data)
    if errors:
        msg = "source violates findings invariants:\n" + "\n".join(f"  - {e}" for e in errors)
        if not force:
            print("REFUSING: " + msg, file=sys.stderr)
            return 1
        print("WARNING (--force): " + msg, file=sys.stderr)
    shutil.copyfile(src, store)
    with open(_lock_path(store), "w", encoding="utf-8") as f:
        f.write(_sha256(store) + "\n")
    print(f"saved: {src} -> {store}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Findings-store integrity guard (GAP-0002)")
    ap.add_argument("--store", default=DEFAULT_STORE, help="findings YAML (default: canonical backup)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("verify", help="check invariants (default)")
    sub.add_parser("snapshot", help="record the current store hash after findings.load")
    gs = sub.add_parser("guard-save", help="promote NEW to the store with a load-before-save guard")
    gs.add_argument("src", help="freshly exported findings YAML to promote")
    gs.add_argument("--force", action="store_true", help="override the hash/invariant gate")
    args = ap.parse_args(argv)

    if args.cmd == "snapshot":
        return cmd_snapshot(args.store)
    if args.cmd == "guard-save":
        return cmd_guard_save(args.store, args.src, args.force)
    return cmd_verify(args.store)


if __name__ == "__main__":
    raise SystemExit(main())
