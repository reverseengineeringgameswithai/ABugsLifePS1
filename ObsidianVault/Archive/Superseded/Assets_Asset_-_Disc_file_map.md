---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - Disc file map.md
aliases:
  - "Asset - Disc file map"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - Disc file map.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_Disc_file_map.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - Disc file map
type: asset
updated: 2026-06-20
tags: [asset, disc, layout, lba, milestone1, b8, b12]
---

# Asset — Disc file map (LBA layout)

> Narrative, navigable map of the disc's on-disc layout (Milestone 1 / [[Gap Audit|GAP-0015]]). The **authoritative machine-readable table** is `REBUILD/abl.xml` (the mkpsxiso manifest: 321 files, per-file LBA `offs` + build date); this note summarizes it. Identity/hashes: [[Checksum Manifest]].

**Disc:** SCUS-94288 · MODE2/2352 · **313,897 sectors** (738,285,744 B) · volume `A_BUGS_LIFE` · boot `cdrom:\SCUS_942.88;1`. **26 directories, 321 files.** Rebuilds byte-exact ([[Finding - Disc rebuild is byte-exact]]).

## LBA geography (load order)
| LBA range | Directory | # | Role |
|---|---|:--:|---|
| 23 | `/` | 1 | **`SCUS_942.88`** boot EXE (load `0x80010000`) |
| 253 | `/` | 1 | `SYSTEM.CNF` boot config |
| 255–291 | **BITS** | 4 | Shared bits: `MEMORY.BIN` (Region-B overlay), `PLANTTER.ALL`/`SEED.ALL` (shared meshes), `TTLOGO.BGR` (TT logo image) |
| 367–1227 | **CHARS / CHARS2 / CHARS3 / CHARS4** | 27/28/28/6 | Character models + anim (`.ALL`/`.ANM`) — see [[Asset - Character and plant models]] |
| 1316 | **FMV** | 1 | `FMV.BIN` (Region-B overlay for video playback) |
| 1566–2231 | **GFX** | 19 | Loading-screen / UI images (PROPACK `*.RAW`) — [[Finding - Region-A texture format decoded]] |
| 2291–2809 | **LEVEL00** | 9 | Dev/stage-0 data (held the build log `ERRORS.ERR` → [[Finding - Build toolchain and PROPACK provenance]]) |
| 2905–16140 | **LEVEL01 … LEVEL10** | 13–16 ea | Per-level data (objects/geometry/audio/terrain) — pattern below |
| 16211–16217 | **PAD** | 7 | `PATH01-05,12,13.BIN` — nav/path data for the "path-level" subsystem → [[Gap Audit\|GAP-0034]] / [[Enemy relocation method]] |
| 16219–16284 | **PLANTS / PLANTS2** | 22/6 | Plant models (`.ALL`/`.ANM`) |
| 16289–16377 | **SFX** | 2 | `GLOBAL.VB`/`GLOBAL.VH` global sound bank ([[Finding - VAB sound bank format]]) |
| 16381–96577 | **BUGSFMV1** | 18 | FMV video streams (`.STR`) — [[Asset - Asset extraction recipe]] |
| 100738–182277 | **BUGSFMV2** | 19 | FMV video streams (`.STR`) |
| 183718–287430 | **BUGXASTR** | 5 | XA audio streams |
| 291695–294035 | **BUGSFMV3** | 2 | FMV video streams (`.STR`) |
| 297363 | `/` | 1 | `BLANK.BIN` (tail filler/padding) |

> The ~67% of the disc past LBA 16381 is streamed FMV + XA media; the *game-logic* data (EXE + overlays + 11 level dirs + paths + sound) all sits in the first **~16,400** sectors.

## Per-level layout (LEVEL01 example, LBA)
The 11 level dirs share a format; counts/LBAs vary per level (per-level addresses, [[Finding - Level formats generalize, content is per-level]]).
| LBA | File | Role |
|---|---|---|
| 2905 | `LEVEL.BIN` | per-level overlay code (Region-A) |
| **2906** | `LEVEL.DAT` | object/pickup placement (type-0x3f + paths) — the modding target ([[Asset - LEVEL.DAT]]) |
| 3069 | `LEVEL.RAW` | compressed geometry + collision (PROPACK; 69 chunks) — [[Asset - LEVEL.RAW]] |
| 3435/3437/3490 | `LEVEL1.BIN/DAT/RAW` | level variant set |
| 3755/4000 | `LEVEL1A.VB/VH` | level sound bank (VAB) |
| 4003 | `LEVEL2.DAT` | additional object set |
| 4132/4380 | `LEVEL2C.VB/VH` | sound bank |
| 4383/4414 | `TERR1.ALL` / `TERRAIN.ALL` | terrain meshes (`.ALL`) |

## Notes
- **Stage↔dir mapping is not 1:1:** the 15 in-game stages map onto the 11 `LEVEL0N` dirs + variant files (`LEVELn`/`LEVELnX`) — see [[Blocker - RE depth is LEVEL01-only|B8]].
- **`offs` (LBA) is authoritative** for byte-exact rebuild; file loading is by-name so in-level edits tolerate LBA shifts only as proven for the boot EXE ([[Finding - File loading is by-name (LBA-shift tolerant)]] — in-level case open, [[Gap Audit\|GAP-0025]]).

## See also
[[Checksum Manifest]] · [[Asset - Disc image and rebuild]] · [[Asset - LEVEL.DAT]] · [[Asset - LEVEL.RAW]] · [[Asset - LEVEL.BIN and overlays]] · [[Asset - Asset extraction recipe]] · [[Roadmap]] · `REBUILD/abl.xml`
