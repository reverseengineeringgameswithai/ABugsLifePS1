---
kind: experiment
id: EXP_2026-08-03_phase4_a18_pause
date: 2026-08-03
status: complete
confidence: substantiated_partial
source_state: original_game
phase4_row: A18_pause
---

# Phase 4 A18 pause

## Result

A18 is **partial, high-value bounded-exhausted; move on**.

The resident pause law, freeze ownership, ongoing presentation, CD/XA stop,
low-level sound servicing, resume edge, and exit-level handoff are confirmed.
No Interpreter movie or cold boot is required for this result.

## Capsule-first decision

No relevant A18/pause capsule exists under the declared Phase 4 v2 external
evidence root. Static code answered admission and dispatch. One named runtime
domain remained: which state domains freeze, whether rendering/CD continue, and
whether resume/exit follow the decoded branches. That justified one isolated,
state-anchored DuckStation control without CPU instrumentation.

## Identity

- pristine media: `SCUS-94288`
- cue SHA-256: `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`
- pristine EXE SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- state: `level01.sav`
- state SHA-256: `5f29b29d2254be1928a01132c2cf6424d426c7ea1308ac709ea4fd737dbbe8a2`
- DuckStation revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`
- binary SHA-256: `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`
- isolated config: `/tmp/duckstation-debugger-phase4-a18-20260803`, port `24418`
- cleanup: launcher-confirmed stopped

## Static causal model

### Admission

Pause uses a rising START edge, not a held-button level:

```text
(0x80082412 & 0x0008) != 0
(0x800822E4 & 0x0008) == 0
```

It additionally requires:

- `u32 0x800822F8 == 0`
- `u32 0x8008216C == 3`
- `s16 0x80082388 == 0x80`

`0x8004F3AC` stores one to `s16 0x8008224E`, clears the exit
selection/confirmation state, and dispatches sound 28.

### Alternate shell

The outer scene loop at `0x8004FEB8` reads the pause flag. Zero calls
`gameplay_state_machine` at `0x8004ECD4`; nonzero calls the pause render entry
at `0x8004F478`, which falls into `0x8004F480`. Both converge on the common
`0x8003E104` tail.

C scanning found 34 unique direct call targets in gameplay and 11 in pause,
with no `jalr` in either bounded root. Gameplay-only targets include player
physics, actor contact/update, movers, HUD animation, the contact-object walker,
berry projectiles, and plants. The pause root keeps scene rendering, pause-menu
drawing/input, presentation, and SFX dispatch.

### Resume and exit

Cross or START on the main option resumes through `0x8004F858`.

Exit is Down, Cross, Left, Cross:

- Down writes exit option 1.
- Cross opens confirmation state 1.
- Left selects confirmation state 2.
- Cross clears pause, writes flow state 5, seeds timer 23, and sets player flag `0x0004`.

The decisive PCs are `0x8004F9C0`, `0x8004F9E4`, `0x8004F9FC`, and
`0x8004FA1C`.

## Runtime counterfactual

Matched 60-frame gameplay and pause legs were run from the same state.

| Domain | Gameplay | Pause |
|---|---|---|
| actor pool `0x8009FE04`, 40 x `0x84` | changed | byte-identical |
| contact pool `0x800B0D18`, 64 x `0x38` | changed | byte-identical |
| plant region `0x80090BF0 + 0x600` | changed | byte-identical |
| HUD sample `0x800A7E00 + 0x100` | changed | byte-identical |
| camera `0x80095358 + 0x60` | not needed | byte-identical from pause 60 to 120 |
| displayed framebuffer | changed | continued changing |

All established player simulation fields were stable. The only byte that moved
inside the sampled `0xB0` range was `0x800A65A8`. C/ASM attribution corrected
that apparent exception: it is `_SsVmFlush`'s modulo-16 sound cursor, not player
simulation. `0x80069658` advances it; it moved 3 to 15 during the settled
60-frame pause window.

The canonical actor pool must not be confused with `0x80090748`. An initial
probe mislabeled that homing-target region as actors. The label and conclusion
were rejected, then the control was rerun against `0x8009FE04`.

## Presentation and audio boundary

Between paused frames 60 and 120, 3,568 of 488,000 pixels changed in a 105x46
pause-menu region. Presentation is active; gameplay rendering is replayed behind
the menu, consistent with the earlier Training double-buffer finding.

CD/XA progress stopped exactly: current/requested LBA stayed
`187189/187190`. The gameplay control advanced from `187186/187187` to
`187337/187338`; after resume it advanced again.

Audio is split:

- pause-menu SFX dispatch remains callable;
- `_SsVmFlush` continues servicing its modulo-16 cursor;
- the current XA/CD read position stops;
- exact per-voice SPU evolution remains unmeasured.

The fork source and docs advertise `spu.status`, but the pinned running binary
returned `-32601` for both the raw call and client wrapper. No per-voice claim is
made from unavailable instrumentation.

## Observation, inference, confirmation

| Class | Claim |
|---|---|
| Observation | Pause menu and framebuffer continue changing while gameplay state domains remain fixed. |
| Inference | Numeric admission gates correspond to normal gameplay eligibility, but their complete special-state vocabulary is not named here. |
| Causal confirmation | The outer branch removes the complete gameplay root and selects the pause renderer; matched controls and exact resume/exit writes agree with that static law. |

## Phase 4 closure metrics

| # | Metric | State | Boundary |
|---|---|---|---|
| 1 | Original oracle | advanced | Pristine save-state control covers enter, 120-frame pause, resume, and exit |
| 2 | Complete frontier | advanced | Root direct-call frontier and all direct pause-flag accesses closed; callee-wide pointer provenance not claimed |
| 3 | Typed state | advanced | Pause/input/option/confirmation/flow/timer/sound-cursor fields typed |
| 4 | Lifecycle | advanced | Admission, held-edge debounce, pause dwell, resume, exit, and reset clears bound |
| 5 | Original interfaces | advanced | Input, gameplay scheduler, scene render, SFX, CD/XA, and transition interface bound |
| 6 | Campaign breadth | bounded | Resident all-stage law plus one ordinary stage; boss/FMV/special contexts deferred |
| 7 | Cross-system | advanced | Input -> shell dispatch -> scheduler/render/audio -> scene-flow chain confirmed |
| 8 | Source closure | met for bounded slice | Semantic C and pristine-EXE C analyzer added |
| 9 | Durable evidence | advanced | Scenario, hashes, machine artifact, Experiment, and Canon added; no reusable capsule |

## Why moving on is justified

Remaining work is special-context breadth, semantic naming of numeric denial
gates, and per-voice SPU behavior on a compatible runtime binary. Reopen only
for a named special-state failure or a MOD dependency intersecting pause.

## Related

- [[SYS_pause_shell]]
- [[EXP_2026-07-11_training_pause_n_double_buffer_flash]]
- `analysis/phase4_a18_pause.json`
- `config/phase4_a18_pause.yaml`
- `src_re/pause_shell_8004ecd4_8004f480.c`
- `tools/phase4_a18_static.c`
