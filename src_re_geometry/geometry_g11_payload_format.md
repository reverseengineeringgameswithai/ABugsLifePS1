# G11 — payload vertex format and primitive emission (`fcn.80010000`)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G10 chain: geometry_g10_payload_render_chain.md](geometry_g10_payload_render_chain.md)

Status: **STATIC ISO ANALYSIS (2026-06-14).** Read-only `SCUS_942.88` disasm (`.text` @`0x80010000`,
file off `0x800`) + read-only DAT byte trace. **No patch, no build, no patch scripts, no committed
binary/RAM/save-state. No collision/pathing claims.**

Goal: decode the payload reached by `[source+0x1c]` (the data the G10 builder case `0x8001ec44`
tail-passes to `fcn.80010000`), so the actual editable visible-geometry fields are known.

---

## 1. `fcn.80010000` — per-object mesh draw routine (CONFIRMED)

Reached as: G10 builder case `0x8001ec44` → `j 0x80020698` → `jal 0x80010000`.

| arg | value | meaning | conf |
|-----|-------|---------|------|
| `a0` | `[source+0x1c]` | **payload pointer** (band `0x8bd8..0x4f32c`) | CONFIRMED |
| `a1` | `0x190` or `0x8000` (from `source[+0x19]&0xc0`) | base OT depth / size flag | CONFIRMED read / role LIKELY |
| `a2` | `(source[+0x18]&0xff)<<3` | base color/code selector | CONFIRMED read / role LIKELY |
| `a3` | `0x1f800384` | view context; `[a3+0xc]=0x1f800390` = OT z-index | CONFIRMED |

Flow (CONFIRMED from disasm):

1. `lw t7,(a0)` = payload **count word**; `addi a0,a0,4` → `a0` = vertex-table base (`payload+4`).
   `s7 = 0x1f800000` (PS1 scratchpad); saves `[0x1f800390]` OT-z to `scratch+0x6c`.
2. `bgtz t7,0x8001024c`: `count>0` path sets `s0 = (payload+4) + count*0xc` (skip the vertex table →
   `s0` = start of the **primitive command stream**). The `count<=0` path runs an alternate 3-point
   GTE setup via `0x80060284` (role LIKELY a degenerate/sprite form; exact trigger UNKNOWN).
3. Sets up code/color tables (`0x800a3390+a2*4`, `0x80091...`, etc.) and clears a primitive scratch ring.
4. **Command-stream loop** at `0x800102d0`:
   - `lh t0,(s0)` = control halfword; `bltz t0` ⇒ end of stream.
   - `type = t0 & 0x1f` → `jr (0x8001036c + type*8)` (jump table; 8-byte `j`+delay entries).
   - `t0 & 0x60` and `t0>>7` select shading/texture/color variant (drive code tables at
     `0x800894e8`, `0x80091...`, `0x800a7dd8`).
   - each case reads its vertex **byte-offsets** from `[s0+2..]`, adds `a0`, `lwc2` the coords into
     the GTE, projects, and packs a GPU polygon; then advances `s0` and loops.

Jump table `@0x8001036c` (types 0–7 shown; pattern repeats in 4s → ~4 base primitive kinds × variant):

| type | target | type | target |
|-----:|--------|-----:|--------|
| 0 | `0x8001046c` | 4 | `0x8001068c` |
| 1 | `0x80010adc` | 5 | `0x80010adc` |
| 2 | `0x800108c8` | 6 | `0x800108c8` |
| 3 | `0x80010c90` | 7 | `0x80010c90` |

### Type-0 case `0x8001046c` (CONFIRMED triangle)
- `lh t1,2(s0)`, `lh t2,4(s0)`, `lh t3,6(s0)` = three vertex **byte-offsets**; `+a0` → vertex addrs.
- `lwc2 0,(t1)` / `lwc2 1,4(t1)` … load each vertex's first 8 bytes (x,y,z) into the GTE.
- GTE `RTPS` (`0x4a180001` @`0x80010488`) and `RTPT` (`0x4a280030` @`0x800104d8`) = perspective
  projection of the points; `NCLIP` (`0x4b400006` @`0x800104fc`) = backface cull (cross-product sign);
  `mfc2` reads screen XY; `sltiu …,0x200` / `sltu …,0xf00000` = screen/`Z` clip-reject.
- On accept, packs a polygon primitive into the OT/primitive buffer. So type 0 = **a triangle** drawn
  from 3 indexed vertices. CONFIRMED.

Other type cases (`0x80010adc`, `0x800108c8`, `0x80010c90`, `0x8001068c`, and the larger targets
`0x80011xxx..0x80012xxx`) are the quad / gouraud / textured / strip variants (LIKELY POLY_F3/FT3/G3/GT3
/F4/FT4 family); exact per-type operand counts = TODO.

---

## 2. `0x80060284` — GTE per-point transform helper (CONFIRMED)

Not libgpu. Two entry points sharing core `0x800602e0`:

| entry | args | body |
|-------|------|------|
| `0x80060284` | `a0`=src vec (3×s32), `a1`=dst | `lw t0/t1/t2,(a0)` → `0x800602e0` → `sw …,(a1)` |
| `0x800602b0` | `a0`=src vec (3×s16), `a1`=dst | `lh …` → `0x800602e0` → `sh …,(a1)` |
| `0x800602e0` | (core) | `mtc2 t0/t1/t2` (load vector) → GTE matrix op → `mfc2 t3/t4/t5` → `t3+t4+t5` → `mtc2 v0` |

So `0x80060284` loads a 3-vector into the GTE, runs the loaded model/rotation matrix transform, and
returns the transformed components (32-bit or 16-bit). It is the **per-point coordinate transform**
used by `fcn.80010000`'s setup. CONFIRMED GTE transform helper; exact GTE op LIKELY a matrix×vector.

---

## 3. Payload layout (CONFIRMED)

```
struct Payload {                                   // reached via source-record +0x1c
  +0x00  u32   vertexCount;                         // N  (CONFIRMED)
  +0x04  Vertex verts[N];                           // stride 0xc (CONFIRMED)
  ...    PrimCmd stream[];                           // starts at +4 + N*0xc (CONFIRMED)
};                                                  // (count<=0 takes an alternate head path)

struct Vertex {            // 0xc bytes (CONFIRMED stride + x,y,z,pad)
  +0x00  s16  x;           // CONFIRMED signed coord (small, local to object)
  +0x02  s16  y;           // CONFIRMED
  +0x04  s16  z;           // CONFIRMED
  +0x06  s16  pad;         // CONFIRMED = 0 in all sampled vertices
  +0x08  u32  attr;        // CONFIRMED present; read by cases (lw +8) — LIKELY UV/normal/color
};

// PrimCmd: control halfword + operands (CONFIRMED for type 0)
//   u16 control;          // type = control & 0x1f -> jumptable @0x8001036c
//                         // control & 0x60, control>>7 = shading/texture/color codes
//   u16 vtxByteOffset[k]; // k=3 for the type-0 triangle ([s0+2/+4/+6]); BYTE offsets (multiples of 0xc) into verts[]
//   [+ optional inline UV/color depending on type]   // LIKELY; per-type layout TODO
//   stream terminates when control < 0 (bltz t0)      // CONFIRMED
```

- The GTE loads vertex bytes `+0/+4` (`lwc2`), i.e. x,y in word0 and z,pad in word1 → only x/y/z are
  the geometric coordinate; `+8 attr` is a separate per-vertex field.
- Primitives reference vertices by **byte offset** (`0,0xc,0x18,…`), not index. CONFIRMED.

---

## 4. Concrete LEVEL01 decode (entry29, the G9 survivor) — CONFIRMED bytes

Bridge: pass-1 entry29 row `DAT 0x1748` → source `[row+0x10]` = `DAT 0x7388` → payload `[src+0x1c]` =
`DAT 0x2f2f8` (runtime `0x8018faf0`).

```
payload @0x2f2f8:  count = 34 (0x22)
vertex table @0x2f2fc, stride 0xc:
  v0  = (x=0,   y=-744, z=-61 )  pad=0  attr=0x00088064
  v1  = (x=0,   y=-985, z=-133)  pad=0  attr=0x000c885c
  v2  = (x=-50, y=-986, z=-120)  pad=0  attr=0x00086850
  v3  = (x=-53, y=-747, z=-49 )  pad=0  attr=...
  v4  = (x=54,  y=-745, z=-47 )  ...
  v5  = (x=51,  y=-988, z=-121)  ...
command stream @0x2f494:
  ctrl=0x0262 (type 2) ; then offsets 0x0000,0x000c,0x0018,0x0024 = verts 0,1,2,3 ...
```

entry0 cross-check (`DAT 0x4680` src → payload `DAT 0xb32c`): count `195`; v0=(1835,2349,5451) pad=0;
first primitive ctrl=`0x0060` (type 0) offsets `0x0030,0x0000,0x000c` = a triangle of verts 4,0,1.
CONFIRMED the same layout for a non-bit3 object.

**Instanced-decor cross-check — payload `0x2d460`** (the DAT-backed payload emit-confirmed in the G18
Candidate B-like floor-ish view; runtime `0x8018dc58`): count `25`, footprint X`[-103,99]`(202) /
Y`[-107,0]`(107) / Z`[-97,97]`(194), flatness 0.53; first command `ctrl=0x0060` (type 0, shade 3) +
element count `0x000e`=14, verts 0,1,2,3,…; all 25 verts referenced (2–5× each). It is reached via the
**bit3** source field `[src+0x1c]` and **93 distinct pass-1 source records share it** → a small closed
blob **instanced ×93** = decor/prop, **not** the walkable floor (see
[geometry_g18_dat_backed_floor_candidate.md](geometry_g18_dat_backed_floor_candidate.md)). This is the
clearest in-DAT example that **one payload + many source records = instanced decoration** (high reference
count is the decor tell, per G15).

DAT offsets for editing entry29 vertex 0 coordinate:

| field | DAT offset | runtime | bytes (pristine) |
|-------|-----------:|---------|------------------|
| v0.x (s16) | `0x2f2fc` | `0x8018faf4` | `00 00` |
| v0.y (s16) | `0x2f2fe` | `0x8018faf6` | `18 fd` (`-744`) |
| v0.z (s16) | `0x2f300` | `0x8018faf8` | `c3 ff` (`-61`) |

---

## 5. Recommended first real visual-geometry edit target (PROPOSAL ONLY — no patch)

Object must survive culling → use **entry29** (the G9 survivor). Ranked:

| # | target | DAT off | why visible | risk | UNKNOWN |
|--:|--------|--------:|-------------|------|---------|
| 1 (recommended) | source `vec[3]` (object origin) | `0x7388` (3×s32) | case `0x8001ec44` subtracts it from camera → translates the *whole* drawn object; CONFIRMED consumed; runtime READ-confirmed | low — single 3×s32, no topology change, reversible | none material |
| 2 | source `scale[3]` | `0x739a` (3×s16, `0x1000`=1.0) | case scales the model matrix → resizes the whole object; most dramatic | a large value could explode/invert the mesh; keep small | exact axis mapping |
| 3 | payload **vertex** coord | `0x2f2fc` v0.x (or `0x2f2fe`/`0x2f300`) | moves one mesh vertex; the truest mesh deformation | subtle (1 of 34 verts); must not touch `pad`/`attr`; pick a clearly-visible vertex | which vertex is most on-screen |
| 4 | source `angle[3]` / matrix idx | `0x7394` / `0x73a1` | rotates the object via the LUT matrix | rotation may be hard to read on a small object | LUT entry meaning |

**Recommended first edit:** **#1 source `vec[3]` @`0x7388`** — biggest, cleanest, lowest-risk visible
change (translate the whole object), single reversible 3×s32 write, CONFIRMED + runtime-confirmed
consumed. **#3 (vertex)** is the definitive "mesh edit" proof once #1 validates the pipeline.

Do **not** infer collision/pathing from any edit; only render consumption is evidenced.

### 5.1 G12 Candidate VEC — RESULT: VALID BUILD / PATCH LIVE / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE (2026-06-14)

Candidate #1 (source `vec[0]`) built as a test image. Why `vec[0]` and `+1024`: it is the lateral
(X-like) component; entry29's payload mesh spans only ~±54 on X, so `+1024` is an unmistakable lateral
translation of the whole drawn object — chosen to avoid the "too subtle" silent results of G8. Culling
is decided by the (unchanged) trail-row body vec, **not** this source vec, so the edit cannot drop the
object from the visibility list; it only changes where it is DRAWN. Single-byte, reversible.

| item | value |
|------|-------|
| field | pass-1 entry29 source record `vec[0]` |
| DAT offset | `0x7388` (runtime `0x80167b80`) |
| original | `f0 d8 ff ff` = `-10000` |
| patched | `f0 dc ff ff` = `-8976` (delta `+1024`) |
| revert | `f0 d8 ff ff` |
| changed bytes vs pristine | exactly one byte, `0x7389` (`d8→dc`) |
| patch cmd | `python3 tools/patch_g12_entry29_source_vec_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G12_ENTRY29_VEC_TEST.DAT` |
| patched DAT | `DAT/LEVEL01_LEVEL_G12_ENTRY29_VEC_TEST.DAT` |
| patched DAT SHA256 | `f01c2a0a90139217629994d1641faf7642cd32b53738f27061d2a0654f3f20ca` |
| patched DAT SHA1 | `67b18e1a56d6893cb3cf5503459b43e111770566` |
| rebuild cmd | `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G12_ENTRY29_VEC_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G12_ENTRY29_VEC_TEST.bin --out-cue ABL_G12_ENTRY29_VEC_TEST.cue --report DAT/LEVEL01_LEVEL_G12_ENTRY29_VEC_TEST_REBUILD.md --write` |
| image | `ABL_G12_ENTRY29_VEC_TEST.cue` / `.bin` |
| embedded verify | LBA `2906`, size `332824`, embedded sha1 `67b18e1a…` == patched DAT (PASSED); `@0x7388` reads `f0 dc ff ff` |
| staged restore | `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine (`786b7a96…` / sha1 `b376cb50…`) |
| artifacts | DAT/BIN/CUE/report gitignored, NOT committed |

**Operator test steps:**
1. Boot `ABL_G12_ENTRY29_VEC_TEST.cue`.
2. Enter LEVEL01.
3. Move to the same edge-of-level / view-location area where the entry29 source reads triggered
   (where `READ 0x80167b80` and case `0x8001ec44` previously fired).
4. Compare against the pristine image at the same camera/location.
5. Look for: whole-object/chunk lateral translation; a terrain/mesh chunk displaced; the object
   clipping/partially leaving view; no visible change; or crash/black screen.
6. Do **not** infer collision/pathing from this test.

Optional CPU confirmation: `READ 0x80167b80` → expect a hit in `fcn.8001ea6c` / case `0x8001ec44`
region; confirm live memory `0x80167b80` reads `f0 dc ff ff` (`-8976`), matching the patch.

**RESULT (operator, 2026-06-14): VALID BUILD / PATCH LIVE / CPU READ CONFIRMED / NO OBVIOUS VISUAL
CHANGE.**
- Boots, LEVEL01 loads, no crash, no black screen.
- CPU read CONFIRMED: `READ 0x80167b80` hit (count 1), PC shown `0x8001ec48`, triggering read
  `0x8001ec44 lw v0,(s2)`, `s2=0x80167b80` → in `fcn.8001ea6c` / case `0x8001ec44`.
- Live-memory proof: DuckStation memory `0x80167b80` = `FFFFDCF0` → bytes `f0 dc ff ff` → s32 `-8976`,
  matching the patch.
- Visual: compared to pristine in the same entry29 / edge-of-level trigger area — no obvious lateral
  shift, mesh movement, clipping change, or visible geometry change.

**Interpretation (do not overstate):** the patched source vector is genuinely live and read by
builder-side code, but the source-origin translation is visually silent in the tested view. This does
**not** disprove the G11 payload path. It means a whole-object origin nudge is not a reliable visible
probe here (LIKELY masked by the object's apparent size/distance/orientation in view, or the entry29
draw uses the `count<=0` path / an unmodeled transform term). **Next is NOT another source `vec[0]`
delta** — move to a direct payload-vertex deformation (§5.2). Collision/pathing **UNKNOWN**.

### 5.2 G13 Candidate PV0 — entry29 payload vertex-0 deformation — RESULT: VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL CHANGE (2026-06-14)

**Why a payload vertex edit is now preferred:** it is a **direct mesh-data deformation** — it changes
the vertex geometry itself rather than relying on whole-object transform behavior, so it bypasses the
G12 ambiguity around source-origin translation. It should affect the specific triangle(s) that use the
vertex (entry29 vertex 0, byte offset `0x0000`, is referenced by the first primitive command), rather
than depending on the object's overall placement being noticeable.

**Axis/delta choice:** across entry29's 34 vertices, X spread = 119, **Y spread = 1769** (dominant,
LIKELY vertical), Z spread = 821. `y` is the most-recognizable single-vertex displacement; `+512` is
~29% of the object's Y extent → a clearly visible vertical spike, well within s16 range. (Fallback if
`+512` over-distorts/clips: `+256` → `-488`.)

| item | value |
|------|-------|
| field | entry29 payload **vertex 0, `y`** (`s16`) |
| DAT offset | `0x2f2fe` (runtime `0x8018faf6`; payload `0x2f2f8` + 4 + vtx0 + 2) |
| original | `18 fd` = `-744` |
| patched | `18 ff` = `-232` (delta `+512`) |
| revert | `18 fd` |
| changed bytes vs pristine | exactly one byte, `0x2f2ff` (`fd→ff`) |
| patch cmd | `python3 tools/patch_g13_entry29_payload_v0_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G13_ENTRY29_PAYLOAD_V0_TEST.DAT` |
| patched DAT | `DAT/LEVEL01_LEVEL_G13_ENTRY29_PAYLOAD_V0_TEST.DAT` |
| patched DAT SHA256 | `a6acffc33287637f5c228321e4dd94509c4c347f255d7743756dafce4c7505cf` |
| patched DAT SHA1 | `b6eecbab2fc37a9b0f8082fa096ca969e4ceafdc` |
| rebuild cmd | `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G13_ENTRY29_PAYLOAD_V0_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G13_ENTRY29_PAYLOAD_V0_TEST.bin --out-cue ABL_G13_ENTRY29_PAYLOAD_V0_TEST.cue --report DAT/LEVEL01_LEVEL_G13_ENTRY29_PAYLOAD_V0_TEST_REBUILD.md --write` |
| image | `ABL_G13_ENTRY29_PAYLOAD_V0_TEST.cue` / `.bin` |
| embedded verify | LBA `2906`, embedded sha1 `b6eecbab…` == patched DAT (PASSED); `@0x2f2fe` reads `18 ff` |
| staged restore | `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine (`786b7a96…`) |
| artifacts | DAT/BIN/CUE/report gitignored, NOT committed |

**Operator test steps:**
1. Boot `ABL_G13_ENTRY29_PAYLOAD_V0_TEST.cue`.
2. Enter LEVEL01.
3. Move to the same edge-of-level / view-location area where entry29's source reads triggered.
4. Compare against pristine at the same camera/location.
5. Look for: one vertex/corner of a terrain/mesh chunk spiking/displaced; a single triangle stretched;
   no visible change; or crash/black screen.
6. Do **not** infer collision/pathing from this test.

**RESULT (operator, 2026-06-14): VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL
CHANGE.**
- Boots, LEVEL01 loads, no crash, no black screen.
- **Watch-address lesson (CONFIRMED):** the initial READ watch on the *inner s16* address `0x8018faf6`
  did NOT hit after ~5 min — because the vertex is loaded by a **32-bit `lwc2`** at the vertex *base*,
  not by a halfword load at the `y` offset. Re-watching the **aligned vertex base** `0x8018faf4` hit
  immediately. **Rule: watch the vertex base / aligned `lwc2` load address (`payload+4 + idx*0xc`,
  and `+4` for the z/pad word), not the inner s16 coordinate address.**
- Vertex read CONFIRMED: `READ 0x8018faf4` hit (count 1), PC shown `0x80010928`
  (`lwc2 v2_z,0x4(t0)`), addr `0x8018faf8`, `t0=a0=0x8018faf4`, `a2=0x801cc554`, `a3=0x1f800384` →
  inside `fcn.80010000` vertex/GTE projection path (the second word `+4` of v0 was being loaded when it
  broke; the first word at `0x8018faf4` had just been read). So the edited v0 IS read by the emitter.
- Visual: compared to pristine in the same entry29 / edge-of-level area — no obvious vertex spike,
  triangle stretch, clipping change, or visible geometry change by eye. (Caveat: screenshots taken
  while a CPU breakpoint is hit show partially-rendered frames and are unreliable; compare with
  breakpoints disabled and gameplay running.)

**Interpretation (do not overstate):** the payload vertex is live and read by `fcn.80010000`, but
moving **v0.y by +512** is visually silent in the tested view. v0 is a mid-body vertex referenced by
relatively few primitives, and `+512` (toward 0 = downward, into the body) is a small inward nudge.
Does **not** disprove the payload path. **Next: pick a vertex by command-stream reference + silhouette
analysis and use a larger delta (G14, §5.3)** — not another guess.

### 5.3 G14 Candidate PV14 — entry29 referenced near-apex vertex — RESULT: VISIBLE RENDER CHANGE / NON-TANGIBLE DECORATION (2026-06-14)

**Command-stream analysis (CONFIRMED).** entry29 command stream spans `DAT 0x2f494..0x2f59c`
(264 bytes), terminated by `ffff ffff` at `0x2f598` (boundary = next payload `0x2f59c`). Decoded first
primitives:

| cmd off | ctrl | type | s2 (strip elems) | vertex byte-offsets → indices |
|--------:|------|-----:|-----------------:|-------------------------------|
| `0x2f494` | `0x0262` | 2 (quad strip) | 3 | `0/0xc/0x18/0x24`→v0,1,2,3 · `0x30..0x54`→v4,5,6,7 · `0x60..0x84`→v8,9,10,11 |
| `0x2f4c8` | `0x8263` | 3 (tri, textured) | 2 | `0x90/0x9c/0xa8`→v12,13,14 · `0xcc`→v17 … |
| `0x2f4e4` | `0x8266` | … | … | (further textured strips; per-type element grammar varies) |

A robust **halfword scan** of the whole stream for valid vertex byte-offsets (`h%0xc==0`, `<0x198`)
gives the reference histogram: **all 34 vertices are referenced; 28 of them exactly twice; 6 once**
(v13,16,20,21,29,30). Total 62 references. So reference frequency alone barely discriminates — the
deciding factor is silhouette/visual distinctiveness combined with multi-triangle sharing.

**Target chosen: vertex 14** (`DAT 0x2f3a4`, `(x,y,z)=(-20,-1601,-579)`). Rationale:
- **refs=2** → a single coord edit deforms 2 triangles. (Avoids the refs=1 apex tips v13/v16, whose
  lone triangle could be backface-culled/occluded → silent, the G13 failure mode.)
- **Near-apex / silhouette extremity:** the mesh is tall/narrow (Y `0..-1769`, X only `±60`); v14 sits
  in the top cluster (apex tip y=-1769; v14 y=-1601), so a vertical displacement breaks the silhouette.
- This is the command-stream-justified upgrade over G13's mid-body, lightly-referenced v0.

| item | value |
|------|-------|
| field | entry29 payload **vertex 14, `y`** (`s16`) |
| DAT offset | `0x2f3a6` (runtime `0x8018fb9e`; vertex base `0x8018fb9c`) |
| original | `bf f9` = `-1601` |
| patched | `bf f5` = `-2625` (delta `-1024`) |
| revert | `bf f9` |
| changed bytes vs pristine | exactly one byte, `0x2f3a7` (`f9→f5`) |
| patch cmd | `python3 tools/patch_g14_entry29_payload_vertex_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.DAT` |
| patched DAT | `DAT/LEVEL01_LEVEL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.DAT` |
| patched DAT SHA256 | `0db535ebf0c879cba8fb704e02e3176418f699ecfcce736bd73363a19558c81c` |
| patched DAT SHA1 | `53608e21ed2e74ef4e5c5057c55832c58ebf5dd9` |
| rebuild cmd | `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.bin --out-cue ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.cue --report DAT/LEVEL01_LEVEL_G14_ENTRY29_PAYLOAD_VERTEX_TEST_REBUILD.md --write` |
| image | `ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.cue` / `.bin` |
| embedded verify | LBA `2906`, embedded sha1 `53608e21…` == patched DAT (PASSED); `@0x2f3a6` reads `bf f5` |
| staged restore | `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine (`786b7a96…`) |
| artifacts | DAT/BIN/CUE/report gitignored, NOT committed |

**Delta:** `-1024` pushes v14.y from `-1601` to `-2625` (further negative = upward), ~58% of the
object's Y extent and well above the apex cluster (`~-1769`) → expected: a sharp spike at the top of
the entry29 chunk affecting two triangles. Larger than G13's `+512` to overcome the prior silence.

**Operator test steps:**
1. Boot `ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.cue`.
2. Enter LEVEL01.
3. Move to the same edge-of-level / view-location area where entry29's reads triggered.
4. Compare against pristine at the same camera/location, **with CPU breakpoints disabled** (gameplay
   running normally — breakpoint-frame screenshots are unreliable for visual comparison).
5. Look for: a spike/peak at the top of a terrain/mesh chunk; two triangles stretched upward; clipping;
   no visible change; or crash/black screen.
6. Do **not** infer collision/pathing from this test.

Optional CPU confirmation (use the **aligned vertex base**, per the G13 lesson): READ watch
`0x8018fb9c` (v14 base) should hit in `fcn.80010000` near the `lwc2` loads; live memory `0x8018fb9e`
should read `bf f5` (`-2625`).

**RESULT (operator, 2026-06-14): VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / VISIBLE RENDER
CHANGE / NON-TANGIBLE DECORATION.**
- Boots, LEVEL01 loads, no crash, no black screen.
- **A visible geometry deformation finally appeared** — the first confirmed visible payload-vertex
  edit. The affected object is **grass / decorative foliage**, and that geometry is **not tangible** in
  gameplay.
- **CONFIRMED:** payload vertex-coordinate edits can visibly deform LEVEL01 render geometry; the
  G10→G11 payload model and the `fcn.80010000` vertex emitter are validated end-to-end (DAT byte →
  on-screen vertex). entry29 payload `DAT 0x2f2f8` is **grass/decor (LIKELY)**, not tangible ground.
- **Method proven, target weak:** this validates the payload-edit method but identifies entry29 as a
  **poor target for tangible-terrain work**. Stop editing entry29.
- **UNKNOWN:** tangible terrain/collision source; whether any visual terrain payload is coupled to
  collision; collision/pathing data source. **Do not infer collision/pathing** from this render edit.

**Next: pivot to a terrain/ground payload (G15).** See
[`geometry_g15_terrain_payload_candidates.md`](geometry_g15_terrain_payload_candidates.md): a static
wide+flat survey shortlists candidates (e213/e128/e280/…), and the recommended next experiment is a
**runtime payload-pointer log at `fcn.80010000`** to identify the actually-drawn ground before editing.

---

## 6. Open items / next

- TODO: per-type operand layout for the non-triangle cases (quad/gouraud/textured); whether `attr`
  (`vertex+0x8`) is UV, packed normal, or color (decode the case bodies' use of `lw +8`).
- TODO: the `count<=0` alternate head path (3-point form).
- Static fully closes the edit-target question; **no runtime watch is required** for G11. (If a later
  build test shows no change, the narrow fallback is a write-watch on the OT buffer during
  `fcn.80010000` to confirm entry29's primitive is emitted on-screen.)
- **G15 (2026-06-14):** pivoted off entry29 grass to a **runtime-confirmed terrain/ground** payload.
  An EXEC `0x80010000` `a0`-log identified `0x80170978` (DAT `0x10180`) as a wide+flat unique ground
  surface; Candidate TERRAIN-PV deformed its vertex 46 `y` (`DAT 0x103ae`, `-1024`). RESULT: VALID BUILD
  / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL CHANGE (the watch fired at the `lwc2` load,
  before the reject tests → vertex read but primitive not proven drawn). Lesson: runtime `a0` frequency
  discriminates instanced decor (high freq) from unique terrain (single hit), and **read ≠ visible**.
- **G16 (2026-06-14):** decoded `fcn.80010000` project→reject→pack and found the screen-space capture
  point — execute BP at `0x800108b4` (packet store, past all RTPS/RTPT/NCLIP/AVSZ4 rejects), read `a0`
  + packet screen-XY at `s3`. The log picked emit-confirmed payload `0x356bc` (e128); editing its v10.y
  produced a **VISIBLE WALL RENDER CHANGE** — the deformed surface is a **vertical wall/cliff face, not
  the walkable floor**, so `0x356bc` is **reclassified wall/vertical terrain face**. First terrain-family
  visible deform (G14 was grass). Lesson: emit-in-the-ground-view is necessary but **not sufficient** to
  mean "floor" — a wall in frame also emits. See
  [geometry_g16_screen_space_vertex_selection.md](geometry_g16_screen_space_vertex_selection.md).
- **G17 (PLANNED 2026-06-14):** find a **walkable floor/top-surface** payload (flat shape + tight local Y
  band + primitive screen-XY on the floor) with emitted evidence, not bbox alone. Static floor shortlist
  e135 `0x1f148` (flat 0.19), e254 `0x08f4c`, e52 `0x17d94`; partial-emit lead `0x1b9f0` (e160). No build
  yet (no floor candidate emit-confirmed as the walkable surface). See
  [geometry_g17_floor_payload_candidates.md](geometry_g17_floor_payload_candidates.md).
  Collision/pathing UNKNOWN — visual floor ≠ collision floor.

## 7. Reproduce (read-only)

```bash
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x80010000 -c 'pD 0x270' SCUS_942.88   # head
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x800102d0 -c 'pD 0xa0'  SCUS_942.88   # cmd loop+dispatch
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8001046c -c 'pD 0xa0'  SCUS_942.88   # type-0 triangle case
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x80060284 -c 'pD 0x90'  SCUS_942.88   # GTE point helper
# payload layout: see §3/§4 byte trace against DAT/LEVEL01_LEVEL.DAT @0x2f2f8 (entry29) / 0xb32c (entry0)
```
