---
kind: system
id: SYS_dat_node_array_and_budgets
created: 2026-08-11
updated: 2026-08-11
status: confirmed
confidence: confirmed
source_state: original_game
aliases: [DAT node array, floor node registration, chunk-32 ceiling, level size budgets]
evidence:
  - EXP_2026-08-19_dat_node_and_budget_evidence_index
  - docs/LEVEL_REPLACEMENT_STATUS.md
  - docs/LEVEL_REPLACEMENT_BLOCKER_TRIAGE.md
---

# DAT node array + the budgets that cap a custom level

## The node array

`LEVEL.DAT +0x45F0`, stride `0x18`, marker at `+0x10`, payload offset at `+0x14`, `T_obj` s32 XYZ at
`+0x00/+0x04/+0x08`. LEVEL01 holds two adjacent runs:

| marker | entries | span | role |
|---|---:|---|---|
| `0xC0080000` | **42** | `+0x45F0..+0x49E0` | native floor/terrain payloads drawn by [[FUNC_80010000_per-object_mesh_draw_-_payload_emitter]] |
| `0xC0040000` | **41** | `+0x49E0..+0x4DB8` | a second node class, immediately after |

The floor run is bounded by the second run, **not by free space**, so a 43rd floor node cannot be
appended without overwriting a `0xC0040000` entry.

## ⛔ Converting a `0xC0040000` node to a floor node does NOT work

Tested 2026-08-11 (`tools/probe_node_marker_flip.py`): flip one `0xC0040000` entry's marker to
`0xC0080000` and repoint it at a freshly appended grid payload — a 2,800 x 2,800 file-unit slab
150 units above the spawn floor, centred on the spawn, impossible to miss.

**Result: 0 of 488,000 pixels differ** from an identity-rebuild control that is itself bit-identical
to pristine. The converted node draws nothing. (An earlier attempt with the slab 1,200 units
overhead produced 19 scattered specks with no coherent geometry — treat that as noise, not a draw.)

**Conclusion: a floor node needs more than its marker and payload pointer.** The registration/cull
record that P57 identified — *"relocating geometry away from its original bbox stops it rendering"* —
lives outside the node array (the stride-`0x14` pass-1 tables whose `+0x10` points back at a node,
walked by `build_g3_native._park_table`). Extending authored coverage therefore means creating a
matching registration record, not flipping one field.

⚠️ So **authored coverage is currently capped at the 42 existing floor payloads and their own
bboxes**. That is a real constraint on custom-level footprint until the registration record is
understood. It is research with a clear next step, not a wall.

## Budgets, measured

| budget | safe | fails | notes |
|---|---:|---:|---|
| **LEVEL.DAT** | ≤ **388,388 B / 190 sectors** | 398,388 | silent load-time overwrite; see `docs/G3_NATIVE_DAT_GROWTH_RESULT.md` |
| **chunk-32 (decompressed)** | **260,688 works** | **322,768 boot-fails** | pristine is 236,944 |

chunk-32 severity scales with size and is **non-monotonic** at the top, exactly like the DAT ceiling:

```
167,568  PASS (but tiles too coarse to hold a wall)
209,104  PASS and contained          <- the shipped full-corridor build
260,688  PASS
322,768  BOOT FAIL
349,200  boots, then PINNED (moved_xz 0)
394,192  BOOT FAIL
```

**Standing guidance: keep chunk-32 at or below ~260,000 B**, and prefer at/below pristine's 236,944
where possible (P52's working world build was 231,664).

## The design rule these budgets force

**Coarse base collision tiles + adaptive refinement only at the walls.** Uniform-fine blows the
chunk-32 budget (pinned/dead); uniform-coarse fits but cannot hold a wall — a 400-unit band inside a
~1500-unit tile becomes a walkable ramp and Flik walks out. `--replace-tile-n 4
--wall-collision-step 41600` is the combination that satisfies both.

## Two more things that are referenced BY POSITION (both cost a build to learn)

- **The pass-1 / pass-3 prop tables** (stride `0x14`, bases `0x1504` and `0x3AEC`). Compacting them
  to delete records **breaks the DAT relocation chain** — `dat_reloc.DAT.scan_sites` immediately
  overruns (offset `0xFFFFC1A6` on a 332,824-byte DAT). Records are referenced by position. Relocate
  them off-field instead (`park_props`), which is already a data edit rather than a runtime hide.
- **The `0xC0040000` node slots** — see the negative result above.

## Collision selection extent

`emit_floor_planes` selects sectors by origin within `hx/hz` of the spawn. `--corridor`
(14500, 30500) misses **7 block sectors**, all west at x −8498..−10921; max |dx| across all 189 is
**17080**. `build_g3_native --play-half 17100 30500` authors every reachable sector: 93 block
replaced + 85 flat added = **178 of 189**, the remaining 11 being the malformed relocation-region
blocks (sunk, not authored).

## ⚠️ Authored walls have a FOOTPRINT HOLE class (2026-08-11)

`--replace-all-blocks` authors a replacement over each block sector's **own pristine footprint**
(`emit_floor_planes._block_footprint` = the union of the OLD block's floor-plane footprints). Where
that footprint does not reach the authored wall band, **the wall is simply not emitted in that
sector**, and neighbouring flat sectors only cover ±1300 around their origin — so a wall crossing
such a boundary can get planes from neither.

Measured on the shipped arena: sector 156 (org 3640,12210) has **20 steep planes pristine and ZERO
after authoring**; its footprint x[3158,3999] z[11772,12582] stops **128 units short** of the north
wall band at z[12710,12800]. The operator independently found exactly one climbable wall — the
north one — reproduced in `docs/JUMP_UP_WALL_REPRO.md` (holds Up + spams Cross, gains 2,966 file
units and leaves the arena). Not proven to be the same spot, but the same wall.

Steep-plane density per wall on that disc: W 266, E 259, **N 149**, S 180 — the north wall is the
sparsest and never reaches the ~90° the W/E walls do.

### ⛔ Authored walls fail at their BASE, not their top — the straddling-cell staircase

The operator found one climbable wall; the cause is a **walkable staircase at the wall base**, and it
is a property of how the band is refined, not of wall height. Measured across the four walls of one
arena — walkable-angle planes (<68.7°) sitting ≤200 file units above the floor:

| wall | reachable steps | lowest | ever escaped? |
|---|---:|---|---|
| **N** | **14** | 90u | **yes — every escape exits north** |
| W | 10 | 85u | yes |
| E | 1 | 40u | — |
| **S** | **0** | — | **never** |

The only wall with no reachable low step is the only one that never failed. North carries 34.1° and
39.5° planes at 90 and 140 units up, repeating along its whole length.

**Origin:** a 90-unit band against a 900-unit rise means a refinement cell that **straddles the
band's inner edge** is part floor and part wall face and averages to an intermediate angle, landing
~90–140 units up — exactly a step. Sparser walls have more straddling cells, so the sparsest wall has
the most steps.

**Fix direction:** not more density in general — ensure no cell straddles the band edge. Snap
refinement boundaries to the band edges, or widen the band so cells fit inside it. Raising wall
HEIGHT does not help (the staircase is at the base): 900→1,200 left the north wall climbable.

### ⚡ Wall ANGLE and wall HEIGHT are two separate rules

Measured from the operator's save (`docs/JUMP_UP_WALL_REPRO.md`): Flik's **jump reach is up to 784
file units**. Against the arena's 900-unit walls that is a **13% margin**, and only one wall of four
is actually beaten — so height is barely doing its job.

- **Angle ≥ ~69°** stops him WALKING up (measured 56.3° escapes, 68.7° contains).
- **Height > ~784 file units, with margin** stops him JUMPING over. **Author at 1,200+.**

**Cheapest candidate fix (untested):** `--coverage-margin`, which already expands replacement
footprints; or make the replacement extent the union of the sector's own footprint and any authored
wall band crossing it.

Related: [[Tier_3_-_Native_Terrain_Path]], [[FUNC_80010000_per-object_mesh_draw_-_payload_emitter]],
[[SYS_collision_and_floor_planes]].
