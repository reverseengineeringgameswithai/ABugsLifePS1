---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Hypotheses/Hypotheses.md
aliases:
  - "Hypotheses"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Hypotheses/Hypotheses.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Hypotheses
type: dashboard
updated: 2026-06-17
tags: [dashboard, hypotheses]
---

# Hypothesis Tracker

> Status vocabulary: **UNKNOWN · INVESTIGATING · LIKELY · CONFIRMED · DISPROVEN** (incl. RETRACTED/SUPERSEDED). The graveyard of disproven hypotheses is as valuable as the confirmed ones — it stops future sessions re-walking dead ends. Sources: `docs/EXPERIMENT_LOG.md`, the geometry G-series.

## Active / open
| # | Statement | Status | Resolve via |
|---|-----------|--------|-------------|
| H-A | Candidate A is specifically the *walkable* visual surface (vs a co-planar visual chunk) | LIKELY | match its screen region to Flik's footing |
| H-B | `fcn.8005b134` participates in the player-Y path it once was credited for | UNKNOWN | [[Open Questions]] #3 |
| H-C | Payload `attr` (vertex+0x8) encodes UV/normal/color | LIKELY | decode primitive cases in [[FUNC_80010000]] |
| H-D | LIST_B (`0x8009e338`) has a real consumer | UNKNOWN | search readers of `0x8009e338` |

## Confirmed (promoted)
| Statement | Evidence | Note |
|-----------|----------|------|
| Visual terrain ≠ collision source | G28 deform didn't move collision; G29 separate file | [[HYP - visual equals collision]] · [[Finding - Visual is not collision]] |
| Floor/collision source = decompressed LEVEL.RAW | G22 bracket + G29 chain | [[Finding - Floor resource is LEVEL.RAW]] · [[Finding - Collision on-disk source is chunk 32]] |
| Candidate A is a DAT-backed visual terrain payload | G28 operator-tested deform | [[Finding - Candidate A is DAT-backed visual terrain]] |
| Player-Y writer is `fcn.8003633c` | G29 WRITE-watch | [[Finding - Player Y writer FUNC_3633C]] |
| New DAT entries can be injected (relocation-aware) | in-game token70 build | [[Finding - Relocation-aware DAT append]] |
| Type-0x3f pickups are coordinate-moddable | many in-game builds | [[Finding - Type-0x3f pickups are coordinate-moddable]] |
| Sky is a GP0 background fill | recolor via VRAM diff | [[Finding - Sky is a GP0 background fill]] |

## Disproven / superseded / retracted (the graveyard)
| Statement | Status | What killed it |
|-----------|--------|----------------|
| `0x21..0x24` are FLIK markers/triggers | SUPERSEDED → special berries | ABL_FLIK_TEST; marker sacrifice removed real berries |
| FLIK letters are kinds `0x21..0x24` | DISPROVEN → `0x10..0x13` | ABL_FLIK10_BIG_TEST + per-letter tests |
| Append fails because seed total 9→10 | DISPROVEN | fixed-count 10-token build loaded fine |
| Global 70-entry / type-0x3f parser cap | DISPROVEN | retail LEVEL05/07/09/10 have 74/77/74/74 |
| Hardcoded code offset (`0x468`/`0x478`/…) causes append crash | DISPROVEN | no such immediate in SCUS/LEVEL.BIN |
| Entries 54..57 are safe sacrifice slots | DISPROVEN | sacrifice removed Gold/Super/Mega-Homing berries |
| Crash is 64-slot contact-pool overflow | DISPROVEN | non-token append (no construct) still crashed |
| Append crash = DAT not loading / type-table failure | DISPROVEN | RAM at `0x8001CE00` shows DAT resident + structurally correct → [[Finding - Relocation-aware DAT append]] |
| `0x8008243c` = level-load phase-transition flag | RETRACTED | it's a main-shell substate index; `0x80082438` is the VSync counter |
| rec10 (`-7`) = "bulk geometry blob to EOF" | SUPERSEDED (G1) | fixed 0x190-byte record ending `0x1500` |
| `fcn.800146e0` is a projection stage | DISPROVEN (G10) | libgte camera-matrix load leaf |
| RTPT `@0x80014970` is part of the terrain chain | DISPROVEN (G10) | belongs to actor/sprite path (reads `0x800b0d18`) |
| `s0=0x4e00` / output rec 261 is the active render record | DISPROVEN (G5.5) | zero read-watch hits |
| entry24 body row is a direct mesh-position row | DISPROVEN (G9) | rejects before list-write → culling row → [[Finding - entry24 is a culling row]] |
| `0x356bc` is walkable ground | DISPROVEN (G16) | edit deformed a wall → [[Finding - 0x356bc is a wall not floor]] |
| LEVEL.RAW `[0xa81ac]` is an editable indexed-geometry stream | SUPERSEDED (G23) | it's compressed → [[Finding - LEVEL.RAW is compressed]] |
| Floor at `0x801bdc58` is an emitted DAT/heap payload | RETRACTED (G26) | `=0x70d4001a`=LEVEL.RAW+0xa81ac; WRITE-watch 0 hits → [[Finding - 0x801bdc58 is compressed source]] |
| Floor is NOT a LEVEL.DAT payload (G17/G18) | DOWNGRADED (G27) | floor-view emit surfaced DAT-backed payloads A/B/C |
| Floor source = a second parsed DAT (G19 H1) | REFUTED (G20) | parser runs once for LEVEL01 |
| Floor source = TERRAIN.ALL conversion (G20 H2) | REFUTED (G21) | EXEC breakpoints, 0 hits |
| `fcn.8005b134` = sole player-Y writer (G5) | SUPERSEDED (G29) | writer is `0x8003633c`; `fcn.8005b134` has 0 jal callers |
| Collision "floor height" is a scalar | DISPROVEN (G29) | it's a set of planes → [[Finding - Collision is planes not scalar]] |
| `0x800F7xxx` grid is the floor contact path | DISPROVEN (G29) | secondary wall/object broadphase; floor = gp+0x57c sector path |
| Sky is a stored image/PNG | DISPROVEN (G30) | GP0 0x02 fill → [[Finding - Sky is a GP0 background fill]] |

## See also
[[Open Questions]] · [[Confirmed Knowledge]] · [[Blockers]] · [[Assumptions Register]] · [[Home]]
