---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8001EA6C.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8001EA6C.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8001EA6C_survivor-list_primitive_builder_-1.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8001EA6C — survivor-list primitive builder #1
type: function
address: 0x8001EA6C
confidence: CONFIRMED
tags: [function, rendering, geometry, gte]
---
# FUNC_8001EA6C — survivor-list primitive builder #1

> Consumes the render survivor list (LIST_A), bridges each survivor to its source record + payload pointer, sets up a per-object transform, and tail-calls the mesh emitter. The bridge from culled rows to drawn geometry. In G30 this path renders the wooden fence.

| Field | Value |
|-------|-------|
| Address | 0x8001EA6C (span `0x8001ea6c..0x800206e0`) |
| Source file | `src_re_geometry/geometry_render_consumers.c` (G10) |
| Confidence | CONFIRMED (bridge + dispatch + case `0x8001ec44`) |

## Purpose
Walks LIST_A (`0x80096ea8`); per row clears tag bit; gates on `lhu[row+0x0e]&0x10==a3`; **bridge**: `s0=[row+0x10]`=output record, `s2=[s0+0x18]`=source record; reads source vec[3] minus camera `0x1f800374` → GTE transform; dispatches on `(row+0x0e & 0x9f6f)<0x6d` via jump table `0x8001a970`; ~29 stores pack a primitive into the GPU/OT buffer `[0x8008240c]`.

## Arguments / Returns
`a0`=LIST_A · `a1`=count · `a2`=`[0x8008240c]` · `a3`=`0x10`. Case `0x8001ec44` (CONFIRMED): bit3/scaled-object setup reads vec/angle/scale, matrix-LUT idx `[s2+0x19]&0x1f`→`0x80089528`, scale path, then `a0=[s2+0x1c]` PAYLOAD POINTER, `j 0x80020698`→`jal` [[FUNC_80010000]].

## Calls (callees)
- `0x8001474c` — libgte transform-one-vector leaf.
- `0x80060484` / `0x800605c4` — libgte matrix-load leaves.
- [[FUNC_80010000]] — mesh emitter (tail).

## Called by (callers)
- [[FUNC_800224EC]] (render driver).

## Globals & structures touched
- LIST_A `0x80096ea8`; source/bit3 records (ptr `+0x1c`) → [[MEM - fcn.80010000 mesh payload]]; OT buffer `[0x8008240c]`.

## Evidence & confidence notes
G10 confirmed the bridge + dispatch (`0x8001eb34`→`0x8001ec44`) by static + runtime READ `0x80167b80`. LIST_B consumer is the analog [[FUNC_800206E8]].

## Related
- Functions: [[FUNC_80010000]] · [[FUNC_800206E8]] · [[FUNC_800224EC]] · [[FUNC_800140A0]]
- Findings: [[Finding - fcn.80010000 payload format]] · [[Finding - Two parser source-record formats]]
- Source docs: `src_re_geometry/geometry_g10_payload_render_chain.md`, `geometry_render_consumers.c`
