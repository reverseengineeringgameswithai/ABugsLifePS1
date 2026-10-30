---
kind: system
id: Brown_seed_plant_behaviors
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_confirmed
confidence: confirmed
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Brown seed plant behaviors.md
aliases:
  - "Brown seed plant behaviors"
archived_source: ObsidianVault/Archive/Superseded/Systems_Brown_seed_plant_behaviors.md
patch_policy: unknown
---

# Brown_seed_plant_behaviors

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Brown seed plant behaviors.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Brown seed plant behaviors — completely solved
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Brown_seed_plant_behaviors.md`
- Migration action: `convert_to_canon`
- Migration confidence: `confirmed`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Brown seed plant behaviors — completely solved`
- `## 1. How the seed is cracked open (same chain at all four tiers)`
- `## 2. What each tier does for Flik (live-measured physics)`
- `## 3. Carry + discard (the seed lifecycle)`
- `## Notes / residuals`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Brown_seed_plant_behaviors.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Phase 4 B01 trampoline closure (2026-08-03)

The mature type-5 brown mushroom handler at `0x8005C58C` assigns player vertical velocity `-3328` on every qualifying cap contact. This is a literal replacement, not a multiplier or a function of incoming fall speed. It also sets mode `5`, clears the contact and timer halfwords, and sets action `3`.

A validated retained Interpreter capsule captures four contacts across mushroom slots 6, 5, 4, and 2. Incoming velocities `1792`, `1536`, `2816`, and `2816` all become exactly `-3328`. Chained mushrooms therefore reuse the same per-contact law.

The physical bounce stores precede Bonus 2 sequence bookkeeping. Re-touching an identity already in the five-byte sequence resets the sequence to that identity but still bounces. New identities append. Filling five distinct entries separately overrides the launch to `-16384`, sets transition `6`, fade `60`, and bonus flag bit 0. The shared effect identifier is `15`.

Evidence and bounded-exhaustion rationale: [[EXP_2026-08-03_phase4_b01_mushroom_trampoline]].

### B01 deep confirmation

A second pristine-ASM C pass proved the normal bounce/latch stores dominate every reachable Bonus 2 bookkeeping path. The trampoline/reset region has no player-vertical-velocity read, no eligibility write, and no plant-position write. Its shared effect tail also has no player-velocity write, so the fifth-distinct `-16384` override survives return. All four capsule contacts share the same two-frame evolution from `-3328`/mode `5` to `-3072`/mode `6`. See [[EXP_2026-08-03_phase4_b01_mushroom_trampoline]].

## B04 cannon correction and bounded closure - 2026-08-03

The older cannon summary's `vy=-7680` impulse is superseded by
[[SYS_cannon_plant]]. Pristine ASM fixes the actual source at `0x800486B8`:
`vy=-8192`; same-update gravity produces the first frame-boundary `-7936`, and
`-7680` is the following boundary. The type-2 handler only starts the 17-tick
seat/lockout and animation handoff. The validated B04 capsule also closes the
cannon-to-dandelion path: latch `11` changes terminal descent from `+4096` to
`+350` until ordinary landing clears the latch. See
[[EXP_2026-08-03_phase4_b04_cannon_plant]].
