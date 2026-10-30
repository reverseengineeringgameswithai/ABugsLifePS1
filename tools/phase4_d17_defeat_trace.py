#!/usr/bin/env python3
"""D17 bird: what the defeat transition actually is, and who causes it.

The row's central binding says defeat is "an instantaneous vm_ip jump to a COMPLETELY
DIFFERENT part of the shared mover-VM bytecode (0x800776ac 'park_arrive_stop' /
0x800776ae 'jump_back')". Those labels are fiction -- see
EXP_2026-08-04_mover_vm_indistinguishable_opcodes. Decoded properly:

    0x800776AC   stream 7   -> handler 0x8004C818 = the interpreter's LOOP TAIL (no body)
    0x800776AE   stream -1  -> jump_back [1] -> 0x800776AC

so the "different part of the bytecode" is an INFINITE DO-NOTHING LOOP: yield, jump
back, forever. Defeat parks the bird's mover-VM in a null program -- its AI is HALTED.

And the circling state is not a "park_seek" either. 0x8007788C sits inside

    0x80077878  set_byte_params [-64,-64]
    0x8007787E  anim_clip_load [0,13]
    0x80077884  wait_random [63,32]
    0x8007788A  random_dir_step
    0x8007788C  <- yield        (the IP the row saw it "parked" at)
    0x8007788E  jump_back -> 0x80077884

i.e. the same wait/random-step wander loop Thumper runs, resting on the yield each tick.

Three things this run answers that the label reading could not:
  1. WHO writes +0x70 at the transition -- the PC that installs the halt program is the
     code that decides "defeated", which the row never identified.
  2. The exact damage-instruction PC (the row records -4/hit as behavioural, "not traced").
  3. If the VM is halted, what moves the bird during the "retreat"? Something other than
     the mover-VM must, and the position writer PCs will say what.

    tools/phase4_d17_defeat_trace.py --port 23700
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
ACTOR_STRIDE = 0x84
BIRD_PROGRAM = (0x80077878, 0x80077894)     # the wander loop the bird circles in
HALT_PROGRAM = (0x800776AC, 0x800776B4)     # yield + jump-back-to-yield
IP_OFF = 0x70

FIELDS = [
    (0x04, 4, "position X (physically interpolated)"),
    (0x08, 4, "position Y"),
    (0x0C, 4, "position Z"),
    (0x5C, 2, "flags"),
    (0x6E, 2, "hp"),
    (0x70, 4, "mover-VM IP"),
]


def s32(v):
    return v - 0x100000000 if v & 0x80000000 else v


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
    ap.add_argument("--port", type=int, default=23700)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--settle", type=float, default=20.0)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json", type=Path, default=ROOT / "analysis/phase4_d17_defeat.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/d17-defeat")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "D17_bird",
        "question": ("what the defeat transition IS, who causes it, and what moves the "
                     "bird once its VM is halted"),
        "movie": str(args.movie.relative_to(ROOT)),
        "static_basis": {
            "halt_program": {
                "range": "0x800776AC..0x800776B4",
                "decode": ("0x800776AC stream 7 -> handler 0x8004C818, the interpreter's "
                           "shared LOOP TAIL (no operation body); 0x800776AE jump_back "
                           "[1] -> 0x800776AC. An infinite do-nothing loop."),
                "meaning": ("defeat parks the mover-VM in a NULL program -- the bird's AI "
                            "is halted. The row's 'park_arrive_stop' label is fiction."),
            },
            "wander_program": {
                "range": "0x80077878..0x80077894",
                "decode": ("set_byte_params / anim_clip_load / wait_random[63,32] / "
                           "random_dir_step / yield@0x8007788C / jump_back -> wait_random"),
                "meaning": ("the 'circling' IP 0x8007788C is the YIELD inside an ordinary "
                            "wait+random-step wander loop -- the same shape Thumper runs, "
                            "not a 'park_seek'"),
            },
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

        # Locate the bird by its VM IP lying inside its own wander program -- derived,
        # not a hard-coded slot. It has NO species callback (species 30 -> the common
        # arm), so the callback-pointer trick used for Thumper is unavailable here.
        c.call("debugger.resume", {})
        time.sleep(args.settle)
        c.call("debugger.pause", {})
        blob = rd(SCAN_LO, SCAN_HI - SCAN_LO)
        base = None
        for off in range(0, len(blob) - ACTOR_STRIDE, 4):
            a = SCAN_LO + off
            if (a - SCAN_LO) % 4:
                continue
            ip = int.from_bytes(blob[off + IP_OFF:off + IP_OFF + 4], "little")
            if BIRD_PROGRAM[0] <= ip < BIRD_PROGRAM[1]:
                hp = s16(int.from_bytes(blob[off + 0x6E:off + 0x70], "little"))
                if 0 < hp <= 120:
                    base = a
                    out["located"] = {"addr": "0x%08X" % a, "hp_at_settle": hp,
                                      "vm_ip_at_settle": "0x%08X" % ip}
                    break
        if base is None:
            out["error"] = ("no actor found with its VM IP inside the bird wander program "
                            "-- raise --settle, or the bird is not yet spawned")
            print(json.dumps(out, indent=1))
            return 1

        c.call("accessLog.clear", {})
        for o, n, lab in FIELDS:
            c.call("accessLog.addWatch", {"address": "0x%08x" % (base + o), "length": n,
                                          "type": "write", "max_events": 60000})
            watch[base + o] = lab

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
        r = by.setdefault(b0, {"label": watch[b0], "count": 0, "writers": {}, "seq": []})
        r["count"] += 1
        pc = str(e.get("instruction_pc") or e.get("pc") or "").lower()
        r["writers"][pc] = r["writers"].get(pc, 0) + 1
        v = e.get("new_value")
        if v is not None:
            r["seq"].append({"f": e.get("frame"), "pc": pc, "v": v})

    ip_rec = by.get(base + 0x70, {"seq": [], "writers": {}})
    hp_rec = by.get(base + 0x6E, {"seq": [], "writers": {}})

    # the frame the VM is parked in the halt loop
    halt = [s for s in ip_rec["seq"] if HALT_PROGRAM[0] <= s["v"] < HALT_PROGRAM[1]]
    first_halt = halt[0] if halt else None

    # hp deltas, to pin the damage instruction
    dmg = []
    prev = None
    for s in hp_rec["seq"]:
        v = s16(s["v"] & 0xFFFF)
        if prev is not None and v < prev:
            dmg.append({"f": s["f"], "pc": s["pc"], "from": prev, "to": v,
                        "delta": v - prev})
        prev = v

    # who moves the bird AFTER the VM is halted
    post = {}
    if first_halt:
        for o in (0x04, 0x08, 0x0C):
            r = by.get(base + o)
            if not r:
                continue
            w = {}
            for s in r["seq"]:
                if s["f"] and first_halt["f"] and s["f"] > first_halt["f"]:
                    w[s["pc"]] = w.get(s["pc"], 0) + 1
            post[watch[base + o]] = sorted(w.items(), key=lambda kv: -kv[1])[:4]

    out["by_field"] = {
        "0x%08X" % a: {"label": r["label"], "writes": r["count"],
                       "writer_pcs": sorted(r["writers"].items(), key=lambda kv: -kv[1])[:6]}
        for a, r in sorted(by.items())
    }
    out["findings"] = {
        "1_defeat_installs_a_halt_program": {
            "first_halt_frame": first_halt["f"] if first_halt else None,
            "installed_by_pc": first_halt["pc"] if first_halt else None,
            "ip_values_seen": sorted({"0x%08X" % s["v"] for s in ip_rec["seq"]}),
            "verdict": ("the VM IP is parked in the 0x800776AC null loop -- the bird's AI "
                        "is HALTED, not 'stopped on arrival'" if first_halt else
                        "the halt program was never entered in this run"),
        },
        "2_damage_instruction": {
            "hp_decrements": dmg[:20],
            "distinct_damage_pcs": sorted({d["pc"] for d in dmg}),
            "deltas": sorted({d["delta"] for d in dmg}),
            "verdict": ("the row recorded -4/hit as behavioural and untraced; these are "
                        "the actual writer PCs"),
        },
        "3_what_moves_the_bird_after_the_halt": {
            "position_writers_after_halt": post,
            "verdict": ("with the mover-VM halted, any continued motion must come from "
                        "these PCs -- if empty, the bird stops moving entirely and the "
                        "'retreat' is animation, not translation"),
        },
    }

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"located": out.get("located"), "frames": out.get("frames"),
                      "ring_truncated": out.get("ring_truncated"),
                      "findings": out["findings"]}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
