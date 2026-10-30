---
kind: function
id: FUNC_8003C388
aliases:
- FUNC_8003C388
- '0x8003c388'
- vram_upload_wait
address: '0x8003c388'
name: vram_upload_wait
status: characterized
confidence: confirmed
source_state: original_game
tier: observed
calls:
- EnterCriticalSection
- LoadImage
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

# FUNC_8003C388 - vram_upload_wait

## Purpose

Uploads deferred frontend image resources to VRAM via `LoadImage`. It contains
**two** distinct consumer sites, one for each of the other two registered-chunk
pointer tables, and the two read **different header layouts** — which is what
splits the registered resources into two format families.

The name is inherited from `re_symbols.sym`; the behaviour below is what has
been established.

## The two consumer sites

**`0x8003c3c0` — table [[MEM_8009C170_registered_chunk_table_0x28_0x2F]] (markers 0x28..0x2F)**

```
sll   $s0, $s0, 2
lui   $at, 0x800a
addu  $at, $at, $s0
lw    $v0, -15856($at)      # tbl[marker] -- EA = 0x8009C210 + marker*4
...
lw    $v0, 4($s4)           # width   -- 32-BIT
lw    $v1, 8($s4)           # height  -- 32-BIT
...
addiu $a1, $s4, 16          # pixel data at +16
jal   0x800628c0            # LoadImage
```

32-bit fields and a +16 payload: this is **family A**, 16bpp direct colour.
`size == 16 + w*h*2` holds exactly on all 3 retail chunks (the 320x256 title
screen among them).

**`0x8003c5ec` — table [[MEM_800A6450_registered_chunk_table_0x58_0x5F]] (markers 0x58..0x5F)**

```
lui   $at, 0x800a
addu  $at, $at, $s0
lw    $v0, 26032($at)       # tbl[marker] -- EA = 0x800A65B0 + marker*4
lhu   $s1, 4($s4)           # width
lhu   $s0, 6($s4)           # height
lhu   $s6, 8($s4)           # palette_bytes
lhu   $s3, 10($s4)          # depth flag (8bpp when 1, 4bpp when 0)
addiu $a0, $zero, 768       # the palette size it expects
addiu $v0, $s4, 12          # palette, then indexed pixels
```

16-bit fields and a +12 payload: this is **family B**, shared with
[[FUNC_8003C8BC_level_texture_stage]].

## Why this matters beyond the format

Both sites index the table (`lui`+`addu`+`lw`), so their displacements are *not*
the table base. A static sweep that matches the base displacement across the
resident EXE and all 30 `.BIN` files finds the three registration **stores** and
**zero reads** — a clean, confident, and wrong negative. These readers were
found by a live `readwrite` watch instead. See
[[SYS_registered_chunk_image_resources]].

## Scope limits

- The function is 1,332 bytes and is not decompiled; only the two consumer
  sequences above and their `LoadImage` calls are established.
- The name `vram_upload_wait` predates this work and the "wait" aspect is not
  something this investigation verified.

## Related

- [[FUNC_8003C8BC_level_texture_stage]]
- [[FUNC_8003A318_high-heap_loader_+_LEVEL.RAW_decompress_orchestrator]]
- [[SYS_registered_chunk_image_resources]]
