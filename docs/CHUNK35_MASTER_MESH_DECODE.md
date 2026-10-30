# Chunk-35 master mesh — first real decode

> ## ⛔ CORRECTION 2026-08-11 — THIS IS NOT THE WALL LAYER
>
> Confirmed in-game by **looking at** the changed pixels, not by counting them. Editing chunk-35
> records changes exactly **Flik's on-screen silhouette** — head, raised arm, torso, legs — with a
> blob displaced *above* him (the `dy −400` shift; −Y is up). The diff bbox grows with the character
> as more records are edited (12×5 → 32×216 → 42×259 → 42×284 px), always centred on him at
> x≈399, **never on terrain**. See `build/c35_R0_117_diff.png`.
>
> Corroborating measurements: the mesh spans only X[−61,61] Y[−566,−1] Z[−122,91] — tall, thin, and
> small, i.e. a standing character, not terrain; and 183 primitives is an ordinary PS1 character
> poly budget.
>
> **So chunk 35 holds an ACTOR/CHARACTER model and `FUNC_800172DC` is an actor-model renderer.**
> The older `walls-are-chunk35` headline is what misled me here — note that memory had already
> corrected itself to *"chunk 34/35 = shared MODEL ARENA, not wall-only"*, and I over-weighted the
> headline. The wall attribution came from poking the runtime buffer `0x8012C1D0`, which is a
> different structure from chunk 35's on-disc content.
>
> **Everything below about the FORMAT stands** — the grammar, the code ties, the authoring results.
> Only the claim about WHICH geometry it is was wrong. The remaining alternative I cannot exclude:
> the mesh is drawn coincident with Flik rather than being his model.


**Date:** 2026-08-11 · Tool: `tools/chunk35_master_mesh.c` (C, per the standing ASM-probing rule)
· Data: `build/chunk35/LEVEL01_chunk{34,35}.dec`

## Why

Chunk 35 was *believed* to be the terrain master mesh — the layer drawing LEVEL01's big brown
wall/terrain masses through `FUNC_800172DC` as GP0(3c) quads, and the only layer a Tier-3
replacement level still could not author. **That identification is now falsified** (see the banner
above); it is an actor/character mesh. The format work below was done under the old belief and
remains valid. Everything else (visible terrain, collision, decor, backdrop) is already replaceable
at source; chunk 35 could only be hidden with a runtime stomp. Replacing it needs to know which
bytes are coordinates and which are draw commands — recorded as blocked since 2026-07-04, because a
blanket 0x30-stride edit **crashes the load** while an identity recompress and a single aligned
vertex edit both boot.

## Result — the grammar accounts for every byte

```
$ ./build/chunk35_master_mesh walk build/chunk35/LEVEL01_chunk35.dec 0xc
consumed to +0x034f4 of 0x034f4 -- EXACT, the grammar accounts for every byte
groups=12 prims=183 verts=200 indices=1761
   0x34 (3-pt textured gouraud): 42
   0x3c (4-pt textured gouraud): 141
```

183 primitives sits right against the live measurement recorded for the runtime buffer
(`0x8012c1d0`, *"the buffer has ~199 quads here"*).

### Primitive record — CONFIRMED

A record starts on a **word boundary** with `RGB | GP0-command` (colour in the low three bytes,
command in the high byte) and its length follows the standard GP0 polygon field rules:

```
nverts   = (cmd & 0x08) ? 4 : 3
textured = (cmd & 0x04)
gouraud  = (cmd & 0x10)
words    = (gouraud ? nverts : 1) + nverts + (textured ? nverts : 0)
```

Only two commands occur: `0x3C` (4-point gouraud textured, 12 words = **0x30**) and `0x34`
(3-point gouraud textured, 9 words = 0x24). The 0x30 figure is exactly the stride recorded for the
runtime render-quad buffer, and the vertex words the earlier live probe found at `+0x04/+0x0c/
+0x14/+0x1c` are this record's four vertex words — the on-disc record and the runtime quad line up.

### Group structure — CONFIRMED to byte-exactness

```
group := primitive-record+  0x00000000  u32 vcount  vertex[vcount]  u16 index[...]
vertex := s16 X, s16 Y, s16 Z, u16 tail   (tail is 0x0110 throughout the samples read)
```

Two rules were each found by a **failed** walk, and both are recorded because guessing either way
round derails the parse:

1. **A primitive record must be word-aligned.** The index list is u16, so scanning every halfword
   finds a phantom primitive — it did, at `+0x24e`, and the walk died two groups in.
2. **`0x00000000` is not always a group terminator.** At `+0x4e8` it is followed by another GP0(0x34)
   record, so it doubles as a run separator. Treat it as a terminator only when what follows is not
   itself a primitive.

### Regularity worth chasing

Every fully-formed group has **verts = 2 × prims** (5/10, 3/6, 7/14, 7/14). Group 5 has 9 prims and
0 verts. Not explained.

## ✅ TIED TO CODE (2026-08-11, second pass)

`FUNC_800172DC` disassembled. Every structural claim above is now anchored to an instruction —
see Canon [[FUNC_800172DC_master_mesh_renderer]] and [[SYS_chunk35_master_mesh]] for the full map.

| grammar claim | instruction |
|---|---|
| high byte is the GP0 command; dispatch on the standard polygon bits | `and t1, t0, 0x3C000000` / `bne t1, at` @ `0x800173E4` |
| quad record is **0x30** | `addi a1, a1, 48` @ `0x80017798`, `0x80017828` |
| triangle record is **0x24** | material byte `lb s1, 35(a1)` @ `0x80017418` (quad: `lb 47(a1)`) |
| four vertices at `+0x04/+0x0C/+0x14/+0x1C`, XY word + Z word | `lwc2 $0..$5` @ `0x80017444..58` plus `mtc2` of `+0x14/+0x18` |
| count/stride-8 block: `u16` count at `+0`, data at `+4`, stride 8 | `lhu s0,0(v1)` / `addi v1,v1,4` / `sll s0,s0,3` @ `0x80017378` |
| that block is walked one entry per primitive | `addi s6, s6, 8` @ `0x80017790`, `0x80017820` |

Two corrections to the first pass:

- The count is a **u16 at `+0` with data at `+4`**, not a u32 — the observed `0a 00 00 00` fits both,
  the code settles it.
- I nearly banked a wrong tie: `sll s0, s0, 3` looked like it doubled as the far-clip distance used
  at `0x80017488`. It does not — `s0` is **reloaded** from `[0x80082254]` at `0x80017390` in between.

### ⚡ And the payoff: this layer selects its own material

```
lb   s1, 47(a1)      ; quad (tri: 35(a1)) -- the record's LAST byte
andi s1, s1, 0x001F  ; 5 bits
sll  s1, s1, 1
add  s2, s1, 0x800A7DD8
lhu  s2, 0(s2)
```

A chunk-35 primitive carries a **5-bit material index in its last byte**, resolved through a runtime
table at `0x800A7DD8`. A `FUNC_80010000` DAT payload cannot do this — its CLUT is render-time state
(`geometry_g57`), so its material is only texture cell × per-vertex colour. The wall CLUT behind the
reference cliff's red-brown lives in *this* layer, which is exactly why the authored DAT floor could
not reach it.

## ✅ IN-GAME: the decode is writable — a single record edited, cold-booted, and visible

`tools/edit_chunk35_record.py` edits vertices **through the grammar**, re-walks the result and
refuses to emit if the grammar no longer accounts for every byte. Discs built with
`build_autolayout_disc.py`, gated with `mod/smoke_test.py`, and frames compared pixel-wise against
an identity-recompress control (the smoke metrics are identical across all of these, so the frame
diff — not the gate — is the measurement).

| disc | edit | gate | pixels changed vs control |
|---|---|---|---:|
| `ABL_C35_IDENTITY` | recompress only | PASS | **0** (bit-identical to pristine) |
| `ABL_C35_REC0` | record 0, `dy −400` | PASS | **47** |
| `ABL_C35_R0_9` | records 0–9, `dy −400` | PASS | **756** |
| `ABL_C35_R0_57` | records 0–57, `dy −400` | PASS | **2,797** |
| `ABL_C35_G9` | records 58–117, `dy −400` | PASS | — |
| `ABL_C35_R0_117` | records 0–117, `dy −400` | PASS | — |
| `ABL_C35_R118_182` | records 118–182, `dy −400` | **BOOT FAIL** | — |
| `ABL_C35_R118_UP` | records 118–182, `dy +400` | **BOOT FAIL** | — |
| `ABL_C35_QUADS` | all 141 `0x3C`, `dy −200` | **BOOT FAIL** | — |
| `ABL_C35_SMALL` | all 183, `dy −10` | **BOOT FAIL** | — |
| `ABL_C35_ALLDY` | all 183, `dy −200` | **BOOT FAIL** | — |

The identity control is bit-identical to the pristine disc's frame, so the 47 pixels are the edit
and nothing else. **The chunk-35 master mesh is authorable on disc**, and the pixel count scales
with the number of records edited (47 → 756 → 2,797).

### The frontier: records 0–117 are authorable, 118–182 are not

**Records 0–117 (118 of 183) can be edited freely** — `dy −400` across all of them boots and
renders. **Records 118–182 break the load**, and they do so in *either* direction.

Four hypotheses died to the bisect, each recorded so none is re-derived:

| hypothesis | killed by |
|---|---|
| magnitude — the shift is too large | `dy = −10` over all records **fails**, `dy = −400` over 118 records **passes** |
| the `0x34` triangle layout is wrong | quads-only (141 × `0x3C`) **fails** |
| run 9 is special (a 60-record outlier vs ≤10 elsewhere) | run 9 **alone** (records 58–117) **passes** |
| Y extent — pushing past the original `Y[−566,−1]` | records 118–182 shifted **+400**, back *into* range, **also fails** |

So it is those records specifically, not how far or which way they move. Run sizes for context —
note the singleton runs at 118, 119, 143, 144:

```
run sizes: 5 3 7 4 9 7 4 9 10 60 [1] [1] 10 4 9 [1] [1] 10 4 9 5 5 5
            ^-------- 0..117 edit cleanly --------^ ^--- 118..182 break the load ---^
```

Records 118/143 and 119/144 are X-mirrored pairs of each other, so they are real geometry rather
than obvious mis-parses — the grammar is not visibly wrong there, which is why this is a frontier
and not a bug with a known fix.

The failing discs hang on a **clean loading screen** (`build/ABL_C35_ALLDY_smoke.png`), not a
corrupted one — so the load path stalls rather than splattering memory, unlike the 213-sector DAT
failure.

### Run count: 23 runs / 22 boundaries — the header's `22` probably means this

Counting primitive runs rather than terminator-plus-vertex-block occurrences gives **23 runs and 22
boundaries**, against the header byte `0x16` = 22 at `+0x09`. My earlier "12 groups" undercounted
because the walk does not increment its group counter on the separator case. Candidate resolution,
not proof.

## What is NOT established

- **Why records 118–182 break the load.** Bounded precisely and four hypotheses eliminated (see the
  table above), but the mechanism is unknown. The leading remaining candidate is that their vertices
  are load-bearing beyond geometry — the loader is documented as welding vertices by position, and
  the runs' own vertex/index blocks are NOT edited in step with the primitives.
- **The `0x34` vertex layout.** Its material byte at `+0x23` is proven; its vertex offsets are not —
  the triangle path loads `lwc2 $1..$5` from `+0x08..+0x18`.
- **Scale.** Chunk 35's vertices span only X[−61,61] Y[−566,−1] Z[−122,91] — a small model, not a
  large terrain mesh. Whatever places/scales it at draw time is unidentified, so calling this "the
  wall layer" rests on the 2026-06-24 live poke, not on anything measured here.
- **The side array's purpose.** It is walked one 8-byte entry per primitive (`lh +0`, `lhu +2`,
  `lhu +4`, `lhu +6`) but what those fields mean is unknown.
- **The per-vertex aux halfwords** at `+0x0A/+0x12/+0x1A/+0x22`, read with `lh` and copied into the
  output packet at `s3+0x18/+0x24/+0x30`.
- **Chunk 34 does not use this grammar** from its data start (marker `0101`, and its header carries
  what look like absolute offsets `0x29998 / 0x2b828 / 0x2a368`, all inside its 182,342 bytes —
  i.e. an offset table). Chunk 34 is a different container and was not decoded.
- **The loader.** `FUNC_8002958C` is **not** the converter: disassembled, it is slot/modulo-100
  arithmetic over a 128-entry table at `0x800992A8` and a struct at `[0x800AEE5C]`. `0x8012c1d0` is
  never materialised as a constant, so the buffer is reached through a pointer; whoever fills it is
  still unidentified. `FUNC_800172DC` (now decoded) is the *consumer*, not the loader.

## Next steps, cheapest first

1. **Attempt the smallest authored edit** — rewrite one `0x3C` record's four vertex words and
   cold-boot it. A single aligned vertex edit is already known to boot, so this is the short step
   that converts the decode into the ability to replace the layer.
2. **Resolve 12 vs 22.** If 22 is the real sub-mesh count, the walk is merging groups.
3. **Find the loader** (see above) if a size-CHANGING edit is ever needed; a size-preserving edit
   does not require it.
4. **Exercise the material index.** The 5-bit selector is the lever for authoring the wall CLUT.

## Tool

```
chunk35_master_mesh disasm <SCUS_942.88> <va-hex> <count>   annotated MIPS
chunk35_master_mesh xref   <SCUS_942.88> <va-hex>           j/jal + lui/addiu-ori references
chunk35_master_mesh header <chunk.dec>                      header bytes + candidate counts
chunk35_master_mesh scan   <chunk.dec> <off-hex>            0x30-block census
chunk35_master_mesh walk   <chunk.dec> <off-hex>            the grammar above, with byte accounting
```

`walk` prints where and why it stops. It is built to **fail loudly** — a hypothesis that quietly
consumes the wrong bytes is worse than none.

```bash
gcc -O2 -Wall -Wextra -o build/chunk35_master_mesh tools/chunk35_master_mesh.c
```

---

# Frontier narrowed: records 151–182 (2026-08-11)

Bisecting the 118–182 breaking region:

| records edited (`dy −400`) | result |
|---|---|
| 0–117 | PASS |
| **118–150** | **PASS** |
| **151–182** | **BOOT FAIL** |

So the breaking set is **records 151–182 (32 of 183)**, and **151 of 183 records are now known
editable**. Five hypotheses are dead (magnitude, `0x34` layout, run 9, Y extent, and now
"everything past 117"). Further bisection is cheap — each step is one disc — but chunk 35 is an
actor mesh, so this is no longer on the critical path for level authoring.
