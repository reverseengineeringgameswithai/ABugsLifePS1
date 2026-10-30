#!/usr/bin/env python3
"""Unit tests for trace_camera_transform decode + analyze_terrain_transform's
camera->world / model->world logic. No DuckStation, no network, no files needed.
Run: python3 tools/test_camera_transform.py
"""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import trace_camera_transform as TC   # noqa: E402
import analyze_terrain_transform as AZ  # noqa: E402
import transform_math as TM            # noqa: E402

RY90 = [[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]]   # orthonormal


# ---- camera tool decoders ----
def test_decode_matrix_blob_identity():
    raw = struct.pack("<9h", 4096, 0, 0, 0, 4096, 0, 0, 0, 4096)
    d = TC.decode_matrix_blob(raw)
    assert d["status"] == "candidate"
    assert d["matrix_float"] == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def test_decode_vec3_s32():
    raw = struct.pack("<3i", 6159, 85, 15403)
    assert TC.decode_vec3_s32(raw)["xyz"] == [6159, 85, 15403]


def test_world_view_from_hit():
    import trace_terrain_transform as tt
    gte = {"RT_0": "0x00001000", "RT_1": "0x00000000", "RT_2": "0x00001000",
           "RT_3": "0x00000000", "RT_4": "0x00001000",
           "TRX": "0x0000000a", "TRY": "0x00000014", "TRZ": "0x0000001e"}
    hit = tt.normalize_hit({"frame": 1, "pc": "0x80010718",
                            "regs": {"pc": "0x80010718", "a0": "0x801790c8"}, "gte": gte})
    wv = TC.world_view_from_hit(hit)
    assert wv is not None and wv["status"] == "candidate"
    assert wv["matrix_float"][1][1] == 1.0
    assert wv["translation"]["trx"] == 10 and wv["translation"]["trz"] == 30


# ---- analyzer: candidate selection ----
def _gte_cand(R, T, source="gte_rt@0x80010718"):
    return {"source": source, "matrix_float": R, "status": "candidate",
            "col_norms": TM.col_norms(R),
            "translation": {"trx": T[0], "try": T[1], "trz": T[2]}}


def test_select_prefers_orthonormal_gte():
    cam = {"world_view_candidates": [_gte_cand(RY90, [10, 20, 30])]}
    sel = AZ.select_world_to_view(cam)
    assert sel["status"] == "selected"
    assert sel["chosen"]["R"] == RY90 and sel["chosen"]["T"] == [10, 20, 30]


def test_select_none_when_not_orthonormal_and_no_scratch():
    scaled = [[1.569, 0, 0], [0, 1.0, 0], [0, 0, 1.046]]
    cam = {"world_view_candidates": [_gte_cand(scaled, [1, 2, 3])]}
    assert AZ.select_world_to_view(cam)["status"] == "none"


def test_select_agreement_with_scratchpad():
    cam = {"world_view_candidates": [
        _gte_cand(RY90, [10, 20, 30]),
        {"source": "scratchpad@0x1f8003b4", "matrix_float": RY90, "status": "candidate"}]}
    sel = AZ.select_world_to_view(cam)
    assert sel["agreement"]["agrees"] is True
    assert sel["agreement"]["scratchpad_vs_chosen_frob"] < 1e-6


# ---- analyzer: composition + cross-check ----
def _terrain_hit(R, M, t, T, v):
    RT_t = TM.matmul3(R, M)
    TR_t = TM.vec_add(TM.matvec3(R, t), T)
    return {"decoded": {"model_to_view_rotation": {"matrix_float": RT_t},
                        "translation": {"trx": TR_t[0], "try": TR_t[1], "trz": TR_t[2]},
                        "input_verts": [{"v": 0, "x": v[0], "y": v[1], "z": v[2]}]}}


def _camera_with_terrain(R, T, t):
    M = TM.identity3()
    hit = _terrain_hit(R, M, t, T, [10, 5, 10])    # world = t + [10,5,10]
    return {"world_view_candidates": [_gte_cand(R, T)],
            "terrain_model_view": {"hits": [hit]},
            "anchors": {"flik_world_pos": {"x": 6159, "y": 85, "z": 15403}}}


def test_compose_passes_when_near_flik():
    cam = _camera_with_terrain(RY90, [10, 20, 30], [6159, 85, 15403])
    res = AZ.analyze_camera({}, cam, thresh=2000.0)
    assert res["status"].startswith("SOLVED"), res["status"]
    assert res["composition"]["crosscheck_vs_flik"]["passed"] is True


def test_compose_rejected_when_far_from_flik():
    cam = _camera_with_terrain(RY90, [10, 20, 30], [100000, 0, 100000])
    res = AZ.analyze_camera({}, cam, thresh=2000.0)
    assert res["status"].startswith("REJECTED"), res["status"]


def test_blocked_without_camera_candidate():
    cam = {"world_view_candidates": [], "anchors": {"flik_world_pos": {"x": 1, "y": 2, "z": 3}}}
    assert AZ.analyze_camera({}, cam, thresh=2000.0)["status"].startswith("BLOCKED")


def test_refuses_solved_without_crosscheck():
    # camera recovered, but the terrain hit has NO input verts -> cannot cross-check
    bad_hit = {"decoded": {"model_to_view_rotation": {"matrix_float": RY90},
                           "translation": {"trx": 0, "try": 0, "trz": 0}, "input_verts": []}}
    cam = {"world_view_candidates": [_gte_cand(RY90, [10, 20, 30])],
           "terrain_model_view": {"hits": [bad_hit]},
           "anchors": {"flik_world_pos": {"x": 6159, "y": 85, "z": 15403}}}
    res = AZ.analyze_camera({}, cam, thresh=2000.0)
    assert res["status"].startswith("BLOCKED"), res["status"]
    assert "CANDIDATE" not in res["status"]


def test_geometry_kind_detects_compact_model():
    # compact, y-offset verts (like Flik's model) -> compact_model_like (B7)
    model_hits = [{"decoded": {"input_verts": [{"x": 18, "y": -310, "z": 36},
                                               {"x": -35, "y": -285, "z": 18}]}}]
    assert AZ.geometry_kind(model_hits)["kind"] == "compact_model_like"
    # wide XZ spread -> terrain_like
    terr_hits = [{"decoded": {"input_verts": [{"x": -4000, "y": 0, "z": -4000},
                                              {"x": 4000, "y": 0, "z": 4000}]}}]
    assert AZ.geometry_kind(terr_hits)["kind"] == "terrain_like"
    assert AZ.geometry_kind([])["kind"] == "unknown"


def test_general_route_uses_nonorthonormal_scratchpad():
    # non-orthonormal scratchpad matrix + camera pos -> general inverse composes
    scaled = [[1.584, 0.0, 0.0], [0.0, 1.012, 0.0], [0.0, 0.0, 1.013]]
    cam = {"world_view_candidates": [{"source": "scratchpad@0x1f8003b4", "matrix_float": scaled,
                                      "status": "candidate"}],
           "camera_pos_candidates": [{"source": "scratchpad@0x1f800374", "xyz": [0, 0, 0],
                                      "status": "candidate"}]}
    hit = {"decoded": {"model_to_view_rotation": {"matrix_float": scaled},
                       "translation": {"trx": 0, "try": 0, "trz": 0},
                       "input_verts": [{"x": 100, "y": 0, "z": 200}]}}
    res = AZ.general_camera_route(cam, [hit], (100, 0, 200), 50.0)
    assert res["status"] == "computed"
    # scaled·v then inverse·that == v -> world ≈ the model vert (near anchor)
    assert res["crosscheck_vs_flik"]["passed"] is True


def test_compact_model_forces_blocked_even_with_camera():
    # camera recoverable, but geometry is a compact model -> must BLOCK (B7), not SOLVE
    scaled = [[1.584, 0.0, 0.0], [0.0, 1.012, 0.0], [0.0, 0.0, 1.013]]
    model_hit = {"decoded": {"model_to_view_rotation": {"matrix_float": scaled},
                             "translation": {"trx": 0, "try": 0, "trz": 0},
                             "input_verts": [{"x": 10, "y": -300, "z": 10}]}}
    cam = {"world_view_candidates": [{"source": "scratchpad@0x1f8003b4", "matrix_float": scaled,
                                      "status": "candidate"}],
           "camera_pos_candidates": [{"source": "scratchpad@0x1f800374", "xyz": [0, 0, 0],
                                      "status": "candidate"}],
           "terrain_model_view": {"hits": [model_hit]},
           "anchors": {"flik_world_pos": {"x": 6159, "y": 85, "z": 15403}}}
    res = AZ.analyze_camera({}, cam, thresh=2000.0)
    assert res["status"].startswith("BLOCKED"), res["status"]
    assert "B7" in res["status"] or "COMPACT MODEL" in res["status"]


def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc!r}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
