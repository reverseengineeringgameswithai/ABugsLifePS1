---
kind: experiment
id: EXP_2026-07-08_c_decompilation_campaign_v1
name: C decompilation campaign v1 (scale matching + toolkit)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_original_compiler, SYS_function_census]
fixtures: []
artifacts: [analysis/decomp_progress.json, analysis/decomp_candidates.json, analysis/compiler_attempts.json, tools/decomp_candidates.py, tools/gen_matched_canon_notes.py]
---

# EXP_2026-07-08_c_decompilation_campaign_v1

## Question
With the C-gate open, can the substrate scale — prove the common function
classes, match a real batch, and become self-driving/measurable?

## Method
Built campaign tooling (auto-defsym symbol resolution, `decomp_candidates.py`
ranker, `decomp_progress.json` metric), then matched functions byte-exact:
each via a clean-room `src/main/*.c`, `compiler_proof.py` flag sweep,
`config/segments.yml` registration, `validate_build.py` SHA-1 gate.

## Observations
- **C-matched 2 → 17; total reconstructed 12 → 27** (10 asm + 17 C).
  `validate_build.py` SHA-1 `af43de22…` PASS at every step (byte-splat).
  `decomp_progress.json`: 2.53% of resident functions, 0.15% by bytes.
- **Auto-defsym** works: C sources call engine functions by census name or an
  `sub_<addr>` anchor, and reference absolute globals by `g_<addr>`, with no
  hand-listed externs (proven on `0x8002d64c` → `sub_8002b424`, `0x800457a0`
  → `CdSearchFile`, `0x8004a0f4` → `sub_8005044c`).
- **Class proofs**: 1-callee wrapper (`0x8002d64c`), branch+delay-slot leaf
  (`0x80024ddc`), and — the key one — saved-reg + stack-local + retry-loop
  (`0x800457a0`), which **pins the optimization level to -O2** (matches at
  `-O2`, differs at `-O1`). Recorded in [[SYS_original_compiler]].
- **Breadth batch**: 11 small absolute-addressing game/unknown functions
  (getters/setters/field-inits/global swaps) + the understood named
  `thumper_driver_cb` (`0x8004A0F4`, Thumper-boss driver).
- **gp-relative class DEFERRED** (recorded, not blocking): cc1 emits
  `lw reg,sym`; GNU-as renders an extern global as absolute `lui`+`lw` (matches
  the game's absolute globals, ~97% of accesses) but not the occasional single
  gp-relative `lw` — that needs a linker-script `_gp` + small-data placement
  (substrate v2).
- **Self-driving**: the ranker excludes matched / data-globals / truncated /
  jr-table / oversized / gp functions and scores by size + callees +
  behavior-known; 343 game/unknown candidates remain queued.

## What was NOT matched (honest limits)
- The understood pickup/HUD cluster (`dat_parser` 0x8001CDC0 ~1.5 KB,
  `source3f_dispatch` 0x80053814 ~1.8 KB, HUD/walker/alloc) is all large and/or
  jr-table/gp — **deferred to a depth milestone**. Phase D substituted the
  named `thumper_driver_cb` per plan.
- A few candidates were skipped rather than forced (load/store scheduling on a
  3-word copy; a branch-layout difference; the 96 B loop `0x8003E760`) — logged,
  not faked.

## Conclusion
The substrate scales: matching is now a measured, ranked, one-function-at-a-time
loop, and the compiler/flags (`-O2`) are fully pinned. Each matched function has
a Canon `FUNC_<addr>` note (bytes = original-game truth). Next: a depth
milestone on the big understood cluster + a substrate v2 for gp/switch-table
classes.
