#!/usr/bin/env python3
"""Phase-2 executable comparison runner: re-collect the pristine oracle's key
baselines from a RUNNING build and FAIL (exit 1) on any divergence.

This is the piece external review asked for: the committed artifacts are
baselines; this runner makes them executable. Two lanes:

  ORDER MATTERS: the movie lane runs FIRST — emulator.loadState restores the
  save state's EMBEDDED memory card, and from-boot movies replay 1:1 only with
  the launcher-seeded card (loading anchors first desyncs every later movie at
  the boot menus; diagnosed live 2026-07-12).

  anchor lane   loadState each hash-pinned identity anchor and compare, against
                the committed artifacts:
                  * typed stable fields  (analysis/phase2_stage_baseline.json)
                  * displayed-frame hash (analysis/phase2_presentation_baseline.json)
                  * SPU voice digest     (analysis/phase2_gate_residuals.json)
                  * contact-pool census  (analysis/phase2_pool_arc_oracle.json)
                Save states validate mounted media, so this lane runs on the
                PRISTINE image — it detects emulator/config/tooling drift and
                re-proves the determinism claims on demand.
  movie lane    replay go_to_end from-boot movies and compare stage-entry frame,
                stage-exit, and end-state collected counters against
                analysis/phase2_completion_oracle.json. From-boot movies replay
                on CANDIDATE discs built from pristine, so this lane is the
                candidate-build regression detector (missing pickups desync the
                counters; broken scene flow breaks the timeline).

Usage:
    tools/launch_repro_playback.sh --config-dir <cfg> --port <p> --token <t> \
        --disc "<image>.cue"
    python3 tools/phase2_compare.py [--port 23472] [--quick] \
        --repro-config-dir <cfg> [--skip-anchors] [--skip-movies] [--out PATH]

--quick compares 5 anchors + 3 movies; default compares all 19 anchors + all 16
movies. Exit 0 = all equal; exit 1 = divergence (report lists every mismatch).
"""
from __future__ import annotations

import argparse
import configparser
import base64
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from build_identity import verify_pristine_media_path
from live_session_provenance import inspect_state_before_load


def validate_repro_config(config_dir: Path, card_seed: Path | None = None) -> dict:
    """Refuse movie comparisons outside the recording-matched profile.

    The movie format's `reproducible` flag does not encode CPU mode or memory
    card identity; both can desync while that flag remains true.
    """
    config_dir = config_dir.resolve()
    if not config_dir.is_absolute() or config_dir == Path.home() / ".local/share/duckstation":
        raise ValueError("repro config must be a dedicated absolute directory")
    settings = config_dir / "duckstation/settings.ini"
    parser = configparser.ConfigParser()
    if not settings.exists() or not parser.read(settings):
        raise ValueError(f"missing replay settings: {settings}")
    required = {
        ("CPU", "ExecutionMode"): "CachedInterpreter",
        ("BIOS", "PatchFastBoot"): "false",
        ("Console", "Enable8MBRAM"): "false",
        ("MemoryCards", "Card1Type"): "PerGameTitle",
        ("MemoryCards", "Directory"): "memcards",
    }
    for (section, key), expected in required.items():
        actual = parser.get(section, key, fallback=None)
        if actual != expected:
            raise ValueError(f"replay setting {section}.{key}={actual!r}, expected {expected!r}")
    card = config_dir / "duckstation/memcards/Disney-Pixar A Bug's Life (USA)_1.mcd"
    seed = card_seed or Path.home() / ".cache/abl/abl_card_seed.mcd"
    if not card.exists() or not seed.exists():
        raise ValueError("replay memory card or declared seed is missing")
    card_hash = hashlib.sha256(card.read_bytes()).hexdigest()
    seed_hash = hashlib.sha256(seed.read_bytes()).hexdigest()
    if card_hash != seed_hash:
        raise ValueError("isolated replay card does not match the declared seed")
    return {"config_dir": str(config_dir), "settings": str(settings),
            "card_seed": str(seed), "card_seed_sha256": seed_hash}
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

POOL_BASE, POOL_SLOTS, POOL_STRIDE = 0x800B0D18, 64, 0x38
SNAPSHOT_FIELDS = [
    ("scene_id", 0x80082504, "u32"),
    ("player_x", 0x800A6500, "s32"), ("player_y", 0x800A6504, "s32"),
    ("player_z", 0x800A6508, "s32"), ("player_floor", 0x800A6548, "s32"),
    ("player_grounded", 0x800A6582, "u8"),
    ("health", 0x800A7E2A, "s16"),      # legacy name: HUD pulse counter
    ("lives", 0x800A65A0, "u8"), ("grain", 0x800A65A1, "u8"),
    ("enemy_quota", 0x800A658E, "u8"), ("equipped_berry", 0x800A6597, "u8"),
    ("power_word", 0x800A6590, "u8"),
]
QUICK_ANCHORS = ["stage01_anthill", "stage03_council_chamber", "stage09_bug_bar",
                 "stage15_canyon_showdown", "training"]
QUICK_MOVIES = ["stage01_anthill", "stage03_council_chamber", "stage09_bug_bar"]


def sha_payload(result: dict) -> str:
    for key in ("data", "png", "base64", "image"):
        if isinstance(result.get(key), str):
            return hashlib.sha256(base64.b64decode(result[key])).hexdigest()
    raise KeyError(f"no payload: {list(result)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-anchors", action="store_true")
    ap.add_argument("--skip-movies", action="store_true")
    ap.add_argument("--write-results-baseline", action="store_true",
                    help="record results/progress anchor frame+typed baselines "
                         "(pristine-guarded) into analysis/phase2_results_baseline.json")
    ap.add_argument("--write-movie-baseline", action="store_true",
                    help="record per-movie mid-stage frame/SPU/pool baselines from "
                         "the pristine image into analysis/phase2_movie_baseline.json")
    ap.add_argument("--out", default=str(ROOT / "analysis" / "phase2_compare_report.json"))
    ap.add_argument("--repro-config-dir",
                    help="required for the from-boot movie lane; directory created by tools/launch_repro_playback.sh")
    args = ap.parse_args()
    repro_profile = None
    if not args.skip_movies:
        if not args.repro_config_dir:
            raise SystemExit("movie lane requires --repro-config-dir from tools/launch_repro_playback.sh; generic debugger configs are not recording-matched")
        try:
            repro_profile = validate_repro_config(Path(args.repro_config_dir))
        except ValueError as exc:
            raise SystemExit(f"REPRO PROFILE GUARD: {exc}")
    if args.write_movie_baseline and args.out == str(
            ROOT / "analysis" / "phase2_compare_report.json"):
        # baseline-writing runs must not clobber the definitive comparison report
        args.out = str(ROOT / "analysis" / "phase2_baseline_write_report.json")

    baseline = json.loads((ROOT / "analysis" / "phase2_stage_baseline.json").read_text())
    presentation = json.loads(
        (ROOT / "analysis" / "phase2_presentation_baseline.json").read_text())
    residuals = json.loads(
        (ROOT / "analysis" / "phase2_gate_residuals.json").read_text())
    pool_doc = json.loads(
        (ROOT / "analysis" / "phase2_pool_arc_oracle.json").read_text())
    completion = json.loads(
        (ROOT / "analysis" / "phase2_completion_oracle.json").read_text())
    movie_baseline_path = ROOT / "analysis" / "phase2_movie_baseline.json"
    movie_baseline = (json.loads(movie_baseline_path.read_text())
                      if movie_baseline_path.exists() else None)
    results_baseline_path = ROOT / "analysis" / "phase2_results_baseline.json"
    results_baseline = (json.loads(results_baseline_path.read_text())
                        if results_baseline_path.exists() else None)

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(900)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def snapshot():
        snap = {}
        for name, addr, width in SNAPSHOT_FIELDS:
            raw = rd(addr, {"u8": 1, "s16": 2, "u32": 4, "s32": 4}[width])
            fmt = {"u8": "<B", "s16": "<h", "u32": "<I", "s32": "<i"}[width]
            snap[name] = struct.unpack(fmt, raw)[0]
        return snap

    def pool_census():
        buf = rd(POOL_BASE, POOL_SLOTS * POOL_STRIDE)
        active = []
        for i in range(POOL_SLOTS):
            e = buf[i * POOL_STRIDE:(i + 1) * POOL_STRIDE]
            if struct.unpack_from("<H", e, 0x22)[0] > 0:
                active.append(i)
        return active, hashlib.sha256(buf).hexdigest()

    def voice_digest(s):
        return [{k: v.get(k) for k in
                 ("index", "on", "pitch", "left_volume", "right_volume",
                  "adsr_volume", "phase", "start_address", "current_address")}
                for v in s["voices"]]

    def stop_movie():
        for m in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(m, {})
            except Exception:
                pass

    status = c.call("debugger.status", {})
    try:
        mounted_verification = verify_pristine_media_path(status.get("game_path", ""))
    except SystemExit as exc:
        # Candidate images are valid comparison targets. Every save anchor must
        # still be centrally declared strict pristine and must embed hash-pinned
        # pristine media; inspect_state_before_load enforces those properties.
        mounted_verification = {"pristine_verified": False,
                                "candidate_media": True,
                                "detail": str(exc)}
    media_identity = {"game_serial": status.get("game_serial"),
                      "game_title": status.get("game_title"),
                      "game_path": status.get("game_path"),
                      "hash_verification": mounted_verification}
    mismatches = []
    checked = {"anchors": 0, "movies": 0, "comparisons": 0}
    new_movie_baseline: dict = {}
    new_results_baseline: dict = {}
    state_inspections = []

    def check(where, what, expected, actual):
        checked["comparisons"] += 1
        if expected != actual:
            mismatches.append({"where": where, "what": what,
                               "expected": expected, "actual": actual})

    # ---- movie lane ----------------------------------------------------------
    if not args.skip_movies:
        labels = QUICK_MOVIES if args.quick else list(completion["stages"])
        for label in labels:
            st = completion["stages"][label]
            stop_movie()
            r = c.call("movie.load", {"path": str(ROOT / st["movie"])})
            pb = c.call("movie.startPlayback", {"load_start_state": True})
            if not pb.get("playing"):
                mismatches.append({"where": label, "what": "movie_playback",
                                   "expected": "playing", "actual": str(pb)})
                continue
            c.call("debugger.pause", {})
            checked["movies"] += 1
            # entry: scene equals target at the recorded entry sample frame
            entry = st["entered_stage_frame"]
            c.call("movie.advanceToFrame",
                   {"frame": entry, "max_frames": st["frames"] + 700}, timeout=900)
            scene = struct.unpack("<I", rd(0x80082504, 4))[0]
            check(label, "entry_scene", st["target_scene"], scene)
            # mid-stage visual/audio/pool checkpoint (candidate-lane coverage for
            # broken terrain, corrupted audio, missing pickups — review item):
            # sampled at entry+600, a deterministic in-stage movie frame
            mid = entry + 600
            if mid < st["frames"]:
                c.call("movie.advanceToFrame",
                       {"frame": mid, "max_frames": st["frames"] + 700}, timeout=900)
                frame_hash = sha_payload(c.call(
                    "gpu.frameSnapshot", {"buffer": "displayed", "format": "raw16"}))
                voices = voice_digest(c.call("spu.status", {}))
                p_active, p_digest = pool_census()
                if args.write_movie_baseline:
                    new_movie_baseline[label] = {
                        "mid_frame": mid, "frame_sha256": frame_hash,
                        "spu_voices": voices,
                        "pool_active": p_active, "pool_sha256": p_digest}
                elif movie_baseline and label in movie_baseline.get("movies", {}):
                    mb = movie_baseline["movies"][label]
                    check(label, "mid_frame_sha256", mb["frame_sha256"], frame_hash)
                    check(label, "mid_spu_voices", mb["spu_voices"], voices)
                    check(label, "mid_pool_active", mb["pool_active"], p_active)
                    check(label, "mid_pool_sha256", mb["pool_sha256"], p_digest)
            # end: counters + exit at movie end
            c.call("movie.advanceToFrame",
                   {"frame": st["frames"], "max_frames": st["frames"] + 700},
                   timeout=900)
            end = snapshot()
            exp = st["movie_end_snapshot"]
            for field in ("scene_id", "grain", "lives", "enemy_quota"):
                check(label, f"end:{field}", exp[field], end[field])
            print(f"[compare] movie {label}: "
                  f"{'OK' if not [m for m in mismatches if m['where'] == label] else 'MISMATCH'}")

    # ---- anchor lane (identity + bonus + RESULTS/completion anchors) ---------
    # review: the results lane was excluded, so results-screen presentation,
    # token grants and displayed totals were unchecked. Completion anchors now
    # compare their typed stable fields AND their displayed frame hash.
    if not args.skip_anchors:
        labels = QUICK_ANCHORS if args.quick else list(baseline["stages"])
        for label in labels:
            st = baseline["stages"].get(label)
            if not st or st.get("role") not in (
                    "identity", "identity_bonus", "lifecycle_completion",
                    "objective_progress"):
                continue
            stop_movie()
            state_info = inspect_state_before_load(
                c, ROOT / st["save"], media_identity)
            r = c.call("emulator.loadState",
                       {"path": str(ROOT / st["save"]), "pause_after_load": True})
            if not r.get("loaded"):
                mismatches.append({"where": label, "what": "loadState",
                                   "expected": "loaded", "actual": str(r)})
                continue
            checked["anchors"] += 1
            state_inspections.append(state_info)
            snap = snapshot()
            for field in st["stable_fields"]:
                if field in snap:
                    check(label, f"stable:{field}", st["anchor"][field], snap[field])
            pres = presentation["anchors"].get(label)
            got_frame = sha_payload(c.call("gpu.frameSnapshot",
                                           {"buffer": "displayed", "format": "raw16"}))
            if pres:
                check(label, "frame_sha256", pres["frame_sha256"], got_frame)
            elif results_baseline and label in results_baseline.get("anchors", {}):
                # results/progress anchors: frame hash pinned by the results lane
                check(label, "results_frame_sha256",
                      results_baseline["anchors"][label]["frame_sha256"], got_frame)
            if args.write_results_baseline and not pres:
                new_results_baseline[label] = {
                    "save": st["save"], "role": st["role"],
                    "frame_sha256": got_frame,
                    "typed": {k: snap[k] for k in st["stable_fields"] if k in snap},
                }
            aud = residuals["audio_baseline"].get(label)
            if aud:
                got_v = voice_digest(c.call("spu.status", {}))
                check(label, "spu_voices", aud["voices"], got_v)
            pool = pool_doc["pool_census"].get(label)
            if pool:
                active, digest = pool_census()
                check(label, "pool_active_slots",
                      [s["slot"] for s in pool["slots"]], active)
                check(label, "pool_sha256", pool["pool_sha256"], digest)
            print(f"[compare] anchor {label}: "
                  f"{'OK' if not [m for m in mismatches if m['where'] == label] else 'MISMATCH'}")

    def _verify_pristine():
        prov = json.loads((ROOT / "tools" / "disc_provenance.json").read_text())
        game_path = Path(status.get("game_path", ""))
        bin_path = None
        if game_path.suffix.lower() == ".cue":
            import re as _re
            for line in game_path.read_text(errors="replace").splitlines():
                m = _re.match(r'\s*FILE\s+"([^"]+)"', line, _re.I)
                if m:
                    bin_path = (game_path.parent / m.group(1)).resolve()
                    break
        pin = prov["files"]["Disney-Pixar A Bug's Life (v1.0).bin"]["sha1"]
        h = hashlib.sha1()
        with bin_path.open("rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        got = h.hexdigest()
        if got != pin:
            raise SystemExit(
                f"PRISTINE GUARD: mounted image {bin_path} sha1 {got} != pinned "
                f"pristine {pin} — REFUSING to write an authoritative baseline "
                "from a non-pristine build.")
        return str(bin_path), got

    if args.write_results_baseline:
        bin_path, got = _verify_pristine()
        results_baseline_path.write_text(json.dumps({
            "_comment": "Results/progress anchor baselines (frame hash + typed "
                        "stable fields) from the HASH-VERIFIED pristine image. "
                        "Regenerate: tools/phase2_compare.py --write-results-baseline.",
            "generated": date.today().isoformat(),
            "media": {"path": bin_path, "sha1": got},
            "anchors": new_results_baseline}, indent=1) + "\n")
        print(f"[compare] wrote results baseline for {len(new_results_baseline)} anchors")

    if args.write_movie_baseline:
        # PRISTINE GUARD (review: a same-serial MOD image could otherwise bless
        # the authoritative baseline): the mounted BIN must hash-match the pinned
        # pristine image before anything is written.
        prov = json.loads((ROOT / "tools" / "disc_provenance.json").read_text())
        game_path = Path(status.get("game_path", ""))
        bin_path = None
        if game_path.suffix.lower() == ".cue":
            import re as _re
            for line in game_path.read_text(errors="replace").splitlines():
                m = _re.match(r'\s*FILE\s+"([^"]+)"', line, _re.I)
                if m:
                    bin_path = (game_path.parent / m.group(1)).resolve()
                    break
        pin = prov["files"]["Disney-Pixar A Bug's Life (v1.0).bin"]["sha1"]
        h = hashlib.sha1()
        with bin_path.open("rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        got = h.hexdigest()
        if got != pin:
            raise SystemExit(
                f"PRISTINE GUARD: mounted image {bin_path} sha1 {got} != pinned "
                f"pristine {pin} — REFUSING to write the authoritative movie "
                "baseline from a non-pristine build.")
        movie_fixture_hashes = {
            lbl: hashlib.sha256(
                (ROOT / completion["stages"][lbl]["movie"]).read_bytes()).hexdigest()
            for lbl in new_movie_baseline}
        movie_baseline_path.write_text(json.dumps({
            "_comment": "Per-movie mid-stage (entry+600) frame/SPU/pool baselines "
                        "from the HASH-VERIFIED pristine image. Regenerate: "
                        "tools/phase2_compare.py --write-movie-baseline on a FRESH "
                        "repro instance mounting the pristine cue (guarded).",
            "generated": date.today().isoformat(),
            "media": {"path": str(bin_path), "sha1": got,
                      "serial": status.get("game_serial")},
            "movie_fixture_sha256": movie_fixture_hashes,
            "movies": new_movie_baseline}, indent=1) + "\n")
        print(f"[compare] wrote movie baseline for {len(new_movie_baseline)} movies "
              f"(pristine sha1 verified {got[:12]}…)")

    report = {
        "_comment": "Executable pristine-vs-candidate comparison report. "
                    "Regenerate: tools/phase2_compare.py against a running build.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial"),
                  "title": status.get("game_title"),
                  "path": status.get("game_path")},
        "mode": "quick" if args.quick else "full",
        "repro_profile": repro_profile,
        "mounted_media_verification": mounted_verification,
        "state_inspections": state_inspections,
        "checked": checked,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:200],
        "verdict": "PASS" if not mismatches else "FAIL",
    }
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    print(f"[compare] {report['verdict']}: {checked['comparisons']} comparisons over "
          f"{checked['anchors']} anchors + {checked['movies']} movies; "
          f"{len(mismatches)} mismatch(es). Report: {args.out}")
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
