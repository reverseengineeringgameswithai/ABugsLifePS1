# Phase 4 - Static ASM Prerequisite Gate

**Navigation:** [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Phase 4 execution note]] · [[Phase 4 - Extent Audit|Extent audit]] · [[Phase 4 - Frontier Closure Workbench|Frontier workbench]]

## Purpose

This gate supplies shared, reproducible evidence needed before a row-specific
semantic frontier can claim mechanical completeness. It does not close Item 2,
does not alter any row status, and does not widen the direct static writer
census.

The gate exists because Phase 4 repeatedly promoted facts proved over a subset
to facts about a larger universe. It records four universes separately:

1. Every byte in the hash-pinned loaded image.
2. Every byte claimed by a typed extent, plus every explicit unclassified gap.
3. Every aligned word with an architecturally valid indirect-control encoding.
4. Instructions reached from typed code/thunk entries by direct control-flow
   edges only.

None of those universes is silently substituted for another.

## Tools and contracts

- `tools/phase4_static_asm_probe.c` performs the byte and static MIPS probe.
- `tools/phase4_static_asm_prereqs.py` compiles the C probe and joins its output
  to hash-pinned repaired extents and retained Phase 3 indirect evidence.
- `tools/verify_phase4_static_asm_prereqs.py` independently decodes the raw
  opcode-candidate set and optionally performs a clean deterministic rebuild.
- `config/phase4_static_asm_prereqs.json` pins the source image, expected
  universes, named site delta, and bounded `jr` declarations.
- `config/phase4_static_asm_ratchet_contract.md` is the detached-verifier
  acceptance contract.

## Current shared findings

The repaired resident extent identity partitions 468,992 loaded text bytes into
435,104 typed bytes and 33,888 explicitly unclassified bytes. The partition is
mechanically complete; semantic image ownership is not complete. The gaps must
not be called padding without additional evidence.

The retained indirect map has 234 typed `jr`/`jalr` sites. The repaired extent
identity adds one named site, `jr t1` at `0x80010364`, for a current conservative
typed candidate universe of 235. Exact-set reconciliation is required; equality
of aggregate counts is never sufficient.

The direct-edge fixed point reaches all 393 words in `scene_flow_dispatcher`,
instead of the prior entry-only 8/393. This is direct/callee evidence, not writer
census evidence. Indirect targets are not followed by that verdict.

The 16-entry mover dispatch at `0x8004C868` also lands at `0x8004C898`, the
start of a 20-byte executable sequence in an unclassified extent gap. The gate
retains that target and its ownership defect explicitly; it does not stretch a
neighboring extent or drop the table entry to manufacture coverage.

> 2026-08-06: the static index DECODED that island from the gate's proved
> target with an explicit stopping proof and promoted it to a first-class
> census record (`jr_target_island_8004c898`, records 1190 → 1191) — without
> widening either neighbouring extent. The gate receipt itself is unchanged and
> still names the region as its own defect, so the census ↔ gate partition
> reconciliation now carries it as a NAMED gate-only gap. The gate artifact is
> also now a first-class member of the index's `source_dependencies` (path +
> sha256), and the index's `cfg_universe` names what it consumes from it. See
> `EXP_2026-08-05_phase4_f01_objective_lifecycle.md`, 2026-08-06 increment.

## Verdict vocabulary

- `image_byte_partition_complete`: claimed extents plus explicit gaps cover the
  loaded image exactly.
- `semantic_image_ownership_complete`: every byte has a proved semantic owner.
- `typed_indirect_inventory_complete`: every valid candidate in typed code or
  thunk extents has a stable site record.
- `direct_cfg_fixed_point_complete_for_declared_universe`: the direct-only CFG
  work queue reached a fixed point.
- `indirect_target_sets_complete`: every indirect site has a proved complete
  target set or a complete external-owner boundary.

Only the first, third, and direct-universe verdicts may be true in the initial
receipt. Item-2 readiness and strict frontier closure remain false.

## Reproduction

From a clean detached checkout with the hash-pinned pristine image provisioned:

```bash
python3 tools/phase4_static_asm_prereqs.py \
  --output analysis/phase4_static_asm_prerequisites.json
python3 tools/verify_phase4_static_asm_prereqs.py \
  --artifact analysis/phase4_static_asm_prerequisites.json \
  --rebuild \
  --output analysis/phase4_static_asm_prerequisite_verdict.json
```

The verifier must run in a second fresh detached worktree before any registry
status is banked. This shared gate itself does not authorize a registry change.

## First consumer, and what the reconciliation actually found (2026-08-06)

`tools/phase4_frontier_extractor.py` consumes this receipt for F01 and reconciles
against it **as a set, in both directions**, failing closed on any resident
indirect site absent from the typed candidate universe. See
[[Phase 4 - Frontier Extractor]].

| | |
|---|---|
| F01 resident indirect CALL sites | 94 — all 94 among the 139 `jalr` sites, 0 outside |
| F01 resident indirect JUMP sites | 51 — all 51 among the 96 `jr` sites, 0 outside |
| gate sites outside that frontier | 45 `jalr` + 45 `jr` |
| out-of-gate-scope sites, named not dropped | 3 (this gate is resident-only) |

⚠️ **The gate's resolved target sets do not reach indirect CALLS.** All 87 bounded
target sets are `jr` switch islands; **0 of 139 `jalr` sites** have one. So the gate
bounds the targets of every resident indirect *jump* F01 retains and of none of its
indirect *calls*. Anyone expecting the 235-site inventory to dispose of a row's
unbounded call unknowns should read that line first.

⚠️ A first attempt at the reconciliation upper-cased hex strings on one side only
and reported an intersection of zero everywhere. The counts looked plausible;
printing the set difference is what exposed it.
