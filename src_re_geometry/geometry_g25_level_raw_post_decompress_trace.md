# G25 — LEVEL.RAW post-decompression path: per-chunk decompress LOOP + type dispatch builder

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G24 decompressor grammar](geometry_g24_level_raw_decompressor.md) ·
[← G23 LEVEL.RAW is compressed](geometry_g23_level_raw_floor_format.md) ·
[← G22 high-heap floor source](geometry_g22_high_heap_floor_source.md) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **RUNTIME `EXEC 0x8001a1dc` TRACE (operator) + READ-ONLY STATIC TRACE of `fcn.8003a318` (2026-06-15).**
Read-only `SCUS_942.88` disasm. **No patch, no build.** No collision/pathing claims — visual ≠ collision.

> **⚠ G26 CORRECTION (2026-06-15).** This doc's framing that the floor payload "is built post-decompression in
> `[0x8015fcbc, 0x801cc390)` near `0x801bdc58`" is **SUPERSEDED**. Operator ground truth: at `Press X to Continue`,
> `[0x801bdc58] = 0x70d4001a` (= `LEVEL.RAW[0xa81ac]`, compressed source) and a **WRITE watch `0x801bdc58` during
> load = 0 hits** → `0x801bdc58` is **never written**; it is **compressed LEVEL.RAW source**, not a render payload.
> So the floor is **not** at `0x801bdc58` at all — the "where in the high region is the floor built" question is
> moot. The G25 **per-chunk decompress-loop / `word0`/`word1` findings below remain CORRECT** (LEVEL.RAW pipeline);
> only the floor-location inference is dropped. The real floor render payload pointer is **UNKNOWN** — re-find it
> from the consumer side with count validation. See
> [geometry_g26_floor_payload_reaudit.md](geometry_g26_floor_payload_reaudit.md).

> **Headline.** The operator's `EXEC 0x8001a1dc` trace shows the decompressor is called **many times** — it runs
> inside a **per-chunk loop** in `fcn.8003a318` (single static call site `0x8003a4e4`, looped). Each iteration:
> reads a chunk header at the compressed cursor `s5`, decompresses that chunk into `fp = [gp+0x588]`, reads
> `s4 = fp[0]` = a **chunk subtype**, and runs a large **type-dispatch builder** (`0x8003a4ec..0x8003c250`) that
> consumes the decompressed chunk and builds runtime resources. This **resolves G24's two open questions**:
> (1) once-vs-per-block → **per-block (looped)**; (2) the "computed-then-dead" header words → **`word0` = per-chunk
> decompressed size (advances `fp`), `word1` = per-chunk compressed size (advances `s5`)** — dead *inside* the
> decompressor, *live* in the caller's loop. **Decisive negative result:** the decompressor output cursor `a1`/`fp`
> tops out at **`0x8015fcbc`**; the runtime floor `0x801bdc58` is **`+0x5df9c` above that** → the floor is **NOT
> direct decompressor output**. It is produced **later**, by a post-decompression builder writing into the high-heap
> region above `fp`'s output. Exact writer = UNKNOWN → one **WRITE watch `0x801bdc58`** pins it (§6).

## 1. Operator runtime trace (`EXEC 0x8001a1dc`) — CONFIRMED

All "normal" hits share `pc=0x8001a1dc`, `ra=0x8003a4ec`, `gp=0x80081d98` → the single call site in `fcn.8003a318`
(`jal 0x8001a1dc` @`0x8003a4e4`, so `ra = 0x8003a4e4 + 8 = 0x8003a4ec` ✓). Called **many times** = a loop.

- `a0` (= `s5`) advances monotonically **up** the compressed LEVEL.RAW buffer `[0x80115aac, 0x801cc690)`.
- `a1` (= `fp = [gp+0x588]`) advances monotonically **up** the decompressed-output region.

**Source-side compressed-chunk bracket for `0xa81ac`** (the floor address treated as a compressed-buffer offset,
`0x801bdc58 − 0x80115aac = 0xa81ac`):

| quantity | value |
|----------|-------|
| compressed load base | `0x80115aac` |
| floor runtime addr (as compressed offset) | `0x801bdc58` → off `0xa81ac` |
| bracketing chunk `a0` (start) | `0x801bd58f` (off `0xa7ae3`) |
| bracketing chunk `a0` (next) | `0x801bf662` |
| ⇒ `0x801bd58f ≤ 0x801bdc58 < 0x801bf662` | floor addr is **inside** this chunk's compressed source |
| target within chunk | `0x801bdc58 − 0x801bd58f = 0x6c9` |
| bracketing chunk `a1` (start) | `0x80143438` |
| bracketing chunk `a1` (next) | `0x80147500` |
| ⇒ decompressed span of this chunk | `0x40c8` (compressed `0x20d3` → ~2× expand) |

**NEGATIVE (decisive):** `a1` never reaches/brackets `0x801bdc58`. Final normal decompressor row:
`a0 = 0x801cc17e`, `a1 = 0x8015fcbc`. `0x801bdc58 − 0x8015fcbc = 0x5df9c` → the floor is **`0x5df9c` above the very
end of the decompressor's output**. **The floor is not in the decompressor's output region.**

**Out-of-scope final row** `a0=0x00000002, a1=0x001e2830, pc=0x8003f33c, ra=0x8003f328`: this is **not** a
decompressor chunk — `0x8003f334..0x8003f340` is a **GPU/DMA spin-wait** (`lw v0,[0x80082250]; beq v0,1,self`,
preceded by `jal 0x80065fcc`); the `a0`/`a1` are stale regs. Correctly excluded by the operator.

## 2. The per-chunk loop in `fcn.8003a318` (CONFIRMED disasm)

`fcn.8003a318(a0=filename)` (span `0x8003a318..0x8003c384`, ~2075 instrs) is the high-heap loader **and** the
LEVEL.RAW chunk assembler. After the file load + table init (G22):

```
0x8003a360  jal 0x8004589c (a0=name)        ; v0 = filesize
0x8003a37c..84  s0 = 0x801cc390 - align4(filesize)   ; top-down dest  (= 0x80115aac for LEVEL.RAW)
0x8003a388  jal 0x80046330 (a0=name,a1=s0)  ; load COMPRESSED LEVEL.RAW -> s0
0x8003a390  move s5, s0                      ; s5 = compressed base/cursor 0x80115aac
            ... init global tables (G22) ...
0x8003a4c0  sw zero, 0x48(sp)               ; CHUNK_IDX = 0
0x8003a4c8  lw fp, 0x588(gp)                ; fp = [gp+0x588] = decompressed-output cursor
0x8003a4cc  j  0x8003c2a4                   ; -> loop head
```

**Loop head `0x8003c29c`** (read 4 header bytes at the compressed cursor):
```
0x8003c29c  lbu v1,(s5)                     ; word0 byte0
0x8003c2a4  bne v1,0xff, 0x8003a4d4         ; any of s5[0..3] != 0xff -> process chunk
0x8003c2ac  lbu v0,1(s5) ; bne ...,0x8003a4d4
0x8003c2bc  lbu v1,2(s5) ; bne ...,0x8003a4d4
0x8003c2cc  lbu v0,3(s5) ; bne ...,0x8003a4d4
0x8003c2dc  ... TERMINATOR: word0 == 0xffffffff -> FINALIZE (§4)
```

**Chunk body `0x8003a4d4`** (decompress one chunk, then dispatch):
```
0x8003a4d4  lw t1,0x48(sp)                  ; CHUNK_IDX
0x8003a4dc  bnez t1,0x8003c2dc              ; (single-shot mode guard; 0 on the LEVEL.RAW path -> stays in loop)
0x8003a4e0  move a0,s5                      ; [delay] a0 = compressed chunk src
0x8003a4e4  jal 0x8001a1dc                  ; DECOMPRESS(a0=s5, a1=fp)
0x8003a4e8  move a1,fp                      ; [delay] a1 = fp = decompressed dst
0x8003a4ec  lw  s4,(fp)                     ; s4 = fp[0] = CHUNK SUBTYPE   (ra lands here)
0x8003a4f4  slti v0,s4,0x20 ; beqz -> 0x8003ada4 (subtype >= 0x20 path)
0x8003a4fc  move s3,fp                      ; s3 = fp = decompressed chunk base (consumed by dispatch)
0x8003a500  lhu s7,4(fp); lhu s6,6(fp); lhu t1,8(fp); lhu t1,0xa(fp)  ; chunk header fields
            ... big subtype dispatch 0x8003a4ec..0x8003c250 ...
```

**Per-chunk tail `0x8003c250`** (advance both cursors, loop back) — *this is where `word0`/`word1` are consumed:*
```
0x8003c250  v1 = (s5[4]<<24)|(s5[5]<<16)|(s5[6]<<8)|s5[7]  + 0xe   ; = BE32(s5+4) + 0xe = word1 + 0xe
0x8003c27c  v0 = [gp+0x614] ; andi 0x800
0x8003c288  beqz -> 0x8003c29c              ; (mode bit 0x800: single-shot vs streamed)
0x8003c28c  addu s5,s5,v1                   ; s5 += word1 + 0xe   (next compressed chunk)
0x8003c290  sw s5,0x664(gp)                 ; cache compressed cursor
            -> loop head 0x8003c29c
```
…and `fp` is advanced **inside each subtype case** by `align4(word0)` (decompressed size), e.g.
`0x8003c130: v0 = align4(BE32(s5[0..3]) + 3)`; `0x8003c13c: addu fp,fp,v0`. There are ~10 `addu fp,fp,v0/v1`
sites (`0x8003b744/b888/b9a0/ba10/bc98/bf8c/c13c/c198/c200/c24c`), one per case, each advancing `fp` by that
case's consumed/produced size.

### Resolves G24's "computed-then-dead" header words
Inside `fcn.8001a1dc` (G24) `word0 = BE32[src+0]` and `word1 = BE32[src+4]` were computed then never read.
**They are read by the CALLER:** `word1 + 0xe` = the compressed chunk stride (`0x8003c264`), and `align4(word0)`
= the decompressed chunk size that advances `fp`. So `word0` = per-chunk **decompressed** byte count, `word1` =
per-chunk **compressed** byte count, `0xe` = the per-chunk header length. (The `0xffffffff` end marker is a
sentinel `word0`.) This also matches the operator's per-chunk `a0`/`a1` deltas (`a0 += word1+0xe`, `a1 += word0`).

## 3. Chunk subtype dispatch (CONFIRMED structure; per-subtype semantics PARTIAL)
`s4 = fp[0]` selects a handler. A `slti s4,0x20` splits "low" subtypes (`0x8003a4ec..`) from "high"
(`0x8003ada4..`). Observed compared constants include `0, 4, 5, 6, 7, 0xb, 0xc, 0xd, 0x1b, 0x1c, 0x1d, 0x1e,
0x20, 0x24, 0x26, 0x29, …`. Sampled handlers (read-only):
- **`s4==0x20`** (`0x8003adb0+`): reads `s3[4/8/0xc/0x10]`, converts 5-bit→8-bit RGB, stores to `0x800771b0+` →
  **environment/light** chunk (not floor).
- **`s4==0xd`** (`0x8003a760+`): args `(0x300,0xc0,…,0x38)` + source `s3+0xc`, `jal 0x8003cc58` → a rect/VRAM-style
  upload from the decompressed chunk body → **texture/image** chunk (not floor).
- **vertex/index builder tail** (`0x8003c058..0x8003c24c`): halfword-array build loop (`sh v0,(s4_local)`,
  cursors `+= 2`) using `jal 0x80061a48`, then `fp += align4(word0)` → **mesh/coordinate** chunk (geometry family).

**Builders the dispatch calls** (candidate floor writers): local `fcn.8003cc58` (×5; consumes `s3+0xc`; itself calls
`0x800628c0/0x800625fc/0x80060154/0x8003e3e0`), hot helpers `0x800628c0` (×10), `0x800625fc` (×10), `0x80061a48`
(×9), plus `0x80055db0`. None writes a `gp`-relative cursor; they write through register destinations set per case.

## 4. Finalize `0x8003c2dc` (CONFIRMED)
On the `word0 == 0xffffffff` terminator:
```
0x8003c2f4  sw 0x801cc390, 0x4a0(gp)        ; [gp+0x4a0] = high-heap TOP (= 0x801d0000 - 0x3c70)
0x8003c31c  sw fp, 0x588(gp)                ; persist final decompressed-output cursor (= 0x8015fcbc)
0x8003c320  jal 0x80063508 (a0=0x801cc520, a1=1, a2=1, a3=lh[0x800910ea], [sp+0x10]=&local)
0x8003c33c  jal 0x80063508 (a0=0x801e14dc, …)   ; model/display registration (args above the high top)
0x8003c350  sw 0x80082084, [0x80096d98]
            ... restore regs; jr ra
```
`[gp+0x4a0] = 0x801cc390` is the high-heap top; `[gp+0x588]` is left at the end of decompressed output.

## 5. Corrected pipeline model (this supersedes the "floor = decompressor output" reading of G23)

```
fcn.8003a318(name):
  load COMPRESSED LEVEL.RAW (0xb6be4) top-down -> s5 = 0x80115aac   [buffer 0x80115aac .. 0x801cc690, top 0x801cc390]
  fp = [gp+0x588]                                                   (decompressed-output cursor)
  LOOP (head 0x8003c29c):
     if s5[0..3] == ff ff ff ff: break -> FINALIZE
     decompress chunk:  fcn.8001a1dc(a0=s5, a1=fp)                  (G24 codec)
     s4 = fp[0] = subtype
     DISPATCH 0x8003a4ec..0x8003c250: consume decompressed chunk s3=fp, build resource (light/texture/mesh/…)
        fp += align4(word0)            (decompressed size; per-case)
     s5 += word1 + 0xe                 (compressed stride; tail 0x8003c250)
  FINALIZE 0x8003c2dc: [gp+0x4a0]=0x801cc390 (top); [gp+0x588]=final fp (0x8015fcbc); jal 0x80063508 x2; return
```

**Where the floor is (LIKELY):** the runtime floor payload `0x801bdc58` is **NOT** in the decompressor output
(`fp` ≤ `0x8015fcbc`). It sits in `[final-fp 0x8015fcbc, high-top 0x801cc390)` — the upper part of the high-heap
buffer (the already-consumed compressed tail), **`0xe738` below the high top `0x801cc390`** and **`0x5df9c` above
the decompressed output**. So the floor `fcn.80010000` payload is **built by a post-decompression stage** — either
a geometry-family subtype case in `fcn.8003a318` (writing into the high region) and/or a later converter that reads
the decompressed output — **not** by the raw decompressor. Exact writer/cursor = **UNKNOWN**.

Memory map (addresses CONFIRMED unless noted):
```
0x80115aac ─ compressed LEVEL.RAW load base (s5 start)
   … s5 (compressed read cursor) walks UP, advancing by word1+0xe per chunk …
0x801bd58f ─ s5 at the chunk that brackets compressed offset 0xa81ac  (a0 in operator trace)
0x801bdc58 ─ RUNTIME FLOOR PAYLOAD  (= high-top − 0xe738; = final-fp + 0x5df9c)   <-- built post-decompress (LIKELY)
0x801cc17e ─ s5 final (near top)
0x801cc390 ─ high-heap TOP ([gp+0x4a0])
0x801cc690 ─ end of compressed load (base + 0xb6be4)

[out_base .. 0x8015fcbc) ─ decompressed-output region (fp); out_base = [gp+0x588] init = UNKNOWN (low-heap, < floor)
0x8015fcbc ─ fp final (end of decompressor output)   <-- a1 NEVER reaches the floor
```
(Whether the floor region is a top-down build cursor from `0x801cc390` or fed by a later loader is the open
question §6 settles. `out_base` was not captured; not needed for the next step.)

## 6. Recommended next runtime runbook — ≤3 BPs (no broad decompressor re-trace, no RAM dump, no patch)

**(1) PRIMARY — WRITE watch `0x801bdc58`** through LEVEL01 load → gameplay.
This catches the **exact PC** that writes the floor payload's first word (the `fcn.80010000` `vertexCount`), plus
the instant it happens. At the hit, record: `pc`, `ra`, and the **source** being copied/built (the register/address
feeding the store). Classify the source:
- source ∈ `[out_base, 0x8015fcbc)` (decompressed output) → the floor is **built from the decompressed data** by a
  converter; the watch PC names that converter.
- source ∈ `[0x8015fcbc, 0x801cc690)` (leftover compressed tail) or computed in-register → built **in place** in the
  high region by a `fcn.8003a318` subtype case.
- if the write PC is inside `fcn.8003a318` (`0x8003a318..0x8003c384`) → floor is built **during** the chunk loop;
  if it is elsewhere → a **separate post-load stage** builds it (re-trace from that PC).

**(2) SECONDARY — EXEC `0x8003a4ec`** (the `lw s4,(fp)` right after each decompress return).
Log per chunk: `s4 = fp[0]` (subtype), `fp` (a1 out cursor), `s5` (a0 compressed cursor), `[sp+0x48]` (CHUNK_IDX).
This **enumerates the chunk subtypes** and identifies which chunk owns compressed offset `0xa81ac`
(`s5 ≤ 0x801bd58f < s5_next`), tying the floor's compressed region to a subtype — and confirms the per-chunk model
(`a0 += word1+0xe`, `a1 += word0`). Cheap, deterministic, fires once per chunk.

**(3) TERTIARY (only if the write watch does NOT fire during the `fcn.8003a318` loop)** — EXEC `0x8003c2dc`
(finalize) and `0x80063508` to inspect the finalize registration, then keep the WRITE watch armed through the rest
of load/early gameplay: the floor may be built by a later stage that reads `[gp+0x588]`/`[gp+0x4a0]`.

This sequence converts the remaining UNKNOWN (the floor's writer) into a single PC with no guessing.

## 7. Guardrails
No patch, no build. No DAT/CUE/BIN/RAW/RAM/save-state committed. `0xa81ac` is **compressed** (do not treat as a
coordinate; G23). Do not patch the runtime/output address `0x801bdc58`. The floor is **not** in LEVEL.DAT and **not**
direct decompressor output. Collision/pathing **UNKNOWN** — visual ≠ collision.

## 8. Reproduce (read-only)
```bash
python3 -c "open('/tmp/abltext.bin','wb').write(open('SCUS_942.88','rb').read()[0x800:0x73000])"
# the per-chunk loop + decompress call + dispatch entry + tail:
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003a318 -c 'pd 220' /tmp/abltext.bin   # loader + chunk body
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003c29c -c 'pd 16'  /tmp/abltext.bin   # loop head + terminator
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003c250 -c 'pd 12'  /tmp/abltext.bin   # tail: s5 += word1+0xe
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003c100 -c 'pd 18'  /tmp/abltext.bin   # fp += align4(word0)
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003c2dc -c 'pd 30'  /tmp/abltext.bin   # finalize
# key PCs: loop entry 0x8003a4cc(j); body 0x8003a4d4; decompress 0x8003a4e4 (ra 0x8003a4ec); subtype s4=fp[0] @0x8003a4ec;
#          fp-advance sites 0x8003b744/b888/b9a0/ba10/bc98/bf8c/c13c/c198/c200/c24c; s5-advance 0x8003c28c; finalize 0x8003c2dc
```
