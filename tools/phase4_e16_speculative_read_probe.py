#!/usr/bin/env python3
"""Characterise the campaign's find: what is 0x80010BF4 doing to the E16 windows?

THE FIND
--------
The validated any% campaign caught a PC that E16's static frontier never
predicted, in LEVEL01 and LEVEL02 (LEVEL00 and LEVEL03 are clean):

    0x80010be8  sll  $t9, $t9, 2        ; t9 = idx*4
    0x80010bec  sltu $a3, $t9, $s5      ; a3 = (idx*4 < limit)   <- test COMPUTED
    0x80010bf0  add  $t9, $t9, $s1      ; t9 = base + idx*4      <- base is a REGISTER
    0x80010bf4  lhu  $t9, 0($t9)        ; THE ACCESS
    0x80010bf8  beq  $a3, $zero, ...    ; <- test ACTED ON, one instruction too late

accessLog reports the PC after the access, so 0x80010BF8 in the log is this load.

TWO REASONS THE STATIC WORK COULD NOT HAVE FOUND IT, and they are different bugs:

 1. SCOPE.  0x80010BF4 lies in no function in analysis/functions_resident.txt.
    The entry `0x80010000 724 per_object_mesh_draw_payload_emitter` ends at
    0x800102D4 -- and 0x80010C88 is `j 0x800102D4`, i.e. the loop head. The
    census truncated the emitter and dropped its whole main loop into a 11,828-byte
    hole. See tools/phase4_resident_gap_census.py.

 2. FORM.  The base is a REGISTER, not a `lui` constant, so this access is not
    region-formed at all. The affine census is structurally blind to it no matter
    how good the function list is. Fixing (1) would NOT have found this.

WHAT THIS DECIDES
-----------------
Whether the access is a benign discarded speculative load or a real consumer of
the E16 tables. The static text says the loaded value is dead when the range test
fails (0x80010C80 is `bne $s2,$zero,...` / `addi $s0,$s0,12`; $t9 unused), but
"the compiler hoisted a load past its own bounds check" is a claim about runtime,
so it gets measured: widen the watch well below and above each window and look at
where this PC's addresses actually land.

  addresses land only OUTSIDE the window, sweeping in from an adjacent array
      -> an overrun of the neighbouring object, value discarded; E16's tables are
         collateral, not data this code consumes
  addresses land INSIDE the window and are consumed
      -> a genuine unenumerated reader; E16's frontier is wrong and must grow

Usage:
  python3 tools/phase4_e16_speculative_read_probe.py \
      --movie 'movies/Phase4/Interpreter/Any% Runs/LEVEL02_Tunnels.movie.json'
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

import subprocess  # noqa: E402

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
SUSPECT = "0x80010bf8"
# PAD widens the watch around each window to show where a sweep comes FROM.
# It defaults to 0 because widening is expensive in a way that DESTROYS the
# measurement: at PAD=256 the neighbouring objects are hot enough to push the
# 200,000-event ring to saturation, and the suspect PC's events get evicted
# before they can be read. The exact windows produce ~118 events in a clean
# movie. Widen only with a raised cap and a short movie.
PAD = 0
WATCH_MAX = 256          # accessLog.addWatch rejects length > 256 (-32602)
WINDOWS = [("markers_0x30_0x57", 0x8009B5A8, 160),
           ("markers_0x28_0x2F", 0x8009C210, 32),
           ("markers_0x58_0x5F", 0x800A65B0, 32)]
SUSPECT_DEFAULT = "0x80010bf8"


def drain(c, sink, seen):
    off = 0
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        ev = page.get("events", [])
        if not ev:
            break
        for e in ev:
            k = (e.get("frame"), e.get("cycle"), e.get("pc"),
                 e.get("address"), e.get("type"))
            if k not in seen:
                seen.add(k)
                sink.append(e)
        off += len(ev)
        if len(ev) < 10000:
            break


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--movie", required=True)
    ap.add_argument("--pc", default=SUSPECT_DEFAULT,
                    help="the logged PC to characterise (accessLog reports PC+4)")
    ap.add_argument("--pad", type=int, default=None,
                    help="bytes of context each side of a window (default 0; see PAD)")
    ap.add_argument("--port", type=int, default=23479)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_e16probe")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_speculative_read_probe.json"))
    args = ap.parse_args()

    global PAD, SUSPECT
    SUSPECT = args.pc
    if args.pad is not None:
        PAD = args.pad
    movie = Path(args.movie)
    if not movie.is_absolute():
        movie = ROOT / movie

    subprocess.run([str(ROOT / "tools/launch_repro_playback.sh"),
                    "--config-dir", args.config_dir, "--port", str(args.port),
                    "--disc", str(DISC), "--execution-mode", "Interpreter"], check=True)
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(900)

    events, seen = [], set()
    try:
        c.call("movie.load", {"path": str(movie)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        frames = st.get("frame_count") or 0
        c.call("accessLog.clear", {})
        # WIDENED windows -- the point is to see where this PC's addresses come FROM.
        # addWatch caps length at 256, so each widened span is laid down in chunks.
        nwatch = 0
        for name, base, ln in WINDOWS:
            lo, hi = base - PAD, base + ln + PAD
            a = lo
            while a < hi:
                span = min(WATCH_MAX, hi - a)
                c.call("accessLog.addWatch",
                       {"address": "0x%08x" % a, "length": span, "type": "readwrite",
                        "label": "%s_w%d" % (name, nwatch), "max_events": 200000})
                nwatch += 1
                a += span
        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        budget = 60 + frames / 30.0
        while time.time() - began < budget:
            time.sleep(1.5)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:                                  # noqa: BLE001
                idx = last
            drain(c, events, seen)
            if idx == last:
                stalls += 1
                if stalls >= 6:
                    break
            else:
                stalls = 0
            last = idx
        drain(c, events, seen)
        final_index = last
    finally:
        try:
            c.call("accessLog.clear", {})
        except Exception:                                      # noqa: BLE001
            pass
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", args.config_dir], check=False)

    # POSITIVE CONTROL. The first run of this probe reported "0 events from the
    # suspect PC" and I could not tell whether that meant the access did not
    # happen or the watch never engaged -- the exact failure the validator was
    # built to prevent, reproduced here because I omitted its control. Never
    # again: report total events, the PC histogram and whether a loader clear
    # fired, so a zero is always interpretable.
    all_pcs = Counter(e.get("pc") for e in events)
    control_fired = bool({"0x8003a3bc", "0x8003a3c0", "0x8005f6a4"} & set(all_pcs))
    mine = [e for e in events if e.get("pc") == SUSPECT]
    addrs = sorted({int(str(e["address"]), 16) for e in mine})
    types = Counter(e.get("type") for e in mine)

    per_window = {}
    for name, base, ln in WINDOWS:
        inside = [a for a in addrs if base <= a < base + ln]
        below = [a for a in addrs if base - PAD <= a < base]
        above = [a for a in addrs if base + ln <= a < base + ln + PAD]
        per_window[name] = {
            "window": "0x%08X..0x%08X" % (base, base + ln),
            "distinct_addresses_inside": len(inside),
            "distinct_addresses_below": len(below),
            "distinct_addresses_above": len(above),
            "inside": ["0x%08X" % a for a in inside[:24]],
            "lowest_seen": "0x%08X" % min(addrs) if addrs else None,
            "highest_seen": "0x%08X" % max(addrs) if addrs else None,
        }

    # contiguity: a sweeping walk shows a constant stride
    strides = Counter(b - a for a, b in zip(addrs, addrs[1:])) if len(addrs) > 1 else Counter()
    by_frame = defaultdict(int)
    for e in mine:
        by_frame[e.get("frame")] += 1

    inside_total = sum(w["distinct_addresses_inside"] for w in per_window.values())
    only_writes = [e for e in mine if str(e.get("type", "")).startswith("w")]

    out = {
        "_comment": "Characterisation of the campaign's unenumerated PC. Regenerate: "
                    "tools/phase4_e16_speculative_read_probe.py",
        "generated": str(date.today()),
        "movie": str(movie.relative_to(ROOT)),
        "suspect_pc_in_log": SUSPECT,
        "actual_access_instruction": "0x80010BF4  lhu $t9,0($t9)  (accessLog reports the "
                                     "PC after the access)",
        "why_static_work_missed_it": {
            "scope": "0x80010BF4 is in no function in analysis/functions_resident.txt; the "
                     "emitter entry at 0x80010000 is 724 bytes and ends at 0x800102D4, which "
                     "is the loop head 0x80010C88 jumps back to.",
            "form": "the base register $s1 is not a lui constant, so the access is not "
                    "region-formed and the affine census is structurally blind to it -- "
                    "fixing the function list alone would NOT have surfaced it.",
        },
        "total_events_all_pcs": len(events),
        "pc_histogram": {k: v for k, v in all_pcs.most_common(20)},
        "control_fired": control_fired,
        "final_playback_index": final_index,
        "movie_frames": frames,
        "watches_laid": nwatch,
        "pad_bytes": PAD,
        "ring_saturated": len(events) >= 200000,
        "events_from_this_pc": len(mine),
        "access_types": dict(types),
        "writes_from_this_pc": len(only_writes),
        "distinct_addresses": len(addrs),
        "address_stride_histogram": {str(k): v for k, v in strides.most_common(6)},
        "frames_touched": len(by_frame),
        "per_window": per_window,
        "addresses_inside_any_window": inside_total,
        "verdict": None,
    }

    if len(events) >= 200000:
        out["verdict"] = ("SATURATED -- the 200,000-event ring filled, so absence of the "
                          "suspect PC proves nothing: its events may have been evicted. "
                          "Re-run with --pad 0.")
    elif not control_fired:
        out["verdict"] = ("INCONCLUSIVE -- no loader clear fired, so the watch cannot be "
                          "shown to have engaged (%d events total, playback reached %s of "
                          "%d frames). A zero here means nothing; fix the run, not the "
                          "conclusion." % (len(events), final_index, frames))
    elif not mine:
        out["verdict"] = ("NOT REPRODUCED -- the watch engaged (%d events, control fired) "
                          "but this PC did not fire in this movie." % len(events))
    elif only_writes:
        out["verdict"] = ("CONSUMER AND MUTATOR -- %d WRITES from this PC. E16's frontier is "
                          "wrong: this is an unenumerated writer, not a stray read."
                          % len(only_writes))
    elif inside_total == 0:
        out["verdict"] = ("COLLATERAL -- %d reads, zero of them inside any E16 window; they "
                          "land in the padding around it. The widened watch caught a "
                          "neighbouring array's walk, and the original 160/32/32-byte watch "
                          "reported the PC only because the watch is per-region. E16's tables "
                          "are not read by this code." % len(mine))
    else:
        out["verdict"] = ("READS INSIDE THE WINDOW -- %d distinct in-window addresses, read "
                          "only (no writes). Consistent with the load being hoisted past its "
                          "own bounds check at 0x80010BF8 and the value discarded, but that "
                          "makes it a real reader of these bytes for enumeration purposes: "
                          "add it to the enumerated set with this characterisation."
                          % inside_total)

    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"events from {SUSPECT}: {len(mine)}   types: {dict(types)}")
    print(f"distinct addresses: {len(addrs)}   inside a window: {inside_total}")
    for n, w in per_window.items():
        print(f"  {n}: inside={w['distinct_addresses_inside']} "
              f"below={w['distinct_addresses_below']} above={w['distinct_addresses_above']}")
    print("\n" + out["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
