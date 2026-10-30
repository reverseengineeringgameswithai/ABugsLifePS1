---
system: grasshoppers
phase4_row: D06_grasshoppers
status: substantiated-partial-bounded-exhausted
---

# Grasshoppers

## Confirmed retail behavior

- Tunnels grasshoppers are actor ID 15, spawn word `0x080f`, mover-VM program 8 at `0x8007760c`.
- All 19 descriptors in the pinned scene use that same actor/program pair. Ground, airborne/roof-entry, and carried-object appearances are states or spawn-subtype presentations, not separately implemented grasshopper actor classes.
- Program 8 combines a resident native initializer, pursuit/arrival, animation/state updates, a random `32..95` tick delay, random heading, and a parked movement state.
- Native selector 3 is Tunnels overlay function `0x800b3d78..0x800b3e84`. It turns toward the player and performs a one-time operation keyed by spawn-template byte `+0x0f`: it creates 24 kind-21 child/effect objects, changes vertical/scale and motion fields, and plays sound 102.
- Pursuit can advance naturally with no player input. Actor ID 15 is exempt from creation-time chase suppression and excluded from the generic hit-triggered aggro path.
- Grasshopper contact enters the common enemy-contact subsystem. Berry damage and death/respawn are also shared enemy systems; no grasshopper-only immunity gate was found.
- In bonus challenge 3, accepted blue-class kills of actor ID 15 build the streak. The fifth accepted kill sets bonus flag bit `0x04` and transition latch 6.

## Limits

The exact visual names for spawn-template subtypes and the kind-21 children are not assigned. A per-berry outcome matrix belongs to shared row D04. These bounded presentation/outcome gaps do not prevent use of the family-level findings above.

Evidence: [[EXP_2026-08-04_phase4_d06_grasshoppers]] and `analysis/phase4_d06_grasshoppers.json`.

