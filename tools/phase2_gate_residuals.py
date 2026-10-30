#!/usr/bin/env python3
"""Phase-2 gate residuals: audio oracle, in-motion presentation, camera-lock
samples, cross-class death matrix, multi-minute soak.

Closes the residual exit-gate items identified by external review:

  audio_baseline     spu.status at every identity anchor (SPUCNT/SPUSTAT + all 24
                     voices: on/pitch/volumes/addresses/ADSR phase), double-captured
                     paused to prove determinism, plus a 120-frame spu.trace event
                     window (key-on/off counts). Voice PITCH fields are the direct
                     sentinel for the high-pitched-audio regression class; XA/CD
                     state alone was only a proxy.
  motion_presentation LEVEL03 movie replayed TWICE, displayed-frame sha256 at fixed
                     movie frames — the in-motion presentation oracle (frame-anchored,
                     deterministic under the repro config).
  camera_lock        the two native R1 camera-lock instances (LEVEL15 movie) sampled
                     at -15/+2/+12/+32 — the class the first action pass missed.
  death_matrix       contact-death (hp:=0, teleport onto censused actor records until
                     a real hit lands) across stage CLASSES: tunnels(02, already in
                     the lifecycle oracle), boss arena(03), city(07), tree(11).
  long_soak          3 emulated minutes idle per anchor (quiet stage01 + empty-roster
                     bug bar 09), chunked, guest-alive/scene-stable checks.

Requires the REPRO instance (movies replay 1:1 only there).
Usage: python3 tools/phase2_gate_residuals.py [--port 23472]
Output: analysis/phase2_gate_residuals.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))

from live_session_provenance import (inspect_state_before_load,
                                     verified_media_identity)
from phase2_compare import validate_repro_config

IDENTITY_ANCHORS = [
    ("training", "phase3_pristine_training_gameplay_i5.sav"),
    ("stage01_anthill", "level01.sav"), ("stage02_tunnels", "level02.sav"),
    ("stage03_council_chamber", "level03.sav"),
    ("stage04_cliffside_canyon", "level04.sav"),
    ("stage05_riverbed_run", "level05.sav"), ("stage06_birdnest", "level_06.sav"),
    ("stage07_city_entrance", "level_07.sav"), ("stage08_city_square", "level_08.sav"),
    ("stage09_bug_bar", "level_09.sav"), ("stage10_clover_forest", "level_10.sav"),
    ("stage11_the_tree", "level_11.sav"), ("stage12_battle_arena", "level_12.sav"),
    ("stage13_anthill_two", "level_13.sav"),
    ("stage14_riverbed_flight", "level_14.sav"),
    ("stage15_canyon_showdown", "level_15.sav"),
    ("bonus1_spiders", "movies/Bonus_Level_01.movie.sav"),
    ("bonus2_mushrooms", "movies/Bonus_Level_02.movie.sav"),
    ("bonus3_grasshoppers", "movies/Bonus_Level_03.movie.sav"),
]
DEATH_ANCHORS = [("stage03_boss_arena", "level03.sav"),
                 ("stage07_city", "level_07.sav"),
                 ("stage11_tree", "level_11.sav")]
MOTION_MOVIE = "movies/go_to_end/LEVEL03.movie.json"
MOTION_FRAMES = list(range(5000, 5601, 100))
SOAK_ANCHORS = ["level01.sav", "level_09.sav"]
SOAK_FRAMES, SOAK_CHUNK = 10800, 600   # 3 emulated minutes

SNAPSHOT_FIELDS = [
    ("scene_id", 0x80082504, "u32"),
    ("player_x", 0x800A6500, "s32"), ("player_y", 0x800A6504, "s32"),
    ("player_z", 0x800A6508, "s32"),
    ("health_true", 0x800A6594, "s16"), ("lives", 0x800A65A0, "u8"),
]


def sha_payload(result: dict) -> str:
    for key in ("data", "png", "base64", "image"):
        if isinstance(result.get(key), str):
            return hashlib.sha256(base64.b64decode(result[key])).hexdigest()
    raise KeyError(f"no payload: {list(result)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--repro-config-dir", required=True,
                    help="dedicated config created by tools/launch_repro_playback.sh")
    args = ap.parse_args()
    try:
        repro_profile = validate_repro_config(Path(args.repro_config_dir))
    except ValueError as exc:
        raise SystemExit(f"REPRO PROFILE GUARD: {exc}")

    from duckstation_debug_client import DebuggerClient

    state = {}

    def connect():
        cli = DebuggerClient("127.0.0.1", args.port, "ws")
        cli.authenticate(args.token)
        cli.transport.sock.settimeout(600)
        state["cli"] = cli

    connect()

    class _Reconnecting:
        """Long advances can outlive the WS session while the emulator keeps
        going — reconnect, confirm the guest, re-pause, retry once (skill rule)."""
        def call(self, method, params, timeout=None):
            kw = {"timeout": timeout} if timeout else {}
            try:
                return state["cli"].call(method, params, **kw)
            except (ConnectionError, OSError):
                connect()
                st = state["cli"].call("debugger.status", {})
                assert st.get("valid", True), f"guest dead after reconnect: {st}"
                if method == "emulator.advanceFrames":
                    state["cli"].call("debugger.pause", {})
                    return {"reconnected": True}
                return state["cli"].call(method, params, **kw)
    c = _Reconnecting()

    def rd(addr, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % addr, "length": n})["hex"])

    def snapshot():
        snap = {}
        for name, addr, width in SNAPSHOT_FIELDS:
            raw = rd(addr, {"u8": 1, "s16": 2, "u32": 4, "s32": 4}[width])
            fmt = {"u8": "<B", "s16": "<h", "u32": "<I", "s32": "<i"}[width]
            snap[name] = struct.unpack(fmt, raw)[0]
        return snap

    def stop_movie():
        for m in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(m, {})
            except Exception:
                pass

    def load(sav):
        stop_movie()
        inspect_state_before_load(c, ROOT / sav, media_identity)
        r = c.call("emulator.loadState", {"path": str(ROOT / sav),
                                          "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        c.call("emulator.clearControllerState", {"port": 0})

    def wr32(a, v):
        c.call("debugger.writeU32", {"address": "0x%08x" % a, "value": v & 0xFFFFFFFF})

    def voice_digest(s):
        keep = []
        for v in s["voices"]:
            keep.append({k: v.get(k) for k in
                         ("index", "on", "pitch", "left_volume", "right_volume",
                          "adsr_volume", "phase", "start_address", "current_address")})
        return keep

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)
    out: dict = {}

    # Movie lanes MUST run before any loadState call. Save states restore their
    # embedded memory card, while the from-boot recordings require the launcher's
    # hash-matched seeded card. Reversing this order silently desynchronizes replay.
    # ---- in-motion presentation ---------------------------------------------
    runs = []
    for rep in range(2):
        stop_movie()
        r = c.call("movie.load", {"path": str(ROOT / MOTION_MOVIE)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        assert st.get("playing") and st.get("reproducible")
        # startPlayback power-cycles a from-boot movie and leaves it running.
        # Freeze it before calculating the first delta or the reset-to-RPC race
        # can consume a few uncounted frames (observed: 4 on the first replay).
        c.call("debugger.pause", {})
        hashes = {}
        for f in MOTION_FRAMES:
            c.call("movie.advanceToFrame",
                   {"frame": f, "max_frames": r["frame_count"] + 700}, timeout=900)
            snap = c.call("gpu.frameSnapshot", {"buffer": "displayed", "format": "raw16"})
            hashes[str(f)] = sha_payload(snap)
        runs.append(hashes)
        print(f"[motion] replay {rep + 1}: {len(hashes)} frame hashes")
    out["motion_presentation"] = {
        "movie": MOTION_MOVIE, "frames": MOTION_FRAMES,
        "replay1": runs[0], "replay2": runs[1],
        "deterministic_across_replays": runs[0] == runs[1],
        "distinct_frames": len(set(runs[0].values())),
    }
    print(f"[motion] deterministic={runs[0] == runs[1]} "
          f"distinct={len(set(runs[0].values()))}/{len(MOTION_FRAMES)}")

    # ---- camera-lock native samples ------------------------------------------
    windows = json.loads((ROOT / "analysis" / "phase2_action_windows.json").read_text())
    samples = []
    for lock_movie, mv in windows["movies"].items():
        lock_frames = mv["events"]["camera_lock"].get("in_stage_frames") or []
        if not lock_frames:
            continue
        stop_movie()
        r = c.call("movie.load", {"path": str(ROOT / lock_movie)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        assert st.get("playing")
        c.call("debugger.pause", {})
        for ef in sorted(lock_frames)[:2]:
            series = {}
            for off in (-15, 2, 12, 32):
                target = ef + off
                cur = c.call("debugger.status", {}).get("frame_number")
                if cur is not None and target < cur:
                    continue
                c.call("movie.advanceToFrame",
                       {"frame": target, "max_frames": r["frame_count"] + 700},
                       timeout=900)
                series[f"{off:+d}"] = snapshot()
            samples.append({"movie": lock_movie, "event_frame": ef,
                            "snapshots": series})
    out["camera_lock_samples"] = samples
    print(f"[camera_lock] sampled {len(samples)} native R1 instances")

    # ---- audio baseline ------------------------------------------------------
    audio = {}
    for label, sav in IDENTITY_ANCHORS:
        load(sav)
        s1, s2 = c.call("spu.status", {}), c.call("spu.status", {})
        det = voice_digest(s1) == voice_digest(s2)
        c.call("spu.trace.start", {"clear": True})
        c.call("emulator.advanceFrames", {"frames": 120})
        c.call("debugger.pause", {})
        ev = c.call("spu.events.get", {"limit": 2000})
        c.call("spu.trace.stop", {})
        events = ev.get("events", [])
        kinds: dict = {}
        voices_touched = set()
        for e in events:
            kinds[e.get("type", "?")] = kinds.get(e.get("type", "?"), 0) + 1
            if e.get("voice") is not None:
                voices_touched.add(e["voice"])
        audio[label] = {
            "save": sav,
            "control": s1.get("control"), "status": s1.get("status"),
            "voices_on": [v["index"] for v in s1["voices"] if v.get("on")],
            "voice_pitches_on": {str(v["index"]): v["pitch"]
                                 for v in s1["voices"] if v.get("on")},
            "voices": voice_digest(s1),
            "deterministic_double_capture": det,
            "events_120f": {"counts": kinds,
                            "voices_touched": sorted(voices_touched)},
        }
        print(f"[audio] {label}: on={audio[label]['voices_on']} "
              f"events={kinds} det={det}")
    out["audio_baseline"] = audio

    # ---- death matrix across stage classes -----------------------------------
    matrix = {}
    for label, sav in DEATH_ANCHORS:
        result = {"anchor": sav}
        load(sav)
        buf = rd(0x8009FE04, 0x84 * 40)
        recs = []
        for i in range(40):
            rid, x, y, z = struct.unpack_from("<Iiii", buf, i * 0x84)
            if (rid == 0 and x == 0 and y == 0 and z == 0) or rid > 0x2000 or abs(x) > 0x400000:
                break
            recs.append((i, rid, x, y, z))
        for i, rid, x, y, z in recs[:14]:
            load(sav)
            c.call("debugger.writeU16", {"address": "0x800A6594", "value": 0})
            for addr, val in ((0x800A6500, x), (0x800A6510, x),
                              (0x800A6504, y), (0x800A6514, y),
                              (0x800A6508, z), (0x800A6518, z)):
                wr32(addr, val)
            before = snapshot()
            death = None
            for _ in range(6):
                c.call("emulator.advanceFrames", {"frames": 60})
                c.call("debugger.pause", {})
                s = snapshot()
                if s["lives"] == before["lives"] - 1:
                    death = s
                    break
            if death:
                result.update({
                    "death_via_record": {"index": i, "id": rid},
                    "respawn_state": death,
                    "respawn_health": death["health_true"],
                    "lives_decremented": True,
                })
                break
        else:
            result["note"] = ("no contact damage from the first records at this "
                              "anchor — actor ids here may be non-hostile; "
                              "documented, not silent")
        matrix[label] = result
        print(f"[death_matrix] {label}: {result.get('death_via_record', result.get('note'))}")
    out["death_matrix"] = matrix

    # ---- long soak ------------------------------------------------------------
    soak = {}
    for sav in SOAK_ANCHORS:
        load(sav)
        base = snapshot()
        alive, chunks = True, 0
        for _ in range(SOAK_FRAMES // SOAK_CHUNK):
            c.call("emulator.advanceFrames", {"frames": SOAK_CHUNK})
            c.call("debugger.pause", {})
            s = snapshot()
            chunks += 1
            if s["scene_id"] != base["scene_id"]:
                alive = False
                break
        soak[sav] = {"frames": chunks * SOAK_CHUNK,
                     "emulated_minutes": round(chunks * SOAK_CHUNK / 3600, 2),
                     "guest_alive_in_scene": alive, "final": snapshot()}
        print(f"[long_soak] {sav}: {soak[sav]['emulated_minutes']}min alive={alive}")
    out["long_soak"] = soak

    doc = {
        "_comment": "Phase-2 gate residuals (audio oracle incl. voice pitches, "
                    "in-motion presentation, camera-lock samples, cross-class death "
                    "matrix, multi-minute soak). Regenerate: "
                    "tools/phase2_gate_residuals.py on the repro instance.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "repro_profile": repro_profile,
        **out,
    }
    path = ROOT / "analysis" / "phase2_gate_residuals.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[residuals] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
