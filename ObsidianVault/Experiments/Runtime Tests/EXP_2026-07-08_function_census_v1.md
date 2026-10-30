---
kind: experiment
id: EXP_2026-07-08_function_census_v1
name: Whole-image function census v1 (static multi-signal)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census, SYS_executable_image, SYS_overlays_and_runtime_loading]
fixtures: []
artifacts: [analysis/functions.json, analysis/functions.csv, analysis/code_coverage.md]
---

# EXP_2026-07-08_function_census_v1

## Question
How many functions does the image actually contain, where exactly, and can a
multi-signal static census close the gap between r2 `aaa` (837 functions,
79.4% code coverage) and the estimated 1,875–3,126 (old blocker B1)?

## Method
`tools/function_census.py` merging: `.sym` symbols, entry point, r2 `aflj`
(resident + 20 overlay passes), 644 PsyQ matches, exhaustive jal/j target scan,
prologue/epilogue patterns, known jr-dispatch tables, reachability BFS, string
ranges + data anchors as false-positive filters. Invariants enforced by
`tests/test_function_census.py` (9 tests; regeneration-identity local_media-gated).

## Observations
- **Resident: 1,370 functions, 89.1% of the text image classified as code**
  (417,684/468,992 B). The remaining ~11% is dominated by real data-in-text
  (strings 5.3%, jump tables, gp-window rodata).
- Confidence: 687 confirmed / 304 high / 262 medium / 117 low.
  Classification: 596 sdk_psyq / 620 unknown / 69 game / 50 bios_thunk / 1 crt0.
- **0 JAL anomalies** after two modeling fixes:
  1. The 51 out-of-text jal targets are the legitimate **resident→overlay entry
     surface** (recorded per-target with caller lists; `0x800B39A4` = universal
     Region-A entry, 13 call sites).
  2. 34 **gap_code** ranges: r2 `realsz` truncation left live call sites
     uncovered (e.g. Region-A loader `0x8003D620` truncated at `+0x58` with
     calls continuing at `+0x84`); the census emits explicit low-confidence
     continuation ranges so the call graph closes.
- Overlays: 192 functions; forcing all 51 union entry offsets into every
  variant over-fragmented (858 records) — structural filter (prologue / end
  marker at −8 / own entry) keeps only function-like ones per variant, the
  rest are recorded per-overlay as `entry_offsets_not_function_like`.
- Deterministic: back-to-back regeneration is byte-identical; inputs are
  sha256-pinned inside the artifact.
- The old B1 estimate of 1,875–3,126 functions was high: it assumed ~150–250 B
  per function over the whole image, but 596 SDK functions + big game
  functions push the mean up; 1,370 + explained data regions is consistent
  with 89.1% coverage.

## Conclusion
The census is the new canonical function inventory (Canon:
[[SYS_function_census]]). r2-only inventory and the "no persisted inventory"
blocker claim are superseded. Next enrichment: Ghidra export (gp-context run)
and Phase-4 dynamic hits.
