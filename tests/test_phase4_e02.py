"""Phase-4 E02 (collision region codes): machine-checkable gates."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "analysis/phase4_e02_region_code_census.json"
BINDING = ROOT / "analysis/phase4_e02_consumer_binding.json"

# Committed catalog rows (RCG-003) that the unfiltered census must reproduce.
CATALOG_EXPECT = {
    "stage01_anthill": [(177, 2)],
    "stage02_tunnels": [(570, 1), (571, 1), (572, 1), (573, 1), (574, 1),
                        (575, 1), (576, 1), (577, 1), (578, 1), (579, 3)],
    "stage04_cliffside_canyon": [(131, 3)],
    "stage05_riverbed_run": [(292, 1), (293, 1), (294, 1), (295, 1),
                             (296, 1), (297, 3)],
    "stage07_city_entrance": [(219, 1), (220, 4), (221, 4), (222, 4),
                              (223, 4), (224, 4), (225, 4)],
    "stage14_riverbed_flight": [(334, 2)],
    "training": [(24, 3)],   # census's own unfiltered reading (an uncommitted
                             # WIP page by another agent concurs; not cited)
}


def _census():
    return json.loads(CENSUS.read_text())


def test_census_regenerates_offline():
    r = subprocess.run([sys.executable, str(ROOT / "tools/phase4_e02_region_code_census.py"),
                        "--out", "/dev/stdout"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]


def test_campaign_code_domain_is_exactly_0_to_4():
    d = _census()
    assert d["distinct_codes_campaign"] == [0, 1, 2, 3, 4]
    assert len(d["levels"]) == 16
    total = sum(d["campaign_code_histogram"].values())
    assert total == sum(l["sector_count"] for l in d["levels"].values())
    assert total > 3000


def test_census_reproduces_all_committed_catalog_rows():
    d = _census()
    for label, expect in CATALOG_EXPECT.items():
        got = [(r["sector"], r["code"]) for r in d["levels"][label]["nonzero_sectors"]]
        assert got == expect, (label, got)


def test_levels_without_codes_are_the_conditional_ending_levels():
    d = _census()
    empty = sorted(l for l, v in d["levels"].items() if not v["nonzero_sectors"])
    assert empty == ["stage03_council_chamber", "stage06_birdnest",
                     "stage08_city_square", "stage09_bug_bar",
                     "stage10_clover_forest", "stage11_the_tree",
                     "stage12_battle_arena", "stage13_anthill_two",
                     "stage15_canyon_showdown"]


def test_disc_crosscheck_level01():
    d = _census()
    cc = d["disc_crosscheck_level01"]
    assert cc["runtime_contains_all_disc_rows"]
    assert [177, 2] in [list(r) for r in cc["disc_rows"]]


def test_binding_covers_every_observed_code():
    b = json.loads(BINDING.read_text())
    branches = b["callers"]["player_dispatch_0x80048138"]["branches"]
    for code in _census()["distinct_codes_campaign"]:
        assert str(code) in branches, code
    # codes 2 and 3 share the exit body; both must claim the latch store
    assert "0x800823A0" in branches["2"] and "IDENTICAL" in branches["3"]
    # the two non-dispatch callers are bound
    assert "code == 4" in b["callers"]["checkpoint_save_0x80054C90"]["behavior"]
    assert "code == 1" in b["callers"]["mover_actor_update_0x8004B940"]["behavior"]


def test_dispatch_decode_matches_pristine_exe():
    """Spot-pin the decoded dispatch: the beq v1,2 comparison and the shared
    exit tail's fade store must exist at the decoded addresses in the EXE."""
    import struct
    exe = (ROOT / "REBUILD" / "files" / "SCUS_942.88").read_bytes()

    def word(vaddr):
        return struct.unpack_from("<I", exe, vaddr - 0x80010000 + 0x800)[0]

    # dispatch head: jal query at 0x80049644; exit-latch guard read
    # lh v0,0x23A0(v0) at 0x8004965C; li v0,2 at 0x80049668 + beq at 0x8004966C
    assert word(0x80049644) == 0x0C00E3CE
    assert word(0x8004965C) == 0x844223A0
    assert word(0x80049668) == 0x24020002
    assert (word(0x8004966C) >> 16) == 0x1062          # beq v1,v0
    # the shared exit tail stores fade 23: sh v0,9328(at) == 0xA4222470,
    # present exactly once in the dispatch body (codes 2 and 3 SHARE it)
    hits = [a for a in range(0x80049640, 0x80049790, 4) if word(a) == 0xA4222470]
    assert len(hits) == 1, [hex(h) for h in hits]
