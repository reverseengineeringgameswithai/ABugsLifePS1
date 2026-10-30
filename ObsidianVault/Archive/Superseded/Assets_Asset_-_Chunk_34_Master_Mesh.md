---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - Chunk 34 Master Mesh.md
aliases:
  - "Asset - Chunk 34 Master Mesh"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - Chunk 34 Master Mesh.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_Chunk_34_Master_Mesh.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - Chunk 34 Master Mesh
type: asset
updated: 2026-06-21
tags: [asset, levelraw, chunk34, mesh, milestone4, gap-0023, gap-0011]
---

# Asset — Chunk 34 master mesh (modding-grade baseline)

> [!warning] Render/collision Canon split
> This legacy asset note preserves the chunk-34/35 investigation. For current Canon, use [[SYS_render_collision_source_separation]] and [[WHYPE_visible_floor_equals_collision]] before making claims about visible floor, chunk-35, or collision. Visual floor and collision source are separate.

> Finishes the modding-grade chunk-34 baseline ([[Gap Audit|GAP-0023]]) and advances the spawn-floor question ([[Gap Audit|GAP-0011]]). **Key reframe (2026-06-20):** chunk 34 (`0x101`) and chunk 35 (`0x102`) are a **definition + payload PAIR** for object 0 — the **master/world mesh** — not two competing terrain sources. Offline-decoded from the local decompressed cache; dynamic transform claims are labeled **local-only**.

## Commands / tools used (offline, deterministic)
`tools/dump_level_raw.py` → decompressed cache; `tools/level_raw_chunk_manifest.py` → marker classification; **`tools/decode_chunk34.py`** (tracked, CI-safe, metadata-only) → reproducible header + offset-table structural report; direct struct parse of `tools/LEVEL_RAW_decompressed/LEVEL.RAW.decompressed` at chunk-34 `decomp_off` (from `chunk_index.json`). Byte-exact decoder ([[Asset - PROPACK Rebuild Strategy]]).

## Structure summary (CONFIRMED-fmt)
Chunk 34 = **mesh DEFINITION**, decompressed 182,342 B.
- `u16@0x00 = 0x0101` (marker: mesh-definition) · `u32@0x04 = 0` (object id = 0 → **master/world**).
- **`u16@0x0a = 0x28 = 40` = sub-mesh count.** *(Corrects the older Finding's "`+0x08`": the count is at **`+0x0a`** — confirmed by direct read; resolves the vault off-by-2.)*
- `@0x0c …` : **40 sub-mesh records, stride 0x10** (observed). Record fields are mostly `u32` values in the `0x19000–0x2bxxx` range = **byte offsets into the shared vertex/data pools** near the chunk's end.
- `@0x2c` : the **`u32` sub-mesh offset table** (`0x1910, 0x3180, 0x42e2, 0x4f3a, …`). **First-hand (2026-06-21, `tools/decode_chunk34.py`):** **33 slots parse cleanly** — 32 monotonic in-bounds offsets + 1 empty (`[19]=0`) — ending at `0x28d88`, **immediately before** the pools at `0x29998`; a *secondary* record/index structure begins at **`+0xb0`** (small increasing u16 run + `fe ff`/`fd ff` padding), **not** more offsets. **So `count@0x0a = 40` ≠ the 33 offset slots** — the count-vs-table relationship and that secondary structure are the precise undecoded part (needs consumer-tracing of the fcn that walks the table).
- Header pointer fields `@0x10/0x14/0x18/0x24/0x28` reference **shared pools** at the tail (`~0x29998, 0x2a368, 0x2adc8, 0x2b828 → EOF 0x2c846`).

## Pools — vertex/index/material hypotheses (LIKELY)
The tail pools decode as **s16 triples**:
- **p1 / p3** = clean model-space **vertex pools** (values ±~1000–32k; body s16 range = **−31888 … 32752**, consistent with s16 vertex coords).
- **p2 / p4 / p5** = mixed `4096` (= **1.0** in 1/4096 fixed point) and `4620` → **per-sub-mesh 3×3 transform matrices**; `0xfffd` (−3) = padding.
- **Materials:** per the shared mesh-primitive grammar ([[Asset - ALL ANM Format Grammar]]), primitives carry **RGB gouraud bytes** (no UV on this class) — visible as the `…34` / `…3c` trailing bytes in the `0x102` payloads. **No texture** indices observed on the master mesh (indexed-colour gouraud). *Hypothesis, not consumer-traced.*

## Payload relationship — chunk 35 (`0x102`, obj 0)
The master mesh's **vertex payload is chunk 35** (`0x102`, obj-id 0), which decompresses into runtime buffer **`0x8012c1d0`**, consumed by **[[FUNC_800172DC]]** (a *general* mesh renderer). So "chunk 34 vs chunk 35" was a false split: **34 = definition, 35 = payload** of the same object-0 mesh.

## Coordinate scale & model→world transform (mixed confidence)
- **The transform is NOT in the chunk** — applied at draw time by the GTE. (CONFIRMED: no transform constants in the def beyond the per-sub-mesh 3×3 matrices.)
- **Scale (LOCAL-ONLY, from [[MEM - Terrain vertex buffer 8012C1D0]] §G33):** model→world column norms ≈ **Y 1.000, X 1.569, Z 1.046**, captured via `execTrace` at RTPT `0x80017464` in [[FUNC_800172DC]]. *Local-only on the dirty fork — needs independent reproduction ([[DuckStation Fork Reproducibility]]).*
- **The explicitly-missing variable = the world translation/origin** (`WORLD_PAYLOAD_Y_OFFSET`). The editor uses an **empirical** `1450` (per project memory) — **now refuted, see the live-validated section below.**

## LIVE-VALIDATED model→world — visible terrain is `FUNC_80010000`, not 34/35 (2026-06-22)
> [!important] Supersedes the §"Coordinate scale" G33 norms **and** the empirical `1450`.
> **B7 = true negative:** [[FUNC_800172DC]] (RTPT `0x80017464`, buffer `0x8012c1d0`) draws **only Flik** (1032 hits each in LEVEL01 + LEVEL02; 0 wide-XZ triangles). Chunk-34/35 is **never drawn** there → the G33 "Y 1.0 / X 1.569 / Z 1.046" norms were **Flik's** model→view, not terrain. The chunk-34 master mesh is the occluded/world-mesh layer; its own world-origin is moot for rendering.
>
> **The visible terrain is [[FUNC_80010000]]** (per-triangle GTE RTPT @ `0x800106f8`; submesh loop `0x8001eacc→0x800206ac`, floor handler `0x8001eb3c`, via `j 0x80020698 → jal 0x80010000`). Model→world:
> **`world = (R⁻¹·(TR + (RT/4096)·v) + Cdiv) × 32`** — scratchpad camera struct `0x1f800374`: C @+0x00, Cdiv (=C/32) @+0x10, RT (world→view, s16/4096) @+0x20, TR @+0x54. RT row-norms (1.6,1,1) = an aspect diag on an orthonormal R.
> **VERIFIED two ways:** (1) forward-projection EXACT — computed SXY == live GTE `SXY0` on 3 captures; (2) gold-standard — a regular ~16000-unit floor-grid tile **under Flik** reconstructs to his footing (world Y −89250 vs Flik −88578 → dY 672 ≈ floor thickness) on `level01_lookingdown_flatground.sav`.
> **REFUTED:** the editor's `(v.x, −v.y+1450, v.z)` — both `WORLD_PAYLOAD_Y_OFFSET=1450` and the per-vertex Y-flip are wrong (no Y flip); and `world = v + T_obj×32` (the object-node `lw(s2+0/4/8)` fields are local extents, not the world anchor).
> **Editor fix:** map DAT floor verts via the validated affine (no Y-flip). **Residual:** isolate the on-disk per-submesh placement (object node at `0x8001eb3c`) for a fully-offline editor; and `RTPT 0x800106f8` is shared across `FUNC_80010000` meshes — filter by the floor handler for absolute floor-only rigor. See [[Gap Audit|GAP-0023]].

## RESOLVED — floor placement reads from LEVEL.DAT (2026-06-22)
> [!success] The "residual" above is **CLOSED for the floor**: the model→world is an **offline read from `LEVEL.DAT`** — no emulator needed.
> **Representation = (B) local verts + per-submesh world anchor `T_obj`** (NOT world-space verts). `LEVEL.DAT` holds a **node array** — LEVEL01 @ file `0x45f0`, **stride `0x18`**: `+0x00/04/08 = T_obj` (s32 world anchor, stored verbatim, **disk == runtime**), `+0x14 = payload file offset`; load reloc = `runtime_payload = DATbase 0x801607f8 + node[+0x14]`.
> **Offline map (editor file units): `world = T_obj + v_local`** — component-wise, **no Y-flip, no scale** (`v_local` = s16 payload vert at `payload_base+4 + i*0x0c`). **Candidate A** = node @ DAT `0x4860`, `T_obj=(-8192,-8192,-8192)`, `+0x14=0x188cc`.
> **CORRECTION:** the §"LIVE-VALIDATED" claim that `world = v + T_obj×32` is "refuted" / `lw(s2+0/4/8)` are "local extents" was a **mislabel** — `lw(s2+0/4/8)` **is** `T_obj` (looks bbox-like only because the floor tiles on an 8192 grid). Live: `R⁻¹·TR + C` == the node's `+0/4/8` exactly; the simple `world = T_obj + v_local` holds (no ×32 in editor file units; ×32 → runtime world).
> **VERIFIED:** LEVEL01 3-way (disk `T_obj` == runtime node == `T_obj+v_local` == GTE-reconstructed world; 2 anchors) + cross-level static (`LEVEL04/LEVEL.DAT` @`0x78ec`, 86 nodes; `LEVEL05` @`0x6710`, 97 nodes; all 8192-grid, flat).
> **Editor fix:** `scene_importer.survey_instances` currently reads the floor placement from the WRONG record (pass-1 trailer `row+0/4/8`); read it from the **node `src+0x00/04/08`** and set `scene3d.py` `place → (ox+v.x, oy+v.y, oz+v.z)` (drop `WORLD_PAYLOAD_Y_OFFSET`/`-v.y`).
> **Residual:** rotated meshes need `M_obj` (`world = T_obj + M_obj·v`; det≈1.74 on a non-LEVEL01 object; axis-aligned floor = `M_obj=I`); decor Y-flip live-unconfirmed. See [[Gap Audit|GAP-0023]].

## Relationship to chunk-32 collision
Independent layer: collision = **chunk 32** (`0x103`) planes → sector table `0x800a7e48` ([[Finding - Collision on-disk source is chunk 32]]). The master mesh (34/35) is **visual geometry**; collision does not derive from it ([[Finding - Visual is not collision]]). Editing chunk 34/35 changes appearance, not footing.

## Spawn-area floor question (advances GAP-0011)
- `Finding - Chunk 34 master mesh structure` argued the spawn ground is chunk 34/35 (0 DAT-terrain verts within 2000u of Flik at Z 15403; DAT terrain Z ≤ 9774).
- [[Finding - Visible ground from DAT verts]] (f13) argues the foreground floor under Flik = LEVEL.DAT via [[FUNC_80010000]].
- **This baseline supports the chunk-34/35 = world-mesh reading** (object 0 = the master world geometry), which is *consistent* with "the broad spawn floor is the world mesh, while DAT objects (Candidate A) are local decor/overrides." **Not resolved** — the decisive test (pick the spawn-floor pixel → trace its draw call's payload provenance) is **deferred to M7** ([[Gap Audit|GAP-0011]]/[[Gap Audit|GAP-0038]]). Labeled separately, not silently merged.

## Functions & symbols involved
[[FUNC_8001A1DC]] (decompressor, writes the buffer) · [[FUNC_800172DC]] (`0x800172dc`, general mesh renderer, RTPT `0x80017464`) · [[FUNC_80010000]] (DAT-object mesh emitter) · buffer `0x8012c1d0` ([[MEM - Terrain vertex buffer 8012C1D0]]). See `symbols/re_symbols.sym`.

## Confidence ledger
- Marker `0x101`/obj 0/count 40 @ `+0x0a` — **CONFIRMED** (direct read).
- Offset table @0x2c — **CONFIRMED (partial)**: 33 slots byte-verified monotonic + in-bounds (`tools/decode_chunk34.py`); the **count(40)-vs-33-slots mapping** + the per-record schema (secondary structure `@+0xb0`) remain **open** (consumer-trace needed).
- Pools = vertex/matrix — **LIKELY**.
- Scale Y≈1.0 — **LIKELY (local-only)**. World origin — **Unknown**.

## Remaining unknowns / next experiments
1. **Resolve `count@0x0a=40` vs the 33 parsed offset slots** and byte-validate the per-record schema (the secondary structure `@+0xb0`) by **consumer-tracing the fcn that walks chunk-34** — which register indexes the table, and how 40 maps to 33 offsets + 4 pools.
2. **Pin the world origin** (`WORLD_PAYLOAD_Y_OFFSET`) — the one missing transform variable. Capture the GTE model→view RT/TR **at a wide-XZ terrain draw** in [[FUNC_800172DC]] (RTPT `0x80017464`), compose with the camera view⁻¹, and cross-check vs Flik anchor `0x800a6500`. **Clear the B7 capture-aliasing blocker first:** at spawn the buffer `0x8012c1d0` is time-multiplexed and held `FLICK.ALL` (compact model) — `fcn.800172dc` ran 0× that frame, so the capture saw Flik, not terrain. **Live next-target:** filter `execTrace@0x80017464` to the wide-XZ/terrain `geometry_kind`, or trace the other emitters of dispatcher `fcn.8001DFE4` (`0x80014b04 / 0x80014ee0 / 0x800153d0 / 0x800163e0`), or reach a scene/frame where the master mesh is actually drawn.
3. ✅ **GAP-0011 decided (M7, 2026-06-21):** trace/`gpu.pickObject` showed the visible spawn floor = LEVEL.DAT via [[FUNC_80010000]] (not chunk-34/35) — see [[Gap Audit|GAP-0011]] **Verified**; chunk-34/35 is the occluded/world-mesh layer.

## Related
[[Asset - LEVEL.RAW Chunk Role Table]] · [[Finding - Chunk 34 master mesh structure]] · [[Finding - Visible ground from DAT verts]] · [[Finding - Visual is not collision]] · [[Asset - ALL ANM Format Grammar]] · [[MEM - Terrain vertex buffer 8012C1D0]] · [[DuckStation Fork Reproducibility]]
