#!/usr/bin/env python3
"""Phase-2 oracle builder: fixture audit + typed pristine stage snapshots.

Two artifacts (Game Solving Roadmap Phase 2):

  analysis/phase2_fixture_audit.json
      Every save state and input movie in the working tree, sha256-pinned and
      classified by the media it identifies: PRISTINE retail image, a MOD/derived
      image, or unreadable. Saves are inspected with emulator.getStateInfo
      (metadata only — nothing is loaded); movies carry their identity header.
      Non-pristine fixtures are NOT deleted — they are marked ineligible for
      oracle construction.

  analysis/phase2_stage_baseline.json
      Typed behavioral snapshots for every pristine stage/bonus/lifecycle anchor:
      scene id, player kinematics block, health/lives/grain/quota/berry/power,
      actor-record and kind-table digests — each captured TWICE (anchor frame and
      anchor+60 frames) so every field carries a stability flag. Stable fields are
      the differential-comparison mask for future reconstructed/diagnostic builds;
      volatile fields are excluded from equality oracles by construction.

Requires an isolated debugger instance with the pristine disc:
    launch_debugger_instance.sh start --config-dir /tmp/duckstation-debugger-phase2 \
        --port 23471 --token debugger-1000 --disc "<pristine>.cue"

Usage: python3 tools/phase2_oracle.py [--port 23471] [--skip-audit] [--skip-baseline]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))

from live_session_provenance import (inspect_state_before_load,
                                     verified_media_identity)

PRISTINE_MEDIA_SUFFIXES = (
    "Disney-Pixar A Bug's Life (v1.0).cue",
    "Disney-Pixar A Bug's Life (v1.0).bin",
)

# Typed snapshot schema: (name, address, width). Widths: u8/s16/s32/u32.
SNAPSHOT_FIELDS = [
    ("scene_id", 0x80082504, "u32"),
    ("player_x", 0x800A6500, "s32"),
    ("player_y", 0x800A6504, "s32"),
    ("player_z", 0x800A6508, "s32"),
    ("player_floor", 0x800A6548, "s32"),
    ("player_grounded", 0x800A6582, "u8"),
    ("health", 0x800A7E2A, "s16"),
    ("lives", 0x800A65A0, "u8"),
    ("grain", 0x800A65A1, "u8"),
    ("enemy_quota", 0x800A658E, "u8"),
    ("equipped_berry", 0x800A6597, "u8"),
    ("power_word", 0x800A6590, "u8"),
]
RECORDS_BASE, RECORD_STRIDE, RECORD_CAP = 0x8009FE04, 0x84, 160
KIND_TABLE, KIND_EXTENT = 0x80096B98, 50
VOLATILITY_FRAMES = 60

# Pristine anchors: (label, save, role). Identity anchors cover Training + all 15
# stages; lifecycle anchors cover completion/results and progression states; bonus
# anchors are the bonus-stage movie start states.
ANCHORS = [
    ("training", "phase3_pristine_training_gameplay_i5.sav", "identity"),
    ("stage01_anthill", "level01.sav", "identity"),
    ("stage02_tunnels", "level02.sav", "identity"),
    ("stage03_council_chamber", "level03.sav", "identity"),
    ("stage04_cliffside_canyon", "level04.sav", "identity"),
    ("stage05_riverbed_run", "level05.sav", "identity"),
    ("stage06_birdnest", "level_06.sav", "identity"),
    ("stage07_city_entrance", "level_07.sav", "identity"),
    ("stage08_city_square", "level_08.sav", "identity"),
    ("stage09_bug_bar", "level_09.sav", "identity"),
    ("stage10_clover_forest", "level_10.sav", "identity"),
    ("stage11_the_tree", "level_11.sav", "identity"),
    ("stage12_battle_arena", "level_12.sav", "identity"),
    ("stage13_anthill_two", "level_13.sav", "identity"),
    ("stage14_riverbed_flight", "level_14.sav", "identity"),
    ("stage15_canyon_showdown", "level_15.sav", "identity"),
    ("bonus1_spiders", "movies/Bonus_Level_01.movie.sav", "identity_bonus"),
    ("bonus2_mushrooms", "movies/Bonus_Level_02.movie.sav", "identity_bonus"),
    ("bonus3_grasshoppers", "movies/Bonus_Level_03.movie.sav", "identity_bonus"),
    ("training_completion", "training_all_stuff_collected_ending.sav", "lifecycle_completion"),
    ("stage01_completion", "level01_end_of_stage.sav", "lifecycle_completion"),
    ("stage02_completion", "LEVEL02_ENDING.sav", "lifecycle_completion"),
    ("stage04_completion", "LEVEL04_ENDING.sav", "lifecycle_completion"),
    ("stage05_completion", "LEVEL05_ENDING.sav", "lifecycle_completion"),
    ("stage07_completion", "LEVEL07_ENDING.sav", "lifecycle_completion"),
    ("stage12_completion", "LEVEL12_ENDING.sav", "lifecycle_completion"),
    ("stage14_completion", "LEVEL14_ENDING.sav", "lifecycle_completion"),
    ("stage08_progress_dim", "LEVEL08_DIM.sav", "objective_progress"),
    ("stage08_progress_manny", "LEVEL08_MANNY.sav", "objective_progress"),
    ("stage08_progress_rosie", "LEVEL08_ROSIE.sav", "objective_progress"),
    ("stage08_progress_tuckroll", "LEVEL08_TUCKROLL.sav", "objective_progress"),
    ("stage10_progress_1", "LEVEL10_1.sav", "objective_progress"),
    ("stage10_progress_2", "LEVEL10_2.sav", "objective_progress"),
    ("stage10_progress_3", "LEVEL10_3.sav", "objective_progress"),
    ("stage10_progress_4", "LEVEL10_4.sav", "objective_progress"),
    ("stage10_progress_5", "LEVEL10_5.sav", "objective_progress"),
    ("stage11_progress_1", "LEVEL11_1.sav", "objective_progress"),
    ("stage11_progress_2", "LEVEL11_2.sav", "objective_progress"),
    ("stage11_progress_3", "LEVEL11_3.sav", "objective_progress"),
    ("stage11_progress_4", "LEVEL11_4.sav", "objective_progress"),
    ("stage11_progress_5", "LEVEL11_5.sav", "objective_progress"),
    ("stage11_progress_dot", "LEVEL11_DOT.sav", "objective_progress"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def classify_media(media_path: str | None) -> str:
    if not media_path:
        return "unknown"
    return "pristine" if media_path.endswith(PRISTINE_MEDIA_SUFFIXES) else "non_pristine"


def audit_fixtures(c) -> dict:
    saves = {}
    for p in sorted(list(ROOT.glob("*.sav")) + list((ROOT / "movies").rglob("*.sav"))):
        rel = str(p.relative_to(ROOT))
        entry = {"sha256": sha256_file(p), "size": p.stat().st_size}
        try:
            info = c.call("emulator.getStateInfo", {"path": str(p)})
            entry["media_path"] = info.get("media_path")
            entry["media_class"] = classify_media(info.get("media_path"))
            for k in ("game_serial", "game_title"):
                if info.get(k):
                    entry[k] = info[k]
        except Exception as exc:
            entry["media_class"] = "unreadable"
            entry["error"] = f"{type(exc).__name__}: {exc}"
        saves[rel] = entry
    movies = {}
    for p in sorted(list(ROOT.glob("*.movie*.json")) + list((ROOT / "movies").rglob("*.json"))):
        rel = str(p.relative_to(ROOT))
        entry = {"sha256": sha256_file(p), "size": p.stat().st_size}
        try:
            doc = json.loads(p.read_text())
            entry["game_serial"] = doc.get("game_serial")
            entry["format_version"] = doc.get("version")
            entry["frames"] = len(doc.get("frames", [])) or None
            entry["media_class"] = ("pristine_serial" if doc.get("game_serial") == "SCUS-94288"
                                    else "unknown_serial")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            entry["media_class"] = "unreadable"
            entry["error"] = str(exc)[:120]
        movies[rel] = entry
    counts = {}
    for coll in (saves, movies):
        for e in coll.values():
            counts[e["media_class"]] = counts.get(e["media_class"], 0) + 1
    return {"saves": saves, "movies": movies, "class_counts": counts,
            "note": "movie identity headers carry serial but NOT the disc image hash; "
                    "a pristine-serial movie recorded on a MOD disc is indistinguishable "
                    "by header alone — cold-boot oracle movies must therefore be replayed "
                    "against the pristine image to be accepted (oracle rule)."}


def snapshot(c, rd) -> dict:
    snap = {}
    for name, addr, width in SNAPSHOT_FIELDS:
        raw = rd(addr, {"u8": 1, "s16": 2, "u32": 4, "s32": 4}[width])
        fmt = {"u8": "<B", "s16": "<h", "u32": "<I", "s32": "<i"}[width]
        snap[name] = struct.unpack(fmt, raw)[0]
    recs = rd(RECORDS_BASE, RECORD_STRIDE * RECORD_CAP)
    n = 0
    while n < RECORD_CAP:
        rid, x, y, z = struct.unpack_from("<Iiii", recs, n * RECORD_STRIDE)
        if (rid == 0 and x == 0 and y == 0 and z == 0) or rid > 0x2000 or abs(x) > 0x400000:
            break
        n += 1
    snap["actor_record_count"] = n
    snap["actor_records_sha256"] = hashlib.sha256(recs[:n * RECORD_STRIDE]).hexdigest()
    tab = rd(KIND_TABLE, KIND_EXTENT * 4)
    blob = bytearray(tab)
    for k in range(KIND_EXTENT):
        (p,) = struct.unpack_from("<I", tab, k * 4)
        blob += rd(p, 0xC)
    snap["kind_table_sha256"] = hashlib.sha256(bytes(blob)).hexdigest()
    st = c.call("debugger.status", {})
    snap["frame"] = st.get("frame_number", st.get("frame"))
    return snap


def build_baseline(c, rd, media_identity) -> dict:
    stages = {}
    for label, sav, role in ANCHORS:
        path = ROOT / sav
        if not path.exists():
            stages[label] = {"role": role, "error": f"anchor missing: {sav}"}
            continue
        inspect_state_before_load(c, path, media_identity)
        r = c.call("emulator.loadState", {"path": str(path), "pause_after_load": True})
        if not r.get("loaded") or r.get("game_serial") != "SCUS-94288":
            stages[label] = {"role": role, "save": sav, "error": f"loadState: {r}"}
            continue
        base = snapshot(c, rd)
        c.call("emulator.advanceFrames", {"frames": VOLATILITY_FRAMES})
        c.call("debugger.pause", {})
        later = snapshot(c, rd)
        stability = {k: base[k] == later[k] for k in base}
        stages[label] = {
            "role": role, "save": sav, "save_sha256": sha256_file(path),
            "anchor": base, "anchor_plus_frames": later,
            "volatility_frames": VOLATILITY_FRAMES,
            "stable_fields": sorted(k for k, s in stability.items() if s),
            "volatile_fields": sorted(k for k, s in stability.items() if not s),
        }
        print(f"[oracle] {label} ({role}): scene={base['scene_id']} "
              f"actors={base['actor_record_count']} "
              f"stable={len(stages[label]['stable_fields'])}/{len(stability)}")
    return stages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23471)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--skip-audit", action="store_true")
    ap.add_argument("--skip-baseline", action="store_true")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(60)

    def rd(addr: int, n: int) -> bytes:
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % addr, "length": n})["hex"])

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)

    if not args.skip_audit:
        audit = {
            "_comment": "Phase-2 fixture audit: every save/movie sha256-pinned and "
                        "classified by identified media. Non-pristine fixtures are "
                        "retained but ineligible for oracle construction. Regenerate: "
                        "tools/phase2_oracle.py.",
            "generated": date.today().isoformat(),
            **audit_fixtures(c),
        }
        out = ROOT / "analysis" / "phase2_fixture_audit.json"
        out.write_text(json.dumps(audit, indent=1) + "\n")
        print(f"[oracle] wrote {out}: {audit['class_counts']}")

    if not args.skip_baseline:
        stages = build_baseline(c, rd, media_identity)
        doc = {
            "_comment": "Phase-2 typed pristine stage snapshots + differential masks. "
                        "stable_fields = safe equality oracle for future builds at the "
                        "same anchor; volatile_fields change within the volatility "
                        "window and are excluded from equality comparison by "
                        "construction. Regenerate: tools/phase2_oracle.py.",
            "generated": date.today().isoformat(),
            "media": {"serial": status.get("game_serial"), "title": status.get("game_title")},
            "snapshot_schema": [
                {"name": n, "address": f"0x{a:08x}", "width": w} for n, a, w in SNAPSHOT_FIELDS
            ] + [
                {"name": "actor_record_count / actor_records_sha256",
                 "address": f"0x{RECORDS_BASE:08x}", "width": f"records*{RECORD_STRIDE:#x}"},
                {"name": "kind_table_sha256", "address": f"0x{KIND_TABLE:08x}",
                 "width": f"{KIND_EXTENT} ptrs + descriptors"},
            ],
            "stages": stages,
        }
        out = ROOT / "analysis" / "phase2_stage_baseline.json"
        out.write_text(json.dumps(doc, indent=1) + "\n")
        ok = sum(1 for s in stages.values() if "error" not in s)
        print(f"[oracle] wrote {out}: {ok}/{len(stages)} anchors snapshotted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
