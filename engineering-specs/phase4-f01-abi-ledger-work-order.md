# Work order: build the F01 ABI ledger (`original_interfaces`)

**Date issued:** 2026-08-10 · **Baseline:** current `master` (record
`git rev-parse HEAD` and `git status --short`; preserve operator WIP).
**Executor:** any agent (drafted for Codex hand-off; self-contained).
**Dimension:** F01 DoD `original_interfaces` — currently **not met**, reason
recorded in `analysis/mechanics_baseline.yaml` → `F01_anthill` →
`dod_scorecard`: *"no ABI ledger."* See
`ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - F01 Closure Roadmap.md`.

---

## 1. What "no ABI ledger" means and what closes it

Every other F01 dimension describes behaviour; this one describes **interfaces**.
The row cannot claim its functions are understood as *callable units* while
nothing records, per function: how arguments arrive, what they mean, what comes
back, and which registers/memory survive the call.

Deliverable is one artifact — `analysis/phase4_f01_abi_ledger.json` — with a
row per function in F01's scope giving:

- **entry / end / image / name** (from the static index; do not re-derive).
- **argument registers actually consumed** (`$a0`–`$a3`) — read-before-write at
  entry, proved by instruction, plus any **stack-passed** arguments with their
  frame offsets.
- **argument type/domain** where derivable (pointer to a known structure,
  index with a proved range, flag word, scalar) — and explicitly `unknown`
  where not. `unknown` is a valid, expected answer; a guess is not.
- **return convention**: `$v0`/`$v1` written on every return path or not;
  void-in-practice; or *no normal return* (halts / tail-jumps).
- **clobber set**: callee-saved registers (`$s0`–`$s7`, `$fp`, `$ra`) saved and
  restored with balanced frame slots vs. those left modified; caller-saved
  registers written.
- **frame size** and whether the frame is fixed or variable.
- **memory side effects at interface level**: which global/`$gp` regions the
  function writes (reuse `tools/region_provenance.c` output rather than
  recomputing).

## 2. Scope — derive it, do not invent it

F01's function scope is already pinned by existing artifacts. Take the union of:
`analysis/phase4_f01_frontier_result.json`, the F01 extents used by
`analysis/phase4_f01_typed_state.json`, and the owner functions recorded in
`analysis/phase4_f01_local_base_recovery.json`. **State the resulting count and
the exact set both directions** (in-scope list plus what each source
contributed). If the sources disagree, report the disagreement — do not silently
union away a discrepancy.

## 3. Existing machinery — connect, do not rebuild

- `analysis/phase4_f01_abi_survey.json` already answers a narrower question
  ("can argument typing decide the base register for this blocked store?") and
  carries a `groups`/`rows` structure. It is a **starting point and a
  cross-check**, not the ledger.
- `tools/phase4_typed_state.py` + `tools/region_provenance.c` own bound and
  region recovery. Consume their outputs.
- The static index owns extents, entries, and call edges.
- Compiled C owns instruction decoding (operator standing rule); the Python
  driver owns identity, pinning, and the receipt.

## 4. Honesty requirements (these are the point of the dimension)

- **Read-before-write is the test** for "this register is an argument." A
  function that writes `$a1` before reading it does not take a second argument,
  however suggestive the call sites look.
- **Call-site agreement is corroboration, not proof.** If every observed caller
  passes a small constant in `$a0`, that is a *lead* about the domain, not a
  proved range. Mark it as such.
- ⚠️ **The `$ra` finding applies here.** Verified 2026-08-10: seven `jr $ra`
  sites in the GTE/clip region jump to non-call-return targets, so `$ra` is
  used as a general-purpose jump register in this binary. Do **not** assume
  return-address discipline when classifying return convention; test it.
- ⚠️ Hoisted-load idiom (22 known sites) distorts naive read-before-write
  analysis — check for it explicitly.
- Exact sets both directions; every universe named; `unknown` preferred to a
  plausible guess; nothing inferred encoded as a passing check.

## 5. Hard rules

- **Do NOT touch the Phase-4 analysis chain**: nothing under
  `analysis/phase4_*frontier*`, the census,
  `config/phase4_f01_frontier_seed.yaml`, the gate artifacts, or the
  typed-state outputs. They pin each other by sha256 and other workstreams
  regenerate them. Your footprint: one new `analysis/` artifact, one new
  `tools/` driver (+ its C probe), one new `tests/` file.
- **Do not modify `analysis/mechanics_baseline.yaml`** or claim the dimension
  met. F01 stays `partial`; only a fresh detached verifier banks status.
- Additive artifacts; commit only your own paths; preserve operator WIP.
- Extent audit regenerated POST-commit; detached-worktree byte-identical
  `--check` verification before done (copy `REBUILD/files`).
- No instrumented replay; the runtime corpus is banked and is corroboration
  only.

## 6. Definition of done

1. `analysis/phase4_f01_abi_ledger.json` + `--check` mode + tests, committed.
2. Coverage stated as a fraction: functions in scope, functions with a complete
   ABI row, and — per field — how many rows are `unknown` and why.
3. Cross-check against `phase4_f01_abi_survey.json`: report agreements and
   **every disagreement**, since two derivations disagreeing is a finding.
4. Detached-worktree reproduction verified.
5. Final report, one sentence each: what the ledger now records; what fraction
   remains `unknown` and behind which obstruction; whether
   `original_interfaces` is eligible for promotion (a partial ledger is a
   legitimate outcome — say so plainly rather than inflating it).

⚠️ **On labelling.** The 2026-08-10 `source_closure` result was reported as an
"exact near-miss" at 3.7% word agreement. The measurement was honest; the label
was not. Report this dimension's completeness with the fraction first and the
adjective second, or omit the adjective.
