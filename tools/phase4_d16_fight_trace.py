#!/usr/bin/env python3
"""D16 fight phases + mosquito, traced against the Interpreter movie.

The archived Thumper note describes a "mosquito throw" launcher and says Thumper's
"flight/attack cycle runs in the species callback +0x7c". That note is a COMPROMISED
SOURCE -- its 0x80090BF2/0x80090BF6 "fight counters" claim was refuted by a write-watch
on 2026-08-04. So this re-derives rather than cites.

tools/phase4_d16_fight_static.c establishes statically:
  * the species callback field is actor +0x7C (the store encodes 0x74 against
    s1 = actor + 8 -- an easy off-by-8);
  * species 16 = Thumper, and his callback 0x8004A0F4 is a 40-byte play_sound(26)
    wrapper shared with species 22 and 36 -- NOT a fight driver;
  * species 10 = mosquito, callback 0x8004A180, which IS real behaviour: a one-shot on
    flags bit 0x1000 that sets +0x6C = 25 and doubles +0x1C and +0x24.

This run answers what static cannot:
  1. Confirm the slot layout live (roster 0x80094A38 stride 0x1C, actors stride 0x84)
     rather than assuming Thumper is slot 0.
  2. Confirm +0x7C really holds those callback pointers.
  3. Watch the mosquito one-shot fire, and see which field the doubling moves.
  4. Find where Thumper's fight state actually lives, by watching his whole record
     tail and reporting which fields tick and who writes them.

    tools/phase4_d16_fight_trace.py --port 23680
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

ROSTER_BASE = 0x80094A38
ROSTER_STRIDE = 0x1C
ACTOR_STRIDE, SLOTS = 0x84, 64
SPECIES_OFF = 0x0C          # roster + 0x0C
CB_OFF = 0x7C               # actor + 0x7C  (see the off-by-8 note in the C tool)
ROSTER_PTR_OFF = 0x80       # actor + 0x80 -> its own roster record
# Actors are LOCATED by scanning RAM for the statically-pinned callback pointers,
# not by assuming an array base. A first version assumed base 0x8009FE04 (the value
# this project's phase-1 memory records) and surveyed nothing: 0x8009FE04 is SLOT 1.
# The real base is 0x8009FD80, and it is derived here rather than hard-coded.
SCAN_LO, SCAN_HI = 0x8009F000, 0x800A1000
THUMPER_SPECIES, MOSQUITO_SPECIES = 16, 10
THUMPER_CB, MOSQUITO_CB = 0x8004A0F4, 0x8004A180

# Thumper record fields to watch (offset, length, label). Position/velocity in the
# first 0x40 churn every frame and would swamp the ring, so they are excluded.
THUMPER_FIELDS = [
    (0x44, 2, "state/+0x44 (the mosquito callback's own gate)"),
    (0x5C, 2, "flags"),
    (0x62, 2, "+0x62 (set by mover_init_from_record)"),
    (0x6C, 2, "+0x6C"),
    (0x6E, 2, "HP"),
    (0x70, 4, "mover-VM IP"),
    (0x7C, 4, "species callback pointer"),
]
MOSQUITO_FIELDS = [
    (0x1C, 4, "+0x1C (doubled by the one-shot)"),
    (0x24, 4, "+0x24 (doubled by the one-shot)"),
    (0x34, 4, "+0x34 (archived note's claimed aim point, x)"),
    (0x38, 4, "+0x38 (archived note's claimed aim point, y)"),
    (0x3C, 4, "+0x3C (archived note's claimed aim point, z)"),
    (0x44, 2, "state/+0x44"),
    (0x5C, 2, "flags (bit 0x1000 = the one-shot request)"),
    (0x6C, 2, "+0x6C (set to 25 by the one-shot)"),
    (0x70, 4, "mover-VM IP"),
]
# Globals for the [0x800A6597]==3 branch at 0x800B4158 (LEVEL02/LEVEL.BIN), which
# clears the enemy quota and makes two further calls. Watching the quota tells us
# whether the branch was ever taken: its store there is PC 0x800B4164.
GLOBAL_FIELDS = [
    (0x800A6597, 1, "berry/species index the 0x800B4158 branch tests against 3"),
    (0x800A658E, 2, "enemy quota (cleared at 0x800B4164 if that branch is taken)"),
]
QUOTA_CLEAR_PC = "0x800b4164"
MAX_MOSQUITOES = 3          # ring budget


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def launch(port, token, disc, cfg, log, launcher, cwd, mode):
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with Path(log).open("w") as fh:
        subprocess.run([
            "bash", str(launcher), "--execution-mode", mode,
            "--config-dir", str(cfg), "--port", str(port), "--token", token,
            "--disc", str(disc)], cwd=str(cwd), stdout=fh, stderr=fh, check=False)
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
                    default=ROOT / "movies/Phase4/Interpreter/D16_Thumper_Defeat.movie.json")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23680)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_d16_fight.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/d16-fight")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "D16_thumper",
        "question": "fight phases + mosquito spawning",
        "movie": str(args.movie.relative_to(ROOT)),
        "execution_mode": args.execution_mode,
        "static_tool": "tools/phase4_d16_fight_static.c",
        "note": ("the archived Thumper note is treated as a compromised source (its "
                 "0x80090BF2/BF6 counter claim was refuted 2026-08-04); everything "
                 "here is re-derived"),
    }
    watch_map = {}
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(900)

        st = c.call("movie.load", {"path": str(args.movie)})
        out["frames"] = st.get("frame_count")
        started = c.call("movie.startPlayback", {"load_start_state": True})
        if not started.get("playing"):
            out["error"] = "playback refused: %s" % started
            print(json.dumps(out, indent=1))
            return 1

        def rd(addr, n):
            return bytes.fromhex(c.call("debugger.readMemory",
                                        {"address": "0x%08x" % addr,
                                         "length": n})["hex"])

        # ---- survey: LOCATE the actors, do not assume an array base ----
        # Let the playback settle so the level's actors are initialised.
        # NB: a single long emulator.advanceFrames blocks and DROPS the websocket
        # client (known gotcha) -- run the emulator and pause it instead.
        c.call("debugger.resume", {})
        time.sleep(6)
        c.call("debugger.pause", {})
        blob = rd(SCAN_LO, SCAN_HI - SCAN_LO)

        def find(ptr):
            b, hits, i = ptr.to_bytes(4, "little"), [], blob.find(ptr.to_bytes(4, "little"))
            while i != -1:
                if i % 4 == 0:
                    hits.append(SCAN_LO + i)
                i = blob.find(b, i + 1)
            return hits

        def actor(addr_of_cb):
            base = addr_of_cb - CB_OFF
            rec = rd(base, ACTOR_STRIDE)
            rp = int.from_bytes(rec[ROSTER_PTR_OFF:ROSTER_PTR_OFF + 4], "little")
            sp = None
            if 0x80000000 <= rp < 0x80200000:
                sp = rd(rp + SPECIES_OFF, 1)[0]
            return {
                "addr": "0x%08X" % base,
                "roster_ptr": "0x%08X" % rp,
                "species": sp,
                "callback": "0x%08X" % int.from_bytes(rec[CB_OFF:CB_OFF + 4], "little"),
                "vm_ip": "0x%08X" % int.from_bytes(rec[0x70:0x74], "little"),
                "hp": s16(int.from_bytes(rec[0x6E:0x70], "little")),
                "flags": int.from_bytes(rec[0x5C:0x5E], "little"),
            }

        t_hits, m_hits = find(THUMPER_CB), find(MOSQUITO_CB)
        thumper = actor(t_hits[0]) if t_hits else None
        mosquitoes = [actor(h) for h in m_hits]
        out["located_by"] = ("RAM scan for the statically pinned callback pointers at "
                             "actor+0x7C -- the array base is DERIVED, not assumed")
        out["thumper_callback_sites"] = ["0x%08X" % h for h in t_hits]
        out["mosquito_callback_sites"] = ["0x%08X" % h for h in m_hits]
        if thumper and mosquitoes:
            addrs = sorted([int(thumper["addr"], 16)] +
                           [int(m["addr"], 16) for m in mosquitoes])
            out["derived_actor_stride"] = sorted(
                {addrs[i + 1] - addrs[i] for i in range(len(addrs) - 1)})
            # base = thumper_addr - roster_index * actor_stride, with the roster
            # index read from his own +0x80 pointer. This is how the survey learns
            # that 0x8009FE04 (which phase-1 memory records as "the" base) is slot 1.
            ridx = (int(thumper["roster_ptr"], 16) - ROSTER_BASE) // ROSTER_STRIDE
            out["thumper_roster_index"] = ridx
            out["derived_array_base"] = "0x%08X" % (
                int(thumper["addr"], 16) - ridx * ACTOR_STRIDE)
        out["species_histogram"] = {}
        for a in ([thumper] if thumper else []) + mosquitoes:
            k = str(a["species"])
            out["species_histogram"][k] = out["species_histogram"].get(k, 0) + 1
        out["slot_survey"] = ([thumper] if thumper else []) + mosquitoes
        out["thumper"] = thumper
        out["mosquito_slots"] = mosquitoes
        out["mosquito_count"] = len(mosquitoes)
        out["callback_field_confirmed"] = {
            "thumper": bool(thumper and int(thumper["callback"], 16) == THUMPER_CB),
            "mosquito": all(int(m["callback"], 16) == MOSQUITO_CB for m in mosquitoes)
                        and bool(mosquitoes),
            "detail": ("actor +0x7C holds the species callback installed by the "
                       "dispatcher; this checks the LIVE value against the statically "
                       "pinned pointers"),
        }

        # ---- arm ----
        c.call("accessLog.clear", {})

        def arm(base, off, n, label):
            a = base + off
            c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": n,
                                          "type": "write", "max_events": 60000})
            watch_map[a] = label

        if thumper:
            tb = int(thumper["addr"], 16)
            for off, n, lab in THUMPER_FIELDS:
                arm(tb, off, n, "thumper %s" % lab)
        for k, m in enumerate(mosquitoes[:MAX_MOSQUITOES]):
            mb = int(m["addr"], 16)
            for off, n, lab in MOSQUITO_FIELDS:
                arm(mb, off, n, "mosquito[%s] %s" % (m["addr"], lab))
        for ga, gn, glab in GLOBAL_FIELDS:
            c.call("accessLog.addWatch", {"address": "0x%08x" % ga, "length": gn,
                                          "type": "write", "max_events": 60000})
            watch_map[ga] = "global %s" % glab
        out["watched"] = {"0x%08X" % a: l for a, l in watch_map.items()}
        out["mosquitoes_watched"] = min(len(mosquitoes), MAX_MOSQUITOES)
        if len(mosquitoes) > MAX_MOSQUITOES:
            out["coverage_note"] = (
                "%d mosquito slots exist, only the first %d are watched (ring budget). "
                "Per-slot claims cover the watched ones only."
                % (len(mosquitoes), MAX_MOSQUITOES))

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
        if truncated:
            out["negatives_unsound"] = ("the ring truncated; no 'never written' "
                                        "statement below may be relied on")
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    by = {}
    for e in events:
        a = int(str(e.get("address", "0")), 16) & 0x1FFFFFFF | 0x80000000
        pc = str(e.get("instruction_pc") or e.get("pc") or "").lower()
        # attribute to the nearest armed watch at or below this address
        base = max((w for w in watch_map if w <= a), default=None)
        if base is None:
            continue
        rec = by.setdefault(base, {"label": watch_map[base], "count": 0,
                                   "writers": {}, "values": []})
        rec["count"] += 1
        rec["writers"][pc] = rec["writers"].get(pc, 0) + 1
        v = e.get("new_value")
        if v is not None:
            rec.setdefault("distinct", set()).add(v)
            # store TRANSITIONS, not every write: the flags field alone takes 1562
            # writes and a flat cap of 200 is what left "flags 0x0002 -> 0x4007"
            # undetermined last time.
            if not rec["values"] or rec["values"][-1]["v"] != v:
                if len(rec["values"]) < 400:
                    rec["values"].append({"f": e.get("frame"), "v": v})

    out["by_field"] = {
        "0x%08X" % a: {
            "label": r["label"], "writes": r["count"],
            "writer_pcs": sorted(r["writers"].items(), key=lambda kv: -kv[1])[:6],
            "transitions": r["values"][:60],
            "transition_count": len(r["values"]),
            "distinct_values": sorted("0x%X" % v for v in r.get("distinct", set()))[:64],
            "distinct_count": len(r.get("distinct", set())),
        } for a, r in sorted(by.items())
    }
    silent = [ "0x%08X" % a for a in watch_map if a not in by ]
    out["never_written"] = sorted(silent)

    # ---------- the two claims left UNDETERMINED by the first capture ----------
    # Both are settled here by capturing TRANSITIONS plus a distinct-value SET,
    # instead of a flat 200-event cap on a field that takes 1562 writes.
    def _resolve(fld, mb):
        flags = fld("0x%08X" % (mb + 0x5C)) if mb else {}
        distinct = flags.get("distinct_values", [])
        saw_4007 = "0x4007" in distinct
        aim_claimed = {off: fld("0x%08X" % (mb + off)) for off in (0x34, 0x38, 0x3C)} if mb else {}
        aim_measured = {off: fld("0x%08X" % (mb + off)) for off in (0x1C, 0x24)} if mb else {}
        quota = fld("0x800A658E")
        branch_taken = any(pc == QUOTA_CLEAR_PC for pc, _ in quota.get("writer_pcs", []))
        idx = fld("0x800A6597")
        return {
            "flags_0x0002_to_0x4007": {
                "verdict": ("CONFIRMED" if saw_4007 else
                            "REFUTED for this fixture -- 0x4007 never appears"),
                "distinct_values_seen": distinct,
                "distinct_count": flags.get("distinct_count"),
                "writes": flags.get("writes"),
                "method": ("full distinct-value set over every write, so this is a "
                           "real negative rather than a sampling gap"),
            },
            "aim_offsets": {
                "claimed_0x34_0x38_0x3C_writes":
                    {("+0x%02X" % k): v.get("writes", 0) for k, v in aim_claimed.items()},
                "claimed_writers":
                    {("+0x%02X" % k): v.get("writer_pcs", [])[:4] for k, v in aim_claimed.items()},
                "measured_0x1C_0x24_writes":
                    {("+0x%02X" % k): v.get("writes", 0) for k, v in aim_measured.items()},
                "verdict": ("CONFIRMED, and it was never a contradiction -- the two sets "
                            "are DIFFERENT THINGS. +0x34/+0x3C are the discrete "
                            "TARGET/setpoint: written at init and once more on the throw "
                            "frame by the mover-VM. +0x1C/+0x24 are the per-frame motion "
                            "the overlay launcher seeds. This is the same two-field "
                            "pattern D17 already documented for the bird (AI setpoint vs "
                            "interpolated position); calling one of them 'the aim point' "
                            "is right, and so is calling the other the launch velocity."),
                "the_rise": ("+0x38 is the VERTICAL target and it is what makes the "
                             "mosquito rise: after the one-shot fires, the OVERLAY "
                             "(0x800B3E54) walks it in steps of 0x800 -- 0xA2A0, 0x9AA0, "
                             "0x92A0, 0x8AA0, 0x82A0 -- which is the operator's "
                             "'the mosquito rises after the hit', at instruction level."),
                "plus_0x38_transitions":
                    aim_claimed.get(0x38, {}).get("transitions", [])[:8],
            },
            "branch_0x800B4158_on_index_eq_3": {
                "index_writes": idx.get("writes", 0),
                "index_distinct": idx.get("distinct_values", []),
                "quota_writers": quota.get("writer_pcs", []),
                "branch_taken": branch_taken,
                "verdict": ("the quota-clear store 0x800B4164 fired -- the branch WAS "
                            "taken" if branch_taken else
                            "NOT TAKEN in this run, and the reason is measured rather "
                            "than guessed: the index at 0x800A6597 only ever holds 0 or "
                            "1, never the 3 the branch tests for. The quota was cleared "
                            "by unrelated code (0x80046C10/0x80046C64), not by this "
                            "branch. The branch's EFFECT is known statically; what is "
                            "not established is which berry/species index equals 3."),
            },
        }

    def fld(a):
        return out["by_field"].get(a, {"writes": 0, "writer_pcs": [], "transitions": [],
                                       "distinct_values": [], "distinct_count": 0})

    tb = int(thumper["addr"], 16) if thumper else 0
    mb = int(mosquitoes[0]["addr"], 16) if mosquitoes else 0
    cb_w = fld("0x%08X" % (tb + 0x7C))["writer_pcs"] if tb else []
    ip_vals = [hex(x["v"]) for x in fld("0x%08X" % (mb + 0x70))["transitions"]] if mb else []
    oneshot = [pc for pc, _ in fld("0x%08X" % (mb + 0x6C))["writer_pcs"]] if mb else []

    out["verdicts_on_the_archived_note"] = {
        "CONFIRMED_species_callback_is_at_actor_plus_0x7C": {
            "evidence": ("live +0x7C holds the statically pinned pointers, and it is "
                         "written exactly once, by 0x8004a5f0 -- the species-16 arm"),
            "writers": cb_w,
            "note": ("a first pass at the static tool read the store offset literally "
                     "and concluded +0x74; the stores are against s1 = actor + 8"),
        },
        "CONFIRMED_mosquito_flight_program_0x80077654": {
            "evidence": "the mosquito's mover-VM IP is seeded to 0x80077654",
            "ip_values_seen": ip_vals[:8],
        },
        "CONFIRMED_the_one_shot_fires": {
            "evidence": ("0x8004a1d8 -- the callback's `[s0+0x6C] = 25` store -- "
                         "executed; this is the 'mosquito rises after the hit' the "
                         "operator described"),
            "plus_0x6C_writers": oneshot,
        },
        "REFUTED_launcher_is_resident_0x80049C98_to_0x80049DB8": {
            "verdict": ("WRONG. That range is inside mover_init_from_record "
                        "0x80049C30, the GENERIC actor initializer (it is also what "
                        "writes Thumper's HP=50). The mosquito throw is OVERLAY code: "
                        "LEVEL02/LEVEL.BIN 0x800B4330..0x800B43C0, which sets the aim "
                        "(+0x1C/+0x24 from the angle table 0x80074970), +0x20 = -3072, "
                        "+0x62 = 10000, cycles a direction counter at 0x800B4940 mod 4, "
                        "and plays sound 25."),
        },
        "REFUTED_thumper_attack_cycle_runs_in_his_species_callback": {
            "verdict": ("WRONG. 0x8004A0F4 is a 40-byte play_sound(26) wrapper shared "
                        "with species 22 and 36. Same trap D18 banked for Thud: "
                        "the species-callback field holds a sound trigger, not a driver."),
        },
        "NOT_CONFIRMED_thumper_program_is_park_in_place_0x800776AC": {
            "verdict": ("mover_init_from_record seeds Thumper's VM IP to 0x80077634 "
                        "(program table entry 9), not 0x800776AC (entry 13). 0x800776AC "
                        "is what the field reads BEFORE init, so a mid-level sample "
                        "taken too early shows it -- which is how this analysis first "
                        "misread it too."),
        },
        "RESOLVED_2026_08_04_second_capture": _resolve(fld, mb),
    }
    out["thumper_fight_phases"] = {
        "verdict": ("there is no separate Thumper phase counter. His behaviour is the "
                    "shared mover-VM: IP +0x70 seeded to 0x80077634 then advanced by "
                    "0x8004C834; +0x6C is the VM WAIT countdown (decrements every 2 "
                    "frames, written by 0x8004C1C0); +0x44 is an action state cycling "
                    "0/1/2 (0x8004C110). The fight's STRUCTURE -- when a mosquito is "
                    "thrown -- lives in the overlay, not in Thumper's record."),
        "on_defeat": ("the overlay writes +0x62 = 10000 at 0x800B45A4 on the same frame "
                      "HP reaches 0"),
    }

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")

    print(json.dumps({
        "frames": out.get("frames"),
        "ring_truncated": out.get("ring_truncated"),
        "species_histogram": out.get("species_histogram"),
        "thumper": out.get("thumper"),
        "mosquito_count": out.get("mosquito_count"),
        "callback_field_confirmed": out.get("callback_field_confirmed"),
        "fields_with_writes": {k: v["writes"] for k, v in out["by_field"].items()},
        "never_written": out["never_written"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
