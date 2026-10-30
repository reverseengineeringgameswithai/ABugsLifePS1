---
kind: function
id: FUNC_800172DC
aliases: [FUNC_800172DC, 0x800172DC, master mesh renderer, chunk-35 wall renderer]
address: 0x800172DC
name: master_mesh_renderer
status: confirmed
confidence: confirmed
source_state: original_game
system: [Tier_3_-_Native_Terrain_Path, SYS_render_collision_source_separation]
calls: []
reads: [0x80082424, 0x80082254, 0x8008249C, 0x80082394, 0x800A7DD8, 0x800A3390, 0x800910B0]
writes: []
uses_tables: [0x800A7DD8]
related_constants: [0x3C000000]
evidence:
  - EXP_2026-08-19_chunk35_master_mesh_evidence_index
  - docs/CHUNK35_MASTER_MESH_DECODE.md
src_paths: [tools/chunk35_master_mesh.c]
---

# FUNC_800172DC — master-mesh renderer (chunk 34/35)

## Purpose

GTE renderer for a chunk-34/35 **master mesh**. ⛔ **Corrected 2026-08-11:** this draws an
**ACTOR/CHARACTER** mesh, not LEVEL01's wall/terrain masses. Proven in-game — editing chunk-35
records changes exactly Flik's on-screen silhouette (`build/c35_R0_117_diff.png`), and the mesh
spans only X[−61,61] Y[−566,−1] Z[−122,91]. The wall attribution came from the runtime buffer
`0x8012C1D0`, a different structure. **The wall layer remains unidentified.**

Three callers: `0x8001DF2C`, `0x8001E9BC`, `0x80022454`.

## Argument contract (recovered from the prologue)

| load | meaning |
|---|---|
| `lw a1, 0x20(a0)` | **primitive stream** pointer — the record array this function walks |
| `lw v1, 0x0C(a0)` | **side-array** base: `u16 count` at `+0`, data at `+4`, stride 8 |
| `lw a1, 0x20(a0)` → `s6 = v1 + 4 + count*8` | side-array cursor, starts just past that array |

```
0x80017378  lhu  s0, 0(v1)      ; u16 count
0x8001737c  addi v1, v1, 4      ; data starts at +4
0x80017380  sll  s0, s0, 3      ; count * 8   -> stride EIGHT
0x80017384  add  s6, s0, v1     ; cursor = just past the array
```

`s0` is then **reloaded** from `[0x80082254]` and reused as the far-clip distance
(`mfc2 SZ; addi -750; slt ... s0`), so the two uses do not share a value — worth stating because
reading them as one is an easy and wrong inference.

## Primitive record — every field tied to an instruction

Dispatch is on the **GP0 command byte** in the record's high byte:

```
0x800173DC  lw   t0, 0(a1)
0x800173E4  and  t1, t0, 0x3C000000     ; at = lui 0x3c00
0x800173E8  bne  t1, at, 0x80017418     ; not a 4-point gouraud-textured poly -> other path
```

`0x3C & 0x3C == 0x3C` takes the quad path; `0x34 & 0x3C == 0x34` does not. So the renderer
discriminates exactly on the standard GP0 polygon bits, which is what makes the record length
derivable from the command.

**Quad record (`0x3C`) — 0x30 bytes**, advance proven by `addi a1, a1, 48` at `0x80017798` and
`0x80017828`:

| offset | instruction | meaning |
|---|---|---|
| `+0x00` | `lw t0, 0(a1)` | `RGB \| GP0 command` |
| `+0x04` | `lwc2 $0` | vertex 0 XY (VXY0) |
| `+0x08` | `lwc2 $1` | vertex 0 Z (VZ0) — low half only |
| `+0x0A` | `lh a3, 10(a1)` | s16 aux, read separately from the Z word |
| `+0x0C` | `lwc2 $2` | vertex 1 XY |
| `+0x10` | `lwc2 $3` | vertex 1 Z |
| `+0x12` | `lh t3, 18(a1)` | s16 aux → `sh t3, 0x18(s3)` into the output packet |
| `+0x14` | `lw t1, 20(a1)` → `mtc2 $0` | vertex 3 XY (second triangle of the quad) |
| `+0x18` | `lw t2, 24(a1)` → `mtc2 $1` | vertex 3 Z |
| `+0x1A` | `lh t4, 26(a1)` | s16 aux → `sh t4, 0x30(s3)` |
| `+0x1C` | `lwc2 $4` | vertex 2 XY |
| `+0x20` | `lwc2 $5` | vertex 2 Z |
| `+0x22` | `lh t5, 34(a1)` | s16 aux → `sh t5, 0x24(s3)` |
| `+0x24/+0x28/+0x2C` | `lw t1/t2/t3` | three colour words |
| `+0x2F` | `lb s1, 47(a1)` | **material index** (see below) |

The four vertices therefore sit at **`+0x04`, `+0x0C`, `+0x14`, `+0x1C`** — stride 8, each an
XY-packed word plus a Z word. That is exactly the set of offsets the 2026-06-24 live poke of the
runtime buffer `0x8012C1D0` found ("vertex Y = high16 of the words @ +0x04/+0x0c/+0x14/+0x1c").
Note this function reads the RESIDENT structure, so these offsets prove the runtime layout; the
on-disc grammar walk agrees field-for-field, but whether the loader copies verbatim is unproven.

**Triangle record (`0x34`) — 0x24 bytes**: same discrimination, material byte at `+0x23`
(`lb s1, 35(a1)` at `0x80017418`). `0x24` is the GP0 word count for a 3-point gouraud textured
polygon, so both record sizes fall out of the command byte.

## ⚡ The material selector — a per-primitive texpage/CLUT index

```
0x800173F0  lb   s1, 47(a1)        ; quad: last byte of the record   (tri: lb s1, 35(a1))
0x80017424  andi s1, s1, 0x001F    ; low 5 bits
0x80017428  sll  s1, s1, 1         ; u16 table index
0x8001742C  add  s2, s1, t3        ; t3 = 0x800A7DD8
0x80017434  lhu  s2, 0(s2)
0x80017438  lhu  s1, 0(s1 + t2)    ; second parallel table
```

**The record's last byte carries a 5-bit material index, resolved through a runtime table at
`0x800A7DD8` (plus a second parallel table).** This is the layer's texture-page/CLUT selector, and
it is *in the data* — unlike the `FUNC_80010000` DAT payloads, where the CLUT is render-time state
and unreachable from the payload (`geometry_g57`). An authored master mesh can therefore choose its
material; an authored DAT floor payload cannot.

## Side array

`s6` advances **8 bytes per primitive** (`addi s6, s6, 8` at `0x80017790`, `0x80017820`) in lockstep
with the `0x30` primitive advance, and is read as `lh +0`, `lhu +2`, `lhu +4`, `lhu +6`. Its purpose
is not established.

## Boundaries

This function consumes an already-resident structure; it is **not** the loader. `FUNC_8002958C` is
**not** the master-mesh converter — disassembled it is slot/modulo-100 arithmetic over a 128-entry
table at `0x800992A8`. `0x8012C1D0` is never materialised as a constant in `SCUS_942.88`, so the
buffer is reached through a pointer. Whoever fills it is still unidentified.

Related: [[Tier_3_-_Native_Terrain_Path]], [[SYS_render_collision_source_separation]],
`docs/CHUNK35_MASTER_MESH_DECODE.md`, `tools/chunk35_master_mesh.c`.
