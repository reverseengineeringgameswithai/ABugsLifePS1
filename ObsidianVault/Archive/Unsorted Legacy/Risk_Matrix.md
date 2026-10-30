---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Risk Matrix.md
aliases:
  - "Risk Matrix"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Risk Matrix.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Risk Matrix
type: index
updated: 2026-06-21
tags: [index, blockers, risk, due-diligence]
---

# Risk Matrix

> One row per blocker. **Impact** / **Likelihood** = consequence × probability *against the full-RE yardstick* (see [[Blockers]]). **Severity** = the assigned tier. **Confidence** = how sure this audit is that the blocker is real and correctly characterized (vault vocab, [[API - determinism]]). **Difficulty** = effort to resolve. Sorted by severity. Each row links to its note (full evidence + research opportunity there).
>
> ⚠️ **The `Severity` column below is the 2026-06-18 *baseline*.** Most blockers were self-downgraded the same day (Remediation log) and the [[Roadmap|decomp-forward charter]] (2026-06-20) re-prioritized the decomp items. See **[[#Current tiers — reconciled 2026-06-20 GAP-0007|Current tiers]]** below for the live state ([[Gap Audit|GAP-0007]] resolved).
>
> ⚠️ **2026-06-22 deep audit** re-verified every blocker against actual repo files (conservative "close only if completely verified"). The authoritative corrected dispositions are in the **[[Blockers#⚠️ Audit reconciliation (2026-06-22) — supersedes stale severities below|Blockers dashboard audit table]]**. Net: **0** blockers fully closed; B6/B13 resolved-as-scoped; the rest partial/open. Key correction vs the refresh below: **B2 = Medium, not Low** (no off-host git remote → host bus-factor still 1).

| ID | Blocker | Category | Impact | Likelihood | Severity | Conf. | Difficulty |
|----|---------|----------|:------:|:----------:|:--------:|:-----:|:----------:|
| B1 | [[Blocker - Decompilation has no build or symbol substrate]] | decompilation / toolchain | High | High | 🔴 Critical | CONFIRMED | High |
| B2 | [[Blocker - Verification is bus-factor-1 on a private emulator fork]] | reproducibility / dynamic-analysis | High | High | 🔴 Critical | CONFIRMED | Medium |
| B3 | [[Blocker - Headline results rest on single-source evidence]] | methodology / epistemic | High | Medium | 🔴 Critical | CONFIRMED | Medium |
| B4 | [[Blocker - Byte-exact disc reproduction is unproven]] | build-reproduction | High | Medium | 🔴 Critical | LIKELY | High |
| B5 | [[Blocker - Audio subsystem is completely unanalyzed]] | audio | High | High | 🟠 Major | CONFIRMED | Low–Med |
| B6 | [[Blocker - FMV video is completely unanalyzed]] | video | High | High | 🟠 Major | CONFIRMED | Low–Med |
| B7 | [[Blocker - Character and plant model formats are unreversed]] | asset-decoding | High | High | 🟠 Major | CONFIRMED | High |
| B8 | [[Blocker - RE depth is LEVEL01-only]] | disc-layout / runtime | Medium | High | 🟠 Major | CONFIRMED | Medium |
| B9 | [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified]] | level-format | High | High | 🟠 Major | CONFIRMED | High |
| B10 | [[Blocker - LEVEL.DAT non-pickup records are undecoded]] | level-format / struct | Medium | High | 🟠 Major | CONFIRMED | Med–High |
| B11 | [[Blocker - Project documentation is stale and contradictory]] | documentation-integrity | Medium | High | 🟠 Major | CONFIRMED | Low |
| B12 | [[Blocker - Disc provenance is unverified]] | provenance / versions | High | Low | 🟠 Major | CONFIRMED | Low |
| B13 | [[Blocker - Original toolchain ground-truth is unmined]] | toolchain / provenance | Medium | High | 🟠 Major | CONFIRMED | Low |
| B14 | [[Blocker - Recompressor cannot reproduce original compression]] | compression / build-repro | Medium | Medium | 🟡 Medium | CONFIRMED | Medium |
| B15 | [[Blocker - Symbol recovery has no authoritative map]] | symbol-recovery | Medium | High | 🟡 Medium | CONFIRMED | Med–High |
| B16 | [[Blocker - Struct and type recovery is shallow]] | struct-recovery | Medium | High | 🟡 Medium | CONFIRMED | Med–High |
| B17 | [[Blocker - Function boundaries and overlays evade the static call graph]] | function-matching | Medium | Medium | 🟡 Medium | CONFIRMED | High |
| B18 | [[Blocker - Collision internals are partly undecoded]] | collision | Medium | Medium | 🟡 Medium | CONFIRMED | Med–High |
| B19 | [[Blocker - Analysis methods have systematic blind spots]] | dynamic-analysis | Medium | Medium | 🟡 Medium | CONFIRMED | Medium |
| B20 | [[Blocker - Offline texture and font extraction is absent]] | textures / fonts | Medium | Medium | 🟡 Medium | LIKELY | Low–Med |

## Current tiers — reconciled 2026-06-20 (GAP-0007)
> The `Severity` column above is the **2026-06-18 baseline**. Most blockers were self-downgraded the same day (Remediation log) and the [[Roadmap|decomp-forward charter]] promoted the decomp items (B1/B15/B16/B17) from "won't-do/optional" to **active**. This table is the **current** state.
>
> **Refreshed 2026-06-21 (M7 outcomes + M8 reconciliation):** B3/B8/B11 updated below for the M7 headline verification — [[Gap Audit|GAP-0038]] **Verified** (visual≠collision now meets the ≥2-method bar: source separation + the G29 Pass-3 counterfactual, both arms), [[Gap Audit|GAP-0039]] **LEVEL02 floor CONFIRMED per-pixel**, [[Gap Audit|GAP-0008]] findings store **Resolved** (f13 sole CONFIRMED) — and the M8 doc-status reconciliation ([[Gap Audit|GAP-0007]]/[[Gap Audit|GAP-0012]]/[[Gap Audit|GAP-0042]]). Third-party reproducibility of the dynamic evidence remains gated on [[Gap Audit|GAP-0001]] (private fork + local fixtures), so these are operator-local confirmations.

| B | Current | Δ | Why / resolves via |
|---|---|:--:|---|
| B1 | 🔴 Critical · **active** | scope-flip | Decomp substrate; won't-do→prioritized (charter) → [[Gap Audit\|GAP-0021]] |
| B2 | 🟡 Medium *(corrected 2026-06-22; was 🟢 Low)* | ⬇ | Fork pinned; vault/tools/findings tracked & paths parametrized — but `git remote -v` is **empty**, so host bus-factor is still 1 (single-disk loss = repo history + fork preservation set both gone). Low only after an off-host remote lands → [[Gap Audit\|GAP-0001]] |
| B3 | 🟡 Medium | ⬇⬇ | **M7 (2026-06-21):** central headline now meets the ≥2-method bar — source separation + G29 Pass-3 counterfactual (both arms); no longer single-source. Medium (not Low) only because the counterfactual is one edit/payload/scene; generality residual pairs with GAP-0039 → [[Gap Audit\|GAP-0038]] **Verified** |
| B4 | 🟡 Medium | ⬇ | Unpatched rebuild byte-exact; size-change/LBA-shift unproven → [[Gap Audit\|GAP-0025]] |
| B5 | 🟢 Low | ⬇ | Audio formats extracted; runtime SPU path open → [[Gap Audit\|GAP-0031]] |
| B6 | 🟢 Low | ⬇ | FMV extracted; in-engine playback trigger open → [[Gap Audit\|GAP-0032]] |
| B7 | 🟢 Low | ⬇ | `.ALL`/`.ANM` decoded end-to-end; fine grammar → [[Gap Audit\|GAP-0026]] |
| B8 | 🟢 Low | — | Architecture validated 12–15 stages; **M7 (2026-06-21):** LEVEL02 (scene 3) floor CONFIRMED per-pixel (DAT via `fcn.80010000`); full per-level chunk/collision map still open → [[Gap Audit\|GAP-0039]] |
| B9 | 🟠 Major | — | 66/69 chunk roles still unpublished → [[Gap Audit\|GAP-0022]]/0023 |
| B10 | 🟢 Low | ⬇ | All 11 DAT record roles decoded |
| B11 | 🟢 Low | ⬇ | M0 reconciled Matrix/findings/naming; **M7:** findings store → f13 sole CONFIRMED ([[Gap Audit\|GAP-0008]] Resolved); **M8 (2026-06-21):** Matrix refreshed for M7 + the stale GAP-0007/0012/0042 statuses reconciled. Low = acute contradictions cleared; re-accrues without the [[CONTRIBUTING]] per-status update rule → [[Gap Audit\|GAP-0007]] |
| B12 | 🟡 Medium | — | USA V1.0 hash-verified; Redump match / manifest open → [[Gap Audit\|GAP-0014]] |
| B13 | 🟢 Low | ⬇ | Toolchain identified; exact PsyQ version / library census open → [[Gap Audit\|GAP-0016]] |
| B14 | 🟡 Medium | — | Literal recompressor game-accepted; byte-exact PROPACK open → [[Gap Audit\|GAP-0024]] |
| B15 | 🟡 Medium · **active** | scope-flip | Symbol map; optional→prioritized (charter) → [[Gap Audit\|GAP-0018]] |
| B16 | 🟡 Medium · **active** | scope-flip | Struct recovery; optional→prioritized (charter) |
| B17 | 🟡 Medium · **active** | — | Overlays not disassembled; prioritized (charter) → [[Gap Audit\|GAP-0020]] |
| B18 | 🟢 Low | ⬇ | Collision math decoded; PATH nav-graph shelved → [[Gap Audit\|GAP-0034]] |
| B19 | 🟢 Low | ⬇ | Method blind spots known + worked-around |
| B20 | 🟢 Low | ⬇ | Textures/fonts extracted (text=image-baked); CLUT exactness → [[Gap Audit\|GAP-0027]] |

## How to read severity vs. likelihood
- A few blockers are **high-impact but low-likelihood-of-biting**: e.g. B12 (the master is *probably* a good dump — a mismatch would be catastrophic but is unlikely). These are kept at Major because the downside is foundational.
- The whole-subsystem gaps (B5/B6/B7) are **certain** gaps (likelihood High) but most are **low-difficulty** because the formats are industry-solved — high severity yet cheap to retire. B7 (`.ALL`/`.ANM`) is the exception: bespoke Iguana format, genuinely hard.
- The infrastructure/epistemic criticals (B1/B2/B3/B4) are the ones that **gate the meaning of everything else** — they are why "Overall (full RE)" in the [[Blockers|scorecard]] is ~2.5 despite strong local results.

## See also
[[Blockers]] · [[Assumptions Register]] · [[Open Questions]] · [[Hypotheses]]
