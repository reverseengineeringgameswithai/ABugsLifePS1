#!/usr/bin/env python3
"""Find the LIVE renderer/source of the visible LEVEL01 spawn ground (read-only).

Pivot: chunk 34/35 did NOT validate as the spawn floor (the 0x80017464 buffer held
Flik's model). The vault says the bulk ground under Flik is fcn.80010000 DAT objects
via sub-emitter FUNC_80019934 (rtpt 0x80019684/0x80019734). This tool CONFIRMS that
live by tracing several candidate render PCs, classifying each PC's geometry
(terrain-like vs compact-model via geometry_kind), composing verts to world with the
recovered camera matrix, and checking proximity to Flik's spawn.

It mutates nothing (no writeMemory; loadState reads a save; execTrace/readMemory/
gpu.pickObject are read-only). Outputs a trace JSON + an analysis JSON.

Candidate PCs (ALL vault-sourced; verify, do not invent):
  * 0x80019684 / 0x80019734  FUNC_80019934 rtpt — bulk-ground sub-emitter of fcn.80010000
                             (Finding - Visible ground from DAT verts)
  * 0x80010718               fcn.80010000 per-primitive SXY site (DAT / Candidate A)
  * 0x800104d8               fcn.80010000 RTPT          (FUNC_80010000)
  * 0x80017464               fcn.800172dc rtpt — contrast (known to draw Flik/compact)
Camera matrix 0x1f8003b4, camera pos 0x1f800374, Flik 0x800A6500 (all live-verified).
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import trace_terrain_transform as tt          # shared decode/connect (unit-tested)
import analyze_terrain_transform as AZ         # geometry_kind
import transform_math as TM

VERSION = "1"
DEFAULT_PCS = [
    ("0x80019684", "FUNC_80019934 rtpt (bulk-ground sub-emitter of fcn.80010000)"),
    ("0x80019734", "FUNC_80019934 rtpt #2"),
    ("0x80010718", "fcn.80010000 per-primitive SXY site (DAT / Candidate A)"),
    ("0x800104d8", "fcn.80010000 RTPT"),
    ("0x80017464", "fcn.800172dc rtpt (contrast: known Flik/compact)"),
]
DAT_PCS = {"0x80019684", "0x80019734", "0x80010718", "0x800104d8"}   # fcn.80010000 family
CHUNK_PCS = {"0x80017464", "0x800174bc", "0x8001784c"}               # fcn.800172dc family
CAM_MAT_ADDR = 0x1F8003B4
CAM_POS_ADDR = 0x1F800374
FLIK_POS_ADDR = 0x800A6500
PTR_REGS = ("a0", "a1", "a2", "s7")    # a0 = payload ptr for fcn.80010000
# verified capture set (terrain tool's GTE+GPR names) + s7 (fcn.80019934 work ctx)
SPAWN_CAPTURE = tt.DEFAULT_CAPTURE + ["s7"]


# --------------------------------------------------------------------------
# Pure analysis (DuckStation-free; unit-tested)
# --------------------------------------------------------------------------
def _verts_to_world(hits, Rinv, C):
    pts = []
    for h in hits:
        rot = h.get("decoded", {}).get("model_to_view_rotation")
        tr = h.get("decoded", {}).get("translation")
        for v in h.get("decoded", {}).get("input_verts") or []:
            if rot and tr:
                pts.append(TM.terrain_vert_to_world(Rinv, C, rot["matrix_float"],
                           [tr["trx"], tr["try"], tr["trz"]], [v["x"], v["y"], v["z"]]))
    return pts


def classify_pc(pc, role, hits, R, C, flik, thresh, min_xz_extent) -> dict:
    """Classify one PC's geometry: terrain-like vs compact-model, and (if camera
    data present) whether it composes to a wide world region near Flik's spawn."""
    gk = AZ.geometry_kind(hits)
    world = None
    if R and C and flik:
        best = None
        for layout, name in ((R, "row-major"), (TM.transpose3(R), "col-major")):
            Rinv = TM.inverse3(layout)
            if Rinv is None:
                continue
            pts = _verts_to_world(hits, Rinv, C)
            if not pts:
                continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
            xz_extent = max(max(xs) - min(xs), max(zs) - min(zs))
            cc = TM.crosscheck_xz(pts, (flik[0], flik[2]), thresh)
            cand = {"layout": name, "world_xz_extent": round(xz_extent, 1),
                    "world_y_mean": round(sum(ys) / len(ys), 1),
                    "median_dist_flik": round(cc["median_xz_dist"], 1),
                    "near_flik": cc["passed"], "n_world_verts": len(pts)}
            if best is None or cand["median_dist_flik"] < best["median_dist_flik"]:
                best = cand
        world = best

    ptrs = Counter()
    dat_backed = False
    for h in hits:
        for r in PTR_REGS:
            v = h.get("regs_int", {}).get(r)
            if v and tt.RAM_LO <= v < tt.RAM_HI:
                ptrs[f"{r}=0x{v:08x}"] += 1
                # a0 = payload ptr; LEVEL.DAT objects live ~0x80170000-0x80190000
                if r == "a0" and 0x80170000 <= v < 0x80190000:
                    dat_backed = True

    # Label on the RAW model-vert spread (camera-matrix-independent terrain signal)
    # + whether composition lands near Flik. The COMPOSED world extent is NOT a
    # gate (the non-orthonormal camera matrix collapses it); it's reported only.
    raw_wide = gk["kind"] == "terrain_like" and gk.get("xz_extent", 0) >= min_xz_extent
    near = bool(world and world["near_flik"])
    if raw_wide and near:
        label = "terrain_like_near_spawn"
    elif raw_wide:
        label = "terrain_like_elsewhere"
    elif gk["kind"] == "compact_model_like":
        label = "compact_model"
    elif gk["kind"] == "unknown":
        label = "unknown"
    else:
        label = "ambiguous"
    return {"pc": pc, "role": role, "n_hits": len(hits), "geometry_kind": gk,
            "world": world, "dat_backed": dat_backed,
            "top_source_pointers": ptrs.most_common(4), "label": label}


def rank_spawn_sources(per_pc: list) -> dict:
    """Decide the overall status + which renderer is the spawn-ground source."""
    found = [p for p in per_pc if p["label"] == "terrain_like_near_spawn"]
    partial = [p for p in per_pc if p["label"] == "terrain_like_elsewhere"]
    dat_found = [p for p in found if p["pc"] in DAT_PCS]
    chunk_found = [p for p in found if p["pc"] in CHUNK_PCS]
    flags = []
    if dat_found and not chunk_found:
        status = "SOURCE_FOUND"
        source = "fcn.80010000 / LEVEL.DAT (Candidate-A family)"
        flags.append("REJECTED_CHUNK34_35_AS_SPAWN_FLOOR")
        flags.append("DAT_COVERAGE_BUG_SUSPECTED")  # editor decodes this family but shows no spawn floor
        winner = dat_found[0]
    elif chunk_found:
        status = "SOURCE_FOUND"
        source = "fcn.800172dc / LEVEL.RAW chunk 34/35"
        winner = chunk_found[0]
    elif found:
        status = "SOURCE_FOUND"
        source = found[0]["role"]
        winner = found[0]
    elif partial:
        status = "SOURCE_PARTIAL"
        source = partial[0]["role"]
        winner = partial[0]
    else:
        status = "BLOCKED"
        source = None
        winner = None
        if all(p["label"] in ("compact_model", "unknown", "ambiguous") for p in per_pc):
            flags.append("only compact-model/unknown hits — no terrain-like draw captured")
    return {"status": status, "source": source, "flags": flags,
            "winner_pc": winner["pc"] if winner else None,
            "winner_summary": winner}


# --------------------------------------------------------------------------
# Live capture
# --------------------------------------------------------------------------
def _read(c, addr, n):
    return bytes.fromhex(c.call("debugger.readMemory", {"address": tt._hexaddr(addr), "length": n})["hex"])


def _collect(c, wid, limit):
    out, off = [], 0
    while True:
        p = {"offset": off, "limit": 1000}
        if wid is not None:
            p["watch_id"] = wid
        res = c.call("execTrace.get", p)
        evs = res.get("events", []) if isinstance(res, dict) else []
        out.extend(evs); off += len(evs)
        if not evs or (limit and len(out) >= limit):
            break
    return out[:limit] if limit else out


def run_live(args, pcs) -> dict:
    c = tt.connect(args.host, args.port, args.token, args.timeout)
    warnings = []
    status = c.call("debugger.status")
    if args.state:
        warnings.append("loadState assumes the SAME disc as the state; mismatch hard-crashes.")
        c.call("emulator.loadState", {"path": args.state})
        for _ in range(max(args.settle, 0)):
            c.call("emulator.advanceFrames", {"frames": 1})

    # camera matrix + pos + Flik (read-only)
    R = C = flik = None
    try:
        raw = _read(c, args.cam_mat, 18)
        vals = struct.unpack("<9h", raw)
        R = [[vals[r * 3 + k] / 4096.0 for k in range(3)] for r in range(3)]
    except Exception as exc:
        warnings.append(f"camera matrix read @0x{args.cam_mat:08x} failed: {exc}")
    try:
        C = [float(v) for v in struct.unpack("<3i", _read(c, args.cam_pos, 12))]
    except Exception as exc:
        warnings.append(f"camera pos read failed: {exc}")
    try:
        fx, fy, fz = struct.unpack("<3i", _read(c, FLIK_POS_ADDR, 12))
        flik = [fx, fy, fz]
    except Exception as exc:
        warnings.append(f"Flik read failed: {exc}")

    per_pc_hits = {}
    for pc, _role in pcs:
        c.call("execTrace.clear")
        wid, cap, fb = None, SPAWN_CAPTURE, False
        try:
            wr = c.call("execTrace.addWatch", tt.addwatch_params(pc, SPAWN_CAPTURE, args.max_events))
            wid = wr.get("watch_id")
        except Exception as exc:
            warnings.append(f"addWatch@{pc} failed: {exc}")
            continue
        c.call("execTrace.run", {"frames": args.frames})
        evs = _collect(c, wid, args.limit_hits)
        per_pc_hits[pc] = [tt.normalize_hit(e, requested=SPAWN_CAPTURE) for e in evs]
    c.call("execTrace.clear")

    # optional GPU pick of the visible floor (lower-center native pixels)
    gpu_picks = None
    if args.gpu_pick:
        gpu_picks = []
        for (px, py) in _pick_points(args.pick_points):
            try:
                res = c.call("gpu.pickObject", {"x": px, "y": py})
                gpu_picks.append({"x": px, "y": py, "status": "observed", "result": res})
            except Exception as exc:
                gpu_picks.append({"x": px, "y": py, "status": "error", "warning": str(exc)})

    return {"endpoint": {"host": args.host, "port": args.port}, "debugger_status": status,
            "camera_matrix": R, "camera_pos": C, "flik_world_pos": flik,
            "per_pc_hits": per_pc_hits, "gpu_picks": gpu_picks, "warnings": warnings}


def _pick_points(spec):
    if spec:
        out = []
        for p in spec.split(";"):
            x, y = p.split(",")
            out.append((int(x), int(y)))
        return out
    # default: a column down the lower-center where ground usually is (native ~512x240)
    return [(256, 150), (256, 180), (256, 210), (200, 200), (312, 200)]


def main(argv=None) -> int:
    repo = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=23460)
    ap.add_argument("--token", default=None)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--state", default=None)
    ap.add_argument("--settle", type=int, default=8)
    ap.add_argument("--frames", type=int, default=4)
    ap.add_argument("--limit-hits", type=int, default=400)
    ap.add_argument("--pcs", default=None, help="comma list of PCs to trace (default: vault candidates)")
    ap.add_argument("--cam-mat", type=lambda s: int(s, 0), default=CAM_MAT_ADDR)
    ap.add_argument("--cam-pos", type=lambda s: int(s, 0), default=CAM_POS_ADDR)
    ap.add_argument("--max-events", type=int, default=10000)
    ap.add_argument("--thresh", type=float, default=80000.0, help="near-Flik XZ radius (runtime units)")
    ap.add_argument("--min-xz-extent", type=float, default=3000.0,
                    help="min RAW model-vert XZ extent to call terrain 'wide' (camera-matrix-independent)")
    ap.add_argument("--filter-geometry", default=None, choices=[None, "terrain_like"],
                    help="if set, the analysis flags only PCs of this geometry kind")
    ap.add_argument("--keep-rejected-summary", action="store_true")
    ap.add_argument("--gpu-pick", action="store_true", help="also gpu.pickObject the visible floor")
    ap.add_argument("--pick-points", default=None, help="';'-sep 'x,y' native pixels")
    ap.add_argument("--out", default=str(repo / "logs" / "spawn_ground_source_trace_live.json"))
    ap.add_argument("--analysis-out", default=str(repo / "logs" / "spawn_ground_source_analysis_live.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    pcs = ([(p.strip(), "user-specified") for p in args.pcs.split(",")] if args.pcs else DEFAULT_PCS)

    meta = {"tool": "trace_spawn_ground_source", "version": VERSION, "disc_mutated": False,
            "guest_ram_written": False, "save_state": args.state, "frames": args.frames,
            "traced_pcs": pcs}
    if args.dry_run:
        meta["mode"] = "dry-run (no emulator)"
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(meta, indent=2))
        print("[trace_spawn_ground_source] dry-run; PCs:", [p for p, _ in pcs])
        return 0

    live = run_live(args, pcs)
    trace = {**meta, "mode": "live", **live}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(trace, indent=2))

    # analysis
    role_by_pc = dict(pcs)
    per_pc = [classify_pc(pc, role_by_pc.get(pc, "?"), hits, live["camera_matrix"],
                          live["camera_pos"], live["flik_world_pos"], args.thresh, args.min_xz_extent)
              for pc, hits in live["per_pc_hits"].items()]
    ranking = rank_spawn_sources(per_pc)
    analysis = {"tool": "spawn_ground_source_analysis", "save_state": args.state,
                "flik_world_pos": live["flik_world_pos"], "camera_pos": live["camera_pos"],
                "per_pc": per_pc, "ranking": ranking,
                "gpu_picks": live.get("gpu_picks"),
                "filter_geometry": args.filter_geometry,
                "do_not": ["bake constants", "place chunk 34/35", "change editor rendering"]}
    if args.keep_rejected_summary:
        analysis["rejected_summary"] = [{"pc": p["pc"], "label": p["label"],
                                         "geometry_kind": p["geometry_kind"]["kind"]}
                                        for p in per_pc if p["label"] != "terrain_like_near_spawn"]
    Path(args.analysis_out).write_text(json.dumps(analysis, indent=2))

    print(f"[trace_spawn_ground_source] live; Flik={live['flik_world_pos']}")
    for p in per_pc:
        w = p["world"] or {}
        print(f"  {p['pc']} {p['label']:24s} kind={p['geometry_kind']['kind']:18s} "
              f"world_xz_extent={w.get('world_xz_extent')} dist_flik={w.get('median_dist_flik')} "
              f"n={p['n_hits']} ptrs={p['top_source_pointers'][:2]}")
    print(f"  STATUS: {ranking['status']}  source={ranking['source']}  flags={ranking['flags']}")
    if live.get("gpu_picks"):
        print(f"  gpu picks: {sum(1 for g in live['gpu_picks'] if g['status']=='observed')} observed")
    print(f"  -> {args.out}\n  -> {args.analysis_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
