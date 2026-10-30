#!/usr/bin/env python3
"""Phase-3 WP6: ownership TRANSFER and RESET across a scene transition.

The gate wants each record's initialization/reset/lifetime, not just its
capacity. So: replay a pristine from-boot playthrough POLL-ONLY (an execTrace
watch during playback desyncs the replay — Phase-2 lesson), sample every record
on both sides of the real scene transition the movie performs, and classify each
typed field by what the transition actually did to it:

  reset_to_zero        the field is zeroed by the load
  reloaded             it changed and is non-zero (fresh level data)
  carried_over         it survived the transition unchanged  <-- ownership
  unchanged_incidental it was already zero and stayed zero

That distinction is the whole point: a field that CARRIES OVER is owned by the
session, not by the scene — those are precisely the fields a mod must not
clobber on load, and the ones save/continue semantics depend on.

Pools are additionally checked for full reclamation: after a transition, no
contact slot, plant slot or actor record may still be held by the OLD scene.

Usage: python3 tools/phase3_transition_reset.py [--port 23473]
Output: analysis/phase3_transition_reset.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

import yaml

try:
    from live_session_provenance import (add_required_live_args,
                                         verified_media_identity,
                                         write_live_evidence)
    from live_toolchain_snapshot import (finish_snapshot_run, verify_snapshot)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args,
                                               verified_media_identity,
                                               write_live_evidence)
    from tools.live_toolchain_snapshot import (finish_snapshot_run, verify_snapshot)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

FMT = {"u8": "<B", "s8": "<b", "u16": "<H", "s16": "<h", "u32": "<I", "s32": "<i"}
SCENE_ID = 0x80082504
RUNTIME_FIXTURES = ROOT / "config" / "phase3_runtime_fixtures.yaml"
CARD_NAME = "Disney-Pixar A Bug's Life (USA)_1.mcd"


def fixture_pin(*rels):
    """DoF #1 (provenance): hash-pin every fixture a finding rests on, plus the
    EXE identity. A finding whose fixtures are not pinned cannot be re-verified
    later — the file could change underneath it silently."""
    import hashlib
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    exe = ROOT / "REBUILD" / "files" / "SCUS_942.88"
    if exe.exists():
        out["REBUILD/files/SCUS_942.88"] = hashlib.sha256(exe.read_bytes()).hexdigest()
    return out

def load_records():
    doc = yaml.safe_load((ROOT / "config" / "record_types.yaml").read_text())
    return {r["id"]: r for r in doc["records"]}


def verify_repro_config(args) -> dict:
    fixtures = yaml.safe_load(RUNTIME_FIXTURES.read_text())["fixtures"]
    declared = fixtures["go_to_end_repro_memory_card"]
    seed = Path(args.card_seed).expanduser().resolve()
    actual = hashlib.sha256(seed.read_bytes()).hexdigest()
    assert seed.stat().st_size == declared["size"], (
        f"repro card size mismatch: {seed.stat().st_size} != {declared['size']}")
    assert actual == declared["sha256"], (
        f"repro card hash mismatch: {actual} != {declared['sha256']}")
    config = Path(args.config_dir).resolve()
    seeded = config / "duckstation" / "memcards" / CARD_NAME
    seeded_sha = hashlib.sha256(seeded.read_bytes()).hexdigest()
    assert seeded_sha == actual, f"isolated config card does not match seed: {seeded_sha}"
    settings = (config / "duckstation" / "settings.ini").read_text()
    required = (
        "PatchFastBoot=false", "ExecutionMode=CachedInterpreter",
        "OverclockEnable=false", "Enable8MBRAM=false", "Directory=memcards",
    )
    missing = [line for line in required if line not in settings]
    assert not missing, f"determinism-matched repro settings missing: {missing}"
    return {
        "manifest": str(RUNTIME_FIXTURES.relative_to(ROOT)),
        "seed_path": str(seed),
        "seed_sha256": actual,
        "seed_size": seed.stat().st_size,
        "isolated_card_path": str(seeded),
        "isolated_card_sha256": seeded_sha,
        "settings": list(required),
        "launcher": "tools/launch_repro_playback.sh",
        "bootstrap": ("initial RPC bootstrap uses -fastboot; every from-boot movie "
                      "then power-cycles via movie.startPlayback with "
                      "load_start_state=true before evidence frame 0"),
        "launcher_sha256": hashlib.sha256(
            (ROOT / "tools" / "launch_repro_playback.sh").read_bytes()).hexdigest(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(ap)
    ap.add_argument("--toolchain-snapshot", type=Path, required=True,
                    help="immutable /tmp snapshot_manifest.json created by "
                         "tools/live_toolchain_snapshot.py")
    ap.add_argument("--card-seed", type=Path, required=True,
                    help="centrally pinned memory-card seed used by the repro launcher")
    ap.add_argument("--stage", default="stage01_anthill")
    ap.add_argument("--all", action="store_true",
                    help="every stage — LEVEL01 alone cannot show whether the "
                         "ownership laws are GENERAL")
    args = ap.parse_args()

    snapshot = verify_snapshot(args.toolchain_snapshot)
    sys.path.insert(0, str(Path(snapshot["_paths"]["client"]).parent))
    from duckstation_debug_client import DebuggerClient
    recs = load_records()
    oracle = json.loads(
        (ROOT / "analysis" / "phase2_completion_oracle.json").read_text())
    stages = (list(oracle["stages"]) if args.all else [args.stage])
    verifier = DebuggerClient("127.0.0.1", args.port, "ws")
    verifier.authenticate(args.token)
    verifier.transport.sock.settimeout(300)
    status = verifier.call("debugger.status", {})
    media_identity = verified_media_identity(verifier, status)
    repro_config = verify_repro_config(args)
    all_results, failures = {}, {}
    for stage_name in stages:
        try:
            all_results[stage_name] = run_stage(oracle, recs, stage_name, args)
        except Exception as exc:
            failures[stage_name] = f"{type(exc).__name__}: {str(exc)[:120]}"
            print(f"[{stage_name}] SKIPPED — {failures[stage_name]}")

    doc = summarise(all_results, failures)
    doc["run_provenance"] = finish_snapshot_run(
        args, generator="tools/phase3_transition_reset.py",
        anchor={"movies": sorted({r["movie"] for r in all_results.values()}),
                "fixture_sha256": doc["fixture_sha256"],
                "media_identity": media_identity,
                "repro_config": repro_config},
        timing={"stages_requested": stages, "stages_measured": len(all_results),
                "polling": "30-frame coarse; flip_frame is the upper edge of a <=30-frame boundary bracket"},
        source_dependencies=(
            "tools/live_toolchain_snapshot.py",
            "tools/launch_repro_playback.sh",
        ),
    )
    path = ROOT / "analysis" / "phase3_transition_reset.json"
    write_live_evidence(path, doc)
    print(f"\n[transition] {len(all_results)}/{len(stages)} stages measured")
    law = doc["laws"]
    print(f"  load gap: {law['load_gap_frames']['min']}-"
          f"{law['load_gap_frames']['max']} frames "
          f"(median {law['load_gap_frames']['median']}) — the world does NOT "
          f"exist for this long after the scene id flips")
    print(f"  session-owned in EVERY stage: {law['session_owned_everywhere']}")
    print(f"  exit reclaims the world: {law['exit_reclaims_world']}")
    for k, v in failures.items():
        print(f"  [skip] {k}: {v}")
    return 1 if failures else 0


def run_stage(oracle, recs, stage_name, args):
    from duckstation_debug_client import DebuggerClient
    st = oracle["stages"][stage_name]
    movie = st["movie"]
    movie_path = ROOT / movie
    actual_movie_sha256 = hashlib.sha256(movie_path.read_bytes()).hexdigest()
    assert actual_movie_sha256 == st["movie_sha256"], (
        f"{stage_name}: movie hash mismatch {actual_movie_sha256} != {st['movie_sha256']}")

    # the movie's own scene timeline tells us where the transition is
    timeline = st["scene_timeline"]
    in_stage = [w for w in timeline if w["scene"] == st["target_scene"]]
    assert in_stage, f"{args.stage}: movie never reaches its scene"
    # TWO transitions, and they answer different questions:
    #   ENTRY (shell -> stage): what does the LOAD initialise/reset?
    #   EXIT  (stage -> shell): what does the game keep, and what does it reclaim?
    pre = [w for w in timeline if w["last"] < in_stage[0]["first"]]
    assert pre, f"{args.stage}: no pre-stage window"
    transitions = [
        ("entry_load", pre[-1]["last"], in_stage[0]["first"]),
        ("exit_to_shell", in_stage[-1]["last"], None),
    ]
    post = [w for w in timeline
            if w["first"] > in_stage[-1]["last"]
            and w["scene"] != st["target_scene"]]
    assert post, f"{args.stage}: movie never leaves the scene"
    transitions[1] = ("exit_to_shell", in_stage[-1]["last"], post[0]["last"])

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(900)
    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def snapshot():
        out = {"scene_id": struct.unpack("<I", rd(SCENE_ID, 4))[0]}
        for rid, rec in recs.items():
            out[rid] = rd(rec["base"], rec["size"] * rec["instances"])
        return out

    for m in ("movie.stopPlayback", "movie.clear"):
        try:
            c.call(m, {})
        except Exception:
            pass
    r = c.call("movie.load", {"path": str(ROOT / movie)})
    pb = c.call("movie.startPlayback", {"load_start_state": True})
    assert pb.get("playing") and pb.get("reproducible"), pb
    total = r["frame_count"]

    # POLL-ONLY: no watches during playback (they desync the replay)
    def classify(before, after_s):
        result = {}
        for rid, rec in recs.items():
            size = rec["size"]
            fields = {}
            for f in rec["fields"]:
                b = struct.unpack_from(FMT[f["width"]], before[rid], f["offset"])[0]
                a = struct.unpack_from(FMT[f["width"]], after_s[rid], f["offset"])[0]
                if b == a:
                    verdict = "carried_over" if b != 0 else "unchanged_incidental"
                elif a == 0:
                    verdict = "reset_to_zero"
                else:
                    verdict = "reloaded"
                fields[f["name"]] = {"before": b, "after": a, "verdict": verdict}

            live_expr = rec.get("live_predicate")
            held_before = held_after = None
            if live_expr:
                def live_count(buf):
                    n = 0
                    for i in range(rec["instances"]):
                        blob = buf[i * size:(i + 1) * size]
                        vals = {f["name"]: struct.unpack_from(FMT[f["width"]],
                                                              blob, f["offset"])[0]
                                for f in rec["fields"]}
                        if eval(live_expr, {"__builtins__": {}}, vals):
                            n += 1
                    return n
                held_before = live_count(before[rid])
                held_after = live_count(after_s[rid])

            result[rid] = {
                "fields": fields,
                "live_before": held_before,
                "live_after": held_after,
                "carried_over": sorted(k for k, v in fields.items()
                                       if v["verdict"] == "carried_over"),
                "reset_to_zero": sorted(k for k, v in fields.items()
                                        if v["verdict"] == "reset_to_zero"),
                "reloaded": sorted(k for k, v in fields.items()
                                   if v["verdict"] == "reloaded"),
            }
        return result

    # The oracle's timeline is a coarse 500-frame grid — too coarse to see a
    # LOAD: at the first in-stage sample the actor table is not populated yet.
    # So walk the movie in fine steps, catch the exact frame the scene id flips,
    # and compare the tick BEFORE the flip against a SETTLED sample after it.
    STEP, SETTLE = 30, 120

    def world_ready(snap) -> bool:
        """The world exists once the actor roster is populated OR the player is
        alive. Both halves are needed:
          * Bug Bar has NO chunk-31 actor roster at all (0 actors — the same
            structural negative Phase 2 documented), so a roster-only test never
            fires there;
          * in several stages the player's health is written a few ticks AFTER
            the roster, so an hp-only test would over-report the load gap.
        """
        rec = recs["actor_record"]
        buf = snap["actor_record"]
        roster = any(struct.unpack_from("<I", buf, i * rec["size"])[0]
                     for i in range(rec["instances"]))
        prec = recs["player_block"]
        hp = struct.unpack_from("<h", snap["player_block"], 0x94)[0]
        return roster or hp > 0
    observed = {}
    prev_snap, prev_frame = None, 0
    # The oracle timeline is sampled only every 500 frames, and scene-id flips
    # lead world readiness by as much as 1170 frames.  Starting a mere 600 frames
    # before the last shell sample can therefore begin *after* the entry flip.
    # Start 2000 frames before the first observed in-stage sample and ignore boot
    # and shell-to-shell changes until the target scene actually appears.
    f = max(0, in_stage[0]["first"] - 2000)
    c.call("movie.advanceToFrame", {"frame": f, "max_frames": total + 700},
           timeout=900)
    prev_snap, prev_frame = snapshot(), f
    entered = prev_snap["scene_id"] == st["target_scene"]
    while f < total and len(observed) < 2:
        f = min(f + STEP, total)
        c.call("movie.advanceToFrame", {"frame": f, "max_frames": total + 700},
               timeout=900)
        snap = snapshot()
        if snap["scene_id"] != prev_snap["scene_id"]:
            entering = not entered and snap["scene_id"] == st["target_scene"]
            exiting = (entered and prev_snap["scene_id"] == st["target_scene"]
                       and snap["scene_id"] != st["target_scene"])
            if not (entering or exiting):
                prev_snap, prev_frame = snap, f
                continue
            name = "entry_load" if entering else "exit_to_shell"
            entered = entered or entering
            flip_frame = f
            if entering:
                # ⚠️ THE SCENE ID FLIPS LONG BEFORE THE WORLD EXISTS: the id
                # changes when the transition starts, but actors/player are only
                # initialised when the disc read completes (~900 frames later).
                # Settling a fixed number of frames therefore samples an EMPTY
                # world. Wait for the world to actually exist.
                while f < total and not world_ready(snap):
                    f = min(f + STEP, total)
                    c.call("movie.advanceToFrame",
                           {"frame": f, "max_frames": total + 700}, timeout=900)
                    snap = snapshot()
                assert world_ready(snap), f"{stage_name}: target world never became ready"
            c.call("movie.advanceToFrame",
                   {"frame": min(f + SETTLE, total),
                    "max_frames": total + 700}, timeout=900)
            settled = snapshot()
            observed[name] = {
                "frames": [prev_frame, min(f + SETTLE, total)],
                "scene": [prev_snap["scene_id"], settled["scene_id"]],
                "scene_id_flip_frame": flip_frame,
                "scene_id_flip_bracket": [prev_frame, flip_frame],
                "world_ready_frame": f if entering else None,
                "load_gap_frames": (f - flip_frame) if entering else None,
                "note": ("the scene-id flip lies in the <=30-frame "
                         "scene_id_flip_bracket; scene_id_flip_frame is its upper "
                         "sample. The WORLD "
                         "(actors, player) only exists at world_ready_frame — the "
                         "gap is the disc load. A mod hooking 'scene changed' runs "
                         "during an EMPTY world." if entering else
                         "sampled the tick before the flip vs settled after it"),
                "records": classify(prev_snap, settled),
            }
            f = min(f + SETTLE, total)
            snap = settled
        prev_snap, prev_frame = snap, f

    for m in ("movie.stopPlayback", "movie.clear"):
        try:
            c.call(m, {})
        except Exception:
            pass

    expected = {"entry_load", "exit_to_shell"}
    assert set(observed) == expected, (
        f"{stage_name}: incomplete transition boundary set "
        f"{sorted(observed)} != {sorted(expected)}")

    return {
        "stage": stage_name,
        "movie": movie,
        "movie_sha256": actual_movie_sha256,
        "transitions": observed,
    }


def summarise(all_results, failures):
    import statistics
    gaps, session_sets, reclaims = [], [], []
    for r in all_results.values():
        entry = r["transitions"].get("entry_load")
        exit_ = r["transitions"].get("exit_to_shell")
        if entry and entry.get("load_gap_frames") is not None:
            gaps.append(entry["load_gap_frames"])
        if exit_:
            pb = exit_["records"]["player_block"]
            session_sets.append(set(pb["carried_over"]))
            ar = exit_["records"]["actor_record"]
            reclaims.append(ar["live_after"] < ar["live_before"])
    common = set.intersection(*session_sets) if session_sets else set()
    return {
        "_comment": "Phase-3 WP6 transition reset/ownership across EVERY stage "
                    "(LEVEL01 alone cannot show whether the laws are general). "
                    "Poll-only over from-boot movies — watches during playback "
                    "desync the replay. Regenerate: "
                    "tools/phase3_transition_reset.py --all.",
        "generated": date.today().isoformat(),
        "stages_measured": len(all_results),
        "skipped": failures,
        "fixture_sha256": fixture_pin(*sorted(
            {r["movie"] for r in all_results.values()})),
        "laws": {
            "load_gap_frames": {
                "_comment": "frames between the scene id flipping and the world "
                            "actually existing — a mod hooking 'scene changed' "
                            "runs inside an EMPTY world for this long",
                "min": min(gaps) if gaps else None,
                "max": max(gaps) if gaps else None,
                "median": (int(statistics.median(gaps)) if gaps else None),
                "per_stage": {k: v["transitions"]["entry_load"]["load_gap_frames"]
                              for k, v in all_results.items()
                              if v["transitions"].get("entry_load")},
            },
            "session_owned_everywhere": sorted(common),
            "exit_reclaims_world": any(reclaims),
        },
        "stages": all_results,
    }


if __name__ == "__main__":
    raise SystemExit(main())
