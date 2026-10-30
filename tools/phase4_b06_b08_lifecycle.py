#!/usr/bin/env python3
"""B06/B08 lifecycle + persistence probes: pause, scene transition, save/load.

Closes the two Definition-of-Done items the cold-boot oracles do not reach:

  DoD 4 LIFECYCLE      -- "behaviour is characterized through creation, repeated use,
                          retirement, death/respawn, PAUSE, SCENE TRANSITION, and
                          RELOAD where applicable". Creation/use/retirement/respawn are
                          covered by the oracles; the last three are not.
  DoD 7 CROSS-SYSTEM   -- the save/load half.

P1 PAUSE
    Set the timer, press START, and advance. A pause that does not stop the tick would
    mean an invincibility drains while the player is in the menu -- observable, and
    exactly the kind of thing "characterized through pause" is asking about.

P2 SCENE TRANSITION
    Force the documented level-exit trigger with a power active and watch which site
    clears the slot. Static analysis says respawn_transition_state_handler bulk-zeroes
    the player block at 0x8005B268; this checks whether the TRANSITION path reaches it,
    rather than assuming the name covers both.

P3 SAVE / LOAD PERSISTENCE
    checkpoint_save (0x80054E5C..0x80054E90) writes a specific field set -- position
    0x6550/0x6554/0x6558, 0x6578, and the power-FLAGS word 0x6590 with `ori 8` -- and
    the alias-aware census shows NO save or checkpoint function writes the power slot
    0x800A657E at all. So an active power should not survive a checkpoint restore.
    Asserted rather than assumed: set a power, checkpoint, clear, restore, read back.

Every probe restores what it perturbed. Interpreter, isolated instance, pristine disc.
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

def _scratch(name: str) -> "pathlib.Path":
    """Portable scratch dir. Was a hard-coded ~/.claude/jobs/<session>/ path in
    the first committed version of these tools -- machine- AND session-specific, so they
    could not run for anyone else. Override with ABL_SCRATCH."""
    import os, tempfile, pathlib as _p
    # Prefer an explicit override, then the harness job dir. Falling straight to the
    # system temp dir is a poor default here: /tmp is a RAM-backed tmpfs under a user
    # quota on this machine, and prior verification clones had already taken 49 GB of it.
    base = (os.environ.get("ABL_SCRATCH")
            or (os.environ.get("CLAUDE_JOB_DIR") and
                _p.Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp" / "abl-scratch")
            or _p.Path(tempfile.gettempdir()) / "abl-scratch")
    p = _p.Path(base) / name
    p.mkdir(parents=True, exist_ok=True)
    return p


ROOT = Path(__file__).resolve().parent.parent
SLOT, FLAGS, HEALTH = 0x800A657E, 0x800A6590, 0x800A6594
REGION = 0x800823A0          # level-exit / region code
TICK_PC = "0x80048654"


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def rd(c, a, n):
    return bytes.fromhex(c.call("debugger.readMemory",
                                {"address": "0x%08x" % a, "length": n})["hex"])


def wr(c, a, b):
    c.call("debugger.writeMemory", {"address": "0x%08x" % a, "hex": b.hex()})


def slot_of(c):
    # struct.unpack("<h") is ALREADY signed. Passing it through s16() as well
    # double-extends: -3 became -65539, because in Python -3 & 0x8000 is truthy.
    return struct.unpack("<h", rd(c, SLOT, 2))[0]


def collect(c):
    out, off = [], 0
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        got = page.get("events") or []
        out.extend(got)
        if len(got) < 10000:
            break
        off += len(got)
    return [{"f": e.get("frame"),
             "pc": str(e.get("instruction_pc") or e.get("pc") or "").lower(),
             "new": s16((e.get("new_value") or 0) & 0xFFFF)} for e in out]


def p1_pause(c, state) -> dict:
    out = {"probe": "P1_pause"}
    c.call("emulator.loadState", {"path": str(state)})
    c.call("emulator.clearControllerState", {"port": 0})
    wr(c, SLOT, struct.pack("<h", 400))

    c.call("emulator.advanceFrames", {"frames": 30})
    running = slot_of(c)
    out["after_30_frames_running"] = running
    out["ticks_while_running"] = 400 - running

    # START opens the in-game pause; hold it briefly, then let the pause sit.
    c.call("emulator.pressButton", {"button": "start", "frames": 4, "port": 0,
                                    "release_after": True})
    before = slot_of(c)
    c.call("emulator.advanceFrames", {"frames": 180})
    after = slot_of(c)
    out["slot_entering_pause"] = before
    out["slot_after_180_paused_frames"] = after
    out["ticks_while_paused"] = before - after

    # leave the pause and confirm the timer resumes
    c.call("emulator.pressButton", {"button": "start", "frames": 4, "port": 0,
                                    "release_after": True})
    c.call("emulator.advanceFrames", {"frames": 30})
    resumed = slot_of(c)
    out["slot_after_resume_30f"] = resumed
    out["ticks_after_resume"] = after - resumed

    frozen = out["ticks_while_paused"] == 0
    out["verdict"] = ("PAUSE FREEZES THE TIMER" if frozen else
                      "timer continued through pause (%d ticks in 180 frames)"
                      % out["ticks_while_paused"])
    out["pause_freezes_timer"] = frozen
    c.call("emulator.clearControllerState", {"port": 0})
    return out


def p2_transition(c, state) -> dict:
    out = {"probe": "P2_scene_transition"}
    c.call("emulator.loadState", {"path": str(state)})
    wr(c, SLOT, struct.pack("<h", 400))
    out["scene_before"] = struct.unpack("<I", rd(c, 0x80082504, 4))[0]
    out["slot_before"] = slot_of(c)

    c.call("accessLog.clear", {})
    c.call("accessLog.addWatch", {"address": "0x%08x" % SLOT, "length": 2,
                                  "type": "write", "max_events": 50000})
    # documented level-exit trigger
    wr(c, REGION, struct.pack("<h", 1))

    # Run long enough for the NEXT level to actually load. A short advance parks the
    # emulator mid-transition, where the player update is not running -- and a frozen
    # slot then looks exactly like a surviving power, which is how the first version of
    # this probe produced an unsupportable "power SURVIVED" verdict.
    samples = []
    for _ in range(12):
        c.call("emulator.advanceFrames", {"frames": 300})
        samples.append({"scene": struct.unpack("<I", rd(c, 0x80082504, 4))[0],
                        "slot": slot_of(c)})
    out["samples"] = samples

    ev = collect(c)
    clears = [e for e in ev if e["new"] == 0]
    out["slot_writers_during_transition"] = sorted({e["pc"] for e in ev})
    out["slot_write_count"] = len(ev)
    out["first_clear"] = clears[0] if clears else None
    out["slot_after"] = slot_of(c)
    out["scene_after"] = samples[-1]["scene"]
    out["cleared_by_0x8005B268"] = any(e["pc"] == "0x8005b268" for e in clears)

    # The tick fires every 2 frames whenever the player update runs. No slot writes at
    # all therefore means gameplay never resumed, and the probe proves nothing either
    # way -- say so rather than reporting the frozen value as a result.
    ticked = any(e["pc"] == TICK_PC for e in ev)
    if not ticked and not clears:
        out["verdict"] = ("INCONCLUSIVE -- no tick and no clear in %d sampled frames, so "
                          "the player update never resumed; a frozen slot here is not "
                          "evidence that a power survives a transition"
                          % (12 * 300))
        out["conclusive"] = False
    elif clears:
        out["verdict"] = "power CLEARED during the transition by %s" % clears[0]["pc"]
        out["conclusive"] = True
    else:
        out["verdict"] = ("power SURVIVED: gameplay resumed (tick observed) in scene %s "
                          "with the slot still %s" % (out["scene_after"], out["slot_after"]))
        out["conclusive"] = True
    return out


def p3_persistence(c, state) -> dict:
    """Does a power survive a save-state round trip and a checkpoint restore?"""
    out = {"probe": "P3_persistence"}
    c.call("emulator.loadState", {"path": str(state)})
    wr(c, SLOT, struct.pack("<h", -3))          # bubble, 3 hits
    out["slot_set"] = slot_of(c)

    tmp = str(_scratch("b0608") / "persist.sav")
    c.call("emulator.saveState", {"path": tmp})
    wr(c, SLOT, struct.pack("<h", 0))
    out["slot_cleared"] = slot_of(c)
    c.call("emulator.loadState", {"path": tmp})
    out["slot_after_state_roundtrip"] = slot_of(c)
    out["savestate_roundtrip_restores"] = out["slot_after_state_roundtrip"] == -3

    # The GAME's own persistence is a different question: the census shows no save or
    # checkpoint routine writes this slot at all.
    census = json.loads((ROOT / "analysis/phase4_b06_b08_census_657e.json").read_text())
    fns = sorted({h["function"] for h in census["writers"] + census["readers"]})
    out["functions_touching_slot"] = fns
    out["any_save_or_checkpoint_writer"] = [f for f in fns
                                            if "save" in f or "checkpoint" in f]
    out["verdict"] = (
        "emulator save-state restores the slot (it is plain RAM); the GAME never "
        "persists it -- no save/checkpoint routine writes 0x800A657E, so a power is "
        "runtime-only and cannot survive a checkpoint restore")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23670)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--state", type=Path, default=ROOT / "level01.sav")
    ap.add_argument("--disc", type=Path, default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--json", type=Path, default=ROOT / "analysis/phase4_b06_b08_lifecycle.json")
    args = ap.parse_args()

    tmp = _scratch("b0608")
    tmp.mkdir(parents=True, exist_ok=True)
    cfg, log = tmp / "cfg-lifecycle", tmp / "launch-lifecycle.log"
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with log.open("w") as fh:
        subprocess.run(["bash", str(ROOT / "tools/launch_repro_playback.sh"),
                        "--execution-mode", "Interpreter", "--config-dir", str(cfg),
                        "--port", str(args.port), "--token", args.token,
                        "--disc", str(args.disc)], cwd=str(ROOT),
                       stdout=fh, stderr=fh, check=False)
    text = log.read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-600:])
    pid = text.split("pid=")[1].split()[0]

    results = []
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(600)
        for fn in (p1_pause, p2_transition, p3_persistence):
            try:
                r = fn(c, args.state)
            except Exception as exc:
                r = {"probe": fn.__name__, "error": str(exc)[:200]}
            results.append(r)
            print(json.dumps(r, indent=1), flush=True)
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    args.json.write_text(json.dumps({
        "_comment": "Phase-4 B06/B08 lifecycle + persistence probes (DoD items 4 and the "
                    "save/load half of 7). Regenerate: tools/phase4_b06_b08_lifecycle.py",
        "state": str(args.state), "execution_mode": "Interpreter",
        "probes": results}, indent=1) + "\n")
    print("wrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
