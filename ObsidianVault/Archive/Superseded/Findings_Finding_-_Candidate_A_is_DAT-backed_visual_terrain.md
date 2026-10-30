---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Candidate A is DAT-backed visual terrain.md
aliases:
  - "Finding - Candidate A is DAT-backed visual terrain"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Candidate A is DAT-backed visual terrain.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Candidate_A_is_DAT-backed_visual_terrain.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Candidate A is DAT-backed visual terrain
type: finding
confidence: CONFIRMED
gstep: G27/G28
tags: [finding, rendering, geometry, dat]
---

# Finding — Candidate A is a DAT-backed VISUAL terrain/floor payload

> A directly-editable, LEVEL.DAT-backed mesh payload that renders a flat world-space terrain/floor stratum. Proven editable by an operator-tested disc build.

> [!success] M7 update (2026-06-21): the **spawn-area** floor under Flik is the same DAT family — `fcn.80010000` sources the whole spawn view from DAT file `0x15dec..0x2f59c` (which **contains** Candidate A `0x188cc`), `fcn.800172dc` idle. Generalizes "DAT-backed visible floor" beyond the G28 patch → [[Experiment - Spawn-floor render source]] (resolves [[Gap Audit\|GAP-0011]]).

**Confidence:** CONFIRMED (visual) · **Established:** G27 (found) → G28 (confirmed) · **Findings-store id:** f13 (related)

## Summary
- **Candidate A** = the strongest of 5 count-validated [[FUNC_80010000]] payloads (G27): DAT offset `0x188cc`, runtime `0x801790c4`, **83 vertices**, flatness **0.154**, 4502×4502, world-space, **unique** (not instanced).
- Vertex format = 12 bytes `[c0, c1, Z, pad, X, Y]`; the **edit lever is the int16 Y at vert+0xa**.
- G28 built an edit (`DAT 0x18992`, v16.y +1024) → **visible terrain deformation** in A's projected screen area.

## Evidence
- G27: all 5 payloads pass the acceptance test at EXEC `0x80010000`; A/B/C are flat world-space floor-stratum chunks (Y≈4400–5200), D/E model-space; A is unique + flattest. Tool `tools/analyze_g27_floor_candidates.py`.
- G28: runtime READ at vertex base `0x801790c8` (ra `0x800206a0`, count 83) + projection EXEC `0x80010718` (SXY central/lower band) + operator visual test = deform visible, Flik/objects render, **collision unaffected** → see [[Finding - Visual is not collision]].
- Gouraud 0x3C tiles → Y-edit reshades (low=yellow, high=purple); large edits garbage (frustum); clean range ≈ ±0x20…0x60.

## Related functions
[[FUNC_80010000]] · [[FUNC_8001EA6C]] (bridge) · [[FUNC_80019934]] (sub-emitter for bulk ground)

## Related memory structures
[[MEM - fcn.80010000 mesh payload]]

## Related experiments
[[Experiment - G28 Candidate A floor Y]] · [[Experiment - G16 emitted payload vertex wall]] (G27 analysis: `tools/analyze_g27_floor_candidates.py`)

## Related fixtures / save states
[[Fixture - g30 openfloor]]

## DuckStation APIs used
[[API - accessLog]] · [[API - execTrace]]

## Next steps
Use the localized-edit harness to target a specific screen region rather than a whole strip (the payload is strip-ordered, not spatial).

## Source
`src_re_geometry/geometry_g27_count_validated_floor_candidates.md`, `geometry_g28_candidate_a_runtime_confirmation.md`
