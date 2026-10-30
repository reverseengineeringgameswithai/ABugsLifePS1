---
kind: experiment
id: EXP_2026_08_03_phase4_b11_blue_berry_shooter
created: 2026-08-03
updated: 2026-08-03
phase: 4
row: B11_blue_berry_shooter
status: substantiated_partial
confidence: high
disposition: bounded-exhausted-move-on
---

# Phase 4 B11 - blue berry shooter

## Disposition

**B11 is substantiated Partial and bounded-exhausted.** Yellow tier 1 is plant type 14. It fires deterministic three-shot volleys through the shared ballistic target helper, constructs contact-object type 66, and produces non-homing weak/class-2 model-110 shots. The dedicated retained capsule closes cadence, natural damage, ownership, and retirement; the yellow ladder closes the plant-instance lifetime.

No new DuckStation run or Interpreter movie is required. Remaining strict-Full work is campaign/species/presentation breadth and does not justify another standalone B11 pass.

## Evidence method

The Phase 4 acceleration order was followed:

1. Validate the dedicated B11 and A13 yellow capsules.
2. Query exact frame-boundary RAM with the official capsule reader.
3. Reduce plant, contact-pool, enemy, HP, quota, and player-counter snapshots in C.
4. Analyze the hash-verified pristine executable in C for the pair table, handler dispatch, firing branches, spawn arguments, and metadata row.
5. Escalate live only if a named missing domain remains.

Python was used only by the official offline capsule reader. Repeated reconstruction comparisons, cadence discovery, impact attribution, lifecycle reduction, and pristine ASM analysis were performed in C.

## Capsule acceptance

### Dedicated engagement control

- Capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B11_blue_shooter_enemy`
- Manifest SHA-256: `c67118a60d2ce90d93609b87c1f9eecea4613d63f3bcedaa85cdfa3d2aabb2fa`
- Movie SHA-256: `7ae34afff0afa72e1eb313e76f6346fe132754c57bd117d6e970495260f5eb69`
- Start-state SHA-256: `22a8f9adb7c6f76731ce33025e8853d5e2b3aff032459d98aa6bd709109e82aa`
- Frames `112997..113628`, 632 frame states, 21,973,648 passive blocks, and 155,263,193 instructions.
- `complete=true`, `truncated=false`, `error=""`, pristine `SCUS-94288`, and empty control mismatch map.
- Capsule and control fingerprints match for machine state, RAM, registers, SPU RAM, and VRAM.

### Yellow ladder control

- Capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/A13__yellow_seed_levels`
- Manifest SHA-256: `03b5872a5bb7ecbdd21c32ffe14c20675ebbef2ff5c98600a4940b473dd89afc`
- Movie SHA-256: `a694c08034893a52f1cbf924cab06f4fb57417cc5e4aff8f8377761e6272c087`
- Start-state SHA-256: `1f00b97137698fe37d7c0a8af31de9eca88574c284769de407d6bad11234e9ce`
- Frames `262374..265797`, 3,424 frame states, 110,475,927 passive blocks, and 847,185,107 instructions.
- Complete, untruncated, error-free, pristine-media, with matching control fingerprints in every retained domain.

The pristine executable SHA-256 is `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

The capsules are frame-boundary/passive-block evidence. Exact instruction claims below come from the pristine executable, not passive block ordering.

## Corrected binding

Yellow tier 1 pair `0x8007A488` is plant type 14 with extra zero. The plant handler table at `0x8001B848` is indexed by `plant_type - 2`, not raw plant type:

```text
type 14 -> index 12 -> entry 0x8001B878 -> handler 0x8005CA7C
```

An initial transient probe printed raw-type-indexed table labels and was rejected immediately. The corrected C pass and raw handler instructions are the evidence used here.

## Targeting and three-muzzle geometry

Handler `0x8005CA7C` first requires plant state `s16 +0x02 == 2`. It fires only when the phase at `+0x04` equals one of three values:

| Phase | Muzzle origin relative to plant | Authored heading |
|---:|---|---:|
| `0x00010000` | `X - 0x22A4, Y - 0x5400, Z - 0x1400` | `0x0AAA` |
| `0x00030000` | `X + 0x22A4, Y - 0x5400, Z - 0x1400` | `0x0555` |
| `0x00050000` | `X, Y - 0x5400, Z + 0x2800` | `0x0000` |

Every muzzle calls shared ballistic helper `0x80046D24` with control/cone value 512. That helper selects the nearest eligible enemy in the muzzle heading cone, requires actor state bit `0x1`, excludes state bits `0xA0`, and calculates bounded lead. If no valid target is available, the authored heading survives and vertical velocity is `-2048`.

The shooter is aimed only at launch; metadata flags `0xE5` do not contain homing bit `0x08`. Velocity uses the shared sine-table ballistic construction and gravity 128. There is no midflight reacquisition or steering.

## Exact firing cadence

The dedicated plant slot changes from empty to type 14 at frame `113039`. The first shot is allocated at `113229`, exactly 190 video frames later.

Each volley contains three shots:

- Shot spacing: 8 video frames, or 4 logic ticks.
- Volley-start spacing: 96 video frames, or 48 logic ticks.
- RNG: none.
- Post-spawn event: 36.

Exact retained allocations:

```text
113229, 113237, 113245
113325, 113333, 113341
113421, 113429, 113437
113517, 113525, 113533
113613, 113621, [113629 lies one frame beyond the capsule]
```

At every retained shot frame, C finds exactly one new timer-100 subtype-13 record and the matching plant phase `1`, `3`, or `5`.

## Constructor, class, model, and ownership

The handler passes **type 66** to `contact_object_spawn` at `0x8005A0E0`. Metadata row 66 is:

```text
020064006e000001320032000d000001e5002080
```

Decoded fields:

- Collision/damage class: 2.
- Spawn timer: 100 logic ticks.
- Model: 110.
- Two radius fields: 50 and 50.
- Subtype/state: 13.
- Flags: `0xE5`, non-homing.
- Record byte `+0x27`: 0, not the mine/permanence lane.

This resolves the old ambiguity: B11 constructs **spawner type 66**, which materializes a **class-2** record using model 110. Model 110 is presentation; it does not make the shot blue/super damage class 5. The projectile therefore inherits the weak/red-class resistance gate.

The shooter calls the shared allocator directly and never increments player-owned count `u8 0x800A6596`. That counter stays zero across the entire dedicated movie. B11 shots do not consume Flik's four-projectile allowance and are not player-owned for capacity accounting, even though they use the friendly contact-vs-enemy damage lane.

## Natural damage and permanence control

The sole side-HP-table change occurs at frame `113395`:

| Field | Before | After |
|---|---:|---:|
| Enemy-id-37 HP column 0 | 98 | 96 |
| Target actor `+0x6E` | 2 | 999 |
| Target state | `0x00004011` | `0x00004891` |
| Permanent quota `0x800A658E` | 9 | 9 |
| Player-owned shots `0x800A6596` | 0 | 0 |
| Equipped berry `0x800A6597` | 0 | 0 |

The target is damageable-table entry 0 at `0x8009FD80`. Subtype-13 contact slot 48 is live at frame `113394` and absent on the damage frame. The hit applies the generic hardcoded `-2` side-table delta and ordinary temporary-death transition. It does not decrement the permanent-kill quota.

This one weak enemy reaches its terminal local value from a single shot because its local counter was 2. It does not support a claim that B11 instantly kills every enemy.

## Retirement

Two natural retirement controls are present:

- **Enemy impact:** slot 48 disappears at frame `113395` with the damage event.
- **Floor intersection:** a missed shot from frame `113229` counts down normally to 60, then its timer is forced to zero at frame `113311`, well before natural timer expiry. Its final position/velocity are frozen while the inert record awaits shared cleanup.

The common non-homing contact path also has timer-expiry, far-distance, and required-flag retirement branches. B11 does not add a separate retirement scheduler.

## Plant-instance lifecycle

The A13 yellow capsule supplies exact allocation and clear boundaries for its type-14 slot:

```text
262517: prior slot contents
262518: type 14 allocated
263187: type 14 still active
263188: type 14 -> 0
```

The natural plant-instance lifetime is exactly 670 video frames, or 335 logic ticks, in this control. This replaces the legacy approximate `~666f` statement.

## Observation, inference, and causal confirmation

- **Observation:** exact capsule frames establish the volleys, natural hit, `-2` HP, temporary death, player-count independence, impact/floor retirement, and 670-frame plant lifetime.
- **Causal confirmation:** pristine instructions establish type-14 binding, the three phase gates, muzzle geometry, target-helper call, type-66 constructor, row-66 metadata, lack of RNG/homing/player-count increment, and permanence byte zero.
- **Bounded inference:** campaign-wide availability and species breadth are not inferred from one fixture; weak-class immunity behavior is delegated to the existing berry-resistance rows.

## Bounded-exhaustion decision

Resolved for B11:

- Exact tier, type, table index, and handler.
- Target predicate, lead/fallback behavior, and all muzzle geometry.
- First-fire delay, intravolley spacing, and repeat cadence.
- Exact spawner type, record class, model, timer, subtype, flags, and gravity.
- Friendly ownership and no use of Flik's projectile counter.
- Natural damage delta and non-permanence.
- Impact and floor retirement.
- Exact natural plant lifetime.

Strict Full could add a campaign-wide type-14 instance/model census, a live no-target control, every resistant enemy family, every generic cull path, and exact GPU/audio presentation ownership. None changes the B11-specific law now established. Keep Partial for breadth honesty, bank the limitations, and move on.

## Transient analysis artifacts

| Artifact | SHA-256 |
|---|---|
| `/tmp/phase4_b11_static_v2.c` | `219ffd68555768821804fe78f48c5019531fce47fe16a6ed8bae240f1c3c4911` |
| `/tmp/phase4_b11_static_v2` | `3a7dcc8f431ecc6b09a6d9ca628bc0b28f3dcc81a2ec147caa33691adab278ca` |
| `/tmp/phase4_b11_static_v2.out` | `2149bf97d3330e1e8f637f813d6f21e58041911d4d2979c053ab4205127fc274` |
| `/tmp/phase4_b11_static_v3.c` | `9cbacec3059fb790bbf93b822c1b0829c11e49059f2ba90f776f7acee130f399` |
| `/tmp/phase4_b11_static_v3` | `54ee3124965536d2a4dd3de40e815bdd6b42a0e4309eac70fb27cc70803b0610` |
| `/tmp/phase4_b11_static_v3.out` | `4bcdf1f67769a667352740788eadcbd3ce362db03288275f9e8a8e8562393e68` |
| `/tmp/phase4_b11_capsule_sample.c` | `c3a952cc3427f9fccb5c88561f42a5014fcf4a823e23be35279214be3bde7468` |
| `/tmp/phase4_b11_capsule_sample.out` | `b2f181e7784ea36f914f0b349c33fc705aa877a393cbb4b1eeb6ce5d9f49006b` |
| `/tmp/phase4_b11_exact_reduce.c` | `61d5871130cc32fe73e21e1604260f8b782c856a5f832abe20f657f7797b1c5a` |
| `/tmp/phase4_b11_exact_reduce.out` | `1ec15d8074c691a6f58c7b2c1828f9bfde032a336f75288137a9234f8d97997d` |
| `/tmp/phase4_b11_impact_reduce.c` | `3f18a508d38193cf45fc0c2e76c0186bf83fbdeeac6a42b740617fa64de07eff` |
| `/tmp/phase4_b11_impact_reduce.out` | `e2fa1cc110b8093fe6abd12a71f30bccae56ee74c8dac922ac233cd1007184de` |
| `/tmp/phase4_b11_lifecycle_reduce.c` | `e3e5b7314dfcad5c8b6987dcdf0f1f943d027a02e6f0f5e69f61c589cddcc5aa` |
| `/tmp/phase4_b11_lifecycle_reduce.out` | `cbc9f9cfe61a1b5eacc41c12269a4030968450c2f0bce91ee8f73d45df5b1557` |

Supporting offline outputs include HP changes SHA-256 `5e23baf5768c758350b2e44ff2d56bff28ecc5c38c621721e6683895ff0dc712`, owned-counter changes `8fac89c32e1a4721730ccc2ffb7471a1d5f9877c08c8cd5b6dd6fc7dd1540581`, and yellow slot-3 changes `9031b44c5bba9d8178fe635bfae24ed39ecc9f19d42c9d8c47f8feee67ead312`. Transient RAM/contact snapshots remain under `/tmp`; no capsule, movie, save, or copyrighted binary is added to the repository.

## Durable links

- [[SYS_blue_berry_shooter]]
- [[Yellow_seed_plant_behaviors]]
- [[SYS_berry_projectile_and_homing]]
- [[Seed_plant_output_binding]]
- `analysis/phase4_b11_blue_berry_shooter.json`
