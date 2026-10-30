#!/usr/bin/env python3
"""RE-basics baseline — ONE reproducible script for the project's static-analysis floor.

Regenerates, from the owner's legally dumped media, everything the "RE basics"
checklist needs, into an UNTRACKED output dir (extracted/re_baseline/ — covered by
the `extracted/*` gitignore). Derived listings of the copyrighted binary are NEVER
committed; only this script and the summary counts (report.json/report.md) are
quoted into the vault ([[Preservation Policy]]).

Stages (each skippable; --all runs everything):
  --provenance   hash disc/.cue/EXE and compare against tools/disc_provenance.json
  --exe          parse the PS-X EXE header -> exe_map.json (magic, entry, load, gp)
  --disasm       radare2 pass over SCUS_942.88: aaa -> functions.json (aflj),
                 strings.json (izzj), full listing SCUS_942.88.asm (pD)
  --overlays     r2 pass per OVL/*.BIN at Region-A base 0x800b39a0 (MEMORY.BIN at
                 Region-B 0x800b5788) -> overlays/<name>.functions.json + .asm
  --codemap      code-vs-data classification of the 0x72800 text image -> code_data_map.json
  --inventory    merge r2 functions + symbols/re_symbols.sym (+ ghidra_functions.csv
                 and psyq_matches.csv when present) -> function_inventory.csv
  --report       report.json + report.md summary (the only vault-quotable artifact)

Recipes baked in (docs/TOOLING.md, docs/EXECUTABLE_AND_OVERLAYS.md):
  r2 5.9.8, psxexe plugin auto-maps TEXT at 0x80010000 (entry 0x8005f690);
  anal.gp=0x80081d98; overlays are raw blobs mapped with -m <region base>.
"""
from __future__ import annotations

import argparse
import binascii
import csv
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import exe_read  # noqa: E402  (reused: LOAD_VA/HDR/TEXT_SIZE/DEFAULT_GP + disasm)

OUT = ROOT / "extracted" / "re_baseline"
MANIFEST = ROOT / "tools" / "disc_provenance.json"
REDUMP = ROOT / "tools" / "redump_expected.json"
SYMBOLS = ROOT / "symbols" / "re_symbols.sym"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
OVL_DIR = ROOT / "OVL"

REGION_A = 0x800B39A0  # LEVEL*.BIN code overlays (header word +0, code +4)
REGION_B = 0x800B5788  # bits\memory.bin, fmv\fmv.bin
BSS_START, BSS_END = 0x80082200, 0x800B399F  # cleared by startup (docs)

R2_ENV = ["-e", "asm.arch=mips", "-e", "asm.bits=32", "-e", "cfg.bigendian=false",
          "-e", f"anal.gp={exe_read.DEFAULT_GP:#x}", "-e", "scr.color=0",
          "-e", "anal.hasnext=true"]


def r2(cmds: str, target: Path, extra: list[str] | None = None) -> str:
    argv = ["r2", "-2", "-q"] + R2_ENV + (extra or []) + ["-c", cmds, str(target)]
    p = subprocess.run(argv, capture_output=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"r2 failed ({p.returncode}) on {target.name}: "
                           f"{p.stderr.decode('utf-8', 'replace')[:400]}")
    return p.stdout.decode("utf-8", "replace")


def _hash_file(path: Path, algos=("sha1",)) -> dict:
    hs = {a: hashlib.new(a) for a in algos if a != "crc32"}
    crc = 0 if "crc32" in algos else None
    size = 0
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            size += len(chunk)
            for h in hs.values():
                h.update(chunk)
            if crc is not None:
                crc = binascii.crc32(chunk, crc)
    out = {a: h.hexdigest() for a, h in hs.items()}
    if crc is not None:
        out["crc32"] = f"{crc & 0xffffffff:08x}"
    out["size"] = size
    return out


# ---------------------------------------------------------------- provenance
def _redump_check(man: dict) -> dict:
    """Compare the manifest identity against the published Redump datfile entry.

    Hash metadata only (tools/redump_expected.json). The .bin chain is
    file == manifest == Redump (the file==manifest leg is the per-file check
    above). The .cue differs from Redump's only by the embedded .bin filename,
    so when the local cue is present we re-verify the normalization: substitute
    Redump's rom name and the SHA-1 must reproduce Redump's cue hash exactly.
    """
    exp = json.loads(REDUMP.read_text())
    roms = {r["name"].rsplit(".", 1)[1]: r for r in exp["game"]["roms"]}
    bin_rec = man["files"]["Disney-Pixar A Bug's Life (v1.0).bin"]
    mism = {k: {"redump": roms["bin"][k], "manifest": bin_rec[k]}
            for k in ("size", "crc32", "md5", "sha1") if roms["bin"][k] != bin_rec[k]}
    verdict = {"datfile": exp["source"]["datfile"], "entry": exp["game"]["name"],
               "bin": "MATCH" if not mism else "MISMATCH",
               **({"bin_mismatches": mism} if mism else {})}
    cue_path = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
    if cue_path.exists():
        norm = cue_path.read_bytes().replace(
            b"Disney-Pixar A Bug's Life (v1.0).bin", roms["bin"]["name"].encode())
        got = hashlib.sha1(norm).hexdigest()
        verdict["cue"] = ("LAYOUT_MATCH (filename-normalized)" if got == roms["cue"]["sha1"]
                          else "MISMATCH")
        verdict["cue_normalized_sha1"] = got
    else:
        verdict["cue"] = "SKIPPED (cue not on this host)"
    verdict["pass"] = verdict["bin"] == "MATCH" and verdict["cue"] != "MISMATCH"
    return verdict


def stage_provenance() -> dict:
    man = json.loads(MANIFEST.read_text())
    results, ok = {}, True
    algo_map = {
        "Disney-Pixar A Bug's Life (v1.0).bin": ("sha1", "md5", "crc32"),
        "Disney-Pixar A Bug's Life (v1.0).cue": ("sha1",),
        "SCUS_942.88": ("sha1", "md5"),
    }
    for name, algos in algo_map.items():
        path = ROOT / name
        rec = man["files"][name]
        if not path.exists():
            results[name] = {"status": "ABSENT"}
            ok = False
            continue
        got = _hash_file(path, algos)
        mism = {k: {"expected": rec[k], "got": got[k]}
                for k in (*algos, *(["size"] if "size" in rec else []))
                if str(rec.get(k)) != str(got.get(k))}
        results[name] = {"status": "PASS" if not mism else "FAIL", **({"mismatches": mism} if mism else {})}
        ok = ok and not mism
    redump = _redump_check(man) if REDUMP.exists() else {"pass": None, "bin": "SKIPPED (no redump_expected.json)"}
    ok = ok and redump["pass"] is not False
    verdict = {"stage": "provenance", "pass": ok, "policy": man["provenance_policy"],
               "files": results, "redump": redump}
    (OUT / "provenance.json").write_text(json.dumps(verdict, indent=2))
    print(f"[provenance] {'PASS' if ok else 'FAIL'}: " +
          ", ".join(f"{n}={r['status']}" for n, r in results.items()) +
          f", redump bin={redump['bin']} cue={redump.get('cue', 'n/a')}")
    return verdict


# ------------------------------------------------------------------- exe map
def stage_exe() -> dict:
    data = EXE.read_bytes()
    magic = data[:8].decode("ascii", "replace")
    pc, gp0, load_va, text_size = struct.unpack_from("<IIII", data, 0x10)
    sp = struct.unpack_from("<I", data, 0x30)[0]
    assert magic == "PS-X EXE", f"bad magic {magic!r}"
    assert load_va == exe_read.LOAD_VA and text_size == exe_read.TEXT_SIZE, "load map drift vs exe_read.py"
    assert exe_read.HDR + text_size == len(data), "header+text != file size"
    m = {
        "stage": "exe",
        "format": "PS-X EXE",
        "platform": "Sony PlayStation (PS1)",
        "cpu": "MIPS R3000A, little-endian, 32-bit",
        "file": EXE.name,
        "file_size": len(data),
        "header_size": exe_read.HDR,
        "load_va": f"{load_va:#010x}",
        "text_size": f"{text_size:#x}",
        "text_end_va": f"{load_va + text_size:#010x}",
        "entry_pc": f"{pc:#010x}",
        "header_gp": f"{gp0:#010x}",
        "runtime_gp": f"{exe_read.DEFAULT_GP:#010x}",
        "initial_sp": f"{sp:#010x}",
        "bss_clear": f"{BSS_START:#010x}-{BSS_END:#010x}",
        "va_to_file_offset": "offset = (va - 0x80010000) + 0x800",
    }
    (OUT / "exe_map.json").write_text(json.dumps(m, indent=2))
    print(f"[exe] {magic} load={m['load_va']} size={m['text_size']} entry={m['entry_pc']} sp={m['initial_sp']}")
    return m


# ------------------------------------------------------------------- disasm
def stage_disasm() -> dict:
    print("[disasm] r2 aaa on SCUS_942.88 …")
    funcs = json.loads(r2("aaa 2>/dev/null; aflj", EXE) or "[]")
    (OUT / "functions.json").write_text(json.dumps(funcs, indent=2))
    strings = json.loads(r2("izzj", EXE) or "[]")
    (OUT / "strings.json").write_text(json.dumps(strings, indent=2))
    listing = r2(f"e asm.flags=false; aaa 2>/dev/null; pD {exe_read.TEXT_SIZE:#x} @ {exe_read.LOAD_VA:#x}", EXE)
    (OUT / "SCUS_942.88.asm").write_text(listing)
    summary = {"stage": "disasm", "functions": len(funcs), "strings": len(strings),
               "listing_lines": listing.count("\n")}
    print(f"[disasm] {summary['functions']} functions, {summary['strings']} strings, "
          f"{summary['listing_lines']} listing lines")
    return summary


# ----------------------------------------------------------------- overlays
def stage_overlays() -> dict:
    odir = OUT / "overlays"
    odir.mkdir(exist_ok=True)
    targets = sorted(OVL_DIR.glob("LEVEL*.BIN")) if OVL_DIR.exists() else []
    mem = ROOT / "MEMORY.BIN"
    per = {}
    for path in targets + ([mem] if mem.exists() else []):
        base = REGION_B if path.name == "MEMORY.BIN" else REGION_A
        size = path.stat().st_size
        if size < 16:  # some LEVEL1.BIN stubs are 4 bytes
            per[path.name] = {"base": f"{base:#x}", "size": size, "functions": 0, "note": "stub, skipped"}
            continue
        extra = ["-n", "-m", f"{base:#x}"]
        funcs = json.loads(r2("aaa 2>/dev/null; aflj", path, extra) or "[]")
        (odir / f"{path.stem}.functions.json").write_text(json.dumps(funcs, indent=2))
        (odir / f"{path.stem}.asm").write_text(
            r2(f"e asm.flags=false; aaa 2>/dev/null; pD {size} @ {base:#x}", path, extra))
        per[path.name] = {"base": f"{base:#x}", "size": size, "functions": len(funcs)}
        print(f"[overlays] {path.name}: base={base:#x} size={size} functions={len(funcs)}")
    summary = {"stage": "overlays", "count": len(per), "per_overlay": per}
    (OUT / "overlays.json").write_text(json.dumps(summary, indent=2))
    return summary


# ------------------------------------------------------------------ codemap
def stage_codemap() -> dict:
    funcs = json.loads((OUT / "functions.json").read_text())
    strings = json.loads((OUT / "strings.json").read_text())
    text_lo, text_hi = exe_read.LOAD_VA, exe_read.LOAD_VA + exe_read.TEXT_SIZE
    total = exe_read.TEXT_SIZE

    code = sorted((f["offset"], f["offset"] + (f.get("realsz") or f.get("size") or 0))
                  for f in funcs if text_lo <= f["offset"] < text_hi)
    merged, code_bytes = [], 0
    for lo, hi in code:
        hi = min(hi, text_hi)
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    code_bytes = sum(hi - lo for lo, hi in merged)
    last_code = max((hi for _, hi in merged), default=text_lo)

    str_bytes = sum(s.get("size", 0) for s in strings
                    if text_lo <= s.get("vaddr", 0) < text_hi)

    m = {
        "stage": "codemap",
        "image": {"start": f"{text_lo:#010x}", "end": f"{text_hi:#010x}", "bytes": total},
        "code": {"bytes": code_bytes, "pct": round(100 * code_bytes / total, 1),
                 "regions": len(merged), "last_function_end": f"{last_code:#010x}"},
        "string_data": {"bytes": str_bytes, "pct": round(100 * str_bytes / total, 1)},
        "unclassified": {"bytes": total - code_bytes - str_bytes,
                         "pct": round(100 * (total - code_bytes - str_bytes) / total, 1)},
        "known_data_anchors": {
            "berry_throw_jump_table": "0x8001b1c0",
            "mover_vm_opcode_table_ptr": "0x8001b2f4",
            "runtime_gp_window": f"{exe_read.DEFAULT_GP - 0x8000:#010x}-{exe_read.DEFAULT_GP + 0x7fff:#010x}",
            "psyq_copyright_string": "0x8007fd00",
        },
        "bss": {"start": f"{BSS_START:#010x}", "end": f"{BSS_END:#010x}",
                "bytes": BSS_END + 1 - BSS_START, "note": "zero-cleared at startup, not in file"},
        "note": "code = union of r2 function ranges; string_data = izz hits in image; "
                "separation is a lower bound (jump tables/rodata beyond strings unclassified).",
    }
    (OUT / "code_data_map.json").write_text(json.dumps(m, indent=2))
    print(f"[codemap] code {m['code']['pct']}% + strings {m['string_data']['pct']}% "
          f"of image classified; last function ends {m['code']['last_function_end']}")
    return m


# ---------------------------------------------------------------- inventory
def _load_symbols() -> dict[int, str]:
    out = {}
    for ln in SYMBOLS.read_text().splitlines():
        mo = re.match(r"^([0-9A-Fa-f]{8})\s+(\S+)", ln)
        if mo:
            out[int(mo.group(1), 16)] = mo.group(2)
    return out


def stage_inventory() -> dict:
    funcs = {f["offset"]: f for f in json.loads((OUT / "functions.json").read_text())}
    syms = _load_symbols()
    ghidra_csv = OUT / "ghidra_functions.csv"
    psyq_csv = OUT / "psyq_matches.csv"
    ghidra = {}
    if ghidra_csv.exists():
        with ghidra_csv.open() as f:
            ghidra = {int(r["address"], 16): r["name"] for r in csv.DictReader(f)}
    psyq = {}
    if psyq_csv.exists():
        with psyq_csv.open() as f:
            psyq = {int(r["address"], 16): r["name"] for r in csv.DictReader(f)}

    text_lo, text_hi = exe_read.LOAD_VA, exe_read.LOAD_VA + exe_read.TEXT_SIZE
    in_text = lambda d: {a for a in d if text_lo <= a < text_hi}
    ghidra, psyq = ({a: v[a] for a in in_text(v)} for v in (ghidra, psyq))
    addrs = sorted(set(funcs) | in_text(syms) | set(ghidra) | set(psyq))
    rows, named = [], 0
    for a in addrs:
        sources = [s for s, present in (("r2", a in funcs), ("sym", a in syms),
                                        ("ghidra", a in ghidra), ("psyq", a in psyq)) if present]
        name = syms.get(a) or psyq.get(a) or ghidra.get(a) or funcs.get(a, {}).get("name", "")
        is_named = bool(syms.get(a) or psyq.get(a)) and not str(name).startswith(("FUNC_", "fcn."))
        named += is_named
        rows.append({"address": f"{a:#010x}", "name": name,
                     "size": funcs.get(a, {}).get("realsz", ""),
                     "sources": "+".join(sources), "named": str(is_named).lower()})
    with (OUT / "function_inventory.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["address", "name", "size", "sources", "named"])
        w.writeheader()
        w.writerows(rows)
    summary = {"stage": "inventory", "total": len(rows), "named": named,
               "r2_only": sum(1 for r in rows if r["sources"] == "r2"),
               "sym_entries_in_text": sum(1 for r in rows if "sym" in r["sources"]),
               "ghidra": len(ghidra), "psyq_matches": len(psyq)}
    print(f"[inventory] {summary['total']} function addresses "
          f"({named} named, {len(psyq)} PsyQ matches, {len(ghidra)} ghidra)")
    return summary


# ------------------------------------------------------------------- report
def stage_report(stages: dict) -> None:
    report = {"generated_by": "tools/re_baseline.py", "stages": stages}
    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    lines = ["# RE baseline report", "",
             "Regenerable via `python tools/re_baseline.py --all`. Untracked; summary counts only.", ""]
    for name, s in stages.items():
        lines.append(f"## {name}")
        lines.append("```json")
        lines.append(json.dumps({k: v for k, v in s.items() if k not in ("per_overlay", "files")},
                                indent=2))
        lines.append("```")
        lines.append("")
    (OUT / "report.md").write_text("\n".join(lines))
    print(f"[report] {OUT / 'report.json'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for s in ("provenance", "exe", "disasm", "overlays", "codemap", "inventory", "report"):
        ap.add_argument(f"--{s}", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    picked = [s for s in ("provenance", "exe", "disasm", "overlays", "codemap", "inventory", "report")
              if a.all or getattr(a, s)]
    if not picked:
        ap.print_help()
        return 1
    stages: dict = {}
    fail = False
    for s in picked:
        if s == "report":
            stage_report(stages)
            continue
        res = globals()[f"stage_{s}"]()
        stages[s] = res
        fail = fail or (res.get("pass") is False)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
