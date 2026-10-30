---
kind: system
id: Enemy_AI_state_machine
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Enemy AI state machine.md
aliases:
  - "Enemy AI state machine"
archived_source: ObsidianVault/Archive/Superseded/Systems_Enemy_AI_state_machine.md
patch_policy: unknown
---

# Enemy_AI_state_machine

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Enemy AI state machine.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Enemy AI state machine (behavior model)
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Enemy_AI_state_machine.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Enemy AI state machine (behavior model)`
- `## Per-enemy map (all five — live-verified)`
- `## Cross-level generality (operator fixtures, 2026-06-22 — scenes 3/4/5/6/10)`
- `## Dispatcher`
- `## Chaser AI — `FUNC_8004DF18` (0x8004df18–0x8004ea84, a0 = slot `0x80095358`) — bee/spider/mosquito`
- `## Boss: BIRD — bespoke, DETERMINED (`FUNC_8004DD98`)`
- `## Boss: HOPPER (final boss) — PARTIAL (fight decoded; defeat shelved)`
- `### ⚠️ Tooling limitation — DuckStation movies recorded DIGITAL buttons only (no analog stick) — ✅ FIXED 2026-06-26`
- `## Boss: THUMPER — PARTIAL (actor + Y-law + defeat-chain decoded; combat bookkeeping is overlay-resident = OPEN)`
- `## Boss: THUD — UNTESTED`
- `## Stationary enemies (worm, pill-beetle) = mover-VM `FUNC_8004C13C``
- `## Contact damage = global collision`
- `## Enemy death / despawn + gold-berry permanence (RCG-022, 2026-07-03)`
- `## Residuals (bounded / named — not open gaps)`
- `## Evidence / reproduction`
- `## Related`

## Corrections to the archived source

**Hopper's identity (`## Boss: HOPPER`) is WRONG in the archived note — 2026-08-02.**
The archived section claims Hopper "REUSES the chaser AI... Actor = chaser slot
`0x80095358`, driver `FUNC_8004DF18`". This is the exact same claim SHAPE the
archived note's own later Thumper correction (residual #5) found wrong:
`0x80095358` is the CAMERA, not a boss — Thumper turned out to be a regular
chunk-31 actor, id 16. The Hopper section was written 2026-06-22, before that
correction (2026-07-03), and was never revisited.

Live re-identification this pass (`analysis/phase4_d20_hopper.json`): Hopper is
**id=22**, a chunk-31 actor at the same live table (`0x8009FE04`, stride
`0x84`) already correct for Thumper — a singular instance (unlike the many
generic id=15/id=11 background actors present in the same scene), confirmed
live/moving, at a plausible distance from Flik in a save captured mid
white-berry-throw, with a distinctive on-screen figure matching a large boss
silhouette. Not yet closed to the same certainty as Thumper's own
disassembly-confirmed identity (`gpu.pickObject` hits the same known
vertex-buffer-only limitation already documented for Thumper) — treat as
high-confidence, not yet fully proven. Full detail and residuals:
`analysis/phase4_d20_hopper.json`.

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Enemy_AI_state_machine.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results. **Exception**: the `## Boss: HOPPER` section's actor-identity claim is superseded — see "Corrections to the archived source" above.
