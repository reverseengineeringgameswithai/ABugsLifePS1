---
kind: system
id: SYS_grain_collection_and_harvester
name: Grain collection and harvester equipment
status: static_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
evidence:
  - analysis/phase4_collectibles_frontier.json
  - EXP_2026-07-30_phase4_collectibles_static_frontier
src_paths:
  - src_re/grain_harvester_equipment_80051db4.c
  - src_re/grain_contact_convergence_8005a308.c
  - src_re/source3f_dispatch_80053814.c
  - src_re/contact_alloc_80059e44.c
  - src_re/pickup_handlers_80054288_80054554.c
---

# Grain collection and harvester equipment

## Original-game ownership

The pristine resident actor-model dispatch indexes actor IDs `1..41` as
`id-1`. Actor ID `35` therefore uses table entry `0x8001BC64`, case
`0x8005E17C`, and the resident string `chars3\flikharv` at `0x8001BA90`.
The model and animation are the hash-pinned retail
`CHARS3/FLIKHARV.ALL` and `FLIKHARV.ANM`.

The Phase-1 census authors actor 35 exactly once, always in fixed actor slot
63 at `0x800A1DFC`, in Anthill, Tunnels, Riverbed Run, City Square, Clover
Forest, and The Tree. The retained C13 actor-ID signature uniquely matches
Anthill. Its frame-0 actor 35 retains source `0x8009511C` and begins at the
Anthill authored X/Z coordinates.

Resident function `0x80051DB4..0x80052090` owns equipment acquisition and
follow behavior. It gates fixed actor ID 35, tests proximity with argument
`40`, and writes harvester bit `0x0080` into the resident `u16` player
power-up flags at `0x800A6590` through instruction `0x80051EB0`. While that
bit is present, the function copies Flik's coordinates and heading into slot
63 before the ordinary actor/contact/source update sequence. In the retained
C13 index, bit `0x80` first appears at movie frame 83 and actor 35 then stays
at the exact frame-boundary delta `(0,192,0)` through frame 617.

## Attraction and collection

The source-3f dispatcher tests bit `0x80` for kind `0x14`. Within squared
distance `0x15F8F`, it constructs contact type `0x51` with stack argument 3,
marks the source consumed, and overwrites the contact target at `+0x10` with
`-1`. The pristine 20-byte metadata row for ctor `0x51` decodes to:

- action ID 20, active gate 200, phase 210;
- signed radius-add 100, auxiliary value 100, state 22;
- selector 0 and flags `0xEA`.

Flags bit `0x08` enters the common branch in the 64-record updater at
`0x8005A308`. Target `-1` selects Flik. With
`delta=(desired-heading)&0xFFF`, the updater adds `delta>>2` below `0x800`
and `(0x800-delta)>>2` otherwise; this is the exact native piecewise rule,
not a conventional shortest-arc formula. It moves Y by one eighth of the error toward
`playerY-0x2000` clamped to `±0x400`, derives X/Z velocities from the resident
sine table shifted by three, and integrates X/Z. This common contact updater
is broader than its historical `berry_projectile_update` label.

Three radii have distinct roles and must not be conflated: `0x15F8F` is the
source squared-distance construction gate, ctor `0x51` stores radius-add 100,
and the contact walker uses base 300 plus that field for a pickup radius of
400. The existing action-20 dispatch calls the resident grain handler.

## Grain count and the 50th grain

`0x80054F9C` increments the `u8` grain count at `0x800A65A1`. At count 50 the
handler snapshots player fields, requests result `-11`, and reaches a static
comparison between fixed addresses `0x80090B80` and `0x800B3988`. They are
unequal in the pristine resident image, so the nested progress/life increment
and its `-8` event are unreachable on this path. The reachable reward tail
stores health value 4 at `0x800A6594` through `0x80055124`.

The retained C02 frame-160 boundary is consistent with that reconstruction:
grain changes `49→50`, true health remains `4→4`, and SPU RAM does not change
in that frame. The cycling health-display byte is presentation state, not
evidence for a new heal value, token write, or emblem owner.

## Closure boundary

These are confirmed original-game static and retained frame-boundary facts.
They do not satisfy a cold-boot oracle or prove a same-anchor bit/radius
intervention. Denial, full contact capacity, reset, death/respawn,
unload/reload, persistence, HUD presentation, and audio asset identity remain
open in the active Phase-4 campaign.

See [[EXP_2026-07-30_phase4_collectibles_static_frontier]] and
[[Game Solving Campaign - Grain Collection and Harvester]].
