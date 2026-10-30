---
kind: system
id: SYS_training_ending_trigger_field
name: Training ending trigger field
status: live_confirmed
confidence: confirmed
source_state: original_game
evidence:
  - EXP_2026-08-02_training_ending_trigger_field
related:
  - Level_Goal_and_Exit_Trigger_Matrix
  - Gameplay_-_Warp_and_Level_Transition
---

# SYS_training_ending_trigger_field

## Confirmed Training contract

The fixture named `level01_ending_for_exit` is actually the **Training** scene:
runtime scene ID `17`. Its ending is a collision-sector region trigger. At the
fixture anchor Flik is in sector `16` with region code `0`; the endpoint is
sector `24`, region code `3`, with runtime origin
`(480, -24096, 268736)` and collision pointer `0x800D4988`.

The engine-level query remains the shared sector path:

- current collision sector: `[0x80090560]`;
- sector table: `0x800A7E48`, stride `0x30`;
- region code: sector record `+0x2E`;
- player gate: `[Flik+0x82] == 1`;
- query: `FUNC_80038F38(0, &Flik[+0x82])`, consumed by the scene handler.

For Training specifically, entering sector `24` through the natural endpoint
route causes the level-ending fade. Do **not** generalize code `3` or sector
geometry across scenes without a separate natural-route proof.

## Exact walkable footprint

The accepted visual footprint is the complete two-triangle collision slope for
sector `24`, not the first triangle alone. Sector-local coordinates are converted
with `world = sector_origin + local * 32`:

| Vertex | Sector-local XYZ | Native world XYZ |
|---|---:|---:|
| A | `(1, -80, 258)` | `(512, -26656, 276992)` |
| B | `(1, 211, 1060)` | `(512, -17344, 302656)` |
| C | `(1159, -80, 258)` | `(37568, -26656, 276992)` |
| D | `(1159, 211, 1060)` | `(37568, -17344, 302656)` |

The union of the two native triangles is the walkable ending surface. The
diagnostic renderer emits it as one flat quad. Its displayed Y coordinates are
`-128` world units above the native values (`-26784` and `-17472`) solely to
avoid z-fighting; that lift is not part of the trigger.

The diagnostic color command is `0x2890EE90`: opaque flat quad, RGB
`(144, 238, 144)`. The captured hardware-rendered image resolves the marker as
approximately `(148, 239, 148)`.

## Scope boundary

This page canonizes **Training only**. The later attempt to reuse the method for
Anthill, Tunnels, Cliffside, and Riverside Canyon was visually off and is not
accepted evidence for those levels. Future work must identify each winning
sector on its natural route and recover that sector's complete collision surface
before rendering it.

See [[EXP_2026-08-02_training_ending_trigger_field]] for fixture hashes,
diagnostic implementation details, and cold-boot evidence.
