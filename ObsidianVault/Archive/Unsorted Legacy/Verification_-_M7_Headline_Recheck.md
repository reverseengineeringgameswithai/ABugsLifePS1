---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Verification - M7 Headline Recheck.md
aliases:
  - "Verification - M7 Headline Recheck"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Verification - M7 Headline Recheck.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Verification - M7 Headline Recheck
type: plan
status: In Progress
date: 2026-06-21
gaps: [GAP-0038, GAP-0011, GAP-0039, GAP-0040, GAP-0021]
tags: [m7, verification, headline, control-document]
---
# Verification — M7 Headline Recheck

> **M7 baseline.** M7 (Verification, Testing & Matching) raises the project's headline findings to its own `CONFIRMED` bar (reproducible **and** causal: ≥2 independent methods or a counterfactual). This note tracks each headline's verification state and what each M7 lane owes. Started 2026-06-21.

## M6 entry condition (carried in)
**M6 = scoped-closed / not globally complete.** All four Roadmap M6 acceptance clauses are supported (event VM Verified; PATH PARTIAL; warp 0035A Verified / 0035B Blocked-by-design; editor seed read/edit/export tracked+tested — 30/30 tests). The deep residuals (GAP-0023 world-origin, GAP-0001 full collision enumeration, GAP-0035B clean handoff, GUI seed drag-move) are **carry-forward gaps, not M6 blockers**. M7 attacks the verification residuals.

## Headline status board
| Headline | Claim | Bar met? | Evidence |
|---|---|:--:|---|
| Visible floor source | **= LEVEL.DAT (`fcn.80010000`)**, incl. the **spawn area** | ✅ **CONFIRMED** | [[Experiment - Spawn-floor render source]] — pick+write-watch+source-classification on pristine `SCUS-94288_1.sav`; chunk-34/35 reconciled as occluded/non-visible; `fcn.800172dc`=0 calls |
| Visual ≠ collision | visible (DAT) ≠ collision (chunk-32 `0x800a7e48`) | ✅ **CONFIRMED (≥2 methods)** | Source separation at spawn ✅ + **G29 Pass-3 pristine-vs-patched counterfactual ✅ (both arms 2026-06-21)**: phase-matched differential differs in only the visual-edit halfword (`0x8017918a` 5001 vs 6025); collision hash/resolver/player-Y/footing byte-identical → [[Experiment - G29 Pass-3 differential]] |
| Findings store | one CONFIRMED visible-floor answer | ✅ **reconciled** | GAP-0008 done: `re_findings_backup.yaml` now has **f13 as the sole CONFIRMED** visible-floor answer (7 evidence refs incl. the M7 experiments); f5/f10 Superseded; f4/f8 stale caveats corrected (surgical edit, no `findings.save`) |
| Codec / seed edit | byte-exact decode; in-budget seed disc edit | ✅ tracked tests | `tests/` 30/30 (codec + 10 seed round-trips); live `+1242 B` in-slack edit local-only |
| Generality | architecture holds beyond LEVEL01 | 🟢 **LEVEL02 floor CONFIRMED per-pixel** | GAP-0039 lane below — floor under Flik on scene 3 = DAT/`fcn.80010000` (per-pixel pick→leaf→caller `ra`); one stage proven, all-stage generality still LIKELY |

## M7 lane status (this first pass)
1. **GAP-0011 — spawn-floor pick/trace** → ✅ **DONE.** Spawn floor = DAT (`fcn.80010000`, sources `0x801765e4..0x8018fd94` = file `0x15dec..0x2f59c`, contains Candidate A `0x188cc`). Contradiction reconciled. → [[Experiment - Spawn-floor render source]].
2. **GAP-0038 — G29 Pass-3** → ✅ **DONE (counterfactual complete).** Spawn-area source separation is the 2nd independent angle; the pristine-vs-patched **G29 Pass-3** ran (both arms 2026-06-21): the G28 BIN was rebuilt locally and a **phase-matched** pristine-vs-G28 differential differs in **only the visual-edit halfword** while the collision sector hash, resolver candidate/plane reads, player-Y writer path, and Flik's footing trajectory are byte-identical. The from-boot replay's post-spawn phase is per-launch (the *trajectory* compares only within a matched phase; the *sector-hash* invariant is phase-robust). Optional residual: a 2nd edit/scene. → [[Experiment - G29 Pass-3 differential]].
3. **GAP-0040 — replayable headlines** → ✅ **four landed.** `tools/trace_spawn_floor.py`, `tools/trace_g29_pass3_arm_a.py`, `tools/trace_g29_pass3_arm_b.py` (disc-parameterised), and now `tools/trace_level02_floor.py` + [[Playbook - Replay headline experiments]] convert the spawn-floor, visual≠collision, and LEVEL02-floor headlines to one-command replays (identity/disc guards, deterministic JSON, self-checking verdict; no media committed).
4. **GAP-0039 — non-LEVEL01 generality** → 🟢 **LEVEL02 floor CONFIRMED per-pixel (2026-06-21).** [[Experiment - LEVEL02 floor source]] did the missing **per-pixel** work on `level02.sav` (scene 3, `G_DAT_BASE_PTR=0x8015e22c`): pick the floor under Flik (GP0(3c) packets `0x801d0d68/af8/f3c`) → write-watch → the store is a **shared GTE leaf `0x80019xxx`** → `execTrace` the leaf's `ra` shows **40/40 callers inside `fcn.80010000`** (`0x8001067c/0x800108b8`); `fcn.80010000` `a0` = **16/16 in DAT** (file `0x7204..0x30098`); collision `0x800a7e48` populated/separate. ⇒ the LEVEL02 visible floor under Flik = **LEVEL.DAT via `fcn.80010000`**. **Correction:** the first pass's "`fcn.800172dc` = 0 calls" was a **single-frame sampling artifact** — robust multi-frame shows **both** drivers active (~4/frame each); the floor *specifically* is the DAT driver, `fcn.800172dc` draws other meshes. *Grade: CONFIRMED for this stage/position* (4 corroborating dynamic methods + identity guard, deterministic); all-stage generality + a LEVEL02 counterfactual remain (still **LIKELY** overall). Local-only (GAP-0001).
5. **GAP-0021 — matching/decomp** → scope-gated, untouched (no modding payoff in this pass).

## Reproducibility ceiling (applies to all dynamic M7 work)
Everything dynamic rides the operator's local DuckStation fork + local fixtures (`.sav`, gitignored) → **GAP-0001/0002**. Replay scripts make headlines *re-runnable on the operator's machine*; third-party reproducibility waits on fork/fixture preservation. Recorded honestly, not as `CONFIRMED`-for-all.

## Next single step
**This pass (2026-06-21, follow-on):** (a) findings store reconciled — GAP-0008 done (f13 sole CONFIRMED); (b) LEVEL02 floor confirmed **per-pixel** — GAP-0039 advanced ([[Experiment - LEVEL02 floor source]]), correcting the first-pass single-frame artifact. Remaining M7 fronts: a **LEVEL02/LEVEL03 collision-table deep trace** (chunk index/count per stage) to take GAP-0039 from per-pixel-floor to a full cross-level chunk+collision map; optionally a **2nd visible-floor edit/scene** to harden GAP-0038 generality. GAP-0001 (off-machine fork/fixture preservation) is the standing reproducibility ceiling.

## Related
[[Roadmap]] · [[Gap Audit]] · [[Experiment - Spawn-floor render source]] · [[Experiment - G29 Pass-3 differential]] · [[Experiment - LEVEL02 floor source]] · [[Playbook - Replay headline experiments]] · [[Finding - Visual is not collision]] · [[Finding - Candidate A is DAT-backed visual terrain]]
