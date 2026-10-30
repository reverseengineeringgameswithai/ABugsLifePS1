---
title: Phase 4 E15 - FMV bounded exhaustion
date: 2026-08-04
status: substantiated-partial-bounded-exhausted
phase4_row: E15_fmv
additional_interpreter_movie_required: false
---

# Phase 4 E15 - FMV bounded exhaustion

## Disposition

E15 is **substantiated partial, bounded-exhausted, and ready to move on**. No additional Interpreter movie is required. This pass corrected the trigger frontier, separated executable FMV code from data/workspace, and converted the retained skip capsule into a causal lifecycle oracle.

Evidence: [`analysis/phase4_e15_bounded_exhaustion.json`](../../analysis/phase4_e15_bounded_exhaustion.json)

C guards: [`tools/phase4_e15_fmv_static.c`](../../tools/phase4_e15_fmv_static.c) and [`tools/phase4_e15_capsule.c`](../../tools/phase4_e15_capsule.c)

## Capsule-first evidence

The v3 `E15_fmv_skip` capsule is complete and untruncated. Its final cycle, frame, RAM, registers, VRAM, SPU RAM, and full state match its control. The C decoder reconstructs 542 frame records and verifies 1,626 domain hashes with zero mismatches. Its source is CachedInterpreter, so it is retained-query/poll-only and must not be armed with new CPU instrumentation.

## Nine triggers, not three

A C census finds nine resident `fmv_bin_load` calls and zero across all 22 overlay images:

| PC | ID | Role |
|---|---|---|
| `0x8004fb5c` | 1 | DLOGO |
| `0x8004fb68` | 0 | TT |
| `0x8004fb74` | 45 | INTRO |
| `0x8004ffd4` | `41 + ((b88a+1)&0xff)` | ALT sequence |
| `0x800500d8` | 46 | LOSE |
| `0x80050284` | 40 | LEV15C |
| `0x8005031c` | B table | Level B clips |
| `0x8005036c` | 41 | LEV15D/all-complete |
| `0x8005b788` | A table | Level A clips |

The previous ID/address sentence was reversed: `0x800500d8` is ID 46 and `0x80050284` is ID 40.

The A table at `0x8007a08b` maps scenes 1-15 to even IDs 10-38. The B table at `0x80077fe3` maps them to odd IDs 11-39. Resident callers therefore cover IDs 0, 1, and 10-46. ID 2 is a real case with no resident caller; IDs 3-9 share the default handler.

## Actual FMV.BIN code frontier

Raw decoding found 538 `jal`-shaped words in the 509,800-byte image. Recursive C control flow from the real entry, all 47 movie cases, the seven-way callback table, direct calls, and runtime-proven address-taken helpers yields:

- 2,995 reachable words, 11,980 bytes.
- 90 entries/case labels.
- 156 direct calls: 64 internal and 92 external.
- 39 unique external targets, all in the resident function census.
- Zero indirect calls and exactly two finite indirect jumps.
- Zero capsule-executed PCs outside the static frontier.

The remaining image is tables, strings, state, and zero-filled workspace. The game-side layer orchestrates stock PsyQ libpress/libcd/libgpu/kernel code; it is not a proprietary 497 KB decoder.

## Skip versus natural completion

The retained movie selects LEV1A, installs limit 386, and holds Start on relative frames 334-342. The overlay calls the controller latch, reads `0x80082412`, masks `0x4008`, takes the abort block once, and takes cleanup once. The frame comparison block runs 72 times, while neither natural-completion writer block runs. Skip and natural completion are distinct exits.

Natural completion remains causally established by the earlier TT frame-limit experiment: changing 440 to 900 changed streamed duration. The retail loop reads `0x80131eee` and raises `0x800cac10` at its threshold.

## Lifecycle boundary

FMV playback is synchronous and has no gameplay pause mode; the active pad path aborts playback. Each invocation reloads the overlay, initializes frame-limit/completion state, cleans up, returns, and reinitializes the resident shell. Progression bytes select movies, but transient decode state is not persistent resume state.

## Bounded residuals

- Initialization of `0x8009b88a` for every nonstandard save history; its direct law and observed zero state are closed.
- The semantic name of the `0x4000` half of abort mask `0x4008`; Start alone is the observed positive input.
- Natural runtime replay of all real clips; the complete tables and shared engine make this content enumeration.
- Every-cycle internals beyond the identified stock PsyQ boundary.

Reopen only for an FMV/selector/progression MOD or a named unusual save-history oracle. Modified-disc validation requires a pristine-base build and cold boot. New traced evidence requires a normal-speed Interpreter recording, not the retained CachedInterpreter source.
