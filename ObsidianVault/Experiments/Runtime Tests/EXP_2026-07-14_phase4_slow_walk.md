---
kind: experiment
id: EXP_2026-07-14_phase4_slow_walk
name: Phase 4 slow-walk campaign
status: complete
date: 2026-07-14
confidence: confirmed
---

# Phase 4 slow-walk campaign

## Question

What exactly does L2/R2 change in pristine locomotion, where is the change
owned, and does it survive stage and lifecycle breadth without overclaiming the
separately owned base movement law?

## Setup and identity

- Generator: `tools/phase4_slow_walk.py`, SHA-256
  `87bfde62b733833fb1f321a702f1254457bfb2f3464ca12f6f948c9965a5e09b`.
- Evidence: `analysis/phase4_slow_walk.json`, final retained SHA-256
  `adb3a0b219bdc7dc0e8d39cd191e423464e7c8a01167d78be8f6602eb96d062e`.
- Executable: pinned pristine `REBUILD/files/SCUS_942.88`, SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- DuckStation fork revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, release
  binary SHA-256 `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method API-manifest semantic SHA-256
  `0f3e6a032a81318afaacbddf5512dd75d0e4fbcda0f4be91d1142acc83f15ed4`.
- A fresh absolute config, dedicated loopback port, ephemeral token,
  mounted-media verification, disc validation before every state load, and
  cleanup limited to the config-owned PID.

## Procedure

The static census re-read the pristine executable, verified the complete player
update and the narrow movement and animation regions, and checked every decisive
instruction word. The live generator then inspected and loaded 19 centrally
pinned strict-pristine gameplay anchors.

Each anchor compared timing-matched Up and R2+Up branches. Separate controls
tested L2 equivalence, shoulder-only input, release/re-entry, pause/resume, and a
native same-scene death/respawn triggered by health zero and a known actor
contact position. A bounded access log attributed the decoded-action reads,
forward-component write, and animation-29 write.

Finally, the from-boot `movies/go_to_end/LEVEL01.movie.json` oracle was loaded in
memory. A branch added only R2 to frames 8103 through 8162, already verified as
Up-only. Neither the base nor edited movie was written to disk.

Regeneration command (config, port, and token must always be new):

`python3 tools/phase4_slow_walk.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Observations

- The player gate masks `0x0300` and changes an intermediate component bound
  from 1792 to 768. The actor path writes animation 29.
- All 18 ordinary gameplay anchors selected animation 29 with R2+Up and a
  non-29 run control. Riverbed Flight was identical across compared fields with
  animation 4 in both branches.
- L2 and R2 outcomes were equal. Shoulder-only R2 had zero X/Z displacement and
  did not select 29. Release/re-entry produced animation sequence 29, 0, 29.
- While paused, X/Y/Z, forward component, and animation stayed frozen. Resume
  restored movement and animation 29.
- Native death/respawn reduced lives from 5 to 4, restored health to 4 in the
  same scene, and selected animation 29 both at and after respawn.
- The 19-event trace was not truncated. It observed action `0x0210` at the
  decisive readers, the speed write at `0x800494AC`, and value 29 at writer
  `0x800566E8`.
- The cold-boot branches matched before editing. After 60 frames, the control
  used animation 0 and the R2 branch used 29; both movies remained reproducible
  and non-truncated.

## Failed hypotheses and conclusion

The Phase-2 “0.605x walk law” is too broad as a universal equation. The pristine
code proves an intermediate 768 versus 1792 component bound, while observed
final displacement varies with the separate base movement and geometry. The stronger,
narrower conclusion is confirmed: L2/R2 is a resident ordinary-locomotion
modifier with a separately owned animation-29 consumer and an explicit flight
exception.

No copyrighted save, movie, capture, BIOS, credential, token, or generated disc
was retained. Canonical conclusion: [[SYS_slow_walk_modifier]].
