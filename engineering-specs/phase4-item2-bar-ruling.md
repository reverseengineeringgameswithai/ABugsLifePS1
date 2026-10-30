# Ruling: the item-2 bar for F01 — accept the enumerated residual, bounded

**Date:** 2026-08-10 · **Decided by:** the assistant, on the operator's instruction that
this call is mine to make. **Status:** a ruling on the *bar*, not a promotion. It does not
move any dimension and does not touch `analysis/mechanics_baseline.yaml`.

---

## The decision

**Accept the enumerated 179-site indirect-control-flow residual as a declared assumption
on F01**, rather than hold strict and leave the row permanently `partial`.

The roadmap (§3) framed this as the choice that decides whether F01 can close at all.
Five `complete_frontier` avenues are spent, all four D3 walls are technique-shaped but
funded only behind a **new prerequisite engine** — region-sensitive alias closure,
field-sensitive object typing, a global ingress contract, or a loader/residency contract.
None is a campaign; each is a project.

## Why accept

1. **The residual is enumerated, not unknown.** 179 named sites with classifications is a
   categorically different object from "unknown unknowns". A declared assumption over a
   closed, listed set is auditable; anyone can later attack any member of it.
2. **The evidence is unusually strong for a negative.** ~200 replays across the full 100%
   corpus and the behaviour library, **zero** observed dispatch into F01's protected set,
   100 of 179 sites silent through any%, the behaviour library, and full 100% completion.
3. **Five independent failures with a consistent shape.** Caller-domain, address-taken,
   target-exclusion, D1/D2 discipline, and D3 contracts all NO-GO'd, each naming a
   technique wall rather than a structural impossibility. That consistency is itself
   evidence that the remaining work is engine-building, not proof-finding.
4. **The cost of holding strict is the whole roadmap, not one row.** F01 is the template
   row. If the most heavily evidenced row in the campaign cannot close, no row can, and
   the 106 others inherit a bar nothing has ever cleared.

## Why this is not a weakening

The acceptance is **bounded**, and the boundary is the point.

- It covers **exactly** the 179 sites enumerated in
  `analysis/phase4_f01_jr_tuple_capture.json`. Not "indirect control flow" in general.
- It is recorded as an **assumption**, never as proof. The row must say *unproved,
  observed-clean across N replays*, with N stated.
- ⚠️ **It is void on a single counter-example.** If any of the 179 is shown to reach the
  protected set — statically or at runtime — the acceptance lapses and the row reopens.
  There is precedent for exactly this: `0x80018CBC`'s "exact" three-target domain missed
  its dominant target and was falsified by runtime. That falsification is *why* the
  assumption must be phrased as observation, and why it must carry a kill switch.
- It does **not** transfer. Other rows blocked by the same sites must make their own case;
  a declared assumption on F01 is not a precedent for F02.

## What it does not do

It does not promote `complete_frontier`, or `typed_state`, or the semantic half of
`original_interfaces`. Those remain gated on the same machinery, and this ruling does not
pretend otherwise — it removes the *bar* as the obstacle, not the *work*.

⚡ **It also does not fund a sixth frontier campaign.** D3's own words: *"another
target-enumeration campaign using the current machinery is not funded by this result."*
Accepting the residual is the alternative to that campaign, not a warm-up for it.

## Sharpening from 2026-08-10

A compiled-C scan over the exact 22-image / 143,060-word universe finds **1,246**
unresolved `jr`/`jalr` occurrences. (An earlier figure of 2,340/260,307 was mine and
double-counted the resident executable; corrected by the verifier.) The corrected number
does not change the ruling — it confirms that exclusive reachability is unprovable by
current means, which is the condition the ruling exists to resolve.

The same wall showed up in a second place today: the finalizer branch law holds on 35/35
observed decisions across all 19 levels and **cannot be proved exclusive**, because a
direct-branch scan cannot resolve those 1,246 occurrences. Two independent encounters with
one wall, in one day, is the pattern that makes "build a new engine first" the wrong next
move.

## What still is not mine

Registry promotion remains with a **fresh detached verifier**. That is not deference — it
is the discipline working. I authored the evidence under review, and today alone I wrote
three checks that could not fail and one census that double-counted. The split exists for
authors like me.
