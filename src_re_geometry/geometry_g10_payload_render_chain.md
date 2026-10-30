# G10 — survivor-list consumers and the payload/primitive render chain

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G9 reject trace: geometry_g9_entry24_dataflow.md](geometry_g9_entry24_dataflow.md)

Status: **STATIC ISO ANALYSIS (2026-06-14).** Read-only disassembly of `SCUS_942.88` (`.text` loads at
`0x80010000`, file offset `0x800`) and read-only byte inspection of `DAT/LEVEL01_LEVEL.DAT`. **No DAT
patch, no build, no patch scripts, no committed binary/RAM/save-state artifacts. No collision/pathing
claims.**

Goal: identify how survivor-list entries produced by `fcn.800140a0` become projected/drawn geometry,
and locate the data that should be edited for an actual *visible* geometry change.

---

## 0. Correction of the prior G10 note

The earlier G10 sketch (in `geometry_render_consumers.c`, prior turn) made two attribution errors that
this full decode corrects:

- **`fcn.800146e0` is NOT a projection stage.** It is a tiny libgte inline leaf: load a 3×3 rotation
  matrix from `a0` and a translation vector from `a1` into the GTE control registers (`ctc2`), then
  `jr ra` at `0x8001471c`. The driver calls it to set up the camera matrix *before* drawing. CONFIRMED.
- **The `RTPT` at `0x80014970` is not on the geometry-list path.** It belongs to a different routine
  starting at `0x80014844` that reads the `0x800b0d18` contact array and `>>5`-scales coordinates
  (LIKELY actor/sprite projection — out of the geometry-list scope). CONFIRMED location, role LIKELY.
- **`0x80060484` / `0x800605c4` are libgte matrix-load leaves** (`ctc2` of a 3×3 matrix), **not** libgpu
  primitive submission. CONFIRMED.

The actual survivor-list consumers are **`fcn.8001ea6c`** and **`fcn.800206e8`**.

---

## 1. The confirmed render chain

```
fcn.800224ec  (scene/render driver, per scene)
  ├─ fcn.800146e0(a0=camera_matrix(+0x394), a1=vec)   ; libgte: load camera rot-matrix + trans into GTE   [CONFIRMED]
  ├─ fcn.800140a0(a0=G_TRAIL_BLOCK_PTR, a1=0x1f8003b4, a2=0x1f800384)
  │       ; cull pass-1 trail rows; SQR/MVMVA reject; survivors' (tagged) row pointers -> LIST_A/LIST_B  [CONFIRMED producer]
  ├─ fcn.80014360(a0=G_PASS3_BASE_PTR, ...)            ; pass-3 analog; also writes LIST_A/LIST_B          [LIKELY producer]
  ├─ fcn.8001ea6c(a0=LIST_A, a1=count, a2=[0x8008240c],       a3=0x10)   ; per-survivor primitive builder  [CONFIRMED]
  └─ fcn.800206e8(a0=LIST_A, a1=count, a2=[0x8008240c]+0x1c4)            ; per-survivor primitive builder  [CONFIRMED]
```

`LIST_A = 0x80096ea8`, `LIST_B = 0x8009e338`. Whole-`.text` hi/lo immediate scan found only 8 refs:
`fcn.800140a0` (`0x80014124` LIST_A cursor, `0x80014140` LIST_B cursor), `fcn.80014360` (`0x800143c8`,
`0x80014588` LIST_A; `0x800145a4` LIST_B), and the driver (`0x8002267c` LIST_A → s2, `0x80022688`
LIST_B → s3, `0x800228b0` LIST_A → a0). The two consumers receive LIST_A as `a0`, so they need no
literal ref. **LIST_B is only ever written** (by both producers); its consumer is **UNKNOWN** (TODO).

`[0x8008240c]` = `gp+0x674` (`gp=0x80081d98`) = LIKELY the active GPU primitive/ordering-table buffer
pointer; the two consumers write to base `+0x0` and base `+0x1c4` → LIKELY two OT sub-ranges.

---

## 2. Per-function decode

### `fcn.800146e0` — libgte camera-matrix load leaf (CONFIRMED)
| item | value |
|------|-------|
| caller | `fcn.800224ec` (`0x80022670`, `0x800228a4`) |
| args | `a0` = rotation matrix (driver passes `…+0x394`), `a1` = translation vector |
| body | `lw` 9 matrix words + `ctc2` into GTE; `lw` 3 vec words + `ctc2`; `jr ra` @`0x8001471c` |
| GTE | control-register loads only (no command) |
| role | set camera/view matrix into the GTE before culling+drawing |
| confidence | CONFIRMED |

The block `0x800146e0..0x80014843` is a cluster of PsyQ-style inline GTE leaves (matrix load, MVMVA
apply, mfc2/store). **`0x8001474c`** is the one the consumers call: load a 3-vector (`lwc2`), `MVMVA`
(`0x80014760`), `mfc2`, store to `(a1)` — i.e. "transform a 3-vector by the loaded matrix". CONFIRMED.

### `fcn.8001ea6c` — survivor-list primitive builder #1 (CONFIRMED)
Span `0x8001ea6c..0x800206e0` (`jr ra` @`0x800206e0`).

| item | value | confidence |
|------|-------|------------|
| caller | `fcn.800224ec` @`0x800226a8` | CONFIRMED |
| `a0` | LIST_A base (`fp`) | CONFIRMED |
| `a1` | survivor count (`s7`); loop while `> 0` | CONFIRMED |
| `a2` | `[0x8008240c]` GPU/OT buffer | CONFIRMED |
| `a3` | `0x10` row-flag gate, saved `[sp+0x58]` | CONFIRMED |
| camera base | `s1 = 0x1f800374`; view vec `0x1f800394`; view matrix `0x1f8003b4` | CONFIRMED |
| list walk | `v1 = LIST_A[s5]`; `a1 = v1 & ~1` (clear tag bit); `s5++` | CONFIRMED |
| gate | `(lhu[row+0x0e] & 0x10) == a3(0x10)` else skip row | CONFIRMED |
| **bridge** | `s0 = [row+0x10]` (output record); `s2 = [s0+0x18]` (source record) | CONFIRMED |
| position use | `[s2+0],[s2+4],[s2+8]` (source `vec[3]`) `- camera[0x10/0x14/0x18]` → `[sp+0x20..0x28]` → `jal 0x8001474c` (GTE transform) | CONFIRMED |
| kind dispatch | `v1 = lh[row+0x0e] & 0x9f6f`; if `v1 < 0x6d`: `jr [0x8001a970 + v1*4]` (jump table) | CONFIRMED |
| further source reads | `[s2+0xc]` (angle), `lh[s2+0x10]`, `lbu[s2+0x13]&0x1f` select sub-behavior | CONFIRMED reads / role LIKELY |
| output | ~29 `sh`/`sw` stores building a primitive packet into the `a2` buffer | CONFIRMED stores / packet LIKELY |
| role | per-survivor: bridge to source record, transform position by camera matrix, dispatch by row-kind, pack a GPU primitive | CONFIRMED |

### `fcn.800206e8` — survivor-list primitive builder #2 (CONFIRMED)
Span `0x800206e8..0x800212f4` (`jr ra` @`0x800212f4`).

| item | value | confidence |
|------|-------|------------|
| caller | `fcn.800224ec` @`0x800228c0` | CONFIRMED |
| `a0` | LIST_A base (saved `[sp+0x58]`) | CONFIRMED |
| `a1` | survivor count (`s7`); loop while `> 0` | CONFIRMED |
| `a2` | `[0x8008240c]+0x1c4` GPU/OT sub-buffer (`s6`) | CONFIRMED |
| camera base | `s2 = 0x1f800374`; view matrix `0x1f8003b4` | CONFIRMED |
| list walk | `a0_i = LIST_A[s5]` (no tag-mask shown at head); `s5++` | CONFIRMED |
| OT depth | reads `lh[row+0x0c]` (extent); derives z/OT index from `[gp+0x5f4]` `>>2` → `sw [0x1f800390]` | CONFIRMED math / OT role LIKELY |
| kind dispatch | `v1 = lh[row+0x0e] & 0x9f6f`; if `v1 < 0x4b`: jump table (`lui at,0x8002`) | CONFIRMED |
| also calls | `fcn.80017b98` (GTE matrix setup), `0x8001474c`, libgte leaves `0x80060484/0x800605c4` | CONFIRMED |
| role | second per-survivor builder, different dispatch set (`<0x4b`) and OT sub-buffer; LIKELY z-sorted OT insertion | CONFIRMED builder / OT LIKELY |

Both consumers dispatch on the same row field (`row+0x0e & 0x9f6f`) but with different table sizes
(`0x6d` vs `0x4b`) → two primitive-type families written into two OT sub-ranges. CONFIRMED.

---

## 3. Bridge: survivor row → output record → source record → payload (CONFIRMED)

Each pass-1 trail row is `0x14` bytes at `DAT 0x1504 + N*0x14`:

```
+0x00 s32  body vec[0]   ┐ view-relative cull position (read by fcn.800140a0)
+0x04 s32  body vec[1]   │
+0x08 s32  body vec[2]   ┘
+0x0c s16  extent/range   (cull; also OT-depth input in fcn.800206e8)
+0x0e s16  flag/kind      (loop sentinel; gate bit 0x10; bit3=0x8 format; kind = &0x9f6f)
+0x10 u32  -> output record at runtime   (file: source-record offset; parser SITE A = [s3+2])
```

The parser (`fcn.8001cdc0` pass 1) relocates `[s3+2]` to the source record, builds the `0x20`-byte
output record (rotation matrix + `out+0x18 = source`), then **overwrites `[s3+2] = out`**. So:

| step | runtime | file (pristine DAT) |
|------|---------|---------------------|
| row `+0x10` | → output record (`≈0x801b1c10` band) | source-record file offset (band `0x45f0..0x8bd8`) |
| output `+0x18` | → source record | (n/a; created at load) |
| source `+0x14`(non-bit3) / `+0x1c`(bit3) | → payload | payload file offset (band `0x8bd8..0x4f32c`) |

`fcn.8001ea6c` confirms the runtime form directly: `s0 = [row+0x10]`, `s2 = [s0+0x18]`, then reads the
source `vec[3]`. CONFIRMED.

### Concrete LEVEL01 bridge (byte-traced, pristine DAT)

| entry | rowbase | flag | fmt | source off | source `vec[3]` | scale[3] / unk12 | payload off | payload count word |
|------:|---------|------|-----|-----------:|-----------------|------------------|------------:|--------------------|
| 0  | `0x1504` | `0x0041` | non-bit3 | `0x04680` | `(-8192,-8192,-8192)` | unk12 `-16376` | `0x0b32c` | `0xc3` = 195 |
| 1  | `0x1518` | `0x0041` | non-bit3 | `0x04698` | `(-8192,-8192,-8192)` | unk12 `-16376` | `0x0c6c8` | `0xa6` = 166 |
| 24 | `0x16e4` | `0x4019` | bit3 | `0x05a48` | `(-10440,-2214,-1468)` | scale `(5582,2003,2455)` | `0x2f59c` | `0x12` = 18 |
| 29 | `0x1748` | `0x4019` | bit3 | `0x07388` | `(-10000,-2374,-1099)` | scale `(5220,5220,5220)` | `0x2f2f8` | `0x22` = 34 |

Runtime addresses (DATbase `0x801607f8`): entry29 source `≈0x80167b80`, entry29 payload `≈0x8018faf0`.

### Payload shape (LIKELY)
Leading `u32` count, then an array of vertex-like records: s16 coordinate triples interleaved with
small attribute bytes. Example (entry29 payload `0x2f2f8`):

```
22 00 00 00 | 00 00 18 fd c3 ff 00 00 | 64 80 08 00 | 00 00 27 fc 7b ff 00 00 | ...
count=34    | x=0  y=-744 z=-61  pad   | attr        | x=0  y=-985 z=-133 pad  | ...
```

CONFIRMED: count word + s16 triples. **Fully decoded in G11** (`geometry_g11_payload_format.md`):
`{u32 vertexCount; Vertex verts[N] (stride 0xc: s16 x,y,z; s16 pad=0; u32 attr); primitive command
stream}`. The command stream references vertices by byte-offset and is emitted by `fcn.80010000`
(RTPS/RTPT projection + NCLIP cull). Attribute (`vertex+0x8`) meaning and per-type operand layout =
TODO.

---

## 4. Editable visible-geometry candidates (PROPOSAL ONLY — no patch)

A visible change requires the object to **survive culling** (be on-screen). **entry29** is the
confirmed survivor from G9 (reached the list-write path), so it is the recommended test subject. Do
**not** edit trail body rows (`+0x00..+0x0c`) for mesh changes — those are cull/bounding volumes (G9).

| # | target | DAT location (entry29) | what it should do | consumer evidence | confidence |
|--:|--------|------------------------|-------------------|-------------------|------------|
| 1 | source `vec[3]` (object render origin) | `0x07388` (3×s32) | translate the whole object's drawn position | case `0x8001ec44` reads `[s2+0/4/8] − camera` → GTE transform (runtime READ `0x80167b80` confirmed, §7) | **CONFIRMED consumed as position** |
| 2 | payload vertex coord | `0x2f2f8`+ (after count word; s16 triple) | move one vertex of the mesh | payload ptr `[s2+0x1c]` loaded by case `0x8001ec44`, projected/emitted by `fcn.80010000` (§7.3) | reachable CONFIRMED / mesh LIKELY |
| 3 | source `scale[3]` (bit3) | `0x0739a` (3×s16, `0x1000`=1.0) | resize the object | case `0x8001ec44` reads `[s2+0x12/0x14/0x16]` and scales the model matrix `>>12` (§7.2) | **CONFIRMED read by runtime builder** |
| 4 | source `angle[3]` | `0x07394` (3×s16) | rotate the object | case `0x8001ec44` reads `[s2+0xc/0xe/0x10]` (staged) + matrix LUT via `[s2+0x19]` (§7.2) | **CONFIRMED read by runtime builder** |

Recommended first test (when a build is later authorized): **#1 source `vec[3]`** — a single clean
3×s32 edit at `0x07388`, CONFIRMED read as the object's render position, large expected visual effect,
fully reversible. #3 (scale) is the best "dramatic, unmistakable" alternative. #2 (payload vertex) is
the truest mesh edit but its stride should be decoded first.

Do **not** infer collision/pathing from any of these; only render consumption is evidenced.

---

## 5. Remaining gap and the single narrowest runtime watch — **EXECUTED / CONFIRMED (2026-06-14)**

The recommended watch was run by the operator and **confirmed the source side is consumed** (full
result + the builder-case decode in §7):

> **READ watch on `0x80167b80`** (entry29 source `vec[0]`, `DATbase+0x7388`) → hit at PC shown
> `0x8001ec48` (`lw v1,0x10(s1)`; the triggering read is `0x8001ec44 lw v0,(s2)`, PC = site+4), with
> `a0=0x80096ea8` (LIST_A), `s1=0x1f800374` (camera), `s2=0x80167b80` (entry29 source). **CONFIRMED**:
> the survivor's source `vec[3]` is read by primitive-builder **case `0x8001ec44`** inside
> `fcn.8001ea6c`, and that case is the render path for survivors in the entry29 region.

The new open gap is one level deeper (the packed-primitive format inside `fcn.80010000`); see §7.

---

## 6. Reproduce (read-only)

```bash
# list-base refs (whole .text hi/lo immediate scan) and consumer disasm
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8001ea6c -c 'pD 0x140' SCUS_942.88
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x800206e8 -c 'pD 0xb0'  SCUS_942.88
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x800146e0 -c 'pD 0x80'  SCUS_942.88
# row -> source -> payload bridge: see §3 byte trace against DAT/LEVEL01_LEVEL.DAT
# builder case + emitter:
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8001ec44 -c 'pD 0x2e0' SCUS_942.88
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x80020698 -c 'pD 0x20'  SCUS_942.88
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x80010000 -c 'pD 0xb0'  SCUS_942.88
```

---

## 7. Runtime evidence + static decode of builder case `0x8001ec44` (2026-06-14)

### 7.1 Runtime watches (operator, pristine image, edge-of-level state)

| watch | observed | meaning | confidence |
|-------|----------|---------|------------|
| READ `0x80167b80` | hit ×1, PC shown `0x8001ec48` (`lw v1,0x10(s1)`); `a0=0x80096ea8`, `s1=0x1f800374`, `s2=0x80167b80`, `s3=0x1f8003b4`, `s4=0x1f800394` | the triggering read is `0x8001ec44 lw v0,(s2)` (PC = site+4); `fcn.8001ea6c` builder code reads the survivor source `vec[0]`; LIST_A is the active list (`a0`) | CONFIRMED |
| EXEC `0x8001eb34` (`jr v0`) | hit ×1, `v0=0x8001ec44`; `a0=0x8018faf4`, `a1=0x80161f54`, `a2=0x801cc554`, `s2=0x80168d80` | kind-dispatch selected case target `0x8001ec44` | CONFIRMED |
| step → `0x8001ec44` (`lw v0,(s2)`) | reached; same regs | case body `0x8001ec44` is entered | CONFIRMED |

**Iteration-linkage caveat (UNKNOWN).** The READ snapshot has `s2=0x80167b80` (entry29 source,
`DAT 0x7388`); the dispatch snapshot has `s2=0x80168d80` (`DAT 0x8588`, a *different* valid source
record). So the two snapshots are **different survivor iterations**, both routed through case
`0x8001ec44`. The dispatch `a1=0x80161f54` indexes to pass-1 row `30` by `(a1−G_TRAIL)/0x14`, but
entry30's *file* source pointer is `0x78b8`, not `0x8588`, so `a1` is **not** a clean rowbase for that
iteration — do **not** assert a one-row mapping. The residual `a0=0x8018faf4` = entry29 payload+4 (see
§7.3) is left over from the prior iteration. CONFIRMED: case `0x8001ec44` handles the survivor cluster
around entry29; exact per-iteration row/source linkage between the two snapshots is **UNKNOWN**.

### 7.2 Case `0x8001ec44` decode (`0x8001ec44..0x8001effc`, CONFIRMED)

This is a **bit3/scaled-object transform-setup** case. It reads the bridged **source record** (`s2`),
the **camera** (`s1=0x1f800374`), builds the model matrix into the view scratchpad
(`s1+0x40 = 0x1f8003b4`), then tail-jumps to the shared emitter. (Repeated `mult … ; mflo ; bgez ;
addiu v0,0xfff ; sra v0,0xc` = round-to-`>>12` 12.4-fixed multiplies; rows collapsed.)

| address | instruction | input / value | field | meaning | out/call | conf |
|---------|-------------|---------------|-------|---------|----------|------|
| `0x8001ec44` | `lw v0,(s2)` | `s2+0x00` | source `vec[0]` | object origin X | →`sp+0x20` | CONFIRMED |
| `0x8001ec48` | `lw v1,0x10(s1)` | `s1+0x10` | camera[0] | view origin X | `v0=vec-cam` | CONFIRMED |
| `0x8001ec58..78` | `lw 4/8(s2)`,`lw 0x14/0x18(s1)` | `s2+0x04/0x08` | source `vec[1..2]` − camera | object origin Y/Z | →`sp+0x24/0x28` | CONFIRMED |
| `0x8001ec7c` | `jal 0x8001474c` | `a0=&(vec−cam)`,`a1=s1+0x54` | — | GTE-transform object origin by view matrix | call | CONFIRMED |
| `0x8001ec84` | `lhu v0,0xc(s2)` | `s2+0x0c` | source `angle[0]` | stage rotation | →`gp+0x540` | CONFIRMED |
| `0x8001ec90/9c` | `lhu 0xe/0x10(s2)` | `s2+0x0e/0x10` | source `angle[1..2]` | stage rotation | →`0x800822da/dc` | CONFIRMED |
| `0x8001ecb0/c0` | `bnez/beqz` on `angle` | `s2+0x0c..0x10` | — | rotation-present vs scale-only path | branch | CONFIRMED |
| `0x8001ecc8/ed0c` | `lbu v0,0x19(s2); andi 0x1f` | `s2+0x19` | matrix-LUT index | choose base orientation matrix | — | CONFIRMED |
| `0x8001ece8..f4` | `sll;…;addiu v0,-0x6ad8` | `0x80089528` | matrix LUT base | base 3×3 matrix `= 0x80089528 + idx*0x20` | — | CONFIRMED |
| `0x8001ecfc` | `jal 0x80060484` | `a0=matrix`,`a2=s1+0x40` | — | libgte: load base matrix into GTE (rotation path) | call | CONFIRMED |
| `0x8001ed3c+` | `lh (a0)…; lh 0x12(s2); mult; >>12` | `s2+0x12` | source `scale[0]` | scale matrix col0 | →`s1+0x40/46/4c` | CONFIRMED |
| `0x8001edb8+` | `lh 2/8/0xe(a0); lh 0x14(s2)` | `s2+0x14` | source `scale[1]` | scale matrix col1 | →`s1+0x42/48/4e` | CONFIRMED |
| `0x8001ee30+` | `lh 4/0xa/0x10(a0); lh 0x16(s2)` | `s2+0x16` | source `scale[2]` | scale matrix col2 | →`s1+0x44/4a/50` | CONFIRMED |
| `0x8001eea4` | `jal 0x800605c4` | `a0=s1+0x40` | — | libgte: load scaled matrix `0x1f8003b4` into GTE | call | CONFIRMED |
| `0x8001eeac..f5c` | `lw (s2)/4/8; lw 0x10/14/18(s1); mult lh s1+0x40..0x50; >>12` | `s2+0x00..0x08`, matrix | — | model-view translation `(camera − vec)·matrix` | →`sp+0x20/24/28` | CONFIRMED |
| `0x8001efd8` | `lbu v0,0x19(s2); andi 0xc0` | `s2+0x19` (bits `0xc0`) | flag | selects `a1=0x190` vs `0x8000` (Z/OT or size flag) | `a1=…` | CONFIRMED read / role LIKELY |
| `0x8001eff0` | `lbu a2,0x18(s2)` | `s2+0x18` | attribute byte | LIKELY color/texture/CLUT selector | `a2=attr` | CONFIRMED read / role LIKELY |
| `0x8001eff4` | `lw a0,0x1c(s2)` | `s2+0x1c` | **payload pointer** | the bit3 payload (vertex array) | `a0=payload` | CONFIRMED |
| `0x8001eff8` | `j 0x80020698` | `a3=s1+0x10` | — | tail to shared emitter | jump | CONFIRMED |

### 7.3 Shared emitter `0x80020698` → `fcn.80010000` (CONFIRMED)

`0x80020698` does `jal 0x80010000` with `a0=payload`, `a1=Z/flag`, `a2=(attr&0xff)<<3` (delay-slot
`sll a2,a2,3`), `a3=0x1f800384`; then `s5++` and `bnez` back to `0x8001eacc` (next survivor); the
function epilogue/`jr ra` is at `0x800206e0`.

`fcn.80010000` (text base) is the **payload-vertex projector / primitive emitter**:
`lw t7,(a0)` = payload **count**; `addi a0,a0,4` skips the count word (→ matches the residual
`a0=0x8018faf4` = entry29 payload `0x8018faf0` + 4); `s2 = −count` loop counter; loads the GTE
matrix/regs (`ctc2`/`mtc2`), projects each vertex, and emits via `jal 0x80060284`. So the **payload is
a `{u32 count; vertex[]}` array** and `fcn.80010000` projects+emits it. CONFIRMED payload role; exact
GPU primitive type (textured tri/quad strip vs flat) and vertex stride = decode of `fcn.80010000` +
`0x80060284` (TODO, §7.5).

### 7.4 Conclusions (CONFIRMED / LIKELY / UNKNOWN)

- **CONFIRMED:** LIST_A is `a0=0x80096ea8` into `fcn.8001ea6c`; the builder reads the survivor source
  record; READ `0x80167b80` (entry29 `vec[0]`) hit in case `0x8001ec44`; dispatch `0x8001eb34` selected
  `v0=0x8001ec44`; case `0x8001ec44` reached.
- **CONFIRMED (new, from the case decode):** case `0x8001ec44` directly reads, for the live render,
  source `vec[3]` (`+0x00`), `angle[3]` (`+0x0c/0e/10`), `scale[3]` (`+0x12/14/16`), the matrix-LUT
  index byte (`+0x19`), the attribute byte (`+0x18`), and the **payload pointer (`+0x1c`)**. This
  upgrades scale/angle from "consumed via the parser-built matrix" to "read directly by the runtime
  builder."
- **LIKELY:** `0x8001ec44` is the builder case for the bit3/scaled survivor cluster around entry29;
  it is a better visible-geometry edit path than cull-row perturbation. The payload is a polygon/mesh
  vertex array (LIKELY a textured strip given the per-object matrix + attribute byte).
- **UNKNOWN:** whether the READ snapshot and the dispatch snapshot are the same iteration (`s2`
  differs); exact primitive format packed by `fcn.80010000`; exact payload vertex stride/topology;
  collision/pathing impact (not evidenced — do not infer).

### 7.5 Next recommended target — **DONE in G11**

`fcn.80010000` and `0x80060284` are decoded in
[`geometry_g11_payload_format.md`](geometry_g11_payload_format.md): payload = `{u32 count; Vertex[N]
stride 0xc (s16 x,y,z; s16 pad; u32 attr); primitive command stream}`; `fcn.80010000` interprets the
stream (type via jump table `@0x8001036c`), projecting vertices with RTPS/RTPT and culling with NCLIP.
Edit-target ranking confirmed there: source `vec[3]` `@0x7388` (translate) first, then `scale[3]`
`@0x739a` (resize), then a payload vertex `@0x2f2fc` (true mesh deformation).

**Build results:** G12 (source `vec[0]` `@0x7388` `+1024`) = VALID BUILD / PATCH LIVE / CPU READ
CONFIRMED (`READ 0x80167b80` in case `0x8001ec44`, live mem `FFFFDCF0`) / **NO OBVIOUS VISUAL CHANGE** —
the source-origin nudge is visually silent in the tested view (does not disprove the payload path). G13
(payload v0.y `@0x2f2fe` `+512`) = VALID BUILD / PATCH LIVE / **VERTEX READ CONFIRMED** (`READ
0x8018faf4` aligned vertex base, PC `0x80010928` `lwc2` in `fcn.80010000`) / **NO OBVIOUS VISUAL
CHANGE** — confirms vertices are read by `fcn.80010000`; lesson: watch the aligned `lwc2` base, not the
inner s16. G14 (command-stream-selected near-apex vertex 14.y `@0x2f3a6` `-1024`) = VALID BUILD / PATCH LIVE /
VERTEX READ CONFIRMED / **VISIBLE RENDER CHANGE** — the first confirmed visible payload-vertex edit,
end-to-end validation of this chain. The deformed object is **grass/decor (non-tangible)**, so G15
pivots to identifying a **terrain/ground** payload (`geometry_g15_terrain_payload_candidates.md`):
static shortlist (e213/e128/e280) + a runtime payload-pointer log at `fcn.80010000` (`a0`=payload) to
confirm the on-screen ground. See `geometry_g11_payload_format.md` §5.1/§5.2/§5.3 and
`geometry_g15_terrain_payload_candidates.md`. Collision/pathing UNKNOWN (visual terrain ≠ collision).

G15 result: the runtime `a0`-log confirmed terrain payload `0x80170978` (DAT `0x10180`); editing its
vertex 46.y (`-1024`) = VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED (`READ 0x80170ba4` at PC
`0x8001069c` `lwc2`) / **NO OBVIOUS VISUAL CHANGE**. The read fired before the project/reject tests, so
read ≠ drawn. G16 decodes the project→reject→pack flow and pinpoints the screen-space capture point
(execute BP at `0x800108b4`, read `a0` + packet screen-XY at `s3`) to select an emitted, on-screen
vertex. See `geometry_g16_screen_space_vertex_selection.md`.
