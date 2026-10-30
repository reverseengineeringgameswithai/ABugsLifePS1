---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80010000.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80010000.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80010000_per-object_mesh_draw_-_payload_emitter.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80010000 — per-object mesh draw / payload emitter
type: function
address: 0x80010000
confidence: CONFIRMED
tags: [function, rendering, geometry, gte]
---
# FUNC_80010000 — per-object mesh draw / payload-vertex projector + emitter

> Draws one object's mesh: reads a vertex payload, projects each vertex through the GTE, and packs primitives into the GPU ordering table. The terminal emitter of the render chain.

| Field | Value |
|-------|-------|
| Address | 0x80010000 (text base) |
| Source file | `src_re_geometry/geometry_render_consumers.c` (G10/G11) |
| Confidence | CONFIRMED (payload format + triangle case); per-type operand layout / `attr` meaning UNKNOWN |

## Purpose
`lw count=[a0]; a0+=4` (vertex base). If count>0, the primitive command stream sits at `payload+4+count*0xc`. Main loop `0x800102d0`: `lh ctrl=[s0]`; `bltz`=end; `type=ctrl&0x1f` → `jr (0x8001036c+type*8)`. Type-0 (`0x8001046c`) = TRIANGLE: read 3 vertex byte-offsets, `lwc2` into GTE, RTPS/RTPT project, NCLIP backface-cull, screen/Z clip, pack polygon to the OT.

## Arguments / Returns
`a0`=payload ptr · `a1`=z/flag · `a2`=color<<3 · `a3`=`0x1f800384` (view vector). Returns void (emits packets). Key PCs: RTPS `0x800104a8`, RTPT `0x800104d8`, NCLIP `0x800104fc`, packet-store gate `0x800108b4`, per-primitive SXY site `0x80010718`, AVSZ4 `0x80010790`.

## Calls (callees)
- `fcn.80060284` / `0x800602e0` — GTE per-point transform leaf (mtc2 → GTE op → mfc2). NOT libgpu.

## Called by (callers)
- [[FUNC_8001EA6C]] (builder #1, via `j 0x80020698`→`jal`) and [[FUNC_800206E8]] (builder #2) — the survivor-list bridge.
- [[FUNC_80019934]] — bulk-ground sub-emitter calls this (ra `0x800108b8`) for the visible foreground floor.
- Shared emitter tail `0x800206a0` is the `ra` seen for Candidate A.

## Globals & structures touched
- Payload: [[MEM - fcn.80010000 mesh payload]] — `{u32 count; Vertex stride 0xc (s16 x,y,z; s16 pad=0; u32 attr); cmd stream}`.
- OT / GPU buffer `[0x8008240c]`. Type jump table `0x8001036c`.

## Evidence & confidence notes
G11 decoded the payload + triangle case by static disasm + byte trace. G13 lesson: watch the **aligned `lwc2` base**, not the inner s16 ([[Finding - Payload vertex edits are visible]]). G16: emit-in-view is necessary but not sufficient for "floor" ([[Finding - 0x356bc is a wall not floor]]). G26 re-audit confirmed `a0` is never rewritten on the main path (kills the `0x801bdc58` payload theory — [[Finding - 0x801bdc58 is compressed source]]).

## Tier-3 GTE-Native P3 Use (2026-07-06)

P3 does **not** suppress this renderer. The current build authors the DAT node-array floor payloads that feed
`FUNC_80010000`: `tools/build_g3_native.py --planes` now defaults to `native_terrain_export.flatten_floor`, setting
every native floor vertex to the authored file-frame surface instead of shifting each payload to its mean
(`--displace-visual` keeps the old path only for A/B checks).

Validated P3 build: `python3 tools/build_g3_native.py --planes --corridor --rise 0 --flatten-blocks --suppress-grass --suppress-horizon --out build/ABL_g3native`.
Offline geometry proof on `build/ABL_g3native_terrain.DAT`: 30 floor payloads / 2775 vertices, every payload
`Y[-497,-497]`, `max_abs_error_to_target_after=0`. Movie validation: `RENDER_C=0`, `FUNC_80010000=7303`, no plunge.

## Tier-3 GTE-Native P5 Use (2026-07-06)

P5 keeps this renderer as the visual path but changes the authored surface input from a flat/ramp scalar to a
Blender-exported heightfield mesh. `build_g3_native.py --surface-json` maps runtime heightfield `dy` to native visual
file-frame `dy/32`, then `flatten_floor` writes those absolute vertex Y values into the same 30 floor payloads.

Validated P5 fixture: `build/g3_native_heightfield.blend` -> `build/g3_native_p5_surface.json` (`33x65`,
`runtime_delta_y`, `dy=[-196,256]`) -> `build/ABL_g3native`. Movie validation: `RENDER_C=0`, `FUNC_80010000=7293`,
no plunge.

## Tier-3 GTE-Native P8-P10 Use (2026-07-06)

The Track-B authoring path now treats this renderer as the visual backend for a constrained Blender level scene:
heightfield terrain, `Spawn`/`Goal` metadata, offline path validation, and material styling. P10 added
`native_terrain_export.style_floor`, a size-preserving pass that sets payload vertex `attr` color and quad UVs.

Validated P8-P10 fixture: `build/g3_native_level_scene.blend` -> `build/g3_native_p8_surface.json` ->
`build/ABL_g3native`. The surface was styled with `color=0x88705c` and UVs `0xc03f,0xc000,0xff00,0xff3f`; offline
payload census showed all 30 floor payloads / 2775 vertices at that color. Movie validation: `RENDER_C=0`,
`FUNC_80010000=7299`, no plunge.

## Related
- Findings: [[Finding - fcn.80010000 payload format]] · [[Finding - Candidate A is DAT-backed visual terrain]] · [[Finding - Visible ground from DAT verts]]
- Functions: [[FUNC_8001EA6C]] · [[FUNC_800206E8]] · [[FUNC_80019934]] · [[FUNC_800172DC]]
- Experiments: [[Experiment - G14 payload vertex grass]] · [[Experiment - G16 emitted payload vertex wall]] · [[Experiment - G28 Candidate A floor Y]]
- Source docs: `src_re_geometry/geometry_g11_payload_format.md`, `geometry_render_consumers.c`
