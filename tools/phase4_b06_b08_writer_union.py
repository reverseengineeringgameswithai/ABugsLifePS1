#!/usr/bin/env python3
"""Union the STATIC frontier with every writer actually observed across the fixtures.

The static censuses (store sites, callee writes, overlays) each carry a residual that
cannot be discharged by analysis: accesses through a pointer loaded from memory, and
indirect calls. This is the other half -- replay every traceable fixture with a write
watch on the power slot and enumerate the PCs that really fire.

It cannot prove absence: a writer on an unexercised path stays invisible. What it does
give is a bound of the form "across N fixtures covering M frames of natural gameplay,
no writer appeared outside the enumerated set" -- which is a materially different and
checkable claim from "the static scan found everything".

Regenerate: tools/phase4_b06_b08_writer_union.py
"""
from __future__ import annotations
import json, struct, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path.home()/"duckstation/scripts/debugger-client"))
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


ROOT = Path("~/Downloads/ABL")
TMP = _scratch("union")
SLOT = 0x800A657E
FIXTURES = [
    ("b06_cold_boot", "movies/Phase4/b06_invincibility_hits_from_boot.movie.json"),
    ("b08_cold_boot", "movies/Phase4/B08_bubble_repeated_hits_from_boot.movie.json"),
    ("level_transition", "movies/B06_LevelTransition_tagged.movie.json"),
]
# Every site the static work accounts for.
KNOWN = {
    "0x80048654": "tick (player_vertical_update)",
    "0x8004a808": "absorb (damage handler)",
    "0x80051ea0": "harvester equip",
    "0x80051f60": "harvester active",
    "0x800588d0": "B06 grant := 400",
    "0x800589a8": "B08 grant := -3",
    "0x8005b268": "respawn reset",
    "0xbfc02bb0": "BIOS memset, called by 0x80046B68 spawn (callee write)",
}
# Correction history: 0x8004AFB0 was formerly included as a static-only
# knockdown clear. The pristine base chain makes its EA player+0x82, not the
# power slot at player+0x7E, so it must not be accepted by a slot-writer union.
RETRACTED_NON_WRITERS = {"0x8004afb0": "player+0x82 store, not slot"}


def run(tag, movie, port):
    cfg = TMP / ("cfg-" + tag)
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    log = TMP / ("launch-" + tag + ".log")
    with log.open("w") as fh:
        subprocess.run(["bash", str(ROOT / "tools/launch_repro_playback.sh"),
                        "--execution-mode", "Interpreter", "--config-dir", str(cfg),
                        "--port", str(port), "--token", "debugger-1000",
                        "--disc", str(ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")],
                       cwd=str(ROOT), stdout=fh, stderr=fh, check=False)
    if "READY" not in log.read_text():
        return {"fixture": tag, "error": "launch failed"}
    pid = log.read_text().split("pid=")[1].split()[0]
    try:
        c = DebuggerClient("127.0.0.1", port, "ws")
        c.authenticate("debugger-1000")
        c.transport.sock.settimeout(900)
        n = c.call("movie.load", {"path": str(ROOT / movie)})["frame_count"]
        c.call("movie.startPlayback", {"load_start_state": True})
        c.call("accessLog.clear", {})
        c.call("accessLog.addWatch", {"address": "0x%08x" % SLOT, "length": 2,
                                      "type": "write", "max_events": 200000})
        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        while time.time() - began < 420:
            time.sleep(1.5)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 5:
                    break
            else:
                stalls = 0
            last = idx
        # keep running past movie end so a transition/spawn memset is included
        for _ in range(10):
            for b in ("cross", "start"):
                try:
                    c.call("emulator.pressButton", {"button": b, "frames": 3, "port": 0,
                                                    "release_after": True})
                except Exception:
                    pass
            c.call("emulator.advanceFrames", {"frames": 240})
        ev, off = [], 0
        while True:
            pg = c.call("accessLog.get", {"offset": off, "limit": 10000})
            got = pg.get("events") or []
            ev.extend(got)
            if len(got) < 10000:
                break
            off += len(got)
        pcs = {}
        for e in ev:
            pc = str(e.get("instruction_pc") or e.get("pc") or "").lower()
            pcs[pc] = pcs.get(pc, 0) + 1
        return {"fixture": tag, "movie": movie, "frames": n,
                "slot_writes": len(ev), "writer_pcs": pcs}
    except Exception as exc:
        return {"fixture": tag, "error": str(exc)[:180]}
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    base = int(sys.argv[1]) if len(sys.argv) > 1 else 23800
    results = [run(t, m, base + i) for i, (t, m) in enumerate(FIXTURES)]
    observed = {}
    for r in results:
        for pc, n in (r.get("writer_pcs") or {}).items():
            observed[pc] = observed.get(pc, 0) + n
    unknown = {pc: n for pc, n in observed.items() if pc not in KNOWN}
    out = {"_comment": __doc__.strip().splitlines()[0],
           "fixtures": results,
           "observed_writers": {pc: {"hits": n, "known_as": KNOWN.get(pc, "UNKNOWN")}
                                for pc, n in sorted(observed.items())},
           "outside_the_enumerated_set": unknown,
           "verdict": ("no writer outside the enumerated set" if not unknown
                       else "UNKNOWN WRITER(S) OBSERVED -- investigate")}
    (ROOT / "analysis/phase4_b06_b08_writer_union.json").write_text(json.dumps(out, indent=1) + "\n")
    for r in results:
        print("%-18s writes=%-6s pcs=%s" % (r.get("fixture"), r.get("slot_writes"),
                                            sorted((r.get("writer_pcs") or {}))))
    print()
    print("VERDICT:", out["verdict"])
    return 0 if not unknown else 1


if __name__ == "__main__":
    raise SystemExit(main())
