---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - CD overlay.md
aliases:
  - "API - CD overlay"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - CD overlay.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - CD overlay
type: api
category: CD-DMA
tags: [api, duckstation, cdrom, overlay, assets, iteration]
---
# API — cd.* (CD file/sector overlay)

> Substitute the bytes the running game reads off the CD — per file or per sector — **without rebuilding or swapping the disc image.** Fast RE iteration; final validation still needs a real rebuilt BIN/CUE.

> [!caution] Status (2026-06-18): implemented + build-clean, but **not committed**. **First live test — DID NOT intercept the LEVEL.DAT read:** overlaying `LEVEL01/LEVEL.DAT` (resolved LBA 2906, 1 sector) and advancing the LEVEL01 load gave **`served_count=0`** and the game loaded the **original** DAT. ⇒ the game's read path for LEVEL.DAT isn't caught by the `ProcessDataSector` hook (likely a bulk/streamed read). **Treat the overlay as unverified for level-data reads.** Working live-verify alternative: the **save-state-repoint** method → [[Experiment - FLIK letters disc mod demo]] (rebuild the BIN, repoint a pre-load state's embedded disc path to it, loadState, advance).

## Methods & syntax
- **`cd.overlayFile {path, base64|hex}`** → `{key, is_file:true, file_path, start_lba, sector_count, byte_length, served_count}` — resolve an ISO9660 `path` (e.g. `LEVEL01/LEVEL.RAW`, case-insensitive, `;1` stripped) to its on-disc LBA range and overlay it. Requires a loaded disc. Re-install replaces.
- **`cd.overrideSectors {lba, base64|hex}`** → same info — overlay a **raw** sector range from `lba` (no disc/FS needed).
- **`cd.clearOverlay {path}`** → `{removed}` · **`cd.clearSectorOverride {lba, length?=2048}`** → `{removed_sectors}` · **`cd.clearOverlays {}`** → `{removed}`.
- **`cd.listOverlays {}`** → `{active, count, total_sectors, overlays:[…]}` — each overlay's `served_count` = covered sectors the game has read since install.
- Client verbs: `cd-overlay-file --iso-path … --data-file …`, `cd-override-sectors --lba … --data-file …`, `cd-clear-overlay`, `cd-clear-sector-override`, `cd-clear-overlays`, `cd-list-overlays`. MCP tools: `cd_overlay_file(path, data_path)`, `cd_override_sectors(lba, data_path)`, `cd_clear_overlay`, `cd_clear_sector_override`, `cd_clear_overlays`, `cd_list_overlays`.
- Launcher cold-boot helper: `launch_debugger_instance.sh start ... --overlay LEVEL01/LEVEL.RAW=/abs/LEVEL.RAW
  --overlay LEVEL01/LEVEL.DAT=/abs/LEVEL.DAT`. The launcher boots the isolated instance, waits for the API, then
  installs each overlay via `cd.overlayFile` before returning READY. This preserves a cold-boot/movie workflow without
  rebuilding a disc.

## Mechanics
- **Granularity = one 2048-byte data sector.** Replacement is split into `ceil(len/2048)` sectors (tail zero-padded); only the **user-data payload** is swapped — the sector header/subheader the game parsed is untouched, so the read looks normal. A read spanning sectors is served sector-by-sector (covered → overlay bytes, uncovered → original).
- **Length need not match:** a file overlay may be **shorter** than the file (trailing sectors keep original bytes), but **not longer** than its on-disc sector span (`-32602`). Sector overlays bounded only by caps (65 536 sectors/overlay, 262 144 total).
- Hook is in `CDROM::ProcessDataSector` behind a one-relaxed-atomic gate — **zero cost when nothing is installed.** XA realtime-audio sectors are **not** overlaid.

## Best use in ABL RE
Iterate on an asset edit without re-mastering the disc: overlay → load a pre-load state → advance → observe. Pairs with [[API - experiment runner]] for a deterministic install→loadState→advance→diff loop, and with [[API - visual diff]] / [[API - gpu.readVramRect]] to confirm the on-screen effect of a [[Finding - Localized terrain edit]].

## Common mistakes / gotchas
> [!warning] **NOT cleared on [[API - loadState]]** (unlike the non-halting traces) — overlays **persist across loads** on purpose, so you install once and re-load to iterate. They are dropped only on **game unload / server stop**, and are keyed to the **mounted disc** — `cd.clearOverlays` before switching discs or the LBAs go stale.
> [!warning] Overlays replace the **on-disc bytes**. [[Finding - LEVEL.RAW is compressed|LEVEL.RAW is compressed]], so overlaying it means supplying the **compressed** form the game decompresses — not raw terrain. Edit/repack in the on-disc encoding.
- Not serialised into save states; affects only **future** reads. A state saved *after* the file already streamed into RAM captures the (already-overlaid) RAM bytes — loading it does not re-read the disc.
- Verify it actually took: `served_count > 0`, then cross-check the bytes in RAM via [[API - transferLog]] (ch3 CDROM→RAM target) + a `readMemory`.

## ABL examples
LEVEL.RAW lives at **disc LBA ~1823–4149** (see [[API - transferLog]], [[Finding - Floor resource is LEVEL.RAW]]). Overlay it, advance the level load, and confirm:
```
cd-overlay-file --iso-path LEVEL01/LEVEL.RAW --data-file edited_level.raw   # served_count:0, sector_count:~110
emulator.advanceFrames {frames:300}                                         # (or loadState a just-before-load save)
cd-list-overlays                                                            # overlays[0].served_count > 0  ✓ game read it
cd-clear-overlay --iso-path LEVEL01/LEVEL.RAW
```
For a surgical patch, `cd.overrideSectors` at the exact LBA of [[Finding - Terrain on-disk source is chunk 35]] / [[Finding - Collision on-disk source is chunk 32]] instead of the whole file.

## Related
[[API - transferLog]] · [[API - experiment runner]] · [[API - loadState]] · [[Asset - LEVEL.RAW]] · [[Asset - LEVEL.BIN and overlays]] · [[Finding - Localized terrain edit]] · [[Playbook - Find geometry sources]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md), client ~/duckstation/scripts/debugger-client/
