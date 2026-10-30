---
kind: system
id: SYS_render_collision_source_separation
name: Render and Collision Source Separation
status: static_seen
confidence: confirmed
source_state: original_game
functions:
  - FUNC_80010000
  - FUNC_800172DC
  - FUNC_8003633C
  - FUNC_800345CC
memory:
  - MEM_8012C1D0
  - MEM_800A7E48
tables: []
constants: []
evidence: []
src_paths:
  - src_re/collision_source_converter_80030f60.c
---

# SYS_render_collision_source_separation

## Purpose

Canonical resolution for the visual-floor versus collision-floor conflict.

## Confirmed behavior

- Visual terrain/floor and collision are separate layers.
- DAT payloads rendered by `FUNC_80010000` are the visible walkable floor source in the confirmed LEVEL01 path.
- LEVEL.RAW chunk 35 feeds the shared mesh buffer used by `FUNC_800172DC`; its terrain role is occluded in the confirmed visible-floor tests.
- Collision uses the collision sector table and plane records, including LEVEL.RAW chunk 32 data, through the movement/collision path.

## Superseded claim

Do not promote "visible floor equals chunk-35 terrain buffer" or "visual terrain equals collision" into Canon.
That historical claim is archived at `Archive/Wrong Hypotheses/WHYPE_visible_floor_equals_collision.md`.

## Evidence

- `Finding - Visual is not collision`
- G28/G29/G30 geometry experiments
- `src_re/collision_source_converter_80030f60.c`
