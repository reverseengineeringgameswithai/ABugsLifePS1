#!/usr/bin/env python3
"""Regenerate the Phase-4 A18 pause-shell campaign from pristine evidence."""
from __future__ import annotations

import argparse
import base64
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
        add_required_live_args, finish_run, inspect_state_before_load,
        select_pristine_save_anchors, verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        select_pristine_save_anchors, verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_pause.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

ACTION_WORD = 0x80082488
PAUSE_FLAG = 0x8008224E
TRANSITION_WORD = 0x800823A0
FADE_WORD = 0x80082470
SCENE_WORD = 0x80082504
PLAYER_BASE = 0x800A6500
ACTOR_POOL = (0x8009FD80, 64 * 0x84)
CONTACT_POOL = (0x800B0D18, 64 * 0x38)
PLANT_POOL = (0x80090BF0, 20 * 0x30)
CAMERA_BLOCK = (0x80095358, 0x60)

CONTROL_SAVE = "level02.sav"
AUDIO_SAVE = "level_14.sav"
FRONTEND_FRAME_SHA256 = (
    "c700c779e712ea3e371fc16b3b262ca0befae8d374f38294ce8d9ed9a04f2ab0")

GAMEPLAY_STATE_MACHINE = (0x8004ECD4, 0x8004F478)
GAMEPLAY_FRAME_RENDER = (0x8004F480, 0x8004FA40)
EXPECTED_REGIONS = {
    "gameplay_state_machine": (
        GAMEPLAY_STATE_MACHINE,
        "83d8e37d6b8bf8cd13e65ec6be99837d6e2975e9c1926d6ce9a812133bedc1f0"),
    "gameplay_frame_render": (
        GAMEPLAY_FRAME_RENDER,
        "c5b19582683528ba2505bbc3152069421a457c8a688fd340d59e372417ef92f7"),
}
EXPECTED_WORDS = {
    "pause_start_mask": (0x8004F314, 0x30420008),
    "pause_entry_flag_writer": (0x8004F3AC, 0xA422224E),
    "pause_scene_render_call": (0x8004F718, 0x0C00893B),
    "pause_confirm_cross_mask": (0x8004F7E8, 0x30624000),
    "pause_confirm_start_mask": (0x8004F808, 0x30620008),
    "pause_resume_flag_writer": (0x8004F858, 0xA420224E),
    "pause_left_mask": (0x8004F89C, 0x30420080),
    "pause_right_mask": (0x8004F8E4, 0x30420020),
    "pause_exit_cross_mask": (0x8004F934, 0x30624000),
    "pause_exit_selection_branch": (0x8004F958, 0x10400031),
    "pause_exit_flag_writer": (0x8004F9C0, 0xA420224E),
    "pause_exit_transition_writer": (0x8004F9E4, 0xA42223A0),
    "pause_exit_fade_writer": (0x8004F9FC, 0xA4222470),
}
ASM_SOURCES = {
    "gameplay_state_machine": (
        "asm/hand_written/8004ecd4_gameplay_state_machine.s",
        "57d38485c2a7821f02b07e794be6960b2b206d3840ac1991d8198fd6d354561d"),
    "gameplay_frame_render": (
        "asm/hand_written/8004f480_gameplay_frame_render.s",
        "3a6aefa628dad0c555529f822522ed31b7ad644b4f2a1bfcb0b94799219154b3"),
}
EXECUTION_WATCHES = {
    "frame_present": 0x80039A70,
    "draw_otag": 0x80062BFC,
    "dma_kick": 0x80064618,
    "scene_render_driver": 0x800224EC,
    "hud_animation_update": 0x80052574,
    "player_update": 0x80048138,
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


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
                f"pristine pause word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, (bounds, expected_sha256) in EXPECTED_REGIONS.items():
        data = exe[_va_offset(bounds[0]):_va_offset(bounds[1])]
        actual = _sha256_bytes(data)
        if actual != expected_sha256:
            raise SystemExit(
                f"pristine pause region mismatch for {name}: {actual}")
        regions[name] = {
            "start": f"0x{bounds[0]:08X}",
            "end_exclusive": f"0x{bounds[1]:08X}",
            "size": len(data), "sha256": actual,
        }
    sources = {}
    for name, (relative, expected) in ASM_SOURCES.items():
        path = ROOT / relative
        actual = _sha256(path)
        if actual != expected:
            raise SystemExit(f"matching assembly changed for {name}: {actual}")
        sources[name] = {"path": relative, "sha256": actual,
                         "status": "byte-matched handwritten assembly"}
    return {
        "executable": {"path": f"REBUILD/files/{EXE_REL}",
                       "sha256": _sha256_bytes(exe)},
        "instruction_words": words, "regions": regions,
        "matching_sources": sources,
        "law": {
            "decoded_start": f"0x{ACTION_WORD:08X}:u16 bit 0x0008",
            "pause_flag": f"0x{PAUSE_FLAG:08X}:u16 domain 0/1",
            "entry_writer": "0x8004F3AC sh v0,0x224e(at)",
            "ordinary_resume_writer": "0x8004F858 sh zero,0x224e(at)",
            "exit_writers": [
                "0x8004F9C0 pause=0", "0x8004F9E4 transition=5",
                "0x8004F9FC fade low half=23"],
            "menu": {
                "main": ["continue", "exit level"],
                "confirmation": ["yes", "no"],
                "confirmation_default": "no",
            },
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    gaps = []
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("pause instruction census is incomplete")
    if len(census.get("regions") or {}) != 2:
        gaps.append("pause owner regions are incomplete")
    if (census.get("law") or {}).get("menu", {}).get(
            "confirmation_default") != "no":
        gaps.append("exit confirmation default is not bound")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _read_memory(client: Any, address: int, length: int) -> bytes:
    result = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(result["hex"])


def _read_int(client: Any, address: int, length: int,
              *, signed: bool = False) -> int:
    return int.from_bytes(_read_memory(client, address, length), "little",
                          signed=signed)


def _frame(client: Any) -> dict[str, Any]:
    row = client.call("gpu.frameSnapshot", {
        "buffer": "displayed", "format": "raw16"})
    encoded = next((row.get(key) for key in ("base64", "data", "image")
                    if isinstance(row.get(key), str)), None)
    if encoded is None:
        raise SystemExit(f"frame snapshot returned no payload: {row.keys()}")
    data = base64.b64decode(encoded)
    return {"sha256": _sha256_bytes(data), "byte_length": len(data),
            "width": row.get("width"), "height": row.get("height"),
            "x": row.get("x"), "y": row.get("y"),
            "format": row.get("format")}


def _snapshot(client: Any) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    player = _read_memory(client, PLAYER_BASE, 0xB0)
    fields = {
        "x": struct.unpack_from("<i", player, 0x00)[0],
        "y": struct.unpack_from("<i", player, 0x04)[0],
        "z": struct.unpack_from("<i", player, 0x08)[0],
        "velocity_x": struct.unpack_from("<i", player, 0x10)[0],
        "velocity_y": struct.unpack_from("<i", player, 0x14)[0],
        "velocity_z": struct.unpack_from("<i", player, 0x18)[0],
        "heading": struct.unpack_from("<I", player, 0x20)[0],
        "desired_heading": struct.unpack_from("<I", player, 0x28)[0],
        "state": struct.unpack_from("<h", player, 0x80)[0],
        "grounded": struct.unpack_from("<h", player, 0x82)[0],
        "animation": struct.unpack_from("<h", player, 0x84)[0],
        "health": struct.unpack_from("<h", player, 0x94)[0],
        "lives": player[0xA0],
    }
    blocks = {
        "player": _sha256_bytes(player),
        "actors": _sha256_bytes(_read_memory(client, *ACTOR_POOL)),
        "contacts": _sha256_bytes(_read_memory(client, *CONTACT_POOL)),
        "plants": _sha256_bytes(_read_memory(client, *PLANT_POOL)),
        "camera": _sha256_bytes(_read_memory(client, *CAMERA_BLOCK)),
    }
    return {
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"), "pause_flag": _read_int(client, PAUSE_FLAG, 2),
        "transition": _read_int(client, TRANSITION_WORD, 4),
        "fade": _read_int(client, FADE_WORD, 4),
        "scene": _read_int(client, SCENE_WORD, 4),
        "player_fields": fields, "block_sha256": blocks,
        "framebuffer": _frame(client),
    }


def _load_anchor(client: Any, path: Path, *, settle: int = 3) -> dict[str, Any]:
    client.call("emulator.clearControllerState", {"port": 0})
    loaded = client.call("emulator.loadState", {
        "path": str(path.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})
    if loaded.get("loaded") is not True:
        raise SystemExit(f"state load failed: {path}: {loaded}")
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": settle})
    return loaded


def _buttons(client: Any, buttons: dict[str, bool]) -> None:
    client.call("emulator.clearControllerState", {"port": 0})
    if buttons:
        client.call("emulator.setControllerState", {
            "port": 0, "buttons": buttons})


def _press(client: Any, button: str, *, hold: int = 3, wait: int = 6) -> None:
    _buttons(client, {button: True})
    client.call("emulator.advanceFrames", {"frames": hold})
    _buttons(client, {})
    if wait:
        client.call("emulator.advanceFrames", {"frames": wait})


def _run_breadth(client: Any,
                 anchors: list[tuple[str, str]]) -> dict[str, Any]:
    rows = {}
    for index, (label, save) in enumerate(anchors, 1):
        _load_anchor(client, ROOT / save)
        before = _snapshot(client)
        _press(client, "start", wait=3)
        paused = _snapshot(client)
        _press(client, "start", wait=3)
        resumed = _snapshot(client)
        row = {"save": save, "before": before, "paused": paused,
               "resumed": resumed}
        if before["scene"] != paused["scene"] or \
                paused["pause_flag"] != 1 or resumed["pause_flag"] != 0 or \
                before["scene"] != resumed["scene"]:
            raise SystemExit(f"pause breadth failed for {label}: {row}")
        rows[label] = row
        print(f"[pause-breadth] {index:02d}/{len(anchors)} {label}")
    return {"summary": {"anchors_compared": len(rows),
                        "labels": list(rows),
                        "pause_entry_count": sum(
                            row["paused"]["pause_flag"] == 1
                            for row in rows.values()),
                        "resume_count": sum(
                            row["resumed"]["pause_flag"] == 0
                            for row in rows.values())},
            "anchors": rows}


def _execution_trace(client: Any, frames: int) -> dict[str, Any]:
    client.call("execTrace.clear", {})
    watches = {}
    for label, pc in EXECUTION_WATCHES.items():
        watches[label] = client.call("execTrace.addWatch", {
            "pc": f"0x{pc:08X}", "capture": ["ra"],
            "label": label, "max_events": 256})
    run = client.call("execTrace.run", {"frames": frames})
    pages = {label: client.call("execTrace.get", {
        "watch_id": watch["watch_id"], "offset": 0, "limit": 256})
        for label, watch in watches.items()}
    client.call("execTrace.clear", {})
    result = {"frames": frames, "run": run, "watches": watches,
              "by_label": pages,
              "hit_counts": {label: len(page.get("events") or [])
                             for label, page in pages.items()}}
    if run.get("truncated") or any(page.get("truncated") for page in pages.values()):
        raise SystemExit(f"paused execution trace truncated: {result}")
    return result


def _run_ownership(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_SAVE)
    active_before = _snapshot(client)
    _buttons(client, {"up": True})
    client.call("emulator.advanceFrames", {"frames": 60})
    _buttons(client, {})
    active_after = _snapshot(client)

    _load_anchor(client, ROOT / CONTROL_SAVE)
    _press(client, "start", wait=3)
    paused_before = _snapshot(client)
    _buttons(client, {"up": True})
    trace = _execution_trace(client, 60)
    _buttons(client, {})
    paused_after = _snapshot(client)
    _press(client, "start", wait=3)
    resumed_before = _snapshot(client)
    _buttons(client, {"up": True})
    client.call("emulator.advanceFrames", {"frames": 60})
    _buttons(client, {})
    resumed_after = _snapshot(client)

    owners = ("actors", "contacts", "plants", "camera")
    result = {
        "active": {"before": active_before, "after": active_after},
        "paused": {"before": paused_before, "after": paused_after},
        "resumed": {"before": resumed_before, "after": resumed_after},
        "execution_trace": trace,
        "summary": {
            "active_changed": {key: active_before["block_sha256"][key] !=
                               active_after["block_sha256"][key]
                               for key in owners},
            "paused_frozen": {key: paused_before["block_sha256"][key] ==
                              paused_after["block_sha256"][key]
                              for key in owners},
            "paused_player_fields_frozen":
                paused_before["player_fields"] == paused_after["player_fields"],
            "paused_framebuffer_changed":
                paused_before["framebuffer"]["sha256"] !=
                paused_after["framebuffer"]["sha256"],
            "resumed_changed": {key: resumed_before["block_sha256"][key] !=
                                resumed_after["block_sha256"][key]
                                for key in owners},
        },
    }
    hits = trace["hit_counts"]
    summary = result["summary"]
    if paused_before["pause_flag"] != 1 or paused_after["pause_flag"] != 1 or \
            resumed_after["pause_flag"] != 0 or \
            not all(summary["paused_frozen"].values()) or \
            not summary["paused_player_fields_frozen"] or \
            not summary["paused_framebuffer_changed"] or \
            hits["frame_present"] == 0 or hits["draw_otag"] == 0 or \
            hits["dma_kick"] == 0 or hits["scene_render_driver"] == 0 or \
            hits["hud_animation_update"] != 0 or hits["player_update"] != 0 or \
            not summary["active_changed"]["actors"] or \
            not summary["active_changed"]["contacts"] or \
            not summary["active_changed"]["camera"] or \
            not summary["resumed_changed"]["actors"] or \
            not summary["resumed_changed"]["contacts"] or \
            not summary["resumed_changed"]["camera"]:
        raise SystemExit(f"pause ownership failed: {result}")
    return result


def _spu_snapshot(client: Any) -> dict[str, Any]:
    row = client.call("spu.status", {})
    voices = [{key: voice.get(key) for key in (
        "index", "on", "phase", "adsr_volume", "current_address",
        "start_address", "repeat_address", "pitch", "loop_repeat",
        "loop_end", "has_samples")}
        for voice in row.get("voices") or []]
    counts = {}
    for voice in voices:
        phase = str(voice.get("phase") or "unknown")
        counts[phase] = counts.get(phase, 0) + 1
    return {"control": row.get("control"), "status": row.get("status"),
            "endx": row.get("endx"), "phase_counts": counts,
            "active_voice_indices": [voice["index"] for voice in voices
                                     if voice.get("on")],
            "voices": voices}


def _run_audio(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / AUDIO_SAVE)
    client.call("emulator.advanceFrames", {"frames": 3})
    active = _spu_snapshot(client)
    _press(client, "start", wait=0)
    client.call("emulator.advanceFrames", {"frames": 60})
    paused = _spu_snapshot(client)
    _press(client, "start", wait=0)
    client.call("emulator.advanceFrames", {"frames": 60})
    resumed = _spu_snapshot(client)
    result = {"save": AUDIO_SAVE, "active": active, "paused": paused,
              "resumed": resumed,
              "summary": {
                  "active_sustain": active["phase_counts"].get("sustain", 0),
                  "paused_sustain": paused["phase_counts"].get("sustain", 0),
                  "paused_release": paused["phase_counts"].get("release", 0),
                  "resumed_sustain": resumed["phase_counts"].get("sustain", 0),
                  "spu_control_stable": len({active["control"], paused["control"],
                                             resumed["control"]}) == 1,
              }}
    summary = result["summary"]
    if summary["active_sustain"] < 1 or summary["paused_sustain"] != 0 or \
            summary["paused_release"] < 1 or summary["resumed_sustain"] < 1 or \
            not summary["spu_control_stable"]:
        raise SystemExit(f"pause audio ownership failed: {result}")
    return result


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "old_value", "new_value", "watch_id")}


def _open_exit_confirmation(client: Any) -> None:
    _press(client, "start", wait=9)
    _press(client, "down", wait=6)
    _press(client, "cross", wait=6)


def _run_exit(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_SAVE)
    _open_exit_confirmation(client)
    negative_before = _snapshot(client)
    _press(client, "cross", wait=6)
    negative_after = _snapshot(client)
    if negative_before["pause_flag"] != 1 or \
            negative_after["pause_flag"] != 1 or \
            negative_after["transition"] != 0:
        raise SystemExit(f"default No exit control failed: {negative_after}")

    _load_anchor(client, ROOT / CONTROL_SAVE)
    _open_exit_confirmation(client)
    _press(client, "left", wait=6)
    positive_before = _snapshot(client)
    client.call("accessLog.clear", {})
    specifications = [
        {"address": f"0x{PAUSE_FLAG:08X}", "length": 2, "type": "write",
         "label": "pause_exit_flag", "max_events": 16, "stop_on_hit": False},
        {"address": f"0x{TRANSITION_WORD:08X}", "length": 4, "type": "write",
         "label": "pause_exit_transition", "max_events": 16,
         "stop_on_hit": False},
        {"address": f"0x{FADE_WORD:08X}", "length": 4, "type": "write",
         "label": "pause_exit_fade", "max_events": 16, "stop_on_hit": False},
    ]
    watches = [client.call("accessLog.addWatch", row) for row in specifications]
    _buttons(client, {"cross": True})
    run = client.call("accessLog.run", {"frames": 6})
    _buttons(client, {})
    page = client.call("accessLog.get", {"offset": 0, "limit": 128})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 16}) for watch in watches]
    client.call("accessLog.clear", {})
    committed = _snapshot(client)
    events = [_trim_event(row) for row in page.get("events") or []]
    pcs = {str(row.get("instruction_pc") or row.get("pc")).lower()
           for row in events}
    fade_writes = [row for row in events
                   if str(row.get("instruction_pc") or row.get("pc")).lower()
                   == "0x8004f9fc"]
    for _ in range(4):
        client.call("emulator.advanceFrames", {"frames": 600}, timeout=900)
    frontend = _snapshot(client)
    result = {
        "negative_default_no": {"before": negative_before,
                                "after": negative_after},
        "positive_yes": {"before": positive_before, "committed": committed,
                         "specifications": specifications, "watches": watches,
                         "run": run, "events": events, "summaries": summaries,
                         "observed_instruction_pcs": sorted(pcs),
                         "frontend": frontend},
        "summary": {
            "negative_retained_pause": negative_after["pause_flag"] == 1,
            "negative_transition": negative_after["transition"],
            "positive_pause_flag": committed["pause_flag"],
            "positive_transition": committed["transition"],
            "positive_fade_write_low_half": (
                int(fade_writes[-1].get("new_value", -1)) & 0xFFFF
                if fade_writes else None),
            "positive_fade_snapshot_low_half": committed["fade"] & 0xFFFF,
            "frontend_scene": frontend["scene"],
            "frontend_frame_sha256": frontend["framebuffer"]["sha256"],
        }}
    if run.get("truncated") or page.get("truncated") or \
            any(row.get("truncated") for row in summaries) or \
            not {"0x8004f9c0", "0x8004f9e4", "0x8004f9fc"} <= pcs or \
            committed["pause_flag"] != 0 or committed["transition"] != 5 or \
            not fade_writes or \
            int(fade_writes[-1].get("new_value", -1)) & 0xFFFF != 23 or \
            frontend["scene"] != 0 or \
            frontend["framebuffer"]["sha256"] != FRONTEND_FRAME_SHA256:
        raise SystemExit(f"positive pause exit failed: {result}")
    return result


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def evidence_gaps(doc: dict[str, Any]) -> list[str]:
    gaps = static_census_gaps(doc.get("static_census") or {})
    breadth = doc.get("live", {}).get("breadth", {}).get("summary", {})
    if (breadth.get("anchors_compared"), breadth.get("pause_entry_count"),
            breadth.get("resume_count")) != (19, 19, 19):
        gaps.append("19-anchor pause breadth is incomplete")
    ownership = doc.get("live", {}).get("ownership", {})
    summary = ownership.get("summary") or {}
    hits = (ownership.get("execution_trace") or {}).get("hit_counts") or {}
    if not all((summary.get("paused_frozen") or {}).values()) or \
            summary.get("paused_player_fields_frozen") is not True or \
            summary.get("paused_framebuffer_changed") is not True or \
            any(hits.get(key, 0) == 0 for key in (
                "frame_present", "draw_otag", "dma_kick", "scene_render_driver")) or \
            hits.get("hud_animation_update") != 0 or hits.get("player_update") != 0:
        gaps.append("pause ownership or presentation evidence is incomplete")
    audio = doc.get("live", {}).get("audio", {}).get("summary", {})
    if audio.get("active_sustain", 0) < 1 or audio.get("paused_sustain") != 0 or \
            audio.get("paused_release", 0) < 1 or \
            audio.get("resumed_sustain", 0) < 1:
        gaps.append("pause audio lifecycle is incomplete")
    exit_summary = doc.get("live", {}).get("exit", {}).get("summary", {})
    if (exit_summary.get("negative_retained_pause"),
            exit_summary.get("negative_transition"),
            exit_summary.get("positive_pause_flag"),
            exit_summary.get("positive_transition"),
            exit_summary.get("positive_fade_write_low_half"),
            exit_summary.get("frontend_scene"),
            exit_summary.get("frontend_frame_sha256")) != (
                True, 0, 0, 5, 23, 0, FRONTEND_FRAME_SHA256):
        gaps.append("pause exit lifecycle is incomplete")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    if static_census_gaps(static):
        raise SystemExit(f"static pause census failed: {static_census_gaps(static)}")
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("first 19 strict-pristine anchors no longer cover gameplay")
    saves = [save for _label, save in anchors]

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required_methods = {
        "debugger.capabilities", "debugger.readMemory", "debugger.status",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "execTrace.addWatch", "execTrace.run",
        "execTrace.get", "execTrace.clear", "accessLog.addWatch",
        "accessLog.run", "accessLog.get", "accessLog.summary",
        "accessLog.clear", "gpu.frameSnapshot", "spu.status",
    }
    missing = sorted(name for name in required_methods
                     if not _method_present(capabilities, name))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    breadth = _run_breadth(client, anchors)
    ownership = _run_ownership(client)
    audio = _run_audio(client)
    exit_flow = _run_exit(client)
    _buttons(client, {})
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})

    run_provenance = finish_run(
        args, generator="tools/phase4_pause.py",
        anchor={
            "type": "strict-pristine gameplay pause breadth, ownership, audio and exit",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections,
            "selection": {**selection, "accepted": selection["accepted"][:19],
                          "rejected": [], "anchors_requested": 19,
                          "anchors_accepted": 19, "anchors_rejected": 0},
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": 3, "button_hold_frames": 3,
            "ownership_hold_frames": 60, "audio_hold_frames": 60,
            "frontend_settle_frames": 2400,
        })
    document = {
        "_comment": (
            "Phase-4 A18 pristine pause-shell evidence. Retail code binds the "
            "entry/resume/menu/exit owners; live evidence supplies 19 gameplay "
            "contexts, frozen gameplay versus continuing presentation, SPU "
            "release/restart, negative No and positive Yes exit paths."),
        "generated": date.today().isoformat(), "static_census": static,
        "live": {"breadth": breadth, "ownership": ownership,
                 "audio": audio, "exit": exit_flow},
        "run_provenance": run_provenance,
    }
    if evidence_gaps(document):
        raise SystemExit(f"pause evidence incomplete: {evidence_gaps(document)}")
    write_live_evidence(OUTPUT, document)
    print(f"[pause] retained A18 campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_pause.py",
                       anchor={"type": "aborted before retained evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
