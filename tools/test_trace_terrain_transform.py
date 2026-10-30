#!/usr/bin/env python3
"""Unit tests for trace_terrain_transform's PARSING/NORMALIZATION core.

Pure Python — does NOT require DuckStation, a save state, or a network. It only
exercises the offline helpers (hex parsing, GTE register decode, hit
normalization, capture building). Run:
    python3 tools/test_trace_terrain_transform.py     (or under pytest)
"""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import trace_terrain_transform as T  # noqa: E402  (no DuckStation import at module load)


def _identity_rt():
    """gte dict for a 1.3.12 identity rotation (each 4096 = 1.0)."""
    return {"RT_0": "0x00001000", "RT_1": "0x00000000", "RT_2": "0x00001000",
            "RT_3": "0x00000000", "RT_4": "0x00001000"}


def test_to_int():
    assert T._to_int("0x8012c1d0") == 0x8012C1D0
    assert T._to_int("8012c1d0") == 0x8012C1D0
    assert T._to_int("00001000") == 4096            # bare hex, no 0x
    assert T._to_int(0x1234) == 0x1234
    assert T._to_int(None) is None
    assert T._to_int("") is None


def test_lohi_signed():
    assert T._lohi(0x00001000) == (4096, 0)
    # high word 0xFFFF must sign-extend to -1
    assert T._lohi(0xFFFF1000) == (4096, -1)


def test_decode_rt_identity():
    rt = T.decode_rt_matrix(_identity_rt())
    assert rt is not None and rt["status"] == "decoded"
    m = rt["matrix_float"]
    assert m[0][0] == 1.0 and m[1][1] == 1.0 and m[2][2] == 1.0
    assert m[0][1] == 0.0 and m[2][0] == 0.0
    assert rt["column_norms_xyz"] == [1.0, 1.0, 1.0]


def test_decode_rt_missing_returns_none():
    assert T.decode_rt_matrix({"RT_0": "0x1000"}) is None  # incomplete


def test_classify_pointer_primary_in_buffer():
    regs = {"a0": "0x80100000", "a1": "0x8012c1f0"}
    p = T.classify_pointer(regs, T.TERRAIN_BUF_BASE, T.TERRAIN_BUF_END)
    assert p["status"] == "observed"
    assert p["reg"] == "a1"
    assert p["offset_from_terrain_base"] == 0x20
    # a0 is a RAM pointer but not in the terrain buffer
    assert any(c["reg"] == "a0" and not c["in_terrain_buffer"] for c in p["other_ram_candidates"])


def test_classify_pointer_none_in_buffer():
    regs = {"a1": "0x80123456", "a0": "0x00000004"}  # a1 in RAM, a0 not
    p = T.classify_pointer(regs, T.TERRAIN_BUF_BASE, T.TERRAIN_BUF_END)
    assert p["status"] == "no candidate in terrain buffer range"
    assert any(c["reg"] == "a1" for c in p["ram_pointer_candidates"])


def test_normalize_hit_full():
    gte = dict(_identity_rt())
    gte.update({"SXY0": "0x00640032", "SXY1": "0x00650033", "SXY2": "0x00660034",
                "V0_XY": "0x000A0014", "V0_Z": "0x00000064"})
    event = {"frame": 7, "cycle": 123, "pc": "0x80017464",
             "regs": {"pc": "0x80017464", "a1": "0x8012c1d0", "a0": "0x80100000"},
             "gte": gte}
    h = T.normalize_hit(event, requested=["pc", "a1", "gte.RT_0", "gte.MAC0", "gte.TRX"])
    assert h["observed"]["frame"] == 7
    assert h["decoded"]["pointer"]["reg"] == "a1"
    assert h["decoded"]["pointer"]["offset_from_terrain_base"] == 0
    assert h["decoded"]["model_to_view_rotation"]["column_norms_xyz"] == [1.0, 1.0, 1.0]
    assert h["decoded"]["screen_xy"][0] == {"s": 0, "x": 0x32, "y": 0x64}
    assert h["decoded"]["input_verts"][0] == {"v": 0, "x": 0x14, "y": 0x0A, "z": 0x64}
    # translation was not captured -> flagged unknown; so was the requested gte.MAC0
    assert "translation" in h["unknown"]
    assert "capture:gte.MAC0" in h["unknown"]
    assert "capture:gte.TRX" in h["unknown"]


def test_build_capture_default_is_valid():
    cap = T.build_capture(None)
    assert len(cap) <= 32, "execTrace.addWatch caps capture at 32 names"
    assert "pc" in cap and "a1" in cap and "gte.RT_0" in cap and "gte.SXY0" in cap
    assert T.build_capture("a1, gte.RT_0 ,pc") == ["a1", "gte.RT_0", "pc"]


def test_addwatch_params():
    p = T.addwatch_params("0x80017464", ["pc", "a1"], 5000)
    assert p["pc"] == "0x80017464"
    assert p["capture"] == ["pc", "a1"]
    assert p["max_events"] == 5000 and p["stop_on_hit"] is False


def test_decode_quad_sample():
    raw = bytearray(0x30)
    struct.pack_into("<I", raw, 0x04, (20 << 16) | 10)   # v0 xy = (10, 20)
    struct.pack_into("<I", raw, 0x0C, (40 << 16) | 30)
    struct.pack_into("<I", raw, 0x14, (60 << 16) | 50)
    struct.pack_into("<I", raw, 0x1C, (80 << 16) | 70)
    for off, z in ((0x08, 100), (0x10, 110), (0x18, 120), (0x20, 130)):
        struct.pack_into("<H", raw, off, z)
    q = T.decode_quad_sample(bytes(raw))
    assert q["verts_xy"] == [[10, 20], [30, 40], [50, 60], [70, 80]]
    assert q["verts_z"] == [100, 110, 120, 130]


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
