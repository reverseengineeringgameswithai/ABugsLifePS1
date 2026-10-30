---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Symbol Map Baseline.md
aliases:
  - "Symbol Map Baseline"
migration_action: superseded
superseded_by:
  - SYS_executable_image
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Symbol Map Baseline.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Symbol Map Baseline
type: reference
updated: 2026-06-20
tags: [symbols, executable, debugger, milestone3, gap-0018]
---

# Symbol map baseline

> Human-reviewed companion to `symbols/re_symbols.sym`. The `.sym` file is deliberately conservative: one sorted `AAAAAAAA label` per line, no comments or binary data, validated by `tools/validate_symbol_map.py`. Generic `FUNC_<ADDR>` labels preserve identity where a semantic rename could overstate evidence.

## Import and authority

- DuckStation committed HEAD supports `debugger.importSymbols` / `exportSymbols`; see [[API - symbols]].
- Import path: `debugger.importSymbols {path:"<absolute>/symbols/re_symbols.sym", format:"sym", merge:true}`.
- [[Symbol Import Round Trip]] proves 85/85 address/name pairs through the fork-compatible CSV representation and an r2 flag script; r2 5.9.8 actually consumed all 85 flags. The safe suite repeats both conversions in temporary files.
- Live DuckStation import has **not** been run because no debugger server was active and GAP-0001's current fork/binary is dirty and local-only. It is optional corroboration, not the reproducible M3 proof.
- This note records semantic confidence. The machine file is an import artifact, not authority over contradictory findings.
- Overlay labels are only meaningful when the named module is resident.

## Resident function labels

| Address / import label | Role | Type | Confidence | Modding-critical | Source |
|---|---|---|---|:--:|---|
| `80010000 FUNC_80010000` | mesh payload projector/emitter | function | Verified | Yes | [[FUNC_80010000]] |
| `800140A0 FUNC_800140A0` | GTE trail-cull transform | function | Verified | Yes | [[FUNC_800140A0]] |
| `800172DC FUNC_800172DC` | shared/active mesh renderer; historical terrain-specific naming disputed | function | Needs Evidence for broad role | Yes | [[FUNC_800172DC]], GAP-0010 |
| `80017B98 FUNC_80017B98` | GTE rotation-matrix setup | function | Verified | Yes | [[FUNC_80017B98]] |
| `80019934 FUNC_80019934` | bulk-ground sub-emitter | function | Verified | Yes | [[FUNC_80019934]] |
| `8001A1DC FUNC_8001A1DC` | LEVEL.RAW decompressor | function | Verified identity; body partial | Yes | [[FUNC_8001A1DC]] |
| `8001CDC0 FUNC_8001CDC0` | DAT parser/relocator | function | Verified | Yes | [[FUNC_8001CDC0]] |
| `8001DFE4 FUNC_8001DFE4` | scene-geometry dispatch | function | Verified | Yes | [[FUNC_8001DFE4]] |
| `8001EA6C FUNC_8001EA6C` | survivor-list builder 1 | function | Verified | No | [[FUNC_8001EA6C]] |
| `800206E8 FUNC_800206E8` | survivor-list builder 2 | function | Verified | No | [[FUNC_800206E8]] |
| `800224EC FUNC_800224EC` | scene/render driver | function | Verified | Yes | [[FUNC_800224EC]] |
| `80025084 FUNC_80025084` | oriented containment/range test | function | Verified | Yes | [[FUNC_80025084]] |
| `80030F60 FUNC_80030F60` | collision sector-table builder | function | Verified | Yes | [[FUNC_80030F60]] |
| `800345CC FUNC_800345CC` | collision resolver | function | Verified | Yes | [[FUNC_800345CC]] |
| `8003633C FUNC_8003633C` | player movement/collision integrator | function | Verified | Yes | [[FUNC_8003633C]] |
| `80036CEC player_y_commit_store` | store PC inside `FUNC_8003633C` | code label | Verified | Yes | [[FUNC_8003633C]] |
| `8003A318 FUNC_8003A318` | high-heap LEVEL.RAW load/decompress orchestrator | function | Verified | Yes | [[FUNC_8003A318]] |
| `8003CF2C FUNC_8003CF2C` | resource-ID/DAT-load dispatcher | function | Verified | Yes | [[FUNC_8003CF2C]] |
| `8003E928 FUNC_8003E928` | horizon/sky-strip draw | function | Verified | Yes | [[FUNC_8003E928]] |
| `80046330 FUNC_80046330` | universal file loader | function | Verified | Yes | [[FUNC_80046330]] |
| `8004ECD4 gameplay_state_machine` | gameplay state machine | function | Verified role | Yes | [[Systems]] / executable docs |
| `8004FA40 main_shell_state_machine` | top-level shell | function | Verified role | Yes | [[Systems]] / executable docs |
| `800526F4 FUNC_800526F4` | HUD draw | function | Verified | Yes | [[FUNC_800526F4]] |
| `80053814 FUNC_80053814` | type-`0x3F` construct/contact dispatch | function | Verified | Yes | [[FUNC_80053814]] |
| `80054EAC FUNC_80054EAC` | grain pickup handler | function | Verified | Yes | [[FUNC_80054EAC]] |
| `800586B0 FUNC_800586B0` | contact/pickup walker | function | Verified | Yes | [[FUNC_800586B0]] |
| `80059E44 FUNC_80059E44` | contact-record allocator | function | Verified | Yes | [[FUNC_80059E44]] |
| `8005B134 FUNC_8005B134` | dispatcher; prior player-position claim superseded | function | Needs Evidence | No | [[FUNC_8005B134]] |
| `8005EC94 FUNC_8005EC94` | animation keyframe core | function | Verified | Yes | [[FUNC_8005EC94]] |
| `8005F690 entry0` | PS-X EXE entry/crt0 | function | Verified | No | PS-X header / executable docs |
| `80060724 FUNC_80060724` | libgte transform leaf | function | Verified | No | [[FUNC_80060724]] |
| `800639CC FUNC_800639CC` | DRAWENV background-fill builder | function | Verified | Yes | [[FUNC_800639CC]] |

## Resident globals and buffers

| Address / import label | Role / type | Confidence | Modding-critical | Source |
|---|---|---|:--:|---|
| `800771BC/C0/C4 sky_clear_r/g/b` | sky clear-color cache scalars | Verified | Yes | [[MEM - Sky DRAWENV color cache 800771BC]] |
| `8007941C contact_metadata_table_b` | contact metadata table | Verified address/producer | Yes | [[MEM - Contact array 800B0D18]] |
| `80079E30 contact_metadata_table_a` | render/contact metadata table | Verified address; some fields partial | Yes | [[MEM - Contact array 800B0D18]] |
| `80081D98 runtime_gp` | runtime GP anchor | Verified | Yes | [[Symbols Index]], executable docs |
| `800822F0 G_DAT_ENTRY_COUNTER` | parser entry counter | Verified | Yes | [[FUNC_8001CDC0]] |
| `80082338 G_PASS2_BASE_PTR` | pass-2 base pointer | Verified | Yes | [[MEM - Trail and pass3 tables]] |
| `8008234C contact_alloc_cursor` | contact allocator cursor | Verified | Yes | [[MEM - Contact array 800B0D18]] |
| `800823A0 master_game_state` | main game state | Verified | Yes | [[Systems]] / executable docs |
| `8008240C G_GPU_OT_OUTPUT_BUFFER_PTR` | active OT/output pointer | Verified | Yes | [[MEM - OT output buffer pointer 8008240C]] |
| `8008243C main_shell_substate` | six-way shell substate | Verified | Yes | executable docs |
| `80082498 G_DAT_BASE_PTR` | runtime DAT base pointer | Verified | Yes | [[MEM - DAT runtime memory map]] |
| `800824AC G_TRAIL_BLOCK_PTR` | trail/pass-1 pointer | Verified | Yes | [[MEM - Trail and pass3 tables]] |
| `80082504 current_scene_id` | scene ID | Verified | Yes | [[Systems]] / executable docs |
| `80082508 G_PASS3_BASE_PTR` | pass-3 pointer | Verified | Yes | [[MEM - Trail and pass3 tables]] |
| `80089528 matrix_lut` | matrix lookup table | Needs Evidence for role | No | [[Symbols Index]] |
| `800901C8 render_body_gating_mask` | body-field render gating bitmask | Verified use | Yes | [[MEM - Trail and pass3 tables]] |
| `80096B98 object_pointer_list` | 128 object pointers | Verified | Yes | executable overlay analysis |
| `80096DA0 dynamic_dat_type_pointer_table` | DAT type→record pointer table | Verified | Yes | [[FUNC_8001CDC0]] |
| `80096DA4 proximity_table_ptr` | proximity table base/pointer use | Needs Evidence for final name | Yes | executable overlay analysis |
| `80096E9C type_3f_record_pointer` | type-`0x3F` source pointer | Verified | Yes | [[MEM - Type-0x3f placement record]] |
| `80096EA8 / 8009E338 render_survivor_list_a/b` | render survivor lists | Verified | No | [[MEM - Survivor lists]] |
| `8009C230 collision_candidate_list` | per-frame candidate list | Verified | Yes | [[MEM - Collision sector table 800A7E48]] |
| `8009C870 visual_sprite_object_pool` | 8 × `0x344` object pool | Verified | Yes | [[Rendering]], executable docs |
| `800A6500/04/08 player_x/y/z` | player position words | Verified | Yes | [[MEM - Player state 800A6500]] |
| `800A652C player_velocity_delta` | velocity/delta field | Needs Evidence for full vector semantics | Yes | [[MEM - Player state 800A6500]] |
| `800A6597 berry_flik_marker` | progress marker | Verified address; exact dual role contextual | Yes | [[MEM - Player state 800A6500]] |
| `800A6598/99/9A seed_counter_0/1/2` | seed counters | Verified | Yes | [[MEM - Player state 800A6500]] |
| `800A65A1 grain_count_hud_mirror` | grain count | Verified | Yes | [[MEM - Player state 800A6500]] |
| `800A65A2 flik_bitmask` | FLIK-letter mask | Verified | Yes | [[MEM - Player state 800A6500]] |
| `800A7E48 collision_sector_table` | 223 × `0x30` collision sectors | Verified | Yes | [[MEM - Collision sector table 800A7E48]] |
| `800AA128 player_collision_sector_record` | documented sector-186 record | Verified for fixture | Yes | [[Finding - Collision lever sector186]] |
| `800B0D18 contact_record_array` | 64 × `0x38` contacts/pickups | Verified | Yes | [[MEM - Contact array 800B0D18]] |
| `800C1688 sky_color_source_table` | on-disk-derived sky colors | Verified | Yes | [[MEM - Sky DRAWENV color cache 800771BC]] |
| `800C1690 collision_plane_block` | collision-plane block example | Verified address/example | Yes | [[MEM - Collision plane record]] |
| `80115AAC level_raw_compressed_base` | LEVEL01 compressed RAW buffer | Verified for LEVEL01 | Yes | [[MEM - LEVEL.RAW chunk model]] |
| `8012C1D0 active_mesh_vertex_buffer` | shared mesh buffer; historical terrain label disputed | Verified address; role Needs Evidence | Yes | [[MEM - Terrain vertex buffer 8012C1D0]], GAP-0010 |
| `801607F8 level_dat_runtime_base` | LEVEL01 DAT image base | Verified for LEVEL01 | Yes | [[MEM - DAT runtime memory map]] |
| `80161CFC trail_pass1_block` | pass-1 block | Verified for LEVEL01 | Yes | [[MEM - Trail and pass3 tables]] |
| `801642E4 pass3_block` | pass-3 block | Verified for LEVEL01 | Yes | same |
| `801B1C10 parser_output_records` | 484 × `0x20` output records | Verified for LEVEL01 | Yes | [[MEM - Parser output record]] |

## Conditional/provisional labels

| Address / import label | Scope | Confidence | Import guidance | Source |
|---|---|---|---|---|
| `1F800374 provisional_camera_scratch_1F800374` | scratchpad | Needs Evidence | Safe syntactically; provisional semantic label | [[Symbols Index]] |
| `1F800384 provisional_view_vector_scratch_1F800384` | scratchpad | Needs Evidence | same | [[Symbols Index]] |
| `1F8003B4 provisional_view_matrix_scratch_1F8003B4` | scratchpad | Needs Evidence | same | [[Symbols Index]] |
| `800B39A0 region_a_overlay_base` | Region A swap base | Verified | Safe base label; module-qualified sublabels required | [[Executable and Overlays]] |
| `800B39A4 level_overlay_init` | Region A `LEVEL*.BIN` universal init | Verified across inspected variants | Import only with Region A context | [[Executable and Overlays]] |
| `800B5788 region_b_overlay_base` | Region B swap base | Verified | Safe base label; content varies (`MEMORY.BIN`/`FMV.BIN`) | [[Executable and Overlays]] |

Approximate collision-plane addresses such as `~0x800D0xxx` are deliberately excluded from the import file. A range or uncertain pointer is not a symbol.

## Validation and update rules

```bash
python3 tools/validate_symbol_map.py
python3 tools/symbol_roundtrip.py --format duckstation-csv --output /tmp/abl-re-symbols.csv
python3 tools/symbol_roundtrip.py --format r2 --output /tmp/abl-re-symbols.r2
```

The validator requires uppercase eight-digit addresses, identifier-safe unique labels, unique addresses, and strict numeric sorting. The round-trip tool preserves address/name only because `.sym` has no type field; type/confidence remain authoritative in this note. When adding a symbol: update this note and `symbols/re_symbols.sym` together; cite a `FUNC_`, `MEM -`, finding, or exact executable evidence; use generic/provisional names when semantics are not verified.

## Related

[[Symbol Import Round Trip]] · [[Symbols Index]] · [[Functions Index]] · [[Memory Structures]] · [[MEM - Global memory map]] · [[Executable and Overlays]] · [[API - symbols]] · [[Decompilation Pilot]]
