#!/usr/bin/env python3
"""Capture the pristine G29 Pass-3 Arm-A collision baseline.

This script loads the operator-supplied LEVEL01 spawn state, verifies the game
and scene, arms non-halting access watches after the required settle frame, and
records eight frames of collision-sector reads plus the collision-resolved
player-Y writer.  It writes no game/disc/state data; ``--output`` is optional
and should point at scratch storage (for example ``/tmp``).

The older Pass-3 plan names sector 186 Y (0x800AA12C), which belongs to the G30
openground fixture.  The current spawn notes identify sector 124
(0x800A9588, Y at 0x800A958C), so both are watched.  A zero-hit sector-186 watch
is therefore a useful fixture-context check, not evidence that collision is
idle.  The script holds Left during the capture because the historical G29 live
note establishes that this fixture does not run player collision while idle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

_DUCK = os.environ.get("DUCKSTATION_DIR", os.path.expanduser("~/duckstation"))
sys.path.insert(0, os.path.join(_DUCK, "scripts", "debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

GAME_SERIAL = "SCUS-94288"
SCENE_ID = 0x80082504
PLAYER_XYZ = (0x800A6500, 0x800A6504, 0x800A6508)
PLAYER_Y = 0x800A6504
SECTOR_TABLE = 0x800A7E48
SECTOR_STRIDE = 0x30
SECTOR_COUNT = 223
SECTOR186_Y = SECTOR_TABLE + 186 * SECTOR_STRIDE + 4
SPAWN_SECTOR = 124
SPAWN_SECTOR_BASE = SECTOR_TABLE + SPAWN_SECTOR * SECTOR_STRIDE
SPAWN_SECTOR_Y = SPAWN_SECTOR_BASE + 4
CANDIDATE_LIST = 0x8009C230
SPAWN_CANDIDATE_SECTORS = (87, 89, 96, 97, 105, 106, 124, 126, 171)


def addr(value: int) -> str:
    return f"0x{value:08x}"


class Dbg:
    def __init__(self, host: str, port: int, token: str):
        self.client = DebuggerClient(host, port, "ws")
        self.client.authenticate(token)
        try:
            self.client.transport.sock.settimeout(60)
        except Exception:
            pass

    def call(self, method: str, params: dict | None = None):
        return self.client.call(method, params or {})

    def read(self, address: int, length: int) -> bytes:
        result = self.call(
            "debugger.readMemory", {"address": addr(address), "length": length}
        )
        return bytes.fromhex(result["hex"])

    def u32(self, address: int) -> int:
        return struct.unpack("<I", self.read(address, 4))[0]

    def s32(self, address: int) -> int:
        return struct.unpack("<i", self.read(address, 4))[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_events(events: list[dict]) -> dict:
    pcs = Counter(event.get("pc", "unknown") for event in events)
    values = Counter(event.get("value_hex", "unknown") for event in events)
    return {
        "event_count": len(events),
        "pcs": dict(sorted(pcs.items())),
        "values": dict(sorted(values.items())),
        "first_frame": events[0].get("frame") if events else None,
        "last_frame": events[-1].get("frame") if events else None,
        "first_cycle": events[0].get("cycle") if events else None,
        "last_cycle": events[-1].get("cycle") if events else None,
    }


def context_for_pc(dbg: Dbg, pc: str) -> dict:
    pc_int = int(pc, 16)
    context = {"pc": pc}
    try:
        result = dbg.call(
            "debugger.disassemble", {"address": addr(pc_int - 4), "count": 2}
        )
        context["nearby_instructions"] = result.get("instructions", [])
    except Exception as error:
        context["disassemble_error"] = str(error)
    if 0x800345CC <= pc_int < 0x80035280:
        context["known_function"] = "FUNC_800345CC collision resolver"
    elif 0x8003633C <= pc_int < 0x8003731C:
        context["known_function"] = "FUNC_8003633C player movement/collision integrator"
    elif 0x80038090 <= pc_int < 0x800390EC:
        context["known_function"] = "FUNC_80038090 secondary candidate consumer"
    return context


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=23460)
    parser.add_argument("--token", default=f"debugger-{os.getuid()}")
    fixture_group = parser.add_mutually_exclusive_group()
    fixture_group.add_argument(
        "--save",
        help="pristine-disc-backed LEVEL01 spawn state",
    )
    fixture_group.add_argument(
        "--movie",
        help="optional pristine from-boot movie used instead of --save",
    )
    parser.add_argument(
        "--disc",
        default=os.path.join(os.getcwd(), "Disney-Pixar A Bug's Life (v1.0).cue"),
        help="expected pristine disc cue (checked against state + mounted media)",
    )
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument("--output", help="optional JSON output path (prefer /tmp)")
    args = parser.parse_args()
    if not args.save and not args.movie:
        args.movie = os.path.join(os.getcwd(), "flik_to_level01_stall.mv.movie.json")

    if not 1 <= args.frames <= 600:
        parser.error("--frames must be in 1..600")
    save = Path(args.save).expanduser().resolve() if args.save else None
    if not args.movie and (save is None or not save.is_file()):
        parser.error(f"save state not found: {save}")
    movie = Path(args.movie).expanduser().resolve() if args.movie else None
    if movie is not None and not movie.is_file():
        parser.error(f"input movie not found: {movie}")
    disc = Path(args.disc).expanduser().resolve()
    if not disc.is_file():
        parser.error(f"pristine disc cue not found: {disc}")

    dbg = Dbg(args.host, args.port, args.token)
    initial_status = dbg.call("debugger.status")
    if initial_status.get("game_serial") != GAME_SERIAL:
        raise SystemExit(
            f"refusing non-ABL instance: {initial_status.get('game_serial')!r}"
        )

    initial_media = dbg.call("emulator.getMediaInfo")
    mounted = Path(initial_media.get("path", "")).expanduser().resolve()
    if mounted != disc:
        raise SystemExit(f"wrong disc mounted before load: {mounted} != {disc}")

    # Controller holds persist across loadState, so force a known neutral start.
    dbg.call("emulator.clearControllerState", {"port": 0})

    state_info = None
    if movie is not None:
        try:
            dbg.call("movie.stopPlayback")
        except Exception:
            pass
        movie_load = dbg.call("movie.load", {"path": str(movie)})
        if movie_load.get("game_serial") != GAME_SERIAL:
            raise SystemExit(
                f"movie has wrong serial: {movie_load.get('game_serial')!r}"
            )
        if not movie_load.get("start_state", {}).get("from_boot"):
            raise SystemExit("movie is not anchored to a cold boot")
        load = dbg.call(
            "movie.startPlayback", {"start_frame": 0, "load_start_state": True}
        )
        dbg.call("emulator.setFastForward", {"enabled": True})
        try:
            remaining = movie_load["frame_count"]
            while remaining:
                step = min(120, remaining)
                dbg.call("emulator.advanceFrames", {"frames": step})
                remaining -= step
        finally:
            dbg.call("emulator.setFastForward", {"enabled": False})
            dbg.call("movie.stopPlayback")
        fixture = {
            "kind": "from_boot_movie",
            "path": str(movie),
            "size": movie.stat().st_size,
            "sha256": sha256_file(movie),
            "movie_load": movie_load,
        }
    else:
        assert save is not None
        state_info = dbg.call("emulator.getStateInfo", {"path": str(save)})
        state_media = Path(state_info.get("media_path", "")).expanduser().resolve()
        if not state_info.get("valid") or state_info.get("serial") != GAME_SERIAL:
            raise SystemExit(f"invalid/wrong-game fixture metadata: {state_info}")
        if state_media != disc:
            raise SystemExit(
                f"fixture is not pristine-disc-backed: {state_media} != {disc}"
            )
        load = dbg.call(
            "emulator.loadState",
            {
                "path": str(save),
                "pause_after_load": True,
                "validate_disc": True,
                "auto_select_disc": False,
            },
        )
        if load.get("game_serial") != GAME_SERIAL:
            raise SystemExit(
                f"loaded state has wrong serial: {load.get('game_serial')!r}"
            )
        fixture = {
            "kind": "save_state",
            "path": str(save),
            "size": save.stat().st_size,
            "sha256": sha256_file(save),
        }
    loaded_media = dbg.call("emulator.getMediaInfo")
    mounted = Path(loaded_media.get("path", "")).expanduser().resolve()
    if mounted != disc:
        raise SystemExit(f"fixture selected non-pristine media: {mounted} != {disc}")

    # Required API safety rule: settle one frame after loadState before watches.
    dbg.call("emulator.advanceFrames", {"frames": 1})
    dbg.call("debugger.pause")
    scene = dbg.u32(SCENE_ID)
    if scene != 1:
        raise SystemExit(f"loaded state is not LEVEL01: scene_id={scene}")

    reached_xyz = [dbg.s32(address) for address in PLAYER_XYZ]
    handoff = None
    if movie is not None:
        # This movie intentionally ends with the in-game START pause menu open.
        # A short Cross pulse dismisses it into normal player control.
        handoff = dbg.call(
            "emulator.pressButton",
            {"button": "cross", "frames": 3, "port": 0, "release_after": True},
        )

    before_status = dbg.call("debugger.status")
    sector_before = dbg.read(SECTOR_TABLE, SECTOR_COUNT * SECTOR_STRIDE)
    before = {
        "player_xyz": [dbg.s32(address) for address in PLAYER_XYZ],
        "sector186_y": dbg.s32(SECTOR186_Y),
        "spawn_sector124_y": dbg.s32(SPAWN_SECTOR_Y),
        "sector_table_full_sha256": hashlib.sha256(sector_before).hexdigest(),
        "sector_table_head_512_sha256": hashlib.sha256(sector_before[:512]).hexdigest(),
    }

    dbg.call("accessLog.clear")
    watch_specs = [
        {
            "key": "sector_table_head",
            "address": SECTOR_TABLE,
            "length": 64,
            "type": "read",
            "why": "original Pass-3 collision-table head watch",
        },
        {
            "key": "sector186_y",
            "address": SECTOR186_Y,
            "length": 4,
            "type": "read",
            "why": "original plan; G30 openground sector, retained as control",
        },
        {
            "key": "candidate_plane_list",
            "address": CANDIDATE_LIST,
            "length": 44 * 4,
            "type": "read",
            "why": "current spawn resolver candidate-plane pointers",
        },
        {
            "key": "player_y",
            "address": PLAYER_Y,
            "length": 4,
            "type": "write",
            "why": "collision-resolved footing output",
        },
    ]
    for sector in SPAWN_CANDIDATE_SECTORS:
        watch_specs.append(
            {
                "key": f"candidate_sector_{sector}",
                "address": SECTOR_TABLE + sector * SECTOR_STRIDE,
                "length": SECTOR_STRIDE,
                "type": "read",
                "why": "candidate sector in the documented pristine-spawn clamp set",
            }
        )
    watches = {}
    for spec in watch_specs:
        result = dbg.call(
            "accessLog.addWatch",
            {
                "address": addr(spec["address"]),
                "length": spec["length"],
                "type": spec["type"],
                "label": spec["key"],
                "max_events": 10000,
            },
        )
        watches[spec["key"]] = {"spec": spec, "watch": result}

    dbg.call(
        "emulator.setControllerState", {"port": 0, "buttons": {"left": True}}
    )
    try:
        run = dbg.call("accessLog.run", {"frames": args.frames})
    finally:
        dbg.call("emulator.clearControllerState", {"port": 0})
    for key, item in watches.items():
        result = dbg.call(
            "accessLog.get", {"watch_id": item["watch"]["watch_id"], "limit": 10000}
        )
        item["events"] = result.get("events", [])
        item["summary"] = summarize_events(item["events"])

    last_player_y_writer = dbg.call(
        "accessLog.lastWriter", {"address": addr(PLAYER_Y)}
    )
    dbg.call("accessLog.clear")

    after_status = dbg.call("debugger.status")
    sector_after = dbg.read(SECTOR_TABLE, SECTOR_COUNT * SECTOR_STRIDE)
    after = {
        "player_xyz": [dbg.s32(address) for address in PLAYER_XYZ],
        "sector186_y": dbg.s32(SECTOR186_Y),
        "spawn_sector124_y": dbg.s32(SPAWN_SECTOR_Y),
        "sector_table_full_sha256": hashlib.sha256(sector_after).hexdigest(),
        "sector_table_head_512_sha256": hashlib.sha256(sector_after[:512]).hexdigest(),
    }

    unique_pcs = sorted(
        {
            event["pc"]
            for item in watches.values()
            for event in item["events"]
            if event.get("pc")
        }
    )
    pc_context = [context_for_pc(dbg, pc) for pc in unique_pcs]
    candidate_pcs = watches["candidate_plane_list"]["summary"]["pcs"]
    player_y_pcs = watches["player_y"]["summary"]["pcs"]
    checks = {
        "scene_is_level01": scene == 1,
        "exact_spawn_reached": reached_xyz == [197091, 2734, 492897],
        "collision_resolver_read_candidate_list": "0x8003463c" in candidate_pcs,
        "player_y_commit_observed": "0x80036cf0" in player_y_pcs,
        "sector_table_unchanged_during_capture": sector_before == sector_after,
    }
    arm_a_captured = all(checks.values())

    report = {
        "experiment": "G29 Pass-3 Arm A",
        "arm": "pristine LEVEL01 spawn baseline",
        "fixture": fixture,
        "disc": {
            "path": str(disc),
            "cue_sha256": sha256_file(disc),
            "state_info": state_info,
            "initial_media": initial_media,
            "loaded_media": loaded_media,
        },
        "identity": {
            "expected_game_serial": GAME_SERIAL,
            "scene_id": scene,
            "load_result": load,
            "initial_status": initial_status,
        },
        "timing": {
            "settle_frames_after_fixture": 1,
            "fixture_reached_player_xyz": reached_xyz,
            "movie_in_game_unpause": {"button": "cross", "frames": 3}
            if movie is not None
            else None,
            "capture_frames": args.frames,
            "controller_input": {"port": 0, "left": True},
            "start_frame": before_status.get("frame"),
            "end_frame": after_status.get("frame"),
            "start_cycle": before_status.get("cycle"),
            "end_cycle": after_status.get("cycle"),
        },
        "address_basis": {
            "collision_sector_table": addr(SECTOR_TABLE),
            "sector_stride": addr(SECTOR_STRIDE),
            "historical_sector186_y": addr(SECTOR186_Y),
            "spawn_sector": SPAWN_SECTOR,
            "spawn_sector_base": addr(SPAWN_SECTOR_BASE),
            "spawn_sector_y": addr(SPAWN_SECTOR_Y),
            "spawn_candidate_sectors_from_current_notes": list(
                SPAWN_CANDIDATE_SECTORS
            ),
            "candidate_plane_list": addr(CANDIDATE_LIST),
            "player_y": addr(PLAYER_Y),
        },
        "before": before,
        "after": after,
        "sector_table_unchanged": sector_before == sector_after,
        "checks": checks,
        "arm_a_captured": arm_a_captured,
        "watches": watches,
        "run_status": run.get("status"),
        "handoff_status": handoff,
        "last_player_y_writer": last_player_y_writer,
        "pc_context": pc_context,
        "call_stack_note": (
            "Access-log read events do not retain call stacks; lastWriter exposes "
            "callStack but the current implementation returns an empty list."
        ),
        "bounded_interpretation": {
            "source": (
                "0x800A7E48 sector records are the runtime collision structure "
                "built from LEVEL01 LEVEL.RAW chunk 32 per the prior load/build trace."
            ),
            "not_dat": (
                "These watched addresses are not the 0x8018xxxx LEVEL.DAT render "
                "payload used by fcn.80010000."
            ),
            "arm_a_only": (
                "This is a pristine baseline. It does not establish the visual-edit "
                "counterfactual until Arm B repeats the capture on the identified G28 disc."
            ),
        },
    }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote {output}")
        print(json.dumps({
            "fixture_sha256": report["fixture"]["sha256"],
            "scene_id": scene,
            "timing": report["timing"],
            "watch_summaries": {
                key: item["summary"] for key, item in watches.items()
            },
            "last_player_y_writer": last_player_y_writer,
            "sector_table_unchanged": report["sector_table_unchanged"],
            "checks": checks,
            "arm_a_captured": arm_a_captured,
        }, indent=2, sort_keys=True))
    else:
        print(rendered)
    return 0 if arm_a_captured else 1


if __name__ == "__main__":
    raise SystemExit(main())
