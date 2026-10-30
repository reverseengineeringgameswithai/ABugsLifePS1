"""Falsification guards for the C16 Stage-15 boss-context death path."""
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
import phase4_c16_boss_death as boss_death  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_c16_boss_death.json"
ARTIFACT_SHA256 = "33f964abe0ca759aec94178092c1c956c340f2c4b079fb989faeb236aeb0935f"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_boss_context_death_recomputes_from_low_level_evidence():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert boss_death.evidence_gaps(doc) == []
    assert doc["summary"] == boss_death.derive_summary(doc["replay"])
    assert doc["summary"]["boss_context_death_paths"] == 1
    assert doc["summary"]["fatal_invocation_causally_confirmed"] is True
    assert doc["summary"]["resident_game_over_law_complete"] is True
    assert doc["summary"]["hopper_or_damage_actor_promoted"] == 0
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_c16_boss_death.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_boss_context_fixture_recomputes_from_central_pristine_pins():
    retained = load_artifact()["fixture_census"]
    assert boss_death.build_fixture_census() == retained
    assert retained["movie"]["version"] == 1
    assert retained["movie"]["frames"] == 2983
    assert retained["movie"]["recorded_input_scope"] == \
        "16 digital buttons; v1 has no analog axes"
    assert retained["movie"]["media_class"] == "pristine_serial"
    assert retained["save"]["media_class"] == "pristine"


def test_stage15_context_recomputes_without_promoting_hopper_causation():
    doc = load_artifact()
    identity = doc["boss_context_identity"]
    assert boss_death.build_boss_context_identity() == identity
    assert identity["scene_graph"]["scene_id"] == 15
    assert identity["scene_graph"]["asset_entry"] == "level05\\level5c"
    assert identity["phase1_actor_probe"]["owner_level"] == \
        "stage15_canyon_showdown"
    assert identity["baseline_fixture_routes"]["D20_hopper"][
        "movie_declared"] is True
    assert identity["baseline_fixture_routes"]["F15_canyon_showdown"][
        "movie_declared"] is True
    assert identity["central_movie_required_routes"] == [
        "mechanics:D20_hopper", "mechanics:F15_canyon_showdown"]
    assert doc["summary"]["runtime_overlay_exact_matches"] == []
    assert all(not row["exact_match"] for row in doc["replay"][
        "first_fatal_boundary"]["runtime_overlay_identity"]["candidates"])
    assert doc["replay"]["first_fatal_boundary"]["attribution"][
        "damage_actor_or_hopper_promoted"] is False
    assert doc["bounded_interpretation"]["forbidden_claim"].startswith(
        "Do not infer from the filename/context")


def test_fatal_caller_and_resident_law_mutations_turn_evidence_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["replay"]["first_fatal_boundary"]["fatal_invocation"][
        "after_return"]["health"] = 0
    assert "fatal invocation" in " ".join(boss_death.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["replay"]["first_fatal_boundary"]["attribution"][
        "producer_link_call_address"] = "0x80000000"
    assert "fatal producer attribution" in " ".join(
        boss_death.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    scene_flow = next(
        row for row in mutated["replay"]["cycle_neutral_trace"]["coverage"]
        if row["label"] == "scene_flow_dispatcher")
    scene_flow["pcs"].remove("0x800500d4")
    assert "resident game-over law" in " ".join(
        boss_death.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["replay"]["first_fatal_boundary"]["before"][
        "cycle_neutral_trace"]["comparison"]["cycle_neutral"] = False
    assert "fatal boundary passive coverage" in " ".join(
        boss_death.evidence_gaps(mutated))


def test_c16_remains_open_and_scenario_names_only_measured_state():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "lives_gameover_continue")
    assert campaign["status"] == "active"
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "lives_gameover_continue: status is not completed"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C16_lives_gameover"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91

    scenario = yaml.safe_load((ROOT / "tools/scenarios/duckstation/"
                               "pristine_hopper_context_final_life.yaml").read_text())
    assert scenario["playback"]["movie"] == "hopper_boss.movie.json"
    assertions = scenario["phases"][0]["assertions"]
    assert {row["id"] for row in assertions} == {
        "c16_boss_context_stays_in_scene_15",
        "c16_boss_context_health_is_fatal",
        "c16_boss_context_final_life_stays_zero",
        "c16_boss_context_death_master_state_selected",
        "c16_boss_context_movie_reproducible",
    }
