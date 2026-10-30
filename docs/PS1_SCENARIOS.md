# DuckStation scenario operator guide

`tools/run_ps1_scenario.py` turns a stable PS1 reproduction into a small YAML
behavioral test. It reuses the fork's Python client and the repository's proven
cold-boot launcher; it does not use the operator's normal DuckStation profile.

## Quick start

```bash
python3 tools/run_ps1_scenario.py \
  tools/scenarios/duckstation/training_pause_resume.yaml --validate-only

python3 tools/run_ps1_scenario.py \
  tools/scenarios/duckstation/training_pause_resume.yaml \
  --disc build/ABL_FRAMEWORK_FINAL.cue \
  --output-dir /tmp/abl-training-pause

python3 tools/run_ps1_suite.py \
  --disc build/ABL_FRAMEWORK_FINAL.cue \
  --output-dir /tmp/abl-ps1-suite

python3 tools/run_ps1_suite.py \
  --suite tools/scenarios/duckstation/bonus_unlock_suite.json \
  --disc "Disney-Pixar A Bug's Life (v1.0).cue" \
  --output-dir /tmp/abl-pristine-bonus-suite
```

Each run creates a unique `/tmp/abl-ps1-scenario-*` config, loopback port, random
token, runtime directory, and PID file. The token is hashed/redacted in reports.
Cleanup clears instrumentation/input and asks the fork launcher to stop only the
PID owned by that config directory. A cleanup failure makes the run an error.

## Scenario anatomy

A scenario declares:

- `target`: disc path and expected serial. `--disc` safely overrides the path for
  a freshly rebuilt image.
- `launch.profile`: `repro` uses `tools/launch_repro_playback.sh` (full boot,
  CachedInterpreter, seeded isolated card) for the existing from-boot movies;
  `generic` uses the fork launcher and fast boot.
- `playback`: input movie, start frame, anchor-load behavior, and whether
  `movie.status.reproducible` is mandatory. A scenario may instead declare a named
  `anchor: {type: save_state, path: ...}`; state metadata and disc identity are
  checked before load and instrumentation is armed afterward.
  Historical from-boot movies whose input was attached after a known running-guest
  delay can set `pause_before_start: true` plus `preplay_neutral_frames: N`; this
  makes that delay emulated-frame-exact instead of dependent on host RPC timing.
- `phases`: ordered `before` actions, one trigger, captures, behavioral assertions,
  and `after` actions.

The checked-in format reference is `tools/ps1_scenario_schema.json`. Runtime
validation is intentionally stricter where a malformed declaration would weaken
evidence.

## Triggers

| Type | Purpose |
|---|---|
| `movie_frame` | Cycle-neutral server-side advance to an absolute movie frame. |
| `emulator_frame` | Advance to an absolute emulator frame. |
| `memory`, `register`, `pc` | `emulator.advanceUntil` predicates including changed/stable. |
| `breakpoint` | Execute/read/write breakpoint with optional condition and deferred actions. |
| `gpu`, `audio`, `rpc_poll` | Poll an RPC result path between bounded frame steps. GPU methods must use `gpu.*`; audio uses `spu.*`. |

For deep movies, advance cleanly to a nearby movie frame before arming traces or
breakpoints. Instrumenting at boot can alter input/CD timing even when the movie
still reports `reproducible:true`.

## Actions and evidence

Typed actions cover conditional breakpoints, access and execute watches, function tracing,
SPU tracing, GPU causality, and `trace.armWhen`. `type: rpc` is the extension point
for any verified fork method without changing the runner. Captures support:

- `capture.atomic` for coherent CPU/RAM/GPU/movie/SPU evidence;
- arbitrary RPC results;
- in-memory frame snapshots for later render diffs;
- screenshots written only inside the run's temporary evidence directory and
  recorded by path/hash.

Assertions support typed RAM/register reads, function/access/exec hit counts,
arbitrary RPC or capture-result paths, and `gpu.diffCurrentFrame` changed-pixel
metrics. Operators should assert behavior or semantic state, not patched bytes.
Use `--expect assertion_id=value` to exercise a known failure without editing a
scenario.

## Reports and debugging

Every run emits `<scenario>.json` and `<scenario>.md`. The machine report contains
repository/fork revisions and dirty summaries, debugger/disc/movie hashes, media
identity, config/port/PID ownership, exact trigger results, actual/expected values,
trace truncation where returned, evidence paths, and cleanup outcome.

When a run fails:

1. Confirm serial/path/hash and `reproducible:true`.
2. Check the phase's actual movie/emulator frame and whether a trigger reached its
   condition or exhausted `max_frames`.
3. Narrow instrumentation to immediately before the divergence.
4. Add an atomic capture, screenshot, access trace, or function trace via the phase;
   keep the new evidence under `/tmp`.
5. Once causal, keep the smallest assertion that would have caught the regression.

## Fixture policy and current replacements

Movies and saves are owner-local and hash-pinned in `tools/fixtures.sha256`; their
bytes remain ignored. Two older v2 berry recordings (`red_berry_enemy_test` and
`killing_spider`) no longer followed their intended behavior on the current
reflowed build (one entered a BIOS exception path; the other missed its throw
window). The suite therefore reuses current v3 Training/LEVEL01 movies. The real
Blackberry pickup scenario adds only a bounded player warp, while repeated throws
seed the three confirmed private-state bytes at a pre-throw frame—the same narrow
setup used by the original experiment. No replacement media or save was committed.

The three state-anchored `Bonus_Level_0N` movies have a separate pristine-disc
suite in `bonus_unlock_suite.json`. It asserts the native challenge counters,
packed unlock flags, transition latch `6`, and scene-`0x10` handoff. These
fixtures are intentionally not part of the default MOD suite because their
target pins the pristine cue hash. The Bonus 3 miss-reset proof is documented in
`EXP_2026-07-11_bonus_unlock_challenges`; it uses a session-only in-memory movie
edit and is not persisted as a second movie fixture.

## Related registries

- `python3 tools/semantic_state.py` validates `config/semantic_state.yaml`.
  `--emit asm|c|scenario|obsidian` prints review snippets; `--output` refuses an
  existing path, so authored ASM/C/notes are never overwritten.
- `python3 tools/validate_mod_layout.py` validates `mod/hook_caves.yaml` declarations
  and optional pristine/patched EXEs. The consolidated build runs declaration,
  per-module emission, and combined-output validation automatically.
