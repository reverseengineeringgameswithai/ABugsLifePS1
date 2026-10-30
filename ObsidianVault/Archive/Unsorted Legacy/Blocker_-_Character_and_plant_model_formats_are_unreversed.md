---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Character and plant model formats are unreversed.md
aliases:
  - "Blocker - Character and plant model formats are unreversed"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Character and plant model formats are unreversed.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Character and plant model formats are unreversed
type: blocker
id: B7
severity: MEDIUM
category: asset-decoding / file-format
confidence: CONFIRMED
tags: [blocker, medium, models, animation, all, anm]
updated: 2026-06-22
---

# 🟡 B7 — Character / plant model + animation formats (`.ALL` / `.ANM`) are unreversed

> ⚠️ **Partially unreversed** (audit 2026-06-22): static geometry + the skinning *mechanism* are decoded, but the per-bone vertex→bone **binding** is OPEN (GAP-0026), and there is **no committed extractor** — so this is not "solved game-wide / Low." See [[#Audit reconciliation (2026-06-22)]].

> Every visible actor and prop ships as a bespoke Iguana `NAME.ALL` (model bundle) + `NAME.ANM` (animation) pair — **78 `.ALL` + 58 `.ANM`**, the largest asset class by file count — with no public spec and no extractor. Only the *terrain* `.ALL` variant was ever probed, and that hypothesis was refuted.

> [!check] **Update (2026-06-18) — `.ALL` structurally decoded via live trace (no operator).** `FLICK.ALL` (Flik, 13548 B) is **resident at `0x8012c1cc`, 95.5% verbatim** (12936/13548) and **position-independent — 0 pointer relocations** (the loader fixes up nothing; internal references are offsets, not absolute addrs). Structure recovered:
> - **Header word0 = a section offset** (FLICK `0x1600`, BADBUG `0x7a2`, FLY `0xafe` — all in-range) pointing to the **renderable primitive list**.
> - **Primitive list (`@0x1600`)** = records of `[RGB colour (3 bytes, grey) + command byte]` (e.g. `56 56 56 3c` — colour + **GP0 `0x3c` gouraud-quad code**, exactly what the renderer emits) followed by **s16 vertex-coordinate triples** (model-space, ±100: `−39,−82,−2 / −50,−46,−3 …`).
> - **Renderer = `fcn.800172dc`** (`0x8001745c`–`0x800174c8`) reads this section every frame to draw Flik (mixed h/w strides = structured primitive parse).
> - **`[0x2698:]` = posed/animated vertex region** (differs from the file's rest pose; the `.ANM` poses it in place).
> - **⚠️ Geometry cross-finding:** the model lives in the **same `0x8012c` buffer** the G30 work attributed to *terrain*, and the **same `fcn.800172dc`** renders both ⇒ `fcn.800172dc` is a **general mesh renderer** and `0x8012c…` is a **shared vertex buffer** (holds the character model in `operator_backup`). Flag for reconciliation with [[Finding - Visible terrain renderer]] / G30 — do not override the operator-verified terrain result; investigate. From 0% to: residency + load addr + header + primitive grammar + renderer + anim boundary. **Severity → Medium.** → [[Finding - Character ALL model format]]
>
> **`.ANM` also decoded (live, walk animation):** `FLICK.ANM` (~0x2c000 B) at `0x800ff984` is a **relocated pointer table** → per-animation **sub-blocks** (idle/walk/…). Sub-block header = frame count (`+2`, masked `0x7fff`), channel counts (`+4/+6/+8`), default values, frame-time table (stride 6); **keyframes are bitmask-compressed** — a bit per channel selects which channels carry an `s16` this frame. Played by `0x8005ec94`–`0x8005f0f4` (core) + `0x8001da94`–`0x8001dfa0` (table accessor). Residual: channel→bone/vertex binding + interp math.
>
> **Generalized across the whole cast (2026-06-18):** `.ALL` `word0` section offset valid on **78/78 (100%)** files (CHARS/CHARS2/3/4, PLANTS/PLANTS2, BITS, *and* LEVELxx terrain `.ALL`); `.ANM` pointer table on **55/58** with `hdr_u16[1]` = animation count (FLICK 40 / ATTAFLIK 4 / PLANT01 3 / FLY 2; 3 compact outliers ACORN/BBIRD/FDIM). One TT scheme covers characters, props, plants, terrain meshes. Catalog → [[Asset - Character and plant models]]. **Severity → Medium** (static format decoded, but the vertex→bone binding is still OPEN — see audit reconciliation; this is *not yet* a game-wide "solved/Low" result, and the validation is not repo-reproducible).
>
> **Channel→bone binding resolved (2026-06-18):** `.ANM` is **24-bone skeletal animation** — each channel = one bone's **rotation** (3× s16 Euler, keyframe-interpolated by frac `t2`), written to `bone[i]+0x18` in an **84-byte-per-bone skeleton at `0x8008a1f8`** → [[MEM - Skeleton bone transform 8008A1F8]]. Only **skinning** (skeleton→vertex GTE transform) remains of the whole model pipeline.
>
> **Skinning decoded → full pipeline mapped (2026-06-18):** rigid **GTE `MVMVA` (`posedVert = M·V + T`)**, one bone per vertex — bone matrix (`+0`) + translation (`+0x14`) loaded via `ctc2 rt_*/trx` (`0x800605c4`), per-vertex transform at emitter `0x80014730`, then RTPS + draw by `fcn.800172dc`. **Entire `.ALL`/`.ANM` model pipeline is now traced end-to-end** (file → skeleton → skin → render); only fine grammar/UV details remain.
>
> **UV + skinning-weight questions RESOLVED (2026-06-18):** **No UVs / no textures** — the character mesh is **indexed-colour gouraud** (5-bit colour/shade index per primitive → 32-entry tables `0x800a7dd8`/`0x800910b0`; a `word0 & 0x3c000000` type field selects variable record layout). **No skinning weights** — rigid `MVMVA`, one bone/vertex (verts ~`base+0x800`, read by skin emitter `14xxx` + renderer `172dc`). Residual is now only the per-type primitive record sizes + the rigid per-bone vertex-assignment table — grammar detail. → [[Finding - Character ALL model format]]. *(Audit 2026-06-22: the per-bone vertex→bone binding turned out NOT to be merely cosmetic — it is OPEN and blocks an animated exporter; see GAP-0026 and the reconciliation section below.)*

**Severity:** ~~Major~~ → **Medium** (static `.ALL`/`.ANM` decoded + skinning MECHANISM mapped, but per-bone vertex→bone BINDING is OPEN (GAP-0026) and there is no committed extractor → not "solved game-wide") · **Impact:** High · **Likelihood:** Low · **Confidence:** CONFIRMED (`.ALL`=model primitive list + s16 verts; `.ANM`=pointer-table of bitmask keyframes) · **Difficulty:** High (custom format)

## Audit reconciliation (2026-06-22)
- **Frontmatter MAJOR vs body "Low" vs reality reconciled → MEDIUM.** The body repeatedly claimed "Low / solved game-wide"; that overstates the actual state.
- **What IS decoded:** static geometry + skinning *mechanism* — `.ALL` word0 prim-list (78/78), `.ANM` pointer table (55/58), 24-bone / 84-byte-per-bone skeleton, rigid `MVMVA` skin transform.
- **What is OPEN:** the per-bone vertex→bone **BINDING** run semantics. The "-2 count = bone count" rule was **REFUTED** (only 3/44 match), which **blocks a full animated exporter** — tracked as **GAP-0026 (In Progress)**.
- **Not repo-reproducible:** there is **NO committed extractor** (`tools/parse_all_anm.py` does NOT exist), so the "validated 78/78" claim cannot be reproduced from the repo. The "solved game-wide / Low" callouts in the body are softened accordingly.

> [!note] The "Iguana Entertainment" attribution below is **stale** — [[Blocker - Original toolchain ground-truth is unmined|B13]] was corrected: the developer is **Traveller's Tales** (Iguana was only the PROPACK licensee). `.ALL`/`.ANM` are TT's custom formats.

## What is known (evidence)
- The full cast as `.ALL`+`.ANM` pairs across `CHARS/` (FLICK, GYPSY, HEIM, MANNY, ROSIE, SLIM, DIM, FRAN, MOS, GRUB, WASP, FLY, BADBUG), `CHARS2/3/4` (DOT, ATTA, MOLT, BBIRD, BADWORM, …) and `PLANTS/`+`PLANTS2/` (PLANT01–14). The EXE lists every path (`chars\flick`, `plants\plant01`, …). `FLICK.ALL` header `00 16 00 00 74 74 74 3c …`; `FLICK.ANM` `00 00 28 00 …`.
- **Partial prior contact:** the *terrain* `.ALL` (`TERRAIN.ALL`/`TERR1.ALL`) was examined during the G18–G22 floor-source hunt ("s16 coordinate-pair streams"), but the hypothesis that the walkable floor is built from them was **REFUTED** (G20/G21, 0 EXEC hits). Character/plant `.ALL`/`.ANM` were never examined.
- `.ALL`/`.ANM` are **custom Iguana Entertainment formats** (the developer, per [[Blocker - Original toolchain ground-truth is unmined|B13]]) — not a standard PS1 container; internal grammar unknown.

## Why it matters
- All character models, skeletal/vertex animation, and props — required for any model ripping, character modding, or claim of asset-class coverage. It is also where most of the game's *authored 3D content* lives.

## Dependencies
- **Depends on:** [[Blocker - Function boundaries and overlays evade the static call graph|B17]] (must RE the loader) and benefits from [[Blocker - Original toolchain ground-truth is unmined|B13]] (PROPACK may pack `.ALL`; the partly-mapped terrain loader is a foothold).

## Research opportunity (direction only)
- The header grammar is recoverable by tracing the `chars\`/`plants\` loader and the already-partly-mapped `TERRAIN.ALL` loader (`fcn.8002ffa8`/`fcn.8002fce8`), and by testing whether the solved LEVEL.RAW decoder ([[Finding - LEVEL.RAW is compressed]]) decodes `.ALL` (in case they share the PROPACK packer). `.ANM` would then correlate to the animation update path. (Direction only.)

## Evidence & sources
- corpus (disc): `REBUILD/files/CHARS*/*.ALL|*.ANM`, `REBUILD/files/PLANTS*/*`, `REBUILD/files/LEVEL01/TERRAIN.ALL`
- vault: [[Assets]] · [[Asset - LEVEL.RAW]] · [[Finding - LEVEL.RAW is compressed]]
- See also: [[Blockers]] · [[Risk Matrix]]
