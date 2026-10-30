---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Tools Catalog.md
aliases:
  - "Tools Catalog"
migration_action: superseded
superseded_by:
  - RE_BASELINE_INDEX
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Tools Catalog.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Tools Catalog
type: index
updated: 2026-07-02
tags: [index, tools]
---

# Tools Catalog

> Inventory of `tools/` (**127** Python files = **75 git-tracked + 52 untracked** host-local/WIP, local re-count 2026-06-28) plus the GUI front-end in `level_editor/`. The catalog was originally re-counted for 2026-06-21 ([[Gap Audit|GAP-0012]] — prior catalog 74; original ~38). `[T]` = git-tracked · `[U]` = untracked (host-local / newer work). The 2026-06-21 delta over 74 is the M7/M3 work now cataloged below — headline-replay traces (`trace_g29_pass3_arm_a/b`, `trace_level02_floor`), the GAP-0035 spawn/warp traces (`trace_initial_spawn`/`trace_warp_landing`/`trace_shell_warp`), and `exe_read`/`level_raw_chunk_manifest` — plus the untracked enemy/chaser/transform WIP cluster (already grouped below). Deeper source-of-truth: `docs/TOOLING.md`.
>
> **Portability + CI safety (re-audited 2026-06-21):** host paths resolve from env vars via `tools/_env.py` (`ABL_DIR`, `DUCKSTATION_DIR`, `ABL_SAVESTATES`); defaults match the dev host. `pip install -r tools/requirements.txt` (`Pillow`; the debugger client is stdlib). **0 hardcoded `/home/<user>` literals.** The only absolute paths are benign/overridable defaults — `/tmp/*.png` scratch (`abl_starry`, `enemy_mover`, `find_enemy`, `find_worm`), `/usr/local/bin/mkpsxiso` (`rebuild_with_patched_dat`, overridable), `/usr/share/fonts/...` (`patch_flik_word`) — not user-home leaks. **CI-safe split: 57 import-time pure-python vs 28** debugger/live/media tools (the 28 import `abl_dbg` or carry `PIL`/abs paths and fail at import in CI **by design**; the entire DAT/codec/seed/test family is CI-safe — it reads disc/level files only via runtime args). `tools/run_safe_tests.py` runs the safe subset; never feed BIOS/disc/save inputs to CI.

## GUI front-end (`level_editor/`)
| Tool | Track | Purpose |
|------|:--:|---------|
| `pyside_level_editor.py` | [T] | **Primary** editor: DAT type-0x3f inspection/edit-plan export + a working "3D Scene" tab (free-fly textured renderer, ray-pick, drag-to-move pickups) and a legacy "3D Tools" diagnostic tab. See [[ABL Level Editor]]. |
| `scene_importer.py` · `scene3d_view.py` · `textures.py` | [T] | Scene import (DAT meshes→tris), the moderngl 3D viewport, and LEVEL.RAW Region-A texture binding. |
| `run_pyside_level_editor.sh` · `requirements-pyside.txt` · `*.desktop` | [T] | Launcher (prefers `.venv`), deps (PySide6/moderngl/numpy), desktop entries. |
| `AblLevelEditor.java` | [T] | Java Swing fallback prototype (2D top-down inspector; single-source mode, no `javac`). |
| `abl_level_editor.py` | [T] | Older Tkinter prototype (no local tkinter; abandoned). `index.html`/`app.js` = retired browser prototype. |

## Build / verify workflow
Patch → rebuild → verify → restore. **Rule:** patch a *copy* of the DAT; keep `Disney-Pixar A Bug's Life (v1.0).bin/.cue` pristine ([[Preservation Policy]]).
1. `tools/patch_*.py <pristine DAT> <out DAT>` — verifies pristine bytes + size `0x51418`, hashes before/after.
2. `tools/rebuild_with_patched_dat.py --patched-dat <out> --target files/LEVEL01/LEVEL.DAT --out-bin <name>.bin --write` — stages into `REBUILD/abl.xml`, rebuilds with **mkpsxiso** (LBA **2906**), verifies embedded bytes, **restores pristine**.
3. Boot the image / load a save in DuckStation; observe. See [[Playbook - Create a deterministic experiment]].

## Catalog / inspection (read-only)
| Tool | Track | Purpose |
|------|:--:|---------|
| `catalog_type3f.py` | [T] | Unified non-mutating type-0x3f catalog (Option C Phase 1). |
| `campaign_level_inventory.py` | [T] | RCG-001 campaign-wide static inventory: stage→directory map, per-level DAT/RAW/sidecar profiles, type-0x3f kind counts, and generated [[Campaign Level Coverage Matrix]]. |
| `editor_visual_fidelity_audit.py` | [T] | RCG-002 static architecture audit: verifies live DuckStation renderer, VRAM readback, offline render harness, and writes [[Editor Visual Fidelity Baseline]]. |
| `level_goal_trigger_catalog.py` | [T] | RCG-003 runtime-save-state catalog: parses DuckStation v84 zstd states, extracts main RAM, scans sector-table region codes `0x800A7E48+sector*0x30+0x2E`, and writes [[Level Goal and Exit Trigger Matrix]]. |
| `catalog_level_grains.py` | [T] | CSV+MD catalog of kind-0x14 grain entries. |
| `list_level_pickups.py` | [T] | Classify all type-0x3f entries by source kind. |
| `tier3_native_object_inventory.py` | [U] | GAP-T3-1 static inventory: join native LEVEL01 type-0x3f objects with the current T3LV floor blob; reports native kind counts, custom-floor hits, and nearest objects to the authored Tier-3 mesh. |
| `list_level_grains.py` | [T] | List grain-source entries across LEVEL*.DAT. |
| `list_level_flik.py` | [T] | List candidate FLIK-letter placements. |
| `nearby_level_entries.py` | [T] | Spatial nearest-neighbor search in a DAT record. |
| `parse_level_raw_chunks.py` | [T] | Parse LEVEL.RAW chunk table; map runtime addr → chunk. |
| `survey_level01_payloads.py` | [T] | Survey/rank LEVEL01 geometry payloads (G15). |
| `analyze_g27_floor_candidates.py` | [T] | Decode/classify count-validated `fcn.80010000` payloads (G27). |
| `compare_level01_rams.py` | [T] | Diff LEVEL01 runtime globals between two RAM dumps. |
| `diagnose_injected_ram.py` | [T] | Diagnose the append-failure RAM dump. |
| `scan_state_refs.py` | [T] | Scan MIPS for refs to candidate state globals. |
| `exe_read.py` | [T] | Static PS-X EXE reader (vaddr→file offset, table/dispatch/xref/`--region-stats`). The trusted static-analysis engine behind the M3/M5/M6 EXE-read findings. |

## DAT patch / move / append
| Tool | Track | Purpose |
|------|:--:|---------|
| `dat_reloc.py` | [T] | **Relocation-aware** scanner + inserter + **deleters** (`build_reloc_insert`/`build_reloc_delete` type-0x3f + `build_reloc_delete_bytes` general mid-structure region delete; reproduces [[FUNC_8001CDC0]]'s 1248-site walk). The trusted engine. |
| `edit_pass1_records.py` | [T] | **Pass-1 scenery/prop write tool** (§11.1-2): `--list`/`--move`/`--set` (size-preserving X/Y/Z) + `--delete-index` (relocation-aware via `build_reloc_delete_bytes`, high-index-first, leaves the mesh payload orphaned). Dry-run default. In-game verified. |
| `sculpt_terrain.py` | [T] | **Terrain height-sculpt brush** (§1a): circular height brush (center/radius/falloff) over a FUNC_80010000 floor payload's vertex-Y (stride 0xc, Y@+2; +Y=down). Size-preserving DAT byte patch. **Spot-driven `--at-runtime-xz X:Z`** auto-picks the payload via `floor_source_map`. In-game: 33–36% visible deform. |
| `floor_source_map.py` | [T] | **Per-region floor-source map** (§1 residual): world XZ → which FUNC_80010000 floor payload draws it (30 payloads, `world = T_obj + v_local` footprints from the node array). `--query`/`--query-runtime`/`--list`. Enables "sculpt the floor anywhere." |
| `catalog_scenery.py` | [T] | **Scenery/decor object catalog** (§11.3a): pass-1 instance table → 152 meshes / 484 instances, with geometry + shape class (flat/tall/long/blocky). `--payload OFF` details one mesh's instances. Decor meshes are inline FUNC_80010000 payloads (not .ALL/.ANM); placement is translation-only (no rotation matrix). |
| `edit_collision_sector.py` | [T] | **Permanent collision edit** (§2): chunk-32 sector origin-Y (`--sector`/`--near-xz`, runtime/src delta) → recompress chunk 32 → splice LEVEL.RAW. In-game: moved Flik's footing 1:1 (−8000). Edits the 189 sectors in chunk 32 (array spans into chunk 33). |
| `edit_sector_region_code.py` | [T] | **Level-EXIT trigger edit** (§10): chunk-32 per-sector region code @`+0x2c` (→ runtime sector-table `+0x2e`); `--list`/`--set I:CODE`/`--clear I` → recompress chunk 32 → splice. Code 2 = the level exit (LEVEL01 = sector 177). Relocation proven in-game (177→108: same walk inert on pristine, ends the level on the edit). Rebuild via `build_autolayout_disc.py`. RE: `src_re/level_exit_trigger.c`. |
| `edit_collision_plane.py` | [T] | **Per-plane collision edit (§2.2): walls/slopes.** Edits an oriented PLANE record in chunk 32 (s16 normal @+0/2/4 \|n\|=0x4000, ref @+6/8/a) by chunk-32 offset — tilt normal / move ref / `--zero-normal` (disable). Recompress+splice (round-trip verified) → `build_autolayout_disc.py`. Resolver = swept [[FUNC_800345CC]]; RE `src_re/collision_plane_resolver_800345cc.c`. Live-verified (A/B walk diverged Flik's path). 6 planes in LEVEL01 (sectors 119/166). |
| `probe_collision_planes.py` | [L] | **LIVE: list the oriented collision planes** (§2.2) — index/sector/chunk-32 offset/normal/ref/world/slope-vs-wall, from the runtime tables `0x8009c230`/`0x80091718` (count `gp+0x57c`). Read-only; feeds `edit_collision_plane.py --offset`. |
| `probe_collision_sector.py` | [L] | **LIVE: find the resolver's SELECTED collision sector under Flik** (§2.1). Binary-search poke-probe over all chunk-32 sectors (poke group origin-Y → nudge → which moves Flik). Reliably finds the floor (spawn = sec99) where XZ-proximity fails. Feeds a localized matched bump (`sculpt_terrain` + `edit_collision_sector`, same Δ — 1:1). |
| `edit_dat_coord_record.py` | [T] | **Edit uncompressed LEVEL.DAT coord records** (§3): mover-VM patrol waypoints (rec1 @ 0x468 type 1, in-game CONFIRMED — relocates a mover object) + the type-11/12/13 polygon zones (editable; "chaser spawn area" role unconfirmed). `--list`/`--record OFF --move/--set-entry`, size-preserving. |
| `build_autolayout_disc.py` | [T] | **Multi-file auto-layout disc builder**: stages arbitrary patched files (size-changing RAW ok) → mkpsxiso `abl_autolayout.xml` (+`-lba`) → restore → verify embedded at recomputed LBA. Used for collision / matched terrain+collision / HUD-word builds. |
| `insert_type3f_entries.py` | [T] | Safe multi-entry append wrapper over `dat_reloc` (dry-run default). |
| `delete_type3f_entries.py` | [T] | Safe multi-entry **DELETE** wrapper over `dat_reloc.build_reloc_delete` (inverse of append; CC5). Removes entries by index high-first, decrements count, bumps baked offsets −0x10; risk-gated (FLIK/telescope/unknown); dry-run default. |
| `apply_level_placements.py` | [T] | Declarative placement-spec runner (the editor's export target). |
| `mod/build.py` | [T] | **One-command modded-disc build** (the editor's "Build Modded Disc" backend, CC1). Code patches (`mod/patch.asm` + C caves) **and/or** `--placements <spec>` data edits → apply → stage into `REBUILD/files` → mkpsxiso → restore-to-pristine → verify embedded at LBA. Uses XA-aware Form2 payload verification for `.XA` files. `--no-code` = data-only; `--no-disc` = patch+verify, skip ISO. For a net-new kind (CC6) the editor drops `--no-code` so the caves are applied. |
| `custom_objects.py` | [T] | **Net-new-object registry** loader (CC6): reads `mod/custom_objects/*.json` (kind/label/`requires_code`/placement_op/default pos). The editor uses it to offer custom pickups (blackberry 0x25) and to decide a plan must build WITH code. |
| `move_type3f_entry.py` | [T] | Conservative fixed-size mover (preserves kind/aux). |
| `patch_level_entry.py` | [T] | Patch X/Y/Z of entries by index/kind. |
| `patch_level_grain.py` | [T] | Patch grain (0x14) Y. |
| `patch_flik_word.py` | [T] | Replace HUD "FLIK" glyph textures with an arbitrary 4-letter word (LEVEL.RAW). |
| `flik_emblem_edit.py` | [T] | Replace the FLIK completion emblem from a user image. Training routes to `LEVEL00/LEVEL.RAW` chunk 3 rect `64,96,64,80`; LEVEL01 routes to both `LEVEL01/LEVEL.RAW` chunk 13 and `LEVEL01/LEVEL1.RAW` chunk 12 rect `64,0,64,64`. Size-changing, so it ships through the auto-layout build path. |
| `build_flik_word_disc.py` | [T] | **One-command HUD-word disc** (editor "Build HUD-Word Disc" backend, §7). Validates the word vs `glyph_assets.available_letters()`, patches LEVEL.RAW+LEVEL1.RAW, rebuilds with the **auto-layout** manifest (recompressed RAW balloons → can't use fixed-LBA `abl.xml`), restores pristine, verifies LEVEL.RAW embedded at its `-lba` LBA. In-game verified (TAKA). |
| `add_level_entry.py` | [T] | ⚠️ naive single append — leaves stale offsets. Obsolete (use `dat_reloc`). |
| `build_markers_54_55_57.py` | [U] | ⚠️ obsolete diagnostic — sacrifices real berries. |

## Geometry G-series patch builders (one DAT build per experiment)
All share `input_dat output_dat [--force]`, validate `EXPECTED_SIZE=0x51418`. [T] all.
`patch_g6_render_sentinel_test` · `patch_g8_entry24_plus08_test` · `…_plus08_a2_test` · `…_plus04_c_test` · `patch_g12_entry29_source_vec_test` · `patch_g13_entry29_payload_v0_test` · `patch_g14_entry29_payload_vertex_test` · `patch_g15_runtime_payload_vertex_test` · `patch_g16_emitted_payload_vertex_test` · `patch_g28_candidate_a_floor_y_test`. → [[Experiments Index]].

## Rebuild
| Tool | Track | Purpose |
|------|:--:|---------|
| `rebuild_with_patched_dat.py` | [T] | Stage patched DAT → mkpsxiso rebuild → verify embedded bytes → restore. |
| `build_per_enemy_discs.py` | [U] | Build one disc per enemy, each relocating only that enemy (RAW chunk-31 / DAT patrol). |

## LEVEL.RAW codec
| Tool | Track | Purpose |
|------|:--:|---------|
| `decode_level_raw.py` | [T] | **Byte-exact** LEVEL.RAW decompressor (faithful port of [[FUNC_8001A1DC]]). |
| `recompress_level_raw.py` | [T] | Literal-run recompressor, round-trip-validated vs the decoder (not byte-exact PROPACK → [[Gap Audit\|GAP-0024]]). |
| `dump_level_raw.py` | [T] | Decompress all of LEVEL01/LEVEL.RAW + a chunk index. |
| `level_raw_chunk_manifest.py` | [T] | Metadata-only 69-chunk **role manifest** (→ `level_raw_chunk_roles.json`); reproducible, CI-tested ([[Gap Audit\|GAP-0022]]). No payload bytes emitted. |
| `seed_table.py` | [T] | Typed parser/editor for the **chunk-31 seed table** (0x1c-byte records) + chunk read/splice over the codec above. Editor-facing seed layer (M6). |
| `apply_seed_edits.py` | [T] | Declarative chunk-31 seed move/set **spec runner** (dedicated schema; mirrors `apply_level_placements.py`). Decompress→edit→recompress→splice→new LEVEL.RAW; rebuild via `rebuild_with_patched_dat.py --target files/LEVEL01/LEVEL.RAW`. |

## Live-debugger client / GPU injection
| Tool | Track | Purpose |
|------|:--:|---------|
| `abl_dbg.py` | [T] | RE driver over the DuckStation external debugger (`from abl_dbg import D`). Env-portable. |
| `abl_starry.py` | [T] | Starry-night sky edit + injected MIPS GP0 display list ([[Finding - GPU primitive injection]]). |
| `abl_night_hook.py` | [T] | **Persistent** per-frame nighttime back-buffer hook ([[Finding - Persistent night render hook]]). |
| `vramdiff.py` | [T] | VRAM framebuffer diff helper (native BGR555; phase-matched diff). |
| `test_overlay_stuck_seed.py` | [T] | Live-test the cd.* sector-overlay API to relocate a stuck seed (needs a running instance). |
| `_step3.py` | [U] | Scratch helper: connect, load `_1.sav`, expose client for tpage/VRAM. |

## Enemy / mover suite (mostly [U] — newer work)
`enemy_mover` · `find_enemy` · `find_bee` · `find_worm` · `find_chaser_home` · `trace_chaser_spawn` · `nav_to_worm` · `movie_pill_check` · `show_moved_pill` · `show_moved_worm` · `verify_enemy_move` · `verify_chaser_move` — all `[U]`: identify/classify/trace and verify enemy relocation (force + phase-matched frame-diff). See [[Enemy relocation method]]. · `verify_seed_move_ingame` `[T]` · `verify_stuck_seed_move` `[T]` — confirm LEVEL.RAW seed edits propagate after booting an edited disc.

## Transform / trace (geometry math)
`transform_math` `[U]` (pure 3×3 linear algebra) · `trace_terrain_transform` `[U]` (execTrace RTPT @0x80017464) · `analyze_terrain_transform` `[U]` (trace→chunk-34/35 model→view) · `trace_camera_transform` `[U]` (camera→world view⁻¹) · `trace_spawn_ground_source` `[U]` (live source of the visible spawn ground → [[Gap Audit\|GAP-0011]]) · `trace_spawn_floor.py` `[T]` (**M7 replayable headline**: asserts `game_serial`, loads a LEVEL01 spawn fixture, picks the floor + write-watches its packet + classifies every `fcn.80010000` source, prints a CONFIRMED verdict — [[Experiment - Spawn-floor render source]]; resolves [[Gap Audit\|GAP-0011]]).

## Spawn / warp / headline traces (live-debugger replays, [T])
> Operator-local (GAP-0001); each authenticates + asserts game/scene/fixture identity (`getStateInfo` media match), emits deterministic JSON, self-checks its verdict, and ships **no media**. Pattern: [[Playbook - Replay headline experiments]].
- `trace_g29_pass3_arm_a.py` · `trace_g29_pass3_arm_b.py` `[T]` — **M7** pristine vs G28-edited collision arms of the G29 Pass-3 counterfactual (Arm B rebuilds the G28 BIN locally, embedded-verified) → [[Experiment - G29 Pass-3 differential]] ([[Gap Audit\|GAP-0038]] Verified).
- `trace_level02_floor.py` `[T]` — **M7** per-pixel LEVEL02 (scene 3) floor render source (pick→leaf→caller `ra`, DAT via `fcn.80010000`) → [[Experiment - LEVEL02 floor source]] ([[Gap Audit\|GAP-0039]]).
- `trace_initial_spawn.py` `[T]` — write-watch the LEVEL01 cold-boot player spawn → [[FUNC_80046B20]] ← resident table `0x80077314` ([[Experiment - Initial spawn write-watch]], GAP-0035).
- `trace_warp_landing.py` `[T]` — divert the cold-boot scene-select to capture non-LEVEL01 warp landings (scene 3/6/2/4, clean) → [[Experiment - Warp landing diversion]] (GAP-0035).
- `trace_shell_warp.py` `[T]` — in-game warp-trigger investigation (orchestrator + transition-state lever `0x800823a0`) → [[Experiment - In-game warp trigger]] (GAP-0035).

## Regression / validation / tests
| Tool | Track | Purpose |
|------|:--:|---------|
| `validate_levels_phase6.py` | [T] | Cross-level non-mutating validation. |
| `regress_type3f_insert.py` · `regress_rebuild_with_patched_dat.py` · `regress_validate_levels_phase6.py` | [T] | Regressions for the append/rebuild/validate wrappers (tmp-only). |
| `regress_editor_build_path.py` | [T] | CC1 regression: editor↔`mod/build.py` contract (`_placements_target` + `Operation.to_yaml` + delete ordering) + `build.py --no-code --no-disc` apply leaves REBUILD pristine (no ISO). |
| `regress_type3f_delete.py` | [T] | CC5 regression: delete engine invariants (round-trip `delete(append(X))==X`, site-count, survivor shift), CLI risk gates, and `apply_level_placements` delete-op parity (tmp-only). |
| `regress_flik_word.py` | [T] | §7 regression: `glyph_assets.available_letters`, `build_flik_word_disc` word validation + `-lba` log parse (dir-disambiguated), editor word helpers (no ISO/emulator). |
| `regress_custom_objects.py` | [T] | CC6 regression: custom-object registry, editor dropdown + `_plan_requires_code` wiring, and per-op `allow_unknown` accept/reject in `apply_level_placements` (no ISO/emulator). |
| `regress_pass1_records.py` | [T] | §11.1-2 regression: `build_reloc_delete_bytes` invariants (delete at first/mid/last, survivor XYZ, in-bounds, −2 sites) + `edit_pass1_records` list/move/set/delete/verify (tmp-only). |
| `regress_sculpt.py` | [T] | §1a/§2 regression: `sculpt_terrain` brush math (size-preserving, only-Y, falloff/flat/clamp), `edit_collision_sector` (sector parse, chunk-32 bound + chunk-33 guard, recompress+splice round-trip), `build_autolayout_disc` LBA parse (no ISO/emulator). |
| `regress_dat_coord_record.py` | [T] | §3 regression: `edit_dat_coord_record` discovery (mover waypoints + zones, excludes type-0x3f), size-preserving translate/set-entry, only-record-changed guard, non-coord refusal (tmp-only). |
| `regress_floor_source_map.py` | [T] | §1/step-9 regression: `floor_source_map` node-array parse + footprints + XZ query (spawn→0x1b9f0), and `sculpt_terrain.resolve_at_xz` spot-driven hook (payload + in-bbox center). |
| `regress_catalog_scenery.py` | [T] | §11.3a regression: `catalog_scenery` pass-1 walk (484 instances, 152 payloads, top 0x2d460 ×93, the 2 anomalous 0x2f700 records) + shape_class (tmp-free). |
| `regress_level_raw_codec.py` | [T] | CC2 regression: decode byte-exact (69 chunks → 1269304 B), provenance alignment (the fixed tracker, 1:1 + in-range), recompress round-trip. Guards the codec. |
| `test_transform_math.py` · `test_camera_transform.py` · `test_trace_terrain_transform.py` · `test_spawn_ground_source.py` | [U] | Standalone unit tests (no emulator). |
| `run_safe_tests.py` | [T] | M2 pytest runner; excludes `gpu`, `live`, and `local_media` markers. |
| `tests/test_level_raw_codec.py` | [T] | Policy-approved oracle decode plus deterministic synthetic encode/decode regressions. |
| `tests/test_repro_manifest.py` · `test_tool_sanity.py` · `test_path_portability.py` | [T] | Manifest integrity, tracked-tool syntax/import, and host-path checks. |

> Safe CI is defined in `.github/workflows/safe-tests.yml` ([[Gap Audit|GAP-0017]]). It never uses disc/BIOS/save/emulator inputs. GPU/editor and live DuckStation checks remain isolated local paths; versions and classifications are in [[Toolchain Census]].

## M0 support (new, 2026-06-20)
| Tool | Track | Purpose |
|------|:--:|---------|
| `_env.py` | [T] | Canonical host-path resolver (`ABL_DIR`/`DUCKSTATION_DIR`/`ABL_SAVESTATES`/`DEBUGGER_CLIENT`). |
| `verify_repro_inputs.py` | [T] | Hash-checks critical inputs (findings store + codec oracles + fork pin) → `repro_inputs.sha256`; guards the findings-store overwrite hazard ([[Gap Audit\|GAP-0002]]). |
| `requirements.txt` | [T] | Exact Python pins (`Pillow`, `pytest`); evidence and external tools in [[Toolchain Census]]. |

## M3 support (new, 2026-06-20)
| Tool | Track | Purpose |
|------|:--:|---------|
| `validate_symbol_map.py` | [T] | Validates unique/sorted DuckStation `AAAAAAAA label` syntax for `symbols/re_symbols.sym`; covered by the safe pytest suite. |
| `symbol_roundtrip.py` | [T] | Converts the symbol baseline to exact DuckStation CSV or r2 flag commands, reparses the result, and requires 85/85 address/name preservation; generated files are temporary. |

## Related
[[Home]] · [[Project Index]] · [[Toolchain Census]] · [[CONTRIBUTING]] · [[Preservation Policy]] · [[Playbook - Create a deterministic experiment]] · [[Experiments Index]] · [[Asset - Disc image and rebuild]]
