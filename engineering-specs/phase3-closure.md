# Phase 3 Closure — Implement/Verify Acceptance Contract

## Mission

Close **Phase 3 — Reconstruct Semantic Architecture and State Ownership** exactly as
defined by the Obsidian roadmap, then prove that closure independently. The executor
may change implementation, machine-readable knowledge, generators, evidence, tests,
and documentation. A fresh verifier must reject the result unless every criterion in
this contract is directly reproduced.

This is a focused Phase 3 closure task. It is not permission to add gameplay features,
promote ALLMODS experiments, or begin Phase 4 subsystem work.

## Authoritative requirements and interpretation order

The authoritative source is:

1. `ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md`
2. Its Phase-execution-index link:
   `ObsidianVault/Playbooks/Game Solving Roadmap/Phase 3 - Reconstruct Semantic Architecture and State Ownership.md`

The hub explicitly says it owns the decision, sequence, shared Definition of Done,
operating rule, and release gate, while the linked phase note owns Phase 3 work
packages, dependencies, progress evidence, exit gate, and handoff. Therefore both
documents are binding, with the hub controlling any conflict.

Do not treat frontmatter such as `status: complete`, a prose statement such as
`EXIT GATE — MET`, an existing JSON `gate_met`, or an old test count as evidence.
Requirements are the normative purpose, scope, work packages, resolved-ASM contract,
five exit bullets, inherited eight-part Definition of Finished, pristine authority,
and operating rules. Contradictory status prose must be corrected to match reproduced
evidence.

## Repository and operator-safety contract

- Read and follow `AGENTS.md` before acting.
- Preserve all operator work. Never reset, clean, checkout over, stash-pop into, or
  otherwise alter unrelated WIP.
- The seed branch contains a scoped WIP Phase 3 repair. Treat it as a candidate, not as
  authoritative truth. Inspect every diff and retain, revise, or supersede it based on
  evidence.
- Do not commit disc images, extracted retail assets, saves, movies, captures, BIOS
  files, tokens, credentials, or other copyrighted/operator-owned bytes.
- Put transient captures under `/tmp`. Commit hashes, manifests, generators, summaries,
  schemas, validators, tests, and notes only.
- The implementation must finish in commits on the Zeroshot worktree branch. No
  closure may depend on a dirty or untracked source file.
- Do not weaken a test, gate, fixture rule, or claim merely to obtain green output.

## Immutable pristine-media authority

The hash-verified pristine retail image is immutable and is the sole behavioral and
build authority.

- Never patch ALLMODS, another MOD image, or a prior derivative.
- Verify pristine input hashes before every build or live experiment.
- Copy pristine input to a new output and apply a selected change exactly once.
- Build each module combination independently from pristine.
- ALLMODS may be used only as historical regression/comparison evidence. It is never a
  build base and never an oracle for original behavior.
- A MOD image may prove only its intentional delta. It cannot establish a pristine-game
  fact.
- Any DuckStation experiment must use a new absolute config directory, dedicated
  loopback port and token, hash-check the mounted CUE and all referenced tracks after
  connection, inspect save-state media before loading, keep disc validation enabled,
  re-arm instrumentation after every load, and stop only the PID owned by that config.
- Cold-boot movie evidence and save-state evidence are distinct. Disc/code/asset
  changes require cold boot plus a timing-matched movie; named hash-pinned states are
  allowed only for narrow runtime questions after media validation.

The operator fixture source is `~/Downloads/ABL`. External inputs must be
provisioned into the Zeroshot worktree only after checking them against
`tools/build_baselines.json`, `analysis/phase0_2_external_fixture_set.json`,
`analysis/phase2_fixture_audit.json`, and any stricter current manifest. Missing or
mismatched inputs are a failure/blocker, never a pass. Do not commit those inputs.

## Binding Phase 3 purpose and scope

The implementation must convert byte reconstruction, static disassembly, and runtime
observations into a whole-game model of functions, state, assets, ownership, lifetimes,
interfaces, and indirect control flow for the pristine architecture—not hook design.

The closure surface includes:

- resident executable;
- both overlay regions and every level overlay;
- `MEMORY.BIN`, `FMV.BIN`, and known SDK/library boundaries;
- global, player, object, contact, enemy, camera, render, audio, frontend state;
- structs, tables, callbacks, jump tables, scripts, event programs, descriptor domains;
- asset load/fixup/ownership paths for geometry, collision, textures, models,
  animation, audio, FMV, UI, and level-specific data;
- initialization, per-frame update, render, damage, death, reset, save, unload, and
  scene-transition lifetimes.

Phase 3 does not require every Phase 4 behavior to be solved end-to-end, but it does
require the bounded semantic architecture/frontier needed for those campaigns. A
bounded frontier must name what is known, what is unknown, the owning interfaces and
state, and the exact next evidence; it must not turn an external lead into a disproof.

## Binding Phase 3 work-package acceptance

All nine work packages in the Phase 3 note must be evidenced. The verifier must build
a machine-readable coverage matrix and reject any silent omission.

1. Every Phase 1 mechanic maps to functions, state, assets, overlay, readers, writers,
   and lifecycle events, or carries an evidence-backed bounded frontier that explicitly
   names the missing link and next experiment.
2. The semantic-state registry contains the state needed by every active subsystem
   campaign in Phase 3 scope.
3. Every fixed-width native domain and every consumer of its selectors is enumerated.
4. Indirect dispatches, callback tables, VM opcodes, overlay entry points, and dynamic
   program selection are enumerated. Unresolved sites remain explicit with reasons;
   computed code jumps must not masquerade as tables.
5. Object, contact, enemy, projectile, seed, plant, player, camera, render, audio,
   objective, and frontend records are represented without erasing unknown fields.
   Every byte in a declared record is a typed field or explicit unknown span.
6. Allocation capacity, slot reuse, ownership transfer, retirement, and reset are
   mapped for the applicable owned record families. Any family not empirically closed
   must carry the explicit blocker permitted by the state-ownership exit bullet.
7. The scene/overlay/resource load and unload graph covers the Phase 3 scope, including
   off-table/exceptional paths rather than silently omitting them.
8. Machine-readable caller/callee/reader/writer and asset-provenance reports exist,
   regenerate, and cover the claimed frontier.
9. Contradictions among ASM, C, runtime evidence, asset observations, schemas,
   registries, generated artifacts, and Canon are reconciled before closure.

Unchecked boxes, a section labelled `Superseded`, or assignment to a later phase do not
waive an explicit Phase 3 work package. If the actual architecture matrix proves an
item complete with bounded unknowns, update the checkbox/progress prose. Otherwise the
phase remains open.

## Resolved-ASM boundary contract

For every original boundary later reconstruction or diagnostics need, machine-readable
evidence must cover:

- live-in/live-out registers;
- stack, `ra`, `hi/lo`, GTE and delay-slot behavior;
- displaced/original instruction effects and continuation state;
- memory reads/writes and calls;
- allocation ownership and error/early-return paths;
- selector/table domains and initialization/reset preconditions.

Resolved ASM proves bytes and control flow, not semantics. Diagnostic hook validation
is a consumer of original contracts, not a substitute for them. Every diagnostic hook
or cave counted by Phase 3 must be validated against the pristine image and the exact
hash-pinned independently built diagnostic image. Missing modules, undecoded cave
extent, undeclared clobbers, displaced-branch changes, delay hazards, or stale images
must reopen the gate.

## The five Phase 3 exit bullets — exact acceptance

The final gate must compute these predicates from retained evidence and exit nonzero
when any is false:

1. **Mechanic frontier:** every Phase 1 mechanic maps to a bounded semantic frontier,
   not merely an isolated address or guessed label. `A07_spin` may remain an
   `external_lead` only if its observed boundary and exact missing trigger/branch
   evidence are explicit. It must not be called disproven without proof.
2. **State ownership:** every original-game state used by a subsystem campaign has an
   owner, width, domain, readers/writers, initialization, reset, and overlay lifetime,
   or an explicit evidence-backed blocker. A `0 -> 0` observation does not prove
   initialization/reset. Declared or pointer-based writers must prevent immutable-ROM
   classification. MOD-private state must be kept distinct from pristine authority.
3. **Dispatch and overlays:** all indirect dispatch and overlay boundaries intersecting
   campaign mechanics are enumerated, including explicit unresolved/refused entries and
   exceptional scene routing.
4. **Continuation contracts:** diagnostic patches can preserve original continuation
   state using machine-checked contracts, proven non-vacuously against the pinned
   independently built image.
5. **Visible unknowns:** unknowns cannot silently become confirmed names or fields.
   Unknown byte accounting, refused inference, confidence, residuals, and supersession
   must remain machine-visible.

The gate must validate the decisive A07, Thud, semantic-lifetime, hook, dispatch,
overlay, record, and knowledge evidence it consumes. It is unacceptable for the gate
to report MET while the corresponding evidence guards fail.

## Inherited Definition of Finished for every confirmed finding

Every confirmed Phase 3 finding must satisfy all eight roadmap requirements. The
knowledge audit must check substance, not only file/string existence.

1. **Ground truth and provenance:** hash-verified pristine media; exact executable,
   overlay or asset identity; fixture hashes; trigger; frame/cycle; observation;
   observation/inference/causal-confirmation separation.
2. **Authoritative machine representation:** appropriate byte-exact ASM/symbols,
   matching C when achieved, typed state/struct schema, and/or mechanic/dispatch/asset/
   overlay/hook/lifecycle registry. Documentation-grade C must be labelled and cannot
   masquerade as matching source.
3. **Reproducible evidence:** smallest deterministic experiment, movie, state, trace
   summary, or static analysis; exact commands/methods and hashes; decisive evidence
   and regeneration method retained.
4. **Executable guard:** behavioral assertion, test, validator, freshness check, or an
   explicit reason and reopening experiment. Generated verdicts must be recomputed from
   low-level evidence, not trust a high-level `passes`, `bound`, `disproven`, or
   `gate_met` field.
5. **Knowledge placement and links:** original facts/provenance in Canon, runtime and
   failed hypotheses in Experiments, MOD-private state/hooks/intended deltas in Mods;
   reciprocal links to source, evidence, tests, roadmap, superseded claims, and unknowns.
6. **MOD consumption contract:** owners, readers/writers, domains,
   init/reset/retirement, continuation ABI or asset constraints, downstream consumers,
   and known unsafe assumptions.
7. **Durability and clean-checkout closure:** all non-copyrighted source, schemas,
   generators, validators and notes committed; no silent untracked dependency; every
   external fixture centrally hash-pinned, media-classified, named by its evidence and
   generator, and marked for preservation.
8. **Confidence/residual/supersession:** evidence-backed vocabulary (`confirmed`,
   `partial`, `inferred`, `disproven`, `blocked`), unresolved variants and next
   experiments, and machine-readable supersession propagated to every consumer.

If any requirement is absent, that finding and Phase 3 remain WIP/partial. The audit
must execute or independently recompute guards where practical; merely finding a test
function on disk is insufficient.

## Evidence regeneration and fixture closure

Inventory every Phase 3 generator, artifact, schema, test, note and external input.
At minimum reconcile the complete families under `tools/phase3_*.py`,
`analysis/phase3_*.json`, `tests/test_phase3_*.py`, `config/semantic_state.yaml`,
`config/record_types.yaml`, `config/phase3_findings.yaml`, `mod/hook_caves.yaml`, and
their linked Canon/Experiments/Mods notes.

For every generator:

- declare whether it is static, local-media, or live;
- enumerate every source and external fixture it opens, including indirect movie/save
  paths loaded from another artifact;
- centrally pin and media-classify all external fixtures and name their generators;
- record exact regeneration command, tool/fork revision, binary hash, config/port,
  media hash, fixture hash, trace/watch limits, pagination totals and truncation;
- regenerate the retained artifact or explicitly reject closure if required evidence
  cannot be reproduced;
- prove freshness byte-for-byte where deterministic, or compare canonical semantic
  content after excluding only explicitly justified volatile metadata;
- reject stale artifacts whose schema predates their generator or guard.

Live generators must inspect `~/duckstation` documentation/source/runtime for the
current API. The fork is dirty; record its Git revision/status and the exact running
binary SHA-256. Use `emulator.getMediaInfo`, hash the mounted CUE and tracks, and guard
against media swaps. Page logs from a paused snapshot and prove stable totals, complete
retrieval, no ring truncation, and no per-watch cap saturation.

## Known minimum discrepancies to investigate

These are observed starting failures, not the complete task and not permission to
ignore anything else the roadmap requires:

- The durable `master` state (`33e364e`) contains an overstated A07 disproof and weak
  lifetime/provenance checks. The seed includes candidate repairs from
  `ccc892c`, which must be independently verified.
- The candidate A07 and Thud generators were strengthened, but retained JSON evidence
  was not regenerated and its new guards fail.
- The semantic-lifetime live path checks only serial, not mounted-media hash, and its
  fixture declaration/knowledge contract is incomplete.
- The gate and knowledge audit can report green while decisive Phase 3 evidence tests
  fail.
- Phase 2 coverage and retroactive knowledge artifacts drift after A07 is correctly
  reclassified as an external lead.
- The Phase 3 finding registry has stale lifetime counts/residual prose.
- The hub, Phase 3 note, generated evidence and tests disagree about whether A07 is
  disproven, whether Phase 3 is complete, and whether Phase 4 may trust Phase 3.
- The Phase 3 note contains unchecked work packages and an allegedly superseded
  remaining-work list that still names render/audio/objective/frontend typing,
  lifetimes, asset provenance, caller/callee reports and overlay semantics as owed.
  Determine closure from the normative work packages and evidence, not the label.

## Required implementation order

1. Inventory and classify current claims and discrepancies.
2. Repair authoritative machine layers and generators first.
3. Re-run static/local evidence and its freshness checks.
4. Run required live pristine experiments in isolated DuckStation instances and bank
   complete evidence.
5. Strengthen guards/gates so every reproduced failure would be rejected.
6. Regenerate downstream Phase 1/2/3 consumers and fixture/source manifests.
7. Update Canon/Experiments/Mods and both roadmap notes last, from the machine truth.
8. Commit the complete scoped result.
9. Reproduce from a fresh clone plus only the declared external fixture set.
10. Have the fresh verifier rerun the contract independently. The executor's own green
    report is not acceptance.

## Mandatory validation matrix

The final branch must record exact commands, exit codes, counts and hashes. At minimum:

```bash
git diff --check
python3 tools/build_identity.py --verify
python3 tools/knowledge_closure_audit.py --write
python3 tools/phase3_knowledge_audit.py
python3 tools/phase3_gate_audit.py
python3 tools/phase3_ownership_graph.py
python3 tools/phase3_xrefs.py
python3 tools/phase3_dispatch_map.py
python3 tools/phase3_jr_tables.py
python3 tools/phase3_overlay_map.py
python3 tools/phase3_record_types.py
python3 tools/phase3_hook_contract.py
python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc
python3 tools/run_safe_tests.py
```

Also run every other generator/freshness validator discovered by the inventory,
including scene assets, transition/reset, unknown fields, camera, render descriptors,
SFX, `jalr`, function-pointer fields, semantic lifetime, A07, and Thud. Use their actual
current CLI schemas; do not invent flags. Run the relevant Phase 1/2 freshness and
oracle checks affected by changed mechanics or evidence.

The pinned code-only build must reproduce the declared output hashes or the authoritative
manifest must be updated only after proving why a legitimate deterministic change was
required. Hook/cave validation must run against that exact output.

## Clean-checkout proof

Closure requires a newly created clone/archive of the final commit, not the executor's
dirty worktree. Provision only the centrally declared external fixture set from the
operator root, verify every byte before use, and record the exact preservation set.

From that clean checkout:

- build the pinned diagnostic image from pristine and reproduce its hashes;
- regenerate all static/local evidence;
- rerun the safe suite, fixture/source/freshness validators, knowledge audit, five-bullet
  gate and hook/cave checks;
- rerun required live evidence or, where the roadmap permits retained live evidence,
  prove that the committed artifact, generator, fixture set and executable guard are
  sufficient to reproduce it exactly;
- prove no tracked source imports or opens an undeclared/untracked dependency;
- prove `git status --short` is clean after deterministic regeneration, excluding only
  ignored external copyrighted fixtures and transient `/tmp` evidence.

No criterion may pass because a fixture is absent, a test is skipped unexpectedly, a
local-only artifact happens to exist in another worktree, or a summary boolean says it
passed.

## Documentation and final status

Update machine truth first, then reconcile:

- the roadmap hub Phase 3 row and Phase 4 dependency row;
- the linked Phase 3 note, checkboxes, progress/evidence, exit gate and handoff;
- `config/phase3_findings.yaml` and all generated consumers;
- linked Canon, Experiments and Mods notes;
- superseded claims, confidence, blockers, exact validation results, clean-checkout
  fixture requirements and remaining bounded unknowns.

Do not claim the game, a Phase 4 subsystem, or all Phase 3 findings are solved. Claim
only the exact Phase 3 architectural closure reproduced by the contract.

## Independent verifier rejection rules

The fresh verifier must inspect raw evidence and independently execute the validation
matrix. It must reject the implementation if any of the following is true:

- any normative roadmap scope/work-package/exit/Finished requirement is omitted;
- pristine media, exact mounted path/tracks, fixture, fork or binary identity is absent
  or mismatched;
- an external dependency is missing, unpinned, misclassified or silently imported;
- a required artifact is stale, non-regenerable, hand-edited, or stronger than its
  retained evidence;
- a high-level verdict is trusted without recomputation;
- gate/knowledge status is green while a consumed guard or freshness test fails;
- A07 is called disproven despite only bounded-negative evidence;
- unknown state/lifetime/dispatch/record data is converted into a confirmed claim;
- tests are weakened, deleted, skipped, or reinterpreted to avoid a failure;
- the clean checkout cannot reproduce with the declared fixture set;
- documentation contradicts machine layers or validation;
- required source/evidence remains uncommitted or the final branch is dirty.

There is no partial acceptance. On failure, return concrete evidence to the executor,
iterate, and verify again with a fresh verifier. Phase 3 is closed only when every item
above is directly reproduced.
