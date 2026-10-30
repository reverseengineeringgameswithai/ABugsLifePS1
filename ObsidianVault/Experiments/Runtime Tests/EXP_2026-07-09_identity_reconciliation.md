---
kind: experiment
id: EXP_2026-07-09_identity_reconciliation
name: Contested function-identity reconciliation (RCA a3)
status: success
confidence: inferred
source_state: evidence
validates: [SYS_function_census, SYS_re_evidence_policy]
artifacts: [symbols/re_symbols.sym, flik_to_level01_stall.mv.movie.json]
---

# EXP_2026-07-09_identity_reconciliation

## Question
Several addresses carried conflicting names across the note title, `re_symbols.sym`, `src_re`, and the
auto-memory (AUDIT-12..17). Which name is authoritative, and can a disc-safe runtime pass corroborate it
before the name is propagated everywhere?

## Method (throwaway instance, pristine disc, no save state)
Launched the isolated debugger instance (port 23460, token `debugger-1000`; **operator port 2346 untouched**).
Booted the **pristine** `Disney-Pixar A Bug's Life (v1.0).cue` and replayed the from-boot movie
`flik_to_level01_stall.mv.movie.json` to LEVEL01 (`current_scene_id`@`0x80082504` = 1). Ran `functionBounds`,
`xrefsTo`, `disassemble`, and `accessLog` write-watches. Instance stopped after.

## Findings
1. **Structural distinctness confirmed (disc-safe, resident EXE).** `debugger.functionBounds` returns
   `confidence:"exact"` for `0x80059E44` (**76** callers), `0x8005BDBC` (**2** callers), and `0x8003E760`
   (**13** callers) — three **distinct** real functions. This proves the note `FUNC_8005BDBC_fcn_8003e760.md`
   wrongly embedded a **foreign** address: `0x8003E760` is `token_descriptor_reskin`, NOT `plant_spawn`
   (AUDIT-13). `0x8004DF18` disassembles as a routine taking its struct via `a0`→`s2` and operating per-field
   (consistent with a follow-law reading a passed camera struct, not enemy-homing on an absolute slot).
2. **From-boot movie reaches LEVEL01 *load*, not active gameplay.** `0x800A6500` (Flik pos) and `0x80095358`
   (camera struct) read all-zero and did not change across 120 frames; `accessLog` write-watches on both
   caught **0** writes. This is the documented from-boot-movie limitation (object/gameplay dispatchers fire
   only with objects on screen; reach live scenes via save states). Live re-derivation of the *semantics* was
   therefore inconclusive here, and chasing a live gameplay save was declined to respect the pristine-only
   constraint (modded saves excluded).
3. **`xrefsTo 0x8012C1D0` = 0.** The shared vertex buffer is addressed via a register-relative base, not an
   absolute `lui`+`lo` pair, so xref cannot enumerate its writers (consistent with the
   [[EXP_2026-07-09_modding_safety_map]] finding that xref misses register-computed addresses).

## Conclusion (authoritative names, evidence-anchored)
`re_symbols.sym` is authoritative and **agrees with independent prior runtime evidence** for every contested
identity, so the sym name is propagated across note/`src_re`/memory:
- `0x80059E44` = **spawn_drop** — prior runtime proof [[EXP_2026-07-07_golddrop_pickup_verifier]] (the drop it
  spawns is the gold-berry token). The "ContactRecord allocator" reading is its constructor sub-role.
- `0x8005BDBC` = **plant_spawn** (distinct from `0x8003E760 token_descriptor_reskin`).
- `0x8004DF18` = **camera_follow_update** — prior live motion test + GAP-0028 camera decode (documented in the
  `enemy-ai-state-machine` correction 2026-07-03); the "chaser @0x80095358" model is superseded.
- `0x8012C1D0` = **shared mesh vertex buffer (terrain + actors)** — chunk 34/35 shared-model-arena finding
  (`walls-are-chunk35`); the "terrain-only" twin is the narrower, older reading.
- `0x8005B134` = **respawn_transition_state_handler**; `0x80060724` = **RotAverage4** (PsyQ GTE signature);
  `0x8004D698` = **setpiece_spawn_manager**.

## Links
[[SYS_function_census]] · [[SYS_re_evidence_policy]] · [[DuckStation_API_Index]] · [[Consistency Audit]].
