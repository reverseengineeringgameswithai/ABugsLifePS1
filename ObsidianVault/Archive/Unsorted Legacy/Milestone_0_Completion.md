---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Milestone 0 Completion.md
aliases:
  - "Milestone 0 Completion"
migration_action: superseded
superseded_by:
  - RE_BASELINE_INDEX
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Milestone 0 Completion.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Milestone 0 Completion
type: plan
updated: 2026-06-20
tags: [plan, roadmap, milestone, reproducibility, completion]
---

# Milestone 0 — Project Hygiene & Reproducibility — Completion Report

> Execution record for [[Roadmap]] **Milestone 0**. **Status: COMPLETE except GAP-0001** (external backup/vendor step). Goal: make every existing result reproducible by a second machine/person, and make the navigation layer tell the truth. **Outcome: 12 of 15 gaps fully closed; 2 advanced to a clean follow-up; 1 residual (GAP-0001) is operator-gated** (off-machine remote). M0 deliverables **tracked in git commit `0d6b0af`** (2026-06-20); 0 copyrighted artifacts committed (only the 2 policy-allowed codec oracles).

## Charter recorded (GAP-0043)
**Decided: modding-grade goal, decomp-forward method.** The owner elected to invest in decompilation infrastructure proactively to reduce downstream friction. This **supersedes [[Remediation Plan]] §4a "B1 won't-do"**: B1/B15/B17 (GAP-0021/0018/0020) are now **active, prioritized** work; M2→M3 are promoted to run right after M0. Recorded in [[Roadmap]] §1; reflected in [[Risk Matrix]] Current tiers and [[CONTRIBUTING]].

## Per-gap outcomes
| Gap | Outcome | What changed |
|---|---|---|
| **GAP-0043** charter | ✅ Decided | [[Roadmap]] §1 charter (decomp-forward); supersedes Remediation §4a. |
| **GAP-0008** findings store: 2 CONFIRMED floor answers | ✅ Resolved | `re_findings_backup.yaml`: f5/f10 → `SUPERSEDED`; f4/f8/f9 caveated; **f13 authoritative + evidence_refs populated**. YAML re-parses; exactly **one** CONFIRMED visible-floor answer (f13). |
| **GAP-0009** occlusion not propagated | ✅ Resolved | Callouts added to [[Home]], [[Finding - Terrain on-disk source is chunk 35]], [[Finding - Localized terrain edit]] (+ FUNC/MEM below). |
| **GAP-0010** `fcn.800172dc` mislabeled "terrain" | ✅ Resolved | [[FUNC_800172DC]] + [[MEM - Terrain vertex buffer 8012C1D0]]: reframed as **shared mesh renderer**, visible-floor role superseded. |
| **GAP-0007** Risk Matrix stale | ✅ Resolved | [[Risk Matrix]] "Current tiers — reconciled 2026-06-20" section; baseline column flagged. |
| **GAP-0003** host-hardcoded paths | ✅ Resolved | `tools/_env.py` + 16 tools de-hardcoded; `grep ~ tools/*.py` = **empty**; `py_compile` = **0**; `tools/requirements.txt` added. |
| **GAP-0002** untracked inputs / overwrite hazard | ✅ Resolved (1 follow-up) | `tools/verify_repro_inputs.py` + baselined `tools/repro_inputs.sha256` (5/5 core, 27 fixtures); guards the findings-store overwrite. **Follow-up:** `git add -f tools/raw_chunk0_*.bin` to track the oracles (commit-on-ask). |
| **GAP-0012** Tools Catalog under-counts | ✅ Resolved | [[Tools Catalog]] regenerated from disk (**71** files, tracked/untracked marked). |
| **GAP-0004** no sharing policy | ✅ Resolved | [[Preservation Policy]] created. |
| **GAP-0042** no CONTRIBUTING | ✅ Resolved | [[CONTRIBUTING]] created. |
| **GAP-0013** editor README stale | ✅ Resolved | `level_editor/README.md`: corrected to describe the working "3D Scene" drag-to-move tab. |
| **GAP-0041** no project roadmap | ✅ Resolved | [[Roadmap]] + [[Gap Audit]] + [[Project Index]] (prior session) linked from [[Home]]. |
| **GAP-0006** artifacts in `tools/` | ✅ Resolved (no-op + doc) | Loose `*.png`/`LEVEL_*.RAW` already gitignored; oracles flagged for force-add. No files deleted (research preserved). |
| **GAP-0005** extractors uncommitted | 🟢 Advanced | [[Asset - Asset extraction recipe]] makes `extracted/` reproducible-by-recipe; one-command VAB/GFX extractors → [[Roadmap]] M4. |
| **GAP-0001** fork/remote reproducibility | 🟡 Residual (operator) | Pin verified (`tools/FORK_COMMIT.txt` = `296955321`). **Off-machine remote + fork vendoring need a remote URL / `~/duckstation` access** — cannot be done autonomously. |

## Verification evidence
- **Findings store:** `python3 -c "yaml.safe_load(...)"` → 13 findings, 2 fixtures, parses; visible-floor CONFIRMED set = `['f13']`.
- **Tool portability:** `grep -rn ~ tools/*.py` → none; `python3 -m py_compile tools/*.py` → exit 0; `tools/_env.py` defaults resolve byte-identically on the dev host.
- **Critical inputs:** `verify_repro_inputs.py` → 5/5 core OK, 27 fixtures present.
- **Legal hygiene:** `git ls-files` → **0** tracked disc/BIOS/save artifacts (311 tracked).

## Hand-off checklist (2026-06-20)
1. ✅ **No copyrighted artifacts tracked** — verified before commit; only the 2 codec oracles (policy-allowed) are binary.
2. ✅ **M0 docs + tool files tracked** — committed `0d6b0af` (31 files: 19 vault notes, findings store, 11 tool files). Your 22 unrelated pre-existing vault WIP files were deliberately **left unstaged**.
3. ✅ **Oracles added** — `tools/raw_chunk0_*.bin` force-added (permitted by [[Preservation Policy]]; required for codec reproducibility).
4. 🟡 **GAP-0001 left open (operator-gated)** — create an off-machine git remote + `git push`; vendor the DuckStation fork (submodule/tarball) + `EXTERNAL_DEBUGGER_CONTROL.md`. Needs a remote URL / `~/duckstation` access. *Until then, dynamic results remain single-host.*
5. ✅ **M0 marked complete except GAP-0001** here + in [[Roadmap]] + [[Remediation Plan]].

Other follow-ups: GAP-0005/M4 — script the VAB/GFX extractors + add `extracted/SHA256SUMS`. The `level_editor/` directory (incl. my GAP-0013 README fix) is **not yet tracked** — tracking the editor source is a separate decision (its `.venv/` must stay out).

## Next milestone
Per the charter, **M2 → M3 (decomp-forward substrate)**: pin PsyQ/library census + CI ([[Gap Audit|GAP-0016/0017]]), then the symbol map, overlay disassembly, and the first `splat`/`objdiff` scaffold ([[Gap Audit|GAP-0018/0020/0021]]).

## See also
[[Roadmap]] · [[Gap Audit]] · [[Reproducibility Checklist]] · [[Remediation Plan]] · [[Risk Matrix]] · [[Preservation Policy]] · [[CONTRIBUTING]]
