---
kind: memory
id: MEM_8009C170
aliases: [MEM_8009C170, 0x8009c170, 0x8009C210, registered_chunk_table_0x28_0x2F]
address: 0x8009C170
name: registered_chunk_table_0x28_0x2F
status: runtime_confirmed
confidence: confirmed
source_state: original_game
system: [SYS_registered_chunk_image_resources]
read_by: [FUNC_8003C388_vram_upload_wait]
written_by: [FUNC_8003A318_high-heap_loader_+_LEVEL.RAW_decompress_orchestrator]
related_structs: []
evidence: [EXP_2026-08-04_phase4_e16_registered_chunk_consumers, EXP_2026-08-04_phase4_e16_anypercent_campaign]
src_paths: [analysis/phase4_e16_registered_chunks.json, analysis/phase4_e16_table_read_watch.json, analysis/phase4_e16_address_materialization.json, analysis/phase4_e16_campaign_verdict.json, analysis/hoisted_load_idiom_scan.json]
patch_policy: safe_to_read
---

# MEM_8009C170 - registered chunk pointer table (markers 0x28..0x2F)

## Purpose

Holds the RAM address of each decompressed LEVEL.RAW chunk whose subtype marker
is in `0x28..0x2F` — the **family A** full-screen 16bpp images, including the
320x256 title screen.

## Addressing

`slot(marker) = 0x8009C170 + marker*4` (RAW marker; see
[[MEM_8009B4E8_registered_chunk_table_0x30_0x57]] for why this trips people up).

**Occupied window: `0x8009C210 .. 0x8009C22F`** (8 slots).

## Written by

`0x8003b9cc` in the LEVEL.RAW loader; also `0x8003a3bc` and the bulk zero at
`0x8005f6a4`.

## Read by

`0x8003c3c0` inside [[FUNC_8003C388_vram_upload_wait]], which reads **32-bit**
width/height and calls `LoadImage` with the payload at `+16`.

## Lifetime — cleared per load

The loader's init zeroes this table on **every** load (`0x8003a3bc`), so its
registrations do not outlive the scene that made them. Its sibling
[[MEM_8009B4E8_registered_chunk_table_0x30_0x57]] is **not** cleared and does
leave dangling pointers behind — see
[[EXP_2026-08-04_phase4_e16_resource_lifetime]].

## Related

- [[SYS_registered_chunk_image_resources]]
- [[MEM_800A6450_registered_chunk_table_0x58_0x5F]]

## Resolved resident materialisation sites (not a complete access census)

**Correction history.** This section was formerly headed "Reader/writer set — now
PROVEN COMPLETE" and claimed nothing outside the recorded set could deliberately
form a pointer here. That was wrong: the scanner only recognizes selected linear
`lui` encodings.

Scanning the whole resident text finds **5 locally tracked `lui`-form materialisation
sites** reaching the three tables, and every reported hit is listed here.

Pointer reloads, arguments, derived aliases, CFG joins, and unmodelled register
definitions are not closed by this scan, so the actual consumer set remains open.
`tools/const_address_materialization.c`; `analysis/phase4_e16_address_materialization.json`.

Corroborated, not established, by a 16-level any% campaign: 1,930 `readwrite`
events across every level, no unexplained PC.

## ⚠️ One INCIDENTAL reader, deliberately NOT listed in `read_by`

The campaign caught the geometry emitter reading this region. It is a load the
compiler scheduled **above its own bounds check**:

```
sltu $a3, $t9, $s5     ; range test COMPUTED
add  $t9, $t9, $s1     ; base is a REGISTER, not a lui constant
lhu  $t9, 0($t9)       ; the read happens REGARDLESS
beq  $a3, $zero, ...   ; test acted on, one instruction too late
```

The loaded value is **discarded** on exactly the path where the address is out of
range, so this is not a consumer and listing it under `read_by` would misrepresent
it. There are **22 such sites** project-wide (`tools/hoisted_load_idiom_scan.c`),
all in the geometry emitters, all read-only.

⚠️ **They will appear in any `accessLog` watch over this region and look exactly
like an unenumerated consumer.** Match watch events against the logged PC
(= load PC **+4**) before concluding you have found a new reader.

Observed here in the campaign: none — the incidental reads landed in the
`0x58..0x5F` window, not this one.
