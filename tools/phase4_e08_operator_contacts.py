#!/usr/bin/env python3
"""Replay existing operator contact movies and route measured E08 actor outcomes.

The operator filenames are discovery leads, not semantic proof.  This generator
therefore retains only outcomes measured from the paired, load-free-inspected
pristine save states: actor/source type words, typed actor response transitions,
player transitions, and cycle-neutral resident-code coverage.  It does not turn
the filename into a species label or complete an enemy-family campaign.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

try:
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
    from phase4_props_movers import (
        ACTOR_BASE, ACTOR_CAPACITY, ACTOR_STRIDE, PLAYER_BASE,
        _actor_snapshot as actor_snapshot,
        _read_memory as read_memory,
    )
except ModuleNotFoundError:  # imported as tools.phase4_e08_operator_contacts
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
    from tools.phase4_props_movers import (
        ACTOR_BASE, ACTOR_CAPACITY, ACTOR_STRIDE, PLAYER_BASE,
        _actor_snapshot as actor_snapshot,
        _read_memory as read_memory,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_e08_operator_contacts.json"
PROPS = ROOT / "analysis/phase4_props_movers.json"
OUTCOME_JOIN = ROOT / "analysis/phase4_e08_outcome_join.json"

FIXTURES = (
    ("D08_fly_lead", "D08_flies", "D08_fly_contact_kill"),
    ("D09_cockroach_lead", "D09_cockroaches", "D09_cockroach_contact_kill"),
    ("D11_grub_lead", "D11_mites_grubs", "D11_grub_contact_kill"),
    ("D11_mite_lead", "D11_mites_grubs", "D11_mite_contact_kill"),
    ("D15_daddy_long_legs_lead", "D15_daddy_long_legs",
     "D15_daddy_long_legs_contact_kill"),
)

MOVIE_DIR = "movies/Phase4"
PLAYER_SIZE = 0xA4
TRACE_RANGES = (
    {"start": "0x80049C30", "end": "0x8004D698",
     "label": "actor_init_vm_contact_and_update", "max_pcs": 200000},
    {"start": "0x80058D68", "end": "0x80059600",
     "label": "resident_actor_damage_and_immunity", "max_pcs": 200000},
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _method_present(capabilities: dict[str, Any], method: str) -> bool:
    methods = capabilities.get("methods") or []
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in methods)


def _cleanup_movie(client: Any) -> None:
    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    try:
        client.call("movie.clear", {})
    except Exception:
        pass


def _fixture_paths(stem: str) -> tuple[str, str]:
    return (f"{MOVIE_DIR}/{stem}.movie.json",
            f"{MOVIE_DIR}/{stem}.movie.sav")


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    rows = []
    for lead, row_lead, stem in FIXTURES:
        movie_rel, save_rel = _fixture_paths(stem)
        movie_path, save_path = ROOT / movie_rel, ROOT / save_rel
        movie_pin = entries.get(movie_rel)
        save = verify_declared_save_fixture(
            save_path, allowed_media_classes={"pristine"})
        if not isinstance(movie_pin, dict) or \
                movie_pin.get("media_class") != "pristine_serial" or \
                movie_pin.get("size") != movie_path.stat().st_size or \
                movie_pin.get("sha256") != _sha256(movie_path):
            raise SystemExit(f"operator contact movie pin drifted: {movie_rel}")
        movie = json.loads(movie_path.read_text())
        start = movie.get("start_state") or {}
        if movie.get("version") != 3 or \
                movie.get("game_serial") != "SCUS-94288" or \
                start.get("game_serial") != "SCUS-94288" or \
                start.get("from_boot") is not False or \
                start.get("reproducible_only_from_state") is not True or \
                start.get("file_size") != save["size"] or \
                not movie.get("frames"):
            raise SystemExit(f"operator contact movie metadata drifted: {movie_rel}")
        rows.append({
            "lead": lead, "row_lead": row_lead,
            "movie": {"path": movie_rel, "sha256": movie_pin["sha256"],
                      "size": movie_pin["size"], "media_class": movie_pin["media_class"],
                      "version": movie["version"], "frames": len(movie["frames"]),
                      "initial_frame": movie["initial_frame"]},
            "save": save,
            "classification_boundary": (
                "operator path is a campaign lead only; measured actor/source "
                "and outcome state determine the retained conclusion"),
        })
    return {"manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
            "count": len(rows), "pairs": rows}


def _player_fields(raw: bytes) -> dict[str, Any]:
    return {
        "position": list(struct.unpack_from("<iii", raw, 0)),
        "velocity_y": struct.unpack_from("<i", raw, 0x30)[0],
        "kick_timer": struct.unpack_from("<h", raw, 0x7A)[0],
        "state": struct.unpack_from("<h", raw, 0x80)[0],
        "grounded": struct.unpack_from("<h", raw, 0x82)[0],
        "animation": struct.unpack_from("<h", raw, 0x88)[0],
        "health": struct.unpack_from("<h", raw, 0x94)[0],
        "lives": raw[0xA0],
    }


def _actor_fields(raw: bytes, slot: int) -> dict[str, Any]:
    row = raw[slot * ACTOR_STRIDE:(slot + 1) * ACTOR_STRIDE]
    return {
        "id": struct.unpack_from("<I", row, 0)[0],
        "flags": struct.unpack_from("<H", row, 0x5C)[0],
        "state": struct.unpack_from("<h", row, 0x6C)[0],
        "hp_or_response": struct.unpack_from("<h", row, 0x6E)[0],
        "source_pointer": f"0x{struct.unpack_from('<I', row, 0x80)[0]:08X}",
    }


def _typed_snapshot(client: Any) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    actor_raw = read_memory(client, ACTOR_BASE, ACTOR_CAPACITY * ACTOR_STRIDE)
    player_raw = read_memory(client, PLAYER_BASE, PLAYER_SIZE)
    return {
        "frame": status["frame"], "cycle": status["cycle"], "pc": status["pc"],
        "actors": [_actor_fields(actor_raw, slot) for slot in range(ACTOR_CAPACITY)],
        "player": _player_fields(player_raw),
    }


def _source_identity(client: Any, snapshot: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result = {}
    full = actor_snapshot(client)
    by_slot = {row["slot"]: row for row in full["records"]}
    for slot, actor in enumerate(snapshot["actors"]):
        if not actor["id"]:
            continue
        row = by_slot.get(slot)
        if not row or row["id"] != actor["id"] or \
                row["source_pointer"] != actor["source_pointer"]:
            raise SystemExit(f"actor/source identity drifted in slot {slot}")
        source = row["source"]
        type_word = (source["program_selector"] << 8) | source["actor_id"]
        result[slot] = {
            "actor_id": row["id"], "source_pointer": row["source_pointer"],
            "type_word": f"0x{type_word:04X}",
            "program_selector": source["program_selector"],
            "callback": row["callback"], "source_flags": source["source_flags"],
            "authored_signature_sha256": source["authored_signature_sha256"],
        }
    return result


def _compact_trace(trace: dict[str, Any]) -> dict[str, Any]:
    coverage = []
    for row in trace["coverage"]:
        data = row["coverage"]
        coverage.append({
            "label": row["label"], "range": row["range"],
            "total_hits": data["total_hits"],
            "distinct_pc_count": data["distinct_pc_count"],
            "truncated": data.get("truncated", False),
            "pcs": data["pcs"],
        })
    return {
        key: trace[key] for key in (
            "target_frame", "trace_mode", "configured_execution_mode",
            "comparison_execution_mode", "control", "instrumented", "comparison")
    } | {"coverage": coverage}


def _decisive_outcome(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return bool(
        (before["id"] and not after["id"]) or
        after["hp_or_response"] < before["hp_or_response"] or
        (after["state"] in {-20, 30} and after["state"] != before["state"])
    )


def _trace_state_at_frame(
        client: Any, movie_path: Path, target: int,
        *, ranges: tuple[dict[str, Any], ...] = TRACE_RANGES) -> dict[str, Any]:
    """Replay control/instrumented branches from the anchor to one target."""
    trace = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": target,
        "ranges": list(ranges)}, timeout=900)
    trace = _compact_trace(trace)
    if trace["comparison"].get("cycle_neutral") is not True or \
            any(row["truncated"] for row in trace["coverage"]):
        raise SystemExit(
            f"operator contact trace was not cycle-neutral at {target}: "
            f"{trace['comparison']}")
    snapshot = _typed_snapshot(client)
    status = client.call("movie.status", {})
    expected_movie_frame = (
        0 if target == status.get("frame_count") and status.get("playing") is False
        else target)
    if status.get("reproducible") is not True or \
            status.get("truncated") is not False or \
            trace["instrumented"]["movie_frame"] != expected_movie_frame:
        raise SystemExit(
            f"operator contact trace lost its movie anchor: target={target} "
            f"instrumented={trace['instrumented']} status={status}")
    return {"snapshot": snapshot, "movie_status": status, "trace": trace}


def _locate_first_outcome(
        client: Any, movie_path: Path, frame_count: int, slot: int,
        initial_actor: dict[str, Any]) -> dict[str, Any]:
    """Binary-search a stable final outcome using fresh continuous replays."""
    lo, hi = 1, frame_count
    probes = []
    while lo < hi:
        mid = (lo + hi) // 2
        replay = _trace_state_at_frame(
            client, movie_path, mid, ranges=(TRACE_RANGES[0],))
        actor = replay["snapshot"]["actors"][slot]
        matched = _decisive_outcome(initial_actor, actor)
        probes.append({"movie_frame": mid, "matched": matched,
                       "emulator_frame": replay["snapshot"]["frame"],
                       "cycle": replay["snapshot"]["cycle"]})
        if matched:
            hi = mid
        else:
            lo = mid + 1
    before = _trace_state_at_frame(
        client, movie_path, lo - 1, ranges=(TRACE_RANGES[0],))
    after = _trace_state_at_frame(
        client, movie_path, lo, ranges=(TRACE_RANGES[0],))
    before_actor = before["snapshot"]["actors"][slot]
    after_actor = after["snapshot"]["actors"][slot]
    if _decisive_outcome(initial_actor, before_actor) or \
            not _decisive_outcome(initial_actor, after_actor):
        raise SystemExit(
            f"operator contact outcome was not a stable first boundary: "
            f"slot={slot} frame={lo}")
    return {
        "movie_frame": lo, "probes": probes,
        "before": {"emulator_frame": before["snapshot"]["frame"],
                   "cycle": before["snapshot"]["cycle"],
                   "actor": before_actor,
                   "player": before["snapshot"]["player"]},
        "after": {"emulator_frame": after["snapshot"]["frame"],
                  "cycle": after["snapshot"]["cycle"],
                  "actor": after_actor,
                  "player": after["snapshot"]["player"]},
        "search_rule": (
            "fresh recorded-anchor replay for every probe; no per-frame "
            "instrumentation or state mutation"),
    }


def _run_movie(client: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    movie = fixture["movie"]
    frame_count = movie["frames"]
    movie_path = ROOT / movie["path"]
    start = _trace_state_at_frame(
        client, movie_path, 0, ranges=(TRACE_RANGES[0],))
    initial = start["snapshot"]
    sources = _source_identity(client, initial)
    full = _trace_state_at_frame(client, movie_path, frame_count)
    final = full["snapshot"]
    outcome_slots = {
        slot for slot in range(ACTOR_CAPACITY)
        if _decisive_outcome(initial["actors"][slot], final["actors"][slot])
    }
    print(f"[e08-operator-contacts] {fixture['lead']} continuous "
          f"0->{frame_count}; outcome_slots={sorted(outcome_slots)}")

    trace = full["trace"]

    controlled = sorted({sources[slot]["type_word"] for slot in outcome_slots
                         if slot in sources})
    boundaries = []
    for slot in sorted(outcome_slots):
        if slot not in sources:
            raise SystemExit(f"outcome actor slot {slot} lacked start-state source identity")
        boundary = _locate_first_outcome(
            client, movie_path, frame_count, slot, initial["actors"][slot])
        boundaries.append({"slot": slot, "source_identity": sources[slot],
                           **boundary})
    _cleanup_movie(client)
    return {
        "lead": fixture["lead"], "row_lead": fixture["row_lead"],
        "fixture": fixture,
        "initial": {"frame": initial["frame"], "cycle": initial["cycle"],
                    "player": initial["player"], "actor_sources": sources,
                    "cycle_neutral_trace": start["trace"]},
        "final": {"frame": final["frame"], "cycle": final["cycle"],
                  "player": final["player"],
                  "ram_sha256": trace["control"]["ram_sha256"],
                  "movie_status": full["movie_status"]},
        "native_outcome_boundaries": boundaries,
        "controlled_type_words": controlled,
        "typed_outcome_observed": bool(controlled),
        "cycle_neutral_trace": trace,
        "classification_boundary": (
            "a measured natural outcome extends outcome coverage only; it does not "
            "assign E08, enemies/combat, D-row, or species ownership, and a "
            "zero-outcome replay remains a bounded negative"),
    }


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    """Recompute proof predicates without trusting the retained summary."""
    gaps = []
    replays = document.get("replays") or []
    if len(replays) != 5:
        gaps.append("operator contact replay count changed")
    controlled = set()
    for replay in replays:
        boundaries = replay.get("native_outcome_boundaries") or []
        derived = set()
        for row in boundaries:
            before = row.get("before") or {}
            after = row.get("after") or {}
            before_actor = before.get("actor") or {}
            after_actor = after.get("actor") or {}
            identity = row.get("source_identity") or {}
            if not before_actor or not after_actor or \
                    _decisive_outcome(before_actor, before_actor) or \
                    not _decisive_outcome(before_actor, after_actor):
                gaps.append(f"{replay.get('lead')}: native outcome boundary changed")
            if row.get("movie_frame", 0) <= 0 or \
                    after.get("cycle", 0) <= before.get("cycle", 0) or \
                    after.get("emulator_frame", 0) <= before.get("emulator_frame", 0):
                gaps.append(f"{replay.get('lead')}: trigger timing boundary changed")
            if identity.get("type_word"):
                derived.add(identity["type_word"])
        retained = set(replay.get("controlled_type_words") or [])
        if derived != retained or replay.get("typed_outcome_observed") is not bool(retained):
            gaps.append(f"{replay.get('lead')}: typed outcome derivation changed")
        trace = replay.get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in trace.get("coverage") or []):
            gaps.append(f"{replay.get('lead')}: cycle-neutral trace changed")
        final = replay.get("final") or {}
        if final.get("ram_sha256") != (trace.get("control") or {}).get("ram_sha256"):
            gaps.append(f"{replay.get('lead')}: final RAM/control identity changed")
        controlled.update(retained)

    summary = document.get("summary") or {}
    if sorted(value.lower() for value in controlled) != \
            sorted(summary.get("controlled_type_words") or []):
        gaps.append("operator controlled type-word union changed")
    join = json.loads(OUTCOME_JOIN.read_text())
    previously_controlled = {
        value.lower() for value in
        join["unclassified_type_words_with_native_contact_controls"]}
    previously_uncontrolled = {
        value.lower() for value in
        join["unclassified_type_words_without_native_contact_control"]}
    new = {value.lower() for value in controlled} & previously_uncontrolled
    aggregate = previously_controlled | new
    remaining = previously_uncontrolled - new
    if sorted(new) != summary.get("newly_controlled_unclassified_type_words") or \
            len(aggregate) != summary.get("unclassified_with_native_outcome_controls") or \
            len(remaining) != summary.get("unclassified_without_native_outcome_control") or \
            sorted(remaining) != summary.get("remaining_uncontrolled_type_words") or \
            summary.get("species_or_row_owners_promoted") != 0:
        gaps.append("aggregate E08 native-outcome partition changed")
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned live process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixtures = build_fixture_census()
    props = json.loads(PROPS.read_text())
    join = json.loads(OUTCOME_JOIN.read_text())
    unclassified = {
        row["type_word"].lower()
        for row in props["live"]["source_actor_clusters"]["behavior_classes"]
        if row["owner_classification"].startswith("unclassified")
    }
    previously_controlled = {
        value.lower() for value in
        join["unclassified_type_words_with_native_contact_controls"]
    }
    previously_uncontrolled = {
        value.lower() for value in
        join["unclassified_type_words_without_native_contact_control"]
    }
    if len(unclassified) != 47 or len(previously_controlled) != 18 or \
            len(previously_uncontrolled) != 29 or \
            previously_controlled | previously_uncontrolled != unclassified:
        raise SystemExit("retained E08 unclassified partition drifted")

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "emulator.getMediaInfo", "emulator.getStateInfo",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks E08 operator-contact methods: {missing}")
    client.call("debugger.pause", {})
    inspections = [inspect_state_before_load(
        client, ROOT / row["save"]["path"], media_identity)
        for row in fixtures["pairs"]]
    replays = [_run_movie(client, row) for row in fixtures["pairs"]]
    final_media = verified_media_identity(client, client.call("debugger.status", {}))

    controlled = sorted({type_word.lower() for replay in replays
                         for type_word in replay["controlled_type_words"]})
    outside_frontier = sorted(set(controlled) - unclassified)
    newly_controlled = sorted(set(controlled) & previously_uncontrolled)
    retained_controlled = sorted(previously_controlled | set(newly_controlled))
    remaining = sorted(unclassified - set(retained_controlled))
    if outside_frontier or not newly_controlled or \
            len(retained_controlled) + len(remaining) != 47:
        raise SystemExit(
            "operator contact outcomes did not extend the bounded E08 frontier: "
            f"outside={outside_frontier} new={newly_controlled}")

    provenance = finish_run(
        args, generator="tools/phase4_e08_operator_contacts.py",
        anchor={
            "type": "five existing state-anchored operator contact movies",
            "saves": [row["save"]["path"] for row in fixtures["pairs"]],
            "fixture_sha256": {row["save"]["path"]: row["save"]["sha256"]
                               for row in fixtures["pairs"]},
            "state_inspections": inspections, "media_identity": media_identity,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "movie_end_rule": "consume every recorded frame",
            "typed_sampling": (
                "cycle-neutral anchor-to-target branches; stable first outcome "
                "located by fresh binary-search replays"),
            "coverage_control": "movie.traceToFrame uninstrumented versus passive cached-block replay",
        })
    document = {
        "_comment": (
            "Natural E08 actor/source outcome controls from existing operator "
            "recordings. Filenames remain row/species leads, never semantic proof."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-e08-operator-contacts/1",
        "fixture_census": fixtures,
        "replays": replays,
        "summary": {
            "movies_replayed": len(replays),
            "controlled_type_words": controlled,
            "newly_controlled_unclassified_type_words": newly_controlled,
            "unclassified_with_native_outcome_controls": len(retained_controlled),
            "unclassified_without_native_outcome_control": len(remaining),
            "remaining_uncontrolled_type_words": remaining,
            "species_or_row_owners_promoted": 0,
        },
        "bounded_interpretation": {
            "observation": (
                "Each retained type word produced a natural typed actor outcome "
                "during a complete reproducible movie replay."),
            "inference": (
                "Those type words extend E08's native-outcome measurement frontier "
                "without assigning them to props/switches/gates, enemies/combat, "
                "any D-row, or a species."),
            "causal_confirmation": (
                "The existing movies are natural positive controls; no input edit "
                "or species-identifying counterfactual was performed."),
            "forbidden_claim": (
                "Do not assign a D-row species or complete an enemy campaign from "
                "the operator filename or this outcome routing alone."),
        },
        "source_dependencies": {
            "tools/phase4_props_movers.py": _sha256(
                ROOT / "tools/phase4_props_movers.py"),
            "analysis/phase4_props_movers.json": _sha256(PROPS),
            "analysis/phase4_e08_outcome_join.json": _sha256(OUTCOME_JOIN),
        },
        "run_provenance": provenance,
    }
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained E08 operator-contact evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print(
        "[e08-operator-contacts] "
        f"{len(newly_controlled)} new controls; "
        f"{len(remaining)} of 47 unclassified type words remain uncontrolled")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(
                args, generator="tools/phase4_e08_operator_contacts.py",
                anchor={"type": "aborted before retained E08 operator-contact evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(
                f"owned E08 operator-contact cleanup also failed: {cleanup_error}",
                file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
