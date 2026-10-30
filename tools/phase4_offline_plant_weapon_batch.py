#!/usr/bin/env python3
"""Build the external cross-movie index for the yellow-plant weapon batch."""

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
OUTPUT = common.ROOT / "analysis/phase4_offline_plant_weapon_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_plant_weapon_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELECTION_ROWS = {
    row["row_id"]: row for row in CONFIGURATION["selection_snapshot"]["rows"]
}
SELF_ARTIFACT = "analysis/phase4_offline_plant_weapon_batch.json"
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()

PLANT_BASE = 0x090BF0
PLANT_STRIDE = 0x30
PLANT_COUNT = 20
ACTOR_BASE = 0x09FD80
ACTOR_STRIDE = 0x84
ACTOR_COUNT = 64
CONTACT_BASE = 0x0B0D18
CONTACT_STRIDE = 0x38
CONTACT_COUNT = 64
QUOTA = 0x0A658E


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


def frame_register_sha(registers: dict[str, int]) -> str:
    payload = json.dumps(registers, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def intersects(runs: list[tuple[int, bytes]], offset: int, length: int) -> bool:
    end = offset + length
    return any(start < end and start + len(data) > offset for start, data in runs)


def plants(image: bytearray) -> list[dict]:
    result = []
    for slot in range(PLANT_COUNT):
        base = PLANT_BASE + slot * PLANT_STRIDE
        plant_type = u16(image, base)
        if plant_type:
            result.append({
                "slot": slot,
                "type": plant_type,
                "expiry": u8(image, base + 0x2E),
            })
    return result


def allocator_contacts(image: bytearray) -> list[dict]:
    """Decode allocator-occupied records; flags bit 0x80 is not the live gate."""
    result = []
    for slot in range(CONTACT_COUNT):
        base = CONTACT_BASE + slot * CONTACT_STRIDE
        lifetime = u16(image, base + 0x22)
        flags = u8(image, base + 0x33)
        if not lifetime or not flags & 0x80:
            continue
        result.append({
            "slot": slot,
            "x": s32(image, base + 0x00),
            "y": s32(image, base + 0x04),
            "z": s32(image, base + 0x08),
            "velocity_x": s32(image, base + 0x0C),
            "velocity_y": s32(image, base + 0x10),
            "velocity_z": s32(image, base + 0x14),
            "action": u16(image, base + 0x20),
            "lifetime": lifetime,
            "raw_u16_24": u16(image, base + 0x24),
            "secondary_counter": u8(image, base + 0x26),
            "kind": u8(image, base + 0x27),
            "radius_add": s16(image, base + 0x28),
            "state": s16(image, base + 0x2C),
            "flags": flags,
        })
    return result


def typed_slot_changes(before: list[dict], after: list[dict], fields: tuple[str, ...]) -> list[dict]:
    left = {row["slot"]: row for row in before}
    right = {row["slot"]: row for row in after}
    events = []
    for slot in sorted(set(left) | set(right)):
        old = left.get(slot) or {}
        new = right.get(slot) or {}
        changed = {
            field: {"before": old.get(field), "after": new.get(field)}
            for field in fields if old.get(field) != new.get(field)
        }
        if changed:
            events.append({"slot": slot, "fields": changed})
    return events


def scan_capsule(reader, capsule_row: dict) -> tuple[dict, dict]:
    directory = Path(capsule_row["capsule_directory"])
    manifest_path = directory / "manifest.json"
    if common.sha256(manifest_path) != capsule_row["capsule_manifest_sha256"]:
        raise ValueError(f"capsule manifest pin mismatch: {manifest_path}")
    capsule = reader.Capsule(directory)
    external_frames = []
    hotspots: Counter[int] = Counter()
    domain_frames: Counter[str] = Counter()
    domain_bytes: Counter[str] = Counter()
    plant_events = []
    quota_events = []
    actor_hp_events = []
    action2_boundaries = []
    action2_signatures: Counter[tuple[int, int, int]] = Counter()
    previous_plants = previous_actors = None
    previous_quota = None
    first_register = last_register = None

    for record_index, item in enumerate(capsule.frames()):
        ram = item.state["ram"]
        current_plants = plants(ram)
        current_actors = frame_index.actor_records(ram)
        current_contacts = allocator_contacts(ram)
        current_quota = u16(ram, QUOTA)
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
            "plant_pool_changed": intersects(
                item.changes["ram"], PLANT_BASE, PLANT_STRIDE * PLANT_COUNT),
            "actor_pool_changed": intersects(
                item.changes["ram"], ACTOR_BASE, ACTOR_STRIDE * ACTOR_COUNT),
            "contact_pool_changed": intersects(
                item.changes["ram"], CONTACT_BASE, CONTACT_STRIDE * CONTACT_COUNT),
            "quota_changed": intersects(item.changes["ram"], QUOTA, 2),
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
        for contact in current_contacts:
            if contact["action"] == 2:
                signature = (contact["raw_u16_24"], contact["kind"], contact["flags"])
                action2_signatures[signature] += 1
                if contact["lifetime"] == 1:
                    action2_boundaries.append({
                        **frame_ref,
                        "contact": contact,
                        "actor_snapshot": current_actors,
                        "quota": current_quota,
                        "correlations": correlations,
                    })
        if previous_plants is not None:
            for event in typed_slot_changes(
                    previous_plants, current_plants, ("type", "expiry")):
                type_change = event["fields"].get("type")
                if type_change:
                    plant_events.append({
                        **frame_ref,
                        "slot": event["slot"],
                        "before_type": type_change["before"] or 0,
                        "after_type": type_change["after"] or 0,
                        "correlations": correlations,
                    })
            if current_quota != previous_quota:
                quota_events.append({
                    **frame_ref,
                    "before": previous_quota,
                    "after": current_quota,
                    "plants": current_plants,
                    "actors": current_actors,
                    "contacts": current_contacts,
                    "correlations": correlations,
                })
            for event in typed_slot_changes(previous_actors, current_actors, ("id", "hp")):
                if "hp" in event["fields"]:
                    actor_hp_events.append({
                        **frame_ref,
                        "slot": event["slot"],
                        "fields": event["fields"],
                        "plants": current_plants,
                        "action2_contacts": [
                            row for row in current_contacts if row["action"] == 2],
                        "quota": current_quota,
                        "correlations": correlations,
                        "top_frame_blocks": [
                            {"pc": f"0x{pc:08x}", "count": count}
                            for pc, count in frame_hotspots.most_common(8)],
                    })
        external_frames.append({
            **frame_ref,
            "register_sha256": register_sha,
            "domain_sha256": item.hashes,
            "changed": changed,
            "range_correlations": correlations,
            "quota": current_quota,
            "plants": current_plants,
            "actors": current_actors,
            "contacts": current_contacts,
            "top_frame_blocks": [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in frame_hotspots.most_common(12)],
        })
        previous_plants = current_plants
        previous_actors = current_actors
        previous_quota = current_quota

    records = len(external_frames)
    expected = int(capsule_row["frames"]) + 1
    if records != expected:
        raise ValueError(
            f"{capsule_row['movie']}: reconstructed {records} records, expected {expected}")
    summary = {
        "movie": capsule_row["movie"],
        "movie_sha256": capsule_row["movie_sha256"],
        "start_state": capsule_row["start_state"],
        "capsule_manifest_sha256": capsule_row["capsule_manifest_sha256"],
        "capsule_tree_sha256": capsule_row["capsule_tree_sha256"],
        "records": records,
        "movie_frames": capsule_row["frames"],
        "first_register_sha256": first_register,
        "last_register_sha256": last_register,
        "domain_change_frames": dict(domain_frames),
        "domain_changed_bytes_sum": dict(domain_bytes),
        "quota_values": sorted({row["quota"] for row in external_frames}),
        "plant_events": plant_events,
        "quota_events": quota_events,
        "actor_hp_events": actor_hp_events,
        "action2_hit_boundaries": action2_boundaries,
        "action2_signatures": [{
            "raw_u16_24": key[0], "kind": key[1], "flags": key[2], "records": count,
        } for key, count in sorted(action2_signatures.items())],
        "top_hotspots": [
            {"pc": f"0x{pc:08x}", "count": count}
            for pc, count in hotspots.most_common(40)],
    }
    return {"movie": capsule_row["movie"], "summary": summary,
            "frames": external_frames}, summary


def source_errors(queue: dict, capsules: dict) -> tuple[list[str], list[dict], dict[str, list[str]]]:
    errors = []
    if CONFIGURATION.get("schema") != "abl-phase4-offline-plant-weapon-batch-source/1":
        errors.append("offline plant-weapon batch source schema is invalid")
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
            rank = (row.get("priority") or {}).get("rank")
            if rank != snapshot["queue_rank"]:
                errors.append(
                    f"selected row rank changed: {row_id} is {rank}, expected {snapshot['queue_rank']}")
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
    if [SELECTION_ROWS[row]["queue_rank"] for row in SELECTED_ROWS] != [1, 2, 3]:
        errors.append("selection snapshot does not retain ranks 1 through 3")
    return errors, selected, movie_to_rows


def hp_events(summary: dict) -> list[dict]:
    return summary["actor_hp_events"]


def tracked_capsule_summary(summary: dict) -> dict:
    return {
        **{key: summary[key] for key in (
            "movie", "movie_sha256", "start_state", "capsule_manifest_sha256",
            "capsule_tree_sha256", "records", "movie_frames",
            "first_register_sha256", "last_register_sha256",
            "domain_change_frames", "domain_changed_bytes_sum", "quota_values",
            "action2_signatures", "top_hotspots", "queue_rows")},
        "plant_event_count": len(summary["plant_events"]),
        "quota_event_count": len(summary["quota_events"]),
        "actor_hp_event_count": len(summary["actor_hp_events"]),
        "action2_hit_boundary_count": len(summary["action2_hit_boundaries"]),
    }


def plant_episodes(summary: dict, plant_type: int) -> list[dict]:
    creations = [event for event in summary["plant_events"]
                 if event["before_type"] == 0 and event["after_type"] == plant_type]
    retirements = [event for event in summary["plant_events"]
                   if event["before_type"] == plant_type and event["after_type"] == 0]
    result = []
    for creation in creations:
        retirement = next((event for event in retirements
                           if event["slot"] == creation["slot"]
                           and event["movie_frame"] > creation["movie_frame"]), None)
        result.append({
            "slot": creation["slot"],
            "creation_frame": creation["movie_frame"],
            "retirement_frame": retirement["movie_frame"] if retirement else None,
        })
    return result


def event_projection(event: dict) -> dict:
    return {
        "movie_frame": event["movie_frame"],
        "slot": event["slot"],
        "fields": event["fields"],
        "quota": event["quota"],
        "action2_contacts": event["action2_contacts"],
        "correlations": event["correlations"],
        "top_frame_blocks": event["top_frame_blocks"],
    }


def hit_projection(event: dict) -> dict:
    return {
        "movie_frame": event["movie_frame"],
        "contact": event["contact"],
        "quota": event["quota"],
        "correlations": event["correlations"],
    }


def quota_projection(event: dict) -> dict:
    return {
        "movie_frame": event["movie_frame"],
        "before": event["before"],
        "after": event["after"],
        "plants": event["plants"],
        "correlations": event["correlations"],
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
    row_movies = {row_id: [item["movie"] for item in
                           queue_rows[row_id]["relevant_capsules"]]
                  for row_id in SELECTED_ROWS}
    summary_by_movie = {row["movie"]: row for row in summaries}
    shared = set(row_movies[SELECTED_ROWS[0]])
    for row_id in SELECTED_ROWS[1:]:
        shared.intersection_update(row_movies[row_id])
    if len(shared) != 1:
        raise ValueError(f"plant-weapon cluster has {len(shared)} shared capsules, expected 1")
    yellow_movie = next(iter(shared))
    dedicated_movies = {}
    for row_id in SELECTED_ROWS:
        unique = set(row_movies[row_id]) - shared
        if len(unique) != 1:
            raise ValueError(
                f"{row_id} has {len(unique)} dedicated capsules, expected 1")
        dedicated_movies[row_id] = next(iter(unique))
    b11_movie = dedicated_movies["B11_blue_berry_shooter"]
    b12_movie = dedicated_movies["B12_homing_shooter"]
    b13_movie = dedicated_movies["B13_mine_plant"]
    yellow = summary_by_movie[yellow_movie]
    b11 = summary_by_movie[b11_movie]
    b12 = summary_by_movie[b12_movie]
    b13 = summary_by_movie[b13_movie]

    def selected_hp(summary: dict, frames: set[int]) -> list[dict]:
        return [event_projection(event) for event in hp_events(summary)
                if event["movie_frame"] in frames]

    findings = {
        "B11_blue_berry_shooter": {
            "dedicated_movie": b11_movie,
            "plant_type_14_episodes": plant_episodes(b11, 14),
            "actor_hp_boundaries": selected_hp(b11, {398, 448}),
            "quota_values": b11["quota_values"],
            "action2_hit_boundaries": [
                hit_projection(event) for event in b11["action2_hit_boundaries"]
                if event["movie_frame"] == 398],
            "bounded_observation": (
                "The dedicated capsule retains a type-14 plant from frame 42, "
                "raw-u16-0x24 value 110/action-2 contact state at the frame-398 "
                "actor HP boundary, and a constant quota. This is frame-boundary "
                "correlation, not projectile ownership or hit-writer attribution."),
        },
        "B12_homing_shooter": {
            "dedicated_movie": b12_movie,
            "plant_type_13_episodes": plant_episodes(b12, 13),
            "actor_hp_boundaries": selected_hp(b12, {668, 716, 1216, 1218}),
            "quota_values": b12["quota_values"],
            "action2_hit_boundaries": [
                hit_projection(event) for event in b12["action2_hit_boundaries"]
                if event["movie_frame"] in {668, 1216}],
            "bounded_observation": (
                "The dedicated capsule retains a type-13 plant from frame 288, "
                "raw-u16-0x24 value 124/action-2 contact state at two actor HP "
                "boundaries, and a constant quota. The passive frames do not prove "
                "homing, target selection, ownership, or the exact hit writer."),
        },
        "B13_mine_plant": {
            "shared_movie": yellow_movie,
            "plant_type_11_episodes": plant_episodes(yellow, 11),
            "shared_quota_boundaries": [
                quota_projection(event) for event in yellow["quota_events"]],
            "shared_actor_hp_boundaries": selected_hp(yellow, {1848}),
            "dedicated_movie": b13_movie,
            "dedicated_type_11_episodes": plant_episodes(b13, 11),
            "dedicated_quota_boundaries": b13["quota_events"],
            "dedicated_actor_hp_boundaries": hp_events(b13),
            "bounded_observation": (
                "The shared yellow capsule retains two type-11 episodes: the first "
                "has a frame-1848 quota and actor-HP boundary and retires at frame "
                "1852; the second retires without a quota boundary. The dedicated "
                "B13 capsule contains no type-11, quota, or actor-HP boundary. This "
                "contrast does not identify a fuse, proximity rule, enemy ownership, "
                "collision callback, or kill causality."),
        },
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
    source_dependencies = {
        "analysis/phase4_trace_capsule_set.json": common.sha256(CAPSULE_PATH),
        "config/phase4_offline_plant_weapon_batch.yaml": common.sha256(CONFIG_PATH),
        "config/record_types.yaml": common.sha256(common.ROOT / "config/record_types.yaml"),
        "tools/phase4_offline_contact_batch.py": common.sha256(
            common.ROOT / "tools/phase4_offline_contact_batch.py"),
        "tools/phase4_offline_plant_weapon_batch.py": common.sha256(Path(__file__)),
    }
    summary_document = {
        "_comment": "Non-copyrighted preservation manifest and bounded findings for the three-row Phase-4 yellow-plant weapon batch; frame boundaries are not exact writer evidence.",
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
                "python3 tools/phase4_offline_plant_weapon_batch.py "
                f"--external-output {external_output} --write"),
            "capsule_count": len(selected_capsules),
            "reconstructed_records": sum(row["records"] for row in summaries),
            "domains": CONFIGURATION["external_index"]["domains"],
            "exact_queue_queries": {
                row_id: queue_rows[row_id]["offline_batch_queries"]
                for row_id in SELECTED_ROWS},
        },
        "external_index": {
            "absolute_path": str(external_output),
            "sha256": hashlib.sha256(external_bytes).hexdigest(),
            "bytes": len(external_bytes),
            "media_class": "external game-derived evidence; never commit",
            "schema": external_document["schema"],
            "preservation_required": True,
        },
        "capsule_summaries": [tracked_capsule_summary(row) for row in summaries],
        "derived_findings": findings,
        "bounded_conclusions": [
            "All four unique relevant capsules reconstruct under the exact pinned reader without a record-count or domain-hash error.",
            "B11 and B12 retain distinct action-2/raw-u16-0x24 contact signatures at named actor-HP boundaries while their enemy quota values remain constant.",
            "The shared yellow capsule retains both a quota-changing first type-11 episode and a no-quota-change second episode; the dedicated B13 capsule is a negative frame-domain observation.",
            "Frame-boundary correlation does not attribute an exact CPU writer, projectile owner, target selector, collision callback, fuse, DMA/GPU/SPU producer, or causal control.",
        ],
        "named_unknowns": {
            row_id: queue_rows[row_id]["named_unknowns"] for row_id in SELECTED_ROWS},
        "live_escalation": None,
        "errors": [],
        "valid": True,
    }
    return external_document, summary_document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--external-output", type=Path,
        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/plant-weapons-v1/index.json")
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
            print("external Phase-4 plant-weapon index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 plant-weapon summary is missing or stale", file=sys.stderr)
            return 1
    else:
        print(summary_bytes.decode(), end="")
    print(
        f"PASS: rows={len(SELECTED_ROWS)} "
        f"capsules={summary['offline_batch']['capsule_count']} "
        f"records={summary['offline_batch']['reconstructed_records']} "
        f"external_sha256={summary['external_index']['sha256']}",
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
