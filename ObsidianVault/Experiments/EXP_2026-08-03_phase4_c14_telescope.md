---
kind: experiment
id: EXP_2026-08-03_phase4_c14_telescope
status: complete
source_state: original_game
system: [SYS_camera, Enemy_spawn_architecture]
row: C14_telescope
---

# Phase 4 C14: the dewdrop telescope — state machine decoded, C-pinned

## Question

Operator: *"what is interesting are the telescopes that 'show' the end of the level or good
collectibles, is that a different row?"* It is — C14_telescope, which already held a retained
operator movie (`c14_telescope_full.movie.json`) and whose own named next ("replay under
camera-state watch") doubled as the telescope fixture E04 had just asked for.

## The replay (poll-only, v3 fixture)

Sampled the camera struct + the shared state variable `0x800824DC` + telescope index
`0x800823CC` every 10 frames across the 652-frame movie (CachedInterpreter fixture →
matching-mode instance, strictly poll-only, no CPU instrumentation). Observed lifecycle:
idle → **−2 transient with index 1** at activation → **view countdown from ~248, ticking
−1 per 2 frames** for ~8 seconds → at expiry, **−117 counting up** (return phase; movie ends
mid-return). Screenshots: Flik stands beside the green dewdrop scope at f0; from f90 the
screen shows a **circular scope-vignette view panning across distant terrain** — while the
follow-camera struct sits **parked, byte-identical, no submode code**. The preview is
rendered by a **separate camera producer** — direct confirmation of E04's
modes-are-separate-producers model. Activation also freezes Flik (velocity + grounded
zeroed).

## The state machine, decoded and pinned in C

Per the operator's standing instruction, the static probing is a compiled C tool —
`tools/phase4_c14_telescope_static.c`, **27 instruction words pinned against the pristine
EXE, 27/27 OK** (the tool caught a byte-order typo in its own first draft, exactly as
designed).

**Owner**: `setpiece_spawn_manager 0x8004D698` — already Canon for the setpiece/bird spawn —
owns the entire lifecycle of `0x800824DC`:

```
0 idle → −1 trigger → −2 acknowledged → 252 view countdown
  (−1 per manager call, gated on goal latch 0x800823A0 clear)
→ 0 → −120 return phase (+1 per call) → −10 → 0 idle
(+ setpiece states 13 → writes 4 to 0x80090BEC; 14 ← sensor 0x80082412 & 0xF000)
```

**Two producers of the −1 trigger, both pinned**: the kind-0x30 telescope activation case
(`0x80054554..94`: state==0 check, index store, −1 write, player freeze) and the scripted
setpiece path. External clears at the respawn tail and scene init — respawn cancels a view.

**This resolves E04's dual-attribution flag with hard evidence**: `G_TELESCOPE_ACTIVE` and
"the setpiece trigger" were both correct fragments of ONE shared special-view state machine
with one owner and multiple trigger producers.

## The content question, closed (2026-08-03, "continue on the drilling")

I'd flagged that the *mechanism* was bounded but the thing actually asked — **what does each
telescope show, and how is that authored?** — was still open. Both halves are now closed.

**The chain**: telescope index (`0x800823CC`) → pointer table `0x80096DC8[index]` → a
LEVEL.DAT **path record** → `setpiece_spawn_init` → the **setpiece actor struct**
`0x80090BC0`. So the preview camera's state source is the setpiece actor — **the telescope
preview and the scripted bird flyby are one system**, which is the root cause of the dual
attribution this row resolved earlier at the state-variable level.

**Record layout**: 4-byte header + 16 waypoints × 12 bytes (stride `0xC4`, matching the
committed "16-waypoint path records"). Init consumes the first two: **waypoint1 → the
actor's start position, waypoint0 → its look target**, both `<<5` by the documented
file→runtime law; heading comes from the Canon `atan2_heading` on (target − position).

**C-pinned**: `tools/phase4_c14_telescope_target.c` — 32/32 instruction words verified,
including the `index*4` table lookup, all six coordinate loads with their shifts, and every
setpiece-actor store. (It caught its own byte-order slips again before anything was banked.)

**Offline → live, exact**: dumping `LEVEL01/LEVEL.DAT` at the three committed record offsets
gives `rec@0x94C` position `(-2117,-5042,2678)` / target `(-5576,-5620,-3772)` in file
coords. Replaying the movie, the setpiece actor at activation reads position
`(-67744,-161344,85696)` and target `(-178432,-179840,-120704)` — **exactly those values
`<<5`, to the unit**, with index 1. The live pointer table proves the mapping is **1-based**:
`[0]=NULL`, `[1..3]` → DAT offsets `0x94C/0xA10/0xAD4`, precisely the three committed
records. During the countdown the actor genuinely **flies** (position walks across the level,
heading swinging, target pinned) and stops the instant the countdown expires.

**Modding lever**: telescope targets are plain on-disc s32 waypoints consumed via the
standard `<<5` law — retargeting what a telescope previews is a straightforward DAT data
edit, same pipeline as the proven enemy-spawn relocation. Not attempted here.

## Still open

The scope-vignette overlay renderer; reuse after the return phase; the all-level kind-0x30
census and per-level record offsets beyond LEVEL01's three (now automatable — stride `0xC4`,
1-based table); how the remaining 14 waypoints are consumed in flight (only two are read at
init); states 13/14 semantics; `0x80082388`/`0x80082412`; which index the scripted bird uses
versus the telescopes.

## Evidence

`analysis/phase4_c14_telescope.json`; `tools/phase4_c14_telescope_static.c`;
retained fixture `movies/Phase4/c14_telescope_full.movie.json`.

## 2026-08-04 bounded-exhaustion addendum

**Status:** Substantiated Partial / bounded-exhausted. Move on.

This addendum supersedes the remaining-open list and the earlier two-producer wording. The new C closure verifier pins 45/45 instructions, confirms 24 direct accesses and 10 stores for 0x800824DC, and matches the campaign's 25 kind-0x30 entries to 25 authored 0xC4 path records.

### Corrections

- There is one pinned direct -1 producer, not two: the kind-0x30 contact action at 0x80054574. The earlier scripted-setpiece attribution described the consumer/system role, not a second direct trigger writer.
- 0x80082412 is the shared current pad word, not a telescope sensor.
- 0x80082388 is the first current channel of the shared screen-transition interpolator, not a telescope-specific timer. The manager waits for it to reach zero before changing -2 to the 252-tick flight.

### Waypoint flight closed

For active states 252 through 29, 0x8004D7AC computes phase = 268 - state. The manager derives segment = phase >> 4 and fraction = phase & 15, then linearly interpolates consecutive 12-byte waypoint triples. This walks waypoint 1 through waypoint 15. Waypoint 0 remains the fixed look target installed at spawn. The interpolated XYZ values, shifted by 5, are written to setpiece actor fields 0x80090BD8/BDC/BE0.

### Early return and states 13/14 closed

The face-button check is accepted only when unsigned(state - 15) < 205, meaning states 15 through 219. A pad mask 0xF000 forces state 14. With the goal latch clear, the same manager call decrements it to 13; on the next call, state 13 writes actor phase 4 at 0x80090BEC. The countdown then continues toward the ordinary return phase.

### Presentation renderer closed

0x80053638 reads 0x800824DC and does nothing at idle zero. Otherwise it calls draw_textured_quad 0x80026A68 four times, at 0x80053694, 0x800536C4, 0x800536F4, and 0x80053720, using mirrored tile-26 quadrants. This is the special-view mask/presentation renderer left open by the earlier pass.

### Reuse lifetime closed

At contact, 0x80053CC4 emits the contact effect, then 0x80053CCC/0x80053CD0 store the consumed sentinel 0x80000000 into the source entry's Y field before action dispatch. Therefore the contacted telescope is one-shot until the scene data is rebuilt. Once the return reaches state zero, another unconsumed telescope can activate. Respawn and scene initialization explicitly clear the shared state; scene reload restores authored source records.

### Campaign census closed

The C LEVEL.DAT walker found 25 kind-0x30 entries and exactly 25 plausible path records:

| Level | Count | Path-record offsets |
|---|---:|---|
| LEVEL01 | 3 | 0x94C, 0xA10, 0xAD4 |
| LEVEL03 | 2 | 0x1508, 0x15CC |
| LEVEL04 | 3 | 0x1AF0, 0x1BB4, 0x1C78 |
| LEVEL05 | 4 | 0x4A8, 0x56C, 0x630, 0x6F4 |
| LEVEL07 | 6 | 0x7AC, 0x870, 0x934, 0x9F8, 0xABC, 0xB80 |
| LEVEL09 | 3 | 0x698, 0x75C, 0x820 |
| LEVEL10 | 4 | 0x654, 0x718, 0x7DC, 0x8A0 |

LEVEL00, LEVEL02, LEVEL06, and LEVEL08 contain none. The kind-0x30 ordinal is incremented before use, matching the path pointer table's one-based layout.

### Bounded residuals

- Recovering the artistic source or VRAM upload provenance of tile 26 would not change renderer ownership or behavior.
- Producing screenshots and prose descriptions for all 25 views is content cataloging, not a missing engine edge.
- Kind 0x31 shares adjacent contact code but is outside this row's named kind-0x30 scope.
- The address census does not claim against a hypothetical pointer alias loaded from RAM; no observed edge requires one.

No new Interpreter movie is required. The retained CachedInterpreter fixture remains valid poll-only evidence, while every newly closed edge here is answered by pristine static code/data. Permanent verifier: tools/phase4_c14_telescope_closure.c. Machine-readable result: analysis/phase4_c14_telescope.json.
