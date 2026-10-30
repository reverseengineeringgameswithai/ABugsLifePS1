---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - execution control.md
aliases:
  - "API - execution control"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - execution control.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - execution control
type: api
category: Execution control
tags: [api, duckstation, execution, registers]
---
# API — execution control

> Pause/resume/step the CPU, run to an address, advance frames, read/write registers, and call guest subroutines.

## Methods & syntax
- **`debugger.pause` / `debugger.resume` / `debugger.reset`** → status object.
- **`debugger.stepInstruction`** — one MIPS instr (*requires pause*; emits `stepComplete`).
- **`debugger.stepOver` / `debugger.stepOut`** — over a call / to caller return (*requires pause*; temp breakpoints).
- **`debugger.runUntilAddress {address}`** — temp breakpoint + run (*requires pause*).
- **`debugger.advanceFrame`** — run exactly one frame then pause.
- **`emulator.advanceFrames {frames | seconds}`** — advance while **held controller input is re-applied each frame**; long durations chunk internally beyond one 600-frame step (up to 100000 total).
- **`emulator.advanceToFrame {frame, max_frames?=100000}`** — fast-forward to an absolute emulator `status.frame`, then pause. Temporarily enables turbo speed control and uses the same chunked frame-step path as `advanceFrames`; held controller input stays applied and active movie playback consumes every intervening sample. Backward targets are rejected. Client: `advance-to-frame --target-frame N`.
- **`debugger.getRegisters`** → all 103 regs (GPRs, pc, hi/lo, COP0, **67 GTE regs**) as int + hex. `getRegister {name}`, `setRegister {name, value}` (*requires pause*; emits `registerChanged`).
- **`debugger.callFunction {address, a0?, a1?, a2?, a3?, timeout?}`** (*requires pause*) — invoke a guest subroutine, using the current paused PC as the return trap. Loads `a0..a3`, points `ra` at the paused PC, jumps to `address`, runs until the callee returns there, then re-pauses and returns `v0`/`v1` (+ status). `timeout` is ms (default 5000, max 60000). If it stops somewhere else first, the call fails with `reason:"stopped_elsewhere"`.
- **Speed / fast-forward** (mirrors the GUI hotkeys; configured `fast_forward_speed`/`turbo_speed`, `0`=unlimited): **`emulator.getSpeed`** → `{fast_forward, turbo, target_speed, non_standard_speed}`; **`emulator.setFastForward {enabled?=true}`** / **`emulator.setTurbo {enabled?=true}`** engage/disengage. Stays engaged until disengaged (NOT cleared by loadState). Client: `speed`/`fast-forward`/`turbo` (`--off` to stop). Live: ~60→~4871 fps (~81×). Burn through long loads, then `setFastForward{enabled:false}`.

## Best use in ABL RE
Frame-stepping toward a state, reading PC/GPRs at a breakpoint hit, poking a register to test a branch. For "advance to an absolute frame" use [[API - advanceToFrame]]; for "advance until a condition" use [[API - advanceUntil]]; for non-halting PC capture use [[API - execTrace]].

## Common mistakes / gotchas
- step/setRegister/runUntilAddress need pause (`-32002`). Read methods work while running but return a **torn snapshot** — pause for coherence.
- Any breakpoint forces the **interpreter (~10–100× slower)** — remove when done.
- GTE registers are read here (and decoded in [[API - GTE state]]), **not** under `gpu.*`.

## ABL examples
G5.5–G16 used GUI execute/data breakpoints + single-stepping to trace the render chain ([[Experiment - G5.5 dynamic watch]]). Live work moved to non-halting traces for speed.

## Related
[[API - advanceToFrame]] · [[API - advanceUntil]] · [[API - addWatch]] · [[API - execTrace]] · [[API - controller input]] · [[API - GTE state]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
