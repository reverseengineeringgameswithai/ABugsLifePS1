---
title: Mosquito actors
status: confirmed-bounded
row: D07
updated: 2026-08-03
---

# Mosquito actors

## Berry-triggered aggro

A Square press does not directly aggro a mosquito. In the confirmed movie, Square occurs at movie frames `340..344`; the berry contacts the mosquito much later at movie frame `1132`.

At emulator frame `39789`, collision/damage function `0x8004ABF4` executes `0x8004B460/0x8004B464`, setting actor flag latch `0x1000`, and `0x8004B650` writes timer `15`. Callback `0x8004A180` clears the latch at frame `39791`. Because the mosquito is state `0`, it skips the callback's state-1-only timer-25/motion-doubling tail. The damage timer expires at `39819`; the AI selects attack state `1` at `39937`, `148` frames after contact, and returns to state `0` at `39981`.

An explicit-Interpreter control with only the Square samples removed produces no berry contact, no latch writer, no damage timer, no callback reaction, and no frame-39937 attack transition. This confirms berry contact/damage as the direct trigger for the delayed attack.

## Ordinary AI state

State `1` and ordinary flag bit `0x4` also occur during undamaged roaming. They are not sufficient evidence of aggro by themselves. Causal identification requires the `0x1000` collision latch and the later divergence from a no-contact control.

## Thumper-spawned mosquito

The Thumper recording allocates actor slot `0x8009FE88` at movie frame `712`, activates it at `718`, and leaves `0x8009FF0C` dormant. This launch variant uses the program beginning at `0x80077654` and is separate from berry-contact damage.

## Provenance

Confirmed domains:

- ordinary roaming and state cycling;
- berry contact as direct damage/aggro trigger;
- latch writer, callback consumer, timer, and delayed attack timing;
- explicit-Interpreter negative control;
- Thumper allocation, activation, launch, and adjacent-slot control.

Bounded outside D07: exact shared collision-volume geometry and exhaustive pursuit-vector arithmetic.

See [[EXP_2026-08-02_phase4_d07_mosquitoes]] and `analysis/phase4_d07_mosquitoes.json`.
