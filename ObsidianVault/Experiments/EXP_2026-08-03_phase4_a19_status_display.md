---
kind: experiment
id: EXP_2026-08-03_phase4_a19_status_display
date: 2026-08-03
status: complete
row: A19_status_display
classification: partial_high_value_bounded_exhausted
---

# Phase 4 A19: SELECT status display

## Result

A19 is substantiated partial and bounded-exhausted. The common SELECT gate,
pulse state machine, authoritative display sources, latching, hold/release
timing, rendering cadence, and non-pausing relationship to gameplay are closed.
No Interpreter movie or cold boot is required for the remaining bounds.

## Authority and escalation

- Pristine executable: `REBUILD/files/SCUS_942.88`, SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Retail cue SHA-256:
  `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`.
- Save anchor: `level01.sav`, SHA-256
  `5f29b29d2254be1928a01132c2cf6424d426c7ea1308ac709ea4fd737dbbe8a2`.
- DuckStation revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`.
- Running binary SHA-256:
  `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
- Isolated config: `/tmp/duckstation-debugger-phase4-a19-20260803-v2`, port
  `24419`. It was recreated and stopped through its owning launcher.

No A19-specific capsule existed. C01 and C02 were the relevant retained
capsules because both include authoritative grain and HUD-digit transitions.
Both manifests report complete, non-truncated, control-matched captures.
The C reader reconstructed 1,083 frame records with zero domain-hash mismatch.
Live escalation was limited to the missing SELECT hold/release domain.

## C-based pristine ASM result

The transient C census loaded the PS-X EXE directly at its declared load address
and found the pulse/input xrefs without modifying the image. Its output SHA-256
was `fe84c555ef3d960fd9697383bf0c51dfbf5429027ff3b9d7cb7d51e0d7c091de`.

The executed path is:

1. `0x800484B0 andi v0,a0,0x0001` tests SELECT.
2. `0x800484C4` skips the panel path when the result is zero.
3. Four calls to `0x800503FC` normalize pulses `0x800B0188`, `18C`, `190`,
   and `194`.
4. The gameplay caller invokes `0x800526F4` with `a0=0x40` at
   `0x8004F3E4/0x8004F3E8`.
5. The HUD renderer advances and draws lives, grain, health, FLIK, and applicable
   scene-specific panels.

`tools/phase4_a19_static.c` retains fixed instruction invariants and a direct
call census against the pristine executable. The compact semantic reconstruction
is in `src_re/status_display_80048138_800503fc_800526f4.c`.

## Capsule result

The C01 capsule reconstructed grain `10 -> 12`; the grain pulse changed 116
times and packed digits updated twice. The C02 capsule reconstructed grain
`49 -> 50`; packed digits changed from `0x0904` to `0x0005` at the HUD update
phase. These are frame-boundary proofs of authoritative-source-to-latch behavior,
not every-cycle proofs of SELECT.

Capsule-query output SHA-256:
`afbad70cccd85a50f4744f3111155ec74fc718705bc29caf69ec934be5e1f254`.

## Live timing and attribution

At the LEVEL01 anchor, controller injection reached the game's current-input
halfword after two display frames. The first active update produced pulse
`0x0080`: the SELECT normalizer wrote `0x0040`, then the HUD added `0x0040`.
All four pulses reached the stable held value `0x0440` after 32 display frames.

After release, sampled pulse values were:

| Display frames since release | Value |
|---:|---:|
| 1 | `0x0440` |
| 2 | `0x0480` |
| 4 | `0x04C0` |
| 8 | `0x0540` |
| 16 | `0x0640` |
| 32 | `0x0840` |
| 64 | `0x0C40` |
| 128 | `0x0000` |

The exact ASM bounds health/grain/FLIK reset to release tick 47 and lives to
tick 48 because the lives branch accepts `0x1000` for one additional update.

A bounded 48-display-frame write watch retained 150 events with no truncation.
It attributed the plateau normalization to the store reported at `0x8005042C`
and the four HUD writes to `0x800528E4`, `0x80052A24`, `0x80052BA0`, and
`0x80052F0C`. An execution watch retained 24 HUD entries with no truncation;
each captured `a0=0x40` and return address `0x8004F3EC`.

## Display-only control

The state was loaded twice. One run advanced 60 display frames without input;
the second held SELECT for the same interval. The following domains were
byte-identical between the two endpoints:

| Domain | SHA-256 in both runs |
|---|---|
| actor pool | `8fc315587a9bbda329de2f1c6a09abfdb21ab53e3df3fba9f013ad8565c4fa87` |
| contact pool | `ca72edaebe3867cf4371c6c895735e73979741765afec35072204a1acdb67eea` |
| plant region | `51a55140e40f04471d351b46accf3bba9d220f5067ee3d26775b578f6b5b1679` |
| camera | `cde7bd842ac2e11dd4c9167c55eacea4d0dd49ce7bb2cad1d3a0ec9016e905cb` |
| player block | `4d7002398bfd1fd8c64af4dd563cfa2bde4d3a2749d76ea85f3062c2d4264dba` |

Only the four HUD pulses differed (`0` in control, `0x0440` under SELECT).
Therefore the status display does not pause simulation.

## Corrections and residual bound

`0x800A6594` is the authoritative signed health field used by the status panel.
`0x800A7E2A` is an animation counter. Older HUD material that assigns
authoritative health to `0x800A7E2A` is superseded for this contract.

Remaining work is low-return and presentation-specific:

- pixel-perfect atlas provenance for every animated glyph frame;
- live screenshots for every special scene branch;
- story names for numeric progress sources in scenes 2, 7, and 11 through 15.

These do not leave the A19 input, timing, state, or gameplay relationship open.
Reopen only for a named special-scene panel, glyph-art dependency, or MOD hook
that intersects this path.

## Component-level exhaustion follow-up

A second pass tested the specific items named in the row rather than treating
the SELECT panel as one aggregate renderer. The retained B07 and A13 capsules
were queried first by compiled C. B07 reconstructed 324 frame boundaries and
972 RAM/VRAM/SPU hashes with zero mismatches; health changed `3 -> 4` at movie
frame 77 and its display latch followed at frame 107. All referenced A13
manifests are complete, untruncated, and exact against their independent
controls.

A compiled pristine-EXE reader recovered 54 relevant draw/upload calls from
`0x80052574..0x800526F4` and `0x800526F4..0x80053638`. Its output hash is
`0fe9a427c935d55fc93192d5d2393f90166569f5ac17083ad373a75cb3972791`.
The immutable executable hash remained
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

The missing renderer-value domain was then tested in an isolated DuckStation
session from hash-pinned `level01.sav`. The accepted session used config
`/tmp/duckstation-debugger-phase4-a19-components-20260803-v3`, port `24422`,
revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, and binary SHA-256
`ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
No movie was played. All mutations were volatile RAM counterfactuals and the
owned PID was stopped through the same config launcher.

Accepted matrices, all untruncated:

- Flik head: fixed tile `0x1C`; it does not participate in the HUD animation
  driver's upload list.
- Lives: `0,1,5,9` reached tile `0x1E` as variants `0,1,5,9`.
- Health: values `1,2,3,4` called the tile-`0x1D` uploader with frames
  `3,2,1,0`, proving `frame = 4-health`. Zero is closed statically as frame 4;
  it was not advanced live because it can trigger unrelated death logic.
- Grain: `0,9,10,49,50` produced `(0,0),(0,9),(1,0),(4,9),(5,0)`.
- FLIK: masks `0,1,2,4,8,5,15` independently switched tiles `0x10..0x13`
  between tinted and normal renderers.
- Selected seed power: zero suppressed the visible pair; selected-slot high
  nibbles `1,2,3,4` produced variants `4,5,5,0`. Unselected slot changes did
  not draw it.

The accepted component matrix output hash is
`e6f0c4af046963571395370794076c93c9220ec3e3e00b26fa86780ae8871dd3`;
the selected seed probe hash is
`467a5c75b10b41fa76610bdde1ac301ac29becb5943c431765637f09ea08ecb3`.
Two empty captures were explicitly rejected: one used the wrong
`build-release` binary, and one suppressed JSON with client `--quiet`. Neither
supports a game claim.

### Closure decision

A19 remains `partial_high_value_bounded_exhausted`, now with each named panel
item individually substantiated. Remaining work is pixel-perfect atlas mapping
or an inactive scene-specific `0x80052C00` branch. Those are low-return and do
not block moving to another row. No Interpreter-mode movie is required.
