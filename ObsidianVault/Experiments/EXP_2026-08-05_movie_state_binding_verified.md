---
type: experiment
status: complete
date: 2026-08-05
system: duckstation input movies
phase: platform
artifacts:
  - tools/movie_arm.py
  - tools/backfill_movie_state_hashes.py
  - analysis/movie_state_hashes.json
---

# Movie ↔ save-state binding is now enforced at both entry points

## Verdict

A state-anchored movie can no longer replay against the wrong save state without
saying so. The binding is enforced **on recording** and **on both playback paths**.
This closes the hole described in [[EXP_2026-08-01_savestate_movie_arm_phase_desync]]'s
family of silent-failure modes: not the phase bug itself, but the neighbouring one
where the movie is fine and the *state under it* has moved.

Verified independently against the running emulator, not accepted from the
changelog. Every claim below was reproduced live.

## What was measured

| Claim | How it was tested | Result |
|---|---|---|
| Recording binds the state | recorded a 30-frame movie anchored to a state I wrote, then hashed that `.sav` **myself** with `hashlib` | movie's `sha256` == my digest (`dc5914ee…`) ✅ |
| Provenance distinguishes origin | inspected the emitted JSON | `sha256_origin: "recording"`, `sha256_provenance: "recording_start"`, `sha256_backfilled: false` ✅ |
| `startPlayback` rejects a mismatch | forged `sha256` to 64 zeros on a copy of `F16_Bonus01` | `-32006`, `mutation_performed: false`, `load_attempted: false`, `loaded: false` ✅ |
| It refuses *before* mutating | same run | `anchor_mutation_attempted: false` ✅ |
| `loadAndArm` rejects too | same forged movie | `-32006`, `failure_cleanup.phase: "start_state_hash_preflight"`, `mutation_started: false` ✅ |
| Legacy unbound movies still play | stripped the hash fields from a copy | plays; `bound: false`, `hash_present: false`, `hash_check_performed: false` ✅ |
| The 123 backfilled fixtures survived | full manifest re-check + marker audit | 123/123 keep `sha256_backfilled: true`, normalized to `sha256_origin: "backfill"`, provenance text intact ✅ |
| Save-state format untouched | `tools/rebuild_guard.py --diff` | `SAVE_STATE_VERSION` 84 unchanged, minimum unchanged ✅ |
| Existing evidence survived the rebuild | `tools/rebuild_guard.py --verify` | both oracles REPRODUCED — F16_Bonus01 (5 increments at `0x8004B3A8`, unlock flag `0x02` at frame 9923) and LEVEL10_cloverforest (mask reaches `0x1F`) ✅ |

The two provenances are deliberately **not** merged, and the distinction is the
whole point:

- `"recording"` — the digest was taken against the state the movie was *actually
  recorded on*. This is a real binding.
- `"backfill"` — the digest was taken against whatever `.sav` sat on disk on
  2026-08-05. It detects **future** drift only. It cannot show the state still
  matches the recording, because at backfill time no recording-time hash existed
  to compare with. A backfilled fixture that had *already* drifted is certified
  good by its own hash.

Anything recorded from 2026-08-05 onward is bound by construction, so
`tools/backfill_movie_state_hashes.py` should never need to run again.

## A claim of mine that this falsified

`tools/movie_arm.py` was introduced arguing that `movie.startPlayback` **does not**
verify `start_state.sha256`, making `loadAndArm` the only safe path. That is now
**false** — both paths verify. The docstring has been corrected in place and
`tests/test_movie_arm.py::test_the_retracted_startPlayback_claim_stays_dead`
guards the wrong sentence's *absence*, not just the correction's presence.

`loadAndArm` is still the right entry point, for the reason it always actually
earned: the atomic arm boundary, the post-state-load media-identity recheck, and
emulator-supplied frame coordinates. Not for the hash.

## Standing observation: anchor ≠ offset by one

At a freshly armed boundary with `phase_correction_pending: true`, the emulator
reports `anchor_emulator_frame: 9238` but `movie_to_emulator_offset: 9239`, while
its own current pair is (emulator 9238 ↔ movie 0). Subtracting the **offset** gives
movie frame −1; subtracting the **anchor** gives 0, which is what the emulator
itself says. The offset plausibly folds in the pending +1 correction.

Reproduced identically on the pre- and post-change binaries, so this is stable
behaviour rather than a regression. `movie_arm.to_movie_frame` therefore calibrates
on the reported **pair** — a fact — and `coordinate_disagreement()` surfaces the
split instead of silently choosing a field. Treating the two as interchangeable
mislabels every event by one frame.

## Scope limits

- Verification covers the **digest of the `.sav` file**. It does not establish that
  the state is *semantically* the right one for the movie, only that the bytes are
  the bytes that were bound.
- The record-time path was exercised on a short synthetic recording, not on a
  full operator-recorded fixture.
- Legacy unbound movies remain playable by design. Their reporting is via
  `bound: false` on the binding object; no `unbound_reason` string is populated.

## Related

- [[EXP_2026-08-01_savestate_movie_arm_phase_desync]] — the other silent movie failure
- [[DuckStation_API_Index]] — method surface and the current binary pins
