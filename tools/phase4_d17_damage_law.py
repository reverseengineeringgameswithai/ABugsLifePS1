#!/usr/bin/env python3
"""D17: the bird's damage law -- why some hits are healed back.

The previous pass recorded a "two-phase fight": nine hits of -3 that the overlay restored
to 50, then hits of -4 that accumulated to the defeat threshold. Reading the overlay shows
it is NOT a phase. LEVEL01/LEVEL1.BIN 0x800B3F34..0x800B3F98:

    a1 = 0x800A0316                  ; the bird's HP (+0x6E)
    v0 = [a1]                        ; current HP
    v1 = [0x800B4420]                ; reference HP
    if (v0 == v1) skip               ; unchanged
    a0 = v1 - v0                     ; damage this hit
    if (a0 != 3)            skip     ; <-- only a 3-damage hit qualifies
    if ([0x800A6597] != 3)  skip     ; <-- ...and only with berry index 3
    if ([0x800B441C] < 5) counter++
    [a1] = v1                        ; RESTORE (delay slot: always runs once reached)

So the restore is per-hit and BERRY-TYPE DEPENDENT: berry index 3 does 3 damage and is
healed back; the other berry does 4 and sticks (0x800B3FA4 accepts it, updates the
reference, plays sound 103). The "two phases" in the earlier trace were the player
switching berries.

This run tests that directly: it timelines the equipped berry index 0x800A6597 against
every HP change, and reports the index in force at each hit.

It also settles what the 0x800B441C counter gates. 0x800B3E50 reads it: while it is < 5,
the overlay writes 0xFFFDCFF0 into the bird's anchor Y (+0x2C) and target Y (+0x38) and
clears flag bit 0x02 -- i.e. it LAUNCHES THE BIRD HIGH. That is the row's "obtaining a
gold berry launches the bird higher", capped at 5 launches.

    tools/phase4_d17_damage_law.py --port 23710
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
SCAN_LO, SCAN_HI = 0x8009F000, 0x800A1000
ACTOR_STRIDE, IP_OFF = 0x84, 0x70
BIRD_PROGRAM = (0x80077878, 0x80077894)

BERRY_INDEX = 0x800A6597       # the index the restore gate tests against 3
KNOCKUP_COUNTER = 0x800B441C   # gates the launch-high block at 0x800B3E50, cap 5
REFERENCE_HP = 0x800B4420      # the overlay's copy of the bird's HP


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


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
                    default=ROOT / "movies/Phase4/Interpreter/D17_Goldberry.movie.json")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23710)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--settle", type=float, default=20.0)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_d17_damage_law.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/d17-dmg")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "D17_bird",
        "question": "why some hits are healed back, and what the 0x800B441C counter gates",
        "movie": str(args.movie.relative_to(ROOT)),
        "static_basis": {
            "restore_gate": ("LEVEL01/LEVEL1.BIN 0x800B3F5C: damage must be exactly 3; "
                             "0x800B3F70: [0x800A6597] must equal 3; then 0x800B3F8C "
                             "restores HP to the reference"),
            "accept_path": ("0x800B3FA4: a -4 hit matches reference-4, sets the hit flag, "
                            "plays sound 103, and updates the reference at 0x800B3FC4"),
            "counter_use": ("0x800B3E50 reads 0x800B441C; while < 5 it writes 0xFFFDCFF0 "
                            "into the bird's anchor Y (+0x2C) and target Y (+0x38) and "
                            "clears flag bit 0x02 -- the launch-high, capped at 5"),
        },
    }
    watch = {}
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(1200)
        st = c.call("movie.load", {"path": str(args.movie)})
        out["frames"] = st.get("frame_count")
        c.call("movie.startPlayback", {"load_start_state": True})

        def rd(a, n):
            return bytes.fromhex(c.call("debugger.readMemory",
                                        {"address": "0x%08x" % a, "length": n})["hex"])

        c.call("debugger.resume", {})
        time.sleep(args.settle)
        c.call("debugger.pause", {})
        blob = rd(SCAN_LO, SCAN_HI - SCAN_LO)
        base = None
        for off in range(0, len(blob) - ACTOR_STRIDE, 4):
            ip = int.from_bytes(blob[off + IP_OFF:off + IP_OFF + 4], "little")
            if BIRD_PROGRAM[0] <= ip < BIRD_PROGRAM[1]:
                hp = s16(int.from_bytes(blob[off + 0x6E:off + 0x70], "little"))
                if 0 < hp <= 120:
                    base = SCAN_LO + off
                    break
        if base is None:
            out["error"] = "bird not located; raise --settle"
            print(json.dumps(out, indent=1))
            return 1
        out["bird_addr"] = "0x%08X" % base
        out["berry_index_at_settle"] = rd(BERRY_INDEX, 1)[0]

        c.call("accessLog.clear", {})
        for a, n, lab in ((base + 0x6E, 2, "bird hp"),
                          (BERRY_INDEX, 1, "equipped berry index"),
                          (KNOCKUP_COUNTER, 4, "knock-up counter"),
                          (REFERENCE_HP, 4, "reference hp"),
                          (base + 0x2C, 4, "bird anchor Y")):
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

    idx_seq = by.get(BERRY_INDEX, {"seq": []})["seq"]
    hp_seq = by.get(base + 0x6E, {"seq": []})["seq"]

    def index_at(frame):
        """The last berry index written at or before this frame."""
        val = out.get("berry_index_at_settle")
        for s in idx_seq:
            if s["f"] is not None and frame is not None and s["f"] <= frame:
                val = s["v"] & 0xFF
            else:
                break
        return val

    hits, prev = [], None
    for s in hp_seq:
        v = s16(s["v"] & 0xFFFF)
        if prev is not None and v != prev:
            hits.append({"f": s["f"], "pc": s["pc"], "from": prev, "to": v,
                         "delta": v - prev, "berry_index": index_at(s["f"]),
                         "kind": ("RESTORE" if v > prev else "damage")})
        prev = v

    dmg = [h for h in hits if h["kind"] == "damage"]
    restores = [h for h in hits if h["kind"] == "RESTORE"]
    by_delta = {}
    for h in dmg:
        by_delta.setdefault(h["delta"], set()).add(h["berry_index"])

    out["by_field"] = {
        "0x%08X" % a: {"label": r["label"], "writes": len(r["seq"]),
                       "writer_pcs": sorted(r["writers"].items(), key=lambda kv: -kv[1])[:5],
                       "values": [x["v"] for x in r["seq"]][:40]}
        for a, r in sorted(by.items())
    }
    out["findings"] = {
        "berry_index_timeline": [{"f": s["f"], "v": s["v"] & 0xFF} for s in idx_seq][:40],
        "berry_index_distinct": sorted({s["v"] & 0xFF for s in idx_seq}),
        "hits": hits[:40],
        "damage_deltas_to_berry_indices": {str(k): sorted(v) for k, v in by_delta.items()},
        "restore_count": len(restores),
        "knockup_counter_values": [x["v"] for x in by.get(KNOCKUP_COUNTER, {"seq": []})["seq"]][:20],
        "verdict": None,
    }
    # the decisive correlation
    three = by_delta.get(-3, set())
    four = by_delta.get(-4, set())
    if three and four and not (three & four):
        out["findings"]["verdict"] = (
            "CONFIRMED berry-type dependent: -3 hits occur only with berry index %s and "
            "-4 hits only with index %s. The 'two-phase fight' was the player switching "
            "berries, not a phase." % (sorted(three), sorted(four)))
    elif three or four:
        out["findings"]["verdict"] = (
            "NOT SEPARABLE from this fixture: -3 indices %s, -4 indices %s. The berry "
            "index did not change in a way that isolates the two damage values, so the "
            "static gate stands unconfirmed live." % (sorted(three), sorted(four)))

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out["findings"][k] for k in
                      ("berry_index_distinct", "damage_deltas_to_berry_indices",
                       "restore_count", "knockup_counter_values", "verdict")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
