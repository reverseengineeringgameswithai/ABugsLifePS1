---
kind: memory
id: MEM_8009FD80
aliases: [MEM_8009FD80, 0x8009fd80, "MEM - Actor pool", MEM_-_Actor_pool, actor_pool, MEM_80090748, 0x80090748]
address: 0x8009FD80
name: actor_pool
status: static_seen
confidence: confirmed
source_state: original_game
system: [SYS_enemy_spawn, SYS_actor_update]
read_by: []
written_by: [mover_updater]
related_structs: []
evidence: [EXP_2026-08-05_phase4_f01_objective_lifecycle]
src_paths: [tools/phase4_typed_state_provenance.c, tools/phase4_typed_state.py]
patch_policy: safe_to_read
---

# MEM_8009FD80 - Actor pool and its pointer table

## Purpose

The array of actor slots the engine iterates every frame, plus the pointer table
through which most subsystems reach them. Bounding this pool is what lets a store
through an unresolved actor pointer be proved **unable to alias a `$gp` global** —
see [[Phase 4 - Typed State Compiler]].

## Layout

| what | value | how it is known |
|---|---|---|
| pool base | **`0x8009FD80`** | `lui s2, 0x800A` / `addiu s2, s2, -640` at `0x8004D248`/`0x8004D24C` |
| stride | **132 = `0x84`** | `addiu s2, s2, 132` at `0x8004D3FC` and `0x8004D410` |
| slot count | **64** | `slti v0, s4, 64` at `0x8004D41C` |
| pool end | **`0x800A1E80`** | `0x8009FD80 + 64 * 0x84 = 0x8009FD80 + 0x2100` |
| pointer table | **`0x80090748`** | `sw s2, 0x748(at)` at `0x8004D378`, indexed by `s3` |

Stride and slot count agree with the Phase-1 chunk-31 registry
(`0x8009FE04`, stride `0x84`), which sits one slot into the pool.

## The pointer table at 0x80090748

`mover_updater` (`0x8004D224`) publishes each live slot into a pointer table so
other subsystems do not have to know the pool's geometry. Consumers load
`[0x80090748]` for element 0 and `[0x80090748 + i*4]` when walking.

**Writers — ≥ 6 image-wide** (⚠️⚠️ CORRECTED 2026-08-06: the previous
"exactly 4, exhaustive scan + index corroboration, 0 missed" was a **lower
bound** — the scan matched one spelling and the corroboration only covers
index-resolved stores, so two computed-base writers were invisible to both.
The corrected C query now finds all six statically. Its positive recognizer
still leaves **10,995 of 11,001 aligned `sb`/`sh`/`sw`-shaped resident-image
instructions unclassified**, while the independent 21-image region analysis
leaves **5,012 stores undecided** for the table window. Six is therefore a
known set and a lower bound, not an exhaustive census. Static receipt:
`analysis/phase4_f01_static_hard_truth.json`; live discovery receipt:
`analysis/phase4_f01_live_gap_read_receipt.json`):

| pc | function | value |
|---|---|---|
| `0x8003A49C` | `high_heap_loader_level_raw_decompress_orchestrator` | `zero` (clear) |
| `0x8004A4B4` | `object_slot_type_init` | `zero` (clear) |
| `0x8004D378` | `mover_updater` | **`s2`** — the pool walk (publisher) |
| `0x8004D43C` | `mover_updater` | `zero` (clear/terminator) |
| `0x80049C10` | `enemy_deathanim_finalize_remove_from_list` | **existing table entry** — COMPACTION moves a live pointer down (`sw a0, 0x0(v1)`, base `a1 = 0x80090748` @`0x80049BF4/BF8` + indexed `addu`) |
| `0x80049C14` | `enemy_deathanim_finalize_remove_from_list` | `zero` — nulls the moved-from slot |

So the table is cleared at level load and at the top of each update pass,
repopulated from the pool, and COMPACTED in place when an enemy is removed.
Two known instructions can put a non-null pointer there: the publisher
(`0x8004D378`, sourcing pool slots) and the compaction mover (`0x80049C10`,
sourcing an existing table entry). The C query proves the latter instruction's
source relation; it does **not** prove the source table's contents. A proof that
all non-null values remain pool slots requires, together: bounded source and
destination indices, an initial table containing only null/pool values, every
non-move publisher preserving that domain, an exhaustive writer universe, and
least-fixed-point induction over the moves. Those premises are not all closed.
`0x80049C14` is independently proved null by its encoded `zero` source; live
values observed stayed in the pool∪null domain, but that sample is corroboration,
not the missing induction proof. **Treat any `writers@` result as a lower bound
unless its residual is zero under a stated complete instruction universe.**

**Hard-Truth binding consequence (2026-08-07):** both consumers of this table's
domain proof are rejected while either missing premise remains. This includes
the older `typed_pointer_load` binding at `actor_player_contact_resolver`, not
only the jr-target island. A fresh verifier rejected its former grandfathering:
the binding's own attestation has `writer_value_domains_proved=false` and
`table_writer_universe.exhaustive=false` with 5,012 undecided stores. All 54 of
its ledger accesses, including 23 acceptance-fixture stores, are therefore
reopened. This is a proof-status correction; it does not alter the six-PC known
lower-bound writer set above.

## Known consumers (loads of `[0x80090748]`)

`actor_player_contact_resolver` `0x8004AC00`/`0x8004B698` ·
`berry_homing_target_acquire` `0x80057468` · `contact_vs_actor_handler`
`0x80058B3C` · `enemy_deathanim_finalize_remove_from_list` `0x80049B98` ·
`mover_updater` `0x8004D44C` · `player_contact_response`
`0x800472CC`/`0x80047774` · `projectile_aim` `0x80046D40` ·
`scene_geometry_draw_dispatcher` `0x8001E01C` · `seed_plant_mine_handler`
`0x8005C92C` · `seed_plant_propeller_handler` `0x8005C45C` ·
`damageable_object_ptr_mesh_transform` `0x80024E28` — plus overlay-side loads in
`LEVEL02_LEVEL1`, `LEVEL03_LEVEL` and `LEVEL10_LEVEL`.

This is consistent with the existing note that berry homing scans `0x80090748`
(see [[SYS_berry_projectile_and_homing|berry homing target acquisition]]).

## Why it matters for modding

The pool is a **fixed 64-slot array**, not a heap. A mod that adds actors past
slot 63 writes into whatever follows `0x800A1E80` — and `0x800A6500` (player
state) is not far above. Respect the 64 bound.

Because the table is fully repopulated from the pool each pass, patching a table
entry directly is pointless; patch the pool slot or the publish at `0x8004D378`.

## Evidence

Derived statically by `tools/phase4_typed_state_provenance.c` (rebuilt and run by
`tools/phase4_typed_state.py`; `--self-test` carries counterexamples) and
cross-checked against `analysis/phase4_static_frontier_index.json`. The corrected
six-writer result, residuals, and conditional move-domain claim are retained in
`analysis/phase4_typed_state.json` and
`analysis/phase4_f01_static_hard_truth.json`. Recorded in
[[EXP_2026-08-05_phase4_f01_objective_lifecycle]].
