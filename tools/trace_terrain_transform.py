#!/usr/bin/env python3
"""Read-only execTrace capture of the LEVEL01 terrain/mesh transform.

Goal (P0 #2): gather the data needed to answer
    "What transform places LEVEL.RAW chunk 34/35 into world space so the real
     spawn ground appears under Flik?"

It traces the GTE RTPT inside FUNC_800172DC (default PC 0x80017464) and writes a
single JSON file for offline analysis (tools/analyze_terrain_transform.py).

SAFETY (hard guarantees):
  * Never writes guest RAM (no writeMemory/scatterWrite).
  * Never touches any disc image or editor data.
  * Only loadStates when --state is given (assumes the SAME disc is mounted as
    the state was made on -- loadState hard-crashes on a disc mismatch -- and
    prints a warning).
  * Removes its execTrace watch on exit (execTrace forces the interpreter).

APIs used are verified against THIS repo's tooling (not invented):
  * client: ~/duckstation/scripts/debugger-client/duckstation_debug_client.py
    (DebuggerClient(host,port,"ws").authenticate(tok); .call(method, params)).
  * execTrace.addWatch {pc, capture[<=32], max_events} -> {watch_id};
    execTrace.run {frames};
    execTrace.get {offset,limit,watch_id?} ->
      {events:[{frame,cycle,pc,regs:{n:hex},gte:{n:hex}}], total, truncated};
    execTrace.clear.   (an unknown capture name rejects the whole watch: -32006.)
  * debugger.readMemory {address,length} -> {hex}; debugger.status.
  * emulator.loadState {path}; emulator.advanceFrames {frames}.
  * GTE register names (gte.-prefixed) confirmed in DuckStation src/core/gte.cpp:
    RT_0..RT_4, TRX/TRY/TRZ, V0_XY/V0_Z/V1_XY/V1_Z/V2_XY/V2_Z, SXY0..2, SZ0..3.
  * FUNC_800172DC: a1 = source vertex buffer base (0x8012c1d0); per-quad stride
    0x30; vert xy at +0x4/0xc/0x14/0x1c (low16 X, high16 Y), z at +0x8/.../0x20.
    The 0x8012c… buffer holds TERRAIN *or* Flik's model depending on state, so
    the analysis must confirm the captured pointer's CONTENTS match chunk 34/35,
    not merely that the pointer is in range.

This script ONLY captures + labels data. It does NOT solve, bake, or place
anything. See tools/analyze_terrain_transform.py for the (still-partial) recovery.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from pathlib import Path

VERSION = "1"
DEFAULT_PC = "0x80017464"            # RTPT inside FUNC_800172DC
TERRAIN_BUF_BASE = 0x8012C1D0        # MEM - Terrain vertex buffer 8012C1D0
TERRAIN_BUF_END = 0x8012E784
FLIK_POS_ADDR = 0x800A6500           # Flik runtime world pos (x,y,z s32) — known anchor
RAM_LO, RAM_HI = 0x80000000, 0x80200000  # plausible main-RAM pointer window

# Candidate source-pointer registers (a1 is the documented one; capture a spread
# so the analysis can identify it empirically instead of trusting one name).
POINTER_REGS = ["a0", "a1", "a2", "a3", "s0", "s1", "t0", "t1"]

# GTE capture set (all names verified valid; a wrong one would reject the watch).
GTE_CAPTURE = [
    "gte.RT_0", "gte.RT_1", "gte.RT_2", "gte.RT_3", "gte.RT_4",   # model->view rotation
    "gte.TRX", "gte.TRY", "gte.TRZ",                              # translation
    "gte.V0_XY", "gte.V0_Z", "gte.V1_XY", "gte.V1_Z",            # input model verts
    "gte.V2_XY", "gte.V2_Z",
    "gte.SXY0", "gte.SXY1", "gte.SXY2",                           # projected screen xy
    "gte.SZ0", "gte.SZ1", "gte.SZ2",                              # projected depth
]
DEFAULT_CAPTURE = ["pc"] + POINTER_REGS + GTE_CAPTURE            # 29 names (<=32)
GPR_FALLBACK = ["pc"] + POINTER_REGS                            # if GTE capture is rejected


# --------------------------------------------------------------------------
# Pure helpers (no DuckStation needed — these are what the unit test covers)
# --------------------------------------------------------------------------
def _to_int(v):
    """execTrace/getRegisters values are HEX strings ('0x..' or bare). Accept a
    hex string, an int (passthrough), or None -> int|None."""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if s == "":
        return None
    if s.lower().startswith("0x"):
        s = s[2:]
    return int(s, 16)


def _s16(u):
    u &= 0xFFFF
    return u - 0x10000 if u & 0x8000 else u


def _s32(u):
    u &= 0xFFFFFFFF
    return u - 0x100000000 if u & 0x80000000 else u


def _lohi(u):
    """Split a u32 into (low s16, high s16) — the GTE/terrain vert packing."""
    u &= 0xFFFFFFFF
    return _s16(u & 0xFFFF), _s16((u >> 16) & 0xFFFF)


def decode_rt_matrix(gte: dict):
    """RT_0..RT_4 -> 3x3 model->view rotation (1.3.12 fixed -> float, /4096).

    Packing (PS1 GTE): RT_0=(R11,R12) RT_1=(R13,R21) RT_2=(R22,R23)
    RT_3=(R31,R32) RT_4=(R33,_). Returns None if any RT_* is missing.
    """
    vals = [_to_int(gte.get(f"RT_{i}")) for i in range(5)]
    if any(v is None for v in vals):
        return None
    r0, r1, r2, r3, r4 = vals
    r11, r12 = _lohi(r0)
    r13, r21 = _lohi(r1)
    r22, r23 = _lohi(r2)
    r31, r32 = _lohi(r3)
    r33, _ = _lohi(r4)
    raw = [[r11, r12, r13], [r21, r22, r23], [r31, r32, r33]]
    m = [[c / 4096.0 for c in row] for row in raw]
    # Column norms: for an orthonormal camera rotation each column's magnitude is
    # the model->world scale on that axis (camera-invariant). G33 found Y ~= 1.0.
    cols = [[m[r][c] for r in range(3)] for c in range(3)]
    norms = [round(sum(x * x for x in col) ** 0.5, 5) for col in cols]
    return {"raw_s16": raw, "matrix_float": m, "fixed_point": "1.3.12 (/4096)",
            "column_norms_xyz": norms, "status": "decoded"}


def decode_translation(gte: dict):
    t = [_to_int(gte.get(k)) for k in ("TRX", "TRY", "TRZ")]
    if any(v is None for v in t):
        return None
    return {"trx": _s32(t[0]), "try": _s32(t[1]), "trz": _s32(t[2]), "status": "decoded"}


def decode_input_verts(gte: dict):
    out = []
    for i in range(3):
        xy = _to_int(gte.get(f"V{i}_XY"))
        z = _to_int(gte.get(f"V{i}_Z"))
        if xy is None or z is None:
            continue
        x, y = _lohi(xy)
        out.append({"v": i, "x": x, "y": y, "z": _s16(z & 0xFFFF)})
    return out


def decode_screen(gte: dict):
    out = []
    for i in range(3):
        sxy = _to_int(gte.get(f"SXY{i}"))
        if sxy is None:
            continue
        x, y = _lohi(sxy)
        out.append({"s": i, "x": x, "y": y})
    return out


def classify_pointer(regs: dict, buf_lo: int, buf_hi: int):
    """Find which captured register holds the source-buffer pointer.

    Primary = first POINTER_REG whose value lands in the terrain buffer window.
    Also lists every register pointing anywhere into main RAM, so the analysis
    can reconsider if the buffer moved.
    """
    candidates = []
    primary = None
    for name in POINTER_REGS:
        v = _to_int(regs.get(name))
        if v is None:
            continue
        in_buf = buf_lo <= v < buf_hi
        in_ram = RAM_LO <= v < RAM_HI
        if in_ram:
            candidates.append({"reg": name, "value_hex": "0x%08x" % v,
                               "in_terrain_buffer": in_buf})
        if in_buf and primary is None:
            primary = {"reg": name, "value_hex": "0x%08x" % v,
                       "value": v, "offset_from_terrain_base": v - buf_lo,
                       "in_terrain_buffer": True}
    if primary is None:
        return {"status": "no candidate in terrain buffer range",
                "ram_pointer_candidates": candidates}
    return {"status": "observed", **primary, "other_ram_candidates": candidates}


def normalize_hit(event: dict, buf_lo: int = TERRAIN_BUF_BASE,
                  buf_hi: int = TERRAIN_BUF_END, requested=None) -> dict:
    """Normalize one execTrace event into observed/decoded/unknown sections.

    `event` is the raw {frame,cycle,pc,regs,gte} dict from execTrace.get.
    Pure: no emulator needed (this is the unit-tested core).
    """
    regs = event.get("regs", {}) or {}
    gte = event.get("gte", {}) or {}
    regs_int = {k: _to_int(v) for k, v in regs.items()}
    gte_int = {k: _to_int(v) for k, v in gte.items()}

    rt = decode_rt_matrix(gte)
    tr = decode_translation(gte)
    verts = decode_input_verts(gte)
    screen = decode_screen(gte)

    unknown = []
    for want, present in (("model_to_view_rotation", rt), ("translation", tr),
                          ("input_verts", verts), ("screen_xy", screen)):
        if not present:
            unknown.append(want)
    # which explicitly-requested capture names never came back
    if requested:
        got = set(regs.keys()) | {"gte." + k for k in gte.keys()}
        for name in requested:
            if name != "pc" and name not in got:
                unknown.append("capture:" + name)

    return {
        "observed": {"frame": event.get("frame"), "cycle": event.get("cycle"),
                     "pc": event.get("pc")},
        "regs_int": regs_int,
        "gte_int": gte_int,
        "decoded": {
            "pointer": classify_pointer(regs, buf_lo, buf_hi),
            "model_to_view_rotation": rt,
            "translation": tr,
            "input_verts": verts,
            "screen_xy": screen,
        },
        "unknown": unknown,
    }


def build_capture(spec: str | None) -> list:
    if not spec:
        return list(DEFAULT_CAPTURE)
    return [c.strip() for c in spec.split(",") if c.strip()]


def addwatch_params(pc: str, capture: list, max_events: int) -> dict:
    return {"pc": pc, "capture": capture, "max_events": max_events,
            "label": "terrain_transform", "stop_on_hit": False}


def decode_quad_sample(raw: bytes) -> dict:
    """Decode one 0x30-stride terrain quad from a buffer sample (best-effort)."""
    if len(raw) < 0x24:
        return {"status": "too short", "len": len(raw)}
    def xy(off):
        u = struct.unpack_from("<I", raw, off)[0]
        return list(_lohi(u))
    def z(off):
        return _s16(struct.unpack_from("<H", raw, off)[0])
    return {"status": "decoded", "verts_xy": [xy(0x4), xy(0xC), xy(0x14), xy(0x1C)],
            "verts_z": [z(0x8), z(0x10), z(0x18), z(0x20)]}


# --------------------------------------------------------------------------
# Live capture (DuckStation required) — imported lazily so the test never needs it
# --------------------------------------------------------------------------
def _hexaddr(a):
    return a if isinstance(a, str) else "0x%08x" % a


def connect(host, port, token, timeout):
    sys.path.insert(0, os.path.expanduser("~/duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient  # noqa: E402
    try:
        from abl_dbg import find_token
    except Exception:
        def find_token():
            return None
    c = DebuggerClient(host, port, "ws")
    tok = token or find_token() or "debugger-1000"
    c.authenticate(tok)
    try:
        c.transport.sock.settimeout(timeout)
    except Exception:
        pass
    return c


def run_live(args) -> dict:
    c = connect(args.host, args.port, args.token, args.timeout)
    warnings: list[str] = []

    try:
        status = c.call("debugger.status")
    except Exception as exc:  # pragma: no cover - needs a live server
        raise SystemExit(f"cannot reach debugger at {args.host}:{args.port}: {exc}")
    if not status.get("system_valid", status.get("running", True)):
        warnings.append("debugger.status reports no/invalid system loaded")

    if args.state:
        warnings.append("loadState assumes the SAME disc is mounted as the state "
                        "was made on; a mismatch hard-crashes DuckStation.")
        c.call("emulator.loadState", {"path": args.state})
        for _ in range(max(args.settle, 0)):     # watch is dropped on load; settle first
            c.call("emulator.advanceFrames", {"frames": 1})

    capture = build_capture(args.capture)
    c.call("execTrace.clear")                     # clean slate (also un-arms old watches)
    used = capture
    fallback = False
    try:
        wr = c.call("execTrace.addWatch", addwatch_params(args.pc, capture, args.max_events))
    except Exception as exc:
        msg = str(exc)
        if "-32006" in msg or "capture" in msg.lower():
            warnings.append(f"addWatch rejected the full capture ({msg}); "
                            "retrying GPR-only (no GTE) — Experiment 1 still works.")
            used, fallback = GPR_FALLBACK, True
            wr = c.call("execTrace.addWatch", addwatch_params(args.pc, used, args.max_events))
        else:
            raise
    watch_id = wr.get("watch_id") if isinstance(wr, dict) else None

    c.call("execTrace.run", {"frames": args.frames})

    # paginate execTrace.get
    raw_events = []
    offset, page = 0, 1000
    total = truncated = None
    while True:
        params = {"offset": offset, "limit": page}
        if watch_id is not None:
            params["watch_id"] = watch_id
        res = c.call("execTrace.get", params)
        evs = res.get("events", []) if isinstance(res, dict) else []
        total = res.get("total", total)
        truncated = res.get("truncated", truncated)
        raw_events.extend(evs)
        offset += len(evs)
        if not evs or (args.limit_hits and len(raw_events) >= args.limit_hits):
            break
    if args.limit_hits:
        raw_events = raw_events[: args.limit_hits]

    hits = [normalize_hit(e, args.buf_base, args.buf_end, requested=used)
            for e in raw_events]

    # Experiment 3 anchors: Flik world pos is a KNOWN address; others are not.
    anchors = {}
    try:
        fb = bytes.fromhex(c.call("debugger.readMemory",
                                  {"address": _hexaddr(FLIK_POS_ADDR), "length": 12})["hex"])
        fx, fy, fz = struct.unpack("<3i", fb)
        anchors["flik_world_pos"] = {"addr": "0x800a6500", "x": fx, "y": fy, "z": fz,
                                     "status": "observed"}
    except Exception as exc:
        anchors["flik_world_pos"] = {"addr": "0x800a6500", "status": "unknown",
                                     "warning": str(exc)}
    anchors["grain_world_pos"] = {"status": "unknown",
                                  "note": "TODO: no RAM address known; runtime ~= file_xyz<<5 "
                                          "(file coords are in the editor's scene_importer)."}
    anchors["camera_to_world"] = {"status": "unknown",
                                  "note": "TODO: REQUIRED for absolute model->world. The RTPT RT/TR "
                                          "captured here is model->VIEW; recovering model->WORLD needs "
                                          "the camera->world (view^-1) transform, whose RAM address is "
                                          "not yet known in the repo/vault. Do not guess it."}

    # Read short source samples at the distinct in-buffer pointers we saw (read-only).
    samples = []
    seen = []
    for h in hits:
        p = h["decoded"]["pointer"]
        if p.get("status") == "observed" and p["value"] not in seen:
            seen.append(p["value"])
            if len(seen) > args.max_samples:
                break
            try:
                raw = bytes.fromhex(c.call("debugger.readMemory",
                                           {"address": _hexaddr(p["value"]),
                                            "length": args.vsample})["hex"])
                samples.append({"addr": p["value_hex"], "hex": raw.hex(),
                                "first_quad": decode_quad_sample(raw)})
            except Exception as exc:
                samples.append({"addr": p["value_hex"], "status": "read failed",
                                "warning": str(exc)})

    c.call("execTrace.clear")                     # cleanup: remove watch, un-force interpreter

    return {
        "endpoint": {"host": args.host, "port": args.port},
        "debugger_status": status,
        "capture_used": used,
        "capture_fallback_used": fallback,
        "hit_count": len(hits),
        "total_hits_reported": total,
        "truncated": truncated,
        "anchors": anchors,
        "buffer_samples": samples,
        "hits": hits,
        "warnings": warnings,
    }


# --------------------------------------------------------------------------
def _meta(args) -> dict:
    return {
        "tool": "trace_terrain_transform",
        "version": VERSION,
        "disc_mutated": False,
        "guest_ram_written": False,
        "save_state": args.state,
        "trace_pc": args.pc,
        "frames_advanced": args.frames,
        "settle_frames": args.settle,
        "capture_requested": build_capture(args.capture),
        "buffer_range": {"base": "0x%08x" % args.buf_base, "end": "0x%08x" % args.buf_end},
        "remaining_unknowns": [
            "model->world transform (only model->VIEW is captured here)",
            "camera->world (view^-1) RAM address — needed to convert view->world",
            "definitive chunk-34 vs chunk-35 identity of the live buffer "
            "(resolve by matching buffer_samples to the decompressed chunk bytes)",
            "grain world-position RAM addresses (anchors for cross-check)",
        ],
        "next_step": "tools/analyze_terrain_transform.py <this file>",
    }


def main(argv=None) -> int:
    repo = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=23460,
                    help="isolated debugger instance port (default 23460)")
    ap.add_argument("--token", default=None, help="auth token (default: find_token() or debugger-1000)")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--state", default=None, help="save-state path to loadState first (SAME disc only)")
    ap.add_argument("--settle", type=int, default=8, help="frames to advance after loadState before tracing")
    ap.add_argument("--frames", type=int, default=4, help="frames to execTrace.run")
    ap.add_argument("--pc", default=DEFAULT_PC, help=f"watch PC (default {DEFAULT_PC})")
    ap.add_argument("--max-events", type=int, default=10000, help="execTrace.addWatch cap")
    ap.add_argument("--limit-hits", type=int, default=None,
                    help="cap stored hits (for small/test runs)")
    ap.add_argument("--capture", default=None, help="comma list of capture names (override default)")
    ap.add_argument("--buf-base", type=lambda s: int(s, 0), default=TERRAIN_BUF_BASE)
    ap.add_argument("--buf-end", type=lambda s: int(s, 0), default=TERRAIN_BUF_END)
    ap.add_argument("--vsample", type=int, default=0x60, help="bytes to read at each source pointer")
    ap.add_argument("--max-samples", type=int, default=16)
    ap.add_argument("--out", default=str(repo / "logs" / "terrain_transform_trace.json"))
    ap.add_argument("--dry-run", action="store_true",
                    help="don't connect; just emit the resolved plan (offline check)")
    args = ap.parse_args(argv)

    report = _meta(args)
    if args.dry_run:
        report["mode"] = "dry-run (no emulator contacted)"
        report["capture_used"] = build_capture(args.capture)
        report["addwatch_params_preview"] = addwatch_params(
            args.pc, report["capture_used"], args.max_events)
        report["hits"] = []
    else:
        report["mode"] = "live"
        report.update(run_live(args))

    out = Path(args.out)
    if not out.is_absolute():
        out = repo / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    print(f"[trace_terrain_transform] mode={report['mode']} pc={args.pc}")
    if not args.dry_run:
        print(f"  hits={report.get('hit_count')} (reported total {report.get('total_hits_reported')}), "
              f"capture_fallback={report.get('capture_fallback_used')}")
        ptr = next((h['decoded']['pointer'] for h in report.get('hits', [])
                    if h['decoded']['pointer'].get('status') == 'observed'), None)
        print(f"  source pointer: {ptr.get('reg') + '=' + ptr.get('value_hex') if ptr else 'NONE in terrain buffer (investigate)'}")
        rt = next((h['decoded']['model_to_view_rotation'] for h in report.get('hits', [])
                   if h['decoded']['model_to_view_rotation']), None)
        print(f"  model->view RT captured: {'yes, column norms ' + str(rt['column_norms_xyz']) if rt else 'NO'}")
        print(f"  Flik anchor: {report['anchors']['flik_world_pos']}")
        for w in report.get("warnings", []):
            print("  WARN:", w)
    print(f"  -> {out}")
    print("  NOTE: model->WORLD is NOT solved by this capture; run the analyzer next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
