#!/usr/bin/env python3
"""F16: what actually writes the Bonus-1 streak counter, live.

The static census closes the domain: `0x8008223C` (= gp+1188) has ONE increment
(`0x8004B3A8`) and SIX clears --

    0x800470D8  berry_throw_dispatch            unconditional, at function entry
    0x8004A6C4  object_slot_type_init           unconditional, after a 64-actor loop
    0x8004A854  resident_level_transition_initiator
    0x8004B1D4  actor_player_contact_resolver
    0x8004B350  actor_player_contact_resolver
    0x8004B3D0  actor_player_contact_resolver   the reset after the fifth

-- and Canon currently documents only the last two. Which of the other four a
player can actually provoke is a different question from which exist, and it is the
question the operator asked: berry kills reset the chain, something else does too,
and some things don't.

This answers it by attribution rather than inference. `F16_Bonus01.movie.json` is
**format v4, Interpreter-recorded**, so instrumentation is free and every write
comes back with the PC that made it. Nothing here is deduced from a listing: each
reset in the run is stamped with its writer.

Watched alongside the counter so each reset can be read against what the player was
doing: the action-state field `0x800A6586` that gates the berry path, the equipped
berry index, and the bonus flags byte.

⚠️ Replayed at 60 Hz via `debugger.resume` + poll, NOT `movie.advanceToFrame`:
frame-stepping does not drive frames through the same poll path, and this movie is
`armed_while_paused`, which is exactly the phase-sensitive case.

    tools/phase4_f16_streak_reset_trace.py --port 23820
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

STREAK = 0x8008223C          # Bonus 1 (F16)
STREAK3 = 0x80082240         # Bonus 3 (F18)
# ⚠️ Bonus 2's five plant identities are five consecutive BYTES, not words: the
# writers are `sb` at 0x80082248,49,4A,4B,4C (e.g. 0x8005C06C/74/7C/84/8C). Watching
# them at stride 4 reads slot 4 as slot 1 and then three unrelated globals, which is
# exactly the mistake an earlier revision of this tool made.
SLOTS2 = 0x80082248          # Bonus 2 (F17), five BYTE slots
FLAGS = 0x8009B889
ACTION = 0x800A6586          # the field whose value 10 calls berry_throw_dispatch
CLASS = 0x800A6584           # player +0x84: >=2 ignore, ==1 count, ==0 reset
BERRY_IDX = 0x800A6597
PROGRESS = 0x80082444        # old_count + 114 on each accepted step

KNOWN_WRITERS = {
    "0x8004b3a8": "INCREMENT (actor_player_contact_resolver)",
    "0x8004b3d0": "clear: the reset after the fifth (challenge complete)",
    "0x8004b350": "clear: actor_player_contact_resolver",
    "0x8004b1d4": "clear: actor_player_contact_resolver",
    "0x800470d8": "clear: berry_throw_dispatch, UNCONDITIONAL at entry",
    "0x8004a6c4": "clear: object_slot_type_init (level/actor init)",
    "0x8004a854": "clear: resident_level_transition_initiator",
    # Bonus 3 (F18)
    "0x80058b34": "B3 clear: streak reset when the berry selector is not blue",
    "0x80059a0c": "B3 clear: contact-dispatch case 13",
    # Bonus 2 (F17)
    "0x8005c580": "B2: append a new mushroom identity",
}

DEFAULT_MOVIE = "movies/Phase4/Interpreter/F16_Bonus01.movie.json"


def launch(port, token, disc, cfg, log, launcher, cwd, mode):
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with Path(log).open("w") as fh:
        subprocess.run(["bash", str(launcher), "--execution-mode", mode,
                        "--config-dir", str(cfg), "--port", str(port), "--token", token,
                        "--disc", str(disc)], cwd=str(cwd), stdout=fh, stderr=fh,
                       check=False)
    text = Path(log).read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-900:])
    return text.split("pid=")[1].split()[0]


def collect(c):
    out, off = [], 0
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        got = page.get("events") or []
        out.extend(got)
        if len(got) < 10000:
            return out, bool(page.get("truncated")), page.get("total")
        off += len(got)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--movie", type=Path, default=ROOT / DEFAULT_MOVIE)
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23820)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=1500.0)
    ap.add_argument("--row", default="F16_bonus1_spiders")
    ap.add_argument("--markers", default="",
                    help="operator-supplied 'MOVIEFRAME:label,...' -- what they did "
                         "and roughly when. These are HYPOTHESES to test, not known "
                         "resets: the point is that some of them will turn out not "
                         "to reset the counter at all.")
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_f16_streak_reset.json")
    args = ap.parse_args()

    # Per-PORT scratch. Three of these are run over the three bonus recordings, and
    # a shared config dir makes the second and third silently fail to bring the API
    # up ("did not come up within 40s") -- which looks like an emulator problem.
    tmp = Path("/tmp/abl-scratch/f16-reset-%d" % args.port)
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": args.row,
        "question": "what writes the Bonus-1 streak 0x8008223C, and when?",
        "movie": str(args.movie.name),
        "static_domain": KNOWN_WRITERS,
        "method": ("Interpreter-recorded v4 movie replayed at 60 Hz with a write watch; "
                   "every write is attributed to the PC that made it"),
    }
    # All three counters are watched in EVERY run on purpose. F18 is the blue-berry
    # challenge, so its recording throws berries constantly -- which is exactly the
    # run in which the Bonus-1 counter should be seen dying at berry_throw_dispatch.
    # A claim tested only in the run it was derived from is barely tested.
    watch = {STREAK: "b1_streak", STREAK3: "b3_streak", FLAGS: "bonus_flags",
             ACTION: "action_state", CLASS: "contact_class",
             BERRY_IDX: "berry_idx", PROGRESS: "progress_cmd"}
    for k in range(5):
        watch[SLOTS2 + k] = "b2_slot%d" % k
    # explicit widths: adjacent byte watches cannot be grouped by a fixed span
    wlen = {a: (2 if a in (FLAGS, ACTION, CLASS, BERRY_IDX) else 4) for a in watch}
    for k in range(5):
        wlen[SLOTS2 + k] = 1
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(1800)

        st = c.call("movie.load", {"path": str(args.movie.resolve())})
        out["movie_frames"] = st.get("frame_count") or st.get("frames")
        status = c.call("movie.status", {})
        out["movie_version"] = status.get("movie_version")
        out["armed_while_paused"] = status.get("armed_while_paused")
        if not c.call("movie.startPlayback", {"load_start_state": True}).get("playing"):
            out["error"] = "playback refused"
            print(json.dumps(out, indent=1))
            return 1
        out["phase_delay_owed"] = c.call("movie.status", {}).get("phase_delay_owed")

        c.call("accessLog.clear", {})
        for a in watch:
            c.call("accessLog.addWatch",
                   {"address": "0x%08x" % a, "length": wlen[a],
                    "type": "write", "max_events": 200000})

        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        while time.time() - began < args.timeout:
            time.sleep(0.5)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 24:
                    break
            else:
                stalls = 0
            last = idx
        out["final_playback_index"] = last
        events, truncated, total = collect(c)
        out["event_total"] = total
        out["ring_truncated"] = truncated
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    by_addr = {}
    for e in events:
        a = int(str(e.get("address", "0")), 16) & 0x1FFFFFFF | 0x80000000
        base = max((w for w in watch if w <= a < w + wlen[w]), default=None)
        if base is None:
            continue
        pc = str(e.get("instruction_pc") or e.get("pc") or "").lower()
        r = by_addr.setdefault(base, {"label": watch[base], "seq": [], "pcs": {}})
        r["pcs"][pc] = r["pcs"].get(pc, 0) + 1
        r["seq"].append({"f": e.get("frame"), "pc": pc, "v": e.get("new_value")})

    streak = by_addr.get(STREAK, {"seq": [], "pcs": {}})
    out["streak_writer_pcs"] = {
        pc: {"count": n, "known_as": KNOWN_WRITERS.get(pc, "UNKNOWN -- not in the "
                                                           "static domain!")}
        for pc, n in sorted(streak["pcs"].items(), key=lambda kv: -kv[1])
    }
    out["streak_writes"] = len(streak["seq"])
    # Operator markers are given in MOVIE frames; accessLog stamps EMULATOR frames.
    # These recordings are state-anchored, so the two differ by the anchor frame and
    # comparing them directly would line every event up against the wrong action.
    anchor = 0
    try:
        anchor = int(json.loads(args.movie.read_text())
                     .get("start_state", {}).get("frame") or 0)
    except Exception:
        pass
    out["movie_anchor_frame"] = anchor

    def mf(f):
        return (f - anchor) if (f is not None and anchor) else f

    out["streak_timeline"] = [
        {"f": s["f"], "mf": mf(s["f"]), "pc": s["pc"], "v": s["v"],
         "what": KNOWN_WRITERS.get(s["pc"], "UNKNOWN")}
        for s in streak["seq"]
    ][:400]

    # a RESET is a clear that destroyed a non-zero streak -- clears of an already
    # zero counter are noise and would inflate any "what resets it" answer.
    # NOTE: the watch logs a store even when it writes the value already there, so
    # "37 berry clears" can mean 37 executions of the path with the counter already
    # at 0. Only the destructive list answers "what killed a live chain".
    real, running = [], 0
    for s in streak["seq"]:
        v = s["v"] if s["v"] is not None else 0
        if v == 0 and running > 0:
            real.append({"f": s["f"], "mf": mf(s["f"]), "pc": s["pc"], "lost": running,
                         "what": KNOWN_WRITERS.get(s["pc"], "UNKNOWN")})
        running = v
    out["destructive_resets"] = real
    out["destructive_reset_pcs"] = sorted({r["pc"] for r in real})

    # correlate against what the operator says they did, in movie frames
    if args.markers:
        marks = []
        for item in args.markers.split(","):
            n, _, label = item.partition(":")
            marks.append({"movie_frame": int(n.strip()), "label": label.strip()})
        for m in marks:
            near = [e for e in out["streak_timeline"]
                    if e["mf"] is not None and abs(e["mf"] - m["movie_frame"]) <= 200]
            m["streak_events_within_200_frames"] = near
            m["destroyed_a_live_chain"] = [
                r for r in real
                if r["mf"] is not None and abs(r["mf"] - m["movie_frame"]) <= 200]
        out["operator_markers"] = marks

    unknown = [pc for pc in streak["pcs"] if pc not in KNOWN_WRITERS]
    out["writers_outside_resolved_set_in_this_run"] = unknown
    out["RETRACTED_domain_closed"] = not unknown
    out["no_observed_writer_outside_resolved_set"] = not unknown
    out["correction_history_domain_closed"] = (
        "Earlier output named this boolean domain_closed. A finite replay only says "
        "whether that run observed a writer outside the resolved static set; it cannot "
        "close unexecuted paths.")

    out["flags_timeline"] = [
        {"f": s["f"], "pc": s["pc"], "v": s["v"]}
        for s in by_addr.get(FLAGS, {"seq": []})["seq"]
    ][:40]
    out["action_state_values_seen"] = sorted(
        {s["v"] for s in by_addr.get(ACTION, {"seq": []})["seq"] if s["v"] is not None})
    out["berry_constructions"] = [
        s["f"] for s in by_addr.get(ACTION, {"seq": []})["seq"] if s["v"] == 10]
    out["contact_class_values_seen"] = sorted(
        {s["v"] for s in by_addr.get(CLASS, {"seq": []})["seq"] if s["v"] is not None})
    # Who sets 0x800A6584, and to what. The static census finds only `sh zero` stores
    # to it by absolute addressing, so whatever writes the NON-zero values does it
    # through a register base and is invisible to an absolute scan. Attribution is
    # the only way to name the value that makes a contact count.
    out["contact_class_writers"] = by_addr.get(CLASS, {"pcs": {}})["pcs"]
    out["contact_class_writes_of_1"] = [
        {"f": s["f"], "pc": s["pc"]}
        for s in by_addr.get(CLASS, {"seq": []})["seq"] if s["v"] == 1][:40]
    out["b3_streak_writers"] = by_addr.get(STREAK3, {"pcs": {}})["pcs"]
    # Destructive resets for Bonus 3 as well, not just Bonus 1. A clear that fires
    # while the streak is already 0 proves the path EXECUTES; only a clear that
    # destroys a live chain proves it MATTERS, and that distinction is the whole
    # point of this recording.
    b3_real, b3_run = [], 0
    for s in by_addr.get(STREAK3, {"seq": []})["seq"]:
        v = s["v"] if s["v"] is not None else 0
        if v == 0 and b3_run > 0:
            b3_real.append({"f": s["f"], "mf": mf(s["f"]), "pc": s["pc"],
                            "lost": b3_run,
                            "what": KNOWN_WRITERS.get(s["pc"], "UNKNOWN")})
        b3_run = v
    out["b3_destructive_resets"] = b3_real
    out["b3_destructive_reset_pcs"] = sorted({r["pc"] for r in b3_real})
    # the equipped berry, so a selector change can be lined up against a clear
    out["berry_idx_timeline"] = [
        {"f": s["f"], "mf": mf(s["f"]), "pc": s["pc"], "v": s["v"]}
        for s in by_addr.get(BERRY_IDX, {"seq": []})["seq"]][:300]
    out["b3_streak_timeline"] = [
        {"f": s["f"], "mf": mf(s["f"]), "pc": s["pc"], "v": s["v"]}
        for s in by_addr.get(STREAK3, {"seq": []})["seq"]][:200]
    # The progress word decides whether the burst plays. Its VALUE and its WRITER
    # are the whole question: B1/B3 emit old_count+114, Bonus 2 emits a constant 113,
    # and the consumer discards anything below 115. Exporting only the slots (as an
    # earlier revision did) makes it impossible to see which chain produced a burst.
    out["progress_timeline"] = [
        {"f": s["f"], "mf": mf(s["f"]), "pc": s["pc"], "v": s["v"],
         "would_burst": (s["v"] is not None and s["v"] >= 115)}
        for s in by_addr.get(PROGRESS, {"seq": []})["seq"]][:200]
    out["progress_writers"] = by_addr.get(PROGRESS, {"pcs": {}})["pcs"]
    out["bursts"] = [e for e in out["progress_timeline"] if e["would_burst"]]

    # The wipe fires every couple of frames, so a flat per-slot cap drowns the two
    # events that actually matter (append and duplicate-restart). Export those
    # separately and uncapped, keyed by the PC that made them.
    B2_WIPE_PCS = {"0x8005c06c", "0x8005c074", "0x8005c07c", "0x8005c084", "0x8005c08c",
                   "0x8005bc94", "0x8005bc9c", "0x8005bca4", "0x8005bcac", "0x8005bcb4"}
    B2_RESTART_PCS = {"0x8005c54c", "0x8005c554", "0x8005c55c", "0x8005c564", "0x8005c56c"}
    b2_events = []
    for k in range(5):
        for s in by_addr.get(SLOTS2 + k, {"seq": []})["seq"]:
            if s["pc"] in B2_WIPE_PCS:
                continue
            b2_events.append({
                "mf": mf(s["f"]), "f": s["f"], "slot": k, "pc": s["pc"], "v": s["v"],
                "what": ("APPEND" if s["pc"] == "0x8005c580"
                         else "DUPLICATE-RESTART" if s["pc"] in B2_RESTART_PCS
                         else "?")})
    b2_events.sort(key=lambda e: (e["mf"] if e["mf"] is not None else 0, e["slot"]))
    out["b2_appends_and_restarts"] = b2_events
    out["b2_duplicate_restart_observed"] = any(
        e["what"] == "DUPLICATE-RESTART" for e in b2_events)

    out["b2_slot_timeline"] = {
        "0x%08X" % (SLOTS2 + k): [
            {"f": s["f"], "mf": mf(s["f"]), "pc": s["pc"], "v": s["v"]}
            for s in by_addr.get(SLOTS2 + k, {"seq": []})["seq"]][:60]
        for k in range(5)}

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in
                      ("movie_frames", "movie_version", "armed_while_paused",
                       "phase_delay_owed", "ring_truncated", "streak_writes",
                       "streak_writer_pcs", "destructive_reset_pcs",
                       "domain_closed", "writers_outside_the_static_domain",
                       "flags_timeline") if k in out}, indent=1)[:3000])
    print("\ndestructive resets (a clear that killed a live streak):")
    for r in out["destructive_resets"][:30]:
        print("  frame %-6s pc %s  lost %d  -- %s" % (r["f"], r["pc"], r["lost"],
                                                      r["what"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
