#!/usr/bin/env python3
"""Build the external cross-movie index for the first offline-ready contact batch."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
from types import ModuleType

import phase4_common as common


QUEUE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
OUTPUT = common.ROOT / "analysis/phase4_offline_contact_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_contact_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
OUTCOME_FIELDS = frozenset(CONFIGURATION["tracked_player_outcome_fields"])
SELECTION_ROWS = {
    row["row_id"]: row for row in CONFIGURATION["selection_snapshot"]["rows"]
}
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


def load_reader(path: Path, expected_sha256: str) -> ModuleType:
    if not path.is_file() or common.sha256(path) != expected_sha256:
        raise ValueError(f"offline reader is absent or hash-mismatched: {path}")
    spec = importlib.util.spec_from_file_location("phase4_pinned_capsule_reader", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load pinned offline reader: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def player(image: bytearray) -> dict:
    base = PLAYER_BASE
    return {
        "x": s32(image, base + 0x00),
        "y": s32(image, base + 0x04),
        "z": s32(image, base + 0x08),
        "heading": u32(image, base + 0x20),
        "velocity_x": s32(image, base + 0x2C),
        "velocity_y": s32(image, base + 0x30),
        "velocity_z": s32(image, base + 0x34),
        "safe_x": s32(image, base + 0x50),
        "safe_y": s32(image, base + 0x54),
        "safe_z": s32(image, base + 0x58),
        "state": u16(image, base + 0x80),
        "grounded": u16(image, base + 0x82),
        "vertical_aux": s16(image, base + 0x84),
        "animation": s16(image, base + 0x88),
        "powerup_flags": u32(image, base + 0x90),
        "health": s16(image, base + 0x94),
        "lives": u8(image, base + 0xA0),
        "grain": u8(image, base + 0xA1),
    }


def actor_records(image: bytearray) -> list[dict]:
    rows = []
    for slot in range(ACTOR_COUNT):
        base = ACTOR_BASE + slot * ACTOR_STRIDE
        actor_id = u32(image, base)
        if not actor_id:
            continue
        rows.append({
            "slot": slot,
            "address": f"0x{0x80000000 + base:08x}",
            "id": actor_id,
            "x": s32(image, base + 0x04),
            "y": s32(image, base + 0x08),
            "z": s32(image, base + 0x0C),
            "velocity_x": s32(image, base + 0x1C),
            "velocity_z": s32(image, base + 0x24),
            "ai_flags": u16(image, base + 0x5C),
            "vm_wait": s16(image, base + 0x60),
            "knockback": s16(image, base + 0x6C),
            "hp": s16(image, base + 0x6E),
            "vm_ip": f"0x{u32(image, base + 0x70):08x}",
            "callback": f"0x{u32(image, base + 0x7C):08x}",
            "source": f"0x{u32(image, base + 0x80):08x}",
        })
    return rows


def contact_records(image: bytearray) -> list[dict]:
    rows = []
    for slot in range(CONTACT_COUNT):
        base = CONTACT_BASE + slot * CONTACT_STRIDE
        ttl = u16(image, base + 0x22)
        flags = u8(image, base + 0x33)
        if ttl <= 0 or not flags & 0x02:
            continue
        rows.append({
            "slot": slot,
            "address": f"0x{0x80000000 + base:08x}",
            "x": s32(image, base + 0x00),
            "y": s32(image, base + 0x04),
            "z": s32(image, base + 0x08),
            "action": u16(image, base + 0x20),
            "active_gate": ttl,
            "kind": u8(image, base + 0x27),
            "radius_add": s16(image, base + 0x28),
            "state": s16(image, base + 0x2C),
            "flags": flags,
        })
    return rows


def intersects(runs: list[tuple[int, bytes]], offset: int, length: int) -> bool:
    end = offset + length
    return any(start < end and start + len(data) > offset for start, data in runs)


def changed_fields(before: dict, after: dict) -> dict:
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)
    }


def typed_actor_changes(before: list[dict], after: list[dict]) -> list[dict]:
    left = {row["slot"]: row for row in before}
    right = {row["slot"]: row for row in after}
    changes = []
    retained = ("id", "hp", "knockback", "ai_flags", "vm_wait", "vm_ip", "callback", "source")
    for slot in sorted(set(left) | set(right)):
        old = left.get(slot) or {}
        new = right.get(slot) or {}
        fields = changed_fields(
            {key: old.get(key) for key in retained},
            {key: new.get(key) for key in retained},
        )
        if fields:
            changes.append({"slot": slot, "fields": fields})
    return changes


def typed_contact_changes(before: list[dict], after: list[dict]) -> list[dict]:
    left = {row["slot"]: row for row in before}
    right = {row["slot"]: row for row in after}
    changes = []
    retained = ("action", "active_gate", "kind", "radius_add", "state", "flags")
    for slot in sorted(set(left) | set(right)):
        old = left.get(slot) or {}
        new = right.get(slot) or {}
        fields = changed_fields(
            {key: old.get(key) for key in retained},
            {key: new.get(key) for key in retained},
        )
        if fields:
            changes.append({"slot": slot, "fields": fields})
    return changes


def frame_register_sha(registers: dict[str, int]) -> str:
    data = json.dumps(registers, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def scan_capsule(reader: ModuleType, capsule_row: dict) -> tuple[dict, dict]:
    directory = Path(capsule_row["capsule_directory"])
    manifest_path = directory / "manifest.json"
    if common.sha256(manifest_path) != capsule_row["capsule_manifest_sha256"]:
        raise ValueError(f"capsule manifest pin mismatch: {manifest_path}")
    capsule = reader.Capsule(directory)
    external_frames = []
    hotspots: Counter[int] = Counter()
    domain_change_frames: Counter[str] = Counter()
    domain_changed_bytes: Counter[str] = Counter()
    player_events = []
    actor_events = []
    contact_events = []
    actor_ids: set[int] = set()
    actor_slots: set[int] = set()
    contact_actions: set[int] = set()
    previous_player = previous_actors = previous_contacts = None
    first_player = last_player = None
    first_register = last_register = None
    records = 0
    for item in capsule.frames():
        records += 1
        ram = item.state["ram"]
        current_player = player(ram)
        actors = actor_records(ram)
        contacts = contact_records(ram)
        actor_ids.update(row["id"] for row in actors)
        actor_slots.update(row["slot"] for row in actors)
        contact_actions.update(row["action"] for row in contacts)
        frame_hotspots = Counter()
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
                domain_change_frames[domain] += 1
                domain_changed_bytes[domain] += changed[domain]["bytes"]
        correlations = {
            "player_block_changed": intersects(item.changes["ram"], PLAYER_BASE, PLAYER_SIZE),
            "actor_pool_changed": intersects(item.changes["ram"], ACTOR_BASE, ACTOR_STRIDE * ACTOR_COUNT),
            "contact_pool_changed": intersects(item.changes["ram"], CONTACT_BASE, CONTACT_STRIDE * CONTACT_COUNT),
            "vram_changed": bool(item.changes["vram"]),
            "spu_ram_changed": bool(item.changes["spu"]),
        }
        register_sha = frame_register_sha(item.registers)
        first_player = first_player or current_player
        last_player = current_player
        first_register = first_register or register_sha
        last_register = register_sha
        if previous_player is not None:
            fields = changed_fields(previous_player, current_player)
            # Keep the tracked summary focused on falsifiable outcome changes.  The
            # full external index retains every decoded player field per frame.
            decisive = {
                key: value for key, value in fields.items()
                if key in OUTCOME_FIELDS
            }
            if decisive:
                player_events.append({
                    "movie_frame": item.movie_frame,
                    "emulator_frame": item.frame,
                    "cycle": item.cycle,
                    "pc": f"0x{item.pc:08x}",
                    "fields": decisive,
                    "correlations": correlations,
                    "top_frame_blocks": [
                        {"pc": f"0x{pc:08x}", "count": count}
                        for pc, count in frame_hotspots.most_common(8)],
                })
            actor_delta = typed_actor_changes(previous_actors, actors)
            if actor_delta:
                actor_events.append({
                    "movie_frame": item.movie_frame,
                    "emulator_frame": item.frame,
                    "changes": actor_delta,
                    "player_health": current_player["health"],
                    "player_lives": current_player["lives"],
                })
            contact_delta = typed_contact_changes(previous_contacts, contacts)
            if contact_delta:
                contact_events.append({
                    "movie_frame": item.movie_frame,
                    "emulator_frame": item.frame,
                    "changes": contact_delta,
                    "player_health": current_player["health"],
                    "player_lives": current_player["lives"],
                })
        external_frames.append({
            "movie_frame": item.movie_frame,
            "emulator_frame": item.frame,
            "cycle": item.cycle,
            "pc": f"0x{item.pc:08x}",
            "register_sha256": register_sha,
            "domain_sha256": item.hashes,
            "changed": changed,
            "range_correlations": correlations,
            "player": current_player,
            "actors": actors,
            "contacts": contacts,
            "top_frame_blocks": [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in frame_hotspots.most_common(12)],
        })
        previous_player, previous_actors, previous_contacts = current_player, actors, contacts
    expected_records = int(capsule_row["frames"]) + 1
    if records != expected_records:
        raise ValueError(
            f"{capsule_row['movie']}: reconstructed {records} records, expected {expected_records}")
    summary = {
        "movie": capsule_row["movie"],
        "movie_sha256": capsule_row["movie_sha256"],
        "capsule_manifest_sha256": capsule_row["capsule_manifest_sha256"],
        "capsule_tree_sha256": capsule_row["capsule_tree_sha256"],
        "records": records,
        "movie_frames": capsule_row["frames"],
        "first_player": first_player,
        "last_player": last_player,
        "first_register_sha256": first_register,
        "last_register_sha256": last_register,
        "domain_change_frames": dict(domain_change_frames),
        "domain_changed_bytes_sum": dict(domain_changed_bytes),
        "actor_ids_observed": sorted(actor_ids),
        "actor_slots_observed": sorted(actor_slots),
        "contact_actions_observed": sorted(contact_actions),
        "player_typed_events": player_events,
        "actor_typed_event_count": len(actor_events),
        "contact_typed_event_count": len(contact_events),
        "actor_hp_event_count": sum(
            "hp" in change["fields"]
            for event in actor_events for change in event["changes"]),
        "top_hotspots": [
            {"pc": f"0x{pc:08x}", "count": count}
            for pc, count in hotspots.most_common(40)],
    }
    external = {
        "movie": capsule_row["movie"],
        "summary": summary,
        "frames": external_frames,
        "actor_typed_events": actor_events,
        "contact_typed_events": contact_events,
    }
    return external, summary


def build(external_output: Path) -> tuple[dict, dict]:
    queue = common.load_json(QUEUE_PATH)
    capsules = common.load_json(CAPSULE_PATH)
    errors: list[str] = []
    if CONFIGURATION.get("schema") != "abl-phase4-offline-contact-batch-source/1":
        errors.append("offline contact batch source schema is invalid")
    if not queue.get("valid") or queue.get("errors"):
        errors.append("offline opportunity queue is invalid")
    queue_rows = {row["row_id"]: row for row in queue.get("rows") or []}
    observed_ranks = []
    for row_id in SELECTED_ROWS:
        row = queue_rows.get(row_id)
        if not row:
            errors.append(f"selected row absent from queue: {row_id}")
            continue
        prior = {
            item.get("artifact") for item in row.get("prior_offline_analysis") or []
        }
        eligible_current = (
            row.get("current_completion_state") == "open"
            and (
                row.get("classification") == "offline_ready"
                or (
                    row.get("classification") == "offline_partial"
                    and "analysis/phase4_offline_contact_batch.json" in prior
                )
            )
        )
        if not eligible_current:
            errors.append(f"selected row is not current open batch evidence: {row_id}")
        observed_ranks.append(SELECTION_ROWS.get(row_id, {}).get("queue_rank"))
    if observed_ranks != list(range(1, len(SELECTED_ROWS) + 1)):
        errors.append(f"selected rows are not the current top five: {observed_ranks}")
    capsule_by_movie = {row["movie"]: row for row in capsules.get("capsules") or []}
    movie_to_rows: dict[str, list[str]] = {}
    for row_id in SELECTED_ROWS:
        for capsule in queue_rows.get(row_id, {}).get("relevant_capsules") or []:
            movie_to_rows.setdefault(capsule["movie"], []).append(row_id)
    selected_capsules = [capsule_by_movie[movie] for movie in sorted(movie_to_rows)]
    expected_capsules = int(CONFIGURATION["expected_unique_capsules"])
    if len(selected_capsules) != expected_capsules:
        errors.append(
            f"selected cluster has {len(selected_capsules)} unique capsules, "
            f"expected {expected_capsules}")
    reader_info = capsules.get("offline_reader_snapshot") or {}
    reader_path = Path(reader_info.get("absolute_path") or "")
    try:
        reader = load_reader(reader_path, reader_info.get("sha256") or "")
    except ValueError as exc:
        errors.append(str(exc))
        reader = None
    if errors:
        raise ValueError("; ".join(errors))
    detailed_rows, summaries = [], []
    for capsule in selected_capsules:
        detail, summary = scan_capsule(reader, capsule)
        detail["queue_rows"] = sorted(movie_to_rows[capsule["movie"]])
        detailed_rows.append(detail)
        summaries.append(summary | {"queue_rows": sorted(movie_to_rows[capsule["movie"]])})

    health_events = []
    life_events = []
    actor_hp_events = 0
    actor_ids: set[int] = set()
    for summary in summaries:
        actor_ids.update(summary["actor_ids_observed"])
        actor_hp_events += summary["actor_hp_event_count"]
        for event in summary["player_typed_events"]:
            if "health" in event["fields"]:
                health_events.append({"movie": summary["movie"], **event})
            if "lives" in event["fields"]:
                life_events.append({"movie": summary["movie"], **event})
    correlation_counts = Counter()
    for event in health_events:
        for key, value in event["correlations"].items():
            if value:
                correlation_counts[key] += 1
    external_document = {
        "_comment": "External game-derived cross-movie index. Preserve outside Git; tracked summary contains only bounded non-copyrighted facts and hashes.",
        "schema": CONFIGURATION["external_index"]["schema"],
        "generated": stable_generated(external_output),
        "selected_rows": list(SELECTED_ROWS),
        "reader": reader_info,
        "selection_snapshot": CONFIGURATION["selection_snapshot"],
        "capsule_index_sha256": common.sha256(CAPSULE_PATH),
        "capsules": detailed_rows,
    }
    external_bytes = render(external_document)
    external_hash = hashlib.sha256(external_bytes).hexdigest()
    source_dependencies = {
        "analysis/phase4_trace_capsule_set.json": common.sha256(CAPSULE_PATH),
        "config/record_types.yaml": common.sha256(common.ROOT / "config/record_types.yaml"),
        "config/phase4_offline_contact_batch.yaml": common.sha256(CONFIG_PATH),
        "tools/phase4_offline_contact_batch.py": common.sha256(Path(__file__)),
    }
    summary_document = {
        "_comment": "Non-copyrighted summary and preservation manifest for the selected Phase-4 offline contact/hazard cluster. Frame-boundary correlations are not writer or causality claims.",
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(OUTPUT),
        "source_dependencies": source_dependencies,
        "queue_counts": CONFIGURATION["selection_snapshot"]["queue_counts"],
        "selected_rows": [{
            "row_id": row_id,
            "queue_rank": SELECTION_ROWS[row_id]["queue_rank"],
            "classification": SELECTION_ROWS[row_id]["classification"],
            "completion_state": SELECTION_ROWS[row_id]["completion_state"],
            "capsules": [row["movie"] for row in queue_rows[row_id]["relevant_capsules"]],
        } for row_id in SELECTED_ROWS],
        "offline_batch": {
            "reader_path": str(reader_path),
            "reader_sha256": reader_info["sha256"],
            "generator_command": (
                "python3 tools/phase4_offline_contact_batch.py --external-output "
                + str(external_output) + " --write"),
            "capsule_count": len(selected_capsules),
            "reconstructed_records": sum(row["records"] for row in summaries),
            "domains": ["registers", "ram", "vram", "spu_ram", "block_flow"],
            "queries": [
                "Pinned Capsule reader full reconstruction for every frame record.",
                "Typed player-block, 64-slot actor-pool and 64-slot contact-pool deltas.",
                "RAM/VRAM/SPU-RAM change-run counts and hashes per frame.",
                "Full-window and per-event block-start hotspot counts.",
                "Cross-movie health/lives change correlations with actor/contact/VRAM/SPU domains.",
            ],
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
        "derived_findings": {
            "movie_count": len(summaries),
            "health_change_events": len(health_events),
            "life_change_events": len(life_events),
            "actor_hp_change_events": actor_hp_events,
            "actor_ids_observed": sorted(actor_ids),
            "health_event_domain_correlations": dict(correlation_counts),
            "health_events": health_events,
            "life_events": life_events,
        },
        "bounded_conclusions": [
            "All 13 selected capsules reconstruct without a domain-hash error under the exact pinned reader.",
            "Typed frame-boundary health/lives, actor-pool, contact-pool, VRAM, SPU-RAM and block-flow correlations are retained for the five selected rows.",
            "Actor identities remain numeric fixed-pool IDs; filenames do not establish species or hazard ownership.",
            "Same-frame correlation does not attribute an exact writer, DMA/GPU/SPU producer, attack source, or causal control.",
        ],
        "named_unknowns": {
            "E10_hazards": "Hazard kind/producer ownership, exact damage writers, per-stage census, denial controls and lifecycle breadth remain open.",
            "D08_flies": "The capsule bounds numeric actor/contact state only; fly species ownership, AI/attacks/drops/variants remain open.",
            "D09_cockroaches": "The capsule bounds numeric actor/contact state only; taxi/ramming/obstacle roles, immunity and traffic interactions remain open.",
            "D11_mites_grubs": "The two capsules remain distinct numeric leads; mite-versus-grub actor ownership, spawn/AI/damage/death breadth remain open.",
            "D15_daddy_long_legs": "The capsule bounds numeric actor/contact state only; web projectile, range, motion and collision ownership remain open.",
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
        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/contact-hazard-v1/index.json")
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
            print("external Phase-4 contact index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 contact summary is missing or stale", file=sys.stderr)
            return 1
    else:
        print(summary_bytes.decode(), end="")
    print(
        f"PASS: rows={len(SELECTED_ROWS)} capsules={summary['offline_batch']['capsule_count']} "
        f"records={summary['offline_batch']['reconstructed_records']} "
        f"external_sha256={summary['external_index']['sha256']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
