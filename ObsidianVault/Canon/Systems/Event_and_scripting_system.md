---
kind: system
id: Event_and_scripting_system
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: low
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Event and scripting system.md
aliases:
  - "Event and scripting system"
archived_source: ObsidianVault/Archive/Superseded/Systems_Event_and_scripting_system.md
patch_policy: unknown
---

# Event_and_scripting_system

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Event and scripting system.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Event & scripting system (GAP-0033) — the three lanes
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Event_and_scripting_system.md`
- Migration action: `split`
- Migration confidence: `low`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Event & scripting system (GAP-0033) — the three lanes`
- `## Lane 1 — per-scene update handlers (scene_id-dispatched CODE; NOT a VM)`
- `## Lane 2 — resident noise cursor `0x800822f4` / table `0x80017DB4` (param jitter; NOT opcodes)`
- `## Lane 3 — the AUTHORED bytecode interpreters (the real GAP-0033 answer)`
- `### 3a. Per-object mover/PATH verb VM → [[FUNC_8004C13C]]`
- `### 3b. Contact-action dispatch → [[FUNC_800586B0]]`
- `### Not an interpreter (ruled out)`
- `## Dispatch-table map (the "callback id" tables)`
- `## GAP-0033 disposition — model COMPLETE (recommend Verified)`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Event_and_scripting_system.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Phase 4 E07 correction (2026-08-02)

The authoritative resident program-table bound is 40 entry points at `0x80077AF8..0x80077B98` (end-exclusive), not the older 13- or 17-entry working bounds. A C decoder reaches 421 valid instructions, every opcode slot, and every native-call slot. Curated status and limits are in [[SYS_event_vm]]; evidence is in [[EXP_2026-08-02_phase4_e07_bounded_exhaustion]].
