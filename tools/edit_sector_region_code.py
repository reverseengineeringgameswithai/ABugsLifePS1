#!/usr/bin/env python3
"""Edit the per-sector REGION CODE in A Bug's Life LEVEL.RAW chunk 32 (§10 level-exit trigger).

Each collision sector source record (chunk-32 local 0x36570, stride 0x4c — same array as
`edit_collision_sector.py`) carries a REGION CODE at **+0x2c (word)**. The converter
FUNC_80030F60 copies it into the runtime sector table (0x800A7E48, stride 0x30) at **+0x2e**,
where `FUNC_80038f38` reads it and `FUNC_80048138` dispatches on it:

    code 1 -> type-2 transition initiator (FUNC_8004A700)
    code 2 -> type-1 LEVEL EXIT  (sets transition lever [0x800823a0]=1)   <-- the end-of-stage trigger
    (0 = no trigger; other codes = other transition kinds used by other levels)

So "where the level ends" = whichever sector(s) carry code 2. In LEVEL01 (pristine) that is
exactly sector 177. This tool lists those codes and lets you SET / CLEAR / MOVE them, then
recompresses ONLY chunk 32 (proven codec; ~1.3x balloon) and splices a new LEVEL.RAW. Because
chunk 32 grows, rebuild the disc with the AUTO-LAYOUT manifest (`tools/build_autolayout_disc.py`),
not the fixed-LBA path.

RE: src_re/level_exit_trigger.c · ObsidianVault `Gameplay - Warp and Level Transition.md` (Pass-5)
/ `Systems/LEVEL01 Level-Edit Punchlist.md` §10. Relocation A/B proven in-game 2026-06-24
(moved LEVEL01 exit 177->108: same forward-walk is inert on pristine, ends the level on the edit).

⚠️ **The array location is PER LEVEL.** `(chunk 32, local 0x36570)` is LEVEL01's and nothing
else's — LEVEL03's array is chunk 28 @0x36890, the training level's is chunk 33 @0xbd80, and
four scenes keep it in a flat `.ALL` container. Until 2026-08-10 this tool hardcoded LEVEL01's
pair, so every other level walked garbage and printed **nothing** — a silence repeatedly at
risk of being read as "this level has no region codes". Other levels are now resolved through
the committed locator `analysis/phase4_e02_disc_region_code_census.json`; an unknown container
is a hard error, never silence. LEVEL01 keeps its independently established constants, and the
locator must agree with them or the tool refuses.

Dry-run unless --write --out. Examples:
  # list every sector's region code
  edit_sector_region_code.py LEVEL.RAW --list
  # move the LEVEL01 exit from sector 177 to sector 108
  edit_sector_region_code.py LEVEL.RAW --clear 177 --set 108:2 --write --out build/x.RAW
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import decode_level_raw as DEC
import recompress_level_raw as REC

ROOT = Path(__file__).resolve().parents[1]
LOCATOR = ROOT / "analysis/phase4_e02_disc_region_code_census.json"

# LEVEL01's array, established independently of the locator artifact and kept that way so the
# runtime census's LEVEL01 disc cross-check stays an outside check rather than a restatement.
LEVEL01_CHUNK, LEVEL01_LOCAL = 32, 0x36570

COLL_CHUNK = 32           # LEVEL01 default; overridden per container by resolve_array()
SECTOR_LOCAL = 0x36570
SECTOR_STRIDE = 0x4c
REGION_CODE = 0x2c        # word; -> runtime sector_table +0x2e
ORIGIN_X = 0x08


def be32(b, o): return struct.unpack_from(">I", b, o)[0]


def split_chunks(raw: bytes):
    off, out = 0, []
    while off + 8 <= len(raw):
        w0, w1 = be32(raw, off), be32(raw, off + 4)
        if w0 == 0xffffffff:
            break
        out.append((off, w0, w1, raw[off:off + 0xe + w1]))
        off += 0xe + w1
    return out


def sectors_in_chunk32(dec_len: int) -> int:
    return (dec_len - SECTOR_LOCAL) // SECTOR_STRIDE


def resolve_array(raw_path: Path):
    """Return (chunk, local_offset, authored_or_None, how) for this container.

    Never guesses: an unrecognised container is a hard error. Silence here is what made
    every non-LEVEL01 level look code-free for months.
    """
    suffix = f"{raw_path.parent.name}/{raw_path.name}"
    entries = {}
    if LOCATOR.exists():
        doc = json.loads(LOCATOR.read_text())
        for label, lv in doc.get("levels", {}).items():
            if lv.get("located"):
                entries[lv["container"]] = (label, lv)

    hit = None
    if entries:
        digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        for cont, (label, lv) in entries.items():
            if lv.get("container_sha256") == digest:
                hit = (cont, label, lv, "locator (container sha256 match)")
                break
        if hit is None and suffix in entries:
            label, lv = entries[suffix]
            hit = (suffix, label, lv, "locator (path match; content differs from pristine)")

    if hit is not None:
        cont, label, lv, how = hit
        chunk = lv["array_chunk"]
        local = int(lv["array_chunk_local_offset"], 16)
        if cont == "LEVEL01/LEVEL.RAW" and (chunk, local) != (LEVEL01_CHUNK, LEVEL01_LOCAL):
            raise SystemExit(f"locator disagrees with LEVEL01's established constants: "
                             f"({chunk}, {local:#x}) != ({LEVEL01_CHUNK}, {LEVEL01_LOCAL:#x})")
        return chunk, local, lv.get("authored_sectors"), f"{cont} via {how}"

    if suffix == "LEVEL01/LEVEL.RAW":
        return LEVEL01_CHUNK, LEVEL01_LOCAL, None, "LEVEL01 established constants"

    known = ", ".join(sorted(entries)) or "(locator artifact missing)"
    raise SystemExit(
        f"no sector-array location known for {suffix!r}.\n"
        f"  The array's (chunk, offset) is PER LEVEL -- guessing LEVEL01's would walk garbage\n"
        f"  and print nothing, which is not evidence of no region codes.\n"
        f"  Regenerate the locator with tools/phase4_e02_disc_region_code_census.py, or pass\n"
        f"  --chunk/--offset explicitly.  Known containers: {known}")


def rec_off(i: int) -> int:
    return SECTOR_LOCAL + i * SECTOR_STRIDE


def get_code(dec: bytes, i: int) -> int:
    return struct.unpack_from("<i", dec, rec_off(i) + REGION_CODE)[0]


def origin(dec: bytes, i: int):
    return struct.unpack_from("<iii", dec, rec_off(i) + ORIGIN_X)


def main() -> int:
    ap = argparse.ArgumentParser(description="Edit LEVEL.RAW chunk-32 per-sector region codes (level-exit trigger).")
    ap.add_argument("raw", type=Path, help="source LEVEL.RAW")
    ap.add_argument("--list", action="store_true", help="list sectors with a non-zero region code and exit")
    ap.add_argument("--list-all", action="store_true", help="list ALL editable sectors (idx, runtime origin, code)")
    ap.add_argument("--set", action="append", default=[], metavar="I:CODE",
                    help="set sector I's region code to CODE (e.g. 108:2); may repeat")
    ap.add_argument("--clear", action="append", default=[], type=lambda s: int(s, 0), metavar="I",
                    help="clear sector I's region code to 0; may repeat")
    ap.add_argument("--write", action="store_true", help="write --out; default dry-run")
    ap.add_argument("--out", type=Path, help="output LEVEL.RAW; required with --write")
    ap.add_argument("--chunk", type=lambda s: int(s, 0), help="override the array's chunk index")
    ap.add_argument("--offset", type=lambda s: int(s, 0), help="override the array's chunk-local offset")
    args = ap.parse_args()

    global COLL_CHUNK, SECTOR_LOCAL
    if (args.chunk is None) != (args.offset is None):
        raise SystemExit("--chunk and --offset must be given together")
    if args.chunk is not None:
        COLL_CHUNK, SECTOR_LOCAL, authored, how = args.chunk, args.offset, None, "manual --chunk/--offset"
    else:
        COLL_CHUNK, SECTOR_LOCAL, authored, how = resolve_array(args.raw)

    raw = args.raw.read_bytes()
    flat = args.raw.suffix.upper() != ".RAW"       # .ALL/.DAT/.BIN are uncompressed
    if flat:
        chunks, dec = None, bytearray(raw)
    else:
        chunks = split_chunks(raw)
        if len(chunks) <= COLL_CHUNK:
            raise SystemExit(f"LEVEL.RAW has {len(chunks)} chunks, need >{COLL_CHUNK}")
        dec = bytearray(DEC.decompress_chunk(chunks[COLL_CHUNK][3]))
    nfit = sectors_in_chunk32(len(dec))
    if authored is not None:
        nfit = min(nfit, authored)                # never list past the authored prefix

    if args.list or args.list_all:
        print(f"array: {how}; chunk {COLL_CHUNK} local {SECTOR_LOCAL:#x}")
        print(f"chunk {COLL_CHUNK}: {len(dec)} B; sectors 0..{nfit-1} editable here"
              + ("" if authored is not None else " (rest span into the next chunk)"))
        for i in range(nfit):
            code = get_code(dec, i)
            if args.list_all or code != 0:
                x, y, z = origin(dec, i)
                tag = "  <-- LEVEL EXIT" if code == 2 else ""
                print(f"  sec {i:3d}: code={code:<4d} runtime origin({x<<5},{y<<5},{z<<5}){tag}")
        return 0

    if args.write and args.out is None:
        raise SystemExit("--write requires --out")
    if args.out is not None and args.out.resolve() == args.raw.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")

    edits = []  # (sector, new_code)
    for spec in args.set:
        try:
            si, cs = spec.split(":")
            edits.append((int(si, 0), int(cs, 0)))
        except ValueError:
            raise SystemExit(f"--set expects I:CODE, got {spec!r}")
    edits += [(i, 0) for i in args.clear]
    if not edits:
        raise SystemExit("nothing to do (use --set / --clear; or --list)")
    over = [i for i, _ in edits if not (0 <= i < nfit)]
    if over:
        raise SystemExit(f"sector(s) {over} not editable in chunk 32 (0..{nfit-1})")

    for i, code in edits:
        old = get_code(dec, i)
        struct.pack_into("<i", dec, rec_off(i) + REGION_CODE, code)
        print(f"  sec {i:3d}: region code {old} -> {code}")

    if flat:
        new_raw = bytes(dec)
        print(f"{args.raw.name}: uncompressed container, {len(new_raw)} bytes (size unchanged).")
    else:
        header6 = chunks[COLL_CHUNK][3][8:0xe]
        newcomp = REC.compress_chunk(bytes(dec), header6)
        if bytes(DEC.decompress_chunk(newcomp)) != bytes(dec):
            raise SystemExit("recompress round-trip mismatch — refusing")
        coff = chunks[COLL_CHUNK][0]
        old_comp_len = len(chunks[COLL_CHUNK][3])
        new_raw = raw[:coff] + newcomp + raw[coff + old_comp_len:]
        print(f"LEVEL.RAW: {len(raw)} -> {len(new_raw)} ({len(new_raw)-len(raw):+d}; chunk"
              f"{COLL_CHUNK} comp {old_comp_len}->{len(newcomp)}). "
              f"Rebuild with tools/build_autolayout_disc.py.")

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(new_raw)
        if flat:
            chk = new_raw
        else:
            rc = split_chunks(new_raw)
            chk = DEC.decompress_chunk(rc[COLL_CHUNK][3])
        for i, code in edits:
            if get_code(chk, i) != code:
                raise SystemExit(f"verify failed: sector {i} edit not present in spliced file")
        print(f"wrote {args.out} ({len(new_raw)} bytes)")
    else:
        print("dry-run only; no LEVEL.RAW written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
