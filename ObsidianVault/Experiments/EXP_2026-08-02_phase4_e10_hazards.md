---
kind: experiment
phase: 4
row: E10
date: 2026-08-02
status: substantiated-partial-high-value-bounded
method: retained-capsule-c-reconstruction-and-c-static-asm
---

# Phase 4 E10 environmental hazards

## Question and scope

Determine whether the retained E10 fixtures support a useful environmental-hazard
mechanism result without another live replay, and whether the row can honestly move
from unresolved to partial.

Included here:

- Rolling acorn, chronological Level 11.
- Falling rocks, chronological Level 2.
- Falling spikes, chronological Level 5.
- Poison goo, chronological Level 7.
- Pits in chronological Levels 2, 5, and 7.

The ground-bird kill zone is already covered by
[[EXP_2026-08-02_phase4_d17_bird]] and was intentionally left untouched. Water,
traffic, and thorn plants/barriers retain their established negative classification.
Webs and the unnamed instant-kill-region census remain open.

## Evidence order and identity

The Phase 4 acceleration rule was followed:

1. Validate the relevant retained v3 capsules.
2. Reconstruct RAM, VRAM, SPU RAM, registers, and block flow offline in C.
3. Correlate health, lives, player XYZ, safe-anchor XYZ, power flags, and damage timer.
4. Reduce event-only block flow to the exact shared paths.
5. Map the runtime PCs back onto the existing hand-written ASM with a second C tool.
6. Do not launch DuckStation when the retained domains already answer the question.

Across seven capsules, C reconstructed 2,804 frame records and verified 8,412
per-frame domain hashes with zero mismatches. Every manifest reports complete,
untruncated, cycle-neutral capture and an empty control-mismatch set. The bounded
manifest summary is SHA-256
c2ee7b8f70d8d5c6e6e741288202d6c8cf319e61a7c5e9ee24dce640477bd0ab.

These are passive CachedInterpreter capsules. They are valid for offline
frame-boundary reconstruction, but their source movies must never be replayed with
CPU instrumentation armed.

## Result 1: four damage hazards, three producer classes

All six captured damage boundaries converge on the same resident damage routine at
0x8004A700. The static body decrements signed health at 0x800A6594 by one.
A nonnegative result arms damage timer 0x800A6592 to +45. A negative result uses
-45 and enters the death-transition branch.

The producer path is not the same for every hazard:

| Fixture | Boundary | Producer path | Exact caller |
|---|---:|---|---|
| Acorn | m428 health 1 to 0; m548 0 to -1 | Actor contact | 0x8004B4A0 |
| Falling rocks | m331 health 4 to 3 | Contact-object walker | 0x80058A48 |
| Falling spikes | m105 health 1 to 0 | Contact-object walker | 0x80058A48 |
| Goo | m108 health 4 to 3; m198 3 to 2 | Player/world collision | 0x80049740 |

The caller classification is runtime-discriminated:

- Only the acorn hit frames take the actor branch surrounding 0x8004B4A0. That
  branch sets actor flag 0x1000, calls the damage routine, then compares health
  before and after.
- Only rock/spike hit frames take the contact-walker tail at 0x80058A24. The
  walker has scanned all 64 contact records; when its hit latch equals one it
  passes player-relative X/Z and a response vector to 0x8004A700 at 0x80058A48.
- Only goo hit frames take the player/world branch through 0x80049718 and call
  0x8004A700 with zero planar impulse at 0x80049740.

Goo's two hits are 90 emulator frames apart, or 45 ordinary 30 Hz gameplay
updates. That matches the static +45 nonfatal damage timer exactly. The acorn's
second captured hit takes the negative-health branch, while spikes demonstrate
the important zero-health boundary: health 1 to 0 is not fatal because the
routine tests result below zero.

The nearest acorn-fixture actor at the hit boundary is actor id 10, record index
26, but that is retained as a correlation rather than promoted to a semantic
identity: the frame-boundary actor flags do not by themselves prove that the
visual rolling acorn owns that record.

## Result 2: pits bypass ordinary health depletion

The three pit fixtures agree at the state boundary:

| Fixture | Commit | Pre-fall Y to restored Y | Health | Lives |
|---|---:|---:|---:|---:|
| Pit Level 2 | m157 | 153067 to 30092 | 3 to 4 | 5 to 4 |
| Pit Level 5 | m145 | 111928 to 3628 | 0 to 4 | 1 to 0 |
| Pit Level 7 | m205 | 121085 to 9584 | 4 to 4 | 6 to 5 |

All three commits execute the same 0x8005B134-family reset path, converging at
0x8005B1BC and continuing through the 64-record reset loop and collision reset
0x8004DC0C. Static ASM explains the atomic frame:

- Load safe-anchor XYZ from 0x800A6550/54/58.
- Write it to live player XYZ 0x800A6500/04/08 and previous position.
- Clear motion and transient player state.
- Restore health to 4.
- Preserve only power flag bit 0x20.
- Decrement the byte at 0x800A65A0 by one.
- Reset collision/contact transition state.

Level 7 is the decisive negative control against a health-depletion explanation:
health remains 4 while lives decreases and position is restored. The fade path at
0x80028D74 and transition-timing blocks at 0x8004D758/0x8004D784 correlate with
the presentation but do not perform the kill.

## C artifacts

- [phase4_e10_capsule.c](../../../tools/phase4_e10_capsule.c) reconstructs all
  domains, verifies each SHA-256, tracks corrected byte-sized lives state, and
  emits event-only block flow.
- [phase4_e10_asm.c](../../../tools/phase4_e10_asm.c) rebuilds instruction PCs
  from the existing ASM and guards the three caller contracts, health split,
  and respawn commit.
- Structured result:
  [phase4_e10_hazards.json](../../../analysis/phase4_e10_hazards.json).
- Central capsule preservation contract:
  [phase4_trace_capsule_set.json](../../../analysis/phase4_trace_capsule_set.json).

The temporary deep-dive outputs are pinned by SHA-256 in the structured result.
They include the exact pit event-flow set, resident ASM reduction, caller
neighborhoods, and capsule-RAM overlay disassembly. No copyrighted capsule,
movie, save, or RAM bytes are added to the repository.

## Phase 4 closure metrics

| Metric | Result | Remaining reason |
|---|---|---|
| Original behavior oracle | Advanced, not met | Seven state-anchored retained fixtures, not a dedicated cold-boot campaign oracle |
| Semantic frontier | Advanced, not met | Three producer classes and two shared outcomes closed; webs and unnamed kill regions remain |
| Typed state | Advanced, not met | Health, lives, timer, flags, position, anchor, and shared handlers typed; per-hazard authored records incomplete |
| Lifecycle | Advanced, not met | Repeated goo/acorn hits and three pit respawns; pause, scene transition, and game over absent |
| Positive/negative controls | Partial | Zero-health nondeath and health-independent pit death are strong controls; full hazard denial matrix absent |
| Campaign breadth | Advanced, not met | Four damage families, pits in three levels, bird credited to D17; webs and census absent |
| Cross-system contracts | Advanced, not met | Actor, contact pool, collision, damage, and lifecycle paths joined; HUD/audio not traced |
| Source closure | Partial | Byte-exact hand ASM and C guards, not matching/reviewed semantic source |
| Durable gate | Advanced, not met | Hash-pinned capsules and reusable C reducers, no dedicated cold-boot promotion assertion |

## Exit and movie decision

E10 advances from unresolved to **substantiated partial**. The high-value
mechanism work represented by the seven retained fixtures is bounded enough to
move on, but the full Phase 4 row is not exhausted or solved.

No new Interpreter movie is required now. Request one only if webs or a named
uncaptured instant-kill region is promoted, or if an exact every-cycle producer
attribution becomes materially necessary. A disc/code/asset change would require
the separate cold-boot path; none was made here.
