---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Fixtures/Fixtures.md
aliases:
  - "Fixtures"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Fixtures/Fixtures.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Fixtures
type: moc
tags: [moc, fixture]
---

# Fixtures — section hub

> A *fixture* is a save state with a documented, reproducible purpose. Load one to reproduce any experiment. Full table in [[Fixtures Index]]; raw `.sav` catalog in [[Save States Index]].

## The fixtures
- [[Fixture - g30 openground]] — flat open dirt; primary G29/G30 working state (player sector sec186).
- [[Fixture - g30 openfloor]] — big open pebbled floor; clean visible-ground view (⚠️ walk-forward spawns enemy+fence).
- [[Fixture - night starry]] — result: sky turned to starry night.
- [[Fixture - starry night workbench]] — working bench for the starry-night injection.

## How to use
[[API - loadState]] → **settle one frame** → [[API - addWatch]] (loadState clears non-halting instrumentation, so re-arm). Source of truth: `fixtures:` block in `src_re_geometry/re_findings_backup.yaml`.

## Related
[[Fixtures Index]] · [[Save States Index]] · [[Experiments Index]] · [[Home]]
