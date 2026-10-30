---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Project documentation is stale and contradictory.md
aliases:
  - "Blocker - Project documentation is stale and contradictory"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Project documentation is stale and contradictory.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Project documentation is stale and contradictory
type: blocker
id: B11
severity: LOW
category: documentation-integrity
confidence: CONFIRMED
tags: [blocker, low, documentation, integrity, staleness]
updated: 2026-06-22
---

# 🟢 B11 — Status labels, the memory index, and the findings store are stale / self-contradictory

> The project's *navigation layer* — the notes a new session reads to gauge what's done — disagrees with itself in load-bearing places. A reader trusting a status header, the memory index, or the findings store at face value will either re-walk solved work or over-trust unsolved work. This is documented here, **not** silently edited (per the brief: record conflicts rather than resolve them).

> [!check] **M7/M8 RESOLUTION (2026-06-21):** several specific conflicts catalogued below are now closed. The **findings store** is reconciled — **f13 is the sole CONFIRMED** visible-floor answer ([[Gap Audit|GAP-0008]] Resolved; f5/f10 Superseded), so "both CONFIRMED" no longer holds. The **vault propagation** of "chunk-35 = the visible terrain surface" is corrected with the occlusion caveat across the clean tracked base ([[Gap Audit|GAP-0009]]/[[Gap Audit|GAP-0010]] Resolved). The **G29 "PLAN ONLY" vs executed** drift is reconciled ([[G29 - Collision source]] CONFIRMED; Pass-3 both arms run, [[Gap Audit|GAP-0038]] Verified). The **codec "solved" vs "gate"** wording remains the live residual. B11 stays a standing blocker (🟢 Low) because doc-drift re-accrues without the [[CONTRIBUTING]] per-status update rule — the entries below are preserved as the historical record.

**Severity:** Low · **Impact:** Medium · **Likelihood:** High · **Confidence:** CONFIRMED · **Difficulty:** Low (to reconcile)

## Audit reconciliation (2026-06-22)
Frontmatter severity is reconciled **down to Low** to match the body (the M7/M8 callout already grades this 🟢 Low). B11 **stays OPEN (partially addressed)** — by its own closure rule it cannot close while catalogued contradictions persist.

**Verified FIXED:**
- Codec "solved" vs "blocking gate" wording — **mostly** reconciled.
- Chunk-35 "= visible terrain surface" over-claim — corrected with the occlusion caveat.
- Findings-store reconciliation (f13 sole CONFIRMED; f5/f10 Superseded) + overwrite-on-save hazard documented.
- Floor-render answer (LEVEL.DAT-backed visual floor) reconciled.

**STILL LIVE (do NOT claim fixed — being corrected separately in this same audit pass):**
- (a) `geometry_g29_collision_source_plan.md` header still says "PLAN ONLY / no emulator run" while its body has confirmed live results.
- (b) `geometry_g30_terrain_render_source_plan.md` status drift — "R3 IN PROGRESS" vs "R5/R6 DONE".
- (c) Dashboard [[Blockers]] + [[Risk Matrix]] still grade B2/B11/B13 inconsistently vs these notes.
- (d) [[Blocker - Original toolchain ground-truth is unmined|B13]] note developer-name drift.

B11 can be **revisited for closure once (a)–(d) land**.

## What is known (evidence) — the specific conflicts
- **Codec "solved" vs "blocking gate" — across ≥4 authorities.** [[Home]], the header of [[Finding - LEVEL.RAW is compressed]], and the cross-session memory say the LZ codec is **SOLVED** (byte-exact decode + working recompress). But [[Open Questions]] **P1 #1**, the warning in [[MEM - LEVEL.RAW chunk model]], the *same* Finding note's own **"Next steps"** ("GATE … edits are RAM/save-state only"), and `docs/GEOMETRY_RE_PLAN.md` all still call it an **unsolved blocking gate**. The Finding note contradicts *itself*.
- **G29 "PLAN ONLY" vs executed.** The `geometry_g29_collision_source_plan.md` header reads "ANALYSIS + RUNTIME-WATCH PLAN ONLY … no emulator run," and the memory index repeats "PLAN ONLY — no build/run" — yet the body records four live DuckStation sessions and a **validated RAM collision edit**. ([[G29 - Collision source]] correctly marks it CONFIRMED — the *source docs* are stale.)
- **G30 status drift.** The plan's top status says an early round "IN PROGRESS" while later sections declare R5/R6 "DONE/FINAL."
- **Findings store contradictions + hazards.** `re_findings_backup.yaml` holds `f5/f10` (visible floor = chunk 35) **and** `f13` (visible floor = LEVEL.DAT) **both CONFIRMED** ([[Blocker - Headline results rest on single-source evidence|B3]]); `f13`'s evidence_refs are blank; the store **overwrites on save** unless `load` is called first ([[API - findings store]]), guarded only by a manual, untracked backup.
- **Vault-level propagation.** [[Confirmed Knowledge]] and [[Finding - Visible terrain renderer]] present `fcn.800172dc`/chunk-35 as "the visible terrain surface," which the project's own §20.1 VRAM-diff shows is ~99 % occluded.

## Why it matters
- The confidence vocabulary (`CONFIRMED`/`LIKELY`/…) is only as good as its upkeep; when the navigation notes are stale, *every* label becomes suspect, and due-diligence cannot use headers/the memory index/the findings store to gauge state. Bus-factor-1 ([[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]]) makes drift more likely (one author, fast iteration).

## Dependencies
- Cross-cutting; tightly related to [[Blocker - Headline results rest on single-source evidence|B3]].

## Research opportunity (direction only)
- Reconciling status headers + the memory index + the findings store against document bodies, filling `f13`'s evidence_refs, and a consistency check that no two findings make contradictory `CONFIRMED` claims about the same subject would restore trust in the labels. (Direction only — this audit deliberately does not rewrite the conflicting notes.)

## Evidence & sources
- vault: [[Home]] · [[Open Questions]] · [[Confirmed Knowledge]] · [[Finding - LEVEL.RAW is compressed]] · [[MEM - LEVEL.RAW chunk model]] · [[G29 - Collision source]] · [[API - findings store]]
- corpus: `src_re_geometry/geometry_g29_collision_source_plan.md`, `geometry_g30_terrain_render_source_plan.md`, `re_findings_backup.yaml`, `docs/GEOMETRY_RE_PLAN.md`, memory `MEMORY.md`
- See also: [[Blockers]] · [[Risk Matrix]]
