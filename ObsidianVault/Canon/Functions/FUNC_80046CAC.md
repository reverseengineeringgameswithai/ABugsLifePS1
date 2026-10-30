---
kind: function
id: FUNC_80046CAC
aliases:
- FUNC_80046CAC
- '0x80046cac'
- resident_level_t_seed_plant_dan_glue
address: '0x80046cac'
name: resident_level_t_seed_plant_dan_glue
status: byte_matched
confidence: confirmed
source_state: original_game
calls:
- FUNC_80041A74
reads: []
writes: []
evidence:
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- src/main/80046cac_resident_level_t_seed_plant_dan_glue.c
patch_policy: unknown
---

# FUNC_80046CAC - resident_level_t_seed_plant_dan_glue

## Status

**Byte-matched from C** (decomp substrate): `src/main/80046cac_resident_level_t_seed_plant_dan_glue.c` compiles to the exact original bytes at `0x80046cac` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x80046cac`
- Matching source: `src/main/80046cac_resident_level_t_seed_plant_dan_glue.c`
- Callees: [[FUNC_80041A74]]

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
