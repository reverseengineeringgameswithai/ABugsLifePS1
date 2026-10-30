---
kind: system
id: SYS_seed_carry_plant_lifecycle
name: Seed carry, plant, uproot, and seed-as-weapon lifecycle
status: live_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_800B0D18
evidence:
  - EXP_2026-07-12_phase2_behavioral_oracle
  - analysis/phase2_final_action_pairs.json
  - analysis/phase2_carry_handstand_oracle.json
src_paths:
  - tools/phase2_final_action_pairs.py
---

# SYS_seed_carry_plant_lifecycle

The full life of a movable seed — pick up, carry, plant, uproot, or use as a
weapon — each step with a behavioural positive/negative pair on pristine media.
Complements [[FUNC_8005BDBC_plant_spawn]] (which colour/count produces which plant)
and the per-family behaviour notes ([[Brown_seed_plant_behaviors]],
[[Blue_seed_plant_behaviors]], [[Green_seed_plant_behaviors]]) with the *lifecycle*
itself.

A movable seed is a **chunk-31 actor record, id 11**, in the fixed table at
`0x8009FE04` (stride `0x84`: u32 id + s32 XYZ).

## Carry law — identity attachment

While held, the seed record's **X/Z equal the player's X/Z exactly**
(`0x800A6500`), with a **fixed Y offset**. It is a true attachment, not a
follow — there is no lag or spring. Dropping detaches it at the drop site.

## Plant / crack — spawner `FUNC_8005BDBC`

X-slam (`0x8004AF80` writes `0x10000` into seed+`0x6C`) drives the plant spawner.
Observed over a four-cycle pristine demo (`blue_seed_levels.movie`):

- A plant-slot **creation lands 20–120 frames after the Cross press**, in
  `0x80090BF0` (20 slots × `0x30`; `+0x00` u16 type, 0 = free), with the cursor
  `0x800822B8` advancing (wraps at `0x14`, skips occupied).
- The plant **type follows the selected colour** (the demo produced 7, 7, 6, 7 —
  the type-6 cycle follows a Triangle colour change).
- **Zero creations anywhere else** in 3795 frames, despite dozens of other inputs.

While a plant is alive, the seed rides its top: the record sits **exactly +20480**
(= 640 << 5) above its ground Y, at pinned X/Z.

## Uproot — Square at the grown plant

- The seed **descends from the plant top back to ground at pinned X/Z**, and the
  plant slot's type clears **40–170 frames after the Square press**.
- The seed record is **conserved** — the seed count never changes across a
  plant/uproot cycle; the same record is re-grounded.
- The expiry byte slot+`0x2E` is still **5** at a player uproot, distinguishing it
  from a natural wilt.
- Negative control: plants persist for 300–600+ frames in windows with no Square.

## Seed as a weapon — drop it on an enemy

Dropping a carried seed onto an eligible enemy kills it. The chain, measured
per-frame and **uninstrumented**:

1. Square → the **carry law breaks** (X/Z identity ends),
2. the seed travels **ballistically** toward the enemy,
3. **on its landing frame**, `enemy+0x6C := −20`,
4. that knockback **decays 0.5/frame**,
5. the enemy is **removed from the live actor table** (`0x80090748`).

Control (same point, no press): carry holds, `+0x6C` stays 0, the enemy persists.

**−20 is the signature.** It is written by exactly two arms — the carried-contact
arm `0x80058E14/18` (gated by contact kind `+0x27 == 4`) and its twin
`0x8004B2CC/D0` — the only `sh -20 → +0x6C` writers in `0x80040000..0x80060000`.
⚠️ The `jal 0x80050994` each arm makes is **`sfx_dispatch`** (the impact *sound*,
id `a0 = −4`), **not** a damage call; the damage *is* the `sh`.

## Method warnings (these cost real time)

- **Instrumentation perturbs this.** With any exec-breakpoint or watch armed, the
  seed drop **misses** the enemy — A/B proven. And `accessLog` / write-breakpoints
  never engage at all under the CachedInterpreter repro config. Measure the drop
  with plain per-frame state reads.
- **An execTrace watch armed during movie playback desyncs the replay.** Movie-lane
  evidence must be **poll-only** (state reads between advances), which is faithful
  and byte-deterministic. See [[EXP_2026-07-12_phase2_behavioral_oracle]].
- **Training's seed is carry-only BY DESIGN** (operator-confirmed) — it exists to
  teach pick-up/carry. Trying to crack it is a category error.
- A synthetic teleport + Square **never** attaches a seed (pickup has facing and
  proximity gates); reach a genuine carry state by replaying a fixture.

## Phase 4 A09 ownership correction (2026-08-03)

The movable-seed pickup/drop path is now resolved beyond the earlier behavioral law.

- `0x800A655C` is a `u32` selected-object offset. Positive movable-actor values are relative to `0x8009FD80`; LEVEL01 value `0x00000A50` selects actor `0x800A07D0`, id 11.
- `0x800A65A3` is a separate `u8` lift/carry/release phase. Movable pickup uses modes 8 through 12; stable attachment is mode 12; manual release writes transient mode 13.
- Pickup is a fresh Square edge with native actor flag, enable, state, 3D proximity, facing, and player-state gates. The identity writer is `0x80047858`; the mode writer is `0x80047874`; actor carried flag `0x40` is set at `0x80047888`.
- Stable carry is owned by actor update `0x8004BA38..0x8004BC10`: X/Z identity and seed `Y=player Y-19200`, with a separation bound that cancels invalid attachment.
- Manual drop is `0x80047C1C..0x80047D00`. It clears flag `0x40`, clears the selected offset, gives the seed outward motion, and enters transient mode 13.
- Manual release does **not** call `0x80046CAC`; the retained A09 capsule has zero passive block hits in that helper while all three manual drops take `0x80047CD4`.
- The fixture name `A09_seed_blocked_drop_LEVEL01` does not mean Square release is denied. The input release has no environment-obstruction gate; collision constrains the seed only after detachment.

The verified retained capsule provides three pickup/drop cycles, a 276-boundary stable no-Square carry control, and post-drop settling. The Training oracle independently confirms the stable attachment law in a second scene. See [[EXP_2026-08-03_phase4_a09_seed_pickup_drop]] and `analysis/phase4_a09_bounded_exhaustion.json`.
