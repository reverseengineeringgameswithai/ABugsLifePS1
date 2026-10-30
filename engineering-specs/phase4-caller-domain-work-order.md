# Work order: interprocedural caller-domain recovery (Phase 4, F01 spearhead)

**Date issued:** 2026-08-07 · **Baseline:** commit `fc2a70875432` (verify before starting)
**Prime rule:** this order has a PILOT STAGE with a hard bail-out. Do not start
the full pass until the pilot's go/no-go record is written into the experiment
log. The 8-hour interval-prover run bought a null result that a one-hour pilot
would have delivered; this order exists to never repeat that.

## Why this is the next increment

F01's two review blockers have converged onto one obstruction. The census
blocker's remaining 9,760 unevidenced bytes and the mechanical blocker's
residuals all die at walls that reduce to *values that depend on what callers
pass in*. Current wall tally (analysis/phase4_f01_local_base_recovery.json):

| wall | sites |
|---|---:|
| blocked_index_interval_unproved_instruction | 52 |
| blocked_writer_universe_exhaustiveness | 26 |
| blocked_return_domain_unrecovered | 9 |
| blocked_no_recovery_method | 8 |
| blocked_stack_entry_value_caller_dependent | 5 |
| blocked_external_interior_entry / delta_not_uniform_positive | 2 |

Corpus-wide, 5,012 undecided stores gate the writer-universe exhaustiveness
argument. The tool this order builds attacks the caller-dependent family
directly and the writer-universe family via its prerequisite (the
caller-closure census).

## What to build

### Stage A — caller-closure census (prerequisite, standalone artifact)

For every census function, decide whether its caller set is CLOSED
(exhaustively enumerable) or OPEN, fail-closed:

- CLOSED iff: all incoming edges are direct `jal`/`j` sites in census code,
  PLUS proved indirect edges only — `phase3_jr_tables.json` and the gate
  artifact's proved jr universes, at their pinned image hashes. Nothing else.
- OPEN iff its entry address appears ANYWHERE as data outside those proved
  tables (generalize the entry-pointer-run scan from the gap-semantics probe
  into a full address-taken sweep over every data byte of every image,
  lui/addiu AND lui/ori materializations included), or any unproved indirect
  edge could reach it. An OPEN function poisons every domain that depends on
  its arguments.
- Output: `analysis/phase4_caller_closure_census.json` — exact sets both
  directions (closed list AND open list with per-function reasons), universe
  named, counts derived not asserted.

### Stage B — interprocedural domain propagation

Over the closed-caller subgraph only:

- **Argument domains** (`a0..a3` + stack-passed): at each proved call site,
  recover the argument's value set/interval with the shared analyser's
  existing bound-recovery machinery; union across all callers; propagate
  transitively to a fixpoint with an explicit widening cap (cap value pinned
  in the config, hitting it = poisoned, named).
- **Return domains**: dually, a callee's return-value domain from its return
  sites, only when every value reaching `v0`/`v1` at every return is itself
  bounded; else poisoned.
- Any poisoning propagates. A domain is either PROVED (with its derivation
  chain recorded) or absent. No confidence scores, no "likely".
- Implementation home: the shared analyser (region_provenance.c) so
  typed-state and the census both consume it — same precedent as the item-2
  bound recovery. The PILOT sample must additionally be re-derived by an
  independent minimal implementation (second-implementation cross-check
  precedent: it caught 2x count inflation once already).

### Stage C — consumption

Re-run the typed-state compiler joining the new domains; re-derive: fixture
stores decided (currently 68/238), corpus undecided stores (currently 5,012),
wall tallies. Regenerate the full chain (index → census → seed repin →
extractor → result) and report the delta against the OLD pins before
re-pinning tests intentionally.

## PILOT STAGE (mandatory, first)

- **Sample:** 20 sites, drawn as: 5 blocked_stack_entry_value_caller_dependent
  (all of them), 5 blocked_return_domain_unrecovered, 10 from
  blocked_index_interval_unproved_instruction whose index source is an
  argument register. List the 20 site IDs in the log BEFORE running.
- **Budget:** one working session (~90 min compute). No full-corpus pass, no
  fixpoint beyond depth 3, closed-caller census may be computed for the
  sample's transitive callers only.
- **GO criterion:** ≥3 of 20 sites decided with proof-grade domains AND every
  decided domain survives the capsule cross-check (all values observed in the
  50 trace capsules for those addresses lie inside the proved domain; one
  violation = soundness bug = halt and report, regardless of count).
- **NO-GO criterion:** <3 decided, or >10 of 20 poisoned specifically by
  OPEN caller sets (that means the address-taken wall dominates and the next
  increment is table-universe proving, not domain propagation). On NO-GO:
  bank the reviewed negative with per-site walls, commit, stop. That outcome
  is a valid deliverable.
- The go/no-go decision, with the per-site table, is written to the
  experiment log BEFORE any full pass begins.

## Hard-truth rules (unchanged, binding)

- Exact sets both directions; sample ≠ universe; universes named at every
  claim. A 99%-fitting model is a FAILED model. Conventions are never
  relabeled as proof (index-convention-bounded sites stay a separate count).
- Never encode an inference as a passing check. Anything undecided reports a
  NAMED wall with its falsifier class.
- Fresh-verifier discipline: F01 status/dispositions do not move in this
  order. `partial` stands; blockers may shrink numerically only via derived,
  re-pinned artifacts. Only a fresh detached verifier banks status changes.
- Pin DERIVED INPUTS, not container artifacts that pin you back (the
  receipt↔index cycle of 2026-08-07 is the named precedent).

## Hygiene (binding)

- Compiled C owns all instruction decoding/probing; Python drivers own
  repository identity and pinning (operator standing rule).
- Preserve operator WIP; no destructive git; additive artifacts; commit
  finished work per the standing authorization; extent audit regenerated
  POST-commit; detached-worktree byte-identical `--check` verification of the
  full chain (copy `REBUILD/files` pristine inputs) before calling any stage
  done.
- No instrumented replay in this order. The capsule store and the preserved
  gap-reader sessions are the only runtime evidence sources. If a live run
  ever seems necessary, STOP and report — it must be batched across rows per
  the standing batching rule, which is an operator decision.
- Do not modify `mechanics_baseline.yaml`, the movie corpus, or any pinned
  fixture. New artifacts get new names.

## Definition of done

1. Pilot record in the experiment log (site list first, then per-site
   outcomes, then the explicit GO/NO-GO sentence).
2. On GO: Stage A artifact + Stage B receipt committed with `--check` modes;
   typed-state/chain regenerated; delta table (decided stores, undecided
   corpus count, per-wall tallies, census unevidenced bytes if any
   value-domain class lands); tests green with derived re-pins; worktree
   verification; experiment log + memory surfaces updated together (a count
   that changes moves on EVERY surface).
3. On NO-GO: the reviewed negative banked to the same standard.
4. Final report states, in one sentence each: what is now decided that was
   not, what remains undecided and behind which wall, and what the next
   single highest-leverage increment is.
