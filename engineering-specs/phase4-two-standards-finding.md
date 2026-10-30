# Finding: Phase 4 has been running two different standards, and F01 was held to the stricter one

**Date:** 2026-08-10 · **Status:** finding, offline, from committed artifacts. Promotes
nothing, changes no status, edits no registry.

---

## The finding

**No completed Phase-4 row has per-dimension evidence.** All 16 rows recorded as 9/9 in
`analysis/phase4_closure_debt.json` carry a **single blanket `basis` string covering all
nine dimensions** — 15 rows say `"whole-campaign low-level audit"` and one says
`"reviewed-absence low-level audit"`. Not one has nine separately-evidenced dimensions.

So `9/9` on those rows is **one audit disposition replicated nine times**, not nine
measurements.

Meanwhile F01 has been assessed **dimension by dimension against named evidence**, with
individual elements adjudicated by a fresh detached verifier, and sits at 1/9.

⚠️ **These two numbers are not the same measurement and cannot be compared.** F01's 1/9
and A01's 9/9 are different instruments reporting on different things.

## The smoking gun

`E07_event_vm` is one of the 16, recorded `campaign_complete`, 9/9, basis
`"whole-campaign low-level audit"`.

The Phase-4 playbook's own status-vocabulary section quotes that same row:

> *"E07 remains partial under the strict Phase 4 nine-metric definition, but it is now
> sufficiently bounded-exhausted to move on."*
> — [[EXP_2026-08-02_phase4_e07_bounded_exhaustion]]

A row that its own experiment page calls **partial under the nine-metric definition** is
registered as **nine-of-nine met**. That is not a contradiction anyone hid — the ledger
records `bounded-exhausted` decisions as completion, which is a defensible reading of the
exit gate. But it means the ledger's `met` is a *disposition*, not a *metric*.

## Why this matters more than a bookkeeping nit

1. **F01 is not evidence that the bar is unreachable.** It is evidence that *the strict
   per-dimension reading* is unreachable — a reading the Phase-4 page has already
   corrected in writing: *"Bounded, not absent… The stricter reading came from well-earned
   caution and overshot."* F01 then spent five campaigns satisfying the overshot reading.
2. **The 16 are not evidence that the bar is reachable.** Nothing in them demonstrates a
   row clearing nine measured dimensions, so they cannot be cited as proof the standard
   is achievable.
3. ⚡ **Registering the ~56 answered-but-unregistered rows would compound this.** Running
   them through the same blanket-disposition path adds throughput without adding
   confidence; running them through F01's per-dimension path would stall them all on the
   same indirect-control-flow wall. Neither is good, and the choice between them has never
   been made explicitly.

## What the exit gate actually asks

Phase 4 exits on four bullets, of which the operative one is:

> *"No unresolved field, dispatch, asset, or overlay intersects that subsystem's behavior
> **without being explicitly bounded**."*

**Bounded, not absent.** Canonical DoD item 2 likewise says *enumerated*, scoped to
*relevant*. Both are satisfiable by an evidenced bounding argument — which is what
`bounded-exhausted` is, and what the 2026-08-10 item-2 ruling
(`engineering-specs/phase4-item2-bar-ruling.md`) applies to F01's 179-site residual.

## The reconciliation that is actually needed

Not more rows and not more F01 campaigns. **Decide, once and explicitly, which standard
Phase 4 is being measured against**, then apply it uniformly:

- If the standard is **bounded-exhaustion** (what the exit gate says, and what all 16
  completed rows actually used): F01 should be re-expressed against it, and the ~56
  answered rows can be registered honestly at a known cost per row.
- If the standard is **per-dimension measurement** (what F01 was held to): then **0 of 107
  rows have ever met it**, the 16 need re-opening, and the campaign needs to say so out
  loud rather than carrying 16 rows that would not survive the test.

Either answer is workable. What is not workable is continuing to run both at once — the
current state punishes the most rigorously examined row in the campaign and rewards the
least examined.

## What this finding does NOT claim

- It does **not** say the 16 rows' underlying research is wrong or shallow. Several are
  backed by substantial banked work.
- It does **not** say `bounded-exhausted` is a loophole. The Phase-4 page explicitly
  says it is the mechanism.
- It does **not** re-open or promote anything. Status changes remain with a fresh
  detached verifier.
