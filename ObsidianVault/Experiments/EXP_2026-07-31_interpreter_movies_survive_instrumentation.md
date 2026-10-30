---
type: experiment
status: complete
date: 2026-07-31
system: duckstation instrumentation
phase: platform
aliases:
  - EXP_interpreter_recorded_movies_survive_full_instrumentation
artifacts:
  - movies/100%/LEVEL00_Training.movie.json
  - movies/100%/LEVEL01.movie.json
  - movies/LEVEL02_savestate_test_interpreter.movie.json
---

# Interpreter-recorded movies survive full instrumentation

## Verdict

**On `Interpreter`, no instrumentation tested has ever desynced a movie replay.**

Ten runs across five operator-recorded movies and four levels — from-boot and
state-anchored, through intro and outro FMV, through sustained XA music
streaming, with the event ring deliberately overflowed — every armed run was
byte-identical to its clean pair: full 2 MiB main-RAM sha256 equal at every
sample point, and a **final cycle delta of exactly 0** in every pair, ~35 billion
emulated cycles in total.

The one boundary is not a desync: a **halting** breakpoint stops the core
mid-frame, so a snapshot taken while halted is a mid-frame snapshot. The run is
still identical (cycle delta 0 over 2,659 hits) — only the observation point
moves.

The failure everyone has been living with belongs to **`CachedInterpreter`**:
arming anything there forces a mode swap and silently destroys a replay recorded
in that mode, with `reproducible: true` still reported and no error raised.

## Question

Armed `execTrace` / `accessLog` watches have desynced movie replays for years,
returning "plausible but empty" captures with no error. Is that a defect in the
tracing subsystem, or something else — and can it be avoided?

## Answer

It was never a tracing defect. It is a **CPU execution-mode mismatch**.

Arming any CPU-level instrumentation forces `CPUExecutionMode::Interpreter`:

```cpp
// src/core/cpu_core.cpp — CPU::CheckForExecutionModeChange()
// Currently, any breakpoints require the interpreter.
const CPUExecutionMode new_execution_mode =
  (g_state.using_debug_dispatcher ? CPUExecutionMode::Interpreter
                                  : g_settings.cpu_execution_mode);
```

`UpdateDebugDispatcherFlag()` raises `using_debug_dispatcher` on
`has_any_breakpoints || instruction_hook || precise_instruction_hook ||
memory_access_hook || trace_to_log`. So `accessLog.addWatch`,
`execTrace.addRangeWatch` and `debugger.addBreakpoint` all trigger the swap.

The historical repro config pins `ExecutionMode=CachedInterpreter`, because that
is what the `go_to_end` movies were recorded in. Arming therefore swapped the
engine mid-replay and the recording drifted off-script — the game ended up
somewhere else entirely, so the awaited event never fired.

**Record and replay on `Interpreter` and the mismatch disappears.** Arming then
requests the mode already in use, nothing switches, and instrumentation is free.

## Evidence

Movie: `movies/LEVEL00_GOTOEND_INTERPRETERTEST.movie.json`
(sha256 `13f335ef1cc742110b306dd864f2494dca14157efd22d2ac55f5b07f430b4c9a`,
7,984 frames, `from_boot`, recorded by the operator on `Interpreter`).

| Run | Mode | Recorded on | Armed | Result |
|---|---|---|---|---|
| A | CachedInterpreter | CachedInterpreter | nothing | matches banked baseline; enters Training @4502 |
| B | CachedInterpreter | CachedInterpreter | **one write watch on a dead address** | **DESYNC** — never entered Training, ended in scene 1 |
| I1 | Interpreter | Interpreter | nothing | enters Training @4002 |
| I2 | Interpreter | Interpreter | one dead-address watch | timeline identical to I1 |
| I4 | Interpreter | Interpreter | 15 watches + execTrace range | timeline identical to I1 |
| MAX | Interpreter | Interpreter | 15 watches + `execTrace` 0x80010000–0x80060000 + `accessHistory` + `transferLog` | **byte-identical to clean** |
| L01 | Interpreter | Interpreter | same maximal set, **17,632-frame LEVEL01 incl. intro + outro FMV** | **byte-identical**, 1207 comparisons |
| L02 | Interpreter | Interpreter | same maximal set, **state-anchored** movie from absolute frame 18726 | **byte-identical**, 578 comparisons |
| OVF | Interpreter | Interpreter | `execTrace` over ALL main RAM, `max_events=5,000,000` → **ring wrapped, `truncated: true` at 200,000** | **byte-identical**, cycle delta 0 |
| HALT | Interpreter | Interpreter | **halting** execute breakpoint, 2,659 hits | run identical (cycle delta 0) but **observations shift** — see below |

Run B is the decisive negative control: the watch was on scratchpad
`0x1F8003F0`, which no game code touches. It fired 24 times, all from BIOS init
at `0xbfc02bb0`. It logged essentially nothing and cost nothing — so the desync
cannot be attributed to callback work. Only the mode flip changed.

The MAX comparison, clean vs fully armed, over 32 sample points every 250 frames:

- **sha256 of all 2 MiB of main RAM — identical at every point**
- 13 typed gameplay fields, actor-record count, actor-record sha256, kind-table sha256
- **544 field comparisons, zero mismatches**
- final frame 7985 both; **final cycle 4,520,555,872 both — delta exactly 0**

While armed it logged 13,870 access events and 10,000 exec events.

## Consequences

- **CPU tracing during movie replay works.** Previously believed impossible; the
  project routed around it with poll-only movie evidence.
- **The arm-late ritual is obsolete** for Interpreter-recorded movies. "Arm ≤1
  tick before or the outcome is suppressed" was a symptom of the mode flip, not a
  property of instrumentation.
- **The boot shadow closes.** PCs that only execute in the first frames can be
  traced by arming before advancing.
- Existing `CachedInterpreter` movies remain valid for **poll-only** oracle work
  (`tools/phase2_compare.py` and the completion oracle are unaffected). They can
  never be traced; re-record on `Interpreter` per level as tracing is needed.

## Halting breakpoints: the one boundary

A **halting** breakpoint (`debugger.addBreakpoint`) does **not** desync the run
either — 2,659 hits, final frame and **final cycle identical to clean, delta 0**.
But it stops the core *mid-frame*, so a snapshot taken while halted is a
mid-frame snapshot and will not match a clean run byte-for-byte.

This was measured rather than assumed. Recording each sample's own cycle showed:
of the 6 sample points whose RAM differed, **all 6 also had a different sample
cycle; there was not one point with the same cycle and different state.** Every
difference is *where* the observation landed, not *what the machine did*.

It is also visible: with a breakpoint armed the display flickers between complete
frames and partially-rasterised ones (background clear colour plus whatever
geometry had been drawn when the core stopped). That is the paused mid-frame GPU,
not corruption.

Practical rule: with halting breakpoints, resume to a frame boundary before
sampling, or compare only points whose sample cycle matches.

Two harness bugs were found and fixed while establishing this, both worth
remembering:

- `movie.advanceToFrame` **returns early and without error** when a halting
  breakpoint stops the core. Trusting the call silently compares samples taken at
  different real frames, which looks exactly like a catastrophic desync. Always
  verify the frame counter afterwards.
- `movie.advanceToFrame` targets a **movie-relative** frame (0..frame_count) even
  for a state-anchored movie whose emulator frame counter starts at 18726.

## Scope and limits

Established across **five movies / four levels**, from-boot and state-anchored,
through FMV transitions and sustained XA streaming, with ring-buffer overflow, at
roughly 35 billion emulated cycles — every one byte-identical.

Discharged since the first draft:

1. ~~Heavy CD/XA streaming~~ — every level streams music continuously via
   `CdlSetfilter`/`CdlReadS`; LEVEL01 ran AUDIO1 ch0 throughout with `transferLog`
   armed.
2. ~~FMV (.STR) playback~~ — the LEVEL01 100% movie crosses both the level-intro
   and level-outro FMV. Highest CD bandwidth the game produces.
3. ~~Ring-buffer overflow~~ — `max_events` is a **per-watch cap defaulting to
   10,000**, which is why a range over all of RAM still stopped at 10,000. Raising
   it to 5,000,000 wrapped the 200,000-entry global ring (`truncated: true`) with
   zero effect on the run.
4. ~~State-anchored movies~~ — LEVEL02, `reproducible_only_from_state: true`.
5. ~~Halting breakpoints~~ — covered above; run identical, observation point moves.

VRAM/GPU/SPU state was not hashed directly, but this is not a meaningful gap: those
domains are downstream of CPU writes, and any feedback difference (GPU busy flags,
SPU IRQ timing, CD interrupts) would have perturbed the CPU. A zero cycle delta
across 4.5 billion cycles rules that out.

## Note on fixture hashes

After these runs, every movie recorded today gained a `notes` field declaring its
Interpreter provenance, so a future reader can tell traceable movies from
CachedInterpreter ones without guessing. That changed each file's sha256; the
frame data is untouched. Hashes quoted here are post-annotation.

## Related

- [[DuckStation_API_Index]] — high-cost gotchas
- [[EXP_2026-08-01_savestate_movie_arm_phase_desync]] — a second, independent way a
  movie replay desyncs, unrelated to CPU mode
- The auto-memory note `duckstation-trace-gotchas` records the superseded
  poll-only rule (memory slug, not a vault note — deliberately not a wikilink).
