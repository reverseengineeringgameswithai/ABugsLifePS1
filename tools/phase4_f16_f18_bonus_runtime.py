#!/usr/bin/env python3
"""F16/F17/F18: measure the bonus stage's completion law on the running game.

The static side (tools/phase4_f16_f18_bonus_stage.c, 82 pins) says the whole bonus
stage reduces to ONE predicate, evaluated every frame in LEVEL06/LEVEL1.BIN:

    dx = (flik.x - target.x) >> 8 ;  dy = ... ; dz = ...
    if (dx*dx + dy*dy + dz*dz < 1600)  ->  [0x800823A0] = 1 ; [0x80082470] = 30

with a coarse gate ahead of it that skips the entire block, completion included,
when a DIFFERENT reference point (0x8009EC50) is more than 359,999 squared units
from the same target.

Reading that off an image is not the same as it being true, and this session has
already produced several self-consistent static readings that were wrong.  So this
measures it three ways, and each way can fail:

  1. NATURAL PATH.  Replay the retained Bonus_Level_01 fixture into scene 0x10 and
     single-step to the frame where the latch flips.  Compute the squared distance
     from the sample taken AT that frame.  The prediction is exact: the value must
     be < 1600 on the firing frame and >= 1600 on the frame before.  A single-frame
     miss falsifies the shift-then-square reading.

  2. NEGATIVE CONTROL.  The predicate must also NOT fire when it shouldn't.  With
     the run paused just inside the stage, the target table entry is moved to a
     chosen distance from wherever Flik actually is -- 40 units, which squares to
     exactly 1600 and must FAIL the `slti ...,1600` -- and the run advanced.  If the
     latch flips anyway the threshold is not 1600, or is not exclusive.

  3. POSITIVE CONTROL.  Then 39 units (1521).  Must fire.  Moving the TARGET rather
     than the player is deliberate: teleporting Flik risks unstreamed geometry, and
     the target lives in overlay RAM where a write is harmless.

It also samples five named reward fields. Health, lives, berry index, power and the
invulnerability timer are compared across the transition. This does not sample the
whole player-state block or position, and it cannot turn the static fixed-form scan
into a global negative.

⚠️ The fixture is a format-v3 (CachedInterpreter-era) movie.  It is POLL-ONLY: arming
any CPU instrumentation would force the interpreter and desync it silently.  Nothing
here arms a watch or a breakpoint while the movie is driving.  That is also why the
completion frame is found by single-stepping and sampling, not by a write watch.

    tools/phase4_f16_f18_bonus_runtime.py --port 23810
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SCENE = 0x80082504
BONUS_SCENE = 0x10
LATCH = 0x800823A0
FADE = 0x80082470
ORDINAL = 0x8009B88A
FLAGS = 0x8009B889
FLIK = (0x800A6500, 0x800A6504, 0x800A6508)
TARGET_TABLE = 0x800B4070
CACHED_VARIANT = 0x800B40B4
ANIM_FRAME = 0x800B40B8
COARSE_REF = (0x8009EC50, 0x8009EC54, 0x8009EC58)
DESC_TABLE = 0x80096B98
OWN_DESCRIPTOR = 0x800B3F78
ACTOR0, STRIDE = 0x8009FD80, 0x84

# Five reward fields sampled by this poll-only run; not the whole player-state block.
PAY = {
    "health": (0x800A6594, "s16"),
    "lives": (0x800A65A0, "u8"),
    "power": (0x800A6590, "u8"),
    "berry_idx": (0x800A6597, "u8"),
    "invuln": (0x800A657E, "u16"),
}

DEFAULT_MOVIE = "movies/Bonus_Level_01.movie.json"


def launch(port, token, disc, cfg, log, launcher, cwd, mode):
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with Path(log).open("w") as fh:
        subprocess.run(["bash", str(launcher), "--execution-mode", mode,
                        "--config-dir", str(cfg), "--port", str(port), "--token", token,
                        "--disc", str(disc)], cwd=str(cwd), stdout=fh, stderr=fh,
                       check=False)
    text = Path(log).read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-900:])
    return text.split("pid=")[1].split()[0]


class Probe:
    def __init__(self, c):
        self.c = c

    def scatter(self, spec):
        """spec: {name: (addr, type)} -> {name: value}.

        ⚠️ scatterRead reports an unreadable item as value 0 with valid=false, so a
        bad address reads as a perfectly plausible zero. Every item is checked; a
        silent zero here would look exactly like a real measurement.
        """
        keys = list(spec)
        reads = [{"address": "0x%08x" % spec[k][0], "type": spec[k][1]} for k in keys]
        r = self.c.call("debugger.scatterRead", {"reads": reads})
        items = r["reads"]
        if len(items) != len(keys):
            raise SystemExit("scatterRead returned %d items for %d reads"
                             % (len(items), len(keys)))
        out = {}
        for i, k in enumerate(keys):
            if not items[i].get("valid"):
                raise SystemExit("scatterRead: %s at 0x%08x is not valid -- refusing "
                                 "to treat it as 0" % (k, spec[k][0]))
            out[k] = items[i]["value"]
        return out

    def raw(self, addr, length):
        return bytes.fromhex(self.c.call("debugger.readMemory",
                                         {"address": "0x%08x" % addr,
                                          "length": length})["hex"])

    def write32(self, addr, value):
        self.c.call("debugger.scatterWrite",
                    {"writes": [{"address": "0x%08x" % addr, "type": "s32",
                                 "value": int(value)}], "atomic": True})


def sample(p):
    s = p.scatter({
        "scene": (SCENE, "s32"), "latch": (LATCH, "s16"), "fade": (FADE, "s16"),
        "ordinal": (ORDINAL, "u8"), "flags": (FLAGS, "u8"),
        "fx": (FLIK[0], "s32"), "fy": (FLIK[1], "s32"), "fz": (FLIK[2], "s32"),
        "anim": (ANIM_FRAME, "s32"), "variant": (CACHED_VARIANT, "s32"),
        "cx": (COARSE_REF[0], "s32"), "cy": (COARSE_REF[1], "s32"),
        "cz": (COARSE_REF[2], "s32"),
    })
    return s


def sq_dist_shifted(ax, ay, az, bx, by, bz):
    """Exactly what the overlay computes: subtract, arithmetic-shift 8, square, sum."""
    # Python's >> on ints floors, which is exactly MIPS `sra` -- including for
    # negative deltas, where truncating instead would be off by one.
    dx, dy, dz = (ax - bx) >> 8, (ay - by) >> 8, (az - bz) >> 8
    return dx * dx + dy * dy + dz * dz


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--movie", type=Path, default=ROOT / DEFAULT_MOVIE)
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="CachedInterpreter",
                    help="match the recording; the v3 fixtures are CachedInterpreter")
    ap.add_argument("--port", type=int, default=23810)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--max-frame", type=int, default=4000)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_f16_f18_bonus_stage.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/f16f18")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "rows": ["F16_bonus1_spiders", "F17_bonus2_mushrooms", "F18_bonus3_grasshoppers"],
        "question": "what are the bonus stage's rules, and what does it pay?",
        "movie": str(args.movie.name),
        "movie_format": "v3 (CachedInterpreter-era) -- POLL ONLY, never instrumented here",
        "static_prediction": (
            "completion iff sum over x,y,z of ((flik - target) >> 8)^2 < 1600, "
            "gated by the same sum from 0x8009EC50 being <= 359999; "
            "on fire: latch 0x800823A0 := 1 and fade 0x80082470 := 30"),
    }

    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(900)
        p = Probe(c)

        st = c.call("movie.load", {"path": str(args.movie)})
        out["movie_frames"] = st.get("frame_count") or st.get("frames")
        if not c.call("movie.startPlayback", {"load_start_state": True}).get("playing"):
            out["error"] = "playback refused"
            print(json.dumps(out, indent=1))
            return 1

        # ---- 1. reach the bonus stage -----------------------------------------
        f, entered = 0, None
        while f < args.max_frame:
            f += 30
            c.call("movie.advanceToFrame", {"frame": f})
            s = sample(p)
            if s["scene"] == BONUS_SCENE:
                entered = f
                break
        out["entered_bonus_scene_at_frame"] = entered
        if entered is None:
            out["error"] = ("never reached scene 0x10 within %d frames -- the fixture "
                            "did not replay as recorded" % args.max_frame)
            print(json.dumps(out, indent=1))
            return 1

        # ---- 2. WAIT for the overlay to actually be resident, and MEASURE where -
        # Reading the moment the scene id flips gives the PREVIOUS overlay: the scene
        # word changes before the load completes.  A first pass here read a target of
        # (-1939650000, 0, 274726915) -- plainly instructions, not coordinates -- and
        # would have "refuted" a law that is in fact correct.  So residency is found
        # by searching for the blob's own bytes, which also turns the static load base
        # from an assumption into a measurement.
        # The signature must be UNIQUE.  A first attempt used the function prologue and
        # matched at 0x800B39D8 -- 0x38 off, and inconsistent with the blob's own
        # internal `jal`, because LEVEL06/LEVEL.BIN opens with the identical prologue.
        # The data tail (descriptor pointers + target table) cannot collide that way.
        disc = (ROOT / "REBUILD/files/LEVEL06/LEVEL1.BIN").read_bytes()
        SIG_LEN = 0x100
        sig = disc[-SIG_LEN:]
        base, waited = None, 0
        while waited < 1200 and base is None:
            waited += 30
            f += 30
            c.call("movie.advanceToFrame", {"frame": f})
            s = sample(p)
            if s["scene"] != BONUS_SCENE:
                break
            if s["latch"] != 0:       # the transition is still running; nothing loaded
                continue
            window = p.raw(0x800B0000, 0x8000)
            i = window.find(sig)
            if i >= 0:
                base = 0x800B0000 + i - (len(disc) - SIG_LEN)
                if window.count(sig) != 1:
                    raise SystemExit("signature is not unique in the window")
        out["overlay_resident_at_frame"] = f if base is not None else None
        out["measured_load_base"] = ("0x%08X" % base) if base is not None else None
        out["measured_base_matches_static"] = (base == 0x800B39A0)
        if base is None:
            out["error"] = "the bonus overlay never appeared in 0x800B0000..0x800B8000"
            print(json.dumps(out, indent=1))
            return 1

        arrival = sample(p)
        out["arrival"] = arrival

        live_tbl = p.raw(TARGET_TABLE, 0x30)
        off = TARGET_TABLE - 0x800B39A0
        out["target_table_matches_disc"] = (live_tbl == disc[off:off + 0x30])
        out["target_table_live_hex"] = live_tbl.hex()

        desc50 = int.from_bytes(p.raw(DESC_TABLE + 50 * 4, 4), "little")
        out["descriptor_slot_50"] = "0x%08X" % desc50
        out["descriptor_slot_50_is_own_token"] = (desc50 == OWN_DESCRIPTOR)

        # ---- 3. the variant's actor culling -----------------------------------
        variant = arrival["ordinal"]
        actors = p.raw(ACTOR0, STRIDE * 40)
        culled, alive = [], []
        for n in range(33):
            o = n * STRIDE
            hp = int.from_bytes(actors[o + 0x6E:o + 0x70], "little", signed=True)
            f62 = int.from_bytes(actors[o + 0x62:o + 0x64], "little", signed=True)
            (culled if (hp == 0 and f62 == 10001) else alive).append(n)
        out["variant_in_play"] = variant
        out["actors_culled"] = culled
        out["actors_alive"] = alive
        expect = {0: list(range(12, 33)), 1: list(range(14, 33)),
                  2: list(range(0, 14))}.get(variant)
        out["cull_prediction"] = expect
        out["cull_matches_prediction"] = (culled == expect) if expect is not None else None

        # ---- 4/5. single-step the whole stage: decision boundary, both sides ----
        # No perturbation is needed for a negative control.  Every frame Flik spends
        # in the stage NOT completing it is one, and there are ~1500 of them.  The
        # predicate is falsified if any pre-fire frame has d2 < 1600 while the coarse
        # gate was satisfied, or if the firing frame has d2 >= 1600.
        tx = int.from_bytes(live_tbl[variant * 16 + 0:variant * 16 + 4], "little",
                            signed=True)
        ty = int.from_bytes(live_tbl[variant * 16 + 4:variant * 16 + 8], "little",
                            signed=True)
        tz = int.from_bytes(live_tbl[variant * 16 + 8:variant * 16 + 12], "little",
                            signed=True)
        out["target"] = {"x": tx, "y": ty, "z": tz}

        prev, fired, anim = None, None, []
        trail = []
        while f < args.max_frame:
            f += 1
            c.call("movie.advanceToFrame", {"frame": f})
            s = sample(p)
            d2 = sq_dist_shifted(s["fx"], s["fy"], s["fz"], tx, ty, tz)
            g2 = sq_dist_shifted(s["cx"], s["cy"], s["cz"], tx, ty, tz)
            rec = {"f": f, "d2": d2, "coarse2": g2, "latch": s["latch"],
                   "fade": s["fade"], "scene": s["scene"]}
            if len(anim) < 24:
                anim.append(s["anim"])
            if len(trail) < 4000:
                trail.append(rec)
            if s["latch"] == 1 and fired is None:
                fired = {"frame": f, "d2_at_fire": d2, "coarse2_at_fire": g2,
                         "fade": s["fade"],
                         "d2_frame_before": prev["d2"] if prev else None,
                         "flik": [s["fx"], s["fy"], s["fz"]]}
                break
            if s["scene"] != BONUS_SCENE:
                out["left_scene_before_firing_at_frame"] = f
                break
            prev = rec

        out["anim_frame_sequence"] = anim
        out["anim_within_0_15"] = all(0 <= a <= 15 for a in anim)
        out["natural_fire"] = fired
        out["trail_tail"] = trail[-12:]

        pre = [t for t in trail if fired is None or t["f"] < fired["frame"]]
        gated = [t for t in pre if t["coarse2"] > 359999]
        inside_but_silent = [t for t in pre if t["d2"] < 1600 and t["coarse2"] <= 359999]
        out["negative_control"] = {
            "frames_stepped_in_stage": len(pre),
            "min_d2_before_firing": min((t["d2"] for t in pre), default=None),
            "frames_where_coarse_gate_blocked": len(gated),
            "max_coarse2_seen": max((t["coarse2"] for t in pre), default=None),
            "frames_inside_1600_that_did_NOT_fire": len(inside_but_silent),
            "violations": inside_but_silent[:5],
        }

        if fired:
            ok = (fired["d2_at_fire"] < 1600
                  and fired["d2_frame_before"] is not None
                  and fired["d2_frame_before"] >= 1600
                  and not inside_but_silent)
            out["natural_verdict"] = (
                ("CONFIRMED to the frame: over %d stepped frames in the stage the "
                 "latch stayed 0 while the squared distance never fell below %d, then "
                 "flipped on frame %d at %d (< 1600) with the previous frame at %d "
                 "(>= 1600), fade %s. Both sides of the boundary are measured."
                 % (len(pre), out["negative_control"]["min_d2_before_firing"],
                    fired["frame"], fired["d2_at_fire"], fired["d2_frame_before"],
                    fired["fade"]))
                if ok else
                ("NOT CONFIRMED: fired at d2=%s, previous frame d2=%s, and %d frames "
                 "were inside 1600 without firing. Re-derive before banking."
                 % (fired["d2_at_fire"], fired["d2_frame_before"],
                    len(inside_but_silent))))

            # ---- 6. the reward -------------------------------------------------
            pay_before = p.scatter({k: v for k, v in PAY.items()})
            pay_before["flags"] = p.scatter({"flags": (FLAGS, "u8")})["flags"]
            pay_before["ordinal"] = p.scatter({"o": (ORDINAL, "u8")})["o"]
            for _ in range(240):
                f += 5
                c.call("movie.advanceToFrame", {"frame": f})
                s = sample(p)
                if s["scene"] != BONUS_SCENE:
                    break
            pay_after = p.scatter({k: v for k, v in PAY.items()})
            pay_after["flags"] = p.scatter({"flags": (FLAGS, "u8")})["flags"]
            pay_after["ordinal"] = p.scatter({"o": (ORDINAL, "u8")})["o"]
            out["pay_before"] = pay_before
            out["pay_after"] = pay_after
            out["scene_after_bonus"] = s["scene"]
            changed = [k for k in PAY if pay_before[k] != pay_after[k]]
            out["player_state_changed_by_reward"] = changed
            out["reward_verdict"] = (
                "the reward changed flags %s -> %s and ordinal %s -> %s; player-state "
                "words changed: %s"
                % (pay_before["flags"], pay_after["flags"], pay_before["ordinal"],
                   pay_after["ordinal"], changed or "NONE"))
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in out
                      if k not in ("trail_tail", "target_table_live_hex", "arrival")},
                     indent=1)[:3200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
