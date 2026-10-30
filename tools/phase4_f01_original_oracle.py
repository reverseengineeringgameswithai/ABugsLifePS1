#!/usr/bin/env python3
"""F01 `original_oracle`: assert all four finalizer leaves from a NATURAL cold-boot run.

The prior evidence (`analysis/phase4_f01_finalizer_witness.json`) is a causal witness for
ONE branch: it anchors on a validated save state and **injects** `u16 2` into the scene
transition request `0x800823A0`, then shows the finalizer `0x80045A60` is skipped. Its own
recorded defects are the anchor (state, not pristine cold boot), the injected value, and
coverage of one branch across four declared leaves.

This tool supplies the complement, with nothing injected. It replays the operator's
from-boot Anthill recording on the determinism-matched Interpreter config and observes the
same four leaves while the objective completes **naturally**:

    0x8004FF14  jal 0x80039BD8        consumer proceeded past its guard      (leaf 1)
    0x8004FF28  lh  v1,0x23a0(v1)     the decision re-read                   (leaves 3,4)
    0x8004FF30  beq v1,2 -> skip      request == 2 skips the finalizer
    0x8004FF38  lw  v0,0x4c4(gp)      [0x8008225C], the other skip condition
    0x8004FF48  jal 0x80045A60        THE FINALIZER                          (leaf 2)

So the finalizer runs iff `request != 2 && [0x8008225C] == 0`. LEVEL01 exits on region
code 2, whose dispatch arm (`0x800496C4`) writes request **1** — therefore a natural
completion exercises the OPPOSITE branch from the injected witness, and the two together
bracket the condition with one arm produced by gameplay rather than by a poke.

Leaves are captured with `execTrace` **`capture_memory`** at the re-read PC, so the values
are the pre-instruction memory the branch is about to act on — no register-timing
assumption. (Capturing a register at the instruction that writes it reads the stale value;
that mistake is already banked in this campaign.)

⚠️ Requires the REPRO launcher, not the generic one:
    tools/launch_repro_playback.sh --config-dir DIR --port N --token T \
        --execution-mode Interpreter --disc "<pristine>.cue"
The generic launcher writes a settings.ini with no `[CPU]` section and silently desyncs
Interpreter-recorded movies. Playback uses `movie.resumeUntilMovieFrame` (the 60 Hz resume
path) rather than frame stepping, because this recording carries `armed_while_paused` and
the arm-phase correction lands differently under `advanceToFrame`.

RUNTIME EVIDENCE, NOT PROOF. Bounded to this one replay. This tool asserts; it does not
promote — only a fresh detached verifier may bank a dimension change.

Usage: python3 tools/phase4_f01_original_oracle.py [--port 23484] [--token T]
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

from phase4_f01_evidence import (  # noqa: E402
    external_identity,
    fixture_entries,
    observed_media_identity,
    pristine_executable_path,
    oracle_provenance_checks,
    pristine_media_checks,
    provisioned_path,
    require_checks,
    sha256_file,
)

MOVIE = ROOT / "movies/Phase4/Interpreter/Any% Runs/LEVEL01_AntHill_FromBoot.movie.json"
SCENE_WORD = 0x80082504
ANTHILL_SCENE = 1
REQUEST_WORD = 0x800823A0
OTHER_SKIP = 0x8008225C
SAMPLE = 500

LEAVES = {
    "consumer_proceeded_hits": 0x8004FF14,
    "decision_reread": 0x8004FF28,
    "finalizer_hits": 0x8004FF48,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23484)
    ap.add_argument("--token", default="f01-oracle")
    ap.add_argument("--movie", default=str(MOVIE))
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_f01_original_oracle.json"))
    args = ap.parse_args()

    entries = fixture_entries()
    movie_identity = external_identity(args.movie, set(entries))
    movie_path = provisioned_path(movie_identity)
    movie_doc = json.loads(movie_path.read_text())
    movie_sha256 = sha256_file(movie_path)
    movie_size = movie_path.stat().st_size

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(1800)

    media = c.call("emulator.getMediaInfo", {})
    media_identity = observed_media_identity(media)
    try:
        require_checks(pristine_media_checks(media_identity), "pristine media")
    except ValueError as exc:
        raise SystemExit(f"wrong media: {exc}") from exc
    mode = c.call("debugger.status", {}).get("execution_mode", {})
    if mode.get("effective") != "Interpreter":
        raise SystemExit(f"not Interpreter: {mode.get('effective')} -- use launch_repro_playback.sh")

    def rd_u32(addr: int) -> int:
        hexs = c.call("debugger.readMemory", {"address": "0x%08x" % addr, "length": 4})["hex"]
        return struct.unpack("<I", bytes.fromhex(hexs))[0]

    try:
        c.call("movie.stopPlayback", {})
    except Exception:
        pass
    loaded = c.call("movie.load", {"path": str(movie_path)})
    frames = loaded["frame_count"]
    started = c.call("movie.startPlayback", {"load_start_state": True})
    if not started.get("playing") or not started.get("reproducible"):
        raise SystemExit(f"playback not reproducible: {started}")

    # ⚠️ A PC watch is an ADDRESS watch, not a code watch. Before the game EXE is loaded,
    # these addresses hold entirely different bytes, and a from-boot replay collects those
    # pre-load executions as if they were hits on our instructions. Measured here:
    # [0x8004FF48] reads 0x00000000 at movie frames 300 and 700 and only becomes
    # `jal 0x80045A60` by frame 1200. So EVERY watch also captures the instruction word at
    # its own PC, and an event is only counted when that word matches the pristine image.
    # Everything is armed in ONE run: re-arming means re-replaying, which invites drift.
    c.call("execTrace.clear", {})
    watches = {}
    for name, pc in LEAVES.items():
        cap = [{"address": "0x%08x" % pc, "width": 4}]          # self-certify the instruction
        if name == "decision_reread":
            cap += [{"address": "0x%08x" % REQUEST_WORD, "width": 2},
                    {"address": "0x%08x" % OTHER_SKIP, "width": 4}]
        watches[name] = c.call("execTrace.addWatch", {"pc": "0x%08x" % pc,
                                                      "capture_memory": cap})["watch_id"]

    timeline, cur, phase = [], 0, {}
    while cur < frames:
        cur = min(cur + SAMPLE, frames)
        r = c.call("movie.resumeUntilMovieFrame", {"frame": cur, "max_frames": frames + 900},
                   timeout=1800)
        ex = r.get("execution", {})
        if not ex.get("completed"):
            raise SystemExit(f"early stop at {cur}: {ex.get('stop_reason')} {ex.get('stop_details')}")
        for k in ("phase_correction_consumed_at", "phase_correction_pending"):
            if ex.get(k) is not None:
                phase.setdefault(k, ex[k])
        scene = rd_u32(SCENE_WORD)
        if timeline and timeline[-1][2] == scene:
            timeline[-1][1] = cur
        else:
            timeline.append([cur, cur, scene])

    trace_response = c.call("execTrace.get", {})
    events = trace_response.get("events", [])
    summary = c.call("execTrace.summary", {})

    def captured(e) -> dict:
        out = {}
        for m in (e.get("memory") or e.get("capture_memory") or []):
            a = int(str(m.get("address")), 16)
            raw = m.get("hex") or m.get("value")
            v = int.from_bytes(bytes.fromhex(raw), "little") if isinstance(raw, str) else raw
            out[a] = v
        return out

    # the pristine instruction word each leaf PC must hold for an event to count
    img = pristine_executable_path().read_bytes()
    t_addr = struct.unpack_from("<I", img, 0x18)[0]
    def image_word(va: int) -> int:
        return struct.unpack_from("<I", img, va - t_addr + 0x800)[0]

    all_pc = {name: [e for e in events if int(str(e.get("pc")), 16) == pc]
              for name, pc in LEAVES.items()}
    per_pc, preload = {}, {}
    for name, pc in LEAVES.items():
        want = image_word(pc)
        keep, drop = [], []
        for e in all_pc[name]:
            (keep if captured(e).get(pc) == want else drop).append(e)
        per_pc[name], preload[name] = keep, drop

    decisions = []
    for e in per_pc["decision_reread"]:
        vals = captured(e)
        req = vals.get(REQUEST_WORD)
        if req is not None and req >= 0x8000:
            req -= 0x10000
        decisions.append({"frame": e.get("frame"), "request": req,
                          "gp4c4": vals.get(OTHER_SKIP)})

    entered = next((s[0] for s in timeline if s[2] == ANTHILL_SCENE), None)
    exited = timeline[-1][2] != ANTHILL_SCENE if timeline else None
    req_values = sorted({d["request"] for d in decisions if "request" in d})
    gp_values = sorted({d["gp4c4"] for d in decisions if "gp4c4" in d})

    # ⚠️ The finalizer PC must be scoped to THIS decision by cycle. A raw whole-run count
    # is not the leaf: the frontend executes 0x8004FF48 hundreds of times during boot, so
    # `finalizer_hits >= 1` would pass even if the Anthill completion had SKIPPED it --
    # an assertion that cannot fail for the right reason.
    dec_ev = per_pc["decision_reread"]
    dec_cycle = dec_ev[0].get("cycle") if dec_ev else None
    fin_ev = per_pc["finalizer_hits"]
    fin_after = [e for e in fin_ev if dec_cycle is not None and e.get("cycle") > dec_cycle]
    fin_before = [e for e in fin_ev if dec_cycle is not None and e.get("cycle") < dec_cycle]

    leaves = {
        "consumer_proceeded_hits": len(per_pc["consumer_proceeded_hits"]),
        "decision_reread_hits": len(dec_ev),
        "request_at_decision": req_values,
        "gp4c4_at_decision": gp_values,
        "finalizer_hits_attributable_to_this_decision": len(fin_after),
        "finalizer_hits_whole_run": len(fin_ev),
        "finalizer_hits_before_decision_unrelated": len(fin_before),
        "unrelated_hit_frame_span": ([fin_before[0].get("frame"), fin_before[-1].get("frame")]
                                     if fin_before else None),
        "decision_to_finalizer_cycles": (fin_after[0].get("cycle") - dec_cycle
                                         if fin_after and dec_cycle is not None else None),
    }

    assertions = [
        {"id": "objective_completed_naturally", "op": "eq", "expected": True,
         "actual": bool(entered is not None and exited),
         "detail": "Anthill scene entered then exited with no injection"},
        {"id": "consumer_proceeded", "op": "eq", "expected": 1,
         "actual": leaves["consumer_proceeded_hits"]},
        {"id": "request_produced_by_gameplay_not_injected", "op": "eq", "expected": [1],
         "actual": req_values,
         "detail": "region code 2 -> dispatch arm 0x800496C4 writes request 1"},
        {"id": "other_skip_condition_ruled_out", "op": "eq", "expected": [0],
         "actual": gp_values},
        {"id": "finalizer_ran_for_this_decision", "op": "eq", "expected": 1,
         "actual": leaves["finalizer_hits_attributable_to_this_decision"],
         "detail": "scoped by cycle to the decision; complement of the injected "
                   "request==2 arm, where the finalizer was skipped"},
        {"id": "finalizer_immediately_follows_the_decision", "op": "le", "expected": 200,
         "actual": leaves["decision_to_finalizer_cycles"],
         "detail": "same basic block: 0x8004FF28 -> 0x8004FF48 is 7 instructions"},
    ]
    for a in assertions:
        v, e = a["actual"], a["expected"]
        if a["op"] == "ge":
            a["passed"] = v is not None and v >= e
        elif a["op"] == "le":
            a["passed"] = v is not None and v <= e
        else:
            a["passed"] = v == e

    provenance_assertions = oracle_provenance_checks(
        movie_identity=movie_identity,
        movie_doc=movie_doc,
        movie_sha256=movie_sha256,
        movie_size=movie_size,
        central_pin=entries.get(movie_identity),
        media_identity=media_identity,
        trace_truncated=trace_response.get("truncated"),
        playback_reproducible=started.get("reproducible"),
        playback_completed=True,
    )

    doc = {
        "_comment": "F01 original_oracle: all four finalizer leaves observed during a NATURAL "
                    "cold-boot completion, nothing injected. Complements the injected "
                    "request==2 witness. RUNTIME EVIDENCE, NOT PROOF -- bounded to this "
                    "replay. Regenerate: tools/phase4_f01_original_oracle.py",
        "schema": "abl-phase4-f01-original-oracle/1",
        "authority": {
            "runtime_silence_proves_absence": False,
            "promotes_row_or_dimension": False,
            "requires_fresh_verifier": True,
            "bounded_to": "one replay of one from-boot movie",
        },
        "fixture": {
            "movie": movie_identity,
            "movie_sha256": movie_sha256,
            "movie_size": movie_size,
            "frames": frames,
            "from_boot": (movie_doc.get("start_state") or {}).get("from_boot"),
            "movie_version": started.get("movie_version"),
            "armed_while_paused": started.get("armed_while_paused"),
            "phase_delay_owed": started.get("phase_delay_owed"),
            "phase_correction": phase,
            "reproducible": started.get("reproducible"),
            "playback_completed": True,
        },
        "media": media_identity,
        "execution_mode": mode.get("effective"),
        "method": {
            "launcher": "tools/launch_repro_playback.sh --execution-mode Interpreter",
            "playback": "movie.resumeUntilMovieFrame (60 Hz resume path, not frame stepping)",
            "capture": "execTrace capture_memory at the decision re-read (pre-instruction)",
            "injection": "NONE -- no write, no perturbation, no poke",
        },
        "branch_under_test": {
            "finalizer": "0x80045A60",
            "runs_iff": "request != 2 && [0x8008225C] == 0",
            "decision_pc": "0x8004FF28",
            "skip_edges": ["0x8004FF30 beq request,2", "0x8004FF40 bnez [0x8008225C]"],
        },
        "scene_timeline": [{"first": a, "last": b, "scene": s} for a, b, s in timeline],
        "entered_anthill_frame": entered,
        "exited_anthill_by_movie_end": exited,
        "leaves": leaves,
        "decisions": decisions,
        "preload_noise_rejected": {
            "counts": {k: len(v) for k, v in preload.items()},
            "why": "A PC watch is an ADDRESS watch, not a code watch. Before the game EXE "
                   "is loaded these addresses hold different bytes, so a from-boot replay "
                   "records executions that are not our instructions at all. Measured: "
                   "[0x8004FF48] = 0x00000000 at movie frames 300 and 700, becoming "
                   "`jal 0x80045A60` by frame 1200. Every event above is kept only when the "
                   "instruction word captured at its own PC equals the pristine image word.",
            "how_it_was_caught": "A raw whole-run finalizer count of 327 against a decision "
                                 "count of 1 is impossible on straight-line code. A compiled-C "
                                 "scan (tools/phase4_f01_finalizer_entry_probe.c) then found "
                                 "ZERO direct branch/jump entries into the block across 22 "
                                 "images and the decoded jr tables, which ruled out the "
                                 "indirect-entry explanation and left code-not-loaded.",
        },
        "assertions": assertions,
        "provenance_assertions": provenance_assertions,
        "all_passed": (all(a["passed"] for a in assertions)
                       and all(a["passed"] for a in provenance_assertions)),
        "exec_trace": {
            "total": trace_response.get("total", summary.get("total")),
            "truncated": trace_response.get("truncated"),
            "completeness_source": "event-bearing execTrace.get response",
        },
        "status_statement": "F01 original_oracle evidence only; the dimension is not promoted here.",
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[oracle] timeline={[(s[2]) for s in timeline]}")
    print(f"[oracle] leaves={leaves}")
    for a in assertions:
        print(f"  {'PASS' if a['passed'] else 'FAIL'}  {a['id']}: {a['actual']} vs {a['expected']}")
    print(f"wrote {args.out}")
    return 0 if doc["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
