---
kind: experiment
id: EXP_2026-07-08_redump_datfile_check
name: Formal Redump datfile comparison (SCUS-94288)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_game_identity_and_provenance]
fixtures: []
artifacts: [tools/redump_expected.json, extracted/re_baseline/provenance.json (regenerable, untracked)]
---

# EXP_2026-07-08_redump_datfile_check - Formal Redump datfile comparison

## Question
Does the owner's dump match the published Redump database entry for
*Disney-Pixar A Bug's Life (USA)* — the formal comparison intentionally skipped
on 2026-07-07 (old blocker B12's last open item)?

## Method
- Downloaded the Redump **Sony - PlayStation datfile** (build "(10914) (2026-06-15
  11-55-46)") from `http://redump.org/datfile/psx/` on 2026-07-08 (site is HTTP-only;
  port 443 refused). Hash metadata only — no disc content sourced.
- Transcribed the `Disney-Pixar A Bug's Life (USA)` entry into
  `tools/redump_expected.json` (plus the "(USA) (Rerelease)" entry as a related record).
- Added a `redump` sub-check to `tools/re_baseline.py --provenance` and three CI-safe
  tests to `tests/test_disc_provenance.py`; ran both.

## Observations
- **.bin = MATCH on all four values**: size 738,285,744 · CRC32 `607704bb` ·
  MD5 `2c3861a3a568d0e8119693f2117d2e00` · SHA-1 `0bc1a29748d4bd608d076495d085e825574880d1`.
- **.cue = LAYOUT_MATCH**: the owner's cue (SHA-1 `25adb139…`) differs from Redump's
  (SHA-1 `d489fb30…`, 97 B) **only** by the embedded `.bin` filename — substituting
  `(v1.0)` → `(USA)` reproduces Redump's cue SHA-1 byte-exactly. Same CRLF line
  endings, same single `TRACK 01 MODE2/2352` layout.
- The datfile's rerelease entry (size 720,789,216, CRC32 `ed6e4cb9`) independently
  confirms the `v1_1_discriminator_crc32` already recorded in `disc_provenance.json`.
- `python tools/re_baseline.py --provenance` → `PASS … redump bin=MATCH
  cue=LAYOUT_MATCH (filename-normalized)`; `pytest tests/test_disc_provenance.py` → 7 passed.

## Conclusion
The source media is now **formally Redump-verified** as *Disney-Pixar A Bug's Life
(USA)*, V1.0. `provenance_policy` upgraded from "assumed-canonical" to
"redump-verified"; archived blocker [[Blocker_-_Disc_provenance_is_unverified]] (B12)
is fully closed. Single remaining scope boundary: no PAL/NTSC-J/proto images owned
(cross-version diffing stays out of scope).
