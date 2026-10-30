"""Falsification and retained-evidence guards for Phase-4 A06."""
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
import phase4_downhill_slide as slide  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_downhill_slide.json"
ARTIFACT_SHA256 = "a78387f11f089b49adfeff3a4e728e7f2a14163a8cded2fc507c4ccb7c4214f6"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    cases = doc["live"]["component_boundary"]["cases"]
    expected = {
        "forward_767": (11, 6), "forward_768": (12, 28),
        "lateral_767": (11, 6), "lateral_768": (12, 28),
        "lateral_minus_768": (12, 28),
    }
    for label, pair in expected.items():
        after = cases[label]["after"]["fields"]
        if (after["action_timer"], after["animation"]) != pair or \
                after["state"] != 5:
            gaps.append(f"component boundary failed for {label}")
    if doc["live"]["component_boundary"][
            "pre_edit_fields_block_cycle_equal"] is not True:
        gaps.append("component boundary branches differed before edits")

    native = doc["live"]["native_movie_oracle"]["checkpoints"]
    if (native["406"]["player"]["fields"]["state"],
            native["406"]["player"]["fields"]["action_timer"],
            native["406"]["player"]["fields"]["animation"]) != (1, 12, 28):
        gaps.append("native landing initializer changed")
    if (native["500"]["player"]["fields"]["state"],
            native["500"]["player"]["fields"]["action_timer"],
            native["500"]["player"]["fields"]["animation"]) != (5, 12, 28):
        gaps.append("native timer-12 slide signature changed")
    if native["714"]["player"]["fields"]["state"] != 0:
        gaps.append("native Cross release did not terminate state 5")

    steering = doc["live"]["steering_counterfactual"]
    if not all((steering["pre_edit_fields_equal"],
                steering["pre_edit_block_equal"],
                steering["pre_edit_cycle_equal"])):
        gaps.append("steering branches differed before Left removal")
    control = steering["control"]["after"]["fields"]
    edited = steering["edited"]["after"]["fields"]
    if control["action_timer"] != 12 or edited["action_timer"] != 12 or \
            control["heading"] == edited["heading"] or \
            (control["x"], control["z"]) == (edited["x"], edited["z"]):
        gaps.append("Left-only steering counterfactual did not diverge")

    cold = doc["live"]["cold_boot"]
    if not all((cold["pre_edit_fields_equal"], cold["pre_edit_block_equal"],
                cold["pre_edit_cycle_equal"])):
        gaps.append("cold-boot branches differed before Cross addition")
    cf = cold["control"]["after"]["fields"]
    ef = cold["edited"]["after"]["fields"]
    if (cf["state"], cf["action_timer"], cf["animation"]) != (0, 10, 6) or \
            (ef["state"], ef["action_timer"], ef["animation"]) != (5, 12, 28):
        gaps.append("cold-boot Cross-only continuation failed")

    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or breadth["applicable_anchors"] != 18 or \
            len(breadth["native_state4_landing_state5_labels"]) != 18:
        gaps.append("gameplay breadth is not 19 anchors / 18 native landings")
    if (breadth["exception_state"], breadth["exception_animation"],
            breadth["exception_action_timer"]) != (0, 4, 0):
        gaps.append("Riverbed Flight exception changed")

    trace = doc["live"]["control_checked_trace"]
    if not all(trace["comparison"].get(key) is True for key in (
            "cycle_neutral", "same_cycle", "same_frame", "same_ram",
            "same_registers")) or any(
                row["coverage"]["truncated"] is not False
                for row in trace["coverage"]):
        gaps.append("control-checked slide trace changed native execution")
    writer = doc["live"]["writer_trace"]
    if writer["truncated"] or any(
            row.get("truncated") or not row.get("events")
            for row in writer["execution"].values()):
        gaps.append("writer attribution is absent or truncated")

    contacts = doc["live"]["contact_matrix"]["summary"]
    if contacts["active_classes"] != 28 or \
            contacts["offensive_target_response_classes"] != [] or \
            len(contacts["ordinary_contact_damaged_player_classes"]) != 8 or \
            len(contacts["player_health_preserved_classes"]) != 20:
        gaps.append("slide damage/contact classification changed")

    pause = doc["live"]["pause_resume"]
    if (pause["paused"]["pause_flag"], pause["frozen"]["pause_flag"],
            pause["resumed"]["pause_flag"]) != (1, 1, 0):
        gaps.append("pause/resume flags changed")
    death = doc["live"]["death_respawn"]
    if (death["respawn"]["fields"]["action_timer"],
            death["respawn"]["fields"]["state"]) != (0, 0) or \
            death["fresh_slide_entry"]["state5"]["fields"]["state"] != 5:
        gaps.append("native respawn did not reset and re-enter A06")

    negative = doc["live"]["shared_state_5_negative"]["state5"]["fields"]
    if negative["state"] != 5 or negative["action_timer"] != 0 or \
            negative["animation"] == 28:
        gaps.append("state-5 negative no longer falsifies the old discriminator")
    return gaps


def test_static_slide_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = slide.build_static_census()
    assert recomputed == retained
    assert slide.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["slide_physics_setup"]["sha256"] == (
        "21b67c75db6ab6abdbb7f24391db803842eadb2becc184fef429ba9aa81f0402")
    assert recomputed["regions"]["slide_latch"]["sha256"] == (
        "1db5764ffa0bd75df1346e8ea1def61452d919e6ff2c5c4423540c126000b4b0")


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = slide.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["component_threshold_inclusive_min"] = 767
    assert "inclusive 768" in " ".join(slide.static_census_gaps(mutated))

    executable = bytearray(slide.EXE_PATH.read_bytes())
    executable[slide._va_offset(0x80048F0C)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        slide.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["component_boundary"]["cases"]["forward_768"][
        "after"]["fields"]["action_timer"] = 11
    assert "forward_768" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["contact_matrix"]["summary"][
        "offensive_target_response_classes"] = ["9:4011"]
    assert "damage/contact" in " ".join(evidence_gaps(mutated))


def test_retained_slide_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []
    coverage = doc["live"]["control_checked_trace"]["coverage"]
    assert [(row["coverage"]["total_hits"],
             row["coverage"]["distinct_pc_count"])
            for row in coverage] == [(33608, 284), (19606, 162)]
    controller_pcs = {row["pc"] for row in coverage[0]["coverage"]["counts_by_pc"]}
    animation_pcs = {row["pc"] for row in coverage[1]["coverage"]["counts_by_pc"]}
    assert {"0x800484a4", "0x800484b4", "0x80048ce4",
            "0x80048df8", "0x80048e00", "0x80048f3c"} <= controller_pcs
    assert {"0x8005684c", "0x80056860"} <= animation_pcs

    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_downhill_slide.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "downhill_slide")
    finding = common.finding_index()["downhill_slide_controller"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_slide_schema_matches_static_and_live_boundaries():
    schema = yaml.safe_load(
        (ROOT / "config/phase4_downhill_slide.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-downhill-slide/1"
    assert int(schema["decoded_input"]["cross_mask"], 16) == \
        static["law"]["cross_mask"]
    assert schema["carry_latch"]["component_threshold_inclusive_min"] == 768
    assert schema["carry_latch"]["forward_decay_per_player_update"] == 2
    assert schema["carry_latch"]["lateral_decay_per_player_update"] == 8
    assert schema["carry_latch"]["animation"] == 28
    assert schema["terrain"]["explicit_slope_predicate"] is None
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
