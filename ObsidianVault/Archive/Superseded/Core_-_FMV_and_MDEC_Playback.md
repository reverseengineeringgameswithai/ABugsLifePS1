---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Core - FMV and MDEC Playback.md
aliases:
  - "Core - FMV and MDEC Playback"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Core - FMV and MDEC Playback.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Core_-_FMV_and_MDEC_Playback.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Core - FMV and MDEC Playback
type: core
updated: 2026-06-22
tags: [core, fmv, mdec, str, overlay, milestone5, gap-0032, b6]
---

# Core — FMV / MDEC playback (baseline)

> M5 consolidation for [[Gap Audit|GAP-0032]] — how FMV playback is triggered + loaded. **Extraction = DONE; in-engine playback trigger = bounded unknown.** Provenance: formats/locations + the FMV.BIN overlay are STATIC/CONFIRMED; the playback call site + sequence logic are hypotheses (DYNAMIC/local-only, [[DuckStation Fork Reproducibility]] / GAP-0001).

## Formats & locations (CONFIRMED)
- **STR** = PS1 streaming-video container (MDEC frames + interleaved XA audio). **All 39 `.STR` decoded** via jpsxdec → [[Asset Extraction Pipeline]].
- FMV file locations ([[Asset - Disc file map]]): **BUGSFMV1** (18 files, LBA 16381–96577), **BUGSFMV2** (19, 100738–182277), **BUGSFMV3** (2, 291695–294035); **BUGXASTR** XA (5, 183718–287430). The FMV/XA media is ~67% of the disc (streamed tail).
- Title image `BITS/TTLOGO.BGR` (320×240 BGR555).

## FMV.BIN overlay (STATIC — CONFIRMED, Region B)
`FMV/FMV.BIN` (LBA 1316; **509,800 B / `0x7C768`**; SHA-1 `9738b2b6…`) loads into **Region-B base `0x800B5788`** (`region_b_overlay_base`) and is **time-swapped with `BITS/MEMORY.BIN`** in the same buffer → [[Executable and Overlays]] · [[MEM - Global memory map]]. FMV.BIN loaders = `fcn.8003e7c0?` (site `0x8003e7fc`) and `fcn.8003f504` (site `0x8003f578`); the sibling MEMORY.BIN loader `fcn.8003f5b8` → init `0x800bd518` (+0x7d90, CONFIRMED). **FMV.BIN entry point is NOT confirmed** (module-residency caveat: Region-B symbols are valid only while the correct module is resident).

## Triggers / front-end (hypothesis)
- The menu **"Movie Clips"** rewatches `.STR` FMVs unlocked by completing sections → [[Menu and HUD structure]].
- Front-end runs in the **shell phase** of `main_shell_state_machine` (`0x8004FA40`), substate dispatch `[0x8008243C]` (`main_shell_substate`) mod 6, table `0x8001b3c4`. Menus are likely overlay-resident (un-RE'd).
- **Leading hypothesis:** the boot front-end sequences intro FMVs (INTRO/DLOGO/TT order) by loading `FMV.BIN` into Region B and invoking its MDEC-playback entry per `.STR`; level-transition clips are triggered from the shell-phase state machine on section completion.

## Known functions / symbols
`0x8004FA40` (`main_shell_state_machine`) · `0x8008243C` (`main_shell_substate`) · `0x800823A0` (`master_game_state`) · `0x80082504` (`current_scene_id`) · Region-B base `0x800B5788` · FMV.BIN loaders `0x8003e7fc` / `0x8003f578`. See `symbols/re_symbols.sym` + [[Executable and Overlays]].

## FMV.BIN manifest + front-end sequence — RESOLVED (2026-06-22; GAP-0032)
**FMV.BIN is a 25-entry MANIFEST + player overlay (decoded from bytes).** Header `19 00 00 00` = **25 entries**, count/format word `25 64 0a 00`, then null-terminated STR paths **in play order**: `BUGSFMV3\TT.STR` → `BUGSFMV3\DLOGO.STR` → `fmv\AD.STR` → `BUGSFMV1\LEV1A.STR`, `LEV1B.STR`, … `LEV9A.STR`, `LEV9B.STR`. ⇒ the **front-end + cutscene SEQUENCE is data-driven by this manifest order** (boot logos TT/DLOGO/AD first, then per-level cutscenes A/B by progress) — closes "front-end FMV sequence logic". File = 509,800 B; the manifest is the first ~`0x100`, so the bulk after it is the **MDEC-player overlay code/data** loaded to Region-B `0x800B5788`.
**Trigger CONFIRMED.** Loader `0x8003e7c0` (store site `0x8003e7fc`) → file reader `0x80046330` with `a1 = 0x800B5788` (Region-B dest) loads `fmv.bin` (the only FMV string resident in the EXE: file off `0xb65c`).
**Correction (supersedes an over-eager recon guess):** the MDEC decode is **NOT** at `0x80010000` — that is the geometry mesh emitter ([[FUNC_80010000]]). The resident EXE carries **no** libpress/MDEC/STR strings (`DecDCT*`/`MDEC`/`.STR` absent), so the decode loop is **not resident** — it lives in the FMV.BIN overlay (`0x800B5788+`, after the manifest) and/or string-less libpress.
**Verdict:** playback **trigger** (shell loads FMV.BIN via `0x8003e7c0`→`0x80046330`) + **sequence** (the 25-entry manifest order) **documented** — acceptance MET. **Residual (local-only/overlay):** the MDEC decode/DMA call site inside the FMV.BIN overlay — Region-B disasm or a cold-boot `execTrace`.

## Named missing / next experiments (residual only)
- **MDEC playback call site** inside the FMV.BIN overlay (`0x800B5788+`) — Region-B disasm or cold-boot `execTrace`.
- Next (LOCAL-ONLY): from a **shell-phase fixture** (the same event-state fixture wall as [[Gap Audit|GAP-0033]]/level-warp), `execTrace` the front-end boot + `transferLog` an FMV load → map the FMV.BIN entry + MDEC call site. Record fork state; label local-only.

## Confidence ledger
STR/MDEC formats, FMV locations, FMV.BIN overlay residency — **CONFIRMED (static)**. FMV.BIN = 25-entry manifest, front-end **sequence** (TT/DLOGO/AD → per-level), **trigger** (`0x8003e7c0`→`0x80046330`) — **CONFIRMED (static, 2026-06-22)**. MDEC decode call site (overlay-resident) — **residual (bounded)**.

## Related
[[Asset - Disc file map]] · [[Asset Extraction Pipeline]] · [[Executable and Overlays]] · [[MEM - Global memory map]] · [[Menu and HUD structure]] · [[Blocker - FMV video is completely unanalyzed]] · [[Core - CD Streaming and Caching]] · [[DuckStation Fork Reproducibility]]
