---
kind: function
id: FUNC_80010000
aliases: [FUNC_80010000, 0x80010000]
address: 0x80010000
name: per-object_mesh_draw_-_payload_emitter
status: static_seen
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: []
src_paths: []
patch_policy: unknown
---

# FUNC_80010000 - per-object mesh draw - payload emitter

## Purpose

Draws one object's mesh: reads a vertex payload, projects each vertex through the GTE, and packs primitives into the GPU ordering table. The terminal emitter of the render chain. P3 does **not** suppress this renderer. The current build authors the DAT node-array floor payloads that feed `FUNC_80010000`: `tools/build_g3_native.py --planes` now defaults to `native_terrain_export.flatten_floor`, setting every native floor vertex to the authored file-frame surface instead of shifting each payload to its mean (`--displace-visual` keeps the old path only for A/B checks). Validated P3 build: `python3 tools/build_g3_native.py --planes --corridor --rise 0 --flatten-blocks --suppress-grass --suppress-horizon --out build/ABL_g3native`. Offline geometry proof on `build/ABL_g3native_terrain.DAT`: 30 floor payloads / 2775 vertices, every payload `Y[-497,-497]`, `max_abs_error_to_target_after=0`. Movi...

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80010000.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80010000`
- Name: `per-object_mesh_draw_-_payload_emitter`
- Original note: `ObsidianVault/Functions/FUNC_80010000.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80010000.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80010000.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80010000.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

## ⚡⚡ Packet emission and the CLUT rule (2026-08-11, disassembled + live-verified)

The emitter builds a PSY-Q **`POLY_GT4`** per quad — `addi s3, s3, 52` at `0x80010678` fixes the
stride at **0x34 / 13 words** (tag + 12). Field map recovered from the stores:

| packet | store | source |
|---|---|---|
| `+0x00` tag | `sw t5, 0(s3)` @`0x80010664` | OT link + length |
| `+0x04` rgb0 \| code | — | |
| `+0x08` xy0 | `sw t5, 8(s3)` @`0x800105f8` | `mfc2 $12` (SXY0) |
| **`+0x0C` uv0 \| CLUT** | **`sw t6, 12(s3)` @`0x80010668`** | see below |
| `+0x10` rgb1 | `sw at, 16(s3)` @`0x800105ec` | payload vertex `attr` |
| `+0x14` xy1 | `sw t6, 20(s3)` @`0x800105fc` | `mfc2 $13` (SXY1) |
| **`+0x18` uv1 \| TPAGE** | `sw t7, 24(s3)` @`0x8001066c` | |
| `+0x1C` rgb2 | `sw v1, 28(s3)` @`0x800105f0` | `lw v1, 8(t0)` — vertex `attr` |
| `+0x20` xy2 | `sw t7, 32(s3)` @`0x80010600` | `mfc2 $14` (SXY2) |
| `+0x24` uv2 | `sh v0, 36(s3)` @`0x80010670` | payload `uv0` |
| `+0x28` rgb3 | `sw v0, 40(s3)` @`0x800105f4` | vertex `attr` |
| `+0x2C` xy3 | `sw t8, 44(s3)` @`0x80010604` | |
| `+0x30` uv3 | `sh v1, 48(s3)` @`0x80010674` | payload `uv1` |

`lw v1, 8(t0)` → `sw v1, 28(s3)` confirms the payload vertex's `attr` word (stride 0x0C, `+0x08`) is
the packet's per-vertex RGB.

### The CLUT is DERIVED FROM THE UVs — it is not render-time state

```
0x8001061c  lhu  v0, 14(s0)        ; s0 = prim record; +0x0E is its uv3 halfword
0x80010628  srl  v1, v0, 6
0x8001062c  andi v1, v1, 0x0003    ; (U >> 6)
0x80010630  srl  at, v0, 12
0x80010634  andi at, at, 0x000C    ; (V >> 6) * 4
0x80010638  add  at, at, v1
0x8001063c  sll  at, at, 16        ; the CLUT sits in the HIGH half of +0x0C
0x80010640  add  t6, t6, at
0x80010668  sw   t6, 12(s3)
```

**`clut = base + (U >> 6) + 4 * (V >> 6)`** — a pure function of which 64×64 atlas cell the
primitive's UVs land in. Verified against all 2,923 pristine primitives: cell `U[0,63] V[192,255]`
→ delta 12 on 1,267/1,267 prims; `U[64,127] V[192,255]` → 13 on 450/450; `U[128,191] V[192,255]`
→ 14 on 171/171. Zero exceptions.

Live, that is exactly the pair recorded as `0x3FFC ground / 0x3FFD wall`: delta 12 → CLUT
`(960,255)` = 0x3FFC, delta 13 → `(976,255)` = 0x3FFD.

⛔ **This falsifies `geometry_g57`'s "the CLUT is not in the DAT command stream — it comes from
render-time".** It is computed from the UV halfwords *in* the stream. Consequence for authoring:
**picking the wall texture cell automatically picks the wall CLUT.** There is no separate material
field to set, and none is needed.
