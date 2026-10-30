# G23 — LEVEL.RAW is COMPRESSED; floor is decompressor output (no editable field at 0xa81ac)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G22 high-heap floor source](geometry_g22_high_heap_floor_source.md) ·
[← G21 file-read caller map](geometry_g21_file_read_caller_map.md) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **READ-ONLY `LEVEL.RAW` + decompressor analysis (2026-06-15).** Read-only `SCUS_942.88` disasm +
read-only `LEVEL.RAW` inspection. **No patch, no build.** No collision/pathing claims — visual ≠ collision.

> **⚠ G26 CONFIRMATION (2026-06-15).** This doc's core claim — `0x801bdc58` / `LEVEL.RAW[0xa81ac]` is **compressed
> data, not a render payload** — is now **proven by runtime ground truth**: at `Press X to Continue`,
> `[0x801bdc58] = 0x70d4001a` (= the compressed word here), and a **WRITE watch `0x801bdc58` during load = 0 hits**.
> This also retires the earlier "floor payload at `0x801bdc58`" reading (G17/G18) that this analysis was chasing:
> `0x801bdc58` is **purely compressed LEVEL.RAW source**, never a floor `fcn.80010000` payload. The decompression
> findings below stand; the real floor render payload pointer is **UNKNOWN**. See
> [geometry_g26_floor_payload_reaudit.md](geometry_g26_floor_payload_reaudit.md).

> **Headline:** decoding `LEVEL.RAW` around `0xa81ac` shows it is **not** flat geometry — it is **compressed
> data**. The G22 high-heap loader `fcn.8003a318` loads LEVEL.RAW and then calls **`fcn.8001a1dc`, an LZ/Huffman
> bitstream DECOMPRESSOR** (`a0 = LEVEL.RAW @0x80115aac` compressed input, `a1 = [gp+0x588]` decompressed
> output). So the floor payload at runtime `0x801bdc58` is the **decompressor's OUTPUT**, and `LEVEL.RAW[0xa81ac]`
> is **compressed bytes** — not an `fcn.80010000` payload, not s16 coordinates, not an editable field.
> **There is no safe direct edit target in LEVEL.RAW at/near `0xa81ac`** (editing compressed data corrupts the
> decode). This **corrects** G22's "indexed-geometry stream at `0xa81ac`" reading. Collision/pathing UNKNOWN.

## 1. The `0xa81ac` window (CONFIRMED bytes) — a dense bitstream, not geometry

```
0x0a8190: 2d 14 00 15 38 23 0d 05 16 e3 23 0e 8e 05 17 38
0x0a81a0: 23 0f 05 18 e3 29 10 8e 05 19 10 2d 1a 00 d4 70   <-- 0xa81ac (= runtime 0x801bdc58)
0x0a81b0: 15 2d 1b 00 71 1c 23 15 c7 05 1d 1c 23 16 05 71
0x0a81c0: 1e 23 17 c7 05 1f 1c 29 18 05 1c 20 00 21 61 71
0x0a81d0: 04 9b 1c c1 2d 22 00 23 c7 23 1c 1c 05 24 23 71
0x0a81e0: 1d 05 25 c7 23 1e 1c 05 26 29 70 1f 05 27 00 71
```

Observations (read-only):
- **Byte/halfword/word:** `u32@0xa81ac` little-endian = `0x70d4001a`, big-endian = `0x1a00d470` — neither is a
  plausible `fcn.80010000` vertexCount. No clean record boundary, no aligned s16 triples.
- **Statistics:** the `[0xa8000,0xa8400)` window has **213 distinct byte values / 1024**, only `25` zeros — high
  local entropy, the signature of compressed/packed data, **not** a coordinate array (which would be `00/ff/01/fe`
  heavy). Whole-file: only ~11% of bytes are `00/ff/01/fe`, and s16 reads at arbitrary offsets are noise
  (`0xa8000`: `11097,-4545,12036,22353,28463,…`). So LEVEL.RAW is **not** arrays of s16 coordinates anywhere.
- **Apparent "incrementing indices"** (`…0d 0e 0f 10…`, `…14…1a 1b 1c…`, `…21 22 23 24 25 26…`) are **artifacts of
  the compressed/literal stream**, not vertex indices (G22 over-read these — see §5). No clean
  `{u32 count; Vertex 0xc(pad=0); cmds}` payload exists **anywhere** in LEVEL.RAW (a full-file scan found **0**).

These facts alone say "compressed." The decompressor (§2) proves it.

## 2. LEVEL.RAW's consumer = `fcn.8001a1dc`, a bitstream DECOMPRESSOR (CONFIRMED disasm)

The G22 high-heap loader `fcn.8003a318` loads LEVEL.RAW (compressed) to `0x80115aac`, then:
```
0x8003a4c8  lw   fp, 0x588(gp)      ; fp = [gp+0x588] = DECOMPRESSED-OUTPUT dest
0x8003a4e0  move a0, s5             ; a0 = LEVEL.RAW base 0x80115aac (COMPRESSED input)
0x8003a4e4  jal  0x8001a1dc         ; decompress(a0=src, a1=dst)
0x8003a4e8  move a1, fp             ; [delay] a1 = fp (output)
0x8003a4ec  lw   s4, (fp)           ; read decompressed header (first word)
```
`fcn.8001a1dc` (`0x8001a1dc .. 0x8001a8f8`, ~`0x720` B) is a hand-optimized **LZ/Huffman bitstream decoder**:

| trait | evidence | meaning |
|-------|----------|---------|
| full register-context save/restore | saves **all** GPRs incl. `k0/k1/gp` at entry (`0x8001a1e8..0x8001a254`), restores at exit (`..0x8001a8e8`) | uses every register as decode state — classic asm codec |
| big-endian control-word fetch | `lbu`×4 + `<<24/<<16/<<8 / or` (`0x8001a270..0x8001a294`), `src += 4` | reads BE 32-bit control words from the stream |
| bit-by-bit flag reader | `t2 = t2+t2; t7 = t2>>8; andi t7,1` (`0x8001a2fc..`, and in every handler) | pulls one bit at a time (literal/match flags, lengths) |
| **literal run copy** | handler `0x8001a418/0x8001a66c`: `lbu t4,(v1); sb t4,(a1); a1++` | copies literal bytes from the compressed stream `v1` to output `a1` |
| **match / back-reference** | handler `0x8001a658`+ : bit-decoded offset/length (`t0=2,t1=0,…`), copies earlier output | LZ back-reference |
| no `jal`, computed jumps only | 0 `jal` in 456 instrs; `j`/branch dispatch on decoded bits | flat interpreter/decoder loop |
| **no GTE/cop2** | 0 `cop2`/`mtc2`/`RTPS`… | pure data decompression, not geometry transform |
| single caller | only `jal fcn.8001a1dc` is `0x8003a4e4` (in `fcn.8003a318`) | dedicated to the LEVEL.RAW load |

So **LEVEL.RAW is a compressed resource**; `fcn.8001a1dc` decompresses it into `[gp+0x588]` and the result is the
level geometry (the floor payload among it). The control stream is **big-endian** (notable; PS1 is otherwise LE).

## 3. Data flow (CONFIRMED chain) and where the floor really is
```
fcn.8003a318 (G22): load COMPRESSED LEVEL.RAW (0xb68e4) -> 0x80115aac  (high-heap, dest = 0x801cc390 - size)
   -> fcn.8001a1dc(a0=0x80115aac compressed, a1=[gp+0x588] dst): LZ/Huffman DECOMPRESS
   -> decompressed geometry (incl. the floor fcn.80010000 payload) in the output region
   later: fcn.80010000 emits the floor payload at runtime 0x801bdc58
```
- The floor at `0x801bdc58` is the **decompressor OUTPUT** (a valid `{u32 count; Vertex; cmds}` payload), which is
  why the emitter read a valid count there (G22) while `LEVEL.RAW[0xa81ac]` (the *compressed* byte that loads at
  that address) is `0x70d4001a`. **They differ because decompression overwrote the loaded compressed byte with the
  decoded payload** — exactly G22's verbatim-vs-processed result, now explained: the process is **decompression**.
- `0xa81ac` is therefore **the compressed byte position that coincides with the floor's runtime address after the
  raw load** — it is *not* the floor's compressed *source* (LZ source is elsewhere/earlier in the stream) and not a
  geometry coordinate. Whether `[gp+0x588]` (output) overlaps the upper LEVEL.RAW buffer (so the floor lands at
  `0x801bdc58`) vs. is a separate buffer is the one runtime detail left (§6).

## 4. Candidate editable source fields — **NONE** (compressed)
There is **no safe direct edit target** in LEVEL.RAW at or near `0xa81ac`:
- the bytes there are **compressed** (LZ/Huffman) — any change corrupts the decode of that and following data;
- there are **no** plain s16 coordinates or `fcn.80010000` payloads anywhere in the file to edit;
- the floor's editable coordinates exist only in the **decompressed** form (runtime buffer), which is a
  runtime/transient address (out of scope to patch, and not a file edit).

A floor edit is therefore **not** a single-byte file patch. It requires either (a) fully decoding the `fcn.8001a1dc`
codec to **decompress → edit a vertex → recompress** LEVEL.RAW, or (b) intercepting the decompressed buffer at
runtime (transient). Both are larger than a coordinate poke; **do not patch `0xa81ac`** (it is not a coordinate).
This is strictly safer than patching the runtime/output address `0x801bdc58` (which is regenerated every load and
whose meaning we'd be guessing).

## 5. Correction to G22
G22 §3 characterized `LEVEL.RAW[0xa81ac]` as "a structured **indexed-geometry stream** (incrementing indices…)"
and left open verbatim-vs-processed. **Corrected:** those bytes are **compressed data**; the apparent incrementing
runs are stream artifacts, not vertex indices. The "processed/generated" half of G22's conclusion is **upheld and
sharpened**: the processing is **LZ/Huffman decompression by `fcn.8001a1dc`**. G22's headline facts stand (Hit #4
loads LEVEL.RAW; it brackets `0x801bdc58`; source-relative offset `0xa81ac`; floor is generated, not verbatim).

## 6. Recommended next step (Task 5) — one narrow runtime BP to map decompress I/O

Static decode of the full `fcn.8001a1dc` codec (bit grammar: literal/match flags, offset/length encoding, the BE
control words, window size) is the eventual path to an editable representation, but it is a substantial RE task.
The single **narrow, deterministic** step that connects the LEVEL.RAW source to the generated floor output:

```
EXEC 0x8001a1dc          (decompressor entry; fires once, at LEVEL01 load, from fcn.8003a318)
  record a0  = compressed source base  (expect 0x80115aac = LEVEL.RAW)
  record a1  = decompressed-output dest = [gp+0x588]
Then set a one-shot EXEC at the return (ra into fcn.8003a318, ~0x8003a4e8) and read v0 = output size, and
read [a1] (the decompressed header).
Decide: does the decompressed-output region [a1, a1+size) contain the floor 0x801bdc58?
  YES -> the floor lives in the DECOMPRESSED output; its editable coordinates are there (runtime/transient),
         and the file-side edit path is decompress->edit->recompress (codec decode required first).
  NO  -> 0x801bdc58 is a different allocation; re-examine the bracket.
```

This is one breakpoint, no RAM dump, no flaky `0x800108b4` repro, no patch. It pins the decompressor I/O mapping
and confirms the floor is decompressor output — the precise question G22 left open. (Optional follow-on: WRITE-watch
`0x801bdc58` to catch the decompressor writing the floor and read the decode cursor at that instant.)

**G24 UPDATE (2026-06-15):** `fcn.8001a1dc` is now statically decoded (PARTIAL) — a custom **LZSS/LZ77 +
variable-length-code** decompressor (MSB-first guard-bit reader; main loop `0x8001a658` flag bit 0=inline literal
byte / 1=back-ref match; var-len length code with byte-`==0` terminator; 16-bit distance hi-bits + inline low byte;
back-ref `out−dist−1`; bit-driven termination). The exact code tables and the dead `word0`/`word1` header fields
are not byte-exact, so **no offline decoder was invented**; the recommended `EXEC 0x8001a1dc` runbook (capture
`a0`/`a1`/output) is the way to get ground truth. Full grammar:
[geometry_g24_level_raw_decompressor.md](geometry_g24_level_raw_decompressor.md).

## 7. Guardrails
No patch, no build. No DAT/CUE/BIN/RAW/RAM/save-state committed. `0xa81ac` is **compressed** — do not treat it as a
coordinate/payload; do not patch it. Do not patch the runtime/output address `0x801bdc58`. Collision/pathing
**UNKNOWN** — visual ≠ collision.

## 8. Reproduce (read-only)
```bash
python3 - <<'PY'
import struct, collections
lr=open('REBUILD/files/LEVEL01/LEVEL.RAW','rb').read()
off=0xa81ac
print('bytes@0xa81ac:', lr[off:off+16].hex(' '))
seg=lr[0xa8000:0xa8400]; print('distinct bytes/1024 =', len(set(seg)), 'zeros =', seg.count(0))  # ~213, 25 -> compressed
# no clean fcn.80010000 payload anywhere:
import struct as st
n=len(lr); s16=lambda o:st.unpack_from('<h',lr,o)[0]; u32=lambda o:st.unpack_from('<I',lr,o)[0]
cnt=sum(1 for o in range(0,n-16,4) if 8<=u32(o)<=2000 and o+4+u32(o)*0xc<=n and all(s16(o+4+i*0xc+6)==0 for i in range(0,u32(o),max(1,u32(o)//50))))
print('clean payload-shaped blocks (pad==0):', cnt)   # 0
PY
# the decompressor + its single caller:
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8001a1dc -c 'pd 40' /tmp/abltext.bin   # BE word-fetch + bit reader
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8001a418 -c 'pd 18' /tmp/abltext.bin   # literal-run copy lbu;sb
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003a4c0 -c 'pd 12' /tmp/abltext.bin   # caller: a0=src,a1=[gp+0x588]
```
