---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Relocation-aware DAT append.md
aliases:
  - "Finding - Relocation-aware DAT append"
migration_action: split
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Relocation-aware DAT append.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Relocation-aware_DAT_append.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Relocation-aware DAT append
type: finding
confidence: CONFIRMED
gstep: n/a (append track)
tags: [finding, dat, relocation]
---

# Finding — True net-new DAT entry injection works (relocation-aware)

> You *can* add brand-new objects to a level — the long-standing "black screen after Press X" was **stale baked relocation offsets**, not a count cap, token logic, or pool limit.

**Confidence:** CONFIRMED (in-game)

## Summary
- LEVEL.DAT contains **1248 baked absolute file-offset fields** (LEVEL01) that [[FUNC_8001CDC0]] relocates at load (`runtime = DATbase + baked_offset`).
- A naive +0x10 byte-shift append moves data but leaves those offsets unchanged → every relocated pointer lands 0x10 short → garbage in geometry/collision/object structs → the *consumer* crashes after "Press X" (PS1 has no MMU, so no fault — just wrong bytes).
- `tools/dat_reloc.py` reproduces the exact relocation walk and bumps all 1248 fields when records shift → clean append.

## Evidence
- **Confirmed milestone:** `ABL_ADD_TOKEN0X29_NEAR64_RELOC_TEST` added entry 70 (kind 0x29, coords `(4928,-50,-3655)`), count 70→71, all 1248 offsets relocated +0x10 → loads, plays, extra token visible & collectible, no glitch.
- Disproven alternatives (all in [[Hypotheses]]): seed-total cap, 70-entry parser cap, hardcoded code offset, contact-pool overflow, DAT-not-loading — each falsified by a targeted test.

## Related functions
[[FUNC_8001CDC0]] · [[FUNC_80053814]]

## Related memory structures
[[MEM - Type-0x3f placement record]]

## Related experiments
[[Experiment - DAT relocation-aware append]]

## Related fixtures / save states
n/a (disc builds)

## DuckStation APIs used
n/a (offline; earlier diagnosis used RAM dumps + `tools/diagnose_injected_ram.py`)

## Next steps
Use `tools/insert_type3f_entries.py` / `tools/apply_level_placements.py` (relocation-aware wrappers) for production insertion; never `tools/add_level_entry.py` (naive, obsolete).

## Source
`docs/DAT_FORMAT_AND_RELOCATION.md`, `docs/EXPERIMENT_LOG.md`; tool `tools/dat_reloc.py`
