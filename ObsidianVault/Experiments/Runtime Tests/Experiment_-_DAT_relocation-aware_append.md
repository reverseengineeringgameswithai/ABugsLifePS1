---
kind: experiment
id: Experiment_-_DAT_relocation-aware_append
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - DAT relocation-aware append.md
aliases:
  - "Experiment - DAT relocation-aware append"
---

# Experiment — DAT relocation-aware append

> Migrated from `ObsidianVault/Experiments/Experiment - DAT relocation-aware append.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — DAT relocation-aware append

> Inject a genuinely new type-0x3f entry without the black-screen failure — by fixing the baked internal offsets.

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of the built disc |
| Build image / tool | `ABL_ADD_TOKEN0X29_NEAR64_RELOC_TEST` via `tools/dat_reloc.py` / `tools/insert_type3f_entries.py` → `tools/rebuild_with_patched_dat.py` |
| Patch | append entry 70, kind `0x29` (seed token), at `(4928, -50, -3655)`; **all 1248 baked offsets relocated** |
| APIs used | offline build + operator in-game verification |

## Goal
Add a brand-new placement entry (not move/repurpose an existing one) and have it appear in-game.

## Procedure (reproducible)
1. `tools/dat_reloc.py --scan` to enumerate the 1248 relocation sites (it reproduces [[FUNC_8001CDC0]]'s relocation walk).
2. `tools/insert_type3f_entries.py <dat> --append-new 0x29:4928:-50:-3655 --write --out <out>` — appends and fixes every baked offset that shifts.
3. `tools/rebuild_with_patched_dat.py` → boot; press X past the loader; verify the new token in-game.

## Result
In-game CONFIRMED: the new token appears and is collectible. The earlier black-screen (from naive byte-shift append, `tools/add_level_entry.py`) was **stale internal baked offsets** after a `+0x10` shift — *not* a count cap or pool limit.

> [!warning] Do **not** use naive `tools/add_level_entry.py` on LEVEL01 (stale offsets → black screen). Use the relocation-aware path. Never repurpose berries 54–57.

## Conclusion
True net-new entry injection works once the 1248 baked offsets are relocated. See [[MEM - Type-0x3f placement record]] and the [[LEVEL.DAT object pipeline]].

## Linked findings / functions / structures
- [[Finding - Relocation-aware DAT append]] · [[Finding - Type-0x3f pickups are coordinate-moddable]]
- [[FUNC_8001CDC0]] · [[MEM - Type-0x3f placement record]] · [[Asset - LEVEL.DAT]]
## Source
`docs/DAT_FORMAT_AND_RELOCATION.md`, `ABL_RE_NOTES.md`
