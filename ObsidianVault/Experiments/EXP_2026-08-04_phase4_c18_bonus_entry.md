---
kind: experiment
id: EXP_2026-08-04_phase4_c18_bonus_entry
date: 2026-08-04
status: complete
phase4_row: C18
verdict: substantiated-partial-bounded-exhausted
---

# Phase 4 C18 - Bonus challenge entry

## Question

Close the row beyond its already-confirmed trigger slices: determine cross-stage applicability, scene-`0x10` loading, the internal bonus-stage completion rule, success versus failure commitment, reward identity, and save persistence.

## Method

The retained Bonus 1 trace capsule was queried before considering live replay. Its manifest is complete and untruncated, movie playback is reproducible, and the C query reconstructed 3,654 frames with 10,962 RAM/VRAM/SPU hash checks and zero mismatches. It covers the fifth trigger, `scene 0x11 -> 0x10`, internal wrapper completion, tentative `0x02 ->` committed `0x22`, and return to scene 0.

No dedicated C18 capsule exists for Bonuses 2 and 3. Their missing domain was shared resident/overlay control flow, so the investigation remained offline: pristine resident ASM, the exact scene-16 overlay `REBUILD/files/LEVEL06/LEVEL1.BIN`, the existing deterministic challenge movies, and a new C static gate. No live DuckStation escalation was required.

```sh
cc -O2 -Wall -Wextra -o /tmp/phase4_d10_capsule \
  tools/phase4_d10_capsule.c -lzstd -lcrypto
/tmp/phase4_d10_capsule \
  asm/hand_written/8004abf4_proximity_updater.s \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/bonus-objectives-v2-20260719/Bonus_Level_01

cc -O2 -Wall -Wextra -o /tmp/phase4_c18_static \
  tools/phase4_c18_static.c -lcrypto
/tmp/phase4_c18_static SCUS_942.88 \
  REBUILD/files/LEVEL06/LEVEL1.BIN \
  > analysis/phase4_c18_bonus_entry.json
```

Static result: `C18_RESIDENT_OVERLAY_STATIC_PASS`.

## Provenance

Pristine executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

Scene-16 overlay SHA-256: `4ea72fd6caaddb287d8eef2086c3b66a74191b6c36ddbeb7feaa1fbf5c8db172`.

Retained Bonus 1 capsule manifest SHA-256: `8e83d3171119f6786052e246b1f2b7d4033d61ad02a537ec56bb8afc08e35413`; collection manifest SHA-256 recorded inside it: `b155a6a33a1dd9af0cb9e22eaee2685cedadf995b4407e0689f61457a7055cd8`.

| Input | SHA-256 |
|---|---|
| `src_re/bonus_unlock_challenges.c` | `c57b8b0d1e11cdb67a9a3872824f6b5ad37ed6d0e0330be8329d03f5cc60dfb2` |
| `asm/hand_written/8004abf4_proximity_updater.s` | `cb5b28d2f150227163e1c82ba93c28fbaac70649d84a95b6728bb24314bc6164` |
| `asm/hand_written/8005bfbc_plant_behavior_walker.s` | `b5dbaa860c6f97792a453e24ecf085ca1cec8a47a245c445804b048f4b97a313` |
| `asm/hand_written/8005c58c_seed_plant_trampoline_handler.s` | `ffe0c5327644cd6ff3bea1269c924d82786263aa38bc69c0b0c2c495cc7bf9ab` |
| `asm/hand_written/80058af8_contact_vs_actor_handler.s` | `2c6313d72dad6d078c23b71028941c4d9306c925bf4d31a510d7bab66328906f` |
| `asm/hand_written/8005905c_berry_tough_damage_dispatch.s` | `f1aa90ff4967fb3286dc49a1bd21099869dd467e2850a69449172da54f53bf44` |
| `asm/hand_written/8005953c_sub_8005953c.s` | `e54bd0abd7b4890b8130e2f564f92c769a753ce9620561a6618c6ff083d1fb12` |
| `asm/hand_written/8004fca0_scene_flow_dispatcher.s` | `80c4643d6584bb0706a6905b939a76225dc0fa92d6c9eebf526337969d349098` |
| `asm/hand_written/80055478_sub_80055478.s` | `ecb9543466bad4d6d185a9088c94cc3084e1f1bcfd0fe3256e80c6914eb4b1d0` |
| `asm/hand_written/80055538_sub_80055538.s` | `c7e7f5f5ddea8805f0c17a1f344a0e8e4a340c20af491703abbc428824f15993` |

The three accepted movie/save pairs retain their previously recorded hashes: Bonus 1 `37083359...f10cc` / `9d117f3b...95c1`, Bonus 2 `bc9c6c4d...459` / `ddc5d7c0...abd5`, Bonus 3 `22ef450e...f984` / `0dd145be...522`.

## Trigger laws and cross-stage availability

The verified movies show one route for each condition, not an exclusive stage gate. Operator confirmation and resident ASM agree: a bonus can be entered from any ordinary stage that provides the required actors/plants.

| Condition | Tentative bit | Earned guard | Exact rule | Hard scene gate |
|---|---:|---:|---|---|
| qualifying butt-slams | `0x02` | `0x20` | five qualifying butt-slammable interactions; raw count, not uniqueness | none; scene `0x10` excluded |
| mushroom chain | `0x01` | `0x10` | five distinct mature type-5 mushroom identities; a duplicate restarts at that identity | none; scene `0x10` excluded |
| grasshopper streak | `0x04` | `0x40` | five lethal blue class-0 contacts against actor ID 15; wrong berry selector or miss/contact case 13 resets | none |

Thus Training spiders, scene-1 seed mushrooms, and Tunnels grasshoppers are canonical fixtures, not hard-coded exclusivity claims. Exhaustively enumerating every alternate stage that can expose five qualifying instances is a placement/reachability sweep, not an unresolved trigger mechanism.

All three successes set transition mode 6 and a fade. The shell turns mode 6 into a one-shot scene override and loads scene `0x10`.

## Scene `0x10` rule

Scene 16 loads pristine `LEVEL06/LEVEL1.BIN` at `0x800B39A0`. Byte `0x8009B88A`, previously unidentified in C17, selects one of three 16-byte target records and also represents the number of successfully completed bonus wrappers.

| Ordinal | X | Y | Z | Auxiliary |
|---:|---:|---:|---:|---:|
| 0 | -13187 | -70036 | -22421 | -70036 |
| 1 | -22349 | -79705 | 48945 | 18380 |
| 2 | 157232 | -42406 | 5891 | -42406 |

The overlay reads Flik's X/Y/Z, subtracts the selected target, shifts each difference right by 8, sums the three squares, and succeeds only when the result is `< 1600`. Success writes transition mode 1 and fade 30. Other overlay work customizes actors/effects for ordinal 0/1/2 but does not grant health, lives, or grain.

## Transactional completion and reward

`0x8009B889` is transactional. Trigger blocks set a low tentative bit. On scene-16 success (return mode 1), the shell computes:

```c
flags = (flags & 0x0f) * 17;   /* copy all low bits into high earned guards */
movie_id = old_bonus_ordinal + 42;
bonus_ordinal++;
play_fmv(movie_id, -1);
```

On any non-success return it instead computes `flags = (flags >> 4) * 17`, restoring low bits from the previously committed high nibble. It does not increment `0x8009B88A` and does not play a reward movie. Merely triggering or entering scene `0x10` therefore cannot permanently earn the bonus.

The movie IDs are completion-order rewards 42, 43, and 44, not hard-bound to a particular challenge identity. The C model exhausts all six challenge orders and all 18 possible abort points. Every order ends at flags `0x77`, ordinal 3, and reward IDs `42,43,44`; every abort restores the exact prior committed state.

The committed high bits are the guards that prevent the corresponding challenge from retriggering. C17 independently proves that `0x8009B889` feeds the frontend movie-viewer availability builder.

## Save impact

The memory-card serializer and deserializer copy 19 bytes beginning at `0x8009B878`. Bonus flags are byte offset 17 and bonus ordinal `0x8009B88A` is offset 18. Both the per-condition earned state and successful-bonus count/variant selector persist across saves.

This resolves C17's previously unidentified 19th byte: within the C18 path it is the successful bonus completion ordinal, scene-16 variant selector, and `42 + ordinal` reward-movie selector.

## Evidence classification

Observed: three pristine trigger movies, exact trigger states, a valid complete Bonus 1 capsule, scene/flag/return timeline, pristine resident instructions, and the exact scene-16 overlay bytes.

Causally established: cross-stage predicate-based triggers, mode-6 scene handoff, three target variants, spatial completion threshold, success commit, non-success rollback, completion-order movie IDs, absence of health/lives/grain reward writes, earned guards, and save persistence.

Bounded inference: alternate-stage reachability depends on authored availability of five qualifying objects. The mechanism is stage-agnostic; this pass does not enumerate every stage/object arrangement.

## Phase 4 closure

| Named row gap | Result |
|---|---|
| trigger logic | closed for all three positive and reset/guard paths |
| bonus-stage loading | closed: mode 6 arms scene `0x10`, `LEVEL06/LEVEL1.BIN` |
| bonus-stage rules | closed at exact ordinal target table and spatial threshold |
| completion | closed for success commit and non-success rollback |
| rewards | closed: committed movie-viewer bit plus FMV IDs 42-44 by completion order; no resource reward |
| save impact | closed: flags and ordinal are the final two bytes of the persisted 19-byte block |

## Verdict

**Substantiated partial, bounded-exhausted.** The named C18 contract is closed. Strict Full retains exhaustive alternate-stage placement/reachability, exact ordinal-specific visual/audio presentation, and live/capsule breadth for Bonus 2/3 wrapper completion. None changes the shared resident/overlay law, and no new Interpreter movie is required for the bounded claim.

Canon: [[SYS_bonus_unlock_challenges]].
