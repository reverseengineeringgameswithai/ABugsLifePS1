"""Falsification guards for the active Thud launch/path/reset campaign."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_thud_defeat as thud  # noqa: E402
import ps1_scenario  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_thud_defeat.json"
ARTIFACT_SHA256 = "74a2651cce32d860118adbc83f58ebaca7c1efa252ee205dbdce6ceece868338"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_thud_defeat_recomputes_low_level_evidence():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert thud.evidence_gaps(doc) == []
    assert doc["summary"] == thud.derive_summary(doc)
    assert doc["summary"] == {
        "movies_replayed": 1,
        "launch_action_instruction_pc": "0x8005a1d8",
        "launch_caller_return": "0x80047254",
        "thud_attack_action_instruction_pc": "0x8005a1d8",
        "thud_attack_caller": "0x800b3ff0",
        "thud_attack_contact_transition": [1, 20],
        "thud_attack_countdown_control": {
            "before": [9, 1, 0, 0],
            "control_after": [8, 20, 200, 128],
            "countdown_zero_after": [0, 1, 0, 0],
        },
        "thud_attack_sound_call": "0x800b3ffc",
        "thud_attack_sound_request": [-14, "0x8009fd84"],
        "thud_attack_sound_key_on": {
            "natural_event_total": 13,
            "call_nop_event_total": 7,
            "start_address": "0x00009e10",
            "frames": [327715, 327716, 327718, 327720],
        },
        "thud_attack_natural_retirement": [175, 0, 0, 0],
        "thud_attack_radius_control": {
            "before": [0, 4, 20, 200, 100, 24],
            "control_after": [0, 4, 20, 199, 100, 24],
            "radius_enlarged_after": [1, 4, 20, 1, 6000, 16],
        },
        "thud_attack_effect_instruction_pcs": [
            "0x80054f9c", "0x800589e0", "0x800589e4"],
        "thud_attack_visual_diff": {
            "pixel_count": 593,
            "bounding_boxes": [
                {"x": 449, "y": 159, "width": 28, "height": 35}],
        },
        "thud_attack_visual_draw": {
            "primitive": "quad", "command_id": 44,
            "dma_source": "0x001cf3d4",
        },
        "thud_attack_renderer": "0x80014844",
        "square_clear_post_action": [2, 4],
        "square_clear_damage_hp": [48, 50],
        "square_clear_phase_counter": [1, 0],
        "natural_transient_hp": [50, 48, 48, 50],
        "damage_instruction_pc": "0x800590e4",
        "restore_instruction_pc": "0x800b3ed0",
        "damage_class_control_hp": [48, 46],
        "overlay_target_control_hp": [50, 49],
        "arena_damage_health": [3, 2],
        "arena_transform_rows": 6,
        "arena_hit_row": 4,
        "arena_damage_call": "0x800b4ae0",
        "arena_threshold_control_health": [2, 3],
        "natural_reset_cycles": 8,
        "phase_restore_frames": [967, 1313, 1713, 2127, 2525, 2941, 3311, 3741],
        "phase_counter_transition": [0, 8],
        "arena_master_transition": [0, 1],
        "phase_path_coordinate_transition": [156704, 4294926880],
        "trajectory_control_delta": {
            "path_coordinate": 4096,
            "actor_position": [4096, 0, 0],
            "actor_motion_target_x_unknown_30_z": [4096, 0, 4096],
            "player_position": [0, 0, 0],
        },
        "phase_guard_outcomes": {
            "control": [50, 50, 1, 9, 0, 0, 0],
            "target_equals_hp": [48, 48, 0, 0, 0, 0, 0],
            "hp_floor": [20, 50, 0, 0, 0, 0, 0],
            "arena_sentinel": [50, 50, 0, 0, 0, 0, 0],
            "counter_eight": [50, 50, 8, 0, 1, 32, 149],
            "grain_formula": [50, 50, 1, 8, 0, 0, 0],
        },
        "natural_hp_transition": [50, 0],
        "hp_zero_instruction_pc": "0x800b4528",
        "retire_instruction_pcs": ["0x8004d270", "0x8004d43c"],
        "retired_movie_frame": 3902,
        "scene_exit": [14, 0],
        "event_program_19_decode_complete": True,
        "runtime_overlay_exactly_staged": False,
        "reset_owner_instruction_count": 153,
        "post_restore_continuation_instruction_count": 77,
        "arena_block_instruction_count": 196,
        "d18_or_f09_completed": 0,
    }
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_thud_defeat.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_thud_fixture_and_static_context_recompute_from_pins():
    doc = load_artifact()
    assert thud.build_fixture_census() == doc["fixture_census"]
    assert thud.build_static_census() == doc["static_census"]
    assert doc["fixture_census"]["movie"]["sha256"] == thud.MOVIE_SHA256
    assert doc["fixture_census"]["save"]["sha256"] == thud.SAVE_SHA256
    program = doc["static_census"]["event_program"]
    assert program["decode_complete"] is True
    assert next(row for row in program["instructions"]
                if row["ip"] == "0x800777a6") == {
        "ip": "0x800777a6", "raw": "0xffff", "idx": 0,
        "op": "jump_back", "conf": "CONFIRMED", "operands": [1],
        "target": "0x800777a4",
    }
    executable = doc["static_census"]["pristine_executable"]
    assert executable["pin"] == {
        "sha256": "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20",
        "size": 471040,
    }
    assert {key: row["sha256"] for key, row in
            executable["resident_slices"].items()} == {
            "contact_vs_actor_damage_block": thud.DAMAGE_SLICE_SHA256,
            "contact_dispatcher": thud.DISPATCHER_SHA256,
            "overlay_update_call": thud.OVERLAY_CALL_SLICE_SHA256,
            "throw_launch_call": thud.THROW_LAUNCH_SLICE_SHA256,
            "contact_allocator": thud.CONTACT_ALLOCATOR_SLICE_SHA256,
            "pass2_object_transform_update": thud.PASS2_TRANSFORM_SLICE_SHA256,
            "collision_candidate_builder": thud.COLLISION_CANDIDATE_SLICE_SHA256,
            "resident_level_transition_initiator": thud.PLAYER_TRANSITION_SLICE_SHA256,
            "action20_dispatch_entry": thud.ACTION20_DISPATCH_ENTRY_SHA256,
            "action20_dispatch_and_common_tail": thud.ACTION20_TAIL_SLICE_SHA256,
            "grain_increment_writer": thud.GRAIN_INCREMENT_SLICE_SHA256,
            "play_sound": thud.PLAY_SOUND_SLICE_SHA256,
            "contact_record_billboard_render": thud.CONTACT_RENDERER_SHA256,
    }


def test_recorded_square_launch_has_exact_allocator_and_counterfactual():
    doc = load_artifact()
    launch = doc["launch_writer_attribution"]
    writers = launch["decisive_writers"]
    assert (writers["action_id"]["instruction_pc"],
            writers["action_id"]["instruction_word"],
            writers["action_id"]["value"],
            writers["action_id"]["new_value"]) == (
                "0x8005a1d8", "0xa6020020", 4, 2)
    assert (writers["lifetime_ttl"]["instruction_pc"],
            writers["lifetime_ttl"]["new_value"]) == ("0x8005a1e4", 100)
    assert (writers["damage_class"]["instruction_pc"],
            writers["damage_class"]["new_value"]) == ("0x8005a270", 0)
    assert launch["caller"] == {
        "allocator_entry": "0x8005a0e0",
        "return_address": "0x80047254",
        "jal_instruction": "0x8004724c",
        "classification": "resident player throw dispatcher",
    }
    assert launch["access"]["total"] == len(launch["access"]["events"]) == 41
    assert launch["access"]["truncated"] is False

    control = doc["launch_input_counterfactual"]
    assert control["observed_outcomes"] == {
        "post_launch": {"natural": [9, 3, 2, 99],
                        "square_cleared": [0, 2, 4, 0]},
        "damage": {"natural": [48, 2], "square_cleared": [50, 4]},
        "restore": {"natural": [50, 1, 4294801440],
                    "square_cleared": [50, 0, 4294798880]},
    }
    before_natural = control["natural"]["points"]["896"]
    before_edited = control["square_cleared"]["points"]["896"]
    for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                "main_ram_sha256", "registers_sha256"):
        assert before_natural[key] == before_edited[key]
    assert control["edit_recipe"]["edited_frame_count"] == 22
    assert control["edit_recipe"]["field"] == "ports.0.square"
    assert "no derivative movie bytes are retained" in control["control_rule"]


def test_post_restore_thud_owned_action_20_launch_is_bounded_and_causal():
    doc = load_artifact()
    runtime = doc["runtime_overlay_identity"]["post_restore_attack_slice"]
    assert (runtime["address"], runtime["length"], runtime["sha256"],
            runtime["instruction_count"]) == (
                "0x800b3ed4", 0x134,
                thud.POST_RESTORE_CONTINUATION_SHA256, 77)
    assert runtime["disassembly_validation"][
        "exact_runtime_bytes_reconstructed"] is True
    assert {address: (row["mnemonic"], row["target"])
            for address, row in runtime["control_transfers"].items()} == \
        thud.POST_RESTORE_CONTROL_TRANSFERS

    boundaries = doc["post_restore_attack_boundaries"]
    expected = {
        "970": ((9, 1, 0, 0), (1, 6)),
        "971": ((8, 20, 200, 128), (2, 7)),
    }
    for frame, (wanted_state, wanted_counts) in expected.items():
        row = boundaries[frame]
        snapshot = row["snapshot"]
        contact = snapshot["thud_attack_contact"]
        assert (snapshot["phase_reset"]["grain_derived_value"],
                contact["action_id"], contact["lifetime_ttl"],
                contact["damage_class"]) == wanted_state
        trace = row["cycle_neutral_trace"]
        assert trace["comparison"]["cycle_neutral"] is True
        assert all(coverage["truncated"] is False
                   for coverage in trace["coverage"])
        counts = {entry["pc"]: entry["count"]
                  for coverage in trace["coverage"]
                  for entry in coverage["decisive_counts_by_pc"]}
        assert (counts["0x800b3ff0"], counts["0x8005a0e0"]) == \
            wanted_counts

    attribution = doc["post_restore_attack_attribution"]
    writers = attribution["decisive_writers"]
    assert (writers["action_id"]["instruction_pc"],
            writers["action_id"]["value"],
            writers["action_id"]["new_value"]) == (
                "0x8005a1d8", 1, 20)
    assert writers["lifetime_ttl"]["new_value"] == 200
    assert writers["damage_class"]["new_value"] == 128
    assert attribution["caller"] == {
        "actor": "0x8009fd80",
        "allocator_call": "0x800b3ff0",
        "allocator_entry": "0x8005a0e0",
        "return_address": "0x800b3ff8",
        "classification": "save-owned Thud overlay continuation",
    }
    assert attribution["access"]["total"] == \
        len(attribution["access"]["events"]) == 27
    assert attribution["access"]["truncated"] is False
    assert all(page["total"] == 1 and page["truncated"] is False
               for page in attribution["execution"].values())

    control = doc["post_restore_attack_control"]
    assert control["single_field"] == "0x800b4cb4"
    assert control["observed_outcomes"] == {
        "before": [9, 1, 0, 0],
        "control_after": [8, 20, 200, 128],
        "countdown_zero_after": [0, 1, 0, 0],
    }
    for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                "main_ram_sha256", "registers_sha256"):
        assert control["control"]["before"][key] == \
            control["countdown_zero"]["before"][key]
    assert control["endpoint_alignment"] == {
        "emulator_frame_equal": True,
        "movie_frame_equal": True,
        "mutation_minus_control_cycle": -1,
        "control_pc": "0x8004fea4",
        "mutation_pc": "0x8004fea4",
    }
    assert "separate matched visual control" in attribution["effect_boundary"]


def test_action_20_launch_sound_request_and_spu_key_ons_are_causal():
    doc = load_artifact()
    attribution = doc["action20_sound_attribution"]
    assert attribution["caller"] == {
        "instruction_pc": "0x800b3ffc",
        "instruction_word": "0x0c014113",
        "actor": "0x8009fd80",
        "callee": "0x8005044c",
        "return_address": "0x800b4004",
        "classification": "save-owned Thud overlay continuation",
    }
    assert attribution["request"] == {
        "signed_cue": -14,
        "unsigned_a0": "0xfffffff2",
        "position_context": "0x8009fd84",
        "play_sound_entry": "0x8005044c",
        "positive_dispatch_hits_in_window": 0,
    }
    assert {label: page["total"] for label, page in
            attribution["execution"].items()} == {
                "caller": 1, "play_sound": 3, "positive_dispatch": 0}
    assert all(page["total"] == len(page["events"]) and
               page["truncated"] is False
               for page in attribution["execution"].values())

    control = doc["action20_sound_control"]
    natural = control["natural"]
    call_nop = control["call_nop"]
    for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                "main_ram_sha256", "registers_sha256"):
        assert natural["before"][key] == call_nop["before"][key]
    assert call_nop["mutation"]["main_ram_differences"] == [
        {"address": "0x800b3ffc", "before": 0x13, "after": 0},
        {"address": "0x800b3ffd", "before": 0x41, "after": 0},
        {"address": "0x800b3ffe", "before": 0x01, "after": 0},
        {"address": "0x800b3fff", "before": 0x0C, "after": 0},
    ]
    assert call_nop["mutation"]["response"]["written"] == 4
    assert call_nop["mutation"]["response"]["code_invalidated"] is True
    assert control["endpoint_alignment"] == {
        "emulator_frame_equal": True,
        "movie_frame_equal": True,
        "pc_equal": True,
        "sp_equal": True,
        "natural_pc": "0x800104b8",
        "nop_pc": "0x800104b8",
        "nop_minus_natural_cycle": 1,
        "action20_record_equal": True,
        "gameplay_state_equal": True,
    }
    assert natural["after"]["thud_attack_contact"]["record_hex"] == \
        call_nop["after"]["thud_attack_contact"]["record_hex"]
    comparison = control["event_comparison"]
    assert {key: comparison[key] for key in (
        "natural_total", "call_nop_total", "natural_minus_call_nop",
        "shared_event_frame")} == {
            "natural_total": 13,
            "call_nop_total": 7,
            "natural_minus_call_nop": 6,
            "shared_event_frame": 327722,
        }
    assert [(event["frame"], event["start_address"]) for event in
            comparison["natural_early_key_ons"]] == [
                (327715, "0x00009e10"), (327716, "0x00009e10"),
                (327718, "0x00009e10"), (327720, "0x00009e10"),
            ]
    assert comparison["call_nop_early_key_ons"] == []
    assert "host-speaker drain" in control["forbidden_claim"]


def test_action_20_natural_miss_and_controlled_grain_effect_are_causal():
    doc = load_artifact()
    boundaries = doc["action20_effect_boundaries"]
    expected = {
        "972": (0, 20, 200, 100, 24),
        "973": (0, 20, 199, 100, 24),
        "1021": (0, 20, 175, 100, 24),
        "1023": (0, 20, 0, 100, 24),
    }
    for frame, wanted in expected.items():
        row = boundaries[frame]
        snapshot = row["snapshot"]
        contact = snapshot["thud_attack_contact"]
        assert (snapshot["phase_reset"]["grain"], contact["action_id"],
                contact["lifetime_ttl"], contact["radius_add"],
                contact["state"]) == wanted
        assert row["walker_geometry"]["inside_radius"] is False
        trace = row["cycle_neutral_trace"]
        assert trace["comparison"]["cycle_neutral"] is True
        assert all(coverage["truncated"] is False
                   for coverage in trace["coverage"])
        pcs = {pc for coverage in trace["coverage"]
               for pc in coverage["pcs"]}
        assert "0x80054eac" not in pcs
        assert "0x80054f9c" not in pcs

    control = doc["action20_effect_control"]
    assert control["single_field"] == "0x800b10f8"
    assert control["observed_outcomes"] == {
        "before": [0, 4, 20, 200, 100, 24],
        "control_after": [0, 4, 20, 199, 100, 24],
        "radius_enlarged_after": [1, 4, 20, 1, 6000, 16],
    }
    natural = control["control"]
    mutated = control["radius_enlarged"]
    for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                "main_ram_sha256", "registers_sha256"):
        assert natural["before"][key] == mutated["before"][key]
    assert natural["before_geometry"]["inside_radius"] is False
    assert mutated["after_write_geometry"]["inside_radius"] is True
    assert mutated["mutation"]["main_ram_differences"] == [
        {"address": "0x800b10f8", "before": 100, "after": 0x70},
        {"address": "0x800b10f9", "before": 0, "after": 0x17},
    ]
    assert mutated["mutation"]["main_ram_difference_count"] == 2
    assert control["endpoint_alignment"]["emulator_frame_equal"] is True
    assert control["endpoint_alignment"]["movie_frame_equal"] is True
    assert control["endpoint_alignment"] == {
        "emulator_frame_equal": True,
        "movie_frame_equal": True,
        "cycle_equal": True,
        "mutation_minus_control_cycle": 0,
        "control_pc": "0x80010508",
        "mutation_pc": "0x80010508",
    }

    attribution = doc["action20_effect_attribution"]
    writers = attribution["decisive_writers"]
    assert (writers["grain_increment"]["instruction_pc"],
            writers["grain_increment"]["instruction_word"],
            writers["grain_increment"]["value"],
            writers["grain_increment"]["new_value"]) == (
                "0x80054f9c", "0xa0430000", 0, 1)
    assert (writers["record_state"]["instruction_pc"],
            writers["record_state"]["value"],
            writers["record_state"]["new_value"]) == (
                "0x800589e0", 24, 16)
    assert (writers["record_active_gate"]["instruction_pc"],
            writers["record_active_gate"]["new_value"]) == (
                "0x800589e4", 1)
    assert attribution["access"]["total"] == \
        len(attribution["access"]["events"]) == 10
    assert attribution["access"]["truncated"] is False
    assert {label: page["total"] for label, page in
            attribution["execution"].items()} == {
                "action20_dispatch": 1, "grain_handler_entry": 1,
                "grain_increment_store": 1, "record_state_store": 1,
                "record_active_store": 1, "bookkeeping_call": 1,
                "bookkeeping_entry": 3,
            }
    assert attribution["decisive_registers"]["bookkeeping"]["a0"] == \
        0xFFFFFFFF
    assert attribution["decisive_registers"]["bookkeeping"]["a1"] == \
        thud.THUD_ATTACK_CONTACT_RECORD
    assert "separate matched control binds one textured billboard" in \
        attribution["bounded_effect"]


def test_action_20_textured_billboard_is_causally_isolated_and_attributed():
    doc = load_artifact()
    visual = doc["action20_visual_presentation_control"]
    assert visual["target_movie_frame"] == 980
    assert visual["single_field"] == "0x800b4cb4"
    assert visual["endpoint_alignment"] == {
        "emulator_frame_equal": True,
        "movie_frame_equal": True,
        "sp_equal": True,
        "pc_equal": False,
        "suppressed_minus_natural_cycle": 0,
        "natural_pc": "0x800104b8",
        "suppressed_pc": "0x80010508",
    }
    for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                "main_ram_sha256", "registers_sha256"):
        assert visual["natural"]["before"][key] == \
            visual["countdown_zero"]["before"][key]
    assert visual["countdown_zero"]["mutation"][
        "main_ram_differences"] == [
            {"address": "0x800b4cb4", "before": 9, "after": 0}]
    assert visual["natural"]["after"]["thud_attack_contact"][
        "action_id"] == 20
    assert visual["countdown_zero"]["after"]["thud_attack_contact"][
        "action_id"] != 20

    diff = visual["frame_diff"]
    assert diff["changed"] is True
    assert diff["pixelCount"] == 593
    assert diff["boundingBoxes"] == [
        {"x": 449, "y": 159, "width": 28, "height": 35}]
    assert diff["region"] == {"x": 0, "y": 0, "width": 800, "height": 610}
    assert diff["metrics"] == {
        "changedPixels": 593,
        "maxDifference": 251,
        "meanAbsoluteDifference": 0.06294006147540984,
        "normalizedScore": 0.0012151639344262295,
        "totalPixels": 488000,
    }

    pick = visual["natural_object_pick"]
    assert pick["query"] == {"x": 295, "y": 65}
    assert pick["pixel"]["rgba"] == [107, 156, 0, 255]
    assert (pick["draw_call"]["primitiveType"],
            pick["draw_call"]["commandId"],
            pick["draw_call"]["frame"]) == ("quad", 44, 327721)
    assert pick["geometry"]["screenRect"] == {
        "x": 799, "y": 322, "width": 20, "height": 13}
    assert pick["geometry"]["uv"] == [
        [240, 112], [255, 112], [240, 127], [255, 127]]
    assert {key: pick["texture"][key] for key in (
        "bpp", "pageX", "pageY", "clutX", "clutY")} == {
            "bpp": "4bpp", "pageX": 512, "pageY": 0,
            "clutX": 880, "clutY": 221,
        }
    assert {key: pick["source"][key] for key in (
        "ramAddress", "dmaSource", "vertexPointer",
        "orderingTableEntry")} == {
            "ramAddress": "0x001cf3d4",
            "dmaSource": "0x001cf3d4",
            "vertexPointer": "0x001cf3d8",
            "orderingTableEntry": "0x001cf3d0",
        }
    assert "Raw GP0 words" in pick["retention_boundary"]

    renderer = doc["action20_renderer_attribution"]
    assert renderer["access"]["total"] == 118
    assert renderer["access"]["truncated"] is False
    assert renderer["access"]["read_watch_hits"] == 102
    assert renderer["access"]["packet_watch_hits"] == 16
    assert renderer["renderer"]["address"] == "0x80014844"
    assert renderer["renderer"]["end_exclusive"] == "0x80014ad4"
    assert renderer["renderer"]["read_total"] == 22
    assert renderer["renderer"]["read_frames"] == [327716, 327722]
    assert sorted(int(row["instruction_pc"], 16) for row in
                  renderer["renderer"]["slot17_reads"]) == sorted(
                      list(thud.CONTACT_RENDERER_READ_PCS) * 2)
    packet = renderer["picked_packet"]
    assert packet["write_total"] == len(packet["writes"]) == 16
    assert packet["first_packet_address_to_instruction_pc"] == {
        "0x801cf3d4": "0x80014a30", "0x801cf3dc": "0x80014a34",
        "0x801cf3e4": "0x80014a38", "0x801cf3ec": "0x80014a3c",
        "0x801cf3d0": "0x80014a40", "0x801cf3e8": "0x80014a44",
        "0x801cf3d8": "0x80014a58", "0x801cf3e0": "0x80014a6c",
    }


def test_transient_damage_and_restore_have_passive_fixed_boundaries():
    doc = load_artifact()
    expected = {
        "964": (50, 2, 0, 50),
        "965": (48, 2, 0, 50),
        "966": (48, 2, 0, 50),
        "967": (50, 2, 0, 50),
    }
    for frame, wanted in expected.items():
        row = doc["transient_damage_boundaries"][frame]
        snapshot = row["snapshot"]
        assert (snapshot["actor"]["hp"], snapshot["contact"]["action_id"],
                snapshot["contact"]["damage_class"],
                snapshot["overlay_target_hp"]) == wanted
        assert row["cycle_neutral_trace"]["comparison"]["cycle_neutral"] is True
        assert all(not item["truncated"]
                   for item in row["cycle_neutral_trace"]["coverage"])
    damage_pcs = {pc for row in doc["transient_damage_boundaries"]["965"]
                  ["cycle_neutral_trace"]["coverage"] for pc in row["pcs"]}
    reset_pcs = {pc for row in doc["transient_damage_boundaries"]["967"]
                 ["cycle_neutral_trace"]["coverage"] for pc in row["pcs"]}
    assert "0x800590e4" in damage_pcs
    assert "0x800b3ed0" in reset_pcs


def test_transient_writers_and_one_field_controls_are_causal():
    doc = load_artifact()
    attribution = doc["transient_writer_attribution"]
    damage = attribution["decisive_writers"]["damage"]
    restore = attribution["decisive_writers"]["restore"]
    assert (damage["instruction_pc"], damage["instruction_word"],
            damage["value"], damage["new_value"]) == (
                "0x800590e4", "0xa642006e", 50, 48)
    assert (restore["instruction_pc"], restore["instruction_word"],
            restore["value"], restore["new_value"]) == (
                "0x800b3ed0", "0xa662006e", 48, 50)
    assert attribution["access"]["truncated"] is False
    assert attribution["access"]["total"] == len(attribution["access"]["events"])
    controls = doc["causal_controls"]
    assert [controls["damage_class"][side]["after"]["actor"]["hp"]
            for side in ("control", "mutation")] == [48, 46]
    assert [controls["overlay_target_hp"][side]["after"]["actor"]["hp"]
            for side in ("control", "mutation")] == [50, 49]
    for key in ("damage_class", "overlay_target_hp"):
        control = controls[key]["control"]
        mutation = controls[key]["mutation"]
        assert control["before"]["main_ram_sha256"] == \
            mutation["before"]["main_ram_sha256"]
        assert control["after"]["emulator_frame"] == \
            mutation["after"]["emulator_frame"]
        assert control["after"]["cycle"] == mutation["after"]["cycle"]


def test_rolling_boulder_six_row_contact_and_threshold_control_are_causal():
    doc = load_artifact()
    boundaries = doc["natural_arena_damage_boundaries"]
    assert [boundaries[str(frame)]["snapshot"]["health"] for frame in
            (thud.ARENA_DAMAGE_PRE_FRAME, thud.ARENA_DAMAGE_POST_FRAME)] == [3, 2]
    assert [boundaries[str(frame)]["snapshot"]["player"]["position"] for frame in
            (thud.ARENA_DAMAGE_PRE_FRAME, thud.ARENA_DAMAGE_POST_FRAME)] == [
                [104318, 1478, -20326], [99005, -934, -18472]]
    for row in boundaries.values():
        trace = row["cycle_neutral_trace"]
        assert trace["comparison"]["cycle_neutral"] is True
        assert all(item["truncated"] is False for item in trace["coverage"])
        pcs = {pc for item in trace["coverage"] for pc in item["pcs"]}
        assert {"0x800b49e0", "0x800b4a04", "0x800b4a60",
                "0x800b4ae0", "0x8004a700", "0x8004a888"}.issubset(pcs)

    attribution = doc["arena_damage_attribution"]
    rows = attribution["distance_rows"]
    assert [row["row"] for row in rows] == list(range(6))
    assert [row["row"] for row in rows if row["inside_threshold"]] == [4]
    assert attribution["hit_row"] == {
        "row": 4, "phase_address": "0x800b4c88",
        "threshold_address": "0x800b4c1c",
        "squared_distance": 454805,
        "squared_distance_threshold": 490000,
        "inside_threshold": True,
        "transformed_position": [3448, -547, -919],
    }
    health = attribution["decisive_health_write"]
    assert (health["instruction_pc"], health["instruction_word"],
            health["value"], health["new_value"]) == (
                "0x8004a888", "0xa4236594", 3, 2)
    assert attribution["access"]["total"] == 1
    assert attribution["access"]["truncated"] is False
    assert all(page["total"] == page["returned"] and
               page["truncated"] is False
               for page in attribution["execution"].values())

    control = doc["arena_damage_control"]
    assert control["single_field"] == "0x800b4c1c"
    assert control["mutation"] == {"from": 490000, "to": 0}
    assert control["observed_health"] == {
        "before": 3, "control_after": 2, "threshold_zero_after": 3}
    for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                "main_ram_sha256", "registers_sha256"):
        assert control["control"]["before"][key] == \
            control["threshold_zero"]["before"][key]
    assert control["control"]["after"]["player"]["position"] == \
        control["threshold_zero"]["after"]["player"]["position"]
    assert control["endpoint_alignment"] == {
        "emulator_frame_equal": True,
        "movie_frame_equal": True,
        "pc_equal": True,
        "sp_equal": True,
        "cycle_equal": True,
        "threshold_zero_minus_control_cycle": 0,
        "control_pc": "0x8004fea4",
        "threshold_zero_pc": "0x8004fea4",
    }


def test_eight_natural_resets_bind_counter_and_path_transition():
    cycles = load_artifact()["natural_phase_cycles"]
    assert [row["damage_target_movie_frame"] for row in cycles] == \
        list(thud.PHASE_DAMAGE_FRAMES)
    assert [row["restore_target_movie_frame"] for row in cycles] == \
        list(thud.PHASE_RESTORE_FRAMES)
    assert [row["damage"]["snapshot"]["phase_reset"]["counter"]
            for row in cycles] == list(range(8))
    assert [row["restore"]["snapshot"]["phase_reset"]["counter"]
            for row in cycles] == list(range(1, 9))
    assert [row["damage"]["snapshot"]["actor"]["hp"]
            for row in cycles] == [48] * 8
    assert [row["restore"]["snapshot"]["actor"]["hp"]
            for row in cycles] == [50] * 8
    assert [row["restore"]["snapshot"]["master_state"]
            for row in cycles] == [0] * 7 + [1]
    assert cycles[-1]["restore"]["snapshot"]["phase_reset"] == {
        "timer": 3, "arena_position": 156704,
        "grain_derived_value": 0, "counter": 8, "heading": 32,
        "motion_timer": 149, "grain": 14,
    }
    for row in cycles:
        for side in ("damage", "restore"):
            trace = row[side]["cycle_neutral_trace"]
            assert trace["comparison"]["cycle_neutral"] is True
            assert all(item["truncated"] is False for item in trace["coverage"])


def test_post_counter_eight_path_writers_and_control_are_causal():
    doc = load_artifact()
    mid = doc["trajectory_mid_boundary"]
    assert mid["snapshot"]["phase_reset"]["arena_position"] == 61984
    assert mid["snapshot"]["actor"]["position"] == [102808, -39328, -3845]
    assert mid["snapshot"]["actor"]["motion_target_x_unknown_30_z"] == \
        [61984, -608, 61984]
    assert mid["cycle_neutral_trace"]["comparison"]["cycle_neutral"] is True

    attribution = doc["trajectory_writer_attribution"]
    expected_pcs = {
        "early_window": {
            thud.PATH_DECREMENT_STORE, thud.TARGET_X_STORE,
            thud.TARGET_Z_STORE, thud.MOTION_TIMER_STORE, thud.HEADING_STORE,
            thud.ACTOR_EARLY_X_STORE, thud.ACTOR_EARLY_Z_STORE,
            thud.ACTOR_TARGET_X_READER, thud.ACTOR_TARGET_Z_READER,
        },
        "late_window": {
            thud.PATH_DECREMENT_STORE, thud.TARGET_X_STORE,
            thud.TARGET_Z_STORE, thud.MOTION_TIMER_STORE, thud.HEADING_STORE,
            thud.ACTOR_LATE_X_STORE, thud.ACTOR_LATE_Z_STORE,
        },
    }
    for window, expected in expected_pcs.items():
        pcs = {int(row["instruction_pc"], 16)
               for row in attribution[window]["events"]}
        assert expected.issubset(pcs)
        accounting = attribution[window]["accounting"]
        assert accounting["total"] == accounting["returned"]
        assert accounting["truncated"] is False
    initial = attribution["decisive_initial_stores"]
    assert [initial["path_decrement"][key]
            for key in ("value", "new_value")] == [156704, 154144]
    assert initial["actor_target_x"]["new_value"] == 154144
    assert initial["actor_target_z"]["new_value"] == 154144

    control = doc["trajectory_control"]
    assert control["single_field"] == "0x800b4cb0"
    assert control["delta"] == 4096
    assert control["observed_end_deltas"] == {
        "actor_position": [4096, 0, 0],
        "actor_motion_target_x_unknown_30_z": [4096, 0, 4096],
        "path_coordinate": 4096,
        "player_position": [0, 0, 0],
    }
    assert control["control"]["end"]["actor"]["position"] == \
        [532, -39328, -1551]
    assert control["control"]["end"]["actor"][
        "motion_target_x_unknown_30_z"] == \
        [-40416, -608, -40416]
    for side in ("control", "mutation"):
        retired = control[side]["retired"]
        assert (retired["actor"]["hp"], retired["actor"]["flags"],
                retired["live_table_0"]) == (0, "0x0055", "0x00000000")


def test_phase_branch_operands_and_matched_controls_are_causal():
    doc = load_artifact()
    branches = doc["phase_branch_attribution"]

    def tuples(window, label, registers):
        return {tuple(int(event["regs"][register], 0) for register in registers)
                for event in branches[window]["events"][label]["events"]}

    assert (50, 48) in tuples("first_reset", "hp_equal_gate", ("v0", "v1"))
    assert (thud.ARENA_NEGATIVE_SENTINEL,
            thud.ARENA_NEGATIVE_SENTINEL) in tuples(
                "first_reset", "negative_arena_gate", ("v0", "v1"))
    assert (8, 8) in tuples(
        "eighth_reset", "counter_eight_gate", ("v0", "v1"))
    assert (46, 48) in tuples(
        "eighth_reset", "target_minus_four_gate", ("v0", "v1"))
    assert branches["first_reset"]["events"]["positive_arena_gate"][
        "events"] == []
    assert branches["eighth_reset"]["events"]["grain_threshold_gate"][
        "events"] == []

    controls = doc["causal_controls"]
    phase = controls["phase_reset_guards"]
    assert phase["observed_outcomes"] == phase["expected_outcomes"] == {
        "control": [50, 50, 1, 9, 0, 0, 0],
        "target_equals_hp": [48, 48, 0, 0, 0, 0, 0],
        "hp_floor": [20, 50, 0, 0, 0, 0, 0],
        "arena_sentinel": [50, 50, 0, 0, 0, 0, 0],
        "counter_eight": [50, 50, 8, 0, 1, 32, 149],
        "grain_formula": [50, 50, 1, 8, 0, 0, 0],
    }
    for mutation in phase["mutations"].values():
        assert mutation["before"]["main_ram_sha256"] == \
            phase["control"]["before"]["main_ram_sha256"]
    master = controls["master_timer_gate"]
    assert master["control"]["after_shared_setup"]["main_ram_sha256"] == \
        master["mutation"]["after_shared_setup"]["main_ram_sha256"]
    assert master["observed_outcomes"] == {
        "control": [50, 105, 1, 0], "mutation": [48, 0, 0, 1]}


def test_natural_boundaries_and_exact_writers_are_independently_bound():
    doc = load_artifact()
    boundaries = doc["natural_defeat_boundaries"]
    expected = {
        "0": (14, 50, "0x4055", "0x8009fd80"),
        "3896": (14, 50, "0x4055", "0x8009fd80"),
        "3900": (14, 0, "0x4055", "0x8009fd80"),
        "3902": (14, 0, "0x0055", "0x00000000"),
        "4041": (0, 0, "0x0055", "0x00000000"),
        "4113": (0, 0, "0x0055", "0x00000000"),
    }
    for frame, wanted in expected.items():
        row = boundaries[frame]
        snap = row["snapshot"]
        assert (snap["scene"], snap["actor"]["hp"],
                snap["actor"]["flags"], snap["live_table_0"]) == wanted
        assert row["cycle_neutral_trace"]["comparison"]["cycle_neutral"] is True
        assert all(item["truncated"] is False
                   for item in row["cycle_neutral_trace"]["coverage"])

    writers = doc["writer_attribution"]["decisive_writers"]
    assert (writers["hp_zero"]["instruction_pc"],
            writers["hp_zero"]["instruction_word"],
            writers["hp_zero"]["value"],
            writers["hp_zero"]["new_value"]) == (
                "0x800b4528", "0xa660006e", 50, 0)
    assert (writers["active_clear"]["instruction_pc"],
            writers["active_clear"]["value"],
            writers["active_clear"]["new_value"]) == (
                "0x8004d270", 0x4055, 0x55)
    assert (writers["live_table_clear"]["instruction_pc"],
            writers["live_table_clear"]["value"],
            writers["live_table_clear"]["new_value"]) == (
                "0x8004d43c", thud.ACTOR, 0)
    assert writers["hp_zero"]["cycle"] < writers["active_clear"]["cycle"] < \
        writers["live_table_clear"]["cycle"]
    accounting = doc["writer_attribution"]["accounting"]
    assert (accounting["total"], accounting["returned"],
            accounting["truncated"]) == (103, 103, False)


def test_runtime_overlay_identity_is_exact_and_not_laundered_to_staged_file():
    runtime = load_artifact()["runtime_overlay_identity"]
    region = runtime["runtime_region_a"]
    staged = runtime["staged_candidates"]
    assert region["length_3500_sha256"] != staged["LEVEL08/LEVEL.BIN"]
    assert region["length_4064_sha256"] != staged["LEVEL08/LEVEL1.BIN"]
    assert runtime["exact_writer_slice"] == {
        "address": "0x800b4518", "length": 36,
        "sha256": thud.WRITER_SLICE_SHA256,
        "bytes_hex": "735f010c2120600210270224620062a66e0060a6090004240b80053cb84ca58c0b80063c",
    }
    reset = runtime["reset_owner_slice"]
    assert {key: reset[key] for key in (
        "address", "length", "sha256", "expected_sha256",
        "instruction_count")} == {
            "address": "0x800b3c70", "length": 612,
            "sha256": thud.RESET_OWNER_SHA256,
            "expected_sha256": thud.RESET_OWNER_SHA256,
            "instruction_count": 153,
        }
    assert reset["disassembly_validation"] == {
        "method": "debugger.disassemble",
        "first_address": "0x800b3c70",
        "last_address": "0x800b3ed0",
        "packed_little_endian_sha256": thud.RESET_OWNER_SHA256,
        "exact_runtime_bytes_reconstructed": True,
        "retention_boundary": (
            "The full original-game instruction capture is validated in memory "
            "but not retained; only decisive transfers and hash metadata are "
            "committed."),
    }
    assert {address: (row["mnemonic"], row["target"])
            for address, row in reset["control_transfers"].items()} == \
        thud.RESET_CONTROL_TRANSFERS
    arena = runtime["arena_transform_collision_slice"]
    assert {key: arena[key] for key in (
        "address", "length", "sha256", "expected_sha256",
        "instruction_count")} == {
            "address": "0x800b4814", "length": 784,
            "sha256": thud.ARENA_BLOCK_SHA256,
            "expected_sha256": thud.ARENA_BLOCK_SHA256,
            "instruction_count": 196,
        }
    assert arena["disassembly_validation"][
        "exact_runtime_bytes_reconstructed"] is True
    assert arena["disassembly_validation"][
        "packed_little_endian_sha256"] == thud.ARENA_BLOCK_SHA256
    assert {address: (row["mnemonic"], row["target"])
            for address, row in arena["control_transfers"].items()} == \
        thud.ARENA_CONTROL_TRANSFERS
    assert arena["bounded_structure"] == {
        "object_rotation_loop_rows": 10,
        "transform_collision_loop_rows": 6,
        "transform_call": "0x800b49e0",
        "candidate_call": "0x800b4a04",
        "damage_call": "0x800b4ae0",
    }
    assert runtime["classification"] == "save-owned exact runtime Region-A bytes"


def test_low_level_mutations_turn_thud_evidence_red():
    doc = load_artifact()
    mutated = copy.deepcopy(doc)
    mutated["natural_defeat_boundaries"]["3900"]["snapshot"]["actor"]["hp"] = 50
    assert "natural boundary 3900" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["writer_attribution"]["decisive_writers"]["hp_zero"][
        "instruction_pc"] = "0x800b4524"
    assert "decisive hp_zero writer" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["natural_defeat_boundaries"]["3902"]["cycle_neutral_trace"][
        "comparison"]["cycle_neutral"] = False
    assert "boundary 3902 trace" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["transient_damage_boundaries"]["965"]["snapshot"]["actor"]["hp"] = 50
    assert "transient boundary 965" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["causal_controls"]["damage_class"]["mutation"]["after"]["actor"]["hp"] = 48
    assert "one-field controls" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["natural_phase_cycles"][7]["restore"]["snapshot"][
        "phase_reset"]["counter"] = 7
    assert "natural phase cycles" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["causal_controls"]["phase_reset_guards"]["observed_outcomes"][
        "counter_eight"][2] = 7
    assert "phase controls" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["runtime_overlay_identity"]["reset_owner_slice"][
        "control_transfers"]["0x800b3db4"]["target"] = "0x800b3e98"
    assert "runtime overlay" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["launch_writer_attribution"]["decisive_writers"]["action_id"][
        "instruction_pc"] = "0x8005a1d4"
    assert "launch action_id writer" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["launch_input_counterfactual"]["observed_outcomes"]["damage"][
        "square_cleared"][0] = 48
    assert "Square launch control" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["post_restore_attack_boundaries"]["971"]["snapshot"][
        "thud_attack_contact"]["action_id"] = 1
    assert "post-restore boundary 971" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["post_restore_attack_control"]["observed_outcomes"][
        "countdown_zero_after"][1] = 20
    assert "post-restore countdown control" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["action20_sound_attribution"]["request"]["signed_cue"] = -13
    assert "sound attribution" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["action20_sound_control"]["event_comparison"][
        "natural_early_key_ons"][0]["start_address"] = "0x00009e18"
    assert "exact-call SPU control" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["action20_effect_boundaries"]["1023"]["snapshot"][
        "phase_reset"]["grain"] = 1
    assert "natural action-20 boundary 1023" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["action20_effect_control"]["observed_outcomes"][
        "radius_enlarged_after"][0] = 0
    assert "action-20 radius control" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["action20_effect_attribution"]["decisive_writers"][
        "grain_increment"]["instruction_pc"] = "0x80054f98"
    assert "action-20 grain_increment writer" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["action20_visual_presentation_control"]["frame_diff"][
        "pixelCount"] = 592
    assert "visual presentation control" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["action20_renderer_attribution"]["renderer"][
        "slot17_reads"][0]["instruction_pc"] = "0x800148dc"
    assert "renderer/packet attribution" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["trajectory_control"]["observed_end_deltas"][
        "path_coordinate"] = 0
    assert "path-coordinate causal" in " ".join(thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["arena_damage_attribution"]["distance_rows"][4][
        "inside_threshold"] = False
    assert "six-row arena attribution" in " ".join(
        thud.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["arena_damage_control"]["observed_health"][
        "threshold_zero_after"] = 2
    assert "arena threshold control" in " ".join(
        thud.evidence_gaps(mutated))


def test_campaign_remains_open_and_scenario_claims_only_measured_state():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "thud_bug_bar")
    assert campaign["status"] == "active"
    coverage = phase4_coverage.build()
    assert coverage["rows"]["D18_thud"]["state"] == "open"
    assert coverage["rows"]["F09_bug_bar"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91

    scenario = ps1_scenario.load_scenario(
        ROOT / "tools/scenarios/duckstation/pristine_thud_natural_defeat.yaml")
    assert scenario["playback"]["movie"] == thud.MOVIE_REL
    assert [phase["trigger"]["target"] for phase in scenario["phases"]] == [
        895, 914, 963, 964, 966, 969, 970, 1020, 1022, 1310, 1312, 1465,
        1471, 1710, 1712, 2124, 2126, 2522, 2524, 2938, 2940, 3308, 3310,
        3738, 3740, 3814, 3896, 3899, 3900, 4040]
    assertion_ids = {row["id"] for phase in scenario["phases"]
                     for row in phase["assertions"]}
    assert len(assertion_ids) == 108
    assert {"thud_reset_8_counter_after", "thud_reset_8_master_after",
            "thud_reset_8_heading_after",
            "thud_reset_8_motion_timer_after", "thud_projectile_post_slot_ttl",
            "thud_path_coordinate_middle",
            "thud_path_target_x_middle", "boulder_row_4_threshold_pre",
            "boulder_damage_player_health", "thud_owned_post_action",
            "thud_owned_post_ttl", "thud_owned_post_class",
            "thud_owned_flight_active_gate",
            "thud_owned_retired_active_gate",
            "thud_owned_retired_grain_unchanged"}.issubset(
                assertion_ids)
    assert all("attack" not in item and "berry" not in item
               for item in assertion_ids)

    effect_scenario = ps1_scenario.load_scenario(
        ROOT / "tools/scenarios/duckstation/"
        "pristine_thud_action20_grain_control.yaml")
    assert effect_scenario["playback"]["movie"] == thud.MOVIE_REL
    assert [phase["trigger"]["target"] for phase in
            effect_scenario["phases"]] == [971, 972]
    assert effect_scenario["phases"][0]["after"] == [{
        "type": "rpc", "id": "enlarge_only_thud_action20_radius",
        "method": "debugger.writeU16",
        "params": {"address": 0x800B10F8, "value": 6000},
    }]
    effect_assertion_ids = {
        row["id"] for phase in effect_scenario["phases"]
        for row in phase["assertions"]}
    assert len(effect_assertion_ids) == 16
    assert {"thud_action20_effect_grain_incremented",
            "thud_action20_effect_active_gate",
            "thud_action20_effect_state",
            "thud_action20_effect_health_unchanged"}.issubset(
                effect_assertion_ids)

    suppression_scenario = ps1_scenario.load_scenario(
        ROOT / "tools/scenarios/duckstation/"
        "pristine_thud_action20_source_suppression.yaml")
    assert suppression_scenario["playback"]["movie"] == thud.MOVIE_REL
    assert [phase["trigger"]["target"] for phase in
            suppression_scenario["phases"]] == [969, 970, 979]
    assert suppression_scenario["phases"][0]["after"] == [{
        "type": "rpc", "id": "zero_only_thud_action20_source_countdown",
        "method": "debugger.writeU32",
        "params": {"address": 0x800B4CB4, "value": 0},
    }]
    suppression_assertion_ids = {
        row["id"] for phase in suppression_scenario["phases"]
        for row in phase["assertions"]}
    assert len(suppression_assertion_ids) == 15
    assert {"thud_action20_suppress_post_action",
            "thud_action20_suppress_visual_action_absent",
            "thud_action20_suppress_visual_grain_unchanged"}.issubset(
                suppression_assertion_ids)

    sound_scenario = ps1_scenario.load_scenario(
        ROOT / "tools/scenarios/duckstation/"
        "pristine_thud_action20_sound_call_control.yaml")
    assert sound_scenario["playback"]["movie"] == thud.MOVIE_REL
    assert [phase["trigger"]["target"] for phase in
            sound_scenario["phases"]] == [969, 980]
    assert sound_scenario["phases"][0]["after"] == [
        {
            "type": "rpc", "id": "nop_only_thud_action20_sound_call",
            "method": "debugger.writeU32",
            "params": {"address": 0x800B3FFC, "value": 0},
        },
        {
            "type": "spu_trace_start",
            "id": "thud_action20_sound_spu_trace",
            "params": {"clear": True},
        },
    ]
    sound_assertion_ids = {
        row["id"] for phase in sound_scenario["phases"]
        for row in phase["assertions"]}
    assert len(sound_assertion_ids) == 19
    assert {"thud_sound_nop_action", "thud_sound_nop_ttl",
            "thud_sound_nop_event_total",
            "thud_sound_nop_first_event_frame",
            "thud_sound_nop_first_key_on_frame"}.issubset(sound_assertion_ids)
