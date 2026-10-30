"""Adversarial guards for the pristine E15 selector/caller reconstruction."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_fmv_static_owners as owners  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_static_owners.json"
ARTIFACT_SHA256 = "8b0ef0d5a0f4f02080a5df30c0611d8888144427f0985cf81ed76c692d1b70f2"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_static_owner_artifact_recomputes_from_hash_verified_pristine_inputs():
    retained = load_artifact()
    assert owners.build() == retained
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert retained["inputs"]["resident_executable"]["identity_verified"] is True
    assert retained["inputs"]["fmv_bin"]["identity_verified"] is True
    assert retained["inputs"]["memory_bin"]["identity_verified"] is True
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_dispatch_is_exhaustive_and_resolves_all_level_a_b_selectors():
    doc = load_artifact()
    dispatch = doc["overlay_dispatch"]
    assert dispatch["selector_domain"] == {
        "minimum": 0,
        "maximum": 46,
        "limit_instruction": {
            "pc": "0x800B62A4",
            "word": "0x2E02002F",
            "mnemonic": "sltiu v0,s0,47",
        },
        "out_of_range_target": "0x800B6574",
    }
    assert [row["selector"] for row in dispatch["selectors"]] == list(range(47))
    assert [row["selector"] for row in dispatch["selectors"]
            if row["action"] == "no_stream"] == list(range(3, 10))
    level_a_paths = [
        "LEV1A", "LEV2A", "LEV3A", "LEV5A", "LEV4A", "LEV6A",
        "LEV7A", "LEV8A", "LEV9A", "LEV10A", "LEV11A", "LEV12A",
        "LEV13A", "LEV14A", "LEV15A",
    ]
    assert [(row["music_id"], row["selector"], row["path"])
            for row in doc["selector_tables"]["level_a"]["entries"][1:]] == [
        (music_id, 8 + 2 * music_id,
         f"BUGSFMV{'1' if music_id < 10 else '2'}/{path}.STR")
        for music_id, path in enumerate(level_a_paths, 1)
    ]
    assert [(row["music_id"], row["selector"], row["path"])
            for row in doc["selector_tables"]["level_b"]["entries"][1:]] == [
        (level, 9 + 2 * level,
         f"BUGSFMV{'1' if level < 10 else '2'}/LEV{level}B.STR")
        for level in range(1, 16)
    ]


def test_all_direct_loader_calls_and_cursor_wrap_are_bounded_without_viewer_claim():
    doc = load_artifact()
    calls = doc["resident_direct_calls"]
    assert calls["exhaustive_direct_call_count"] == 9
    assert [row["call"]["pc"] for row in calls["calls"]] == [
        "0x8004FB5C", "0x8004FB68", "0x8004FB74", "0x8004FFD4",
        "0x800500D8", "0x80050284", "0x8005031C", "0x8005036C",
        "0x8005B788",
    ]
    main_shell = calls["caller_regions"]["main_shell_state_machine"]
    assert main_shell["start"] == "0x8004FA40"
    assert main_shell["end"] == "0x8004FC3C"
    assert main_shell["size"] == 508
    level_a_owner = calls["caller_regions"][
        "gameplay_state_reset_cursor_seed"]
    assert level_a_owner["start"] == "0x8005B714"
    assert level_a_owner["end"] == "0x8005BC64"
    assert level_a_owner["size"] == 1360
    cursor = doc["bonus_clip_cursor"]
    assert cursor["streaming_old_cursor_values"] == [0, 1, 2, 3, 4, 255]
    assert [(cursor["outcomes"][value]["selector"],
             cursor["outcomes"][value]["path"])
            for value in (0, 1, 2, 3, 4, 5, 255)] == [
        (42, "BUGSFMV2/ALT1.STR"),
        (43, "BUGSFMV2/ALT2.STR"),
        (44, "BUGSFMV2/ALT3.STR"),
        (45, "BUGSFMV2/INTRO.STR"),
        (46, "BUGSFMV2/LOSE.STR"),
        (47, None),
        (41, "BUGSFMV2/LEV15D.STR"),
    ]
    assert doc["summary"]["directly_unowned_stream_selectors"] == [2]
    assert any("movie viewer" in row
               for row in doc["claims"]["not_claimed"])


def test_selector_2_computed_call_exclusion_and_player_slice_are_exact():
    doc = load_artifact()
    reachability = doc["selector_reachability"]
    assert reachability["reviewed_unreachable_stream_selectors"] == [2]
    assert reachability["selector_2"] == {
        "path": "fmv/ad.str", "frame_count": 1410,
        "classification": "unreachable_pristine_manifest_row",
        "basis": reachability["selector_2"]["basis"],
    }
    assert reachability["direct_loader_address_taken"] is False
    assert set(reachability["address_materializations"].values()) == {0}
    computed = reachability["computed_target_exclusion"]
    assert len(computed["code_owner_images"]) == 23
    assert computed["standard_materializations"] == []
    assert len(computed["unresolved_jalr_def_use"]) == 4
    assert computed["result"] == \
        "no pristine code owner can supply 0x8003E7C0 to jalr"
    assert reachability["resident_indirect_call_census"]["jalr_sites"] == 139
    assert reachability["resident_indirect_call_census"][
        "installed_fmv_bin_load_targets"] == 0

    completion = doc["completion_ownership"]
    assert completion["summary"] == {
        "total_xrefs": 4, "writers": 3, "readers": 1,
        "set_writers": 2, "clear_writers": 1,
    }
    assert [row["instruction"]["pc"] for row in completion["xrefs"]] == [
        "0x800B6B24", "0x800B6B48", "0x800B6DD0", "0x800B743C"]
    player = doc["player_frontier"]
    assert player["function"]["size"] == 1988
    assert player["direct_call_count"] == 50
    assert player["unique_direct_targets"] == 30
    assert player["indirect_calls"] == []
    assert player["completion_exit"]["stop_target"] == "0x800B6E38"


def test_player_boundary_typed_state_has_exact_xrefs_aliases_and_domains():
    typed = load_artifact()["player_typed_state"]
    assert typed["summary"] == {
        "region_b_address_rows": 30,
        "absolute_xrefs": 99,
        "player_xrefs": 58,
        "pointer_aliases": 6,
        "enumerated_state_ranges": 3,
        "unclassified_xrefs": 0,
        "all_xrefs_verified": True,
    }
    fields = {row["name"]: row for row in typed["fields"]}
    assert fields["decoded_frame_index"]["storage_type"] == "s32"
    assert [row["instruction"]["pc"] for row in
            fields["previous_decoded_frame_index"]["xrefs"]] == [
                "0x800B6B14"]
    assert fields["decode_stop_latch"]["storage_type"] == "u8"
    assert [row["instruction"]["pc"]
            for row in fields["cached_frame_width"]["xrefs"]] == [
                "0x800B6B54", "0x800B6BB8", "0x800B6BD0"]
    assert [row["instruction"]["pc"]
            for row in fields["cached_frame_height"]["xrefs"]] == [
                "0x800B6B6C", "0x800B6BC0", "0x800B6BE0"]
    assert fields["active_block_index"]["valid_domain"].startswith(
        "boolean 0 or 1")
    assert fields["display_mode"]["storage_type"] == "s16"
    assert fields["selected_frame_limit"]["valid_domain"] == \
        "pristine manifest values 156..3162"
    assert [row["instruction"]["pc"]
            for row in fields["completion_request"]["xrefs"]] == [
        "0x800B6B24", "0x800B6B48", "0x800B6DD0", "0x800B743C"]
    assert typed["structures"]["double_buffer"] == {
        "base": "0x800CABE0", "size": 12,
        "layout": ["pointer32 block[2]", "u32 active_index"],
        "alias_helper": "0x800B6C24..0x800B6CA4",
        "exact_behavior": typed["structures"]["double_buffer"][
            "exact_behavior"],
    }
    assert typed["player_function"]["entry_abi"][0] == {
        "source": "a1", "storage": "s2 then 0x80131EEE",
        "type": "s16", "role": "selected frame limit"}


def test_exact_historical_receipt_exception_is_machine_enforced_and_not_extensible():
    accepted = load_artifact()["historical_oracle_acceptance"]
    assert accepted["classification"] == "closed_exact_historical_receipt_exception"
    assert accepted["sha256"] == owners.LEGACY_FMV_SHA256
    assert all(accepted["checks"].values())
    assert "Every new E15 live run" in accepted["non_extensible_rule"]


@pytest.mark.local_media
def test_opcode_and_table_mutations_turn_the_static_proof_red():
    exe = bytearray(owners.EXE_PATH.read_bytes())
    call_offset = owners.EXE_HEADER + 0x8004FB5C - owners.EXE_BASE
    struct.pack_into("<I", exe, call_offset, 0)
    with pytest.raises(SystemExit, match="JAL census drifted"):
        owners.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(owners.EXE_PATH.read_bytes())
    level_b_offset = owners.EXE_HEADER + owners.LEVEL_B_TABLE - owners.EXE_BASE + 1
    exe[level_b_offset] = 3
    with pytest.raises(SystemExit, match="non-stream selector"):
        owners.build(exe_data=bytes(exe), verify_identity=False)

    fmv = bytearray(owners.FMV_PATH.read_bytes())
    limit_offset = owners.SELECTOR_LIMIT_PC - owners.FMV_BASE
    struct.pack_into("<I", fmv, limit_offset, 0)
    with pytest.raises(SystemExit, match="upper-bound instruction drifted"):
        owners.build(fmv_data=bytes(fmv), verify_identity=False)

    fmv = bytearray(owners.FMV_PATH.read_bytes())
    completion_offset = 0x800B743C - owners.FMV_BASE
    struct.pack_into("<I", fmv, completion_offset, 0)
    with pytest.raises(SystemExit, match="xref census is incomplete"):
        owners.build(fmv_data=bytes(fmv), verify_identity=False)

    memory = bytearray(owners.MEMORY_PATH.read_bytes())
    struct.pack_into("<I", memory, 0, owners.RESIDENT_LOADER)
    with pytest.raises(SystemExit, match="address-taken"):
        owners.build(memory_data=bytes(memory), verify_identity=False)

    memory = bytearray(owners.MEMORY_PATH.read_bytes())
    struct.pack_into("<II", memory, 0, 0x3C088004, 0x2508E7C0)
    with pytest.raises(SystemExit, match="computed"):
        owners.build(memory_data=bytes(memory), verify_identity=False)

    fmv = bytearray(owners.FMV_PATH.read_bytes())
    omitted_offset = 0x800B6B14 - owners.FMV_BASE
    struct.pack_into("<I", fmv, omitted_offset, 0)
    with pytest.raises(SystemExit, match="typed-state xref drift"):
        owners.build(fmv_data=bytes(fmv), verify_identity=False)

    fmv = bytearray(owners.FMV_PATH.read_bytes())
    unclassified_offset = 0x800B6B14 - owners.FMV_BASE
    struct.pack_into("<I", fmv, unclassified_offset, 0xAC239A56)
    with pytest.raises(SystemExit, match="unclassified typed-state xref"):
        owners.build(fmv_data=bytes(fmv), verify_identity=False)

    fmv = bytearray(owners.FMV_PATH.read_bytes())
    typed_offset = 0x800B6DB8 - owners.FMV_BASE
    struct.pack_into("<I", fmv, typed_offset, 0)
    with pytest.raises(SystemExit, match="typed-state xref drift"):
        owners.build(fmv_data=bytes(fmv), verify_identity=False)

    legacy = copy.deepcopy(json.loads(owners.LEGACY_FMV_PATH.read_text()))
    legacy["run_provenance"]["cleanup"]["owned_pid_stopped"] = False
    with pytest.raises(SystemExit, match="owned_cleanup"):
        owners.build(legacy_doc=legacy, verify_identity=False)


def test_fmv_schema_banks_the_static_and_interface_boundaries_without_closing_e15():
    schema = yaml.safe_load((ROOT / "config/phase4_fmv.yaml").read_text())
    assert schema["schema"] == "abl-phase4-fmv/11"
    static = schema["static_selector_ownership"]
    assert static["direct_resident_calls"] == 9
    assert static["level_a_table"]["selectors"] == [10, 38]
    assert static["level_b_table"]["selectors"] == [11, 39]
    assert static["bonus_cursor"]["wrap_streaming_old_value"] == 255
    assert static["reachability"]["reviewed_unreachable_stream_selectors"] == [2]
    assert static["completion_request"]["xrefs"] == 4
    assert schema["typed_state"]["player_boundary"][
        "region_b_address_rows"] == 30
    assert schema["interface_frontier"]["resident_consumers"][
        "direct_call_count"] == 9
    assert schema["interface_frontier"]["source_status"][
        "unclassified_callbacks"] == 0
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    assert campaign["status"] == "active"
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "fmv_playback: status is not completed"]


def test_four_promoted_dimensions_remain_audited_after_static_continuations():
    debt = json.loads((ROOT / "analysis/phase4_closure_debt.json").read_text())
    e15 = next(row for row in debt["rows"] if row["row_id"] == "E15_fmv")
    assert e15["dimensions"]["original_oracle"] == {
        "basis": "audited dimension promotion", "errors": [], "state": "met"}
    assert e15["dimensions"]["complete_frontier"] == {
        "basis": "audited dimension promotion", "errors": [], "state": "met"}
    assert e15["dimensions"]["typed_state"] == {
        "basis": "audited dimension promotion", "errors": [], "state": "met"}
    assert e15["dimensions"]["durable_evidence"] == {
        "basis": "audited dimension promotion", "errors": [], "state": "met"}
    assert e15["dimensions"]["original_interfaces"] == {
        "basis": "retained evidence exists but no audited promotion",
        "errors": [], "state": "partial"}
    assert e15["counts"] == {"met": 4, "not_applicable": 0, "remaining": 5}
    assert e15["next_lane"] == "static"
    assert "exhausts the player's post-helper decision partition" in \
        e15["next_lane_reason"]
    assert "Completion alone issues CdlStop(8)" in \
        e15["next_lane_reason"]
    assert "without promoting lifecycle" in \
        e15["next_lane_reason"]
    assert "first caller-owned Region-B overwrite" in \
        e15["next_action"]
    assert "classify its E16/E14 owner" in \
        e15["next_action"]
    continuations = json.loads((
        ROOT / "analysis/phase4_fmv_lifecycle_continuations.json").read_text())
    assert continuations["summary"]["unclassified_continuations"] == 0
    assert continuations["transient_player_continuations"][
        "static_routing_closed"] is True
    assert continuations["dimension_boundary"]["claim"] == "partial"
    route = continuations["transient_player_continuations"][
        "native_cd_event_route"]
    assert route["unclassified_static_edges"] == 0
    assert route["runtime_event_delivery_claimed"] is False
    assert debt["counts"]["dimensions"] == {
        "gap": 769, "met": 148, "partial": 46}
