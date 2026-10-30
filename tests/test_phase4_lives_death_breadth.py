"""Falsification guards for C16 multi-scene resident death-law breadth."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_lives_death_breadth as breadth  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_lives_death_breadth.json"
ARTIFACT_SHA256 = "a7cc74d126490c34f3bf5d84bd512616fab4ceb2bf754a8b883367350fdcccc4"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_c16_death_breadth_recomputes_from_low_level_state_and_pcs():
    document = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert document["campaign_state"] == "active_partial"
    assert breadth.evidence_gaps(document) == []
    summary = breadth.derive_summary(document["replays"])
    assert document["summary"] == summary
    assert summary["classification_counts"] == {
        "final_life_game_over_selected": 1,
        "nonfatal_damage_boundary": 3,
        "ordinary_respawn_completed": 4,
    }
    assert summary["death_paths_joined_to_exact_resident_law"] == 5
    assert summary["death_scenes"] == [3, 4, 6, 10, 12]
    assert summary["exact_first_trigger_paths"] == 8
    assert summary["trigger_producer_path_counts"] == {
        "contact_pool_damage": 2,
        "player_region_code_1_exit": 3,
        "player_region_code_4_hazard": 1,
        "proximity_contact": 1,
        "scene_overlay_level06_level": 1,
    }
    assert summary["hazard_kinds_or_owners_promoted"] == 0
    assert document["trigger_static_census"]["direct_call_count"] == 8
    assert all(
        row["first_transition_trigger"]["attribution"]["exact"] is True
        for row in document["replays"])
    assert document["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_lives_death_breadth.py").read_bytes()).hexdigest()
    assert document["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(
        document, require_selection=False) == []


@pytest.mark.local_media
def test_c16_death_breadth_fixtures_recompute_from_central_pristine_pins():
    retained = load_artifact()["fixture_census"]
    assert breadth.hazards.build_fixture_census() == retained
    assert retained["count"] == 8
    assert all(row["movie"]["media_class"] == "pristine_serial"
               for row in retained["pairs"])
    assert all(row["save"]["media_class"] == "pristine"
               for row in retained["pairs"])


def test_decisive_pc_trace_and_summary_mutations_turn_c16_breadth_red():
    document = load_artifact()

    mutated = copy.deepcopy(document)
    respawn = next(
        row for row in mutated["replays"]
        if row["law_evidence"]["classification"] == "ordinary_respawn_completed")
    coverage = next(
        row for row in respawn["cycle_neutral_trace"]["coverage"]
        if row["label"] == "respawn_transition_state_handler")
    coverage["pcs"].remove("0x8005b348")
    gaps = " ".join(breadth.evidence_gaps(mutated))
    assert "resident-law derivation changed" in gaps
    assert "exact resident death law is incomplete" in gaps

    mutated = copy.deepcopy(document)
    mutated["replays"][0]["cycle_neutral_trace"]["comparison"][
        "cycle_neutral"] = False
    assert "cycle-neutral coverage changed" in " ".join(
        breadth.evidence_gaps(mutated))

    mutated = copy.deepcopy(document)
    mutated["summary"]["death_paths_joined_to_exact_resident_law"] = 8
    assert "summary changed" in " ".join(breadth.evidence_gaps(mutated))

    mutated = copy.deepcopy(document)
    capture = mutated["replays"][0]["first_transition_trigger"][
        "entry_register_capture"]
    capture["ra"] = "0x8004b4ac"
    gaps = " ".join(breadth.evidence_gaps(mutated))
    assert "entry link-register derivation changed" in gaps
    assert "exact first trigger producer is incomplete" in gaps

    mutated = copy.deepcopy(document)
    trigger = mutated["replays"][1]["first_transition_trigger"]
    after_damage = next(
        row for row in trigger["after"]["cycle_neutral_trace"]["coverage"]
        if row["label"] == "damage_and_death_initiator")
    after_damage["pcs"].remove("0x8004a700")
    assert "exact first trigger producer is incomplete" in " ".join(
        breadth.evidence_gaps(mutated))


def test_cross_scene_overlay_bytes_override_filename_and_scene_inference():
    document = load_artifact()
    replay = next(row for row in document["replays"]
                  if row["lead"] == "E10_ground_bird_lead")
    trigger = replay["first_transition_trigger"]
    attribution = trigger["attribution"]
    capture = trigger["entry_register_capture"]
    assert attribution["producer_path_id"] == "scene_overlay_level06_level"
    assert attribution["link_call_address"] == "0x800b3e94"
    assert attribution["static_direct_call_match"] is True
    assert capture["arguments"]["a3"] == "0x00000003"
    runtime_match = next(
        row for row in trigger["runtime_overlay_identity"][
            "runtime_direct_calls"]
        if row["overlay"] == "LEVEL06_LEVEL.BIN")
    assert runtime_match["slice_matches"] is True
    assert runtime_match["declared_scene_match"] is False
    assert attribution["trigger_to_outcome_movie_frames"] == 119
    assert attribution["lives_decrement_reached_by_typed_outcome"] is True


def test_c16_breadth_support_does_not_promote_campaign_or_e10_ownership():
    document = load_artifact()
    assert document["summary"]["hazard_kinds_or_owners_promoted"] == 0
    assert document["bounded_interpretation"]["forbidden_claim"].startswith(
        "Do not assign a hazard kind")
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
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91
