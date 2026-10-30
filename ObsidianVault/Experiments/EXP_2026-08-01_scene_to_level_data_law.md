---
type: experiment
status: complete
date: 2026-08-01
system: scene / level-data selection
phase: 3
artifacts:
  - analysis/phase3_scene_asset_graph.json
  - tools/phase3_scene_asset_graph.py
  - tools/campaign_level_inventory.py
---

# Which level data a scene loads — the real law, and the one that was wrong

## Verdict

`analysis/phase3_scene_asset_graph.json` stated

> row index = scene_id − 1 … the ASSET PREFIX selects the sub-level data

That law was **never derived from code** — it was an assumption written into the
generator, which read a NUL-terminated string at `base + i*0x10` and stamped
`scene_id = i + 1`. It is **wrong for 11 of 15 scenes**, and the strings it reads are
**VAB/sound-bank prefixes**, not level data.

## The real law

```
0x8003CF84  addiu v1, s4, -1        ; s4 = scene id
0x8003CF88  sltiu v0, v1, 17        ; valid 1..17
0x8003CFB4  lw    v0, -0x5050(at)   ; jr table 0x8001AFB0[scene-1]   <-- PERMUTED
0x8003CFBC  jr    v0
   ...
0x8003D204  slti  v0, s4, 11
0x8003D208  bne   v0, zero, 0x8003D220
0x8003D214  addiu s4, s4, -10       ; scene >= 11 -> dir = scene - 10
0x8003D218  ori   v0, v0, 320       ; flags |= 0x140 -> the "1" file-name variant
0x8003D21C  sw    v0, 0x614(gp)     ; 0x800823AC
```

> **`dir = scene_id ≤ 10 ? scene_id : scene_id − 10`**
> **`file = scene_id ≤ 10 ? LEVEL.DAT : LEVEL1.DAT`** (same for `.BIN` / `.RAW`)

So **each disc directory hosts two scenes**, `d` and `d+10`, as `LEVEL.*` and `LEVEL1.*`.
The jr table only selects which **sound bank** string the handler loads.

## The player-facing level number is a third permutation

The campaign progression table at **`0x80077FA0`**:

```
[17, 1, 3, 2, 6, 10, 11, 4, 5, 14, 7, 12, 13, 9, 8, 15, -1]
```

maps the operator's level ordinal → scene id. Ordinal 0 is training (scene 17);
**ordinal 6 → scene 11 → `LEVEL01/LEVEL1.DAT`**.

So three distinct numbering spaces were being conflated: **level ordinal**, **scene id**,
and **disc directory**.

## How it was caught, and why it survived so long

The operator said the level they call 06 (the bird boss) has *"only 4 blue tokens and 2
yellow/gold tokens"*. That fingerprint is unique across all 21 staged DATs and lands on
`LEVEL01/LEVEL1.DAT` — which the old artifact assigned to **scene 6**, while the operator's
save reads **11** at `0x80082504`. Both could not be right.

I first "resolved" the conflict the wrong way round, banking a claim that `0x80082504` is
not the scene id, on the argument that it reads 17 while the table has 15 rows. **That was
false** — scene 17 is a legitimate scene on an exceptional route, documented in the very
artifact I was correcting. Retracted the same commit.

## Independent confirmations

1. **Directory agreement.** With the permutation, the VAB directory equals the
   arithmetically derived directory for **all 15** campaign scenes. Under the identity
   assumption that agreement breaks for 11 of 15. This is now an assertion in the
   generator (`vab_dir_matches_disc_dir`).
2. **Both operator fingerprints reproduce exactly**: Level 01 → `LEVEL01/LEVEL.DAT`
   (3 blue), Level 06 → `LEVEL01/LEVEL1.DAT` (4 blue + 2 gold).
3. **Training is scene 17 → `LEVEL07/LEVEL1.*`, not `LEVEL00`.** Corroborated by
   `tools/training_board_edit.py` and `tools/patch_training_overlay.py`, which already
   target `LEVEL07/LEVEL1.*`, and by `LEVEL00/LEVEL.DAT` having zero type-0x3f entries.

## Corrected

- `tools/phase3_scene_asset_graph.py` — decodes the jr table and the arithmetic; emits 17
  scenes with `string_row`, `disc_dir`, `level_data` and the agreement check.
- `analysis/phase3_scene_asset_graph.json` — regenerated, 0 gaps.
- `tools/campaign_level_inventory.py` — `STAGE_MAP` rebuilt keyed by **scene id**.

## Not established

- Flag bits 3–5 of `0x800823AC` (base `0x38`) and the branch at `0x8003D588`.
- `LEVEL01/LEVEL2.DAT` and `LEVEL04/LEVEL4.DAT` are unreachable by any scene id under this
  law (they would need flag bits `0x200`/`0x300`) — leftovers, unverified.
- `analysis/scene_to_dat_map.json` (a runtime DAT-residency probe) produced empty results
  and should be regenerated as an independent runtime confirmation.

## Related

- [[SYS_player_power_slot]] — the campaign that surfaced it
- [[EXP_2026-08-01_phase4_b06_b08_power_slot]]
