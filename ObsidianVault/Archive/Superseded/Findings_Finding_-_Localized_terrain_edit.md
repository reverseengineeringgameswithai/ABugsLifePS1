---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Localized terrain edit.md
aliases:
  - "Finding - Localized terrain edit"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Localized terrain edit.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Localized_terrain_edit.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Localized terrain edit
type: finding
confidence: CONFIRMED
gstep: G30
tags: [finding, rendering, terrain, method]
---

# Finding — Localized terrain editing works (but a dramatic pit is rendering-limited)

> You can edit terrain quads inside a screen box; what's hard is a *photogenic* localized pit — that's a rendering/viewport limit, not a tooling limit.

> [!warning] Edit target is the occluded buffer (2026-06-20 · GAP-0009/0011)
> The SXY-capture **method** here is valid, but it edits `fcn.800172dc`'s buffer (`0x8012c1d0`) — now known to be the **occluded** general-mesh buffer, not the visible floor (= LEVEL.DAT via [[FUNC_80010000]], f13). For a *visible* localized edit, apply the same method to the f13 DAT vert-Y lever. This compounds with the "rendering-limited pit" caveat. See [[Experiment - Visible floor renderer neutralize]].

**Confidence:** CONFIRMED · **Established:** G30 R6 · **Findings-store id:** f9

## Summary
Method: EXEC at [[FUNC_800172DC]] rtpt `0x80017464`, capture per-quad SXY + the `a1` buffer pointer, then edit the quads whose SXY fall inside a chosen screen box (diff-confirmed). **Limits:** near ground clips off the screen bottom (`y>200` at native 512×224) so you can't screen-select the closest quads; selectable mid quads are small so Y edits look subtle; camera follows Flik in Y and the texture is uniform/gouraud — so a *uniform* matched lower is invisible. A dramatic localized matched pit is therefore rendering-limited.

## Evidence
Live [[API - execTrace]] capture of per-quad SXY + [[API - scatterWrite]] edits within a screen box, verified by [[API - gpu.readVramRect]] + [[API - visual diff]]. The buffer is strip-ordered, not spatial, so spatial targeting must go through projected SXY.

## Related functions
[[FUNC_800172DC]]

## Related memory structures
[[MEM - Terrain vertex buffer 8012C1D0]]

## Related experiments
[[Experiment - G30 localized terrain edit]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - execTrace]] · [[API - scatterWrite]] · [[API - gpu.readVramRect]] · [[API - visual diff]] · [[API - snapshot bundle]]

## Next steps
Use the GTE-trace/frame-diff harness to calibrate model↔world scale and target a spatial region; combine with the [[Finding - Collision lever sector186|collision lever]] for a matched pit.

## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md` §16; findings-store f9
