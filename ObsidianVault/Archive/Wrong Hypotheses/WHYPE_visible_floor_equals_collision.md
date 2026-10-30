---
kind: wrong_hypothesis
id: WHYPE_visible_floor_equals_collision
status: resolved_wrong
confidence: confirmed
resolved_by:
  - ObsidianVault/_Revamp/CONFLICTS.md
  - ObsidianVault/Canon/Systems/SYS_render_collision_source_separation.md
  - ObsidianVault/Findings/Finding - Visual is not collision.md
---

# WHYPE_visible_floor_equals_collision

## Wrong claim

The visible floor is simply the chunk-35 terrain buffer, or visual terrain and collision are the same source.

## Resolution

Wrong. Visual and collision layers are separate.

- Confirmed visible floor path: DAT payloads through `FUNC_80010000`.
- Chunk-35/`FUNC_800172DC` is a shared mesh path with occluded terrain role in the confirmed tests.
- Collision uses sector/plane data, including LEVEL.RAW chunk 32, through the movement/collision path.

## Canon destination

- `Canon/Systems/SYS_render_collision_source_separation.md`
