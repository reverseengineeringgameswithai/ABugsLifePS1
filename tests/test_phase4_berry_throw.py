"""Falsification and retained-evidence guards for Phase-4 A08."""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_berry_throw as berry  # noqa: E402
import phase4_common as common  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_berry_throw.json"
ARTIFACT_SHA256 = "83e4b56c0290de42e6a00e0831299bc255fe24be2bb6d39b2a71c2448f66b57d"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    cold = doc["live"]["cold_boot"]
    if cold["pre_edit_field_differences"] or not all((
            cold["pre_edit_block_equal"], cold["pre_edit_cycle_equal"],
            cold["pre_edit_emulator_frame_equal"])):
        gaps.append("cold-boot branches differ before fresh Square")
    spawn = cold["edited"]["execution"]["spawn_return"]
    if len(spawn["events"]) != 1 or \
            int(spawn["events"][0]["regs"]["s1"], 16) != 2:
        gaps.append("cold-boot fresh Square did not spawn red class 2")

    gates = doc["live"]["gate_controls"]["cases"]
    for label in doc["live"]["gate_controls"]["allow_cases"]:
        if not gates[label]["arm_trace"]["events"]:
            gaps.append(f"positive berry gate did not arm: {label}")
    for label in doc["live"]["gate_controls"]["block_cases"]:
        if gates[label]["arm_trace"]["events"]:
            gaps.append(f"negative berry gate armed: {label}")
    edge = gates["fresh_edge"]
    if edge["blocked_while_first_held"]["fields"]["throw_windup"] != 0 or \
            edge["blocker_cleared_while_still_held"]["fields"]["throw_windup"] != 0 or \
            edge["fresh_after_release"]["fields"]["throw_windup"] <= 0:
        gaps.append("Square edge control changed")

    selectors = doc["live"]["selector_matrix"]
    if selectors["selector_type_pairs"] != [[0, 2], [1, 5], [2, 8],
                                               [3, 11], [4, 45]]:
        gaps.append("native selector/type map changed")
    for raw, row in selectors["trials"].items():
        selector = int(raw)
        if row["descriptor_type"] != row["expected_type"] or \
                (row["aim_helper_hits"] > 0) != (selector in (0, 1, 3)):
            gaps.append(f"selector descriptor/aim split changed: {selector}")

    arc = doc["live"]["straight_arc_and_retirement"]
    if len(arc["samples"]) < 8 or arc["retired"]["record"]["lifetime_ttl"] != 0 or \
            arc["retired"]["player"]["fields"]["berries_in_flight"] != 0:
        gaps.append("straight trajectory/retirement evidence is incomplete")
    for index, delta in enumerate(arc["per_update_deltas"]):
        before = arc["samples"][index]
        if delta["delta_position"] != before["velocity"] or \
                delta["delta_velocity_y"] != 128 or delta["ttl_delta"] != -1:
            gaps.append("straight integration order changed")
            break

    for selector, primary, secondary, mode, return_pc in (
            ("2", 8, 16, "0x00000001", "0x80057584"),
            ("4", 45, 48, "0x00000000", "0x80057540")):
        row = doc["live"]["homing_transitions"][selector]
        if (row["primary_type"], row["secondary_type"]) != (primary, secondary) or \
                row["acquisition_trace"]["events"][0]["regs"]["a1"] != mode or \
                row["secondary_spawn"]["return_pc"] != return_pc or \
                row["secondary_spawn"]["record_after_native_update"]["flags"] & 8 == 0 or \
                row["retired"]["in_flight"] != 0:
            gaps.append(f"homing lifecycle changed: selector {selector}")

    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or len(breadth["spawned_labels"]) != 18 or \
            breadth["blocked_labels"] != ["bonus2_mushrooms"] or \
            breadth["riverbed_flight_spawned"] is not True:
        gaps.append("gameplay breadth is not 19 anchors / 18 native throws")

    pause = doc["live"]["pause_resume"]
    if (pause["paused"]["player"]["pause_flag"],
            pause["frozen"]["player"]["pause_flag"],
            pause["resumed"]["player"]["pause_flag"]) != (1, 1, 0) or \
            pause["paused"]["record"]["record_sha256"] != \
            pause["frozen"]["record"]["record_sha256"]:
        gaps.append("projectile pause/resume changed")
    death = doc["live"]["death_respawn"]
    if death["before"]["fields"]["berries_in_flight"] != 3 or \
            death["respawn"]["fields"]["berries_in_flight"] != 0 or \
            not death["fresh_post_respawn_throw"]["execution"]["spawn_return"]["events"]:
        gaps.append("native respawn did not clear and rearm A08")
    return gaps


def test_static_berry_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = berry.build_static_census()
    assert recomputed == retained
    assert berry.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["throw_gate"]["sha256"] == (
        "fcad27d427db56f52c528954d6a556f9b7025e286297bdbebddfe81fd2fc622c")
    assert recomputed["regions"]["projectile_update"]["sha256"] == (
        "a95bb0c5dbdd8b97df049879436427329d63ee51ed8e6ef2a523525a65933577")


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = berry.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["gravity_per_projectile_update"] = 127
    assert "gravity" in " ".join(berry.static_census_gaps(mutated))

    executable = bytearray(berry.EXE_PATH.read_bytes())
    executable[berry._va_offset(0x80048FC4)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        berry.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["selector_matrix"]["selector_type_pairs"][4][1] = 44
    assert "selector/type" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["straight_arc_and_retirement"]["per_update_deltas"][0][
        "delta_velocity_y"] = 127
    assert "integration" in " ".join(evidence_gaps(mutated))


def test_retained_berry_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_berry_throw.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_cold_boot_counterfactual_precedes_every_save_state_inspection():
    source = inspect.getsource(berry._run)
    assert source.index("cold_boot = _run_cold_boot") < \
        source.index("inspections = [inspect_state_before_load")


def test_completed_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "berry_throw")
    finding = common.finding_index()["ordinary_berry_throw"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_berry_schema_matches_static_live_and_mod_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_berry_throw.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-berry-throw/1"
    assert int(schema["decoded_input"]["square_mask"], 16) == static["law"]["square_mask"]
    assert [row["primary_type"] for row in schema["selectors"]["rows"]] == \
        [2, 5, 8, 11, 45]
    assert schema["pool"]["integration_order"] == [
        "position += current velocity", "velocity_y += gravity",
        "lifetime_ttl -= 1"]
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
