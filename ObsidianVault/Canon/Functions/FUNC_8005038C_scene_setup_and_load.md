---
kind: function
id: FUNC_8005038C
aliases:
- FUNC_8005038C
- '0x8005038c'
- scene_setup_and_load
address: '0x8005038c'
name: scene_setup_and_load
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- display_buffers_init
- resource_id_dat_load_dispatcher
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/8005038c_scene_setup_and_load.c
patch_policy: safe_to_read
---

# FUNC_8005038C - scene_setup_and_load

## Purpose
Wraps display-buffer init + DAT resource load for entering a scene

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Saves+zeroes 0x80082504; gated a1!=-1 sets 0x800823ac=a1+1084 (live disassembly correction, 2026-08-02 — the address is `0x800823ac`, not the `0x800821ac` this page previously stated; confirmed via `lui at,0x8008` + `sw v0,0x23ac(at)` at `0x800503c0`), calls display_buffers_init(0x80039478) + resource_id_dat_load_dispatcher(0x8003cf2c) + 0x800b96e4(a0)
- callers main_shell_state_machine, scene_flow_dispatcher, sub_800502c4

## Live confirmation — Hopper (D20) defeat transition, 2026-08-02

Live-traced (`analysis/phase4_d20_hopper.json`'s `FINALE_TRIGGER_TRACED_2026-08-02`) as
the exact function firing the scene transition out of Hopper's boss fight: an `accessLog`
write-watch on `0x80082504` (`scene_id`) caught the zeroing write at `0x800503ac` (frame
36166 of `movies/Phase4/Interpreter/D20.movie.json`) right as the bird-nest defeat
cinematic ends. Confirms this function is genuinely generic/whole-game — not
boss-specific — since a Hopper defeat routes through the exact same dispatcher already
documented for ordinary scene transitions. Which of the 3 documented callers fired this
specific invocation was not confirmed (would need a breakpoint armed before frame 36166).

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]] · [[SYS_enemy_ai]] (D20 row)
