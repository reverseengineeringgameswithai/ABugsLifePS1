#!/usr/bin/env python3
"""Bank the C16 post-game-over title-restart and native-card boundary.

The dedicated C16 recording is replayed on a fresh isolated copy of the
centrally pinned memory card.  Natural input and a derivative that removes only
the last seven Start samples are compared at identical movie boundaries.  The
tool retains hashes and typed state, never the card, save, movie derivative, or
captured frame bytes.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

try:
    import phase4_grain_gates as e09
    import phase4_lives_gameover as c16
    from live_session_provenance import (
        add_required_live_args,
        finish_run,
        inspect_state_before_load,
        retained_pristine_save_gaps,
        verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_c16_frontend_card
    from tools import phase4_grain_gates as e09
    from tools import phase4_lives_gameover as c16
    from tools.live_session_provenance import (
        add_required_live_args,
        finish_run,
        inspect_state_before_load,
        retained_pristine_save_gaps,
        verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_c16_frontend_card.json"
C16_ARTIFACT = ROOT / "analysis/phase4_lives_gameover.json"
E09_ARTIFACT = ROOT / "analysis/phase4_grain_gates.json"

NATURAL_FRAMES = (0, c16.CONTINUE_PRE_FRAME, c16.CONTINUE_POST_FRAME,
                  c16.FINAL_FRAME)
REMOVED_FRAMES = (c16.CONTINUE_PRE_FRAME, c16.CONTINUE_POST_FRAME,
                  c16.FINAL_FRAME)
PROGRESS_SHA256 = "611fc682fd1235862b4656dd2a2920beb89ee79b1032ae18ce91a0b34a5c0418"
CARD_SHA256 = "63c08f0143e7b714309de900905f22944ae07f1da881ce9aa3a0237a5dacf517"
EXPECTED_FRAME_HASHES = {
    "post-game-over-title-before-Start":
        "30443b10664b96afec97590c88301068be51cc72a556226c2747268e4fcc2a93",
    "natural-stage-select":
        "7e8459b7fbac83d4a11846a8f7b723712eb4a49e1b717f12240e5362120d71f0",
    "Start-removed-title":
        "6ddda7cecbd2e6493e3531656741ef642e6a12e6ec6f007ef8021cde29ffcd3a",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _method_present(capabilities: dict[str, Any], method: str) -> bool:
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in capabilities.get("methods") or [])


def build_static_join() -> dict[str, Any]:
    c16_doc = json.loads(C16_ARTIFACT.read_text())
    e09_doc = json.loads(E09_ARTIFACT.read_text())
    instruction = c16_doc["static_census"]["instructions"] \
        ["continue_scene_config_lives_write"]
    serializer = e09_doc["static_census"]["card_serialization"]
    start = int(serializer["source_start"], 16)
    end = int(serializer["source_end_exclusive"], 16)
    if instruction != {
            "address": "0x80055550", "file_offset": "0x45D50",
            "instruction_word": "0xA02265A0"}:
        raise SystemExit("C16 scene-config lives writer drifted")
    if start != e09.PROGRESS_BLOCK or end - start != e09.PROGRESS_BLOCK_LENGTH:
        raise SystemExit("E14-owned native card serializer range drifted")
    if not (c16.LIVES < start or c16.LIVES >= end):
        raise SystemExit("lives unexpectedly entered the native serialized block")
    return {
        "sources": {
            "c16": {"path": C16_ARTIFACT.relative_to(ROOT).as_posix(),
                    "sha256": _sha256(C16_ARTIFACT)},
            "e14_interface": {
                "path": E09_ARTIFACT.relative_to(ROOT).as_posix(),
                "sha256": _sha256(E09_ARTIFACT),
                "owner": "E14 card serialization, reproduced by completed E09"},
        },
        "scene_config_lives_write": instruction,
        "card_serialization": serializer,
        "lives": {"address": f"0x{c16.LIVES:08X}", "width": "u8",
                  "inside_serialized_block": False},
        "classification": (
            "The exact title-restart lives byte is outside the bidirectional "
            "336-byte native card copy range; live card hashes decide whether "
            "this particular path performs any separate card write."),
    }


def _frame_capture(client: Any, directory: Path, label: str) -> dict[str, Any]:
    path = directory / f"{label}.png"
    captured = client.call("emulator.captureFrame", {"path": str(path.resolve())})
    hashed = client.call("emulator.hashFrame", {
        "path": str(path.resolve()), "hash": "sha256"})
    return {
        "label": label,
        "captured": captured.get("captured"),
        "width": captured.get("width"), "height": captured.get("height"),
        "emulator_frame": captured.get("frame"),
        "pixel_sha256": hashed.get("hash") or hashed.get("value"),
        "hash_method": hashed.get("hash_type") or hashed.get("algorithm") or "sha256",
        "transient_storage": "temporary directory; captured frame deleted",
    }


def _boundary(client: Any, card: Path, seed: Path, frame: int) -> dict[str, Any]:
    progress = c16._read_memory(
        client, e09.PROGRESS_BLOCK, e09.PROGRESS_BLOCK_LENGTH)
    card_bytes = card.read_bytes()
    seed_bytes = seed.read_bytes()
    return {
        "movie_frame": frame,
        "snapshot": c16._snapshot(client),
        "main_ram_sha256": _sha256_bytes(c16._read_main_ram(client)),
        "progress_block": {
            "start": f"0x{e09.PROGRESS_BLOCK:08X}",
            "length": e09.PROGRESS_BLOCK_LENGTH,
            "sha256": _sha256_bytes(progress),
        },
        "isolated_card_sha256": _sha256_bytes(card_bytes),
        "immutable_seed_sha256": _sha256_bytes(seed_bytes),
        "isolated_card_equals_seed": card_bytes == seed_bytes,
    }


def _run_branch(client: Any, movie: Path, frames: tuple[int, ...], *,
                card: Path, seed: Path, capture: dict[int, str],
                directory: Path) -> dict[str, Any]:
    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    client.call("movie.load", {"path": str(movie.resolve())})
    started = client.call("movie.startPlayback", {
        "start_frame": 0, "load_start_state": True})
    boundaries = []
    current = 0
    for frame in frames:
        if frame:
            client.call("movie.advanceToFrame", {
                "frame": frame, "max_frames": frame - current + 8}, timeout=900)
        client.call("debugger.pause", {})
        row = _boundary(client, card, seed, frame)
        if frame in capture:
            row["frame_capture"] = _frame_capture(
                client, directory, capture[frame])
        boundaries.append(row)
        current = frame
    status = client.call("movie.status", {})
    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    client.call("movie.clear", {})
    return {
        "started": {key: started.get(key) for key in
                    ("reproducible", "truncated", "frame_count")},
        "final_status": {key: status.get(key) for key in
                         ("reproducible", "truncated", "frame_count",
                          "playback_index", "playing")},
        "boundaries": boundaries,
    }


def _by_frame(branch: dict[str, Any], frame: int) -> dict[str, Any]:
    return next(row for row in branch.get("boundaries") or []
                if row.get("movie_frame") == frame)


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if document.get("campaign_state") != "active_partial":
        gaps.append("C16 frontend/card campaign state changed")
    static = document.get("static_join") or {}
    serializer = static.get("card_serialization") or {}
    if serializer.get("source_start") != "0x8009EC68" or \
            serializer.get("source_end_exclusive") != "0x8009EDB8" or \
            serializer.get("length") != 336 or \
            (static.get("lives") or {}).get("inside_serialized_block") is not False:
        gaps.append("C16/E14 static serializer join changed")

    live = document.get("live") or {}
    natural = live.get("natural_title_restart") or {}
    removed = live.get("last_start_removed") or {}
    for label, branch in (("natural", natural), ("removed", removed)):
        if (branch.get("started") or {}).get("reproducible") is not True or \
                (branch.get("final_status") or {}).get("truncated") is not False:
            gaps.append(f"{label} movie reproducibility changed")
    try:
        natural_pre = _by_frame(natural, c16.CONTINUE_PRE_FRAME)
        removed_pre = _by_frame(removed, c16.CONTINUE_PRE_FRAME)
        natural_post = _by_frame(natural, c16.CONTINUE_POST_FRAME)
        removed_post = _by_frame(removed, c16.CONTINUE_POST_FRAME)
        natural_final = _by_frame(natural, c16.FINAL_FRAME)
        removed_final = _by_frame(removed, c16.FINAL_FRAME)
    except StopIteration:
        return gaps + ["frontend/card replay lost a required movie boundary"]

    pre_keys = ("main_ram_sha256", "progress_block", "isolated_card_sha256")
    if any(natural_pre.get(key) != removed_pre.get(key) for key in pre_keys) or \
            natural_pre.get("snapshot") != removed_pre.get("snapshot"):
        gaps.append("natural/Start-removed branches differ before edited input")
    n_post = (natural_post.get("snapshot") or {}).get("typed") or {}
    r_post = (removed_post.get("snapshot") or {}).get("typed") or {}
    n_final = (natural_final.get("snapshot") or {}).get("typed") or {}
    r_final = (removed_final.get("snapshot") or {}).get("typed") or {}
    if (n_post.get("scene"), n_post.get("lives"),
            r_post.get("scene"), r_post.get("lives")) != (0, 5, 0, 0):
        gaps.append("post-game-over title-Start lives split changed")
    if (n_final.get("scene"), n_final.get("lives"),
            r_final.get("scene"), r_final.get("lives")) != (0, 5, 0, 0):
        gaps.append("title-restart/refusal final boundary changed")

    all_boundaries = (natural.get("boundaries") or []) + \
        (removed.get("boundaries") or [])
    progress_hashes = {(row.get("progress_block") or {}).get("sha256")
                       for row in all_boundaries}
    card_hashes = {row.get("isolated_card_sha256") for row in all_boundaries}
    seed_hashes = {row.get("immutable_seed_sha256") for row in all_boundaries}
    if progress_hashes != {PROGRESS_SHA256}:
        gaps.append("post-game-over progress-block boundary changed")
    if card_hashes != {CARD_SHA256} or seed_hashes != {CARD_SHA256} or \
            any(row.get("isolated_card_equals_seed") is not True
                for row in all_boundaries):
        gaps.append("post-game-over path changed the isolated card or seed")
    card = live.get("card_diff") or {}
    if card.get("changed_bytes") != 0 or card.get("size_before") != 131072 or \
            card.get("size_after") != 131072:
        gaps.append("post-game-over card diff changed")

    recipes = live.get("movie_recipes") or {}
    if (recipes.get("natural") or {}).get("changed_frames") != [] or \
            (recipes.get("last_start_removed") or {}).get("changed_frames") != \
            list(c16.CONTINUE_START_FRAMES):
        gaps.append("frontend movie single-variable edit changed")
    captures = {
        row["label"]: row.get("pixel_sha256") for row in (
            natural_pre.get("frame_capture") or {},
            natural_final.get("frame_capture") or {},
            removed_final.get("frame_capture") or {})
        if row.get("label")
    }
    if captures != EXPECTED_FRAME_HASHES:
        gaps.append("title/stage-select visual hash boundary changed")

    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned C16 frontend/card process was not stopped")
    if document.get("run_provenance"):
        gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_join()
    fixtures = c16.build_fixture_census()
    source_movie = json.loads(c16.MOVIE.read_text())
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.captureFrame", "emulator.hashFrame",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks C16 frontend/card methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, c16.SAVE, media_identity)
    repro = e09._verify_repro_config(args)
    card = Path(repro["isolated_card_path"])
    seed = Path(repro["seed_path"])
    card_before = card.read_bytes()

    with tempfile.TemporaryDirectory(prefix="abl-phase4-c16-frontend-") as temp_text:
        temp = Path(temp_text)
        natural_movie = temp / "natural.movie.json"
        removed_movie = temp / "last-start-removed.movie.json"
        natural_recipe = c16._write_variant(
            source_movie, natural_movie, start_state=c16.SAVE,
            anchor_label="<centrally-pinned-C16-save>")
        removed_recipe = c16._write_variant(
            source_movie, removed_movie, start_state=c16.SAVE,
            anchor_label="<centrally-pinned-C16-save>", edit="continue_removed")
        natural = _run_branch(
            client, natural_movie, NATURAL_FRAMES, card=card, seed=seed,
            capture={c16.CONTINUE_PRE_FRAME: "post-game-over-title-before-Start",
                     c16.FINAL_FRAME: "natural-stage-select"}, directory=temp)
        removed = _run_branch(
            client, removed_movie, REMOVED_FRAMES, card=card, seed=seed,
            capture={c16.FINAL_FRAME: "Start-removed-title"}, directory=temp)
        card_after = card.read_bytes()
        final_media = verified_media_identity(
            client, client.call("debugger.status", {}))

        document = {
            "_comment": (
                "Active C16 frontend/card evidence. The fourth Start is a "
                "post-game-over title restart, not proof of a Continue menu "
                "choice. It resets lives outside the native serialized block "
                "without changing the isolated card."),
            "generated": date.today().isoformat(),
            "schema": "abl-phase4-c16-frontend-card/1",
            "campaign_state": "active_partial",
            "static_join": static,
            "fixture_census": fixtures,
            "live": {
                "repro_config": repro,
                "movie_recipes": {"natural": natural_recipe,
                                  "last_start_removed": removed_recipe},
                "natural_title_restart": natural,
                "last_start_removed": removed,
                "card_diff": e09._card_diff(card_before, card_after),
            },
            "bounded_interpretation": {
                "observation": (
                    "At movie frame 3662 the transient frame is the title "
                    "screen. Natural Start frames 3663..3669 reach scene 0/lives "
                    "5 and the stage-select frame by 4006; removing only those "
                    "frames leaves scene 0/lives 0 on the same title frame."),
                "inference": (
                    "The exact 0x80055550 write is post-game-over title-restart "
                    "scene initialization. It is not evidence of a separately "
                    "presented Continue menu choice."),
                "causal_confirmation": (
                    "The branches are identical at frame 3662. Across both, the "
                    "336-byte progress block, fresh isolated card and immutable "
                    "seed remain byte-identical while only natural input writes "
                    "lives 0 to 5."),
                "card_boundary": (
                    "The E14-owned native serializer copies 0x8009EC68..0x8009EDB7. "
                    "Lives at 0x800A65A0 is outside it, and this restart performs "
                    "no host-card write. Explicit later native Save/Load choices "
                    "remain frontend/persistence work."),
                "forbidden_claim": (
                    "Do not rename the path Continue, infer a menu option, claim "
                    "no card interaction on other frontend paths, or close C16."),
            },
            "bounded_open_frontier": {
                "frontend": (
                    "Explicit native Save/Load, no-card/corrupt-card behavior and "
                    "any other title/menu choices remain open."),
                "deaths": (
                    "Scripted, special, boss, bonus and exceptional death classes "
                    "plus remaining stage breadth remain open."),
                "next_experiment": (
                    "Bind one existing boss/bonus or scripted death lead to its "
                    "exact producer and resident transition law."),
            },
            "run_provenance": {},
        }
        gaps = evidence_gaps(document)
        if gaps:
            diagnostic = Path("/tmp/abl-phase4-c16-frontend-failed.json")
            diagnostic.write_text(json.dumps(document, indent=1) + "\n")
            raise SystemExit(f"retained C16 frontend/card evidence failed: {gaps}")
        document["run_provenance"] = finish_run(
            args, generator="tools/phase4_c16_frontend_card.py",
            anchor={
                "type": "state-anchored post-game-over title restart on fresh isolated card",
                "save": c16.SAVE_REL,
                "fixture_sha256": {c16.SAVE_REL: fixtures["save"]["sha256"]},
                "state_inspections": [inspection],
                "media_identity": media_identity,
                "final_media_identity": final_media,
                "movie": fixtures["movie"],
                "card_fixture": {
                    "manifest": repro["manifest"],
                    "sha256": repro["seed_sha256"],
                    "size": repro["seed_size"],
                    "media_class": "operator_owned_memory_card"},
            },
            timing={
                "cpu_overclock_percent": 100, "cd_read_speedup": 1,
                "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
                "execution_mode": "CachedInterpreter",
                "movie_frames": {"pre_title_Start": c16.CONTINUE_PRE_FRAME,
                                 "post_title_Start": c16.CONTINUE_POST_FRAME,
                                 "final": c16.FINAL_FRAME},
            })
        cleanup_gaps = evidence_gaps(document)
        if cleanup_gaps:
            raise SystemExit(
                f"retained C16 frontend/card cleanup failed: {cleanup_gaps}")
        write_live_evidence(OUTPUT, document)
    print("[phase4-c16-frontend-card] retained title-restart/card boundary")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    parser.add_argument("--card-seed", type=Path, required=True,
                        help="centrally pinned replay memory-card seed")
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(
                args, generator="tools/phase4_c16_frontend_card.py",
                anchor={"type": "aborted before retained C16 frontend/card evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(f"owned C16 frontend/card cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
