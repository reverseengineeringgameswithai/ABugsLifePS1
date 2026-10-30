---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Author a custom backdrop.md
aliases:
  - "Playbook - Author a custom backdrop"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Author a custom backdrop.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Author a custom backdrop
type: playbook
status: proven end-to-end on LEVEL01 (ABL_NIGHTSKY); tooling generalizes with known limits
updated: 2026-07-02
tags: [playbook, backdrop, sky, horizon, chunk29, night, leveleditor, hre-009]
---

# Playbook — Author a custom backdrop (sky + horizon) for a level

> The reusable recipe distilled from the ABL_NIGHTSKY build (day→night LEVEL01 with a
> full-sky starfield). System reference: [[Backdrop and sky layer]]. Tool:
> `tools/backdrop_edit.py`. Cave: `mod/caves/night_stars.c` + `mod/patch_nightsky.asm`.

## What you're editing (two independent layers)

1. **The panorama image** — a palettized W×H image at the start of a LEVEL.RAW chunk
   (LEVEL01: chunk 29, 128×96; LEVEL07: chunk 30, 128×160). Drawn as 64×32 screen-space
   sprite tiles, horizontally looping (`phase = −yaw·7/16 mod W`; 360° = 14 image-widths
   at W=128), vertically anchored at header field `b` + camera pitch. The **sky fill**
   above the band is a flat GP0-02 color taken from this image's **palette**.
2. **Optional geometry above the band** — the panorama cannot extend above its band
   (taller images are blocked: they upload inside the level's VRAM texture-atlas strips,
   and the rows below belong to scene textures). Anything in the fill region (stars,
   etc.) must be drawn as primitives: see the night_stars cave pattern below.

## Step-by-step

```bash
# 1. See what the level has (works for any level; finds the chunk automatically)
python3 tools/backdrop_edit.py extract LEVEL01 -o preview.png

# 2a. Night preset (the proven ABL_NIGHTSKY transform: dark blue sky family, dimmed
#     ground, flattened hills, N sparse faint in-band stars)
python3 tools/backdrop_edit.py night LEVEL01 --stars 10 -o /tmp/LEVEL_night.RAW

# 2b. ...or a fully custom panorama (quantized to ≤250 colors; entry-0 rule applied)
python3 tools/backdrop_edit.py replace LEVEL01 --image my_panorama.png -o /tmp/LEVEL_new.RAW

# 3. Build a bootable disc (stages LEVEL.RAW + optionally a patched EXE, restores after)
python3 tools/backdrop_edit.py build --raw /tmp/LEVEL_night.RAW --level-dir LEVEL01 \
        [--exe /tmp/SCUS_patched.88] --out REBUILD/ABL_MYSKY
```

Every `night`/`replace` run performs the **full-file decode regression** (all chunks
byte-identical except the edited one) before writing — do not bypass it.

## The rules (each one broke a build before it was a rule)

1. **Tileable in X.** The engine loops the image; a seam shows every 128 px.
2. **Palette entry 0 = the image's top-row color.** The flat sky fill reads the palette
   and must continue the image's top edge seamlessly.
3. **Only touch palette entries the image actually indexes.** The 0x300 "palette" region
   also carries non-color bytes consumed by other texture machinery — a full-palette
   rewrite scrambled the HUD plant icon and prop textures. To gain new colors, remap a
   low-usage *used* entry's pixels to its nearest neighbor, then repurpose that entry
   (`backdrop_edit.free_entries` does this).
4. **Never truncate LEVEL.RAW; grow only within its sector count.** A truncated tail
   chops the last chunk → "Loading…" hang (possibly only on some machines — the
   corruption is RAM-content-dependent). The tool enforces both.
5. **Don't raise H.** VRAM rows under the backdrop are the level's texture atlas
   (verified: (832,96+) in LEVEL01 holds scene textures; the atlas uploads as generic
   64×192 strips). Use geometry for sky above the band.
6. **Verify on a cold boot, not a save state.** Save states snapshot RAM including any
   old cave code and the old backdrop — they replay bugs you already fixed.

## Full-sky content above the band: the night_stars cave pattern

`mod/caves/night_stars.c` (+ hook in `mod/patch_nightsky.asm`, cave @`0x800810C0`) emits
flat GP0(60) dot primitives through the game's own packet protocol — reusable for any
"stuff in the sky" (stars, rain, fireflies…):

- **Hook**: the backdrop tile builder's epilogue (`jr ra @0x8003EEC0`) — runs exactly
  when the backdrop draws, never in menus/boot.
- **Emit protocol**: `pkt = [gp+0x704]` (`0x8008249C`) bump cursor into the frame packet
  arena; `pkt[3]` = payload word count; `pkt[7]` = GP0 cmd; fields at +4/+8/+0xC; then
  `AddPrim(0x80061B74)([gp+0x674]+0x14E0, pkt)` = the background OT bucket (draws over
  the sky fill, behind the world); bump cursor by packet size. No custom buffers needed.
- **Move WITH the backdrop** (the two bugs to not repeat):
  - X: `x = (base_x + (yaw*7 >> 4)) & 511` — note **PLUS**: the tile builder negates its
    phase (`negu @0x8003EC24`); using the raw −yaw law pans dots opposite the band at 2×
    relative speed (glaring in L1 look mode, where one tap swings yaw ~500 units ≈ 44°
    vs ~40 in normal mode).
  - Y: store each element's **altitude above the band** and compute
    `y = [0x8009C1FC] − alt` per frame. `0x8009C1FC` = the live pitch-adjusted band top
    (76 neutral, ~168 at L1+down look-up, ~3 looking down); screen-fixed y detaches from
    the band on jumps/pitch.
- **Gate on the scene id** (`[0x80082504]`) so other levels keep their native skies.
- Budget: the cave + a 90-star table ≈ 0x2F0 of the 0x405-byte zero-run.

## Known limits / extensions

- **Chunk-straddling backdrops** (LEVEL02, LEVEL05): the LZ window spans chunks (the
  decoder shares one output buffer across the whole file), and some levels' backdrop
  objects legitimately cross a chunk boundary. Editing those needs a multi-chunk
  re-encode (re-encode both touched chunks from the cumulative stream) — the tool
  detects and refuses with exact chunk numbers. LEVEL01/LEVEL07-class (chunk-contained)
  work today.
- Header `a` = 0x24 in every level seen (constant format tag?); `b` = the band's vertical
  anchor (LEVEL01 0x4C for 96-tall, LEVEL07 0x26 for 160-tall) and is live at
  `0x800771B8` (W/H live at `0x800771B0/B4`).
- The disc combines a data edit (LEVEL.RAW) and optionally a code patch (EXE): the
  `build` subcommand stages both and restores the tree afterward. `mod/build.py` is NOT
  used because its patch slot (`mod/patch.asm`) carries other work.

## Provenance

Built/duplicated from the ABL_NIGHTSKY sessions (2026-07-02): sunset + custom + night
backdrops cold-boot proven; scroll/pitch laws decoded ([[Backdrop and sky layer]]);
encoder `tools/lz_encode_level_raw.py` (real back-references, 1.002× of the original
compressor — the enabler for size-safe chunk edits). C references:
`src_re/backdrop_tile_builder_8003e928.c` · `src_re/backdrop_sky_copier_8003b280.c`.
