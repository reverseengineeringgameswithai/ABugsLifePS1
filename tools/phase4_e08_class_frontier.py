#!/usr/bin/env python3
"""Build the bounded static E08 uncontrolled-class frontier."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sys

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_e08_class_frontier.yaml"
PROPS_PATH = common.ROOT / "analysis/phase4_props_movers.json"
CONTACTS_PATH = common.ROOT / "analysis/phase4_e08_operator_contacts.json"
OFFLINE_PATH = common.ROOT / "analysis/phase4_offline_e08_batch.json"
PROGRAMS_PATH = common.ROOT / "analysis/vm_programs.json"
FUNCTIONS_PATH = common.ROOT / "analysis/functions.json"
SEGMENTS_PATH = common.ROOT / "config/segments.yml"
OUTPUT = common.ROOT / "analysis/phase4_e08_class_frontier.json"


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            generated = common.load_json(OUTPUT).get("generated")
            if isinstance(generated, str) and generated:
                return generated
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def norm_hex(value: str | int) -> str:
    number = int(value, 0) if isinstance(value, str) else value
    return f"0x{number:08x}"


def norm_type(value: str) -> str:
    return f"0x{int(value, 0):04x}"


def _one_by(items: list[dict], key: str, value: object, label: str) -> dict:
    matches = [item for item in items if item.get(key) == value]
    if len(matches) != 1:
        raise ValueError(f"{label} must resolve exactly once, got {len(matches)}")
    return matches[0]


def _program_map(programs: dict, expected: dict) -> dict[int, dict]:
    if programs.get("schema_version") != 2 or \
            programs.get("selector_count") != expected["selector_count"]:
        raise ValueError("decoded VM selector census drifted")
    result: dict[int, dict] = {}
    for program in programs.get("programs") or []:
        if not program.get("decode_complete"):
            raise ValueError(f"incomplete VM program {program.get('id')}")
        for selector in program.get("selectors") or []:
            if selector in result:
                raise ValueError(f"duplicate decoded VM selector {selector}")
            result[selector] = program
    if set(result) != set(range(expected["selector_count"])):
        raise ValueError("decoded VM selector map is not exactly 0..39")
    return result


def _callback_census(classes: list[dict], functions: dict, segments: dict,
                     expected: dict) -> dict[str, dict]:
    callbacks = sorted({
        norm_hex(callback)
        for row in classes
        for callback in row.get("callbacks") or []
        if int(callback, 0)
    })
    if len(callbacks) != expected["callback_functions"]:
        raise ValueError("resident callback census count drifted")
    function_rows = functions.get("functions") or []
    attempted = segments.get("attempted") or []
    result: dict[str, dict] = {}
    for callback in callbacks:
        function = _one_by(
            function_rows, "start", callback, f"callback function {callback}")
        segment = _one_by(
            attempted, "start", int(callback, 0), f"callback source {callback}")
        if function.get("space") != "resident" or \
                function.get("classification") != "game" or \
                function.get("confidence") != "confirmed" or \
                function.get("match") not in {"asm", "c"}:
            raise ValueError(f"callback function classification drifted: {callback}")
        source = segment.get("source")
        expected_match = "c" if str(source).endswith(".c") else "asm"
        if function["match"] != expected_match or \
                int(segment["end"]) != int(function["end"], 0):
            raise ValueError(f"callback source join drifted: {callback}")
        result[callback] = {
            "start": callback,
            "end": function["end"],
            "size": function["size"],
            "name": function["name"],
            "match": function["match"],
            "source": source,
            "source_sha256": common.sha256(common.ROOT / source),
        }
    return result


def _offline_partition(offline: dict, uncontrolled: set[str]) -> tuple[
        dict[str, str], dict[str, list[str]], Counter[str]]:
    findings = offline.get("derived_findings") or {}
    partitions = {
        "retained_significant": {
            norm_type(value)
            for value in findings.get(
                "uncontrolled_type_words_with_significant_changes") or []},
        "retained_timing_only": {
            norm_type(value)
            for value in findings.get(
                "uncontrolled_type_words_with_only_vm_timing_changes") or []},
        "retained_absent": {
            norm_type(value)
            for value in findings.get("uncontrolled_type_words_absent") or []},
    }
    flattened = [value for values in partitions.values() for value in values]
    if len(flattened) != len(set(flattened)) or set(flattened) != uncontrolled:
        raise ValueError("offline evidence does not partition the uncontrolled set")
    cohort = {
        value: name for name, values in partitions.items() for value in values}
    movies: dict[str, list[str]] = defaultdict(list)
    for capsule in offline.get("capsule_summaries") or []:
        for value in capsule.get("uncontrolled_type_words_observed") or []:
            movies[norm_type(value)].append(capsule["movie"])
    significant_counts = Counter(
        norm_type(event["type_word"])
        for event in findings.get("significant_uncontrolled_actor_events") or [])
    return cohort, dict(movies), significant_counts


def build() -> dict:
    config = common.load_yaml(CONFIG_PATH)
    props = common.load_json(PROPS_PATH)
    contacts = common.load_json(CONTACTS_PATH)
    offline = common.load_json(OFFLINE_PATH)
    programs = common.load_json(PROGRAMS_PATH)
    functions = common.load_json(FUNCTIONS_PATH)
    segments = common.load_yaml(SEGMENTS_PATH)
    if config.get("schema") != "abl-phase4-e08-class-frontier-source/1":
        raise ValueError("E08 class-frontier source schema drifted")
    expected = config["expected"]

    classes = props["live"]["source_actor_clusters"]["behavior_classes"]
    if len(classes) != expected["behavior_classes"]:
        raise ValueError("behavior-class census drifted")
    type_words = [norm_type(row["type_word"]) for row in classes]
    if len(type_words) != len(set(type_words)):
        raise ValueError("behavior-class type words are duplicated")
    downstream = {
        norm_type(row["type_word"]) for row in classes
        if row.get("owner_classification") == "confirmed_downstream"}
    unowned_rows = [
        row for row in classes
        if row.get("owner_classification") ==
        "unclassified_e08_or_downstream_candidate"]
    unowned = {norm_type(row["type_word"]) for row in unowned_rows}
    if len(downstream) != expected["downstream_owned_classes"] or \
            len(unowned) != expected["unowned_classes"] or \
            downstream.intersection(unowned) or \
            len(downstream | unowned) != len(classes):
        raise ValueError("downstream/unowned class partition drifted")

    summary = contacts.get("summary") or {}
    uncontrolled_values = [
        norm_type(value)
        for value in summary.get("remaining_uncontrolled_type_words") or []]
    uncontrolled = set(uncontrolled_values)
    if len(uncontrolled_values) != len(uncontrolled) or \
            not uncontrolled.issubset(unowned) or \
            len(uncontrolled) != expected["uncontrolled_classes"] or \
            len(unowned - uncontrolled) != expected["controlled_unowned_classes"]:
        raise ValueError("native-control class partition drifted")
    if summary.get("unclassified_with_native_outcome_controls") != \
            expected["controlled_unowned_classes"] or \
            summary.get("unclassified_without_native_outcome_control") != \
            expected["uncontrolled_classes"]:
        raise ValueError("native-control aggregate disagrees with its class list")

    program_by_selector = _program_map(programs, expected)
    callback_by_address = _callback_census(
        classes, functions, segments, expected)
    cohort_by_type, movies_by_type, significant_counts = _offline_partition(
        offline, uncontrolled)
    cohort_counts = Counter(cohort_by_type.values())
    if cohort_counts != Counter({
            "retained_significant": expected["retained_significant_classes"],
            "retained_timing_only": expected["retained_timing_only_classes"],
            "retained_absent": expected["retained_absent_classes"],
    }):
        raise ValueError("retained evidence cohort counts drifted")

    policy = config["priority_policy"]
    cohort_rank = {
        name: index for index, name in enumerate(policy["cohort_order"])}
    weights = policy["interface_weights"]
    path_opcodes = set(policy["path_opcodes"])
    frontier = []
    for source in unowned_rows:
        type_word = norm_type(source["type_word"])
        if type_word not in uncontrolled:
            continue
        selector = int(source["program_selector"])
        if not 0 <= selector < expected["selector_count"]:
            raise ValueError(f"selector outside decoded domain: {type_word}")
        program = program_by_selector[selector]
        opcodes = list(program["behavior_signature"])
        callbacks = [norm_hex(value) for value in source.get("callbacks") or []]
        unknown_callbacks = [
            value for value in callbacks
            if int(value, 0) and value not in callback_by_address]
        if unknown_callbacks:
            raise ValueError(
                f"unknown callbacks for {type_word}: {unknown_callbacks}")
        nonzero_callbacks = [
            callback_by_address[value]
            for value in callbacks if int(value, 0)]
        interface_score = (
            weights["call_native"] * int("call_native" in opcodes) +
            weights["player_proximity"] * int("player_proximity" in opcodes) +
            weights["nonzero_callback"] * int(bool(nonzero_callbacks)) +
            weights["path_motion"] * int(bool(path_opcodes.intersection(opcodes)))
        )
        cohort = cohort_by_type[type_word]
        row = {
            "type_word": type_word,
            "actor_id": int(source["actor_id"]),
            "program_selector": selector,
            "program": {
                "id": program["id"],
                "entry": program["entry"],
                "end": program["end"],
                "instruction_count": program["instruction_count"],
                "behavior_signature": opcodes,
                "decode_complete": program["decode_complete"],
            },
            "callbacks": callbacks,
            "callback_functions": nonzero_callbacks,
            "authored_observations": int(source["observations"]),
            "authored_signatures": source["authored_signatures"],
            "authored_parameter_hashes": source["authored_parameter_hashes"],
            "labels": source["labels"],
            "scenes": source["scenes"],
            "moved_observations": int(source["moved_observations"]),
            "evidence_cohort": cohort,
            "retained_movies": sorted(movies_by_type.get(type_word, [])),
            "significant_event_records": significant_counts[type_word],
            "interface_score": interface_score,
            "semantic_owner": None,
            "native_outcome_control": False,
            "next_action": (
                "Reconstruct the native trigger and writer from this exact "
                "program/callback/source interface before any owner claim."),
        }
        row["_sort"] = (
            cohort_rank[cohort],
            -interface_score,
            -row["authored_observations"],
            type_word,
        )
        frontier.append(row)
    frontier.sort(key=lambda row: row.pop("_sort"))
    for rank, row in enumerate(frontier, 1):
        row["priority_rank"] = rank
    if [row["type_word"] for row in frontier[:5]] != \
            policy["expected_first_five"]:
        raise ValueError("static frontier priority order drifted")
    moved = [row["type_word"] for row in frontier if row["moved_observations"]]
    if len(moved) != expected["moved_uncontrolled_classes"]:
        raise ValueError("uncontrolled movement census drifted")

    callback_rows = [
        callback_by_address[address] for address in sorted(callback_by_address)]
    return {
        "_comment": (
            "Generated static E08 closure frontier. Recompute with "
            "python3 tools/phase4_e08_class_frontier.py --check."),
        "schema": "abl-phase4-e08-class-frontier/1",
        "generated": stable_generated(),
        "campaign_id": config["campaign_id"],
        "row_id": config["row_id"],
        "source_dependencies": {
            str(path.relative_to(common.ROOT)): common.sha256(path)
            for path in (
                CONFIG_PATH, PROPS_PATH, CONTACTS_PATH, OFFLINE_PATH,
                PROGRAMS_PATH, FUNCTIONS_PATH, SEGMENTS_PATH)
        },
        "summary": {
            "behavior_classes": len(classes),
            "downstream_owned_classes": len(downstream),
            "unowned_classes": len(unowned),
            "controlled_unowned_classes": len(unowned - uncontrolled),
            "uncontrolled_classes": len(frontier),
            "retained_significant_classes": cohort_counts["retained_significant"],
            "retained_timing_only_classes": cohort_counts["retained_timing_only"],
            "retained_absent_classes": cohort_counts["retained_absent"],
            "duplicate_type_words": 0,
            "missing_class_joins": 0,
            "unknown_callbacks": 0,
            "selectors_outside_decoded_domain": 0,
            "moved_uncontrolled_classes": len(moved),
            "class_owners_promoted": 0,
        },
        "callback_census": callback_rows,
        "frontier": frontier,
        "claim_boundary": config["claim_boundary"],
        "bounded_conclusions": [
            "The 28 classes are the duplicate-free complement of 19 controlled classes inside the exact 47-class unowned actor/source universe.",
            "Each class joins to one decoded selector program, authored source signatures, the exact resident callback census, and one retained-evidence cohort.",
            "Five significant frame-boundary classes rank before two timing-only and 21 absent classes; priority selects static/live targets but proves no semantic owner or causality.",
            "No uncontrolled class moved in the retained source catalog, so movement cannot distinguish the current frontier.",
            "Complete-frontier closure remains false while native outcome writers, final owners, authored state, denial/success, lifecycle, and persistence intersect E08.",
        ],
        "next_live_candidates": [
            {
                "priority_rank": row["priority_rank"],
                "type_word": row["type_word"],
                "evidence_cohort": row["evidence_cohort"],
                "program_selector": row["program_selector"],
                "program_id": row["program"]["id"],
                "callbacks": row["callbacks"],
                "retained_movies": row["retained_movies"],
            }
            for row in frontier[:5]
        ],
        "valid": True,
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        document = build()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    output = render(document)
    if args.write:
        OUTPUT.write_bytes(output)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != output:
            print("tracked E08 class frontier is missing or stale", file=sys.stderr)
            return 1
    else:
        print(output.decode(), end="")
    print(
        f"PASS: frontier={document['summary']['uncontrolled_classes']} "
        f"significant={document['summary']['retained_significant_classes']} "
        f"timing={document['summary']['retained_timing_only_classes']} "
        f"absent={document['summary']['retained_absent_classes']}",
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
