---
kind: experiment
id: EXP_2026-08-03_phase4_c15_respawn_anchor
status: complete
source_state: original_game
system: [FUNC_80054C90, FUNC_8005B134]
row: C15_respawn_anchor
---

# Phase 4 C15: death respawn-anchor selection, resolved

## Question

Operator, directly: "sometime the death spawns Flik somewhere pre-determined, like in
cliffside with the bird, was this banked or no" — then "go for C15 and do it until you
completely deem it bound exhausted." The row's own long-standing ambiguity: does death
respawn use the continuously-maintained "safe anchor" or fall back to the level's fixed
scene-entry spawn table? And does it differ by death class?

## The general rule, resolved

Death respawn **always** uses the safe anchor. `FUNC_8005B134` (the respawn/transition state
handler, states `v0∈[3,10]`) has a common tail (`0x8005b1bc..0x8005b2dc`) that unconditionally
reads the anchor (`0x800A6550/54/58`) and writes it into the live position
(`0x800A6500/04/08`) plus the previous/render copy, then zeroes a large block of player
state. The scene spawn table (`FUNC_80046B20` via `FUNC_8005B714`) is used **only** at level
entry — there is no "fallback to the table" path for death specifically. This was already
documented in an archived (superseded but provenance-preserved) Canon page, cross-checked
against the current thin page and found consistent.

## The anchor-update gate, fully decoded and cross-verified

`FUNC_80054C90` (already hand-reconstructed, and independently cross-checked instruction-
for-instruction against the raw pristine ASM listing this pass) conditionally copies live
player XYZ into the anchor. All of these must hold:

- player `+0x82` (`0x800A6582`) nonzero
- transition timer `0x80082470` == 0
- helper `0x80038e48` returns 0
- player `+0x84` (`0x800A6584`) == 0
- **scene_id (`0x80082504`) != 6**
- helper `0x80038f84` returns nonzero
- helper `0x80038f38` does not return 4
- a 64-record proximity scan over the enemy pool rejects the update if too close to certain
  flagged actors

The `scene_id != 6` check is a literal, unconditional branch in resident code — verified
directly against the raw ASM (`lw v1,0x2504(v1)` / `addiu v0,zero,6` / `beq v1,v0,exit`).
Scene 6 is `F04_cliffside_canyon`.

## Live verification — the frozen anchor

Reused the pre-existing `D17_Cliffside_Bird_Death.movie.json` (already Interpreter-recorded,
527 frames). Sampled the anchor every 40 frames across the whole movie: it stays **exactly**
`(93783,-83752,-134554)` from frame 0 through frame 440, while Flik's actual position moves
thousands of units. Direct, live proof the exclusion holds through real gameplay, not just a
code-reading inference.

**Contrast, a normal scene**: loaded `level01.sav` (scene 1) directly, held "up" for 300
frames. The anchor updated from `(197091,2734,492897)` to `(53096,-4116,602364)`, closely
tracking the new live position — confirming the general continuous-tracking rule holds
outside scene 6.

## Live verification — the death moment itself

Narrowed to 2-frame resolution around the documented respawn-commit frame (448): at the exact
frame lives drop `9→8`, **both** the anchor and live position jump to the identical value
`(35329,-85228,-154696)` simultaneously. Armed `accessLog` write-watches on both addresses and
pinned the exact writer: PC `0x800B3B00`/`0x800B3B24`/`0x800B3B3C`, inside a clean,
exact-bounded 544-byte **overlay** function (`0x800B39A4..0x800B3BC0`).

Disassembling that function shows the written values are **hardcoded literal constants**
(`ori v1,zero,0x8a01` = 35329, built via `lui`/`ori` immediate construction) — not derived
from Flik's own prior position, not the scene's entry-anchor value, not a table lookup. This
is a third, independent mechanism: **the bird encounter's own overlay code plants a
pre-authored "safe landing" coordinate directly into the anchor as part of its own death
handling**, bypassing both the (excluded) continuous update and the level-entry table
entirely.

## Direct answer to the operator's question

**Yes, now banked.** Cliffside's "pre-determined" respawn isn't because death respawn
generally uses a fixed table — it doesn't; the general rule is the continuously-tracked safe
anchor. Cliffside is a documented special case: its scene is hard-excluded from the anchor's
continuous update, and the bird hazard's own overlay hardcodes a specific safe-landing
coordinate into the anchor at the exact death moment.

## What's still open

The exact semantic meaning of several individual gate conditions (inferred from structure,
not independently proven); the precise enemy id/flag criteria in the 64-record proximity
exclusion; whether other levels have similar hazard-specific hardcoded overlay overrides
(plausible by analogy, not tested — low-return campaign breadth unless a specific row needs
it); the bird's own paired-teleport write target (adjacent in the same overlay, not fully
decoded — out of C15's own scope).

## Evidence

`analysis/phase4_c15_respawn_anchor.json`; static source
`asm/hand_written/80054c90_checkpoint_save.s` (cross-verified against
`asm/nonmatchings/resident/80054c90.s`); archived provenance
`ObsidianVault/Archive/Superseded/Functions_FUNC_8005B134.md`; reused fixture
`movies/Phase4/Interpreter/D17_Cliffside_Bird_Death.movie.json`.
