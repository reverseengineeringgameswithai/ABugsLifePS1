---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8004ABF4.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8004ABF4.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8004ABF4_unnamed.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8004ABF4
type: function
addr: 0x8004abf4
confidence: CONFIRMED (static decode + runtime behaviour) / actor role LIKELY
tags: [function, gameplay, warp, transition, milestone6, gap-0033, gap-0035, runtime]
updated: 2026-06-21
---

# FUNC_8004ABF4 — per-tick transition/phase updater (type-6 warp commit)

> Enclosing function of the `[0x800823a0]=6` store at `0x8004b3c0` (the type-6 level-exit lever).
> **Runtime CORRECTS the prior "one-shot resident initiator" framing: this runs EVERY gameplay tick**
> and the type-6 commit is a *dormant countdown branch*. Static decode (`tools/exe_read.py`) + runtime
> (isolated DuckStation, `level02.sav`) — **runtime is LOCAL-ONLY** ([[DuckStation Fork Reproducibility]] / GAP-0001).

## How it is reached — the native gameplay gate `0x8004f0e8`
In the gameplay update path (right after the scene-verb dispatch `0x80054964` at `0x8004f038`), at
**`0x8004f0e8`**: `jal 0x8004abf4` is called **iff** `[0x800a657c]==0` **and** `[0x800a6594]≥0`
(`0x8004f0c0`-`0x8004f0e0`; plus a `scene_id==17` special case reading overlay-local `[0x800b4a3c]`).

**RUNTIME (local-only):** during normal LEVEL play (`level02.sav`, scene 3) those fields read
`[0x800a657c]=0`, `[0x800a6594]=4` ⇒ **gate OPEN**, and `0x8004abf4` **is invoked every tick with no
transition**. So `[0x800a657c]/[0x800a6594]` are a *"transitions-allowed this tick"* precondition,
**NOT the level-exit trigger** (the earlier static guess that they were the exit condition is corrected).

## Body — operates on the active special-actor `[0x80090748]`
- Entry: `s1 = [0x80090748]` (a shared actor pointer); **`beq s1,zero → 0x8004b6a8` (early-exit)**.
- **RUNTIME (local-only):** `[0x80090748] = 0` (NULL) in mid-level saves ⇒ it early-exits every tick;
  that is why the countdown stays dormant and `[0x8008223c]` is never written during play.
- When non-null: computes **player-relative squared distances** (`(actor+0x4/0x8/0xc − ref)>>5`,
  `mult`; ref = player `0x800a6500` cluster) — i.e. a **proximity** computation.
- `[0x80090748]` = a shared "active special actor" pointer (2 writers, both `sw zero`: load-clear
  `0x8003a49c`, transition-clear `0x8004a4b4`; 7 readers across spawn/pickup/transition/death;
  non-null assignment is an indirect pointer-store in the DAT-parse/spawn region — not yet pinned).

## The type-6 commit = a 5-tick countdown `[0x8008223c]`
The warp commit branch (`0x8004b38c`) is gated by **`[0x8009b889]&0x20==0`** and **`scene_id!=16`**
(`0x8004b35c`-`0x8004b384`); then it **reads `[0x8008223c]`, increments it** (`0x8004b3a8`), and **only
when it reaches 5** (was 4): sets `[0x80082444]=oldsub+0x72`, **`[0x800823a0]=6`** (`0x8004b3c0`),
`[0x80082470]=30` (fade), and resets `[0x8008223c]=0`. `[0x8008223c]` has 6 reset-to-0 writers + this
one incrementer.
- **RUNTIME (local-only):** `[0x8008223c]` rests at 0 with **zero writers across 3 play frames**;
  forcing `[0x8008223c]=4` did **nothing** (incrementer never fired) ⇒ the countdown branch is reached
  only when the upstream actor/proximity/flag conditions hold, which they do not in normal play.

## Writes (the type-6 arm carries NO destination)
Only `[0x80082444]`, `[0x800823a0]=6`, `[0x80082470]=30`. **No scene-index / scene-id / resource write.**
The destination is resolved later by the shell SM (`0x8004fda0`: `scene_table[ [0x8008245c] ]`, or forced
to scene **16** when `[0x8008225c]!=0`) — see [[Gameplay - Warp and Level Transition]]. This is why a
raw forced `[0x800823a0]=6` has no real destination → scene-16 crash ([[Experiment - In-game warp trigger]]).

## Confidence
- Gate `0x8004f0e8`, body structure, countdown `[0x8008223c]`→5 commit, no-destination write —
  **CONFIRMED (static, EXE-read)**.
- "runs every tick / gate open in play / `[0x80090748]` null mid-level / countdown dormant" —
  **CONFIRMED (runtime, LOCAL-ONLY GAP-0001)**.
- "`[0x80090748]` = exit/goal-trigger actor, proximity-gated arm" — **LIKELY** (distance computation +
  warp-countdown structure; the exact distance gate not yet pinned).

## Related
[[FUNC_8004A700]] · [[Gameplay - Warp and Level Transition]] · [[Gameplay - Events and Triggers]] · [[Experiment - In-game warp trigger]] · [[FUNC_8005222C]] · [[FUNC_8005B714]] · [[MEM - Player state 800A6500]] · `tools/exe_read.py`
