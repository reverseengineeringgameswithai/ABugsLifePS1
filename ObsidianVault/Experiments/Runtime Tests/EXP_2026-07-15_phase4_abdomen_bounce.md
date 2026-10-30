---
kind: experiment
id: EXP_2026-07-15_phase4_abdomen_bounce
name: Phase 4 abdomen-bounce campaign
status: complete
date: 2026-07-15
confidence: confirmed
---

# Phase 4 abdomen-bounce campaign

## Question

What exact pristine law recognizes the second Cross, selects the short versus
high slam, qualifies target contact, rebounds or increments a chain, and resets
across miss, pause, death, respawn, transition, and exceptional controllers?

## Setup and identity

- Generator `tools/phase4_abdomen_bounce.py`, SHA-256
  `138cb9bc8630972557efc747a34d1d1d105661108dcdb929084a0ce28e314e61`.
- Evidence `analysis/phase4_abdomen_bounce.json`, SHA-256
  `f7dec85ee70365cb98886ac749d8dd1e7b2ff4c749d0f4c5caf069349921dda1`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  release-binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method RPC semantic SHA-256
  `0f3e6a032a81318afaacbddf5512dd75d0e4fbcda0f4be91d1142acc83f15ed4`.
- The retained run used a fresh absolute `/tmp` config, dedicated loopback port
  and token, verified mounted retail media, inspected every save before load,
  and stopped only its config-owned PID.

Regeneration command, with freshly created values each run:

`python3 tools/phase4_abdomen_bounce.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Diagnosis and observations

The static census verified 24 decisive retail instructions plus exact hashes
for the 6004-byte player owner, 564-byte slam branch, 2744-byte proximity owner,
and 296-byte target/streak slice. The byte-matched assembly is authority;
`src_re` files are documentation-grade.

The from-boot diagnosis corrected the old “state 4 is the whole move” shorthand.
The source first Cross ran at frames 8350..8377 and the second at 8380..8408.
Removing only the second window kept state 2; the control entered high-slam
state 4. The branches were field/block/cycle/frame equal before the edit.

Direct distance controls then isolated the exact signed threshold. Distance
8192 produced state 3/aux 0. Distance 8193 produced state 4/aux 9: static code
shows the branch wrote 10 and the retained sample occurred after one decrement.
The standardized double Cross produced state 4/aux 9 in 18 ordinary contexts;
Riverbed Flight stayed state 0/animation 4/aux 0.

The pinned Bonus-1 movie naturally enters state 4/aux 9 at frame 104 and reaches
aux 1/velocity 4096 before impact. Between frames 124 and 128 the selected
spider at `0x800A0014` changed response state 0→-20 and s16 `+0x54/+0x58`
0→4096, while player health stayed 4 and streak changed 0→1. The same replay
reached streak 4 at frame 750 and, by 1250, scene 0x10/streak 0/latch 6/unlock
bit 2.

`movie.traceToFrame` ran an untouched CachedInterpreter control and an
instrumented replay to movie frame 140. Both ended at cycle 5294556433,
emulator frame 9352, RAM SHA-256
`18d7310a45ee996bc6aa49a26f24ef40f14f372b5ab5aaceea6b408beeeff4c9`,
and register SHA-256
`da5acf3e6d5a9a8287bdb17dcd3856622f6ff5851191c5bea915df2f5d77e0aa`.
Coverage was untruncated: 2532 hits/115 PCs in the controller range and 54
hits/54 PCs in the contact range.

## Causal timer branch and failed hypotheses

Control and edit replays were exactly equal at movie frame 124: aux 1, player
fields, whole-block hash, cycle 5285497172, and emulator frame 9336. Changing
only the s16 aux to 0 before the same impact changed the frame-128 result:

- control: streak 1, state 4, velocity 4096, player health 4;
- edited: streak 0, state 5, observed velocity -1024, player health 3.

Static writers show -1536 is written before the same update advances gravity.
Actor animation later overwrote the immediate animation-3 publication, so the
retained post-update value 8 is not relabeled as the contact writer. This
counterfactual falsified the requested “damage per accepted hit” assumption:
the accepted timer-1 stomp preserved player health, while the expired timer-0
contact damaged the player and rebounded. It also avoids inventing a generic
target HP field; family HP/death remains D-owned.

The first lifecycle implementation was rejected before promotion because its
“fresh post-respawn” check reloaded the save. The strengthened run marks aux 7
only after native fatal contact has begun, observes native same-scene respawn
clear it to 0 and decrement lives 5→4, waits in that same timeline, then enters
state 4/aux 9 on a fresh double Cross. Pause separately froze all action fields
and resumed countdown.

## Causal conclusion and residuals

Static opcodes, cold boot, exact distance controls, operator anchor, gameplay
breadth, natural five-stomp chain, control-neutral native coverage, timer-only
counterfactual, miss, pause, and same-timeline respawn jointly confirm ordinary
A05. A06, E02/E05, family lifecycle, bosses, and F14 retain separate rows.

No copyrighted fixture, BIOS, capture, token, credential, or generated disc was
committed. Canonical result: [[SYS_abdomen_bounce]].
