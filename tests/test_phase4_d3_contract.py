"""Guards for the frozen Phase-4 D3 contract reviewed negative."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis/phase4_d3_contract.json"
TOOL = ROOT / "tools/phase4_d3_contract.py"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"


def _doc() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_d3_contract_artifact_is_reproducible() -> None:
    subprocess.run(
        [sys.executable, str(TOOL), "--check"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    )


def test_frozen_universes_and_sample_are_exact() -> None:
    doc = _doc()
    universes = doc["universes"]
    assert universes["frozen_indirect_sites"]["count"] == 179
    assert len(universes["frozen_indirect_sites"]["site_ids"]) == 179
    assert universes["d3_pointer_dispatch"]["count"] == 140
    assert len(set(universes["d3_pointer_dispatch"]["site_ids"])) == 140
    assert universes["pilot"]["count"] == 12
    assert len(set(universes["pilot"]["site_ids"])) == 12
    assert universes["pilot"]["frozen_before_outcomes"] is True
    assert universes["protected_set"]["combined_unique_image_pc_count"] == 128
    assert len(set(universes["protected_set"]["combined_ids"])) == 128


def test_contract_partition_and_wall_labels_fail_closed() -> None:
    contracts = _doc()["contracts"]
    assert {name: row["sample_site_count"] for name, row in contracts.items()} == {
        "shared_dispatch_cell_0x8007fbc4": 10,
        "object_field_provenance": 1,
        "bios_ingress_exception": 1,
        "dynamic_module_boundary": 0,
    }
    assert all(row["contract_established"] is False for row in contracts.values())
    assert all(row["wall_shape"] == "technique-shaped" for row in contracts.values())
    assert all(row["immunity_to_missing_reaching_definitions"] for row in contracts.values())
    assert all(
        row["protected_set_disjointness"]["proved_for_universal_membership_set"] is False
        for row in contracts.values())


def test_shared_cell_known_writer_is_not_promoted_to_census() -> None:
    row = _doc()["contracts"]["shared_dispatch_cell_0x8007fbc4"]
    writer = row["known_direct_writer_lower_bound"]
    assert writer["store_pc"] == "0x80060fe8"
    assert writer["store_word"] == "0xac22fbc4"
    assert writer["derived_address"] == "0x8007fbc4"
    assert writer["derived_value"] == "0x80061668"
    assert writer["direct_writer_count_is_census"] is False
    assert row["writer_set"]["unresolved_write_count"] == 4266
    assert row["writer_set"]["full_width_unresolved_write_count"] == 2244
    assert row["writer_set"]["writer_universe_closed"] is False
    assert row["table_membership_invariant"]["proved"] is False


def test_object_and_bios_candidates_remain_nonglobal() -> None:
    contracts = _doc()["contracts"]
    obj = contracts["object_field_provenance"]
    assert obj["byte_fact"]["source_pc"] == "0x8004d1e0"
    assert obj["byte_fact"]["source_word"] == "0x8e02007c"
    assert obj["retained_field_observation"]["instances_seen"] == 1286
    assert obj["retained_field_observation"]["distinct_handlers"] == 9
    assert obj["runtime_observed_targets"]["count"] == 10
    assert obj["shared_abi_cost"]["consumed_argument_domains_known"]["fraction"] == "1/867"
    assert obj["table_membership_invariant"]["proved"] is False

    bios = contracts["bios_ingress_exception"]
    assert bios["byte_fact"]["source_pc"] == "0x80060c74"
    assert bios["byte_fact"]["source_word"] == "0x240a00b0"
    assert bios["entry_scoped_candidate"]["targets"] == ["0x000000b0"]
    assert bios["entry_scoped_candidate"]["primary_and_independent_c_agree"] is True
    assert bios["entry_scoped_candidate"]["accepted_as_global_contract"] is False
    assert bios["table_membership_or_named_exception_invariant"]["proved"] is False


def test_dynamic_boundary_requires_residency_identity() -> None:
    row = _doc()["contracts"]["dynamic_module_boundary"]
    probe = row["independent_byte_probe"]
    assert probe["guard_word"] == "0x2c820008"
    assert probe["load_word"] == "0x8c2257b4"
    assert probe["site_word"] == "0x00400008"
    assert probe["table_start"] == "0x800b57b4"
    assert probe["table_end"] == "0x800b57d4"
    assert len(probe["slots"]) == 8
    runtime = row["runtime"]
    assert {"0x800cabe0", "0x800cabe4"} <= set(runtime["outside_static_code_census"])
    assert runtime["memory_getResidency_retained_per_hit"] is False
    assert runtime["transferLog_retained_per_hit"] is False
    assert row["residency_alias_warning"]["same_virtual_address_has_pinned_fmv_data_role"] is True
    assert row["loader_membership_invariant"]["proved"] is False


def test_per_site_results_tile_sample_and_no_vacuous_pass_exists() -> None:
    doc = _doc()
    sample = doc["universes"]["pilot"]["site_ids"]
    outcomes = doc["per_site_outcomes"]
    assert [row["site"] for row in outcomes] == sample
    assert len(outcomes) == 12
    assert all(row["part_1_membership_invariant_proved"] is False for row in outcomes)
    assert all(
        row["part_2_protected_disjointness_proved_for_membership_set"] is False
        for row in outcomes)
    assert all(row["gate_grade_proved"] is False for row in outcomes)
    assert all(row["hoisted_load_idiom_match"] is False for row in outcomes)
    assert sum(bool(row["observed_targets"]) for row in outcomes) == 2


def test_no_go_residual_and_f01_state_do_not_move() -> None:
    doc = _doc()
    decision = doc["decision"]
    assert decision["verdict"] == "NO-GO"
    assert decision["fractions"]["contracts_fully_established"] == "0/4"
    assert decision["fractions"]["frozen_sites_gate_grade_proved"] == "0/12"
    assert decision["residual"]["before"] == 179
    assert decision["residual"]["after"] == 179
    assert decision["residual"]["movement"] == 0
    assert decision["status_movement_authorized"] is False
    assert decision["sixth_attempt_funding"][
        "complete_frontier_retains_a_technical_avenue"] is True
    assert doc["protected_state"] == {
        "f01_status": "partial",
        "item_2": "not_met",
        "mechanics_baseline_touched": False,
        "forbidden_runtime_artifact_touched": False,
        "instrumented_replay_performed": False,
        "analysis_chain_regenerated": False,
    }


def test_experiment_orders_freeze_outcomes_then_decision() -> None:
    text = EXPERIMENT.read_text()
    freeze = text.index("D3 contract pilot FREEZE (pre-outcome)")
    outcome = text.index("D3 contract pilot outcome: reviewed negative")
    per_site = text.index("### Per-site outcomes (recorded before the decision)", outcome)
    per_contract = text.index("### Per-contract findings and wall labels", per_site)
    decision = text.index("### Mandatory decision (after the per-site and per-contract record)", per_contract)
    explicit = text.index("PILOT DECISION: NO-GO", decision)
    assert freeze < outcome < per_site < per_contract < decision < explicit
    assert "0/4 contracts" in text[explicit:]
    assert "0/12 frozen sites" in text[explicit:]
