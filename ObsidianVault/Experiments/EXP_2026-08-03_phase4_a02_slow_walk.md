---
kind: experiment
id: EXP_2026-08-03_phase4_a02_slow_walk
status: complete
source_state: original_game
system: [Gameplay_-_Input_and_Movement]
row: A02_slow_walk
---

# Phase 4 A02: slow walking (L2/R2), synthesized from A01

## Question

Operator: "go for a02." A02_slow_walk was the row's own next unstarted item — but before
launching fresh live investigation, checked for a matching donor row first (the lesson from
this session's own F04/F06/F15 passes: a thin row's whole named gap can sometimes already be
answered by an adjacent row that happens to trace the same code). Found one: `A01_move_run`
had ~11-hour-old uncommitted work tracing `FUNC_80048138` — the exact function A02's own
pre-existing binding already implicated via pad word `0x80082488`.

## Why this closes A02 without new live work

A02's own registry row already cited "L2/R2 walk modifier read from pad word `0x80082488`
(& `0x0300`)" — from an older synthetic probe, with no traced instruction. A01's
bounded-exhaustion pass (`analysis/phase4_a01_move_run.json`,
`src_re/move_run_80048138.c`, `tools/phase4_a01_static.c`) independently arrived at the
SAME address and mask while investigating ordinary run movement, because slow-walk isn't a
separate mechanism — it's the same movement function reading the same pad bit for two
independent purposes.

**Speed law**: `FUNC_80048138` reads pad word `0x80082488` (`andi v0,a0,0x300` at
`0x80048494`) to pick `input_cap = 0x300` (walk) vs `0x700` (run), scaled by the Q14
movement magnitude at `0x80049150..0x80049158`. `tools/phase4_a01_static.c` verifies this
instruction word (and 39 others) directly against the checked-in pristine ASM listing —
0 missing.

**Animation law**: `FUNC_800563D4` reads the SAME halfword (`lhu v1,0x2488(v1)` at
`0x80056474`) to select animation `29` (slow walk) vs `0` (run) vs `22` (idle) —
independently of the speed-cap consumer.

**Live counterfactual (from A01's own same-save controls)**: holding Up+R2 for 8 API frames
produced XYZ/velocity/forward-component identical to plain Up (`378` units) — the projected
forward component hadn't yet reached the `0x300` slow cap in that short window — but the
animation switched to `29` immediately. This is a genuinely useful finding for A02
specifically: **the speed cap and the animation selection are two independently-read
consumers of the same pad bit**, not one fused "walk mode" flag. A naive test that only
checks animation would conclude the walk modifier takes effect instantly; it doesn't — the
actual velocity change ramps in only once the forward component climbs high enough to hit
the lower cap.

**Turning and lifecycle**: the shared modulo-4096 heading-convergence law, decay/acceleration
constants, and release-to-idle behavior are identical code regardless of the walk/run bit —
there was never a separate "slow-walk turn law" to find, closing that part of A02's own
`missing` field by demonstrating its absence rather than leaving it unaddressed.

## What's NOT closed by this synthesis

A01's own live counterfactual ran only 8 API frames — deliberately short, enough to prove
the animation gate fires immediately, but never long enough to reach the slow cap and
re-measure a real displacement ratio. **A02's existing `0.605x` walk/run ratio is still the
older `phase2_action_oracle` synthetic-probe figure**, not independently re-derived from
fresh runtime data this pass. A longer (60+ frame) same-save Up+R2 hold would be needed to
do that directly, if ever worth the effort. Also open: whether the walk modifier interacts
differently with turning-in-place, slopes, or other action states — A01 tested plain Up
extensively but Up+R2 only for the short animation-gate check.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_a02_slow_walk.py tests/test_phase4_a01_move_run.py
cc -O2 -std=c11 -Wall -Wextra tools/phase4_a01_static.c -o /tmp/phase4_a01_static_check
/tmp/phase4_a01_static_check   # 40 checks, 0 missing
```

## Evidence

`analysis/phase4_a02_slow_walk.json`; donor evidence:
`analysis/phase4_a01_move_run.json`, `src_re/move_run_80048138.c`,
`tools/phase4_a01_static.c`, `ObsidianVault/Experiments/EXP_2026-08-03_phase4_a01_move_run.md`.
