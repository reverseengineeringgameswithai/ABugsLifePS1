"""Contract tests for the compiled-C F01 ABI ledger."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis/phase4_f01_abi_ledger.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_bytes())


def row(doc: dict, image: str, entry: int) -> dict:
    return next(
        item for item in doc["rows"]
        if item["image"] == image and int(item["entry"], 0) == entry
    )


def test_regenerator_is_byte_identical() -> None:
    subprocess.run(
        [sys.executable, "tools/phase4_f01_abi_ledger.py", "--check"],
        cwd=ROOT, check=True,
    )


def test_scope_is_exact_in_both_directions() -> None:
    doc = load()
    assert doc["scope"]["count"] == 764
    assert len(doc["scope"]["in_scope"]) == 764
    frontier, typed, local = doc["scope"]["sources"]
    assert [frontier["count"], typed["count"], local["count"]] == [764, 645, 20]
    assert [
        len(frontier["in_scope_absent_from_source"]),
        len(typed["in_scope_absent_from_source"]),
        len(local["in_scope_absent_from_source"]),
    ] == [0, 119, 744]
    assert all(not source["source_outside_union"] for source in doc["scope"]["sources"])
    assert len(doc["scope"]["identifier_name_disagreements"]) == 9
    assert doc["scope"]["source_relationships"] == {
        "frontier_absent_from_local_base_count": 744,
        "frontier_absent_from_typed_state_count": 119,
        "frontier_roots_equal_reached_functions": True,
        "local_base_only": [],
        "local_base_owners_are_subset_of_frontier": True,
        "typed_state_is_subset_of_frontier": True,
        "typed_state_only": [],
    }


def test_every_static_index_identity_and_requested_field_is_present() -> None:
    doc = load()
    index = json.loads((ROOT / "analysis/phase4_static_frontier_index.json").read_bytes())
    indexed = {
        (item["image_id"], int(item["entry"], 0)): item
        for item in index["records"] if item.get("entry")
    }
    assert len(doc["rows"]) == 764
    for item in doc["rows"]:
        source = indexed[(item["image"], int(item["entry"], 0))]
        assert item["name"] == source["name"]
        assert int(item["end_exclusive"], 0) == int(source["end"], 0)
        assert item["abi_row_complete"] is True
        assert isinstance(item["arguments"], list)
        assert isinstance(item["stack_arguments"], list)
        assert item["return_convention"]["classification"]
        assert len(item["callee_saved"]) == 10
        assert item["frame"]["kind"] in {
            "none", "fixed", "variable_or_unknown", "inherited_or_unbalanced",
        }
        assert item["stack_argument_analysis"]["classification"] in {
            "call_entry_sp_anchored", "inherited_or_unbalanced_entry_sp",
            "variable_or_unknown_sp", "unknown_entry_sp_provenance",
        }
        assert item["memory_side_effects"]["scope"].startswith(
            "direct entry-reachable stores"
        )
        assert item["memory_side_effects"]["all_decoded_store_sites_accounted_for"] is True


def test_arguments_are_instruction_proved_and_unknowns_are_explicit() -> None:
    doc = load()
    total = 0
    for item in doc["rows"]:
        for argument in item["arguments"]:
            total += 1
            assert argument["register"] in {"a0", "a1", "a2", "a3"}
            assert argument["proof_pc"].startswith("0x")
            assert argument["proof_word"].startswith("0x")
            assert argument["proof_role"] in {
                "memory_base", "store_value", "indirect_target", "branch_predicate",
                "unaligned_load_merge_value", "arithmetic",
            }
            assert argument["type_domain"]["kind"] in {"pointer", "unknown"}
            assert argument["type_domain"]["domain"]
    assert total == 867
    assert doc["coverage"]["consumed_argument_domains_known"]["fraction"] == "1/867"
    player = row(doc, "SCUS_942_88", 0x80048138)
    assert player["arguments"] == [{
        "pointer_use_pc": None,
        "proof_pc": "0x80048140",
        "proof_role": "arithmetic",
        "proof_word": "0x00808821",
        "register": "a0",
        "type_domain": {
            "agreed_value": "0x800a6500",
            "binding_register": "s1",
            "domain": "player_actor",
            "kind": "pointer",
            "proof_source": "accepted retained typed-state binding",
        },
    }]


def test_ra_is_not_assumed_to_be_a_return_register() -> None:
    doc = load()
    player = row(doc, "SCUS_942_88", 0x80048138)
    assert player["entry_ra_call_link_proved"] is False
    assert player["normal_return_sites"] == []
    assert player["incoming_ra_continuation_sites"] == ["0x800498a4"]
    assert player["return_convention"]["classification"] == "unknown_entry_ra_provenance"
    assert player["return_convention"]["normal_return_count"] == 0
    assert player["return_convention"]["incoming_ra_continuation_count"] == 1
    assert not player["non_entry_ra_jr_ra_sites"]
    gte = row(doc, "SCUS_942_88", 0x800153D0)
    assert {item["pc"] for item in gte["non_entry_ra_jr_ra_sites"]} >= {"0x800163d8"}
    assert "0x800163d8" not in gte["normal_return_sites"]

    caution = doc["ra_general_jump_caution_crosscheck"]
    exact_sites = {
        0x80018F44, 0x8001923C, 0x80019614, 0x80019B3C,
        0x80019F34, 0x8001A0DC, 0x8001A1D4,
    }
    assert caution["unique_sites_expected"] == caution["unique_sites_checked"] == 7
    assert caution["site_target_pairs_checked"] == 18
    assert caution["all_sites_decode_as_jr_ra"] is True
    assert caution["all_observed_targets_lack_call_at_target_minus_8"] is True
    assert caution["all_sites_outside_ledger_scope"] is True
    assert {int(item["site_pc"], 0) for item in caution["pairs"]} == exact_sites
    assert all(item["site_word"] == "0x03e00008" for item in caution["pairs"])
    assert all(item["target_minus_8_is_call"] is False for item in caution["pairs"])


def test_frame_stack_and_clobber_witnesses() -> None:
    doc = load()
    player = row(doc, "SCUS_942_88", 0x80048138)
    assert player["frame"] == {
        "balanced_on_all_incoming_ra_continuations": True,
        "balanced_on_all_normal_returns": None,
        "entry_sp_basis_known": True,
        "kind": "fixed",
        "maximum_sp_delta": 0,
        "minimum_sp_delta": -256,
        "positive_sp_adjustment_without_extent_push": False,
        "size_bytes": 256,
        "sp_state_has_unknown": False,
    }
    callee = {item["register"]: item for item in player["callee_saved"]}
    assert callee["ra"]["status"] == "balanced_save_restore_on_incoming_ra_continuations"
    assert callee["ra"]["matching_restore_instructions"] >= 1
    assert callee["s1"]["status"] == "balanced_save_restore_on_incoming_ra_continuations"
    assert doc["coverage"]["stack_argument_domains_known"]["denominator"] == 94
    assert doc["coverage"]["stack_argument_domains_known"]["numerator"] == 0


def test_inherited_frames_are_not_stack_arguments() -> None:
    doc = load()
    suffix = row(doc, "LEVEL08_LEVEL1", 0x800B3AEC)
    assert suffix["frame"] == {
        "balanced_on_all_incoming_ra_continuations": False,
        "balanced_on_all_normal_returns": None,
        "entry_sp_basis_known": False,
        "kind": "inherited_or_unbalanced",
        "maximum_sp_delta": 40,
        "minimum_sp_delta": 0,
        "positive_sp_adjustment_without_extent_push": True,
        "size_bytes": None,
        "sp_state_has_unknown": False,
    }
    assert suffix["stack_argument_analysis"] == {
        "classification": "inherited_or_unbalanced_entry_sp",
        "entry_call_link_proved": False,
        "entry_call_witness_pc": None,
        "entry_call_witness_word": None,
        "largest_positive_sp_adjustment_bytes": 40,
        "maximum_positive_sp_delta": 40,
        "positive_sp_adjustment_without_extent_push": True,
    }
    assert suffix["stack_arguments"] == []
    assert [
        (item["proof_pc"], item["entry_relative_offset"], item["proof_word"])
        for item in suffix["unclassified_entry_relative_stack_loads"]
    ] == [
        ("0x800b3b4c", 36, "0x8fbf0024"),
        ("0x800b3b50", 32, "0x8fb40020"),
        ("0x800b3b54", 28, "0x8fb3001c"),
        ("0x800b3b58", 24, "0x8fb20018"),
        ("0x800b3b5c", 20, "0x8fb10014"),
        ("0x800b3b60", 16, "0x8fb00010"),
    ]
    assert doc["coverage"]["unknown_reasons"]["inherited_or_unbalanced_entry_frame_rows"] == 17
    assert doc["coverage"]["unknown_reasons"]["unclassified_entry_relative_stack_loads"] == 161
    assert doc["coverage"]["unknown_reasons"]["unclassified_stack_loads_without_entry_call_proof"] == 17
    assert all(
        item["stack_argument_analysis"]["classification"] == "call_entry_sp_anchored"
        for item in doc["rows"] if item["stack_arguments"]
    )
    anchored = row(doc, "LEVEL04_LEVEL", 0x800B3CD8)
    assert anchored["stack_argument_analysis"]["entry_call_link_proved"] is True
    assert anchored["stack_argument_analysis"]["entry_call_witness_pc"] == "0x800b4138"
    assert anchored["stack_argument_analysis"]["entry_call_witness_word"] == "0x0c02cf36"
    assert anchored["stack_arguments"][0]["entry_sp_offset"] == 16
    unanchored = row(doc, "SCUS_942_88", 0x80026858)
    assert unanchored["stack_argument_analysis"]["classification"] == "unknown_entry_sp_provenance"
    assert unanchored["frame"]["entry_sp_basis_known"] is False


def test_t9_and_canonical_callee_save_regressions() -> None:
    doc = load()
    t9_witness = row(doc, "SCUS_942_88", 0x80014844)
    t9 = next(
        item for item in t9_witness["caller_saved_written"]
        if item["register"] == "t9"
    )
    assert t9 == {
        "direct_instruction_write": True,
        "first_direct_write_pc": "0x80014848",
        "first_direct_write_word": "0x20190040",
        "may_be_clobbered_by_nested_call": False,
        "register": "t9",
    }

    level04 = row(doc, "LEVEL04_LEVEL", 0x800B3F3C)
    s0 = next(item for item in level04["callee_saved"] if item["register"] == "s0")
    assert s0 == {
        "ambiguous_save_slots": False,
        "entry_sp_slot": -16,
        "matching_restore_instructions": 1,
        "register": "s0",
        "save_pc": "0x800b3f5c",
        "status": "balanced_save_restore_on_incoming_ra_continuations",
    }
    assert level04["incoming_ra_continuation_sites"] == ["0x800b440c"]
    assert level04["callee_saved_effects_classified"] is True
    assert level04["fully_resolved"] is False


def test_all_hoisted_loads_are_redecoded_by_c() -> None:
    doc = load()
    check = doc["hoisted_load_crosscheck"]
    assert check["expected"] == check["checked"] == 22
    assert check["all_recognized"] is True
    assert all(item["decoded_as_load"] for item in check["rows"])
    assert all(item["contiguous_idiom_recognized"] for item in check["rows"])
    assert {int(item["load_pc"], 0) for item in check["rows"]} == {
        int(item["load_pc"], 0)
        for item in json.loads((ROOT / "analysis/hoisted_load_idiom_scan.json").read_bytes())["hits"]
    }


def test_region_provenance_is_reused_not_recomputed() -> None:
    doc = load()
    reuse = doc["inputs"]["region_provenance_reuse"]
    assert reuse["tool"] == "tools/region_provenance.c"
    assert reuse["rerun_by_this_ledger"] is False
    assert reuse["windows_queried"] == ["0x800823a0/2", "0x80082470/2"]
    assert sum(reuse["site_verdicts"].values()) > 0
    assert all(
        item["memory_side_effects"]["all_decoded_store_sites_accounted_for"]
        for item in doc["rows"]
    )


def test_abi_survey_every_row_agrees_or_is_listed() -> None:
    doc = load()
    check = doc["abi_survey_crosscheck"]
    assert check["rows_checked"] == 50
    assert len(check["every_row"]) == 50
    assert check["agreements"] + check["disagreements"] == 50
    assert len(check["every_disagreement"]) == check["disagreements"]
    assert check["agreements"] == 50
    assert check["disagreements"] == 0


def test_coverage_is_fraction_first_and_does_not_promote() -> None:
    doc = load()
    assert doc["schema"] == "abl-phase4-f01-abi-ledger/2"
    assert doc["coverage"]["complete_abi_rows"]["fraction"] == "764/764"
    assert doc["coverage"]["mechanically_closed_rows"]["fraction"] == "0/764"
    assert doc["coverage"]["fully_resolved_rows"]["fraction"] == "0/764"
    assert doc["coverage"]["return_convention_known_rows"]["fraction"] == "0/764"
    assert doc["coverage"]["callee_saved_effects_classified_rows"]["fraction"] == "617/764"
    assert doc["coverage"]["unknown_reasons"]["unproved_entry_ra_provenance_rows"] == 621
    assert doc["coverage"]["unknown_reasons"]["no_proved_normal_return_but_exit_provenance_open_rows"] == 143
    assert doc["coverage"]["unknown_reasons"]["ambiguous_callee_save_rows"] == 0
    assert doc["coverage"]["unknown_reasons"]["callee_saved_effects_unclassified_rows"] == 147
    assert doc["coverage"]["unknown_reasons"]["callee_saved_effects_rejected_for_incomplete_cfg_rows"] == 4
    assert all(
        not item["fully_resolved"]
        for item in doc["rows"]
        if item["return_convention"]["classification"]
        in {
            "unknown_return_discipline", "unknown_entry_ra_provenance",
            "unknown_no_proved_normal_return",
        }
    )
    assert all(
        not item["fully_resolved"]
        for item in doc["rows"]
        if not item["callee_saved_effects_classified"]
    )
    for entry in (0x80014B04, 0x80014EE0, 0x800172DC, 0x80060154):
        incomplete = row(doc, "SCUS_942_88", entry)
        assert incomplete["mechanically_complete"] is False
        assert incomplete["callee_saved_effects_classified"] is False
        assert incomplete["callee_saved_effects_unclassified_reason"] == "compiled_cfg_incomplete"
    assert all(
        not item["fully_resolved"]
        for item in doc["rows"]
        if any(save["ambiguous_save_slots"] for save in item["callee_saved"])
    )
    assert doc["status"] == "partial"
    assert doc["original_interfaces_eligible_for_promotion"] is False
    assert doc["authority"]["promotes_dimension"] is False
    assert doc["authority"]["runtime_replay_used"] is False
