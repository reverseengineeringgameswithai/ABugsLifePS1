---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Level-warp mechanism.md
aliases:
  - "Finding - Level-warp mechanism"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Level-warp mechanism.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Level-warp_mechanism.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Level-warp mechanism
type: finding
confidence: CONFIRMED (mechanism) / UNVERIFIED (live warp execution)
tags: [finding, b8, levelload, warp, stages]
updated: 2026-06-18
---

# Finding — Level-load / stage-warp mechanism

> The complete level-load chain + the 15-stage→directory map = the **recipe for a level-warp** (load LEVEL02–10 on demand). The mechanism is fully traced; a **verified live warp is not yet executed** (see Caveat). Also resolves B8's "15-variant→10-dir stage map" unknown.

**Confidence:** CONFIRMED (chain traced live) · **Established:** 2026-06-18 (B8)

## The levers
- **Requested stage:** `[0x80082504]` (s32) — read by the load orchestrator at entry (=1 in LEVEL01).
- **Loaded stage:** `[gp+0x564] = [0x800822FC]` (s16) — tracked by the stage loader to skip reloads (=1 in LEVEL01).
- **15-stage → directory map** (filename-string table @ `0x8001ad0c`):

| stage | dir\overlay | stage | dir\overlay | stage | dir\overlay |
|--:|--|--:|--|--:|--|
| 1 | level01\level1a | 6 | level01\level2c | 11 | level02\level4b |
| 2 | level03\level1b | 7 | level04\level3a | 12 | level03\level4c |
| 3 | level02\level1c | 8 | level05\level3b | 13 | level09\level5a |
| 4 | level06\level2a | 9 | level04\level3c | 14 | level08\level5b |
| 5 | level10\level2b | 10 | level07\level4a | 15 | level05\level5c |

## The load chain (CONFIRMED)
```
main-shell SM (0x8004fa40) --[load substate]--> jal orchestrator 0x8005222c
  0x8005222c: fp = [0x80082504]              ; target stage (read at entry)
              loads global resources (idx 19) then the stage
              --> jal stage-loader fcn.8003cf2c(a0 = stage 1..15)
  fcn.8003cf2c: dispatch (a0-1) @ table 0x8001afb0 -> per-stage handler
                sets [gp+0x564]=a0; a0 = stage filename; --> common tail 0x8003d1fc
  0x8003d1fc: --> jal 0x80042e94               ; the actual CD load of the stage's files
```
Orchestrator callers: `0x8004fca8`, `0x8005028c` (both in the main-shell SM). `fcn.8003cf2c` callers: `0x8003f544 / 0x800503cc / 0x80052290 / 0x8005b830` (the `0x80052290` one does `a0 = [0x80082504]` directly).

## Warp recipe
Set `[0x80082504]` = target stage (1–15), then cause the main-shell SM to enter its load substate (re-invoking `0x8005222c`).

## The clean lever (CONFIRMED)
The main loop (`0x8004fa40`, the never-returning boot entry) dispatches by substate `[0x8008243c]`:
```
v1 = [0x8008243c]; if v1 < 6: jr table[v1]   ; table @ 0x8001b3c4
```
and **substate 5 → the load case `0x8004fca0`** → clears `[0x8008243c]` → orchestrator `0x8005222c` (stage from `[0x80082504]`). So the warp lever is: set `[0x80082504]`=target + `[0x8008243c]`=5.

> [!warning] Caveat — ATTEMPTED; verified warp NOT achieved (the lever needs the **shell phase**). Setting `[0x8008243c]=5` + `[0x80082504]=3` **mid-gameplay crashed to BIOS** (`pc=0xbfc0d8e0`): that substate dispatch is the **shell-phase** path and is *not* the active context during in-level play (a different loop runs), so forcing substate=5 mid-level corrupts the flow. (`npc` is also unsettable, ruling out a direct call; instruction-patching hits the same context problem.) A **verified warp therefore needs a shell-phase entry** — a pre-level/inter-level save state (none on hand; all saves are mid-gameplay) or RE of the gameplay→shell transition (quit/die path). `loadState` cleanly recovers from the crash. The *mechanism + lever* are fully mapped; the missing piece is the **shell-phase context**, not an instruction patch.

## Related
[[Blocker - RE depth is LEVEL01-only]] · [[Finding - Level formats generalize, content is per-level]] · [[FUNC_8003CF2C]] · [[Asset - LEVEL.BIN and overlays]] · [[Finding - GPU primitive injection]] (the patch-redirect technique)
- Source: live disasm/trace 2026-06-18 (B8)
