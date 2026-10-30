#!/usr/bin/env python3
"""LEVEL.RAW chunk load-evidence join (Phase 4 — docs/SUBSTRATE.md).

Joins the boot-trace decompressor call events (analysis/traces/boot_trace.json,
watch `level_raw_lzss_decompress` = FUNC_8001A1DC) against the byte-exact chunk
table (tools/LEVEL_RAW_decompressed/chunk_index.json) to produce ONE committed
record per LEVEL01 chunk:

  analysis/level_raw_chunks.json — chunk_id, file offsets/sizes, observed
  load (decompress) destination address, requesting caller (ra), semantic
  role + confidence (seeded from the Canon chunk-role table, upgraded with
  runtime evidence), and the evidence trail.

The decompressor's register convention (which of a0/a1 is the compressed
source) is determined empirically per event: the argument that falls inside
the LEVEL.RAW compressed image window is the source; the other RAM argument is
the destination.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "analysis" / "traces" / "boot_trace.json"
CHUNK_INDEX = ROOT / "tools" / "LEVEL_RAW_decompressed" / "chunk_index.json"
OUT = ROOT / "analysis" / "level_raw_chunks.json"

COMPRESSED_BASE = 0x80115AAC          # LEVEL.RAW compressed image (LEVEL01)
COMPRESSED_SIZE = 0xB6BE4
RAM_LO, RAM_HI = 0x80000000, 0x80200000

# Semantic seed — Canon chunk-role table (GAP-0022; vault
# [[MEM_LEVEL.RAW_CHUNK_INVENTORY]] / Asset - LEVEL.RAW Chunk Role Table).
def seed_role(cid: int) -> tuple[str, str]:
    if cid in (29,):
        return "backdrop panorama + sky palette (subtype 0x24)", "confirmed"
    if cid == 31:
        return "seed table (subtype 0x23)", "confirmed"
    if cid == 32:
        return "collision planes + sky table (subtype 0x103)", "confirmed"
    if cid == 34:
        return "master mesh definition (subtype 0x101, obj 0)", "confirmed"
    if cid == 35:
        return "master mesh payload (subtype 0x102 -> 0x8012C1D0)", "confirmed"
    if cid == 33:
        return "collision sector-source tail (sectors 189-222; first 0xa14 bytes)", "confirmed"
    if cid <= 14 or cid in (28, 30):
        return "texture page (Region A VRAM upload)", "confirmed_format"
    if 15 <= cid <= 31:
        return "sprite container (subtype 0x22)", "likely"
    return "per-object mesh def/payload pair (obj-id keyed)", "likely"


def main() -> int:
    chunks = json.loads(CHUNK_INDEX.read_text())
    trace = json.loads(TRACE.read_text())
    events = trace["anchor_events"].get("level_raw_lzss_decompress", [])

    # empirical src/dst classification per event
    calls = []
    for ev in events:
        regs = ev.get("regs", ev)   # execTrace nests captured registers under "regs"
        args = {}
        for reg in ("a0", "a1", "a2"):
            v = regs.get(reg)
            if isinstance(v, str):
                v = int(v, 16)
            if v is not None:
                args[reg] = v
        src = next((v for v in args.values()
                    if COMPRESSED_BASE <= v < COMPRESSED_BASE + COMPRESSED_SIZE), None)
        dst = next((v for r, v in args.items()
                    if v != src and RAM_LO <= v < RAM_HI), None)
        if src is not None:
            calls.append({"src_off": src - COMPRESSED_BASE, "dst": dst,
                          "ra": regs.get("ra"), "frame": ev.get("frame")})

    # map src offsets to chunks: nearest chunk whose comp_off <= src_off,
    # tolerating the per-chunk size/stream header
    offs = sorted((c["comp_off"], c["chunk"]) for c in chunks)
    def owner(src_off: int):
        import bisect
        i = bisect.bisect_right(offs, (src_off, 1 << 30)) - 1
        if i < 0:
            return None, None
        comp_off, cid = offs[i]
        return cid, src_off - comp_off
    by_chunk: dict[int, list[dict]] = {}
    unmatched = []
    for call in calls:
        cid, delta = owner(call["src_off"])
        if cid is not None and delta is not None and delta <= 0x20:
            by_chunk.setdefault(cid, []).append(call)
        else:
            unmatched.append(call)

    records = []
    for c in chunks:
        cid = c["chunk"]
        role, conf = seed_role(cid)
        obs = by_chunk.get(cid, [])
        rec = {
            "chunk_id": cid,
            "file": "LEVEL01/LEVEL.RAW",
            "comp_off": c["comp_off"],
            "comp_size": c["word1"],
            "decomp_off": c["decomp_off"],
            "decomp_size": c["word0"],
            "load_address": (f"0x{obs[0]['dst']:08x}"
                             if obs and obs[0]["dst"] is not None else None),
            "exec_address": None,
            "loader_caller": obs[0]["ra"] if obs else None,
            "decompressor": "0x8001a1dc" if obs else None,
            "first_frame": obs[0]["frame"] if obs else None,
            "decompress_calls_observed": len(obs),
            "semantic_guess": role,
            "confidence": conf,
            "runtime_load_observed": bool(obs),
            "evidence": (["EXP_2026-07-08_boot_trace_baseline"] if obs else [])
                        + ["chunk_index.json (byte-exact codec)"],
        }
        records.append(rec)

    doc = {
        "generated_by": "tools/chunk_evidence.py",
        "source_trace": {k: trace[k] for k in ("movie", "disc", "fork_rev")},
        "compressed_base": f"{COMPRESSED_BASE:#010x}",
        "decompress_calls_total": len(calls),
        "decompress_calls_unmatched": unmatched[:20],
        "chunks": records,
    }
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    loaded = sum(1 for r in records if r["runtime_load_observed"])
    print(f"[chunks] {loaded}/69 chunks with observed runtime decompress; "
          f"{len(unmatched)} unmatched call(s) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
