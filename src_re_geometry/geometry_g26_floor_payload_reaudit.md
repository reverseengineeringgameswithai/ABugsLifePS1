# G26 — `0x801bdc58` is compressed LEVEL.RAW source, NOT a floor render payload (re-audit + pivot)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G25 post-decompress trace](geometry_g25_level_raw_post_decompress_trace.md) ·
[← G23 LEVEL.RAW is compressed](geometry_g23_level_raw_floor_format.md) ·
[← G22 high-heap floor source](geometry_g22_high_heap_floor_source.md) ·
[← G18 output-buffer floor trace](geometry_g18_output_buffer_floor_trace.md) ·
[← G17 floor payload candidates](geometry_g17_floor_payload_candidates.md)

Status: **CORRECTION + PIVOT (operator ground truth + read-only `SCUS_942.88` re-audit, 2026-06-15).** No patch,
no build. No collision/pathing claims — visual ≠ collision.

> **Headline (CORRECTION).** Two operator checks **falsify** the long-running "`0x801bdc58` = walkable-floor
> `fcn.80010000` payload" assumption (G17 Candidate B → G18 → G19 → G22 → G25):
> 1. At **`Press X to Continue`**, memory at `0x801bdc58` = `70 D4 00 1A` = `0x70d4001a` — **exactly**
>    `LEVEL.RAW[0xa81ac]` (the compressed-source word, G22/G23).
> 2. **WRITE watch `0x801bdc58` during LEVEL01 load = 0 hits** — nothing ever writes there.
>
> So `0x801bdc58` holds **compressed LEVEL.RAW source bytes, unchanged across the whole load**. It is **NOT** a
> generated/decompressed render payload, and it never was. The walkable-floor/top-surface render payload pointer
> is **UNKNOWN** and must be re-found from the **consumer** side (`fcn.80010000`) with an **on-the-spot vertex-count
> validation** (§4). The LEVEL.RAW loading/decompression RE (G22–G25) **stands** as characterization of the
> LEVEL.RAW resource pipeline — it just never proved anything about the floor render payload (§3).

> **✓ G27 UPDATE (2026-06-15) — the §4 runbook RAN.** The operator captured five `fcn.80010000` payloads at
> **PRIMARY EXEC `0x80010000`** in the Candidate-B floor view; **all five pass the §2 acceptance test** (`[a0]` =
> claimed count exactly: 83/48/58/36/25; `pad==0`; clean `ffff ffff` terminators) and **all are DAT-backed**. They
> split by structure into **A/B/C = flat, wide, world-space floor-stratum chunks** and **D/E = model-space
> prop/decor** (E = the G18b `0x2d460` instanced ×93). **Candidate A** (`DAT 0x188cc`, 83v, flat **0.154**,
> Y-band 316, 4502×4502, unique) is the **strongest floor/top-surface candidate** and is **DAT-backed → directly
> editable**. This **downgrades** the old "floor is not in LEVEL.DAT" inference (it rested on the retracted
> `0x801bdc58`). Remaining gate (per §4 SECONDARY + G16): screen-XY-confirm A lands on the lower-center walkable
> band before any edit. Full decode/classification:
> [geometry_g27_count_validated_floor_candidates.md](geometry_g27_count_validated_floor_candidates.md).

## 1. Ground truth (operator) — CONFIRMED

| check | result | meaning |
|-------|--------|---------|
| `[0x801bdc58]` at `Press X to Continue` | `70 D4 00 1A` (LE `0x70d4001a`) | = `LEVEL.RAW[0xa81ac]` exactly → still **compressed source** |
| WRITE watch `0x801bdc58` during load | **0 hits** | nothing writes the floor address; not decompressor output (G25), not a builder target |
| ⇒ classification | **compressed LEVEL.RAW source byte (LEVEL.RAW + 0xa81ac)** | NOT an `fcn.80010000` payload, NOT a coordinate, NOT editable |

`0x801bdc58 − 0x80115aac (LEVEL.RAW load base, G22) = 0xa81ac`. The compressed buffer `[0x80115aac, 0x801cc690)`
is loaded by DMA (no CPU stores → consistent with the 0-hit write watch) and the upper region around `0x801bdc58`
is consumed-but-not-overwritten compressed data (G25: decompressor output `a1`/`fp` tops at `0x8015fcbc`, `0x5df9c`
below the floor address). Both facts now converge: **`0x801bdc58` is compressed source, full stop.**

## 2. Acceptance test for a real `fcn.80010000` payload base `P` (CONFIRMED format, G11)
A genuine payload is `{ u32 vertexCount; Vertex verts[N] (stride 0xc: s16 x;y;z; s16 pad=0; u32 attr); u16 command
stream }`. So for any candidate base `P`:
- **`[P]` (first word) must be a plausible vertex count** — small positive. LEVEL01 observed counts: 25, 34, 63,
  92, 110, 195, 230… → bound ≈ `1..few-thousand`.
- the **vertices at `P+4`** must read as coordinates (s16 with `pad==0`), **not** high-entropy/compressed bytes.

`0x801bdc58` **fails both**: `[0x801bdc58] = 0x70d4001a = 1,892,548,634` (impossible — LEVEL.RAW is only `0xb68e4`
≈ 748 KB total), and the `0xa81ac` window is 213 distinct bytes/1024 = compressed (G23). **⇒ not a payload.**

## 3. Re-audit: why the old `0x800108b4` evidence pointed here (disasm-grounded)

**The `a0 − 4` formula is CORRECT — that is *not* the bug.** Read-only re-disasm of `fcn.80010000`:
- entry `0x80010000`: `t7 = [a0]` = count; `bgtz t7 → 0x8001024c` (count>0 main path), delay slot `a0 += 4`;
  `0x80010040 s5 = a0` (vertex base).
- **count>0 main path `0x8001024c..0x800108xx`: `a0` is NEVER written** (the only `a0` writes are the entry
  `a0+=4` and the count≤0 sub-path `0x8001009c/ec/0x8001014c/0x80010174`, all `< 0x8001024c`). `a0` is *read* as the
  vertex base for address math (`vtx = byte_offset + a0`, e.g. `0x80010474/8c/9c/a4`). **`s5` is reused**
  (`lui s5,0x8008` @`0x80010298`), so `s5 ≠` vertex base in the main path.
- packet-store gate `0x800108b4 = addi s3,s3,0x34`: `s3` = GPU packet/OT cursor (loaded `lw s3,(t2)` with
  `t2=0x800823f4`); `s0` = vertex cursor; **`a0` = payload+4 = vertex base**.

So at `0x800108b4`, **`payload base = a0 − 4` is the right recovery for a genuine call.** The error is therefore
**not** the formula but that **the recovered base was never count-validated on the spot**:
- The G17 Candidate B log recorded `a0 = 0x801bdc5c` ⇒ payload `= 0x801bdc58`, whose first word is `0x70d4001a`.
- A real `fcn.80010000(payload=0x801bdc58)` would read `count = 0x70d4001a` (~1.9 billion) and walk a command
  stream at `a0 + count*0xc` (wildly out of bounds) — it **cannot** "emit 17 clean primitives then move on."
- ⇒ those `0x800108b4` hits did **not** correspond to a valid floor-payload draw at `0x801bdc58`. Per the
  operator's read: **wrong timing/context, a stale/coincidental `a0`, or an `a0`-interpretation that did not apply**
  — and crucially the count at `a0−4` was never checked. (The exact misread cannot be reconstructed offline; the
  inference is simply falsified, and the fix is to validate `[P]` at capture time — §4.)

**Net:** keep the *mechanism* (`a0−4` ⇒ payload base at `0x800108b4`; `[a0]` ⇒ count at the `0x80010000` entry),
**drop the conclusion** (`0x801bdc58` is the floor payload).

### What this corrects vs what it preserves
| prior claim | verdict |
|-------------|---------|
| G17 Candidate B: emitted floor/top-surface payload at `0x801bdc58` | **WRONG** — `0x801bdc58` is compressed source |
| G18: `0x801bdc58` = output-buffer/runtime-generated floor payload (DAT source unknown) | **premise WRONG** (not a payload); its *parser-once / reloc-targets `<0x4f32c` / emitter loads `a0` from `[s2+0x1c]`* facts stand |
| G19/G20/G21: trace the *source file* of the data at `0x801bdc58` | **valid as LEVEL.RAW-pipeline RE**; it found the compressed source, not a floor payload |
| G22: floor source file = LEVEL.RAW; `0x801bdc58` = LEVEL.RAW+0xa81ac | **`0x801bdc58 = LEVEL.RAW+0xa81ac` CONFIRMED** (now *proven* by the Press-X byte match); "floor" label dropped |
| G23: LEVEL.RAW is compressed; `0xa81ac` not editable | **CONFIRMED & strengthened** (Press-X value = compressed word) |
| G24/G25: `fcn.8001a1dc` per-chunk decompress loop; word0/word1 = decompressed/compressed sizes | **CONFIRMED** (LEVEL.RAW pipeline) — independent of the floor question |
| G25: "floor built post-decompression near `0x801bdc58`" | **SUPERSEDED** — `0x801bdc58` is never written (write-watch 0); the floor is **not** there at all |
| G16: `0x356bc` visible **wall** deform (DAT-backed payload) | **stands** — a real DAT-backed payload (a wall, not the floor) |

## 4. New runbook — re-find the floor render payload from the consumer side (≤3 BPs, count-validated)

Do this **at a confirmed walkable-floor / top-surface view** (Flik standing on the floor, floor filling the lower
-center of the frame). No patch, no build, no broad decompressor tracing.

**(1) PRIMARY — EXEC `0x80010000`** (`fcn.80010000` entry; `a0` = *raw* payload base, no ±4 ambiguity). Per hit log:
```
PC                      (= 0x80010000)
a0                      = payload base P
[a0]   (first word)     = vertexCount   <-- VALIDATE: plausible small positive; REJECT 0x70d4001a / negative / huge
first 0x40 bytes at a0   (eyeball: u32 count, then s16 x,y,z,pad=0 triples — coordinates, not compressed noise)
a1 (z/flag), a2 (color<<3), a3 (=0x1f800384)
RA                      = caller (builder) -> hints DAT-backed vs generated path
```
Keep only payloads that **pass the §2 acceptance test**. Discard the rest. (This is the step the old evidence
skipped.)

**(2) SECONDARY — EXEC `0x800108b4`** (packet-store gate; only primitives that survive clip/cull reach here =
on-screen). For each hit: `payload = a0 − 4` (a0 = vertex base, CONFIRMED §3); cross-check `[a0−4]` = the same
plausible count; read the GPU packet at `s3` (screen XY at packet `+0x00/08/0c/14/18/20`, or BP `0x80010718` for
`mfc2 SXY0/1/2`). The **floor** payload's primitives project to the **lower/central** screen band and form a wide,
near-horizontal surface (contrast G16's `0x356bc` wall = upper/side).

**(3) CLASSIFY the surviving payload base `P`:**
- `P − DATbase(0x801607f8) ∈ [0, 0x51418)` and `[P]` plausible → **DAT-backed** (directly editable in LEVEL.DAT;
  re-check the G17 static floor shortlist e135 `0x1f148` / e254 `0x08f4c` / e52 `0x17d94` against `P`).
- `P` in the decompressed LEVEL.RAW output region (`< 0x8015fcbc`, G25) → **LEVEL.RAW-decompressed** (edit needs the
  `fcn.8001a1dc` codec: decompress→edit→recompress).
- `P` elsewhere in heap, written at runtime → **generated** (WRITE-watch `P` to find the writer).

## 5. Minimum evidence required before ANY future floor edit
1. **Actual payload pointer `P`** captured at `0x80010000` for the floor view (count-validated).
2. **Source class** of `P`: DAT-backed vs LEVEL.RAW-decompressed vs generated (the §4(3) test).
3. **Payload sanity:** `[P]` = plausible vertex count; `P+4` vertex table = s16 coords (`pad==0`); command stream
   present with a valid (`<0`) terminator — i.e. it parses as a real `fcn.80010000` payload, not `0x70d4001a`.
4. **Visible floor association:** `P`'s emitted primitives (EXEC `0x800108b4` / SXY at `0x80010718`) land on the
   walkable floor/top surface in the floor view.

Only with all four is an edit defensible. (Collision/pathing remains a separate, UNKNOWN question — visual floor ≠
collision floor; do not infer.)

## 6. Guardrails
No patch, no build. `0x801bdc58` is **compressed LEVEL.RAW source** — do not treat it as a payload/coordinate, do
not patch it; do not patch runtime addresses. The real floor render payload pointer is **UNKNOWN**. No broad
decompressor re-trace. Collision/pathing **UNKNOWN**.

## 7. Reproduce (read-only)
```bash
python3 -c "open('/tmp/abltext.bin','wb').write(open('SCUS_942.88','rb').read()[0x800:0x73000])"
# fcn.80010000 entry: a0=payload, [a0]=count, a0+=4, s5=a0 (vertex base):
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x80010000 -c 'pd 28' /tmp/abltext.bin
# count>0 main path: a0 is NOT rewritten; s5 is reused (lui s5,0x8008 @0x80010298):
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8001024c -c 'pd 20' /tmp/abltext.bin
# packet-store gate 0x800108b4: addi s3,s3,0x34 (s3=GPU packet cursor, s0=vertex cursor, a0=vertex base):
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x80010860 -c 'pd 28' /tmp/abltext.bin
# the Press-X byte match (compressed source word):
python3 -c "import struct;lr=open('REBUILD/files/LEVEL01/LEVEL.RAW','rb').read();print(hex(struct.unpack_from('<I',lr,0xa81ac)[0]))"  # 0x70d4001a
```
