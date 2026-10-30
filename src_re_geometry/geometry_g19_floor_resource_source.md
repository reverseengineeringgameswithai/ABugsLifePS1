# G19 — floor/terrain resource source (pivot away from reproducing `a0=0x801bdc5c`)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G18 output-buffer trace](geometry_g18_output_buffer_floor_trace.md) ·
[← G18 DAT-backed candidate](geometry_g18_dat_backed_floor_candidate.md) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **STATIC RESOURCE INVENTORY + LOADER TRACE + RUNTIME-CHECK PROPOSAL (2026-06-14).** Read-only
`SCUS_942.88` disasm + read-only file inspection of the extracted LEVEL01 sidecar resources.
**No patch, no build.** No collision/pathing claims — visual ≠ collision.

> **Headline:** stop trying to re-hit `EXEC 0x800108b4` with `a0=0x801bdc5c`. The generated floor payload
> `0x801bdc58` is **OBSERVED ONCE / STRONG BUT NOT REPRODUCIBLE / source still UNKNOWN**; the reproducible
> nearby hits are DAT-backed decor (`0x2d460`). Pivoting to the resource side: LEVEL01 ships **two more
> parser-format DATs** — `LEVEL1.DAT` and `LEVEL2.DAT` — that **contain wide-flat floor-signature payloads
> in the exact `fcn.80010000` format** (LEVEL.DAT does not), and the engine's resource loader parses
> **multiple** DATs into the heap. So the walkable floor is **LIKELY a second parsed DAT** (loaded after
> LEVEL.DAT, into the `0x801bxxxx` heap region), not a runtime mesh generated from `.RAW`/`.ALL`. Exact
> file+offset is **UNKNOWN** until a deterministic loader trace (proposed §7) — which does **not** need
> `a0` reproduction.

## 0. G20 UPDATE (2026-06-14) — the loader trace REFUTED H1; terrain `.all` is now leading

The proposed §7 loader trace was run: `EXEC 0x8003d550` and `EXEC 0x8003d568` each hit **once** during
"Loading Level…", with `a1=0x51418` at the parse = LEVEL.DAT. **No second parse.** So the parser
`fcn.8001cdc0` runs **exactly once for LEVEL01**, and **H1 below (floor = a second parsed DAT) is REFUTED**;
G18's "parser once" stands. The floor comes from a **non-parser** loader. Static mapping (G20) found it: the
**post-DAT terrain `.all` loader** `fcn.8002ffa8` (file-read `0x8002ffe4`) + processor `fcn.8002fce8`, which
loads `TERRAIN.ALL`/`TERR1.ALL` into the **heap cursor** region where `0x801bdc58` lives — making **H2 the
leading hypothesis.** Full map + the new runbook (EXEC `0x8002ffe4`):
[geometry_g20_sidecar_loader_trace.md](geometry_g20_sidecar_loader_trace.md). (The H1/H2/H3 ranking in §5
below is **superseded** by this update; kept for the record.)

**G21 UPDATE (2026-06-14):** the G20 terrain-`.all` runbook (`EXEC 0x8002ffe4`/`0x80030dc0`) also got **0
hits** → H2 is now **open/unconfirmed too** (the orchestrator skips the file-read when the terrain is cached).
All sidecar hypotheses are now being resolved the robust way: **one breakpoint at the universal file-loader
entry `EXEC 0x80046330`** (`a0`=filename, `a1`=dest) logs every load; new prime suspect = the indirect
high-heap loader `fcn.8003a318` (`0x801cc390 − size`, region can contain the floor). Map + runbook:
[geometry_g21_file_read_caller_map.md](geometry_g21_file_read_caller_map.md).

**G22 RESOLUTION (2026-06-14): the floor source resource is `LEVEL.RAW`.** `EXEC 0x80046330` Hit #4 caught
`fcn.8003a318` loading **LEVEL.RAW** (dest-size `0xb68e4` = its exact size) to `0x80115aac`, bracketing the
floor `0x801bdc58` at offset `0xa81ac`. The floor is **converted/generated from LEVEL.RAW at runtime** (the
`0xa81ac` bytes are an indexed-geometry stream, not a verbatim payload). So the answer to this doc's question
("which sidecar produces the floor") is **LEVEL.RAW** — not a parsed DAT (H1, refuted G20) and not `TERRAIN.ALL`
(H2, did not fire G21). Detail: [geometry_g22_high_heap_floor_source.md](geometry_g22_high_heap_floor_source.md).

## 1. Reproducibility correction (record both states)

```
0x801bdc58  (runtime floor/top-surface payload, EXEC 0x800108b4, a0=0x801bdc5c):
  OBSERVED ONCE / IMPORTANT / NOT CURRENTLY REPRODUCIBLE
  likely generated/heap floor payload past LEVEL.DAT EOF (0x801b1c10), +0x7248 into the next-resource region
  DAT source UNKNOWN (this DAT-of-origin is the G19 question)

0x8018dc58 / DAT 0x2d460  (reproducible in nearby near-floor views):
  REPRODUCIBLE, DAT-backed (valid LEVEL.DAT offset 0x2d460)
  decoded as instanced decor/pebble (93 source records share it; 202×107×194; flat 0.53)
  NOT the floor  (see geometry_g18_dat_backed_floor_candidate.md)
```

**Why reproduction was abandoned (operator + tooling reality):** the floor payload only appeared in one
broad-floor camera/draw-order state; near-identical views emit the DAT decor `0x2d460` instead; DuckStation's
GUI has **no conditional breakpoint** (`EXEC 0x800108b4 if a0==0x801bdc5c`), so pressing F5 hoping for the
exact `a0` is too fragile to be a workflow. The productive path is to identify the floor **resource/source**,
which does not depend on hitting that pointer again.

## 2. LEVEL01 sidecar resource inventory (CONFIRMED — `REBUILD/files/LEVEL01/`)

| file | size | hex | first bytes | classification (CONFIRMED by header/format) |
|------|-----:|----:|-------------|---------------------------------------------|
| `LEVEL.DAT` | 332824 | `0x51418` | `0b 00 00 00` (rec count 11) | **parsed DAT** — base `0x801607f8`; props/decor/walls/grass (G10–G18) |
| `LEVEL.DAT.orig` | 332824 | `0x51418` | — | pristine Oct-1998 backup of LEVEL.DAT |
| **`LEVEL1.DAT`** | 107880 | `0x1a568` | `01 00 00 00 3e 00 3f 00` (rec count 1) | **parsed DAT** — 1 rec (`0x3f`×62) + large geometry region; **contains floor payloads** (§5) |
| **`LEVEL2.DAT`** | 264068 | `0x40784` | `0c 00 00 00 36 00 3f 00` (rec count 12) | **parsed DAT** — 12 recs (`0x3f/0x01/-2..-b`); **contains big floor payloads** (§5) |
| `LEVEL.RAW` | 747748 | `0xb68e4` | `00 00 83 0c …` (magic `0c830000`) | **compressed** blob (high-entropy packed tail) |
| `LEVEL1.RAW` | 541200 | `0x84210` | `00 00 83 0c …` (same magic) | **compressed** blob |
| `TERRAIN.ALL` | 236940 | `0x39d8c` | `b6 b2 01 00 / 01 00 02 00 / a9 fe 77 01 …` | **uncompressed s16 (x,z) coordinate-pair stream** + sub-header `01 00 02 00` |
| `TERR1.ALL` | 61560 | `0xf078` | `cc 6c 00 00 / 01 00 02 00 / e1 fe 2a 01 …` | **uncompressed s16 (x,z) coordinate-pair stream** + same sub-header |
| `LEVEL.BIN` | 1680 | `0x690` | `05 00 00 00 / 27bdffe0 …` | **MIPS overlay code** (count word + `addiu sp,sp,-0x20` prologue) |
| `LEVEL1.BIN` | 2700 | `0xa8c` | `0f 00 00 00 / 27bdffe0 …` | **MIPS overlay code** |
| `LEVEL1A.VB` / `.VH` | 501680 / 5152 | — | — | VAB audio body / header |
| `LEVEL2C.VB` / `.VH` | 506528 / 5152 | — | — | VAB audio body / header |

Sizes match the figures the G18 trace recorded (`LEVEL.RAW 0xb68e4`, `LEVEL1.RAW 0x84210`,
`TERRAIN.ALL 0x39d8c`, `TERR1.ALL 0xf078`). The new facts here: **LEVEL1.DAT / LEVEL2.DAT are also
parser-format DATs**, and the `.RAW` files are **compressed** (so a raw-loaded `.RAW` is not in the
`fcn.80010000` payload format unless decompressed first).

## 3. Header/format classification (CONFIRMED bytes)

- **Parsed DATs** (`LEVEL.DAT`/`LEVEL1.DAT`/`LEVEL2.DAT`): word0 = top-level record count; records use the
  CONFIRMED size rules (`0x3f`→`4+cnt*0x10`; non-neg→`4+cnt*0xc`; neg→`(((3c+1)>>1)<<2)+0x10`); a post-record
  word locates the trailing relocation block; the bulk is the post-trailing geometry/payload region reached
  by relocation — **the same format `fcn.8001cdc0` parses and `fcn.80010000` emits.** LEVEL1.DAT trails at
  `0x3ec`; LEVEL2.DAT at `0x1200`. Both parse cleanly end-to-end.
- **`.RAW`** : shared magic `00 00 83 0c` then a structured/packed body — **compressed** (the nibble-patterned
  tail is not s16 coordinates or a `{count;vertex}` header). Word0 `0x0c830000` is far too large to be a
  payload count. A converter/decompressor must expand it before use.
- **`.ALL`** : word0 (size/flag) + `01 00 02 00` sub-header + a long run of **s16 (x,z) pairs** (e.g.
  TERRAIN.ALL `a9 fe 77 01` = `(−343, 375)`), i.e. a 2D terrain coordinate stream — **not** the
  `{u32 count; Vertex 0xc; cmds}` payload format → would need runtime conversion to be emitted by
  `fcn.80010000`.
- **`.BIN`** (level/level1) : a small count word then MIPS machine code → **level overlay code**, not geometry.
  (Separate from `bits\memory.bin`, a memory-layout descriptor referenced by the loader at `0x8001adfc`.)

## 4. The loader — multi-DAT, resource-ID dispatch (CONFIRMED disasm)

- **`fcn.8003cf2c` = resource-ID dispatcher.** It takes `a0` = resource id `s4`, computes `v1 = id−1`,
  range-checks `sltiu v1,0x11` (17 ids), and `jr` through a jump table at **VA `0x8001afb0`** (17 handler
  entries, all in `0x8003cfc4..0x8003d1e0`). **4 callers**: `0x8003f544`, `0x800503cc`, `0x80052290`,
  `0x8005b830` (resource id read from `[0x80082504]`).
- The handlers converge on a **shared file-read + parse block** (`~0x8003d2f0..0x8003d570`):
  - `0x8003d4ac sw v0,0x2498(at)` → **DATbase (`[0x80082498]`) := heap cursor** for this load.
  - `0x8003d550 jal fcn.80046330` → read the file (a0 = path buffer `sp+0x10`, a1 = DATbase dest); returns
    bytes read.
  - resource-type flags `0x614(gp)` select a sub-handler (`0x8003d330+`: bits 0 / 6–7 branch to
    `0x8003d394/3a8/3bc/3d0…`).
  - `0x8003d568 jal fcn.8001cdc0` → **parse this DAT** (a1 = filesize); cursor advances past it + parser output.
- **Filename tables in the executable:**
  - VA `~0x8001ae00`: `level1.raw`,`level2.raw`,…,`level.raw`, `level1.dat`,`level2.dat`,`level3.dat`,`level.dat`,
    `gfx\*.raw`, `fmv\fmv.bin`; and (`~0x8001b170`) `level1.bin`,`level2.bin`,`level.bin`.
  - VA `~0x80082128`: `.all`,`.all`,`terr1`,`terr2`,`terr3`,`terrain`,`level`,…`.anm`; plus `bits\plantter.all`,
    `bits\memory.bin`.

**CORRECTION to a G18 statement (important):** G18 wrote "parser `fcn.8001cdc0` is called **once**
→ LEVEL.DAT parsed once." That is a **single static call site**, not a runtime guarantee — the call site
lives inside `fcn.8003cf2c`, which has **4 callers** and is a per-resource dispatcher, so the parser
**executes once per DAT loaded** and can run multiple times per level. Consequently a **second parsed DAT**
(e.g. LEVEL1.DAT) loaded after LEVEL.DAT would be relocated against **its own** heap base and its payload
pointers would land in the `0x801bxxxx` region — exactly where the floor `0x801bdc58` lives. G18's other
facts hold (the floor is **not** in the LEVEL.DAT image at `0x801607f8`; all of *that* DAT's 1248 reloc
targets are `< 0x4f32c`). What changes is the **source hypothesis** (§5).

## 5. Floor-source hypotheses (ranked)

### H1 (LEADING) — the floor is a SECOND parsed DAT (`LEVEL1.DAT` and/or `LEVEL2.DAT`)
- **Direct evidence:** a read-only payload scan of LEVEL1.DAT / LEVEL2.DAT finds many **wide-flat
  floor-signature** payloads in the **exact** `{u32 count; Vertex stride 0xc (pad=0); cmd stream}` format,
  whereas LEVEL.DAT's payloads are walls/grass/decor:

  | file | floor-signature payloads (flat `<0.6`, footprint `≥2000`) | examples (file off / cnt / X / Y / Z / flat) |
  |------|-----------------------------------------------------------|----------------------------------------------|
  | LEVEL1.DAT | **18** | `0x27dc` 68 `X4022 Y98 Z4052` flat 0.02 · `0x34c0` 48 `X3557 Z3568` 0.03 · `0x3930` 60 0.03 · several `Y=0` planes (`0x44dc`,`0x46a8`,…) |
  | LEVEL2.DAT | **73** | `0x1268c` 304 `X5005 Z18000` flat 0.10 · `0x0a3e8` 282 0.19 · `0x0bf50` 409 0.21 · `0x1a78c` 169 0.15 |

- **Format match:** parser-format DAT payloads are natively in the `fcn.80010000` format → **no converter
  needed**; the emitter loads `a0=[s2+0x1c]` with no base add because the parser already relocated it
  (G18 §3.2) — works identically for a second DAT relocated against its own base.
- **Loader match:** the engine has a multi-DAT loader (§4); `level.dat/level1.dat/level2.dat/level3.dat`
  are in the filename table and `LEVEL1.DAT`/`LEVEL2.DAT` ship in the LEVEL01 directory.
- **This reframes the floor as editable in principle** — in a *different* DAT than the one G12–G18 edited —
  **once the loader trace (§7) pins which DAT + offset.** (Do not patch yet; nothing is pinned.)

### H2 (ALTERNATE) — runtime conversion of `TERRAIN.ALL` / `TERR1.ALL`
- The `.ALL` files are s16 (x,z) coordinate streams (terrain mesh data) that would be **converted/decompressed
  at runtime** into the payload format and emitted. Possible, but **weaker** than H1: it requires an unproven
  converter, and the data is **not** natively in the emitter format (unlike the parsed DATs). Keep as a
  fallback.

### H3 (LESS LIKELY) — decompressed `LEVEL.RAW`/`LEVEL1.RAW`
- The `.RAW` files are compressed; decompressed output *could* contain payloads, but there is no evidence
  they decompress to the `fcn.80010000` format, and `.RAW` more commonly holds VRAM/texture or scenery data.
  Lowest priority.

## 6. Why the exact file+offset is NOT pinned statically (UNKNOWN, honestly)
The floor sits `0x7248` past the simple heap cursor `0x801b6a10` (G3). But testing the three plausible
second-DAT bases against LEVEL1.DAT and LEVEL2.DAT, **none** makes `0x801bdc58` land on a clean payload
`count`:

| assumed 2nd-DAT base | floor file offset | LEVEL1.DAT `u32@off` | LEVEL2.DAT `u32@off` |
|----------------------|------------------:|----------------------|----------------------|
| `0x801b1c10` (LEVEL.DAT EOF) | `0xc048` | `0x178b0b6f` (not a count) | `0xf560` (62816, not a count) |
| `0x801b5890` (pass-1 written end) | `0x83c8` | `0x1d13ed3d` | `0x370fd28` |
| `0x801b6a10` (reserved end / cursor) | `0x7248` | `0xc778c778` | `0x383535` |

So the second parsed DAT does **not** load at the naive cursor — **something loads between** LEVEL.DAT's
output and the next parsed DAT (another resource, or sector/heap alignment shifts the base). The exact base
cannot be derived from one runtime address. **This is precisely what the loader trace resolves** — and it is
deterministic, unlike re-hitting `a0`.

## 7. Proposed narrow runtime check (NO `a0=0x801bdc5c` reproduction needed)

Goal: log **(filename → load base, size)** for every resource loaded during LEVEL01 entry, so the resource
whose `[base, base+size)` contains `0x801bdc58` is identified (and `floor offset = 0x801bdc58 − base`). This
fires **deterministically at load**, every time — no camera/draw-order/`a0` dependence, no F5 grinding.

**Primary — DAT load/parse log (two execute breakpoints, fired at load):**
1. Boot the **pristine** image; **arm before/at LEVEL01 load** (the resources load during the loading screen).
2. **EXEC BP at `0x8003d550`** (`jal fcn.80046330`, the file read). At each hit record:
   - the **path string** at `a0` (= `sp+0x10` buffer) — the filename being loaded,
   - `a1` = **destination base** (DATbase for this resource),
   - `v0` after return = **bytes read** (size).
3. **EXEC BP at `0x8003d568`** (`jal fcn.8001cdc0`, the parse). At each hit record:
   - **DATbase = `[0x80082498]`** (this DAT's base), and `a1` = filesize.
   - 1st hit ⇒ `0x801607f8` / `0x51418` (LEVEL.DAT, expected). **2nd+ hit ⇒ the second parsed DAT's base
     `B2` and size `S2`.** If `B2 ≤ 0x801bdc58 < B2+S2`, **the floor is in that DAT** at offset
     `0x801bdc58 − B2`; cross-check that offset is a clean payload `count` in the corresponding file
     (LEVEL1.DAT or LEVEL2.DAT). The §2 file then names the floor resource.

**Alternative — write-watch on a stable next-resource base (no `a0`):**
- **WRITE watch `0x801b6a10`** (the first word of the "next resource" region) armed during LEVEL01 load. The
  breaking PC = the loader/copier that populates that region; read the **source pointer** it copies from
  (reveals the originating file/base) and whether it is the DAT file-read (`fcn.80046330`) or a
  converter/decompressor. (Broader than watching `0x801bdc58` itself, and it does not require the floor draw.)

**Outcome routing:**
- 2nd parse hits with `B2 ≤ 0x801bdc58 < B2+S2` and the offset is a clean payload ⇒ **H1 confirmed**; the
  floor is `LEVEL1.DAT`/`LEVEL2.DAT` at a known offset → a future single-s16 vertex edit becomes possible in
  **that** file (new tool, separate from the LEVEL.DAT tools).
- file-read loads a `.ALL` to a base ≤ `0x801bdc58` then a converter writes the payload ⇒ **H2**; the floor
  lives in `TERRAIN.ALL`/`TERR1.ALL`.
- the writer copies from a decompressed `.RAW` buffer ⇒ **H3**.

## 8. Guardrails / scope
No patch, no build. No DAT/CUE/BIN/RAM/save-state committed. Do **not** treat offsets past a DAT's EOF as
offsets into that DAT (each parsed DAT has its own base). Do **not** patch runtime-buffer addresses.
Collision/pathing **UNKNOWN** — visual floor ≠ collision floor. Do **not** resume grinding `EXEC 0x800108b4`
for `a0=0x801bdc5c`.

## 9. Reproduce (read-only)

```bash
# sidecar inventory + first-byte classification:
ls -l REBUILD/files/LEVEL01
python3 - <<'PY'
import struct
for f in ['LEVEL1.DAT','LEVEL2.DAT']:
    d=open('REBUILD/files/LEVEL01/'+f,'rb').read()
    print(f, 'reccount word0 =', struct.unpack_from('<I',d,0)[0])   # parser-format DATs
PY
# loader dispatch + call sites (carve text past the 0x800 PS-EXE header):
python3 -c "open('/tmp/abltext.bin','wb').write(open('SCUS_942.88','rb').read()[0x800:0x73000])"
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003cf2c -c 'pd 40' /tmp/abltext.bin   # dispatcher
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003d2f0 -c 'pd 44' /tmp/abltext.bin   # shared load+parse
# parser call sites (one static): jal fcn.8001cdc0 = bytes 70 73 00 0c ; loader fcn.8003cf2c has 4 callers
```
