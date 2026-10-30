---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Headline results rest on single-source evidence.md
aliases:
  - "Blocker - Headline results rest on single-source evidence"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Headline results rest on single-source evidence.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Headline results rest on single-source evidence
type: blocker
id: B3
severity: MEDIUM
category: methodology / epistemic
confidence: CONFIRMED
tags: [blocker, medium, methodology, evidence, geometry, collision]
updated: 2026-06-22
---

# 🔴 B3 — Several headline "CONFIRMED" results are single-sourced and have flipped before

> The project's marquee conclusions are real work, but the *evidence pattern* behind them is fragile: single operator eyeballs, one live run, or one pointer capture — and the corpus has a demonstrated history of promoting such captures to `CONFIRMED` and later **retracting** them. Most acutely, **the project held two contradictory `CONFIRMED` answers for which file renders the visible floor** (since **resolved** → f13/LEVEL.DAT, M7 — see the resolution callout). This is the classic "looks solved but conceals unresolved risk."

> [!check] **RESOLVED 2026-06-18 → f13 (authoritative).** A patch-verified, frame-matched, **7-scene** live-API neutralize test settled the visible-floor contradiction: `fcn.800172dc`/chunk-35 contributes **0 visible px** (it fires but is fully occluded), while `fcn.80010000`/**LEVEL.DAT draws the visible walkable floor** (its removal flattens the pebble ground). The earlier "172dc flattens the ground" was a **function-address swap** (`0x80010000` ↔ `0x800172dc`). **f5/f10 → DISPROVEN, f13 → CONFIRMED** → [[Experiment - Visible floor renderer neutralize]]. *Note: this took THREE live mis-steps (a confounded animation-diff, a `diffFrames` flush-race giving a false 62.7%, and the address-swap) before the verified test settled it — a textbook demonstration of exactly the risk this blocker tracks.*
>
> **UPDATE (M7/M8 2026-06-21):** two of the three evidence items below are now closed — the findings store is reconciled to **f13 as the sole CONFIRMED** floor answer ([[Gap Audit|GAP-0008]] Resolved), and the **G29 Pass-3 counterfactual has since been run, both arms** ([[Gap Audit|GAP-0038]] Verified), corroborating the G28 keystone. B3 stays open (**🟡 Medium**) for the *general* single-source / bus-factor-1 pattern, not these now-closed instances.

> [!note] **Audit reconciliation (2026-06-22) — frontmatter reconciled to Medium.** Frontmatter still read CRITICAL while the body had already downgraded to 🟡 Medium; frontmatter is now **MEDIUM** to match.
>
> ## Audit reconciliation (2026-06-22)
> **Status: PARTIALLY ADDRESSED → severity Medium.** The floor-render *instance* is genuinely closed: finding **f13** confirmed by **≥2 independent methods** (7-scene live neutralize + the **G29 Pass-3 counterfactual** run on both arms, with a **SHA-256-identical** collision table across the pristine/deformed images). That specific contradiction no longer carries unquantified risk. **BUT** the general single-source *pattern* persists across the **un-rechecked corpus** — most live-only `CONFIRMED` claims have not had the reproducible VRAM-diff / count-validation standard retro-applied. So the blocker stays **OPEN at Medium** for the pattern, not for the now-closed floor instance. The note is otherwise honest about its own evidence.

**Severity:** ~~Critical~~ → **Medium** (floor instance closed via ≥2 independent methods; general pattern persists) · **Impact:** High · **Likelihood:** Medium · **Confidence:** CONFIRMED · **Difficulty:** Medium

## What is known (evidence)
- **Live contradiction — visible-floor source.** `geometry_g30_terrain_render_source_plan.md` §14–17 + findings `f5/f10` conclude the visible terrain = [[FUNC_800172DC]] reading the chunk-35 buffer. The *same document's* §20.1 VRAM-diff then shows that buffer is **~99 % occluded** (a sliver), and §20.3 + finding **f13** conclude the bulk visible ground is [[FUNC_80010000]] drawing **LEVEL.DAT** objects. `re_findings_backup.yaml` holds **both as CONFIRMED**; the vault propagated the chunk-35 framing ([[Finding - Visible terrain renderer]], [[Confirmed Knowledge]]).
- **Decisive collision test never run.** `geometry_g29_collision_source_plan.md` names a Pass-3 differential (READ-watch the floor-height operand `S` over pristine vs the [[Experiment - G28 Candidate A floor Y|G28]]-deformed image) as *the* clean proof of visual≠collision independence. The operand `S` was never pinned and **Pass-3 was never executed**; the marquee result rests instead on the later sector-table live-edit chain.
- **G28 keystone = one eyeball.** The "Candidate A is visible terrain" upgrade ([[Finding - Candidate A is DAT-backed visual terrain]]) rests on a single built image + an operator visual report, with the screenshot **uncommitted**, the **Y-sign→screen mapping unconfirmed**, and the observed effect *opposite* the predicted direction.
- **Demonstrated retraction history.** The "floor payload at `0x801bdc58`" premise propagated as the working floor identity across ~9 phases (G17→G26) before falsification ([[Finding - 0x801bdc58 is compressed source]]); root cause was an **uncounted pointer capture**. The G30 terrain renderer flipped **four times in one session**; `NEUTRALIZE` was declared "structurally blind to terrain." Records were reclassified up to 3×.

## Why it matters
- Load-bearing "solved" results carry **unquantified correctness risk**, and the whole [[Finding - Visual is not collision|visual≠collision]] framing inherits any mis-attribution in A7/A8/A9 ([[Assumptions Register]]). A future effort building on these inherits hypotheses that have flipped before.
- The project *already built* the reproducible tool that would settle these (VRAM-diff / `gp0Trace`) but has not retro-applied it to the headline claims.

## Dependencies
- **Depends on:** [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]] · [[Blocker - Analysis methods have systematic blind spots|B19]]. **Related assumptions:** A7, A8, A9.

## Research opportunity (direction only)
- The uncertainty would drop sharply by re-deriving the headline geometry with the **reproducible** VRAM-diff + `gp0Trace` attribution method (native 512×224, before/after, per-emitter screen-area), reconciling `f5/f10` vs `f13`, and either running or formally retiring the G29 Pass-3 differential. The G26 count-validation acceptance test is the natural standard to apply retroactively to every live-only `CONFIRMED` claim. (Directions, not a plan.)

## Evidence & sources
- vault: [[G30 - Terrain render source]] · [[G29 - Collision source]] · [[Finding - Visible terrain renderer]] · [[Finding - Candidate A is DAT-backed visual terrain]] · [[Finding - Visual is not collision]] · [[Hypotheses]] · [[API - visual diff]] · [[API - execTrace]]
- corpus: `src_re_geometry/geometry_g30_terrain_render_source_plan.md` (§14–17, §20.1, §20.3), `geometry_g29_collision_source_plan.md` (§2.6–2.13), `geometry_g28_candidate_a_runtime_confirmation.md` (§5.3), `geometry_g26_floor_payload_reaudit.md`, `re_findings_backup.yaml` (f5/f10/f13)
- See also: [[Blockers]] · [[Risk Matrix]]
