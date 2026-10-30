# Geometry RE Notes (hub) — LEVEL01 first

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [← ABL_RE_NOTES.md](../ABL_RE_NOTES.md)

Working hub for the geometry-creation research track. This is the place to jot cross-file
findings, the current pipeline sketch, the address glossary, and open questions. Phase-specific
detail lives in the sibling files. **No mesh/collision label without evidence; render and
collision stay separate; CONFIRMED/LIKELY/UNKNOWN/TODO on every claim.**

## Scope
- Target: how `LEVEL01/LEVEL.DAT` records **after** the type-`0x3f` pickup record become runtime
  render geometry and collision/pathing geometry.
- Out of scope (context only): the type-`0x3f` pickup pipeline, the `0x800b0d18` contact array,
  the `0x8009c870` sprite-object pool, the `0x80096b98` 128-entity list.

## Pipeline sketch (current best understanding)

```
LEVEL01/LEVEL.DAT
  rec0  type 0x3f  @0x004   -> pickups (SOLVED; not the target)
  rec1  type 0x01  @0x468   -\
  rec2  type 0x0b  @0x94c    |
  rec3  type 0x0c  @0xa10    |  non-0x3f records — roles UNKNOWN (G1)
  rec4  type 0x0d  @0xad4    |
  rec5..rec10 (-2..-7)       -/  negative/packed records — roles UNKNOWN (G1)
  post-record word @0x1500 = 0
  trailing block @0x1504:
    PASS 1 table  @0x1512  (stride 0x14, 484 entries)  --\
    PASS 2 base   @0x3ae8  ([p2]=-1 -> EMPTY)             |  fcn.8001cdc0 relocation passes
    PASS 3 table  @0x3afa  (stride 0x14, 140 entries)   --/
  geometry DATA region [0x45f0, 0x51418=EOF): targets of ALL 1248 relocated pointers (G1 CONFIRMED)
    source-record band  [0x45f0, 0x8bd8)  : 624 [s3+2] targets (pass1 0x45f0..0x7ce0; pass3 0x7d00..0x8bc0)
    payload band        [0x8bd8, 0x4f32c] : 624 [s0+0x14]/[s0+0x1c] sub-pointer targets
        |
        v  fcn.8001cdc0 PASS 1  (CONFIRMED in src_re/dat_parser_8001cdc0.c)
  DATbase + arg2 : array of 0x20-byte OUTPUT RECORDS  (G3: arg2 = DAT filesize; base = end of DAT)
    out+0x00..0x10 = 3x3 GTE rotation matrix (9 int16), bit3-path scaled by [s0+0x12/14/16]
    out+0x18       = pointer to source record s0 (in geometry region)
    (pass1 writes 484 records; count -> G_DAT_ENTRY_COUNTER ; return = (pass1+pass3)<<5 bytes)
        |
        v  RENDER CONSUMER (G4/G10): driver fcn.800224ec
  fcn.800140a0 culls pass-1 trail rows -> survivor row pointers into LIST_A(0x80096ea8)/LIST_B(0x8009e338)
        |
        v  G10 per-survivor builders fcn.8001ea6c / fcn.800206e8
  bridge: row+0x10 -> output record -> +0x18 -> source record -> +0x14/+0x1c -> PAYLOAD [0x8bd8,0x4f32c]
  read source vec[3] - camera, GTE transform, dispatch by row-kind, pack primitive into GPU/OT [0x8008240c]
        |
        v
  drawn geometry   (collision path still UNKNOWN — G5 negative)
```

Evidence that consumers exist and matter: the naive-append black screen was a **consumer of the
corrupted post-`0x3f` geometry** crashing after Press X, while the pickup pass (which reads the
correctly-rebuilt type table) survived (CONFIRMED, `docs/DAT_FORMAT_AND_RELOCATION.md`).

### G1 status (ANALYZED 2026-06-13)
- Top-level records end at **`0x1500`** (CONFIRMED). The old "record `-7` = bulk geometry blob to
  EOF" wording is **SUPERSEDED**: rec10 (`-7`) is a fixed `0x190`-byte packed record ending at
  `0x1500`; the geometry-heavy data is the post-trailing region `[0x45f0, EOF)`.
- **0 of 1248** relocation targets fall in the records or the trailing tables; **all 1248** point
  into `[0x45f0, 0x4f32c]`, split into a source-record band `[0x45f0, 0x8bd8)` and a payload band
  `[0x8bd8, 0x4f32c]`. Full tables in [level01_dat_geometry_inventory.md](level01_dat_geometry_inventory.md).
- Source-record pointers are spaced `0x18` early, but the parser reads `[s0+0x1c]` — **stride/size
  conflict OPEN for G2** (see open questions #8).

### G3 status (ANALYZED 2026-06-13)
- Caller `fcn.8003cf2c` @`0x8003d568`: **DATbase = `[sp+0x98]` heap cursor**; the DAT is read there;
  **arg2 = file-reader (`fcn.80046330`) return = DAT file size** (CONFIRMED by disasm). So the pass-1
  **output base = DATbase + filesize = end of the loaded DAT**.
- LEVEL01 (DATbase `0x801607f8` LIKELY): output base `0x801b1c10`; pass-1 array = 484×`0x20` (`0x3c80`)
  → ends `0x801b5890`. Parser **return = (484+140)<<5 = `0x4e00`** → caller reserves to `0x801b6a10`.
  **MISMATCH:** `0x1180` (= 140×`0x20`) is counted (pass-3 entries) but NOT written by pass-1 — a
  reserved/uninitialized gap (role UNKNOWN).
- Source records + payload band live **inside** the DAT image; the pass-1 matrix output array lives
  **after** it. Full map in [geometry_runtime_buffers.c](geometry_runtime_buffers.c).

### G4 status (ANALYZED 2026-06-13; G6 render effect CONFIRMED 2026-06-14)
- Consumer search = gp-relative ref scan of the 5 parser globals. Only **6 external refs**: `fcn.800224ec`
  reads `G_TRAIL_BLOCK_PTR` (@`0x800225f4`) and `G_PASS3_BASE_PTR` (@`0x80022858`); `fcn.80029030`/
  `fcn.800292dc` read `G_PASS2_BASE_PTR` (pass-2 EMPTY in LEVEL01 → not active).
- **`fcn.800224ec` = CONFIRMED scene/render driver** reading the parser geometry: calls confirmed render
  loop `fcn.8003f938`, GTE matrix setup `fcn.80017b98` ×2, stages a view matrix/vector in scratchpad
  `0x1f8003b4`/`0x1f800384` (camera `0x1f800374`), called per-scene from `0x8004f4xx`.
- It dispatches the trail/pass3 pointers to **GTE transform helpers** `fcn.800140a0`/`80014360`/`800146e0`
  (32–39 cop2 ops; MVMVA matrix×vector + SQR distance). G5.5/G6 now CONFIRM the `fcn.800140a0`
  trail flag path has render-stage visual impact: patching `DAT+0x1526` (`41 00` -> `ff ff`) caused
  major terrain/ground render disappearance/cutoff. No RTPS/RTPT/GPU-primitive seen yet, so the exact
  primitive emission site is UNKNOWN.
- Linkage: parser repoints trailing-table `[s3+2] = out`, so the `0x20` output matrices are reached via
  `G_TRAIL_BLOCK_PTR` → table → output record. `G_DAT_ENTRY_COUNTER`/`G_DAT_BASE_PTR` have no external
  geometry reader. Detail in [geometry_render_consumers.c](geometry_render_consumers.c).

### G5.5 status (PART C read hit RUN 2026-06-14) — render-stage field read CONFIRMED
- Read watches on the chosen pass-1 bit3 source/output record had **no hits**:
  `0x801b3cb0` (output rec 261 matrix[0]), `0x801b3cc8` (output rec 261 source pointer), and
  `0x8016560a` (source `s0+0x12` scale0). Therefore that specific output/source record reader
  remains **UNKNOWN**.
- Execute fallback hit only the expected G4 render-stage helper PCs:
  `0x800140a0` with `a0=0x80161cfc` (`G_TRAIL_BLOCK_PTR`), `0x80014360` with `a0=0x801642e4`
  (`G_PASS3_BASE_PTR`), and `0x800146e0` with `s2=0x801642e4`. The later hits were captured after
  moving Flik and stopping, not necessarily during active movement/collision. This CONFIRMS runtime
  execution of the parser-geometry helper path.
- Part C read watches `0x80161d0a` and `0x80161d1e` hit in `fcn.800140a0` (DuckStation PC
  `0x80014174`, expected read site `0x80014170`). These map to LEVEL01 DAT file `0x1512` and
  `0x1526`, pass-1 trail entry0/entry1 flag/sentinel halfwords (`0x0041`). The entry1 hit repeated
  after resume/F5 at the same read site. This CONFIRMS concrete DAT-backed parser-geometry fields
  are read at runtime by the render-stage path.
- G6 is now ready **only as a render-stage diagnostic edit**. Collision impact remains **UNKNOWN**;
  no collision-aware diagnostic edit is supported. Tested body-field watches (`DAT+0x1510/0x1508/
  0x150c`) remained zero-hit, so the safest exact render-stage edit target still needs care. Full
  table in [geometry_g55_dynamic_watch.md](geometry_g55_dynamic_watch.md).

### G6 status (TESTED 2026-06-14) — render-stage diagnostic succeeded
- Patch: `LEVEL01/LEVEL.DAT+0x1526`, pass-1 trail entry1 flag/sentinel, `41 00` -> `ff ff`.
- Result in `ABL_G6_RENDER_SENTINEL_TEST.cue`: title/menu and LEVEL01 load; standing terrain/ground
  render is mostly empty/missing; sky and some horizon/grass/backdrop remain visible; Flik, objects,
  enemy/props load; no black screen and no crash.
- After movement, Flik can stand/move on the invisible/missing terrain in the tested area and objects
  still load.
- Conclusion: `DAT+0x1526` controls render-stage trail scanning/visibility. This supports
  render/collision separation for this field. Collision/pathing pipeline remains **UNKNOWN**.

### G7 status (BODY READ CONFIRMED 2026-06-14) — render-body field identification
- Reinspection of `fcn.800140a0` shows flag scanning and body processing are separate. The helper
  reads every nonnegative `entry+0x0e` flag/sentinel, but body fields are read only when the runtime
  bitmask table at `0x800901c8 + (entry>>3)` has bit `0x80 >> (entry&7)` set.
- Body read sites:
  `0x8001419c` = `entry+0x00` word;
  `0x800141a0` = `entry+0x08` word;
  `0x800141a4` = `entry+0x0c` halfword;
  `0x800141b4` / `0x80014258` = `entry+0x04` word.
- This explains the earlier zero-hit body watches: entry0/entry1 flag reads hit because scanning is
  unconditional, while entry0 body reads likely skipped because the current row bit was clear.
- Runtime watch round on the pristine/working image:
  `0x80161e78` = `DAT+0x1680`, pass-1 trail entry19 `+0x00`, expected PC `0x8001419c`, no hit;
  `0x80161e84` = `DAT+0x168c`, pass-1 trail entry19 `+0x0c`, expected PC `0x800141a4`, no hit;
  `0x80161edc` = `DAT+0x16e4`, pass-1 trail entry24 `+0x00`, expected PC `0x8001419c`, no hit during
  general standing/walking/jumping/camera movement away from the area, then one hit when Flik/camera
  was near a specific edge-of-level area. Do not attribute the hit to F collection.
- Entry24 hit: DuckStation PC `0x800141a0`, actual read site `0x8001419c: lw s3,-0x14(a0)`,
  `a0=0x80161ef0`, read address `a0-0x14=0x80161edc`, reported `s3=0xfffd126d`.
- Interpretation: entry24 `+0x00` is a CONFIRMED DAT-backed render-body field read by
  `fcn.800140a0`. Entry24 appears view/location/edge-of-level gated. Entry19
  remains **ZERO-HIT / NOT ELIGIBLE YET**. It is **UNKNOWN** whether entry19 is never used,
  scene/camera gated, distance gated, or active only in a different route/state.

### G7 Path A status (COMPLETE 2026-06-14) — entry24 body row CONFIRMED
- In the same edge-of-level / view-location gated area (not F-collection), the `+0x00` control
  re-fired (hit count 2) and all three adjacent entry24 body fields hit at the predicted PCs with
  `a0=0x80161ef0`:
  `0x80161ee4` = `+0x08` (`DAT+0x16ec`), PC shown `0x800141a4`, read site `0x800141a0`;
  `0x80161ee8` = `+0x0c` (`DAT+0x16f0`), PC shown `0x800141a8`, read site `0x800141a4`;
  `0x80161ee0` = `+0x04` (`DAT+0x16e8`), PC shown `0x8001425c`, read site `0x80014258`.
- The `+0x04` hit at `0x80014258` confirms the non-negative-`+0x0c` branch (pristine `+0x0c=734>=0`).
- **CONFIRMED:** the full entry24 body row (`+0x00/+0x04/+0x08/+0x0c`) is a **non-sentinel
  DAT-backed render body row** read by `fcn.800140a0`. **LIKELY** location/view gated. Field
  semantics, downstream GPU stage, and visual effect remain **UNKNOWN**. Collision/pathing
  **UNKNOWN**.
- **Flagged:** at the `+0x00` hit DuckStation reported `s3=0xfffd126d` while the static DAT word is
  `0xffffd800` (`-10240`); **UNKNOWN** whether the row is runtime-rewritten. This gates any static
  edit.
- **G8 (COMPLETE for small same-sign perturbations, 2026-06-14):** Candidate A = entry24 `+0x08`
  (`DAT+0x16ec: 9f fa ff ff → 9f fb ff ff`, `+256`). The **blocking** live-value gate **PASSED**: in
  the edge-of-level entry24 state, `READ 0x80161ee4` broke at PC `0x800141a4` with the live word
  `0xfffffa9f` == static, so `+0x08` is static-DAT-backed at the read (the `+0x00` mismatch does not
  apply). Patched DAT `DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_TEST.DAT` (sha1 `67dbb832…`) and image
  `ABL_G8_ENTRY24_PLUS08_TEST.cue` built; embedded byte at `0x16ec` verified `9f fb ff ff` (LBA 2906);
  staged workspace restored to pristine. DAT/BIN/CUE artifacts gitignored/not committed.
  `+0x00` avoided as edit target; `+0x0c`/`+0x0e` excluded as control/sentinel.
  **Emulator result (2026-06-14): EXECUTED / VALID BUILD / NO OBVIOUS VISUAL CHANGE** (boots, LEVEL01
  loads, no crash/black screen; edge-of-level entry24 area looks effectively the same as pristine by
  eye). The `+256` nudge was likely too small, visually masked, or not directly positional; `+0x08`
  may still be render-body/range/vector data, semantics **UNKNOWN**. Optional CPU confirmation:
  **CONFIRMED data read in G8 image** (READ `0x80161ee4` fired at PC `0x800141a4`, read site
  `0x800141a0`, `a0=0x80161ef0`, hit count 1); raw `s5=0xfffffb9f` not separately captured, so
  patched-bytes proof is the embedded DAT verification (`0x16ec`=`9f fb ff ff`). **Candidate A2 BUILT
  2026-06-14** (larger same-field nudge `DAT+0x16ec: 9f fa ff ff → 9f fe ff ff`, `-353`, `+1024`;
  patched sha1 `8714b578…`; image `ABL_G8_ENTRY24_PLUS08_A2_TEST.cue`, embedded `0x16ec` verified
  `9f fe ff ff` at LBA 2906; workspace restored to pristine). **A2 result 2026-06-14: EXECUTED / VALID
  BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE** — boots, no crash; READ `0x80161ee4` hit
  (count 1, PC `0x800141a4`, `a0=0x80161ef0`); **memory view CONFIRMS live RAM `0x80161ee4=FFFFFE9F`**
  matching the A2 patch (cross-checked `+0x00=FFFFD800`, `+0x04=FFFFF5B3`); edge-of-level area
  unchanged by eye; save state captured (not committed). Candidate C `+0x04` (`DAT+0x16e8:
  b3 f5 ff ff → b3 f9 ff ff`, `-2637 → -1613`, `+1024`) also produced an EXECUTED / VALID BUILD /
  CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE result: READ `0x80161ee0` hit once, PC shown
  `0x8001425c`, actual read site `0x80014258`; the edge-of-level area remained effectively unchanged
  by eye vs pristine/A2. Small same-sign perturbations of entry24 body fields were valid and read but
  visually imperceptible (A `+256`, A2 `+1024`, C `+1024`). This does not disprove render-body
  relevance, but continued blind/small entry24 perturbation testing is low-yield. **Next: G9
  dataflow tracing after the reads**, not another small entry24 perturbation. Full detail in
  [geometry_g55_dynamic_watch.md](geometry_g55_dynamic_watch.md) §12-15. Collision/pathing impact
  remains **UNKNOWN**.
- **G9 (RUNTIME REJECT RESULT, 2026-06-14):** entry24 `+0x00/+0x04/+0x08` flow as a
  view-relative vector `(+0x00-t5, +0x04-t6, +0x08-t7)` after the read block, while `+0x0c` selects
  the non-negative path and acts as an extent/range term. The path feeds `SQR` at `0x8001425c`
  (opcode `0x4aa00428`) and `MVMVA` at `0x80014298` (opcode `0x4a49e012`), then runs reject branches
  before a possible accepted row-pointer write at `0x8001430c` (list A, base `0x80096ea8`) or
  `0x80014320` (list B, base `0x8009e338`). This makes entry24 **LIKELY** culling/bounds/range data
  rather than a direct mesh-position row. Runtime stepping from `READ 0x80161ee0` CONFIRMED entry24
  passes the first reject at `0x80014280` (`s3=0xffff262b`, `bgez` not taken), then rejects at
  `0x800142b0` (`t0=0x000010b1`, operator-observed `bgtz` branch back to `0x80014170` taken). Therefore entry24 participates
  in GTE/math reject testing but does not reach late list-write output in the tested edge-of-level
  state. This explains G8 A/A2/C no-obvious-visual-change results: the patched fields influence the
  reject calculation, but entry24 still was not inserted into the visible output/list path in this
  state. A noisy late-write observation with `t0=0x80161f40` was another row, not entry24; it maps to
  pass-1 entry29, DAT row `0x1748` (`+0x04=0x174c`, `+0x08=0x1750`, `+0x0c=0x1754`). RAM alone would
  not prove the branch result; manual stepping or CPU/GTE-aware tracing is required. Full detail in
  [geometry_g9_entry24_dataflow.md](geometry_g9_entry24_dataflow.md).

### G10 status (STATIC ISO ANALYSIS 2026-06-14) — survivor-list consumers + payload bridge
- **Consumers CONFIRMED:** the survivor lists `fcn.800140a0` builds (`LIST_A=0x80096ea8`,
  `LIST_B=0x8009e338`) are consumed by **`fcn.8001ea6c`** (`a2=[0x8008240c]`, gate `0x10`) and
  **`fcn.800206e8`** (`a2=[0x8008240c]+0x1c4`), both called by driver `fcn.800224ec`. Each is a
  per-survivor primitive builder: walk LIST_A, gate/clear-tag, dispatch on `row+0x0e & 0x9f6f` via a
  jump table, GTE-transform, pack ~29 stores into the GPU/OT buffer `[0x8008240c]` (`gp+0x674`).
- **Bridge CONFIRMED (row → drawn data):** trail row `+0x10` → output record → `+0x18` → source
  record (band `0x45f0..0x8bd8`) → `+0x14`(non-bit3)/`+0x1c`(bit3) → **payload band**
  `0x8bd8..0x4f32c`. `fcn.8001ea6c` reads source `vec[3]` (`[s2+0/4/8]`) minus camera `0x1f800374`
  as the object's render position. Payload = `u32` count + s16 vertex triples (LIKELY ~12B stride).
- **Corrections:** `fcn.800146e0` = libgte camera-matrix load leaf (NOT projection); `0x80060484/
  0x800605c4` = libgte matrix leaves (NOT libgpu); RTPT `@0x80014970` is `fcn.80014844`'s contact-array
  path, not the geometry list chain.
- **Editable visible-geometry targets (proposal only; object must survive culling — use G9 survivor
  entry29, DAT row `0x1748`):** source `vec[3]` `@0x7388` (CONFIRMED render position), source
  `scale[3]` `@0x739a` / `angle[3]` `@0x7394` (CONFIRMED feed the output matrix), payload vertex
  `@0x2f2f8`+ (reachable CONFIRMED, mesh LIKELY). Full detail in
  [geometry_g10_payload_render_chain.md](geometry_g10_payload_render_chain.md).
- **G10 runtime + case decode (2026-06-14):** operator watches CONFIRMED the survivor source side:
  READ `0x80167b80` (entry29 `vec[0]`) hit in `fcn.8001ea6c` builder code, and EXEC `0x8001eb34`
  dispatch selected case `0x8001ec44`. Static decode of case `0x8001ec44` (`0x8001ec44..0x8001effc`):
  reads source `vec[3]`−camera → GTE; stages `angle[3]`; picks a base matrix from LUT `0x80089528`
  via `[s2+0x19]&0x1f`; scales it by `scale[3]` (`[s2+0x12/14/16]`, `>>12`) into `0x1f8003b4`; loads
  `payload ptr = [s2+0x1c]`; tail-jumps to emitter `0x80020698` → `jal fcn.80010000` (payload =
  `{u32 count; vertex[]}`, projected/emitted). This UPGRADES scale/angle to CONFIRMED read by the
  runtime builder. ITERATION CAVEAT: READ snapshot `s2=0x80167b80` vs dispatch `s2=0x80168d80` are
  different iterations — no one-row claim. **Next (static):** decode `fcn.80010000`/`0x80060284` for
  primitive type + vertex stride + GPU/OT write. See `geometry_g10_payload_render_chain.md` §7.

### G11 status (STATIC ISO ANALYSIS 2026-06-14) — payload vertex format + primitive emission
- **`fcn.80010000` = per-object mesh draw routine (CONFIRMED).** `a0`=payload, `a1`=z/flag,
  `a2`=color<<3, `a3`=`0x1f800384`. Reads payload count, then interprets a primitive **command stream**:
  `lh ctrl=[s0]`; `type=ctrl&0x1f` → jump table `@0x8001036c`; `bltz` ends. Type-0 case `0x8001046c`
  is a **triangle**: 3 vertex byte-offsets `[s0+2/+4/+6]`+`a0`, `lwc2` coords → GTE, RTPS/RTPT project,
  NCLIP backface-cull, screen/Z clip, pack polygon to OT.
- **`0x80060284` = GTE per-point transform helper** (not libgpu): `0x80060284` 32-bit / `0x800602b0`
  16-bit, core `0x800602e0` = `mtc2 vec → GTE matrix op → mfc2 sum`.
- **Payload layout (CONFIRMED):** `{u32 vertexCount; Vertex verts[N] (stride 0xc: s16 x; s16 y; s16 z;
  s16 pad=0; u32 attr); primitive command stream}`. Coords are s16 x/y/z at vertex `+0/+2/+4`;
  `attr@+8` LIKELY UV/normal/color. Primitives reference vertices by **byte offset** (`0,0xc,0x18,…`).
- **LEVEL01 entry29** (`DAT 0x1748` → source `0x7388` → payload `0x2f2f8`): count 34,
  v0=(0,-744,-61); **entry0** (`0xb32c`): count 195, v0=(1835,2349,5451). CONFIRMED bytes.
- **Edit targets (survivor entry29):** #1 source `vec[3]` `@0x7388` (translate, recommended),
  #2 `scale[3]` `@0x739a` (resize), #3 payload vertex `@0x2f2fc` (true mesh deform). Detail in
  [geometry_g11_payload_format.md](geometry_g11_payload_format.md).

### G12 status (RESULT 2026-06-14) — source vec[0] read-confirmed, visually silent
- **Candidate VEC** = pass-1 entry29 source record `vec[0]` (object render origin), `DAT 0x7388`,
  `f0 d8 ff ff` (`-10000`) → `f0 dc ff ff` (`-8976`, `+1024`, single byte). Built via
  `tools/patch_g12_entry29_source_vec_test.py` → `ABL_G12_ENTRY29_VEC_TEST.cue` (patched DAT SHA256
  `f01c2a0a…`).
- **RESULT: VALID BUILD / PATCH LIVE / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE.** `READ
  0x80167b80` hit (PC `0x8001ec48`, read site `0x8001ec44`, `s2=0x80167b80`) in `fcn.8001ea6c` case
  `0x8001ec44`; live memory `0x80167b80`=`FFFFDCF0` (matches patch); but no obvious lateral shift /
  mesh movement / clipping vs pristine in the entry29 view.
- **Interpretation:** source vector is live and read, but a whole-object origin nudge is visually
  silent here (LIKELY masked by object size/distance/orientation, or the `count<=0` draw path / an
  unmodeled transform term). Does NOT disprove the G11 payload path. **Next: direct payload-vertex
  deformation (G13), not another source-vec delta.** Collision/pathing UNKNOWN.

### G13 status (RESULT 2026-06-14) — payload vertex 0 read-confirmed, visually silent
- **Candidate PV0** = entry29 payload **vertex 0, `y`** (`DAT 0x2f2fe`), `18 fd` (`-744`) → `18 ff`
  (`-232`, `+512`). Built → `ABL_G13_ENTRY29_PAYLOAD_V0_TEST.cue` (patched DAT SHA256 `a6acffc3…`).
- **RESULT: VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL CHANGE.**
- **WATCH-ADDRESS LESSON (CONFIRMED):** the watch on the inner s16 `0x8018faf6` did NOT hit — the
  vertex is loaded by a **32-bit `lwc2` at the vertex base**, not a halfword at the `y` offset.
  Re-watching the **aligned vertex base `0x8018faf4`** hit at PC `0x80010928` (`lwc2 …,0x4(t0)`,
  `t0=a0=0x8018faf4`) inside `fcn.80010000`. **Rule: watch the aligned `lwc2` load address
  (`payload+4 + idx*0xc`, and the `+4` z/pad word), not the inner s16 coordinate.**
- Vertex IS read by the emitter, but v0.y `+512` is visually silent (v0 mid-body, lightly referenced,
  small inward delta). Does NOT disprove the payload path. **Next: command-stream-selected vertex +
  larger delta (G14).** Collision/pathing UNKNOWN.

### G14 status (BUILT 2026-06-14; emulator test PENDING) — command-stream-selected near-apex vertex
- **Command-stream decode (CONFIRMED):** entry29 stream `DAT 0x2f494..0x2f59c` (`ffff ffff` terminator).
  First prims: `0x2f494` type-2 quad strip (verts 0–11), `0x2f4c8` type-3 textured tri strip
  (verts 12,13,14,17,…). Halfword scan: **all 34 verts referenced, 28 twice, 6 once** (v13,16,20,21,29,30).
- **Candidate PV14** = entry29 payload **vertex 14, `y`** (`DAT 0x2f3a6`, runtime `0x8018fb9e`; vertex
  base `0x8018fb9c`), `bf f9` (`-1601`) → `bf f5` (`-2625`, `-1024`, single byte `0x2f3a7`). Chosen by
  silhouette + multi-tri sharing: refs=2 (deforms 2 triangles) AND near-apex (tall mesh Y `0..-1769`,
  X `±60`). Avoids refs=1 apex tips v13/v16 (lone triangle could be culled = G13 silent risk). `-1024`
  = upward spike ~58% of object Y extent, larger than G13's `+512`.
- **Build:** `tools/patch_g14_entry29_payload_vertex_test.py` →
  `DAT/LEVEL01_LEVEL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.DAT` (SHA256 `0db535eb…`, sha1 `53608e21…`);
  rebuild → `ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.cue`/`.bin`; embedded verified at LBA 2906
  (`@0x2f3a6`=`bf f5`); staged restored to pristine. Artifacts gitignored/not committed. Detail:
  [geometry_g11_payload_format.md](geometry_g11_payload_format.md) §5.3.
- **RESULT 2026-06-14: VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / VISIBLE RENDER CHANGE /
  NON-TANGIBLE DECORATION.** First **confirmed visible** payload-vertex edit — proves the payload-edit
  method end-to-end (DAT byte → on-screen vertex via `fcn.80010000`). The deformed object is
  **grass / decorative foliage**, **not tangible** in gameplay. entry29 (`DAT 0x2f2f8`) = grass/decor
  (LIKELY); a poor target for terrain. **Pivot to a ground payload (G15).** UNKNOWN: tangible
  terrain/collision source. Do not infer collision/pathing.

### G15 status (STATIC CANDIDATES + RUNTIME PLAN 2026-06-14) — terrain/ground payload identification
- **Pivot:** G14 proved the method but entry29 is decor. G15 surveys all 482 pass-1 payloads
  (`tools/survey_level01_payloads.py`) using **flatness = Yspread / max(Xspread,Zspread)**: grass/decor
  tall+narrow (flat>2, small footprint, instanced); terrain/ground wide+flat (flat<0.5, big footprint).
- **Shortlist (CONFIRMED metrics; role LIKELY):** e213 (`0x0d934`, rt `0x8016e12c`, 182v, flat 0.48,
  biggest footprint), e128 (`0x356bc`, rt `0x80195eb4`, 230v), e280/e282/e264/e265 (very flat wide
  floors), e17 (huge but coarse → maybe background). Detail in
  [geometry_g15_terrain_payload_candidates.md](geometry_g15_terrain_payload_candidates.md).
- **RUNTIME RESULT (2026-06-14):** EXEC `0x80010000` `a0`-log while on ground. The static "primary"
  `0x8018c234` was **REJECTED** (flat 1.76, count 37, instanced ×6 → decor; high frequency = instanced
  decoration, NOT terrain). Picked **`0x80170978`** (DAT `0x10180`): wide (X 7937), flat (0.30), 63
  verts all referenced (connected surface), positive-Y ground stratum, drawn once → terrain/ground
  render (LIKELY). Static shortlist (e213/e128/e280) did NOT appear in the log (not in tested view) →
  runtime selection was necessary.
- **Candidate TERRAIN-PV RESULT (commit 9c2558e build): VALID BUILD / PATCH LIVE / VERTEX READ
  CONFIRMED / NO OBVIOUS VISUAL CHANGE.** payload `0x10180` vertex 46 `y` `DAT 0x103ae` `7302`→`6278`
  (`-1024`). CPU: READ `0x80170ba4` hit at PC `0x8001069c` (`lwc2`) in `fcn.80010000`; but no visible
  spike/displacement vs pristine. The watch fired at the vertex *load* (before reject tests) → proves
  read, not that the primitive was emitted. **Read-confirmation ≠ visible.** Detail in
  [geometry_g15_terrain_payload_candidates.md](geometry_g15_terrain_payload_candidates.md).

### G16 status (VISIBLE WALL RENDER CHANGE CONFIRMED 2026-06-14) — screen-space vertex selection
- **Why:** G12–G15 all read-confirmed but visually silent; the G15 watch hit at the `lwc2` load,
  before the reject tests, so vertex-read ≠ primitive-drawn. G16 needs screen-space evidence.
- **`fcn.80010000` decode (CONFIRMED):** RTPS (`0x4a180001`@`0x800106a8`) / RTPT
  (`0x4a280030`@`0x800106f8`) project; `mfc2 SXY0/1/2` (regs 12/13/14) → `t5/t6/t7` = packed screen XY
  (`(Y<<16)|X`, signed halves); NCLIP backface (`0x4b400006`) + screen-bound (`sltiu …,0x200`) + AVSZ4
  depth (`0x4b68002e`) rejects all jump to skip `0x800108b8`; survivors store screen-XY into the GPU
  packet at `s3` (`+0x00/08/0c/14/18/20`) then `addi s3,s3,0x34` (`0x800108b4`).
- **Screen-space capture (ISO-identified):** execute BP at **`0x800108b4`**, read `a0` (payload) +
  packet at `s3` (unpack X=low s16, Y=high s16); on-screen iff X/Y in ≈`0..320`×`0..240`. Static DAT
  cannot derive projected screen pos (camera-dependent).
- **RUNTIME RESULT (2026-06-14):** EXEC `0x800108b4` (packet-store gate) log while on ground → payload
  **`0x356bc`** (= static e128, rt `0x80195eb4`) emitted **≥5** primitives; **`0x1b9f0`** (rt
  `0x8017c1e8`) **≥2**. Emit-confirmed on-screen terrain candidates (stronger than G15's read-only).
  Corrections: at `0x800108b4` `a0` = vertex-table ptr ⇒ payload = `a0−4`; `t5/t6/t7` there are reused
  packet/OT words (NOT SXY — logged values unpack to impossible coords) → read packet at `s3` for
  screen XY, or BP `0x80010718`; pixel mapping = TODO.
- **Candidate EMITTED-PV BUILT + TESTED:** payload `0x356bc` (230v, X 5838, Y 5093–8332, Z 6700) vertex
  **v10** `y` (central in the observed-emitted first-command quads) `DAT 0x3573a` (rt `0x80195f32`, base
  `0x80195f30`), `b9 1a` (`6841`) → `b9 16` (`5817`, `-1024`, single byte `0x3573b`). Tool
  `tools/patch_g16_emitted_payload_vertex_test.py` → patched DAT SHA256 `96206e69…`; image
  `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue`; embedded verified LBA 2906 (`@0x3573a`=`b9 16`); staged
  restored to pristine. Artifacts gitignored/not committed.
- **RESULT (operator, 2026-06-14): VALID BUILD / PATCH LIVE / EMITTED PAYLOAD CONFIRMED / VISIBLE WALL
  RENDER CHANGE.** Image boots, LEVEL01 loads, no crash/black screen; a **visible deformation** appeared
  on a **vertical wall/cliff face — NOT the walkable floor/top surface**. CONFIRMED: payload-vertex edits
  visibly deform terrain-family render geometry; `0x356bc` is screen-space/emitted and editable. **`0x356bc`
  RECLASSIFIED wall/vertical terrain face** (not floor) — its flatness `0.48` and local Y band
  (q25–q75=`1354`) are the least-flat of the shortlist, consistent with a wall. Lesson: emit-in-the-ground-
  view is necessary but **not sufficient** for "floor" — a wall in frame also emits. UNKNOWN: walkable
  floor payload; collision/pathing impact. **This is NOT a floor collision edit; visual terrain ≠
  collision — do not infer.** **Next: G17 floor/top-surface target.** Detail in
  [geometry_g16_screen_space_vertex_selection.md](geometry_g16_screen_space_vertex_selection.md) §9.

### G17 status (RUNTIME RESULT 2026-06-14) — walkable floor / top-surface payload target
- **Goal:** find the **walkable floor/top surface** Flik stands on (a flat horizontal payload), using
  emitted-primitive evidence (EXEC `0x800108b4`), filtered for floor — not the G16 wall `0x356bc`, not
  grass/decor `0x2f2f8`.
- **Floor discriminator:** flatness `< 0.35` AND tight local Y band (q25–q75 `< 900`) AND wide footprint
  AND unique (drawn once). The G16 wall fails this (flat 0.48, Yband 1354).
- **Static floor shortlist (CONFIRMED metrics; role LIKELY; NO emitted evidence yet):** e135 `0x1f148`
  (flat **0.19**, Yband 409, 110v), e254 `0x08f4c` (0.22, 53v), e52 `0x17d94` (0.23, 122v), e264 `0x0945c`
  (0.28), e280 `0x0eb14` (0.29), e265 `0x09dbc` (0.30).
- **Lead candidate (partial emit evidence):** `0x1b9f0` (e160, rt `0x8017c1e8`, flat 0.32, Yband 573) —
  emitted ≥2 primitives in the G16 ground-view log; floor-vs-flat-ledge role UNKNOWN until re-logged on
  the floor.
- **No patch/build prepared** (guardrail: no floor target from bbox alone). G17 = re-run the `0x800108b4`
  log while standing on / framing the walkable floor, capture `a0`+`s3` packet screen-XY (or BP
  `0x80010718` for `t5/t6/t7` SXY) to confirm the primitive lands on the floor, then build a single-s16
  Y deform. Detail + runbook in
  [geometry_g17_floor_payload_candidates.md](geometry_g17_floor_payload_candidates.md).
- **RUNTIME RESULT (Candidate B, 2026-06-14):** broad floor view, Flik centered, EXEC `0x800108b4` — **all
  17 hits = one payload `a0=0x801bdc5c` → base `0x801bdc58`**. `a0−4−DATbase = 0x5d460` is **INVALID**
  (`> 0x51418` EOF); output-buffer offset `0xc048`. Classification **EMITTED FLOOR/TOP-SURFACE CANDIDATE /
  RUNTIME-GENERATED OR OUTPUT-BUFFER PAYLOAD / DAT SOURCE UNKNOWN**. The walkable floor is **NOT** a
  LEVEL.DAT payload → the static floor shortlist does not apply to this view. → **G18 trace.**
  Collision/pathing UNKNOWN.

### G18 status (STATIC TRACE + RUNTIME RUNBOOK 2026-06-14) — output-buffer floor payload source
- **Where `0x801bdc58` sits:** EOF `0x801b1c10` `+0xc048`; past pass-1 output `0x801b5890` and reserved end
  `0x801b6a10` (`+0x7248`) → in the **"next resource"** heap region (G3 map). Not the DAT, not the matrix
  output buffer, not the reserved gap. `0x5d460` is **not** a DAT offset.
- **Static trace (CONFIRMED):** parser `fcn.8001cdc0` called **once** (`jal @0x8003d568`); all 1248 reloc
  targets in `[0x45f0,0x4f32c]` (max `<< 0x5d460`); emitter loads `a0` **directly** from `[s2+0x1c]`
  (`0x80020684`) / `[s2+0x20]` (`0x80020694`) with **no base add**, then `0x80020698 jal fcn.80010000`
  (the only real caller). So `0x801bdc58` is **not** parser-relocated; the source-record payload field was
  written at runtime (a generator), or `s2` is heap-resident.
- **LIKELY source:** separate LEVEL01 terrain resources — `LEVEL.RAW`(`0xb68e4`)/`LEVEL1.RAW`(`0x84210`)/
  `TERRAIN.ALL`(`0x39d8c`)/`TERR1.ALL`(`0xf078`); `TERRAIN.ALL`/`TERR1.ALL` start with s16 coordinate-pair
  streams (terrain mesh, not the `fcn.80010000` payload format → converted at runtime). Exe references
  `level.raw`/`bits\plantter.all`/`terr1`/`.all`. The walkable floor is **not in LEVEL.DAT** (explains all
  prior negatives).
- **DAT source NOT found.** Next: narrow runtime **WRITE watch `0x801bdc58`** during load (= the
  generator/writer PC + the resource it copies from) + EXEC BP `0x80020684` cond `a0==0x801bdc5c` to read
  `s2` (DAT `<0x801b1c10` vs heap `≥`). Do not patch runtime-buffer addresses. Detail:
  [geometry_g18_output_buffer_floor_trace.md](geometry_g18_output_buffer_floor_trace.md). Collision/pathing
  UNKNOWN — visual floor ≠ collision floor.

### G18b status (CANDIDATE B-LIKE LOG + DAT DECODE 2026-06-14) — DAT-backed payload `0x2d460` = instanced decor, not floor
- **Separate log, do NOT merge with the exact Candidate B (`0x801bdc58`).** A near-floor re-log of EXEC
  `0x800108b4` (operator moved very close to the Candidate B floor view, not pixel-identical) showed all
  parsed hits at `a0=0x8018dc5c` → base `0x8018dc58` → DAT off **`0x2d460`** — **VALID** (`< 0x51418`), i.e.
  **direct LEVEL.DAT-backed** (unlike the heap `0x801bdc58` = off `0x5d460`, past EOF). Emit-confirmed ≥17
  primitives; 17-hit `s3` table `0x801d1f38..0x801d26f0`.
- **Static decode (CONFIRMED) supersedes the operator's "floor candidate" read:** payload `0x2d460` = count
  25, footprint 202×107×194, flatness 0.53, command stream `0x2d590..0x2d6ec` (first cmd `ctrl 0x0060` type 0
  + 14-element strip), all 25 verts referenced (2–5× each) → a small closed blob; **93 pass-1 source records
  point at it** (flag `0x19`, scale ≈`(4349,4096,3153)`, scattered vec/angle) → **heavily instanced
  decor/prop, NOT walkable floor.** Same trap as G15 (high-frequency instanced `a0` = decor → reject; ×93).
- **Edit-target decision: NO build.** Fails every floor filter; payload-vertex visibility already proven
  (G14/G16). Reference-only proposed decor-confirmation edit (v22 `y`, `DAT 0x2d56e` `95 ff`/−107 →
  `95 fb`/−1131, −1024) recorded but not built/committed. Walkable floor remains the heap payload
  `0x801bdc58` (not in LEVEL.DAT). Detail:
  [geometry_g18_dat_backed_floor_candidate.md](geometry_g18_dat_backed_floor_candidate.md). Collision/pathing
  UNKNOWN — visual ≠ collision.

### G19 status (RESOURCE INVENTORY + LOADER TRACE + RUNTIME-CHECK PROPOSAL 2026-06-14) — floor is LIKELY a SECOND parsed DAT
- **Pivot:** `0x801bdc58` reclassified **OBSERVED ONCE / NOT REPRODUCIBLE** (DuckStation GUI has no
  conditional BP → no F5 grinding for `a0=0x801bdc5c`); the reproducible nearby hit is DAT decor `0x2d460`.
  Stop reproducing the pointer; identify the floor **resource/source**.
- **LEVEL01 sidecars (CONFIRMED, `REBUILD/files/LEVEL01/`):** `LEVEL.RAW`(`0xb68e4`)/`LEVEL1.RAW`(`0x84210`)
  = **compressed** (magic `00 00 83 0c`); `TERRAIN.ALL`(`0x39d8c`)/`TERR1.ALL`(`0xf078`) = **uncompressed s16
  (x,z) coordinate streams** (+`01 00 02 00` sub-header); `LEVEL.BIN`(`0x690`)/`LEVEL1.BIN`(`0xa8c`) = **MIPS
  overlay code**; **`LEVEL1.DAT`(`0x1a568`)/`LEVEL2.DAT`(`0x40784`) = parser-format DATs that CONTAIN wide-flat
  floor-signature payloads** (LEVEL.DAT does not). Audio: `LEVEL1A.VB/VH`, `LEVEL2C.VB/VH`.
- **Loader (CONFIRMED disasm):** `fcn.8003cf2c` = resource-id dispatcher (jump table `0x8001afb0`, 17 handlers,
  **4 callers** `0x8003f544/0x800503cc/0x80052290/0x8005b830`) → shared file-read `fcn.80046330` (`0x8003d550`,
  sets DATbase `[0x80082498]`) + parse `fcn.8001cdc0` (`0x8003d568`). Filename tables at exe VA `~0x8001ae00`
  (level/level1/level2/level3 ×.dat/.raw/.bin, gfx\*, fmv\) and `~0x80082128` (terr1/terr2/terr3/terrain ×.all,
  bits\plantter.all, bits\memory.bin).
- **CORRECTION to G18 "parser called once":** that is the SINGLE STATIC CALL SITE, not runtime-once — the
  loader has 4 callers and dispatches per resource, so the parser runs **once per DAT loaded**. A **second
  parsed DAT** (LEVEL1/LEVEL2.DAT) is relocated against its own heap base → its payloads land in `0x801bxxxx`
  where the floor sits. (G18's LEVEL.DAT-image facts still hold.)
- **Floor-source hypotheses:** **H1 (LEADING)** second parsed DAT (LEVEL1/LEVEL2.DAT — native payload format,
  contain floor payloads); **H2** TERRAIN.ALL/TERR1.ALL converted at runtime (weaker); **H3** decompressed
  `.RAW` (least likely). Exact file+offset **UNKNOWN** — none of bases `0x801b1c10`/`0x801b5890`/`0x801b6a10`
  makes `0x801bdc58` a clean payload, so an intervening load/alignment shifts the 2nd-DAT base.
- **Proposed runtime check (no `a0` reproduction, deterministic at load):** EXEC BP `0x8003d550` (read path
  `a0`=`sp+0x10`, dest base `a1`, size) + `0x8003d568` (read DATbase `[0x80082498]`, filesize) → log every
  `(filename→base,size)`; the DAT whose `[base,base+size)` contains `0x801bdc58` owns the floor (offset =
  `0x801bdc58 − base`). Alt: WRITE-watch `0x801b6a10` during load. No patch/build. Detail:
  [geometry_g19_floor_resource_source.md](geometry_g19_floor_resource_source.md). Collision/pathing UNKNOWN.
  **(SUPERSEDED by G20: the trace ran → parser ONCE → H1 REFUTED; floor source = terrain `.all`, see below.)**

### G20 status (SIDECAR LOADER MAP + RUNTIME RUNBOOK 2026-06-14) — floor source = terrain `.all` (non-parser)
- **Loader-trace result (operator):** `EXEC 0x8003d550` & `EXEC 0x8003d568` each hit **once**, `a1=0x51418`
  (LEVEL.DAT), no further hits → **parser `fcn.8001cdc0` runs EXACTLY ONCE for LEVEL01**. **G19 H1 (second
  parsed DAT) REFUTED;** G18 "parser once" re-vindicated. Stepping deeper into this path = circular.
- **Why insufficient:** only `0x8003d550` (of the **14** `fcn.80046330` file-reads) feeds the parser; all
  other resources (terrain `.all`, `bits\memory.bin`, `fmv\fmv.bin`, audio `.vb/.vh`, `.anm`, a high-heap
  streamed load) load via different sites and **bypass** `fcn.8001cdc0`. The operator watched only the DAT path.
- **PRIME non-circular target = terrain `.all` loader (CONFIRMED disasm):** `fcn.8005d654` (sidecar load loop,
  16 callers, indexes object table `0x800a6300`) → `fcn.8002ffa8` (builds `<name>.all` from name table
  `0x80082128`=`.all`/`0x80082138`=`terr1`/`0x80082150`=`terrain`; file-read **`0x8002ffe4`** to `[s0]`) →
  `fcn.8002fce8` (processes the `.all` s16 (x,z) stream into `0x4c`-stride records at `0x80098a8a`). The
  orchestrator loads each terrain slot into a **heap cursor `[s1]`** and advances it — same pattern that left
  LEVEL.DAT's cursor at `0x801b6a10`, so terrain `.all` lands in the `0x801bxxxx` region where the floor
  `0x801bdc58` sits. `TERRAIN.ALL`/`TERR1.ALL` are s16 (x,z) streams (not verbatim payloads; `0x7248` is not a
  payload in either) → floor mesh is **runtime-generated**. Other sites: memory.bin `0x8003d310/0x8003f5d0`→
  `0x800b5788`; fmv `0x8003e7fc/0x8003f578`; audio `0x80042f58`; anm `0x8005d6ec`; **high-heap load `0x8003a388`
  → dest `~0x801cc390`** (H3/RAW candidate).
- **Hypotheses re-ranked: H2 (terrain `.all` → generated floor) LEADING; H1 REFUTED; H3 (decompressed
  `LEVEL.RAW`) open/lower.**
- **Recommended runbook (ONE, deterministic, no `a0` repro):** EXEC `0x8002ffe4` (+ sibling `0x80030dc0`) at
  LEVEL01 load → record `a0`(built filename), `a1`(dest base), step-over size, `s0/s1/s2/ra`; test
  `a1 ≤ 0x801bdc58 < a1+size` → floor lives in that terrain file (offset `0x801bdc58 − a1`). Fallback: EXEC
  `0x8003a388` (high-heap loader). No patch/build. Detail:
  [geometry_g20_sidecar_loader_trace.md](geometry_g20_sidecar_loader_trace.md). Collision/pathing UNKNOWN.
  **(CORRECTED by G21: this runbook got 0 hits → terrain `.all` NOT confirmed; H2 downgraded; see below.)**

### G21 status (CALLER MAP + NEGATIVE RESULT + CALLEE-ENTRY RUNBOOK 2026-06-14) — watch `fcn.80046330` entry
- **Negative result:** operator armed `EXEC 0x8002ffe4` & `EXEC 0x80030dc0` (G20 terrain `.all` reads) → **0
  hits** during LEVEL01 load. **G20 "prime target / H2 leading" REFUTED;** H2 now open/unconfirmed. Two
  CONFIRMED structural misses: (a) orchestrator `fcn.8005d654` **skips the file-read when terrain is cached**
  (`0x8005d76c bnez v0,0x8005d794` → `fcn.8002fce8` runs, no load); (b) high-heap loader `fcn.8003a318`
  (read `0x8003a388`) is reached **indirectly** (no direct `jal`) → no call-site BP catches it.
- **Universal loader (CONFIRMED): `fcn.80046330(a0=bare filename, a1=dest) → v0=bytes`** (prepends CD/level
  dir). All **14** file-read sites funnel through it. CALLER MAP (14 sites → 11 fns): **#1 `0x8003d550`
  `fcn.8003cf2c`** = LEVEL resource dispatcher (builds `level<N>.<ext>` via `fcn.80046538`+name table
  `0x8001ae54/60`; loads **all** `level*.dat/raw/bin`; **fired LEVEL.DAT ×1 `0x51418`**); #2/#10 `bits\memory.bin`
  →`0x800b5788`; #3/#4 terrain `.all` (`fcn.8002ffa8`/`fcn.80030d64`, **0 hits**); **#6 `0x8003a388`
  `fcn.8003a318`** high-heap loader (**dest `0x801cc390 − align(size)` top-down**, indirect = PRIME); #7 fixed
  `0x800b39a0`; #8/#9 `fmv\fmv.bin`; #11/#12 audio `.vb`; #13 fixed `0x80095398`; #14 `.anm`.
- **All `level*.{dat,raw,bin}` funnel through #1**, which fired only for LEVEL.DAT → LEVEL1/2.DAT, LEVEL.RAW,
  LEVEL.BIN did not load via the dispatcher in the window (cached/other phase/indirect). **High-heap suspect:**
  `fcn.8003a318` region can **contain** `0x801bdc58` for files ≥`0xe738` above the DAT (TERR1.ALL `0xf078` →
  `[0x801bd318,0x801cc390)`, floor +`0x940`; LEVEL1.DAT `0x1a568` → +`0xbe30`); raw bytes there aren't clean
  payloads → floor is **generated** (static can't pin; runbook can).
- **Recommended runbook (ONE, broad-but-narrow, no `a0` repro): `EXEC 0x80046330` (callee entry).** Every load
  funnels here (incl. the indirect high-heap loader + cached-skip cases). Record `a0`(filename C-string),
  `a1`(dest), `ra`(caller→subsystem via the map), `v0`(size via one-shot BP at `ra`); test
  `a1 ≤ 0x801bdc58 < a1+size` → that file is the floor source (offset `0x801bdc58 − a1`). If none brackets it
  through load→gameplay → floor is **cached/boot-generated** → escalate (arm `0x80046330` from title screen, or
  watch processor `EXEC 0x8002fce8`). No patch/build. Detail:
  [geometry_g21_file_read_caller_map.md](geometry_g21_file_read_caller_map.md). Collision/pathing UNKNOWN.

### G22 status (HIGH-HEAP BRACKET + SOURCE FILE = LEVEL.RAW 2026-06-14) — floor resource NAMED
- **The G21 runbook worked.** `EXEC 0x80046330` **Hit #4** (`ra=0x8003a390` = the indirect high-heap loader
  `fcn.8003a318`, G21's PRIME suspect): dest `a1=0x80115aac`, size `v0=0xb6be4`, range `[0x80115aac,0x801cc690)`
  **brackets the floor `0x801bdc58`** → source offset `0xa81ac`. **Hit #6** control = LEVEL.DAT (`a1=0x801607f8`),
  does not bracket.
- **Source file = LEVEL.RAW (CONFIRMED by size+dest):** `fcn.8003a318` sets `dest = 0x801cc390 − align(filesize)`;
  `0x801cc390 − 0x80115aac = 0xb68e4` = **LEVEL.RAW's exact logical size** (bytes-read `0xb6be4` = `+0x300`
  padding); next-closest sidecar 207 KB off. `0xa81ac` = 92% through LEVEL.RAW. (Hit #4 before Hit #6 → LEVEL.RAW
  loads first; the DAT+output overwrite its lower-middle; the floor sits in the surviving upper part above
  `0x801b6a10`.)
- **NOT verbatim/editable at `0xa81ac`:** `LEVEL.RAW[0xa81ac]` `u32=0x70d4001a` (impossible count) — an
  **indexed-geometry stream**, not the `fcn.80010000` `{u32 count; vertex 0xc; cmds}` format. The floor emitted a
  valid payload at runtime → runtime `0x801bdc58` ≠ disk `LEVEL.RAW[0xa81ac]` → floor is **runtime-converted from
  LEVEL.RAW** (confirms G18 "runtime-generated floor", now NAMES the file). `fcn.8003a318` = resource-setup
  (loads LEVEL.RAW, inits global tables `0x800a65b0`/`0x8009fc10`/`0x80095138`/`0x80098638`); the buffer is
  consumed by the converter. A direct `0xa81ac` file edit is invalid.
- **Recommendation (Option A, no patch):** read-only decode of LEVEL.RAW's geometry format around `0xa81ac`
  (vertex pool + index grammar) toward an eventual LEVEL.RAW-format edit (never LEVEL.DAT) + one deterministic
  confirm at Hit #4 (read `a0`=`"level.raw"`; read `0x801bdc58` right after load, compare to
  `LEVEL.RAW[0xa81ac]`=`1a 00 d4 70`). Detail:
  [geometry_g22_high_heap_floor_source.md](geometry_g22_high_heap_floor_source.md). Collision/pathing UNKNOWN.

### G23 status (LEVEL.RAW IS COMPRESSED 2026-06-15) — floor = decompressor output; no editable field at 0xa81ac
- **`LEVEL.RAW[0xa81ac]` is COMPRESSED data,** not geometry: window `[0xa8000,0xa8400)` = 213 distinct bytes/1024
  (high entropy); s16 reads are noise; a full-file scan finds **0** clean `fcn.80010000` payloads. The G22-observed
  "incrementing indices" were compressed-stream artifacts (G22 over-read them — CORRECTED).
- **Consumer = `fcn.8001a1dc` = LZ/Huffman bitstream DECOMPRESSOR (CONFIRMED disasm).** `fcn.8003a318` calls it:
  `0x8003a4c8 lw fp,0x588(gp)`; `0x8003a4e0 move a0,s5`(=LEVEL.RAW base `0x80115aac` compressed); `0x8003a4e4 jal
  0x8001a1dc`; `a1=fp`(=`[gp+0x588]` decompressed dst); `0x8003a4ec lw s4,(fp)`. Traits: full register-context
  save/restore (all GPRs); big-endian control-word fetch; bit-by-bit flag reader; literal-run copy `0x8001a418`
  (`lbu(v1);sb(a1);a1++`); back-ref match `0x8001a658`; **no jal; no GTE; single caller**. Span
  `0x8001a1dc..0x8001a8f8`. Control stream is **big-endian**.
- **So the floor `0x801bdc58` = DECOMPRESSOR OUTPUT** (valid payload), while `LEVEL.RAW[0xa81ac]`=`0x70d4001a` is the
  compressed byte that loads at that address (decompression overwrote it). `0xa81ac` is **NOT a coordinate, NOT
  editable**. Confirms+sharpens G18/G22 "runtime-generated floor" → the process is **decompression**.
- **No safe edit target** (compressed). A floor edit needs decompress→edit→recompress (decode the `fcn.8001a1dc`
  codec) — not a file-byte patch; safer than patching runtime output `0x801bdc58`.
- **Next (one BP):** `EXEC 0x8001a1dc` → read `a0`(src=LEVEL.RAW)/`a1`(dst=`[gp+0x588]`)/size → confirm
  `[a1,a1+size)` contains `0x801bdc58`. Static follow-on: decode the `fcn.8001a1dc` bit grammar to decompress
  LEVEL.RAW offline. Detail:
  [geometry_g23_level_raw_floor_format.md](geometry_g23_level_raw_floor_format.md). Collision/pathing UNKNOWN.

### G24 status (DECOMPRESSOR GRAMMAR PARTIAL 2026-06-15) — fcn.8001a1dc = LZSS/LZ77 + var-len codes; no decoder invented
- **`fcn.8001a1dc` (`0x8001a1dc..0x8001a8f8`, ~456 instrs, single caller `0x8003a4e4`) decoded as a custom
  LZSS/LZ77 + variable-length-code decompressor (CONFIRMED structure):** prologue saves all GPRs; reads two
  **big-endian** header words `word0=BE32[src+0]`/`word1=BE32[src+4]` → `a2=dst+word0`/`a0=src+0xe+word1`, **both
  computed then NEVER read** (dead; purpose UNKNOWN); header `0xe` bytes; `v1=src+0xe` cursor; `dst`=output.
- **Bit reader:** MSB-first, byte-at-a-time from `v1`, guard-bit refill (~9 inlined reload sites). **Main loop
  `0x8001a658`** = LZSS flag bit: `0`→ copy one inline literal byte (`*a1++=*v1++`); `1`→ match. **Match:**
  var-len length code (escape@9→`N×4` literal run `0x8001a3fc`; long byte `0x8001a708`, **byte==0 = TERMINATOR**
  `0x8001a804`, else `+8`); 16-bit distance (hi bits coded+byte-swap | inline low byte); back-ref `out−dist−1`;
  copy odd-byte + 2/iter (+RLE when dist-hi==0). **Termination bit-driven** (NOT `word0`); final scratch flush is a
  **no-op** here.
- **Exact length/distance code tables + `word0`/`word1` meaning NOT byte-exact** → per the task rule, **NO offline
  decoder invented** (would be guessing). The dead `word0`/`word1`/`a0`/`a2` hint at a two-stream/size-checked
  variant not taken on this path (UNKNOWN).
- **NEXT (one BP, ground truth):** `EXEC 0x8001a1dc` → record hit count, `a0`(=LEVEL.RAW `0x80115aac` src),
  `a1`(=`[gp+0x588]` dst); at the return dump a decompressed-output window. Floor **decompressed** offset =
  `0x801bdc58 − dst` (≠ compressed `0xa81ac`); search output for the floor `fcn.80010000` payload. That ground
  truth validates any future `tools/decode_level_raw.py` byte-exactly. Detail:
  [geometry_g24_level_raw_decompressor.md](geometry_g24_level_raw_decompressor.md). Collision/pathing UNKNOWN.

### G25 status (POST-DECOMPRESS TRACE 2026-06-15) — per-chunk decompress LOOP; floor built post-decompress
- **Operator `EXEC 0x8001a1dc` trace:** the decompressor is called **MANY times** (every hit `ra=0x8003a4ec`,
  `gp=0x80081d98`) → it runs in a **per-chunk loop** in `fcn.8003a318` (single static call site `0x8003a4e4`,
  looped). `a0` walks the compressed LEVEL.RAW buffer `[0x80115aac,0x801cc690)`; `a1` (`=fp=[gp+0x588]`) walks the
  decompressed output. **Resolves G24 "once vs per-block" → PER-BLOCK.**
- **Loop (CONFIRMED disasm):** entry `0x8003a4cc j 0x8003c2a4`; head `0x8003c29c` reads `s5[0..3]`, `ff ff ff ff`
  (= `word0` sentinel) → finalize `0x8003c2dc`; else body `0x8003a4d4`: `jal 0x8001a1dc(a0=s5,a1=fp)`, `s4=fp[0]`
  = **chunk subtype**, big **type dispatch** `0x8003a4ec..0x8003c250` consumes the decompressed chunk (`s3=fp`) and
  builds a resource; per case `fp += align4(word0)` (e.g. `0x8003c13c`); tail `0x8003c250` `s5 += word1+0xe`; loop.
  Finalize `0x8003c2dc`: `[gp+0x4a0]=0x801cc390` (high top), `[gp+0x588]=final fp`, `jal 0x80063508 ×2`, return.
- **Resolves G24 "word0/word1 computed-then-dead":** dead *inside* the codec, **live in the caller** — `word0` =
  per-chunk **decompressed** size (advances `fp`), `word1` = per-chunk **compressed** size (advances `s5`), `0xe` =
  chunk header length; `word0==0xffffffff` = stream terminator. Matches the operator's deltas (`a0 += word1+0xe`,
  `a1 += word0`).
- **Source-side compressed bracket for `0xa81ac`:** the chunk with `a0=0x801bd58f` (next `a0=0x801bf662`) contains
  the floor address `0x801bdc58` at `+0x6c9`; that chunk's decompressed output `a1=0x80143438..0x80147500` (span
  `0x40c8`).
- **DECISIVE NEGATIVE:** `a1`/`fp` tops at **`0x8015fcbc`**; the floor `0x801bdc58` is **`+0x5df9c` above** → the
  floor is **NOT direct decompressor output**. It sits in `[final-fp 0x8015fcbc, high-top 0x801cc390)` = upper
  high-heap (consumed-compressed tail), `0xe738` below the top.
- **CORRECTED MODEL:** the walkable-floor `fcn.80010000` payload at `0x801bdc58` is **built by a post-decompression
  stage** (a geometry-family subtype case in `fcn.8003a318` writing into the high region, and/or a later converter
  reading the decompressed output) — **not** the raw decompressor. Exact writer = **UNKNOWN**. Candidate builders:
  `fcn.8003cc58` (×5, consumes `s3+0xc`), hot helpers `0x800628c0`/`0x800625fc` (×10) / `0x80061a48` (×9),
  `0x80055db0`, finalize `0x80063508` (×2). The operator's "odd final row" (`pc=0x8003f33c`) is a **GPU/DMA
  spin-wait**, not a chunk — correctly excluded.
- **NEXT (decisive, ≤3 BPs):** **WRITE watch `0x801bdc58`** during load → record writer `pc`/`ra` + the copied
  source (decompressed `[..,0x8015fcbc)` vs leftover compressed vs computed); **secondary EXEC `0x8003a4ec`** to log
  per-chunk `s4`(subtype)/`fp`/`s5` and tie `0xa81ac` to a subtype; tertiary `0x8003c2dc`/`0x80063508` only if the
  write watch doesn't fire in the loop. No patch/build. Detail:
  [geometry_g25_level_raw_post_decompress_trace.md](geometry_g25_level_raw_post_decompress_trace.md).
  Collision/pathing UNKNOWN.

### G26 status (CORRECTION + PIVOT 2026-06-15) — `0x801bdc58` is compressed LEVEL.RAW source, NOT a floor payload
- **Operator ground truth RETRACTS the floor-at-`0x801bdc58` premise (G17 Candidate B → G18/G19/G22/G25):**
  (1) at `Press X to Continue`, `[0x801bdc58] = 0x70d4001a` = `LEVEL.RAW[0xa81ac]` exactly (compressed source word);
  (2) **WRITE watch `0x801bdc58` during load = 0 hits** (never written). ⇒ `0x801bdc58` is **compressed LEVEL.RAW
  source**, unchanged across load — **never** an `fcn.80010000` render payload.
- **Acceptance test it fails:** a real payload base `P` needs `[P]` = a plausible small vertex count and s16-coord
  vertices at `P+4`. `[0x801bdc58]=0x70d4001a` = 1.9 billion (impossible; LEVEL.RAW is `0xb68e4` total) and the
  `0xa81ac` window is compressed (213 distinct/1024, G23). Not a payload.
- **Re-audit (disasm-grounded): the `a0−4` formula is CORRECT, not the bug.** In `fcn.80010000` the count>0 main
  path (`0x8001024c..`) never rewrites `a0` (only the entry `a0+=4` and the count≤0 sub-path do), so at the gate
  `0x800108b4` `a0` = vertex base = payload+4 ⇒ `payload = a0−4` for a *genuine* call. The G17 hits' `a0−4 =
  0x801bdc58` was **never count-validated**; a real call with count `0x70d4001a` cannot emit 17 clean primitives →
  those hits did not map to a valid floor payload (wrong context/timing/stale `a0`). `s5` is reused
  (`lui s5,0x8008` @`0x80010298`) so it is *not* the vertex base in the main path.
- **PRESERVED (LEVEL.RAW pipeline RE, independent of the floor):** LEVEL.RAW loads compressed to `0x80115aac`
  (G22); `0x801bdc58 = LEVEL.RAW+0xa81ac` (now *proven* by the Press-X byte); `fcn.8001a1dc` per-chunk decompress
  loop in `fcn.8003a318`, `word0`/`word1` = decompressed/compressed sizes (G24/G25). These characterize the
  resource, **not** the floor.
- **STATUS:** the walkable-floor/top-surface render payload pointer is **UNKNOWN**. (G16's `0x356bc` is a real
  DAT-backed payload but a **wall**; the static floor shortlist e135 `0x1f148`/e254 `0x08f4c`/e52 `0x17d94` are
  DAT-backed candidates with no emitted evidence.)
- **NEXT (≤3 BPs, count-validated, consumer side):** PRIMARY **EXEC `0x80010000`** at a confirmed floor view →
  record PC, `a0`(=payload base), `[a0]`(count — VALIDATE; reject `0x70d4001a`/huge/neg), first `0x40` bytes at
  `a0`, `a1/a2/a3`, `ra`(caller). SECONDARY **EXEC `0x800108b4`** → `payload=a0−4`, cross-check count, read `s3`
  packet screen-XY (or BP `0x80010718` SXY) to confirm prims land on the floor. Classify `P`: DAT-backed
  (`P−0x801607f8 ∈ [0,0x51418)`) / LEVEL.RAW-decompressed (`P < 0x8015fcbc`) / generated. No patch/build. Detail:
  [geometry_g26_floor_payload_reaudit.md](geometry_g26_floor_payload_reaudit.md). Collision/pathing UNKNOWN.

### G27 status (COUNT-VALIDATED DECODE 2026-06-15) — 5 genuine payloads; Candidate A = strongest floor/top-surface
- **The G26 runbook ran.** Operator captured five `fcn.80010000` payloads at **EXEC `0x80010000`** (a0 = RAW
  payload base) in the Candidate-B floor view. **All five pass the G26 §2 acceptance test** (`[a0]` = claimed count
  EXACTLY 83/48/58/36/25; `pad==0` 100%; clean `ffff ffff` terminators; all N verts referenced) and **all are
  DAT-backed** (`a0−DATbase ∈ [0,0x51418)`) — genuine, unlike the retracted `0x801bdc58` (`0x70d4001a`). Decoded
  read-only via `tools/analyze_g27_floor_candidates.py`; **decoder validated by Candidate E reproducing the
  committed G18b `0x2d460` decode** (25v, 202×107×194, flat 0.53, **93** source-record refs).

  | cand | DAT off | cnt | flat | Y-IQR | footprint | coord space | refs | class |
  |------|--------:|----:|-----:|------:|-----------|-------------|-----:|-------|
  | **A** | `0x188cc` | 83 | **0.154** | **316** | 4502×4502 | WORLD (Y≈4400–5060) | 1 | **FLOOR/TOP — STRONGEST** |
  | **B** | `0x38870` | 48 | 0.260 | 234 | 1757×1680 | WORLD (same stratum) | 1 | floor/top (adjacent tile) |
  | **C** | `0x38cb0` | 58 | 0.365 | 277 | 1706×2222 | WORLD (adj. in Z) | 1 | floor/top (edge relief/ramp) |
  | **D** | `0x38548` | 36 | 0.568 | 422 | 1935×1874 | MODEL (±950, −Y) | 1 | **NOT floor** (wall/struct-or-prop) |
  | **E** | `0x2d460` | 25 | 0.530 | 67 | 202×194 | MODEL (±100) | **93** | decor (CONFIRMED; = G18b) |

- **Discriminators (structure, not screen-visibility):** A/B/C carry large positive WORLD coords in one shared
  Y≈4400–5200 stratum → co-planar baked terrain (floor family); D/E are centered on the local MODEL origin → placed
  objects (prop/decor; E instanced ×93). A/B clear the floor filter (<0.35 flat, <900 band) decisively; C is
  borderline-flat with a tight core (edge lip/ramp); D/E fail flatness; all verts referenced → connected meshes.
- **Candidate A is the strongest floor/top-surface candidate** — flattest (0.154, beats the prior static shortlist
  e135 0.19), tightest Y core (316), widest (4502×4502), world-space, unique — and **DAT-backed (off `0x188cc`) →
  directly editable**, the property the retracted heap floor `0x801bdc58` lacked.
- **DOWNGRADES the G17/G18 "walkable floor is NOT a LEVEL.DAT payload" inference** (it rested on the retracted
  `0x801bdc58`): the count-validated floor-view emit *does* surface DAT-backed floor-shaped payloads (A/B/C).
  **UNKNOWN** (not claimed): whether A is the *walkable* surface vs a co-planar visual chunk; whether a
  LEVEL.RAW-decompressed/generated payload also feeds the view (A–E captured, not proven exhaustive).
  (`0x8018dc58`=Cand E = valid DAT payload; `0x801bdc58`=invalid compressed source — do not conflate.)
- **NEXT (ONE read-only BP):** EXEC `0x800108b4`, keep `a0==0x801790c8` (A vertex base), read `s3`-packet screen-XY
  (or `0x80010718` SXY) → confirm A's survivors project to the **lower-center walkable band** (Flik on it) before
  any edit (G16: emit-in-frame ≠ floor). Contingent edit spec ready (A v16 `y` @`DAT 0x18992` `89 13`→`89 17`,
  +1024, single byte; revert `89 13`) but **NOT built**. Detail:
  [geometry_g27_count_validated_floor_candidates.md](geometry_g27_count_validated_floor_candidates.md).
  Collision/pathing UNKNOWN — visual ≠ tangible.

### G28 status (RUNTIME READ + PROJECTION CONFIRMATION 2026-06-15) — Candidate A reaches the render/projection path
- **The G27 §5 gate ran (consumer side).** Operator confirmed Candidate A (`0x801790c4` / DAT `0x188cc` / count 83)
  is active in the floor view and reaches projection:
  - **READ watch `0x801790c8`** (A vertex base) **hit repeatedly** — `a0=0x801790c8`, `ra=0x800206a0`,
    payload base `a0−4=0x801790c4`, count at base = 83 (matches G27).
  - **EXEC `0x80010718`** (per-primitive site, after `mfc2 SXY0/1/2`) hit while A active:
    prim1 `SXY0=0x007A0164 SXY1=0x00730182 SXY2=0x007B0180`; prim2 `SXY0=0x007F01A8 SXY1=0x007701CF SXY2=0x008501F1`
    (same `a0`/`ra`). Unpacked `(Y<<16)|X`: **Y≈115–133 → central/lower-central band** (plausible floor); X≈356–497
    recorded raw (horizontal viewport mapping = TODO, G16).
- **Classification:** Candidate A = **VALID DAT-BACKED PAYLOAD / RUNTIME READ CONFIRMED / PROJECTION PATH CONFIRMED /
  LIKELY VISUAL FLOOR/TOP-SURFACE / TANGIBILITY UNKNOWN.**
- **Keep separate:** `0x801790c4` (Candidate A, valid DAT payload) vs `0x801bdc58` (compressed LEVEL.RAW source,
  RETRACTED G26, never written) — one hex digit apart; do not conflate. G26 retraction stands.
- **BUILT (embedded-verified) + OPERATOR-TESTED → VISIBLE TERRAIN DEFORMATION:** guarded same-size reversible edit
  `tools/patch_g28_candidate_a_floor_y_test.py` (LEVEL01/LEVEL.DAT @ `0x18992`, A v16 `y`, `89 13`→`89 17`,
  +1024, single byte; revert `89 13`; same-size `0x51418`; never in place; no collision/pathing files) was built
  via the shared `tools/rebuild_with_patched_dat.py` into `ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue` (patched DAT
  sha1 `a1cf8d8e…`; embedded DAT verified at LBA 2906; staged workspace restored to pristine `b376cb50…`;
  artifacts gitignored/not committed). **Operator test result (2026-06-15):** boots, LEVEL01 loads; the tested
  floor/terrain area **visibly deforms** (caves inward; shifts slightly with viewing angle) in the lower/central
  region matching A's projected area; Flik and other objects still render; **collision/pathing did NOT align with
  the visual deformation.**
- **Candidate A reclassified → CONFIRMED DAT-backed VISUAL terrain/floor render payload** (the `DAT+0x18992` edit
  affects visible terrain; A is **not** decor/grass/prop; A is part of the visible floor/top-surface render mesh
  in the tested area). **LIKELY** A belongs to the visible floor/top-surface mesh family of the Candidate-B view.
  **UNKNOWN:** the collision/pathing source for this surface, and whether A has any collision/tangibility data
  elsewhere. Explicit: **visual terrain payload ≠ collision/pathing source** — the tested deform did not
  alter/align with collision, so collision/pathing is separate or sourced elsewhere (no claim that collision
  moved; no tangibility claim). Detail:
  [geometry_g28_candidate_a_runtime_confirmation.md](geometry_g28_candidate_a_runtime_confirmation.md).
  Collision/pathing UNKNOWN — visual ≠ tangible; do not infer. **Next: G29 collision/pathing source discovery.**

### G29 status (ANALYSIS + RUNTIME-WATCH PLAN 2026-06-15) — collision/pathing source for the confirmed visual floor
- **Objective:** find the runtime data/function path that controls Flik's **ground contact / floor height /
  walkability / collision response** over the floor area G28 proved is a *visual* mesh (Candidate A). Use
  Candidate A only as a **visual anchor**; do **NOT** assume collision is in A, LEVEL.DAT, or LEVEL.RAW.
- **G28 split carried forward (CONFIRMED):** the `DAT+0x18992` edit visibly caved Candidate A's floor, but
  collision/pathing did **not** follow → `visual terrain payload ≠ collision/pathing source`. Collision source
  **UNKNOWN**.
- **Static recon (Task 1; existing evidence only):** the G5 negative stands — no static parser-geometry
  collision consumer; ~40 player-pos readers touch no geometry handle → the floor query uses a **non-global
  pointer or a non-parser source** → G29 must be **runtime-first**. Candidate targets:
  - `0x800a6504` **player Y** (`re_types.h` CONFIRMED) — floor contact resolves here; writer-of-Y UNKNOWN.
  - `fcn.8005b134` **LIKELY** floor/movement integrator (G5-named player-pos writer; Region-A overlay verbs).
    **Contradiction to resolve at runtime:** EXEC-doc L409 lists progress/pos writers
    `fcn.80047284/80048138/8004a700/800563d4/80056f68/8005b12c` — the WRITE watch decides which writes Y.
  - `fcn.80025084` oriented containment test (actor `0x800a0a64`, matrix `0x80090fb0`; caller `fcn.8004d224`)
    — plausible **wall/ledge** collision primitive (CONFIRMED shape / role UNKNOWN).
  - `PAD\PATH*.BIN` (≤1.3 KB) via loader `fcn.80046330` — **LIKELY** external pathing (CAUTION: likely
    AI/enemy, not Flik floor).
  - **DECOY/EXCLUDE:** contact array `0x800b0d18` + walker `fcn.800586b0` (player-Y bias −0x1cc0) = pickups.
- **Runbook (Task 2; ≤6 BPs/pass):** Pass 1 WRITE watch `0x800a6504` (stand+walk) → writer PC = integrator;
  Pass 2 EXEC that PC → find floor-height operand `S`, READ-watch it, classify band (DAT not A's vertex band /
  LEVEL.RAW-decompressed / sidecar / generated); **Pass 3 (DECISIVE)** READ-watch `S` over the floor pristine
  vs the G28-deformed patch — identical `S`/Y ⇒ collision **independent of Candidate A** ⇒ `S` CONFIRMED floor
  source; Pass 4 EXEC `0x80046330` entry → log loads, find a `PAD\PATH*.BIN`/sidecar buffer bracketing `S`;
  Pass 5 (low) EXEC `0x80025084` on wall/ledge contact.
- **False-positive guardrails (Task 3):** render path `fcn.80010000`/`0x800108b4`/`0x80010718` is NOT
  collision; visual deformation is NOT tangibility; `0x801bdc58` is compressed LEVEL.RAW source (not a payload;
  ≠ Candidate E `0x8018dc58`); do NOT assume LEVEL.RAW (retracted heap-floor theory) or LEVEL.DAT collision
  because the visual floor is DAT-backed; the contact walker's −0x1cc0 Y bias is a pickup artifact.
- **No patch/build/run this pass.** Detail:
  [geometry_g29_collision_source_plan.md](geometry_g29_collision_source_plan.md). Next runtime action: **Pass 1
  WRITE watch `0x800a6504`**. Collision/pathing UNKNOWN — visual ≠ collision.

### G29 Pass 1 RESULT (2026-06-15) — player-Y writer = `FUNC_3633C` @`0x8003633c` (NOT `fcn.8005b134`)
- **Operator ran Pass 1 (PRISTINE):** WRITE watch `0x800a6504`, Candidate-B floor, Flik moving. Writer PCs:
  `0x80036384` / `0x80036cf0` / `0x80036d58`; state at `0x80036384`: `a0=s1=s7=0x800a6500`, `a1=s5=0x800a652c`,
  `a2=0x800a6582`; others carry `ra=0x80036c70`.
- **Static disasm (SCUS_942.88, t_addr `0x80010000`+`0x800`; r2 read-only) resolves all three to ONE function:**
  `FUNC_3633C` head `0x8003633c` — per-frame **movement + collision-response integrator**. `s7=a0`=player struct
  base (rt `0x800a6500`); `s5=a1`=velocity/delta vec (rt `0x800a652c`=base+0x2c); `a2`=contact-flag bytes (rt
  `0x800a6582`=base+0x82). Callers (jal scan): `0x800495c8` (RA `0x800495d0`, observed), `0x8004c024`, `0x8004e628`.
- **DuckStation reports PC = store+4.** Four stores to `[s7+4]=0x800a6504`:
  - `0x80036380` `sw v0,4(s7)` `v0=[s7+4]−0xc80` (obs `0x80036384`) = **Y probe-bias DOWN** `0xc80`; NOT a floor value.
  - `0x80036cec` `sw v1,4(s7)` `v1=[sp+0x1c]` (obs `0x80036cf0`) = **COMMIT of the collision-RESOLVED position**
    (`X=[sp+0x18]`,`Y=[sp+0x1c]`,`Z=[sp+0x20]`) = the **floor/contact-corrected Y — the decisive write**.
  - `0x80036d30` `sw v0,4(s7)` `v0=[s7+4]+[s5+4]` (PC `0x80036d34`, **not** observed) = free velocity integration.
  - `0x80036d54` `sw a0,4(s7)` `a0=[s7+4]+0xc80` (obs `0x80036d58`) = **Y probe-bias UP** (restore); NOT a floor value.
- **Active collision helper = `0x800345cc`** (`ra=0x80036c70`=`0x80036c68+8`). `FUNC_3633C` calls `0x80035f24`
  (sweep), `0x800345cc` (→result code), `0x80035280` (alt). `0x800345cc`/`0x80035280` read `[gp+0x57c]`=collision-
  candidate COUNT (`gp=0x80081d98`→`0x80082314`), iterate a per-frame candidate list, write the resolved position
  into the `sp+0x10`/`sp+0x18` scratch buffer. **Floor-height source `S` = an element of that gp-scratch candidate
  list** (non-global pointer) → **vindicates** the G5 negative (no static parser-geometry collision consumer).
- **`fcn.8005b134` SUPERSEDED/PENDING (not erased):** store site is `0x8003633c`, not `0x8005b134`; `fcn.8005b134`
  has **0** jal callers (overlay/jump-table dispatched), `0x8003633c` has 3 (none = `0x8005b134`). "Sole player-pos
  writer = `fcn.8005b134`" no longer holds for the per-frame movement path; `fcn.8005b134` may write pos in another
  (scripted/spawn/overlay) context — relationship UNKNOWN. The `−0xc80` bias ≠ pickup `−0x1cc0`.
- **NEXT = Pass 2** (no patch/build/G28-compare yet): EXEC `0x80036cec` (resolved `[sp+0x18..0x20]` floor pos); EXEC
  `0x800345cc` (candidate-list base + floor-height operand `S`, `[gp+0x57c]=0x80082314` count); READ-watch `S`,
  classify band. Pass 3 (G28 differential) only after `S` is identified. Collision/pathing UNKNOWN; visual ≠ collision.

### G29 Pass 2 RESULT (2026-06-15) — resolved-Y is a per-axis ACCUMULATE; floor source = collision-candidate list (UNLOCATED)
- **Confirmed at EXEC `0x80036cec`:** `sp=0x801FFE00`, `v1=0xFFFE2196`, working buffer
  `[sp+0x18..0x24]={0x5B7B, 0xFFFE2196, 0xFFFFB44B, 0xFFFF0000}` (`[sp+0x1c]`==`v1`==resolved Y). **WRITE watch
  `0x801FFE1C`** (=`sp+0x1c`) caught **two** writers (r2-verified; PC=store+4):
  - **Hit A `0x80035EDC`→store `0x80035ED8` `sw v0,4(s5)`** inside helper **`0x800345cc`** = the resolved-Y COMPUTE.
    A 3-component **accumulate** `pos[i] (word @s5) += signed_halfword delta[i] (@s3)` (X `s5+0`←`s3+0`, Y `s5+4`←
    `s3+2`, Z `s5+8`←`s3+4`). `s5=0x801FFE18`=FUNC_3633C `sp+0x18` working buffer (passed as `s4`→`a1`→helper `s5`);
    `s3=0x801FFE10`=`sp+0x10` delta buffer (`a0`→helper `s3`). At the hit `[s3+2]=0` ⇒ Y delta 0 ⇒ value pre-existed
    (write site, not origin).
  - **Hit B `0x80036BE0`→store `0x80036BDC` `sw v1,0x1c(sp)`** inside FUNC_3633C = a COPY/seed
    `[sp+0x18..0x24]←[s7..s7+0xc]`, gated by `bgtz [gp+0x57c]`/`blez [gp+0x5cc]`. Propagation, not the origin.
- **Structural correction:** at Hit B **`s7=0x801FFEA8` = a STACK position vector, NOT the player global `0x800a6500`.**
  FUNC_3633C sets `s7=a0` at entry, so this invocation integrates a stack XYZ vector and its `0x80036cec` commit
  writes `[0x801FFEAC]`, not player Y. FUNC_3633C is a **reusable position+collision integrator** over whatever `a0`
  points at (Pass 1 caught the player-base invocation). **Do NOT claim `0x801FFEA8`=player**; the stack-vector→
  `0x800a6504` link is a separate step (UNKNOWN/TODO).
- **Source chain:** per-frame collision-candidate list (counts `[gp+0x57c]=0x80082314`,`[gp+0x5cc]=0x80082364`) →
  sweep helper `0x80035f24` (called `0x80036c50`; `a0=sp+0x10` delta-out) writes per-axis **deltas** → accumulate
  helper `0x800345cc` adds them into `sp+0x18` → commit `0x80036cec`. Floor-height value lives in the candidate list;
  its **backing region is UNKNOWN**. Source data structure = **PARTIAL**.
- **NEXT (Pass 2-next, one BP):** EXEC `0x80035f24` — dump `a0`(`sp+0x10` delta-out)/`a1`(`sp+0x18`)/`a2`(`s5`)/`a3`
  + candidate-list base (+`[gp+0x57c]`/`[gp+0x5cc]`); step to the `lw`/`lh` reading a floor-height candidate `S`;
  classify `S` band. (`0x80035ed8` only consumes pre-computed deltas — won't reveal the source.) No G28 compare until
  `S` found. No patch/build. Collision/pathing UNKNOWN; visual ≠ collision.

### G29 — candidate-record read/compare evidence (2026-06-15)
- **Evidence:** at `pc=0x80036B70` (`ra=0x800363CC`, `s5=0x801FFEB8`, `s7=0x801FFEA8` — the §Pass-2 stack-vector
  invocation), `v1` equals the 32-bit LE word at **`t1−0x08`**. CONFIRMED in 3 captures:
  `t1=0x800F7BB8 v1=0x11FC`, `t1=0x800F7B74 v1=0x121A`, `t1=0x800F7B30 v1=0x1300` (`[t1−0x08]` LE matches each). The
  `0x44` spacing is **between samples**, not a proven record stride. Records at **`0x800F7xxx`** = runtime/heap/BSS
  (above exe end `~0x80082800`, below DAT `0x801607f8`/RAW `0x80115aac`); **backing source UNKNOWN** (not DAT/RAW/decompressed).
- **Capture-point roles:** `0x80036B78` = post-read PC previously observed; `0x80036B74` = useful read/compare site;
  `0x80036B70` = stronger post-load/pre-compare capture point. **Exact load PC = TODO, likely near `0x80036B6C`**
  unless statically confirmed.
- **Pointer caveat:** earlier `0x80036B74` captures `t2=t1−0x30`, `t6=t1+0x90`; newer `0x80036B70` captures
  `t2=t1−0x30`, `t6=t2`. ⇒ `t2=t1−0x30` **appears stable**; the `t6` relationship is **state/site-dependent — not
  universal**.
- **Static (r2) grounding (confirm at runtime):** loop `0x800369a0..0x80036b7c` (in FUNC_3633C) walks a chained list
  of candidate blocks (`t2`; next-ptr `lw t2,-4(t2)`; count `lhu [t2]`); per entry `t1=t2+a3*0xc` (so `t2=t1−0x30` ⇒
  `a3=4`); `t6=t2` then `+=0xc0`/outer. Candidate `+4` word loads at `0x80036a38` `lw v1,4(t1)`, feeds a bounding/
  range-overlap compare (`slt v1,t5` @`0x80036a40`); after `addiu t1,t1,0xc` @`0x80036b40` it equals `[t1−0x08]`.
  Matches copied to output list **`0x80090868`** (stride `0xc`, count `[gp+0x5cc]=0x80082364`). So `[t1−0x08]` is
  **LIKELY a candidate scalar in the compare/selection path** (coordinate bound / range / ranking / contact metric) —
  **semantic UNKNOWN; NOT confirmed floor height.**
- **Boundary:** G28 Candidate A stays CONFIRMED visual/render only; its deform did not follow collision; **collision/
  pathing source remains UNKNOWN** (no claim about A). **Next:** static/decompile inspection `0x80036B6C..0x80036B78`
  to confirm the exact load. Authoritative BP block (doc only): `FINAL BREAKPOINTS: EXEC 0x80036B70`. No patch/build.

### G29 LIVE (2026-06-15, DuckStation external debugger + controller input; Flik MOVING) — collision/floor SOURCE identified
- **Setup:** JSON-RPC debugger `127.0.0.1:2346` + new `setControllerState`/`advanceFrames`/`pressButton` on
  `SCUS-94288_1.sav`. **Idle state has NO player collision** (`FUNC_3633C` never called for `0x800a6500`; every contact
  list empty) — **movement is required**. Holding `left` makes the player integrator run and resolve Y.
- **CONFIRMED data path** (live addresses): player XZ `0x800a6500` (moving) → **sector table `0x800a7e48`** (count
  `[gp+0x508]=223`, start `[gp+0x6cc]=191`; `0x30`-byte recs: AABB min `+0x14/+0x1c`, ext `+0x24/+0x28`, flag `+0x2c`,
  block ptr `+0x10`; `0x80036700`/`0x80036804`) → `[sector+0x10]` block (`0x800C1690`) → 32-byte collision records
  `~0x800D0xxx` AABB-tested (`0x80036820..0x8003690c`) → matches stored as **pointers** into the **`gp+0x57c` list
  `@0x8009c230`** (store `0x800368E8`) → resolution helpers (`0x800345cc`/accumulate `0x80035ED8`) → resolved
  `[sp+0x18..]` → **commit `0x80036CEC` writes player Y** `0x800a6504`.
- **Decisive capture (moving player):** `s7=0x800a6500`, `[gp+0x57c]=7`, list `@0x8009c230 =
  {0x800D0FA8,1028,1048,10C8,10E8,1108,1128}` (all `0x800D0xxx`), `posY −109521 → resolvedY −109693` (**dY=−172**,
  dZ=+189). Contact list non-empty **exactly during** Y resolution.
- **CONFIRMED:** floor/collision SOURCE = sector table `0x800a7e48` + `0x800C/0x800D` record blocks via `gp+0x57c`,
  reached by a **non-global** `[sector+0x10]` chain (the pointer the G5 scan couldn't see — G5 negative **vindicated**,
  now resolved). **Separate** from the DAT visual floor (Candidate A) and from the `gp+0x5cc`/`0x800F7xxx` grid (global
  `0x8009f9ec`, **0 winners** same-frame → LIKELY a secondary wall/object broadphase). **Directly EXPLAINS G28.**
- **TODO:** on-disk backing of `0x800a7e48`/`0x800C-0x800D` (LEVEL.RAW-decompressed vs collision sidecar vs generated)
  → WRITE-watch during **level load**; exact record-field→resolved-Y arithmetic in the helpers. No patch/build/mem-write;
  save state not overwritten. Detail: [geometry_g29_collision_source_plan.md](geometry_g29_collision_source_plan.md) §2.8.

### G29 LIVE — collision/floor ON-DISK SOURCE = LEVEL.RAW (decompressed) (2026-06-15)
- From the **pre-load** state `SCUS-94288_2.sav` (`[0x800a7e48]=0`, count=0 at load → before build), WRITE-watches
  pinned the source. **CONFIRMED full disk→player-Y chain:**
  `LEVEL.RAW` (compressed) → loaded `0x80115aac` by `fcn.8003a318` (G22) → **decompressed per-chunk by `fcn.8001a1dc`
  into `0x800F7xxx`** [WRITE hit `pc=0x8001A60C` in the decompressor, `ra=0x8003A4EC` in `fcn.8003a318`; compressed src
  `a0=0x8018B598`/`s5=0x8015ED7B` ∈ LEVEL.RAW buffer] → built+scaled(`<<5`) into the **sector table `0x800a7e48`** by
  `0x80030F60` (copies from src rec `t1=0x800F7BF8`; caller `0x800314CC`) → runtime: player XZ → sector AABB →
  `[sector+0x10]` → `0x800D0xxx` records → `gp+0x57c` list `0x8009c230` → helpers `0x800345cc`/`0x80035ED8` →
  commit `0x80036CEC` writes player Y.
- **⇒ collision/floor SOURCE FILE = LEVEL.RAW (decompressed).** The G22–G25 LEVEL.RAW pipeline's **payoff**: LEVEL.RAW
  carries **collision**; LEVEL.DAT carries the **visual** floor (Candidate A) — **definitively explains G28**.
- **TODO:** LEVEL.RAW is compressed (codec `fcn.8001a1dc`) → a collision edit needs decompress→edit→recompress /
  chunk-locate; exact decompressed record format + record→Y math. No edit attempted; slots 1&2 backed up; the build
  happens within the ~10–20 s load (≤45 s watch timeouts suffice). Detail:
  [geometry_g29_collision_source_plan.md](geometry_g29_collision_source_plan.md) §2.9.

### G29 LIVE — collision record format = PLANE; floor resolution = signed plane-distance clamp (2026-06-15)
- Decoded the `0x800D0xxx` records: they are **collision PLANES**. Format (sector-relative; `gp+0x57c` stores
  `record+12 = s0`): `s0+0/+2/+4` s16 = **normal** X/Y/Z (floor planes ⇒ |normal.y| dominant); `s0+6/+8/+0xa` s16 =
  **reference point** X/Y/Z, each `<<5` (×32 → world units, matching the `>>5` grid quantization); remaining bytes =
  selection AABB (+ likely edge data, TODO).
- **Resolver `0x800345cc` plane test** (`0x80034750..0x800347b8`, CONFIRMED disasm + read-watch at `0x80034760`):
  `d = Σ normal·(P − 32·refpt)` over XYZ (P = sector-relative pos+delta), `d >>= 14`; `d≥0` ⇒ in front (skip), `d<0` ⇒
  penetrating ⇒ swept-crossing clamp onto the plane → per-axis delta → accumulate `0x80035ED8` → commit `0x80036CEC`.
- Sector (`0x800a7e48[idx]`, idx from parallel list `0x80091718`): `+0/+4/+8` origin (sector-relative basis), `+0x10`
  record-block ptr. **Live ex.:** record `0x800D0FA8` normal `(-1941,-15885,3509)` (floor), refpt `(-461,249,296)×32`,
  sector idx 104 originY `-123808`, player Y `-109521 → -109693`.
- **⇒ "floor height" is a PLANE, not a scalar**; resolved Y = player clamped against the `gp+0x57c` plane records.
  These planes are the LEVEL.RAW-decompressed `0x800D0xxx` data (§2.9). **TODO:** exact clamp arithmetic
  `0x800347c4..0x80035ec0` + remaining record bytes (poke-confirm precluded by no-write guardrail). Detail:
  [geometry_g29_collision_source_plan.md](geometry_g29_collision_source_plan.md) §2.10.

### G29 LIVE — clamp math complete (swept crossing → nearest in-face → stop-with-skin) (2026-06-15)
- Finished the resolver `0x800345cc` per-record clamp (CONFIRMED disasm `0x800347c4..0x80034b30`): sector-relative
  `d_after=(N·(pos+δ−32·refpt))>>14`, `d_before=(N·(pos−32·refpt))>>14`; **swept test** processes only a front→back
  crossing (`d_before≥0 && d_after<0`); crossing `= δ·d_before/(d_before−d_after)`; **point-in-face** `0x80032610`
  (picks normal's dominant axis, 2D point-in-polygon over record edges `s0+0xc..+0x16`); keep **nearest** hit.
- Response (post-loop `0x80034a50+`, validator `0x800322a0`): **stop-with-skin** clamp per axis
  `resolved[i] = pos[i] + δ[i]·(d_before>>3)/((d_before>>3)−((d_after−0xc0)>>3))` → working buffer → commit
  `0x80036CEC` → player Y. The **`−0xc0` (192)** on `d_after` = a **collision skin** (Flik stops ~192 units in front of
  the plane). Distinct from FUNC_3633C's `±0xc80` entry probe.
- **Record format (resolver-final):** `s0+0/+2/+4` normal (fixed-point unit vec; `>>14` normalizes the dot);
  `s0+6/+8/+0xa` reference point (`×32`, polygon anchor); `s0+0xc..+0x16` face edges. Floor ⇒ `|normal.y|` dominant.
- **⇒ complete floor-contact record→Y math decoded.** TODO (minor): no-contact branch `0x80035210`, slide/re-test
  iteration, `0x800322a0` internals, remaining record bytes. **Next: the LEVEL.RAW collision edit** (decompress→edit a
  floor plane→recompress; collision analog of G28). Detail:
  [geometry_g29_collision_source_plan.md](geometry_g29_collision_source_plan.md) §2.11.

### G29 LIVE — collision EDIT validated in RAM; visual-floor exploration (2026-06-16)
- **Collision edit CONFIRMED in RAM:** lowering the sector-104 origin Y (`0x800A91C8+4`) moves Flik's resolved Y
  ~1:1 (e.g. +8192→endY +7499, +16384→+16496, −8192→−7603, same input/path) — he falls/lands, or **dies past the
  kill-plane** (≤ ~−8000 safe; −12288 = death/respawn). RAM edit faithfully mirrors a LEVEL.RAW edit (no build/disc-swap
  needed for validation). The resolver re-clamps **only while moving** (stationary edits don't snap him).
- **Visual floor under Flik = world-space dirt, NOT the object payloads:** spike + clean-uniform-shift tests on two
  emitted-payload sets were no-ops on the bulk dirt; toggling Candidate A doesn't change it; the collision sector
  record has only a `+0x10` (collision-block) pointer. **Candidate A** (`0x801790c4`, DAT `0x188cc`) **IS** an
  editable visual floor **tile** (clean uniform lower renders **stably** — operator image #2) but only at its
  dip-area location (DAT/model space, not the bulk dirt).
- **Engine notes:** render **caches transformed geometry** (camera movement refreshes; clean uniform edits stable,
  degenerate spikes flicker); **blind RAM corruption CRASHES**. `captureFrame`→PNG works for visual validation.
- ⇒ The bulk visible dirt is drawn by a member of the **GTE renderer family `0x80010000–0x8001a120`** other than
  `fcn.80010000` (objects); G6's `DAT+0x1526` trail gating points at the trail/pass path. Finding + editing it is a
  render-subsystem RE sub-project → **[G30 plan](geometry_g30_terrain_render_source_plan.md)** (R1–R6).

### G30 status (PLAN 2026-06-16) — visible-terrain render-source discovery + matched floor edit
- **Goal:** locate the world-space dirt renderer + its editable geometry, then lower it to **match** a collision edit
  (Flik falls onto a visibly-lowered floor on flat ground). Multi-step; live-debug + r2; no blind corruption.
- **Phases:** R1 map `fcn.800224ec`/`fcn.8003f938` call tree → terrain-renderer shortlist; R2 EXEC-BP the shortlist →
  find the big-ground-polygon emitter (by SXY); R3 trace its vertex-buffer base + format/coord-space; R4 READ-watch +
  ONE clean uniform Y edit (walk to refresh) → confirm + calibrate; R5 WRITE-watch at level load → on-disk source
  (LEVEL.RAW chunk); R6 matched visual+collision lower on a FLAT spot → screenshot.
- **R1 DONE** (call tree mapped, terrain narrowed to 6 emitters). **R2 DONE (cache-CLEAN, 2026-06-16, §11):** the
  cache-confounded interim is resolved — combined static frame-loop trace (scene fn `0x8004ecd4`, frame loop caller
  `0x8004fecc`, render cluster `0x8004f388–0x8004f458`) + 60-frame-movement neutralize (camera scrolled +11168 px ⇒
  cache refreshed). **Dirt persists in EVERY variant ⇒ "separate background layer" CONFIRMED cache-clean.** Side
  findings: `fcn.8001ea6c`/`fcn.80017b98` = wooden fence; `fcn.800140a0` = cull; `fcn.8001dfe4`/`fcn.8003f938`/
  `0x80053638` = no effect this state. **Exact dirt renderer still UNKNOWN — narrowed to: per-call-site neutralize of
  `fcn.800224ec` (`0x8004f428` vs `0x8004f448`), or method (d) GP0/vertex-buffer READ-watch (recommended next).**
  Full plan: [geometry_g30_terrain_render_source_plan.md](geometry_g30_terrain_render_source_plan.md).

### G5 status (ANALYZED 2026-06-14) — NEGATIVE result plus G6 separation evidence
- **No static collision/pathing consumer of the parser geometry found.** lui-tracking scan: the geometry
  record-type slots `TT[0x01/0x0b/0x0c/0x0d/-2..-7]` have **zero** readers (only `TT[0x3f]` pickups is
  consumed via the type table); only the render driver reads `G_TRAIL/PASS3`; **~40** functions read
  player pos `0x800a6500/04/08` but **none** also reads a parser-geometry handle.
- `fcn.80025084` (oriented containment) reads actor `0x800a0a64` (+0x80 coords `<<5`, +0x66 extent),
  object table `0x800a6300`, matrix `0x80090fb0` — **not** the parser geometry; one caller `fcn.8004d224`.
- Player-pos **writer** `fcn.8005b134` dispatches to Region-A overlay verbs; reads no parser geometry.
  Pathing data is external (`PAD\PATH*.BIN`). Detail in
  [geometry_collision_consumers.c](geometry_collision_consumers.c).
- G6 made terrain render mostly disappear while tested ground collision remained usable. This supports
  render/collision separation for the `DAT+0x1526` trail flag field, but does not map the collision
  pipeline.
- Conclusion: parser geometry's only identified consumer is the **render** path (G4); collision (if it
  uses this geometry) must do so via a non-global pointer, or uses a different data source.

## Source-record (`s0`) formats — RESOLVED in G2 (CONFIRMED)
There are **two** source-record formats, chosen per table entry by flag bit3 (`0x8`). This resolves
the G1 "`0x18` stride vs `[s0+0x1c]`" conflict: non-bit3 records are `0x18` bytes and never touch
`+0x1c`; bit3 records are `0x20` bytes. Shared prefix `{ s32 vec[3] @+0x00; s16 angle[3] @+0x0c }`.

**Non-bit3 record — `0x18` bytes** (174 pass1 + 85 pass3; dominant stride `0x18`):
| off | width | meaning | confidence |
|----:|------:|---------|------------|
| `+0x00` | 3×s32 | `vec[3]` coordinate-like (role UNKNOWN) | CONFIRMED shape |
| `+0x0c` | 3×s16 | `angle[3]` → `fcn.80017b98` (often 0,0,0) | CONFIRMED (used) |
| `+0x12` | s16 | scalar; **not used by parser on this path** | CONFIRMED present / role UNKNOWN |
| `+0x14` | u32 | **relocated pointer** (SITE B/H) → payload band | CONFIRMED |

**Bit3 record — `0x20` bytes** (310 pass1 + 55 pass3; dominant stride `0x20`):
| off | width | meaning | confidence |
|----:|------:|---------|------------|
| `+0x00` | 3×s32 | `vec[3]` coordinate-like (role UNKNOWN) | CONFIRMED shape |
| `+0x0c` | 3×s16 | `angle[3]` → `fcn.80017b98` | CONFIRMED (used) |
| `+0x12` | 3×s16 | `scale[3]` per-axis matrix scale (12.4 fixed; `0x1000`=1.0) | CONFIRMED (used) |
| `+0x18` | u32 | scalar; **not relocated** (flag `0x20` never set in LEVEL01) | CONFIRMED present / role UNKNOWN |
| `+0x1c` | u32 | **relocated pointer** (SITE D/I) → payload band | CONFIRMED |

Gated fields `+0x18`(non-bit3 SITE C) / `+0x20`(bit3 SITE E) require flag `0x20`, which is **never set
in LEVEL01** → they never fire. The flag halfword at the table entry `[s3+0]` selects path: bit3
(`0x8`) chooses the bit3/scaled format; bit5 (`0x20`) the extra pointer; bit7 (`0x80`) a normalize.

## Output-record (`0x20`-byte, in `DATbase+arg2`) layout — pass 1 only (G2)
Built once per pass-1 table entry (both formats produce one). Pass 3 builds **no** output record.
| off | width | meaning | confidence |
|----:|------:|---------|------------|
| `+0x00..+0x11` | 9×int16 | 3×3 rotation matrix from `angle[3]` (bit3: scaled by `scale[3]`) | CONFIRMED |
| `+0x12..+0x17` | 6 B | UNKNOWN (maybe written by `fcn.80017b98`; not decompiled) | UNKNOWN |
| `+0x18` | ptr | → source record `s0` (relocated) | CONFIRMED |
| `+0x1c..+0x1f` | 4 B | UNKNOWN (not written by visible parser code) | UNKNOWN |

Shape resembles a PsyQ `MATRIX` but the `+0x18` source pointer would clobber `MATRIX.t[1]`, so it is
**LIKELY not** a live translation matrix — leave the gaps UNKNOWN until a consumer (G4/G5) is found.

## Address glossary (geometry-relevant)
| symbol / addr | meaning | confidence |
|---|---|---|
| `G_DAT_BASE_PTR` `0x80082498` | loaded DAT base; relocation adds it | CONFIRMED |
| `G_TRAIL_BLOCK_PTR` `0x800824ac` | trailing relocation block ptr (LEVEL01 file `0x1504`) | CONFIRMED |
| `G_PASS2_BASE_PTR` `0x80082338` | pass-2 base (file `0x3ae8`) | CONFIRMED |
| `G_PASS3_BASE_PTR` `0x80082508` | pass-3 base (file `0x3aec`) | CONFIRMED |
| `G_DAT_ENTRY_COUNTER` `0x800822f0` | pass1+pass3 output-record counter | CONFIRMED |
| `0x80091210..` | pass-2 16-bit output table (LEVEL01 empty) | CONFIRMED (mechanism) / UNKNOWN (meaning) |
| `gp+0x5f4` `0x8008238c` | scene-gated size 0x580/0x500/0x600 | CONFIRMED (write) / UNKNOWN (meaning) |
| `gp+0x604` `0x8008239c` | epilogue: `out_end - tail` when tail != -1 | CONFIRMED (write) / UNKNOWN |
| `DATbase + arg2` | pass-1 `0x20`-byte output-record buffer; **arg2 = DAT filesize** → base = end of DAT (LEVEL01 LIKELY `0x801b1c10`) | CONFIRMED rel. |
| `DATbase` | loaded DAT base = caller heap cursor `[sp+0x98]` (LEVEL01 `0x801607f8` LIKELY) | CONFIRMED mechanism |
| `0x8003d568` | the single `jal 0x8001cdc0` call site (in `fcn.8003cf2c`) | CONFIRMED |
| `0x80090fb0` | 3×3 rotation matrix used by `fcn.80025084` containment test | CONFIRMED (used) |
| `fcn.80017b98` | GTE rotation-matrix setup (no relocation) | CONFIRMED |
| `fcn.80025084` | oriented range/containment test (geometry; render-vs-collision UNKNOWN) | CONFIRMED geom / UNKNOWN role |
| `fcn.800224ec` | scene/render driver; reads `G_TRAIL_BLOCK_PTR`/`G_PASS3_BASE_PTR`; calls render loop + GTE helpers | CONFIRMED render driver (G4) |
| `fcn.800140a0`/`80014360`/`800146e0` | GTE transform helpers (MVMVA/SQR) fed the parser geometry by the driver | LIKELY render-stage (G4) |
| `0x1f8003b4` / `0x1f800384` | scratchpad view matrix / view vector staged for the GTE | CONFIRMED (used by driver) |
| `[0x80082440]` (gp+0x6a8) | geometry loop count read by `fcn.800140a0` (NOT `G_DAT_ENTRY_COUNTER`) | CONFIRMED |
| `0x801b3cb0` | G5.5 watched output rec 261 matrix[0]; no read-watch hits observed | CONFIRMED address / UNKNOWN reader |
| `0x801b3cc8` | G5.5 watched output rec 261 source pointer; no read-watch hits observed | CONFIRMED address / UNKNOWN reader |
| `0x8016560a` | G5.5 watched source `s0=0x4e00` scale0; no read-watch hits observed | CONFIRMED address / UNKNOWN reader |
| `0x80161e78` | G7 pass-1 trail entry19 `+0x00` body word (`DAT+0x1680`); runtime watch produced no hit | ZERO-HIT / NOT ELIGIBLE YET |
| `0x80161e84` | G7 pass-1 trail entry19 `+0x0c` body/range halfword (`DAT+0x168c`); runtime watch produced no hit | ZERO-HIT / NOT ELIGIBLE YET |
| `0x80161edc` | G7 pass-1 trail entry24 `+0x00` body word (`DAT+0x16e4`); read near a specific edge-of-level area by `0x8001419c: lw s3,-0x14(a0)` with `a0=0x80161ef0` (runtime `s3=0xfffd126d` ≠ static `0xffffd800`) | CONFIRMED render-stage body-field read / role UNKNOWN; runtime-vs-static mismatch UNKNOWN |
| `0x80161ee0` | G7 Path A pass-1 trail entry24 `+0x04` body word (`DAT+0x16e8`, `b3 f5 ff ff`); read by `0x80014258: lw t1,-0x10(a0)` (non-neg `+0x0c` path); G8 Candidate C `+1024` was CPU-read-confirmed with no obvious visual change | CONFIRMED render-stage body-field read / role UNKNOWN |
| `0x80161ee4` | G7 Path A pass-1 trail entry24 `+0x08` body word (`DAT+0x16ec`, `9f fa ff ff`); read by `0x800141a0: lw s5,-0x0c(a0)`; G8 Candidates A/A2 were CPU-read-confirmed with no obvious visual change | CONFIRMED render-stage body-field read / role UNKNOWN |
| `0x80161ee8` | G7 Path A pass-1 trail entry24 `+0x0c` body halfword (`DAT+0x16f0`, `de 02`=734); read by `0x800141a4: lh t4,-0x08(a0)`; sign selects `+0x04` branch | CONFIRMED render-stage body-field read / role UNKNOWN |
| `0x800901c8` | runtime bitmask table used by `fcn.800140a0` to gate pass-1 trail body reads | CONFIRMED by disasm / runtime values UNKNOWN |
| `LIST_A` `0x80096ea8` | survivor row-pointer list A; written by `fcn.800140a0`/`fcn.80014360`, read by `fcn.8001ea6c`/`fcn.800206e8` | CONFIRMED |
| `LIST_B` `0x8009e338` | survivor row-pointer list B; only written (both producers); consumer UNKNOWN | CONFIRMED write / consumer UNKNOWN |
| `[0x8008240c]` `gp+0x674` | GPU/OT buffer pointer passed to the builders (`+0x0` and `+0x1c4` sub-ranges) | CONFIRMED arg / OT role LIKELY |
| `fcn.8001ea6c` | survivor-list primitive builder #1 (gate `0x10`; jump table `@0x8001a970`, `<0x6d`) | CONFIRMED |
| `fcn.800206e8` | survivor-list primitive builder #2 (OT z-index from `gp+0x5f4`; jump table `<0x4b`; buffer `+0x1c4`) | CONFIRMED |
| `fcn.800146e0` | libgte leaf: load camera rot-matrix + trans vector into GTE (`jr ra@0x8001471c`) — NOT projection | CONFIRMED |
| `fcn.80014844` | separate routine: reads contact array `0x800b0d18`, `>>5` coords, RTPT `@0x80014970` (LIKELY actor/sprite path) | CONFIRMED location / role LIKELY |
| `0x1f800374` | camera/view base subtracted from source `vec[3]` in the builders | CONFIRMED (used) |
| `fcn.80010000` | per-object mesh draw: payload count + vertex table + primitive command stream → RTPS/RTPT/NCLIP → OT | CONFIRMED |
| `0x80060284` / `0x800602b0` | GTE per-point transform helper (32-bit / 16-bit), core `0x800602e0` | CONFIRMED |
| `0x8001036c` | `fcn.80010000` primitive-type jump table (`type=ctrl&0x1f`, 8-byte entries) | CONFIRMED |
| payload `Vertex` | stride `0xc`: `s16 x;y;z; s16 pad=0; u32 attr` (attr LIKELY UV/normal/color) | CONFIRMED shape / attr role LIKELY |
| `0x800108b4` | `fcn.80010000` packet-store gate (`addi s3,s3,0x34`), past all RTPS/RTPT/NCLIP/AVSZ4 rejects; EXEC BP here = emitted-primitive evidence (`a0`=vertex base → payload=`a0−4`; `s3`=GPU packet cursor). **G26: ALWAYS validate `[a0−4]` = plausible count (reject `0x70d4001a`) — the formula is right but unvalidated bases mislead; prefer `EXEC 0x80010000` entry (`a0`=raw payload, `[a0]`=count) for the source-of-truth** | CONFIRMED |
| `0x80010718` | `fcn.80010000` right after `mfc2 SXY0/1/2`; read `t5/t6/t7` = packed screen XY `(Y<<16)|X` (signed halves) — cleaner than `s3` packet for screen coords | CONFIRMED |
| payload `0x356bc` (rt `0x80195eb4`, e128) | G16-edited 230v payload; v10.y deform = **VISIBLE WALL/cliff face render change** → **wall/vertical terrain face** (NOT floor); flat 0.48, local Y band 1354 | CONFIRMED emitted+visible / **wall (CONFIRMED by visual)** |
| payload `0x1b9f0` (rt `0x8017c1e8`, e160) | G17 lead floor candidate; 92v, flat 0.32, tight Y band 573; emitted ≥2 prims in the G16 ground-view log | CONFIRMED emitted / floor-vs-ledge role UNKNOWN |
| payload `0x1f148`/`0x08f4c`/`0x17d94` (e135/e254/e52) | G17 static floor shortlist; flattest wide unique surfaces (flat 0.19/0.22/0.23); NO emitted evidence yet | CONFIRMED metrics / floor role LIKELY |
| payload `0x188cc` = **Candidate A** (rt base `0x801790c4`, vtx base `0x801790c8`) | G27/G28 count-validated DAT-backed floor payload; 83v, flat 0.154, 4502×4502, world-space, unique; runtime-read + projection-confirmed (G28); **G28 visual test: editing v16.y (`DAT 0x18992`, +1024) visibly deformed the floor/terrain in A's projected area (caves inward, angle-dependent), Flik/objects unaffected, collision did not follow** | **CONFIRMED DAT-backed VISUAL floor/top-surface render payload** / walkable + collision/pathing UNKNOWN |
| `0x80020684` / `0x80020694` | emitter payload-ptr load: `lw a0,0x1c(s2)` / `lw a0,0x20(s2)` (NO base add) → `0x80020698 jal fcn.80010000`; gate `gp+0x6a8` loopcount vs `s0` | CONFIRMED |
| `0x801bdc58` (`= LEVEL.RAW+0xa81ac`) | **G26: compressed LEVEL.RAW SOURCE, NOT a floor payload.** Press-X `[0x801bdc58]=0x70d4001a` (= the compressed word); WRITE watch during load = 0 hits. The G17 "floor payload at `0x801bdc58`" claim is RETRACTED (`a0−4` was never count-validated; `0x70d4001a` is an impossible count) | CONFIRMED compressed source / floor payload UNKNOWN |
| `0x801b1c10` / `0x801b5890` / `0x801b6a10` | DAT EOF (=pass-1 output base) / pass-1 `OutputRecord20[484]` end / parser reserved end (heap cursor → next resource) | CONFIRMED (G3) |
| LEVEL01 terrain resources `LEVEL.RAW`/`TERRAIN.ALL`/`TERR1.ALL`/`LEVEL1.DAT` | separately-loaded resources (s16-coord terrain streams etc.) that land in the heap; LIKELY source of the runtime floor payload | CONFIRMED files / role LIKELY |
| `fcn.8003a318` | high-heap loader + LEVEL.RAW **per-chunk decompress LOOP** + chunk-subtype dispatch builder (span `0x8003a318..0x8003c384`) | CONFIRMED (G22/G25) |
| `0x8003a4e4` / `0x8003a4ec` | the single `jal fcn.8001a1dc` call site (looped) / its return `ra` (also the `lw s4,(fp)` chunk-subtype read) | CONFIRMED (G25) |
| `0x8003c29c` / `0x8003c2dc` | LEVEL.RAW chunk loop head (read `s5[0..3]`; `ff ff ff ff`=terminator) / finalize (`[gp+0x4a0]=0x801cc390`, `jal 0x80063508 ×2`) | CONFIRMED (G25) |
| `0x8003c250` / `0x8003c13c` | per-chunk tail `s5 += word1+0xe` (compressed stride) / a per-case `fp += align4(word0)` (decompressed size) | CONFIRMED (G25) |
| LEVEL.RAW chunk header (`word0`@s5[0..3], `word1`@s5[4..7], BE32) | `word0` = decompressed chunk size, `word1` = compressed chunk size, `0xe` = header len; `word0==0xffffffff` = terminator (G24 "dead" words are caller-live) | CONFIRMED (G25) |
| `[gp+0x588]` `0x80082320` (`fp`) | decompressed-output cursor; final `0x8015fcbc` (does NOT reach floor `0x801bdc58`, `+0x5df9c` above) | CONFIRMED (G25) |
| `[gp+0x4a0]` `0x80082238` | high-heap TOP `0x801cc390` (set at finalize); floor `0x801bdc58` = top − `0xe738` | CONFIRMED (G25) |
| `fcn.8003cc58` / `0x800628c0` / `0x800625fc` / `0x80061a48` | LEVEL.RAW chunk builders (consume decompressed chunk `s3`); candidate floor-payload writers | CONFIRMED callees / floor-writer UNKNOWN |

## Open questions (rolling)
1. Roles of records `0x01`/`0x0b`/`0x0c`/`0x0d` and negatives `-2..-7` (G1).
2. Does the pass-1 output buffer hold render transforms, collision transforms, or both? (G3/G4/G5)
3. `s0` source coordinate field located in G2: `vec[3]` (3×s32) at `+0x00` — role still UNKNOWN
   (position-shaped). The deeper geometry payload it/the ptr reaches (`0x8bd8..0x4f32c`) is UNKNOWN (G3).
4. Who reads `DATbase+arg2` and the `out+0x18` source pointers? **Partly answered (G4):** reached via
   `G_TRAIL_BLOCK_PTR` → trailing table → output record, by render driver `fcn.800224ec` → GTE helper
   `fcn.800140a0`. Exact per-field reads still UNKNOWN (G4 open item / G5).
5. Is `fcn.80025084` (matrix `0x80090fb0`) fed by this geometry, and is it render or collision?
   **Answered (G5):** it reads actor/object data (0x800a0a64 / 0x800a6300), **not** the parser geometry;
   render-vs-collision still UNKNOWN but it is out of the geometry-consumer question.
6. Meaning of the pass-2 table `0x80091210..` and the scene-gated sizes (G2/G3).
7. rec10-vs-"EOF" doc reconciliation — **RESOLVED in G1** (rec10 ends `0x1500`; geometry data is post-trailing).
8. Source-record stride/size conflict — **RESOLVED in G2**: two formats, non-bit3 `0x18` (ptr @+0x14),
   bit3 `0x20` (ptr @+0x1c); neither reads out of bounds.
9. Roles of the fixed `3×s32` records (`0x01/0x0b/0x0c/0x0d`) and the packed negative records
   (`-2..-7`): byte shapes known (G1), semantics UNKNOWN.
10. Meaning of non-bit3 `+0x12` and bit3 `+0x18` scalars; payload-band contents (G3).
11. Pass-3 relocated source records have a separate (direct) consumer from pass-1 output records —
    identify both, keep separate (G4/G5).
12. G5.5 Part B fallback confirmed runtime execution of the render-stage helper path, but not a
    specific parser-geometry field read. Retarget to an active/on-camera output record or inspect
    `fcn.800140a0` to compute which table entries are actually read.
13. G7/G8: entry24 body row (`+0x00/+0x04/+0x08/+0x0c`) CONFIRMED read (Path A). G8 A/A2/C small
    same-sign perturbations were valid builds and CPU-read-confirmed but visually imperceptible:
    `+0x08` `+256`, `+0x08` `+1024`, and `+0x04` `+1024` all showed no obvious visual change in the
    tested edge-of-level area. This does not disprove render-body relevance, but continued
    blind/small entry24 perturbations are low-yield. Entry19 `+0x00` and entry19 `+0x0c` remain
    zero-hit / not eligible yet. **Next:** G9 dataflow tracing after the entry24 reads. **OPEN:** is
    entry24's `+0x00` body word runtime-rewritten or state/time-variable at the read site?
14. G9 runtime trace: entry24 `+0x00/+0x04/+0x08` are paired as `(+0x00-t5, +0x04-t6,
    +0x08-t7)`, feed `SQR`/`MVMVA`, and gate output-list membership through reject branches; `+0x0c`
    acts as path/extent term. Runtime stepping CONFIRMED entry24 passes `0x80014280` but rejects at
    `0x800142b0` before the late list-write path in the tested state. The late-write rowbase
    `0x80161f40` was not entry24; it maps to entry29 / DAT row `0x1748`. **Next:** G9b should find
    and map a row that survives to `0x8001430c` or `0x80014320`, then use that surviving row as the
    visual-edit candidate instead of entry24. See `src_re_geometry/geometry_g9_entry24_dataflow.md`.
15. G10 (static + runtime): survivor lists are consumed by `fcn.8001ea6c`/`fcn.800206e8`, which bridge
    `row+0x10`→output record→`+0x18`→source record→`+0x14/+0x1c`→payload `[0x8bd8,0x4f32c]`, read
    source `vec[3]`−camera, and pack primitives into GPU/OT buffer `[0x8008240c]`. **Editable
    visible-geometry targets (use survivor entry29):** source `vec[3]` `@0x7388`, `scale[3]` `@0x739a`,
    `angle[3]` `@0x7394`, payload vertex `@0x2f2f8`. **RESOLVED (2026-06-14):** runtime READ
    `0x80167b80` + EXEC `0x8001eb34` CONFIRMED dispatch to builder case `0x8001ec44`; that case is
    decoded (reads vec/angle/scale/attr/payload-ptr, scales a LUT matrix `@0x80089528` by `scale[3]`,
    tail-calls emitter `fcn.80010000`); scale/angle now CONFIRMED read by the runtime builder.
    **STILL OPEN:** whether READ vs dispatch snapshots are the same iteration (`s2` differs); LIST_B
    consumer. See `src_re_geometry/geometry_g10_payload_render_chain.md` §7.
16. G11 (static): `fcn.80010000` decoded — payload = `{u32 count; Vertex[N] stride 0xc (s16 x,y,z;
    s16 pad; u32 attr); primitive command stream}`; type-0 = triangle (RTPS/RTPT + NCLIP), vertices
    referenced by byte offset; `0x80060284` = GTE per-point transform helper. **Edit targets (entry29):**
    source `vec[3]` `@0x7388`, `scale[3]` `@0x739a`, payload vertex `@0x2f2fc`. **STILL OPEN:** per-type
    operand layout (quad/gouraud/textured cases); `attr`(`vertex+0x8`) meaning; `count<=0` head path.
    See `src_re_geometry/geometry_g11_payload_format.md`.
17. G16/G17 (visual): the `0x800108b4` emit gate picked emit-confirmed payload `0x356bc`; editing v10.y
    produced a **VISIBLE WALL/cliff render change** (NOT floor) → `0x356bc` is **wall/vertical terrain
    face**. Emit-in-ground-view is necessary but **not sufficient** for "floor" (a wall in frame also
    emits). **OPEN (G17):** which payload is the **walkable floor/top surface**? Static floor shortlist
    e135 `0x1f148` (flat 0.19)/e254 `0x08f4c`/e52 `0x17d94`; partial-emit lead `0x1b9f0` (e160, ≥2 prims).
    Method: re-run EXEC `0x800108b4` while framing the floor, capture `a0`+`s3` packet screen-XY (or BP
    `0x80010718` for SXY) to confirm the primitive lands on the floor, then edit a single floor vertex.
    No build until a floor payload is emit-confirmed AND its screen-XY lands on the walkable surface.
    **OPEN (still):** is any visual floor payload coupled to collision? (visual floor ≠ collision floor —
    not inferred). See `src_re_geometry/geometry_g17_floor_payload_candidates.md`.
18. G17 Candidate B / G18 (runtime+static): the emitted walkable-floor payload is at runtime
    `0x801bdc58` (a0=`0x801bdc5c`, all 17 hits one payload) — **past LEVEL.DAT EOF** (`0x801b1c10`) and the
    parser output (`0x801b6a10`), in the "next resource" heap region; `0x5d460` is NOT a valid DAT offset.
    CONFIRMED it is **not** a LEVEL.DAT payload: parser runs once, all reloc targets `<0x4f32c`, emitter
    loads `a0` directly from `[s2+0x1c]/[s2+0x20]` (no base add). LIKELY from a separate terrain resource
    (`LEVEL.RAW`/`TERRAIN.ALL`/`TERR1.ALL`) loaded into the heap. **OPEN:** which resource + which generator
    writes `0x801bdc58`, and is `s2` a DAT source record (payload field runtime-written) or heap-resident?
    **Next:** WRITE watch `0x801bdc58` during load + read `s2` at emitter `0x80020684`. No DAT floor edit
    available (floor not in LEVEL.DAT). Collision UNKNOWN. See
    `src_re_geometry/geometry_g18_output_buffer_floor_trace.md`.
19. G22–G25 (LEVEL.RAW): floor source resource = `LEVEL.RAW` (G22), which is **compressed** (G23) and decompressed
    by `fcn.8001a1dc` (G24, grammar PARTIAL). **G25:** the decompressor runs in a **per-chunk loop** in
    `fcn.8003a318`; `word0`/`word1` = per-chunk decompressed/compressed sizes (caller-consumed). *(The G22–G25
    LEVEL.RAW loading/decompression RE stands; see Q20 for the G26 correction of the "floor at `0x801bdc58`"
    premise.)* See `src_re_geometry/geometry_g25_level_raw_post_decompress_trace.md`.
20. **G26 (CORRECTION/PIVOT):** `0x801bdc58` is **compressed LEVEL.RAW source** (`= LEVEL.RAW+0xa81ac`), **NOT** a
    floor render payload — proven by operator ground truth: Press-X `[0x801bdc58]=0x70d4001a` (the compressed word)
    and WRITE watch during load = **0 hits** (never written). This **retracts** the floor-at-`0x801bdc58` premise
    that runs through Q17/Q18/Q19 (G17 Candidate B → G18 → G22 → G25 "built post-decompression near `0x801bdc58`").
    Re-audit: the `fcn.80010000` `a0−4` payload-base formula is correct (a0 = vertex base, never rewritten in the
    count>0 path), but the G17 hits were never **count-validated** (`0x70d4001a` is an impossible count). **OPEN:**
    the actual walkable-floor render payload pointer (UNKNOWN); whether it is DAT-backed (re-test e135 `0x1f148`/
    e254 `0x08f4c`/e52 `0x17d94`), LEVEL.RAW-decompressed, or generated. **Next (count-validated, consumer side):**
    PRIMARY EXEC `0x80010000` (`a0`=payload base, validate `[a0]`=count, dump `0x40` bytes, record `ra`); SECONDARY
    EXEC `0x800108b4` (`payload=a0−4`, cross-check count, `s3` packet screen-XY / `0x80010718` SXY → floor =
    lower-center). No patch/build. Collision/pathing UNKNOWN. See
    `src_re_geometry/geometry_g26_floor_payload_reaudit.md`.
21. **G27/G28 (count-validated floor + visual confirmation):** the floor-view `EXEC 0x80010000` capture surfaced
    five count-validated DAT-backed payloads (A–E); **Candidate A** (`DAT 0x188cc`, rt `0x801790c4`, 83v, flat
    0.154) is the strongest floor/top-surface. G28 confirmed A is runtime-read + projection-path active, then the
    built same-size edit (v16 `y` @`DAT 0x18992`, +1024) was **operator-tested → VISIBLE terrain deformation** in
    A's projected area (caves inward, angle-dependent), Flik/objects unaffected, **collision did NOT follow**. So
    **Candidate A = CONFIRMED DAT-backed VISUAL terrain/floor render payload** (not decor); **visual terrain
    payload ≠ collision/pathing source**. **OPEN (G29):** the **collision/pathing source** for this floor surface
    is UNKNOWN — do not assume it is in Candidate A, LEVEL.DAT, or LEVEL.RAW without new evidence; find it with
    runtime collision probes / movement-height (floor-contact) reads, not the visual render path. (Secondary
    option: controlled visual terrain sculpting within Candidate A, if the goal is more render-geometry editing.)
    See `src_re_geometry/geometry_g28_candidate_a_runtime_confirmation.md`. Collision/pathing UNKNOWN.

## Do-not / guardrails
- No DAT/BIN/CUE patching; no ISO build; no edits to `src_re/` pickup files; no new whole-game
  decompilation. See `docs/GEOMETRY_RE_PLAN.md` §1.
