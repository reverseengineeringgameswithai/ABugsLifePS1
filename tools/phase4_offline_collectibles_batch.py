#!/usr/bin/env python3
"""Build the external four-row Phase-4 collectibles/equipment offline index."""

from __future__ import annotations

import argparse
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
OUTPUT = common.ROOT / "analysis/phase4_offline_collectibles_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_collectibles_batch.yaml"
CAMERA_CONFIG_PATH = common.ROOT / "config/phase4_camera_controls.yaml"
SEMANTIC_CONFIG_PATH = common.ROOT / "config/semantic_state.yaml"
CONTACT_TOOL_PATH = common.ROOT / "tools/phase4_offline_contact_batch.py"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELECTION_ROWS = {
    row["row_id"]: row for row in CONFIGURATION["selection_snapshot"]["rows"]
}
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()

CONTACT_BASE = 0x0B0D18
CONTACT_STRIDE = 0x38
CONTACT_COUNT = 64
HEALTH_DISPLAY = 0x0A7E2A
CAMERA_MODE = 0x082220
CAMERA_ORBIT_BIAS = 0x082280
CAMERA_VERTICAL_TARGET = 0x082460
CAMERA_RECORD = 0x095358
OBJECT_POINTER = 0x096B98
SELF_ARTIFACT = "analysis/phase4_offline_collectibles_batch.json"


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


def u32(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<I", image, offset)[0]


def s32(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<i", image, offset)[0]


def raw_contacts(image: bytearray) -> list[dict]:
    rows = []
    for slot in range(CONTACT_COUNT):
        base = CONTACT_BASE + slot * CONTACT_STRIDE
        rows.append({
            "slot": slot,
            "x": s32(image, base + 0x00),
            "y": s32(image, base + 0x04),
            "z": s32(image, base + 0x08),
            "action": u16(image, base + 0x20),
            "active_gate": u16(image, base + 0x22),
            "kind": u8(image, base + 0x27),
            "radius_add": s16(image, base + 0x28),
            "state": s16(image, base + 0x2C),
            "flags": u8(image, base + 0x33),
        })
    return rows


def camera_state(image: bytearray) -> dict:
    base = CAMERA_RECORD
    return {
        "mode": s32(image, CAMERA_MODE),
        "position": [s32(image, base + offset) for offset in (0x00, 0x04, 0x08)],
        "target": [s32(image, base + offset) for offset in (0x0C, 0x10, 0x14)],
        "distance": u16(image, base + 0x1E),
        "orbit_yaw": u16(image, base + 0x20),
        "profile_suppression": u16(image, base + 0x22),
        "pitch_scale": s16(image, base + 0x24),
        "vertical_angle": u16(image, base + 0x2A),
        "orbit_bias": s32(image, CAMERA_ORBIT_BIAS),
        "vertical_target": s32(image, CAMERA_VERTICAL_TARGET),
        "object_pointer": f"0x{u32(image, OBJECT_POINTER):08x}",
    }


def changed(before: dict, after: dict) -> dict:
    return {
        key: {"before": before[key], "after": after[key]}
        for key in sorted(after) if before.get(key) != after.get(key)
    }


def targeted_scan(reader, capsule_row: dict, grain_frames: set[int],
                  include_camera: bool) -> dict:
    capsule = reader.Capsule(Path(capsule_row["capsule_directory"]))
    prior_contacts = None
    prior_camera = None
    prior_display = None
    first_display = None
    grain_boundaries = []
    display_events = []
    camera_changes = []
    camera_values: dict[str, set] = {
        key: set() for key in (
            "mode", "distance", "orbit_yaw", "profile_suppression", "pitch_scale",
            "vertical_angle", "orbit_bias", "vertical_target", "object_pointer")
    }
    records = 0
    for item in capsule.frames():
        records += 1
        ram = item.state["ram"]
        player = frame_index.player(ram)
        contacts = raw_contacts(ram)
        display = s16(ram, HEALTH_DISPLAY)
        first_display = display if first_display is None else first_display
        if prior_display is not None and display != prior_display:
            display_events.append({
                "movie_frame": item.movie_frame,
                "before": prior_display,
                "after": display,
            })
        if item.movie_frame in grain_frames and prior_contacts is not None:
            resets = []
            action20 = []
            for old, new in zip(prior_contacts, contacts):
                fields = changed(old, new)
                if not fields:
                    continue
                if (new["action"] == 4 and new["radius_add"] == 100
                        and new["active_gate"] > 0 and old["active_gate"] == 0):
                    resets.append({
                        "slot": new["slot"],
                        "active_gate": new["active_gate"],
                        "state": new["state"],
                        "flags": new["flags"],
                    })
                if (old["action"] == new["action"] == 20
                        and old["active_gate"] > 1 and new["active_gate"] == 1
                        and old["state"] == 22 and new["state"] == 16):
                    distance_squared = sum(
                        (new[axis] - player[axis]) ** 2 for axis in ("x", "y", "z"))
                    action20.append({
                        "slot": new["slot"],
                        "before_active_gate": old["active_gate"],
                        "after_active_gate": new["active_gate"],
                        "before_state": old["state"],
                        "after_state": new["state"],
                        "distance_squared_to_player": distance_squared,
                    })
            grain_boundaries.append({
                "movie_frame": item.movie_frame,
                "effect_record_resets": resets,
                "action20_collection_transitions": action20,
            })
        if include_camera:
            camera = camera_state(ram)
            for key in camera_values:
                value = camera[key]
                camera_values[key].add(tuple(value) if isinstance(value, list) else value)
            delta = camera if prior_camera is None else changed(prior_camera, camera)
            if delta:
                camera_changes.append({
                    "movie_frame": item.movie_frame,
                    "state" if prior_camera is None else "changes": delta,
                })
            prior_camera = camera
        prior_contacts = contacts
        prior_display = display
    if records != int(capsule_row["frames"]) + 1:
        raise ValueError(f"targeted scan record mismatch: {capsule_row['movie']}")
    return {
        "records": records,
        "health_display_first": first_display,
        "health_display_last": prior_display,
        "health_display_events": display_events,
        "grain_boundaries": grain_boundaries,
        "camera": {
            "distinct": {
                key: [list(value) if isinstance(value, tuple) else value
                      for value in sorted(values, key=str)]
                for key, values in camera_values.items()
            },
            "change_points": camera_changes,
        } if camera_changes else None,
    }


def source_errors(queue: dict, capsules: dict) -> tuple[list[str], list[dict], dict[str, list[str]]]:
    errors = []
    if CONFIGURATION.get("schema") != "abl-phase4-offline-collectibles-batch-source/1":
        errors.append("offline collectibles batch source schema is invalid")
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
    if [SELECTION_ROWS[row_id]["queue_rank"] for row_id in SELECTED_ROWS] != [1, 2, 3, 4]:
        errors.append("selection snapshot does not retain ranks 1 through 4")
    return errors, selected, movie_to_rows


def grain_events(summary: dict) -> list[dict]:
    return [event for event in summary["player_typed_events"] if "grain" in event["fields"]]


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

    old_outcomes = frame_index.OUTCOME_FIELDS
    frame_index.OUTCOME_FIELDS = frozenset(CONFIGURATION["tracked_player_outcome_fields"])
    detailed_rows, summaries, targeted = [], [], {}
    try:
        for capsule in selected_capsules:
            detail, summary = frame_index.scan_capsule(reader, capsule)
            rows = sorted(movie_to_rows[capsule["movie"]])
            detail["queue_rows"] = rows
            summary["queue_rows"] = rows
            detailed_rows.append(detail)
            summaries.append(summary)
            targeted[capsule["movie"]] = targeted_scan(
                reader, capsule,
                {event["movie_frame"] for event in grain_events(summary)},
                "C14_telescope" in rows)
    finally:
        frame_index.OUTCOME_FIELDS = old_outcomes

    summary_by_movie = {row["movie"]: row for row in summaries}
    row_movies = {
        row_id: sorted(
            capsule["movie"] for capsule in selected_capsules
            if row_id in movie_to_rows[capsule["movie"]])
        for row_id in SELECTED_ROWS
    }
    row_events = {
        row_id: [
            {"movie": movie, **event}
            for movie in row_movies[row_id]
            for event in grain_events(summary_by_movie[movie])]
        for row_id in SELECTED_ROWS
    }
    c14_movie = row_movies["C14_telescope"][0]
    c14_camera = targeted[c14_movie]["camera"]
    camera_position_frames = [
        row["movie_frame"] for row in c14_camera["change_points"]
        if row["movie_frame"] and "position" in row.get("changes", {})]
    camera_target_frames = [
        row["movie_frame"] for row in c14_camera["change_points"]
        if row["movie_frame"] and "target" in row.get("changes", {})]
    target_transition = next(
        row["changes"]["target"] for row in c14_camera["change_points"]
        if row["movie_frame"] == 65 and "target" in row.get("changes", {}))
    position_transitions = [
        row for row in c14_camera["change_points"]
        if row["movie_frame"] and "position" in row.get("changes", {})]

    queue_rows = {row["row_id"]: row for row in queue["rows"]}
    exact_queries = {
        row_id: queue_rows[row_id]["offline_batch_queries"]
        for row_id in SELECTED_ROWS
    }
    external_document = {
        "_comment": "External game-derived per-frame index. Preserve outside Git; never commit.",
        "schema": CONFIGURATION["external_index"]["schema"],
        "generated": stable_generated(external_output),
        "selected_rows": list(SELECTED_ROWS),
        "reader": reader_info,
        "selection_snapshot": CONFIGURATION["selection_snapshot"],
        "capsule_index_sha256": common.sha256(CAPSULE_PATH),
        "capsules": detailed_rows,
        "targeted_evidence": targeted,
    }
    external_bytes = render(external_document)
    external_hash = hashlib.sha256(external_bytes).hexdigest()
    source_dependencies = {
        "analysis/phase4_trace_capsule_set.json": common.sha256(CAPSULE_PATH),
        "config/record_types.yaml": common.sha256(common.ROOT / "config/record_types.yaml"),
        "config/semantic_state.yaml": common.sha256(SEMANTIC_CONFIG_PATH),
        "config/phase4_camera_controls.yaml": common.sha256(CAMERA_CONFIG_PATH),
        "config/phase4_offline_collectibles_batch.yaml": common.sha256(CONFIG_PATH),
        "tools/phase4_offline_contact_batch.py": common.sha256(CONTACT_TOOL_PATH),
        "tools/phase4_offline_collectibles_batch.py": common.sha256(Path(__file__)),
    }

    def event_boundaries(row_id: str) -> list[dict]:
        rows = []
        for event in row_events[row_id]:
            boundary = next(
                item for item in targeted[event["movie"]]["grain_boundaries"]
                if item["movie_frame"] == event["movie_frame"])
            rows.append(event | boundary)
        return rows

    c01 = event_boundaries("C01_grain_pickup")
    c02 = event_boundaries("C02_fifty_grain_reward")
    c13 = event_boundaries("C13_grain_harvester")
    c01_movie = row_movies["C01_grain_pickup"][0]
    c02_movie = row_movies["C02_fifty_grain_reward"][0]
    c13_movie = row_movies["C13_grain_harvester"][0]
    derived_findings = {
        "C01_grain_pickup": {
            "grain_initial": summary_by_movie[c01_movie]["first_player"]["grain"],
            "grain_final": summary_by_movie[c01_movie]["last_player"]["grain"],
            "grain_event_frames": [row["movie_frame"] for row in c01],
            "grain_events": c01,
            "bounded_observation": "Two +1 grain boundaries each coincide with five action-4 radius-100 contact-record resets and changes in every retained frame domain.",
        },
        "C02_fifty_grain_reward": {
            "grain_initial": summary_by_movie[c02_movie]["first_player"]["grain"],
            "grain_final": summary_by_movie[c02_movie]["last_player"]["grain"],
            "grain_event_frames": [row["movie_frame"] for row in c02],
            "grain_events": c02,
            "health_initial": summary_by_movie[c02_movie]["first_player"]["health"],
            "health_final": summary_by_movie[c02_movie]["last_player"]["health"],
            "health_display_initial": targeted[c02_movie]["health_display_first"],
            "health_display_final": targeted[c02_movie]["health_display_last"],
            "health_display_event_count": len(targeted[c02_movie]["health_display_events"]),
            "health_display_values": sorted({
                value for event in targeted[c02_movie]["health_display_events"]
                for value in (event["before"], event["after"])}),
            "health_display_at_grain_boundary": next(
                event for event in targeted[c02_movie]["health_display_events"]
                if event["movie_frame"] == 160),
            "bounded_observation": "The 49-to-50 boundary leaves true health unchanged and has no same-frame SPU-RAM change; it coincides with five action-4 radius-100 contact-record resets. The display field is already cycling and its same-frame step cannot establish a heal.",
        },
        "C13_grain_harvester": {
            "grain_initial": summary_by_movie[c13_movie]["first_player"]["grain"],
            "grain_final": summary_by_movie[c13_movie]["last_player"]["grain"],
            "grain_event_frames": [row["movie_frame"] for row in c13],
            "grain_events": c13,
            "action20_transition_count": sum(
                len(row["action20_collection_transitions"]) for row in c13),
            "bounded_observation": "Nine +1 grain boundaries each coincide with one action-20 contact transition from state 22/gate >1 to state 16/gate 1 and changes in every retained frame domain.",
        },
        "C14_telescope": {
            "player_outcome_events": row_events["C14_telescope"],
            "manual_mode_values": c14_camera["distinct"]["mode"],
            "stable_control_values": {
                key: c14_camera["distinct"][key]
                for key in ("distance", "orbit_yaw", "profile_suppression", "pitch_scale",
                            "vertical_angle", "orbit_bias", "vertical_target", "object_pointer")
            },
            "target_change_frames": camera_target_frames,
            "position_change_frames": camera_position_frames,
            "target_transition": target_transition,
            "position_transition_first": position_transitions[0],
            "position_transition_last": position_transitions[-1],
            "bounded_observation": "The derived target changes at frame 65 and position smooths through frame 147 while manual mode and retained camera-control inputs stay constant.",
        },
    }
    summary_document = {
        "_comment": "Non-copyrighted preservation manifest and bounded findings for four Phase-4 offline rows; frame boundaries are not exact writer evidence.",
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
                "python3 tools/phase4_offline_collectibles_batch.py --external-output "
                + str(external_output) + " --write"),
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
        "capsule_summaries": summaries,
        "derived_findings": derived_findings,
        "bounded_conclusions": [
            "All four relevant capsules reconstruct under the exact pinned reader without a record-count or domain-hash error.",
            "C01 and C02 retain a repeated five-record action-4 effect signature at grain boundaries; this does not identify the pickup/reward owner or exact writer.",
            "C13 retains nine one-for-one action-20 state transitions and grain increments; the movie filename remains a lead, not harvester ownership proof.",
            "C14 retains a derived camera transition with stable manual/control fields; this does not identify telescope ownership or a camera producer.",
            "Frame-boundary correlation does not attribute an exact CPU writer, actor/fixture owner, DMA/GPU/SPU producer or causal control.",
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
        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/collectibles-v1/index.json")
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
            print("external Phase-4 collectibles index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 collectibles summary is missing or stale", file=sys.stderr)
            return 1
    else:
        print(summary_bytes.decode(), end="")
    print(
        f"PASS: rows={len(SELECTED_ROWS)} capsules={summary['offline_batch']['capsule_count']} "
        f"records={summary['offline_batch']['reconstructed_records']} "
        f"external_sha256={summary['external_index']['sha256']}",
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
