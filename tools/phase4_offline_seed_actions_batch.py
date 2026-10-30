#!/usr/bin/env python3
"""Build the external cross-movie index for handstand and seed-as-weapon."""

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
import phase4_offline_seed_lifecycle_batch as seed_index


QUEUE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
OUTPUT = common.ROOT / "analysis/phase4_offline_seed_actions_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_seed_actions_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELECTION_ROWS = {
    row["row_id"]: row for row in CONFIGURATION["selection_snapshot"]["rows"]
}
SELF_ARTIFACT = "analysis/phase4_offline_seed_actions_batch.json"
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()

PLAYER_BASE = 0x0A6500
PLAYER_SIZE = 0xB0
ACTOR_BASE = 0x09FD80
ACTOR_STRIDE = 0x84
ACTOR_COUNT = 64
CONTACT_BASE = 0x0B0D18
CONTACT_STRIDE = 0x38
CONTACT_COUNT = 64
ENEMY_TABLE = 0x090748
ENEMY_TABLE_COUNT = 64
PLANT_BASE = 0x090BF0
PLANT_STRIDE = 0x30
PLANT_COUNT = 20
SEED_ID = 11
A11_SEED_SLOT = 20
A11_TARGET_SLOT = 0


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


def u16(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<H", image, offset)[0]


def u32(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<I", image, offset)[0]


def plant_slots(image: bytearray) -> list[dict]:
    return [{
        "slot": slot,
        "type": u16(image, PLANT_BASE + slot * PLANT_STRIDE),
        "seed_backlink": f"0x{u32(image, PLANT_BASE + slot * PLANT_STRIDE + 0x20):08x}",
        "lifecycle_phase_raw": frame_index.u8(
            image, PLANT_BASE + slot * PLANT_STRIDE + 0x2E),
    } for slot in range(PLANT_COUNT)]


def live_actor_table(image: bytearray) -> list[str]:
    return [f"0x{value:08x}" for index in range(ENEMY_TABLE_COUNT)
            if (value := u32(image, ENEMY_TABLE + index * 4))]


def function_counts(flow: list[tuple[int, int, int]], row_id: str) -> dict[str, dict]:
    result = {}
    for candidate in CONFIGURATION["candidate_functions"][row_id]:
        start, end = int(candidate["start"]), int(candidate["end"])
        blocks = [(pc, count) for pc, count, _ in flow if start <= pc < end]
        result[candidate["name"]] = {
            "hits": sum(count for _, count in blocks),
            "distinct_block_starts": len(blocks),
            "candidate_instruction_block_start_covered": any(
                pc == int(candidate.get("arm_block_start",
                                        candidate.get("writer_block_start",
                                                      candidate.get("writer_pc"))))
                for pc, _ in blocks),
            "covered_block_starts": [f"0x{pc:08x}" for pc, _ in blocks],
        }
    return result


def changed_fields(before: dict, after: dict) -> dict:
    return {key: {"before": before.get(key), "after": after.get(key)}
            for key in sorted(set(before) | set(after))
            if before.get(key) != after.get(key)}


def input_edges(movie_pin: dict) -> dict[str, list[int]]:
    return seed_index.input_edges(movie_pin)


def movie_pin(queue_rows: dict[str, dict], logical_path: str) -> dict:
    pins = [item for row_id in SELECTED_ROWS
            for item in queue_rows[row_id].get("relevant_movies") or []
            if item["path"] == logical_path]
    identities = {(item["sha256"], item["bytes"], item["declared_start_state"])
                  for item in pins}
    if len(identities) != 1:
        raise ValueError(f"selected rows do not identify one current movie pin: {logical_path}")
    return pins[0]


def scan_capsule(reader, capsule_row: dict, pin: dict, row_id: str) -> tuple[dict, dict]:
    directory = Path(capsule_row["capsule_directory"])
    manifest_path = directory / "manifest.json"
    if common.sha256(manifest_path) != capsule_row["capsule_manifest_sha256"]:
        raise ValueError(f"capsule manifest pin mismatch: {manifest_path}")
    if capsule_row["movie_sha256"] != pin["sha256"]:
        raise ValueError(f"capsule/movie pin mismatch: {capsule_row['movie']}")
    if capsule_row["start_state"]["path"] != pin["declared_start_state"]:
        raise ValueError(f"capsule/start-state pin mismatch: {capsule_row['movie']}")
    edges = input_edges(pin)
    capsule = reader.Capsule(directory)
    frames = []
    hotspots: Counter[int] = Counter()
    domain_frames: Counter[str] = Counter()
    domain_bytes: Counter[str] = Counter()
    player_events = []
    actor_events = []
    contact_events = []
    prior_player = prior_actors = prior_contacts = None
    first_register = last_register = None
    for record_index, item in enumerate(capsule.frames()):
        ram = item.state["ram"]
        player = frame_index.player(ram)
        actors = frame_index.actor_records(ram)
        contacts = frame_index.contact_records(ram)
        plants = plant_slots(ram)
        live = live_actor_table(ram)
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
        register_sha = frame_index.frame_register_sha(item.registers)
        first_register = first_register or register_sha
        last_register = register_sha
        correlations = {
            "player_block_changed": frame_index.intersects(
                item.changes["ram"], PLAYER_BASE, PLAYER_SIZE),
            "actor_pool_changed": frame_index.intersects(
                item.changes["ram"], ACTOR_BASE, ACTOR_STRIDE * ACTOR_COUNT),
            "contact_pool_changed": frame_index.intersects(
                item.changes["ram"], CONTACT_BASE, CONTACT_STRIDE * CONTACT_COUNT),
            "enemy_live_table_changed": frame_index.intersects(
                item.changes["ram"], ENEMY_TABLE, ENEMY_TABLE_COUNT * 4),
            "plant_pool_changed": frame_index.intersects(
                item.changes["ram"], PLANT_BASE, PLANT_STRIDE * PLANT_COUNT),
            "vram_changed": bool(item.changes["vram"]),
            "spu_ram_changed": bool(item.changes["spu"]),
        }
        frame_ref = {
            "record_index": record_index,
            "movie_frame": item.movie_frame,
            "emulator_frame": item.frame,
            "cycle": item.cycle,
            "pc": f"0x{item.pc:08x}",
        }
        if prior_player is not None:
            fields = changed_fields(prior_player, player)
            decisive = {key: value for key, value in fields.items()
                        if key in {"x", "y", "z", "state", "grounded", "animation"}}
            if decisive:
                player_events.append({**frame_ref, "fields": decisive,
                                      "correlations": correlations})
            actor_delta = frame_index.typed_actor_changes(prior_actors, actors)
            if actor_delta:
                actor_events.append({**frame_ref, "changes": actor_delta})
            contact_delta = frame_index.typed_contact_changes(prior_contacts, contacts)
            if contact_delta:
                contact_events.append({**frame_ref, "changes": contact_delta})
        frames.append({
            **frame_ref,
            "register_sha256": register_sha,
            "domain_sha256": item.hashes,
            "changed": changed,
            "range_correlations": correlations,
            "player": player,
            "actors": actors,
            "contacts": contacts,
            "active_plants": [plant for plant in plants if plant["type"]],
            "live_actor_table": live,
            "candidate_function_flow": function_counts(item.flow, row_id),
            "top_frame_blocks": [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in frame_hotspots.most_common(12)],
        })
        prior_player, prior_actors, prior_contacts = player, actors, contacts
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
        "input_edges": edges,
        "domain_change_frames": dict(domain_frames),
        "domain_changed_bytes_sum": dict(domain_bytes),
        "first_register_sha256": first_register,
        "last_register_sha256": last_register,
        "player_typed_event_count": len(player_events),
        "actor_typed_event_count": len(actor_events),
        "contact_typed_event_count": len(contact_events),
        "top_hotspots": [{"pc": f"0x{pc:08x}", "count": count}
                         for pc, count in hotspots.most_common(40)],
    }
    detail = {"movie": capsule_row["movie"], "summary": summary,
              "frames": frames, "player_events": player_events,
              "actor_events": actor_events, "contact_events": contact_events}
    return detail, summary


def actor(frame: dict, slot: int) -> dict | None:
    return next((row for row in frame["actors"] if row["slot"] == slot), None)


def exact_position_runs(frames: list[dict]) -> list[dict]:
    runs = []
    current = None
    for frame in frames:
        key = (frame["player"]["x"], frame["player"]["y"],
               frame["player"]["z"], frame["player"]["grounded"])
        if current is None or key != current["key"]:
            if current is not None:
                runs.append(current)
            current = {"key": key, "start_movie_frame": frame["movie_frame"],
                       "end_movie_frame": frame["movie_frame"], "records": 1}
        else:
            current["end_movie_frame"] = frame["movie_frame"]
            current["records"] += 1
    if current is not None:
        runs.append(current)
    return runs


def event_flow(frame: dict) -> dict:
    return {name: value for name, value in frame["candidate_function_flow"].items()
            if value["hits"]}


def derive_a10(detail: dict, summary: dict) -> dict:
    frames = detail["frames"]
    zero_grounded = [run for run in exact_position_runs(frames) if run["key"][3] == 0]
    frozen = max(zero_grounded, key=lambda row: row["records"])
    frozen = {key: value for key, value in frozen.items() if key != "key"} | {
        "position": list(max(zero_grounded, key=lambda row: row["records"])["key"][:3]),
        "grounded": 0,
    }
    state_events = []
    prior = frames[0]["player"]
    for frame in frames[1:]:
        player = frame["player"]
        fields = {key: {"before": prior[key], "after": player[key]}
                  for key in ("state", "grounded") if prior[key] != player[key]}
        if fields:
            state_events.append({"movie_frame": frame["movie_frame"],
                                 "fields": fields,
                                 "candidate_function_flow": event_flow(frame),
                                 "range_correlations": frame["range_correlations"]})
        prior = player
    dismount = next((row for row in state_events
                     if row["fields"].get("state", {}).get("after") == 6), None)
    frozen_frames = [frame for frame in frames
                     if frozen["start_movie_frame"] <= frame["movie_frame"]
                     <= frozen["end_movie_frame"]]
    seed_slots = sorted({row["slot"] for frame in frozen_frames
                         for row in frame["actors"] if row["id"] == SEED_ID})
    active_plant_types = sorted({row["type"] for frame in frozen_frames
                                 for row in frame["active_plants"]})
    attached_seed_slots = sorted({row["slot"] for frame in frozen_frames
                                  for row in frame["actors"] if row["id"] == SEED_ID
                                  and row["x"] == frame["player"]["x"]
                                  and row["z"] == frame["player"]["z"]})
    seed_distance_minima = {}
    for slot in seed_slots:
        distances = [sum((seed[key] - frame["player"][key]) ** 2
                         for key in ("x", "y", "z"))
                     for frame in frozen_frames
                     if (seed := actor(frame, slot)) is not None]
        seed_distance_minima[str(slot)] = min(distances)
    handstand_events = [row for row in state_events if row["movie_frame"] >= 1030]
    return {
        "movie": summary["movie"],
        "square_press_frames": summary["input_edges"]["square_press"],
        "longest_exact_frozen_zero_grounded_run": frozen,
        "handstand_state_or_grounded_events": handstand_events,
        "dismount_state_6_event": dismount,
        "seed_actor_slots_during_frozen_run": seed_slots,
        "seed_actor_slots_exactly_xz_attached_during_frozen_run": attached_seed_slots,
        "seed_actor_minimum_player_distance_squared": seed_distance_minima,
        "active_plant_types_during_frozen_run": active_plant_types,
        "bounded_observation": (
            "The exact pinned movie supplies frame-boundary state, grounded, position, "
            "input and passive block-flow correlations for the full handstand interval. "
            "The actor/plant census bounds but does not identify the mounted object's "
            "collision primitive or an exact state writer."),
    }


def derive_a11(detail: dict, summary: dict) -> dict:
    frames = detail["frames"]
    target_address = f"0x{0x80000000 + ACTOR_BASE + A11_TARGET_SLOT * ACTOR_STRIDE:08x}"
    series = []
    for frame in frames:
        seed = actor(frame, A11_SEED_SLOT)
        target = actor(frame, A11_TARGET_SLOT)
        if not seed or not target:
            continue
        carry = (seed["x"] == frame["player"]["x"]
                 and seed["z"] == frame["player"]["z"]
                 and frame["player"]["y"] - seed["y"] == 19200)
        distance_squared = sum((seed[key] - target[key]) ** 2 for key in ("x", "y", "z"))
        series.append({"movie_frame": frame["movie_frame"], "carry": carry,
                       "seed_position": [seed["x"], seed["y"], seed["z"]],
                       "target_position": [target["x"], target["y"], target["z"]],
                       "target_knockback": target["knockback"],
                       "distance_squared": distance_squared,
                       "target_in_live_table": target_address in frame["live_actor_table"],
                       "candidate_function_flow": event_flow(frame),
                       "range_correlations": frame["range_correlations"]})
    drop_press = 327
    detach = next(row for row in series if row["movie_frame"] >= drop_press and not row["carry"])
    hit = next((row for row in series if row["movie_frame"] >= detach["movie_frame"]
                and row["target_knockback"] == -20), None)
    removal = next((row for row in series if hit and row["movie_frame"] >= hit["movie_frame"]
                    and not row["target_in_live_table"]), None)
    before_hit = [row for row in series if hit and hit["movie_frame"] - 8 <= row["movie_frame"] < hit["movie_frame"]]
    after_hit = [row for row in series if hit and row["movie_frame"] > hit["movie_frame"]]
    landed = bool(hit and before_hit and after_hit and
                  any(sum((a - b) ** 2 for a, b in zip(row["seed_position"], hit["seed_position"]))
                      > 512 ** 2 for row in before_hit) and
                  all(sum((a - b) ** 2 for a, b in zip(row["seed_position"], hit["seed_position"]))
                      <= 64 ** 2 for row in after_hit))
    knockback_series = [{"movie_frame": row["movie_frame"],
                         "value": row["target_knockback"]}
                        for row in series if hit and row["movie_frame"] >= hit["movie_frame"]
                        and row["target_knockback"] < 0]
    hit_flow = hit["candidate_function_flow"] if hit else {}
    arm_discriminator = {
        name: value["candidate_instruction_block_start_covered"]
        for name, value in hit_flow.items()
    }
    return {
        "movie": summary["movie"],
        "square_press_frames": summary["input_edges"]["square_press"],
        "seed_slot": A11_SEED_SLOT,
        "seed_address": f"0x{0x80000000 + ACTOR_BASE + A11_SEED_SLOT * ACTOR_STRIDE:08x}",
        "target_slot": A11_TARGET_SLOT,
        "target_address": target_address,
        "carry_attachment_predicate": "seed x/z equal player x/z; player_y - seed_y equals 19200",
        "detachment": detach,
        "hit": hit,
        "seed_stays_within_64_units_after_hit": landed,
        "knockback_decay": {
            "records": len(knockback_series),
            "first": knockback_series[0] if knockback_series else None,
            "last": knockback_series[-1] if knockback_series else None,
            "distinct_values": sorted({row["value"] for row in knockback_series}),
            "two_frame_hold_per_integer_step": all(
                sum(row["value"] == value for row in knockback_series) == 2
                for value in range(-20, 0)),
        },
        "hit_candidate_arm_block_discriminator": arm_discriminator,
        "live_table_removal": removal,
        "minimum_distance_squared_after_drop": min(
            row["distance_squared"] for row in series if row["movie_frame"] >= drop_press),
        "bounded_observation": (
            "The natural pinned movie reproduces drop, ballistic convergence, the -20 "
            "target knockback state and live-table removal. Hit-frame passive block "
            "coverage can distinguish candidate function families only when their block "
            "starts differ; it is not an exact-instruction write trace or a new control."),
    }


def source_errors(queue: dict, capsules: dict) -> tuple[list[str], list[dict], dict[str, str]]:
    errors = []
    if CONFIGURATION.get("schema") != "abl-phase4-offline-seed-actions-batch-source/1":
        errors.append("offline seed-actions source schema is invalid")
    if not queue.get("valid") or queue.get("errors") or len(queue.get("rows") or []) != 107:
        errors.append("offline queue is invalid or not exactly 107 rows")
    queue_rows = {row["row_id"]: row for row in queue.get("rows") or []}
    movie_rows = {}
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
        capsules_for_row = row.get("relevant_capsules") or []
        if len(capsules_for_row) != 1:
            errors.append(f"selected row does not identify exactly one capsule: {row_id}")
        else:
            movie_rows[capsules_for_row[0]["movie"]] = row_id
    capsule_by_movie = {row["movie"]: row for row in capsules.get("capsules") or []}
    selected = [capsule_by_movie[movie] for movie in sorted(movie_rows)
                if movie in capsule_by_movie]
    if len(selected) != int(CONFIGURATION["expected_unique_capsules"]):
        errors.append(f"selected cluster has {len(selected)} capsules, expected 2")
    return errors, selected, movie_rows


def tracked_summary(summary: dict) -> dict:
    keys = ("movie", "movie_sha256", "movie_bytes", "media_class", "start_state",
            "capsule_manifest_sha256", "capsule_tree_sha256", "control_match",
            "records", "movie_frames", "domain_change_frames",
            "domain_changed_bytes_sum", "first_register_sha256",
            "last_register_sha256", "player_typed_event_count",
            "actor_typed_event_count", "contact_typed_event_count", "top_hotspots")
    return {**{key: summary[key] for key in keys},
            "input_edge_counts": {key: len(value) for key, value in summary["input_edges"].items()}}


def build(external_output: Path) -> tuple[dict, dict]:
    queue = common.load_json(QUEUE_PATH)
    capsules = common.load_json(CAPSULE_PATH)
    errors, selected, movie_rows = source_errors(queue, capsules)
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
        row_id = movie_rows[capsule["movie"]]
        pin = movie_pin(queue_rows, capsule["movie"])
        detail, summary = scan_capsule(reader, capsule, pin, row_id)
        detail["queue_row"] = row_id
        summary["queue_row"] = row_id
        details[row_id], summaries[row_id] = detail, summary
    findings = {
        "A11_seed_as_weapon": derive_a11(
            details["A11_seed_as_weapon"], summaries["A11_seed_as_weapon"]),
        "A10_handstand": derive_a10(
            details["A10_handstand"], summaries["A10_handstand"]),
    }
    external_document = {
        "_comment": "External game-derived per-frame index; preserve outside Git.",
        "schema": CONFIGURATION["external_index"]["schema"],
        "generated": stable_generated(external_output),
        "selected_rows": list(SELECTED_ROWS),
        "reader": reader_info,
        "capsule_index_sha256": common.sha256(CAPSULE_PATH),
        "capsules": [details[row_id] for row_id in SELECTED_ROWS],
    }
    external_bytes = render(external_document)
    external_hash = hashlib.sha256(external_bytes).hexdigest()
    summary_document = {
        "_comment": "Non-copyrighted summary and preservation manifest for the A10/A11 offline batch.",
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(OUTPUT),
        "source_dependencies": {
            "analysis/phase4_trace_capsule_set.json": common.sha256(CAPSULE_PATH),
            "config/phase4_offline_seed_actions_batch.yaml": common.sha256(CONFIG_PATH),
            "tools/phase4_offline_seed_actions_batch.py": common.sha256(Path(__file__)),
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
                "python3 tools/phase4_offline_seed_actions_batch.py --external-output "
                + str(external_output) + " --write"),
            "capsule_count": len(selected),
            "reconstructed_records": sum(row["records"] for row in summaries.values()),
            "domains": ["registers", "ram", "vram", "spu_ram", "block_flow"],
            "exact_queue_queries": {
                row_id: queue_rows[row_id]["offline_batch_queries"] for row_id in SELECTED_ROWS},
        },
        "external_index": {
            "absolute_path": str(external_output),
            "sha256": external_hash,
            "bytes": len(external_bytes),
            "schema": external_document["schema"],
            "media_class": "external game-derived evidence; never commit",
            "preservation_required": True,
        },
        "capsule_summaries": [tracked_summary(summaries[row_id]) for row_id in SELECTED_ROWS],
        "derived_findings": findings,
        "bounded_conclusions": [
            "Both current capsules reconstruct every retained frame boundary under the exact pinned reader.",
            "A10 handstand state/grounded/position and A11 carry/knockback/live-table changes are correlated with exact input edges and passive block-start flow.",
            "VRAM and SPU-RAM change points are retained, but no GPU submission, SPU voice event or exact CPU writer is attributed.",
            "The pre-existing native positive/negative A11 control remains the causal authority; this natural movie batch adds reusable frame evidence.",
        ],
        "named_unknowns": {
            "A10_handstand": "Mounted object/collision identity and exact dismount writer remain unresolved unless passive block flow excludes all but one candidate family.",
            "A11_seed_as_weapon": "Eligible enemy-family breadth and exact arm instruction remain unresolved unless passive block flow uniquely bounds a candidate function; kind semantics still require controlled mapping.",
        },
        "live_escalation_ids": ["P4-ITER69-A11-MISSING-CAPSULE", "P4-ITER69-A10-MISSING-CAPSULE"],
        "errors": [],
        "valid": True,
    }
    return external_document, summary_document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-output", type=Path,
                        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/seed-actions-v1/index.json")
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
            print("external Phase-4 seed-actions index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 seed-actions summary is missing or stale", file=sys.stderr)
            return 1
    else:
        print(summary_bytes.decode(), end="")
    print(f"PASS: rows=2 capsules={summary['offline_batch']['capsule_count']} "
          f"records={summary['offline_batch']['reconstructed_records']} "
          f"external_sha256={summary['external_index']['sha256']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
