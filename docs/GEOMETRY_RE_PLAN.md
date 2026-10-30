# Geometry RE Plan — A Bug's Life (SCUS-94288), LEVEL01 first

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

Phased, evidence-driven research plan for **how LEVEL01 geometry is created at runtime**
from `LEVEL01/LEVEL.DAT` — specifically the records and relocation structures that live
**after** the type-`0x3f` pickup/object placement record. This is a *planning/scaffolding*
pass: it sets up targets, files, and evidence rules. It does not decompile new functions,
patch data, or build images.

Scaffold lives in [`src_re_geometry/`](../src_re_geometry/). This plan is the index for it.

---

## 1. Purpose and non-goals

### Purpose
Reconstruct, with evidence, the runtime pipeline that turns LEVEL01 DAT records (records
`0x01`, `0x0b`, `0x0c`, `0x0d`, the negative-type records `-2..-7`, and the trailing
relocation tables) into the level's **render geometry** and **collision/pathing geometry**.
The pickup/type-`0x3f` system is treated as already-solved *context*, not the target.

### Non-goals
- No ISO builds.
- No patching of DAT/BIN/CUE files (until a single supported diagnostic edit in G6, and only
  when explicitly instructed to build).
- No modification of the existing pickup decompilation files in `src_re/`.
- No broad whole-game decompilation; only the geometry creation/consumer paths for LEVEL01.
- **No mesh/collision/pathing semantics inferred without code or runtime evidence.** A
  structure is not "mesh" or "collision" until a consumer proves it.
- No new reverse engineering performed in this planning pass; G1+ do the work later.

---

## 2. Relationship to the completed pickup/object decompilation phases

The pickup track (`docs/DECOMPILATION_PLAN.md`, phases 1–6) is **DONE** and provides the
foundation this plan builds on:

| Completed asset | What it gives the geometry track |
|---|---|
| `src_re/dat_parser_8001cdc0.c` (Phase 1, CONFIRMED) | The parser/relocator. Its **pass 1 / pass 2 / pass 3** are exactly the geometry-facing machinery: pass 1 builds `0x20`-byte output records (GTE matrix + source pointer) into `DATbase+arg2`; pass 3 relocates a second pointer table. This is the entry point for G2. |
| `tools/dat_reloc.py` (CONFIRMED, 1248 LEVEL01 sites) | Enumerates every relocated pointer and its target. The targets land in the post-`0x3f` geometry region `[0x45f0, EOF)`. This is the evidence base for G1. |
| `src_re/re_types.h` | Confirmed globals (`G_DAT_BASE_PTR`, `G_TRAIL_BLOCK_PTR`, `G_PASS2_BASE_PTR`, `G_PASS3_BASE_PTR`, `G_DAT_ENTRY_COUNTER`). Geometry structs will be added here only when a body proves them. |
| `docs/DAT_FORMAT_AND_RELOCATION.md` | Confirms the post-`0x3f` records are the level's static geometry/object-instance + (candidate) collision data, and that the post–Press-X crash from naive append was a **consumer of corrupted geometry** — proof such consumers exist and are gameplay-fatal. |
| `docs/EXECUTABLE_AND_OVERLAYS.md` | Maps adjacent runtime systems to *exclude*: the `0x8009c870` sprite-object pool, the `0x80096b98` 128-entity list, and `fcn.80025084` (oriented range/containment test — a geometry candidate that may belong to G5). |

**Boundary rule:** the type-`0x3f` construct path (`fcn.80053814` reading `0x80096e9c`) and the
contact array `0x800b0d18` are pickup systems — out of scope except where they help *distinguish*
pickups from geometry.

---

## 3. Known starting facts (CONFIRMED unless noted)

DAT parsing / relocation:
- `fcn.8001cdc0` parses DAT records and performs internal relocation (`field += DATbase`).
- Type-`0x3f` placement is fully understood (pickups).
- Naive append black-screened because trailing/internal geometry relocation offsets were stale.
- `tools/dat_reloc.py` reproduced the relocation walk; many relocated pointers point into the
  post-`0x3f` geometry region.
- `fcn.80017b98` (called from pass 1) sets up a GTE rotation matrix; it relocates **no** file
  pointers.

LEVEL01 top-level record layout (re-derived from the Phase-1 parser size rules against pristine
`DAT/LEVEL01_LEVEL.DAT`, sha1 `b376cb50…`, size `0x51418`; offsets match
`docs/DAT_FORMAT_AND_RELOCATION.md`):

| rec | file off | type | count | entry size | parser size | ends | role (confidence) |
|----:|---------:|-----:|------:|-----------:|------------:|-----:|-------------------|
| 0 | `0x0004` | `0x3f` | 70 | `0x10` | `0x464` | `0x0468` | pickups/placements — **SOLVED context** (CONFIRMED) |
| 1 | `0x0468` | `0x01` | 104 | `0x0c` | `0x4e4` | `0x094c` | UNKNOWN geometry/object record |
| 2 | `0x094c` | `0x0b` | 16 | `0x0c` | `0x0c4` | `0x0a10` | UNKNOWN |
| 3 | `0x0a10` | `0x0c` | 16 | `0x0c` | `0x0c4` | `0x0ad4` | UNKNOWN |
| 4 | `0x0ad4` | `0x0d` | 16 | `0x0c` | `0x0c4` | `0x0b98` | UNKNOWN |
| 5 | `0x0b98` | `-2` | 48 | packed | `0x130` | `0x0cc8` | UNKNOWN negative/packed |
| 6 | `0x0cc8` | `-3` | 88 | packed | `0x220` | `0x0ee8` | UNKNOWN |
| 7 | `0x0ee8` | `-4` | 64 | packed | `0x190` | `0x1078` | UNKNOWN |
| 8 | `0x1078` | `-5` | 65 | packed | `0x198` | `0x1210` | UNKNOWN |
| 9 | `0x1210` | `-6` | 56 | packed | `0x160` | `0x1370` | UNKNOWN |
| 10 | `0x1370` | `-7` | 64 | packed | `0x190` | `0x1500` | UNKNOWN |

- Negative-type entry size = `(((3*count+1)>>1)<<2)+0x10` (CONFIRMED parser rule).
- **Discrepancy RESOLVED in G1 (2026-06-13):** the older `DAT_FORMAT_AND_RELOCATION.md` wording
  "record 10 ... (bulk geometry blob to EOF)" is **SUPERSEDED**. rec10 (`-7`) is a fixed
  `0x190`-byte packed record ending at `0x1500`; the post-record word at `0x1500` is `0`, so the
  trailing block starts at `0x1504`. The geometry-heavy **data** lives *after* the trailing
  relocation tables, in `[0x45f0, EOF)`, reached only via baked offsets relocated by `fcn.8001cdc0`.
  See §6 of `src_re_geometry/level01_dat_geometry_inventory.md`.

Trailing relocation block (CONFIRMED via `tools/dat_reloc.py`):
- trail @ `0x1504`; pass 2 base @ `0x3ae8` (`[p2] = -1` → pass 2 EMPTY); pass 3 base @ `0x3aec`.
- Site counts: PASS 1 = 968 (484 `[s3+2]` + 174 `[s0+0x14]` + 310 `[s0+0x1c]`); PASS 2 = 0;
  PASS 3 = 280 (140 `[s3+2]` + 85 `[s0+0x14]` + 55 `[s0+0x1c]`). **Total 1248.**
- Relocated pointer **values** span `[0x45f0, 0x4f32c]`. First `P1.A [s3+2]` targets:
  `0x4680, 0x4698, 0x46b0, 0x4788, 0x47a0, 0x4a58, …`. First `P1.B [s0+0x14]` targets:
  `0xb32c, 0xc6c8, 0xd768, 0x13138, …`. So pass-1 source records cluster near `~0x45f0`; their
  `+0x14/+0x1c` sub-pointers reach deep into the blob (densest region the high `0x1xxxx–0x4xxxx`).
- Pass 1 / pass 3 tables likely build or reference runtime geometry/collision structures
  (LIKELY — they are the only DAT machinery that constructs transform records).

Parser geometry output (CONFIRMED from `dat_parser_8001cdc0.c`):
- Pass 1 writes **`0x20`-byte output records** to `DATbase + arg2` (`s4`), one per table entry.
  Each: `fcn.80017b98` fills a 3×3 GTE rotation matrix (9 × int16) at `out+0x00..0x10`; the bit3
  path then scales that matrix in place by per-axis scale halfwords `[s0+0x12/0x14/0x16]`; `out+0x18`
  = pointer to the source record `s0`. Output-record count → `G_DAT_ENTRY_COUNTER`; return =
  `count << 5` (bytes).
- Source record `s0` (in the geometry region) known fields: `+0x0c` rotation/angle inputs;
  `+0x12/0x14/0x16` scale halfwords (bit3 path); `+0x14`/`+0x1c` (+gated `+0x18/+0x20`) relocated
  pointers deeper into geometry data; `+0x16` second scale; coords/extents UNKNOWN.

Adjacent geometry-candidate consumer already seen (EXECUTABLE_AND_OVERLAYS.md):
- `fcn.80025084` — oriented bounding/containment test using rotation matrix `0x80090fb0`; "geometry,
  not collectible", render-vs-collision UNKNOWN. Candidate input for G4/G5.

---

## 4. Phase table G1–G6

| Phase | Goal | Primary file(s) | Status |
|------:|------|-----------------|--------|
| **G1** | DAT geometry inventory: document every LEVEL01 top-level record (type/count/offset/size/role/fixed-vs-packed) and cross-map relocation targets to record/blob ranges. | `src_re_geometry/level01_dat_geometry_inventory.md` | **ANALYZED (2026-06-13)** — record table CONFIRMED (records end `0x1500`); trailing tables CONFIRMED (pass1 484 @0x1512, pass2 empty @0x3ae8, pass3 140 @0x3afa); all 1248 reloc targets in `[0x45f0,0x4f32c]` (source band `[0x45f0,0x8bd8)`, payload band `[0x8bd8,0x4f32c]`); non-`0x3f` byte patterns recorded. Open: source-record stride/size conflict → G2. |
| **G2** | Parser geometry output model: extract the geometry-relevant parts of `fcn.8001cdc0` (pass 1/3 output records, the `0x20`-byte format, output-buffer/return relationship, globals written). Annotate; do **not** redo the parser decompile. | `src_re_geometry/dat_geometry_records.c` | **ANALYZED (2026-06-13)** — `0x18` vs `[s0+0x1c]` conflict RESOLVED: two source formats (non-bit3 `0x18` ptr@+0x14; bit3 `0x20` ptr@+0x1c + `scale[3]`), shared prefix `{vec[3];angle[3]}`. Pass-1 builds `0x20` `ParserOutputRecord20` (rot matrix + `+0x18` src ptr) into `DATbase+arg2`; pass-3 is relocation-only (no output record). Candidate structs recorded; not promoted to `re_types.h`. Open: arg2 base, consumers, payload-band, `+0x12`/`+0x18` scalars → G3. |
| **G3** | Runtime geometry buffers: identify buffers populated by parser output and candidate struct layouts (matrix records, source-geometry pointers, bounding/extent, collision records). RAM/global addresses only when code supports them; fields stay `unkNN`. | `src_re_geometry/geometry_runtime_buffers.c` | **ANALYZED (2026-06-13)** — caller `fcn.8003cf2c`@`0x8003d568` resolved: DATbase = heap cursor `[sp+0x98]`; **arg2 = file-reader return = DAT filesize**; output base = DATbase+filesize (LEVEL01 `0x801b1c10` LIKELY). Pass-1 array 484×`0x20`; return `(484+140)<<5` → **`0x1180` reserved-vs-written mismatch** documented. Source+payload bands live inside the DAT; output array after it. No role labels. Open: concrete DATbase, sector-padding, gap role → G4/G5. |
| **G4** | Render consumers: find functions that read parser-created geometry records to draw (search callers/refs of the output buffer, relocated geometry pointers, GTE matrix records). Geometry draw paths only. | `src_re_geometry/geometry_render_consumers.c` | **CONFIRMED render-stage terrain visibility path (G6 test 2026-06-14).** `fcn.800224ec` CONFIRMED scene/render driver reads `G_TRAIL_BLOCK_PTR`/`G_PASS3_BASE_PTR`, calls render loop `fcn.8003f938`, GTE matrix setup `fcn.80017b98`, and dispatches to GTE helpers `fcn.800140a0/80014360/800146e0`. G5.5 CONFIRMED `fcn.800140a0` reads pass-1 trail flag/sentinel fields at `DAT+0x1512`/`DAT+0x1526`. G6 patch `DAT+0x1526: 41 00 -> ff ff` caused major terrain/ground render disappearance/cutoff while game continued. Open: exact trail-field semantics and downstream GPU primitive stage. |
| **G5** | Collision/pathing consumers: find functions that consume geometry/collision data for player/world collision; distinguish render-only mesh from collision/pathing where evidence allows; identify candidate floor/wall/edge tests and coordinate systems. | `src_re_geometry/geometry_collision_consumers.c` | **ANALYZED (2026-06-14) — NEGATIVE, with G6 separation evidence.** No static parser-geometry collision consumer. Geom record-type slots `TT[0x01/0x0b/0x0c/0x0d/-2..-7]` have ZERO readers (only `TT[0x3f]`); only render driver reads `G_TRAIL/PASS3`; ~40 player-pos readers, none read geometry. G6 made terrain render mostly disappear, but Flik could still stand/move on the invisible/missing terrain in the tested area. This supports render/collision separation for `DAT+0x1526`, but the full collision/pathing pipeline remains **UNKNOWN**. |
| **G6** | Minimal geometry diagnostic edit: propose ONE minimal, reversible, single-field edit (move one vertex/point or alter one bounded record) with exact offset/orig bytes/new bytes/expected effect/revert plan. Only after G1–G5 yield a supported target. Do **not** build the ISO unless later instructed. | (proposal/build/result record in `GEOMETRY_RE_PLAN.md` §G6 + notes) | **RENDER-STAGE DIAGNOSTIC TEST SUCCEEDED (2026-06-14).** Read watches `0x80161d0a` and `0x80161d1e` hit in `fcn.800140a0` (DuckStation PC `0x80014174`, expected read site `0x80014170`), proving concrete LEVEL01 DAT-backed pass-1 trail flag/sentinel fields are read at runtime. G6 sentinel test patch `DAT+0x1526: 41 00 -> ff ff` caused major terrain/ground render disappearance/cutoff with no crash; Flik/objects/enemy/props still loaded, and tested terrain collision remained usable. Collision/pathing remains **UNKNOWN**; no collision-aware G6. |
| **G7/G8** | Render-body field identification and controlled entry24 render-body perturbations. | `src_re_geometry/geometry_g55_dynamic_watch.md`, `geometry_render_consumers.c` | **G7 read coverage COMPLETE / G8 small-perturbation tests COMPLETE (2026-06-14).** Reinspection of `fcn.800140a0` shows it scans every nonnegative `entry+0x0e` flag, but reads body fields only when the runtime visibility bitmask byte at `0x800901c8 + (entry>>3)` has bit `0x80 >> (entry&7)` set. Entry19 `+0x00` and entry19 `+0x0c` remain **ZERO-HIT / NOT ELIGIBLE YET**. Entry24 is a CONFIRMED non-sentinel DAT-backed render body row, LIKELY location/view gated, semantics UNKNOWN, collision UNKNOWN. Path A CONFIRMED all entry24 body reads by `fcn.800140a0` at `a0=0x80161ef0`: `+0x00` `DAT+0x16e4` read site `0x8001419c`, `+0x08` `DAT+0x16ec` read site `0x800141a0`, `+0x0c` `DAT+0x16f0` read site `0x800141a4`, `+0x04` `DAT+0x16e8` read site `0x80014258` (non-negative `+0x0c` branch). G8 Candidate A (`+0x08`, `+256`), A2 (`+0x08`, `+1024`), and C (`+0x04`, `+1024`) were all valid builds; A and C had CPU data reads CONFIRMED, and A2 had CPU read plus live RAM confirmation. All three showed **NO OBVIOUS VISUAL CHANGE** in the tested edge-of-level area. Conclusion: small same-sign perturbations of entry24 body fields are valid and read but visually imperceptible; this does not disprove render-body relevance, but continued blind/small entry24 body-word perturbations are low-yield. **Next phase: G9 dataflow tracing**, not another small entry24 perturbation. Artifacts gitignored/not committed. |
| **G10** | Survivor-list consumers + payload/primitive render chain: who consumes LIST_A/LIST_B and where survivors become drawn geometry; locate the actual visible-geometry edit target. | `src_re_geometry/geometry_g10_payload_render_chain.md`, `geometry_render_consumers.c` | **CONFIRMED by static ISO disasm (2026-06-14); see §4.4.** Consumers are **`fcn.8001ea6c`** and **`fcn.800206e8`** (per-survivor primitive builders). Each walks LIST_A, BRIDGES `row+0x10`→output record→`+0x18`→source record, transforms source `vec[3]` by the camera matrix, dispatches by row-kind (`flag&0x9f6f`) via jump tables, and packs primitives into GPU/OT buffer `[0x8008240c]`. **Corrections:** `fcn.800146e0` is a libgte camera-matrix load *leaf* (not a projection stage); `0x80060484/0x800605c4` are libgte matrix helpers (not libgpu submit); the RTPT @`0x80014970` is a separate contact-array (`0x800b0d18`) path. Bridge byte-traced to payload band `[0x8bd8,0x4f32c]` (u32 count + s16 vertex triples). **Runtime (§4.4, 2026-06-14):** READ `0x80167b80` + EXEC `0x8001eb34` CONFIRMED dispatch to builder case `0x8001ec44`; that case decoded — reads source `vec[3]`/`angle[3]`/`scale[3]`/attr/payload-ptr `[s2+0x1c]`, scales LUT matrix `@0x80089528`, tail-calls emitter `fcn.80010000` (payload=`{u32 count;vertex[]}`). `scale[3]`/`angle[3]` now CONFIRMED read by the runtime builder. Edit candidates (proposal only, survivor entry29): source `vec[3]` @`0x7388`, `scale[3]` @`0x739a`, `angle[3]` @`0x7394`, payload vertex @`0x2f2f8`. Next: decode `fcn.80010000` primitive format. |
| **G11** | Decode the payload reached via source `+0x1c`: vertex format, primitive command stream, and the emitter `fcn.80010000`. | `src_re_geometry/geometry_g11_payload_format.md`, `geometry_render_consumers.c` | **CONFIRMED by static ISO disasm (2026-06-14); see §4.5.** `fcn.80010000` = per-object mesh draw: reads payload count, then a primitive **command stream** (`type=ctrl&0x1f` → jump table `@0x8001036c`); type-0 case `0x8001046c` = triangle (RTPS `0x4a180001` / RTPT `0x4a280030` project, NCLIP `0x4b400006` backface-cull, screen/Z clip, pack polygon to OT). Payload layout: `{u32 vertexCount; Vertex verts[N] stride 0xc = (s16 x; s16 y; s16 z; s16 pad=0; u32 attr); command stream}`; vertices referenced by byte offset. `0x80060284` = GTE per-point transform helper (not libgpu). entry29 `DAT 0x2f2f8` count 34, v0=(0,-744,-61); entry0 `0xb32c` count 195. Edit targets (survivor entry29): source `vec[3]` `@0x7388`, `scale[3]` `@0x739a`, payload vertex `@0x2f2fc`. |
| **G12** | First real visual-geometry edit: reversibly translate a surviving object via its source `vec[3]` and build a test image. | `src_re_geometry/geometry_g11_payload_format.md` §5.1, `tools/patch_g12_entry29_source_vec_test.py` | **RESULT 2026-06-14: VALID BUILD / PATCH LIVE / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE; see §4.6.** Candidate VEC = entry29 source `vec[0]` `DAT 0x7388` `-10000`→`-8976` (`+1024`). `READ 0x80167b80` hit in `fcn.8001ea6c` case `0x8001ec44`; live mem `0x80167b80`=`FFFFDCF0` (matches patch); but no obvious visual change vs pristine. Source-origin nudge is visually silent here (does NOT disprove the payload path). **Next: payload-vertex deformation (G13), not another source-vec delta.** |
| **G13** | Direct mesh deformation: reversibly move one s16 coordinate of one payload vertex of a surviving object and build a test image. | `src_re_geometry/geometry_g11_payload_format.md` §5.2, `tools/patch_g13_entry29_payload_v0_test.py` | **RESULT 2026-06-14: VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL CHANGE; see §4.7.** Candidate PV0 = entry29 payload vertex 0 `y` `DAT 0x2f2fe` `-744`→`-232` (`+512`). Initial watch on inner s16 `0x8018faf6` missed; re-watch on aligned vertex base `0x8018faf4` hit at PC `0x80010928` (`lwc2`) in `fcn.80010000`. Vertex is read, but v0.y `+512` visually silent. **Lesson: watch the aligned `lwc2` base, not the inner s16. Next: command-stream-selected vertex + larger delta (G14).** |
| **G14** | Pick a payload vertex by primitive-command reference + silhouette analysis (not a guess) and deform it with a larger delta. | `src_re_geometry/geometry_g11_payload_format.md` §5.3, `tools/patch_g14_entry29_payload_vertex_test.py` | **RESULT 2026-06-14: VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / VISIBLE RENDER CHANGE / NON-TANGIBLE DECORATION; see §4.8.** Candidate PV14 = entry29 vertex 14 `y` `DAT 0x2f3a6` `-1601`→`-2625` (`-1024`). **First confirmed visible payload-vertex edit** — proves the payload-edit method end-to-end. Affected object is grass/decorative foliage (non-tangible). entry29 is a poor target for terrain; **pivot to a ground payload (G15)**. Collision/pathing UNKNOWN (not inferred). |
| **G15** | Identify a terrain/ground render payload (vs grass/decor), confirm the on-screen ground at runtime, then deform one of its vertices. | `src_re_geometry/geometry_g15_terrain_payload_candidates.md`, `tools/survey_level01_payloads.py`, `tools/patch_g15_runtime_payload_vertex_test.py` | **RESULT 2026-06-14: VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL CHANGE; see §4.9.** Runtime `a0`-log at `fcn.80010000` rejected the static primary `0x8018c234` (instanced decor); picked wide+flat unique `0x80170978` (DAT `0x10180`). TERRAIN-PV = vertex 46 `y` `DAT 0x103ae` `7302`→`6278` (`-1024`). CPU: READ `0x80170ba4` hit at PC `0x8001069c` (`lwc2`) in `fcn.80010000`. No visible change — read-confirmation (at the `lwc2` load, **before** reject tests) is not enough; need screen-space evidence (G16). Collision/pathing UNKNOWN. |
| **G16** | Select a vertex with screen-space evidence (projects on-screen + survives to an emitted primitive), not just DAT metrics. | `src_re_geometry/geometry_g16_screen_space_vertex_selection.md`, `tools/patch_g16_emitted_payload_vertex_test.py` | **VISIBLE WALL RENDER CHANGE CONFIRMED 2026-06-14; see §4.10.** Image `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue` boots, LEVEL01 loads, no crash/black screen; a **visible deformation** appeared on a **vertical wall/cliff face — NOT the walkable floor**. Classification **VALID BUILD / PATCH LIVE / EMITTED PAYLOAD CONFIRMED / VISIBLE WALL RENDER CHANGE**; payload `0x356bc` **reclassified wall/vertical terrain face** (not floor/top-surface). Confirms payload-vertex edits visibly deform terrain-family render geometry. Runtime EXEC `0x800108b4` (packet-store gate) log: payload `0x356bc` (= static e128, rt `0x80195eb4`) emitted ≥5 primitives in the ground view; `0x1b9f0` ≥2. (`a0`@`0x800108b4` = vertex-table ptr → payload = `a0−4`. Correction: `t5/t6/t7` there are packet/OT words, not SXY — read packet at `s3` for screen coords; mapping = TODO.) Candidate EMITTED-PV = `0x356bc` vertex 10 `y` `DAT 0x3573a` `b9 1a` (`6841`) → `b9 16` (`5817`, `-1024`, one byte; central vertex of an observed-emitted quad). Patched DAT SHA256 `96206e69…`; image `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue`; embedded verified at LBA 2906 (`@0x3573a`=`b9 16`); staged restored to pristine. Artifacts gitignored/not committed. Collision/pathing UNKNOWN — visual terrain ≠ collision; **not** a floor collision edit. **Next: G17 walkable floor/top-surface payload (§4.11).** |
| **G17** | Find a **walkable floor/top-surface** render payload using emitted-primitive evidence (EXEC `0x800108b4`), filtering for a flat horizontal floor (broad X/Z, low local Y band, top surface Flik stands on) — not a vertical wall/cliff (G16 `0x356bc`) or grass/decor (`0x2f2f8`). | `src_re_geometry/geometry_g17_floor_payload_candidates.md` | **RUNTIME RESULT 2026-06-14 — emitted floor is an OUTPUT-BUFFER/HEAP payload; see §4.11.** Candidate B log (broad floor view, EXEC `0x800108b4`): all 17 hits = one payload `a0=0x801bdc5c` → base **`0x801bdc58`** = DAT off `0x5d460` **INVALID** (`>0x51418` EOF), output-buffer offset `0xc048`. Classification **EMITTED FLOOR/TOP-SURFACE CANDIDATE / RUNTIME-GENERATED OR OUTPUT-BUFFER PAYLOAD / DAT SOURCE UNKNOWN**. The walkable floor is **not** a LEVEL.DAT payload → static floor shortlist (e135/e254/e52/`0x1b9f0`) superseded for this view. → **G18 trace.** Collision/pathing UNKNOWN. **⚠ RETRACTED by G26 (§4.21): `0x801bdc58` is compressed LEVEL.RAW source, not an emitted payload — Candidate B was never count-validated; real floor pointer UNKNOWN.** |
| **G18** | Trace runtime floor payload `0x801bdc58` to its DAT source or generator: writers to the output region, parser/generator paths, source-record/list-row linkage, content match to any DAT band. | `src_re_geometry/geometry_g18_output_buffer_floor_trace.md`, `geometry_g18_dat_backed_floor_candidate.md`, `geometry_runtime_buffers.c` | **STATIC TRACE + RUNTIME RUNBOOK 2026-06-14; see §4.12/§4.13.** CONFIRMED: parser `fcn.8001cdc0` runs **once** (LEVEL.DAT only); all 1248 reloc targets in `[0x45f0,0x4f32c]` (max `<< 0x5d460`); emitter loads `a0` **directly** from `[s2+0x1c]`/`[s2+0x20]` with **no base add** (`0x80020684/0x80020694`). So `0x801bdc58` is **not** a parser-relocated LEVEL.DAT pointer; it is written at runtime (generator) or `s2` is heap-resident. LEVEL01 ships separate terrain resources (`LEVEL.RAW`/`TERRAIN.ALL`/`TERR1.ALL`, s16-coord streams) that land in the "next resource" heap region (`0x801b6a10+`) where `0x801bdc58` sits. **DAT source NOT found** (floor is not in LEVEL.DAT). Next: narrow runtime **WRITE watch `0x801bdc58`** during load + read `s2` at `0x80020684` (DAT-vs-heap source). **§4.13 (2026-06-14):** a *Candidate B-LIKE* view (very close, not pixel-identical) emitted a **DAT-backed** payload `a0=0x8018dc5c`→base `0x8018dc58`→DAT **`0x2d460`** (VALID); static decode = small (202×107×194) closed blob, **93 pass-1 references → instanced decor/prop, NOT floor** (operator's runtime "floor candidate" read superseded). No floor target; **no build**. Collision/pathing UNKNOWN. **⚠ G26 (§4.21): the premise "trace floor payload `0x801bdc58`" is RETRACTED — `0x801bdc58` is compressed LEVEL.RAW source (never written; Press-X `0x70d4001a`). The parser-once / reloc-`<0x4f32c` / direct-`[s2+0x1c]` facts here stand; the floor pointer is UNKNOWN.** |
| **G19** | Pivot from reproducing runtime floor pointer `0x801bdc58` (not reliably reproducible) to identifying the floor/terrain **resource/source**: inventory LEVEL01 sidecars, classify headers, find the loader/parse path, determine whether a separate resource produces the heap floor geometry. | `src_re_geometry/geometry_g19_floor_resource_source.md`, `geometry_runtime_buffers.c` | **STATIC RESOURCE INVENTORY + LOADER TRACE + RUNTIME-CHECK PROPOSAL 2026-06-14; see §4.14.** `0x801bdc58` reclassified **OBSERVED ONCE / NOT REPRODUCIBLE** (DuckStation GUI has no conditional BP); `0x2d460` decor is the reproducible nearby hit. Sidecars: `LEVEL.RAW`/`LEVEL1.RAW` **compressed**; `TERRAIN.ALL`/`TERR1.ALL` **s16 (x,z) streams**; `LEVEL.BIN`/`LEVEL1.BIN` **overlay code**; **`LEVEL1.DAT`/`LEVEL2.DAT` are parser-format DATs that CONTAIN wide-flat floor-signature payloads** (LEVEL.DAT does not). Loader `fcn.8003cf2c` = resource-id dispatcher (17 handlers, 4 callers) → shared file-read `fcn.80046330` + parse `fcn.8001cdc0` → **CORRECTION: parser runs once PER DAT, not once total** (4 loader callers), so a 2nd parsed DAT lands in the `0x801bxxxx` heap. **LIKELY floor source = a second parsed DAT (LEVEL1/LEVEL2.DAT)**; exact file+offset UNKNOWN (no naive base matches). Next: deterministic loader trace (EXEC BP `0x8003d550`/`0x8003d568` log filename→base) — no `a0` reproduction. No patch/build. Collision/pathing UNKNOWN. |
| **G20** | Loader-trace result + non-circular sidecar tracing: the LEVEL.DAT load BP confirmed only the known path, so map the OTHER resource loaders (terrain `.all`, memory.bin, fmv, audio, decompressors) and recommend one deterministic floor-source runbook. | `src_re_geometry/geometry_g20_sidecar_loader_trace.md`, `geometry_runtime_buffers.c` | **STATIC LOADER MAP + RUNTIME-RUNBOOK 2026-06-14; see §4.15.** Operator trace: `EXEC 0x8003d550`/`0x8003d568` each hit **once**, `a1=0x51418` = LEVEL.DAT → **parser `fcn.8001cdc0` runs exactly once for LEVEL01** → **G19 H1 (second parsed DAT) REFUTED**; G18 "parser once" re-vindicated. Mapped all 14 `fcn.80046330` file-reads: only `0x8003d550` is the DAT/parse path; the rest bypass the parser. **Prime non-circular target = the post-DAT terrain `.all` loader `fcn.8002ffa8`** (file-read `0x8002ffe4`/`0x80030dc0`; builds `terr*/terrain.all` from name table `0x80082128`; loads into the **heap cursor** region where the floor `0x801bdc58` sits; processes via `fcn.8002fce8` → `0x4c`-stride records `0x80098a8a`), orchestrated by `fcn.8005d654` (16 callers). `.ALL` = s16 (x,z) streams (not verbatim payloads) → floor is **runtime-generated**. **H2 (terrain `.all` → generated floor) now LEADING.** Runbook: EXEC `0x8002ffe4`(+`0x80030dc0`) log filename/dest/size; test `a1 ≤ 0x801bdc58 < a1+size`. No patch/build. Collision/pathing UNKNOWN. |
| **G21** | G20 correction + broader file-read caller analysis: the proposed terrain `.ALL` BPs did not fire, so enumerate ALL `fcn.80046330` callers, classify, map to sidecar files, and recommend one callee-entry runbook. | `src_re_geometry/geometry_g21_file_read_caller_map.md`, `geometry_runtime_buffers.c` | **NEGATIVE RESULT + FULL CALLER MAP + RUNBOOK 2026-06-14; see §4.16.** Operator: `EXEC 0x8002ffe4`/`0x80030dc0` **0 hits** → G20 terrain-`.all` "prime target" **REFUTED** (H2 downgraded to open). Two structural misses: orchestrator `fcn.8005d654` **skips file-read if terrain cached** (`bnez` @`0x8005d76c`), and high-heap loader **`fcn.8003a318`** (read `0x8003a388`, dest **`0x801cc390 − size`** top-down) is reached **indirectly** (no call-site BP can catch it; its region can **contain** `0x801bdc58`). Mapped all **14** `fcn.80046330` callers → 11 fns (LEVEL dispatcher `fcn.8003cf2c`/`0x8003d550` = all `level*.dat/raw/bin`, fired LEVEL.DAT ×1; memory.bin; FMV; audio; anm; terrain `.all` no-hit; high-heap). **Loader signature `fcn.80046330(a0=filename,a1=dest)`** = universal choke point. **Runbook: EXEC `0x80046330` (entry)** — log `a0`(name)/`a1`(dest)/`ra`(caller)/`v0`(size) for every load; test `a1 ≤ 0x801bdc58 < a1+size`. No patch/build. Collision/pathing UNKNOWN. |
| **G22** | High-heap floor-load bracketing + source-file identification: the `EXEC 0x80046330` runbook caught the load whose range contains `0x801bdc58`; identify the file and inspect the source offset. | `src_re_geometry/geometry_g22_high_heap_floor_source.md`, `geometry_runtime_buffers.c` | **BRACKET CONFIRMED + SOURCE FILE = LEVEL.RAW 2026-06-14; see §4.17.** Operator `EXEC 0x80046330` **Hit #4** (`ra=0x8003a390` = indirect high-heap loader `fcn.8003a318`): dest **`0x80115aac`**, size `0xb6be4`, range `[0x80115aac,0x801cc690)` **brackets the floor `0x801bdc58`** at source offset **`0xa81ac`**. The dest-size = `0x801cc390−0x80115aac` = **`0xb68e4` = LEVEL.RAW's exact size** → **source file = LEVEL.RAW** (next-closest sidecar 207 KB off). **BUT** `LEVEL.RAW[0xa81ac]` `u32=0x70d4001a` is **not** a valid payload count (it's an indexed-geometry stream); the floor emitted a valid payload at runtime → **floor is CONVERTED/GENERATED from LEVEL.RAW at runtime, not verbatim at `0xa81ac`** (so NOT directly editable). Hit #6 control = LEVEL.DAT (`0x801607f8`), doesn't bracket. Next (Option A): read-only decode of LEVEL.RAW's geometry format + one deterministic confirm (read `a0`="level.raw", compare `0x801bdc58` post-load to disk). No patch/build. Collision/pathing UNKNOWN. |
| **G23** | Read-only decode of `LEVEL.RAW` around the floor offset `0xa81ac`: byte/word grammar, record boundaries, coordinate-vs-index-vs-compressed classification, candidate editable source fields. | `src_re_geometry/geometry_g23_level_raw_floor_format.md`, `geometry_runtime_buffers.c` | **LEVEL.RAW IS COMPRESSED; floor = decompressor OUTPUT 2026-06-15; see §4.18.** `LEVEL.RAW[0xa81ac]` is **compressed bytes** (213 distinct/1024, high entropy; no s16 structure; **0** clean `fcn.80010000` payloads anywhere in the file). The G22 loader `fcn.8003a318` calls **`fcn.8001a1dc`** = an **LZ/Huffman bitstream DECOMPRESSOR** (`a0`=LEVEL.RAW `0x80115aac` compressed in, `a1`=`[gp+0x588]` decompressed out; full reg-context save; BE control words; literal-copy `0x8001a418` + back-ref `0x8001a658`; no GTE; single caller). So the floor `0x801bdc58` is the **decompressor's output**, and `0xa81ac` is the compressed byte that loads at that address — **NOT a coordinate, NOT editable** (corrects G22's "indexed-geometry stream"). **No safe edit target** (compressed). Next: **EXEC `0x8001a1dc`** read `a0`(src)/`a1`(dst)/size → confirm the floor is in the decompressed output region. No patch/build. Collision/pathing UNKNOWN. |
| **G24** | Decode the `LEVEL.RAW` decompressor `fcn.8001a1dc` enough for an offline decoder or a precise runbook; document the compression grammar. | `src_re_geometry/geometry_g24_level_raw_decompressor.md`, `geometry_runtime_buffers.c` | **GRAMMAR PARTIAL; ground-truth runbook 2026-06-15; see §4.19.** `fcn.8001a1dc` (`0x8001a1dc..0x8001a8f8`) = custom **LZSS/LZ77 + variable-length-code** decompressor: full reg-save; `0xe`-byte header (`word0`/`word1` BE, both **computed-then-dead**); `v1=src+0xe` cursor; **MSB-first guard-bit reader**; main loop `0x8001a658` flag bit (0=inline literal byte, 1=match); match = var-len length code (escape@9→`N×4` literal run; long byte; **byte==0=TERMINATOR**) + 16-bit distance (hi bits coded + low byte inline) → back-ref `out−dist−1`; **bit-driven termination** + (no-op) scratch flush. **Structure CONFIRMED with PCs; exact length/distance code tables + `word0`/`word1` meaning NOT byte-exact** → per task, **no decoder invented**. Next: **EXEC `0x8001a1dc`** capture `a0`(src)/`a1`(dst)/return → dump decompressed output (ground truth); floor decompressed offset = `0x801bdc58 − dst` (≠ compressed `0xa81ac`). No patch/build. Collision/pathing UNKNOWN. |
| **G25** | Record the `EXEC 0x8001a1dc` runtime result and statically trace the **post-decompression** path: the loop that calls the decompressor, where each decompressed chunk is consumed, and any builder/copy/convert path that could create the high floor payload near `0x801bdc58`. | `src_re_geometry/geometry_g25_level_raw_post_decompress_trace.md`, `geometry_g24_level_raw_decompressor.md`, `geometry_runtime_buffers.c` | **PER-CHUNK DECOMPRESS LOOP CONFIRMED; FLOOR IS POST-DECOMPRESSION-BUILT 2026-06-15; see §4.20.** Operator `EXEC 0x8001a1dc` = **many hits** (`ra=0x8003a4ec`, `gp=0x80081d98`) → the decompressor runs in a **per-chunk loop in `fcn.8003a318`** (single call site `0x8003a4e4`, looped). Loop: head `0x8003c29c` (read `s5[0..3]`; `ff ff ff ff`=terminator→finalize `0x8003c2dc`) → body `0x8003a4d4` `jal 0x8001a1dc(a0=s5,a1=fp)`, `s4=fp[0]`=**chunk subtype**, dispatch `0x8003a4ec..0x8003c250` consumes the decompressed chunk (`s3=fp`) + builds a resource, `fp += align4(word0)` per case, tail `0x8003c250` `s5 += word1+0xe`. **Resolves G24:** once-vs-per-block → **per-block**; `word0`/`word1` "dead" words are **caller-live** = per-chunk **decompressed**/**compressed** sizes. **Source bracket for `0xa81ac`:** chunk `a0=0x801bd58f`→`0x801bf662` contains the floor addr at `+0x6c9`; its decompressed `a1=0x80143438`→`0x80147500`. **DECISIVE NEGATIVE:** `a1`/`fp` tops at `0x8015fcbc`; floor `0x801bdc58` is `+0x5df9c` above → **floor is NOT decompressor output** — it is **built post-decompression** in `[final-fp,high-top 0x801cc390)` (`top−0xe738`) by a subtype-case builder (`fcn.8003cc58`/`0x800628c0`/`0x800625fc`/`0x80061a48`) and/or a later converter; exact writer UNKNOWN. Operator's "odd final row" `pc=0x8003f33c` = GPU/DMA spin-wait (excluded). Next: **WRITE watch `0x801bdc58`** (writer PC) + **EXEC `0x8003a4ec`** (per-chunk subtype log). No patch/build. Collision/pathing UNKNOWN. **⚠ SUPERSEDED by G26: `0x801bdc58` is compressed source, not the floor — the "floor built post-decompression near `0x801bdc58`" inference is dropped (the per-chunk-loop / `word0`/`word1` LEVEL.RAW findings stand).** |
| **G26** | Correction/pivot: operator ground truth shows `0x801bdc58` is compressed LEVEL.RAW source, not a render payload. Reclassify it, preserve the LEVEL.RAW findings, re-audit the `0x800108b4`/`a0−4` evidence, and give a count-validated runbook to re-find the real floor payload from the consumer side. | `src_re_geometry/geometry_g26_floor_payload_reaudit.md`, `geometry_g22..g25` + `geometry_runtime_buffers.c` + `geometry_notes.md` | **`0x801bdc58` RECLASSIFIED = COMPRESSED LEVEL.RAW SOURCE; FLOOR PAYLOAD POINTER UNKNOWN; see §4.21.** Operator: at `Press X to Continue` `[0x801bdc58]=0x70d4001a` (= `LEVEL.RAW[0xa81ac]`) and **WRITE watch `0x801bdc58` during load = 0 hits** → never written, still compressed at Press X. **Acceptance test fails:** count `0x70d4001a` (~1.9 B) is impossible and the bytes are compressed (G23). **Re-audit (disasm):** the `a0−4` payload-base formula is **correct** (`a0`=vertex base, never rewritten in the count>0 path of `fcn.80010000`; `s5` is reused), so the bug is **not** the formula — the G17 Candidate B hits were **never count-validated**; a real `fcn.80010000(0x801bdc58)` (count `0x70d4001a`) cannot emit 17 clean primitives → those hits did not map to a floor payload (wrong context/timing/stale `a0`). **RETRACTS** G17 Candidate B + the "floor at `0x801bdc58`" framing of G18/G19/G22/G25; **PRESERVES** the LEVEL.RAW load/decompress RE (G22 `0x801bdc58=LEVEL.RAW+0xa81ac` now *proven*; G23 compressed; G24/G25 per-chunk decompress loop + `word0`/`word1`). **Real floor render payload pointer = UNKNOWN.** Next (count-validated, consumer side): PRIMARY **EXEC `0x80010000`** (`a0`=raw payload base; validate `[a0]`=plausible count; dump `0x40` bytes; record `ra`); SECONDARY **EXEC `0x800108b4`** (`payload=a0−4`, cross-check count, `s3` packet screen-XY / `0x80010718` SXY → floor = lower-center). Classify `P`: DAT-backed (`P−0x801607f8∈[0,0x51418)`) / LEVEL.RAW-decompressed (`P<0x8015fcbc`) / generated. No patch/build. Collision/pathing UNKNOWN. |
| **G27** | Document + statically classify the five count-validated `fcn.80010000` payloads (A–E) the operator captured at `EXEC 0x80010000` in the Candidate-B floor view; decode each (count, vertex table, bbox, flatness, command refs, instancing), prioritize A, classify floor/wall/decor, recommend ONE next experiment. No patch/build. | `src_re_geometry/geometry_g27_count_validated_floor_candidates.md`, `geometry_g26_floor_payload_reaudit.md` + `geometry_runtime_buffers.c` + `geometry_notes.md`, `tools/analyze_g27_floor_candidates.py` | **5 GENUINE PAYLOADS DECODED; CANDIDATE A = STRONGEST FLOOR/TOP-SURFACE; see §4.22.** All five **pass the G26 §2 acceptance test** (`[a0]` = claimed count exactly 83/48/58/36/25; `pad==0` 100%; clean `ffff ffff` terminators; all verts referenced) and **all are DAT-backed** (`P−DATbase∈[0,0x51418)`) — genuine, unlike `0x70d4001a`. Decoder validated: **E reproduces the committed G18b `0x2d460` decode** (25v, 202×107×194, flat 0.53, **93 refs**). Split by structure (not screen-visibility): **A/B/C = flat, wide, WORLD-space chunks in one shared Y≈4400–5200 stratum** (floor family); **D/E = MODEL-space-centered objects** (prop/decor; E instanced ×93). **A (`DAT 0x188cc`, 83v, flat 0.154, Y-band 316, 4502×4502, unique) = strongest floor/top-surface** — flatter than the whole prior static shortlist (e135 0.19) and **DAT-backed → directly editable** (the property the retracted heap `0x801bdc58` lacked). B = smaller adjacent floor tile (0.260); C = floor tile with edge relief/ramp (0.365); **D rejected as floor** (flat 0.568, big Y relief, model-space, distinct −Y stratum → wall/structural-or-prop, role UNKNOWN); E = confirmed instanced decor. **Downgrades** the G17/G18 "floor not in LEVEL.DAT" inference (it rested on the retracted `0x801bdc58`) — the floor-view emit *does* surface DAT-backed floor-shaped payloads; whether A is the *walkable* surface vs a co-planar visual chunk is **UNKNOWN**. NEXT (ONE read-only BP): **EXEC `0x800108b4`** filtered to `a0==0x801790c8`, read `s3`-packet screen-XY (or `0x80010718` SXY) → confirm A's survivors land in the **lower-center walkable band** before any edit. Contingent edit spec ready (A v16 `y` @`DAT 0x18992` `89 13`→`89 17`, +1024) but **NOT built**. No patch/build. Collision/pathing UNKNOWN — visual ≠ tangible. |
| **G28** | Document Candidate A runtime READ + projection-path confirmation (the G27 §5 gate, consumer side); prepare AND build the guarded same-size visual diagnostic image (no visual result yet). | `src_re_geometry/geometry_g28_candidate_a_runtime_confirmation.md`, `geometry_g27_count_validated_floor_candidates.md` + `geometry_runtime_buffers.c` + `geometry_notes.md`, `tools/patch_g28_candidate_a_floor_y_test.py` | **CANDIDATE A = CONFIRMED DAT-BACKED VISUAL TERRAIN/FLOOR PAYLOAD — image built + OPERATOR-TESTED → VISIBLE TERRAIN DEFORMATION; see §4.23.** READ watch `0x801790c8` (A vertex base) hit **repeatedly** in the active render path (`a0=0x801790c8`, `ra=0x800206a0`, payload base `a0−4=0x801790c4`, count 83). **EXEC `0x80010718`** (post-`mfc2 SXY0/1/2`) hit while A active: prim1 `SXY0=0x007A0164/SXY1=0x00730182/SXY2=0x007B0180`; prim2 `SXY0=0x007F01A8/SXY1=0x007701CF/SXY2=0x008501F1` — unpacked `(Y<<16)|X` → **Y≈115–133 = central/lower-central band** (plausible floor projection); X≈356–497 raw (horizontal viewport mapping = TODO, G16). Classification **VALID DAT-BACKED PAYLOAD / RUNTIME READ CONFIRMED / PROJECTION PATH CONFIRMED / LIKELY VISUAL FLOOR/TOP-SURFACE / TANGIBILITY UNKNOWN.** `0x801790c4` (Candidate A) is kept **distinct** from the retracted `0x801bdc58` (compressed LEVEL.RAW source, G26 — never written, not a payload). Guarded same-size reversible edit `tools/patch_g28_candidate_a_floor_y_test.py` (LEVEL01/LEVEL.DAT @ `0x18992`, A v16 `y`, `89 13`→`89 17`, +1024, single byte; revert `89 13`; `0x51418` same-size; never in place; no collision/pathing files) **was BUILT** into `ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue` via the shared `rebuild_with_patched_dat.py`; embedded DAT verified at LBA 2906 (sha1 `a1cf8d8e…`), staged workspace restored to pristine, artifacts gitignored/not committed. **Operator test (2026-06-15): boots/LEVEL01-load YES; the tested floor/terrain VISIBLY DEFORMS (caves inward, angle-dependent) in A's projected area; Flik/objects still render; collision/pathing did NOT align with the deform.** Candidate A reclassified **CONFIRMED DAT-backed VISUAL terrain/floor render payload** (not decor/prop); **visual terrain payload ≠ collision/pathing source** (the deform did not move/align collision; tangibility UNKNOWN). Collision/pathing UNKNOWN — visual ≠ tangible; do not infer. **NEXT: G29 collision/pathing source discovery.** |
| **G9** | Trace entry24 values after `fcn.800140a0` reads them; produce a field-by-field dataflow runbook/table, not a patch. | `src_re_geometry/geometry_g9_entry24_dataflow.md`, `geometry_g55_dynamic_watch.md`, `geometry_render_consumers.c`, `geometry_notes.md` | **RUNTIME REJECT RESULT RECORDED (2026-06-14).** Static trace shows entry24 `+0x00/+0x04/+0x08` are paired as a view-relative vector and `+0x0c` acts as an extent/range term through `SQR`/`MVMVA` reject testing. Runtime stepping from `READ 0x80161ee0` confirmed entry24 passes the first reject test at `0x80014280` (`s3=0xffff262b`, branch not taken) but rejects at `0x800142b0` (`t0=0x000010b1`, branch back to `0x80014170` taken). Therefore entry24 is read and participates in GTE/math reject testing, but in this tested state it does not reach the late list-write path. This explains why G8 A/A2/C were valid/read yet visually unchanged. Late write observation with `t0=0x80161f40` was another row, not entry24; it maps cleanly to pass-1 entry29, DAT row `0x1748` (`+0x04=0x174c`, `+0x08=0x1750`, `+0x0c=0x1754`). **Next: G9b**, find/map a row that survives to `0x8001430c` or `0x80014320`, then test visible effect. |
| **G29** | Collision/pathing SOURCE discovery for the G28-confirmed VISUAL floor (Candidate A). Static recon of likely floor-contact/collision state, then a runtime-watch RUNBOOK comparing standing/walking over normal floor vs over the G28 deform to isolate state that does NOT follow the visual mesh. Analysis + plan only. | `src_re_geometry/geometry_g29_collision_source_plan.md`, `geometry_collision_consumers.c`, `geometry_runtime_buffers.c`, `geometry_notes.md` | **ANALYSIS + RUNTIME-WATCH PLAN 2026-06-15 — NO patch/build/run.** Carries the G28 split (visual terrain payload ≠ collision/pathing source; collision UNKNOWN, not assumed in A/LEVEL.DAT/LEVEL.RAW). G5 negative re-affirmed → collision query uses a non-global pointer or non-parser source → **runtime-first**. Candidate targets: player Y `0x800a6504` (writer-of-Y UNKNOWN; contradiction — G5 names `fcn.8005b134` sole writer vs EXEC-doc L409 writers `fcn.80047284/80048138/8004a700/800563d4/80056f68/8005b12c` → WRITE watch decides); `fcn.80025084` oriented containment (wall/ledge candidate, role UNKNOWN); `PAD\PATH*.BIN` via loader `fcn.80046330` (LIKELY AI pathing, not floor); EXCLUDE pickup walker `fcn.800586b0`/`0x800b0d18` (−0x1cc0 Y bias). Runbook: **P1** WRITE-watch `0x800a6504` → Y-writer PC; **P2** EXEC that PC → floor-height operand `S`, classify band; **P3 (decisive)** READ-watch `S` pristine vs G28-deformed patch → identical ⇒ `S` CONFIRMED floor source, independent of A; **P4** EXEC `0x80046330` → sidecar/PATH buffer bracketing `S`; **P5** EXEC `0x80025084` on wall/ledge. False-positive guardrails recorded (render path ≠ collision; visual ≠ tangible; `0x801bdc58` stays compressed source; no LEVEL.RAW/LEVEL.DAT collision assumption). Next runtime action: **P1 WRITE watch `0x800a6504`**. Collision/pathing UNKNOWN. **P1 RESULT (2026-06-15, operator ran PRISTINE WRITE watch `0x800a6504`, Flik moving):** writer PCs `0x80036384`/`0x80036cf0`/`0x80036d58` all resolve (r2 disasm, t_addr `0x80010000`) to ONE function `FUNC_3633C` @`0x8003633c` = per-frame **movement + collision-response integrator** (`s7`=player base `0x800a6500`, `s5`=velocity `0x800a652c`, `a2`=contact flags `0x800a6582`; caller `0x800495c8` RA `0x800495d0`, also `0x8004c024`/`0x8004e628`). **DuckStation reports PC = store+4.** Four stores to `[s7+4]=0x800a6504`: `0x80036380` (`−0xc80` Y probe-bias DOWN, NOT floor), **`0x80036cec`** (`v1=[sp+0x1c]` = COMMIT of the collision-RESOLVED position `[sp+0x18..0x20]` = **the floor/contact-corrected Y — decisive**), `0x80036d30` (free `pos+=vel`, not observed), `0x80036d54` (`+0xc80` restore, NOT floor). Active collision helper = **`0x800345cc`** (`ra=0x80036c70`); it + `0x80035280` iterate a per-frame collision-candidate list (count `[gp+0x57c]=0x80082314`, gp `0x80081d98`) and write the resolved pos into `sp+0x10/0x18` → **floor source `S` is an element of that gp-scratch list (non-global pointer) — VINDICATES the G5 negative**. **`fcn.8005b134` SUPERSEDED/PENDING** (store is `0x8003633c`; `fcn.8005b134` has 0 jal callers, `0x8003633c` has 3, none = `8005b134`; not erased). exact store/source operand IDENTIFIED. **NEXT = P2** (no patch/build, no G28 compare yet): EXEC `0x80036cec` (resolved floor pos) + EXEC `0x800345cc` (candidate-list base + operand `S`), READ-watch `S`, classify band; P3 differential only after `S` found. Visual ≠ collision. **P2 RESULT (2026-06-15, operator confirmed `0x80036cec`: `sp=0x801FFE00`,`v1=0xFFFE2196`, working buf `[sp+0x18..0x24]={0x5B7B,0xFFFE2196,0xFFFFB44B,0xFFFF0000}`; then WRITE watch `0x801FFE1C`):** two writers (r2-verified, PC=store+4) — **Hit A `0x80035ED8` `sw v0,4(s5)`** in helper **`0x800345cc`** = the resolved-Y COMPUTE, a 3-axis **accumulate** `pos(word @s5) += signed_halfword delta(@s3)` (`s5=0x801FFE18`=FUNC_3633C `sp+0x18` working buf, `s3=0x801FFE10`=`sp+0x10` deltas); at the hit `[s3+2]=0`→Y delta 0→value pre-existed (write site, not origin). **Hit B `0x80036BDC` `sw v1,0x1c(sp)`** in FUNC_3633C = a COPY/seed `[sp+0x18..0x24]←[s7..+0xc]`, gated by `bgtz[gp+0x57c]`/`blez[gp+0x5cc]` — propagation, not origin. **Structural correction:** at Hit B `s7=0x801FFEA8` = a **stack** position vector, NOT player global `0x800a6500` → this FUNC_3633C invocation integrates a stack XYZ vector (commit writes `0x801FFEAC`); FUNC_3633C is a reusable integrator over whatever `a0` points at; stack-vec→`0x800a6504` link is a separate step (UNKNOWN). **Source chain:** candidate list (counts `[gp+0x57c]=0x80082314`/`[gp+0x5cc]=0x80082364`) → sweep helper `0x80035f24` writes deltas to `sp+0x10` → accumulate `0x800345cc` → commit `0x80036cec`. **`0x801FFE1C` source writer identified (both); source data structure = PARTIAL** (candidate-list backing region UNKNOWN). **NEXT = P2-next: EXEC `0x80035f24`** (dump pointer args + candidate-list base, find floor-height read `S`, classify band). No patch/build; no G28 compare. Visual ≠ collision. **G29 LIVE (2026-06-15, DuckStation external-debugger JSON-RPC + new controller-input API; Flik MOVING) — COLLISION/FLOOR SOURCE IDENTIFIED:** idle state has no player collision (movement required); holding Flik walking, the player integrator `FUNC_3633C` (`a0=0x800a6500`) resolves Y through a **CONFIRMED** chain — player XZ `0x800a6500` → **sector table `0x800a7e48`** (count `[gp+0x508]=223`; `0x30`-byte recs, AABB `+0x14/+0x1c`/`+0x24/+0x28`, block ptr `+0x10`; `0x80036700`/`0x80036804`) → `[sector+0x10]` block (`0x800C1690`) → 32-byte collision records `~0x800D0xxx` AABB-tested (`0x80036820..0x8003690c`) → matches stored as pointers into the **`gp+0x57c` list `0x8009c230`** (store `0x800368E8`) → helpers `0x800345cc`/accumulate `0x80035ED8` → commit `0x80036CEC` writes player Y. Decisive: `s7=0x800a6500`, `[gp+0x57c]=7` (list = `0x800D0FA8…0x800D1128`), `posY −109521→ −109693` (dY=−172) — contact list non-empty exactly during Y resolution. Source reached by a **non-global** `[sector+0x10]` chain (G5 negative vindicated), **SEPARATE from the DAT visual floor (explains G28)** and from the `gp+0x5cc`/`0x800F7xxx` grid (global `0x8009f9ec`, 0 winners → secondary wall/object broadphase). **TODO:** on-disk backing of `0x800a7e48`/`0x800C-0x800D` (WRITE-watch at level load) + exact field→Y math. No patch/build/mem-write; state not overwritten. Detail: `geometry_g29_collision_source_plan.md` §2.8. **ON-DISK SOURCE CONFIRMED = LEVEL.RAW (decompressed) (2026-06-15):** from pre-load state `SCUS-94288_2.sav` (`[0x800a7e48]=0` at load) a WRITE-watch caught the sector-table builder (`0x80030F60`, copies from src `t1=0x800F7BF8`), and a watch on `0x800F7BF8` caught its filler at **`pc=0x8001A60C` (LEVEL.RAW decompressor `fcn.8001a1dc`), `ra=0x8003A4EC` (loader `fcn.8003a318`)** with compressed src in the LEVEL.RAW buffer `[0x80115aac,0x801cc690)`. Full disk→player-Y chain: **LEVEL.RAW (compressed) → `fcn.8003a318` load `0x80115aac` → `fcn.8001a1dc` decompress → `0x800F7xxx` → built(`<<5`) into sector table `0x800a7e48` + `0x800C/0x800D` record blocks → runtime sector-AABB select → `gp+0x57c` list `0x8009c230` → helpers `0x800345cc`/`0x80035ED8` → commit `0x80036CEC` → player Y `0x800a6504`.** ⇒ collision lives in **LEVEL.RAW**, visual floor (Cand A) in **LEVEL.DAT** — definitively EXPLAINS G28. EDIT TODO: LEVEL.RAW compressed → decompress/edit/recompress (codec `fcn.8001a1dc`); exact record format + field→Y math open. No edit; slots 1&2 backed up. Detail §2.9. **RECORD FORMAT DECODED (2026-06-15, §2.10):** the `0x800D0xxx` collision records are **PLANES** — `s0+0/+2/+4` s16 = normal X/Y/Z (floor ⇒ |normal.y| dominant), `s0+6/+8/+0xa` s16 = reference point ×32 (matches the `>>5` grid). Resolver `0x800345cc` (`0x80034750..0x800347b8`) computes signed plane distance `d = Σ normal·(P−32·refpt)` (`>>14`); `d≥0` skip (front), `d<0` clamp the swept move onto the plane → per-axis delta → accumulate `0x80035ED8` → commit `0x80036CEC`. Record read CONFIRMED at `0x80034760` (read-watch). Sector `0x800a7e48[idx]` gives the sector-relative origin (`+0/+4/+8`). Live ex.: record `0x800D0FA8` normal `(-1941,-15885,3509)` (floor), sector idx 104 originY `-123808`, player Y `-109521→-109693`. ⇒ **floor = a plane (normal+point), not a scalar height**; resolved Y = player clamped against the `gp+0x57c` plane records. TODO: exact clamp math `0x800347c4..0x80035ec0` + remaining record bytes (poke-confirm precluded by no-write rule). **CLAMP MATH COMPLETE (2026-06-15, §2.11):** resolver `0x800345cc` per plane record (sector-relative): `d_after=(N·(pos+δ−32·refpt))>>14`, `d_before=(N·(pos−32·refpt))>>14`; **swept test** = front→back crossing only (`d_before≥0 && d_after<0`); crossing `= δ·d_before/(d_before−d_after)`; **point-in-face** `0x80032610` (normal's dominant axis → 2D point-in-poly over record edges `s0+0xc..+0x16`); keep nearest. Response (post-loop `0x80034a50`, validator `0x800322a0`): **stop-with-skin** `resolved[i]=pos[i]+δ[i]·(d_before>>3)/((d_before>>3)−((d_after−0xc0)>>3))` → commit `0x80036CEC` → player Y. The `−0xc0`(192) = collision skin (stops in front of the plane). Record (final): normal `s0+0/+2/+4`, refpt `s0+6/+8/+0xa` (×32), face edges `s0+0xc..+0x16`. **⇒ full floor-contact record→Y math decoded.** Next: LEVEL.RAW collision edit (decompress→edit a floor plane→recompress; collision analog of G28). **G29 candidate-record read/compare evidence (2026-06-15):** at `pc=0x80036B70` (`ra=0x800363CC`, `s5=0x801FFEB8`, `s7=0x801FFEA8`) `v1`==32-bit LE word at `[t1−0x08]` — CONFIRMED in 3 captures (`t1=0x800F7BB8/0x800F7B74/0x800F7B30` → `v1=0x11FC/0x121A/0x1300`); the `0x44` spacing is between samples, NOT a proven record stride. Records at `0x800F7xxx` = runtime/heap/BSS (above exe end `~0x80082800`, below DAT/RAW); **backing source UNKNOWN**. Roles: `0x80036B78`=post-read PC; `0x80036B74`=read/compare site; `0x80036B70`=stronger post-load/pre-compare capture; **exact load PC TODO** (static candidate `0x80036a38 lw v1,4(t1)`, near `0x80036B6C` per operator — confirm at runtime). Pointer caveat: `t2=t1−0x30` appears stable; `t6` is state/site-dependent (earlier `t6=t1+0x90`, newer `t6=t2`) — not universal. Static grounding: range-overlap loop `0x800369a0..0x80036b7c` copies matched candidates to output list `0x80090868` (stride `0xc`, count `[gp+0x5cc]=0x80082364`); `[t1−0x08]` (= a `0xc`-stride sub-record `+4` word) is **LIKELY a compare/selection scalar — semantic UNKNOWN, NOT confirmed floor height.** G28/G29 boundary preserved: Candidate A stays visual/render only, collision source UNKNOWN. Doc-only BP block: `FINAL BREAKPOINTS: EXEC 0x80036B70`. Next: static/decompile `0x80036B6C..0x80036B78`. |
| **G30** | Visible walkable-terrain ("dirt") render-source discovery + matched floor edit. Find how the **world-space dirt Flik stands on** is RENDERED, locate its editable geometry buffer + on-disk source, then lower it to MATCH a collision edit (Flik falls onto a visibly-lowered floor on flat ground). | `src_re_geometry/geometry_g30_terrain_render_source_plan.md` | **PLAN 2026-06-16 (multi-step R1–R6, live-debug + r2; no blind corruption).** Builds on G29 (collision=LEVEL.RAW, full disk→player-Y chain; collision RAM edit proven 1:1) + this session's live work. **Established:** the bulk visible dirt is **world-space, NOT the `fcn.80010000` object payloads** (spike + clean-uniform-shift tests negative on 2 payload sets; toggling Candidate A no-ops the flat dirt), NOT reached via the collision sector record (only `+0x10` collision-block ptr); **Candidate A is one editable visual floor TILE** (clean uniform lower renders stably — operator image #2 — but only at its dip-area location, DAT/model space). The dirt is drawn by a member of the **GTE renderer FAMILY `0x80010000–0x8001a120`** other than `fcn.80010000` (objects); **G6** showed the trail path (`fcn.800140a0`, `DAT+0x1526`) gates terrain visibility. Engine: render **caches transformed geometry** (camera movement refreshes; clean uniform edits stable, spikes flicker); **blind RAM corruption CRASHES** (pointer-rich). **Phases:** **R1** map `fcn.800224ec`/`fcn.8003f938` call tree → terrain-renderer shortlist (static); **R2** EXEC-BP shortlist → find the big-ground-polygon emitter (live, by SXY); **R3** trace its vertex-buffer base + format/coord-space; **R4** READ-watch + ONE clean uniform Y edit (walk to refresh) → confirm + calibrate scale; **R5** WRITE-watch at level load → on-disk source (LEVEL.RAW chunk); **R6** matched visual+collision lower on a FLAT spot → screenshot. Guardrails: no corruption sweeps, clean non-pointer edits only, collision kill-plane limit, save-state hygiene, no artifact commits. **R1 DONE** (call tree → 6-emitter shortlist, §9). **R2 DONE cache-clean** (§11): frame loop = `0x8004fecc` → scene fn `0x8004ecd4` → render cluster `0x8004f388–0x8004f458`; 60-frame-movement neutralize (camera scrolled, no freeze) shows **dirt persists in every variant ⇒ "separate background layer" CONFIRMED**; `fcn.8001ea6c`/`fcn.80017b98` = fence, `fcn.800140a0` = cull. **Next: R2-continued — per-call-site neutralize of `fcn.800224ec` (`0x8004f428` vs `0x8004f448`), or method (d) GP0/vertex-buffer READ-watch (recommended), then R3.** |

Recommended order: **G1 → G2 → G3 → (G4 ∥ G5) → G6.** G4 and G5 can proceed in parallel once G3
names the buffers, but their hypotheses must stay in separate files.

---

## 4.1. G6 proposal/build — render-stage diagnostic edit only

**Status:** DIAGNOSTIC IMAGE TESTED 2026-06-14. Render-stage diagnostic succeeded. Do not treat this
as collision-aware.

**Why this target:** G5.5 confirmed `fcn.800140a0` reads pass-1 trail flag/sentinel halfwords at
LEVEL01 DAT offsets `0x1512` and `0x1526`. The recommended body/range fields at `DAT+0x1510`,
`DAT+0x1508`, and `DAT+0x150c` were watched and had no hits, so a body/position-like edit is not
currently defensible as a proven runtime-read field. This proposal therefore uses the later confirmed
flag/sentinel (`entry1`, not `entry0`) to minimize blast radius relative to terminating at entry0.

| field | value |
|-------|-------|
| target file | `LEVEL01/LEVEL.DAT` (pristine source: `DAT/LEVEL01_LEVEL.DAT`) |
| exact DAT offset | `0x1526` |
| runtime address with DATbase `0x801607f8` | `0x80161d1e` |
| table entry | pass-1 trail entry 1, `entry+0x0e` flag/sentinel halfword |
| confirmed reader | `fcn.800140a0`, read site `0x80014170: lh t3,0x0e(a0)` |
| original bytes | `41 00` (`0x0041`) |
| proposed new bytes | `ff ff` (`-1` sentinel) |
| revert bytes | `41 00` |

**Observed render-stage effect (CONFIRMED):** `ABL_G6_RENDER_SENTINEL_TEST.cue` reaches title/menu and
enters LEVEL01. Standing still, terrain/ground render is mostly empty/missing, while background sky
and some horizon/grass/backdrop remain visible. Flik, objects, enemy/props still load. No black screen
and no crash. Compared with pristine, this is a major render-stage terrain disappearance/cutoff.

**Interpretation:** `DAT+0x1526` / pass-1 trail entry1 flag/sentinel controls render-stage trail
scanning/visibility. The edit likely makes `fcn.800140a0` treat entry1 as a negative sentinel and stop
after entry0, but the exact trail-field semantics and downstream GPU primitive path remain **UNKNOWN**.

**Collision/pathing impact:** **UNKNOWN.** In the tested area, Flik could stand and move on the
invisible/missing terrain, which supports render/collision separation for this field. This does not
identify the full collision/pathing data source or prove global collision behavior.

**Reversibility:** single halfword. Restore bytes at `LEVEL01/LEVEL.DAT+0x1526` from `ff ff` to
`41 00`.

### G6 build record (2026-06-14)

Active rebuild source verified before patching:

| item | value |
|------|-------|
| active DAT | `REBUILD/files/LEVEL01/LEVEL.DAT` |
| size | `332824` (`0x51418`) |
| SHA256 | `786b7a964129d4fee6a1983b356e172d406b17663d87b8befe645b92dbf08b53` |
| bytes at `0x1526` | `41 00` |

Patch tool:

```
python3 tools/patch_g6_render_sentinel_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST.DAT
```

Patched DAT:

| item | value |
|------|-------|
| path | `DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST.DAT` |
| size | `332824` |
| SHA256 | `149419dd724943dafa101b29e3a2bec179e188ebc0c93e8f42b1a095fea6c31a` |
| SHA1 | `717a0875f28fd8c93c6db9209c5e7981f3fcc97d` |
| changed bytes | `0x1526: 41 00 -> ff ff` |
| revert bytes | `41 00` |

Rebuild command:

```
python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G6_RENDER_SENTINEL_TEST.bin --out-cue ABL_G6_RENDER_SENTINEL_TEST.cue --write --report DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST_REBUILD.md
```

Rebuild result:
- Output: `ABL_G6_RENDER_SENTINEL_TEST.bin` / `ABL_G6_RENDER_SENTINEL_TEST.cue`.
- Embedded `LEVEL01/LEVEL.DAT` at LBA 2906 verified SHA1
  `717a0875f28fd8c93c6db9209c5e7981f3fcc97d`.
- `REBUILD/files/LEVEL01/LEVEL.DAT` was restored to the pristine source after build.

### G6 emulator result (2026-06-14)

User-tested image: `ABL_G6_RENDER_SENTINEL_TEST.cue`.

| check | result |
|-------|--------|
| reaches title/menu | yes |
| enters LEVEL01 | yes |
| standing still render | terrain/ground mostly empty/missing; sky and some horizon/grass/backdrop visible |
| actors/objects | Flik, objects, enemy/props still load |
| crash/black screen | no |
| after movement | Flik can stand/move on invisible/missing terrain in tested area; objects still load |
| pristine comparison | major render-stage terrain disappearance/cutoff |

Conclusion: G6 render-stage diagnostic edit succeeded. Collision/pathing remains **UNKNOWN** beyond
the tested observation that ground collision remained usable in the tested area.

## 4.2. G7 — render-body field identification

**Status:** RENDER-BODY FIELD READ CONFIRMED 2026-06-14. No DAT/BIN/CUE patching and no build.

**Goal:** find a DAT-backed pass-1 trail body field read at runtime by `fcn.800140a0`, avoiding the
`entry+0x0e` flag/sentinel stop field used by G6.

### `fcn.800140a0` body-field gating

Reinspection of `fcn.800140a0` confirms two separate operations:

1. The loop scans every pass-1 trail row until `lh entry+0x0e` is negative.
2. Body fields are read only if the row's bit is set in a runtime bitmask table.

Relevant control flow:

| PC | operation | meaning |
|----|-----------|---------|
| `0x80014164` | `lb s1,0(s0)` with `s0=0x800901c8...` | loads current 8-entry bitmask byte |
| `0x80014170` | `lh t3,0x0e(a0)` | scans the row flag/sentinel |
| `0x80014174` | `and t9,s1,s4` | tests current row bit; initial `s4=0x80`, shifts down each row |
| `0x80014178` | `bltz t3,0x80014330` | negative flag terminates loop |
| `0x80014180..0x80014190` | shift/reload bitmask; increment `a0 += 0x14` | advances row and bit |
| `0x80014194` | `beqz t9,0x80014170` | if row bit clear, skip all body-field reads |
| `0x8001419c` | `lw s3,-0x14(a0)` | reads processed row `entry+0x00` |
| `0x800141a0` | `lw s5,-0x0c(a0)` | reads processed row `entry+0x08` |
| `0x800141a4` | `lh t4,-0x08(a0)` | reads processed row `entry+0x0c` |
| `0x800141b4` / `0x80014258` | `lw t1,-0x10(a0)` | reads processed row `entry+0x04` |

The delay-slot increment means body loads use negative offsets from the already-incremented `a0`;
they still read the row whose flag was just tested.

**Why entry0/entry1 body watches likely did not hit:** `entry+0x0e` is read before the bitmask gate,
so entry0/entry1 flag watches confirm scanning. The tested entry0 body fields (`DAT+0x1510`,
`DAT+0x1508`, `DAT+0x150c`) are behind `beqz t9`; if the entry0 bit in `[0x800901c8] & 0x80` was
clear for the current camera/frame, those reads are skipped. The same likely applies to entry1.

### Candidate body-field READ watches

Use one watchpoint at a time in pristine LEVEL01. Confirm live `DATbase=0x801607f8` and
`G_TRAIL_BLOCK_PTR=0x80161cfc` first. These candidates avoid `entry+0x0e` and target rows whose
non-`0x0041` flags/position in the table make them better candidates for active processing than
entry0/entry1. The bitmask column is not a DAT field; it is the runtime gate to inspect if an
execute breakpoint is used.

| priority | entry | field | DAT offset | runtime address | original value / bytes | runtime bit gate | expected read PC |
|---------:|------:|-------|------------|-----------------|------------------------|------------------|------------------|
| 1 | 19 | `+0x00` word | `0x1680` | `0x80161e78` | `-8839` / `79 dd ff ff` | `[0x800901ca] & 0x10` | `0x8001419c` |
| 2 | 19 | `+0x0c` halfword | `0x168c` | `0x80161e84` | `195` / `c3 00` | `[0x800901ca] & 0x10` | `0x800141a4` |
| 3 | 24 | `+0x00` word | `0x16e4` | `0x80161edc` | `-10240` / `00 d8 ff ff` | `[0x800901cb] & 0x80` | `0x8001419c` |
| 4 | 31 | `+0x0c` halfword | `0x177c` | `0x80161f74` | `189` / `bd 00` | `[0x800901cb] & 0x01` | `0x800141a4` |
| 5 | 45 | `+0x00` word | `0x1888` | `0x80162080` | `-5661` / `e3 e9 ff ff` | `[0x800901cd] & 0x04` | `0x8001419c` |
| 6 | 132 | `+0x00` word | `0x1f54` | `0x8016274c` | `487` / `e7 01 00 00` | `[0x800901d8] & 0x08` | `0x8001419c` |

If a watch hits at the expected PC in `fcn.800140a0`, classify it as a CONFIRMED render-stage
DAT-backed body-field read. It becomes eligible for a later G7/G8 render-only diagnostic proposal
only after recording hit count, PC, current phase, `a0`, and value read. Collision/pathing impact
remains **UNKNOWN** unless a non-render PC also reads the same field.

### Runtime results (2026-06-14)

Testing was on the pristine/working image, not the G6 sentinel image. For each watch, all other
breakpoints/watchpoints were disabled, one READ watch was active at a time, and the operator resumed
with F5 while standing still, walking, jumping, and changing camera/view angles.

| watch | maps to | expected read | result | classification |
|-------|---------|---------------|--------|----------------|
| `0x80161e78` | pass-1 trail entry19 `+0x00` body word, `DAT+0x1680`, bytes `79 dd ff ff` | `0x8001419c` / `fcn.800140a0` | no hit | **ZERO-HIT / NOT ELIGIBLE YET** |
| `0x80161e84` | pass-1 trail entry19 `+0x0c` body/range halfword, `DAT+0x168c`, bytes `c3 00` | `0x800141a4` / `fcn.800140a0` | no hit | **ZERO-HIT / NOT ELIGIBLE YET** |
| `0x80161edc` | pass-1 trail entry24 `+0x00` body word, `DAT+0x16e4`, original bytes `00 d8 ff ff` | `0x8001419c` / `fcn.800140a0` | no hit during general standing/walking/jumping/camera movement away from the area; later hit once when Flik/camera was near a specific edge-of-level area | **CONFIRMED render-stage DAT-backed body-field read** |

Entry24 hit details:

| field | value |
|-------|-------|
| trigger context | Flik/camera near a specific edge-of-level area; not attributed to F collection |
| READ watch | `0x80161edc` |
| DuckStation PC shown | `0x800141a0` |
| actual read site | `0x8001419c: lw s3,-0x14(a0)` |
| `a0` at hit | `0x80161ef0` |
| read address | `a0 - 0x14 = 0x80161edc` |
| DAT offset | `0x16e4` |
| loaded value reported in `s3` | `0xfffd126d` |

Interpretation: `fcn.800140a0` still CONFIRMED scans pass-1 trail flags/sentinels broadly, and
entry24 `+0x00` is now a CONFIRMED DAT-backed body field read by the render-stage path. Entry24
appears view/location/edge-of-level gated in this test. Entry19 remains
**ZERO-HIT / NOT ELIGIBLE YET**. It remains **UNKNOWN** whether entry19 is never used,
scene/camera gated, distance gated, or only active in a different route/state.

### DuckStation runbook — active-entry discovery

1. Boot the pristine image into LEVEL01 and wait until Flik is controllable.
2. Confirm memory:
   - `mem32[0x80082498] = 0x801607f8`
   - `mem32[0x800824ac] = 0x80161cfc`
3. Inspect the runtime bitmask bytes beginning at `0x800901c8`. For each nonzero bit:
   - `entry = byte_index * 8 + bit_index`
   - `bit mask = 0x80 >> bit_index`
   - row base = `G_TRAIL_BLOCK_PTR + entry * 0x14`
   - `DAT offset = row base - DATbase`
4. For active rows, set one READ watch at a time on row `+0x00`, `+0x04`, `+0x08`, or `+0x0c`.
5. Alternative: set execute breakpoints at the actual body-read sites and record `a0` when hit:
   `0x8001419c`, `0x800141a0`, `0x800141a4`, `0x800141b4`, `0x80014258`.
   At these stops, the processed row base is `a0 - 0x14` because `a0` was advanced in the delay slot.
6. Derive `entry_index = (row_base - G_TRAIL_BLOCK_PTR) / 0x14`, then set concrete READ watches on
   that row's body fields.
7. A hit at one of the body-read PCs inside `fcn.800140a0` is the desired G7 evidence. A hit only at
   `0x80014170` is a scan/flag hit, not a body-field hit.

Entry24 `+0x00` is eligible for a future same-size render-body diagnostic proposal because it has a
CONFIRMED body-field read with exact DAT offset, hit PC, `a0`, value read, and trigger phase. Do not
patch yet. Collision/pathing impact remains **UNKNOWN** unless a non-render PC also reads the same
field.

### Path A — entry24 adjacent body-field coverage (COMPLETE 2026-06-14)

Goal: complete entry24 body coverage by watching the rest of the row (`+0x08`, `+0x0c`, `+0x04`) in
the **same edge-of-level area** that fired `READ 0x80161edc`. One READ watch at a time. No patch, no
build. Row base `0x80161edc = G_TRAIL_BLOCK_PTR + 24*0x14 = DATbase+0x16e4`. DuckStation shows
PC = read-site + 4 (post-read stop, CONFIRMED at `+0x00`).

**RESULT: all four entry24 body fields CONFIRMED read by `fcn.800140a0`** at the predicted PCs with
`a0=0x80161ef0`, in the edge-of-level / view-location gated area (not F-collection). The `+0x00`
control re-fired (hit count 2). The `+0x04` hit at `0x80014258` confirms the non-negative-`+0x0c`
branch.

| field | runtime addr | DAT off | pristine bytes | signed | read site (`fcn.800140a0`) | PC shown | result |
|-------|--------------|--------:|----------------|-------:|----------------------------|----------|--------|
| `+0x00` word | `0x80161edc` | `0x16e4` | `00 d8 ff ff` | `-10240` | `0x8001419c` | `0x800141a0` | **CONFIRMED** (control, hit count 2) |
| `+0x04` word | `0x80161ee0` | `0x16e8` | `b3 f5 ff ff` | `-2637` | `0x80014258` | `0x8001425c` | **CONFIRMED** |
| `+0x08` word | `0x80161ee4` | `0x16ec` | `9f fa ff ff` | `-1377` | `0x800141a0` | `0x800141a4` | **CONFIRMED** |
| `+0x0c` half | `0x80161ee8` | `0x16f0` | `de 02` | `734` | `0x800141a4` | `0x800141a8` | **CONFIRMED** |

entry24 is a **CONFIRMED non-sentinel DAT-backed render body row**; **LIKELY** location/view gated;
field semantics, downstream GPU stage, and visual effect **UNKNOWN**; collision/pathing **UNKNOWN**.
**Flagged:** at the `+0x00` hit DuckStation reported `s3=0xfffd126d` while the static DAT word is
`0xffffd800`; **UNKNOWN** whether the row is runtime-rewritten (gates any static edit — see §4.3).

**Should `+0x04` be tested? YES.** `+0x04` is read on one of two branches selected by the sign of
`+0x0c`: `0x800141b4` (negative) or `0x80014258` (non-negative). Pristine `+0x0c` = `0x02de` =
`734 ≥ 0`, so the negative path is dead and `+0x04` reads at `0x80014258` (PC shown `0x8001425c`).
All four body fields are read in one straight-line block once the row's bitmask bit
(`[0x800901cb] & 0x80`) is set, so `+0x04` should hit in the same state as `+0x00`.

Procedure: (1) confirm `mem32[0x80082498]=0x801607f8`, `mem32[0x800824ac]=0x80161cfc`; (2) watch
`0x80161edc` as a positive control and reposition into the edge-of-level spot until it breaks at PC
`0x800141a0`; (3) swap to one of `0x80161ee4`/`0x80161ee8`/`0x80161ee0` at a time without moving and
record PC shown, accessed address, value, `a0`, phase, hit count.

A HIT at the expected PC = CONFIRMED render-stage DAT-backed body read, completing entry24 body
coverage; eligible for a later render-body diagnostic. A NO-HIT while the `+0x00` control still fires
in the same frame is unexpected (one straight-line block) — re-check watch address/width and the
gate bit before concluding, and record verbatim. If `+0x00` itself stops firing, the edge-of-level
state was not reproduced; reposition. Collision/pathing impact remains **UNKNOWN**. Do not patch yet.

## 4.3. G8 — render-body diagnostic PROPOSAL (entry24 body field) — NOT YET PATCHED

**Status:** PROPOSAL ONLY (2026-06-14). No DAT/BIN/CUE patch, no ISO build, no commit of binary
artifacts. Full detail in `src_re_geometry/geometry_g55_dynamic_watch.md` §11.

**Why entry24:** Path A CONFIRMED the whole entry24 body row is read by `fcn.800140a0` at
deterministic PCs. These are **non-sentinel** body fields, so a small numeric perturbation probes
render geometry rather than toggling a scan terminator like the G6 edit.

**Blocking verification gate (before any patch):** the `+0x00` static word (`0xffffd800`) differs
from the runtime-read value (`0xfffd126d`). Until explained, a static DAT edit may not survive to the
read site. Before patching any field, read its live word in the edge-of-level area and confirm it
equals the static DAT bytes at the read instant. If they differ, the row is runtime-rewritten →
**do not patch** that field. **Avoid `+0x00` as the edit target** for this reason.

**Candidate edits (same-size, reversible; LIKELY render-body/range/vector fields; UNKNOWN exact
visual effect — no shape/position semantics claimed):**

| id | field | DAT off | orig bytes (value) | candidate new bytes (value) | perturbation | revert |
|----|-------|--------:|--------------------|-----------------------------|--------------|--------|
| A (recommended) | entry24 `+0x08` word | `0x16ec` | `9f fa ff ff` (`-1377`) | `9f fb ff ff` (`-1121`) | `+256`, 1 byte | `9f fa ff ff` |
| B (escalation) | entry24 `+0x08` word | `0x16ec` | `9f fa ff ff` (`-1377`) | `61 05 00 00` (`+1377`) | sign-flip | `9f fa ff ff` |
| C (alt field) | entry24 `+0x04` word | `0x16e8` | `b3 f5 ff ff` (`-2637`) | `b3 f9 ff ff` (`-1613`) | `+1024`, 1 byte | `b3 f5 ff ff` |

`+0x08` is chosen first: single deterministic read site (`0x800141a0`, no branch dependency),
smallest-magnitude body word, and neither the `+0x0c` branch/sign term nor the `+0x0e` flag/sentinel
(the G6 destructive field). `+0x0c` and `+0x0e` are **explicitly excluded** (control/sentinel).

**Expected render-stage effect:** **UNKNOWN exact visual effect.** Possible outcomes to record
without prejudging: no visible change; a small local geometry shift/distortion near the edge-of-level
area; or a local visibility change. A full-screen terrain loss like G6 is **not** expected from a
small numeric body edit.

**Explicit uncertainty:** field semantics (coordinate/range/vector) UNKNOWN; edit survival to the
read site UNKNOWN until the gate passes; observability of a small perturbation UNKNOWN;
collision/pathing impact UNKNOWN.

**Operator test (only when a build is later authorized):** run the verification gate; on a copy of
the pristine DAT apply Candidate A (`DAT+0x16ec: 9f fa ff ff → 9f fb ff ff`); rebuild a test image;
revisit the edge-of-level area and compare against pristine; escalate to B only if A is imperceptible;
revert by restoring `9f fa ff ff`. Never commit DAT/BIN/CUE. Do not patch yet.

**G8 status (BUILT 2026-06-14):** live-value gate **PASSED**, patched DAT and test image **built**;
emulator visual test **pending**.

- **Live-value gate PASSED:** in the edge-of-level entry24 state, `READ 0x80161ee4` broke at PC shown
  `0x800141a4` (read site `0x800141a0`, `a0=0x80161ef0`); debugger banner `addr=0x80161ee4
  [0xfffffa9f]`. The live word equals the static DAT value `0xfffffa9f` (`9f fa ff ff`), so `+0x08` is
  static-DAT-backed at the read instant. (The `+0x00` mismatch does not apply to `+0x08`.)
- **Patch:** `python3 tools/patch_g8_entry24_plus08_test.py DAT/LEVEL01_LEVEL.DAT
  DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_TEST.DAT` → patched DAT SHA256
  `bdc21f3546f9795d9a91871833e47158838f6ea6cce8ddcd00e5b6c286e24e49`, SHA1
  `67dbb8322741fc3863aa5e9c81aa463c3505da2d`; only `DAT+0x16ec` word changed (`9f fa ff ff → 9f fb ff
  ff`). Pristine input untouched; script re-confirmed to refuse wrong original bytes.
- **Build:** `tools/rebuild_with_patched_dat.py … --out-bin ABL_G8_ENTRY24_PLUS08_TEST.bin --out-cue
  ABL_G8_ENTRY24_PLUS08_TEST.cue --write`. Embedded `LEVEL01/LEVEL.DAT` at LBA `2906` verified SHA1
  `67dbb832…` (== patched); embedded byte at file `0x16ec` reads `9f fb ff ff`. Staged workspace
  restored to pristine (`b376cb50…`).
- **Artifacts:** DAT/BIN/CUE and the rebuild report are **gitignored and not committed** (as with
  G6/G7). Full execution record + operator visual-test steps in `geometry_g55_dynamic_watch.md` §12.
- **UNKNOWN:** exact visual effect (test pending; "no visible change" is a valid result); field
  semantics; collision/pathing impact (must not be inferred from a render-stage edit).

**G8 Candidate A result (2026-06-14): EXECUTED / VALID BUILD / NO OBVIOUS VISUAL CHANGE** (not a
failure). `ABL_G8_ENTRY24_PLUS08_TEST.cue` boots, LEVEL01 loads, no crash/black screen; in the
edge-of-level entry24 area there was no obvious terrain shift/deformation, clipping/range change, or
missing/altered geometry — pristine and G8 look effectively the same by eye. The `+256` same-field
nudge was likely too small, visually masked, or not directly positional; `+0x08` may still be
render-body/range/vector data. **Optional CPU confirmation: CONFIRMED data read in G8 image; raw
patched register value not separately captured.** The READ `0x80161ee4` data watch was redone
correctly in `ABL_G8_ENTRY24_PLUS08_TEST.cue` — observed PC shown `0x800141a4` (read site
`0x800141a0`, `a0=0x80161ef0`, hit count 1), CONFIRMING the patched field is reached/read by
`fcn.800140a0`. The screenshot does not clearly show `s5=0xfffffb9f`; proof the image holds the
patched bytes is the embedded DAT verification (`DAT+0x16ec`=`9f fb ff ff`). Collision/pathing remains
**UNKNOWN**.

**G8 Candidate A2 (BUILT and tested 2026-06-14):** larger same-field escalation of
A, still controlled/reversible. Patch `DAT+0x16ec: 9f fa ff ff → 9f fe ff ff` (`-1377 → -353`, delta
`+1024`, single byte). Built via `tools/patch_g8_entry24_plus08_a2_test.py` (pristine-only guard) +
`tools/rebuild_with_patched_dat.py`: patched DAT SHA256
`0c2be4fbc9bdd7ae70699c3f5728c5e52511789f5ae6962f83a001fac4b957d5` (SHA1 `8714b578…`); image
`ABL_G8_ENTRY24_PLUS08_A2_TEST.cue`/`.bin`; embedded `LEVEL01/LEVEL.DAT` verified at LBA `2906`
(`0x16ec` = `9f fe ff ff`); staged workspace restored to pristine. Artifacts gitignored/not committed.
Full record + operator test steps in `geometry_g55_dynamic_watch.md` §13.

**G8 Candidate A2 result (2026-06-14): EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL
CHANGE.** `ABL_G8_ENTRY24_PLUS08_A2_TEST.cue` boots, LEVEL01 loads, no crash; the edge-of-level entry24
area is effectively unchanged by eye. CPU data-read CONFIRMED (READ `0x80161ee4` hit, count 1, PC
`0x800141a4`, `a0=0x80161ef0`). **Memory-byte proof CONFIRMED:** the CPU memory view shows
`0x80161ee4 = FFFFFE9F` (`9f fe ff ff`), so live RAM matches the A2 patch (cross-checked against the
adjacent row: `+0x00=FFFFD800`, `+0x04=FFFFF5B3`). A DuckStation save state + RAM dump were captured at
the trigger location for future reproduction (not committed). The `+1024` change is CPU-read- and
RAM-confirmed yet visually imperceptible → `+0x08` may be too subtle/masked/not directly positional;
render-body relevance not disproven. Detail in `geometry_g55_dynamic_watch.md` §13.

**G8 Candidate C result (2026-06-14): EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL
CHANGE.** Candidate C switched from `+0x08` (A/A2, both visually imperceptible) to another
CONFIRMED-read body field, entry24 `+0x04` (`DAT+0x16e8: b3 f5 ff ff → b3 f9 ff ff`,
`0xfffff5b3` / `-2637` → `0xfffff9b3` / `-1613`, delta `+1024`, single byte, still negative,
reversible; read at `0x80014258`, the non-negative-`+0x0c` branch). Built via
`tools/patch_g8_entry24_plus04_c_test.py` (pristine-only guard) + `tools/rebuild_with_patched_dat.py`;
image `ABL_G8_ENTRY24_PLUS04_C_TEST.cue`/`.bin`; embedded `LEVEL01/LEVEL.DAT` verified at LBA `2906`
(`0x16e8` = `b3 f9 ff ff`); staged workspace restored to pristine. CPU confirmation: READ
`0x80161ee0` hit once, DuckStation PC shown `0x8001425c`, actual read site `0x80014258`. Visual
result: boots, LEVEL01 loads, no crash, no black screen, no obvious localized terrain
shift/deformation, no obvious clipping/range change, and no obvious missing/altered visual geometry.
By eye, Candidate C looks effectively the same as pristine / A2 in the tested edge-of-level area.
Collision/pathing was not assessed and remains **UNKNOWN**.

### G8 perturbation summary and conclusion

Small same-sign perturbations of entry24 body fields were valid and read but visually imperceptible:

| candidate | field | DAT offset | delta | CPU/read status | visual result |
|-----------|-------|------------|------:|-----------------|---------------|
| A | entry24 `+0x08` | `0x16ec` | `+256` | CONFIRMED data read | no obvious visual change |
| A2 | entry24 `+0x08` | `0x16ec` | `+1024` | CPU READ CONFIRMED; live RAM matched patch | no obvious visual change |
| C | entry24 `+0x04` | `0x16e8` | `+1024` | CPU READ CONFIRMED | no obvious visual change |

This does **not** disprove render-body relevance, but it does show that continued small perturbations
of entry24 body words are low-yield. Stop blind/small entry24 perturbation testing as the immediate
next step. The next phase should trace where these values flow after `fcn.800140a0` reads them.

### G9 runtime result — entry24 dataflow/reject path

**Goal:** trace entry24 values after `fcn.800140a0` reads them. Do not patch DAT files, build images,
or run patch scripts for G9. Detailed static table and runtime runbook:
[`src_re_geometry/geometry_g9_entry24_dataflow.md`](../src_re_geometry/geometry_g9_entry24_dataflow.md).

First static result (2026-06-14):

| field | DAT offset | read instruction | observed static flow | confidence |
|-------|------------|------------------|----------------------|------------|
| `+0x00` | `0x16e4` | `0x8001419c lw s3,-0x14(a0)` | `+0x00-t5` -> coarse `SQR` input and full `MVMVA` vector input | CONFIRMED dataflow; LIKELY culling/range role |
| `+0x04` | `0x16e8` | `0x80014258 lw t1,-0x10(a0)` | `+0x04-t6` -> full `MVMVA` vector input paired with `+0x00/+0x08` | CONFIRMED arithmetic pairing; LIKELY culling/range role |
| `+0x08` | `0x16ec` | `0x800141a0 lw s5,-0x0c(a0)` | `+0x08-t7` -> coarse `SQR` input and full `MVMVA` vector input | CONFIRMED dataflow; LIKELY culling/range role |
| `+0x0c` | `0x16f0` | `0x800141a4 lh t4,-0x08(a0)` | sign branch/path selector, `t4>>4`, extent/range term in reject tests | CONFIRMED branch control; LIKELY extent/range role |

Static interpretation: entry24 `+0x00/+0x04/+0x08` form a view-relative vector
`(+0x00-t5, +0x04-t6, +0x08-t7)`. The non-negative `+0x0c` path feeds `SQR`
(`0x8001425c`, opcode `0x4aa00428`) and `MVMVA` (`0x80014298`, opcode `0x4a49e012`), then runs
reject branches before any accepted row-pointer write to list A (`0x8001430c`, base `0x80096ea8`) or
list B (`0x80014320`, base `0x8009e338`). No direct GPU primitive, visible coordinate, or mesh vertex
write was observed in this block. Entry24 is therefore **LIKELY** culling/bounds/range data rather
than a direct mesh-position row in `fcn.800140a0`.

Runtime result: operator stepped from `READ 0x80161ee0` (`+0x04`, actual read site `0x80014258`,
PC shown `0x8001425c`, `a0=0x80161ef0`). At `0x80014280`, `s3=0xffff262b`, so `bgez` was not taken
and entry24 passed the first reject. At `0x800142b0`, `t0=0x000010b1`, and the operator-observed
`bgtz t0,0x80014170` branch was taken. **CONFIRMED:** entry24 is read by `fcn.800140a0` and participates in GTE/math
reject testing, but in the tested edge-of-level state it rejects at `0x800142b0` before the late
list-write path.

This explains G8 A/A2/C: their patched fields influence the reject calculation, but entry24 still is
not inserted into the visible output/list path in this tested state. Do not overstate: it remains
**UNKNOWN** whether entry24 can survive in another camera/player state, **UNKNOWN** whether the late
list writes are render visibility lists (still **LIKELY**), and **UNKNOWN** for collision/pathing.

Earlier noisy EXEC observation: the late write path was observed for another row with
`t0=0x80161f40`, not entry24 rowbase `0x80161edc`; do not claim entry24 reached the list-write path.
The other row maps cleanly: `(0x80161f40 - 0x80161cfc) / 0x14 = 0x244 / 0x14 = 29`, so it is pass-1
entry29 with DAT row `0x1748` (`+0x04=0x174c`, `+0x08=0x1750`, `+0x0c=0x1754`).

RAM/save-state note: a RAM dump alone would not have proven this branch result because the decisive
evidence was transient CPU/GTE register state at specific PCs. The saved state is useful for
reproducing the trigger, but manual stepping or a CPU/GTE-aware trace is required to confirm
reject/list-write behavior.

G9b recommendation: find a row that survives to `0x8001430c` or `0x80014320`, map that row back to
DAT offset, then test whether its body fields produce visible changes. Entry24 is a confirmed
read/reject row, but not a good visual-edit target in this tested state.

## 4.4. G10 — survivor-list consumers and the payload/primitive render chain

**Status:** STATIC ISO ANALYSIS (2026-06-14). Read-only `SCUS_942.88` disasm + read-only DAT byte
trace. No patch, no build. Full detail:
[`src_re_geometry/geometry_g10_payload_render_chain.md`](../src_re_geometry/geometry_g10_payload_render_chain.md).

**Chain (CONFIRMED):**

```
fcn.800224ec  ├ fcn.800146e0(cam matrix,vec)         libgte: load camera matrix into GTE
              ├ fcn.800140a0(trail,…)                cull pass-1 rows -> LIST_A/LIST_B survivors
              ├ fcn.80014360(pass3,…)                pass-3 analog producer (LIKELY)
              ├ fcn.8001ea6c(LIST_A,count,[0x8008240c],0x10)        primitive builder #1
              └ fcn.800206e8(LIST_A,count,[0x8008240c]+0x1c4)       primitive builder #2
```

`LIST_A=0x80096ea8`, `LIST_B=0x8009e338`; `[0x8008240c]=gp+0x674` = LIKELY active GPU/OT buffer.
LIST_B is only written (both producers); its consumer is **UNKNOWN**.

**Consumer behavior (CONFIRMED):** `fcn.8001ea6c` (span `0x8001ea6c..0x800206e0`) walks LIST_A, clears
each pointer's tag bit (`&~1`), gates rows on `lhu[row+0x0e]&0x10==a3(0x10)`, BRIDGES `s0=[row+0x10]`
(output record) → `s2=[s0+0x18]` (source record), reads source `vec[3]` (`[s2+0/4/8]`) minus camera
`0x1f800374[+0x10/14/18]`, GTE-transforms via leaf `0x8001474c`, dispatches on `(row+0x0e & 0x9f6f)<0x6d`
via jump table `@0x8001a970`, and packs ~29 stores into the `a2` buffer. `fcn.800206e8`
(span `0x800206e8..0x800212f4`) is the same shape with a different dispatch set (`<0x4b`), an OT z-index
from `[gp+0x5f4]>>2` → `0x1f800390`, and the `+0x1c4` OT sub-buffer.

**Corrections to the earlier G10 sketch:** `fcn.800146e0` is a libgte camera-matrix load *leaf*
(`jr ra @0x8001471c`), **not** a projection stage; `0x80060484/0x800605c4` are libgte matrix-load
leaves, **not** libgpu submit; the `RTPT @0x80014970` belongs to `fcn.80014844` (reads contact array
`0x800b0d18`), a separate actor/sprite path.

**Bridge to editable data (CONFIRMED, byte-traced):** trail row `+0x10` → output record → `+0x18` →
source record (band `0x45f0..0x8bd8`) → `+0x14`(non-bit3)/`+0x1c`(bit3) → payload (band
`0x8bd8..0x4f32c`). Payload = `u32` count + s16 coordinate-triple vertex records (LIKELY ~12B stride).
entry29 (DAT row `0x1748`, the CONFIRMED G9 survivor): source `@0x7388` `vec=(-10000,-2374,-1099)`
`scale=(5220,5220,5220)`, payload `@0x2f2f8` count `34`.

**Edit-target candidates (PROPOSAL ONLY — object must survive culling; use entry29):**

| # | target | DAT (entry29) | effect | evidence | confidence |
|--:|--------|---------------|--------|----------|------------|
| 1 | source `vec[3]` | `0x07388` (3×s32) | translate object's drawn position | case `0x8001ec44` reads `[s2+0/4/8]−camera`→GTE (runtime READ `0x80167b80` confirmed) | CONFIRMED consumed |
| 3 | source `scale[3]` | `0x0739a` (3×s16) | resize object | case `0x8001ec44` reads `[s2+0x12/14/16]`, scales model matrix `>>12` | CONFIRMED read by runtime builder |
| 4 | source `angle[3]` | `0x07394` (3×s16) | rotate object | case `0x8001ec44` reads `[s2+0xc/0xe/0x10]` + matrix LUT via `[s2+0x19]` | CONFIRMED read by runtime builder |
| 2 | payload vertex | `0x2f2f8`+ (s16 triple) | move one vertex | payload ptr `[s2+0x1c]` → `fcn.80010000` projector/emitter | reachable CONFIRMED / mesh LIKELY |

Recommended first edit (when authorized): **#1 source `vec[3]` @`0x07388`** — single clean 3×s32,
CONFIRMED-consumed render position, large reversible effect.

Recommended first edit unchanged after the runtime result below: **#1 source `vec[3]`** (translate)
or **#3 scale[3]** (resize) — both now CONFIRMED read by the runtime builder for a surviving row.

### G10 runtime result + builder case `0x8001ec44` (2026-06-14)

Operator watches on the pristine image (full table in
[`geometry_g10_payload_render_chain.md`](../src_re_geometry/geometry_g10_payload_render_chain.md) §7):

| watch | result | meaning |
|-------|--------|---------|
| READ `0x80167b80` (entry29 `vec[0]`) | HIT, PC shown `0x8001ec48` (read site `0x8001ec44 lw v0,(s2)`), `a0=0x80096ea8`, `s2=0x80167b80` | survivor source `vec[3]` read by builder case `0x8001ec44`; LIST_A active | CONFIRMED |
| EXEC `0x8001eb34` (`jr v0`) | HIT, `v0=0x8001ec44` | kind-dispatch selects case `0x8001ec44` | CONFIRMED |
| step → `0x8001ec44` | reached | case body entered | CONFIRMED |

**Iteration caveat (UNKNOWN):** dispatch snapshot `s2=0x80168d80` (`DAT 0x8588`) ≠ READ snapshot
`s2=0x80167b80` (entry29) — different survivor iterations, both via case `0x8001ec44`; `a0=0x8018faf4`
is an entry29-payload+4 residual. No one-row claim.

**Case `0x8001ec44` (bit3/scaled transform setup, CONFIRMED static decode `0x8001ec44..0x8001effc`):**
reads source `vec[3]`(`[s2+0/4/8]`)−camera → GTE leaf `0x8001474c`; stages `angle[3]`
(`[s2+0xc/0xe/0x10]`); selects a base 3×3 matrix from LUT `0x80089528` via `[s2+0x19]&0x1f`; multiplies
it by `scale[3]` (`[s2+0x12/0x14/0x16]`, `>>12`) into view scratch `0x1f8003b4` (loaded via
`0x800605c4`); computes `(camera−vec)·matrix`; then loads `a0 = [s2+0x1c]` (**payload pointer**),
`a2 = [s2+0x18]` (attr byte), `a1 = 0x190|0x8000` and tail-jumps `0x80020698` → `jal fcn.80010000`
(payload-vertex projector/emitter; payload = `{u32 count; vertex[]}`, `a0+=4` skips count).
**UPGRADE:** `scale[3]`/`angle[3]` are now CONFIRMED read directly by the runtime builder (table above
updated). **STILL OPEN:** `fcn.80010000`/`0x80060284` primitive type + payload vertex stride + GPU/OT
write target.

**Next recommended target:** static decode of `fcn.80010000` (+ `0x80060284`) to fix the payload
vertex stride / primitive type / OT write; optional narrow runtime write-watch on the OT buffer
(`a2`, e.g. `0x801cc554`) to capture one emitted primitive. Collision/pathing **UNKNOWN** (do not infer).

## 4.5. G11 — payload vertex format and primitive emission

**Status:** STATIC ISO ANALYSIS (2026-06-14). Read-only disasm + DAT byte trace; no patch/build. Full
detail: [`src_re_geometry/geometry_g11_payload_format.md`](../src_re_geometry/geometry_g11_payload_format.md).

**`fcn.80010000`** (`a0`=payload, `a1`=z/flag, `a2`=color<<3, `a3`=`0x1f800384`) is the **per-object
mesh draw routine**. It reads `payload[0]`=vertex count, advances `a0+=4` to the vertex table, then
(count>0) sets `s0`=command-stream start (`payload+4+count*0xc`) and runs the **command-stream loop**
`0x800102d0`: `lh ctrl=[s0]`; `bltz ctrl` ends; `type=ctrl&0x1f` → `jr (0x8001036c + type*8)`;
`ctrl&0x60` / `ctrl>>7` select shading/texture/color. Type-0 case `0x8001046c` = **triangle**: reads
3 vertex byte-offsets `[s0+2/+4/+6]`, `+a0` → vertex addrs, `lwc2` coords into the GTE, projects with
**RTPS** (`0x4a180001`) / **RTPT** (`0x4a280030`), backface-culls with **NCLIP** (`0x4b400006`),
screen/`Z`-clips, and packs a polygon into the OT/primitive buffer. CONFIRMED.

**`0x80060284`** = GTE **per-point transform helper** (32-bit entry `0x80060284`, 16-bit `0x800602b0`;
core `0x800602e0` = `mtc2 vec → GTE matrix op → mfc2 + sum`). **Not** libgpu. CONFIRMED.

**Payload layout (CONFIRMED):**

```
{ u32 vertexCount;
  Vertex verts[N];                 // stride 0xc: s16 x; s16 y; s16 z; s16 pad(=0); u32 attr
  PrimCmd stream[];                // u16 ctrl + vertex byte-offsets (+ per-type operands); bltz ends
}
```

Coordinates are s16 `x/y/z` at vertex `+0/+2/+4`; `attr@+8` LIKELY UV/normal/color. Primitives
reference vertices by **byte offset** (`0,0xc,0x18,…`). entry29 payload `DAT 0x2f2f8`: count 34,
v0=`(0,-744,-61)`; entry0 `DAT 0xb32c`: count 195, v0=`(1835,2349,5451)`. CONFIRMED bytes.

**Recommended first real visual-geometry edit (PROPOSAL ONLY; survivor entry29):**

| # | target | DAT off | effect | risk |
|--:|--------|--------:|--------|------|
| 1 (recommended) | source `vec[3]` | `0x7388` (3×s32) | translate whole object | low (single field, no topology change) |
| 2 | source `scale[3]` | `0x739a` (3×s16) | resize whole object | keep small; large value can explode/invert |
| 3 | payload vertex `v0.x/y/z` | `0x2f2fc/fe/0x2f300` (s16) | move one mesh vertex (true mesh deform) | subtle (1 of 34); don't touch `pad`/`attr` |

**Open:** per-type operand layout for non-triangle cases; `attr`(`vertex+0x8`) meaning; `count<=0`
alternate head path. **No runtime watch required for G11** (static-confirmed); collision/pathing
**UNKNOWN** (do not infer).

## 4.6. G12 — first real visual-geometry edit (entry29 source vec[0]) — RESULT: read-confirmed, visually silent

**Status:** RESULT 2026-06-14 — **VALID BUILD / PATCH LIVE / CPU READ CONFIRMED / NO OBVIOUS VISUAL
CHANGE.** This was the first edit aimed at *visible* geometry (vs. the G6–G9 trail/cull-row tests).
Full build record + operator steps in
[`src_re_geometry/geometry_g11_payload_format.md`](../src_re_geometry/geometry_g11_payload_format.md) §5.1.

**Result:** boots / LEVEL01 loads / no crash. `READ 0x80167b80` hit (count 1, PC shown `0x8001ec48`,
read site `0x8001ec44`, `s2=0x80167b80`) in `fcn.8001ea6c` case `0x8001ec44`; DuckStation memory
`0x80167b80` = `FFFFDCF0` (`f0 dc ff ff`, `-8976`) matching the patch. But the entry29 / edge-of-level
view showed no obvious lateral shift, mesh movement, or clipping change vs pristine. **Interpretation:**
the patched source vector is live and read, yet a whole-object origin nudge is visually silent in the
tested view (LIKELY masked by object size/distance/orientation, or the entry29 draw uses the `count<=0`
path / an unmodeled transform term). This does **not** disprove the G11 payload path. **Next is a
direct payload-vertex deformation (G13), not another source-vec delta.** Collision/pathing UNKNOWN.

**Target & rationale.** entry29 (the G9-confirmed survivor) source record `vec[0]` = the object's
render origin (G10 case `0x8001ec44` subtracts it from the camera and GTE-transforms it; G11 confirms
the payload mesh is drawn relative to it). `vec[0]` is the lateral (X-like) axis; entry29's payload
mesh is only ~±54 wide on X, so `+1024` is an unmistakable lateral translation. Crucially, visibility
culling is decided by the (unchanged) **trail-row** body vec, not this source vec — so the edit cannot
remove the object from the draw list; it only changes where it renders. Single-byte, reversible.

| item | value |
|------|-------|
| DAT offset | `0x7388` (runtime `0x80167b80`) |
| original → patched | `f0 d8 ff ff` (`-10000`) → `f0 dc ff ff` (`-8976`), delta `+1024` |
| revert | `f0 d8 ff ff` |
| changed bytes | exactly one (`0x7389`, `d8→dc`) |
| patch cmd | `python3 tools/patch_g12_entry29_source_vec_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G12_ENTRY29_VEC_TEST.DAT` |
| patched DAT SHA256 | `f01c2a0a90139217629994d1641faf7642cd32b53738f27061d2a0654f3f20ca` (sha1 `67b18e1a…`) |
| rebuild cmd | `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G12_ENTRY29_VEC_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G12_ENTRY29_VEC_TEST.bin --out-cue ABL_G12_ENTRY29_VEC_TEST.cue --report DAT/LEVEL01_LEVEL_G12_ENTRY29_VEC_TEST_REBUILD.md --write` |
| image | `ABL_G12_ENTRY29_VEC_TEST.cue` / `.bin` |
| embedded verify | LBA `2906`, embedded sha1 `67b18e1a…` == patched DAT (PASSED); `@0x7388`=`f0 dc ff ff` |
| staged restore | `REBUILD/files/LEVEL01/LEVEL.DAT` → pristine (`786b7a96…`) |
| artifacts | DAT/BIN/CUE/report gitignored, NOT committed |

**Operator test:** boot `ABL_G12_ENTRY29_VEC_TEST.cue`; enter LEVEL01; go to the edge-of-level area
where `READ 0x80167b80` / case `0x8001ec44` fired; compare to pristine at the same camera; look for a
whole-object lateral shift, clipping, no change, or crash. Optional CPU confirm: `READ 0x80167b80`
should hit in `fcn.8001ea6c` and live memory `0x80167b80` should read `f0 dc ff ff`. **Do not infer
collision/pathing.** "No visible change" is a valid result (would implicate the `count<=0` path or an
unmodeled transform). Semantics beyond "object render origin" UNKNOWN.

## 4.7. G13 — direct mesh deformation (entry29 payload vertex 0, y) — RESULT: read-confirmed, visually silent

**Status:** RESULT 2026-06-14 — **VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL
CHANGE.** Full record + operator steps in
[`src_re_geometry/geometry_g11_payload_format.md`](../src_re_geometry/geometry_g11_payload_format.md) §5.2.

**Result:** boots / LEVEL01 loads / no crash. **Watch-address lesson:** the watch on the inner s16
`0x8018faf6` did not hit (the vertex is loaded by a 32-bit `lwc2` at the vertex base, not a halfword at
the `y` offset); re-watching the aligned base `0x8018faf4` hit immediately at PC `0x80010928`
(`lwc2`) in `fcn.80010000` — so the edited vertex is read. But moving v0.y by `+512` was visually
silent (v0 is mid-body, lightly referenced, small inward delta). Does **not** disprove the payload
path. **Next: choose a vertex from command-stream references + silhouette (G14), with a larger delta.**
Collision/pathing UNKNOWN.

**Why a payload-vertex edit now:** G12 confirmed the source vector is read but a whole-object origin
nudge was visually silent. A payload-vertex edit is a **direct mesh-data deformation** — it changes the
vertex geometry itself and affects the specific triangle(s) using that vertex, bypassing the
whole-object-transform ambiguity. entry29 vertex 0 (byte offset `0x0000`) is referenced by the first
primitive command, so it is part of a real drawn triangle.

**Axis/delta:** across entry29's 34 vertices X spread = 119, **Y spread = 1769** (dominant, LIKELY
vertical), Z spread = 821 → `y` chosen for the most-recognizable single-vertex displacement; `+512`
≈ 29% of the object's Y extent, well within s16 range (fallback `+256` if it over-distorts).

| item | value |
|------|-------|
| field | entry29 payload **vertex 0, `y`** (`s16`) |
| DAT offset | `0x2f2fe` (runtime `0x8018faf6`) |
| original → patched | `18 fd` (`-744`) → `18 ff` (`-232`), delta `+512` |
| revert | `18 fd` |
| changed bytes | exactly one (`0x2f2ff`, `fd→ff`) |
| patch cmd | `python3 tools/patch_g13_entry29_payload_v0_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G13_ENTRY29_PAYLOAD_V0_TEST.DAT` |
| patched DAT SHA256 | `a6acffc33287637f5c228321e4dd94509c4c347f255d7743756dafce4c7505cf` (sha1 `b6eecbab…`) |
| rebuild cmd | `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G13_ENTRY29_PAYLOAD_V0_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G13_ENTRY29_PAYLOAD_V0_TEST.bin --out-cue ABL_G13_ENTRY29_PAYLOAD_V0_TEST.cue --report DAT/LEVEL01_LEVEL_G13_ENTRY29_PAYLOAD_V0_TEST_REBUILD.md --write` |
| image | `ABL_G13_ENTRY29_PAYLOAD_V0_TEST.cue` / `.bin` |
| embedded verify | LBA `2906`, embedded sha1 `b6eecbab…` == patched DAT (PASSED); `@0x2f2fe`=`18 ff` |
| staged restore | `REBUILD/files/LEVEL01/LEVEL.DAT` → pristine (`786b7a96…`) |
| artifacts | DAT/BIN/CUE/report gitignored, NOT committed |

**Operator test:** boot `ABL_G13_ENTRY29_PAYLOAD_V0_TEST.cue`; enter LEVEL01; go to the entry29
edge-of-level area; compare to pristine; look for one vertex/corner of a mesh chunk spiking or a single
triangle stretched (vs no change / crash). Optional CPU confirm: READ watch `0x8018faf6` should hit in
`fcn.80010000` (vertex `lwc2` load); live memory `0x8018faf6` should read `18 ff` (`-232`). **Do not
infer collision/pathing.** Semantics UNKNOWN.

## 4.8. G14 — command-stream-selected near-apex vertex (entry29 vertex 14, y) — RESULT: visible, non-tangible decor

**Status:** RESULT 2026-06-14 — **VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / VISIBLE RENDER
CHANGE / NON-TANGIBLE DECORATION.** Full record + command-stream analysis in
[`src_re_geometry/geometry_g11_payload_format.md`](../src_re_geometry/geometry_g11_payload_format.md) §5.3.

**Result:** the first **confirmed visible** payload-vertex edit — a geometry deformation appeared in the
entry29 area. The affected object is **grass / decorative foliage**, **not tangible** in gameplay.
CONFIRMED: payload vertex-coordinate edits visibly deform LEVEL01 render geometry; the G10→G11 model +
`fcn.80010000` emitter are validated end-to-end. entry29 (`DAT 0x2f2f8`) = grass/decor (LIKELY), a poor
target for tangible terrain. UNKNOWN: tangible terrain/collision source. **Do not infer
collision/pathing.** Next: pivot to a ground payload (§4.9 / G15).

**Selection (not a guess):** decoded entry29's primitive command stream (`DAT 0x2f494..0x2f59c`,
`ffff ffff` terminator). First prims: `0x2f494` type-2 quad strip (verts 0–11), `0x2f4c8` type-3
textured triangle strip (verts 12,13,14,17,…). A halfword scan for valid vertex byte-offsets shows
**all 34 verts referenced, 28 twice, 6 once** (v13,16,20,21,29,30). Reference frequency barely
discriminates → chose by silhouette + multi-triangle sharing: **vertex 14** (`(-20,-1601,-579)`,
refs=2, near-apex in a tall Y `0..-1769` / X `±60` mesh). Avoids the refs=1 apex tips v13/v16 whose
lone triangle could be culled (the G13 silent-result risk).

| item | value |
|------|-------|
| field | entry29 payload **vertex 14, `y`** (`s16`) |
| DAT offset | `0x2f3a6` (runtime `0x8018fb9e`; vertex base `0x8018fb9c`) |
| original → patched | `bf f9` (`-1601`) → `bf f5` (`-2625`), delta `-1024` (upward spike) |
| revert | `bf f9` |
| changed bytes | exactly one (`0x2f3a7`, `f9→f5`) |
| patch cmd | `python3 tools/patch_g14_entry29_payload_vertex_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.DAT` |
| patched DAT SHA256 | `0db535ebf0c879cba8fb704e02e3176418f699ecfcce736bd73363a19558c81c` (sha1 `53608e21…`) |
| rebuild cmd | `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.bin --out-cue ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.cue --report DAT/LEVEL01_LEVEL_G14_ENTRY29_PAYLOAD_VERTEX_TEST_REBUILD.md --write` |
| image | `ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.cue` / `.bin` |
| embedded verify | LBA `2906`, embedded sha1 `53608e21…` == patched DAT (PASSED); `@0x2f3a6`=`bf f5` |
| staged restore | `REBUILD/files/LEVEL01/LEVEL.DAT` → pristine (`786b7a96…`) |
| artifacts | DAT/BIN/CUE/report gitignored, NOT committed |

**Operator test:** boot `ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.cue`; enter LEVEL01; go to the entry29
edge-of-level area; compare to pristine **with breakpoints disabled / gameplay running** (breakpoint
frames are unreliable); look for a spike at the top of a mesh chunk / two stretched triangles (vs no
change / crash). Optional CPU confirm: READ watch the **aligned vertex base** `0x8018fb9c` (per the
G13 lesson) → hit in `fcn.80010000`; live `0x8018fb9e` should read `bf f5` (`-2625`). **Do not infer
collision/pathing.** Semantics UNKNOWN.

## 4.9. G15 — terrain/ground payload identification — RESULT: read-confirmed, visually silent

**Status:** RESULT 2026-06-14 — **VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL
CHANGE.** Full detail (runtime `a0`-log table §6, build record §7) in
[`src_re_geometry/geometry_g15_terrain_payload_candidates.md`](../src_re_geometry/geometry_g15_terrain_payload_candidates.md);
reusable tool `tools/survey_level01_payloads.py`.

**Result:** CPU READ `0x80170ba4` hit at PC `0x8001069c` (`lwc2`) in `fcn.80010000` (PATCH LIVE / vertex
read), but no visible spike/pit/displacement vs pristine. The watch fired at the vertex *load*, before
the backface/screen-bound/depth reject tests — so it does **not** prove v46's primitive was emitted.
**Read-confirmation ≠ visible.** Drives G16 (screen-space evidence). Collision/pathing UNKNOWN.

**Runtime result (the decisive step):** EXEC `0x80010000` `a0`-log while standing on ground →
the static "primary" `0x8018c234` is **rejected** (flat 1.76, count 37, instanced ×6 → decor; high
frequency = instanced decoration, NOT terrain). Picked **`0x80170978`** (DAT `0x10180`): wide
(X 7937), flat (0.30), 63 verts all referenced (connected surface), positive-Y ground stratum, drawn
once → terrain/ground render (LIKELY). The §2 static shortlist (e213/e128/e280) did **not** appear in
the log (not in the tested view), confirming runtime selection was necessary.

**Candidate TERRAIN-PV (BUILT):** payload `0x10180` central vertex **v46** `y`, `DAT 0x103ae`
(runtime `0x80170ba6`, base `0x80170ba4`), `86 1c` (`7302`) → `86 18` (`6278`, `-1024`). `-1024` drops
y below the surface min (`6738`) → an upward spike out of the ground (maximally visible). Patched DAT
SHA256 `1466f8e5…`; image `ABL_G15_RUNTIME_PAYLOAD_VERTEX_TEST.cue`; embedded verified at LBA 2906
(`@0x103ae`=`86 18`); staged restored to pristine. Artifacts gitignored/not committed.

**Operator test:** boot the image; enter LEVEL01; return to the runtime-log ground area; compare to
pristine **with breakpoints disabled**; look for a spike rising out of the ground (vs no change /
crash). CPU confirm: READ aligned base `0x80170ba4` → hit in `fcn.80010000`; live `0x80170ba6`=`86 18`.
**Do not infer collision/pathing — visual terrain ≠ collision** (background-element not fully excluded).

### Original static shortlist (superseded by runtime for the tested view, kept for reference)

**Discriminator (CONFIRMED metric):** flatness = `Yspread / max(Xspread, Zspread)`. Grass/decor are
tall+narrow (flatness > 2, small footprint, often instanced — multiple trail rows → one payload).
Terrain/ground are wide+flat (flatness < 0.5, footprint tens of millions, higher vertex count).

**Shortlist (CONFIRMED metrics; terrain role LIKELY; runtime = DATbase `0x801607f8` + payload):**

| cand | payload DAT | runtime | cnt | Xsp | Ysp | Zsp | flat | note |
|------|------------:|---------|----:|----:|----:|----:|-----:|------|
| e213 | `0x0d934` | `0x8016e12c` | 182 | 8410 | 4039 | 7571 | 0.48 | biggest footprint + high verts → major terrain (LIKELY) |
| e128 | `0x356bc` | `0x80195eb4` | 230 | 5838 | 3239 | 6700 | 0.48 | most verts, square footprint → ground (LIKELY) |
| e280 | `0x0eb14` | `0x8016f30c` | 124 | 7632 | 2245 | 4636 | 0.29 | very flat + wide → floor (LIKELY) |
| e282 | `0x0f6f4` | `0x8016feec` | 115 | 8085 | 2545 | 4697 | 0.31 | flat floor (LIKELY) |
| e264/e265 | `0x0945c`/`0x09dbc` | `0x80169c54`/`0x8016a5b4` | 94/131 | ~8200 | ~2400 | ~4500 | ~0.29 | adjacent flat-floor pair (LIKELY) |
| e17 | `0x22510` | `0x80182d08` | 60 | 11164 | 3110 | 5001 | 0.28 | huge but coarse → background slab? (UNKNOWN) |

**Static limit:** shape ≠ what is on screen in the tested camera; a big flat payload could be
background/ceiling. So:

**G15 PRIMARY (recommended next experiment) — runtime payload-pointer identification:**
1. Boot pristine; enter LEVEL01; frame the visible ground/tree surface to change.
2. Execute breakpoint at **`0x80010000`** (`fcn.80010000` entry); at entry **`a0` = payload pointer**.
3. Log `a0` over a few frames while looking at that ground.
4. Match logged `a0` against the shortlist runtime addresses → the match IS the on-screen ground.
5. Then edit that confirmed payload's central vertex (single s16, reversible) as G15-Candidate
   TERRAIN-PV.

**SECONDARY (only if skipping runtime):** lead static pick **e213**, central vertex **v21** `y`,
`DAT 0x0da36` (runtime `0x8016e22e`), `bd 15` (`5565`) → `bd 19` (`6589`, `+1024`); CPU confirm via
READ on aligned base `0x8016e22c`. Lower confidence — e213 may be terrain, a prop, or background until
runtime confirms. **Do not assume any candidate is tangible/collidable** (render evidence only).

## 4.10. G16 — screen-space vertex selection — VISIBLE WALL RENDER CHANGE CONFIRMED

**Status:** VISIBLE WALL RENDER CHANGE CONFIRMED 2026-06-14. Full detail
(runtime hit table §6, build record §7, visual result §9) in
[`src_re_geometry/geometry_g16_screen_space_vertex_selection.md`](../src_re_geometry/geometry_g16_screen_space_vertex_selection.md).

**Visual result (operator, 2026-06-14):** `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue` boots, LEVEL01
loads, no crash, no black screen, and a **visible deformation** was found. The affected geometry is a
**vertical wall/cliff face — NOT the walkable floor/top surface**. Classification:
**VALID BUILD / PATCH LIVE / EMITTED PAYLOAD CONFIRMED / VISIBLE WALL RENDER CHANGE.**

CONFIRMED: (a) payload vertex edits visibly deform terrain-family render geometry; (b) payload `0x356bc`
is screen-space/emitted and visibly editable; (c) payload `0x356bc` is **wall / vertical terrain face,
not floor/top-surface** — **reclassified** from the G15/G16 "terrain/ground (LIKELY)" guess. This is the
first end-to-end *terrain-family* deform (G14 was grass/decor); the screen-space gate (`0x800108b4`) was
the right method, but emit-in-the-ground-view is **necessary, not sufficient** — a wall in the frame also
emits. UNKNOWN: collision/pathing impact; the walkable floor/top-surface render payload; whether any
visual floor payload is coupled to collision. **Do not infer collision/pathing; this is not a floor
collision edit.** G16 succeeded as a visible render edit but **not** as a walkable-floor target →
**G17 (§4.11).**

**Why:** G12–G15 were all read-confirmed but visually silent. The G15 watch fired at the `lwc2` vertex
load (`0x8001069c`), **before** the reject tests — so "vertex is read" does not prove its primitive is
drawn. G16 requires **screen-space evidence** (emitted primitive).

**Runtime result:** EXEC `0x800108b4` (packet-store gate, past all RTPS/RTPT/NCLIP/AVSZ4 rejects) while
on ground → payload `0x356bc` (= static e128, rt `0x80195eb4`) emitted **≥5** primitives; `0x1b9f0`
(rt `0x8017c1e8`) **≥2**. These are emit-confirmed on-screen terrain candidates. Two corrections from
the log: (a) at `0x800108b4`, `a0` = vertex-table pointer ⇒ payload base = `a0 − 4`; (b) `t5/t6/t7`
there are reused packet/OT/color words (the logged values unpack to impossible screen coords), so clean
screen XY must be read from the packet at `s3` (offsets `+0x00/0x08/0x0c/0x14/0x18/0x20`) or via a BP
at `0x80010718` — `t5/t6/t7`→pixel mapping is TODO.

**Candidate EMITTED-PV (BUILT):** payload `0x356bc` (230 verts, X 5838, Y 5093–8332 ground stratum,
Z 6700) vertex **v10** `y` — central within the observed-emitted first-command quads (hits 1–5 =
verts 0–19) — `DAT 0x3573a` (rt `0x80195f32`, base `0x80195f30`), `b9 1a` (`6841`) → `b9 16` (`5817`,
`-1024`). Patched DAT SHA256 `96206e69…`; image `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue`; embedded
verified at LBA 2906 (`@0x3573a`=`b9 16`); staged restored to pristine. Artifacts gitignored/not
committed. Escalation if subtle: v10.y `-2048` (`b9 12`, below surface min → spike above the surface).
**Visual terrain ≠ collision** — do not infer.

**`fcn.80010000` decode (CONFIRMED):** each case projects vertices (RTPS `0x4a180001` @`0x800106a8`,
RTPT `0x4a280030` @`0x800106f8`), reads packed screen XY via `mfc2 SXY0/1/2` (regs 12/13/14) →
`t5/t6/t7` (each `(screenY<<16)|screenX`, signed halves), then runs **NCLIP** backface
(`0x4b400006`), screen-bound (`sltiu …,0x200`), and **AVSZ4** OT-depth (`0x4b68002e`) rejects — **all
jumping to skip `0x800108b8`**. A surviving primitive stores its screen-XY into the GPU packet at `s3`
(offsets `+0x00/0x08/0x0c/0x14/0x18/0x20`) and advances `addi s3,s3,0x34` at `0x800108b4`.

**Screen-space capture (ISO-identified; one narrow GUI BP):** execute BP at **`0x800108b4`** (packet
fully written, past all rejects). Read `a0` (payload → DAT off `a0−0x801607f8`) and the packet at `s3`
(unpack screen X=low s16, Y=high s16). A primitive is on-screen iff X/Y fall in the visible window
(≈`0..320`×`0..240`). Static DAT cannot derive projected screen position (camera/player dependent), so:

*(The runbook above was EXECUTED — see the §4.10 runtime result and the §6/§7 record in the G16 doc.
It selected payload `0x356bc` and Candidate EMITTED-PV v10, now BUILT.)* **Visual terrain ≠ collision**
— do not infer.

## 4.11. G17 — walkable floor / top-surface payload target

**Status:** RUNTIME RESULT 2026-06-14 — the emitted floor is an **output-buffer/heap payload**, not a
LEVEL.DAT payload. No patch, no build. Full detail in
[`src_re_geometry/geometry_g17_floor_payload_candidates.md`](../src_re_geometry/geometry_g17_floor_payload_candidates.md);
source trace in §4.12 / [`geometry_g18_output_buffer_floor_trace.md`](../src_re_geometry/geometry_g18_output_buffer_floor_trace.md).

**Candidate B runtime result:** broad walkable floor view, Flik centered, EXEC `0x800108b4` — all 17 hits
were one payload `a0=0x801bdc5c` → base **`0x801bdc58`**: raw DAT off `0x5d460` is **INVALID** (`>0x51418`
EOF), output-buffer offset `0xc048`. Classification **EMITTED FLOOR/TOP-SURFACE CANDIDATE /
RUNTIME-GENERATED OR OUTPUT-BUFFER PAYLOAD / DAT SOURCE UNKNOWN**. The walkable floor is **not** in
LEVEL.DAT → the static floor shortlist below (e135/e254/e52/`0x1b9f0`) does not apply to this view; it is
kept only as the LEVEL.DAT flat-payload record. Collision/pathing UNKNOWN. (The original PLANNED shortlist
and runbook follow.)

**Goal:** find a **walkable floor / top-surface** render payload — the flat horizontal surface Flik
stands on — using emitted-primitive evidence (EXEC `0x800108b4`), not bbox metrics alone. Filter for
floor, not the G16 vertical wall.

**Why the G16 wall is not the floor (CONFIRMED metric signal):** `0x356bc` (e128) has local Y spread
(q25–q75) `1354` and flatness `0.48` — the *least* flat of the static "terrain" shortlist; its visible
deform was a wall/cliff. True floor candidates are flatter with a tighter local Y band.

**Floor filter (prioritise):** emit while the camera looks at / Flik stands on the walkable ground; broad
X/Z spread; low/flat local Y variation; visually the top surface where Flik can stand; **not**
grass/decor (`0x2f2f8` family); **not** a vertical wall/cliff (`0x356bc`); **emitted-primitive evidence,
not vertex-read-only**.

**Static floor shortlist (CONFIRMED metrics; role LIKELY; NO emitted evidence yet — runtime gate
required):**

| cand | payload DAT | runtime | cnt | Xsp | Ysp | Zsp | flat | local Yband (q25–q75) | refs | role (confidence) |
|------|------------:|---------|----:|----:|----:|----:|-----:|----------------------:|------|-------------------|
| **e135** | `0x1f148` | `0x8017f940` | 110 | 5546 | 1069 | 4541 | **0.19** | 409 | e135 (unique) | flattest wide surface → **floor (LIKELY)** |
| **e254** | `0x08f4c` | `0x80169744` | 53 | 6756 | 1504 | 4120 | **0.22** | 636 | e254 (unique) | very flat wide → **floor (LIKELY)** |
| **e52** | `0x17d94` | `0x8017858c` | 122 | 5005 | 1128 | 5000 | **0.23** | 622 | e52 (unique) | flat, square footprint → **floor (LIKELY)** |
| **e280** | `0x0eb14` | `0x8016f30c` | 124 | 7632 | 2245 | 4636 | 0.29 | 812 | e280 (unique) | flat + wide → **floor (LIKELY)** |
| **e264/e265** | `0x0945c`/`0x09dbc` | `0x80169c54`/`0x8016a5b4` | 94/131 | ~8300 | ~2400 | ~4500 | 0.28/0.30 | 684/649 | adjacent pair → **floor region (LIKELY)** |
| `0x1b9f0` (**lead, partial emit**) | `0x1b9f0` | `0x8017c1e8` | 92 | 4513 | 1427 | 4130 | 0.32 | 573 | e160 (unique) | flat, **≥2 emitted prims in the G16 ground-view log** → strongest floor lead, but role floor-vs-flat-ledge UNKNOWN until re-logged on the floor |

(All are unique/drawn-once — unlike instanced decor whose `a0` repeats. e128/`0x356bc` excluded = wall;
`0x2f2f8` excluded = grass.)

**Recommendation:** run the G17 runtime runbook (below) before any edit. The lead is `0x1b9f0` (already
has partial emit evidence); the flatter static picks (e135/e254/e52) are backups to confirm at the
`0x800108b4` gate while framing the floor. **Do not build from bbox alone** (guardrail). Build only after
a floor payload is emit-confirmed *and* its primitive's screen position lands on the walkable floor.

### G17 runtime runbook (DuckStation, operator)

1. **Use the pristine image** (`Disney-Pixar A Bug's Life (v1.0).cue` rebuild base), unless specifically
   re-testing a later G17 patch. Confirm `mem32[0x80082498]=0x801607f8` (DATbase).
2. **Stand on / look directly at the walkable floor/top surface** so it fills the screen (the flat ground
   Flik stands on, not a wall, not grass). Avoid framing cliffs.
3. Set **EXEC breakpoint `0x800108b4`** (`addi s3,s3,0x34`, the packet-store gate past all
   RTPS/RTPT/NCLIP/AVSZ4 rejects in `fcn.80010000`). Disable all other breakpoints/watches.
4. Record **10–20 hits** while the floor fills the view. For each:
   - `a0`
   - payload base = `a0 − 4`
   - payload DAT offset = payload base − `0x801607f8`
   - `s3` (packet pointer)
   - hit number
   - brief visual/camera note (what the floor looks like; is a wall also in frame?)
5. **Prefer hits that occur while the visible floor fills the screen** (minimise wall/grass in frame),
   and prefer `a0` values that map to the flat shortlist above (e135/e254/e52/e280/e264/e265 or the
   `0x1b9f0` lead). High-frequency repeated `a0` = instanced decor (reject, per G15).
6. **Do not use paused-frame / breakpoint-frame visuals as the final comparison** — capture with
   breakpoints disabled and gameplay running.

Screen-coordinate capture (optional, to prove the primitive lands on the floor, not a wall): at
`0x800108b4` read the just-written packet at `s3` (screen-XY words at `s3+0x00/0x08/0x0c/0x14/0x18/0x20`;
unpack X = low s16, Y = high s16; on-screen ≈ `0..320`×`0..240`). The cleaner alternative is an EXEC BP
at **`0x80010718`** (right after `mfc2 SXY0/1/2`) reading `t5/t6/t7` (each `(screenY<<16)|screenX`). A
floor primitive should project into the **lower/central** screen band (where the ground is), a wall into
the **upper/side** band — use this to disambiguate floor from wall. (`t5/t6/t7` at `0x800108b4` are
reused packet words — do NOT read SXY there; that was the G16 correction.)

**After the log:** pick the flattest emit-confirmed floor payload whose primitive screen-XY lands on the
walkable floor; choose its central, multiply-referenced vertex; then (and only then) build a single-s16,
reversible Y deform via `tools/patch_g17_floor_payload_vertex_test.py`. Collision/pathing UNKNOWN — do
not infer; visual floor ≠ collision floor.

## 4.12. G18 — output-buffer floor payload trace (`0x801bdc58`)

**Status:** STATIC ISO TRACE + RUNTIME RUNBOOK 2026-06-14. No patch, no build. Full detail in
[`src_re_geometry/geometry_g18_output_buffer_floor_trace.md`](../src_re_geometry/geometry_g18_output_buffer_floor_trace.md).

**Goal:** trace the G17 floor payload `0x801bdc58` to its DAT source or generator.

**Output-buffer / DAT-EOF correction (CONFIRMED):**

| address | meaning |
|---------|---------|
| `0x801607f8` | DATbase |
| `0x801b1c10` | DAT EOF = DATbase + filesize (`0x51418`) = pass-1 output base |
| `0x801b5890` | pass-1 `ParserOutputRecord20[484]` end (`+0x3c80`) |
| `0x801b6a10` | parser reserved end (`+0x4e00`); heap cursor → next resource |
| **`0x801bdc58`** | floor payload = EOF `+0xc048` = reserved-end `+0x7248` (in the **next-resource** heap region) |

`0x5d460` is **not** a DAT offset (past EOF); the floor is **not** the loaded DAT, the pass-1 matrix output
buffer, or the reserved gap.

**Static trace (CONFIRMED):**
- Parser `fcn.8001cdc0` is called **once** (`jal @0x8003d568`) → LEVEL.DAT parsed once; no second-parse
  heap source records.
- All **1248** LEVEL.DAT relocation targets are in `[0x45f0, 0x4f32c]` (`tools/dat_reloc.py`); max `0x4f32c`
  is `0xe134` below the floor's required `0x5d460` → **no parser-relocated pointer equals `0x801bdc58`.**
- The emitter loads the payload pointer **directly** from the source record with **no base add**:
  `0x80020684 lw a0,0x1c(s2)` / `0x80020694 lw a0,0x20(s2)` → `0x80020698 jal fcn.80010000` (the function's
  only real caller). So `[s2+0x1c]`/`[s2+0x20]` already holds the **absolute** payload address; for the
  floor it holds a heap pointer the parser did not write → **runtime-written** (a generator), or `s2` is
  itself heap-resident.

**Separate terrain resources (LIKELY source):** LEVEL01 ships `LEVEL.RAW` (`0xb68e4`), `LEVEL1.RAW`
(`0x84210`), `TERRAIN.ALL` (`0x39d8c`), `TERR1.ALL` (`0xf078`) beside `LEVEL.DAT`; `TERRAIN.ALL`/`TERR1.ALL`
begin with s16 coordinate-pair streams (terrain mesh, **not** in the `fcn.80010000` payload format →
converted at runtime). The executable references the names (`level.raw`, `bits\plantter.all`, `terr1`,
`.all`). The next-resource heap region (where `0x801bdc58` sits) is where such a resource lands. This also
explains every prior negative: **the walkable floor is not in LEVEL.DAT**, so no LEVEL.DAT vertex edit
moved it.

**Recommendation (DAT source NOT found):** one narrow runtime check —
1. **WRITE watch `0x801bdc58`** during LEVEL01 load/before gameplay → the breaking PC = the
   generator/writer; record the source pointer it copies from (reveals the originating resource).
2. EXEC BP at `0x80020684` conditioned `a0==0x801bdc5c` → read **`s2`**: `< 0x801b1c10` ⇒ DAT source record
   (its `+0x1c`/`+0x20` was runtime-written; `DAT off = s2 − 0x801607f8`); `≥ 0x801b1c10` ⇒ heap-resident
   object. Also read `[s2+0x1c]`/`[s2+0x20]`/`[s2+0x18]`.

Do **not** patch runtime-buffer addresses or treat `0x5d460` as a DAT offset. Collision/pathing UNKNOWN —
visual floor ≠ collision floor.

## 4.13. G18 — DAT-backed emitted payload `0x2d460` (Candidate B-like view) — INSTANCED DECOR, not floor

**Status:** RUNTIME LOG RECORDED + STATIC DECODE 2026-06-14. No patch, no build. Full detail in
[`src_re_geometry/geometry_g18_dat_backed_floor_candidate.md`](../src_re_geometry/geometry_g18_dat_backed_floor_candidate.md).

The operator moved very close to the earlier Candidate B walkable-floor view (not pixel-identical) and ran
EXEC `0x800108b4` again. This time all parsed hits showed a **different, DAT-backed** payload:

| field | value |
|-------|-------|
| `a0` | `0x8018dc5c` |
| payload base (`a0−4`) | `0x8018dc58` |
| DAT offset (`−DATbase 0x801607f8`) | **`0x2d460`** — **VALID** (`< 0x51418` EOF) |
| earlier exact Candidate B (for contrast) | base `0x801bdc58` → off `0x5d460` — **INVALID** (heap, past EOF) |

**Do NOT merge** this Candidate B-like log with the earlier exact Candidate B output-buffer log: the runtime
bases differ (`0x8018…` vs `0x801b…`) and map to entirely different payloads (DAT vs heap). The log proves
`0x2d460` is direct LEVEL.DAT-backed and emit-confirmed (≥17 primitives past all rejects); 17-hit `s3` table
in the candidate doc §1.

**Static decode of `0x2d460` (CONFIRMED bytes) — supersedes the operator's "floor candidate" read:**

| field | value |
|-------|-------|
| count | **25** verts |
| vertex table | `DAT 0x2d464` (rt `0x8018dc5c`), stride `0xc` |
| command stream | `DAT 0x2d590 .. 0x2d6ec` (348 B); first cmd `ctrl 0x0060` (type 0, shade 3) + element count `0x000e`=14, verts 0,1,2,3,… |
| bbox | X `[-103,99]` (202), Y `[-107,0]` (107), Z `[-97,97]` (194) |
| flatness Ysp/max(Xsp,Zsp) | **0.53** (fails floor filter `<0.35`) |
| reference histogram | all 25 verts referenced (2–5× each, none once) → closed connected blob |
| **pass-1 references** | **93** distinct source records → **heavily instanced** (flag `0x19`, scale ≈`(4349,4096,3153)`, varied vec/angle scattered across X`[-11255,9240]`/Z`[-14150,24980]`) |

**Role: DAT-BACKED EMITTED PAYLOAD / INSTANCED DECOR-PROP (93×), NOT WALKABLE FLOOR / COLLISION UNKNOWN.**
This is the same trap G15 flagged (high-frequency instanced `a0` = decor → reject; ×93 here). The walkable
floor that fills the screen remains the heap payload `0x801bdc58` (off `0x5d460`, §4.12), not in LEVEL.DAT.

**Edit-target decision: NO build.** `0x2d460` fails every floor criterion (instanced, tiny footprint, flat
0.53). A `…_FLOOR_VERTEX_TEST` on instanced decor would mislabel it, and payload-vertex visibility is already
proven (G14 grass / G16 wall). A *reference-only* proposed decor-confirmation edit (bottom apex v22 `y`,
`DAT 0x2d56e` `95 ff`/−107 → `95 fb`/−1131, −1024) is recorded in the candidate doc §4 but **not** built or
committed. Guardrails: no DAT/CUE/BIN artifacts; no collision/pathing claim; single vertex; visual ≠ collision.

## 4.14. G19 — floor/terrain resource source (pivot from `a0` reproduction)

**Status:** STATIC RESOURCE INVENTORY + LOADER TRACE + RUNTIME-CHECK PROPOSAL 2026-06-14. No patch, no build.
Full detail in [`src_re_geometry/geometry_g19_floor_resource_source.md`](../src_re_geometry/geometry_g19_floor_resource_source.md).

**Reproducibility correction (recorded):**
- `0x801bdc58` (runtime floor payload, EXEC `0x800108b4`, `a0=0x801bdc5c`): **OBSERVED ONCE / IMPORTANT /
  NOT CURRENTLY REPRODUCIBLE** — DuckStation GUI has no conditional breakpoint, so re-hitting the exact `a0`
  by F5 is too fragile to be a workflow. DAT source UNKNOWN.
- `0x8018dc58` / DAT `0x2d460` (reproducible in nearby views): **DAT-backed instanced decor/pebble, NOT floor**
  (G18b). Stop grinding for `0x801bdc5c`.

**LEVEL01 sidecar inventory (CONFIRMED, `REBUILD/files/LEVEL01/`):**

| file | hex size | classification |
|------|---------:|----------------|
| `LEVEL.DAT` | `0x51418` | parsed DAT (base `0x801607f8`) — props/decor/walls/grass |
| **`LEVEL1.DAT`** | `0x1a568` | **parser-format DAT; contains wide-flat floor payloads** (18 floor-signature) |
| **`LEVEL2.DAT`** | `0x40784` | **parser-format DAT; contains big floor payloads** (73 floor-signature) |
| `LEVEL.RAW` / `LEVEL1.RAW` | `0xb68e4` / `0x84210` | **compressed** (magic `00 00 83 0c`) |
| `TERRAIN.ALL` / `TERR1.ALL` | `0x39d8c` / `0xf078` | **uncompressed s16 (x,z) coordinate streams** + `01 00 02 00` sub-header |
| `LEVEL.BIN` / `LEVEL1.BIN` | `0x690` / `0xa8c` | **MIPS overlay code** |
| `LEVEL1A.VB/VH`, `LEVEL2C.VB/VH` | — | VAB audio |

**Loader (CONFIRMED disasm):** `fcn.8003cf2c` = resource-id dispatcher (jump table `0x8001afb0`, 17 handlers,
**4 callers**) → shared file-read `fcn.80046330` (`0x8003d550`, sets DATbase `[0x80082498]`) + parse
`fcn.8001cdc0` (`0x8003d568`). **CORRECTION to G18:** the parser's single static call site executes **once
per DAT loaded**, not once total (the loader is per-resource with 4 callers) — so a **second parsed DAT**
relocates against its own heap base and its payloads land in the `0x801bxxxx` region where the floor lives.
(G18's "floor not in the LEVEL.DAT image at `0x801607f8`" remains correct.)

**Floor-source hypotheses (ranked):** **H1 (LEADING)** = a second parsed DAT (`LEVEL1.DAT`/`LEVEL2.DAT`),
which natively contain wide-flat floor payloads in the exact `fcn.80010000` format (no converter needed);
**H2** = runtime conversion of `TERRAIN.ALL`/`TERR1.ALL` s16 streams (weaker, needs a converter);
**H3** = decompressed `.RAW` (least likely). Exact file+offset **UNKNOWN** — no naive second-DAT base
(`0x801b1c10`/`0x801b5890`/`0x801b6a10`) makes `0x801bdc58` land on a clean payload, so an intervening
load/alignment shifts the second DAT's base.

**Next (proposed, no `a0` reproduction):** deterministic loader trace at LEVEL01 load — EXEC BP `0x8003d550`
(read path `a0`=`sp+0x10`, dest base `a1`, size) and `0x8003d568` (read DATbase `[0x80082498]`, filesize) to
log every `(filename → base, size)`; the DAT whose `[base, base+size)` contains `0x801bdc58` owns the floor
(offset = `0x801bdc58 − base`). Alternative: WRITE-watch `0x801b6a10` during load. Guardrails: no patch/build;
each DAT has its own base (don't treat past-EOF as same-DAT offsets); collision/pathing UNKNOWN.

## 4.15. G20 — sidecar loaders; LEVEL.DAT-only trace → terrain `.all` is the leading floor source

**Status:** STATIC LOADER MAP + RUNTIME-RUNBOOK 2026-06-14. No patch, no build. Full detail in
[`src_re_geometry/geometry_g20_sidecar_loader_trace.md`](../src_re_geometry/geometry_g20_sidecar_loader_trace.md).

**Loader-trace result (operator):** `EXEC 0x8003d550` and `EXEC 0x8003d568` each hit **once** during
"Loading Level…", `a1=0x51418` at the parse = LEVEL01/LEVEL.DAT; no further hits. **Conclusion:** the parser
`fcn.8001cdc0` runs **exactly once for LEVEL01** (LEVEL.DAT only) → **G19's H1 (floor = a second parsed DAT)
is REFUTED**; G18's empirical "parser once" stands. Stepping deeper into this path is circular.

**Why `0x8003d550`/`0x8003d568` is insufficient:** it is the *only* one of the **14** `fcn.80046330`
file-read sites that feeds the parser; every other resource (terrain `.all`, `memory.bin`, FMV, audio,
`.anm`, and a high-heap streamed load) loads via a **different** site and **bypasses** `fcn.8001cdc0`. The
operator watched only the DAT path, so the floor-producing load was never observed.

**Prime non-circular target — the terrain `.all` loader (CONFIRMED disasm):**
`fcn.8005d654` (sidecar load loop, 16 callers, indexes object table `0x800a6300`) → `fcn.8002ffa8` (builds
`<name>.all` from name table `0x80082128`=`.all`/`0x80082138`=`terr1`/`0x80082150`=`terrain`; file-read
`0x8002ffe4` to `[s0]`) → `fcn.8002fce8` (processes the `.all` s16 stream into `0x4c`-stride records at
`0x80098a8a`). The orchestrator loads each terrain slot into a **heap cursor `[s1]`** and advances it — the
same allocation pattern that put LEVEL.DAT's cursor at `0x801b6a10`, so the terrain data lands in the
`0x801bxxxx` region where the floor `0x801bdc58` lives. `TERRAIN.ALL`/`TERR1.ALL` are s16 `(x,z)` streams
(not verbatim payloads; `0x7248` is not a payload in either) → the floor mesh is **runtime-generated** from
them. This is **not** the LEVEL.DAT path (different file, different file-read site, calls `fcn.8002fce8` not
`fcn.8001cdc0`).

**Hypotheses re-ranked:** **H2 (terrain `.all` → generated floor) now LEADING**; **H1 (second parsed DAT)
REFUTED**; **H3 (decompressed `LEVEL.RAW`) open/lower** (candidate: high-heap loader `0x8003a388`, dest
`~0x801cc390`).

**Recommended runbook (one, deterministic, no `a0` repro):** EXEC `0x8002ffe4` (+ sibling `0x80030dc0`) at
LEVEL01 load — record `a0` (built filename string), `a1` (dest base), step over to get size, `s0/s1/s2/ra`;
test whether `a1 ≤ 0x801bdc58 < a1+size` → floor lives in that terrain file (offset `0x801bdc58 − a1`).
Fallback: EXEC `0x8003a388` (high-heap loader). No patch/build; collision/pathing UNKNOWN.

**⚠ SUPERSEDED by G21 (§4.16):** the operator armed `EXEC 0x8002ffe4`/`0x80030dc0` and got **0 hits** → the
terrain `.all` runbook is **not confirmed** (the orchestrator skips the file-read when the terrain is cached,
and `fcn.8003a318` is indirect). Use the **callee-entry** runbook (`EXEC 0x80046330`) instead.

## 4.16. G21 — `fcn.80046330` caller map; terrain `.all` BPs did not fire → watch the callee entry

**Status:** NEGATIVE RUNTIME RESULT + FULL STATIC CALLER MAP + ONE RUNBOOK 2026-06-14. No patch, no build.
Full detail in [`src_re_geometry/geometry_g21_file_read_caller_map.md`](../src_re_geometry/geometry_g21_file_read_caller_map.md).

**Negative result:** `EXEC 0x8002ffe4` and `EXEC 0x80030dc0` (the G20 terrain `.all` reads) each hit **0**
times during LEVEL01 load. **G20's "prime confirmed target" is REFUTED**; H2 (terrain `.all` → floor) is
**open/unconfirmed**, not leading. Two CONFIRMED structural reasons call-site BPs keep missing the floor load:
(a) orchestrator `fcn.8005d654` **skips the file-read when the terrain is already resident** (`0x8005d76c
bnez v0,0x8005d794` → processor `fcn.8002fce8` runs with no file load); (b) the high-heap loader
`fcn.8003a318` (read `0x8003a388`) is reached **indirectly** (no direct `jal`), so no call-site BP catches it.

**Full `fcn.80046330` caller map (14 sites → 11 functions, CONFIRMED disasm):** `fcn.80046330(a0=filename,
a1=dest)` is the universal file loader. Sites: **#1** `0x8003d550` `fcn.8003cf2c` = LEVEL resource dispatcher
(builds `level<N>.<ext>` → loads all `level*.dat/raw/bin`; **fired once = LEVEL.DAT `0x51418`**); #2/#10
memory.bin; #3/#4 terrain `.all` (`fcn.8002ffa8`/`fcn.80030d64`, **0 hits**); **#6** `0x8003a388`
`fcn.8003a318` high-heap loader (**dest `0x801cc390 − align(size)` top-down**, indirect — PRIME); #7 fixed;
#8/#9 FMV; #11/#12 audio; #13 fixed; #14 `.anm`. All `level*.{dat,raw,bin}` funnel through #1, which fired
only for LEVEL.DAT → the other level files did not load via the dispatcher in the window.

**High-heap suspect:** `fcn.8003a318` loads a file to `0x801cc390 − size`; for `TERR1.ALL` (`0xf078`) →
region `[0x801bd318, 0x801cc390)` **contains** the floor `0x801bdc58` (offset `0x940`); for `LEVEL1.DAT`
(`0x1a568`) → contains it at `0xbe30`. Exact bytes there are not a clean payload in the raw files (floor is
**generated**, not verbatim) — static can't pin it; the runbook can.

**Recommended runbook (ONE, broad-but-narrow):** **EXEC `0x80046330`** (callee entry) — every file load funnels
here, including the indirect high-heap loader and any cached-skip case. Record `a0` (filename C-string), `a1`
(dest base), `ra` (caller → subsystem via the §2 map), and `v0` at return (size, via one-shot BP at `ra`).
Test `a1 ≤ 0x801bdc58 < a1+size` per load → the file that brackets it is the floor source (offset
`0x801bdc58 − a1`). If none brackets it through load→gameplay, the floor is **cached/boot-generated** →
escalate (arm `0x80046330` from the title screen, or watch processor `EXEC 0x8002fce8`). No patch/build;
collision/pathing UNKNOWN.

## 4.17. G22 — high-heap load brackets the floor; source file = LEVEL.RAW (processed, not verbatim)

**Status:** BRACKET CONFIRMED + SOURCE FILE IDENTIFIED 2026-06-14. No patch, no build. Full detail in
[`src_re_geometry/geometry_g22_high_heap_floor_source.md`](../src_re_geometry/geometry_g22_high_heap_floor_source.md).

**The G21 callee-entry runbook worked.** `EXEC 0x80046330`, **Hit #4** (`ra=0x8003a390` = the indirect
high-heap loader `fcn.8003a318`): dest `a1 = 0x80115aac`; at the loader return `v0 = 0xb6be4` (size). Range
`[0x80115aac, 0x801cc690)` **brackets the floor `0x801bdc58`** → source offset `0x801bdc58 − 0x80115aac =
0xa81ac`. **Hit #6** control = LEVEL.DAT (`a1=0x801607f8`, `ra=0x8003d558`), does not bracket.

**Source file = LEVEL.RAW (CONFIRMED by size + dest):** `fcn.8003a318` sets `dest = 0x801cc390 −
align(filesize)`; `0x801cc390 − 0x80115aac = 0xb68e4` = **LEVEL.RAW's exact logical size** (bytes-read `0xb6be4`
= `+0x300` sector/read padding). No other sidecar is within 200 KB. `0xa81ac` is 92% through LEVEL.RAW.

**But not verbatim/editable at `0xa81ac`:** `LEVEL.RAW[0xa81ac]` `u32 = 0x70d4001a` is an impossible vertex
count — it is a structured **indexed-geometry stream** (incrementing indices), **not** the `fcn.80010000`
`{u32 count; vertex 0xc; cmds}` format. The floor emitted a *valid* payload at runtime, so the runtime floor at
`0x801bdc58` **differs** from the loaded LEVEL.RAW byte at `0xa81ac` → the floor is **converted/generated from
LEVEL.RAW at runtime**, confirming G18's "runtime-generated floor" and **naming the source file**. A direct
`0xa81ac` file-offset edit is **invalid**. `fcn.8003a318` is a resource-setup function (loads LEVEL.RAW, inits
global tables) — the buffer is consumed by the geometry converter.

**Recommendation (Option A — file identified, decode the source):** read-only decode of LEVEL.RAW's geometry
format around `0xa81ac` (vertex pool, index grammar) toward an eventual LEVEL.RAW-format edit (never a LEVEL.DAT
edit), plus one deterministic confirmation at Hit #4 (read `a0` C-string = "level.raw"; read `0x801bdc58` right
after the load and compare to `LEVEL.RAW[0xa81ac]` = `1a 00 d4 70` to settle verbatim-vs-processed). **Do not
patch.** Collision/pathing UNKNOWN.

## 4.18. G23 — LEVEL.RAW is COMPRESSED; the floor is decompressor output (no editable field at 0xa81ac)

**Status:** READ-ONLY LEVEL.RAW + decompressor analysis 2026-06-15. No patch, no build. Full detail in
[`src_re_geometry/geometry_g23_level_raw_floor_format.md`](../src_re_geometry/geometry_g23_level_raw_floor_format.md).

Decoding `LEVEL.RAW` around `0xa81ac` shows it is **not** geometry — it is **compressed data** (the `[0xa8000,
0xa8400)` window has 213 distinct bytes/1024 with high entropy; s16 reads are noise; a full-file scan finds **0**
clean `fcn.80010000` payloads). The G22 high-heap loader `fcn.8003a318` loads LEVEL.RAW then calls
**`fcn.8001a1dc`**, an **LZ/Huffman bitstream DECOMPRESSOR**: `fcn.8001a1dc(a0 = LEVEL.RAW @0x80115aac compressed,
a1 = [gp+0x588] decompressed output)`. Evidence (CONFIRMED disasm): full register-context save/restore (all GPRs),
big-endian control-word fetch, bit-by-bit flag reader, literal-run copy (`0x8001a418`: `lbu;sb;a1++`), back-reference
match (`0x8001a658`), no `jal`, **no GTE/cop2**, single caller (`0x8003a4e4`). Span `0x8001a1dc..0x8001a8f8`.

**Consequence:** the floor at runtime `0x801bdc58` is the **decompressor's OUTPUT** (a valid `fcn.80010000` payload),
while `LEVEL.RAW[0xa81ac]` is the **compressed byte that loads at that address** (`0x70d4001a`) — decompression
overwrote it with the decoded payload. So `0xa81ac` is **not a coordinate and not editable**. This **corrects**
G22's "indexed-geometry stream at `0xa81ac`" reading and sharpens its "processed/generated" conclusion to
**decompression**. **No safe edit target** exists in compressed LEVEL.RAW; a floor edit would require
decompress→edit→recompress (decode the `fcn.8001a1dc` codec first) — not a single-byte file patch, and safer than
patching the runtime output `0x801bdc58`.

**Recommended next step (Option A — decode the source):** **EXEC `0x8001a1dc`** (decompressor entry, fires once at
LEVEL01 load) — read `a0` (compressed src = LEVEL.RAW), `a1` (decompressed dst = `[gp+0x588]`), and the output size
at return; confirm `[a1, a1+size)` contains the floor `0x801bdc58`. Static follow-on: decode the `fcn.8001a1dc` bit
grammar to decompress LEVEL.RAW offline. No patch/build. Collision/pathing UNKNOWN.

## 4.19. G24 — LEVEL.RAW decompressor `fcn.8001a1dc` grammar (partial) + ground-truth runbook

**Status:** READ-ONLY static decode 2026-06-15. No patch, no build, **no decoder tool** (grammar partial). Full
detail in [`src_re_geometry/geometry_g24_level_raw_decompressor.md`](../src_re_geometry/geometry_g24_level_raw_decompressor.md).

`fcn.8001a1dc` (`0x8001a1dc..0x8001a8f8`, ~456 instrs, single caller `0x8003a4e4`) decoded as a custom
**LZSS / LZ77 + variable-length-code** decompressor (CONFIRMED structure, exact codes PARTIAL):
- **Prologue/header:** saves all GPRs; reads two **big-endian** words `word0=BE32[src+0]`, `word1=BE32[src+4]`
  (→ `a2=dst+word0`, `a0=src+0xe+word1`, both **computed then never read** — §6 of the doc); `0xe`-byte header;
  `v1 = src + 0xe` = the bit/literal cursor; `dst` = output.
- **Bit reader:** MSB-first, one byte at a time from `v1`, guard-bit refill (~9 inlined reload sites).
- **Main loop `0x8001a658`:** LZSS flag bit — `0` = copy one inline literal byte from `v1`; `1` = back-ref match.
- **Match:** variable-length length code (escape at value `9` → long-literal `N×4` run `0x8001a3fc`; long byte
  `0x8001a708`, **byte `== 0` = stream terminator** `0x8001a804`); 16-bit distance (hi bits coded + byte-swap +
  **low byte inline** from `v1`); back-ref source `out − dist − 1`; copy with odd-byte + RLE-when-hi==0 paths.
- **Termination:** bit/terminator-driven (NOT `word0`); a final scratch-stack flush that is a **no-op** here.

**Output size is bit-driven**; `word0`/`word1`/`a0`/`a2` are computed-but-dead (UNKNOWN purpose — possibly a
two-stream/size-checked variant not taken). **Exact length/distance code tables are not byte-exact** → per the
task rule, **no offline decoder is invented**. **Recommended next step:** **EXEC `0x8001a1dc`** — record hit
count, `a0` (compressed src = LEVEL.RAW), `a1` (decompressed dst = `[gp+0x588]`); at the return dump a window of
the decompressed output (ground truth). The floor's **decompressed** offset = `0x801bdc58 − dst` (different from
the compressed `0xa81ac`); search the output for the floor `fcn.80010000` payload to pin it. That ground truth
validates any future `tools/decode_level_raw.py` byte-exactly. No patch/build. Collision/pathing UNKNOWN.

## 4.20. G25 — LEVEL.RAW post-decompression: per-chunk decompress LOOP + type-dispatch builder

**Status:** RUNTIME `EXEC 0x8001a1dc` (operator) + READ-ONLY static trace of `fcn.8003a318` 2026-06-15. No patch,
no build. Full detail in
[`src_re_geometry/geometry_g25_level_raw_post_decompress_trace.md`](../src_re_geometry/geometry_g25_level_raw_post_decompress_trace.md).

**Runtime trace (operator).** `EXEC 0x8001a1dc` produced **many** hits (every one `ra=0x8003a4ec`, `gp=0x80081d98`)
→ the decompressor runs in a **per-chunk loop** in `fcn.8003a318` (single static call site `0x8003a4e4`, looped).
`a0` walks the compressed LEVEL.RAW buffer `[0x80115aac,0x801cc690)`; `a1` (= `fp = [gp+0x588]`) walks the
decompressed output. The "odd final row" `a0=2,a1=0x1e2830,pc=0x8003f33c` is a **GPU/DMA spin-wait**
(`lw [0x80082250]; beq …,1,self`), not a chunk — correctly excluded.

**Loop (CONFIRMED disasm), span `0x8003a318..0x8003c384`:**
- entry `0x8003a4cc j 0x8003c2a4`; **head `0x8003c29c`** reads `s5[0..3]`; `ff ff ff ff` (= `word0` sentinel) →
  **finalize `0x8003c2dc`**; else **body `0x8003a4d4`**.
- body: `jal 0x8001a1dc(a0=s5 compressed src, a1=fp dst)`; `s4 = fp[0]` = **chunk subtype**; big **type dispatch**
  `0x8003a4ec..0x8003c250` consumes the decompressed chunk (`s3=fp`) and builds a runtime resource; each case does
  `fp += align4(word0)`.
- tail `0x8003c250`: `v1 = BE32(s5[4..7]) + 0xe = word1 + 0xe`; `s5 += v1` (next compressed chunk); loop back.
- finalize `0x8003c2dc`: `[gp+0x4a0]=0x801cc390` (high-heap top), `[gp+0x588]=final fp`, `jal 0x80063508 ×2`, return.

**Resolves the two G24 open items.** Once-vs-per-block → **per-block**. The "computed-then-dead" header words are
**dead inside the codec but live in the caller**: `word0` = per-chunk **decompressed** byte count (advances `fp`),
`word1` = per-chunk **compressed** byte count (advances `s5`), `0xe` = chunk header length, `word0==0xffffffff` =
stream terminator. Matches the operator's per-chunk deltas (`a0 += word1+0xe`, `a1 += word0`).

**Source-side compressed-chunk bracket for `0xa81ac`** (= `0x801bdc58 − 0x80115aac`): the chunk with
`a0=0x801bd58f` (next `a0=0x801bf662`) contains the floor address at `+0x6c9`; that chunk's decompressed output
`a1=0x80143438`→`0x80147500` (span `0x40c8`).

**Decisive negative + corrected model.** The decompressor output cursor `a1`/`fp` tops at **`0x8015fcbc`**; the
floor `0x801bdc58` is **`+0x5df9c` above** → the floor is **NOT direct decompressor output**. It sits in
`[final-fp 0x8015fcbc, high-top 0x801cc390)` (the upper high-heap buffer / consumed-compressed tail), **`0xe738`
below the high top**. So the walkable-floor `fcn.80010000` payload is **built by a post-decompression stage** — a
geometry-family chunk-subtype case in `fcn.8003a318` writing into the high region, and/or a later converter reading
the decompressed output — **not** by the raw decompressor. Candidate builders: `fcn.8003cc58` (×5, consumes
`s3+0xc`), hot helpers `0x800628c0`/`0x800625fc` (×10) / `0x80061a48` (×9), `0x80055db0`, finalize `0x80063508`
(×2). Exact floor-writer PC/cursor = **UNKNOWN**.

**Next runbook (≤3 BPs; no decompressor re-trace, no RAM dump, no patch).** (1) PRIMARY **WRITE watch
`0x801bdc58`** → record writer `pc`/`ra` + the copied source (decompressed `[..,0x8015fcbc)` vs leftover compressed
vs computed in-register; is the PC inside `fcn.8003a318` or a later stage?). (2) SECONDARY **EXEC `0x8003a4ec`** →
log per chunk `s4`(subtype)/`fp`/`s5`/`[sp+0x48]`, enumerating subtypes and tying compressed offset `0xa81ac` to a
subtype. (3) TERTIARY (only if the write watch doesn't fire in the loop) EXEC `0x8003c2dc`/`0x80063508` then keep
the watch armed through later load. Collision/pathing UNKNOWN — visual ≠ collision.

**⚠ G26 outcome (2026-06-15):** the G25 WRITE watch `0x801bdc58` returned **0 hits**, and at `Press X to Continue`
`[0x801bdc58]=0x70d4001a` = `LEVEL.RAW[0xa81ac]` → `0x801bdc58` is **compressed source, never written**, so the
"floor built post-decompression near `0x801bdc58`" hypothesis is **dropped** (see §4.21). The per-chunk-loop /
`word0`/`word1` LEVEL.RAW findings above stand.

## 4.21. G26 — `0x801bdc58` is compressed LEVEL.RAW source, NOT a floor render payload (correction + pivot)

**Status:** CORRECTION + PIVOT 2026-06-15 (operator ground truth + read-only `SCUS_942.88` re-audit). No patch, no
build. Full detail in
[`src_re_geometry/geometry_g26_floor_payload_reaudit.md`](../src_re_geometry/geometry_g26_floor_payload_reaudit.md).

**Ground truth (operator).** (1) At `Press X to Continue`, `[0x801bdc58] = 70 D4 00 1A = 0x70d4001a` — exactly
`LEVEL.RAW[0xa81ac]` (the compressed-source word). (2) **WRITE watch `0x801bdc58` during LEVEL01 load = 0 hits.** So
`0x801bdc58` holds **compressed LEVEL.RAW source bytes, unchanged across the whole load** — it is **not** a generated
`fcn.80010000` render payload, and never was.

**Acceptance test it fails.** A real payload base `P` needs `[P]` = a plausible small vertex count (LEVEL01: 25…230)
and s16-coord vertices at `P+4`. `[0x801bdc58]=0x70d4001a` = 1.9 billion (impossible — LEVEL.RAW is `0xb68e4` total)
and the `0xa81ac` window is compressed (213 distinct/1024, G23). Not a payload.

**Re-audit — the `a0−4` formula is CORRECT, not the bug (disasm).** In `fcn.80010000`: entry `t7=[a0]`=count;
`bgtz → 0x8001024c` (count>0), delay `a0+=4`, `s5=a0`=vertex base. The count>0 main path **never rewrites `a0`**
(only the entry `a0+=4` and the count≤0 sub-path `< 0x8001024c` do); `a0` is read as the vertex base for vertex
address math; `s5` is **reused** (`lui s5,0x8008` @`0x80010298`). At gate `0x800108b4` (`addi s3,s3,0x34`; `s3`=GPU
packet cursor from `[0x800823f4]`, `s0`=vertex cursor), `a0` = payload+4, so `payload = a0−4` is right **for a
genuine call**. The G17 Candidate B hits recorded `a0−4 = 0x801bdc58` but **never count-validated it**; a real call
with count `0x70d4001a` would walk a command stream wildly out of bounds and cannot "emit 17 clean primitives." So
those hits did not map to a valid floor payload (wrong context/timing/stale `a0`). **Fix: validate `[P]` at capture
time** (prefer the `0x80010000` entry where `a0` = raw payload base and `[a0]` = count).

**Corrects / preserves.** RETRACTS: G17 Candidate B ("emitted floor at `0x801bdc58`"); the "floor payload at
`0x801bdc58`" framing of G18/G19; G25's "floor built post-decompression near `0x801bdc58`." PRESERVES (LEVEL.RAW
pipeline RE, independent of the floor): LEVEL.RAW loads compressed to `0x80115aac` (G22); `0x801bdc58 =
LEVEL.RAW+0xa81ac` (now *proven* by the Press-X byte); LEVEL.RAW is compressed (G23); `fcn.8001a1dc` per-chunk
decompress loop + `word0`/`word1` sizes (G24/G25). G16's `0x356bc` remains a real DAT-backed payload (a **wall**).

**Real floor render payload pointer = UNKNOWN.** New runbook (count-validated, consumer side) at a confirmed floor
view: PRIMARY **EXEC `0x80010000`** (record PC, `a0`=payload base, `[a0]`=count → **validate**, first `0x40` bytes,
`a1/a2/a3`, `ra`); SECONDARY **EXEC `0x800108b4`** (`payload=a0−4`, cross-check count, read `s3` packet screen-XY or
BP `0x80010718` SXY → floor projects to lower-center). Classify `P`: DAT-backed (`P−0x801607f8 ∈ [0,0x51418)`;
re-test the static floor shortlist e135 `0x1f148`/e254 `0x08f4c`/e52 `0x17d94`) / LEVEL.RAW-decompressed
(`P < 0x8015fcbc`) / generated. **Minimum evidence before any edit:** validated pointer `P`; source class; payload
sanity (`[P]` count + s16 vertices + command-stream terminator); visible floor association. No patch/build.
Collision/pathing UNKNOWN — visual floor ≠ collision floor.

## 4.22. G27 — count-validated `fcn.80010000` floor candidates (consumer-side decode)

**Status:** STATIC DECODE + CLASSIFICATION 2026-06-15 (operator-captured `EXEC 0x80010000` payloads + read-only
`DAT/LEVEL01_LEVEL.DAT` decode via `tools/analyze_g27_floor_candidates.py`). No patch, no build. Full detail in
[`src_re_geometry/geometry_g27_count_validated_floor_candidates.md`](../src_re_geometry/geometry_g27_count_validated_floor_candidates.md).

The operator ran the G26 §4 runbook (PRIMARY `EXEC 0x80010000`, validate `[a0]`=count) at the Candidate-B floor view
and captured five payloads. **All five pass the G26 §2 acceptance test** — `[a0]` = the claimed count exactly
(83/48/58/36/25), `pad==0` in 100% of vertices, each command stream ends in a clean `ffff ffff` terminator, all N
verts cited — and **all are DAT-backed** (`P−DATbase ∈ [0,0x51418)`). These are genuine payloads, unlike the
retracted `0x801bdc58` (`0x70d4001a`). The decoder is validated by **Candidate E reproducing the committed G18b
`0x2d460` decode** byte-for-byte (25v, 202×107×194, flat 0.53, **93** source-record references).

| cand | DAT off | cnt | flat | Y-band (IQR) | footprint | coord space | refs | classification |
|------|--------:|----:|-----:|-------------:|-----------|-------------|-----:|----------------|
| **A** | `0x188cc` | 83 | **0.154** | **316** | 4502×4502 | WORLD (Y≈4400–5060) | 1 | **floor/top-surface — STRONGEST** |
| **B** | `0x38870` | 48 | 0.260 | 234 | 1757×1680 | WORLD (same Y stratum) | 1 | floor/top-surface (smaller adjacent tile) |
| **C** | `0x38cb0` | 58 | 0.365 | 277 | 1706×2222 | WORLD (adj. in Z) | 1 | floor/top-surface (edge relief / ramp) |
| **D** | `0x38548` | 36 | 0.568 | 422 | 1935×1874 | MODEL (±950, −Y) | 1 | **NOT floor** — wall/structural-or-prop (role UNKNOWN) |
| **E** | `0x2d460` | 25 | 0.530 | 67 | 202×194 | MODEL (±100) | **93** | decor (CONFIRMED; = G18b, instanced ×93) |

**Discriminators (structure, not screen-visibility):** (1) **coordinate space** — A/B/C carry large positive
world-space coords → baked terrain chunks; D/E are centered on the local model origin → placed model objects
(prop/decor). (2) **Shared Y stratum** — A/B/C all sit in Y≈4400–5200 (co-planar tiled ground); D at ≈−5500, E at
≈−100. (3) **Flatness + tight IQR** — A/B clear the floor filter (<0.35, <900) decisively; C is borderline-flat with
a tight core; D/E fail. (4) **Instancing** — E ×93 = decor; A/B/C/D unique (drawn once). (5) all verts referenced →
connected meshes.

**Candidate A is the strongest floor/top-surface candidate** — flattest (0.154, beating the whole prior static
shortlist; G17 best e135 = 0.19), tightest Y core (316), widest footprint (4502×4502), world-space, unique, count 83
— and **DAT-backed (off `0x188cc`) → directly editable**, the property the retracted heap floor `0x801bdc58` lacked.

**This downgrades the G17/G18 "the walkable floor is NOT a LEVEL.DAT payload" inference** (it rested entirely on the
retracted `0x801bdc58`): the count-validated floor-view emit *does* surface DAT-backed, flat, world-space
floor-shaped payloads (A/B/C). **UNKNOWN** (not claimed): whether A is the *walkable* surface vs a co-planar
visual-only chunk, and whether a LEVEL.RAW-decompressed/generated payload also feeds the view (A–E is the captured
set, not proven exhaustive).

**NEXT (ONE read-only BP, no patch/build):** EXEC `0x800108b4` (packet-store survivor gate), log all hits and keep
`a0 == 0x801790c8` (= Candidate A vertex base, payload `0x801790c4 + 4`); read the GPU packet at `s3` (or `EXEC
0x80010718` for SXY0/1/2) and confirm A's survivors project into the **lower-center walkable band** (Flik standing on
it) before any edit — the G16 lesson that emit-in-frame ≠ floor. A contingent same-size edit spec is ready
(A v16 `y` @`DAT 0x18992` `89 13`→`89 17`, +1024, single byte; revert `89 13`) but **NOT built** — gated on that
confirmation. Collision/pathing UNKNOWN — visual ≠ tangible.

## 4.23. G28 — Candidate A runtime READ + projection-path confirmation; same-size edit prepared

**Status:** RUNTIME READ + PROJECTION-PATH CONFIRMATION 2026-06-15 (operator read watch + execute BPs in the
Candidate-B floor/top-surface view); the guarded same-size diagnostic image was **BUILT + embedded-verified and
then OPERATOR-TESTED → VISIBLE TERRAIN DEFORMATION** (build record §5.2 in the linked file; visual result below +
linked-file §5.3; artifacts gitignored/not committed). **Candidate A is now a CONFIRMED DAT-backed visual
terrain/floor render payload; collision/pathing did NOT align with the deform (separate or sourced elsewhere).**
Full detail in
[`src_re_geometry/geometry_g28_candidate_a_runtime_confirmation.md`](../src_re_geometry/geometry_g28_candidate_a_runtime_confirmation.md).

G28 closes the G27 §5 gate from the consumer side: **Candidate A reaches the render/projection path.**

**Evidence (operator):**
- **READ watch `0x801790c8`** (Candidate A vertex base) **hit repeatedly** in the active render path:
  `a0 = 0x801790c8`, `ra = 0x800206a0`, payload base `a0 − 4 = 0x801790c4`, count at payload base = **83** (matches G27).
- **EXEC `0x80010718`** (per-primitive site, immediately after `mfc2 SXY0/1/2`) hit while Candidate A was active:

  | # | pc | a0 | ra | SXY0 | SXY1 | SXY2 |
  |---|----|----|----|------|------|------|
  | 1 | `0x80010718` | `0x801790c8` | `0x800206a0` | `0x007A0164` | `0x00730182` | `0x007B0180` |
  | 2 | `0x80010718` | `0x801790c8` | `0x800206a0` | `0x007F01A8` | `0x007701CF` | `0x008501F1` |

  Unpacking each packed `SXYn` as `(Y<<16)|X` (signed 16-bit halves, the CONFIRMED G16 convention): **Y clusters
  tightly in ≈115–133** (the **central / lower-central** vertical band of a ~240-line field) → consistent with the
  operator's "plausible lower/central screen-space" read and a floor/top-surface (the G16 wall projected upper/side).
  X values (≈356–497) are recorded raw; exact horizontal placement needs the GPU draw-offset/viewport mapping, which
  is **not byte-exact yet (TODO, G16)**, so horizontal position is **not** used for any decisive claim.

**Classification:**
```
VALID DAT-BACKED PAYLOAD /
RUNTIME READ CONFIRMED /
PROJECTION PATH CONFIRMED /
LIKELY VISUAL FLOOR/TOP-SURFACE /
TANGIBILITY UNKNOWN
```

**Candidate A (`0x801790c4`) vs the retracted compressed source (`0x801bdc58`):** kept strictly separate. `0x801790c4`
= Candidate A, DAT `0x188cc`, count 83, runtime-read + projection-confirmed (this section). `0x801bdc58` =
`LEVEL.RAW + 0xa81ac`, **compressed source** (first word `0x70d4001a`, WRITE-watch 0 hits) — **RETRACTED as a payload
in G26** and not resurrected here. They differ by one hex digit but are entirely different objects. (`0x8018dc58` =
Candidate E = a valid DAT decor payload; also do not conflate.)

**Same-size diagnostic edit — PREPARED, NOT BUILT/RUN:** `tools/patch_g28_candidate_a_floor_y_test.py`.

| field | value |
|-------|-------|
| target file | `LEVEL01/LEVEL.DAT` (pristine `DAT/LEVEL01_LEVEL.DAT`, sha1 `b376cb50…`, `0x51418`) |
| payload / vertex / field | Candidate A (DAT `0x188cc`, runtime `0x801790c4`, count 83) · vertex 16 · `y` (s16) |
| field DAT offset | `0x18992` (= `0x188cc + 4 + 16*0xc + 2`; runtime base `0x80179188`, y at `0x8017918a`) |
| original / new bytes | `89 13` (`0x1389`/5001) → `89 17` (`0x1789`/6025) |
| delta / revert | `+0x0400` / +1024 (single byte `0x18993` `13→17`) · revert `89 13` |
| discipline | same-size `0x51418` only; never in place; verify exact original bytes; touches **no** collision/pathing files |

Build (only when explicitly instructed) uses the **existing shared wrapper** `tools/rebuild_with_patched_dat.py`
(same flow as the G6 build; **no new wrapper added**, consistent with G12–G16) → future image
**`ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue`**:

```bash
python3 tools/patch_g28_candidate_a_floor_y_test.py \
    DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST.DAT
python3 tools/rebuild_with_patched_dat.py \
    --patched-dat DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST.DAT \
    --target files/LEVEL01/LEVEL.DAT \
    --out-bin ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.bin \
    --out-cue ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue \
    --write --report DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST_REBUILD.md
```

**Visual test result (operator, 2026-06-15) — `ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue`:**

| check | result |
|-------|--------|
| boots / LEVEL01 loads | **YES / YES** |
| visible deformation | **YES** — tested floor/terrain **caves inward / deforms** in Candidate A's projected (lower/central) area |
| angle dependence | deformation **shifts slightly with viewing angle** |
| other objects | Flik and other scene objects **still render** |
| collision / pathing | **does NOT align with the visual deformation** |

```
CONFIRMED: Candidate A is a DAT-backed VISUAL terrain/floor payload; the edit at DAT+0x18992 affects VISIBLE
           terrain geometry; A is NOT just decor/grass/prop; A is part of the visible floor/top-surface render
           mesh in the tested area; visual render geometry and collision/pathing are SEPARATE for this edit.
LIKELY:    A belongs to the visible terrain/floor/top-surface mesh family used in the Candidate-B view.
UNKNOWN:   the actual collision/pathing source for this floor surface; whether A has collision/tangibility data
           elsewhere.
```

Explicit: **visual terrain payload ≠ collision/pathing source** — the tested visual deformation did not alter or
align with collision, so collision/pathing remains separate or sourced elsewhere (no claim that collision moved;
no tangibility claim). The pre-test Y-sign→screen mapping was UNCONFIRMED; the observed inward cave (vs the
tentatively-worded spike) still confirms a clear out-of-plane deformation of visible terrain (byte-exact viewport
mapping remains TODO, G16).

**Operator runbook (G28 visual test — RAN 2026-06-15; result above / linked-file §5.3):**
```
1. Build the G28 Candidate A image from pristine disc + patched LEVEL.DAT.
2. Boot LEVEL01.
3. Use the same Candidate B floor/top-surface view.
4. Compare visible floor/top-surface near the lower/central screen band.
5. Expected visual effect:
   Candidate A vertex16 Y is raised by +1024, so if Candidate A is visible floor/top-surface,
   a local visual deformation should appear.
6. If no visible change:
   Candidate A may be off-screen in that view, occluded, not the specific floor patch area,
   or the chosen vertex may be visually subtle.
7. Collision/pathing remains UNKNOWN unless separately tested.
```

This documentation pass executed no patch/build/edit; the G28 image was built (linked §5.2) and operator-tested
(result above / linked §5.3) in prior steps. Candidate A = **CONFIRMED visual terrain/floor render payload**;
collision/pathing **UNKNOWN** — the deform did not align with collision; **visual terrain payload ≠
collision/pathing source**; do not infer tangibility. **Next: G29 — collision/pathing source discovery for the
confirmed visual floor terrain** (do not assume it is in Candidate A / LEVEL.DAT / LEVEL.RAW without new evidence;
use runtime collision / movement-height probes, not the visual render path alone).

## 5. Required evidence standards

- Use the confidence vocabulary everywhere: **`CONFIRMED` / `LIKELY` / `UNKNOWN` / `TODO`.**
  - `CONFIRMED` = disassembly **and** (where applicable) a runtime test / byte-exact tool.
  - `LIKELY` = strong static evidence, not runtime-verified; flagged.
  - `UNKNOWN` = not determined; never guess a name/value.
  - `TODO` = explicit work item.
- **Never label a structure mesh / collision / pathing / render unless code or a test supports it.**
  Until then it is a "geometry record (role UNKNOWN)".
- **Keep render and collision hypotheses in separate files** (`geometry_render_consumers.c` vs
  `geometry_collision_consumers.c`). Do not let a single function "explain both" without evidence.
- **Preserve old offsets and new shifted offsets** whenever relocation/shift is relevant (e.g. a
  pre-append value `0x4680` and its post-append `0x4690`).
- **Prefer small tables of offsets/ranges over prose speculation.** One row per record/field/site.
- Never overwrite an `UNKNOWN`/`unkNN` with a guess; downgrade a label if evidence weakens.
- `re_types.h` is updated **only** when a decompiled body evidences a field; promote `unkNN` →
  named with a confidence marker, and note it here.
- Don't infer LEVEL01 conclusions for other levels; LEVEL01 first, others later with their own
  evidence.
- Cross-check all relocation claims against `tools/dat_reloc.py` (expect 1248 LEVEL01 sites).

---

## 6. File scaffold

```
docs/GEOMETRY_RE_PLAN.md                      (this file — index + phase plan)
src_re_geometry/
  geometry_notes.md                           hub: pipeline sketch, glossary, open questions
  level01_dat_geometry_inventory.md           G1: record table + relocation-target map
  dat_geometry_records.c                      G2: parser geometry-output model (annotates fcn.8001cdc0)
  geometry_runtime_buffers.c                  G3: runtime buffers + candidate struct layouts
  geometry_render_consumers.c                 G4: render consumer search + findings
  geometry_collision_consumers.c              G5: collision/pathing consumer search + findings
```

The `.c` files are **hand-decompilation notes / structured pseudocode**; they need not compile.
Each begins with the standard header (below) and keeps confidence labels inline. They share
`../src_re/re_types.h`; geometry structs are added there only when evidenced.

Standard header (every `src_re_geometry/*.c`, mirrors `docs/DECOMPILATION_PLAN.md` §6):
- ORIGINAL ADDRESS(ES) (+ size if known)
- CONFIDENCE (overall; "C body = TODO" until written)
- SOURCE NOTES consulted
- KNOWN CALLERS / KNOWN CALLEES
- KNOWN GLOBALS (use `re_types.h` names)
- UNRESOLVED QUESTIONS
- optional `CONFIRMED MODEL (spec, not yet code)` then a `TODO` stub.

---

## 7. Review checklist (per geometry phase)

- [ ] Standard header complete (addr, confidence, sources, callers, callees, globals, unresolved).
- [ ] Every claim carries a confidence label; `UNKNOWN`/`unkNN` left intact (no guesses).
- [ ] No structure called mesh/collision/pathing/render without a cited consumer or test.
- [ ] Render hypotheses and collision hypotheses are in separate files.
- [ ] Relocation claims cross-checked against `tools/dat_reloc.py` (1248 sites); offsets quoted.
- [ ] Old vs new shifted offsets preserved where a shift is discussed.
- [ ] Signed/unsigned loads, shifts/masks, halfword/byte widths preserved in any pseudocode.
- [ ] GP-relative globals resolved against `gp=0x80081d98` and named via `re_types.h`.
- [ ] Tables preferred over prose; one row per record/field/site.
- [ ] `re_types.h` updated ONLY for fields a body actually evidences; this plan's §4 status updated.
- [ ] No DAT/BIN/CUE mutation; no ISO build; no edits to `src_re/` pickup files.
- [ ] If a finding contradicts a `docs/*.md`, STOP and reconcile; mark superseded in `EXPERIMENT_LOG.md`.

---

## 8. Recommended first execution prompt (G1)

> "Execute Geometry Phase G1 only (DAT geometry inventory). Read `docs/GEOMETRY_RE_PLAN.md`,
> `src_re_geometry/level01_dat_geometry_inventory.md`, `src_re/dat_parser_8001cdc0.c`, and
> `docs/DAT_FORMAT_AND_RELOCATION.md` first. Do not mutate DAT/BIN/CUE, do not build an ISO, do
> not modify `src_re/`, and do not decompile new functions.
>
> Using only non-mutating reads of `DAT/LEVEL01_LEVEL.DAT` and `tools/dat_reloc.py --scan`:
> (1) For each top-level record (`0x01`, `0x0b`, `0x0c`, `0x0d`, `-2..-7`), dump the first few
> entries/words and describe the byte pattern (stride, field widths, value ranges) **without
> guessing** a role; label each role UNKNOWN/LIKELY with the evidence. (2) Confirm the rec10-vs-EOF
> discrepancy and document the true geometry-data region `[~0x45f0, 0x51418)` that the relocation
> pointers target. (3) Map relocation sites to record/blob ranges: which `[s3+2]` source records sit
> where, which `[s0+0x14]`/`[s0+0x1c]` targets cluster where, and the densest target regions.
> (4) Fill the tables in `level01_dat_geometry_inventory.md`, keeping CONFIRMED/LIKELY/UNKNOWN/TODO
> discipline and preferring tables over prose. Then update §4 status (G1 → analyzed) and note any
> doc reconciliation in `EXPERIMENT_LOG.md`. Do not start G2."

---

**Related docs:** [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md) ·
[DECOMPILATION_PLAN.md](DECOMPILATION_PLAN.md) ·
[EXECUTABLE_AND_OVERLAYS.md](EXECUTABLE_AND_OVERLAYS.md) ·
[LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)
