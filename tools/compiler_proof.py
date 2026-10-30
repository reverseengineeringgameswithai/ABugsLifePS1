#!/usr/bin/env python3
"""Compiler/flag matrix runner for the decomp substrate C path (docs/SUBSTRATE.md).

Sweeps a grid of (era compiler, cc1 flags, maspsx args) for one candidate C
function, byte-compares each build against the original bytes, and records
EVERY attempt (match or miss) to analysis/compiler_attempts.json so no
combination is ever retested blind. On the first match it prints the winning
row (use --grid to sweep the whole matrix regardless).

  python tools/compiler_proof.py --function 80061d04 --source src/main/80061d04_SetPolyGT4.c
  python tools/compiler_proof.py --function 80061d04 --source ... --grid

The winning row's (compiler, cc1_flags, maspsx_args) is what belongs in the
`c_toolchain:` block of config/segments.yml.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from substrate_common import (BUILD, HANDWRITTEN, ROOT, compile_at,  # noqa: E402
                              c_toolchain_available, load_segments,
                              load_declaration_profiles, load_toolchain_manifest,
                              original_exe, resolve_declaration_profile, va_to_off)

ATTEMPTS = ROOT / "analysis" / "compiler_attempts.json"

# Default matrix. Compilers come from the toolchain manifest (primary first).
OPT_FLAGS = [["-O2"], ["-O1"], ["-O0"], ["-O3"]]
G_FLAGS = [["-G0"], ["-G8"]]
FIXED = ["-mcpu=3000"]
MASPSX_VARIANTS = [
    ["--dont-expand-li", "--expand-div"],
    ["--dont-expand-li"],
    [],
    ["--expand-li"],
]


def _load_attempts() -> list[dict]:
    if ATTEMPTS.exists():
        return json.loads(ATTEMPTS.read_text()).get("attempts", [])
    return []


def _key(a: dict) -> tuple:
    return (a["function"], a.get("source_sha256", "legacy"),
            a.get("declaration_profile", "source"), a["compiler_id"],
            tuple(a["cc1_flags"]), tuple(a["maspsx_args"]))


def _diff(orig: bytes, new: bytes) -> tuple[int, int | None]:
    n = max(len(orig), len(new))
    diffs, first = 0, None
    for off in range(0, n, 4):
        if orig[off:off + 4] != new[off:off + 4]:
            diffs += 1
            if first is None:
                first = off
    return diffs, first


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--function", required=True, help="start VA (hex, e.g. 80061d04)")
    ap.add_argument("--source", required=True, help="candidate C source (repo-relative)")
    ap.add_argument("--grid", action="store_true", help="sweep whole matrix (don't stop at first match)")
    ap.add_argument("--compilers", help="comma list of compiler ids (default: all in manifest)")
    ap.add_argument("--extern", action="append", default=[],
                    help="global resolved at link, name=0xADDR (repeatable)")
    ap.add_argument("--profiles",
                    help="comma-separated declaration profiles (default: entry profile/source)")
    ap.add_argument("--all-profiles", action="store_true",
                    help="sweep every configured declaration profile")
    ap.add_argument("--small-data", action="store_true",
                    help="force the PSYQ -G8/$gp path for an unregistered candidate")
    args = ap.parse_args()

    seg = load_segments()
    va = int(args.function, 16)
    entry = next((a for a in seg["attempted"] if a["start"] == va), None)
    externs = dict(kv.split("=", 1) for kv in args.extern)
    if entry is not None and entry.get("externs"):
        externs = {**entry["externs"], **externs}
    # extent from segments if registered, else from census
    if entry is not None:
        end = entry["end"]
    else:
        census = json.loads((ROOT / "analysis" / "functions.json").read_text())
        rec = next((r for r in census["functions"]
                    if r["space"] == "resident" and int(r["start"], 16) == va), None)
        if rec is None:
            raise SystemExit(f"{va:#x} is not a census function start")
        end = int(rec["end"], 16)
    want = end - va
    src = ROOT / args.source
    src_sha = hashlib.sha256(src.read_bytes()).hexdigest()

    man = load_toolchain_manifest()
    compilers = (args.compilers.split(",") if args.compilers
                 else [c["id"] for c in man["compilers"]])

    exe = original_exe(seg)
    orig = exe[va_to_off(seg, va):va_to_off(seg, va) + want]
    section_layout = entry.get("sections") if entry else None
    original_sections = None
    if section_layout:
        original_sections = {
            name: exe[va_to_off(seg, section["start"]):va_to_off(seg, section["end"])]
            for name, section in section_layout.items()
        }

    # substrate v2: gp-relative entries opt in via `small_data: true`; the gp path
    # forces -G8 on both cc1 and the assemble tail and defines _gp.
    small_data = args.small_data or bool(entry and entry.get("small_data"))
    gp = seg.get("gp")
    if isinstance(gp, str):
        gp = int(gp, 16)

    attempts = {_key(a): a for a in _load_attempts()}
    profile_doc = load_declaration_profiles()
    if args.all_profiles:
        profile_names = list(profile_doc["profiles"])
    elif args.profiles:
        profile_names = args.profiles.split(",")
    else:
        profile_names = [(entry or {}).get("declaration_profile", profile_doc["default"])]
    grid = list(itertools.product(profile_names, compilers, OPT_FLAGS, G_FLAGS,
                                  MASPSX_VARIANTS))
    winner = None
    for profile_name, cid, opt, g, maspsx in grid:
        if not c_toolchain_available(cid):
            print(f"[proof] skip {cid}: toolchain absent")
            continue
        cc1_flags = [*opt, *g, *FIXED]
        try:
            profile = resolve_declaration_profile(profile_name)
        except Exception as e:  # missing external oracle is a profile error, not a crash
            row = {"function": f"{va:#010x}", "source_sha256": src_sha,
                   "declaration_profile": profile_name, "declaration_evidence": {},
                   "compiler_id": cid, "cc1_flags": cc1_flags, "maspsx_args": maspsx,
                   "result": "error", "differing_words": None,
                   "first_mismatch_va": None, "note": str(e)[:200]}
            attempts[_key(row)] = row
            continue
        try:
            new = compile_at(src, va, compiler_id=cid, cc1_flags=cc1_flags,
                             maspsx_args=maspsx,
                             include_dirs=[BUILD, HANDWRITTEN, *profile["include_dirs"]],
                             externs=externs, small_data=small_data, gp=gp,
                             cpp_args=profile["cpp_args"], section_layout=section_layout)
        except Exception as e:  # noqa: BLE001 — a failed build is a recorded miss
            row = {"function": f"{va:#010x}", "source_sha256": src_sha,
                   "declaration_profile": profile_name,
                   "declaration_evidence": profile["evidence"],
                   "compiler_id": cid, "cc1_flags": cc1_flags, "maspsx_args": maspsx,
                   "result": "error", "differing_words": None,
                   "first_mismatch_va": None, "note": str(e).splitlines()[-1][:200]}
            attempts[_key(row)] = row
            continue
        if isinstance(new, dict):
            size_ok = all(len(new.get(name, b"")) == len(data)
                          for name, data in original_sections.items())
            section_diffs = {name: _diff(data, new.get(name, b""))
                             for name, data in original_sections.items()}
            diffs = sum(v[0] for v in section_diffs.values())
            first_vas = [section_layout[name]["start"] + first
                         for name, (_, first) in section_diffs.items() if first is not None]
            first_va = min(first_vas) if first_vas else None
            first = None
        else:
            size_ok = len(new) == want
            diffs, first = _diff(orig, new)
            first_va = va + first if first is not None else None
        match = size_ok and diffs == 0
        row = {"function": f"{va:#010x}", "source_sha256": src_sha,
               "declaration_profile": profile_name,
               "declaration_evidence": profile["evidence"],
               "compiler_id": cid, "cc1_flags": cc1_flags, "maspsx_args": maspsx,
               "result": "match" if match else "mismatch",
               "differing_words": diffs,
               "first_mismatch_va": (f"{first_va:#010x}" if first_va is not None else None),
               "note": "" if size_ok else "compiled section size differs from layout"}
        attempts[_key(row)] = row
        tag = "MATCH" if match else f"mismatch({diffs}w)"
        print(f"[proof] {profile_name} {cid} {' '.join(cc1_flags)} "
              f"maspsx={maspsx or '[]'} -> {tag}")
        if match and winner is None:
            winner = row
            if not args.grid:
                break

    ATTEMPTS.parent.mkdir(exist_ok=True)
    rows = sorted(attempts.values(),
                  key=lambda a: (a["function"], a.get("declaration_profile", "source"),
                                 a["compiler_id"],
                                 " ".join(a["cc1_flags"]), " ".join(a["maspsx_args"])))
    ATTEMPTS.write_text(json.dumps(
        {"generated_by": "tools/compiler_proof.py", "attempts": rows}, indent=1) + "\n")

    if winner:
        print(f"\n[proof] WINNER for {va:#010x}: profile={winner['declaration_profile']} "
              f"compiler={winner['compiler_id']} "
              f"cc1_flags={winner['cc1_flags']} maspsx_args={winner['maspsx_args']}")
        print("[proof] pin this in config/segments.yml c_toolchain (if not already).")
        return 0
    print(f"\n[proof] NO MATCH for {va:#010x} across {len(grid)} combos "
          f"({len([a for a in attempts.values() if a['function']==f'{va:#010x}'])} recorded).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
