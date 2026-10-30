# Work order: indirect-table / address-taken universe proving (Phase 4)

> **ERRATUM (2026-08-07, post-execution):** the targets table below labels the
> four witnesses as "data word[s]" holding the roots' entries. That was this
> order's misreading of the caller-domain receipt, whose witness field records
> the *first unresolved indirect transfer* (e.g. MEMORY:0x800B970C is the
> `jr $v0` at the end of frontend_state_dispatch, word 0x00400008 — an
> instruction, not a pointer cell). Stage A found 0/0/0/1 real address-taken
> occurrences and the pilot correctly returned NO-GO. See
> `analysis/phase4_address_taken_pilot.json` (`prior_receipt_witness_semantics`,
> `fixed_witness_resolution`) — the receipt, not this order, is authoritative.


**Date issued:** 2026-08-07 · **Baseline:** commit `f8d41264ff86` (verify first)
**Position in the chain:** the caller-domain pilot (receipt
`analysis/phase4_caller_domain_pilot.json`, b31b7493…) returned NO-GO with 10
of 20 sites poisoned by OPEN caller sets. This order closes those sets. Its
success re-arms the caller-domain pilot **against the same frozen 20-site
list** (built-in before/after); its failure names the wall that has final
authority over F01's mechanical blocker. Either outcome advances Phase 4:
every row's item-2 bar (enumerated universes) dies at indirect control flow
today, and this is the increment that decides whether that wall opens.

## The concrete targets (from the pilot receipt — do not re-derive, START here)

The 10 OPEN sites reduce to **four closure roots**, each with a
machine-recorded openness witness:

| closure root (function) | openness witness (where the entry escapes) |
|---|---|
| `LEVEL02_LEVEL1:0x800B3F08` | data word `MEMORY:0x800B970C` |
| `LEVEL08_LEVEL1:0x800B4084` | data word `MEMORY:0x800B970C` (same cell family) |
| `LEVEL05_LEVEL:0x800B3D80` | data word `LEVEL05_LEVEL:0x800B4228` |
| `SCUS_942_88:0x8005C58C` | data word `LEVEL03_LEVEL:0x800B4B38` (cross-image: overlay data holds a RESIDENT entry) |

Closing a root means proving, for EVERY address-taken occurrence of its
entry: (a) the complete consumer set of the containing table/cell, (b) each
consumer's index/selection domain, at gate grade — the same standard as the
proved-jr machinery. Then the root's indirect entry edges are an exact set
and its caller set is CLOSED.

## What exists — connect, don't rebuild

- `phase3_jr_tables.json`: 869 recovered indirect targets, already loaded by
  the census/index CFG (fail-closed on image hash). Use its table extents.
- The gate artifact's per-edge jr proofs: THE grade bar. ⚠️ Standing review
  ruling: **never generalize jr state propagation beyond a proved edge** —
  every table/consumer proof is per-edge, or it is not a proof.
- The gap-semantics entry-pointer-run scan + the library-partition
  materialization tracker: generalize these into the Stage-A sweep.
- E16 chunk roles: the marker space's 3 pointer-table ranges are already
  mapped from loader `0x8003A318` — reuse, cite, do not re-derive.
- ⚠️ Mover-VM lesson: table slots can SHARE a handler (8 slots →
  `0x8004C818`). Count occurrences, never just unique targets.

## Stages

### Stage A — corpus address-taken census

Every aligned word of every image (resident + all overlays at their pinned
bases, MEMORY.BIN included) whose value equals any census function entry,
PLUS every code materialization of an entry (lui/addiu AND lui/ori), PLUS a
named residual class for computed-entry arithmetic (fail-closed: anything
that COULD synthesize an entry and cannot be bounded makes the target OPEN).
Output: exact occurrence sets both directions (per-function occurrence list;
per-data-region member list). C probe owns the sweep; driver owns pinning.
False-positive model stated (a data word equal to an entry by coincidence is
possible — the consumer proof in Stage B is what converts membership into an
edge, so Stage A alone never closes anything).

### Stage B — per-table consumer + domain proofs

For each witness cell/table from the pilot four (pilot) and then each
address-taken region (full pass): enumerate every static reader of the
region (the shared analyser's resolved accesses + the jr/gate consumer
sites), prove each consumer's index/selection domain by instruction, and
prove the region's extent (the same evidence tiers as the gap-semantics
receipt: instruction-derived extent or content-verified). A region with any
unproved consumer, or a consumer with an unproved domain, leaves all its
members OPEN — named per-region walls.

### Stage C — closure verdicts + consumption

`analysis/phase4_caller_closure_census.json` (the artifact Stage A of the
caller-domain order specified): CLOSED/OPEN per function with per-function
evidence chains. Then re-run the **caller-domain pilot against the frozen
20-site list unchanged** — its GO/NO-GO criteria apply as written. Only if
THAT goes GO does the caller-domain full pass run. Chain regen + derived
re-pins as usual.

## PILOT (mandatory, first)

- **Scope:** the four closure roots above and their witness cells ONLY, plus
  whatever regions those witnesses prove to be members of. Freeze the target
  list (roots + witnesses) in the experiment log BEFORE any consumer proof
  is attempted — same freeze-before-outcomes discipline the last pilot
  honored.
- **Budget:** one session (~2 h compute).
- **GO:** ≥2 of the 4 roots CLOSED at gate grade, AND the capsule/runtime
  cross-check is clean where applicable (any runtime-observed indirect
  target or callback pointer, from the 50 capsules or the preserved
  gap-reader sessions, that falls OUTSIDE a proved-complete set is a
  soundness violation — halt and report regardless of count).
- **NO-GO:** ≤1 root closed, or the witnesses resolve to a consumer class
  that is itself unbounded (e.g., the MEMORY:0x800B970C cell is written by
  code whose own writer universe is OPEN — the recursive case). Bank the
  reviewed negative with per-root walls and the recursion depth at which it
  died. That outcome would establish that F01's mechanical blocker needs a
  different final argument (e.g., a whole-table value-domain invariant), and
  says so explicitly.
- Independent second implementation for the Stage-A sweep over the pilot
  regions (occurrence counts must match exactly; the 2x-inflation precedent
  is why).

## Hard-truth + hygiene (binding, unchanged)

Exact sets both directions; universes named; conventions ≠ proof; nothing
inferred encoded as a passing check; a count that changes moves on every
surface. C owns instruction decoding; Python owns identity/pinning. Pin
derived inputs, never mutually-pinning containers. F01 status/dispositions
do not move (`partial` stands; only a fresh detached verifier banks).
Preserve operator WIP; additive artifacts; commit finished work; extent
audit POST-commit; detached-worktree byte-identical `--check` verification
(copy `REBUILD/files`). **No instrumented replay** — capsules and preserved
sessions only; a live run requires operator sign-off under the batching
rule. ⚠️ Hoisted-load idiom (22 known sites) is a standing hazard for any
consumer-site attribution — check for it explicitly.

## Definition of done

1. Frozen pilot target record in the log (roots + witnesses, pre-outcome),
   then per-root outcome table, then the explicit GO/NO-GO sentence.
2. On GO: Stage A/B artifacts with `--check` modes; the closure census; the
   re-armed caller-domain pilot's result against the frozen 20; delta table
   (OPEN→CLOSED count, caller-domain sites decided, wall tallies, corpus
   undecided stores); tests green with derived re-pins; worktree
   verification; log + memory surfaces updated together.
3. On NO-GO: the reviewed negative to the same standard, with the recursion
   wall named and the recommended replacement argument for F01's mechanical
   blocker stated in one sentence.
