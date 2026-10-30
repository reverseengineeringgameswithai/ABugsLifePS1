"""Guards for the C17 (movie viewer / FMV unlocks) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_c17_movie_viewer.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_c17_movie_viewer.json"
STATIC_SRC = ROOT / "asm" / "hand_written" / "800502c4_sub_800502c4.s"
RAW_ASM = ROOT / "asm" / "nonmatchings" / "resident" / "800502c4.s"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_garbled_address_corrected():
    doc = load_artifact()
    mech = doc["MECHANISM_RESOLVED_2026-08-03"]
    assert "0x8009B878" in mech["corrects_a_garbled_prior_citation"]
    assert "0x800a-18312" in mech["corrects_a_garbled_prior_citation"]


def test_per_level_and_campaign_wide_triggers_documented():
    doc = load_artifact()
    mech = doc["MECHANISM_RESOLVED_2026-08-03"]
    assert "0x80077FE3" in mech["per_level_clip_trigger"]
    assert "112" in mech["campaign_wide_ending_trigger"]
    assert "41" in mech["campaign_wide_ending_trigger"]


def test_persistence_confirmed_via_save_serializer():
    doc = load_artifact()
    mech = doc["MECHANISM_RESOLVED_2026-08-03"]
    assert "19 bytes from 0x8009b878" in mech["persistence_confirmed"]


def test_live_verification_pins_level_index_and_atomic_transition():
    doc = load_artifact()
    live = doc["LIVE_VERIFICATION_2026-08-03"]
    assert "index 6" in live["level_index_confirmed_empirically"].lower() or "Index 6" in live["level_index_confirmed_empirically"]
    assert "scene_id+1" in live["level_index_confirmed_empirically"] or "scene_id + 1" in live["level_index_confirmed_empirically"]
    assert "8970" in live["transition_is_instant_not_incremental"]
    assert "8980" in live["transition_is_instant_not_incremental"]


def test_menu_reader_found_with_four_gate_classes():
    doc = load_artifact()
    menu = doc["MENU_READER_FOUND_2026-08-03"]
    builder = menu["menu_availability_builder"]
    assert "0x800b4120" in builder
    assert "0x800b4084" in builder
    assert "0x80082284" in builder
    assert "0x8009B888" in builder
    assert "0x8009B889" in builder


def test_menu_playback_dispatch_bypasses_fmv_bin_load():
    doc = load_artifact()
    menu = doc["MENU_READER_FOUND_2026-08-03"]
    dispatch = menu["playback_dispatch"]
    assert "0x800B6250" in dispatch
    assert "0x8003f580" in dispatch
    assert "zero hits" in dispatch


def test_still_open_menu_gap_marked_resolved():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert still_open["menu_presentation_not_found"].startswith("RESOLVED 2026-08-03")


def test_operator_fixture_exists():
    movie = ROOT / "movies" / "Phase4" / "Interpreter" / "C17_MovieViewer.movie.json"
    assert movie.exists()


def test_static_source_files_exist_and_are_consistent():
    assert STATIC_SRC.exists()
    assert RAW_ASM.exists()
    static_text = STATIC_SRC.read_text()
    assert "18312" in static_text or "-18312" in static_text
    assert "112" in static_text


def test_registry_status_is_partial_with_bounded_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: C17_movie_viewer")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "C17_movie_viewer"
    assert row["status"] == "partial"
    assert "UNLOCK TABLE + FINAL-CLIP CONDITIONS RESOLVED 2026-08-03" in " ".join(row["bindings"])
    assert "MENU READER FOUND 2026-08-03" in " ".join(row["bindings"])
    assert "BOUNDED EXHAUSTED 2026-08-03" in row["next"]
