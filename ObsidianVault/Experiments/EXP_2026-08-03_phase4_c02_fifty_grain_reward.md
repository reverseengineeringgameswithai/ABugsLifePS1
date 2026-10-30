---
kind: experiment
date: 2026-08-03
phase: 4
row: C02_fifty_grain_reward
status: substantiated_partial_bounded_exhaustion
source_state: original_game
---

# Phase 4 C02 - fifty-grain reward

## Result

C02 is sufficiently substantiated to move on. The exact `49 -> 50` trigger, instruction order, true-health refill, emblem state, HUD channels, dead extra-life branch, presentation lifetime, resident scene scope, and direct save boundary are resolved.

No new Interpreter movie is required. The retained movie naturally proves the reward at full health; a matched isolated `debugger.callFunction` control proves the damaged-health effect without changing any persistent file.

## Evidence identity

- Pristine media: `SCUS-94288`; cue SHA-256 `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`.
- Pristine executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Retained capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/C02_grain_49_to_50`.
- Capsule manifest SHA-256: `f89163cd15655275a529c44a3382308e9c14a194e23a761aa41cdc7e8e9a7e8e`.
- Preservation index: [`analysis/phase4_trace_capsule_set.json`](../../analysis/phase4_trace_capsule_set.json).
- Movie SHA-256: `cff9196b7b8b9d9c8391a57c85907a0271b4ff563ec8475ea676fac82012e90c`.
- Anchor state SHA-256: `a6291970431030b5aefd8455b73c68583f10417c73e97ac820be249ee4859ebb`.
- Structured evidence: [`analysis/phase4_c02_fifty_grain_reward.json`](../../analysis/phase4_c02_fifty_grain_reward.json).

## Capsule validation

The capsule contains 438 inclusive frame boundaries (`200029..200466`, movie `0..437`), 8 chunks, 617,333 flow items, and 16,797,938 represented instructions. The C reducer verified 1,314 RAM/VRAM/SPU hashes with zero mismatches and no truncation.

The only grain-count transition is emulator frame `200189`, movie frame `160`:

| Field | Before | Frame boundary after |
|---|---:|---:|
| grain `0x800A65A1` | 49 | 50 |
| true health `0x800A6594` | 4 | 4 |
| lives `0x800A65A0` | 1 | 1 |
| extra-life HUD `0x800B0188` | 0 | 0 |
| grain HUD `0x800B018C` | 0 | 128 |
| reward HUD `0x800B0190` | 0 | 128 |

That frame executes `0x80054EAC`, count block `0x80054F88`, exact-50 block `0x80055014`, two calls to `0x8005044C`, and the type-`0x3F` caller at `0x80054278`. The scene is `0x11`: scene `0x11` suppresses only the optional pre-effect, not the exact-50 reward.

## Exact ASM order

The pristine executable decoded by C establishes this order:

1. `0x80054F9C`: store post-increment count `50`.
2. `0x80054FA0..0x80054FF8`: pulse ordinary grain HUD `0x800B018C`.
3. `0x8005500C`: compare post-increment count with exactly `50` and enter the reward.
4. `0x80055014..0x8005505C`: snapshot player X/Y/Z and player `+0x48` into `0x80090B80..8C`; initialize scale `0x80090B90=1024`.
5. `0x80055060`: call `0x8005044C` with id `-11` and the player base.
6. `0x80055078`: compare constant addresses `0x80090B80` and `0x800B3988`; they are unequal, so the retail extra-life block, second sound `-8`, and `0x800B0188` pulse are unreachable.
7. `0x80055124`: store `4` to signed true health `0x800A6594`.
8. `0x80055128..0x80055170`: pulse reward HUD `0x800B0190`.

The count comparison is equality, not `>=`. If a mod or corruption skips from 49 past 50, this handler does not run the reward at the later value.

## Matched accelerated health control

The natural movie starts with true health already `4`, so the health writer executes without a visible value delta. A matched isolated control closed that gap.

Session identity:

- Dedicated config: `/tmp/duckstation-c02-GGi5Vj`; port `28743`; ephemeral token not preserved.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; binary SHA-256 `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`.
- Media and save identity were verified before loading. Both cases began paused at emulator frame `200029` from the same hash-pinned state.
- No instrumentation was needed. Each case changed only disposable RAM, invoked `debugger.callFunction` at `0x80054EAC`, then the anchor was reloaded.

Results:

| Case | Count | Forced health | Health after | Grain HUD | Reward HUD | Emblem struct | Lives |
|---|---|---:|---:|---:|---:|---|---:|
| negative control | `48 -> 49` | 1 | 1 | 64 | 0 | unchanged | 1 |
| treatment | `49 -> 50` | 1 | 4 | 64 | 64 | seeded, scale 1024 | 1 |

This proves the health write is threshold-owned rather than an ordinary-grain side effect. The instance was restored, traces and breakpoints were cleared, and owned PID `930155` was stopped through its config launcher.

## Canon correction: health addresses

`0x800A6594` is Flik's signed true health. Exact-50 writer `0x80055124` sets it to `4`.

`0x800A7E2A` is not true health. Across the entire retained movie it free-runs through a `1..7` animation cycle before and after the pickup. Older grain-emblem documentation interpreted its visible refill animation as the health value itself; C02 corrects that semantic while preserving the observed presentation.

## Emblem and HUD lifetime

- The reward HUD channel `0x800B0190` is armed at movie frame `160`, is last nonzero at `283`, and returns to zero at `284`.
- The emblem/effect structure `0x80090B80` is active through movie frame `409`; X becomes the `0x80000000` inactive sentinel at frame `410`.
- Lives remain `1`, grain remains `50`, and true health is `4` at the final captured frame `437`.
- The grain HUD channel is distinct from the reward channel and remains in its completed-panel state after the reward presentation ends.

## Save, results, and token boundary

`FUNC_80055478` serializes lives, a scene halfword byte, a 19-byte header, and 64 five-byte scene records. It does not directly serialize grain count `0x800A65A1`, true health `0x800A6594`, or emblem state `0x80090B80`.

The grain emblem is transient presentation and the in-level grain objective remains count-derived at `grain == 50`; there is no separate token bit written by `0x80054EAC`. Downstream results-screen campaign flags, save-menu consequences, and movie unlocks are separate consumers owned by E13, E14, and C17. C17 is concurrently assigned to another agent and was not touched here.

## All-level boundary

The exact-50 gate is resident code with no level-id exception. Scene `0x11` naturally executed it, proving the scene-specific pre-effect exclusion does not suppress the reward. Whether a stage authors enough placed/dynamic grain to reach 50 is a content question, not a different reward law.

## Closure decision

C02 is a bounded-exhausted partial. Reopen only for strict natural damaged-health presentation or a concrete downstream results/save/movie dependency. Neither requires holding this row open.

## Reproduction commands

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_c01_capsule.c -o /tmp/phase4_c02_capsule -lcrypto
/tmp/phase4_c02_capsule ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/C02_grain_49_to_50

cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_c01_static.c -o /tmp/phase4_c02_static
/tmp/phase4_c02_static REBUILD/files/SCUS_942.88 0x80054eac 0x8005518c

cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_c02_xrefs.c -o /tmp/phase4_c02_xrefs
/tmp/phase4_c02_xrefs REBUILD/files/SCUS_942.88
```

## Related

- [[SYS_fifty_grain_reward]]
- [[SYS_grain_pickup]]
- [[FUNC_80054EAC_grain_pickup_handler]]
- [[FUNC_80055478_serialize_savegame_buffer]]
- [[FUNC_800526F4_HUD_draw]]
