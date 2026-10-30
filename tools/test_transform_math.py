#!/usr/bin/env python3
"""Unit tests for transform_math (pure linear algebra). No DuckStation.
Run: python3 tools/test_transform_math.py
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import transform_math as M  # noqa: E402


def _close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def _vclose(a, b, tol=1e-4):
    return all(_close(x, y, tol) for x, y in zip(a, b))


def _ry90():
    # rotation 90 deg about Y: orthonormal, det +1
    return [[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]]


def test_basic_ops():
    I = M.identity3()
    assert M.matvec3(I, [3, 4, 5]) == [3, 4, 5]
    assert M.transpose3([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
    assert M.matmul3(I, _ry90()) == _ry90()


def test_orthonormality_discriminates():
    rot = M.orthonormality(_ry90())
    assert rot["is_orthonormal"] and rot["ortho_error"] < 1e-6 and _close(rot["det"], 1.0)
    # a model-space RT carries scale (G33: norms ~1.569/1.0/1.046) -> NOT orthonormal
    scaled = [[1.569, 0, 0], [0, 1.0, 0], [0, 0, 1.046]]
    assert not M.orthonormality(scaled)["is_orthonormal"]


def test_invert_world_to_view_roundtrip():
    R, T = _ry90(), [10.0, 20.0, 30.0]
    inv = M.invert_world_to_view(R, T)
    p = [102.0, 202.0, 309.0]
    p_view = M.vec_add(M.matvec3(R, p), T)            # world->view
    back = M.vec_add(M.matvec3(inv["R_transpose"], p_view), inv["camera_world_pos"])
    assert _vclose(back, p), back


def test_terrain_vert_to_world_roundtrip():
    R, T = _ry90(), [10.0, 20.0, 30.0]
    Mmodel = [[2.0, 0, 0], [0, 1.0, 0], [0, 0, 3.0]]  # model->world rot+scale
    t = [100.0, 200.0, 300.0]                          # model origin in world
    RT_t = M.matmul3(R, Mmodel)                        # captured terrain RT = R*M
    TR_t = M.vec_add(M.matvec3(R, t), T)              # captured terrain TR = R*t + T
    inv = M.invert_world_to_view(R, T)
    v = [1.0, 2.0, 3.0]
    pw = M.terrain_vert_to_world(inv["R_transpose"], inv["camera_world_pos"], RT_t, TR_t, v)
    assert _vclose(pw, [102.0, 202.0, 309.0]), pw     # == M*v + t


def test_inverse3_general_and_singular():
    # general (non-orthonormal) matrix: inv(A)·A ≈ I
    A = [[1.584, 0.1, -0.2], [0.0, 1.012, 0.05], [0.3, -0.1, 1.013]]
    prod = M.matmul3(M.inverse3(A), A)
    assert M.frob_diff(prod, M.identity3()) < 1e-9
    # inverse of an orthonormal matrix equals its transpose
    Ri, Rt = M.inverse3(_ry90()), M.transpose3(_ry90())
    assert all(_close(Ri[r][c], Rt[r][c]) for r in range(3) for c in range(3))
    # singular -> None
    assert M.inverse3([[1, 2, 3], [2, 4, 6], [0, 0, 1]]) is None


def test_crosscheck_xz():
    near = [[6200, 0, 15500], [6000, 0, 15300]]
    far = [[0, 0, 0], [100000, 0, 100000]]
    assert M.crosscheck_xz(near, (6159, 15403), 2000.0)["passed"]
    assert not M.crosscheck_xz(far, (6159, 15403), 2000.0)["passed"]
    assert not M.crosscheck_xz([], (6159, 15403), 2000.0)["passed"]  # never a free pass


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
