---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Build toolchain and PROPACK provenance.md
aliases:
  - "Finding - Build toolchain and PROPACK provenance"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Build toolchain and PROPACK provenance.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Build_toolchain_and_PROPACK_provenance.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Build toolchain and PROPACK provenance
type: finding
confidence: CONFIRMED
tags: [finding, toolchain, provenance, propack, psyq, iguana, levelraw]
updated: 2026-06-18
---

# Finding — Original build toolchain & PROPACK provenance (from on-disc dev artifacts)

> Two developer files shipped on the retail disc reveal the exact original build pipeline. This captures [[Blocker - Original toolchain ground-truth is unmined|B13]] and **renames the LEVEL.RAW codec**: it is **Rob Northen PROPACK 2.29**, not a bespoke LZSS.

**Confidence:** CONFIRMED (verbatim on-disc evidence) · **Established:** 2026-06-18 (Phase 1a)

## The pipeline
- **Developer:** **Traveller's Tales** (the decoded `TTLOGO.BGR` is the Traveller's Tales logo; cf. `TT.STR`; corroborated by Wikipedia + Internet Archive). Published by **SCEA**; the separate GBC version was Tiertex/THQ. ⚠️ **Correction:** the `ERRORS.ERR` string `REGISTERED TO IGUANA ENTERTAINMENT 01-FEB-95` attests only the **PROPACK tool's license**, *not* the game's developer — an earlier over-attribution to Iguana is corrected here (the kind of single-source slip flagged in [[Blocker - Headline results rest on single-source evidence|B3]]).
- **Build system:** SN Systems **PsyMake 1.11** (`PsyMake version 1.11 copyright SN Systems Software Ltd 1993`) driving **PsyQ** (`[psyq] makefile=makefile.mak`, STATE.RST); a DOS batch driver (`level00\tpages.BAT`). Dev tree `C:\play\bugs\`, CD staging `\play\bugs\cd\`, char tools on `D:\play\bugs\cd\chars\`.
- **Compression:** Rob Northen Computing **PROPACK 2.29** (`Copyright (c) 1991-95 Rob Northen Computing, UK`) → the "custom LZSS" in [[Finding - LEVEL.RAW is compressed]] is **RNC PROPACK 2.29**. Confirms [[Assumptions Register|A13]].
- **Asset tool:** `lbmbugs` v2.0 ("{LBMBUGS (lbm+data Add frame} to PlayStation grabber v2.0") — packs DeluxePaint `.lbm` bitmaps + `.bgr` backgrounds into `level.raw` via PROPACK, one frame per call, under DOS/4GW:
  - `lbmbugs …\level.raw …\backdrop.bgr 32 256 128`  (background; trailing args ≈ tpage/CLUT/VRAM geometry — to confirm in Phase 1e)
  - `lbmbugs …\level.raw …\clover00.lbm 0` · `…\player00.lbm 1`  (final arg = frame/append mode flag)

## LEVEL.RAW = PROPACK-packed lbm/bgr frames (key reframing)
- The build log packs `clover00.lbm`: **original 33548 → compressed 22398**. The project's chunk0 oracle has the **same decompressed size 33548**, and `word0`=33548 recurs for most chunks (`chunk_index.json`) ⇒ **33548 (0x830C) is a fixed frame size** and LEVEL.RAW is a stack of PROPACK-packed `lbm`/`bgr` frames assembled by `lbmbugs` (cf. `tpages.BAT` = texture pages). ⚠️ **Caveat (no over-claim):** LEVEL01 chunk0's *compressed* size is **24332**, not clover00's **22398** — so chunk0 is a *different image of the same frame class*, **not literally `clover00`** (clover00 was packed for LEVEL00). The decompressed-size match confirms the **frame format + PROPACK lineage**, nothing more.
- `backdrop.bgr`: 65548 → 30780 (53.04%).
- The project's **literal-only** recompressor emits ~1.02× (≈34 KB for chunk0) vs PROPACK's 22398 → **not byte- or size-compatible** with the original packer → corroborates [[Blocker - Recompressor cannot reproduce original compression|B14]].

## Implications (what this unblocks)
- **B7 / B20:** the existing decoder may decode `GFX/*.RAW`, `*.ALL`, `.bgr` if they share PROPACK — a free path into textures/models (Phase 1d/1e). A public RNC-PROPACK decoder is an independent oracle.
- **B1 / B4:** pins the compiler/linker family (PsyQ + PsyMake 1.11) for any matching decomp / from-source rebuild.
- **LEVEL00** ships the build log ⇒ it is a developer/test stage ([[Blocker - RE depth is LEVEL01-only|B8]]).

## Verified offline (Phase 1d/1e, 2026-06-18)
- **GFX/*.RAW are the same PROPACK container** — the existing decoder decoded `GFX/CIRCUS.RAW` chunk 0 → 33548 B with the LEVEL.RAW frame header (`0d 00 00 00 | 00 01 00 01 | 00 03`). ⇒ the solved codec **unlocks the GFX images offline today** → advances [[Blocker - Offline texture and font extraction is absent|B20]].
- **`.ALL`/`.ANM` are uncompressed** (no PROPACK header; `TERRAIN.ALL` opens `b6 b2 01 00 …` = decompressed chunk-32 content) → not compression-gated, but still bespoke → [[Blocker - Character and plant model formats are unreversed|B7]].
- `TTLOGO.BGR` decoded (320×240 BGR555) → `extracted/TTLOGO.png` (the Traveller's Tales logo).

## References (existing preservation research)
- [The Cutting Room Floor — A Bug's Life (PlayStation)](https://tcrf.net/A_Bug's_Life_(PlayStation)) — community RE / unused-content notes.
- [Internet Archive — A Bug's Life (USA) (V1.1)](https://archive.org/details/psx_bugslife) — confirms a **V1.1** exists (our disc is **V1.0**); dev credited Traveller's Tales.
- [Wikipedia — A Bug's Life (video game)](https://en.wikipedia.org/wiki/A_Bug's_Life_(video_game)) — developer/publisher.

## Related
[[Blocker - Original toolchain ground-truth is unmined]] · [[Blocker - Recompressor cannot reproduce original compression]] · [[Finding - LEVEL.RAW is compressed]] · [[MEM - LEVEL.RAW chunk inventory]] · [[Asset - LEVEL.RAW]] · [[Asset - Disc image and rebuild]] · [[Confirmed Knowledge]]
- Source: `REBUILD/files/LEVEL00/ERRORS.ERR`, `REBUILD/files/CHARS/STATE.RST`
