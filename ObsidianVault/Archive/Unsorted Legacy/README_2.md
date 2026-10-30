---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/README.md
aliases:
  - "README"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/README.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Vault README & Conventions
type: meta
updated: 2026-06-21
tags: [meta, onboarding]
---

# ABL Reverse-Engineering Vault — README

This is an **Obsidian knowledge graph** for the *A Bug's Life* (PS1, serial **SCUS-94288**) reverse-engineering project. It is a *cross-referenced summary layer* over the source material — it does **not** replace the original docs. Start at **[[Home]]**.

> [!important] This vault summarizes; it does not own the truth.
> The authoritative sources are the original Markdown docs in `~/Downloads/ABL/docs/` and `~/Downloads/ABL/src_re_geometry/`, the decompiled C in `~/Downloads/ABL/src_re*/`, and the machine-readable findings store `~/Downloads/ABL/src_re_geometry/re_findings_backup.yaml`. Every note links back to its source. When in doubt, open the source.

## Onboarding for a future Claude session (read this first)
1. Open **[[Home]]** for the project state, then **[[Confirmed Knowledge]]** for the settled facts. To **contribute**, read **[[CONTRIBUTING]]** + the **[[Roadmap]]** (milestones M0–M8, backlog, evidence standards) and **[[Gap Audit]]**. Before committing or sharing anything, read **[[Preservation Policy]]** (what may/may not be committed: disc/BIOS/saves/extracted assets, and why).
2. To resume active work, read **[[Open Questions]]** (sorted by priority) and the latest geometry plan `src_re_geometry/geometry_g30_terrain_render_source_plan.md`.
3. Before any live experiment, read **`.claude/skills/duckstation-external-debugger/SKILL.md`** (the required live-debugger guide), **[[DuckStation API Index]]** and **[[Playbook - Create a deterministic experiment]]**. The live debugger has sharp edges (settle after `loadState` before `addWatch`; `findings.load` BEFORE `findings.save` or you overwrite) and is operator-gated until [[Gap Audit|GAP-0001]].
4. The project's persistent cross-session memory lives separately at `~/.claude/projects/-home-user-Downloads-ABL/memory/MEMORY.md`. This vault is the *expanded* form of that memory.

## Directory map
| Folder | Holds |
|--------|-------|
| `Findings/` | One note per confirmed/【in-progress】 discovery. The heart of the vault. |
| `Functions/` | `FUNC_<ADDR>` encyclopedia entries (one per important routine). |
| `Experiments/` | One note per build/test or live experiment — reproducible. |
| `Fixtures/` | Save-state fixtures (game state you can load to reproduce work). |
| `Save States/` | Index + raw catalog of every `.sav` on disk. |
| `DuckStation API/` | Capability map — one note per debugger feature. |
| `Memory Structures/` | RAM buffers, tables, structs, record layouts. |
| `Symbols/` | Flat symbol table (address → name → note). |
| `Hypotheses/` | Tracked hypotheses with status + evidence. |
| `Open Questions/` | Unresolved questions, gates, next steps. |
| `Confirmed Knowledge/` | The "what we know for sure" digest. |
| `Systems / Collision / Rendering / Geometry / Camera / Physics / Assets` | Topic hubs (MOCs) that gather related findings. |
| `Playbooks/` | Reusable RE workflows wired to the DuckStation API. |
| `Indexes/` | Auto-style index notes (Functions/Findings/Experiments/Fixtures/API/Symbols). |

## Naming conventions (keep basenames UNIQUE — Obsidian resolves wiki-links by basename)
| Kind | Pattern | Example |
|------|---------|---------|
| Function | `FUNC_<UPPERHEX>` (no `0x`) | `[[FUNC_800172DC]]` |
| Finding | `Finding - <short title>` | `[[Finding - Visible terrain renderer]]` |
| Experiment | `Experiment - <label>` | `[[Experiment - G28 Candidate A floor Y]]` |
| Fixture | `Fixture - <name>` | `[[Fixture - g30 openground]]` |
| API feature | `API - <method>` | `[[API - execTrace]]` |
| Memory struct | `MEM - <name> <ADDR>` | `[[MEM - Terrain vertex buffer 8012C1D0]]` |
| Hypothesis | `HYP - <slug>` | `[[HYP - visual equals collision]]` |
| Playbook | `Playbook - <task>` | `[[Playbook - Trace rendering ownership]]` |
| Symbol | listed in `[[Symbols Index]]` | — |

## Linking rules
- Every **Finding** links to: its **Functions**, **Memory Structures**, **Experiments**, **Fixtures/Save States**, **DuckStation APIs** used, and the **source doc** (relative path under `~/Downloads/ABL`).
- Every **Function** backlinks to the Findings/Experiments that touch it.
- Every **Experiment** names the **Fixture/save state**, **APIs**, exact procedure, result, and **linked Findings**.
- Every **Hypothesis** links its supporting + contradicting evidence (Findings/Experiments).
- Use Obsidian **backlinks** (bottom of each note) to navigate — most notes are reachable from any other in ≤2 hops.

## Confidence vocabulary
`CONFIRMED` (built+observed or multi-evidence) · `LIKELY` · `INVESTIGATING` · `UNKNOWN` · `DISPROVEN` / `RETRACTED`.

> [!tip] Maintenance: the full note-name registry is **[[_Canonical Links]]** — add a note's name there when you create it, so wiki-links keep resolving.

## Source-of-truth pointers
- Index/summary: `ABL_RE_NOTES.md`
- Findings store (YAML, machine-readable): `src_re_geometry/re_findings_backup.yaml`
- Geometry arc: `src_re_geometry/geometry_g*.md` (G5.5 → G30)
- Experiment history (incl. dead ends): `docs/EXPERIMENT_LOG.md`
- DuckStation control reference: `~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md` + `~/duckstation/docs/external-debugger*.md`
- Python debugger client: `~/duckstation/scripts/debugger-client/`
