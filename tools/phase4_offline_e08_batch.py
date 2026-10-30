#!/usr/bin/env python3
"""Derive the E08 authored-source frontier from the retained frame index."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys

import phase4_common as common


QUEUE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
CONTACT_PATH = common.ROOT / "analysis/phase4_offline_contact_batch.json"
PROPS_PATH = common.ROOT / "analysis/phase4_props_movers.json"
OUTCOME_PATH = common.ROOT / "analysis/phase4_e08_outcome_join.json"
OPERATOR_PATH = common.ROOT / "analysis/phase4_e08_operator_contacts.json"
HAZARD_PATH = common.ROOT / "analysis/phase4_e08_hazard_outcomes.json"
OUTPUT = common.ROOT / "analysis/phase4_offline_e08_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_e08_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELF_ARTIFACT = "analysis/phase4_offline_e08_batch.json"
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()


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


def normalized_type(value: str) -> str:
    return value.lower()


def significant_change(fields: dict) -> bool:
    policy = CONFIGURATION["significant_actor_change_policy"]
    if set(fields).intersection(policy["direct_fields"]):
        return True
    knockback = fields.get("knockback") or {}
    return knockback.get("before", 0) <= 0 < knockback.get("after", 0)


def source_map(replay: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for identity in replay["initial"]["actor_sources"].values():
        pointer = identity["source_pointer"].lower()
        normalized = {**identity, "source_pointer": pointer,
                      "type_word": normalized_type(identity["type_word"])}
        prior = result.get(pointer)
        if prior is not None and prior != normalized:
            raise ValueError(f"ambiguous authored source pointer: {pointer}")
        result[pointer] = normalized
    return result


def validate_sources(queue: dict, capsules: dict, contact: dict,
                     external_path: Path, external_bytes: bytes) -> tuple[dict, list[dict]]:
    errors = []
    if CONFIGURATION.get("schema") != "abl-phase4-offline-e08-batch-source/1":
        errors.append("offline E08 source schema is invalid")
    if not queue.get("valid") or queue.get("errors") or len(queue.get("rows") or []) != 107:
        errors.append("offline queue is invalid or not exactly 107 rows")
    if contact.get("schema") != "abl-phase4-offline-contact-batch/1" or \
            not contact.get("valid") or contact.get("errors"):
        errors.append("retained contact index summary is invalid")
    expected_external = CONFIGURATION["external_index"]
    if len(external_bytes) != int(expected_external["expected_bytes"]) or \
            hashlib.sha256(external_bytes).hexdigest() != expected_external["expected_sha256"]:
        errors.append("external contact index does not match the E08 preservation pin")
    contact_external = contact.get("external_index") or {}
    if external_path != Path(contact_external.get("absolute_path") or "").resolve() or \
            contact_external.get("sha256") != expected_external["expected_sha256"] or \
            contact_external.get("bytes") != expected_external["expected_bytes"]:
        errors.append("contact summary and E08 external-index declaration disagree")

    rows = {row["row_id"]: row for row in queue.get("rows") or []}
    selection = CONFIGURATION["selection_snapshot"]["rows"][0]
    row = rows.get(selection["row_id"])
    if not row:
        errors.append("selected E08 row is absent")
        row = {}
    prior = {item.get("artifact") for item in row.get("prior_offline_analysis") or []}
    if row.get("current_completion_state") != "open" or \
            row.get("classification") != "offline_partial" or \
            (row.get("priority") or {}).get("rank") != selection["queue_rank"]:
        errors.append("selected E08 row is no longer the current rank-3 open partial")
    if prior and SELF_ARTIFACT not in prior:
        errors.append("selected E08 row gained a different unaccounted offline analysis")
    queries = row.get("offline_batch_queries") or []
    if len(queries) != 156:
        errors.append(f"E08 query set has {len(queries)} entries, expected 156")

    capsule_by_movie = {item["movie"]: item for item in capsules.get("capsules") or []}
    selected_movies = {item["movie"] for item in row.get("relevant_capsules") or []}
    selected = [capsule_by_movie[movie] for movie in sorted(selected_movies)
                if movie in capsule_by_movie]
    if len(selected_movies) != int(CONFIGURATION["expected_unique_capsules"]) or \
            len(selected) != len(selected_movies):
        errors.append("E08 does not resolve to exactly 13 current capsules")
    if errors:
        raise ValueError("; ".join(errors))
    return row, selected


def join_movie(capsule: dict, replay: dict, uncontrolled: set[str]) -> dict:
    identities = source_map(replay)
    frames = capsule["frames"]
    frame_indexes = {frame["movie_frame"]: index for index, frame in enumerate(frames)}
    joined = 0
    changes = 0
    observed: Counter[str] = Counter()
    significant: list[dict] = []
    significant_by_frame: dict[int, list[dict]] = defaultdict(list)
    all_significant_by_frame: dict[int, list[dict]] = defaultdict(list)

    for event in capsule["actor_typed_events"]:
        index = frame_indexes[event["movie_frame"]]
        after = {actor["slot"]: actor for actor in frames[index]["actors"]}
        before = {actor["slot"]: actor
                  for actor in frames[max(0, index - 1)]["actors"]}
        for change in event["changes"]:
            changes += 1
            actor = after.get(change["slot"]) or before.get(change["slot"])
            identity = identities.get((actor or {}).get("source", "").lower())
            if identity is None:
                continue
            joined += 1
            type_word = identity["type_word"]
            observed[type_word] += 1
            if not significant_change(change["fields"]):
                continue
            record = {
                "movie_frame": event["movie_frame"],
                "emulator_frame": event["emulator_frame"],
                "slot": change["slot"],
                "type_word": type_word,
                "actor_id": identity["actor_id"],
                "source_pointer": identity["source_pointer"],
                "program_selector": identity["program_selector"],
                "callback": identity["callback"].lower(),
                "changes": change["fields"],
            }
            all_significant_by_frame[event["movie_frame"]].append(record)
            if type_word in uncontrolled:
                significant.append(record)
                significant_by_frame[event["movie_frame"]].append(record)

    player_correlations = []
    for player_event in capsule["summary"]["player_typed_events"]:
        exact = all_significant_by_frame.get(player_event["movie_frame"], [])
        if exact:
            player_correlations.append({
                "movie_frame": player_event["movie_frame"],
                "cycle": player_event["cycle"],
                "player_fields": player_event["fields"],
                "actor_changes": exact,
                "top_frame_blocks": player_event["top_frame_blocks"],
                "uncontrolled_type_words": sorted({
                    item["type_word"] for item in exact
                    if item["type_word"] in uncontrolled}),
            })

    return {
        "movie": capsule["movie"],
        "records": len(frames),
        "actor_typed_event_records": len(capsule["actor_typed_events"]),
        "actor_change_records": changes,
        "actor_change_records_joined": joined,
        "observed_type_word_counts": dict(sorted(observed.items())),
        "uncontrolled_type_words_observed": sorted(set(observed).intersection(uncontrolled)),
        "uncontrolled_significant_changes": significant,
        "uncontrolled_significant_frames": sorted(significant_by_frame),
        "same_boundary_player_correlations": player_correlations,
        "summary": capsule["summary"],
        "frames": frames,
    }


def find_change(detail: dict, frame: int, slot: int) -> dict:
    matches = [item for item in detail["uncontrolled_significant_changes"]
               if item["movie_frame"] == frame and item["slot"] == slot]
    if not matches:
        # Known controls are not necessarily in the uncontrolled frontier.
        identities = detail["_all_significant_by_frame"]
        matches = [item for item in identities.get(frame, []) if item["slot"] == slot]
    if len(matches) != 1:
        raise ValueError(f"expected one actor change at frame {frame}, slot {slot}")
    return matches[0]


def build(external_path: Path) -> dict:
    queue = common.load_json(QUEUE_PATH)
    capsules = common.load_json(CAPSULE_PATH)
    contact = common.load_json(CONTACT_PATH)
    props = common.load_json(PROPS_PATH)
    outcome = common.load_json(OUTCOME_PATH)
    operator = common.load_json(OPERATOR_PATH)
    hazard = common.load_json(HAZARD_PATH)
    external_bytes = external_path.read_bytes()
    row, selected = validate_sources(
        queue, capsules, contact, external_path, external_bytes)
    external = json.loads(external_bytes)
    if external.get("schema") != CONFIGURATION["external_index"]["schema"] or \
            external.get("capsule_index_sha256") != \
            CONFIGURATION["external_index"]["generation_capsule_set_sha256"]:
        raise ValueError("external contact index schema or capsule-set pin drifted")
    reader = capsules.get("offline_reader_snapshot") or {}
    if external.get("reader") != reader or \
            contact.get("offline_batch", {}).get("reader_sha256") != reader.get("sha256"):
        raise ValueError("external contact index reader pin drifted")

    external_capsules = {item["movie"]: item for item in external.get("capsules") or []}
    selected_movies = {item["movie"] for item in selected}
    if set(external_capsules) != selected_movies:
        raise ValueError("external contact index does not contain exactly the E08 capsule set")
    queue_pins = {item["movie"]: item for item in row["relevant_capsules"]}
    for capsule in selected:
        pin = queue_pins[capsule["movie"]]
        external_summary = external_capsules[capsule["movie"]]["summary"]
        for key in ("movie_sha256", "capsule_manifest_sha256", "capsule_tree_sha256"):
            if pin[key] != capsule[key] or external_summary[key] != capsule[key]:
                raise ValueError(f"E08 capsule pin drifted: {capsule['movie']}:{key}")

    replays = {replay["fixture"]["movie"]["path"]: replay
               for document in (operator, hazard) for replay in document["replays"]}
    if set(replays) != selected_movies:
        raise ValueError("E08 replay/source maps do not match the selected capsule set")
    uncontrolled = {normalized_type(value)
                    for value in hazard["summary"]["remaining_uncontrolled_type_words"]}
    if len(uncontrolled) != 28 or \
            hazard["summary"]["unclassified_with_native_outcome_controls"] != 19:
        raise ValueError("E08 native-control frontier drifted")

    details = {}
    for movie in sorted(selected_movies):
        detail = join_movie(external_capsules[movie], replays[movie], uncontrolled)
        # Retain a private lookup during derivation only; it is stripped below.
        identities = source_map(replays[movie])
        all_by_frame: dict[int, list[dict]] = defaultdict(list)
        frames = detail["frames"]
        frame_indexes = {frame["movie_frame"]: index for index, frame in enumerate(frames)}
        for event in external_capsules[movie]["actor_typed_events"]:
            index = frame_indexes[event["movie_frame"]]
            after = {actor["slot"]: actor for actor in frames[index]["actors"]}
            before = {actor["slot"]: actor for actor in frames[max(0, index - 1)]["actors"]}
            for change in event["changes"]:
                actor = after.get(change["slot"]) or before.get(change["slot"])
                identity = identities.get((actor or {}).get("source", "").lower())
                if identity is None or not significant_change(change["fields"]):
                    continue
                all_by_frame[event["movie_frame"]].append({
                    "movie_frame": event["movie_frame"],
                    "emulator_frame": event["emulator_frame"],
                    "slot": change["slot"],
                    "type_word": identity["type_word"],
                    "actor_id": identity["actor_id"],
                    "source_pointer": identity["source_pointer"],
                    "program_selector": identity["program_selector"],
                    "callback": identity["callback"].lower(),
                    "changes": change["fields"],
                })
        detail["_all_significant_by_frame"] = all_by_frame
        details[movie] = detail

    totals = {
        "reconstructed_records": sum(item["records"] for item in details.values()),
        "actor_typed_event_records": sum(item["actor_typed_event_records"] for item in details.values()),
        "actor_change_records": sum(item["actor_change_records"] for item in details.values()),
        "actor_change_records_joined": sum(item["actor_change_records_joined"] for item in details.values()),
    }
    observed = sorted(set().union(*(
        set(item["uncontrolled_type_words_observed"]) for item in details.values())))
    significant_types = sorted({change["type_word"] for item in details.values()
                                for change in item["uncontrolled_significant_changes"]})

    expected = CONFIGURATION["expected_findings"]
    for key in ("actor_typed_event_records", "actor_change_records",
                "actor_change_records_joined"):
        if totals[key] != expected[key]:
            raise ValueError(f"E08 {key} drifted: {totals[key]}")
    if observed != [normalized_type(value)
                    for value in expected["uncontrolled_type_words_observed"]]:
        raise ValueError(f"E08 observed uncontrolled type words drifted: {observed}")
    if significant_types != [normalized_type(value) for value in
                             expected["uncontrolled_type_words_with_significant_changes"]]:
        raise ValueError(f"E08 significant uncontrolled type words drifted: {significant_types}")

    known_boundaries = []
    for expected_boundary in CONFIGURATION["known_native_boundaries"]:
        detail = details[expected_boundary["movie"]]
        change = find_change(detail, expected_boundary["movie_frame"], expected_boundary["slot"])
        if change["type_word"] != normalized_type(expected_boundary["type_word"]):
            raise ValueError("known E08 native boundary type word drifted")
        for field, value in expected_boundary["expected_changes"].items():
            if change["changes"].get(field) != value:
                raise ValueError(f"known E08 native boundary drifted: {field}")
        known_boundaries.append({
            "movie": expected_boundary["movie"],
            "movie_frame": expected_boundary["movie_frame"],
            "slot": expected_boundary["slot"],
            "type_word": change["type_word"],
            "changes": change["changes"],
            "reproduced": True,
        })

    player_correlations = [{"movie": movie, **correlation}
                           for movie, detail in details.items()
                           for correlation in detail["same_boundary_player_correlations"]]
    uncontrolled_correlations = [
        {"movie": item["movie"], "movie_frame": item["movie_frame"],
         "type_word": type_word, "player_fields": item["player_fields"]}
        for item in player_correlations
        for type_word in item["uncontrolled_type_words"]]
    expected_correlations = [{
        "movie": item["movie"], "movie_frame": item["movie_frame"],
        "type_word": normalized_type(item["type_word"]),
        "player_field": item["player_field"]}
        for item in expected["same_boundary_uncontrolled_player_correlations"]]
    actual_correlations = [{
        "movie": item["movie"], "movie_frame": item["movie_frame"],
        "type_word": item["type_word"],
        "player_field": next(iter(item["player_fields"]))}
        for item in uncontrolled_correlations]
    if actual_correlations != expected_correlations:
        raise ValueError(f"E08 player/actor correlations drifted: {actual_correlations}")

    hotspot_counts: Counter[str] = Counter()
    seen_frames = set()
    for movie, detail in details.items():
        frame_by_number = {frame["movie_frame"]: frame for frame in detail["frames"]}
        for frame_number in detail["uncontrolled_significant_frames"]:
            if (movie, frame_number) in seen_frames:
                continue
            seen_frames.add((movie, frame_number))
            for block in frame_by_number[frame_number]["top_frame_blocks"]:
                hotspot_counts[block["pc"]] += block["count"]

    capsule_summaries = []
    for movie, detail in details.items():
        summary = detail["summary"]
        capsule_summaries.append({
            "movie": movie,
            "movie_sha256": summary["movie_sha256"],
            "capsule_manifest_sha256": summary["capsule_manifest_sha256"],
            "capsule_tree_sha256": summary["capsule_tree_sha256"],
            "records": detail["records"],
            "actor_typed_event_records": detail["actor_typed_event_records"],
            "actor_change_records": detail["actor_change_records"],
            "actor_change_records_joined": detail["actor_change_records_joined"],
            "uncontrolled_type_words_observed": detail["uncontrolled_type_words_observed"],
            "uncontrolled_significant_event_count": len(detail["uncontrolled_significant_changes"]),
            "player_typed_event_count": len(summary["player_typed_events"]),
            "domain_change_frames": summary["domain_change_frames"],
        })

    significant_events = sorted(
        ({"movie": movie, **change} for movie, detail in details.items()
         for change in detail["uncontrolled_significant_changes"]),
        key=lambda item: (item["movie"], item["movie_frame"], item["slot"]))
    current_row = CONFIGURATION["selection_snapshot"]["rows"][0]
    return {
        "_comment": "Non-copyrighted E08 summary over the preserved external contact/hazard frame index.",
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(OUTPUT),
        "source_dependencies": {
            "analysis/phase4_trace_capsule_set.json": common.sha256(CAPSULE_PATH),
            "analysis/phase4_offline_contact_batch.json": common.sha256(CONTACT_PATH),
            "analysis/phase4_props_movers.json": common.sha256(PROPS_PATH),
            "analysis/phase4_e08_outcome_join.json": common.sha256(OUTCOME_PATH),
            "analysis/phase4_e08_operator_contacts.json": common.sha256(OPERATOR_PATH),
            "analysis/phase4_e08_hazard_outcomes.json": common.sha256(HAZARD_PATH),
            "config/phase4_offline_e08_batch.yaml": common.sha256(CONFIG_PATH),
            "tools/phase4_offline_e08_batch.py": common.sha256(Path(__file__)),
        },
        "selection_snapshot": CONFIGURATION["selection_snapshot"],
        "selected_rows": [{
            **current_row,
            "capsules": sorted(selected_movies),
        }],
        "offline_batch": {
            "reader_path": reader["absolute_path"],
            "reader_sha256": reader["sha256"],
            "generator_command": (
                "python3 tools/phase4_offline_e08_batch.py --external-index "
                + str(external_path) + " --write"),
            "capsule_count": len(selected_movies),
            **totals,
            "domains": ["registers", "ram", "vram", "spu_ram", "block_flow"],
            "exact_queue_queries": row["offline_batch_queries"],
            "query_count": len(row["offline_batch_queries"]),
            "reused_external_index": True,
        },
        "external_index": {
            "absolute_path": str(external_path),
            "sha256": hashlib.sha256(external_bytes).hexdigest(),
            "bytes": len(external_bytes),
            "schema": external["schema"],
            "media_class": "external game-derived evidence; never commit",
            "preservation_required": True,
            "reused_from": "analysis/phase4_offline_contact_batch.json",
        },
        "capsule_summaries": capsule_summaries,
        "derived_findings": {
            "native_control_frontier_unchanged": {
                "unclassified_with_native_outcome_controls": 19,
                "unclassified_without_native_outcome_control": 28,
                "class_owners_promoted": 0,
            },
            "uncontrolled_type_words_observed": observed,
            "uncontrolled_type_words_absent": sorted(uncontrolled.difference(observed)),
            "uncontrolled_type_words_with_significant_changes": significant_types,
            "uncontrolled_type_words_with_only_vm_timing_changes": sorted(
                set(observed).difference(significant_types)),
            "significant_uncontrolled_actor_events": significant_events,
            "known_native_boundaries_reproduced": known_boundaries,
            "same_boundary_player_actor_correlations": player_correlations,
            "same_boundary_uncontrolled_player_actor_correlations": uncontrolled_correlations,
            "significant_frame_top_block_aggregate": [
                {"pc": pc, "count": count}
                for pc, count in hotspot_counts.most_common(24)],
        },
        "bounded_conclusions": [
            "All 3,364 retained actor-change records join to measured authored source identities; no fixture filename supplies the type word.",
            "Seven of the 28 uncontrolled classes occur in actor-change records; five have HP/flags/source/identity/callback or knockback-activation boundaries.",
            "Type 0x1b1f knockback activation shares two LEVEL11 frame boundaries with player health loss and is a priority lead, not causal or semantic ownership proof.",
            "The four retained live typed boundaries reproduce at frame granularity, independently cross-checking their HP/flag leaves.",
            "Top-block aggregation is limited to the index's retained per-frame leaders and is passive block-start evidence, not an every-cycle trace.",
        ],
        "named_unknowns": {
            "ownership": "Final ownership remains unknown for the 19 outcome-controlled unowned classes and all 28 uncontrolled classes.",
            "native_controls": "The five newly prioritized classes still lack positive/negative native counterfactual controls; frame correlation does not consume this gap.",
            "authored_state": "Native switch/gate/mover state, initialization, capacity, retirement, denial and success behavior remain untyped.",
            "lifecycle": "Checkpoint, death, reload, transition and save/load persistence/reset remain untested for E08 interaction state.",
            "precision": "The capsules do not expose exact writer instructions/cycles, DMA/GPU submission, or SPU voice attribution.",
        },
        "live_escalation_ids": [],
        "live_escalation_decision": (
            "No live run: the current queue had no offline-ready row, E08 was the "
            "highest-ranked unconsumed subsystem-sized partial cluster, and its "
            "retained capsules answered the iteration's prioritization questions."),
        "campaign_closed": False,
        "errors": [],
        "valid": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--external-index", type=Path,
        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/contact-hazard-v1/index.json")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    external_path = args.external_index.resolve()
    try:
        document = build(external_path)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    output = render(document)
    if args.write:
        OUTPUT.write_bytes(output)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != output:
            print("tracked Phase-4 E08 offline summary is missing or stale", file=sys.stderr)
            return 1
    else:
        print(output.decode(), end="")
    findings = document["derived_findings"]
    print(
        f"PASS: rows=1 capsules={document['offline_batch']['capsule_count']} "
        f"changes={document['offline_batch']['actor_change_records_joined']} "
        f"observed={len(findings['uncontrolled_type_words_observed'])}/28 "
        f"significant={len(findings['uncontrolled_type_words_with_significant_changes'])}/28",
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
