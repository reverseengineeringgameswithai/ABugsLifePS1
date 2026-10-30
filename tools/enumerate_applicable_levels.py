#!/usr/bin/env python3
"""Which stages can actually produce the B06 / B08 pickups?

DoD item 6 asks for "every APPLICABLE level", so the list has to be derived rather than
guessed. Two different questions, and conflating them is the trap:

  WHERE THE LANE CAN BE RAISED -- placement of the blue seed-power token (type-0x3f kind
  0x2A). Static, from the level .DAT. But the counter 0x800A6599 PERSISTS across levels,
  so a stage with no tokens is NOT thereby inapplicable.

  WHERE THE OUTPUT CAN BE PRODUCED -- the real test. These pickups are plant OUTPUTS:
  blue x1 -> type 7, blue x3 -> type 6. The plant body model comes from
  *(0x800A649C + type*4), a per-level table filled at load, and NULL means the plant
  functions but is INVISIBLE. Read at runtime from each stage's save state.

Stage -> .DAT uses the corrected law (see EXP_2026-08-01_scene_to_level_data_law):
  dir  = scene_id <= 10 ? scene_id : scene_id - 10
  file = scene_id <= 10 ? LEVEL.DAT : LEVEL1.DAT
and the operator's level ordinal comes from the campaign table at 0x80077FA0.

Regenerate: tools/enumerate_applicable_levels.py
"""
from __future__ import annotations
import json, re, struct, subprocess, sys, time
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
TMP = _scratch("applic")
PLANT_MODEL_TABLE = 0x800A649C
BLUE_COUNTER = 0x800A6599
SCENE = 0x80082504
CAMPAIGN = [17, 1, 3, 2, 6, 10, 11, 4, 5, 14, 7, 12, 13, 9, 8, 15]   # 0x80077FA0

# operator level ordinal -> a save state that sits in that stage
SAVES = {
    1: "level01.sav", 2: "level02.sav", 3: "level03.sav", 4: "level04.sav",
    5: "level05.sav", 6: "level_06.sav", 7: "level_07.sav", 8: "level_08.sav",
    9: "level_09.sav", 10: "level_10.sav", 11: "level_11.sav", 12: "level_12.sav",
    13: "level_13.sav", 14: "level_14.sav", 15: "level_15.sav",
}


def dat_for(scene_id):
    d = scene_id if scene_id <= 10 else scene_id - 10
    return "LEVEL%02d/%s" % (d, "LEVEL.DAT" if scene_id <= 10 else "LEVEL1.DAT")


def blue_tokens(dat_rel):
    p = ROOT / "REBUILD/files" / dat_rel
    if not p.exists():
        return None
    out = subprocess.run(["python3", str(ROOT / "tools/list_level_pickups.py"), str(p)],
                         capture_output=True, text=True).stdout
    return sum(1 for l in out.splitlines()
               if re.match(r"\s*\d+\s+0x[0-9a-f]+\s+0x[0-9a-f]+\s+0x2a\b", l))


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 23820
    subprocess.run(["rm", "-rf", str(TMP / "cfg")], check=False)
    log = TMP / "launch.log"
    with log.open("w") as fh:
        subprocess.run(["bash", str(ROOT / "tools/launch_repro_playback.sh"),
                        "--execution-mode", "Interpreter", "--config-dir", str(TMP / "cfg"),
                        "--port", str(port), "--token", "debugger-1000",
                        "--disc", str(ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")],
                       cwd=str(ROOT), stdout=fh, stderr=fh, check=False)
    if "READY" not in log.read_text():
        raise SystemExit("launch failed")
    pid = log.read_text().split("pid=")[1].split()[0]
    rows = []
    try:
        c = DebuggerClient("127.0.0.1", port, "ws")
        c.authenticate("debugger-1000")
        c.transport.sock.settimeout(600)

        def rd(a, n):
            return bytes.fromhex(c.call("debugger.readMemory",
                                        {"address": "0x%08x" % a, "length": n})["hex"])
        for ordinal in sorted(SAVES):
            sav = ROOT / SAVES[ordinal]
            scene_expected = CAMPAIGN[ordinal] if ordinal < len(CAMPAIGN) else None
            rec = {"operator_level": ordinal, "save": sav.name,
                   "scene_id_expected": scene_expected}
            if not sav.exists():
                rec["error"] = "save missing"
                rows.append(rec); continue
            try:
                c.call("emulator.loadState", {"path": str(sav)})
                scene = struct.unpack("<I", rd(SCENE, 4))[0]
                rec["scene_id_measured"] = scene
                rec["scene_matches_campaign_table"] = (scene == scene_expected)
                rec["dat"] = dat_for(scene)
                rec["blue_tokens_in_dat"] = blue_tokens(rec["dat"])
                rec["blue_counter"] = rd(BLUE_COUNTER, 1)[0]
                t6 = struct.unpack("<I", rd(PLANT_MODEL_TABLE + 6 * 4, 4))[0]
                t7 = struct.unpack("<I", rd(PLANT_MODEL_TABLE + 7 * 4, 4))[0]
                rec["plant_model_type6_bubble"] = "0x%08X" % t6
                rec["plant_model_type7_invinc"] = "0x%08X" % t7
                rec["B08_producible"] = t6 != 0
                rec["B06_producible"] = t7 != 0
            except Exception as exc:
                rec["error"] = str(exc)[:140]
            rows.append(rec)
            print(json.dumps({k: rec.get(k) for k in
                              ("operator_level", "scene_id_measured", "dat",
                               "blue_tokens_in_dat", "B06_producible", "B08_producible")}),
                  flush=True)
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    ok = [r for r in rows if "error" not in r]
    out = {"_comment": __doc__.strip().splitlines()[0],
           "campaign_table_0x80077FA0": CAMPAIGN,
           "law": "dir = scene<=10 ? scene : scene-10; file = scene<=10 ? LEVEL.DAT : LEVEL1.DAT",
           "levels": rows,
           "B06_applicable": [r["operator_level"] for r in ok if r.get("B06_producible")],
           "B08_applicable": [r["operator_level"] for r in ok if r.get("B08_producible")],
           "token_bearing": [r["operator_level"] for r in ok if (r.get("blue_tokens_in_dat") or 0) > 0],
           "scene_law_disagreements": [r["operator_level"] for r in ok
                                       if r.get("scene_matches_campaign_table") is False]}
    (ROOT / "analysis/phase4_b06_b08_applicable_levels.json").write_text(json.dumps(out, indent=1) + "\n")
    print()
    print("B06 producible in levels:", out["B06_applicable"])
    print("B08 producible in levels:", out["B08_applicable"])
    print("blue-token bearing      :", out["token_bearing"])
    print("scene-law disagreements :", out["scene_law_disagreements"] or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
