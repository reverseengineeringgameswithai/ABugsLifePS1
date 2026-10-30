---
type: experiment
phase: 4
row: B03
date: 2026-08-02
status: bounded-exhaustion-partial
method: c-static-asm-and-pristine-exe
---

# Phase 4 B03 bounded exhaustion

## Question

After the Interpreter movie closed sustained glide, steering, landing, release,
and latch timing, exhaust the remaining high-yield offline B03 questions without
reproducing the repository-wide pointer-provenance wall or demanding redundant
stage movies.

## Method and identity

`tools/phase4_b03_asm_static.c` directly parses all retained hand-written ASM,
decodes raw control transfers, propagates constant addresses and call arguments,
classifies every direct absolute or typed player-relative `0x800A659E` access,
and verifies the brown-tier/type-8
dispatch tables in the hash-verified pristine executable.

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  tools/phase4_b03_asm_static.c -o /tmp/phase4_b03_asm_static
/tmp/phase4_b03_asm_static \
  asm/hand_written REBUILD/files/SCUS_942.88 \
  > analysis/phase4_b03_dandelion_static.json
```

- C source SHA-256: `2cea55aa079a854da53812c65b79a79c7596907a5a431e8d8e4d0b4533e14cfc`.
- Generated artifact SHA-256: `09d7728928dcb3320c8a8450e3c41039ada8363aac03624e073e97ab536fefcf`.
- Pristine `SCUS_942.88` SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Corpus: 892 files, 100,425 instructions.
- Runtime fixture and state are centrally pinned in `tools/fixtures.sha256`.
- No DuckStation or PCSX-Redux process was launched.

## Direct frontier

Observation: the retained ASM has exactly 19 direct latch accesses: 15 absolute
and four typed `$s1+0x9E` player-relative sites, totaling ten reads and nine
writes. Every site is classified by PC and owner in the JSON artifact. Direct
writers store only literal `0`, `11`, or `12`; no direct timer, decrement, or
arithmetic writer exists.

Boundary: this is a complete direct retained-ASM census, not a proof over every
indirect player pointer or overlay alias. That stronger proof inherits the same
general pointer-provenance wall already recorded for B06/B08 and is deliberately
not rebuilt for B03.

## New static conclusions

- Pristine resident tables bind brown tier 3 to plant type `8` and type `8` to
  handler `0x8005C818`.
- The launch and latch have explicit native negative conditions: selected-slot
  mismatch, missing plant activation bits, failed radius-40 sphere, or harvester
  flag `0x80`.
- `0x80051B84` directly gates the overhead effect on latch `11` and action
  lockout zero, then calls `effect_mesh_transform` at `0x80051C30` with origin
  player Y `-22528`.
- `actor_skinned_update` writes player animation `18` at `0x800568D4` while
  latch `11` is active.
- Direct retirement is grounded `0x80048700`, level transition `0x8004A87C`,
  harvester activation `0x80051EA4`, and respawn `0x8005B314`.
- The visual tail is corrected to the runtime evidence: greater than two and at
  most eleven movie frames after latch clear. Exact display-buffer timing is not
  claimed.

## Phase 4 scorecard

| # | Item | Result |
|---|---|---|
| 1 | Original oracle | Advanced: one native hash-pinned Interpreter fixture |
| 2 | Complete frontier | Deferred: direct surface complete, shared indirect wall remains |
| 3 | Typed state | Met |
| 4 | Lifecycle | Advanced: direct retirement paths classified |
| 5 | Original interfaces | Advanced: core physics, presentation, animation, sound and propeller bridge |
| 6 | Campaign breadth | Deferred as low return |
| 7 | Cross-system | Advanced |
| 8 | Source closure | Met, documentation-grade semantic C plus byte-exact ASM |
| 9 | Durable evidence | Advanced: central fixture pins and regenerable C gate |

## Exit decision

**High-yield B03 scope is exhausted; the Phase 4 row remains `partial`.** Stop
standalone work here. Reopen only for general pointer typing or when a concrete
MOD/campaign requirement makes native dandelion-to-propeller combination,
stage-specific reachability, or exact GPU tail timing material. No new movie is
currently required, and cold boot is not required absent a disc/code/asset
change.

## Related

- [[SYS_dandelion_glide]]
- [[EXP_2026-08-02_phase4_b03_dandelion_capsule]]
- [[EXP_2026-08-02_phase4_b03_dandelion_interpreter_trace]]
- `config/phase4_b03_dandelion.yaml`
