#!/usr/bin/env python3
"""Freshly attribute the F01 code-3 request store with current access-log fields.

The retained campaign sweep kept only the compatibility ``pc`` field.  On the
runtime used for that sweep it named store PC + 4, so the code-3 observation was
inferred by subtracting four.  Current DuckStation exposes both ``reported_pc``
and ``instruction_pc``.  This probe filters the request-word write watch to the
small dispatch range and retains both fields plus the instruction word.

Launch an isolated Interpreter instance with ``tools/launch_repro_playback.sh``
before running this tool.  The default LEVEL02 movie is state-anchored and is
known to exercise the code-3 arm; no memory is written or perturbed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

from phase4_f01_evidence import pristine_executable_path  # noqa: E402

MOVIE = ROOT / "movies/Phase4/Interpreter/100% Runs/LEVEL02_Tunnels.movie.json"
REQUEST_WORD = 0x800823A0
CODE2_STORE = 0x800496D8
CODE3_STORE = 0x800496F8
FILTER_END = 0x800496FC
EXPECTED_STORE_WORD = 0xA42223A0
CHUNK = 5000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def captured_word_from_image(address: int) -> int:
    image = pristine_executable_path().read_bytes()
    text_address = struct.unpack_from("<I", image, 0x18)[0]
    return struct.unpack_from("<I", image, address - text_address + 0x800)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--movie", type=Path, default=MOVIE)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    from duckstation_debug_client import DebuggerClient

    movie = args.movie.resolve()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(3600)

    media_before = client.call("emulator.getMediaInfo", {})
    mode_before = client.call("debugger.status", {}).get("execution_mode", {})
    if media_before.get("game_serial") != "SCUS-94288":
        raise SystemExit(f"wrong media: {media_before}")
    if mode_before.get("effective") != "Interpreter":
        raise SystemExit(f"need Interpreter, got {mode_before.get('effective')}")

    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    client.call("accessLog.clear", {})
    loaded = client.call("movie.load", {"path": str(movie)})
    frames = int(loaded["frame_count"])
    started = client.call("movie.startPlayback", {"load_start_state": True})
    if not started.get("playing") or not started.get("reproducible"):
        raise SystemExit(f"playback not reproducible: {started}")

    # startPlayback loads the state and clears non-halting watches, so arm only
    # after it returns.  The filter accepts both the actual store PCs and the
    # legacy callback's possible +4 report for code 3.
    watch = client.call("accessLog.addWatch", {
        "address": f"0x{REQUEST_WORD:08x}",
        "length": 2,
        "type": "write",
        "max_events": 100,
        "label": "f01_code2_code3_request_store",
        "filter": {
            "pc": {"min": f"0x{CODE2_STORE:08x}",
                   "max": f"0x{FILTER_END:08x}"}
        },
    })

    current = 0
    while current < frames:
        current = min(current + CHUNK, frames)
        result = client.call(
            "movie.resumeUntilMovieFrame",
            {"frame": current, "max_frames": frames + 900},
            timeout=3600,
        )
        execution = result.get("execution", {})
        if not execution.get("completed"):
            raise SystemExit(
                f"early stop @{current}: {execution.get('stop_reason')} "
                f"{execution.get('stop_details')}"
            )

    trace = client.call("accessLog.get", {
        "watch_id": watch["watch_id"], "offset": 0, "limit": 10000,
    })
    media_after = client.call("emulator.getMediaInfo", {})
    mode_after = client.call("debugger.status", {}).get("execution_mode", {})
    client.call("accessLog.clear", {})

    events = []
    for event in trace.get("events", []):
        events.append({key: event.get(key) for key in (
            "frame", "cycle", "pc", "reported_pc", "instruction_pc",
            "instruction_word", "instruction", "address", "type", "width",
            "value", "new_value", "watch_id",
        )})

    code3 = [event for event in events
             if str(event.get("instruction_pc", "")).lower() ==
             f"0x{CODE3_STORE:08x}"]
    assertions = {
        "media_serial_stable": (
            media_before.get("game_serial") == media_after.get("game_serial") ==
            "SCUS-94288"
        ),
        "interpreter_before_and_after": (
            mode_before.get("effective") == mode_after.get("effective") ==
            "Interpreter"
        ),
        "trace_not_truncated": trace.get("truncated") is False,
        "exactly_one_code3_store": len(code3) == 1,
        "code3_instruction_word_matches_pristine": (
            len(code3) == 1 and
            int(str(code3[0].get("instruction_word")), 16) ==
            captured_word_from_image(CODE3_STORE) == EXPECTED_STORE_WORD
        ),
        "code3_wrote_request_one": (
            len(code3) == 1 and code3[0].get("new_value") == 1
        ),
    }

    report = {
        "schema": "abl-phase4-f01-write-watch-pc-probe/1",
        "question": ("Does a fresh access watch identify the code-3 request "
                     "write by instruction_pc without subtracting four?"),
        "movie": str(movie),
        "movie_sha256": sha256_file(movie),
        "frames": frames,
        "media_before": media_before,
        "media_after": media_after,
        "execution_mode_before": mode_before,
        "execution_mode_after": mode_after,
        "watch": watch,
        "events": events,
        "assertions": assertions,
        "all_passed": all(assertions.values()),
        "conclusion": ("instruction_pc directly names 0x800496f8; compatibility "
                       "pc/reporting behavior is not used for attribution"),
    }
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"[f01-pc] events={len(events)} code3={len(code3)} "
          f"passed={report['all_passed']} wrote {args.out}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
