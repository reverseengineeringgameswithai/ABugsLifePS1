# G22 — high-heap floor load bracketed; source file = LEVEL.RAW (processed, not verbatim)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G21 file-read caller map](geometry_g21_file_read_caller_map.md) ·
[← G20 sidecar loader trace](geometry_g20_sidecar_loader_trace.md) ·
[← G18 output-buffer trace](geometry_g18_output_buffer_floor_trace.md) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **RUNTIME BRACKET CONFIRMED + SOURCE FILE IDENTIFIED (LEVEL.RAW) + STATIC OFFSET DECODE (2026-06-14).**
Read-only `SCUS_942.88` disasm + read-only sidecar file inspection. **No patch, no build.** No collision/pathing
claims — visual ≠ collision.

> **⚠ G26 CORRECTION (2026-06-15).** This doc treats `0x801bdc58` as the "walkable-floor payload" whose source it
> traces. Operator ground truth now shows that premise is **wrong**: at `Press X to Continue` `[0x801bdc58] =
> 0x70d4001a` (= `LEVEL.RAW[0xa81ac]`, the compressed word) and a **WRITE watch `0x801bdc58` during load = 0 hits`**
> → `0x801bdc58` is **compressed LEVEL.RAW source**, never an `fcn.80010000` render payload. What **stands** (and is
> now *proven* by the Press-X byte match): the **high-heap load brackets `0x801bdc58` ⇒ source = LEVEL.RAW**, and
> `0x801bdc58 = LEVEL.RAW + 0xa81ac`. What is **dropped**: the "floor payload / floor source" labeling — this trace
> identified the **compressed LEVEL.RAW resource**, not the floor render payload, which is **UNKNOWN**. See
> [geometry_g26_floor_payload_reaudit.md](geometry_g26_floor_payload_reaudit.md).

> **Headline:** the G21 callee-entry runbook (`EXEC 0x80046330`) worked. **Hit #4** — the indirect high-heap
> loader `fcn.8003a318` (`ra=0x8003a390`) — loaded a file to base **`0x80115aac`**, size `0xb6be4`, range
> `[0x80115aac, 0x801cc690)`, which **brackets the floor payload `0x801bdc58`** at source offset **`0xa81ac`**.
> The allocation size the loader used for the destination is **`0xb68e4` = LEVEL.RAW's exact logical size**
> (`0x801cc390 − 0xb68e4 = 0x80115aac`), so **the source file is LEVEL.RAW** (no other sidecar is within
> 200 KB). BUT `LEVEL.RAW[0xa81ac]` is **not** a clean `fcn.80010000` payload (`u32 count = 0x70d4001a`,
> impossible) — it is a structured indexed-geometry stream in LEVEL.RAW's own format. Since the floor emitted
> a *valid* payload at runtime, the floor at `0x801bdc58` is **converted/generated from LEVEL.RAW at runtime,
> not verbatim at `0xa81ac`**. So: **floor source resource = LEVEL.RAW (CONFIRMED by load); a direct
> file-offset edit at `0xa81ac` is NOT valid** (the resource is processed). Collision/pathing UNKNOWN.

## 0. ⚠ G23 CORRECTION (2026-06-15) — `0xa81ac` is COMPRESSED, the floor is decompressor output

This doc's §3 read `LEVEL.RAW[0xa81ac]` as "a structured **indexed-geometry stream**." **Corrected (G23):** those
bytes are **compressed data**. The G22 loader `fcn.8003a318` calls **`fcn.8001a1dc`, an LZ/Huffman bitstream
DECOMPRESSOR** (`a0 = LEVEL.RAW @0x80115aac` compressed, `a1 = [gp+0x588]` decompressed output; full reg-context
save, BE control words, literal/back-ref copy, no GTE, single caller). So **LEVEL.RAW is compressed**; the floor at
`0x801bdc58` is the **decompressor's OUTPUT**, and `0xa81ac` is the compressed byte that loads at that address —
**not a coordinate, not editable**. The "processed/generated, not verbatim" conclusion below is **upheld and
sharpened** (the process = decompression). Full record:
[geometry_g23_level_raw_floor_format.md](geometry_g23_level_raw_floor_format.md).

## 1. Hit #4 — high-heap load brackets the floor (CONFIRMED runtime)

Operator armed `EXEC 0x80046330` (universal file-loader entry, per G21) through LEVEL01 load.

**Hit #4 at loader entry:**
| reg | value | meaning |
|-----|-------|---------|
| PC | `0x80046330` | `fcn.80046330` entry |
| `a1` | `0x80115aac` | destination base (dest = `fp`) |
| `ra` | `0x8003a390` | caller = `fcn.8003a318` (the G21 indirect high-heap loader) |

Operator then set `EXEC 0x8003a390` and resumed to the loader return:
| reg | value | meaning |
|-----|-------|---------|
| PC | `0x8003a390` | return into `fcn.8003a318` |
| `v0` | `0x000b6be4` | bytes read (size) |
| `s0` | `0x80115aac` | dest base (kept) |

**Bracket (CONFIRMED arithmetic):**
```
dest base    = 0x80115aac
size (v0)    = 0x000b6be4
loaded range = 0x80115aac .. 0x801cc690
floor base   = 0x801bdc58
0x80115aac <= 0x801bdc58 < 0x801cc690   -> INSIDE
source offset = 0x801bdc58 - 0x80115aac = 0x000a81ac
```

**Hit #6 — control (CONFIRMED):** loader entry `a1 = 0x801607f8`, `ra = 0x8003d558` = the known LEVEL.DAT
load/parse path; LEVEL.DAT range `[0x801607f8, 0x801b1c10)` does **not** contain `0x801bdc58`. (Hit #4 precedes
Hit #6, so LEVEL.RAW loads first and the DAT later overwrites the lower-middle of LEVEL.RAW; the floor at
`0x801bdc58` sits **above** the DAT EOF `0x801b1c10` and the parser reserved end `0x801b6a10`, so it is in the
**surviving upper part** of the LEVEL.RAW buffer.)

**Recorded classification:**
```
HIGH-HEAP FILE LOAD BRACKETS FLOOR PAYLOAD /
SOURCE OFFSET 0xA81AC WITHIN LOADED RESOURCE /
SOURCE FILE = LEVEL.RAW (size/dest-confirmed; filename string not yet captured) /
FLOOR IS PROCESSED/GENERATED FROM LEVEL.RAW, NOT VERBATIM AT 0xA81AC
```
Collision/pathing **UNKNOWN** — do not infer.

## 2. Source-file identification — LEVEL.RAW (CONFIRMED by size + dest)

`fcn.8003a318(a0 = filename)` computes `dest = 0x801cc390 − align(filesize)` (ceiling `0x801cc390 =
0x801d0000 − 0x3c70`; size from `fcn.8004589c`), then `jal fcn.80046330(a0, a1=dest)`. For Hit #4:

| quantity | value | match |
|----------|-------|-------|
| dest (operator) | `0x80115aac` | — |
| ⇒ size used for dest = `0x801cc390 − 0x80115aac` | **`0xb68e4`** | **= LEVEL.RAW logical size exactly** |
| bytes read `v0` | `0xb6be4` (`= 0xb68e4 + 0x300`) | LEVEL.RAW + sector/read padding |

Closest sidecar by size to `0xb6be4`: **LEVEL.RAW `0xb68e4` (Δ 768 bytes)**; the next (LEVEL1.RAW `0x84210`)
is **207 KB** away. The dest computation used LEVEL.RAW's exact logical size. **⇒ Hit #4 loads `LEVEL.RAW`.**
(The G21 LEVEL.RAW row predicted exactly this: dest `0x80115aac`, offset `0xa81ac`.) Filename string `a0` was
not captured by the operator, so the name is **size/dest-confirmed, not string-confirmed** — a 30-second
runtime read can confirm it (§4).

`0xa81ac` is in range (`< 0xb68e4`) and `= 92.1%` through LEVEL.RAW (near the end — the geometry section).

## 3. What is at `LEVEL.RAW[0xa81ac]`? — NOT a verbatim `fcn.80010000` payload (CONFIRMED bytes)

```
LEVEL.RAW @0xa81ac:  1a 00 d4 70 | 15 2d 1b 00 | 71 1c 23 15 | c7 05 1d 1c | 23 16 05 71 | 1e 23 17 c7 ...
   u32@0xa81ac = 0x70d4001a   -> as a payload vertexCount: IMPOSSIBLE (1.9 billion)
```
This is **not** the `{u32 count; Vertex stride 0xc (pad=0); cmd stream}` format the floor uses. It is a
**structured indexed-geometry stream**: note the incrementing small indices `…1b,1c,1d,1e,1f…` and `…15,16,17…`
and `…21,22,23,24,25,26…` with recurring tokens (`23 1X`, `c7 05`, `05 1X`) — characteristic of a
triangle/quad **index/strip** stream into a vertex pool (a compact terrain-mesh encoding), **distinct** from
LEVEL.DAT's byte-offset payloads.

**Deduction the floor is processed, not verbatim (CONFIRMED logic):** at the floor draw (Candidate B), the
emitter `fcn.80010000` read a *valid small* `vertexCount` at `0x801bdc58` and emitted ≥17 clean primitives.
But the byte that LEVEL.RAW loads at `0x801bdc58` is `0x70d4001a` (invalid). Therefore the runtime floor payload
at `0x801bdc58` **differs from the loaded LEVEL.RAW byte at `0xa81ac`** — i.e. LEVEL.RAW is **converted into
`fcn.80010000` payloads at runtime** (and the result lands in the surviving upper buffer where the floor sits),
exactly the "runtime-generated floor geometry" classification from G18. The source offset `0xa81ac` is where the
floor's loaded LEVEL.RAW data sits, **but it is not a directly-editable payload coordinate.**

**`fcn.8003a318` post-load behaviour (CONFIRMED disasm):** after `jal fcn.80046330` it keeps the base in `s5`
and **initializes global tables** (8-entry arrays at `0x800a65b0`/`0x8009fc10`; `0x81`-entry arrays at
`0x80095138`/`0x80098638`; `0x100` bytes at `0x800a*`; clears `0x80094a38`/`0x80090bf0` via `fcn.8005f7ac`) and
reads scene flags `0x614(gp)`. It is a **resource-setup** function — it does not keep LEVEL.RAW verbatim; the
buffer is consumed by the geometry converter (the table-driven stage that emits `fcn.80010000` payloads). LEVEL.RAW
header (`0x0c830000, 0x0c5f0000, 0x40eba75b, …` then packed data; no clean offset table in the first `0x80` B)
is a custom container, consistent with §3.

## 4. Recommendation (Task 3) — Option A: read-only source decode + one deterministic confirmation

Source file **is** identified (LEVEL.RAW), but the offset `0xa81ac` is **not** a known clean floor-like stream
(it is LEVEL.RAW's own indexed-geometry format, processed at runtime). So this is **Option A** (inspect/decode
the source offset; do **not** patch), not C. Concretely:

**(A.1) Read-only static decode of LEVEL.RAW's geometry format around `0xa81ac`** — characterize the indexed
stream (vertex pool location, index width, strip/primitive grammar) and find the vertex coordinates the floor's
indices reference. This is the path to an eventual *LEVEL.RAW-format* edit (a separate tool, never a LEVEL.DAT
edit). Read-only; no patch.

**(A.2) One deterministic runtime confirmation (no flaky `0x800108b4` repro, no RAM dump)** — at the *already
deterministic* Hit #4:
```
EXEC 0x80046330 ; on the hit whose ra==0x8003a390 (Hit #4):
   read the C-string at a0  -> confirm the filename is "level.raw"   (closes the string gap in §2)
Then set EXEC 0x8003a390 and resume to the loader return; immediately read 16 bytes at 0x801bdc58:
   == 1a 00 d4 70 …  -> LEVEL.RAW is loaded verbatim there (floor generated LATER, in place)
   != that           -> the region was already converted / is a separate allocation
This settles verbatim-vs-processed and confirms the filename in two cheap reads.
```

**Do not** patch `LEVEL.RAW[0xa81ac]` — it is not the floor payload (the resource is processed/converted). Any
future floor edit must target LEVEL.RAW's geometry format (after A.1) or the converter, and only after a runtime
test — not a blind file-offset write. Collision/pathing UNKNOWN.

## 5. What this resolves / leaves open
- **RESOLVED:** the walkable-floor payload's source **resource is `LEVEL.RAW`** (loaded by the indirect
  high-heap loader `fcn.8003a318`, bracketing `0x801bdc58` at offset `0xa81ac`). This supersedes the earlier
  guesses (second parsed DAT — refuted G20; terrain `.all` — did not fire G21). It confirms the long-standing
  G18 conclusion that the floor is a separately-loaded, runtime-generated terrain resource, and **names the
  file**.
- **OPEN (UNKNOWN):** LEVEL.RAW's internal geometry format and the converter that emits `fcn.80010000` payloads;
  whether `0xa81ac` is verbatim-then-overwritten or read-from-elsewhere; the filename string (size/dest-confirmed
  only); collision/pathing (always — visual ≠ collision).

## 6. Reproduce (read-only)
```bash
python3 - <<'PY'
import struct
lr=open('REBUILD/files/LEVEL01/LEVEL.RAW','rb').read()
dest=0x80115aac; floor=0x801bdc58; off=floor-dest          # 0xa81ac
print('LEVEL.RAW size',hex(len(lr)),'dest-size 0x801cc390-dest =',hex(0x801cc390-dest))  # == 0xb68e4 == size
print('LEVEL.RAW[0x%x] u32 ='%off, hex(struct.unpack_from('<I',lr,off)[0]))               # 0x70d4001a (not a count)
print('bytes:', lr[off:off+16].hex(' '))
PY
# the indirect high-heap loader + its post-load table init:
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003a318 -c 'pd 70' /tmp/abltext.bin
```
