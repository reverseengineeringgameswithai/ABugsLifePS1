---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Create a deterministic experiment.md
aliases:
  - "Playbook - Create a deterministic experiment"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Create a deterministic experiment.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Create a deterministic experiment
type: playbook
tags: [playbook, method, determinism]
---

# Playbook — Create a deterministic experiment

> The foundation under every CONFIRMED finding. A result you can't reproduce from a named fixture with scripted input and a fixed frame count is at most **LIKELY**.

## When to use
Any time you want a result you can trust, re-run, and cite.

## Steps
1. **Pin the start.** Save a fixture with [[API - saveState]] (or reuse one from [[Fixtures Index]]). Never experiment from "wherever the game happens to be."
2. **Pin timing settings** (see [[API - determinism]]): Rewind OFF, Run-ahead OFF/fixed, CPU overclock 100%, CD speedup default, matching BIOS/region/disc.
3. **Load + settle.** [[API - loadState]] then advance ≥1 frame **before** arming any watch (`addWatch` right after load can crash). Remember loadState clears all non-halting watches — re-arm.
4. **Script the input.** Use [[API - controller input]] (`setControllerState`/`pressButton`) — never hand-press. Held buttons re-apply every frame.
5. **Advance a fixed number of frames**, then pause ([[API - execution control]] `advanceFrames`, or [[API - advanceUntil]] for a condition).
6. **Capture + diff.** Prefer the [[API - experiment runner]] (`experiment.run` / `experiment.compareRuns`) which composes load→baseline→perturb→advance→capture→diff in one call.

## CONFIRMED vs LIKELY
- `experiment.compareRuns` counterfactual that produces the *predicted* change ⇒ **CONFIRMED**.
- A single uncontrolled snapshot / correlation ⇒ **LIKELY**.
Record the verdict in the [[API - findings store]] (load before save!).

## Reproducible vs not
Bit-exact: CPU/GTE registers, main RAM, scratchpad, save states. NOT reproducible: audio timing, exact CD read scheduling. Screenshots are corroboration, not proof.

## ABL example
Every G28/G29/G30 result was promoted to CONFIRMED this way; the disc-build experiments add an operator visual test on top. → [[Experiment - G29 collision lever validation]].

## Related
[[API - determinism]] · [[API - experiment runner]] · [[Playbook - Verify a hypothesis]] · `~/duckstation/docs/external-debugger-determinism.md`
