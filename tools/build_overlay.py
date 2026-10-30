#!/usr/bin/env python3
"""Overlay decompilation track — byte-splat build + validate pristine overlays.

SEPARATE from the resident substrate (tools/build_psx_exe.py). Each overlay is a
standalone image CdRead-loaded at a fixed VA (config/overlays.yml region_a/b).
Matched overlay functions are compiled at their load VA (VA = base + file_offset)
via the shared substrate pipeline and spliced into a copy of the blob; the rebuilt
blob must be SHA-1-identical to the original.

Owner-supplied media is read from the hash-pinned ``REBUILD/files`` pristine
staging tree, so this is local_media-gated (like the resident EXE).  The old
``OVL/*.BIN`` extraction copies are deliberately not inputs: a clean checkout
must not need two independently provisioned paths for identical retail bytes.
Writes analysis/overlay_decomp_progress.json; the resident metric
(``analysis/decomp_progress.json``) is never touched here.

  python tools/build_overlay.py                # build+validate every listed overlay
  python tools/build_overlay.py LEVEL02_LEVEL  # one overlay
  python tools/build_overlay.py --progress     # (re)write the overlay metric only
  python tools/build_overlay.py --candidates [OVERLAY]   # rank easy unmatched fns
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from substrate_common import BUILD, HANDWRITTEN, build_entry, load_segments  # noqa: E402

# COP2/GTE and syscall words can't be emitted from C — exclude, like the resident
# ranker's excluded classes (tools/decomp_candidates.py).
_HARD_OPS = {0x12, 0x3a, 0x32, 0x3e}

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "overlays.yml"
CENSUS = ROOT / "analysis" / "functions.json"
PROGRESS = ROOT / "analysis" / "overlay_decomp_progress.json"


def _sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def _overlay_seg(man: dict) -> dict:
    """A seg-like dict so substrate_common.build_entry reuses the resident
    c_toolchain + _gp (overlays share the resident $gp)."""
    seg = load_segments()
    return {"c_toolchain": seg["c_toolchain"], "gp": man.get("gp", seg.get("gp"))}


def _census_overlay_totals() -> dict:
    fns = json.loads(CENSUS.read_text())["functions"]
    ov = [r for r in fns if r.get("space") == "overlay" and r.get("range_type") == "code"]
    per: dict[str, int] = {}
    for r in ov:
        per[r["overlay"]] = per.get(r["overlay"], 0) + 1
    return {"code_functions": len(ov), "per_overlay": per}


def build_overlay(name: str, ov: dict, seg: dict) -> dict:
    blob_path = ROOT / ov["blob"]
    if not blob_path.exists():
        raise SystemExit(f"overlay blob missing (local_media): {blob_path}")
    blob = bytearray(blob_path.read_bytes())
    orig_sha = _sha1(bytes(blob))
    if ov.get("sha1") and orig_sha != ov["sha1"]:
        raise SystemExit(f"{name}: blob sha1 {orig_sha} != manifest {ov['sha1']}")
    base = ov["base"] if isinstance(ov["base"], int) else int(ov["base"], 16)
    matched = []
    for a in ov.get("attempted") or []:
        start = a["start"] if isinstance(a["start"], int) else int(a["start"], 16)
        end = a["end"] if isinstance(a["end"], int) else int(a["end"], 16)
        want = end - start
        off = start - base
        if off < 0 or off + want > len(blob):
            raise SystemExit(f"{name}: {start:#x} maps outside the blob (off {off:#x})")
        data = build_entry(a, seg, include_dirs=[BUILD, HANDWRITTEN])
        if len(data) != want:
            raise SystemExit(f"{name}: {a['source']} built {len(data)} B, range is {want}")
        ok = bytes(blob[off:off + want]) == data
        blob[off:off + want] = data
        print(f"[overlay] {name} {a['source']} @ {start:#x} ({want} B) "
              f"{'MATCH' if ok else 'DIFFERS'}")
        matched.append({"start": f"{start:#010x}", "bytes": want,
                        "source": a["source"], "matched": ok})
    rebuilt_sha = _sha1(bytes(blob))
    passed = rebuilt_sha == orig_sha
    print(f"[overlay] {name}: rebuilt sha1={rebuilt_sha} "
          f"{'PASS' if passed else 'FAIL (blob changed)'}")
    return {"overlay": name, "blob": ov["blob"], "base": f"{base:#010x}",
            "sha1": orig_sha, "rebuilt_sha1": rebuilt_sha, "validated": passed,
            "matched_functions": sum(1 for m in matched if m["matched"]),
            "attempted": matched}


def write_progress(results: list[dict]) -> None:
    totals = _census_overlay_totals()
    matched = sum(r["matched_functions"] for r in results)
    PROGRESS.write_text(json.dumps({
        "generated_by": "tools/build_overlay.py",
        "note": "Overlay track is SEPARATE from resident (analysis/decomp_progress.json).",
        "overlay_code_functions": totals["code_functions"],
        "matched": {"functions": matched,
                    "pct_functions": round(100 * matched / totals["code_functions"], 2)
                    if totals["code_functions"] else 0.0},
        "per_overlay_totals": totals["per_overlay"],
        "results": results,
    }, indent=1) + "\n")
    print(f"[overlay] wrote {PROGRESS.relative_to(ROOT)}: "
          f"{matched}/{totals['code_functions']} overlay code functions matched")


def rank_candidates(man: dict, pick: str | None) -> None:
    """Separate overlay ranker (mirrors tools/decomp_candidates.py exclusions but
    over blob bytes): small, complete (ends in `jr ra`), no cop2/GTE/syscall, and
    not already in the manifest. Cheap leaves first."""
    fns = json.loads(CENSUS.read_text())["functions"]
    matched = {(name, int(a["start"], 16) if isinstance(a["start"], str) else a["start"])
               for name, ov in (man.get("overlays") or {}).items()
               for a in (ov.get("attempted") or [])}
    rows = []
    for r in fns:
        if r.get("space") != "overlay" or r.get("range_type") != "code":
            continue
        stem = r["overlay"]
        if pick and stem != pick:
            continue
        base = man["region_b"] if stem == "MEMORY" else man["region_a"]
        base = base if isinstance(base, int) else int(base, 16)
        declared = (man.get("overlays") or {}).get(stem)
        if not declared:
            continue
        blob_path = ROOT / declared["blob"]
        if not blob_path.exists():
            continue
        blob = blob_path.read_bytes()
        va, sz = int(r["start"], 16), r["size"]
        off = va - base
        if off < 0 or off + sz > len(blob) or sz > 0x60:
            continue
        ws = [struct.unpack("<I", blob[off + i:off + i + 4])[0] for i in range(0, sz, 4)]
        if not any(w == 0x03e00008 for w in ws):        # must return (jr ra)
            continue
        if any((w >> 26) in _HARD_OPS or w == 0xc for w in ws):
            continue
        if (stem, va) in matched:
            continue
        rows.append((sz, va, stem, r["classification"], r.get("name") or ""))
    rows.sort()
    print(f"[overlay-candidates] {len(rows)} easy unmatched overlay leaves"
          + (f" in {pick}" if pick else ""))
    for sz, va, stem, cls, nm in rows[:30]:
        print(f"  {va:#010x} {sz:>3}B {stem:<16} {cls:<7} {nm}")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    progress_only = "--progress" in sys.argv[1:]
    man = yaml.safe_load(MANIFEST.read_text())
    if "--candidates" in sys.argv[1:]:
        rank_candidates(man, args[0] if args else None)
        return 0
    seg = _overlay_seg(man)
    overlays = man.get("overlays") or {}
    pick = args[0] if args else None
    results = []
    for name, ov in overlays.items():
        if pick and name != pick:
            continue
        if progress_only:
            # metric without rebuilding (assume prior validation)
            results.append({"overlay": name, "matched_functions": len(ov.get("attempted") or [])})
            continue
        results.append(build_overlay(name, ov, seg))
    if not results:
        raise SystemExit(f"no overlay matched '{pick}'" if pick else "no overlays in manifest")
    if not progress_only and any(not r["validated"] for r in results):
        write_progress(results)
        raise SystemExit("[overlay] validation FAILED — see DIFFERS above")
    write_progress(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
