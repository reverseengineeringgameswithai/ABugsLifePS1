#!/usr/bin/env python3
"""Reproduce the live Phase-4 C13 harvester disengage and bee controls.

This is the deliberately small live complement to phase4_c13_harvester.py.
The capsule-backed tool owns equip and grain attraction.  This tool starts from
the same hash-pinned pristine movie, creates a transient end-of-movie anchor,
and runs three matched continuations:

* Cross clears the equipped state and harvester power bit.
* Remaining equipped changes the LEVEL01 bee's HP 4 -> 998 and retires it.
* Disengaging before that contact leaves the same bee alive with HP 4.

The tool never patches RAM or media.  Its transient save remains under /tmp.
The caller must launch and stop the named isolated DuckStation instance.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any

try:
    from live_session_provenance import (
        add_required_live_args,
        inspect_state_before_load,
        verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:
    from tools.live_session_provenance import (
        add_required_live_args,
        inspect_state_before_load,
        verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
DUCK = Path.home() / "duckstation"
CLIENT_DIR = DUCK / "scripts" / "debugger-client"
sys.path.insert(0, str(CLIENT_DIR))

MOVIE = ROOT / "movies" / "Phase4" / "c13_GRAIN_HARVESTER.movie.json"
START_STATE = ROOT / "movies" / "Phase4" / "c13_GRAIN_HARVESTER.movie.sav"
ANNOTATIONS = ROOT / "movies" / "Phase4" / "c13_GRAIN_HARVESTER.annotations.yaml"
OUTPUT = ROOT / "analysis" / "phase4_c13_harvester_live.json"

HARVESTER_STATE = 0x800A657E
POWER_FLAGS = 0x800A6590
HARVESTER_BIT = 0x80
LIVE_TABLE = 0x80090748
LIVE_TABLE_SLOTS = 64
LEVEL01_BEE_ID = 13
ACTOR_HP = 0x6E
ACTOR_FLAGS = 0x5C


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def connect(port: int, token: str):
    from duckstation_debug_client import DebuggerClient

    client = DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(300)
    return client


class Rig:
    def __init__(self, client):
        self.client = client

    def call(self, method: str, params: dict[str, Any] | None = None):
        return self.client.call(method, params or {})

    def memory(self, address: int, length: int) -> bytes:
        row = self.call(
            "debugger.readMemory",
            {"address": f"0x{address:08X}", "length": length},
        )
        return bytes.fromhex(row["hex"])

    def u16(self, address: int) -> int:
        return struct.unpack("<H", self.memory(address, 2))[0]

    def s16(self, address: int) -> int:
        return struct.unpack("<h", self.memory(address, 2))[0]

    def u32(self, address: int) -> int:
        return struct.unpack("<I", self.memory(address, 4))[0]

    def clear_runtime_controls(self) -> None:
        self.call("movie.clear", {})
        self.call("emulator.clearControllerState", {"port": 0})
        self.call("accessLog.clear", {})
        self.call("provenanceLog.stop", {})
        self.call("provenanceLog.clear", {})

    def advance(self, frames: int) -> None:
        remaining = frames
        while remaining:
            step = min(remaining, 600)
            self.call("emulator.advanceFrames", {"frames": step})
            remaining -= step

    def load(self, path: Path) -> dict[str, Any]:
        row = self.call(
            "emulator.loadState",
            {"path": str(path.resolve()), "pause_after_load": True},
        )
        if row.get("loaded") is not True or row.get("game_serial") != "SCUS-94288":
            raise RuntimeError(f"state load failed or wrong media: {row}")
        return row


def actor_snapshot(rig: Rig, address: int) -> dict[str, Any]:
    return {
        "record": f"0x{address:08X}",
        "id": rig.u32(address),
        "flags_0x5c": rig.u16(address + ACTOR_FLAGS),
        "hp_0x6e": rig.s16(address + ACTOR_HP),
    }


def live_pointers(rig: Rig) -> list[int]:
    raw = rig.memory(LIVE_TABLE, LIVE_TABLE_SLOTS * 4)
    pointers = list(struct.unpack(f"<{LIVE_TABLE_SLOTS}I", raw))
    return [pointer for pointer in pointers if pointer]


def find_actor(rig: Rig, actor_id: int) -> int:
    matches = [
        pointer for pointer in live_pointers(rig)
        if 0x80000000 <= pointer < 0x80200000 and rig.u32(pointer) == actor_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one live actor id {actor_id}, got {matches}")
    return matches[0]


def equip_snapshot(rig: Rig) -> dict[str, Any]:
    flags = rig.u16(POWER_FLAGS)
    return {
        "harvester_state_s16": rig.s16(HARVESTER_STATE),
        "power_flags_u16": flags,
        "harvester_bit_0x80": bool(flags & HARVESTER_BIT),
    }


def advance_until_change(
    rig: Rig, *, address: int, value_type: str, max_frames: int
) -> dict[str, Any]:
    return rig.call(
        "emulator.advanceUntil",
        {
            "condition": {
                "kind": "memory",
                "address": f"0x{address:08X}",
                "type": value_type,
                "op": "changed",
            },
            "max_frames": max_frames,
            "observe": False,
        },
    )


def replay_to_end(rig: Rig, transient: Path) -> dict[str, Any]:
    loaded = rig.call("movie.load", {"path": str(MOVIE.resolve())})
    if loaded.get("reproducible") is not True or loaded.get("game_serial") != "SCUS-94288":
        raise RuntimeError(f"movie load failed provenance guard: {loaded}")
    playing = rig.call(
        "movie.startPlayback",
        {"start_frame": 0, "load_start_state": True},
    )
    if playing.get("playing") is not True:
        raise RuntimeError(f"movie playback did not start: {playing}")
    advanced = rig.call("movie.advanceToFrame", {"frame": 617, "max_frames": 700})
    if advanced.get("frames_advanced") != 617:
        raise RuntimeError(f"movie did not reach its exact end: {advanced}")
    equipped = equip_snapshot(rig)
    if equipped["harvester_state_s16"] != 1 or not equipped["harvester_bit_0x80"]:
        raise RuntimeError(f"movie end is not equipped: {equipped}")
    saved = rig.call("emulator.saveState", {"path": str(transient)})
    if saved.get("saved") is not True:
        raise RuntimeError(f"transient end anchor was not saved: {saved}")
    return {
        "movie_frames_advanced": advanced["frames_advanced"],
        "emulator_frame": advanced["status"]["frame"],
        "equipped": equipped,
        "transient_anchor": {
            "path": str(transient),
            "sha256": sha256(transient),
            "retained": False,
        },
    }


def cross_branch(rig: Rig, transient: Path) -> dict[str, Any]:
    rig.load(transient)
    rig.clear_runtime_controls()
    before = equip_snapshot(rig)
    press = rig.call(
        "emulator.pressButton",
        {"button": "cross", "frames": 1, "port": 0, "release_after": True},
    )
    rig.advance(3)
    after = equip_snapshot(rig)
    return {
        "before": before,
        "input": {"button": "cross", "held_frames": 1},
        "press_end_frame": press["status"]["frame"],
        "settle_frames_after_press": 3,
        "after": after,
        "cleared": (
            before["harvester_state_s16"] == 1
            and before["harvester_bit_0x80"]
            and after["harvester_state_s16"] == 0
            and not after["harvester_bit_0x80"]
        ),
    }


def equipped_bee_branch(rig: Rig, transient: Path) -> dict[str, Any]:
    rig.load(transient)
    rig.clear_runtime_controls()
    bee = find_actor(rig, LEVEL01_BEE_ID)
    before = actor_snapshot(rig, bee)
    hp_change = advance_until_change(
        rig, address=bee + ACTOR_HP, value_type="s16", max_frames=220
    )
    at_contact = actor_snapshot(rig, bee)
    id_change = advance_until_change(
        rig, address=bee, value_type="u32", max_frames=300
    )
    retired = actor_snapshot(rig, bee)
    pointers_after = live_pointers(rig)
    return {
        "actor_identity": {
            "level": "LEVEL01",
            "id": LEVEL01_BEE_ID,
            "record": f"0x{bee:08X}",
            "mover_vm_family_lead": "bee program family (independent prior Canon)",
        },
        "before": before,
        "contact": {
            "frames_after_movie_end": hp_change["frames_advanced"],
            "advance_result": {
                "stopped": hp_change["stopped"],
                "reason": hp_change["reason"],
                "final_value": hp_change["final_value"],
            },
            "actor": at_contact,
        },
        "retirement": {
            "frames_after_contact": id_change["frames_advanced"],
            "frames_after_movie_end": (
                hp_change["frames_advanced"] + id_change["frames_advanced"]
            ),
            "advance_result": {
                "stopped": id_change["stopped"],
                "reason": id_change["reason"],
                "final_value": id_change["final_value"],
            },
            "actor": retired,
            "absent_from_live_table": bee not in pointers_after,
        },
        "passes": (
            before["id"] == LEVEL01_BEE_ID
            and before["hp_0x6e"] == 4
            and hp_change["stopped"]
            and at_contact["hp_0x6e"] == 998
            and id_change["stopped"]
            and retired["id"] == 0
            and bee not in pointers_after
        ),
    }


def disengaged_bee_control(rig: Rig, transient: Path) -> dict[str, Any]:
    rig.load(transient)
    rig.clear_runtime_controls()
    bee = find_actor(rig, LEVEL01_BEE_ID)
    before = actor_snapshot(rig, bee)
    rig.call(
        "emulator.pressButton",
        {"button": "cross", "frames": 1, "port": 0, "release_after": True},
    )
    rig.advance(135)
    at_contact_checkpoint = actor_snapshot(rig, bee)
    equipped_at_contact_checkpoint = equip_snapshot(rig)
    rig.advance(86)
    at_retirement_checkpoint = actor_snapshot(rig, bee)
    pointers_after = live_pointers(rig)
    return {
        "input": {
            "button": "cross",
            "held_frames": 1,
            "timing": "immediately after the shared movie-end anchor",
        },
        "before": before,
        "at_equipped_contact_checkpoint": {
            "frames_after_movie_end": 136,
            "equip": equipped_at_contact_checkpoint,
            "actor": at_contact_checkpoint,
        },
        "at_equipped_retirement_checkpoint": {
            "frames_after_movie_end": 222,
            "actor": at_retirement_checkpoint,
            "still_in_live_table": bee in pointers_after,
        },
        "passes": (
            before["hp_0x6e"] == 4
            and at_contact_checkpoint["id"] == LEVEL01_BEE_ID
            and at_contact_checkpoint["hp_0x6e"] == 4
            and equipped_at_contact_checkpoint["harvester_state_s16"] == 0
            and not equipped_at_contact_checkpoint["harvester_bit_0x80"]
            and at_retirement_checkpoint["id"] == LEVEL01_BEE_ID
            and at_retirement_checkpoint["hp_0x6e"] == 4
            and bee in pointers_after
        ),
    }


def instrumentation_residual(rig: Rig, transient: Path) -> dict[str, Any]:
    """Reproduce the known edge suppression without using it as behavior authority."""
    rig.load(transient)
    rig.clear_runtime_controls()
    watch = rig.call(
        "accessLog.addWatch",
        {
            "address": f"0x{HARVESTER_STATE:08X}",
            "length": POWER_FLAGS + 2 - HARVESTER_STATE,
            "type": "write",
            "label": "c13_disengage_writer_attempt",
            "max_events": 128,
        },
    )
    rig.call(
        "emulator.setControllerState",
        {"port": 0, "buttons": {"cross": True}},
    )
    result = rig.call("accessLog.run", {"frames": 1})
    rig.call("emulator.clearControllerState", {"port": 0})
    after = equip_snapshot(rig)
    rig.call("accessLog.clear", {})
    return {
        "purpose": "platform limitation only; not original-game behavioral authority",
        "watch_id": watch["watch_id"],
        "armed_ticks_before_input_frame": 0,
        "events": len(result.get("events", [])),
        "truncated": bool(result.get("truncated")),
        "after": after,
        "edge_suppressed": (
            not result.get("events")
            and after["harvester_state_s16"] == 1
            and after["harvester_bit_0x80"]
        ),
        "consequence": (
            "Do not claim a live writer PC for Cross disengage from this API path. "
            "Use the uninstrumented paired branch for behavior and pristine static "
            "stores for the current writer candidate."
        ),
    }


def source_identity(capabilities: dict[str, Any]) -> dict[str, Any]:
    source = capabilities.get("source") or {}
    status_raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1"], cwd=DUCK
    )
    return {
        "duckstation_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=DUCK, text=True
        ).strip(),
        "duckstation_status_sha256": hashlib.sha256(status_raw).hexdigest(),
        "capabilities_source": source,
        "api": capabilities.get("api"),
        "binary": capabilities.get("binary"),
        "features": capabilities.get("features"),
    }


def run(args) -> int:
    client = connect(args.port, args.token)
    rig = Rig(client)
    status = rig.call("debugger.status", {})
    media = verified_media_identity(rig, status)
    state_inspection = inspect_state_before_load(rig, START_STATE, media)
    capabilities = rig.call("debugger.capabilities", {})
    transient = Path(f"/tmp/phase4-c13-end-equipped-{os.getpid()}.sav")

    movie_sha = sha256(MOVIE)
    state_sha = sha256(START_STATE)
    annotations_sha = sha256(ANNOTATIONS)
    end = replay_to_end(rig, transient)
    cross = cross_branch(rig, transient)
    equipped = equipped_bee_branch(rig, transient)
    control = disengaged_bee_control(rig, transient)
    instrumentation = instrumentation_residual(rig, transient)

    static_writer_contract = {
        "equip_state_store": "0x80051EA0 (sh 1 -> 0x800A657E)",
        "equip_bit_store": "0x80051EB0 (sh flags|0x80 -> 0x800A6590)",
        "active_state_maintenance": "0x80051F60 (sh 1 -> 0x800A657E)",
        "bee_hp_998_store": (
            "0x8004B208 in FUNC_8004ABF4; reached only after the branch at "
            "0x8004B160 observes 0x800A6590 bit 0x80 or another native attack gate"
        ),
        "confidence": (
            "pristine static words plus exact uninstrumented HP outcome; the access "
            "logger suppresses this fixture's edge and is not cited as writer proof"
        ),
    }

    doc = {
        "schema": "abl-phase4-c13-harvester-live-v1",
        "generated": date.today().isoformat(),
        "status": "partial",
        "authority": {
            "media": "hash-verified pristine retail SCUS-94288",
            "allmods_role": "none",
            "media_identity": media,
        },
        "inputs": {
            "movie": {
                "path": MOVIE.relative_to(ROOT).as_posix(),
                "sha256": movie_sha,
            },
            "start_state": {
                "path": START_STATE.relative_to(ROOT).as_posix(),
                "sha256": state_sha,
                "inspection": state_inspection,
            },
            "annotations": {
                "path": ANNOTATIONS.relative_to(ROOT).as_posix(),
                "sha256": annotations_sha,
            },
        },
        "run_provenance": {
            "config_dir": str(Path(args.config_dir).resolve()),
            "port": args.port,
            "instance_state": args.instance_state,
            "source_identity": source_identity(capabilities),
            "generator_sha256": sha256(Path(__file__)),
        },
        "shared_end_anchor": end,
        "cross_disengage": cross,
        "equipped_bee_branch": equipped,
        "disengaged_bee_control": control,
        "instrumentation_residual": instrumentation,
        "static_writer_contract": static_writer_contract,
        "computed_checks": {
            "movie_ends_equipped": (
                end["equipped"]["harvester_state_s16"] == 1
                and end["equipped"]["harvester_bit_0x80"]
            ),
            "cross_disengages": cross["cleared"],
            "equipped_bee_retires": equipped["passes"],
            "disengaged_bee_survives": control["passes"],
            "access_log_edge_suppression_reproduced": instrumentation["edge_suppressed"],
        },
        "conclusions": [
            (
                "Cross disengages the LEVEL01 grain harvester: 0x800A657E changes "
                "1->0 and 0x800A6590 bit 0x80 clears in the uninstrumented branch."
            ),
            (
                "Remaining equipped causes the id-13 LEVEL01 bee at 0x8009FF0C to "
                "change HP 4->998 at +136 frames, then id 13->0 and live-table "
                "retirement 86 frames later."
            ),
            (
                "The matched immediate-Cross control leaves the same bee at HP 4, "
                "id 13, and present in 0x80090748 at both +136 and +222 frames."
            ),
        ],
        "remaining": [
            "Exact per-frame writer that steers ctor-0x51 grain contacts",
            "Cross disengage writer PC (live logging suppresses the edge; static candidate remains)",
            "Harvester enemy eligibility/immunity breadth beyond this LEVEL01 bee",
            "All-level availability and render/animation ownership",
        ],
    }
    if not all(doc["computed_checks"].values()):
        print(json.dumps(doc["computed_checks"], indent=2), file=sys.stderr)
        return 1
    write_live_evidence(OUTPUT, doc)
    print(
        "[c13-live] Cross cleared; bee HP 4->998 at +"
        f"{equipped['contact']['frames_after_movie_end']}f and retired at +"
        f"{equipped['retirement']['frames_after_movie_end']}f; "
        "matched disengaged control survived"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_required_live_args(parser)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
