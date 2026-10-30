#!/usr/bin/env python3
"""Pure 3x3 linear algebra for recovering camera->world and composing a
chunk 34/35 model->world candidate. No numpy, no DuckStation, no I/O — just math
that the analyzer and its unit tests share.

Frame conventions (PS1 GTE, 1.3.12 fixed = /4096):
  world->view:   p_view = R · p_world + T        (R = control.rotation, T = TR)
  At a WORLD-space draw (model = identity) the captured GTE RT = R and TR = T.
  At a MODEL-space draw the captured RT_t = R·M and TR_t = R·t + T, so for a
  model vertex v:   p_view = RT_t·v + TR_t = R·(M·v + t) + T.
  Therefore the model->world point is
      p_world = R^-1 · (p_view - T) = R^T · (RT_t·v + TR_t) + C,
  where (R orthonormal) R^-1 = R^T and the camera world position C = -R^T · T.

Everything is plain python lists: a 3x3 matrix is [[r,r,r],[r,r,r],[r,r,r]]
(row-major), a vector is [x, y, z].
"""
from __future__ import annotations

import math

Mat3 = list  # [[float]*3]*3
Vec3 = list   # [float]*3


def identity3() -> Mat3:
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def transpose3(m: Mat3) -> Mat3:
    return [[m[c][r] for c in range(3)] for r in range(3)]


def matvec3(m: Mat3, v: Vec3) -> Vec3:
    return [sum(m[r][c] * v[c] for c in range(3)) for r in range(3)]


def matmul3(a: Mat3, b: Mat3) -> Mat3:
    return [[sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]


def vec_add(a: Vec3, b: Vec3) -> Vec3:
    return [a[i] + b[i] for i in range(3)]


def vec_sub(a: Vec3, b: Vec3) -> Vec3:
    return [a[i] - b[i] for i in range(3)]


def vec_scale(v: Vec3, s: float) -> Vec3:
    return [x * s for x in v]


def det3(m: Mat3) -> float:
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def col_norms(m: Mat3) -> Vec3:
    return [math.sqrt(sum(m[r][c] ** 2 for r in range(3))) for c in range(3)]


def frob_diff(a: Mat3, b: Mat3) -> float:
    return math.sqrt(sum((a[r][c] - b[r][c]) ** 2 for r in range(3) for c in range(3)))


def orthonormality(m: Mat3) -> dict:
    """How close m is to a pure rotation: ||m^T·m - I|| (0 = perfect), det, norms.

    A world->view rotation is orthonormal (norms ~1, det ~+1). A model-space RT
    (R·M with scale) is NOT — this is the discriminator for picking the camera.
    """
    mt_m = matmul3(transpose3(m), m)
    err = frob_diff(mt_m, identity3())
    d = det3(m)
    return {"ortho_error": err, "det": d, "col_norms": col_norms(m),
            "is_orthonormal": err < 0.06 and abs(abs(d) - 1.0) < 0.06}


def inverse3(m: Mat3):
    """General 3x3 inverse (adjugate/det). Returns None if singular.

    Needed because the live LEVEL01 camera matrix is NOT orthonormal (it bakes in
    non-uniform scale, det != 1), so the R^T shortcut in invert_world_to_view is
    invalid for it.
    """
    d = det3(m)
    if abs(d) < 1e-12:
        return None
    cof = [
        [(m[1][1] * m[2][2] - m[1][2] * m[2][1]), -(m[1][0] * m[2][2] - m[1][2] * m[2][0]),
         (m[1][0] * m[2][1] - m[1][1] * m[2][0])],
        [-(m[0][1] * m[2][2] - m[0][2] * m[2][1]), (m[0][0] * m[2][2] - m[0][2] * m[2][0]),
         -(m[0][0] * m[2][1] - m[0][1] * m[2][0])],
        [(m[0][1] * m[1][2] - m[0][2] * m[1][1]), -(m[0][0] * m[1][2] - m[0][2] * m[1][0]),
         (m[0][0] * m[1][1] - m[0][1] * m[1][0])],
    ]
    adj = transpose3(cof)
    return [[adj[r][c] / d for c in range(3)] for r in range(3)]


def invert_world_to_view(R: Mat3, T: Vec3) -> dict:
    """world->view (R,T) -> camera->world: R^T and eye C = -R^T·T.

    Assumes R orthonormal (true for a real camera rotation). Returns the pieces
    needed to map view-space back to world-space; the caller should first verify
    orthonormality(R)['is_orthonormal'].
    """
    Rt = transpose3(R)
    C = vec_scale(matvec3(Rt, T), -1.0)
    return {"R_transpose": Rt, "camera_world_pos": C, "assumes_orthonormal": True}


def terrain_vert_to_world(Rt: Mat3, C: Vec3, RT_t: Mat3, TR_t: Vec3, v_model: Vec3) -> Vec3:
    """Model-space terrain vertex -> world: R^T·(RT_t·v + TR_t) + C."""
    view = vec_add(matvec3(RT_t, v_model), TR_t)
    return vec_add(matvec3(Rt, view), C)


def _median(xs: list) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def crosscheck_xz(points: list, anchor_xz, thresh: float) -> dict:
    """Do the reconstructed world points cluster near the anchor (Flik) in XZ?

    This is the reproducible gate: terrain verts should land near Flik's spawn
    (X,Z). Returns the median XZ distance, the fraction within `thresh`, and a
    boolean `passed`. With no points it returns passed=False (never a free pass).
    """
    ax, az = anchor_xz
    dists = [math.hypot(p[0] - ax, p[2] - az) for p in points]
    if not dists:
        return {"status": "no points", "passed": False}
    within = sum(1 for d in dists if d <= thresh)
    return {"median_xz_dist": _median(dists), "min_xz_dist": min(dists),
            "max_xz_dist": max(dists), "frac_within_thresh": within / len(dists),
            "thresh": thresh, "n": len(dists),
            "passed": _median(dists) <= thresh}
