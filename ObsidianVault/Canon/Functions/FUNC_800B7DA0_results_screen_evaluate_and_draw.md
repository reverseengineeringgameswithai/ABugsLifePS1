---
kind: function
id: FUNC_800B7DA0
aliases: [FUNC_800B7DA0, 0x800b7da0, results_screen_evaluate_and_draw, popcount8]
address: 0x800B7DA0
name: results_screen_evaluate_and_draw
status: static_confirmed
confidence: confirmed
source_state: original_game
overlay: BITS/MEMORY.BIN
system: [SYS_level_results_screen]
calls: [hud_draw_sprite_tile, frontend_tpage_draw, music_play_once]
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - src_re/level_complete_results_800b7da0.c
  - EXP_2026-08-03_phase4_c05_three_tokens
  - analysis/phase4_c05_three_tokens.json
src_paths:
  - src_re/level_complete_results_800b7da0.c
  - tools/phase4_c05_results_overlay_locate.c
patch_policy: unknown
---

# FUNC_800B7DA0 — level-complete results screen: evaluate, set, draw

> **Renamed 2026-08-04.** This page was auto-generated as `popcount8` — the
> generator took the name of the first `static` helper in the modding pseudocode
> inside `src_re/level_complete_results_800b7da0.c`, not the routine at this
> address. The page body always described the LEVEL COMPLETE results overlay
> correctly; only the title was wrong. `popcount8` is retained as an alias so old
> links resolve.

> **⚠️ Overlay code.** `0x800B7DA0` is this function only while `BITS/MEMORY.BIN`
> is resident. Several overlays occupy the `0x800Bxxxx` window — C17's
> movie-viewer menu builder sits at `0x800B4084` and C04's completion handler at
> `0x800B40C4`, in *different* overlays. An overlay address alone never identifies
> code; always pair it with the file.

## Identity (independently re-derived 2026-08-04)

`BITS/MEMORY.BIN` loads **verbatim** at `0x800B5788`; bounds
`0x800B7DA0..0x800B8788` (`functionBounds` confidence `exact`, cleanEnd, 2540
bytes, prologue `addiu sp,sp,-144`); sole caller `0x800B9754`.

Base and bounds were **already recorded** in the long-committed
`src_re/level_complete_results_800b7da0.c` (`RESULT_MEMORY_BIN_BASE`,
`RESULT_FUNC_START`, `RESULT_FUNC_END`). C05 re-derived them independently — from
a live read-watch, then from an offline scan of all 326 retail files — and they
agree exactly. What that file does **not** cover, and what C05 adds, is the axis
evaluation and the unlock-bit writes below; it documents row 2's word renderer and
medal timing for modding purposes instead.

`tools/phase4_c05_results_overlay_locate.c` verifies **30/30** instruction words at
derived file offsets and confirms `BITS/MEMORY.BIN` is the only retail file
containing this code — so the whole binding is reproducible offline.

## It evaluates the three axes — and this is where the bits are SET

| Axis | Source | Condition | Bit | Earned tile |
|---|---|---|---|---|
| grain | `0x800A65A1` (u8, clamped to 50 via `sltiu 51`) | `== 50` | `0x01` | 59 |
| FLIK letters | `0x800A65A2` (u8 mask) | `== 0x0F` | `0x02` | 58 |
| enemies | `0x800A658E` (s16 quota, clamped ≥0) | `== 0` | `0x04` | 57 |

Each block reads `unlock_array[level]` (`0x8009B878`, index `0x8008245C`) and:

- **bit already set** → per-axis stack slot = `2` (earned on an earlier visit);
- **bit clear** → slot = `1` (newly earned), `ori` the bit in, **`sb` it back to
  `unlock_array[level]`**, and set `0x800823E4 = 1` (a "something was newly earned
  on this screen" flag).

This is the **bit setter**. All three live in this one routine — which is exactly
why C17 observed `array[6]` jump `0 → 7` **atomically** rather than in three steps,
and it corrects the earlier assumption that the setters lived separately in
C02/C03/C04's completion paths.

**The third axis is enemies by construction** — the condition tests the enemy
quota. That is proof, not the icon inference recorded on 2026-08-03, and it agrees
with the independent bit map in [[FUNC_80051B84_reward_token_marker_stage]]: two
unrelated code paths assign the same bit to the same axis.

## Presentation — the real locked-vs-earned selection

Rows draw at `y = 32` (grain), `100` (FLIK), `168` (enemies).

- While the row's **animated counter has not reached that row's total**, the row
  draws **locked tile 52** — the red `?` — at `x = 248`. (The same
  counter-reaches-total gate the committed source calls the "medal reveal", where
  it notes row 2 comparing the animated `s6` against the literal `4`.)
- Once it reaches the total:
  - slot `1` (newly earned) → earned tile at `x = 240`, full bright, via
    `hud_draw_sprite_tile` `0x80025F54`;
  - slot `2` (earned on an earlier visit) → the **same** tile via `0x80026858`
    with `(128,128,128)` in three stack args — a **dimmed** token. This is the
    `RESULT_MEDAL_DIM_SITE` the committed source already names.

This is the earned-vs-locked selection that the 2026-08-03 pass wrongly attributed
to the in-world marker stage.

## Live cross-check

At the captured frame: grain `= 50`, FLIK mask `= 0x0F`, quota `= 0`, enemy
**total** `0x80082258 = 9`, `unlock_array[6] = 7`, newly-earned flag `= 1`. The
screenshot shows `50/50` + earned grain token, `4/4` + earned FLIK token, and
`00/09` still counting up with the red `?` — exactly the counter-gated presentation
above. `0x80082258 = 9` is the `/09` denominator, confirming the third counter is
*defeated / total* enemies.

## The counter animation (decoded offline 2026-08-04)

`tools/phase4_c05_counter_animation.c` pins **46/46** words against the pristine
`BITS/MEMORY.BIN`, no emulator.

The screen is **one per-frame loop**: `0x800B7F98` (`wait_for_frame_sync_flag`) …
`0x800B8740` (`bne s3, zero`). `s3` is the screen countdown, seeded to **800** and
decremented once per frame.

Three numerators share one law — `if (numerator < target && fp == 0) { numerator++;
sfx(14); }` — where `fp` toggles every frame, so **counters tick at 30 Hz**.
`s1 = (s1+1) & 0xF` on the `fp==0` frames drives the spinning icon.

| Row | Numerator | Target |
|---|---|---|
| grain | `s4` | `[0x800A65A1]` |
| FLIK | `s6` | `popcount_table[0x800BE444 + mask]` |
| enemies | `s5` | `[0x80082258] − [0x800A658E]` = total − remaining = defeated |

Digits use `hud_draw_sprite_tile(x, y, tile, glyph)`: tile **56** is the digit font,
the fourth argument is the glyph, **10** is `/`, and tens come from the `0x66666667`
divide-by-10 reciprocal.

**The grain denominator `50` is two literal glyph indices** in shared overlay code —
so it is 50 on every level. The only per-level number on the screen is the enemy
total.

**The header tile is latch-driven**: `0x800B7FC0` reads the goal latch `0x800823A0`
— `==1` selects tile 54, otherwise tile 55.

**The button is a fast-forward, not a skip.** A *fresh* press on the face-button mask
`0xF000` (`[0x80082412]` set, `[0x800822E4]` clear), inside `25 ≤ s3 < 740`: if all
three numerators are already at target and the one-shot flag is clear, `s3 = 24`;
otherwise `s3 = 54` **and the numerators snap to their targets**. That is how a token
can appear immediately after a press — the tokens are gated on the numerator reaching
the total, and the snap satisfies that gate.

`0x800BE444` is a 16-entry **popcount** table (`0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4`;
next byte 252, so only the 4-bit domain is meaningful) — which is what the
auto-generated `popcount8` page name was describing. ⚠️ It lies in `MEMORY.BIN`'s
runtime-mutable tail, so only its **disc** bytes are proven.

## The dimmed already-earned token, confirmed live (2026-08-04)

The slot-`2` path had never been observed executing — every fixture is a first-time
completion. Forced it by poking `unlock_array[6] = 0x07` **before** the evaluator
ran, on the existing LEVEL06 movie, then capturing the identical emulator frame as
the control.

- **State:** `array[6]` stayed `0x07` and the newly-earned flag `0x800823E4` stayed
  **0** (control: `1`) — no block took the newly-earned branch, so all three slots
  were `2`.
- **Pixels:** 42,185 changed, bounding box `x[602..760] y[71..422]` — exactly the
  token column, rows 1 and 2 only. Grain mean brightness `94.6 → 72.2`, FLIK
  `111.4 → 87.7`. The tokens render **translucent** — grass and background show
  through — instead of solid.
- **Built-in negative control:** row 3 was still showing the red `?` (its counter
  had not reached the total) and changed by **exactly 0** pixels; nothing outside
  the token column changed either.

So `slot==1` draws solid via `hud_draw_sprite_tile`, `slot==2` draws the same tile
translucent via `0x80026858` with `(128,128,128)`. This also answers the old
"replay behaviour once a level already reads 7" question at the presentation level:
the screen still appears, the counters still animate, and the tokens come up dimmed.

## Where the newly-earned flag goes — it triggers the save (2026-08-04)

`0x800823E4` is set by all three blocks when an axis is earned for the **first** time.
Nothing in the resident executable reads it; inside `BITS/MEMORY.BIN` there is exactly
**one** load, at `0x800B8AD0`, in a routine starting at `0x800B8ACC`. That routine is
the **save path**:

```
v0 = [0x800823E4]
if (v0 == 0) goto done            ; nothing new -> never saves
v0 = 0x800B7BA4()                 ; gate routine
[0x800823E4] = v0
if (v0 == 0) goto clear
s0 = 0x8009EC68                   ; THE SAVE BUFFER
0x80055478(s0)                    ; serialize_savegame_buffer
if (0x800BB6F4() != 0)            ; the card write
    [0x8008245C] = -2             ; failure sentinel into the level index
0x80055538(s0)                    ; the save deserializer
clear: [0x800823E4] = 0
done:
```

So the flag means "progress changed on this screen, therefore save", and the **save
buffer is `0x8009EC68`** — passed to both
[[FUNC_80055478_serialize_savegame_buffer]] and the deserializer `0x80055538`, tying
this screen to E14's save schema.

It also completes the replay story from the persistence side: a pure replay of an
already-100% level sets no bits, so every slot is `2`, so the flag is never set, and
this routine **skips the entire save block**. Together with the dimmed-token result
above, the replay case is now described at both the presentation and persistence
levels. Pinned 20/20 offline by `tools/phase4_c05_newly_earned_flag.c`.

## Not traced

The gate routine `0x800B7BA4` and the card writer `0x800BB6F4` (frontend/save
territory, E14); the caller `0x800B9754` and the rest of `MEMORY.BIN`; a **live**
re-read of the `0x800BE444` table.

## C source excerpt

See `src_re/level_complete_results_800b7da0.c` for the row-2 word-renderer and
medal-timing notes, the ALLMODS `BITS/MEMORY.BIN` patch layout, and the warning
that `0x800BE444` is Flik's Journey vine/leaf data and must not be used as scratch.
