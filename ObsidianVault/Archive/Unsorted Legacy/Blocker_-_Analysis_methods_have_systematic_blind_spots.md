---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Analysis methods have systematic blind spots.md
aliases:
  - "Blocker - Analysis methods have systematic blind spots"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Analysis methods have systematic blind spots.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Analysis methods have systematic blind spots
type: blocker
id: B19
severity: MEDIUM
category: dynamic-analysis
confidence: CONFIRMED
tags: [blocker, medium, methodology, dma, gte, viewport]
updated: 2026-06-22
---

# 🟡 B19 — The dynamic toolkit has structural blind spots that have already caused mis-attributions

> The project's instrumentation can't see certain classes of state, and the camera/viewport already hides certain visual changes. These are not bugs in the work — they are limits of the method that have *already* produced wrong turns (renderer flips, follower confusion) and one unachieved goal (the localized pit).

> [!check] Update (2026-06-18) — blind spots now characterized **with working mitigations** (from the live B3/B14/172dc work):
> - **`captureFrame`/`diffFrames` flush race** (false 62.7% vs real 1.6%) → trust settled-file PIL / native VRAM pixel compares, not an immediate `diffFrames`.
> - **Animation confound** → frame-match: reload the same state + equal frame counts (determinism control then = 0%).
> - **Re-arm/settle after `loadState`** → the terrain renderer needs ~10 settle frames before it fires (`run(1)` right after load returns 0 hits).
> - **read ≠ drawn** → verify a neutralize patch actually stops the function (execTrace its internal rtpt: 172→0) before trusting a 0% diff.
> - **Multi-layer overdraw / runtime-buffer writes** → a static RAM-vs-decode compare is confounded by runtime writes (localized block, not a cascade); isolate by neutralizing emitters or comparing sub-regions.
> These convert B19 from "unknown limits" to "known + worked-around." **Severity stays Medium** (these are characterized confounds, but several blind spots below are *permanent method limits*, not removable defects).

## Audit reconciliation (2026-06-22)
**Status: PARTIALLY ADDRESSED → severity Medium (stays OPEN).** Reconciling frontmatter and body to **Medium** (the earlier "→ Low" callout overstated — characterized ≠ eliminated).
- **STALE bullet RESOLVED:** "Model↔world scale is unmeasured" is no longer true — **G33** calibrated scale = **1.000** via orthonormal GTE-column norms. That item is struck below.
- The remaining items are **PERMANENT method limits with documented mitigations**, not fully "resolved": DMA-updated state is invisible to CPU watchpoints (→ use **transferLog**, `gpu.vramWriteLog`, `provenance.timeline`, or GTE render hooks); scratchpad `0x1F800000` is not covered by `memoryScan`/`accessLog` (→ read manually or capture via `debugger.snapshot` selected memory); `NEUTRALIZE` is structurally blind to terrain (→ use `gpu.traceRegion` / `gpu.pickObject` plus MOVE/RECOLOR + VRAM-diff); near-ground geometry clips off the bottom at 512×224 (→ frame-matched VRAM-diff). Mitigations bound the risk but don't remove the limits.
- **Stays OPEN at Medium.**

**Severity:** **Medium** (permanent method limits with workarounds; one stale item resolved) · **Impact:** Medium · **Likelihood:** Medium · **Confidence:** CONFIRMED · **Difficulty:** Medium

## What is known (evidence)
- **DMA-updated structures are invisible to CPU watchpoints.** `accessLog`/`memoryScan` cover main RAM only; the gem's contact-array "followers" are DMA-updated, so watchpoints saw nothing and several slots correlated with the screen yet didn't *drive* it ([[INV - Green sparkly bobbing gem (save _7-_8-_9)]]).
- **Scratchpad `0x1F800000` is not covered** by `memoryScan`/`accessLog` (the camera/view struct there must be read manually).
- **`NEUTRALIZE` is structurally blind to terrain** (camera locks to Flik's Y + uniform texture) and **near-ground geometry clips off the bottom at 512×224** — a real change can be off-screen ([[API - determinism]], [[Open Questions]]).
- ~~**Model↔world scale is unmeasured**~~ — **RESOLVED (G33, 2026-06-22):** scale calibrated to **1.000** via orthonormal GTE rotation-column norms; the visual buffer (model-space, strip-ordered) and world-space collision share a unit scale, so a spatially-correlated visual+collision edit (the "photogenic pit") can now be targeted.
- **Audio/SPU timing is not reproducible** on the harness ([[API - determinism]]).

## Why it matters
- These blind spots bound what dynamic evidence can establish and feed the single-source-evidence risk ([[Blocker - Headline results rest on single-source evidence|B3]]); they also block the overlapping-writer attribution in collision ([[Blocker - Collision internals are partly undecoded|B18]]) and any spatial visual/collision co-edit.

## Dependencies
- **Depends on:** [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]] (the harness defines the blind spots). **Feeds:** [[Blocker - Headline results rest on single-source evidence|B3]] · [[Blocker - Collision internals are partly undecoded|B18]].

## Research opportunity (direction only)
- For DMA/scratchpad-resident data, start with `provenance.timeline` / `transferLog.resolve` / `gpu.vramWriteLog` when a RAM/VRAM range exists; use GTE-input render hooks (the technique already behind [[Finding - GPU primitive injection]] / `abl_starry.py`) when the source is scratchpad-only. Frame-matched VRAM-diff ([[API - visual diff]]) still catches off-screen/occluded changes the eye misses.

## Evidence & sources
- vault: [[API - determinism]] · [[Finding - GPU primitive injection]] · [[Finding - Visual is not collision]] · [[API - visual diff]] · [[INV - Green sparkly bobbing gem (save _7-_8-_9)]] · [[Open Questions]]
- corpus: `src_re_geometry/geometry_g30_terrain_render_source_plan.md` (§15.3, §16, §20)
- See also: [[Blockers]] · [[Risk Matrix]]
