"""Falsification and retained-evidence guards for Phase-4 E07."""
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
import phase4_event_vm as event_vm  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_event_vm.json"
ARTIFACT_SHA256 = "ffd57b372940018a8f0b0129bce88a479e1c040088bc90d5b02fb8a912069770"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps = event_vm.static_census_gaps(doc["static_census"])
    cold = doc["live"]["cold_boot"]
    if cold["scene"] != 1 or cold["fetch_total"] <= 0 or \
            cold["status"]["reproducible"] is not True or \
            cold["status"]["truncated"] is not False:
        gaps.append("cold-boot VM fetch did not reproduce")

    breadth = doc["live"]["breadth"]
    summary = breadth["summary"]
    if summary["anchors"] != 19 or len(summary["scenes"]) != 16 or \
            summary["traced_contexts"] < 5 or summary["fetch_events"] <= 0:
        gaps.append("VM gameplay breadth is incomplete")
    invalid = [
        (row["label"], actor["slot"])
        for row in breadth["trials"] for actor in row["before"]["records"]
        if actor["source"]["valid"] and actor["program"] is None
    ]
    if invalid:
        gaps.append("valid-source actor IP escaped the decoded program bank")
    if any(selector > 39 for selector in summary["observed_selectors"]):
        gaps.append("authored live selector escaped 0..39")

    selectors = doc["live"]["selector_controls"]["trials"]
    if [selectors[key]["actual_actor_ip"] for key in ("0", "39", "40")] != \
            ["0x8007745C", "0x80077AC0", "0x03020100"] or \
            selectors["40"]["in_valid_program_region"] is not False:
        gaps.append("selector positive/negative controls changed")

    pause = doc["live"]["pause_resume"]
    if (pause["paused"]["pause_flag"], pause["frozen"]["pause_flag"],
            pause["resumed"]["pause_flag"]) != (1, 1, 0) or \
            pause["paused"]["actors"]["raw_sha256"] != \
            pause["frozen"]["actors"]["raw_sha256"] or \
            pause["post_trace_actors"]["raw_sha256"] == \
            pause["frozen"]["actors"]["raw_sha256"]:
        gaps.append("VM pause/resume lifecycle changed")

    death = doc["live"]["death_respawn"]
    if death["respawn"]["health"] != 4 or \
            death["respawn"]["lives"] != death["before"]["lives"] - 1 or \
            death["respawn"]["scene"] != death["before"]["scene"] or \
            death["post_respawn_trace"]["fetch_total"] <= 0:
        gaps.append("native respawn did not rebuild and rearm the VM")

    reuse = doc["live"]["scene_reuse"]
    rows = reuse["loads"]
    if [row["scene"] for row in rows] != [1, 3, 1] or \
            rows[0]["actor_sources"] != rows[2]["actor_sources"] or \
            rows[0]["actor_sources"] == rows[1]["actor_sources"]:
        gaps.append("scene transition did not rebuild actor/source ownership")
    return gaps


def test_static_event_vm_census_recomputes_from_pinned_pristine_inputs():
    retained = load_artifact()["static_census"]
    recomputed = event_vm.build_static_census()
    assert recomputed == retained
    assert event_vm.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["vm"]["selector_count"] == 40
    assert recomputed["instruction_count"] == 421
    assert recomputed["overlays"]["images"] == 20
    assert recomputed["overlays"]["exact_function_bindings_count"] == 9


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    static = event_vm.build_static_census()
    mutated = copy.deepcopy(static)
    mutated["vm"]["selector_count"] = 13
    assert "selector table" in " ".join(event_vm.static_census_gaps(mutated))
    mutated = copy.deepcopy(static)
    mutated["call_slot_occurrences"].pop("9")
    assert "CALL slot" in " ".join(event_vm.static_census_gaps(mutated))

    executable = bytearray(event_vm.EXE_PATH.read_bytes())
    offset = event_vm.EXE_HEADER + event_vm.SELECTOR_LOAD - event_vm.EXE_BASE
    executable[offset] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        event_vm.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["selector_controls"]["trials"]["40"][
        "in_valid_program_region"] = True
    assert "selector positive/negative" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["pause_resume"]["frozen"]["pause_flag"] = 0
    assert "pause/resume" in " ".join(evidence_gaps(mutated))


def test_retained_event_vm_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_event_vm.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["duckstation"]["revision"] == (
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5")
    assert run["duckstation"]["binary_sha256"] == (
        "c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec")
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_event_vm_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "event_vm")
    finding = common.finding_index()["event_vm_contract"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []


def test_event_vm_schema_matches_static_and_mod_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_event_vm.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-event-vm/1"
    assert schema["resident_vm"]["program_selector_table"]["slots"] == \
        static["vm"]["selector_count"]
    assert len(schema["call_slots"]) == 9
    assert schema["overlay_contract"]["pinned_images"] == \
        static["overlays"]["images"]
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
