---
type: experiment
status: complete
date: 2026-08-10
system: collision region codes / level exit + hazard triggers
phase: 4
artifacts:
  - analysis/phase4_e02_disc_region_code_census.json
  - tools/phase4_e02_disc_region_code_census.py
  - tools/edit_sector_region_code.py
---

# Disc-side region-code census: 16/16 scenes, and code 3 is not dead

## Verdict

Every authored region code in shipped terrain, read from each scene's **own
container**, diffed against the runtime table: **16/16 scenes located, 3,235 authored
sectors compared, 0 disagreements.** Before this, the disc side was cross-checked for
**LEVEL01 alone**.

## The blocker was not real

F01's task queue recorded this as "blocked on a per-level locator for the sector
source array", to be recovered from the converter `FUNC_80030F60`. **That locator had
been committed six days earlier.** `analysis/phase4_e02_collision_roundtrip.json`
(2026-08-04) already binds all 16 scenes to their container *and* the array's offset
inside it, `failing_levels: []`, proven by an independent C reimplementation of the
converter diffed against save RAM.

⚠️ **Second occurrence of this pattern**, after `phase3_jr_tables.json` (869 decoded
indirect targets the static index never read). **Grep `analysis/` before building a
locator, extractor or census.**

## Why 15 levels looked code-free

`tools/edit_sector_region_code.py` hardcoded LEVEL01's `(chunk 32, local 0x36570)`.
**Both coordinates vary per level** — the chunk index alone ranges over 27–33, and
four scenes keep the array in a flat `.ALL` container with no chunks at all. Pointed
anywhere else the tool walked garbage and printed **nothing**.

The earlier diagnosis ("LEVEL03's chunk 32 is 4,936 B") named the right symptom but
half the cause: LEVEL03's array is in **chunk 28**, not a differently-sized chunk 32.

> ⚡ **A tool that reports nothing is not a negative result** until it has been shown
> to report something on a known-positive input.

Now hardened: an unrecognised container is a **hard error listing the known ones**,
never silence. LEVEL01 keeps its independently established constants and the locator
must agree with them, so the runtime census's LEVEL01 cross-check stays an outside
check rather than a restatement.

## Method, and why it is not circular

Per scene: re-locate the authored array in its container, read the authored region
code at **`src+0x2C`** straight from the container bytes, diff against the runtime
table's **`+0x2E`** for the same sector index (the converter law, writers
`0x80030F94` / `0x80031264`).

**The alignment is fixed by sector ORIGINS (`+0x08`), never by the code field at
`+0x2C`.** The field being checked takes no part in choosing the alignment, so
agreement is a real check of the converter law rather than a restatement of it.

**Self-validating:** the tool independently derives LEVEL01 = **chunk 32, local
`0x36570`** — the exact pair that had been hardcoded.

**Complete, not a subset:** the 720 runtime-registered tail sectors carry **zero**
nonzero codes (`runtime_nonzero_beyond_authored` empty in all 16), so the authored
prefix is the entire code population.

## The census

| level | scene | container | chunk | local | authored | nonzero |
|---|---:|---|---:|---|---:|---|
| training | 17 | LEVEL07/LEVEL1.RAW | 33 | `0xbd80` | 25 | 24:3 |
| anthill | 1 | LEVEL01/LEVEL.RAW | 32 | `0x36570` | 178 | 177:2 |
| tunnels | 3 | LEVEL03/LEVEL.RAW | 28 | `0x36890` | 589 | 570‑578:1, 579:3 |
| council chamber | 2 | LEVEL02/LEVEL.RAW | 28 | `0x120e0` | 100 | — |
| cliffside canyon | 6 | LEVEL06/LEVEL.RAW | 30 | `0x2915c` | 132 | 131:3 |
| riverbed run | 10 | LEVEL10/LEVEL.RAW | 31 | `0x1d2ac` | 298 | 292‑296:1, 297:3 |
| birdnest | 11 | LEVEL01/LEVEL1.RAW | 29 | `0xd99c` | 75 | — |
| city entrance | 4 | LEVEL04/LEVEL.RAW | 31 | `0x2cdfc` | 229 | 219:1, 220‑225:4 |
| city square | 5 | LEVEL05/TERRAIN.ALL | flat | `0x28034` | 333 | — |
| bug bar | 14 | LEVEL04/LEVEL1.RAW | 27 | `0x41dc` | 1 | — |
| clover forest | 7 | LEVEL07/TERRAIN.ALL | flat | `0x1d34c` | 138 | — |
| the tree | 12 | LEVEL02/TERR1.ALL | flat | `0x30cd4` | 262 | — |
| battle arena | 13 | LEVEL03/LEVEL1.RAW | 31 | `0x5b04` | 12 | — |
| anthill pt2 | 9 | LEVEL09/LEVEL.RAW | 31 | `0x2f2e4` | 176 | — |
| riverbed flight | 8 | LEVEL08/LEVEL.RAW | 31 | `0x2b1b0` | 335 | 334:2 |
| canyon showdown | 15 | LEVEL05/LEVEL1.RAW | 31 | `0x29c54` | 352 | — |

Authored histogram **0:3208, 1:15, 2:2, 3:4, 4:6** — nonzero counts equal the runtime
census exactly.

## ⚡ Code 3 is not dead code

It is the ordinary **exit trigger** of four stages: training (s24), tunnels (s579),
cliffside canyon (s131), riverbed run (s297).

⚠️ **CORRECTION, same day.** This page first said code 3 "had never been observed
firing". Wrong — I generalised the F01/E10 exec-watch result (which watched the arm
entry `0x800496E8`) to the whole corpus. The 100% corpus write-watch sweep **did**
observe it: writer PC `0x800496FC` for request value 1 pairs with the code-3 arm's
store at `0x800496F8` (store PC + 4; neither reported PC is itself a store). Arm 3 is
**live at runtime**. Still not established: a direct exec hit on `0x800496E8`, and
which levels drove the writes — the sweep does not break writers down per level.

**E10's campaign-wide instant-kill census is served:** code 1 = **15 sectors** —
scene 3 ×9, scene 10 ×5, scene 4 ×1 — and nowhere else in shipped terrain. Code 4
(goo, damage-only, suppresses checkpointing) = 6 sectors, all scene 4.

**Structural law, true in all 7 code-bearing scenes:** every nonzero code lives in a
single contiguous band at or near the **end** of the authored array — hazard and exit
sectors are appended after the terrain proper. A cheap sanity check on any future edit.

## Universe named

Scene ids are valid **1..17** (`0x8003CF84`: `addiu v1,s4,-1` / `sltiu v0,v1,17`). The
progression table `0x80077FA0` lists 16, and the census covers those **16 of 17**.
Scene **16** is uncovered — absent from the table, reached only via the force flag
`[0x8008225C]` (map/results), and it has no save anchor. A named residual, not a
silence.

Related: [[EXP_2026-08-03_phase4_e02_region_codes]] ·
[[Level_Goal_and_Exit_Trigger_Matrix]] · [[EXP_2026-08-05_phase4_f01_objective_lifecycle]]
