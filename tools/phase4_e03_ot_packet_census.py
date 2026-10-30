#!/usr/bin/env python3
"""Phase-4 E03: OT/packet census per scene class via gp0Trace.

Captures N consecutive frames of the GP0 command stream per scene class
(normal gameplay / boss / FMV / frontend), classifies every command into a
packet family, clusters DMA source addresses into buffer regions, and records
double-buffering evidence (per-frame DMA cluster alternation + display-area
origin from gpu.getStatus + the active output-buffer pointer [0x8008240C],
Canon MEM - OT output buffer pointer).

Arming sequence per the fork docs: gp0Trace.start -> clear -> advanceFrames
while the scene is actively drawing -> get (paginated, oldest-first).
gp0Trace entries carry {frame, opcode, source dma|mmio, source_addr(dma),
words}. MMIO-only scenes (menus) are expected and recorded as such.

Usage: python3 tools/phase4_e03_ot_packet_census.py --port 23701 \
           [--frames 4] [--out analysis/phase4_e03_ot_packet_census.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))

from live_session_provenance import (inspect_state_before_load,
                                     verified_media_identity)

OT_ACTIVE_PTR = 0x8008240C     # Canon: displayed drawenv/output buffer pointer
KNOWN_BUFFERS = {              # Canon starry-night finding
    0x801E134C: "output_buffer_A (drawenv x0)",
    0x801CC390: "output_buffer_B (drawenv x512)",
}

SCENES = [
    ("normal_gameplay", "level02.sav", 30),
    ("boss_showdown", "level_15.sav", 30),
    ("fmv", "movies/Phase4/E15_fmv_skip.movie.sav", 250),
    ("training", "phase3_pristine_training_gameplay_i5.sav", 30),
]


def family(op: int, words) -> str:
    if op == 0x00: return "nop"
    if op == 0x01: return "clear_cache"
    if op == 0x02: return "fill_rect"
    if 0x20 <= op <= 0x3F:
        tex = "tex" if op & 0x04 else "flat"
        shape = "quad" if op & 0x08 else "tri"
        gou = "gouraud_" if op & 0x10 else ""
        st = "_semitrans" if op & 0x02 else ""
        return f"poly_{gou}{tex}_{shape}{st}"
    if 0x40 <= op <= 0x5F:
        return "line" + ("_semitrans" if op & 0x02 else "")
    if 0x60 <= op <= 0x7F:
        size = {0x00: "var", 0x08: "1x1", 0x10: "8x8", 0x18: "16x16"}[op & 0x18]
        tex = "sprite" if op & 0x04 else "rect"
        st = "_semitrans" if op & 0x02 else ""
        return f"{tex}_{size}{st}"
    if 0x80 <= op <= 0x9F: return "vram_to_vram_copy"
    if 0xA0 <= op <= 0xBF: return "cpu_to_vram_blit"
    if 0xC0 <= op <= 0xDF: return "vram_to_cpu_read"
    if op == 0xE1: return "env_texpage"
    if op == 0xE2: return "env_texwindow"
    if op == 0xE3: return "env_draw_area_tl"
    if op == 0xE4: return "env_draw_area_br"
    if op == 0xE5: return "env_draw_offset"
    if op == 0xE6: return "env_mask"
    return f"unknown_0x{op:02x}"


def cluster(addrs, gap=0x4000):
    """Cluster sorted RAM addresses into regions separated by > gap."""
    out = []
    for a in sorted(addrs):
        if out and a - out[-1][1] <= gap:
            out[-1][1] = a
            out[-1][2] += 1
        else:
            out.append([a, a, 1])
    return [{"lo": f"0x{lo:08x}", "hi": f"0x{hi:08x}", "count": n}
            for lo, hi, n in out]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23701)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--frames", type=int, default=4)
    ap.add_argument("--dump-dir", default="", help="dir for per-scene 2MB RAM dumps (C walker input)")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e03_ot_packet_census.json"))
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(60)

    def rd_u32(addr):
        h = c.call("debugger.readMemory", {"address": "0x%08x" % addr, "length": 4})["hex"]
        return struct.unpack("<I", bytes.fromhex(h))[0]

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)

    scenes = {}
    for label, sav, settle in SCENES:
        path = ROOT / sav
        if not path.exists():
            scenes[label] = {"error": f"save missing: {sav}"}
            continue
        inspect_state_before_load(c, path, media_identity)
        r = c.call("emulator.loadState", {"path": str(path), "pause_after_load": True})
        if not r.get("loaded"):
            scenes[label] = {"error": f"loadState failed: {r}"}
            continue
        c.call("emulator.advanceFrames", {"frames": settle})

        c.call("gp0Trace.start", {"max_entries": 65536, "max_params": 16})
        c.call("gp0Trace.clear", {})
        per_frame_meta = []
        for _ in range(args.frames):
            c.call("emulator.advanceFrames", {"frames": 1})
            gs = c.call("gpu.getStatus", {})
            per_frame_meta.append({
                "ot_active_ptr": f"0x{rd_u32(OT_ACTIVE_PTR):08x}",
                "vram_source_rect": gs["crtc"]["vram_source_rect"],
                "drawing_offset": gs["drawing_offset"],
                "display_24bpp": gs["gpustat"]["display_area_color_depth_24"],
            })

        entries, off = [], 0
        while True:
            page = c.call("gp0Trace.get", {"offset": off, "limit": 4096})
            entries.extend(page["entries"])
            off += page["count"]
            if off >= page["total"] or page["count"] == 0:
                break
        truncated = page.get("truncated", False)
        c.call("gp0Trace.stop", {})

        frames = {}
        for e in entries:
            f = frames.setdefault(e["frame"], {
                "families": {}, "dma": 0, "mmio": 0, "dma_addrs": [],
                "env_texpage_values": set(), "semitrans_prims": 0})
            op = e["command_id"]
            fam = family(op, e.get("words", []))
            f["families"][fam] = f["families"].get(fam, 0) + 1
            if e["source"] == "dma":
                f["dma"] += 1
                f["dma_addrs"].append(int(e["source_addr"], 16) | 0x80000000)
            else:
                f["mmio"] += 1
            if fam.endswith("_semitrans"):
                f["semitrans_prims"] += 1
            if op == 0xE1:
                f["env_texpage_values"].add(e["words"][0])

        frame_rows = []
        addr_sets = {}
        for fi, (fnum, f) in enumerate(sorted(frames.items())):
            addr_sets[fnum] = set(f["dma_addrs"])
            frame_rows.append({
                "frame": fnum,
                "meta": per_frame_meta[fi] if fi < len(per_frame_meta) else None,
                "total": f["dma"] + f["mmio"],
                "dma": f["dma"], "mmio": f["mmio"],
                "semitrans_prims": f["semitrans_prims"],
                "families": dict(sorted(f["families"].items(),
                                        key=lambda kv: -kv[1])),
                "env_texpage_values": sorted(f["env_texpage_values"]),
                "dma_clusters": cluster(f["dma_addrs"]),
                "first_dma_addr": (f"0x{f['dma_addrs'][0]:08x}"
                                   if f["dma_addrs"] else None),
            })

        # Packet lifetime: exact source-addr recurrence between frames.
        # With double-buffered OTs, same-parity frames (N vs N+2) share a
        # buffer; retained/static packet pools recur at IDENTICAL addresses
        # even across parities.
        fnums = sorted(addr_sets)
        recurrence = []
        for i in range(len(fnums) - 1):
            for j in (i + 1, i + 2):
                if j >= len(fnums):
                    continue
                a, b = addr_sets[fnums[i]], addr_sets[fnums[j]]
                inter = a & b
                recurrence.append({
                    "frames": [fnums[i], fnums[j]],
                    "parity": "same" if (fnums[j] - fnums[i]) % 2 == 0 else "opposite",
                    "a_only": len(a - b), "b_only": len(b - a),
                    "shared": len(inter),
                    "shared_clusters": cluster(sorted(inter))[:8],
                })

        # RAM snapshot at the post-capture pause, for the C OT-walker
        # cross-implementation (kept out of the repo; sha256 recorded).
        dump_path = Path(args.dump_dir) / f"{label}_ram.bin"
        if args.dump_dir:
            with dump_path.open("wb") as fh:
                for base in range(0x80000000, 0x80200000, 0x10000):
                    fh.write(bytes.fromhex(c.call(
                        "debugger.readMemory",
                        {"address": "0x%08x" % base, "length": 0x10000})["hex"]))
            dump_sha = hashlib.sha256(dump_path.read_bytes()).hexdigest()
        else:
            dump_path, dump_sha = None, None

        scenes[label] = {
            "save": sav,
            "save_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "settle_frames": settle,
            "captured_frames": len(frame_rows),
            "trace_truncated": truncated,
            "frames": frame_rows,
            "addr_recurrence": recurrence,
            "ram_dump": str(dump_path) if dump_path else None,
            "ram_dump_sha256": dump_sha,
        }
        tot = sum(fr["total"] for fr in frame_rows)
        print(f"{label}: {len(frame_rows)} frames, {tot} cmds, "
              f"truncated={truncated}")

    out = {
        "_comment": "Phase-4 E03 OT/packet census per scene class via gp0Trace. "
                    "Known output buffers annotated from Canon (starry-night "
                    "finding): active ptr [0x8008240C] alternates 0x801E134C/"
                    "0x801CC390. Regenerate: tools/phase4_e03_ot_packet_census.py",
        "generated": str(date.today()),
        "media_identity": media_identity,
        "known_buffers": {f"0x{k:08x}": v for k, v in KNOWN_BUFFERS.items()},
        "scenes": scenes,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
