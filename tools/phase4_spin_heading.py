#!/usr/bin/env python3
"""Regenerate the Phase-4 A07 directional-spin/heading campaign.

The historical lead called this a secret ``spin`` move.  The pristine game
implements the reproducible behavior as an ordinary sequence of current
direction samples: each sample writes a desired 12-bit heading and the resident
player controller turns Flik toward it.  No history recognizer or private spin
mode participates.  This tool binds that positive heading behavior without
turning the earlier bounded negative into an absence proof.
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
    from build_identity import verify_staged_input
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )
    import phase4_run_locomotion as run_common
except ModuleNotFoundError:
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )
    from tools import phase4_run_locomotion as run_common


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_spin_heading.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

PLAYER_BASE = 0x800A6500
ACTION_WORD = 0x80082488
PAUSE_FLAG = 0x8008224E
ACTOR_RECORD_BASE = 0x8009FE04
HEADING_MASK = 0x0FFF
DIRECTION_MASK = 0x00F0
CARDINAL_MASKS = {"up": 0x10, "right": 0x20, "down": 0x40, "left": 0x80}

SOURCE_ORDER = ("left", "up", "right", "down")
REVERSE_ORDER = ("left", "down", "right", "up")
DWELL_FRAMES = 4
RELEASE_FRAMES = 1
POST_FRAMES = 12
SETTLE_FRAMES = 3
BLOCK_FRAMES = DWELL_FRAMES + RELEASE_FRAMES

CONTROL_ANCHORS = (
    ("stage01_ant_hill", "level01.sav"),
    ("training_entry", "phase3_pristine_training_gameplay_i5.sav"),
    ("training_completion", "training_all_stuff_collected_ending.sav"),
)
LIFECYCLE_ANCHOR = "level02.sav"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
MOVIE_EDIT_START = 8103
MOVIE_DIRECTION_FRAMES = 8
MOVIE_EDIT_END = MOVIE_EDIT_START + MOVIE_DIRECTION_FRAMES * len(SOURCE_ORDER)

SECONDARY_LEAD = {
    "role": "non-authoritative trigger lead only",
    "url": "https://pixar.fandom.com/wiki/A_Bug%27s_Life%3A_The_Video_Game",
    "retrieved": "2026-07-15",
    "wording_under_test":
        "press the directional buttons from the left to the right, in clockwise order",
    "authority_rule":
        "Only hash-verified pristine media and executable bytes establish the behavior.",
}

EXPECTED_WORDS = {
    "analog_path_current_action_sample": (0x80047F6C, 0x94632488),
    "analog_desired_heading_writer": (0x80048044, 0xAC226528),
    "dpad_path_current_action_sample": (0x80048094, 0x94632488),
    "dpad_direction_mask": (0x800480A8, 0x306300F0),
    "dpad_desired_heading_writer": (0x80048104, 0xAC226528),
    "dpad_heading_domain_mask": (0x80048118, 0x30420FFF),
    "controller_direction_mask": (0x8004911C, 0x306200F0),
    "stationary_heading_snap": (0x800491A4, 0xAE220020),
    "turn_difference_mask": (0x80049250, 0x30440FFF),
    "bounded_heading_writer": (0x80049298, 0xAE220020),
    "heading_domain_writer": (0x800492A8, 0xAE220020),
}

TRACE_FIELDS = {
    "timer": PLAYER_BASE + 0x7A,
    "state": PLAYER_BASE + 0x80,
    "aux": PLAYER_BASE + 0x84,
    "animation": PLAYER_BASE + 0x88,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _va_offset(address: int) -> int:
    return EXE_HEADER + address - EXE_BASE


def _word(exe: bytes, address: int) -> int:
    return struct.unpack_from("<I", exe, _va_offset(address))[0]


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    if exe is None:
        exe = EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine A07 word mismatch at 0x{address:08X}: "
                f"actual=0x{actual:08X} expected=0x{expected:08X}")
        words[name] = {"address": f"0x{address:08X}", "word": f"0x{actual:08X}"}

    locomotion = run_common.build_static_census(exe)
    xrefs_path = ROOT / "analysis/phase3_xrefs.json"
    xrefs = json.loads(xrefs_path.read_text())["entries"]["original.player_heading"]
    reader_names = sorted({row["function"] for row in xrefs["readers"]})
    return {
        "executable": locomotion["executable"],
        "regions": {
            "current_direction_helper": locomotion["regions"]["input_helper"],
            "heading_controller": locomotion["regions"]["horizontal_controller"],
        },
        "instruction_words": words,
        "law": {
            "direction_mask": DIRECTION_MASK,
            "cardinal_masks": CARDINAL_MASKS,
            "heading_domain": [0, HEADING_MASK],
            "default_max_turn_step": run_common.DEFAULT_TURN_STEP,
            "input_history_storage": None,
            "recognizer_shape":
                "The helper samples the current action word, table-maps its current "
                "direction nibble, and writes player+0x28; it carries no cross-tick "
                "direction history or private spin state.",
            "positive_behavior":
                "Successive current directions move desired heading and the ordinary "
                "controller converges player+0x20 through the 12-bit wrap.",
        },
        "heading_xrefs": {
            "artifact": "analysis/phase3_xrefs.json",
            "artifact_sha256": _sha256(xrefs_path),
            "address": xrefs["address"],
            "reader_count": xrefs["reader_count"],
            "reader_names": reader_names,
            "render_facing_reader": "actor_skinned_update" in reader_names,
        },
        "source_status": {
            "input_helper":
                "asm/hand_written/80047ebc_sub_80047ebc.s is the byte-matched build unit",
            "player_controller":
                "asm/hand_written/80048138_player_vertical_update.s is the byte-matched build unit",
            "semantic_c":
                "src_re/player_update_80048138.c is documentation-grade and is not execution authority",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    if law.get("direction_mask") != DIRECTION_MASK:
        gaps.append("direction mask differs from 0x00F0")
    if law.get("cardinal_masks") != CARDINAL_MASKS:
        gaps.append("cardinal direction mapping differs")
    if law.get("heading_domain") != [0, HEADING_MASK]:
        gaps.append("heading domain differs from 0..4095")
    if law.get("input_history_storage") is not None:
        gaps.append("current-direction helper unexpectedly claims history storage")
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive A07 instruction census is incomplete")
    xrefs = census.get("heading_xrefs") or {}
    if xrefs.get("reader_count", 0) < 20 or xrefs.get("render_facing_reader") is not True:
        gaps.append("heading consumer/render-facing boundary is incomplete")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _snapshot(client: Any) -> dict[str, Any]:
    snap = run_common._snapshot(client)
    fields = snap["fields"]
    return {
        "frame": snap["frame"], "cycle": snap["cycle"], "scene": snap["scene"],
        "pause_flag": snap["pause_flag"],
        "working_actions": snap["working_actions"],
        "player_block_sha256": snap["player_block_sha256"],
        "x": fields["x"], "y": fields["y"], "z": fields["z"],
        "heading": fields["heading"], "input_heading": fields["input_heading"],
        "forward_component": fields["forward_component"],
        "lateral_component": fields["lateral_component"],
        "timer": struct.unpack_from("<h", bytes.fromhex(client.call(
            "debugger.readMemory", {"address": "0x800A657A", "length": 2})["hex"]))[0],
        "state": fields["state"], "grounded": fields["grounded"],
        "aux": struct.unpack_from("<h", bytes.fromhex(client.call(
            "debugger.readMemory", {"address": "0x800A6584", "length": 2})["hex"]))[0],
        "animation": fields["animation"], "health": fields["health"],
        "lives": fields["lives"],
    }


def _load_anchor(client: Any, path: Path) -> dict[str, Any]:
    loaded = run_common._load_anchor(client, path)
    client.call("emulator.clearControllerState", {"port": 0})
    if SETTLE_FRAMES != run_common.SETTLE_FRAMES:
        client.call("emulator.advanceFrames", {
            "frames": SETTLE_FRAMES - run_common.SETTLE_FRAMES})
    return loaded


def _sample_frames(client: Any, count: int) -> list[dict[str, Any]]:
    rows = []
    for _ in range(count):
        client.call("emulator.advanceFrames", {"frames": 1})
        rows.append(_snapshot(client))
    return rows


def _signed_step(current: int, previous: int) -> int:
    return ((current - previous + 2048) & HEADING_MASK) - 2048


def _metrics(rows: list[dict[str, Any]], *, skip_first_block: bool = False) -> dict[str, Any]:
    headings = [row["heading"] for row in rows]
    input_headings = [row["input_heading"] for row in rows]
    start = BLOCK_FRAMES if skip_first_block else 1
    steps = [_signed_step(headings[index], headings[index - 1])
             for index in range(max(1, start), len(headings))]
    bounded = [step for step in steps if abs(step) <= run_common.DEFAULT_TURN_STEP]
    raw_pairs = list(zip(headings, headings[1:]))
    input_pairs = list(zip(input_headings, input_headings[1:]))
    return {
        "samples": len(rows),
        "heading_path": headings,
        "input_heading_path": input_headings,
        "heading_values": sorted(set(headings)),
        "input_heading_values": sorted(set(input_headings)),
        "heading_change_count": sum(a != b for a, b in raw_pairs),
        "heading_wrap_events": sum(abs(b - a) > 2048 for a, b in raw_pairs),
        "input_heading_wrap_events":
            sum(abs(b - a) > 2048 for a, b in input_pairs),
        "post_left_signed_turn": sum(bounded),
        "post_left_positive_steps": sum(step > 0 for step in bounded),
        "post_left_negative_steps": sum(step < 0 for step in bounded),
        "max_bounded_turn_step": max((abs(step) for step in bounded), default=0),
        "direction_masks": sorted({row["working_actions"] & DIRECTION_MASK for row in rows}),
        "states": sorted({row["state"] for row in rows}),
        "timers": sorted({row["timer"] for row in rows}),
        "aux_values": sorted({row["aux"] for row in rows}),
        "animations": sorted({row["animation"] for row in rows}),
    }


def _run_sequence(client: Any, order: tuple[str, ...]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, controller = [], []
    for button in order:
        set_result = client.call("emulator.setControllerState", {
            "port": 0, "buttons": {button: True}})
        controller.append({"button": button, "set": set_result})
        rows.extend(_sample_frames(client, DWELL_FRAMES))
        clear = client.call("emulator.clearControllerState", {"port": 0})
        controller[-1]["clear"] = clear
        rows.extend(_sample_frames(client, RELEASE_FRAMES))
    rows.extend(_sample_frames(client, POST_FRAMES))
    return rows, controller


def _run_branch(client: Any, path: Path,
                order: tuple[str, ...] | None) -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    before = _snapshot(client)
    if order is None:
        rows = _sample_frames(
            client, len(SOURCE_ORDER) * BLOCK_FRAMES + POST_FRAMES)
        controller: list[dict[str, Any]] = []
    else:
        rows, controller = _run_sequence(client, order)
    client.call("emulator.clearControllerState", {"port": 0})
    after = rows[-1]
    return {
        "load": loaded, "order": list(order or ()), "controller": controller,
        "before": before, "after": after,
        "metrics": _metrics(rows, skip_first_block=order is not None),
        "displacement": [after["x"] - before["x"], after["z"] - before["z"]],
    }


def _run_controls(client: Any) -> dict[str, Any]:
    anchors = {}
    for label, save in CONTROL_ANCHORS:
        path = ROOT / save
        neutral = _run_branch(client, path, None)
        source = _run_branch(client, path, SOURCE_ORDER)
        reverse = _run_branch(client, path, REVERSE_ORDER)
        anchors[label] = {
            "save": save, "neutral": neutral,
            "left_up_right_down": source,
            "left_down_right_up": reverse,
        }
        source_m, reverse_m = source["metrics"], reverse["metrics"]
        expected_masks = sorted([0, *CARDINAL_MASKS.values()])
        if source_m["direction_masks"] != expected_masks or \
                reverse_m["direction_masks"] != expected_masks or \
                source_m["heading_change_count"] < 8 or \
                reverse_m["heading_change_count"] < 8 or \
                (source_m["heading_wrap_events"] +
                 source_m["input_heading_wrap_events"]) < 1 or \
                (reverse_m["heading_wrap_events"] +
                 reverse_m["input_heading_wrap_events"]) < 1 or \
                source_m["post_left_signed_turn"] <= 0 or \
                reverse_m["post_left_signed_turn"] >= 0 or \
                source_m["max_bounded_turn_step"] > run_common.DEFAULT_TURN_STEP or \
                reverse_m["max_bounded_turn_step"] > run_common.DEFAULT_TURN_STEP or \
                any(m[key] != [0] for m in (source_m, reverse_m)
                    for key in ("states", "timers", "aux_values")):
            raise SystemExit(f"A07 exact control failed at {label}: {anchors[label]}")
    return {
        "summary": {
            "anchor_labels": list(anchors),
            "orders": [list(SOURCE_ORDER), list(REVERSE_ORDER)],
            "anchors_with_opposite_signed_turn": sorted(
                label for label, row in anchors.items()
                if row["left_up_right_down"]["metrics"]["post_left_signed_turn"] > 0
                and row["left_down_right_up"]["metrics"]["post_left_signed_turn"] < 0),
            "anchors_with_zero_special_fields": sorted(
                label for label, row in anchors.items()
                if all(branch["metrics"][key] == [0]
                       for branch in (row["left_up_right_down"], row["left_down_right_up"])
                       for key in ("states", "timers", "aux_values"))),
        },
        "anchors": anchors,
    }


def _run_breadth(client: Any,
                 anchors: list[tuple[str, str]]) -> dict[str, Any]:
    rows = {}
    for index, (label, save) in enumerate(anchors, 1):
        neutral = _run_branch(client, ROOT / save, None)
        source = _run_branch(client, ROOT / save, SOURCE_ORDER)
        rows[label] = {"save": save, "neutral": neutral, "source": source}
        print(f"[spin-breadth] {index:02d}/{len(anchors)} {label}: "
              f"heading_changes={source['metrics']['heading_change_count']}")
    responsive = sorted(
        label for label, row in rows.items()
        if row["source"]["metrics"]["heading_path"] !=
        row["neutral"]["metrics"]["heading_path"])
    disabled = sorted(set(rows) - set(responsive))
    zero_special = sorted(
        label for label, row in rows.items()
        if all(row["source"]["metrics"][key] == row["neutral"]["metrics"][key]
               for key in ("states", "timers", "aux_values")))
    summary = {
        "labels": list(rows), "anchors_compared": len(rows),
        "heading_responsive_labels": responsive,
        "heading_disabled_labels": disabled,
        "source_matches_neutral_special_field_labels": zero_special,
    }
    if len(rows) != 19 or len(responsive) != 19 or disabled or \
            len(zero_special) != 19:
        raise SystemExit(f"A07 gameplay breadth failed: {summary}")
    return {"summary": summary, "anchors": rows}


def _run_pause(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    paused_before = _snapshot(client)
    paused_rows, _ = _run_sequence(client, SOURCE_ORDER)
    paused_after = _snapshot(client)
    # The directions are pause-menu input and may move its selection, so use a
    # fresh copy of the same anchor for the resume/re-entry branch.  This keeps
    # the paused freeze causal without assuming which menu item stayed selected.
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    # Give the pause shell a non-Start raw state before requesting the fresh edge.
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"l1": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    resumed_before = _snapshot(client)
    resumed_rows, _ = _run_sequence(client, SOURCE_ORDER)
    resumed_after = _snapshot(client)
    result = {
        "paused_before": paused_before, "paused_after": paused_after,
        "paused_metrics": _metrics(paused_rows, skip_first_block=True),
        "resumed_before": resumed_before, "resumed_after": resumed_after,
        "resumed_metrics": _metrics(resumed_rows, skip_first_block=True),
        "player_block_frozen":
            paused_before["player_block_sha256"] == paused_after["player_block_sha256"],
    }
    if paused_before["pause_flag"] != 1 or paused_after["pause_flag"] != 1 or \
            not result["player_block_frozen"] or \
            result["paused_metrics"]["heading_change_count"] != 0 or \
            resumed_after["pause_flag"] != 0 or \
            result["resumed_metrics"]["heading_change_count"] < 4:
        raise SystemExit(f"A07 pause/resume failed: {result}")
    return result


def _checked_write(client: Any, method: str, address: int, value: int) -> dict[str, Any]:
    width = {"debugger.writeU16": 2, "debugger.writeU32": 4}[method]
    result = client.call(method, {
        "address": f"0x{address:08X}", "value": value & ((1 << (width * 8)) - 1)})
    if result.get("written") != width:
        raise SystemExit(f"A07 perturbation write failed: {method}: {result}")
    return result


def _run_respawn(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    before = _snapshot(client)
    actor_id, actor_x, actor_y, actor_z = struct.unpack(
        "<Iiii", bytes.fromhex(client.call("debugger.readMemory", {
            "address": f"0x{ACTOR_RECORD_BASE:08X}", "length": 16})["hex"]))
    writes = [_checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x94, 0)]
    for address, value in (
        (PLAYER_BASE + 0x00, actor_x), (PLAYER_BASE + 0x10, actor_x),
        (PLAYER_BASE + 0x04, actor_y), (PLAYER_BASE + 0x14, actor_y),
        (PLAYER_BASE + 0x08, actor_z), (PLAYER_BASE + 0x18, actor_z),
    ):
        writes.append(_checked_write(client, "debugger.writeU32", address, value))
    flow, respawn = [], None
    for _ in range(8):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = _snapshot(client)
        flow.append(row)
        if row["lives"] == before["lives"] - 1 and row["health"] == 4:
            respawn = row
            break
    reentry_rows = []
    if respawn is not None:
        reentry_rows, _ = _run_sequence(client, SOURCE_ORDER)
    client.call("emulator.clearControllerState", {"port": 0})
    result = {
        "anchor": LIFECYCLE_ANCHOR,
        "actor": {"id": actor_id, "x": actor_x, "y": actor_y, "z": actor_z},
        "writes": writes, "before": before, "flow": flow, "respawn": respawn,
        "reentry_metrics": _metrics(reentry_rows, skip_first_block=True)
            if reentry_rows else None,
    }
    if respawn is None or result["reentry_metrics"] is None or \
            respawn["scene"] != before["scene"] or \
            result["reentry_metrics"]["heading_change_count"] < 4 or \
            result["reentry_metrics"]["states"] != [0] or \
            result["reentry_metrics"]["timers"] != [0] or \
            result["reentry_metrics"]["aux_values"] != [0]:
        raise SystemExit(f"A07 native respawn/re-entry failed: {result}")
    return result


def _run_reload_reset(client: Any) -> dict[str, Any]:
    path = ROOT / "training_all_stuff_collected_ending.sav"
    _load_anchor(client, path)
    before = _snapshot(client)
    rows, _ = _run_sequence(client, SOURCE_ORDER)
    changed = _snapshot(client)
    _load_anchor(client, path)
    restored = _snapshot(client)
    result = {
        "anchor": path.name, "before": before,
        "sequence_metrics": _metrics(rows, skip_first_block=True),
        "changed": changed, "restored": restored,
        "heading_restored": restored["heading"] == before["heading"],
        "input_heading_restored": restored["input_heading"] == before["input_heading"],
    }
    if result["sequence_metrics"]["heading_change_count"] < 4 or \
            not result["heading_restored"] or not result["input_heading_restored"]:
        raise SystemExit(f"A07 reload reset failed: {result}")
    return result


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "new_value", "watch_id")}


def _checked_watch(client: Any, watch: dict[str, Any]) -> dict[str, Any]:
    watch_id = int(watch["watch_id"])
    page = client.call("accessLog.get", {
        "watch_id": watch_id, "offset": 0, "limit": 10000})
    events = list(page.get("events") or [])
    total = int(page.get("total", 0))
    while len(events) < total:
        nxt = client.call("accessLog.get", {
            "watch_id": watch_id, "offset": len(events),
            "limit": min(10000, total - len(events))})
        if int(nxt.get("total", -1)) != total or not nxt.get("events"):
            raise SystemExit(f"A07 access-log total drift/empty page: {nxt}")
        events.extend(nxt["events"])
    matching = [row for row in page.get("watches") or []
                if int(row.get("watch_id", -1)) == watch_id]
    saturated = any(int(row.get("hit_count", 0)) >= int(row.get("max_events", 0))
                    for row in matching)
    result = {
        "watch": watch, "total": total, "returned": len(events),
        "truncated": bool(page.get("truncated")),
        "watch_cap_saturated": saturated,
        "events": [_trim_event(row) for row in events],
    }
    if result["truncated"] or result["returned"] != total or saturated or \
            len(matching) != 1:
        raise SystemExit(f"A07 access log incomplete: {result}")
    return result


def _run_writer_trace(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / "training_all_stuff_collected_ending.sav")
    client.call("accessLog.clear", {})
    specifications = {
        "current_action_reads": {
            "address": f"0x{ACTION_WORD:08X}", "length": 2, "type": "read",
            "label": "current action read by direction helper", "max_events": 4096,
            "stop_on_hit": False,
            "filter": {"pc": {"min": "0x80047EBC", "max": "0x80048137"}}},
        "input_heading_writes": {
            "address": f"0x{PLAYER_BASE + 0x28:08X}", "length": 4, "type": "write",
            "label": "desired heading writes", "max_events": 4096,
            "stop_on_hit": False},
        "heading_writes": {
            "address": f"0x{PLAYER_BASE + 0x20:08X}", "length": 4, "type": "write",
            "label": "player heading writes", "max_events": 4096,
            "stop_on_hit": False},
        "action_fields": {
            "address": f"0x{PLAYER_BASE + 0x7A:08X}", "length": 0x10,
            "type": "write", "label": "timer/state/aux/animation writes",
            "max_events": 4096, "stop_on_hit": False},
    }
    watches = {name: client.call("accessLog.addWatch", spec)
               for name, spec in specifications.items()}
    rows, _ = _run_sequence(client, SOURCE_ORDER)
    logs = {name: _checked_watch(client, watch) for name, watch in watches.items()}
    client.call("accessLog.clear", {})
    pcs = {
        name: sorted({str(row.get("instruction_pc")).lower()
                      for row in log["events"]})
        for name, log in logs.items()
    }
    result = {
        "order": list(SOURCE_ORDER), "metrics": _metrics(rows, skip_first_block=True),
        "specifications": specifications, "logs": logs,
        "observed_instruction_pcs": pcs,
    }
    if "0x80048044" not in pcs["input_heading_writes"] or \
            not {"0x800491a4", "0x80049298"} <= set(pcs["heading_writes"]) or \
            any(log["truncated"] or log["watch_cap_saturated"] or
                log["returned"] != log["total"] for log in logs.values()):
        raise SystemExit(f"A07 writer attribution failed: {result}")
    return result


def _verify_base_movie() -> tuple[dict[str, Any], dict[str, Any]]:
    path = ROOT / BASE_MOVIE
    pin = (json.loads(FIXTURE_SET.read_text()).get("entries") or {}).get(BASE_MOVIE)
    if not pin or pin.get("media_class") != "pristine_serial" or \
            not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"A07 cold-boot movie lacks exact central pin: {pin}")
    movie = json.loads(path.read_text())
    if movie.get("format") != "DuckStationInputMovie" or movie.get("version") != 3 or \
            (movie.get("start_state") or {}).get("from_boot") is not True:
        raise SystemExit("A07 cold-boot anchor is not a v3 from-boot movie")
    for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
        pad = ((movie["frames"][index].get("ports") or {}).get("0") or {})
        if pad.get("up") is not True or any(pad.get(button) for button in (
                "left", "right", "down", "l1", "r1", "l2", "r2", "cross",
                "circle", "square", "triangle", "start", "select")):
            raise SystemExit(f"A07 cold-boot edit window changed at frame {index}")
    return movie, {"path": BASE_MOVIE, "sha256": pin["sha256"],
                   "size": pin["size"], "media_class": pin["media_class"]}


def _run_cold_boot(client: Any) -> dict[str, Any]:
    movie, pin = _verify_base_movie()
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass
    registry_ids: list[int] = []

    def edit_branch(movie_id: int, source: bool) -> list[dict[str, Any]]:
        responses = []
        for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
            pad = dict(movie["frames"][index]["ports"]["0"])
            for button in CARDINAL_MASKS:
                pad[button] = False
            if source:
                offset = (index - MOVIE_EDIT_START) // MOVIE_DIRECTION_FRAMES
                pad[SOURCE_ORDER[offset]] = True
            responses.append(client.call("movie.editFrame", {
                "movieId": movie_id, "frame": index, "input": {"0": pad}}))
        return responses

    def play_branch(movie_id: int) -> dict[str, Any]:
        activated = client.call("movie.activate", {"movieId": movie_id})
        started = client.call("movie.startPlayback", {"load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_START, "max_frames": 9000}, timeout=900)
        before = _snapshot(client)
        before_movie = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_END, "max_frames": 100}, timeout=900)
        after = _snapshot(client)
        after_movie = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})
        return {"activated": activated, "started": started, "before": before,
                "before_movie": before_movie, "after": after,
                "after_movie": after_movie}

    try:
        loaded = client.call("movie.load", {"path": str((ROOT / BASE_MOVIE).resolve())})
        stored = client.call("movie.store", {})
        registry_ids.append(stored["movieId"])
        neutral_branch = client.call("movie.branch", {
            "movieId": stored["movieId"], "fromFrame": len(movie["frames"])})
        source_branch = client.call("movie.branch", {
            "movieId": stored["movieId"], "fromFrame": len(movie["frames"])})
        registry_ids.extend([neutral_branch["movieId"], source_branch["movieId"]])
        neutral_edits = edit_branch(neutral_branch["movieId"], False)
        source_edits = edit_branch(source_branch["movieId"], True)
        neutral = play_branch(neutral_branch["movieId"])
        source = play_branch(source_branch["movieId"])
    finally:
        try:
            client.call("movie.stopPlayback", {})
        except Exception:
            pass
        for movie_id in reversed(registry_ids):
            try:
                client.call("movie.remove", {"movieId": movie_id})
            except Exception:
                pass
        try:
            client.call("movie.clear", {})
        except Exception:
            pass
    result = {
        "base_movie": pin, "loaded": loaded,
        "edit_recipe": {
            "order": list(SOURCE_ORDER), "start_frame": MOVIE_EDIT_START,
            "end_frame_exclusive": MOVIE_EDIT_END,
            "frames_per_direction": MOVIE_DIRECTION_FRAMES,
            "edited_frame_count": len(source_edits),
            "neutral_edit_count": len(neutral_edits),
        },
        "neutral": neutral, "source": source,
        "pre_edit_player_block_equal":
            neutral["before"]["player_block_sha256"] ==
            source["before"]["player_block_sha256"],
        "pre_edit_cycle_equal": neutral["before"]["cycle"] == source["before"]["cycle"],
        "post_edit_heading_differs":
            neutral["after"]["heading"] != source["after"]["heading"],
        "post_edit_position_differs":
            (neutral["after"]["x"], neutral["after"]["z"]) !=
            (source["after"]["x"], source["after"]["z"]),
    }
    statuses = (neutral["started"], neutral["before_movie"], neutral["after_movie"],
                source["started"], source["before_movie"], source["after_movie"])
    if any(row.get("reproducible") is not True or row.get("truncated") is not False
           for row in statuses) or not result["pre_edit_player_block_equal"] or \
            not result["pre_edit_cycle_equal"] or \
            not result["post_edit_heading_differs"] or \
            not result["post_edit_position_differs"] or \
            source["after"]["scene"] != 1 or \
            any(source["after"][key] != neutral["after"][key]
                for key in ("state", "timer", "aux")):
        raise SystemExit(f"A07 cold-boot causal control failed: {result}")
    return result


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    rows = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: rows[save] for save in saves}


def run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    gaps = static_census_gaps(static)
    if gaps:
        raise SystemExit(f"A07 static census failed: {gaps}")
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("first 19 strict-pristine anchors no longer cover gameplay")
    saves = list(dict.fromkeys(
        [save for _label, save in anchors] +
        [save for _label, save in CONTROL_ANCHORS] + [LIFECYCLE_ANCHOR]))
    selected_rows = [row for row in selection["accepted"] if row["save"] in saves]
    if {row["save"] for row in selected_rows} != set(saves):
        raise SystemExit("A07 fixture selection does not cover every loaded save")

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required_methods = {
        "debugger.capabilities", "debugger.readMemory", "debugger.readStruct",
        "debugger.writeU16", "debugger.writeU32", "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "accessLog.addWatch", "accessLog.get",
        "accessLog.clear", "movie.load", "movie.store", "movie.branch",
        "movie.editFrame", "movie.activate", "movie.startPlayback",
        "movie.advanceToFrame", "movie.stopPlayback", "movie.status",
        "movie.remove", "movie.clear",
    }
    missing = sorted(name for name in required_methods
                     if not _method_present(capabilities, name))
    if missing:
        raise SystemExit(f"running debugger lacks A07 methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    controls = _run_controls(client)
    breadth = _run_breadth(client, anchors)
    trace = _run_writer_trace(client)
    pause = _run_pause(client)
    reload_reset = _run_reload_reset(client)
    respawn = _run_respawn(client)
    cold_boot = _run_cold_boot(client)

    client.call("emulator.clearControllerState", {"port": 0})
    client.call("accessLog.clear", {})
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass
    selection_current = {
        **selection, "accepted": selected_rows, "rejected": [],
        "anchors_requested": len(selected_rows),
        "anchors_accepted": len(selected_rows), "anchors_rejected": 0,
    }
    run_provenance = finish_run(
        args, generator="tools/phase4_spin_heading.py",
        anchor={
            "type": "cold-boot edited-input control plus strict-pristine heading/lifecycle sweep",
            "saves": saves,
            "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections,
            "selection": selection_current,
            "cold_boot_movie": cold_boot["base_movie"],
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "sequence": {"order": list(SOURCE_ORDER), "dwell_frames": DWELL_FRAMES,
                         "release_frames": RELEASE_FRAMES,
                         "post_frames": POST_FRAMES},
            "breadth_anchors": len(anchors),
            "cold_boot_edit": cold_boot["edit_recipe"],
        },
    )
    document = {
        "_comment":
            "Phase-4 A07 positive directional-heading campaign. The secondary source "
            "only supplied the left-start order; every conclusion is recomputed from "
            "hash-verified pristine bytes and live media. Regenerate live with "
            "tools/phase4_spin_heading.py and explicit isolated-instance arguments.",
        "generated": date.today().isoformat(),
        "secondary_lead": SECONDARY_LEAD,
        "static_census": static,
        "live": {
            "controls": controls, "breadth": breadth, "writer_trace": trace,
            "pause_resume": pause, "reload_reset": reload_reset,
            "death_respawn": respawn, "cold_boot": cold_boot,
        },
        "run_provenance": run_provenance,
        "fixture_sha256": _fixture_pins(selection, saves),
        "classification": "positive_directional_heading_behavior",
        "scope_boundary": {
            "established":
                "Left-start cardinal sweeps rotate the current desired/player heading "
                "through the ordinary controller in opposite directions and are "
                "visible through the existing heading consumers.",
            "not_claimed":
                "No distinct spin attack, cheat effect, cross-tick recognizer, private "
                "mode, damage response, or source-reported pause exploit is claimed.",
            "phase3_negative":
                "The earlier bounded negative remains valid for distinct state/unknown "
                "writer hypotheses; it is superseded only as the interpretation of A07.",
        },
    }
    write_live_evidence(OUTPUT, document)
    print("[spin-heading] exact controls=3, heading-responsive breadth=19, "
          "special-field matches=19, owned PID stopped")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
