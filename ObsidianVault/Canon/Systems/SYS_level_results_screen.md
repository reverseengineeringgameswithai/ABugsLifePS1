---
kind: system
id: SYS_level_results_screen
created: 2026-07-08
updated: 2026-08-04
status: static_confirmed
confidence: confirmed
source_state: original_game_reference_or_mod_reference
functions:
  - FUNC_800B7DA0
  - FUNC_80051B84
evidence:
  - EXP_2026-08-03_phase4_c05_three_tokens
  - analysis/phase4_c05_three_tokens.json
src_paths:
  - src_re/flik_emblem_results_menu.c
  - tools/phase4_c05_results_overlay_locate.c
  - tools/phase4_c05_counter_animation.c
address: 0x00140100
patch_policy: safe_to_read
---

# SYS_level_results_screen - flik emblem results menu

## Purpose

This page closes the migration source-coverage gap for `src_re/flik_emblem_results_menu.c`. It records the symbol `G_DAT_BASE_PTR_ADDR` and links the C reference into the structured vault.

- Address if known: `0x00140100`
- Coverage comments: globals/constants: G_DAT_BASE_PTR_ADDR, JOURNEY_FLIK_PACKET, JOURNEY_FLIK_WORD0, JOURNEY_FLIK_WORD1, JOURNEY_FLIK_WORD2_CLUT_UV, JOURNEY_FLIK_WORD3_SIZE, LEVEL01_DAT_BASE, RESULT_FLIK_PACKET


## C source excerpt

Source: `src_re/flik_emblem_results_menu.c`

```c
/*
 * flik_emblem_results_menu.c -- RE notes for FLIK result/menu emblem ownership.
 *
 * Status 2026-07-06:
 * - In-level Anthill FLIK emblem replacement is a LEVEL01-local 4bpp glyph asset edit.
 * - Training's local FLIK badge is now wired separately through LEVEL00/LEVEL.RAW
 *   chunk 3 rect 64,96,64,80, plus the visible spawned coin at rect
 *   64,128,64,64 / CLUT slot 9. The LEVEL COMPLETE coin copy is patched
 *   separately in LEVEL00/LEVEL2.RAW chunk 1 rect 64,128,64,64 / CLUT slot 9.
 *   Follow-up live VRAM inspection from the resaved _1.sav showed the actual
 *   in-game Training spawned coin in the LEVEL07 collectibles atlas at rect
 *   64,0,64,64. Raw VRAM-nibble comparison maps the full
 *   visible X/FLIK strip exactly to LEVEL07/LEVEL.RAW chunk 12 rect 0,0,128,64
 *   and LEVEL07/LEVEL1.RAW chunk 13 rect 0,0,128,64. The gameplay primitive's
 *   blue/silver runtime CLUT at VRAM x=1008,y=253 is shared with Flik head/HUD
 *   portrait art. A brief attempt to recolour that CLUT made the spawned coin
 *   match the result screen but also recoloured Flik's head; the active stager
 *   now leaves the shared CLUT untouched, preserves transparent source pixels
 *   on the in-game tile, and uses a Training-specific clean silver coin-face
 *   asset so the old FLIK text is covered without filling the sprite rectangle.
 *   The Training result coin is palette-constrained for visual consistency. A
 *   full-colour in-game Training emblem needs a runtime primitive CLUT redirect
 *   or duplicate per-token CLUT.
 *   The earlier chunk 12 rect 128,192 candidate was a false static-atlas match
 *   and leaves the old silver FLIK coin visible.
 * - The LEVEL01 LEVEL COMPLETE coin is covered by the LEVEL01-local RAW edits in
 *   tools/flik_emblem_edit.py. The remaining Flik's Journey top-right token samples
 *   shared menu texture data loaded from LEVEL00 assets. Directly patching that source
 *   is not level-specific.
 * - Runtime copy hooks tried at the GPU linked-list DMA starter were unsafe; see
 *   mod/mods/flik_result_emblem_experimental.asm. Do not ship that hook.
 * - Active ALLMODS no longer patches the LEVEL00/LEVEL2.RAW shared copy by default.
 *   The flik_menu_result_emblems_level2 stager remains registered for explicit
 *   experiments only. The earlier Training-load failure was caused by the stale
 *   training tutorial EXE cave path, not by the LEVEL00 emblem resize itself.
 * - The Flik's Journey token is not a 3D model. It is a GP0(65) textured
 *   rectangle sprite selecting from pre-rendered tiny flipbook frames.
 * - Training collection was verified without relying on the desyncing movie path:
 *   from scene 0x11, DAT base 0x8011cc50, type-0x3f entries 50-53 live at
 *   0x8011cf78/0x8011cf88/0x8011cf98/0x8011cfa8. F/L start hidden in Training
 *   (status 0), so the debugger test forces entries 50-53 to their LEVEL07_LEVEL1.DAT
 *   disk coords with status 1, then teleports Flik to each runtime coord (file<<5).
 *   The native mask 0x800A65A2 advanced 0->1->3->7->0xf and all four entries
 *   received the consumed Y sentinel 0x80000000.
 * - Stronger Training visual verification moved entries 50-53 to Flik's current
 *   cold-boot Training position instead of moving Flik. This kept the camera stable,
 *   collected all four letters natively (mask 0xf), and captured the spawned token
 *   without the black rectangle regression. For the result screen, writing the known
 *   transition latch 0x800823A0=1 after collection reached the level-complete screen;
 *   this is a verification shortcut, not a discovered Training exit-sector route.
 */
#include <stdint.h>

#define G_DAT_BASE_PTR_ADDR        0x80082498u
#define LEVEL01_DAT_BASE           0x801607F8u

/* LEVEL COMPLETE FLIK coin, observed with gpu.pickObject at movie frame 9000. */
#define RESULT_FLIK_PACKET         0x801E2A38u
#define RESULT_FLIK_WORD0          0x65400040u
#define RESULT_FLIK_WORD1          0x006400F0u
#define RESULT_FLIK_WORD2_CLUT_UV  0x3F798040u
#define RESULT_FLIK_WORD3_SIZE     0x00400040u
#define RESULT_FLIK_TPAGE_X        640u
#define RESULT_FLIK_TPAGE_Y        256u
#define RESULT_FLIK_UV_X           64u
#define RESULT_FLIK_UV_Y           128u
#define RESULT_FLIK_W              64u
#define RESULT_FLIK_H              64u
#define RESULT_FLIK_CLUT_X         912u
#define RESULT_FLIK_CLUT_Y         253u

/*
 * Flik's Journey top-right tiny coin, earlier observed as a GP0(65) textured
 * sprite. Later checks showed that the collecting_FLIK_LEVEL01 movie and
 * collecting_flik.sav do not currently anchor the exact selector-token frame
 * after the final-letter route, so these constants are retained as a candidate
 * until re-picked on a confirmed Flik's Journey selector token.
 */
#define JOURNEY_FLIK_PACKET        0x801CD8ECu
#define JOURNEY_FLIK_WORD0         0x650006C4u
#define JOURNEY_FLIK_WORD1         0x00140100u
#define JOURNEY_FLIK_WORD2_CLUT_UV 0x3E7DC040u
#define JOURNEY_FLIK_WORD3_SIZE    0x00180018u
#define JOURNEY_FLIK_TPAGE_X       640u
#define JOURNEY_FLIK_TPAGE_Y       256u
#define JOURNEY_FLIK_UV_X          64u
#define JOURNEY_FLIK_UV_Y          192u
#define JOURNEY_FLIK_W             24u
#define JOURNEY_FLIK_H             24u
#define JOURNEY_FLIK_CLUT_X        976u
#define JOURNEY_FLIK_CLUT_Y        249u

/*
 * On-disc shared source patched by tools/flik_emblem_edit.py.
 * LEVEL00/LEVEL.RAW chunk 3 and LEVEL00/LEVEL2.RAW chunk 1 decompress to the
 * same 256x256 4bpp page.
 */
#define SHARED_MENU_RESULT_LEVEL_RAW_CHUNK   3u
#define SHARED_MENU_RESULT_LEVEL2_RAW_CHUNK  1u
#define SHARED_RESULT_RECT_X                 64u
#define SHARED_RESULT_RECT_Y                 128u
#define SHARED_RESULT_RECT_W                 64u
#define SHARED_RESULT_RECT_H                 64u
#define SHARED_RESULT_CLUT_SLOT              9u
#define SHARED_JOURNEY_FRAME0_X              0u
#define SHARED_JOURNEY_FRAME0_Y              192u
#define SHARED_JOURNEY_FRAME1_X              64u
#define SHARED_JOURNEY_FRAME1_Y              192u
#define SHARED_JOURNEY_FRAME2_X              112u
#define SHARED_JOURNEY_FRAME2_Y              192u
#define SHARED_JOURNEY_FRAME_W               24u
#define SHARED_JOURNEY_FRAME_H               24u
#define SHARED_JOURNEY_CLUT_SLOT             13u

/* Training badge target used by the GUI's level-specific `training` route. */
#define TRAINING_BADGE_LEVEL_RAW_CHUNK        3u
#define TRAINING_BADGE_RECT_X                 64u
#define TRAINING_BADGE_RECT_Y                 96u
#define TRAINING_BADGE_RECT_W                 64u
#define TRAINING_BADGE_RECT_H                 80u
#define TRAINING_COIN_LEVEL_RAW_CHUNK         3u
#define TRAINING_COIN_RECT_X                  64u
#define TRAINING_COIN_RECT_Y                  128u
#define TRAINING_COIN_RECT_W                  64u
#define TRAINING_COIN_RECT_H                  64u
#define TRAINING_COIN_CLUT_SLOT               9u
#define TRAINING_RESULT_LEVEL2_RAW_CHUNK      1u
#define TRAINING_INGAME_LEVEL_RAW_CHUNK       12u
#define TRAINING_INGAME_LEVEL1_RAW_CHUNK      13u
#define TRAINING_INGAME_RECT_X                64u
#define TRAINING_INGAME_RECT_Y                0u
#define TRAINING_INGAME_RECT_W                64u
#define TRAINING_INGAME_RECT_H                64u
#define TRAINING_INGAME_SHARED_CLUT_X         1008u
#define TRAINING_INGAME_SHARED_CLUT_Y         253u

#define TRAINING_SCENE_ID                     0x11u
#define TRAINING_DAT_BASE                     0x8011CC50u
#define TRAINING_TYPE3F_ENTRY_BASE            0x8011CC58u
#define TRAINING_FLIK_F_ENTRY                 0x8011CF78u
#define TRAINING_FLIK_L_ENTRY                 0x8011CF88u
#define TRAINING_FLIK_I_ENTRY                 0x8011CF98u
#define TRAINING_FLIK_K_ENTRY                 0x8011CFA8u
#define TRAINING_FLIK_MASK_ADDR               0x800A65A2u
#define TYPE3F_CONSUMED_Y_SENTINEL            0x80000000u

/*
 * LEVEL01 custom glyph source still resident on result/menu screens.
 * A debugger-only VRAM copy from this source to RESULT_FLIK_* decodes correctly.
 * It is 64x64, so it cannot be copied directly to JOURNEY_FLIK_* without cropping.
 */
#define LEVEL01_GLYPH_VRAM_X       720u
#define LEVEL01_GLYPH_VRAM_Y       0u
#define LEVEL01_GLYPH_CLUT_X       784u
#define LEVEL01_GLYPH_CLUT_Y       215u

/*
 * GP0 VRAM-to-VRAM copy constants used in the failed experimental hook:
 * command: 0x80000000
 * tile source: x=720,y=0, width=16 VRAM words, height=64 rows
 * tile destination: x=656,y=384, width=16 words, height=64 rows
 * CLUT source: x=784,y=215, width=16 words, height=1 row
 * CLUT destination: x=912,y=253, width=16 words, height=1 row
 */
```

## The results screen itself (C05, 2026-08-04)

The level-complete screen is [[FUNC_800B7DA0_results_screen_evaluate_and_draw]], in
the **`BITS/MEMORY.BIN`** overlay (loaded verbatim at `0x800B5788`; that file is the
only one of the 326 retail files containing this code). It evaluates the three
completion axes, **sets** the per-level unlock bits, and draws the screen.

| Axis | Source | Condition | Bit | Earned tile |
|---|---|---|---|---|
| grain | `0x800A65A1` (u8, clamped to 50) | `== 50` | `0x01` | 59 |
| FLIK letters | `0x800A65A2` (u8 mask) | `== 0x0F` | `0x02` | 58 |
| enemies | `0x800A658E` (s16 quota) | `== 0` | `0x04` | 57 |

Bits go into `unlock_array[level]` (`0x8009B878`, index `0x8008245C`); all three set
means `7`, which is what [[FUNC_800502C4_fmv_sequence_completion_check]] requires to
unlock the level's bonus movie clip and what
[[FUNC_80055478_serialize_savegame_buffer]] persists. Because all three bits are
written by this one routine, the array byte transitions `0 → 7` atomically.

**Locked vs earned:** while a row's animated counter has not reached its total, the
row draws **tile 52 — the red `?`** — at `x = 248`. Once it reaches the total, a
newly-earned axis draws its tile full-bright at `x = 240` via `hud_draw_sprite_tile`
`0x80025F54`, and an axis earned on a previous visit draws the same tile **dimmed**
via `0x80026858` with `(128,128,128)` modulation.

The third counter is *defeated / total* **enemies** — the denominator is
`0x80082258` (9 on Birdnest, matching the on-screen `/09`). This is proven by the
condition itself, correcting the earlier "seed tokens" labelling.

Distinct from the **in-world** reward-token markers drawn during gameplay by
[[FUNC_80051B84_reward_token_marker_stage]]. **Correction history:** this sentence
formerly said the same bits "tint" the floating sprite. That was wrong: the downstream
consumer uses the value to select GPU semi-transparency (earned markers are translucent;
unearned markers are opaque), without changing the primitive RGB bytes.

### Counter animation (2026-08-04)

One per-frame loop, countdown `s3` seeded to 800. Three numerators share the law
`if (n < target && fp == 0) { n++; sfx(14); }` with `fp` toggling every frame, so the
counters tick at **30 Hz**. Targets: grain `[0x800A65A1]`, FLIK
`popcount_table[0x800BE444 + mask]`, enemies `[0x80082258] − [0x800A658E]`
(total − remaining = defeated).

Digits go through `hud_draw_sprite_tile(x, y, tile, glyph)` with tile **56** as the digit
font and glyph **10** as `/`. The grain denominator is the **literal** glyph pair `5`,`0`,
so 50 grain is required on every level; the enemy total is the only per-level number.
The header tile is latch-driven (`0x800823A0 == 1` → tile 54, else 55).

The face-button press is a **fast-forward, not a skip**: a fresh press on mask `0xF000`
inside `25 ≤ s3 < 740` either ends the screen shortly (all counters already done) or
**snaps the numerators to their targets**. Pinned 46/46 offline by
`tools/phase4_c05_counter_animation.c`.
