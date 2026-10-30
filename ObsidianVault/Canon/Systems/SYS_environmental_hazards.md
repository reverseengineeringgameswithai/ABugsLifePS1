---
kind: system
id: SYS_environmental_hazards
status: partial
confidence: high
updated: 2026-08-02
phase4_row: E10
---

# Environmental hazards

## Confirmed shared architecture

Environmental hazards do not use one producer representation, but the covered
damage hazards converge on one resident outcome:

| Hazard family | Producer class | Damage caller |
|---|---|---|
| Rolling acorn | Actor contact | 0x8004B4A0 |
| Falling rocks | Contact-object pool | 0x80058A48 |
| Falling spikes | Contact-object pool | 0x80058A48 |
| Poison goo | Player/world collision | 0x80049740 |

Each calls the shared routine at 0x8004A700. It decrements signed player health
at 0x800A6594 by one. Result zero remains alive; only a negative result enters
the death branch. Nonfatal damage sets 0x800A6592 to +45 gameplay updates;
fatal damage sets it to -45 and arms the transition.

This is confirmed across six natural frame boundaries: two acorn contacts, one
rock contact, one spike contact, and two goo contacts. Goo's repeated hits are
90 emulator frames, or 45 gameplay updates, apart.

## Pit death and restoration

Pits are not ordinary damage contacts. Three independent levels show the same
health-independent lives-loss commit through the 0x8005B134 reset family:

- Restore live and previous player XYZ from safe anchor 0x800A6550/54/58.
- Restore health 0x800A6594 to 4.
- Decrement the lives byte at 0x800A65A0.
- Clear motion/transient state and preserve only power flag bit 0x20.
- Call collision reset 0x8004DC0C and clear contact transition state.

The Level 7 fixture keeps health at 4 while losing a life, directly disproving
the idea that pit death is implemented by draining health.

## Scope boundaries

- The Cliffside ground-bird kill zone belongs to
  [[SYS_bird_boss]] / [[EXP_2026-08-02_phase4_d17_bird]].
- Water, traffic, and thorn plants/barriers are not retail hazards.
- Webs and a campaign-wide census of other instant-kill regions remain open.
- The nearest rolling-acorn-fixture actor is id 10, but frame-boundary
  correlation is not enough to canonize that visual identity.

## Evidence

- [[EXP_2026-08-02_phase4_e10_hazards]]
- [Structured E10 result](../../../analysis/phase4_e10_hazards.json)
- [C capsule reducer](../../../tools/phase4_e10_capsule.c)
- [C static-ASM guard](../../../tools/phase4_e10_asm.c)

The retained capsules are frame-boundary evidence, not every-cycle traces and
not a claim of full E10 completion.
