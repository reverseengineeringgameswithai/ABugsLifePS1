#!/usr/bin/env python3
"""Read-only discovery of the LEVEL01 camera->world (view^-1) transform.

The terrain trace (tools/trace_terrain_transform.py) gives model->VIEW at the
chunk-34/35 RTPT (0x80017464). To turn that into model->WORLD we need the
camera's world->view (R,T); this tool gathers MULTIPLE independent candidate
sources for it -- read-only -- so the analyzer can cross-validate them instead of
trusting any single one. Nothing is baked or placed here.

Candidate sources (all addresses/PCs are VAULT-SOURCED with provenance and are
overridable; they are treated as candidates to VERIFY, never as ground truth):
  * Strategy A  -- GTE RT/TR at the WORLD-space renderer fcn.80010000 @0x80010718,
    where the draw is world-space so the GTE rotation IS the pure world->view
    (orthonormal). Provenance: Finding - Candidate A is DAT-backed visual terrain.
  * same-pose model->view at the terrain RTPT 0x80017464 (for the composition).
  * Strategy A2 -- execTrace the libgte camera-matrix load leaf fcn.800146e0,
    capture a0 (=matrix ptr) / a1 (=translation ptr), then READ them. Locates the
    world->view matrix in RAM. Provenance: geometry_g10_payload_render_chain.md.
  * Strategy B  -- direct READS of the vault's candidate RAM matrices: scratchpad
    view matrix 0x1f8003b4 + camera pos 0x1f800374; actor/camera struct 0x800a0a64.
  * getGteState -- decoded float control rotation/translation (observed snapshot).
  * Strategy D  -- Flik world pos 0x800A6500 (cross-check anchor).
  * Strategy C  -- optional --compare-state: re-read candidates at a 2nd state and
    diff, so camera-dependent fields are distinguishable from static ones.

SAFETY: no writeMemory, no scatterWrite, no disc/editor/RAM mutation; loadState
only with --state (same disc only) and warned; execTrace watches removed on exit.

APIs reused/verified: see tools/trace_terrain_transform.py (shared helpers) and
debugger.readMemory / debugger.getGteState / execTrace.* (confirmed in the repo).
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import trace_terrain_transform as tt   # shared, unit-tested decode/connect helpers

VERSION = "1"

# --- vault-sourced CANDIDATE locations (verify at runtime; do not bake) --------
WORLD_PC_CANDIDATE = "0x80010718"      # fcn.80010000 post-RTPT (world-space draw)
TERRAIN_PC = "0x80017464"              # fcn.800172dc RTPT (model-space chunk 34/35)
SETUP_PC_CANDIDATE = "0x800146e0"      # libgte camera-matrix load leaf (a0=mat,a1=tr)
SCRATCH_MAT_CANDIDATE = 0x1F8003B4     # scratchpad world->view matrix (9 s16, /4096)
SCRATCH_POS_CANDIDATE = 0x1F800374     # scratchpad camera world pos (3 s32)
CAM_STRUCT_CANDIDATE = 0x800A0A64      # actor/camera struct (+4/8/c pos, +0x28 matrix)
FLIK_POS_ADDR = 0x800A6500

# GTE-rich capture for the renderer PCs (<=32 names; reuses tt's verified names).
CAM_CAPTURE = ["pc", "a0", "a1", "a2", "a3"] + tt.GTE_CAPTURE
SETUP_CAPTURE = ["pc", "a0", "a1", "a2", "a3"]


# --------------------------------------------------------------------------
# Pure decoders (DuckStation-free; covered by the unit test)
# --------------------------------------------------------------------------
def decode_matrix_blob(raw: bytes, fixed: float = 4096.0) -> dict:
    """9 contiguous s16 (a RAM matrix blob) -> 3x3 float, row-major assumed.

    Row/col-major is AMBIGUOUS from bytes alone; the analyzer resolves it by
    agreement with the GTE RT (compare M and M^T). Returns status 'candidate'.
    """
    if len(raw) < 18:
        return {"status": "too short", "len": len(raw)}
    vals = struct.unpack_from("<9h", raw, 0)
    m = [[vals[r * 3 + c] / fixed for c in range(3)] for r in range(3)]
    return {"status": "candidate", "raw_s16": list(vals), "matrix_float": m,
            "fixed_point": "1.3.12 (/4096)", "layout_assumed": "row-major (verify vs GTE RT)"}


def decode_vec3_s32(raw: bytes) -> dict:
    if len(raw) < 12:
        return {"status": "too short", "len": len(raw)}
    x, y, z = struct.unpack_from("<3i", raw, 0)
    return {"status": "candidate", "xyz": [x, y, z]}


def world_view_from_hit(hit: dict) -> dict | None:
    """Pull (rotation, translation) out of a normalized renderer hit as a
    world->view candidate, with an orthonormality note (computed lazily here as
    column norms; the analyzer does the full check)."""
    rot = hit["decoded"].get("model_to_view_rotation")
    tr = hit["decoded"].get("translation")
    if not rot:
        return None
    return {"status": "candidate", "matrix_float": rot["matrix_float"],
            "col_norms": rot["column_norms_xyz"], "raw_s16": rot["raw_s16"],
            "translation": tr, "pointer": hit["decoded"].get("pointer")}


# --------------------------------------------------------------------------
# Live capture
# --------------------------------------------------------------------------
def _read(c, addr, n):
    return bytes.fromhex(c.call("debugger.readMemory", {"address": tt._hexaddr(addr), "length": n})["hex"])


def _collect(c, watch_id, limit_hits):
    out, offset = [], 0
    while True:
        params = {"offset": offset, "limit": 1000}
        if watch_id is not None:
            params["watch_id"] = watch_id
        res = c.call("execTrace.get", params)
        evs = res.get("events", []) if isinstance(res, dict) else []
        out.extend(evs)
        offset += len(evs)
        if not evs or (limit_hits and len(out) >= limit_hits):
            break
    return out[:limit_hits] if limit_hits else out


def _arm(c, pc, capture, max_events, warnings):
    """addWatch with GPR-only fallback on -32006 (bad capture name)."""
    try:
        wr = c.call("execTrace.addWatch", tt.addwatch_params(pc, capture, max_events))
        return wr.get("watch_id"), capture, False
    except Exception as exc:
        if "-32006" in str(exc) or "capture" in str(exc).lower():
            warnings.append(f"addWatch@{pc} rejected GTE capture ({exc}); GPR-only fallback.")
            wr = c.call("execTrace.addWatch", tt.addwatch_params(pc, tt.GPR_FALLBACK, max_events))
            return wr.get("watch_id"), tt.GPR_FALLBACK, True
        raise


def _read_candidate_matrices(c, args, warnings) -> tuple[list, list]:
    """Strategy B: direct reads of the vault's candidate RAM matrices/positions."""
    world_view, cam_pos = [], []
    if args.no_direct_reads:
        return world_view, cam_pos
    for label, addr in (("scratchpad@0x%08x" % args.scratch_mat, args.scratch_mat),
                        ("cam_struct@0x%08x+0x28" % args.cam_struct, args.cam_struct + 0x28)):
        try:
            raw = _read(c, addr, 18)
            d = decode_matrix_blob(raw)
            d.update({"source": label, "addr": "0x%08x" % addr, "raw_hex": raw.hex()})
            world_view.append(d)
        except Exception as exc:
            world_view.append({"source": label, "addr": "0x%08x" % addr,
                               "status": "rejected", "reason": f"read failed: {exc}"})
    for label, addr in (("scratchpad@0x%08x" % args.scratch_pos, args.scratch_pos),
                        ("cam_struct@0x%08x+0x4" % args.cam_struct, args.cam_struct + 0x4)):
        try:
            raw = _read(c, addr, 12)
            d = decode_vec3_s32(raw)
            d.update({"source": label, "addr": "0x%08x" % addr, "raw_hex": raw.hex()})
            cam_pos.append(d)
        except Exception as exc:
            cam_pos.append({"source": label, "addr": "0x%08x" % addr,
                            "status": "rejected", "reason": f"read failed: {exc}"})
    return world_view, cam_pos


def run_live(args) -> dict:
    c = tt.connect(args.host, args.port, args.token, args.timeout)
    warnings: list[str] = []
    try:
        status = c.call("debugger.status")
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"cannot reach debugger at {args.host}:{args.port}: {exc}")

    if args.state:
        warnings.append("loadState assumes the SAME disc is mounted as the state "
                        "was made on; a mismatch hard-crashes DuckStation.")
        c.call("emulator.loadState", {"path": args.state})
        for _ in range(max(args.settle, 0)):
            c.call("emulator.advanceFrames", {"frames": 1})

    c.call("execTrace.clear")
    world_wid, world_cap, world_fb = _arm(c, args.world_pc, CAM_CAPTURE, args.max_events, warnings)
    terr_wid, _, _ = _arm(c, args.terrain_pc, CAM_CAPTURE, args.max_events, warnings)
    setup_wid = None
    if not args.no_setup:
        setup_wid, _, _ = _arm(c, args.setup_pc, SETUP_CAPTURE, args.max_events, warnings)

    c.call("execTrace.run", {"frames": args.frames})

    world_hits = [tt.normalize_hit(e, requested=world_cap) for e in _collect(c, world_wid, args.limit_hits)]
    terr_hits = [tt.normalize_hit(e, requested=CAM_CAPTURE) for e in _collect(c, terr_wid, args.limit_hits)]

    # Strategy A -> world->view candidates from the world-space renderer GTE RT/TR
    world_view = []
    for h in world_hits:
        wv = world_view_from_hit(h)
        if wv:
            wv["source"] = "gte_rt@%s (world-space draw)" % args.world_pc
            world_view.append(wv)
            break   # one representative is enough; orthonormality is checked downstream
    if not world_view:
        warnings.append(f"no GTE rotation captured at world_pc {args.world_pc} "
                        "(fallback or no hits) -- relying on direct-read candidates.")

    # Strategy A2 -> locate the matrix in RAM via the setup leaf's a0/a1, then read it
    setup_candidates = []
    if setup_wid is not None:
        setup_hits = [tt.normalize_hit(e, requested=SETUP_CAPTURE) for e in _collect(c, setup_wid, 64)]
        seen = []
        for h in setup_hits:
            a0 = h["regs_int"].get("a0")
            a1 = h["regs_int"].get("a1")
            if a0 is None or a0 in seen:
                continue
            seen.append(a0)
            entry = {"source": "setup_leaf@%s" % args.setup_pc,
                     "a0_matrix_ptr": "0x%08x" % a0,
                     "a1_translation_ptr": ("0x%08x" % a1) if a1 else None, "status": "candidate"}
            if tt.RAM_LO <= a0 < tt.RAM_HI:
                try:
                    entry["matrix"] = decode_matrix_blob(_read(c, a0, 18))
                except Exception as exc:
                    entry["matrix"] = {"status": "rejected", "reason": str(exc)}
            if a1 and tt.RAM_LO <= a1 < tt.RAM_HI:
                try:
                    entry["translation"] = decode_vec3_s32(_read(c, a1, 12))
                except Exception as exc:
                    entry["translation"] = {"status": "rejected", "reason": str(exc)}
            setup_candidates.append(entry)
            if len(setup_candidates) >= 4:
                break

    # Strategy B -> direct reads of vault candidate matrices/positions
    direct_mats, direct_pos = _read_candidate_matrices(c, args, warnings)
    world_view.extend(direct_mats)
    world_view.extend(setup_candidates)

    # getGteState observed snapshot (decoded floats)
    try:
        gte_state = {"status": "observed", "value": c.call("debugger.getGteState", {})}
    except Exception as exc:
        gte_state = {"status": "unknown", "warning": str(exc)}

    # Strategy D -> Flik anchor
    anchors = {}
    try:
        fx, fy, fz = struct.unpack("<3i", _read(c, FLIK_POS_ADDR, 12))
        anchors["flik_world_pos"] = {"addr": "0x800a6500", "x": fx, "y": fy, "z": fz, "status": "observed"}
    except Exception as exc:
        anchors["flik_world_pos"] = {"addr": "0x800a6500", "status": "unknown", "warning": str(exc)}

    # Strategy C -> optional second-state diff (camera fields change; static don't)
    compare = None
    if args.compare_state:
        c.call("execTrace.clear")
        c.call("emulator.loadState", {"path": args.compare_state})
        for _ in range(max(args.settle, 0)):
            c.call("emulator.advanceFrames", {"frames": 1})
        cmp_mats, cmp_pos = _read_candidate_matrices(c, args, warnings)
        try:
            cmp_gte = c.call("debugger.getGteState", {})
        except Exception:
            cmp_gte = None
        compare = {"state": args.compare_state, "world_view_reads": cmp_mats,
                   "camera_pos_reads": cmp_pos, "gte_state": cmp_gte,
                   "note": "fields that DIFFER from the primary state are camera-dependent."}

    c.call("execTrace.clear")   # cleanup: remove watches, un-force interpreter

    return {
        "endpoint": {"host": args.host, "port": args.port},
        "debugger_status": status,
        "observed_trace_pcs": {"world_pc": args.world_pc, "terrain_pc": args.terrain_pc,
                               "setup_pc": None if args.no_setup else args.setup_pc},
        "world_view_candidates": world_view,
        "camera_pos_candidates": direct_pos,
        "terrain_model_view": {"pc": args.terrain_pc, "hits": terr_hits,
                               "note": "same camera pose as the world_view candidates"},
        "gte_state_snapshot": gte_state,
        "anchors": anchors,
        "compare_state": compare,
        "warnings": warnings,
    }


def _meta(args) -> dict:
    return {
        "tool": "trace_camera_transform", "version": VERSION,
        "disc_mutated": False, "guest_ram_written": False,
        "save_state": args.state, "frames_advanced": args.frames, "settle_frames": args.settle,
        "candidate_sources": {
            "world_renderer_pc": args.world_pc, "terrain_pc": args.terrain_pc,
            "setup_pc": None if args.no_setup else args.setup_pc,
            "scratchpad_matrix": "0x%08x" % args.scratch_mat,
            "scratchpad_camera_pos": "0x%08x" % args.scratch_pos,
            "cam_struct": "0x%08x" % args.cam_struct,
        },
        "remaining_unknowns": [
            "which candidate is the true world->view (resolved by mutual agreement + Flik cross-check)",
            "row- vs column-major of the RAM matrix blobs (resolved by agreement with GTE RT)",
            "an in-game spawn-camera eye/target RAM address (editor reconstructs it; none confirmed)",
        ],
        "next_step": "tools/analyze_terrain_transform.py <terrain_trace.json> --camera <this file>",
    }


def main(argv=None) -> int:
    repo = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=23460)
    ap.add_argument("--token", default=None)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--state", default=None, help="save-state to loadState first (SAME disc only)")
    ap.add_argument("--compare-state", default=None, help="2nd save-state for camera-field diff (Strategy C)")
    ap.add_argument("--settle", type=int, default=8)
    ap.add_argument("--frames", type=int, default=4)
    ap.add_argument("--limit-hits", type=int, default=None)
    ap.add_argument("--world-pc", default=WORLD_PC_CANDIDATE)
    ap.add_argument("--terrain-pc", default=TERRAIN_PC)
    ap.add_argument("--setup-pc", default=SETUP_PC_CANDIDATE)
    ap.add_argument("--no-setup", action="store_true", help="skip the setup-leaf trace")
    ap.add_argument("--no-direct-reads", action="store_true", help="skip scratchpad/struct reads")
    ap.add_argument("--scratch-mat", type=lambda s: int(s, 0), default=SCRATCH_MAT_CANDIDATE)
    ap.add_argument("--scratch-pos", type=lambda s: int(s, 0), default=SCRATCH_POS_CANDIDATE)
    ap.add_argument("--cam-struct", type=lambda s: int(s, 0), default=CAM_STRUCT_CANDIDATE)
    ap.add_argument("--max-events", type=int, default=10000)
    ap.add_argument("--out", default=str(repo / "logs" / "camera_transform_trace.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    report = _meta(args)
    if args.dry_run:
        report["mode"] = "dry-run (no emulator contacted)"
    else:
        report["mode"] = "live"
        report.update(run_live(args))

    out = Path(args.out)
    if not out.is_absolute():
        out = repo / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    print(f"[trace_camera_transform] mode={report['mode']}")
    print(f"  candidate sources: world_pc={args.world_pc} terrain_pc={args.terrain_pc} "
          f"setup_pc={'(skipped)' if args.no_setup else args.setup_pc}")
    if not args.dry_run:
        wv = report.get("world_view_candidates", [])
        print(f"  world->view candidates gathered: {len(wv)}")
        for c in wv[:6]:
            print(f"    - {c.get('source')}: norms={c.get('col_norms') or (c.get('matrix_float') and 'matrix')} status={c.get('status')}")
        print(f"  terrain model->view hits: {len(report.get('terrain_model_view', {}).get('hits', []))}")
        print(f"  Flik anchor: {report['anchors']['flik_world_pos']}")
        for w in report.get("warnings", []):
            print("  WARN:", w)
    print(f"  -> {out}")
    print("  NOTE: camera->world is NOT confirmed here; the analyzer cross-validates + cross-checks vs Flik.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
