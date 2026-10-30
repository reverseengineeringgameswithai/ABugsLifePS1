---
kind: function
id: FUNC_800526FC
aliases: [FUNC_800526FC, 0x800526fc]
address: 0x800526fc
name: results_screen_render
status: live_confirmed
confidence: medium
source_state: original_game
system: [SYS_level_results_screen, SYS_hud_counters]
calls: [hud_draw_sprite_tile, hud_draw_glyph, result_draw_glyph_dim, result_upload_anim_frame, play_sound]
reads: []
writes: []
uses_tables: []
evidence:
  - EXP_2026-07-08_understanding_campaign_u1
src_paths: []
patch_policy: unknown
---

# FUNC_800526FC - results screen render

## Purpose

Composites the level-results / HUD screen: draws sprite tiles and glyphs (`hud_draw_sprite_tile`, `hud_draw_glyph`, `result_draw_glyph_dim`), uploads animation frames (`result_upload_anim_frame`), and plays sounds (`play_sound`). The `result_*` callees are specific to the results screen.

## Evidence (runtime, u1.2)

- **dynamic** — fired live during LEVEL01 (`execTrace`).
- Call-graph: callees `hud_draw_sprite_tile`, `hud_draw_glyph`, `result_draw_glyph_dim`, `result_upload_anim_frame`, `play_sound`.
- Tier **proven** (the `result_*` callee names are unambiguous). Exact HUD-vs-results split of its body not yet pinned.

Address `0x800526fc` (3900 B). See [[EXP_2026-07-08_understanding_campaign_u1]] · [[SYS_level_results_screen]].
