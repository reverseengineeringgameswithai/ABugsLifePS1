---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/HUD letter glyphs and word swap.md
aliases:
  - "HUD letter glyphs and word swap"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/HUD letter glyphs and word swap.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/HUD_letter_glyphs_and_word_swap.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: HUD letter glyphs and word swap
type: system
confidence: CONFIRMED
tags: [system, hud, glyph, flik, atta, texture, level-editor, mod, level01]
updated: 2026-07-07
---
# HUD letter glyphs — "FLIK" → any 4-letter word

> The LEVEL01 status HUD (hold **SELECT** ~0.5 s) shows a 4-letter word — "FLIK" in retail. Each
> letter is a **24×23, 4-bit golden sprite** that **spins 360° about the vertical axis** (~16-frame
> strip). The letters are **texture data**, not characters — so swapping the word is a *graphics*
> edit. This note documents the end-to-end, editor-facing pipeline, verified in-game showing **ATTA**
> with the spin intact (2026-06-23, cold-boot of the edited disc).

> [!note] 2026-07-05 FLIK5 test
> Retail is still a 4-slot glyph/collection design. A one-off **FLIKF** test was proven by code patch,
> not by changing the texture pipeline: append a normal kind-`0x10` F entry, make the F handler assign
> bit `0x10` only for appended entry 70, compare completion against mask `0x1f`, and draw an extra
> SELECT-panel tile `0x10` at `x=0xd0`. Do **not** copy/overwrite pickup descriptor bytes to fake a
> new F kind: the first attempt reused a shared descriptor slot and replaced the top-left Flik head HUD
> model. See [[Experiment - FLIK5 five-letter token gate]].

> [!note] 2026-07-05 FLIK completion emblem image
> The collected FLIK emblem looks **silver** on screen, but live `gpu.pickObject` showed the visible
> top GP0(2c) quad samples the gold-looking static texture page and is recolored by CLUT `x=784,y=215`.
> Patch both source copies: `LEVEL01/LEVEL.RAW` texture chunk **13** and `LEVEL01/LEVEL1.RAW` texture
> chunk **12**, rect **64×64 at x=64,y=0** in both. `tools/flik_emblem_edit.py` replaces both from a
> user PNG and `mod/build.py --mods` uses the auto-layout manifest when that size-changing RAW edit is
> selected. **Training is LEVEL00, not LEVEL01:** its FLIK badge is `LEVEL00/LEVEL.RAW` chunk **3**,
> rect **x=64,y=96,w=64,h=80**. See [[Experiment - FLIK emblem image replacement]].
>
> [!note] 2026-07-06 routing fix
> `collecting_flik.sav` + `UP` for 60 frames reconfirmed the Anthill completion emblem as a
> level-local glyph/tile: tpage `704,0`, CLUT `784,215`, UV `64..127/0..63`. The manifest/build path
> now uses `flik_emblem_edit.LEVEL_TARGETS`: `training` maps only to `LEVEL00/LEVEL.RAW`; `anthill`
> maps only to `LEVEL01/LEVEL.RAW` + `LEVEL01/LEVEL1.RAW`; unmapped levels no longer silently patch
> LEVEL01.
>
> [!note] 2026-07-06 colour fix
> The emblem is still a 4bpp glyph, but it is **not limited to grayscale**. The first image workflow
> only rewrote texel indices and left the runtime silver CLUT untouched, so coloured art collapsed to
> black/white/grey. The Anthill draw's CLUT is on-disc palette **slot 1** in the same source chunks
> (`LEVEL.RAW` chunk 13 and `LEVEL1.RAW` chunk 12). `tools/flik_emblem_edit.py` now writes a derived
> 15-colour palette to that slot and maps alpha to index 0. Index 0 must stay the native disc
> green-key (`0,255,0`), not RGB black, or it renders as a black square instead of becoming
> transparent.
>
> [!note] 2026-07-06 in-world pickup glyph extraction
> The F/L/I/K **pickup objects** are separate from the SELECT-panel strip below. `SPINNING_F.sav`,
> `SPINNING_L.sav`, `SPINNING_I.sav`, and `SPINNING_K.sav` were loaded against
> `build/ABL_ALLMODS.cue`; holding **L1+DOWN** kept each token against the sky for GPU capture.
> `gpu.pickObject` / `gpu.traceRegion` resolved the visible letter face as a 4bpp textured quad on
> tpage **x=640,y=0** using the same golden CLUT **x=880,y=217**. The face tiles are static
> **24×24** UVs in a 2×2 block: F `(u=192,v=64)`, L `(216,64)`, I `(192,88)`, K `(216,88)`.
> Later Training work showed those UVs are also live destinations for repeated narrow **6×24** VRAM
> uploads; the extracted 24×24 tile is a phase/source sample, not the whole native spin model.
> Extracted reference files live at
> `mod/glyphs/pickup_letters/` (`metadata.json` has save hashes and debugger provenance).
>
> [!note] 2026-07-06 Training in-world `TRAINING` word
> The Training pickup word is patched separately from the LEVEL01 SELECT-panel word strip.
> User-facing target: **Training / LEVEL00**, scene id `0x11`. Retail disc resources for these
> in-world pickups live in the **LEVEL07** folder: `LEVEL07/LEVEL1.DAT`, `LEVEL07/LEVEL.RAW`,
> and `LEVEL07/LEVEL1.RAW`. `tools/training_word_pickups.py` keeps native
> kinds `0x10..0x13`, remaps only Training entries 50-53 and appended entries 62-65, replaces
> the native F/L/I/K spin strips with T/R/A/I, and appends native-style N/G strips on free
> kinds `0x26/0x27`. The live pickup page is `LEVEL07/LEVEL.RAW` chunk 11 /
> `LEVEL07/LEVEL1.RAW` chunk 12; chunks 12/13 were an off-by-one dead end. Reference word
> order/UVs:
> T `(192,112)`, R `(216,112)`, A `(192,136)`, I `(192,88)`, N `(216,136)`, I `(192,88)`,
> N `(216,136)`, G `(192,160)`.
> Cave note: the current Training hook map is collection `0x800811C0`, compare `0x800812B8`,
> extra-letter anim pump `0x800813F0`, projector visual gate `0x80081460`, descriptor pointers
> `0x8008126C`, and SELECT full-row gate `0x8008157C` reached from `0x80052D98`. Do not reuse `0x8007FBC8` for this gate;
> it is overwritten during Training scene load and previously caused the `PC=0x000000a0`
> blank-screen failure. Do not reuse `0x8007F130..0x8007F16F` for the helper/table either:
> that clobbered live retail word `0x8007F16C`, later read around `0x800616C0`, causing the
> Training crash. Old helper descriptor/table offsets `+0x2c`/`+0x38` rendered the letters as
> horizontal colored bands; the current path avoids that helper table and uses native strip
> uploads instead. Save states restore captured VRAM, so `visual_FLIK_garbage.sav` remains a
> stale-texture reproduction anchor; verify texture fixes from cold boot/movie replay. Keep
> `0x800811BC` as a `nop`: blackberry `CAVE_THROW` uses it as the return-jump delay slot, and the
> old collection cave there crashed berry throws.

## What the letters are
- **Not text.** There is no A–Z font; only the 4 FLIK glyph slots + object icons exist as tiles → see
  the auto-memory `flik-letters-are-glyphs`. So "FLIK"→"ATTA" is a texture replace, not a char swap.
- **Glyph format:** 24×23 texels, 4-bit (16-colour), row-major as 6 LE halfwords/row × 23 = **276
  bytes**. Texels index a fixed **golden CLUT** (index 0 = transparent; 1..15 = gold ramp, *bright→dark*,
  lum 221→22). CLUT read live from VRAM **(880,217)** on the pristine disc → `mod/glyphs/golden_clut.json`.
- **Animation:** each slot is a strip of ~16 frames at **0x120 stride** filling its LEVEL.RAW sprite
  chunk; the glyph spins 360° about the vertical axis, on-screen width following **|cos θ|** (face-on →
  edge-on sliver → face-on; edge-on twice per turn). Frames play in **offset order**. Confirmed by
  profiling the original F strip (widths 16,16,14,9,5,9,14,16,… = two |cos| dips 8 frames apart).

## In-world pickup letter face tiles
The native collectible objects for F/L/I/K render differently from the SELECT-panel word:
- **Format:** 24×24, 4bpp, same golden CLUT `x=880,y=217`.
- **Runtime texture page:** tpage `x=640,y=0`.
- **UV tile map:** F `192,64`; L `216,64`; I `192,88`; K `216,88`.
- **Extraction:** `gpu.decodeTexture` source coordinates are `x = 640 + u/4`, `y = v`, `w=24`, `h=24`,
  `bpp=4`, `clut_x=880`, `clut_y=217`.
- **Reference output:** `mod/glyphs/pickup_letters/F.png` etc are raw texture-space tiles; the
  `display_oriented/` copies are easier to read as letters.
- **Spin model:** native F/L/I/K cells are refreshed by repeated narrow VRAM uploads while the object
  draw code projects a textured quad. Treat a captured 24x24 tile as one phase/source sample, not
  the full in-world animation.
- **Training generated letters:** `mod/glyphs/pickup_letters/training/` contains T/R/A/N/G art for
  `tools/training_word_pickups.py`; native I is reused as source art, and the stager bakes
  8-frame spin strips for T/R/A/I/N/G.

## Where they live / how drawn
- **Draw code:** `src_re/hud_800526f4.c : draw_flik_bit_panel` — `for i in 0..3: draw tile (0x10+i) at
  x=0x70+i*0x18`. The C only names tile IDs **0x10/0x11/0x12/0x13** (= F/L/I/K slots); the pixels are in
  the texture atlas. (Scene-5 record icons reuse tiles 0x32/0x34/0x35/0x33.) See [[FUNC_800526F4]].
- **On disc:** the HUD uploads the glyph atlas from **BOTH** `LEVEL01/LEVEL.RAW` and `LEVEL01/LEVEL1.RAW`
  (each holds the strip; patch both or it reverts). HUD first-frame offsets (decompressed):
  `LEVEL.RAW` F/L/I/K = `0x77c60/0x78c2c/0x79bf8/0x7abc4`; `LEVEL1.RAW` = `0x6f954/0x70920/0x718ec/0x728b8`.
- **Why not live:** the game re-decompresses + re-uploads the atlas to reallocating RAM each frame, so
  live VRAM/RAM edits revert (whack-a-mole). The **disc edit is the only persistent route** — and the
  correct level-editor mechanism.

## Editor-facing pipeline (the "type a word" feature)
Front end = **`mod/glyphs/`** (see its `README.md`):
- `flik_word.h` — **the word** (`#define FLIK_WORD "ATTA"`, slot 0..3). Single source of truth.
- `letters/<L>.png` — per-letter art (gold on transparent). **F/L/I/K extracted lossless** (round-trip
  0/276 bytes); **A/T** = the new gold letters for ATTA. Any A–Z works; drop in a `<L>.png`.
- `golden_clut.json` — lets conversion run **offline** (no emulator).

Bridge = **`tools/glyph_assets.py`**:
- `image_to_glyph(png)` — crop → scale to 24×23 cell → nearest-CLUT match (alpha → transparent).
- `image_to_spin_frames(png,n)` — **synthesize** the n-frame spin from one flat image: squash by
  `|cos θ|`, mirror the back half. A single front-view PNG animates like the original 3D glyph (only a
  front view is supplied), so the spin survives the swap.

Build = **`tools/patch_flik_word.py`** (reads `FLIK_WORD`): decode LEVEL.RAW → overwrite each slot's
full spin strip with synthesized frames (offset = play order) → recompress only touched chunks →
reassemble **both** LEVEL.RAW + LEVEL1.RAW (`+~13 KB`, LBA-shift-safe, file loader is by-name). Then
`mkpsxiso REBUILD/abl_autolayout.xml`.

## Completion emblem image
- FLIK-letter completion calls `fcn.8005044c(-0x0b, &player)` and then, if progress is below 9,
  `fcn.8005044c(-8, &player)`. Static disassembly shows `-0x0b` selects descriptor pointer
  `0x80078244` through the negative-effect table rooted at `0x80078330`.
- Live `gpu.pickObject` on the collected emblem identifies the visible top primitive as `GP0(2c)` with
  texture page `raw=0x066b` (VRAM x=704,y=0), CLUT `raw=0x35f1` (x=784,y=215), and UV
  **64..127 / 0..63**. The static tile looks gold; the runtime CLUT makes it silver.
- Editable source copies are `LEVEL01/LEVEL.RAW` chunk **13** and `LEVEL01/LEVEL1.RAW` chunk **12**,
  rect **x=64,y=0,w=64,h=64** in both.
- The matching on-disc CLUT is palette **slot 1** in both chunks. Patch that slot with the texel data
  or the replacement renders through the native silver palette. Keep slot entry 0 as the native
  green-key transparent colour and quantize opaque pixels only to indices 1..15.
- Training uses a separate source: `LEVEL00/LEVEL.RAW` chunk **3**, rect
  **x=64,y=96,w=64,h=80**. The extra 16px height covers the stored `FLIK` label below the circular
  icon; replacing only 64x64 leaves old lettering visible.
- Tool path: `tools/flik_emblem_edit.py <image> --stage-out <RAW>` or manifest asset
  `tool: flik_emblem` plus `tool: flik_emblem_level1` with `params.image`. The GUI exposes one
  **FLIK emblem image** picker for mapped levels and writes both Anthill entries. The picker is
  disabled for levels whose source tile has not been identified yet.

## Slot map
| Slot | Tile | HUD x | Retail | ATTA |
|---|---|---|---|---|
| 0 | 0x10 | 0x70 | F | A |
| 1 | 0x11 | 0x88 | L | T |
| 2 | 0x12 | 0xA0 | I | T |
| 3 | 0x13 | 0xB8 | K | A |

## Length / completion notes
- Retail completion is the low nibble of `0x800A65A2`: F/L/I/K set bits `0x01/0x02/0x04/0x08`,
  and the shared completion tail runs when the mask equals `0x0f`.
- The 2026-07-05 FLIK5 proof shows the token gate can be extended without touching glyph assets:
  appended entry 70 is a duplicate native F (`kind 0x10`), the F handler special-cases that entry to
  set bit `0x10`, and the completion check becomes `0x1f`. Verified from cold boot: after four
  letters mask `0x0f`, progress/lives byte `0x800A65A0` stayed `5`; after fifth letter mask `0x1f`,
  byte advanced to `6`.
- The SELECT status panel can draw an extra F by issuing one more draw of tile `0x10` at `x=0xd0`.
  This is a code patch; the existing texture-word tools remain 4-slot tools.
- The Training `TRAINING` pickup word extends the in-world collection gate to 8 bits only in scene
  `0x11`: entries 50-53 map to bits 0..3, appended entries 62-65 map to bits 4..7, and the dynamic
  compare cave returns mask `0xff` for Training but `0x0f` everywhere else.
- 2026-07-07 Training SELECT layout: the first 8-slot version appended slots 4-7 after the native
  row from the tail hook, which left `TRAINING` too far right. Current `tools/training_word_pickups.py`
  hooks the first letter draw at `0x80052D98`, scene-gates on Training, and draws all 8 slots from
  RAW-resident code at `x=0x48+i*0x18`. Non-Training replays the displaced native bitmask load and
  keeps the original 4-letter row at `0x70,0x88,0xA0,0xB8`.

## Verification (2026-06-23)
- Disc **`REBUILD/ABL_ATTA_GOLD.bin/.cue`** cold-booted on the isolated DuckStation (port 23460) via the
  from-boot movie `flik_to_level01_stall.mv.movie.json` → LEVEL01; held **SELECT** to raise the panel.
- Captured a frame sequence: the panel reads **A-T-T-A**, and the letters are at **different rotation
  phases** across frames (e.g. slot 2 edge-on in one shot, slot 0 edge-on in the next) → the **spin
  works**. The two A's (slots 0 & 3, incl. **K→A**) are face-on and unmistakable. Operator also
  confirmed manually.
- The earlier all-frames-identical approach showed ATTA but **frozen** (no spin) — fixed by writing the
  per-frame spin strip.

## Related
- auto-memory `flik-letters-are-glyphs` (step-1 glyph-vs-text + earlier ATTA discs) · [[FUNC_800526F4]]
- [[Menu and HUD structure]] · [[Grain emblem and HUD total mod]] · [[ABL Level Editor]]
- [[Experiment - FLIK5 five-letter token gate]]
- [[Experiment - FLIK emblem image replacement]]
- LEVEL.RAW codec: `tools/decode_level_raw.py` + `recompress_level_raw.py`
