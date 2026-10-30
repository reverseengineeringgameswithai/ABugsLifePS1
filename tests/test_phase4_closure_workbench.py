"""All-nine obligation, pilot, mutation, and live-escalation workbench guards."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_closure_workbench as workbench  # noqa: E402


def row(report, row_id):
    return next(value for value in report["rows"] if value["row_id"] == row_id)


def pilot(report, row_id):
    return next(value for value in report["pilots"] if value["row_id"] == row_id)


def test_retained_report_is_exact_107_by_9_and_never_self_promotes():
    report = workbench.build()
    assert report["schema"] == workbench.OUTPUT_SCHEMA
    assert report["summary"]["baseline_rows"] == 107
    assert report["summary"]["dimensions_per_row"] == 9
    assert report["summary"]["obligations"] == 963
    assert len(report["rows"]) == 107
    assert all(len(value["obligations"]) == 9 for value in report["rows"])
    assert [value["id"] for value in report["dimensions"]] == list(workbench.DIMENSIONS)
    assert report["authority"] == workbench.AUTHORITY
    assert all(value["dimension_promoted"] is False for value in report["pilots"])
    assert workbench.OUTPUT_PATH.read_bytes() == workbench.canonical_json(report)


def test_workbench_playbook_is_linked_from_the_phase4_roadmap():
    note = ROOT / ("ObsidianVault/Playbooks/Game Solving Roadmap/"
                   "Phase 4 - Frontier Closure Workbench.md")
    roadmap = ROOT / ("ObsidianVault/Playbooks/Game Solving Roadmap/"
                      "Phase 4 - Solve Every Gameplay and Engine Subsystem.md")
    assert note.is_file()
    assert "status: candidate" in note.read_text()
    assert "[[Phase 4 - Frontier Closure Workbench|" in roadmap.read_text()


def test_b06_and_e16_surface_real_review_candidates_without_inventing_campaigns():
    report = workbench.build()
    b06 = row(report, "B06_invincibility")
    e16 = row(report, "E16_streaming_overlays")
    assert b06["campaign_registered"] is False and b06["campaign_id"] is None
    assert e16["campaign_registered"] is False and e16["campaign_id"] is None
    b06_pilot = pilot(report, "B06_invincibility")
    assert b06_pilot["disposition"] == "review_ready_but_unregistered"
    assert b06_pilot["facts"] == {
        "candidate_sites": 251, "classified": 251,
        "residual_entries": 13, "unexplained": 0,
    }
    e16_pilot = pilot(report, "E16_streaming_overlays")
    assert e16_pilot["disposition"] == \
        "scope_limited_review_ready_but_unregistered"
    assert e16_pilot["facts"]["row_wide"] is False
    assert e16_pilot["facts"]["materialization_sites"] == 5
    e16_item2 = next(value for value in e16["obligations"]
                     if value["id"] == "complete_frontier")
    assert e16_item2["retained_state"] == "gap"
    assert e16_item2["review_state"] == "unregistered_scoped_claim"


def test_follow_on_pilots_distinguish_benchmark_localization_and_real_gap():
    report = workbench.build()
    assert pilot(report, "E15_fmv")["disposition"] == "ready_for_fresh_verifier"
    assert pilot(report, "C13_grain_harvester")["disposition"] == \
        "localization_ready_not_promotion"
    e08 = pilot(report, "E08_props_movers_gates")
    assert e08["disposition"] == "not_ready"
    assert not any("callback source verification missing" in error
                   for error in e08["errors"])
    assert any("unresolved boundaries" in error for error in e08["errors"])
    assert next(value for value in row(report, "E15_fmv")["obligations"]
                if value["id"] == "complete_frontier")["retained_state"] == "met"
    assert next(value for value in row(report, "C13_grain_harvester")["obligations"]
                if value["id"] == "complete_frontier")["retained_state"] == "partial"


def test_claim_index_preserves_scopes_and_exposes_conflicts_instead_of_resolving_them():
    report = workbench.build()
    index = report["claim_index"]
    assert index["counts"]["claims"] == len(index["claims"])
    assert index["counts"]["findings"] == len(index["findings"])
    assert index["conflicts"] == []
    e16 = next(value for value in index["claims"]
               if value["id"] == "scorecard:E16_streaming_overlays:complete_frontier")
    assert e16["claim"] == "met_in_scope"
    assert "three registered-chunk" in e16["scope"]
    assert e16["debt_state"] == "gap"
    assert any(value["supersedes"] for value in index["findings"])
    assert all(len(value["supersession_statement_sha256"]) == len(value["supersedes"])
               for value in index["findings"])


def test_work_packets_are_actionable_but_not_promotion_packets():
    report = workbench.build()
    packet = workbench.row_packet(report, "E08_props_movers_gates", "complete_frontier")
    assert packet["schema"] == "abl-phase4-work-packet/1"
    assert packet["campaign_registered"] is True
    assert [value["id"] for value in packet["obligations"]] == ["complete_frontier"]
    obligation = packet["obligations"][0]
    assert obligation["accelerator"] == "scoped semantic-frontier compiler with Z3 witnesses"
    assert obligation["missing_layers"] == ["callers_callees"]
    assert packet["pilots"][0]["disposition"] == "not_ready"
    assert packet["authority"]["promotes_row_or_dimension"] is False
    with pytest.raises(workbench.WorkbenchError, match="unknown Phase-4 row"):
        workbench.row_packet(report, "NOT_A_ROW")


def test_capsule_projection_is_hash_only_and_drops_private_absolute_roots():
    report = workbench.build()
    strings = json.dumps(report)
    assert "/home/" not in strings
    b06 = row(report, "B06_invincibility")["capsule_opportunity"]
    assert b06["capsules"]
    assert all("capsule_directory" not in value for value in b06["capsules"])
    assert all(len(value["capsule_tree_sha256"]) == 64 for value in b06["capsules"])
    assert report["shared_services"]["capsules"] == {
        "schema": "abl-phase4-trace-capsule-set-v1",
        "capsules": 50, "valid": True, "errors": [],
    }


def test_retained_green_bits_are_recomputed_from_current_source_hashes():
    report = workbench.build()
    receipts = report["shared_services"]["retained_receipts"]
    assert report["shared_services"]["fixture_audit_valid"] == \
        receipts["fixture_audit"]["ready"]
    assert report["shared_services"]["inventory_structural_ready"] == \
        receipts["campaign_inventory"]["ready"]
    assert all("/home/" not in json.dumps(value) for value in receipts.values())

    expected = {
        "one": ROOT / "analysis/mechanics_baseline.yaml",
        "two": ROOT / "config/phase4_campaigns.yaml",
    }
    synthetic = {
        "inputs": {key: workbench.sha256(path) for key, path in expected.items()},
        "structural_ready": True,
    }
    status = workbench._retained_receipt_status(synthetic, expected)
    assert status["ready"] is True and status["errors"] == []
    synthetic["inputs"]["one"] = "0" * 64
    stale = workbench._retained_receipt_status(synthetic, expected)
    assert stale["ready"] is False
    assert "INPUT_HASH_DRIFT:one" in stale["errors"]


def test_live_preflight_consumes_capsules_and_rejects_unneeded_api_change():
    report = workbench.build()
    plan = workbench.live_plan(
        report, "E15_fmv", "lifecycle", "exact_instruction_attribution",
        "exact first teardown instruction after natural completion",
        "same-anchor natural completion", "same-anchor pre-completion hold", None)
    assert plan["ready_for_isolated_live_design"] is True
    assert plan["duckstation_api_change_allowed"] is False
    assert plan["capsule_query"]["relevant"]
    assert plan["capsule_query"]["prior_offline_analysis"]
    redundant = workbench.live_plan(
        report, "E15_fmv", "lifecycle", "exact_instruction_attribution",
        "exact teardown PC", "positive", "control", "execTrace")
    assert redundant["ready_for_isolated_live_design"] is False
    assert "API_SURFACE_ALREADY_AVAILABLE" in redundant["errors"]
    missing = workbench.live_plan(
        report, "E16_streaming_overlays", "lifecycle", "missing_or_invalid_capsule",
        "no retained unload-transition capsule", "enter and leave level",
        "enter level and hold before exit", None)
    assert missing["ready_for_isolated_live_design"] is True


def test_b06_residual_mutations_fail_the_independent_adapter():
    source = json.loads((ROOT / "analysis/phase4_b06_promotion_residuals.json").read_text())
    mutations = [
        lambda row: row["ledger"].update(classified=250),
        lambda row: row["ledger"].update(unexplained=1),
        lambda row: row["ledger"].update(sites_without_a_proof=1),
        lambda row: row["bounded_residuals"][0].update(intersects_dimension=True),
        lambda row: row["bounded_residuals"][0].update(next_experiment=""),
        lambda row: row["linter_result"].update(rejections=["synthetic"]),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(source)
        mutate(changed)
        result = workbench._pilot_b06(changed, registered=False)
        assert result["disposition"] == "not_ready" and result["errors"]


def test_e16_scope_materialization_and_residual_mutations_fail_adapter():
    scorecard = json.loads((ROOT / "analysis/phase4_e16_dod_scorecard.json").read_text())
    residuals = json.loads((ROOT / "analysis/phase4_e16_promotion_residuals.json").read_text())
    materialization = json.loads(
        (ROOT / "analysis/phase4_e16_address_materialization.json").read_text())
    mutations = [
        lambda a, b, c: next(row for row in a["items"] if row["n"] == 2).update(
            state="met"),
        lambda a, b, c: a.update(scope_caveat="thin"),
        lambda a, b, c: b["bounded_residuals"][0].update(intersects_dimension=True),
        lambda a, b, c: c.update(sites_inside=4),
    ]
    for mutate in mutations:
        a, b, c = copy.deepcopy(scorecard), copy.deepcopy(residuals), copy.deepcopy(
            materialization)
        mutate(a, b, c)
        result = workbench._pilot_e16(a, b, c, registered=False)
        assert result["disposition"] == "not_ready" and result["errors"]


@pytest.mark.parametrize("mutate,match", [
    (lambda row: row.update(schema="abl-phase4-closure-workbench-policy/2"), "must use"),
    (lambda row: row["dimensions"][0].update(ordinal=True), "ordinal"),
    (lambda row: row["dimensions"][0].update(required_layers=[]), "required_layers"),
    (lambda row: row["frontier_policy"].update(unknown_is_disjoint=True),
     "unknown_is_disjoint"),
    (lambda row: row["frontier_policy"].update(
        strict_compiler_closure_equals_item2=True), "strict_compiler"),
    (lambda row: row["live_escalation"].update(capsule_is_frame_boundary_only=False),
     "authority boundary"),
    (lambda row: row["authority"].update(promotes_row_or_dimension=True), "authority"),
])
def test_policy_mutations_fail_closed(mutate, match):
    policy = workbench.load_yaml(workbench.POLICY_PATH)
    mutate(policy)
    with pytest.raises(workbench.WorkbenchError, match=match):
        workbench.validate_policy(policy)
