---
kind: experiment
id: EXP_2026-07-09_understanding_u3
aliases: [EXP_2026-07-09_understanding_u3, "understanding u3"]
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census, SYS_re_evidence_policy, SYS_overlays_and_runtime_loading]
artifacts: [tools/trace_name_candidates.py, analysis/traces/u3_evidence.json, analysis/naming/u3_batch01.json, analysis/vm_programs.json]
---

# EXP_2026-07-09_understanding_u3 — runtime execTrace understanding push (pristine saves, no new recordings)

## Question
Static naming was exhausted at u2 (unknown 375, no more static signal). Can the **158 pristine save states**
(MSM content-gated; modded saves excluded) + the u1 execTrace loop recover more *understanding* — real
callers, live args, opcode semantics — with **no new movie recordings**?

## Method (throwaway instance 23460; operator port 2346 untouched; watches re-armed after every loadState)
`tools/trace_name_candidates.py`: for each `dynamic:true` census candidate (grouped by its `levels`), load a
pristine per-level `.sav`, arm `execTrace.addWatch{pc, capture:[a0..a3, ra]}` on ≤14 candidate PCs, advance
~900 frames, aggregate per-fn evidence — callers (`ra` resolved to the containing named fn), args (classified
against named globals via `re_symbols` + `memory_map`), and hit counts. 263 candidates traced; **82 fired**.

## Results
- **u3-1 — 31 names, resident unknown 375 → 344.** Definitive: `0x80065FBC/FCC` =
  `EnterCriticalSection`/`ExitCriticalSection` (`li a0,1/2; syscall` — the 23-caller mystery pair, tier
  `proven`). All **17 mover-VM opcode handlers** named from the opcode table `0x8001B2F4` (`mover_vm_op<N>_
  <sem>`, proven). Runtime-pinned game fns: `enemy_strike_contact_effect` (caller `vm_motion_apply_chase`,
  calls `play_sound`+`spawn_drop`), `actor_mesh_render_pass` (caller `scene_render_driver`),
  `collision_probe_{candidate,player}_pass`, `checkpoint_player_state_read`, `pickup_icon_vram_upload`,
  `global_mode_flags_read` (`0x80082488`), `exec_queue_kick` (`_exeque`), `scene_geometry_normal_pass`, etc.
- **u3-2 — VM ISA 25/26 CONFIRMED.** Live handler traces promoted 3 of the 4 LIKELY opcodes: **op5**
  `path_next_waypoint` (mosquito, `a1` walks the u16 waypoint cursor @`0x80077BB4`), **op14** `anim_clip_load`
  (clip/set pairs, bee/worm), **op24** `call_play_sound` (worm STRIKE, operand `0x18` = sound id). **op11**
  `seek_path_endpoint` never fired across 6 enemy saves → honestly stays LIKELY.
- **u3-3 — 2 overlay Residual-B fns.** `LEVEL02_LEVEL1 0x800B48F4` = `color_channel_lerp` (40 live hits/frame,
  channel-mask args — settles that it is CODE not data); `LEVEL06_LEVEL 0x800B3BBC` =
  `transition_handler_arg_entry` (2-insn arg-preload entry called live from the resident scene-verb
  dispatcher). The 3 others need a menu-context save (none pristine) → join the movie-blocked set.

## Evidence policy
Runtime-observed identities (syscall bytes, opcode-table membership, caller+arg context) → tier `proven`;
caller-context-only → `inferred`; fns that never fired stay `unknown` (never guessed).

## Links
[[SYS_function_census]] · [[SYS_re_evidence_policy]] · [[FUNC_8004C13C_FUNC_8004C13C]] · [[SYS_enemy_ai]] ·
[[Consistency Audit]] · [[DuckStation_API_Index]].
