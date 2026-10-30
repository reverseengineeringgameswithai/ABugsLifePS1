#!/usr/bin/env python3
"""Reproduce the Phase-2 movie/execTrace perturbation on pristine media.

The same hash-pinned movie is replayed twice without instrumentation and once
with a harmless execution watch armed before advancing.  The decisive raw
observable is the first plant slot at movie frame 120.  This tool is live and
must be run against a fresh isolated external-debugger instance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
MOVIE = ROOT / "movies/Phase4/A13/blue_seed_levels.movie.json"
STATE = ROOT / "movies/Phase4/A13/blue_seed_levels.movie.sav"
OUT = ROOT / "analysis/phase2_platform_gotchas.json"
PLANT_SLOTS = 0x80090BF0
PLANT_CURSOR = 0x800822B8
TARGET_FRAME = 120


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23474)
    ap.add_argument("--token", default="phase2-closure")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)
    status = c.call("debugger.status", {})
    if status.get("game_serial") != "SCUS-94288":
        raise SystemExit(f"wrong media: {status}")

    def rd(addr: int, length: int) -> bytes:
        r = c.call("debugger.readMemory", {"address": f"0x{addr:08x}", "length": length})
        return bytes.fromhex(r["hex"])

    def clear():
        for method in ("movie.stopPlayback", "movie.clear", "execTrace.clear"):
            try:
                c.call(method, {})
            except Exception:
                pass

    def trial(watch: bool) -> dict:
        clear()
        c.call("movie.load", {"path": str(MOVIE)})
        start = c.call("movie.startPlayback", {"load_start_state": True})
        if not start.get("playing") or not start.get("reproducible"):
            raise RuntimeError(start)
        watch_id = None
        if watch:
            watch_id = c.call("execTrace.addWatch", {
                "pc": "0x8005BDBC", "capture": [], "label": "plant_spawn",
                "max_events": 16,
            })["watch_id"]
        c.call("movie.advanceToFrame", {"frame": TARGET_FRAME, "max_frames": 1000}, timeout=300)
        raw = rd(PLANT_SLOTS, 20 * 0x30)
        cursor = struct.unpack("<I", rd(PLANT_CURSOR, 4))[0]
        result = {
            "watch_armed": watch,
            "watch_id": watch_id,
            "frame": TARGET_FRAME,
            "slot0_type": struct.unpack_from("<H", raw, 0)[0],
            "plant_cursor": cursor,
            "plant_table_sha256": hashlib.sha256(raw).hexdigest(),
        }
        if watch_id is not None:
            tr = c.call("execTrace.get", {"watch_id": watch_id, "offset": 0, "limit": 16})
            result["watch_events"] = tr.get("total", len(tr.get("events", [])))
        clear()
        return result

    poll_a = trial(False)
    poll_b = trial(False)
    watched = trial(True)
    poll_repeatable = poll_a == poll_b
    poll_expected = poll_a["slot0_type"] == 7 and poll_a["plant_cursor"] == 1
    perturbed = (watched["slot0_type"], watched["plant_cursor"], watched["plant_table_sha256"]) != (
        poll_a["slot0_type"], poll_a["plant_cursor"], poll_a["plant_table_sha256"])
    doc = {
        "_comment": "Live A/B platform constraint. Regenerate only on a fresh isolated pristine instance: python3 tools/phase2_platform_gotchas.py --port PORT --token TOKEN.",
        "generated": date.today().isoformat(),
        "authority": {
            "serial": status["game_serial"],
            "media": status.get("game_path"),
            "duckstation_fork_head": subprocess.check_output(
                ["git", "-C", str(Path.home() / "duckstation"), "rev-parse", "HEAD"],
                text=True).strip(),
            "duckstation_binary_sha256": sha(
                Path.home() / "duckstation/build-release/bin/duckstation-qt"),
            "debugger_transport": "ws loopback; isolated config required by AGENTS.md",
        },
        "fixture": {
            "movie": str(MOVIE.relative_to(ROOT)), "movie_sha256": sha(MOVIE),
            "state": str(STATE.relative_to(ROOT)), "state_sha256": sha(STATE),
        },
        "execTrace_movie_desynchronization": {
            "target_frame": TARGET_FRAME,
            "poll_only_a": poll_a,
            "poll_only_b": poll_b,
            "watch_armed": watched,
            "poll_only_byte_deterministic": poll_repeatable,
            "poll_only_expected_first_plant": poll_expected,
            "watch_changes_behavioral_state": perturbed,
            "confirmed": poll_repeatable and poll_expected and perturbed,
        },
        "input_edge_rule": {
            "classification": "confirmed_by_kick_control_artifact",
            "source": "analysis/phase2_action_behavior.json:controls.kick.trials",
            "constraint": "A held button does not create a fresh-press edge; edge-gated actions require a released frame before the press.",
        },
        "non_regenerable_residuals": [
            {
                "claim": "A11 PC watches shift timing enough for the dropped seed to miss.",
                "status": "observed_not_independently_banked",
                "next": "Add an isolated same-anchor watch/no-watch seed-hit A/B probe if PC-level attribution is needed.",
            },
            {
                "claim": "CachedInterpreter accessLog/write breakpoints did not engage in the A11 repro.",
                "status": "observed_not_independently_banked",
                "next": "Add a fork-level write-watch conformance test before relying on this limitation.",
            },
        ],
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[platform] poll_repeatable={poll_repeatable} expected={poll_expected} watch_perturbed={perturbed}")
    return 0 if doc["execTrace_movie_desynchronization"]["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
