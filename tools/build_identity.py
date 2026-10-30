#!/usr/bin/env python3
"""Phase-0 build identity: hash-pinned baselines for every disc-build input.

Roadmap: ObsidianVault/Playbooks/Game Solving Roadmap/Phase 0 - Stabilize and
Establish Identity.md. The hash-verified pristine retail image is the sole build
base; ALLMODS and every other MOD image are read-only historical evidence.

This module owns `tools/build_baselines.json`:
  * `staged_inputs`  — sha256 of EVERY file under REBUILD/files (the actual bytes
    mod/build.py patches and stages into mkpsxiso). A staged input that does not
    match its pin means the staging tree is contaminated (e.g. a failed restore
    left a patched file behind) and the build must not proceed.
  * `pristine_media` — the retail .bin/.cue pins, duplicated from
    tools/disc_provenance.json (Redump-verified) so one file answers "what may a
    build read and what must it never overwrite".
  * `read_only_evidence` — last-known-good MOD artifacts (ALLMODS et al.) kept
    ONLY for historical regression comparison. Never a build base, never an
    overwrite target.

Usage:
    python3 tools/build_identity.py --write            # (re)baseline staged inputs
    python3 tools/build_identity.py --verify           # verify all staged inputs
    python3 tools/build_identity.py --verify SCUS_942.88 LEVEL01/LEVEL.DAT
Library (used by mod/build.py):
    load_baselines() / verify_staged_input(rel, data) / protected_output(path)

Exit code 0 = verified; 1 = mismatch/missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "tools" / "build_baselines.json"
PROVENANCE = ROOT / "tools" / "disc_provenance.json"
REBUILD_FILES = ROOT / "REBUILD" / "files"

# Last-known-good MOD artifacts retained as read-only comparison evidence.
# Repo-relative; missing entries are recorded as absent, never fatal.
EVIDENCE_ARTIFACTS = {
    "build/ABL_ALLMODS.bin": "last-known-good consolidated ALLMODS disc",
    "build/ABL_ALLMODS.cue": "cue for the last-known-good ALLMODS disc",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def verify_pristine_media_path(path: Path | str,
                               baselines: dict | None = None) -> dict:
    """Hash-verify the media path DuckStation reports as actually mounted.

    A serial is not media identity: ALLMODS and every derivative retain SCUS-94288.
    For a cue sheet, verify both the cue bytes and every referenced track against
    ``pristine_media``. Directly mounted images are verified as one pinned file.
    Raises ``SystemExit`` on any absent, unpinned, or mismatched file.
    """
    b = baselines or load_baselines()
    pins = b.get("pristine_media") or {}
    mounted = Path(path).expanduser().resolve()
    if not mounted.is_file():
        raise SystemExit(f"MOUNTED-MEDIA GUARD: reported media path is absent: {mounted}")

    files = [mounted]
    if mounted.suffix.lower() == ".cue":
        refs = []
        file_re = re.compile(r'^\s*FILE\s+(?:"([^"]+)"|(\S+))\s+', re.IGNORECASE)
        for line in mounted.read_text(errors="replace").splitlines():
            match = file_re.match(line)
            if match:
                ref = match.group(1) or match.group(2)
                track = Path(ref)
                refs.append((track if track.is_absolute() else mounted.parent / track).resolve())
        if not refs:
            raise SystemExit(f"MOUNTED-MEDIA GUARD: cue names no track files: {mounted}")
        files.extend(refs)

    verified = {}
    for media_file in files:
        if not media_file.is_file():
            raise SystemExit(
                f"MOUNTED-MEDIA GUARD: mounted media component is absent: {media_file}")
        pin = pins.get(media_file.name)
        if not pin or not pin.get("sha1"):
            raise SystemExit(
                f"MOUNTED-MEDIA GUARD: mounted media component is not pristine-pinned: "
                f"{media_file.name}")
        actual = sha1_file(media_file)
        expected = pin["sha1"].lower()
        if actual != expected:
            raise SystemExit(
                f"MOUNTED-MEDIA GUARD: {media_file} does not match the pristine pin.\n"
                f"  pinned {expected}\n  actual {actual}\n"
                "A matching serial is insufficient; refuse MOD/derivative media.")
        verified[media_file.name] = {
            "path": str(media_file),
            "actual_sha1": actual,
            "expected_sha1": expected,
            "matches_pin": True,
        }

    return {
        "mounted_path": str(mounted),
        "pin_source": "tools/build_baselines.json",
        "pristine_verified": True,
        "files": verified,
    }


def load_baselines() -> dict:
    if not BASELINES.exists():
        raise SystemExit(
            f"build baselines missing: {BASELINES} — generate with "
            "`python3 tools/build_identity.py --write` from a verified-pristine "
            "REBUILD/files tree (run tools/re_baseline.py --provenance first)")
    return json.loads(BASELINES.read_text())


def verify_staged_input(rel: str, data: bytes, baselines: dict | None = None) -> None:
    """Assert `data` (the bytes about to be used as a build input for
    REBUILD/files/<rel>) matches the pinned pristine hash. Raises SystemExit."""
    b = baselines or load_baselines()
    pin = b["staged_inputs"].get(rel)
    if pin is None:
        raise SystemExit(
            f"staged input not pinned in {BASELINES.name}: {rel} — a build may only "
            "read pinned pristine inputs. If this file legitimately belongs to the "
            "pristine extraction, re-baseline with tools/build_identity.py --write "
            "after verifying provenance.")
    got = hashlib.sha256(data).hexdigest()
    if got != pin["sha256"]:
        raise SystemExit(
            f"PRISTINE-INPUT GUARD: REBUILD/files/{rel} does not match its pinned "
            f"pristine sha256.\n  pinned {pin['sha256']}\n  actual {got}\n"
            "The staging tree is contaminated (failed restore, manual edit, or a MOD "
            "image was used as a source). Restore this file from the pristine disc "
            "(dumpsxiso of the hash-verified retail image) before building. NEVER "
            "patch ALLMODS or any prior derivative.")


def verify_tree(baselines: dict | None = None) -> None:
    """Assert the ENTIRE staging tree matches its pins (every pinned file present
    and byte-identical; no unpinned extras). mkpsxiso consumes all staged files,
    not only the ones a build patches, so contamination anywhere in the tree
    would enter the disc — this is the full-tree pre-build gate. Raises SystemExit."""
    b = baselines or load_baselines()
    pins = b["staged_inputs"]
    problems = []
    seen = set()
    for p in sorted(REBUILD_FILES.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(REBUILD_FILES)).replace("\\", "/")
        seen.add(rel)
        pin = pins.get(rel)
        if pin is None:
            problems.append(f"UNPINNED extra file in staging: {rel}")
            continue
        if p.stat().st_size != pin["size"] or sha256_file(p) != pin["sha256"]:
            problems.append(f"CONTAMINATED staged input: {rel}")
    for rel in pins:
        if rel not in seen:
            problems.append(f"MISSING pinned staged input: {rel}")
    if problems:
        detail = "\n  ".join(problems[:20])
        more = f"\n  … and {len(problems) - 20} more" if len(problems) > 20 else ""
        raise SystemExit(
            f"PRISTINE-TREE GUARD: staging tree does not match tools/build_baselines.json "
            f"({len(problems)} problem(s)):\n  {detail}{more}\n"
            "Restore the affected files from the pristine disc before building; "
            "diagnose with `python3 tools/build_identity.py --verify`.")


def protected_output(path: Path, baselines: dict | None = None) -> str | None:
    """Return a reason string if `path` must never be overwritten by a build."""
    b = baselines or load_baselines()
    try:
        resolved = path.resolve()
    except OSError:
        return None
    protected = {}
    for name in b.get("pristine_media", {}):
        protected[(ROOT / name).resolve()] = "the hash-verified PRISTINE retail image"
    for rel, meta in b.get("read_only_evidence", {}).items():
        protected[(ROOT / rel).resolve()] = f"read-only historical evidence ({meta['role']})"
    reason = protected.get(resolved)
    if reason:
        return f"{path} is {reason}; builds must write to a NEW output path"
    return None


def prove_tree_pristine_by_rebuild() -> None:
    """Mechanical proof the staging tree is pristine: mkpsxiso-rebuild the disc from
    REBUILD/abl.xml and require the result to reproduce the Redump-verified retail
    image byte-exactly (sha1). This is the gate that makes it impossible for
    --write to bless a contaminated tree. Raises SystemExit on any mismatch."""
    import subprocess
    import tempfile
    prov = json.loads(PROVENANCE.read_text())
    bin_name = next(n for n in prov["files"] if n.endswith(".bin"))
    want_sha1 = prov["files"][bin_name]["sha1"]
    mkpsxiso = Path(os.environ.get("ABL_MKPSXISO", "/usr/local/bin/mkpsxiso"))
    xml = ROOT / "REBUILD" / "abl.xml"
    if not mkpsxiso.exists():
        raise SystemExit(f"mkpsxiso not found at {mkpsxiso} (set ABL_MKPSXISO); "
                         "the rebuild proof is REQUIRED before pinning baselines")
    if not xml.exists():
        raise SystemExit(f"layout manifest missing: {xml}")
    with tempfile.TemporaryDirectory(prefix="abl-rebuild-proof-") as td:
        out_bin = Path(td) / "proof.bin"
        out_cue = Path(td) / "proof.cue"
        print("[build_identity] rebuild proof: mkpsxiso from REBUILD/abl.xml …")
        proc = subprocess.run([str(mkpsxiso), "-y", "-o", str(out_bin),
                               "-c", str(out_cue), str(xml)],
                              cwd=str(ROOT), text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            raise SystemExit(f"rebuild proof failed: mkpsxiso error\n{proc.stdout[-2000:]}")
        h = hashlib.sha1()
        with out_bin.open("rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        got = h.hexdigest()
    if got != want_sha1:
        raise SystemExit(
            f"REBUILD PROOF FAILED: staging tree does NOT reproduce the pristine retail "
            f"image (rebuilt sha1 {got}, Redump-verified {want_sha1}). The tree is "
            "contaminated — REFUSING to pin baselines. Restore the affected files from "
            "the pristine disc first (compare sectors to locate them).")
    print(f"[build_identity] rebuild proof PASS: staging tree reproduces the retail "
          f"image byte-exactly (sha1 {got})")


def write_baselines() -> dict:
    if not REBUILD_FILES.is_dir():
        raise SystemExit(f"staging tree missing: {REBUILD_FILES}")
    prov = json.loads(PROVENANCE.read_text())
    staged = {}
    for p in sorted(REBUILD_FILES.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(REBUILD_FILES)).replace("\\", "/")
            staged[rel] = {"sha256": sha256_file(p), "size": p.stat().st_size}
    evidence = {}
    for rel, role in EVIDENCE_ARTIFACTS.items():
        p = ROOT / rel
        if p.exists():
            evidence[rel] = {"sha256": sha256_file(p), "size": p.stat().st_size,
                             "role": role}
        else:
            evidence[rel] = {"sha256": None, "size": None, "role": role,
                             "note": "absent at baseline time"}
    doc = {
        "_comment": (
            "Phase-0 hash-pinned build baselines (hash METADATA only, no copyrighted "
            "bytes). staged_inputs = pristine sha256 of every REBUILD/files input; "
            "mod/build.py refuses to patch an input that does not match its pin. "
            "read_only_evidence = last-known-good MOD artifacts, comparison-only. "
            "Regenerate ONLY from a verified-pristine tree: run tools/re_baseline.py "
            "--provenance, then tools/build_identity.py --write."),
        "generated": date.today().isoformat(),
        "pristine_media": {
            name: meta for name, meta in prov["files"].items()
        },
        "provenance_ref": "tools/disc_provenance.json (Redump-verified; see "
                          "ObsidianVault/Canon/Systems/SYS_game_identity_and_provenance.md)",
        "staged_inputs": staged,
        "read_only_evidence": evidence,
    }
    BASELINES.write_text(json.dumps(doc, indent=2) + "\n")
    return doc


def verify_all(rels: list[str] | None = None) -> int:
    b = load_baselines()
    pins = b["staged_inputs"]
    targets = rels or sorted(pins)
    bad = 0
    for rel in targets:
        p = REBUILD_FILES / rel
        if rel not in pins:
            print(f"UNPINNED  {rel}")
            bad += 1
            continue
        if not p.exists():
            print(f"MISSING   {rel}")
            bad += 1
            continue
        got = sha256_file(p)
        if got != pins[rel]["sha256"]:
            print(f"MISMATCH  {rel}  pinned={pins[rel]['sha256'][:16]}… actual={got[:16]}…")
            bad += 1
    extra = [str(p.relative_to(REBUILD_FILES)).replace("\\", "/")
             for p in REBUILD_FILES.rglob("*") if p.is_file()] if rels is None else []
    for rel in extra:
        if rel not in pins:
            print(f"UNTRACKED {rel} (present in staging, not pinned)")
            bad += 1
    print(f"[build_identity] {'FAIL' if bad else 'PASS'}: "
          f"{len(targets) - bad}/{len(targets)} staged inputs match their pins"
          + (f", {bad} problem(s)" if bad else ""))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true",
                    help="(re)baseline staged inputs from the current REBUILD/files tree")
    ap.add_argument("--verify", nargs="*", metavar="REL",
                    help="verify staged inputs (all when no REL given)")
    args = ap.parse_args()
    if args.write:
        if os.environ.get("ABL_UNSAFE_SKIP_REBUILD_PROOF") == "1":
            print("[build_identity] WARNING: ABL_UNSAFE_SKIP_REBUILD_PROOF=1 — pinning "
                  "WITHOUT the byte-exact rebuild proof. A contaminated tree pinned now "
                  "poisons every future guard decision. Only for known-good emergencies.")
        else:
            prove_tree_pristine_by_rebuild()
        doc = write_baselines()
        n = len(doc["staged_inputs"])
        total = sum(m["size"] for m in doc["staged_inputs"].values())
        print(f"[build_identity] wrote {BASELINES.relative_to(ROOT)}: "
              f"{n} staged inputs pinned ({total} B), "
              f"{len(doc['read_only_evidence'])} evidence artifact(s)")
        return 0
    if args.verify is not None:
        return verify_all(args.verify or None)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
