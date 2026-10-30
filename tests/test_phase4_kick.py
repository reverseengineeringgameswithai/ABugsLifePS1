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
import phase4_kick as kick  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_kick.json"
ARTIFACT_SHA256 = "9a98c343164dd995a4425f1f9426a4f7e6ca429713143ad7552c2947bc3bc928"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    controls = doc["live"]["native_controls"]
    if any(controls["positive_chords"][side]["minimum_timer"] != -16
           for side in ("l2", "r2")):
        gaps.append("L2/R2 positive chord did not arm -16")
    negatives = controls["negative_controls"]
    for name in ("square_without_shoulder", "shoulder_without_square",
                 "square_preheld_then_shoulder", "player_gate_5c_nonzero"):
        if any(row["fields"]["kick_timer"] < 0
               for row in negatives[name]["samples"]):
            gaps.append(f"negative control armed: {name}")
    if negatives["floor_distance_1023"]["minimum_timer"] != -16 or \
            negatives["floor_distance_1024"]["minimum_timer"] != 0:
        gaps.append("exclusive 1024-unit floor boundary changed")
    if doc["live"]["recovery"]["distinct_timer_transitions"] != list(range(-16, 1)):
        gaps.append("kick recovery is not the exact -16..0 transition sequence")

    breadth = doc["live"]["input_breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or len(breadth["armed_labels"]) != 18:
        gaps.append("input breadth is not 19 anchors / 18 ordinary arms")
    if (breadth["exception_minimum_timer"], breadth["exception_animation"],
            breadth["exception_grounded"]) != (0, 4, 0):
        gaps.append("Riverbed Flight exceptional boundary changed")

    matrix = doc["live"]["contact_matrix"]["summary"]
    for key, expected in (("ordinary_kick_eligible", 20),
                          ("response_only_0x80", 3),
                          ("separate_actor_path_0x20", 2),
                          ("ordinary_contact_suppressed_0x800", 3),
                          ("static_live_classification_matches", 28)):
        if len(matrix[key]) != expected:
            gaps.append(f"contact class predicate changed: {key}")

    cold = doc["live"]["cold_boot"]
    if cold["pre_edit_field_differences"] or not all((
            cold["pre_edit_block_equal"], cold["pre_edit_cycle_equal"],
            cold["pre_edit_emulator_frame_equal"])):
        gaps.append("cold-boot branches differ before the input edit")
    if cold["control"]["after"]["fields"]["kick_timer"] != 0 or \
            cold["edited"]["after"]["fields"]["kick_timer"] >= 0 or \
            cold["edited"]["after"]["fields"]["animation"] != 1:
        gaps.append("cold-boot input counterfactual did not isolate kick")

    trace = doc["live"]["writer_trace"]["execution"]
    if any(row["truncated"] or not row["events"] for row in trace.values()):
        gaps.append("decisive kick execution trace is missing or truncated")
    if int(trace["timer_arm"]["events"][0]["regs"]["v0"], 16) != 0xFFFFFFF0:
        gaps.append("traced kick arm did not write -16")
    if int(trace["target_state_30"]["events"][0]["regs"]["v0"], 16) != 30:
        gaps.append("traced native contact did not select actor state 30")
    return gaps


def test_static_kick_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = kick.build_static_census()
    assert recomputed == retained
    assert kick.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["kick_arm"]["sha256"] == (
        "90364f8098cd49f1f14954fa3b33c5b9c8546eb51f2a6037b3cf88f3b6e08747")
    assert recomputed["regions"]["proximity_owner"]["sha256"] == (
        "f7f97dbbb6f91888c19e267fa72fee2cae4c95512a6f2b38c0db0b03ea69592a")


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = kick.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["timer_start"] = -15
    assert "kick timer does not arm at -16" in kick.static_census_gaps(mutated)

    executable = bytearray(kick.EXE_PATH.read_bytes())
    executable[kick._va_offset(0x80048F4C)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        kick.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["recovery"]["distinct_timer_transitions"][4] = -99
    assert "exact -16..0" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["contact_matrix"]["summary"][
        "static_live_classification_matches"].pop()
    assert "static_live_classification_matches" in " ".join(evidence_gaps(mutated))


def test_retained_kick_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []

    death = doc["live"]["death_respawn"]
    assert death["before"]["fields"]["kick_timer"] == 11
    assert death["respawn"]["fields"]["kick_timer"] == 0
    assert death["post_respawn_kick"]["minimum_timer"] == -16

    pause = doc["live"]["pause_resume"]
    assert pause["frozen_fields"] == ["x", "y", "z", "kick_timer", "animation"]
    assert pause["paused_start"]["pause_flag"] == 1
    assert pause["resumed"]["pause_flag"] == 0

    trials = doc["live"]["contact_matrix"]["trials"]
    ordinary = trials["9:4011"]
    assert ordinary["neutral"]["after"]["actor"]["state"] == 15
    assert ordinary["neutral"]["after"]["player"]["fields"]["health"] == 3
    assert ordinary["kick"]["after"]["actor"]["state"] == 30
    assert ordinary["kick"]["after"]["player"]["fields"]["health"] == 4
    assert trials["14:4085"]["kick"]["after"]["actor"]["state"] == 15
    assert trials["11:4030"]["kick"]["after"]["actor"]["state"] != 30

    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_kick.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "kick_attack")
    finding = common.finding_index()["ordinary_kick_attack"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_kick_schema_matches_static_live_and_mod_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_kick.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-kick/1"
    assert int(schema["decoded_input"]["shoulder_mask"], 16) == static["law"]["shoulder_mask"]
    assert int(schema["decoded_input"]["square_mask"], 16) == static["law"]["square_mask"]
    assert schema["ordinary_controller"]["timer"]["arm"] == -16
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
