"""Fail-closed and mutation guards for promotion-packet preflight."""

import copy
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_promotion_preflight as preflight  # noqa: E402


def codes(document: dict, packet_id: str) -> set[str]:
    packet = next(row for row in document["packets"] if row["id"] == packet_id)
    return {row["code"] for row in packet["errors"]}


def test_retained_preflight_recomputes_byte_identically():
    assert preflight.OUTPUT_PATH.read_text() == preflight.render(preflight.build())


def test_controls_pass_and_open_c13_stays_rejected():
    document = json.loads(preflight.OUTPUT_PATH.read_text())
    verdicts = {row["id"]: row["verdict"] for row in document["packets"]}
    assert verdicts["E15_complete_frontier_retained_control"] == \
        "ready_for_fresh_verifier"
    assert verdicts["E08_original_oracle_retained_control"] == \
        "ready_for_fresh_verifier"
    assert verdicts["C13_complete_frontier_open_control"] == "not_ready"
    assert {"CLAIM_MISSING", "LAYER_KNOWLEDGE_MISSING", "RESIDUAL_INTERSECTS"} <= \
        codes(document, "C13_complete_frontier_open_control")
    assert document["registry_mutated"] is False


def test_stale_debt_and_fake_success_are_rejected():
    config = common.load_yaml(preflight.CONFIG_PATH)
    stale = copy.deepcopy(config)
    stale["debt_snapshot"]["sha256"] = "0" * 64
    assert {row["code"] for row in preflight.build(config=stale)["global_errors"]} == {
        "DEBT_HASH_STALE"}

    fake = copy.deepcopy(config)
    fake["packets"][0]["success"] = True
    document = preflight.build(config=fake)
    assert "FAKE_SUCCESS_FIELD" in codes(
        document, "E15_complete_frontier_retained_control")

    nested = copy.deepcopy(config)
    nested["packets"][0]["static_frontier"]["success"] = True
    document = preflight.build(config=nested)
    assert "FAKE_SUCCESS_FIELD" in codes(
        document, "E15_complete_frontier_retained_control")


def test_policy_path_layers_and_required_dispositions_are_immutable():
    config = common.load_yaml(preflight.CONFIG_PATH)
    missing_policy = copy.deepcopy(config)
    missing_policy["policy"] = "config/does-not-exist.yaml"
    assert "POLICY_PATH_INVALID" in {
        row["code"] for row in preflight.build(config=missing_policy)["global_errors"]}

    reduced_layers = copy.deepcopy(config)
    reduced_layers["layer_ids"].remove("source")
    reduced_layers["layer_ids"].remove("knowledge")
    document = preflight.build(config=reduced_layers)
    assert "LAYER_POLICY_INVALID" in {row["code"] for row in document["global_errors"]}
    assert "LAYER_SET_INCOMPLETE" not in codes(
        document, "E15_complete_frontier_retained_control")

    optionalized = copy.deepcopy(config)
    optionalized["packets"][0]["layer_dispositions"]["source"] = {
        "status": "not_applicable",
        "reason": "A deliberately long but invalid attempt to waive a canonical required layer.",
    }
    document = preflight.build(config=optionalized)
    assert "REQUIRED_LAYER_NOT_REQUIRED" in codes(
        document, "E15_complete_frontier_retained_control")


def test_frontier_writer_and_signedness_mutations_have_stable_codes():
    pilots = common.load_json("analysis/phase4_static_frontier_pilots.json")
    altered = copy.deepcopy(pilots)
    altered["E15_fmv"]["actual"]["player_xrefs"] = 57
    document = preflight.build(overrides={
        "analysis/phase4_static_frontier_pilots.json": altered})
    assert "FRONTIER_PLAYER_XREF_DRIFT" in codes(
        document, "E15_complete_frontier_retained_control")

    altered = copy.deepcopy(pilots)
    contract = altered["C13_grain_harvester"]["state_contract"]["powerup_flags"]
    contract["selected_writer"]["pc"] = "0x80051EB4"
    contract["reader_signedness"] = ["signed"]
    document = preflight.build(overrides={
        "analysis/phase4_static_frontier_pilots.json": altered})
    c13_codes = codes(document, "C13_complete_frontier_open_control")
    assert {"WRITER_DRIFT", "SIGNEDNESS_DRIFT"} <= c13_codes


def test_missing_paths_knowledge_residual_and_external_hash_fail_closed(monkeypatch):
    config = common.load_yaml(preflight.CONFIG_PATH)
    missing_path = copy.deepcopy(config)
    missing_path["packets"][0]["clean_checkout_dependencies"].append(
        "analysis/does-not-exist.json")
    document = preflight.build(config=missing_path)
    assert "CLEAN_DEPENDENCY_MISSING" in codes(
        document, "E15_complete_frontier_retained_control")

    registry = common.load_yaml(common.REGISTRY_PATH)
    mutated = copy.deepcopy(registry)
    e15 = next(row for row in mutated["child_campaigns"] if row["id"] == "fmv_playback")
    e15["dimension_claims"]["complete_frontier"]["residuals"][0][
        "intersects_dimension"] = True
    document = preflight.build(registry=mutated)
    assert "RESIDUAL_INTERSECTS" in codes(
        document, "E15_complete_frontier_retained_control")

    original_sha = preflight.sha256
    monkeypatch.setattr(preflight, "sha256", lambda path: "0" * 64
                        if Path(path).name.endswith(".sav") else original_sha(path))
    document = preflight.build()
    assert "EXTERNAL_HASH_DRIFT" in codes(
        document, "E08_original_oracle_retained_control")
