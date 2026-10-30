---
kind: experiment
id: EXP_2026-07-18_phase4_pause_shell
name: Phase 4 pristine pause-shell reproduction
status: complete
created: 2026-07-18
updated: 2026-07-18
confidence: confirmed
---

# Phase 4 pristine pause-shell reproduction

## Fixture census and authority

Before selecting the campaign, the recursive census found 110 files under
`~/Downloads/ABL/movies/Phase4/` and 147 files in the broader movies
tree. Filenames were treated only as leads. No recording declared the needed
pristine A18 start state and trigger, so no movie bytes were consumed or
committed. The prior `small_pause_issue.sav` lead is centrally classified
non-pristine and was rejected as original-game authority.

The retained run used centrally declared strict-pristine saves. `level02.sav`
is SHA-256
`9c4cd968151e8c2f630b89b58a9da90e9143de6bd5b14c859e2b783d12f7f152`;
`level_14.sav` is
`6e56d8c4780851f85059b477186b5b1346e23ed7e8eac79a134192e03fef5f50`.
All nineteen selected anchors, their declarations, pre-load state inspections,
and embedded pristine media are retained in `analysis/phase4_pause.json`.
Mounted CUE/track SHA-1 pins and serial `SCUS-94288` were verified before any
load. ALLMODS was not an input or authority.

## Reproduction

The isolated retained instance used config
`/tmp/abl-phase4-i1-a18-retained-20704`, loopback port 20704 and a local token.
The generator stopped only PID 601254 owned by that config. Port, token digest,
fork/binary/runtime-tree hashes, settings, media identity and cleanup are in
the artifact; the plaintext token is not retained.

Command:

`python3 tools/phase4_pause.py --port 20704 --token <local> --config-dir /tmp/abl-phase4-i1-a18-retained-20704 --instance-state recreated`

Observed results:

- 19/19 strict-pristine gameplay anchors entered pause and resumed without
  changing scene.
- Active/resumed held-Up controls changed actors, contacts and camera. Paused
  held-Up froze actor/contact/plant/camera hashes and all selected player
  semantic fields.
- During 60 paused frames the execution counts were present 20, DrawOTag 20,
  DMA kick 40, scene render 20, HUD animation 0, player update 0. The displayed
  raw frame changed.
- Riverbed Flight changed 8 sustain voices active -> 0 sustain/1 release while
  paused -> 7 sustain after resume, with stable SPU control.
- Default No retained pause and transition 0. Selected Yes produced attributed
  writers `0x8004F9C0`, `0x8004F9E4`, `0x8004F9FC`, with values 0, 5 and 23.
  After 2400 frames the frontend was scene 0 with raw16 SHA-256
  `c700c779e712ea3e371fc16b3b262ca0befae8d374f38294ce8d9ed9a04f2ab0`.

Transient visual checks under `/tmp` displayed Pause / Continue / Exit Level,
then Are You Sure? / Yes / No, and finally the Journey level-selection screen.
No PNG, screenshot, save, movie, disc or BIOS is retained.

## Observation, inference, confirmation

Observation: the exact memory hashes, typed fields, PCs, instruction words,
hit counts, voice phases, transition values and frontend hash above were read
from hash-verified pristine media.

Inference: the resident shell freezes gameplay/HUD update ownership while
continuing presentation and handing audio voices to release/restart behavior.

Causal confirmation: Start-only entry/resume reproduced on nineteen anchors;
held-Up active/paused/resumed controls separated freeze from inactivity; exact
write watches attributed selected-Yes exit values; default No was the negative
control. Static pristine bytes independently bind the same owners and branches.

## Failed instrumentation attempt

The first retained attempt used the debugger client's default ten-second RPC
timeout for a 600-frame frontend advance. The generator raised, stopped its
owned instance, and emitted no artifact. A second run reached the exact
frontend hash but armed the exit write log for three frames, three frames before
the writers. The final run used an explicit long timeout and a six-frame write
window; no behavioral predicate was weakened.

Original-game conclusion: [[SYS_pause_shell]]. Machine contract:
`config/phase4_pause.yaml`.
