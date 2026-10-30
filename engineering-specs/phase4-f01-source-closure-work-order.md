# Work order: byte-match `player_vertical_update` (F01 `source_closure`)

**Date issued:** 2026-08-10 · **Baseline:** current `master` (record
`git rev-parse HEAD` and `git status --short`; preserve operator WIP).
**Executor:** any agent (drafted for Codex hand-off; self-contained).
**Dimension:** F01 DoD `source_closure` — see
`ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - F01 Closure Roadmap.md`.

---

## 1. The target, and the whole job

F01's `source_closure` dimension is `partial`: `FUNC_80038F38` is byte-matched;
**`player_vertical_update` @ `0x80048138`, 6,004 bytes, is not.** Byte-matching
it is the entire scope of this order.

Byte-matched means: C compiled through the project's proven original toolchain
produces machine code **byte-identical** to the pristine image at that address.
Not "functionally equivalent." Not "close." Byte-identical, or it is a named
near-miss with an exact word-diff count.

This is a big function but a well-precedented task — the project has
byte-matched 968 functions ([[decomp-v5-bytepercent]]).

## 2. Toolchain and existing machinery — use it, do not rebuild

- **Compiler contract (proven, do not deviate):** GCC 2.7.2, `-O2 -G0
  -mcpu=3000`, assembled via `maspsx --dont-expand-li` (add `--expand-div`
  where the existing harness does). See [[psyq-compiler-proof-c-gate]].
- **`tools/substrate_common.py`** → `compile_at(source, va, compiler_id=...,
  cc1_flags=..., maspsx_args=..., include_dirs=...)` is the canonical
  compile-and-place harness. Byte comparison is against `original_exe()` at
  `va_to_off(va)`.
- **`tools/dc_permute.py`** — the decomp permuter. When the source is
  semantically right but a few words off due to GCC-2.7.2 scheduling or
  register allocation, this hill-climbs semantics-preserving rewrites until the
  diff reaches zero. **Use it for the endgame; do not hand-tune scheduling.**
- **`tools/gen_handasm.py`** — hand-asm generation, the fallback when C cannot
  express the shape.
- **`src_re/abdomen_bounce_80048138_8004abf4.c`** already carries a
  documentation-grade slice of this function with a typed `PlayerA05` struct
  (field offsets +0x00 x/y/z, +0x2c vx/vy/vz, +0x48 floor_y, +0x7a
  action_timer, +0x80 air_state, +0x82 grounded, +0x84 dive_phase, +0x88
  animation_selector). ⚠️ That file is explicitly **not** a standalone original
  function and is not linked into the mod — treat it as a semantic reference
  and a struct head-start, **not** as a seed to compile.
- `src_re/re_types.h` holds the shared typedefs.

## 3. Method

1. **Disassemble and partition.** 6,004 bytes is ~1,500 instructions. Recover
   the CFG, identify the frame layout, callee-saved register discipline, and
   the call sites. Produce a block-level map before writing any C.
2. **Type the state.** Extend the `PlayerA05` reference struct to every offset
   this function actually touches. Field naming should follow observed
   semantics; where semantics are unknown, name by offset and say so.
3. **Write C incrementally and compile continuously.** Do not write 1,500
   instructions' worth of C and then compile. Match region by region, keeping
   a running word-diff count against the image so progress is measurable and
   regressions are immediate.
4. **Close the last words with `dc_permute.py`.** Scheduling/regalloc residuals
   are its job.
5. **If a region resists C entirely**, isolate it, record exactly which
   instruction shape defeats the compiler, and use `gen_handasm.py` for that
   region only — with the boundary and the reason named in the receipt.

## 4. Deliverables

- `src_re/player_vertical_update_80048138.c` (new file; do **not** overwrite
  `abdomen_bounce_80048138_8004abf4.c`).
- `analysis/phase4_f01_source_closure.json` — receipt with: target address and
  size, compiler contract used, image sha256, **word-diff count (0 on match)**,
  per-region match status, any hand-asm regions with their justification, and
  the reproduction command line.
- A `--check` mode that re-compiles and re-verifies byte-identity from a clean
  checkout.
- Test coverage in `tests/` asserting the byte-match (or the pinned near-miss
  count, if that is the honest outcome).

## 5. Success / stopping criteria

- **MATCH:** word-diff 0 across all 6,004 bytes. `source_closure` becomes
  eligible for promotion (promotion itself is a separate, verifier-gated step —
  do not attempt it).
- **NEAR-MISS:** bank the exact residual word count, the addresses of the
  differing words, and the specific compiler behavior implicated. A pinned
  near-miss is a legitimate deliverable; a vague "mostly matches" is not.
- **Budget guidance:** if 6 hours of compute produce no measurable diff
  reduction, stop and report the wall rather than grinding — same
  bail-out discipline as the pilot work orders.

## 6. Hard rules

- **Do NOT touch the Phase-4 analysis chain.** Nothing under
  `analysis/phase4_*frontier*`, the census, `config/phase4_f01_frontier_seed.yaml`,
  the gate artifacts, or the typed-state outputs. Those pin each other by
  sha256 and are regenerated by other workstreams; a write from here corrupts
  them. This order is deliberately file-disjoint: `src_re/`, one new
  `analysis/` receipt, one new test.
- **Do not modify `analysis/mechanics_baseline.yaml`** or claim the dimension
  met. F01 stays `partial`; only a fresh detached verifier banks status.
- Preserve operator WIP; additive artifacts; commit only your own paths.
- Extent audit regenerated POST-commit; detached-worktree byte-identical
  verification before calling done (copy `REBUILD/files` pristine inputs).
- Exact numbers, both directions. "Byte-identical" is a measurement, never an
  impression.

## 7. Definition of done

1. The C file, the receipt with its word-diff count, the `--check` mode, and
   the test — committed.
2. Detached-worktree reproduction verified.
3. Final report in one sentence each: match or exact residual; any hand-asm
   regions and why; whether `source_closure` is now eligible for promotion.
