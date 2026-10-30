# Work order: per-site target-domain / exclusion proofs (Phase 4 — the last argument)

**Date issued:** 2026-08-07 · **Baseline:** commit `2a617486b30f` + the erratum
commit on the address-taken order (verify both; the address-taken receipt
`analysis/phase4_address_taken_pilot.json` is the authoritative predecessor —
read its field semantics from the receipt itself, not from any order's summary
of it; that mistake has now been made once and is documented in the erratum).

## Standing in the chain — and the stakes

Caller-domain pilot: NO-GO (OPEN caller sets). Address-taken pilot: NO-GO
(the OPEN-ness is not table-membership; the corrected code-only unproved
jr/jalr universe is the obstruction). Both receipts name the same successor,
which this order executes:

> complete per-site target-domain/exclusion proofs over the corrected
> code-only jr/jalr universe, using whole-table value-domain invariants for
> table-backed sites.

This is the **last known argument** for F01's mechanical blocker. A GO here
cascades: exclusions → closure census → caller-domain pilot (frozen 20) →
typed-state → both F01 blockers. A NO-GO here means no further technical
increment is queued — the residual goes to the operator as input to an
item-2 bar decision. Because of that, the NO-GO reporting requirements below
are stricter than in prior orders.

## The universe (derive, pin, freeze — before anything else)

The predecessor receipt's `corrected_indirect_universe_movement` gives
per-superset corrected counts (~178 code-only unproved sites per superset,
255 before masking). Stage 0 derives the exact UNION across supersets, as a
pinned ID list (image:pc:kind:register), with the masking rules applied and
cited. This union is the denominator for every claim in this order. Exact
set, both directions: sites in, and the named reason each masked site is out.

## Stage 1 — classification (mechanical, cheap, before any proof)

Classify every union site by idiom, with per-site evidence:

- `table_backed`: target loaded from an identifiable table/cell (the
  pointer-load site and region are recoverable). These are candidates for
  **whole-table value-domain invariants**: prove the VALUE SET of the table
  (every word in the proven extent is a member of an enumerated set —
  content-verified, the trig-proof tier), which bounds the site's targets
  WITHOUT an index-domain proof. ⚠️ The invariant must hold for every
  possible table state: if the table is written at runtime, its writer set
  must be accounted (this is where the recursion can reappear — record it,
  don't hide it).
- `computed`: target arithmetic from non-table inputs.
- `register_provenance`: target from a saved register / call argument.
- `return_like`: jr through a register that provably holds a return address
  (requires the proof, not the convention — a jr $ra site in this universe
  is here precisely because the CFG could not prove it).
- Anything unclassifiable: its own named class, fail-closed.

Report the stratum histogram. It is a first-class deliverable even alone:
it tells the operator what the residual is MADE OF.

## Stage 2 — per-site proofs (pilot first)

For each site, in preference order:

1. **Full target-domain proof** (gate grade): the complete target set,
   per-edge evidence, appended to the proved-jr universe via the existing
   gate machinery. Never generalized beyond the proved edge.
2. **Exclusion proof** (new, and sufficient for F01): when the full domain
   is out of reach, prove the target set CANNOT intersect the protected
   set — the F01 table-writer entries (the 58 KNOWN_WRITERS), the window
   idiom sites, and the four closure roots. A whole-table value-domain
   invariant whose value set is disjoint from the protected set is an
   exclusion proof even with the index domain unproved.
3. Neither → named wall, with the exact registers/cells where the proof
   died and whether the failure recurses through an OPEN writer universe
   (record the cycle explicitly: site → cell → writers → site).

## PILOT (mandatory, frozen first)

- **Selection (mechanical, outcome-blind):** ≤12 sites: every union site
  whose exclusion would close ≥1 of the four closure roots from the
  address-taken pilot, plus the SCUS sites whose static reachable cone
  contains a KNOWN_WRITERS member, truncated to 12 by ascending pc. Freeze
  the list + the selection query in the experiment log BEFORE Stage-2 work.
- **Budget:** one session (~2.5 h compute).
- **GO:** ≥4 of the pilot sites carry a landed proof (either kind), at
  least one of them a whole-table value-domain invariant, AND the runtime
  cross-check is clean: every capsule-observed or preserved-session-observed
  indirect target at a proven site lies inside its proved/excluded domain
  (one violation = soundness halt, regardless of count).
- **NO-GO:** ≤3 landed, or the walls recurse into OPEN writer universes for
  a majority of attempted sites.
- Independent cross-check: a second implementation re-derives the pilot
  sites' classifications and, for each landed proof, re-verifies the claim
  from the image bytes alone (2x-inflation precedent).

## NO-GO reporting (stricter than prior orders — this feeds a bar decision)

1. The stratum histogram over the full union (Stage 1 runs regardless).
2. Per attempted site: the wall, the exact cell/register chain, and the
   recursion cycle if any.
3. One paragraph, no hedging: what the item-2 bar would have to accept to
   close F01's mechanical blocker without this argument (e.g., "exclusion
   assumed for N sites whose tables are runtime-written by code inside the
   same open cycle"), and what runtime evidence exists bearing on those N
   (capsule observations, preserved sessions) WITHOUT claiming it as proof.
4. No recommendation to lower the bar — the decision is the operator's.
   State the facts that price it.

## Hard-truth + hygiene (binding, unchanged)

Exact sets both directions; universes named; conventions ≠ proof; a landed
proof cites instruction words, not plausibility; nothing inferred is encoded
as a passing check; counts move on every surface together. C owns
instruction decoding; Python owns identity/pinning; pin derived inputs
(never mutually-pinning containers). F01 status/dispositions do not move;
only a fresh detached verifier banks. Preserve operator WIP; additive
artifacts; commit finished work; extent audit POST-commit; detached-worktree
byte-identical `--check` verification with copied `REBUILD/files`. **No
instrumented replay** — capsules + preserved sessions only; live runs need
operator sign-off under the batching rule. ⚠️ Hoisted-load idiom (22 sites)
applies to every pointer-load attribution. ⚠️ Shared-handler lesson: tables
may repeat targets — occurrences, not unique values.

## Definition of done

1. Frozen union + frozen pilot list (pre-outcome), then per-site outcomes,
   then the GO/NO-GO sentence — in that order in the log.
2. On GO: proof artifacts with `--check`; gate universe additions per-edge;
   closure census delta; the caller-domain pilot re-run against its frozen
   20; typed-state + chain regen with derived re-pins; tests green;
   worktree verification; log + memory together.
3. On NO-GO: the full NO-GO report above, banked to the same standard, and
   nothing else started.
