---
kind: experiment
id: EXP_2026-07-15_phase4_kick_attack
name: Phase 4 kick-attack campaign
status: complete
date: 2026-07-15
confidence: confirmed
---

# Phase 4 kick-attack campaign

## Question

What exact pristine law maps the shoulder/Square chord to kick timing and
animation, which resident actor contacts consume it, how are response classes
selected, and where do pause, respawn, Flight, and family-specific work bound it?

## Setup and identity

- Generator `tools/phase4_kick.py`, SHA-256
  `4997d80eb20bd7462ec66391415c0a601a6244c25a70f92220b5d61ea91a2cf8`.
- Evidence `analysis/phase4_kick.json`, SHA-256
  `9a98c343164dd995a4425f1f9426a4f7e6ca429713143ad7552c2947bc3bc928`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Mounted pristine CUE SHA-1
  `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5`; track SHA-1
  `0bc1a29748d4bd608d076495d085e825574880d1`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  88 recorded dirty paths, release-binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method RPC semantic SHA-256
  `0f3e6a032a81318afaacbddf5512dd75d0e4fbcda0f4be91d1142acc83f15ed4`.
- Every retained run used a freshly created absolute `/tmp` config, dedicated
  loopback port/token, verified mounted media, inspected every state before load,
  re-armed instrumentation after loads, and stopped only the config-owned PID.

Regeneration command, with new values for every run:

`python3 tools/phase4_kick.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Static and native input procedure

The static census verified 42 decisive instruction words and exact hashes for
the 128-byte arm branch, full 2744-byte proximity owner, 608-byte response
classification region, and 556-byte animation path. It also enumerated nine
timer writers, correcting the earlier single-writer registry and the earlier
whole-domain `-16..0` shorthand.

Fresh `level01.sav` branches reproduced L2+fresh Square and R2+fresh Square as
equivalent positives. Square alone, shoulder alone, pre-held Square, negative
timer retry, player `+0x5C=1`, and exact floor distance 1024 were negatives;
distance 1023 was the paired boundary positive. Deduplicated recovery values
were exactly `-16,-15,...,-1,0`, and a fresh chord re-armed after zero.

All 19 gameplay anchors were inspected against verified media before load. The
chord armed timer -16 and animation 1 in Training, stages 1–13 and 15, and all
three bonuses. Riverbed Flight stayed timer 0, grounded 0, animation 4.

## Contact matrix

For each anchor, the compact live pointer table was enumerated without treating
its index as stable identity. The union contained 28 distinct current
`(actor id, flags)` classes. Each representative was reloaded fresh for two
direct calls to the resident proximity owner: timer 0 and timer -16. Player
position was placed at the exact contact center reconstructed from the actor's
current animation phase, geometry pointer, heading, and fixed-point LUT.

Twenty ordinary classes changed from neutral actor response 15/player health 3
to kick response 30/player health 4 and player animation 30. Three flag-`0x80`
classes selected response 15 without damaging the kicking player. Two
flag-`0x20` and three flag-`0x800` classes did not select state 30. All 28
observations matched the static flag classifier. One id-28 neutral trial also
experienced unrelated live-scene interaction, but its fresh kick branch still
matched the `0x800` suppression law; the conclusion uses the paired target and
kick predicates, not that unrelated damage as immunity evidence.

This matrix is deliberately described as active classes at saved moments. It
does not substitute for authored family rosters, boss overlays, enemy AI,
berry immunity, respawn, permanence, or quotas.

## Lifecycle, trace, and cold boot

Pause froze X/Y/Z, timer, and animation. Cross confirmed Resume, after which
the negative timer resumed recovery. A native same-scene death was induced with
health 0, timer 11, and contact placement; respawn restored health 4, decremented
lives, cleared timer 11 to 0, and accepted a fresh R2+Square kick.

Untruncated access and execution watches captured native input mask, timer arm
`v0=0xfffffff0` at cycle 7088968867/frame 12521, recovery `-16 -> -15`,
animation 1, phase reset, contact timer read, actor state-30 write
`v0=0x1e` at cycle 7092016282/frame 12526, and player response animation 30.
Health remained 4. The actor's AI later advanced response 30 to another state;
the causal assertion is therefore attached to the instruction event, not to a
snapshot forty emulator frames later.

The from-boot movie was branched only in memory. Adding L2 over frames
8135..8160 and a fresh Square press over 8140..8143 preserved identical fields,
whole player-block hash, cycle, and emulator frame before the edit. At frame
8148 the control had timer 0/animation 0; edited input had timer -13/animation 1.
Neither branch was written to disk.

Two guard-triggered failed captures were useful diagnostics. A two-emulator-frame
Square pulse missed the resident player-update cadence, producing no arm event;
the retained trace holds Square for eight frames and proves the actual poll.
The next run correctly captured state 30 but initially checked the target forty
frames later, after AI had advanced it to 22. The retained guard now asserts the
causal state-30 instruction event and keeps the later state as lifecycle evidence.

## Conclusion and residuals

Static bytes, exact native controls, recovery, all-stage input breadth, paired
28-class contact controls, lifecycle, attributed native contact, and cold boot
jointly confirm ordinary A04. Enemy-family lifecycle/immunity, boss/overlay
contacts, E02 internals, and F14 remain separate rows and do not intersect this
generic resident law.

No media, state, movie, capture, BIOS, token, credential, or generated disc was
committed. Canonical result: [[SYS_kick_attack]].
