---
kind: memory
id: MEM_-_LEVEL.RAW_chunk_model
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_confirmed
confidence: confirmed
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Memory Structures/MEM - LEVEL.RAW chunk model.md
aliases: [MEMLEVEL.RAW chunk model, MEM_-_LEVEL.RAW_chunk_model]
archived_source: ObsidianVault/Archive/Superseded/Memory_Structures_MEM_-_LEVEL.RAW_chunk_model.md
patch_policy: unknown
---

# MEM_-_LEVEL.RAW_chunk_model

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Memory Structures/MEM - LEVEL.RAW chunk model.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: MEM — LEVEL.RAW chunk model
- Archived full source: `ObsidianVault/Archive/Superseded/Memory_Structures_MEM_-_LEVEL.RAW_chunk_model.md`
- Migration action: `convert_to_canon`
- Migration confidence: `confirmed`
- Migration reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

## Legacy Heading Index

- `# MEM — LEVEL.RAW chunk model`
- `## Load + decompress pipeline`
- `## Key chunks (LEVEL01)`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Memory_Structures_MEM_-_LEVEL.RAW_chunk_model.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Chunk subtype markers, campaign-wide (E16, 2026-08-04)

**Every chunk carries its own subtype marker: a `u32` at decompressed offset
0.** (The chunk-34 note's "marker 0x101@0" generalises to all chunks.) A chunk's
family is therefore *readable*, not something to infer from load order.

Marker space, classified across **all 24 `LEVEL*.RAW`**
(`analysis/phase4_e16_chunk_census.json`, gated by
`tests/test_phase4_e16_chunk_census.py`):

| marker | family | campaign count |
|---|---|---|
| `< 0x20` | texture / VRAM-upload resource (size-varied) | 296 |
| `0x22` | sprite / animation strip container | 228 |
| `0x23` | seed table — **always exactly 1,796 B** | 17 |
| `0x24` | backdrop panorama + sky palette | 9 |
| `0x101` | mesh definition (+4 object id, +0x0A sub-mesh count) | 208 |
| `0x102` | mesh payload (+4 object id) | 228 |
| `0x103` | collision planes + sky table | 14 |
| `0x104` | collision sector-source — **always exactly 17,764 B** | 14 |

**Mesh pairing law:** every `0x101` definition has a `0x102` payload of the same
object id — never the reverse. The one asymmetry is **object id 11: a payload
with no definition in 16 of 17 mesh-bearing files** (id 0 likewise in 4). Note
as a lead only: E05 found *actor* id 11 is the seed, but these are mesh object
ids and the two numbering spaces are not shown to be the same.

**Correction:** chunk 33 was recorded as the "collision sector-source *tail*" of
chunk 32. Its marker is `0x104`, distinct from 32's `0x103` — a family of its
own, once per collision-bearing file at fixed size, not a continuation.

**New enumerated residual:** 74 chunks carry markers outside every classified
family — `0x20`, `0x26`, `0x28`–`0x2A`, `0x30`–`0x58`, `0x5A`, `0x5C` —
concentrated in `LEVEL00/*.RAW` (52), `LEVEL08/LEVEL1.RAW` (5) and
`LEVEL09/LEVEL1.RAW` (17, entirely marker `0x20`). Invisible to the older
LEVEL01-only census.

**Correction history (three passes).** The first follow-up called all 74 chunks
images from dimension-shaped headers; that was too broad. A second pass then said
only marker `0x20` was an image family; later consumer analysis showed that this
over-corrected. The settled count is **63/74 confirmed image resources**: 17 marker
`0x20` sky/backdrops plus 46 pointer-registered frontend images. The remaining 11
marker-`0x26` chunks have a loader disposition but no image semantics established.

**Marker `0x20` is pinned: a
320×256 16bpp RGB555 full-screen image** (17 of them fill
`LEVEL09/LEVEL1.RAW`) — identical headers and sizes across all 17,
`16 + 320×256×2 = 163,856` exactly, bit 15 clear on every sampled pixel, and
its role is the sky/backdrop, not a loading screen. At that first pass the other
**57 were not pinned**: size arithmetic alone could not fix their layouts, and a
uniqueness check found **0 of 74** chunks uniquely determined (2–12 fits each).
Reading later consumers subsequently resolved 46 of those 57; marker `0x26`
(11 chunks) remains the semantic residual.

### Loader-confirmed header layout (0x8003A318)

`high_heap_loader_level_raw_decompress_orchestrator` reads `lw s4,0(fp)`
immediately after the decompressor and then `slti s4,32` — so **the marker at
+0 and the `<0x20` class split are retail-code facts**, not data-shape
inferences. Its dispatch compares 32/34/35/36/257/258/259/260, matching the
observed marker space exactly.

**Header layout, pinned by the LoadImage call site:**
`LoadImage(rect_from(+4,+6), base + 12 + even(u16@+8))` — pixel data begins at
**chunk + 12 + even(field@+8)**. The previously-guessed "768-byte palette" is
simply the value of the `+8` field. The loader then advances `rect.x` by
`rect.w` in a tiled VRAM upload loop bounded at the 768/192 region.

**Marker `0x20` is the SKY/BACKDROP resource.** Its handler decodes the u16 at
+16 as RGB555 (`andi 0x1f` / `>>5 & 0x1f` / `>>10`, scaled 5→8 bits via the
`0x84210843` reciprocal-multiply) into **0x800771BC (R) / 0x800771C0 (G) /
0x800771C4 (B)** — exactly the per-level sky-colour cache the starry-night mod
patches. Since `16 + 320×256×2` matches the chunk size exactly, that u16 is the
image's first pixel, so the sky colour is sampled from the backdrop itself.

⚠️ **Correction (same day):** an earlier revision called `0x20` a
"320×256 RGB555 loading screen". The geometry was right; the **role was wrong**
— loading screens live in `GFX/*.RAW`. `0x20` is sky/backdrop.

### Complete marker space (loader dispatch fully reconstructed)

| markers | disposition |
|---|---|
| `< 0x20` | texture/VRAM page — `LoadImage(rect, base + 12 + even(u16@+8))` |
| `0x20` | sky/backdrop — RGB555 @ +16 → sky-colour cache 0x800771BC/C0/C4 |
| `0x22` | sprite / animation strip container |
| `0x23` | **memcpy 1,792 B from chunk+4 → fixed table 0x800949B8** (why every 0x23 chunk is 1,796 B) |
| `0x24` | backdrop panorama, header 16 B, data @ +16, via `level_texture_upload` 0x8003CC58 |
| `0x28`–`0x2F` | **pointer-registered**: `TABLE[marker] = chunk base` @ `0x8009C170 + marker*4` |
| `0x30`–`0x57` | **pointer-registered** @ `0x8009B4E8 + marker*4` (40 slots) |
| `0x58`–`0x5F` | **pointer-registered** @ `0x800A6450 + marker*4` |
| `0x101`–`0x104` | mesh definition / payload / collision planes / collision sector-source |

**46 of the 74 previously-unclassified chunks are pointer-registered** — the
loader records where they are and never interprets them, so their formats
belong to whatever consumer reads `TABLE[marker]`. That is why size arithmetic
could not determine their layout.

⚠️ **Correction to a correction:** an earlier revision said "the 74 unknown chunks
are image resources"; the next revision over-corrected that to "true only of
`0x20`" because this loader merely registers 46 of them. Later consumers settle
those 46 as frontend images. Thus 63 are established images and only the 11
marker-`0x26` roles remain open. Dimension-shaped `u16`s alone were never enough;
the later consumer instructions are the missing evidence.

### Overlay region-A calling contract (ABI)

Recorded here because it is the other half of the same loader story. Region A
base **0x800B39A0**; the u32 at base+0 is a **header**, the first function
starts at **base+4**. The contract is **not a vector table**: resident code
holds **hardcoded absolute `jal`s** into the swap buffer (`jal 0x800B39A4` at
0x8003D674/84/94/C4…), dispatched per scene, and **each overlay implements only
the entries its own scene needs** (1–5 each across 19 `LEVEL*.BIN`; every
overlay implements at least one). The committed map's 42 addresses are the
**union across the campaign**, not a per-overlay requirement.

`0x800B39A4` is the common primary entry — implemented by **13 of 19** overlays,
matching the committed map's **13 resident call sites** exactly. Corroborations:
`0x800B4084` lands in `LEVEL08/LEVEL1.BIN`, which is C17's committed
movie-viewer menu reader; and the base matches the one derived independently in
D18. *Limit:* function starts are detected as `addiu sp,sp,-N` or `jr ra` only,
so per-overlay entry lists are lower bounds.

See [[EXP_2026-08-04_phase4_e16_chunk_roles]] and
`analysis/phase4_e16_overlay_abi.json`.
