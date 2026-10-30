---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Character ALL model format.md
aliases:
  - "Finding - Character ALL model format"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Character ALL model format.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Character_ALL_model_format.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Character ALL model format
type: finding
status: confirmed
confidence: CONFIRMED
tags: [finding, models, all, anm, rendering, b7]
updated: 2026-06-18
---

# Finding — `.ALL` character model format (structural decode)

> `CHARS/NAME.ALL` is a **position-independent model bundle**: a header whose **word0 is a section offset** to a **primitive list** of `[colour + GP0 command]` + s16 vertex triples, rendered by the general mesh renderer `fcn.800172dc`. Decoded live from `FLICK.ALL` (no operator) — moves [[Blocker - Character and plant model formats are unreversed|B7]] from 0% to a structural foothold.

## Evidence (live, `SCUS-94288_operator_backup.sav`)
- **`FLICK.ALL` (13548 B) is resident at `0x8012c1cc`** — header byte-exact, **95.5% verbatim** (12936/13548) vs the disc file, **0 pointer relocations** (`ram == file` everywhere except posed verts ⇒ no fix-up table; references are file-relative offsets, position-independent).
- The non-verbatim bytes are a contiguous region from file **`0x2698`** onward = **runtime-posed vertices** (the `.ANM` animation modifies the rest pose in place). `[0:0x2698]` is static.
- **Header:** `word0` = an in-range **section offset** — `FLICK 0x1600`, `BADBUG 0x7a2`, `FLY 0xafe`. Points at the renderable primitive list.
- **Primitive list (`@word0`):** records of `[3-byte grey RGB colour][1 command byte]` then **s16 vertex-coordinate triples** (model-space ±100). Example bytes `56 56 56 3c | d9 ff ae ff fe ff …` = colour `(0x56,0x56,0x56)` + command **`0x3c`** (GP0 gouraud-quad — the same primitive the renderer emits) + verts `(−39,−82,−2)…`.
- **Renderer = `fcn.800172dc`** (`0x8001745c`/`78`/`bc`/`c4`/`c8`) reads the `0x1600` section every frame (mixed halfword/word strides = structured parse) to draw Flik.

## Interpretation
- `.ALL` = a **pre-built GPU-primitive model** (colour + command + s16 verts), not a TMD and not PROPACK-compressed (loads verbatim). The LEVEL.RAW decoder is **not** needed for `.ALL`.
- `.ANM` drives the posed-vertex region `[0x2698:]` (skinning/vertex animation) — next target.

## ⚠️ Cross-finding (flag, do not override)
`0x8012c…` is the **same buffer** [[MEM - Terrain vertex buffer 8012C1D0]] / G30 attributed to **terrain**, and **`fcn.800172dc` renders both** the character model (here) and terrain (G30). ⇒ `fcn.800172dc` is a **general mesh renderer** over a **shared vertex buffer**, not terrain-specific. Reconcile with [[Finding - Visible terrain renderer]] — the operator-verified terrain deform stands; what needs revisiting is whether "terrain buffer" is better named "active mesh vertex buffer." See [[Open Questions]].

## `.ANM` animation format (decoded live, walk animation)
- **`FLICK.ANM` (~0x2c000 B) resident at `0x800ff984`**; unlike `.ALL` it **IS relocated** — the header is a **pointer table** whose entries (`0x29998, 0x2b828, 0x2a368, 0x2adc8, …`) are fixed up at load to absolute addrs (`base + offset`, e.g. `0x800ff984+0x29998 = 0x8012931c` ✓). Each entry → one **animation sub-block** (idle/walk/jump/…).
- **Active animation = the sub-block** the player is in; walking, Flik plays the block at file `0x29998`.
- **Sub-block header** (`@0x29998`): `+2` = **frame count** (low 15 bits; `andi 0x7fff`, high bit = loop/flag → 17 frames), `+4/+6/+8` = channel/bone counts (`24/72/24`), then a run of **default channel values** (`9× 0xfffd = −3`), then a **frame-time table at stride 6** (`6,12,18,24,…`).
- **Keyframes = bitmask-compressed channel updates.** The animator (`0x8005f028`+) does `lbu` a mask byte → `srav v0,v0,v1; andi v0,1` to test **one bit per channel**; for each set bit it reads an `s16` (`lh 0xc(t)`) and applies it — i.e. **only changed channels are stored per keyframe**, interpolated across the frame-time table.
- **Players:** pointer-table accessor `0x8001da94`–`0x8001dfa0` (derefs header `+0x4/+0x6`); animation core `0x8005ec94`–`0x8005f0f4` (frame walk + bitmask channel decode). Driving Flik forward moved player-Y and produced 2765 ANM reads at the `0x29998` block — deterministic.

## Generalization across the whole cast (offline, all model files)
The format is **universal**, validated over every model file on disc:
- **`.ALL` — 78/78 (100%)** carry a valid in-range `word0` section offset, across **CHARS, CHARS2, CHARS3, CHARS4, PLANTS, PLANTS2, BITS** (`SEED`/`PLANTTER`) **and the `LEVELxx` terrain `.ALL`** (e.g. `BADBUG 0x7a2`, `DIM 0x1316`, `PLANTTER 0x209a`, `SEED 0x1f54`). So one parser handles characters, props, plants, and terrain meshes.
- **`.ANM` — 55/58** have the relocatable pointer table (≥2 in-range offsets). **`hdr_u16[1]` = animation count**, confirmed: **FLICK = 40** (the hero), `ATTAFLIK = 4`, `PLANT01 = 3`, `FLY/BADBUG = 2` (simple actors). File size scales with it (FLICK `.ANM` = 178 KB).
- **3 `.ANM` outliers** (compact variants, all animCount = 2): `CHARS3/ACORN.ANM` (224 B — minimal), `CHARS3/BBIRD.ANM` (5120 B), `CHARS3/FDIM.ANM` (3980 B). Same family, table just not at the scanned offsets — flagged, not yet parsed.

⇒ B7's "generalize across the cast" residual is **closed**: the `.ALL`/`.ANM` model+animation format is one TT-authored scheme used game-wide. Runtime-validated on FLICK; structurally validated on all 78+58 files.

## Channel → bone binding (decoded live)
The `.ANM` is **skeletal animation** — a channel drives a **bone rotation**, not a vertex group:
- **Skeleton = array of 84-byte (`0x54`) bone structs** at `~0x8008a1f8` (per actor; next actor's skeleton is `+42×84` away → [[MEM - Skeleton bone transform 8008A1F8]]). FLICK = **24 bones** (sub-block `+4 = 24`; `+6 = 72 = 24×3` components; `+8 = 24`).
- **Each channel = one bone.** The animator decodes a channel into **3 s16** (keyframe `+0xc/+0xe/+0x10`), **linearly interpolated** between frame N (`t0`) and N+1 (`t1`) by fraction `t2` (0.16 fixed-point; `0x8000` = ½): `cur + ((next−cur)·t2 >> 16)`, written to the bone's **rotation at `+0x18/0x1a/0x1c`** with `+0x1e = 1` (w). Values are GTE-scaled (`4096 = 1.0`); an un-animated bone reads near-identity.
- The **bitmask** (1 bit/channel, `0x8005f028`) gates which bones update each keyframe — sparse, only moving bones stored. Keyframe records stride `0x72` in the `.ANM` data.
⇒ `.ANM` is a **24-bone skeletal animation** with sparse, interpolated per-bone Euler rotations. The skeleton then skins the `.ALL` mesh (GTE matrices) — the only remaining model residual.

## Skinning (decoded — GTE rigid transform)
The posed skeleton transforms the `.ALL` vertices via the **GTE**, decoded from disasm:
- **Per-bone matrix load** (`0x800605c4`): `lw` 5 words from the bone struct `+0x0` → `ctc2 rt_0..rt_4` (the **3×3 GTE rotation matrix**, 9 s16 packed in 5 words); then `+0x14/+0x18/+0x1c` → `ctc2 trx/try/trz` (**translation**). So a bone struct = `[matrix 5w @ +0][translation 3w @ +0x14]`.
- **Per-vertex transform** (skinning emitter `0x80014730`): `lwc2 ir1/ir2/ir3 ← vertex xyz` → **`mvmva sf m=1 v=3 t=1`** (GTE Matrix-Vector-Multiply-Add: **`posedVert = RotMatrix·V + Translation`**) → `swc2 mac1/2/3 → output`.
- ⇒ **rigid skinning**: each vertex is transformed by exactly one bone's matrix (`M·V+T`), then projected (RTPS) and drawn by [[FUNC_800172DC]]. (No per-vertex blend weights observed — one bone per vertex.)

**The full model pipeline is now mapped end-to-end:** `.ALL` (verbatim mesh) → `.ANM` bitmask keyframes → 24-bone skeleton ([[MEM - Skeleton bone transform 8008A1F8]]) → Euler→GTE matrix per bone → **`MVMVA` skin (`M·V+T`)** → RTPS project → `fcn.800172dc` draw.

## Shading / texture — UV question RESOLVED: no UVs
The character mesh is **untextured, indexed-colour gouraud** (decoded from the renderer's packet build `0x800173b0`+):
- Each primitive's **word0 carries a TYPE field** (`word0 & 0x3c000000`) selecting the record layout — variable-size records per type (colour index at `+0x2f` for one type, `+0x23` for another). This is why a fixed-`0x30` stride doesn't fit characters.
- The primitive carries a **5-bit colour/shade index** (`lb +0x2f`, `andi 0x1f`) that looks up **32-entry colour/shade tables at `0x800a7dd8` and `0x800910b0`** — **no texture page, no CLUT, no UV coordinates**. The "grey RGB" seen in the raw bytes is the indexed palette value, not a texture.
⇒ **No UVs / no textures on the character model** — it is flat/gouraud shaded via a small indexed palette. (UV residual closed.)

## Skinning weights — RESOLVED: none (rigid)
- Skinning is **rigid `MVMVA` (`M·V+T`), one bone per vertex** — **no per-vertex blend weights** (none observed in the GTE path).
- The **vertex data sits ~`base+0x800`** in the `.ALL`, read by **both** the skinning emitter (`0x80014xxx`) and the renderer (`0x800172dc`).
- (Note: the `0x8001474c` `MVMVA` leaf is a *shared* GTE helper — 60 calls/frame across many callers — so it is not FLICK-exclusive; FLICK's skinning is orchestrated by the model-proc functions `0x8001dxxx`.)

## Primitive grammar — per-type record sizes DECODED
Two primitive types, selected by the **`word0 & 0x3c000000`** type field (from the renderer dispatch `0x800173e4`):
- **Quad** — `(word0 & 0x3c000000) == 0x3c000000` → **`0x30`-byte record** (4 verts), colour/shade index at **`+0x2f`**.
- **Triangle** — otherwise → **`0x24`-byte record** (3 verts), colour index at **`+0x23`**.
- Each record = vertex coords (s16 xy + z per vert) + the 5-bit palette index at the record tail (→ tables `0x800a7dd8`/`0x800910b0`). The **caller** advances `a1` by `0x30`/`0x24` per type.
- Parsing `FLICK.ALL` primitive section (`@word0=0x1600`) with these strides walks a clean run of **76 primitives (23 quads + 53 tris)** to the list terminator (`0x21c4`); the file's tail region beyond that is a separate section (pre-`word0` vertex data + a trailing block).

## Residuals (minor — fine layout only)
- The `[0:word0]` vertex section layout and the **per-bone vertex-assignment** grouping (rigid one-bone/vertex, so a vertex-range/segment table — orchestrated by `0x8001dxxx`; the exact table not split) + the trailing post-primitive section.
- Field reconciliation: the animator's `+0x18` channel write vs the GTE load reading `+0x14..+0x1c` as translation (Euler→matrix build step between).
- The 3 compact `.ANM` outliers (ACORN/BBIRD/FDIM) — confirm the variant layout.

## Sources
- live: `tools/abl_dbg.py` (RAM search + `accessLog` renderer trace), `SCUS-94288_operator_backup.sav`
- disc: `REBUILD/files/CHARS/FLICK.ALL`, `FLICK.ANM`
- vault: [[Blocker - Character and plant model formats are unreversed]] · [[Finding - Visible terrain renderer]] · [[MEM - Terrain vertex buffer 8012C1D0]] · [[FUNC_800172DC]]
