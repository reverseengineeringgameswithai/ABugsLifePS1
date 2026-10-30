---
kind: experiment
id: EXP_2026-07-14_phase4_run_locomotion
name: Phase 4 run-locomotion campaign
status: complete
date: 2026-07-14
confidence: confirmed
---

# Phase 4 run-locomotion campaign

## Question

How does pristine D-pad/analog input become ordinary horizontal motion, which
fields and writers own it, how collision consumes it, and does the law survive
stage and lifecycle breadth?

## Setup and identity

- Generator `tools/phase4_run_locomotion.py`, SHA-256
  `cfab9e244e8a73f0760cd8dc69b2f2574dc01ccd745c94ecf683b3a2c1ac346e`.
- Evidence `analysis/phase4_run_locomotion.json`, SHA-256
  `96e22099965c4df517b06d798b62c29fd0128e99ec0507b4e33653a7a9d4d7d2`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  release-binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method RPC semantic SHA-256
  `0f3e6a032a81318afaacbddf5512dd75d0e4fbcda0f4be91d1142acc83f15ed4`.
- Every attempt used a new absolute `/tmp` config, dedicated loopback port and
  token, verified mounted retail media, inspected saves before loading, and
  stopped only the config-owned PID.

Regeneration command, with freshly created values every time:

`python3 tools/phase4_run_locomotion.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Procedure and observations

The static census verified 26 decisive pristine instructions plus exact hashes
for the input helper, horizontal controller, collision commits, and animation
gate. The live run inspected and loaded 19 centrally pinned strict-pristine
anchors. Each compared neutral with 60 emulator frames of Up and retained every
sample, proposal-equal motion, resolver-adjusted motion, and vertical response.

All 18 ordinary contexts decoded Up, moved, differed from neutral, exposed an
exact velocity-proposal tick, and ended in animation 0. Fourteen retained a
resolver-adjusted tick. Riverbed Flight was the exact negative: animation 4 and
no compared field difference.

Controls covered four D-pad directions, full/half/deadzone analog, acceleration,
release/re-entry, and Up-to-Right turning. Full/half forward components were
1804/909; deadzone was zero. Pause/resume and a native health-zero actor-contact
death proved lifecycle behavior. Respawn reduced lives 5→4 and restored health
4 before held Up resumed animation 0.

An untruncated access/exec trace attributed desired heading, heading, both local
components, world velocity, and collision-resolved position writers. D-pad
magnitude was `0x3FDE`, half analog was exactly `0x2000`, and deadzone never
entered the magnitude helper.

The from-boot LEVEL01 movie was branched in memory. Removing only Up from frames
8103..8162 preserved identical player fields, player-block hash, cycle, and
emulator frame at the edit boundary. Afterward the control forward component was
472 and edited neutral was 0. Neither movie branch was written to disk.

## Failed hypotheses and causal conclusion

- An initial ad-hoc diagnostic passed an empty controller request and was
  rejected by the API with `-32602`; no evidence was retained and the owned PID
  was stopped.
- The first campaign assertion assumed Up must appear in all 60 samples. The
  next assumed 59. Replays showed a 30 Hz player update on alternating emulator
  frames: latch onset is sample 1–3, then continuously asserted, yielding
  58–60 samples. The final guard tests onset and contiguity instead of hiding
  those raw samples.
- The inherited label “horizontal speed tracks hypot” was too broad. Static
  owner flow, directional controls, and signed runtime values show `+0x38/+0x3C`
  are local forward/lateral components rotated into world velocity.

Observation, inference, and causal confirmation are kept separate in
`config/phase4_findings.yaml`. No copyrighted fixture, BIOS, capture, token,
credential, or generated disc was committed. Canonical result:
[[SYS_run_locomotion_controller]].
