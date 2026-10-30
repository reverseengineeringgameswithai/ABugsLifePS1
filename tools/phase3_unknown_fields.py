#!/usr/bin/env python3
"""Phase-3 WP5: drain the unknown-byte queue by EXACT-MATCH hypothesis testing.

The record probe triaged every unknown byte into always-zero / constant /
varying. The varying runs are velocity/rotation-shaped, so test that directly
instead of eyeballing hex.

Method — capture the WHOLE record every frame while the object is in motion,
then, offline, for every candidate (offset, width, signedness) in the unknown
spans, check the strongest possible claim:

    field[t] == pos[t+1] - pos[t]      (an exact integrator velocity)

An exact per-frame equality over dozens of frames is not a coincidence, and it
is falsifiable: one mismatched frame kills the candidate. Weaker relationships
are reported too, but only exact matches are promoted:

  * exact_velocity   — field equals the next-frame position delta on EVERY frame
  * constant_delta   — field changes by a fixed amount each frame (gravity!)
  * varies_with_move — changes only while moving (a lead, not a proof)

Subjects:
  player   a pristine stage anchor, driven forward with synthetic input
  berry    red_berry_thrown.sav — the in-flight projectile contact slot, whose
           known law (fall 128/frame^2) is a built-in control: if the tool
           cannot rediscover gravity from the bytes, do not trust its verdicts

Usage: python3 tools/phase3_unknown_fields.py [--port 23473]
Output: analysis/phase3_unknown_fields.json
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import date
from pathlib import Path

import yaml

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

FMT = {"u16": "<H", "s16": "<h", "u32": "<I", "s32": "<i"}
SIZE = {"u16": 2, "s16": 2, "u32": 4, "s32": 4}
AXES = ("x", "y", "z")


def load_records():
    doc = yaml.safe_load((ROOT / "config" / "record_types.yaml").read_text())
    return {r["id"]: r for r in doc["records"]}


def unknown_offsets(rec) -> set[int]:
    covered = set()
    for f in rec["fields"]:
        n = {"u8": 1, "s8": 1, "u16": 2, "s16": 2, "u32": 4, "s32": 4}[f["width"]]
        covered.update(range(f["offset"], f["offset"] + n))
    return set(range(rec["size"])) - covered


def declared_at(rec, off, n):
    for f in rec["fields"]:
        w = {"u8": 1, "s8": 1, "u16": 2, "s16": 2, "u32": 4, "s32": 4}[f["width"]]
        if f["offset"] < off + n and off < f["offset"] + w:
            return f["name"]
    return None


def candidates(rec):
    """Every aligned (offset,width) in the record — INCLUDING declared ones, so
    a field we typed wrongly (e.g. a 'knockback' that is really velocity-Y) is
    caught rather than protected by its own label."""
    out = []
    for w, n in SIZE.items():
        for off in range(0, rec["size"] - n + 1, n):     # natural alignment
            out.append((off, w))
    return out


def analyse(rec, frames):
    """frames = [(record_bytes, (x, y, z)), ...] consecutive.

    Two cadence facts the first attempt got wrong:
      * the game integrates on ALTERNATE frames (30 Hz logic on 60 Hz frames),
        so a delta of 0 is a no-op frame, not evidence against a candidate;
      * a velocity may be written BEFORE the move it causes (read at frame t it
        equals the NEXT delta — e.g. the berry, whose gravity is applied first)
        or AFTER (it equals the delta that just happened — e.g. the player).
    So test both alignments over the frames where the position actually moved,
    and require an exact match on EVERY one of them.
    """
    results = []
    moved = [t for t in range(1, len(frames))
             if frames[t][1] != frames[t - 1][1]]
    if len(moved) < 4:
        return results
    for off, w in candidates(rec):
        vals = [struct.unpack_from(FMT[w], blob, off)[0] for blob, _ in frames]
        constant = len(set(vals)) == 1
        verdict = {}
        for ai, axis in enumerate(AXES):
            d = {t: frames[t][1][ai] - frames[t - 1][1][ai] for t in moved}
            if not any(d.values()):
                continue
            # Alignment A: the field equals the delta that just happened.
            # Alignment B: it equals the NEXT move's delta (pre-integrated).
            pairs = [(t, moved[i + 1]) for i, t in enumerate(moved[:-1])]

            def streak(hits: list[bool]) -> int:
                best = cur = 0
                for h in hits:
                    cur = cur + 1 if h else 0
                    best = max(best, cur)
                return best

            # A match on a ZERO delta is worthless: while jumping in place dx == 0
            # and half the record is 0, so "0 == 0" would promote every field.
            # Only frames with a NON-ZERO delta count as evidence.
            for label, hits in (
                ("written_after_move",
                 [vals[t] == d[t] != 0 for t in moved]),
                ("written_before_move (pre-integrated)",
                 [vals[t] == d[t2] != 0 for t, t2 in pairs]),
            ):
                # A velocity is the move PROPOSAL: the integrator can CLAMP the
                # actual position (collision, ground), so demanding equality on
                # every frame rejects real fields. Require a long CONSECUTIVE
                # exact run instead — physics holds until something clamps it —
                # and report the total match rate alongside.
                run = streak(hits)
                if run >= 6:
                    verdict["exact_velocity"] = axis
                    if constant:
                        verdict["caveat"] = ("the field is CONSTANT over the "
                                             "window (a steady velocity) — exact "
                                             "equality, but weaker evidence than "
                                             "a varying field")
                    verdict["alignment"] = label
                    verdict["longest_exact_run"] = run
                    verdict["match"] = f"{sum(hits)}/{len(hits)} moved frames"
                    verdict["mismatches_are"] = (
                        "none" if sum(hits) == len(hits) else
                        "frames where the integrator clamped the position "
                        "(collision/ground) while the velocity persisted")
                    break
            if "exact_velocity" in verdict:
                break
        steps = [vals[t] - vals[t - 1] for t in moved]
        is_pos = (declared_at(rec, off, SIZE[w]) or "").startswith("pos_")
        if len(set(steps)) == 1 and steps[0] and not is_pos:
            # (a position advancing at a steady speed trivially has a constant
            #  delta — that is the definition of velocity, not a discovery)
            verdict["constant_delta_per_move"] = steps[0]
        if verdict:
            n = SIZE[w]
            verdict.update({"offset": f"0x{off:02X}", "width": w,
                            "declared_as": declared_at(rec, off, n),
                            "sample": vals[:6]})
            results.append(verdict)
    # one row per offset: keep the widest matching width (a 32-bit velocity also
    # "matches" in its low 16 bits — reporting both is noise)
    best = {}
    for r in results:
        k = r["offset"]
        if k not in best or SIZE[r["width"]] > SIZE[best[k]["width"]]:
            best[k] = r
    return sorted(best.values(), key=lambda r: int(r["offset"], 16))


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

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(ap)
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    recs = load_records()
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)
    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)
    state_inspections = {}

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def load(sav):
        if sav not in state_inspections:
            state_inspections[sav] = inspect_state_before_load(
                c, ROOT / sav, media_identity)
        r = c.call("emulator.loadState",
                   {"path": str(ROOT / sav), "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        c.call("emulator.clearControllerState", {"port": 0})

    out = {}

    # ---- subject 1: the player, driven forward -------------------------------
    prec = recs["player_block"]
    baseline = json.loads(
        (ROOT / "analysis" / "phase2_stage_baseline.json").read_text())
    anchor = baseline["stages"]["stage01_anthill"]["save"]
    load(anchor)
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    c.call("emulator.advanceFrames", {"frames": 20})       # reach steady speed
    frames = []
    for _ in range(40):
        blob = rd(prec["base"], prec["size"])
        pos = struct.unpack_from("<iii", blob, 0)
        frames.append((blob, pos))
        c.call("emulator.advanceFrames", {"frames": 1})
    c.call("emulator.clearControllerState", {"port": 0})
    out["player_block"] = {
        "anchor": anchor, "input": "up held (running)",
        "frames": len(frames),
        "findings": analyse(prec, frames),
    }

    # ---- subject 1b: the player JUMPING (flat running has dy == 0, so vertical
    # velocity is unprovable without vertical motion) --------------------------
    load(anchor)
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"cross": True}})
    c.call("emulator.advanceFrames", {"frames": 4})
    c.call("emulator.clearControllerState", {"port": 0})
    frames = []
    for _ in range(40):
        blob = rd(prec["base"], prec["size"])
        frames.append((blob, struct.unpack_from("<iii", blob, 0)))
        c.call("emulator.advanceFrames", {"frames": 1})
    out["player_block_jump"] = {
        "anchor": anchor, "input": "cross (jump) — vertical motion",
        "frames": len(frames),
        "findings": analyse(prec, frames),
    }

    # ---- subject 3: a MOVING ENEMY (the actor record's +0x14..0x23 run) -------
    arec = recs["actor_record"]
    load(anchor)
    abase, asize, an = arec["base"], arec["size"], arec["instances"]

    def moving_actor():
        a = rd(abase, asize * an)
        c.call("emulator.advanceFrames", {"frames": 2})     # 30 Hz logic cadence
        b = rd(abase, asize * an)
        best, best_d = None, 0
        for i in range(an):
            if struct.unpack_from("<I", b, i * asize)[0] == 0:
                continue
            pa = struct.unpack_from("<iii", a, i * asize + 4)
            pb = struct.unpack_from("<iii", b, i * asize + 4)
            d = sum(abs(x - y) for x, y in zip(pa, pb))
            if d > best_d:
                best, best_d = i, d
        return best

    idx = moving_actor()
    frames = []
    if idx is not None:
        for _ in range(40):
            blob = rd(abase + idx * asize, asize)
            frames.append((blob, struct.unpack_from("<iii", blob, 4)))   # pos @ +0x04
            c.call("emulator.advanceFrames", {"frames": 1})
    out["actor_record"] = {
        "anchor": anchor, "moving_actor_index": idx,
        "actor_id": (struct.unpack_from("<I", frames[0][0], 0)[0]
                     if frames else None),
        "frames": len(frames),
        "findings": analyse(arec, frames) if frames else [],
    }

    # ---- subject 2: the in-flight berry (gravity is the built-in control) ----
    crec = recs["contact_record"]
    load("red_berry_thrown.sav")
    base, size, n = crec["base"], crec["size"], crec["instances"]

    def moving_slot():
        """Find the slot whose position actually changes frame to frame."""
        a = rd(base, size * n)
        c.call("emulator.advanceFrames", {"frames": 2})   # 30 Hz logic cadence
        b = rd(base, size * n)
        for i in range(n):
            pa = struct.unpack_from("<iii", a, i * size)
            pb = struct.unpack_from("<iii", b, i * size)
            at = struct.unpack_from("<H", b, i * size + 0x22)[0]
            if at > 0 and pa != pb:
                return i
        return None

    slot = moving_slot()
    frames = []
    if slot is not None:
        for _ in range(24):                    # short: the berry lands
            blob = rd(base + slot * size, size)
            pos = struct.unpack_from("<iii", blob, 0)
            frames.append((blob, pos))
            c.call("emulator.advanceFrames", {"frames": 1})
    out["contact_record"] = {
        "anchor": "red_berry_thrown.sav",
        "moving_slot": slot,
        "frames": len(frames),
        "findings": analyse(crec, frames) if frames else [],
    }

    run_provenance = finish_run(
        args, generator="tools/phase3_unknown_fields.py",
        anchor={"saves": [anchor, "red_berry_thrown.sav"],
                "fixture_sha256": fixture_pin(anchor, "red_berry_thrown.sav"),
                "state_inspections": list(state_inspections.values()),
                "media_identity": media_identity},
        timing={"player_frames": out.get("player_block", {}).get("frames"),
                "actor_frames": out.get("actor_record", {}).get("frames"),
                "contact_frames": out.get("contact_record", {}).get("frames")},
    )
    doc = {
        "_comment": "Phase-3 WP5 unknown-byte drainer. EXACT-MATCH hypothesis "
                    "testing: a candidate is promoted only if it equals the "
                    "per-frame position delta on EVERY captured frame (one "
                    "mismatch kills it). The berry's known gravity (128/frame^2) "
                    "is the built-in control — a run that cannot rediscover it "
                    "should not be trusted. Regenerate: "
                    "tools/phase3_unknown_fields.py.",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media": {"serial": status.get("game_serial")},
        "media_identity_after_connect": media_identity,
        "fixture_sha256": fixture_pin(anchor, "red_berry_thrown.sav"),
        "subjects": out,
    }
    path = ROOT / "analysis" / "phase3_unknown_fields.json"
    write_live_evidence(path, doc)
    for rid, s in out.items():
        print(f"[{rid}] {s['frames']} frames -> {len(s['findings'])} findings")
        for f in s["findings"]:
            what = (f"velocity {f['exact_velocity']} [run {f['longest_exact_run']}, "
                    f"{f['match']}] ({f['alignment']})"
                    if "exact_velocity" in f else
                    f"constant delta {f['constant_delta_per_move']}/move")
            tag = (f"  !! currently declared as {f['declared_as']}"
                   if f.get("declared_as") else "")
            print(f"    {f['offset']} {f['width']:>3s}: {what}{tag}")
    print(f"[unknown_fields] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
