---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Checksum Manifest.md
aliases:
  - "Checksum Manifest"
migration_action: superseded
superseded_by:
  - SYS_game_identity_and_provenance
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Checksum Manifest.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Checksum Manifest
type: reference
updated: 2026-06-20
tags: [reference, provenance, checksums, preservation, milestone1, b12]
---

# Checksum Manifest — source media identity

> Authoritative provenance for the project's source disc and key files (Milestone 1 / [[Gap Audit|GAP-0014]]). Records **hashes and metadata only** — never the copyrighted bytes ([[Preservation Policy]]). Hashes were computed locally 2026-06-20 from the owner's image. Companion: [[Asset - Disc file map]] (the on-disc layout), `tools/verify_repro_inputs.py` (integrity manifest for derived inputs).

## Release identity
| Field | Value |
|---|---|
| Title | **Disney / Pixar — A Bug's Life** |
| Serial | **SCUS-94288** |
| Region | **NTSC-U (USA)** |
| Developer | **Traveller's Tales** (confirms [[Finding - Build toolchain and PROPACK provenance]]) |
| Publisher | Sony Computer Entertainment |
| Release date | 1998-11-01 · UPC 711719428824 · 1 disc |
| Version | **V1.0** (this copy). The later V1.1 rerelease differs (recorded disc CRC32 `ed6e4cb9`). |
| Disc master dates | files dated **1995-11-30 … 1998-10-21** (per `REBUILD/abl.xml`); master ≈ Oct 1998. |

## Hashes (computed 2026-06-20)
**Disc image** `Disney-Pixar A Bug's Life (v1.0).bin` (MODE2/2352, **738,285,744 B**, 313,897 sectors):
| Algo | Value |
|---|---|
| CRC32 | `607704bb` |
| MD5 | `2c3861a3a568d0e8119693f2117d2e00` |
| SHA-1 | `0bc1a29748d4bd608d076495d085e825574880d1` |

**Cue sheet** `Disney-Pixar A Bug's Life (v1.0).cue` · SHA-1 `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5`

**Boot executable** `SCUS_942.88` (PS-X EXE, 471,040 B) · SHA-1 `af43de22474f15664d0e17498fbd27faeb7ed111` · MD5 `5848df330a0e4583dcfdd22d1fe9b0ff` · load `0x80010000`, entry `0x8005F690`.

> LEVEL01/LEVEL.DAT (the primary modding target) and the codec oracles are hash-tracked separately in `tools/verify_repro_inputs.py` / `tools/repro_inputs.sha256`.

## Provenance status (B12)
- ✅ **Internally consistent + matches recorded public values.** The computed CRC32/MD5 equal the values the project previously noted as "matching public hashes," and the boot-EXE SHA-1 matches [[docs path|EXECUTABLE_AND_OVERLAYS]] (`af43de22…`). The CRC32 `607704bb` is the canonical single-track verification value used by Redump-derived datfiles.
- 🟡 **Formal Redump datfile comparison pending** — a one-step cross-check against the redump.org PSX datfile entry for SCUS-94288 (compare CRC32/MD5/SHA-1 per track). Not blocking; the CRC32 above is the key. *(Do not source the image itself from third parties — verify the owner's dump only.)*
- **Regional/proto scope:** PAL (SCES-*) / NTSC-J and any prototype builds are **out of scope** — none owned; cross-version diffing is not pursued. Recorded here so the boundary is explicit (the V1.1 CRC `ed6e4cb9` is noted only to distinguish this V1.0).

## How to verify a copy
1. Hash the image: `crc32` / `md5sum` / `sha1sum` → compare to the table above.
2. The disc rebuilds **byte-exact** from `REBUILD/abl.xml` via mkpsxiso ([[Finding - Disc rebuild is byte-exact]]) — a second, structural provenance check.

## Sources
- Release metadata: [psxdatacenter — SCUS-94288](https://psxdatacenter.com/games/U/D/SCUS-94288.html) (region/serial/date/UPC/developer).
- Disc/EXE hashes: computed locally from the owner's image (2026-06-20).

## See also
[[Asset - Disc file map]] · [[Preservation Policy]] · [[Finding - Disc rebuild is byte-exact]] · [[Finding - Build toolchain and PROPACK provenance]] · [[Asset - Disc image and rebuild]] · [[Blocker - Disc provenance is unverified]] · [[Roadmap]]
