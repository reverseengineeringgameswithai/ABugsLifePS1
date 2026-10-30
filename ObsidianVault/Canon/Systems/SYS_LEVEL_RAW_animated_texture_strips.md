---
kind: system
id: SYS_LEVEL_RAW_ANIMATED_TEXTURE_STRIPS
aliases: [LEVEL.RAW animated texture strips, subtype 0x22, ambient tile uploader]
status: confirmed
confidence: high
source_state: original_game
evidence:
  - EXP_2026-08-03_phase4_e01_terrain_visual
  - analysis/phase4_e01_closure.json
related_functions:
  - 0x8003B830
  - 0x80026DF4
  - 0x80056F68
  - 0x800628C0
---

# LEVEL.RAW animated texture strips

## Confirmed path

LEVEL.RAW subtype 0x22 is an animated texture-strip resource.

- Loader 0x8003B830 publishes chunk+8 to the primary per-tile data table at 0x80089638 + tile*4.
- Uploader 0x80026DF4 joins that data with the descriptor at 0x80096B98 + tile*4, calculates the destination rectangle and frame byte offset, then calls GPU upload helper 0x800628C0.
- Resident ambient driver 0x80056F68 drives LEVEL01 tiles 124 and 125. Scene overlays also call the uploader directly for exceptional tiles.

## LEVEL01 tile 125

The exact pristine runtime join is:

- subtype-0x22 chunk base 0x800C0920;
- strip data 0x800C0928;
- descriptor 0x8008209C;
- 40x19 source frame, 4bpp;
- GPU destination (259,38), transfer size 10x19 VRAM words/pixels.

At frame 12519, 0x80026DF4(tile=125, buffer=0, frame=5) was followed in the same frame by the matching GP0 A0 transfer. This confirms that tile 125 produces the animated scenery cell previously observed around coarse VRAM coordinate (256,32).

## Recurrence

Tile 125 uses frame byte 0x800A65A6 and countdown 0x800A65A7.

- Gate false: reset and upload frame 0.
- Gate true: after countdown expiration, script/RNG bytes select delay (byte & 7)+3 and frame (next_byte & 3)+2.
- Result: animated frames 2 through 5, with 3 through 10 driver ticks between selections.

The gate helper 0x80045678 is intentionally not semantically overnamed. Its exact proven result is a per-slot bit-2 test after matching the supplied pointer.

## Campaign bounds

The C campaign census found 228 subtype-0x22 strips in 18 RAW files with zero decode errors. A static scan of all 20 level overlays found six direct uploader calls for exceptional level-owned animations and no direct call to either resident wrapper.

See [[EXP_2026-08-03_phase4_e01_terrain_visual]] and analysis/phase4_e01_closure.json for hashes, call sites, live cycles, and bounded unknowns.
