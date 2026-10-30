---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - findings store.md
aliases:
  - "API - findings store"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - findings store.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - findings store
type: api
category: Findings
tags: [api, duckstation, findings, fixtures, persistence]
---
# API — findings store

> The agent's persistent RE notebook: findings + fixtures persisted to YAML. This vault is the human-readable mirror of it.

## Methods & syntax
- **`findings.upsert {finding}`** (auto-id `f<N>`; sets created/updated), **`findings.get {id}`**, **`findings.delete {id}`**, **`findings.list {game_serial?, confidence?, type?}`**.
- **`findings.save {path?}`** (writes findings+fixtures), **`findings.load {path?}`** (REPLACES in-memory store with file).
- **`fixtures.add {fixture}`** (auto-id `x<N>`; `save_state_path` REQUIRED), `fixtures.get/list`, **`fixtures.load {id}`** (loads the save state).
- **Schema:** *Finding* = `{id, address, address_end, name, type:field|function|table|asset|routine|hypothesis|note, confidence:UNKNOWN|LIKELY|CONFIRMED, evidence_refs:[{kind:access_log|memory_scan|screenshot|snapshot_bundle|diff|manual_note, summary, path, hash, frame, pc, note}], notes, game_serial, source_save_state, tags}`. *Fixture* = `{id, name, save_state_path, game_serial, description, frame, tags, expected_start_pc}`.

## Best use in ABL RE
Record every confirmed/likely fact as you go, with evidence refs and the fixture that reproduces it. Default `confidence` = LIKELY; promote to CONFIRMED only after re-deriving from a named fixture ([[API - experiment runner]]).

## Common mistakes / gotchas
> [!warning] **Always `findings.load` FIRST.** Instances do NOT auto-load `re_findings.yaml`, and `findings.save` **OVERWRITES** the whole file — so saving without loading first destroys prior findings. Canonical ABL backup: `src_re_geometry/re_findings_backup.yaml`.
- Default path = `<user data dir>/re_findings.yaml`; any absolute path accepted; never writes into the source tree.

## ABL examples
Findings **f1–f13** (sky cache, sky table, terrain renderer/buffer, collision table/lever, libgte leaf, visible-ground) and fixtures **x1/x2** (g30 openground/openfloor) live here — see [[Findings Index]] and `src_re_geometry/re_findings_backup.yaml`.

## Related
[[API - experiment runner]] · [[API - saveState]] · [[Fixtures Index]] · [[Findings Index]] · [[Confirmed Knowledge]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
