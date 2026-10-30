---
kind: wrong_hypothesis
id: WHYPE_midgame_scene_id_clean_lever
status: resolved_wrong
confidence: confirmed
resolved_by:
  - ObsidianVault/_Revamp/CONFLICTS.md
  - ObsidianVault/Canon/Systems/SYS_warp_and_level_transition_safety.md
  - ObsidianVault/Experiments/Experiment - In-game warp trigger.md
---

# WHYPE_midgame_scene_id_clean_lever

## Wrong claim

Poking `scene_id` or shell substate during gameplay is a clean warp lever.

## Resolution

Wrong. `scene_id` is hot dispatch/resource state during active gameplay. Mutating it mid-level makes scene consumers run against mismatched loaded resources and can crash.

Native transition requires the transition-state/fade/shell/resource/scene-init chain.

## Canon destination

- `Canon/Systems/SYS_warp_and_level_transition_safety.md`
