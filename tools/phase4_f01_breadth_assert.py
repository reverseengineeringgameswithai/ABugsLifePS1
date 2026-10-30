#!/usr/bin/env python3
"""F01 `campaign_breadth`: assert the finalizer BRANCH LAW on every level, not just LEVEL01.

The existing breadth sweep (`analysis/phase4_f01_campaign_breadth.json`) OBSERVES the
lifecycle cells across 19 movies with memory write-watches. It carries no assertions and
self-declares `promotes_campaign_breadth: false`. The dimension's method is to run F01's
assertions across the corpus, so this tool asserts the law the LEVEL01 oracle established:

    0x8004FF28  lh v1,0x23a0(v1)      the decision re-read
    0x8004FF30  beq v1,2 -> skip      request == 2 SKIPS the finalizer
    0x8004FF38  lw v0,0x4c4(gp)       [0x8008225C], the other skip condition
    0x8004FF40  bnez v0  -> skip      nonzero SKIPS the finalizer
    0x8004FF48  jal 0x80045A60        THE FINALIZER

> finalizer runs **iff** `request != 2 && [0x8008225C] == 0`

Every decision is checked both ways: a decision that should call must be followed by a
finalizer event inside CYCLE_WINDOW, and a decision that should skip must not be. This
can genuinely fail, which is the point — an assertion that cannot fail is not a check
(see the 2026-08-10 original_oracle write-up).

⚠️ Every watch also captures the instruction word **at its own PC**, and an event counts
only when it equals the pristine image word. On a from-boot movie the EXE is absent for
~1,000 frames and a PC watch logs whatever else occupied the address; these corpus movies
are state-anchored so they are immune, but the guard is kept because it is cheap and the
next corpus may not be.

Parallel by design: one isolated DuckStation per worker, each with its own config dir,
port and token; movies are claimed with atomic `mkdir`, longest-first so the critical
path (LEVEL15, ~76k frames) starts immediately. Results are written per movie so partial
progress survives, then merged by `--consolidate`.

  worker      : phase4_f01_breadth_assert.py --port N --token T --workdir DIR
  consolidate : phase4_f01_breadth_assert.py --consolidate --workdir DIR [--out JSON]
"""
from __future__ import annotations

import argparse
from functools import lru_cache
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
    pristine_media_checks,
    provisioned_path,
    require_checks,
    sha256_file,
)

CONSUMER, DECISION, FINALIZER = 0x8004FF14, 0x8004FF28, 0x8004FF48
REQUEST_WORD, OTHER_SKIP = 0x800823A0, 0x8008225C
SCENE_WORD = 0x80082504
CYCLE_WINDOW = 2000          # decision -> finalizer is 28 cycles; 2000 is generous
CHUNK = 5000
DECISION_IMAGE_WORD = "0x846323A0"

DECLARED_LEVELS = frozenset({
    "F16_Bonus01", "F17_Bonus02", "F18_Bonus03", "LEVEL00_Training",
    "LEVEL01_Anthill", "LEVEL02_Tunnels", "LEVEL03_CouncilChamber",
    "LEVEL04_Cliffside", "LEVEL05_RiverbedCanyon", "LEVEL06",
    "LEVEL07_CITYENTRANCE", "LEVEL08_CITYSQUARE", "LEVEL09_BUGBAR",
    "LEVEL10_CLOVERFOREST", "LEVEL11_THETREE", "LEVEL12_BATTLEARENA",
    "LEVEL13_ANTHILLPT2", "LEVEL14_RIVERBEDFLIGHT", "LEVEL15",
})


def movie_list() -> list[tuple[str, Path]]:
    src = json.loads((ROOT / "analysis/phase4_f01_campaign_breadth.json").read_text())
    entries = fixture_entries()
    out = []
    for s in src["sessions"]:
        identity = external_identity(s["movie"], set(entries))
        p = provisioned_path(identity)
        out.append((s["level"], p))
    levels = [level for level, _ in out]
    if (len(levels) != len(DECLARED_LEVELS) or len(set(levels)) != len(levels)
            or set(levels) != DECLARED_LEVELS):
        raise ValueError(
            "source corpus differs from the exact declared 19-level universe: "
            f"missing={sorted(DECLARED_LEVELS - set(levels))} "
            f"extra={sorted(set(levels) - DECLARED_LEVELS)} count={len(levels)}"
        )
    # longest first: the wall clock is the longest single movie, so start it immediately
    out.sort(key=lambda lp: -lp[1].stat().st_size)
    return out


def replay_one(c, level: str, path: Path, image_word, runtime: dict) -> dict:
    entries = fixture_entries()
    identity = external_identity(path, set(entries))
    path = provisioned_path(identity)
    movie_doc = json.loads(path.read_text())
    movie_hash = sha256_file(path)
    pin = entries.get(identity) or {}
    fixture_errors = []
    if pin.get("sha256") != movie_hash:
        fixture_errors.append("movie hash does not match central pin")
    if pin.get("size") != path.stat().st_size:
        fixture_errors.append("movie size does not match central pin")
    start = movie_doc.get("start_state") or {}
    if start.get("from_boot") is not False:
        fixture_errors.append("breadth movie is not state anchored")
    try:
        state_identity = external_identity(start.get("path", ""), set(entries))
        state_path = provisioned_path(state_identity)
        state_pin = entries.get(state_identity) or {}
        if sha256_file(state_path) != start.get("sha256"):
            fixture_errors.append("state bytes do not match movie metadata")
        if state_pin.get("sha256") != start.get("sha256"):
            fixture_errors.append("state metadata does not match central pin")
        if state_pin.get("size") != state_path.stat().st_size:
            fixture_errors.append("state size does not match central pin")
    except (OSError, ValueError) as exc:
        state_identity = None
        fixture_errors.append(f"invalid state identity: {exc}")
    if fixture_errors:
        return {"level": level, "movie": identity,
                "error": "; ".join(fixture_errors)}

    try:
        c.call("movie.stopPlayback", {})
    except Exception:
        pass
    c.call("execTrace.clear", {})
    loaded = c.call("movie.load", {"path": str(path)})
    frames = loaded["frame_count"]
    started = c.call("movie.startPlayback", {"load_start_state": True})
    if not started.get("playing") or not started.get("reproducible"):
        return {"level": level, "error": f"playback not reproducible: {started}"}

    for pc in (CONSUMER, DECISION, FINALIZER):
        cap = [{"address": "0x%08x" % pc, "width": 4}]
        if pc == DECISION:
            cap += [{"address": "0x%08x" % REQUEST_WORD, "width": 2},
                    {"address": "0x%08x" % OTHER_SKIP, "width": 4}]
        c.call("execTrace.addWatch", {"pc": "0x%08x" % pc, "capture_memory": cap})

    cur = 0
    while cur < frames:
        cur = min(cur + CHUNK, frames)
        r = c.call("movie.resumeUntilMovieFrame", {"frame": cur, "max_frames": frames + 900},
                   timeout=3600)
        ex = r.get("execution", {})
        if not ex.get("completed"):
            return {"level": level, "error": f"early stop @{cur}: {ex.get('stop_reason')}",
                    "stop_details": ex.get("stop_details")}

    tr = c.call("execTrace.get", {"offset": 0, "limit": 10000})
    events, truncated = tr.get("events", []), tr.get("truncated")

    def cap_of(e) -> dict:
        out = {}
        for m in (e.get("memory") or []):
            a = int(str(m.get("address")), 16)
            raw = m.get("hex") or m.get("value")
            out[a] = int.from_bytes(bytes.fromhex(raw), "little") if isinstance(raw, str) else raw
        return out

    kept, rejected = {}, {}
    for pc in (CONSUMER, DECISION, FINALIZER):
        want = image_word(pc)
        same = [e for e in events if int(str(e.get("pc")), 16) == pc]
        kept[pc] = [e for e in same if cap_of(e).get(pc) == want]
        rejected[pc] = len(same) - len(kept[pc])

    fin_cycles = sorted(e["cycle"] for e in kept[FINALIZER])
    decisions, failures = [], []
    for e in kept[DECISION]:
        v = cap_of(e)
        req = v.get(REQUEST_WORD)
        if req is not None and req >= 0x8000:
            req -= 0x10000
        gp = v.get(OTHER_SKIP)
        should_call = (req != 2 and gp == 0)
        cyc = e["cycle"]
        followed = [fc for fc in fin_cycles if 0 < fc - cyc <= CYCLE_WINDOW]
        row = {"frame": e.get("frame"), "cycle": cyc, "request": req, "gp4c4": gp,
               "law_predicts_finalizer": should_call,
               "finalizer_observed": bool(followed),
               "delta_cycles": (followed[0] - cyc) if followed else None,
               "self_certification": {
                   "pc": "0x%08X" % DECISION,
                   "instruction_word": "0x%08X" % v.get(DECISION)
                       if isinstance(v.get(DECISION), int) else None,
                   "pristine_instruction_word": "0x%08X" % image_word(DECISION),
               }}
        row["self_certification"]["passed"] = (
            row["self_certification"]["instruction_word"] == DECISION_IMAGE_WORD
            and row["self_certification"]["pristine_instruction_word"]
            == DECISION_IMAGE_WORD
        )
        row["law_holds"] = (row["law_predicts_finalizer"] == row["finalizer_observed"])
        if not row["law_holds"]:
            failures.append(row)
        decisions.append(row)

    unattributed = [fc for fc in fin_cycles
                    if not any(0 < fc - d["cycle"] <= CYCLE_WINDOW for d in decisions)]
    return {
        "level": level,
        "movie": identity,
        "movie_sha256": movie_hash,
        "movie_size": path.stat().st_size,
        "start_state": {"identity": state_identity, "sha256": start.get("sha256")},
        "frames": frames,
        "reproducible": started.get("reproducible"),
        "playback_completed": True,
        "movie_version": started.get("movie_version"),
        "from_boot": start.get("from_boot"),
        "runtime": runtime,
        "scene_at_end": None,
        "counts": {"consumer": len(kept[CONSUMER]), "decisions": len(kept[DECISION]),
                   "finalizer": len(kept[FINALIZER])},
        "preload_rejected": {"consumer": rejected[CONSUMER], "decision": rejected[DECISION],
                             "finalizer": rejected[FINALIZER]},
        "decisions": decisions,
        "law_failures": failures,
        "finalizer_calls_not_attributable_to_a_decision": len(unattributed),
        "exec_trace": {
            "total": tr.get("total"),
            "returned": len(events),
            "truncated": truncated,
            "completeness_source": "event-bearing execTrace.get response",
        },
        "exec_trace_truncated": truncated,
        "law_holds_for_every_decision": bool(decisions) and not failures,
    }


def worker(args) -> int:
    from duckstation_debug_client import DebuggerClient
    wd = Path(args.workdir); (wd / "claims").mkdir(parents=True, exist_ok=True)
    (wd / "results").mkdir(parents=True, exist_ok=True)

    img = pristine_executable_path().read_bytes()
    t_addr = struct.unpack_from("<I", img, 0x18)[0]
    def image_word(va: int) -> int:
        return struct.unpack_from("<I", img, va - t_addr + 0x800)[0]

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(3600)
    media = c.call("emulator.getMediaInfo", {})
    media_identity = observed_media_identity(media)
    try:
        require_checks(pristine_media_checks(media_identity), "pristine media")
    except ValueError as exc:
        raise SystemExit(f"wrong media on port {args.port}: {exc}") from exc
    mode = c.call("debugger.status", {}).get("execution_mode", {})
    if mode.get("effective") != "Interpreter":
        raise SystemExit(f"port {args.port} is {mode.get('effective')}, need Interpreter")
    runtime = {"execution_mode": mode.get("effective"), "media": media_identity}

    done = 0
    for level, path in movie_list():
        claim = wd / "claims" / level
        try:
            claim.mkdir()                      # atomic claim
        except FileExistsError:
            continue
        try:
            res = replay_one(c, level, path, image_word, runtime)
        except Exception as exc:               # a dead movie must not kill the worker
            res = {"level": level, "error": f"{type(exc).__name__}: {exc}"}
        (wd / "results" / f"{level}.json").write_text(json.dumps(res, indent=1) + "\n")
        ok = "ok" if res.get("law_holds_for_every_decision") else res.get("error", "LAW FAILURE")
        print(f"[:{args.port}] {level}: {ok} "
              f"decisions={res.get('counts',{}).get('decisions')} "
              f"finalizer={res.get('counts',{}).get('finalizer')}", flush=True)
        done += 1
    print(f"[:{args.port}] worker done, {done} movie(s)", flush=True)
    return 0


def _derived_decision_failure(level: str, decision: dict) -> str | None:
    cert = decision.get("self_certification") or {}
    if not (
        cert.get("pc") == "0x8004FF28"
        and cert.get("instruction_word") == DECISION_IMAGE_WORD
        and cert.get("pristine_instruction_word") == DECISION_IMAGE_WORD
        and cert.get("passed") is True
    ):
        return f"{level}: decision lacks a pristine instruction-word certificate"

    frame, cycle = decision.get("frame"), decision.get("cycle")
    request, gp4c4 = decision.get("request"), decision.get("gp4c4")
    if (not isinstance(frame, int) or isinstance(frame, bool) or frame < 0
            or not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0):
        return f"{level}: decision lacks integer frame/cycle trace coordinates"
    if (not isinstance(request, int) or isinstance(request, bool)
            or not -0x8000 <= request <= 0x7FFF):
        return f"{level}: decision lacks a captured signed-u16 request"
    if (not isinstance(gp4c4, int) or isinstance(gp4c4, bool)
            or not 0 <= gp4c4 <= 0xFFFFFFFF):
        return f"{level}: decision lacks a captured u32 gp4c4 operand"

    predicted = request != 2 and gp4c4 == 0
    observed = decision.get("finalizer_observed")
    if not isinstance(observed, bool):
        return f"{level}: finalizer_observed is not boolean"
    if decision.get("law_predicts_finalizer") is not predicted:
        return f"{level}: stored prediction disagrees with request/gp inputs"
    if decision.get("law_holds") is not True or predicted != observed:
        return f"{level}: decision row violates the branch law"
    delta = decision.get("delta_cycles")
    if observed and (type(delta) is not int or not 0 < delta <= CYCLE_WINDOW):
        return f"{level}: observed finalizer has invalid cycle attribution"
    if not observed and delta is not None:
        return f"{level}: skipped finalizer carries a cycle attribution"
    return None


@lru_cache(maxsize=1)
def declared_fixture_envelopes() -> dict[str, dict]:
    """Resolve and independently verify the exact campaign fixture envelope once."""
    source = json.loads((ROOT / "analysis/phase4_f01_campaign_breadth.json").read_text())
    entries = fixture_entries()
    envelopes = {}
    for session in source.get("sessions") or []:
        level = session.get("level")
        movie_identity = external_identity(session.get("movie", ""), set(entries))
        movie_path = provisioned_path(movie_identity)
        movie_doc = json.loads(movie_path.read_text())
        movie_pin = entries.get(movie_identity) or {}
        start = movie_doc.get("start_state") or {}
        state_identity = external_identity(start.get("path", ""), set(entries))
        state_path = provisioned_path(state_identity)
        state_pin = entries.get(state_identity) or {}
        actual_movie_hash = sha256_file(movie_path)
        actual_state_hash = sha256_file(state_path)
        source_errors = []
        if movie_pin.get("sha256") != actual_movie_hash:
            source_errors.append("provisioned movie hash differs from central pin")
        if movie_pin.get("size") != movie_path.stat().st_size:
            source_errors.append("provisioned movie size differs from central pin")
        if movie_pin.get("media_class") != "pristine_serial":
            source_errors.append("movie central pin is not pristine_serial")
        if movie_pin.get("preservation_required") is not True:
            source_errors.append("movie central pin is not preservation-required")
        if state_pin.get("sha256") != actual_state_hash:
            source_errors.append("provisioned state hash differs from central pin")
        if state_pin.get("size") != state_path.stat().st_size:
            source_errors.append("provisioned state size differs from central pin")
        if state_pin.get("preservation_required") is not True:
            source_errors.append("state central pin is not preservation-required")
        if not (
            start.get("from_boot") is False
            and start.get("loaded_before_recording") is True
            and start.get("reproducible_only_from_state") is True
            and start.get("game_serial") == "SCUS-94288"
            and movie_doc.get("game_serial") == "SCUS-94288"
            and start.get("sha256") == actual_state_hash
            and start.get("file_size") == state_path.stat().st_size
        ):
            source_errors.append("movie start-state metadata is incoherent")
        envelopes[level] = {
            "movie": movie_identity,
            "movie_sha256": actual_movie_hash,
            "movie_size": movie_path.stat().st_size,
            "state": state_identity,
            "state_sha256": actual_state_hash,
            "frames": session.get("frames"),
            "source_errors": source_errors,
        }
    if (len(envelopes) != len(DECLARED_LEVELS)
            or set(envelopes) != DECLARED_LEVELS):
        raise ValueError("fixture envelopes do not equal the declared 19-level corpus")
    return envelopes


def _fixture_runtime_failure(row: dict) -> str | None:
    level = row.get("level")
    expected = declared_fixture_envelopes().get(level)
    if expected is None:
        return f"{level}: no declared fixture envelope"
    if expected["source_errors"]:
        return f"{level}: " + "; ".join(expected["source_errors"])
    start = row.get("start_state") or {}
    if not (
        row.get("movie") == expected["movie"]
        and row.get("movie_sha256") == expected["movie_sha256"]
        and row.get("movie_size") == expected["movie_size"]
        and row.get("frames") == expected["frames"]
        and row.get("from_boot") is False
        and start.get("identity") == expected["state"]
        and start.get("sha256") == expected["state_sha256"]
    ):
        return f"{level}: fixture identity/hash/size/anchor envelope mismatch"
    runtime = row.get("runtime") or {}
    if runtime.get("execution_mode") != "Interpreter":
        return f"{level}: runtime is not Interpreter"
    failed_media = [
        check["id"] for check in pristine_media_checks(runtime.get("media") or {})
        if not check["passed"]
    ]
    if failed_media:
        return f"{level}: pristine media checks failed: {', '.join(failed_media)}"
    trace = row.get("exec_trace") or {}
    counts = row.get("counts") or {}
    rejected = row.get("preload_rejected") or {}
    exact_count_keys = {"consumer", "decisions", "finalizer"}
    exact_rejected_keys = {"consumer", "decision", "finalizer"}
    if not (
        type(trace.get("total")) is int
        and type(trace.get("returned")) is int
        and trace["total"] >= 0
        and trace["total"] == trace["returned"]
        and trace.get("truncated") is False
        and row.get("exec_trace_truncated") is False
        and set(counts) == exact_count_keys
        and set(rejected) == exact_rejected_keys
        and all(type(value) is int and value >= 0 for value in counts.values())
        and all(type(value) is int and value >= 0 for value in rejected.values())
        and counts.get("decisions") == len(row.get("decisions") or [])
        and trace["total"] == sum(counts.values()) + sum(rejected.values())
    ):
        return f"{level}: event-bearing trace page is incomplete or truncated"
    return None


def corpus_gate(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Evaluate the exact corpus from row contents; never trust summary booleans."""
    levels = [row.get("level") for row in rows]
    observed = {level for level in levels if isinstance(level, str)}
    duplicates = sorted({level for level in observed if levels.count(level) > 1})
    exact_universe = (
        len(rows) == len(DECLARED_LEVELS)
        and len(observed) == len(DECLARED_LEVELS)
        and observed == DECLARED_LEVELS
        and not duplicates
    )
    errors = [f"{row.get('level')}: {row.get('error')}"
              for row in rows if row.get("error")]
    incomplete = [row.get("level") for row in rows
                  if row.get("reproducible") is not True
                  or row.get("playback_completed") is not True]
    truncated = [row.get("level") for row in rows
                 if row.get("exec_trace_truncated") is not False
                 or (row.get("exec_trace") or {}).get("truncated") is not False]
    fixture_failures = [
        failure for row in rows
        if (failure := _fixture_runtime_failure(row)) is not None
    ]

    decision_failures: list[str] = []
    for row in rows:
        level = str(row.get("level"))
        decisions = row.get("decisions")
        if not isinstance(decisions, list) or not decisions:
            decision_failures.append(f"{level}: zero decisions")
            continue
        if (row.get("counts") or {}).get("decisions") != len(decisions):
            decision_failures.append(f"{level}: decision count mismatch")
        for decision in decisions:
            failure = _derived_decision_failure(level, decision)
            if failure:
                decision_failures.append(failure)

    retained_failures = [
        f"{row.get('level')}: retained law_failures is nonempty"
        for row in rows if row.get("law_failures") != []
    ]
    row_summary_failures = [
        f"{row.get('level')}: law_holds_for_every_decision is not true"
        for row in rows if row.get("law_holds_for_every_decision") is not True
    ]
    law_failures = decision_failures + retained_failures + row_summary_failures

    gates = [
        {
            "id": "exact_declared_19_level_universe",
            "passed": exact_universe,
            "expected": sorted(DECLARED_LEVELS),
            "actual": sorted(observed),
            "detail": {"row_count": len(rows), "duplicates": duplicates,
                       "missing": sorted(DECLARED_LEVELS - observed),
                       "extra": sorted(observed - DECLARED_LEVELS)},
        },
        {"id": "zero_errors", "passed": not errors, "expected": [], "actual": errors},
        {"id": "all_playbacks_reproducible_and_completed", "passed": not incomplete,
         "expected": [], "actual": incomplete},
        {"id": "all_exec_traces_nontruncated", "passed": not truncated,
         "expected": [], "actual": truncated},
        {"id": "all_fixture_and_runtime_provenance_exact",
         "passed": exact_universe and not fixture_failures,
         "expected": [], "actual": fixture_failures},
        {"id": "at_least_one_self_certified_decision_per_level",
         "passed": exact_universe and not decision_failures,
         "expected": [], "actual": decision_failures},
        {"id": "zero_derived_or_retained_law_failures", "passed": not law_failures,
         "expected": [], "actual": law_failures},
    ]
    return gates, law_failures


def consolidate(args) -> int:
    wd = Path(args.workdir)
    rows = [json.loads(p.read_text()) for p in sorted((wd / "results").glob("*.json"))]
    gates, fails = corpus_gate(rows)
    errs = [r for r in rows if r.get("error")]
    ok = [r for r in rows if not r.get("error")]
    total_dec = sum(len(r.get("decisions") or []) for r in rows)
    passed = all(gate["passed"] for gate in gates)
    doc = {
        "_comment": "F01 campaign_breadth ASSERTION pass: the finalizer branch law "
                    "(finalizer iff request != 2 && [0x8008225C] == 0) checked at every "
                    "transition decision on every level of the corpus. Extends the LEVEL01 "
                    "oracle campaign-wide. RUNTIME EVIDENCE, NOT PROOF -- bounded to these "
                    "replays. Regenerate: tools/phase4_f01_breadth_assert.py",
        "schema": "abl-phase4-f01-breadth-assert/1",
        "authority": {"is_proof": False, "promotes_campaign_breadth": False,
                      "changes_f01_status": False, "requires_fresh_verifier": True},
        "law": {"statement": "finalizer 0x80045A60 runs iff request != 2 and [0x8008225C] == 0",
                "decision_pc": "0x8004FF28", "finalizer_pc": "0x8004FF48",
                "cycle_window": CYCLE_WINDOW},
        "method": {"launcher": "tools/launch_repro_playback.sh --execution-mode Interpreter",
                   "playback": "movie.resumeUntilMovieFrame (60 Hz resume path)",
                   "parallel": "one isolated instance per worker, atomic mkdir claiming, "
                               "longest movie first",
                   "guard": "every event self-certifies the instruction word at its own PC"},
        "levels_asserted": len(ok),
        "levels_errored": len(errs),
        "total_decisions_checked": total_dec,
        "corpus_gate": gates,
        "law_failures": fails,
        "law_holds_everywhere": passed,
        "results": {r["level"]: r for r in rows
                    if isinstance(r.get("level"), str)},
    }
    out = Path(args.out or (ROOT / "analysis/phase4_f01_breadth_assertions.json"))
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"levels asserted : {len(ok)}  errored: {len(errs)}")
    print(f"decisions checked: {total_dec}   law failures: {len(fails)}")
    for r in errs:
        print(f"  ERROR {r['level']}: {r['error']}")
    for f in fails:
        print(f"  LAW FAILURE {f}")
    print(f"wrote {out}")
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--port", type=int)
    ap.add_argument("--token")
    ap.add_argument("--consolidate", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    if args.consolidate:
        return consolidate(args)
    if not args.port or not args.token:
        raise SystemExit("worker mode needs --port and --token")
    return worker(args)


if __name__ == "__main__":
    sys.exit(main())
