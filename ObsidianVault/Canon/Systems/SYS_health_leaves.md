---
kind: system
id: SYS_health_leaves
name: Health Leaves
status: substantiated_partial
confidence: confirmed_core_bounded_residuals
source_state: original_game
functions:
  - FUNC_800498AC
  - FUNC_80058864
  - FUNC_8005953C
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-08-03_phase4_c12_health_leaves
  - analysis/phase4_c12_health_leaves.json
  - tools/phase4_c12_static.c
---

# SYS_health_leaves

## Canon contract

- True player health is signed halfword `0x800A6594`.
- A health leaf adds exactly one to that field.
- The pickup handler itself does not clamp the result.
- Normal refill/initial health is four.
- `0x800A7E2A` is HUD animation state, not health.

## Generic enemy-death drop

The generic death-animation retirement path evaluates one health-leaf roll when
health is below four. Its test is:

```c
mask = (2u << health) - 1u;
drop = (rng_byte & mask) == 0;
```

This gives odds `1/2`, `1/4`, `1/8`, and `1/16` at health zero through three.
Enemy flag `+0x5C & 0x40` suppresses the producer. A successful roll creates
constructor 38 at enemy Y minus `0x1000`.

This is not a timer or a separate mercy-counter cadence.

## Secondary producer

Constructor 50 retires through effect selector 23. That effect always creates
constructor 58 and, when health is below four, has a flat `1/8` chance to create
constructor 38 at source Y minus `0x800`.

The player-facing object name for constructor 50 is not confirmed. Retain the
numeric name until behavioral or asset evidence names it. Ordinary native thrown
berries are not this path because their effect selectors differ.

## Lifetime and pickup

Constructor-38 metadata seeds TTL 200. The contact-object lifecycle consumes TTL
at 30 Hz, so an untouched leaf lasts about 6.67 seconds. The metadata radius
contribution is 100 and the effective walker pickup radius is 400 scaled units.

Collection dispatches action 9, increments health by one, plays sound 62, writes
state 7, and forces TTL 1. The record retires on the next logic tick.

## Persistence boundary

Health damage, leaf healing, the 50-grain refill, and player initialization write
the runtime health halfword. Health is not directly serialized by the progression
serializer boundary established in C02/C03.

## Bounded residuals

- modern Interpreter-recorded natural presentation oracle
- artificial multi-leaf overfill behavior
- player-facing semantic name for constructor 50
- row-specific attribution of the already-confirmed shared TTL decrement PC

These residuals do not block moving on from Phase 4 C12.

## Evidence

- [[EXP_2026-08-03_phase4_c12_health_leaves]]
- `analysis/phase4_c12_health_leaves.json`
- `tools/phase4_c12_static.c`
