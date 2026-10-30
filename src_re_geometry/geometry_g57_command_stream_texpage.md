# G57 — fcn.80010000 command-stream batch format + per-face texture page (editor V1)

Status: **DECODED + live-GP0-validated (2026-06-24)**, isolated DuckStation, pristine
Disney-Pixar A Bug's Life (v1.0), LEVEL01. Drives the level-editor visual-fidelity item **V1**
(`ObsidianVault/Systems/LEVEL01 Editor Visual-Fidelity Plan.md`). Renderer consumers:
`level_editor/scene_importer.py::_extract_faces`, `scene3d.py::assemble`.

## Headline
Each `fcn.80010000` mesh payload's command stream is a sequence of **batches** `[ctrl:u16][count:u16]`
+ primitives. The `ctrl` word **is the GP0 texpage**, BUT **bit 15 (`0x8000`) means "draw this batch
with the CURRENT page" (inherit) — only a ctrl WITHOUT `0x8000` switches the page** (from bits 0-4).
So most meshes effectively use one page (their first non-`0x8000` ctrl); only **~12** LEVEL01 meshes
genuinely switch pages mid-stream. V1 tracks the page per batch (honouring the inherit flag) and
assigns it **per face**, so the genuinely-switching meshes get correct multi-page texturing.

> **Correction (do not repeat the trap):** an earlier pass read `ctrl & 0x1f` on EVERY batch incl.
> `0x8000` ones → "174/208 meshes multi-page" and assigned the floor's `0x8064`/`0x8264` batches to
> **page 4** → the floor rendered **blue** (page 4 is a blue palette). The **live game frame
> (`gpu.captureFrame`) shows the floor is brown dirt**, and *all* page-4 CLUTs are blue, proving those
> batches do NOT switch to page 4 — they inherit page 0 (dirt). Candidate A (the floor) is page 0
> throughout. The `0x8000`-inherit rule is the fix.

## Command-stream batch format (after the vertex block)
A payload is: `u32 count` · `count` vertices (stride 0x0c) · then the command stream:
```
repeat:
  u16 ctrl          # GP0 texpage word for this batch (see bit layout)
  u16 prim_count
  prim_count × {
    u16 v0,v1,v2,v3   # vertex byte-offsets (multiples of 0x0c, < count*0x0c)
    u16 uv0,uv1,uv2,uv3  # low byte = U, high byte = V (0..255, texture-page space)
  }                   # quad v0,v1,v2,v3 -> tris (v0,v1,v2)+(v0,v2,v3)
```
A word that doesn't validate as a batch header (its first primitives' vertex offsets aren't aligned
/ in range) is skipped (resync) — same robustness as before. The batch parse reproduces the old
face count on **207 / 208** meshes (1 mesh ±2 faces), so geometry is unchanged; only the page is now
per-face. (Candidate A @0x188cc: batches `[0x60,10][0x8064,36][0x260,1][0x8264,12]` = 59 prims =
118 faces ✓. With the `0x8000`-inherit rule the `0x8064`/`0x8264` batches inherit page 0, so the
floor is page 0 (dirt) throughout — matching the live brown-floor frame.)

## The `ctrl` word == GP0 texpage (E1) — bit layout
Confirmed by gp0Trace: the command-stream `ctrl` word equals the **GP0 texpage** the game sets for
that batch's primitives (it appears verbatim in the GP0 `0x3C`/`0x34` polygon command's texpage
field — e.g. command-stream `0x60` → GP0 word5 hi `0x0060`). Standard PS1 GP0(E1) layout:
- bits 0-3 = **texpage X base** (×64 in VRAM)   ← `& 0x0f`
- bit 4    = texpage Y base (×256)              ← so `ctrl & 0x1f` = the VRAM **page index**
- bits 5-6 = semi-transparency mode (→ editor V_T transparency)
- bits 7-8 = texture colour mode (0 = 4bpp here)
- bit 9    = dither (seen toggling between same-page batches: 0x60 vs 0x260)
- **bit 15 (`0x8000`) = INHERIT: draw this batch with the CURRENT page; do NOT switch.** A ctrl
  WITHOUT bit 15 sets the page from bits 0-4. (So decode: `if ctrl & 0x8000: page = current` else
  `current = ctrl & 0x1f; page = current`.) This is the load-bearing correction — reading `& 0x1f`
  on `0x8000` batches put the brown floor on the blue page 4.

`page_index → LEVEL.RAW chunk` via `LEVEL01_VRAM_PAGE_CHUNK` (VRAM-matched once): {0:0,1:1,2:2,3:3,
4:4,5:5,6:6,7:8,8:9,9:10,10:12,11:13}.

## Live GP0 validation (gp0Trace, `level01_end_of_stage.sav`, 1 frame = 1507 cmds)
Textured draws are GP0 `0x3C` (1202, gouraud-tex quad) + `0x34` (167, gouraud-tex tri); the texpage
is embedded in **word5 (hi 16)**, the CLUT in **word2 (hi 16)** — there are almost no separate
`0xE1` texpage commands. Page indices actually drawn: **0:361, 1:198, 2:98, 3:440, 4:292**, + a few
strays. The game does draw all of pages 0-4 — but those page-4 draws are **genuinely-blue geometry**
(sky / blue elements), NOT the floor: every page-4 CLUT (0x3a70-0x3a7f, VRAM row 233) decodes to a
blue palette, and the captured frame's floor is brown. So per-face is correct **with the `0x8000`-
inherit rule** (floor → page 0); reading `&0x1f` on `0x8000` batches wrongly painted the floor with
the blue page 4. `command_id` in a gp0Trace entry is the bare opcode (0x3c), not shifted.

## Per-page CLUT + VRAM ground truth (for the V1-secondary CLUT-accuracy pass)
gp0Trace gives each draw's CLUT word (word2 hi); CLUT VRAM = `((clut&0x3f)*16, (clut>>6)&0x1ff)`,
page VRAM = `((tp&0xf)*64, ((tp>>4)&1)*256)`. Dominant per ground page (4bpp):
| page | texpage | CLUT word | CLUT VRAM | page VRAM |
|---|---|---|---|---|
| 0 | 0x60 | 0x3ffc | (960,255) | (0,0) |
| 1 | 0x61 | 0x3f70 | (768,253) | (64,0) |
| 2 | 0x62 | 0x3ef4 | (832,251) | (128,0) |
| 3 | 0x63 | 0x3ab2 | (800,234) | (192,0) |
| 4 | 0x04 | 0x3a74 | (832,233) | (256,0) |
**Tested + reverted:** swapping `RIPPED_PAGES` chunks 0-4 to `gpu.decodeTexture` of these dominant
CLUTs rendered the floor **purple (worse)** — because page 4 is blue under *every* CLUT in row 233
(`dec_page4` mean (94,95,139)) and the dominant CLUT belongs to blue (sky) draws, not the floor.
Lesson: a page is sampled with **multiple CLUTs** per draw, the CLUT is **not** in the DAT command
stream (it comes from render-time), and the look is `texture × vertex-colour`. So one-CLUT-per-page is
fundamentally lossy. Pages 0-3's existing rips already decode to sensible dirt/stone (page 0 dominant
CLUT 0x3ffc → brown (132,106,80) == the existing rip). With the inherit rule the floor uses page 0
(correct), so CLUT accuracy is now a **minor** residual (the ~12 genuine multi-page meshes + any
non-floor page that's mis-rip'd). A full fix needs the per-draw CLUT source RE'd, not a per-page swap.

## What V1 changed (code)
- `_extract_faces` → `[ctrl][count]` batch parser with **`0x8000`-inherit** page tracking; returns
  per-face `face_pages`.
- `SceneMesh.face_chunks` (per-face LEVEL.RAW chunk); `import_meshes` maps `face_pages`→chunks;
  per-mesh `texture_chunk` = dominant chunk (summary only).
- `scene3d.assemble` → `face_layers_for(mesh)`: per-face atlas layer (was one page per mesh).
- Test: `test_scene_importer.test_per_face_texture_pages`.

## Open (V1-secondary, now MINOR)
With the inherit rule the floor + most meshes use pages whose existing rips are fine, so the dirt-soup
is gone. Residual: **decor texturing** (`decor_prop` ∉ `TEXTURED_CLASSES`) and **per-draw CLUT
accuracy** for the ~12 genuine multi-page meshes (needs the render-time CLUT source RE'd — a per-page
swap is proven lossy, see above). Validate via matched-vantage A/B (`render_capture.py` vs
`gpu.captureFrame`). See the Visual-Fidelity Plan V1.
