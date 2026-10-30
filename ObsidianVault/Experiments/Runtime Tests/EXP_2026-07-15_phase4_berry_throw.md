---
kind: experiment
id: EXP_2026-07-15_phase4_berry_throw
name: Phase 4 berry-throw campaign
status: complete
date: 2026-07-15
confidence: confirmed
---

# Phase 4 berry-throw campaign

## Question

What exact pristine law admits and dispatches an ordinary berry throw, how do
all five equipped selectors aim and allocate contact records, and how do straight
and homing records update, retire, pause, reset, and generalize across gameplay?

## Setup and identity

- Generator `tools/phase4_berry_throw.py`, SHA-256
  `a61b75d620e8b1aa8a1a1ab0c43539cf0a334a10b2656e2eb10d0329067f82eb`.
- Evidence `analysis/phase4_berry_throw.json`, SHA-256
  `83e4b56c0290de42e6a00e0831299bc255fe24be2bb6d39b2a71c2448f66b57d`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Cold-boot LEVEL01 movie SHA-256
  `bfedc0d0f4828998fc598257b35ad090180ad6cb01ea317bc40229f977dc40fb`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  release-binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and retained 203-method RPC manifest.

The retained run used fresh absolute config
`/tmp/abl-phase4-i9-a08-cold-first-2`, loopback port 26325, an ephemeral token,
and owned PID 289484. It verified mounted SCUS-94288 CUE/BIN hashes, inspected
and exact-matched all 23 selected pristine saves before loading, and stopped
only that PID. Regeneration requires new isolation values:

`python3 tools/phase4_berry_throw.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

ALLMODS and `homingberry_worm.sav` were excluded as original-game authority.
Cold boot ran before every save-state inspection/load, from an explicitly paused
launcher baseline. A second fresh config replay reproduced the same semantic
observations and retained the evidence artifact byte-for-byte at the SHA above.

## Static diagnosis and input controls

The static census reread and hashed the pinned executable regions for the player
gate, aim helper, full dispatch, allocator, projectile updater, and cleanup. It
establishes a fresh Square edge, windup arm 18 and dispatch value 10; admission
requires current windup below 7, in-flight count below 4, gate `+0x9E` below 12,
zero special/shared-timer/vertical-aux state, and animation outside 8/10/13/17.

Stable live controls reproduced the two exact unsigned boundaries: in-flight 3
armed while 4 blocked, and `+0x9E` 11 armed while 12 blocked. Special mode,
shared timer 12, and vertical aux 1 blocked. Holding Square while a blocker
cleared did not arm; release and fresh press did. Attempts to poke windup or
animation as if they were stable inputs were rejected because upstream native
updates rewrote them before the gate. Their opcodes remain census evidence, not
false single-field controls.

## Selectors, allocation, and trajectory

Selector-only trials from one pristine anchor produced the exact primary map
0→2, 1→5, 2→8, 3→11, 4→45. Selectors 0/1/3 entered aim helper `0x80046D24`;
2/4 skipped it and used the heading/-2048 vertical setup. Every successful
dispatch allocated a distinct native record from the 64 × `0x38` pool at
`0x800B0D18` through full entry `0x8005A0E0`, stored gravity 128, and called SFX 2.
Static allocator flow proves a round-robin free-slot search with no full-pool
escape.

Eleven consecutive straight-record transitions resolve the integration order.
Each position delta equals the record's current velocity; afterward VY increases
by exactly 128 and TTL decreases by one. Native cleanup retires the record and
returns the in-flight count to zero.

Strict-pristine homing fixtures distinguish successful target acquisition from
the no-target fallback. Selector 2 primary type 8 passes acquisition mode 1 and
spawns type 16 at return PC `0x80057584`; selector 4 primary type 45 passes mode 0
and spawns type 48 at `0x80057540`. Both confirmed secondaries have flags 237 and
TTL 100 after update, and both lifecycle controls return in-flight count to zero.

## Cold boot, breadth, and lifecycle

The timing-matched from-boot edit changes only frames 8550..8620, with Square
held only at 8558..8561. Control and edited branches have identical selected
fields, whole player-block hash, cycle, and emulator frame before the edit at
8551. The edit arms at 8561 and dispatches/spawns at 8617: stored class 2,
returned record `0x800B1958`, and SFX 2. Control retains zero in-flight records.

The 19-anchor strict-pristine sweep covers Training, stages 1–15, and all three
bonuses. Eighteen spawn, including Riverbed Flight. Bonus 2 Mushrooms is the
sampled negative: animation changes 24→22 but windup stays zero and no record
spawns.

Pause preserves the full active-record hash, while resume advances it. For the
same-scene death control, marked windup/in-flight 5/3 becomes 0/0 after native
respawn and lives decrement 5→4; a fresh red throw then reaches windup/in-flight
8/1 without save reload.

## Failed hypotheses and corrections

- **`0x80047170` is the throw function entry:** false. It is the selector read;
  the byte-matched full function begins at `0x800470AC`.
- **The in-flight admission limit is 8:** false. The unsigned exact boundary is
  `<4`.
- **Stored VY is a pre-integrated next-position delta:** false. Position consumes
  current VY first, then gravity adds 128.
- **All selectors use the target aim helper:** false. Homing and mega skip the
  ordinary helper.
- **The pool cursor identifies the thrown object:** false. It is only the next
  round-robin search position; the allocator return identifies the record.
- **A primary homing berry mutates into its homing record:** false. Types 8/45
  allocate distinct secondaries 16/48.
- **`red_berry_thrown.sav` proves target acquisition:** false. It exercises the
  no-target fallback; strict homing/mega fixtures provide the positive controls.
- **Bonus 2 or Riverbed Flight can be assumed from ordinary action rules:** false.
  Their sampled contexts were measured explicitly and diverge in opposite ways.

Static census, stable gates, selector matrix, straight recurrence, exact homing
fixtures, cold boot, breadth, pause, retirement, and same-timeline respawn jointly
confirm ordinary A08. Original facts: [[SYS_berry_projectile_and_homing]].
