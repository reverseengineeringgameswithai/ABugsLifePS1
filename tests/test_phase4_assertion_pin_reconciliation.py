"""Guards for bounded Phase-4 assertion identity reconciliation."""

import copy
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_reconcile_assertion_pins as reconcile  # noqa: E402


def test_assertion_reconciliation_is_fresh_and_semantically_bounded():
    updates, report = reconcile.build()
    assert report["valid"] is True and report["errors"] == []
    assert report["schema"] == "abl-phase4-assertion-pin-reconciliation/2"
    assert reconcile.OUTPUT.read_text() == reconcile.render_report(report)
    assert all(path.read_text() == rendered for path, rendered in updates)
    assert sum(row["assertions_checked"] for row in report["targets"]) > 700
    assert all(row["artifact_pins_changed"] == 0 for row in report["targets"])
    assert all(row["joined_hash_leaves_changed"] == 0
               for row in report["targets"])
    assert len(report["identity_artifacts"]) == len(reconcile.IDENTITY_ARTIFACTS)
    legacy = next(
        row for row in report["identity_artifacts"]
        if row["path"] == "analysis/phase4_method_legacy_live_index.json")
    assert legacy["sha256"] == common.sha256(
        ROOT / "analysis/phase4_method_legacy_live_index.json")
    exact_pc = next(
        row for row in report["identity_artifacts"]
        if row["path"] ==
        "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json")
    assert exact_pc["sha256"] == common.sha256(
        ROOT / "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json")
    transition = next(
        row for row in report["identity_artifacts"]
        if row["path"] ==
        "analysis/phase4_fmv_levelb_transition_relocalization.json")
    assert transition["sha256"] == common.sha256(
        ROOT / "analysis/phase4_fmv_levelb_transition_relocalization.json")
    chained_paths = {
        "config/phase4_fmv_levelb_two_pc_first_hit.yaml",
        "analysis/phase4_fmv_levelb_two_pc_first_hit.json",
        "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json",
        "analysis/phase4_fmv_levelb_pre15792_partition.json",
        "analysis/phase4_fmv_frame_sync_wait_ownership.json",
    }
    retained_paths = {
        row["path"] for row in report["identity_artifacts"]
    }
    assert chained_paths <= retained_paths
    for path in chained_paths:
        row = next(
            item for item in report["identity_artifacts"]
            if item["path"] == path)
        assert row["sha256"] == common.sha256(ROOT / path)
    validator = next(
        row for row in report["identity_artifacts"]
        if row["path"] == "tools/phase4_method_metrics.py")
    assert validator["sha256"] == common.sha256(
        ROOT / "tools/phase4_method_metrics.py")
    assert report["consumer_changes"] == []
    assert all(row["consumer_replacements"] == 0
               for row in report["identity_artifacts"])


def test_reconciler_repairs_an_artifact_pin_without_changing_expectation():
    source = yaml.safe_load(common.REGISTRY_PATH.read_text())
    mutated = copy.deepcopy(source)
    assertion = next(reconcile._assertions(mutated))
    original_expected = copy.deepcopy(assertion["expected"])
    assertion["sha256"] = "0" * 64
    repaired, changes = reconcile.reconciled_document(mutated)
    repaired_assertion = next(reconcile._assertions(repaired))
    assert repaired_assertion["sha256"] == common.sha256(
        common.ROOT / repaired_assertion["artifact"])
    assert repaired_assertion["expected"] == original_expected
    assert {row["kind"] for row in changes} == {"artifact_pin"}


def test_only_hash_valued_join_expectations_can_be_refreshed():
    source = yaml.safe_load(common.REGISTRY_PATH.read_text())
    mutated = copy.deepcopy(source)
    candidate = None
    for assertion in reconcile._assertions(mutated):
        if assertion["op"] != "eq":
            continue
        actual = reconcile._resolved_value(assertion["artifact"],
                                            assertion["json_path"])
        if isinstance(actual, str) and reconcile.SHA256_RE.fullmatch(actual):
            candidate = assertion
            break
    assert candidate is not None
    candidate["expected"] = "0" * 64
    repaired, changes = reconcile.reconciled_document(mutated)
    repaired_rows = list(reconcile._assertions(repaired))
    repaired_candidate = next(
        row for row in repaired_rows
        if (row["artifact"], row["json_path"], row["op"])
        == (candidate["artifact"], candidate["json_path"], candidate["op"]))
    assert repaired_candidate["expected"] == reconcile._resolved_value(
        candidate["artifact"], candidate["json_path"])
    assert any(row["kind"] == "joined_hash_leaf" for row in changes)


def test_retained_report_contains_no_migration_delta():
    retained = json.loads(reconcile.OUTPUT.read_text())
    assert all(not row["changes"] for row in retained["targets"])


def test_reconciler_never_rewrites_its_own_migration_boundary():
    assert Path(reconcile.__file__).resolve() not in reconcile._consumer_paths()
    assert reconcile.INITIAL_IDENTITY_SHA256[
        "analysis/phase4_method_legacy_live_index.json"
    ] == "7960b86c1034ddbba36ab62ce61625f8d5ea4ccdfa39ed1f59f722cdb9ac25d8"


def test_reconciler_preserves_retained_generated_date_across_calendar_days(
        monkeypatch, tmp_path):
    retained = tmp_path / "reconciliation.json"
    retained.write_text(json.dumps({"generated": "2001-02-03"}))
    monkeypatch.setattr(reconcile, "OUTPUT", retained)
    assert reconcile.stable_generated() == "2001-02-03"
    _updates, report = reconcile.build()
    assert report["generated"] == "2001-02-03"
