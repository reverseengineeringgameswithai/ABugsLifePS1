---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - LEVEL.RAW is compressed.md
aliases:
  - "Finding - LEVEL.RAW is compressed"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - LEVEL.RAW is compressed.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_LEVEL.RAW_is_compressed.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - LEVEL.RAW is compressed
type: finding
confidence: CONFIRMED
gstep: G23/G24
tags: [finding, levelraw, compression, gate]
---

# Finding — LEVEL.RAW is LZSS-compressed (the "LZ codec gate")

> Both the terrain-mesh layer (chunk 35; renders *occluded* — the **visible** floor is LEVEL.DAT via [[FUNC_80010000]], f13) and the collision planes (chunk 32) live inside a custom-compressed LEVEL.RAW. This **was** the single biggest blocker to *permanent disc* terrain/collision edits and to the [[Seed planting system|seed level-editor]] (seed placements are in chunk 32). **✅ SOLVED 2026-06-17 — a byte-exact decompressor + working recompressor now exist (see below).**

**Confidence:** CONFIRMED (structure) / PARTIAL (exact code tables) · **Established:** G23 / G24

## Summary
- LEVEL.RAW is a custom **LZSS/LZ77** stream: big-endian header words (`word0`=decompressed size, `word1`=compressed size, `0xe`-byte header), MSB-first bit reader, literal/match flags, variable-length length codes, 16-bit distance, terminator at a zero long-byte.
- Decompressed by [[FUNC_8001A1DC]] (single caller `0x8003a4e4`), driven per-chunk by [[FUNC_8003A318]].
- The exact length/distance code tables are **not** byte-exact yet → no offline encode/decode tool exists.

## Evidence
Entropy analysis ( `[0xa8000,0xa8400)` = 213 distinct bytes/1024) + full disasm of `fcn.8001a1dc` (~456 instrs, no GTE, no jal). G25 confirmed the per-chunk loop.

## Related functions
[[FUNC_8001A1DC]] · [[FUNC_8003A318]] · [[FUNC_80046330]]

## Related memory structures
[[MEM - LEVEL.RAW chunk model]]

## Related experiments
n/a (static + live trace)

## Related fixtures / save states
`SCUS-94288_2.sav` (pre-load)

## DuckStation APIs used
[[API - accessLog]] · [[API - execTrace]] · [[API - transferLog]]

## ✅✅ END-TO-END WRITE PATH PROVEN IN-GAME (2026-06-17, G32)
The full editor write path is **operator-confirmed in-game**, not just round-trip-validated:
1. Decompressed `LEVEL.RAW` chunk **31** (the seed chunk; decomp off `0x965d4`, word0 1796).
2. Located the LEVEL01 **start-seed** record at chunk-local `0x2dc` = file `(6184,111,17525)`.
3. Edited X `6184 → 3000` (runtime `197888 → 96000`), recompressed **only chunk 31**, spliced into LEVEL.RAW.
4. Rebuilt the disc → `REBUILD/ABL_SEED_MOVE_TEST.bin/.cue`. Embedded-verify: LBA **3069 unchanged**,
   size 748990 (grew 1242 B but stayed within the same 366 sectors → **no LBA shift**; next file still 3435).
5. **Operator booted the rebuilt disc → the seed visibly spawned at the new (far-left) location.** The
   game's *own* decompressor read our edited bytes off disc. Verify helper: `tools/verify_seed_move_ingame.py`.
- Full decompressed dump now cached on disk: `tools/LEVEL_RAW_decompressed/LEVEL.RAW.decompressed`
  (1,269,320 B) + `chunk_index.json` (per-chunk comp/decomp offsets) — for direct grep/inspection.
- This retires the [[Seed planting system|GUI seed editor]] codec risk entirely: decompress → edit table
  → recompress one chunk → rebuild is a working, layout-safe pipeline.

## ✅ SOLVED (2026-06-17, G31) — the codec is COMPLETE (no longer a gate)
- **Decompressor BYTE-EXACT** (`tools/decode_level_raw.py`): chunk0 33548/33548 + full LEVEL.RAW (69
  chunks → 1,269,304 B). **Recompressor WORKING** (`tools/recompress_level_raw.py`, literal-run): full
  chunk0 + edited chunks round-trip (decode(encode(x))==x), ~1.02× size.
- Key fixes: the long-length **terminator** (byte==0 → read 1 more bit; only byte==0 AND next-bit==0
  ends) and the bit-reader **init** (byte0 yields 6 bits, reloads 8 → `first_bits=6`).
- **Unblocks**: disc edits of chunk 32 (collision/**seeds**) / chunk 35 (terrain), and the
  [[Seed planting system|GUI seed level-editor]] (decompress → edit table → recompress edited chunk →
  rebuild). Full record: `src_re_geometry/geometry_g24_level_raw_decompressor.md` §G31a–d.

## G31 progress (2026-06-17) — ground truth captured, decoder + recompressor DONE
- **Decisive §7 step DONE:** clean (compressed → decompressed) ground-truth pair captured via execute BP at
  `0x8001a1dc` (a0=compressed `0x80115aac`, a1=decompressed `0x800b5790`); chunk0 = `word0` 0x830c (33548) ←
  `word1` 0x5f0c (24332). **Compressed chunk0 == `REBUILD/files/LEVEL01/LEVEL.RAW` @ file offset 0x0** → the
  editor can operate on the file. Oracle saved: `tools/raw_chunk0_compressed.bin` / `raw_chunk0_decompressed.bin`.
- Building the Python decoder now (validate byte-exact vs the oracle). Recompressor can be literal-only.
- Motivation: unlocks the [[Seed planting system|GUI seed editor]] (move/add seeds) **and** disc edits of
  chunk 32/35. Full runbook: `src_re_geometry/geometry_g24_level_raw_decompressor.md` §G31.

## Next steps
**Status (reconciled 2026-06-18):** the codec is identified as **RNC PROPACK 2.29** ([[Finding - Build toolchain and PROPACK provenance]]) and the **decoder is byte-exact** (also decodes `GFX/*.RAW`). The remaining gate is **re-injection**: the recompressor is literal-only and **unproven on console** → prove via the Phase 3 disc boot-test ([[Blocker - Recompressor cannot reproduce original compression|B14]]). A byte-exact *rebuild* additionally needs a PROPACK-equivalent encoder. Until the boot-test, treat permanent disc edits as plausible-but-unverified; RAM/save-state edits work today.

## Source
`src_re_geometry/geometry_g23_level_raw_floor_format.md`, `geometry_g24_level_raw_decompressor.md`, `geometry_g25_level_raw_post_decompress_trace.md`
