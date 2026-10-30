---
kind: system
id: SYS_bonus_stage
name: The bonus stage (scene 0x10) -- rules, layout variants, and reward
status: live_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-08-04_phase4_f16_f18_bonus_stage
  - analysis/phase4_f16_f18_bonus_stage.json
src_paths:
  - tools/phase4_f16_f18_bonus_stage.c
  - tools/phase4_f16_f18_bonus_runtime.py
  - tests/test_phase4_f16_f18_bonus_stage.py
patch_policy: safe_to_read
---

# SYS_bonus_stage

The stage the three hidden challenges take you to. This page is about the stage
itself; the challenges that unlock it are
[[SYS_bonus_unlock_challenges]].

**There is only one bonus stage.** All three challenges lead to scene `0x10`,
and which of its three layouts you get depends on **how many bonuses you have
already completed**, not on which challenge you just solved. Rows
`F16_bonus1_spiders`, `F17_bonus2_mushrooms` and `F18_bonus3_grasshoppers`
therefore share one answer rather than having three.

## The overlay

Scene `0x10` runs `LEVEL06/LEVEL1.BIN` at base `0x800B39A0` — 1,820 bytes,
455 words, structurally partitioned by the tool into 1 header word + 373 presumed
code + 81 data. Four return-delimited spans tile the presumed code range, and no
resolved direct branch or call from those spans targets the presumed data region.
Indirect control flow and semantic reachability are not closed. Confirmed two
independent ways: the Phase-3
scene-asset graph maps scene 16 to `level06`/`LEVEL1.BIN`. In the overlay census,
this blob contains the only two resolved direct overlay reads of bonus ordinal
`0x8009B88A`, at `0x800B3B38` and `0x800B3C9C`; its sibling `LEVEL06/LEVEL.BIN`
(scene 6, an ordinary stage in the same directory) has no resolved direct read.
The resident shell also reads the ordinal at `0x8004FFAC` and writes it at
`0x8004FFD0`. The overlay scan retains 4,967 unresolved-base accesses, including
129 in this blob.

**Correction history (2026-08-04 audit):** “the only image in the game that reads
the bonus ordinal” was factually false because the resident EXE reads it. The
corrected claim is limited to resolved direct overlay reads and retains the scanner
residual. The former “accounted for completely” claim also exceeded the tool: its
word partition is exhaustive, but its control-flow analysis is direct-target only.

| VA | words | role |
|---|---|---|
| `0x800B39A4` | 84 | installs a 51-entry pickup descriptor table at `0x80096B98` |
| `0x800B3AF4` | 15 | advances the goal token's UV animation frame |
| `0x800B3B30` | 90 | stage init: culls actors by variant |
| `0x800B3C98` | 184 | per-frame update: beacon, particles, completion test |

## The rule: reach the token

The entire stage is one predicate, evaluated every frame in `0x800B3C98`:

```
d² = Σ over x,y,z of ((flik[i] - target[i]) >> 8)²     ; sra 8, then mult
if (d² < 1600)  →  [0x800823A0] = 1 ; [0x80082470] = 30
```

`0x800823A0` is the shared transition latch, `0x80082470` the fade timer — that
store *is* the completion (`0x800B3F18` / `0x800B3F24`). The goal radius is 40
in shifted units.

**The decoded completion block has no timer, score, fail-state or enemy gate.** Its
resolved path tests the coarse distance, the existing transition latch and the goal
distance before writing completion. Actors the init leaves alive run on ordinary
resident code, so this does not exclude hazards or failure behavior supplied by
callees or resident systems.

**Correction history (2026-08-04 audit):** the former claim that none of those
conditions existed “anywhere in the overlay” exceeded a decoded-block analysis. The
completion-path negative is retained; the overlay-global negative is retracted.

Two conditions gate that test, and both skip it entirely:

- **Coarse gate.** The squared distance from `0x8009EC50` (a view reference
  point, sole writer `0x8004EC94`, written right after camera follow update
  `0x8004DF18` — **not** Flik) to the same target must be `<= 359,999`
  (`0x800B3D2C`/`0x800B3D30`, branch `0x800B3D50`). Observably live: it blocked
  78 frames of the verified run.
- **Already latched.** If `[0x800823A0]` is already `1`, skip — completion
  cannot fire twice (`0x800B3D5C`/`0x800B3D64`).

## The three layouts

`0x8009B88A` — the persisted **completion ordinal** — indexes a `0x10`-stride
table at `0x800B4070` and drives three culling branches in the init. Culling is
`actor+0x6E := 0` (HP) and `actor+0x62 := 10001` — the same two fields the acorn
retirement path uses in The Tree (there with `+0x62 := 5`), see
[[EXP_2026-08-04_phase4_f11_the_tree_scouts]].

| variant | actors kept | target (x, y, z) | beacon y | beacon rgb |
|---|---|---|---|---|
| 0 | 0..11 | −13187, −70036, −22421 | −70036 | 128, 32, 0 |
| 1 | 0..13 | −22349, −79705, 48945 | 18380 | 96, 112, 128 |
| 2 | 14..32 | 157232, −42406, 5891 | −42406 | 128, 96, 0 |

Branch pins: `0x800B3B54` (block A runs only when variant == 2, culling 0..11),
`0x800B3B94` (block B skipped when variant == 1, culling 12..13), `0x800B3C20`
(block C skipped when variant == 2, culling 14..32).

⚠️ Only **variant 0** has been observed running. Variants 1 and 2 are decoded
from the table and pinned in the image, but confirming them live needs a session
that completes two and three bonuses.

✅ **Operator-confirmed from play (2026-08-04):** the order does not matter — doing
mushrooms first goes to the same bonus stage as doing grasshoppers first, and so on.
That is precisely what selection by the completion *ordinal* predicts and what
selection by challenge identity forbids, so it is independent confirmation of the
binding above from outside the code.

## The token

The install function copies 51 words from `0x800B3FA4` over the pickup
kind→descriptor table at `0x80096B98`, and the last entry points back into the
blob at `0x800B3F78`. The update tail advances a counter at `0x800B40B8` masked
to `0..15`, indexing a 16-entry UV table at `0x800B3F84` (u steps `0x20` across
8 columns, then v steps to `0x40` — an 8×2 strip) and writing u/v at `+8`/`+9`
of that descriptor. So the bonus stage replaces the pickup table wholesale and
adds its own animated token as the last kind.

Per frame the update also emits a beacon via `0x80023544` at the target with the
per-variant RGB triple from `0x800B40A0[variant*6]`, appends a 16-byte entry to
the marker list at `0x800B1B58` (cap 47, count at `0x800824CA`), and — while the
shared update-inhibit byte `0x800910A3` is clear — calls `spawn_drop`
(`0x80059E44`) at the target jittered by 3 bytes taken from the rolling cursor
`0x800822F4`.

## The reward

In the resident shell, not the overlay:

```
[0x800823A0] == 6  →  gp+1220 (0x8008225C) := 1        ; 0x80050230, one-shot
...next scene...
gp+1220 set?       →  cleared immediately              ; 0x8004FF94
  latch != 1       →  reward skipped entirely          ; 0x8004FF98
  latch == 1       →  0x8009B889 := (flags & 0x0F) * 17
                      0x8009B88A += 1
                      fmv_bin_load(old_ordinal + 42)   ; 0x8004FFD4
```

The reward is **FMV 42/43/44 in completion order** — first, second or third
bonus, not which challenge. The tentative low bit the challenge set becomes
permanent only here: `(flags & 0x0F) * 17` mirrors the low nibble into the high
nibble, and the high bits are the already-earned guards.

**The restore block is not an else-branch.** No branch separates the success
commit from `flags = (flags >> 4) * 17` at `0x8004FFE0`; success falls through
into it. That is deliberate, not a bug — for all 16 low-nibble values
`((x*17) >> 4) * 17 == x*17`, so re-running it after a commit is a no-op. Do not
"fix" the missing branch.

**Bounded reward result.** A fixed-displacement store scan finds no direct store in
the bonus overlay or reward block `0x8004FF7C..0x80050000` whose encoded address
resolves into `0x800A6500..0x800A65A8`, including the XYZ words. Separately, the
controlled transition observed no change to the five sampled fields: health, lives,
power word, berry index and invulnerability timer. Position was not sampled by that
runtime tool.

**Correction history (2026-08-04 audit):** “Nothing else is paid” and “no store in
the whole bonus overlay” were too broad. The scanner assumes a directly materialized
`0x800A` base and cannot exclude pointer-derived stores or callee effects; the active
claim is the fixed-form scan plus the named runtime observation.

## Verified

82 static pins (`tools/phase4_f16_f18_bonus_stage.c`, load base derived rather
than assumed) plus a poll-only replay of `movies/Bonus_Level_01.movie.json`,
which is format v3 and can never be traced. The decision boundary was measured
on both sides: over 672 single-stepped frames in the stage the latch stayed `0`
while d² never fell below 1859; on frame 2683 it read 1592 and the latch flipped.
Zero frames were inside 1600 without firing. Live target table byte-identical to
the disc blob; load base located in RAM at exactly `0x800B39A0`; variant-0 cull
exactly `[12..32]` as predicted; reward flags `0x02 → 0x22`, ordinal `0 → 1`,
no player-state change.

Full account and the two first-pass errors that the tooling caught:
[[EXP_2026-08-04_phase4_f16_f18_bonus_stage]].
