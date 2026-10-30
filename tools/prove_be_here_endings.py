#!/usr/bin/env python3
"""Live-probe RCG-003 "be here" endpoint save states through DuckStation RPC.

This is intentionally narrow: it loads only the operator-confirmed simple
endpoint saves, drives normal controller input, and watches the retail
transition latch. It does not probe conditional/boss endings.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


CLIENT_PATH = Path("~/duckstation/scripts/debugger-client/duckstation_debug_client.py")

SECTOR_TABLE = 0x800A7E48
SECTOR_STRIDE = 0x30
SECTOR_REGION_CODE = 0x2E
CURRENT_SECTOR = 0x80090560
SCENE_ID = 0x80082504
FLIK_BASE = 0x800A6500
FLIK_GATE = 0x800A6582
TRANSITION_LEVER = 0x800823A0
FADE_COLOR = 0x80082470

SAVE_CASES = [
    ("LEVEL02", "LEVEL02_ENDING.sav", 579, 3, None),
    ("LEVEL04", "LEVEL04_ENDING.sav", 131, 3, None),
    ("LEVEL05", "LEVEL05_ENDING.sav", 297, 3, None),
    ("LEVEL14", "LEVEL14_ENDING_1.sav", 334, 2, "start"),
]

BUTTON_TRIALS = [
    ("up", {"up": True}),
]


def load_client_module() -> Any:
    spec = importlib.util.spec_from_file_location("duckstation_debug_client", CLIENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {CLIENT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_fields(client: Any) -> dict[str, Any]:
    reads = [
        {"address": hex(CURRENT_SECTOR), "type": "s32"},
        {"address": hex(FLIK_GATE), "type": "u8"},
        {"address": hex(TRANSITION_LEVER), "type": "u16"},
        {"address": hex(FADE_COLOR), "type": "u16"},
        {"address": hex(SCENE_ID), "type": "u16"},
        {"address": hex(FLIK_BASE + 0x00), "type": "s32"},
        {"address": hex(FLIK_BASE + 0x04), "type": "s32"},
        {"address": hex(FLIK_BASE + 0x08), "type": "s32"},
    ]
    result = client.call("debugger.scatterRead", {"reads": reads}, timeout=10.0)
    vals = [r.get("value") for r in result["reads"]]
    sector = vals[0]
    out: dict[str, Any] = {
        "current_sector": sector,
        "flik_gate": vals[1],
        "transition_lever": vals[2],
        "fade_color": vals[3],
        "scene_id": vals[4],
        "flik_x": vals[5],
        "flik_y": vals[6],
        "flik_z": vals[7],
    }
    if isinstance(sector, int) and 0 <= sector < 700:
        code_addr = SECTOR_TABLE + sector * SECTOR_STRIDE + SECTOR_REGION_CODE
        code = client.call("debugger.readU16", {"address": hex(code_addr)}, timeout=10.0)
        out["current_sector_code"] = code.get("value")
    else:
        out["current_sector_code"] = None
    return out


def clear_controller(client: Any) -> None:
    client.call("emulator.clearControllerState", {"port": 0}, timeout=10.0)


def run_trial(
    client: Any,
    state_path: Path,
    trial_name: str,
    buttons: dict[str, bool],
    frames: int,
    prelude_button: str | None,
) -> dict[str, Any]:
    client.call("emulator.loadState", {"path": str(state_path), "pause_after_load": True}, timeout=30.0)
    clear_controller(client)
    client.call("accessLog.clear", {}, timeout=10.0)
    before = read_fields(client)
    watch = client.call(
        "accessLog.addWatch",
        {
            "address": hex(TRANSITION_LEVER),
            "length": 2,
            "type": "write",
            "label": "transition_lever",
            "max_events": 256,
            "stop_on_hit": False,
        },
        timeout=10.0,
    )
    prelude = None
    if prelude_button:
        prelude = client.call(
            "emulator.pressButton",
            {"button": prelude_button, "frames": 6, "port": 0, "release_after": True},
            timeout=10.0,
        )
    if buttons:
        client.call("emulator.setControllerState", {"port": 0, "buttons": buttons}, timeout=10.0)
    run = client.call("accessLog.run", {"frames": frames}, timeout=60.0)
    clear_controller(client)
    after = read_fields(client)
    events = client.call(
        "accessLog.get",
        {"watch_id": watch["watch_id"], "offset": 0, "limit": 256},
        timeout=10.0,
    )
    status = client.call("debugger.status", {}, timeout=10.0)
    return {
        "trial": trial_name,
        "buttons": buttons,
        "frames": frames,
        "prelude_button": prelude_button,
        "prelude": prelude,
        "before": before,
        "after": after,
        "watch": watch,
        "run_total": run.get("total"),
        "events": events.get("events", []),
        "event_total": events.get("total"),
        "truncated": events.get("truncated"),
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2346)
    parser.add_argument("--token", default=None)
    parser.add_argument("--frames", type=int, default=180)
    parser.add_argument("--out", type=Path, default=Path("build/rcg003_be_here_probe.json"))
    args = parser.parse_args()

    mod = load_client_module()
    token = args.token or mod.find_token()
    client = mod.DebuggerClient(args.host, args.port, "ws")
    try:
        if token:
            client.authenticate(token)
        media = client.call("emulator.getMediaInfo", {}, timeout=10.0)
        status = client.call("debugger.status", {}, timeout=10.0)
        output: dict[str, Any] = {
            "probe": "RCG-003 be-here endpoints",
            "media": media,
            "initial_status": status,
            "cases": [],
        }
        for level, save_name, expected_sector, expected_code, prelude_button in SAVE_CASES:
            state_path = (args.root / save_name).resolve()
            case: dict[str, Any] = {
                "level": level,
                "save": str(state_path),
                "expected_sector": expected_sector,
                "expected_code": expected_code,
                "trials": [],
                "first_hit": None,
            }
            for trial_name, buttons in BUTTON_TRIALS:
                trial = run_trial(client, state_path, trial_name, buttons, args.frames, prelude_button)
                case["trials"].append(trial)
                hit_sector = trial["after"].get("current_sector") == expected_sector
                hit_code = trial["after"].get("current_sector_code") == expected_code
                wrote_latch = bool(trial["events"]) or trial["after"].get("transition_lever") != 0
                if case["first_hit"] is None and (hit_sector or hit_code or wrote_latch):
                    case["first_hit"] = {
                        "trial": trial_name,
                        "hit_sector": hit_sector,
                        "hit_code": hit_code,
                        "wrote_latch": wrote_latch,
                        "after": trial["after"],
                        "events": trial["events"][:8],
                    }
                    if wrote_latch:
                        break
            output["cases"].append(case)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output, indent=2))
    finally:
        try:
            clear_controller(client)
            client.call("accessLog.clear", {}, timeout=10.0)
        finally:
            client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
