---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Loading screen backdrops are GFX RAW images.md
aliases:
  - "Finding - Loading screen backdrops are GFX RAW images"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Loading screen backdrops are GFX RAW images.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Loading_screen_backdrops_are_GFX_RAW_images.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Loading-screen backdrops are GFX/*.RAW images
type: finding
status: SOLVED — format decoded, custom replacement cold-boot verified (ABL_NOCTURNAL_LOAD)
updated: 2026-07-02
confidence: CONFIRMED (format, level mapping, display crop, overlay band — all live-verified)
tags: [finding, loadingscreen, gfx, levelraw, codec, leveleditor, asset]
---

# Finding — The pre-level "Loading" screen backdrops live in GFX/*.RAW

> The between-level loading screen (level-name art + "loading…"/"Press X" prompt) is a
> **separate asset** from the in-game chunk-29 panorama ([[Backdrop and sky layer]]). It is a
> full-screen 16bpp image in `GFX/<NAME>.RAW`, compressed with the **same LZ chunk codec as
> LEVEL.RAW**. Custom replacement is cold-boot proven (disc `REBUILD/ABL_NOCTURNAL_LOAD`).

## Where it lives + the disc→level mapping

`GFX/` holds one `*.RAW` per loading screen. The names are grouped by campaign order, **not**
by level directory:

| file | screen |
|---|---|
| `GFX/LEVEL1A.RAW` | **Level One** — "Welcome to Ant Island / Find the entrance to the anthill" |
| `GFX/LEVEL1B.RAW` | Level Two — "Tunnel Run" |
| `GFX/LEVEL1C.RAW` | Level Three — "They Call Him Thumper" |
| `GFX/LEVEL2A.RAW …` | continue the campaign (2A/2B/2C, 3A…) |
| `GFX/LOADING.RAW` | the yellow **"loading…"** overlay sprite (pans down, then → "Press X") |
| `GFX/TRAINING.RAW`, `CIRCUS.RAW`, `FILM.RAW` | other screens |

Files are pinned to fixed LBAs in `REBUILD/abl.xml` (`LEVEL1A.RAW` @ `offs=1641`, next file
`LEVEL1B.RAW` @ `offs=1689`) ⇒ **48-sector budget** (98304 B) for LEVEL1A. Loading is by-name
([[Finding - File loading is by-name (LBA-shift tolerant)]]) so a size change is tolerated, but
staying ≤ the pinned budget keeps the standard layout with zero LBA shift.

## The container + image format (CONFIRMED)

Each `GFX/*.RAW` is a sequence of LZ chunks — identical grammar to LEVEL.RAW
(`tools/decode_level_raw.py`): BE `u32 word0`=decompressed size, `u32 word1`=compressed size,
6 header bytes, body of `0xE+word1` bytes; `0xFFFFFFFF` terminator. `seed_table.find_chunk`
and `lz_encode_level_raw.compress_chunk` work on them unchanged.

- **LEVEL1A.RAW = 2 chunks.** Chunk 0 (33548 B decompressed, **byte-identical across
  LEVEL1A/1B/1C**) is a shared resource (font/CLUT machinery) — never touched. Chunk 1 is the
  **backdrop image**. LOADING.RAW = 1 chunk (the overlay image, same image format).
- **Image chunk payload** = `0x10 + 320*256*2` = 163856 B:
  ```
  +0x00  16-byte header  (u16 x, y, w=0x140=320, h=0x100=256, …) — a VRAM load-rect descriptor
  +0x10  320×256 pixels, PS1 16bpp framebuffer format = RGB555 little-endian
         bit0-4 R, bit5-9 G, bit10-14 B, bit15 = mask/STP (0 in every retail screen)
  ```
  No palette — it is direct-colour, unlike the chunk-29 panorama.

## Display + overlay geometry (live-measured)

- The screen displays **~240 of the 256 stored rows** (standard PS1 NTSC) — the bottom ~16 px
  of the stored image are **off-screen** ("cut from the bottom"). Retail art keeps only
  expendable background there.
- The `GFX/LOADING.RAW` "loading…" text is stored mid-image (rows ~113–147) but **pans down**
  at runtime to a fixed bottom band (~rows 205+), then is replaced by a flashing "Press X"
  in the same band. Retail backdrops keep their lowest text (the subtitle) at **row ≤ ~190**
  so the overlay never covers it. Custom art that fills the frame drops its subtitle into the
  overlay band → the fix is a small upward shift (see the tool's `--shift-up`, ~16 for LEVEL1x).

## Proof

`GFX/LEVEL1A.RAW` chunk 1 replaced with a night-themed "Nocturnal Ant Island" image
(`mod/loadscreens/src/Nocturnal_Ant_Island.png`), re-encoded (chunk 1 body 94436→45308 B,
RAW 96664→47536 B = 24/48 sectors), full-file decode regression clean, disc rebuilt
(`REBUILD/ABL_NOCTURNAL_LOAD`), **cold-boot verified** via `flik_to_level01_stall.mv.movie.json`:
the nocturnal backdrop renders on the LEVEL01 loading screen and "loading…" sits cleanly below
the subtitle (`mod/loadscreens/ref/LEVEL1A_nocturnal_ingame.png`). No code — pure asset edit.

## Tool + reuse

`tools/loadscreen_edit.py` — `extract <NAME>` / `replace <NAME> --image X [--shift-up N]
[--sector-budget 48] -o out.RAW`. Reuses the LEVEL.RAW codec + the `splice_and_verify`
regression pattern from `tools/backdrop_edit.py`. Recipe:
[[Playbook - Replace a loading-screen backdrop]].

## Related

[[Backdrop and sky layer]] (the DIFFERENT in-game panorama) ·
[[Finding - File loading is by-name (LBA-shift tolerant)]] ·
[[Finding - LEVEL.RAW is compressed]] · `tools/loadscreen_edit.py` · `tools/decode_level_raw.py`
