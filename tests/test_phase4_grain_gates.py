"""Falsification and retained-evidence guards for the completed E09 campaign."""
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
import phase4_grain_gates as gates  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_grain_gates.json"
ARTIFACT_SHA256 = "e15c0890a3795dc43be25ea16cb60790f0379e6920703172b15a163ad787ba54"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps = gates.static_census_gaps(doc["static_census"])
    if doc["fixture_census"]["count"] != 12:
        gaps.append("complete E09 fixture census changed")
    replays = doc["live"]["natural_replays"]
    if len(replays) != 12:
        gaps.append("natural replay count changed")
        return gaps
    for row in replays:
        if row["after"]["status"]["frame"] - row["before"]["status"]["frame"] \
                != row["fixture"]["frames"]:
            gaps.append("natural replay did not consume every recorded frame")
        if row["status"]["reproducible"] is not True \
                or row["status"]["truncated"] is not False:
            gaps.append("natural replay reproducibility changed")

    expected_changes = {0: 3, 2: 5, 4: 2, 5: 1, 7: 6}
    for movie_index, row in enumerate(replays[:9]):
        before = row["before"]["tunnels_table"]
        after = row["after"]["tunnels_table"]
        changed = [index for index in range(9)
                   if before[index]["state"] != after[index]["state"]]
        expected = [expected_changes[movie_index]] if movie_index in expected_changes else []
        if changed != expected:
            gaps.append(f"Tunnels natural transition changed for movie {movie_index}")
        for index in changed:
            if (before[index]["state"], after[index]["state"]) != (4295, 1680):
                gaps.append("Tunnels natural transition endpoints changed")
    if (replays[1]["before"]["lives"], replays[1]["after"]["lives"]) != (2, 1):
        gaps.append("closed-gate death boundary changed")
    if (replays[8]["before"]["scene"], replays[8]["after"]["scene"]) != (3, 1):
        gaps.append("game-over transition boundary changed")

    for index, row in enumerate(replays[9:]):
        threshold = 10 * (index + 1)
        if row["before"]["grain"] != threshold - 1 \
                or row["after"]["grain"] != threshold - 1 \
                or row["before"]["city_gate_states"][index] != -1 \
                or row["after"]["city_gate_states"][index] != -1:
            gaps.append(f"City threshold-minus-one negative changed for gate {index}")
    controls = doc["live"]["city_threshold_controls"]
    if len(controls) != 3:
        gaps.append("City threshold control count changed")
    for index, row in enumerate(controls):
        threshold = 10 * (index + 1)
        if row["threshold"] != threshold or row["mutation"]["before"] != threshold - 1 \
                or row["mutation"]["after"] != threshold \
                or row["before"]["city_gate_states"][index] != -1 \
                or row["after"]["city_gate_states"][index] != 0:
            gaps.append(f"City causal threshold transition changed for gate {index}")
    lifecycle = doc["live"]["successful_open_death_respawn"]
    for implementation, expected_scene, expected_gate in (
            ("tunnels", 3, 1680), ("city", 4, 0)):
        row = lifecycle[implementation]
        gate_index = row["target_gate_index"]
        before_gate = gates._gate_projection(row["before"], implementation)
        fatal_gate = gates._gate_projection(row["fatal"], implementation)
        respawn_gate = gates._gate_projection(row["respawn"], implementation)
        if row["before"]["scene"] != expected_scene or \
                row["fatal"]["scene"] != expected_scene or \
                row["respawn"]["scene"] != expected_scene or \
                before_gate[gate_index] != expected_gate or \
                fatal_gate != before_gate or respawn_gate != before_gate or \
                row["fatal"]["player"]["health"] >= 0 or \
                row["respawn"]["player"]["health"] != 4 or \
                row["respawn"]["lives"] != row["before"]["lives"] - 1 or \
                row["respawn"]["grain"] != row["before"]["grain"] or \
                row["respawn"]["player"]["safe_anchor"] != \
                row["before"]["player"]["safe_anchor"]:
            gaps.append(f"{implementation} successful-open lifecycle changed")
    card = doc["live"]["card_persistence"]
    native_load = card["native_load"]
    native_save = card["native_save"]
    if card["default_before_native_load"]["block_sha256"] == \
            native_load["after"]["block_sha256"] or \
            native_load["serialized_block_card_offsets"] != [8708, 16900]:
        gaps.append("native card load classification changed")
    if card["causal_mutation"]["resident_progress_byte"]["offset"] != 335 or \
            card["causal_mutation"]["resident_progress_byte"]["after"] != 0x5A or \
            native_save["serialized_block_card_offsets"] != [25092] or \
            native_save["card_before_sha256"] == native_save["card_after_sha256"] or \
            native_save["diff"]["size_before"] != 131072 or \
            native_save["diff"]["size_after"] != 131072 or \
            card["status"]["reproducible"] is not True or \
            card["status"]["truncated"] is not False:
        gaps.append("native card save classification changed")
    if doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is not True:
        gaps.append("owned debugger instance was not stopped")
    return gaps


def test_fixture_and_static_census_recompute_from_pinned_inputs():
    retained = load_artifact()
    assert gates.build_fixture_census() == retained["fixture_census"]
    assert gates.build_static_census() == retained["static_census"]
    assert gates.static_census_gaps(retained["static_census"]) == []
    assert retained["live_code_census"]["tunnels_initial_table"] == [
        dict(zip(("state", "id", "threshold", "x", "z"), values), index=index)
        for index, values in enumerate(gates.EXPECTED_TUNNELS_TABLE)
    ]
    central = json.loads(live.FIXTURE_SET.read_text())["entries"]
    menu = central[gates.MENU_MOVIE_REL]
    assert menu["sha256"] == retained["fixture_census"]["shared_card_movie"]["sha256"]
    runtime = yaml.safe_load(gates.RUNTIME_FIXTURES.read_text())["fixtures"] \
        ["go_to_end_repro_memory_card"]
    assert "tools/phase4_grain_gates.py" in runtime["consumers"]


def test_static_and_live_leaf_mutations_turn_the_e09_proof_red():
    static = gates.build_static_census()
    mutated = copy.deepcopy(static)
    mutated["law"]["city_thresholds"][1] = 19
    assert "law drifted" in " ".join(gates.static_census_gaps(mutated))

    overlay = bytearray(gates.CITY_OVERLAY.read_bytes())
    overlay[gates.CITY_OVERLAY_FUNCTION_OFFSET] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        # The staged-input guard is deliberately exercised directly because
        # build_static_census always reads the immutable provisioned path.
        gates.verify_staged_input(gates.CITY_OVERLAY_REL, bytes(overlay))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["natural_replays"][0]["after"]["tunnels_table"][3]["state"] = 4200
    assert "endpoints changed" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["city_threshold_controls"][2]["after"]["city_gate_states"][2] = -1
    assert "causal threshold" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["successful_open_death_respawn"]["tunnels"] \
        ["respawn"]["tunnels_table"][3]["state"] = 4295
    assert "successful-open lifecycle" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["card_persistence"]["native_save"] \
        ["serialized_block_card_offsets"] = []
    assert "native card save" in " ".join(evidence_gaps(mutated))


def test_retained_grain_gate_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert doc["campaign_state"] == "completed"
    assert evidence_gaps(doc) == []
    assert doc["live_code_census"]["tunnels_function"]["sha256"] == \
        "b5d7cd0da1401ecf8abebf55dcb0c0e142ef328b6d8809f783a04cf2e22baabd"
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_grain_gates.py").read_bytes()).hexdigest()
    assert run["duckstation"]["revision"] == \
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5"
    assert run["duckstation"]["binary_sha256"] == \
        "c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec"
    assert live.retained_pristine_save_gaps(doc) == []


def test_e09_campaign_is_completed_only_from_low_level_evidence():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "grain_gates")
    assert campaign["status"] == "completed"
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    coverage = phase4_coverage.build()
    assert coverage["rows"]["E09_grain_gates"]["state"] == "campaign_complete"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91


def test_grain_gate_schema_matches_machine_and_mod_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_grain_gates.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-grain-gates/1"
    assert schema["campaign_state"] == "completed"
    assert schema["city_entrance"]["thresholds"] == static["law"]["city_thresholds"]
    assert schema["tunnels"]["table"] == {
        "address": "0x800B4C1C", "stride": 0x14, "capacity": 9}
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
