---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - transferLog.md
aliases:
  - "API - transferLog"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - transferLog.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - transferLog
type: api
category: CD-DMA
tags: [api, duckstation, dma, cdrom, provenance]
---
# API — transferLog (CD-ROM + DMA provenance)

> Asset-load provenance the CPU watchpoints can't see: DMA blocks and CD-ROM sector reads.

## Methods & syntax
- **`transferLog.start` / `stop` / `clear`** (requires a loaded system).
- **`transferLog.get {offset?, limit?, kind?:"dma"|"cdrom", channel?, direction?, address?:{min,max}, lba?:{min,max}}`** → `{events:[{frame, cycle, kind, channel?, channel_name?, address?, word_count?, bytes?, direction?, lba?}], total, truncated}`.
- **`transferLog.resolve {address:<number|"0x...">}`** → `{address, resolved, file, disc, lba, fileOffset, sourceRange:{start,end}, compressed, compression:{type:"known"|"unknown"|"none", compressedOffset, decompressedOffset, confidence}, confidence:"exact"|"probable"|"unknown", candidates:[…], ambiguous, notes:[]}`. **Static address → disc/file provenance, resolvable at any time** (incl. from a post-load save state) — see below.
- **Provenance (live):** CD `lba` (ch3 CDROM `from_device`) → RAM target of a sector; ch2 GPU `to_device` = RAM source of a display list/texture upload. Correlate a CD `lba` to the following ch3 DMA `address` to map disc sector → RAM region.
- Companions: `emulator.getCdromState`, `emulator.getDmaState` (live state only; no history), and [[API - provenance.timeline]] for a sorted RAM/DMA/access/VRAM evidence report.

## Static provenance (`transferLog.resolve`)
> The reverse of `get`: you have a RAM **address** and want the disc file it came from — without correlating raw events by hand, and **even from a save state** captured after the load.

Evidence, strongest first → top-level fields are the primary, `candidates`/`ambiguous` carry the rest:
1. **Known decompression records** — the only source that returns `compressed:true`. *None tracked yet* (packed assets fall through to DMA correlation).
2. **Executable load map** — boot EXE's PS-EXE header → deterministic RAM→disc mapping, `confidence:"exact"`. **Works from any post-load save state** (no DMA history needed).
3. **DMA↔CD-ROM correlation** — a device→RAM block covering the address (from the buffered transfer log) paired with the sector streamed just before it, mapped to a file via the ISO file table. `confidence:"probable"`; needs recorded history, so re-`start` + replay the load after a `loadState`.

`resolved:false` + a `notes` entry when nothing matches (e.g. a streamed-asset address in a save state with no recorded DMA — re-arm `start` and replay to recover it). Reads the live log only; never disturbs it.

## Best use in ABL RE
Mapping disc → RAM: which LBA range supplies a buffer, and which DMA channel uploads it to VRAM.

## Common mistakes / gotchas
> [!warning] Disabled+cleared on [[API - loadState]] — **`transferLog.start` again after a load.** Ring 100000 events.
- This is the answer to "the data appeared in RAM but no CPU instruction wrote it" — it came via DMA.

## ABL examples
LEVEL.RAW load provenance: **disc LBA 1823–4149** → RAM, underpinning [[Finding - Terrain on-disk source is chunk 35]] and [[Finding - Floor resource is LEVEL.RAW]].

`transfer-resolve --address <terrain RAM addr>` (after `transfer-start` + replaying the level load) maps a terrain RAM address straight back to `LEVEL01/LEVEL.RAW` + `fileOffset`, turning "which chunk is this RAM struct from" into one call instead of hand-correlating ch3 DMA `address` against CD `lba`. From a level save state it still resolves EXE-resident addresses (`confidence:"exact"`); streamed-asset addresses need the log re-armed + a replay. Directly relevant to [[Blocker - Disc provenance is unverified]].

## Related
[[API - accessLog]] · [[API - gp0Trace]] · [[Asset - LEVEL.RAW]] · [[Playbook - Find geometry sources]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
