---
kind: system
id: SYS_registered_chunk_image_resources
aliases:
- SYS_registered_chunk_image_resources
- registered chunk image resources
- pointer-registered LEVEL.RAW chunks
status: solved
confidence: confirmed
source_state: original_game
row: E16_streaming_overlays
functions:
- FUNC_8003A318_high-heap_loader_+_LEVEL.RAW_decompress_orchestrator
- FUNC_8003C8BC_level_texture_stage
- FUNC_8003C388_vram_upload_wait
memory:
- MEM_8009B4E8_registered_chunk_table_0x30_0x57
- MEM_8009C170_registered_chunk_table_0x28_0x2F
- MEM_800A6450_registered_chunk_table_0x58_0x5F
evidence:
- EXP_2026-08-04_phase4_e16_registered_chunk_consumers
- analysis/phase4_e16_registered_chunks.json
- analysis/phase4_e16_table_read_watch.json
src_paths:
- tools/phase4_e16_registered_chunks.py
- tools/phase4_e16_image_header.c
- tools/phase4_e16_table_read_watch.py
- tools/phase4_e16_decode_registered_image.py
- tools/mips_ea_window.c
patch_policy: safe_to_read
---

# SYS - Registered chunk image resources (deferred VRAM upload)

## What it is

Most LEVEL.RAW chunks are decoded by the loader as it walks the file. Chunks
whose subtype marker falls in **`0x28..0x5F`** are different: the loader
**records the decompressed chunk's address in a pointer table indexed by the
marker and moves on without interpreting it**. Something else uploads it later.

That "something else" is the frontend's image path. All 46 such chunks in the
retail game live in **LEVEL00** — the frontend — and they are its art: menu
icons, pre-rendered UI text, and the title screen.

## The three tables

| markers | displacement base | occupied window | consumer |
|---|---|---|---|
| 0x28–0x2F | 0x8009C170 | 0x8009C210–0x8009C22F | `vram_upload_wait` @0x8003c3c0 → `LoadImage` |
| 0x30–0x57 | 0x8009B4E8 | 0x8009B5A8–0x8009B647 | `level_texture_stage` @0x8003c920 → `level_texture_upload` |
| 0x58–0x5F | 0x800A6450 | 0x800A65B0–0x800A65CF | `vram_upload_wait` @0x8003c5ec → `LoadImage` |

`slot(marker) = displacement_base + marker*4`, using the **raw** marker. The
displacement base is not the first occupied slot — see
[[MEM_8009B4E8_registered_chunk_table_0x30_0x57]].

## The two formats

The split is not a modelling choice; the two consumers read different widths.

**Family A — markers 0x28–0x2F** (consumer uses `lw`, payload at `+16`):

```
u32 marker  @0
u32 width   @+4
u32 height  @+8
u32 ?       @+12
16bpp direct-colour pixels @+16
size == 16 + width*height*2
```

**Family B — markers 0x30–0x5F** (consumer uses `lhu`, payload at `+12`):

```
u32 marker        @0
u16 width         @+4
u16 height        @+6
u16 palette_bytes @+8      (768 in all 43 retail chunks)
u16 depth_flag    @+10     (1 = 8bpp, 0 = 4bpp)
palette (256 x RGB888) @+12, then indexed pixels
size == 12 + palette_bytes + width*height / (1 if 8bpp else 2)
```

**All 46 retail chunks satisfy their family's law exactly** — 40 at 8bpp, 3 at
4bpp, 3 at 16bpp. There is no free parameter to absorb a bad guess.

Read family A's 32-bit fields as 16-bit and its height and depth flag both look
like `0`; those are the high halves, and that misreading is what once made 6
chunks appear malformed.

## The family-B upload, end to end

`level_texture_stage` reads the `+10` depth flag at `0x8003cb54` and uses it to
rewrite the VRAM rect width — `w>>1` for 8bpp, `(w+3)>>2` for 4bpp, i.e. how
many pixels pack into one 16-bit VRAM word. The rect is built at `0x80089848`
and handed to `LoadImage` with the pixel source at
`chunk + 12 + (palette_bytes & ~1)`.

The palette is copied to a stack buffer and walked **three bytes at a time**
(code-level proof of 256 × RGB888), each component scaled to 75% by `(v*96)>>7`
— **except** entries matching `R<5 && G>=250 && B<5`, which pass through
untouched. That is the pure-green **transparency key**: marker `0x30` has
exactly one such entry (index 0 = `(0,255,0)`), used by all four corners and 50%
of the image. Scaling it would turn 255 into 191 and break the match.

`level_texture_upload` runs twice — once on the chunk's palette, once on the
scaled copy — staging both a normal and a dimmed CLUT.

## Confirmation

Decoding with this layout produces recognisable retail art — marker `0x43` is
the memory-card UI atlas ("please wait / load / save / exit / not an "a bug's
life" save game / press ○ to load"), marker `0x28` is the 320x256 title screen.
`tools/phase4_e16_decode_registered_image.py` reproduces it; the renders are not
committed because the art is copyrighted.

## Ownership and lifetime — and a dangling-pointer hazard

The tables hold raw pointers with no refcount, size or owner field, and the three
are **not** treated alike:

- **0x28–0x2F and 0x58–0x5F are zeroed by the loader's init on every load**
  (`0x8003a3bc`, `0x8003a3c0`).
- **0x30–0x57 is cleared by the startup bulk-zero loop, but not by the
  per-load loader init.**

An earlier revision collapsed those two lifetimes into "never cleared." That was
wrong: the pristine loop at `0x8005F690..0x8005F6B0` zeroes
`[0x80082200, 0x800B39A0)`, including this table. What the later replay proves is
that the table is not cleared again at the frontend-to-gameplay load boundary.

Replaying boot → frontend → Clover Forest: 38 slots are populated in the
frontend, and 36 still hold pointers after the game has moved to a gameplay
level. Those 36 are **genuinely dangling** — a chunk's marker is a `u32` at its
own offset 0, and **0 of 36 still read back their marker**. They point into
`0x800BE670..0x80181E44` in the high heap, which the gameplay load has refilled
with its own data.

Retail is safe only because nothing calls the upload path for those markers
outside the frontend. The safety is **positional, not structural**: nothing on
the path validates a pointer. `level_texture_stage(marker)` would fetch the
dangling pointer, read garbage `u16` width/height/palette_bytes out of gameplay
data, and hand that to `LoadImage` — a VRAM DMA sized by those garbage fields.

⚠️ **Modding:** a mod that reuses this upload path during gameplay (custom HUD
or menu art) must re-register the chunk first. The table still *looks* populated.

See [[EXP_2026-08-04_phase4_e16_resource_lifetime]].

## The methodological trap in this one

The consumers index the table:

```
lui  $at, 0x800A
addu $at, $at, index
lw   $v0, DISP($at)
```

so **their displacement is not the table's base**. A static scan matching the
base displacement — run over the resident EXE *and* all 30 `.BIN` files, both
addressing forms, with a check that the addresses never appear as data
constants, and a `$gp`-reachability argument — returned **three stores and zero
reads**. It was thorough, and it was wrong: the 0x30–0x57 reader sits at
displacement `-19032`, just outside the `[-19224, -19064]` base window.

A live `readwrite` watch found all three consumers in a single run. The lesson
is not "static analysis is unreliable" but that **a search's completeness is a
property of the search's own assumptions** — here, the assumption that a table
is addressed from its base.

The sibling failure mode is recorded in the auto-memory as
`knockdown-not-a-slot-writer`: never encode an inference as a passing structural
check.

## Resolved materialisation sites do not close the consumer set

The section above ends on the right lesson — *a search's completeness is a
property of the search's own assumptions* — and a 16-level any% campaign then
found the assumption that was still load-bearing here.

**Two of them, in fact, and they are independent:**

**SCOPE.** Every static census behind this page ran over
`analysis/functions_resident.txt`: 998 functions covering **90.1%** of the
resident text, leaving 46,360 bytes unanalysed — of which **32,144 bytes in 12
gaps are majority-non-zero live code** (a reachability-only count of 46,020 was
corrected 2026-08-04; a fifth of it is zero words below `$gp`). The campaign caught `0x80010BF4` reading a table window,
and that address is in no listed function: `per_object_mesh_draw_payload_emitter`
is recorded as 724 bytes, but `0x80010C88` is `j 0x800102D4` — its own loop head.
The function's whole body was in the hole. → `tools/text_coverage_audit.c`.

**FORM.** That access's base is a **register**, not a `lui` constant, so the
affine census is structurally blind to it. Repairing the function list would not
have surfaced it. This is the same wall that stopped B06/B08 and E15.

### The materialisation scan and its limit

**Correction history.** An earlier revision called this a bounding argument and
said every deliberate address must be locally `lui`-materialised. That was wrong.
The scanner reports one common encoding; it does not chase stored/reloaded pointers,
arguments, derived aliases, CFG joins, or every register definition.

Against the three tables the linear scanner reports **5 sites, every one listed on
this page** — the
two loader address-takes feeding the init clears, and the three consumer reads in
`level_texture_stage` / `vram_upload_wait`. Plus 815 near misses within 512 B,
which is simply the neighbourhood being dense.

That is a five-hit encoding result, not a complete access census. The runtime campaign
corroborates the listed consumers for those executions but cannot close unseen paths.
→ `tools/const_address_materialization.c`.

### The incidental reader you will see in a watch

The campaign's two finds are a load the compiler scheduled **above its own bounds
check** — it reads `base+index` regardless and discards the result on the failing
path. `0x80010BF8`: 53 reads over 7 levels. `0x80010DA0` (the byte-identical
sibling 424 bytes later, which surfaced only on the **last** movie): 51 reads
across all 8 words of the `0x58..0x5F` window. All reads, never a write.

⚠️ There are **22 such sites** (`tools/hoisted_load_idiom_scan.c`), all in the
geometry emitters. They will show up in any `accessLog` watch over these tables
looking exactly like an unenumerated consumer. Match events against the logged PC
(= load PC **+4**) and check this family before concluding you have found a new
reader — that is now a general caution for watch work in this project, not a
footnote to this system.

## Related

- [[Asset_-_LEVEL.RAW_Chunk_Role_Table]]
- [[Asset_-_LEVEL.RAW]]
- [[SYS_overlays_and_runtime_loading]]
- [[EXP_2026-08-04_phase4_e16_registered_chunk_consumers]]
- [[EXP_2026-08-04_phase4_e16_anypercent_campaign]]
