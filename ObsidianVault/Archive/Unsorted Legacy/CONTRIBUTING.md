---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/CONTRIBUTING.md
aliases:
  - "CONTRIBUTING"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/CONTRIBUTING.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: CONTRIBUTING
type: reference
updated: 2026-06-21
tags: [reference, onboarding, workflow, contributing]
---

# Contributing

> How to do work in this project so it stays reproducible, evidence-based, and self-consistent. Resolves [[Gap Audit|GAP-0042]]. Read [[README]] (vault conventions) and [[Preservation Policy]] (legal/sharing) first.

## Project charter (decided 2026-06-20)
**Goal = modding-grade behavioral RE; method = decomp-forward.** The end goal is moddable LEVEL01+ (move/add pickups, deform terrain, recolor sky, move seeds, inject GPU prims). The owner has elected to **invest in decompilation infrastructure proactively** (buildable/diffable substrate, symbol map, overlay disassembly) to cut downstream friction — so [[Blocker - Decompilation has no build or symbol substrate|B1]]/[[Blocker - Symbol recovery has no authoritative map|B15]]/[[Blocker - Function boundaries and overlays evade the static call graph|B17]] are **active work**, not "won't-do." See [[Roadmap]] §1.

## Before you start
1. Read [[Home]] → [[Confirmed Knowledge]] → [[Open Questions]] (priority-sorted) and the [[Roadmap]] near-term plan.
2. Before any live experiment: read **`.claude/skills/duckstation-external-debugger/SKILL.md`** — the required guide for safely driving the local debugger fork (isolated-instance launch, game/fixture identity verification, watches, save states, movies, evidence capture) — plus [[DuckStation API Index]] + [[Playbook - Create a deterministic experiment]]. Sharp edges: settle after `loadState` before `addWatch`; **`findings.load` BEFORE `findings.save`** (it overwrites — see the guard below). **All live-debugger / dynamic-evidence work is operator-gated until [[Gap Audit|GAP-0001]] is resolved** (it rides one private DuckStation fork + host-local `.sav` fixtures, so it reproduces only on the owner's machine — record such results as local-only, never as third-party-reproducible `CONFIRMED`).
3. Provision tools: `pip install -r tools/requirements.txt`. Host paths come from env vars (`ABL_DIR`, `DUCKSTATION_DIR`, `ABL_SAVESTATES`) with on-host defaults — see `tools/_env.py`. **Never hardcode `/home/<user>`** in a tool (CI/grep enforces 0).
4. Run `python3 tools/run_safe_tests.py` before committing tool changes. This suite is intentionally independent of ROMs, BIOS, extracted assets, saves, DuckStation, and GPU access; see [[Toolchain Census]].

## Evidence standard (non-negotiable)
Every claim promoted to [[Confirmed Knowledge]] / a `Finding -` / the findings store must follow [[Roadmap]] §6: file path + offset/address + tool & version + command + observed output + **confidence** + date + related notes. `CONFIRMED` means **reproducible AND causal** (a counterfactual, or ≥2 independent methods) per [[API - determinism]]. A single uncontrolled snapshot is at most `LIKELY`. *Screenshots corroborate; they don't prove.* Use a **fixture** (save state/movie) + a fixed frame count; for animated subjects use a **phase-matched control**.

## Status & priority vocab
Tag tasks/notes with the [[Roadmap]] taxonomies: status `Unknown · Needs Evidence · In Progress · Blocked · Verified · Superseded`; priority `P0` (blocks safe/reproducible work) · `P1` (blocks major progress) · `P2` (important) · `P3` (cleanup). When a result flips an old one, mark the old note **Superseded** and link the replacement (don't delete it — history matters).

## Workflow rules
- **Never edit the pristine disc** `Disney-Pixar A Bug's Life (v1.0).bin/.cue`. Patch a *copy*; build to a separate output. Tools verify pristine bytes + size before patching.
- **Never `git add -f` a copyrighted or local-capture artifact** (see [[Preservation Policy]]). The disc image, BIOS, save states + memory cards (`*.sav`/`*.mcr`), EXE/DAT/RAW, `extracted/` assets, and local captures (screenshots `*.png`, frame/RAM dumps, `accessLog`/`execTrace` traces, `*.movie.json`) stay gitignored. Document **fixture hashes** instead ([[Fixtures Index]] · `tools/fixtures.sha256` for headline fixtures; [[Checksum Manifest]] · `repro_inputs.sha256` via `tools/verify_repro_inputs.py` for source media + core inputs) — the hash is committable; the media is not. `tests/test_no_forbidden_artifacts.py` fails the build if a forbidden artifact is ever tracked.
- **Guard the findings store (GAP-0002):** before/after a session that may call `findings.save`, run `python3 tools/check_findings_store.py` (semantic invariants — f13 is the sole CONFIRMED visible-floor answer, M7 anchors intact) **and** `python3 tools/verify_repro_inputs.py` (byte tamper-evidence). Both run in `run_safe_tests.py`, so an evidence-dropping overwrite fails the suite. To refresh the tracked backup from a fresh export, use the load-before-save guard: `check_findings_store.py snapshot` (after `findings.load`) → `check_findings_store.py guard-save NEW` (refuses a clobber unless byte-identical to the snapshot + invariants pass; `--force` overrides). Re-baseline the byte manifest intentionally with `verify_repro_inputs.py --write`.
- **Keep docs honest:** after an experiment, update the relevant index ([[Findings Index]], [[_Canonical Links]], [[Confirmed Knowledge]]) in the same pass. Doc debt is tracked as [[Blocker - Project documentation is stale and contradictory|B11]].
- **Update the control docs on any status change (the M8 rule):** when a Finding, Experiment, tool, or claim moves a gap's status, update **[[Roadmap]]** (§2 summary row + the owning milestone) **and** **[[Gap Audit]]** (the gap's index row + detail entry) in the same commit; update **[[Tools Catalog]]** when you add/remove/rename a `tools/*.py`; refresh **[[Risk Matrix]]**'s current-tier table when a blocker's real severity changes; register major new notes in **[[Project Index]]** + **[[_Canonical Links]]**. A status that lives in only one of these is itself a stale-doc bug — exactly the [[Gap Audit|GAP-0007]]/[[Gap Audit|GAP-0012]] failure mode. Use absolute (ISO) dates.

## Adding a note
Use the [[README]] naming patterns (`FUNC_<HEX>`, `Finding - …`, `MEM - … <ADDR>`, `API - …`, etc.) — keep basenames **unique** (Obsidian resolves links by basename). **Register the new basename in [[_Canonical Links]].** Link every Finding to its Functions/MEM/Experiments/Fixtures/APIs and its source doc.

## Where work is tracked
- **[[Roadmap]]** — milestones M0–M8, backlog, near-term plan, risk register.
- **[[Gap Audit]]** — the 43 stable gaps (GAP-0001…0043) with acceptance criteria.
- **[[Open Questions]]** — priority-sorted + grouped-by-subsystem questions.
- **[[Blockers]]** / [[Remediation Plan]] — the due-diligence catalog + execution log.
Pick work from the [[Roadmap]] backlog (P0→P3); record the GAP-ID you're closing.

## Reproducibility (commit only when asked)
Per repo policy, **commit or push only when the owner asks.** Stage your own changes; don't sweep up unrelated work-in-progress. The DuckStation fork is pinned in `tools/FORK_COMMIT.txt`; an off-machine remote / fork vendoring is the outstanding reproducibility step ([[Gap Audit|GAP-0001]]).

## See also
[[README]] · [[Preservation Policy]] · [[Roadmap]] · [[Gap Audit]] · [[Reproducibility Checklist]] · [[Playbooks]] · [[API - determinism]]
