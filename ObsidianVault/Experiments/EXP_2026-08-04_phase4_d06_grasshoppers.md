---
date: 2026-08-04
phase: 4
row: D06_grasshoppers
status: substantiated-partial-bounded-exhausted
tags: [phase4, grasshopper, enemy-ai, static-analysis, interpreter]
---

# Phase 4 D06: grasshopper family

## Question

Bind the ground, airborne/roof-entry, attack, carried-object, and immunity claims for the grasshopper family without inventing separate variants that are not present in the executable.

## Inputs and preservation

- `SCUS_942.88`: SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- `REBUILD/files/LEVEL03/LEVEL.BIN`: SHA-256 `fef7bd2a72c5c293b2f164ba1ca195f45c0843c5f19e52cbfdb48fd14fbc59a1`, raw overlay at `0x800b39a0`.
- `grasshopper.sav`: SHA-256 `40edaae0c6a8c90fa45315695d60ede16bdfc96afe69c01e4c11c56b5c610f05`.
- `grasshopper_aggro.sav`: SHA-256 `2fa4742d057647d7833ae3cb52584f39e940a8fe6441bcb4653eede08ff7a135`.
- No relevant retained D06 capsule matched the capsule index. This was recorded as live escalation `P4-D06-20260804-GRASSHOPPER` before the bounded confirming replay.
- All static inspection was read-only. The durable C extractor is `tools/phase4_d06_static.c`; its output is derived only from the two hash-pinned retail binaries.

## Corrections made during investigation

The level overlays are raw mapped images, not PS-X EXEs with a `0x800` file header. `LEVEL03/LEVEL1.BIN` is the bonus overlay and is not the Tunnels resident overlay. The correct resident input is `LEVEL03/LEVEL.BIN` at `0x800b39a0`. No conclusion below uses the rejected mappings or an early over-broad CFG walk; the selector-3 function boundary is the independently established returning function `0x800b3d78..0x800b3e84` (68 instructions).

## Static result

Scene 3 contains 19 grasshopper spawn descriptors. Every one is the same descriptor family: word `0x080f`, actor ID 15, mover-VM program index 8, HP 6, delay 100, and flags `0x0052`. The program table at `0x80077af8` resolves index 8 to `0x8007760c`.

Program 8 contains the native-selector call, pursuit/arrival opcode `0x0006`, opcode `0x0015`, animation/state changes, a random `32..95` tick cooldown, a random-heading step, and a parked movement state. The interpreter loads actor program pointer `+0x70` at `0x8004c17c`, fetches an opcode at `0x8004c1ec`, and commits the next pointer at `0x8004c834`. Shared arrival code at `0x8004d02c..0x8004d03c` clears motion/cooldown and advances the program.

Native selector 3 calls the Tunnels overlay at `0x800b3d78`. That function turns the actor toward the player, sets flag bit 1, reads the spawn-template byte at `+0x0f`, and indexes a resident table at `0x800b4d20`. On a subtype's first occurrence it creates 24 kind-21 child/effect objects, increases actor field `+0x6a` by 2400, sets motion field `+0x20` to -2048, and plays sound 102. The three direct callees are `0x80060ae4`, `0x80059e44`, and `0x8005044c`.

This proves the supposed ground/flying/carried-seed variants are presentation or state variations inside actor 15/program 8. It does **not** justify naming the template subtypes or the kind-21 children as seeds without visual evidence.

The actor-creation history gate explicitly exempts actor ID 15 from chase-bit suppression. The generic hit-triggered aggro path excludes ID 15, so grasshopper pursuit is native/program driven rather than created by taking a hit. Contact, berry damage, and death/respawn flow into the shared D03, D04, and D05 mechanisms; no grasshopper-only berry-immunity branch was found.

The unique bonus-3 rule remains independently bound: an accepted blue-class kill of actor ID 15 increments the streak, and the fifth accepted kill sets bonus flag bit `0x04` and transition latch 6. Other contacts reset or fail the streak according to the shared challenge gate.

## Narrow live escalation

DuckStation used a fresh absolute config directory, dedicated loopback port/token, the pristine `SCUS-94288` media, and Interpreter execution. Instrumentation was re-armed after each state load. Playback used `debugger.resume` at normal speed, not `movie.advanceToFrame` or fast-forward.

In `grasshopper.sav`, active slot 44 (`0x800a1430`, backlink `0x80094f08`) began at program `0x8007761c`, field `+0x60 = 10`. With no input, `0x8004d03c` advanced `0x8007761c -> 0x8007761e` at frame 250462, and `0x8004c834` committed `0x8007762e` at frame 250466. Selector 3 received no hit in this interval, confirming it is initialization-time behavior rather than a recurring aggro latch.

In `grasshopper_aggro.sav`, the same actor began at program `0x8007762e`, field `+0x60 = 7`. The common contact handler `0x8004a700` executed at frame 251244 with `s1=0x800a1430` and return address `0x8004b4a8`. Player health stayed 11 in that sampled call. This binds interface admission only; it is not a claim that all grasshopper contact is harmless because the common contact subsystem still owns its gating and invulnerability timing.

Both states already had chase-capable flag bit `0x2`. Their relevant difference is program/motion state, not a damage-created aggro bit.

## Closure decision

**Substantiated partial, bounded-exhausted.** D06 now has exact actor, program, native overlay, state-transition writer, and shared-system boundaries. Remaining unknowns are presentation labels for template byte `+0x0f`, visual identity of the 24 kind-21 children, and a per-berry matrix already owned by D04. Their cost is high relative to D06's semantic return and none blocks the Phase 4 family binding.

No new Interpreter movie is required to move on. Request one only if exact visual subtype labels or grasshopper-specific per-berry outcomes become an explicit deliverable.

Structured evidence: `analysis/phase4_d06_grasshoppers.json`.

