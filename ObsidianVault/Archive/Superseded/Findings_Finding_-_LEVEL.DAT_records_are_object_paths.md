---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - LEVEL.DAT records are object paths.md
aliases:
  - "Finding - LEVEL.DAT records are object paths"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - LEVEL.DAT records are object paths.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_LEVEL.DAT_records_are_object_paths.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - LEVEL.DAT records are object paths
type: finding
confidence: CONFIRMED
tags: [finding, leveldat, paths, format, b10]
updated: 2026-06-18
---

# Finding — LEVEL.DAT top-level records 1–10 are object PATHS (waypoint arrays)

> The 10 previously-undecoded LEVEL.DAT top-level records — the `0x01`/`0x0b`/`0x0c`/`0x0d` fixed 3×s32 records and the packed negative records `-2..-7` — are **path / waypoint data** for moving objects. Identifies the role of the undecoded half of LEVEL.DAT → [[Blocker - LEVEL.DAT non-pickup records are undecoded|B10]] (resolves the G1 "role UNKNOWN").

**Confidence:** CONFIRMED for rec1 (live consumer traced); LIKELY for rec2–10 (identical format) · **Established:** 2026-06-18 (B10, live API)

## How it was found
- rec1 (type `0x01`, 104 entries of 3×s32) at runtime `0x80160c64` holds a **smoothly-varying point sequence** (X 4978→4596→4214; Y −1256→−1411→−1563) = a spline/path, not scattered positions.
- 0 reads in idle play; a **read-watch while walking Flik forward** (which spawns a moving object here) caught the consumer at **`0x8004c400`** reading rec1 entries 44/45.

## The consumer — path follower @ `0x8004c400`
> **2026-06-21:** `0x8004c400` is the body of **opcode 9 of the per-object "object actor" bytecode VM [[FUNC_8004C13C]]** (table `0x8001b2f4[9]=0x8004c46c`) — this live read-watch is the VM running opcode 9, which reads a path **waypoint** (`object[+0x5e]` index, stride 0xc, `<<5` file→world) into the object's move-**target** `object[+0x34/38/3c]`. So these LEVEL.DAT path records are the **waypoint DATA** opcode 9 consumes. **The VM PROGRAM (opcode stream) is RESIDENT** (EXE program table `0x80077af8`), *not* LEVEL.DAT — only this path/waypoint data and the object spawn/selection are on-disc. ⇒ edit a mover's *path* here (LEVEL.DAT); edit its *behaviour program* via EXE patch. Full model → [[Event and scripting system]] (the GAP-0033 interpreter).

For a moving-object struct `s0` (path base in `a1`):
```
idx = s0[+0x5e]                 ; current waypoint index (s16)
e   = a1 + idx*0xc              ; entry size 0xc = 3×s32  (a1 = rec1 base 0x80160c64)
s0[+0x30] = e[+0] << 5          ; X = path[idx].x * 32
s0[+0x34] = e[+4] << 5          ; Y = path[idx].y * 32
s0[+0x38] = e[+8] << 5          ; Z = path[idx].z * 32
```
i.e. **the object's world position (`+0x30/34/38`) is set to `path[idx] << 5`** (the standard file→world `<<5`); the object advances `idx` to travel the path. (`s0+0x3c` is a per-segment accumulator updated just before.)

## Record format (role CONFIRMED; byte format per G1 §5)
- **rec1 `0x01` (104) and rec2–4 `0x0b`/`0x0c`/`0x0d` (16 each):** arrays of **3×s32 world waypoints** (X,Y,Z, pre-`<<5`) — different path groups (rec1 = the long 104-point path; 0x0b/0c/0d = 16-point paths).
- **rec5–10 negative (`-2..-7`):** a 3×s32 **start point** + a **delta-encoded byte stream** (G1 §5) → LIKELY the same paths in compact delta form. (Exact delta widths = remaining follow-up.)

## Implications (modding)
- The undecoded half of LEVEL.DAT is **object-movement paths** — unlocks editing **moving platforms / enemy patrols / scripted movers**: change a waypoint's 3×s32 → the object's track moves. The per-entry lever is the same `<<5` file→world convention as pickups.
- Distinct from the `PAD\PATH*.BIN` AI-nav files (→ [[Blocker - Collision internals are partly undecoded|B18]]); these are in-DAT object paths.

## Related
[[Asset - LEVEL.DAT]] · [[LEVEL.DAT object pipeline]] · [[MEM - DAT runtime memory map]] · [[Blocker - LEVEL.DAT non-pickup records are undecoded]]
- Source: live read-watch (consumer `0x8004c400`); `src_re_geometry/level01_dat_geometry_inventory.md` §5
