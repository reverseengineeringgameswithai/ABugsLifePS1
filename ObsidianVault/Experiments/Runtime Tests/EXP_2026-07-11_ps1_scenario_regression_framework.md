---
kind: experiment
id: EXP_2026_07_11_ps1_scenario_regression_framework
name: Persistent PS1 scenario and regression framework
status: implemented_and_live_calibrated
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: tooling_and_runtime_evidence
systems:
  - SYS_re_evidence_policy
mods:
  - MOD_hook_cave_manifest_validation
playbooks:
  - PLAYBOOK_mod_regression_troubleshooting
artifacts:
  - docs/PS1_RE_REGRESSION_ARCHITECTURE.md
  - docs/PS1_SCENARIOS.md
  - tools/ps1_scenario.py
  - tools/run_ps1_scenario.py
  - tools/scenarios/duckstation/regression_suite.json
  - /tmp/abl-framework-vertical-slice/training_scene_identity.json
  - /tmp/abl-framework-probe
---

# Persistent PS1 scenario and regression framework

## Purpose

Replace one-off debugger scripts with small declarative behavioral scenarios while
preserving the project's evidence-first, isolated-session rules. The implementation
extends the existing DuckStation Python client and `tools/launch_repro_playback.sh`;
it does not add another transport or replace specialized investigation scripts.

## Operator handoff

Start with `docs/PS1_SCENARIOS.md`. Validate or run one scenario with
`tools/run_ps1_scenario.py`; run the checked-in regression manifest with
`tools/run_ps1_suite.py --disc <fresh-build.cue> --output-dir <evidence-dir>`.
When behavior diverges, keep the JSON/Markdown report, narrow instrumentation to the
pre-divergence window, then commit the smallest scenario assertion that reproduces
the regression. See [[Regression Troubleshooting Playbook]] for the full diagnostic
ladder.

## Vertical slice

The first live slice cold-booted the rebuilt consolidated disc with
`movies/ALLMODS_Training_Still.movie.json`, advanced cycle-neutrally to movie frame
6900, and read `current_scene_id` at `0x80082504`. Actual value was `0x11`, matching
Training. JSON and Markdown reports were written under
`/tmp/abl-framework-vertical-slice`; the unique config used port 56943 and PID-scoped
cleanup succeeded. Launcher token output was subsequently redacted in reports.

## Framework surface

- Unique config/port/token/PID lifecycle with media identity and source/binary/input
  hashes.
- Movie or validated named-save anchors; ordered phase triggers for frames,
  memory/register/PC, breakpoints, GPU, audio, and generic RPC predicates.
- Conditional breakpoint actions, access/function/exec traces, GPU/SPU tracing,
  atomic captures, screenshots, typed memory/register/hit-count/result/render
  assertions, and JSON/Markdown reports.
- Curated semantic registry at `config/semantic_state.yaml`, explicitly separated
  into original, MOD-private, and unresolved hypothesis namespaces. Generators are
  review-only and refuse to overwrite authored files.

## Calibrated behavioral reproductions

The initial scenarios were run against the consolidated baseline build during
calibration:

- boot/menu: frontend scene `0`, reproducible movie remained true, and a 60-frame
  render diff changed 143,577 pixels;
- Training pause/resume: pause flag `0x8008224E` changed `0 -> 1 -> 0` while scene
  stayed `0x11`;
- tutorial progression: live overlay step advanced `0 -> 1 -> 2`, with a coherent
  atomic capture at step 2;
- native red control: current v3 Training input executed the shared throw hook while
  private Blackberry state remained clear;
- repeated Blackberry throw: current v3 LEVEL01 input plus the same three-byte
  private-state seed used by the original experiment produced repeated hook coverage;
- representative damage: the v3 LEVEL01 100% movie reached the exact enemy HP store
  at `0x800590E4` under cycle-neutral single-PC coverage;
- real Blackberry pickup: the separate collection scenario uses the current Training
  movie and a bounded player warp to exercise the actual pickup/normalizer path.

## Fixture correction

The old v2 `red_berry_enemy_test.movie.json` entered a BIOS exception path on the
current reflowed build. The old `killing_spider.movie.json` remained reproducible at
the emulator level but no longer exercised its intended throw window. They are not
trusted behavioral fixtures for this build. Their hashes remain provenance; the
suite uses existing current v3 movies rather than recording a larger replacement.
Where the original Blackberry experiment forced equip state, the scenario records
the identical bounded three-byte seed before asserting behavior.

## Final verification

- Final consolidated disc build passed declaration checks, per-module emitted-byte
  bounds (Blackberry 380, golddrop 229, grain HUD 345 changed bytes), composed layout
  validation, pristine staging restoration, and all 13 embedded-file checks.
- `build/ABL_FRAMEWORK_FINAL.bin` SHA-256:
  `32eb252f63d550bd4ece87a16d0b9c11b45d5ff942e0f084b97b949e879df084`.
- All seven scenarios passed against that exact disc. Suite report:
  `/tmp/abl-framework-final-suite/suite.json`, SHA-256
  `b9f27490baeda753e8317648a4e7d6a15f02055de353243d8515f63a5ff72d29`.
- Safe suite after integration: 135 passed, 7 deselected, with the same three
  pre-existing old-GCC `cpp` failures present before integration (baseline was 114
  passed, 7 deselected, three failures).
- Intentional failure used `--expect current_scene_is_training=0`. The report named
  address `0x80082504`, expected `0`, actual `17` (`0x11`), and still confirmed
  PID-scoped cleanup success:
  `/tmp/abl-framework-intentional-failure/training_scene_identity.md`.

## Separation

This note contains framework design and runtime results. No new original-game claim
was promoted to Canon. Confirmed original addresses used by assertions retain their
existing Canon evidence. Hook/cave allocations and validation policy live in
[[MOD_hook_cave_manifest_validation]].
