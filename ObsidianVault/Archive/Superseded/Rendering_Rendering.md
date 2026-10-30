---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Rendering/Rendering.md
aliases:
  - "Rendering"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Rendering/Rendering.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Rendering.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Rendering
type: hub
tags: [hub, rendering, gpu, gte]
---

# Rendering — Map of Content

> How geometry and the sky reach the screen, and the levers for editing them.

## Render pipeline
[[FUNC_800224EC]] (scene/render driver) → [[FUNC_800140A0]] (GTE trail cull → [[MEM - Survivor lists|LIST_A/B]]) → [[FUNC_8001EA6C]] / [[FUNC_800206E8]] (primitive builders) → [[FUNC_80010000]] (per-object mesh emitter, RTPS/RTPT/NCLIP) → GPU/OT buffer. Terrain surface is drawn separately by [[FUNC_800172DC]] via [[FUNC_8001DFE4]]; bulk geometry uses the libgte leaf bank [[FUNC_80060724]].

## Confirmed findings
- [[Finding - Visible terrain renderer]] · [[Finding - Visible ground from DAT verts]] · [[Finding - Candidate A is DAT-backed visual terrain]]
- [[Finding - fcn.80010000 payload format]] · [[Finding - Payload vertex edits are visible]] · [[Finding - 0x356bc is a wall not floor]]
- [[Finding - Sky is a GP0 background fill]] · [[Finding - Sky color on-disk table]] · [[Finding - GPU primitive injection]] · [[Finding - Persistent night render hook]] ([[FUNC_8003E928]] haze, [[MEM - OT output buffer pointer 8008240C]] back-buffer)
- [[Finding - Trail flag gates terrain render]] · [[Finding - Localized terrain edit]]

## Structures
[[MEM - fcn.80010000 mesh payload]] · [[MEM - Terrain vertex buffer 8012C1D0]] · [[MEM - Sky DRAWENV color cache 800771BC]] · [[MEM - Survivor lists]] · [[MEM - Trail and pass3 tables]]

## Sky
The sky is a **GP0 0x02 fill**, not an image — recolor via the cache [[MEM - Sky DRAWENV color cache 800771BC]] (built by [[FUNC_800639CC]]); the starry-night effect *draws over* it ([[Finding - GPU primitive injection]]).

## GTE / VRAM tooling
GTE state via [[API - GTE state]] / [[API - execTrace]] (`gte.SXY0` capture); VRAM via [[API - gpu.readVramRect]] + [[API - visual diff]]; display list via [[API - gp0Trace]].

## Experiments
[[Experiment - G14 payload vertex grass]] · [[Experiment - G16 emitted payload vertex wall]] · [[Experiment - G28 Candidate A floor Y]] · [[Experiment - G30 localized terrain edit]] · [[Experiment - G30 sky recolor]] · [[Experiment - Starry night sky injection]]

## Playbooks
[[Playbook - Trace rendering ownership]] · [[Playbook - Find geometry sources]]

## Source docs
`src_re_geometry/geometry_render_consumers.c`, `geometry_g10_payload_render_chain.md`, `geometry_g30_terrain_render_source_plan.md`.
