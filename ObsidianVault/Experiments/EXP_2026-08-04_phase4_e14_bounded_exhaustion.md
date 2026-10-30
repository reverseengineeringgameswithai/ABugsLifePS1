---
kind: experiment
id: EXP_2026-08-04_phase4_e14_bounded_exhaustion
status: complete
source_state: original_game
system: [MEM_80089938, SYS_menu_and_frontend, FUNC_80055478]
row: E14_frontend_save
---

# Phase 4 E14 frontend/save bounded exhaustion

## Disposition

E14 is **substantiated partial and bounded-exhausted; move on**. It is not
strictly solved under the full Phase 4 scorecard. No additional Interpreter
movie is required for this disposition.

The August 3 pass mapped the 348-byte save ABI and the 64x5 table, but its open
list contained three claims that static C analysis can now close:

- values above 100 did not have an unidentified increment writer;
- `0x80054644` was not a frontend sentinel scan;
- the CHASE direction did not require a new live A/B once the independent enemy
  AI flag binding was joined.

The old artifact remains historical evidence. The machine-readable superseding
packet is `analysis/phase4_e14_bounded_exhaustion.json`.

## Capsule-first preflight

No E14 trace capsule exists under the declared Phase 4 external-evidence root.
The named missing domains were instruction ownership and MEMORY.BIN static
effects, which resident/overlay reconstruction answers directly. A live replay
would not strengthen the closed writer census, so DuckStation was not launched.

## C whole-image table census

Transient C analyzer `/tmp/e14_table_census.c` followed MIPS `lui 0x8009`
materializations through indexed `addu` expressions across the pristine EXE and
all `.BIN` images under `REBUILD/files`.

Result:

| Domain | Loads | Stores | Total |
|---|---:|---:|---:|
| Resident executable | 20 | 12 | 32 |
| All raw `.BIN` images | 0 | 0 | 0 |

The resident writer frontier is exhaustive at useful Phase 4 resolution:

| Writer | Exact effect |
|---|---|
| `mover_init_from_record` `0x80049D3C` | Applicable values below 64 are clamped up to 64. |
| `actor_player_contact_resolver` `0x8004B2A8/0x8004B318` | Two `-2` lanes, guarded at 65. |
| `actor_player_contact_resolver` `0x8004B4F4` | `+2` while the old value is below 200. |
| `type_0x3f...` `0x80054690` | Lazy old-column to new-column copy, 64 rows. |
| `contact_walker` `0x80058AB4` | The same lazy column-copy law. |
| `scene_config_apply` `0x800555DC..0x8005561C` | Copy five bytes for each of 64 rows from config/save data. |
| contact-vs-actor tail `0x80059384` | `-2` while the old value is at least 33. |

This corrects the old `unlocated increment source`: `0x8004B4F4` is the source.
The caller snapshots true health `0x800A6594`, invokes ordinary contact damage
at `0x8004B4A0`, rereads health, and adds 2 only if health changed. Values such
as 110 are therefore native output, not unexplained save noise.

## Adaptive encounter-state law

The table is not universally enemy HP. It is a persistent per-actor-species,
per-native-berry encounter score:

- a successful enemy body hit on Flik moves the current entry `+2`;
- several Flik-to-actor hit/KO lanes move it `-2`;
- `mover_init_from_record` clears actor flag bit `0x2` at score `>=100`, except
  actor ID 15;
- the landed-hit path sets bit `0x2` below score 120 when metadata byte `+0x11`
  is 100, except IDs 13 and 15;
- `SYS_enemy_ai` independently proves bit `0x2` is the CHASE gate.

Thus the previously requested aggro A/B is no longer a missing domain. The code
and independent flag binding establish the direction. The reason grasshopper ID
15 has its own path is designer intent not encoded in these branches; the exact
exception remains documented but does not block safe consumption of the ABI.

## The `0xFF` block corrected

At `0x80054628`, the gameplay pickup dispatcher detects a berry-selector change.
If row zero of the destination column is still `0xFF`, the loop at
`0x80054674..0x8005469C` copies the old selector column into the new selector
column for every one of the 64 rows. The contact walker mirrors the same rule at
`0x80058A74..0x80058AB4`.

This is lazy berry-column inheritance when a berry class becomes available. It
is not frontend code and it does not scan arbitrary `0xFF` entries.

## Save and continue closure

The established save layout remains:

| Bytes | State |
|---|---|
| 0 | Lives |
| 1 | Campaign progress |
| 2..20 | Sixteen completion bytes plus three adjacent FMV/challenge bytes |
| 21..27 | Serializer gap, used only by scene-config CD mix/display offset fields |
| 28..347 | The persistent 64x5 adaptive table |

E15 resolves the formerly unknown byte `0x8009B88A`: the resident call at
`0x8004FFD4` increments it and requests FMV ID `41 + incremented_byte`. It is a
persisted alternate-FMV sequence counter. Unusual-save wrap behavior stays an
explicit E15 residual rather than an E14 blocker.

C16's normal-speed Interpreter evidence already closes Continue: lives are
restored by `scene_config_apply` at `0x80055538`, not by directly rerunning the
new-game initializer. C05 closes the results-save edge: the sole MEMORY.BIN
reader of `0x800823E4` gates serialize, card write, apply, and flag clear.

## Options and the unsupported remap assumption

A second transient C tool reconstructed the global/call surface of MEMORY.BIN's
`menu_nav_cursor 0x800B687C..0x800B79C8`.

Confirmed effects:

- fixed literal pad masks are read directly from held `0x80082412` and edge
  `0x800822E4`;
- the branch at `0x800B73B0` toggles a bit-`0x80` option and calls
  `pad_rumble_update` at `0x800B74E4`;
- the branch at `0x800B75B8` handles d-pad screen adjustment and stores
  `0x800822CC/0x800822D0`; the same function passes these values to
  `set_draw_env_offset` at `0x800B6B58`;
- it reapplies the table-indexed CD mix through `cd_audio_volume_apply` at
  `0x800B7900`, but has zero direct accesses to SFX master volume
  `0x8008247E`;
- the save serializer contains none of these option globals.

No mutable button-map table participates in this path. The old row text bundled
an unsupported control-remapping assumption into the real options question.
The retail path uses fixed controls; rumble and screen centering are the concrete
option effects recovered here.

## Persistent guard

`tools/phase4_e14_static.c` preserves the table frontier and critical resident
and MEMORY.BIN instruction pins. It also rejects overlay table references and a
new direct SFX-volume access in the options function.

Reproduction, when validation is requested:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror \
  -o /tmp/phase4_e14_static tools/phase4_e14_static.c
mapfile -d '' overlays < <(
  find REBUILD/files -type f -name '*.BIN' \
    ! -path 'REBUILD/files/BITS/MEMORY.BIN' -print0
)
/tmp/phase4_e14_static \
  REBUILD/files/SCUS_942.88 \
  REBUILD/files/BITS/MEMORY.BIN \
  "${overlays[@]}"
```

Transient evidence hashes:

| Artifact | SHA-256 |
|---|---|
| `/tmp/e14_table_census.c` | `0565398965836423412d1e09c3eee7c96eae6c4e31e743c71c4787ee1101c480` |
| `/tmp/e14_table_census` | `2d26e6723676c23510494e736145a3000b1e740720e2d5b22f5a23b7f307bb6f` |
| `/tmp/e14_table_census.out` | `922ac3b6530b6f98baf55e7fe36906721a1c4ae42ecae20a88cf5b14d02df752` |
| `/tmp/e14_frontend_census.c` | `78f0f34a40774a195eaef8548b9def7107f3d9ae958a20a907b2f935f632b66d` |
| `/tmp/e14_frontend_census` | `c8cb9c0a89b287553216c934012a7e11121f93d1df2a858805f4ac1cc463a862` |
| `/tmp/e14_frontend_census.out` | `1e2cead0926a399139e6f6fd8fec3821e1c945e5e793611413b03cf1006b3483` |

## Honest residuals

E14 remains partial because it lacks a dedicated cold-boot full memcard
failure/retry oracle and pixel-level presentation coverage for every baked menu
page. The grasshopper exception's designer rationale also remains unknown.

Those residuals do not intersect the recovered save ABI, writer frontier,
adaptive CHASE law, Continue restore, results-triggered save chain, or option
effects. Reopen E14 for a save/card/options MOD, not to replay already-covered
static behavior.

The shared Phase 4 roadmap and mechanics baseline were concurrently dirty and
were deliberately left untouched. This note is the durable E14 row update.

## Related

[[EXP_2026-08-03_phase4_e14_frontend_save]] |
[[MEM_80089938_actor_berry_column_state_table]] |
[[SYS_menu_and_frontend]] |
[[SYS_enemy_ai]] |
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]]
