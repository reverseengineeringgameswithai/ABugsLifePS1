---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Backdrop and sky layer.md
aliases:
  - "Backdrop and sky layer"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Backdrop and sky layer.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Backdrop_and_sky_layer.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Backdrop and sky layer (HRE-009)
type: system
status: SOLVED — source, scroll law, recolor AND full custom-image replacement all cold-boot proven
updated: 2026-07-02
confidence: CONFIRMED (format, sky chain, scroll law, recolor + custom-image replacement)
tags: [system, backdrop, sky, horizon, levelraw, chunk29, hre-009, leveleditor, codec]
---

# Backdrop and sky layer (HRE-009)

> What the "far horizon" actually is, where it lives on disc, and the proven authoring levers.
> Closes the discovery core of **HRE-009** from [[Retail Gameplay Completeness Gap Audit]].
> Proof disc: sunset-recolored LEVEL01, cold-boot verified (scratch `ABL_SUNSET`).

## The backdrop composition model

The player-facing "sky + far horizon" is FOUR layers, each with its own source and lever:

| layer | what | source | lever |
|---|---|---|---|
| sky | per-frame GP0 `0x02` flat fill | **chunk-29 palette entry** (via the copier below) — NOT chunk 32 (old finding corrected) | palette edit (disc) or RAM cache `0x800771BC/C0/C4` (live) |
| far horizon | **a palettized PANORAMA IMAGE** (LEVEL01: 128×96) | **LEVEL.RAW chunk 29** | replace/recolor the image or palette on disc (proven) |
| far terrain meshes | dirt-wall / grass-rim geometry | LEVEL.RAW meshes ~`0x8012C64C..0x8012E5CC` RAM, builders `FUNC_80014B04` (dirt) / `0x80013108` (grass), dispatch `0x8001D3CC` | render-side stubbing proven intractable (Phase-4); data-source nulling open |
| skyline props | pass-3 decor records | LEVEL.DAT pass-3 table @`0x3AEC` | per-prop suppression proven — [[Finding - Pass-3 decor records decoded (cull anchor + suppression)]] |

## Chunk-29 backdrop image format (CONFIRMED, generalizes across levels)

```
+0x00 u32 a        (LEVEL01: 0x24; other levels vary — meaning OPEN, maybe draw params)
+0x04 u32 b        (LEVEL01: 0x4C)
+0x08 u16 width    (LEVEL01: 128)
+0x0A u16 height   (LEVEL01: 96; LEVEL02/05: 128; LEVEL07: 160)
+0x0C u32 0x00010300  (low u16 0x300 = palette bytes; high u16 1 = format flag)
+0x10 RGB888 palette × 256   (0x300 bytes)
+0x310 8bpp indexed image, width×height  (LEVEL01: 0x3000 B → chunk = 0x3310 exactly)
```

- LEVEL01's image = the familiar horizon: sky band, distant hills, grass rim, layered dirt
  wall (render: scratch `chunk29_backdrop.png`). **Palette entry it starts with = the sky
  fill color `#3159DB`** — the flat sky seamlessly continues the image's top edge.
- Cross-level: LEVEL05's = the moonlit box-city panorama, LEVEL07's = a clover forest —
  **each level ships its own theme backdrop in its LEVEL.RAW** (search key: header bytes
  `00 03 01 00` at +0xC). Custom levels can ship a fully custom panorama.
- The image is consumed at level load (uploaded to VRAM as a texture; the palette run no
  longer exists in RAM at gameplay). The old note's "texture frame" label was half right.

## The sky-color chain (corrects [[Finding - Sky color on-disk table]])

Copier `0x8003B280..` (level load):
```
record  = s3 + (t1 & ~1)          ; s3 = chunk-29 runtime staging base (NOT 0x800C1688 = chunk-32)
idx     = record[+0x10]           ; per-level/record palette index byte
entry   = s3 + idx*3
R,G,B   = entry[+0x10], [+0x11], [+0x12]   ; i.e. palette[idx] (table base = +0x10)
→ 0x800771BC/C0/C4 (the DRAWENV cache FUNC_800639CC turns into the GP0 02 fill)
```
A second color is read right after (`[a0+0xF]` index → another palette entry) — likely the
far/fog or gradient companion color (OPEN). The old chunk-32 attribution came from reading
the copier's `s3` register when chunk 32 was resident at that staging address; the actual
byte source is the **chunk-29 palette** — which is why `31 59 DB` was found at decompressed
`0x8AFC8` = chunk-29 local `+0x10` (palette entry 0) and never in chunk 32.

## Proven disc lever: palette recolor (cold-boot, 2026-07-02)

Sunset proof: recolored 31 blue-dominant palette entries (blue→orange swap), re-encoded
chunk 29, spliced, padded LEVEL.RAW to its exact original size (layout-safe, LBA 3069
untouched), rebuilt, cold-booted via the boot movie: **sky fill AND horizon image both
render sunset-orange** (`0x800771BC` = DB/3B/18), terrain/Flik/props untouched, level plays.
One palette edit recolors the whole backdrop because both layers derive from it.

### The enabler: a REAL LZ encoder — `tools/lz_encode_level_raw.py`

The old `recompress_level_raw` is literal-run-only (~1.02× of RAW size): chunk 29 would
grow 13072→13330 B and overflow LEVEL.RAW's fixed sector budget (the file CANNOT grow —
pinned LBA 3069, dirent-size-bound reads). The new encoder emits real back-references
(greedy hash-chain, window 4096, len 2..263, litrun escapes) against the byte-exact
decoder grammar, including the empirically-mapped bit-register mechanics (init byte = 6
usable bits; 8 bits/reg byte MSB-first; MAIN-flag sentinel quirk at drain points).
Results: chunk-0 oracle 24397 vs 24346 B original (**1.002×**); sunset chunk-29 6915 vs
6977 B original (**smaller**). Round-trip asserted on every call. This also substantially
closes [[Blocker - Recompressor cannot reproduce original compression]] for practical
purposes (size-competitive, not byte-identical).

## Draw + scroll law — SOLVED (2026-07-02, operator save `backdrop` + code decode)

**The backdrop is a screen-space sprite tile layer that LOOPS the panorama by modulo
arithmetic — the operator's hypothesis was exactly right.**

- **Renderer**: a grid of **GP0(65) opaque sprite tiles, 64×32 px each** (no GTE), sampling
  the chunk-29 image as an **8bpp VRAM texture @ (832,0), CLUT @ (768,209)** (decodeTexture
  reproduces the offline PNG 1:1). Columns cycle u=0 / u=64 (the two halves of the 128-wide
  image); rows stack v=0/32/64 (the three 32-px bands of the 96-tall image).
- **Builder `FUNC_8003E928`** (bounds exact ..`0x8003EEC4`; packet x|y writers
  `0x8003EC50/5C/68`), runs per frame:

  ```
  yaw    = s16 [0x800824B2]                 ; CAMERA YAW, PS1 units (4096 = 360°) — new global
  phase  = (-yaw * 7 * 512) >> 13           ; = -yaw * 7/16 px
  phase &= 0xFF;  phase %= [0x800771B0]     ; MODULO THE IMAGE WIDTH ← the loop
  → gp+0x530 (0x800822C8); tile x-grid starts at -phase
  ```
  (A second branch handles incremental updates with ±0x1000 wraparound. `[0x800771B0/B4]`
  = the live backdrop **width/height** (128/96) — the chunk-29 header dims; the block sits
  just before the sky cache `0x800771BC`.) Formula live-verified against gp+0x530 — with a
  FULLY SETTLED camera (2.5 s per tap, operator's point): **exact match 5/5, zero error**,
  phase visibly wrapping mod 128 across the sweep; mid-swing samples also match (the
  builder recomputes per frame, so settling only affects the per-tap deltas, not the law).
- **Consequences**:
  - Tap right → yaw decreases ~40 units (3.5°) → the tile grid slides **exactly
    −yaw·7/16 px**; when the phase wraps mod 128, the same picture continues — **the
    panorama repeats every 128 screen px**, seamlessly (the image is authored tileable).
  - **One full 360° turn scrolls exactly 4096·7/16 = 1792 px = 14.0 image-widths**
    (measured ≈5 px/°; formula 4.98 px/°).
  - **Translation does NOT appear in the formula** — walking/teleporting cannot move the
    backdrop: it is an infinite-distance skybox, rotation-only. (The earlier ambiguous
    24%-changed test box was near-geometry/dither noise, as suspected.)
  - The 7/16 gearing means one 512-px screen ≈ 103° of yaw — the backdrop pans slightly
    slower than world geometry, the classic distant-horizon cheat.

## Residuals

- ~~Parallax/draw transform~~ SOLVED above (rotation-only tile layer, mod-width loop).
- VRAM upload call site (the code that copies chunk-29 → VRAM (832,0) at load) — the
  DESTINATION + format are confirmed; the uploader PC is not traced.
- Header fields `a`/`b` (+0x00/+0x04) semantics; the second copier color (`[a0+0xF]`).
- Far-terrain MESH backdrop (dirt wall / grass rim geometry): authoring lever still open
  (Phase-4: render-side stubbing intractable; data-source route undecided). NOTE: at the
  `backdrop` save's high vantage the image layer IS the whole visible horizon — the mesh
  layer matters mainly at ground-level poses.
- ~~Full custom-image replacement demo~~ **DONE (2026-07-02)**: a synthetic night panorama
  (purple gradient + stars + silhouette ridges, tileable, 250-color quantized, palette
  entry 0 = top-row sky color) baked into chunk 29 (compressed to 860 B!) and cold-booted:
  starfield horizon in-game, sky fill seamless. Custom per-level backdrops are fully
  authorable end-to-end.
- Sky-fill index record (`[record+0x10]`) location on disc (which chunk-29-adjacent record
  selects the palette entry per level).

### ⚠️ Palette-region gotcha (2026-07-02, night-backdrop build)
**Not all 0x300 bytes at chunk-29 +0x10 are colors.** Rewriting ALL 256 entries (a global
night-darken) scrambled OTHER textures on the booted disc — the HUD plant icon and the
acorn/white-cap prop textures rendered as noise — while an edit touching only entries the
backdrop image actually indexes (207 of 256 in LEVEL01) is clean. The never-used bytes are
consumed by other texture machinery (likely via the header `a=0x24`/`b=0x4C` offsets, which
point into this region). **Authoring rule: edit only image-used entries; to gain custom
entries (e.g. star colors), pick a LOW-USAGE used entry, remap its few pixels to the nearest
color, then repurpose it — never touch never-used bytes.** (Empirical A/B: sunset build =
blue-entries-only = clean; first night build = all-entries = corrupted; used-only night
build = clean, HUD icon pixel-identical to reference.)

### Full-sky starfield via geometry (ABL_NIGHTSKY, 2026-07-02) — "replacing how the backdrop works"
The fill region above the tile band cannot hold image content, and a taller chunk-29 image is
blocked in LEVEL01 (recon: the backdrop uploads inside generic **64×192 atlas STRIP uploads** —
its VRAM home is atlas-packing, not a rect constant; rows (832,96+) hold live scene textures).
Solution: **stars as geometry** — `mod/caves/night_stars.c` (cave @`0x800810C0`, hook = the tile
builder's epilogue `jr ra @0x8003EEC0` via `mod/patch_nightsky.asm`) emits 1–2 px flat GP0(60)
dots through the game's own packet protocol: bump cursor `[gp+0x704]` (`0x8008249C`), payload-size
byte at pkt+3, cmd at pkt+7, then `AddPrim(0x80061B74)` into the background OT bucket
`[gp+0x674]+0x14E0` — the same bucket the tiles use, so dots draw over the fill, behind the world.
X scrolls by the tile law (−yaw·7/16 mod 512); Y draws only below **`[0x8009C1FC]` = the LIVE
pitch-adjusted band-top** (76 neutral, ~168 at L1+down look-up, ~3 looking down) so looking up
reveals more stars automatically; `[0x800823BE]` = the band's visible-row clip. Gated to scene 1.
Verified cold-boot: full-sky varied-brightness stars at neutral AND L1+down, panning with the
panorama. (Combined EXE+RAW disc staged manually — build.py's patch.asm slot holds operator WIP.)

### New globals / functions (this decode)
`0x800824B2` s16 camera yaw (4096/rev) · `0x800822C8` (gp+0x530) backdrop scroll phase · `0x8009C1FC` live pitch-adjusted band-top Y · `0x800823BE` band visible-row clip · packet cursor `0x8008249C` (gp+0x704) + bg OT bucket `[0x8008240C]+0x14E0` + AddPrim `0x80061B74` ·
`0x800771B0/B4` backdrop image W/H · `0x800823BE` tile clip helper · builder `FUNC_8003E928`
(..0x8003EEC4) · backdrop texture VRAM (832,0) 8bpp + CLUT (768,209), GP0(65) 64×32 tiles.

## Reuse

**Authoring recipe + tooling: [[Playbook - Author a custom backdrop]]** — `tools/backdrop_edit.py`
(extract/night/replace/build subcommands, any level, auto-locates the chunk, enforces every rule
below, full regression built in) + the night_stars cave pattern for content above the band.
Cross-level notes: LEVEL07 = chunk 30 (128×160, b=0x26); LEVEL02/05 backdrops STRADDLE a chunk
boundary (the LZ window spans chunks — multi-chunk splice needed, tool refuses cleanly);
header `a` = 0x24 in all levels seen.

## Repro

- Extract/preview: `seed_table.read_chunk_decompressed(raw, 29)` → palette @+0x10, image
  @+0x310; render with PIL (scratch `chunk29_backdrop.png`, `backdrop_LEVEL05_*.png`, …).
- Recolor bake: edit palette → `lz_encode_level_raw.compress_chunk(dec, header6=span.header6)`
  → splice → `rebuild_with_patched_dat.py --target files/LEVEL01/LEVEL.RAW`.
  **⚠️ SPLICE SIZE RULE (bug post-mortem 2026-07-02):** if the re-encoded chunk is SMALLER,
  padding the file back to its original size is optional; if it is LARGER, the file MAY GROW
  as long as the total stays within the 366-sector allocation (`ceil(size/2048) <= 366`) —
  mkpsxiso re-derives the dirent size automatically. **NEVER truncate to the original size:**
  an early night-backdrop build wrote `new_raw[:len(raw)]`, chopping 26 tail bytes off the
  LAST chunk → the level hung at "Loading..." on the operator's machine (and survived only by
  RAM luck in the verification run). ALWAYS run the full-file decode regression before baking:
  `decompress_file(new_raw)` must yield the same chunk count + byte-identical decompressed
  output everywhere except the edited chunk.
- Encoder self-test: `python3 tools/lz_encode_level_raw.py` (chunk-0 oracle round-trip).

## Related

[[Retail Gameplay Completeness Gap Audit]] · [[Finding - Sky is a GP0 background fill]] ·
[[Finding - Sky color on-disk table]] (corrected by this note) ·
[[Finding - Pass-3 decor records decoded (cull anchor + suppression)]] ·
[[Finding - LEVEL.RAW is compressed]] · [[Tier 3 - Level Replacement Phases]] ·
`tools/lz_encode_level_raw.py` · `src_re/backdrop_sky_copier_8003b280.c`
