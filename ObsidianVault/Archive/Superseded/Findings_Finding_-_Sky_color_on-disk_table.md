---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Sky color on-disk table.md
aliases:
  - "Finding - Sky color on-disk table"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Sky color on-disk table.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Sky_color_on-disk_table.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Sky color on-disk table
type: finding
confidence: CONFIRMED
gstep: G30
tags: [finding, sky, levelraw, chunk32]
---

# Finding — Sky color on-disk source = table `0x800c1688` (chunk 32)

> The persistent (on-disk) source for the sky clear color, distinct from the RAM cache lever.

**Confidence:** ~~CONFIRMED~~ **CORRECTED 2026-07-02** · **Established:** G30 · **Findings-store id:** f2

> [!important] CORRECTED (2026-07-02, HRE-009): the on-disk source is the **CHUNK-29 PALETTE**, not chunk 32.
> The copier `0x8003B280..` reads `palette[idx]` at `s3 + idx*3 + 0x10` — and `+0x10` is exactly the
> palette base of the **chunk-29 backdrop panorama image** (`{header 0x10; RGB888×256 @+0x10; 8bpp
> image @+0x310}`). That is why the warning below could never find `31 59 db` in chunk 32 but found it
> at decompressed `0x8afc8` = **chunk-29 local `+0x10` = palette entry 0**. The `s3=0x800c1688` register
> capture was a decompression STAGING address, not a chunk-32 attribution. Disc recolor proven cold-boot
> (sunset LEVEL01: one palette edit recolors the sky fill AND the horizon image). Full model + levers:
> [[Backdrop and sky layer]]; format/copier C: `src_re/backdrop_sky_copier_8003b280.c`.

> [!warning] Static-dump discrepancy (2026-06-19, level-editor Phase 1 pass)
> A read of the cached decompressed chunk 32 does **not** reproduce the on-disk claim: chunk-32 offset 0 is the record header `03 01 00 00 b6 b2 …` (matches [[MEM - Collision plane record]]), and the bytes `31 59 db` do **not** occur anywhere in chunk 32 — they appear at decompressed `0x8afc8`, inside **chunk 29** (a texture frame). So `31 59 db` is confirmed as the live **RAM cache** value, but its **on-disk offset within chunk 32 is NOT byte-confirmed** (it is not at offset 0). Resolve by accessLog-ing the actual copier read offset (`s3=0x800c1688 + ?`). Sky import is therefore deferred in the editor — see [[ABL 3D Phase 1 Gap Checklist]].

## Summary
The authoritative on-disk sky RGB is the LEVEL.RAW-derived color table at `0x800c1688`, entry 0 = bytes `31 59 db`. Pre-level, copier code `0x8003b2b8 / 0x8003b2d8 / 0x8003b2f8` copies those bytes into the RAM cache [[MEM - Sky DRAWENV color cache 800771BC]] (`0x800771bc/c0/c4`), which the per-frame builder [[FUNC_800639CC]] turns into the GP0 `0x02` fill. The table sits in LEVEL.RAW **chunk 32** (same chunk as collision).

## Evidence
Pre-load accessLog trace caught the three copies from `s3=0x800c1688`; `tools/parse_level_raw_chunks.py` maps `0x800c1688` to chunk 32 (file off `0x492cf`).

## Related functions
[[FUNC_800639CC]] · [[FUNC_8001A1DC]]

## Related memory structures
[[MEM - Sky DRAWENV color cache 800771BC]] · [[MEM - LEVEL.RAW chunk model]]

## Related experiments
[[Experiment - G30 sky recolor]]

## Related fixtures / save states
`SCUS-94288_2.sav` (pre-load) · [[Fixture - night starry]]

## DuckStation APIs used
[[API - accessLog]] · [[API - gpu.readVramRect]] · [[API - visual diff]]

## Next steps
For a RAM/save-state recolor, patch the cache; for a persistent recolor, patch the table (LZ-codec gated, see [[Finding - LEVEL.RAW is compressed]]).

## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md` §19.2; findings-store f2
