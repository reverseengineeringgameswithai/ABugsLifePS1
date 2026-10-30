# G18 — output-buffer floor payload trace (`0x801bdc58`)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G17 floor candidates](geometry_g17_floor_payload_candidates.md) ·
[← G16 screen-space selection](geometry_g16_screen_space_vertex_selection.md) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **STATIC ISO TRACE + RUNTIME RUNBOOK (2026-06-14).** Read-only `SCUS_942.88` disasm + read-only
file inspection. **No patch, no build.** No collision/pathing claims — visual floor ≠ collision floor.

> **⚠ G26 CORRECTION (2026-06-15) — the premise of this doc is RETRACTED.** This doc traces "the output-buffer
> floor payload `0x801bdc58`", inherited from G17 Candidate B. Operator ground truth: at `Press X to Continue`
> `[0x801bdc58] = 0x70d4001a` (= `LEVEL.RAW[0xa81ac]`, compressed source) and a **WRITE watch `0x801bdc58` during
> load = 0 hits** → `0x801bdc58` is **compressed LEVEL.RAW source**, never an `fcn.80010000` payload. So
> `0x801bdc58` is **not** a floor payload to trace. What **survives** from this doc (independent facts, still
> CONFIRMED): parser `fcn.8001cdc0` runs once; all 1248 LEVEL.DAT reloc targets `< 0x4f32c`; the emitter loads `a0`
> directly from `[s2+0x1c]`/`[s2+0x20]` (no base add). What is **dropped**: that `0x801bdc58` is the (or any) floor
> render payload. The real floor payload pointer is **UNKNOWN** — re-find from the consumer side with count
> validation: [geometry_g26_floor_payload_reaudit.md](geometry_g26_floor_payload_reaudit.md).

## 0. Why G18 exists

G17 Candidate B (operator runtime log, EXEC `0x800108b4`, broad walkable floor view, Flik centered) found
the emitted floor/top-surface payload at runtime **`a0 = 0x801bdc5c` → payload base `0x801bdc58`**. That
address is **past the loaded LEVEL.DAT** and **past the parser output buffer**, so it is **not** a direct
LEVEL.DAT-backed payload. G18 traces where `0x801bdc58` comes from.

## 1. G17 Candidate B runtime result (17 hits, all one payload)

EXEC `0x800108b4` (`fcn.80010000` packet-store gate, past all RTPS/RTPT/NCLIP/AVSZ4 rejects). At this PC:
`a0` = vertex-table pointer ⇒ **payload base = `a0 − 4`**; `s3` = GPU packet/output pointer advanced by
`0x34`. **All 17 hits had identical `a0 = 0x801bdc5c`** (one floor surface emitting 17 primitives):

| hit | s3 (packet) | Δ from prev | note |
|----:|-------------|------------:|------|
| 1 | `0x801e5414` | — | |
| 2 | `0x801e5448` | `+0x34` | |
| 3 | `0x801e547c` | `+0x34` | |
| 4 | `0x801e54b0` | `+0x34` | |
| 5 | `0x801e54e4` | `+0x34` | |
| 6 | `0x801e5684` | `+0x1a0` | gap (other prims interleaved) |
| 7 | `0x801e56b8` | `+0x34` | |
| 8 | `0x801e56ec` | `+0x34` | |
| 9 | `0x801e5720` | `+0x34` | |
| 10 | `0x801e58f4` | `+0x1d4` | gap |
| 11 | `0x801e5928` | `+0x34` | |
| 12 | `0x801e595c` | `+0x34` | |
| 13 | `0x801e5990` | `+0x34` | |
| 14 | `0x801e59c4` | `+0x34` | |
| 15 | `0x801e59c4` | `+0x00` | duplicate register state vs prior screenshot |
| 16 | `0x801e59f8` | `+0x34` | |
| 17 | `0x801e5b98` | `+0x1a0` | gap |

Fixed for all 17 hits:

| field | value |
|-------|-------|
| PC | `0x800108b4` |
| `a0` | `0x801bdc5c` |
| payload base (`a0 − 4`) | `0x801bdc58` |
| raw DAT offset (`a0−4 − DATbase`) | `0x5d460` |
| valid DAT offset? | **NO** (`0x5d460 > 0x51418` EOF) |
| output base (DATbase + filesize) | `0x801b1c10` |
| output-buffer offset (`a0−4 − 0x801b1c10`) | `0xc048` |

**Classification (recorded):**
```
EMITTED FLOOR/TOP-SURFACE CANDIDATE /
RUNTIME-GENERATED OR OUTPUT-BUFFER PAYLOAD /
DAT SOURCE UNKNOWN
```
Collision/pathing **UNKNOWN** — do not infer.

## 2. The output-buffer / DAT-EOF correction (CONFIRMED)

| address | meaning | source |
|---------|---------|--------|
| `0x801607f8` | DATbase (LEVEL.DAT load base) | CONFIRMED (live RAM) |
| `0x801b1c10` | DAT EOF = DATbase + filesize (`0x51418`); = pass-1 output base | CONFIRMED (G3) |
| `0x801b5890` | pass-1 `ParserOutputRecord20[484]` end (`+0x3c80`) | CONFIRMED (G3) |
| `0x801b6a10` | parser reserved end (`+0x4e00` = (484+140)<<5); heap cursor → next resource | CONFIRMED (G3) |
| **`0x801bdc58`** | **floor payload base** = EOF `+0xc048` = reserved-end `+0x7248` | CONFIRMED (this log) |

So the floor payload is **`0x7248` into the "next resource" heap region** that loads *after* the LEVEL.DAT
parser output. It is **not** the DAT, **not** the pass-1 matrix output buffer, and **not** the reserved
gap. Treating `0x5d460` as a DAT offset is invalid (guardrail).

## 3. Static trace — how `fcn.80010000` receives the payload pointer (CONFIRMED)

### 3.1 The parser runs once; all relocation targets stay inside the DAT
- `jal fcn.8001cdc0` appears at **exactly one** call site (`0x8003d568`, in `fcn.8003cf2c`) → LEVEL.DAT is
  parsed once. There is **no second parse** producing heap-resident source records.
- All **1248** LEVEL.DAT relocation targets lie in `[0x45f0, 0x4f32c]` (`tools/dat_reloc.py`, G1). The max
  target `0x4f32c` is `0xe134` **below** the floor's `0x5d460`. So **no parser-relocated pointer can equal
  `0x801bdc58`.** CONFIRMED.

### 3.2 The emitter loads the payload pointer directly from the source record (no base added)
`fcn.80010000`'s only real caller is the shared emitter tail `0x80020698` (`jal fcn.80010000`); the other
`/x 0040000c`/`00400008` byte hits are mis-aligned coincidences. Ten dispatch cases funnel into it
(`j 0x80020698` @ `0x8001ec3c/eff8/f1ac/f4c4/fd14/fd24/20104/20320/20330/20688`). The pointer load:

```
0x80020668  lw   v0, 0x6a8(gp)        ; v0 = geometry loop count  [0x80082440]
0x80020670  sll  v0, v0, 2
0x80020674  slt  v0, s0, v0           ; s0 = per-object index
0x80020678  beqz v0, 0x80020690       ; if !(s0 < count<<2) -> use +0x20
0x80020684  lw   a0, 0x1c(s2)         ; a0 = [source+0x1c]  (payload pointer)   <-- no base add
0x80020690  lbu  a2, 0x18(s2)
0x80020694  lw   a0, 0x20(s2)         ; a0 = [source+0x20]  (alt payload pointer) <-- no base add
0x80020698  jal  fcn.80010000         ; a0 = payload base
```

`a0` is taken **verbatim** from `[s2+0x1c]` or `[s2+0x20]` — **no `addu DATbase`**. So the source-record
field already holds the **absolute** payload address. (Builder case `0x8001ec44`, the G16 wall path, sets
its own `a0 = [s2+0x1c]` at `0x8001eff4` then `j 0x80020698` — same shape.)

### 3.3 Consequence (CONFIRMED logic)
For the floor, `[s2+0x1c]` (or `[s2+0x20]`) = `0x801bdc58` (heap). Two ways that field can hold a heap
address:
1. **`s2` is a DAT source record whose payload field was written at runtime** by a generator (the parser
   left it un-relocated — note `+0x20` / SITE E requires flag `0x20`, which is **never set in LEVEL01**, so
   the parser never touches it; a runtime step could fill it), **or**
2. **`s2` itself is a heap-resident structure** built by a runtime generator (not a DAT source record).

Either way, **the floor payload pointer is established after the parse, by runtime code — not by LEVEL.DAT
relocation.** CONFIRMED that it is not parser-produced; which of (1)/(2) is **UNKNOWN** (needs one runtime
read of `s2` — §5).

## 4. Where the floor data comes from (LIKELY) — separate LEVEL01 terrain resources

LEVEL01 ships dedicated resources beyond `LEVEL.DAT`, and the executable references them by name:

| file | size | first bytes | shape |
|------|-----:|-------------|-------|
| `LEVEL.DAT` | `0x51418` | `0b 00 00 00` (rec count) | the parsed object/geometry DAT (walls/grass/props) |
| `LEVEL.RAW` / `LEVEL1.RAW` | `0xb68e4` / `0x84210` | `00 00 83 0c …` | raw blob (level mesh/scenery) |
| `TERRAIN.ALL` | `0x39d8c` | `b6 b2 01 00 / 01 00 02 00 / a9 fe 77 01 …` | **s16 coordinate-pair stream → terrain mesh** |
| `TERR1.ALL` | `0xf078` | `cc 6c 00 00 / 01 00 02 00 / e1 fe 2a 01 …` | **s16 coordinate-pair stream → terrain mesh** |

Executable strings: `level.dat`/`level1.dat`/…, `level.raw`/`level1.raw`/…, `bits\plantter.all`, `terr1`,
`.all`. So the game loads `LEVEL.DAT` **and** a `.raw`/`.all` terrain resource into the heap. The
"next resource" region (`0x801b6a10+`, where the floor payload `0x801bdc58` lives) is exactly where such a
resource lands after the parser output.

`TERRAIN.ALL`/`TERR1.ALL` start with s16 coordinate pairs (e.g. `0x0177fea9` = `(−343, 375)`), i.e. terrain
mesh data — but **not** in `fcn.80010000`'s `{u32 count; Vertex stride 0xc; cmd stream}` payload format
(`TERRAIN.ALL` word0 `0x1b2b6` is far too large to be a `0xc`-stride vertex count). So a runtime step
**converts/decompresses** the terrain resource into the `fcn.80010000` payload format in the heap, then
points a source-record field at it. This matches the "runtime-generated output-buffer payload"
classification. **LIKELY**; the exact resource + generator is **UNKNOWN** until the runtime trace (§5)
identifies the writer.

(Note: this also explains every prior negative result — G12–G16 edited LEVEL.DAT payloads, which are
walls/grass/props; the **walkable floor is not in LEVEL.DAT**, so no LEVEL.DAT vertex edit could move it.)

## 5. Recommended next step — narrow runtime writer/source trace (DAT source NOT found)

The DAT source is **not** found (and cannot be, by §3): the floor payload is heap/runtime, not a LEVEL.DAT
offset. So **do not** attempt a LEVEL.DAT one-coordinate floor edit. One narrow runtime check, two cheap
reads in the same session:

**Primary — WRITE watch to catch the generator/writer:**
1. Boot the **pristine** image; enter LEVEL01; reach the Candidate B floor view (or just complete the load
   — the payload is built during/just after load).
2. Set a **WRITE watch on `0x801bdc58`** (the payload count word) — ideally armed **during LEVEL01 load /
   before gameplay**, since the buffer is likely populated at load time. The breaking PC = the
   **generator/writer**; record PC, the writing function, and the source register/pointer it copies from
   (which should reveal the originating resource, e.g. a `LEVEL.RAW`/`.ALL` base + offset).
3. If the write happens before the watch can arm, instead WRITE-watch a **later** word of the payload
   (e.g. `0x801bdc58 + 4` first vertex) or set an **execute** breakpoint inside the conversion routine once
   §`5`-disambiguator (below) reveals it.

**Disambiguator — read `s2` at the emitter (resolves §3.3 case 1 vs 2), same session:**
4. Set an EXEC breakpoint at **`0x80020684`** (or `0x80020698`) conditioned on `a0 == 0x801bdc5c`; when it
   breaks, read **`s2`**:
   - `s2 < 0x801b1c10` → `s2` is a **DAT source record** whose `+0x1c`/`+0x20` was runtime-written to the
     heap payload (case 1); then `DAT off = s2 − 0x801607f8` gives the **DAT source row to inspect** (its
     other fields — vec/scale/angle — *are* DAT-editable even though the payload is not).
   - `s2 ≥ 0x801b1c10` → `s2` is a **heap-resident** structure (case 2); the whole object is generated.
   - Also read `[s2+0x1c]`/`[s2+0x20]` to confirm which field holds `0x801bdc58`, and `[s2+0x18]` (attr).

**Outcome routing:**
- If the writer copies from a `LEVEL.RAW`/`TERRAIN.ALL`/`TERR1.ALL` base, the **floor lives in that file**
  → a future safe edit target is one s16 coordinate **in that terrain file** (new patch tool, separate
  from the LEVEL.DAT tools), not in LEVEL.DAT.
- If `s2` is a DAT source record (case 1), a future test could edit that DAT source row's **transform**
  fields (vec/scale/angle) to move/scale the whole floor object — but **not** its payload vertices (heap).

Collision/pathing remains **UNKNOWN** throughout — visual floor ≠ collision floor; do not infer.

## 5b. A SECOND, DAT-backed "Candidate B-like" log — instanced decor `0x2d460` (DO NOT MERGE)

The operator later moved **very close** to the Candidate B walkable-floor view (not guaranteed
pixel-identical) and re-ran EXEC `0x800108b4`. That separate log captured a **different** payload —
**DAT-backed**, not the heap floor of §1:

| log | runtime payload base | `−DATbase` | valid DAT? | payload |
|-----|----------------------|-----------:|------------|---------|
| **exact Candidate B (§1)** | `0x801bdc58` | `0x5d460` | **NO** (heap, past EOF) | the **walkable floor** (output-buffer/heap) |
| **Candidate B-LIKE (new)** | `0x8018dc58` | **`0x2d460`** | **YES** | **instanced decor/prop**, not the floor |

The runtime bases differ in one hex digit (`0x801b…` vs `0x8018…`) and point to entirely different payloads.
**Keep the two logs separate.** Static decode of `0x2d460` (full record:
[geometry_g18_dat_backed_floor_candidate.md](geometry_g18_dat_backed_floor_candidate.md)): count 25,
footprint 202×107×194, flatness 0.53, all 25 verts referenced, and **93 pass-1 source records point at it**
→ **heavily instanced decor/prop, NOT the walkable floor** (operator's runtime-only "floor candidate" read
superseded). So even the DAT-backed payload in the near-floor view is scattered decoration sitting on the
floor — **the walkable floor itself is still the heap payload `0x801bdc58`, not in LEVEL.DAT.** No floor edit
target; no build. The §5 runtime writer/source trace for `0x801bdc58` remains the next step.

## 5c. Reproducibility status + G19 pivot (2026-06-14)

`a0=0x801bdc5c` / payload `0x801bdc58` is now classified **OBSERVED ONCE / STRONG BUT NOT REPRODUCIBLE /
DAT SOURCE UNKNOWN.** It appeared in one broad-floor camera/draw-order state; near-identical views emit the
DAT decor `0x2d460` instead (§5b), and DuckStation's GUI has **no conditional breakpoint**
(`EXEC 0x800108b4 if a0==0x801bdc5c`), so re-hitting the exact pointer by F5 is too fragile to be a workflow.
**Stop grinding for it.**

The §5 writer/source runbook (WRITE-watch `0x801bdc58`) is **superseded** as the primary step by the **G19
resource-side pivot**: instead of reproducing the draw, identify the floor **resource/source** and the
**loader** that lands it in the heap. Key G19 findings (full detail
[geometry_g19_floor_resource_source.md](geometry_g19_floor_resource_source.md)):
- LEVEL01 ships **two more parser-format DATs** — `LEVEL1.DAT` (`0x1a568`) and `LEVEL2.DAT` (`0x40784`) —
  that **contain wide-flat floor-signature payloads** in the exact `fcn.80010000` format (LEVEL.DAT does not).
- The loader `fcn.8003cf2c` is a **resource-id dispatcher with 4 callers**; the parser `fcn.8001cdc0` (single
  static call site) executes **once per DAT loaded**, not once total. **CORRECTION:** this doc's §3.1
  ("parser called once → no second-parse heap source records") was a static-call-site statement; at runtime a
  **second parsed DAT** is relocated against its own heap base and its payloads land in the `0x801bxxxx`
  region. So the floor is **LIKELY a second parsed DAT**, not necessarily a `.RAW`/`.ALL` runtime conversion.
- The "all 1248 reloc targets `< 0x4f32c`" fact (§3.1) is about the **LEVEL.DAT** image only; it does **not**
  bound a second DAT's targets.
- New deterministic runtime check (no `a0` reproduction): EXEC BP at the loader file-read `0x8003d550` and
  parse `0x8003d568` to log every `(filename → base, size)` at LEVEL01 load.

**G20 RESULT (2026-06-14):** that check was run — `0x8003d550`/`0x8003d568` each hit **once**, `a1=0x51418`
(LEVEL.DAT). So the parser runs **exactly once for LEVEL01** → **the G19 "second parsed DAT" idea is REFUTED**
and this doc's original §3.1 ("parser called once") is empirically confirmed for LEVEL01. The floor comes
from a **non-parser** loader: the post-DAT **terrain `.all` loader** `fcn.8002ffa8` (file-read `0x8002ffe4`,
processor `fcn.8002fce8`) loads `TERRAIN.ALL`/`TERR1.ALL` into the heap cursor region where `0x801bdc58` sits,
and the floor mesh is **generated** from the s16 `(x,z)` stream (not a verbatim `.all` offset). Full loader
map + the next runbook (EXEC `0x8002ffe4`): [geometry_g20_sidecar_loader_trace.md](geometry_g20_sidecar_loader_trace.md).

**G22 RESULT (2026-06-14) — the floor source resource is NAMED: `LEVEL.RAW`.** The G21 callee-entry runbook
(`EXEC 0x80046330`) caught **Hit #4** (`ra=0x8003a390` = indirect high-heap loader `fcn.8003a318`) loading a
file to `0x80115aac`, size `0xb6be4`, range `[0x80115aac, 0x801cc690)` — which **brackets `0x801bdc58`** at
offset `0xa81ac`. The dest-size `0x801cc390 − 0x80115aac = 0xb68e4` = **LEVEL.RAW's exact size** → the floor's
loaded resource is **`LEVEL.RAW`**. `LEVEL.RAW[0xa81ac]` is an indexed-geometry stream (`u32=0x70d4001a`, not a
payload count) and the floor emitted a valid payload at runtime, so the floor is **runtime-converted from
LEVEL.RAW** (this doc's §3.3 "runtime-written by a generator" — now sourced to LEVEL.RAW). A direct LEVEL.RAW
`0xa81ac` edit is invalid (processed resource). Detail:
[geometry_g22_high_heap_floor_source.md](geometry_g22_high_heap_floor_source.md).

## 6. Reproduce (read-only)

```bash
# parser called once:
r2 -q -a mips -b 32 -e scr.color=0 -c '/x 7073000c' SCUS_942.88   # jal fcn.8001cdc0 -> only 0x8003d568
# emitter a0 source (no base add):
r2 -q -a mips -b 32 -e scr.color=0 -s 0x80020660 -c 'pd 16' SCUS_942.88
# reloc ceiling: all 1248 LEVEL.DAT targets in [0x45f0,0x4f32c] (tools/dat_reloc.py --scan); 0x5d460 > EOF 0x51418
# resource files: ls REBUILD/files/LEVEL01 (LEVEL.RAW, TERRAIN.ALL, TERR1.ALL, LEVEL1.DAT, ...)
# resource name strings:
r2 -q -e scr.color=0 -c 'izz' SCUS_942.88 | grep -iE '\.raw|\.all|\.dat'
```
