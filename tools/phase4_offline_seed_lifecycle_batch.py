#!/usr/bin/env python3
"""Build the external cross-movie index for the seed lifecycle batch."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

import phase4_common as common
import phase4_offline_contact_batch as frame_index


QUEUE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
OUTPUT = common.ROOT / "analysis/phase4_offline_seed_lifecycle_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_seed_lifecycle_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELECTION_ROWS = {
    row["row_id"]: row for row in CONFIGURATION["selection_snapshot"]["rows"]
}
SELF_ARTIFACT = "analysis/phase4_offline_seed_lifecycle_batch.json"
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
PLANT_CURSOR = 0x0822B8
PLANT_BASE = 0x090BF0
PLANT_STRIDE = 0x30
PLANT_COUNT = 20


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


def u8(image: bytearray, offset: int) -> int:
    return image[offset]


def u16(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<H", image, offset)[0]


def u32(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<I", image, offset)[0]


def s16(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<h", image, offset)[0]


def s32(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<i", image, offset)[0]


def player_state(image: bytearray) -> dict:
    return {
        "x": s32(image, PLAYER_BASE),
        "y": s32(image, PLAYER_BASE + 0x04),
        "z": s32(image, PLAYER_BASE + 0x08),
        "velocity_y": s32(image, PLAYER_BASE + 0x30),
        "state": u16(image, PLAYER_BASE + 0x80),
        "grounded": u16(image, PLAYER_BASE + 0x82),
    }


def seed_actors(image: bytearray, player: dict) -> list[dict]:
    result = []
    for slot in range(ACTOR_COUNT):
        base = ACTOR_BASE + slot * ACTOR_STRIDE
        if u32(image, base) != SEED_ACTOR_ID:
            continue
        x, y, z = s32(image, base + 0x04), s32(image, base + 0x08), s32(image, base + 0x0C)
        result.append({
            "slot": slot,
            "address": f"0x{0x80000000 + base:08x}",
            "actor_id": SEED_ACTOR_ID,
            "x": x,
            "y": y,
            "z": z,
            "velocity_x": s32(image, base + 0x1C),
            "velocity_z": s32(image, base + 0x24),
            "ai_flags": u16(image, base + 0x5C),
            "knockback": s16(image, base + 0x6C),
            "hp": s16(image, base + 0x6E),
            "exact_player_attachment": (
                x == player["x"] and z == player["z"]
                and player["y"] - y == 19200),
        })
    return result


def plant_slots(image: bytearray) -> list[dict]:
    return [{
        "slot": slot,
        "type": u16(image, PLANT_BASE + slot * PLANT_STRIDE),
        "lifecycle_phase_raw": u8(image, PLANT_BASE + slot * PLANT_STRIDE + 0x2E),
    } for slot in range(PLANT_COUNT)]


def frame_register_sha(registers: dict[str, int]) -> str:
    payload = json.dumps(registers, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def intersects(runs: list[tuple[int, bytes]], offset: int, length: int) -> bool:
    end = offset + length
    return any(start < end and start + len(data) > offset for start, data in runs)


def movie_file(logical_path: str) -> Path:
    path = Path(logical_path)
    if path.is_absolute() or not path.parts or path.parts[0] != "movies":
        raise ValueError(f"movie path is not centrally rooted: {logical_path}")
    return OPERATOR_ROOT / path


def input_edges(movie_pin: dict) -> dict[str, list[int]]:
    path = movie_file(movie_pin["path"])
    if not path.is_file():
        raise ValueError(f"centrally declared movie is missing: {path}")
    if path.stat().st_size != int(movie_pin["bytes"]):
        raise ValueError(f"movie byte pin mismatch: {path}")
    if common.sha256(path) != movie_pin["sha256"]:
        raise ValueError(f"movie hash pin mismatch: {path}")
    if not movie_pin.get("central_pin_current"):
        raise ValueError(f"movie central pin is not current: {path}")
    if not movie_pin.get("declared_start_state"):
        raise ValueError(f"movie lacks a declared start state: {path}")
    document = common.load_json(path)
    buttons = ("cross", "square", "circle", "triangle")
    result = {f"{button}_press": [] for button in buttons}
    result.update({f"{button}_release": [] for button in buttons})
    prior = {button: False for button in buttons}
    for row in document.get("frames") or []:
        controls = (row.get("ports") or {}).get("0") or {}
        frame = int(row["frame"])
        for button in buttons:
            current = bool(controls.get(button))
            if current != prior[button]:
                result[f"{button}_{'press' if current else 'release'}"].append(frame)
            prior[button] = current
    return result


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
    return pins[0]


def scan_capsule(reader, capsule_row: dict, movie_pin: dict) -> tuple[dict, dict]:
    directory = Path(capsule_row["capsule_directory"])
    manifest_path = directory / "manifest.json"
    if common.sha256(manifest_path) != capsule_row["capsule_manifest_sha256"]:
        raise ValueError(f"capsule manifest pin mismatch: {manifest_path}")
    if capsule_row["movie_sha256"] != movie_pin["sha256"]:
        raise ValueError(f"capsule/movie central pins disagree: {capsule_row['movie']}")
    if (capsule_row["start_state"]["path"]
            != movie_pin["declared_start_state"]):
        raise ValueError(f"capsule/start-state declaration disagrees: {capsule_row['movie']}")
    edges = input_edges(movie_pin)
    capsule = reader.Capsule(directory)

    external_frames = []
    hotspots: Counter[int] = Counter()
    domain_frames: Counter[str] = Counter()
    domain_bytes: Counter[str] = Counter()
    plant_type_events = []
    phase_events = []
    cursor_events = []
    attachment_counts: Counter[int] = Counter()
    prior_plants = None
    prior_cursor = None
    first_register = last_register = None

    for record_index, item in enumerate(capsule.frames()):
        ram = item.state["ram"]
        player = player_state(ram)
        seeds = seed_actors(ram, player)
        plants = plant_slots(ram)
        cursor = u8(ram, PLANT_CURSOR)
        for seed in seeds:
            if seed["exact_player_attachment"]:
                attachment_counts[seed["slot"]] += 1
        frame_hotspots: Counter[int] = Counter()
        for pc, count, _ in item.flow:
            hotspots[pc] += count
            frame_hotspots[pc] += count
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
            "plant_cursor_changed": intersects(item.changes["ram"], PLANT_CURSOR, 1),
            "vram_changed": bool(item.changes["vram"]),
            "spu_ram_changed": bool(item.changes["spu"]),
        }
        register_sha = frame_register_sha(item.registers)
        first_register = first_register or register_sha
        last_register = register_sha
        frame_ref = {
            "record_index": record_index,
            "movie_frame": item.movie_frame,
            "emulator_frame": item.frame,
            "cycle": item.cycle,
            "pc": f"0x{item.pc:08x}",
        }
        if prior_plants is not None:
            for before, after in zip(prior_plants, plants):
                if before["type"] != after["type"]:
                    plant_type_events.append({
                        "movie_frame": item.movie_frame,
                        "slot": after["slot"],
                        "before_type": before["type"],
                        "after_type": after["type"],
                        "phase_before": before["lifecycle_phase_raw"],
                        "phase_after": after["lifecycle_phase_raw"],
                        "cursor_before": prior_cursor,
                        "cursor_after": cursor,
                        "correlations": correlations,
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
            if prior_cursor != cursor:
                cursor_events.append({
                    "movie_frame": item.movie_frame,
                    "before": prior_cursor,
                    "after": cursor,
                })
        external_frames.append({
            **frame_ref,
            "register_sha256": register_sha,
            "domain_sha256": item.hashes,
            "changed": changed,
            "range_correlations": correlations,
            "player": player,
            "seed_actors": seeds,
            "plant_cursor": cursor,
            "active_plants": [row for row in plants if row["type"]],
            "top_frame_blocks": [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in frame_hotspots.most_common(12)],
        })
        prior_plants = plants
        prior_cursor = cursor

    records = len(external_frames)
    expected = int(capsule_row["frames"]) + 1
    if records != expected:
        raise ValueError(
            f"{capsule_row['movie']}: reconstructed {records} records, expected {expected}")
    creations = [row for row in plant_type_events
                 if row["before_type"] == 0 and row["after_type"] != 0]
    retirements = [row for row in plant_type_events
                   if row["before_type"] != 0 and row["after_type"] == 0]
    summary = {
        "movie": capsule_row["movie"],
        "movie_sha256": capsule_row["movie_sha256"],
        "movie_bytes": movie_pin["bytes"],
        "media_class": movie_pin["media_class"],
        "start_state": capsule_row["start_state"],
        "capsule_manifest_sha256": capsule_row["capsule_manifest_sha256"],
        "capsule_tree_sha256": capsule_row["capsule_tree_sha256"],
        "control_match": capsule_row["control_match"],
        "records": records,
        "movie_frames": capsule_row["frames"],
        "input_edges": edges,
        "domain_change_frames": dict(domain_frames),
        "domain_changed_bytes_sum": dict(domain_bytes),
        "first_register_sha256": first_register,
        "last_register_sha256": last_register,
        "seed_slots": sorted({seed["slot"] for frame in external_frames
                              for seed in frame["seed_actors"]}),
        "attachment_counts": {str(key): value
                              for key, value in sorted(attachment_counts.items())},
        "plant_type_events": plant_type_events,
        "plant_creations": creations,
        "plant_retirements": retirements,
        "plant_phase_events": phase_events,
        "cursor_events": cursor_events,
        "top_hotspots": [
            {"pc": f"0x{pc:08x}", "count": count}
            for pc, count in hotspots.most_common(40)],
    }
    return {"movie": capsule_row["movie"], "summary": summary,
            "frames": external_frames}, summary


def source_errors(queue: dict, capsules: dict) -> tuple[list[str], list[dict], dict[str, list[str]]]:
    errors = []
    if CONFIGURATION.get("schema") != "abl-phase4-offline-seed-lifecycle-batch-source/1":
        errors.append("offline seed lifecycle batch source schema is invalid")
    if not queue.get("valid") or queue.get("errors"):
        errors.append("offline opportunity queue is invalid")
    if len(queue.get("rows") or []) != 107:
        errors.append("offline opportunity queue does not contain exactly 107 rows")
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
                    f"selected row rank changed: {row_id} is {rank}, expected {snapshot['queue_rank']}")
        for capsule in row.get("relevant_capsules") or []:
            movie_to_rows.setdefault(capsule["movie"], []).append(row_id)
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
    if [SELECTION_ROWS[row_id]["queue_rank"] for row_id in SELECTED_ROWS] != [1, 2, 3]:
        errors.append("selection snapshot does not retain ranks 1 through 3")
    return errors, selected, movie_to_rows


def frame_seed(frame: dict, slot: int) -> dict | None:
    return next((row for row in frame["seed_actors"] if row["slot"] == slot), None)


def true_runs(frames: list[dict], slot: int) -> list[dict]:
    runs, start, last = [], None, None
    for frame in frames:
        seed = frame_seed(frame, slot)
        active = bool(seed and seed["exact_player_attachment"])
        if active and start is None:
            start = frame["movie_frame"]
        if not active and start is not None:
            runs.append({"start_movie_frame": start, "end_movie_frame": last})
            start = None
        if active:
            last = frame["movie_frame"]
    if start is not None:
        runs.append({"start_movie_frame": start, "end_movie_frame": last})
    return runs


def nearest_prior(values: list[int], frame: int, *, after: int = -1) -> int | None:
    candidates = [value for value in values if after < value <= frame]
    return max(candidates) if candidates else None


def first_stable_position(frames: list[dict], slot: int, start: int, end: int,
                          minimum_records: int = 10) -> dict | None:
    selected = [frame for frame in frames if start <= frame["movie_frame"] <= end]
    for index, frame in enumerate(selected):
        window = selected[index:index + minimum_records]
        if len(window) < minimum_records:
            break
        seeds = [frame_seed(item, slot) for item in window]
        if any(seed is None for seed in seeds):
            continue
        positions = {(seed["x"], seed["y"], seed["z"]) for seed in seeds}
        if len(positions) == 1:
            seed = seeds[0]
            return {"movie_frame": frame["movie_frame"],
                    "position": [seed["x"], seed["y"], seed["z"]]}
    return None


def first_velocity_reversal(frames: list[dict], slot: int, start: int, end: int) -> dict | None:
    selected = [frame for frame in frames if start <= frame["movie_frame"] <= end]
    if not selected:
        return None
    initial = frame_seed(selected[0], slot)
    if initial is None:
        return None
    signs = {
        "velocity_x": 1 if initial["velocity_x"] > 0 else -1 if initial["velocity_x"] < 0 else 0,
        "velocity_z": 1 if initial["velocity_z"] > 0 else -1 if initial["velocity_z"] < 0 else 0,
    }
    for frame in selected[1:]:
        seed = frame_seed(frame, slot)
        if seed is None:
            continue
        for component in ("velocity_x", "velocity_z"):
            value = seed[component]
            sign = 1 if value > 0 else -1 if value < 0 else 0
            if signs[component] and sign and sign != signs[component]:
                return {
                    "movie_frame": frame["movie_frame"],
                    "component": component,
                    "initial_value": initial[component],
                    "reversed_value": value,
                    "position": [seed["x"], seed["y"], seed["z"]],
                }
    return None


def y_motion_episodes(frames: list[dict], slot: int) -> list[dict]:
    changes = []
    prior = None
    for frame in frames:
        seed = frame_seed(frame, slot)
        if seed is None:
            prior = None
            continue
        if prior is not None and seed["y"] != prior["seed"]["y"]:
            changes.append({
                "movie_frame": frame["movie_frame"],
                "before_y": prior["seed"]["y"],
                "y": seed["y"],
                "x": seed["x"],
                "z": seed["z"],
            })
        prior = {"frame": frame["movie_frame"], "seed": seed}
    episodes = []
    active = None
    for change in changes:
        if active is None or change["movie_frame"] - active["end_movie_frame"] > 2:
            if active is not None:
                episodes.append(active)
            active = {
                "start_movie_frame": change["movie_frame"],
                "end_movie_frame": change["movie_frame"],
                "before_y": change["before_y"],
                "end_y": change["y"],
                "end_x": change["x"],
                "end_z": change["z"],
            }
        else:
            active["end_movie_frame"] = change["movie_frame"]
            active["end_y"] = change["y"]
            active["end_x"] = change["x"]
            active["end_z"] = change["z"]
    if active is not None:
        episodes.append(active)
    for row in episodes:
        row["net_y"] = row["end_y"] - row["before_y"]
    return [row for row in episodes if abs(row["net_y"]) >= 10000]


def tracked_capsule_summary(summary: dict) -> dict:
    keys = (
        "movie", "movie_sha256", "movie_bytes", "media_class", "start_state",
        "capsule_manifest_sha256", "capsule_tree_sha256", "control_match",
        "records", "movie_frames", "domain_change_frames",
        "domain_changed_bytes_sum", "first_register_sha256",
        "last_register_sha256", "seed_slots", "attachment_counts",
        "top_hotspots", "queue_rows",
    )
    return {
        **{key: summary[key] for key in keys},
        "input_edge_counts": {key: len(value) for key, value in summary["input_edges"].items()},
        "plant_creation_count": len(summary["plant_creations"]),
        "plant_retirement_count": len(summary["plant_retirements"]),
        "plant_phase_event_count": len(summary["plant_phase_events"]),
        "cursor_event_count": len(summary["cursor_events"]),
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
    details, summaries = [], []
    for capsule in selected_capsules:
        pin = capsule_movie_pin(queue_rows, capsule["movie"])
        detail, summary = scan_capsule(reader, capsule, pin)
        rows = sorted(movie_to_rows[capsule["movie"]])
        detail["queue_rows"] = rows
        summary["queue_rows"] = rows
        details.append(detail)
        summaries.append(summary)
    detail_by_movie = {row["movie"]: row for row in details}
    summary_by_movie = {row["movie"]: row for row in summaries}
    row_movies = {
        row_id: [item["movie"] for item in queue_rows[row_id]["relevant_capsules"]]
        for row_id in SELECTED_ROWS
    }
    exact_queries = {
        row_id: queue_rows[row_id]["offline_batch_queries"] for row_id in SELECTED_ROWS
    }

    a09_movie = row_movies["A09_seed_pickup_drop"][0]
    a09_summary = summary_by_movie[a09_movie]
    a09_frames = detail_by_movie[a09_movie]["frames"]
    mobile_slot = max((int(slot) for slot in a09_summary["attachment_counts"]),
                      key=lambda slot: int(a09_summary["attachment_counts"][str(slot)]))
    carry_runs = true_runs(a09_frames, mobile_slot)
    square_presses = a09_summary["input_edges"]["square_press"]
    for index, run in enumerate(carry_runs):
        run["pickup_press_frame"] = nearest_prior(square_presses, run["start_movie_frame"])
        run["pickup_to_attachment_frames"] = (
            run["start_movie_frame"] - run["pickup_press_frame"])
        next_start = (carry_runs[index + 1]["start_movie_frame"] - 1
                      if index + 1 < len(carry_runs) else a09_summary["movie_frames"])
        detach = run["end_movie_frame"] + 1
        drop_press = nearest_prior(square_presses, detach, after=run["start_movie_frame"])
        run["drop_press_frame"] = drop_press
        run["drop_to_detachment_frames"] = detach - drop_press
        run["detachment_movie_frame"] = detach
        seed = frame_seed(next(frame for frame in a09_frames
                               if frame["movie_frame"] == detach), mobile_slot)
        run["detachment_state"] = {
            key: seed[key] for key in
            ("x", "y", "z", "velocity_x", "velocity_z", "ai_flags", "hp")}
        run["first_horizontal_velocity_reversal"] = first_velocity_reversal(
            a09_frames, mobile_slot, detach, next_start)
        run["first_stable_position"] = first_stable_position(
            a09_frames, mobile_slot, detach, next_start)
    a09_finding = {
        "movie": a09_movie,
        "mobile_seed_slot": mobile_slot,
        "mobile_seed_address": f"0x{0x80000000 + ACTOR_BASE + mobile_slot * ACTOR_STRIDE:08x}",
        "carry_attachment_predicate": (
            "seed x/z equal player x/z and player_y - seed_y equals 19200"),
        "carry_runs": carry_runs,
        "bounded_observation": (
            "The pinned pristine movie contains three exact player/seed attachment "
            "intervals. Each interval detaches after a later square press, then reaches "
            "a stable position after at least one stored horizontal velocity component "
            "reverses. The capsule does not identify the collision primitive or geometry."),
    }

    blue_movie = row_movies["A14_plant_seed"][0]
    blue_summary = summary_by_movie[blue_movie]
    blue_frames = detail_by_movie[blue_movie]["frames"]
    blue_slot = max(blue_summary["seed_slots"], key=lambda slot: (
        max((frame_seed(frame, slot) or {"y": 0})["y"] for frame in blue_frames)
        - min((frame_seed(frame, slot) or {"y": 0})["y"] for frame in blue_frames)))
    episodes = y_motion_episodes(blue_frames, blue_slot)
    raises = [row for row in episodes if row["net_y"] > 0]
    descents = [row for row in episodes if row["net_y"] < 0]
    cross_presses = blue_summary["input_edges"]["cross_press"]
    blue_square_presses = blue_summary["input_edges"]["square_press"]
    creations = []
    for event in blue_summary["plant_creations"]:
        prior_cross = nearest_prior(cross_presses, event["movie_frame"])
        raise_episode = next((row for row in raises
                              if row["end_movie_frame"] == event["movie_frame"]), None)
        creations.append({
            **event,
            "nearest_prior_cross_press": prior_cross,
            "cross_to_creation_frames": event["movie_frame"] - prior_cross,
            "seed_raise_episode": raise_episode,
        })
    a14_finding = {
        "movie": blue_movie,
        "mobile_seed_slot": blue_slot,
        "mobile_seed_address": f"0x{0x80000000 + ACTOR_BASE + blue_slot * ACTOR_STRIDE:08x}",
        "creations": creations,
        "bounded_observation": (
            "Four typed plant-slot creations coincide with the final boundary of four "
            "large positive seed-y episodes and advance the plant cursor by one. Each "
            "follows a cross press; frame boundaries do not identify the gate or writer."),
    }

    retirements = []
    for event in blue_summary["plant_retirements"]:
        descent = max((row for row in descents
                       if row["end_movie_frame"] < event["movie_frame"]),
                      key=lambda row: row["end_movie_frame"], default=None)
        square = nearest_prior(blue_square_presses,
                               descent["start_movie_frame"] if descent else event["movie_frame"])
        retirements.append({
            **event,
            "nearest_prior_square_press": square,
            "square_to_descent_frames": (
                descent["start_movie_frame"] - square if descent and square is not None else None),
            "seed_descent_episode": descent,
            "retirement_after_descent_frames": (
                event["movie_frame"] - descent["end_movie_frame"] if descent else None),
        })
    a15_finding = {
        "movie": blue_movie,
        "mobile_seed_slot": blue_slot,
        "retirements": retirements,
        "retirement_phase_raw_values": [row["phase_after"] for row in retirements],
        "bounded_observation": (
            "Four typed retirements follow four large negative seed-y episodes and prior "
            "square presses. Three type-7 retirements retain raw slot byte +0x2E value 5, "
            "but the type-6 retirement retains 13; value 5 is therefore not a universal "
            "player-uproot signature. Exact teardown writers remain unresolved."),
    }

    findings = {
        "A09_seed_pickup_drop": a09_finding,
        "A14_plant_seed": a14_finding,
        "A15_uproot_plant": a15_finding,
    }
    external_document = {
        "_comment": "External game-derived cross-movie index; preserve outside Git.",
        "schema": CONFIGURATION["external_index"]["schema"],
        "generated": stable_generated(external_output),
        "selected_rows": list(SELECTED_ROWS),
        "reader": reader_info,
        "selection_snapshot": CONFIGURATION["selection_snapshot"],
        "capsule_index_sha256": common.sha256(CAPSULE_PATH),
        "capsules": details,
    }
    external_bytes = render(external_document)
    external_hash = hashlib.sha256(external_bytes).hexdigest()
    source_dependencies = {
        "analysis/phase4_trace_capsule_set.json": common.sha256(CAPSULE_PATH),
        "config/phase4_offline_seed_lifecycle_batch.yaml": common.sha256(CONFIG_PATH),
        "tools/phase4_offline_contact_batch.py": common.sha256(
            common.ROOT / "tools/phase4_offline_contact_batch.py"),
        "tools/phase4_offline_seed_lifecycle_batch.py": common.sha256(Path(__file__)),
    }
    summary_document = {
        "_comment": "Non-copyrighted preservation manifest and bounded findings for the three-row Phase-4 seed lifecycle batch; frame boundaries are not exact writer evidence.",
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(OUTPUT),
        "source_dependencies": source_dependencies,
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
                "python3 tools/phase4_offline_seed_lifecycle_batch.py "
                f"--external-output {external_output} --write"),
            "capsule_count": len(selected_capsules),
            "reconstructed_records": sum(row["records"] for row in summaries),
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
        "capsule_summaries": [tracked_capsule_summary(row) for row in summaries],
        "derived_findings": findings,
        "bounded_conclusions": [
            "Both relevant capsules reconstruct under the exact pinned reader without a record-count or domain-hash error.",
            "The actor pool base is 0x8009FD80; the mobile A09 seed occupies slot 20 while the moving blue seed occupies slot 1 at fixture-specific address 0x8009FE04.",
            "A09 retains three exact attachment intervals and successful post-press releases followed by horizontal stored-velocity component reversals and stable positions.",
            "The blue fixture retains four cursor-advancing plant creations, four large seed raises, four large seed descents and four later plant retirements.",
            "Plant slot byte +0x2E is subtype-owned raw lifecycle state: observed retirement values are 5, 5, 13 and 5, so value 5 is not a universal uproot signature.",
            "Frame-boundary correlation does not attribute an exact CPU writer, collision geometry, plant eligibility gate, DMA/GPU/SPU producer or causal control.",
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
        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/seed-lifecycle-v1/index.json")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    external_output = args.external_output.resolve()
    try:
        external, summary = build(external_output)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
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
            print("external Phase-4 seed lifecycle index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 seed lifecycle summary is missing or stale", file=sys.stderr)
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
