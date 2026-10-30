---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Level Goal and Exit Trigger Matrix.md
aliases:
  - "Level Goal and Exit Trigger Matrix"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Level Goal and Exit Trigger Matrix.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Level_Goal_and_Exit_Trigger_Matrix.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Level Goal and Exit Trigger Matrix
type: system
status: active baseline
updated: 2026-07-02
confidence: RUNTIME-SAVE-STATE + LIVE-PROBE
tags: [system, gameplay, exits, collision, rcg-003]
---

# Level Goal and Exit Trigger Matrix

> Runtime-save-state catalog for [[Retail Gameplay Completeness Gap Audit]] `RCG-003`. The mechanism is the LEVEL01-proven collision-sector region-code path: `FUNC_80048138` calls `FUNC_80038f38(0,&Flik+0x82)`, which reads `0x800A7E48 + sector*0x30 + 0x2E`. Source anchor: `src_re/level_goal_trigger_catalog.c`; generator: `tools/level_goal_trigger_catalog.py`.

## Evidence Boundary

- Uses DuckStation v84 save-state headers and zstd state blocks; extracts only the in-memory `Bus` main-RAM block.
- Scans `0x800A7E48` with stride `0x30` and keeps codes `1..4` only when origin coordinates and plane pointers look like real collision sectors.
- This identifies the native sector-trigger surfaces present at each save-state anchor. It does not prove boss HP, cutscene, harvester, or overlay objective success logic.
- Live route proof uses DuckStation external debugger on pristine `SCUS-94288`, load-state validation enabled, internal controller input only, and an access watch on transition latch `0x800823A0`.
- Save states are all `SCUS-94288`; only SHA-256 prefixes are recorded here.

## Region-Code Semantics

| Code | Current meaning | Confidence |
|---:|---|---|
| 1 | Calls `FUNC_8004A700` type-2 transition path from `FUNC_80048138` | Resident dispatch decoded; per-level destination semantics still open |
| 2 | Type-1 level exit body: `[0x800823A0]=1`, fade color `23`, `FUNC_80050994(58,0)` | Live-proven on LEVEL01; present again in stage 8 save-state table |
| 3 | Resident dispatch has a nonzero case; appears as terminal/goal-adjacent marker in several stages | Semantics unresolved |
| 4 | Resident dispatch has a nonzero case; appears as a cluster in stage 4 | Semantics unresolved |

## Save-State Trigger Matrix

| Save | Scene | Stage dir | Overlay | Current sector/code | Trigger sectors |
|---|---:|---|---|---|---|
| `level01.sav` | 1 | `LEVEL01` | `LEVEL1A` | 99/`0` | `177:code2` @ (-163008,-169888,-124832) |
| `level01_end_of_stage.sav` | 1 | `LEVEL01` | `LEVEL1A` | 119/`0` | `177:code2` @ (-163008,-169888,-124832) |
| `level01_lookingdown_flatground.sav` | 1 | `LEVEL01` | `LEVEL1A` | 106/`0` | `177:code2` @ (-163008,-169888,-124832) |
| `level02.sav` | 3 | `LEVEL02` | `LEVEL1C` | 548/`0` | `570:code1` @ (176352,64224,117088), `571:code1` @ (470112,64224,-423840), `572:code1` @ (471712,64224,537728), `573:code1` @ (1111712,64224,1336128), `574:code1` @ (1174240,64224,1961280), `575:code1` @ (1615424,64224,2512384), `576:code1` @ (816864,64224,277568), `577:code1` @ (1454496,64224,1397760), `578:code1` @ (811616,59552,593280), `579:code3` @ (1864160,35520,2916480) |
| `level03.sav` | 2 | `LEVEL03` | `LEVEL1B` | 92/`0` | none exposed at this anchor |
| `level04.sav` | 6 | `LEVEL01` | `LEVEL2C` | 84/`0` | `131:code3` @ (-1719040,39424,-219488) |
| `level05.sav` | 10 | `LEVEL07` | `LEVEL4A` | 245/`0` | `292:code1` @ (285312,23328,920384), `293:code1` @ (397440,28256,917952), `294:code1` @ (-199872,23264,1148032), `295:code1` @ (-361024,35136,524960), `296:code1` @ (-39776,22720,957280), `297:code3` @ (135168,-896,2075328) |
| `level_06.sav` | 11 | `LEVEL02` | `LEVEL4B` | 48/`0` | none exposed at this anchor |
| `level_07.sav` | 4 | `LEVEL06` | `LEVEL2A` | 74/`0` | `219:code1` @ (714912,27648,74784), `220:code4` @ (140928,1120,157792), `221:code4` @ (152192,1888,83744), `222:code4` @ (336256,0,204512), `223:code4` @ (497440,-3968,44288), `224:code4` @ (583872,-5920,-288), `225:code4` @ (-72384,1568,-103360) |
| `level_08.sav` | 5 | `LEVEL10` | `LEVEL2B` | 154/`?` | none exposed at this anchor |
| `level_09.sav` | 14 | `LEVEL08` | `LEVEL5B` | 0/`0` | none exposed at this anchor |
| `level_10.sav` | 7 | `LEVEL04` | `LEVEL3A` | 101/`?` | none exposed at this anchor |
| `level_11.sav` | 12 | `LEVEL03` | `LEVEL4C` | 180/`?` | none exposed at this anchor |
| `level_12.sav` | 13 | `LEVEL09` | `LEVEL5A` | 7/`0` | none exposed at this anchor |
| `level_13.sav` | 9 | `LEVEL04` | `LEVEL3C` | 118/`0` | none exposed at this anchor |
| `level_14.sav` | 8 | `LEVEL05` | `LEVEL3B` | 0/`0` | `334:code2` @ (1198912,-116448,4879104) |
| `level_15.sav` | 15 | `LEVEL05` | `LEVEL5C` | 276/`0` | none exposed at this anchor |

## Interpretation

- `level01*.sav` confirms the already-solved stage-1 exit sector `177:code2`.
- `level02.sav` (scene 3 / `LEVEL02`, stage `LEVEL1C`) exposes a large code-1 cluster at sectors `570..578` and a code-3 sector `579`; this matches the prior deep collision-map note that this scene has hundreds of sectors.
- `level04.sav` and `level05.sav` expose single/clustered code-3 endpoints; `level_07.sav` exposes code-1 plus code-4 cluster; `level_14.sav` exposes a code-2 exit-like sector.
- Many stage-start saves expose no nonzero sector triggers at the start anchor. That means the sector mechanism is absent from the loaded table at that anchor or is elsewhere in the level; it does not prove the level lacks a goal.

## Objective Scope Refinement

Operator classification (2026-07-02): the non-boss retail endings split into a simple **"be here"** lane and a conditional collection/rescue lane. Do **not** pursue the conditional endings in the current RCG-003 pass.

| Level | Ending class | Current handling |
|---|---|---|
| `LEVEL02` | Be-here ending | In scope for the current sector-trigger proof lane. |
| `LEVEL04` | Be-here ending | In scope for the current sector-trigger proof lane. |
| `LEVEL05` | Be-here ending | In scope for the current sector-trigger proof lane. |
| `LEVEL14` | Be-here ending | In scope for the current sector-trigger proof lane. |
| `LEVEL07` | Conditional character contact | Out of scope for now: Flik must walk into Heimlich, Slim, or Francis. |
| `LEVEL08` | Conditional multi-character contact | Out of scope for now: Flik must walk into Dim, Rosie, Manny, and Tuck&Roll; order can vary. |
| `LEVEL10` | Conditional collection | Out of scope for now: bird parts `_1`..`_5` can be collected in any order. |
| `LEVEL11` | Conditional scouts + Dot | Out of scope for now: interact with all 5 ant scouts in any order, then jump into Dot last. |
| `LEVEL13` | Conditional Atta rescue | Out of scope for now: walk into Atta after forcing Hopper to let her go; Hopper-forces-Atta setup is explicitly outside this pass. |

## Be-Here Live Route Proof

Tool: `tools/prove_be_here_endings.py`; capture: `build/rcg003_be_here_probe.json`. Disc: `~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue`, serial `SCUS-94288`. Each run loads the endpoint save, drives DuckStation controller state, advances under `accessLog.run`, and watches writes to `0x800823A0`.

Access-log attribution note: on current DuckStation builds, use `instruction_pc` / `instruction` from `accessLog.get` for the true store and keep `reported_pc` only as the callback PC. Older captures in this note predate that field and therefore used the old `pc-4` correction.

| Level | Save | Input script | Live result |
|---|---|---|---|
| `LEVEL02` | `LEVEL02_ENDING.sav` | Hold `UP` for 300 frames | Enters sector `579`; transition latch becomes `1`; watch records `0x800823A0` write at reported `pc=0x800496fc`, true store `0x800496f8`. |
| `LEVEL04` | `LEVEL04_ENDING.sav` | Hold `UP` for 300 frames | Enters sector `131`; transition latch becomes `1`; watch records `0x800823A0` write at reported `pc=0x800496fc`, true store `0x800496f8`. |
| `LEVEL05` | `LEVEL05_ENDING.sav` | Hold `UP` for 300 frames | Enters sector `297`; transition latch becomes `1`; watch records `0x800823A0` write at reported `pc=0x800496fc`, true store `0x800496f8`. |
| `LEVEL14` | `LEVEL14_ENDING_1.sav` | Press `START` for 6 frames, then hold `UP` for 300 frames | Transition latch becomes `1`; watch records `0x800823A0` write at reported `pc=0x800496dc`, true store `0x800496d8`. Final sampled sector was `242`, so this is latch-path proof rather than sector-334 route proof. |

Instruction attribution:

- `0x800496f8`: `sh v0, 0x23a0(at)` after `v0=1`, followed by fade color setup at `0x80049700..0x80049704` and `jal 0x80050994`.
- `0x800496d8`: same latch store in the adjacent resident exit branch; it jumps into the shared fade/SFX tail at `0x80049700`.

## Residual RCG-003 Work

- The simple be-here endings are live-proven as completion-latch routes for `LEVEL02`, `LEVEL04`, `LEVEL05`, and `LEVEL14`.
- Decode resident cases for codes `3` and `4` and the `FUNC_8004A700` destination/resource semantics for code `1`.
- Keep conditional endings and boss/special objective success as separate follow-up gaps; those are not sector-table-only exits.
- Trace the converter/source mapping for every non-LEVEL01 table if source-side editing of these triggers is required. Runtime indices are now known for the save-state anchors; exact disc-source record offsets are not yet proven for every level.

## Tool Output

```bash
python3 tools/level_goal_trigger_catalog.py --root . --json build/level_goal_trigger_catalog.json --markdown 'ObsidianVault/Systems/Level Goal and Exit Trigger Matrix.md'
python3 tools/prove_be_here_endings.py --root ~/Downloads/ABL --frames 300 --out build/rcg003_be_here_probe.json
```
