---
node_type: experiment
title: "EXP - Training ending trigger field and exact green footprint"
date: 2026-08-02
status: confirmed_training_only
result: exact_two_triangle_walkable_footprint
tags: [training, ending-trigger, collision-sector, visualization, duckstation]
canon:
  - SYS_training_ending_trigger_field
---

# Training ending trigger field investigation

## Result

Training's walk-here ending is associated with runtime collision sector `24`,
region code `3`, in scene `17`. The accurate light-green marker is the complete
two-triangle walkable slope belonging to that sector. The earlier three-vertex
marker covered only half and is superseded by the four-vertex version.

This result is **Training-only**. The later multi-level extrapolation is excluded
from this finding because its visuals were not accurate.

## Identity and anchor

- Retail game: `SCUS-94288`, Disney-Pixar A Bug's Life.
- Retail BIN SHA-256:
  `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`.
- Retail CUE SHA-256:
  `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`.
- Fixture: `level01_ending_for_exit`, SHA-256
  `6ca386b9bb5cf260a8f5f7e936ebde59aa4a39e309920519be0fb302310c4cf6`.
- Fixture state: scene `17`; Flik XYZ `(21466, -23763, 273466)`;
  `[Flik+0x82]=1`; current sector `16`, code `0`; transition latch
  `[0x800823A0]=0`.
- Winning record exposed at the anchor: sector `24`, code `3`, origin
  `(480, -24096, 268736)`, collision pointer `0x800D4988`.
- Isolated debugger profile: `/tmp/abl-ending-hitbox-full`, WebSocket port
  `23773`; the profile-owned process was stopped through its launcher.
- DuckStation executable SHA-256:
  `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`.

The save loaded against the verified retail image with disc validation enabled.
The isolated memory card differed from the card serialized in the state, so
DuckStation marked the session with `MemoryCardMismatch`; no claim here depends
on memory-card contents.

## Observation and reconstruction

The sector catalog found sector `24` as the endpoint's nonzero region-code
record. Following the natural route changes the player's collision classification
to that sector and produces the ending fade.

Sector `24` supplies four corner coordinates for its two-triangle slope:

| Vertex | Local XYZ | Native world XYZ | Draw-only lifted XYZ |
|---|---:|---:|---:|
| A | `(1, -80, 258)` | `(512, -26656, 276992)` | `(512, -26784, 276992)` |
| B | `(1, 211, 1060)` | `(512, -17344, 302656)` | `(512, -17472, 302656)` |
| C | `(1159, -80, 258)` | `(37568, -26656, 276992)` | `(37568, -26784, 276992)` |
| D | `(1159, 211, 1060)` | `(37568, -17344, 302656)` | `(37568, -17472, 302656)` |

The native values follow directly from
`world = (480, -24096, 268736) + local * 32`. The `-128` Y adjustment in the
last column is an anti-z-fighting display offset, not an expansion or movement
of the trigger.

## Diagnostic renderer

The temporary renderer was deliberately scene-specific:

- gate on runtime scene ID `17`;
- hook the gameplay `DrawOTag` call at `0x80064618`;
- accept only the gameplay ordering table at `[0x8008240C] + 0x14E0`;
- project the four world points using the current camera at scratchpad
  `0x1F800374/378/37C`;
- prepend one opaque flat quad to ordering-table bucket `+0x0CA4`;
- use GP0 word `0x2890EE90` for light green.

The first implementation rendered A/B/C as a single triangle. Adding D and
changing the packet from a three-vertex polygon to a four-vertex polygon is the
material correction that made the displayed marker cover the full accepted
Training footprint.

## Build and behavioral evidence

- Corrected ASM SHA-256:
  `e11b4c7560b74d1e72597ccda0c565f60bf4d38ce3b2f8aa5b5e5e90b64ab2a5`.
- Corrected patched EXE SHA-256:
  `98acecdb6ef41e9ea837f149a0529e6951b739e4081a7c50866abb6e419093b9`.
- Build manifest SHA-256:
  `15472e9d0f6ebbf4d4adcdc02b45c3c5b0012da00f87ea54d42ff2d2edfdfbb0`.
- Diagnostic BIN SHA-256:
  `b743528341d347f5cda82a10dfa1b49cd595472c85eda307910546e45fdb6643`.
- Diagnostic CUE SHA-256:
  `25e99f08e84a8b043ebea46d91bb0fcd4056adf4fea62df9a99ed7f9e82c66f6`.
- Accepted displayed-frame capture SHA-256:
  `da5867f9e9762c92e1eef13ce063d636e0bd00e84792cc768f8d87f073586bb9`.
- Cold-boot input movie: `movies/go_to_end/LEVEL00-Training.movie.json`,
  SHA-256
  `b4bad8a7650b9cc35657718f5a0857147b20fe75a0707c0b2e7413ea3af3bd7e`.
- Cold-boot frame `8300` capture SHA-256:
  `a2405873424e24513b4a8cb068f0fefcd9372547a335ab86ecf5819f75973ca3`.

The rebuilt disc cold-booted as `SCUS-94288`; the recorded Training movie reached
the endpoint with the corrected marker resident. Runtime readback confirmed the
on-disc hook at `0x80064618` and the complete renderer body at `0x8007F174`.

Transient binaries, screenshots, save states, logs, and disc images remain
outside the Vault/repository. Only their paths and hashes are retained here.

## Evidence boundary and future reuse

Observed: fixture identity/state, scene ID, sector record, surface coordinates,
visible four-corner marker, cold boot, and on-disc code readback.

Confirmed for Training: entering the sector-24 endpoint through the natural
route ends the level, and the two-triangle slope is the accepted walkable visual
footprint.

Not claimed: a vertically bounded 3D trigger volume, universal meaning for
region code `3`, or validity of the later Anthill/Tunnels/Cliffside/Riverside
coordinates. Reuse elsewhere requires a new natural-route sector transition and
complete native-surface reconstruction.

## Related

[[SYS_training_ending_trigger_field]] | [[Level_Goal_and_Exit_Trigger_Matrix]] |
[[Gameplay_-_Warp_and_Level_Transition]]
