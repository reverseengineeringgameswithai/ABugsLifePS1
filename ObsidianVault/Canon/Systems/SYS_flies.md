# Horsefly / FLY enemy

## Scope and identity

Phase 4 row `D08_flies` is the fat brown flying enemy with large red eyes. The retail identity is actor ID `6`, chunk-31 type word `0x0F06`, with `CHARS/FLY.ALL` and `CHARS/FLY.ANM`. It is not the dragonfly, mosquito, bee/wasp, or Thud.

The family binds to mover program `0x800776D0` and callback `0x8004A144`. The callback is shared and only emits positional sound ID 40 while actor field `+0x44 < 2`; it is not a Horsefly attack routine.

## Movement and attack

The complete Horsefly mover program is:

1. `set_byte_params[-64,-64]`
2. `anim_clip_load[0,2]`
3. `wait_random[63,32]`
4. `random_dir_step`
5. `park_seek`
6. `jump_back[5]`

There is no player-proximity, native-call, chase, or projectile opcode. The Horsefly wanders and damages Flik through the ordinary actor-contact resolver; there is no separate family aggro/strike state to find. In the retained D08 movie, contact at movie frame 190 executes `0x8004B650` once, stores reaction 15 at actor `+0x6C`, and follows the shared D03 player-damage/knockback law.

## Damage and temporary KO

The accepted projectile path stores reaction 20 at `0x80058ED8`, dispatches damage from projectile marker `+0x2C`, and stores HP at `0x800590E4`. Marker damage is shared: `0/12 -> -2`, `1 -> -99`, `127 -> -4`, `128 -> -3`, default `-1`. Actor flags `+0x5C & 0x40` are the shared resistance gate; the observed Horsefly is not resistant.

The accepted capsule records two hits: HP `8 -> 6` at movie frame 426 and `6 -> 4` at frame 472. The movie name says `contact_kill`, but the recording does **not** kill the Horsefly; it ends alive at 4 HP.

A bounded post-movie continuation supplied two more natural Square throws. HP changed `4 -> 2 -> 0`; the lethal hit then:

- writes the 999 temporary-KO sentinel at `0x800592A8`;
- clears actor `+0x60`;
- transforms flags with `| 0x0880` and `& ~0x0002`;
- redirects `+0x70` to `0x800776AC` at `0x800592C8`;
- calls `0x800498AC(actor, 1)`.

Program `0x800776AC` is `park_arrive_stop; jump_back[1]`, explaining the live `0x800776AC/AE` alternation. Death class `s7=1` branches around the `s7>=2` effect/quota-decrement block, so no write to enemy quota `0x800A658E` and no immediate slot deletion are expected for this blue-berry temporary KO. Respawn ownership is the shared D05 retirement/reinstantiation system, not a Horsefly-specific routine.

## Campaign variants

The Phase-1 census contains 22 actor-ID-6 records across the complete named scope:

| Stage | Instances | Mover/callback | Pose/model pointer |
|---|---:|---|---|
| Riverbed Run (`stage05`) | 4 | `0x800776D0` / `0x8004A144` | `0x80137B4C` |
| City Entrance (`stage07`) | 9 | `0x800776D0` / `0x8004A144` | `0x8010F798` |
| City Square (`stage08`) | 9 | `0x800776D0` / `0x8004A144` | `0x800CF480` |

One active City Square instance is parked at `0x800776E4`, an instruction inside the same `0x800776D0` program. The named stages vary pose/model data, not family mechanics.

## Evidence and boundary

- `analysis/phase4_d08_static.json`
- `analysis/phase4_d08_evidence.json`
- `src_re/fly_actor_id6.c`
- [[EXP_2026-08-04_phase4_d08_flies]]

`D08_flies` is a substantiated partial and bounded-exhausted move-on row. Remaining per-berry visuals, gold-kill effect presentation, exact per-instance respawn delay, and animation/audio naming are shared-system or presentation breadth with poor return. Reopen for a contradictory actor-ID-6 variant or a named Horsefly-specific drop/respawn question. No new Interpreter movie is required for the current closure.
