#!/usr/bin/env python3
"""B06/B08: runtime audio-dispatch assertion (DoD 7) and scene transition (DoD 4).

A1 AUDIO -- NATURAL
    The B06 grant calls sfx_dispatch(65) at 0x800588C0, guarded by `bgtz` at
    0x800588B8 so it fires only when the slot is not already positive. Until now that
    was bound from disassembly alone. Replay the cold-boot movie with an exec trace
    over the grant block and confirm the call actually executes when the pickup is
    collected.

A2 AUDIO -- THE GUARD
    The interesting half. Set the slot positive immediately before the grant: the
    store must STILL write 400 (both arms of the branch reach it), while the
    sfx_dispatch call must be SKIPPED. That is a behavioural difference the
    disassembly predicts and nothing has yet observed.

T1 SCENE TRANSITION
    The earlier probe forced the region code from mid-level and parked the emulator
    in a state where the player update never resumed, so it proved nothing. This
    starts from a save taken AT the end of a stage, where the transition is the
    natural next thing to happen, and watches whether the power survives into the
    next loaded scene or is cleared -- and by which site.

    It reports INCONCLUSIVE unless gameplay demonstrably resumes (the tick fires),
    because a frozen slot during a load is not evidence either way.
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
SLOT, SCENE = 0x800A657E, 0x80082504
GRANT_STORE = "0x800588d0"
SFX_CALL = "0x800588c0"        # jal sfx_dispatch, delay slot a0 = 65
GUARD = "0x800588b8"           # bgtz -- skips the sfx call when already positive
TICK_PC = "0x80048654"
RESPAWN_CLEAR = "0x8005b268"


def rd(c, a, n):
    return bytes.fromhex(c.call("debugger.readMemory",
                                {"address": "0x%08x" % a, "length": n})["hex"])


def wr(c, a, b):
    c.call("debugger.writeMemory", {"address": "0x%08x" % a, "hex": b.hex()})


def slot_of(c):
    return struct.unpack("<h", rd(c, SLOT, 2))[0]


def scene_of(c):
    return struct.unpack("<I", rd(c, SCENE, 4))[0]


def exec_counts(c, keys):
    counts = {k: 0 for k in keys}
    total, off = 0, 0
    while True:
        page = c.call("execTrace.get", {"offset": off, "limit": 10000})
        got = page.get("events") or []
        for e in got:
            pc = str(e.get("pc") or e.get("address") or "").lower()
            if pc in counts:
                counts[pc] += 1
        total += len(got)
        if len(got) < 10000:
            break
        off += len(got)
    return counts, total


def play_to_end(c, timeout=400):
    c.call("debugger.resume", {})
    began, last, stalls = time.time(), -1, 0
    while time.time() - began < timeout:
        time.sleep(1.5)
        try:
            idx = c.call("movie.status", {}).get("playback_index")
        except Exception:
            idx = last
        if idx == last:
            stalls += 1
            if stalls >= 5:
                break
        else:
            stalls = 0
        last = idx
    return last


def audio_probe(c, movie, poke_before_grant=None) -> dict:
    """Replay the cold-boot B06 movie; count the sfx call vs the grant store."""
    tag = "A2_guard" if poke_before_grant is not None else "A1_natural"
    out = {"probe": tag, "movie": Path(movie).name}
    n = c.call("movie.load", {"path": str(movie)})["frame_count"]
    if not c.call("movie.startPlayback", {"load_start_state": True}).get("playing"):
        return {**out, "error": "playback refused"}
    c.call("execTrace.clear", {})
    c.call("execTrace.addRangeWatch", {"start": "0x800588a8", "end": "0x800588e0",
                                       "max_events": 2000000})
    c.call("accessLog.clear", {})
    c.call("accessLog.addWatch", {"address": "0x%08x" % SLOT, "length": 2,
                                  "type": "write", "max_events": 200000})
    if poke_before_grant is not None:
        # The natural grant is at movie frame ~5336-ish of the emulator counter; drive
        # to just before it via the movie cursor, then set the slot positive.
        c.call("movie.advanceToFrame", {"frame": poke_before_grant, "max_frames": n + 900})
        wr(c, SLOT, struct.pack("<h", 200))
        out["poked_at_movie_frame"] = poke_before_grant
        out["slot_before_grant"] = slot_of(c)
    play_to_end(c)

    counts, total = exec_counts(c, [GRANT_STORE, SFX_CALL, GUARD])
    out["exec_events"] = total
    out["grant_store_executions"] = counts[GRANT_STORE]
    out["sfx_call_executions"] = counts[SFX_CALL]
    out["guard_executions"] = counts[GUARD]

    ev, off = [], 0
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        got = page.get("events") or []
        ev.extend(got)
        if len(got) < 10000:
            break
        off += len(got)
    grants = [e for e in ev
              if str(e.get("instruction_pc") or e.get("pc") or "").lower() == GRANT_STORE]
    out["grant_writes"] = [{"f": g.get("frame"),
                            "new": struct.unpack("<h", struct.pack("<H", (g.get("new_value") or 0) & 0xFFFF))[0]}
                           for g in grants][:4]
    return out


def transition_probe(c, state) -> dict:
    out = {"probe": "T1_scene_transition", "state": Path(state).name}
    c.call("emulator.loadState", {"path": str(state)})
    out["scene_before"] = scene_of(c)
    wr(c, SLOT, struct.pack("<h", 400))
    c.call("accessLog.clear", {})
    c.call("accessLog.addWatch", {"address": "0x%08x" % SLOT, "length": 2,
                                  "type": "write", "max_events": 200000})
    samples = []
    for _ in range(16):
        c.call("emulator.advanceFrames", {"frames": 300})
        samples.append({"scene": scene_of(c), "slot": slot_of(c)})
    out["samples"] = samples[::3]

    ev, off = [], 0
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        got = page.get("events") or []
        ev.extend(got)
        if len(got) < 10000:
            break
        off += len(got)
    pcs = [str(e.get("instruction_pc") or e.get("pc") or "").lower() for e in ev]
    out["slot_writer_pcs"] = sorted(set(pcs))
    out["slot_write_count"] = len(ev)
    out["scene_after"] = samples[-1]["scene"]
    out["slot_after"] = samples[-1]["slot"]
    scene_changed = out["scene_after"] != out["scene_before"]
    ticked = TICK_PC in pcs
    cleared = RESPAWN_CLEAR in pcs
    if not ticked:
        out["verdict"] = ("INCONCLUSIVE -- the tick never fired, so gameplay did not "
                          "resume in the sampled window; a frozen slot is not evidence")
        out["conclusive"] = False
    elif not scene_changed:
        out["verdict"] = ("INCONCLUSIVE -- gameplay ran but the scene never changed, so "
                          "no transition was observed")
        out["conclusive"] = False
    elif cleared:
        out["verdict"] = ("power CLEARED across the transition by %s" % RESPAWN_CLEAR)
        out["conclusive"] = True
    else:
        out["verdict"] = ("power SURVIVED the transition into scene %s with the slot at "
                          "%s, and gameplay demonstrably resumed (tick observed)"
                          % (out["scene_after"], out["slot_after"]))
        out["conclusive"] = True
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23700)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--disc", type=Path, default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--movie", type=Path,
                    default=ROOT / "movies/Phase4/b06_invincibility_hits_from_boot.movie.json")
    ap.add_argument("--end-state", type=Path, default=ROOT / "level01_end_of_stage.sav")
    ap.add_argument("--poke-frame", type=int, default=5200)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_b06_b08_audio_transition.json")
    args = ap.parse_args()

    tmp = _scratch("audiotrans")
    tmp.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rm", "-rf", str(tmp / "cfg")], check=False)
    log = tmp / "launch.log"
    with log.open("w") as fh:
        subprocess.run(["bash", str(ROOT / "tools/launch_repro_playback.sh"),
                        "--execution-mode", "Interpreter", "--config-dir", str(tmp / "cfg"),
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
        c.transport.sock.settimeout(900)
        for fn, kw in ((audio_probe, {"movie": args.movie}),
                       (audio_probe, {"movie": args.movie,
                                      "poke_before_grant": args.poke_frame}),
                       (transition_probe, {"state": args.end_state})):
            try:
                r = fn(c, **kw)
            except Exception as exc:
                r = {"probe": fn.__name__, "error": str(exc)[:220]}
            results.append(r)
            print(json.dumps(r, indent=1), flush=True)
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    args.json.write_text(json.dumps({
        "_comment": "Phase-4 B06/B08 audio-dispatch (DoD 7) and scene-transition (DoD 4) "
                    "probes. Regenerate: tools/phase4_b06_b08_audio_transition.py",
        "execution_mode": "Interpreter", "probes": results}, indent=1) + "\n")
    print("wrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
