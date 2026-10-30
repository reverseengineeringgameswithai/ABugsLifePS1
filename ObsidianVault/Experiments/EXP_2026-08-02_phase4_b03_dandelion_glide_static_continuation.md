---
type: experiment
phase: 4
row: B03
date: 2026-08-02
status: partial-runtime-gate
method: c-static-asm
---

# Phase 4 B03 dandelion glide static continuation

## Scope

Continue B03 without replaying DuckStation. This pass asks whether sustained
glide, steering, release/landing, and latch timing can be resolved from retained
resident ASM. It follows the Phase 4 acceleration rule: use retained static and
capsule evidence first, then escalate only for a named runtime-only gap.

No DuckStation instance, movie playback, save state, or `execTrace` observer was
used.

## C method

The C11 analyzer performs textual MIPS constant propagation over all retained
hand-written ASM. It seeds the documented
`player_update_80048138(a0 = 0x800A6500)` ABI, records player-field xrefs, and
emits local instruction windows.

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  tools/phase4_b03_glide_state_static.c \
  -o /tmp/phase4_b03_glide_state_static
/tmp/phase4_b03_glide_state_static asm/hand_written \
  > analysis/phase4_b03_glide_state_static.json
```

The run scanned 892 files and 100,425 instructions. It found 27 `air_state`, 34
`grounded`, 52 `velocity_y`, 29 `velocity_x`, 29 `velocity_z`, and 19
`plant_latch` candidate xrefs. Conclusions below use locally checked instruction
windows and CFG order, not raw linear-propagation candidates by themselves.

## Static observations

### Sustained glide

- `0x8005C848` writes `VY = -4096` and `0x8005C854` writes state `5`.
- `0x8005C8BC` conditionally writes latch `11` after the elevated quantized XYZ
  radius-40 test.
- `0x800486DC` checks latch `11` once per player update.
- While airborne, `0x80048704..0x80048728` computes
  `VY = (VY < 350) ? VY + 256 : 350` and jumps to `0x80048D90`.
- This skips ordinary state `5 -> 6` and the normal gravity cap of `4096`. The
  latch-11 mechanic is a sustained shallow descent capped at `+350`, not
  altitude hold.
- From `-4096`, the negative-velocity portion sums to 30,720 units of rise. The
  terminal transition is `256 -> 512 -> 350` because comparison occurs before
  addition.
- Without latch `11`, state `5` advances to `6` at `0x80048D64` and ordinary
  `+256` gravity applies. That is the ballistic launch seen in the retained
  capsule.

### Steering

- Both vertical paths converge at `0x80048D90`.
- The shared input/motion tail then stores `VX` at `0x80049524` and `VZ` at
  `0x80049540`.
- Glide therefore retains ordinary horizontal input processing.
- Static reachability does not measure input gain, turn response, or route
  usefulness. Those remain behavioral facts.

### Release and landing

- `0x80046CAC` clears carrier offset `0x800A655C`, indexed binding
  `0x800A657A`, and carrier flag `0x800A65A3` before the dandelion impulse.
- No dandelion-handler input test or manual release branch exists.
- If latch `11` is active and grounded is nonzero, `0x80048700` clears the
  latch and continues through ordinary landing handling.
- With ordinary no-Cross input, the grounded path writes state `0` at
  `0x80048D10`. Cross can enter existing jump/butt-slam logic; it is not a
  dandelion release.
- Release is automatic on grounding or a forced reset/transition, not a
  player-controlled drop.

### Latch lifetime and tick order

- The scheduler calls player update at `0x8004EFD8` and plant walker later at
  `0x8004F010`.
- A latch written by the dandelion walker first affects motion next gameplay
  tick.
- Collision grounding is produced by the player integrator after the latch
  check. A newly detected landing clears latch `11` on the following tick.
- The ungrounded latch-11 path never clears the latch.
- Direct retained-ASM clears also occur in forced action-8 cleanup, resident
  level transition, and respawn/reset paths.
- Latch `12` is separate: contact writes it, player update caps positive `VY`
  at `512`, and accepted propeller activation clears `12`. Propeller does not
  clear latch `11`, preserving the dandelion-to-propeller bridge.

## Row delta

Static ASM now establishes the sustained-glide law, steering reachability,
automatic release, grounding-driven landing transition, and latch `11/12`
ownership/tick order.

B03 remains Partial only for:

- a reproduction that satisfies the latch-11 sphere gate rather than producing
  only the state-5/state-6 ballistic launch;
- measured directional response during latch-11 glide;
- visual carrier presentation;
- controlled landing on the intended route;
- exact movie-frame write/use/ground/clear alignment and route breadth.

## Runtime gate

The next evidence requires a newly recorded Interpreter-mode movie containing a
confirmed latch-11 activation, neutral glide, directional steering, and a
controlled landing. Do not replay a cached Interpreter-mode movie with
`execTrace` because that combination can desynchronize.

Use a narrow window over:

- `0x8005C8BC`, latch-11 write;
- `0x800486DC..0x80048728`, glide consumption and VY;
- `0x80049524` and `0x80049540`, steering stores;
- `0x800A6582`, grounding attribution;
- `0x80048700`, latch clear.

## Evidence hashes

```text
d39c449b4b98a79710e96e24bd3ad4514756fea365c75348cbfcc92294f47c5c  tools/phase4_b03_glide_state_static.c
c75537acd752a76d0cac45280b32f7e12fb4e0088dca373df0e6ae098eeb1e7f  analysis/phase4_b03_glide_state_static.json
f50038e52d548c44f59f8ac09ca17559e441be749d06dcf5b758cf6f13f38bdc  asm/hand_written/80048138_player_vertical_update.s
995442d8eb48423d488ff6c5036aef961b10f6ff40c007b4e96e1328e854dff2  asm/hand_written/8005c818_seed_plant_dandelion_handler.s
f11ef7dfbcd3e3f7e3eac3e16b87f0c2633b0289d4485d9d99bdcd738f8e437b  asm/hand_written/8005c258_seed_plant_propeller_handler.s
63a30afadc1ab0cbcea2807414b742041b7b2b4cf81dc8a605a9dc0e4a08aac4  asm/hand_written/80046cac_sub_80046cac.s
57d38485c2a7821f02b07e794be6960b2b206d3840ac1991d8198fd6d354561d  asm/hand_written/8004ecd4_gameplay_state_machine.s
```

## Related

- [[EXP_2026-08-02_phase4_b03_dandelion_capsule]]
- `analysis/phase4_b03_dandelion_static.json`
- `src_re/dandelion_glide_static_8005c818.c`
- `src_re/dandelion_glide_state_80048138.c`
