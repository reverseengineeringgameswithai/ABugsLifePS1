---
kind: index
id: FIXTURES_INDEX
name: Runtime fixture index
status: current
aliases:
  - Fixtures Index
  - Fixture - g30 openground
  - Fixture - g30 openfloor
  - Fixture - night live
  - Fixture - night starry
  - Fixture - starry night workbench
---

# Runtime fixture index

This is the live landing page for legacy fixture names. The old per-fixture
pages are preserved in `Archive/Unsorted Legacy`; resolving an old wikilink to
this index does **not** assert that its save, movie, runtime, or media identity
still satisfies the current evidence contract.

Current machine authorities:

- `config/phase3_runtime_fixtures.yaml` — declared runtime fixtures;
- `config/fixture_reference_sets.yaml` — reference-set membership;
- `analysis/phase4_fixture_audit.json` — Phase 4 fixture/pin audit;
- `analysis/phase0_2_external_fixture_set.json` — external fixture preservation;
- `tests/test_fixtures_manifest.py` — manifest guard.

Before reuse, require the fixture to appear in the applicable current manifest,
verify its media and runtime identities, and follow the cold-boot/save-state
boundary in [[SYS_re_evidence_policy]]. Historical G30 and starry-night names
remain search aliases here only so live notes no longer route silently into
superseded documentation.

