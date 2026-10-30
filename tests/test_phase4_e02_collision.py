"""Phase-4 E02b (collision plane half): machine-checkable gates.

Covers analysis/phase4_e02_collision_roundtrip.json -- the all-level
source->runtime round trip (independent C reimplementation of FUNC_80030F60
diffed against save RAM) + the campaign plane census.

2026-08-04 corrections (two rounds, both my own errors):
  1. Four scenes were pinned as "runtime-built". SEARCH-SCOPE error (.ALL
     containers never swept) + a bounds bug (the tool demanded room for every
     RUNTIME sector, but containers hold only the AUTHORED prefix).
  2. Bug Bar then looked like the one true runtime case. Wrong again: the
     candidate pre-filter required the first FOUR records to match, but Bug
     Bar authors exactly ONE sector (the other 45 are runtime-registered).
ALL 16 scenes now resolve to a disc container. There is no runtime-built case.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_e02_collision_roundtrip.json"

# Every scene resolves to a disc container -- no runtime-built exceptions.
RUNTIME_BUILT = set()

# Empirically proven scene -> container bindings (zero-mismatch round trips).
# Note both container families occur: LEVEL.RAW chunk 32 (block base 8) and
# the uncompressed .ALL terrain containers (block base 4, live-derived).
PROVEN_BINDINGS = {
    "training": ("LEVEL07/LEVEL1.RAW", 8),
    "stage01_anthill": ("LEVEL01/LEVEL.RAW", 8),
    "stage02_tunnels": ("LEVEL03/LEVEL.RAW", 8),
    "stage03_council_chamber": ("LEVEL02/LEVEL.RAW", 8),
    "stage04_cliffside_canyon": ("LEVEL06/LEVEL.RAW", 8),
    "stage05_riverbed_run": ("LEVEL10/LEVEL.RAW", 8),
    "stage06_birdnest": ("LEVEL01/LEVEL1.RAW", 8),
    "stage07_city_entrance": ("LEVEL04/LEVEL.RAW", 8),
    "stage08_city_square": ("LEVEL05/TERRAIN.ALL", 4),
    "stage09_bug_bar": ("LEVEL04/LEVEL1.RAW", 8),
    "stage10_clover_forest": ("LEVEL07/TERRAIN.ALL", 4),
    "stage11_the_tree": ("LEVEL02/TERR1.ALL", 4),
    "stage12_battle_arena": ("LEVEL03/LEVEL1.RAW", 8),
    "stage13_anthill_two": ("LEVEL09/LEVEL.RAW", 8),
    "stage14_riverbed_flight": ("LEVEL08/LEVEL.RAW", 8),
    "stage15_canyon_showdown": ("LEVEL05/LEVEL1.RAW", 8),
}


def _art():
    return json.loads(ART.read_text())


def test_c_tool_compiles():
    subprocess.run(["cc", "-O2", "-Werror", "-fsyntax-only",
                    str(ROOT / "tools/phase4_e02_collision_roundtrip.c")], check=True)


def test_all_sixteen_scenes_roundtrip_exactly():
    d = _art()
    for label, (container, _bb) in PROVEN_BINDINGS.items():
        row = d["levels"][label]
        assert row["matched_raw"] == container, (label, row["matched_raw"])
        m = row["match"]
        assert m["roundtrip_mismatches"] == 0, label
        assert m["census"]["bad_blocks"] == 0, label
        assert m["census"]["planes"] > 0, label


def test_block_base_is_container_family_dependent():
    """RAW chunk-32 lays blocks from offset 8; .ALL containers from offset 4
    (derived live from the Clover Forest load: container base 0x8017A0A4,
    sector-0 block pointer 0x8017A0A8)."""
    d = _art()
    for label, (container, bb) in PROVEN_BINDINGS.items():
        assert d["levels"][label]["match"]["block_base"] == bb, label
        assert container.endswith(".ALL") == (bb == 4), label


def test_every_scene_resolves_to_a_disc_container():
    d = _art()
    assert d["failing_levels"] == []
    assert set(d["levels"]) == set(PROVEN_BINDINGS)


def test_flag2c_law_holds_on_every_authored_sector():
    """Runtime +0x2C == source +0x14 on ALL authored sectors campaign-wide --
    resolving the +0x2C/+0x2E wording tension (region code is +0x2E, from
    src +0x2C; runtime +0x2C mirrors src +0x14 like runtime +0x0C does)."""
    d = _art()
    for label in PROVEN_BINDINGS:
        m = d["levels"][label]["match"]
        assert m["flag2c"]["eq_src14"] == m["authored_count"], label


def test_census_totals_and_normal_discipline():
    d = _art()
    t = d["campaign_totals"]
    assert t["planes"] == t["floors"] + t["walls_vertical"] + t["ceilings"]
    assert t["planes"] > 58000
    assert t["normal_len_off"] == 0          # all unit normals within rounding
    assert t["bad_blocks"] == 0              # every block walk lands exactly


def test_authored_prefix_never_exceeds_the_runtime_table():
    """Containers hold only the AUTHORED records; the runtime table adds a
    runtime-registered tail. LEVEL01's split is the proven 178 + 45."""
    d = _art()
    m = d["levels"]["stage01_anthill"]["match"]
    assert m["authored_count"] == 178 and m["runtime_extra"] == 45
    # Bug Bar is the extreme: ONE authored sector, 45 registered at runtime --
    # the dynamically-assembled arena, and the reason a 4-record candidate
    # pre-filter wrongly rejected its container.
    bb = d["levels"]["stage09_bug_bar"]["match"]
    assert bb["authored_count"] == 1 and bb["runtime_extra"] == 45
    for label in PROVEN_BINDINGS:
        mm = d["levels"][label]["match"]
        assert mm["authored_count"] + mm["runtime_extra"] == mm["sector_count"], label
        assert mm["authored_count"] > 0, label
