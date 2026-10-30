---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Correlate rendering and collision.md
aliases:
  - "Playbook - Correlate rendering and collision"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Correlate rendering and collision.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Correlate rendering and collision
type: playbook
tags: [playbook, geometry, collision, rendering, method]
---

# Playbook — Correlate rendering and collision

> The hardest ABL trick: make a *visible* terrain change that Flik also physically interacts with. Because **visual ≠ collision** ([[Finding - Visual is not collision]]), you must edit two independent levers in a matched way.

> [!warning] **M7 correction (2026-06-21):** the **visible** floor lever is **LEVEL.DAT / [[FUNC_80010000]]** (Candidate A) — the chunk-35 buffer renders **occluded** ([[Gap Audit|GAP-0011]]). Steps 2–3 below were written to target the chunk-35 buffer (`0x80017464` rtpt / `0x8012c1d0`); for a *visible* change, lower the **DAT payload** instead. The collision lever (chunk 32) is unchanged.

## When to use
Goal experiments like "make Flik fall into a visible pit."

## The two levers (must be matched)
| Layer | Lever | Note |
|-------|-------|------|
| Visual | [[MEM - fcn.80010000 mesh payload]] Candidate A (LEVEL.DAT — the **visible** floor, f13) **and/or** the [[MEM - Terrain vertex buffer 8012C1D0]] chunk-35 quads (*occluded — M7; editing these alone is not visible*) | [[Finding - Candidate A is DAT-backed visual terrain]] / [[Finding - Visible terrain renderer]] |
| Collision | [[MEM - Collision sector table 800A7E48]] sector origin Y (local = sec186) | [[Finding - Collision lever sector186]] |

## Steps
1. Pick a flat open spot ([[Fixture - g30 openground]] / [[Fixture - g30 openfloor]]).
2. **Calibrate model↔screen** with [[API - execTrace]] at the terrain renderer's rtpt (`0x80017464`) — capture per-quad SXY + the buffer pointer to know *which* quads project to *which* screen region.
3. **Lower the visual quads** inside a screen box via [[API - scatterWrite]]; verify with [[API - gpu.readVramRect]] + [[API - visual diff]].
4. **Lower the matching collision sector(s)** (sec186 + adjacent — a single sector gets clamped by neighbors).
5. **Test physically:** scripted jump ([[API - controller input]]), watch player Y land on the lowered floor ([[API - addWatch]] / [[API - frame capture]]).

## Why it's currently rendering-limited
Near ground clips off the bottom (512×224), the camera follows Flik in Y, and the texture is uniform/gouraud, so a *uniform* matched lower is invisible. The terrain buffer is strip-ordered, not spatial. A dramatic photogenic pit is **P1 open** — see [[Open Questions]] and [[Finding - Localized terrain edit]].

## Related
[[Geometry pipeline]] · [[Playbook - Trace rendering ownership]] · [[Playbook - Trace collision resolution]] · [[Experiment - G30 localized terrain edit]] · [[Experiment - G29 collision lever validation]]
