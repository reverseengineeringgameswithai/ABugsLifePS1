# Phase 4 Acceleration Tooling Ratchet

## Objective

Implement and independently verify the tooling tranche defined by
`ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Acceleration Tooling Strategy.md`:

1. the Static Frontier Compiler;
2. the overlay semantic index; and
3. the promotion-packet preflight linter.

The terminal claim is production tooling readiness for the current corpus and the
E15/E08/C13 proof pilots. It is not Phase-4 closure, row/dimension promotion, the
all-row rollout, PCSX-Redux migration, or any DuckStation method-universe change.

## Immutable seed and work boundary

- Seed commit: `dbab87c1c2bfe87ae2cb7ffe222ee2b87f745f8b`.
- Work occurs on one isolated `ratchet/phase4-acceleration-*` branch and worktree.
- The operator checkout and every unrelated worktree are read-only inputs.
- The ratchet never merges, pushes, resets, cleans, stashes, or overwrites operator
  work.
- All pristine media and derived retail sources are external, centrally declared,
  hash-verified inputs. They are never committed.
- The DuckStation fork, APIs, fixtures, scenarios, tests, evidence contracts, and
  operating method are read-only and explicitly outside this tranche.

## Required implementation surface

### Strategy and knowledge

- The acceleration note contains the complete diagnosis, all proposed investments,
  implementation/deferred decisions, official references, operating rules, metrics,
  residuals, and hard-truth marker.
- The Phase-4 execution note links reciprocally to it.
- Before acceptance the note remains `status: candidate` and
  `acceleration_ratchet: pending`.

### Static frontier compiler

- A headless Ghidra exporter consumes canonical function specifications and emits raw
  high/instruction p-code outside Git.
- A deterministic Python normalizer joins canonical census, image identity, symbols,
  source status, calls, memory accesses, state/record schemas, and target declarations.
- The tracked index covers every resident census record and every current overlay code
  function exactly once. Data records are explicit non-code records.
- Code/thunk records expose blocks, direct/indirect calls, returns, memory expressions,
  access widths, signed-operation evidence, state/type joins, exact/structural
  fingerprints, analysis method, and unresolved boundaries.
- No silent omission, depth-limited closure, automatic semantic owner, or authored
  success boolean is accepted.
- Raw p-code, decompiled C, Ghidra projects, and retail bytes remain external.

### Overlay semantic index

- All Region-A level overlays and Region-B MEMORY code functions are represented with
  their correct file hash, base, `$gp`, header rule, extents, and unique image identity.
- The current seed's 158 overlay code functions appear exactly once.
- Same-VA functions in different overlays remain distinct.
- Exact and structural clusters are separate and explicitly non-promoting.
- FMV is supported as an additional Region-B module for the E15 benchmark without
  conflating MEMORY lifetime.

### Proof pilots

- E15 reproduces the 30 declared Region-B rows, 99 exact xrefs, and 58 player-boundary
  xrefs, or the candidate provides and guards every independently accepted difference.
- E08 joins 28 uncontrolled classes, 40 selectors, and ten callbacks and produces the
  five bounded priority slices with zero automatic owner/dimension promotions.
- C13 binds retained grain/harvester roots and reports every retained open boundary
  without promoting a row/dimension.

### Promotion preflight

- The input and output schemas are versioned and documented.
- Common and dimension-specific obligations are derived from current Phase-4 policy.
- Current debt/source/artifact/external hashes and tracked paths are recomputed.
- Missing layers require explicit `not_applicable` reasons.
- Residuals, clean-checkout dependencies, and a disposable falsifier are mandatory.
- The tool's maximum positive is `ready_for_fresh_verifier`; it never edits the
  campaign registry or debt ledger.
- Stable mutation guards cover stale debt, missing/widened frontier, writer/signedness
  drift, untracked paths, missing knowledge, intersecting residuals, bad hashes, and
  fake success fields.

## Implementer obligations

Each implementation round must:

1. read this contract, the immutable plan snapshot, the current candidate, progress
   ledger, and preceding verifier gaps;
2. preserve interrupted scoped work and avoid repeating verified work;
3. implement the highest-leverage remaining contract gap;
4. update low-level code/config/schema before generated artifacts and prose;
5. add positive, negative, mutation, determinism, and clean-checkout tests;
6. verify pristine inputs before consuming them;
7. commit only scoped non-copyrighted work and leave the implementation worktree clean;
8. return the exact tested commit, commands/results, claims, and residuals; and
9. never weaken a test, count, policy, or benchmark to obtain green output.

## Fresh hard-truth verifier obligations

A fresh verifier that did not implement the candidate must use a detached checkout and
assume the claim is false. It must:

- inspect actual Java/Python logic, schemas, configs, indexes, and tests rather than
  trusting notes or top-level `valid` fields;
- provision and hash-verify only centrally declared external inputs;
- regenerate the full index twice in separate temporary Ghidra projects and compare
  normalized bytes;
- independently reconcile census cardinality, image/base/`$gp` identity, function
  extents, E15 xrefs, E08 joins, and C13 residuals;
- introduce representative corruptions for every rejection family;
- verify raw/decompiled/copyrighted payloads did not enter Git;
- run focused, vault, generated-artifact, and clean-checkout checks, plus an exact
  immutable-seed-versus-candidate differential for the broader safe suite;
- reject every candidate-only safe-suite failure, while reporting inherited failures
  without changing the out-of-scope subsystem that owns them;
- leave its detached HEAD and status unchanged; and
- return `accepted` only with no gap and no required input.

`rejected` requires exact reproducible gaps. `blocked_external` requires an exact input
that cannot be generated, recovered, or centrally provisioned. Tool crashes,
permission failures, timeouts, dirty trees, missing tests, or incomplete runs are not
acceptance.

## Acceptance gate

The tooling tranche is accepted only when all of the following are true:

1. The candidate implementation branch is committed and clean.
2. `tools/build_identity.py --verify` passes all 327 pristine staged inputs.
3. Every current resident record and overlay code function is present exactly once,
   with zero fatal analysis errors.
4. Two fresh full regenerations are byte-identical after normalization.
5. The E15 benchmark is exact or every difference is independently explained and
   mutation-guarded.
6. E08 and C13 application reports meet their non-promotion boundaries.
7. Valid promotion packets pass; every declared mutation fails with its stable code.
8. The scoped acceleration, local-media, vault, inventory, and clean-checkout checks
   pass. The broader safe suite is regression-neutral against the immutable seed:
   every candidate failure must reproduce at the seed and no new failure is accepted.
   Existing DuckStation external-debugger identity drift and pre-existing absolute-
   home-path portability failures are disclosed inherited facts, not greenwashed and
   not repaired by this tranche.
9. No prohibited external or copyrighted content is committed.
10. A fresh verifier returns `accepted`, `gaps=[]`, and an empty required-input field
    for the exact candidate commit.

## Deterministic banking

After hard-truth acceptance, `tools/phase4_acceleration_bank.py` may change only the
acceleration note's `status`, `acceleration_ratchet`, and verdict marker. It embeds the
run ID, reviewed commit, verification time, conclusion, and verifier-decision SHA-256.
The controller then reruns focused tests and vault validation, verifies the bank-only
diff boundary, commits it, and leaves the worktree clean.

The ratchet never merges or pushes. The final handoff reports the branch, banked
commit, verifier decision, validation commands, and any non-intersecting residuals.
