---
type: experiment
status: active
date: 2026-07-19
system: Phase 4 execution methodology
phase: 4
---

# Phase 4 closure funnel

## Question

Why did the Phase 4 ratchet retain substantial pristine evidence without materially
reducing the number of open roadmap rows, and what execution policy makes later Codex,
Claude, and ratchet sessions converge on solved subsystems?

## Observation

The pre-audit machine state reported 16/107 complete rows, 91 open rows, and 2/12
complete families. Forty-two rows were labelled `offline_partial`, but that label meant
only that a retained capsule had been queried. It did not measure any of the nine
requirements in the roadmap's Definition of Done. Several consecutive iterations added
useful evidence to already-partial campaigns without promoting a row.

The prior controller also allowed `open_autonomous` to return before its clean-worktree
check, selected work from evidence availability rather than closure debt, and reserved
fresh verification for whole-phase closure/blocker claims. Existing Phase 4 live tools
mostly drove client-side replay/instrumentation loops; the current DuckStation atomic
scenario, unified provenance, capability, and capture surfaces were not an enforced
project contract.

## Decision

Phase 4 now uses a single-campaign closure funnel:

1. reuse a validated external derived index or capsule to localize the question;
2. reconstruct static owners, control flow, state, assets, and source boundaries;
3. run a small atomic live positive/negative batch only for a predeclared missing fact;
4. bank the finding into authoritative machine layers, falsifiable guards, Canon,
   Experiments, and a future-MOD consumption contract.

`analysis/phase4_offline_opportunity_queue.json` remains an evidence-availability view.
`analysis/phase4_derived_index.json` is the reusable external-index catalog.
`analysis/phase4_closure_debt.json`, generated from
`config/phase4_closure_policy.yaml`, is the only scheduler and evaluates all 107 rows
against all nine roadmap dimensions. The normal WIP limit is one campaign and three
coupled rows.

Every ratchet status must be a tested commit with a clean worktree. A row or dimension
promotion triggers a fresh campaign-scoped verifier; a periodic review runs at least
every third iteration. Two no-promotion iterations on the same campaign trigger a
method/lane change. A separate fresh verifier still owns whole-phase closure.

## Machine surfaces

- Closure policy: `config/phase4_closure_policy.yaml`
- Closure debt: `tools/phase4_closure_debt.py` →
  `analysis/phase4_closure_debt.json`
- Derived-index catalog: `tools/phase4_derived_index.py` →
  `analysis/phase4_derived_index.json`
- Atomic live-plan adapter: `tools/phase4_duckstation_batch.py`
- Bounded assertion-identity reconciler:
  `tools/phase4_reconcile_assertion_pins.py` →
  `analysis/phase4_assertion_pin_reconciliation.json`
- Controller: `tools/flik_hard_truth_ratchet.sh`
- Contract: `engineering-specs/phase4-closure.md`

The live adapter refuses a plan unless its row belongs to the selected campaign, its
escalation was declared before the run, its fixtures are centrally pinned as pristine,
and it supplies same-anchor positive/negative jobs. It checks the running debugger's
capability/schema and media identity and writes raw results outside Git.

A live plan uses schema `abl-phase4-duckstation-batch/1` and names the selected
`campaign_id`, up to three `row_ids`, current planned `escalation_ids`, exact
`expected_debugger` API/schema/source/binary identity, and `expected_media` with the
absolute pristine CUE plus every centrally pinned track. Each of its 1–128 jobs uses
`loadStateAndRun` or `bootAndRun`, one bounded `run`, optional arming-only
instrumentation, and a bounded atomic `capture`; `control_pairs` bind same-anchor,
same-duration positive and negative jobs. Run `--validate-only` before connecting.
The eventual result path must be outside the Git worktree.

The full safe-suite audit exposed a dependency cascade when the new derived-index
catalog became a declared consumer of centrally pinned movies. Retained evidence
payloads remained unchanged, but their source/fixture dependency identities—and thus
their artifact hashes—changed. `phase4_reconcile_upstream_dependencies.py` handles the
bounded payload-preserving metadata refresh; the assertion-identity reconciler then
updates only current artifact pins and SHA-valued joined leaves in the campaign and
finding registries. Its parser preserves the existing YAML representation, its guard
proves a stable no-delta rerun, and it cannot modify an ordinary behavioral expected
value. Coverage, queues, debt, inventory, and guards must be regenerated afterward.

## Residuals

- The debt ledger does not retroactively promote old partial evidence; campaigns must
  add explicit low-level dimension claims or complete their existing audited contract.
- Capsules remain frame-boundary evidence. Exact instruction, DMA, GPU, or SPU cause
  may still require a targeted live experiment.
- The adapter intentionally does not launch or kill DuckStation. The invoking session
  must follow `AGENTS.md` and the external-debugger skill for a fresh isolated instance
  and owned-PID cleanup.
- A campaign verifier establishes only its scoped promotion. It cannot declare Phase 4
  closed.

## Links

- [[Game Solving Roadmap - From Reconstruction to Reliable Modding]]
- [[Phase 4 - Solve Every Gameplay and Engine Subsystem]]
- [[EXP_2026-07-18_phase4_trace_capsules]]
