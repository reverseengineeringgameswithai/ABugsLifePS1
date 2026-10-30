"""Falsification and retained-evidence guards for Phase-4 A01."""
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
import phase4_run_locomotion as run  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_run_locomotion.json"
ARTIFACT_SHA256 = "96e22099965c4df517b06d798b62c29fd0128e99ec0507b4e33653a7a9d4d7d2"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    breadth = doc["live"]["breadth"]["summary"]
    exact_lengths = {
        "ordinary_labels": 18,
        "up_observed_labels": 19,
        "ordinary_moved_labels": 18,
        "ordinary_outcome_delta_labels": 18,
        "ordinary_animation_0_labels": 18,
        "ordinary_proposal_exact_labels": 18,
    }
    if breadth["anchors_compared"] != 19 or breadth["ordinary_anchors"] != 18:
        gaps.append("gameplay breadth is not exactly 19/18 anchors")
    for key, expected in exact_lengths.items():
        if len(breadth[key]) != expected:
            gaps.append(f"breadth predicate is incomplete: {key}")
    if breadth["flight_animation"] != run.FLIGHT_ANIMATION or \
            breadth["flight_outcome_differences"]:
        gaps.append("Riverbed Flight negative control diverged")

    cold = doc["live"]["cold_boot"]
    if cold["pre_edit_field_differences"] or not all((
            cold["pre_edit_block_equal"], cold["pre_edit_cycle_equal"],
            cold["pre_edit_emulator_frame_equal"])):
        gaps.append("cold-boot branches differ before the edit window")
    if cold["control_up"]["after"]["fields"]["forward_component"] == 0 or \
            cold["edited_neutral"]["after"]["fields"]["forward_component"] != 0:
        gaps.append("cold-boot Up/neutral forward-component delta is absent")

    controls = doc["live"]["controls"]
    if any(row["after"]["working_actions"] & run.DIRECTION_MASK !=
           row["expected_mask"] for row in controls["directions"].values()):
        gaps.append("D-pad decoded direction control failed")
    analog = controls["analog"]
    if analog["deadzone"]["displacement_x"] or analog["deadzone"]["displacement_z"]:
        gaps.append("analog deadzone moved the player")
    if not (0 < abs(analog["half_up"]["after"]["fields"]["forward_component"]) <
            abs(analog["full_up"]["after"]["fields"]["forward_component"])):
        gaps.append("analog magnitude did not scale the forward component")

    trace = doc["live"]["writer_trace"]
    required = {
        "0x80048044", "0x800491a4", "0x800494ac", "0x800494b0",
        "0x80049524", "0x80049540", "0x80036ce8", "0x80036cf0",
    }
    pcs = {str(row["instruction_pc"]).lower()
           for row in trace["dpad_up"]["events"]}
    if any(row["truncated"] or row["execution"]["truncated"]
           for row in trace.values()) or not required <= pcs:
        gaps.append("decisive controller/integrator trace is absent or truncated")
    return gaps


def test_static_run_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = run.build_static_census()
    assert recomputed == retained
    assert run.static_census_gaps(recomputed) == []
    assert len(recomputed["instruction_words"]) == 26
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["horizontal_controller"]["sha256"] == (
        "8e8693ef3a80f340307c026ec30fe66405702b6744875957e080e8803473a008")


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = run.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["default_turn_step"] = 257
    assert "default_turn_step differs from 256" in run.static_census_gaps(mutated)

    executable = bytearray(run.EXE_PATH.read_bytes())
    executable[run._va_offset(0x800494B0)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        run.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["breadth"]["summary"]["ordinary_moved_labels"].pop()
    assert "breadth predicate is incomplete: ordinary_moved_labels" in \
        evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["cold_boot"]["pre_edit_cycle_equal"] = False
    assert "cold-boot branches differ before the edit window" in evidence_gaps(mutated)


def test_retained_run_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []

    breadth = doc["live"]["breadth"]
    for row in breadth["anchors"].values():
        assert row["up_action_first_sample"] in (1, 2, 3)
        assert row["up_action_contiguous_after_latch"] is True
        assert row["up_action_samples"] >= 58
    assert breadth["summary"]["resolver_adjusted_labels"]
    assert breadth["summary"]["vertical_response_labels"]

    controls = doc["live"]["controls"]
    curve = controls["acceleration_release_reentry"]
    assert curve["start"]["forward_component"] == 0
    assert max(map(abs, curve["changed_speeds"])) >= 1700
    assert curve["release"][-1]["forward_component"] == 0
    assert curve["reentry"][-1]["forward_component"] != 0
    steps = controls["turn_up_to_right"]["heading_steps"]
    assert len(steps) >= 10
    assert max(row["step"] for row in steps) <= run.DEFAULT_TURN_STEP

    pause = doc["live"]["pause_resume"]
    assert pause["frozen_fields"] == [
        "x", "y", "z", "forward_component", "animation"]
    assert pause["resumed_after_up"]["pause_flag"] == 0
    assert pause["resumed_after_up"]["fields"]["animation"] == run.RUN_ANIMATION

    death = doc["live"]["death_respawn"]
    assert death["respawn"]["fields"]["health"] == 4
    assert death["respawn"]["fields"]["lives"] == death["before"]["fields"]["lives"] - 1
    assert death["post_respawn_run"]["fields"]["animation"] == run.RUN_ANIMATION

    trace = doc["live"]["writer_trace"]
    assert {int(row["regs"]["v0"], 16) for row in
            trace["analog_half"]["execution"]["events"]} == {8192}
    assert trace["analog_deadzone"]["execution"]["events"] == []

    cold = doc["live"]["cold_boot"]
    assert cold["edit_recipe"]["edited_frame_count"] == 60
    for side in ("control_up", "edited_neutral"):
        for key in ("started", "before_movie", "after_movie"):
            assert cold[side][key]["reproducible"] is True
            assert cold[side][key]["truncated"] is False

    provenance = doc["run_provenance"]
    assert provenance["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_run_locomotion.py").read_bytes()).hexdigest()
    assert provenance["rpc_manifest"]["source"]["method_count"] == 203
    assert provenance["duckstation"]["binary_sha256"] == (
        "c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec")
    assert provenance["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "run_locomotion")
    finding = common.finding_index()["run_locomotion_controller"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_run_schema_matches_static_and_live_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_run_locomotion.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-run-locomotion/1"
    assert int(schema["decoded_input"]["direction_mask"], 16) == \
        static["law"]["direction_mask"]
    assert schema["horizontal_controller"]["forward_component"]["ordinary_target"] == 1792
    assert schema["horizontal_controller"]["lateral_component"]["friction"] == 256
    assert schema["animation"]["ordinary_run_animation"] == 0
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
