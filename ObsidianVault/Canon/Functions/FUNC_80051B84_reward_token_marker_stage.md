---
kind: function
id: FUNC_80051B84
aliases:
- FUNC_80051B84
- '0x80051b84'
- reward_token_marker_stage
address: '0x80051b84'
name: reward_token_marker_stage
status: static_confirmed
confidence: confirmed
source_state: original_game
tier: confirmed
calls:
- FUNC_80051938
evidence:
- EXP_2026-08-03_phase4_c05_three_tokens
- analysis/phase4_c05_three_tokens.json
src_paths:
- tools/phase4_c05_marker_stage.c
- tools/phase4_c05_tokens_static.c
- tests/test_phase4_c05_three_tokens.py
patch_policy: safe_to_read
---

# FUNC_80051B84 — reward-token marker stage

> **⚠️ This page was published on 2026-08-03 under the wrong name and the wrong
> premise** ("results-screen token renderer"; the bit was said to select "the real
> icon versus the red `?`"). Corrected 2026-08-04. The bit→record→sprite map below
> is unchanged and was never in doubt; what changed is *where this code runs and
> what the bit does*. See [[EXP_2026-08-03_phase4_c05_three_tokens]].

An **in-world** per-frame stage that draws a floating marker above each of the
three reward-token records, passing that level's corresponding unlock bit into the
draw, where it selects **semi-transparency**: already-earned axes get a translucent
marker (see below). Every instruction word cited here is pinned against the pristine
executable by `tools/phase4_c05_marker_stage.c` (47/47 OK).

## Why this is gameplay code, not a results screen

- Its **only** caller is the per-frame gameplay state machine `0x8004ECD4`.
- Its first half is gated on live player fields (`0x800A659E == 0x0B`,
  `0x800A657C == 0`) and draws at **Flik's live world position**
  (`0x800A6500/04/08`) — coordinates a results screen has no use for.
- The callee distance-culls against the camera/eye position `0x8009EC50/54/58`.

## Per-record block

Three near-identical blocks. Each:

1. loads the record **address** (`0x800B3988`, `0x80090B68`, `0x80090B80`),
2. skips when `record[0]` equals the consumed sentinel `0x80000000`,
3. passes a fixed **sprite id**,
4. reads `unlock_array[level]` — the 16-byte array at `0x8009B878`, indexed by
   the halfword at `0x8008245C` — masks **exactly one bit**, and
5. calls the marker stage `0x80051938` with `(record, sprite_id, bit)`.

| Bit | Axis | Record | Sprite id | Owning registry row |
|---|---|---|---|---|
| `0x01` | grain reward | `0x80090B80` (`G_REWARD_SNAPSHOT`) | `0x28` | C02 |
| `0x02` | FLIK letters | `0x800B3988` (`G_FLK_SNAPSHOT`) | `0x1F` | C03 |
| `0x04` | enemies | `0x80090B68` (all-defeated event object) | `0x1B` | C04 |

All three record globals are named in *committed* C sources
(`src_re/pickup_handlers_80054288_80054554.c`, `src_re/enemy_death_permanence.c`),
not inferred here. `0x01 | 0x02 | 0x04 == 7` — exactly the per-level value
[[FUNC_800502C4_fmv_sequence_completion_check]] requires before a level's bonus
movie clip unlocks, and which [[FUNC_80055478_serialize_savegame_buffer]] persists.

## What the callee does with the bit — `0x80051938`

`0x80051938` loads `[0x8009EC50]` and falls through into `0x80051940`:

1. reads `record[0]/[4]/[8]` as world X/Y/Z;
2. squared distance to `0x8009EC50/54/58`, each delta `>> 8` before squaring;
3. **if that exceeds `0x0004C8FF`, return** — a distance cull, not a draw;
4. `beqz a2` → bit **set** gives `a2 = 0x60`, bit **clear** leaves `a2 = 0`;
   then `v0 = 0x60 - a2`, so the values handed downstream are `(0xC0, 0x00)` when
   the bit is set and `(0xC0, 0x60)` when it is clear. **What that field means is
   not established** — see the retraction below. It is certainly not an icon
   selector;
5. draws via the same sprite routine `0x80022FE0` the first half uses, at
   `record Y - 0x1A00` (hoisted above the object);
6. registers the record into the marker list `0x800B1B58 + i*16`, count at
   `0x800824CA`, capped at `0x2F`.

There is no `?` sprite anywhere in this path — the red `?` on the results screen is
tile 52, drawn by [[FUNC_800B7DA0_results_screen_evaluate_and_draw]].

> **⚠️ Naming history — three passes.** 2026-08-03: "the bit selects earned-vs-locked
> icons" (wrong venue). 2026-08-04: "the bit picks a **colour/tint** component pair"
> (wrong semantic, inference stated as fact). Then retracted to "meaning not
> established". **Now resolved** — it is a **semi-transparency selector**.

## What the bit actually does — resolved 2026-08-04

`tools/phase4_c05_marker_semitransparency.c` pins the whole chain, 21/21, offline.

`effect_mesh_transform` `0x80022FE0` stores the value into a **28-byte effect draw
record**. Exactly **one** consumer of those records exists — `0x80023ABC` — which is
provable rather than assumed: only four functions touch the record count at
`0x80082374` (`gp+0x5DC`), namely the two producers, a reset, and that consumer.

The record begins at **`0x8009E8D0`**, not `0x8009E8E0`. The producers address it as
`0x800A0000-0x1720 + i*28` (so the field looks like `+0x02`), while the consumer sets
`t6 = 0x800A0000-0x1730` and walks `t0 = t6 + 0x12` with a 28-byte stride — the same
address via a different base, which is why an earlier displacement grep found nothing.

```
lh   v1, (t0)              ; the bit-dependent value
li   v0, 0x60
beq  v1, v0, skip          ; == 0x60 -> leave it alone
prim = [0x8008249C]
prim[7] |= 0x02            ; semi-transparency
skip:
```

The same record's `+0x08/+0x09/+0x0A` go to `prim[4]/[5]/[6]`. A PS1 GPU packet's
first word after the tag is `0xCC_BBGGRR`, so those are **R, G, B** and `prim[7]` is
the **command byte** — whose bit `0x02` is the semi-transparency (ABE) flag.

| Unlock bit | Value | Test | Marker |
|---|---|---|---|
| **clear** (axis not yet earned) | `0x60` | `== 0x60` | **opaque** |
| **set** (axis already earned) | `0x00` | `!= 0x60` | **semi-transparent** |

So an already-earned reward keeps a **translucent** in-world marker — the same visual
language as the results screen's dimmed already-earned token, reached by a different
mechanism (the screen modulates colour through `0x80026858`; this sets the GPU's ABE
bit). Two independent code paths expressing "already earned" the same way is a useful
cross-check on the whole bit map.

## What this function does not do

It only **reads** the bits. Both the writers and the results-screen token and
counter renderers live in [[FUNC_800B7DA0_results_screen_evaluate_and_draw]], not
here and not in C02/C03/C04's own paths.
