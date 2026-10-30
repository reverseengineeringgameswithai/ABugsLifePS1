---
title: "Phase 4 C11 - Seed tokens"
date: 2026-08-04
status: complete
phase4_row: C11
verdict: substantiated-partial-bounded-exhausted
---

# Phase 4 C11 - Seed tokens

## Question

Close the Phase 4 Seed Tokens row as far as pristine resident ASM and authored level data permit: bind all five token kinds to retail colors and plant outputs, explain the pickup transaction and feedback, enumerate availability across the campaign, and establish reset/persistence boundaries.

## Method

Capsule-first review found no dedicated C11 pickup capsule. The five retained A13 color/output capsules were validated and used only as independent color/output corroboration; their coverage does not include the C11 token-writer PCs. The named missing domains were resident token dispatch and whole-game authored placement, both answerable offline from the pristine executable and `LEVEL.DAT` files. No live DuckStation replay was required.

A persistent C gate verifies the pristine executable hash, handler jump table, lane stores, output-object IDs, one-shot source retirement, feedback calls, registry/HUD flow, level initialization, save exclusion, latent-helper ownership, all 256 byte inputs to the packing arithmetic, and all source-`0x3f` tables in `LEVEL00..LEVEL10`.

```sh
cc -O2 -Wall -Wextra -o /tmp/phase4_c11_static \
  tools/phase4_c11_static.c -lcrypto
/tmp/phase4_c11_static SCUS_942.88 REBUILD/files \
  > analysis/phase4_c11_seed_tokens.json
```

Result: `C11_RESIDENT_AND_AUTHORED_STATIC_PASS`.

## Identity and retained evidence

Pristine executable: `SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

Validated A13 capsule manifest SHA-256 values:

| Color | Manifest SHA-256 |
|---|---|
| blue | `81053aba5b5ec9bb9e33fbb944fffd09d9df2ed95528ff8dafb931e042b7f17d` |
| brown | `902bfdfffa3dcb6ef11d7ab77405ad306a96a330bb344e85944a46a20f88b1dd` |
| green | `4b820e271795cf7a5f56168206e3d07f34ba5bc8285b6c5dc8c4210bac171695` |
| purple | `c86cb9e2baeff56d10d2d6d09b1a63ba1b11904546e93d0add39519478db5b5e` |
| yellow | `03b5872a5bb7ecbdd21c32ffe14c20675ebbef2ff5c98600a4940b473dd89afc` |

All five manifests report complete capture, no truncation/error, reproducible movie, no control mismatch, and capsule/control full-state fingerprint equality. The central preservation record is `analysis/phase4_trace_capsule_set.json`.

Relevant transcription hashes:

| Input | SHA-256 |
|---|---|
| `asm/hand_written/80053814_source3f_dispatch.s` | `21057ddf05253bcdca9f4ff1b544330d72396c241947aa412f7ce3169fe6abec` |
| `asm/hand_written/80053754_sub_80053754.s` | `f28202fee7aa87e42ffc6b2dd1003ca5cc9f5aa711e944a4b6a65b33c280139e` |
| `asm/hand_written/80046b20_level_load_player_spawn_writer.s` | `5cc4abedda1bb9dad0d1439f071a607721215bb3179ec6324c2359411f724556` |
| `asm/hand_written/8005b714_gameplay_state_reset_cursor_seed.s` | `07b436d13edd1628b61702d27030a1b02af23212758f8e99b352f2831f1c15ca` |
| `asm/hand_written/800526fc_results_screen_render.s` | `70118b83c50b58710f9a891b6b9d69b8dd5773077a504b6bc441bc096b5b6331` |
| `asm/hand_written/8005044c_play_sound.s` | `546f5d1d5cdd6bc4ae83f8c15f8b25464813031b50425df6b37291b8a061f9a6` |
| `asm/hand_written/80050994_sfx_dispatch.s` | `c7b1a3120fcfbea617050068c0e94cbc836ff7b01effc3194186e1aad5ed6b68` |
| `asm/hand_written/80055478_sub_80055478.s` | `ecb9543466bad4d6d185a9088c94cc3084e1f1bcfd0fe3256e80c6914eb4b1d0` |
| `asm/hand_written/80055538_sub_80055538.s` | `c7e7f5f5ddea8805f0c17a1f344a0e8e4a340c20af491703abbc428824f15993` |

Every `LEVEL.DAT` hash and discovered table offset is recorded in `analysis/phase4_c11_seed_tokens.json`.

## Findings

### Exact five-family binding

| Kind | Retail color | Packed lane | Handler | Store PC | Output object |
|---|---|---:|---:|---:|---:|
| `0x29` | brown/orange | `0x800A6598` | `0x800542F4` | `0x8005431C` | `0x16` |
| `0x2A` | blue | `0x800A6599` | `0x8005433C` | `0x80054364` | `0x17` |
| `0x2B` | green | `0x800A659A` | `0x800543B8` | `0x800543E0` | `0x19` |
| `0x2C` | purple | `0x800A659B` | `0x80054434` | `0x8005445C` | `0x18` |
| `0x2D` | yellow | `0x800A659C` | `0x800544D0` | `0x800544F8` | `0x2F` |

Correction to the earlier C11 interpretation: these bytes are the plant-output selector/availability lanes themselves, not separate token counters. For each pickup, `n=(old+1)&7` and the handler stores `(n<<4)|n`. It simultaneously raises the maximum low nibble and selects the new tier in the high nibble.

### Collection and feedback transaction

The source-`0x3f` loop computes contact distance in its downscaled coordinate domain and requires squared distance `< 2500`. For ordinary seed tokens it calls `0x80057620`, writes the `0x80000000` retirement sentinel to the runtime source entry's Y field at `0x80053CD0`, and then dispatches the color handler. The token is one-shot for the life of that loaded source table.

Brown dispatches `0x80050994(-3)` in its handler. All four non-brown paths converge on the same `0x80050994(-3)` call. The common post-loop path then calls `0x8005044C(-3, pickup_coordinates)`. This closes the feedback event and coordinate binding, but not the final audible sample or GPU primitive.

### First-unlock registry and HUD

On first unlock only, blue/green/purple/yellow append values `1/2/3/4` into the first zero nibble of `0x800B0196`. The value is an ordered color-lane index, not a quantity.

The HUD starts with lane 0 (brown), then loads each following lane index from the low nibble of that registry, shifts the registry right four bits, and reads `0x800A6598 + lane`. The displayed tier comes from that packed byte's high nibble. This establishes why first-unlock order controls non-brown meter order without changing color identity.

### Whole-game authored availability

Counts below are per unique retail level directory. Reused campaign stages intentionally reuse the same directory data.

| Directory | Brown | Blue | Green | Purple | Yellow |
|---|---:|---:|---:|---:|---:|
| `LEVEL00` | 0 | 0 | 0 | 0 | 0 |
| `LEVEL01` | 3 | 3 | 3 | 0 | 0 |
| `LEVEL02` | 0 | 0 | 0 | 4 | 0 |
| `LEVEL03` | 0 | 0 | 2 | 4 | 0 |
| `LEVEL04` | 0 | 1 | 4 | 4 | 2 |
| `LEVEL05` | 1 | 4 | 2 | 4 | 0 |
| `LEVEL06` | 2 | 0 | 2 | 0 | 0 |
| `LEVEL07` | 3 | 3 | 2 | 2 | 0 |
| `LEVEL08` | 0 | 0 | 0 | 0 | 0 |
| `LEVEL09` | 1 | 4 | 4 | 0 | 3 |
| `LEVEL10` | 1 | 3 | 4 | 0 | 0 |

Unique-directory totals are brown 11, blue 18, green 23, purple 18, yellow 5: 75 token placements. Campaign stage-to-directory order is `01,03,02,06,10,01,04,05,04,07,02,03,09,08,05`; the machine evidence expands all 15 stages.

Brown begins at tier 1, and its largest authored count is 3. Every non-brown authored count is at most 4. Therefore all retail level states stay at or below tier 4; the modulo-8 handler wrap exists mathematically but is unreachable from authored campaign data.

### Reset and persistence boundaries

Level load clears 168 bytes beginning at `0x800A6500`, then writes brown `0x11`. Gameplay initialization also clears `0x800B0196`. Reloading the level rebuilds the authored source table and restores token placements.

The ordinary respawn path does not write the five packed lanes. The memory-card serializer/deserializer references the separate 19-byte unlock array at `0x8009B878` and has zero references to `0x800A6598..0x800A659C`. Seed-output tiers are per-level runtime state, not memory-card progression.

### Latent helper correction

`0x80053754` duplicates generic tier increment, reskin, and first-unlock registry work. The pristine executable contains no direct jump/call owner and no literal pointer to the helper. It is latent and is not the X-button output-cycle path. The active X path changes selection without increasing the maximum, as documented in [[Seed_plant_output_binding]].

## Evidence classification

Observed: pristine hashes, exact instructions/tables, all `LEVEL.DAT` placement counts, and the five independently validated A13 capsule identities.

Causally established: kind-to-lane/output binding, tier update math, one-shot retirement ordering, feedback event calls, first-unlock registry insertion, HUD registry traversal, level initialization, respawn lane preservation, and memory-card exclusion.

Inference: the retail color names attach to the exact output-object map through the prior A13 color/output evidence. Exact audiovisual realization of event `-3` is not inferred from its dispatch calls.

## Closure against the Phase 4 row

| Requirement | Result |
|---|---|
| five local kind-to-retail-color bindings | closed |
| plant-output unlock effect | closed at exact packed-lane stores and output IDs |
| pickup one-shot behavior | closed at the pre-dispatch source retirement sentinel |
| pickup feedback | closed through event/coordinate dispatch; exact AV presentation retained as Strict-Full residual |
| all-level availability | closed for all unique directories and expanded 15-stage mapping |
| reset/persistence | closed for level load, ordinary respawn lane behavior, source reload, registry initialization, and memory-card exclusion |
| retail tier bounds | exhaustive handler math plus authored-data maximum closes natural states |

## Verdict

**Substantiated partial, bounded-exhausted.** C11's gameplay contract is closed to the Phase 4 standard. A live Interpreter movie would add only presentation evidence unless a future task specifically demands exact GPU/SPU attribution or frame/cycle timing for the `-3` feedback. Synthetic counters beyond retail-authored tier 4 are also outside this row's bounded campaign claim.

Canon: [[Seed_token_collection_and_progression]].
