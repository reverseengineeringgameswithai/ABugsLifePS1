---
kind: experiment
id: EXP_2026_07_14_phase4_ratchet_iteration1_machine_gate
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
related:
  - PLAYBOOK_game_solving_phase_4
  - PLAYBOOK_game_solving_roadmap
  - SYS_phase3_semantic_architecture_frontier
---

# Phase 4 ratchet iteration 1 — exhaustive campaign registry and fail-closed gate

## Trigger and placement

Phase 4 began with no campaign registry, evidence inventory, scorecard generator, or
whole-phase executable gate. Existing `partial` prose and prior phase summaries could
not establish any Phase-4 exit predicate. This iteration builds the framework and
records its falsification result. It does not add an original-game fact, so the note
belongs in Experiments rather than Canon. It adds no MOD-private state or intended
delta, so no Mods note is applicable.

## Inputs and upstream reproduction

The acceptance contract SHA-256 is
`1d0d15387b2692145cf1668f4d0e8f9cc783c0c8bb2df1eaebb4bc4776541729`,
matching its adjacent pin. The clean seed initially lacked declared external inputs;
the first low-level `phase3_gate_audit.py` run therefore exited 1 on upstream
durability while its coverage and decisive-evidence predicates remained MET.

`tools/provision_clean_checkout_inputs.py` copied exactly 1,262 centrally declared,
hash-verified inputs from `~/Downloads/ABL`: three pristine-media files, 327
pristine staged inputs, 63 non-pristine comparison fixtures, 127 strict-pristine
fixtures, 63 pristine-serial movies, 651 derived-retail assembly files, three
derived-retail disassemblies, and 25 derived-retail metadata files. No provisioned
bytes are tracked. `tools/build_identity.py --verify` then matched 327/327 staged
inputs, and the recomputed Phase-3 gate exited 0 with all low-level predicates MET.

No Phase-4 DuckStation session was run. The binding implementation order requires the
machine registry and falsifiable gate before substantive campaigns; no runtime claim
was made that would justify launching an emulator. Future live campaigns must use a
fresh absolute config, unique port and token, mounted-media hash verification, current
source/binary/capability identity, and config-owned PID cleanup.

## Machine representation

`config/phase4_campaigns.yaml` assigns every authoritative row exactly once to one of
the twelve families and records dependency-only overlaps separately. Child campaigns
and absence proofs are empty until actual work begins. `config/phase4_findings.yaml`
is likewise empty rather than manufacturing reusable findings.

The retained generators are:

- `analysis/phase4_priority.json` — centrality/gap-derived ordering;
- `analysis/phase4_coverage_matrix.json` — 107-row and twelve-family scorecard plus
  six work-package predicates;
- `analysis/phase4_fixture_audit.json` — central pin, media class, current-byte, and
  Phase-2 trigger/blocker join;
- `analysis/phase4_knowledge_audit.json` — child/finding/vault/handoff audit;
- `analysis/phase4_campaign_inventory.json` — campaign, row, frontier, source,
  decompilation, fixture, generator, artifact, test, schema, note, finding, and
  downstream-consumer inventory;
- `analysis/phase4_gate.json` — exact four exit predicates and global prerequisites.

The gate evaluates exact JSON leaves with artifact SHA-256 pins. Evidence paths whose
segments are `passes`, `complete`, `solved`, `status`, `met`, `gate_met`,
`overall_met`, `closure_ready`, `verified`, or `success` are rejected as
self-certification.

## Observation, inference, and bounded conclusion

Observation: the authoritative registry contains 107 rows. The derived owner map has
107 unique entries across all twelve families. Priority WP1 is MET. With no child
campaigns or reviewed absence proofs, coverage is 0/107 rows and 0/12 families; WP2
through WP6 and all four exit predicates are OPEN.

Inference: Phase 3 supplies a durable architecture frontier and enough pristine
fixtures to prioritize campaigns, but it is not evidence that any subsystem satisfies
Phase 4's stricter behavior, lifecycle, breadth, source, and consumption contract.

Bounded conclusion: only the Phase-4 machine/falsification layer and work package 1
are complete. Every subsystem campaign remains future autonomous work. A20's inherited
`not_applicable` label is deliberately still OPEN because Phase 4 has not yet banked a
reviewed pristine-absence proof.

## Falsification

The tests remove A01's owner, duplicate A01 into a second family, inject a campaign
whose only evidence is `passes=true`, `complete=true`, and `gate_met=true`, and point
an assertion at Phase 3's high-level `gate_met` leaf. The registry rejects both owner
mutations, the self-certified campaign covers zero rows, and the evidence evaluator
rejects the summary leaf. The unmodified whole-phase gate remains nonzero and reports
all four predicates OPEN.

## Reproduction commands

```text
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL
python3 tools/build_identity.py --verify
python3 tools/phase3_gate_audit.py
python3 tools/phase4_priority.py
python3 tools/phase4_coverage.py
python3 tools/phase4_inventory.py
python3 tools/phase4_gate.py
python3 -m pytest -q tests/test_phase4_registry.py tests/test_phase4_gate.py
```

The Phase-4 coverage and gate commands are expected to exit 1 until their retained
low-level predicates become true; tests assert that this red state is accurate.

## Links and next experiment

Roadmap ownership: [[Game Solving Roadmap - From Reconstruction to Reliable Modding]]
and [[Phase 4 - Solve Every Gameplay and Engine Subsystem]]. The next campaign is the
highest-ranked core input/player-action surface. It must create a child note only when
work begins, select strict-pristine cold-boot controls, enumerate its full semantic
frontier and lifecycle, and bank low-level assertions before any row can become solved.
