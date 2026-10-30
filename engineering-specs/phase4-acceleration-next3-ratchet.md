# Phase-4 acceleration investments 4-6 hard-truth ratchet

## Scope

Review only the exact candidate commit implementing the bounded incremental evidence
DAG, DuckStation movie/scenario minimizer, and MIPS32LE micro-execution oracle. The
accepted first acceleration tranche remains immutable. PCSX-Redux is out of scope.
No verifier may launch, edit, rebuild, copy, or kill DuckStation; this ratchet verifies
the adapter contract and synthetic pilots without a live emulator run.

## Required identities

- Record the full candidate commit, immutable first-tranche parent, dirty state, Python
  runtime, PyYAML version, pytest version, and Unicorn version.
- Provision a fresh environment from `tools/requirements.txt`; Unicorn must resolve to
  exactly 2.1.4.
- Verify `tools/build_identity.py --verify` without modifying pristine inputs.
- Run from a new detached checkout/worktree. Keep mutation copies and all transient
  movies, scenarios, receipts, reports, and caches outside Git.

## DAG acceptance

1. Recompute `analysis/phase4_evidence_dag.json` byte-for-byte.
2. Prove the six configured nodes are acyclic, output ownership is unique, every
   produced-input edge is declared, paths are repository-relative, and no live node is
   in the retained graph.
3. Mutate exact input bytes and observe direct plus conservative downstream dirtiness.
4. Mutate presentation-only JSON and prove semantic consumers stay clean while exact
   consumers invalidate.
5. Mutate a semantic value and prove semantic consumers invalidate.
6. Execute a disposable two-node graph and prove a semantic-no-op producer runs while
   its semantic descendant is dynamically pruned.
7. Reject a removed node, cycle, missing edge, duplicate owner, symlink tree, missing
   path, unsafe path, live execution without allow, and failed generator.
8. Confirm exact identities remain present beside every semantic identity and are not
   replaced by normalization.

## Minimizer acceptance

1. Recompute `analysis/phase4_movie_minimizer_pilot.json` byte-for-byte and independently
   reproduce the 12-to-2-frame synthetic reduction.
2. Prove frame deletion reindexes frames and shifts only movie-frame scenario anchors;
   emulator-frame anchors and the assertion universe are preserved.
3. Reject malformed versions, noncontiguous frames, unknown controls, invalid axes,
   duplicate assertions, source overwrite, repository output, and existing external
   output collisions.
4. Adversarially mutate every receipt obligation: DuckStation identity, exact candidate
   binding, media/binary/config/launcher/token hashes, source revision, isolated config,
   loopback/port, settings verification, runtime and movie execution modes, assertion
   and control roles/run IDs, pass/error/truncation, assertion IDs, reproducibility,
   anchor class, instrumentation re-arm, PID ownership, cleanup, and raw secrets.
5. Every cached-interpreter variant must fail. The verifier must confirm the policy and
   note state the hard rule: all movie work and every launched DuckStation instance use
   verified `Interpreter`.
6. Confirm the pilot is labeled synthetic and cannot be interpreted as runtime,
   campaign, or promotion evidence.

## MIPS-oracle acceptance

1. In the pinned environment, recompute `analysis/phase4_mips_oracle_pilot.json`
   byte-for-byte and independently run all generated cases.
2. Reproduce mask, signed comparison, 32-bit wraparound, and RAM-local load/store
   pilots with zero model mismatches.
3. Inject a wrong model and retain a smaller failing counterexample.
4. Reject engine/version/architecture drift, forbidden routine classes, excessive
   cases/instructions, unsafe allowed memory, initialization outside allowed memory,
   COP0, COP2/GTE, cache, syscall/break, MMIO, undeclared data, self-modifying code,
   control escape, and instruction-limit exhaustion.
5. Confirm no retail bytes, decompilation, RAM dump, disc, save, or movie is committed;
   all pilot code is synthetic.
6. Confirm the report states micro-execution is not behavioral authority, performs no
   campaign promotion, and still requires native DuckStation controls.

## Integration acceptance

- New generators, outputs, schemas, and tests are fully declared in the Phase-4
  inventory, with no orphan or stale declaration.
- Focused tests, retained artifact checks, inventory, vault validation, forbidden
  artifact checks, build identity, and a candidate-vs-parent safe-suite differential
  have no candidate-only failures.
- Generated downstream artifacts are refreshed in their declared order from a clean
  candidate state. No historical campaign claim, movie, scenario, DuckStation method,
  DuckStation source, fixture, or evidence receipt is changed.
- The exact candidate has no Redux path, Redux dependency, or Redux-specific branch.
- Acceptance is an external JSON using schema
  `abl-phase4-acceleration-next3-hard-truth-decision/1`, with empty `gaps` and
  `required_inputs`. Only `tools/phase4_acceleration_next_bank.py` may replace the
  pending marker and ratchet frontmatter after acceptance.
