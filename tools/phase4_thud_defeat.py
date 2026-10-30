#!/usr/bin/env python3
"""Bind Thud's pristine launches, arena, path, reset and defeat without closure.

The centrally pinned ``thud_boss_movie`` recording reaches the end of the Bug
Bar fight.  Passive ``movie.traceToFrame`` pairs retain cycle-neutral machine
boundaries.  Separate interpreter-only access/exec passes attribute exact
writers; matched one-field controls falsify the input-launch, damage-class,
reset-source, phase-counter, HP-guard, arena-row threshold, path-coordinate and
grain-formula hypotheses.  A natural rolling-boulder overlap binds one six-row
transform/collision branch to player damage; eight reset cycles bind the
counter-8 transition and an exact actor-target path.  The post-restore
continuation also binds one boss-owned action-20 contact-object launch.  Its
natural trajectory misses and retires without collection; a matched one-field
radius control binds its native player-proximity pickup path and grain-counter
effect.  A matched allocation-suppression branch and in-memory framebuffer
diff bind one natural textured-quad presentation to the resident contact-record
billboard renderer without retaining image bytes.  One exact launch-call NOP
also binds the actor-positioned negative sound request to its bounded emulated
SPU key-on sequence while preserving the action-20 object.  Instrumented passes
are never used as timing evidence.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

try:
    import phase4_c16_bonus_death as base
    import phase4_e08_operator_contacts as contacts
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, retained_pristine_save_gaps,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_thud_defeat
    from tools import phase4_c16_bonus_death as base
    from tools import phase4_e08_operator_contacts as contacts
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, retained_pristine_save_gaps,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_thud_defeat.json"
MOVIE_REL = "thud_boss_movie.movie.json"
SAVE_REL = "thud_boss_movie.movie.sav"
MOVIE_SHA256 = "70e5988852315924e7eba7f8ba23632545ad329878e3e5b8a59de91955bcddaa"
SAVE_SHA256 = "789d9b601d592748af934c162513e91f1e63a8d2bbe8ce2cb3b9c16876b32a99"

SCENE = 0x80082504
MASTER_STATE = 0x800823A0
HEALTH = 0x800A6594
LIVES = 0x800A65A0
LIVE_TABLE_0 = 0x80090748
ACTOR = 0x8009FD80
ACTOR_ID = ACTOR
ACTOR_POS_X = ACTOR + 0x04
ACTOR_POS_Y = ACTOR + 0x08
ACTOR_POS_Z = ACTOR + 0x0C
ACTOR_VELOCITY_X = ACTOR + 0x1C
ACTOR_UNKNOWN_20 = ACTOR + 0x20
ACTOR_VELOCITY_Z = ACTOR + 0x24
ACTOR_MOTION_TARGET_X = ACTOR + 0x28
ACTOR_UNKNOWN_30 = ACTOR + 0x30
ACTOR_MOTION_TARGET_Z = ACTOR + 0x34
ACTOR_FLAGS = ACTOR + 0x5C
ACTOR_HP = ACTOR + 0x6E
ACTOR_VM_IP = ACTOR + 0x70
ACTOR_CALLBACK = ACTOR + 0x7C
ACTOR_SOURCE = ACTOR + 0x80

CONTACT_POOL = 0x800B0D18
CONTACT_STRIDE = 0x38
CONTACT_SLOT = 26
CONTACT_RECORD = CONTACT_POOL + CONTACT_SLOT * CONTACT_STRIDE
CONTACT_ACTION = CONTACT_RECORD + 0x20
CONTACT_TTL = CONTACT_RECORD + 0x22
CONTACT_DAMAGE_CLASS = CONTACT_RECORD + 0x34
OVERLAY_TARGET_HP = 0x800B4C70

THUD_ATTACK_CONTACT_SLOT = 17
THUD_ATTACK_CONTACT_RECORD = (
    CONTACT_POOL + THUD_ATTACK_CONTACT_SLOT * CONTACT_STRIDE)
THUD_ATTACK_CONTACT_ACTION = THUD_ATTACK_CONTACT_RECORD + 0x20
THUD_ATTACK_CONTACT_TTL = THUD_ATTACK_CONTACT_RECORD + 0x22
THUD_ATTACK_CONTACT_RADIUS = THUD_ATTACK_CONTACT_RECORD + 0x28
THUD_ATTACK_CONTACT_STATE = THUD_ATTACK_CONTACT_RECORD + 0x2C
THUD_ATTACK_CONTACT_CLASS = THUD_ATTACK_CONTACT_RECORD + 0x34

PLAYER = 0x800A6500
PLAYER_WINDUP = PLAYER + 0x86
PLAYER_IN_FLIGHT = PLAYER + 0x96
PLAYER_SELECTOR = PLAYER + 0x97
DECODED_ACTION = 0x80082488
PREVIOUS_PAD = 0x80082380

THROW_CALL = 0x8004724C
THROW_RETURN = 0x80047254
CONTACT_ALLOCATOR = 0x8005A0E0
ALLOCATOR_ACTION_STORE = 0x8005A1D8
ALLOCATOR_TTL_STORE = 0x8005A1E4
ALLOCATOR_CLASS_STORE = 0x8005A270

DAMAGE_DISPATCH = 0x8005905C
DAMAGE_STORE = 0x800590E4
OVERLAY_CALL = 0x80054A64
OVERLAY_UPDATE = 0x800B3C70
OVERLAY_COMPARE = 0x800B3D3C
OVERLAY_RESTORE = 0x800B3ED0

PHASE_TIMER = 0x800B4C44
# Historical artifacts call this ``arena_position``.  The iteration-22
# intervention narrows the proved meaning to a Thud phase path coordinate.
PHASE_PATH_COORDINATE = 0x800B4CB0
ARENA_POSITION = PHASE_PATH_COORDINATE
GRAIN_PHASE_VALUE = 0x800B4CB4
PHASE_COUNTER = 0x800B4CC8
PHASE_HEADING = 0x800B4CD0
PHASE_MOTION_TIMER = 0x800B4CD8
GRAIN = 0x800A65A1
ARENA_NEGATIVE_SENTINEL = 0xFFFD6E20
ARENA_POSITIVE_SENTINEL = 0x00026E20

ARENA_DAMAGE_PRE_FRAME = 1466
ARENA_DAMAGE_POST_FRAME = 1472
ARENA_TRANSFORM_ROW_COUNT = 6
ARENA_HIT_ROW = 4
ARENA_ROW_PHASE_BASE = 0x800B4C78
ARENA_DISTANCE_THRESHOLD_BASE = 0x800B4C0C
ARENA_HIT_THRESHOLD = ARENA_DISTANCE_THRESHOLD_BASE + ARENA_HIT_ROW * 4
ARENA_HIT_THRESHOLD_VALUE = 490000
ARENA_ROW_LOOP = 0x800B48A4
ARENA_TRANSFORM_CALL = 0x800B49E0
ARENA_CANDIDATE_CALL = 0x800B4A04
ARENA_DISTANCE_COMPARE = 0x800B4A60
ARENA_PLAYER_GATE = 0x800B4A74
ARENA_ROW_STATE_STORE = 0x800B4AA8
ARENA_DAMAGE_CALL = 0x800B4AE0
PLAYER_TRANSITION_ENTRY = 0x8004A700
PLAYER_HEALTH_STORE = 0x8004A888

START_FRAME = 0
PRE_DEFEAT_FRAME = 3896
# movie.traceToFrame's target is the next input index to execute.  These
# post-step assertion boundaries are therefore two indices later than the
# playback_index displayed immediately after the corresponding frame step.
HP_ZERO_FRAME = 3900
RETIRE_FRAME = 3902
SCENE_EXIT_FRAME = 4041
FINAL_FRAME = 4113
MOVIE_FRAMES = 4113

TRANSIENT_PRE_FRAME = 964
TRANSIENT_DAMAGE_FRAME = 965
TRANSIENT_HOLD_FRAME = 966
TRANSIENT_RESET_FRAME = 967

POST_RESTORE_ATTACK_PRE_FRAME = 970
POST_RESTORE_ATTACK_POST_FRAME = 971
POST_RESTORE_ATTACK_ATTRIBUTION_FRAME = 967
POST_RESTORE_ATTACK_ATTRIBUTION_FRAMES = 10
POST_RESTORE_ATTACK_CALL = 0x800B3FF0
POST_RESTORE_ATTACK_RETURN = 0x800B3FF8
POST_RESTORE_SOUND_CALL = 0x800B3FFC
POST_RESTORE_SOUND_RETURN = 0x800B4004
POST_RESTORE_SOUND_WORD = 0x0C014113
PLAY_SOUND_ENTRY = 0x8005044C
SFX_DISPATCH_ENTRY = 0x80050994
ACTION20_SOUND_REQUEST = -14
ACTION20_SOUND_REQUEST_U32 = ACTION20_SOUND_REQUEST & 0xFFFFFFFF
ACTION20_SOUND_SAMPLE_START = "0x00009e10"
ACTION20_SOUND_SHARED_FRAME = 327722
ACTION20_SOUND_KEY_ON_FRAMES = (327715, 327716, 327718, 327720)

ACTION20_EFFECT_PRE_FRAME = 972
ACTION20_EFFECT_POST_FRAME = 973
ACTION20_VISUAL_FRAME = 980
ACTION20_NATURAL_ACTIVE_FRAME = 1021
ACTION20_NATURAL_RETIRE_FRAME = 1023
ACTION20_RADIUS_CONTROL_VALUE = 6000
ACTION20_DISPATCH_ENTRY = 0x8001B5B8
ACTION20_DISPATCH_TARGET = 0x800589B8
ACTION20_HANDLER_ENTRY = 0x80054EAC
ACTION20_GRAIN_STORE = 0x80054F9C
ACTION20_STATE_STORE = 0x800589E0
ACTION20_ACTIVE_STORE = 0x800589E4
ACTION20_BOOKKEEPING_CALL = 0x800589FC
ACTION20_BOOKKEEPING_ENTRY = 0x8005044C
ACTION20_VISUAL_QUERY = (295, 65)
ACTION20_VISUAL_PACKET = 0x801CF3D0
ACTION20_VISUAL_PACKET_LENGTH = 0x40
CONTACT_RENDERER_ADDRESS = 0x80014844
CONTACT_RENDERER_LENGTH = 0x290
CONTACT_RENDERER_SHA256 = (
    "7fa7b409bac944db9fb8a779fe26d9965930b9ca986002f8e849875ff2e36a0e")
CONTACT_RENDERER_END = CONTACT_RENDERER_ADDRESS + CONTACT_RENDERER_LENGTH
CONTACT_RENDERER_READ_PCS = (
    0x800148E0, 0x800148E4, 0x800148F0, 0x800148F4,
    0x800148F8, 0x80014924, 0x8001492C, 0x8001496C,
    0x80014984, 0x800149B0, 0x800149F4,
)
CONTACT_RENDERER_PACKET_PCS = (
    0x80014A30, 0x80014A34, 0x80014A38, 0x80014A3C,
    0x80014A40, 0x80014A44, 0x80014A58, 0x80014A6C,
)

LAUNCH_EDIT_START = 896
LAUNCH_EDIT_END = 918
LAUNCH_PRE_FRAME = 896
LAUNCH_TRACE_FRAME = 913
LAUNCH_POST_FRAME = 915
LAUNCH_DAMAGE_FRAME = 965
LAUNCH_RESTORE_FRAME = 967

TRAJECTORY_START_FRAME = 3741
TRAJECTORY_MID_FRAME = 3815
TRAJECTORY_END_FRAME = 3896
TRAJECTORY_RETIRE_FRAME = 3902
TRAJECTORY_DELTA = 4096
PATH_DECREMENT_STORE = 0x800B43A8
TARGET_X_STORE = 0x800B43B8
TARGET_Z_STORE = 0x800B43BC
MOTION_TIMER_STORE = 0x800B4470
HEADING_STORE = 0x800B44BC
ACTOR_EARLY_X_STORE = 0x8004CD64
ACTOR_EARLY_Z_STORE = 0x8004CDCC
ACTOR_LATE_X_STORE = 0x8004CE08
ACTOR_LATE_Z_STORE = 0x8004CE38
ACTOR_TARGET_X_READER = 0x8004CD6C
ACTOR_TARGET_Z_READER = 0x8004C928

PHASE_RESTORE_FRAMES = (967, 1313, 1713, 2127, 2525, 2941, 3311, 3741)
PHASE_DAMAGE_FRAMES = tuple(frame - 2 for frame in PHASE_RESTORE_FRAMES)

TRACE_RANGES = (
    {"label": "event_vm", "start": "0x8004C13C", "end": "0x8004C31C"},
    {"label": "mover_updater", "start": "0x8004D224", "end": "0x8004D6A0"},
    {"label": "scene_flow", "start": "0x8004FCA0", "end": "0x800502C4"},
    {"label": "overlay_update_call", "start": "0x80054A60", "end": "0x80054A70"},
    {"label": "contact_damage", "start": "0x8005905C", "end": "0x800590E8"},
    {"label": "player_transition", "start": "0x8004A700", "end": "0x8004AA34"},
    {"label": "region_a", "start": "0x800B0000", "end": "0x800C0000"},
)

RUNTIME_OVERLAY_BASE = 0x800B39A0
LEVEL_BIN_SIZE = 3500
LEVEL1_BIN_SIZE = 4064
WRITER_SLICE_ADDRESS = 0x800B4518
WRITER_SLICE_LENGTH = 36
WRITER_SLICE_SHA256 = "971ab8241ab58d147d4dc0b8c2548cda182195982cdcc6b6de84b81014dad177"

EXE_BASE = 0x80010000
EXE_HEADER_SIZE = 0x800
DAMAGE_SLICE_ADDRESS = DAMAGE_DISPATCH
DAMAGE_SLICE_LENGTH = 0x8C
DAMAGE_SLICE_SHA256 = "37267ce05f2791cf2f9f2eaa5c69dcfdd8584242817068c24df540689855c649"
DISPATCHER_ADDRESS = 0x80054964
DISPATCHER_LENGTH = 0x16C
DISPATCHER_SHA256 = "d78a62c9777f3576773287b703d0e4363e607e81f770d1e34c06396edf2622da"
OVERLAY_CALL_SLICE_ADDRESS = 0x80054A60
OVERLAY_CALL_SLICE_LENGTH = 0x10
OVERLAY_CALL_SLICE_SHA256 = "318ad5bc4abd4338da1e51022a432c348fc5db9f10dc2f06bb89c1ce656c226d"
THROW_LAUNCH_SLICE_ADDRESS = 0x80047220
THROW_LAUNCH_SLICE_LENGTH = 0x40
THROW_LAUNCH_SLICE_SHA256 = "8a4903814bb781ef2887db60cf8203f3d35d3b827c2798c5bd7d2fbf47d42732"
CONTACT_ALLOCATOR_SLICE_ADDRESS = CONTACT_ALLOCATOR
CONTACT_ALLOCATOR_SLICE_LENGTH = 0x198
CONTACT_ALLOCATOR_SLICE_SHA256 = "af2839c1c27c4127b4f7d18f31da4869a615b6a7141a9fd088b0710a186e11b1"
PASS2_TRANSFORM_SLICE_ADDRESS = 0x80029508
PASS2_TRANSFORM_SLICE_LENGTH = 0x70
PASS2_TRANSFORM_SLICE_SHA256 = "0ab98c91ed6f02ae6ed0303a47f021a5ad254ea5b13be7d7998e30d6b48bedf2"
COLLISION_CANDIDATE_SLICE_ADDRESS = 0x80037320
COLLISION_CANDIDATE_SLICE_LENGTH = 0x380
COLLISION_CANDIDATE_SLICE_SHA256 = "6ba1df922159d2b9bfcdf36860e667411ff3a8a2afdd769137510775e0e5984a"
PLAYER_TRANSITION_SLICE_ADDRESS = PLAYER_TRANSITION_ENTRY
PLAYER_TRANSITION_SLICE_LENGTH = 0x334
PLAYER_TRANSITION_SLICE_SHA256 = "006837971da56526412ace711aa560d72eef0b9aff8ee0c9087c97303edc1626"
ACTION20_DISPATCH_ENTRY_LENGTH = 4
ACTION20_DISPATCH_ENTRY_SHA256 = "c242b0ea2b3482a29d2095f40e7e1b3ef01db3ec842208e0db7f5dfeeb86563b"
ACTION20_TAIL_SLICE_ADDRESS = ACTION20_DISPATCH_TARGET
ACTION20_TAIL_SLICE_LENGTH = 0x50
ACTION20_TAIL_SLICE_SHA256 = "3801270967aa9a0088252f050c8e5cf1c089ea64a4861b8a68e81f635311e600"
GRAIN_INCREMENT_SLICE_ADDRESS = 0x80054F88
GRAIN_INCREMENT_SLICE_LENGTH = 0x1C
GRAIN_INCREMENT_SLICE_SHA256 = "26aab7214fda929923bfa0176d2fb5c65c52f06ed3d6e95ab8860f1a4a1987cb"
PLAY_SOUND_SLICE_LENGTH = 0x3AC
PLAY_SOUND_SLICE_SHA256 = (
    "ffd93c418662e743429c966f4080065688227dcee6b17aab0ba4b21d383331b1")
RESET_OWNER_LENGTH = 0x264
RESET_OWNER_SHA256 = "6f01004b1528e9c2adac072c8afc9acb695637d0be3d4ffbb78061ed06b33574"
ARENA_BLOCK_ADDRESS = 0x800B4814
ARENA_BLOCK_LENGTH = 0x310
ARENA_BLOCK_SHA256 = "4169c4691a2d31867a9d237d006d91a83b5d3a2d2485c8669f0fed3e3032218d"
POST_RESTORE_CONTINUATION_ADDRESS = 0x800B3ED4
POST_RESTORE_CONTINUATION_LENGTH = 0x134
POST_RESTORE_CONTINUATION_SHA256 = (
    "10992dee6815d74e6b89109980f16d6c60f0230d94f52f0730b7e217d30badba")

RESET_CONTROL_TRANSFERS = {
    "0x800b3ca0": ("bne", "0x800b3cbc"),
    "0x800b3cc8": ("bne", "0x800b3d30"),
    "0x800b3cdc": ("bne", "0x800b3d20"),
    "0x800b3d18": ("j", "0x800b3d30"),
    "0x800b3d50": ("beq", "0x800b3ed4"),
    "0x800b3d58": ("bne", "0x800b3ed4"),
    "0x800b3d88": ("beq", "0x800b3d9c"),
    "0x800b3d94": ("bne", "0x800b3ec4"),
    "0x800b3db4": ("bne", "0x800b3e9c"),
    "0x800b3e40": ("bne", "0x800b3e74"),
    "0x800b3e94": ("j", "0x800b3ec4"),
    "0x800b3eac": ("bne", "0x800b3ebc"),
}

ARENA_CONTROL_TRANSFERS = {
    "0x800b4850": ("bne", "0x800b4870"),
    "0x800b4868": ("j", "0x800b487c"),
    "0x800b487c": ("jal", "0x800292dc"),
    "0x800b488c": ("bne", "0x800b4838"),
    "0x800b48d4": ("beq", "0x800b48e0"),
    "0x800b4924": ("bne", "0x800b4930"),
    "0x800b4964": ("bne", "0x800b4974"),
    "0x800b49e0": ("jal", "0x80029508"),
    "0x800b4a04": ("jal", "0x80037320"),
    "0x800b4a64": ("beq", "0x800b4aac"),
    "0x800b4a74": ("bne", "0x800b4aac"),
    "0x800b4ab4": ("bne", "0x800b48a4"),
    "0x800b4ac4": ("bne", "0x800b4ae8"),
    "0x800b4ae0": ("jal", "0x8004a700"),
    "0x800b4ae8": ("jal", "0x800b3aec"),
    "0x800b4b1c": ("jr", None),
}

POST_RESTORE_CONTROL_TRANSFERS = {
    "0x800b3ee4": ("beq", "0x800b3ef8"),
    "0x800b3ef0": ("jal", "0x8004c10c"),
    "0x800b3f04": ("blez", "0x800b4004"),
    "0x800b3f18": ("beq", "0x800b4004"),
    "0x800b3f2c": ("bne", "0x800b3f7c"),
    "0x800b3f74": ("j", "0x800b3ff0"),
    "0x800b3ff0": ("jal", "0x8005a0e0"),
    "0x800b3ffc": ("jal", "0x8005044c"),
}


def _sha256(path: Path) -> str:
    return base._sha256(path)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exe_slice(exe: bytes, address: int, length: int) -> bytes:
    offset = EXE_HEADER_SIZE + address - EXE_BASE
    data = exe[offset:offset + length]
    if len(data) != length:
        raise SystemExit(f"short pristine EXE slice at 0x{address:08x}")
    return data


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    movie_path = ROOT / MOVIE_REL
    movie_pin = entries.get(MOVIE_REL) or {}
    save = verify_declared_save_fixture(
        ROOT / SAVE_REL, allowed_media_classes={"pristine"})
    movie = json.loads(movie_path.read_text())
    frames = movie.get("frames") or []
    start = movie.get("start_state") or {}
    keys = {
        key for frame in frames for port in (frame.get("ports") or {}).values()
        for key in port
    }
    expected_keys = {
        "circle", "cross", "down", "l1", "l2", "l3", "left", "r1",
        "r2", "r3", "right", "select", "square", "start", "triangle", "up",
    }
    if movie_pin.get("sha256") != MOVIE_SHA256 or \
            movie_pin.get("size") != movie_path.stat().st_size or \
            movie_pin.get("media_class") != "pristine_serial" or \
            _sha256(movie_path) != MOVIE_SHA256 or \
            save.get("sha256") != SAVE_SHA256 or \
            movie.get("format") != "DuckStationInputMovie" or \
            movie.get("version") != 1 or movie.get("game_serial") != "SCUS-94288" or \
            movie.get("initial_frame") != 326743 or len(frames) != MOVIE_FRAMES or \
            start.get("game_serial") != "SCUS-94288" or \
            start.get("from_boot") is not False or \
            start.get("reproducible_only_from_state") is not True or \
            Path(start.get("path", "")).name != Path(SAVE_REL).name or \
            start.get("file_size") != save["size"] or keys != expected_keys:
        raise SystemExit("Thud movie/state pin or metadata drifted")
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "inventory_scope": (
            "Selected after recursively enumerating movies/Phase4 and the broader "
            "operator movie tree; the existing relevant recording was preferred."),
        "movie": {
            "path": MOVIE_REL, "sha256": MOVIE_SHA256,
            "size": movie_pin["size"], "media_class": "pristine_serial",
            "version": 1, "frames": MOVIE_FRAMES, "initial_frame": 326743,
            "recorded_input_scope": "all 16 digital buttons; no analog axes",
        },
        "save": save,
        "classification_boundary": (
            "The filename and JSON serial are leads only. Pre-load save inspection, "
            "mounted pristine CUE/BIN hashes, typed actor state and natural replay "
            "carry the authority claim."),
    }


def build_static_census() -> dict[str, Any]:
    event_vm = json.loads((ROOT / "analysis/phase4_event_vm.json").read_text())
    programs = ((event_vm.get("static_census") or {}).get("vm") or {}).get(
        "programs") or []
    program = next((row for row in programs if row.get("id") == "program_19"), {})
    scene = (json.loads(
        (ROOT / "analysis/phase3_scene_asset_graph.json").read_text()
    ).get("scenes") or {}).get("scene_14") or {}
    pins = json.loads((ROOT / "tools/build_baselines.json").read_text())[
        "staged_inputs"]
    staged = {}
    for rel in ("LEVEL08/LEVEL.BIN", "LEVEL08/LEVEL1.BIN"):
        path = ROOT / "REBUILD/files" / rel
        staged[rel] = {
            "path": path.relative_to(ROOT).as_posix(),
            "size": path.stat().st_size,
            "sha256": _sha256(path),
            "pin": pins[rel],
        }
    exe_path = ROOT / "REBUILD/files/SCUS_942.88"
    exe_pin = pins["SCUS_942.88"]
    exe = exe_path.read_bytes()
    resident_slices = {}
    for label, address, length, expected_sha256 in (
            ("contact_vs_actor_damage_block", DAMAGE_SLICE_ADDRESS,
             DAMAGE_SLICE_LENGTH, DAMAGE_SLICE_SHA256),
            ("contact_dispatcher", DISPATCHER_ADDRESS, DISPATCHER_LENGTH,
             DISPATCHER_SHA256),
            ("overlay_update_call", OVERLAY_CALL_SLICE_ADDRESS,
             OVERLAY_CALL_SLICE_LENGTH, OVERLAY_CALL_SLICE_SHA256),
            ("throw_launch_call", THROW_LAUNCH_SLICE_ADDRESS,
             THROW_LAUNCH_SLICE_LENGTH, THROW_LAUNCH_SLICE_SHA256),
            ("contact_allocator", CONTACT_ALLOCATOR_SLICE_ADDRESS,
             CONTACT_ALLOCATOR_SLICE_LENGTH,
             CONTACT_ALLOCATOR_SLICE_SHA256),
            ("pass2_object_transform_update", PASS2_TRANSFORM_SLICE_ADDRESS,
             PASS2_TRANSFORM_SLICE_LENGTH, PASS2_TRANSFORM_SLICE_SHA256),
            ("collision_candidate_builder", COLLISION_CANDIDATE_SLICE_ADDRESS,
             COLLISION_CANDIDATE_SLICE_LENGTH,
             COLLISION_CANDIDATE_SLICE_SHA256),
            ("resident_level_transition_initiator",
             PLAYER_TRANSITION_SLICE_ADDRESS,
             PLAYER_TRANSITION_SLICE_LENGTH,
             PLAYER_TRANSITION_SLICE_SHA256),
            ("action20_dispatch_entry", ACTION20_DISPATCH_ENTRY,
             ACTION20_DISPATCH_ENTRY_LENGTH,
             ACTION20_DISPATCH_ENTRY_SHA256),
            ("action20_dispatch_and_common_tail", ACTION20_TAIL_SLICE_ADDRESS,
             ACTION20_TAIL_SLICE_LENGTH,
             ACTION20_TAIL_SLICE_SHA256),
            ("grain_increment_writer", GRAIN_INCREMENT_SLICE_ADDRESS,
             GRAIN_INCREMENT_SLICE_LENGTH,
             GRAIN_INCREMENT_SLICE_SHA256),
            ("play_sound", PLAY_SOUND_ENTRY, PLAY_SOUND_SLICE_LENGTH,
             PLAY_SOUND_SLICE_SHA256),
            ("contact_record_billboard_render", CONTACT_RENDERER_ADDRESS,
             CONTACT_RENDERER_LENGTH, CONTACT_RENDERER_SHA256)):
        data = _exe_slice(exe, address, length)
        resident_slices[label] = {
            "address": f"0x{address:08x}", "length": length,
            "sha256": _sha256_bytes(data), "expected_sha256": expected_sha256,
        }
    result = {
        "scene": scene,
        "event_program": program,
        "staged_overlay_candidates": staged,
        "pristine_executable": {
            "path": "REBUILD/files/SCUS_942.88", "size": len(exe),
            "sha256": _sha256_bytes(exe), "pin": exe_pin,
            "load_base": f"0x{EXE_BASE:08x}",
            "header_size": EXE_HEADER_SIZE,
            "resident_slices": resident_slices,
            "decisive_words": {
                "damage_dispatch": "0x8642006e",
                "damage_class_load": "0x9223002c",
                "class_zero_branch": "0x1060000c",
                "minus_two_branch": "0x08016439",
                "minus_two_value": "0x2482fffe",
                "damage_store": "0xa642006e",
                "overlay_call": "0x0c02cf1c",
                "overlay_call_delay": "0x00000000",
                "throw_spawn_call": "0x0c016838",
                "throw_return_sfx_argument": "0x24040002",
                "allocator_action_store": "0xa6020020",
                "arena_transform_call": "0x0c00a542",
                "arena_candidate_call": "0x0c00dcc8",
                "arena_distance_gate": "0x10400011",
                "arena_player_gate": "0x1440000d",
                "arena_damage_call": "0x0c0129c0",
                "action20_dispatch_target": "0x800589b8",
                "action20_handler_call": "0x0c0153ab",
                "action20_state_value": "0x24100010",
                "grain_increment_store": "0xa0430000",
                "action20_state_store": "0xa650000a",
                "action20_active_store": "0xa6570000",
                "action20_bookkeeping_call": "0x0c014113",
                "action20_launch_sound_call": "0x0c014113",
                "renderer_active_gate_load": "0x93080022",
                "renderer_action_load": "0x970a0020",
                "renderer_packet_command_store": "0xaeea000c",
            },
        },
        "runtime_identity_rule": (
            "Region-A addresses are scene/save-owned. Exact runtime bytes must be "
            "captured and may not be labeled LEVEL08/LEVEL*.BIN unless hashes match."),
    }
    expected_scene = {
        "scene_id": 14, "asset_entry": "level08\\level5b", "disc_dir": "level08",
        "asset_prefix": "level5b", "loading_screen": "gfx\\level5b.raw",
        "overlays": {"LEVEL08_LEVEL": 6, "LEVEL08_LEVEL1": 6},
        "phase2_stage_labels": ["stage09_bug_bar"],
    }
    expected_program = {
        "entry": "0x80077798", "end": "0x800777ac", "id": "program_19",
        "selectors": [19], "instruction_count": 5,
        "behavior_signature": ["set_byte_params", "anim_clip_load",
                               "park_arrive_stop", "jump_back", "park_end"],
        "decode_complete": True,
    }
    if scene != expected_scene or any(program.get(key) != value
                                       for key, value in expected_program.items()):
        raise SystemExit(f"Thud scene/program routing drifted: {result}")
    jump = next((row for row in program.get("instructions") or []
                 if row.get("ip") == "0x800777a6"), {})
    if jump != {"ip": "0x800777a6", "raw": "0xffff", "idx": 0,
                "op": "jump_back", "conf": "CONFIRMED", "operands": [1],
                "target": "0x800777a4"}:
        raise SystemExit(f"Thud E07 decoded instruction drifted: {jump}")
    for rel, row in staged.items():
        if row["size"] != row["pin"]["size"] or \
                row["sha256"] != row["pin"]["sha256"]:
            raise SystemExit(f"staged pristine input pin drifted: {rel}")
    if len(exe) != exe_pin["size"] or _sha256_bytes(exe) != exe_pin["sha256"]:
        raise SystemExit("pristine executable pin drifted")
    if any(row["sha256"] != row["expected_sha256"]
           for row in resident_slices.values()):
        raise SystemExit(f"Thud resident slice drifted: {resident_slices}")
    return result


def _read_int(client: Any, address: int, fmt: str) -> int:
    return struct.unpack("<" + fmt, base._read_memory(
        client, address, struct.calcsize(fmt)))[0]


def _contact_snapshot(client: Any, slot: int) -> dict[str, Any]:
    record = CONTACT_POOL + slot * CONTACT_STRIDE
    data = base._read_memory(client, record, CONTACT_STRIDE)
    # Keep the original three typed reads as independent coherence checks.  The
    # control suite was recorded with this RPC cadence; changing it can move an
    # advanceFrames pause boundary by one CPU cycle even though guest RAM is
    # identical.  New typed fields are decoded from the already captured record.
    action_id = _read_int(client, record + 0x20, "B")
    lifetime_ttl = _read_int(client, record + 0x22, "H")
    damage_class = _read_int(client, record + 0x34, "B")
    if action_id != struct.unpack_from("<H", data, 0x20)[0] or \
            lifetime_ttl != struct.unpack_from("<H", data, 0x22)[0] or \
            damage_class != data[0x34]:
        raise SystemExit(f"incoherent contact snapshot for slot {slot}")
    return {
        "pool": f"0x{CONTACT_POOL:08x}", "slot": slot,
        "record": f"0x{record:08x}",
        "record_hex": data.hex(),
        "position": list(struct.unpack_from("<iii", data, 0x00)),
        "velocity": list(struct.unpack_from("<iii", data, 0x0C)),
        "gravity": struct.unpack_from("<h", data, 0x18)[0],
        "action_id": action_id,
        "lifetime_ttl": lifetime_ttl,
        "secondary_lifetime": struct.unpack_from("<H", data, 0x26)[0],
        "radius_add": struct.unpack_from("<h", data, 0x28)[0],
        "state": struct.unpack_from("<h", data, 0x2C)[0],
        "flags": data[0x33],
        "damage_class": damage_class,
        "classification_bytes": list(data[0x34:0x37]),
    }


def _snapshot(client: Any, *, include_full_ram: bool = False) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    movie = client.call("movie.status", {})
    result = {
        "emulator_frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"), "sp": status.get("sp"),
        "movie_frame": movie.get("playback_index"),
        "movie_reproducible": movie.get("reproducible"),
        "movie_truncated": movie.get("truncated"),
        "scene": _read_int(client, SCENE, "I"),
        "master_state": _read_int(client, MASTER_STATE, "H"),
        "health": _read_int(client, HEALTH, "h"),
        "lives": _read_int(client, LIVES, "B"),
        "live_table_0": f"0x{_read_int(client, LIVE_TABLE_0, 'I'):08x}",
        "actor": {
            "address": f"0x{ACTOR:08x}",
            "id": _read_int(client, ACTOR_ID, "I"),
            "position": [_read_int(client, address, "i") for address in
                         (ACTOR_POS_X, ACTOR_POS_Y, ACTOR_POS_Z)],
            "velocity_fields": [_read_int(client, address, "i") for address in
                                (ACTOR_VELOCITY_X, ACTOR_UNKNOWN_20,
                                 ACTOR_VELOCITY_Z)],
            "motion_target_x_unknown_30_z": [
                _read_int(client, address, "i") for address in
                (ACTOR_MOTION_TARGET_X, ACTOR_UNKNOWN_30,
                 ACTOR_MOTION_TARGET_Z)],
            "flags": f"0x{_read_int(client, ACTOR_FLAGS, 'H'):04x}",
            "hp": _read_int(client, ACTOR_HP, "h"),
            "vm_ip": f"0x{_read_int(client, ACTOR_VM_IP, 'I'):08x}",
            "callback": f"0x{_read_int(client, ACTOR_CALLBACK, 'I'):08x}",
            "source": f"0x{_read_int(client, ACTOR_SOURCE, 'I'):08x}",
        },
        "contact": _contact_snapshot(client, CONTACT_SLOT),
        "thud_attack_contact": _contact_snapshot(
            client, THUD_ATTACK_CONTACT_SLOT),
        "player": {
            "position": [_read_int(client, PLAYER + offset, "i")
                         for offset in (0, 4, 8)],
            "throw_windup": _read_int(client, PLAYER_WINDUP, "H"),
            "in_flight_count": _read_int(client, PLAYER_IN_FLIGHT, "B"),
            "equipped_selector": _read_int(client, PLAYER_SELECTOR, "B"),
            "decoded_action": _read_int(client, DECODED_ACTION, "H"),
            "previous_pad": _read_int(client, PREVIOUS_PAD, "H"),
        },
        "overlay_target_hp": _read_int(client, OVERLAY_TARGET_HP, "I"),
        "phase_reset": {
            "timer": _read_int(client, PHASE_TIMER, "I"),
            "arena_position": _read_int(client, ARENA_POSITION, "I"),
            "grain_derived_value": _read_int(
                client, GRAIN_PHASE_VALUE, "I"),
            "counter": _read_int(client, PHASE_COUNTER, "I"),
            "heading": _read_int(client, PHASE_HEADING, "I"),
            "motion_timer": _read_int(client, PHASE_MOTION_TIMER, "I"),
            "grain": _read_int(client, GRAIN, "B"),
        },
    }
    if include_full_ram:
        result["main_ram_sha256"] = _sha256_bytes(base._main_ram(client))
        result["registers_sha256"] = base._register_sha256(client)
    return result


def _trace_boundary(client: Any, movie_path: Path, frame: int) -> dict[str, Any]:
    trace = contacts._compact_trace(client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": frame,
        "ranges": list(TRACE_RANGES)}, timeout=900))
    if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in trace.get("coverage") or []):
        raise SystemExit(f"Thud trace was not cycle-neutral at frame {frame}")
    snapshot = _snapshot(client)
    if snapshot["movie_reproducible"] is not True or \
            snapshot["movie_truncated"] is not False:
        raise SystemExit(f"Thud movie lost reproducibility at frame {frame}")
    return {"target_movie_frame": frame, "snapshot": snapshot,
            "cycle_neutral_trace": trace}


def _post_restore_attack_boundary(
        client: Any, movie_path: Path, frame: int) -> dict[str, Any]:
    ranges = (
        {"label": "post_restore_continuation",
         "start": f"0x{POST_RESTORE_CONTINUATION_ADDRESS:08X}",
         "end": f"0x{POST_RESTORE_CONTINUATION_ADDRESS + POST_RESTORE_CONTINUATION_LENGTH - 4:08X}"},
        {"label": "contact_allocator",
         "start": f"0x{CONTACT_ALLOCATOR:08X}",
         "end": f"0x{CONTACT_ALLOCATOR + CONTACT_ALLOCATOR_SLICE_LENGTH - 4:08X}"},
    )
    raw = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": frame,
        "ranges": list(ranges)}, timeout=900)
    trace = contacts._compact_trace(raw)
    decisive_pcs = {
        f"0x{POST_RESTORE_ATTACK_CALL:08x}",
        f"0x{CONTACT_ALLOCATOR:08x}",
    }
    for raw_row, retained_row in zip(raw.get("coverage") or [],
                                     trace.get("coverage") or []):
        counts = (raw_row.get("coverage") or {}).get("counts_by_pc") or []
        retained_row["decisive_counts_by_pc"] = [
            {"pc": str(row.get("pc", "")).lower(),
             "count": row.get("count")}
            for row in counts
            if str(row.get("pc", "")).lower() in decisive_pcs
        ]
    if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in trace.get("coverage") or []):
        raise SystemExit(
            f"Thud post-restore trace was not cycle-neutral at frame {frame}")
    snapshot = _snapshot(client)
    if snapshot["movie_reproducible"] is not True or \
            snapshot["movie_truncated"] is not False:
        raise SystemExit(
            f"Thud post-restore movie lost reproducibility at frame {frame}")
    return {"target_movie_frame": frame, "snapshot": snapshot,
            "cycle_neutral_trace": trace}


def _validate_natural_phase_cycles(cycles: list[dict[str, Any]]) -> None:
    if len(cycles) != 8:
        raise SystemExit(f"Thud natural phase-cycle count drifted: {len(cycles)}")
    restore_grains = (0, 0, 0, 4, 8, 12, 14, 14)
    negative_restore = (ARENA_NEGATIVE_SENTINEL + 2560) & 0xFFFFFFFF
    positive_restore = ARENA_POSITIVE_SENTINEL - 2560
    for index, row in enumerate(cycles, 1):
        damage = (row["damage"]["snapshot"] or {})
        restore = (row["restore"]["snapshot"] or {})
        damage_phase = damage.get("phase_reset") or {}
        restore_phase = restore.get("phase_reset") or {}
        sentinel = (ARENA_NEGATIVE_SENTINEL if index % 2 == 1
                    else ARENA_POSITIVE_SENTINEL)
        moved_sentinel = negative_restore if index % 2 == 1 else positive_restore
        damage_observed = (
            damage.get("actor", {}).get("hp"), damage.get("overlay_target_hp"),
            damage_phase.get("counter"), damage_phase.get("arena_position"),
            damage_phase.get("grain_derived_value"), damage.get("master_state"),
        )
        restore_observed = (
            restore.get("actor", {}).get("hp"), restore.get("overlay_target_hp"),
            restore_phase.get("counter"), restore_phase.get("arena_position"),
            restore_phase.get("grain_derived_value"),
            restore_phase.get("grain"), restore.get("master_state"),
            restore_phase.get("heading"), restore_phase.get("motion_timer"),
        )
        expected_damage = (48, 50, index - 1, sentinel, 0, 0)
        expected_restore = (
            50, 50, index, moved_sentinel, 0 if index == 8 else 9,
            restore_grains[index - 1], 1 if index == 8 else 0,
            32 if index == 8 else 0, 149 if index == 8 else 0,
        )
        if damage_observed != expected_damage:
            raise SystemExit(
                f"Thud natural phase damage {index} drifted: {damage_observed}")
        if restore_observed != expected_restore:
            raise SystemExit(
                f"Thud natural phase restore {index} drifted: {restore_observed}")


def _natural_phase_cycles(
        client: Any, movie_path: Path,
        transient_boundaries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cycles = []
    for index, (damage_frame, restore_frame) in enumerate(
            zip(PHASE_DAMAGE_FRAMES, PHASE_RESTORE_FRAMES), 1):
        damage = transient_boundaries.get(str(damage_frame)) or \
            _trace_boundary(client, movie_path, damage_frame)
        restore = transient_boundaries.get(str(restore_frame)) or \
            _trace_boundary(client, movie_path, restore_frame)
        cycles.append({
            "cycle": index, "damage_target_movie_frame": damage_frame,
            "restore_target_movie_frame": restore_frame,
            "damage": damage, "restore": restore,
        })
    _validate_natural_phase_cycles(cycles)
    return cycles


def _runtime_overlay_identity(client: Any) -> dict[str, Any]:
    level = base._read_memory(client, RUNTIME_OVERLAY_BASE, LEVEL_BIN_SIZE)
    level1 = base._read_memory(client, RUNTIME_OVERLAY_BASE, LEVEL1_BIN_SIZE)
    writer = base._read_memory(client, WRITER_SLICE_ADDRESS, WRITER_SLICE_LENGTH)
    reset_owner = base._read_memory(client, OVERLAY_UPDATE, RESET_OWNER_LENGTH)
    arena_block = base._read_memory(
        client, ARENA_BLOCK_ADDRESS, ARENA_BLOCK_LENGTH)
    post_restore = base._read_memory(
        client, POST_RESTORE_CONTINUATION_ADDRESS,
        POST_RESTORE_CONTINUATION_LENGTH)
    disassembly = client.call("debugger.disassemble", {
        "address": f"0x{OVERLAY_UPDATE:08X}",
        "count": RESET_OWNER_LENGTH // 4,
    })
    instructions = [{key: row.get(key) for key in (
        "address", "bytes", "mnemonic", "operands", "text", "branch_target")}
        for row in disassembly.get("instructions") or []]
    reconstructed = b"".join(
        struct.pack("<I", int(row["bytes"], 16)) for row in instructions)
    control_transfers = {
        row["address"]: {
            "mnemonic": row["mnemonic"], "target": row["branch_target"],
            "text": row["text"], "bytes": row["bytes"],
        }
        for row in instructions
        if row["address"] in RESET_CONTROL_TRANSFERS
    }
    arena_disassembly = client.call("debugger.disassemble", {
        "address": f"0x{ARENA_BLOCK_ADDRESS:08X}",
        "count": ARENA_BLOCK_LENGTH // 4,
    })
    arena_instructions = [{key: row.get(key) for key in (
        "address", "bytes", "mnemonic", "operands", "text", "branch_target")}
        for row in arena_disassembly.get("instructions") or []]
    arena_reconstructed = b"".join(
        struct.pack("<I", int(row["bytes"], 16))
        for row in arena_instructions)
    arena_transfers = {
        row["address"]: {
            "mnemonic": row["mnemonic"], "target": row["branch_target"],
            "text": row["text"], "bytes": row["bytes"],
        }
        for row in arena_instructions
        if row["address"] in ARENA_CONTROL_TRANSFERS
    }
    post_restore_disassembly = client.call("debugger.disassemble", {
        "address": f"0x{POST_RESTORE_CONTINUATION_ADDRESS:08X}",
        "count": POST_RESTORE_CONTINUATION_LENGTH // 4,
    })
    post_restore_instructions = [{key: row.get(key) for key in (
        "address", "bytes", "mnemonic", "operands", "text", "branch_target")}
        for row in post_restore_disassembly.get("instructions") or []]
    post_restore_reconstructed = b"".join(
        struct.pack("<I", int(row["bytes"], 16))
        for row in post_restore_instructions)
    post_restore_transfers = {
        row["address"]: {
            "mnemonic": row["mnemonic"], "target": row["branch_target"],
            "text": row["text"], "bytes": row["bytes"],
        }
        for row in post_restore_instructions
        if row["address"] in POST_RESTORE_CONTROL_TRANSFERS
    }
    staged_level = ROOT / "REBUILD/files/LEVEL08/LEVEL.BIN"
    staged_level1 = ROOT / "REBUILD/files/LEVEL08/LEVEL1.BIN"
    result = {
        "runtime_region_a": {
            "base": f"0x{RUNTIME_OVERLAY_BASE:08x}",
            "length_3500_sha256": _sha256_bytes(level),
            "length_4064_sha256": _sha256_bytes(level1),
        },
        "staged_candidates": {
            "LEVEL08/LEVEL.BIN": _sha256(staged_level),
            "LEVEL08/LEVEL1.BIN": _sha256(staged_level1),
        },
        "exact_writer_slice": {
            "address": f"0x{WRITER_SLICE_ADDRESS:08x}",
            "length": WRITER_SLICE_LENGTH, "sha256": _sha256_bytes(writer),
            "bytes_hex": writer.hex(),
        },
        "reset_owner_slice": {
            "address": f"0x{OVERLAY_UPDATE:08x}",
            "length": RESET_OWNER_LENGTH, "sha256": _sha256_bytes(reset_owner),
            "expected_sha256": RESET_OWNER_SHA256,
            "instruction_count": len(instructions),
            "disassembly_validation": {
                "method": "debugger.disassemble",
                "first_address": (instructions[0]["address"]
                                  if instructions else None),
                "last_address": (instructions[-1]["address"]
                                 if instructions else None),
                "packed_little_endian_sha256": _sha256_bytes(reconstructed),
                "exact_runtime_bytes_reconstructed": reconstructed == reset_owner,
                "retention_boundary": (
                    "The full original-game instruction capture is validated "
                    "in memory but not retained; only decisive transfers and "
                    "hash metadata are committed."),
            },
            "control_transfers": control_transfers,
        },
        "post_restore_attack_slice": {
            "address": f"0x{POST_RESTORE_CONTINUATION_ADDRESS:08x}",
            "length": POST_RESTORE_CONTINUATION_LENGTH,
            "sha256": _sha256_bytes(post_restore),
            "expected_sha256": POST_RESTORE_CONTINUATION_SHA256,
            "instruction_count": len(post_restore_instructions),
            "disassembly_validation": {
                "method": "debugger.disassemble",
                "first_address": (post_restore_instructions[0]["address"]
                                  if post_restore_instructions else None),
                "last_address": (post_restore_instructions[-1]["address"]
                                 if post_restore_instructions else None),
                "packed_little_endian_sha256": _sha256_bytes(
                    post_restore_reconstructed),
                "exact_runtime_bytes_reconstructed": (
                    post_restore_reconstructed == post_restore),
                "retention_boundary": (
                    "The full original-game continuation is validated in "
                    "memory but not retained; only exact hash metadata and "
                    "control transfers are committed."),
            },
            "control_transfers": post_restore_transfers,
            "bounded_structure": {
                "actor": f"0x{ACTOR:08x}",
                "derived_countdown": f"0x{GRAIN_PHASE_VALUE:08x}",
                "allocator_call": f"0x{POST_RESTORE_ATTACK_CALL:08x}",
                "allocator_entry": f"0x{CONTACT_ALLOCATOR:08x}",
                "allocator_return": f"0x{POST_RESTORE_ATTACK_RETURN:08x}",
            },
        },
        "arena_transform_collision_slice": {
            "address": f"0x{ARENA_BLOCK_ADDRESS:08x}",
            "length": ARENA_BLOCK_LENGTH,
            "sha256": _sha256_bytes(arena_block),
            "expected_sha256": ARENA_BLOCK_SHA256,
            "instruction_count": len(arena_instructions),
            "disassembly_validation": {
                "method": "debugger.disassemble",
                "first_address": (arena_instructions[0]["address"]
                                  if arena_instructions else None),
                "last_address": (arena_instructions[-1]["address"]
                                 if arena_instructions else None),
                "packed_little_endian_sha256": _sha256_bytes(
                    arena_reconstructed),
                "exact_runtime_bytes_reconstructed": (
                    arena_reconstructed == arena_block),
                "retention_boundary": (
                    "The full save-owned instruction block is validated in "
                    "memory but not retained; only exact hash metadata and "
                    "control transfers are committed."),
            },
            "control_transfers": arena_transfers,
            "bounded_structure": {
                "object_rotation_loop_rows": 10,
                "transform_collision_loop_rows": ARENA_TRANSFORM_ROW_COUNT,
                "transform_call": f"0x{ARENA_TRANSFORM_CALL:08x}",
                "candidate_call": f"0x{ARENA_CANDIDATE_CALL:08x}",
                "damage_call": f"0x{ARENA_DAMAGE_CALL:08x}",
            },
        },
        "classification": "save-owned exact runtime Region-A bytes",
    }
    if result["runtime_region_a"]["length_3500_sha256"] == \
            result["staged_candidates"]["LEVEL08/LEVEL.BIN"] or \
            result["runtime_region_a"]["length_4064_sha256"] == \
            result["staged_candidates"]["LEVEL08/LEVEL1.BIN"] or \
            result["exact_writer_slice"]["sha256"] != WRITER_SLICE_SHA256 or \
            result["reset_owner_slice"]["sha256"] != RESET_OWNER_SHA256 or \
            result["post_restore_attack_slice"]["sha256"] != \
            POST_RESTORE_CONTINUATION_SHA256 or \
            result["arena_transform_collision_slice"]["sha256"] != \
            ARENA_BLOCK_SHA256 or \
            len(instructions) != RESET_OWNER_LENGTH // 4 or \
            len(post_restore_instructions) != \
            POST_RESTORE_CONTINUATION_LENGTH // 4 or \
            len(arena_instructions) != ARENA_BLOCK_LENGTH // 4 or \
            reconstructed != reset_owner or \
            post_restore_reconstructed != post_restore or \
            arena_reconstructed != arena_block or \
            {address: (row["mnemonic"], row["target"])
            for address, row in control_transfers.items()} != \
            RESET_CONTROL_TRANSFERS or \
            {address: (row["mnemonic"], row["target"])
             for address, row in post_restore_transfers.items()} != \
            POST_RESTORE_CONTROL_TRANSFERS or \
            {address: (row["mnemonic"], row["target"])
             for address, row in arena_transfers.items()} != \
            ARENA_CONTROL_TRANSFERS:
        raise SystemExit(f"Thud runtime overlay identity drifted: {result}")
    return result


def _start_movie(client: Any, movie_path: Path) -> None:
    base._cleanup(client)
    loaded = client.call("movie.load", {"path": str(movie_path.resolve())})
    started = client.call("movie.startPlayback", {
        "start_frame": 0, "load_start_state": True})
    if loaded.get("frame_count") != MOVIE_FRAMES or \
            started.get("reproducible") is not True or \
            started.get("truncated") is not False:
        raise SystemExit(f"Thud movie did not start reproducibly: {started}")


def _advance_movie_to(client: Any, movie_path: Path, frame: int) -> dict[str, Any]:
    _start_movie(client, movie_path)
    advanced = client.call("movie.advanceToFrame", {
        "frame": frame, "max_frames": frame + 1})
    snapshot = _snapshot(client)
    if snapshot["movie_frame"] != frame - 1 or \
            snapshot["movie_reproducible"] is not True or \
            snapshot["movie_truncated"] is not False:
        raise SystemExit(f"Thud movie boundary {frame} drifted: {snapshot}")
    return advanced


def _launch_writer_attribution(client: Any, movie_path: Path) -> dict[str, Any]:
    """Attribute the naturally recorded slot-26 allocation without timing claims."""
    _advance_movie_to(client, movie_path, LAUNCH_TRACE_FRAME)
    before = _snapshot(client)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    access_spec = {
        "address": f"0x{CONTACT_RECORD:08X}", "length": CONTACT_STRIDE,
        "type": "write", "label": "slot_26_allocation", "max_events": 256,
    }
    access_watch = client.call("accessLog.addWatch", access_spec)
    exec_watch = client.call("execTrace.addWatch", {
        "pc": f"0x{CONTACT_ALLOCATOR:08X}", "capture": ["ra", "a0", "a1"],
        "label": "contact_allocator_entry", "max_events": 16,
    })
    run = client.call("accessLog.run", {"frames": 8})
    page = client.call("accessLog.get", {"offset": 0, "limit": 1024})
    execution = client.call("execTrace.get", {
        "watch_id": exec_watch["watch_id"], "offset": 0, "limit": 16})
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    events = page.get("events") or []

    def event_at(address: int, pc: int) -> dict[str, Any] | None:
        return next((row for row in events
                     if str(row.get("address", "")).lower() ==
                     f"0x{address:08x}" and
                     str(row.get("instruction_pc", "")).lower() ==
                     f"0x{pc:08x}"), None)

    action = event_at(CONTACT_ACTION, ALLOCATOR_ACTION_STORE)
    ttl = event_at(CONTACT_TTL, ALLOCATOR_TTL_STORE)
    damage_class = event_at(CONTACT_DAMAGE_CLASS, ALLOCATOR_CLASS_STORE)
    exec_events = execution.get("events") or []
    allocator_regs = _registers(exec_events[0]) if exec_events else {}
    if (before["contact"]["action_id"], before["player"]["throw_windup"],
            before["player"]["in_flight_count"]) != (4, 10, 2):
        raise SystemExit(f"Thud pre-launch boundary drifted: {before}")
    if (str((action or {}).get("instruction_word", "")).lower(),
            (action or {}).get("value"), (action or {}).get("new_value")) != \
            ("0xa6020020", 4, 2) or \
            (ttl or {}).get("new_value") != 100 or \
            (damage_class or {}).get("new_value") != 0 or \
            allocator_regs.get("ra") != THROW_RETURN:
        raise SystemExit(
            f"Thud natural launch allocation drifted: "
            f"{action} {ttl} {damage_class} {allocator_regs}")
    if page.get("truncated") is not False or page.get("total") != len(events) or \
            execution.get("truncated") is not False or \
            execution.get("total") != len(exec_events) or len(exec_events) != 1:
        raise SystemExit("Thud launch attribution accounting incomplete")
    return {
        "execution_mode_boundary": (
            "accessLog/execTrace force the interpreter. The exact allocation "
            "and caller are source attribution only; passive and matched movie "
            "branches carry behavior."),
        "start_target_movie_frame": LAUNCH_TRACE_FRAME,
        "frames_run": 8,
        "before": before,
        "access": {
            "specification": access_spec, "watch": access_watch,
            "events": events, "total": page.get("total"),
            "truncated": page.get("truncated"),
        },
        "execution": execution,
        "decisive_writers": {
            "action_id": action, "lifetime_ttl": ttl,
            "damage_class": damage_class,
        },
        "caller": {
            "allocator_entry": f"0x{CONTACT_ALLOCATOR:08x}",
            "return_address": f"0x{allocator_regs['ra']:08x}",
            "jal_instruction": f"0x{THROW_CALL:08x}",
            "classification": "resident player throw dispatcher",
        },
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "selector_boundary": (
            "The allocation and resident caller are exact. This campaign does "
            "not assign a berry color from the sampled selector byte."),
    }


def _post_restore_attack_attribution(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Attribute one Thud-overlay allocation without timing claims."""
    _advance_movie_to(client, movie_path, POST_RESTORE_ATTACK_ATTRIBUTION_FRAME)
    before = _snapshot(client)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    access_spec = {
        "address": f"0x{THUD_ATTACK_CONTACT_RECORD:08X}",
        "length": CONTACT_STRIDE, "type": "write",
        "label": "thud_action_20_contact", "max_events": 256,
    }
    access_watch = client.call("accessLog.addWatch", access_spec)
    call_watch = client.call("execTrace.addWatch", {
        "pc": f"0x{POST_RESTORE_ATTACK_CALL:08X}",
        "capture": ["a0", "a1", "a2", "a3", "s3"],
        "label": "thud_overlay_allocator_call", "max_events": 16,
    })
    allocator_watch = client.call("execTrace.addWatch", {
        "pc": f"0x{CONTACT_ALLOCATOR:08X}",
        "capture": ["ra", "a0", "a1", "a2", "a3", "s3"],
        "label": "contact_allocator_entry", "max_events": 16,
    })
    run = client.call("accessLog.run", {
        "frames": POST_RESTORE_ATTACK_ATTRIBUTION_FRAMES})
    access_page = client.call("accessLog.get", {"offset": 0, "limit": 1024})
    call_page = client.call("execTrace.get", {
        "watch_id": call_watch["watch_id"], "offset": 0, "limit": 16})
    allocator_page = client.call("execTrace.get", {
        "watch_id": allocator_watch["watch_id"], "offset": 0, "limit": 16})
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    events = access_page.get("events") or []

    def event_at(address: int, pc: int) -> dict[str, Any] | None:
        return next((row for row in events
                     if str(row.get("address", "")).lower() ==
                     f"0x{address:08x}" and
                     str(row.get("instruction_pc", "")).lower() ==
                     f"0x{pc:08x}"), None)

    action = event_at(THUD_ATTACK_CONTACT_ACTION, ALLOCATOR_ACTION_STORE)
    ttl = event_at(THUD_ATTACK_CONTACT_TTL, ALLOCATOR_TTL_STORE)
    damage_class = event_at(
        THUD_ATTACK_CONTACT_CLASS, ALLOCATOR_CLASS_STORE)
    call_events = call_page.get("events") or []
    allocator_events = allocator_page.get("events") or []
    call_regs = _registers(call_events[0]) if call_events else {}
    allocator_regs = _registers(allocator_events[0]) if allocator_events else {}
    if (str((action or {}).get("instruction_word", "")).lower(),
            (action or {}).get("value"), (action or {}).get("new_value")) != \
            ("0xa6020020", 1, 20) or \
            (ttl or {}).get("new_value") != 200 or \
            (damage_class or {}).get("new_value") != 128 or \
            call_regs.get("s3") != ACTOR or \
            allocator_regs.get("ra") != POST_RESTORE_ATTACK_RETURN or \
            allocator_regs.get("s3") != ACTOR:
        raise SystemExit(
            "Thud post-restore allocation drifted: "
            f"{action} {ttl} {damage_class} {call_regs} {allocator_regs}")
    if access_page.get("truncated") is not False or \
            access_page.get("total") != len(events) or \
            call_page.get("truncated") is not False or \
            call_page.get("total") != len(call_events) or \
            allocator_page.get("truncated") is not False or \
            allocator_page.get("total") != len(allocator_events) or \
            len(call_events) != 1 or len(allocator_events) != 1:
        raise SystemExit("Thud post-restore attribution accounting incomplete")
    return {
        "execution_mode_boundary": (
            "accessLog/execTrace force the interpreter. Exact caller and "
            "allocator writes are source attribution only; passive boundaries "
            "and a separate matched one-field branch carry behavior."),
        "start_target_movie_frame": POST_RESTORE_ATTACK_ATTRIBUTION_FRAME,
        "frames_run": POST_RESTORE_ATTACK_ATTRIBUTION_FRAMES,
        "before": before,
        "access": {
            "specification": access_spec, "watch": access_watch,
            "events": events, "total": access_page.get("total"),
            "truncated": access_page.get("truncated"),
        },
        "execution": {"call": call_page, "allocator": allocator_page},
        "decisive_writers": {
            "action_id": action, "lifetime_ttl": ttl,
            "damage_class": damage_class,
        },
        "caller": {
            "actor": f"0x{call_regs['s3']:08x}",
            "allocator_call": f"0x{POST_RESTORE_ATTACK_CALL:08x}",
            "allocator_entry": f"0x{CONTACT_ALLOCATOR:08x}",
            "return_address": f"0x{allocator_regs['ra']:08x}",
            "classification": "save-owned Thud overlay continuation",
        },
        "allocated_contact": {
            "slot": THUD_ATTACK_CONTACT_SLOT,
            "record": f"0x{THUD_ATTACK_CONTACT_RECORD:08x}",
            "action_id": 20, "lifetime_ttl": 200, "damage_class": 128,
        },
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "effect_boundary": (
            "The caller and action-20 allocation are exact. This evidence does "
            "not alone assign a presentation, hit, damage amount, target, or "
            "completion effect; the separate matched visual control binds one "
            "textured-billboard presentation."),
    }


def _post_restore_attack_control(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Suppress the natural launch by zeroing only its derived countdown."""
    def branch(mutate: bool) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, POST_RESTORE_ATTACK_PRE_FRAME)
        before = _control_snapshot(client)
        write = None
        after_write = None
        if mutate:
            write = client.call("debugger.writeU32", {
                "address": f"0x{GRAIN_PHASE_VALUE:08X}", "value": 0})
            after_write = _control_snapshot(client)
        advance = client.call("movie.advanceToFrame", {
            "frame": POST_RESTORE_ATTACK_POST_FRAME,
            "max_frames": POST_RESTORE_ATTACK_POST_FRAME + 1})
        return {"before": before, "write": write,
                "after_write": after_write, "after": _control_snapshot(client),
                "advance": advance,
                "target_movie_frame": POST_RESTORE_ATTACK_POST_FRAME}

    control = branch(False)
    countdown_zero = branch(True)
    aligned_before = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                      "main_ram_sha256", "registers_sha256")
    if any(control["before"][key] != countdown_zero["before"][key]
           for key in aligned_before) or \
            countdown_zero["after_write"]["main_ram_sha256"] == \
            countdown_zero["before"]["main_ram_sha256"]:
        raise SystemExit("Thud post-restore branches do not share one origin")

    def outcome(row: dict[str, Any]) -> tuple[int, int, int, int]:
        contact = row["thud_attack_contact"]
        return (row["phase_reset"]["grain_derived_value"],
                contact["action_id"], contact["lifetime_ttl"],
                contact["damage_class"])

    before_outcome = outcome(control["before"])
    control_outcome = outcome(control["after"])
    mutation_outcome = outcome(countdown_zero["after"])
    if before_outcome != (9, 1, 0, 0) or \
            control_outcome != (8, 20, 200, 128) or \
            mutation_outcome != (0, 1, 0, 0) or \
            any(control["after"][key] != countdown_zero["after"][key]
                for key in ("emulator_frame", "movie_frame", "pc", "sp")) or \
            countdown_zero["after"]["cycle"] - \
            control["after"]["cycle"] != -1:
        raise SystemExit(
            "Thud post-restore control drifted: "
            f"{before_outcome} {control_outcome} {mutation_outcome}; "
            f"control_endpoint={control['after']}; "
            f"mutation_endpoint={countdown_zero['after']}")
    return {
        "control": control, "countdown_zero": countdown_zero,
        "single_field": f"0x{GRAIN_PHASE_VALUE:08x}",
        "mutation": {"from": 9, "to": 0},
        "observed_outcomes": {
            "before": list(before_outcome),
            "control_after": list(control_outcome),
            "countdown_zero_after": list(mutation_outcome),
        },
        "endpoint_alignment": {
            "emulator_frame_equal": (
                control["after"]["emulator_frame"] ==
                countdown_zero["after"]["emulator_frame"]),
            "movie_frame_equal": (
                control["after"]["movie_frame"] ==
                countdown_zero["after"]["movie_frame"]),
            "mutation_minus_control_cycle": (
                countdown_zero["after"]["cycle"] -
                control["after"]["cycle"]),
            "control_pc": control["after"]["pc"],
            "mutation_pc": countdown_zero["after"]["pc"],
        },
        "control_rule": (
            "Each side reloads target 970 from the same pinned pristine "
            "movie/state with full RAM/register/cycle equality before the one "
            "write. Both advance through movie target 971. The changed branch path "
            "ends one CPU cycle earlier and is intentionally not presented as "
            "equal-cycle timing evidence."),
        "causal_confirmation": (
            "Changing only the derived countdown from 9 to zero prevents the "
            "natural slot-17 action-20/TTL-200/class-128 allocation."),
    }


def _action20_sound_attribution(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Attribute the negative launch cue without using the trace for timing."""
    _advance_movie_to(client, movie_path, POST_RESTORE_ATTACK_ATTRIBUTION_FRAME)
    before = _snapshot(client)
    client.call("execTrace.clear", {})
    watches = {
        "caller": client.call("execTrace.addWatch", {
            "pc": f"0x{POST_RESTORE_SOUND_CALL:08X}",
            "capture": ["a0", "a1", "a2", "a3", "s3", "ra"],
            "label": "thud_action20_launch_sound_call", "max_events": 16,
        }),
        "play_sound": client.call("execTrace.addWatch", {
            "pc": f"0x{PLAY_SOUND_ENTRY:08X}",
            "capture": ["a0", "a1", "a2", "a3", "s3", "ra"],
            "label": "play_sound_entry", "max_events": 16,
        }),
        "positive_dispatch": client.call("execTrace.addWatch", {
            "pc": f"0x{SFX_DISPATCH_ENTRY:08X}",
            "capture": ["a0", "a1", "ra"],
            "label": "positive_sfx_dispatch", "max_events": 64,
        }),
    }
    run = client.call("execTrace.run", {
        "frames": POST_RESTORE_ATTACK_ATTRIBUTION_FRAMES})
    pages = {
        label: client.call("execTrace.get", {
            "watch_id": watch["watch_id"], "offset": 0, "limit": 64})
        for label, watch in watches.items()
    }
    client.call("execTrace.clear", {})

    caller_events = pages["caller"].get("events") or []
    play_events = pages["play_sound"].get("events") or []
    negative_events = [
        event for event in play_events
        if _registers(event).get("a0") == ACTION20_SOUND_REQUEST_U32 and
        _registers(event).get("a1") == ACTOR_POS_X and
        _registers(event).get("ra") == POST_RESTORE_SOUND_RETURN
    ]
    caller_regs = _registers(caller_events[0]) if caller_events else {}
    request_regs = _registers(negative_events[0]) if negative_events else {}
    expected_totals = {"caller": 1, "play_sound": 3,
                       "positive_dispatch": 0}
    if any(page.get("truncated") is not False or
           page.get("total") != len(page.get("events") or []) or
           page.get("total") != expected_totals[label]
           for label, page in pages.items()) or \
            len(caller_events) != 1 or len(negative_events) != 1 or \
            caller_regs.get("a0") != ACTION20_SOUND_REQUEST_U32 or \
            caller_regs.get("s3") != ACTOR or \
            request_regs.get("a0") != ACTION20_SOUND_REQUEST_U32 or \
            request_regs.get("a1") != ACTOR_POS_X or \
            request_regs.get("ra") != POST_RESTORE_SOUND_RETURN:
        raise SystemExit(
            "Thud action-20 sound attribution drifted: "
            f"pages={pages}; caller={caller_regs}; request={request_regs}")
    return {
        "execution_mode_boundary": (
            "execTrace forces the interpreter. This replay attributes the exact "
            "caller and arguments only; the separate matched SPU branch carries "
            "causal behavior and neither branch is used as passive timing proof."),
        "start_target_movie_frame": POST_RESTORE_ATTACK_ATTRIBUTION_FRAME,
        "frames_run": POST_RESTORE_ATTACK_ATTRIBUTION_FRAMES,
        "before": before, "watches": watches, "execution": pages,
        "caller": {
            "instruction_pc": f"0x{POST_RESTORE_SOUND_CALL:08x}",
            "instruction_word": f"0x{POST_RESTORE_SOUND_WORD:08x}",
            "actor": f"0x{caller_regs['s3']:08x}",
            "callee": f"0x{PLAY_SOUND_ENTRY:08x}",
            "return_address": f"0x{POST_RESTORE_SOUND_RETURN:08x}",
            "classification": "save-owned Thud overlay continuation",
        },
        "request": {
            "signed_cue": ACTION20_SOUND_REQUEST,
            "unsigned_a0": f"0x{request_regs['a0']:08x}",
            "position_context": f"0x{request_regs['a1']:08x}",
            "play_sound_entry": f"0x{PLAY_SOUND_ENTRY:08x}",
            "positive_dispatch_hits_in_window": pages[
                "positive_dispatch"].get("total"),
        },
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "bounded_interpretation": (
            "This is one negative play_sound cue with the Thud position pointer. "
            "It is not a positive sfx_dispatch id, named asset, waveform, host-"
            "speaker drain or general E12 audio mapping."),
    }


def _action20_sound_control(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """NOP only the launch sound call and compare bounded SPU event pages."""
    def branch(nop_call: bool) -> dict[str, Any]:
        # State load invalidates instrumentation. Stop/clear before the load and
        # explicitly re-arm only after the exact branch origin is restored.
        client.call("spu.trace.stop", {})
        client.call("spu.trace.clear", {})
        _advance_movie_to(client, movie_path, POST_RESTORE_ATTACK_PRE_FRAME)
        before_ram = base._main_ram(client)
        before = _control_snapshot(client)
        code_before = client.call("debugger.readU32", {
            "address": f"0x{POST_RESTORE_SOUND_CALL:08X}"})
        mutation = None
        after_write = None
        if nop_call:
            write = client.call("debugger.writeU32", {
                "address": f"0x{POST_RESTORE_SOUND_CALL:08X}", "value": 0})
            after_ram = base._main_ram(client)
            differences = [
                {"address": f"0x{0x80000000 + index:08x}",
                 "before": before_ram[index], "after": after_ram[index]}
                for index in range(len(before_ram))
                if before_ram[index] != after_ram[index]
            ]
            after_write = _control_snapshot(client)
            mutation = {
                "method": "debugger.writeU32",
                "address": f"0x{POST_RESTORE_SOUND_CALL:08x}",
                "from": f"0x{POST_RESTORE_SOUND_WORD:08x}", "to": "0x00000000",
                "response": write, "main_ram_differences": differences,
                "main_ram_difference_count": len(differences),
            }
        trace_start = client.call("spu.trace.start", {"clear": True})
        advance = client.call("movie.advanceToFrame", {
            "frame": ACTION20_VISUAL_FRAME,
            "max_frames": ACTION20_VISUAL_FRAME + 1})
        after = _control_snapshot(client)
        code_after = client.call("debugger.readU32", {
            "address": f"0x{POST_RESTORE_SOUND_CALL:08X}"})
        events = client.call("spu.events.get", {"offset": 0, "limit": 1000})
        trace_stop = client.call("spu.trace.stop", {})
        client.call("spu.trace.clear", {})
        return {
            "before": before, "code_before": code_before,
            "mutation": mutation, "after_write": after_write,
            "trace_start": trace_start, "advance": advance, "after": after,
            "code_after": code_after, "spu_events": events,
            "trace_stop": trace_stop,
        }

    natural = branch(False)
    call_nop = branch(True)
    origin_keys = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                   "main_ram_sha256", "registers_sha256")
    if any(natural["before"][key] != call_nop["before"][key]
           for key in origin_keys):
        raise SystemExit("Thud sound branches do not share one machine origin")
    expected_differences = [
        {"address": f"0x{POST_RESTORE_SOUND_CALL + offset:08x}",
         "before": value, "after": 0}
        for offset, value in enumerate((0x13, 0x41, 0x01, 0x0C))
    ]
    mutation = call_nop["mutation"] or {}
    response = mutation.get("response") or {}
    if natural["code_before"].get("value") != POST_RESTORE_SOUND_WORD or \
            natural["code_after"].get("value") != POST_RESTORE_SOUND_WORD or \
            call_nop["code_before"].get("value") != POST_RESTORE_SOUND_WORD or \
            call_nop["code_after"].get("value") != 0 or \
            mutation.get("main_ram_differences") != expected_differences or \
            mutation.get("main_ram_difference_count") != 4 or \
            response.get("written") != 4 or \
            response.get("code_invalidated") is not True:
        raise SystemExit(f"Thud sound NOP was not isolated: {call_nop}")

    contact_keys = (
        "record_hex", "position", "velocity", "gravity", "action_id",
        "lifetime_ttl", "secondary_lifetime", "radius_add", "state",
        "flags", "damage_class", "classification_bytes")
    semantic_keys = ("scene", "master_state", "health", "lives",
                     "live_table_0", "actor", "player", "overlay_target_hp",
                     "phase_reset")
    if any(natural["after"][key] != call_nop["after"][key]
           for key in ("emulator_frame", "movie_frame", "sp")) or \
            (natural["after"]["pc"], call_nop["after"]["pc"]) != \
            ("0x800104b8", "0x800104b8") or \
            call_nop["after"]["cycle"] - natural["after"]["cycle"] != 1 or \
            any(natural["after"][key] != call_nop["after"][key]
                for key in semantic_keys) or \
            any(natural["after"]["thud_attack_contact"][key] !=
                call_nop["after"]["thud_attack_contact"][key]
                for key in contact_keys):
        raise SystemExit(
            "Thud sound endpoints lost semantic alignment: "
            f"natural={natural['after']}; nop={call_nop['after']}")

    natural_events = natural["spu_events"]
    nop_events = call_nop["spu_events"]
    natural_early = [
        event for event in natural_events.get("events") or []
        if event.get("type") == "key_on" and
        event.get("frame", ACTION20_SOUND_SHARED_FRAME) <
        ACTION20_SOUND_SHARED_FRAME
    ]
    nop_early = [
        event for event in nop_events.get("events") or []
        if event.get("type") == "key_on" and
        event.get("frame", ACTION20_SOUND_SHARED_FRAME) <
        ACTION20_SOUND_SHARED_FRAME
    ]
    if natural_events.get("total") != 13 or \
            natural_events.get("truncated") is not False or \
            natural_events.get("total") != len(natural_events.get("events") or []) or \
            nop_events.get("total") != 7 or \
            nop_events.get("truncated") is not False or \
            nop_events.get("total") != len(nop_events.get("events") or []) or \
            [event.get("frame") for event in natural_early] != \
            list(ACTION20_SOUND_KEY_ON_FRAMES) or \
            any(str(event.get("start_address", "")).lower() !=
                ACTION20_SOUND_SAMPLE_START for event in natural_early) or \
            nop_early:
        raise SystemExit(
            "Thud sound SPU event boundary drifted: "
            f"natural={natural_events}; nop={nop_events}")
    return {
        "control_rule": (
            "Both sides reload target 970 from the same pinned pristine state "
            "with full RAM/register/cycle equality. The mutation replaces only "
            "the save-owned jal at 0x800B3FFC with one NOP and invalidates its "
            "code page. SPU tracing is re-armed after each load; both branches "
            "advance to target 980 and preserve the same action-20 record and "
            "gameplay state. The NOP path ends one guest cycle later at the "
            "same separately retained exact PC."),
        "target_movie_frame": ACTION20_VISUAL_FRAME,
        "single_instruction": f"0x{POST_RESTORE_SOUND_CALL:08x}",
        "natural": natural, "call_nop": call_nop,
        "endpoint_alignment": {
            "emulator_frame_equal": True, "movie_frame_equal": True,
            "pc_equal": True, "sp_equal": True,
            "natural_pc": "0x800104b8", "nop_pc": "0x800104b8",
            "nop_minus_natural_cycle": 1,
            "action20_record_equal": True,
            "gameplay_state_equal": True,
        },
        "event_comparison": {
            "natural_total": natural_events.get("total"),
            "call_nop_total": nop_events.get("total"),
            "natural_minus_call_nop": (
                natural_events.get("total") - nop_events.get("total")),
            "shared_event_frame": ACTION20_SOUND_SHARED_FRAME,
            "natural_early_key_ons": natural_early,
            "call_nop_early_key_ons": nop_early,
        },
        "causal_confirmation": (
            "Suppressing only the exact -14 play_sound call removes six bounded "
            "SPU events, including four pre-shared-frame key-ons whose sample "
            "start address is 0x00009E10, without removing or changing the "
            "action-20 launch object."),
        "forbidden_claim": (
            "The emulated key-on sequence does not name an asset, retain audio "
            "bytes, prove a waveform, prove host-speaker drain, bind natural-hit "
            "frequency, or complete the general E12 audio campaign."),
    }


def _action20_geometry(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Recompute the resident walker math from one retained typed snapshot."""
    contact = snapshot["thud_attack_contact"]
    player_x, player_y, player_z = snapshot["player"]["position"]
    record_x, record_y, record_z = contact["position"]
    scaled = [
        ((player_x - record_x) * 0x300) >> 13,
        (((player_y - 0x1CC0) - record_y) * 0x100) >> 13,
        ((player_z - record_z) * 0x300) >> 13,
    ]
    squared_distance = sum(value * value for value in scaled)
    radius = 0x12C + contact["radius_add"]
    return {
        "player_position": [player_x, player_y, player_z],
        "player_y_bias": -0x1CC0,
        "record_position": [record_x, record_y, record_z],
        "scaled_delta": scaled,
        "squared_distance": squared_distance,
        "radius": radius,
        "squared_radius": radius * radius,
        "inside_radius": squared_distance < radius * radius,
        "live_flag_set": bool(contact["flags"] & 2),
    }


def _action20_effect_boundary(
        client: Any, movie_path: Path, frame: int) -> dict[str, Any]:
    ranges = (
        {"label": "resident_contact_walker",
         "start": "0x800586B0", "end": "0x80058AF4"},
        {"label": "resident_grain_handler",
         "start": "0x80054EAC", "end": "0x80055188"},
    )
    raw = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": frame,
        "ranges": list(ranges)}, timeout=900)
    trace = contacts._compact_trace(raw)
    decisive_pcs = {
        f"0x{ACTION20_DISPATCH_TARGET:08x}",
        f"0x{ACTION20_HANDLER_ENTRY:08x}",
        f"0x{ACTION20_GRAIN_STORE:08x}",
        f"0x{ACTION20_STATE_STORE:08x}",
        f"0x{ACTION20_ACTIVE_STORE:08x}",
    }
    for raw_row, retained_row in zip(raw.get("coverage") or [],
                                     trace.get("coverage") or []):
        counts = (raw_row.get("coverage") or {}).get("counts_by_pc") or []
        retained_row["decisive_counts_by_pc"] = [
            {"pc": str(row.get("pc", "")).lower(),
             "count": row.get("count")}
            for row in counts
            if str(row.get("pc", "")).lower() in decisive_pcs
        ]
    if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in trace.get("coverage") or []):
        raise SystemExit(
            f"Thud action-20 trace was not cycle-neutral at frame {frame}")
    snapshot = _snapshot(client)
    if snapshot["movie_reproducible"] is not True or \
            snapshot["movie_truncated"] is not False:
        raise SystemExit(
            f"Thud action-20 movie lost reproducibility at frame {frame}")
    return {
        "target_movie_frame": frame,
        "snapshot": snapshot,
        "walker_geometry": _action20_geometry(snapshot),
        "cycle_neutral_trace": trace,
    }


def _action20_effect_boundaries(
        client: Any, movie_path: Path) -> dict[str, Any]:
    frames = (ACTION20_EFFECT_PRE_FRAME, ACTION20_EFFECT_POST_FRAME,
              ACTION20_NATURAL_ACTIVE_FRAME, ACTION20_NATURAL_RETIRE_FRAME)
    result = {
        str(frame): _action20_effect_boundary(client, movie_path, frame)
        for frame in frames
    }
    expected = {
        ACTION20_EFFECT_PRE_FRAME: (0, 20, 200, 100, 24),
        ACTION20_EFFECT_POST_FRAME: (0, 20, 199, 100, 24),
        ACTION20_NATURAL_ACTIVE_FRAME: (0, 20, 175, 100, 24),
        ACTION20_NATURAL_RETIRE_FRAME: (0, 20, 0, 100, 24),
    }
    for frame, wanted in expected.items():
        snapshot = result[str(frame)]["snapshot"]
        contact = snapshot["thud_attack_contact"]
        observed = (
            snapshot["phase_reset"]["grain"], contact["action_id"],
            contact["lifetime_ttl"], contact["radius_add"], contact["state"])
        pcs = {
            str(pc).lower()
            for row in result[str(frame)]["cycle_neutral_trace"]["coverage"]
            for pc in row.get("pcs") or []
        }
        if observed != wanted or \
                f"0x{ACTION20_HANDLER_ENTRY:08x}" in pcs or \
                f"0x{ACTION20_GRAIN_STORE:08x}" in pcs:
            raise SystemExit(
                f"Thud natural action-20 boundary {frame} drifted: "
                f"{observed} {sorted(pcs)}")
    return result


def _action20_effect_control(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Enlarge only slot 17's signed radius and let the native walker consume it."""
    def branch(mutate: bool) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, ACTION20_EFFECT_PRE_FRAME)
        before_ram = base._main_ram(client)
        before = _control_snapshot(client)
        mutation = None
        after_write = None
        if mutate:
            write = client.call("debugger.writeU16", {
                "address": f"0x{THUD_ATTACK_CONTACT_RADIUS:08X}",
                "value": ACTION20_RADIUS_CONTROL_VALUE})
            after_ram = base._main_ram(client)
            differences = [
                {"address": f"0x{0x80000000 + index:08x}",
                 "before": before_ram[index], "after": after_ram[index]}
                for index in range(len(before_ram))
                if before_ram[index] != after_ram[index]
            ]
            after_write = _control_snapshot(client)
            mutation = {
                "method": "debugger.writeU16",
                "address": f"0x{THUD_ATTACK_CONTACT_RADIUS:08x}",
                "from": 100, "to": ACTION20_RADIUS_CONTROL_VALUE,
                "response": write,
                "main_ram_differences": differences,
                "main_ram_difference_count": len(differences),
            }
        advance = client.call("movie.advanceToFrame", {
            "frame": ACTION20_EFFECT_POST_FRAME - 1,
            "max_frames": ACTION20_EFFECT_POST_FRAME})
        return {
            "before": before,
            "before_geometry": _action20_geometry(before),
            "mutation": mutation,
            "after_write": after_write,
            "after_write_geometry": (
                _action20_geometry(after_write) if after_write else None),
            "after": _control_snapshot(client),
            "advance": advance,
            "target_movie_frame": ACTION20_EFFECT_POST_FRAME - 1,
        }

    control = branch(False)
    radius_enlarged = branch(True)
    aligned = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
               "main_ram_sha256", "registers_sha256")
    if any(control["before"][key] != radius_enlarged["before"][key]
           for key in aligned):
        raise SystemExit("Thud action-20 effect branches do not share one origin")
    expected_differences = [
        {"address": f"0x{THUD_ATTACK_CONTACT_RADIUS:08x}",
         "before": 100, "after": 0x70},
        {"address": f"0x{THUD_ATTACK_CONTACT_RADIUS + 1:08x}",
         "before": 0, "after": 0x17},
    ]
    if radius_enlarged["mutation"]["main_ram_differences"] != \
            expected_differences or \
            radius_enlarged["mutation"]["response"].get("written") != 2 or \
            radius_enlarged["after_write"]["cycle"] != \
            radius_enlarged["before"]["cycle"] or \
            radius_enlarged["after_write"]["registers_sha256"] != \
            radius_enlarged["before"]["registers_sha256"]:
        raise SystemExit(
            f"Thud action-20 radius mutation was not isolated: "
            f"{radius_enlarged['mutation']}")

    def outcome(row: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
        contact = row["thud_attack_contact"]
        return (
            row["phase_reset"]["grain"], row["health"],
            contact["action_id"], contact["lifetime_ttl"],
            contact["radius_add"], contact["state"])

    before_outcome = outcome(control["before"])
    control_outcome = outcome(control["after"])
    mutation_outcome = outcome(radius_enlarged["after"])
    if before_outcome != (0, 4, 20, 200, 100, 24) or \
            control_outcome != (0, 4, 20, 199, 100, 24) or \
            mutation_outcome != (1, 4, 20, 1, 6000, 16) or \
            control["before_geometry"]["inside_radius"] is not False or \
            radius_enlarged["after_write_geometry"]["inside_radius"] is not True or \
            any(control["after"][key] != radius_enlarged["after"][key]
                for key in ("emulator_frame", "movie_frame")):
        raise SystemExit(
            "Thud action-20 radius control drifted: "
            f"{before_outcome} {control_outcome} {mutation_outcome}")
    return {
        "control": control,
        "radius_enlarged": radius_enlarged,
        "single_field": f"0x{THUD_ATTACK_CONTACT_RADIUS:08x}",
        "observed_outcomes": {
            "before": list(before_outcome),
            "control_after": list(control_outcome),
            "radius_enlarged_after": list(mutation_outcome),
        },
        "endpoint_alignment": {
            "emulator_frame_equal": (
                control["after"]["emulator_frame"] ==
                radius_enlarged["after"]["emulator_frame"]),
            "movie_frame_equal": (
                control["after"]["movie_frame"] ==
                radius_enlarged["after"]["movie_frame"]),
            "cycle_equal": (
                radius_enlarged["after"]["cycle"] ==
                control["after"]["cycle"]),
            "mutation_minus_control_cycle": (
                radius_enlarged["after"]["cycle"] -
                control["after"]["cycle"]),
            "control_pc": control["after"]["pc"],
            "mutation_pc": radius_enlarged["after"]["pc"],
        },
        "control_rule": (
            "Each side reloads target 972 from the same centrally pinned "
            "pristine movie/state with full RAM/register/cycle equality. The "
            "only mutation is the two-byte signed radius_add field; both sides "
            "then advance through deterministic movie target 972 and stop at "
            "the same frame and cycle at the same retained exact PC."),
        "causal_confirmation": (
            "Changing only radius_add from 100 to 6000 makes the existing "
            "action-20 record pass the resident player-proximity gate. Native "
            "handling increments grain 0->1, stores record state 16 and sets "
            "the active gate to 1 without changing player health."),
    }


def _compact_object_pick(pick: dict[str, Any]) -> dict[str, Any]:
    """Retain semantic GPU provenance without the raw GP0 payload."""
    draw = pick.get("drawCall") or {}
    return {
        "hit": pick.get("hit"),
        "query": {"x": pick.get("x"), "y": pick.get("y")},
        "frame": pick.get("frame"),
        "pixel": pick.get("pixel"),
        "draw_call": {key: draw.get(key) for key in (
            "gp0Index", "frame", "command", "primitiveType",
            "texturePage", "clut", "semiTransparency", "semiTransparent",
            "commandId", "commandIdHex")},
        "geometry": pick.get("geometry"),
        "texture": pick.get("texture"),
        "draw_mode": pick.get("drawMode"),
        "source": pick.get("source"),
        "retention_boundary": (
            "Raw GP0 words and any framebuffer bytes are not retained; typed "
            "draw geometry, texture metadata and RAM provenance are sufficient."),
    }


def _action20_visual_presentation_control(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Suppress the source allocation and diff one exact natural render frame."""
    client.call("gpu.clearFrameSnapshot", {})

    def branch(suppress: bool) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, POST_RESTORE_ATTACK_PRE_FRAME)
        before_ram = base._main_ram(client)
        before = _control_snapshot(client)
        mutation = None
        after_write = None
        if suppress:
            write = client.call("debugger.writeU32", {
                "address": f"0x{GRAIN_PHASE_VALUE:08X}", "value": 0})
            after_ram = base._main_ram(client)
            differences = [
                {"address": f"0x{0x80000000 + index:08x}",
                 "before": before_ram[index], "after": after_ram[index]}
                for index in range(len(before_ram))
                if before_ram[index] != after_ram[index]
            ]
            after_write = _control_snapshot(client)
            mutation = {
                "method": "debugger.writeU32",
                "address": f"0x{GRAIN_PHASE_VALUE:08x}",
                "from": 9, "to": 0, "response": write,
                "main_ram_differences": differences,
                "main_ram_difference_count": len(differences),
            }
        advance = client.call("movie.advanceToFrame", {
            "frame": ACTION20_VISUAL_FRAME,
            "max_frames": ACTION20_VISUAL_FRAME + 1})
        after = _control_snapshot(client)
        return {
            "before": before, "mutation": mutation,
            "after_write": after_write, "advance": advance, "after": after,
        }

    natural = branch(False)
    reference = client.call("gpu.captureFrameSnapshot", {})
    pick = _compact_object_pick(client.call("gpu.pickObject", {
        "x": ACTION20_VISUAL_QUERY[0], "y": ACTION20_VISUAL_QUERY[1],
        "all_contributors": False}))
    suppressed = branch(True)
    diff = client.call("gpu.diffCurrentFrame", {
        "against": reference["snapshotId"]})
    client.call("gpu.clearFrameSnapshot", {
        "snapshotId": reference["snapshotId"]})

    origin_keys = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                   "main_ram_sha256", "registers_sha256")
    endpoint_keys = ("emulator_frame", "movie_frame", "sp")
    if any(natural["before"][key] != suppressed["before"][key]
           for key in origin_keys):
        raise SystemExit("Thud visual branches do not share one machine origin")
    expected_difference = [{
        "address": f"0x{GRAIN_PHASE_VALUE:08x}", "before": 9, "after": 0}]
    if suppressed["mutation"]["main_ram_differences"] != expected_difference or \
            suppressed["mutation"]["main_ram_difference_count"] != 1 or \
            suppressed["mutation"]["response"].get("written") != 4 or \
            suppressed["after_write"]["cycle"] != \
            suppressed["before"]["cycle"] or \
            suppressed["after_write"]["registers_sha256"] != \
            suppressed["before"]["registers_sha256"]:
        raise SystemExit(
            f"Thud visual suppression mutation was not isolated: "
            f"{suppressed['mutation']}")
    if any(natural["after"][key] != suppressed["after"][key]
           for key in endpoint_keys) or \
            suppressed["after"]["cycle"] - natural["after"]["cycle"] != 0 or \
            (natural["after"]["pc"], suppressed["after"]["pc"]) != \
            ("0x800104b8", "0x80010508") or \
            natural["after"]["thud_attack_contact"]["action_id"] != 20 or \
            suppressed["after"]["thud_attack_contact"]["action_id"] == 20:
        raise SystemExit(
            "Thud visual branches lost exact endpoint alignment: "
            f"natural={natural['after']}; suppressed={suppressed['after']}")

    metrics = diff.get("metrics") or {}
    expected_box = [{"x": 449, "y": 159, "width": 28, "height": 35}]
    if diff.get("changed") is not True or diff.get("pixelCount") != 593 or \
            diff.get("boundingBoxes") != expected_box or \
            diff.get("region") != {
                "x": 0, "y": 0, "width": 800, "height": 610} or \
            metrics.get("changedPixels") != 593 or \
            metrics.get("totalPixels") != 488000 or \
            metrics.get("maxDifference") != 251 or \
            abs(metrics.get("meanAbsoluteDifference", 0.0) -
                0.06294006147540984) > 1e-15 or \
            abs(metrics.get("normalizedScore", 0.0) -
                0.0012151639344262295) > 1e-15:
        raise SystemExit(f"Thud visual frame diff drifted: {diff}")

    draw = pick.get("draw_call") or {}
    texture = pick.get("texture") or {}
    source = pick.get("source") or {}
    geometry = pick.get("geometry") or {}
    if pick.get("hit") is not True or \
            pick.get("query") != {"x": 295, "y": 65} or \
            (pick.get("pixel") or {}).get("rgba") != [107, 156, 0, 255] or \
            draw.get("primitiveType") != "quad" or \
            draw.get("commandId") != 44 or \
            draw.get("frame") != 327721 or \
            geometry.get("screenRect") != {
                "x": 799, "y": 322, "width": 20, "height": 13} or \
            geometry.get("screenVertices") != [
                [799, 322], [818, 322], [799, 334], [818, 334]] or \
            geometry.get("uv") != [
                [240, 112], [255, 112], [240, 127], [255, 127]] or \
            texture.get("textured") is not True or \
            (texture.get("bpp"), texture.get("pageX"), texture.get("pageY"),
             texture.get("clutX"), texture.get("clutY")) != \
            ("4bpp", 512, 0, 880, 221) or \
            (source.get("ramAddress"), source.get("dmaSource"),
             source.get("vertexPointer"), source.get("orderingTableEntry")) != \
            ("0x001cf3d4", "0x001cf3d4", "0x001cf3d8", "0x001cf3d0"):
        raise SystemExit(f"Thud visual object pick drifted: {pick}")

    return {
        "control_rule": (
            "Both sides reload target 970 from the same pinned pristine "
            "movie/state with full RAM/register/cycle equality. The only write "
            "sets the derived countdown 9->0, suppressing the source allocation. "
            "Both sides then stop at the same movie/emulator frame and SP "
            "before an in-memory framebuffer diff. The suppressed path ends on "
            "the same cycle at a separately retained exact PC. No image bytes are "
            "written or retained."),
        "target_movie_frame": ACTION20_VISUAL_FRAME,
        "single_field": f"0x{GRAIN_PHASE_VALUE:08x}",
        "natural": natural, "countdown_zero": suppressed,
        "endpoint_alignment": {
            key + "_equal": natural["after"][key] == suppressed["after"][key]
            for key in endpoint_keys + ("pc",)
        } | {
            "suppressed_minus_natural_cycle": 0,
            "natural_pc": "0x800104b8", "suppressed_pc": "0x80010508",
        },
        "frame_reference": {key: reference.get(key) for key in (
            "width", "height", "frame")},
        "frame_diff": diff,
        "natural_object_pick": pick,
        "causal_confirmation": (
            "Suppressing only the source countdown removes one 593-pixel "
            "28x35 framebuffer region. The natural pixels belong to a textured "
            "quad whose exact DMA source is 0x001CF3D4."),
    }


def _action20_renderer_attribution(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Bind slot 17's typed record to the picked quad's packet writer."""
    _advance_movie_to(client, movie_path, ACTION20_EFFECT_PRE_FRAME)
    before = _snapshot(client)
    client.call("accessLog.clear", {})
    specs = (
        {"address": f"0x{THUD_ATTACK_CONTACT_RECORD:08X}",
         "length": CONTACT_STRIDE, "type": "read",
         "label": "action20_slot17_renderer_reads", "max_events": 4096},
        {"address": f"0x{ACTION20_VISUAL_PACKET:08X}",
         "length": ACTION20_VISUAL_PACKET_LENGTH, "type": "write",
         "label": "action20_picked_packet_writes", "max_events": 4096},
    )
    watches = [client.call("accessLog.addWatch", spec) for spec in specs]
    run = client.call("accessLog.run", {"frames": 8})
    page = client.call("accessLog.get", {"offset": 0, "limit": 4096})
    client.call("accessLog.clear", {})
    events = page.get("events") or []
    read_id, packet_id = (row["watch_id"] for row in watches)
    renderer_reads = [
        row for row in events if row.get("watch_id") == read_id and
        CONTACT_RENDERER_ADDRESS <= int(
            str(row.get("instruction_pc")), 16) < CONTACT_RENDERER_END]
    packet_writes = [row for row in events
                     if row.get("watch_id") == packet_id]
    observed_read_pcs = [
        int(str(row.get("instruction_pc")), 16) for row in renderer_reads]
    expected_read_pcs = list(CONTACT_RENDERER_READ_PCS) * 2
    if sorted(observed_read_pcs) != sorted(expected_read_pcs) or \
            sorted({row.get("frame") for row in renderer_reads}) != \
            [327716, 327722]:
        raise SystemExit(
            f"Thud action-20 renderer read sequence drifted: {renderer_reads}")

    first_packet_map = {
        0x801CF3D4: 0x80014A30, 0x801CF3DC: 0x80014A34,
        0x801CF3E4: 0x80014A38, 0x801CF3EC: 0x80014A3C,
        0x801CF3D0: 0x80014A40, 0x801CF3E8: 0x80014A44,
        0x801CF3D8: 0x80014A58, 0x801CF3E0: 0x80014A6C,
    }
    observed_packet_map = {
        int(str(row.get("address")), 16):
        int(str(row.get("instruction_pc")), 16)
        for row in packet_writes if
        int(str(row.get("address")), 16) in first_packet_map
    }
    watch_rows = {row.get("watch_id"): row
                  for row in page.get("watches") or []}
    if page.get("truncated") is not False or page.get("total") != 118 or \
            page.get("total") != len(events) or \
            (watch_rows.get(read_id) or {}).get("hit_count") != 102 or \
            (watch_rows.get(packet_id) or {}).get("hit_count") != 16 or \
            len(renderer_reads) != 22 or len(packet_writes) != 16 or \
            any(row.get("frame") != 327716 for row in packet_writes) or \
            observed_packet_map != first_packet_map:
        raise SystemExit("Thud action-20 renderer attribution is incomplete")

    action_reads = [row for row in renderer_reads
                    if str(row.get("address", "")).lower() ==
                    f"0x{THUD_ATTACK_CONTACT_ACTION:08x}" and
                    str(row.get("instruction_pc", "")).lower() ==
                    "0x8001496c"]
    if len(action_reads) != 2 or \
            any((row.get("value") or 0) & 0xFFFF != 20
                for row in action_reads):
        raise SystemExit(f"Thud renderer did not read action 20: {action_reads}")

    return {
        "execution_mode_boundary": (
            "accessLog forces the interpreter. These reads and packet writes "
            "attribute source only; the matched cached-interpreter framebuffer "
            "control carries visual behavior and exact timing."),
        "start_target_movie_frame": ACTION20_EFFECT_PRE_FRAME,
        "frames_run": 8,
        "before": before,
        "access": {
            "specifications": list(specs), "watches": watches,
            "total": page.get("total"), "truncated": page.get("truncated"),
            "read_watch_hits": (watch_rows.get(read_id) or {}).get("hit_count"),
            "packet_watch_hits": (
                watch_rows.get(packet_id) or {}).get("hit_count"),
        },
        "renderer": {
            "address": f"0x{CONTACT_RENDERER_ADDRESS:08x}",
            "end_exclusive": f"0x{CONTACT_RENDERER_END:08x}",
            "classification": "resident contact-record billboard renderer",
            "slot17_reads": renderer_reads,
            "read_total": len(renderer_reads),
            "read_frames": sorted({row.get("frame") for row in renderer_reads}),
        },
        "picked_packet": {
            "window": {"address": f"0x{ACTION20_VISUAL_PACKET:08x}",
                       "length": ACTION20_VISUAL_PACKET_LENGTH},
            "writes": packet_writes, "write_total": len(packet_writes),
            "first_packet_address_to_instruction_pc": {
                f"0x{address:08x}": f"0x{pc:08x}"
                for address, pc in first_packet_map.items()},
        },
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "attribution": (
            "The pristine renderer reads slot 17's active gate, flags, XYZ, "
            "sizes, action 20, subtype, mode and command/color word. In the same render "
            "tick it writes the picked quad beginning at exact DMA source "
            "0x001CF3D4 through resident PCs 0x80014A30..0x80014A6C."),
    }


def _action20_effect_attribution(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Attribute the controlled action-20 pickup without timing claims."""
    _advance_movie_to(client, movie_path, ACTION20_EFFECT_PRE_FRAME)
    before = _snapshot(client)
    write = client.call("debugger.writeU16", {
        "address": f"0x{THUD_ATTACK_CONTACT_RADIUS:08X}",
        "value": ACTION20_RADIUS_CONTROL_VALUE})
    after_write = _snapshot(client)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    access_specs = (
        {"address": f"0x{THUD_ATTACK_CONTACT_RECORD:08X}",
         "length": CONTACT_STRIDE, "type": "write",
         "label": "thud_action20_record", "max_events": 512},
        {"address": f"0x{GRAIN:08X}", "length": 1, "type": "write",
         "label": "grain_counter", "max_events": 64},
    )
    access_watches = [client.call("accessLog.addWatch", spec)
                      for spec in access_specs]
    exec_specs = (
        ("action20_dispatch", ACTION20_DISPATCH_TARGET,
         ["ra", "s0", "s1", "s2", "s3"]),
        ("grain_handler_entry", ACTION20_HANDLER_ENTRY,
         ["ra", "s0", "s1", "s2", "s3"]),
        ("grain_increment_store", ACTION20_GRAIN_STORE,
         ["ra", "v0", "v1", "s0", "s1", "s2", "s3"]),
        ("record_state_store", ACTION20_STATE_STORE,
         ["ra", "s0", "s1", "s2", "s3"]),
        ("record_active_store", ACTION20_ACTIVE_STORE,
         ["ra", "s0", "s1", "s2", "s3"]),
        ("bookkeeping_call", ACTION20_BOOKKEEPING_CALL,
         ["ra", "a0", "a1", "s0", "s1", "s2", "s3"]),
        ("bookkeeping_entry", ACTION20_BOOKKEEPING_ENTRY,
         ["ra", "a0", "a1", "s0", "s1", "s2", "s3"]),
    )
    exec_watches = [client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": registers,
        "label": label, "max_events": 16})
        for label, pc, registers in exec_specs]
    run = client.call("accessLog.run", {"frames": 1})
    page = client.call("accessLog.get", {"offset": 0, "limit": 1024})
    execution = {
        label: client.call("execTrace.get", {
            "watch_id": watch["watch_id"], "offset": 0, "limit": 32})
        for (label, _pc, _registers), watch in zip(exec_specs, exec_watches)
    }
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    events = page.get("events") or []

    def event_at(address: int, pc: int) -> dict[str, Any] | None:
        return next((row for row in events
                     if str(row.get("address", "")).lower() ==
                     f"0x{address:08x}" and
                     str(row.get("instruction_pc", "")).lower() ==
                     f"0x{pc:08x}"), None)

    grain = event_at(GRAIN, ACTION20_GRAIN_STORE)
    state = event_at(THUD_ATTACK_CONTACT_STATE, ACTION20_STATE_STORE)
    active = event_at(THUD_ATTACK_CONTACT_TTL, ACTION20_ACTIVE_STORE)
    dispatch_regs = _registers(
        (execution["action20_dispatch"].get("events") or [{}])[0])
    handler_regs = _registers(
        (execution["grain_handler_entry"].get("events") or [{}])[0])
    state_regs = _registers(
        (execution["record_state_store"].get("events") or [{}])[0])
    bookkeeping_events = execution["bookkeeping_entry"].get("events") or []
    bookkeeping = next((row for row in bookkeeping_events
                        if _registers(row).get("a1") ==
                        THUD_ATTACK_CONTACT_RECORD and
                        _registers(row).get("ra") == 0x80058A04), None)
    bookkeeping_regs = _registers(bookkeeping or {})
    after = _snapshot(client)
    if (str((grain or {}).get("instruction_word", "")).lower(),
            (grain or {}).get("value"), (grain or {}).get("new_value")) != \
            ("0xa0430000", 0, 1) or \
            (str((state or {}).get("instruction_word", "")).lower(),
             (state or {}).get("value"), (state or {}).get("new_value")) != \
            ("0xa650000a", 24, 16) or \
            (str((active or {}).get("instruction_word", "")).lower(),
             (active or {}).get("new_value")) != ("0xa6570000", 1) or \
            dispatch_regs.get("s3") != THUD_ATTACK_CONTACT_RECORD or \
            handler_regs.get("ra") != 0x800589C0 or \
            (state_regs.get("s0"), state_regs.get("s1"),
             state_regs.get("s2"), state_regs.get("s3")) != \
            (16, 0xFFFFFFFF, THUD_ATTACK_CONTACT_TTL,
             THUD_ATTACK_CONTACT_RECORD) or \
            (bookkeeping_regs.get("a0"), bookkeeping_regs.get("a1"),
             bookkeeping_regs.get("ra")) != \
            (0xFFFFFFFF, THUD_ATTACK_CONTACT_RECORD, 0x80058A04) or \
            (after["phase_reset"]["grain"],
             after["thud_attack_contact"]["lifetime_ttl"],
             after["thud_attack_contact"]["state"]) != (1, 1, 16):
        raise SystemExit(
            "Thud action-20 effect attribution drifted: "
            f"{grain} {state} {active} {dispatch_regs} {handler_regs} "
            f"{state_regs} {bookkeeping_regs}")
    expected_exec_totals = {
        "action20_dispatch": 1, "grain_handler_entry": 1,
        "grain_increment_store": 1, "record_state_store": 1,
        "record_active_store": 1, "bookkeeping_call": 1,
        "bookkeeping_entry": 3,
    }
    if page.get("truncated") is not False or \
            page.get("total") != len(events) or \
            page.get("total") != 10 or \
            any(execution[label].get("truncated") is not False or
                execution[label].get("total") != total or
                execution[label].get("total") !=
                len(execution[label].get("events") or [])
                for label, total in expected_exec_totals.items()):
        raise SystemExit("Thud action-20 attribution accounting incomplete")
    return {
        "execution_mode_boundary": (
            "accessLog/execTrace force the interpreter. These exact writes and "
            "registers are source/effect attribution only; passive boundaries "
            "and the separate matched branch carry natural and causal behavior."),
        "start_target_movie_frame": ACTION20_EFFECT_PRE_FRAME,
        "frames_run": 1,
        "before": before,
        "radius_write": write,
        "after_write": after_write,
        "access": {
            "specifications": list(access_specs), "watches": access_watches,
            "events": events, "total": page.get("total"),
            "truncated": page.get("truncated"),
        },
        "execution": execution,
        "decisive_writers": {
            "grain_increment": grain,
            "record_state": state,
            "record_active_gate": active,
        },
        "decisive_registers": {
            "dispatch": dispatch_regs,
            "handler_entry": handler_regs,
            "common_tail": state_regs,
            "bookkeeping": bookkeeping_regs,
        },
        "after": after,
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "bounded_effect": (
            "The native action-20 player-proximity path calls resident handler "
            "0x80054EAC, increments grain, records state 16, sets the active "
            "gate to 1 and calls bookkeeping with result -1. This path does not "
            "itself bind presentation; a separate matched control binds one "
            "textured billboard. Sound, damage amount, natural-hit frequency "
            "and completion remain open."),
    }


def _launch_input_counterfactual(client: Any, movie_path: Path) -> dict[str, Any]:
    """Clear only Square across the recorded launch window in registry memory."""
    movie_doc = json.loads(movie_path.read_text())
    registry_ids: list[int] = []

    def play(movie_id: int) -> dict[str, Any]:
        activated = client.call("movie.activate", {"movieId": movie_id})
        started = client.call("movie.startPlayback", {"load_start_state": True})
        points = {}
        for frame in (LAUNCH_PRE_FRAME, LAUNCH_POST_FRAME,
                      LAUNCH_DAMAGE_FRAME, LAUNCH_RESTORE_FRAME):
            client.call("movie.advanceToFrame", {
                "frame": frame, "max_frames": frame + 1}, timeout=900)
            points[str(frame)] = _control_snapshot(client)
        client.call("movie.stopPlayback", {})
        return {"activated": activated, "started": started, "points": points}

    try:
        _start_movie(client, movie_path)
        stored = client.call("movie.store", {})
        registry_ids.append(stored["movieId"])
        natural_branch = client.call("movie.branch", {
            "movieId": stored["movieId"],
            "fromFrame": len(movie_doc["frames"])})
        edited_branch = client.call("movie.branch", {
            "movieId": stored["movieId"],
            "fromFrame": len(movie_doc["frames"])})
        registry_ids.extend(
            [natural_branch["movieId"], edited_branch["movieId"]])
        edits = []
        square_source_frames = []
        for index in range(LAUNCH_EDIT_START, LAUNCH_EDIT_END):
            pad = dict(movie_doc["frames"][index]["ports"]["0"])
            if pad.get("square") is True:
                square_source_frames.append(index)
            pad["square"] = False
            edits.append(client.call("movie.editFrame", {
                "movieId": edited_branch["movieId"], "frame": index,
                "input": {"0": pad}}))
        client.call("movie.stopPlayback", {})
        natural = play(natural_branch["movieId"])
        edited = play(edited_branch["movieId"])
    finally:
        try:
            client.call("movie.stopPlayback", {})
        except Exception:
            pass
        for movie_id in reversed(registry_ids):
            try:
                client.call("movie.remove", {"movieId": movie_id})
            except Exception:
                pass
        try:
            client.call("movie.clear", {})
        except Exception:
            pass

    natural_points = natural["points"]
    edited_points = edited["points"]
    aligned = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
               "main_ram_sha256", "registers_sha256")
    if any(natural_points[str(LAUNCH_PRE_FRAME)][key] !=
           edited_points[str(LAUNCH_PRE_FRAME)][key] for key in aligned):
        raise SystemExit("Thud launch branches differ before the edit window")

    def launch_tuple(row: dict[str, Any]) -> tuple[int, ...]:
        return (row["player"]["throw_windup"],
                row["player"]["in_flight_count"],
                row["contact"]["action_id"],
                row["contact"]["lifetime_ttl"])

    post = {side: list(launch_tuple(points[str(LAUNCH_POST_FRAME)]))
            for side, points in (("natural", natural_points),
                                 ("square_cleared", edited_points))}
    damage = {
        side: [points[str(LAUNCH_DAMAGE_FRAME)]["actor"]["hp"],
               points[str(LAUNCH_DAMAGE_FRAME)]["contact"]["action_id"]]
        for side, points in (("natural", natural_points),
                             ("square_cleared", edited_points))}
    restore = {
        side: [points[str(LAUNCH_RESTORE_FRAME)]["actor"]["hp"],
               points[str(LAUNCH_RESTORE_FRAME)]["phase_reset"]["counter"],
               points[str(LAUNCH_RESTORE_FRAME)]["phase_reset"][
                   "arena_position"]]
        for side, points in (("natural", natural_points),
                             ("square_cleared", edited_points))}
    if launch_tuple(natural_points[str(LAUNCH_PRE_FRAME)])[:2] != (6, 2) or \
            post != {"natural": [9, 3, 2, 99],
                     "square_cleared": [0, 2, 4, 0]} or \
            damage != {"natural": [48, 2], "square_cleared": [50, 4]} or \
            restore != {"natural": [50, 1, 4294801440],
                        "square_cleared": [50, 0, 4294798880]}:
        raise SystemExit(
            f"Thud Square counterfactual drifted: {post} {damage} {restore}")
    if len(edits) != LAUNCH_EDIT_END - LAUNCH_EDIT_START or \
            not square_source_frames or any(
                points[str(frame)]["movie_reproducible"] is not True or
                points[str(frame)]["movie_truncated"] is not False
                for points in (natural_points, edited_points)
                for frame in (LAUNCH_PRE_FRAME, LAUNCH_POST_FRAME,
                              LAUNCH_DAMAGE_FRAME, LAUNCH_RESTORE_FRAME)):
        raise SystemExit("Thud launch counterfactual registry/replay drifted")
    return {
        "source_movie": {"path": MOVIE_REL, "sha256": MOVIE_SHA256},
        "edit_recipe": {
            "field": "ports.0.square", "value": False,
            "start_frame": LAUNCH_EDIT_START,
            "end_frame_exclusive": LAUNCH_EDIT_END,
            "edited_frame_count": len(edits),
            "source_square_frames": square_source_frames,
        },
        "natural": natural, "square_cleared": edited,
        "observed_outcomes": {"post_launch": post, "damage": damage,
                              "restore": restore},
        "control_rule": (
            "Both branches activate in-memory descendants of the same pinned "
            "movie and are full-RAM/register/cycle equal at target 896. Only "
            "Square is cleared for source frames 896..917; no derivative movie "
            "bytes are retained."),
        "falsified_alternative": (
            "The action-2 allocation, subsequent -2 contact and first reset are "
            "not invariant to the recorded Square input window."),
    }


def _registers(event: dict[str, Any]) -> dict[str, int]:
    return {key: int(value, 0) for key, value in (event.get("regs") or {}).items()}


def _signed32(value: int) -> int:
    return value - (1 << 32) if value & 0x80000000 else value


def _arena_damage_attribution(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Attribute one rolling-boulder overlap without using it for timing."""
    _advance_movie_to(client, movie_path, ARENA_DAMAGE_PRE_FRAME)
    before = _snapshot(client)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    access_spec = {
        "address": f"0x{HEALTH:08X}", "length": 2, "type": "write",
        "label": "player_health", "max_events": 64,
    }
    access_watch = client.call("accessLog.addWatch", access_spec)
    exec_specs = (
        ("row_loop", ARENA_ROW_LOOP, ["s2", "s6", "s7", "fp"]),
        ("transform_call", ARENA_TRANSFORM_CALL,
         ["a0", "a1", "a2", "a3", "s2", "s6", "s7", "fp"]),
        ("candidate_call", ARENA_CANDIDATE_CALL,
         ["a0", "a1", "a2", "a3", "s1", "s2", "s4", "s5",
          "s6", "s7", "fp"]),
        ("distance_compare", ARENA_DISTANCE_COMPARE,
         ["v0", "v1", "s1", "s2", "s4", "s5", "s6", "s7", "fp"]),
        ("player_gate", ARENA_PLAYER_GATE,
         ["v0", "v1", "s2", "s6", "s7", "fp"]),
        ("row_state_store", ARENA_ROW_STATE_STORE,
         ["v0", "v1", "s0", "s1", "s2", "s3", "s6", "s7", "fp"]),
        ("damage_call", ARENA_DAMAGE_CALL,
         ["a0", "a1", "a2", "a3", "ra", "s0", "s1", "s2", "s3",
          "s4", "s5", "s6", "s7", "fp", "sp"]),
        ("transition_entry", PLAYER_TRANSITION_ENTRY,
         ["a0", "a1", "a2", "a3", "ra", "s0", "s1", "s2", "s3", "sp"]),
        ("health_store", PLAYER_HEALTH_STORE,
         ["v0", "v1", "a0", "a1", "a2", "a3", "ra", "sp"]),
    )
    exec_watches = [client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": capture, "label": label,
        "max_events": 128}) for label, pc, capture in exec_specs]
    run = client.call("accessLog.run", {"frames": 6})
    access_page = client.call("accessLog.get", {"offset": 0, "limit": 256})
    execution_pages = {
        label: client.call("execTrace.get", {
            "watch_id": watch["watch_id"], "offset": 0, "limit": 128})
        for (label, _pc, _capture), watch in zip(exec_specs, exec_watches)
    }
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    damage_events = execution_pages["damage_call"].get("events") or []
    if len(damage_events) != 1:
        raise SystemExit(f"Thud arena damage-call count drifted: {damage_events}")
    contact_frame = damage_events[0].get("frame")
    execution: dict[str, Any] = {}
    for label, page in execution_pages.items():
        all_events = page.get("events") or []
        execution[label] = {
            "total": page.get("total"), "returned": len(all_events),
            "truncated": page.get("truncated"),
            "contact_frame_events": [row for row in all_events
                                     if row.get("frame") == contact_frame],
        }

    distance_events = execution["distance_compare"]["contact_frame_events"]
    distance_rows = []
    for event in distance_events:
        registers = _registers(event)
        row = registers["s2"]
        distance_rows.append({
            "row": row,
            "phase_address": f"0x{ARENA_ROW_PHASE_BASE + row * 4:08x}",
            "threshold_address": (
                f"0x{ARENA_DISTANCE_THRESHOLD_BASE + row * 4:08x}"),
            "squared_distance": registers["v0"],
            "squared_distance_threshold": registers["v1"],
            "inside_threshold": registers["v0"] < registers["v1"],
            "transformed_position": [_signed32(registers[key]) for key in
                                     ("s1", "s5", "s4")],
        })
    inside = [row for row in distance_rows if row["inside_threshold"]]
    access_events = access_page.get("events") or []
    health_write = next((row for row in access_events
                         if str(row.get("instruction_pc", "")).lower() ==
                         f"0x{PLAYER_HEALTH_STORE:08x}" and
                         row.get("value") == 3 and
                         row.get("new_value") == 2), None)
    transition_events = execution["transition_entry"]["contact_frame_events"]
    transition_registers = (_registers(transition_events[0])
                            if transition_events else {})
    player_gate_events = execution["player_gate"]["contact_frame_events"]
    after = _snapshot(client)
    expected_rows = list(range(ARENA_TRANSFORM_ROW_COUNT))
    row_loop = [_registers(row)["s2"] for row in
                execution["row_loop"]["contact_frame_events"]]
    transform_rows = [_registers(row)["a0"] for row in
                      execution["transform_call"]["contact_frame_events"]]
    candidate_rows = [_registers(row)["s2"] for row in
                      execution["candidate_call"]["contact_frame_events"]]
    if row_loop != expected_rows or transform_rows != expected_rows or \
            candidate_rows != expected_rows or \
            [row["row"] for row in distance_rows] != expected_rows or \
            inside != [{
                "row": ARENA_HIT_ROW,
                "phase_address": f"0x{ARENA_ROW_PHASE_BASE + ARENA_HIT_ROW * 4:08x}",
                "threshold_address": f"0x{ARENA_HIT_THRESHOLD:08x}",
                "squared_distance": 454805,
                "squared_distance_threshold": ARENA_HIT_THRESHOLD_VALUE,
                "inside_threshold": True,
                "transformed_position": [3448, -547, -919],
            }] or \
            len(player_gate_events) != 1 or \
            _registers(player_gate_events[0]).get("s2") != ARENA_HIT_ROW or \
            _registers(player_gate_events[0]).get("v0") != 0 or \
            (transition_registers.get("ra"), transition_registers.get("a3")) != \
            (ARENA_DAMAGE_CALL + 8, 0) or health_write is None or \
            (before["health"], after["health"]) != (3, 2):
        raise SystemExit(
            f"Thud arena row attribution drifted: {row_loop} {transform_rows} "
            f"{candidate_rows} {distance_rows} {player_gate_events} "
            f"{transition_registers} {health_write} {before} {after}")
    if access_page.get("truncated") is not False or \
            access_page.get("total") != len(access_events) or any(
                page["truncated"] is not False or
                page["total"] != page["returned"]
                for page in execution.values()):
        raise SystemExit("Thud arena attribution accounting incomplete")
    return {
        "execution_mode_boundary": (
            "accessLog and execTrace force the interpreter. The six-row call "
            "chain and exact health writer are attribution only; passive "
            "traceToFrame boundaries and a separate matched threshold control "
            "carry behavior and timing."),
        "start_target_movie_frame": ARENA_DAMAGE_PRE_FRAME,
        "frames_run": 6, "contact_emulator_frame": contact_frame,
        "before": before, "after": after,
        "access": {
            "specification": access_spec, "watch": access_watch,
            "events": access_events, "total": access_page.get("total"),
            "truncated": access_page.get("truncated"),
        },
        "execution": execution,
        "distance_rows": distance_rows,
        "hit_row": inside[0],
        "decisive_health_write": health_write,
        "transition_entry_registers": transition_registers,
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "bounded_join": (
            "The save-owned loop transforms six object rows, calls the resident "
            "candidate builder for each, and compares player distance against "
            "a per-row squared threshold. Only row 4 passes; with player +0x92 "
            "zero, 0x800B4AE0 calls the resident level-transition/damage "
            "initiator with a3=0, and 0x8004A888 stores health 3->2."),
    }


def _arena_damage_control(client: Any, movie_path: Path) -> dict[str, Any]:
    """Zero only the winning row's squared-distance threshold."""
    def branch(mutate: bool) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, ARENA_DAMAGE_PRE_FRAME)
        before = _control_snapshot(client)
        threshold_before = _read_int(client, ARENA_HIT_THRESHOLD, "I")
        write = None
        after_write = None
        if mutate:
            write = client.call("debugger.writeU32", {
                "address": f"0x{ARENA_HIT_THRESHOLD:08X}", "value": 0})
            after_write = _control_snapshot(client)
        advance = client.call("movie.advanceToFrame", {
            "frame": ARENA_DAMAGE_POST_FRAME - 1,
            "max_frames": ARENA_DAMAGE_POST_FRAME})
        return {
            "before": before, "threshold_before": threshold_before,
            "write": write, "after_write": after_write,
            "after": _control_snapshot(client),
            "threshold_after": _read_int(client, ARENA_HIT_THRESHOLD, "I"),
            "advance": advance,
            "target_movie_frame": ARENA_DAMAGE_POST_FRAME - 1,
        }

    control = branch(False)
    threshold_zero = branch(True)
    aligned = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
               "main_ram_sha256", "registers_sha256")
    if any(control["before"][key] != threshold_zero["before"][key]
           for key in aligned) or \
            control["threshold_before"] != ARENA_HIT_THRESHOLD_VALUE or \
            threshold_zero["threshold_before"] != ARENA_HIT_THRESHOLD_VALUE or \
            threshold_zero["threshold_after"] != 0 or \
            threshold_zero["after_write"]["main_ram_sha256"] == \
            threshold_zero["before"]["main_ram_sha256"]:
        raise SystemExit("Thud arena threshold branches do not share one origin")
    control_after = control["after"]
    zero_after = threshold_zero["after"]
    if (control["before"]["health"], control_after["health"],
            zero_after["health"]) != (3, 2, 3) or \
            control_after["player"]["position"] != \
            zero_after["player"]["position"] or any(
                control_after[key] != zero_after[key]
                for key in ("emulator_frame", "movie_frame", "pc", "sp")) or \
            zero_after["cycle"] - control_after["cycle"] != 0 or \
            (control_after["pc"], zero_after["pc"]) != \
            ("0x8004fea4", "0x8004fea4"):
        raise SystemExit(
            f"Thud arena threshold outcome drifted: {control_after} {zero_after}")
    return {
        "control": control, "threshold_zero": threshold_zero,
        "single_field": f"0x{ARENA_HIT_THRESHOLD:08x}",
        "row": ARENA_HIT_ROW,
        "mutation": {"from": ARENA_HIT_THRESHOLD_VALUE, "to": 0},
        "observed_health": {
            "before": control["before"]["health"],
            "control_after": control_after["health"],
            "threshold_zero_after": zero_after["health"],
        },
        "endpoint_alignment": {
            "emulator_frame_equal": (
                control_after["emulator_frame"] == zero_after["emulator_frame"]),
            "movie_frame_equal": (
                control_after["movie_frame"] == zero_after["movie_frame"]),
            "pc_equal": control_after["pc"] == zero_after["pc"],
            "sp_equal": control_after["sp"] == zero_after["sp"],
            "cycle_equal": zero_after["cycle"] == control_after["cycle"],
            "threshold_zero_minus_control_cycle": 0,
            "control_pc": "0x8004fea4", "threshold_zero_pc": "0x8004fea4",
        },
        "control_rule": (
            "Each side reloads target 1466 from the same pinned pristine "
            "movie/state. Full RAM, registers, cycle, frame, PC and SP match "
            "before the only write; both sides advance through deterministic "
            "movie target 1471."),
        "causal_confirmation": (
            "Changing only row 4's squared-distance threshold from 490000 to "
            "zero prevents health 3->2 while player position, frame, PC and SP "
            "remain equal; the threshold-zero branch ends on the same cycle."),
    }


def _transient_writer_attribution(client: Any, movie_path: Path) -> dict[str, Any]:
    _advance_movie_to(client, movie_path, TRANSIENT_PRE_FRAME - 1)
    before = _snapshot(client)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    access_specs = (
        {"address": f"0x{ACTOR_HP:08X}", "length": 2, "type": "write",
         "label": "thud_hp", "max_events": 64},
        {"address": f"0x{CONTACT_DAMAGE_CLASS:08X}", "length": 1,
         "type": "read", "label": "contact_damage_class", "max_events": 64},
        {"address": f"0x{OVERLAY_TARGET_HP:08X}", "length": 4,
         "type": "read", "label": "overlay_target_hp", "max_events": 64},
    )
    access_watches = [client.call("accessLog.addWatch", row)
                      for row in access_specs]
    exec_specs = (
        ("damage_dispatch_inner_block", DAMAGE_DISPATCH,
         ["a0", "v0", "v1", "s1", "s2", "ra"]),
        ("damage_store", DAMAGE_STORE,
         ["a0", "v0", "v1", "s1", "s2", "ra"]),
        ("overlay_update_call", OVERLAY_CALL, ["ra"]),
        ("overlay_update_entry", OVERLAY_UPDATE, ["ra", "sp"]),
        ("overlay_hp_compare", OVERLAY_COMPARE, ["v0", "s3"]),
        ("overlay_restore_store", OVERLAY_RESTORE, ["v0", "s3"]),
    )
    exec_watches = [client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": capture, "label": label,
        "max_events": 64}) for label, pc, capture in exec_specs]
    run = client.call("accessLog.run", {"frames": 30})
    page = client.call("accessLog.get", {"offset": 0, "limit": 1024})
    execution = {label: client.call("execTrace.get", {
        "watch_id": watch["watch_id"], "offset": 0, "limit": 64})
        for (label, _pc, _capture), watch in zip(exec_specs, exec_watches)}
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    events = page.get("events") or []
    hp_changes = [row for row in events if str(row.get("address", "")).lower()
                  == f"0x{ACTOR_HP:08x}" and row.get("value") !=
                  row.get("new_value")]
    damage = next((row for row in hp_changes if row.get("value") == 50 and
                   row.get("new_value") == 48), None)
    restore = next((row for row in hp_changes if row.get("value") == 48 and
                    row.get("new_value") == 50), None)
    damage_exec = (execution["damage_store"].get("events") or [{}])[0]
    restore_exec = (execution["overlay_restore_store"].get("events") or [{}])[0]
    target_read_pcs = {str(row.get("instruction_pc", "")).lower()
                       for row in events
                       if str(row.get("address", "")).lower() ==
                       f"0x{OVERLAY_TARGET_HP:08x}"}
    if (str((damage or {}).get("instruction_pc", "")).lower(),
            str((damage or {}).get("instruction_word", "")).lower()) != \
            ("0x800590e4", "0xa642006e") or \
            (str((restore or {}).get("instruction_pc", "")).lower(),
             str((restore or {}).get("instruction_word", "")).lower()) != \
            ("0x800b3ed0", "0xa662006e"):
        raise SystemExit(f"Thud transient writers drifted: {hp_changes}")
    if _registers(damage_exec) != {
            "a0": 50, "v0": 48, "v1": 0, "s1": CONTACT_RECORD + 8,
            "s2": ACTOR, "ra": 0x80058EC0} or \
            _registers(restore_exec) != {"v0": 50, "s3": ACTOR}:
        raise SystemExit(
            f"Thud transient writer registers drifted: {damage_exec} {restore_exec}")
    if not {"0x800b3d44", "0x800b3ec8"}.issubset(target_read_pcs):
        raise SystemExit(f"Thud target-field reads drifted: {target_read_pcs}")
    if page.get("truncated") is not False or page.get("total") != len(events) or \
            any(row.get("truncated") or not (row.get("events") or [])
                for row in execution.values()):
        raise SystemExit("Thud transient trace accounting incomplete")
    return {
        "execution_mode_boundary": (
            "accessLog/execTrace force the interpreter. These rows attribute "
            "writers and ownership only; passive trace pairs carry timing."),
        "start_target_movie_frame": TRANSIENT_PRE_FRAME - 1,
        "frames_run": 30, "before": before,
        "access": {
            "specifications": list(access_specs), "watches": access_watches,
            "events": events, "total": page.get("total"),
            "truncated": page.get("truncated"),
        },
        "execution": execution,
        "decisive_writers": {"damage": damage, "restore": restore},
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "ownership_boundary": (
            "0x8005905C is an inner class-dispatch block inside the resident "
            "0x80058AF8 contact-vs-actor handler, not a standalone call entry. "
            "0x80054A64 calls the save-owned overlay update at 0x800B3C70."),
    }


def _phase_branch_attribution(client: Any, movie_path: Path) -> dict[str, Any]:
    specs = (
        ("master_gate", 0x800B3CA0, ["v0"]),
        ("timer_gate", 0x800B3CC8, ["v0"]),
        ("master_timer_zero_gate", 0x800B3CDC, ["v0"]),
        ("hp_equal_gate", 0x800B3D50, ["v0", "v1"]),
        ("hp_floor_gate", 0x800B3D58, ["v0", "v1"]),
        ("negative_arena_gate", 0x800B3D88, ["v0", "v1"]),
        ("positive_arena_gate", 0x800B3D94, ["v0", "v1"]),
        ("counter_eight_gate", 0x800B3DB4, ["v0", "v1"]),
        ("target_minus_four_gate", 0x800B3E40, ["v0", "v1"]),
        ("grain_threshold_gate", 0x800B3EAC, ["v0", "v1"]),
        ("restore_store", OVERLAY_RESTORE, ["v0", "s3"]),
    )

    def capture(label: str, start_frame: int) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, start_frame)
        before = _snapshot(client)
        client.call("execTrace.clear", {})
        watches = [client.call("execTrace.addWatch", {
            "pc": f"0x{pc:08X}", "capture": registers,
            "label": name, "max_events": 32,
        }) for name, pc, registers in specs]
        run = client.call("execTrace.run", {"frames": 3})
        events = {
            name: client.call("execTrace.get", {
                "watch_id": watch["watch_id"], "offset": 0, "limit": 32})
            for (name, _pc, _registers), watch in zip(specs, watches)
        }
        client.call("execTrace.clear", {})
        if any(row.get("truncated") is not False or
               row.get("total") != len(row.get("events") or [])
               for row in events.values()):
            raise SystemExit(f"Thud {label} phase-branch trace incomplete")
        return {
            "start_target_movie_frame": start_frame,
            "frames_run": 3,
            "before": before,
            "events": events,
            "after": _snapshot(client),
            "final_status": {key: (run.get("status") or {}).get(key)
                             for key in ("pc", "sp", "frame", "cycle")},
        }

    first = capture("first", PHASE_DAMAGE_FRAMES[0])
    eighth = capture("eighth", PHASE_DAMAGE_FRAMES[-1])

    def tuples(window: dict[str, Any], label: str,
               registers: tuple[str, ...]) -> set[tuple[int, ...]]:
        rows = ((window.get("events") or {}).get(label) or {}).get("events") or []
        return {tuple(int((row.get("regs") or {})[name], 0)
                      for name in registers) for row in rows}

    expected_present = {
        "first": {
            "hp_equal_gate": (("v0", "v1"), (50, 48)),
            "hp_floor_gate": (("v0", "v1"), (0, 48)),
            "negative_arena_gate": (
                ("v0", "v1"),
                (ARENA_NEGATIVE_SENTINEL, ARENA_NEGATIVE_SENTINEL)),
            "counter_eight_gate": (("v0", "v1"), (1, 8)),
            "grain_threshold_gate": (("v0", "v1"), (1, 0)),
            "restore_store": (("v0", "s3"), (50, ACTOR)),
        },
        "eighth": {
            "hp_equal_gate": (("v0", "v1"), (50, 48)),
            "hp_floor_gate": (("v0", "v1"), (0, 48)),
            "negative_arena_gate": (
                ("v0", "v1"),
                (ARENA_NEGATIVE_SENTINEL, ARENA_POSITIVE_SENTINEL)),
            "positive_arena_gate": (
                ("v0", "v1"),
                (ARENA_POSITIVE_SENTINEL, ARENA_POSITIVE_SENTINEL)),
            "counter_eight_gate": (("v0", "v1"), (8, 8)),
            "target_minus_four_gate": (("v0", "v1"), (46, 48)),
            "restore_store": (("v0", "s3"), (50, ACTOR)),
        },
    }
    windows = {"first": first, "eighth": eighth}
    for window_name, expectations in expected_present.items():
        for event_label, (registers, wanted) in expectations.items():
            if wanted not in tuples(windows[window_name], event_label, registers):
                raise SystemExit(
                    f"Thud {window_name} {event_label} branch tuple drifted")
    for window_name, absent in {
            "first": ("positive_arena_gate", "target_minus_four_gate"),
            "eighth": ("grain_threshold_gate",)}.items():
        for event_label in absent:
            if ((windows[window_name]["events"].get(event_label) or {}).get(
                    "events") or []):
                raise SystemExit(
                    f"Thud {window_name} unexpectedly executed {event_label}")
    return {
        "execution_mode_boundary": (
            "Point execTrace watches force the interpreter. These two three-frame "
            "windows attribute branch operands only; passive traceToFrame pairs "
            "carry natural frame/cycle behavior."),
        "first_reset": first,
        "eighth_reset": eighth,
        "expected_branch_operands": expected_present,
    }


def _control_snapshot(client: Any) -> dict[str, Any]:
    return _snapshot(client, include_full_ram=True)


def _causal_controls(client: Any, movie_path: Path) -> dict[str, Any]:
    def branch(frame: int, frames: int, *, write_method: str | None = None,
               address: int | None = None, value: int | None = None) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, frame)
        before = _control_snapshot(client)
        written = None
        after_write = None
        if write_method is not None and address is not None and value is not None:
            written = client.call(write_method, {
                "address": f"0x{address:08X}", "value": value})
            after_write = _control_snapshot(client)
        client.call("emulator.advanceFrames", {"frames": frames})
        return {"before": before, "write": written,
                "after_write": after_write, "after": _control_snapshot(client),
                "frames_advanced": frames}

    damage_control = branch(TRANSIENT_PRE_FRAME, 1)
    damage_mutation = branch(
        TRANSIENT_PRE_FRAME, 1, write_method="debugger.writeU8",
        address=CONTACT_DAMAGE_CLASS, value=127)
    target_control = branch(TRANSIENT_DAMAGE_FRAME, 2)
    target_mutation = branch(
        TRANSIENT_DAMAGE_FRAME, 2, write_method="debugger.writeU32",
        address=OVERLAY_TARGET_HP, value=49)
    phase_control = branch(PHASE_DAMAGE_FRAMES[0], 2)
    target_equal_mutation = branch(
        PHASE_DAMAGE_FRAMES[0], 2, write_method="debugger.writeU32",
        address=OVERLAY_TARGET_HP, value=48)
    hp_floor_mutation = branch(
        PHASE_DAMAGE_FRAMES[0], 2, write_method="debugger.writeU16",
        address=ACTOR_HP, value=20)
    arena_sentinel_mutation = branch(
        PHASE_DAMAGE_FRAMES[0], 2, write_method="debugger.writeU32",
        address=ARENA_POSITION, value=0)
    counter_eight_mutation = branch(
        PHASE_DAMAGE_FRAMES[0], 2, write_method="debugger.writeU32",
        address=PHASE_COUNTER, value=7)
    grain_formula_mutation = branch(
        PHASE_DAMAGE_FRAMES[0], 2, write_method="debugger.writeU8",
        address=GRAIN, value=41)

    def master_branch(*, mutate_master: bool) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, PHASE_DAMAGE_FRAMES[0])
        before_setup = _control_snapshot(client)
        setup_write = client.call("debugger.writeU32", {
            "address": f"0x{PHASE_TIMER:08X}", "value": 0})
        after_shared_setup = _control_snapshot(client)
        mutation_write = None
        after_mutation = None
        if mutate_master:
            mutation_write = client.call("debugger.writeU16", {
                "address": f"0x{MASTER_STATE:08X}", "value": 1})
            after_mutation = _control_snapshot(client)
        client.call("emulator.advanceFrames", {"frames": 2})
        return {
            "before_setup": before_setup, "setup_write": setup_write,
            "after_shared_setup": after_shared_setup,
            "mutation_write": mutation_write,
            "after_mutation": after_mutation,
            "after": _control_snapshot(client), "frames_advanced": 2,
        }

    master_control = master_branch(mutate_master=False)
    master_mutation = master_branch(mutate_master=True)
    damage = {"control": damage_control, "mutation": damage_mutation}
    target = {"control": target_control, "mutation": target_mutation}
    for label, pair, wanted_before, wanted_after in (
            ("damage_class", damage, (50, 0, 50), ((48, 0, 50), (46, 127, 50))),
            ("overlay_target", target, (48, 0, 50), ((50, 0, 50), (49, 0, 49)))):
        control_before = pair["control"]["before"]
        mutation_before = pair["mutation"]["before"]
        before_tuple = (control_before["actor"]["hp"],
                        control_before["contact"]["damage_class"],
                        control_before["overlay_target_hp"])
        aligned_keys = ("emulator_frame", "cycle", "movie_frame")
        if before_tuple != wanted_before or any(
                control_before[key] != mutation_before[key]
                for key in (*aligned_keys, "main_ram_sha256", "registers_sha256")):
            raise SystemExit(f"Thud {label} pre-branch mismatch")
        outcomes = []
        for side in ("control", "mutation"):
            after = pair[side]["after"]
            outcomes.append((after["actor"]["hp"],
                             after["contact"]["damage_class"],
                             after["overlay_target_hp"]))
        if tuple(outcomes) != wanted_after or any(
                pair["control"]["after"][key] != pair["mutation"]["after"][key]
                for key in aligned_keys):
            raise SystemExit(f"Thud {label} outcome mismatch: {outcomes}")
    if damage_mutation["after_write"]["main_ram_sha256"] == \
            damage_mutation["before"]["main_ram_sha256"] or \
            target_mutation["after_write"]["main_ram_sha256"] == \
            target_mutation["before"]["main_ram_sha256"]:
        raise SystemExit("Thud control mutation did not change main RAM")

    phase_mutations = {
        "target_equals_hp": target_equal_mutation,
        "hp_floor": hp_floor_mutation,
        "arena_sentinel": arena_sentinel_mutation,
        "counter_eight": counter_eight_mutation,
        "grain_formula": grain_formula_mutation,
    }
    aligned_keys = ("emulator_frame", "cycle", "movie_frame",
                    "main_ram_sha256", "registers_sha256")
    if any(phase_control["before"][key] != mutation["before"][key]
           for mutation in phase_mutations.values() for key in aligned_keys):
        raise SystemExit("Thud phase-control starting boundaries differ")

    def phase_tuple(row: dict[str, Any]) -> tuple[int, ...]:
        reset = row["phase_reset"]
        return (row["actor"]["hp"], row["overlay_target_hp"],
                reset["counter"], reset["grain_derived_value"],
                row["master_state"], reset["heading"],
                reset["motion_timer"])

    phase_outcomes = {
        "control": phase_tuple(phase_control["after"]),
        **{name: phase_tuple(row["after"])
           for name, row in phase_mutations.items()},
    }
    expected_phase_outcomes = {
        "control": (50, 50, 1, 9, 0, 0, 0),
        "target_equals_hp": (48, 48, 0, 0, 0, 0, 0),
        "hp_floor": (20, 50, 0, 0, 0, 0, 0),
        "arena_sentinel": (50, 50, 0, 0, 0, 0, 0),
        "counter_eight": (50, 50, 8, 0, 1, 32, 149),
        "grain_formula": (50, 50, 1, 8, 0, 0, 0),
    }
    if phase_outcomes != expected_phase_outcomes:
        raise SystemExit(f"Thud phase-control outcomes drifted: {phase_outcomes}")
    for name, mutation in phase_mutations.items():
        if mutation["after_write"]["main_ram_sha256"] == \
                mutation["before"]["main_ram_sha256"]:
            raise SystemExit(f"Thud {name} mutation did not change main RAM")

    master_pair = {"control": master_control, "mutation": master_mutation}
    master_aligned = ("emulator_frame", "cycle", "movie_frame",
                      "main_ram_sha256", "registers_sha256")
    if any(master_control["before_setup"][key] !=
           master_mutation["before_setup"][key] for key in master_aligned) or \
            any(master_control["after_shared_setup"][key] !=
                master_mutation["after_shared_setup"][key]
                for key in master_aligned):
        raise SystemExit("Thud master-gate shared setup differs")
    master_outcomes = {
        side: (row["after"]["actor"]["hp"],
               row["after"]["phase_reset"]["timer"],
               row["after"]["phase_reset"]["counter"],
               row["after"]["master_state"])
        for side, row in master_pair.items()
    }
    if master_outcomes != {
            "control": (50, 105, 1, 0),
            "mutation": (48, 0, 0, 1)}:
        raise SystemExit(f"Thud master-gate outcomes drifted: {master_outcomes}")
    return {
        "damage_class": {
            **damage, "single_field": f"0x{CONTACT_DAMAGE_CLASS:08x}",
            "mutation": {**damage_mutation,
                         "interpretation": "class 0->127 selects -4, changing HP 48->46"},
            "falsified_alternative": (
                "The 50->48 decrement is not invariant to the contact damage-class byte.")},
        "overlay_target_hp": {
            **target, "single_field": f"0x{OVERLAY_TARGET_HP:08x}",
            "mutation": {**target_mutation,
                         "interpretation": "target 50->49 changes restored HP 50->49"},
            "falsified_alternative": (
                "The 48->50 restoration is not independent of 0x800B4C70.")},
        "phase_reset_guards": {
            "control": phase_control,
            "mutations": phase_mutations,
            "observed_outcomes": phase_outcomes,
            "expected_outcomes": expected_phase_outcomes,
            "single_fields": {
                "target_equals_hp": f"0x{OVERLAY_TARGET_HP:08x}",
                "hp_floor": f"0x{ACTOR_HP:08x}",
                "arena_sentinel": f"0x{ARENA_POSITION:08x}",
                "counter_eight": f"0x{PHASE_COUNTER:08x}",
                "grain_formula": f"0x{GRAIN:08x}",
            },
            "interpretation": (
                "Exact target/HP equality and signed HP<21 suppress the restore; "
                "only an exact arena sentinel increments the counter; counter 8 "
                "enters master state 1; grain 41 changes the same-frame derived "
                "value from 9 to 8."),
        },
        "master_timer_gate": {
            **master_pair,
            "shared_setup_field": f"0x{PHASE_TIMER:08x}=0",
            "single_field": f"0x{MASTER_STATE:08x}",
            "observed_outcomes": master_outcomes,
            "interpretation": (
                "With the same timer-zero setup, master state 0 integrates the "
                "scene-14 reset path while master state 1 blocks it."),
        },
        "control_rule": (
            "Each side reloads the same pristine movie/state boundary; only the "
            "named field differs before an equal emulator.advanceFrames step. "
            "The master-state pair additionally applies the same timer-zero setup "
            "to both sides before its named mutation."),
    }


def _trajectory_writer_attribution(
        client: Any, movie_path: Path) -> dict[str, Any]:
    """Bind the counter-8 path-coordinate and generic actor-motion join."""
    specs = (
        {"address": f"0x{ACTOR_POS_X:08X}", "length": 0x34,
         "type": "write", "label": "actor_motion_writes", "max_events": 1000},
        {"address": f"0x{PHASE_PATH_COORDINATE:08X}", "length": 4,
         "type": "write", "label": "path_coordinate", "max_events": 256},
        {"address": f"0x{PHASE_MOTION_TIMER:08X}", "length": 4,
         "type": "write", "label": "motion_timer", "max_events": 256},
        {"address": f"0x{PHASE_HEADING:08X}", "length": 4,
         "type": "write", "label": "heading", "max_events": 256},
        {"address": f"0x{ACTOR_MOTION_TARGET_X:08X}", "length": 4,
         "type": "read", "label": "target_x_reads", "max_events": 256},
        {"address": f"0x{ACTOR_MOTION_TARGET_Z:08X}", "length": 4,
         "type": "read", "label": "target_z_reads", "max_events": 256},
    )

    def capture(frame: int, frames: int) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, frame)
        before = _snapshot(client)
        client.call("accessLog.clear", {})
        watches = [client.call("accessLog.addWatch", spec) for spec in specs]
        run = client.call("accessLog.run", {"frames": frames})
        page = client.call("accessLog.get", {"offset": 0, "limit": 10000})
        client.call("accessLog.clear", {})
        events = page.get("events") or []
        if page.get("truncated") is not False or page.get("total") != len(events) or \
                any((row.get("hit_count") or 0) >= row.get("max_events", 0)
                    for row in page.get("watches") or []):
            raise SystemExit(f"Thud trajectory trace incomplete at {frame}")
        return {
            "start_target_movie_frame": frame, "frames_run": frames,
            "before": before, "after": _snapshot(client),
            "specifications": list(specs), "watches": watches,
            "events": events,
            "accounting": {"total": page.get("total"),
                           "returned": len(events),
                           "truncated": page.get("truncated")},
            "final_status": {key: (run.get("status") or {}).get(key)
                             for key in ("pc", "sp", "frame", "cycle")},
        }

    early = capture(TRAJECTORY_START_FRAME, 20)
    late = capture(TRAJECTORY_MID_FRAME, 10)

    def pcs(window: dict[str, Any]) -> set[str]:
        return {str(row.get("instruction_pc", "")).lower()
                for row in window["events"]}

    early_required = {
        PATH_DECREMENT_STORE, TARGET_X_STORE, TARGET_Z_STORE,
        MOTION_TIMER_STORE, HEADING_STORE, ACTOR_EARLY_X_STORE,
        ACTOR_EARLY_Z_STORE, ACTOR_TARGET_X_READER, ACTOR_TARGET_Z_READER,
    }
    late_required = {
        PATH_DECREMENT_STORE, TARGET_X_STORE, TARGET_Z_STORE,
        MOTION_TIMER_STORE, HEADING_STORE, ACTOR_LATE_X_STORE,
        ACTOR_LATE_Z_STORE,
    }
    early_pcs = pcs(early)
    late_pcs = pcs(late)
    if {f"0x{pc:08x}" for pc in early_required} - early_pcs or \
            {f"0x{pc:08x}" for pc in late_required} - late_pcs:
        raise SystemExit(
            f"Thud trajectory writer/readers drifted: {early_pcs} {late_pcs}")
    path_step = next((row for row in early["events"]
                      if str(row.get("instruction_pc", "")).lower() ==
                      f"0x{PATH_DECREMENT_STORE:08x}"), None)
    target_x = next((row for row in early["events"]
                     if str(row.get("instruction_pc", "")).lower() ==
                     f"0x{TARGET_X_STORE:08x}"), None)
    target_z = next((row for row in early["events"]
                     if str(row.get("instruction_pc", "")).lower() ==
                     f"0x{TARGET_Z_STORE:08x}"), None)
    if ((path_step or {}).get("value"), (path_step or {}).get("new_value")) != \
            (156704, 154144) or \
            (target_x or {}).get("new_value") != 154144 or \
            (target_z or {}).get("new_value") != 154144:
        raise SystemExit(
            f"Thud trajectory initial stores drifted: {path_step} "
            f"{target_x} {target_z}")
    return {
        "execution_mode_boundary": (
            "accessLog forces the interpreter. These windows attribute exact "
            "writers/readers only; passive boundaries and the matched one-field "
            "control carry behavior and timing."),
        "early_window": early, "late_window": late,
        "decisive_initial_stores": {
            "path_decrement": path_step,
            "actor_target_x": target_x,
            "actor_target_z": target_z,
        },
        "proved_join": (
            "The overlay decrements 0x800B4CB0 by 2560, copies the result to "
            "actor +0x28/+0x34, and resident actor motion reads those targets."),
    }


def _trajectory_control(client: Any, movie_path: Path) -> dict[str, Any]:
    """Shift only the phase path coordinate and measure downstream state."""
    def branch(mutate: bool) -> dict[str, Any]:
        _advance_movie_to(client, movie_path, TRAJECTORY_START_FRAME)
        before = _control_snapshot(client)
        write = None
        after_write = None
        if mutate:
            write = client.call("debugger.writeU32", {
                "address": f"0x{PHASE_PATH_COORDINATE:08X}",
                "value": before["phase_reset"]["arena_position"] +
                TRAJECTORY_DELTA})
            after_write = _control_snapshot(client)
        client.call("emulator.advanceFrames", {
            "frames": TRAJECTORY_END_FRAME - TRAJECTORY_START_FRAME})
        end = _control_snapshot(client)
        client.call("emulator.advanceFrames", {
            "frames": TRAJECTORY_RETIRE_FRAME - TRAJECTORY_END_FRAME})
        retired = _control_snapshot(client)
        return {"before": before, "write": write, "after_write": after_write,
                "end": end, "retired": retired}

    control = branch(False)
    mutation = branch(True)
    aligned = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
               "main_ram_sha256", "registers_sha256")
    if any(control["before"][key] != mutation["before"][key] for key in aligned):
        raise SystemExit("Thud trajectory branches differ before mutation")
    if mutation["after_write"]["phase_reset"]["arena_position"] != \
            control["before"]["phase_reset"]["arena_position"] + \
            TRAJECTORY_DELTA or \
            mutation["after_write"]["main_ram_sha256"] == \
            mutation["before"]["main_ram_sha256"]:
        raise SystemExit("Thud trajectory mutation did not change one field")

    control_end = control["end"]
    mutation_end = mutation["end"]
    expected_control = {
        "position": [532, -39328, -1551],
        "motion_target_x_unknown_30_z": [-40416, -608, -40416],
        "path": 4294926880,
        "player": [82399, 3502, 9180],
        "hp": 50,
    }
    observed_control = {
        "position": control_end["actor"]["position"],
        "motion_target_x_unknown_30_z": control_end["actor"][
            "motion_target_x_unknown_30_z"],
        "path": control_end["phase_reset"]["arena_position"],
        "player": control_end["player"]["position"],
        "hp": control_end["actor"]["hp"],
    }
    deltas = {
        "actor_position": [b - a for a, b in zip(
            control_end["actor"]["position"],
            mutation_end["actor"]["position"])],
        "actor_motion_target_x_unknown_30_z": [b - a for a, b in zip(
            control_end["actor"]["motion_target_x_unknown_30_z"],
            mutation_end["actor"]["motion_target_x_unknown_30_z"])],
        "path_coordinate": (
            mutation_end["phase_reset"]["arena_position"] -
            control_end["phase_reset"]["arena_position"]),
        "player_position": [b - a for a, b in zip(
            control_end["player"]["position"],
            mutation_end["player"]["position"])],
    }
    if observed_control != expected_control or deltas != {
            "actor_position": [TRAJECTORY_DELTA, 0, 0],
            "actor_motion_target_x_unknown_30_z": [
                TRAJECTORY_DELTA, 0, TRAJECTORY_DELTA],
            "path_coordinate": TRAJECTORY_DELTA,
            "player_position": [0, 0, 0]}:
        raise SystemExit(
            f"Thud trajectory control drifted: {observed_control} {deltas}")
    end_aligned = ("emulator_frame", "cycle", "movie_frame")
    if any(control_end[key] != mutation_end[key] for key in end_aligned) or \
            control_end["phase_reset"]["heading"] != \
            mutation_end["phase_reset"]["heading"] or \
            control_end["phase_reset"]["motion_timer"] != \
            mutation_end["phase_reset"]["motion_timer"]:
        raise SystemExit("Thud trajectory branches lost equal-time alignment")
    for row in (control["retired"], mutation["retired"]):
        if (row["actor"]["hp"], row["actor"]["flags"], row["live_table_0"]) != \
                (0, "0x0055", "0x00000000"):
            raise SystemExit(f"Thud shifted-path retirement drifted: {row}")
    if mutation["retired"]["actor"]["position"][0] - \
            control["retired"]["actor"]["position"][0] != TRAJECTORY_DELTA:
        raise SystemExit("Thud shifted-path actor X did not persist to retirement")
    return {
        "control": control, "mutation": mutation,
        "single_field": f"0x{PHASE_PATH_COORDINATE:08x}",
        "delta": TRAJECTORY_DELTA,
        "end_target_movie_frame": TRAJECTORY_END_FRAME,
        "retire_target_movie_frame": TRAJECTORY_RETIRE_FRAME,
        "observed_end_deltas": deltas,
        "interpretation": (
            "A +4096 path-coordinate mutation produces exact +4096 actor X/Z "
            "motion targets and +4096 final actor X while player position, actor "
            "Y/Z, heading and timer stay fixed. Both branches still retire at "
            "the sampled boundary, so completion policy is not assigned."),
        "control_rule": (
            "Each side reloads target 3741 from the same pristine movie/state. "
            "Full RAM, registers, cycle, frame, PC and SP match before the only "
            "write; both sides then advance equal emulator-frame counts."),
    }


def _writer_attribution(client: Any, movie_path: Path) -> dict[str, Any]:
    _start_movie(client, movie_path)
    client.call("movie.advanceToFrame", {
        "frame": PRE_DEFEAT_FRAME, "max_frames": PRE_DEFEAT_FRAME + 1})
    before = _snapshot(client)
    client.call("accessLog.clear", {})
    specs = (
        {"address": f"0x{ACTOR_HP:08X}", "length": 2, "type": "write",
         "label": "thud_hp", "max_events": 1000},
        {"address": f"0x{ACTOR_FLAGS:08X}", "length": 2, "type": "write",
         "label": "thud_flags", "max_events": 1000},
        {"address": f"0x{LIVE_TABLE_0:08X}", "length": 4, "type": "write",
         "label": "live_table_0", "max_events": 1000},
        {"address": f"0x{SCENE:08X}", "length": 4, "type": "write",
         "label": "scene", "max_events": 1000},
    )
    watches = [client.call("accessLog.addWatch", spec) for spec in specs]
    run = client.call("accessLog.run", {"frames": 145})
    page = client.call("accessLog.get", {"offset": 0, "limit": 10000})
    client.call("accessLog.clear", {})
    events = page.get("events") or []
    by_id = {row["watch_id"]: row["label"] for row in watches}
    changes = [{**event, "watch_label": by_id.get(event.get("watch_id"))}
               for event in events
               if event.get("new_value") is not None and
               event.get("new_value") != event.get("value")]
    decisive = {}
    for label, old, new in (
            ("hp_zero", 50, 0), ("active_clear", 0x4055, 0x55),
            ("live_table_clear", ACTOR, 0)):
        matches = [row for row in changes if row.get("value") == old and
                   row.get("new_value") == new]
        # The mover clears/re-arms the active bit on earlier frames.  The last
        # matching transition is the persistent retirement clear immediately
        # preceding the live-table zero; retain that rather than an early pulse.
        decisive[label] = matches[-1] if matches else None
    accounting = {
        "total": page.get("total"), "returned": len(events),
        "truncated": page.get("truncated"),
        "watches": [{key: row.get(key) for key in (
            "watch_id", "address", "length", "type", "label",
            "max_events", "hit_count")} for row in page.get("watches") or []],
    }
    result = {
        "execution_mode_boundary": (
            "accessLog forces the interpreter. Its instruction/value rows are "
            "writer attribution only; behavior/timing comes from separate passive "
            "cycle-neutral traceToFrame replays."),
        "start_movie_frame": PRE_DEFEAT_FRAME, "frames_run": 145,
        "before": before, "accounting": accounting,
        "value_changing_events": changes, "decisive_writers": decisive,
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "scene_watch_boundary": (
            "No scene event is required: the scene transition resets/unloads "
            "instrumentation. Passive frame 4039 is the scene-exit authority."),
    }
    expected = {
        "hp_zero": ("0x800b4528", "0xa660006e", "sh zero, 0x6e(s3)",
                    "0x8009fdee", 50, 0),
        "active_clear": ("0x8004d270", "0xa6220000", "sh v0, 0x0(s1)",
                         "0x8009fddc", 0x4055, 0x55),
        "live_table_clear": ("0x8004d43c", "0xac200748", "sw zero, 0x748(at)",
                             "0x80090748", ACTOR, 0),
    }
    for label, wanted in expected.items():
        row = decisive.get(label) or {}
        observed = (str(row.get("instruction_pc", "")).lower(),
                    str(row.get("instruction_word", "")).lower(),
                    row.get("instruction"), str(row.get("address", "")).lower(),
                    row.get("value"), row.get("new_value"))
        if observed != wanted:
            raise SystemExit(f"Thud decisive writer {label} drifted: {observed}")
    if accounting["truncated"] is not False or accounting["returned"] != \
            accounting["total"] or any((row.get("hit_count") or 0) >= 1000
                                        for row in accounting["watches"]):
        raise SystemExit(f"Thud access accounting incomplete: {accounting}")
    return result


def derive_summary(document: dict[str, Any]) -> dict[str, Any]:
    boundaries = document.get("natural_defeat_boundaries") or {}
    snap = lambda key: (boundaries.get(str(key)) or {}).get("snapshot") or {}
    writers = ((document.get("writer_attribution") or {}).get(
        "decisive_writers") or {})
    transient = document.get("transient_damage_boundaries") or {}
    transient_snap = lambda key: (transient.get(str(key)) or {}).get(
        "snapshot") or {}
    transient_writers = ((document.get("transient_writer_attribution") or {}).get(
        "decisive_writers") or {})
    controls = document.get("causal_controls") or {}
    cycles = document.get("natural_phase_cycles") or []
    first_damage = (((cycles[0] if cycles else {}).get("damage") or {}).get(
        "snapshot") or {})
    last_restore = (((cycles[-1] if cycles else {}).get("restore") or {}).get(
        "snapshot") or {})
    phase_outcomes = ((controls.get("phase_reset_guards") or {}).get(
        "observed_outcomes") or {})
    launch_writers = ((document.get("launch_writer_attribution") or {}).get(
        "decisive_writers") or {})
    launch_outcomes = ((document.get("launch_input_counterfactual") or {}).get(
        "observed_outcomes") or {})
    trajectory = document.get("trajectory_control") or {}
    trajectory_deltas = trajectory.get("observed_end_deltas") or {}
    arena_boundaries = document.get("natural_arena_damage_boundaries") or {}
    arena_snap = lambda key: (arena_boundaries.get(str(key)) or {}).get(
        "snapshot") or {}
    arena_attribution = document.get("arena_damage_attribution") or {}
    arena_control = document.get("arena_damage_control") or {}
    post_restore_attribution = document.get(
        "post_restore_attack_attribution") or {}
    post_restore_writers = post_restore_attribution.get(
        "decisive_writers") or {}
    post_restore_boundaries = document.get(
        "post_restore_attack_boundaries") or {}
    post_restore_snap = lambda key: (post_restore_boundaries.get(
        str(key)) or {}).get("snapshot") or {}
    post_restore_control = document.get("post_restore_attack_control") or {}
    sound_attribution = document.get("action20_sound_attribution") or {}
    sound_control = document.get("action20_sound_control") or {}
    sound_request = sound_attribution.get("request") or {}
    sound_comparison = sound_control.get("event_comparison") or {}
    action20_boundaries = document.get("action20_effect_boundaries") or {}
    action20_snap = lambda key: (action20_boundaries.get(
        str(key)) or {}).get("snapshot") or {}
    action20_control = document.get("action20_effect_control") or {}
    action20_writers = ((document.get(
        "action20_effect_attribution") or {}).get("decisive_writers") or {})
    visual = document.get("action20_visual_presentation_control") or {}
    visual_diff = visual.get("frame_diff") or {}
    visual_pick = visual.get("natural_object_pick") or {}
    visual_draw = visual_pick.get("draw_call") or {}
    visual_source = visual_pick.get("source") or {}
    renderer = document.get("action20_renderer_attribution") or {}
    return {
        "movies_replayed": 1,
        "launch_action_instruction_pc": (launch_writers.get(
            "action_id") or {}).get("instruction_pc", "").lower(),
        "launch_caller_return": ((document.get(
            "launch_writer_attribution") or {}).get("caller") or {}).get(
                "return_address"),
        "thud_attack_action_instruction_pc": (post_restore_writers.get(
            "action_id") or {}).get("instruction_pc", "").lower(),
        "thud_attack_caller": (post_restore_attribution.get(
            "caller") or {}).get("allocator_call"),
        "thud_attack_contact_transition": [
            (post_restore_snap(POST_RESTORE_ATTACK_PRE_FRAME).get(
                "thud_attack_contact") or {}).get("action_id"),
            (post_restore_snap(POST_RESTORE_ATTACK_POST_FRAME).get(
                "thud_attack_contact") or {}).get("action_id"),
        ],
        "thud_attack_countdown_control": (post_restore_control.get(
            "observed_outcomes") or {}),
        "thud_attack_sound_call": ((sound_attribution.get("caller") or {}).get(
            "instruction_pc")),
        "thud_attack_sound_request": [
            sound_request.get("signed_cue"),
            sound_request.get("position_context")],
        "thud_attack_sound_key_on": {
            "natural_event_total": sound_comparison.get("natural_total"),
            "call_nop_event_total": sound_comparison.get("call_nop_total"),
            "start_address": ACTION20_SOUND_SAMPLE_START,
            "frames": [event.get("frame") for event in
                       sound_comparison.get("natural_early_key_ons") or []],
        },
        "thud_attack_natural_retirement": [
            (action20_snap(ACTION20_NATURAL_ACTIVE_FRAME).get(
                "thud_attack_contact") or {}).get("lifetime_ttl"),
            (action20_snap(ACTION20_NATURAL_RETIRE_FRAME).get(
                "thud_attack_contact") or {}).get("lifetime_ttl"),
            (action20_snap(ACTION20_NATURAL_ACTIVE_FRAME).get(
                "phase_reset") or {}).get("grain"),
            (action20_snap(ACTION20_NATURAL_RETIRE_FRAME).get(
                "phase_reset") or {}).get("grain"),
        ],
        "thud_attack_radius_control": (action20_control.get(
            "observed_outcomes") or {}),
        "thud_attack_effect_instruction_pcs": [
            (action20_writers.get(label) or {}).get(
                "instruction_pc", "").lower()
            for label in ("grain_increment", "record_state",
                          "record_active_gate")],
        "thud_attack_visual_diff": {
            "pixel_count": visual_diff.get("pixelCount"),
            "bounding_boxes": visual_diff.get("boundingBoxes"),
        },
        "thud_attack_visual_draw": {
            "primitive": visual_draw.get("primitiveType"),
            "command_id": visual_draw.get("commandId"),
            "dma_source": visual_source.get("dmaSource"),
        },
        "thud_attack_renderer": ((renderer.get("renderer") or {}).get(
            "address")),
        "square_clear_post_action": [
            (launch_outcomes.get("post_launch") or {}).get(side, [None] * 4)[2]
            for side in ("natural", "square_cleared")],
        "square_clear_damage_hp": [
            (launch_outcomes.get("damage") or {}).get(side, [None] * 2)[0]
            for side in ("natural", "square_cleared")],
        "square_clear_phase_counter": [
            (launch_outcomes.get("restore") or {}).get(side, [None] * 3)[1]
            for side in ("natural", "square_cleared")],
        "natural_transient_hp": [
            transient_snap(frame).get("actor", {}).get("hp") for frame in
            (TRANSIENT_PRE_FRAME, TRANSIENT_DAMAGE_FRAME,
             TRANSIENT_HOLD_FRAME, TRANSIENT_RESET_FRAME)],
        "damage_instruction_pc": (transient_writers.get("damage") or {}).get(
            "instruction_pc", "").lower(),
        "restore_instruction_pc": (transient_writers.get("restore") or {}).get(
            "instruction_pc", "").lower(),
        "damage_class_control_hp": [
            (((controls.get("damage_class") or {}).get(side) or {}).get(
                "after") or {}).get("actor", {}).get("hp")
            for side in ("control", "mutation")],
        "overlay_target_control_hp": [
            (((controls.get("overlay_target_hp") or {}).get(side) or {}).get(
                "after") or {}).get("actor", {}).get("hp")
            for side in ("control", "mutation")],
        "arena_damage_health": [
            arena_snap(ARENA_DAMAGE_PRE_FRAME).get("health"),
            arena_snap(ARENA_DAMAGE_POST_FRAME).get("health")],
        "arena_transform_rows": len(
            arena_attribution.get("distance_rows") or []),
        "arena_hit_row": (arena_attribution.get("hit_row") or {}).get("row"),
        "arena_damage_call": f"0x{ARENA_DAMAGE_CALL:08x}",
        "arena_threshold_control_health": [
            (arena_control.get("observed_health") or {}).get(
                "control_after"),
            (arena_control.get("observed_health") or {}).get(
                "threshold_zero_after")],
        "natural_reset_cycles": len(cycles),
        "phase_restore_frames": list(PHASE_RESTORE_FRAMES),
        "phase_counter_transition": [
            (first_damage.get("phase_reset") or {}).get("counter"),
            (last_restore.get("phase_reset") or {}).get("counter")],
        "arena_master_transition": [first_damage.get("master_state"),
                                     last_restore.get("master_state")],
        "phase_path_coordinate_transition": [
            (last_restore.get("phase_reset") or {}).get("arena_position"),
            snap(TRAJECTORY_END_FRAME).get("phase_reset", {}).get(
                "arena_position")],
        "trajectory_control_delta": {
            "path_coordinate": trajectory_deltas.get("path_coordinate"),
            "actor_position": trajectory_deltas.get("actor_position"),
            "actor_motion_target_x_unknown_30_z": trajectory_deltas.get(
                "actor_motion_target_x_unknown_30_z"),
            "player_position": trajectory_deltas.get("player_position"),
        },
        "phase_guard_outcomes": {
            key: list(value) for key, value in phase_outcomes.items()},
        "natural_hp_transition": [snap(PRE_DEFEAT_FRAME).get("actor", {}).get("hp"),
                                  snap(HP_ZERO_FRAME).get("actor", {}).get("hp")],
        "hp_zero_instruction_pc": (writers.get("hp_zero") or {}).get(
            "instruction_pc", "").lower(),
        "retire_instruction_pcs": [
            (writers.get("active_clear") or {}).get("instruction_pc", "").lower(),
            (writers.get("live_table_clear") or {}).get(
                "instruction_pc", "").lower()],
        "retired_movie_frame": RETIRE_FRAME,
        "scene_exit": [snap(PRE_DEFEAT_FRAME).get("scene"),
                       snap(SCENE_EXIT_FRAME).get("scene")],
        "event_program_19_decode_complete": bool(
            (document.get("static_census") or {}).get(
                "event_program", {}).get("decode_complete")),
        "runtime_overlay_exactly_staged": False,
        "reset_owner_instruction_count": ((document.get(
            "runtime_overlay_identity") or {}).get(
                "reset_owner_slice") or {}).get("instruction_count"),
        "post_restore_continuation_instruction_count": ((document.get(
            "runtime_overlay_identity") or {}).get(
                "post_restore_attack_slice") or {}).get("instruction_count"),
        "arena_block_instruction_count": ((document.get(
            "runtime_overlay_identity") or {}).get(
                "arena_transform_collision_slice") or {}).get(
                    "instruction_count"),
        "d18_or_f09_completed": 0,
    }


def _source_dependencies() -> dict[str, str]:
    paths = [
        "tools/phase4_c16_bonus_death.py",
        "tools/phase4_e08_operator_contacts.py",
        "analysis/phase4_event_vm.json",
        "analysis/phase3_scene_asset_graph.json",
        "analysis/functions.csv",
        "asm/hand_written/80014844_sub_80014844.s",
        "asm/hand_written/8005044c_play_sound.s",
        "tools/build_baselines.json",
        "REBUILD/files/LEVEL08/LEVEL.BIN",
        "REBUILD/files/LEVEL08/LEVEL1.BIN",
        "REBUILD/files/SCUS_942.88",
    ]
    return {path: _sha256(ROOT / path) for path in paths}


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if document.get("schema") != "abl-phase4-thud-lifecycle/9":
        gaps.append("Thud evidence schema changed")
    if document.get("campaign_state") != "active_partial":
        gaps.append("Thud campaign state is not active_partial")
    for label, builder, key in (("fixture", build_fixture_census, "fixture_census"),
                                ("static", build_static_census, "static_census")):
        try:
            current = builder()
        except (OSError, KeyError, ValueError, SystemExit) as error:
            current = None
            gaps.append(f"Thud {label} recomputation failed: {error}")
        if current is not None and document.get(key) != current:
            gaps.append(f"Thud {label} census changed")
    if document.get("source_dependencies") != _source_dependencies():
        gaps.append("Thud source dependencies changed")
    boundaries = document.get("natural_defeat_boundaries") or {}
    snapshots = {int(key): (row.get("snapshot") or {})
                 for key, row in boundaries.items()}
    expected = {
        0: (14, 0, 4, 0, "0x8009fd80", 36, "0x4055", 50),
        3896: (14, 1, 1, 0, "0x8009fd80", 36, "0x4055", 50),
        3900: (14, 1, 1, 0, "0x8009fd80", 36, "0x4055", 0),
        3902: (14, 1, 1, 0, "0x00000000", 36, "0x0055", 0),
        4041: (0, None, 1, 0, "0x00000000", 36, "0x0055", 0),
        4113: (0, 1, 1, 0, "0x00000000", 36, "0x0055", 0),
    }
    for frame, wanted in expected.items():
        row = snapshots.get(frame) or {}
        actor = row.get("actor") or {}
        observed = (row.get("scene"), row.get("master_state") if wanted[1] is not None
                    else None, row.get("health"), row.get("lives"),
                    row.get("live_table_0"), actor.get("id"),
                    actor.get("flags"), actor.get("hp"))
        if observed != wanted:
            gaps.append(f"Thud natural boundary {frame} changed: {observed}")
        trace = (boundaries.get(str(frame)) or {}).get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(item.get("truncated") for item in trace.get("coverage") or []):
            gaps.append(f"Thud natural boundary {frame} trace changed")
    pcs_by_frame = {
        frame: {str(pc).lower() for item in
                ((boundaries.get(str(frame)) or {}).get(
                    "cycle_neutral_trace", {}).get("coverage") or [])
                for pc in item.get("pcs") or []}
        for frame in (HP_ZERO_FRAME, RETIRE_FRAME)}
    if "0x800b4528" not in pcs_by_frame[HP_ZERO_FRAME]:
        gaps.append("Thud passive HP-zero instruction coverage changed")
    if not {"0x8004d270", "0x8004d43c"}.issubset(
            pcs_by_frame[RETIRE_FRAME]):
        gaps.append("Thud passive retirement instruction coverage changed")
    transient = document.get("transient_damage_boundaries") or {}
    expected_transient = {
        TRANSIENT_PRE_FRAME: (50, 2, 0, 50),
        TRANSIENT_DAMAGE_FRAME: (48, 2, 0, 50),
        TRANSIENT_HOLD_FRAME: (48, 2, 0, 50),
        TRANSIENT_RESET_FRAME: (50, 2, 0, 50),
    }
    transient_pcs: dict[int, set[str]] = {}
    for frame, wanted in expected_transient.items():
        row = transient.get(str(frame)) or {}
        snapshot = row.get("snapshot") or {}
        contact = snapshot.get("contact") or {}
        observed = (snapshot.get("actor", {}).get("hp"),
                    contact.get("action_id"), contact.get("damage_class"),
                    snapshot.get("overlay_target_hp"))
        if observed != wanted:
            gaps.append(f"Thud transient boundary {frame} changed: {observed}")
        trace = row.get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(item.get("truncated") for item in trace.get("coverage") or []):
            gaps.append(f"Thud transient boundary {frame} trace changed")
        transient_pcs[frame] = {str(pc).lower() for item in
            trace.get("coverage") or [] for pc in item.get("pcs") or []}
    if "0x800590e4" not in transient_pcs.get(TRANSIENT_DAMAGE_FRAME, set()):
        gaps.append("Thud passive transient damage coverage changed")
    if "0x800b3ed0" not in transient_pcs.get(TRANSIENT_RESET_FRAME, set()):
        gaps.append("Thud passive transient restore coverage changed")
    arena_boundaries = document.get("natural_arena_damage_boundaries") or {}
    expected_arena_boundaries = {
        ARENA_DAMAGE_PRE_FRAME: (3, [104318, 1478, -20326], 50),
        ARENA_DAMAGE_POST_FRAME: (2, [99005, -934, -18472], 50),
    }
    for frame, wanted in expected_arena_boundaries.items():
        row = arena_boundaries.get(str(frame)) or {}
        snapshot = row.get("snapshot") or {}
        observed = (snapshot.get("health"),
                    (snapshot.get("player") or {}).get("position"),
                    (snapshot.get("actor") or {}).get("hp"))
        trace = row.get("cycle_neutral_trace") or {}
        pcs = {str(pc).lower() for coverage in trace.get("coverage") or []
               for pc in coverage.get("pcs") or []}
        required_pcs = {
            f"0x{ARENA_TRANSFORM_CALL:08x}",
            f"0x{ARENA_CANDIDATE_CALL:08x}",
            f"0x{ARENA_DISTANCE_COMPARE:08x}",
            f"0x{ARENA_DAMAGE_CALL:08x}",
            f"0x{PLAYER_TRANSITION_ENTRY:08x}",
            f"0x{PLAYER_HEALTH_STORE:08x}",
        }
        if observed != wanted or \
                (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(item.get("truncated") for item in trace.get("coverage") or []) or \
                required_pcs - pcs:
            gaps.append(
                f"Thud passive arena boundary {frame} changed: {observed}")
    arena_attribution = document.get("arena_damage_attribution") or {}
    arena_rows = arena_attribution.get("distance_rows") or []
    hit_row = arena_attribution.get("hit_row") or {}
    arena_health_write = arena_attribution.get("decisive_health_write") or {}
    arena_execution = arena_attribution.get("execution") or {}
    arena_access = arena_attribution.get("access") or {}
    if [row.get("row") for row in arena_rows] != \
            list(range(ARENA_TRANSFORM_ROW_COUNT)) or \
            [row.get("row") for row in arena_rows
             if row.get("inside_threshold")] != [ARENA_HIT_ROW] or \
            (hit_row.get("threshold_address"),
             hit_row.get("squared_distance"),
             hit_row.get("squared_distance_threshold")) != \
            (f"0x{ARENA_HIT_THRESHOLD:08x}", 454805,
             ARENA_HIT_THRESHOLD_VALUE) or \
            (str(arena_health_write.get("instruction_pc", "")).lower(),
             arena_health_write.get("value"),
             arena_health_write.get("new_value")) != \
            (f"0x{PLAYER_HEALTH_STORE:08x}", 3, 2) or \
            arena_access.get("truncated") is not False or \
            arena_access.get("total") != len(arena_access.get("events") or []) or \
            any(page.get("truncated") is not False or
                page.get("total") != page.get("returned")
                for page in arena_execution.values()):
        gaps.append("Thud six-row arena attribution changed")
    arena_control = document.get("arena_damage_control") or {}
    arena_control_side = arena_control.get("control") or {}
    arena_zero_side = arena_control.get("threshold_zero") or {}
    arena_endpoint = arena_control.get("endpoint_alignment") or {}
    arena_aligned = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                     "main_ram_sha256", "registers_sha256")
    if arena_control.get("single_field") != f"0x{ARENA_HIT_THRESHOLD:08x}" or \
            arena_control.get("observed_health") != {
                "before": 3, "control_after": 2,
                "threshold_zero_after": 3} or \
            any((arena_control_side.get("before") or {}).get(key) !=
                (arena_zero_side.get("before") or {}).get(key)
                for key in arena_aligned) or \
            (arena_control_side.get("after") or {}).get("player", {}).get(
                "position") != \
            (arena_zero_side.get("after") or {}).get("player", {}).get(
                "position") or arena_endpoint != {
                    "emulator_frame_equal": True,
                    "movie_frame_equal": True,
                    "pc_equal": True,
                    "sp_equal": True,
                    "cycle_equal": True,
                    "threshold_zero_minus_control_cycle": 0,
                    "control_pc": "0x8004fea4",
                    "threshold_zero_pc": "0x8004fea4"}:
        gaps.append("Thud arena threshold control changed")
    launch = document.get("launch_writer_attribution") or {}
    launch_decisive = launch.get("decisive_writers") or {}
    launch_expected = {
        "action_id": ("0x8005a1d8", 4, 2),
        "lifetime_ttl": ("0x8005a1e4", None, 100),
        "damage_class": ("0x8005a270", None, 0),
    }
    for label, wanted in launch_expected.items():
        row = launch_decisive.get(label) or {}
        observed = (str(row.get("instruction_pc", "")).lower(),
                    row.get("value") if wanted[1] is not None else None,
                    row.get("new_value"))
        if observed != wanted:
            gaps.append(f"Thud launch {label} writer changed: {observed}")
    launch_access = launch.get("access") or {}
    launch_execution = launch.get("execution") or {}
    if launch_access.get("truncated") is not False or \
            launch_access.get("total") != len(launch_access.get("events") or []) or \
            launch_execution.get("truncated") is not False or \
            launch_execution.get("total") != 1 or \
            ((launch.get("caller") or {}).get("return_address") !=
             f"0x{THROW_RETURN:08x}"):
        gaps.append("Thud launch attribution accounting/caller changed")
    launch_control = document.get("launch_input_counterfactual") or {}
    launch_outcomes = launch_control.get("observed_outcomes") or {}
    if launch_outcomes != {
            "post_launch": {"natural": [9, 3, 2, 99],
                            "square_cleared": [0, 2, 4, 0]},
            "damage": {"natural": [48, 2], "square_cleared": [50, 4]},
            "restore": {"natural": [50, 1, 4294801440],
                        "square_cleared": [50, 0, 4294798880]}}:
        gaps.append(f"Thud Square launch control changed: {launch_outcomes}")
    launch_points = {
        side: (launch_control.get(side) or {}).get("points") or {}
        for side in ("natural", "square_cleared")}
    launch_aligned = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                      "main_ram_sha256", "registers_sha256")
    if any((launch_points["natural"].get(str(LAUNCH_PRE_FRAME)) or {}).get(key) !=
           (launch_points["square_cleared"].get(
               str(LAUNCH_PRE_FRAME)) or {}).get(key)
           for key in launch_aligned):
        gaps.append("Thud launch branches no longer align before input edit")
    launch_boundaries = document.get("natural_launch_boundaries") or {}
    expected_launch_boundaries = {
        LAUNCH_PRE_FRAME: (6, 2, 4),
        LAUNCH_POST_FRAME: (9, 3, 2),
    }
    for frame, wanted in expected_launch_boundaries.items():
        row = launch_boundaries.get(str(frame)) or {}
        snapshot = row.get("snapshot") or {}
        observed = (snapshot.get("player", {}).get("throw_windup"),
                    snapshot.get("player", {}).get("in_flight_count"),
                    snapshot.get("contact", {}).get("action_id"))
        trace = row.get("cycle_neutral_trace") or {}
        if observed != wanted or \
                (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(item.get("truncated") for item in trace.get("coverage") or []):
            gaps.append(f"Thud passive launch boundary {frame} changed: {observed}")
    post_restore_boundaries = document.get(
        "post_restore_attack_boundaries") or {}
    expected_post_restore = {
        POST_RESTORE_ATTACK_PRE_FRAME: ((9, 1, 0, 0), (1, 6)),
        POST_RESTORE_ATTACK_POST_FRAME: ((8, 20, 200, 128), (2, 7)),
    }
    for frame, (wanted_state, wanted_counts) in expected_post_restore.items():
        row = post_restore_boundaries.get(str(frame)) or {}
        snapshot = row.get("snapshot") or {}
        contact = snapshot.get("thud_attack_contact") or {}
        observed_state = (
            (snapshot.get("phase_reset") or {}).get("grain_derived_value"),
            contact.get("action_id"), contact.get("lifetime_ttl"),
            contact.get("damage_class"),
        )
        trace = row.get("cycle_neutral_trace") or {}
        count_map = {
            entry.get("pc"): entry.get("count")
            for coverage in trace.get("coverage") or []
            for entry in coverage.get("decisive_counts_by_pc") or []
        }
        observed_counts = (
            count_map.get(f"0x{POST_RESTORE_ATTACK_CALL:08x}"),
            count_map.get(f"0x{CONTACT_ALLOCATOR:08x}"),
        )
        if observed_state != wanted_state or observed_counts != wanted_counts or \
                (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(item.get("truncated") for item in
                    trace.get("coverage") or []):
            gaps.append(
                f"Thud post-restore boundary {frame} changed: "
                f"{observed_state} {observed_counts}")
    post_restore_attribution = document.get(
        "post_restore_attack_attribution") or {}
    post_restore_writers = post_restore_attribution.get(
        "decisive_writers") or {}
    expected_post_restore_writers = {
        "action_id": ("0x8005a1d8", 1, 20),
        "lifetime_ttl": ("0x8005a1e4", None, 200),
        "damage_class": ("0x8005a270", None, 128),
    }
    for label, wanted in expected_post_restore_writers.items():
        writer = post_restore_writers.get(label) or {}
        observed = (
            str(writer.get("instruction_pc", "")).lower(),
            writer.get("value") if wanted[1] is not None else None,
            writer.get("new_value"),
        )
        if observed != wanted:
            gaps.append(
                f"Thud post-restore {label} writer changed: {observed}")
    post_restore_access = post_restore_attribution.get("access") or {}
    post_restore_execution = post_restore_attribution.get("execution") or {}
    post_restore_caller = post_restore_attribution.get("caller") or {}
    if post_restore_access.get("truncated") is not False or \
            post_restore_access.get("total") != \
            len(post_restore_access.get("events") or []) or \
            post_restore_access.get("total") != 27 or \
            any((post_restore_execution.get(label) or {}).get("truncated") is not False or
                (post_restore_execution.get(label) or {}).get("total") != 1
                for label in ("call", "allocator")) or \
            post_restore_caller.get("actor") != f"0x{ACTOR:08x}" or \
            post_restore_caller.get("return_address") != \
            f"0x{POST_RESTORE_ATTACK_RETURN:08x}":
        gaps.append("Thud post-restore attribution accounting/caller changed")
    post_restore_control = document.get("post_restore_attack_control") or {}
    post_restore_alignment = post_restore_control.get("endpoint_alignment") or {}
    if post_restore_control.get("single_field") != \
            f"0x{GRAIN_PHASE_VALUE:08x}" or \
            post_restore_control.get("observed_outcomes") != {
                "before": [9, 1, 0, 0],
                "control_after": [8, 20, 200, 128],
                "countdown_zero_after": [0, 1, 0, 0]} or \
            post_restore_alignment.get("emulator_frame_equal") is not True or \
            post_restore_alignment.get("movie_frame_equal") is not True or \
            post_restore_alignment.get("mutation_minus_control_cycle") != -1 or \
            post_restore_alignment.get("control_pc") != "0x8004fea4" or \
            post_restore_alignment.get("mutation_pc") != "0x8004fea4":
        gaps.append("Thud post-restore countdown control changed")
    sound_attribution = document.get("action20_sound_attribution") or {}
    sound_execution = sound_attribution.get("execution") or {}
    sound_caller = sound_attribution.get("caller") or {}
    sound_request = sound_attribution.get("request") or {}
    expected_sound_totals = {
        "caller": 1, "play_sound": 3, "positive_dispatch": 0}
    if any((sound_execution.get(label) or {}).get("truncated") is not False or
           (sound_execution.get(label) or {}).get("total") != total or
           (sound_execution.get(label) or {}).get("total") !=
           len((sound_execution.get(label) or {}).get("events") or [])
           for label, total in expected_sound_totals.items()) or \
            sound_caller.get("instruction_pc") != \
            f"0x{POST_RESTORE_SOUND_CALL:08x}" or \
            sound_caller.get("instruction_word") != \
            f"0x{POST_RESTORE_SOUND_WORD:08x}" or \
            sound_caller.get("actor") != f"0x{ACTOR:08x}" or \
            sound_caller.get("callee") != f"0x{PLAY_SOUND_ENTRY:08x}" or \
            sound_caller.get("return_address") != \
            f"0x{POST_RESTORE_SOUND_RETURN:08x}" or \
            sound_request != {
                "signed_cue": ACTION20_SOUND_REQUEST,
                "unsigned_a0": f"0x{ACTION20_SOUND_REQUEST_U32:08x}",
                "position_context": f"0x{ACTOR_POS_X:08x}",
                "play_sound_entry": f"0x{PLAY_SOUND_ENTRY:08x}",
                "positive_dispatch_hits_in_window": 0,
            }:
        gaps.append("Thud action-20 sound attribution changed")
    sound_control = document.get("action20_sound_control") or {}
    sound_natural = sound_control.get("natural") or {}
    sound_nop = sound_control.get("call_nop") or {}
    sound_mutation = sound_nop.get("mutation") or {}
    sound_response = sound_mutation.get("response") or {}
    sound_events = sound_control.get("event_comparison") or {}
    natural_early = sound_events.get("natural_early_key_ons") or []
    nop_early = sound_events.get("call_nop_early_key_ons") or []
    expected_sound_differences = [
        {"address": f"0x{POST_RESTORE_SOUND_CALL + offset:08x}",
         "before": value, "after": 0}
        for offset, value in enumerate((0x13, 0x41, 0x01, 0x0C))
    ]
    sound_origin_keys = ("emulator_frame", "cycle", "movie_frame", "pc",
                         "sp", "main_ram_sha256", "registers_sha256")
    if sound_control.get("single_instruction") != \
            f"0x{POST_RESTORE_SOUND_CALL:08x}" or \
            sound_mutation.get("main_ram_differences") != \
            expected_sound_differences or \
            sound_mutation.get("main_ram_difference_count") != 4 or \
            sound_response.get("written") != 4 or \
            sound_response.get("code_invalidated") is not True or \
            any((sound_natural.get("before") or {}).get(key) !=
                (sound_nop.get("before") or {}).get(key)
                for key in sound_origin_keys) or \
            sound_control.get("endpoint_alignment") != {
                "emulator_frame_equal": True, "movie_frame_equal": True,
                "pc_equal": True, "sp_equal": True,
                "natural_pc": "0x800104b8", "nop_pc": "0x800104b8",
                "nop_minus_natural_cycle": 1,
                "action20_record_equal": True,
                "gameplay_state_equal": True,
            } or \
            {key: sound_events.get(key) for key in (
                "natural_total", "call_nop_total",
                "natural_minus_call_nop", "shared_event_frame")} != {
                    "natural_total": 13, "call_nop_total": 7,
                    "natural_minus_call_nop": 6,
                    "shared_event_frame": ACTION20_SOUND_SHARED_FRAME,
                } or \
            [event.get("frame") for event in natural_early] != \
            list(ACTION20_SOUND_KEY_ON_FRAMES) or \
            any(event.get("type") != "key_on" or
                str(event.get("start_address", "")).lower() !=
                ACTION20_SOUND_SAMPLE_START for event in natural_early) or \
            nop_early:
        gaps.append("Thud action-20 exact-call SPU control changed")
    action20_boundaries = document.get("action20_effect_boundaries") or {}
    expected_action20 = {
        ACTION20_EFFECT_PRE_FRAME: (0, 20, 200, 100, 24),
        ACTION20_EFFECT_POST_FRAME: (0, 20, 199, 100, 24),
        ACTION20_NATURAL_ACTIVE_FRAME: (0, 20, 175, 100, 24),
        ACTION20_NATURAL_RETIRE_FRAME: (0, 20, 0, 100, 24),
    }
    for frame, wanted in expected_action20.items():
        row = action20_boundaries.get(str(frame)) or {}
        snapshot = row.get("snapshot") or {}
        contact = snapshot.get("thud_attack_contact") or {}
        observed = (
            (snapshot.get("phase_reset") or {}).get("grain"),
            contact.get("action_id"), contact.get("lifetime_ttl"),
            contact.get("radius_add"), contact.get("state"))
        trace = row.get("cycle_neutral_trace") or {}
        pcs = {str(pc).lower() for coverage in trace.get("coverage") or []
               for pc in coverage.get("pcs") or []}
        geometry = row.get("walker_geometry") or {}
        if observed != wanted or \
                (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(coverage.get("truncated") for coverage in
                    trace.get("coverage") or []) or \
                f"0x{ACTION20_HANDLER_ENTRY:08x}" in pcs or \
                f"0x{ACTION20_GRAIN_STORE:08x}" in pcs or \
                geometry.get("inside_radius") is not False:
            gaps.append(
                f"Thud natural action-20 boundary {frame} changed: {observed}")
    action20_control = document.get("action20_effect_control") or {}
    action20_control_side = action20_control.get("control") or {}
    action20_mutation_side = action20_control.get("radius_enlarged") or {}
    action20_mutation = action20_mutation_side.get("mutation") or {}
    action20_alignment = action20_control.get("endpoint_alignment") or {}
    aligned = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
               "main_ram_sha256", "registers_sha256")
    expected_radius_differences = [
        {"address": f"0x{THUD_ATTACK_CONTACT_RADIUS:08x}",
         "before": 100, "after": 0x70},
        {"address": f"0x{THUD_ATTACK_CONTACT_RADIUS + 1:08x}",
         "before": 0, "after": 0x17},
    ]
    if action20_control.get("single_field") != \
            f"0x{THUD_ATTACK_CONTACT_RADIUS:08x}" or \
            action20_control.get("observed_outcomes") != {
                "before": [0, 4, 20, 200, 100, 24],
                "control_after": [0, 4, 20, 199, 100, 24],
                "radius_enlarged_after": [1, 4, 20, 1, 6000, 16]} or \
            action20_mutation.get("main_ram_differences") != \
            expected_radius_differences or \
            action20_mutation.get("main_ram_difference_count") != 2 or \
            any((action20_control_side.get("before") or {}).get(key) !=
                (action20_mutation_side.get("before") or {}).get(key)
                for key in aligned) or \
            ((action20_control_side.get("before_geometry") or {}).get(
                "inside_radius")) is not False or \
            ((action20_mutation_side.get("after_write_geometry") or {}).get(
                "inside_radius")) is not True or \
            action20_alignment.get("emulator_frame_equal") is not True or \
            action20_alignment.get("movie_frame_equal") is not True or \
            action20_alignment.get("cycle_equal") is not True or \
            action20_alignment.get("mutation_minus_control_cycle") != 0 or \
            action20_alignment.get("control_pc") != "0x80010508" or \
            action20_alignment.get("mutation_pc") != "0x80010508":
        gaps.append("Thud action-20 radius control changed")
    action20_attribution = document.get("action20_effect_attribution") or {}
    action20_writers = action20_attribution.get("decisive_writers") or {}
    expected_action20_writers = {
        "grain_increment": ("0x80054f9c", 0, 1),
        "record_state": ("0x800589e0", 24, 16),
        "record_active_gate": ("0x800589e4", None, 1),
    }
    for label, wanted in expected_action20_writers.items():
        writer = action20_writers.get(label) or {}
        observed = (
            str(writer.get("instruction_pc", "")).lower(),
            writer.get("value") if wanted[1] is not None else None,
            writer.get("new_value"))
        if observed != wanted:
            gaps.append(f"Thud action-20 {label} writer changed: {observed}")
    action20_access = action20_attribution.get("access") or {}
    action20_execution = action20_attribution.get("execution") or {}
    expected_action20_exec = {
        "action20_dispatch": 1, "grain_handler_entry": 1,
        "grain_increment_store": 1, "record_state_store": 1,
        "record_active_store": 1, "bookkeeping_call": 1,
        "bookkeeping_entry": 3,
    }
    action20_registers = action20_attribution.get("decisive_registers") or {}
    if action20_access.get("truncated") is not False or \
            action20_access.get("total") != 10 or \
            action20_access.get("total") != \
            len(action20_access.get("events") or []) or \
            any((action20_execution.get(label) or {}).get("truncated") is not False or
                (action20_execution.get(label) or {}).get("total") != total or
                (action20_execution.get(label) or {}).get("total") !=
                len((action20_execution.get(label) or {}).get("events") or [])
                for label, total in expected_action20_exec.items()) or \
            (action20_registers.get("bookkeeping") or {}).get("a0") != \
            0xFFFFFFFF or \
            (action20_registers.get("bookkeeping") or {}).get("a1") != \
            THUD_ATTACK_CONTACT_RECORD:
        gaps.append("Thud action-20 attribution accounting/registers changed")
    visual = document.get("action20_visual_presentation_control") or {}
    natural_visual = visual.get("natural") or {}
    suppressed_visual = visual.get("countdown_zero") or {}
    suppression_mutation = suppressed_visual.get("mutation") or {}
    visual_diff = visual.get("frame_diff") or {}
    visual_metrics = visual_diff.get("metrics") or {}
    visual_pick = visual.get("natural_object_pick") or {}
    visual_draw = visual_pick.get("draw_call") or {}
    visual_geometry = visual_pick.get("geometry") or {}
    visual_texture = visual_pick.get("texture") or {}
    visual_source = visual_pick.get("source") or {}
    visual_origin_keys = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                          "main_ram_sha256", "registers_sha256")
    if visual.get("single_field") != f"0x{GRAIN_PHASE_VALUE:08x}" or \
            visual.get("target_movie_frame") != ACTION20_VISUAL_FRAME or \
            suppression_mutation.get("main_ram_differences") != [{
                "address": f"0x{GRAIN_PHASE_VALUE:08x}",
                "before": 9, "after": 0}] or \
            suppression_mutation.get("main_ram_difference_count") != 1 or \
            any((natural_visual.get("before") or {}).get(key) !=
                (suppressed_visual.get("before") or {}).get(key)
                for key in visual_origin_keys) or \
            visual.get("endpoint_alignment") != {
                "emulator_frame_equal": True, "movie_frame_equal": True,
                "sp_equal": True, "pc_equal": False,
                "suppressed_minus_natural_cycle": 0,
                "natural_pc": "0x800104b8", "suppressed_pc": "0x80010508"} or \
            ((natural_visual.get("after") or {}).get(
                "thud_attack_contact") or {}).get("action_id") != 20 or \
            ((suppressed_visual.get("after") or {}).get(
                "thud_attack_contact") or {}).get("action_id") == 20 or \
            visual_diff.get("changed") is not True or \
            visual_diff.get("pixelCount") != 593 or \
            visual_diff.get("boundingBoxes") != [{
                "x": 449, "y": 159, "width": 28, "height": 35}] or \
            visual_metrics.get("changedPixels") != 593 or \
            visual_metrics.get("totalPixels") != 488000 or \
            visual_metrics.get("maxDifference") != 251 or \
            visual_pick.get("hit") is not True or \
            visual_draw.get("primitiveType") != "quad" or \
            visual_draw.get("commandId") != 44 or \
            visual_geometry.get("screenRect") != {
                "x": 799, "y": 322, "width": 20, "height": 13} or \
            visual_texture.get("bpp") != "4bpp" or \
            visual_source.get("dmaSource") != "0x001cf3d4":
        gaps.append("Thud action-20 visual presentation control changed")
    renderer = document.get("action20_renderer_attribution") or {}
    renderer_access = renderer.get("access") or {}
    renderer_body = renderer.get("renderer") or {}
    packet = renderer.get("picked_packet") or {}
    renderer_reads = renderer_body.get("slot17_reads") or []
    packet_writes = packet.get("writes") or []
    observed_renderer_pcs = sorted(
        str(row.get("instruction_pc", "")).lower() for row in renderer_reads)
    expected_renderer_pcs = sorted(
        f"0x{pc:08x}" for pc in list(CONTACT_RENDERER_READ_PCS) * 2)
    expected_packet_map = {
        "0x801cf3d4": "0x80014a30", "0x801cf3dc": "0x80014a34",
        "0x801cf3e4": "0x80014a38", "0x801cf3ec": "0x80014a3c",
        "0x801cf3d0": "0x80014a40", "0x801cf3e8": "0x80014a44",
        "0x801cf3d8": "0x80014a58", "0x801cf3e0": "0x80014a6c",
    }
    if renderer_access.get("total") != 118 or \
            renderer_access.get("truncated") is not False or \
            renderer_access.get("read_watch_hits") != 102 or \
            renderer_access.get("packet_watch_hits") != 16 or \
            renderer_body.get("address") != \
            f"0x{CONTACT_RENDERER_ADDRESS:08x}" or \
            renderer_body.get("read_total") != 22 or \
            renderer_body.get("read_frames") != [327716, 327722] or \
            observed_renderer_pcs != expected_renderer_pcs or \
            packet.get("write_total") != 16 or len(packet_writes) != 16 or \
            packet.get("first_packet_address_to_instruction_pc") != \
            expected_packet_map:
        gaps.append("Thud action-20 renderer/packet attribution changed")
    runtime = document.get("runtime_overlay_identity") or {}
    region = runtime.get("runtime_region_a") or {}
    staged = runtime.get("staged_candidates") or {}
    writer_slice = runtime.get("exact_writer_slice") or {}
    reset_owner = runtime.get("reset_owner_slice") or {}
    post_restore_owner = runtime.get("post_restore_attack_slice") or {}
    arena_owner = runtime.get("arena_transform_collision_slice") or {}
    observed_transfers = {
        address: (row.get("mnemonic"), row.get("target"))
        for address, row in (reset_owner.get("control_transfers") or {}).items()}
    observed_arena_transfers = {
        address: (row.get("mnemonic"), row.get("target"))
        for address, row in (arena_owner.get("control_transfers") or {}).items()}
    observed_post_restore_transfers = {
        address: (row.get("mnemonic"), row.get("target"))
        for address, row in (
            post_restore_owner.get("control_transfers") or {}).items()}
    if region.get("length_3500_sha256") == staged.get("LEVEL08/LEVEL.BIN") or \
            region.get("length_4064_sha256") == staged.get("LEVEL08/LEVEL1.BIN") or \
            writer_slice.get("sha256") != WRITER_SLICE_SHA256 or \
            reset_owner.get("sha256") != RESET_OWNER_SHA256 or \
            reset_owner.get("instruction_count") != RESET_OWNER_LENGTH // 4 or \
            (reset_owner.get("disassembly_validation") or {}).get(
                "exact_runtime_bytes_reconstructed") is not True or \
            (reset_owner.get("disassembly_validation") or {}).get(
                "packed_little_endian_sha256") != RESET_OWNER_SHA256 or \
            observed_transfers != RESET_CONTROL_TRANSFERS or \
            post_restore_owner.get("sha256") != \
            POST_RESTORE_CONTINUATION_SHA256 or \
            post_restore_owner.get("instruction_count") != \
            POST_RESTORE_CONTINUATION_LENGTH // 4 or \
            (post_restore_owner.get("disassembly_validation") or {}).get(
                "exact_runtime_bytes_reconstructed") is not True or \
            (post_restore_owner.get("disassembly_validation") or {}).get(
                "packed_little_endian_sha256") != \
            POST_RESTORE_CONTINUATION_SHA256 or \
            observed_post_restore_transfers != \
            POST_RESTORE_CONTROL_TRANSFERS or \
            arena_owner.get("sha256") != ARENA_BLOCK_SHA256 or \
            arena_owner.get("instruction_count") != ARENA_BLOCK_LENGTH // 4 or \
            (arena_owner.get("disassembly_validation") or {}).get(
                "exact_runtime_bytes_reconstructed") is not True or \
            (arena_owner.get("disassembly_validation") or {}).get(
                "packed_little_endian_sha256") != ARENA_BLOCK_SHA256 or \
            observed_arena_transfers != ARENA_CONTROL_TRANSFERS:
        gaps.append("Thud save-owned runtime overlay classification changed")
    natural_cycles = document.get("natural_phase_cycles") or []
    try:
        _validate_natural_phase_cycles(natural_cycles)
    except (KeyError, TypeError, SystemExit) as error:
        gaps.append(f"Thud natural phase cycles changed: {error}")
    for row in natural_cycles:
        for side in ("damage", "restore"):
            trace = (row.get(side) or {}).get("cycle_neutral_trace") or {}
            if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                    any(item.get("truncated") for item in
                        trace.get("coverage") or []):
                gaps.append(
                    f"Thud phase cycle {row.get('cycle')} {side} trace changed")
    trajectory_attribution = document.get("trajectory_writer_attribution") or {}
    trajectory_pcs = {
        window: {str(event.get("instruction_pc", "")).lower()
                 for event in ((trajectory_attribution.get(window) or {}).get(
                     "events") or [])}
        for window in ("early_window", "late_window")}
    expected_trajectory_pcs = {
        "early_window": {
            PATH_DECREMENT_STORE, TARGET_X_STORE, TARGET_Z_STORE,
            MOTION_TIMER_STORE, HEADING_STORE, ACTOR_EARLY_X_STORE,
            ACTOR_EARLY_Z_STORE, ACTOR_TARGET_X_READER, ACTOR_TARGET_Z_READER},
        "late_window": {
            PATH_DECREMENT_STORE, TARGET_X_STORE, TARGET_Z_STORE,
            MOTION_TIMER_STORE, HEADING_STORE, ACTOR_LATE_X_STORE,
            ACTOR_LATE_Z_STORE},
    }
    for window, pcs in expected_trajectory_pcs.items():
        if {f"0x{pc:08x}" for pc in pcs} - trajectory_pcs[window]:
            gaps.append(f"Thud {window} trajectory attribution changed")
        accounting = (trajectory_attribution.get(window) or {}).get(
            "accounting") or {}
        if accounting.get("truncated") is not False or \
                accounting.get("total") != accounting.get("returned"):
            gaps.append(f"Thud {window} trajectory accounting changed")
    trajectory = document.get("trajectory_control") or {}
    if trajectory.get("observed_end_deltas") != {
            "actor_position": [4096, 0, 0],
            "actor_motion_target_x_unknown_30_z": [4096, 0, 4096],
            "path_coordinate": 4096,
            "player_position": [0, 0, 0]}:
        gaps.append("Thud path-coordinate causal deltas changed")
    trajectory_mid = document.get("trajectory_mid_boundary") or {}
    trajectory_mid_snapshot = trajectory_mid.get("snapshot") or {}
    if ((trajectory_mid_snapshot.get("phase_reset") or {}).get(
            "arena_position"),
            (trajectory_mid_snapshot.get("actor") or {}).get("position"),
            (trajectory_mid_snapshot.get("actor") or {}).get(
                "motion_target_x_unknown_30_z")) != \
            (61984, [102808, -39328, -3845], [61984, -608, 61984]) or \
            ((trajectory_mid.get("cycle_neutral_trace") or {}).get(
                "comparison") or {}).get("cycle_neutral") is not True:
        gaps.append("Thud passive trajectory-mid boundary changed")
    trajectory_control = trajectory.get("control") or {}
    trajectory_mutation = trajectory.get("mutation") or {}
    if ((trajectory_control.get("end") or {}).get("actor") or {}).get(
            "position") != [532, -39328, -1551] or \
            ((trajectory_control.get("end") or {}).get("actor") or {}).get(
                "motion_target_x_unknown_30_z") != [-40416, -608, -40416] or \
            any(((trajectory_control.get("retired") or {}).get("actor") or {}).get(
                    key) != value for key, value in
                (("hp", 0), ("flags", "0x0055"))) or \
            any(((trajectory_mutation.get("retired") or {}).get("actor") or {}).get(
                    key) != value for key, value in
                (("hp", 0), ("flags", "0x0055"))):
        gaps.append("Thud path-coordinate control endpoints changed")
    branch_attribution = document.get("phase_branch_attribution") or {}
    branch_expectations = {
        "first_reset": {
            "hp_equal_gate": (("v0", "v1"), (50, 48)),
            "negative_arena_gate": (
                ("v0", "v1"),
                (ARENA_NEGATIVE_SENTINEL, ARENA_NEGATIVE_SENTINEL)),
            "counter_eight_gate": (("v0", "v1"), (1, 8)),
            "grain_threshold_gate": (("v0", "v1"), (1, 0)),
        },
        "eighth_reset": {
            "positive_arena_gate": (
                ("v0", "v1"),
                (ARENA_POSITIVE_SENTINEL, ARENA_POSITIVE_SENTINEL)),
            "counter_eight_gate": (("v0", "v1"), (8, 8)),
            "target_minus_four_gate": (("v0", "v1"), (46, 48)),
        },
    }
    for window, expectations in branch_expectations.items():
        events = (branch_attribution.get(window) or {}).get("events") or {}
        for label, (registers, wanted) in expectations.items():
            rows = (events.get(label) or {}).get("events") or []
            observed = {tuple(int((event.get("regs") or {})[register], 0)
                              for register in registers) for event in rows}
            if wanted not in observed:
                gaps.append(f"Thud {window} {label} attribution changed")
    writer = document.get("writer_attribution") or {}
    accounting = writer.get("accounting") or {}
    decisive = writer.get("decisive_writers") or {}
    expected_writers = {
        "hp_zero": ("0x800b4528", 50, 0),
        "active_clear": ("0x8004d270", 0x4055, 0x55),
        "live_table_clear": ("0x8004d43c", ACTOR, 0),
    }
    for label, wanted in expected_writers.items():
        row = decisive.get(label) or {}
        if (str(row.get("instruction_pc", "")).lower(), row.get("value"),
                row.get("new_value")) != wanted:
            gaps.append(f"Thud decisive {label} writer changed")
    if accounting.get("truncated") is not False or \
            accounting.get("returned") != accounting.get("total"):
        gaps.append("Thud access-log accounting changed")
    transient_writer = document.get("transient_writer_attribution") or {}
    transient_decisive = transient_writer.get("decisive_writers") or {}
    if ((str((transient_decisive.get("damage") or {}).get(
                "instruction_pc", "")).lower(),
         (transient_decisive.get("damage") or {}).get("value"),
         (transient_decisive.get("damage") or {}).get("new_value")) !=
            ("0x800590e4", 50, 48) or
        (str((transient_decisive.get("restore") or {}).get(
                "instruction_pc", "")).lower(),
         (transient_decisive.get("restore") or {}).get("value"),
         (transient_decisive.get("restore") or {}).get("new_value")) !=
            ("0x800b3ed0", 48, 50)):
        gaps.append("Thud transient decisive writers changed")
    controls = document.get("causal_controls") or {}
    control_outcomes = {
        "damage_class": [(((controls.get("damage_class") or {}).get(side) or {}).get(
            "after") or {}).get("actor", {}).get("hp")
            for side in ("control", "mutation")],
        "overlay_target_hp": [(((controls.get("overlay_target_hp") or {}).get(side)
            or {}).get("after") or {}).get("actor", {}).get("hp")
            for side in ("control", "mutation")],
    }
    if control_outcomes != {"damage_class": [48, 46],
                            "overlay_target_hp": [50, 49]}:
        gaps.append(f"Thud one-field controls changed: {control_outcomes}")
    phase_control_outcomes = {
        key: list(value) for key, value in (((controls.get(
            "phase_reset_guards") or {}).get("observed_outcomes") or {}).items())}
    expected_phase_control_outcomes = {
        "control": [50, 50, 1, 9, 0, 0, 0],
        "target_equals_hp": [48, 48, 0, 0, 0, 0, 0],
        "hp_floor": [20, 50, 0, 0, 0, 0, 0],
        "arena_sentinel": [50, 50, 0, 0, 0, 0, 0],
        "counter_eight": [50, 50, 8, 0, 1, 32, 149],
        "grain_formula": [50, 50, 1, 8, 0, 0, 0],
    }
    master_outcomes = {
        key: list(value) for key, value in (((controls.get(
            "master_timer_gate") or {}).get("observed_outcomes") or {}).items())}
    if phase_control_outcomes != expected_phase_control_outcomes:
        gaps.append(f"Thud phase controls changed: {phase_control_outcomes}")
    if master_outcomes != {"control": [50, 105, 1, 0],
                           "mutation": [48, 0, 0, 1]}:
        gaps.append(f"Thud master/timer control changed: {master_outcomes}")
    summary = derive_summary(document)
    if document.get("summary") != summary or summary != {
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
            "phase_restore_frames": list(PHASE_RESTORE_FRAMES),
            "phase_counter_transition": [0, 8],
            "arena_master_transition": [0, 1],
            "phase_path_coordinate_transition": [156704, 4294926880],
            "trajectory_control_delta": {
                "path_coordinate": 4096,
                "actor_position": [4096, 0, 0],
                "actor_motion_target_x_unknown_30_z": [4096, 0, 4096],
                "player_position": [0, 0, 0],
            },
            "phase_guard_outcomes": expected_phase_control_outcomes,
            "natural_hp_transition": [50, 0],
            "hp_zero_instruction_pc": "0x800b4528",
            "retire_instruction_pcs": ["0x8004d270", "0x8004d43c"],
            "retired_movie_frame": 3902, "scene_exit": [14, 0],
            "event_program_19_decode_complete": True,
            "runtime_overlay_exactly_staged": False,
            "reset_owner_instruction_count": 153,
            "post_restore_continuation_instruction_count": 77,
            "arena_block_instruction_count": 196,
            "d18_or_f09_completed": 0}:
        gaps.append("Thud derived summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned Thud process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixture = build_fixture_census()
    static = build_static_census()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.readU32",
        "debugger.writeU8", "debugger.writeU16",
        "debugger.writeU32", "debugger.disassemble",
        "debugger.getRegisters", "debugger.clearBreakpoints",
        "emulator.getMediaInfo", "emulator.getStateInfo",
        "emulator.advanceFrames",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status", "movie.clear",
        "movie.store", "movie.branch", "movie.editFrame", "movie.activate",
        "movie.remove",
        "accessLog.addWatch", "accessLog.run", "accessLog.get", "accessLog.clear",
        "execTrace.addWatch", "execTrace.run", "execTrace.get", "execTrace.clear",
        "gpu.captureFrameSnapshot", "gpu.diffCurrentFrame",
        "gpu.clearFrameSnapshot", "gpu.pickObject",
        "spu.trace.start", "spu.trace.stop", "spu.trace.clear",
        "spu.events.get",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks Thud methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, ROOT / SAVE_REL, media)
    movie_path = ROOT / MOVIE_REL
    _start_movie(client, movie_path)
    runtime_overlay = _runtime_overlay_identity(client)
    launch_boundaries = {
        str(frame): _trace_boundary(client, movie_path, frame)
        for frame in (LAUNCH_PRE_FRAME, LAUNCH_POST_FRAME)}
    post_restore_attack_boundaries = {
        str(frame): _post_restore_attack_boundary(client, movie_path, frame)
        for frame in (POST_RESTORE_ATTACK_PRE_FRAME,
                      POST_RESTORE_ATTACK_POST_FRAME)}
    action20_effect_boundaries = _action20_effect_boundaries(client, movie_path)
    frames = (START_FRAME, PRE_DEFEAT_FRAME, HP_ZERO_FRAME, RETIRE_FRAME,
              SCENE_EXIT_FRAME, FINAL_FRAME)
    boundaries = {str(frame): _trace_boundary(client, movie_path, frame)
                  for frame in frames}
    transient_frames = (TRANSIENT_PRE_FRAME, TRANSIENT_DAMAGE_FRAME,
                        TRANSIENT_HOLD_FRAME, TRANSIENT_RESET_FRAME)
    transient_boundaries = {
        str(frame): _trace_boundary(client, movie_path, frame)
        for frame in transient_frames}
    arena_damage_boundaries = {
        str(frame): _trace_boundary(client, movie_path, frame)
        for frame in (ARENA_DAMAGE_PRE_FRAME, ARENA_DAMAGE_POST_FRAME)}
    natural_phase_cycles = _natural_phase_cycles(
        client, movie_path, transient_boundaries)
    trajectory_mid_boundary = _trace_boundary(
        client, movie_path, TRAJECTORY_MID_FRAME)
    launch_writers = _launch_writer_attribution(client, movie_path)
    post_restore_attack_attribution = _post_restore_attack_attribution(
        client, movie_path)
    post_restore_attack_control = _post_restore_attack_control(
        client, movie_path)
    action20_sound_attribution = _action20_sound_attribution(
        client, movie_path)
    action20_sound_control = _action20_sound_control(client, movie_path)
    action20_effect_attribution = _action20_effect_attribution(
        client, movie_path)
    action20_effect_control = _action20_effect_control(client, movie_path)
    action20_visual_presentation_control = \
        _action20_visual_presentation_control(client, movie_path)
    action20_renderer_attribution = _action20_renderer_attribution(
        client, movie_path)
    launch_control = _launch_input_counterfactual(client, movie_path)
    transient_writers = _transient_writer_attribution(client, movie_path)
    arena_damage_attribution = _arena_damage_attribution(client, movie_path)
    arena_damage_control = _arena_damage_control(client, movie_path)
    phase_branches = _phase_branch_attribution(client, movie_path)
    controls = _causal_controls(client, movie_path)
    trajectory_writers = _trajectory_writer_attribution(client, movie_path)
    trajectory_control = _trajectory_control(client, movie_path)
    writers = _writer_attribution(client, movie_path)
    base._cleanup(client)
    final_media = verified_media_identity(
        client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_thud_defeat.py",
        anchor={
            "type": "existing state-anchored Thud natural-defeat recording",
            "save": SAVE_REL, "movie": MOVIE_REL,
            "fixture_sha256": {SAVE_REL: SAVE_SHA256, MOVIE_REL: MOVIE_SHA256},
            "state_inspections": [inspection], "media_identity": media,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "movie_format": "v1 all digital buttons",
            "boundaries": {"pre_defeat": PRE_DEFEAT_FRAME,
                           "launch_pre": LAUNCH_PRE_FRAME,
                           "launch_post": LAUNCH_POST_FRAME,
                           "transient_pre": TRANSIENT_PRE_FRAME,
                           "transient_damage": TRANSIENT_DAMAGE_FRAME,
                           "transient_hold": TRANSIENT_HOLD_FRAME,
                           "transient_reset": TRANSIENT_RESET_FRAME,
                           "post_restore_attack_pre": (
                               POST_RESTORE_ATTACK_PRE_FRAME),
                           "post_restore_attack_post": (
                               POST_RESTORE_ATTACK_POST_FRAME),
                           "action20_effect_pre": ACTION20_EFFECT_PRE_FRAME,
                           "action20_effect_post": ACTION20_EFFECT_POST_FRAME,
                           "action20_visual": ACTION20_VISUAL_FRAME,
                           "action20_sound": ACTION20_VISUAL_FRAME,
                           "action20_natural_active": (
                               ACTION20_NATURAL_ACTIVE_FRAME),
                           "action20_natural_retire": (
                               ACTION20_NATURAL_RETIRE_FRAME),
                           "arena_damage_pre": ARENA_DAMAGE_PRE_FRAME,
                           "arena_damage_post": ARENA_DAMAGE_POST_FRAME,
                           "phase_damage": list(PHASE_DAMAGE_FRAMES),
                           "phase_restore": list(PHASE_RESTORE_FRAMES),
                           "trajectory_start": TRAJECTORY_START_FRAME,
                           "trajectory_mid": TRAJECTORY_MID_FRAME,
                           "trajectory_end": TRAJECTORY_END_FRAME,
                           "hp_zero": HP_ZERO_FRAME, "retire": RETIRE_FRAME,
                           "scene_exit": SCENE_EXIT_FRAME, "final": FINAL_FRAME},
            "trace_mode": (
                "fresh passive movie.traceToFrame control/instrumented pairs; "
                "separate re-armed accessLog/execTrace attribution replay and "
                "fresh matched input/one-field control branches; in-memory "
                "framebuffer diff/object pick with no retained image bytes; "
                "post-load SPU trace re-arm plus exact launch-call NOP control"),
        })
    document = {
        "_comment": (
            "Active D18/F09 evidence: one recorded player-projectile launch, "
            "one Thud-overlay action-20 contact-object launch and controlled "
            "native grain-pickup effect plus one causally isolated textured "
            "billboard presentation and one exact negative-cue SPU key-on "
            "sequence, "
            "one causal six-row rolling-boulder contact, eight pristine Thud "
            "contact-damage/overlay-reset cycles, the counter-8 actor-target "
            "path, defeat, retirement and scene exit. General audio mapping, "
            "other boss attacks, full arena ownership/completion and the "
            "complete hit curve remain open."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-thud-lifecycle/9",
        "campaign_state": "active_partial",
        "fixture_census": fixture, "static_census": static,
        "runtime_overlay_identity": runtime_overlay,
        "natural_launch_boundaries": launch_boundaries,
        "launch_writer_attribution": launch_writers,
        "launch_input_counterfactual": launch_control,
        "post_restore_attack_boundaries": post_restore_attack_boundaries,
        "post_restore_attack_attribution": post_restore_attack_attribution,
        "post_restore_attack_control": post_restore_attack_control,
        "action20_sound_attribution": action20_sound_attribution,
        "action20_sound_control": action20_sound_control,
        "action20_effect_boundaries": action20_effect_boundaries,
        "action20_effect_attribution": action20_effect_attribution,
        "action20_effect_control": action20_effect_control,
        "action20_visual_presentation_control": (
            action20_visual_presentation_control),
        "action20_renderer_attribution": action20_renderer_attribution,
        "transient_damage_boundaries": transient_boundaries,
        "natural_arena_damage_boundaries": arena_damage_boundaries,
        "natural_phase_cycles": natural_phase_cycles,
        "transient_writer_attribution": transient_writers,
        "arena_damage_attribution": arena_damage_attribution,
        "arena_damage_control": arena_damage_control,
        "phase_branch_attribution": phase_branches,
        "causal_controls": controls,
        "trajectory_mid_boundary": trajectory_mid_boundary,
        "trajectory_writer_attribution": trajectory_writers,
        "trajectory_control": trajectory_control,
        "natural_defeat_boundaries": boundaries,
        "writer_attribution": writers,
        "bounded_interpretation": {
            "observation": (
                "Recorded Square input precedes a slot-26 action-2 allocation "
                "and the first contact. Eight actor-id-36 HP 50->48->50 cycles "
                "advance the phase counter 0->8 and alternate exact signed path "
                "sentinels. Separately, one six-row save-owned transform loop "
                "places an object close enough to the player to call the resident "
                "transition/damage initiator and lower health 3->2; transient "
                "visual context shows a rolling-boulder overlap. The eighth "
                "restore enters master state 1. After the first restore, the "
                "same actor-owned overlay naturally allocates slot 17 as "
                "action 20, TTL 200 and class 128. Its natural trajectory keeps "
                "grain at zero and retires without collection. At target 980 "
                "the natural frame contains one small textured quad that is "
                "absent when the source allocation is suppressed. The same "
                "launch calls play_sound with cue -14 and the actor-position "
                "pointer; its bounded SPU window contains four early key-ons at "
                "sample start 0x00009E10. The counter-8 path "
                "coordinate then decrements by 2560 per update and is copied to "
                "actor X/Z motion targets. Later HP reaches 0, the active bit/"
                "live-table slot clear, and scene 14 exits."),
            "inference": (
                "Scene graph and actor identity bind this lifecycle to Thud in "
                "Stage 9 Bug Bar. Resident caller 0x8004724C classifies the "
                "observed action-2 allocation as a player throw without assigning "
                "a berry color from the sampled selector. The save-owned caller "
                "0x800B3FF0 and actor register bind the separate action-20 "
                "contact-object launch to Thud. Static pristine dispatch bytes "
                "and live registers bind its controlled contact to the resident "
                "player-proximity walker and grain handler. The pristine "
                "0x80014844 renderer and exact RAM packet source bind its "
                "observed presentation as a contact-record textured billboard. "
                "The save-owned 0x800B3FFC caller and pristine resident "
                "play_sound slice bind its separate negative-cue request."),
            "causal_confirmation": (
                "The Square-cleared branch suppresses the allocation, damage and "
                "first reset. Writer traces bind 50->48 to 0x800590E4 and 48->50 to "
                "0x800B3ED0. Equal-frame one-field controls change class 0->127 "
                "and HP 48->46, target 50->49 and restored HP 50->49, and bind "
                "the target-equality, signed HP floor, exact arena sentinel, "
                "counter-8, grain threshold and master/timer guards. Point traces "
                "capture matching branch operands; passive coverage independently "
                "contains the writers at fixed frames. Zeroing only the winning "
                "arena row's squared-distance threshold prevents health 3->2 at "
                "an equal-cycle/position endpoint. A +4096 path-coordinate "
                "control yields exact +4096 actor X/Z targets and final actor X. "
                "Zeroing only the derived countdown at target 970 suppresses "
                "the natural action-20 allocation at target 971. Enlarging only "
                "slot 17 radius_add from 100 to 6000 at target 972 makes the "
                "native action-20 branch increment grain 0->1, store state 16 "
                "and set its active gate to 1 at the next frame; the matched "
                "control keeps grain 0, state 24 and decrements 200->199. A "
                "separate matched countdown branch removes exactly 593 pixels "
                "in one 28x35 framebuffer box; object picking and complete "
                "interpreter attribution join that natural quad to slot 17 and "
                "its resident packet writer. NOPing only 0x800B3FFC preserves "
                "the action-20 record and gameplay endpoint while reducing the "
                "bounded SPU page 13->7 and removing four early 0x00009E10 "
                "key-ons."),
            "forbidden_claim": (
                "Do not infer a berry color, action-20 damage effect, named "
                "sound asset, waveform, host-speaker drain, texture/model "
                "identity beyond the measured billboard, natural hit frequency, "
                "a monotonic HP curve, complete attack policy, complete rolling-"
                "arena geometry/ownership/completion, unsampled continuation "
                "paths, or D18/F09 completion."),
        },
        "bounded_open_frontier": {
            "attacks_phases": (
                "One player-thrown projectile source/launch and one Thud-owned "
                "action-20 contact-object source/launch, natural miss/retirement "
                "controlled player-proximity grain-pickup path and one causal "
                "textured-billboard presentation are bound. Its negative -14 "
                "play_sound request and one bounded 0x00009E10 SPU key-on "
                "sequence are also causal. Named sound-asset/waveform identity, "
                "host drain, natural-hit frequency, other "
                "variants and complete attack policy remain open."),
            "arena": (
                "One six-row save-owned object-transform/collision branch and "
                "row-4 damage threshold are causal for a visible rolling-boulder "
                "overlap. Counter 8 naturally enters master state 1 with heading "
                "32 and motion timer 149. The boss path coordinate and actor-"
                "motion trajectory are separately causal; complete geometry, "
                "ownership, phase linkage and completion remain open."),
            "damage_curve": (
                "Eight natural action-2/class-0 contacts give -2 and class 127 "
                "gives -4 under intervention. Full berry-power/HP curves remain "
                "open."),
            "reset_policy": (
                "The exact 612-byte save-owned reset-owner front half and its "
                "equality/floor/sentinel/counter/grain/master guards are bound. "
                "The next exact 308-byte continuation slice and one natural "
                "allocator branch are bound; other continuation paths remain open."),
            "lifecycle": (
                "Initialization, re-engagement, retry/checkpoint and persistence "
                "breadth remain open; only natural defeat/retirement/exit is bound."),
            "next_experiment": (
                "Bind another attack or continue from "
                "the causal rolling-boulder row to full geometry, phase linkage "
                "and completion without relabeling the actor path; leave broader "
                "audio identity and lifecycle to E12."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    document["summary"] = derive_summary(document)
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(
            f"retained Thud evidence failed: {gaps}; "
            f"arena_endpoint={arena_damage_control['endpoint_alignment']}; "
            f"action20_endpoint={action20_effect_control['endpoint_alignment']}")
    write_live_evidence(OUTPUT, document)
    print("[thud-defeat] action-20 sound/billboard/grain lifecycle bound")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        if (Path(args.config_dir) / "instance.pid").is_file():
            try:
                finish_run(
                    args, generator="tools/phase4_thud_defeat.py",
                    anchor={"type": "aborted before retained Thud evidence"},
                    timing={})
            except BaseException as cleanup_error:
                print(
                    f"owned Thud cleanup also failed: {cleanup_error}",
                    file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
