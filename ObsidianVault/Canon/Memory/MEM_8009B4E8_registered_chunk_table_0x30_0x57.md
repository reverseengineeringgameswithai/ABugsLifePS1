---
kind: memory
id: MEM_8009B4E8
aliases: [MEM_8009B4E8, 0x8009b4e8, 0x8009B5A8, registered_chunk_table_0x30_0x57]
address: 0x8009B4E8
name: registered_chunk_table_0x30_0x57
status: runtime_confirmed
confidence: confirmed
source_state: original_game
system: [SYS_registered_chunk_image_resources]
read_by: [FUNC_8003C8BC_level_texture_stage]
written_by: [FUNC_8003A318_high-heap_loader_+_LEVEL.RAW_decompress_orchestrator]
related_structs: []
evidence: [EXP_2026-08-04_phase4_e16_registered_chunk_consumers, EXP_2026-08-04_phase4_e16_anypercent_campaign]
src_paths: [analysis/phase4_e16_registered_chunks.json, analysis/phase4_e16_table_read_watch.json, analysis/phase4_e16_address_materialization.json, analysis/phase4_e16_campaign_verdict.json, analysis/hoisted_load_idiom_scan.json]
patch_policy: safe_to_read
---

# MEM_8009B4E8 - registered chunk pointer table (markers 0x30..0x57)

## Purpose

Holds the RAM address of each decompressed LEVEL.RAW chunk whose subtype marker
is in `0x30..0x57`, so the frontend can upload that image to VRAM later.

## Addressing — read this before watching it

`0x8009B4E8` is the **displacement base**, not the first occupied slot. The
registration store is

```
lui  $at, 0x800a
addu $at, $at, ($s4 << 2)     # $s4 = the RAW marker
sw   $s3, -19224($at)         # 0x8003bf48
```

so `slot(marker) = 0x8009B4E8 + marker*4`. The `addiu $v0,$s4,-48` just before
it is only the `sltiu` bounds check, **not** a rebasing of the index.

**Occupied window: `0x8009B5A8 .. 0x8009B647`** (40 slots).

Watching `0x8009B4E8..+160` watches 160 bytes entirely *below* the table — the
loader's own stores never fire there, and the window instead reports an
unrelated global that is read as an s16 triple. That mistake cost a full live
run on 2026-08-04.

## Written by

`0x8003bf48` in the LEVEL.RAW loader (registration), plus the startup bulk-zero
store at `0x8005F6A0` that clears all three tables. DuckStation access logs report
that store as `0x8005F6A4` because their event PC is the following instruction.

## Read by

`0x8003c920` inside [[FUNC_8003C8BC_level_texture_stage]] — 24 reads observed in
one boot→frontend→level-select run.

## Lifetime - startup-cleared, not per-load-cleared

Unlike its two siblings, this table is **not reset by the loader's init on every
load** (`0x8003A3BC`, `0x8003A3C0`); those stores cover only the two eight-slot
sibling tables. It is zeroed once by the startup loop at `0x8005F690..0x8005F6B0`,
whose `[0x80082200, 0x800B39A0)` range contains the full occupied window.

**Correction history.** An earlier revision said the table was "NEVER cleared"
and that "nothing zeroes this table." That was wrong and contradicted the startup
bulk-zero already named above. The surviving finding is narrower: after startup,
no per-load reset clears this table. Measured across boot -> frontend -> Clover
Forest, 36 frontend
registrations survive into gameplay, and **0 of 36 still read back their own
marker** — the high-heap memory they point at has been reused. They are
genuinely dangling, and nothing on the upload path validates them.

See [[EXP_2026-08-04_phase4_e16_resource_lifetime]].

## Related

- [[SYS_registered_chunk_image_resources]]
- [[MEM_8009C170_registered_chunk_table_0x28_0x2F]]
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
