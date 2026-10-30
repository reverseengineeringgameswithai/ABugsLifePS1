---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - experiment runner.md
aliases:
  - "API - experiment runner"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - experiment runner.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - experiment runner
type: api
category: Experiment
tags: [api, duckstation, experiment, causation]
---
# API — experiment runner

> The capstone: compose load → baseline → perturb → advance (fixed) → capture → diff into one call. `compareRuns` is the counterfactual that turns correlation into causation.

## Methods & syntax
- **`experiment.run {from_state?, baseline?:{registers?, memory?:[{label,address,length}]}, perturb?:{memory_writes?, controller?, watches?}, advance_frames (0..600), capture?:{registers?, memory?, access_log?}}`** → `{baseline, after, diff:{registers:[…], memory:[…]}, access_events}`.
- **`experiment.run` (animation-aware)** `{perturb?, frames, captureControl:true, diff:true|{region?, grid?, threshold?}}` → `{control:{snapshotId, framesAdvanced, captures}, perturbed:{…}, diff:{changed, regions:[{x,y,width,height}], pixelCount, metrics}, determinism:{sameInitialState, sameInputs, snapshotId, notes}}`. See below.
- **`experiment.compareRuns {from_state(REQUIRED), run_a, run_b}`** — runs `run` twice from the SAME fixture (reloading between), adds an A-vs-B diff = **the counterfactual**.
- **`experiment.diffMemory` / `experiment.diffRegisters`** — stateless diffs vs a baseline.
- **`experiment.warpAndSettle`** (new) `{writes:[{address, type:"u32"|"s32"|"float"|"fixed", value}], frames?, inputs?:[{port?, buttons}], untilStable?:{enabled, maxFrames, visualThreshold}, capture?}` → `{writesApplied, framesAdvanced, stable, stability:{checked, lastChangedFrame, threshold}, capture:{snapshotId, frame}, notes}`. See below.

## warpAndSettle (teleport-then-settle)
> "Poke position-like state, then advance **until rendering/streaming settles** before you look." For far-object verification where a raw RAM teleport drops into unstreamed "void" geometry (a known [[DuckStation API Index|footgun]]).

Applies the **typed** `writes` (`fixed` decodes a 1.16/20.12-style fixed-point value, `float`/`u32`/`s32` as named — same `ParseTypedWrite` as [[API - scatterWrite]]), then advances. With `untilStable.enabled` it advances up to `maxFrames`, **frame-diffing consecutive frames in memory** (reuses [[API - in-memory frame diff]]) until the change falls below `visualThreshold` — `stability.lastChangedFrame` is the last frame that still moved; `stable:false` + a `notes` warning means it never settled in time. `capture` returns an in-memory `{snapshotId, frame}` of the settled frame to diff/inspect.

**Far-object verification workflow:** teleport Flik near a distant object (`writes` = position), `untilStable` so the streamer loads the geometry and the camera stops drifting, then `capture` the settled frame and [[API - in-memory frame diff|diffCurrentFrame]] / [[API - gpu.pickObject]] it — instead of a raw teleport that screenshots a half-streamed void or crashes. Pair with [[API - crash safety and health events|guestHalted]] to catch a teleport that crashes the guest.

## Animation-aware mode (phase-matched no-force control)
> The fix for "I perturbed a *running* scene and the diff is all animation." Built into `experiment.run`.

`captureControl:true` (or any `diff`) makes the runner snapshot the initial state **in memory**, run a **control** path with the perturbation **stripped**, restore the *identical* snapshot, run the **perturbed** path, and diff the two *frames* (shared `FrameDiff` core, same metrics as [[API - visual diff]]). Animation present in both cancels → only the perturbation's visual effect remains. `frames` aliases `advance_frames`; `diff.threshold` absorbs dither; `diff.region`/`grid` scope the compare. `determinism.sameInitialState` is **verified** by re-hashing the restored snapshot (both `snapshotId`s match ⇒ same start). `changed:false` + `pixelCount:0` ⇒ the poke had no visible effect at that frame.

## Best use in ABL RE
The highest-value RE primitive: prove *causation*. Perturb X, predict effect on Y, run, confirm. `compareRuns` (with vs without the perturbation) is what upgrades a finding to **CONFIRMED**.

## Common mistakes / gotchas
- Register diff needs BOTH `baseline.registers` and `capture.registers`; memory diff is matched **by request order** — capture the same regions before and after.
- Watches the run armed are removed afterward, but **memory pokes persist** (reload to undo); **controller hold is left in place** after `run` — clear it.

## ABL examples
The CONFIRMED-vs-LIKELY rubric ([[API - determinism]]) is built on this. The collision lever (lower sector Y → Flik falls ~1:1) and visual-≠-collision split are exactly compareRuns-style counterfactuals → [[Finding - Collision RAM edit moves footing 1to1]], [[Finding - Visual is not collision]].

## Related
[[API - determinism]] · [[API - in-memory frame diff]] · [[API - findings store]] · [[API - scatterWrite]] · [[API - crash safety and health events]] · [[Playbook - Verify a hypothesis]] · [[Playbook - Create a deterministic experiment]]

Source: ~/duckstation/docs/external-debugger-experiment-runner.md
