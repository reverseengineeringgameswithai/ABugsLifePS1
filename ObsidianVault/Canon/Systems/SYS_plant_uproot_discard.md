---
kind: system
id: SYS_plant_uproot_discard
name: Plant uproot and seed restoration
title: Plant uproot and seed restoration
tags: [canon, plants, seeds, player-actions]
status: confirmed
confidence: confirmed
source_state: original_game
evidence:
  - EXP_2026-08-03_phase4_a15_uproot_discard
  - EXP_2026-07-19_phase4_offline_seed_lifecycle_batch
---

# Plant uproot and seed restoration

## Confirmed retail behavior

- Uproot uses a **new Square edge**, not a continuously held Square state.
- The nearest candidate must be occupied (`slot+0 != 0`), mature
  (`slot+2 != 0`), eligible (`slot+0x2E & 2`), close enough, and within the
  accepted facing cone.
- Admission clears eligibility bit `0x02` and raises uproot bit `0x40` in
  `slot+0x2E`, retaining the seed backlink at `slot+0x20`.
- The linked seed actor descends at pinned X/Z from the planted height offset
  `+20480` to ground.
- The restored seed is the **same actor**, not a newly allocated actor; the
  observed live type-11 seed count remains constant.
- Seed source color resets to `0`; it is not retained. Global selection lanes
  remain unchanged.
- Cleanup is logical invalidation: `0x8005CE2C` writes zero to `slot+0` when
  the shared animation command stream reaches a zero terminator. Backlink,
  `slot+0x2E`, and other fields can remain as inert residue.
- The plant allocation cursor does not decrement during teardown.

## Key retail addresses

| Address | Meaning |
|---|---|
| `0x80090BF0` | 20-slot plant array base |
| `0x30` | Plant slot stride |
| `slot+0x20` | Linked seed actor pointer |
| `slot+0x2E` | Eligibility/uproot and family state |
| `0x800822B8` | Plant allocation cursor |
| `0x800478E8..0x80047A24` | Square-edge admission and ownership handoff |
| `0x80049DF4` | Observed seed source color reset writer |
| `0x8005CD2C` | Shared plant animation-command interpreter |
| `0x8005CE2C` | Terminal `sh zero,0(s0)` slot invalidation |
| `0x8005BE90` | Plant type allocation store |
| `0x8005BF18` | Seed backlink allocation store |

## Evidence boundary

Four retained pristine cycles cover plant types `7, 7, 6, 7`, including long
no-Square persistence controls. Exact teardown attribution comes from a
state-anchored continuation armed only after CachedInterpreter playback was
stopped. This is original-game behavior, so no patched-disc cold boot is
required.

Commands, hashes, completeness, disassembly, and the rejected early contract
table are in [[EXP_2026-08-03_phase4_a15_uproot_discard]].
