---
kind: function
id: FUNC_80045AAC
aliases:
- FUNC_80045AAC
- '0x80045aac'
- cd_audio_mix_control_5aac
address: '0x80045aac'
name: cd_audio_mix_control_5aac
status: byte_matched
confidence: confirmed
source_state: original_game
calls:
- FUNC_8006DC90
reads: []
writes: []
evidence:
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- src/main/80045aac_cd_audio_mix_control_5aac.c
patch_policy: unknown
---

# FUNC_80045AAC - cd_audio_mix_control_5aac

## Status

**Byte-matched from C** (decomp substrate): `src/main/80045aac_cd_audio_mix_control_5aac.c` compiles to the exact original bytes at `0x80045aac` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x80045aac`
- Matching source: `src/main/80045aac_cd_audio_mix_control_5aac.c`
- Callees: [[FUNC_8006DC90]]

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
