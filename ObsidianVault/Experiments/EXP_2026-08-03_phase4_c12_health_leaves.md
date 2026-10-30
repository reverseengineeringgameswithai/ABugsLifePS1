---
kind: experiment
id: EXP_2026-08-03_phase4_c12_health_leaves
date: 2026-08-03
status: complete
confidence: substantiated_partial
source_state: original_game
phase4_row: C12_health_leaves
---

# Phase 4 C12 health leaves

## Result

C12 is **substantiated partial and bounded-exhausted for Phase 4**. Move on.

The exact heal, generic enemy-death gate and odds, secondary numeric producer,
leaf lifetime, pickup radius, collection teardown, and health reset boundary are
instruction-bound. A live DuckStation escalation would add a modern behavioral
oracle, but it is not needed to answer the row's current RAM or block-flow
questions.

## Capsule-first disposition

No relevant C12, health, or leaf capsule was present under the declared
`ABL-external-evidence/trace-capsules/Phase4/v2` root. The missing domains were
not frame presentation, exact instruction attribution, GPU, SPU, or DMA. They
were resident-code control flow and static metadata, so the investigation stayed
offline against the hash-verified pristine executable and retained ASM.

Pristine input:

- `REBUILD/files/SCUS_942.88`
- size `471040`
- SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- load address `0x80010000`

## Observation

Historical fixtures exist at `health_drop.sav`, `health_test.sav`, and
`movies/Phase4/B07_health_partial_full.movie.json`. The B07 movie predates
recorded Interpreter-mode provenance and is retained as poll-only historical
evidence. It was not armed with CPU instrumentation and is not being promoted
as current trace causality.

The generic contact-object lifecycle was already live-confirmed: TTL decrements
on the 30 Hz logic cadence and retires at zero. C12 reuses that lifecycle.

## Static causal result

### Correct health field

`s16 0x800A6594` is true player health. The older interpretation that called it
a separate mercy counter is obsolete. `0x800A7E2A` is the free-running HUD leaf
animation/pulse field, not health.

The direct writer boundary is:

- damage: `0x8004A888`, health minus one
- health-leaf pickup: `0x80058890`, health plus one
- 50-grain refill: `0x80055124`, health becomes four
- player initialization: `0x8005B30C`, health becomes four

No direct health serializer writer appears in the census, consistent with the
C02/C03 serializer boundary.

### Generic enemy-death producer

Inside `enemy_update_deathanim`:

- `0x800499A0` loads signed health.
- `0x800499A8` requires health below four.
- The RNG cursor at `0x800822F4` advances once for the test.
- The mask is `(2 << health) - 1`.
- A leaf spawns only when `(rng_byte & mask) == 0`.
- Enemy flag `record+0x5C & 0x40` suppresses this producer.
- `0x80049A10` allocates constructor 38 at enemy X, enemy Y minus `0x1000`, enemy Z, using profile 13.

The per-death odds are therefore:

| Health | Drop chance |
|---:|---:|
| 0 | 1/2 |
| 1 | 1/4 |
| 2 | 1/8 |
| 3 | 1/16 |
| 4 or more | impossible through this producer |

This is a once-per-retirement death-path decision, not a periodic mercy timer.

### Secondary numeric producer

Metadata constructor 50 has action 50 and retirement effect selector 23. Its
effect target is `0x80059D78`. That block always spawns constructor 58, then
checks health below four and makes an independent flat `1/8` test. On success,
`0x80059DEC` spawns constructor 38 at source Y minus `0x800` and records
bookkeeping id 29.

The player-facing name of constructor 50 is not established, so it remains a
numeric producer boundary. This does not hide an unbounded mechanism: the
constructor, action, effect, health gate, odds, spawn, and output are all pinned.

Native thrown-berry constructors are excluded. Rows 2, 5, 8, 11, 16, 45, and
48 use effect selectors 1, 2, 5, 4, 3, 9, and 8, not 23.

### Leaf metadata and collection

Constructor 38 at `0x80079714` is:

```text
0900c800d200000164006400d6ff0000e3808080
```

- action id: `9`
- TTL seed: `200` logic ticks
- untouched lifetime: about `6.67` seconds at 30 Hz
- radius contribution: `100`
- effective walker pickup radius: `400` scaled units
- flags: `0xE3`

The action-9 handler at `0x80058864` reads health, adds exactly one, and stores
the result at `0x80058890`. It dispatches sound 62 and bookkeeping `-4`.
There is no hard clamp in this handler. Ordinary spawn gates keep natural
sequential collection at the normal four-health boundary, but already-spawned
leaves are a separate edge.

The common collection tail writes state 7 and TTL 1 at `0x800589E0` and
`0x800589E4`; the generic lifecycle retires the record on the next logic tick.

## C acceleration

`tools/phase4_c12_static.c` reads the pristine PS-X EXE, verifies the row-38
signature, decodes constructor rows 38 and 50, resolves the action/effect jump
targets, emits selected instruction words, computes the health-indexed odds,
and performs a direct `0x6594` load/store census.

Transient C analyzers and ASM extracts were kept in `/tmp`. Important output
hashes are centralized in `analysis/phase4_c12_health_leaves.json`.

## Observation, inference, confirmation

| Class | Claim |
|---|---|
| Observation | Historical saves/movies show the health-leaf presentation and existing contact TTL cadence. |
| Inference | Constructor 50 likely has a recognizable gameplay name, but table shape alone is insufficient to assign it. |
| Causal/static confirmation | The exact heal, gates, RNG masks, odds, constructor ids, metadata, and teardown follow directly from pristine instruction/data bytes. |

## Why moving on is justified

The remaining work has minimal Phase 4 return:

- record a modern Interpreter natural-leaf oracle
- provoke an artificial multiple-already-spawned-leaf overfill test
- attach a player-facing name to constructor 50
- re-attribute the already live-confirmed shared TTL decrement instruction specifically to C12

None changes the core health-leaf contract. Reopen only if one of those edges
becomes material. No Interpreter movie is required now.

## Related

- [[SYS_health_leaves]]
- [[SYS_player]]
- `analysis/phase4_c12_health_leaves.json`
- `tools/phase4_c12_static.c`
