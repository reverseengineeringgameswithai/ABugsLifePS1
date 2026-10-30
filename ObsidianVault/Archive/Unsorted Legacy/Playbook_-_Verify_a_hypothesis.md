---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Verify a hypothesis.md
aliases:
  - "Playbook - Verify a hypothesis"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Verify a hypothesis.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Verify a hypothesis
type: playbook
tags: [playbook, method, hypothesis]
---

# Playbook — Verify a hypothesis

> Turn a guess into a CONFIRMED/DISPROVEN entry in the [[Hypotheses]] tracker. The goal is a **causal counterfactual**, not just a correlation.

## When to use
You have a claim like "X controls Y" (e.g. "this buffer is the floor").

## Steps
1. **State it falsifiably** and add it to [[Hypotheses]] as INVESTIGATING.
2. **Predict a perturbation's effect.** "If X is the floor, setting X+delta will move Flik's resting Y by ~delta."
3. **Build a deterministic experiment** ([[Playbook - Create a deterministic experiment]]).
4. **Run the counterfactual** with [[API - experiment runner]] `experiment.compareRuns` (same fixture, run A = baseline, run B = perturbed). Compare `A.after` vs `B.after`.
5. **Decide:** predicted change appears ⇒ CONFIRMED. Nothing / something else ⇒ DISPROVEN (or refine). Record in [[Hypotheses]] **and** the [[API - findings store]].
6. **For visual claims**, corroborate with [[API - gpu.readVramRect]] + [[API - visual diff]] or a disc build + operator test (screenshots are corroboration only).

## Watch out for
- "Read-confirmed but visually silent" ≠ confirmed control (G8/G12/G13/G15 read fine but didn't move anything). Insist on a *visible/measurable effect*.
- A buffer can be *read* yet rejected before use (entry24 — [[Finding - entry24 is a culling row]]).

## ABL example
G26 disproved the "floor at `0x801bdc58`" hypothesis with a WRITE-watch (0 hits) → [[Finding - 0x801bdc58 is compressed source]]. G29 confirmed the sector-table floor with a 1:1 RAM-edit counterfactual → [[Finding - Collision RAM edit moves footing 1to1]].

## Related
[[Hypotheses]] · [[API - experiment runner]] · [[API - findings store]] · [[Playbook - Create a deterministic experiment]]
