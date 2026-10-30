---
title: Phase 4 D07 mosquito roaming, berry aggro, and Thumper launch
status: bounded-exhausted
date: 2026-08-03
row: D07
---

# D07 mosquito investigation

## Closure

D07 is **bounded exhausted** and ready to move on. Explicit-Interpreter playback confirms the user-observed behavior: a berry damages the mosquito, and the mosquito attacks Flik several seconds later. Square is upstream input only; the direct trigger is berry contact.

## Correction to the earlier replay

The earlier isolated profile did not explicitly contain `[CPU] ExecutionMode=Interpreter`. Its apparent no-hit replay was desynchronized and its conclusion is superseded. The corrected profile was fresh and isolated, explicitly set Interpreter before boot, mounted verified `SCUS-94288`, disabled fast-forward/turbo, and used normal-speed `debugger.resume`. Clean, instrumented, and control replays synchronized.

## Exact contact and delayed attack

Movie start emulator frame: `38657`. Square occurs at movie frames `340..344`, but the berry does not contact the mosquito until movie frame `1132`, emulator frame `39789`.

- `39789`: `0x8004B460/0x8004B464` ORs latch `0x1000` into actor flags, producing `0x5003`.
- `39789`: `0x8004B650` writes damage timer `15` to actor `+0x6C`.
- `39791`: callback `0x8004A1D0` clears `0x1000`, producing flags `0x4001`.
- The mosquito is state `0` at consumption, so the callback's state-1-only timer-25 and motion-doubling tail does not execute.
- `39819`: the damage timer reaches zero.
- `39937`: the AI VM selects state `1` and ordinary bit `0x4` at `0x8004C694/0x8004C688`.
- `39981`: it returns to state `0` and clears bit `0x4`.

The contact-to-attack-state interval is `148` emulator frames, matching the visible several-second delay.

## Causal control

A C-generated in-memory movie control changed only Square frames `340..344` to false. The original movie remained untouched. Replaying this control under the same explicit Interpreter profile produced:

- no execution of latch writer range `0x8004B458..0x8004B468`;
- no execution of the callback reaction body `0x8004A1C4..0x8004A1F0`;
- no writes to damage timer `+0x6C`;
- autonomous state transitions at `38931`, `39155`, and `39481`, but no later `39937` attack transition.

This separates input from trigger: Square enables the berry action, but contact/damage at frame `39789` sets the mosquito response in motion.

## Other D07 lanes

Ordinary roaming is confirmed independently and demonstrates that state `1`/bit `0x4` can occur without damage. Those values alone are not an aggro proof; the decisive provenance is the contact writer plus delayed control divergence.

The Thumper movie allocates slot `0x8009FE88` at movie frame `712`, activates it at `718`, and leaves adjacent slot `0x8009FF0C` dormant. Its program begins at `0x80077654` and its launch is distinct from the berry-damage path.

## Bounded exclusions

Exact collision-volume geometry belongs the shared collision subsystem, not D07. Exhaustively deriving every pursuit-vector arithmetic step after state `1` would add minimal return after the trigger, state, timing, writer, callback, negative control, roaming lane, and Thumper variant are all bound.

No additional movie and no cold boot are required for D07.

## Reproduction sources

- `tools/phase4_d07_asm.c`
- `tools/phase4_d07_movie_inputs.c`
- `tools/phase4_d07_movie_control.c`
- `tools/phase4_d07_actor_reduce.c`
- `tools/phase4_d07_callback_asm_check.c`
- `tools/phase4_d07_hit_writer_scan.c`
- `tools/phase4_d07_verified_hit_reduce.c`
- `analysis/phase4_d07_mosquitoes.json`
