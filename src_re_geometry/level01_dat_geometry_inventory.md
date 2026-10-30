# G1 — LEVEL01 DAT Geometry Inventory

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md)

**Phase G1 deliverable (ANALYZED 2026-06-13).** Non-mutating inventory of every LEVEL01 top-level
DAT record and the trailing relocation structures, with relocation targets mapped to file ranges.
Roles of non-`0x3f` records remain **byte-pattern descriptions only** — no mesh/collision/render/
pathing labels (no consumer evidence yet; that is G4/G5).

Source: pristine `DAT/LEVEL01_LEVEL.DAT` (sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`,
size `0x51418` = 332824 B). Record offsets/sizes from the CONFIRMED Phase-1 parser size rules
(`src_re/dat_parser_8001cdc0.c`); relocation data from `tools/dat_reloc.py` scan logic (1248 sites).
All figures below were regenerated read-only this phase.

## 1. Top-level record map (CONFIRMED)

Top-level record count = **11**. Records end at **`0x1500`** (CONFIRMED).

| rec | file off | type | count | entry size | parser size | ends | fixed/packed | role |
|----:|---------:|-----:|------:|-----------:|------------:|-----:|--------------|------|
| 0 | `0x0004` | `0x3f` | 70 | `0x10` | `0x464` | `0x0468` | fixed | pickups — **SOLVED context** (CONFIRMED) |
| 1 | `0x0468` | `0x01` | 104 | `0x0c` | `0x4e4` | `0x094c` | fixed `0xc` | 3×s32 per entry (see §5) — role UNKNOWN |
| 2 | `0x094c` | `0x0b` | 16 | `0x0c` | `0x0c4` | `0x0a10` | fixed `0xc` | 3×s32 per entry — role UNKNOWN |
| 3 | `0x0a10` | `0x0c` | 16 | `0x0c` | `0x0c4` | `0x0ad4` | fixed `0xc` | 3×s32 per entry — role UNKNOWN |
| 4 | `0x0ad4` | `0x0d` | 16 | `0x0c` | `0x0c4` | `0x0b98` | fixed `0xc` | 3×s32 per entry — role UNKNOWN |
| 5 | `0x0b98` | `-2` | 48 | packed | `0x130` | `0x0cc8` | packed | s32 prefix + packed byte stream — role UNKNOWN |
| 6 | `0x0cc8` | `-3` | 88 | packed | `0x220` | `0x0ee8` | packed | s32 prefix + packed byte stream — role UNKNOWN |
| 7 | `0x0ee8` | `-4` | 64 | packed | `0x190` | `0x1078` | packed | s32 prefix + packed byte stream — role UNKNOWN |
| 8 | `0x1078` | `-5` | 65 | packed | `0x198` | `0x1210` | packed | s32 prefix + packed byte stream — role UNKNOWN |
| 9 | `0x1210` | `-6` | 56 | packed | `0x160` | `0x1370` | packed | s32 prefix + packed byte stream — role UNKNOWN |
| 10 | `0x1370` | `-7` | 64 | packed | `0x190` | `0x1500` | packed | s32 prefix + packed byte stream — role UNKNOWN |

Parser size rules (CONFIRMED):
- type `0x3f`: `4 + count*0x10`
- other non-negative type: `4 + count*0x0c`
- negative type: `(((3*count + 1) >> 1) << 2) + 0x10` (`>>1` rounds toward zero)

## 2. Trailing / parser-structure map (CONFIRMED)

post-record word @ `0x1500` = `0x0` → trailing-block locator `s2 += (w<<7)+4` → trail = `0x1504`.

| structure | file range | stride | entries | confidence |
|-----------|------------|-------:|--------:|------------|
| post-record word | `0x1500..0x1504` | — | — | CONFIRMED |
| trailing block base | `0x1504` | — | — | CONFIRMED |
| **PASS 1 table** | `0x1512..0x3ae2` | `0x14` | **484** | CONFIRMED |
| **PASS 2 base** | `0x3ae8` | `0x04` | **0** (`[p2]=-1`, EMPTY) | CONFIRMED |
| **PASS 3 table** | `0x3afa..0x45ea` | `0x14` | **140** | CONFIRMED |
| (pass-1 table walk begins at trail+0xe = `0x1512`; pass-3 at p3+0xe = `0x3afa`) | | | | |

Relocation site totals (CONFIRMED, matches `tools/dat_reloc.py` = 1248):

| pass | site | field | count | confidence |
|-----:|------|-------|------:|------------|
| 1 | `P1.A` | `[s3+2]` | 484 | CONFIRMED |
| 1 | `P1.B` | `[s0+0x14]` | 174 | CONFIRMED |
| 1 | `P1.D` | `[s0+0x1c]` | 310 | CONFIRMED |
| 2 | `P2.F` | `[a0+4]` | 0 | CONFIRMED |
| 3 | `P3.G` | `[s3+2]` | 140 | CONFIRMED |
| 3 | `P3.H` | `[s0+0x14]` | 85 | CONFIRMED |
| 3 | `P3.I` | `[s0+0x1c]` | 55 | CONFIRMED |
|   |   | **total** | **1248** | CONFIRMED |

## 3. Region map (CONFIRMED) — the geometry-data region

The geometry-heavy data is **after** the top-level records and **after** the trailing relocation
tables. **0 of 1248** relocation targets land inside the records or the trailing tables; **all 1248**
land in `[0x45f0, 0x4f32c]`.

| region | file range | contents | confidence |
|--------|------------|----------|------------|
| header + records 0..10 | `0x0000..0x1500` | the 11 top-level records | CONFIRMED |
| trailing relocation tables | `0x1504..0x45ea` | pass-1 / pass-2 / pass-3 tables | CONFIRMED |
| **source-record band** | **`0x45f0..0x8bd8`** | the `s0` records pointed to by `[s3+2]` (pass-1 + pass-3); 624 distinct pointers | CONFIRMED (band) |
| **payload band** | **`0x8bd8..0x4f32c` (→ EOF `0x51418`)** | targets of the `[s0+0x14]`/`[s0+0x1c]` sub-pointers | CONFIRMED (band) |

Source vs sub-pointer split (CONFIRMED):

| pointer class | sites | value band |
|---|---:|---|
| source-record `[s3+2]` (P1.A + P3.G) | 624 | `0x45f0 .. 0x8bc0` |
| sub-pointer `[s0+0x14]/[s0+0x1c]` (P1.B/D, P3.H/I) | 624 | `0x8bd8 .. 0x4f32c` |

Per-site value bands (CONFIRMED):

| site | n | min | max |
|------|---:|-----|-----|
| `P1.A [s3+2]` | 484 | `0x45f0` | `0x7ce0` |
| `P3.G [s3+2]` | 140 | `0x7d00` | `0x8bc0` |
| `P1.B [s0+0x14]` | 174 | `0x8bd8` | `0x46a20` |
| `P1.D [s0+0x1c]` | 310 | `0x2ba3c` | `0x43c50` |
| `P3.H [s0+0x14]` | 85 | `0x46e98` | `0x4f274` |
| `P3.I [s0+0x1c]` | 55 | `0x4c910` | `0x4f32c` |

Observations (CONFIRMED bytes; interpretation LIKELY/UNKNOWN as marked):
- The pass-1 and pass-3 `[s3+2]` source-record bands are **disjoint and contiguous**
  (`0x45f0..0x7ce0` then `0x7d00..0x8bc0`): LIKELY two separate object/instance groups built by
  the two passes.
- The first 12 sorted source-record pointers are spaced exactly **`0x18`** apart → LIKELY `s0`
  records have a `0x18`-byte stride in their array. **OPEN CONFLICT (TODO G2):** the parser reads
  `[s0+0x1c]` (bit3 path, SITE D, 310×) and `[s0+0x20]` (gated, never LEVEL01), which lie *beyond*
  a `0x18` stride. So either the stride is not uniformly `0x18`, the array is not fully contiguous,
  or bit3/non-bit3 records occupy size-segregated sub-bands. Do not assume a record size yet.
- Sub-pointers reach as deep as `0x4f32c` (just under EOF `0x51418`), confirming the payload band
  is the bulk of the file.

## 4. Target-density tables (CONFIRMED)

min target = `0x45f0` · max target = `0x4f32c`.

| classification | count |
|---|---:|
| targets inside top-level records (`<0x1500`) | 0 |
| targets inside trailing tables (`0x1504..0x45ea`) | 0 |
| targets after trailing tables (`≥0x45f0`) | 1248 |

Top 10 densest `0x1000`-aligned target ranges:

| range | targets |
|-------|--------:|
| `0x5000..0x6000` | 140 |
| `0x7000..0x8000` | 138 |
| `0x6000..0x7000` | 131 |
| `0x2d000..0x2e000` | 125 |
| `0x2f000..0x30000` | 116 |
| `0x8000..0x9000` | 110 |
| `0x4000..0x5000` | 107 |
| `0x4f000..0x50000` | 72 |
| `0x2b000..0x2c000` | 53 |
| `0x4d000..0x4e000` | 25 |

First 20 relocation targets (value, source field, site):

| # | value | field | site |
|--:|-------|-------|------|
| 1 | `0x004680` | `0x001514` | P1.A `[s3+2]` |
| 2 | `0x00b32c` | `0x004694` | P1.B `[s0+0x14]` |
| 3 | `0x004698` | `0x001528` | P1.A `[s3+2]` |
| 4 | `0x00c6c8` | `0x0046ac` | P1.B `[s0+0x14]` |
| 5 | `0x0046b0` | `0x00153c` | P1.A `[s3+2]` |
| 6 | `0x00d768` | `0x0046c4` | P1.B `[s0+0x14]` |
| 7 | `0x004788` | `0x001550` | P1.A `[s3+2]` |
| 8 | `0x013138` | `0x00479c` | P1.B `[s0+0x14]` |
| 9 | `0x0047a0` | `0x001564` | P1.A `[s3+2]` |
| 10 | `0x0143a0` | `0x0047b4` | P1.B `[s0+0x14]` |
| 11 | `0x004a58` | `0x001578` | P1.A `[s3+2]` |
| 12 | `0x022a90` | `0x004a6c` | P1.B `[s0+0x14]` |
| 13 | `0x004a70` | `0x00158c` | P1.A `[s3+2]` |
| 14 | `0x0231bc` | `0x004a84` | P1.B `[s0+0x14]` |
| 15 | `0x004a88` | `0x0015a0` | P1.A `[s3+2]` |
| 16 | `0x0243d4` | `0x004a9c` | P1.B `[s0+0x14]` |
| 17 | `0x004aa0` | `0x0015b4` | P1.A `[s3+2]` |
| 18 | `0x024e98` | `0x004ab4` | P1.B `[s0+0x14]` |
| 19 | `0x004ad0` | `0x0015c8` | P1.A `[s3+2]` |
| 20 | `0x025684` | `0x004ae4` | P1.B `[s0+0x14]` |

Note the interleave: a `[s3+2]` source pointer (low band) is immediately followed by that record's
`[s0+0x14]` sub-pointer (high band) — i.e. pass 1 relocates each source record then chases its
sub-pointer (CONFIRMED, matches the Phase-1 body).

Last 20 relocation targets (tail is pass-3; many `[s0+0x1c]`/`[s0+0x14]` repeat the same payload
addresses `0x4f32c` / `0x4f274`):

| # | value | field | site |
|--:|-------|-------|------|
| 1229 | `0x008ac8` | `0x004524` | P3.G `[s3+2]` |
| 1230 | `0x04f32c` | `0x008ae4` | P3.I `[s0+0x1c]` |
| 1231 | `0x008ae8` | `0x004538` | P3.G `[s3+2]` |
| 1232 | `0x04f32c` | `0x008b04` | P3.I `[s0+0x1c]` |
| 1233 | `0x008b08` | `0x00454c` | P3.G `[s3+2]` |
| 1234 | `0x04f32c` | `0x008b24` | P3.I `[s0+0x1c]` |
| 1235 | `0x008b28` | `0x004560` | P3.G `[s3+2]` |
| 1236 | `0x04f32c` | `0x008b44` | P3.I `[s0+0x1c]` |
| 1237 | `0x008b48` | `0x004574` | P3.G `[s3+2]` |
| 1238 | `0x04f274` | `0x008b5c` | P3.H `[s0+0x14]` |
| 1239 | `0x008b60` | `0x004588` | P3.G `[s3+2]` |
| 1240 | `0x04f274` | `0x008b74` | P3.H `[s0+0x14]` |
| 1241 | `0x008b78` | `0x00459c` | P3.G `[s3+2]` |
| 1242 | `0x04f274` | `0x008b8c` | P3.H `[s0+0x14]` |
| 1243 | `0x008b90` | `0x0045b0` | P3.G `[s3+2]` |
| 1244 | `0x04f274` | `0x008ba4` | P3.H `[s0+0x14]` |
| 1245 | `0x008ba8` | `0x0045c4` | P3.G `[s3+2]` |
| 1246 | `0x04f274` | `0x008bbc` | P3.H `[s0+0x14]` |
| 1247 | `0x008bc0` | `0x0045d8` | P3.G `[s3+2]` |
| 1248 | `0x04f274` | `0x008bd4` | P3.H `[s0+0x14]` |

## 5. Non-`0x3f` record byte patterns (CONFIRMED bytes; roles UNKNOWN)

Byte-pattern description only. No role assigned without a consumer.

### Fixed `0x0c`-stride records (`0x01`, `0x0b`, `0x0c`, `0x0d`)
Each entry is **three little-endian s32** (`0xc` bytes), i.e. an (a,b,c) triple.

| rec | type | entry 0 (s32 triple) | entry 1 | observed |
|----:|-----:|----------------------|---------|----------|
| 1 | `0x01` | `(4978, -1256, 16516)` | `(4596, -1411, 16510)` | magnitudes in the low-thousands; 2nd field negative, mildly varying across entries — LIKELY a positional/vector triple in file space (pre-`<<5`); role UNKNOWN |
| 2 | `0x0b` | `(-5576, -5620, -3772)` | `(-2117, -5042, 2678)` | signed triples, mixed sign; same 3×s32 shape — role UNKNOWN |
| 3 | `0x0c` | `(8564, -4724, 13253)` | `(9013, -3952, 15009)` | positive-leaning triples — role UNKNOWN |
| 4 | `0x0d` | `(-9416, -4290, -2080)` | `(-3722, -6731, -440)` | negative-leaning triples — role UNKNOWN |

The three fixed records `0x0b/0x0c/0x0d` are each exactly 16 entries; `0x01` is 104. The 3×s32
shape is consistent across all four (CONFIRMED). Whether these are coordinates, directions, or
indices is UNKNOWN (no consumer read yet).

### Packed negative records (`-2..-7`)
Layout (LIKELY, from the size rule `0x10 + ((3*count+1)>>1)*4`): a fixed prefix followed by a
packed stream. Observed bytes:

- **Prefix:** the first 12 bytes of every negative record read as **three s32** (a coordinate-like
  triple), e.g. rec5 `(-1568, -3115, -368)`, rec8 `(-740, -186, 1162)`, rec10 `(-1022, -186, -768)`.
  Records `-4..-7` share the **same 2nd s32 = `-186` (`0xffffff46`)** in the prefix (CONFIRMED;
  meaning UNKNOWN).
- **Packed stream (after the prefix):** a run of **small signed byte pairs** with many `0x00`/`0xff`
  sign bytes, e.g. rec5 `…0f00 f6ff 47ff 2600 eaff 51ff 3c00 e3ff…`. Magnitudes are small and
  drift gradually — CONSISTENT with a delta-encoded / packed sequence (LIKELY). Exact field
  widths and the prefix/stream boundary are **TODO (G2)**; do not assume.

| rec | type | count | prefix s32 triple | shared note |
|----:|-----:|------:|-------------------|-------------|
| 5 | `-2` | 48 | `(-1568, -3115, -368)` | — |
| 6 | `-3` | 88 | `(-68, -3194, 911)` | — |
| 7 | `-4` | 64 | `(1288, -199, 17920)` | prefix word2 region differs; see raw |
| 8 | `-5` | 65 | `(-740, -186, 1162)` | word2 = `-186` |
| 9 | `-6` | 56 | `(-1631, -186, 697)` | word2 = `-186` |
| 10 | `-7` | 64 | `(-1022, -186, -768)` | word2 = `-186` |

## 6. Reproduce (non-mutating)

```bash
# record map + trailing-block locator
python3 - <<'PY'
import struct
d=open('DAT/LEVEL01_LEVEL.DAT','rb').read()
n=struct.unpack_from('<i',d,0)[0]; off=4
for i in range(n):
    cnt=struct.unpack_from('<h',d,off)[0]; typ=struct.unpack_from('<h',d,off+2)[0]
    if typ<0:
        t=3*cnt+1; t=(t+((t>>31)&1))>>1; size=(t<<2)+0x10
    else:
        size=(cnt<<4)+4 if typ==0x3f else ((3*cnt)<<2)+4
    print(f"rec{i:2d} {off:#06x} type={typ:#x} count={cnt} size={size:#x} end={off+size:#06x}")
    off+=size
PY

# relocation site enumeration + density (uses tools/dat_reloc.py scan logic)
PYTHONDONTWRITEBYTECODE=1 python tools/dat_reloc.py DAT/LEVEL01_LEVEL.DAT --scan
```

## 7. G1 open items handed to G2/G3

- Reconcile the source-record stride (`0x18` observed) vs the parser reading `[s0+0x1c]`/`[s0+0x20]`.
- Determine the layout of the `0x18`-ish `s0` source records (coords? the angle/scale fields are at
  `+0xc..+0x16` per Phase 1).
- Identify what the sub-pointer payloads (`0x8bd8..0x4f32c`) contain. **→ ANSWERED in G11 (§8).**
- Decode the packed negative-record stream (`-2..-7`) and the role of the fixed `3×s32` records.
- Resolve which buffer/consumer reads the pass-1 `0x20`-byte output records (G4/G5).

## 8. Payload-band contents — DECODED (G11, 2026-06-14)

The sub-pointer payloads (source `+0x14`/`+0x1c` → band `0x8bd8..0x4f32c`) are **per-object mesh
records** read by `fcn.80010000`. Full decode in
[geometry_g11_payload_format.md](geometry_g11_payload_format.md). Layout (CONFIRMED):

```
+0x00  u32  vertexCount (N)
+0x04  Vertex verts[N]   ; stride 0xc = { s16 x; s16 y; s16 z; s16 pad(=0); u32 attr }
...    primitive command stream ; per prim: u16 ctrl (type=ctrl&0x1f) + vertex byte-offsets; bltz ends
```

Coordinates are s16 `x/y/z` at vertex `+0/+2/+4`; `attr@+8` role LIKELY UV/normal/color (TODO).
Primitives index vertices by **byte offset** into `verts[]` (multiples of `0xc`).

Concrete LEVEL01 examples (pristine DAT, CONFIRMED bytes):

| via | source off | payload off | count | v0 (x,y,z) | v0 DAT off |
|-----|-----------:|------------:|------:|------------|-----------:|
| pass-1 entry0 (`DAT 0x1504`) | `0x4680` | `0x0b32c` | 195 | `(1835,2349,5451)` | `0x0b330` |
| pass-1 entry29 (`DAT 0x1748`, G9 survivor) | `0x7388` | `0x2f2f8` | 34 | `(0,-744,-61)` | `0x2f2fc` |

Edit targets for a visible change (proposal only; survivor entry29): source `vec[3]` `@0x7388`,
source `scale[3]` `@0x739a`, or a payload vertex coord `@0x2f2fc` (see G11 §5).

### entry29 primitive command stream (CONFIRMED, G14 2026-06-14)

Stream span `DAT 0x2f494..0x2f59c` (264 B), terminated by `ffff ffff` at `0x2f598` (boundary = next
payload `0x2f59c`). Vertices are referenced by **byte offset** (`idx*0xc`) into the vertex table.
First primitives:

| cmd off | ctrl | type | strip elems | vertices |
|--------:|------|-----:|------------:|----------|
| `0x2f494` | `0x0262` | 2 (quad strip) | 3 | v0–v3, v4–v7, v8–v11 |
| `0x2f4c8` | `0x8263` | 3 (textured tri strip) | 2 | v12,v13,v14 ; v17,… |
| `0x2f4e4` | `0x8266` | 3-class | … | further textured strips |

Reference histogram (halfword scan for valid vertex offsets across the whole stream): **all 34 verts
referenced; 28 twice, 6 once** (v13,16,20,21,29,30); 62 total references. Mesh is tall/narrow:
Y `0..-1769` (apex tip v13/v16), X `±60`, Z `8..-813`. Near-apex multiply-referenced verts (good edit
targets): **v14** `(-20,-1601,-579)` @`0x2f3a4`, **v15** `(21,-1600,-580)` @`0x2f3b0`. G14 edits
v14.y @`0x2f3a6` → **VISIBLE deform, but entry29 is grass/decor (non-tangible)**.

### Payload classification survey (G15, 2026-06-14)

entry29's tall/narrow shape = grass/decor. A read-only survey of all 482 pass-1 payloads
(`tools/survey_level01_payloads.py`, metric flatness = `Yspread/max(Xspread,Zspread)`) separates
grass/decor (flat > 2, small footprint, instanced) from terrain/ground (flat < 0.5, big footprint,
higher vert count). Terrain shortlist: e213 `0x0d934` (182v), e128 `0x356bc` (230v), e280 `0x0eb14`,
e282 `0x0f6f4`, e264/e265. Full table + runtime-confirmation plan in
[geometry_g15_terrain_payload_candidates.md](geometry_g15_terrain_payload_candidates.md). Roles LIKELY
(render only); **visual terrain ≠ collision** — do not infer.

**Runtime-confirmed terrain (G15, 2026-06-14):** an EXEC `0x80010000` `a0`-log (operator on ground)
showed the static shortlist was NOT drawn in the tested view; the actual ground-render surface is
payload **`DAT 0x10180`** (runtime `0x80170978`): 63 verts, X spread 7937, flatness 0.30, positive-Y
ground stratum, drawn once. High-frequency `a0` pointers (`0x8018c234` ×6, `0x8018c570` ×4) are
**instanced decor/props** (tall/small, reused), not terrain. G15 Candidate TERRAIN-PV edited vertex 46
`y` @`DAT 0x103ae` → VALID BUILD / VERTEX READ CONFIRMED / **no obvious visual change** (read ≠ drawn).
G16 (see [geometry_g16_screen_space_vertex_selection.md](geometry_g16_screen_space_vertex_selection.md))
adds the screen-space gate: a payload vertex is only a good edit target once its primitive is confirmed
**emitted + on-screen** (execute BP at `fcn.80010000`+`0x800108b4`, read packet screen-XY at `s3`).

**G16 emitted-primitive result (2026-06-14):** the runtime gate log confirmed payload **`DAT 0x356bc`**
(rt `0x80195eb4`, = static **e128**: 230 verts, X 5838, Y 5093–8332, Z 6700, flat 0.48) emits ≥5
primitives in the ground view, and **`DAT 0x1b9f0`** (rt `0x8017c1e8`, 92 verts) ≥2. G16 Candidate
EMITTED-PV edited `0x356bc` vertex 10 `y` @`DAT 0x3573a` (`6841`→`5817`, `-1024`). (Note: at `0x800108b4`,
`a0` = vertex-table ptr, payload = `a0−4`.)

**G16 visual RESULT (2026-06-14): VISIBLE WALL RENDER CHANGE.** The `0x356bc` edit visibly deformed a
**vertical wall/cliff face — NOT the walkable floor/top surface** → **`0x356bc` (e128) reclassified
wall/vertical terrain face** (not "ground"). CONFIRMED: payload-vertex edits visibly deform
terrain-family render geometry; UNKNOWN: the walkable floor payload and any collision coupling.
**Visual terrain ≠ collision** — do not infer; this is not a floor collision edit.

**G17 (PLANNED 2026-06-14):** find the **walkable floor/top-surface** payload (flat shape + tight local Y
band + primitive screen-XY on the floor) with emitted evidence. Static floor shortlist (flatter than the
`0x356bc` wall): **e135 `0x1f148`** (flat 0.19, Yband 409), **e254 `0x08f4c`** (0.22), **e52 `0x17d94`**
(0.23), e264 `0x0945c`/e265 `0x09dbc` (~0.29), e280 `0x0eb14` (0.29); partial-emit lead **`0x1b9f0`**
(e160, ≥2 prims). No build until a floor payload is emit-confirmed as the walkable surface. See
[geometry_g17_floor_payload_candidates.md](geometry_g17_floor_payload_candidates.md).

**G17 Candidate B / G18 RESULT (2026-06-14): the walkable floor is NOT a LEVEL.DAT payload.** The
`0x800108b4` emit log of the broad floor view returned one payload at runtime `0x801bdc58` — **past
LEVEL.DAT EOF** (`0x801b1c10`), past the pass-1 output buffer and reserved gap, in the "next resource" heap
region (`a0−4−DATbase = 0x5d460` is INVALID: `> 0x51418`). This is consistent with §3/§4's reloc proof:
**all 1248 relocation targets land in `[0x45f0, 0x4f32c]`** (none past EOF), the parser runs once, and the
emitter loads `a0` directly from `[s2+0x1c]/[s2+0x20]` with no base add — so no LEVEL.DAT pointer can reach
`0x801bdc58`. The floor is a **runtime/output-buffer payload**, LIKELY converted from a separate LEVEL01
terrain resource (`LEVEL.RAW`/`TERRAIN.ALL`/`TERR1.ALL`, which ship beside `LEVEL.DAT` and begin with s16
coordinate streams). So the §5 walkable floor/terrain that the naive-append crash implicated may be
sourced **outside** this DAT. DAT source UNKNOWN; collision/pathing UNKNOWN. Trace + runbook:
[geometry_g18_output_buffer_floor_trace.md](geometry_g18_output_buffer_floor_trace.md).

**G18b — one-payload-many-records is INSTANCING (2026-06-14).** A near-floor re-log emitted a DAT-backed
payload at runtime `0x8018dc58` → DAT off **`0x2d460`** (VALID). It is the clearest in-DAT example of
**instancing**: a single payload (count 25, footprint 202×107×194, flatness 0.53, all 25 verts referenced)
is shared by **93 distinct pass-1 source records** (bit3 path, `[src+0x1c]=0x2d460`, scale ≈`(4349,4096,3153)`,
scattered vec/angle). High reference count ⇒ **instanced decor/prop, NOT the walkable floor** (per the G15
high-frequency rule). Confirms the §8 model `source +0x1c → payload band` with N:1 source-to-payload sharing,
and that the sub-pointer density (`0x2d000..0x2e000` = 125 reloc targets, §4) reflects many records pointing
into the same decor payloads. Full record:
[geometry_g18_dat_backed_floor_candidate.md](geometry_g18_dat_backed_floor_candidate.md). Roles render-only;
**visual ≠ collision** — do not infer.
