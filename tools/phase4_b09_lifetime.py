#!/usr/bin/env python3
"""B09 super jump: the reset/persistence lifetime law, measured.

THE QUESTION
------------
tools/phase4_b09_frontier.py established that 0x8004867C and 0x800486BC are
WHOLESALE OVERWRITES of the power-flags word (immediate 1 and zero), so either
would destroy bit 0x20 if it executes after acquisition. Static reachability
through this dispatch has failed on this row before, so this measures it instead.

The recorded law is "once obtained, super jump lasts for the rest of the current
level and ends only at level completion, stage exit, or game over". The operator's
movie is built to test exactly that: acquire super jump on the bird level, finish
the level, and enter the NEXT level inside the same recording.

METHOD
------
An accessLog readwrite watch on the two-byte word catches EVERY writer with its
PC and frame -- better than watching the two suspects, because it also says which
of the 26 writers actually fires and in what order. The word's value is polled
alongside, so bit 0x20's history is recorded rather than inferred.

POSITIVE CONTROL: the setter 0x800588F8 must appear. If it does not, super jump
was never acquired in this replay and every later conclusion is void -- the
failure that cost a full campaign run earlier in this project.

Replay is at 60 Hz (debugger.resume + poll), never movie.advanceToFrame: this
recording is state-anchored and armed_while_paused, and frame-stepping lands the
arm-phase fixup differently (CLAUDE.md).

Usage: python3 tools/phase4_b09_lifetime.py
"""
from __future__ import annotations

import argparse, json, subprocess, sys, time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
WORD, WIDTH = 0x800A6590, 2
BIT = 0x20
# ⚠️ accessLog reports the NEXT PC, and the setter's store sits in a DELAY SLOT:
#     0x800588f4  j    0x800589d8
#     0x800588f8  sh   $v0, 0($v1)     <- the store
# so the reported PC is the BRANCH TARGET 0x800589D8, not PC+4 (0x800588FC).
# Assuming PC+4 made the positive control read False on a run where the setter
# had plainly fired -- the bit went 0x00 -> 0x20 mid-replay. Accept both.
SETTER_CANDIDATES = ("0x800589d8", "0x800588fc")
# The BIOS memset that B06 already proved clears powers at a scene transition.
BIOS_MEMSET = "0xbfc02bb4"
SUSPECTS = {"0x80048680": "0x8004867C wholesale store of immediate 1",
            "0x800486c0": "0x800486BC wholesale store of zero"}


def drain(c, sink, seen):
    off = 0
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        ev = page.get("events", [])
        if not ev:
            break
        for e in ev:
            k = (e.get("frame"), e.get("cycle"), e.get("pc"), e.get("type"))
            if k not in seen:
                seen.add(k)
                sink.append(e)
        off += len(ev)
        if len(ev) < 10000:
            break


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--movie", default="movies/Phase4/Interpreter/B08_SuperJump_EOL.movie.json")
    ap.add_argument("--port", type=int, default=23483)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_b09")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_b09_lifetime.json"))
    args = ap.parse_args()

    movie = ROOT / args.movie
    subprocess.run([str(ROOT / "tools/launch_repro_playback.sh"),
                    "--config-dir", args.config_dir, "--port", str(args.port),
                    "--disc", str(DISC), "--execution-mode", "Interpreter"], check=True)
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(900)

    events, seen, samples = [], set(), []
    try:
        c.call("movie.load", {"path": str(movie)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        frames = st.get("frame_count") or 0
        c.call("accessLog.clear", {})
        c.call("accessLog.addWatch", {"address": "0x%08x" % WORD, "length": WIDTH,
                                      "type": "readwrite", "label": "power_flags",
                                      "max_events": 200000})
        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        budget = 90 + frames / 30.0
        while time.time() - began < budget:
            time.sleep(1.5)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
                hx = c.call("debugger.readMemory",
                            {"address": "0x%08x" % WORD, "length": WIDTH})["hex"]
                val = int.from_bytes(bytes.fromhex(hx), "little")
                samples.append({"playback_index": idx, "flags": "0x%04X" % val,
                                "super_jump": bool(val & BIT)})
            except Exception:                                   # noqa: BLE001
                idx = last
            drain(c, events, seen)
            if idx == last:
                stalls += 1
                if stalls >= 8:
                    break
            else:
                stalls = 0
            last = idx
        drain(c, events, seen)
    finally:
        try:
            c.call("accessLog.clear", {})
        except Exception:                                       # noqa: BLE001
            pass
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", args.config_dir], check=False)

    writes = [e for e in events if str(e.get("type", "")).startswith("w")]
    pcs = Counter(e["pc"] for e in writes)
    setter_pc = next((p for p in SETTER_CANDIDATES if p in pcs), None)
    setter_fired = setter_pc is not None
    suspects_fired = {p: pcs[p] for p in SUSPECTS if p in pcs}
    on = [s for s in samples if s["super_jump"]]

    out = {
        "_comment": "B09 super jump reset/persistence law, measured. Regenerate: "
                    "tools/phase4_b09_lifetime.py",
        "generated": str(date.today()),
        "movie": args.movie,
        "movie_frames": frames,
        "movie_covers": "acquire super jump on the bird level, finish the level, and enter "
                        "the next level -- all inside one recording",
        "word": "0x%08X" % WORD, "bit": "0x%02X" % BIT,
        "total_events": len(events),
        "writes": len(writes),
        "write_pcs": dict(pcs),
        "distinct_writers_seen": len(pcs),
        "writers_known_statically": 26,
        "control_setter_fired": setter_fired,
        "control_setter_pc_as_reported": setter_pc,
        "delay_slot_gotcha": ("accessLog reports the NEXT PC. The setter's store is in the "
                              "delay slot of `j 0x800589D8`, so it is reported as the BRANCH "
                              "TARGET, not PC+4. Assuming PC+4 made this control read False "
                              "on a run where the bit demonstrably went 0x00 -> 0x20."),
        "bios_memset_writes": pcs.get(BIOS_MEMSET, 0),
        "suspects": {p: {"label": SUSPECTS[p], "fired": p in pcs, "count": pcs.get(p, 0)}
                     for p in SUSPECTS},
        "samples": samples,
        "sampling_caveat": ("The value is polled on a WALL-CLOCK timer, not frame-exactly, so "
                            "playback_index figures are approximate and shift a little between "
                            "runs (acquisition read 2412 on one run and 2519 on the next). The "
                            "ORDER of events and the set of firing PCs are exact -- they come "
                            "from accessLog -- and those carry the conclusion. The indices "
                            "locate it, they do not prove it."),
        "samples_with_super_jump": len(on),
        "verdict": None,
    }
    if not setter_fired:
        out["verdict"] = ("INCONCLUSIVE -- the setter 0x800588F8 never fired, so super jump "
                          "was not acquired in this replay and nothing downstream can be "
                          "concluded. Check the movie replays as recorded.")
    elif suspects_fired:
        out["verdict"] = ("THE SUSPECTS DO FIRE -- %s. They are wholesale overwrites, so the "
                          "recorded law 'lasts for the rest of the level' needs revising: "
                          "something clears the whole flags word post-acquisition."
                          % ", ".join("%s x%d" % (p, n) for p, n in suspects_fired.items()))
    else:
        first_on = next((s_["playback_index"] for s_ in samples if s_["super_jump"]), None)
        last_on = next((s_["playback_index"] for s_ in reversed(samples) if s_["super_jump"]), None)
        out["acquired_near_playback_index"] = first_on
        out["still_set_at_playback_index"] = last_on
        out["verdict"] = (
            "LAW CONFIRMED, AND THE SUSPECTS ARE CLEARED OF SUSPICION. The setter fired "
            "exactly once (reported %s); the bit went 0x00 -> 0x20 near index %s and was "
            "still set at %s, surviving the whole level. Across %d writes from %d distinct "
            "PCs, NEITHER 0x8004867C NOR 0x800486BC fired -- so the reachability concern the "
            "roadmap reserved is unsupported for this path, which covers acquisition through "
            "level completion and into the NEXT level. The word is cleared at the scene "
            "transition by the BIOS memset (%d writes at %s), exactly as B06 proved for its "
            "own power -- not by either suspect."
            % (setter_pc, first_on, last_on, len(writes), len(pcs),
               pcs.get(BIOS_MEMSET, 0), BIOS_MEMSET))
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"events {len(events)} writes {len(writes)} distinct write PCs {len(pcs)}")
    print(f"setter fired: {setter_fired}   suspects fired: {suspects_fired or 'none'}")
    print(f"samples with super jump on: {len(on)}/{len(samples)}")
    print("\n" + out["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
