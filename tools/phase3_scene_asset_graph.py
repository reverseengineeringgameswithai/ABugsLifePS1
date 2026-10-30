#!/usr/bin/env python3
"""Phase-3 WP7: the scene -> asset -> overlay load graph.

The game keeps the whole campaign's resource routing in three EXE tables,
found by scanning the pristine image for level-ish strings and then locating
the code that materializes each table base:

  scene_asset_table    0x8001AD0C  15 x 0x10  "levelNN\\levelXY"
                       consumer 0x8003CFDC in resource_id_dat_load_dispatcher
                       (0x8003CF2C)
  gfx_loadscreen_table 0x8001AE98  15 x 0x10  "gfx\\levelXY.raw"
                       consumer 0x8003F4B8 in switch_dispatch_struct_by_index
                       (0x8003F3B4)
  level_bin_table      0x8001B174   n x 0x0C  "levelN.bin"
                       consumer 0x80046718 in level_file_path_build (0x80046618)

Row i of the asset/GFX tables is scene_id i+1: the disc DIRECTORY (levelNN)
selects the overlay pair (LEVELNN_LEVEL / LEVELNN_LEVEL1 in the function
census) while the ASSET PREFIX (levelXY) selects which sub-level's data and
loading screen load from it — which is why disc directory numbers do NOT
track scene ids (scene 11 loads level02\\level4b).

Cross-verified against the Phase-2 completion oracle: each stage movie's
observed `target_scene` must resolve here to a row, and the 16 stage labels
must land on 15 distinct campaign scenes + Training (scene 17, which is NOT
in this table — it is loaded off-table, so it is reported as a computed gap
rather than silently omitted).

Usage: python3 tools/phase3_scene_asset_graph.py   (requires the local EXE)
Output: analysis/phase3_scene_asset_graph.json
"""
from __future__ import annotations

import json
import struct
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
EXE_BASE = 0x8000F800

SCENE_ASSET_TABLE = 0x8001AD0C
GFX_TABLE = 0x8001AE98
LEVEL_BIN_TABLE = 0x8001B174
ROWS = 15          # entries in the STRING POOL at SCENE_ASSET_TABLE
STRIDE = 0x10
SCENES = 17        # entries in the resource dispatch jr table 0x8001AFB0 (scene_id-1)
RESOURCE_JR = "0x8003CFBC"

CONSUMERS = {
    "scene_asset_table": {"site": "0x8003CFDC",
                          "function": "resource_id_dat_load_dispatcher "
                                      "(0x8003CF2C)"},
    "gfx_loadscreen_table": {"site": "0x8003F4B8",
                             "function": "switch_dispatch_struct_by_index "
                                         "(0x8003F3B4)"},
    "level_bin_table": {"site": "0x80046718",
                        "function": "level_file_path_build (0x80046618)"},
}


def fixture_pin(*rels):
    """DoF #1 (provenance): hash-pin the EXE the decode rests on, so the finding
    cannot silently drift onto a different image."""
    import hashlib
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out
def cstr(exe: bytes, vaddr: int, limit: int = 0x10) -> str:
    off = vaddr - EXE_BASE
    raw = exe[off:off + limit]
    end = raw.find(b"\x00")
    return raw[: end if end >= 0 else limit].decode("ascii", "replace")


def main() -> int:
    exe = EXE.read_bytes()
    census = json.loads((ROOT / "analysis" / "functions.json").read_text())
    oracle = json.loads(
        (ROOT / "analysis" / "phase2_completion_oracle.json").read_text())
    baseline = json.loads((ROOT / "tools" / "build_baselines.json").read_text())
    jr = json.loads((ROOT / "analysis" / "phase3_jr_tables.json").read_text())
    transition = json.loads(
        (ROOT / "analysis" / "phase3_transition_reset.json").read_text())

    overlays: dict[str, list] = {}
    for f in census["functions"]:
        if f.get("space") == "overlay":
            overlays.setdefault(f["overlay"], []).append(f)

    # stage label -> observed scene id (Phase-2 replay evidence)
    scene_to_stage = {}
    for label, st in oracle["stages"].items():
        if isinstance(st.get("target_scene"), int):
            scene_to_stage.setdefault(st["target_scene"], []).append(label)

    # ------------------------------------------------------------------ #
    # CORRECTED 2026-08-01. This loop previously assumed `row index = scene_id - 1`
    # and read a string at SCENE_ASSET_TABLE + (scene-1)*0x10. That assumption was
    # never derived from code and is WRONG: the dispatcher indexes a PERMUTED jr
    # table at 0x8001AFB0, and the strings it reaches are VAB/sound-bank prefixes,
    # not level data. The .DAT is chosen arithmetically further down the same
    # function. Under the old assumption the string's directory disagreed with the
    # real directory for 11 of 15 scenes.
    #
    #   0x8003CF84  addiu v1, s4, -1      ; s4 = scene id
    #   0x8003CF88  sltiu v0, v1, 17      ; valid 1..17
    #   0x8003CFB4  lw    v0, -0x5050(at) ; jr table 0x8001AFB0[scene-1]  (PERMUTED)
    #   0x8003D204  slti  v0, s4, 11
    #   0x8003D214  addiu s4, s4, -10     ; scene >= 11 -> dir = scene - 10
    #   0x8003D218  ori   v0, v0, 320     ; and select the "1" file-name variant
    # ------------------------------------------------------------------ #
    def word(va: int) -> int:
        return struct.unpack_from("<I", exe, va - EXE_BASE)[0]

    def string_row_of(handler: int):
        """The lui/addiu pair inside a scene handler that forms its string pointer."""
        hi = None
        for k in range(14):
            ins = word(handler + k * 4)
            op, rs, rt, imm = ins >> 26, (ins >> 21) & 31, (ins >> 16) & 31, ins & 0xFFFF
            if op == 0x0F and rt == 4:
                hi = imm
            elif op == 0x09 and rt == 4 and rs == 4 and hi is not None:
                addr = (hi << 16) + (imm - 0x10000 if imm & 0x8000 else imm)
                if SCENE_ASSET_TABLE <= addr < SCENE_ASSET_TABLE + ROWS * STRIDE:
                    return (addr - SCENE_ASSET_TABLE) // STRIDE
                return None
        return None

    jr_targets = {t["index"]: int(t["target"], 16)
                  for t in jr["decoded"][RESOURCE_JR]["targets"]}

    rows, gaps = {}, []
    for scene_id in range(1, SCENES + 1):
        handler = jr_targets.get(scene_id - 1)
        srow = string_row_of(handler) if handler else None
        asset = cstr(exe, SCENE_ASSET_TABLE + srow * STRIDE) if srow is not None else ""
        gfx = cstr(exe, GFX_TABLE + srow * STRIDE) if srow is not None else ""
        vab_dir, _, prefix = asset.partition("\\")

        # the LEVEL DATA selector -- arithmetic, independent of the string table
        disc_dir_num = scene_id if scene_id <= 10 else scene_id - 10
        disc_dir = "level%02d" % disc_dir_num
        dat_name = "LEVEL.DAT" if scene_id <= 10 else "LEVEL1.DAT"
        bin_name = "LEVEL.BIN" if scene_id <= 10 else "LEVEL1.BIN"
        raw_name = "LEVEL.RAW" if scene_id <= 10 else "LEVEL1.RAW"

        ovl_tag = disc_dir.upper()
        ovl_pair = sorted(k for k in overlays if k.startswith(ovl_tag + "_"))
        stages = scene_to_stage.get(scene_id, [])
        row = {
            "scene_id": scene_id,
            "dispatch_handler": "0x%08X" % handler if handler else None,
            "string_row": srow,
            "vab_entry": asset,
            "vab_dir": vab_dir,
            "asset_prefix": prefix,
            "loading_screen": gfx,
            "disc_dir": disc_dir,
            "level_data": {"dat": dat_name, "bin": bin_name, "raw": raw_name},
            # independent cross-check: for every campaign scene the VAB directory
            # must equal the arithmetically derived directory. It does, 15/15.
            "vab_dir_matches_disc_dir": (vab_dir == disc_dir) if vab_dir else None,
            "overlays": {k: len(overlays[k]) for k in ovl_pair},
            "phase2_stage_labels": stages,
        }
        if scene_id <= ROWS:
            if not ovl_pair:
                gaps.append(f"scene {scene_id} ({disc_dir}): no overlay in the census "
                            f"for {ovl_tag}")
            if not stages:
                gaps.append(f"scene {scene_id} ({disc_dir}): no Phase-2 stage movie "
                            "resolves to this scene")
            if row["vab_dir_matches_disc_dir"] is False:
                gaps.append(f"scene {scene_id}: VAB dir {vab_dir} != disc dir {disc_dir}")
        rows[f"scene_{scene_id:02d}"] = row

    # scenes the Phase-2 oracle SAW that this table cannot explain
    off_table = {s: labels for s, labels in scene_to_stage.items()
                 if not (1 <= s <= ROWS)}
    exceptional_routes = []
    for s, labels in off_table.items():
        if s == 17 and labels == ["training"]:
            # Training is not a missing row in the 15-entry campaign string
            # table.  It is an explicit exceptional route: scene-1-based index
            # 16 in the 17-entry resource dispatcher shares the default handler,
            # while its centrally pinned resources live under LEVEL00 and its
            # loading screen is the separate EXE string gfx\training.raw.
            resource = jr["decoded"]["0x8003CFBC"]
            target = next(row for row in resource["targets"] if row["index"] == 16)
            staged = baseline["staged_inputs"]
            assets = {
                path: staged[path] for path in sorted(staged)
                if path.startswith("LEVEL00/") or path == "GFX/TRAINING.RAW"
            }
            exceptional_routes.append({
                "scene": 17,
                "stage_labels": labels,
                "owner": "resource_id_dat_load_dispatcher + resident scene handler 17",
                "route": {
                    "resource_dispatch_table": "0x8001AFB0",
                    "resource_dispatch_index": 16,
                    "resource_dispatch_target": target["target"],
                    "disc_directory": "LEVEL00",
                    "loading_screen": "gfx\\training.raw",
                    "overlay_semantics": "LEVEL00/LEVEL.BIN is a pinned 4-byte sentinel, not a Region-A code overlay; Training uses the resident/shared route plus LEVEL00 data",
                },
                "assets": assets,
                "evidence": [
                    "analysis/phase2_completion_oracle.json:stages.training",
                    "analysis/phase3_jr_tables.json:decoded.0x8003CFBC",
                    "tools/build_baselines.json:staged_inputs.LEVEL00",
                    "REBUILD/files/SCUS_942.88 string at 0x8001AF98",
                ],
            })
        else:
            gaps.append(f"scene {s} ({', '.join(labels)}) is OFF-TABLE and has "
                        "no exceptional route mapping")

    bins = []
    for i in range(8):
        s = cstr(exe, LEVEL_BIN_TABLE + i * 0x0C, 0x0C)
        if not s or not s.startswith("level"):
            break
        bins.append(s)

    doc = {
        "_comment": "Phase-3 WP7 scene->asset->overlay load graph, decoded from "
                    "the pristine EXE tables and cross-verified against the "
                    "Phase-2 completion oracle's observed scene ids. Gaps are "
                    "computed. Regenerate: tools/phase3_scene_asset_graph.py "
                    "(needs the LOCAL EXE).",
        "generated": date.today().isoformat(),
        "fixture_sha256": fixture_pin("REBUILD/files/SCUS_942.88"),
        "tables": {
            "scene_asset_table": {"address": f"0x{SCENE_ASSET_TABLE:08X}",
                                  "rows": ROWS, "stride": STRIDE,
                                  **CONSUMERS["scene_asset_table"]},
            "gfx_loadscreen_table": {"address": f"0x{GFX_TABLE:08X}",
                                     "rows": ROWS, "stride": STRIDE,
                                     **CONSUMERS["gfx_loadscreen_table"]},
            "level_bin_table": {"address": f"0x{LEVEL_BIN_TABLE:08X}",
                                "entries": bins,
                                **CONSUMERS["level_bin_table"]},
        },
        "law": "CORRECTED 2026-08-01. The dispatcher validates 1 <= scene_id <= 17 "
               "(0x8003CF84/0x8003CF88) and jumps through a PERMUTED jr table at "
               "0x8001AFB0 indexed by scene_id-1; the string each handler reaches is a "
               "VAB/sound-bank prefix, NOT level data. The level data is selected "
               "arithmetically at 0x8003D204..0x8003D21C: dir = scene_id <= 10 ? "
               "scene_id : scene_id - 10, and the file-name variant flips to the '1' "
               "form for scene_id >= 11 (flags 0x140 into 0x800823AC). So each disc "
               "directory hosts TWO scenes, d and d+10, as LEVEL.* and LEVEL1.*. "
               "The prior law 'row index = scene_id - 1' was an assumption in this "
               "generator, never derived from code, and is wrong for 11 of 15 scenes. "
               "Cross-check: with the permutation, the VAB directory equals the "
               "arithmetically derived directory for all 15 campaign scenes.",
        "operator_level_numbering": "the campaign progression table at 0x80077FA0 maps "
               "the player-facing level ordinal to scene_id: "
               "[17, 1, 3, 2, 6, 10, 11, 4, 5, 14, 7, 12, 13, 9, 8, 15, -1]. "
               "Ordinal 0 = training (scene 17); ordinal 6 = scene 11 = LEVEL01/LEVEL1.DAT.",
        "scenes": rows,
        "overlay_inventory": {k: len(v) for k, v in sorted(overlays.items())},
        "exceptional_routes": exceptional_routes,
        "unload_graph": {
            "entry": {
                "owner": "scene_load_init/resource dispatcher then world-ready population",
                "evidence": "analysis/phase3_transition_reset.json",
                "law": "scene id flips 450..1170 frames before the actor roster and player state are ready",
            },
            "exit": {
                "owner": "transition orchestrator",
                "evidence": "analysis/phase3_transition_reset.json:laws.exit_reclaims_world=false",
                "law": "exit does not reclaim actor/plant/contact bytes; the old world remains stale in RAM",
            },
            "overwrite": {
                "owner": "next scene resource load",
                "evidence": "analysis/phase3_transition_reset.json",
                "law": "the next load overwrites world-owned records; session-owned player fields carry across",
            },
            "exceptions": [
                {"scene": 17, "law": "Training shares scene 1's SOUND BANK via jr index 16 "
                                     "(0x8001AFB0[16] = 0x8003CFC4), but its level data is "
                                     "LEVEL07/LEVEL1.* by the same arithmetic law -- NOT "
                                     "LEVEL00. Corroborated by tools/training_board_edit.py "
                                     "and tools/patch_training_overlay.py, which already "
                                     "target LEVEL07/LEVEL1.*, and by LEVEL00/LEVEL.DAT "
                                     "having zero type-0x3f entries."},
                {"scene": 9, "law": "Bug Bar loads no actor roster"},
                {"scope": "four stages", "law": "health becomes ready after the roster; world-ready needs both signals"},
            ],
            "observed_exit_reclaims_world": transition["laws"]["exit_reclaims_world"],
        },
        "gaps": gaps,
    }
    path = ROOT / "analysis" / "phase3_scene_asset_graph.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[scene-graph] {ROWS} scenes decoded; "
          f"{sum(1 for r in rows.values() if r['phase2_stage_labels'])} "
          f"cross-verified by Phase-2 movies; {len(gaps)} gaps")
    for g in gaps:
        print(f"  GAP {g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
