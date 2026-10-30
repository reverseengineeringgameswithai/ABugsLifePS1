---
kind: experiment
id: EXP_2026-07-12_phase3_architecture_maps
name: Phase-3 architecture maps — dispatch tables and the scene/asset load graph
status: confirmed
created: 2026-07-12
updated: 2026-07-13
confidence: confirmed
source_state: original_game
systems:
  - SYS_indirect_dispatch_map
  - SYS_scene_asset_load_graph
  - SYS_record_layouts_and_lifetimes
artifacts:
  - tools/phase3_record_types.py
  - config/record_types.yaml
  - analysis/phase3_record_types.json
  - analysis/phase3_record_probe.json
  - tests/test_phase3_records.py
  - tools/phase3_dispatch_map.py
  - tools/phase3_scene_asset_graph.py
  - tools/phase3_ownership_graph.py
  - analysis/phase3_dispatch_map.json
  - analysis/phase3_scene_asset_graph.json
  - analysis/phase3_ownership_graph.json
  - config/semantic_state.yaml
  - tests/test_phase3_dispatch.py
  - tests/test_phase3_scene_graph.py
  - tests/test_phase3_ownership.py
---

# EXP_2026-07-12_phase3_architecture_maps

## Question

Phase 3 needs a machine-readable architecture map. Two structures were unbound:
the game's **indirect dispatch** (which jump tables exist, what they point at,
and how much dispatch is unaccounted for) and the campaign's **resource
routing** (which scene loads which level data, loading screen, and overlay).

## Method

Static, offline, on the **pristine** EXE (`REBUILD/files/SCUS_942.88`,
`file_off = vaddr − 0x8000F800`), with every claim resolved against the
committed function census (`analysis/functions.json`) and symbol store
(`symbols/re_symbols.sym`), and then **cross-checked against independent
runtime evidence** from the Phase-2 oracle.

1. Decode the three known jump tables target-by-target; flag any target outside
   censused code or inside an unnamed function as a computed gap.
2. Scan every censused resident code range for `jr <reg ≠ ra>` / `jalr` to get a
   *bound* on total indirect dispatch, not just the tables we happen to know.
3. Scan the image for level-ish ASCII, then find the `lui`/`addiu` pairs that
   materialize each string-table base to identify the consuming functions.
4. Decode the routing tables and require every row to agree with the scene id
   the corresponding Phase-2 `go_to_end` movie actually reached.

## Result — dispatch

44/44 jump-table targets resolved and named, 0 gaps.

- **mover/event VM** `0x8001B2F4`, 26 slots → 19 distinct handlers. The
  interpreter's dispatch is byte-verified at `0x8004C1FC..0x8004C220`:
  `sltiu v0,v1,26` (bound), scale, `lw v0,-0x4D0C(at)` (= `0x8001B2F4 + op*4`),
  `jr v0`. Unused opcodes point at the fall-through handler.
- **berry throw** `0x8001B1C0`, 5 slots → five *interior entry offsets* of
  `berry_throw_dispatch` (`0x8004719C`/`A8`/`B4`/`BC`/`C8`), each setting the
  throw POWER before the common path. This explains, mechanically, why the table
  cannot be extended in place for a new berry.
- **plant behaviours** `0x8001B848`, 13 slots, index = **type − 2**, matching the
  independently derived brown/green seed Canon (cannon `0x8005C110`, propeller
  `0x8005C258`, trampoline `0x8005C58C`, dandelion `0x8005C818`, green passive
  `0x8005CCE8`).

Whole-EXE bound: **234 indirect-control sites**. The exhaustive follow-up
classifies all 95 `jr` sites as 36 decoded tables, 45 computed code jumps, and
14 unresolved sites with explicit reasons. Of 139 `jalr` calls, 99 use 30 global
callback slots, 36 use record-relative function-pointer fields, and 4 retain
explicit unresolved reasons (`analysis/phase3_jr_tables.json` and
`analysis/phase3_jalr_callbacks.json`).

## Result — scene/asset routing

Three ASCII tables, each with its consumer identified:

| Table | Address | Consumer |
|---|---|---|
| scene asset (15 × 0x10, `levelNN\levelXY`) | `0x8001AD0C` | `0x8003CFDC` in `resource_id_dat_load_dispatcher` (`0x8003CF2C`) |
| GFX loading screen | `0x8001AE98` | `0x8003F4B8` in `switch_dispatch_struct_by_index` (`0x8003F3B4`) |
| level BIN | `0x8001B174` | `0x80046718` in `level_file_path_build` (`0x80046618`) |

**Load law:** row index = scene_id − 1; the disc DIRECTORY selects the overlay
pair, the ASSET PREFIX selects the sub-level data + loading screen. Disc dir
numbers do **not** track scene ids (scene 11 → `level02\level4b`).

**Cross-evidence:** all 15 rows reproduce the scene ids observed in the 15
Phase-2 stage movies. The static decode and the recorded replays agree on every
campaign stage, and neither was derived from the other.

## Correction landed here

`0x80050994` is **`sfx_dispatch`**. The seed-impact arms studied in Phase-2's
A11 therefore *play an impact sound* (id `a0 = −4`) and *write the knockback*
(`sh -20 → enemy+0x6C`) — the `jal` was never a damage call. The behavioural
result is unchanged (the knockback write is the damage), but the mechanism text
in `analysis/phase2_final_action_pairs.json` and its generator were corrected.

## Boundaries (not silently omitted)

- **Training (scene 17) is outside the campaign table but no longer unmapped.**
  The dispatcher uses `0x8001AFB0[16] -> 0x8003CFC4`; the exceptional route pins
  `LEVEL00` and `GFX/TRAINING.RAW`, and records that the four-byte
  `LEVEL00/LEVEL.BIN` is not a code overlay.
- `object_pointer_list` `0x80096B98` is RAM/BSS populated at load time. The live
  follow-up enumerates it at all 42 pristine anchors and proves the pointer map is
  stable while the loader rewrites CLUT/texpage fields per level.
- `LEVEL10` has a single overlay where every other directory has a `_LEVEL` /
  `_LEVEL1` pair — unexplained.

## Result — typed records and lifetimes (WP5/WP6)

Eight record views typed under the rule **typing must not erase ignorance**:
every byte is a declared field or an explicit UNKNOWN span
([[SYS_record_layouts_and_lifetimes]]). They cover all twelve required families:
object, contact, enemy, projectile, seed, plant, player, camera, render, audio,
objective, and frontend. **181/524 bytes typed (34.5%)** — every other byte is
*named as unknown*, not hidden.

The layout validator earned itself immediately: `berries_in_flight` at `+0x96`
had to be **u8, not u16** — a u16 there silently swallows `equipped_berry` at
`+0x97`.

**The occupancy trap.** A first probe reported the contact pool at **64/64**,
which cannot be true — the allocator has no full-array escape, so a full pool
hangs, and the retail game plainly does not. The bug was the metric: a dead slot
keeps **residue**, so "has non-zero bytes" is not occupancy. Re-measured with the
game's *own* predicates — and there are two distinct ones, the walker/live gate
(`active_type > 0 AND flags & 0x02`) and the allocator's skip test
(`flags & 0x80 AND active_type != 0`) — across all 42 hash-pinned pristine
anchors:

| Record | live | allocator-occupied peak | headroom |
|---|---|---|---|
| contact | 0–2 | **4 / 64** | **60** |
| plant | 0–12 | 12 / 20 | 8 |
| actor | 0–40 | 40 / 40 | fixed table |

So the capacity hang is a **mod-introduced risk, not a latent retail bug** —
pristine play peaks at 4 of 64 slots. The constraint stands regardless.

Every unknown byte is triaged (always-zero / constant / varying) into a work
queue; the varying clusters are velocity/rotation-shaped (`player +0x20..0x39`,
`actor +0x14..0x23`, `contact +0x0C..0x18`) and are held as hypotheses, not
written into the registry as fields.

## Reproduce

```
python3 tools/phase3_record_types.py         # offline: validate + byte accounting
python3 tools/phase3_record_types.py --probe --port "$PORT" --token "$TOKEN" \
  --config-dir "$CONFIG" --instance-state "$INSTANCE" # live: fields + occupancy
python3 tools/phase3_dispatch_map.py        # needs the local EXE
python3 tools/phase3_scene_asset_graph.py   # needs the local EXE
python3 tools/phase3_ownership_graph.py     # offline
python3 -m pytest tests/test_phase3_dispatch.py tests/test_phase3_scene_graph.py \
                 tests/test_phase3_ownership.py -q
```
