# Work order: repair `original_oracle` and `campaign_breadth` to the adjudicated bar

**Date issued:** 2026-08-10 · **Baseline:** current `master` — record `git rev-parse HEAD`
and `git status --short` (hash + line count) first; the operator WIP in that status is
**not yours**.
**Executor:** any agent; drafted for Codex hand-off, self-contained.
**Predecessor:** `engineering-specs/phase4-f01-oracle-breadth-verification-work-order.md`,
adjudicated NOT MET / NOT MET at `a35982d815f5d`, accepted at `ec4efd8e92f16`.

---

## 1. Standing

Both dimensions were rejected with **specific missing elements**, each carrying its own
`would_satisfy` sentence in `analysis/phase4_f01_oracle_breadth_verification.json`. That
verdict is the specification. **Where this document and the verdict differ, the verdict
wins** — I wrote the rejected artifacts, so my restatement is the less authoritative text.

**I am not asking you to make the dimensions pass.** I am asking you to close the named
elements where they can be closed, and to report honestly where they cannot. "NOT DONE,
because X" and "BLOCKED on an operator recording" are both good outcomes. A repair that
makes a gate pass without satisfying the element is the failure mode to avoid — three
times today a check was written that could not fail, and every one was mine.

⚠️ **Do not edit `analysis/mechanics_baseline.yaml`.** Promotion is a fresh verifier's act
after resubmission (§6), not part of repair.

⚠️ **Do not adjust `analysis/phase4_movie_priority.json`.** `test_phase4_closure_debt.py`
has one pre-existing failure — the movie-ready batch names `C15_checkpoints`, absent from
the closure-debt rows. It fails identically at `ec4efd8` and is out of scope. Do not
"fix" it by editing the selection artifact.

**Starting state (verify, don't trust):** roadmap §0 is clear as of `3d74f34` —
`phase4_closure_debt.py --write` returns `PASS: rows=16/107 dimension_met=149`, stable
across consecutive runs. Green: knowledge_closure 16/16, extent_audit 9/9, substrate
11/11, f01_source_closure 10/10. Red: the one pre-existing closure-debt test above.

## 2. Part A — harness integrity. Do this FIRST; it gates everything else

Both generators accept invalid input and report success. Until that is fixed, **no
artifact either tool produces has standing**, whatever its content.

Reproduced defects in `tools/phase4_f01_breadth_assert.py --consolidate`:

| mutation | current result | required |
|---|---|---|
| empty corpus, zero results | `law_holds_everywhere: true` | fail |
| one level, zero decisions | `law_holds_everywhere: true` | fail |
| `exec_trace_truncated: true` | ignored entirely | fail |

`tools/phase4_f01_original_oracle.py` likewise hardcodes `from_boot` rather than deriving
it, and never gates trace truncation.

**Required:** every gate fails closed, and **each one is mutation-tested** — construct the
input that should break it and prove it does. Add those mutations as committed tests, not
as a one-off script. The verdict's `fail_closed_corpus_gate` element names the specific
set: *the exact declared 19-level universe, at least one self-certified decision per
level, non-truncated traces, zero errors and zero law failures.*

## 3. Part B — `original_oracle`, three named elements

### B1 `natural_request2_skip_control` — try this before asking for a recording

The skip arm's request 2 is still injected from a save-state anchor. A natural request 2
is produced by **death** (the `a3≠0` path stores request 2 unconditionally at
`0x8004A9F4`), so any from-boot movie containing a death would supply it.

⚡ **Check the two other from-boot movies first.** The corpus holds exactly three
(`from_boot=3, state_anchored=80`): `LEVEL01_AntHill_FromBoot` (already used, request 1
only), **`D18_thud_fight.movie.json`** (15,600 frames, a boss fight) and
**`E02_FreshLoad_Clover.movie.json`** (5,562 frames). If either naturally reaches a
death, this element closes with **no new recording**. Replay them with the oracle's leaf
watches and report what the decisions show.

If neither does, this is **BLOCKED on an operator recording**: a cold-boot movie in which
Flik dies naturally. Say so plainly rather than substituting an injected control.

### B2 `fail_closed_oracle_provenance`

Derive and assert, rather than assume: the no-start-state/from-boot metadata, pristine
media identity, and non-truncation. Then **add the from-boot movie to the central
preservation manifest** — it is the one fixture in play that is not centrally pinned
(SHA-256 `b29ae839…`, 5,062,842 bytes; the 19 breadth movies and 19 anchors all are).
Mutate each property and require failure.

### B3 `fresh_detached_oracle_regeneration`

The artifact embeds the emulator's **absolute** `media.path`, so a detached checkout
regenerates `ca3fa12f…` against retained `419b229c…` — one field different, everything
semantic identical. Normalize media identity to a checkout-independent value, regenerate,
and byte-compare from a separately provisioned detached checkout.

## 4. Part C — `campaign_breadth`, four named elements

C3 (`fail_closed_corpus_gate`) and C4 (`fresh_detached_regeneration`) are Part A and the
same path-normalization as B3, applied to all 19 sources.

The two that are real work:

### C1 `preoutcome_applicability_matrix`

*"Freeze a complete applicability matrix across every required layer — stages, objectives,
enemy/actor variants, special modes, exceptional paths. Every applicable cell gets a
centrally pinned fixture plus self-certifying assertion; every inapplicable cell gets a
reproducible reason/proof; all cells classified, all applicable cells pass."*

This reframes the dimension: not "run assertions over the corpus" but **"freeze the
universe, then show coverage of it."** My pass answered the easier question. Expect the
denominators to be larger than 19.

### C2 `predeclared_level_type_mapping`

Eight types — normal, traversal-special, boss, chase, city, interior, exterior, bonus —
with at least one passing replay each.

⚠️ **The authorship hazard is the whole difficulty.** Everyone involved now knows which
levels passed, and the verdict is explicit that *"labels chosen from these outcomes would
not"* satisfy it. So the mapping must come from an **independent authority**: the row /
Canon definition, the scene table `0x80077FA0`, level structure and disc data — never from
the result set. **Freeze it in its own commit, before consulting any outcome**, so the
ancestry shows it could not have been fitted.

I deliberately did not assign these labels myself for exactly this reason. If you conclude
the mapping cannot be established independently at this remove, **say so** — that is a
legitimate finding, and it would mean this dimension needs a differently-sourced taxonomy
rather than more replays.

## 5. Hard rules

- **Replay only** via `tools/launch_repro_playback.sh --execution-mode Interpreter`;
  verify `[CPU] ExecutionMode=Interpreter` and the media serial before trusting a replay.
  The generic launcher writes no `[CPU]` section and silently desyncs.
- ⚠️ **A PC watch is an ADDRESS watch.** On a from-boot movie the EXE is absent for
  ~1,000 frames and a watch logs whatever else occupied the address — this produced 326
  phantom "finalizer" hits. Self-certify the instruction word at each watch PC. Relevant
  to B1, which is from-boot by definition.
- **Isolated instances**: fresh absolute config dir, dedicated port and token each; stop
  only PIDs owned by your own config dirs. **The operator runs their own DuckStation —
  leave it alone.** Parallelism is fine and encouraged; the wall clock is bounded by the
  longest single movie, so ~8 workers is the practical ceiling.
- **Freeze before outcomes** — baseline commit, `git status` hash/line count, and for C2
  the taxonomy itself, all committed before results are inspected. Checked by ancestry.
- Compiled C owns instruction decoding; Python owns identity and pinning.
- **Re-pinning a generated artifact:** regenerate to a **fixed point** and prove stability
  across two consecutive runs before recording a hash. A hash taken mid-settle is stale on
  arrival — that cost a wasted commit today. And `phase4_closure_debt.py` needs `--write`;
  bare it validates and prints PASS without writing.
- `analysis/phase4_extent_audit.json` enumerates **git-tracked** files: `git add` first,
  **then** refresh, then commit.
- Preserve operator WIP; commit only your own files.

## 6. Definition of done

Per element (B1–B3, C1–C4, plus Part A), exactly one of:

- **DONE** — with the evidence, and the mutation that proves the gate can fail.
- **NOT DONE** — with the missing piece named as "X would satisfy it".
- **BLOCKED** — with the exact dependency (B1 is the likely one).

Then: **do not self-promote.** Resubmission for adjudication requires a **fresh detached
verifier who did not author the repair** — the producer/verifier split that has held for
all six pilots this campaign. If Part A and B2/B3 close but B1 is blocked,
`original_oracle` is still NOT MET, and saying so is the correct result.

Report fractions before adjectives. `unknown` beats a plausible guess.
