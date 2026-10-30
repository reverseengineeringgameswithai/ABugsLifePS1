---
kind: memory
id: MEM_8009FD80_enemy_actor_pool
aliases: [MEM_8009FD80_enemy_actor_pool]
name: Enemy actor pool
status: partial
canonical_address: false
primary_address_note: MEM_8009FD80_actor_pool
confidence: confirmed_layout_partial_fields
source_state: original_game
memory:
  - 0x8009FD80
---

# Enemy actor pool at `0x8009FD80`

The pool contains 40 records with stride `0x84`. Actor ID is at `+0x00`; XYZ position begins at `+0x04`; X velocity at `+0x1C` and Z velocity at `+0x24` are confirmed.

## Correction history: `+0x20` was initially left unnamed

A 2026-08-02 Phase 4 D02 C analysis reconstructed six valid retained capsules across 2,895 frames and 77,071 active actor samples. Confirmed X/Z controls matched approximately 94% of moved frames, while `+0x20` matched Y displacement only 61/1,431 times. Therefore `+0x20` is not the direct Y-delta counterpart implied by field symmetry. It spans negative and positive values and is not padding, but its positive semantics require exact writer/reader attribution. See [[EXP_2026-08-02_phase4_d02_actor20]].

That first pass correctly rejected a symmetry-only name, but its conclusion that the
field remained unnamed is superseded. The retail instruction and attributed runtime
access pins below establish signed Y velocity; collision integration explains why a
frame-boundary Y delta need not equal the final sampled velocity.

## Confirmed record field: `+0x20 velocity_y` (2026-08-02)

The 40-record pool at `0x8009FD80` uses an `0x84`-byte stride. The motion triplet is now confirmed:

| Offset | Meaning | Evidence |
|---:|---|---|
| `+0x1C` | signed X velocity | prior capsule/control correlation |
| `+0x20` | signed Y velocity | Interpreter access trace plus retail ASM below |
| `+0x24` | signed Z velocity | prior capsule/control correlation |

Retail code establishes `+0x20` independently of layout symmetry:

- `0x8004BF14..0x8004BF38` and `0x8004CF34..0x8004CF50` add gravity step `+0x100` and clamp at `+0x1000`.
- `0x8004BFA4..0x8004BFB0` and `0x8004CF54..0x8004CF6C` add the field into actor Y at `+0x08`.
- `0x80049E00..0x80049E0C` initializes airborne motion to `-0xD00` or `-0xB60`.
- `0x8004C04C` and `0x8004D02C` clear the field on settle/collision result paths.
- Generic vector math observes the word as the `+4` component of the XYZ vector rooted at actor `+0x1C`.

Sign convention in these paths is negative/upward and positive/downward. Do not equate a frame-boundary `deltaY` with the sampled final `velocity_y`: collision integration can consume, cap, correct, or clear the velocity within an update.

Runtime provenance: Interpreter movie v4 `D02.movie`, clean/armed cycle delta 0 and identical full-RAM SHA-256, 1,991 untruncated accesses across 23 instruction sites. See `[[EXP_2026-08-02_phase4_d02_actor20]]` and `analysis/phase4_d02_actor20_runtime.json`.

### `+0x20` deep-audit precision

All 813 runtime writes and all 1,178 runtime reads from the accepted Interpreter trace have named roles; no access site remains unexplained. One control-flow wording correction applies: `0x8004D02C` is the delay slot of the branch at `0x8004D028`, so its zero store executes for either branch outcome once that path is reached. It is a path-level velocity clear. The `0x8004C04C` store remains a genuinely conditional near-zero settle clear selected by `abs(velocity_y) < 2`.

The remaining unknowns are only numeric representation scale and species-specific scheduling cadence. These do not weaken the confirmed `velocity_y` name. See `analysis/phase4_d02_actor20_deep_audit.json` and `tools/phase4_d02_actor20_semantic_guard.c`.

### Independently corroborated, 2026-08-03

`SYS_propeller_plant`'s own investigation — unrelated fixture, unrelated methodology —
independently found a propeller lift mechanic subtracting `512` from actor `+0x20` per
qualifying tick, consistent with this page's own sign convention (negative = upward). A
fresh, independently-scripted live re-sample of `D02.movie.json` reproduced the exact
airborne-impulse-plus-one-gravity-tick arithmetic (`-3328+256=-3072`) and the actor-removal
event, without reusing the original accessLog capture. See
`analysis/phase4_d02_actor20.json`'s `INDEPENDENT_VERIFICATION_2026-08-03`.

## The pool drives model loading (E05, 2026-08-03)

At level load, `level_load_chunks` (0x8005DAD0) walks this pool's 64 slots and
dispatches each record's id (+0x00, valid 1..41) through the jr table at
0x8001BBDC — each case hardcodes the model path and loads it via
`level_chunk_loader` (0x8005D654), persisting the pointer at
**0x800A6300 + 4*id**. The full id→path table and 16-level live confirmation:
[[SYS_actor_model_loading]], `analysis/phase4_e05_model_binding_static.json`,
`analysis/phase4_e05_model_pointers_live.json`. Note id 11's model is
`bits\seed` (dedicated loader 0x8005D924) — the plantable seed actor.
