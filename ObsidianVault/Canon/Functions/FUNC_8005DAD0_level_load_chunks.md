---
kind: function
id: FUNC_8005DAD0
aliases: [FUNC_8005DAD0, 0x8005dad0, level_load_chunks]
address: 0x8005dad0
name: level_load_chunks
status: runtime_confirmed
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: [EXP_2026-08-03_phase4_e05_actor_model_binding]
src_paths: [symbols/re_symbols.sym, analysis/phase4_e05_model_binding_static.json, asm/hand_written/8005dad0_level_load_chunks.s]
patch_policy: safe_to_read
---

# FUNC_8005DAD0 - level load: actor-pool walk and model dispatch

## Purpose

The per-level load driver that turns the actor pool into loaded character
models. It is the owner of the **id -> model binding**, which is CODE, not a
data table.

## Behavior (decoded + live-confirmed)

1. **Skeleton bank clear.** The prologue memsets `0x80089F58` for **25,200
   bytes = 300 x 84-byte bone records** (the bank whose FLICK window is
   [[MEM_8008A1F8_Skeleton_bone_transform_8008A1F8]]).
2. **Flik variant pre-dispatch** (`0x8005DB64..0x8005DC74`): the scene word
   `[0x80082504]` selects the player model path, loaded with `a3 = 0` (slot 0):
   scenes {2,3} -> `chars3\flickd`; {4,5} -> `chars4\flickp`;
   {6,10,11,14} -> `chars3\flickp`; otherwise `chars\flick`.
3. **Pool walk.** Iterates the 64 slots of the actor pool
   [[MEM_8009FD80_enemy_actor_pool]] (stride 0x84), reads each record's id at
   `+0x00`, and for ids **1..41** dispatches through the jr table at
   **0x8001BBDC** (index = id - 1; site 0x8005DCA0 in the committed phase-3
   jr-table decode). Each case body hardcodes `a0 = model path string` and
   `a3 = model id == actor id`, then tail-calls
   [[FUNC_8005D654_level_chunk_loader]].
4. **Plant dispatch.** A second jr table at **0x8001BC84** (14 entries, list
   built by 0x80052090, site 0x8005E2AC) loads `plants\plantNN` with
   `a3 = 103 + N` -- which is why the Canon plant model table
   `0x800A649C + 4N` IS slots 104..117 of the shared registry.

The complete 41-entry id -> path table (EXE-decoded, zero inconsistencies) and
its 16/16-level live confirmation are in [[SYS_actor_model_loading]].

## Note on the address

`0x8005DE60` ([[FUNC_8005DE60_load_character_models]]) is a **label inside this
function** -- the first character-model case body, not a separate routine.

## Related

[[SYS_actor_model_loading]] · [[FUNC_8005D654_level_chunk_loader]] ·
[[FUNC_8005D924_level_chunk_file_load]] · [[MEM_8009FD80_enemy_actor_pool]]