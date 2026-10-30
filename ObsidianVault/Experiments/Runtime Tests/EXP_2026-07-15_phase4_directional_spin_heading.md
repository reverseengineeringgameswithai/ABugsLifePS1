---
kind: experiment
id: EXP_2026-07-15_phase4_directional_spin_heading
name: Phase 4 directional spin heading campaign
status: complete
date: 2026-07-15
confidence: confirmed
---

# Phase 4 directional spin heading campaign

## Question and identity

What reproducible pristine behavior underlies the A07 “spin / secret
directional move” lead, which code and state own it, and where does it apply?

- Generator `tools/phase4_spin_heading.py`, SHA-256
  `141dd39218672cd8be3f9af2b8fc0d093b0a33a0bb1d852e942174b82c810bbc`.
- Evidence `analysis/phase4_spin_heading.json`, SHA-256
  `37001b491feab00011646617cce7cce65316bb6c0e5ba2ceff694953f212c4a4`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- All 20 save states and the from-boot LEVEL01 movie are centrally pinned in
  `analysis/phase0_2_external_fixture_set.json`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  release binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  with a 203-method source manifest.

The retained run was refreshed again after D18 added semantic ownership for the
exact chunk-31 actor-position context and thus changed the hash-pinned Phase-3
xref input. It used fresh config
`/tmp/abl-phase4-i27-spin-refresh-final-20477.hF7V6S`, port 20477, and an
ephemeral token. It verified the mounted pristine CUE/BIN, validated every save
header before load, reproduced all 19 responsive breadth anchors plus the exact
controls, and stopped only owned PID 1341105. The xref input SHA-256 is
`d9bbebb854c06e06478c98acc39666adccc1a6fc5de87e84093b04e20f1f01a0`;
no A07 behavior or conclusion changed. Regeneration requires new isolation values:

`python3 tools/phase4_spin_heading.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Observation

Three exact anchors ran timing-matched neutral, Left/Up/Right/Down, and
Left/Down/Right/Up branches. The two orders produced opposite signed post-Left
turns and used only the five expected direction masks. State, timer, and aux
stayed zero. A 19-anchor source-versus-neutral sweep found heading divergence
at every gameplay anchor and identical state/timer/aux sets.

Untruncated access logs attributed all six current-action reads, six desired
heading writes, 21 player-heading writes, and 52 action-field accesses. The
live path was `0x80047F6C -> 0x80048044 ->
0x800491A4/0x80049298/0x800492A8`. Static executable bytes independently show
the current-sample helper, 12-bit heading law, no history storage, and 21
resident heading readers.

Pause froze the whole player block and yielded zero heading changes. Because
direction buttons move the pause menu, resume was tested from a separate clean
branch and yielded 14 heading changes. Reload restored heading and desired
heading. Native same-scene respawn changed lives 5 to 4, restored health 4,
and accepted a 14-change re-entry sequence. The cold-boot edited and unedited
branches matched before the edit; only the heading and position diverged after
the directional edit while action lifecycle fields remained equal.

## Inference and causal confirmation

Successive current-direction samples feed the ordinary desired-heading and
player-heading controller. Opposite order, timing-matched neutral, complete
writer attribution, static byte law, lifecycle resets, and a cold-boot
one-variable edit jointly establish that causal path. They do not establish a
separate spin action or the web source's other claims.

## Failed hypotheses and corrections

- **A07 requires a distinct player mode or unknown writer:** the Phase-3
  battery correctly found neither; Phase 4 found the positive behavior inside
  named ordinary input/heading functions.
- **The live D-pad writer is `0x80048104`:** false for AnalogController; the
  observed writer is `0x80048044`. The former is the pure-digital fallback.
- **One scene disables this heading path because A01 Up movement is disabled:**
  false; Riverbed Flight still changes heading, while F14 retains its own
  movement and camera ownership.
- **A cold-boot positive branch must have zero aux:** false; the movie already
  carries an action lifecycle. Equality with the unedited branch is the causal
  control.
- **Paused directions can be reused to prove immediate resume:** false; they
  navigate the pause menu. The retained resume control starts from a separate
  clean branch.

The historical Phase-3 bounded negative remains valid for the exact claims it
made: its battery observed no distinct state or unknown writer. It is not an
absence proof and does not conflict with this ordinary-heading result. No
copyrighted or operator-owned fixture is committed. Canonical result:
[[SYS_directional_spin_heading]].
