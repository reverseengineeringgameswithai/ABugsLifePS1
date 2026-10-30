---
kind: experiment
id: EXP_2026_08_02_phase4_b03_dandelion_capsule
name: Phase 4 B03 dandelion retained-capsule narrowing
status: complete
date: 2026-08-02
confidence: high
source_state: original_game
systems:
  - B03_dandelion_glide
evidence:
  - analysis/phase4_b03_dandelion_capsule.json
  - tools/phase4_b03_capsule_probe.c
---

# Phase 4 B03 dandelion retained-capsule narrowing

## Question and boundary

Start the unfinished B03 dandelion-glide row by using the accepted Phase 4
acceleration lane before requesting another live replay. The bounded questions were:

1. Does seed_plant_dandelion_handler execute in the retained updraft fixture?
2. What player-state transition aligns with its exceptional path?
3. Does the previously identified contact-pool kind 13 carry this interaction?

This is save-state and frame-boundary capsule evidence. It is not a cold-boot oracle,
an instruction-exact write trace, or closure of steering, attachment, release, landing,
and cross-level behavior.

## Evidence identity

- Capsule: ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B03_dandelion_updraft
- Registry receipt: analysis/phase4_trace_capsule_set.json
- Manifest SHA-256: d97ab00a0abd67881d0fdc91dbc82a0c0a0d503bd87ea544b8d32ed865a9d14b
- Capsule tree SHA-256: 226be1ba5d41ede26aeeffbe7b083c0196313b7f74f8094d3c90345c96d2ee15
- Movie SHA-256: e0a278a5fe546d93b81a98f1c1c8f67d172e567fa03f02d6bfde9860ab524188
- Start-state SHA-256: b9abf6449bb16c77ac4830c8fc5574133ed8af44002a96f9ad0a08ccc783bde0
- Preserved DuckStation binary SHA-256: 55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8
- Registry control_match: true

The C reader parsed all 17 chunks exactly, reconstructed 998 frame boundaries, and
checked all 2,994 embedded RAM/VRAM/SPU SHA-256 values. No reconstruction mismatch,
truncation, unknown record, or trailing parse error occurred. The manifest's 997 frame
count is the input/advance span; the chunk stream contains boundaries movie 0 through
997, including the terminal post-input boundary after the 997 movie rows (0 through
996). The distinction is retained rather than silently normalised.

## C acceleration method

The reusable reader is tools/phase4_b03_capsule_probe.c. It uses libzstd directly,
parses DSTCAP01 records without Python, reconstructs all three domains, validates each
embedded domain hash, reads the player block, walks the 64 by 0x38 contact pool, and
correlates frame-level RAM with passive block-flow counts.

Reproduction:

    cc -O2 -std=c11 -Wall -Wextra -Werror \
      tools/phase4_b03_capsule_probe.c \
      -o /tmp/phase4_b03_capsule_probe -lzstd -lcrypto
    /tmp/phase4_b03_capsule_probe \
      ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B03_dandelion_updraft \
      > /tmp/phase4_b03_capsule_probe.json

The compact retained result is analysis/phase4_b03_dandelion_capsule.json.

## Observations

### Handler polling and the single exceptional path

The passive block flow records seed_plant_dandelion_handler entry 0x8005C818 on 455
frame boundaries. The normal blocks 0x8005C898 and 0x8005C8C0 also appear 455 times,
while 0x8005C880 appears 454 times. Trigger-only blocks 0x8005C820, 0x8005C834,
0x8005C83C, and 0x8005C87C each appear exactly once.

The only seven-block handler sample is movie frame 180, emulator frame 61596, cycle
34875306551. Static decode of the already retained hand assembly makes the state stores
unambiguous:

- 0x8005C840 loads -4096; 0x8005C848 stores it to player velocity_y at 0x800A6530.
- 0x8005C84C loads 5; it is not a store.
- 0x8005C854 stores mode 5 to 0x800A6580.
- 0x8005C860 and 0x8005C868 clear 0x800A6582 and 0x800A6584.
- 0x8005C870 stores 3 to 0x800A6588.

This corrects the older src_re/brown_seed_plants.c comment that called 0x8005C84C an
attachment write.

### Exact frame-boundary motion

- Movie 178: Y -88933, velocity_y +1856, mode 2. Flik is descending.
- Movie 180 trigger: Y -87689, velocity_y -4096, mode 5.
- Movie 182: Y -91529, velocity_y -3840, mode 6.
- Movie 180 through 242: every two movie frames, velocity_y increases by exactly 256
  and player delta-Y equals the new velocity_y. All 31 updates satisfy both equalities.
- Apex: Y -118409 at movie 210 through 212, exactly 30,720 units above trigger Y.
- Movie 244: collision clamps Y to -84122, contact flags become 0x0101, velocity_y is
  -30, and mode is still 6.
- Movie 246: mode returns to 0.

Observation: the handler supplies a one-shot upward impulse and the shared airborne
state immediately owns the ballistic arc. Mode 5 lasts only movie 180 through 181 in
this event. No sustained handler-owned sink rate is present in this segment.

### Kind-13 contact-pool negative

At every one of the 998 reconstructed boundaries, the C walker finds zero records with
action_id 13 and a nonzero low lifetime byte in the 64-slot contact pool at 0x800B0D18.
The handler still takes its exceptional path and changes Flik's motion.

Observation: the kind-13 descriptor remains visually identified as dandelion artwork,
but it is not the live contact-pool carrier for this captured plant interaction. The
stationary plant type-8 handler and the kind-13 contact descriptor must remain separate
addressing and behavior domains.

## Inference

For this fixture, the row's updraft/lift component is best modelled as a one-shot
velocity replacement (-4096) followed by the common +256 gravity integrator, not as a
per-frame dandelion-handler lift. The two-frame mode-5 transition may be an entry state,
but this capsule alone does not establish semantic attachment or what visual object is
carried.

## Not proved

- The precise object pointer and overlap values passed into the trigger call.
- Instruction-level runtime attribution of each player-field store.
- Steering, sink rate during an actual sustained glide, release/drop, or landing rules.
- Propeller-combination behavior outside this single recorded event.
- Cold-boot and cross-level breadth.

## Next experiment

Use the named movie-180 anchor only for the missing exact-attribution domain. In an
isolated DuckStation instance, arm execution/access capture before the trigger, confirm
the 0x8005C848 and 0x8005C854 stores, retain the plant-slot pointer, and compare neutral,
steering, and release inputs against a no-trigger control. Re-arm all instrumentation
after loading the state and preserve the result as a declarative scenario.

## C static ASM continuation

### Method

The follow-up did not use the capsule or Python as its analysis engine. The C11 program
`tools/phase4_b03_asm_static.c` parsed the repository's existing
`asm/hand_written` corpus directly:

    cc -O2 -std=c11 -Wall -Wextra -Werror \
      tools/phase4_b03_asm_static.c \
      -o /tmp/phase4_b03_asm_static
    /tmp/phase4_b03_asm_static asm/hand_written \
      > analysis/phase4_b03_dandelion_static.json

The run covered 892 files and 100,425 instructions. It decodes textual instructions and
raw J/JAL/branch words, accounts for call delay-slot arguments, propagates constants and
absolute addresses, computes entry reachability, and performs a corpus-wide direct
access census for `0x800A659E`. All six dandelion-specific derived checks passed.

### Selected-slot trigger

`plant_behavior_walker 0x8005BFBC` calls `player_sector_lookup 0x80038E48`, subtracts
one into `s4`, initializes `s5` as the current 0x30-byte plant-slot index, and fixes
`fp = 0x800A6500`. The selector returns zero unless player contact `0x800A6582 >= 256`
and the selected collision-sector field passes its `>=104` threshold. Therefore the
dandelion condition `s4 == s5` means that this plant is the player-selected slot.

The walker dispatches only mature slots (`extra_state & 4`). The dandelion body adds
`extra_state & 2` before taking its primary trigger path.

### Primary path is detach plus lift

At `0x8005C834` the handler calls `0x80046CAC`. Static analysis of that callee and its
nested `0x80041A74` proves it is a reset/detach operation:

- If `0x800A655C > 0`, resolve `0x8009FD80 + offset`, clear actor fields
  `+0x1C/+0x20/+0x24`, and clear actor flag `0x40` at `+0x5C`.
- Clear indexed state selected by `0x800A658C`.
- Clear `0x800A657A`, `0x800A655C`, and `0x800A65A3`.

The helper consumes no positional argument. It cannot be the previously claimed
attachment writer. After detachment, the handler writes:

- `0x800A6530 = -4096` at `0x8005C848`.
- `0x800A6580 = 5` at `0x8005C854`.
- `0x800A6582 = 0` and `0x800A6584 = 0`.
- `0x800A6588 = 3`.
- Positional sound `15` through `play_sound`, centered on `slot+8`.

The capsule independently observes these frame-boundary values, while the static pass
establishes the controlling predicate and callee semantics.

### Dandelion-to-propeller bridge

Outside the primary trigger, dandelion temporarily mutates `slot->y -= 0x7400`, calls
the three-axis helper `0x80052508(slot+8, player, 40)`, then restores
`slot->y += 0x7400`. The helper computes:

    ((dx >> 8)^2 + (dy >> 8)^2 + (dz >> 8)^2) < 40^2

Inside that quantized sphere, and only when harvester flag `0x80` is clear, dandelion
writes interaction latch `0x800A659E = 11`.

The propeller handler provides the direct consumer:

- X/Z proximity uses `0x800524B8(slot+8, player, 40)`.
- Harvester flag `0x80` must be clear and player contact `0x800A6582` must be zero.
- Let `dy = plant_y - player_y`. Values `12289..40959` are accepted directly.
- The inner band `4097..12288` is accepted only when the latch is `11`.
- Accepted updates detach carried state, write mode `5` and action `13`, apply
  `velocity_y -= 512`, and clamp values below `-3072` to `-3072`.
- If the latch is `12`, propeller clears it after the detach call.

This is the first static mechanism linking the row's dandelion and propeller halves.
It does not by itself prove the visual carrier or sustained steering behavior.

### Latch frontier and shared-code correction

The direct absolute `0x800A659E` census finds 15 accesses. Its only direct nonzero
literal writers are `11` from dandelion and `12` from
`player_contact_response 0x80047A58`. Propeller reads both states; player update,
transition, respawn, and other lifecycle paths clear the latch. Indirect and overlay
accesses remain outside this direct retained-ASM census.

CFG reachability also corrects the function boundary: `0x8005C8D4..0x8005C914` is not
reachable from dandelion entry because dandelion jumps to `0x8005CCE8` after restoring
Y. The mine handler branches backward into `0x8005C8D4`. That suffix is shared plant
animation code, not dandelion behavior.

### Runtime evidence gate

No movie was needed for this static pass. If the remaining steering/carrier/latch-timing
questions require `execTrace`, the cached-Interpreter B03 recording must not be reused:
the recent observer-mode discovery predicts desynchronization. Record a new movie in
Interpreter mode spanning sustained travel, propeller re-entry, steering, release, and
landing, then trace only the named remaining branches.

### Source status

`src_re/dandelion_glide_static_8005c818.c` is documentation-grade semantic C for the
reachable dandelion path, detach helper, quantized proximity laws, and propeller bridge.
It advances source closure but is not byte-matched and does not claim the full glide
lifecycle.

## Links

[[Phase 4 - Solve Every Gameplay and Engine Subsystem]] |
[[Phase 4 - Acceleration Tooling Strategy]] |
[[Whole-Game Mechanics Baseline]] |
[[SYS_contact_objects_and_drops]]
