#!/usr/bin/env python3
"""D16_thumper / F03_council_chamber live oracle: what 0x80090BEE really is.

WHY THIS EXISTS
---------------
Both rows carried the binding "Thumper defeat -> 0x80090BEE = 2", and their shared
`next` was "trace 0x80090BEE = 2 consumers into the level-exit transition".  A static
pass (tools/phase4_d16_f03_static.c) says that premise is a category error:

  * 0x80090BEE is the FLAGS halfword of the shared cinematic-camera block at
    0x80090BC0 (+0x2E).  It is written only by the two camera-start functions
    0x8004D9E8 and 0x8004DA94, each from a CALLER-SUPPLIED argument.
  * "2" is therefore not a defeat code -- it is the flags value the Council Chamber
    overlay happens to pass (LEVEL02/LEVEL.BIN, 0x800B4118: `addiu v0,zero,2`).
  * The LEVEL EXIT is a DIFFERENT store, later in the same overlay block:
    `[0x800823A0] = 1` at 0x800B4190 (the goal latch).

OVERLAY IDENTITY IS ASSERTED, NOT ASSUMED
-----------------------------------------
Region A (0x800B39A0) is a SHARED swap buffer: every LEVEL*/LEVEL*.BIN loads at the
same VA, so an overlay address means nothing without knowing which blob is resident.
Reading the defeat code out of the wrong blob is a real failure mode -- this analysis
first attributed it to LEVEL03/LEVEL1.BIN, and the live run disproved that.  So the
first thing this oracle does is hash the resident region-A window and match it against
every candidate blob, and it FAILS if the match is not the expected one.

This oracle checks that account against the real fixture instead of trusting the
disassembly, because a self-consistent static reading is exactly what produced the
wrong binding in the first place.

REGIME -- POLL ONLY, DELIBERATELY
---------------------------------
thumper_boss.movie.json was recorded in the CachedInterpreter era.  Arming ANY CPU
instrumentation (accessLog watch / execTrace / breakpoint) forces
CPUExecutionMode::Interpreter, which desyncs such a movie SILENTLY -- `reproducible`
stays true and the capture comes back plausible but empty.  So this oracle uses
nothing but readMemory, which takes no CPU hook and is safe during replay.

The cost of that choice is honest and recorded in the artifact: polling cannot see a
transition that lasts a single frame.  Every claim this oracle asserts is about a
state that PERSISTS for many frames (the overlay arms a 150-frame timer), so the sampling gap does not carry any of the load.  The one-frame
camera phase hops (0x80090BEC 2->1) are REPORTED if sampled and never asserted.

USAGE
    tools/phase4_d16_f03_oracle.py --port 23660 \
        --movie thumper_boss.movie.json \
        --json analysis/phase4_d16_f03_oracle.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# --- the addresses under test, all re-derived by tools/phase4_d16_f03_static.c ---
CAM_STATE = 0x80090BEC   # cinematic-camera phase   (h)
CAM_FLAGS = 0x80090BEE   # cinematic-camera flags   (h)  <- the row's "defeat flag"
POWER     = 0x800A6590   # power/suppression word   (h)
GOAL      = 0x800823A0   # goal latch = the actual level-exit signal (h)
THUMPER_HP = 0x8009FE72  # Thumper actor record 0x8009FE04 (chunk-31) + 0x6E
CAM_TIMER = 0x80082470   # post-defeat timer the overlay sets to 150
REGION_A  = 0x800B39A0   # shared overlay swap buffer
EXPECT_OVERLAY = "REBUILD/files/LEVEL02/LEVEL.BIN"
DEFEAT_HP_THRESHOLD = 21  # `slti v0,v0,21` at 0x800B4078
SCENE     = 0x80082504   # scene id (u32)


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def launch(port, token, disc, cfg, log, launcher, cwd, mode):
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with Path(log).open("w") as fh:
        subprocess.run([
            "bash", str(launcher), "--execution-mode", mode,
            "--config-dir", str(cfg), "--port", str(port), "--token", token,
            "--disc", str(disc)], cwd=str(cwd), stdout=fh, stderr=fh, check=False)
    text = Path(log).read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-800:])
    return text.split("pid=")[1].split()[0]


def overlay_candidates(root):
    """First 256 bytes of every region-A blob -> its identity."""
    out = {}
    for p in sorted(root.glob("REBUILD/files/LEVEL*/LEVEL*.BIN")):
        b = p.read_bytes()
        out[hashlib.sha256(b[:256]).hexdigest()] = str(p.relative_to(root))
    return out


def sample(c):
    """One coherent read of the whole state tuple.

    0x80090BEC and 0x80090BEE are adjacent, so a single 4-byte read gets both from
    the same instant -- important, because the camera phase and its flags are
    written by the same function within one frame.
    """
    blk = bytes.fromhex(c.call("debugger.readMemory",
                               {"address": "0x%08x" % CAM_STATE, "length": 4})["hex"])
    def rd(addr, n=2):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % addr, "length": n})["hex"])
    return {
        "cam_state": int.from_bytes(blk[0:2], "little"),
        "cam_flags": int.from_bytes(blk[2:4], "little"),
        "power":     int.from_bytes(rd(POWER), "little"),
        "goal":      s16(int.from_bytes(rd(GOAL), "little")),
        "hp":        s16(int.from_bytes(rd(THUMPER_HP), "little")),
        "timer":     s16(int.from_bytes(rd(CAM_TIMER), "little")),
        "scene":     int.from_bytes(rd(SCENE, 4), "little"),
        "ovl":       hashlib.sha256(rd(REGION_A, 256)).hexdigest(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--movie", type=Path, default=ROOT / "thumper_boss.movie.json")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="CachedInterpreter",
                    help="must match how the movie was RECORDED (default matches the "
                         "CachedInterpreter-era thumper fixtures)")
    ap.add_argument("--port", type=int, default=23660)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_d16_f03_oracle.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/d16-oracle")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "rows": ["D16_thumper", "F03_council_chamber"],
        "movie": str(args.movie),
        "disc": str(args.disc),
        "execution_mode": args.execution_mode,
        "regime": "60 Hz (debugger.resume + poll). readMemory ONLY -- no accessLog, no "
                  "execTrace, no breakpoints, because arming any of them forces "
                  "Interpreter and would silently desync this CachedInterpreter-era movie.",
        "sampling_limit": "polling cannot observe a state that lasts a single frame; "
                          "no assertion below depends on one.",
        "addresses": {
            "cam_state": "0x%08x" % CAM_STATE, "cam_flags": "0x%08x" % CAM_FLAGS,
            "power": "0x%08x" % POWER, "goal_latch": "0x%08x" % GOAL,
            "thumper_hp": "0x%08x" % THUMPER_HP, "cam_timer": "0x%08x" % CAM_TIMER,
        },
    }
    trace = []
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(600)

        st = c.call("movie.load", {"path": str(args.movie)})
        out["frames"] = st.get("frame_count")
        out["from_boot"] = bool((st.get("start_state") or {}).get("from_boot"))

        started = c.call("movie.startPlayback", {"load_start_state": True})
        if not started.get("playing"):
            out["error"] = "playback refused: %s" % started
            print(json.dumps(out, indent=1))
            return 1

        out["baseline"] = sample(c)
        c.call("debugger.resume", {})

        began, last_idx, stalls, last_tuple = time.time(), -1, 0, None
        while time.time() - began < args.timeout:
            try:
                s = sample(c)
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception as exc:                     # noqa: BLE001
                out.setdefault("poll_errors", []).append(str(exc))
                time.sleep(0.2)
                continue
            key = (s["cam_state"], s["cam_flags"], s["power"], s["goal"], s["hp"])
            if key != last_tuple:
                trace.append({"i": idx, **s})
                last_tuple = key
            if idx == last_idx:
                stalls += 1
                if stalls >= 40:
                    break
            else:
                stalls = 0
            last_idx = idx

        out["wall_seconds"] = round(time.time() - began, 1)
        out["final_playback_index"] = last_idx
        out["final"] = sample(c)
        out["distinct_states"] = len(trace)
        out["trace"] = trace
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    # ---------------------------------------------------------------- checks --
    checks, failures = {}, []

    def check(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    # ---- overlay identity FIRST: an overlay address is meaningless without it ----
    cands = overlay_candidates(ROOT)
    seen = []
    for t in trace + [out.get("final", {})]:
        h = t.get("ovl")
        if h and (not seen or seen[-1] != h):
            seen.append(h)
    resident = [cands.get(h, "UNRECOGNISED:" + h[:16]) for h in seen]
    out["resident_region_a_overlays"] = resident
    check("resident_overlay_is_expected",
          any(r == EXPECT_OVERLAY for r in resident),
          "region A holds %s during the fight (expected %s); every overlay address in "
          "this analysis is only meaningful given this blob" % (resident, EXPECT_OVERLAY))

    hps = [t["hp"] for t in trace]
    out["hp_min"] = min(hps) if hps else None
    out["hp_max"] = max(hps) if hps else None
    # A fixture that never crosses the threshold proves nothing; report INDETERMINATE
    # rather than let the "after" list go empty and every check vacuously pass.
    crossed = any(h >= DEFEAT_HP_THRESHOLD for h in hps) and any(
        h < DEFEAT_HP_THRESHOLD for h in hps)
    out["hp_crossed_threshold_in_run"] = crossed
    if not crossed:
        out["indeterminate"] = True
        out["indeterminate_reason"] = (
            "Thumper HP (0x8009FE72) did not cross the <%d defeat threshold within this "
            "run (min=%s, max=%s), so the transition was not observed from both sides. "
            "This is the fixture gap both rows already record."
            % (DEFEAT_HP_THRESHOLD, out["hp_min"], out["hp_max"]))
        out["checks"] = checks
        out["pass"] = None
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps({k: out.get(k) for k in
                          ("rows", "hp_crossed_threshold_in_run", "hp_min", "hp_max",
                           "resident_region_a_overlays", "distinct_states",
                           "indeterminate_reason")}, indent=1))
        return 2

    after = [t for t in trace if t["hp"] < DEFEAT_HP_THRESHOLD]
    check("goal_latch_set_on_defeat",
          any(t["goal"] == 1 for t in after),
          "the level-exit signal [0x800823A0] reaches 1 after HP drops below %d"
          % DEFEAT_HP_THRESHOLD)
    check("cam_flags_becomes_2",
          any(t["cam_flags"] & 0x02 for t in after),
          "cinematic-camera flags gains bit 0x02 -- the value the rows called the "
          "'defeat flag'")
    check("power_bit4_set_during_cinematic",
          any(t["power"] & 0x04 for t in after),
          "the camera selector 0x8004EA8C ORs bit 0x04 into 0x800A6590 while the "
          "cinematic runs")
    check("cam_flags_bit0_activates",
          any(t["cam_flags"] & 0x01 for t in after),
          "bit 0x01 (cinematic camera ACTIVE) is set by the selector's case-1 path")

    # ---- what this oracle deliberately does NOT assert ----------------------
    # An earlier revision asserted "the goal latch is observed set while 0x80090BEE is
    # still 0, therefore the exit does not depend on it". That check was UNSOUND and is
    # removed rather than kept as a passing one: sample() issues several sequential RPC
    # reads, so a frame boundary inside one sample yields a TORN tuple, and the first
    # run of this oracle produced exactly that false ordering. Runtime polling cannot
    # order two stores in the same basic block.
    #
    # The ordering is settled statically instead, and is the OPPOSITE of that guess:
    # in LEVEL02/LEVEL.BIN the camera start (jal 0x8004DA94 at 0x800B4138) comes BEFORE
    # the goal-latch store (0x800B4190), in one straight-line block, in the same frame.
    # What makes the exit independent of 0x80090BEE is not ordering but the exhaustive
    # consumer census in tools/phase4_d16_f03_static.c: the ONLY readers of 0x80090BEE
    # are the camera selector 0x8004EA8C and the HUD/letterbox swap in
    # gameplay_state_machine, and none of them reads or writes 0x800823A0, the scene id,
    # or any loader entry point.
    latch_i = next((t["i"] for t in trace if t["goal"] == 1), None)
    flags_i = next((t["i"] for t in trace if t["cam_flags"] & 0x03), None)
    out["first_goal_latch_index"] = latch_i
    out["first_cam_flags_index"] = flags_i
    out["ordering_note"] = (
        "same basic block, same frame: camera start 0x800B4138 precedes the goal-latch "
        "store 0x800B4190. Polling cannot resolve this and does not try to.")

    # ---- but the EXIT ITSELF is observable and is asserted --------------------
    scenes = [t.get("scene") for t in trace] + [out.get("final", {}).get("scene")]
    out["scene_timeline"] = [s for i, s in enumerate(scenes)
                             if s is not None and (i == 0 or s != scenes[i - 1])]
    check("level_exit_actually_completes",
          latch_i is not None and any(s not in (None, 2) for s in scenes[1:]),
          "after the goal latch is set the run leaves scene 2 (timeline %s) -- the "
          "level-exit transition genuinely fires in this fixture"
          % out["scene_timeline"])
    out["checks"] = checks
    out["failures"] = failures or None
    out["pass"] = not failures
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"pass": out["pass"], "failures": failures,
                      "distinct_states": out["distinct_states"],
                      "hp_min": out["hp_min"], "hp_max": out["hp_max"],
                      "first_goal_latch_index": out.get("first_goal_latch_index"),
                      "first_cam_flags_index": out.get("first_cam_flags_index"),
                      "resident_region_a_overlays":
                          out.get("resident_region_a_overlays")}, indent=1))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
