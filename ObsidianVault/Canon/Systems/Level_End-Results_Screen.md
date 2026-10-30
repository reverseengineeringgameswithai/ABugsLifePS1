---
kind: system
id: Level_End-Results_Screen
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: low
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Level End-Results Screen.md
aliases:
  - "Level End-Results Screen"
archived_source: ObsidianVault/Archive/Superseded/Systems_Level_End-Results_Screen.md
patch_policy: unknown
---

# Level_End-Results_Screen

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Level End-Results Screen.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Level End-Results Screen
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Level_End-Results_Screen.md`
- Migration action: `split`
- Migration confidence: `low`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Level End-Results Screen`
- `## Repro method`
- `## Finding 1 — grain / FLIK-count / third counter are NOT broken (count-up animation, not a bug)`
- `## Finding 2 — letters are spinning pseudo-3D objects; the "mirrored K" is NOT a confirmed texture bug (retracted)`
- `### What IS confirmed about the draw mechanism`
- `### Residual work (not completed this pass)`
- `## Finding 3 — CONFIRMED: all three counters (grain, FLIK letters, gold-kill row) are dynamic, driven by live RAM globals, not hardcoded per-save constants`
- `## Extending FLIK to up to 8 letters — design (not yet implemented)`
- `### Empirical test toward "FLIKFLIK" (8 letters), 2026-07-05`
- `## Operator note on process`
- `## Reproduction commands`
- `# advance in <=30-frame chunks; large single advanceFrames calls (e.g. 600) have`
- `# intermittently dropped the debugger socket (server-side) in this session —`
- `# chunk them and reconnect/relaunch the isolated instance if the socket resets.`
- `## Finding 4 — the results-screen draw routine, FULLY DECODED (2026-07-05 continuation)`
- `## Finding 5 — FLIKFLIK (8-letter) extension: LIVE-PROVEN PARTIAL, not disc-persisted`
- `## Finding 6 — numerator-digit regression: root-caused and fixed (2026-07-05, second pass)`
- `### Still open (unchanged from Finding 5)`
- `### Honest status / what's NOT done (superseded by Finding 7 below for the layout design)`
- `## Finding 7 — dynamic word-length-aware layout (2026-07-05, third pass)`
- `### Design`
- `### Tuning iteration (operator-caught, fixed live)`
- `### Verification — full requested test matrix, all 7 cases confirmed via native-resolution screenshots`
- `### Residual notes`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Level_End-Results_Screen.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
