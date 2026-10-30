---
kind: experiment
id: EXP_2026-07-08_ghidra_gp_context
name: Ghidra $gp register context + global recovery check
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census]
fixtures: []
artifacts: [ghidra/scripts/SetGpAndExport.java, "ghidra/out/ghidra_<addr>_gp.c (regenerable, untracked - derived from the copyrighted EXE)", "extracted/re_baseline/ghidra_functions.csv (regenerable, untracked)"]
---

# EXP_2026-07-08_ghidra_gp_context

## Question
Does setting the MIPS `$gp` register context (`0x80081D98`, the runtime gp that
r2 already assumes via `anal.gp`) make Ghidra's decompiler resolve gp-relative
globals correctly — and can the same run finally export a Ghidra function list
for the census?

## Method
`ghidra/scripts/SetGpAndExport.java` on the existing ABLPilot project
(headless, `-process SCUS_942.88`): set gp register context over
`0x80010000–0x80082800`, `analyzeAll`, export text-range functions to
`extracted/re_baseline/ghidra_functions.csv`, re-decompile the 3 pilot samples
to `ghidra/out/ghidra_<addr>_gp.c`. Before/after diff vs the pre-gp
`ghidra_<addr>.c`; resolved globals cross-checked against `src_re` +
`re_symbols.sym` ground truth (r2 with `anal.gp` set is the oracle).

## Observations
- **`unaff_gp`: 28 → 0** (`ghidra_8001cdc0`); other two samples were already 0
  (they use absolute addressing).
- Resolved-global spot checks (all CONFIRMED against ground truth):
  - `current_scene_id` (0x80082504) now appears **by imported name** inside
    `FUNC_8001CDC0` — the scene-gated branch (0xf/0xb) is readable directly.
  - `DAT_8008238C` = gp+0x5f4 with scene-gated values 0x580/0x500/0x600 —
    matches the "scene-gated sizes @gp+0x5f4" open item recorded in
    `docs/DECOMPILATION_PLAN.md` / `src_re/dat_parser_8001cdc0.c`.
  - `DAT_80091210` — the pass-2 output table already documented in src_re.
  - `grain_count_hud_mirror` (0x800A65A1) resolves by name in the HUD sample.
- Export: **699 text-range functions (74 carrying real names)**; FUN_* Sanitized
  to empty so `re_symbols.sym` stays the only naming authority.
- Census refresh: ghidra signal now non-zero; resident census 1,370 → 1,371
  functions, coverage 89.1% → 89.3%; all census invariants still pass.

## Conclusion
Ghidra's gp-relative global recovery is now trustworthy **for the checked
surface**: the mechanism is proven, but any individual recovered global outside
the spot-checked set still needs verification before Canon promotion (rule
recorded in `ghidra/PILOT_REPORT.md`). The ghidra discovery signal is live in
[[SYS_function_census]].
