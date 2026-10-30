#!/usr/bin/env python3
"""Map each in-game scene to the disc LEVEL directory whose DAT it actually loads.

WHY THIS EXISTS
---------------
The disc has LEVEL00..LEVEL10 directories; the game has 15+ scenes with scene ids that
are NOT sequential (level01.sav -> scene 1, level02.sav -> 3, level03.sav -> 2,
level_06.sav -> 11 ...). Assuming `LEVEL06/` is "level 6" produces wrong answers: it
says LEVEL06 contains no blue seed-power token, while the operator can see one above
Flik on spawn in the level they call 6. The directory name is not the level number.

Getting this right is a prerequisite for any "every applicable level" claim (Phase-4
DoD item 6): you cannot enumerate which levels contain a pickup until you know which
DAT each level loads.

METHOD
------
LEVEL.DAT is uncompressed and loaded verbatim, so disc bytes == RAM bytes. For each
save state: load it, read main RAM, and search for a distinctive slice of every
candidate DAT. Whichever file's bytes are resident is the one that scene loaded.

Several probe slices are taken from each file and all must match, so a short shared
run (headers, padding) cannot produce a false pairing.

USAGE
    tools/map_scene_to_dat.py --port 23680 --states level01.sav level_06.sav ...
    tools/map_scene_to_dat.py --port 23680            # all level*.sav in the repo root
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import time
from pathlib import Path

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
SCENE = 0x80082504
RAM_BASE, RAM_SIZE, CHUNK = 0x80000000, 2 * 1024 * 1024, 512 * 1024
PROBE_LEN = 48
PROBE_OFFSETS = (0x40, 0x180, 0x400)


def probes(path: Path):
    data = path.read_bytes()
    out = []
    for off in PROBE_OFFSETS:
        if off + PROBE_LEN <= len(data):
            sl = data[off:off + PROBE_LEN]
            if len(set(sl)) > 4:          # skip padding / all-same runs
                out.append(sl)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23680)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--disc", type=Path, default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--states", nargs="*", default=None)
    ap.add_argument("--json", type=Path, default=ROOT / "analysis/scene_to_dat_map.json")
    args = ap.parse_args()

    if args.states:
        states = [Path(s) if Path(s).is_absolute() else ROOT / s for s in args.states]
    else:
        states = sorted({p for pat in ("level*.sav", "LEVEL*.sav")
                         for p in ROOT.glob(pat)
                         if "tier3" not in p.name.lower() and "modded" not in p.name.lower()})

    cands = {}
    for p in sorted(ROOT.glob("REBUILD/files/LEVEL*/*.DAT")):
        pr = probes(p)
        if pr:
            cands[str(p.relative_to(ROOT))] = pr
    print("candidate DATs: %d, states: %d" % (len(cands), len(states)))

    tmp = _scratch("scenemap")
    tmp.mkdir(parents=True, exist_ok=True)
    log = tmp / "launch.log"
    subprocess.run(["rm", "-rf", str(tmp / "cfg")], check=False)
    with log.open("w") as fh:
        subprocess.run(["bash", str(ROOT / "tools/launch_repro_playback.sh"),
                        "--execution-mode", "Interpreter", "--config-dir", str(tmp / "cfg"),
                        "--port", str(args.port), "--token", args.token,
                        "--disc", str(args.disc)], cwd=str(ROOT),
                       stdout=fh, stderr=fh, check=False)
    text = log.read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-600:])
    pid = text.split("pid=")[1].split()[0]

    results = []
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(900)
        for sav in states:
            rec = {"state": sav.name}
            try:
                c.call("emulator.loadState", {"path": str(sav)})
                rec["scene_id"] = struct.unpack("<I", bytes.fromhex(c.call(
                    "debugger.readMemory",
                    {"address": "0x%08x" % SCENE, "length": 4})["hex"]))[0]
                ram = b"".join(bytes.fromhex(c.call(
                    "debugger.readMemory",
                    {"address": "0x%08x" % (RAM_BASE + o), "length": CHUNK})["hex"])
                    for o in range(0, RAM_SIZE, CHUNK))
                hits = [name for name, prs in cands.items()
                        if all(pr in ram for pr in prs)]
                rec["dats_resident"] = sorted(hits)
                rec["level_dir"] = sorted({h.split("/")[2] for h in hits})
            except Exception as exc:
                rec["error"] = str(exc)[:160]
            results.append(rec)
            print(json.dumps(rec), flush=True)
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    by_scene = {}
    for r in results:
        if "scene_id" in r:
            by_scene.setdefault(r["scene_id"], set()).update(r.get("level_dir") or [])
    args.json.write_text(json.dumps({
        "_comment": "Scene id -> disc LEVEL directory, determined by finding which DAT's "
                    "bytes are resident in RAM (LEVEL.DAT is uncompressed, so disc bytes "
                    "== RAM bytes). The directory name is NOT the level number. "
                    "Regenerate: tools/map_scene_to_dat.py",
        "states": results,
        "scene_to_level_dir": {str(k): sorted(v) for k, v in sorted(by_scene.items())},
    }, indent=1) + "\n")
    print("\nscene -> level dir:")
    for k, v in sorted(by_scene.items()):
        print("  scene %-3s -> %s" % (k, ", ".join(sorted(v)) or "(none matched)"))
    print("wrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
