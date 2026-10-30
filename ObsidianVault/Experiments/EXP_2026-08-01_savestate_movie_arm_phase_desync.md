---
type: experiment
status: complete
date: 2026-08-01
system: duckstation input movies
phase: platform
artifacts:
  - movies/b06_desync_test.movie.json
  - tools/rephase_movie.py
---

# Save-state movies desync by one frame from the arm phase

## Verdict

A state-anchored input movie can replay exactly **one frame out of phase** with
how it was recorded. It fails **silently**: `movie.startPlayback` still reports
`reproducible: true`, nothing errors, and the run simply drifts off-script.

Shifting the input stream **+1 frame later** corrects it. Proven objectively and
confirmed visually by the operator.

## Mechanism

`src/core/input_movie.cpp:324`:

```cpp
if (GetFrameNumber() == s_arm_frame && s_mode == Mode::Playing)
{ ApplySample(...); return; }          // reapply WITHOUT advancing
if (s_mode == Mode::Recording)
{ s_movie.frames.push_back(SampleControllers(...)); }   // falls through
```

with the author's own comments:

- :33 — *"If arming happens during the PumpMessages phase of a FrameDone (i.e. the
  system was running)… **When armed while paused, the first callback belongs to
  the next frame**."*
- :318 — *"Recording deliberately falls through: this is the input poll that drives
  its first post-state frame, **so omitting it shifts the entire movie one frame
  early on replay**."*

The compensation therefore fires only when arming happened inside a *running*
FrameDone. Record in one arm state and replay in the other and the whole stream is
off by one. `version` is not the discriminator — every movie involved is
`version=3`, so `s_play_legacy_delay_pending` (which already inserts exactly one
neutral frame, for v1) never engages.

## Evidence

`movies/b06_desync_test.movie.json` (1252 frames, state-anchored,
`reproducible_only_from_state: true`), replayed at **60 Hz** on `Interpreter`:

| variant | inv-timer writes | grant `0x800588D0` | operator |
|---|---|---|---|
| as recorded | **0** | never fires | "desynced" |
| **+1 frame later** | **401** | **fires at frame 8282, value 400** | "good result" |

The marker is objective: `0x800588D0` writing 400 to `0x800A657E` is the
invincibility grant bound in [[EXP_2026-07-31_interpreter_movies_survive_instrumentation]]
and `analysis/phase4_b06_b08_powerups.json`. It fires only in the corrected phase.

Replays are internally deterministic in both variants (two runs of each produced
identical event counts and final state), so the divergence is **recording vs
replay**, not replay vs replay.

## `movie.advanceToFrame` is not equivalent to 60 Hz playback

The same +1 movie:

| driven by | inv-timer writes | grant |
|---|---|---|
| `movie.advanceToFrame` | **0** | never |
| running at 60 Hz | **401** | fires at 8282 |

advanceToFrame does not drive frames through the same PumpMessages → input poll →
`OnFrameDone` path, so the arm-phase fixup lands differently. **Anything
phase-sensitive must be verified at 60 Hz.** This also means the instrumentation-
neutrality result in the sibling note, which was established entirely under
advanceToFrame, is scoped to that regime and has not been re-proven at 60 Hz.

## Fix — applied in the fork, movie format v4

`StartRecording` now records the arm phase and `StartPlayback` honours it, reusing
the existing one-neutral-frame mechanism:

```cpp
// StartRecording
s_movie.armed_while_paused = (System::GetState() != System::State::Running);
// StartPlayback
s_play_legacy_delay_pending = (s_movie.version < FIRST_PRIMED_VERSION) || s_movie.armed_while_paused;
```

Additive by construction: a movie with no `armed_while_paused` loads as `false`,
which is precisely the assumption every pre-v4 build already replayed it under, so
**no existing recording changes behaviour**. The flag is honoured on any version
that carries it, so a v3 file can opt in without being rewritten.

`movie.status` gained `movie_version`, `armed_while_paused` and
`phase_delay_owed` — deliberately, because the failure this prevents is silent and
a caller must be able to *see* whether the correction is in force.

Files: `src/core/input_movie.{h,cpp}`, `src/duckstation-qt/input_movie_file.cpp`,
`src/duckstation-qt/debuggerrpc.cpp`. Requires a rebuilt `duckstation-qt`, which
re-touches the Phase-3 binary pins.

### Verification on the rebuilt binary (60 Hz, `debugger.resume` + poll)

`b06_desync_test.movie.json` — the movie independently shown above to need +1 —
run twice: once untagged, once hand-tagged `armed_while_paused: true`.

| arm | `phase_delay_owed` | inv-timer writes | first grant | operator |
|---|---|---|---|---|
| untagged (as today) | false | **0** | none | "first one desynced" |
| tagged | true | **401** | **frame 8282, value 400** | "2nd one does not desync" |

The tagged run reproduces the externally-rephased run exactly, and the untagged run
reproduces today's behaviour exactly — the regression control that guarantees the
existing corpus is untouched.

### Correcting existing movies

`tools/rephase_movie.py IN OUT --tag-arm-phase` (preferred: sets the flag, frames
untouched) or `--shift +1` (rewrites the stream; works on pre-v4 builds). Neither
overwrites.

⚠️ **Do not blanket-apply either to the corpus.** Most existing movies replay
correctly as recorded — the Phase-2 oracle is 701 comparisons with 0 mismatch — so
"correcting" them would break them. Only correct a movie shown to be one frame
early.

## Related unverified bindings in the same format

The movie file records **neither** the CPU execution mode, **nor** the arm phase,
**nor** the start state's hash (`start_state.sha256` is `null` — two different
2,093,607-byte `.sav` files exist side by side in `movies/`). Three bindings that
exist but are not verified, each failing silently.

## Related

- [[EXP_2026-07-31_interpreter_movies_survive_instrumentation]]
- [[DuckStation_API_Index]]
