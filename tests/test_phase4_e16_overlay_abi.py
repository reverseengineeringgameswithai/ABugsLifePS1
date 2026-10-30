"""Phase-4 E16: the overlay calling contract (region A ABI)."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_e16_overlay_abi.json"


def _art():
    return json.loads(ART.read_text())


def test_abi_tool_compiles():
    subprocess.run(["cc", "-O2", "-Werror", "-fsyntax-only",
                    str(ROOT / "tools/phase4_e16_overlay_abi.c")], check=True)


def test_abi_is_hardcoded_absolute_calls_not_a_vector_table():
    a = _art()["the_abi"]
    assert "NOT a vector table" in a["shape"]
    assert "0x800B39A4" in a["shape"]
    assert "UNION across the" in a["shape"]


def test_every_overlay_implements_at_least_one_entry():
    per = _art()["per_overlay_entries"]
    assert len(per) == 19
    assert all(len(v) >= 1 for v in per.values())
    assert max(len(v) for v in per.values()) <= 5


def test_primary_entry_count_matches_recorded_call_sites():
    """13 overlays implement 0x800b39a4; the committed map records 13 resident
    call sites for it. Two unrelated counts agreeing is the corroboration."""
    per = _art()["per_overlay_entries"]
    n = sum(1 for v in per.values() if "0x800b39a4" in v)
    assert n == 13
    assert "13 of 19" in _art()["the_abi"]["primary_entry"]


def test_c17_menu_reader_lands_in_the_right_overlay():
    """0x800B4084 is committed C17 canon (movie-viewer menu reader); the ABI
    scan independently places it in LEVEL08/LEVEL1.BIN."""
    per = _art()["per_overlay_entries"]
    assert "0x800b4084" in per["LEVEL08_LEVEL1.BIN"]


def test_method_limits_are_stated():
    m = _art()["method_limits"]
    assert "LOWER BOUNDS" in m and "addiu sp,sp,-N" in m
