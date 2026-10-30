---
kind: campaign
id: props_movers_gates
phase: 4
family: objects_events_hazards
rows: [E08_props_movers_gates]
status: active
evidence: [analysis/phase4_props_movers.json, analysis/phase4_e08_oracle_audit.json, analysis/phase4_e08_outcome_join.json, analysis/phase4_e08_operator_contacts.json, analysis/phase4_e08_hazard_outcomes.json, analysis/phase4_offline_e08_batch.json, analysis/phase4_e08_class_frontier.json]
---
# Game Solving Campaign - Props Movers Switches and Gates

## Scope and current decision

This active E08 campaign owns pass-table props, actor/source movers, native
switch/gate contacts, their authored state, outcomes, and lifecycle. It does not
absorb E01 terrain visuals, E02 collision, E11 dynamic geometry, enemy/seed
family policy, or E07 bytecode semantics.

The campaign is **not complete**. Its bounded pristine scene-1
`original_oracle` dimension is met. The static catalog, actor/source clusters
and rendering/lifecycle substrate are reproduced, but interaction rules and
persistence still intersect the row's behavior. Eight of nine dimensions
remain.

## Reproduced frontier

- a centrally pinned pristine from-boot scene-1 oracle at movie frames
  8550–8580, with mounted-media verification, 484 pass-1 rows, 140 pass-3 rows,
  64 actor slots, stable collision, and the 2,872/5,938/0 pixel paired-control
  outcomes;
- all 21 pinned staged DATs;
- 9,097 pass-1 and 1,684 pass-3 records with exact pointer-class accounting;
- pass-1 source/model handoff with a 2,872-pixel positive control;
- pass-3 bitmap suppression with a 5,938-pixel positive and a cull-preserving
  zero-pixel anchor negative;
- 64 actor records, all 41 observed actor IDs, 19 anchors and 16 scene IDs;
- 605 exact actor-to-source joins, grouped into 54 type-word behavior classes
  and 283 authored variants across 37 naturally observed VM selectors and ten
  nonzero callbacks;
- confirmed downstream ownership for seven classes carried by actor IDs 11
  (seeds), 14 (Dot), 16 (Thumper), and 36 (Thud), leaving 47 classes explicit;
- exact cross-evidence joins from all 28 A04/A06 native proximity-call
  representatives to E08 actor/source identity and E07 VM programs: 22 type
  words are controlled, including 18 of the 47 unowned classes;
- five complete existing operator movie/state replays, each inspected against
  pristine `SCUS-94288` media before load and advanced through cycle-neutral
  `movie.traceToFrame` branches: four have stable typed native outcome
  boundaries, adding type `0x060C` to the aggregate controlled frontier; the
  D11 mite lead has no stable typed actor outcome and promotes no filename role;
- eight complete E10 hazard movie/state replays across LEVEL02, LEVEL04,
  LEVEL05, LEVEL07 and LEVEL11: all eight change health or lives and retain
  cycle/RAM/register-equivalent resident plus Region-A coverage, but none has a
  stable final typed actor outcome; they add no class owner and leave the
  aggregate unowned frontier at 19 controlled / 28 uncontrolled;
- complete offline consumption of all 13 relevant retained capsules and 156
  queue queries: all 3,364 actor changes join to measured source identities;
  seven uncontrolled classes occur, five have significant frame changes, and
  `0x1B1F` knockback activations coincide with two LEVEL11 health-loss frames
  without being promoted into causality or ownership;
- an exhaustive static partition of the 28 classes without native controls:
  every class joins to one decoded VM program, authored source signatures, and
  the exact ten-function resident callback census; retained evidence partitions
  them into five significant, two timing-only, and 21 absent classes, ranking
  `0x2528`, `0x2629`, `0x050D`, `0x1B1F`, and `0x1E20` first without
  promoting a semantic owner or a frame correlation;
- a natural A05 type-`0x0109` control: accepted abdomen bounce writes actor
  response -20, increments the Bonus-1 streak, and preserves health 4; the
  equal-frame/cycle expired branch writes response 15, leaves streak 0, and
  lowers health to 3;
- focused pristine controls for `wooden_fence.sav` and
  `offering_stone_and_ramp.sav`; both are ordinary scene-1 table/actor anchors,
  so their filenames remain visual leads rather than interaction proof;
- v3 cold boot, pause/resume, and LEVEL01 -> LEVEL02 -> LEVEL01 rebuild; and
- exact parser, culler, initializer, actor-update, and pool-updater code regions.

The render branches preserve collision-sector hashes and player position. This
keeps visual control separate from collision and interaction claims.

## Open binding work

1. Assign final ownership for the 19 unowned classes with measured native
   outcomes, and obtain a native outcome control for the remaining 28,
   without guessing roles from filenames, pointers, or legacy species names.
2. Starting with ranked types `0x2528`, `0x2629`, `0x050D`, `0x1B1F`, and
   `0x1E20`, reconstruct one native trigger/writer candidate per relevant
   class; capture live only for an exact causal fact absent from the static
   VM/callback/source join.
3. Type the authored switch/gate/mover state and its capacity/initialization/
   retirement contract.
4. Replay success and denial through pause, death, checkpoint, reload, scene
   transition, and save/load; distinguish transient, checkpoint, session, and
   persistent state.
5. Add a reusable Phase-4 finding only after the interaction and persistence
   frontier no longer intersects E08 behavior.

## Guard and handoff

`tests/test_phase4_e08_oracle_audit.py` recomputes the complete bounded oracle
artifact from the retained pristine run, central movie/fixture catalogs,
closed offline receipt, derived-index join, semantic sources and raw retail
executable regions. It rejects boot, control, collision, executable, offline
boundary, and artifact-byte drift. The dimension claim promotes no adjacent
E08 predicate and no E10/D11 row.
`tests/test_phase4_props_movers.py` recomputes all static rows, source/type-word
joins, exact retained live predicates, focused controls, provenance, schema
agreement, mutation failures, and the machine-derived fact that E08 remains
open. `tests/test_phase4_e08_outcome_join.py` independently recomputes the
28-row native contact join, its 18/29 unowned-class partition, the natural
type-`0x0109` branch, and representative low-level falsification.
`tests/test_phase4_e08_operator_contacts.py` derives the aggregate 19/28
frontier from typed boundaries and cycle-neutral traces, checks the five
central fixture pairs, and falsifies low-level outcome and trace leaves.
`tests/test_phase4_e08_hazard_outcomes.py` rechecks the eight central E10 pairs,
derives player deltas and the unchanged 19/28 partition from low-level replay
boundaries, and falsifies player, trace and ownership leaves.
`tests/test_phase4_offline_e08_batch.py` revalidates the 145,510,233-byte
external index, all 13 capsule/source joins, the 156-query set, the four live
boundary cross-checks, the seven/five offline frontier, and the rule that
correlation promotes no owner or native control.
`tests/test_phase4_e08_class_frontier.py` recomputes the exact 47 = 19 + 28
partition, all 28 VM/callback/source joins, the 5/2/21 retained-evidence
partition and priority order. It falsifies duplicate/missing classes,
out-of-domain selectors, unknown callbacks, and priority-evidence drift while
requiring `complete_frontier` to remain open.
`config/phase4_props_movers.yaml` holds the typed record, contact-outcome and
MOD-safety contract; `config/phase4_e08_class_frontier.yaml` holds the bounded
static prioritization contract.

Evidence: [[EXP_2026-07-15_phase4_props_movers_catalog]] ·
[[EXP_2026-07-19_phase4_offline_e08_batch]] ·
[[EXP_2026-07-30_phase4_e08_class_frontier]] ·
Canon: [[SYS_pass_table_props_and_movers]].
