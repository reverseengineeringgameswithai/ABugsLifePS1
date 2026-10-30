---
kind: experiment
id: EXP_2026-07-15_phase4_downhill_slide
name: Phase 4 downhill-slide campaign
status: complete
date: 2026-07-15
confidence: confirmed
---

# Phase 4 downhill-slide campaign

## Question

What exact pristine law initializes and sustains the downhill abdomen slide,
and how does it terminate, steer, interact with collision/contact, and reset?

## Setup and identity

- Generator `tools/phase4_downhill_slide.py`, SHA-256
  `a54e760f8f1db544d76a2ecac3e410a4c2e97facd5f5a8dd6a9a81359a2f7619`.
- Evidence `analysis/phase4_downhill_slide.json`, SHA-256
  `a78387f11f089b49adfeff3a4e728e7f2a14163a8cded2fc507c4ccb7c4214f6`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Native slide movie SHA-256
  `c228473c4191166e3ea7a4f918aa580aebe8c39b7c18663e5ad82ebb7c1c4a45`;
  its pristine save SHA-256
  `1b4be8816ca8897b1b374ac96c9912baa089bf76c9bab285377efbad8f26ac66`.
- Cold-boot LEVEL01 movie SHA-256
  `bfedc0d0f4828998fc598257b35ad090180ad6cb01ea317bc40229f977dc40fb`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  release-binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method RPC manifest.

The retained run used fresh absolute config
`/tmp/abl-phase4-i8-a06-live4-9272ab0`, loopback port 24888, and an ephemeral
token. It verified the mounted `SCUS-94288` CUE/BIN identity before every
experiment, inspected every save before load, and stopped only its config-owned
PID. Regeneration requires newly created isolation values:

`python3 tools/phase4_downhill_slide.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Diagnosis and observations

The static census re-read 41 decisive instructions from the pinned retail
executable and hashed the player, setup, landing/state, latch, animation, and
proximity regions. Byte-matched assembly remains authority; `src_re` is
documentation-grade and is not a build input.

The native movie established the observable sequence: state 4 before contact;
state/timer/animation 1/12/28 at frame 406; grounded 5/12/28 by 410 and through
500; state 0 after Cross release by 714. The initializer writes timer 12 and
aux -6144. A slow sample can already be timer 11 because positive decrement
occurs in the same resident update; eligible carried motion immediately
re-arms it to 12.

Single-field perturbations at identical player-block/cycle/frame anchors
isolated the component law. Forward 767 and lateral 767 produced timer 11 and
animation 6. Forward 768, lateral 768, and lateral -768 produced timer 12 and
animation 28. Static code confirms signed forward comparison and absolute
lateral magnitude. The latch contains no slope or floor read.

Removing only Left from native movie frames 451..491 kept both branches in
state 5/timer 12 but changed heading and X/Z path. Adding only Cross to the
cold-boot movie frames 8475..8481 preserved exact pre-edit fields, whole player
block, cycle, and frame; at frame 8480 it changed control 0/10/6 into edited
5/12/28.

Control-checked `movie.traceToFrame` coverage was untruncated and neutral for
cycle, frame, full RAM, and registers: 33,608 hits across 284 player-controller
PCs and 19,606 across 162 animation PCs. Execution watches directly attributed
the landing aux/timer writers, state-5 selection, component threshold, timer
re-arm, and animation-28 selection.

## Failed hypotheses and corrections

- **State 5 identifies the slide:** false. An ordinary held jump landed in
  shared state 5 with timer 0 and animation 5.
- **Player `+0x42/+0x46=(11,12)` is the action state:** false. Those values are
  animation frame counters; the action tuple is state/timer/animation at
  `+0x80/+0x7A/+0x88` plus its input/component context.
- **A slope predicate re-arms the slide:** false for the resident latch. It
  reads Cross and movement components only. Collision/terrain affects their
  inputs through the separate E02 interface.
- **First landing sample must remain 12:** too strong. The initializer writes
  12, but a non-eligible carry can be sampled at 11 after the same-update
  decrement.
- **Threshold failure immediately exits state 5:** false. It retires timer 12
  and animation 28; held Cross may leave the shared state value visible.
- **Slide is a generic attack:** false. None of 28 paired active classes
  selected target response -20/30, though eight retained ordinary player damage.

An early lifecycle implementation that would have reloaded the save was not
accepted. The retained control marks timer/state/animation 12/5/28 only after
native fatal contact begins, observes native same-scene respawn clear timer and
state to zero, and obtains a fresh state-4 landing in the same timeline.

Static census, native movie, exact component controls, steering and cold-boot
counterfactuals, trace attribution, 19-anchor breadth, 28-class contact matrix,
pause, and same-timeline respawn jointly confirm ordinary A06. No copyrighted
fixture, BIOS, capture, credential, token, or generated disc is committed.
Canonical result: [[SYS_downhill_slide_controller]].
