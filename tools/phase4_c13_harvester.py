#!/usr/bin/env python3
"""Regenerate the capsule-backed Phase-4 C13 grain-harvester evidence.

This tool is intentionally offline.  It consumes the centrally preserved,
hash-pinned C13 trace capsule, its exact reader snapshot, the operator annotation
sidecar, and the pristine staged executable.  It does not launch DuckStation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "analysis" / "phase4_c13_harvester.json"
LIVE_OUTPUT = ROOT / "analysis" / "phase4_c13_harvester_live.json"
CAPSULE_INDEX = ROOT / "analysis" / "phase4_trace_capsule_set.json"
CONTRACT = ROOT / "config" / "phase4_c13_harvester.yaml"
ANNOTATIONS = ROOT / "movies" / "Phase4" / "c13_GRAIN_HARVESTER.annotations.yaml"
MOVIE = ROOT / "movies" / "Phase4" / "c13_GRAIN_HARVESTER.movie.json"
START_STATE = ROOT / "movies" / "Phase4" / "c13_GRAIN_HARVESTER.movie.sav"
PRISTINE_EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"

PLAYER_BASE = 0x800A6500
HARVESTER_STATE = 0x800A657E
POWER_FLAGS = 0x800A6590
GRAIN_COUNT = 0x800A65A1
TYPE3F_PTR = 0x80096E9C
CONTACT_BASE = 0x800B0D18
CONTACT_STRIDE = 0x38
CONTACT_SLOTS = 64

KIND_GRAIN = 0x14
GRAIN_CTOR_ACTION = 0x14
GRAIN_CTOR_TTL = 200
GRAIN_CTOR_FLAGS = 0xEA
GRAIN_DISTANCE_GATE = 0x15F8F
CONSUMED_Y = -0x80000000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_capsule_reader(path: Path):
    """Load the exact externally preserved reader without importing host HEAD."""
    spec = importlib.util.spec_from_file_location("abl_c13_trace_capsule_reader", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load capsule reader: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def ram_offset(address: int) -> int:
    return address & 0x1FFFFF


def u8(ram: bytes | bytearray, address: int) -> int:
    return ram[ram_offset(address)]


def u16(ram: bytes | bytearray, address: int) -> int:
    return struct.unpack_from("<H", ram, ram_offset(address))[0]


def s16(ram: bytes | bytearray, address: int) -> int:
    return struct.unpack_from("<h", ram, ram_offset(address))[0]


def u32(ram: bytes | bytearray, address: int) -> int:
    return struct.unpack_from("<I", ram, ram_offset(address))[0]


def s32(ram: bytes | bytearray, address: int) -> int:
    return struct.unpack_from("<i", ram, ram_offset(address))[0]


def pristine_word(exe: bytes, address: int) -> int:
    offset = 0x800 + address - 0x80010000
    if offset < 0 or offset + 4 > len(exe):
        raise ValueError(f"address outside pristine executable: {address:#x}")
    return struct.unpack_from("<I", exe, offset)[0]


def annotation_by_id(doc: dict[str, Any], annotation_id: str) -> dict[str, Any]:
    return next(row for row in doc["annotations"] if row["id"] == annotation_id)


def grain_metric(ram: bytes, source_xyz: tuple[int, int, int]) -> int:
    player = (
        s32(ram, PLAYER_BASE + 0x00) >> 5,
        (s32(ram, PLAYER_BASE + 0x04) >> 5) - 0xE6,
        s32(ram, PLAYER_BASE + 0x08) >> 5,
    )
    delta = tuple((player[i] - source_xyz[i]) >> 3 for i in range(3))
    return sum(value * value for value in delta)


def contact_signature(ram: bytes, slot: int) -> tuple[int, int, int]:
    base = CONTACT_BASE + slot * CONTACT_STRIDE
    return u16(ram, base + 0x20), s16(ram, base + 0x22), u8(ram, base + 0x33)


def contact_xyz(ram: bytes, slot: int) -> tuple[int, int, int]:
    base = CONTACT_BASE + slot * CONTACT_STRIDE
    return tuple(s32(ram, base + offset) for offset in (0, 4, 8))


def find_index_row(index: dict[str, Any]) -> dict[str, Any]:
    return next(
        row for row in index["capsules"]
        if row["movie"] == "movies/Phase4/c13_GRAIN_HARVESTER.movie.json"
    )


def build(
    *,
    capsule_directory: Path | None = None,
    reader_path: Path | None = None,
) -> dict[str, Any]:
    index = json.loads(CAPSULE_INDEX.read_text())
    index_row = find_index_row(index)
    capsule_directory = (
        capsule_directory.resolve()
        if capsule_directory
        else Path(index_row["capsule_directory"]).resolve()
    )
    reader_decl = index["offline_reader_snapshot"]
    reader_path = (
        reader_path.resolve()
        if reader_path
        else Path(reader_decl["absolute_path"]).resolve()
    )

    annotations = yaml.safe_load(ANNOTATIONS.read_text())
    contract = yaml.safe_load(CONTRACT.read_text())
    movie = json.loads(MOVIE.read_text())
    live = json.loads(LIVE_OUTPUT.read_text())
    manifest_path = capsule_directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    input_checks = {
        "movie_sha256_matches_annotation":
            sha256(MOVIE) == annotations["movie_sha256"],
        "movie_sha256_matches_capsule":
            sha256(MOVIE) == manifest["movie"]["sha256"] == index_row["movie_sha256"],
        "start_state_sha256_matches_annotation":
            sha256(START_STATE) == annotations["start_state_sha256"],
        "start_state_sha256_matches_capsule":
            sha256(START_STATE) == manifest["start_state"]["sha256"]
            == index_row["start_state"]["sha256"],
        "capsule_manifest_sha256_matches_index":
            sha256(manifest_path) == index_row["capsule_manifest_sha256"],
        "capsule_complete": manifest["complete"] is True,
        "capsule_control_clean": not manifest["control"]["mismatches"],
        "capsule_pristine_serial":
            manifest["authority"]["expected_serial"] == "SCUS-94288",
        "reader_sha256_matches_index":
            sha256(reader_path) == reader_decl["sha256"],
        "live_complement_schema":
            live["schema"] == "abl-phase4-c13-harvester-live-v1",
        "live_complement_movie_sha256":
            live["inputs"]["movie"]["sha256"] == sha256(MOVIE),
        "live_complement_state_sha256":
            live["inputs"]["start_state"]["sha256"] == sha256(START_STATE),
        "live_complement_annotation_sha256":
            live["inputs"]["annotations"]["sha256"] == sha256(ANNOTATIONS),
        "live_complement_pristine_media":
            live["authority"]["media_identity"]["hash_verification"]
            ["pristine_verified"] is True,
        "live_complement_checks":
            all(live["computed_checks"].values()),
        "machine_contract_row":
            contract["row"] == "C13_grain_harvester",
        "machine_contract_status":
            contract["status"] == "partial",
        "machine_contract_equip_state":
            contract["machine_contract"]["equip_state"]["address"]
            == HARVESTER_STATE
            and contract["machine_contract"]["equip_state"]["width"] == "s16",
        "machine_contract_powerup_bit":
            contract["machine_contract"]["powerup_flags"]["address"]
            == POWER_FLAGS
            and contract["machine_contract"]["powerup_flags"]["harvester_bit"]
            == 0x80,
        "machine_contract_level01_actor":
            contract["machine_contract"]["level01_harvester_actor"]["address"]
            == 0x800A1DFC
            and contract["machine_contract"]["level01_harvester_actor"]
            ["required_id"] == 0x23,
        "machine_contract_grain_gate":
            contract["machine_contract"]["grain_source"]
            ["distance_metric_inclusive_max"] == GRAIN_DISTANCE_GATE
            and contract["machine_contract"]["grain_source"]
            ["contact_ctor_selector"] == 0x51,
    }
    if not all(input_checks.values()):
        failures = [name for name, value in input_checks.items() if not value]
        raise RuntimeError(f"C13 evidence input checks failed: {failures}")

    reader = load_capsule_reader(reader_path)
    capsule = reader.Capsule(capsule_directory)
    frames: dict[int, dict[str, Any]] = {}
    ordered_frames: list[int] = []
    for frame in capsule.frames():
        ordered_frames.append(frame.movie_frame)
        frames[frame.movie_frame] = {
            "emulator_frame": frame.frame,
            "cycle": frame.cycle,
            "pc": frame.pc,
            "ram": bytes(frame.state["ram"]),
        }

    if ordered_frames != list(range(0, 618)):
        raise RuntimeError(
            f"unexpected C13 capsule movie-frame sequence: "
            f"{ordered_frames[:2]}..{ordered_frames[-2:]}"
        )

    equip_input = annotation_by_id(annotations, "equip_input")
    equip_frame = equip_input["frame"]
    movie_frames = {row["frame"]: row["ports"]["0"] for row in movie["frames"]}
    square_edge = (
        not movie_frames[equip_frame - 1]["square"]
        and movie_frames[equip_frame]["square"]
    )

    first_harvester_bit = next(
        frame for frame in ordered_frames
        if u16(frames[frame]["ram"], POWER_FLAGS) & 0x80
    )
    first_harvester_state = next(
        frame for frame in ordered_frames
        if s16(frames[frame]["ram"], HARVESTER_STATE) == 1
    )
    equip_samples = []
    for frame in (0, 79, 80, 82, 83, 87, 168, 511, 616, 617):
        ram = frames[frame]["ram"]
        equip_samples.append({
            "movie_frame": frame,
            "emulator_frame": frames[frame]["emulator_frame"],
            "cycle": frames[frame]["cycle"],
            "harvester_state_s16": s16(ram, HARVESTER_STATE),
            "power_flags_u16": u16(ram, POWER_FLAGS),
            "harvester_bit_0x80": bool(u16(ram, POWER_FLAGS) & 0x80),
        })

    initial_ram = frames[0]["ram"]
    type3f = u32(initial_ram, TYPE3F_PTR)
    type3f_count = u16(initial_ram, type3f)
    grain_sources = []
    for index_number in range(type3f_count):
        base = type3f + 4 + index_number * 0x10
        if u8(initial_ram, base + 0x0C) == KIND_GRAIN:
            grain_sources.append({
                "index": index_number,
                "address": base,
                "xyz_file_units": tuple(s32(initial_ram, base + off) for off in (0, 4, 8)),
            })

    source_events = []
    prior_y = {
        row["index"]: row["xyz_file_units"][1]
        for row in grain_sources
    }
    sources_by_index = {row["index"]: row for row in grain_sources}
    for frame in ordered_frames[1:]:
        ram = frames[frame]["ram"]
        before = frames[frame - 1]["ram"]
        for index_number, old_y in list(prior_y.items()):
            source = sources_by_index[index_number]
            y = s32(ram, source["address"] + 4)
            if y == old_y:
                continue
            prior_y[index_number] = y
            if y != CONSUMED_Y:
                continue

            new_slots = []
            expected_xyz = tuple(value << 5 for value in source["xyz_file_units"])
            for slot in range(CONTACT_SLOTS):
                signature = contact_signature(ram, slot)
                prior_signature = contact_signature(before, slot)
                if (
                    signature == (GRAIN_CTOR_ACTION, GRAIN_CTOR_TTL, GRAIN_CTOR_FLAGS)
                    and prior_signature != signature
                    and contact_xyz(ram, slot) == expected_xyz
                ):
                    new_slots.append(slot)
            if len(new_slots) != 1:
                raise RuntimeError(
                    f"grain source {index_number} at frame {frame} maps to "
                    f"{len(new_slots)} matching ctor slots"
                )
            source_events.append({
                "movie_frame": frame,
                "emulator_frame": frames[frame]["emulator_frame"],
                "source_index": index_number,
                "source_address": f"0x{source['address']:08X}",
                "source_xyz_file_units": list(source["xyz_file_units"]),
                "metric_previous_frame": grain_metric(
                    before, source["xyz_file_units"]
                ),
                "metric_activation_frame": grain_metric(
                    ram, source["xyz_file_units"]
                ),
                "contact_slot": new_slots[0],
                "contact_record": f"0x{CONTACT_BASE + new_slots[0] * CONTACT_STRIDE:08X}",
                "contact_action_id": GRAIN_CTOR_ACTION,
                "contact_initial_ttl": GRAIN_CTOR_TTL,
                "contact_initial_flags": GRAIN_CTOR_FLAGS,
            })

    grain_count_events = []
    previous_count = u8(initial_ram, GRAIN_COUNT)
    for frame in ordered_frames[1:]:
        count = u8(frames[frame]["ram"], GRAIN_COUNT)
        if count != previous_count:
            grain_count_events.append({
                "movie_frame": frame,
                "before": previous_count,
                "after": count,
            })
            previous_count = count

    for source_event, count_event in zip(source_events, grain_count_events, strict=True):
        slot = source_event["contact_slot"]
        contact = CONTACT_BASE + slot * CONTACT_STRIDE
        frame = count_event["movie_frame"]
        ram = frames[frame]["ram"]
        source_event["collection"] = {
            **count_event,
            "contact_xyz": list(contact_xyz(ram, slot)),
            "contact_state_0x2c": s16(ram, contact + 0x2C),
        }

    visual_first = annotation_by_id(annotations, "first_grain_attraction")["frames"]
    visual_last = annotation_by_id(annotations, "last_grain_attraction")["nominal_frame"]
    movie_end = annotation_by_id(annotations, "movie_end_equipped")["frame"]

    static_words_expected = {
        "0x80051DB4": 0x3C028008,  # current controller word base
        "0x80051DB8": 0x84422488,  # lh v0, 0x80082488
        "0x80051DCC": 0x30428000,  # Square held
        "0x80051DDC": 0x84422380,  # prior controller word
        "0x80051DE4": 0x30428000,  # Square was not previously held
        "0x80051DEC": 0x24020023,  # required actor id 0x23
        "0x80051DF4": 0x26311DFC,  # actor record 0x800A1DFC
        "0x80051E24": 0x94426590,  # read power/harvester flags
        "0x80051E2C": 0x30420080,  # test bit 0x80
        "0x80051EA0": 0xA602FFFC,  # harvester state := 1
        "0x80051EA8": 0x34630080,  # set bit 0x80
        "0x80051EB0": 0xA4236590,  # store power/harvester flags
        "0x80051F60": 0xA422657E,  # active path maintains state
        "0x80053BEC": 0x94426590,  # grain dispatcher reads flags
        "0x80053BF4": 0x30420080,  # grain dispatcher tests bit 0x80
        "0x80053C14": 0x34425F8F,  # completes 0x15F8F metric gate
        "0x80053C20": 0x24070051,  # ctor 0x51
        "0x80053C40": 0x0C016791,  # contact allocator
        "0x80053C4C": 0xAE430000,  # source Y := consumed sentinel
        "0x8004B158": 0x94426590,  # actor resolver reads power flags
        "0x8004B160": 0x30420080,  # harvester enemy-contact gate
        "0x8004B200": 0x10400002,  # skip special HP when attack bit absent
        "0x8004B204": 0x240203E6,  # delayed-destroy sentinel 998
        "0x8004B208": 0xA622006E,  # actor HP := 998
    }
    exe = PRISTINE_EXE.read_bytes()
    static_words_actual = {
        address: pristine_word(exe, int(address, 16))
        for address in static_words_expected
    }
    static_checks = {
        address: static_words_actual[address] == expected
        for address, expected in static_words_expected.items()
    }
    if not all(static_checks.values()):
        failures = [name for name, value in static_checks.items() if not value]
        raise RuntimeError(f"C13 pristine static anchors drifted: {failures}")

    computed_checks = {
        "square_has_fresh_edge_at_80": square_edge and equip_frame == 80,
        "harvester_state_and_bit_rise_together":
            first_harvester_state == first_harvester_bit == 83,
        "unequipped_through_annotated_approach":
            all(
                not (u16(frames[frame]["ram"], POWER_FLAGS) & 0x80)
                and s16(frames[frame]["ram"], HARVESTER_STATE) == 0
                for frame in range(0, 80)
            ),
        "equipped_through_movie_end":
            all(
                u16(frames[frame]["ram"], POWER_FLAGS) & 0x80
                and s16(frames[frame]["ram"], HARVESTER_STATE) == 1
                for frame in range(83, movie_end + 2)
            ),
        "all_source_events_cross_exact_native_gate":
            len(source_events) == 9
            and all(
                row["metric_previous_frame"] > GRAIN_DISTANCE_GATE
                and row["metric_activation_frame"] <= GRAIN_DISTANCE_GATE
                for row in source_events
            ),
        "source_events_construct_exact_grain_contacts":
            len(source_events) == 9
            and all(
                row["contact_action_id"] == GRAIN_CTOR_ACTION
                and row["contact_initial_ttl"] == GRAIN_CTOR_TTL
                and row["contact_initial_flags"] == GRAIN_CTOR_FLAGS
                for row in source_events
            ),
        "nine_contacts_increment_grain_count_once_each":
            [(row["before"], row["after"]) for row in grain_count_events]
            == [(value, value + 1) for value in range(9)],
        "operator_first_visual_window_follows_engine_activation":
            source_events[0]["movie_frame"] < visual_first[0]
            and visual_first[0] - source_events[0]["movie_frame"] <= 8,
        "operator_last_visual_frame_follows_engine_activation":
            source_events[-1]["movie_frame"] < visual_last
            and visual_last - source_events[-1]["movie_frame"] <= 8,
    }
    if not all(computed_checks.values()):
        failures = [name for name, value in computed_checks.items() if not value]
        raise RuntimeError(f"C13 computed checks failed: {failures}")

    return {
        "_comment": (
            "Phase-4 C13 offline evidence. Verdicts are regenerated from the "
            "hash-pinned pristine trace capsule and pristine executable; they are "
            "not trusted from a retained high-level passes field."
        ),
        "schema": "abl-phase4-c13-harvester-v1",
        "generated": str(annotations["authority"]["recorded"]),
        "status": "partial",
        "authority": {
            "media": "hash-verified pristine retail SCUS-94288",
            "allmods_role": "none; ALLMODS was not consumed",
            "capsule_kind": "frame-boundary RAM/VRAM/SPU/register evidence",
            "limitations": [
                "The retained movie does not contain a disengage edge.",
                "The retained movie ends before the operator-led bee contact.",
                "Frame-boundary deltas cannot attribute an exact writer instruction.",
                "The retained live complement supplies the behavioral Cross and bee "
                "controls. Exact Cross and steering PCs are owned by the C static-ASM "
                "continuation in analysis/phase4_c13_asm_static.json.",
            ],
        },
        "inputs": {
            "annotation": {
                "path": str(ANNOTATIONS.relative_to(ROOT)),
                "sha256": sha256(ANNOTATIONS),
            },
            "machine_contract": {
                "path": str(CONTRACT.relative_to(ROOT)),
                "sha256": sha256(CONTRACT),
                "schema_version": contract["schema_version"],
            },
            "movie": {
                "path": str(MOVIE.relative_to(ROOT)),
                "sha256": sha256(MOVIE),
            },
            "start_state": {
                "path": str(START_STATE.relative_to(ROOT)),
                "sha256": sha256(START_STATE),
                "media_class": "external game-derived fixture; never commit",
            },
            "capsule": {
                "directory": str(capsule_directory),
                "manifest_sha256": sha256(manifest_path),
                "tree_sha256": index_row["capsule_tree_sha256"],
                "preservation_index": str(CAPSULE_INDEX.relative_to(ROOT)),
            },
            "offline_reader": {
                "path": str(reader_path),
                "sha256": sha256(reader_path),
            },
            "pristine_executable": {
                "path": str(PRISTINE_EXE.relative_to(ROOT)),
                "sha256": sha256(PRISTINE_EXE),
            },
            "live_complement": {
                "path": str(LIVE_OUTPUT.relative_to(ROOT)),
                "sha256": sha256(LIVE_OUTPUT),
                "schema": live["schema"],
                "generator_sha256": live["run_provenance"]["generator_sha256"],
                "duckstation_binary_sha256":
                    live["run_provenance"]["source_identity"]["binary"]["sha256"],
            },
            "checks": input_checks,
        },
        "equip": {
            "input_frame": equip_frame,
            "square_fresh_edge": square_edge,
            "state_address": f"0x{HARVESTER_STATE:08X}",
            "power_flags_address": f"0x{POWER_FLAGS:08X}",
            "harvester_bit": "0x0080",
            "first_state_one_frame": first_harvester_state,
            "first_bit_set_frame": first_harvester_bit,
            "actor_record": "0x800A1DFC",
            "required_actor_id": 0x23,
            "samples": equip_samples,
        },
        "grain_attraction": {
            "source_record": {
                "pointer_global": f"0x{TYPE3F_PTR:08X}",
                "runtime_pointer": f"0x{type3f:08X}",
                "entry_count": type3f_count,
                "grain_kind": f"0x{KIND_GRAIN:02X}",
                "grain_entries": len(grain_sources),
                "entry_stride": "0x10",
                "consumed_y": f"0x{CONSUMED_Y & 0xFFFFFFFF:08X}",
            },
            "activation_metric": {
                "expression": (
                    "sum((((player_file_xyz_with_y_bias - source_xyz) >> 3)^2))"
                ),
                "player_y_bias_file_units": -0xE6,
                "inclusive_max": GRAIN_DISTANCE_GATE,
            },
            "source_events": source_events,
            "grain_count_address": f"0x{GRAIN_COUNT:08X}",
            "grain_count_events": grain_count_events,
            "initial_grain_count": u8(initial_ram, GRAIN_COUNT),
            "final_grain_count": u8(frames[617]["ram"], GRAIN_COUNT),
        },
        "pristine_static_contract": {
            "executable_sha256": sha256(PRISTINE_EXE),
            "words": {
                address: {
                    "expected": f"0x{static_words_expected[address]:08X}",
                    "actual": f"0x{static_words_actual[address]:08X}",
                    "matches": static_checks[address],
                }
                for address in static_words_expected
            },
            "interpretation": [
                "0x80051DB4..0x80052090 is the harvester enter/active updater, not SFX glue.",
                "Entry requires a fresh Square edge, actor id 0x23 at 0x800A1DFC, grounded proximity, and idle gates.",
                "Entry writes harvester state 0x800A657E := 1 and sets 0x800A6590 bit 0x80.",
                "FUNC_80053814 consumes eligible kind-0x14 source entries and constructs ctor-0x51 contact records only while bit 0x80 is set and the exact 0x15F8F metric passes.",
                "FUNC_8004ABF4 reads the same bit at 0x8004B158/0x8004B160; "
                "its special contact branch writes HP 998 at 0x8004B208.",
                "Cross clears bit 0x80 at 0x8004A94C; once 0x80051F60 stops maintaining "
                "state 1, the normal positive-slot tick stores 1-1 at 0x80048654.",
                "The grain dispatcher stores target -1 at 0x80053C58. Ctor flags 0xEA "
                "select the homing path, whose Y/X/Z position writes are "
                "0x8005A4C8/0x8005A548/0x8005A56C.",
                "Grain collection reaches the shared SFX manager at 0x80054F80 and "
                "increments 0x800A65A1 at 0x80054F9C.",
            ],
        },
        "computed_checks": computed_checks,
        "conclusions": [
            {
                "claim": (
                    "0x800A6590 bit 0x80 is the harvester-equipped/grain-attraction "
                    "enable bit in this pristine LEVEL01 fixture."
                ),
                "confidence": "confirmed",
                "basis": (
                    "fresh Square edge -> bit/state transition; pristine static enter "
                    "writer; exact grain-dispatch reader; nine source/contact/count chains"
                ),
            },
            {
                "claim": (
                    "0x800A657E value 1 is maintained throughout the equipped interval."
                ),
                "confidence": "confirmed_for_retained_fixture",
                "basis": "frame-boundary capsule plus pristine stores at 0x80051EA0/0x80051F60",
            },
            {
                "claim": (
                    "The retained pass attracts nine of LEVEL01's 50 authored grains. "
                    "Each source crosses the exact native metric, becomes a ctor-0x51 "
                    "contact, and increments the grain counter once."
                ),
                "confidence": "confirmed",
                "basis": "source sentinel, ctor signature/coordinates, and counter events",
            },
            {
                "claim": (
                    "Cross disengages the harvester: 0x800A657E changes 1->0 and "
                    "0x800A6590 bit 0x80 clears."
                ),
                "confidence": "confirmed_for_retained_fixture",
                "basis": (
                    "unmodified shared movie-end anchor plus an uninstrumented Cross "
                    "continuation in analysis/phase4_c13_harvester_live.json"
                ),
            },
            {
                "claim": (
                    "Remaining equipped permanently retires the LEVEL01 id-13 bee, "
                    "whereas immediate Cross disengagement leaves the same record "
                    "alive at the matched +136/+222-frame checkpoints."
                ),
                "confidence": "confirmed_for_level01_bee",
                "basis": (
                    "paired pristine continuations from one transient anchor; HP "
                    "4->998->retired versus HP 4 and live-table retention"
                ),
            },
            {
                "claim": (
                    "Ctor-0x51 grain contacts target the player and use the shared "
                    "homing updater; exact Y/X/Z writers are 0x8005A4C8, "
                    "0x8005A548, and 0x8005A56C."
                ),
                "confidence": "confirmed_static_with_capsule_correlation",
                "basis": (
                    "C scan of all hand ASM plus pristine instruction words and nine "
                    "capsule-confirmed ctor records in analysis/phase4_c13_asm_static.json"
                ),
            },
            {
                "claim": (
                    "Cross disengagement is a two-owner chain: 0x8004A94C clears "
                    "the harvester bit, then 0x80048654 decrements the no-longer-"
                    "maintained positive slot from 1 to 0."
                ),
                "confidence": "confirmed_static_plus_behavioral_control",
                "basis": (
                    "whole-ASM writer census, pristine words, and the retained "
                    "uninstrumented Cross continuation"
                ),
            },
        ],
        "remaining": {
            "requires_isolated_live_run": [
                "Behavioral breadth is retained for only one of six statically applicable harvester placements; collect additional Interpreter evidence only if the shared pointer frontier is first closed or reviewed-bounded.",
                "Capacity saturation, pause/resume persistence, and exact GPU/SPU attribution remain named live domains for a future strict-closure campaign."
            ],
            "deferred_low_return_breadth": [
                "exhaustive all-level harvester availability survey",
                "exhaustive animation/asset identity and save-load persistence survey",
                "enemy-family fixture matrix beyond the structurally generic resolver gate",
            ],
            "escalation_rule": (
                "Request a new Interpreter movie only for a named enemy-family, level, "
                "or persistence behavioral control; no movie is required for current "
                "high-value C13 closure."
            ),
        },
    }


def render(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capsule", type=Path)
    parser.add_argument("--reader", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write and args.check:
        parser.error("--write and --check are mutually exclusive")

    doc = build(capsule_directory=args.capsule, reader_path=args.reader)
    rendered = render(doc)
    if args.write:
        args.output.write_text(rendered)
    elif args.check:
        if not args.output.is_file() or args.output.read_text() != rendered:
            print("C13 harvester artifact is missing or stale", file=sys.stderr)
            return 1
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
