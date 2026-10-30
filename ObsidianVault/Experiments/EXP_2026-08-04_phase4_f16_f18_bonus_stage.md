---
type: experiment
status: complete
date: 2026-08-04
system: Bonus stage (scene 0x10)
phase: 4
artifacts:
  - analysis/phase4_f16_f18_bonus_stage.json
  - tools/phase4_f16_f18_bonus_stage.c
  - tools/phase4_f16_f18_bonus_runtime.py
  - tests/test_phase4_f16_f18_bonus_stage.py
fixtures:
  - movies/Bonus_Level_01.movie.json
---

# Phase 4 F16/F17/F18: what the bonus stage actually is, and what it pays

## Question

`F16_bonus1_spiders`, `F17_bonus2_mushrooms` and `F18_bonus3_grasshoppers` each
carried exactly one open item, and it was the **same** item: *"Bonus stage
rules/reward."* The three rows differ only in the unlock challenge that gets you
there — five spider butt-slams, five distinct mushrooms, five blue-berry
grasshopper kills — and all three of those were already bound. What none of them
said is what happens after the transition fires.

That framing turned out to be the answer to a structural question the rows never
asked: **there is only one bonus stage, and it is the same one for all three
rows.** Which layout you get depends on how many bonuses you have already
finished, not on which challenge you just completed. So one investigation closes
three rows, and it closes them with the *same* evidence rather than three
parallel arguments.

## Scope note

A concurrently-running agent (row `C18_bonus_entry`) reached overlapping
conclusions while this was being written, and its work was uncommitted at the
time. Nothing here is copied from it: every claim below is a pin against the
pristine image or a live measurement. Where the two readings differ, the
difference is stated in "Two things the entry-side reading does not cover"
rather than quietly reconciled. Its Canon file was deliberately left untouched
to avoid colliding with an in-flight commit; this system got its own Canon page.

## Method

**Static.** `tools/phase4_f16_f18_bonus_stage.c` — 82 pins, `-Werror`, run
against `REBUILD/files/SCUS_942.88` and `REBUILD/files/LEVEL06/LEVEL1.BIN`.
Per the standing rule, static ASM probing is done with a compiled self-verifying
tool, never by reading a disassembler dump into prose.

The load base is **derived, not assumed**: exactly one `j`/`jal` in the blob
targets an address inside the blob's own span, and that target must land
immediately after a `jr ra` + `nop` pair. Both hold only for `0x800B39A0`.

The overlay is 1,820 bytes. `--accounting` structurally partitions all 455 words
into 1 header + 373 presumed code + 81 data. Four return-delimited spans tile the
presumed code range with no gap or overlap, and no resolved direct branch or call
targets the presumed data region. It does not resolve `jr`/`jalr` targets or prove
semantic reachability. **Correction history (2026-08-04 audit):** the former
“exhaustive accounting; no fifth hidden function” reading exceeded this method and
is retracted.

**Runtime.** `tools/phase4_f16_f18_bonus_runtime.py` replays the retained
`movies/Bonus_Level_01.movie.json` fixture. That movie is **format v3**
(CachedInterpreter-era), so it is poll-only forever: arming any CPU
instrumentation would force the interpreter and desync it silently. Nothing here
arms a watch or a breakpoint. The firing frame is therefore found by
single-stepping and sampling, not by a write watch.

## What the bonus stage is

Scene `0x10` runs `LEVEL06/LEVEL1.BIN`. Confirmed two independent ways: the
Phase-3 scene-asset graph maps scene 16 to `disc_dir level06`, `bin LEVEL1.BIN`;
and that blob is the **only** image in the entire game that reads the persisted
bonus ordinal `0x8009B88A`, which it does twice. Its sibling
`LEVEL06/LEVEL.BIN` (scene 6, an ordinary stage in the same disc directory)
never reads it — so the bonus logic belongs to the file, not to the directory.

The four functions:

| VA | words | what it is |
|---|---|---|
| `0x800B39A4` | 84 | installs a 51-entry pickup descriptor table at `0x80096B98` |
| `0x800B3AF4` | 15 | advances the goal token's UV animation frame |
| `0x800B3B30` | 90 | stage init: culls actors by variant |
| `0x800B3C98` | 184 | per-frame update: beacon, particles, completion test |

**The whole stage is one predicate.** Every frame, `0x800B3C98` computes

```
d² = Σ over x,y,z of ((flik[i] - target[i]) >> 8)²        ; sra, then mult
if (d² < 1600)  →  [0x800823A0] = 1 ; [0x80082470] = 30
```

`0x800823A0` is the shared transition latch and `0x80082470` the fade timer, so
that store *is* the completion. The decoded completion path has no timer, score,
fail-state or enemy gate: it reaches completion through the two distance checks
and the existing-latch guard. Actors left alive are driven by ordinary resident
code, and callee effects were not closed.

**Correction history (2026-08-04 audit):** “no timer, no score, no fail state and
no enemy requirement anywhere in the overlay” generalized a decoded completion
path into an overlay-global negative. Only the path-scoped statement remains active.

**A second distance test gates the first.** Ahead of the completion check the
same function computes the squared distance from a *different* reference point,
`0x8009EC50`, to the same target, and if it exceeds **359,999** it jumps past
everything — beacon, particles, and the completion test included. So completion
is unreachable while that point is far, regardless of where Flik is. The
reference point has exactly one writer in the game, `0x8004EC94`, immediately
after the camera follow update `0x8004DF18`, and it is **not** Flik: on the
firing frame it was 182 units from the target while Flik was 40.

**The variant selects a layout.** `0x8009B88A` — the persisted *completion
ordinal*, not the challenge id — indexes a 0x10-stride table at `0x800B4070`
and drives three actor-culling branches. Culling is `actor+0x6E := 0` (HP) and
`actor+0x62 := 10001`, the same retirement pair F11 found on acorns.

| variant | actors kept | target (x, y, z) | beacon y | beacon rgb |
|---|---|---|---|---|
| 0 | 0..11 | −13187, −70036, −22421 | −70036 | 128, 32, 0 |
| 1 | 0..13 | −22349, −79705, 48945 | 18380 | 96, 112, 128 |
| 2 | 14..32 | 157232, −42406, 5891 | −42406 | 128, 96, 0 |

**The token you chase is this overlay's own sprite.** The install function
copies 51 words from `0x800B3FA4` over the pickup kind→descriptor table at
`0x80096B98`, and the last entry points back into the blob at `0x800B3F78`. The
update tail advances a counter masked to `0..15`, which indexes a 16-entry UV
table at `0x800B3F84` (u steps `0x20` across 8 columns, then v steps to `0x40` —
an 8×2 strip) and writes u/v at `+8`/`+9` of that descriptor. So the bonus stage
replaces the pickup table wholesale and adds its own animated token as the last
kind.

## What it pays

The reward lives in the resident shell, not the overlay.

```
[0x800823A0] == 6  →  gp+1220 (0x8008225C) := 1        ; 0x80050230, one-shot
...next scene...
gp+1220 set?       →  clear it immediately             ; 0x8004FF94
  latch != 1       →  skip the reward entirely         ; 0x8004FF98
  latch == 1       →  flags 0x8009B889 := (flags & 0x0F) * 17
                      ordinal 0x8009B88A += 1
                      fmv_bin_load(old_ordinal + 42)   ; 0x8004FFD4
```

So the reward is **FMV 42/43/44 in completion order** — the movie you get
depends on whether this was your first, second or third bonus, not on which
challenge you solved. And the tentative low bit set by the challenge is only
made permanent here: `(flags & 0x0F) * 17` mirrors the low nibble into the high
nibble, and the high bits are the "already earned" guards.

**The restore block is not an else-branch.** There is no branch between the
success commit and the `flags = (flags >> 4) * 17` block at `0x8004FFE0` —
success *falls through* into it. That reads as a bug until you notice the
arithmetic is idempotent: for every one of the 16 low-nibble values,
`((x*17) >> 4) * 17 == x*17`. The tool proves this over the whole domain rather
than arguing it. Worth recording so nobody "fixes" the missing branch.

**Bounded reward result.** The fixed-displacement scan finds no direct store in the
bonus overlay or reward block `0x8004FF7C..0x80050000` resolving into
`0x800A6500..0x800A65A8`; pointer-derived stores and callee effects remain open.
The controlled transition separately observed no change in the five sampled fields:
health, lives, power word, berry index and invulnerability timer. It did not sample
position.

**Correction history (2026-08-04 audit):** “pays nothing else,” “no store in the
entire bonus overlay,” and “position is read-only” exceeded the fixed-form scan and
the five-field runtime sample. Those global negatives are retracted.

## Runtime results

Replay of `Bonus_Level_01` (poll-only), entering scene `0x10` at frame 1140:

- **Load base measured, not assumed.** The blob's unique 256-byte data tail was
  located in RAM at exactly `0x800B39A0`, matching the statically derived base.
- Live target table is **byte-identical** to the disc blob.
- Descriptor slot 50 reads `0x800B3F78` — the overlay's own token, as predicted.
- Variant 0 in play; culled actors were **exactly** `[12..32]`, the prediction
  for variant 0, with none extra and none missing.
- The animation counter stayed within `0..15` across 24 stepped frames.
- **The decision boundary, both sides.** Over 672 single-stepped frames inside
  the stage the latch stayed `0` and the squared distance never fell below
  **1859**. On frame 2683 it read **1592** and the latch flipped to `1` with the
  fade set. Zero frames were inside 1600 without firing.

  ```
  f 2679  d² 2170   latch 0
  f 2681  d² 1859   latch 0
  f 2683  d² 1592   latch 1   fade 29
  ```

- **The coarse gate is observably live**: 78 of those frames exceeded 359,999 on
  the reference point (max seen 414,796), i.e. the completion test was skipped
  on them for a reason unrelated to Flik's distance.
- Reward measured across the transition: flags `0x02 → 0x22`, ordinal `0 → 1`,
  scene → `0` (journey menu), and **no** player-state word changed.

## Two things the entry-side reading does not cover

Recorded as differences, not corrections — both readings agree on the 1600 test.

1. **The coarse gate on `0x8009EC50` at 359,999.** It is a genuine second
   condition on completion, not a rendering optimisation: the branch it takes
   skips the completion store as well as the beacon, and it demonstrably fired
   on 78 frames of this run. A description of the stage that lists only the 1600
   test is incomplete.
2. **The restore block's fallthrough.** Describing it as what happens on a
   non-success return is right in effect but hides that it also runs after a
   success and is idempotent by construction.

## What a first reading got wrong

Two errors, both caught by the tooling rather than by reasoning:

- **Read too early.** Sampling the moment the scene id flips to `0x10` returns
  the *previous* overlay: the scene word changes before the load completes. The
  first pass read a target of `(-1939650000, 0, 274726915)` — plainly
  instructions, not coordinates — and printed `REFUTED` for a law that is
  correct. Fixed by waiting for the transition latch to clear and then
  *searching* for the blob rather than assuming residency. Same class as the
  pre-init misreads in F11 and D16.
- **A signature that wasn't unique.** The first residency search used the
  function prologue and matched at `0x800B39D8` — 0x38 off, and inconsistent
  with the blob's own internal `jal` — because `LEVEL06/LEVEL.BIN` opens with
  the identical prologue. Fixed by signing on the data tail and asserting the
  match is unique.

Also worth flagging for reuse: `debugger.scatterRead` reports an unreadable item
as `value: 0` with `valid: false`. A bad address reads back as a perfectly
plausible zero. The probe asserts per-item validity and refuses to treat an
invalid item as data.

## Follow-up: the Bonus-1 streak law (operator-directed)

After the above was banked the operator corrected the F16 row and asked a second
question:

> "there's a misconception on the row: it can be any enemy that is
> butt-slammable. Just in the movie given it's spiders only. […] I've noticed
> that killing enemies with the berry will reset the count, and I believe one
> other action does too, but there are other things that will not reset the
> count. I'll let you figure that out via C code probing ASM."

`tools/phase4_f16_streak_law.c` (43 pins) settles all of it. Full standing
description: [[SYS_bonus1_streak_law]].

**The correction is right, and the code is stronger than the correction.**
Nothing in the streak logic looks at the enemy *at all*. In the contact resolver
`s6` is set once at `0x8004AC78` to `0x800A657A` — the **player** struct — and
is never reassigned inside the per-actor loop (proven, not asserted: the tool
scans the loop body for any write to `$s6`). Every deciding test is player state
at the instant of contact. "Spiders" was the fixture; the row name has been
changed.

**Resolved-site census, not domain closure.** The current general scan resolves
seven direct writers and one direct reader in the resident EXE. It retains 12,956
unresolved-base accesses (44 same-width sites in related functions), 149 indirect
calls and the overlay pointer residual. The v4 run observed no writer outside the
resolved set in that run; it did not close the static residual.

**Correction history (2026-08-04 audit):** the former “domain is closed,” “exactly
eight sites,” “nothing in any overlay,” and “complete statement rather than a
survey” wording promoted a resolved-site sample into closure. Those propositions
are retracted; the seven-writer/one-reader resolved set remains pinned.

**"Some things reset it, some don't" is one field with three outcomes**, not two
rules — `sltiu` at `0x8004B2B4` against `0x800A6584`: `>= 2` branches past every
write to the counter (inert), `== 1` counts, `== 0` clears.

**The berry claim is slightly too narrow, in a useful direction.** The clear at
`0x800470D8` is at the *entry* of the berry constructor and is unconditional —
proven both ways, no branch in `[0x800470AC, 0x800470D8)` and nothing in the
function branching over it. Its sole caller fires when the berry action state
reaches 10, which Canon already establishes is construction. So the **throw**
ends the chain, kill or no kill. Stated as a falsifiable prediction rather than
a conclusion, because the clean recording never throws a berry.

### What the live runs could and could not show

`F16_Bonus01` is a *perfect* run: five increments, unlock, done. It therefore
exercises the counting side and the success reset only, and cannot speak to any
of the reset causes. Recorded as a limit rather than glossed.

One thing the capture did add that no listing would have: `0x800A6584` is not a
small enumeration. Over the run it took `0..10` **and** negative values
(`-6144..-512`, step 512). Since the gate is `lhu` + `sltiu`, every negative
value reads as a huge unsigned number and lands in the inert bucket — so a
*signed* reading of that test would get the behaviour backwards across much of
the field's real domain.

## Status

All three rows' single open item — "Bonus stage rules/reward" — is closed, by
one shared mechanism. See [[SYS_bonus_stage]] for the standing description and
`analysis/phase4_f16_f18_bonus_stage.json` for the raw capture. The F16 streak
law is [[SYS_bonus1_streak_law]].

Not claimed: the variant 1 and variant 2 layouts are decoded from the table and
pinned in the image, but only variant 0 has been *observed* running. Confirming
the other two needs a session that completes two and three bonuses.
