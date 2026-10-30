---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - LEVEL.BIN and overlays.md
aliases:
  - "Asset - LEVEL.BIN and overlays"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - LEVEL.BIN and overlays.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_LEVEL.BIN_and_overlays.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - LEVEL.BIN and overlays
type: asset
confidence: CONFIRMED
tags: [asset, overlay, executable]
---

# Asset — LEVEL.BIN & code overlays

> Per-level code overlays swapped into two fixed RAM regions, plus the per-object model/behavior overlays.

## Summary
The boot executable `SCUS_942.88` (resident `0x80010000`–`0x800827FF`) loads code overlays at runtime:
- **Region A — base `0x800B39A0`**: per-level code overlay `LEVEL0N\LEVEL[M].BIN`. Universal entry `level_overlay_init` at `+4` (`0x800B39A4`); loaded by `fcn.8003d620` via [[FUNC_80046330]] (filename built by `fcn.80046618`). Verbs include `0x800B3AEC` (object spawner) and `0x800B3BB8` (event/update).
- **Region B — base `0x800B5788`**: rotates through `bits\memory.bin` (MEMORY.BIN, 36448 B, init `+0x7D90` = `0x800BD518`) and `fmv\fmv.bin`; loaded by `fcn.8003f5b8`.

## Per-object overlays (`OVL/*.BIN`)
Per-object model + behavior. **Berry identity (color/model) lives in the overlay model, not in the LEVEL.DAT entry** — so you move a berry by editing its DAT entry coords but you must not change its kind ([[Finding - Type-0x3f pickups are coordinate-moddable]]).

## Other level resource files
`GFX\*.RAW` (per-level VRAM/texture), `PAD\PATH*.BIN` (pathfinding ≤1.3 KB), `BITS\PLANTTER.ALL`, `SEED.ALL`, `TTLOGO.BGR` (title image).

## Related
- Functions: [[FUNC_80046330]] · [[FUNC_8003CF2C]]
- Assets: [[Asset - LEVEL.DAT]] · [[Asset - LEVEL.RAW]] · [[Asset - Disc image and rebuild]]
- Source: `docs/EXECUTABLE_AND_OVERLAYS.md`
