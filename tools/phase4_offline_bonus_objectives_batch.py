#!/usr/bin/env python3
"""Build the external cross-movie frame index for the three bonus objectives."""

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
import phase4_offline_seed_lifecycle_batch as input_index


QUEUE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
OUTPUT = common.ROOT / "analysis/phase4_offline_bonus_objectives_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_bonus_objectives_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELECTION_ROWS = {
    row["row_id"]: row for row in CONFIGURATION["selection_snapshot"]["rows"]
}
MOVIE_ROWS = dict(CONFIGURATION["movie_rows"])
SELF_ARTIFACT = "analysis/phase4_offline_bonus_objectives_batch.json"
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()

PLAYER_BASE = 0x0A6500
PLAYER_SIZE = 0xB0
ACTOR_BASE = 0x09FD80
ACTOR_SIZE = 0x2100
CONTACT_BASE = 0x0B0D18
CONTACT_SIZE = 0xE00
OBJECTIVE_BASE = 0x08223C
OBJECTIVE_SIZE = 0x02B0
STATE_FIELDS = (
    "bonus1_stomp_streak", "bonus3_blue_kill_streak",
    "bonus2_mushroom_sequence", "transition_latch", "progress_command",
    "fade_timer", "scene", "bonus_flags", "player_vertical_speed",
    "native_berry_selector",
)


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


def typed_state(ram: bytearray) -> dict:
    return {
        "bonus1_stomp_streak": struct.unpack_from("<I", ram, 0x08223C)[0],
        "bonus3_blue_kill_streak": struct.unpack_from("<I", ram, 0x082240)[0],
        "bonus2_mushroom_sequence": list(struct.unpack_from("<5b", ram, 0x082248)),
        "transition_latch": struct.unpack_from("<h", ram, 0x0823A0)[0],
        "progress_command": struct.unpack_from("<I", ram, 0x082444)[0],
        "fade_timer": struct.unpack_from("<h", ram, 0x082470)[0],
        "scene": struct.unpack_from("<I", ram, 0x082504)[0],
        "bonus_flags": ram[0x09B889],
        "player_vertical_speed": struct.unpack_from("<i", ram, 0x0A6530)[0],
        "native_berry_selector": ram[0x0A6597],
    }


def changed_fields(before: dict | None, after: dict) -> dict:
    if before is None:
        return {}
    return {key: {"before": before[key], "after": after[key]}
            for key in STATE_FIELDS if before[key] != after[key]}


def candidate_flow(flow: list[tuple[int, int, int]]) -> dict[str, dict]:
    result = {}
    for candidate in CONFIGURATION["candidate_ranges"]:
        start, end = int(candidate["start"]), int(candidate["end"])
        blocks = [(pc, count) for pc, count, _ in flow if start <= pc < end]
        decisive = int(candidate["decisive_block_start"])
        result[candidate["name"]] = {
            "hits": sum(count for _, count in blocks),
            "distinct_block_starts": len(blocks),
            "decisive_block_start": f"0x{decisive:08x}",
            "decisive_block_start_covered": any(pc == decisive for pc, _ in blocks),
            "covered_block_starts": [f"0x{pc:08x}" for pc, _ in blocks],
        }
    return result


def movie_pin(queue_rows: dict[str, dict], logical_path: str) -> dict:
    pins = [item for row_id in SELECTED_ROWS
            for item in queue_rows[row_id].get("relevant_movies") or []
            if item["path"] == logical_path]
    identities = {(item["sha256"], item["bytes"], item["declared_start_state"])
                  for item in pins}
    if len(identities) != 1:
        raise ValueError(f"selected rows do not identify one movie pin: {logical_path}")
    return pins[0]


def scan_capsule(reader, capsule_row: dict, pin: dict) -> tuple[dict, dict]:
    directory = Path(capsule_row["capsule_directory"])
    manifest = directory / "manifest.json"
    if common.sha256(manifest) != capsule_row["capsule_manifest_sha256"]:
        raise ValueError(f"capsule manifest pin mismatch: {manifest}")
    if capsule_row["movie_sha256"] != pin["sha256"] or \
            capsule_row["start_state"]["path"] != pin["declared_start_state"]:
        raise ValueError(f"capsule fixture join mismatch: {capsule_row['movie']}")

    capsule = reader.Capsule(directory)
    frames = []
    state_events = []
    hotspots: Counter[int] = Counter()
    domain_frames: Counter[str] = Counter()
    domain_bytes: Counter[str] = Counter()
    candidate_totals: dict[str, Counter[int]] = {
        row["name"]: Counter() for row in CONFIGURATION["candidate_ranges"]}
    prior = None
    first_register = last_register = None
    for record_index, item in enumerate(capsule.frames()):
        state = typed_state(item.state["ram"])
        changes = changed_fields(prior, state)
        frame_hotspots: Counter[int] = Counter()
        for pc, count, _ in item.flow:
            hotspots[pc] += count
            frame_hotspots[pc] += count
            for candidate in CONFIGURATION["candidate_ranges"]:
                if int(candidate["start"]) <= pc < int(candidate["end"]):
                    candidate_totals[candidate["name"]][pc] += count
        domains = {}
        for domain in ("ram", "vram", "spu"):
            runs = item.changes[domain]
            domains[domain] = {
                "runs": len(runs),
                "bytes": sum(len(data) for _, data in runs),
            }
            if runs:
                domain_frames[domain] += 1
                domain_bytes[domain] += domains[domain]["bytes"]
        register_sha = frame_index.frame_register_sha(item.registers)
        first_register = first_register or register_sha
        last_register = register_sha
        reference = {
            "record_index": record_index,
            "movie_frame": item.movie_frame,
            "emulator_frame": item.frame,
            "cycle": item.cycle,
            "pc": f"0x{item.pc:08x}",
        }
        flow = candidate_flow(item.flow)
        frame = {
            **reference,
            "register_sha256": register_sha,
            "domain_sha256": item.hashes,
            "changed": domains,
            "range_correlations": {
                "player_block_changed": frame_index.intersects(
                    item.changes["ram"], PLAYER_BASE, PLAYER_SIZE),
                "actor_pool_changed": frame_index.intersects(
                    item.changes["ram"], ACTOR_BASE, ACTOR_SIZE),
                "contact_pool_changed": frame_index.intersects(
                    item.changes["ram"], CONTACT_BASE, CONTACT_SIZE),
                "objective_state_changed": frame_index.intersects(
                    item.changes["ram"], OBJECTIVE_BASE, OBJECTIVE_SIZE),
                "vram_changed": bool(item.changes["vram"]),
                "spu_ram_changed": bool(item.changes["spu"]),
            },
            "objective_state": state,
            "objective_state_changes": changes,
            "candidate_flow": flow,
            "top_frame_blocks": [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in frame_hotspots.most_common(12)],
        }
        frames.append(frame)
        if changes:
            state_events.append({**reference, "changes": changes,
                                 "candidate_flow": flow})
        prior = state
    expected = int(capsule_row["frames"]) + 1
    if len(frames) != expected:
        raise ValueError(
            f"{capsule_row['movie']}: reconstructed {len(frames)}, expected {expected}")
    summary = {
        "movie": capsule_row["movie"],
        "movie_sha256": capsule_row["movie_sha256"],
        "movie_bytes": pin["bytes"],
        "media_class": pin["media_class"],
        "start_state": capsule_row["start_state"],
        "capsule_manifest_sha256": capsule_row["capsule_manifest_sha256"],
        "capsule_tree_sha256": capsule_row["capsule_tree_sha256"],
        "control_match": capsule_row["control_match"],
        "records": len(frames),
        "movie_frames": capsule_row["frames"],
        "input_edges": input_index.input_edges(pin),
        "domain_change_frames": dict(domain_frames),
        "domain_changed_bytes_sum": dict(domain_bytes),
        "first_register_sha256": first_register,
        "last_register_sha256": last_register,
        "objective_state_event_count": len(state_events),
        "candidate_range_totals": {
            name: {
                "hits": sum(counts.values()),
                "distinct_block_starts": len(counts),
                "covered_block_starts": [f"0x{pc:08x}" for pc in sorted(counts)],
            } for name, counts in candidate_totals.items()},
        "top_hotspots": [{"pc": f"0x{pc:08x}", "count": count}
                         for pc, count in hotspots.most_common(40)],
    }
    return {"movie": capsule_row["movie"], "summary": summary,
            "frames": frames, "objective_state_events": state_events}, summary


def progress_events(detail: dict, field: str, scene_before: int) -> list[dict]:
    events = []
    for event in detail["objective_state_events"]:
        change = event["changes"].get(field)
        if not change:
            continue
        frame = detail["frames"][event["record_index"]]
        if frame["objective_state"]["scene"] != scene_before:
            continue
        events.append({
            "movie_frame": event["movie_frame"],
            "cycle": event["cycle"],
            "before": change["before"],
            "after": change["after"],
            "candidate_flow": event["candidate_flow"],
            "range_correlations": frame["range_correlations"],
        })
    return events


def first_change(detail: dict, field: str, after) -> dict:
    return next(event for event in detail["objective_state_events"]
                if (event["changes"].get(field) or {}).get("after") == after)


def derive_one(detail: dict, row_id: str, progress_field: str,
               scene_before: int) -> dict:
    expected = CONFIGURATION["expected_findings"][row_id]
    progress = progress_events(detail, progress_field, scene_before)
    completion = first_change(detail, "transition_latch", 6)
    scene = first_change(detail, "scene", 16)
    completion_frame = detail["frames"][completion["record_index"]]
    flags = completion["changes"].get("bonus_flags")
    observed = {
        "progress_frames": [row["movie_frame"] for row in progress],
        "progress_values": [row["after"] for row in progress],
        "completion_frame": completion["movie_frame"],
        "scene_16_frame": scene["movie_frame"],
        "flag_before": flags["before"] if flags else None,
        "flag_after": flags["after"] if flags else None,
    }
    if observed != expected:
        raise ValueError(f"{row_id} objective findings drifted: {observed!r}")
    return {
        "movie": detail["movie"],
        "progress_field": progress_field,
        "progress_events": progress,
        "completion": {
            "movie_frame": completion["movie_frame"],
            "cycle": completion["cycle"],
            "state_changes": completion["changes"],
            "objective_state": completion_frame["objective_state"],
            "candidate_flow": completion["candidate_flow"],
        },
        "scene_16_transition": {
            "movie_frame": scene["movie_frame"],
            "cycle": scene["cycle"],
            "frames_after_completion": scene["movie_frame"] - completion["movie_frame"],
        },
        "expected_findings_reproduced": True,
    }


def source_errors(queue: dict, capsules: dict) -> tuple[list[str], list[dict]]:
    errors = []
    if CONFIGURATION.get("schema") != \
            "abl-phase4-offline-bonus-objectives-batch-source/1":
        errors.append("offline bonus-objectives source schema is invalid")
    if not queue.get("valid") or queue.get("errors") or len(queue.get("rows") or []) != 107:
        errors.append("offline queue is invalid or not exactly 107 rows")
    queue_rows = {row["row_id"]: row for row in queue.get("rows") or []}
    selected_movies = set()
    for row_id in SELECTED_ROWS:
        row = queue_rows.get(row_id)
        if not row:
            errors.append(f"selected row missing: {row_id}")
            continue
        prior = {item.get("artifact") for item in row.get("prior_offline_analysis") or []}
        eligible = row.get("current_completion_state") == "open" and (
            row.get("classification") == "offline_ready" or
            (row.get("classification") == "offline_partial" and SELF_ARTIFACT in prior))
        if not eligible:
            errors.append(f"selected row is not current open batch evidence: {row_id}")
        if row.get("classification") == "offline_ready" and \
                (row.get("priority") or {}).get("rank") != SELECTION_ROWS[row_id]["queue_rank"]:
            errors.append(f"selected row rank changed: {row_id}")
        selected_movies.update(item["movie"] for item in row.get("relevant_capsules") or [])
    if selected_movies != set(MOVIE_ROWS):
        errors.append(f"selected capsule movies changed: {sorted(selected_movies)}")
    capsule_by_movie = {row["movie"]: row for row in capsules.get("capsules") or []}
    selected = [capsule_by_movie[movie] for movie in sorted(selected_movies)
                if movie in capsule_by_movie]
    if len(selected) != int(CONFIGURATION["expected_unique_capsules"]):
        errors.append(f"selected cluster has {len(selected)} capsules, expected 3")
    return errors, selected


def tracked_summary(summary: dict) -> dict:
    keys = ("movie", "movie_sha256", "movie_bytes", "media_class", "start_state",
            "capsule_manifest_sha256", "capsule_tree_sha256", "control_match",
            "records", "movie_frames", "domain_change_frames",
            "domain_changed_bytes_sum", "first_register_sha256",
            "last_register_sha256", "objective_state_event_count",
            "candidate_range_totals", "top_hotspots")
    return {**{key: summary[key] for key in keys},
            "input_edge_counts": {key: len(value)
                                  for key, value in summary["input_edges"].items()}}


def build(external_output: Path) -> tuple[dict, dict]:
    queue = common.load_json(QUEUE_PATH)
    capsules = common.load_json(CAPSULE_PATH)
    errors, selected = source_errors(queue, capsules)
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
    details, summaries = {}, {}
    for capsule in selected:
        movie = capsule["movie"]
        detail, summary = scan_capsule(reader, capsule, movie_pin(queue_rows, movie))
        details[movie], summaries[movie] = detail, summary
    findings = {
        "F16_bonus1_spiders": derive_one(
            details["movies/Bonus_Level_01.movie.json"],
            "F16_bonus1_spiders", "bonus1_stomp_streak", 17),
        "F17_bonus2_mushrooms": derive_one(
            details["movies/Bonus_Level_02.movie.json"],
            "F17_bonus2_mushrooms", "bonus2_mushroom_sequence", 1),
        "F18_bonus3_grasshoppers": derive_one(
            details["movies/Bonus_Level_03.movie.json"],
            "F18_bonus3_grasshoppers", "bonus3_blue_kill_streak", 3),
    }
    findings["C18_bonus_entry"] = {
        "source_movies": sorted(details),
        "completion_frames": {
            row_id: row["completion"]["movie_frame"]
            for row_id, row in findings.items()},
        "scene_16_frames": {
            row_id: row["scene_16_transition"]["movie_frame"]
            for row_id, row in findings.items()},
        "shared_transition_latch": 6,
        "shared_destination_scene": 16,
        "bounded_observation": (
            "All three natural objective movies reach the shared scene-16 wrapper; "
            "the capsules do not decode its asset-selection or persistence writer."),
    }
    external_document = {
        "_comment": "External game-derived bonus-objective frame index; never commit.",
        "schema": CONFIGURATION["external_index"]["schema"],
        "generated": stable_generated(external_output),
        "selected_rows": list(SELECTED_ROWS),
        "reader": reader_info,
        "capsule_index_sha256": common.sha256(CAPSULE_PATH),
        "capsules": [details[movie] for movie in sorted(details)],
    }
    external_bytes = render(external_document)
    external_hash = hashlib.sha256(external_bytes).hexdigest()
    summary_document = {
        "_comment": "Non-copyrighted summary and preservation manifest for the bonus-objectives offline batch.",
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(OUTPUT),
        "source_dependencies": {
            "analysis/phase4_trace_capsule_set.json": common.sha256(CAPSULE_PATH),
            "config/phase4_offline_bonus_objectives_batch.yaml": common.sha256(CONFIG_PATH),
            "tools/phase4_offline_bonus_objectives_batch.py": common.sha256(Path(__file__)),
        },
        "selection_snapshot": CONFIGURATION["selection_snapshot"],
        "selected_rows": [{
            "row_id": row_id,
            "queue_rank": SELECTION_ROWS[row_id]["queue_rank"],
            "classification": SELECTION_ROWS[row_id]["classification"],
            "completion_state": SELECTION_ROWS[row_id]["completion_state"],
            "capsules": [item["movie"] for item in queue_rows[row_id]["relevant_capsules"]],
        } for row_id in SELECTED_ROWS],
        "offline_batch": {
            "reader_path": str(reader_path),
            "reader_sha256": reader_info["sha256"],
            "generator_command": (
                "python3 tools/phase4_offline_bonus_objectives_batch.py "
                "--external-output " + str(external_output) + " --write"),
            "capsule_count": len(selected),
            "reconstructed_records": sum(row["records"] for row in summaries.values()),
            "domains": ["registers", "ram", "vram", "spu_ram", "block_flow"],
            "exact_queue_queries": {
                row_id: queue_rows[row_id]["offline_batch_queries"]
                for row_id in SELECTED_ROWS},
        },
        "external_index": {
            "absolute_path": str(external_output),
            "sha256": external_hash,
            "bytes": len(external_bytes),
            "schema": external_document["schema"],
            "media_class": "external game-derived evidence; never commit",
            "preservation_required": True,
        },
        "capsule_summaries": [tracked_summary(summaries[movie])
                              for movie in sorted(summaries)],
        "derived_findings": findings,
        "bounded_conclusions": [
            "All three current capsules reconstruct every retained frame boundary under the exact pinned reader.",
            "Natural progress, completion latch 6, unlock-bit mutation and scene-16 entry are reproduced for each challenge.",
            "Passive block flow correlates each completion boundary with its documented resident challenge family, not an exact store cycle.",
            "VRAM and SPU-RAM change points are retained without claiming GPU submission or SPU voice attribution.",
            "Historical native controls remain causal authority for rejected spider impacts, duplicate mushrooms and Bonus-3 miss resets.",
        ],
        "named_unknowns": {
            "C18_bonus_entry": "Scene-16 asset selection, result persistence, and return dispatch are not decoded by the natural frame capsules.",
            "F16_bonus1_spiders": "Qualifying target-family breadth and exact store-cycle attribution remain outside frame-boundary evidence.",
            "F17_bonus2_mushrooms": "The natural movie has no duplicate; duplicate-reset causality remains solely in the retained native control.",
            "F18_bonus3_grasshoppers": "The natural movie has no miss; case-13 reset causality remains solely in the retained native control.",
        },
        "live_escalation_ids": [
            "P4-ITER70-C18-MISSING-CAPSULE", "P4-ITER70-F16-MISSING-CAPSULE",
            "P4-ITER70-F17-MISSING-CAPSULE", "P4-ITER70-F18-MISSING-CAPSULE"],
        "errors": [],
        "valid": True,
    }
    return external_document, summary_document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--external-output", type=Path,
        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/bonus-objectives-v1/index.json")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    external_output = args.external_output.resolve()
    try:
        external, summary = build(external_output)
    except (OSError, ValueError, KeyError, RuntimeError, StopIteration) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    external_bytes, summary_bytes = render(external), render(summary)
    if args.write:
        external_output.parent.mkdir(parents=True, exist_ok=True)
        external_output.write_bytes(external_bytes)
        OUTPUT.write_bytes(summary_bytes)
    elif args.check:
        if not external_output.is_file() or external_output.read_bytes() != external_bytes:
            print("external Phase-4 bonus-objectives index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 bonus-objectives summary is missing or stale", file=sys.stderr)
            return 1
    else:
        print(summary_bytes.decode(), end="")
    print(f"PASS: rows=4 capsules={summary['offline_batch']['capsule_count']} "
          f"records={summary['offline_batch']['reconstructed_records']} "
          f"external_sha256={summary['external_index']['sha256']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
