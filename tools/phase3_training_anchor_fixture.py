#!/usr/bin/env python3
"""Generate or verify the strict-pristine Training gameplay save used by censuses.

The legacy ``collecting_FLIK_LEVELTRAINING.movie.sav`` carries the retail serial
but was recorded on ALLMODS. This tool derives its replacement only by replaying
the hash-pinned from-boot Training movie on hash-verified pristine media to movie
playback index 6904 (scene 17).  The guest is paused before playback starts so
the separate start/advance RPCs cannot consume a host-scheduling-dependent number
of frames.  Every run regenerates a transient candidate and byte-compares it with
the centrally pinned external fixture before that fixture may be consumed.

The save remains external/copyrighted and must never be committed. Only its pin,
recipe, state metadata, and live provenance are banked here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         verified_media_identity,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               verified_media_identity,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
MOVIE = "collecting_FLIK_LEVELTRAINING.movie.json"
DEFAULT_OUTPUT = "phase3_pristine_training_gameplay_i5.sav"
TARGET_MOVIE_FRAME = 6904
EXPECTED_EMULATOR_FRAME = 6905
EXPECTED_SCENE = 17


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=ROOT / DEFAULT_OUTPUT)
    add_required_live_args(ap)
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient

    output = args.output.resolve()
    try:
        output_rel = output.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise SystemExit("--output must be a provisioned path inside this checkout") from exc
    movie = ROOT / MOVIE
    movie_doc = json.loads(movie.read_text())
    start = movie_doc.get("start_state") or {}
    if not (movie_doc.get("version") == 3 and start.get("from_boot") is True
            and start.get("reproducible_only_from_state") is False
            and not start.get("path") and not start.get("sha256")):
        raise SystemExit(f"Training movie is no longer an independent from-boot anchor: {start}")

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(900)
    status = c.call("debugger.status", {})
    media_identity = verified_media_identity(c, status)

    fixture_created_now = not output.exists()
    fixture_entries = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text()
    )["entries"]
    fixture_declaration = fixture_entries.get(output_rel) or {}
    expected_fixture = (
        fixture_declaration.get("sha256"), fixture_declaration.get("size"))
    if not all(expected_fixture):
        raise SystemExit(
            f"Training output is not centrally hash/size declared: {output_rel}")
    if output.exists() and (sha256(output), output.stat().st_size) != expected_fixture:
        raise SystemExit(
            "provisioned Training fixture differs from its central declaration: "
            f"actual={sha256(output)}/{output.stat().st_size} "
            f"expected={expected_fixture[0]}/{expected_fixture[1]}")
    candidate = Path(args.config_dir).resolve() / "training-anchor-replay.sav"
    candidate.unlink(missing_ok=True)
    c.call("debugger.pause", {})
    loaded_movie = c.call("movie.load", {"path": str(movie)})
    started = c.call("movie.startPlayback", {
        "start_frame": 0, "load_start_state": True,
    })
    if not started.get("playing") or not started.get("reproducible"):
        raise SystemExit(f"Training movie playback is not reproducible: {started}")
    before_advance = c.call("movie.status", {})
    advanced = c.call("movie.advanceToFrame", {
        "frame": TARGET_MOVIE_FRAME,
        "max_frames": TARGET_MOVIE_FRAME + 700,
    }, timeout=900)
    c.call("debugger.pause", {})
    status_at_anchor = c.call("debugger.status", {})
    movie_at_anchor = c.call("movie.status", {})
    scene = c.call("debugger.readU32", {"address": "0x80082504"}).get("value")
    if scene != EXPECTED_SCENE:
        raise SystemExit(
            f"Training replay did not reach scene {EXPECTED_SCENE}: scene={scene}")
    if before_advance.get("playback_index") != 0 or \
            advanced.get("start_playback_index") != 0:
        raise SystemExit(
            "Training replay raced before deterministic advancement: "
            f"before={before_advance.get('playback_index')} "
            f"advance_start={advanced.get('start_playback_index')}")
    if movie_at_anchor.get("playback_index") != TARGET_MOVIE_FRAME or \
            status_at_anchor.get("frame") != EXPECTED_EMULATOR_FRAME:
        raise SystemExit(
            "Training replay stopped at the wrong deterministic boundary: "
            f"movie={movie_at_anchor.get('playback_index')} "
            f"emulator={status_at_anchor.get('frame')}")
    saved = c.call("emulator.saveState", {"path": str(candidate)})
    if saved.get("saved") is not True:
        raise SystemExit(f"saveState failed: {saved}")
    stopped_playback = c.call("movie.stopPlayback", {})
    if stopped_playback.get("playing") is not False:
        raise SystemExit(f"movie playback did not stop cleanly: {stopped_playback}")

    candidate_sha256 = sha256(candidate)
    candidate_size = candidate.stat().st_size
    if (candidate_sha256, candidate_size) != expected_fixture:
        raise SystemExit(
            "deterministic Training regeneration differs from the central fixture "
            f"pin: generated={candidate_sha256}/{candidate_size} "
            f"expected={expected_fixture[0]}/{expected_fixture[1]}")
    if fixture_created_now:
        candidate.replace(output)
    else:
        output_sha256 = sha256(output)
        output_size = output.stat().st_size
        if (candidate_sha256, candidate_size) != (output_sha256, output_size):
            raise SystemExit(
                "deterministic Training regeneration differs from the provisioned "
                f"fixture: generated={candidate_sha256}/{candidate_size} "
                f"provisioned={output_sha256}/{output_size}")
    playback = {
        "reproduction_verified": True,
        "candidate_generated_in_this_run": True,
        "provisioned_fixture_created_in_this_run": fixture_created_now,
        "requested_start_frame": 0,
        "start_playback_index": before_advance.get("playback_index"),
        "advance_start_playback_index": advanced.get("start_playback_index"),
        "target_movie_frame": TARGET_MOVIE_FRAME,
        "observed_playback_index": movie_at_anchor.get("playback_index"),
        "observed_emulator_frame": status_at_anchor.get("frame"),
        "observed_cycle": status_at_anchor.get("cycle"),
        "observed_pc": status_at_anchor.get("pc"),
        "loaded_frame_count": loaded_movie.get("frame_count"),
        "reproducible": started.get("reproducible"),
        "generated_sha256": candidate_sha256,
        "generated_size": candidate_size,
        "matches_provisioned_fixture": True,
    }

    state_inspection = inspect_state_before_load(c, output, media_identity)
    loaded = c.call("emulator.loadState", {
        "path": str(output), "pause_after_load": True, "validate_disc": True,
    })
    if loaded.get("loaded") is not True:
        raise SystemExit(f"replacement Training save failed to load: {loaded}")
    scene = c.call("debugger.readU32", {"address": "0x80082504"}).get("value")
    if scene != EXPECTED_SCENE:
        raise SystemExit(
            f"replacement Training save is not in scene {EXPECTED_SCENE}: {scene}")

    pins = {output_rel: sha256(output), MOVIE: sha256(movie)}
    run_provenance = finish_run(
        args, generator="tools/phase3_training_anchor_fixture.py",
        anchor={
            "save": output_rel,
            "fixture_sha256": pins,
            "state_inspections": [state_inspection],
            "media_identity": media_identity,
        },
        timing={
            "movie": MOVIE,
            "movie_frame": TARGET_MOVIE_FRAME,
            "emulator_frame": EXPECTED_EMULATOR_FRAME,
            "expected_scene": EXPECTED_SCENE,
            "candidate_generated_in_this_run": True,
            "provisioned_fixture_created_in_this_run": fixture_created_now,
        },
    )
    doc = {
        "_comment": "Strict-pristine Training gameplay save recipe and verification. "
                    "The external save is never committed. Regenerate or verify: "
                    "python3 tools/phase3_training_anchor_fixture.py --output "
                    "phase3_pristine_training_gameplay_i5.sav <live args>.",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "fixture_sha256": pins,
        "output": output_rel,
        "output_size": output.stat().st_size,
        "movie": {
            "path": MOVIE,
            "version": movie_doc.get("version"),
            "frames": len(movie_doc.get("frames") or []),
            "from_boot": start.get("from_boot"),
            "reproducible_only_from_state": start.get("reproducible_only_from_state"),
            "target_frame": TARGET_MOVIE_FRAME,
        },
        "playback_generation": playback,
        "observed_scene": scene,
        "classification": "strict_pristine",
        "supersedes": "collecting_FLIK_LEVELTRAINING.movie.sav as original authority",
    }
    write_live_evidence(ROOT / "analysis/phase3_training_anchor_fixture.json", doc)
    print(f"[training-anchor] {'generated' if fixture_created_now else 'verified'} "
          f"{output_rel} sha256={pins[output_rel]} scene={scene}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
