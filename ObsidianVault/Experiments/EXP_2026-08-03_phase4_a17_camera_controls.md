---
title: "Phase 4 A17: manual camera controls"
date: 2026-08-03
status: confirmed
tags: [phase4, camera, controls, l1, r1, asm, duckstation]
---

# Phase 4 A17: manual camera controls

## Question and row boundary

A17 asks how L1 look/reset and R1 camera lock are admitted, parameterized, bounded,
and released. [[EXP_2026-08-03_phase4_e04_camera_system]] already owns the broader
camera record, telescope, cutscene, and setpiece-producer questions. This pass therefore
closed only the manual-control layer that is unique to A17.

No relevant retained trace capsule or deliberate L1/R1 movie existed. The named missing
domain was shoulder-input arbitration and release recurrence, so a narrow live run from
the hash-pinned `level01.sav` state was justified. No Interpreter movie was required.

## Identity and method

The static pass used C against the pristine ASM listing for `camera_follow_update`
`0x8004DF18..0x8004EA8C` (733 instructions), followed by a C xref census over 2,258
other ASM listings. The live pass used only Python as JSON-RPC transport; a C reducer
performed the sample comparison.

| Item | Pin |
|---|---|
| Retail cue | `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644` |
| Pristine executable | `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20` |
| `level01.sav` | `5f29b29d2254be1928a01132c2cf6424d426c7ea1308ac709ea4fd737dbbe8a2` |
| DuckStation revision | `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` (dirty fork; binary pinned below) |
| DuckStation binary | `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899` |
| Execution | `Interpreter`, isolated config `/tmp/abl-phase4-a17-20260803`, port `23517` |

The mounted and state-embedded media both reported `SCUS-94288` and the same retail
cue. Instrumentation was armed after every state load. The owned instance was stopped
through its config-scoped launcher.

## Confirmed control bindings

`camera_follow_update` reads active-high pad word `0x80082488`:

| Control | Mask | Decode |
|---|---:|---|
| L1 | `0x0400` | `0x8004DFDC` |
| R1 | `0x0800` | `0x8004E064` |

The shoulder selector is the word at `gp+0x488 = 0x80082220`: neutral writes `0`,
L1 writes `2`, and R1 writes `3`. This is the missing A17 input-mode binding.

L1 is tested first. The R1 body is reachable only when L1 is clear. A simultaneous
L1+R1 run hit the L1 body ten times and the R1 body zero times, and its camera metrics
matched L1 alone. There is no separate combined shoulder mode.

## L1 look/reset law

L1 selects:

| Parameter | Default L1 | L1+Up | L1+Down |
|---|---:|---:|---:|
| distance target `s3` | `600` | `600` | `600` |
| vertical offset `s0` | `0x3000` | `0x8000` | `0x1000` |
| look offset `s1` | `0` | `0` | `0x3000` |
| collision threshold `s4` | `160000` | `160000` | `160000` |
| countdown/gate `s5` | `8` | `8` | `8` |

Camera `+0x1E` approaches the selected distance in signed 32-unit steps per camera
update. It is a crossing recurrence rather than a saturating clamp: ten 30 Hz updates
moved `900 -> 580` around the nominal target `600`.

Camera `+0x18` is a 12-bit boom/look angle with shortest-arc quarter-step smoothing at
`0x8004E8F8..0x8004E928`. The controls produced `8 -> 5` for plain L1,
`8 -> 19` for L1+Up, and `8 -> 4035` for L1+Down. The last value is normal 12-bit
wrap while approaching through zero, not an unbounded angle.

## R1 lock and lifetime

R1 selects distance target `1400`, vertical offset `0x6000`, and scaled squared leash
threshold `1,960,000`. It passes angular steps `a0=a1=0` to the common `+0x20`
heading writer, so the camera follow heading is frozen while R1 is sampled. The leash
comparison is:

`((player_x-camera_x)>>5)^2 + ((player_y-camera_y)>>5)^2 + ((player_z-camera_z)>>5)^2 < 1,960,000`

That corresponds to a world-space radius of `44,800` units. A 20-frame R1 run moved
distance `900 -> 1220`; a held R1+Up run moved Flik by 14,166 Manhattan units while
camera heading stayed unchanged.

R1 has no hidden post-release latch. The next ordinary update stops selecting the R1
branch. After 20 held frames plus 24 released frames, distance returned to `900` and
the control word was normal `0x0001`. Boom remained `41` after peaking at `47`, which
is residual geometry smoothing, not continued lock state.

## Corrected `+0x22` interpretation

E04 provisionally described observed values such as `0x0A01` and `0x0Bxx` as camera
submodes. Pristine control flow disproves that stable-enum interpretation:

- `0x8004DF40..0x8004DF5C` extracts the signed high byte and decrements it when nonzero.
- L1 writes control bit `0x0800` at `0x8004E01C` and refreshes the associated countdown.
- The low byte remained the normal gameplay value `0x01` in every A17 trial.
- Held L1 reached `0x0F01`; release returned it to `0x0001`.

Thus `+0x22` is a low-byte active/control value plus high-byte countdown/control bits,
not the unbound stable camera-mode enum that the old row text expected.

## Collision and special-camera boundary

Two collision layers are visible in pristine code:

1. `0x8004E3B0` calls `camera_region_query 0x800376A0` while constructing the target.
2. `0x8004E628` calls a secondary candidate solver only when the scaled player-camera
   distance is below `s4` and `s5 == 0`. Candidate deltas must each be below `1024` in
   absolute value; otherwise `0x8004E6A8..0x8004E6C8` restores the old target.

L1's refreshed nonzero `s5` bypasses the secondary candidate solver, while the earlier
region query still applies. R1 uses `s5=0` and the large leash bound.

The C xref census found both calls to `camera_follow_update` in the normal per-frame
dispatcher `FUNC_8004EA8C`. The shared special selector `0x800824DC` is read and written
by separate gameplay/setpiece paths. Live telescope/cutscene producer enumeration is
therefore still E04 work; it is not an unclosed duplicate inside A17.

## Observation, inference, and causal confirmation

**Observation:** neutral, L1, R1, both, L1+Up, L1+Down, and two release trials produced
the field trajectories recorded in `analysis/phase4_a17_camera_controls.json`. All
cited access and execution traces reported `truncated=false`.

**Static inference:** the constants loaded into `s0..s5` are the requested manual
camera profile, and the distance/collision branches describe its recurrence and bounds.

**Causal confirmation:** execTrace tied L1 and R1 inputs to their mutually exclusive
branch bodies and captured their registers at the common writer. AccessLog attributed
the resulting `+0x18/+0x1E/+0x20/+0x22` writes to the exact pristine PCs. State reset
between trials ruled out inherited camera state.

## Closure

**A17 is bounded-exhausted and Full.** Its unique input/state binding, priority,
look presets, R1 lock, release lifetime, recurrence, collision/leash gates, and normal
producer boundary are closed. E04 remains Partial for live telescope/cutscene/setpiece
camera behavior and the broader `0x800824DC` semantic reconciliation.

## Transient evidence and reproduction

Transient files remain under `/tmp`; their hashes make the cited run identifiable:

| Artifact | SHA-256 |
|---|---|
| C ASM scanner source | `f1101e7131cadedff4d8810243bb38510ce6e6a05b7c724c6d3632b9b85f3f8f` |
| C ASM scanner binary | `8b444d65959a20ccdaf51ea91c633e4a2836b2420770c9f3fccb14831c24720e` |
| ASM scan output | `f374be65486677976c598537db3502298cb8b3b007f9d5b4d33f312c98107bc0` |
| C xref scanner source | `10b01663006f670eea8f2ad46fb973b118e1f3affe185f4e3d24ba713c1450f1` |
| C xref scanner binary | `d1e9e5cc85892a8a9afc111fc256c0038492172fc2dd6bd8bab71cb5175ac4e8` |
| xref output | `c05e20111491289bc0505de6b8a09dfd7baf3ee345d3cc57f8adcf93f1c9cec5` |
| Python RPC transport | `476590bfeb3b96108e2d4866d29a779be306b2bcf10fbe2f9c42450857772f7f` |
| C reducer source | `98cbcdafd494e60ffa3b76fa86fdb69601bfd1e59c959f0c7b2835add84c8931` |
| C reducer binary | `1c63ed98c392e64bee74b6d68d9ac333de216b2f13c2f41dca7862440ce1c3ee` |
| raw samples | `e4e01430a517a85f29694913d62119e60411ed22b5367aaea96e9b095b2db26d` |
| raw traces | `e9436b20ee76f43c59f4f007f65676f3bac27acd2535b626eba099c1f9bdee7a` |
| C-reduced metrics | `4759edf344e957c1bf2bcf65c76027a5146e37b68a110ad0485e214d795b6e39` |

Core reproduction commands were:

```bash
gcc -O2 -Wall -Wextra -std=c11 /tmp/phase4_a17_asm_scan_v3.c -o /tmp/phase4_a17_asm_scan_v4
/tmp/phase4_a17_asm_scan_v4
gcc -O2 -Wall -Wextra -std=c11 /tmp/phase4_a17_xref_scan.c -o /tmp/phase4_a17_xref_scan
/tmp/phase4_a17_xref_scan
python3 /tmp/phase4_a17_live_transport.py
gcc -O2 -Wall -Wextra -std=c11 /tmp/phase4_a17_reduce.c -o /tmp/phase4_a17_reduce
/tmp/phase4_a17_reduce /tmp/phase4_a17_samples.csv
```

Machine-readable result: `analysis/phase4_a17_camera_controls.json`.

