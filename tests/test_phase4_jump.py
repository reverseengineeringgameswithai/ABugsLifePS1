"""Falsification and retained-evidence guards for Phase-4 A03."""
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
import phase4_jump as jump  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_jump.json"
ARTIFACT_SHA256 = "456d1cd488a66fcc735942268a9fd12509b48562daec5d828a92565dbe86937a"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    controls = doc["live"]["controls"]
    heights = controls["height_curve"]
    if heights != sorted(heights) or len(set(heights)) < 5:
        gaps.append("held-Cross height curve is not monotone with five distinct outcomes")
    if controls["super_flag_0x20"]["height"] <= controls["normal"]["height"]:
        gaps.append("native super-jump modifier does not increase height")

    coyote = doc["live"]["coyote_controls"]
    if coyote["inside_512_guard_clear"]["after"]["fields"]["state"] != 1:
        gaps.append("inside-threshold coyote positive did not take off")
    if any(coyote[key]["after"]["fields"]["state"] == 1 for key in (
            "boundary_1024_guard_clear", "inside_512_guard_set")):
        gaps.append("coyote threshold or guard negative took off")

    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or breadth["applicable_anchors"] != 18:
        gaps.append("gameplay breadth is not 19 anchors / 18 ordinary paths")
    for key in ("airborne_labels", "returned_grounded_labels",
                "rise_animation_3_labels"):
        if len(breadth[key]) != 18:
            gaps.append(f"breadth predicate is incomplete: {key}")
    if set(breadth["exception_outcome_differences"]) != {
            "x", "y", "z", "velocity_y"} or \
            breadth["exception_animation"] != 4 or breadth["exception_state"] != 0:
        gaps.append("Riverbed Flight exceptional boundary changed")

    cold = doc["live"]["cold_boot"]
    if cold["pre_edit_field_differences"] or not all((
            cold["pre_edit_block_equal"], cold["pre_edit_cycle_equal"],
            cold["pre_edit_emulator_frame_equal"])):
        gaps.append("cold-boot branches differ before the Cross edit")
    control = cold["control_cross"]["after"]["fields"]
    edited = cold["edited_neutral"]["after"]["fields"]
    if (control["state"], control["grounded"], control["animation"]) != (1, 0, 3):
        gaps.append("cold-boot Cross control did not enter ordinary rise")
    if edited["state"] != 0 or edited["grounded"] == 0:
        gaps.append("cold-boot Cross removal did not remain grounded")

    trace = doc["live"]["writer_trace"]
    pcs = {str(row.get("instruction_pc")).lower() for row in trace["events"]}
    required = {"0x80048b60", "0x80048bdc", "0x80048be8",
                "0x80048bf4", "0x80048d50", "0x80048d8c", "0x80036cec"}
    if trace["truncated"] or not required <= pcs:
        gaps.append("decisive jump trace is absent or truncated")
    if any(row.get("truncated") or not (row.get("events") or [])
           for row in trace["execution"].values()):
        gaps.append("decisive jump execution watch is absent or truncated")
    return gaps


def test_static_jump_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = jump.build_static_census()
    assert recomputed == retained
    assert jump.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["jump_branch"]["sha256"] == (
        "c03f2352d7a3091962bc55cdd182b595622e74d2db37d1fe2456d38c0bfbc942")
    assert recomputed["regions"]["release_gravity"]["sha256"] == (
        "2f63206cd7a64ffde5f4d6fa418ceb2d0c3ec292f8084cede080afd1f3ed9661")


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = jump.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["normal_impulse"] = -3071
    assert "normal takeoff impulse is not -3072" in jump.static_census_gaps(mutated)

    executable = bytearray(jump.EXE_PATH.read_bytes())
    executable[jump._va_offset(0x80048B68)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        jump.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["controls"]["height_curve"][5] = 1
    assert "held-Cross height curve" in evidence_gaps(mutated)[0]
    mutated = copy.deepcopy(document)
    mutated["live"]["cold_boot"]["pre_edit_cycle_equal"] = False
    assert "cold-boot branches differ" in " ".join(evidence_gaps(mutated))


def test_retained_jump_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []

    controls = doc["live"]["controls"]
    assert controls["height_curve"] == [6336, 6336, 8256, 11520, 14016, 16896]
    assert controls["normal"]["height"] == 6336
    assert controls["super_flag_0x20"]["height"] == 9120

    pause = doc["live"]["pause_resume"]
    assert pause["frozen_fields"] == [
        "x", "y", "z", "velocity_y", "state", "grounded", "animation"]
    assert pause["paused_start"]["pause_flag"] == 1
    assert pause["paused_after_neutral"]["pause_flag"] == 1
    assert pause["cross_confirmed_resume_and_jump"]["pause_flag"] == 0

    death = doc["live"]["death_respawn"]
    assert death["respawn"]["fields"]["health"] == 4
    assert death["respawn"]["fields"]["lives"] == death["before"]["fields"]["lives"] - 1
    assert death["post_respawn_jump"]["fields"]["state"] == 1

    execution = doc["live"]["writer_trace"]["execution"]
    takeoff = execution["takeoff"]["events"][0]
    assert int(takeoff["regs"]["s3"], 16) == (jump.NORMAL_IMPULSE & 0xFFFFFFFF)
    assert int(takeoff["regs"]["s4"], 16) == (jump.NORMAL_IMPULSE & 0xFFFFFFFF)
    assert execution["velocity_commit"]["events"][0]["regs"]["s4"] == "0xfffff500"
    assert execution["collision_call"]["events"][0]["regs"]["a0"] == "0x800a6500"

    cold = doc["live"]["cold_boot"]
    assert cold["edit_recipe"]["edited_frame_count"] == 28
    for side in ("control_cross", "edited_neutral"):
        for key in ("started", "before_movie", "after_movie"):
            assert cold[side][key]["reproducible"] is True
            assert cold[side][key]["truncated"] is False

    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_jump.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "jump_controller")
    finding = common.finding_index()["ordinary_jump_controller"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_jump_schema_matches_static_and_live_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_jump.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-jump/1"
    assert int(schema["decoded_input"]["cross_mask"], 16) == static["law"]["cross_mask"]
    assert schema["ordinary_controller"]["takeoff"]["normal_impulse"] == -3072
    assert schema["ordinary_controller"]["takeoff"]["super_jump_impulse"] == -3776
    assert schema["ordinary_controller"]["held"]["gravity_per_player_update"] == 256
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
