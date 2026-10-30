---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Verification is bus-factor-1 on a private emulator fork.md
aliases:
  - "Blocker - Verification is bus-factor-1 on a private emulator fork"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Verification is bus-factor-1 on a private emulator fork.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Verification is bus-factor-1 on a private emulator fork
type: blocker
id: B2
severity: MEDIUM
category: reproducibility / dynamic-analysis-dependency
confidence: CONFIRMED
tags: [blocker, medium, reproducibility, duckstation, dynamic-analysis]
updated: 2026-06-22
---

# 🔴 B2 — The entire dynamic-evidence layer is bus-factor-1 on a private DuckStation fork

> Nearly every `CONFIRMED` result in this vault was established **dynamically**, and the dynamic method depends on a **non-stock DuckStation fork** + a JSON-RPC control server on a fixed TCP port + specific un-versioned save states + absolute `~` paths + operator visual judgement. None of it is reproducible by a third party from the repo. If the fork or the host is lost, the verification half of the project — and the project's own definition of `CONFIRMED` ([[API - determinism]]) — evaporates.

> [!note] Audit update (2026-06-18): the codec oracles `raw_chunk0_*.bin` are in fact **git-tracked** (force-added) — correcting the claim below. Still at risk: the findings YAML is untracked and the fork (`~/duckstation` @ `a6c052d46`, branch `external-debugger-control`) has **14 uncommitted files**. Concrete de-risking steps: [[Reproducibility Checklist]].

> [!check] **PARTIALLY ADDRESSED (2026-06-18) — fork pinned + critical inputs tracked, but no off-host remote.** Three core actions are done: (1) **DuckStation fork committed & pinned** — `~/duckstation` HEAD `296955321` (was `a6c052d46` + 14 dirty), recorded in `tools/FORK_COMMIT.txt`; (2) **findings store + whole Obsidian vault + RE tools now git-tracked** (ABL `438449b`, 231 files); (3) **host paths parametrized** — `tools/abl_dbg.py` now uses env `DUCKSTATION_DIR` / `ABL_SAVESTATES` (with the old defaults), so it's no longer `~`-hardwired. Codec oracles were already tracked. ⇒ a third party with the pinned fork + repo can re-derive the dynamic results. **Residual (load-bearing, see reconciliation):** the ABL repo has **no off-machine remote** (`git remote -v` is empty) — both repo history and the fork preservation set live only under `~`, so a single-disk loss destroys them; save-state fixtures remain host-local (gitignored); a few hardest claims still rest on operator eyeballing (mitigated by the reproducible `vramdiff.py` path). **Severity → Medium** (not Low: host-level bus-factor remains 1).

## Audit reconciliation (2026-06-22)
**Status: PARTIALLY ADDRESSED → severity Medium** (the earlier "RESOLVED → Low" callout overstated). Verified at audit:
- Fork **is** pinned — `tools/FORK_COMMIT.txt`, HEAD `296955321`. ✓
- Paths **are** parametrized — `tools/abl_dbg.py` reads `DUCKSTATION_DIR` / `ABL_SAVESTATES`. ✓
- Vault + findings + tools **are** git-tracked. ✓
- **BUT `git remote -v` is EMPTY** — there is no off-machine remote. Repo history *and* the fork preservation set both live under `~`; a single-disk loss destroys both. Bus-factor therefore remains **1 at the host level**.
- **Residuals:** (a) no off-host remote; (b) host-local gitignored save states; (c) some claims still rest on operator eyeballing. Not fully resolved until at least one of these (off-host push) is in place.

**Severity:** ~~Critical~~ → **Medium** (fork pinned + inputs tracked + paths parametrized, but no off-host remote → host bus-factor 1) · **Impact:** High · **Likelihood:** Low · **Confidence:** CONFIRMED · **Difficulty:** Medium

## What is known (evidence)
- The whole [[DuckStation API Index|debugger API]] (`accessLog`, `execTrace`, `transferLog`, `gp0Trace`, `memoryScan`, `gpu.readVramRect`, `experiment.run`, `findings`, `emulator.*`, `gpu.*`) is **not present in stock DuckStation**. `tools/abl_dbg.py` hardwires `sys.path.insert(0,"~/duckstation/scripts/debugger-client")` and `port=2346`. Spec: `~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md`.
- Verification depends on **un-versioned save states** under `~/.local/share/duckstation/savestates/` (see [[Save States Index]]) and operator steps like "boot `REBUILD/ABL_SEED_MOVE_TEST.bin` … reach LEVEL01 first" (`tools/verify_seed_move_ingame.py`).
- Sharp edges that make runs fragile/timing-sensitive: "settle a frame after `loadState` before `addWatch` (else crash)"; `loadState` clears non-halting watches (must re-arm); the game instance binds `2346` with a distinct token; aggressive load/write cycles have crashed the server (port refused).
- **Untracked critical inputs** (outside git, one machine): `src_re_geometry/re_findings_backup.yaml`, the `raw_chunk0_*.bin` codec oracles, the save states, and the fork itself. The findings store `OVERWRITES` on save unless `load` is called first ([[API - findings store]]).
- The hardest claims are confirmed by an **operator looking at the screen** (e.g. G28 terrain deform; "NEUTRALIZE is blind to terrain → use MOVE/RECOLOR"), not by an automated assertion.

## Why it matters
- The project's `CONFIRMED` rubric *is* reproducibility-on-this-harness ([[API - determinism]]). Bus-factor 1 across emulator build + host + save states + human judgement means **no independent party can re-derive any dynamic result**, and a single lost artifact breaks verification permanently.
- Compounds [[Blocker - Headline results rest on single-source evidence|B3]] (single-source claims are only re-checkable through this one environment) and the build pipeline's hidden host dependencies.

## Dependencies
- **Root dependency** under most dynamic findings. **Feeds:** [[Blocker - Headline results rest on single-source evidence|B3]] · [[Blocker - Analysis methods have systematic blind spots|B19]]. **Related assumptions:** A2, A12 in [[Assumptions Register]].

## Research opportunity (direction only)
- Where the missing durability lives: archiving the DuckStation fork source + exact build commit + the control spec *into the project*, versioning the minimal save states (or a scripted boot→scene route) and the codec oracle blobs, and parameterizing the absolute paths. Reducing reliance on operator eyeballing means leaning on the project's own reproducible frame/VRAM-diff path ([[API - visual diff]], `tools/vramdiff.py`) for assertions. (Direction only — not a task list.)

## Evidence & sources
- vault: [[DuckStation API Index]] · [[API - determinism]] · [[API - findings store]] · [[Save States Index]] · [[Tools Catalog]]
- corpus: `tools/abl_dbg.py`, `tools/verify_seed_move_ingame.py`, `tools/abl_starry.py`, `tools/abl_night_hook.py`, `~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md`
- See also: [[Blockers]] · [[Risk Matrix]]
