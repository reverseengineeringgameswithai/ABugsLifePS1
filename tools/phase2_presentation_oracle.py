#!/usr/bin/env python3
"""Phase-2 presentation baseline: deterministic GPU frame hashes + GPU/CD state
at every pristine identity anchor.

Per anchor: load the hash-pinned save paused, capture the displayed framebuffer
twice via gpu.frameSnapshot (paused captures are documented byte-identical —
the double capture PROVES determinism per anchor), record its sha256, GPU status
(GPUSTAT/draw mode/CRTC), and CD-ROM/DMA state (XA/audio streaming ownership).
These hashes are the differential presentation mask for future builds: a
reconstructed/diagnostic image loading the same anchor must reproduce the same
displayed frame byte-for-byte.

Usage: python3 tools/phase2_presentation_oracle.py [--port 23472]
Output: analysis/phase2_presentation_baseline.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))

from live_session_provenance import (inspect_state_before_load,
                                     verified_media_identity)

ANCHORS = [
    ("training", "phase3_pristine_training_gameplay_i5.sav"),
    ("stage01_anthill", "level01.sav"),
    ("stage02_tunnels", "level02.sav"),
    ("stage03_council_chamber", "level03.sav"),
    ("stage04_cliffside_canyon", "level04.sav"),
    ("stage05_riverbed_run", "level05.sav"),
    ("stage06_birdnest", "level_06.sav"),
    ("stage07_city_entrance", "level_07.sav"),
    ("stage08_city_square", "level_08.sav"),
    ("stage09_bug_bar", "level_09.sav"),
    ("stage10_clover_forest", "level_10.sav"),
    ("stage11_the_tree", "level_11.sav"),
    ("stage12_battle_arena", "level_12.sav"),
    ("stage13_anthill_two", "level_13.sav"),
    ("stage14_riverbed_flight", "level_14.sav"),
    ("stage15_canyon_showdown", "level_15.sav"),
    ("bonus1_spiders", "movies/Bonus_Level_01.movie.sav"),
    ("bonus2_mushrooms", "movies/Bonus_Level_02.movie.sav"),
    ("bonus3_grasshoppers", "movies/Bonus_Level_03.movie.sav"),
]


def payload_sha256(result: dict) -> str:
    for key in ("data", "png", "base64", "image"):
        if isinstance(result.get(key), str):
            return hashlib.sha256(base64.b64decode(result[key])).hexdigest()
    raise KeyError(f"no image payload in frameSnapshot result: {list(result)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)

    anchors = {}
    for label, sav in ANCHORS:
        path = ROOT / sav
        if not path.exists():
            anchors[label] = {"error": f"anchor missing: {sav}"}
            continue
        for method in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(method, {})
            except Exception:
                pass
        inspect_state_before_load(c, path, media_identity)
        r = c.call("emulator.loadState", {"path": str(path), "pause_after_load": True})
        if not r.get("loaded"):
            anchors[label] = {"error": f"loadState: {r}"}
            continue
        snap1 = c.call("gpu.frameSnapshot", {"buffer": "displayed", "format": "raw16"})
        snap2 = c.call("gpu.frameSnapshot", {"buffer": "displayed", "format": "raw16"})
        h1, h2 = payload_sha256(snap1), payload_sha256(snap2)
        gpu = c.call("gpu.getStatus", {})
        cd = c.call("emulator.getCdromState", {})
        dma = c.call("emulator.getDmaState", {})
        anchors[label] = {
            "save": sav,
            "frame_sha256": h1,
            "deterministic_double_capture": h1 == h2,
            "frame_meta": {k: snap1.get(k) for k in ("width", "height", "format", "buffer")
                           if k in snap1},
            "gpu_status": {k: gpu.get(k) for k in sorted(gpu) if not isinstance(gpu[k], (list, dict))},
            "cdrom": {k: cd.get(k) for k in sorted(cd) if not isinstance(cd[k], (list, dict))},
            "dma_channels_active": sum(
                1 for ch in (dma.get("channels") or []) if isinstance(ch, dict) and ch.get("busy")),
        }
        print(f"[presentation] {label}: frame {h1[:12]}… deterministic={h1 == h2}")

    doc = {
        "_comment": "Phase-2 presentation baseline: per-anchor displayed-frame sha256 "
                    "(double-captured to prove determinism) + GPU/CD/DMA state on the "
                    "pristine image. A future build loading the same anchor must "
                    "reproduce the frame hash. Regenerate: tools/phase2_presentation_oracle.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "anchors": anchors,
    }
    out = ROOT / "analysis" / "phase2_presentation_baseline.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    ok = sum(1 for a in anchors.values() if a.get("deterministic_double_capture"))
    print(f"[presentation] wrote {out}: {ok}/{len(anchors)} anchors deterministic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
