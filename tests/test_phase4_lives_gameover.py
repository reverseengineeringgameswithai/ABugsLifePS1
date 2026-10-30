"""Falsification guards for the active Phase-4 C16 lifecycle campaign."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_lives_gameover as c16  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_lives_gameover.json"
ARTIFACT_SHA256 = "6aa96878f311b7a470479b226094d10e1a4ec2a534edb8310e08e05070b75748"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_c16_evidence_recomputes_exact_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert doc["campaign_state"] == "active_partial"
    assert c16.evidence_gaps(doc) == []
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_lives_gameover.py").read_bytes()).hexdigest()
    assert run["duckstation"]["revision"] == \
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5"
    assert run["duckstation"]["binary_sha256"] == \
        "c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec"
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_fixture_and_static_census_recompute_from_hash_pins():
    retained = load_artifact()
    assert c16.build_fixture_census() == retained["fixture_census"]
    assert c16.build_static_census() == retained["static_census"]
    assert retained["fixture_census"]["movie"]["input_segments"] == \
        c16.EXPECTED_SEGMENTS
    instructions = retained["static_census"]["instructions"]
    assert instructions["fatal_health_write"]["instruction_word"] == "0xA4236594"
    assert instructions["final_life_reader"]["instruction_word"] == "0x904265A0"
    assert instructions["respawn_health_restore"]["instruction_word"] == "0xA4226594"
    assert instructions["respawn_lives_decrement"]["instruction_word"] == "0xA02665A0"
    assert instructions["continue_scene_config_lives_write"]["instruction_word"] == \
        "0xA02265A0"


def test_single_variable_and_writer_mutations_turn_the_c16_proof_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["live"]["one_life_ordinary_respawn"]["state_recipe"]["mutation"] \
        ["main_ram_difference_count"] = 2
    assert "not single-variable" in " ".join(c16.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["neutral_input_no_death"]["damage_trace"][
        "cycle_neutral_trace"]["coverage"][0]["total_hits"] = 1
    assert "damage positive/neutral" in " ".join(c16.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["continue_transition"]["natural_post"][
        "cycle_neutral_trace"]["control"]["ram_sha256"] = "00" * 32
    gaps = " ".join(c16.evidence_gaps(mutated))
    assert "control/instrumented signatures diverged" in gaps
    assert "retained control signature changed" in gaps

    mutated = copy.deepcopy(doc)
    events = mutated["live"]["continue_transition"]["writer_attribution"]["events"]
    events[0]["new_value"] = 4
    assert "Continue lives writer attribution" in " ".join(c16.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    pcs = mutated["live"]["one_life_ordinary_respawn"]["respawn_trace"][
        "cycle_neutral_trace"]["coverage"][0]["pcs"]
    pcs.remove("0x8005b348")
    assert "ordinary respawn writer coverage" in " ".join(c16.evidence_gaps(mutated))


def test_c16_registry_is_active_without_promoting_coverage():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "lives_gameover_continue")
    assert campaign["status"] == "active"
    for assertions in campaign["evidence"].values():
        for assertion in assertions:
            assert common.audit_assertion(assertion) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "lives_gameover_continue: status is not completed"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C16_lives_gameover"]["state"] == "open"
    assert coverage["families"]["player_lifecycle"]["derived_status"] == "active"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91


def test_c16_schema_keeps_open_dependencies_and_mod_safety_explicit():
    schema = yaml.safe_load((ROOT / "config/phase4_lives_gameover.yaml").read_text())
    assert schema["schema"] == "abl-phase4-lives-gameover/2"
    assert schema["campaign_state"] == "active_partial"
    assert schema["reproduced_controls"]["anchor"]["lives"] == 0
    assert schema["reproduced_controls"]["ordinary_respawn_control"]["result"] == {
        "scene": 9, "true_health": 4, "lives": 0, "master_state": 0}
    restart = schema["reproduced_controls"]["post_game_over_title_restart"]
    assert restart["natural"] == {
        "scene": 0, "lives": 5, "writer": 0x80055550}
    assert restart["start_removed"] == {
        "scene": 0, "lives": 0, "writer_0x80055550_executed": False}
    assert set(schema["ownership_boundaries"]["still_open"]) == {
        "C15 broader authored respawn-row and overlay selector policy.",
        "Hazard-kind and remaining actor/script ownership plus scripted, setpiece and exceptional death classes and other bonus contexts; bounded Thumper, Thud-row-4 and Riverbed-Flight actor paths do not complete their campaign owners, and the Bonus-3 context path assigns no named enemy or F18 behavior.",
        "Explicit native Save/Load after game over, no-card/corrupt-card behavior and other title/menu branches.",
        "Remaining campaign-stage and transition breadth beyond the retained five-scene death-law join.",
    }
    breadth = schema["reproduced_controls"]["multi_scene_death_law"]
    assert breadth["retained_outcomes"] == {
        "ordinary_respawn_completed": 4,
        "final_life_game_over_selected": 1,
        "nonfatal_damage_boundary": 3,
    }
    assert breadth["scene_values"] == [3, 4, 6, 10, 12]
    assert breadth["exact_first_transition_producers"] == 8
    assert breadth["producer_path_counts"] == {
        "proximity_contact": 1,
        "contact_pool_damage": 2,
        "player_region_code_4_hazard": 1,
        "player_region_code_1_exit": 3,
        "scene_overlay_level06_level": 1,
    }
    assert "checkpoint" in schema["mod_contract"]["unsafe_assumptions"]
    assert "card" in schema["mod_contract"]["unsafe_assumptions"]
