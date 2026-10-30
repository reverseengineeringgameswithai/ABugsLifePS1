---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Core - CD Streaming and Caching.md
aliases:
  - "Core - CD Streaming and Caching"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Core - CD Streaming and Caching.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Core_-_CD_Streaming_and_Caching.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Core - CD Streaming and Caching
type: core
updated: 2026-06-20
tags: [core, cd, streaming, loader, milestone5, gap-0029, b8]
---

# Core — CD streaming & caching (first-pass model)

> M5 first-pass model for [[Gap Audit|GAP-0029]] — is level/media data all-at-load, streamed, or cached? **Provenance:** loader chain + by-name loading are STATIC/CONFIRMED; transferLog LBA provenance is DYNAMIC/local-only ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Loader chain (STATIC — CONFIRMED)
- **`[[FUNC_80046330]]`** = the file-load choke point: `(a0 = bare filename string, a1 = dest RAM base) → v0 = bytes read`; **14 call sites** across 11 functions; prepends the CD/level directory.
- **`[[FUNC_8003CF2C]]`** = resource dispatcher (jump table `0x8001afb0`, 17 handlers): sets DATbase, calls parser [[FUNC_8001CDC0]].
- **`[[FUNC_8003A318]]`** = LEVEL.RAW loader: reads the compressed RAW to `0x80115aac` (`level_raw_compressed_base`, size `0xb6be4`), then a **per-chunk decompress loop** (`word0`=decomp / `word1`=comp size, `0xffffffff` terminator) via [[FUNC_8001A1DC]], dispatching to builders incl. collision [[FUNC_80030F60]]. *(Note: the "streamed loader `0x8003a388`" referenced elsewhere is the `FUNC_80046330` **call site inside** `FUNC_8003A318`, not a separate streaming engine.)*
- CD init = `fcn.80045d6c` (CdInit); libcd anchors: CdInit-fail `0x8001c2c0`, `Cdl*` table `0x8001c2e0`.

## File loading is by-name (STATIC + dynamic — STRONG)
The loader is passed a **path string, not an LBA**. A runtime ISO9660 filename table is built at **`0x80086c00`** (BSS, filled from the disc directory at boot). ⇒ a rebuilt disc with shifted LBAs still resolves by name → [[Finding - File loading is by-name (LBA-shift tolerant)]]. *Proven for the EXE boot (cold-boot of a shifted disc loaded `SYSTEM.CNF`+EXE by name); the in-level RAW load step is operator/local-only.* Ties into [[Asset - LBA Shift Rebuild Proof]].

## All-at-load vs streamed (first-pass MODEL)
- **Level geometry = all-at-load (per level).** The `TERRAIN.ALL` "conversion/cache" hypothesis got **0 EXEC hits and was dropped** (G21; [[Hypotheses]] "REFUTED"). LEVEL.DAT/LEVEL.RAW/level VABs load once at level entry via the chain above.
- **Disc geography ([[Asset - Disc file map]]):** all game-logic data (EXE + overlays + 11 `LEVEL0N` dirs + `PAD` + `SFX`) sits in the **first ~16,400 sectors**; **~67% of the disc past LBA 16381 is streamed FMV + XA media** (BUGSFMV1/2/3, BUGXASTR).
- **Streamed (separate path):** XA audio (libcd `CdlReadS`/`CdlSetfilter`, see [[Core - Runtime Audio Path]]) and STR/MDEC FMV ([[Core - FMV and MDEC Playback]]) are the genuine *streamed* subsystems.

### Per-subsystem unknowns
| Subsystem | Model | Status |
|---|---|---|
| **Level geometry/objects** | all-at-load per level | CONFIRMED (static + 0-hit cache refute) |
| **Audio (XA music)** | streamed off-disc (libcd) | LIKELY; runtime path open ([[Core - Runtime Audio Path]]) |
| **FMV (STR)** | streamed off-disc | LIKELY; trigger open ([[Core - FMV and MDEC Playback]]) |
| **Front-end/menu** | overlay-resident | Unknown (event-gated) |
| **Mid-level data (`PAD/PATH*.BIN`)** | unknown | **Unknown** — possibly event-gated |

## transferLog evidence (DYNAMIC — LOCAL-ONLY)
LEVEL.RAW load provenance = disc **LBA 1823–4149 → RAM** (underpins the chunk-32/35 source findings) → [[API - transferLog]]. `transferLog.resolve` maps RAM addr → disc file (EXE-resident `confidence:"exact"`; streamed-asset needs a re-armed log + replay). **Re-arm after every `loadState`.**

## `abl.xml` relationship
`REBUILD/abl.xml` is the authoritative **321-file LBA manifest** (`offs=` pins LBAs for byte-exact rebuild). Because loading is by-name, an **auto-layout** rebuild (drop `offs`) is what's needed to grow files — its in-level boot is the GAP-0025 local-only residual ([[Asset - LBA Shift Rebuild Proof]]).

## Named missing / next experiments
- **Does ANY mid-level streaming/caching exist** (vs confirmed all-at-load per level)? And the runtime role of **`PAD/PATH*.BIN`** (LBA 16211–16217).
- **Blocker:** mid-level loads may be **event-gated** → unreachable from current mid-gameplay saves (the recurring [[Gap Audit|GAP-0033]] event-state-fixture wall).
- Next: `transferLog` (re-armed) across a level with a known mid-level trigger; `accessLog.lastWriter` on a streamed buffer. Local-only; cite fork state.

## Related
[[Asset - Disc file map]] · [[Asset - LBA Shift Rebuild Proof]] · [[Core - Runtime Audio Path]] · [[Core - FMV and MDEC Playback]] · [[FUNC_80046330]] · [[FUNC_8003CF2C]] · [[FUNC_8003A318]] · [[API - transferLog]] · [[Finding - File loading is by-name (LBA-shift tolerant)]] · [[DuckStation Fork Reproducibility]]
