---
kind: function
id: FUNC_8003E928
aliases: [FUNC_8003E928, 0x8003e928]
address: 0x8003E928
name: backdrop_tile_builder_8003e928
status: static_seen
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: []
src_paths:
  - src_re/backdrop_tile_builder_8003e928.c
patch_policy: hook_candidate
---

# FUNC_8003E928 - backdrop tile builder 8003e928

## Purpose

Draws the bright-blue **horizon haze band** (and the dirt-wall backdrop) as a row of textured rectangles tiled across the screen. Called **once per frame** from `0x80039b24`; emits ~24 primitives via the generic primitive builder at `0x8003ec50` (24 calls return to `0x8003ecbc`). 2026-07-06: `tools/build_g3_native.py --suppress-horizon` bakes this same neutralizer into the resident EXE for the GTE-native replacement disc. Patch site: `SCUS_942.88+0x2F128`; runtime bytes become `08 00 E0 03 00 00 00 00`. Validation on `build/ABL_g3native.cue`: full `g3native_movie.movie.json` replay still passes (`RENDER_C=0`, `FUNC_80010000=7301`, no plunge), and `gpu.pickObject` at former texpage-`0x68D` points `(310,82)` and `(300,105)` returns background. This removes the P2 backdrop sprite strip; it does not touch the target native GTE floor emitter.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8003E928.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8003E928`
- Name: `backdrop_tile_builder_8003e928`
- Original note: `ObsidianVault/Functions/FUNC_8003E928.md`
- Source path: `src_re/backdrop_tile_builder_8003e928.c`

## C source excerpt

Source: `src_re/backdrop_tile_builder_8003e928.c`

```c
/* ============================================================================
 * backdrop_tile_builder_8003e928.c — the looping panorama tile layer [HRE-009 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : FUNC_8003E928 (bounds exact ..0x8003EEC4). Packet x|y word
 *                      writers observed live at 0x8003EC50/5C/68 (accessLog on a
 *                      picked backdrop sprite's DMA packet). Helper jal targets
 *                      0x80061C28/0x80061C50 (packet init/link, libgpu-style).
 * CONFIDENCE         : CONFIRMED — scroll law read from the disasm AND live-verified
 *                      against gp+0x530 across camera taps (±1 = the +0x1FFF arith-
 *                      shift rounding on negative yaw); tile geometry from
 *                      gpu.pickObject; texture from gpu.decodeTexture (VRAM 832,0
 *                      8bpp + CLUT 768,209 reproduces the chunk-29 image 1:1).
 * SOURCE NOTES       : ObsidianVault/Systems/Backdrop and sky layer.md; operator
 *                      save `backdrop` (high vantage, clean horizon).
 *
 * WHAT THE PLAYER SEES: turning the camera scrolls the far horizon; the picture
 * repeats — because this builder lays out the chunk-29 panorama as a SCREEN-SPACE
 * grid of GP0(65) sprite tiles (64x32 px, u alternating 0/64, v rows 0/32/64) whose
 * x-grid starts at a phase computed MODULO THE IMAGE WIDTH from the camera yaw.
 * The panorama loops every 128 screen px; a full 360-degree turn scrolls it exactly
 * 4096 * 7/16 = 1792 px = 14.0 image-widths (~4.98 px/deg). Camera POSITION never
 * enters the formula: the backdrop is an infinite-distance, rotation-only skybox.
 * ============================================================================ */

#include "re_types.h"

#define LH(p)   (*(int16_t  *)(p))
#define LW(p)   (*(int32_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))

#define G_CAMERA_YAW      0x800824B2u /* s16, PS1 angle units: 4096 = 360 deg (NEW global) */
#define G_BACKDROP_W      0x800771B0u /* live image width  (LEVEL01: 128) — chunk-29 header */
#define G_BACKDROP_H      0x800771B4u /* live image height (LEVEL01: 96)                    */
#define G_SCROLL_PHASE    0x800822C8u /* gp+0x530: tile-grid start phase (px, 0..W-1)       */
#define G_YAW_PREV        0x80082398u /* gp+0x600: previous -yaw (incremental branch)       */
#define G_TILE_CLIP       0x800823BEu /* s16 per-tile right-clip helper                     */
/* Texture: chunk-29 image uploaded at VRAM (832,0), 8bpp, CLUT (768,209).
 * Tiles: GP0(65) opaque raw-UV sprites, 64x32; u cycles 0/64, v rows 0/32/64. */

void backdrop_tile_builder_8003e928(void)
{
    /* --- scroll phase from the camera yaw (first-run branch; an incremental
     *     branch with +/-0x1000 wraparound follows on later frames) --- */
    int yaw = LH(G_CAMERA_YAW);
    int v = -yaw;
    int px = (v * 7) << 9;            /* v*3584 */
    if (px < 0) px += 0x1FFF;         /* arith-shift floor correction */
    px >>= 13;                        /* = -yaw * 7/16 px */
    px &= 0xFF;
    int phase = px % LW(G_BACKDROP_W);/* MODULO IMAGE WIDTH -> the panorama LOOPS */
    SW(G_SCROLL_PHASE, phase);

    /* --- tile emission (0x8003EBEC..): for each 64-px column across the screen,
     *     starting at x = -phase, emit GP0(65) sprites for each 32-px v-row:
     *       packet+0x08 = x|y            (writers 0x8003EC50/5C/68 region)
     *       packet+0x0C = clut|v|u       (u = (column*64) % image_width)
     *       packet+0x10 = w=64|h(clipped via G_TILE_CLIP / row remainder)
     *     rows capped by G_BACKDROP_H (s7 <= 0x100). Linked into the background
     *     OT chain (the pass DrawOTag kicks before the scene OT). --- */
}

/* ----------------------------------------------------------------------------
 * EMPIRICAL FACTS (operator save `backdrop`, 2026-07-02):
 *  - gpu.pickObject on the horizon: GP0(65) 64x32 sprites, texpage (832,0) mode-1,
 *    CLUT (768,209); sky pixels report "background" (the GP0 02 fill, no drawable).
 *  - gpu.decodeTexture(832,0,128,96,8bpp,clut 768,209) == the chunk-29 image.
 *  - Right-taps: yaw -40 units (3.5 deg)/tap, tile x slides -17..18 px/tap
 *    (~5 px/deg); u alternates 0/64 as tiles pass a fixed screen pixel.
 *  - Live phase (gp+0x530) matches (-yaw*7/16) mod 128 within rounding.
 *  - Full turn = 4096*7/16 = 1792 px = exactly 14 image-widths.
 *  - No camera-position term anywhere: pure rotation-only skybox (settles the
 *    HRE-009 parallax question; earlier translation-diff ambiguity was noise).
 * ---------------------------------------------------------------------------- */

/* ----------------------------------------------------------------------------
 * G3-NATIVE P2 BAKE (2026-07-06):
 * In the Tier-3 GTE-native replacement build, this function's GP0(65) panorama
 * sprites are removable behind the authored terrain. Live test on
 * build/ABL_g3native.cue: entry `jr ra; nop` removes texpage 0x68D / CLUT
 * 0x3470 picks at the movie frame ~5300 background strip, while FUNC_80010000
 * stays active and Flik/collision validation still pass. build_g3_native.py
 * exposes this as `--suppress-horizon`, a size-preserving resident-EXE patch at
 * SCUS_942.88+0x2F128 (0x8003E928 -> 08 00 E0 03 00 00 00 00).
 *
 * CORRECTION (2026-07-06): this function is not gameplay-only. Manual boot
 * showed the same global stub removes/changes the level-select/menu backdrop
 * too. Treat `--suppress-horizon` as an opt-in A/B experiment unless a future
 * patch gates it to the LEVEL01 gameplay context.
 * ---------------------------------------------------------------------------- */

/* ----------------------------------------------------------------------------
 * P54 (2026-07-07) — SOURCE-LEVEL suppression that IS menu-safe: instead of
 * stubbing this menu-shared function, blank its per-level INPUT — fill the
 * LEVEL01 chunk-29 panorama image with its own top-row sky palette index
 * (pixels only; the 0x300 palette region holds non-color bytes other texture
 * machinery consumes — backdrop_edit.py authoring rules). The GP0(65) band
 * then renders flat sky and the GP0(02) sky fill (palette[img[0]]) matches
 * seamlessly. Implemented as build_g3_native.py --blank-backdrop via
 * backdrop_edit.find_backdrop_chunk/splice_and_verify. The GP0(60) untextured
 * fog sprite (color in the packet, not the image) remains as a haze band.
 * ---------------------------------------------------------------------------- */

/* ----------------------------------------------------------------------------
 * P54b (2026-07-07) — LEVEL01 has AT LEAST TWO panorama images, and this
 * builder tiles whichever is resident for the zone: the primary 128x96 grass
 * horizon (RAW full+0x8AFB8; what backdrop_edit.find_backdrop_chunk returns)
 * AND a second 128x128 far-terrain image (RAW full+0x39550) whose tiles read
 * as sweeping in-level pebble ridges/branches (the operator's terrain.png).
 * The VRAM strip at (832,0) is RE-UPLOADED per zone, which is why blanking
 * only the 128x96 image left the masses textured in later zones. Surgical
 * removal that KEEPS the horizon: blank only the 128x128 image's pixels to
 * its own sky index (build_g3_native.py --blank-far-terrain). [gp+0x404]
 * (0x8008219C) is a dynamic counter the game rewrites — NOT a kill lever.
 * ---------------------------------------------------------------------------- */
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8003E928.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8003E928.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8003E928.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
