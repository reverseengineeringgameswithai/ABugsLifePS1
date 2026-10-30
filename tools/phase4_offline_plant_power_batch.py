#!/usr/bin/env python3
"""Build the external cross-movie index for the plant and player-power batch."""

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
OUTPUT = common.ROOT / "analysis/phase4_offline_plant_power_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_plant_power_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELECTION_ROWS = {
    row["row_id"]: row for row in CONFIGURATION["selection_snapshot"]["rows"]
}
SELF_ARTIFACT = "analysis/phase4_offline_plant_power_batch.json"
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()

PLAYER_BASE = 0x0A6500
PLAYER_SIZE = 0xB0
POWER_STATUS = PLAYER_BASE + 0x90
PLANT_CURSOR = 0x0822B8
PLANT_BASE = 0x090BF0
PLANT_STRIDE = 0x30
PLANT_COUNT = 20
SELECTOR_BASE = 0x07A448
SELECTOR_COUNT = 20


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


def s16(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<h", image, offset)[0]


def s32(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<i", image, offset)[0]


def player_state(image: bytearray) -> dict:
    """Decode the bounded fields without merging 0x800A6590 and 0x800A6592."""
    return {
        "y": s32(image, PLAYER_BASE + 0x04),
        "velocity_y": s32(image, PLAYER_BASE + 0x30),
        "state": u16(image, PLAYER_BASE + 0x80),
        "grounded": u16(image, PLAYER_BASE + 0x82),
        "power_status_low_u16": u16(image, POWER_STATUS),
        "power_aux_raw_s16": s16(image, POWER_STATUS + 2),
        "health": s16(image, PLAYER_BASE + 0x94),
        "lives": u8(image, PLAYER_BASE + 0xA0),
    }


def plant_state(image: bytearray) -> list[dict]:
    return [{
        "slot": slot,
        "type": u16(image, PLANT_BASE + slot * PLANT_STRIDE),
        "expiry": u8(image, PLANT_BASE + slot * PLANT_STRIDE + 0x2E),
    } for slot in range(PLANT_COUNT)]


def selector_matrix(image: bytearray) -> list[list[int]]:
    return [[u16(image, SELECTOR_BASE + slot * 4),
             u16(image, SELECTOR_BASE + slot * 4 + 2)]
            for slot in range(SELECTOR_COUNT)]


def matrix_sha(matrix: list[list[int]]) -> str:
    payload = json.dumps(matrix, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def frame_register_sha(registers: dict[str, int]) -> str:
    payload = json.dumps(registers, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def intersects(runs: list[tuple[int, bytes]], offset: int, length: int) -> bool:
    end = offset + length
    return any(start < end and start + len(data) > offset for start, data in runs)


def transition(before: dict, after: dict, fields: tuple[str, ...]) -> dict:
    return {key: {"before": before[key], "after": after[key]}
            for key in fields if before[key] != after[key]}


def close_run(runs: list[dict], value: int, first: dict, last: dict) -> None:
    runs.append({
        "value": value,
        "start_movie_frame": first["movie_frame"],
        "end_movie_frame": last["movie_frame"],
        "records": last["record_index"] - first["record_index"] + 1,
    })


def scan_capsule(reader, capsule_row: dict) -> tuple[dict, dict]:
    directory = Path(capsule_row["capsule_directory"])
    manifest_path = directory / "manifest.json"
    if common.sha256(manifest_path) != capsule_row["capsule_manifest_sha256"]:
        raise ValueError(f"capsule manifest pin mismatch: {manifest_path}")
    capsule = reader.Capsule(directory)

    external_frames: list[dict] = []
    hotspots: Counter[int] = Counter()
    domain_frames: Counter[str] = Counter()
    domain_bytes: Counter[str] = Counter()
    player_events: list[dict] = []
    plant_type_events: list[dict] = []
    cursor_events: list[dict] = []
    selector_events: list[dict] = []
    status_runs: list[dict] = []
    selector_snapshots: dict[str, list[list[int]]] = {}
    prior_player = prior_plants = prior_selector = None
    prior_cursor = None
    run_value = None
    run_first = run_last = None
    first_player = last_player = None
    first_register = last_register = None

    for record_index, item in enumerate(capsule.frames()):
        ram = item.state["ram"]
        current_player = player_state(ram)
        current_plants = plant_state(ram)
        current_cursor = u8(ram, PLANT_CURSOR)
        current_selector = selector_matrix(ram)
        current_selector_sha = matrix_sha(current_selector)
        selector_snapshots.setdefault(current_selector_sha, current_selector)
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
            "player_block_changed": intersects(
                item.changes["ram"], PLAYER_BASE, PLAYER_SIZE),
            "power_status_range_changed": intersects(
                item.changes["ram"], POWER_STATUS, 4),
            "plant_pool_changed": intersects(
                item.changes["ram"], PLANT_BASE, PLANT_STRIDE * PLANT_COUNT),
            "plant_cursor_changed": intersects(
                item.changes["ram"], PLANT_CURSOR, 1),
            "selector_matrix_changed": intersects(
                item.changes["ram"], SELECTOR_BASE, SELECTOR_COUNT * 4),
            "vram_changed": bool(item.changes["vram"]),
            "spu_ram_changed": bool(item.changes["spu"]),
        }
        register_sha = frame_register_sha(item.registers)
        first_player = first_player or current_player
        last_player = current_player
        first_register = first_register or register_sha
        last_register = register_sha

        frame_ref = {
            "record_index": record_index,
            "movie_frame": item.movie_frame,
            "emulator_frame": item.frame,
            "cycle": item.cycle,
            "pc": f"0x{item.pc:08x}",
        }
        status = current_player["power_status_low_u16"]
        if run_value is None:
            run_value, run_first = status, frame_ref
        elif status != run_value:
            close_run(status_runs, run_value, run_first, run_last)
            run_value, run_first = status, frame_ref
        run_last = frame_ref

        if prior_player is not None:
            fields = transition(prior_player, current_player, (
                "state", "grounded", "power_status_low_u16", "power_aux_raw_s16",
                "health", "lives", "y", "velocity_y"))
            decisive = {key: value for key, value in fields.items()
                        if key in ("state", "grounded", "power_status_low_u16",
                                   "power_aux_raw_s16", "health", "lives")}
            if decisive:
                player_events.append({
                    **{key: frame_ref[key] for key in
                       ("movie_frame", "emulator_frame", "cycle", "pc")},
                    "fields": decisive,
                    "correlations": correlations,
                    "top_frame_blocks": [
                        {"pc": f"0x{pc:08x}", "count": count}
                        for pc, count in frame_hotspots.most_common(8)],
                })
            for before, after in zip(prior_plants, current_plants):
                if before["type"] != after["type"]:
                    plant_type_events.append({
                        **{key: frame_ref[key] for key in
                           ("movie_frame", "emulator_frame", "cycle", "pc")},
                        "slot": after["slot"],
                        "before_type": before["type"],
                        "after_type": after["type"],
                        "before_expiry": before["expiry"],
                        "after_expiry": after["expiry"],
                        "cursor_before": prior_cursor,
                        "cursor_after": current_cursor,
                        "correlations": correlations,
                    })
            if prior_cursor != current_cursor:
                cursor_events.append({
                    "movie_frame": item.movie_frame,
                    "before": prior_cursor,
                    "after": current_cursor,
                    "plant_type_changes": sum(
                        left["type"] != right["type"]
                        for left, right in zip(prior_plants, current_plants)),
                })
            if prior_selector != current_selector:
                selector_events.append({
                    "movie_frame": item.movie_frame,
                    "before_sha256": matrix_sha(prior_selector),
                    "after_sha256": current_selector_sha,
                })

        external_frames.append({
            **frame_ref,
            "register_sha256": register_sha,
            "domain_sha256": item.hashes,
            "changed": changed,
            "range_correlations": correlations,
            "player": current_player,
            "plant_cursor": current_cursor,
            "active_plants": [row for row in current_plants if row["type"]],
            "selector_matrix_sha256": current_selector_sha,
            "top_frame_blocks": [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in frame_hotspots.most_common(12)],
        })
        prior_player = current_player
        prior_plants = current_plants
        prior_cursor = current_cursor
        prior_selector = current_selector

    records = len(external_frames)
    if run_value is not None:
        close_run(status_runs, run_value, run_first, run_last)
    expected_records = int(capsule_row["frames"]) + 1
    if records != expected_records:
        raise ValueError(
            f"{capsule_row['movie']}: reconstructed {records} records, "
            f"expected {expected_records}")

    jump_episodes = []
    active = None
    for frame in external_frames:
        state = frame["player"]
        if active is None and state["grounded"] == 0 and state["velocity_y"] < 0:
            prior = external_frames[frame["record_index"] - 1] if frame["record_index"] else None
            if prior and prior["player"]["grounded"] != 0:
                active = {
                    "takeoff_movie_frame": frame["movie_frame"],
                    "takeoff_y": state["y"],
                    "takeoff_velocity_y": state["velocity_y"],
                    "takeoff_status_low_u16": state["power_status_low_u16"],
                    "apex_movie_frame": frame["movie_frame"],
                    "apex_y": state["y"],
                }
        if active is not None:
            if state["y"] < active["apex_y"]:
                active["apex_y"] = state["y"]
                active["apex_movie_frame"] = frame["movie_frame"]
            if (frame["movie_frame"] > active["takeoff_movie_frame"]
                    and state["grounded"] != 0):
                active["landing_movie_frame"] = frame["movie_frame"]
                active["airborne_records"] = (
                    frame["record_index"]
                    - next(row["record_index"] for row in external_frames
                           if row["movie_frame"] == active["takeoff_movie_frame"]))
                jump_episodes.append(active)
                active = None

    creations = [event for event in plant_type_events
                 if event["before_type"] == 0 and event["after_type"] != 0]
    retirements = [event for event in plant_type_events
                   if event["before_type"] != 0 and event["after_type"] == 0]
    summary = {
        "movie": capsule_row["movie"],
        "movie_sha256": capsule_row["movie_sha256"],
        "start_state": capsule_row["start_state"],
        "capsule_manifest_sha256": capsule_row["capsule_manifest_sha256"],
        "capsule_tree_sha256": capsule_row["capsule_tree_sha256"],
        "records": records,
        "movie_frames": capsule_row["frames"],
        "first_player": first_player,
        "last_player": last_player,
        "first_register_sha256": first_register,
        "last_register_sha256": last_register,
        "domain_change_frames": dict(domain_frames),
        "domain_changed_bytes_sum": dict(domain_bytes),
        "status_values_low_u16": sorted({
            frame["player"]["power_status_low_u16"] for frame in external_frames}),
        "power_aux_raw_s16_range": [
            min(frame["player"]["power_aux_raw_s16"] for frame in external_frames),
            max(frame["player"]["power_aux_raw_s16"] for frame in external_frames),
        ],
        "status_runs": status_runs,
        "player_typed_events": player_events,
        "plant_type_events": plant_type_events,
        "plant_creations": creations,
        "plant_retirements": retirements,
        "cursor_events": cursor_events,
        "selector_matrix_snapshots": selector_snapshots,
        "selector_matrix_events": selector_events,
        "jump_episodes": jump_episodes,
        "top_hotspots": [
            {"pc": f"0x{pc:08x}", "count": count}
            for pc, count in hotspots.most_common(40)],
    }
    external = {
        "movie": capsule_row["movie"],
        "summary": summary,
        "frames": external_frames,
    }
    return external, summary


def source_errors(queue: dict, capsules: dict) -> tuple[list[str], list[dict], dict[str, list[str]]]:
    errors = []
    if CONFIGURATION.get("schema") != "abl-phase4-offline-plant-power-batch-source/1":
        errors.append("offline plant/power batch source schema is invalid")
    if not queue.get("valid") or queue.get("errors"):
        errors.append("offline opportunity queue is invalid")
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
            actual_rank = (row.get("priority") or {}).get("rank")
            if actual_rank != snapshot["queue_rank"]:
                errors.append(
                    f"selected row rank changed: {row_id} is {actual_rank}, "
                    f"expected {snapshot['queue_rank']}")
        for capsule in row.get("relevant_capsules") or []:
            movie_to_rows.setdefault(capsule["movie"], []).append(row_id)
    capsule_by_movie = {row["movie"]: row for row in capsules.get("capsules") or []}
    try:
        selected = [capsule_by_movie[movie] for movie in sorted(movie_to_rows)]
    except KeyError as exc:
        errors.append(f"selected capsule absent from capsule index: {exc}")
        selected = []
    if len(selected) != int(CONFIGURATION["expected_unique_capsules"]):
        errors.append(
            f"selected cluster has {len(selected)} unique capsules, expected "
            f"{CONFIGURATION['expected_unique_capsules']}")
    if [SELECTION_ROWS[row_id]["queue_rank"] for row_id in SELECTED_ROWS] != [1, 2, 3, 4, 5]:
        errors.append("selection snapshot does not retain ranks 1 through 5")
    return errors, selected, movie_to_rows


def event_fields(summary: dict, field: str) -> list[dict]:
    return [event for event in summary["player_typed_events"] if field in event["fields"]]


def tracked_capsule_summary(summary: dict) -> dict:
    """Retain pins and aggregate facts; detailed events stay in the external index."""
    keys = (
        "movie", "movie_sha256", "start_state", "capsule_manifest_sha256",
        "capsule_tree_sha256", "records", "movie_frames", "first_player",
        "last_player", "first_register_sha256", "last_register_sha256",
        "domain_change_frames", "domain_changed_bytes_sum",
        "status_values_low_u16", "power_aux_raw_s16_range", "top_hotspots",
        "queue_rows",
    )
    return {
        **{key: summary[key] for key in keys},
        "player_typed_event_count": len(summary["player_typed_events"]),
        "health_event_count": len(event_fields(summary, "health")),
        "life_event_count": len(event_fields(summary, "lives")),
        "plant_creation_count": len(summary["plant_creations"]),
        "plant_retirement_count": len(summary["plant_retirements"]),
        "cursor_event_count": len(summary["cursor_events"]),
        "selector_matrix_sha256": sorted(summary["selector_matrix_snapshots"]),
        "selector_change_event_count": len(summary["selector_matrix_events"]),
        "jump_episode_count": len(summary["jump_episodes"]),
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

    details, summaries = [], []
    for capsule in selected_capsules:
        detail, summary = scan_capsule(reader, capsule)
        rows = sorted(movie_to_rows[capsule["movie"]])
        detail["queue_rows"] = rows
        summary["queue_rows"] = rows
        details.append(detail)
        summaries.append(summary)

    queue_rows = {row["row_id"]: row for row in queue["rows"]}
    row_movies = {
        row_id: [item["movie"] for item in queue_rows[row_id]["relevant_capsules"]]
        for row_id in SELECTED_ROWS
    }
    exact_queries = {
        row_id: queue_rows[row_id]["offline_batch_queries"] for row_id in SELECTED_ROWS
    }
    summary_by_movie = {row["movie"]: row for row in summaries}
    a13_movies = row_movies["A13_cycle_plant_output"]
    b06_movie = next(movie for movie in row_movies["B06_invincibility"]
                     if "/b06_" in movie.lower())
    b07_movie = next(movie for movie in row_movies["B07_health_power"]
                     if "/B07_" in movie)
    b08_movie = next(movie for movie in row_movies["B08_bubble_shield"]
                     if "/B08_" in movie)
    b09_movie = next(movie for movie in row_movies["B09_super_jump"]
                     if "/B09_" in movie)

    table_variants: dict[str, dict] = {}
    for movie in a13_movies:
        summary = summary_by_movie[movie]
        for digest, matrix in summary["selector_matrix_snapshots"].items():
            table_variants.setdefault(digest, {"matrix": matrix, "movies": []})[
                "movies"].append(movie)
    a13_findings = {
        "movies": [{
            "movie": movie,
            "creation_frames": [event["movie_frame"] for event in
                                summary_by_movie[movie]["plant_creations"]],
            "creation_types": [event["after_type"] for event in
                               summary_by_movie[movie]["plant_creations"]],
            "retirement_frames": [event["movie_frame"] for event in
                                  summary_by_movie[movie]["plant_retirements"]],
            "cursor_events": summary_by_movie[movie]["cursor_events"],
            "selector_matrix_sha256": sorted(
                summary_by_movie[movie]["selector_matrix_snapshots"]),
            "selector_change_events": summary_by_movie[movie]["selector_matrix_events"],
        } for movie in a13_movies],
        "creation_count": sum(len(summary_by_movie[movie]["plant_creations"])
                              for movie in a13_movies),
        "retirement_count": sum(len(summary_by_movie[movie]["plant_retirements"])
                                for movie in a13_movies),
        "selector_variants": table_variants,
        "bounded_observation": (
            "Typed slot creation/retirement and cursor boundaries are reconstructed "
            "for all five retained A13 movies. Selector contents have more than one "
            "pristine-control-matched runtime variant, so the resident address is not "
            "treated as one immutable cross-fixture table."),
    }

    def power_finding(movie: str) -> dict:
        row = summary_by_movie[movie]
        return {
            "movie": movie,
            "health_initial": row["first_player"]["health"],
            "health_final": row["last_player"]["health"],
            "health_events": event_fields(row, "health"),
            "lives_events": event_fields(row, "lives"),
            "status_values_low_u16": row["status_values_low_u16"],
            "status_runs": row["status_runs"],
            "power_aux_raw_s16_range": row["power_aux_raw_s16_range"],
        }

    b06 = power_finding(b06_movie)
    b06["bounded_observation"] = (
        "Health remains 4 while the decoded low status halfword and the adjacent "
        "raw signed halfword traverse several intervals; no retained boundary "
        "identifies an attack source, invincibility owner, timer writer or denial control.")
    b07 = power_finding(b07_movie)
    b07["bounded_observation"] = (
        "Health changes from 3 to 4 at one retained boundary inside a broader "
        "low-status interval; same-frame evidence does not identify the health-power owner.")
    b08 = power_finding(b08_movie)
    b08["bounded_observation"] = (
        "Two retained health-decrement boundaries coincide with low-status/auxiliary "
        "transitions; the capsule does not establish bubble ownership, absorption, "
        "attack ownership or a counterfactual protection control.")
    b09 = power_finding(b09_movie)
    b09["jump_episodes"] = summary_by_movie[b09_movie]["jump_episodes"]
    b09["bounded_observation"] = (
        "One movie contains two grounded-to-airborne episodes. The episode under "
        "low status 32 has a more-negative retained takeoff velocity and apex than "
        "the status-0 episode; frame boundaries do not identify the enabling writer.")

    findings = {
        "A13_cycle_plant_output": a13_findings,
        "B06_invincibility": b06,
        "B07_health_power": b07,
        "B08_bubble_shield": b08,
        "B09_super_jump": b09,
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
        "config/phase4_offline_plant_power_batch.yaml": common.sha256(CONFIG_PATH),
        "tools/phase4_offline_plant_power_batch.py": common.sha256(Path(__file__)),
    }
    summary_document = {
        "_comment": "Non-copyrighted preservation manifest and bounded findings for the five-row Phase-4 plant/power batch; frame boundaries are not exact writer evidence.",
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
                "python3 tools/phase4_offline_plant_power_batch.py "
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
            "All nine relevant capsules reconstruct under the exact pinned reader without a record-count or domain-hash error.",
            "The four bytes at 0x800A6590 are retained as an unsigned low status halfword plus an adjacent raw signed halfword; this batch does not merge them into one semantic flags value.",
            "Five A13 movies retain typed plant slot/cursor transitions and two selector-matrix variants; table residency is qualified by fixture/runtime state.",
            "B07 retains one health increment, B08 retains two health decrements, and B09 retains paired status-0/status-32 jump episodes.",
            "Frame-boundary correlation does not attribute an exact CPU writer, plant/power owner, attack source, DMA/GPU/SPU producer or causal control.",
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
        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/plant-powers-v1/index.json")
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
            print("external Phase-4 plant/power index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 plant/power summary is missing or stale", file=sys.stderr)
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
