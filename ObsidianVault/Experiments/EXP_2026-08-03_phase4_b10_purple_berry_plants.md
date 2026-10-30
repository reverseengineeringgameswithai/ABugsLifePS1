---
kind: experiment
id: EXP_2026_08_03_phase4_b10_purple_berry_plants
created: 2026-08-03
updated: 2026-08-03
phase: 4
row: B10_purple_berry_plants
status: substantiated_partial
confidence: high
disposition: bounded-exhausted-move-on
---

# Phase 4 B10 - purple berry plants

## Disposition

**B10 is substantiated Partial and bounded-exhausted.** The four tier grants, plant producer, contact-object lifecycle, equip writes, overwrite behavior, throw persistence, and level-load reset are closed. The retained capsule supplies all four natural positive controls, while C analysis of the hash-verified pristine executable supplies exact instruction and branch attribution.

No DuckStation replay or new Interpreter movie is required. Remaining strict-Full work is campaign/presentation/reset breadth with minimal expected return.

## Scope and overlap

B10 owns the purple seed lane's route from selected tier to a type-6 plant, grant-object constructor, contact action, and equipped berry byte. A13 owns generic output selection and timeout. A08 and C07-C10 own thrown projectile behavior and enemy damage after a berry is equipped. The generic contact allocator/walker is shared with E06.

## Method

The Phase 4 acceleration order was followed:

1. Validate and query the relevant retained capsule.
2. Reconstruct exact frame-boundary RAM around all four equip changes.
3. Reduce the player/contact snapshots with C.
4. Analyze the pristine executable with C for the pair table, type-6 handler, metadata, dispatch table, action handlers, equip writer frontier, throw path, and level initialization.
5. Escalate live only if a named domain remains missing.

Python was used only through the official trace-capsule reader to reconstruct retained evidence. All repeated comparison and pristine ASM analysis logic was implemented in C.

## Capsule acceptance

- Capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/A13__purple_seed_levels`
- Manifest SHA-256: `c86cb9e2baeff56d10d2d6d09b1a63ba1b11904546e93d0add39519478db5b5e`
- Movie SHA-256: `6dd25c666bdd8040a84e62b1ebeb9bbe33100f151f4534773c8043d79cc31176`
- Start-state SHA-256: `a78f53720ed38902f38c4a6c7b35406b30013dba51a41d791d66df56a4df5d79`
- Pristine executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- Identity: pristine `SCUS-94288`.
- Capture: 2,316 frame states, 78,903,390 passive blocks, 571,789,014 instructions.
- Manifest reports `complete=true`, `truncated=false`, and `error=""`.
- Independent control mismatch map is empty.
- Capsule and control fingerprints match exactly for full machine state, RAM, registers, SPU RAM, and VRAM.

The capsule is frame-boundary/passive-block evidence. It is not used for exact instruction attribution, and no `execTrace` claim is made from it.

## Observation: four natural equip transitions

Exact offline reads of `0x800A6590..0x800A659F` establish:

| Purple selector | Emulator frame | Equip transition | Result |
|---:|---:|---:|---|
| `0x14` | 133396 | `0 -> 1` | Blue/Super |
| `0x24` | 133920 | `1 -> 2` | Green/Homing |
| `0x34` | 134486 | `2 -> 4` | Purple/Mega Homing |
| `0x44` | 135204 | `4 -> 3` | Gold |

These correct the historical note's one-frame-later approximations. The equip byte is `u8 0x800A6597`; purple selected/available nibbles are at `0x800A659B`.

The C reducer compared the complete 64-slot contact pool across each boundary. Every equip change had exactly one changed grant record with the matching action:

| Equip result | Action | Contact slot | Collection transition |
|---:|---:|---:|---|
| 1 | 35 | 39 | count `185 -> 1` |
| 2 | 33 | 38 | count `194 -> 1` |
| 4 | 36 | 21 | count `200 -> 1` |
| 3 | 34 | 32 | count `185 -> 1` |

All four records are in common state 7 with flags `0xE2`, radius add 100, and auxiliary timer 240. The first collected record remains at count 1 through frame 133397 and is inactive by frame 133398, two video frames after the equip write.

## C-based pristine ASM confirmation

### Tier table

The purple lane occupies four entries in the resident 20-pair table:

| Tier | Pair address | Plant type | Extra | Constructor formula result |
|---:|---:|---:|---:|---:|
| 1 | `0x8007A478` | 6 | `0x4000` | 35 |
| 2 | `0x8007A47C` | 6 | `0x2000` | 33 |
| 3 | `0x8007A480` | 6 | `0x1000` | 32 |
| 4 | `0x8007A484` | 6 | `0x3000` | 34 |

All four tiers therefore grow the same type-6 carrier plant; only its extra field changes.

### Deterministic one-shot producer

The type-6 handler is `0x8005C6F0..0x8005C740`. Admission requires:

```text
(u32(slot + 0x2C) & 0x000A0000) == 0x00020000
```

It derives the constructor as `(signed(slot+0x2E) >> 12) + 31`, calls contact allocation at `0x8005C728 -> 0x80059E44`, uses metadata-A index 3, and spawns at plant X, plant Y minus `0x1400`, plant Z. No RNG participates.

After allocation, `0x8005C738..0x8005C740` sets bit `0x0008` in slot `+0x2E`. That changes the admission-mask result and prevents the same plant instance from producing another grant. This is a deterministic one-object activation, not a cadence roll.

### Contact metadata and collection

Constructors 32-35 share the following metadata:

- Initial countdown: 230 logic ticks.
- Auxiliary timer: 240.
- Radius add: 100, producing effective walker radius `300 + 100 = 400`.
- Common collection state: 7.
- Flags: `0xE2`.

The uncollected lifetime is approximately 7.67 seconds at the 30 Hz logic rate. On overlap, the walker selects `action_id - 2` from dispatch table `0x8001B570`, writes the equip byte, plays the tier-specific pickup sound, and enters the common collection tail.

| Constructor | Action | Handler | Equip | SFX |
|---:|---:|---:|---:|---:|
| 35 | 35 | `0x80058968` | 1 | 53 |
| 33 | 33 | `0x80058940` | 2 | 54 |
| 32 | 36 | `0x80058978` | 4 | 55 |
| 34 | 34 | `0x80058954` | 3 | 56 |

Collection directly overwrites `0x800A6597`; there is no inventory stack, same-tier denial, or compare-before-store in these handlers.

### Equip lifetime and reset

The accepted throw path at `0x80047160..0x8004725C` reads player `+0x97`, validates native indexes 0-4, maps them to projectile classes, and spawns the projectile. It contains no write to equip. Throwing therefore does not consume or reset a B10 berry selection.

Level initialization at `0x80046B68` calls the bulk clear on player base `0x800A6500` for `0xA8` bytes. This range includes `0x800A6597`, restoring default/red equip 0 on level load. A later native grant can overwrite the byte at any time. The direct writer census also found a separate native assignment family at `0x8005428C..0x800542DC`; its broader source semantics are outside B10 and are not renamed here.

## Observation, inference, confirmation

- **Observation:** Four capsule frames show `0 -> 1 -> 2 -> 4 -> 3`, each accompanied by exactly one matching contact action and collection-tail transition.
- **Causal confirmation:** Pristine instructions fix all tier pairs, constructor formula, one-shot bit, action dispatch targets, equip stores, sounds, throw non-write, and level-load clear.
- **Inference kept bounded:** Shared metadata plus the already-confirmed contact countdown supplies uncollected lifetime; the movie does not leave every tier uncollected to visual expiry.

## Bounded-exhaustion decision

Resolved:

- All four tier-to-constructor/action/equip mappings.
- Natural runtime control for every tier.
- Spawn gate, position, deterministic one-shot behavior, and lack of RNG.
- Contact radius, countdown, flags, sounds, collection tail, and retirement.
- Direct overwrite semantics.
- Persistence across throws.
- Level-load reset.

Strict Full would still add a campaign-wide visible type-6 model/instance census, four separate uncollected-expiry visual controls, paired ordinary-respawn/scene-reload persistence controls, and exact GPU ownership of the shared berry-icon animation. Those are breadth and presentation questions; none changes the B10 mechanic now instruction-bound and naturally observed. Keep Partial for evidence-breadth honesty, bank the limitation, and move on.

## Transient evidence and commands

Official reader shape:

```bash
python3 ~/duckstation/scripts/debugger-client/trace_capsule_query.py \
  "$CAPSULE" read --frame FRAME --domain ram --offset OFFSET --length LENGTH
```

Important query outputs:

| Artifact | SHA-256 |
|---|---|
| `/tmp/phase4_b10_equip_changes.json` | `dd7f34762bf853f54249c93935bfa3f074a02af76c98af707321af836cf01d30` |
| `/tmp/phase4_b10_selector_changes.json` | `8a2518ae4a2d9c6aa4f4f20898cc689f1f287943e624ff0efa83d9c4f3007fec` |
| `/tmp/phase4_b10_capsule_reduce.c` | `44190979fa9a06ee6e981fcadabd78e9d775feb164575ec82ae5b0fcf3ac9bd0` |
| `/tmp/phase4_b10_capsule_reduce` | `896fc84d8a92a12527c972a361976a393a3ead4d758fdaddfaf61b5f2b92088a` |
| `/tmp/phase4_b10_capsule_reduce.out` | `338d1800a684502a1d90ebc97607ee1c3447d57d6b89db78e56b65e60b18ba52` |
| `/tmp/phase4_b10_static.c` | `5984aae6fdcc34b6ae8bf94b1207dbbce34abf7249f244ae0f34d16d48626ce4` |
| `/tmp/phase4_b10_static` | `2dad7cdca04d304e165f4c04eb6cd73cf35421f50d4ffd535cce4e423fb1c2ac` |
| `/tmp/phase4_b10_static.out` | `d1e0c9e4a7b4f0cb1cd8451d0fc2de43edac8bade0e2b4bb2cf6b7f48555c65d` |

Representative contact snapshot hashes are `46a26c561b206136b08d55972cae27b8d777deb16e1fb716f0c73151ec475e0f` before tier-1 collection and `6ae03a470b8067d6cfaead78596908f72d144889130308db7a1581f6a416abc8` after it. All transient snapshots remain under `/tmp`; no movie, save, capsule, or copyrighted binary is added to the repository.

## Durable links

- [[SYS_purple_berry_plants]]
- [[Purple_seed_plant_behaviors]]
- [[Seed_plant_output_binding]]
- [[SYS_berry_projectile_and_homing]]
- [[EXP_2026-08-03_phase4_a13_bounded_exhaustion]]
- `analysis/phase4_b10_purple_berry_plants.json`
