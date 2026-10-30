#!/usr/bin/env python3
"""Turn a trace_terrain_transform JSON into a CANDIDATE chunk 34/35 transform.

This is the smallest follow-up to the trace. It is deliberately conservative:
it reports model->VIEW (rotation + translation + per-axis scale) and identifies
which on-disk chunk the live buffer matches, but it DOES NOT and CANNOT produce
an absolute model->world placement yet — that needs the camera->world transform,
which the trace flags as unknown. Nothing here is baked into the editor.

Run:
    python3 tools/analyze_terrain_transform.py logs/terrain_transform_trace.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import transform_math as TM  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "tools" / "LEVEL_RAW_decompressed" / "LEVEL.RAW.decompressed"
IDX = REPO / "tools" / "LEVEL_RAW_decompressed" / "chunk_index.json"


def _chunk_offsets():
    items = json.loads(IDX.read_text())
    items = items if isinstance(items, list) else items.get("chunks", items)
    out = {}
    if isinstance(items, list):
        for c in items:
            n = c.get("chunk", c.get("index"))
            out[int(n)] = c.get("decomp_off")
    return out


def _byte_match(sample_hex: str, chunk_off: int, n: int) -> int:
    """Count equal bytes between a buffer sample and a chunk's decompressed head."""
    if chunk_off is None or not RAW.exists():
        return -1
    sample = bytes.fromhex(sample_hex)[:n]
    disk = RAW.read_bytes()[chunk_off:chunk_off + len(sample)]
    return sum(1 for a, b in zip(sample, disk) if a == b)


def select_world_to_view(camera: dict) -> dict:
    """Pick a verified world->view (R,T) from the camera-trace candidates.

    Prefers the GTE RT/TR captured at the world-space renderer (unambiguous and
    self-consistent). Uses the direct-read scratchpad matrix + camera pos as
    INDEPENDENT cross-validation (matrix agreement, and C == -R^T·T). Returns
    status 'selected' with {R,T,source,ortho,...} or 'none' (-> BLOCKED), never a
    free pass. Pure: takes the parsed camera dict.
    """
    cands = camera.get("world_view_candidates", []) or []
    pos_cands = camera.get("camera_pos_candidates", []) or []
    reasons = []

    gte = next((c for c in cands if str(c.get("source", "")).startswith("gte_rt")
                and c.get("matrix_float") and c.get("translation")), None)
    scratch_mat = next((c for c in cands if "scratchpad" in str(c.get("source", ""))
                        and c.get("matrix_float")), None)
    scratch_pos = next((c for c in pos_cands if "scratchpad" in str(c.get("source", ""))
                        and c.get("xyz")), None)

    chosen = None
    if gte:
        R = gte["matrix_float"]
        tr = gte["translation"]
        T = [tr["trx"], tr["try"], tr["trz"]]
        o = TM.orthonormality(R)
        if o["is_orthonormal"]:
            chosen = {"R": R, "T": T, "source": gte["source"], "ortho": o}
            reasons.append("GTE world-space RT is orthonormal -> used as world->view.")
        else:
            reasons.append(f"GTE RT not orthonormal (err={o['ortho_error']:.3f}); not world-space?")
    if chosen is None and scratch_mat and scratch_pos:
        # fall back to scratchpad: T = -R·C  (layout ambiguous w/o GTE -> warn)
        R = scratch_mat["matrix_float"]
        o, ot = TM.orthonormality(R), TM.orthonormality(TM.transpose3(R))
        Ruse = R if o["ortho_error"] <= ot["ortho_error"] else TM.transpose3(R)
        ouse = TM.orthonormality(Ruse)
        if ouse["is_orthonormal"]:
            C = [float(v) for v in scratch_pos["xyz"]]
            T = TM.vec_scale(TM.matvec3(Ruse, C), -1.0)
            chosen = {"R": Ruse, "T": T, "source": scratch_mat["source"] + " + " + scratch_pos["source"],
                      "ortho": ouse, "note": "row/col-major ambiguous without GTE; verify."}
            reasons.append("fell back to scratchpad matrix + camera pos (no usable GTE RT).")

    # cross-validation: does the scratchpad matrix agree with the chosen R?
    agreement = None
    if chosen and scratch_mat:
        Rs = scratch_mat["matrix_float"]
        d_direct = TM.frob_diff(chosen["R"], Rs)
        d_transp = TM.frob_diff(chosen["R"], TM.transpose3(Rs))
        agreement = {"scratchpad_vs_chosen_frob": round(min(d_direct, d_transp), 4),
                     "layout": ("same" if d_direct <= d_transp else "transposed"),
                     "agrees": min(d_direct, d_transp) < 0.06}
        reasons.append(f"scratchpad matrix {'agrees' if agreement['agrees'] else 'DISAGREES'} "
                       f"with chosen R (frob={agreement['scratchpad_vs_chosen_frob']}).")
    # cross-validation: predicted camera pos C == read scratchpad pos?
    pos_check = None
    if chosen and scratch_pos:
        C_pred = TM.invert_world_to_view(chosen["R"], chosen["T"])["camera_world_pos"]
        C_read = [float(v) for v in scratch_pos["xyz"]]
        pos_check = {"C_predicted": [round(x, 1) for x in C_pred], "C_read": C_read,
                     "dist": round(TM.crosscheck_xz([[C_pred[0], 0, C_pred[2]]],
                                                    (C_read[0], C_read[2]), 1e18)["min_xz_dist"], 1)}

    if chosen is None:
        return {"status": "none", "reasons": reasons or ["no orthonormal world->view candidate"]}
    return {"status": "selected", "chosen": chosen, "agreement": agreement,
            "camera_pos_check": pos_check, "reasons": reasons}


def compose_model_world(R, T, terrain_hits: list, flik, thresh: float) -> dict:
    """Compose model->view (per terrain hit) with world->view^-1 -> world verts,
    then cross-check they cluster near Flik in XZ. Pure."""
    inv = TM.invert_world_to_view(R, T)
    Rt, C = inv["R_transpose"], inv["camera_world_pos"]
    world_verts = []
    for h in terrain_hits or []:
        rot = h.get("decoded", {}).get("model_to_view_rotation")
        tr = h.get("decoded", {}).get("translation")
        verts = h.get("decoded", {}).get("input_verts") or []
        if not rot or not tr or not verts:
            continue
        RT_t, TR_t = rot["matrix_float"], [tr["trx"], tr["try"], tr["trz"]]
        for v in verts:
            world_verts.append(TM.terrain_vert_to_world(Rt, C, RT_t, TR_t, [v["x"], v["y"], v["z"]]))
    if not world_verts:
        return {"status": "blocked", "reason": "no terrain verts (need RT_t + TR_t + input_verts)",
                "camera_world_pos": [round(x, 1) for x in C]}
    cc = TM.crosscheck_xz(world_verts, (flik[0], flik[2]), thresh)
    return {"status": "candidate_passed" if cc["passed"] else "rejected",
            "camera_world_pos": [round(x, 1) for x in C], "n_world_verts": len(world_verts),
            "crosscheck_vs_flik": cc,
            "sample_world_verts": [[round(c, 1) for c in p] for p in world_verts[:5]]}


def geometry_kind(terrain_hits: list) -> dict:
    """Classify the captured GTE geometry as terrain-like (wide ground plane) vs a
    compact model (B7: 0x8012c1d0 can hold Flik's model instead of terrain).

    Terrain quads spread widely in XZ and sit near the ground; a character model
    is compact and y-offset. This flags when 0x80017464 is NOT drawing chunk 34/35.
    """
    vs = [v for h in terrain_hits or [] for v in (h.get("decoded", {}).get("input_verts") or [])]
    if not vs:
        return {"kind": "unknown", "reason": "no input verts captured", "n_verts": 0}
    xs = [v["x"] for v in vs]; ys = [v["y"] for v in vs]; zs = [v["z"] for v in vs]
    xz_extent = max(max(xs) - min(xs), max(zs) - min(zs))
    y_mean = sum(ys) / len(ys)
    if xz_extent < 1500 and abs(y_mean) > 100:
        kind = "compact_model_like"
        reason = (f"XZ extent {xz_extent} small and |y_mean| {abs(y_mean):.0f} offset -> a compact "
                  "model (B7: likely Flik's FLICK.ALL in the 0x8012c1d0 buffer), NOT chunk 34/35 terrain")
    elif xz_extent >= 3000:
        kind = "terrain_like"
        reason = f"XZ extent {xz_extent} wide -> ground-plane geometry"
    else:
        kind = "ambiguous"
        reason = f"XZ extent {xz_extent}, y_mean {y_mean:.0f} -> inconclusive"
    return {"kind": kind, "reason": reason, "n_verts": len(vs),
            "xz_extent": xz_extent, "y_mean": round(y_mean, 1)}


def general_camera_route(camera: dict, terrain_hits: list, flik, thresh: float) -> dict:
    """Fallback when no ORTHONORMAL world->view exists: the live LEVEL01 camera
    matrix is non-orthonormal, so use a GENERAL inverse of the verified scratchpad
    matrix (0x1f8003b4) + the read camera pos (0x1f800374). Tries both byte layouts
    and keeps the one with the best Flik cross-check. Still gated by the cross-check.
    """
    mat = next((c for c in camera.get("world_view_candidates", []) or []
                if "scratchpad" in str(c.get("source", "")) and c.get("matrix_float")), None)
    pos = next((c for c in camera.get("camera_pos_candidates", []) or []
                if "scratchpad" in str(c.get("source", "")) and c.get("xyz")), None)
    if not mat or not pos:
        return {"status": "no_scratchpad", "reason": "no scratchpad matrix + camera pos to invert"}
    R = mat["matrix_float"]; C = [float(v) for v in pos["xyz"]]
    best = None
    for layout, name in ((R, "row-major"), (TM.transpose3(R), "col-major")):
        Rinv = TM.inverse3(layout)
        if Rinv is None:
            continue
        wv = []
        for h in terrain_hits or []:
            rot = h.get("decoded", {}).get("model_to_view_rotation")
            tr = h.get("decoded", {}).get("translation")
            for v in h.get("decoded", {}).get("input_verts") or []:
                if rot and tr:
                    wv.append(TM.terrain_vert_to_world(Rinv, C, rot["matrix_float"],
                              [tr["trx"], tr["try"], tr["trz"]], [v["x"], v["y"], v["z"]]))
        if not wv:
            continue
        cc = TM.crosscheck_xz(wv, (flik[0], flik[2]), thresh)
        if best is None or cc["median_xz_dist"] < best["crosscheck_vs_flik"]["median_xz_dist"]:
            best = {"layout": name, "crosscheck_vs_flik": cc,
                    "sample_world_verts": [[round(c, 1) for c in p] for p in wv[:5]]}
    if best is None:
        return {"status": "no_verts", "reason": "scratchpad matrix singular or no terrain verts"}
    return {"status": "computed", "camera_world_pos": [round(x, 1) for x in C],
            "method": "general inverse of scratchpad matrix 0x1f8003b4 + camera pos 0x1f800374",
            "matrix_orthonormality": TM.orthonormality(R), **best}


def analyze_camera(terrain: dict, camera: dict, thresh: float) -> dict:
    """Full model->world attempt. SOLVED only with a reproducible Flik cross-check;
    otherwise BLOCKED/REJECTED with the precise reason (incl. the B7 model-vs-terrain
    check, which is the decisive gate when 0x80017464 isn't drawing chunk 34/35)."""
    flik = (camera.get("anchors", {}) or {}).get("flik_world_pos") \
        or terrain.get("anchors", {}).get("flik_world_pos")
    terrain_hits = (camera.get("terrain_model_view", {}) or {}).get("hits") or terrain.get("hits") or []
    gkind = geometry_kind(terrain_hits)
    sel = select_world_to_view(camera)

    if sel["status"] == "selected" and flik and "x" in flik:
        comp = compose_model_world(sel["chosen"]["R"], sel["chosen"]["T"], terrain_hits,
                                   (flik["x"], flik["y"], flik["z"]), thresh)
        comp["world_view_route"] = "orthonormal (R^T inverse)"
    elif flik and "x" in flik:
        comp = general_camera_route(camera, terrain_hits, (flik["x"], flik["y"], flik["z"]), thresh)
    else:
        comp = {"status": "no_anchor"}

    # decide status — geometry kind is the decisive gate (can't validate terrain
    # from a buffer that holds a character model), then the Flik cross-check.
    if not flik or "x" not in flik:
        status = "BLOCKED — no Flik world anchor to cross-check against"
    elif gkind["kind"] == "compact_model_like":
        status = ("BLOCKED — 0x80017464 buffer is a COMPACT MODEL (B7: likely Flik), NOT chunk 34/35 "
                  "terrain; re-capture at a pose where the terrain renderer emits wide ground verts")
    elif comp.get("status") in ("no_scratchpad", "no_verts", "no_anchor", "blocked"):
        status = f"BLOCKED — camera->world not usable ({comp.get('reason', comp.get('status'))})"
    elif comp.get("crosscheck_vs_flik", {}).get("passed"):
        status = "SOLVED — model->world cross-check PASSED near Flik (still NOT BAKED, NOT PLACED)"
    else:
        cc = comp.get("crosscheck_vs_flik", {})
        status = (f"REJECTED — terrain verts cluster {cc.get('median_xz_dist', '?'):.0f} from Flik "
                  f"(> thresh {thresh:.0f}); camera/composition/anchor wrong" if cc else
                  "REJECTED — composition produced no usable cross-check")
    return {"status": status, "geometry_kind": gkind, "world_view_selection": sel,
            "composition": comp, "flik_anchor": flik,
            "do_not": ["bake constants", "place chunk 34/35 in the editor"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace", help="path to terrain_transform_trace.json")
    ap.add_argument("--camera", default=None, help="camera_transform_trace.json (enables model->world attempt)")
    ap.add_argument("--thresh", type=float, default=80000.0,
                    help="XZ cross-check radius in RUNTIME units (~file<<5); default 80000 (~2500 file)")
    ap.add_argument("--out", default=None, help="write candidate JSON here")
    args = ap.parse_args(argv)

    rep = json.loads(Path(args.trace).read_text())
    hits = rep.get("hits", [])
    print(f"[analyze] {args.trace}: {len(hits)} hits, pc={rep.get('trace_pc')}")
    if not hits and not args.camera:
        print("  no hits — run the trace against a LIVE instance at the spawn first:")
        print("    tools/trace_terrain_transform.py --port 23460 --state <spawn>.sav")
        return 0
    if not hits:
        print("  (terrain trace empty; will use the camera trace's terrain_model_view if present)")

    # 1) which register is the source pointer, and where it points
    ptr_regs = Counter(h["decoded"]["pointer"].get("reg")
                       for h in hits if h["decoded"]["pointer"].get("status") == "observed")
    ptr_vals = sorted({h["decoded"]["pointer"]["value_hex"]
                       for h in hits if h["decoded"]["pointer"].get("status") == "observed"})
    print(f"  source-pointer register(s): {dict(ptr_regs) or 'NONE in terrain buffer (investigate)'}")
    print(f"  distinct pointer values: {ptr_vals[:8]}{' …' if len(ptr_vals) > 8 else ''}")

    # 2) chunk identity: match a buffer sample to chunk 34 vs 35 on disk
    chunk_id = {"status": "unknown"}
    samples = [s for s in rep.get("buffer_samples", []) if s.get("hex")]
    if samples:
        offs = _chunk_offsets()
        n = len(bytes.fromhex(samples[0]["hex"]))
        m34 = _byte_match(samples[0]["hex"], offs.get(34), n)
        m35 = _byte_match(samples[0]["hex"], offs.get(35), n)
        chunk_id = {"bytes_compared": n, "match_chunk34": m34, "match_chunk35": m35,
                    "best": ("chunk35" if m35 >= m34 else "chunk34"),
                    "caveat": "live buffer is decompressed/possibly transformed; "
                              "a low match may mean it holds Flik's model, not terrain (B7)."}
        print(f"  chunk identity (byte match /{n}): chunk34={m34} chunk35={m35} -> {chunk_id['best']}")
    else:
        print("  chunk identity: no buffer samples in trace (re-run trace with samples)")

    # 3) model->view rotation/translation/scale (G33 expected Y-scale ~= 1.0)
    rot = next((h["decoded"]["model_to_view_rotation"] for h in hits
                if h["decoded"]["model_to_view_rotation"]), None)
    tr = next((h["decoded"]["translation"] for h in hits if h["decoded"]["translation"]), None)
    if rot:
        nx, ny, nz = rot["column_norms_xyz"]
        print(f"  model->view rotation captured. per-axis scale (col norms) = "
              f"X {nx}  Y {ny}  Z {nz}   (G33 expects Y~=1.0)")
    else:
        print("  model->view rotation: NOT captured (GTE capture missing — check fallback)")
    if tr:
        print(f"  translation (view space): {tr}")

    candidate = {
        "tool": "analyze_terrain_transform",
        "source_trace": str(args.trace),
        "status": "PARTIAL — model->VIEW only; NOT solved, NOT baked, NOT placed",
        "source_pointer_register": dict(ptr_regs),
        "pointer_values": ptr_vals,
        "chunk_identity": chunk_id,
        "model_to_view": {"rotation": rot, "translation": tr,
                          "per_axis_scale_from_col_norms": rot["column_norms_xyz"] if rot else None},
        "flik_anchor": rep.get("anchors", {}).get("flik_world_pos"),
        "blocked_on": [
            "camera->world (view^-1): world = inv(view) · view_space; RAM address unknown.",
            "cross-check: push a captured input vert through the full model->world and "
            "confirm its XZ lands near Flik (6159,15403) and Y near nearby grain.",
        ],
        "do_not": ["bake constants", "place chunk 34/35 in the editor"],
    }

    # --- model->world attempt (only when a camera trace is supplied) ---
    if args.camera:
        camera = json.loads(Path(args.camera).read_text())
        cam = analyze_camera(rep, camera, args.thresh)
        candidate["camera_to_world"] = cam
        candidate["status"] = cam["status"]
        sel = cam.get("world_view_selection", {})
        print(f"\n  [camera] {args.camera}")
        for r in sel.get("reasons", []):
            print(f"    - {r}")
        if cam.get("composition"):
            comp = cam["composition"]
            cc = comp.get("crosscheck_vs_flik", {})
            print(f"    camera world pos: {comp.get('camera_world_pos')}")
            print(f"    terrain verts cross-check vs Flik: median_xz={cc.get('median_xz_dist')} "
                  f"thresh={cc.get('thresh')} passed={cc.get('passed')} "
                  f"(n={comp.get('n_world_verts') or cc.get('n')})")
            print(f"    geometry_kind: {cam['geometry_kind']['kind']} — {cam['geometry_kind']['reason']}")
        print(f"  STATUS: {cam['status']}")

    out = Path(args.out) if args.out else (REPO / "logs" / "terrain_transform_candidate.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(candidate, indent=2))
    print(f"  -> {out}")
    if not args.camera:
        print("  CONCLUSION: model->view recovered; model->WORLD still BLOCKED on camera->world "
              "(supply --camera <camera_transform_trace.json> to attempt it).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
