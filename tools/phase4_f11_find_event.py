#!/usr/bin/env python3
"""F11: what actually SETS a scout's found-bit, traced on the operator's recording.

The static pass (tools/phase4_f11_static.c) established that a scout counts as found when
its actor flags (+0x5C) carry bit 0x1000, and that the overlay clears the bit again after
handling. What it could NOT say is what SETS the bit -- the find event itself.

The counting loop names the actors exactly:

    0x800B4238  a0 = 0x800A14B4
    0x800B4240  s1 = a0 - 792  = 0x800A119C      ; scout 0's actor base
    0x800B4268  s0 = a0 - 788  = s1 + 4
    0x800B4298  lhu v0,0x58(s0)                  ; == [s1 + 0x5C], the flags
    0x800B42A0  andi v0,v0,0x1000                ; the found bit
    0x800B4324  s0 += 132                        ; actor stride
    0x800B432C  slti s2,5                        ; EXACTLY FIVE scouts

so the flag words are 0x800A119C + n*0x84 + 0x5C for n = 0..4.

Watching those five plus the published counter gives the whole event: which PC sets the
bit, which clears it, and how the counter follows.

    tools/phase4_f11_find_event.py --port 23750
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
SCOUT0, STRIDE, NSCOUTS, FLAGS_OFF = 0x800A119C, 0x84, 5, 0x5C
COUNTER = 0x800B4A48
TIMER = 0x800B4A4C
GOAL_LATCH = 0x800823A0      # the campaign-wide level-exit signal
SCENE_ID = 0x80082504
FOUND_BIT = 0x1000


def launch(port, token, disc, cfg, log, launcher, cwd, mode):
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with Path(log).open("w") as fh:
        subprocess.run(["bash", str(launcher), "--execution-mode", mode,
                        "--config-dir", str(cfg), "--port", str(port), "--token", token,
                        "--disc", str(disc)], cwd=str(cwd), stdout=fh, stderr=fh,
                       check=False)
    text = Path(log).read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-800:])
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
    ap.add_argument("--movie", type=Path,
                    default=ROOT / "movies/Phase4/Interpreter/F11_scouts.movie.json")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23750)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_f11_find_event.json")
    # the same watch works for any contact-bit actor set (scouts, acorns, ...)
    ap.add_argument("--base", type=lambda x: int(x, 0), default=None,
                    help="actor-set base; default is the scout set 0x800A119C")
    ap.add_argument("--count", type=int, default=None, help="how many actors")
    ap.add_argument("--label", default="scout")
    args = ap.parse_args()

    global SCOUT0, NSCOUTS
    if args.base is not None:
        SCOUT0 = args.base
    if args.count is not None:
        NSCOUTS = args.count

    tmp = Path("/tmp/abl-scratch/f11-find")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "F11_the_tree",
        "actor_set": args.label,
        "question": "does the contact bit 0x1000 ever set on this actor set",
        "movie": str(args.movie.relative_to(ROOT)),
        "scouts": ["0x%08X" % (SCOUT0 + n * STRIDE) for n in range(NSCOUTS)],
        "flag_words": ["0x%08X" % (SCOUT0 + n * STRIDE + FLAGS_OFF) for n in range(NSCOUTS)],
        "basis": ("actor set and stride read off the counting loop itself "
                  "(0x800B4240 / 0x800B4324 / slti s2,5), not assumed"),
    }
    watch = {}
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(1200)
        st = c.call("movie.load", {"path": str(args.movie)})
        out["frames"] = st.get("frame_count")
        started = c.call("movie.startPlayback", {"load_start_state": True})
        if not started.get("playing"):
            out["error"] = "playback refused: %s" % started
            print(json.dumps(out, indent=1))
            return 1
        out["movie_version"] = c.call("movie.status", {}).get("movie_version")

        # The recording starts BEFORE the level loads, so arming at frame 0 also
        # captures the overlay's own init writes -- which is what we want.
        c.call("accessLog.clear", {})
        for n in range(NSCOUTS):
            a = SCOUT0 + n * STRIDE + FLAGS_OFF
            c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": 2,
                                          "type": "write", "max_events": 60000})
            watch[a] = "%s%d flags" % (args.label, n)
        for a, n, lab in ((COUNTER, 4, "counter"), (TIMER, 4, "post-find timer"),
                          (GOAL_LATCH, 2, "goal latch (level exit)"),
                          (SCENE_ID, 4, "scene id")):
            c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": n,
                                          "type": "write", "max_events": 60000})
            watch[a] = lab

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
                if stalls >= 20:
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

    by = {}
    for e in events:
        a = int(str(e.get("address", "0")), 16) & 0x1FFFFFFF | 0x80000000
        b0 = max((w for w in watch if w <= a), default=None)
        if b0 is None:
            continue
        r = by.setdefault(b0, {"label": watch[b0], "seq": [], "writers": {}})
        pc = str(e.get("instruction_pc") or e.get("pc") or "").lower()
        r["writers"][pc] = r["writers"].get(pc, 0) + 1
        v = e.get("new_value")
        if v is not None:
            r["seq"].append({"f": e.get("frame"), "pc": pc, "v": v})

    # transitions of the found bit, per scout
    sets, clears = [], []
    for n in range(NSCOUTS):
        a = SCOUT0 + n * STRIDE + FLAGS_OFF
        prev = None
        for s in by.get(a, {"seq": []})["seq"]:
            v = s["v"] & 0xFFFF
            if prev is not None:
                if not (prev & FOUND_BIT) and (v & FOUND_BIT):
                    sets.append({"scout": n, "f": s["f"], "pc": s["pc"],
                                 "from": hex(prev), "to": hex(v)})
                elif (prev & FOUND_BIT) and not (v & FOUND_BIT):
                    clears.append({"scout": n, "f": s["f"], "pc": s["pc"],
                                   "from": hex(prev), "to": hex(v)})
            prev = v

    counter_seq = [{"f": s["f"], "pc": s["pc"], "v": s["v"]}
                   for s in by.get(COUNTER, {"seq": []})["seq"]]
    latch_seq = [{"f": s["f"], "pc": s["pc"], "v": s["v"] & 0xFFFF}
                 for s in by.get(GOAL_LATCH, {"seq": []})["seq"]]
    scene_seq = [{"f": s["f"], "pc": s["pc"], "v": s["v"]}
                 for s in by.get(SCENE_ID, {"seq": []})["seq"]]

    out["by_field"] = {
        "0x%08X" % a: {"label": r["label"], "writes": len(r["seq"]),
                       "writer_pcs": sorted(r["writers"].items(), key=lambda kv: -kv[1])[:6]}
        for a, r in sorted(by.items())
    }
    out["findings"] = {
        "bit_set_events": sets,
        "bit_clear_events": clears,
        "setter_pcs": sorted({s["pc"] for s in sets}),
        "clearer_pcs": sorted({s["pc"] for s in clears}),
        "counter_timeline": counter_seq[:60],
        "counter_values": [s["v"] for s in counter_seq],
        "counter_reached_zero": any(s["v"] == 0 for s in counter_seq),
        "goal_latch_writes": latch_seq[:20],
        "goal_latch_writer_pcs": sorted({s["pc"] for s in latch_seq}),
        "scene_id_writes": scene_seq[:20],
        "verdict": None,
        "objective_verdict": None,
    }
    # Does the count reaching zero drive the exit?
    zero_f = next((s["f"] for s in counter_seq if s["v"] == 0), None)
    latch_f = next((s["f"] for s in latch_seq if s["v"] == 1), None)
    if zero_f is not None and latch_f is not None:
        out["findings"]["objective_verdict"] = (
            "counter reached 0 at frame %s; the goal latch was set to 1 at frame %s by "
            "%s -- %s" % (zero_f, latch_f,
                          [s["pc"] for s in latch_seq if s["v"] == 1][:2],
                          "AFTER the count hit zero, consistent with the count gating "
                          "the exit" if latch_f >= zero_f else
                          "BEFORE the count hit zero, so the count does NOT gate it"))
    elif zero_f is None:
        out["findings"]["objective_verdict"] = (
            "the counter never reached 0 in this capture, so the objective question is "
            "NOT answered by this run")
    else:
        out["findings"]["objective_verdict"] = (
            "the counter reached 0 at frame %s but the goal latch was never set to 1 -- "
            "reaching 0 is NOT by itself the exit" % zero_f)
    if sets:
        out["findings"]["verdict"] = (
            "the found bit is SET by %s (%d event(s) across %d scout(s)); cleared by %s"
            % (sorted({s["pc"] for s in sets}), len(sets),
               len({s["scout"] for s in sets}), sorted({s["pc"] for s in clears})))
    else:
        out["findings"]["verdict"] = (
            "no 0->1 transition of bit 0x1000 was captured on any of the five scout "
            "flag words. Either the find sets the bit somewhere else, or these are not "
            "the scouts, or no find occurred in the captured window -- the counter "
            "timeline says which.")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"frames": out.get("frames"),
                      "ring_truncated": out.get("ring_truncated"),
                      "by_field": out["by_field"],
                      "findings": {k: out["findings"][k] for k in
                                   ("bit_set_events", "bit_clear_events",
                                    "counter_values", "verdict")}}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
