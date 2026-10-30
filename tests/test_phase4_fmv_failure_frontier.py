"""Adversarial guards for E15's upstream event/failure frontier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_failure_frontier as frontier  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_failure_frontier.json"
# Updated only after recomputation from hash-verified pristine inputs.
ARTIFACT_SHA256 = \
    "923cdfc4fedc8c82caef5c6937c365654da424fadac5ac40122053c0f3e33d23"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_failure_frontier_recomputes_from_pristine_and_pinned_sources():
    retained = load_artifact()
    assert frontier.build() == retained
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert retained["inputs"]["resident_executable"]["identity_verified"] is True
    assert retained["inputs"]["fmv_bin"]["identity_verified"] is True
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_event_producer_partition_preserves_the_unresolved_native_boundary():
    retained = load_artifact()
    delivery = retained["native_event_delivery"]
    assert delivery["deliver_event"]["resident_direct_call_count"] == 4
    assert delivery["deliver_event"]["matching_registered_class_spec"] == 0
    assert delivery["deliver_event"][
        "all_resident_direct_callers_classified"] is True
    assert delivery["getintr"]["direct_deliver_event_calls"] == 0
    assert delivery["producer_boundary"] == {
        "candidate_domain": "BIOS_or_interrupt_service",
        "classification":
            "outside_resident_direct_deliver_event_call_surface",
        "exact_producer_instruction_claimed": False,
        "native_delivery_frequency_claimed": False,
    }
    callers = delivery["deliver_event"]["resident_direct_callers"]
    assert [
        (row["site"], row["event_class"], row["event_spec"])
        for row in callers
    ] == [
        ("0x8006BD20", "0xF0000009", "0x00000020"),
        ("0x8006D6C4", "0xF0000003", "0x00000020"),
        ("0x8006D6EC", "0xF0000003", "0x00000040"),
        ("0x8006D714", "0xF0000003", "0x00000040"),
    ]


def test_failure_paths_have_exact_owners_and_do_not_claim_runtime_outcomes():
    retained = load_artifact()
    paths = retained["failure_paths"]
    assert paths["file_open"]["helper"]["failure_returns"] == [
        "0x800B8D14", "0x800B8D2C"]
    assert paths["file_open"]["player"] == {
        "diagnostic_call": "0x800B6E54",
        "failure_rejoins_shared_initialization": True,
        "failure_target": "0x800B6E4C",
        "helper_call": "0x800B6DD8",
        "predicate": "0x800B6DE8",
        "shared_initialization_call": "0x800B6E68",
    }
    timeout = paths["decode_poll_timeout"]
    assert timeout["poll"]["budget"] == 0x00800000
    assert timeout["timeout_transition"]["ready_one_store"]["pc"] == \
        "0x800B6D04"
    assert paths["cd_submit_retry"]["getlocp"]["retry_branch"] == "0x800B7044"
    assert paths["cd_submit_retry"]["read2"]["retry_branch"] == "0x800B7054"
    assert all(
        row["native_runtime_outcome_claimed"] is False
        for row in (paths["file_open"], paths["decode_poll_timeout"]))
    assert paths["cd_submit_retry"]["native_retry_counts_claimed"] is False
    assert retained["summary"] == {
        "classified_failure_path_families": 3,
        "classified_resident_direct_event_callers": 4,
        "exact_failure_windows": 4,
        "resident_direct_event_matches": 0,
        "runtime_outcomes_claimed": 0,
        "selected_controls": 1,
        "unclassified_static_failure_edges": 0,
        "decode_timeout_packet_hypotheses_falsified": 1,
        "decode_timeout_state_transitions": 1,
    }


def test_decode_timeout_preserves_falsified_packet_and_corrected_coordinates():
    retained = load_artifact()
    timeout = retained["failure_paths"]["decode_poll_timeout"]
    assert timeout["function"]["return_sites"] == ["0x800B6D60"]
    assert timeout["caller_count"] == 1
    assert timeout["direct_callers"][0]["site"] == "0x800B72A0"
    assert timeout["record_pointer_chain"]["record_base"] == "0x800CABE0"
    assert timeout["fields"]["rect_bank"]["fields"] == {
        "x": "s16 +0x00",
        "y": "s16 +0x02",
        "width": "s16 +0x04",
        "height": "s16 +0x06",
    }
    assert timeout["fields"]["present_rect"]["fields"] == {
        "x": "s16 +0x00",
        "y": "s16 +0x02",
        "width": "s16 +0x04",
        "height": "s16 +0x06",
    }
    assert timeout["field_layout_authorities"]["agree_on_field_order"] == [
        "x", "y", "width", "height"]

    transition = timeout["timeout_transition"]
    assert {
        name: (
            row["load"]["pc"],
            row["source_record_offset"],
            row["store"]["pc"],
            row["destination_record_offset"],
            row["semantic_type"],
        )
        for name, row in transition["coordinate_copies"].items()
    } == {
        "x": ("0x800B6D18", "0x10", "0x800B6D2C", "0x24", "s16"),
        "y": ("0x800B6D30", "0x12", "0x800B6D38", "0x26", "s16"),
    }
    assert transition["extent_fields_untouched"][
        "width_or_height_store_present"] is False
    assert [
        row["record_offset"]
        for row in transition["extent_fields_untouched"][
            "record_halfword_stores"]
    ] == [0x24, 0x26]

    successor = retained["static_successor"]
    assert successor["closed_sub_boundary"] == \
        "decode_timeout_recovery_coordinate_state_ownership"
    assert successor["falsifier"]["packet_hypothesis"]["outcome"] == \
        "falsified"
    assert successor["falsifier"]["packet_hypothesis"]["evidence"] == {
        "authoritative_field_order": ["x", "y", "width", "height"],
        "presentation_store_offsets": ["0x24", "0x26"],
        "reason": "instructions copy x/y; width/height remain untouched",
        "selected_slot_load_offsets": ["0x10", "0x12"],
    }
    corrected = successor["falsifier"]["corrected_claim"]
    assert corrected["outcome"] == "survived"
    assert all(corrected["checks"].values())
    assert successor["dimension_promoted"] is False
    assert timeout["native_runtime_outcome_claimed"] is False


def test_selected_control_is_one_word_bounded_and_does_not_overclaim():
    control = load_artifact()["selected_control"]
    assert control["only_difference"] == {
        "address": "0x800B6DE8",
        "kind": "code_write",
        "original_word": "0x12020018",
        "replacement_word": "0x10000018",
        "same_failure_target": "0x800B6E4C",
    }
    assert control["passive_window"] == {
        "clock": "movie_frame", "start": 160, "stop": 260}
    assert control["precise_window"] == {
        "clock": "movie_frame", "start": 170, "stop": 240}
    assert control["offline_localization"]["overlay_resident_interval"] == {
        "clock": "movie_frame", "start": 69, "stop": 416}
    assert control["native_failed_handle_claimed"] is False
    assert control["missing_or_malformed_media_claimed"] is False
    assert control["user_visible_policy_claimed"] is False
    assert load_artifact()["dimension_boundary"] == {
        "claim": "partial",
        "closed_sub_boundary":
            "upstream_event_and_failure_path_static_partition",
        "dimension": "lifecycle",
        "dimension_promoted": False,
        "next_lane": "live",
        "next_missing_fact": "E15/file-open-failure-routing-outcome",
    }


def _mutate(data: bytes, pc: int, *, base: int, header: int) -> bytes:
    changed = bytearray(data)
    changed[header + pc - base] ^= 1
    return bytes(changed)


@pytest.mark.local_media
@pytest.mark.parametrize(
    "pc",
    [0x8006BD20, 0x8006D6C4, 0x8006D6EC, 0x8006D714],
)
def test_each_resident_deliver_event_caller_mutation_fails_closed(pc):
    exe = frontier.EXE_PATH.read_bytes()
    with pytest.raises(SystemExit, match=(
            "resident DeliverEvent surface opcode drifted|"
            "resident DeliverEvent call census drifted|"
            "FMV failure-frontier window drifted")):
        frontier.build(
            exe_data=_mutate(
                exe, pc, base=frontier.EXE_BASE, header=frontier.EXE_HEADER),
            verify_identity=False)


@pytest.mark.local_media
@pytest.mark.parametrize(
    "pc",
    [
        0x800B6DE8,
        0x800B6CBC,
        0x800B6D04,
        0x800B6D08,
        0x800B6D0C,
        0x800B6D18,
        0x800B6D2C,
        0x800B6D30,
        0x800B6D38,
        0x800B6D44,
        0x800B6D4C,
        0x800B6D60,
        0x800B709C,
        0x800B70D4,
        0x800B729C,
        0x800B72A0,
        0x800B7044,
        0x800B8D14,
    ],
)
def test_each_failure_family_mutation_fails_closed(pc):
    fmv = frontier.FMV_PATH.read_bytes()
    with pytest.raises(
            SystemExit,
            match="FMV failure-frontier window drifted|"
                  "FMV failure frontier opcode drifted"):
        frontier.build(
            fmv_data=_mutate(fmv, pc, base=frontier.FMV_BASE, header=0),
            verify_identity=False)


@pytest.mark.local_media
def test_authoritative_rect_layout_mutation_fails_closed(
        tmp_path, monkeypatch):
    changed = frontier.TYPED_FMV_CONFIG.read_text().replace(
        "fields: [s16_x, s16_y, s16_w, s16_h]",
        "fields: [s16_w, s16_y, s16_x, s16_h]",
        1)
    mutated = tmp_path / "phase4_fmv.yaml"
    mutated.write_text(changed)
    monkeypatch.setattr(frontier, "TYPED_FMV_CONFIG", mutated)
    with pytest.raises(
            SystemExit, match="authoritative FMV typed RECT layout drifted"):
        frontier.build()


@pytest.mark.local_media
def test_generated_static_owner_layout_mutation_fails_closed(
        tmp_path, monkeypatch):
    retained = json.loads(frontier.STATIC_OWNERS.read_text())
    retained["player_typed_state"]["structures"]["rect_bank"]["fields"][0] = \
        "s16 w"
    mutated = tmp_path / "phase4_fmv_static_owners.json"
    mutated.write_text(json.dumps(retained))
    monkeypatch.setattr(frontier, "STATIC_OWNERS", mutated)
    with pytest.raises(
            SystemExit,
            match="generated FMV static-owner RECT layout drifted"):
        frontier.build()
