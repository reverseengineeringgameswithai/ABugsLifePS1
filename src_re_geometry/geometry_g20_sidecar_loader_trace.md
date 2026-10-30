# G20 — sidecar resource loaders (non-circular floor-source tracing)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G19 resource source](geometry_g19_floor_resource_source.md) ·
[← G18 output-buffer trace](geometry_g18_output_buffer_floor_trace.md) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **STATIC LOADER MAP + RUNTIME-RUNBOOK PROPOSAL (2026-06-14).** Read-only `SCUS_942.88` disasm
(PS-EXE text carved at file `0x800`, VA `0x80010000`) + read-only sidecar file inspection. **No patch, no
build.** No collision/pathing claims — visual ≠ collision.

> **Headline:** the operator's loader trace (`0x8003d550`/`0x8003d568` each hit **once**, `a1=0x51418`)
> confirms the **LEVEL.DAT parse path only** — the parser `fcn.8001cdc0` runs **exactly once** for LEVEL01.
> This **refutes G19's leading hypothesis H1** (floor = a *second parsed DAT* via the same parser) and
> re-vindicates G18's empirical "parser once." The floor must therefore come from a **different, non-parser
> loader**. Static mapping finds it: a **post-DAT sidecar terrain loader** — `fcn.8002ffa8` builds
> `<name>.all` filenames and file-reads `TERRAIN.ALL`/`TERR1.ALL` into the **heap cursor** region (where the
> floor `0x801bdc58` lives), then `fcn.8002fce8` converts the s16 coordinate stream into geometry. The
> operator never watched this path. **H2 (terrain `.all` → generated floor) is now the LEADING hypothesis.**

## 0. ⚠ G21 CORRECTION (2026-06-14) — the terrain `.all` runbook below did NOT fire

The §7 runbook was run: `EXEC 0x8002ffe4` and `EXEC 0x80030dc0` each hit **0** times during LEVEL01 load. So
this doc's claim that the terrain `.all` loader is the **"prime non-circular target"** and that **H2 is
leading** is **NOT confirmed** and is **downgraded**: terrain `.all` is a candidate that *did not fire* —
because (a) the orchestrator `fcn.8005d654` **skips the file-read when the terrain is already resident**
(`0x8005d76c bnez v0,0x8005d794` → calls `fcn.8002fce8` directly), and/or (b) the terrain loads in a
different phase. The loader/processor/orchestrator **addresses** in this doc remain valid; only the
"prime/confirmed" framing and the file-read-site runbook are wrong. The corrected instrument is the **callee
entry** `EXEC 0x80046330` (catches all loads regardless of call site/caching), plus a new PRIME suspect — the
**indirect high-heap loader `fcn.8003a318`** (`0x801cc390 − size`). Full map + runbook:
[geometry_g21_file_read_caller_map.md](geometry_g21_file_read_caller_map.md).

**G22 RESULT (2026-06-14): floor source = `LEVEL.RAW`, NOT the terrain `.all`.** The `EXEC 0x80046330`
runbook's Hit #4 (`ra=0x8003a390` = `fcn.8003a318`) loaded **LEVEL.RAW** to `0x80115aac` (dest-size `0xb68e4` =
LEVEL.RAW's exact size), bracketing the floor `0x801bdc58` at offset `0xa81ac`. So the floor comes from
**LEVEL.RAW** (processed/converted at runtime — `LEVEL.RAW[0xa81ac]` is an indexed-geometry stream, not a
verbatim payload), **not** the `TERRAIN.ALL`/`TERR1.ALL` loader this doc explored (which never fired). The
loader/processor/orchestrator addresses here remain valid for the `.all` terrain subsystem, but the **walkable
floor's resource is LEVEL.RAW**. Detail: [geometry_g22_high_heap_floor_source.md](geometry_g22_high_heap_floor_source.md).

## 1. Loader-trace result (operator, 2026-06-14) — CONFIRMS LEVEL.DAT ONLY

| breakpoint | hits during "Loading Level…" | observed |
|------------|------------------------------|----------|
| `EXEC 0x8003d550` (DAT file-read `jal fcn.80046330`) | **once** | reads `LEVEL.DAT` to DATbase `[0x80082498]` |
| `EXEC 0x8003d568` (DAT parse `jal fcn.8001cdc0`) | **once** | `a1 = 0x00051418` = LEVEL01/LEVEL.DAT size |

No further hits before gameplay / after Press X.

**Conclusion (CONFIRMED):** the parser `fcn.8001cdc0` executes **exactly once for LEVEL01** (LEVEL.DAT only).
This is decisive against G19's H1: **the floor is NOT a second parsed DAT** loaded via `fcn.8001cdc0`. The
4-caller dispatcher `fcn.8003cf2c` exists, but for LEVEL01 only the LEVEL.DAT case fires the parse.
(`LEVEL1.DAT`/`LEVEL2.DAT` may belong to other areas/states or load via a non-parse path; they are no longer
the leading floor candidate.) Stepping further into this path = **circular** (it re-derives the known parser),
so G20 looks elsewhere.

## 2. The 14 file-read (`fcn.80046330`) call sites — what each loads (CONFIRMED disasm)

`fcn.80046330(a0 = path string, a1 = destination base) → bytes read`. Mapping each site by its `a0`/`a1`
setup (filename strings resolved from the executable):

| file-read site | filename source (`a0`) | destination (`a1`) | role | operator watched? |
|----------------|------------------------|--------------------|------|-------------------|
| `0x8003d550` | `sp+0x10` built from level table | **DATbase `[0x80082498]`** | **LEVEL.DAT parse path (KNOWN)** | **YES** (1 hit, `0x51418`) |
| `0x8003d310` | `0x8001adfc` = `bits\memory.bin` | `0x800b5788` | memory-layout descriptor | no |
| `0x8003f5d0` | `0x8001adfc` = `bits\memory.bin` | `0x800b5788` | memory.bin (other caller) | no |
| `0x8003e7fc` | `0x8001ae6c` = `fmv\fmv.bin` | `0x800b5788` | FMV | no |
| `0x8003f578` | `0x8001ae6c` = `fmv\fmv.bin` | `0x800b5788` | FMV (other caller) | no |
| `0x8003d638` | (fixed) | `0x800b39a0` | small fixed-buffer load | no |
| **`0x8002ffe4`** | `sp+0x10` built **`.all`** (`0x80082128`) | **`[s0]` heap dest** | **TERRAIN `.all` loader (`fcn.8002ffa8`)** | **NO ← prime** |
| **`0x80030dc0`** | `sp+0x10` built **`.all`** (`0x80082130`) | **`[s0]` heap dest** | **TERRAIN `.all` loader (variant)** | **NO** |
| `0x80042f58` | `sp+0x10` built **`.vb`** (`0x800821b0`) | `s0+0x800b5790` | audio VAB body | no |
| `0x80042f20` | (fixed) | `0x800972a8` | audio | no |
| `0x8005d6ec` | `sp+0x10` built **`.anm`** (`0x800821f8`) | `[s2]` | animation | no |
| `0x8003a388` | (set via `0x8004589c`) | **`~0x801cc390 − size`** (HIGH HEAP) | high-heap streamed load | no |
| `0x80055d98` | (fixed) | `0x80095398` | fixed-buffer load | no |
| `0x800310c8` | `0x8001aaec` (pointer table, not a string) | `[s0]` | non-filename call | no |

**The operator watched only the DAT path.** Every other site bypasses `fcn.8001cdc0` entirely — so any of
them is a non-circular candidate. The strongest are the **terrain `.all` loaders** (heap destination, in the
floor region) and the **high-heap loader `0x8003a388`** (dest `~0x801cc390`, between the floor payload
`0x801bdc58` and the floor GPU packets `~0x801e5xxx`).

## 3. The terrain `.all` loader path (LEADING floor-source candidate, CONFIRMED disasm)

```
fcn.8005d654  (terrain/sidecar resource-load loop, frame -0x140, 16 callers          <- orchestrator
               0x8005dc58, 0x8005e274 + 0x90*i .. 0x8005ea50; indexes object table 0x800a6300)
   └─ fcn.8002ffa8  (a2=&dest; builds "<name>.all" via fcn.8005f76c + fcn.8005f74c[".all"@0x80082128])
        ├─ 0x8002ffe4  jal fcn.80046330(a0=sp+0x10 filename, a1=[s0]=dest)   <- terrain file-read
        └─ 0x8002fff0  jal fcn.8002fce8(a0=s1, a1=s0)                        <- terrain PROCESSOR
   (orchestrator then: [s1] += returned size  -> advances a HEAP CURSOR; checks a 0x4c-stride record's
    type field == 0xc at 0x80098a8a)
```

- **`fcn.8002ffa8`** appends `.all` (name table `0x80082128`=`.all`, `0x80082138`=`terr1`, `0x80082140`=`terr2`,
  `0x80082148`=`terr3`, `0x80082150`=`terrain`) → loads `TERR1.ALL` / `TERRAIN.ALL` to `[s0]`, then calls the
  processor.
- **`fcn.8002fce8`** = terrain processor: walks the loaded `.all` stream (`[t1]` cursor, `+4` header then a
  word count), builds **stride-`0x4c`** records into globals `0x80098a8a`/`0x8009ee5c` (a per-cell terrain
  table), threshold `0x100`, type field compared to `0xc`. (It writes the **index/record table** to fixed
  globals — the renderable mesh is generated from these + the heap-resident `.all` coordinate data.)
- **`fcn.8005d654`** orchestrator loads each terrain slot into a **heap cursor `[s1]`** and advances it by the
  returned size — the same heap-cursor allocation pattern LEVEL.DAT used (cursor was at `0x801b6a10` after the
  DAT, §G3), so the terrain `.all` data lands in the **`0x801bxxxx` region where the floor `0x801bdc58`
  lives.** This is the key linkage the LEVEL.DAT-only trace missed.

### Why this is NOT the known LEVEL.DAT path
- Different file (`*.ALL`, built from the `terr/.all` name table `0x80082128`+), different file-read site
  (`0x8002ffe4`/`0x80030dc0`, not `0x8003d550`), and it calls **`fcn.8002fce8`**, **not** the parser
  `fcn.8001cdc0`. So watching it cannot re-derive the LEVEL.DAT parser; it is a genuinely separate path.

### Why the floor is GENERATED, not a verbatim `.all` offset (CONFIRMED bytes)
- `TERRAIN.ALL` (`0x39d8c`) / `TERR1.ALL` (`0xf078`) begin with s16 `(x,z)` coordinate pairs + sub-header
  `01 00 02 00`; a payload-shape scan finds **0** wide-flat floor payloads in TERRAIN.ALL and only 2 tiny
  ones at the tail of TERR1.ALL; offset `0x7248` is **not** a clean payload `count` in either. So the `.all`
  data is **not** in the `fcn.80010000` `{u32 count; Vertex 0xc; cmds}` format — the floor mesh is
  **converted/generated at runtime** from the `.all` coordinate stream (consistent with "runtime-generated
  heap floor geometry"; the exact file→`0x801bdc58` byte map is therefore not a static offset).

## 4. Other dispatch tables / name references (CONFIRMED)
- **`fcn.8003cf2c`** resource-id dispatcher — jump table VA **`0x8001afb0`** (17 handlers, ids 1–17), 4
  callers (`0x8003f544`/`0x800503cc`/`0x80052290`/`0x8005b830`); the DAT case is the only one that parses.
- **`fcn.8005d654`** terrain/sidecar loop — **16 callers** (`0x8005dc58`, `0x8005e274`+`0x90·i`…`0x8005ea50`),
  indexes object table `0x800a6300`.
- **Filename tables:** VA `~0x8001ae00` = `level/level1/level2/level3 ×.dat/.raw/.bin`, `gfx\*.raw`,
  `fmv\fmv.bin`; VA `~0x80082128` = `.all`,`terr1`,`terr2`,`terr3`,`terrain`,`.vh`,`.vb`,`.anm`,`level`,
  `level0`; `0x8001adfc`=`bits\memory.bin`; `0x8001acec`=`bits\plantter.all`.

## 5. Candidate memory bases / sizes (CONFIRMED addresses; roles LIKELY)
| region | role | confidence |
|--------|------|-----------|
| `0x801607f8 .. 0x801b1c10` | LEVEL.DAT image | CONFIRMED |
| cursor `0x801b6a10` after DAT parse | next-resource heap base | CONFIRMED (G3) |
| **`0x801bdc58`** = cursor `+0x7248` | **floor payload (runtime-generated)** | OBSERVED ONCE |
| `~0x801cc390` | high-heap streamed-load dest (`0x8003a388`) | CONFIRMED addr / role UNKNOWN |
| `~0x801e5xxx` | floor GPU/OT packets (`s3` in the Candidate B log) | CONFIRMED (G18) |
| `0x80098a8a` / `0x8009ee5c` | terrain `0x4c`-stride record tables (`fcn.8002fce8`) | CONFIRMED write / role LIKELY |
| `0x800b5788` | memory.bin / FMV load buffer | CONFIRMED |
| `0x800972a8` / `0x80095398` / `0x800b5790` | audio / fixed buffers | CONFIRMED addr |

## 6. Floor-source hypotheses (re-ranked after the loader trace)
- **H2 (NOW LEADING)** — the floor is **generated from the terrain `.all` resource** (`TERRAIN.ALL`/`TERR1.ALL`)
  by the `fcn.8002ffa8` loader + `fcn.8002fce8` processor (+ a per-frame tessellator), loaded into the heap
  cursor region where `0x801bdc58` sits. Best fit: heap destination, runtime generation (the `.all` data is a
  coordinate stream, not a verbatim payload), and the operator's trace ruled out the parse path.
- **H1 (REFUTED)** — second parsed DAT via `fcn.8001cdc0`. The loader trace shows the parser runs once.
- **H3 (OPEN, lower)** — decompressed `LEVEL.RAW` (compressed magic `00 00 83 0c`); its load site is not yet
  tied to the heap region. The high-heap loader `0x8003a388` (dest `~0x801cc390`) is a candidate to check.

## 7. Recommended next runbook — ONE deterministic check (no `a0` reproduction)

**Watch the terrain `.all` loader file-read.** It fires deterministically when LEVEL01 loads its terrain,
identifies the file and destination, and brackets whether the floor `0x801bdc58` is inside the loaded region —
without reproducing the floor draw and without re-entering the LEVEL.DAT parser.

```
Pristine image. Arm before/at "Loading Level…".

EXEC 0x8002ffe4        (terrain .all file-read inside fcn.8002ffa8)
  also arm: EXEC 0x80030dc0   (the sibling .all loader variant)
At each hit record:
  PC
  a0  -> read the C-string at a0 (= sp+0x10): the built filename, expect "terr1.all" / "terrain.all"
  a1  -> destination base
  s0, s1, s2, ra      (s0 = dest struct; ra = caller for context)
  then STEP OVER the jal (one instr past return) and read v0 = bytes read (size)

Decide: if  a1 <= 0x801bdc58 < a1 + size   -> the floor lives in THIS terrain file;
        floor offset within it = 0x801bdc58 - a1  (NOT a LEVEL.DAT offset).
Then (optional, same session) EXEC 0x8002fce8 (a0=s1,a1=s0) to watch the conversion, and read the
record-table base it writes (0x80098a8a) to map cell -> mesh.
```

**Why narrow/deterministic:** one (two) execute breakpoints at file-load time; no RAM dump; no F5 grind for
`a0=0x801bdc5c`; not the LEVEL.DAT parser. If neither terrain read brackets `0x801bdc58`, the fallback is the
high-heap loader **`EXEC 0x8003a388`** (record `a0` filename, `s0`=dest `~0x801cc390`, size) — the only other
file-read with a heap-region destination.

**Alternative (if DuckStation range-watches are clean):** a WRITE watch on a small **stable** word a little
below the floor, e.g. the next-resource base `0x801b6a10` (not `0x801bdc58` itself), armed during load — the
breaking PC is the loader/copier that populates the region; read the source pointer it copies from.

## 8. Guardrails
No patch, no build. No DAT/CUE/BIN/RAM/save-state committed. Each parsed DAT has its own base — do not treat
offsets past a DAT's EOF as offsets into it; the floor offset (if found) is relative to the **terrain file**
base, not LEVEL.DAT. Do not patch runtime-buffer addresses. Collision/pathing **UNKNOWN** — visual ≠ collision.
Do not resume `EXEC 0x800108b4` for `a0=0x801bdc5c`, and do not step further into the LEVEL.DAT parse.

## 9. Reproduce (read-only)
```bash
python3 -c "open('/tmp/abltext.bin','wb').write(open('SCUS_942.88','rb').read()[0x800:0x73000])"
# the 14 file-read sites: jal fcn.80046330 = bytes cc 18 01 0c
# terrain loader + processor:
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8002ffa8 -c 'pd 24' /tmp/abltext.bin   # fcn.8002ffa8 .all loader
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8002fce8 -c 'pd 40' /tmp/abltext.bin   # fcn.8002fce8 processor
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8005d654 -c 'pd 80' /tmp/abltext.bin   # fcn.8005d654 orchestrator
# name tables: 0x80082128 ".all"/terr*/terrain ; 0x8001ae00 level*.dat/raw/bin
```
