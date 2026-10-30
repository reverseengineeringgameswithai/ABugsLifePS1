> [!IMPORTANT]
> **Status correction, 2026-08-02:** C13 is partial, with high-yield
> row-specific work exhausted. The earlier bounded-exhaustion verdict below is
> historical and is not a Phase 4 solved/closed state. Strict closure is blocked
> by the open shared pointer frontier and incomplete behavioral/interface breadth.
> See analysis/phase4_c13_dod_scorecard.json.
>
> New C evidence: all 15 active RAW scene resources were decompressed and scanned;
> six placements were found (operator levels 1,2,5,8,10,11), all record 63 and
> identical outside position. Retained behavior covers only one placement.
>
> Evidence hashes: RAW C 0bfaf928d0d806a8c129d9d651ba81eee009c929f03d0159980d7951911010b3; RAW JSON c25a12e65332334e2a6de2b6c0e28588f157be41b9632e03e3ababfb27564975; DoD C
> 02ae24f6b10ab478ff068df5906513278d573d11ba949bf522192a9bbfa99b2b; DoD JSON ddf562c17a2f0254d55aba067272745b0731f99a577eb3c064633c3f1aca714a; ASM C cb20521bcbb422ec187e38cac4ebd024ffdc924f4712f81663b358e3c6308257; ASM JSON
> 830bb4b23e533ec9af19854a531c1f2c3552d3bce457566cc3cc158615606cf9; regenerated C13 artifact 2daaf0c1e9719879f623b7f2cb441cea5154671be0912bbb72178d8a21ce0118.

# Experiment - Phase 4 C13 grain-harvester bounded exhaustion

**Date:** 2026-08-02  
**Row:** `C13_grain_harvester`  
**Verdict:** **partial, high-yield row-specific work exhausted**  
**Runtime mutation:** none  
**New Interpreter movie required:** no

## Question

Can the remaining high-value C13 gaps, especially exact grain steering and Cross
disengagement ownership, be closed from the accepted trace capsule and pristine
ASM without another timing-sensitive live replay?

## Authority and method

The accepted frame-boundary capsule remains the runtime authority. It is complete,
untruncated, and its independent control matches RAM, registers, VRAM, SPU RAM, and
full-machine state. The earlier matched pristine continuations remain the behavioral
authority for Cross disengagement and the LEVEL01 bee control.

The continuation used C for the new static investigation:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror \
  tools/phase4_c13_asm_static.c -o /tmp/phase4_c13_asm_static
/tmp/phase4_c13_asm_static \
  asm/hand_written \
  analysis/phase4_c13_harvester.json \
  REBUILD/files/SCUS_942.88 \
  > analysis/phase4_c13_asm_static.json
```

The scanner walks every hand-ASM file, propagates constant/load masks for shared
state and flag writers, recognizes computed and exact contact-array bases, captures
named flow anchors, and reads each raw word from the pristine retail executable.
It scanned 892 files and 100,425 instructions. All 28 named anchors were present in
both the ASM and executable.

Transient scanner defects were disclosed and fixed before evidence was banked:
operand splitting stopped after the first comma, raw tabs were not JSON-escaped,
exact contact-array bases were initially omitted, and `.word` calls were counted
without anchor capture. Only the final source and artifact below are authoritative.

## Capsule correlation

The C reducer consumes the accepted capsule-derived report rather than replaying
DuckStation. It counts nine source events and nine matching ctor signatures:

- action id `0x14`
- TTL `200`
- flags `0xEA`
- exact source/contact/count-chain check true

This is correlation to frame-boundary evidence, not an every-cycle capsule claim.

## Findings

### Cross is a two-owner clear chain

`0x8004A94C` stores `flags & 0xFF7E`, clearing `0x800A6590` bit `0x80`.
`0x80051F60` can no longer maintain `0x800A657E = 1`. The ordinary positive-slot
tick then writes the decremented value at `0x80048654`, producing `1 -> 0`.
This reconciles the earlier uninstrumented three-frame Cross observation without
inventing a direct positive-state Cross writer.

The old candidate `0x8004A808` is not this clear. Its sign split reaches that store
only for a negative power-slot value and belongs to the bubble-hit path.

### Ctor `0x51` uses the shared homing path

`FUNC_80053814` selects ctor `0x51`, consumes the authored source, materializes
`-1` at `0x80053C50`, and stores it to contact `+0x10` at `0x80053C58`.
The nine capsule records have flags `0xEA`, including homing bit `0x08`.

The updater tests that bit at `0x8005A350/0x8005A358`. Target `-1` selects player
coordinates and the bearing helper at `0x8005A39C`. Exact position writers are:

- Y steering: `0x8005A4C8`
- X motion: `0x8005A548`
- Z motion: `0x8005A56C`

The census also found generic allocation, spawn, clamp, and effect-copy writers.
Duplicated `0x8005ACC8..0x8005AF08` candidates are overlapping transcriptions of
one source region, not independent runtime writers.

### Collection, audio, reset, and enemy gate

Action `0x14` dispatches through the contact walker at `0x800589B8`. Collection
conditionally calls the shared SFX manager at `0x80054F80` and increments
`0x800A65A1` at `0x80054F9C`.

Respawn/reset writes state zero at `0x8005B268`; the `0x8005B340` retention mask
also clears harvester bit `0x80`.

The enemy resolver reads/tests the same bit at `0x8004B158/0x8004B160` and writes
HP `998` at `0x8004B208`. There is no actor-id whitelist inside that harvester
sub-branch; eligibility comes from the common contact and actor-flag gates. Only
the LEVEL01 id-13 bee has a retained matched behavioral control.

## Closure boundary

C13 is exhausted for Phase 4 high-value mechanics: equip, maintain, disengage,
authored-source gating, construction, homing, collection, counter/SFX ownership,
reset ownership, and the known enemy retirement path have bounded evidence.

Deferred low-return breadth:

- exhaustive enemy-family and immunity fixtures
- every-level harvester availability
- complete animation/asset identity and save-load persistence surveys
- full MOD regression contract, which belongs to Phase 5

No Interpreter movie is needed now. Request one only when a specific deferred level,
enemy family, or persistence behavior becomes the named question. Cold boot is not
required for this non-mutating ASM/capsule continuation; the earlier pristine live
controls remain the behavioral complement.

## Evidence and preservation

- C source: `tools/phase4_c13_asm_static.c`
  - SHA-256: `cb20521bcbb422ec187e38cac4ebd024ffdc924f4712f81663b358e3c6308257`
- C artifact: `analysis/phase4_c13_asm_static.json`
  - SHA-256: `830bb4b23e533ec9af19854a531c1f2c3552d3bce457566cc3cc158615606cf9`
- Capsule report: `analysis/phase4_c13_harvester.json`
  - SHA-256: `2daaf0c1e9719879f623b7f2cb441cea5154671be0912bbb72178d8a21ce0118`
- Matched live complement: `analysis/phase4_c13_harvester_live.json`
  - SHA-256: `09c17e19c2fc328eb0cf304d822557170ce03ffb4676a2b99d202d563893ce99`
- Machine contract: `config/phase4_c13_harvester.yaml`
  - SHA-256: `1925e21838fb0414bd63e2f9f3a7a37c71bea569919a240381b9163271e8cae7`
- Capsule manifest:
  `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/c13_GRAIN_HARVESTER/manifest.json`
  - SHA-256: `486be1c2d5ced63db19348806821b7079e27bf60cee3a63a80b2d2a72326adc7`
- Pristine executable SHA-256:
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`

Related: [[EXP_2026-07-30_phase4_c13_grain_harvester]], [[SYS_grain_harvester]].

## 2026-08-04 target-specific frontier closure

The earlier work was not repeated. This continuation addressed the two open
gameplay-frontier questions that prevented a bounded-exhaustion disposition:
the shared player-slot access frontier and the complete flag-access frontier
for `0x800A6590`.

### Capsule-first control

The retained v3 capsule
`Phase4/v3/c13_GRAIN_HARVESTER` was validated and queried before any live
replay. Its manifest SHA-256 is
`486be1c2d5ced63db19348806821b7079e27bf60cee3a63a80b2d2a72326adc7`.
The existing C probe reproduced 618 frame-boundary records, 1,854 verified
domain hashes, 342,405 changed runs, the state/flag transition at movie frame
83, and nine grain contacts paired with nine counter rises. Every observed
target was `-1` and every observed contact flag was `0xEA`. The regenerated
probe JSON SHA-256 was
`ddf562c17a2f0254d55aba067272745b0731f99a577eb3c064633c3f1aca714a`.

### C/static ASM frontier

The pristine executable is pinned by SHA-256
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
The original C ASM pass regenerated its 892-file / 100,425-instruction result
exactly (`830bb4b23e533ec9af19854a531c1f2c3552d3bce457566cc3cc158615606cf9`).
An expanded C hand-ASM pass found 59 readable exact flag accesses. That count
is deliberately not used as the completeness bound: the pristine-binary C
scanner found 80 exact accesses, and its independently reconciled hit set
matched exactly.

For the flag halfword, the conservative target-specific provenance pass began
with 435 possible indirect sites. C-established alignment, negative-index,
and finite-bound exclusions removed 235, leaving 200 sites for a fail-closed
row-specific classifier. The C classifier assigned all 200: 139 reads and 61
writes, split into 12 player-local and 188 cross-domain accesses, with zero
unexplained sites. The finite domains include actor records, the visual-object
pool, a bounded gameplay-state table, the contact-SFX table, and seed-handler
records. Their bounds or address congruence exclude aliasing the player flag.

The exact direct writer semantics remain one bit-`0x0080` setter
(`0x80051EB0`), two clearers (`0x8004A94C`, `0x8005B340`), and fourteen
read/modify/write sites whose masks preserve the bit. The shared signed state
slot at `0x800A657E` inherits the current player-slot proof: 192 conservative
residual sites, all classified, zero unexplained. This supersedes the stale
251-site metric in the earlier scorecard.

The one repository Python command in this continuation was only the existing
reconciliation wrapper between the C scanner and the prior census. It did no
ASM classification; the analysis and fail-closed residual discharge were C.

### Lifecycle and breadth disposition

- Pause excludes the gameplay state machine, so equip maintenance and the
  harvester tick are frozen while both player fields persist.
- A level/scene transition clears the `0x800A6500` player block, covering both
  `+0x7E` and `+0x90`; the harvester state is runtime-only rather than save
  persistence.
- A saturated 64-entry contact pool has a known allocator non-return edge.
  The retained valid-retail run peaks at 3/64, so this is a bounded shared-
  substrate failure mode rather than an unexplained C13 branch.
- Static breadth remains 15 active scene resources with six identical
  non-position harvester placements; the capsule supplies one natural live
  placement. This supports partial substantiation, not universal confirmation.

### Disposition

**C13 is substantiated partial and bounded-exhausted for valid-retail gameplay.**
The strict leftovers are exact render/animation/SPU identity, malformed or
corrupt pointer/asset behavior, and redundant natural-placement breadth. They
are either presentation-only or outside the declared retail bound and have
minimal return for Phase 4. No additional Interpreter movie is required to
move on. A future movie is justified only by a named presentation/audio
question or contradictory valid-retail behavior.

Machine-readable synthesis:
`analysis/phase4_c13_closure_20260804.json`.
