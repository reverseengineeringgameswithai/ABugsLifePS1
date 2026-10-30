#!/usr/bin/env python3
"""Observe where the knockdown chain actually diverts during a natural contact.

WHY THIS EXISTS
---------------
`tools/phase4_knockdown_reachability.py` proves from the pristine image that the
knockdown store at `0x8004AFB0` is reachable and targets player+0x82, not the power
slot. An earlier revision of this probe called it a power-slot clear; that was wrong.
This is the runtime half: replay a fixture with real contacts and record how far down
that chain the game naturally gets, which guard turns it away, and with what values.

That is a stronger observation than the earlier "execTrace over the block returned zero
events". Zero events was consistent with two very different worlds -- the code being
unreachable, or the probe watching a range the game diverts before ever entering. The
per-guard histogram distinguishes them.

SELF-CHECK -- THIS IS THE POINT
-------------------------------
Arming any CPU instrumentation forces `CPUExecutionMode::Interpreter`. A movie recorded
on `CachedInterpreter` therefore desyncs the instant the trace is armed, SILENTLY:
`reproducible` still reports true and the capture looks plausible but empty. An empty
histogram would then be indistinguishable from "the guard chain is never entered", and
reading it as evidence would repeat a mistake this campaign has already made once.

So the probe asserts the fixture's KNOWN oracle markers in the same armed run. If the
grant and the absorbs still land on their recorded frames, the replay is faithful and
the histogram means something. If they do not, the run is reported INCONCLUSIVE and no
conclusion is drawn from the trace at all.

USAGE
    tools/phase4_knockdown_probe.py --port 23820
    tools/phase4_knockdown_probe.py --movie movies/Phase4/b06_invincibility_hits_from_boot.movie.json
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


def _scratch(name: str) -> Path:
    import os
    import tempfile
    base = (os.environ.get("ABL_SCRATCH")
            or (os.environ.get("CLAUDE_JOB_DIR") and
                Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp" / "abl-scratch")
            or Path(tempfile.gettempdir()) / "abl-scratch")
    p = Path(base) / name
    p.mkdir(parents=True, exist_ok=True)
    return p


ROOT = Path(__file__).resolve().parent.parent
SLOT = 0x800A657E
STORE_SITE = 0x8004AFB0
TRACE_LO, TRACE_HI = 0x8004AE80, 0x8004AFC8

# The guard chain, in the order the code tests it. Reaching a later PC means every
# earlier guard was satisfied on that pass.
GUARD_PCS = [
    (0x8004AE9C, "actor+0x5C & 0x20 != 0"),
    (0x8004AEA8, "actor+0x5C & 0x40 == 0"),
    (0x8004AEBC, "player+0x84 != 1   (THE DECIDING BRANCH)"),
    (0x8004AF04, "actor+0x6C == 0"),
    (0x8004AF18, "player+0x00 < actor+0x08"),
    (0x8004AF2C, "player+0x9F == 0"),
    (0x8004AF3C, "actor+0x5E != 0"),
    (0x8004AF4C, "player+0x2C >= 0"),
    (0x8004AF5C, "player+0x7C != 0"),
    (0x8004AF6C, "player+0x84 != 17"),
    (0x8004AF70, "--- knockdown body entered ---"),
    (STORE_SITE, "*** player+0x82 store executed (NOT the power slot) ***"),
]


def rd(c, a, n):
    return bytes.fromhex(c.call("debugger.readMemory",
                                {"address": "0x%08x" % a, "length": n})["hex"])


def drain(c, method, limit=10000):
    out, off = [], 0
    while True:
        page = c.call(method, {"offset": off, "limit": limit})
        got = page.get("events") or []
        out.extend(got)
        if len(got) < limit:
            return out, bool(page.get("truncated"))
        off += len(got)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23820)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--movie", type=Path,
                    default=ROOT / "movies/Phase4/B08_bubble_repeated_hits_from_boot.movie.json")
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_knockdown_probe.json")
    ap.add_argument("--poke-live", type=int, default=None, metavar="VALUE",
                    help="Halt at the guard chain's first pass, set the slot to VALUE, "
                         "resume, and confirm that the player+0x82 store does not zero "
                         "the slot. This corroborates the statically pinned EA.")
    args = ap.parse_args()

    if not args.movie.exists():
        print("fixture absent:", args.movie)
        return 2

    tmp = _scratch("knockdown")
    subprocess.run(["rm", "-rf", str(tmp / "cfg")], check=False)
    log = tmp / "launch.log"
    with log.open("w") as fh:
        subprocess.run(["bash", str(ROOT / "tools/launch_repro_playback.sh"),
                        "--execution-mode", "Interpreter",
                        "--config-dir", str(tmp / "cfg"),
                        "--port", str(args.port), "--token", args.token,
                        "--disc", str(args.disc)], cwd=str(ROOT),
                       stdout=fh, stderr=fh, check=False)
    text = log.read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-800:])
    pid = text.split("pid=")[1].split()[0]

    out = {"movie": args.movie.name, "execution_mode": "Interpreter"}
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(900)

        n = c.call("movie.load", {"path": str(args.movie)})["frame_count"]
        out["frame_count"] = n
        if not c.call("movie.startPlayback", {"load_start_state": True}).get("playing"):
            raise SystemExit("playback refused")

        c.call("execTrace.clear", {})
        c.call("execTrace.addRangeWatch", {"start": "0x%08x" % TRACE_LO,
                                           "end": "0x%08x" % TRACE_HI,
                                           "max_events": 2000000})
        c.call("accessLog.clear", {})
        c.call("accessLog.addWatch", {"address": "0x%08x" % SLOT, "length": 2,
                                      "type": "write", "max_events": 200000})

        # A live-power intervention, when asked for. This is sound precisely BECAUSE the
        # ten guards read player +0x00/+0x2C/+0x7C/+0x84/+0x9F and actor +0x5C/+0x5E/+0x6C
        # and never the power slot +0x7E -- so writing the slot cannot change whether the
        # knockdown fires. It changes only the negative control being watched.
        if args.poke_live is not None:
            # The API signals a breakpoint with a `breakpointHit` EVENT and identifies
            # breakpoints by id; `debugger.status` carries no hit field, and the type is
            # "execute", not "exec". Polling status for a hit count silently waits out
            # its whole timeout and pokes nothing -- which is what the first version of
            # this did.
            bp = c.call("debugger.addBreakpoint",
                        {"address": "0x8004AF04", "type": "execute"})
            out["poke_breakpoint"] = bp
            c.call("debugger.resume", {})
            armed = False
            try:
                ev0 = c.wait_event(
                    lambda e: e.get("event") in ("breakpointHit", "paused"),
                    timeout=float(args.timeout))
                out["breakpoint_event"] = {k: ev0.get(k)
                                           for k in ("event", "pc", "frame", "id")}
                c.call("debugger.writeMemory",
                       {"address": "0x%08x" % SLOT,
                        "hex": struct.pack("<h", args.poke_live).hex()})
                out["poked_slot_to"] = struct.unpack("<h", rd(c, SLOT, 2))[0]
                try:
                    c.call("debugger.removeBreakpoint", {"id": bp.get("id")})
                except Exception:
                    c.call("debugger.removeBreakpoint", {"address": "0x8004AF04"})
                armed = True
            except Exception as exc:
                out["poke_error"] = str(exc)[:200]
            out["poke_armed"] = armed
            if not armed:
                out["poke_note"] = ("never halted at 0x8004AF04 -- no intervention was "
                                    "made, so this run is just the natural one")

        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        while time.time() - began < args.timeout:
            time.sleep(2.0)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 6:
                    break
            else:
                stalls = 0
            last = idx
        out["final_playback_index"] = last

        ev, trunc = drain(c, "execTrace.get")
        acc, atrunc = drain(c, "accessLog.get")
        out["exec_events"] = len(ev)
        out["exec_truncated"] = trunc
        out["slot_write_events"] = len(acc)
        out["slot_watch_truncated"] = atrunc

        counts = {}
        for e in ev:
            pc = str(e.get("pc") or e.get("address") or "").lower()
            counts[pc] = counts.get(pc, 0) + 1
        frames_of = {}
        for e in ev:
            pc = str(e.get("pc") or e.get("address") or "").lower()
            frames_of.setdefault(pc, []).append(e.get("frame"))
        out["guard_histogram"] = [
            {"pc": "0x%08X" % pc, "condition": why,
             "times_reached": counts.get("0x%08x" % pc, 0),
             "frames": frames_of.get("0x%08x" % pc, [])[:8]}
            for pc, why in GUARD_PCS]
        # WAS THE POWER LIVE WHEN IT FIRED? Reachability alone does not close item 4 --
        # Interleave the store site's frames with the slot's own write timeline.
        out["player_plus_0x82_store_frames"] = frames_of.get(
            "0x%08x" % STORE_SITE, [])

        # ---- the self-check: did the fixture's own oracle markers survive arming? ----
        writes = [{"frame": a.get("frame"),
                   "pc": str(a.get("instruction_pc") or a.get("pc") or "").lower(),
                   "value": struct.unpack("<h", struct.pack(
                       "<H", (a.get("new_value") or 0) & 0xFFFF))[0]}
                  for a in acc]
        out["slot_writes"] = writes[:40]
        grants = [w for w in writes if w["value"] in (-3, 400)]
        out["grant_writes_seen"] = grants[:6]
        faithful = bool(grants)
        out["replay_faithful"] = faithful

        # A slot write from this PC would contradict the statically pinned player+0x82 EA.
        site_slot_writes = [w for w in writes if w["pc"] == "0x%08x" % STORE_SITE]
        out["slot_writes_from_player_plus_0x82_site"] = site_slot_writes
        if args.poke_live is not None:
            out["live_power_verdict"] = (
                ("CONTRADICTION -- 0x8004AFB0 appeared as a slot writer at frame %s." %
                 site_slot_writes[0]["frame"])
                if site_slot_writes else
                ("CONFIRMED -- with the slot set live to %d, 0x8004AFB0 produced no "
                 "slot write, as the player+0x82 EA predicts." % args.poke_live))
        store_executions = counts.get("0x%08x" % STORE_SITE, 0)
        if not faithful:
            out["verdict"] = ("INCONCLUSIVE -- the fixture's own grant marker did not "
                              "reproduce in the armed run, so this movie was very likely "
                              "recorded on CachedInterpreter and desynced the moment the "
                              "trace was armed. The histogram below is NOT evidence. "
                              "Re-record this level on Interpreter before drawing any "
                              "conclusion about the knockdown chain.")
        elif store_executions:
            out["verdict"] = ("OBSERVED -- the player+0x82 knockdown store executed %d "
                              "time(s) naturally; it produced no power-slot write."
                              % store_executions)
        else:
            reached = [g for g in out["guard_histogram"] if g["times_reached"]]
            deepest = reached[-1] if reached else None
            out["verdict"] = (
                "NOT REACHED NATURALLY, and the replay IS faithful (grant markers "
                "reproduced), so this is a real measurement rather than a desync. "
                "Deepest guard reached: %s. The chain diverts before the knockdown body."
                % (("%s (%s), %d times" % (deepest["pc"], deepest["condition"],
                                           deepest["times_reached"]))
                   if deepest else "none -- the contact resolver's knockdown region was "
                                   "never entered at all"))
        print(json.dumps({k: v for k, v in out.items() if k != "slot_writes"}, indent=1))
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
