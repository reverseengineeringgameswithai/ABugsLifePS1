#!/usr/bin/env python3
"""Phase-3 gate bullet 2: init / reset / overlay-lifetime for every owned entry.

The gate wants, for every owned state: owner, width, domain, readers, writers,
INITIALIZATION, RESET, and OVERLAY LIFETIME — or an explicit blocker. Owner/width/
domain are in config/semantic_state.yaml; readers/writers came from P1
(phase3_xrefs.py). This fills the last three, deriving what is derivable and
measuring the rest live.

Each of the 58 addressed entries is classified:

  overlay_lifetime   from its address alone:
                       resident_rom  (< 0x80090000: EXE code/const table)
                       resident_ram  (game RAM/BSS)
                       overlay       (0x800B39A4..0x800BE5E8: swapped per level)

  init / reset       for RAM-space state, MEASURED across a real scene transition
                     (the method proven in phase3_transition_reset.py — poll-only
                     over a from-boot movie, sampled before the scene-id flip vs
                     after world-ready):
                       reset_to_zero   zeroed by the load
                       reloaded        changed, non-zero (fresh level data)
                       carried_over    survived unchanged (session-owned)
                       unchanged_zero  was zero, stayed zero (no evidence)
                     for ROM tables/const: init = "load_time (image)", reset =
                     "never (immutable in ROM)" — DERIVED, not a measurement, and
                     labelled as such. An honest derivation beats a fake probe.

Usage: python3 tools/phase3_semantic_lifetime.py [--port 23473]
Output: analysis/phase3_semantic_lifetime.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from datetime import date
from pathlib import Path

import yaml

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from build_identity import verify_pristine_media_path  # noqa: E402

SCENE_ID = 0x80082504
OVERLAY_LO, OVERLAY_HI = 0x800B39A4, 0x800BE5E8
# The loaded resident EXE image: header stripped, loaded at t_addr 0x80010000, file
# 471040-0x800 = 0x72800 bytes => spans [0x80010000, 0x80082800). EVERYTHING at or
# above 0x80082800 is BSS/heap RAM — it is not in the on-disc image, so it CANNOT be
# ROM, regardless of what the static writer scan found.
EXE_LOAD_LO, EXE_LOAD_HI = 0x80010000, 0x80082800
# ROM vs RAM is TWO tests, not one, and getting this wrong both ways has bitten us:
#   (1) The old `< 0x80090000 => ROM` rule mislabeled BSS runtime state (scene_id
#       0x80082504) as ROM. (2) The over-correction — "ROM iff no static writers" —
#       mislabeled pointer-written BSS above the image (actor table, camera, mesh
#       buffer) as ROM, because the static scan CANNOT see pointer-based writes.
# Correct: an address ABOVE the loaded image is RAM (BSS/heap), full stop. WITHIN the
# loaded image, static writers distinguish self-modified data (RAM) from a const
# table (ROM). Never-written + above the image is still RAM (writers were missed).
WIDTHS = {"u8": ("<B", 1), "s8": ("<b", 1), "u16": ("<H", 2), "s16": ("<h", 2),
          "u32": ("<I", 4), "s32": ("<i", 4)}


def fixture_pin(*rels):
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def verified_media_identity(client, status: dict) -> dict:
    before = client.call("emulator.getMediaInfo", {})
    if not before.get("has_media") or not before.get("path"):
        raise SystemExit(f"mounted-media guard: no media is mounted: {before}")
    if status.get("game_serial") != "SCUS-94288" or \
            before.get("game_serial") != status.get("game_serial"):
        raise SystemExit(
            f"mounted-media guard: debugger/media serial mismatch: {status} / {before}")
    verification = verify_pristine_media_path(before["path"])
    after = client.call("emulator.getMediaInfo", {})
    stable_keys = ("has_media", "path", "game_serial", "subimage_count", "subimage_index")
    if any(before.get(key) != after.get(key) for key in stable_keys):
        raise SystemExit(
            f"mounted-media guard: media changed while hashing: {before} -> {after}")
    return {
        "game_serial": status.get("game_serial"),
        "game_title": status.get("game_title"),
        "game_path": before["path"],
        "has_media": True,
        "serials_agree": True,
        "rpc_before_hash": before,
        "rpc_after_hash": after,
        "hash_verification": verification,
    }


def overlay_lifetime(addr: int, has_writers: bool) -> str:
    if OVERLAY_LO <= addr <= OVERLAY_HI:
        return "overlay"
    if addr >= EXE_LOAD_HI:
        return "resident_ram"          # BSS/heap — above the loaded image, never ROM
    if has_writers:
        return "resident_ram"          # in-image but written at runtime => mutable
    return "resident_rom"              # in-image, never written => const table in ROM


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(ap)
    ap.add_argument("--stage", default="stage01_anthill")
    args = ap.parse_args()

    sem = yaml.safe_load((ROOT / "config" / "semantic_state.yaml").read_text())
    entries = [e for e in sem["entries"] if isinstance(e.get("address"), int)]

    xr = json.loads((ROOT / "analysis" / "phase3_xrefs.json").read_text())["entries"]
    def writers_of(e):
        return xr.get(e["id"], {}).get("writer_count", 0)

    def declared_writers_of(e):
        return len(e.get("writers") or [])

    for e in entries:
        # The pristine static scan cannot see MOD cave writers. Registry-declared
        # writers are still writers; ignoring them falsely turns the private
        # blackberry runtime bytes into immutable retail-image constants.
        e["_declared_writers"] = declared_writers_of(e)
        e["_ol"] = overlay_lifetime(
            e["address"], writers_of(e) > 0 or e["_declared_writers"] > 0)

    # measure live: a resident_ram SCALAR we can read as a single value
    ram = [e for e in entries
           if e["_ol"] == "resident_ram" and e.get("width") in WIDTHS
           and e.get("namespace") != "mod_private"]
    derived = [e for e in entries if e not in ram]

    from duckstation_debug_client import DebuggerClient
    oracle = json.loads(
        (ROOT / "analysis" / "phase2_completion_oracle.json").read_text())
    st = oracle["stages"][args.stage]
    movie = st["movie"]

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(900)
    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", status
    media_identity = verified_media_identity(c, status)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def read_val(e):
        fmt, n = WIDTHS[e["width"]]
        return struct.unpack(fmt, rd(e["address"], n))[0]

    def scene():
        return struct.unpack("<I", rd(SCENE_ID, 4))[0]

    def snapshot():
        return {e["id"]: read_val(e) for e in ram}

    def actors_live():
        buf = rd(0x8009FE04, 40 * 0x84)
        return any(struct.unpack_from("<I", buf, i * 0x84)[0] for i in range(40))

    # replay poll-only; catch the scene flip; sample before it vs after world-ready
    for m in ("movie.stopPlayback", "movie.clear"):
        try:
            c.call(m, {})
        except Exception:
            pass
    r = c.call("movie.load", {"path": str(ROOT / movie)})
    pb = c.call("movie.startPlayback", {"load_start_state": True})
    assert pb.get("playing") and pb.get("reproducible"), pb
    total = r["frame_count"]

    tl = st["scene_timeline"]
    in_stage = [w for w in tl if w["scene"] == st["target_scene"]]
    pre = [w for w in tl if w["last"] < in_stage[0]["first"]]
    STEP = 30
    f = max(0, pre[-1]["last"] - 300)
    c.call("movie.advanceToFrame", {"frame": f, "max_frames": total + 700}, timeout=900)
    before, before_scene, before_frame = snapshot(), scene(), f
    # walk to the flip into the stage
    while f < total - 300:
        f += STEP
        c.call("movie.advanceToFrame", {"frame": f, "max_frames": total + 700}, timeout=900)
        if scene() == st["target_scene"]:
            break
        before, before_scene, before_frame = snapshot(), scene(), f
    # advance to world-ready
    while f < total - 120 and not actors_live():
        f += STEP
        c.call("movie.advanceToFrame", {"frame": f, "max_frames": total + 700}, timeout=900)
    c.call("movie.advanceToFrame", {"frame": min(f + 120, total),
                                    "max_frames": total + 700}, timeout=900)
    after, after_scene = snapshot(), scene()
    for m in ("movie.stopPlayback", "movie.clear"):
        try:
            c.call(m, {})
        except Exception:
            pass
    assert before_scene != after_scene, (before_scene, after_scene)

    # A single transition CANNOT distinguish "reset to zero" from "already zero,
    # irrelevant here" — this movie starts fresh, so grain/health/etc read 0->0.
    # The all-16-stage transition sweep ALREADY classified the record-backed player
    # fields (session-owned survive the exit). Cross-reference it rather than let
    # one sample mislabel a known session field as "no evidence".
    tr = json.loads((ROOT / "analysis" / "phase3_transition_reset.json").read_text())
    session_owned = set(tr["laws"]["session_owned_everywhere"])   # record field names
    # map registry ids -> the record field name the sweep used
    SESSION_IDS = {
        "original.player_health_true": "health_true",
        "original.player_lives": "lives",
        "original.grain_count": "grain_count",
        "original.enemy_permanence_quota": "enemy_permanence_quota",
    }

    out = {}
    for e in ram:
        b, a = before[e["id"]], after[e["id"]]
        verdict = ("carried_over" if b == a and b != 0 else
                   "unchanged_zero" if b == a else
                   "reset_to_zero" if a == 0 else "reloaded")
        # A single transition CANNOT interpret a session field: depending on exactly
        # which frame the pre-flip snapshot lands on, lives/health/grain read 9->9 or
        # 0->N or 0->0 — none of which is a reliable reset verdict. The 16-stage
        # transition sweep IS authoritative for these, so defer to it unconditionally
        # (not only for the 0->0 case), and record the noisy single sample honestly.
        fld = SESSION_IDS.get(e["id"])
        if fld and fld in session_owned:
            verdict = "carried_over"
            corroborated = ("session-owned per the 16-stage transition sweep "
                            "(analysis/phase3_transition_reset.json), which is "
                            f"authoritative; this single-transition sample read {b}->"
                            f"{a}, which one transition cannot interpret")
        else:
            corroborated = None
        entry = {
            "address": f"0x{e['address']:08X}", "width": e["width"],
            "overlay_lifetime": "resident_ram",
            "static_writers": writers_of(e),
            "declared_writers": e["_declared_writers"],
            "init": ("unknown" if verdict == "unchanged_zero"
                     else "zeroed_at_load" if verdict == "reset_to_zero"
                     else "loaded_from_level_data" if verdict == "reloaded"
                     else "preserved_across_load"),
            "reset": verdict,
            "before": b, "after": a, "measured": True,
            **({"corroborated_by": corroborated} if corroborated else {}),
        }
        if verdict == "unchanged_zero":
            entry["blocker"] = {
                "kind": "insufficient_transition_evidence",
                "observation": f"single transition observed {b}->{a} (0->0)",
                "why": "0->0 proves neither initialization nor reset behavior",
                "next": "establish a nonzero precondition, trigger the relevant load/reset, "
                        "and observe whether the owner clears, preserves, or reloads it",
            }
        out[e["id"]] = entry
    for e in derived:
        ol = e["_ol"]
        nw = writers_of(e)
        declared = e["_declared_writers"]
        addr = e["address"]
        above_image = addr >= EXE_LOAD_HI
        if e.get("namespace") == "mod_private":
            # These bytes live inside the resident image range but are mutable MOD
            # state. Their cold-boot value is derived from the hash-pinned full MOD
            # image; pristine live sampling cannot establish their scene-reset law.
            patched = ROOT / "build" / "SCUS_942.88.patched"
            hook_doc = json.loads(
                (ROOT / "analysis" / "phase3_hook_contracts.json").read_text())
            expected = hook_doc["patched_image_pin"]["expected_sha256"]
            actual = hashlib.sha256(patched.read_bytes()).hexdigest() if patched.exists() else None
            image_verified = actual == expected
            fmt, _width = WIDTHS[e["width"]]
            off = addr - EXE_LOAD_LO + 0x800
            initial = struct.unpack_from(fmt, patched.read_bytes(), off)[0] \
                if image_verified else None
            out[e["id"]] = {
                "address": f"0x{addr:08X}", "width": e["width"],
                "overlay_lifetime": "resident_ram",
                "static_writers": nw,
                "declared_writers": declared,
                "above_loaded_image": above_image,
                "init": ("load_time_zero_from_pinned_MOD_image"
                         if initial == 0 else "unknown"),
                "reset": "unknown",
                "initial_value_in_pinned_MOD_image": initial,
                "patched_image_sha256": actual,
                "patched_image_matches_pin": image_verified,
                "measured": False,
                "derivation": "MOD-private resident RAM: registry-declared MOD cave "
                              "writers make it mutable even though the pristine static "
                              "xref scan sees zero writers; cold-boot byte derived from "
                              "the pinned full MOD image",
                "blocker": {
                    "kind": "mod_private_reset_unmeasured",
                    "observation": "pristine-media transition probes cannot exercise "
                                   "MOD-private writers",
                    "why": "scene-transition reset/retention has not been measured on "
                           "the pinned MOD build",
                    "next": "cold-boot the pinned MOD image, drive a scene transition, "
                            "and trace the declared owner writers",
                },
            }
            continue
        # a RAM entry the static scan found NO writers for is pointer-written (the
        # scan cannot resolve base+offset stores); say so instead of implying writers
        ram_writer_note = (f"{nw} static writers" if nw else
                           "written via pointer (base+offset) — 0 static writers "
                           "because the xref scan cannot resolve pointer-based stores; "
                           "it is RAM by location (above the 0x80082800 image end)")
        out[e["id"]] = {
            "address": f"0x{addr:08X}", "width": e.get("width"),
            "overlay_lifetime": ol,
            "static_writers": nw,
            "declared_writers": declared,
            "above_loaded_image": above_image,
            "init": ("load_time (const in the EXE/ROM image)" if ol == "resident_rom"
                     else "overlay_load (swapped in with its level)" if ol == "overlay"
                     else "runtime (BSS zero at load, then written by the code)"),
            "reset": ("never (immutable const in ROM)" if ol == "resident_rom"
                      else "on_overlay_swap" if ol == "overlay"
                      else f"runtime (mutable BSS/heap RAM, {ram_writer_note}) — "
                           "non-scalar/table, so not probed as a single value; "
                           "per-record reset is in phase3_transition_reset.json"),
            "measured": False,
            "derivation": ("EXE/const table with NO static writers, WITHIN the loaded "
                           "image — value lives in the image, not written at runtime"
                           if ol == "resident_rom"
                           else "overlay-resident — lifetime is its overlay's "
                           "load/unload" if ol == "overlay" else
                           f"mutable BSS/heap RAM ({ram_writer_note}); non-scalar or a "
                           "table — measured per-record, not as one value"),
        }

    from collections import Counter
    ol_counts = Counter(v["overlay_lifetime"] for v in out.values())
    reset_counts = Counter(v["reset"] for v in out.values())
    run_provenance = finish_run(
        args, generator="tools/phase3_semantic_lifetime.py",
        anchor={"movie": movie, "fixture_sha256": fixture_pin(movie),
                "media_identity": media_identity},
        timing={"before_frame": before_frame,
                "after_frame": min(f + 120, total),
                "scene_transition": [before_scene, after_scene],
                "poll_step_frames": STEP},
    )
    doc = {
        "_comment": "Phase-3 init/reset/overlay-lifetime for every owned entry. "
                    "RAM-scalar state is MEASURED across a real scene transition "
                    "(poll-only, world-ready aware); ROM tables and overlay entries "
                    "are DERIVED from their address and labelled measured:false — an "
                    "honest derivation beats a fake probe. Regenerate: "
                    "tools/phase3_semantic_lifetime.py",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media_identity_before_playback": media_identity,
        "fixture_sha256": fixture_pin(movie, "build/SCUS_942.88.patched"),
        "playback_provenance": {
            "oracle_stage": args.stage,
            "movie": movie,
            "movie_load": r,
            "movie_start": pb,
            "target_scene": st["target_scene"],
            "timeline_source": "analysis/phase2_completion_oracle.json",
        },
        "stage": args.stage,
        "transition": {"scene": [before_scene, after_scene],
                       "frames": [before_frame, min(f + 120, total)]},
        "entries_total": len(out),
        "measured_live": len(ram),
        "derived": len(derived),
        "overlay_lifetime_counts": dict(ol_counts),
        "reset_counts": dict(reset_counts),
        "entries": out,
    }
    path = ROOT / "analysis" / "phase3_semantic_lifetime.json"
    write_live_evidence(path, doc)
    print(f"[lifetime] {len(out)} entries: {len(ram)} measured live, "
          f"{len(derived)} derived")
    print(f"[lifetime] overlay lifetime: {dict(ol_counts)}")
    print(f"[lifetime] reset: {dict(reset_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
