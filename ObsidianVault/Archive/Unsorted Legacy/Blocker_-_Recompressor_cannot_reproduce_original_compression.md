---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Recompressor cannot reproduce original compression.md
aliases:
  - "Blocker - Recompressor cannot reproduce original compression"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Recompressor cannot reproduce original compression.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Recompressor cannot reproduce original compression
type: blocker
id: B14
severity: LOW
category: compression / build-reproduction
confidence: CONFIRMED
tags: [blocker, low, compression, codec, levelraw]
updated: 2026-06-22
---

# 🟡 B14 — The LEVEL.RAW recompressor re-encodes, but does not reproduce the original compression

> The "codec SOLVED" headline conceals two real limits: the **decoder is byte-exact only against a single (untracked) chunk0 oracle**, and the **recompressor is literal-only** — it produces a decode-compatible but *larger, differently-encoded* stream that has **never been booted on console**. Fine for live/save-state edits; a genuine risk for permanent disc edits and any byte-exact rebuild.

> [!check] Update (2026-06-18, live API) — **substantially CLEARED.** (1) **Recompressor IS game-accepted:** the G32 seed-disc (literal-recompressed chunk 31, spliced into LEVEL.RAW, rebuilt) was **operator-booted and the seed moved** — the game's own decompressor read the re-encoded bytes off disc → the "never booted on console" concern is refuted. (2) **Decoder validated beyond chunk0:** live chunk-35 decompression (`0x8012c1d0`) matches the offline decoder **byte-exact except one localized block `[9876,11210]`** — and because the data is correct *both before and after* that block, it is **not** a decode cascade (an LZ error desyncs everything downstream); the block is the game's runtime writes to the render buffer. So the decoder is correct on chunk 35 + the chunk0 byte-exact oracle. **Residual:** byte-exact reproduction of *original* bytes still needs a PROPACK-equivalent encoder (preservation/byte-exact-rebuild only — modding works); a full 69-chunk load-time capture would fully close decoder validation; size-growing edits past a sector boundary still need LBA-shift handling. **Severity → Low.**

> [!check] **Decoder validation CLOSED across all 69 chunks (2026-06-18).** Drove the level load from the **pre-load state `SCUS-94288_2.sav`** with an `execTrace.addWatch` on the decompressor `0x8001a1dc` (capturing `a0`=compressed-src). The live per-chunk loop fired **69 calls whose `a0` source pointers match my offline parser's chunk-start offsets exactly — chunk indices 0–68, complete** (`a0 = 0x80115aac + cumulative(0xe+word1)`; the lone 2 extra hits are a different-phase leftover, not LEVEL.RAW chunk starts). Independently, the **offline decoder decodes all 69 chunks to their exact declared `word0` decompressed size** (69/69 length-exact). Combined with the prior **byte-exact** decodes on chunk0 (oracle) + chunk35 (live), the decoder is now validated end-to-end: **container segmentation live-confirmed for every chunk + length-exact decode for every chunk + byte-exact on samples**. Retires **A5** ("decoder validated on only 2 chunks"). Residual is purely the *encoder* side (byte-exact reproduction of original PROPACK bytes), which only matters for preservation rebuilds, not modding.

> [!check] **Step-10 closure (2026-06-24) — the two named residuals settled.** (1) **LBA-shift handling for
> size-growing edits = DONE:** a LARGE chunk recompress (chunk 32: +58 KB) rebuilds via
> `tools/build_autolayout_disc.py` (mkpsxiso `abl_autolayout.xml`) and **boots LEVEL01 with the game reading
> the edit** (runtime collision table reflects it). (2) **The "size-neutral minimal-patch / broken provenance
> tracker":** the provenance tracker is now **fixed** (`decode_level_raw` `prov` aligns 1:1), but size-neutral
> patching is **inherently unsafe for this LZ** — a literal byte can be a match SOURCE so a compressed-byte
> patch propagates, and structured data is mostly match-output → **recompress is required** (balloon handled
> by auto-layout). Remaining residual is unchanged + optional: a PROPACK-equivalent **match-emitting encoder**
> (preservation / no-balloon / `cd.overlay`-live only — modding is unaffected). Codec guard:
> `tools/regress_level_raw_codec.py`. See [[LEVEL01 Level-Edit Punchlist#Cross-cutting blockers (affect several elements)|CC2/CC3]].

> [!check] **Match-emitting encoder DELIVERED (2026-07-02, HRE-009).** `tools/lz_encode_level_raw.py` is a
> **real back-reference LZ encoder** for the codec (greedy hash-chain, window 4096, len 2–263, litrun
> escapes; bit-register mechanics empirically mapped incl. the MAIN-flag sentinel quirk; round-trip asserted
> on every call). **chunk-0 oracle: 24,397 B vs 24,346 B original = 1.002×** (the literal-run tool produced
> 34,089 B = 1.4×); the chunk-29 backdrop even re-encodes SMALLER than the original (6,915 vs 6,977 B) —
> enabling size-neutral in-place splices (pad to original file size, no LBA shift, no auto-layout needed).
> Cold-boot proven: the sunset-backdrop LEVEL01 disc ([[Backdrop and sky layer]]). Remaining residual is
> byte-IDENTICAL reproduction of the original PROPACK output (preservation-only; sizes are now competitive).

**Severity:** ~~Medium~~ → **Low** (post-validation) · **Impact:** Medium · **Likelihood:** Low · **Confidence:** CONFIRMED · **Difficulty:** Medium

## Audit reconciliation (2026-06-22)
**True status: PARTIALLY ADDRESSED — and the TITLED claim ("cannot reproduce original compression") is TRULY UNRESOLVED.** Severity stays **Low** (modding-scoped), but the note conflates two distinct things; separating them:
- **DECODER — verified (ran the tool):** `tools/decode_level_raw.py` round-trips **byte-exact** (chunk0: 24,346 → 33,548 B, matches the live oracle). This half is solid.
- **ENCODER — original-byte reproduction NOT achieved (ran the tool):** `tools/recompress_level_raw.py` produces a **valid-but-different, LARGER** stream — chunk0 re-encodes to **34,089 B vs the original 24,346 B** (~1.4×). `recompressed != original`. It is a **literal-run encoder, not a match-finder**, so "reproduce original compression" is **not** done.
- The note's "game-accepted / booted (G32 seed disc)" result is **true and useful for MODDING** (the game's own decompressor reads the re-encoded bytes), but it is **not** original-byte reproduction — the note conflates the two.
- **Residuals:** a **PROPACK-2.29-equivalent match-finding encoder** is still needed for byte-exact rebuild; and the **~1.4× size growth reintroduces [[Blocker - Byte-exact disc reproduction is unproven|B4]]'s untested LBA-shift problem** for any real size-growing disc edit.

## What is known (evidence)
- `tools/recompress_level_raw.py` implements a **literal-run encoder only** (no real LZ match-finding), "~1.02× size"; it self-checks by round-trip against *its own* decoder (`decode(encode(x))==x`), **not** against the game and **never booted** ([[Finding - LEVEL.RAW is compressed]] caveats; `docs/GEOMETRY_RE_PLAN.md`).
- `tools/decode_level_raw.py` is byte-exact only vs the **chunk0** live oracle (`tools/raw_chunk0_{compressed,decompressed}.bin`, **untracked**). Chunks 1–68 are validated solely by decode→encode→decode self-consistency, which can be self-consistent yet wrong on code paths chunk0 never exercised. The hard late bugs (long-length terminator; the byte0 6-vs-8 flag-bit init; a bit-boundary guard edge that stalled G31b) signal fragility.
- The original packer is **Rob Northen PROPACK 2.29** ([[Blocker - Original toolchain ground-truth is unmined|B13]]) — reproducing original bytes would need a PROPACK-equivalent encoder.

## Why it matters
- Gates permanent disc edits of chunks 31/32/35. A silently-wrong decode on an untested chunk, an oversized literal-only chunk that breaks LBA layout, or a game that rejects the re-encoded stream would each break the "permanent patch" path despite "codec COMPLETE."

## Dependencies
- **Feeds:** [[Blocker - Byte-exact disc reproduction is unproven|B4]]. **Depends on:** [[Blocker - Original toolchain ground-truth is unmined|B13]] (PROPACK lineage) · [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified|B9]] (per-chunk validation). **Related assumptions:** A4, A5.

## Research opportunity (direction only)
- Capturing live decompressed ground-truth for several **non-chunk0** chunks (incl. a texture and a high subtype) and diffing the decoder would extend the byte-exact guarantee; booting one rebuilt disc with a recompressed chunk would prove acceptance + size headroom; a real-match (PROPACK-equivalent) encoder is the fallback if headroom is insufficient. (Direction only.)

## Evidence & sources
- vault: [[Finding - LEVEL.RAW is compressed]] · [[MEM - LEVEL.RAW chunk model]] · [[FUNC_8001A1DC]]
- corpus: `tools/decode_level_raw.py`, `tools/recompress_level_raw.py`, `tools/raw_chunk0_*.bin`, `src_re_geometry/geometry_g24_level_raw_decompressor.md` (§G31)
- See also: [[Blockers]] · [[Risk Matrix]]
