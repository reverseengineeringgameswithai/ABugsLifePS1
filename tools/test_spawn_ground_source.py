#!/usr/bin/env python3
"""Unit tests for trace_spawn_ground_source pure analysis (no DuckStation).
Run: python3 tools/test_spawn_ground_source.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import trace_spawn_ground_source as S  # noqa: E402
import transform_math as TM            # noqa: E402

FLIK = [6159, 85, 15403]
I3 = TM.identity3()


def _hit(verts, a0=0x80178590, rt=None, tr=(0, 0, 0)):
    return {"regs_int": {"a0": a0},
            "decoded": {"model_to_view_rotation": {"matrix_float": rt or I3},
                        "translation": {"trx": tr[0], "try": tr[1], "trz": tr[2]},
                        "input_verts": [{"x": v[0], "y": v[1], "z": v[2]} for v in verts]}}


def test_classify_terrain_like_near_spawn():
    # wide world-space verts (R=identity, C=Flik) -> wide extent, near Flik
    wide = [_hit([(-25000, 0, -25000), (25000, 0, 25000),
                  (25000, 0, -25000), (-25000, 0, 25000)])]
    p = S.classify_pc("0x80019684", "bulk ground", wide, I3, list(FLIK), FLIK,
                      thresh=80000.0, min_xz_extent=20000.0)
    assert p["geometry_kind"]["kind"] == "terrain_like", p["geometry_kind"]
    assert p["world"]["near_flik"] is True
    assert p["label"] == "terrain_like_near_spawn", p["label"]
    assert any("a0=0x80178590" in s for s, _ in p["top_source_pointers"])


def test_classify_compact_model():
    compact = [_hit([(18, -310, 36), (-18, -310, 36), (-25, -299, 70)])]
    p = S.classify_pc("0x80017464", "flik renderer", compact, I3, list(FLIK), FLIK,
                      thresh=80000.0, min_xz_extent=20000.0)
    assert p["geometry_kind"]["kind"] == "compact_model_like"
    assert p["label"] == "compact_model"


def test_rank_dat_source_found_rejects_chunk():
    per_pc = [
        {"pc": "0x80019684", "label": "terrain_like_near_spawn", "role": "DAT bulk ground"},
        {"pc": "0x80017464", "label": "compact_model", "role": "flik"},
    ]
    r = S.rank_spawn_sources(per_pc)
    assert r["status"] == "SOURCE_FOUND"
    assert "DAT" in r["source"]
    assert "REJECTED_CHUNK34_35_AS_SPAWN_FLOOR" in r["flags"]
    assert "DAT_COVERAGE_BUG_SUSPECTED" in r["flags"]
    assert r["winner_pc"] == "0x80019684"


def test_rank_chunk_source_found():
    per_pc = [{"pc": "0x80017464", "label": "terrain_like_near_spawn", "role": "chunk35"}]
    r = S.rank_spawn_sources(per_pc)
    assert r["status"] == "SOURCE_FOUND"
    assert "chunk 34/35" in r["source"]


def test_rank_blocked_when_only_compact():
    per_pc = [{"pc": "0x80017464", "label": "compact_model", "role": "flik"},
              {"pc": "0x80010718", "label": "compact_model", "role": "dat"}]
    r = S.rank_spawn_sources(per_pc)
    assert r["status"] == "BLOCKED"
    assert any("compact-model" in f for f in r["flags"])


def test_rank_partial():
    per_pc = [{"pc": "0x80010718", "label": "terrain_like_elsewhere", "role": "dat"}]
    assert S.rank_spawn_sources(per_pc)["status"] == "SOURCE_PARTIAL"


def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t(); print(f"PASS {t.__name__}")
        except AssertionError as exc:
            failed += 1; print(f"FAIL {t.__name__}: {exc!r}")
        except Exception as exc:  # noqa: BLE001
            failed += 1; print(f"ERROR {t.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
