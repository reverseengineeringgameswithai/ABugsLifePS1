---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - determinism.md
aliases:
  - "API - determinism"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - determinism.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - determinism
type: api
category: Determinism
tags: [api, duckstation, determinism, confidence]
---
# API — determinism (the reproducibility contract)

> The rules that make an experiment reproducible — and the confidence rubric (CONFIRMED / LIKELY / UNKNOWN) every finding is graded against.

## The contract (holds only if the experiment is "closed")
1. Start from a **named save state** ([[Fixtures Index|fixture]]), not "wherever the game is."
2. **Pin timing settings.**
3. Apply input as **scripted, frame-accurate API injection** ([[API - controller input]]), not by hand.
4. Advance a **fixed** number of frames, then pause.

**Settings to pin:** CPU overclock (default 100%), CD read/seek speedup, **Rewind OFF**, **Run-ahead OFF or fixed**, region/BIOS/disc must match the fixture. If two re-runs disagree on CPU/RAM, a setting changed.

## Reproducibility table
- **Bit-exact:** CPU registers, PC, main RAM (2 MB), scratchpad, GTE/COP0, save-state contents → basis of every CONFIRMED claim.
- **Mostly (small diffs possible):** screenshot / displayed frame → corroboration only.
- **NOT reproducible:** audio/SPU timing; CD async read *scheduling* (contents stable, timing approximate).

## Confidence rubric
- **CONFIRMED** — reproducible AND causal: re-derived from a fixture + a controlled perturbation produces the predicted change ([[API - experiment runner]] `compareRuns`), or ≥2 independent methods agree.
- **LIKELY** — single uncontrolled snapshot / correlation without counterfactual / not re-run.
- **UNKNOWN** — not observed, or causality not established.

## ABL caveats (hard-won)
- **NEUTRALIZE is blind to terrain** (camera locks to Flik's Y + uniform texture) → use MOVE/RECOLOR/localized tests. See [[Finding - Visual is not collision]].
- Near-ground geometry clips off the bottom at native **512×224** → a real change can be off-screen ([[Open Questions]]).

## Related
[[API - experiment runner]] · [[API - controller input]] · [[API - loadState]] · [[API - findings store]] · [[Playbook - Create a deterministic experiment]] · [[Playbook - Verify a hypothesis]]

Source: ~/duckstation/docs/external-debugger-determinism.md
