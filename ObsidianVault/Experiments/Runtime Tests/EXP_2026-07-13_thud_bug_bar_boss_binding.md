---
node_type: experiment
title: "EXP — F09/Thud (Bug Bar boss) bound by poke-falsification"
date: 2026-07-13
status: partial
result: bound
phase: 3
mechanic: F09_bug_bar
tags: [phase3, boss, enemy, poke-falsification]
---

# F09 / D18 — Thud (Stage-9 Bug Bar boss) bound from the running game

**Result: BOUND** (boss identity, damage path, and defeat mechanism), `partial`
(the rolling-arena transform and Thud's multi-phase attack program are still open).
Thud is setpiece/trigger-spawned — Bug Bar's chunk-31 record table is all-zero — so
a static binding is impossible; this is a live poke-falsification, following the
decoded sibling boss Thumper (`src_re/thumper_boss.c`) as the template.

## Method (poke-falsification, not breakpoint tracing)
Load the stage-9 arena (`level_09.sav`, scene 14), confirm mounted-media identity is
pristine SCUS-94288 after connecting, find the boss via the live enemy table, then
POKE its HP and watch the retire. Breakpoint-heavy tracing drifts under movie replay
(the Thumper lesson), so every claim is a poke that either reproduces the retire or
does not.

## Findings (`analysis/phase3_thud.json`, save sha256-pinned)
- **Identity**: sole live enemy in table `0x80090748`, actor **id 0x24 (36)**, HP
  **`+0x6e` = 50**, flags `+0x5c` bit `0x40` = berry-damageable (SYS berry→enemy
  damage, dispatch `0x8005905C`), bit `0x4000` = active/live.
- **Driver**: per-actor callback `+0x7c` = `0x8004A0F4`; movement via the mover-VM
  interpreter `FUNC_8004C13C` (program pointer at `+0x70`).
- **Defeat**: at HP `+0x6e` ≤ 0, the **`mover_updater` (`FUNC_8004D224`)** retires
  the boss — zeroes its slot in the live table `0x80090748` (`sw` @`0x8004D43C`) and
  clears the `+0x5c` active bit `0x4000` (`sh` @`0x8004D270`). **Poke-falsified both
  ways: HP=1 survives, HP=0 retires.**

## Guard & residual
Guard: `tests/test_phase3_thud.py` pins the verdict as computed from the artifact
(not hand-set). Residual (Phase 4): the rolling-arena transform and the mover-VM
attack-phase FSM at the program pointer are undecoded — `F09_bug_bar`/`D18_thud`
remain `partial`.

Canon result: [[SYS_thud_bug_bar_boss]].

Related: [[SYS_enemy_death_and_permanence]] · template boss: `src_re/thumper_boss.c`
