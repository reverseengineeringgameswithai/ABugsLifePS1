"""Contracts for the gated F01 player_vertical_update C-source receipt."""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_f01_source_closure.json"
SOURCE = ROOT / "src_re" / "player_vertical_update_80048138.c"
DRIVER = ROOT / "tools" / "phase4_f01_source_closure.py"


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(ARTIFACT.read_text())


def classify(size_bytes: int, differing_words: int) -> str:
    if size_bytes == 6004 and differing_words == 0:
        return "MATCH"
    if size_bytes == 6004 and differing_words <= 16:
        return "NEAR_MISS"
    return "NO_GO"


def validate_region_gate(regions: list[dict]) -> None:
    first_open = next(
        (index for index, row in enumerate(regions) if row["differing_words"] != 0),
        len(regions),
    )
    for index, row in enumerate(regions):
        if row["status"] == "closed":
            assert row["differing_words"] == 0
            assert index < first_open
            assert row["closed"] is True
            assert row["words_remaining"] == 0
        elif row["status"] == "active_open":
            assert index == first_open
            assert row["differing_words"] > 0
            assert row["gate_scored"] is True
            assert row["closed"] is False
            assert row["words_remaining"] == row["differing_words"]
        elif row["status"] == "not_attempted_gate_blocked":
            assert index > first_open
            assert row["gate_scored"] is False
            assert row["closed"] is False
            assert row["words_remaining"] is None
        else:
            raise AssertionError(f"unknown gate status {row['status']}")


@pytest.mark.local_media
def test_recompile_and_receipt_are_byte_current() -> None:
    proc = subprocess.run(
        ["python3", str(DRIVER), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (
        "NO_GO 0 of 6 regions closed; 70 words remaining in region 1; "
        "size delta -56 bytes"
    ) in proc.stdout


@pytest.mark.local_media
def test_absolute_output_regeneration_is_byte_identical(tmp_path: Path) -> None:
    regenerated = tmp_path / "phase4_f01_source_closure.json"
    proc = subprocess.run(
        ["python3", str(DRIVER), "--write", "--output", str(regenerated)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert regenerated.read_bytes() == ARTIFACT.read_bytes()


def test_target_freeze_and_compiler_contract_are_exact(receipt: dict) -> None:
    assert receipt["schema"] == "abl-phase4-f01-source-closure/2"
    assert receipt["execution_freeze"] == {
        "issued_baseline_commit": "7ea89416dfaff1d4e9d8498ee806d24b23e41e6f",
        "freeze_commit": "10339263c1e89a37817c55ba84e393883fc46c5e",
        "issued_baseline_status_short_line_count": 116,
        "issued_baseline_status_short_sha256": (
            "dbb9bee516c80b08983dd3cb4cafdfb799a939818771c90a899407c0d31b1616"
        ),
        "pre_outcome_contents": receipt["execution_freeze"]["pre_outcome_contents"],
        "status_note": receipt["execution_freeze"]["status_note"],
    }
    assert receipt["target"] == {
        "name": "player_vertical_update",
        "start": "0x80048138",
        "end_exclusive": "0x800498AC",
        "size_bytes": 6004,
        "word_count": 1501,
        "retail_slice_sha256": (
            "cab9a859cd6284a25c2ec4d0ba5072a0261b826a0497004e1a528dc0ebc74024"
        ),
    }
    assert receipt["inputs"]["image_sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
    )
    contract = receipt["compiler_contract"]
    assert contract["compiler_id"] == "gcc2.7.2-psx"
    assert contract["cc1_sha256_observed"] == contract["cc1_sha256_pin"]
    assert contract["cpp_sha256_observed"] == contract["cpp_sha256_pin"]
    assert contract["maspsx_entry_sha256_observed"] == (
        "d170463b0c519a825db97d3f30ffbe0228e4cf642de2dc64fb30f90f118c2b0c"
    )
    assert contract["cc1_flags"] == [
        "-O2", "-G0", "-mcpu=3000", "-fno-builtin",
    ]
    assert contract["maspsx_args"] == ["--dont-expand-li", "--expand-div"]
    assert contract["small_data"] is False


def test_source_pin_and_c_origin_are_explicit(receipt: dict) -> None:
    assert receipt["inputs"]["source"] == "src_re/player_vertical_update_80048138.c"
    assert receipt["inputs"]["source_sha256"] == hashlib.sha256(
        SOURCE.read_bytes()
    ).hexdigest()
    source = SOURCE.read_text()
    assert "void player_vertical_update(PlayerA05 *player)" in source
    assert 'register u8 *abl_gp asm ("$28")' in source
    assert "__asm__" not in source
    assert "asm/hand_written" not in source
    assert receipt["hand_asm_regions"] == []
    assert receipt["source_closure_eligible_for_promotion"] is False
    for offset in ("86", "96", "97"):
        assert f"field_{offset}" in source
    for unsupported_name in ("action_guard_86", "contact_class_96", "status_mode_97"):
        assert unsupported_name not in source


def test_match_near_miss_and_no_go_are_mutually_exact(receipt: dict) -> None:
    assert classify(6004, 0) == "MATCH"
    assert classify(6004, 1) == "NEAR_MISS"
    assert classify(6004, 16) == "NEAR_MISS"
    assert classify(6004, 17) == "NO_GO"
    assert classify(6000, 1) == "NO_GO"
    assert classify(6008, 1) == "NO_GO"
    assert receipt["result"] == "NO_GO"
    assert receipt["classification"]["exact_match"] is False
    assert receipt["classification"]["near_miss"] is False
    assert receipt["classification"]["no_go"] is True
    assert "exactly 6004 bytes" in receipt["classification"]["near_miss_definition"]
    assert "at most 16" in receipt["classification"]["near_miss_definition"]


def test_measurement_is_symmetric_and_current(receipt: dict) -> None:
    measured = receipt["measurement"]
    assert measured["compiled_size_bytes"] == 5948
    assert measured["size_delta_bytes"] == -56
    assert measured["compiled_word_count"] == 1487
    assert measured["compared_word_positions"] == 1501
    assert measured["equal_word_positions"] == 129
    assert measured["differing_word_positions"] == 1372
    assert measured["retail_extent_differing_word_positions"] == 1372
    assert measured["compiled_only_word_positions"] == 0
    assert measured["retail_only_word_positions"] == 14
    assert len(measured["differences"]) == 1372
    addresses = [int(row["address"], 16) for row in measured["differences"]]
    assert addresses == sorted(set(addresses))


def test_region_gate_tiles_target_and_fails_closed(receipt: dict) -> None:
    regions = receipt["regions"]
    assert [row["word_count"] for row in regions] == [158, 89, 387, 223, 426, 218]
    assert sum(row["word_count"] for row in regions) == 1501
    assert [row["start"] for row in regions] == [
        "0x80048138", "0x800483B0", "0x80048514",
        "0x80048B20", "0x80048E9C", "0x80049544",
    ]
    assert [row["status"] for row in regions] == [
        "active_open",
        "not_attempted_gate_blocked",
        "not_attempted_gate_blocked",
        "not_attempted_gate_blocked",
        "not_attempted_gate_blocked",
        "not_attempted_gate_blocked",
    ]
    validate_region_gate(regions)
    gate = receipt["region_gate"]
    assert gate["regions_closed"] == 0
    assert gate["words_remaining_in_active_region"] == 70
    assert gate["later_region_work_authorized"] is False
    assert gate["first_open_region"] == {
        "number": 1,
        "name": "controller_history_and_spin",
        "start": "0x80048138",
        "end_exclusive": "0x800483B0",
        "words_remaining": 70,
    }
    assert [row["closed"] for row in gate["regions"]] == [False] * 6
    assert [row["words_remaining"] for row in gate["regions"]] == [
        70, None, None, None, None, None,
    ]

    false_closed = deepcopy(regions)
    false_closed[0]["status"] = "closed"
    with pytest.raises(AssertionError):
        validate_region_gate(false_closed)

    premature_later = deepcopy(regions)
    premature_later[1]["status"] = "active_open"
    premature_later[1]["gate_scored"] = True
    with pytest.raises(AssertionError):
        validate_region_gate(premature_later)


def test_phase0_frame_and_gp_prerequisites_are_reproduced(receipt: dict) -> None:
    phase0 = receipt["phase0_findings"]
    frame = phase0["frame_and_register_map"]
    assert frame["status"] == "cleared"
    assert frame["retail_frame_size_bytes"] == 256
    assert frame["compiled_frame_size_bytes"] == 256
    assert frame["exact_prefix_word_count"] == 54
    assert frame["exact_prefix_end_exclusive"] == "0x80048210"
    assert all(row["equal"] for row in frame["witnesses"])
    second = next(row for row in frame["witnesses"] if row["pc"] == "0x8004813C")
    assert second["compiled_word"] == second["retail_word"] == "0xAFB100DC"

    gp = phase0["mixed_gp_relative_addressing"]
    assert gp["status"] == "cleared"
    assert gp["observed_access_count"] == gp["expected_access_count"] == 17
    assert gp["region_1_observed_access_count"] == 10
    assert all(row["matches"] for row in gp["summary"])
    assert [row["observed_access_count"] for row in gp["summary"]] == [4, 6, 2, 2, 3]
    assert {row["gp_offset"] for row in gp["accesses"]} == {
        "0x502", "0x618", "0x63C", "0x69C", "0x73C",
    }


def test_phase0_hypotheses_were_tested_in_order(receipt: dict) -> None:
    probes = receipt["phase0_findings"]["ordered_hypothesis_tests"]
    declaration = probes["definition_vs_extern_and_sdata"]
    assert [row["variant"] for row in declaration["variants"]] == [
        "extern_reference",
        "extern_with_sdata_attribute",
        "translation_unit_definition",
        "translation_unit_sdata_definition",
    ]
    assert len({row["cc1_probe_body_sha256"] for row in declaration["variants"]}) == 1
    assert all(row["cc1_symbolic_load"] for row in declaration["variants"])
    assert all(not row["cc1_explicit_gp_operand"] for row in declaration["variants"])
    assert all(not row["gprel16_emitted"] for row in declaration["variants"])
    assert all(row["g0_relocations"] == ["R_MIPS_HI16", "R_MIPS_LO16"]
               for row in declaration["variants"])

    profiles = probes["declaration_profile"]
    assert profiles["all_outputs_identical"] is True
    assert len({row["compiled_sha256"] for row in profiles["profiles"]}) == 1
    nonzero_g = probes["nonzero_g"]
    assert nonzero_g["outcome"] == "link_error"
    assert nonzero_g["gprel16_overflow"] is True
    assert nonzero_g["small_data_section_too_large"] is True
    assert nonzero_g["contract_changed"] is False


def test_attempt_history_and_no_go_wall_are_honest(receipt: dict) -> None:
    attempts = receipt["attempt_history"]
    assert attempts[0]["evidence_status"] == "unretained_executor_observation"
    assert attempts[0]["supports_current_result"] is False
    assert attempts[1]["evidence_status"] == "unretained_executor_observation"
    assert "compiled_size_bytes" not in attempts[1]
    assert attempts[2]["outcome"] == "NEAR_MISS"
    assert attempts[2]["compiled_size_bytes"] == 6012
    assert attempts[2]["differing_word_positions"] == 1447
    assert attempts[2]["supports_current_result"] is False
    assert attempts[3]["outcome"] == "NO_GO"
    assert attempts[3]["supports_current_result"] is True
    assert attempts[3]["regions_closed"] == 0
    assert attempts[3]["active_region_differing_words"] == 70
    assert attempts[3]["source_sha256"] == receipt["inputs"]["source_sha256"]
    assert attempts[3]["compiled_sha256"] == receipt["measurement"]["compiled_sha256"]

    assert receipt["compiler_walls"] == [{
        "class": "extent_and_cfg_shape",
        "binding_subproblem": "region_1_source_expression_order_and_register_lifetime",
        "wall_shape": "technique_shaped",
        "evidence": receipt["compiler_walls"][0]["evidence"],
    }]
    assert receipt["no_go"]["binding_wall"] == "extent_and_cfg_shape"
    assert receipt["no_go"]["binding_subproblem"] == (
        "region_1_source_expression_order_and_register_lifetime"
    )
    assert receipt["no_go"]["wall_shape"] == "technique_shaped"
    assert receipt["no_go"]["later_regions_attempted"] is False
    assert receipt["dc_permute"]["used"] is False
    assert "5948 rather than 6004" in receipt["dc_permute"]["reason"]
    assert receipt["status_statement"].startswith("F01 source_closure remains partial")
