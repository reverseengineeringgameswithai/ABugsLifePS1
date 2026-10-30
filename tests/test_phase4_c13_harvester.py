"""Guards for the capsule-backed Phase-4 C13 grain-harvester evidence."""

import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_c13_harvester.json"
ANNOTATIONS = ROOT / "movies" / "Phase4" / "c13_GRAIN_HARVESTER.annotations.yaml"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"
SEMANTIC = ROOT / "config" / "semantic_state.yaml"
CONTRACT = ROOT / "config" / "phase4_c13_harvester.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_c13_retained_claims_are_bounded_and_causally_chained():
    doc = load_artifact()
    assert doc["schema"] == "abl-phase4-c13-harvester-v1"
    assert doc["status"] == "partial"
    assert doc["authority"]["media"].startswith("hash-verified pristine")
    assert doc["authority"]["allmods_role"].startswith("none")
    assert all(doc["inputs"]["checks"].values())
    assert all(doc["computed_checks"].values())

    equip = doc["equip"]
    assert equip["input_frame"] == 80
    assert equip["square_fresh_edge"] is True
    assert equip["first_state_one_frame"] == equip["first_bit_set_frame"] == 83
    assert equip["state_address"] == "0x800A657E"
    assert equip["power_flags_address"] == "0x800A6590"

    attraction = doc["grain_attraction"]
    assert attraction["source_record"]["grain_entries"] == 50
    assert attraction["activation_metric"]["inclusive_max"] == 0x15F8F
    assert [row["movie_frame"] for row in attraction["source_events"]] == [
        161, 177, 197, 227, 261, 431, 453, 481, 505,
    ]
    assert [row["collection"]["movie_frame"] for row in attraction["source_events"]] == [
        211, 227, 247, 281, 339, 485, 507, 535, 561,
    ]
    assert attraction["initial_grain_count"] == 0
    assert attraction["final_grain_count"] == 9
    assert all(
        row["metric_previous_frame"] > 0x15F8F
        and row["metric_activation_frame"] <= 0x15F8F
        and row["contact_action_id"] == 0x14
        and row["contact_initial_ttl"] == 200
        and row["contact_initial_flags"] == 0xEA
        for row in attraction["source_events"]
    )


def test_c13_live_complement_closes_only_the_measured_controls():
    doc = load_artifact()
    live = doc["remaining"]["requires_isolated_live_run"]
    assert any("moves ctor-0x51" in item for item in live)
    assert any("writer PC" in item for item in live)
    assert "all-level harvester availability" in doc["remaining"]["not_closed_by_this_fixture"]
    assert doc["inputs"]["checks"]["live_complement_checks"] is True

    claims = [row["claim"] for row in doc["conclusions"]]
    assert any("Cross disengages" in claim for claim in claims)
    assert any("LEVEL01 id-13 bee" in claim for claim in claims)


def test_c13_annotation_and_registry_link_are_present():
    annotations = yaml.safe_load(ANNOTATIONS.read_text())
    assert annotations["row"] == "C13_grain_harvester"
    assert annotations["annotations"][1]["id"] == "equip_input"
    assert annotations["annotations"][1]["frame"] == 80
    assert annotations["post_movie_leads"][0]["id"] == "manual_disengage"
    assert annotations["post_movie_leads"][1]["id"] == "harvester_enemy_contact"

    registry = yaml.safe_load(REGISTRY.read_text())
    row = next(item for item in registry["rows"] if item["id"] == "C13_grain_harvester")
    assert "movies/Phase4/c13_GRAIN_HARVESTER.annotations.yaml" in row["fixture_have"]


def test_c13_static_contract_is_tied_to_pristine_bytes():
    doc = load_artifact()
    words = doc["pristine_static_contract"]["words"]
    assert all(row["matches"] for row in words.values())
    assert words["0x80051EA8"]["actual"] == "0x34630080"
    assert words["0x80051EB0"]["actual"] == "0xA4236590"
    assert words["0x80053BF4"]["actual"] == "0x30420080"
    assert words["0x80053C20"]["actual"] == "0x24070051"
    assert words["0x8004B160"]["actual"] == "0x30420080"
    assert words["0x8004B204"]["actual"] == "0x240203E6"
    assert words["0x8004B208"]["actual"] == "0xA622006E"


def test_c13_is_promoted_to_machine_and_canon_layers():
    contract = yaml.safe_load(CONTRACT.read_text())
    assert contract["row"] == "C13_grain_harvester"
    assert contract["status"] == "partial"
    equip = contract["machine_contract"]["equip_state"]
    assert equip["address"] == 0x800A657E
    assert equip["width"] == "s16"
    actor = contract["machine_contract"]["level01_harvester_actor"]
    assert actor["address"] == 0x800A1DFC
    assert actor["required_id"] == 0x23

    semantic = yaml.safe_load(SEMANTIC.read_text())["entries"]
    flags = next(row for row in semantic if row["id"] == "original.player_powerup_flags")
    assert flags["address"] == 0x800A6590
    assert any(writer.get("address") == 0x80051EB0 for writer in flags["writers"])

    symbols = (ROOT / "symbols" / "re_symbols.sym").read_text()
    assert "8004ABF4 actor_player_contact_resolver" in symbols
    assert "80051DB4 harvester_update_entry" in symbols
    assert "80051DBC harvester_equip_and_active_update" in symbols

    c_source = (ROOT / "src_re" / "grain_harvester_80051db4.c").read_text()
    assert "HARVESTER_METRIC_MAX 0x15f8f" in c_source
    assert "HARVESTER_ENEMY_HP_SENTINEL 998" in c_source
    canon = (ROOT / "ObsidianVault" / "Canon" / "Systems" /
             "SYS_grain_harvester.md").read_text()
    assert "C13 remains" not in canon
    assert "## Bounded residuals" in canon


def test_c13_retained_live_artifact_has_paired_behavioral_controls():
    live = json.loads(
        (ROOT / "analysis" / "phase4_c13_harvester_live.json").read_text()
    )
    assert live["schema"] == "abl-phase4-c13-harvester-live-v1"
    assert all(live["computed_checks"].values())
    assert live["cross_disengage"]["cleared"] is True
    assert live["equipped_bee_branch"]["passes"] is True
    assert live["disengaged_bee_control"]["passes"] is True
    assert live["equipped_bee_branch"]["contact"]["actor"]["hp_0x6e"] == 998
    assert live["equipped_bee_branch"]["retirement"]["absent_from_live_table"]
    assert live["disengaged_bee_control"][
        "at_equipped_retirement_checkpoint"
    ]["still_in_live_table"]


@pytest.mark.local_media
def test_c13_artifact_is_fresh_against_external_capsule():
    result = subprocess.run(
        [sys.executable, "tools/phase4_c13_harvester.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_c13_strict_phase4_state_and_static_breadth_are_bounded():
    score = json.loads(
        (ROOT / "analysis" / "phase4_c13_dod_scorecard.json").read_text()
    )
    raw = json.loads(
        (ROOT / "analysis" / "phase4_c13_raw_applicability.json").read_text()
    )
    artifact = json.loads(ARTIFACT.read_text())

    assert artifact["status"] == "partial"
    assert score["status"] == "partial"
    assert score["closure_state"] == "OPEN"
    assert score["high_yield_row_specific_work"] == "exhausted"
    assert score["final_predicates"]["strict_phase4_solved"] is False

    assert raw["files_scanned"] == 15
    assert raw["matching_files"] == 6
    assert raw["total_harvester_records"] == 6
    matching = [
        item for item in raw["files"] if item["harvester_matches"] == 1
    ]
    assert all(
        item["actor_table"]["harvester_records"][0]["record"] == 63
        for item in matching
    )
    assert {
        tuple(item["actor_table"]["harvester_records"][0]["params"])
        for item in matching
    } == {("0x28806465", "0x00000019", "0x40402040")}

    frontier = score["dimensions"][1]
    assert frontier["status"] == "not_met"
    assert frontier["metrics"] == {
        "direct_same_width_accesses_open": 251,
        "indirect_calls_open": 149,
        "overlay_pointer_accesses_open": 4967,
    }
    breadth = score["dimensions"][5]
    assert breadth["static_applicability"]["applicable_operator_levels"] == [
        1, 2, 5, 8, 10, 11
    ]
    assert breadth["behavioral_breadth"] == {
        "retained_applicable_placements": 1,
        "total_applicable_placements": 6,
        "complete": False,
    }
    assert score["movie_decision"]["needed_now"] is False
