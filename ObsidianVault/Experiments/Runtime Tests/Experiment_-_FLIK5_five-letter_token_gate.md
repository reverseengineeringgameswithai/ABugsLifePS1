---
kind: experiment
id: Experiment_-_FLIK5_five-letter_token_gate
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - FLIK5 five-letter token gate.md
aliases:
  - "Experiment - FLIK5 five-letter token gate"
---

# Experiment — FLIK5 five-letter token gate

> Migrated from `ObsidianVault/Experiments/Experiment - FLIK5 five-letter token gate.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — FLIK5 five-letter token gate

Goal: prove the FLIK-letter/token gate can require more than the retail 4 letters. Test build:
`build/ABL_FLIK5.cue`.

## Implementation
- Move native LEVEL01 entries 50–53 in front of spawn.
- Append entry 70 as a duplicate native F: `kind 0x10`, status byte `1`.
- Patch the F handler so the original F still sets bit `0x01`, but appended entry 70 sets bit `0x10`.
- Patch all shared FLIK completion comparisons from `0x0f` to `0x1f`.
- Patch the SELECT panel to draw a fifth tile `0x10` slot at `x=0xd0`.

Files:
- `mod/mods/flik5.asm`
- `mod/placements/flik5_level01_spawn.yaml`
- `tools/verify_flik5.py`

## Failed approach to avoid
Do not make a fake F by overwriting the descriptor for a free kind such as `0x15`. That made the extra
pickup look like F, but also replaced the top-left Flik-head HUD icon. Correct fix: keep the appended
letter as native `kind 0x10` and special-case the appended entry address in the F handler.

## Verification
DuckStation API, isolated config `/tmp/duckstation-flik5c`, port `23463`, from-boot movie
`flik_to_level01_stall.mv.movie.json`.

`tools/verify_flik5.py` results:
- Mounted media: `~/Downloads/ABL/build/ABL_FLIK5.cue`, `SCUS-94288`.
- Runtime type-`0x3f` record: `0x801607fc`.
- Runtime type-`0x3f` count: `71`.
- After four letters: entries 50–53 consumed, mask `0x0f`, progress/lives byte `0x800A65A0` stayed `5`.
- After fifth letter: entry 70 consumed, mask `0x1f`, byte advanced to `6`.

Visual check:
- Captured `/tmp/flik5_select_fixed.png`.
- SELECT strip shows `FLIKF`.
- Top-left Flik-head icon is normal.

## Related
[[HUD letter glyphs and word swap]] · [[Menu and HUD structure]] · [[MEM - Type-0x3f placement record]] · [[FUNC_80053814]] · [[FUNC_800526F4]]
