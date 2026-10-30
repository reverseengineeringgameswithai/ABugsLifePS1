---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80025084.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80025084.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80025084_oriented_containment_-_range_test.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80025084 — oriented containment / range test
type: function
address: 0x80025084
confidence: CONFIRMED
tags: [function, collision, actor]
---
# FUNC_80025084 — oriented containment / range test

> An oriented bounding/containment test on actor/object data. A G5/G29 wall-or-ledge collision candidate — notably it reads **no parser geometry**.

| Field | Value |
|-------|-------|
| Address | 0x80025084 |
| Source file | `geometry_collision_consumers.c` |
| Confidence | CONFIRMED head disasm + role |

## Purpose
**Wall/ledge collision — oriented-plane containment with a collision radius.** CONFIRMED at runtime (2026-06-18): firing it required reaching a wall (the `openfloor` fence) — **108 hits while Flik pushed into the fence, 0 on open ground**. Per wall edge (record via `[a1+0]` → object table `0x800a6300`):
- computes the **3D dot product** `dist = Σ_i ((player_pos[i] << 5) − edge_point[i]) · normal[i]`, where player pos = `[a1+0x80]→[+0/+4/+8]`, edge point = `[a2+0/+4/+8]`, edge normals = `0x8009?fbc / 0xfbe / 0xfc0` (the `0x80090fb0` rotation/normal block);
- normalizes `dist >>= 17` (normals are ~17-bit fixed point);
- tests `dist > −radius` (radius = `int16 [a1+0x6a]`) ⇒ player penetrating the wall plane → resolve (push back / slide along the normal).
Reads NO parser geometry handle — it is the **wall/ledge side** of collision, distinct from the floor path ([[FUNC_800322A0]] point-in-face) and the no-contact free-move branch (`0x80035210`).

**Slide resolution (`0x80025170`+):** a *second* dot product against a **tangent** vector (`0x80090fb0/fb2/fb4`) gives `tangential = dot(delta, tangent) >> 17` = position *along* the wall — so the wall is an oriented **segment** (normal + tangent basis). Collision requires within `radius` perpendicular **and** within the segment span tangentially; resolution **corrects the normal component (stop) and preserves the tangential (slide along the wall)**. The caller `fcn.8004d224` iterates this over walls (the slide/re-test loop).

> **Fixture:** `SCUS-94288_fence_wall.sav` — Flik at the openfloor fence; holding ↑ re-fires this function. Saved 2026-06-18.

## Arguments / Returns
`a1` = actor struct (`0x800a0a64`). Returns containment/range result.

## Calls (callees)
- matrix/transform helpers (libgte).

## Called by (callers)
- exactly one: `fcn.8004d224` @ `0x8004d3bc`.

## Globals & structures touched
- actor `0x800a0a64` · object table `0x800a6300` · rotation matrix `0x80090fb0`.

## Evidence & confidence notes
Surfaced in the G5 collision-consumer search; because it holds no geometry handle it supported [[Finding - No static collision consumer]]. Floor collision turned out to live elsewhere (sector path, [[FUNC_8003633C]]); this is the wall/object-side candidate.

## Related
- Findings: [[Finding - No static collision consumer]] · [[Finding - Visual is not collision]]
- Functions: [[FUNC_8003633C]] (floor path, separate)
- Source docs: `src_re_geometry/geometry_g29_collision_source_plan.md`, `geometry_notes.md` (G5)
