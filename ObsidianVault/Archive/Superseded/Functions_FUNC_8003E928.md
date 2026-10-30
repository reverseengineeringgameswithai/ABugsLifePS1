---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8003E928.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8003E928.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8003E928_unnamed.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8003E928
type: function
confidence: CONFIRMED
address: "0x8003E928"
tags: [function, rendering, sky, horizon, haze]
---

# FUNC_8003E928 — horizon / sky-strip draw routine ("the haze")

Draws the bright-blue **horizon haze band** (and the dirt-wall backdrop) as a row of textured rectangles tiled across the screen. Called **once per frame** from `0x80039b24`; emits ~24 primitives via the generic primitive builder at `0x8003ec50` (24 calls return to `0x8003ecbc`).

## Behavior (CONFIRMED)
- Prologue `addiu sp,sp,-88 ; lw v1,0x404(gp)` at `0x8003e928`.
- The tiling loop steps x across the 512-px screen by the value at **`0x800771b0`** (=128 → ~4-9 tiles); rect width 64 (`addiu v0,zero,64` @0x8003ec80), height 32 (`s5=32`). Reads game data at `0x800a7de2` and the sky-color region `0x8007xxxx`.
- The rects are GP0 `0x65` (textured), modulating a sky texture → the visible band is at screen-y≈76, BGR555 `0x6d66` ≈ RGB(48,88,216) (the original daytime sky colour). This band is **separate from** the GP0 0x02 background fill ([[Finding - Sky is a GP0 background fill]]) and is NOT controlled by the `0x800771bc/c0/c4` cache — patching that cache leaves this band bright.
- Runs AFTER the render hook `0x80062d04` (cycle order: hook → this fn emit → caller); the band is therefore DMA'd to VRAM after the hook, so an overlay band at the hook gets overdrawn.

## Mod lever
Neutralize with **`jr ra ; nop`** (`0x03E00008 0x00000000`) at `0x8003e928` → the horizon haze band disappears (smooth dark sky to the grass line). Side effect: the **dirt-wall backdrop** it also draws is removed (grass meets ground directly). Restore prologue = `0x27BDFFA8 0x8F830404`. Used by [[Finding - Persistent night render hook]] / `tools/abl_night_hook.py` (`HAZE_FN`).

## Tier-3 GTE-Native P2 Use

2026-07-06: `tools/build_g3_native.py --suppress-horizon` bakes this same neutralizer into the resident EXE for the
GTE-native replacement disc. Patch site: `SCUS_942.88+0x2F128`; runtime bytes become `08 00 E0 03 00 00 00 00`.
Validation on `build/ABL_g3native.cue`: full `g3native_movie.movie.json` replay still passes (`RENDER_C=0`,
`FUNC_80010000=7301`, no plunge), and `gpu.pickObject` at former texpage-`0x68D` points `(310,82)` and `(300,105)`
returns background. This removes the P2 backdrop sprite strip; it does not touch the target native GTE floor emitter.

## Related
[[Finding - Persistent night render hook]] · [[Finding - Sky is a GP0 background fill]] · [[FUNC_800639CC]] · [[MEM - Sky DRAWENV color cache 800771BC]]

## Source
Live disassembly + exec-trace this session (write-watch of OT haze rect `0x801d54fc` → builder `0x8003ec50`; entry scan + caller trace).
