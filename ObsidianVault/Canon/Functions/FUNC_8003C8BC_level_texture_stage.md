---
kind: function
id: FUNC_8003C8BC
aliases:
- FUNC_8003C8BC
- '0x8003c8bc'
- level_texture_stage
address: '0x8003c8bc'
name: level_texture_stage
status: characterized
confidence: confirmed
source_state: original_game
tier: observed
calls:
- level_texture_upload
evidence:
- EXP_2026-08-04_phase4_e16_registered_chunk_consumers
- analysis/phase4_e16_registered_chunks.json
- analysis/phase4_e16_table_read_watch.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- tools/phase4_e16_registered_chunks.py
- tools/mips_ea_window.c
patch_policy: safe_to_read
---

# FUNC_8003C8BC - level_texture_stage

## Purpose

Uploads one **deferred frontend image resource** to VRAM, selected by its
LEVEL.RAW chunk **subtype marker**. This is the consumer for the pointer table
[[MEM_8009B4E8_registered_chunk_table_0x30_0x57]] (markers 0x30..0x57).

The name is inherited from `re_symbols.sym`; what is established here is the
behaviour below, not the name.

## Mechanism

At `0x8003c920` it fetches the registered chunk pointer for a marker:

```
sll   $v0, $a0, 2
lui   $at, 0x800a
addu  $at, $at, $v0
lw    $s1, -19032($at)      # tbl[marker] -- EA = 0x8009B5A8 + marker*4
lhu   $s2, 4($s1)           # width
lhu   $s3, 6($s1)           # height
lhu   $s7, 8($s1)           # palette_bytes
addiu $s0, $s1, 12          # palette, then indexed pixels
jal   0x8003cc58            # level_texture_upload
```

So the resource layout is not guessed from file sizes — it is read here. See
[[SYS_registered_chunk_image_resources]] for the full format and the size law
that all 46 retail chunks satisfy exactly.

`addiu $a3, $s1, 780` further on is `+12 + 768`, i.e. the pixel data immediately
after the 768-byte palette — corroborating the header split from a second site
in the same function.

## The rest of the upload (2026-08-04)

**The depth flag IS read here** — at `0x8003cb54`, 0x298 bytes past the table
fetch, which is why a short window around the fetch missed it:

```
lh   $v1, 10($s1)          # the +10 depth flag
bne  $v1, $zero, .Lis8bpp
...
  flag == 0:  w = (w + 3) >> 2     # 4 pixels per 16-bit VRAM word -> 4bpp
  flag == 1:  w = w >> 1           # 2 pixels per 16-bit VRAM word -> 8bpp
```

It rewrites the VRAM **rect width** by pixel depth. The rect itself is built at
`0x80089848` (`x @+0`, `y @+2`, `w @+4` = `0x8008984C`, `h @+6` = `0x8008984E`)
and passed to `LoadImage` (`0x800628c0`) as `a0`.

The pixel source is `a1 = chunk + 12 + (palette_bytes & ~1)` — the same
`12 + round_down_even(u16@+8)` rule already pinned for the texture-page path,
reached here independently.

**Palette pipeline.** The 768-byte palette is copied to a stack buffer at
`sp+32` and walked **three bytes at a time** — code-level proof that it is
256 × RGB888 — scaling each component to 75% with `(v*96)>>7`. Entries matching
`R<5 && G>=250 && B<5` are left **unscaled**: that is the pure-green
transparency key. In marker `0x30` exactly one palette entry matches (index 0 =
`(0,255,0)`), it is what all four image corners use, and it is 50% of the
image — scaling it would turn 255 into 191 and break the key.

`level_texture_upload` is called **twice**: once with the chunk's own palette
(`0x8003c944`) and once with the 75%-scaled stack copy (`0x8003cae0`), so a
normal and a dimmed CLUT are both staged.

## Scope limits

- That the dimmed CLUT is a menu "unselected" variant is a **reading**, not
  established.
- Full control flow is not decompiled; the fetch, header decode, palette
  pipeline, rect construction and upload above are what has been read.
- **Corrected 2026-08-04:** I first named `andi $v0,$v0,3` at `0x8003c954` as
  the 4bpp/8bpp lead. It is not — it is `or $v0,$s0,$a2` then `andi 3`, an
  **alignment** test selecting between a word copy and the `lwl`/`lwr` path.

## Related

- [[FUNC_8003C388_vram_upload_wait]] — the sibling consumer for the other two tables
- [[FUNC_8003CC1C_level_texture_stage_reset]]
- [[FUNC_8003A318_high-heap_loader_+_LEVEL.RAW_decompress_orchestrator]] — the registrar
- [[SYS_registered_chunk_image_resources]]
