---
kind: system
id: SYS_game_identity_and_provenance
name: Game identity and source-media provenance
aliases: [Checksum Manifest, Checksum_Manifest, Blocker_-_Disc_provenance_is_unverified]
status: live_confirmed
confidence: confirmed
source_state: original_game
functions: []
memory: []
tables: []
constants: []
evidence: [EXP_2026-07-08_re_baseline_run, EXP_2026-07-08_redump_datfile_check]
src_paths: [tools/disc_provenance.json, tools/redump_expected.json, tools/re_baseline.py, tests/test_disc_provenance.py]
---

# SYS_game_identity_and_provenance

## Purpose
Single Canon home for WHAT game this project reverse-engineers and HOW we know our
source media is exactly that release. Machine-readable twin: `tools/disc_provenance.json`
(verified by `tools/re_baseline.py --provenance` and guarded by `tests/test_disc_provenance.py`).

## Confirmed behavior

### Release identity
| Field | Value |
|---|---|
| Title | Disney / Pixar — A Bug's Life |
| Serial | **SCUS-94288** |
| Region | NTSC-U (USA) |
| Developer | Traveller's Tales (see [[Finding - Build toolchain and PROPACK provenance]]) |
| Publisher | Sony Computer Entertainment America |
| Release | 1998-11-01 · UPC 711719428824 · 1 disc |
| Version | **V1.0** (the later V1.1 rerelease has disc CRC32 `ed6e4cb9` — discriminator only) |
| Disc master | files dated 1995-11-30 … 1998-10-21 (per `REBUILD/abl.xml`); master ≈ Oct 1998 |

### Hashes (computed 2026-06-20 from the owner's dump; re-verified PASS 2026-07-08)
| File | Identity |
|---|---|
| `Disney-Pixar A Bug's Life (v1.0).bin` (MODE2/2352, 738,285,744 B, 313,897 sectors) | CRC32 `607704bb` · MD5 `2c3861a3a568d0e8119693f2117d2e00` · SHA-1 `0bc1a29748d4bd608d076495d085e825574880d1` |
| `Disney-Pixar A Bug's Life (v1.0).cue` | SHA-1 `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5` |
| `SCUS_942.88` (PS-X EXE, 471,040 B) | SHA-1 `af43de22474f15664d0e17498fbd27faeb7ed111` · MD5 `5848df330a0e4583dcfdd22d1fe9b0ff` |

### Provenance policy
- **Redump-verified** (2026-07-08, supersedes the 2026-07-07 assumed-canonical decision):
  the owner's `.bin` matches the published Redump entry **"Disney-Pixar A Bug's Life (USA)"**
  on all four values — size 738,285,744 · CRC32 `607704bb` · MD5 `2c3861a3…` · SHA-1 `0bc1a297…`.
  The `.cue` is **layout-identical**: substituting only the embedded `.bin` filename
  (`(v1.0)` → `(USA)`) reproduces Redump's cue SHA-1 `d489fb30…` byte-exactly.
  The datfile's "(USA) (Rerelease)" entry (CRC32 `ed6e4cb9`) independently confirms the
  recorded V1.1 discriminator. Reference metadata: `tools/redump_expected.json`
  (transcribed from the Redump PSX datfile, 2026-06-15 build, retrieved 2026-07-08);
  no disc content was sourced from any third party.
- The image is a legal dump of the owner's disc and is never distributed;
  only hashes/metadata are recorded — never copyrighted bytes.
- Secondary structural check: the disc rebuilds **byte-exact** from `REBUILD/abl.xml`
  via mkpsxiso (0/313,897 sectors differ).
- Scope boundary: PAL / NTSC-J / prototypes are out of scope (none owned); V1.1 CRC is
  recorded only to distinguish this V1.0.

## Unknowns
- None material for identity.

## Evidence
- [[EXP_2026-07-08_redump_datfile_check]] — formal Redump datfile comparison: bin MATCH,
  cue LAYOUT_MATCH (filename-normalized).
- [[EXP_2026-07-08_re_baseline_run]] — full-hash re-verification PASS on this host.
- Supersedes archived [[Checksum_Manifest]] and fully closes archived
  [[Blocker_-_Disc_provenance_is_unverified]] (B12).
