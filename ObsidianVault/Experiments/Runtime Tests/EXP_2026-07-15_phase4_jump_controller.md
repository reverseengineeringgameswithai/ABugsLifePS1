---
kind: experiment
id: EXP_2026-07-15_phase4_jump_controller
name: Phase 4 jump-controller campaign
status: complete
date: 2026-07-15
confidence: confirmed
---

# Phase 4 jump-controller campaign

## Question

What exact pristine law maps Cross press/hold/release to ordinary jumping, how
do native modifiers and coyote eligibility work, and where do collision,
animation, pause, death, and exceptional paths take ownership?

## Setup and identity

- Generator `tools/phase4_jump.py`, SHA-256
  `7a8cb29cc67ac8d5e707ad6fcc0b7135885930b9d7262e348b486a4e366a58a9`.
- Evidence `analysis/phase4_jump.json`, SHA-256
  `456d1cd488a66fcc735942268a9fd12509b48562daec5d828a92565dbe86937a`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  release-binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method RPC semantic SHA-256
  `0f3e6a032a81318afaacbddf5512dd75d0e4fbcda0f4be91d1142acc83f15ed4`.
- Every run used a fresh absolute `/tmp` config, dedicated loopback port and
  token, verified mounted retail media, inspected every save before load, and
  stopped only the config-owned PID.

Regeneration command, with freshly created values each run:

`python3 tools/phase4_jump.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Procedure and observations

The static census verified 21 decisive instructions and exact hashes for the
6004-byte player function, 616-byte ordinary jump branch, takeoff branch, and
release/gravity branch. The byte-matched ASM is authoritative;
`src_re/player_update_80048138.c` remains documentation-grade.

From identical `level01.sav` loads, Cross holds of 1, 2, 4, 8, 12, and 20
emulator frames produced heights `6336, 6336, 8256, 11520, 14016, 16896`.
The equality of the first two is native update quantization, not an omitted
sample. At the same two-frame hold, directly selecting valid native flag
`0x0020` changed the first committed takeoff velocity from -2816 to -3520 and
height from 6336 to 9120.

Controlled transient field perturbations tested the native coyote branch on
the first player update. Distance 512 with guard 0 took off; exact distance
1024 and distance 512 with guard 1 both remained state 0 and received only the
normal +256 gravity step. These writes were not presented as natural scene
events; they are causal controls over valid field domains.

All 18 ordinary anchors across Training, stages 1–13 and 15, and three bonuses
entered airborne state, selected rise animation 3, and returned grounded.
Riverbed Flight falsified an early exact-neutral assumption: Cross changed
X/Y/Z/vertical velocity while retaining state 0 and animation 4. The corrected
result records it as a separate F14 controller path.

Pause testing also falsified the initial “Cross remains frozen” hypothesis.
Neutral pause was exactly frozen, but Cross is the selected Resume confirmation;
the held edge resumed play and immediately jumped. Native health-zero actor
contact then proved death/respawn reinitialization and a fresh post-respawn jump.

Untruncated access and execution traces attributed the Cross read, state 1 and
2 writers, grounded clear, animation 3 writer, velocity commit, collision call,
and collision-resolved Y writer. The first takeoff watch captured `s3=s4=-3072`;
the first velocity commit/collision call carried -2816 after gravity.

Machine reconciliation then promoted coyote guard `0x80082434` into the exhaustive
semantic-state scope and regenerated the pristine scene-transition lifetime census.
`analysis/phase3_semantic_lifetime.json` SHA-256
`34d8cde64d9562fd1f2b7f09aa4238fdb06d292dd26ca49ad1b0ce40144a0f2e`
covers 69/69 entries (40 measured, 29 derived) and records the guard as resident RAM.
The single transition observed 0→0, so its inability to distinguish initialization
is kept as an explicit measurement blocker; static writers `0x80046C84/0x800495E4`
and the A03 causal guard controls establish the bounded behavior without relabeling
that 0→0 observation.

The from-boot LEVEL01 movie was branched only in memory. Removing Cross from
frames 8011..8038 while preserving original direction/analog input produced
identical fields, player-block hash, cycle, and emulator frame at frame 8011.
At frame 8025 the control was state 1, grounded 0, animation 3, while edited
neutral was state 0 and grounded 257. Neither branch was written to disk.

## Causal conclusion and residuals

Static constants, controlled hold/release and native modifier deltas, exact
coyote boundary controls, attributed writers, breadth, lifecycle, and cold boot
jointly confirm ordinary A03. E02 resolver geometry, A05 slam, plant activation,
and F14 flight remain separate rows and do not intersect the bounded ordinary
jump controller.

No copyrighted fixture, BIOS, capture, token, credential, or generated disc was
committed. Canonical result: [[SYS_jump_controller]].
