---
kind: memory
id: MEM_800A6450
aliases: [MEM_800A6450, 0x800a6450, 0x800A65B0, registered_chunk_table_0x58_0x5F]
address: 0x800A6450
name: registered_chunk_table_0x58_0x5F
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

# MEM_800A6450 - registered chunk pointer table (markers 0x58..0x5F)

## Purpose

Holds the RAM address of each decompressed LEVEL.RAW chunk whose subtype marker
is in `0x58..0x5F` (family B, indexed images).

## Addressing — note the neighbourhood

`slot(marker) = 0x800A6450 + marker*4`, so the **occupied window is
`0x800A65B0 .. 0x800A65CF`**.

That window is **adjacent to, not inside, any documented player field**. The
highest known field of [[MEM_800A6500_Player_state_800A6500]] is lives at
`0x800A65A0`, which ends 16 bytes below the table; no `memory_map.json` region
covers `0x800A65B0` either. So the earlier framing of this as an "overlap with
the player-state block" was **too strong** — it is proximity within the same
BSS neighbourhood, with no known field colliding.

What is genuinely unresolved is the player block's **extent**: it has never been
formally bounded, so "no known field collides" is not the same as "no field
collides". Only 4 chunks campaign-wide carry markers in this range (0x58,
0x5a ×2, 0x5c — all in LEVEL00) and the frontend is not gameplay, so the uses
are separated in time regardless. If a player-block field near `0x800A65B0` ever
misbehaves after a frontend visit, start here.

## Written by

`0x8003bc54` in the LEVEL.RAW loader; also `0x8003a3c0`, `0x8005db28`, and the
bulk zero at `0x8005f6a4`.

## Read by

`0x8003c5ec` inside [[FUNC_8003C388_vram_upload_wait]] — the site that reads the
`+10` depth flag.

## Lifetime — cleared per load

The loader's init zeroes this table on **every** load (`0x8003a3c0`), so its
registrations do not outlive the scene that made them. Its sibling
[[MEM_8009B4E8_registered_chunk_table_0x30_0x57]] is **not** cleared and does
leave dangling pointers behind — see
[[EXP_2026-08-04_phase4_e16_resource_lifetime]].

## Related

- [[SYS_registered_chunk_image_resources]]
- [[MEM_8009B4E8_registered_chunk_table_0x30_0x57]]

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

**This is the window the incidental reads actually hit.** Measured:
`0x80010BF8` 53 reads over 7 levels (LEVEL01 was a single read of `0x800A65C0`,
the marker-`0x5C` slot); `0x80010DA0` — the byte-identical sibling 424 bytes
later — 51 reads on LEVEL15 across 8 distinct addresses, i.e. **every word of
the 32-byte window**. All reads; not one write, which the idiom guarantees
structurally because the scan matches loads only.
