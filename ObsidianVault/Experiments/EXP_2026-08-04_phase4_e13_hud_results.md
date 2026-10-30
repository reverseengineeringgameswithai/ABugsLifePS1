---
kind: experiment
id: EXP_2026-08-04_phase4_e13_hud_results
status: complete
source_state: original_game
system: [SYS_level_results_screen]
row: E13_hud_results
---

# Phase 4 E13: the in-game HUD renderer, and the results half by synthesis

## Question

E13's `next` was *"compare results-screen object lists across normal vs boss completion saves"*,
with `missing` listing *"every panel/mode, animation, boss/special-level differences, save
consequences."* Two of those turned out to be answerable from code rather than by collecting
saves, and one was already closed by C05 the same day.

## Step 1 — the in-game HUD renderer

The function census names `0x800526FC` **`results_screen_render`**. That name is wrong twice,
and both errors matter:

1. `0x800526FC` is **not a function entry**. The real entry is `0x800526F4`, an 8-byte head
   that reads the transition timer `0x80082470` and falls through — exactly the shape of C05's
   marker stage (`0x80051938` → `0x80051940`).
2. It is **not the results screen**. That is
   [[FUNC_800B7DA0_results_screen_evaluate_and_draw]] in the `BITS/MEMORY.BIN` overlay, which
   reads the unlock array `0x8009B878` — an address `0x800526F4` never touches.

What it actually is: the **per-frame in-game HUD stage**, called from the gameplay state
machine `0x8004ECD4` (the `jal` sits at `0x8004F3E4`) — the same driver that calls C05's
reward-token marker stage. It reads exactly the on-screen counter set: grain `0x800A65A1`,
FLIK mask `0x800A65A2`, enemy quota `0x800A658E`, enemy total `0x80082258`, lives
`0x800A65A0`, goal latch `0x800823A0` — and draws through `hud_draw_sprite_tile` `0x80025F54`.

The FLIK letters are four near-identical blocks, one per mask bit, evenly spaced 24px apart:

| Mask bit | x | Tile |
|---|---|---|
| `0x01` | `0x70` | — |
| `0x02` | `0x88` | `0x11` |
| `0x04` | `0xA0` | `0x12` |
| `0x08` | `0xB8` | `0x13` |

That independently reproduces the already-committed "FLIK letters are glyphs, sprite tiles
`0x10`–`0x13`" finding, and matches the live gameplay capture taken during C05 (F L I K across
the top of the screen).

`tools/phase4_e13_ingame_hud.c` pins all of it — **22/22, first build, offline**. Caller and
body were both checked *before* naming, per the rule C05's corrections produced. This is the
**third** census name this session that pointed at the right area with the wrong label
(`effect_render_stage`, `popcount8`, now this) — the pattern is worth treating as structural,
not incidental.

## Step 2 — the results half, by synthesis

No new work: C05 closed this the same day. Cited rather than redone, so E13 doesn't
re-investigate it. The evaluator, the 30 Hz counter law, the locked/earned/dimmed token states,
and — answering E13's own **"save consequences"** gap directly — the newly-earned flag
`0x800823E4` as the **save trigger**, gating serialize → card write → deserialize over the
buffer at `0x8009EC68`. A pure replay sets no bits, so no save happens.

## Step 3 — what selects the panel mode

**One flag: the goal latch `0x800823A0`**, used consistently in both renderers.

- In the HUD stage: when the transition timer is running **and** the latch is still clear — a
  non-completion transition — it writes `0x400` into `0x800B0188/18C/190`.
- In the results screen: latch `== 1` selects header tile **54**, otherwise tile **55**.

So E13's "boss/special-level differences" has a code-side answer that doesn't need per-mode
saves collected first.

**Not established:** what the tile-55 variant actually looks like, whether boss stages differ
beyond this latch, and what `0x800B0188/18C/190` mean. The row's own fixtures
(`level01_end_of_stage.sav`, `LEVEL02_ENDING.sav`) would settle the first two and were not run
this pass. Flagged rather than assumed.

## Step 4 — the three halfwords, decoded

`0x800B0188/018C/0190` are **per-HUD-element animation phase counters**. Each runs a
`0..0x1000` cycle advanced once per frame by the HUD stage's own argument, with `0x400` as the
significant point:

| Address | Element | Behaviour at `0x400` |
|---|---|---|
| `0x800B0188` | lives | latches `0x800A65A0` into the display slot |
| `0x800B018C` | grain | latches `0x800A65A1`; digits split by the `0xCCCCCCCD` ÷10 reciprocal |
| `0x800B0190` | — | **not** a latch: a piecewise ramp (rise → plateau at `0x400` → fall), doubled; an animation *magnitude* |

Which makes the transition write meaningful: forcing all three to `0x400` puts every element at
its commit/peak point — freeze the HUD showing current values rather than mid-animation.

The same halfwords are read and written by `0x80054EB4`, the body behind the already-Canon
8-byte head `grain_pickup_handler` `0x80054EAC`. That's a **fourth** instance of this codebase's
8-byte-head-then-fall-through idiom, after `0x800526F4`, `0x8004F478`, and C05's `0x80051938`.
Worth treating as a recognised pattern: when a census entry looks like a function, check whether
it is really a *body*.

`tools/phase4_e13_hud_anim_phases.c` — **19/19, first build, offline**.

## Step 5 — the presentation questions, closed

**Do boss stages differ? No — and this is a static, exhaustive answer.** I walked every
`lui`/load/store pair in `FUNC_800B7DA0..0x800B8788` to enumerate the routine's *complete*
global set:

- **reads** — enemy total `0x80082258`, the pad edge pair `0x800822E4`/`0x80082412`, goal latch
  `0x800823A0`, level index `0x8008245C` (used **solely** to index the unlock array), unlock
  array `0x8009B878`, quota `0x800A658E`, grain `0x800A65A1`, FLIK mask `0x800A65A2`, popcount
  table `0x800BE444`;
- **writes** — newly-earned flag `0x800823E4`, the unlock array, and the quota clamp.

**There is no boss-specific input** — no scene id beyond the array index, no `0x80090BEE`
(Thumper), no `0x800B4BA8` (Hopper), no per-level table beyond the unlock array. Boss stages get
the *same* results screen; the only per-level variation is that level's unlock byte and its
enemy total. So E13's "boss/special-level differences" needed no fixtures at all.

*(A bare `0x800A0000` also shows up in the scan — an addressing artifact of the `lui`+`addu`
indexed forms, not a distinct global.)*

**What the tile-55 variant is: "level total".** The header tile is re-read every frame *inside*
the results loop, so a poke flips it on the same screen — a far cleaner A/B than the C05 marker
case. Replaying the existing LEVEL06 movie to the results screen and writing `0` to the goal
latch:

| Latch | Tile | Banner |
|---|---|---|
| `1` | 54 | **level complete** |
| `0` | 55 | **level total** |

Same screen, same counters and tokens — only the banner changes. So "level total" is the
non-completion *summary variant of the same screen*, not a separate screen, which fits the HUD
stage's own use of the latch.

**Honest limits:** the pixel diff across the two captures is dominated by three frames of
counter animation, so the diff number is *not* the evidence — the cropped header images are.
And "level total" was produced by **forcing** the latch; the natural path that reaches the
results screen with the latch clear was not exercised.

## Still open

Per-panel breadth beyond this screen — other frontend panels were never in steps 1–5's scope.
The **natural** path that reaches the results screen with the goal latch clear was not
exercised; "level total" was produced by forcing the latch.

`0x8004F478` — the real entry behind the census's `gameplay_frame_render` `0x8004F480` — remains
*bounded but not decoded*: its body touches only `0x800822B0`, `0x800823A0` and `0x80082470` and
no player or HUD stats, so it is a transition/scene-flow stage, not a HUD one. That rules it out
of E13's scope without decoding it.

## Evidence

`analysis/phase4_e13_hud_results.json`; `tools/phase4_e13_ingame_hud.c` (22/22);
`analysis/phase4_c05_three_tokens.json` for the results half.
