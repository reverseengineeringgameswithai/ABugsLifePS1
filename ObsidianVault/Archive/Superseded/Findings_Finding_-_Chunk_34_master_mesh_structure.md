---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Chunk 34 master mesh structure.md
aliases:
  - "Finding - Chunk 34 master mesh structure"
migration_action: split
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Chunk 34 master mesh structure.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Chunk_34_master_mesh_structure.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Chunk 34 master mesh structure
type: finding
confidence: PARTIAL (structure mapped, decode incomplete)
gstep: editor-spawn-ground
tags: [finding, geometry, levelraw, chunk34, terrain, leveleditor]
---

# Finding — LEVEL.RAW chunk 34 (master ground mesh) structure

> [!warning] **SUPERSEDED claim (corrected M7, 2026-06-21 — [[Gap Audit|GAP-0011]] Verified):** this note originally concluded *"the spawn ground is chunk 34/35, not DAT."* That is **refuted for the visible render.** A live pick+trace at Flik's exact spawn (file Z **15403** — the very Z cited below) shows the visible floor packet is emitted by **`fcn.80010000` reading LEVEL.DAT** (20/20 emitter calls source DAT, span file `0x15dec..0x2f59c` incl. Candidate A `0x188cc`); **`fcn.800172dc` (chunk-35) ran 0 times**. ⇒ **visible spawn floor = LEVEL.DAT.** See [[Experiment - Spawn-floor render source]] (`tools/trace_spawn_floor.py`). chunk-34/35 = the **occluded / collision-adjacent** static-mesh layer — *not* the visible spawn renderer. The structural analysis below (chunk-34 layout + the model→world transform blocker, [[Gap Audit|GAP-0023]]) **stands** and remains the open work.

> The ground Flik stands on at spawn is rendered from **LEVEL.DAT** (`fcn.80010000`, f13); chunk 34 (master mesh) + chunk 35 (near strip) form a separate, **occluded / collision-adjacent** layer. Chunk 34's top-level structure is mapped; full decode + world placement is the remaining work ([[Gap Audit|GAP-0023]]).

**Confidence:** PARTIAL *(chunk-34 structure mapped; decode incomplete)* · **Established:** 2026-06-20 (level-editor spawn-ground effort) · **Visible-floor attribution SUPERSEDED 2026-06-21 (M7 — visible spawn floor = LEVEL.DAT; see banner)**

## Why this matters (corrected)
The **level editor** renders only a *subset* of the DAT `fcn.80010000` payloads (aligned via the empirical Y offset), and that subset **does not cover the spawn area**: 0 DAT terrain verts within 2000u of Flik (6159,15403) or the grain (5525,12996) in the editor's loaded set; the editor's DAT terrain Z maxes at 9774. The original note read this as *"so the spawn ground must come from chunk 34/35."* **M7 refuted that inference for the visible render:** at runtime the game emits the spawn floor from DAT meshes spanning file `0x15dec..0x2f59c` (Candidate A `0x188cc` is inside that span) — i.e. the "DAT doesn't reach Z 15403" bound measured **one static payload**, not the full DAT floor stratum the runtime draws. So the editor's *coverage gap* is an **editor data-loading issue** (which DAT payloads it loads + the model→world transform), **not** evidence that chunk-34/35 renders the spawn floor. The genuine remaining work is the chunk-34 decode + model→world transform below ([[Gap Audit|GAP-0023]]).

## Chunk 34 layout (mapped)
- `+0x00` u32 `0x101` (subtype "01 01"). `+0x08` u16 hi = **40** (sub-mesh count).
- `+0x2c` onward: a **sub-mesh offset table** (40 u32, increasing: 0x1910, 0x3180, 0x42e2, 0x4f3a, 0x5b92, …; some 0 = empty slots).
- `+0x10/14/18`, `+0x24/28`: pointers to **shared pools** near the end (0x29998, 0x2a368, 0x2adc8, 0x2b828, 0x2bffa → EOF 0x2c846).
- **Pools** decode as s16 triples: p1 (0x29998) and p3 (0x2adc8) are clean **model-space vertex pools** (coords ±1000, centered on origin); p2/p4/p5 mix in `4096`(=1.0)/`4620` values = **per-sub-mesh transform matrices** (3×3 fixed-point). `0xfffd`(-3) is padding/fill.
- Each sub-mesh descriptor (e.g. 0x1910) holds vertex byte-offset lists (stride 6 = s16 triple) + faces, like a finer-grained `fcn.80010000`.

## The blocker (remaining work — multi-session)
The vertices are **model-space, centered near origin** (±1000). Placing them at Flik's spawn needs the **runtime model→world transform**, which is NOT in the chunk — it is applied at draw time by the terrain renderer (GTE). Getting it requires: capture the GTE model→view during the chunk-34/35 draw (`execTrace` near the terrain RTPT), establish the camera (world→view) from a reference, derive model→world, then map runtime→editor — which is tangled in the unresolved **Y-bias** between the runtime world (Flik 0x800A6500) and the editor placement frame (`scene3d.WORLD_PAYLOAD_Y_OFFSET` is the empirical patch for the DAT terrain; the true relation is undecoded).

## Status
- ✅ Editor spawn camera matches `_1.sav` (3rd-person, behind Flik facing the 3 grain).
- ✅ DAT terrain aligned to its objects (Y offset).
- ❌ **SUPERSEDED:** "spawn ground = chunk 34/35" — visible spawn floor is **LEVEL.DAT** (M7, [[Gap Audit|GAP-0011]] Verified; [[Experiment - Spawn-floor render source]]).
- ⏳ Chunk-34 structure mapped; sub-mesh decode + runtime model→world placement = genuine multi-session RE ([[Gap Audit|GAP-0023]]).
- ⏳ Editor coverage gap (spawn area shows no loaded ground) traced to which DAT payloads the editor loads + the model→world transform — an **editor** issue, not chunk-34/35 attribution.

## Related
[[Experiment - Spawn-floor render source]] (M7 — visible spawn floor = LEVEL.DAT) · [[Finding - Candidate A is DAT-backed visual terrain]] · [[FUNC_80010000]] · [[Finding - DAT record holds decor instance world position]] · [[Finding - Region-A texture format decoded]] · [[MEM - LEVEL.RAW chunk inventory]] · [[MEM - Terrain vertex buffer 8012C1D0]] (chunk 35) · [[ABL 3D Level Editor Roadmap]]
