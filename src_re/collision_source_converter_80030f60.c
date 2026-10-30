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
 *     +0x0c .. : count * 0x20-byte PLANE(=triangle) records
 *   group byte size = 12 + count*0x20 ; groups laid contiguously.
 *
 * PLANE RECORD (0x20 B, 16*s16). Player floor use decoded from FUNC_80032610 (normal.y<0):
 *   +0x00 s16 normal.x   |   +0x02 s16 normal.y  (SIGN selects: <0 = floor/up-facing, >=0 = wall)
 *   +0x04 s16 normal.z   |   |normal| == 0x4000 (dist math >>14; -Y is up so a floor has normal.y<0)
 *   +0x06 s16 V0.x (=ref.x)  +0x08 s16 V0.y (=ref.y)  +0x0a s16 V0.z (=ref.z)   // sector-local, <<5 at use
 *   +0x0c s16 edge1.x +0x0e s16 edge1.y +0x10 s16 edge1.z // V1 = V0 + edge1
 *   +0x12 s16 edge2.x +0x14 s16 edge2.y +0x16 s16 edge2.z // V2 = V0 + edge2
 *   +0x18 s16 fp.minX  +0x1a s16 fp.extX     // per-record FOOTPRINT AABB (fine candidate select,
 *   +0x1c s8 fp.minYhi +0x1d u8 fp.extY      // player builder: Y min=V0.y+minYhi*64, extent=extY*64
 *   +0x1e s8 fp.minZhi +0x1f s8 fp.extZ      // Z min=V0.z+minZhi*64, extent=extZ*64
 *   FLOOR Y at Flik's XZ = solve normal·(P - V0<<5)=0 for P.y (the swept/height eval). The point-in-
 *   polygon test (FUNC_80032610) consumes the two complete XYZ edge vectors literally.
 *
 * PLAYER CANDIDATE-LIST BUILDER (inside FUNC_8003633C, per frame):
 *   1. BROAD grid: iterate gp+0x6c0 cells of a spatial grid @0x800b2540 (stride 0x14: +0x00 s16
 *      first_slot, +0x02 s16 count, +0x04 s32 minX, +0x08 s32 minZ, +0x0c s32 extX, +0x10 s32 extZ).
 *      Cells whose AABB overlaps Flik(+-4096) -> copy their s16 SECTOR indices (table @0x800a2388,
 *      first_slot*2) into scratchpad 0x1f800000.
 *   2. Per gathered SECTOR: runtime-sector AABB refine (0x800a7e48 +0x14/+0x24 min, +0x1c/+0x28 ext),
 *      flag 0<+0x2c<100; then walk that sector's BLOCK groups (group AABB @0x80037548, then per-record
 *      XYZ footprint @0x80036864). Each surviving record ptr -> candidate array 0x8009c230[k]; its sector
 *      -> 0x80091718[k]; count -> gp+0x57c. The ordinary swept resolver FUNC_80035280 then calls
 *      FUNC_80032610. FUNC_80037320 is the separate entity/projectile candidate path.
 *
 * EMITTER RECIPE (now unblocked): per collision sector covering the terrain, emit ONE group (or a few)
 * whose records = the sector's terrain triangles: normal = unit face normal *0x4000 (normal.y<0); V0 = a
 * corner (sector-local >>5); edge1/edge2 = the other corners - V0 (full XYZ); footprint = the triangle's XZ AABB
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
 * confirmed live in RAM = pristine ref.y − raise/32 exactly). Findings from raising sec 107/108's
 * floor planes and walking Flik LEVEL01 spawn->valley:
 *   - Flik's WALKING floor is a HYBRID: the per-sector FLAT origin-Y (edit_collision_sector) is the
 *     default; a floor PLANE (normal.y<0) OVERRIDES it ONLY where Flik's XZ is INSIDE that plane's
 *     triangle footprint (the FUNC_80038090 point-in-polygon test). Where no floor-triangle contains
 *     him, the flat origin-Y applies.
 *   - PROOF: raising 107/108 planes left Flik's Y UNCHANGED on the flat high ground near spawn (he was
 *     not inside their triangles there -> flat floor won), but in the VALLEY (where the same planes tile
 *     the steep descent and DO contain him) a +5000 raise stopped his descent (Y −2016 vs pristine
 *     −19135) — the plane floor rose under him. => floor planes = the SUB-SECTOR SLOPE floor.
 *   - CONSEQUENCE FOR THE EMITTER (validated approach): to make Flik walk a smooth STEEP slope, TILE the
 *     terrain area with floor-triangle records (no XZ gaps, so he is always inside one) whose planes
 *     follow the Blender surface. The per-sector-flat origin-Y remains the base for gentle/flat ground
 *     (native_collision_from_heightfield); planes add the steep detail flat sectors can't. Uniform
 *     re-heights create a raised "island" with an edge Flik walks off (fall) — a real emitter must match
 *     the surface continuously + blend with the flat neighbours.
 *   - emit_collision_reheight.py (DONE, size-preserving): re-heights an existing block's planes to a
 *     raise or a heightfield — the safe lever where a block already exists (126 LEVEL01 sectors). Adding
 *     planes to a currently-FLAT sector still needs the chunk-32 length-prefix resize (B4, remaining).
 *
 * ----------------------------------------------------------------------------
 * C2 — ADD A BLOCK TO A FLAT SECTOR (resize). Progress 2026-07-06 (tools/emit_collision_addblock.py):
 *   RESIZE MECHANISM — VALIDATED IN-GAME (cold boot). To grow the block region: insert the block bytes at
 *   the sector's running-sum position, bump the length prefix at chunk-32 +0x04 (+block_s16), and append
 *   the (relocated) sector array. The array's chunk-32 portion is 189 sectors; sectors 189..222 (all flat)
 *   live in chunk 33, which the loader places CONTIGUOUSLY after the (now larger) chunk 32 — CONFIRMED: a
 *   disc with chunk 32 grown +372 B (a copied block added to a flat sector) COLD-BOOTS cleanly, Flik spawns
 *   + walks the pristine path (the level base pointer @0x80082498 just shifts by +372). So the loader does
 *   NOT use fixed per-chunk addresses; resizing chunk 32 is safe.
 *   BLOCK OWNERSHIP — DECODED + VERIFIED. `block_size` (+0x04) alone does NOT make a sector own a block;
 *   the marker is src sector **+0x4a**: the converter does `bne [+0x4a],1,block-path` (0x80030e9c) — so
 *   +0x4a==1 => flat (descriptor-copy path, its runtime entry is copied via the +0x48 reverse-map index);
 *   +0x4a==0 => BLOCK sector (its block is processed, cursor advances, runtime +0x10 = block ptr). Setting
 *   a flat sector's +0x4a=0 + block_size + inserting the block makes it OWN the block: VERIFIED live — the
 *   runtime sector +0x10 then points at the inserted block and its X-AABB is computed correctly from the
 *   record footprint (grid-builder @0x80031498 scans footprints -> sector AABB @0x800a7e48 +0x14/+0x24).
 *   FOOTPRINT ENCODING — DECODED (2026-07-06). Per-record footprint (rec+0x18..0x1f):
 *     X: rec+0x18 s16 minX, rec+0x1a s16 extX  (candidate fine test @0x8003758c: Flik.x_local - minX <u
 *        extX + 256). CORRECT in the codec as-is.
 *     Z: rec+0x1e s8, rec+0x1f s8. FINE test (candidate builder, the one that gates selection): minZ =
 *        V0.z + rec[0x1e]*64 ; extZ = rec[0x1f]*64. GRID-builder (@0x800314xx, coarse sector AABB into
 *        0x800a7e48 +0x14/+0x24) uses the SAME minZ but maxZ = V0.z + rec[0x1e]*64 + rec[0x1f]*4096 (an
 *        over-inflated coarse bound). native_collision_mesh_codec Plane.from_fields reproduces rec+0x1e/0x1f
 *        BYTE-EXACT vs real records. Player selection additionally reads rec+0x1c/+0x1d as a packed
 *        Y minimum delta/extent; only the separate entity/projectile selector omits that Y gate.
 *     => the footprint-Z "blocker" is RESOLVED. KEY practical constraint: real records use SMALL footprints
 *        (rec+0x1f ~6-19, extZ ~400-1200 file); a block TILES its area with MANY small triangles. A single
 *        oversized quad (rec+0x1f ~78) inflates the grid AABB ~10x and breaks grid-cell assignment.
 *   With realistic tiled footprints covering the sector ORIGIN, a from-scratch flat-sector block IS
 *   broad-phase SELECTED (verified live: sec 77 appears in 0x80091718; its candidate record @0x8009c230
 *   has the correct normal/ref).
 *   ALSO decoded while validating: (a) real FLOOR triangles are wound CLOCKWISE ((V1-V0)x(V2-V0) < 0) and
 *   TILTED (normal ~ terrain face, e.g. (288,-15546,5161)), not axis-aligned/vertical; the point-in-polygon
 *   floor test (FUNC_80038090) needs the right winding. (b) SIGN: -Y is UP (spawn Y +2734; walking up the
 *   slope -> Y more negative; free-fall -> Y increases). A floor plane catches a falling Flik only when it
 *   is ABOVE him (more negative Y).
 * ----------------------------------------------------------------------------
 * GRID-CELL BUILDER — DECODED (2026-07-07, FUNC @0x800313a8..0x8003229c, called by the parent that also
 * calls the converter). This is the broad-phase the candidate builder (FUNC_80037320) reads. Three stages:
 *   1. PER-SECTOR AABB (loop to 700, gate runtime +0x0c==6/7/8): write each sector's WORLD AABB to the
 *      runtime table 0x800a7e48 — minX@+0x14, minZ@+0x1c, extX@+0x24, extZ@+0x28 = origin + footprint
 *      bounds<<5 (X from rec+0x18/0x1a; Z min = V0.z+rec[0x1e]*64, Z max += rec[0x1f]*4096 -> Z is
 *      OVER-INFLATED, normal). gp+0x508 counts these sectors (LEVEL01 N=223).
 *   2. OVERALL BOUNDS: 2nd pass tracks min/max X/Z over all sector AABBs (gate runtime +0x2c==6/7/8).
 *   3. GRID DIMS + CELL FILL: step = isqrt((Xspan/N)*(Zspan/N)) * isqrt(N*10) ≈ sqrt(Xspan*Zspan*10/N)
 *      (0x80031870/88 call isqrt @0x80060154); gridW=ceil(Xspan/step), gridH=ceil(Zspan/step). LEVEL01:
 *      step≈209500, ~20 POPULATED cells. Each CELL entry @0x800b2540 (stride 0x14): +0x00 s16 first_slot,
 *      +0x02 s16 count, +0x04 s32 minX, +0x08 s32 minZ, +0x0c s32 extX, +0x10 s32 extZ. Sectors are binned
 *      to a regular grid cell by position; a cell's AABB = UNION of its member sectors; member sector
 *      indices go in the table @0x800a2388 (cell.first_slot..). (Verified live: 20 cells, sizes/lists read.)
 *   CANDIDATE BUILDER (FUNC_80037320) then: PHASE 1 — for each cell whose AABB contains Flik(±4096 vs
 *   +8192 slack), copy its sector indices to scratchpad 0x1f800000. PHASE 2 — iterate gathered sectors:
 *   per-sector AABB gate @0x800374ac ((Flik.x+4096-minX) <u (extX+8192), same for Z @0x800374c8) + flag
 *   @0x800374e4 (+0x2c !=0 && <100); survivors read their block (+0x10) and run the per-record footprint
 *   fine test, appending hits to 0x8009c230 / 0x80091718, count gp+0x57c.
 *
 * P22 GRID/LIST BUILDER PROVENANCE (2026-07-06). In the failing Track-B replacement interaction
 * P17 seed+[0,73,92], the render/cull crash is now traced back to this grid/list-builder family, not
 * to the render dispatch itself and not to FUNC_80035280 rejecting a collision plane. The bad render
 * source slot 0x801c362c is valid (0x80175b84) at movie frame 4282, then becomes 0xfffabfa0 at frame
 * 4283. A focused store trace captures:
 *
 *     0x80031a64  sw v0,0(a2)   with a2=0x801c362c, v0=0xfffabfa0, ra=0x80031890
 *
 * The same writer pass also uses 0x800319a0 `sw s7,0(t9)` to initialise parallel words around
 * 0x801c3614..0x801c3688. Register context at the bad store has t4=0x800a9d98, which is runtime
 * sector-table entry 167 (0x800a7e48 + 167*0x30), so the value being stored is grid/sector bounds
 * data, not a native render payload pointer. The P21 render/cull dispatch later consumes the same
 * address as [s0+0x18] for dispatch key 65 and faults at 0x8001eb3c.
 *
 * Replacement correlation: adding sector 92 to seed+[0,73] grows decompressed chunk 32 by 6324 bytes
 * and shifts later block data; sector 92 changes from a 1884-byte retained flattened block to an
 * 8208-byte authored replacement block. P23 should inspect the destination-base/limit math of this
 * grid/list builder before broad replacement resumes. Evidence:
 * docs/G3_NATIVE_P22_RENDER_NODE_BUILDER_PROVENANCE.md,
 * build/g3_native_p22_builder_provenance_report.json.
 *
 * ============================================================================
 * *** C2 BREAKTHROUGH (2026-07-08) — the multi-day "not selected" struggle was READING THE WRONG LIST. ***
 * FUNC_80037320 (the candidate builder with the 0x800374ac per-sector gate) is the ENEMY/entity collision
 * builder — it has 8 callers, ALL enemy-AI / projectile (0x8004ce80, 0x8004cf94, ...), and it is invoked with
 * ENTITY positions, NEVER Flik's (single-step @0x800374ac showed arg = enemy XZ, not Flik XZ). The shared
 * candidate arrays (gp+0x57c / 0x8009c230 / 0x80091718) are OVERWRITTEN per entity, so every earlier read of
 * "the candidate list" was some enemy's, not Flik's.
 * THE PLAYER FLOOR is FUNC_8003633C (0x8003633c..0x8003731c, exact) — self-contained: it resets gp+0x57c
 * (@0x800363b4), builds its OWN candidate list with FLIK's position, resolves, and writes Flik.Y (writers
 * @0x80036384/0x80036cf0/0x80036d58, found by an accessLog write-watch on 0x800a6504). Breaking @0x800368d8
 * (right after the player builds its list) and reading gp+0x57c/0x80091718 while Flik walks over the tile:
 * **sec 77 IS in Flik's candidate list** (e.g. secs = [44,44,44,77,100,100,...]). So resize + ownership +0x4a=0
 * + footprint + grid membership ALL work end-to-end for the PLAYER — the from-scratch block IS selected.
 * *** C2 COMPLETE — SYNTHESIZED BLOCK CATCHES FLIK, VALIDATED IN-GAME (2026-07-09). ***
 * THE PLAYER SWEPT RESOLVER is FUNC @0x80035280 (0x80035280..0x80035f20, exact) — NOT 0x800345cc (that is a
 * collision dispatcher). Found by an accessLog READ-watch on the synthesized plane record: the reader is
 * 0x80035408 (inside 0x80035280). It iterates the PLAYER candidate list (sector 0x80091718[i], plane ptr
 * s0=0x8009c230[i]), makes Flik's segment endpoints sector-relative, and for each plane:
 *     normal = s0+0x0/+0x2/+0x4 ; ref = s0+0x6/+0x8/+0xa (each <<5 at use).
 *     d1 = (normal . (p1 - ref<<5)) >> 14   (@0x80035460)  ; if d1 >= 0 -> SKIP (bgez, @0x80035464)
 *     d0 = (normal . (p0 - ref<<5)) >> 14   (@0x800354b0)  ; if d0 <  0 -> SKIP (bltz, @0x800354b4)
 *     CROSSING iff d0>=0 AND d1<0 (segment goes from the +normal side to the -normal side); span s1=d0-d1,
 *     contact interpolated and committed to Flik (FUNC_8003633C writes Flik.Y @0x80036cf0/d58).
 * So a FLOOR = normal points UP (-Y): p0 above (d0>=0) -> p1 below (d1<0) = Flik crossing DOWN onto the floor.
 *
 * *** THERE IS NO PLANE-RECORD DISCRIMINATOR *** — the synthesized record's normal/ref/footprint are read and
 * processed by the resolver EXACTLY like a real one. The emitter needs NO patch. Proof: with normal (0,-0x4000,0)
 * (up) + CW winding, teleport Flik ABOVE the tile (plane Y=-4992, ~7800 above the flat floor) and let him fall —
 * he is CAUGHT at Y=-5251 (= plane -4992 + Flik's ~256 stand height) and stays there STABLE for 32+ frames,
 * floating in mid-air ~7800 above the ground on the from-scratch block, then walks off the tile edge. Screenshot:
 * Flik standing elevated. Disc build/collision_sec77j.RAW / ABL_addblock_test.
 *
 * WHY THE MULTI-DAY STRUGGLE (all now understood, none were emitter bugs):
 *   1) The candidate list I kept reading (gp+0x57c / 0x8009c230 / 0x80091718) is the ENEMY builder's
 *      (FUNC_80037320, 8 enemy-AI callers) — overwritten per entity. The PLAYER floor is FUNC_8003633C which
 *      builds its OWN list; sec 77 IS in it (secs=[44,44,44,77,100,...]).
 *   2) PHYSICS: a floor plane only acts when Flik's MOTION CROSSES it from the +normal side; it does NOT lift a
 *      standing/walking Flik onto a higher plane, and a plane below the flat floor is ignored. He must FALL or
 *      DESCEND onto it (which is why the valley reheight of real slopes worked, and a flat spawn-area plane
 *      showed nothing during a level walk). The flat per-sector origin-Y is the default surface; planes add the
 *      slopes/steps that moving Flik crosses.
 *   3) One earlier drop used normal +Y (down) -> free-fall; and "confirming" reads used the enemy list.
 *
 * PLANE FLOOR FRAME (2026-07-10, proven by two catch tests): the swept resolver's floor Y = ref.y<<5 (ABSOLUTE
 * file frame) — it does NOT add the sector origin.y for the Y component (it DOES subtract origin XZ for the
 * footprint/point-in-poly). Proof: platform ref.y=-188 -> Flik caught at ~-6016=-188<<5 (not -3328+-6016); after
 * setting ref.y=(target>>5) directly, Flik caught at the target. So a heightfield->collision mesh sets each
 * vertex Y = surface_runtime>>5 (absolute), X/Z = world-origin (sector-local). tools/heightfield_collision.py
 * (quad_record/mesh_block) does this. NOTE the per-sector FLAT floor (origin-Y, edit_collision_sector) IS the
 * origin.y<<5 mechanism — different from planes; both are used (flat floor = walk base, planes = cross/fall).
 *
 * FULL C2 PIPELINE (all proven): resize chunk-32 (grow block region, bump length prefix @+0x04, relocate array;
 * cold-boots) + block ownership (src sector +0x4a=0) + footprint encoding (rec+0x18/1a X, rec+0x1e/1f Z; small
 * tiled footprints) + CW-wound floor tris (normal (0,-0x4000,0)) + grid membership (player selects it) + the
 * swept resolver catches Flik. tools/emit_collision_addblock.py + native_collision_mesh_codec are CORRECT AS-IS.
 * To make Flik WALK a from-scratch slope (not just land on a flat plane), author the tiles as a ramp/steps his
 * path descends across, exactly like a real slope block.
 * ============================================================================
 *
 * C2-POLISH (2026-07-05, pipeline hardening — no new RE, reconciles the frame + a harness pitfall):
 *   - TELEPORT-CATCH IS NOT A RELIABLE AUTO-TEST. Poking Flik's Y to drop him onto an add-block plane is flaky:
 *     the physics can snap him to the pristine floor in one frame, and (operator-confirmed) if the resolved
 *     plane floor sits UNDERNEATH where he lands he falls straight through — the swept test only fires when his
 *     motion CROSSES the plane from the +normal side. The frame is NOT the bug: the catch is real (two C2 tests,
 *     floor = ref.y<<5 ABSOLUTE, unchanged), it is the TELEPORT that is fragile. So the regression harness
 *     (tools/test_terrain_pipeline.py) validates the add-block via a RELIABLE proxy instead: the platform block
 *     is SELECTED as a live PLAYER candidate (FUNC_8003633C list, gp+0x57c / 0x80091718) when Flik's XZ is over
 *     it — broad-phase is XZ-only, so it is robust to (and needs no) Y drop. That proves the whole chain (resize
 *     + ownership +0x4a=0 + footprint + grid membership); the final swept catch stays C2-proven above.
 *   - REHEIGHT SIGN UNIFIED (emit_collision_reheight.py): ref.y += delta/32, SAME direction as the flat floor's
 *     origin-Y += delta/32 and the visual displace v.y += delta (plane floor = ref.y<<5 absolute, so +delta/32
 *     moves it +delta). --raise-runtime passes -R so a positive R raises (–Y up). (Was -delta/32, opposite the
 *     origin-Y shift, risking a double-shift.)
 *   - --all-blocks DECODE GUARD (native_collision_mesh_codec.decode_block): raises ValueError when a group
 *     overruns its block, so the chunk-32 RELOCATION region (0x12345678 magic @0x35830+, sectors 178-188) is not
 *     mis-parsed into short records; the reheight driver skips those sectors instead of corrupting them.
 * ============================================================================
 *
 * NEW-LEVEL POC + ADD-BLOCK CATCH BLOCKER (2026-07-05, tools/build_poc_newlevel.py):
 *
 * FRAME MODEL (calibrated in-game, decisive): render_runtime = node_world << 5 (UNIFORM x32 for XYZ). Proven by
 * replacing the spawn payload with a flat mesh at node-Y=93 -> it renders exactly at Flik's feet (~2976 = 93<<5,
 * Flik spawn center 2734). So a native floor payload frame = Flik/runtime frame >> 5, same as the collision STORED
 * frame. Consequence: a VISUAL vertex Y and its MATCHING collision plane ref.y are BOTH (runtime_Y >> 5) — author
 * both from one surface in the runtime>>5 ("file") frame and they align (validated: Flik stands on the visible
 * authored floor). Spawn facts: Flik (197091,2734,492897); node/file XZ = raw>>5 = (6159,15403); covering payload
 * 0x1b9f0; spawn stands on collision sectors 100 (BLOCK) + 77 (flat).
 *
 * WHAT WORKS: overwrite the OG sectors' collision HEIGHTS with an authored surface, keeping their catching plane
 * STRUCTURES (flat: origin-Y = surf>>5; BLOCK: each plane -> normal (0,-0x4000,0) + ref.y = surf>>5). Flik then
 * rests + walks on the authored surface at the AUTHORED height (POC: platform A Y~4064, NOT the OG 2734) — proving
 * authored collision (not OG) carries him.
 *
 * ADD-BLOCK CATCH IS BROKEN (supersedes the "C2 COMPLETE — catches Flik" claim above, now believed a
 * teleport-artifact): a from-scratch block added to a flat sector (emit_collision_addblock + mesh_block) IS
 * SELECTED into the PLAYER candidate list (0x80091718 shows sector 77) but the swept resolver does NOT catch a
 * NATURALLY-falling Flik — he passes straight through (POC: fell from spawn 2734 through the add-block platform at
 * 4500 down to the dropped-OG floor at 202993). By contrast, REHEIGHTED ORIGINAL block-sector planes DO catch. So
 * the discriminator is between a sector that was a BLOCK from disc-load vs a FLAT sector CONVERTED at author-time.
 * NOT the fix: +0x4a=0 (add_block sets it) and +0x48=-1 (every original block sector has +0x48==-1, flats have
 * 0/1; setting it changed nothing). The remaining difference is a LOAD-TIME runtime-structure build (Y-bounds /
 * plane list / reverse-map) that the loader does for original block sectors but not for a converted one.
 * IMPORTANT METHOD NOTE: writing Flik's position words (0x800a6500/04/08) FREEZES him (zeroes velocity) — teleport
 * "catch" tests are invalid; only a NATURAL fall (cold-boot spawn drop, or walking) tests the resolver.
 * NEXT to unblock arbitrary new-level collision: set an execute breakpoint in the player floor resolver
 * FUNC@0x80035280 with Flik falling onto an add-block plane, and compare the per-plane branch inputs / runtime
 * sector fields against an original block sector that catches. Until then, authored collision is limited to
 * OVERWRITING existing plane structures -> it only covers OG-walkable XZ (an authored footprint extending past the
 * OG floor has COVERAGE GAPS; the POC ramp-traverse plunges at the first gap).
 * ============================================================================
 *
 * ADD-BLOCK CATCH — RESOLVER SINGLE-STEP (2026-07-05, FUNC@0x80035280 disassembled + live-traced, no teleport):
 *
 * ROOT CAUSE #1 (PROVEN + FIXED): the swept resolver's plane-floor formula ADDS the runtime sector origin.
 *   Disasm: the crossing dot uses (Flik.pos - 0x800a7e48[sector].origin) MINUS (ref<<5), i.e. for a floor normal
 *   (0,-0x4000,0):  d = (ref.y<<5 + origin.y<<5) - Flik.y ;  it SKIPS the plane unless Flik crosses that floor.
 *   So plane_floor_runtime = ref.y<<5 + origin.y<<5, NOT the "ref.y<<5 absolute" claimed before (that was wrong —
 *   it came from teleport-freeze artifacts). Live-measured on the add-block disc: sector 77 origin.y=-3328, my
 *   plane ref.y was 140 -> effective floor 140<<5 + (-3328) = 1152 (ABOVE Flik's spawn 2734) -> he starts below it
 *   -> never crosses down -> falls through. FIX (heightfield_collision.mesh_block + build_poc_newlevel block
 *   overwrite): ref.y = surf>>5 - origin_file.y. Verified: block planes now CATCH (POC Flik rests on a block plane
 *   at an authored height instead of only the flat sector). This ALSO explains the POC "coverage gaps": the block
 *   planes were at ref.y<<5 (no origin) = wildly wrong floors (sector 100: 140<<5-50368 = -45888) -> never caught,
 *   so only flat sectors held Flik.
 *
 * FINDING #2 (the resolver runs in a PHYSICS position frame, NOT the render pos 0x800a6504). The resolver's a1/s5
 *   arg points at a STACK buffer (~0x801ffe30) holding Flik's PHYSICS position; a0/s3 is the per-frame movement
 *   DELTA. Back-calculated from d1 = floor - p1.y: during a jump the physics Flik.y led the RENDER Flik.y by a
 *   large, NON-constant amount (physics -64 vs render 1792 mid-fall; converge at rest). So (a) writing 0x800a6504
 *   only moves the RENDER pos and the physics sim snaps it back -> teleport catch-tests are invalid (confirms the
 *   operator's warning), and (b) collision authored to match RENDER heights is mis-placed in the PHYSICS frame,
 *   so during motion OG planes (higher in the physics frame) can catch Flik before he reaches an add-block plane.
 *
 * RESIDUAL (not yet closed): even with the correct floor + OG neutralized (ab_test: OG dropped, add-block floor
 *   4480, Flik spawn 2734), a from-scratch add-block did NOT catch the fast boot-fall (Flik reached the dropped-OG
 *   floor). Candidate selection works (sector 77 evaluated 154x/jump), the plane record is read correctly, and the
 *   floor is now correct — so the remaining suspects are (i) the PHYSICS-frame offset above (calibrate physics vs
 *   render before setting ref.y), and (ii) fast-fall TUNNELING vs the plane's point-in-poly footprint. NEXT:
 *   author a controllable ISOLATED fall (drop OG below an add-block, Flik JUMPs down onto it — repeatable, no
 *   teleport) and single-step d0(s2 @0x800354b4)/d1(s4 @0x80035464)/point-in-poly for sector 77 in the PHYSICS
 *   frame. Method that works: execTrace @0x80035464 capturing [s4,fp,s0] + read the plane at s0; the Cross button
 *   is JUMP; hold XZ over the block; correlate physics p1.y = floor - d1.
 * ============================================================================
 *
 * ADD-BLOCK CATCH — ISOLATED SINGLE-STEP (2026-07-05, full swept-resolver flow traced; Cross=jump, no teleport):
 *
 * FULL RESOLVER FLOW for a floor plane (FUNC@0x80035280, per candidate): d1 test @0x80035464 (bgez s4 -> skip if
 * d1>=0, d1 = plane_floor - p1.y) -> d0 test @0x800354b4 (bltz s2 -> skip if d0<0) -> POINT-IN-POLY jal 0x80032610
 * @0x80035644 (returns 0 if Flik's XZ is outside the triangle -> skip; gated on |ny|>|nx|,|nz| = "mostly vertical")
 * -> keep NEAREST crossing (min v1 = d0<<14/(d0-d1)) recorded @0x800356a4 (plane->sp+0x90, sector->sp+0xa0) -> after
 * the loop, RESPONSE @0x8003573c: a PARTIAL push-back added to the physics pos [s5], displacement = delta *
 * (d0>>3) / ((d0>>3) - ((d1-192)>>3)). It is NOT a snap: for a DEEP first-crossing (d1 large -ve) the fraction is
 * tiny, so a fast faller is only nudged and keeps sinking.
 *
 * LIVE RESULT on the isolated jump (add-block floor 5000, OG dropped below): sector 77 CROSSES (d1=-1518, d0=82),
 * PASSES point-in-poly (one tiled plane returns 1), and IS RECORDED as the sole best crossing — yet Flik is not
 * caught. So the earlier stages all work; the failure is the partial-push-back response vs a deep crossing.
 *
 * KEY (kills the "converted add-block is special" theory): an ORIGINAL block sector (100) reheighted to a flat floor
 * at 5000 fails the SAME fast fall Flik as a from-scratch add-block. So add-block-vs-original is NOT the
 * discriminator. In EVERY neutralize configuration Flik reliably comes to rest on whichever sectors were left at
 * the DEEP ~10234 level and passes through anything placed at 5000 (flat OR block), which points at a physics-side
 * mechanic (spawn-snap / velocity handling / a safety-floor), NOT the plane emitter. STRONG CONFOUNDS remain
 * (per-sector XZ coverage — Flik's spawn XZ is owned by BLOCK sector 100, so a "flat sector at 5000" test may not
 * actually sit under him; plus the physics-vs-render frame), so the final catch-reliability discriminator is NOT
 * cleanly isolated.
 *
 * CONCLUSION / do-not-change-the-emitter-yet: root-cause #1 (floor formula ref.y = surf>>5 - origin.y) is proven +
 * fixed and is necessary. But the block-plane catch is entangled with the physics integrator (the partial-push-back
 * response + a deep-fall mechanic), not a further emitter field. NEXT (physics integrator, not the resolver): find
 * where Flik's fall VELOCITY / grounded-state is set each frame (accessLog write-watch the physics-pos buffer [s5]
 * during a fall to find the integrator), and whether a kill/safety floor forces the ~10234 rest; only then decide
 * if block-plane catching is viable or if authored walkable floors must stay on the flat per-sector origin-Y path
 * (native_collision_from_heightfield), which is the mechanism the game itself uses for the ground Flik stands on.
 * ============================================================================
 *
 * C2 (SUPERSEDED by the breakthrough above — this described the ENEMY list, not Flik's):
 * A from-scratch flat-sector block (sec 77 + tiles) is SYSTEMATICALLY excluded from selection. Established:
 *   - The builder runs DURING MOVEMENT; the candidate list is STALE on static frames (this confounded early
 *     static reads — always sample Y/candidates while Flik is walking, in small frame increments from spawn).
 *   - Sec 77 IS gathered + iterated by phase 2 (execTrace @0x80037494 shows sec 77 in the per-sector loop).
 *   - Continuous walk (cont2): Flik walks SQUARELY through sec 77's tile region (inside its runtime AABB,
 *     directly over a tile at multiple frames), yet sec 77 NEVER enters the candidate list (0/24 samples),
 *     while real sectors 107/108 are selected on essentially every frame. So it is NOT edge-of-path geometry.
 *   - CONFIRMED sec 77 IS in Flik's grid cell (cell16 contains Flik + lists 77), and its runtime AABB gate
 *     PASSES by hand-calc at Flik's live position ((Flik.x+4096-minX)<u(extX+8192) etc all true), and its
 *     full runtime record (0x800a7e48 +0x00..0x2f) shows NO anomalous field vs a working sector (108) — same
 *     +0x0c=6, +0x2c=6, a valid +0x10 block ptr, sane AABB. Yet across a 24-sample continuous walk squarely
 *     over its tiles, sec 77 enters the candidate list 0/24 times. So the discriminator is SUBTLER than cell
 *     membership, the AABB gate, or any single runtime field — it is UNISOLATED despite the grid + both
 *     candidate phases being fully decoded.
 *   NEXT to close it: this needs LIVE SINGLE-STEP (halting breakpoint), not execTrace/hand-calc. Set an
 *     execute breakpoint at 0x800374ac with Flik parked over a sec-77 tile mid-walk, step through the
 *     per-sector gate for sec 77, and read t6/t7/a0 and each branch outcome to see the exact comparison that
 *     drops it (candidates: the gather may pass a STALE Flik box; a per-frame reset of sec 77's block ptr; or
 *     a dedup that drops a sector whose block was ADDED after the descriptor pass). Also worth: does pass-1
 *     of the grid builder actually walk a newly-owned block's footprints, or does it read the block via a
 *     structure the ADD-BLOCK path did not populate (e.g. the +0x48 descriptor / reverse-map used by the
 *     +0x4a!=1 vs ==1 paths)?
 *   Everything ELSE is proven correct: resize (+cold-boot), ownership (+0x4a=0), footprint encoding, CW
 *   winding, -Y-up sign. TOOLS: emit_collision_addblock.py, native_collision_mesh_codec (CW floor tris);
 *   reheight path (emit_collision_reheight.py) is the fully-working emitter for the 126 sectors with a block.
 * ============================================================================ */

/* ============================================================================
 * PER-FACE PLANE-EMITTER -- WALKING VALIDATED (2026-07-05)
 * ----------------------------------------------------------------------------
 * The corridor/reheight path (per-sector origin-Y + block-plane delta reheight) hit its ceiling: it only ~halves
 * LEVEL01's hilly collision (movie max-climb -201469 -> -96655) and can't flatten (residual ~7860 near spawn),
 * because the delta is sampled from the VISUAL per-payload mean, not each sector's real collision height. Absolute
 * origin-Y set BREAKS the sectors (Flik falls through) -- reconfirmed 2026-07-05 even for a uniform target.
 *
 * SO: emit PER-FACE planes from an authored floor SURFACE instead. tools/emit_floor_planes.py:
 *   - FLAT play-patch sectors get a from-scratch per-face mesh block (heightfield_collision.mesh_block +
 *     emit_collision_addblock; add_block recomputes offsets each call, so it runs SEQUENTIALLY over many sectors).
 *   - BLOCK sectors get their planes reheighted toward the same surface (emit_collision_reheight, per-sector delta).
 *
 * KEY RESULT -- the open question ("does Flik WALK per-face planes, or do they only fall-catch?") is answered YES:
 *   - Flat de-risk (surface = flat 2144 rt): controlled +X walk climbs 5031 vs 7860 for origin-Y/reheight -> per-face
 *     planes carry a WALKING Flik, FLATTER than origin-Y, no fall-through, feet aligned with the visible floor.
 *   - Ramp (platform A 2144 -> +X ramp -> platform B raised 4000 rt): Flik WALKS UP the ramp, climb 3522 ~= the
 *     4000 rise, no plunge. So the heightfield_collision docstring's claim ("a ramp of floor tris lets Flik walk
 *     the slope -- his gravity segment crosses the rising surface") HOLDS for walking UP, not just descending.
 *     This is the capability the reheight ceiling could not provide.
 *
 * REMAINING (documented, not blockers): (1) VISUAL match -- the ramp test reused a FLAT displace DAT, so the GTE
 * floor floats above Flik at platform B; regenerate the visual to the SAME platform->ramp->platform profile. (2)
 * BLOCK sectors still reheight (delta, imperfect) -- replacing their blocks with per-face meshes (block-REPLACE
 * resize, not just add-to-flat) would remove the residual. (3) extend the emitter over the whole g3native movie
 * corridor + validate via validate_g3_native_movie.py. TOOLS: emit_floor_planes.py (+ heightfield_collision.mesh_block,
 * emit_collision_addblock, emit_collision_reheight). Chunk-34/35 visual strip stays parked until collision fully
 * carries Flik. Vault: [[Tier 3 - Native Terrain Path]] "Per-face plane-emitter".
 * ============================================================================ */

/* ---- PER-FACE EMITTER + MATCHED VISUAL: A->ramp->B and the FULL movie corridor (2026-07-05) ----
 * build_g3_native.py --planes pairs the per-face collision (emit_floor_planes) with a GTE visual regenerated from
 * the SAME surface. FRAME KEY: the visual payload frame renders x32 in runtime (node<<5; flat-aligned pair
 * base_y -497 <-> collision runtime 2144), so the VISUAL rise = collision_rise/32 to raise a platform by the same
 * screen amount.
 *   A->ramp->B (--planes): platform A visual+collision COINCIDE (Flik stands on the visible floor); Flik WALKS UP
 *     the ramp (climb ~3522 ~= rise). Residual: at the raised platform-B TRANSITION the GTE floor shows a floating
 *     "sheet" -- displace flattens each payload to its own MEAN, so a height step reads as a sheet edge (a
 *     displace-to-mean limitation, not collision).
 *   FULL CORRIDOR (--planes --corridor --rise 0): 85 flat sectors get per-face blocks + 86 block sectors reheighted
 *     across the whole g3native movie path. Movie-validated (validate_g3_native_movie.py): RENDER_C(OT)=0,
 *     FUNC_80010000 active (5124 hits), NO plunge, Flik walks the full traversal aligned with the floor under his
 *     feet. Max hill-climb -201469(pristine) -> -96655(origin-Y+reheight) -> -37727(per-face) = ~81% flatter (vs
 *     52% for origin-Y). Per-face planes on FLAT sectors (vs origin-Y) are the big win.
 *   UPDATED 2026-07-06: P3 closed the displace-to-mean visual residual for the current flat corridor. planes-mode
 *     now defaults to native_terrain_export.flatten_floor(), which SETS every FUNC_80010000 floor vertex to the
 *     authored surface instead of shifting each payload to its mean. Legacy displace visual is kept only behind
 *     --displace-visual for A/B captures. Remaining non-P3 items: chunk-34/35 structural terrain and the small
 *     0x604 dirt hard path. */

/* ---- BLOCK-REPLACE narrow gate -- MECHANISM works, SELECTION does not (2026-07-05) ----
 * Goal: replace an existing BLOCK sector's collision with a from-scratch per-face mesh (finish the delta-reheight
 * residual). tools/emit_collision_addblock.replace_block() mirrors add_block for a sector that already owns a block:
 * splice new block bytes at the running-sum position, adjust the chunk-32 +0x04 length prefix + the sector's
 * block_size. STRUCTURE VERIFIED: resizes, recompress round-trips, cold-boots (sector 99: 4460->816 B).
 * BUT the narrow gate FAILS in-game: replacing sector 99 (covers Flik's spawn) with a per-face mesh at the flatten
 * surface -> Flik FALLS THROUGH (plunge), at any tiling density (coarse 4x4 .. fine 16x16). REHEIGHTING the SAME
 * sector to the same surface catches him fine. So the mesh itself is valid (add_block to FLAT sectors catches Flik,
 * C2) -- the gap is that replacing a BLOCK sector leaves the sector-record state that REGISTERS the block for
 * candidate SELECTION stale: reheight keeps the pristine planes' footprints (and the sector AABB @0x800a7e48
 * derived from +0x14/1c/24/28 = origin+footprint<<5, and the +0x1e/+0x48 reverse-map indices), while replace_block
 * only rewrites +0x04. So the new block is present but NOT selected into Flik's candidate list (FUNC_8003633C).
 * NEXT (before scaling replace to the corridor): update the target sector's footprint AABB (+0x14/1c/24/28) + the
 * reverse-map (+0x1e/+0x48) to the new mesh's extent so the grid builder registers + selects it -- OR keep the
 * reheight path (already 81% flatter across the movie, Flik walks it). Gate NOT passed -> replace NOT scaled.
 * TOOLS: emit_collision_addblock.replace_block, emit_floor_planes.emit(replace_sectors=...). */

/* ---- BLOCK-REPLACE/FLATTEN follow-up: SELECTION works; the wall is seam DISCONTINUITY (2026-07-05) ----
 * CORRECTION to the prior note (which guessed replace_block left registration stale): a runtime probe of the
 * FAILING build (0x800a7e48 + 99*0x30) shows the replaced/flattened sector 99 IS registered -- origin correct,
 * block ptr valid (0x800cd3f0), runtime AABB COVERS spawn, flag=6 (0<f<100) -- and Flik is CAUGHT at spawn
 * (X=197108 stable). So selection/registration is NOT the problem. Flik falls only when WALKING.
 * TWO real causes found: (1) a grid REPLACE makes big-footprint quads (fp.extX ~293 file) that break the FINE
 * per-record candidate select (@0x8003758c) during motion -- pristine blocks use MANY SMALL footprints clustered on
 * the walkable area, not a uniform grid over the bbox. Fix attempt: flatten_block (emit_collision_reheight) SETS the
 * EXISTING planes' ref.y to a uniform floor (KEEPS their small footprints), size-preserving. (2) But flattening ONE
 * sector to a uniform height while its NEIGHBOURS are delta-REHEIGHTED (varied) creates a height DISCONTINUITY at
 * the sector seam -- Flik walks off the flat sector into a step and falls. So the one-sector gate is CONFOUNDED:
 * authored-flat and delta-reheight can't meet cleanly at a seam. A valid flatten test needs a CONSISTENT surface
 * across ALL block sectors in the region (no seams) -- i.e. it can't be proven on one sector in isolation.
 * STATUS: reheight path (Flik walks the whole movie, 81% flatter, -201469->-37727) stays the working ceiling;
 * fully-authored flat block collision needs whole-region consistent flattening (calibrated per-sector floors so
 * seams match) -- a dedicated pass, not a one-sector drop-in. TOOLS: replace_block, flatten_block (both work
 * structurally). chunk-34/35 strip PARKED. */

/* ---- WHOLE-REGION BLOCK FLATTEN -- VALIDATED (2026-07-06) ----
 * P1 is now a passed build path, not just the next hypothesis. tools/emit_floor_planes.py gained
 * flatten_blocks=True; for every selected block sector it calls emit_collision_reheight.flatten_block(), setting the
 * existing planes to one floor while preserving their native small footprints. This avoids the grid-replace
 * big-footprint failure and removes the one-sector seam confound by applying the same surface region-wide.
 *
 * Canonical menu-safe build command:
 *   python3 tools/build_g3_native.py --planes --corridor --rise 0 --flatten-blocks --suppress-grass
 *     --out build/ABL_g3native
 *   --suppress-horizon remains available only for explicit A/B backdrop experiments; it globally stubs
 *   menu-shared FUNC_8003E928 and is not baseline-safe.
 * Collision side of that build: 85 flat sectors get per-face blocks; 86 block sectors are FLATTENED; malformed
 * relocation-region block sectors 178-188 are skipped as before. Movie validation on build/ABL_g3native.cue:
 * RENDER_C=0, FUNC_80010000=7301, no plunge, Flik Y range [-11682,5216]. So the whole-region flatten keeps Flik
 * carried across the operator's full traversal and improves the previous per-face/reheight floor (-37727 min Y) to
 * -11682 min Y on the same movie path. Residual relief remains, but the seam-discontinuity wall is cleared enough
 * to move to P2. */

/* ---- P3 ABSOLUTE NATIVE VISUAL -- VALIDATED (2026-07-06) ----
 * P3 fixes the visual side, not collision selection/resolution. tools/build_g3_native.py --planes now emits the
 * native GTE floor through native_terrain_export.flatten_floor() by default: for each DAT node-array floor payload
 * (FUNC_80010000 input), set vertex world Y directly from the authored file-frame surface. This is size-preserving
 * (same vertex count/command stream) and removes the old displace-to-mean behavior that kept LEVEL01 relief inside
 * each payload.
 *
 * Canonical menu-safe P3 build:
 *   python3 tools/build_g3_native.py --planes --corridor --rise 0 --flatten-blocks --suppress-grass
 *     --out build/ABL_g3native
 * Geometry proof on build/ABL_g3native_terrain.DAT: 30 floor payloads / 2775 vertices, every payload
 * Y[-497,-497], max_payload_y_range_after=0, max_abs_error_to_target_after=0 (artifact:
 * build/p3_abs_geometry_stats.json). Movie validation: RENDER_C=0, FUNC_80010000=7303, no plunge, Flik Y range
 * [-11681,5216]. So the current flat authored corridor has no retained native-floor relief/sheet artifact. */

/* ---- P5 BLENDER HEIGHTFIELD PROFILE -- VALIDATED (2026-07-06) ----
 * P5 extends the P4 profile loop from a flat/ramp scalar to a Blender-authored heightfield mesh while keeping the
 * same native-frame collision model. tools/abl_blender/export_g3_native_profile.py now recognizes scene prop
 * abl_g3_surface=heightfield and exports a mesh grid named G3NativeHeightfield to surface_json. The grid convention
 * is bx=game_x/256, by=game_z/256, bz=-runtime_delta_y/256. tools/build_g3_native.py --surface-json then maps:
 *   visual file Y     = base_y@spawn + runtime_delta_y/32
 *   collision runtime = pa_rt + runtime_delta_y
 * using the validated anchor pair base_y=-497 <-> pa_rt=2144. This is the same x32 visual quirk, made explicit
 * for arbitrary sampled heightfields. absolute_file_y and file_delta_y modes are also accepted for future fixtures.
 *
 * Validated command:
 *   python3 tools/build_g3_native_from_blender.py build/g3_native_heightfield.blend --validate
 *     --shot-prefix g3nm_p5height --profile build/g3_native_p5_profile.json
 *     --surface-out build/g3_native_p5_surface.json --report build/g3_native_p5_report.json
 * Surface: runtime_delta_y grid 33x65, dy=[-196,256]. Collision side stayed on the P1/P3 path:
 * 85 flat sectors got per-face mesh blocks, 86 native block sectors were flattened to the sampled surface, and
 * relocation-region sectors 178-188 skipped as before. Movie validation: RENDER_C=0, FUNC_80010000=7293, no plunge,
 * Flik Y range [-10017,5374].
 *
 * Boundary: this closes GENTLE non-flat heightfield authoring through native GTE + matched collision. It does not
 * prove arbitrary topology, overhangs, walls, or steep authored meshes; those need a later mesh/collision frontier
 * beyond flatten_block's per-sector uniform block treatment. P7 regression tool:
 * tools/regress_g3_native_authoring.py checks the dy/32 mapping and wrapper command. */

/* ---- P8/P9 TRACK-B SCENE CONTRACT -- VALIDATED OFFLINE + MOVIE (2026-07-06) ----
 * P8/P9 are a pragmatic level-authoring slice on top of the validated heightfield path, not a new collision
 * primitive. export_g3_native_profile.py now exports level_meta from Blender empties:
 *   Spawn/G3Spawn -> x,z,runtime_delta_y,radius
 *   Goal/G3Goal/Exit -> x,z,runtime_delta_y,radius
 * using the same bx=X/256, by=Z/256, bz=-runtime_delta_y/256 convention as the heightfield grid.
 *
 * tools/validate_g3_native_scene.py is the offline gate. It checks that surface_json exists, spawn/goal are inside
 * the surface footprint, and a grid path connects spawn to goal with adjacent runtime height steps <=512. This does
 * NOT replace the in-game resolver proof; it prevents bad authored scenes from reaching the expensive DuckStation
 * run. build_g3_native_from_blender.py --check-scene wires this into the one-command path before disc build.
 *
 * Validated fixture build/g3_native_level_scene.blend:
 *   scene gate PASS: path_nodes=63, dy=[-196,256], max adjacent runtime step=20.
 *   movie gate PASS: RENDER_C=0, FUNC_80010000=7299, no plunge, Flik Y range [-11553,5373].
 *
 * Closure boundary: Spawn/Goal are metadata/offline validation only right now; the game is not yet patched to use
 * them for actual spawn relocation or level-complete trigger behavior. That is the next runtime integration step. */

/* ---- P15 COLLISION RESIDUAL AUDIT -- OLD FOOTPRINTS BOUNDED, NOT SOLVED (2026-07-06) ----
 * Manual P14 play exposed an overstatement in the P1/P11-P14 status: Track-B currently has a validated authored
 * heightfield ROUTE over LEVEL01's native chunk-32 sector structure, not a clean authored collision world.
 *
 * Working baseline:
 *   - FLAT selected chunk-32 sectors get authored per-face blocks via heightfield_collision.mesh_block +
 *     emit_collision_addblock.add_block.
 *   - existing BLOCK sectors are flattened with emit_collision_reheight.flatten_block(), preserving LEVEL01's
 *     native small X/Z plane footprints because that is what the fine per-record candidate selector tolerates while
 *     Flik walks.
 *   - malformed/non-mesh selected sectors 178..188 are skipped by the current decoder/emitter.
 *   - chunk-33 and other runtime collision sources are outside this emitter.
 *
 * New audit tool: tools/report_g3_native_collision_coverage.py. It compares pristine LEVEL.RAW against the built
 * RAW, using the relocated sector-array offset after add_block, and classifies each chunk-32 sector. This is an
 * offline source audit only; DuckStation validation still proves physics.
 *
 * P14 --retile-blocks experiment: structurally rewrote 86 block-sector footprints in place while preserving block
 * sizes/counts, but cold-boot validation FAILED. Flik stayed pinned at the authored spawn
 * (197088,5344,492896); marker/goal traversal did not complete. So retile_block is not a replacement for
 * flatten_block yet.
 *
 * P14 --sink-outside-collision 200000 experiment: PASS as a partial mitigation. Non-selected chunk-32 sector
 * origin floors are moved far down; marker fired around frame 4410, goal around frame 4490, RENDER_C=0,
 * FUNC_80010000=672, no plunge. This reduces off-route stock floor catches but does NOT remove retained footprints
 * inside the authored region.
 *
 * Coverage on the passing sink build (build/g3_native_platform_ramp_sink_collision_coverage.json):
 *   authored_added_block_on_pristine_flat_sector      85
 *   flattened_old_block_retained_footprints           86
 *   selected_malformed_block_left_as_old_collision    11  (178..188)
 *   sunk_outside_author_region                         7
 *   surface-node clean added-block coverage           0.277
 *   surface-node added+flattened-retained coverage    0.586
 *
 * Correct conclusion: the old collision regression is bounded and measurable, but not fixed for arbitrary Blender
 * levels. The next real collision frontier is either making retiled/replaced block footprints walkable in-game, or
 * porting Track-A's proven per-face collision logic over the GTE-authored Track-B surface. */

/* ---- P16 BLOCK-SECTOR SELECTOR TRACE -- REPLACE WORKS LOCALLY, RETILE DOES NOT (2026-07-06) ----
 * Correction to the older "replacement is rejected/stale" and broad "retile pins Flik" notes:
 * tools/trace_g3_native_collision_selector.py now cold-boots an isolated DuckStation instance, replays
 * g3native_movie.movie.json, samples the player candidate list (gp+0x57c / 0x80091718 / 0x8009c230), and traces
 * resolver PCs 0x80035464(d1), 0x800354b4(d0), 0x80035644/4c(point-in-poly), 0x8003573c(response), plus
 * RENDER_C and FUNC_80010000. build_g3_native.py also writes per-disc RAW snapshots so traces cite the exact staged
 * chunk-32 image instead of the shared build/ABL_g3native_collision.RAW scratch file.
 *
 * Minimal facts:
 *   - Control P14/P15 path still passes: 85 added flat-sector blocks, 86 flattened retained-footprint block
 *     sectors, RENDER_C=0, FUNC_80010000 active, marker+goal reached.
 *   - --retile-sector 100 now PASSES after using the decoded native block footprint union instead of origin+/-TILE.
 *     Sector 100 reaches response_8003573c in the native resolver.
 *   - --retile-sector 99 FAILS and is the minimal bad retile case. Control sector 99 is selected but all target
 *     point-in-poly returns are zero, so it does not catch the spawn route. Retiled sector 99 reaches response at
 *     frame 4355, then Flik is off-route by frame 4360 (Z 468202 vs control 492984).
 *   - --replace-sector 99, --replace-sector 100, and paired --replace-sector 99 --replace-sector 100 all PASS
 *     cold-boot traversal, marker, and goal. Therefore native block replacement is not inherently rejected by the
 *     selector.
 *   - Whole-region --retile-blocks still FAILS pinned at spawn. For sector 100, candidates are sampled but no d1/d0
 *     / point-in-poly / response events fire after spawn, so broad retile breaks upstream movement/floor update
 *     before FUNC_80035280 iterates target planes.
 *
 * Current invariant: size-preserving retile is unsafe because it keeps old group/record counts/layout while filling
 * new X/Z cells; in sector 99 it converts a retained-footprint point-in-poly rejection into an active response.
 * Size-changing replace_block with a fresh heightfield_collision.mesh_block is locally accepted and walkable for
 * the spawn pair sectors, but it is still opt-in and not scaled to the full selected block region. Keep P11/P14
 * baseline on flatten_block until replacement is expanded sector-by-sector with cold-boot traversal evidence.
 *
 * Evidence doc: docs/G3_NATIVE_P16_COLLISION_SELECTOR.md. */

/* ---- P17 ROUTE-SCALE BLOCK REPLACEMENT -- VALIDATED FOR MOVIE ROUTE (2026-07-06) ----
 * P17 expands the P16 "replace is accepted locally" result to the current platform/ramp movie route, without
 * promoting replacement to the baseline. tools/trace_g3_native_route_sectors.py cold-boots the built disc, replays
 * the movie, maps runtime plane pointers back to chunk-32 sectors, and emits the retained route block sectors that
 * should be converted from flatten_block to replace_block.
 *
 * Control route over the P11/P14/P15 flattened baseline identified retained block-sector targets:
 *   93, 99, 100, 107, 108
 * using candidate/response evidence, not screenshots or manual play feel. Each expansion used explicit opt-in
 * --replace-sector flags plus --flatten-blocks for the rest of the region; --retile-sector/--retile-blocks and
 * --sink-outside-collision stayed out of the test.
 *
 * Cold-boot traversal passed for:
 *   99+100, then +108, then +93, then +107.
 * Final build build/ABL_g3native_p17_route_final.cue reached marker+goal with RENDER_C=0 and FUNC_80010000 active.
 * Final provenance reports control_targets_replaced=[93,99,100,107,108], control_targets_not_replaced=[],
 * retained_route_block_sectors=[], malformed_route_sectors=[].
 *
 * Boundary: this is route-scale authored block replacement, not a clean global collision world. The final coverage
 * still reports 81 flattened old-footprint block sectors, 11 selected malformed old sectors, and 7 untouched outside
 * block sectors. Evidence doc: docs/G3_NATIVE_P17_ROUTE_COLLISION_REPLACEMENT.md. */

/* ---- P18 AUTHORED-AREA REPLACEMENT SWEEP -- BLOCKED ON INTERACTION SET (2026-07-06) ----
 * P18 added runtime provenance classification to tools/trace_g3_native_route_sectors.py. With --p18-provenance and
 * --coverage-report it cold-boots the disc, samples Flik XYZ plus the player candidate list (gp+0x57c,
 * 0x8009c230, 0x80091718), maps response plane pointers back to sectors, classifies candidates/responses by the
 * coverage status, and explicitly records no_swept_plane_response_observed intervals. This keeps visual residuals
 * separate from collision proof.
 *
 * Provenance baseline:
 *   - flattened control: retained route sectors [93,99,100,107,108], retained responses on [93,99,100].
 *   - P17 final: retained route sectors [], replaced_authored_block responses on [99,100].
 *
 * Sweep result: best passing expansion is P17 seed plus [0,73,87,88,89,90,91] (12 replaced sectors total). Adding
 * sector 92 in the accepted B01 order fails. Sector 92 alone with the P17 seed passes; reduced interaction testing
 * found a 1-minimal failing set P17 seed + [0,73,92]. The pairs 92+0 and 92+73 pass, but 92+0+73 fails.
 *
 * Minimal failing build build/ABL_g3native_p18_bisect_b01_interact_t02_0_73.cue: Flik remains exactly at
 * (197088,5344,492896) from frame 4335 through 6530. Candidate samples still show sectors
 * [44,45,77,99,107,108], but resolver watch totals are all zero after spawn:
 * d1_test_80035464=0, d0_test_800354b4=0, point_in_poly_call_80035644=0, response_8003573c=0, and
 * player_y_commit_80036cec=0. Therefore the blocker is an upstream movement/update stall before FUNC_80035280
 * iterates planes, not a retained/malformed/outside collision response.
 *
 * Evidence doc: docs/G3_NATIVE_P18_COLLISION_PROVENANCE_SWEEP.md. */

/* ---- P19 MINIMAL INTERACTION MOVEMENT-STALL DIAGNOSIS (2026-07-06) ----
 * P19 added tools/trace_g3_native_movement_stall.py to compare exactly:
 *   - P17 seed [93,99,100,107,108]
 *   - P18 best prefix seed+[0,73,87,88,89,90,91]
 *   - sector 92 alone with the P17 seed
 *   - seed+[0,73] immediate control
 *   - minimal failing seed+[0,73,92]
 *
 * The first divergent invariant is now sharper than P18's "before FUNC_80035280": in the failing interaction,
 * movie playback still advances and the P11 runtime spawn has applied, but FUNC_80048138 has ZERO hits in the
 * post-spawn trace window. Consequently the player integrator call site 0x800495c8, hook site 0x800495d0,
 * FUNC_8003633C entry/tail, candidate reset 0x800363b4, candidate append 0x800368e8, FUNC_80035F24,
 * FUNC_800345CC, FUNC_80035280, d1/d0/PIP/response, and player-Y commit are all zero.
 *
 * Candidate samples [44,45,77,99,107,108] in the failing build are STALE: accessLog records zero writes after spawn
 * to gp+0x57c / 0x80091718 / 0x8009c230, while every passing control records 7299 candidate-list-related writes
 * over the same 90-frame window. So do not interpret the failing candidate list as current selector evidence.
 *
 * Passing controls all first move at movie frame 4360 and show FUNC_80048138=20, FUNC_8003633C entry/tail=24/20,
 * FUNC_80035280=5, d1/d0=89/38, response=2, player_y_commit=11. The failing interaction stays fixed at
 * (197088,5344,492896), keeps movie playback advancing 4332->4421, has FUNC_8003633C entry/tail=0/0, and has
 * first_divergent_invariant player_update_80048138_not_running.
 *
 * Evidence doc: docs/G3_NATIVE_P19_MOVEMENT_STALL_DIAGNOSIS.md. */

/*
 * P23 collision grid-builder destination diagnosis (2026-07-06). Live five-case tracing proves
 * 0x800319a0/0x80031a64 use t9/a2 = base+s1, element index s1/4. In the failing seed+[0,73,92]
 * run the base is 0x801c3390 and 0x801c362c is inside the intended builder output range. The bad
 * value 0xfffabfa0 is produced by the max-Z path from a collision block group plus runtime sector
 * entry 167 origin-Z, so the value itself is valid grid/bounds data. The fault is the workspace
 * overlap/lifetime collision with render/cull, not corrupted collision source arithmetic.
 */

/*
 * P43 practical Track-B authoring boundary (2026-07-06). The stable designer
 * examples deliberately stay inside the P29/P30 collision-island contract:
 * bounded heightfield floors, mild ramps/plateaus/ridges, spawn/marker/goal,
 * sink-outside scoped to the authored profile, and native FUNC_80010000 active
 * with Track-A off. They do not exercise this converter's broad replacement or
 * add-block paths, and they do not claim walls, caves, stacked floors, objects,
 * free-roam, retile, chunk-35 cleanup, or full old-collision replacement.
 * P44 only adds a designer pattern router/evidence gate on top of that pack:
 * choose the intent first, then prove the edited scene with preflight plus
 * cold-boot marker/goal, RENDER_C=0, FUNC_80010000>0, no plunge, and island
 * evidence. It does not promote any P43 pattern to a baseline/default.
 * P45 stress-matrix probes are evidence-only generated scenes under build/:
 * they tighten triggers, widen routes, and increase mild height/ridge terms to
 * measure the current envelope. They do not exercise new converter behavior.
 *
 * P46/P47 collision-frontier catch-up (2026-07-07): replacement-sector evidence
 * resumed as opt-in frontier work, not as a baseline/default. P46 formalized the
 * five route seed sectors [93,99,100,107,108] in tools/g3_native_collision_frontier.py
 * and passed cold boot with marker/goal, RENDER_C=0, FUNC_80010000>0, no plunge,
 * replaced_authored_block=5, and no retained route blocks. P47 then expanded the
 * same fixture to the prefix07 envelope [0,73,87,88,89,90,91,93,99,100,107,108],
 * again passing marker frame 4410, goal frame 4490, RENDER_C=0, FUNC_80010000=500,
 * no plunge, replaced_authored_block=12, retained route blocks [], and active route
 * responses only from replaced authored sectors [99,100].
 *
 * Evidence caveat: later RE showed that global gp+0x57c / 0x8009c230 / 0x80091718
 * candidate samples can be stale or entity-owned in some traces. Treat response
 * events mapped directly from the resolver plane pointer (s0) through the built RAW
 * plane map as the stronger proof. Candidate-list sampling remains useful context,
 * but it is not standalone proof of player-floor selection. Sector 92 remains
 * excluded from unguarded P47 because the 0,73,92 interaction is the P20-P24
 * stale render/cull workspace fault, not a swept-resolver rejection.
 *
 * P48 result (2026-07-07): installing --p24-stale-render-guard is not enough
 * to admit sector 92 into the P47 envelope. The guarded P47 control passes with
 * skip counter 0, but P47+92 stalls at spawn with FUNC_80010000=0, no goal,
 * P24 skip counter 0, and no player-floor liveness. Sector 92 therefore fails
 * before the P24 key-65 guard path; keep it out of the usable replacement
 * envelope until a new upstream cause is isolated.
 *
 * P49 result (2026-07-07): the full P48 probe reproduces the P27 helper
 * frontier rather than a swept-floor rejection. The full set including sector
 * 91+92 enters render-driver helper 0x8003efc8 and does not return; the
 * nearest pass omits sector 91 while still including 92. The active-record
 * pointer/span diverges as 0x801c561c/0xfff94040 vs 0x801c411c/0x0000000f.
 * Do not treat candidate-list samples as proof that sector 92 is valid.
 *
 * P50 result (2026-07-07): the replacement layout can admit sector 92 only in
 * the guarded swap envelope that omits sector 91. Cold boot reaches marker and
 * goal with replaced_authored_block=12, RENDER_C=0, FUNC_80010000=413, retained
 * route blocks [], and exactly one P24 skip. The full 91+92 set remains blocked
 * before native GTE, so this is not an unguarded sector-92/default promotion.
 */

/*
 * P51/P52 ROOT FIX (2026-07-07) — the P18–P50 replacement-layout fault chain is
 * SOLVED. All of it (P20 key-65 bus error, P22/P23 workspace overlap, P26 GTE
 * loss, P27/P49 render-driver helper loop, P48/P50 sector-91/92 exclusions) was
 * ONE bug: the load-time collision grid/list builder FUNC_800313A8 scribbles
 * five per-sector bounds arrays at fixed offsets below the hard-coded arena
 * limit [0x80082238]=0x801CC390 (writer 0x8003C2F4), AFTER render nodes are
 * built; grown chunk-32 layouts push live render nodes/records into that
 * [limit-0x9000, limit) window. Fix: pack the window spacing 0x2000 -> 0x800
 * (5-word EXE patch, build_g3_native.py --p51-scratch-pack). The full 13-sector
 * envelope incl. 91+92 now passes unguarded, and --replace-all-blocks (P52)
 * authors ALL 86 corridor block sectors (+85 flat add-blocks) with zero
 * retained footprints, cold-boot proven. Sector-92/91 "interactions", the P24
 * guard, and the guarded swap envelope are OBSOLETE as constraints. Full RE +
 * evidence: src_re/collision_grid_builder_800313a8.c, docs/G3_NATIVE_P51_*.md,
 * docs/G3_NATIVE_P52_*.md, vault [[Tier 3 - Native Terrain Path]] P51/P52.
 */
