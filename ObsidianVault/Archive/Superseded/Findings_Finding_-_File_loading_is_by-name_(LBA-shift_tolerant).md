---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - File loading is by-name (LBA-shift tolerant).md
aliases:
  - "Finding - File loading is by-name (LBA-shift tolerant)"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - File loading is by-name (LBA-shift tolerant).md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_File_loading_is_by-name_(LBA-shift_tolerant).md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - File loading is by-name (LBA-shift tolerant)
type: finding
confidence: STRONG (static/runtime evidence; pending one boot-test)
gstep: G34
tags: [finding, cdrom, fileloader, leveleditor, permanence]
---

# Finding — ABL loads files BY NAME (path), so disc LBA shifts are tolerated

> Decides the whole permanent-edit strategy: because the game resolves files by **filename/path** from a
> directory it reads **off the disc at runtime**, a rebuilt disc with shifted LBAs still works. ⇒ permanent
> level edits = **recompress chunk + rebuild**; no size-neutral patching / provenance rewrite needed.

**Confidence:** STRONG (static + runtime trace) · **Established:** G34 (2026-06-18)

## Evidence
1. **The file loader [[FUNC_80046330]] is passed a PATH STRING, not an LBA.** EXEC-trace at `0x80046330`
   during a level load (from `_2` pre-load save): `a0 → "level01\level1…"` (lowercase, backslash path).
2. **A runtime filename table in ISO9660 format** (`.RAW;1`, `RAW;1`, `LEVEL01`, `CIRCUS.RAW;1` …) lives at
   **`0x80086c00`**. That address is in the **BSS/heap region** (`≥0x80082800` is *not* file-backed per the
   executable map), so the table is **filled at runtime** — i.e. read from the disc's ISO9660 directory, not
   compiled into the EXE. `"LEVEL.RAW"` (the raw name) appears nowhere in 2 MB RAM; only the `;1`-suffixed
   directory form does.

⇒ The loader takes a path, looks it up in the disc-derived directory table to get the LBA. A rebuilt disc
updates that directory, so the game follows the new LBAs.

## Why it matters (permanence strategy)
- **Retires the #8 "balloon" blocker for the rebuild path:** recompressing an edited chunk (literal encoder,
  ~1.02–1.3× larger) shifts later files' LBAs, but the game re-resolves them by name ⇒ fine.
- So the seed pipeline (decompress → edit → **recompress whole chunk** → rebuild) generalizes to the **large**
  chunks (collision 32 / terrain 35) **without** needing size-neutral minimal-patch or the (broken) provenance
  tracker. Those remain only relevant for the `cd.overlayFile` *live-iteration* path (overlay can't exceed a
  file's sector span — but a full rebuild can).

## Boot test (G34) — PARTIAL PASS
Built an **auto-layout** disc (`REBUILD/abl_autolayout.xml` = `abl.xml` with the 350 fixed `offs` stripped)
with the seed-moved + chunk-35-ballooned `LEVEL.RAW` → **LEVEL.RAW grows +4 sectors, every later file's LBA
shifts**. Disc: `REBUILD/ABL_LBA_SHIFT_TEST.bin/.cue` (313901 sectors). Key build note: the **normal rebuild
XML pins LBAs** (`offs=…`), so it reproduces the original layout and *cannot* grow a file — you must use the
auto-layout XML to actually shift LBAs.
- **Cold-booted the test disc** (debugger.reset → BIOS vector `0xbfc02b74`): **it boots and runs** — the BIOS
  loaded `SYSTEM.CNF` + the EXE `SCUS_942.88` **by name from the shifted directory** (game reached its menu,
  pc `0x8004feXX`). ✅ Positive evidence that a shifted-layout disc resolves files by name.
- **Could NOT reach LEVEL01** to verify the game's `LEVEL.RAW` load: auto-navigating the menus blind failed
  (don't know ABL's menu; `captureFrame` kept crashing DuckStation so couldn't see the screen), and the
  emulator crashed ~6× under sustained debugger load.
- **Net:** boot + by-name EXE load on the shifted disc CONFIRMED; the in-level `LEVEL.RAW` load step remains
  operator-verifiable (boot `ABL_LBA_SHIFT_TEST.bin`, play to LEVEL01 → start seed should be far-left, file
  X=3000). Combined with the path-string loader + BSS directory table, **gate #1 is effectively closed.**

(Re-injection of a *literal*-recompressed chunk was already proven in-game by the seed edit,
[[Finding - LEVEL.RAW is compressed]] §G32.)

## Related
[[FUNC_80046330]] · [[Plan - Terrain+collision matched bump (Option B)]] · [[Finding - LEVEL.RAW is compressed]] ·
[[Relaunching DuckStation]] · [[Finding - Floor resource is LEVEL.RAW]]

## Source
EXEC-trace `0x80046330` (a0/ra) + 2 MB RAM string scan + filename table @ `0x80086c00`, from `_2.sav`.
