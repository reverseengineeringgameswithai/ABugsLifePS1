#!/usr/bin/env python3
"""Capture a G29 Pass-3 collision trace and the resident DAT visual-edit value.

This is the disc-parameterised sibling of ``tools/trace_g29_pass3_arm_a.py``.  It
runs the *identical* collision watch set, controller input, and timing as Arm A,
and additionally reads the one LEVEL.DAT visual-floor halfword that the G28
Candidate-A edit changes (file ``0x18992`` -> runtime ``0x8017918a``; pristine
5001, patched +1024 = 6025).  Running it against the pristine disc reproduces the
Arm-A baseline; running it against the rebuilt G28 disc is **Arm B**.

The resident visual-edit read is the decisive guard that the intended disc is
actually mounted: the from-boot movie boots whatever media is loaded, so a
patched value of 6025 proves the G28 LEVEL.DAT reached RAM, and a pristine 5001
proves it did not.  Use ``--expect-visual`` to fail loudly on a mismatch.

It writes no game/disc/state data; ``--output`` is optional and should point at
scratch storage (for example ``/tmp``).
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

# FUNC_800345CC collision resolver consumes the candidate-plane list at one of
# several sibling read sites depending on the capture micro-phase (Arm A's
# committed run saw 0x8003463c; the from-boot replay phase here uses 0x80035304).
# The robust invariant is not the exact PC but that a PC inside the resolver
# reads the canonical active collision planes below.
RESOLVER_LO, RESOLVER_HI = 0x800345CC, 0x80035400
KNOWN_ACTIVE_PLANES = (
    "0x800ccc60",
    "0x800cd0d0",
    "0x800cd0f0",
    "0x800cd110",
    "0x800cd130",
)

# Resident LEVEL01 LEVEL.DAT image base (Candidate A vertex base 0x801790c4 =
# DAT_BASE + file 0x188cc -> DAT_BASE = 0x801607f8; cross-checked against the
# chaser spawn-area records).  The G28 visual edit is DAT file 0x18992.
DAT_BASE = 0x801607F8
G28_DAT_FILE_OFFSET = 0x18992
VISUAL_EDIT_ADDR = DAT_BASE + G28_DAT_FILE_OFFSET  # 0x8017918a
CANDIDATE_A_VERT0 = 0x801790C4
VISUAL_PRISTINE = 5001
VISUAL_PATCHED = 6025


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

    def s16(self, address: int) -> int:
        return struct.unpack("<h", self.read(address, 2))[0]


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
    if RESOLVER_LO <= pc_int < RESOLVER_HI:
        context["known_function"] = "FUNC_800345CC collision resolver"
    elif 0x8003633C <= pc_int < 0x8003731C:
        context["known_function"] = "FUNC_8003633C player movement/collision integrator"
    elif 0x80038090 <= pc_int < 0x800390EC:
        context["known_function"] = "FUNC_80038090 secondary candidate consumer"
    return context


def read_visual(dbg: Dbg) -> dict:
    """Read the resident DAT visual-edit halfword plus context windows."""
    return {
        "addr": addr(VISUAL_EDIT_ADDR),
        "value": dbg.s16(VISUAL_EDIT_ADDR),
        "window_hex": dbg.read(VISUAL_EDIT_ADDR - 4, 16).hex(),
        "candidate_a_vert0_addr": addr(CANDIDATE_A_VERT0),
        "candidate_a_vert0_hex": dbg.read(CANDIDATE_A_VERT0, 16).hex(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=23460)
    parser.add_argument("--token", default=f"debugger-{os.getuid()}")
    fixture_group = parser.add_mutually_exclusive_group()
    fixture_group.add_argument("--save", help="disc-backed LEVEL01 spawn state")
    fixture_group.add_argument(
        "--movie", help="from-boot movie used instead of --save"
    )
    parser.add_argument(
        "--disc",
        required=True,
        help="expected mounted disc cue (pristine for baseline, G28 for Arm B)",
    )
    parser.add_argument(
        "--arm-label", default="G29 Pass-3 (parameterised)", help="report label"
    )
    parser.add_argument(
        "--expect-visual",
        type=int,
        help="fail unless the resident DAT visual halfword equals this (5001 or 6025)",
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
        parser.error(f"disc cue not found: {disc}")

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
                f"fixture is not for the requested disc: {state_media} != {disc}"
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
        raise SystemExit(f"fixture selected unexpected media: {mounted} != {disc}")

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
    visual_before = read_visual(dbg)
    sector_before = dbg.read(SECTOR_TABLE, SECTOR_COUNT * SECTOR_STRIDE)
    before = {
        "player_xyz": [dbg.s32(address) for address in PLAYER_XYZ],
        "sector186_y": dbg.s32(SECTOR186_Y),
        "spawn_sector124_y": dbg.s32(SPAWN_SECTOR_Y),
        "visual_edit": visual_before,
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

    dbg.call("emulator.setControllerState", {"port": 0, "buttons": {"left": True}})
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
    visual_after = read_visual(dbg)
    sector_after = dbg.read(SECTOR_TABLE, SECTOR_COUNT * SECTOR_STRIDE)
    after = {
        "player_xyz": [dbg.s32(address) for address in PLAYER_XYZ],
        "sector186_y": dbg.s32(SECTOR186_Y),
        "spawn_sector124_y": dbg.s32(SPAWN_SECTOR_Y),
        "visual_edit": visual_after,
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
    candidate_values = set(watches["candidate_plane_list"]["summary"]["values"])
    player_y_pcs = watches["player_y"]["summary"]["pcs"]
    visual_value = visual_after["value"]
    resolver_read = any(
        RESOLVER_LO <= int(pc, 16) < RESOLVER_HI for pc in candidate_pcs
    )
    active_planes_seen = sum(p in candidate_values for p in KNOWN_ACTIVE_PLANES)
    checks = {
        "scene_is_level01": scene == 1,
        "exact_spawn_reached": reached_xyz == [197091, 2734, 492897],
        # Robust to capture phase: the resolver read the candidate list AND the
        # canonical active collision planes were among the values, regardless of
        # which sibling read PC (0x8003463c / 0x80035304) fired this phase.
        "collision_resolver_read_candidate_list": resolver_read
        and active_planes_seen >= 3,
        "player_y_commit_observed": "0x80036cf0" in player_y_pcs,
        "sector_table_unchanged_during_capture": sector_before == sector_after,
        "visual_edit_value_known": visual_value in (VISUAL_PRISTINE, VISUAL_PATCHED),
    }
    if args.expect_visual is not None:
        checks["visual_edit_matches_expected"] = visual_value == args.expect_visual
    arm_captured = all(checks.values())

    report = {
        "experiment": "G29 Pass-3 (Arm B / parameterised)",
        "arm": args.arm_label,
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
            "dat_base": addr(DAT_BASE),
            "g28_dat_file_offset": addr(G28_DAT_FILE_OFFSET),
            "visual_edit_addr": addr(VISUAL_EDIT_ADDR),
            "candidate_a_vert0": addr(CANDIDATE_A_VERT0),
            "visual_pristine_value": VISUAL_PRISTINE,
            "visual_patched_value": VISUAL_PATCHED,
        },
        "before": before,
        "after": after,
        "sector_table_unchanged": sector_before == sector_after,
        "visual_edit_value": visual_value,
        "visual_edit_is_patched": visual_value == VISUAL_PATCHED,
        "collision_resolver": {
            "candidate_read_pcs": candidate_pcs,
            "resolver_pc_seen": resolver_read,
            "active_planes_seen": active_planes_seen,
            "known_active_planes": list(KNOWN_ACTIVE_PLANES),
        },
        "checks": checks,
        "arm_captured": arm_captured,
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
                "The watched collision addresses are not the 0x8018xxxx LEVEL.DAT "
                "render payload used by fcn.80010000; the visual_edit read at "
                f"{addr(VISUAL_EDIT_ADDR)} IS that DAT payload (Candidate A region)."
            ),
            "counterfactual": (
                "When run on the G28 disc the visual_edit value is the patched 6025 "
                "while the collision sector table hash and reader path match the "
                "pristine baseline -> the visual edit does not perturb collision."
            ),
        },
    }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote {output}")
        print(json.dumps({
            "arm_label": args.arm_label,
            "fixture_sha256": report["fixture"]["sha256"],
            "disc_cue_sha256": report["disc"]["cue_sha256"],
            "scene_id": scene,
            "visual_edit_value": visual_value,
            "visual_edit_is_patched": visual_value == VISUAL_PATCHED,
            "timing": report["timing"],
            "watch_summaries": {
                key: item["summary"] for key, item in watches.items()
            },
            "last_player_y_writer": last_player_y_writer,
            "sector_table_unchanged": report["sector_table_unchanged"],
            "checks": checks,
            "arm_captured": arm_captured,
        }, indent=2, sort_keys=True))
    else:
        print(rendered)
    return 0 if arm_captured else 1


if __name__ == "__main__":
    raise SystemExit(main())
