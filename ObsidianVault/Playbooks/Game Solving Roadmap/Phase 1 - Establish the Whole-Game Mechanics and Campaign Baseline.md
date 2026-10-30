---
kind: playbook
id: PLAYBOOK_game_solving_phase_1
name: Phase 1 - Establish the Whole-Game Mechanics and Campaign Baseline
aliases:
  - Phase 1 - Build the Original-Game Behavioral Oracle
status: complete
created: 2026-07-11
updated: 2026-07-12
confidence: high
parent: PLAYBOOK_game_solving_roadmap
previous: PLAYBOOK_game_solving_phase_0
next: PLAYBOOK_game_solving_phase_2
depends_on:
  - PLAYBOOK_game_solving_phase_0
---

# Phase 1 - Establish the Whole-Game Mechanics and Campaign Baseline

**Navigation:** [[Phase 0 - Stabilize and Establish Identity|Previous phase]] · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]] · [[Phase 2 - Build the Pristine Whole-Game Behavioral Oracle|Next phase]]

## Purpose

Bound the entire pristine game before prioritizing implementation work. Every control,
mechanic, object family, enemy, boss, collectible, objective, hazard, overlay, menu,
audio mode, and level-specific exception must appear in a tracked inventory even when
its internal implementation is unknown.

This phase prevents LEVEL01, recent regressions, or active MOD features from becoming
proxies for the game's real scope.

## Authoritative baseline

[[Whole-Game Mechanics Baseline]] is the current player-facing and engine-facing
inventory. It reconciles the retail PlayStation manual, campaign documentation, the
disc/static inventory, and current Canon. It is an audit document, not Canon; external
mechanic descriptions remain research leads until confirmed against the verified
pristine image.

## Work packages

- [x] Reconcile every retail-manual mechanic with a pristine trigger and a local status.
  — `analysis/mechanics_baseline.yaml` (machine-readable twin of the baseline note;
  every row carries status + fixture requirement + next experiment).
- [x] Complete the 15-stage plus Training/bonus objective and special-mechanic matrix.
  — Section F: 19 rows (Training, stages 1–15, 3 bonus), each with existing fixtures
  where available and a named next experiment; ratcheted by
  `tests/test_mechanics_baseline.py`.
- [x] Inventory all input actions, action combinations, camera controls, and denied
  states. — Section A: 20 rows incl. the Circle negative-control row.
- [x] Inventory all collectibles, pickups, equipment, rewards, counters, unlocks, and
  persistence paths. — Section C: 18 rows.
- [x] Inventory all seed/plant outputs, traversal aids, temporary powers, combat plants,
  and combination mechanics. — Section B: 14 rows.
- [x] Inventory all enemy families, variants, attacks, immunities, drops, respawns, and
  bosses. — Section D: 20 rows (13 manual families + 5 bosses, validator-enforced).
- [x] Inventory all hazards, movers, gates, switches, scripted objects, dynamic worlds,
  and objective actors. — Section E rows E06–E11 (hazard families enumerated in E10).
- [x] Inventory presentation and lifecycle systems: HUD, pause, results, menu, options,
  save/load, continue/game over, FMV, SFX, XA, and scene/overlay transitions.
  — Rows A18/A19, C16/C17, E12–E16 + the section-G lifecycle axes.
- [x] Bind every inventory row to known source files, functions, tables, memory, assets,
  overlays, fixtures, and explicit unknowns where available. — 78/107 rows carry
  concrete bindings; 29 rows are EXPLICIT unknowns (listed by the validator report);
  67/107 rows reference existing repo fixtures (existence test-enforced).
- [x] Identify unclassified object kinds, actor slots, overlay handlers, and asset
  families without guessing their roles. — `analysis/phase1_unclassified.json`
  (weakly-named functions 54+53 of 755 game/data fns; LEVEL.RAW chunk roles 63/69
  below full confirmation; VM 26 opcodes / 1 not fully confirmed / 12 of 13 programs
  unnoted) **plus the live censuses** `analysis/phase1_kind_actor_census.json`
  (tools/phase1_census.py, 2026-07-12, isolated instance + pristine saves):
  contact-object kinds 0..49 all enumerated with descriptors (4 Canon-bound, 46
  explicit unknown-role) and chunk-31 actor records for Training + all 15 stages
  (fixed table 0x8009FE04, stride 0x84; 456 records, 38 distinct ids — 2 Canon-bound,
  36 explicit unknown-role; record tails link into the mover-VM program region).
  Census finding: Bug Bar authors ZERO chunk-31 records even mid-Thud-fight — Thud's
  actor source is recorded as an explicit unknown (row F09).

## Baseline record schema

Every mechanic/system row must record:

- Player-facing behavior and applicable stages.
- Evidence class: retail manual, pristine observation, static code, runtime trace,
  asset/disc evidence, or secondary lead.
- Current status under the roadmap's strict Solved definition.
- Known functions, state, assets, overlays, readers, writers, and lifecycle anchors.
- Missing semantic and behavioral work.
- Required pristine movie/save fixture and expected observable behavior.
- Dependencies and cross-system interactions.

## Exit gate

- Every manual control and mechanic is represented.
- All 15 stages, Training, and known bonus stages have objective/special-mechanic rows.
- Every known regular enemy family and boss has a campaign row.
- All disc object kinds, actor/model families, and overlays are classified or explicitly
  preserved as unknown.
- Every row names a next evidence-producing experiment; no gap is hidden behind a
  generic “gameplay” or “miscellaneous” bucket.

Phase 1 does not require each row to be solved. It requires confidence that the solve
surface is complete enough that later phases cannot silently omit a major mechanic.

## Handoff to Phase 2

Phase 2 receives the complete row inventory, pristine identities, fixture requirements,
and observable behavior targets from which to build the oracle matrix.

## Progress record

| Work package | Status | Evidence |
|---|---|---|
| Machine-readable row registry | **done 2026-07-12** | `analysis/mechanics_baseline.yaml`: 107 rows (A20/B14/C18/D20/E16/F19) + 6 lifecycle axes; validated by `tools/mechanics_baseline.py` (schema, status vocabulary, campaign/family/boss coverage, fixture existence, no generic buckets); ratcheted in the safe suite by `tests/test_mechanics_baseline.py`. Suite evidence @ `cc00182` (dirty=396): `pytest tests/ -q -m "not live"` → 178 passed / 1 deselected; `pytest tests/ -q -m "not live and not local_media"` → 169 passed / 10 deselected (the two figures differ only by the marker filter — 9 tests need local media) |
| Manual mechanic inventory | done (registry) | [[Whole-Game Mechanics Baseline]] rows transcribed 1:1 with per-row `next` experiments; statuses: 70 partial / 27 unresolved / 9 external_lead / 1 not_applicable / 0 solved (strict-Solved rule test-enforced; counts from `tools/mechanics_baseline.py --report`) |
| Campaign stage inventory | done (rows) / oracle pending | Section F: Training + 15 stages + 3 bonus rows; 15/19 rows already bind existing save/movie fixtures (e.g. `LEVEL10_1-5.sav` piece states, `LEVEL08_*` performer states, boss movies) |
| Enemy/boss inventory | done (rows) / bindings partial | Section D: 13 manual families + 5 bosses; per-family variants and immunity matrix remain the named experiments |
| Object/hazard inventory | **done 2026-07-12** | E06–E11 rows; kind + actor censuses complete in `analysis/phase1_kind_actor_census.json` (kinds 0–49 with descriptors; 456 chunk-31 records / 38 ids across Training+15 stages); token-color mapping remains C11's named experiment |
| Presentation/lifecycle inventory | done (rows) | A18/A19, C16/C17, E12–E16, section-G axes |
| Unclassified-unknowns inventory | partial | `analysis/phase1_unclassified.json`: 54 placeholder-named + 53 weakly-named fns, 63/69 LEVEL.RAW chunks below full confirmation, VM 26 opcodes with 1 not fully confirmed + 12/13 programs without behavior notes (axis repaired 2026-07-12 — the earlier "10 opcodes" figure was a tool bug that measured the length of the table-address string); **complete 2026-07-12** together with the live censuses in `analysis/phase1_kind_actor_census.json` (46 unknown-role kinds + 36 unknown-role actor ids explicitly preserved) |

## Exit-gate assessment — PASSED 2026-07-12 (second pass)

- Every manual control and mechanic is a tracked registry row (validator-enforced).
- All 15 stages, Training, and the 3 bonus rows exist with fixtures/next experiments.
- Every manual enemy family and boss has a row (validator-enforced).
- All disc object kinds, actor families, and overlays are classified or explicitly
  preserved as unknown: contact kinds 0..49 enumerated (46 explicit unknowns), actor
  ids enumerated across Training+15 stages (36 explicit unknowns), overlay/function
  naming, chunk roles, and VM opcodes inventoried in `analysis/phase1_unclassified.json`.
- Every row names its next evidence-producing experiment; no generic buckets.

Live-census evidence (2026-07-12): isolated instance `/tmp/duckstation-debugger-phase1`
port 23470, fork HEAD `fe0cca16b` (dirty, 82 status lines), pristine disc verified
serial SCUS-94288 at load and per `emulator.loadState` response for each of 16 save
anchors (per-save sha256 recorded in the census JSON). Bookkeeping corrections after
external review: registry status counts fixed (27 unresolved, not 25), E06 now carries
the full kind census, the unclassified-inventory VM axis was repaired (the earlier
"10 opcodes" measured the length of the address string "0x8001b2f4"; real figures are
26 opcodes / 1 not fully confirmed, matching Canon 25/26).

Residual work moves to later phases: role-binding the 36 unknown actor ids and 46
unknown kinds (Phase 4 subsystem work, next-experiments named on rows D01/E06), and
Thud's non-chunk-31 actor source (row F09).

## Retroactive knowledge-closure audit — 2026-07-12

**Result:** the Phase-1 behavioral/inventory gate remains closed; knowledge closure is
**partial**. The 107-row registry, unclassified inventory, census generator, fixture
hashes, tests, and handoff are inventoried in
`analysis/phase0_2_knowledge_closure.yaml`. The registry validator passes with A07 now
honestly classified as an external lead rather than an absence proof.

The census is no longer orphaned analysis prose. Its runtime evidence home is
[[EXP_2026-07-12_phase1_kind_actor_census]], and its confirmed layouts/bases flow into
`config/record_types.yaml`, `config/semantic_state.yaml`,
`analysis/phase3_record_types.json`, and the corresponding validators. Confirmed
interior sites which cannot legally be function symbols are represented in
`config/confirmed_sites.yaml` and guarded by `tools/confirmed_sites.py` instead of
being inserted as false function starts.

All Phase-1/2 evidence fixtures referenced by the registry or retained artifacts are
now joined into `analysis/phase0_2_external_fixture_set.json`: 251 entries, each with
sha256, size, media class, consumers, preservation requirement, local hash check, and
generator/capture classification; zero referenced fixtures lack a central pin. The
remaining knowledge residual is the safe MOD consumption contract for the 46 unknown
contact roles, 36 unknown actor IDs, and Thud's separate source. Those remain explicit
later-phase blockers, not solved findings. Repo-wide clean-checkout closure also
inherits the four tracked→untracked source dependencies recorded by the Phase-0 audit.

Validation at audit close: mechanics registry **107 rows PASS**; focused
knowledge/Phase-1/Phase-2/Phase-3 promotion tests **65 passed**; clean archive
Phase-0..2 slice **81 passed / 4 media skips / 9 deselected**; central preservation
set **251 entries / 0 missing pins / all 251 local hashes match**; confirmed-address
promotion **86 represented / 0 missing**. Generated row coverage is 70 pristine
triggers / 37 documented blockers after the corrected A07 classification.
