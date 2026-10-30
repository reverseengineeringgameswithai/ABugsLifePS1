---
kind: system
id: SYS_chunk35_master_mesh
created: 2026-08-11
updated: 2026-08-11
status: confirmed
confidence: confirmed  # format confirmed; layer IDENTITY corrected 2026-08-11
source_state: original_game
aliases: [Chunk-35 master mesh, terrain master mesh, wall layer]
evidence:
  - EXP_2026-08-19_chunk35_master_mesh_evidence_index
  - docs/CHUNK35_MASTER_MESH_DECODE.md
  - tools/chunk35_master_mesh.c
---

# Chunk-35 master mesh (an ACTOR mesh — not the wall layer)

> ## ⛔ CORRECTION 2026-08-11 — THIS IS NOT THE WALL LAYER
>
> Confirmed in-game by **looking at** the changed pixels, not by counting them. Editing chunk-35
> records changes exactly **Flik's on-screen silhouette** — head, raised arm, torso, legs — with a
> blob displaced *above* him (the `dy −400` shift; −Y is up). The diff bbox grows with the character
> as more records are edited (12×5 → 32×216 → 42×259 → 42×284 px), always centred on him at
> x≈399, **never on terrain**. See `build/c35_R0_117_diff.png`.
>
> Corroborating measurements: the mesh spans only X[−61,61] Y[−566,−1] Z[−122,91] — tall, thin, and
> small, i.e. a standing character, not terrain; and 183 primitives is an ordinary PS1 character
> poly budget.
>
> **So chunk 35 holds an ACTOR/CHARACTER model and `FUNC_800172DC` is an actor-model renderer.**
> The older `walls-are-chunk35` headline is what misled me here — note that memory had already
> corrected itself to *"chunk 34/35 = shared MODEL ARENA, not wall-only"*, and I over-weighted the
> headline. The wall attribution came from poking the runtime buffer `0x8012C1D0`, which is a
> different structure from chunk 35's on-disc content.
>
> **Everything below about the FORMAT stands** — the grammar, the code ties, the authoring results.
> Only the claim about WHICH geometry it is was wrong. The remaining alternative I cannot exclude:
> the mesh is drawn coincident with Flik rather than being his model.


## Canon conclusion

`LEVEL*.RAW` chunk 35 is a **self-contained GPU primitive stream** drawn by
[[FUNC_800172DC_master_mesh_renderer]]. In-game editing shows it renders an **actor/character**
(the changed pixels trace Flik's silhouette), NOT the wall/terrain masses it was long believed to
hold. It is independent of the `FUNC_80010000` DAT floor and of chunk-32 collision.

⚠️ Consequence: **the wall layer is still unidentified**, so a Tier-3 replacement level still has an
un-authorable layer. Do not cite this note as having solved that.

The format is now decoded and **tied to the code that reads it**. A grammar walk consumes
**every byte** of LEVEL01's 13,556-byte chunk 35, and each field below is anchored to an
instruction, not to a pattern that happens to fit.

## Grammar (byte-exact over all of LEVEL01 chunk 35)

```
group := primitive-record+  0x00000000  u16 count (+2 pad)  entry[count]  u16 index[...]
prim  := word-aligned [ RGB | GP0-command ], length from the standard GP0 field rules:
           nverts   = (cmd & 0x08) ? 4 : 3
           textured = (cmd & 0x04)
           gouraud  = (cmd & 0x10)
           words    = (gouraud ? nverts : 1) + nverts + (textured ? nverts : 0)
entry := 8 bytes  (s16 @+0, u16 @+2, u16 @+4, u16 @+6)
```

LEVEL01 chunk 35: **12 groups, 183 primitives** — 141 × `0x3C` (4-point gouraud textured,
12 words = **0x30**) and 42 × `0x34` (3-point, 9 words = 0x24). 183 primitives sits against the
~199 quads counted live in the runtime buffer.

## What the code proves

| grammar claim | instruction |
|---|---|
| high byte is the GP0 command, and dispatch is on the standard polygon bits | `and t1, t0, 0x3C000000` / `bne t1, at` @ `0x800173E4` |
| quad record is **0x30** | `addi a1, a1, 48` @ `0x80017798`, `0x80017828`; material byte `lb 47(a1)` |
| triangle record is **0x24** | material byte `lb 35(a1)` @ `0x80017418` |
| four vertices at `+0x04/+0x0C/+0x14/+0x1C`, XY word + Z word | `lwc2 $0..$5` @ `0x80017444..0x80017458` + `mtc2` of `+0x14/+0x18` |
| side array: `u16 count` at `+0`, data at `+4`, **stride 8** | `lhu s0,0(v1)` / `addi v1,v1,4` / `sll s0,s0,3` @ `0x80017378` |
| side array advances one entry per primitive | `addi s6, s6, 8` @ `0x80017790`, `0x80017820` |

⚠️ **Careful about what this bridges.** `FUNC_800172DC` consumes the RESIDENT structure, so its
offsets prove the *runtime* record layout. The grammar walk separately fits the *on-disc* bytes, and
the two agree field-for-field — including the vertex offsets the 2026-06-24 live poke of
`0x8012C1D0` independently found. That means the loader either copies records verbatim or emits an
identical layout; **which of the two is not proven**, because the loader is still unidentified. The
older "on-disk format ≠ runtime buffer" note is therefore right about the *container* and wrong (or
at least unsupported) about the *record*.

## ⚡ Consequence for authoring: this layer CAN choose its material

The record's **last byte carries a 5-bit material index** (`lb +0x2F` quad / `+0x23` tri,
`andi 0x1F`), resolved through a runtime table at `0x800A7DD8`.

This is the sharpest contrast with the DAT floor path. A `FUNC_80010000` payload cannot select a
CLUT — it is render-time state (`geometry_g57`), so an authored floor's material is only
*texture cell × per-vertex colour*. A chunk-35 primitive selects its material **from the data**.
The wall CLUT that gives LEVEL01's cliffs their dark red-brown belongs to this layer, which is why
an authored DAT payload could never reach it.

## Two parse rules that each cost a failed walk

1. **A primitive must be word-aligned.** The index list is `u16`, so testing every halfword invents
   a phantom primitive — it did, at `+0x24E`, and derailed the walk two groups in.
2. **`0x00000000` is not always a group terminator.** At `+0x4E8` another `GP0(0x34)` record follows
   it, so it doubles as a run separator. Treat it as a terminator only when what follows is not
   itself a primitive.

## Open

- **12 groups vs the header's 22.** The byte at `+0x09` of chunk 35 is `0x16` = 22; the walk finds
  12. One of the two is not what it looks like. (Offset correction: chunk 35 carries this at
  `+0x09`, chunk 34 carries `0x28` = 40 at `+0x0A` — one byte earlier than the older note recorded.)
- **The side array's purpose** and the per-vertex `lh` aux halfwords at `+0x0A/+0x12/+0x1A/+0x22`
  (copied into the output packet at `s3+0x18/+0x24/+0x30`).
- **The loader.** `FUNC_8002958C` is **not** the converter (it is slot/modulo-100 arithmetic over a
  128-entry table at `0x800992A8`). `0x8012C1D0` is never materialised as a constant, so the buffer
  is reached via a pointer; whoever fills it is unidentified.
- **Chunk 34 is a different container** (marker `0101`; header holds absolute offsets
  `0x29998 / 0x2B828 / 0x2A368`, all inside its 182,342 bytes). This grammar does not parse it.
- **Why records 118–182 break the load** (see the authoring section below). Four hypotheses are
  already eliminated; the mechanism is not known.

## ✅ AUTHORING: the layer is editable on disc, and the frontier is bounded

`tools/edit_chunk35_record.py` edits vertices through the grammar, re-walks the result, and refuses
to emit unless the grammar still accounts for every byte. Discs cold-booted and gated with
`mod/smoke_test.py`; frames compared pixel-wise against an identity-recompress control, because the
smoke metrics are identical across every one of these discs — the gate cannot see the change.

| edit | gate | pixels changed vs control |
|---|---|---:|
| identity (recompress only) | PASS | **0** — bit-identical to pristine |
| record 0, `dy −400` | PASS | **47** |
| records 0–9, `dy −400` | PASS | **756** |
| records 0–57, `dy −400` | PASS | **2,797** |
| records 58–117, `dy −400` | PASS | — |
| records 0–117, `dy −400` | PASS | — |
| records 118–182, `dy ±400` | **BOOT FAIL** | — |
| all 183, `dy −10` or `−200` | **BOOT FAIL** | — |

**Records 0–117 of 183 are authorable**, and the effect scales with how many are edited. The
identity control being bit-identical to pristine is what makes the 47-pixel result mean the edit and
nothing else.

**Records 118–182 break the load in either direction.** Four hypotheses are dead: not magnitude
(`dy −10` over all fails, `dy −400` over 118 passes), not the `0x34` layout (quads-only fails), not
run 9 being a 60-record outlier (run 9 alone passes), not Y extent (shifting +400 back into the
original `Y[−566,−1]` also fails). Leading candidate: those vertices are load-bearing beyond
geometry — the loader welds vertices by position and the runs' own vertex/index blocks are not
edited in step. Failing discs hang on a **clean** loading screen, so the load stalls rather than
corrupting memory.

Related: [[FUNC_800172DC_master_mesh_renderer]], [[Tier_3_-_Native_Terrain_Path]],
[[SYS_collision_and_floor_planes]].
