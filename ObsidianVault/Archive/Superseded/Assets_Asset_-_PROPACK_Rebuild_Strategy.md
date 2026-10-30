---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - PROPACK Rebuild Strategy.md
aliases:
  - "Asset - PROPACK Rebuild Strategy"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - PROPACK Rebuild Strategy.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_PROPACK_Rebuild_Strategy.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - PROPACK Rebuild Strategy
type: asset
updated: 2026-06-20
tags: [asset, propack, codec, rebuild, milestone4, b14, gap-0024]
---

# Asset — PROPACK / compressed-rebuild strategy (decision)

> M4 decision for [[Gap Audit|GAP-0024]] / [[Blocker - Recompressor cannot reproduce original compression|B14]]: **no PROPACK-equivalent encoder is available; the safe method is literal recompression + a size-budget rule** tied to rebuild/boot validation. This is sufficient for modding-grade edits; byte-exact *original* reproduction of compressed assets is not pursued unless a payoff appears.

## Codec facts
- **Identity:** Rob Northen **PROPACK 2.29** (on-disc `ERRORS.ERR`; [[Finding - Build toolchain and PROPACK provenance]]). Not bespoke LZSS.
- **Decoder: BYTE-EXACT on all 69 chunks.** `tools/decode_level_raw.py` (port of [[FUNC_8001A1DC]]); validated by `tests/test_level_raw_codec.py` (passes) and the full-file decode (69 chunks → 1,269,304 B). Chunk format `[word0 decomp][word1 comp][6-B hdr][stream]`.
- **Chunk0 oracle (tracked):** `tools/raw_chunk0_compressed.bin` (24,346 B incl. header) ↔ `tools/raw_chunk0_decompressed.bin` (33,548 B), captured live at `0x8001a1dc`. In the integrity manifest (`tools/verify_repro_inputs.py`).

## Encoder status
- **No PROPACK-equivalent encoder locally.** A public RNC-PROPACK *decoder* exists (independent oracle), but no committed/known **encoder** that reproduces PROPACK bit-streams.
- **Recompressor = literal-run encoder** (`tools/recompress_level_raw.py`, `encode_chunk`/`compress_chunk`): round-trips `decode(encode(x)) == x` (CONFIRMED), but is **functionally** equivalent only — **not byte- or size-equivalent**. Measured overhead on the chunk0 oracle: original PROPACK **24,346 B → literal ≈ 34 KB** (~**1.4×** the original compressed size; literal ≈ decompressed size + small run headers).

## The size-budget rule (the safe method)
Editor flow: decompress LEVEL.RAW → edit chunk(s) in place → **recompress only the edited chunk(s)** (unedited chunks keep their original, smaller PROPACK bytes) → reassemble → rebuild.

**Net LEVEL.RAW growth when editing one chunk ≈ (literal_size − original_PROPACK_size) ≈ 0.4 × original_comp_size of that chunk.** An edit is **LBA-safe** iff that growth stays within the file's sector slack (LEVEL01/LEVEL.RAW slack = **1820 B**, [[Asset - LBA Shift Rebuild Proof]]):

| Edit a chunk whose original comp size is… | literal grows it by ~ | vs LEVEL.RAW slack 1820 B |
|---|---|---|
| small (e.g. ch31 seeds, 584 B) | +~1.2 KB | ✅ fits (this is the proven seed case) |
| medium (e.g. ch35 mesh, 6.9 KB) | +~2.8 KB | ⚠️ over slack → LBA shift |
| large (e.g. ch32 collision, 182 KB) | +~55 KB | ❌ far over → LBA shift |

**Rule of thumb:** literal-recompress edits are LBA-safe only for **small chunks within the file's slack**; medium/large edits require the reflow (LBA-shift) path, whose in-level boot is unproven ([[Asset - LBA Shift Rebuild Proof]]). To stay byte-shrinking, **edit in place without growing the decompressed chunk** (e.g. change values, not counts) so even literal re-encode stays near the original size.

## Validating compressed output without copyrighted payloads
- Round-trip on the tracked **chunk0 oracle** (`tests/test_level_raw_codec.py`) — no copyrighted media needed (CI-safe).
- Synthetic round-trip on generated buffers (the codec test does this too).
- Never commit decompressed chunks or rebuilt RAW/discs (gitignored; [[Preservation Policy]]).

## Risks for permanent mods
- Literal inflation can silently push a file past its slot → LBA shift → unverified boot.
- The 6-byte chunk header must be preserved (recompressor takes `header6`).
- Multi-chunk edits compound growth.

## Next action
- **If a payoff needs byte-exact or non-inflating compressed edits:** evaluate a public RNC-PROPACK **encoder** against the chunk0 oracle (acceptance: `encode(decomp)==oracle_comp`). Otherwise the size-budget rule stands.
- Add an editor guard that **computes the post-edit literal size and warns if it exceeds the file's slack** (ties into [[Asset - LBA Shift Rebuild Proof]]).

## Related
[[Finding - LEVEL.RAW is compressed]] · [[Asset - LBA Shift Rebuild Proof]] · [[Asset - LEVEL.RAW Chunk Role Table]] · `tools/decode_level_raw.py` · `tools/recompress_level_raw.py` · `tests/test_level_raw_codec.py`
