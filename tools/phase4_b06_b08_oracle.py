#!/usr/bin/env python3
"""B06/B08 cold-boot oracle: replay a from-boot movie and ASSERT the natural lifecycle.

WHY THIS EXISTS
---------------
The B06 row was once called solved on runtime evidence whose decisive runs began by
POKING the invincibility timer, from save-state-anchored movies with `from_boot:false`.
That fails DoD item 1, which requires a deterministic cold-boot reproduction with
observable assertions -- and it fails it in a way that matters, because a poked timer
proves the damage path reads the slot, not that collecting the pickup produces that
state in the first place.

This replays a movie anchored to a POWER-ON BOOT and asserts the whole lifecycle with
no pokes of any kind:

B06 (invincibility, time-consumed):
  1. GRANT      0x800588D0 writes 400 -- naturally, from collecting the pickup
  2. PROTECTED  contacts occur while the timer is positive (stagger writes at
                0x8004A814) and NO write to true health lands
  3. TICK       the timer decreases monotonically, one per two frames
  4. EXPIRY     it lands exactly on 0 -- never negative, which would silently become a
                bubble shield (the `blez` guard at 0x80048648)
  5. VULNERABLE after expiry, a contact reaches 0x8004A888 and health decrements

B08 (bubble shield, hit-consumed):
  1. GRANT      0x800589A8 writes -3 -- naturally, from collecting the pickup
  2. ABSORB     each contact increments the quota toward 0 via 0x8004A808, and NO
                write to true health lands while the quota is negative
  3. NOT TICKED the tick 0x80048654 never touches the slot while it is negative --
                a bubble is time-INVARIANT, which is the `blez` guard's other half and
                the property that distinguishes the two rows sharing one halfword
  4. POP        the quota reaches exactly 0
  5. VULNERABLE after the pop, a contact reaches 0x8004A888 and health decrements

It is also the committed runner the runtime claims were missing: the artifact it emits
is computed, not authored, and it exits non-zero if any assertion fails.

Driven at 60 Hz (`debugger.resume` + poll), never `movie.advanceToFrame`, because the
two regimes are not equivalent for anything phase-sensitive.

USAGE
    tools/phase4_b06_oracle.py --port 23650 \
        --movie movies/Phase4/b06_invincibility_hits_from_boot.movie.json \
        --json analysis/phase4_b06_oracle.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # for live_session_provenance
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

def _scratch(name: str) -> "pathlib.Path":
    """Portable scratch dir. Was a hard-coded ~/.claude/jobs/<session>/ path in
    the first committed version of these tools -- machine- AND session-specific, so they
    could not run for anyone else. Override with ABL_SCRATCH."""
    import os, tempfile, pathlib as _p
    # Prefer an explicit override, then the harness job dir. Falling straight to the
    # system temp dir is a poor default here: /tmp is a RAM-backed tmpfs under a user
    # quota on this machine, and prior verification clones had already taken 49 GB of it.
    base = (os.environ.get("ABL_SCRATCH")
            or (os.environ.get("CLAUDE_JOB_DIR") and
                _p.Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp" / "abl-scratch")
            or _p.Path(tempfile.gettempdir()) / "abl-scratch")
    p = _p.Path(base) / name
    p.mkdir(parents=True, exist_ok=True)
    return p


ROOT = Path(__file__).resolve().parent.parent
SLOT, HEALTH, STAGGER = 0x800A657E, 0x800A6594, 0x800A6592
B06_GRANT_PC = "0x800588d0"
B08_GRANT_PC = "0x800589a8"
ABSORB_PC = "0x8004a808"
TICK_PC = "0x80048654"
DAMAGE_PC = "0x8004a888"

ROWS = {
    "b06": {"movie": "movies/Phase4/b06_invincibility_hits_from_boot.movie.json",
            "artifact": "analysis/phase4_b06_oracle.json"},
    "b08": {"movie": "movies/Phase4/B08_bubble_repeated_hits_from_boot.movie.json",
            "artifact": "analysis/phase4_b08_oracle.json"},
}


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def launch(port, token, disc, cfg, log, launcher, cwd):
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with Path(log).open("w") as fh:
        subprocess.run([
            "bash", str(launcher), "--execution-mode", "Interpreter",
            "--config-dir", str(cfg), "--port", str(port), "--token", token,
            "--disc", str(disc)], cwd=str(cwd), stdout=fh, stderr=fh, check=False)
    text = Path(log).read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-800:])
    return text.split("pid=")[1].split()[0]


def collect(c, method="accessLog.get"):
    out, off = [], 0
    while True:
        page = c.call(method, {"offset": off, "limit": 10000})
        got = page.get("events") or []
        out.extend(got)
        if len(got) < 10000:
            break
        off += len(got)
    return out



def _run_provenance(client, generator: pathlib.Path) -> dict:
    """Bind this artifact to the exact media, fork and toolchain that produced it.

    engineering-specs/phase4-closure.md requires a retained oracle to carry mounted-media
    identity and debugger binary/capability provenance. Without them an artifact cannot be
    distinguished from one produced against a different disc or a since-changed fork --
    which is the whole point of retaining it. Reuses the Phase-3 helper rather than
    inventing a second provenance format; degrades to a recorded reason if it is
    unavailable, instead of silently omitting the field.
    """
    import hashlib
    import subprocess
    from datetime import datetime, timezone

    def _sha(path):
        try:
            return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
        except OSError:
            return None

    def _git(*a, cwd):
        try:
            return subprocess.run(["git", *a], cwd=str(cwd), capture_output=True,
                                  text=True, check=False).stdout.strip()
        except OSError:
            return None

    duck = pathlib.Path.home() / "duckstation"
    prov = {
        "generator": str(generator.relative_to(ROOT)) if generator.is_relative_to(ROOT)
                     else generator.name,
        "generator_sha256": _sha(generator),
        "repository_head": _git("rev-parse", "HEAD", cwd=ROOT),
        "repository_dirty": bool(_git("status", "--short", cwd=ROOT)),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "duckstation": {"revision": _git("rev-parse", "HEAD", cwd=duck),
                        "dirty": bool(_git("status", "--short", cwd=duck))},
    }
    try:
        import live_session_provenance as lsp
        prov["media_identity"] = lsp.verified_media_identity(
            client, client.call("debugger.status", {}))
    except SystemExit:
        raise
    except Exception as exc:
        prov["media_identity"] = None
        prov["media_identity_unavailable"] = str(exc)[:200]
        # Fall back to the RPC's own view, which is weaker but still binds the disc.
        try:
            prov["media_info_rpc"] = client.call("emulator.getMediaInfo", {})
        except Exception:
            pass
    return prov


def _watch_saturation(client) -> dict:
    """Whether any watch dropped events. A truncated ring means the run's negative
    claims ('zero health writes') are unsound -- the evidence may simply have been
    dropped. phase4-closure.md requires this to be retained, not assumed."""
    out = {}
    for name, method in (("accessLog", "accessLog.get"), ("execTrace", "execTrace.get")):
        try:
            page = client.call(method, {"offset": 0, "limit": 1})
            out[name] = {"truncated": bool(page.get("truncated")),
                         "total": page.get("total")}
        except Exception as exc:
            out[name] = {"error": str(exc)[:120]}
    errors = [n for n, v in out.items() if isinstance(v, dict) and "error" in v]
    out["any_truncated"] = any(
        isinstance(v, dict) and v.get("truncated") for v in out.values())
    # An error is UNKNOWN, not "not truncated". Collapsing the two is how a failed
    # safety check turns into a passing one.
    out["indeterminate"] = bool(errors)
    out["errors"] = errors or None
    return out

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--row", choices=sorted(ROWS), default="b06")
    ap.add_argument("--movie", type=Path)
    ap.add_argument("--disc", type=Path, default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path, default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--port", type=int, default=23650)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=420.0)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    if args.movie is None:
        args.movie = ROOT / ROWS[args.row]["movie"]
    if args.json is None:
        args.json = ROOT / ROWS[args.row]["artifact"]

    tmp = _scratch("oracle-%s" % args.row)
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT)
    out = {"row": args.row, "movie": str(args.movie), "disc": str(args.disc),
           "regime": "60 Hz (debugger.resume + poll); no advanceToFrame; no pokes",
           "execution_mode": "Interpreter"}
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(600)
        out["run_provenance"] = _run_provenance(c, pathlib.Path(__file__).resolve())

        st = c.call("movie.load", {"path": str(args.movie)})
        out["frames"] = st["frame_count"]
        out["from_boot"] = bool((st.get("start_state") or {}).get("from_boot"))
        if not out["from_boot"]:
            out["error"] = "movie is NOT anchored to a cold boot; this oracle requires from_boot"
            print(json.dumps(out, indent=1))
            return 1

        started = c.call("movie.startPlayback", {"load_start_state": True})
        if not started.get("playing"):
            out["error"] = "playback refused: %s" % started
            print(json.dumps(out, indent=1))
            return 1

        c.call("accessLog.clear", {})
        # Scene identity matters for DoD item 6: a natural fixture recorded in the same
        # stage as every earlier one adds lifecycle evidence but not campaign breadth.
        c.call("accessLog.addWatch", {"address": "0x80082504", "length": 4,
                                      "type": "write", "max_events": 20000})
        for a in (SLOT, HEALTH, STAGGER):
            c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": 2,
                                          "type": "write", "max_events": 200000})
        c.call("debugger.resume", {})

        began, last, stalls = time.time(), -1, 0
        while time.time() - began < args.timeout:
            time.sleep(1.0)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 6:
                    break
            else:
                stalls = 0
            last = idx
        out["wall_seconds"] = round(time.time() - began, 1)
        out["final_playback_index"] = last

        ev = []
        for e in collect(c):
            ev.append({"f": e.get("frame"),
                       "addr": str(e.get("address", "")).lower(),
                       "pc": str(e.get("instruction_pc") or e.get("pc") or "").lower(),
                       "new": s16((e.get("new_value") or 0) & 0xFFFF)})
        scene_writes = [e for e in ev if e["addr"].startswith("0x8008250")]
        out["scene_writes"] = [{"f": e["f"], "scene": e["new"] & 0xFFFF} for e in scene_writes][-8:]
        try:
            out["final_scene_id"] = int.from_bytes(bytes.fromhex(c.call(
                "debugger.readMemory", {"address": "0x80082504", "length": 4})["hex"]), "little")
        except Exception:
            out["final_scene_id"] = None
        slot = [e for e in ev if e["addr"] in ("0x800a657e", "0x800a657f")]
        health = [e for e in ev if e["addr"] in ("0x800a6594", "0x800a6595")]
        stagger = [e for e in ev if e["addr"] in ("0x800a6592", "0x800a6593")]
        # Sample saturation HERE, inside the live session. Doing it after the `finally`
        # below queries a killed emulator: both calls raise, and an errors-only result
        # used to compute any_truncated=False -- a safety check reporting "fine" when it
        # had in fact failed to run. That is strictly worse than no check.
        out["watch_saturation"] = _watch_saturation(c)
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    checks, failures = {}, []

    def check(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    if args.row == "b06":
        grants = [e for e in slot if e["pc"] == B06_GRANT_PC and e["new"] == 400]
        out["grant_count"] = len(grants)
        out["first_grant"] = grants[0] if grants else None
        check("1_natural_grant", bool(grants),
              "0x800588D0 wrote 400 at frame %s" % (grants[0]["f"] if grants else None))
        if grants:
            g = grants[0]["f"]
            ticks = [e for e in slot if e["pc"] == TICK_PC and e["f"] >= g]
            zeros = [e for e in ticks if e["new"] == 0]
            expiry = zeros[0]["f"] if zeros else None
            out["expiry_frame"] = expiry
            seq = [e["new"] for e in ticks]
            monotone = all(b - a == -1 for a, b in zip(seq, seq[1:])) if len(seq) > 1 else False
            check("3_tick_monotone", monotone,
                  "%d tick writes, %s" % (len(seq), "strictly -1 each" if monotone
                                          else "NOT strictly decreasing: %s" % seq[:12]))
            check("4_expiry_lands_on_zero", expiry is not None and min(seq or [1]) == 0,
                  "min tick value %s, first zero at frame %s" % (min(seq) if seq else None, expiry))
            if expiry is not None:
                prot = [e for e in stagger if g <= e["f"] < expiry and e["new"] == -30]
                dmg = [e for e in health if g <= e["f"] < expiry and e["pc"] == DAMAGE_PC]
                check("2_protected_contacts", bool(prot) and not dmg,
                      "%d intercepted contacts while active, %d health writes (must be 0)"
                      % (len(prot), len(dmg)))
                post = [e for e in health if e["f"] > expiry and e["pc"] == DAMAGE_PC]
                out["health_writes_after_expiry"] = post[:8]
                check("5_vulnerable_after_expiry", bool(post),
                      "%d damage writes at 0x8004A888 after natural expiry" % len(post))
            else:
                check("2_protected_contacts", False, "no expiry frame; window undefined")
                check("5_vulnerable_after_expiry", False, "no expiry frame")
        else:
            for n in ("2_protected_contacts", "3_tick_monotone",
                      "4_expiry_lands_on_zero", "5_vulnerable_after_expiry"):
                check(n, False, "no natural grant observed")
    else:
        grants = [e for e in slot if e["pc"] == B08_GRANT_PC and e["new"] == -3]
        out["grant_count"] = len(grants)
        out["first_grant"] = grants[0] if grants else None
        check("1_natural_grant", bool(grants),
              "0x800589A8 wrote -3 at frame %s" % (grants[0]["f"] if grants else None))
        if grants:
            g = grants[0]["f"]
            absorbs = [e for e in slot if e["pc"] == ABSORB_PC and e["f"] >= g]
            out["absorbs"] = absorbs[:12]
            pops = [e for e in absorbs if e["new"] == 0]
            pop = pops[0]["f"] if pops else None
            out["pop_frame"] = pop
            seq = [e["new"] for e in absorbs]
            climbing = all(b - a == 1 for a, b in zip(seq, seq[1:])) if len(seq) > 1 else bool(seq)
            check("2_absorb_increments", climbing and bool(absorbs),
                  "%d absorbs, values %s" % (len(absorbs), seq[:8]))
            # the row-defining property: a NEGATIVE slot is never touched by the tick
            window_end = pop if pop is not None else max((e["f"] for e in slot), default=g)
            ticked = [e for e in slot if e["pc"] == TICK_PC and g <= e["f"] <= window_end]
            check("3_bubble_not_time_consumed", not ticked,
                  "%d tick writes while the quota was negative (must be 0)" % len(ticked))
            check("4_pop_lands_on_zero", pop is not None,
                  "quota reached 0 at frame %s" % pop)
            if pop is not None:
                dmg = [e for e in health if g <= e["f"] < pop and e["pc"] == DAMAGE_PC]
                out["health_writes_while_shielded"] = dmg[:8]
                check("2b_no_damage_while_shielded", not dmg,
                      "%d health writes between grant and pop (must be 0)" % len(dmg))
                post = [e for e in health if e["f"] > pop and e["pc"] == DAMAGE_PC]
                out["health_writes_after_pop"] = post[:8]
                check("5_vulnerable_after_pop", bool(post),
                      "%d damage writes at 0x8004A888 after the pop" % len(post))
            else:
                check("2b_no_damage_while_shielded", False, "no pop frame; window undefined")
                check("5_vulnerable_after_pop", False, "no pop frame")
        else:
            for n in ("2_absorb_increments", "2b_no_damage_while_shielded",
                      "3_bubble_not_time_consumed", "4_pop_lands_on_zero",
                      "5_vulnerable_after_pop"):
                check(n, False, "no natural grant observed")

    out["checks"] = checks
    out["failures"] = failures
    out["verdict"] = "PASS" if not failures else "FAIL"
    out["totals"] = {"slot_writes": len(slot), "health_writes": len(health),
                     "stagger_writes": len(stagger)}
    out["all_health_writes"] = [e for e in health if e["pc"] == DAMAGE_PC][:12]
    sat = out.get("watch_saturation") or {"unavailable": "not sampled"}
    if sat.get("any_truncated"):
        failures.append("a watch ring TRUNCATED -- negative claims in this run are "
                        "unsound because events may have been dropped")
    if sat.get("indeterminate"):
        failures.append("watch saturation could not be determined (%s) -- this run's "
                        "negative claims cannot be relied on" % sat.get("errors"))

    print(json.dumps({k: out[k] for k in
                      ("row", "verdict", "frames", "from_boot", "final_scene_id", "wall_seconds", "grant_count",
                       "first_grant", "expiry_frame", "pop_frame", "totals", "checks")
                      if k in out}, indent=1))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + "\n")
        print("wrote", args.json)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
