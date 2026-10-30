#!/usr/bin/env python3
"""Phase-2 all-stage death/lifecycle matrix: reproduce the death->respawn law on
EVERY campaign anchor (exit-gate breadth item from external review).

Per stage: true health := 0, teleport onto each censused chunk-31 record in turn
(pos + prev-tick mirrors) until a real contact hit fires the death flow; record
the killing record, respawn state, and law conformance (lives-1, respawn hp==4).
Stages whose records never produce contact damage are recorded as such with the
records tried — a documented outcome, not a silent gap (some rosters are
non-hostile at the anchor, e.g. seeds/props/NPCs; stage09's table is empty).

Usage: python3 tools/phase2_death_matrix.py [--port 23472]
Output: analysis/phase2_death_matrix.json
"""
from __future__ import annotations

import argparse
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

ANCHORS = [
    ("training", "phase3_pristine_training_gameplay_i5.sav"),
    ("stage01_anthill", "level01.sav"), ("stage02_tunnels", "level02.sav"),
    ("stage03_council_chamber", "level03.sav"),
    ("stage04_cliffside_canyon", "level04.sav"),
    ("stage05_riverbed_run", "level05.sav"), ("stage06_birdnest", "level_06.sav"),
    ("stage07_city_entrance", "level_07.sav"), ("stage08_city_square", "level_08.sav"),
    ("stage09_bug_bar", "level_09.sav"), ("stage10_clover_forest", "level_10.sav"),
    ("stage11_the_tree", "level_11.sav"), ("stage12_battle_arena", "level_12.sav"),
    ("stage13_anthill_two", "level_13.sav"),
    ("stage14_riverbed_flight", "level_14.sav"),
    ("stage15_canyon_showdown", "level_15.sav"),
]
MAX_RECORDS = 64   # full rosters (review: 24 truncated stages 10/11/14)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--stages", help="comma-separated stage labels to (re)run; "
                                     "others are merged from the existing artifact")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def snap():
        return {"hp": struct.unpack("<h", rd(0x800A6594, 2))[0],
                "lives": rd(0x800A65A0, 1)[0],
                "scene": struct.unpack("<I", rd(0x80082504, 4))[0],
                "pos": list(struct.unpack("<iii", rd(0x800A6500, 12)))}

    state_inspections = {}

    def load(sav):
        for m in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(m, {})
            except Exception:
                pass
        inspection = inspect_state_before_load(c, ROOT / sav, media_identity)
        state_inspections[sav] = inspection
        r = c.call("emulator.loadState", {"path": str(ROOT / sav),
                                          "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        c.call("emulator.clearControllerState", {"port": 0})

    def wr32(a, v):
        c.call("debugger.writeU32", {"address": "0x%08x" % a, "value": v & 0xFFFFFFFF})

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)

    matrix = {}
    prior = {}
    out_path = ROOT / "analysis" / "phase2_death_matrix.json"
    only = set(args.stages.split(",")) if args.stages else None
    if only and out_path.exists():
        prior = json.loads(out_path.read_text()).get("matrix", {})
    for label, sav in ANCHORS:
        if only and label not in only:
            if label in prior:
                matrix[label] = prior[label]
            continue
        load(sav)
        buf = rd(0x8009FE04, 0x84 * MAX_RECORDS)
        recs = []
        for i in range(MAX_RECORDS):
            rid, x, y, z = struct.unpack_from("<Iiii", buf, i * 0x84)
            if (rid == 0 and x == 0 and y == 0 and z == 0) or rid > 0x2000 \
                    or abs(x) > 0x400000:
                break
            recs.append((i, rid, x, y, z))
        entry = {"anchor": sav, "records_available": len(recs), "records_tried": 0,
                 "records_skipped_seeds": 0}
        for i, rid, x, y, z in recs:
            if rid == 11:
                # id 11 = movable seed class (proven by the carry oracle): seeds
                # deal no contact damage, and landing on seed geometry clips Flik
                # through the floor (operator-observed twice) — skip them.
                entry["records_skipped_seeds"] += 1
                continue
            load(sav)
            c.call("debugger.writeU16", {"address": "0x800A6594", "value": 0})
            # NORMALIZE LIVES (operator catch: six late-stage anchors sit at
            # lives=0, where death fires the game-over FMV instead of an
            # in-level respawn and a lives-1 detector misses it entirely)
            c.call("debugger.writeU8", {"address": "0x800A65A0", "value": 3})
            # place Flik ABOVE and BESIDE the record, not inside it — exact-center
            # teleports clip into object geometry (operator-observed: Clover Forest
            # seeds) and BURROWED enemies' records sit BELOW the floor (operator-
            # observed: emerging spiders), so drop from well above (Y is down:
            # y-6000) and let gravity settle Flik onto the surface; no fall damage.
            tx, ty, tz = x - 250, y - 6000, z - 250
            for addr, val in ((0x800A6500, tx), (0x800A6510, tx),
                              (0x800A6504, ty), (0x800A6514, ty),
                              (0x800A6508, tz), (0x800A6518, tz)):
                wr32(addr, val)
            c.call("emulator.advanceFrames", {"frames": 60})   # fall + settle
            c.call("debugger.pause", {})
            before = snap()
            entry["records_tried"] += 1
            death = None
            for _ in range(6):
                c.call("emulator.advanceFrames", {"frames": 60})
                c.call("debugger.pause", {})
                s = snap()
                # widened detector: any lives change or scene exit = death flow
                if s["lives"] != before["lives"] or s["scene"] != before["scene"]:
                    death = s
                    break
            if death:
                entry.update({
                    "death_observed": True,
                    "via_record": {"index": i, "id": rid},
                    "respawn": death,
                    "law_lives_minus_1": death["lives"] == before["lives"] - 1,
                    "law_respawn_hp_4": death["hp"] == 4,
                    "law_same_scene": death["scene"] == before["scene"],
                })
                break
        else:
            entry.update({
                "death_observed": False,
                "note": "no contact damage from the records tried at this anchor. "
                        "METHOD-BOUNDED negative: ground-contact probes only — "
                        "airborne actors (seed-carrying grasshoppers, fliers; "
                        "operator-noted in Anthill Part Two) can be missed by the "
                        "drop placement, and non-hostile rosters (seeds/NPCs/props) "
                        "produce no contact by nature.",
            })
        matrix[label] = entry
        print(f"[death_matrix] {label}: "
              f"{entry.get('via_record', entry.get('note'))}")

    observed = sum(1 for e in matrix.values() if e.get("death_observed"))
    doc = {
        "_comment": "All-stage death/lifecycle matrix (exit-gate breadth). "
                    "Regenerate: tools/phase2_death_matrix.py.",
        "generated": date.today().isoformat(),
        "media": media_identity,
        "state_inspections": [state_inspections[sav]
                              for _, sav in ANCHORS if sav in state_inspections],
        "stages_with_death_observed": observed,
        "stages_total": len(matrix),
        "matrix": matrix,
        "method_caveats": {
            "negative_conclusions": "method-bounded: ground-contact drop probes only. Airborne actors (seed-carrying grasshoppers in Anthill Part Two, fliers) can be missed; non-hostile rosters (tutorial NPCs, seeds, props) produce no contact by nature.",
            "seed_records_skipped": "id 11 (proven movable-seed class) skipped — no contact damage, and landing on seed geometry clips Flik through the floor (operator-observed).",
            "knockback_not_representative": "hits landing while Flik settles from the drop can tunnel him through geometry (operator-observed on spiders) — NO knockback/post-hit-trajectory conclusions are drawn from these probes; only the death-flow laws (lives-1, respawn hp=4, same scene) are claimed.",
            "stage14_rail": "Riverbed Flight auto-carries Flik (Atta rail) — probes there are rail-constrained; the recorded death stands, negatives within the stage are weaker.",
            "death_attribution": "by record LOCATION; the killer is whatever contacted Flik there, not necessarily the record's own id.",
        },
    }
    out = ROOT / "analysis" / "phase2_death_matrix.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[death_matrix] wrote {out}: {observed}/{len(matrix)} stages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
