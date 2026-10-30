# G18 — DAT-backed emitted payload `0x2d460` (Candidate B-like view) — INSTANCED DECOR, not floor

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G18 output-buffer floor trace](geometry_g18_output_buffer_floor_trace.md) ·
[← G17 floor candidates](geometry_g17_floor_payload_candidates.md) ·
[← G16 screen-space selection](geometry_g16_screen_space_vertex_selection.md) ·
[← G11 payload format](geometry_g11_payload_format.md)

Status: **RUNTIME LOG RECORDED + STATIC DECODE (2026-06-14).** Read-only `SCUS_942.88` model + read-only
`DAT/LEVEL01_LEVEL.DAT` decode. **No patch, no build.** No collision/pathing claims — visual ≠ collision.

> **Headline:** the operator's Candidate B-**like** view (very close to the earlier walkable-floor view,
> not pixel-identical) emitted a **DAT-backed** payload at runtime `0x8018dc58` → DAT off **`0x2d460`**
> (VALID, `< 0x51418`). Decoding `0x2d460` shows it is **NOT** the walkable floor: it is a **small
> (~202×107×194) closed blob mesh referenced by 93 pass-1 source records → heavily instanced decor/prop.**
> The operator's runtime-only "strong floor candidate" read is **superseded** by the static metrics.
> **No floor edit target is supported here; no build prepared.**

## 0. Why this doc is separate from the earlier Candidate B log

There are now **two different** "Candidate B-ish" emitted-payload logs. They must not be merged:

| log | runtime payload base | `−DATbase` | valid DAT? | what it is |
|-----|----------------------|-----------:|------------|------------|
| **earlier exact Candidate B** (G17/G18 §1) | `0x801bdc58` | `0x5d460` | **NO** (`> 0x51418` EOF) | output-buffer/heap floor payload — **walkable floor**, not in LEVEL.DAT (traced in [g18 output-buffer trace](geometry_g18_output_buffer_floor_trace.md)) |
| **this Candidate B-LIKE** (here) | `0x8018dc58` | **`0x2d460`** | **YES** | **DAT-backed** payload — decodes to **instanced decor/prop**, not the floor |

The two runtime bases differ in one hex digit (`0x801b…` vs `0x8018…`) and map to entirely different
payloads. The earlier base is heap (past EOF); this base is inside the loaded DAT. So this log captured a
**different emitted primitive** — a piece of small scattered decoration in/near the floor view, not the
floor surface that fills the screen. The walkable floor itself remains the heap payload `0x801bdc58`.

## 1. Candidate B-like runtime log (EXEC `0x800108b4`, 17 parsed hits)

Breakpoint `EXEC 0x800108b4` = `fcn.80010000` post-projection/reject packet-store gate (`addi s3,s3,0x34`,
past all RTPS/RTPT/NCLIP/AVSZ4 rejects). At this PC: `a0` = vertex-table pointer ⇒ **payload base = `a0−4`**;
`s3` = GPU packet/output pointer advanced by `0x34`. Operator: moved very close to the earlier Candidate B
walkable-floor/top-surface view (not guaranteed pixel-identical). **All parsed hits show the same
DAT-backed emitted payload.**

Fixed for every hit:

| field | value |
|-------|-------|
| PC | `0x800108b4` |
| `a0` | `0x8018dc5c` |
| payload base (`a0−4`) | `0x8018dc58` |
| raw DAT offset (`a0−4 − DATbase 0x801607f8`) | **`0x2d460`** |
| valid DAT offset? | **YES** (`0x2d460 < 0x51418` EOF) |

Per-hit packet pointer `s3` (monotone with strip gaps where other primitives interleave):

| Hit | PC | a0 | payload base | DAT off | valid DAT? | s3 (packet) | Δ from prev | note |
|----:|----|----|--------------|---------|------------|-------------|------------:|------|
| 5  | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D1F38` | — | DAT-backed emitted payload |
| 6  | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D1F6C` | `+0x34` | DAT-backed emitted payload |
| 7  | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D1FA0` | `+0x34` | DAT-backed emitted payload |
| 8  | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D1FD4` | `+0x34` | DAT-backed emitted payload |
| 9  | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D2008` | `+0x34` | DAT-backed emitted payload |
| 10 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D21A8` | `+0x1a0` | gap (other prims interleaved) |
| 11 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D21DC` | `+0x34` | DAT-backed emitted payload |
| 12 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D2210` | `+0x34` | DAT-backed emitted payload |
| 13 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D2244` | `+0x34` | DAT-backed emitted payload |
| 14 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D23E4` | `+0x1a0` | gap |
| 15 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D2418` | `+0x34` | DAT-backed emitted payload |
| 16 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D244C` | `+0x34` | DAT-backed emitted payload |
| 17 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D2480` | `+0x34` | DAT-backed emitted payload |
| 18 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D2620` | `+0x1a0` | gap |
| 19 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D2654` | `+0x34` | DAT-backed emitted payload |
| 20 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D2688` | `+0x34` | DAT-backed emitted payload |
| 22 | `0x800108B4` | `0x8018DC5C` | `0x8018DC58` | `0x2D460` | yes | `0x801D26F0` | `+0x68` | DAT-backed emitted payload |

**CONFIRMED from the log:** a DAT-backed payload `0x2d460` emitted ≥17 primitives (survived all projection/
reject tests) in this near-floor view. **Unlike** the earlier exact-Candidate-B output-buffer payload
`0x801bdc58` (heap, off `0x5d460`, past EOF), this one is **direct LEVEL.DAT-backed** and therefore
**editable in LEVEL.DAT**. That is the only thing the runtime log proves; *what* `0x2d460` is requires the
static decode (§2).

**Caveat on `a0` repetition:** identical `a0` across all hits does **not** prove "one big surface." Instanced
objects reuse the **same** payload pointer for every instance, so 17 same-`a0` hits is equally consistent with
one instance emitting 17 primitives *or* several instances of a shared mesh in frame. The decode (§2) is
decisive.

## 2. Static decode of payload `0x2d460` (read-only, CONFIRMED bytes)

```
payload @0x2d460:  count = 25 (0x19)
vertex table @0x2d464 (runtime 0x8018dc5c), stride 0xc
command stream @0x2d590 .. 0x2d6ec (348 bytes; next-payload boundary 0x2d6ec)
```

### 2.1 Bounding box / shape metrics

| metric | value |
|--------|-------|
| vertex count | **25** |
| bbox X | `[-103, 99]` → spread **202** |
| bbox Y | `[-107, 0]` → spread **107** |
| bbox Z | `[-97, 97]` → spread **194** |
| flatness = Ysp / max(Xsp,Zsp) | **0.53** |
| local Y band (q25–q75) | 67 (q25 `-92`, q75 `-25`) — tight only because the whole object is tiny |
| pads (`vertex+0x6`) | all 0 (CONFIRMED) |

The vertex table is a **small closed blob**: six verts at `y=0` form a top ring (v18–v21, v23, v24), the
single bottom apex is **v22** `(-2, -107, 0)`, and the mid bands (`y=-25/-53/-92`) wrap the sides. X `±100`,
Z `±97`, height 107 → a roughly rounded ~200-wide, ~107-tall lump (rock / clod / clump / tuft shape).

### 2.2 Instancing — the decisive signal

**93 distinct pass-1 source records all point their payload field (`[src+0x1c]`, bit3 path) at `0x2d460`.**
Every one is flag `0x0019` (bit3 set), `attr[src+0x18]=0x04`, and they share a near-constant scale
`scale[3]≈(4349, 4096, 3153)` (a handful differ slightly) with **widely varied** `vec[3]` and `angle[3]`:

| pass-1 entries referencing `0x2d460` (93 total) |
|---|
| 19, 31, 92, 93, 105, 106, 117, 122, 125, 136, 138, 140, 157, 158, 159, 162, 168, 170, 191, 192, 199, 200, 205, 206, 207, 219, 220, 221, 222, 224, 229, 242, 243, 250, 253, 263, 266, 271, 275, 279, 283, 292, 297, 299, 300, 301, 303, 304, 308, 309, 310, 317, 320, 323, 324, 325, 329, 336, 340, 350, 354, 355, 356, 357, 358, 365, 366, 379, 381, 382, 386, 387, 398, 401, 406, 407, 412, 416, 418, 422, 423, 424, 427, 435, 443, 445, 452, 461, 466, 478, 480, 481, 482 |

The 93 instance origins (`vec[3]`) scatter sparsely across a huge area — X roughly `[-11255, +9240]`,
Z roughly `[-14150, +24980]`, all at a similar Y stratum (`~ -1000 .. -4317`), with **varied rotations**.
A 200-unit object covering a ~20000×40000 area with only 93 instances is **sparse scatter** (props/decor),
**not** a dense tiled grid (a tiled floor would need thousands of regularly-spaced, same-rotation tiles).

### 2.3 Command stream / first emitted primitive (CONFIRMED)

First halfwords at `0x2d590`:
```
0060 000e | 0000 000c 0018 0024 | ccfc e3fc e0f3 d2f3 | 0030 000c 0000 003c | e3ff e3fc ccfc caff | 0048 0054 …
```
- `ctrl = 0x0060` → `type = ctrl&0x1f = 0` (triangle/strip base), shade bits `(ctrl>>5)&3 = 3`, `tex = ctrl>>7 = 0`.
- next halfword `0x000e = 14` = strip element count (same grammar as the G16 wall `0x356bc` first command,
  `ctrl 0x0060` + element count).
- then vertex **byte-offsets** `0x0000/0x000c/0x0018/0x0024` → verts **0,1,2,3**, interleaved with
  attr/UV/color words (`0xccfc`, `0xe3fc`, … — not multiples of `0xc`, not vertex offsets).

**Reference histogram (halfword scan for valid `%0xc` offsets across the whole stream):** all **25/25
vertices referenced; 2–5 refs each; none referenced exactly once** (idx→refs:
`0:4 1:4 2:3 3:4 4:4 5:4 6:4 7:4 8:5 9:4 10:3 11:4 12:4 13:4 14:3 15:4 16:4 17:4 18:2 19:2 20:2 21:2 22:3 23:2 24:2`).
A fully-connected closed mesh with every vertex shared by multiple triangles = a solid small prop, not a flat
floor slab.

## 3. Role classification

```
DAT-BACKED EMITTED PAYLOAD CONFIRMED /
INSTANCED DECOR / PROP (93×) — NOT WALKABLE FLOOR OR TOP-SURFACE /
COLLISION/PATHING UNKNOWN
```

Evidence (all CONFIRMED, read-only):

| floor filter (G17 §2) | floor requires | `0x2d460` | pass? |
|-----------------------|----------------|-----------|-------|
| unique / drawn-once | 1 reference | **93 references** | ✗ instanced |
| wide footprint | Xsp/Zsp in the thousands | 202 × 194 | ✗ tiny |
| flatness `< 0.35` | flat slab | **0.53** | ✗ |
| top surface Flik stands on | broad horizontal plane | small closed blob | ✗ |

This is the **same trap G15 flagged** ("high-frequency repeated `a0` = instanced decor → reject"; G15
rejected `0x8018c234` ×6 / `0x8018c570` ×4). `0x2d460` is even more heavily instanced (×93).
**Independent corroboration:** the G15 EXEC `0x80010000` `a0`-log *already* observed this exact runtime
base — `0x8018dc58 ×2`, classified there as a **"pebble"** decor — so two separate runtime logs (G15 and
this G18b) and the static decode all agree `0x2d460` is a small instanced prop, not the floor. The operator's
runtime note ("strong immediate floor/top-surface render candidate") was based on *emit-in-the-floor-view
alone*, which G16 already established is **necessary but not sufficient** — a wall in frame emits (G16), and
so does scattered floor decoration (here). The static decode supersedes the runtime-only guess.

**What this does and does not change:**
- It does **not** make `0x2d460` the walkable floor. The walkable floor that *fills the screen* remains the
  heap/output-buffer payload `0x801bdc58` (off `0x5d460`, past EOF) from the earlier exact Candidate B log —
  still **not** a LEVEL.DAT payload (see [g18 output-buffer trace](geometry_g18_output_buffer_floor_trace.md)).
- It **does** confirm that scattered decoration sitting on/near the floor *is* DAT-backed and emit-confirmed,
  so a LEVEL.DAT vertex edit on `0x2d460` would be **visible** (unlike the read-only-only G15 pick) — but it
  would deform a small prop in up to 93 places, not the floor.

## 4. Edit-target decision — NO floor build (analysis does not support a floor target)

Per the task guardrails and the G15/G17 discipline, **no floor edit target is selected and no build is
prepared.** `0x2d460` fails every floor criterion (§3). Building a `…_FLOOR_VERTEX_TEST` image on instanced
decor would mislabel it as floor and add little: the payload-vertex-edit method is **already proven visible**
(G14 grass, G16 wall). Editing one more instanced decor mesh would only re-confirm "decor is editable."

**Proposed single-coordinate target (RECORDED FOR REFERENCE ONLY — not built, not a floor):** if a future
session wants to *visibly confirm the decor classification*, the cleanest one-s16 test is the bottom apex
**v22 `y`** (the lone silhouette extremity, refs=3, shared by 3 triangles):

| item | value |
|------|-------|
| payload | `0x2d460` (instanced decor, 93×) |
| vertex | **v22** `(-2, -107, 0)`, the bottom apex |
| field | v22 `y` (s16) |
| DAT offset | **`0x2d56e`** (vertex base `0x2d56c`; runtime `0x8018dd6a`, base `0x8018dd68`) |
| original bytes / value | `95 ff` = `-107` |
| proposed new bytes / value | `95 fb` = `-1131` (delta **−1024**, single byte `0x2d56f` `ff→fb`) |
| revert | `95 ff` |
| expected effect | a sharp downward spike at the underside of **every** in-view instance of this prop (≈10× the object's height) — confirms it is a small instanced object, not a floor |
| uncertainty | this is **decor, not floor**; the spike appears at up to 93 scattered sites; may be small on-screen if instances are distant; collision/pathing UNKNOWN |

Watch (per the G13 lesson) the **aligned vertex base** `0x8018dd68` (not the inner s16) to confirm the
`lwc2` load if ever tested.

**Guardrails honored:** no DAT/CUE/BIN/RAM/save-state produced or committed; no collision/pathing claim; no
trail/cull-row edit; single-vertex only; visual ≠ collision.

## 5. Where this leaves the walkable-floor hunt

- The walkable floor is **still not located in LEVEL.DAT.** The only DAT-backed payload found in the near-floor
  view is instanced decor (`0x2d460`); the screen-filling floor is the heap payload `0x801bdc58`
  ([g18 output-buffer trace](geometry_g18_output_buffer_floor_trace.md)).
- **Next (unchanged from G18):** the narrow runtime writer/source trace for `0x801bdc58` —
  WRITE watch `0x801bdc58` during LEVEL01 load (= generator PC + source resource) + EXEC BP `0x80020684`
  cond `a0==0x801bdc5c` to read `s2` (DAT `<0x801b1c10` vs heap `≥`). The LIKELY source is a separate terrain
  resource (`LEVEL.RAW`/`TERRAIN.ALL`/`TERR1.ALL`).
- **Method note for the operator:** at the `0x800108b4` gate, also capture the packet **screen-XY** at `s3`
  (`+0x00/0x08/0x0c/0x14/0x18/0x20`; X=low s16, Y=high s16) — a floor primitive lands in the lower/central
  band; small scattered decor lands as compact clusters. The cleanest "is this the floor?" check stays the
  **DAT decode (refs + footprint + flatness)**, which is what reclassified `0x2d460` here.

**Reproducibility (G19 correction, 2026-06-14):** this DAT decor payload `0x2d460` (rt `0x8018dc58`) is the
**reproducible** nearby hit; the actual floor `0x801bdc58` is **OBSERVED ONCE / NOT REPRODUCIBLE** (no
conditional BP in DuckStation → no F5 grinding for `a0=0x801bdc5c`). The hunt **pivots to the resource side**:
the floor is **LIKELY a second parser-format DAT** (`LEVEL1.DAT`/`LEVEL2.DAT`, which contain wide-flat floor
payloads), loaded into the heap after LEVEL.DAT — see
[geometry_g19_floor_resource_source.md](geometry_g19_floor_resource_source.md). The next step is a
deterministic loader trace (EXEC BP `0x8003d550`/`0x8003d568`), not reproducing the floor draw.

## 6. Reproduce (read-only)

```bash
python3 - <<'PY'
import struct
d=open('DAT/LEVEL01_LEVEL.DAT','rb').read()
u16=lambda o:struct.unpack_from('<H',d,o)[0]; s16=lambda o:struct.unpack_from('<h',d,o)[0]
u32=lambda o:struct.unpack_from('<I',d,o)[0]
PAY=0x2d460; DATBASE=0x801607F8; TRAIL=0x1504
print('a0=0x8018dc5c -> base 0x8018dc58 -> off', hex(0x8018dc58-DATBASE), 'valid', 0x8018dc58-DATBASE<0x51418)
cnt=u32(PAY); vb=PAY+4
xs=[s16(vb+i*12) for i in range(cnt)]; ys=[s16(vb+i*12+2) for i in range(cnt)]; zs=[s16(vb+i*12+4) for i in range(cnt)]
print('count',cnt,'X',min(xs),max(xs),'Y',min(ys),max(ys),'Z',min(zs),max(zs))
refs=sum(1 for e in range(484) for src in [u32(TRAIL+e*0x14+0x10)]
         if 0x45F0<=src<0x8BD8 and (u16(TRAIL+e*0x14+0xE)&8) and u32(src+0x1C)==PAY)
print('pass-1 references to 0x2d460 =',refs,'(instanced decor if >>1)')
PY
# emitter packet-store gate: EXEC 0x800108b4 ; a0=vertex-table ptr -> payload=a0-4
```
