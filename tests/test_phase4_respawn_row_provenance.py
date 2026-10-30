"""Falsification guards for the C15 authored respawn-row provenance join."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_respawn_row_provenance as rows  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_respawn_row_provenance.json"
ARTIFACT_SHA256 = "7de632b7c4cc4bcb88fc5f1d3a4a6d6341ef9915cc8df55e2a7c22903bd3cafd"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_row_provenance_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert rows.evidence_gaps(doc) == []
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_respawn_row_provenance.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["duckstation"]["revision"] == \
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5"
    assert doc["run_provenance"]["duckstation"]["binary_sha256"] == \
        "91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6"
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True


def test_static_dat_census_recomputes_from_all_pinned_inputs():
    doc = load_artifact()
    assert rows.build_static_census() == doc["static_census"]
    census = doc["static_census"]
    assert census["scan_scope"] == {
        "glob": "REBUILD/files/LEVEL*/*.DAT",
        "staged_input_count": 21,
        "type_01_record_count": 14,
        "all_inputs_hash_verified": True,
    }
    assert census["unique_runtime_window_matches"] == [{
        "path": "REBUILD/files/LEVEL03/LEVEL.DAT",
        "index": 1,
        "type": 1,
        "count": 18,
        "offset": "0x458",
        "size": 220,
        "record_sha256": rows.EXPECTED_TYPE_01_RECORD_SHA256,
        "plus_next_header_size": 224,
        "plus_next_header_sha256": rows.EXPECTED_TYPE_01_PLUS_HEADER_SHA256,
    }]
    assert census["parser"]["instructions"][
        "nonnegative_type_pointer_store"] == {
            "address": "0x8001CEDC", "instruction_word": "0xAC520000"}


def test_runtime_source_and_prior_causal_join_are_exact():
    doc = load_artifact()
    runtime = doc["live"]["runtime_dat"]
    assert runtime["base"] == "0x8015E22C"
    assert runtime["type_01_pointer"] == "0x8015E684"
    assert runtime["type_01_file_offset"] == "0x458"
    assert runtime["record_sha256"] == rows.EXPECTED_TYPE_01_RECORD_SHA256
    assert runtime["staged_byte_identical"] is True
    assert doc["live"]["selected_row"] == {
        "index": 6,
        "runtime_address": "0x8015E6D0",
        "file_offset": "0x4A4",
        "raw_xyz": [15678, 0, 15438],
        "scaled_xz": [501696, 494016],
        "row_sha256": rows.EXPECTED_SELECTED_ROW_SHA256,
        "staged_byte_identical": True,
    }
    current = rows._existing_causal_join()
    assert doc["existing_causal_join"] == current
    assert current["artifact_sha256"] == \
        "fc71182a5ffeb1acc15a305d4c707ac2f2846ebc173497d48a4bbc3fd1fc0660"
    assert current["selector_denial"] == {
        "single_changed_byte": "0x800A6590",
        "status_before": "0x0014", "status_after": "0x0004",
        "cleared_mask": "0x0010", "selector_total_hits": 17,
        "post_safe_xyz": [507900, 31787, 503976],
        "post_live_xyz": [507900, 31787, 503976],
    }


def test_native_progression_and_current_binary_movie_repair_are_exact():
    doc = load_artifact()
    live = doc["live"]
    progression = live["progression"]
    receipt = progression["receipt"]
    assert receipt["schema"] == "abl-phase4-respawn-progression/1"
    assert receipt["state"]["sha256"] == rows.EXPECTED_PROGRESSION_STATE_SHA256
    assert receipt["blank_card"]["exists"] is False
    assert receipt["generated_card"]["sha256"] == rows.PROGRESSION_CARD_SHA256
    assert receipt["generated_card"]["progression_marker_count"] == 1
    assert receipt["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert receipt["run_provenance"]["debugger"]["recreated"] is True
    assert live["card_before"] == live["card_after"]
    assert live["card_after"]["sha256"] == rows.PROGRESSION_CARD_SHA256

    assert live["control"]["after"]["scene"] == 1
    assert live["pre_edit_boundary_equal_to_control"] is True
    assert live["after"]["scene"] == 3
    assert live["trace_window"] == [6300, 7600]
    assert live["in_memory_edit"] == {
        **live["in_memory_edit"],
        "button_removed": "left",
        "start_frame": 6307,
        "end_frame_exclusive": 6316,
        "edited_frame_count": 9,
        "edited_movie_semantic_sha256":
            rows.EXPECTED_EDITED_MOVIE_SEMANTIC_SHA256,
        "derivative_saved": False,
    }


def test_two_process_reproduction_is_declarative_and_retained():
    doc = load_artifact()
    scenario = rows._declarative_scenario()
    assert scenario == {
        "path": (
            "tools/scenarios/duckstation/"
            "pristine_c15_authored_row_provenance.yaml"),
        "sha256": "81dc60f669be9dfac82f34d9816401398e58d720de0a308a62d064db26a1da9f",
        "schema": "abl-duckstation-two-process-scenario/1",
        "id": "pristine_c15_authored_row_provenance",
        "assertion_count": 11,
    }
    assert doc["declarative_scenario"] == scenario


def test_provenance_mutations_turn_the_evidence_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["live"]["runtime_dat"]["type_01_pointer"] = "0x8015E688"
    assert "runtime type-0x01 record" in " ".join(rows.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["static_census"]["unique_runtime_window_matches"].append(
        copy.deepcopy(mutated["static_census"]["unique_runtime_window_matches"][0]))
    assert "not unique LEVEL03" in " ".join(rows.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["selected_row"]["raw_xyz"][0] += 1
    assert "selected row-6" in " ".join(rows.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["existing_causal_join"]["mutated_live_xyz"][0] += 1
    assert "causal join" in " ".join(rows.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["progression"]["receipt"]["generated_card"]["sha256"] = "0" * 64
    assert "progression receipt" in " ".join(rows.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["in_memory_edit"]["start_frame"] -= 1
    assert "in-memory movie repair" in " ".join(rows.evidence_gaps(mutated))


def test_movie_is_centrally_declared_and_c15_stays_active():
    fixtures = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())[
            "entries"]
    matching = [(path, pin) for path, pin in fixtures.items()
                if pin.get("sha256") == rows.EXPECTED_MOVIE_SHA256]
    assert len(matching) == 1
    _path, pin = matching[0]
    assert pin["media_class"] == "pristine_serial"
    assert pin["preservation_required"] is True
    assert pin["copyrighted_or_operator_owned"] is True

    state = fixtures["level01_end_of_stage.sav"]
    assert state["sha256"] == rows.EXPECTED_PROGRESSION_STATE_SHA256
    assert state["media_class"] == "pristine"
    assert state["preservation_required"] is True
    assert state["copyrighted_or_operator_owned"] is True

    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "safe_respawn_anchor")
    assert campaign["status"] == "active"
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C15_checkpoints"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91


def test_c15_schema_corrects_shared_dat_slot_without_overclaiming():
    schema = yaml.safe_load(
        (ROOT / "config/phase4_checkpoint_respawn.yaml").read_text())
    field = schema["typed_state"]["dat_type_01_pointer"]
    assert field["address"] == 0x80096DA4
    assert "shared DAT type-pointer table slot" in field["boundary"]
    assert schema["ownership_boundaries"]["still_open"] == [
        "Source and general activation policy of status mask 0x0010, denial behavior in other row-selecting variants, plus reset scope.",
        "Indirect/additional overlay variants, actor, scripted and exceptional death classes plus remaining-stage, save/load and scene-transition breadth.",
    ]
