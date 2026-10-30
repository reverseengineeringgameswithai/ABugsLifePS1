"""The second-window index-interval receipt is exact and non-promoting."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_index_interval_demo as demo  # noqa: E402
import phase4_inventory  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_index_interval_non_f01_demo.json"

pytestmark = pytest.mark.skipif(not ARTIFACT.is_file(),
                                reason="demonstration receipt absent")


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(ARTIFACT.read_bytes())


def test_retained_receipt_is_fresh():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_index_interval_demo.py"),
         "--output", str(ARTIFACT), "--check"],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_exact_resident_store_and_table_address_universes(receipt):
    universe = receipt["universe"]
    assert universe["source_store_access_rows"] == 11352
    assert len(universe["c_rejected_source_rows"]) == 78
    assert sum(universe["base_definition_class_tally"].values()) == 11352
    assert universe["table_address_class_store_rows"] == 124
    assert len(universe["table_address_class_store_site_ids"]) == 124
    assert universe["every_selected_site_processed"] is True
    assert {row["id"] for row in receipt["sites"]} == set(
        universe["table_address_class_store_site_ids"])


def test_interval_and_convention_counts_are_on_the_same_exact_universe(receipt):
    interval = receipt["interval_measurement"]
    assert interval["decided"]["count"] == 0
    assert interval["unproved"]["count"] == 110
    assert interval["proved_but_does_not_exclude_window"]["count"] == 6
    assert interval[
        "address_decided_but_external_entry_unclosed"]["count"] == 8
    assert sum(bucket["count"] for bucket in interval.values()) == 124
    assert receipt["pre_external_entry_gate_measurement"][
        "address_decided"]["count"] == 8
    convention = receipt["convention_measurement_on_same_universe"]
    assert convention["any_region_provenance_exclusion"]["count"] == 46
    assert convention["index_sign_or_loop_bound_convention_exclusion"]["count"] == 1
    assert convention["unconditional_alignment_exclusion"]["count"] == 45
    comparison = receipt["comparison_exact_sets"]
    assert comparison[
        "decided_by_both_interval_and_assumption_convention"]["count"] == 0
    assert comparison[
        "decided_by_interval_not_assumption_convention"]["count"] == 0
    assert comparison[
        "decided_by_assumption_convention_not_interval"]["count"] == 1


def test_every_interval_decision_has_a_full_instruction_derivation(receipt):
    lo = int(receipt["window"]["start"], 16)
    hi = int(receipt["window"]["end"], 16)
    decided_ids = set(receipt["interval_measurement"]["decided"]["site_ids"])
    queries = {row["id"]: row["result"]
               for row in receipt["index_domain_queries"]}
    for row in receipt["sites"]:
        assert row["derivations"]
        if row["id"] in decided_ids:
            assert row["interval_outcome"] == "interval_decided"
            assert row["breaking_instruction"] is None
            for derivation in row["derivations"]:
                query = queries[derivation["index_domain_query_id"]]
                assert query["verdict"] is True
                assert query["all_reaching_definitions_whitelisted"] is True
                assert derivation["no_32bit_wrap"] is True
                a, b = map(lambda value: int(value, 16),
                           derivation["effective_address_interval"])
                assert b <= lo or a >= hi
        elif row["interval_outcome"] == "interval_unproved":
            breaker = row["breaking_instruction"]
            assert breaker and breaker["pc"] and breaker["word"] and breaker["reason"]


def test_ram_alias_and_unknown_entry_gates_are_exact(receipt):
    alias_rows = {
        row["id"] for row in receipt["sites"]
        if any((derivation.get("ps1_ram_alias_check") or {}).get(
            "overlapping_aliases") for derivation in row["derivations"])}
    assert len(alias_rows) == 6
    closure = receipt["external_indirect_transfer_closure"]
    assert closure["site_count"] == 247
    assert closure["complete_indirect_jump_site_count"] == 87
    assert closure["unknown_indirect_jump_site_count"] == 20
    assert closure["unknown_indirect_call_site_count"] == 140
    assert len(closure["unknown_transfer_site_ids"]) == 160
    catalogs = {row["id"]: row for row in receipt["external_entry_sets"]}
    assert catalogs
    for row in receipt["sites"]:
        entry_set = catalogs[row["external_interior_entry_set_id"]]
        assert entry_set["entry_count"] == row["external_interior_entry_count"]
        assert entry_set["entry_count"] > 0


def test_local_ra_ratchet_movement_is_exact_in_both_directions(receipt):
    movement = receipt["diagnostic_outcome_movement_from_05bc6b8a251b"]
    assert movement["baseline_universe_count"] == 739
    assert movement["current_universe_count"] == 124
    assert len(movement["baseline_only_ids"]) == 615
    assert movement["current_only_ids"] == []
    categories = movement["categories"]
    assert len(categories["external_interior_entry"]["lost_ids"]) == 13
    assert categories["external_interior_entry"]["gained_ids"] == []
    assert len(categories["proved_interval_does_not_exclude_window"][
        "lost_ids"]) == 22
    assert categories["proved_interval_does_not_exclude_window"][
        "gained_ids"] == []
    assert categories["interval_unproved"]["gained_ids"] == []
    assert len(categories["interval_unproved"]["lost_ids"]) == 580


def test_receipt_has_no_row_or_gate_authority(receipt):
    assert receipt["window"] == {
        "start": "0x800a657e", "end": "0x800a6580", "width": 2,
        "not_f01": True}
    assert receipt["authority"] == {
        "capability_measurement_only": True,
        "changes_f01_status": False,
        "changes_demonstration_row_status": False,
        "changes_campaign_registry": False,
        "promotes_any_dimension": False,
    }


def test_demo_generator_receipt_and_test_are_inventory_declared():
    inventory = yaml.safe_load(
        (ROOT / "config/phase4_inventory.yaml").read_bytes())
    generators = {row["path"]: row for row in inventory["generators"]}
    assert generators["tools/phase4_index_interval_demo.py"] == {
        "path": "tools/phase4_index_interval_demo.py",
        "classification": "local_media",
        "outputs": ["analysis/phase4_index_interval_non_f01_demo.json"],
    }
    assert "tests/test_phase4_index_interval_demo.py" in inventory["tests"]
    gaps = phase4_inventory.build_campaign_inventory()["gaps"]
    for path in ("tools/phase4_typed_state.py",
                 "tools/phase4_index_interval_demo.py"):
        assert path not in gaps["missing_generator_declarations"]
    for path in ("analysis/phase4_f01_typed_state.json",
                 "analysis/phase4_f01_abi_survey.json",
                 "analysis/phase4_index_interval_non_f01_demo.json"):
        assert path not in gaps["orphan_artifacts"]
    for path in ("tests/test_phase4_typed_state.py",
                 "tests/test_phase4_index_interval_demo.py"):
        assert path not in gaps["missing_test_declarations"]
    assert "config/phase4_f01_typed_state.yaml" not in \
        gaps["missing_schema_declarations"]
