---
kind: experiment
date: 2026-08-03
phase: 4
row: C01_grain_pickup
status: substantiated_partial_bounded_exhaustion
source_state: original_game
---

# Phase 4 C01 - grain spawn and direct pickup

## Result

C01 is sufficiently substantiated to move on. The ordinary source, constructor gate, direct-contact gate, count/HUD law, retirement state, ordinary audio result, four executable callers, and pristine placement census are bounded. The row remains `partial` only for explicitly separated low-return or adjacent-row work.

No new Interpreter-mode movie is required for this closure. Record one later only if an exact writer PC for the direct-source status byte or natural ctor-`0x51` actor provenance becomes a concrete dependency.

## Evidence identity

- Media: pristine `SCUS-94288`; `REBUILD/files/SCUS_942.88` SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Retained capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/C01_grain_pickup`.
- Capsule manifest SHA-256: `9cd98e28d7a7fd253f8f1227b3ebe290d49140022a4a2983b3159273ffa3f2fa`; tree SHA-256: `b00cc7a957acca603d3bff6b7fa58e95e88d9445d1ea7a162b496ea39a4c0efa`.
- Preservation index: [`analysis/phase4_trace_capsule_set.json`](../../analysis/phase4_trace_capsule_set.json).
- Movie SHA-256: `385bb743192200bad070919cd048a1a6315523057f104f1c5555e9d1e057d076`; anchor state SHA-256: `2421ce34a50d65765b605df87aac789b9de942d86891ade12820da8f5f9f1986`.
- Capsule integrity: 11 chunks, 645 inclusive boundaries (`173978..174622`, movie `0..644`), 1,935 RAM/VRAM/SPU hash checks with zero mismatches, 944,067 flow items, 20,675,828 represented instructions, no truncation.
- Structured evidence: [`analysis/phase4_c01_grain_pickup.json`](../../analysis/phase4_c01_grain_pickup.json).

## Method

The retained capsule was validated and queried before any live work. Offline C reducers reconstructed frame RAM, verified every declared domain hash, counted relevant blocks, and compared the type-`0x3F` placement table at the two count transitions. A separate C decoder read the pristine PS-X EXE and bounded `0x80054EAC`, its callers, and the `0x80053814` dispatch. A C `LEVEL.DAT` census structurally located type-`0x3F` tables and counted kind `0x14` entries.

Representative commands:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_c01_static.c -o /tmp/phase4_c01_static
/tmp/phase4_c01_static REBUILD/files/SCUS_942.88 0x80054eac 0x8005518c

cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_c01_capsule.c -o /tmp/phase4_c01_capsule -lcrypto
/tmp/phase4_c01_capsule ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/C01_grain_pickup

cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_c01_dat_census.c -o /tmp/phase4_c01_dat_census -lcrypto
/tmp/phase4_c01_dat_census REBUILD/files
```

No game state, disc, movie, save, capsule, or executable was mutated. Cold-boot reproduction is not required because this investigation changed no disc, code, or assets.

## Observations

| Emulator frame | Movie frame | Count | Source entry | Source transition | `0x800B018C` | Flow |
|---:|---:|---:|---:|---|---:|---|
| `174174` | `196` | `10 -> 11` | `12` | Y `-1625 -> 0x80000000`; status `1 -> 0` | `0 -> 128` | handler 1, type-3F caller 1, exact-50 0 |
| `174518` | `540` | `11 -> 12` | `11` | Y `-1657 -> 0x80000000`; status `1 -> 0` | `0 -> 128` | handler 1, type-3F caller 1, exact-50 0 |

Exactly one 16-byte placement record changed at each boundary. The second retired record stayed unchanged through final frame `174622`; the first stayed retired until the second pickup and through the final frame. This is source retirement, not bobbing or a transient animation delta.

The capsule exercised only direct target `0x80054278`. It did not exercise the contact-walker caller, effect/drop caller, harvester caller, optional pre-effect spawn, or the exact-50 branch.

## Static pickup law

`FUNC_80054EAC` at `0x80054EAC` performs the following bounded logic:

- It advances the shared script/PRNG byte cursor at `0x800822F4` and tests the first byte's low nibble.
- A low nibble of zero enters an optional pre-effect route. That route is rejected in scene `0x11`, game state `2`, when player flags `0x800A6590 & 4` are set, when `gp+0x6B4` is nonzero, or when `0x80045678(player)` rejects it. Its second byte selects the variant passed to `0x80044D28`.
- The ordinary count update is an unconditional `lbu 0x800A65A1`, `+1`, `sb`. It is an 8-bit wrapping update, not a saturating counter.
- The grain HUD pulse at `0x800B018C` changes `0 -> 64`; values `1025..3071 -> 1024`; values at least `3072 -> 4096-current`.
- Only a post-increment value exactly equal to `50` enters the reward branch. That branch seeds an effect structure at `0x80090B80`, calls sound/event `-11`, and writes `0x800A6594=4` on the pristine reachable path. The two ordinary capsule events did not execute it; their pre-existing `0x800A6594=4` was not caused by these pickups.

The four direct executable callers are `0x80054278`, `0x800589B8`, `0x80059CB4`, and `0x8005B374`. The retained movie naturally used only `0x80054278`.

## Source, spawn, and contact pipeline

The on-disk source is the first type-`0x3F` record in each applicable `LEVEL.DAT`: a 4-byte header followed by 16-byte entries. Ordinary grain is kind `0x14`; coordinates are stored in file units and become runtime units by `<<5`. All 474 pristine grain entries have source status byte `0`; runtime construction/relocation produces eligible status `1`, as observed in the capsule.

`FUNC_80053814` scans eligible entries (`Y != 0x80000000`, status `1`) using:

```c
dx = (player_x_file - entry_x) >> 3;
dy = ((player_y_file - 0xE6) - entry_y) >> 3;
dz = (player_z_file - entry_z) >> 3;
dist2 = dx*dx + dy*dy + dz*dz;
```

- Actorized spawn: if `0x800A6590 & 0x80`, kind is `0x14`, and `dist2 <= 0x15F8F`, it calls `0x80059E44` with ctor `0x51`, writes the source Y sentinel, and stores `-1` at actor `+0x10`.
- Direct source contact: if the constructor branch is not taken and `dist2 < 0x9C4`, jump-table target `0x80054278` calls `0x80054EAC` and leaves result `-1`, which reaches the ordinary sound/event helper.
- The capsule's before/after flags were `0x0008`, so its two pickups were direct-source contacts rather than the `0x80` actorized constructor route.

The capsule proves the full record retirement result at the same boundaries. Its count-mode block flow cannot name the exact instruction that additionally clears status `1 -> 0`; exact writer attribution would require an Interpreter access watch and is not necessary to distinguish the lifecycle.

## Pristine placement census

The C census found 11 extracted `LEVEL.DAT` files and ten valid type-`0x3F` tables. Static kind-`0x14` placements total `474`:

| Source | Grain placements |
|---|---:|
| `LEVEL00` | 0 (no type-`0x3F` table) |
| `LEVEL01`, `02`, `03` | 50 each |
| `LEVEL04` | 24 |
| `LEVEL05`, `06`, `07`, `08`, `09`, `10` | 50 each |

This is a placement census, not a claim that all obtainable grain is finite or limited to 474. The executable also has effect/drop, contact-walker, and harvester routes into the same handler.

## Closure boundary

C01 can move on because the observable trigger, source record, spawn branch, direct-contact branch, counter/HUD effects, retirement, audio result, call graph, and all pristine source placements are covered.

Remaining work is intentionally delegated or low-return:

- C02 owns exact 49-to-50 reward ordering and consequences.
- C13 owns attraction and harvester radius behavior.
- Exact direct-source retirement writer PC is an attribution refinement, not a missing state transition.
- A natural ctor-`0x51` actorized pickup would corroborate an already bounded static branch but is not required unless later mod work targets that branch.

## Transient evidence hashes

- Static handler output: `ffebe530486f1699b3b2dc042e4eb700daf912905018cf59ec32e9b1e0ea01dc`.
- Caller output: `7679e0edad93cb2d5d68c64292d6a30925358f8d2f45a349b1849b056124820e`.
- Capsule reduction: `7fd477f965fd315bdc3d02a40f17f4dcbec0642e3fdbc766313fbb887b4ad3ac`.
- Placement reduction: `6b0fef9ecf24aa5ad486041a15db42f1ebe17576c16486fa109b5f779bfb84fc`.
- Record-diff C/output: `5341468aa556ecb45a7cb081c324bb7671e763bab1383c6be5faefdf7e158624` / `f1e64a8fb2124a2ed67ac00b912e47aaebafdf053c7921ac5eb09865fafdf337`.
- DAT-census C/output: `f38e25c4de4e0e36d74d050a2241ac6c3d5f9b7c4dc1d9ed89e1740ab6e8fcfd` / `3d1b58fdd1a06af94612fd4124f9ea9ae7383f5c9316f8d7a142e8e2b4ebf564`.

## Related

- [[SYS_grain_pickup]]
- [[FUNC_80054EAC_grain_pickup_handler]]
- [[FUNC_80053814_type-0x3f_construct_+_contact-action_dispatch]]
- [[MEM_TYPE-0X3F_PLACEMENT_RECORD_Type-0x3f_placement_record]]
- [[EXP_2026-07-30_phase4_c13_grain_harvester]]
