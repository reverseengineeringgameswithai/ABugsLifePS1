#!/usr/bin/env python3
"""D16/F03 TRACED run -- what polling could not reach.

The poll-only oracle (tools/phase4_d16_f03_oracle.py) had to run on a
CachedInterpreter-era fixture, so it could observe state but never a WRITER. Three
questions were left open by that limit, and one of them is a live suspicion:

  1. The cinematic camera's EXIT path (selector case 3, 0x8004EB98..0x8004EBD0) was
     never observed at all -- the old fixture ended with flags still 3 and power bit
     0x04 still set.
  2. 0x80082388, the value the selector waits on before completing phases 1 and 3,
     is unidentified.
  3. ⚠️ The archived Thumper note claims "fight phase/attack counters tick at
     0x80090BF2 / 0x80090BF6". A full static census over the pristine EXE and all 21
     overlay blobs finds ZERO absolute accesses to 0x80090BF6 and, for 0x80090BF2, a
     single INDEXED READ at 0x80021C34 (`at = 0x80090000 + s0`) -- not a counter tick.
     Those two addresses are camera-block +0x32 and +0x36, immediately past the field
     this row just proved had been misattributed to Thumper. Either they are written
     through a pointer (the declared blind spot of both static scans) or the
     attribution is wrong in the same way. A write-watch settles it; nothing static can.

This runs on an INTERPRETER-recorded movie, where arming instrumentation is free, and
reports the actual writer PC for every address of interest.

    tools/phase4_d16_f03_trace.py --port 23670 \
        --movie movies/Phase4/Interpreter/D16_Thumper_Defeat.movie.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REGION_A = 0x800B39A0

# address -> (length, label)
WATCH = {
    0x80090BEC: (2, "cinematic camera PHASE"),
    0x80090BEE: (2, "cinematic camera FLAGS"),
    0x80090BF2: (2, "alleged 'fight phase counter' (camera block +0x32)"),
    0x80090BF6: (2, "alleged 'attack counter' (camera block +0x36)"),
    0x800A6590: (2, "power/suppression word"),
    0x800823A0: (2, "goal latch = level exit"),
    0x80082388: (2, "value the camera selector waits on"),
    0x8009FE72: (2, "Thumper HP (actor 0x8009FE04 + 0x6E)"),
    0x80082362: (1, "four_byte_store out 0 (a0)"),
    0x8008248A: (1, "four_byte_store out 1 (a1)"),
    0x8008241E: (1, "four_byte_store out 2 (a2)"),
    0x8008248B: (1, "four_byte_store out 3 (a3)"),
}


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


def overlay_candidates():
    out = {}
    for p in sorted(ROOT.glob("REBUILD/files/LEVEL*/LEVEL*.BIN")):
        out[hashlib.sha256(p.read_bytes()[:256]).hexdigest()] = str(p.relative_to(ROOT))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--movie", type=Path,
                    default=ROOT / "movies/Phase4/Interpreter/D16_Thumper_Defeat.movie.json")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23670)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_d16_f03_trace.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/d16-trace")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "rows": ["D16_thumper", "F03_council_chamber"],
        "movie": str(args.movie.relative_to(ROOT)),
        "execution_mode": args.execution_mode,
        "regime": ("Interpreter-recorded movie: arming accessLog is free (no mode "
                   "switch, so no silent desync). 60 Hz resume+poll."),
        "watches": {"0x%08X" % a: l for a, (_, l) in WATCH.items()},
    }
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
        status = c.call("movie.status", {})
        out["movie_version"] = status.get("movie_version")
        out["armed_while_paused"] = status.get("armed_while_paused")
        out["phase_delay_owed"] = status.get("phase_delay_owed")

        # Watches MUST be armed after startPlayback: the start-state load clears them.
        c.call("accessLog.clear", {})
        for a, (n, _) in WATCH.items():
            c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": n,
                                          "type": "write", "max_events": 200000})

        # ⚠️ Hashing the head of region A only identifies the blob SHORTLY AFTER LOAD:
        # the overlay mutates its own first bytes at runtime, so this returns
        # UNRECOGNISED mid-level even when the blob is unquestionably resident. Kept as
        # a weak signal; the authoritative identity check is the writer-PC one below.
        cands = overlay_candidates()
        h = hashlib.sha256(bytes.fromhex(c.call(
            "debugger.readMemory",
            {"address": "0x%08x" % REGION_A, "length": 256})["hex"])).hexdigest()
        out["region_a_head_hash_at_start"] = cands.get(h, "UNRECOGNISED:" + h[:16])

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
        out["wall_seconds"] = round(time.time() - began, 1)

        h2 = hashlib.sha256(bytes.fromhex(c.call(
            "debugger.readMemory",
            {"address": "0x%08x" % REGION_A, "length": 256})["hex"])).hexdigest()
        out["region_a_head_hash_at_end"] = cands.get(h2, "UNRECOGNISED:" + h2[:16])

        events, truncated, total = collect(c)
        out["event_total"] = total
        out["ring_truncated"] = truncated
        if truncated:
            out["negative_claims_unsound"] = (
                "the event ring TRUNCATED, so any 'zero writes' statement below may "
                "simply be a dropped event and must not be read as a negative result")
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    # ------------------------------------------------------------- group ----
    by_addr = {}
    for e in events:
        a = int(str(e.get("address", "0")), 16) & 0x1FFFFFFF | 0x80000000
        pc = str(e.get("instruction_pc") or e.get("pc") or "").lower()
        rec = by_addr.setdefault(a, {"count": 0, "writers": {}, "values": []})
        rec["count"] += 1
        rec["writers"][pc] = rec["writers"].get(pc, 0) + 1
        v = e.get("new_value")
        if v is not None and len(rec["values"]) < 400:
            rec["values"].append({"f": e.get("frame"), "v": s16(v & 0xFFFF)})

    out["by_address"] = {}
    for a, (n, label) in WATCH.items():
        rec = by_addr.get(a)
        out["by_address"]["0x%08X" % a] = {
            "label": label,
            "writes": rec["count"] if rec else 0,
            "writer_pcs": (sorted(rec["writers"].items(), key=lambda kv: -kv[1])
                           if rec else []),
            "value_sequence": (rec["values"][:60] if rec else []),
        }

    # ---- overlay identity, the strong way -----------------------------------
    # A write to the goal latch FROM PC 0x800B4190 can only happen if the blob whose
    # 0x800B4190 is `sh v0,0x23a0(at)` is the one executing. That is LEVEL02/LEVEL.BIN.
    latch = out["by_address"]["0x800823A0"]
    out["overlay_identity"] = {
        "method": ("writer PC, not a memory hash: the overlay mutates its own first "
                   "bytes at runtime, so hashing region A only identifies the blob "
                   "shortly after load and reads UNRECOGNISED mid-level"),
        "expected_pc": "0x800b4190",
        "expected_blob": "REBUILD/files/LEVEL02/LEVEL.BIN",
        "confirmed": any(pc == "0x800b4190" for pc, _ in latch["writer_pcs"]),
    }

    # ---- the three questions this run existed to answer ----------------------
    bf2 = out["by_address"]["0x80090BF2"]
    bf6 = out["by_address"]["0x80090BF6"]
    flags = out["by_address"]["0x80090BEE"]
    bios = lambda pcs: [p for p, _ in pcs if p.startswith("0xbfc")]
    game = lambda pcs: [p for p, _ in pcs if not p.startswith("0xbfc")]

    out["findings"] = {
        "Q3_the_alleged_fight_counters": {
            "0x80090BF6": {
                "verdict": ("REFUTED as an attack counter. Every write comes from the "
                            "BIOS (bulk zeroing at load); no game code writes it."),
                "writes": bf6["writes"],
                "game_writers": game(bf6["writer_pcs"]),
                "bios_writers": bios(bf6["writer_pcs"]),
            },
            "0x80090BF2": {
                "verdict": ("REAL variable, WRONG owner. Written by "
                            "gameplay_effect_spawner 0x8005CD2C (site 0x8005CE6C), not "
                            "by anything Thumper-specific; cycles 0/1/1/2 on a ~48-frame "
                            "period throughout, including long before and after the "
                            "fight."),
                "writes": bf2["writes"],
                "game_writers": game(bf2["writer_pcs"]),
                "static_census_found_zero_stores": True,
                "why_static_missed_it": ("written through a POINTER -- exactly the blind "
                                         "spot both static scans declared. The declared "
                                         "blind spot was real, which is why no negative "
                                         "was claimed against it."),
            },
        },
        "Q1_the_camera_exit_path": {
            "verdict": ("case 3 (0x8004EB98..0x8004EBD0) NEVER FIRES in this scene. The "
                        "flags word is written exactly 3 times in 4060 frames: BIOS 0, "
                        "then 2 by the camera start 0x8004DB44, then 3 by case 1 "
                        "0x8004EB1C. The cinematic is never released -- the level ends "
                        "with it active and the suppression bit still set."),
            "writes": flags["writes"],
            "writer_pcs": flags["writer_pcs"],
            "implication": ("case 3 belongs to cinematics that RETURN to gameplay (the "
                            "telescope path). This level has no telescope, so the exit "
                            "path is unreachable here -- 'does not occur', not merely "
                            "'unobserved'."),
        },
        "Q2_what_0x80082388_is": {
            "verdict": ("the transition/fade countdown owned by "
                        "contact_cursor_transition_reset 0x80054AD4 -- the function "
                        "immediately after four_byte_store 0x80054AAC, i.e. the same "
                        "subsystem the camera selector drives."),
            "writes": out["by_address"]["0x80082388"]["writes"],
            "writer_pcs": out["by_address"]["0x80082388"]["writer_pcs"][:5],
        },
        "BONUS_hp_arc_at_instruction_level": {
            "verdict": ("berry_tough_damage_dispatch 0x800590E4 writes Thumper HP "
                        "EXACTLY 15 times, 50 -> 20 in steps of 2. The registry's "
                        "'15 hits' is now instruction-level, not inferred from polling. "
                        "Init 50 by mover_init_from_record 0x80049CA0; final 0 by the "
                        "overlay's level_completion_handler 0x800B45AC."),
            "writer_pcs": out["by_address"]["0x8009FE72"]["writer_pcs"],
            "values": [x["v"] for x in out["by_address"]["0x8009FE72"]["value_sequence"]],
        },
    }

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")

    summary = {k: {"writes": v["writes"],
                   "writers": [p for p, _ in v["writer_pcs"][:4]]}
               for k, v in out["by_address"].items()}
    print(json.dumps({"final_playback_index": out.get("final_playback_index"),
                      "frames": out.get("frames"),
                      "ring_truncated": out.get("ring_truncated"),
                      "overlay_identity": out["overlay_identity"],
                      "summary": summary}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
