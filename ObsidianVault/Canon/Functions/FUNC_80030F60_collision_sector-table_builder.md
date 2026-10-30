---
kind: function
id: FUNC_80030F60
aliases: [FUNC_80030F60, 0x80030f60]
address: 0x80030F60
name: collision_sector-table_builder
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
src_paths:
  - src_re/collision_source_converter_80030f60.c
patch_policy: hook_candidate
---

# FUNC_80030F60 - collision sector-table builder

## Purpose

Converts the decompressed LEVEL.RAW chunk-32 source into the runtime collision sector table that the movement integrator queries.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80030F60.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80030F60`
- Name: `collision_sector-table_builder`
- Original note: `ObsidianVault/Functions/FUNC_80030F60.md`
- Source path: `src_re/collision_source_converter_80030f60.c`

## C source excerpt

Source: `src_re/collision_source_converter_80030f60.c`

```c
/* ============================================================================
 * collision_source_converter_80030f60.c — chunk-32 collision SOURCE → runtime
 * tables converter [DECODED 2026-07-05] (for the per-face plane-emitter, M4b)
 * ----------------------------------------------------------------------------
 * Extends collision_plane_resolver_800345cc.c (the resolver) + G29. This decodes
 * FUNC_80030F60 (bounds 0x80030d64..0x800313a4, 1604 B, confidence exact), which
 * runs once per level load to build the runtime collision structures from the
 * decompressed LEVEL.RAW chunk 32. Decoded via live disasm (isolated DuckStation,
 * pristine v1.0, LEVEL01 state) — the authoritative source for the collision-block
 * format the plane-emitter must generate.
 *
 * WHY THIS MATTERS: the visible floor Flik "walks" is the flat per-sector origin-Y
 * (edit_collision_sector.py). Smooth per-face collision needs ORIENTED PLANES
 * (collision_plane_resolver_800345cc.c) generated from the terrain mesh. But planes
 * do NOT live in a simple array — they live inside per-sector collision-mesh BLOCKS,
 * and those blocks + the sector source records are what this converter parses. So
 * the emitter must synthesize these blocks, not just append plane records.
 *
 * SOURCE SECTOR ARRAY (chunk-32-local 0x36570 = runtime 0x800F7BF8, stride 0x4c,
 * 223 records, record i <-> sector i). Fields the converter reads (per sector):
 *   +0x04  s32  block_size   // in s16 UNITS: the running block pointer s0 advances
 *                            //   s0 += src[+0x04]*2 per sector (0x80031070-80)
 *   +0x08  s32  origin.X >>5 // copied to runtime sector +0x00 then <<5 in place
 *   +0x0c  s32  origin.Y >>5 //   (t3/t4/t5 loop: lw; sll v0,v0,5; sw) -> +0x04
 *   +0x10  s32  origin.Z >>5 //   -> +0x08   (origin-Y is the flat-floor lever, G33)
 *   +0x14  s32  ?            // copied raw to runtime sector +0x0c (AABB min? extent?)
 *   +0x1e  s16  idx          // if !=0: table[0x800a207e + idx*2] = sector index (reverse map)
 *   +0x2c  s32  flag         // -> runtime 0x800a7e76 + sector*? (region/flag; +0x2e area)
 *   +0x48  s16  idx2         // if >=0: table[s3 + idx2*2 + 0x68] = sector index (2nd reverse map)
 *
 * RUNTIME SECTOR TABLE (0x800a7e48, stride 0x30) built by the converter:
 *   +0x00/04/08 origin X/Y/Z (<<5)   +0x0c src[+0x14]   +0x10 block ptr (= running s0)
 *   +0x14/1c AABB min   +0x24/28 extent   +0x2c flag     (layout from MEM note, confirmed)
 *
 * PER-SECTOR COLLISION BLOCK (contiguous region walked by s0; runtime +0x10 points at
 * each sector's block; block byte size = src[+0x04]*2). Layout (partially decoded):
 *   - header + VERTEX / POLYGON data (sec 119: ~0x490 B before its first plane record)
 *   - PLANE records (0x20 B each): s16 normal[3] (|n|==0x4000) + s16 ref[3] (sector-local,
 *     <<5 at use) + s16 ext[5] (poly edges/extent, used by point-in-face test 0x80032610 /
 *     FUNC_80038090). LEVEL01 planes: chunk-32 0x1c420,0x1cc30,0x1cc50,0x1cc70 (sec 119),
 *     0x303f8,0x30418 (sec 166). Flat sectors (0,1,2..) SHARE the base block @chunk-32 0x8.
 *   - RELOCATION: a pointer field == 0x12345678 (lui 0x1234/ori 0x5678, 0x80031030-68) is
 *     fixed up in place to a runtime pointer from array s5[a0] — the mechanism that turns
 *     scattered in-block plane/geom pointers into live addresses. The emitter MUST reproduce
 *     any 0x12345678 magic the block format uses, or leave a self-consistent block.
 *
 * RUNTIME PLANE INDEX (rebuilt per FRAME by the candidate-list builder, NOT this converter):
 *   count = *(s32*)(gp+0x57c)  (0 when Flik is away from any plane; ~44 near planes, dup'd)
 *   candidate ptr[i]  = *(u32*)(0x8009c230 + i*4)   -> a plane record in a nearby sector block
 *   candidate sec[i]  = *(s16*)(0x80091718 + i*2)   -> owning sector (for sector-relative p0/p1)
 *   Selection = sector-AABB test around Flik -> gather that sector's block planes into the list.
 *
 * ============================================================================
 * EMITTER IMPLICATIONS (design, M4b)
 * ----------------------------------------------------------------------------
 * To make Flik walk a SMOOTH per-face terrain, generate, per collision sector covering the
 * terrain, a collision block whose planes = the terrain triangles in that sector:
 *   plane.normal = unit(tri normal) * 0x4000 ; plane.ref = a tri vertex (sector-local, >>5) ;
 *   plane.ext    = the tri edge/extent data the point-in-face test needs (FORMAT STILL TODO).
 * Then set src[+0x04] block_size, lay the blocks contiguously, fix relocation magic, recompress
 * chunk 32 (decode/recompress_level_raw), rebuild (build_autolayout_disc).
 *
 * REMAINING DECODE before the emitter can be written:
 *   1. The block HEADER (vertex count / poly count / plane count) — the ~0x490 B before sec 119's
 *      first plane. 2. The ext[5] poly-extent + how point-in-face (0x80032610 / FUNC_80038090)
 *      uses it (so a generated plane is "hit" over the right triangle footprint). 3. Whether the
 *      block requires vertices+polys or planes-alone suffice for the swept floor test.
 *
 * ----------------------------------------------------------------------------
 * BLOCK STRUCTURE — PHASE B decode (2026-07-05, offline parse of sec-119 block @ chunk-32 0x1bf90,
 * size 5956 B; block offset = running sum of src[+0x04]*2 from base 0x8).
 *   - The block is a DENSE oriented-plane collision MESH (sec 119 alone ≈150-185 plane records),
 *     NOT "flat floor + a few planes". The old "6 planes" figure was the PER-FRAME AABB candidate
 *     list (gp+0x57c) near Flik in one pose — the full block holds the whole sector's slope mesh.
 *   - Plane record CONFIRMED 0x20 B (16×s16): normal[3] (|n|=0x4000) + ref[3] (sector-local point)
 *     + ext[10]. (The resolver-note ext[5] was a partial read; stride between consecutive planes
 *     0xca0→0xcc0→0xce0 is exactly 0x20.) The records CROSS-REFERENCE each other — consecutive
 *     planes share ref values and a plane's ext contains its neighbours' ref coords (e.g. planes
 *     0xca0 & 0xce0 share ref (1750,-1268,-1880); 0xca0.ext holds 1750,477 which is 0xce0.ref/ext).
 *     => this is an INDEXED mesh (shared verts/edges), not independent planes.
 *   - The block is NOT a flat [marker][count]+records array: a [0x0001][count] walk from blk+0 fails
 *     immediately, and known plane offsets 0x490 vs 0xca0 are 0x810 apart = 64.5 records (HALF-record
 *     off) → plane runs sit at DIFFERENT alignments separated by header/interleaved data. Header at
 *     blk+0x0: [0001][0001][-1448][234][-2708][485] (6×s16) before the first normal at blk+0xc.
 *   RESOLVER (decoded, collision_plane_resolver_800345cc.c): swept segment test vs the AABB-selected
 *   candidate planes; ref used <<5; dist = (n·(p-ref<<5))>>14. Committer FUNC_8003633C.
 *
 * EMITTER FEASIBILITY (honest, Phase B): synthesizing a VALID block for arbitrary Blender terrain
 * requires decoding (a) the indexed-mesh layout + per-run headers, (b) how planes are AABB-selected
 * into candidate arrays 0x8009c230 / 0x80091718 so a new plane is actually tested near Flik, (c) the
 * ext[10] region/edge semantics, (d) the 0x12345678 relocation. This is a large, high-risk build.
 * COUNTERWEIGHT: the per-sector-FLAT floor (edit_collision_sector origin-Y, matched to the visual via
 * native_terrain_export --displace + native_collision_from_heightfield with the delta/32 FRAME FIX)
 * was validated in-game (2026-07-05) to walk GENTLE native-density Blender terrain smoothly — the
 * stated goal. Falls occur only on LEVEL01's ORIGINAL steep valleys (plane-resolved), which a new
 * gentle Blender level would not have. So the plane-emitter is a steep-terrain enhancement, not a
 * blocker to authoring gentle custom levels. See [[tier3-native-terrain-pivot]] Phase A.
 *
 * COMPLEXITY / PRAGMATIC NOTE: this is a full collision-mesh block format, NOT a flat plane list —
 * a substantial emitter. For GENTLE native-density terrain (subtle bumps) the per-sector-flat floor
 * (edit_collision_sector origin-Y, matched via native_terrain_export --displace) is ADEQUATE (223
 * sectors = fine granularity, small walkable steps); the traversal "stepping/stuck" was from a STEEP
 * authored dome/ridge. Reserve the full plane-emitter for genuinely steep slopes/walls, or add a few
 * oriented planes to existing slots via edit_collision_plane rather than synthesizing whole blocks.
 * ============================================================================
 *
 * ============================================================================
 * *** FULLY DECODED FORMAT (2026-07-06, live disasm of the candidate-builder FUNC_80037320
 * + the floor resolver FUNC_80038090; offline parse CONFIRMED: sec-119 block = 16 groups /
 * 180 planes, parse lands EXACTLY at block end, all 180 |normal|=0x4000, all known planes on
 * record boundaries). This SUPERSEDES the "indexed-mesh / not-a-[marker][count]-array" note above,
 * which was wrong: the earlier walk failed only because it skipped the 8-byte group AABB. ***
 *
 * PER-SECTOR COLLISION BLOCK  (bytes come straight from chunk 32; runtime sector +0x10 -> block):
 *   BLOCK = a sequence of GROUPS, terminated when a group's marker s16 < 0 (bgez check @0x80037628
 *           / lh v0,0x2(t2) sign @0x80038140). GROUP:
 *     +0x00 s16 marker      // >=0 to be a valid group (LEVEL01 uses 1)
 *     +0x02 s16 count       // # plane records in this group
 *     +0x04 s16 aabb.minX   // group broad-phase AABB, sector-local FILE frame (>>5)
 *     +0x06 s16 aabb.extX
 *     +0x08 s16 aabb.minZ
 *     +0x0a s16 aabb.extZ
 *     +0x0c .. : count * 0x20-byte PLANE(=triangle/quad) records
 *   group byte size = 12 + count*0x20 ; groups laid contiguously.
 *
 * PLANE RECORD (0x20 B, 16*s16). Field use decoded from FUNC_80038090 (floor path, normal.y<0):
 *   +0x00 s16 normal.x   |   +0x02 s16 normal.y  (SIGN selects: <0 = floor/up-facing, >=0 = wall)
 *   +0x04 s16 normal.z   |   |normal| == 0x4000 (dist math >>14; -Y is up so a floor has normal.y<0)
 *   +0x06 s16 V0.x (=ref.x)  +0x08 s16 V0.y (=ref.y)  +0x0a s16 V0.z (=ref.z)   // sector-local, <<5 at use
 *   +0x0c s16 dV1.x   +0x0e s16 dV2.x        // other polygon verts as XZ DELTAS from V0:
 *   +0x10 s16 dV1.z   +0x12 s16 dV2.z        //   V1=(V0.x+dV1.x, V0.z+dV1.z), V2=(V0.x+dV2.x,..)
 *   +0x14 s16 dV3.x   +0x16 s16 dV3.z        // (4th vert -> quad; triangle leaves these degenerate)
 *   +0x18 s16 fp.minX  +0x1a s16 fp.extX     // per-record FOOTPRINT AABB (fine candidate select,
 *   +0x1c s16 ?(pad/hi) +0x1e s8 fp.minZhi   //   builder @0x8003758c): X = [fp.minX .. +fp.extX];
 *   +0x1f s8 fp.extZ                         //   Z min = V0.z + fp.minZhi*64, Z ext = fp.extZ*64
 *   FLOOR Y at Flik's XZ = solve normal·(P - V0<<5)=0 for P.y (the swept/height eval). The point-in-
 *   polygon test (FUNC_80038090 @0x800381a8+) uses V0 + the dV edges (exact edge-cross + div).
 *
 * CANDIDATE-LIST BUILDER (FUNC_80037320, per frame; args = Flik AABB box):
 *   1. BROAD grid: iterate gp+0x6c0 cells of a spatial grid @0x800b2540 (stride 0x14: +0x00 s16
 *      first_slot, +0x02 s16 count, +0x04 s32 minX, +0x08 s32 minZ, +0x0c s32 extX, +0x10 s32 extZ).
 *      Cells whose AABB overlaps Flik(+-4096) -> copy their s16 SECTOR indices (table @0x800a2388,
 *      first_slot*2) into scratchpad 0x1f800000.
 *   2. Per gathered SECTOR: runtime-sector AABB refine (0x800a7e48 +0x14/+0x24 min, +0x1c/+0x28 ext),
 *      flag 0<+0x2c<100; then walk that sector's BLOCK groups (group AABB @0x80037548, then per-record
 *      footprint @0x8003758c). Each surviving record ptr -> candidate array 0x8009c230[k]; its sector
 *      -> 0x80091718[k]; count -> gp+0x57c. Finally calls FUNC_80038090(Flik) to resolve the floor.
 *
 * EMITTER RECIPE (now unblocked): per collision sector covering the terrain, emit ONE group (or a few)
 * whose records = the sector's terrain quads: normal = unit face normal *0x4000 (normal.y<0); V0 = a
 * corner (sector-local >>5); dV1/dV2/dV3 = other corners - V0 (XZ >>5); footprint = the quad's XZ AABB
 * (>>5, Z packed as *64); group AABB = union of footprints. Set src sector +0x04 block_size (=block
 * bytes/2), lay blocks contiguously, handle relocation + the spatial grid (converter FUNC_80030F60,
 * decode next), recompress chunk 32, rebuild. Tool: tools/native_collision_mesh_codec.py (planned).
 *
 * ----------------------------------------------------------------------------
 * B4 — LOAD PIPELINE + RESIZE (2026-07-06, converter FUNC_80030F60 @0x80030d64 + its parent
 * @0x80031498 which calls it then builds broad-phase). Key facts for the emitter:
 *   - BROAD-PHASE IS AUTO-DERIVED AT LOAD: the parent scans every block's records and computes the
 *     spatial grid (0x800b2540), sector AABBs (0x800a7e48 +0x14/+0x24), and global Y-bounds (gp+0x51c)
 *     from the record FOOTPRINTS (rec+0x18/+0x1a X, rec+0x0a/+0x1e/+0x1f Z). => the emitter does NOT
 *     author the grid; correct block footprints are sufficient.
 *   - RELOCATION (0x12345678) appears ONLY in a special region near the block-region end (chunk-32
 *     0x35830..0x364fc, 11 hits), NOT in normal sector blocks (sec 119 @0x1bf90 has none). => an
 *     emitted normal block needs no relocation; leave that region intact.
 *   - BLOCK ptr = implicit RUNNING SUM: converter walks s0 += src[+0x04]*2 per sector; block bytes are
 *     laid contiguously in SECTOR ORDER from chunk-32 0x8. Flat sectors have block_size 0 (share the
 *     running position). Terminator = a group header with marker s16 < 0 at block+block_size*2-... .
 *   - CHUNK 32 IS LENGTH-PREFIXED SUB-ARRAYS: the converter reads via a cursor (s0), each sub-array
 *     = [u32 count_s16][count_s16*2 bytes]; sector array offset (0x36570 in pristine) is thus DERIVED,
 *     not fixed. RESIZING the block region requires updating that length prefix + shifting the sector
 *     array — the one remaining piece for ADD-BLOCK (a currently-flat sector). SIZE-PRESERVING block
 *     edits (re-height an existing block's planes, keeping counts/footprints) need NONE of this and are
 *     the safe first emitter step.
 *   - FRAME: ref/footprint are file frame (<<5 at use); a floor-Y change of N runtime units = ref.y
 *     delta of N/32 (same >>5 gotcha as native_collision_from_heightfield).
 *
 * ----------------------------------------------------------------------------
 * SEMANTICS — WHAT THE FLOOR PLANES ACTUALLY DO (2026-07-06, IN-GAME PROVEN via
 * tools/emit_collision_reheight.py, a SIZE-PRESERVING re-height of a block's plane records; edit
```

Note: source excerpt truncated; 684 additional lines remain in `src_re/collision_source_converter_80030f60.c`.

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80030F60.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80030F60.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80030F60.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
