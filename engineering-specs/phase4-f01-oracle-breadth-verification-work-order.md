# Work order: adjudicate F01 `original_oracle` and `campaign_breadth`

**Date issued:** 2026-08-10 · **Baseline:** current `master` — record `git rev-parse HEAD`
and `git status --short` (hash + line count) before touching anything; the operator WIP in
that status is **not yours** and must not be committed.
**Executor:** a **fresh detached verifier**. Drafted for Codex hand-off; self-contained.
**Dimensions submitted:** F01 `original_oracle`, F01 `campaign_breadth`.

---

## 1. Standing — read this before anything else

Two dimensions have new evidence. **This document submits evidence for adjudication. It
does not request promotion, and its framing is not a conclusion.**

The author of the evidence (me) cannot promote a dimension —
[[f01-fresh-verifier-verdict]] and the roadmap both reserve that to a fresh detached
verifier. So the question in front of you is *not* "confirm this". It is:

> Does the evidence, on its own terms, meet each dimension's bar — and if not, what
> exactly is missing?

**A rejection is a fully acceptable outcome and is worth more than a soft acceptance.**
Four of the five prior pilots this campaign returned NO-GO, and each was accepted. §4
lists the places I already believe are weakest; that list is not exhaustive and is not a
promise that nothing else is wrong.

⚠️ **Do not edit `analysis/mechanics_baseline.yaml` as part of *checking*.** If you
conclude a dimension is met, the registry edit is the separate, explicit final step —
and it must be a deliberate act with its reasoning recorded, not a side effect.

## 2. What is submitted

### 2a. `original_oracle` — currently `partial` with a registered claim

**Evidence:** `analysis/phase4_f01_original_oracle.json`, produced by
`tools/phase4_f01_original_oracle.py`.
**Write-up:** [[EXP_2026-08-10_phase4_f01_original_oracle]].

The scorecard records three defects in the prior witness
(`analysis/phase4_f01_finalizer_witness.json`): the anchor is a validated save state and
not a pristine cold boot; the deciding value `2` is **injected** rather than produced by
gameplay; it covers one branch of four declared leaves. The new run claims to answer all
three: a genuine cold boot (`from_boot: true`, no start anchor), nothing injected, and all
four leaves observed while the objective completes naturally —
`consumer_proceeded 1`, `decision 1` at frame 5895 with **request 1** and
`[0x8008225C] 0`, finalizer called **28 cycles** later. 6/6 assertions pass.

### 2b. `campaign_breadth` — currently `not_met`

**Evidence:** `analysis/phase4_f01_breadth_assertions.json`, produced by
`tools/phase4_f01_breadth_assert.py` + `tools/phase4_f01_breadth_run.sh`.

19/19 levels asserted, 35 decisions, **0 law failures**, against the branch law

> finalizer `0x80045A60` runs **iff** `request != 2 && [0x8008225C] == 0`

with 19 predicted-CALL and 16 predicted-SKIP decisions, and both skip edges exercised
(13 via `beq request,2`, 3 via `bnez [0x8008225C]`).

⚠️ **Also relevant:** the scorecard note for this dimension still reads
*"LEVEL01 only, though the dispatch is campaign-wide"*. That note predates the 19-movie
sweep and is stale. Judge the dimension against the evidence, not against the note — but
note that a stale scorecard is itself a finding worth recording.

## 3. What a promotion must establish

For each dimension independently:

1. **The artifact regenerates.** Re-run the tool and diff. `original_oracle` needs a live
   replay (§5); `campaign_breadth` needs 19. If you cannot afford the replays, say so and
   scope your verdict accordingly rather than accepting on inspection alone.
2. **Every assertion can fail.** For each one, construct the mutation that should break it
   and confirm it does. This is the specific failure mode that occurred here — see §4a.
3. **The dimension's own bar is met**, as written in
   `analysis/mechanics_baseline.yaml` for `F01_anthill`, not as summarised by me.
4. **Claimed identities hold** — movie hashes, media serial, execution mode, pinned image.
5. **Nothing forbidden moved** (§5).

## 4. Where I believe this is weakest — attack here first

I found two of my own errors today, both of the same family: a check that could not fail,
and a negative that outran its evidence. Assume more of the same.

### 4a. An assertion that could not fail — already happened once, in this exact tool

The first version of the oracle asserted `finalizer_hits >= 1` against a whole-run count
of 327, of which **326 were phantom** (a PC watch on a from-boot movie logs pre-EXE-load
code at the same address). It would have passed even if the real completion had *skipped*
the finalizer. Fixed by self-certifying the instruction word at each watch PC and scoping
by cycle.

**Check that the fix is real, and that no other assertion in either artifact has the same
shape.** Both tools are small enough to read end to end.

### 4b. `CYCLE_WINDOW = 2000` is an unjustified free parameter

`tools/phase4_f01_breadth_assert.py` attributes a finalizer call to a decision if it lands
within 2,000 cycles. The observed real delta is **28**. I chose 2,000 as "generous" and
**never tested sensitivity**. Too wide and a later decision's call could be misattributed
to an earlier one; too narrow and a real call is missed and reported as a law failure.
**Re-run across a range of windows and report whether the result is stable.** If the
verdict moves with the window, the pass is not sound.

### 4c. The law's *completeness* is not proved

The law was derived from LEVEL01's bytes and the finalizer is only reachable through the
decision **as far as a direct-branch scan can see**:
`tools/phase4_f01_finalizer_entry_probe.c` found zero direct entries into
`[0x8004FF14, 0x8004FF50)` across 22 images / 260,307 words, and zero in the decoded
`analysis/phase3_jr_tables.json`. But **2,340 indirect `jr`/`jalr` sites remain
unresolved**, so "the finalizer is reachable only through this decision" is *not*
established. The artifact's `finalizer_calls_not_attributable_to_a_decision: 0` is
empirical support across 19 replays, not a proof. **Decide whether the dimension's bar
needs that closure; if it does, this fails.**

### 4d. `campaign_breadth` has NO level-type mapping — I think this is the strongest
### reason to reject it

The dimension is defined in `analysis/mechanics_baseline.yaml` as *"campaign breadth
(normal / traversal-special / boss / chase / city / interior / exterior / bonus)"*.

**My artifact contains no mapping from the 19 levels to those eight types.** I asserted
type coverage in prose and never demonstrated it. I deliberately did **not** assign the
types myself, because picking labels after the fact to make coverage come out complete
would mean choosing the thing I am verifying against.

So: either the mapping must come from the row definition's intent, or the dimension is not
demonstrated. **Your call, and "not demonstrated" is a legitimate answer.**

### 4e. An inferred API convention behind the code-3 correction

I corrected an earlier claim by concluding that the write-watch reports **store PC + 4**,
on the grounds that the recorded writer PCs `0x800496DC` / `0x800496FC` sit four bytes
after the only two stores to `0x800823A0` in that neighbourhood (`0x800496D8`,
`0x800496F8`), and that neither reported PC is itself a store. That is an inference about
the API's reporting convention, **not** a documented contract. **Confirm it against the
fork's source or a controlled experiment, or reject the code-3 conclusion that rests on
it.** The conclusion appears in Canon
([[Level_Goal_and_Exit_Trigger_Matrix]]), [[EXP_2026-08-10_phase4_e02_disc_region_code_census]],
the handoff, and memory — so if it is wrong, four surfaces are wrong.

### 4f. Scope limits I believe are correctly stated — confirm rather than assume

- Both artifacts self-declare `is_proof: false` / `promotes_*: false` /
  `requires_fresh_verifier: true`. Confirm the tools cannot emit a promotion.
- `original_oracle` rests on **one** completion of **one** level. That is the F01 row's own
  level, but a single run is a single run.
- All 19 breadth movies are **state-anchored**, so they say nothing about cold boot. Only
  the oracle movie is from-boot.

## 5. Hard rules

- **Replay only** via `tools/launch_repro_playback.sh --execution-mode Interpreter`. The
  generic debugger launcher writes a `settings.ini` with no `[CPU]` section and silently
  desyncs Interpreter-recorded movies. Verify `[CPU] ExecutionMode=Interpreter` and the
  media serial before drawing any conclusion from a replay.
- **Isolated instances only**: fresh absolute config dir, dedicated loopback port and
  token per instance. Stop only PIDs owned by your own config dirs — never a
  process-name kill. **The operator runs their own DuckStation; leave it alone.**
- **Do not touch** the analysis chain beyond the two artifacts under review: frontier,
  census, seed, gate, typed-state artifacts, and `analysis/mechanics_baseline.yaml`
  (except as the deliberate final step in §1).
- **Freeze before outcomes.** Commit a pre-outcome freeze — baseline commit, `git status`
  hash/line count, the artifact hashes you are judging, and your planned checks — before
  inspecting any result. Outcomes land in a later commit; the ordering is checked by
  ancestry.
- Compiled C owns instruction decoding; Python owns identity and pinning.
- Preserve operator WIP; commit only your own files. If a tracked tool imports a module,
  `git add` the module.
- `analysis/phase4_extent_audit.json` enumerates **git-tracked** files. If you add files:
  `git add` first, **then** refresh it, then commit — otherwise it goes stale twice.

## 6. Definition of done

A committed verdict per dimension, each one of:

- **MET** — with the evidence that satisfied every element of the bar, and the registry
  edit as an explicit separate step.
- **NOT MET** — with the exact missing element named, in the form "X would satisfy it".
- **CANNOT ADJUDICATE** — with what you were unable to run and why.

Plus, for each of §4a–§4f, a line saying whether it survived your check. And any finding
of your own that the list did not anticipate — that is the part I cannot write for you.

Report fractions before adjectives. `unknown` beats a plausible guess.
