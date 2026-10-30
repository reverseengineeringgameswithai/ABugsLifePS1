#!/usr/bin/env python3
"""Build the static Phase-4 grain/harvester ownership frontier."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys

import phase4_common as common


ROOT = common.ROOT
CONFIG_PATH = ROOT / "config/phase4_collectibles_frontier.yaml"
OUTPUT = ROOT / "analysis/phase4_collectibles_frontier.json"
CONFIG = common.load_yaml(CONFIG_PATH)
EXTERNAL_INDEX = Path(CONFIG["external_index"]["path"])

SEMANTIC_SOURCES = (
    "config/semantic_state.yaml",
    "src_re/grain_harvester_equipment_80051db4.c",
    "src_re/grain_contact_convergence_8005a308.c",
    "src_re/source3f_dispatch_80053814.c",
    "src_re/contact_alloc_80059e44.c",
    "src_re/pickup_handlers_80054288_80054554.c",
)


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_hash(path: Path, expected: str) -> None:
    require(path.is_file(), f"missing input: {path}")
    observed = common.sha256(path)
    require(observed == expected, f"input hash mismatch: {path}: {observed}")


def exe_offset(va: int) -> int:
    return va - int(CONFIG["inputs"]["executable"]["load_base"])


def exe_word(executable: bytes, va: int) -> int:
    return struct.unpack_from("<I", executable, exe_offset(va))[0]


def exe_slice(executable: bytes, start: int, end: int) -> bytes:
    require(start < end, f"invalid executable slice: {start:#x}..{end:#x}")
    return executable[exe_offset(start):exe_offset(end)]


def actor(frame: dict, actor_id: int) -> dict:
    matches = [row for row in frame["actors"] if row["id"] == actor_id]
    require(len(matches) == 1, (
        f"frame {frame['movie_frame']} has {len(matches)} actor {actor_id} rows"))
    return matches[0]


def level_actor_rows(census: dict, actor_id: int) -> list[dict]:
    rows = []
    for level_name, level in census["levels"].items():
        matches = [
            row for row in level.get("actor_records") or []
            if int(row["id"]) == actor_id
        ]
        if matches:
            require(len(matches) == 1, (
                f"{level_name} has duplicate actor {actor_id} rows"))
            row = matches[0]
            rows.append({
                "level": level_name,
                "save": level["save"],
                "save_sha256": level["save_sha256"],
                "slot": row["index"],
                "address": row["addr"],
                "xyz": row["xyz"],
                "source": row["pointer_fields"].get("+0x80"),
                "vm_ip": row["pointer_fields"].get("+0x70"),
            })
    return rows


def c13_offline(index: dict, census: dict) -> dict:
    movie = CONFIG["anchors"][2]["movie"]["path"]
    matches = [row for row in index["capsules"] if row["movie"] == movie]
    require(len(matches) == 1, f"external index has {len(matches)} C13 capsules")
    capsule = matches[0]
    frames = capsule["frames"]
    require(len(frames) == 618, f"C13 frame-record count is {len(frames)}, expected 618")
    actor_id = int(CONFIG["harvester"]["actor_id"])
    bit = int(CONFIG["harvester"]["powerup_bit"])
    first_bit_frame = next(
        frame for frame in frames if int(frame["player"]["powerup_flags"]) & bit)
    pickup_frame = int(CONFIG["harvester"]["observed_pickup_frame"])
    require(first_bit_frame["movie_frame"] == pickup_frame, (
        f"first bit-0x80 frame is {first_bit_frame['movie_frame']}, expected {pickup_frame}"))
    previous = next(
        frame for frame in frames
        if frame["movie_frame"] == pickup_frame - 1)
    require(not (int(previous["player"]["powerup_flags"]) & bit),
            "harvester bit was already set before the retained pickup boundary")

    observed_ids = sorted({
        int(row["id"]) for frame in frames for row in frame["actors"]
    })
    signature_matches = []
    for level_name, level in census["levels"].items():
        ids = sorted(int(value) for value in level["actor_id_histogram"])
        if ids == observed_ids:
            signature_matches.append(level_name)

    attached = []
    for frame in frames:
        if frame["movie_frame"] < pickup_frame:
            continue
        player = frame["player"]
        owned = actor(frame, actor_id)
        attached.append({
            "movie_frame": frame["movie_frame"],
            "delta": [
                owned[axis] - player[axis] for axis in ("x", "y", "z")
            ],
            "powerup_flags": player["powerup_flags"],
        })
    deltas = sorted({tuple(row["delta"]) for row in attached})
    require(deltas == [tuple(CONFIG["harvester"]["observed_follow_delta"])],
            f"C13 post-pickup actor/player deltas differ: {deltas}")
    require(all(int(row["powerup_flags"]) & bit for row in attached),
            "C13 harvester bit does not persist through the retained suffix")

    first = frames[0]
    first_actor = actor(first, actor_id)
    pickup_actor = actor(first_bit_frame, actor_id)
    return {
        "movie": movie,
        "records": len(frames),
        "actor_ids_observed": observed_ids,
        "unique_level_signature_matches": signature_matches,
        "frame_0": {
            "player_xyz": [first["player"][axis] for axis in ("x", "y", "z")],
            "player_powerup_flags": first["player"]["powerup_flags"],
            "actor": {
                key: first_actor[key]
                for key in ("slot", "address", "id", "x", "y", "z", "vm_ip", "source")
            },
        },
        "pickup_boundary": {
            "movie_frame": pickup_frame,
            "powerup_flags_before": previous["player"]["powerup_flags"],
            "powerup_flags_after": first_bit_frame["player"]["powerup_flags"],
            "actor_xyz": [pickup_actor[axis] for axis in ("x", "y", "z")],
            "player_xyz": [
                first_bit_frame["player"][axis] for axis in ("x", "y", "z")
            ],
            "actor_player_delta": attached[0]["delta"],
        },
        "attached_suffix": {
            "first_movie_frame": attached[0]["movie_frame"],
            "last_movie_frame": attached[-1]["movie_frame"],
            "records": len(attached),
            "distinct_actor_player_deltas": [list(row) for row in deltas],
            "powerup_bit_persistent": True,
        },
    }


def decode_metadata(row: bytes) -> dict:
    return {
        "row_hex": row.hex(),
        "action_id": struct.unpack_from("<H", row, 0x00)[0],
        "active_gate": struct.unpack_from("<H", row, 0x02)[0],
        "phase": struct.unpack_from("<h", row, 0x04)[0],
        "radius_add": struct.unpack_from("<h", row, 0x08)[0],
        "field_2a": struct.unpack_from("<h", row, 0x0A)[0],
        "state": struct.unpack_from("<h", row, 0x0C)[0],
        "selector": row[0x0F],
        "flags": row[0x10],
    }


def build() -> dict:
    require(CONFIG["schema"] == "abl-phase4-collectibles-frontier-source/1",
            "collectibles frontier config schema mismatch")
    for spec in CONFIG["inputs"].values():
        check_hash(ROOT / spec["path"], spec["sha256"])
    check_hash(EXTERNAL_INDEX, CONFIG["external_index"]["sha256"])
    require(EXTERNAL_INDEX.stat().st_size == int(CONFIG["external_index"]["bytes"]),
            "external collectibles index size changed")
    for anchor in CONFIG["anchors"]:
        check_hash(ROOT / anchor["movie"]["path"], anchor["movie"]["sha256"])
        check_hash(
            ROOT / anchor["start_state"]["path"], anchor["start_state"]["sha256"])

    executable_path = ROOT / CONFIG["inputs"]["executable"]["path"]
    executable = executable_path.read_bytes()
    census = common.load_json(ROOT / CONFIG["inputs"]["actor_census"]["path"])
    offline = common.load_json(ROOT / CONFIG["inputs"]["offline_summary"]["path"])
    index = common.load_json(EXTERNAL_INDEX)
    require(index["schema"] == CONFIG["external_index"]["schema"],
            "external collectibles index schema mismatch")

    slices = []
    for expected in CONFIG["expected_slices"]:
        start, end = int(expected["start"]), int(expected["end"])
        data = exe_slice(executable, start, end)
        observed = hashlib.sha256(data).hexdigest()
        require(observed == expected["sha256"], (
            f"executable slice {start:#x}..{end:#x} changed: {observed}"))
        slices.append({
            "start": f"0x{start:08X}",
            "end": f"0x{end:08X}",
            "bytes": len(data),
            "sha256": observed,
        })

    words = {}
    for pc, expected in CONFIG["expected_words"].items():
        pc_int, expected_int = int(pc), int(expected)
        observed = exe_word(executable, pc_int)
        require(observed == expected_int, (
            f"instruction {pc_int:#x} changed: {observed:#010x}"))
        words[f"0x{pc_int:08X}"] = f"0x{observed:08X}"

    harvester = CONFIG["harvester"]
    actor_id = int(harvester["actor_id"])
    # The actor-model dispatch range is IDs 1..41, indexed as actor_id - 1.
    jump_va = int(harvester["actor_jump_table"]) + (actor_id - 1) * 4
    jump_target = exe_word(executable, jump_va)
    require(jump_target == int(harvester["actor_case"]),
            f"actor {actor_id} jump target changed: {jump_target:#x}")
    string_va = int(harvester["asset_string_va"])
    string_offset = exe_offset(string_va)
    expected_string = harvester["asset_string"].encode() + b"\0"
    require(executable[string_offset:string_offset + len(expected_string)] == expected_string,
            "harvester asset string changed")

    metadata_va = (
        int(CONFIG["grain_source"]["metadata_table"])
        + int(CONFIG["grain_source"]["ctor_type"]) * 0x14)
    metadata_bytes = exe_slice(executable, metadata_va, metadata_va + 0x14)
    metadata = decode_metadata(metadata_bytes)
    require(metadata["row_hex"] == CONFIG["grain_source"]["metadata_row_hex"],
            "ctor 0x51 metadata row changed")
    for field, expected in CONFIG["grain_source"]["metadata"].items():
        require(metadata[field] == int(expected), (
            f"ctor 0x51 {field} changed: {metadata[field]}"))

    authored = level_actor_rows(census, actor_id)
    require([row["level"] for row in authored] ==
            CONFIG["harvester"]["expected_authored_levels"],
            "actor 35 authored-level set changed")
    require(all(
        row["slot"] == int(harvester["actor_slot"])
        and int(row["address"], 16) == int(harvester["actor_address"])
        for row in authored), "actor 35 is not consistently fixed slot 63")

    c13 = c13_offline(index, census)
    require(c13["unique_level_signature_matches"] == ["stage01_anthill"],
            "C13 actor-ID signature is not unique to stage01")
    stage01 = next(row for row in authored if row["level"] == "stage01_anthill")
    require(c13["frame_0"]["actor"]["id"] == actor_id and
            c13["frame_0"]["actor"]["slot"] == int(harvester["actor_slot"]),
            "C13 frame-0 harvester actor identity changed")
    require(c13["frame_0"]["actor"]["source"] == stage01["source"],
            "C13 actor source does not join the stage01 actor-35 source")

    findings = offline["derived_findings"]
    c01 = findings["C01_grain_pickup"]
    c02 = findings["C02_fifty_grain_reward"]
    c13_summary = findings["C13_grain_harvester"]
    reward = CONFIG["reward_50"]
    require(int(reward["reward_snapshot_address"]) != int(reward["compared_address"]),
            "the fixed grain-50 progress branch unexpectedly became reachable")

    source_dependencies = {
        "frontier_contract": {
            "path": str(CONFIG_PATH.relative_to(ROOT)),
            "sha256": common.sha256(CONFIG_PATH),
        },
        "actor_census": {
            "path": CONFIG["inputs"]["actor_census"]["path"],
            "sha256": common.sha256(
                ROOT / CONFIG["inputs"]["actor_census"]["path"]),
        },
        "offline_summary": {
            "path": CONFIG["inputs"]["offline_summary"]["path"],
            "sha256": common.sha256(
                ROOT / CONFIG["inputs"]["offline_summary"]["path"]),
        },
    }
    for relative in SEMANTIC_SOURCES:
        source_dependencies[Path(relative).stem] = {
            "path": relative,
            "sha256": common.sha256(ROOT / relative),
        }

    document = {
        "_comment": (
            "Bounded non-copyrighted static/offline assertions. External index, "
            "movie, save, asset and executable bytes remain outside this artifact."),
        "schema": "abl-phase4-collectibles-frontier/1",
        "generated": stable_generated(),
        "campaign": {
            "id": CONFIG["campaign_id"],
            "family": CONFIG["family"],
            "rows": CONFIG["selected_rows"],
            "first_unmet_dimension": CONFIG["first_unmet_dimension"],
            "next_lane": CONFIG["next_lane"],
            "dimension_promoted": CONFIG["closure_boundary"]["dimension_promoted"],
        },
        "claim": CONFIG["exact_claim"],
        "falsifier": CONFIG["falsifier"],
        "inputs": {
            "external_index": {
                "path": str(EXTERNAL_INDEX),
                "sha256": common.sha256(EXTERNAL_INDEX),
                "bytes": EXTERNAL_INDEX.stat().st_size,
                "schema": index["schema"],
                "media_class": CONFIG["external_index"]["media_class"],
                "preservation_required": True,
            },
            "executable": {
                "path": CONFIG["inputs"]["executable"]["path"],
                "sha256": common.sha256(executable_path),
            },
            "anchors": CONFIG["anchors"],
            "source_dependencies": source_dependencies,
        },
        "offline_localization": {
            "C01_grain_pickup": {
                "grain_transition": [c01["grain_initial"], c01["grain_final"]],
                "grain_event_frames": c01["grain_event_frames"],
                "effect_signature_per_event": [
                    {
                        "movie_frame": row["movie_frame"],
                        "action_ids": sorted({
                            item.get("action", 4)
                            for item in row["effect_record_resets"]
                        }),
                        "radius_adds": sorted({
                            item.get("radius_add", 100)
                            for item in row["effect_record_resets"]
                        }),
                        "records": len(row["effect_record_resets"]),
                    }
                    for row in c01["grain_events"]
                ],
            },
            "C02_fifty_grain_reward": {
                "grain_transition": [c02["grain_initial"], c02["grain_final"]],
                "grain_event_frames": c02["grain_event_frames"],
                "true_health_transition": [
                    c02["health_initial"], c02["health_final"]],
                "same_frame_spu_ram_changed": c02["grain_events"][0][
                    "correlations"]["spu_ram_changed"],
                "health_display_boundary": c02["health_display_at_grain_boundary"],
            },
            "C13_grain_harvester": c13 | {
                "grain_transition": [
                    c13_summary["grain_initial"], c13_summary["grain_final"]],
                "grain_event_frames": c13_summary["grain_event_frames"],
                "action20_transition_count":
                    c13_summary["action20_transition_count"],
            },
        },
        "static_frontier": {
            "actor_asset_ownership": {
                "actor_id": actor_id,
                "actor_jump_table_entry": f"0x{jump_va:08X}",
                "case_target": f"0x{jump_target:08X}",
                "asset_string": harvester["asset_string"],
                "asset_string_va": f"0x{string_va:08X}",
                "model_sha256": CONFIG["inputs"]["harvester_model"]["sha256"],
                "animation_sha256":
                    CONFIG["inputs"]["harvester_animation"]["sha256"],
                "authored_levels": authored,
            },
            "equip_and_follow": {
                "function": "0x80051DB4..0x80052090",
                "sole_gameplay_caller": "0x8004EFF8",
                "actor_id_gate": actor_id,
                "fixed_actor_slot": int(harvester["actor_slot"]),
                "proximity_radius_argument":
                    int(harvester["pickup_radius_argument"]),
                "powerup_flag": {
                    "address": f"0x{int(harvester['powerup_flag_address']):08X}",
                    "bit": f"0x{int(harvester['powerup_bit']):04X}",
                    "writer": "0x80051EB0",
                },
                "follow_stores": [
                    "0x80051F94", "0x80051F9C", "0x80051FA4",
                    "0x80051FAC", "0x80051FB4", "0x80051FBC",
                    "0x80051FC4", "0x80051FCC", "0x80051FD4",
                    "0x80051FDC",
                ],
                "gameplay_update_order": [
                    "harvester_equipment_0x80051DB4",
                    "actor_update_0x8004D224",
                    "contact_update_0x8005A308",
                    "source_dispatch_0x8005CD2C",
                    "contact_walker_0x8005BFBC",
                ],
            },
            "grain_attraction_source": {
                "kind": int(CONFIG["grain_source"]["kind"]),
                "powerup_bit_gate": f"0x{int(harvester['powerup_bit']):04X}",
                "squared_distance_max":
                    int(CONFIG["grain_source"]["squared_distance_max"]),
                "constructor": "contact_alloc_0x80059E44",
                "constructor_type": int(CONFIG["grain_source"]["ctor_type"]),
                "constructor_stack_arg":
                    int(CONFIG["grain_source"]["constructor_stack_arg"]),
                "post_constructor_target_store": {
                    "pc": "0x80053C58", "value": -1},
                "metadata": metadata,
            },
            "grain_convergence": {
                "function": "0x8005A308..0x8005B12C",
                "record_count": 64,
                "precondition": (
                    "flags bit 0x08, active_gate > 0 and target +0x10 == -1"),
                "horizontal_target": "player X/Z",
                "heading_law": (
                    "delta=(atan2(playerX-recordX, playerZ-recordZ)-heading)"
                    "&0xFFF; add delta>>2 when delta<0x800, otherwise add "
                    "(0x800-delta)>>2"),
                "vertical_law": (
                    "recordY -= clamp((recordY + 0x2000 - playerY) >> 3, "
                    "-0x400, +0x400)"),
                "horizontal_velocity": (
                    "sin(heading)>>3 and sin(heading+0x400)>>3, then integrate X/Z"),
                "source_squared_distance_max":
                    int(CONFIG["grain_source"]["squared_distance_max"]),
                "pickup_walker_radius": {
                    "base": int(CONFIG["grain_source"][
                        "native_pickup_base_radius"]),
                    "radius_add": metadata["radius_add"],
                    "total": int(CONFIG["grain_source"][
                        "native_pickup_total_radius"]),
                },
            },
            "fifty_grain_reward": {
                "grain_increment_writer": "0x80054F9C",
                "target_compare": {
                    "pc": "0x8005500C",
                    "value": int(reward["grain_target"]),
                },
                "reward_event_call": "0x80055060",
                "progress_branch": {
                    "comparison_pc": "0x80055078",
                    "left_address":
                        f"0x{int(reward['reward_snapshot_address']):08X}",
                    "right_address":
                        f"0x{int(reward['compared_address']):08X}",
                    "reachable": bool(reward["progress_branch_reachable"]),
                },
                "reachable_health_store": {
                    "pc": "0x80055124",
                    "address": f"0x{int(reward['health_address']):08X}",
                    "value": int(reward["health_value"]),
                },
            },
            "executable_slices": slices,
            "instruction_words": words,
        },
        "closure_boundary": CONFIG["closure_boundary"],
        "named_residuals": [
            {
                "boundary": "original oracle",
                "intersects_dimension": True,
                "reason": (
                    "All selected movies are pristine save-start anchors, not "
                    "cold-boot reproductions."),
            },
            {
                "boundary": "causal controls",
                "intersects_dimension": True,
                "reason": (
                    "No same-anchor bit-0x80 denial or source-radius control was "
                    "executed in this static iteration."),
            },
            {
                "boundary": "lifecycle and breadth",
                "intersects_dimension": True,
                "reason": (
                    "Denial, capacity, reset, death/respawn, unload/reload and "
                    "persistence paths remain open."),
            },
        ],
    }
    gaps = evidence_gaps(document)
    document["errors"] = gaps
    document["valid"] = not gaps
    return document


def evidence_gaps(document: dict) -> list[str]:
    gaps = []
    campaign = document.get("campaign") or {}
    if campaign.get("rows") != CONFIG["selected_rows"]:
        gaps.append("selected row set changed")
    if campaign.get("dimension_promoted") is not False:
        gaps.append("static frontier must not promote a roadmap dimension")
    offline = document.get("offline_localization") or {}
    if offline.get("C01_grain_pickup", {}).get("grain_event_frames") != [196, 540]:
        gaps.append("C01 grain boundaries changed")
    c02 = offline.get("C02_fifty_grain_reward", {})
    if c02.get("grain_transition") != [49, 50]:
        gaps.append("C02 49-to-50 boundary changed")
    c13 = offline.get("C13_grain_harvester", {})
    if c13.get("unique_level_signature_matches") != ["stage01_anthill"]:
        gaps.append("C13 stage ownership join changed")
    if c13.get("pickup_boundary", {}).get("actor_player_delta") != [0, 192, 0]:
        gaps.append("C13 harvester follow delta changed")
    static = document.get("static_frontier") or {}
    asset = static.get("actor_asset_ownership") or {}
    if asset.get("actor_id") != 35 or asset.get("case_target") != "0x8005E17C":
        gaps.append("actor-35 FLIKHARV dispatch changed")
    source = static.get("grain_attraction_source") or {}
    if source.get("squared_distance_max") != 0x15F8F:
        gaps.append("grain attraction source radius changed")
    metadata = source.get("metadata") or {}
    if (metadata.get("action_id"), metadata.get("active_gate"),
            metadata.get("radius_add"), metadata.get("state"),
            metadata.get("flags")) != (20, 200, 100, 22, 0xEA):
        gaps.append("ctor-0x51 metadata changed")
    convergence = static.get("grain_convergence") or {}
    if convergence.get("pickup_walker_radius", {}).get("total") != 400:
        gaps.append("grain pickup walker radius changed")
    reward = static.get("fifty_grain_reward") or {}
    if reward.get("progress_branch", {}).get("reachable") is not False:
        gaps.append("grain-50 progress branch reachability changed")
    if reward.get("reachable_health_store", {}).get("value") != 4:
        gaps.append("grain-50 health store changed")
    if not document.get("closure_boundary", {}).get("missing"):
        gaps.append("open closure boundary was erased")
    return gaps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--external-index", type=Path)
    return parser.parse_args()


def main() -> int:
    global EXTERNAL_INDEX
    args = parse_args()
    if args.external_index is not None:
        EXTERNAL_INDEX = args.external_index.resolve()
    try:
        document = build()
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: collectibles frontier: {exc}")
        return 1
    data = render(document)
    if args.write:
        OUTPUT.write_bytes(data)
        print(
            "PASS: collectibles frontier "
            f"rows={len(document['campaign']['rows'])} "
            f"dimension_promoted={str(document['campaign']['dimension_promoted']).lower()}")
        return 0
    if not OUTPUT.is_file():
        print(f"FAIL: missing generated artifact: {OUTPUT}")
        return 1
    if OUTPUT.read_bytes() != data:
        print(f"FAIL: stale generated artifact: {OUTPUT}")
        return 1
    print(
        "PASS: collectibles frontier "
        f"rows={len(document['campaign']['rows'])} "
        f"dimension_promoted={str(document['campaign']['dimension_promoted']).lower()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
