"""Guards for the Phase-4 E15 FMV movie-id dispatch findings (2026-08-01/02).

Not a full row-closure gate like test_phase4_c13_harvester.py -- E15 item 2 is still
ADVANCED, not MET. This only pins the facts that are done: the movie-id table decode,
the trigger call chain, and the source/Canon/baseline agreeing on them.
"""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_e15_fmv_frontier.json"
FLAG_CENSUS = ROOT / "analysis" / "phase4_e15_completion_flag_overlay_census.json"
SRC = ROOT / "src_re" / "fmv_player_streaming.c"
CANON = ROOT / "ObsidianVault" / "Canon" / "Systems" / "SYS_fmv_player_streaming.md"
BASELINE = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_movie_id_table_has_47_slots_and_40_real_cases():
    doc = load_artifact()
    table = doc["MOVIE_ID_TABLE_2026-08-02"]["table"]
    assert len(table) == 47
    default_slots = [k for k, v in table.items() if v[0] == "DEFAULT"]
    real_slots = [k for k, v in table.items() if v[0] != "DEFAULT"]
    assert sorted(int(k) for k in default_slots) == list(range(3, 10))
    assert len(real_slots) == 40


def test_literal_trigger_sites_resolve_to_the_expected_movies():
    doc = load_artifact()
    table = doc["MOVIE_ID_TABLE_2026-08-02"]["table"]
    assert table["40"][0] == "BUGSFMV2\\LEV15C.STR"
    assert table["46"][0] == "BUGSFMV2\\LOSE.STR"
    # id40 (LEV15C) must be the longest clip in the table -- the basis for the
    # "inferred campaign finale" reading; this is a structural fact, not the inference.
    max_frames = max(v[1] for v in table.values() if v[1] is not None)
    assert table["40"][1] == max_frames


def test_completion_flag_direct_accesses_and_residual_are_both_guarded():
    census = json.loads(FLAG_CENSUS.read_text())
    fmv = next(x for x in census["overlays"] if x["overlay"] == "FMV")
    assert [(h["pc"], h["kind"]) for h in fmv["hits"]] == [
        ("0x800B6B24", "write"),
        ("0x800B6B48", "write"),
        ("0x800B6DD0", "write"),
        ("0x800B743C", "read"),
    ]
    assert fmv["unresolved_base_accesses"] == 2580
    assert sum(x["unresolved_base_accesses"] for x in census["overlays"]) == 7547


def test_completion_flag_closure_overclaim_stays_retracted():
    text = CANON.read_text()
    flat = " ".join(text.split())
    assert "four statically resolved direct overlay" in flat
    assert "values at the three resolved direct overlay writers are exactly `{0,1}`" in flat
    assert "**Completion flag `0x800CAC10` — overlay side fully resolved.**" not in text
    assert "`u32`, domain **exactly `{0,1}`**" not in text
    assert "the domain closure is retracted" in text


def test_source_file_carries_the_selection_mechanism_constants():
    text = SRC.read_text()
    for sym in ("SCENE_FLOW_DISPATCHER", "FMV_ENTRY_POINT", "FMV_MOVIEID_TABLE",
                "FMV_MOVIEID_DEFAULT", "FMV_PLAYBACK_CALL"):
        assert re.search(r"#define\s+%s\s" % sym, text), sym
    assert "0x800B5AA4" in text
    assert "0x8004FCA0" in text


def test_source_file_attributes_the_frame_count_values_to_the_prior_2026_07_04_work():
    text = SRC.read_text()
    assert "ADDED 2026-08-01/02" in text
    assert "2026-07-04 work above proves and exploits the EFFECT" in text
    assert "not a new discovery of the counts themselves" in text


def test_baseline_row_still_reads_partial_and_item2_advanced():
    doc = yaml.safe_load(BASELINE.read_text())
    rows = doc["rows"] if isinstance(doc, dict) and "rows" in doc else doc
    row = next(r for r in rows if r["id"] == "E15_fmv")
    assert row["status"] == "partial"
    assert "ADVANCED not MET" in row["missing"]
