---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Home.md
aliases:
  - "Home"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Home.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Home
type: dashboard
updated: 2026-06-21
tags: [dashboard, home]
---

# 🐜 A Bug's Life — RE Knowledge Vault

> Reverse-engineering of *Disney•Pixar A Bug's Life* (PS1, **SCUS-94288**) — lawful preservation/educational analysis of an owned disc. This vault is the cross-linked knowledge graph over the project. New here? Read **[[README]]** for conventions, then this page.

## Project at a glance
The project reverse-engineers how the game sources, renders, and collides level **geometry**, and how level **objects/pickups** are stored — to make the game *moddable* (move/add pickups, deform terrain, recolor the sky) and to drive experiments through a custom **DuckStation external debugger**. Two parallel tracks:
- **Pickup/DAT track** — type-0x3f object placement in `LEVEL.DAT`; coordinate modding + true entry injection. ✅ shipped in-game.
- **Geometry track (G1→G30)** — the visual vs. collision floor question, answered: **they are different files**. ✅ confirmed.

## ⭐ Major discoveries
- **[[Finding - Visual is not collision]]** — the visible floor (LEVEL.DAT via `fcn.80010000`) and the collision floor (LEVEL.RAW chunk 32) are independent layers (the LEVEL.RAW chunk-35 terrain mesh is a third, *occluded* layer). *The* central result.
- **[[Finding - Candidate A is DAT-backed visual terrain]]** — a directly-editable DAT mesh payload that deforms the visible floor (G28, operator-tested).
- **[[Finding - Collision sector table]]** + **[[Finding - Player Y writer FUNC_3633C]]** — the full disk→player-Y collision chain (G29).
- **[[Finding - Visible terrain renderer]]** — `fcn.800172dc` is a **shared mesh renderer**; in the 7-scene neutralize its terrain output is **occluded (~0 visible px)** and the **visible floor = LEVEL.DAT / [[FUNC_80010000]]** (f13). **Visible spawn floor = LEVEL.DAT confirmed (M7);** chunk-34/35 = occluded / collision-adjacent — [[Gap Audit|GAP-0011]] **Resolved** (G30 → M7).
- **[[Finding - Sky is a GP0 background fill]]** + **[[Finding - GPU primitive injection]]** — sky is a flat fill; turned into a starry night by injecting GPU primitives.
- **[[Finding - Relocation-aware DAT append]]** — new objects can be added; the old "black screen" was stale baked offsets.
- **[[Seed planting system]]** — the plantable seeds are a *separate* system from the type-0x3f pickups; mapped runtime (live-move handle + rooted/grown flags), traced to **LEVEL.RAW chunk 31**.
- **[[Finding - LEVEL.RAW is compressed|LEVEL.RAW codec SOLVED]]** — byte-exact decompressor **and** working recompressor (`tools/decode_level_raw.py` / `recompress_level_raw.py`). Unlocks permanent disc edits of terrain/collision/seeds. *This was the long-standing gate.*

## 🔬 Active investigations
- **[[ABL Level Editor]]** — standalone Java desktop GUI scaffold exists for type-`0x3f` pickup/DAT placement editing; seed-table and terrain/collision layers remain future work.
- **[[Seed planting system|GUI seed level-editor]]** — move/add seeds in a level editor. **Codec gate now CLEARED** (LEVEL.RAW decompress+recompress done); next is the seed-table parser/editor layer on the decompressed data.
- **[[G30 - Terrain render source]]** — localized, photogenic terrain pit (rendering-limited; needs the GTE-trace/frame-diff harness).
- See the full priority-sorted list in **[[Open Questions]]**.

## 🏆 Recent achievements
- Initial standalone [[ABL Level Editor]] desktop scaffold (`level_editor/AblLevelEditor.java`, launched by `level_editor/run_level_editor.sh`) for read-only type-`0x3f` inspection and placement-spec export.
- G28→G30 closed the visual-vs-collision question and found both render + collision sources.
- Starry-night GPU injection ([[Fixture - night starry]]).
- A live experiment-harness API (accessLog / execTrace / transferLog / gp0Trace / experiment.run / findings store) — see **[[DuckStation API Index]]**.

## 🧭 Navigate
| Section | Entry point |
|---------|-------------|
| **Plan & control** | **[[Roadmap]]** · [[Gap Audit]] · [[Project Index]] · [[Preservation Policy]] · [[Glossary]] |
| Settled facts | [[Confirmed Knowledge]] |
| What's unknown | [[Open Questions]] · [[Hypotheses]] |
| Risks & readiness | [[Blockers]] · [[Risk Matrix]] · [[Assumptions Register]] |
| Discoveries | [[Findings Index]] |
| Code | [[Functions Index]] · [[Symbols Index]] |
| RAM/structs | [[Memory Structures]] |
| Experiments | [[Experiments Index]] |
| Reproduce state | [[Fixtures]] · [[Fixtures Index]] · [[Save States Index]] |
| Debugger | [[DuckStation API Index]] |
| Files/assets | [[Assets]] · [[Tools Catalog]] |
| How-to | [[Playbooks]] |
| Topic hubs | [[Systems]] · [[Rendering]] · [[Collision]] · [[Geometry]] · [[Physics]] · [[Camera]] |

## 🔗 High-value references (source material)
- `ABL_RE_NOTES.md` — canonical index · `src_re_geometry/re_findings_backup.yaml` — machine-readable findings store
- `src_re_geometry/geometry_g30_terrain_render_source_plan.md` — latest geometry plan
- `docs/EXPERIMENT_LOG.md` — full history incl. dead ends · `docs/GEOMETRY_RE_PLAN.md` — phased plan
- `~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md` + `~/duckstation/scripts/debugger-client/` — debugger API & client
- Persistent cross-session memory: `~/.claude/projects/-home-user-Downloads-ABL/memory/MEMORY.md`
