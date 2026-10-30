---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Project Index.md
aliases:
  - "Project Index"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Project Index.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Project Index
type: index
updated: 2026-07-02
tags: [index, navigation, control-document]
---

# 🧭 Project Index — navigation hub

> The single entry point to the project's **control documents**, knowledge MOCs, source material, and tools. Complements **[[Home]]** (the discovery dashboard / "what's exciting") — this note is the **map** ("where is everything"). New here? [[README]] → [[Home]] → [[Roadmap]].

## Control documents (start here)
| Doc | What it is |
|---|---|
| **[[Roadmap]]** | Top-level control document — status, milestones M0–M8, backlog, risk register, 2-week plan. |
| **[[Gap Audit]]** | The 43 stable gaps (GAP-0001…GAP-0043) with evidence, priority, and acceptance criteria. |
| **[[Gap Priorities]]** | Priority-grouped (P0–P3) view of the open gap backlog + closed-with-residual items; derived from [[Gap Audit]]. |
| **[[Open Questions]]** | Priority-sorted unresolved questions + the experiment that resolves each (grouped by subsystem). |
| **[[Glossary]]** | Project-specific + general RE/PS1 terms. |
| **[[Milestone 0 Completion]]** | M0 execution record — hygiene & reproducibility (done 2026-06-20). |
| **[[Preservation Policy]]** · **[[CONTRIBUTING]]** | What may/may not be shared · how to do work here. |
| **[[Blockers]]** | The B1–B20 due-diligence catalog (full-RE yardstick). |
| **[[Risk Matrix]]** · **[[Assumptions Register]]** · **[[Remediation Plan]]** · **[[Reproducibility Checklist]]** | Risk/assumption/execution views over the blockers. |
| **[[Confirmed Knowledge]]** · **[[Hypotheses]]** | Settled facts · tracked/disproven beliefs. |

## Knowledge MOCs (topic hubs)
- **Systems & engine:** [[Systems]] · [[Rendering]] · [[Collision]] · [[Geometry]] · [[Physics]] · [[Camera]] · [[Geometry pipeline]] · [[LEVEL.DAT object pipeline]] · [[Campaign Level Coverage Matrix]] · [[Editor Visual Fidelity Baseline]] · [[Level Goal and Exit Trigger Matrix]] · [[Menu and HUD structure]] · [[Seed planting system]] · [[Enemy relocation method]]
- **Indexes:** [[Findings Index]] · [[Functions Index]] · [[Symbols Index]] · [[Experiments Index]] · [[Fixtures Index]] · [[DuckStation API Index]] · [[Save States Index]] · [[_Canonical Links]]

## Setup, toolchain & reproducibility
- **Vault:** [[README]] (conventions) · [[CONTRIBUTING]] · [[Preservation Policy]] · [[Toolchain Census]] (versions/test classes) · [[DuckStation Fork Reproducibility]] (fork/API evidence chain) · [[Tools Catalog]] (Python tools + GUI editor) · [[ABL Level Editor]] · [[ABL 3D Level Editor Roadmap]]
- **Live debugger (operator-gated, GAP-0001):** `.claude/skills/duckstation-external-debugger/SKILL.md` — the required guide for safely driving the local DuckStation external-debugger fork (isolated instance, fixture identity, watches, evidence capture); local tooling, not committed. Spec: `~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md`.
- **Asset extraction:** [[Asset - Asset extraction recipe]] (regenerating `extracted/`)
- **Provenance/build:** [[Finding - Build toolchain and PROPACK provenance]] · [[Finding - Disc rebuild is byte-exact]] · [[Asset - Disc image and rebuild]]
- **Source docs (outside the vault, under `~/Downloads/ABL/`):**
  - `docs/TOOLING.md` · `docs/TOOLING_OPTION_C_PLAN.md` + `PHASE0_1…PHASE6_REPORT.md` — tool/build workflow
  - `docs/COORDINATE_MODDING.md` — pickup coordinate modding
  - `tools/FORK_COMMIT.txt` — pinned DuckStation fork hash (`296955321`)
  - `~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md` — the custom debugger API spec (out-of-repo; GAP-0001)

## Binary / executable analysis
- **M3 baseline (complete for modding-grade):** [[MEM - Global memory map]] · [[Symbol Map Baseline]] (`symbols/re_symbols.sym`) · [[Symbol Import Round Trip]] · [[Executable and Overlays]] · [[Decompilation Pilot]]
- **Indexes:** [[Symbols Index]] · [[Functions Index]] (28 `FUNC_*`) · [[Memory Structures]]
- **Key functions:** [[FUNC_8001CDC0]] (DAT parser) · [[FUNC_80010000]] (mesh emitter) · [[FUNC_8003633C]] (player-Y writer) · [[FUNC_80046B20]] (player spawn/placement) · [[FUNC_800345CC]] (collision resolve) · [[FUNC_8001A1DC]] (LEVEL.RAW codec) · [[FUNC_800172DC]] (mesh renderer) · [[FUNC_8005EC94]] (`.ANM` player)
- **Source docs:** `docs/EXECUTABLE_AND_OVERLAYS.md` (image/overlays/memory) · `docs/DECOMPILATION_PLAN.md` · `src_re/*.c` (reconstructed C) · `src_re/re_types.h` (structs)
- **Related gaps:** GAP-0018 (symbol baseline: Verified) · GAP-0019 (memory map: Verified) · GAP-0020 (M3 overlay baseline complete; deeper RE In Progress) · GAP-0021 (behavioral pilot finalized; compile/diff Deferred/In Progress)

## Assets & file formats
- **Notes:** [[Asset - LEVEL.DAT]] · [[Asset - LEVEL.RAW]] · [[Asset - LEVEL.BIN and overlays]] · [[Asset - Character and plant models]] · [[Asset - Disc image and rebuild]] · [[Asset - Disc file map]] · [[Checksum Manifest]] (provenance)
- **M4 file-format baseline:** [[Asset - LEVEL.RAW Chunk Role Table]] (69/69 classified) · [[Asset - Chunk 34 Master Mesh]] · [[Asset - PROPACK Rebuild Strategy]] · [[Asset - LBA Shift Rebuild Proof]] · [[Asset - ALL ANM Format Grammar]] · [[Asset - GFX CLUT Exactness]] · [[Asset Extraction Pipeline]]
- **Format findings:** [[Finding - LEVEL.RAW is compressed]] (PROPACK codec) · [[MEM - LEVEL.RAW chunk inventory]] (69 chunks) · [[Finding - Chunk 34 master mesh structure]] · [[Finding - Character ALL model format]] · [[Finding - VAB sound bank format]] · [[Finding - Region-A texture format decoded]] · [[Finding - Two parser source-record formats]] · [[Finding - LEVEL.DAT records are object paths]]
- **Source docs:** `docs/DAT_FORMAT_AND_RELOCATION.md` · `docs/LEVEL01_TYPE3F_MAP.md` · `docs/LEVEL_OBJECT_PIPELINE.md` · `REBUILD/abl.xml` (disc file table) · `src_re_geometry/re_findings_backup.yaml` (findings store)
- **Related gaps:** GAP-0022/0023 (chunk roles) · GAP-0024/0025 (compressed rebuild) · GAP-0026/0027 (model/CLUT residuals)

## Game systems (coverage)
- **SOLID:** rendering ([[Rendering]]) · collision ([[Collision]]) · physics ([[Physics]]) · animation ([[Finding - Character ALL model format]]) · level loading ([[Systems]]) · pickups ([[LEVEL.DAT object pipeline]]) · text=image-baked ([[Blocker - Offline texture and font extraction is absent|B20]])
- **PARTIAL:** boot/main loop ([[Systems]]) · player ([[MEM - Player state 800A6500]]) · camera ([[Camera]], GAP-0028) · menus/save ([[Menu and HUD structure]], GAP-0036) · audio/FMV (extract-only, GAP-0031/0032) · OT/packets (GAP-0030)
- **STUB / ABSENT:** scripting/event system (GAP-0033) · AI/PATH nav-graph (GAP-0034) · performance model
- **M5 core engine baseline:** [[Core - Camera and Projection]] (GAP-0028) · [[Core - Rendering OT and GPU Packets]] (GAP-0030) · [[Core - CD Streaming and Caching]] (GAP-0029) · [[Core - Runtime Audio Path]] (GAP-0031) · [[Core - FMV and MDEC Playback]] (GAP-0032)
- **M6 gameplay baseline (started):** [[Gameplay Systems Baseline]] · [[Gameplay - Events and Triggers]] (GAP-0033 — dispatch + cursor model; [[Experiment - Event Sequencer Trace]]) · [[Gameplay - DAT Event Stream]] (GAP-0033 — cursor seed found: resident table `0x80017DB4` via [[FUNC_8005B714]]; overlay-seed refuted, LEVEL.DAT-source corrected) · [[Gameplay - Resident Event Stream]] (GAP-0033 — `0x80017DB4` decoded: resident PRNG/noise table; consumers classified) · [[Gameplay - Resident Noise and Ctor 0x71]] (GAP-0033 — ctor-0x71 = contact/proximity entity, not rendered; noise lane closed as a side-branch) · [[MEM - Event System Globals]] · [[Gameplay - Warp and Level Transition]] (GAP-0035 — orchestrator [[FUNC_8005222C]] + callees decoded; warp = reload+reseed+fade+handler-swap; **warp LANDING confirmed**) · [[Gameplay - Player Spawn and Placement]] (GAP-0035 — player placement = 3-layer checkpoint/respawn, separate from warp) · [[Gameplay - Initial Player Spawn]] (GAP-0035 — load-spawn **RUNTIME-CONFIRMED**: [[FUNC_80046B20]]`(player, scene_id)` ← resident EXE table `0x80077314`; LEVEL.DAT/LEVEL.BIN refuted → [[Experiment - Initial spawn write-watch]]) · [[Experiment - Warp landing diversion]] (GAP-0035 — non-LEVEL01 warp landings reuse the same fn/table, `index==scene_id`, clean) · [[Experiment - In-game warp trigger]] (GAP-0035 — orchestrator [[FUNC_8005222C]] shell-only; gameplay↔shell gate `0x8008224e`; mid-gameplay scene_id crash explained; **native trigger LEVER captured** = transition-state `0x800823a0`=6 → scene-init; clean landing = overlay/GAP-0033) · [[Gameplay - Input and Movement]] (GAP-0037 lane)

## Scripts & tools
- **Catalog:** [[Tools Catalog]] (tracked/untracked inventory) · environment/version evidence in [[Toolchain Census]] · workflow details in `docs/TOOLING.md`
- **Trusted engines:** `tools/dat_reloc.py` (relocation-aware DAT) · `tools/decode_level_raw.py` + `recompress_level_raw.py` (LEVEL.RAW codec) · `tools/level_raw_chunk_manifest.py` (chunk-role metadata → `level_raw_chunk_roles.json`) · `tools/exe_read.py` (static EXE table/dispatch reader → address metadata) · `tools/rebuild_with_patched_dat.py` (mkpsxiso rebuild) · `tools/abl_dbg.py` (debugger driver)
- **Editor:** `level_editor/pyside_level_editor.py` (primary; pickup planner + 3D scene view) · `level_editor/AblLevelEditor.java` (fallback prototype)
- **Safe tests:** `python3 tools/run_safe_tests.py` → codec oracle/synthetic round-trip, manifest, syntax/import, path portability, symbol-map format, and DuckStation-CSV/r2 symbol round-trips; `.github/workflows/safe-tests.yml` runs them without copyrighted/local-only inputs.
- **Isolated tests:** `tools/regress_*.py`, editor/GPU tests, and DuckStation live scripts require local inputs/environments; see [[Toolchain Census]] (GAP-0017/GAP-0040).

## Evidence logs & history
- `docs/EXPERIMENT_LOG.md` — full experiment history incl. dead ends (92 KB)
- `docs/GEOMETRY_RE_PLAN.md` — the phased geometry plan (164 KB) · `src_re_geometry/geometry_g*.md` — the G1–G30 arc
- [[Experiments Index]] — vault experiment notes (reproducible) · [[Hypotheses]] — the belief graveyard
- `ABL_RE_NOTES.md` (repo root) — the original canonical index · persistent memory: `~/.claude/projects/-home-user-Downloads-ABL/memory/MEMORY.md`

## Maintenance
When adding a note, register it in [[_Canonical Links]]. Control docs ([[Roadmap]], [[Gap Audit]]) carry `Last audited` / `Next review` — refresh each cycle. Keep **one** `CONFIRMED` answer per question ([[Roadmap]] M8).

## See also
[[Home]] · [[Roadmap]] · [[Gap Audit]] · [[Open Questions]] · [[Glossary]] · [[README]]
