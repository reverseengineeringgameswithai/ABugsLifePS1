---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - ALL ANM Format Grammar.md
aliases:
  - "Asset - ALL ANM Format Grammar"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - ALL ANM Format Grammar.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_ALL_ANM_Format_Grammar.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - ALL ANM Format Grammar
type: asset
updated: 2026-06-22
tags: [asset, model, animation, all, anm, milestone4, b7, gap-0026]
---

# Asset — `.ALL` / `.ANM` format grammar (editor-safe baseline)

> Consolidated, editor-oriented grammar for the Traveller's Tales model (`.ALL`) and animation (`.ANM`) formats ([[Gap Audit|GAP-0026]] / [[Blocker - Character and plant model formats are unreversed|B7]]). Synthesizes [[Finding - Character ALL model format]] + [[MEM - Skeleton bone transform 8008A1F8]] and ties them to the **same mesh-primitive grammar used by the LEVEL.RAW geometry chunks** ([[Asset - LEVEL.RAW Chunk Role Table]] Region C). Examples are metadata (offsets/counts), never payload bytes.

## File families inspected
`CHARS/CHARS2/CHARS3/CHARS4` (characters), `PLANTS/PLANTS2` (plants), `BITS` (`SEED.ALL`, `PLANTTER.ALL`), `LEVELxx/TERRAIN.ALL`/`TERR1.ALL`. **Round-trip validated `.ALL` 78/78, `.ANM` 58/58** (2026-06-22, `tools/parse_all_anm.py`). `.ALL`/`.ANM` are **uncompressed** (not PROPACK).

## `.ALL` — model (grammar — round-trip VALIDATED 78/78, 2026-06-22)
- **Position-independent** (0 relocations; loads verbatim to its RAM slot). Uncompressed.
- **`word0` (file `+0`) = byte offset** splitting **two element streams**: `SECTION_A = [4:word0]`, `SECTION_B = [word0:EOF]` (detail/LOD levels). Each is a flat sequence of **primitive lists** + **skin/vertex blocks** (FLICK `word0=0x1600`).
- **Primitive record (on-disk):** `[N colour words][nv vertices]`. A **colour word** = little-endian `[B][G][R][cmd]`; a **vertex** = `[s16 x][s16 y][s16 z][u16 packed-normal]` (8 B). **Type = the LAST colour word's `cmd & 0x3c`:** `0x3c` → **quad** (`nv=4`, tex id `+0x2f`), `0x34` → **triangle** (`nv=3`, tex id `+0x23`); a `00 00 00 00` word **terminates the list**. Renderer [[FUNC_800172DC]] strides `+0x30` quad / `+0x24` tri. Characters are **gouraud** (one colour word per vertex, `N=nv`) → quad record `0x30`, tri `0x24`; flat shading = `N=1`. ⚠️ The earlier "type from `(word0 & 0x3c000000)` at record+0" read the **runtime-expanded** record, not the on-disk one — the on-disk discriminator is this colour-cmd scan.
- **Skin/vertex block:** `u16 vcount; u16 unk;` then `vertex[vcount]` (8 B each, byte`[6:8]==0x0110` packed-normal marker), then a **bone-attachment `s16` index list** using `-1/-2/-3` (`FFFF/FFFE/FFFD`) sentinels, walked by skinning core [[FUNC_8005EC94]] (entry `0x8005ec84`), bone matrices at `0x80089f58 + 84*idx`. ⚠️ those sentinels live **inside** the attachment lists — they do **not** delimit `[4:word0]` (and stray `FFFF` also occurs as ordinary vertex coords).
- **Shading:** 5-bit indexed gouraud, no UV/texture on characters.

## `.ANM` — animation (grammar — round-trip VALIDATED 58/58, fully field-typed, 2026-06-22)
- **One uniform layout** — the ACORN/BBIRD/FDIM "outliers" are just `anim_count==2` files (**no compact-inline special case**). File = `[u16 res0][u16 anim_count][u32 res1][u32 offset[anim_count]]` (pointer table = **absolute** file offsets in anim-index order; `0` = empty anim) then sub-blocks packed contiguously in ascending-offset order to EOF.
- **Sub-block:** `+0 u16 w0` · `+2 u16 fcflag` (`frame_count = fcflag & 0x7fff`) · `+4 u16 n4` · `+6 u16 n6` (s16 **values per frame**) · `+8 u16 n8` (frame-time entries) · `+0xa u16 n10` (meta bytes) · `+0xc s16[n8]` frame-time/key table (`-1/-2/-3` sentinels) · `u8[n10]` meta · then **dense, frame-major `s16[frame_count][n6]`** keyframes. **Size = `0xc + 2·n8 + n10 + 2·n6·frame_count`** (byte-exact, all 299 sub-blocks). ⚠️ There is **NO per-frame bitmask** — the earlier "bitmask keyframes" claim is **refuted** (every channel carries an s16 every frame in this on-disc image).
- **Skeleton:** per-model bone count, 84-byte stride at `~0x8008a1f8` ([[MEM - Skeleton bone transform 8008A1F8]]); rigid GTE `MVMVA`, one bone/vertex, no weights. Sampler core [[FUNC_8005EC94]] region (`FUNC_8005EC80`/`FUNC_8005F110`).

## Relationship to LEVEL.RAW meshes
The `0x101`/`0x102` mesh def/payload chunks (ch34–68) carry the **same RGB-gouraud primitive grammar** (visible as trailing `…34`/`…3c` colour bytes) and are drawn by the same renderer — so this grammar is the **shared mesh format** for actors, plants, and level geometry. The level meshes add the `0x101` definition wrapper (obj-id + sub-mesh table); characters embed the primitive list directly via `word0`.

## Parser / closure status — round-trip VALIDATED (2026-06-22; GAP-0026)
- **Committed tool: `tools/parse_all_anm.py`** — a byte-exact round-trip parser/emitter for BOTH formats with a CI-safe self-test (metadata only, **no payload emitted**). **`emit(parse(x)) == x` holds over the full repo corpus: `.ALL` 78/78, `.ANM` 58/58** (run: `python3 tools/parse_all_anm.py`). ⇒ the GAP-0026 acceptance — *a round-trip `.ALL`/`.ANM` exporter covers all 78/58* — is **MET**. Grammars decoded from the consumers in `SCUS_942.88` (renderer [[FUNC_800172DC]], skinning core `0x8005ec84`, `.ANM` sampler `FUNC_8005EC80`) and proven by the assert.
- **`.ANM` = fully field-decoded** — every byte typed (editing one keyframe perturbs exactly its 2 bytes; restore byte-exact).
- **`.ALL` = byte-exact round-trip; primitive layer fully field-decoded** (6634 records re-emitted from fields, 0 mismatch). The **skin-attachment tails + variable section-B mini-headers** are byte-preserved **verbatim** (≈47% of CHARS bytes field-typed; the large `LEVEL*/TERRAIN.ALL` bodies are mostly verbatim).
- **Residual (honest, within Resolved):** *semantic* field-typing of the `.ALL` non-primitive spans — the `-1/-2/-3` skin-attachment run semantics + the section-B mini-header. Reproduction is already exact; this is completeness, not round-trip. The skinning **mechanism** is decoded ([[FUNC_8005EC94]]: sentinel `s16` index list + `0x80089f58 + 84*idx` bone matrices; per-frame transient buffers built from the `.ALL`); a tempting "`-2`-count = bone count" lead was **refuted (3/44 CHARS)** — recorded so it isn't re-chased.

## Minor open details (non-blocking)
- The animator `+0x18` write vs GTE `+0x14` read reconciliation (Euler→matrix step).
- Per-channel meaning of the `.ANM` `n6` value lanes (the *layout* is byte-exact; the semantic channel→bone map is partial).

## Modding relevance & safe-editing constraints
- **Safe now:** edit **vertex coordinates** (s16 triples) and **gouraud RGB** in place — fixed record sizes, no relocation, no recompression (`.ALL` is uncompressed). Keep record counts/sizes constant.
- **Not safe / unknown:** changing prim counts (shifts `word0`/section), re-binding verts to bones, retargeting animation channels.
- For LEVEL.RAW meshes, combine with [[Asset - PROPACK Rebuild Strategy]] (recompression budget).

## Related
[[Finding - Character ALL model format]] · [[MEM - Skeleton bone transform 8008A1F8]] · [[Asset - Character and plant models]] · [[Asset - Chunk 34 Master Mesh]] · [[FUNC_800172DC]] · [[FUNC_8005EC94]]
