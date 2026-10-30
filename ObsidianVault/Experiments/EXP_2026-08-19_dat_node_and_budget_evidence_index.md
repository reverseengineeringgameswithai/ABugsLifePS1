---
kind: experiment
id: EXP_2026-08-19_dat_node_and_budget_evidence_index
name: LEVEL.DAT node and budget evidence index
status: evidence_index
created: 2026-08-19
experiment_date: 2026-08-11
source_state: original_game
systems: [SYS_dat_node_array_and_budgets]
evidence:
  - docs/G3_NATIVE_DAT_GROWTH_RESULT.md
  - docs/G3_NATIVE_DAT_SIZE_CAP_TEST.md
  - docs/LEVEL_REPLACEMENT_STATUS.md
  - docs/LEVEL_REPLACEMENT_BLOCKER_TRIAGE.md
---

# LEVEL.DAT node and budget evidence index

This is a provenance repair for the 2026-08-11 authoring experiments. It does
not claim a new run. The source documents retain the cold-boot commands,
identity controls, size-bisect results, residency checks, screenshots, and
correction history.

## Claims supported by the retained record

- LEVEL01 contains 42 `0xC0080000` floor-node records followed by a distinct
  `0xC0040000` run; appending a floor node would overwrite the second run.
- A marker-and-pointer-only conversion produced no coherent draw, establishing
  that another registration/culling record is required.
- A 388,388-byte / 190-sector LEVEL.DAT passed the recorded gate, whereas
  398,388 bytes failed. This is an empirical bracket, not a universal allocator
  law or a cross-level guarantee.
- The retained chunk-32 results support approximately 260,000 decompressed
  bytes as present authoring guidance, with non-monotonic failures above it.

## Canon consumer

[[SYS_dat_node_array_and_budgets]]

