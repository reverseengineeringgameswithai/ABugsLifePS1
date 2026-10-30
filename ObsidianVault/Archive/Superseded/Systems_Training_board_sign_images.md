---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Training board sign images.md
aliases:
  - "Training board sign images"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Training board sign images.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Training_board_sign_images.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Training board sign images
type: system
confidence: PARTIAL — draw source CONFIRMED (live); disc byte offset UNRESOLVED (see blocker)
tags: [system, texture, image, npc, sign, training, level01, tutorial, atlas]
updated: 2026-07-04
---
# The tutorial ant's chalkboard "sign" is an IMAGE, not glyphs

> The instructor ant in the LEVEL01 training area raises/lowers a chalkboard
> signpost that cycles through pictures (a bug + "×6", "×1" berries, seeds,
> mushrooms, green gems, an **Exit** card). Question: are those built from
> HUD/font **glyphs**, or is each a texture **image**? **Answer: image.**
> RE: `src_re/training_board_sign.c`.

## Determination — IMAGE (per-level 4bpp texture atlas)
- The board face is **one `GP0(0x3c)` Gouraud-textured quad**, sampling a
  **64×64 tile** of a 4bpp VRAM texture atlas — this part is solid and re-confirmed
  fresh on 2026-07-04. It is **not** composed from the HUD digit/letter glyph
  tiles (that's the separate [[HUD letter glyphs and word swap]] sprite system).
- "Changing signs" = the quad's **UV window moves to a different tile** of the
  same atlas. The NPC raising/lowering the board is animation; the picture swap
  is a UV change.
- ⚠️ **REVISED — whether the "×N" count is baked into that same tile or stamped
  separately is now OPEN**, not settled. Live `gp0Trace` during a boot replay
  caught the tile's upload as a full-atlas LoadImage (frame 3707) followed by a
  smaller per-tile update (frame 3866) with a still-smaller **nested** sub-update
  inside it (frame 3866, 4×32 texels) — positioned like a separate digit stamp
  on a static silhouette. Not yet confirmed either way. Full detail:
  [[Blocker - Training board sign disc offset unresolved]].

## Draw source (live `gpu.pickObject` on the board)
| field | value |
|---|---|
| primitive | `GP0(0x3c)` textured quad, opaque |
| texture page | x=320, y=0, **mode 0 = 4bpp** (raw `0x0605`) |
| CLUT | x=784, y=229 (raw `0x3971`), 16 entries |
| UV tile | u 64–127, v 0–63 → 64×64 texels (the "×6 bug" tile) |
| atlas VRAM hash | `SHA256[:16] = 00f3cf71b4a28d30` (stable across 2 states) |

Reading VRAM page (320,0) back as 4bpp 256×256 shows the **whole atlas**: ~16
tutorial tiles laid out 4×4 (×N counts, seeds, mushrooms, green gems, "Exit").

## Which level is this? — Training (scene 17), NOT the anthill
⚠️ **Disc folder ≠ in-game level.** The board scene is **`current_scene_id = 17`** (live-read on
the board), which the operator identifies as **Training** — a *different* in-game level from the
**Anthill / Level 1** (`scene 1`). But the disc **packs several scenes' data in one folder**: the
Training board's atlas lives in the **`LEVEL01` disc folder's base `LEVEL.RAW`** (`LEVEL00/LEVEL.RAW`
does not contain it). So: the picture is Training's; the bytes sit in the LEVEL01 folder. The mod
studio therefore organizes by **in-game level** (Training / Anthill / …), each bound to its own
asset files — never by disc folder — so Training and the anthill stay separate in the UI.

## Disc provenance — UNRESOLVED (2026-07-04)
⚠️ An earlier pass of this note claimed decompressed offset `LEVEL01/LEVEL.RAW
@0x98650` (logical chunk 32). **That claim is RETRACTED** — it was a false-positive
from a too-short, background-dominated signature; rendering those bytes with the
known CLUT produces noise, not this tile. Exhaustively ruled out since: every
Region-A texture-page chunk (33548/17164 B decompressed, the documented
`+0x30c`-pixels format) across every `.RAW` file on disc — zero hits. `GFX/TRAINING.RAW`'s
two real chunks are the loading-screen "start" prompt and its 320×256 16bpp
backdrop, not this tile (despite that file genuinely loading during the Training
level-load window, confirmed via live CD-read tracing). Full dead-end log,
what live tracing DID reveal (the frame 3707/3866 upload events), and the
recommended next angles: **[[Blocker - Training board sign disc offset unresolved]]**.

## Extract (proven — still works regardless of the disc-offset blocker)
- **Live:** `gpu.decodeTexture {x:336,y:0,width:64,height:64,bpp:4,clut_x:784,clut_y:229}`
  → the 64×64 board tile PNG. Whole atlas: `x:320,width:256,height:256`, same CLUT.
  Tool: `tools/training_board_edit.py extract-tile|extract-atlas`.

## Replace — BLOCKED on the disc-offset question above
Once the real offset is found: decode the container → overwrite the tile's 4bpp
pixels (re-indexed to the CLUT) → recompress (mind the sector budget — see the
blocker note; chunk-scale recompression can grow past a fixed-LBA slot) → rebuild
→ cold-boot → verify with `gpu.frameSnapshot`. This fork has **no `gpu.writeVramRect`**,
so there's no pure live VRAM poke — it must go through a disc edit.

## Related
[[HUD letter glyphs and word swap]] (contrast: glyphs) · [[Backdrop and sky layer]]
(other LEVEL.RAW image chunks) · [[Dot guide NPC]] (other LEVEL01 NPC) ·
[[Blocker - Training board sign disc offset unresolved]] · [[Consolidated mod build manifest]]
(Mod Studio UX) · `src_re/training_board_sign.c` · `tools/training_board_edit.py`
