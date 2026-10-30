---
kind: system
id: SYS_status_display
name: SELECT Status Display
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - 0x80048138
  - 0x800503FC
  - 0x800526F4
memory:
  - 0x800B0188
  - 0x800B018C
  - 0x800B0190
  - 0x800B0194
evidence:
  - EXP_2026-08-03_phase4_a19_status_display
---

# SELECT status display

## Canon contract

The gameplay controller bit for `SELECT` is `0x0001`. At `0x800484B0`, the
resident player update tests that bit. While it is held, it calls the shared
pulse normalizer at `0x800503FC` for four halfwords:

| Pulse | Panel source |
|---|---|
| `0x800B0188` | lives byte `0x800A65A0`, latched at `0x800B018A` |
| `0x800B018C` | grain byte `0x800A65A1`, packed digits at `0x800B018E` |
| `0x800B0190` | true health `0x800A6594`, latched at `0x800B0192` |
| `0x800B0194` | FLIK bits `0x800A65A2` and scene-specific status icons |

`0x800A7E2A` is a free-running health/HUD animation counter, not the
authoritative health source.

## Hold and release law

The normalizer mirrors values at or above `0x0C00`, clamps the middle phase to
`0x0400`, and changes zero to `0x0040`. The gameplay HUD renderer then adds
`0x0040` on each 30 Hz update. Consequently, a sustained hold is observed at a
frame boundary as `0x0440`: the input path clamps to `0x0400`, then the renderer
advances it once.

At the LEVEL01 anchor, the four panels reach the sustained value 32 display
frames after injection. Release removes the clamp. The pulses then advance
through the mirrored/retraction phase and wrap to zero. The lives pulse accepts
`0x1000` for one extra 30 Hz update; health, grain, and FLIK reset as they reach
`0x1000`.

The latches refresh while the panel is held, so it is a live status view rather
than a snapshot.

## Simulation relationship

The status display does not pause gameplay. A phase-matched 60-display-frame
control and SELECT run produced identical actor, contact, plant, camera, and
player-state hashes. Only the four HUD pulse halfwords differed.

## Scope

The common path is resident and shared across gameplay scenes. Scene-specific
branches reuse the FLIK/status pulse for additional icons or progress meters.
The exact story labels of some scene-specific numeric sources and exhaustive
pixel-atlas provenance remain outside this behavioral contract.

## Component closure (2026-08-03)

The shared SELECT panel is now resolved at item level:

- Flik's head is fixed glyph tile `0x1C` at return address `0x80052898`.
- Lives uses source `0x800A65A0`, latch `0x800B018A`, and tile `0x1E`; tested
  values `0,1,5,9` were forwarded unchanged as digit variants.
- Health uses authoritative byte `0x800A6594`, latch `0x800B0192`, tile
  `0x1D`, and upload frame `4-health`. Runtime covered `1..4`; pristine ASM
  closes zero as frame 4 without advancing death logic. B07 naturally proves
  the `3 -> 4` source and delayed latch transition.
- Grain uses byte `0x800A65A1` and packed latch `0x800B018E`; its low byte is
  tens and high byte is ones. `0,9,10,49,50` produced the exact digit pairs.
- FLIK byte `0x800A65A2` maps bits `0..3` to tiles `0x10..0x13`. Every set
  bit selects the normal glyph renderer; every clear bit selects the tinted
  renderer. None, each singleton, mixed `0x5`, and all `0xF` were traced.
- The visible selected seed-power pair is absent at zero. In the level01
  fixture, selected slot `0x800A6598` high nibbles `1,2,3,4` produced variants
  `4,5,5,0`; changes to the three unselected slots did not draw the pair.

The animation driver at `0x80052574` advances the four FLIK tiles and related
HUD resources independently of the fixed Flik-head glyph. The inactive
`0x80052C00` presentation branch and pixel-perfect atlas archaeology are not
needed to explain the row's operator-visible mechanic. A19 is therefore
**partial, high-value bounded-exhausted**, and no Interpreter movie is required.
