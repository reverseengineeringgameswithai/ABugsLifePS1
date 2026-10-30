# Work order: re-adjudicate `original_oracle` — B1 is answered

**Date issued:** 2026-08-10 · **Baseline:** current `master` (`7c85a8a`) — record
`git rev-parse HEAD` and `git status --short` first; operator WIP is **not yours**.
**Executor:** a **fresh detached verifier who did not author the repair or the evidence.**
**Scope:** `original_oracle` only. `campaign_breadth` is **not** resubmitted — its C1/C2
elements remain NOT DONE and nothing has changed for them.

---

## 1. What changed since the last adjudication

`analysis/phase4_f01_oracle_breadth_repair.json` closed 5 of 8 elements and left B1
`BLOCKED` on *"a centrally pinned pristine cold-boot movie in which Flik dies naturally"*.

**That movie now exists**, and the probe accepts it:

| | |
|---|---|
| fixture | `movies/Phase4/Interpreter/F01_natural_death_FromBoot.movie.json` |
| identity | sha256 `766a7a87…`, 4,678,121 B, v4, **`from_boot: true`**, 6,840 frames |
| request writer | `0x8004A8B4` `sh v0,0x23a0(at)` → **2**, frame 6536 |
| decision | frame 6655, request **2**, `[0x8008225C]` 0 — 119 frames later |
| consumer proceeded | yes |
| **finalizer** | **not observed** |
| injection | **none** |

`element_outcome` in `analysis/phase4_f01_request2_probe.json` moved **BLOCKED → DONE**,
3/3 captures, 1 control, 0 validation errors.

⚡ The writer is the **`a3=0` health-depletion** arm, whose store is *conditional* on
health going negative — not the unconditional `a3≠0` pit store. That is the arm no
existing fixture exercised naturally, so it is stronger evidence than a pit death.

## 2. ⚠️ Four failing tests are the FIRST thing to adjudicate

I did not touch them, on purpose. **They are the acceptance criteria for the element I am
claiming to have closed**, and the first one exists precisely to stop a premature DONE.
Rewriting them as the interested party is the conflict the fresh-verifier split exists to
prevent — so the call is yours, including the call that I got this wrong.

| test | why it fails |
|---|---|
| `test_retained_pair_is_valid_and_honestly_blocked` | asserts `element_outcome == "BLOCKED"`, `captures == 2`, `controls == []`, and the key `exact_pair_replayed` |
| `test_invalid_pair_is_not_misreported_as_blocked` | pair-size arithmetic (`assert 2 == 1`) |
| `test_access_events_preserve_aliases_and_do_not_infer_overlay_images` | now iterates three retained receipts instead of two |
| `test_oracle_movie_is_centrally_pinned_without_committing_its_bytes` | pins an exact fixture entry; its `consumers` list gained `analysis/phase2_fixture_audit.json` when I regenerated the fixture audit to pin the new movie |

**Decide for each**: is this a test whose expectation was legitimately overtaken by the
work, or a test catching something I broke? The fourth is the one I am least sure about —
it is a derived-field change from *my* regeneration, not from the recording.

Whatever you conclude, the replacement assertions must still be able to fail. A test that
asserts DONE unconditionally is worse than the one it replaced.

## 3. Tool changes to review

- `EXPECTED_MOVIES` extended by one entry (the new movie). Additive.
- `consolidate()` generalized from a hardcoded pair to an **exact-set check over the
  declared candidates** — `len(receipts) == len(EXPECTED_MOVIES)`, no duplicates, exact
  set equality. Renamed `exact_pair_replayed` → `exact_set_replayed` and
  `captures_required` 2 → `len(EXPECTED_MOVIES)`.

**Check this is a generalization and not a loosening.** It should still reject a missing,
duplicated or extra receipt; confirm by mutation rather than by reading.

## 4. What to verify

1. **Regenerate.** The consolidated artifact was built from the two **verifier-retained**
   receipts inside the prior `analysis/phase4_f01_request2_probe.json` plus the new live
   one — not from fresh D18/E02 replays. If you want the whole set re-replayed, say so;
   it is ~20 minutes of Interpreter time.
2. **Re-derive the control from the image bytes.** `0x8004A8B4` must be the resident
   death store (`0xA42223A0`), and the pristine certificate in the receipt must match.
3. **Confirm the finalizer really was not called** — not merely absent from a filtered
   list. `finalizer_cycles: []` with `all_retained_events_certified: true` and **326
   pre-load events rejected**; satisfy yourself the rejection is the guard working and not
   the evidence being filtered away.
4. **The whole dimension, not just B1.** B2 and B3 were accepted previously; confirm they
   still hold after today's regenerations rather than assuming.
5. **Then rule on `original_oracle`.** If MET, the registry edit is a separate, explicit
   step with its reasoning recorded. §0 is clear (`phase4_closure_debt.py --write` returns
   `PASS: rows=16/107 dimension_met=149`, stable), so promotion is mechanically possible
   for the first time.

⚠️ The scorecard **note** still describes the injected save-state oracle and says
`campaign_breadth` is "LEVEL01 only". It is stale in three places. Judge against
artifacts; if you promote, the note needs correcting in the same deliberate step.

## 5. Hard rules

Unchanged from the prior orders, and all of them cost time today:

- Replay **only** via `tools/launch_repro_playback.sh --execution-mode Interpreter`;
  verify `[CPU] ExecutionMode=Interpreter` and the media serial first.
- ⚠️ **A PC watch is an ADDRESS watch.** On a from-boot movie the EXE is absent for
  ~1,000 frames — that is the 326 rejected events, and it is why every watch self-certifies
  its instruction word. Directly relevant here: this fixture is from-boot.
- Isolated instances, own config dir/port/token, stopped by config dir. **The operator's
  own DuckStation is off limits** — identify it by environment, never by process name.
- Freeze before outcomes; ancestry is checked.
- Re-pin only at a proven **fixed point**; `phase4_closure_debt.py` needs `--write`.
- `git add` new files **before** refreshing `analysis/phase4_extent_audit.json`.
- Do not touch `analysis/phase4_movie_priority.json` — its closure-debt test failure is
  pre-existing and out of scope.

## 6. Definition of done

- A verdict on `original_oracle`: **MET** (with the registry edit as a separate step) or
  **NOT MET** (with the missing element named as "X would satisfy it").
- A ruling on each of the four tests in §2, with replacements that can fail.
- A statement on whether §3's generalization is sound.

Report fractions before adjectives. `unknown` beats a plausible guess.
