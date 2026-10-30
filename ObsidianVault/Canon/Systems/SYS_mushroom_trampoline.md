# Mushroom trampoline system

## Phase 4 B01 closure

B01 is **Substantiated Partial / bounded-exhausted** for valid mature type-5 mushroom contacts in pristine retail gameplay.

The contact handler at `0x8005C58C` requires matching contact identity and mature-state bit `0x0002`. Every qualifying ordinary contact assigns player vertical velocity `-3328`, mode `5`, contact `0`, timer `0`, and action `3`; it does not scale or add to incoming velocity.

Distinct mushroom identities append to a five-byte sequence. A duplicate still performs the normal bounce before resetting that sequence. Five distinct entries select a separate completion path: velocity `-16384`, transition `6`, fade timer `60`, bonus bit `1`, then shared effect identifier `15`.

The retained capsule supplies four qualifying contacts across four mushroom slots with differing incoming velocities and identical launch/recovery behavior. C static analysis proves no hidden coefficient, eligibility mutation, plant-position mutation, or shared-tail velocity overwrite in the bounded handler region.

Evidence: [[EXP_2026-08-03_phase4_b01_mushroom_trampoline]], `analysis/phase4_b01_bounded_exhaustion.json`, `analysis/phase4_b01_deep_confirmation.json`, and `analysis/phase4_b01_capsule.json`.
