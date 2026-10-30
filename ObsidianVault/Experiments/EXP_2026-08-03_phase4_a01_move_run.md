---
kind: experiment
id: EXP_2026-08-03_phase4_a01_move_run
date: 2026-08-03
row: A01_move_run
status: substantiated_partial_bounded_exhausted
confidence: confirmed_with_bounded_runtime
---

# Phase 4 A01 move/run investigation

## Disposition

A01 remains `partial`, but is `bounded_exhausted` for Phase 4 prioritization. The reusable input, heading, acceleration, velocity, normal-ground collision, animation, and release chain is causally bound. Exhaustively replaying every authored wall, slope, obstruction, and level is content-surface enumeration with low marginal return and is explicitly deferred rather than mislabeled solved.

No Interpreter movie is required. This was a pristine-ASM-first investigation followed by same-save API counterfactuals for the named missing runtime comparisons. Cold boot is not required because no disc, code, asset, or persistent game state was changed.

## Capsule gate

The required Phase 4 capsule audit found no manifest identity-bound to `lag_walkingaround.movie.json` or `level01.sav`:

```bash
rg -l 'lag_walkingaround|level01\.sav' \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4 \
  --glob manifest.json
```

The empty result means a name-adjacent capsule cannot be substituted. Offline static analysis remained primary; the isolated save-state run was justified only for input magnitude, turning, animation, slope-contact, and release controls.

## Identity and anchor

| Item | Identity |
|---|---|
| Game | `SCUS-94288`, pristine retail cue |
| Cue SHA-256 | `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644` |
| BIN SHA-256 | `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566` |
| Save | `level01.sav`, SHA-256 `5f29b29d2254be1928a01132c2cf6424d426c7ea1308ac709ea4fd737dbbe8a2` |
| Legacy movement movie | `lag_walkingaround.movie.json`, SHA-256 `3db6ad898d9dcc257b2d0ed75f1385493e3c5b90f066b63eb4db18a5f06bad31`; not replayed |
| DuckStation | revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty external-debugger fork |
| Binary SHA-256 | `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899` |
| Isolation | `/tmp/duckstation-a01-move-run-20260803-02`, port `24412`, Interpreter, normal speed |

`emulator.getStateInfo`, `debugger.status`, and `emulator.getMediaInfo` agreed on the serial and media before the save was loaded. External controller state was cleared before every accepted branch because controller holds intentionally survive `loadState`.

## Static ASM result

The C guard is `tools/phase4_a01_static.c`; the documentation model is `src_re/move_run_80048138.c`.

| Stage | Pristine owner and law |
|---|---|
| Direction | `FUNC_80047EBC` consumes the camera-relative vector globals and writes target heading `player+0x28`. Digital left/right also change the target at `0x800490D0/0x80049100`. |
| Magnitude | Default cap is `0x700`; the `0x0300` L2/R2 slow mask selects `0x300`; the shared resolver scales the cap by its Q14 magnitude at `0x80049150..0x80049158`. |
| Turning | `0x80049240..0x800492A8` computes the shortest modulo-4096 difference, caps it by `0x400`, shifts it by the state-selected amount, and converges actual heading `player+0x20`. |
| Acceleration | Lateral and forward projected components decay toward zero by `0x100` and `0x40`. Active forward input adds `0x50+0x40`; the components are bounded and published at `player+0x38/+0x3C`. |
| Velocity | `0x800494B4..0x80049540` rotates projected components through the trig table and stores `player+0x2C/+0x34`. |
| Collision | `0x80049558..0x80049564` snapshots prior XYZ, then `0x800495C8` passes position, velocity, and `player+0x82` contact bytes to `FUNC_8003633C`. Its collision loop publishes contact bytes and resolved position/floor behavior. |
| Animation | Grounded default cases resolve to idle `22`, run `0`, and slow walk `29`; `0x800569AC` latches the requested animation. |

## Runtime controls

All values are from the same save anchor. API frames are 60 Hz; the traced gameplay update ran on frames `12513, 12515, 12517, 12519`, establishing the 30 Hz movement tick.

| Control | Result |
|---|---|
| Idle 16 frames | XYZ stayed `(197091,2734,492897)`, velocity/components stayed zero, grounded `0x0101`, animation `22`. |
| Up 2/8/16 frames | Forward component `144/378/681`; at 16 frames XYZ `(194530,2666,494937)`, grounded `0x0101`, animation `0`. |
| Up+R2 8 frames | Same early displacement/component as Up because the component had not reached the slow cap; animation was `29`. Existing Phase 2 60-frame data gives slow/run displacement ratios `0.6057413181` X and `0.6040426982` Z. |
| Up+Left 8 frames | Target and actual heading `2737`; XYZ `(196220,2703,492400)`. |
| Up+Right 8 frames | Target and actual heading `177`; XYZ `(197369,2721,493903)`. |
| Analog full-up 8 frames | API reported `AnalogController`; the game working word became Up `0x0010`, and XYZ exactly matched digital Up `(196302,2755,493550)`. |
| Release after 16-frame Up | The first released 30 Hz ticks reduced the forward component `681 -> 616 -> 551`; after 24 API frames all XYZ velocity and both projected components were zero, grounded remained `0x0101`, and idle animation `22` was restored. |
| Normal slope response | Across the run controls, Y and floor changed together while contact remained `0x0101`; the controller did not confuse slope-following with airborne state. |

### Instrumentation flight

After loading the state, eight PC watches were re-armed and Up was held for eight API frames. The bounded execTrace retained 25 events with no truncation. PCs `0x80049140`, `0x80049348`, `0x800494AC`, `0x80049524`, `0x80049540`, and `0x800495C8` each hit four times. `0x800569AC` hit once for the animation transition. `0x80056654` had zero hits in this already-selected animation window; that negative result is not generalized.

The first event was frame `12513`, cycle `7084378841`; the last was frame `12519`, cycle `7087777137`. At the integrator call, arguments were `a0=0x800A6500`, `a1=0x800A652C`, and `a2=0x800A6582`, confirming the static object/velocity/contact binding.

## Evidence classification

**Observation:** clean idle is stable; digital and analog full-up agree; left/right diverge in heading and trajectory; R2 changes animation before its speed cap becomes active; slope travel retains contact; release returns velocity/components and animation to idle.

**Inference:** the shared direction resolver normalizes physical analog full-up and D-pad Up into the same player movement path, while the cap and animation branches remain independently selectable.

**Causal confirmation:** pristine ASM supplies the exact constants and store/call chain, the same-save controls change one input variable, and untruncated execTrace hits the calculation, velocity stores, integrator handoff, and animation latch on the expected 30 Hz ticks.

## Rejected run

An initial batch was discarded because its branches inherited external controller holds across save loads. It produced identical cases and working button words from the previous branch. Accepted controls explicitly call `emulator.clearControllerState` before each reload. No conclusion uses the rejected batch.

## Closure boundary

Solved here: input normalization, run/slow caps, acceleration and decay, turning, velocity rotation, integrator handoff, normal slope/contact behavior, grounded animation coupling, and release-to-idle lifecycle.

Deferred: every authored collision surface/obstruction, all-level movement oracles, and special-state overrides already owned by dedicated rows. Those are broad enumeration, not a missing reusable law. This is sufficient to move on while retaining the honest `partial` status.

Structured evidence: `analysis/phase4_a01_move_run.json`.
