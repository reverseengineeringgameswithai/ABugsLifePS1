#!/usr/bin/env python3
"""Validate recorded movies against E16's table windows -- automatically.

WHY THIS EXISTS
---------------
The operator cannot tell, while playing, whether a recording will turn out to be
usable. Asking them to watch for something is the wrong design: the check belongs
here. Record normally; this says which movies are usable and which need redoing.

It also removes the failure that cost a full run earlier -- reading "no writes"
as a clean result when the instrument simply never engaged.

WHAT IT CHECKS, PER MOVIE
-------------------------
1. OCCUPANCY   the 0x30..0x57 table must reach >= 30 populated slots at some
               point. From a hub save state it starts populated (~38); from boot
               it climbs during the frontend. Either way, if it never populates,
               the movie is not exercising the state under test.
2. CONTROL     the loader's init clears (0x8003A3BC / 0x8003A3C0) must fire, or
               the bulk zero at 0x8005F6A4. These run on every level load, so
               their presence proves the watch engaged AND a load happened. This
               is the positive control; without it a clean result means nothing.
3. FALSIFIER   every write/read event's PC must be in the enumerated set. A PC
               outside it is the thing the campaign is looking for: something
               reaching these tables that the static frontier did not predict.

A movie is USABLE only if 1 and 2 hold. If 3 finds an unenumerated PC the movie
is still usable -- it has found something, which is the point.

Usage:
  python3 tools/phase4_e16_validate_movies.py --movies movies/Phase4/Interpreter/L01.movie.json ...
  python3 tools/phase4_e16_validate_movies.py --glob 'movies/Phase4/Interpreter/E16_*.movie.json'
"""
from __future__ import annotations

import argparse
import glob as globmod
import json
import struct
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
TABLES = [("markers_0x30_0x57", 0x8009B5A8, 160),
          ("markers_0x28_0x2F", 0x8009C210, 32),
          ("markers_0x58_0x5F", 0x800A65B0, 32)]

# Every PC observed touching these tables in the proven boot -> frontend -> Clover
# run (analysis/phase4_e16_table_read_watch.json), plus the BIOS memset.
ENUMERATED = {
    "0x8003bf4c": "loader registration store, markers 0x30..0x57",
    "0x8003b9d0": "loader registration store, markers 0x28..0x2F",
    "0x8003bc58": "loader registration store, markers 0x58..0x5F",
    "0x8003a3bc": "loader init clear, 0x28..0x2F table",
    "0x8003a3c0": "loader init clear, 0x58..0x5F table",
    "0x8005f6a4": "bulk zero (entry0)",
    "0x8003c924": "level_texture_stage read",
    "0x8003c3c4": "vram_upload_wait read (0x28..0x2F)",
    "0x8003c5f0": "vram_upload_wait read (0x58..0x5F)",
    "0xbfc0d868": "BIOS memset during boot",
    # Found BY this campaign in LEVEL01/02/05/10, then characterised
    # (analysis/phase4_e16_speculative_read_probe.json). It is a reader of these
    # bytes but not a CONSUMER of them -- see INCIDENTAL below.
    "0x80010bf8": "mesh emitter's hoisted load, 0x80010BF4 -- INCIDENTAL, see INCIDENTAL",
}
# the hoisted-load family counts as enumerated; see INCIDENTAL below for why
CONTROL_PCS = {"0x8003a3bc", "0x8003a3c0", "0x8005f6a4"}

# PCs that touch a window without being able to mean anything by it.
#
# 0x80010BF4 `lhu $t9,0($t9)` sits in per_object_mesh_draw_payload_emitter, whose
# body the function census had dropped entirely. The compiler hoisted it above
# its own range check:
#
#     0x80010bec  sltu $a3, $t9, $s5     ; range test computed
#     0x80010bf0  add  $t9, $t9, $s1     ; base is a REGISTER, not a lui constant
#     0x80010bf4  lhu  $t9, 0($t9)       ; load happens regardless
#     0x80010bf8  beq  $a3, $zero, ...   ; range test acted on, one instruction late
#
# and at 0x80010C80 the loaded $t9 is dead (`bne $s2,$zero` / `addi $s0,$s0,12`).
#
# MEASURED, and the volume varies by level. An earlier note here said "1 read of
# 1 address on 1 frame", which was true of LEVEL01 only; corrected:
#   0x80010BF8  53 reads over 7 of the 16 levels (1, 2, 7, 29, 1, 2, 11).
#               LEVEL01 was the single read of 0x800A65C0.
#   0x80010DA0  51 reads on LEVEL15 across 8 distinct addresses -- every word of
#               the 32-byte 0x58..0x5F table.
# Both read-only. Of all 1,930 campaign events, not one from these PCs is a write,
# which the idiom guarantees structurally: the scan matches loads only.
#
# What makes it safe to classify rather than merely small: no code in the entire
# text segment -- including the 46 KB the function census omits -- can materialise
# a pointer into these windows outside the already-enumerated set
# (analysis/phase4_e16_address_materialization.json). A register-based access that
# lands here therefore CANNOT be deliberate. This one is an overrun past a bounds
# check whose result is discarded.
#
# It is still enumerated, not excused: it reads the bytes, so it belongs in the
# set. It just cannot inform anything about what consumes them.
INCIDENTAL_MEASURED = {
    "0x80010bf8": ("per_object_mesh_draw_payload_emitter, load hoisted above its own "
                   "bounds check at 0x80010BF8; result discarded. 53 reads over 7 "
                   "campaign levels, read-only. No materialisation site exists for these "
                   "windows outside the enumerated set, so it cannot be deliberate."),
    "0x80010da0": ("the sibling copy of the same loop body 424 bytes later, same idiom. "
                   "51 reads on LEVEL15 across 8 distinct addresses -- the whole 32-byte "
                   "0x58..0x5F table -- read-only."),
}

# THE WHOLE FAMILY, read from the static scan rather than typed here.
#
# The campaign found 0x80010BF8 in LEVEL01, then 0x80010DA0 in LEVEL15 -- the
# identical instruction sequence 424 bytes away, in a duplicated copy of the same
# loop. Discovering these one movie at a time is not a method, so
# tools/hoisted_load_idiom_scan.c enumerates every load the compiler scheduled
# above the branch that bounds it: 22 sites, all in the geometry emitters.
#
# Admitting the family is not "assume the rest are fine". It rests on two static
# results, neither of which is runtime silence:
#   * each site is machine-matched to the hoisted-load pattern, so its result is
#     discarded on exactly the path where the address is out of range;
#   * no materialisation site can form a pointer into these windows outside the
#     enumerated set, so NO register-based access here can be deliberate --
#     which is a property of the windows, not of any particular PC.
# Loaded from the artifact so the set cannot drift away from the scan.
def _load_hoisted_family() -> dict:
    p = ROOT / "analysis/hoisted_load_idiom_scan.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    return {h["logged_pc"].lower():
            "hoisted-load idiom at %s (%s), result discarded on the out-of-range path"
            % (h["load_pc"], h["width"]) for h in d.get("hits", [])}


INCIDENTAL = {**_load_hoisted_family(), **INCIDENTAL_MEASURED}


def read_u32s(c, addr, count):
    hx = c.call("debugger.readMemory",
                {"address": "0x%08x" % addr, "length": count * 4})["hex"]
    return list(struct.unpack("<%dI" % count, bytes.fromhex(hx)))


def drain(c, sink, seen):
    off, trunc = 0, False
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        ev = page.get("events", [])
        trunc |= page.get("truncated", False)
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
    return trunc


def validate(movie: Path, port: int, config_dir: str, step: int) -> dict:
    subprocess.run([str(ROOT / "tools/launch_repro_playback.sh"),
                    "--config-dir", config_dir, "--port", str(port),
                    "--disc", str(DISC), "--execution-mode", "Interpreter"], check=True)
    row: dict = {"movie": str(movie.relative_to(ROOT))}
    c = DebuggerClient("127.0.0.1", port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(900)
    events, seen, trunc, peak, start_occ = [], set(), False, 0, None
    try:
        # ORDER AND METHOD BOTH MATTER, and getting them wrong returns a clean-looking
        # zero. CLAUDE.md: "movie.advanceToFrame IS NOT EQUIVALENT TO 60 Hz PLAYBACK ...
        # the arm-phase fixup lands differently. Verify anything phase-sensitive at
        # 60 Hz." Every one of these recordings is state-anchored and most report
        # phase_delay_owed, so frame-stepping them captured 0 events on the first run.
        # Replay at 60 Hz with debugger.resume + poll, and arm the watches AFTER
        # startPlayback (the order proven in phase4_b06_b08_writer_union.py).
        row["movie_load"] = c.call("movie.load", {"path": str(movie)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        row["frames"] = st.get("frame_count")
        row["phase_delay_owed"] = st.get("phase_delay_owed")
        row["movie_version"] = st.get("movie_version")

        c.call("accessLog.clear", {})
        for name, base, ln in TABLES:
            c.call("accessLog.addWatch", {"address": "0x%08x" % base, "length": ln,
                                          "type": "readwrite", "label": name,
                                          "max_events": 200000})

        def occ():
            return sum(1 for v in read_u32s(c, TABLES[0][1], 40) if v)

        start_occ = occ()
        peak = start_occ
        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        budget = 60 + (row["frames"] or 0) / 30.0        # generous wall-clock allowance
        while time.time() - began < budget:
            time.sleep(1.5)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:                              # noqa: BLE001
                idx = last
            trunc |= drain(c, events, seen)
            try:
                peak = max(peak, occ())
            except Exception:                              # noqa: BLE001
                pass
            if idx == last:
                stalls += 1
                if stalls >= 6:
                    break
            else:
                stalls = 0
            last = idx
        row["final_playback_index"] = last
        trunc |= drain(c, events, seen)
    finally:
        try:
            c.call("accessLog.clear", {})
        except Exception:                                  # noqa: BLE001
            pass
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", config_dir], check=False)

    pcs = Counter(e["pc"] for e in events)
    unenumerated = {p: n for p, n in pcs.items()
                    if p not in ENUMERATED and p not in INCIDENTAL}
    incidental = {p: n for p, n in pcs.items() if p in INCIDENTAL}
    row.update({
        "events": len(events), "truncated": trunc,
        "occupancy_at_start": start_occ, "occupancy_peak": peak,
        "pcs": dict(pcs), "unenumerated_pcs": unenumerated,
        "check_occupancy": peak >= 30,
        "check_control": bool(CONTROL_PCS & set(pcs)),
        "check_falsifier_clean": not unenumerated,
        "incidental_pcs": incidental,
    })
    if not row["check_occupancy"]:
        row["verdict"] = ("UNUSABLE -- the tables never populated (peak %d slots). The "
                          "movie does not exercise the state under test; re-record from a "
                          "hub save state taken AFTER the frontend has finished loading."
                          % peak)
    elif not row["check_control"]:
        row["verdict"] = ("INCONCLUSIVE -- no loader clear or bulk zero fired, so the watch "
                          "cannot be shown to have engaged. A clean result here would mean "
                          "nothing. Re-record ensuring a level is actually entered.")
    elif unenumerated:
        row["verdict"] = ("USABLE AND IT FOUND SOMETHING -- %d PC(s) touched the tables that "
                          "the static frontier did not predict: %s"
                          % (len(unenumerated), ", ".join(sorted(unenumerated))))
    elif incidental:
        row["verdict"] = ("USABLE AND CLEAN -- tables populated (peak %d), control fired, "
                          "every one of %d events from an enumerated PC; %d of them from a "
                          "characterised INCIDENTAL PC (%s)."
                          % (peak, len(events), sum(incidental.values()),
                             ", ".join(sorted(incidental))))
    else:
        row["verdict"] = ("USABLE AND CLEAN -- tables populated (peak %d), control fired, "
                          "and every one of %d events came from an enumerated PC."
                          % (peak, len(events)))
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--movies", nargs="*", default=[])
    ap.add_argument("--glob", default="")
    ap.add_argument("--port", type=int, default=23474)
    ap.add_argument("--step", type=int, default=400)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_e16val")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_movie_validation.json"))
    ap.add_argument("--merge", action="store_true",
                    help="keep rows already in --out for movies not validated in this run")
    args = ap.parse_args()

    paths = [Path(m) for m in args.movies]
    if args.glob:
        paths += [Path(p) for p in sorted(globmod.glob(args.glob))]
    if not paths:
        print("no movies given", file=sys.stderr)
        return 2

    # MERGE exists because a campaign run silently destroyed something load-bearing.
    # The artifact carried the validator's own proof -- the run against
    # E02_FreshLoad_Clover, a movie with a known answer -- and overwriting it with
    # 16 campaign movies deleted that row, so the gate asserting "this validator was
    # proven before it was trusted" started failing. The proof and the campaign both
    # belong in the artifact; neither should evict the other.
    rows = []
    if args.merge and Path(args.out).exists():
        prior = json.loads(Path(args.out).read_text()).get("movies", [])
        names = {str(Path(m).name) for m in paths}
        rows = [r for r in prior if Path(str(r.get("movie", ""))).name not in names]
        print(f"merging {len(rows)} prior row(s) from {args.out}")
    for m in paths:
        if not m.is_absolute():
            m = ROOT / m
        print(f"--- validating {m.name}")
        try:
            rows.append(validate(m, args.port, args.config_dir, args.step))
        except Exception as e:                             # noqa: BLE001
            rows.append({"movie": str(m), "error": repr(e)[:300],
                         "verdict": "ERROR -- see error field"})
        print("    " + rows[-1].get("verdict", "?")[:150])

    out = {
        "_comment": "Automatic validation of recorded movies against E16's table windows. "
                    "The operator never has to watch for anything while playing. "
                    "Regenerate: tools/phase4_e16_validate_movies.py",
        "generated": str(date.today()),
        "enumerated_pcs": ENUMERATED,
        "incidental_pcs": INCIDENTAL,
        "checks": {
            "occupancy": "the 0x30..0x57 table must reach >= 30 populated slots",
            "control": "a loader clear or the bulk zero must fire -- proves the watch "
                       "engaged AND a level load happened",
            "falsifier": "every event PC must be in the enumerated set; anything else is "
                         "a find, not a failure",
        },
        "movies": rows,
        "summary": {
            "usable": sum(1 for r in rows if str(r.get("verdict", "")).startswith("USABLE")),
            "unusable_or_inconclusive": sum(
                1 for r in rows if str(r.get("verdict", "")).startswith(("UNUSABLE", "INCONCLUSIVE"))),
            "found_unenumerated_pcs": sorted(
                {p for r in rows for p in (r.get("unenumerated_pcs") or {})}),
            "movies_with_incidental_pcs": sorted(
                r["movie"] for r in rows if r.get("incidental_pcs")),
        },
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nusable: {out['summary']['usable']}/{len(rows)}")
    if out["summary"]["found_unenumerated_pcs"]:
        print("UNENUMERATED PCs FOUND:", out["summary"]["found_unenumerated_pcs"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
