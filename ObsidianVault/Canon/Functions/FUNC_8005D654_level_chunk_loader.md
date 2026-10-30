---
kind: function
id: FUNC_8005D654
aliases: [FUNC_8005D654, 0x8005d654, level_chunk_loader]
address: 0x8005d654
name: level_chunk_loader
status: runtime_confirmed
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: [EXP_2026-08-03_phase4_e05_actor_model_binding]
src_paths: [symbols/re_symbols.sym, analysis/phase4_e05_model_pointers_live.json, asm/hand_written/8005d654_sub_8005d654.s]
patch_policy: safe_to_read
---

# FUNC_8005D654 - model file load + per-id pointer registry write

## Purpose

Loads one named model resource and **persists its runtime pointer in the per-id
model registry**. Called from every case body of
[[FUNC_8005DAD0_level_load_chunks]] with `a3` = the model id.

## Behavior

- **First-load guard**: reads `[0x800A6300 + 4*id]` (`lw v0,25344($at)`,
  `$at = 0x800A0000 + id*4`) and returns early when already loaded.
- **Registry write**: on load it stores the resource pointer back to
  `0x800A6300 + 4*id` (`sw v0,25344($at)` at the same gp-relative slot) --
  the write that makes the registry the authority for "which model is loaded
  for this actor id".
- **Second registry**: the first-load path also consults
  `[0x800A2188 + 4*id]` (`lw a3,8584($at)`). Live, campaign-wide, that word
  EQUALS the model pointer wherever non-null, is null for id 11 (the seed --
  the corpus's one model with no `.ANM`), and null for slot 0 on scenes
  {4,5,7,9,12}. **Its writer is unattributed; do not name it an ANM table.**

## Verification

All 16 level saves: the registry's non-null slot set is EXACTLY
`{0 (Flik)} u {this level's pool ids} u {this level's plant slots}` --
`analysis/phase4_e05_model_pointers_live.json`, gated by
`tests/test_phase4_e05.py`.

## Related

[[SYS_actor_model_loading]] · [[FUNC_8005DAD0_level_load_chunks]] ·
[[FUNC_8005D924_level_chunk_file_load]] (the seed's dedicated variant)