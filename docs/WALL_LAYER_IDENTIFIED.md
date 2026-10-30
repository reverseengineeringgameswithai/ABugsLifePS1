# The wall layer is `FUNC_80010000` — there is no separate un-authorable layer

**Date:** 2026-08-11 · Tool: `tools/probe_wall_layer.py` · Evidence:
`build/wall_layer_probe.json`, `build/wall_layer_causality.json`, `build/wall_layer_writer.json`,
`build/wall_layer_probe.png`

## Why this was asked

Chunk 35 was believed to be the wall/terrain layer, and the "one layer a Tier-3 replacement level
cannot author". Editing it on disc falsified that — the changed pixels trace Flik's silhouette, not
terrain (`docs/CHUNK35_MASTER_MESH_DECODE.md`). That left the wall layer unidentified. Rather than
read more notes, this asks the screen.

## Method

Cold boot the **pristine** disc in an isolated DuckStation, replay boot→LEVEL01, turn the camera
onto the cliff (`Down` 2f, then `L1` 40f, settle), then sweep `gpu.pickObject` over a grid of native
CRTC pixels (512×224) and cluster hits by GP0 command, texture page, CLUT and `source.ramAddress`.
Non-mutating; CPU hooks armed only *after* the movie stops (arm-late), so the CachedInterpreter
recording cannot desync.

## Result 1 — cliff and floor are the SAME draw class, split by CLUT

| screen region | command | texture page | CLUT |
|---|---|---|---|
| **cliff face** (dark reddish-brown) | `GP0(3c)` quad | (0,0) | **(976,255)** |
| **pebbled floor** | `GP0(3c)` quad | (0,0) | **(960,255)** / (864,255) |

CLUT word = `((y & 0x1ff) << 6) | ((x >> 4) & 0x3f)`:

- `(976,255)` → `(255<<6)|61` = **0x3FFD** — the *wall* CLUT
- `(960,255)` → `(255<<6)|60` = **0x3FFC** — the *ground* CLUT

That is exactly the `CLUT 0x3FFC ground / 0x3FFD wall` pair Track A recorded, now confirmed live on
the pristine game. Same command, same texture page — **the cliff and the floor differ only by
palette.**

## Result 2 — the wall packets are written by `FUNC_80010000`

`pickObject`'s `source.ramAddress` is the assembled GP0 **packet** (all hits land in
`0x801Cxxxx–0x801Dxxxx`, the packet arena), not the source geometry. Two steps to get past it:

**`gpu.traceCausality` names only the flush.** All 56 wall-CLUT pixels report submitting PC
`0x80064658` with stack `0x80065648 ← 0x80067f20 ← 0x80065b4c ← 0x800390f0 ← 0x800186ec ←
0x80039a70`. That is the DrawOTag DMA kick and the frame-present path — exactly the documented
limitation ("DMA commands record the instruction/call stack latched when channel 2 was kicked").
Useless for identifying the builder, and recorded so nobody repeats it.

**A write-watch on the packet names the builder.** `accessLog.addWatch` on the wall packet
`0x801e8cec`, 4 frames:

```
writer PC 0x800105f8, 0x80010604, 0x80010608, 0x80010674, 0x80010678, 0x80010574
```

Every one is inside **`FUNC_80010000`** — the native GTE terrain emitter that draws the LEVEL.DAT
floor node payloads.

## What this means

**There is no separate, un-authorable wall layer.** LEVEL01's cliffs are drawn by the same emitter,
from the same LEVEL.DAT payloads, that the Tier-3 pipeline already authors and already replaces.
The gap I reported as open after the chunk-35 falsification is closed — in the good direction.

It also reopens the authored-cliff material residual from earlier today — and the next section
settles it. (My first guess here, that the authored cliff wore the **ground** CLUT, is wrong; it is
corrected below rather than deleted.)

## ✅ RESOLVED — the CLUT is derived from the UVs

`FUNC_80010000` builds a PSY-Q `POLY_GT4` (stride 0x34, `addi s3, s3, 52` @`0x80010678`) and forms
the CLUT at `0x80010628`–`0x80010640` from the primitive's **uv3 halfword** (`lhu v0, 14(s0)`):

```
clut = base + (U >> 6) + 4 * (V >> 6)
```

A pure function of which 64×64 atlas cell the UVs land in. Verified over all 2,923 pristine
primitives with **zero exceptions**:

| texture cell | CLUT delta | prims |
|---|---:|---|
| `U[0,63] V[192,255]` (dirt/ground) | **12** → 0x3FFC | 1,267 / 1,267 |
| `U[64,127] V[192,255]` (rock/wall) | **13** → 0x3FFD | 450 / 450 |
| `U[128,191] V[192,255]` | 14 | 171 / 171 |

⛔ **This falsifies `geometry_g57`'s "the CLUT is not in the DAT command stream — it comes from
render-time".** It is computed from UV bits that are in the stream.

### Which also corrects what I said an hour earlier

I claimed the authored cliff "wore the ground palette". **Wrong** — measured on
`build/ABL_ARENA_CLIFF_LOW.cue`: 131 picks on `clut(976,255)` = **0x3FFD, the wall palette**, against
154 on 0x3FFC for the floor. All four `WALL_UV` rotations yield delta 13 by construction, so
`harvest_wall_style` was already selecting cliff material correctly.

**So there is nothing to fix in the material path.** Any remaining tone gap against
`PRISTINE_CLIFF_REFERENCE.png` is per-vertex colour and lighting, not palette — the authored floor
uses `NEUTRAL 0x808080` (luminance 128) where pristine floors average 116, so the authored world is
uniformly brighter than the game's.

## Historical: the open question as first posed

**What selects the CLUT word inside `FUNC_80010000`?** The packet's CLUT|UV word is written from
that same instruction window, but the selector is not yet identified.

⚠️ I first read the table lookup at `0x80010590`–`0x8001059c` (`sll t9,2` → bounds check → `lhu`
from `s1` → add base) as a material table. **That is wrong** — `0x80010568 mfc2 t9, $7` loads GTE
**OTZ**, so that path is the ordering-table depth bucket, and `lui t4, 0x0c00` / `lw t5, 0(t9)` /
`add t5, t5, t4` is the standard OT link plus the tag's `0x0C` length field — 12 words FOLLOWING the
tag, i.e. the 13-word / 0x34 `POLY_GT4` confirmed independently by `addi s3, s3, 52`. Retracted in
place.

My first candidate was the batch `ctrl` word's unexplained `0x100`/`0x200` bits. **Not the answer** —
the CLUT comes from the UVs (above). Bits 8–9 of `ctrl` remain unexplained, but they are not the
material selector.

## Reproduce

```bash
python3 tools/probe_wall_layer.py                       # sweep + cluster
python3 tools/probe_wall_layer.py --causality --step 12 # (names the DMA kick only)
python3 tools/probe_wall_layer.py --writer   --step 12  # names the builder
```
