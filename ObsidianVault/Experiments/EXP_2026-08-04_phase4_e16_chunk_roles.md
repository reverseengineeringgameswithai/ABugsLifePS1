---
type: experiment
status: complete
date: 2026-08-04
system: streaming, loaders, overlays
phase: 4
artifacts:
  - analysis/phase4_e16_chunk_census.json
  - tools/phase4_e16_chunk_classify.c
  - tools/phase4_e16_chunk_census.py
  - tests/test_phase4_e16_chunk_census.py
---

# Phase 4 E16: closing the 46 unconfirmed LEVEL.RAW chunk roles

## Question

E16's `next`: "Close the unconfirmed LEVEL.RAW chunk roles (46 'likely')."
The committed census (`analysis/level_raw_chunks.json`) classified 69 chunks of
**one** file (LEVEL01/LEVEL.RAW) from boot traces, leaving 46 as semantic
guesses inferred from load order.

## Method

The row proposed "targeted load traces". A cheaper and stronger instrument
existed: **each chunk carries its own subtype marker — a `u32` at decompressed
offset 0** (the committed chunk-34 note already recorded "marker 0x101@0"; it
generalises). So a chunk's family can be *read off its bytes* instead of
inferred from when it happens to load.

A compiled C classifier (`-Werror`) reads that marker plus the secondary word
at +4; a Python driver decompresses every chunk of **every** `LEVEL*.RAW` with
the committed byte-exact codec and runs the classifier over all of them. One
file proves nothing about a format — 24 files can.

## Results

**All 46 "likely" chunks are confirmed, none contradicted.** Chunks 15–27 carry
marker `0x22` (sprite/animation strip containers) and chunks 36–68 carry
alternating `0x101`/`0x102` (mesh definition / payload) exactly as guessed.

Campaign-wide family counts: 296 texture pages · 228 sprite strip containers ·
208 mesh definitions · 228 mesh payloads · 17 seed tables · 14 collision-plane
chunks · 14 collision sector-source chunks · 9 backdrop panoramas.

**Two exact structural invariants**, holding in every file that has them:

- every **`0x104` collision sector-source** chunk is **17,764 bytes**;
- every **`0x23` seed table** is **1,796 bytes**.

**The mesh pairing law, and its one exception.** Every `0x101` definition has a
`0x102` payload sharing its object id — *never the reverse*, in any file. The
sole asymmetry is **object id 11, which is a payload with no definition in 16
of the 17 mesh-bearing files** (id 0 does the same in 4 files). Worth noting
without over-reading: E05 established that **actor** id 11 is the seed
(`bits\seed`), the corpus's one model with no `.ANM` — but these are *mesh*
object ids inside the RAW, and I have not shown the two numbering spaces are
the same. The coincidence is a lead, not a finding.

**A correction to the committed census.** Chunk 33 was labelled "collision
sector-source *tail*" of chunk 32. Its marker is **`0x104`**, a distinct
subtype from 32's `0x103` — it is its own family, not a continuation, and it
appears exactly once per collision-bearing file at a fixed size.

## The genuinely new residual: 74 chunks the LEVEL01 census could not see

Reading all 24 files exposed a marker space **larger than the committed census
knew**. **74 chunks** carry markers outside every classified family —
`0x20`, `0x26`, `0x28`–`0x2A`, `0x30`–`0x58`, `0x5A`, `0x5C` — concentrated in
`LEVEL00/*.RAW` (52, the menu/training assets) plus `LEVEL08/LEVEL1.RAW` (5)
and `LEVEL09/LEVEL1.RAW` (17, whose every chunk is marker `0x20`).

These were invisible to a LEVEL01-only census, so this pass converts "46
unknown roles" into "46 confirmed + 74 newly enumerated". That is a net
increase in *known unknowns*, which is the honest outcome: the marker values
and their exact file/chunk locations are now recorded, so closing them is a
bounded next task rather than an open-ended one.

## Follow-up: what the 74 unknown chunks are

They are **images**. Every one carries a self-describing header whose `u16`
fields hold plausible pixel dimensions (320×256, 256×256, 160×132, 64×64…).
They are not an unknown *data* family; they are pictures.

**One family is pinned.** Marker **`0x20` = a 320×256 16bpp (RGB555)
full-screen image**, 17 of them filling `LEVEL09/LEVEL1.RAW`. Three
independent lines agree: all 17 chunks share an identical header
`(0x20,0,320,0,256,0)` and identical size 163,856; `16 + 320×256×2 = 163,856`
exactly, with no slack; and bit 15 is clear on all 20,000 sampled pixels, as
expected for opaque RGB555. This corroborates the committed loading-screen
format ("320×256 RGB555 chunk").

**The other 57 are NOT pinned, and I want to be explicit about why.** A
permissive search over (header size, palette presence, dimension fields, bpp,
frame count) "solved" 74 of 74 with a tidy five-class breakdown. Then a
uniqueness check showed **zero of the 74 are uniquely determined** — every
chunk admits 2–12 distinct combinations that reproduce its byte size exactly.
The tidy answer was an **over-fit**, and it is recorded in the artifact as
refuted rather than banked. Leading candidates (12-byte header + 768-byte
palette + w×h at 8bpp for the `0x30`–`0x53` run; 16-byte header + w×h×2 for
`0x28`–`0x2A`) are plausible and unproven.

**Decisive next step**, and it needs no fixture: read the **loader** that
consumes these chunks and see how it interprets the header. The committed
census already records a `loader_caller` (`0x8003A4EC` for LEVEL01 chunk 15).
That is static resident-EXE work.

**Methodological note**, recorded so the next pass does not repeat it: for
self-describing binary resources, matching a size formula is not evidence
unless the fit is shown to be **unique**. Count the alternative fits before
claiming a layout.

## Reading the loader: the header layout, code-confirmed

The decisive step needed no fixture. `high_heap_loader_level_raw_decompress_orchestrator`
(**0x8003A318**; the census's recorded `loader_caller` 0x8003A4EC is a site
inside it) does this immediately after calling the decompressor:

```
jal  0x8001A1DC          ; level_raw_lzss_decompressor
lw   s4, 0(fp)           ; <-- the SUBTYPE MARKER, u32 at offset 0
slti v0, s4, 32          ; <-- the class split at 0x20
```

So both of the census's central assumptions are **confirmed in retail code**,
not inferred from data shape. The dispatch chain then compares 32, 34, 35, 36,
257, 258, 259, 260 — precisely the marker space the data census found.

**The texture-page path pins the header.** It stages a libgpu `RECT` from the
u16s at +4/+6 and then calls
`LoadImage(rect, base + 12 + round_even(u16@+8))`. Pixel data therefore begins
at **chunk + 12 + even(field@+8)** — which turns the previously *guessed*
"12-byte header + 768-byte palette" into a fact: **768 is simply the value of
the `+8` field** for that family. The loader then advances `rect.x` by
`rect.w` and re-uploads, i.e. a tiled VRAM upload loop bounded at the 768/192
VRAM region.

**Marker `0x20` turned out to be something better than a picture.** Its handler
reads u32s at +4/+8/+12, then takes the **u16 at +16** and decodes it as
RGB555 — `andi 0x1f` for R, `>>5 & 0x1f` for G, `>>10` for B, each scaled
5→8 bits by the standard `0x84218421` reciprocal-multiply — and stores the
three channels to gp-relative 29116/29120/29124 = **0x800771BC / 0x800771C0 /
0x800771C4**. Those are *exactly* the per-level **sky-colour cache** addresses
the committed starry-night mod patches. Given the exact size arithmetic
(16 + 320×256×2), offset +16 is where the image data begins, so the sky colour
appears to be sampled from the image's **first pixel** — the decode and the
destination globals are code-confirmed; "first pixel" is the single
inferential step and is flagged as such.

### Correction to my own claim, same day

Earlier in this pass I pinned marker `0x20` as a "320×256 RGB555 full-screen
image" corroborating the committed **loading-screen** format. The pixel
geometry stands — 320×256 16bpp, exact size match, bit 15 clear. **The role was
wrong.** The loader feeds this chunk's colour into the per-level sky-colour
cache, so `0x20` is the **sky/backdrop** resource. Loading screens live in
`GFX/*.RAW`, a different container. The corroboration I reached for was the
wrong canon; the right one was the backdrop/sky note sitting one shelf over.

## The complete marker space — and why arithmetic was never going to work

Reconstructing the loader's full dispatch closes the space. Beyond the
individually-handled markers, there are **three range-indexed pointer tables**:

| markers | disposition |
|---|---|
| `< 0x20` | texture/VRAM page — `LoadImage(rect, base + 12 + even(u16@+8))`, tiled upload |
| `0x20` | sky/backdrop — RGB555 at +16 → sky-colour cache |
| `0x21`–`0x26` | individual arms (see below) |
| `0x28`–`0x2F` | **pointer-registered**: `TABLE[marker] = chunk base` @ `0x8009C170 + marker*4` |
| `0x30`–`0x57` | **pointer-registered** @ `0x8009B4E8 + marker*4` (40 slots) |
| `0x58`–`0x5F` | **pointer-registered** @ `0x800A6450 + marker*4` |
| `0x101`–`0x104` | mesh definition / payload / collision planes / collision sector-source |

Two of the individual arms are worth recording. **`0x23` is a straight
1,792-byte memcpy from chunk+4 into the fixed RAM table `0x800949B8`** — which
is exactly *why* every `0x23` chunk measures 1,796 bytes, converting that
observed invariant into a mechanism. **`0x24`** uses a 16-byte header with data
at +16 and uploads through `level_texture_upload` (0x8003CC58).

All 74 previously-unclassified chunks now have a disposition: 17 sky/backdrop,
11 in the `0x26` arm, and **46 pointer-registered** (3 + 39 + 4 across the three
tables).

**This explains the earlier failure directly.** Those 46 chunks are *registered
by pointer and never interpreted by this loader* — it records where the chunk
sits and moves on. Their layout is decided by whatever consumer later reads
`TABLE[marker]`. No amount of size arithmetic on the bytes could have recovered
a format the loader never imposes.

### Second correction, same pass

Earlier in this pass I concluded that **all 74 unknown chunks are image
resources**, because their headers carry dimension-looking `u16`s. That is
wrong for the 46 pointer-registered ones — the loader treats them as opaque
blobs. The claim survives only for the `0x20` family. **Dimension-shaped
numbers in a header are not evidence of an image when the code never reads them
as one.** The earlier framing is kept in the artifact, marked superseded, so the
reasoning trail stays visible.

**Next step:** find the *consumers* that read `0x8009B4E8` / `0x8009C170` /
`0x800A6450`. Those, not the loader, define the 46 formats.

## The overlay ABI (region A)

The row's other half. The committed overlay map records 42 addresses inside
region A (base **0x800B39A0**) that resident code calls, at irregular offsets —
so the contract is **not a vector table**. Resident code contains **hardcoded
absolute `jal` instructions** into the swap buffer (e.g. `jal 0x800B39A4` at
0x8003D674/84/94/C4…), dispatched per scene.

Checking all 42 addresses against all 19 `LEVEL*.BIN` files settles the shape:
**each overlay implements only the entries its own scene needs** (1–5 each; 17
distinct entry-sets across 19 files; every overlay implements at least one).
The 42 recorded addresses are the **union across the campaign**, not a
per-overlay requirement. The word at base+0 is a header (LEVEL04/LEVEL1.BIN:
0x12); the first function begins at base+4.

**0x800B39A4 (base+4) is the common primary entry** — implemented by **13 of
19** overlays, which matches the committed map's record of **13 resident call
sites** for that address exactly. Two counts derived from unrelated evidence
agreeing is the corroboration that the model is right.

Two more independent checks land: **0x800B4084 is implemented by
`LEVEL08/LEVEL1.BIN`**, and committed C17 canon names 0x800B4084 the
movie-viewer *menu reader* — the ABI scan places that function in the right
overlay without being told; and the region base 0x800B39A0 matches the base I
derived independently during D18 from the Bug Bar overlay's counter-store
encoding.

**Method limit, stated plainly:** a function start is detected as
`addiu sp,sp,-N` or a bare `jr ra` stub, so leaf functions with other prologues
are missed. Per-overlay entry counts and the "27 of 42 implemented" union are
**lower bounds**. This constrains completeness, not the shape of the ABI.

**Modding consequence:** because the call sites are hardcoded absolute
addresses into a *swap buffer*, an overlay-region address has no fixed meaning
across scenes. A cave hooking region A must condition on the scene id
(0x80082504) and must preserve the entry addresses its scene's overlay
implements.

## Scope limits

- Marker `< 0x20` is mapped to "texture page" on the strength of the committed
  `confirmed_format` labels for LEVEL01. It holds loosely campaign-wide —
  274 of 296 are the canonical 33,548/17,164 bytes, but **22 are other sizes**.
  Treat the low-marker family as "VRAM-upload resource, size-varied", not as a
  uniform page.
- Marker semantics are structural. This pass says *what family a chunk is*, not
  what its contents mean; `0x22` strip internals and the `0x101` sub-mesh
  layout remain as they were.

## Gates

`tests/test_phase4_e16_chunk_census.py` — 14 tests: classifier compiles; all 46
"likely" chunks confirmed against the committed census; campaign family counts;
the two fixed-size invariants; the mesh pairing law plus its id-11 exception;
and that the 74 unknown markers are enumerated with their files rather than
silently bucketed; that the 74 are image resources with `0x20` pinned; and
that the over-fit is kept visible as refuted; the loader's marker/class-split
confirmation; the header+preamble pin; the sky-colour decode; and that the
loading-screen role correction stays visible; the full marker-space map with
its three pointer-table bases; and that the "all 74 are images" framing is
marked superseded rather than deleted. All pass.

## Related

[[MEM_-_LEVEL.RAW_chunk_model]] · [[EXP_2026-08-04_phase4_e02_collision_roundtrip]]
(chunk 32/0x103 proven independently) · [[EXP_2026-08-04_phase4_e08_object_census]]

## Update 2026-08-04 — the overlay-ABI lower bound, tightened

This experiment recorded its per-overlay entry lists and its "27 of 42" union as
**lower bounds**, because the detector accepted only `addiu sp,sp,-N` or a bare
`jr ra` as a function start, so a leaf function with any other prologue read as
"not implemented".

A structurally different detector removes that assumption entirely: in
contiguous code a function **start** is the instruction after the delay slot of a
`jr ra`. No prologue shape is assumed.

| detector | union of the 42 implemented somewhere |
|---|---|
| prologue matching (original) | 27 |
| return-derived (new) | 39 |
| both agree | 24 |
| **either** | **42 / 42** |

So **every one of the 42 committed region-A entry points is a function start in
at least one overlay** — the union was not merely under-counted, it was complete
all along and could not be shown.

Both detectors are kept, because they err in **opposite** directions: prologue
matching under-counts (misses unusual prologues), return scanning over-counts
(embedded data decoding as a false `jr ra` invents a start). Together they
bracket the truth rather than replacing one guess with another. Three entries —
`0x800b39b8`, `0x800b39c8`, `0x800b39dc` — are found **only** by prologue
matching, so the new detector does not subsume the old one.

The prologue detector reproduces **exactly 27**, which is the check that matters:
the old method was replicated faithfully before claiming to improve on it.

**Correction:** this note says 19 `LEVEL*.BIN`. There are **20** —
`LEVEL00/LEVEL.BIN` is a 4-byte stub (header word only, zero functions), so it
was invisible to a scan that counted implementing files.

**Residual:** 18 of the 42 are confirmed by only one of the two detectors, and
nothing here checks at runtime that a scene actually *calls* the entries its
overlay implements. Gate: `tests/test_phase4_e16_registered_chunks.py`.
Artifact: `analysis/phase4_e16_overlay_starts.json`.
