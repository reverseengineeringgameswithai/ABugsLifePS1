# G24 — LEVEL.RAW decompressor `fcn.8001a1dc` grammar (partial) + ground-truth runbook

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G23 LEVEL.RAW is compressed](geometry_g23_level_raw_floor_format.md) ·
[← G22 high-heap floor source](geometry_g22_high_heap_floor_source.md) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **READ-ONLY static decode of `fcn.8001a1dc` (2026-06-15).** Read-only `SCUS_942.88` disasm
(`0x8001a1dc..0x8001a8f8`, ~456 instrs) + read-only `LEVEL.RAW` header inspection. **No patch, no build, no
decoder tool** (grammar is **partial** — exact code tables need the runtime ground truth, §7). No
collision/pathing claims.

> **G25 UPDATE (2026-06-15) — two §6 open items RESOLVED by the caller's loop.** The operator's `EXEC 0x8001a1dc`
> trace shows the decompressor is called **MANY times** (a per-chunk loop in `fcn.8003a318`, not once) → answers the
> §6/§99 "once vs per-block" question: **per-block**. And the §6 "`word0`/`word1` computed-then-dead" mystery is
> solved: they are dead *inside* `fcn.8001a1dc` but **live in the caller** — `fcn.8003a318` reads `word1 + 0xe` as
> the compressed chunk stride (`0x8003c264..0x8003c278: s5 += word1 + 0xe`) and `align4(word0)` as the decompressed
> chunk size that advances the output cursor `fp` (`0x8003c13c: fp += align4(word0)`). So **`word0` = per-chunk
> decompressed byte count, `word1` = per-chunk compressed byte count, `0xe` = header length**; a `word0 ==
> 0xffffffff` chunk is the **stream terminator**. The decisive `EXEC 0x8001a1dc` ground-truth run (§7) ALSO produced
> a key negative: the decompressor output cursor `a1`/`fp` tops at `0x8015fcbc`, while the floor `0x801bdc58` is
> `+0x5df9c` above it → **the floor is NOT direct decompressor output**. Full
> record: [geometry_g25_level_raw_post_decompress_trace.md](geometry_g25_level_raw_post_decompress_trace.md).

> **⚠ G26 CORRECTION (2026-06-15).** `0x801bdc58` is now CONFIRMED **compressed LEVEL.RAW source**, NOT a render
> payload: at `Press X to Continue` `[0x801bdc58] = 0x70d4001a` (= `LEVEL.RAW[0xa81ac]`) and a **WRITE watch
> `0x801bdc58` during load = 0 hits** (never written). This G24 decompressor decode is **unaffected** (it describes
> the LEVEL.RAW codec, not the floor). The walkable-floor render payload pointer is **UNKNOWN** — re-find it from
> the consumer side (`fcn.80010000`) with count validation. See
> [geometry_g26_floor_payload_reaudit.md](geometry_g26_floor_payload_reaudit.md).

> **Verdict: grammar PARTIAL.** `fcn.8001a1dc` is a custom **LZSS / LZ77 + variable-length-code** decompressor:
> MSB-first guard-bit reader, flag bit (0 = inline literal byte, 1 = back-reference match), a variable-length
> match-length code with a long-run/byte escape, a 16-bit distance (high bits coded + low byte inline), and a
> **bit-driven terminator** (a zero length-byte). The **structure is confirmed with exact PCs**; the **exact
> length/distance code tables, the header-field meanings, and the (dead) two-stream setup are NOT byte-exact**.
> Per the task rule, **no offline decoder is invented**. The decisive next step is one DuckStation BP that
> captures the **decompressed output buffer** (ground truth), which both validates a future decoder and locates
> the floor in decompressed space (§7).

## 1. Signature, prologue, header (CONFIRMED disasm)

`fcn.8001a1dc(a0 = compressed src, a1 = decompressed dst)` — single caller `0x8003a4e4` in `fcn.8003a318`
(G22), with `a0 = LEVEL.RAW @0x80115aac`, `a1 = [gp+0x588]`.

- **Prologue** (`0x8001a1e0..0x8001a254`): frame `-0x70`, saves **all** GPRs (incl. `k0/k1/gp/ra`); `t3 = sp`
  (scratch base); `sp -= 0x80` (work area). `t6 = a0` (compressed read cursor), `s1 = a1` (output base).
- **Header parse** (`0x8001a270..0x8001a2ec`): reads two **big-endian** 32-bit words from `t6` (`lbu`×4 +
  `<<24/16/8 | or`), each advancing `t6 += 4`:
  - `word0 = BE32[src+0]`  → `a2 = a1 + word0`  (**computed, then NEVER read** — see §6)
  - `word1 = BE32[src+4]`  → `a0 = (t6+0xa) + word1` (**computed, then NEVER read** — see §6)
  - `v1 = t6 + 0xa = src + 0xe`  ← **the bitstream/literal cursor** (decode reads everything from `v1`)
  - scratch: `sw word0,(t3)`; `t3 -= 2`; `sh 0,(t3)` (sets up the §5 flush, which is a no-op here)
- LEVEL.RAW actual header: `word0 = 0x0000830c`, `word1 = 0x00005f0c`, `hdr[8:0xe] = 5b a7 eb 40 02 03`,
  stream `@0xe = 10 00 00 71 01 01 …`. **Header length = `0xe` bytes.**

## 2. Bit reader (CONFIRMED mechanism; exact guard arithmetic LIKELY)

MSB-first, one byte at a time from `v1`, with a guard/marker scheme. The "read 1 bit" idiom (inlined
everywhere) is:
```
t2 <<= 1 ; bit = (t2 >> 8) & 1 ; t2 &= 0xFF        ; emit MSB
if (t2 == 0)  reload:  t2 = *v1++ ; t2 = (t2<<1) | bit ; bit = (t2>>8)&1   ; refill a byte
```
- **Bit order: MSB-first** within each byte (CONFIRMED: `>>8` extracts the just-shifted-out top bit).
- ~9 specialised reload entry points (`0x8001a31c/338/354/370/38c/3a8/3c4/3e0/628/778/794/7b0/7cc/7e8`) — each
  refills a byte and jumps back to the handler that needed the bit (hand-inlined to avoid call overhead).
- The guard makes a byte yield exactly 8 bits before `t2==0` triggers a refill. (Exact marker init is the
  `t2 = 0xffffff00 ; t7 = 1` seed at `0x8001a2f0`; treat the precise edge arithmetic as LIKELY until validated.)

## 3. Main loop = LZSS flag (CONFIRMED) — `0x8001a658`
```
loop:
  bit = read_bit()
  if bit == 0:                 # 0x8001a66c: LITERAL
      *a1++ = *v1++            # copy one inline literal byte
      ... (a fast path 0x8001a648 chains consecutive literals)
  else:                        # 0x8001a690: MATCH  -> §4
      decode_match()
  ... until terminator (§5)
```
So **flag bit 0 = one literal byte copied inline from `v1` to output; flag bit 1 = a back-reference match.**
This is classic LZSS. (A separate **long-literal-run** handler at `0x8001a3fc/0x8001a434` copies `N×4` bytes
inline from `v1` — reached from the length-code escape, §4.)

## 4. Match: length + distance + copy (structure CONFIRMED; exact codes PARTIAL)

**Match entry `0x8001a690`** sets `t0 = 2, t1 = 0`, then reads a **variable-length match-length code** through
the dispatch handlers (`0x8001a488/4a8/4cc/500/520/540/56c/724`), accumulating `t0` via `t0 = t0*2 + bit`:
- escape: when the length code hits **`9`** (`0x8001a4dc: t0-9==0`) → long-literal-run (`0x8001a3fc`, copy `N×4`);
- long lengths: `0x8001a708: t0 = *v1++` (a full byte); **`if that byte == 0 → TERMINATOR`** (`0x8001a804`), else
  `t0 += 8`.

**Distance** (`0x8001a540..0x8001a598`): high bits are bit-coded into `t1`, **byte-swapped** (`0x8001a57c`),
then the **low byte is read inline** from `v1` (`0x8001a590: t1 = (*v1++) | (t1 & 0xff00)`). Back-reference
source: `t6 = a1 − distance − 1` (`0x8001a59c..0x8001a5a4`).

**Copy** (`0x8001a5a8..0x8001a620`): `len` (in `t0`) bytes copied from the output history `t6` to `a1`, handling
an odd leading byte (`t7 = t0 & 1; t0 >>= 1`) then 2-bytes-per-iter; a special path (`0x8001a5d4`, taken when the
distance high byte is 0) does a 1/2-byte **RLE-style** fill. Distances reference already-emitted output → true
LZ77 back-reference.

## 5. Termination + finalize (CONFIRMED mechanism)
- **Terminator:** the long-length byte `== 0` at `0x8001a708` → `0x8001a804` → the exit check `0x8001a834`
  (`bne t7,0 → loop`); when it falls through, decoding ends. **Output size is therefore bit/terminator-driven,
  not `word0`-driven** (`a2 = a1+word0` is never consulted — §6).
- **Finalize `0x8001a83c..0x8001a874`:** reads `t5 = lhu[t3]` (a count) and flushes `t5` halfword→byte entries
  to output. In this path the count is the `0` written at setup, so the flush is a **no-op**; `t3` has **no
  mid-loop pushes** (the scratch stack is vestigial here). Then all GPRs restore, `sp += 0x80+0x70`, `jr ra`.

## 6. Confirmed-unused / unexplained (TODO)
- **`word0`/`word1` are RESOLVED (G25):** dead *inside* `fcn.8001a1dc`, but **read by the caller** `fcn.8003a318`
  per chunk — `word1 + 0xe` = compressed chunk stride (`s5 += word1+0xe`), `align4(word0)` = decompressed chunk
  size (`fp += align4(word0)`). So **`word0` = per-chunk decompressed byte count, `word1` = per-chunk compressed
  byte count, `0xe` = the chunk header length**. (LEVEL.RAW's first chunk: `word0=0x830c`, `word1=0x5f0c`.) The
  `a2 = dst+word0` / `a0 = v1+word1` computed inside the codec remain dead leftovers of a size-checked variant.
- **Once vs per-block is RESOLVED (G25): PER-BLOCK.** The operator's `EXEC 0x8001a1dc` trace shows many hits (a
  loop in `fcn.8003a318`); a `word0 == 0xffffffff` chunk terminates the stream.
- The exact **length-code bit table** and **distance high-bit width** are only partially traced (the handler
  topology is known; the precise bit→value mapping is not byte-exact) — still TODO.

## 7. Recommended next step — ONE BP to capture the decompressed output (ground truth)

Do **not** invent a decoder from the partial grammar. Capture the emulator's correct output instead; it
validates any future decoder byte-exactly **and** locates the floor in decompressed space.

```
EXEC 0x8001a1dc            (decompressor entry; fires at LEVEL01 load from fcn.8003a318)
  record hit count (1 vs many -> single-shot vs per-block)
  record a0 = compressed src base   (expect 0x80115aac = LEVEL.RAW)
  record a1 = decompressed dst base = [gp+0x588]
Set a one-shot EXEC at the return (ra = 0x8003a4e8 in fcn.8003a318); at the return:
  read a1 region start = the dst captured above
  the DECOMPRESSED OUTPUT now lives at [dst .. final_a1)   (final_a1 advanced by the decode)
  dump a modest window of [dst .. dst+0x20000) for inspection (NOT a full broad RAM dump)
Validation vs the floor:
  - the runtime floor payload is 0x801bdc58 (G22). If dst <= 0x801bdc58 < final_a1, the floor is in the
    DECOMPRESSED output; its decompressed offset = 0x801bdc58 - dst  (this is the real, post-decode offset,
    DIFFERENT from the compressed 0xa81ac).
  - search the dumped output for the floor fcn.80010000 payload {u32 count; Vertex 0xc; cmds} to pin it.
```

With that ground truth, a future pass can (a) write `tools/decode_level_raw.py` and verify it reproduces the
captured bytes exactly, and (b) locate the floor's decompressed coordinates for an eventual edit path
(decompress → edit → recompress). **No patch, no build.** Collision/pathing UNKNOWN.

## 8. Clean pseudocode (confidence-tagged)
```c
// fcn.8001a1dc(src, dst)   [CONFIRMED structure; *exact codes PARTIAL*]
u8 *v1 = src + 0xE;                 // CONFIRMED: bitstream + inline literal/distance bytes
u8 *out = dst;
u32 word0 = be32(src+0);           // CONFIRMED read; *use UNKNOWN* (a2=dst+word0 is dead)
u32 word1 = be32(src+4);           // CONFIRMED read; *use UNKNOWN* (a0=v1+word1 is dead)
bitreader br = {v1, MSB_FIRST};    // CONFIRMED MSB-first, byte-at-a-time, guard-bit refill
for (;;) {
  if (br.bit() == 0) {             // CONFIRMED: LZSS flag
      *out++ = *v1++;              // CONFIRMED: inline literal byte
  } else {
      int len = decode_len(&br, &v1);     // PARTIAL: var-len code; escape@9 -> Nx4 literal run;
                                          //          long byte; *byte==0 => TERMINATE*  (CONFIRMED)
      int dist = (decode_hi(&br) << 8) | *v1++;   // PARTIAL: hi bits coded (+byteswap) | low byte inline
      u8 *ref = out - dist - 1;            // CONFIRMED back-reference base
      copy_lz(out, ref, len);             // CONFIRMED: odd-byte + 2/iter, RLE path when hi==0
      out += len;
  }
}
// finalize: flush t3 scratch (no-op here); restore regs; return.  CONFIRMED.
```

## 9. Reproduce (read-only)
```bash
python3 -c "open('/tmp/abltext.bin','wb').write(open('SCUS_942.88','rb').read()[0x800:0x73000])"
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8001a1dc -c 'pd 460' /tmp/abltext.bin   # whole decompressor
# header words (big-endian):
python3 - <<'PY'
import struct; lr=open('REBUILD/files/LEVEL01/LEVEL.RAW','rb').read()
print('word0',hex(struct.unpack_from('>I',lr,0)[0]),'word1',hex(struct.unpack_from('>I',lr,4)[0]),'stream@0xe',lr[0xe:0x1a].hex(' '))
PY
# key PCs: main 0x8001a658 (flag); literal 0x8001a66c; match 0x8001a690; len-escape 0x8001a4dc/0x8001a708;
#          terminator 0x8001a804; finalize 0x8001a83c; a0/a2 computed-but-unused (0x8001a2b0/0x8001a2e4)
```

---

## G31 — GROUND TRUTH CAPTURED (2026-06-17) — codec work unblocked for the level editor

**Why:** building a GUI level editor that moves/adds **seeds** (the plantable points — a separate
system from type-0x3f pickups; see `ObsidianVault/Systems/Seed planting system.md`). Seeds live in
**LEVEL.RAW chunk 32** (decompressed), so the editor needs a real LEVEL.RAW **decompressor + recompressor**.

**The decisive §7 step is now DONE — clean (compressed → decompressed) ground-truth pair captured** via a
DuckStation execute BP at the decompressor entry `0x8001a1dc` (from save `_2` + adv 80 → resume to BP):
- a0 (compressed in) = `0x80115aac`, a1 (decompressed out) = `0x800b5790`.
- chunk0 header CONFIRMS G24: `word0`(decomp)=`0x830c`=33548, `word1`(comp)=`0x5f0c`=24332, hdr `5ba7eb400203`.
- **Compressed chunk0 stream == `REBUILD/files/LEVEL01/LEVEL.RAW` at file offset `0x0`** → the editor can
  operate directly on the LEVEL.RAW file; chunks are sequential (`+ word1 + 0xe` to next compressed chunk,
  `+ align4(word0)` to next output region; `word0==0xffffffff` = terminator, per G25).
- Saved artifacts (the decoder validation oracle): `tools/raw_chunk0_compressed.bin` (24346 B incl 0xe hdr),
  `tools/raw_chunk0_decompressed.bin` (33548 B). decomp head: `00000000 00010001 00030000 5949...`.

**Next (decoder build):** implement `fcn.8001a1dc`'s bit-grammar in Python (MSB-first reader, literal/match
flag, varlen length code, 16-bit distance), validate **byte-exact** against `raw_chunk0_decompressed.bin`,
then decode all chunks. Recompressor can be **literal-only** (LZSS decoders accept all-literal streams) for
a simple, valid round-trip — only needs size headroom in the rebuild. That unlocks seeds + terrain/collision
for the editor in one go.

### G31b — faithful decoder port: 37% byte-exact (2026-06-17)
`tools/decode_level_raw.py` is a faithful instruction-level port of `fcn.8001a1dc`. It decodes
**12271/33548 bytes BYTE-EXACT** against the oracle, then diverges at out 0x2fef. CONFIRMED-correct:
the 9-bit guard bit-reader (init `t2=byte0<<2|2`), main loop, full match length-tree (b1/b2/b3 +
A470 + long-byte terminator), distance (LEN_C/E724/byteswap low-16), the LZ copy **with pre-zeroed
history (negative back-refs read as 0)**, and the Nx4 literal-run. REMAINING bug: a bit-BOUNDARY
guard edge case in the *unmasked* flag path (0x8001a658) — to finish, instrument the live
decompressor's `v1` at out=0x2fef and match the byte/bit alignment. Recompressor (literal-only) is
trivial once the decoder is byte-exact.

### G31c — DECOMPRESSOR BYTE-EXACT ✅ (2026-06-17)
`tools/decode_level_raw.py` decodes chunk0 **33548/33548 bytes byte-exact**, and the full
`LEVEL.RAW` (747748 B) → **1,269,304 B over 69 chunks** (terminator @comp 0xb68d8). The last bug
was the **long-length terminator**: `byte==0` at `0x8001a708` does NOT terminate; it falls to
`0x8001a804` which reads ONE more bit — `bit!=0` ⇒ continue (MAIN), only `byte==0 AND next-bit==0`
⇒ finalize/terminate. CONFIRMED the **seed placement table is in the decompressed output** (records
`(3095,-80,16750)`@0x965d8, `(6145,-2845,5190)`@0x966f0). Editor READ path solved. Remaining for the
write path: a recompressor (literal-only is enough; mirror the guard bit-writer + round-trip vs this
byte-exact decoder).

### G31d — RECOMPRESSOR COMPLETE ✅ (2026-06-17)
`tools/recompress_level_raw.py` is a literal-run encoder, round-trip-validated against the byte-exact
decoder: **full chunk0 (33548 B) round-trips** (decode(encode(x))==x), and edited chunks round-trip
with the edits preserved (~1.02x size). The encoder co-runs the exact decoder register machine in emit
mode, forcing literal-runs (MATCH→A470 b1=0,b4b5b6=1→t0=9→LITRUN, 4-bit count → 4*(C+3) bytes) plus
the terminator. The init asymmetry was the last fix: **byte0 yields 6 flag bits (bits 5→0), reloaded
bytes yield 8 (bits 7→0)** — `first_bits=6`. Public API `compress_chunk(decompressed, header6)`.
**The LEVEL.RAW codec (decompress + recompress) is COMPLETE** — the GUI level-editor read+write path
for seeds (and terrain/collision) is unblocked. Editor flow: decompress → edit seed table → recompress
only the edited chunk(s) → reassemble → rebuild.
