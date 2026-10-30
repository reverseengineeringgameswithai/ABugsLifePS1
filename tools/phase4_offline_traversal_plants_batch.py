#!/usr/bin/env python3
"""Build the external cross-movie index for the traversal-plant batch."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys

import phase4_common as common
import phase4_offline_contact_batch as frame_index
import phase4_offline_seed_lifecycle_batch as seed_index


QUEUE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
OUTPUT = common.ROOT / "analysis/phase4_offline_traversal_plants_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_traversal_plants_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELECTION_ROWS = {
    row["row_id"]: row for row in CONFIGURATION["selection_snapshot"]["rows"]
}
HANDLERS = {key: int(value) for key, value in CONFIGURATION["handler_blocks"].items()}
SELF_ARTIFACT = "analysis/phase4_offline_traversal_plants_batch.json"
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()
OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL"))).resolve()

PLAYER_BASE = 0x0A6500
PLAYER_SIZE = 0xB0
ACTOR_BASE = 0x09FD80
ACTOR_STRIDE = 0x84
ACTOR_COUNT = 64
SEED_ACTOR_ID = 11
PLANT_BASE = 0x090BF0
PLANT_STRIDE = 0x30
PLANT_COUNT = 20
EQUIPPED_BERRY = 0x0A6597


def stable_generated(path: Path) -> str:
    if path.is_file():
        try:
            value = json.loads(path.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def movie_file(logical_path: str) -> Path:
    path = Path(logical_path)
    if path.is_absolute() or not path.parts or path.parts[0] != "movies":
        raise ValueError(f"movie path is not centrally rooted: {logical_path}")
    return OPERATOR_ROOT / path


def intersects(runs: list[tuple[int, bytes]], offset: int, length: int) -> bool:
    end = offset + length
    return any(start < end and start + len(data) > offset for start, data in runs)


def plant_slots(image: bytearray) -> list[dict]:
    rows = []
    for slot in range(PLANT_COUNT):
        base = PLANT_BASE + slot * PLANT_STRIDE
        rows.append({
            "slot": slot,
            "type": frame_index.u16(image, base),
            "state": frame_index.u16(image, base + 0x02),
            "x": frame_index.s32(image, base + 0x08),
            "y": frame_index.s32(image, base + 0x0C),
            "z": frame_index.s32(image, base + 0x10),
            "lifecycle_phase_raw": frame_index.u8(image, base + 0x2E),
        })
    return rows


def seed_actors(image: bytearray, player: dict) -> list[dict]:
    rows = []
    for slot in range(ACTOR_COUNT):
        base = ACTOR_BASE + slot * ACTOR_STRIDE
        if frame_index.u32(image, base) != SEED_ACTOR_ID:
            continue
        x = frame_index.s32(image, base + 0x04)
        y = frame_index.s32(image, base + 0x08)
        z = frame_index.s32(image, base + 0x0C)
        rows.append({
            "slot": slot,
            "address": f"0x{0x80000000 + base:08x}",
            "x": x,
            "y": y,
            "z": z,
            "velocity_x": frame_index.s32(image, base + 0x1C),
            "velocity_y": frame_index.s32(image, base + 0x20),
            "velocity_z": frame_index.s32(image, base + 0x24),
            "ai_flags": frame_index.u16(image, base + 0x5C),
            "exact_player_attachment": (
                x == player["x"] and z == player["z"]
                and player["y"] - y == 19200),
        })
    return rows


def player_state(image: bytearray) -> dict:
    return {
        "x": frame_index.s32(image, PLAYER_BASE),
        "y": frame_index.s32(image, PLAYER_BASE + 0x04),
        "z": frame_index.s32(image, PLAYER_BASE + 0x08),
        "velocity_y": frame_index.s32(image, PLAYER_BASE + 0x30),
        "state": frame_index.u16(image, PLAYER_BASE + 0x80),
        "grounded": frame_index.u16(image, PLAYER_BASE + 0x82),
    }


def capsule_movie_pin(queue_rows: dict[str, dict], logical_path: str) -> dict:
    pins = []
    for row_id in SELECTED_ROWS:
        pins.extend(item for item in queue_rows[row_id].get("relevant_movies") or []
                    if item["path"] == logical_path)
    if not pins:
        raise ValueError(f"capsule movie has no selected-row central pin: {logical_path}")
    identities = {(item["sha256"], item["bytes"], item["declared_start_state"],
                   item["media_class"]) for item in pins}
    if len(identities) != 1:
        raise ValueError(f"selected rows disagree on movie identity: {logical_path}")
    pin = pins[0]
    path = movie_file(logical_path)
    if not path.is_file() or path.stat().st_size != int(pin["bytes"]):
        raise ValueError(f"centrally declared movie is absent or size-mismatched: {path}")
    if common.sha256(path) != pin["sha256"]:
        raise ValueError(f"centrally declared movie hash mismatch: {path}")
    if not pin.get("central_pin_current") or not pin.get("declared_start_state"):
        raise ValueError(f"movie central declaration is not current/complete: {path}")
    return pin


def source_errors(queue: dict, capsules: dict) -> tuple[list[str], list[dict], dict[str, list[str]]]:
    errors = []
    expected_schema = "abl-phase4-offline-traversal-plants-batch-source/1"
    if CONFIGURATION.get("schema") != expected_schema:
        errors.append("offline traversal-plant batch source schema is invalid")
    if not queue.get("valid") or queue.get("errors"):
        errors.append("offline opportunity queue is invalid")
    if len(queue.get("rows") or []) != 107:
        errors.append("offline opportunity queue does not contain exactly 107 rows")
    if not capsules.get("complete") or capsules.get("errors"):
        errors.append("trace capsule set is invalid")
    queue_rows = {row["row_id"]: row for row in queue.get("rows") or []}
    movie_to_rows: dict[str, list[str]] = {}
    for row_id in SELECTED_ROWS:
        row = queue_rows.get(row_id)
        if not row:
            errors.append(f"selected row absent from queue: {row_id}")
            continue
        prior = {item.get("artifact") for item in row.get("prior_offline_analysis") or []}
        eligible = row.get("current_completion_state") == "open" and (
            row.get("classification") == "offline_ready"
            or (row.get("classification") == "offline_partial" and SELF_ARTIFACT in prior))
        if not eligible:
            errors.append(f"selected row is not current open batch evidence: {row_id}")
        snapshot = SELECTION_ROWS[row_id]
        if row.get("classification") == "offline_ready":
            rank = (row.get("priority") or {}).get("rank")
            if rank != snapshot["queue_rank"]:
                errors.append(
                    f"selected row rank changed: {row_id} is {rank}, "
                    f"expected {snapshot['queue_rank']}")
        for capsule in row.get("relevant_capsules") or []:
            movie_to_rows.setdefault(capsule["movie"], []).append(row_id)
    expected_ranks = list(range(1, len(SELECTED_ROWS) + 1))
    if [SELECTION_ROWS[row_id]["queue_rank"] for row_id in SELECTED_ROWS] != expected_ranks:
        errors.append("selection snapshot does not retain consecutive ranks 1 through 6")
    capsule_by_movie = {row["movie"]: row for row in capsules.get("capsules") or []}
    selected = []
    for movie in sorted(movie_to_rows):
        if movie not in capsule_by_movie:
            errors.append(f"selected capsule absent from capsule index: {movie}")
        else:
            selected.append(capsule_by_movie[movie])
    if len(selected) != int(CONFIGURATION["expected_unique_capsules"]):
        errors.append(
            f"selected cluster has {len(selected)} unique capsules, expected "
            f"{CONFIGURATION['expected_unique_capsules']}")
    return errors, selected, movie_to_rows


def scan_capsule(reader, capsule_row: dict, movie_pin: dict) -> tuple[dict, dict]:
    directory = Path(capsule_row["capsule_directory"])
    manifest_path = directory / "manifest.json"
    if common.sha256(manifest_path) != capsule_row["capsule_manifest_sha256"]:
        raise ValueError(f"capsule manifest pin mismatch: {manifest_path}")
    if capsule_row["movie_sha256"] != movie_pin["sha256"]:
        raise ValueError(f"capsule/movie pins disagree: {capsule_row['movie']}")
    if capsule_row["start_state"]["path"] != movie_pin["declared_start_state"]:
        raise ValueError(f"capsule/start-state declaration disagrees: {capsule_row['movie']}")
    capsule = reader.Capsule(directory)
    frames = []
    hotspots: Counter[int] = Counter()
    handler_totals: Counter[str] = Counter()
    domain_frames: Counter[str] = Counter()
    domain_bytes: Counter[str] = Counter()
    type_events, phase_events, equip_events = [], [], []
    prior_plants = None
    prior_equip = None
    first_register = last_register = None
    for record_index, item in enumerate(capsule.frames()):
        ram = item.state["ram"]
        player = player_state(ram)
        plants = plant_slots(ram)
        equip = frame_index.u8(ram, EQUIPPED_BERRY)
        frame_blocks: Counter[int] = Counter()
        for pc, count, _ in item.flow:
            hotspots[pc] += count
            frame_blocks[pc] += count
        handler_counts = {}
        for name, pc in HANDLERS.items():
            count = frame_blocks[pc]
            handler_counts[name] = count
            handler_totals[name] += count
        changed = {}
        for domain in ("ram", "vram", "spu"):
            runs = item.changes[domain]
            changed[domain] = {
                "runs": len(runs),
                "bytes": sum(len(data) for _, data in runs),
            }
            if runs:
                domain_frames[domain] += 1
                domain_bytes[domain] += changed[domain]["bytes"]
        correlations = {
            "player_block_changed": intersects(item.changes["ram"], PLAYER_BASE, PLAYER_SIZE),
            "actor_pool_changed": intersects(
                item.changes["ram"], ACTOR_BASE, ACTOR_STRIDE * ACTOR_COUNT),
            "plant_pool_changed": intersects(
                item.changes["ram"], PLANT_BASE, PLANT_STRIDE * PLANT_COUNT),
            "equipped_berry_changed": intersects(item.changes["ram"], EQUIPPED_BERRY, 1),
            "vram_changed": bool(item.changes["vram"]),
            "spu_ram_changed": bool(item.changes["spu"]),
        }
        if prior_plants is not None:
            for before, after in zip(prior_plants, plants):
                if before["type"] != after["type"]:
                    type_events.append({
                        "movie_frame": item.movie_frame,
                        "slot": after["slot"],
                        "before_type": before["type"],
                        "after_type": after["type"],
                        "phase_before": before["lifecycle_phase_raw"],
                        "phase_after": after["lifecycle_phase_raw"],
                    })
                if before["lifecycle_phase_raw"] != after["lifecycle_phase_raw"]:
                    phase_events.append({
                        "movie_frame": item.movie_frame,
                        "slot": after["slot"],
                        "type_before": before["type"],
                        "type_after": after["type"],
                        "before": before["lifecycle_phase_raw"],
                        "after": after["lifecycle_phase_raw"],
                    })
        if prior_equip is not None and equip != prior_equip:
            equip_events.append({
                "movie_frame": item.movie_frame,
                "before": prior_equip,
                "after": equip,
                "range_changed": correlations["equipped_berry_changed"],
            })
        register_sha = seed_index.frame_register_sha(item.registers)
        first_register = first_register or register_sha
        last_register = register_sha
        frames.append({
            "record_index": record_index,
            "movie_frame": item.movie_frame,
            "emulator_frame": item.frame,
            "cycle": item.cycle,
            "pc": f"0x{item.pc:08x}",
            "register_sha256": register_sha,
            "domain_sha256": item.hashes,
            "changed": changed,
            "range_correlations": correlations,
            "player": player,
            "active_plants": [row for row in plants if row["type"]],
            "seed_actors": seed_actors(ram, player),
            "equipped_berry": equip,
            "handler_counts": handler_counts,
            "top_frame_blocks": [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in frame_blocks.most_common(12)],
        })
        prior_plants = plants
        prior_equip = equip
    expected = int(capsule_row["frames"]) + 1
    if len(frames) != expected:
        raise ValueError(
            f"{capsule_row['movie']}: reconstructed {len(frames)} records, expected {expected}")
    summary = {
        "movie": capsule_row["movie"],
        "movie_sha256": capsule_row["movie_sha256"],
        "movie_bytes": movie_pin["bytes"],
        "media_class": movie_pin["media_class"],
        "start_state": capsule_row["start_state"],
        "capsule_manifest_sha256": capsule_row["capsule_manifest_sha256"],
        "capsule_tree_sha256": capsule_row["capsule_tree_sha256"],
        "control_match": capsule_row["control_match"],
        "records": len(frames),
        "movie_frames": capsule_row["frames"],
        "domain_change_frames": dict(domain_frames),
        "domain_changed_bytes_sum": dict(domain_bytes),
        "first_register_sha256": first_register,
        "last_register_sha256": last_register,
        "plant_type_events": type_events,
        "plant_phase_events": phase_events,
        "equipped_berry_events": equip_events,
        "handler_block_counts": dict(handler_totals),
        "top_hotspots": [
            {"pc": f"0x{pc:08x}", "count": count}
            for pc, count in hotspots.most_common(40)],
    }
    return {"movie": capsule_row["movie"], "frames": frames}, summary


def consecutive_runs(frames: list[dict], predicate) -> list[list[dict]]:
    runs, current = [], []
    for frame in frames:
        if predicate(frame):
            if current and frame["movie_frame"] != current[-1]["movie_frame"] + 1:
                runs.append(current)
                current = []
            current.append(frame)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def velocity_transitions(frames: list[dict], target: int) -> list[dict]:
    rows = []
    for before, after in zip(frames, frames[1:]):
        prior = before["player"]["velocity_y"]
        current = after["player"]["velocity_y"]
        if current == target and prior != target:
            rows.append({
                "movie_frame": after["movie_frame"],
                "before_velocity_y": prior,
                "after_velocity_y": current,
                "player": after["player"],
            })
    return rows


def nearest_plant(frame: dict, plant_type: int) -> dict | None:
    player = frame["player"]
    choices = []
    for plant in frame["active_plants"]:
        if plant["type"] != plant_type:
            continue
        distance_sq = ((player["x"] - plant["x"]) ** 2
                       + (player["z"] - plant["z"]) ** 2)
        choices.append((distance_sq, plant))
    if not choices:
        return None
    distance_sq, plant = min(choices, key=lambda row: row[0])
    return {**plant, "horizontal_distance_squared": distance_sq}


def plant_cycles(summary: dict, plant_types: set[int]) -> list[dict]:
    events = summary["plant_type_events"]
    phases = summary["plant_phase_events"]
    rows = []
    for creation in events:
        if creation["before_type"] != 0 or creation["after_type"] not in plant_types:
            continue
        retirement = next((row for row in events
                           if row["movie_frame"] > creation["movie_frame"]
                           and row["slot"] == creation["slot"]
                           and row["before_type"] == creation["after_type"]
                           and row["after_type"] == 0), None)
        if retirement is None:
            continue
        phase_rows = [row for row in phases
                      if row["slot"] == creation["slot"]
                      and creation["movie_frame"] <= row["movie_frame"]
                      <= retirement["movie_frame"]]
        rows.append({
            "slot": creation["slot"],
            "plant_type": creation["after_type"],
            "creation_movie_frame": creation["movie_frame"],
            "retirement_movie_frame": retirement["movie_frame"],
            "retained_lifetime_frames": (
                retirement["movie_frame"] - creation["movie_frame"]),
            "phase_transitions": [{
                "movie_frame": row["movie_frame"],
                "before": row["before"],
                "after": row["after"],
            } for row in phase_rows],
        })
    return rows


def tracked_capsule_summary(summary: dict) -> dict:
    keys = (
        "movie", "movie_sha256", "movie_bytes", "media_class", "start_state",
        "capsule_manifest_sha256", "capsule_tree_sha256", "control_match",
        "records", "movie_frames", "domain_change_frames",
        "domain_changed_bytes_sum", "first_register_sha256",
        "last_register_sha256", "handler_block_counts", "top_hotspots",
        "queue_rows",
    )
    return {
        **{key: summary[key] for key in keys},
        "plant_type_event_count": len(summary["plant_type_events"]),
        "plant_phase_event_count": len(summary["plant_phase_events"]),
        "equipped_berry_events": summary["equipped_berry_events"],
    }


def derive_findings(details: dict[str, dict], summaries: dict[str, dict],
                    row_movies: dict[str, list[str]]) -> dict:
    b01_movie = row_movies["B01_mushroom_trampoline"][0]
    b01_frames = details[b01_movie]["frames"]
    bounces = velocity_transitions(b01_frames, -3328)
    frame_by_number = {frame["movie_frame"]: frame for frame in b01_frames}
    for event in bounces:
        frame = frame_by_number[event["movie_frame"]]
        event["nearest_type_5_plant"] = nearest_plant(frame, 5)
        event["mushroom_handler_block_count"] = frame["handler_counts"]["mushroom"]

    b02_movie = row_movies["B02_propeller_plant"][0]
    b02_frames = details[b02_movie]["frames"]
    lift_runs = consecutive_runs(
        b02_frames,
        lambda frame: (frame["player"]["state"] == 5
                       and frame["player"]["velocity_y"] <= -2048))
    lifts = []
    for run in lift_runs:
        velocity_steps = []
        for frame in run:
            value = frame["player"]["velocity_y"]
            if not velocity_steps or velocity_steps[-1]["velocity_y"] != value:
                velocity_steps.append({"movie_frame": frame["movie_frame"], "velocity_y": value})
        lifts.append({
            "start_movie_frame": run[0]["movie_frame"],
            "end_movie_frame": run[-1]["movie_frame"],
            "velocity_steps": velocity_steps,
            "minimum_velocity_y": min(row["player"]["velocity_y"] for row in run),
            "handler_count_sum": sum(
                row["handler_counts"]["propeller"] for row in run),
        })
    second_window = [frame for frame in b02_frames if 400 <= frame["movie_frame"] <= 700]
    seed_slots: dict[int, int] = {}
    for frame in second_window:
        for seed in frame["seed_actors"]:
            seed_slots[seed["slot"]] = max(
                seed_slots.get(seed["slot"], 0), abs(seed["velocity_y"]))
    moving_seed_slot = max(seed_slots, key=seed_slots.get)
    seed_runs = consecutive_runs(
        second_window,
        lambda frame: any(seed["slot"] == moving_seed_slot and seed["velocity_y"] != 0
                          for seed in frame["seed_actors"]))
    second_lift = lifts[1]
    seed_run = next(run for run in seed_runs
                    if run[0]["movie_frame"] <= second_lift["start_movie_frame"]
                    <= run[-1]["movie_frame"])
    seed_values = [next(seed for seed in frame["seed_actors"]
                        if seed["slot"] == moving_seed_slot) for frame in seed_run]
    attached_frames = [frame for frame, seed in zip(seed_run, seed_values)
                       if seed["exact_player_attachment"]]
    seed_trajectory = {
        "slot": moving_seed_slot,
        "address": seed_values[0]["address"],
        "start_movie_frame": seed_run[0]["movie_frame"],
        "end_movie_frame": seed_run[-1]["movie_frame"],
        "minimum_velocity_y": min(row["velocity_y"] for row in seed_values),
        "minimum_y": min(row["y"] for row in seed_values),
        "ai_flags_values": sorted({row["ai_flags"] for row in seed_values}),
        "exact_carried_flag_0x20_present": any(
            row["ai_flags"] & 0x20 for row in seed_values),
        "exact_player_attachment_records": sum(
            bool(row["exact_player_attachment"]) for row in seed_values),
        "exact_player_attachment_interval": {
            "start_movie_frame": attached_frames[0]["movie_frame"],
            "end_movie_frame": attached_frames[-1]["movie_frame"],
        },
        "attachment_end_to_second_lift_start_frames": (
            second_lift["start_movie_frame"] - attached_frames[-1]["movie_frame"]),
    }

    b03_movie = row_movies["B03_dandelion_glide"][0]
    b03_frames = details[b03_movie]["frames"]
    dandelion_launches = velocity_transitions(b03_frames, -4096)
    overlap = [frame for frame in b03_frames
               if frame["handler_counts"]["dandelion"]
               and frame["handler_counts"]["propeller"]]
    landing = next((frame for frame in overlap
                    if frame["player"]["grounded"] and frame["player"]["velocity_y"] == 0), None)

    b04_movie = row_movies["B04_cannon_plant"][0]
    b04_frames = details[b04_movie]["frames"]
    constant_runs = []
    current = []
    current_key = None
    for frame in b04_frames:
        has_cannon = any(row["type"] == 2 for row in frame["active_plants"])
        player = frame["player"]
        key = (player["x"], player["y"], player["z"], player["state"],
               player["grounded"], player["velocity_y"])
        eligible = has_cannon and player["state"] == 0 and player["velocity_y"] == 0
        if eligible and key == current_key:
            current.append(frame)
        else:
            if current:
                constant_runs.append(current)
            current = [frame] if eligible else []
            current_key = key if eligible else None
    if current:
        constant_runs.append(current)
    launch_frame = next(frame for frame in b04_frames
                        if frame["player"]["velocity_y"] <= -7000)
    seated = max((run for run in constant_runs
                  if run[-1]["movie_frame"] < launch_frame["movie_frame"]),
                 key=lambda run: run[-1]["movie_frame"])
    launch_index = b04_frames.index(launch_frame)
    later_discrete_dandelion_impulses = []
    for before, after in zip(b04_frames[launch_index:], b04_frames[launch_index + 1:]):
        if (after["player"]["velocity_y"] == -4096
                and after["player"]["velocity_y"] - before["player"]["velocity_y"] <= -2048):
            later_discrete_dandelion_impulses.append(after["movie_frame"])

    b05_movie = row_movies["B05_green_leaf_platforms"][0]
    green_cycles = plant_cycles(summaries[b05_movie], {1, 4, 9, 10})

    b10_movie = row_movies["B10_purple_berry_plants"][0]
    b10_frames = details[b10_movie]["frames"]
    b10_summary = summaries[b10_movie]
    purple_cycles = plant_cycles(b10_summary, {6})
    equip_events = b10_summary["equipped_berry_events"]
    grant_by_type = {
        1: "berry_grant_type_1", 2: "berry_grant_type_2",
        4: "berry_grant_type_4", 3: "berry_grant_type_3",
    }
    for event in equip_events:
        handler = grant_by_type[event["after"]]
        candidates = [frame for frame in b10_frames if frame["handler_counts"][handler]]
        nearest = min(candidates, key=lambda frame: abs(
            frame["movie_frame"] - event["movie_frame"]))
        creation = max((row for row in purple_cycles
                        if row["creation_movie_frame"] <= event["movie_frame"]),
                       key=lambda row: row["creation_movie_frame"])
        event["grant_handler"] = handler
        event["grant_handler_movie_frame"] = nearest["movie_frame"]
        event["grant_to_equip_frame_delta"] = event["movie_frame"] - nearest["movie_frame"]
        event["plant_creation_movie_frame"] = creation["creation_movie_frame"]
        event["creation_to_equip_frames"] = (
            event["movie_frame"] - creation["creation_movie_frame"])

    return {
        "B01_mushroom_trampoline": {
            "movie": b01_movie,
            "bounce_velocity_y": -3328,
            "bounce_events": bounces,
            "distinct_nearest_plant_slots": sorted({
                row["nearest_type_5_plant"]["slot"] for row in bounces}),
            "bounded_observation": (
                "Four frame-boundary transitions to -3328 correlate with four distinct "
                "nearby type-5 slots and passive mushroom-handler block starts. The "
                "capsule does not prove a combo law, fifth-bounce bonus, or exact writer."),
        },
        "B02_propeller_plant": {
            "movie": b02_movie,
            "player_lift_runs": lifts,
            "nearby_seed_vertical_motion": seed_trajectory,
            "bounded_observation": (
                "Two player lift ramps reach and hold -3072. A seed follows a vertical "
                "trajectory overlapping the second ramp after an earlier exact player/seed "
                "position-attachment interval. The attachment ends before that lift, so "
                "the capsule does not prove propeller-to-seed causality."),
        },
        "B03_dandelion_glide": {
            "movie": b03_movie,
            "dandelion_velocity_transitions": dandelion_launches,
            "propeller_dandelion_handler_overlap": {
                "first_movie_frame": overlap[0]["movie_frame"],
                "last_movie_frame": overlap[-1]["movie_frame"],
                "retained_frames": len(overlap),
                "first_grounded_zero_velocity_frame": (
                    landing["movie_frame"] if landing else None),
            },
            "bounded_observation": (
                "One frame-boundary transition to -4096 is retained. Later propeller and "
                "dandelion handler overlap ends in a grounded state, but passive block "
                "starts do not establish a glide attachment, updraft, sink law, or writer."),
        },
        "B04_cannon_plant": {
            "movie": b04_movie,
            "seated_constant_interval": {
                "start_movie_frame": seated[0]["movie_frame"],
                "end_movie_frame": seated[-1]["movie_frame"],
                "records": len(seated),
                "player": seated[0]["player"],
            },
            "launch": {
                "movie_frame": launch_frame["movie_frame"],
                "velocity_y": launch_frame["player"]["velocity_y"],
                "cannon_handler_block_count": launch_frame["handler_counts"]["cannon"],
                "dandelion_handler_block_count": launch_frame["handler_counts"]["dandelion"],
            },
            "later_discrete_dandelion_impulse_frames": later_discrete_dandelion_impulses,
            "bounded_observation": (
                "The retained seated interval is followed by one cannon-sized launch. "
                "A type-8 handler coexists, but no later discrete transition to -4096 is "
                "retained; the movie name is not proof of a successful combo."),
        },
        "B05_green_leaf_platforms": {
            "movie": b05_movie,
            "green_plant_cycles": green_cycles,
            "green_collision_tail_block_count": (
                summaries[b05_movie]["handler_block_counts"]["green_collision_tail"]),
            "bounded_observation": (
                "The fixture retains one complete type-4, type-10, type-9 and type-1 "
                "lifecycle with distinct phase timing. The shared collision tail executes, "
                "but frame boundaries do not bind a specific leaf plane or climb primitive."),
        },
        "B10_purple_berry_plants": {
            "movie": b10_movie,
            "purple_plant_cycles": purple_cycles,
            "equipped_berry_transitions": equip_events,
            "observed_equip_sequence": [equip_events[0]["before"]]
            + [row["after"] for row in equip_events],
            "bounded_observation": (
                "Four complete type-6 lifecycles correlate with one grant-handler start "
                "and one equipped-byte transition each, in order 0,1,2,4,3. Exact pickup "
                "collision and reset behavior remain outside frame-boundary attribution."),
        },
    }


def build(external_output: Path) -> tuple[dict, dict]:
    queue = common.load_json(QUEUE_PATH)
    capsules = common.load_json(CAPSULE_PATH)
    errors, selected_capsules, movie_to_rows = source_errors(queue, capsules)
    reader_info = capsules.get("offline_reader_snapshot") or {}
    reader_path = Path(reader_info.get("absolute_path") or "")
    try:
        reader = frame_index.load_reader(reader_path, reader_info.get("sha256") or "")
    except ValueError as exc:
        errors.append(str(exc))
        reader = None
    if errors:
        raise ValueError("; ".join(errors))
    queue_rows = {row["row_id"]: row for row in queue["rows"]}
    detail_rows, summary_rows = [], []
    for capsule in selected_capsules:
        pin = capsule_movie_pin(queue_rows, capsule["movie"])
        detail, summary = scan_capsule(reader, capsule, pin)
        rows = sorted(movie_to_rows[capsule["movie"]])
        detail["queue_rows"] = rows
        summary["queue_rows"] = rows
        detail_rows.append(detail)
        summary_rows.append(summary)
    detail_by_movie = {row["movie"]: row for row in detail_rows}
    summary_by_movie = {row["movie"]: row for row in summary_rows}
    row_movies = {
        row_id: [item["movie"] for item in queue_rows[row_id]["relevant_capsules"]]
        for row_id in SELECTED_ROWS
    }
    exact_queries = {
        row_id: queue_rows[row_id]["offline_batch_queries"] for row_id in SELECTED_ROWS
    }
    findings = derive_findings(detail_by_movie, summary_by_movie, row_movies)
    external_document = {
        "_comment": "External game-derived cross-movie index; preserve outside Git.",
        "schema": CONFIGURATION["external_index"]["schema"],
        "generated": stable_generated(external_output),
        "selected_rows": list(SELECTED_ROWS),
        "reader": reader_info,
        "selection_snapshot": CONFIGURATION["selection_snapshot"],
        "capsule_index_sha256": common.sha256(CAPSULE_PATH),
        "capsules": detail_rows,
    }
    external_bytes = render(external_document)
    external_hash = hashlib.sha256(external_bytes).hexdigest()
    dependency_paths = [
        "analysis/phase4_trace_capsule_set.json",
        "config/phase4_offline_traversal_plants_batch.yaml",
        "src_re/brown_seed_plants.c",
        "src_re/green_seed_plants.c",
        "src_re/purple_seed_plants.c",
        "tools/phase4_offline_contact_batch.py",
        "tools/phase4_offline_seed_lifecycle_batch.py",
        "tools/phase4_offline_traversal_plants_batch.py",
    ]
    summary_document = {
        "_comment": "Non-copyrighted preservation manifest and bounded findings for the six-row Phase-4 traversal-plant batch; frame boundaries are not exact writer evidence.",
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(OUTPUT),
        "source_dependencies": {
            path: common.sha256(common.ROOT / path) for path in dependency_paths
        },
        "queue_counts": CONFIGURATION["selection_snapshot"]["queue_counts"],
        "selected_rows": [{
            "row_id": row_id,
            "queue_rank": SELECTION_ROWS[row_id]["queue_rank"],
            "classification": SELECTION_ROWS[row_id]["classification"],
            "completion_state": SELECTION_ROWS[row_id]["completion_state"],
            "capsules": row_movies[row_id],
        } for row_id in SELECTED_ROWS],
        "offline_batch": {
            "reader_path": str(reader_path),
            "reader_sha256": reader_info["sha256"],
            "generator_command": (
                "python3 tools/phase4_offline_traversal_plants_batch.py "
                f"--external-output {external_output} --write"),
            "capsule_count": len(selected_capsules),
            "reconstructed_records": sum(row["records"] for row in summary_rows),
            "domains": CONFIGURATION["external_index"]["domains"],
            "exact_queue_queries": exact_queries,
        },
        "external_index": {
            "absolute_path": str(external_output),
            "sha256": external_hash,
            "bytes": len(external_bytes),
            "media_class": "external game-derived evidence; never commit",
            "schema": external_document["schema"],
            "preservation_required": True,
        },
        "capsule_summaries": [tracked_capsule_summary(row) for row in summary_rows],
        "derived_findings": findings,
        "bounded_conclusions": [
            "All six relevant capsules reconstruct under the exact pinned reader without a record-count or domain-hash error.",
            "The six movies are current centrally hash-pinned pristine-media fixtures with declared start states and matching capsule media controls.",
            "The batch retains four mushroom bounce boundaries, two propeller lift ramps, one dandelion launch boundary, one cannon launch, four green lifecycles and four purple equip transitions.",
            "The B04 title does not override the retained state: no later discrete dandelion-sized impulse follows its cannon launch.",
            "Frame-boundary correlation and passive block starts do not attribute exact CPU writers, collision geometry, DMA/GPU/SPU producers, causal controls, or between-frame behavior.",
        ],
        "named_unknowns": {
            row_id: queue_rows[row_id]["named_unknowns"] for row_id in SELECTED_ROWS
        },
        "live_escalation": None,
        "errors": [],
        "valid": True,
    }
    return external_document, summary_document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--external-output", type=Path,
        default=(EXTERNAL_EVIDENCE_ROOT
                 / "derived/Phase4/traversal-plants-v1/index.json"))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    external_output = args.external_output.resolve()
    try:
        external, summary = build(external_output)
    except (OSError, ValueError, KeyError, RuntimeError, StopIteration) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    external_bytes = render(external)
    summary_bytes = render(summary)
    if args.write:
        external_output.parent.mkdir(parents=True, exist_ok=True)
        external_output.write_bytes(external_bytes)
        OUTPUT.write_bytes(summary_bytes)
    elif args.check:
        if not external_output.is_file() or external_output.read_bytes() != external_bytes:
            print("external Phase-4 traversal-plant index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 traversal-plant summary is missing or stale", file=sys.stderr)
            return 1
    else:
        print(summary_bytes.decode(), end="")
    print(
        f"PASS: rows={len(SELECTED_ROWS)} "
        f"capsules={summary['offline_batch']['capsule_count']} "
        f"records={summary['offline_batch']['reconstructed_records']} "
        f"external_sha256={summary['external_index']['sha256']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
