---
kind: system
id: SYS_warp_and_level_transition_safety
name: Warp and Level Transition Safety
status: static_seen
confidence: confirmed
source_state: original_game
functions:
  - FUNC_8005222C
  - FUNC_8005B714
  - FUNC_80046B20
memory:
  - MEM_EVENT_SYSTEM_GLOBALS
tables:
  - TABLE_80077FA0
constants: []
evidence: []
src_paths:
  - src_re/level_exit_trigger.c
  - src_re/proximity_updater_8004abf4.c
---

# SYS_warp_and_level_transition_safety

## Purpose

Canonical safety rule for level transition and warp work.

## Confirmed behavior

- `current_scene_id` at `0x80082504` drives both scene/update dispatch and resource loading.
- During active gameplay, `scene_id` is hot state. Raw mid-gameplay mutation sends consumers down the wrong scene paths against the currently loaded level data and can crash.
- Native transitions go through transition-state, fade, shell/menu state, destination selection, resource loading, scene init, and player spawn.
- Poking shell substate or `scene_id` directly is not a clean in-game level-to-level warp.

## Safe rule

Only change scene destination through the shell-phase/native transition path, or use a cold-boot/pre-latch experiment that explicitly controls the scene table and resources.

## Superseded claim

Do not promote "mid-gameplay `scene_id`/substate poke is a clean warp lever" into Canon.
That historical claim is archived at `Archive/Wrong Hypotheses/WHYPE_midgame_scene_id_clean_lever.md`.

## Evidence

- `Experiment - In-game warp trigger`
- `Gameplay - Warp and Level Transition`
