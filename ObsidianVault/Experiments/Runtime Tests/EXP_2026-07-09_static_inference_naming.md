---
kind: experiment
id: EXP_2026-07-09_static_inference_naming
name: Static-inference naming at scale — resident unknown 215 → 0
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census, SYS_decomp_substrate]
fixtures: []
artifacts: [symbols/re_symbols.sym, analysis/functions.json, analysis/extent_overrides.json, tools/function_census.py, analysis/naming/sc1_batch01.json, analysis/naming/sc1_batch02.json, analysis/naming/sc1_batch03_clusters.json, analysis/naming/sc1_batch04_lib.json, analysis/naming/sc1_batch05_final.json, analysis/naming/sc1_batch06_residual.json]
---

# EXP_2026-07-09_static_inference_naming

## Question
After u1–u3, the runtime-trace naming accelerator was **exhausted**: the residual 215 unknown resident
functions are load-time / init / event functions that don't fire in idle mid-scene saves (validated —
the exec-trace mechanism works, `mover_vm` fired 60×, but the residual fired **0 across scenario saves +
driven input**, 2/42). Can the residual be named to **zero** by static call-graph + disassembly
inference, evidence-gated, without breaking the byte-exact rebuild?

## Method
**Parallel static inference.** For each unknown, a grounded bundle
(`$JOBDIR/tmp/bundle.py`: disasm + resolved callers/callees + referenced named globals) was fed to a
general-purpose sub-agent, which proposed an evidence-cited name (or a `RECLASSIFY_DATA` flag). Each
proposal cites the specific offsets/callers/callees it was derived from; the parent verified a sample
against raw disassembly, then applied via `tools/apply_symbol_names.py` (enforces uniqueness + evidence +
resident-start). Every batch re-ran `function_census.py` + `validate_build.py` (SHA-1 must hold) +
`run_safe_tests.py`. Waves (manifests in `analysis/naming/`):

| Wave | Scope | unknown |
|---|---|---|
| sc1_batch01 | 46 with-caller game fns | 215 → 169 |
| sc1_batch02 | 73 no-caller game fns (indirect/dispatch) | 169 → 96 |
| sc1_batch03 | 12 mechanical clusters (scene-flow, mover-VM, anim) | 96 → 84 |
| (sc-2) | 8 alignment-padding words → data | 84 → 76 |
| sc1_batch04 | 21 PsyQ library `_body` tails + helpers | 76 → 55 |
| sc1_batch05 | 13 stubs / wrappers / predicates | 55 → 42 |
| sc1_batch06 | final 42 fragment taxonomy (below) | 42 → **0** |

## The residual fragment taxonomy (the last 42)
Nearly all 42 were **function-boundary artifacts**, classified per case:
- **A — fall-through preamble** (24): a caller-reachable entry that preloads a register the *next* named
  function immediately uses, then falls through. Real alternate entry point → named `<target>_entry`.
- **B — mis-split tail / case-body** (4): the interior/epilogue of the *preceding* named function
  (no prologue; frees a frame it never allocated, or a jump-table case-body). These were **extent-merged**
  into their parents (`extent_overrides.json` + `segments.yml` parent-`.s` regenerated to cover the
  merged range + tail segment dropped): `berry_projectile_update` (+0x5a9ac), `actor_skinned_update`
  (+0x56ef0), `collision_grid_l_level_overlay__glue` (+0x3d678), `bulk_ground_sub_emitter` (+0x19b48).
- **C — standalone unnamed function** (13): named by role (`gte_vec_length_sqrt_helper`,
  `clear_gameplay_pool_on_reset`, `exception_context_save`, `handler_register_8007fbd4`, pad thunks,
  nullsubs, …).
- **D — genuine data** (3): invalid-opcode word pairs in libgte/BIOS-thunk regions →
  `_RESIDENT_DATA_OVERRIDE` (census-only; build unchanged).

## Result
**Resident unknown 215 → 0; `all_resident_candidates_classified` FLIPPED True.** `re_symbols.sym`
761 → 1301 symbols; every resident code function (900 after the 4 extent-merges) carries a **real
descriptive name** — zero `FUNC_`/`sub_` placeholders, zero named-not-merged fragments. SHA-1
`af43de22…` held through every commit; 110 safe tests green.

**Notable discoveries surfaced by the sweep:** `decompress_lz_bitstream` (the LEVEL.RAW LZ codec),
`vsprintf_core` / `text_stream_printf`, `mesh_draw_command_interpreter`, `build_render_survivor_list`
(GTE cull), `object_animate_rotation_matrix`, `load_character_models`, `serialize_savegame_buffer`,
`enemy_deathanim_finalize_remove_from_list`, `sfx_proximity_priority_gate`, and full clusters
(spawn_drop bursts, mover-VM opcode handlers, GTE/GPU primitive builders, PsyQ library `_body` tails).

**Honesty note.** Names are **inferred** tier (deduced from static evidence), not runtime-proven; the
per-name evidence + rationale is preserved in the `analysis/naming/sc1_batch*.json` manifests. The
acceptance safety test was rewritten to the true invariant `gate == (unknown == 0)`.
See [[SYS_function_census]] · [[SYS_decomp_substrate]] · [[EXP_2026-07-09_audio_engine_probe]].
