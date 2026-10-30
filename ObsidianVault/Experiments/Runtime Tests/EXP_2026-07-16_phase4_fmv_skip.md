---
kind: experiment
id: EXP_2026-07-16_phase4_fmv_skip
name: Phase 4 E15 Start-skip and natural cold-boot completion
date: 2026-07-16
status: reproduced_partial
confidence: confirmed_with_open_consumers
source_state: original_game
system: SYS_fmv_player_streaming
artifacts: [analysis/phase4_fmv.json, analysis/phase4_offline_fmv_batch.json]
---
# Phase 4 E15 Start-skip and natural cold-boot completion

## Question and falsifiers

Does native Start skip the currently playing FMV at the existing E15 fixture,
and can that claim be separated from the filename and from stale Region-B
memory after the overlay retires? Separately, does neutral cold boot naturally
complete, reset and reuse FMV.BIN before handing off to the frontend?

The result would fail if the movie/state pair were not centrally pinned; its
state or mounted media were not hash-verified pristine `SCUS-94288`; input
other than Start differed; branches diverged before Start; any retained trace
changed cycles, RAM, registers or frame against its internal control; coverage
truncated; the Region-B identity guard was absent; or cleanup failed to stop
the exact isolated owner. The cold-boot result would also fail if its source
were not a pinned `from_boot` movie, the transient recipe changed non-input
state, a completion/limit boundary drifted, Region B retired early, or the
scene-1 handoff were inferred from an FMV address after unload.

## Fixture selection and provenance

Before choosing work, the iteration recursively inventoried all 110 files under
`~/Downloads/ABL/movies/Phase4` and all 147 files in the broader movie
tree. The existing `E15_fmv_skip.movie.json` plus save was the relevant lead, so
no operator recording was duplicated or requested. The external bytes remain
untracked. Their central pins are:

- movie SHA-256 `ca5219db048a986605bb20c2376166e9014645c7da87c8347a6e6ec0fb681fba`,
  size 370,143, media class `pristine_serial`;
- save SHA-256 `851e8ebffa8b8417abb30ff0791ca4c1872a43cf06101247ee1ff97e4cdac417`,
  size 1,193,583, media class `pristine`.
- cold-boot movie SHA-256
  `bfedc0d0f4828998fc598257b35ad090180ad6cb01ea317bc40229f977dc40fb`,
  size 7,631,156, media class `pristine_serial`, v3 and `from_boot`.

A read-only isolated inspection first verified save format version 84, serial
`SCUS-94288` and its embedded pristine retail cue/track. The retained run then
used the mounted hash-verified pristine cue, fresh config
`/tmp/abl-phase4-i8-e15-natural-final2-19964`, dedicated loopback port 19964, debugger
fork revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, and release binary
SHA-256 `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`.
The generator stopped only config-owned PID 423255. The token is redacted.

```text
python3 tools/build_identity.py --verify
python3 tools/phase3_duckstation_rpc_manifest.py --check
python3 tools/phase4_fmv.py --port 19964 --token <ephemeral> \
  --config-dir /tmp/abl-phase4-i8-e15-natural-final2-19964 \
  --instance-state recreated
```

The skip branch is state-anchored; the natural-completion branch is an
independent cold boot. No disc, save or movie was modified or committed.

## Method

Static reconstruction verifies pristine `FMV/FMV.BIN` and `SCUS_942.88`, walks
all 40 manifest/frame-count pairs, checks every encoded `addiu` word, and hashes
the resident load/wait/completion regions. The fixture parser proves its only
active samples are Start at movie frames 334 through 342.

The debugger loads the original movie for a natural branch. It then stores that
same parsed movie in the session registry and edits only those nine
`ports.0.start` samples to neutral. No derivative recording bytes are written.
Both branches are traced at frames 333, 343 and 541 across resident FMV/shell,
libcd/libpress and FMV.BIN ranges. Each retained trace compares uninstrumented
and passive cached-interpreter replay before its result is accepted.

For the independent boot path, the generator verifies the broader movie's
central pin and `from_boot` metadata, writes an ephemeral derivative in which
all 7,429 non-neutral port-0 frames are neutral, records the exact changed-frame
and derivative digests, and deletes those bytes before retention. It traces
movie frames 2000, 3000, 3200, 4600, 4800, 8400, 8500 and 9400. The final
window adds focused `0x800B6B00..0x800B6B60` completion coverage. Every point
contains a fresh automatic uninstrumented/cached-block comparison from power-on.

The first coverage request after a fresh recompiler launch is used only as a
discarded backend-transition warm-up. It returned zero range hits and a distinct
one-cycle endpoint on initial attempts; later calls were exact and nonzero. The
retained natural/control comparison therefore begins only after the transition,
and the generator hard-codes the stable pre-trigger signature.

## Observations

- Movie frame 333 is exact on both branches: cycle `2585837573`, emulator frame
  4568, PC `0x80070D00`, SP `0x801FF600`, RAM SHA-256
  `1044d5b7d0bb6dc5a563a18c98e497e66f7919152d3ddcf1b093e2f4a01224e5`
  and register SHA-256
  `754f0d34004d6508c9410c0c667bcf2726cb94bcb12241db10630a0622b63117`.
- At frame 343, the Start branch is at PC `0x80065340`; the Start-removed branch
  is at FMV.BIN PC `0x800B98F0`. Both still have exact FMV.BIN head identity,
  completion request 0 and selected limit 386.
- At frame 541, the Start branch no longer has FMV.BIN at Region B and has
  stream backloc 73. The control remains inside exact FMV.BIN with completion
  request 0, selected limit 386 and backloc 163.
- All six retained traces have nonzero hits in all four ranges, no truncation,
  and exact cycle/RAM/register/frame equivalence against their internal control.
- Static row 3 maps `BUGSFMV1/LEV1A.STR` to limit 386 at FMV.BIN offset
  `0x0B94` / runtime `0x800B631C`, instruction `0x24050182`.
- Neutral cold boot reaches exact natural completion request 1 for
  `dlogo.str`/156 at movie frame 3000 and backloc 154, `tt.str`/440 at frame
  4600 and backloc 438, and `INTRO.STR`/1750 at frame 8400 and backloc 1748.
- The exact FMV.BIN head remains resident across all three streams. At frames
  3200 and 4800, completion and selected limit are both 0, confirming reset
  before the next stream rather than immediate selection at the sampled frame.
- FMV.BIN is absent at frame 8500. At frame 9400 its old Region-B fields remain
  untyped and resident scene/shell substate are 1/1.
- All eight cold-boot points are full-RAM/register/cycle/frame neutral. The
  frame-9400 signature is cycle `5322300418`, emulator frame 9401, RAM SHA-256
  `a7c7d53e554fb9a6a0c8677ef14507a2fe6f62c4a18cc968e0232a9aff5ce37d`,
  register SHA-256
  `dd0c7942321d82f501232c1a220c87592877dc793d32e0ea30e0f3a0e7e1d127`;
  completion-range coverage has 49,146 hits, 23 PCs and no truncation.

Observation: only the Start branch changes immediate execution and has retired
the FMV overlay by the final movie boundary. Inference: Start is a native skip
input at this pristine LEV1A anchor. Causal confirmation: the in-memory movie
diff contains exactly nine Start-to-neutral edits and the branches are exact
before those samples.

## Failed hypotheses and corrections

- A filename was not accepted as behavior. Central pinning, state inspection,
  replay and a single-variable control were required.
- An initial derivative serialized to a separate transient file did not give a
  stable pre-input comparison. The accepted method preserves the debugger's
  original parsed anchor and edits its in-memory registry copy only.
- The first attempt expected a particular running-latch value. The observed
  latch is already zero at the compared window, so that attractive but false
  timing predicate was removed; the PC and overlay-residency outcomes are the
  retained causal boundaries.
- The first retained-path attempt compared the debugger's initial backend
  transition call with steady-state calls. Repeated original and edited frame-
  333 probes proved the fixture deterministic; a discarded warm-up now makes
  all retained comparisons use the same execution mode.
- Raw values at `0x800CAC10` after FMV.BIN retires were initially displayed as
  completion state. They are not typed then. The final artifact emits Region-B
  fields only while the exact FMV.BIN head hash is resident.
- The first cold-boot retention attempt labelled frames 3200 and 4800 as the
  next streams already selected. Its typed guard failed because both limits
  were still 0. The corrected evidence records these as reset boundaries; the
  later natural completion points independently bind limits 440 and 1750.

## Result and next experiment

The 2026-07-19 retained-capsule pass subsequently reconstructed the complete
542-record Start branch without replay. It narrows exact head residency to
frames 69..416, shows that completion/limit initialization continues after the
first matching head boundary, follows backloc 1..73 over frames 218..362, and
bounds retirement between 416 and 417. It does not alter this experiment's
causal authority or broaden the LEV1A claim. See
[[EXP_2026-07-19_phase4_offline_fmv_batch]].

Native Start skip is confirmed for one state-anchored LEV1A playback. Neutral
cold boot confirms natural completion/reset/reuse/retirement for dlogo, title
and intro plus the scene-1 frontend handoff. The complete 40-entry static
dispatch is banked. E15 remains active on 36 live paths. The next experiment
should reuse existing end-of-level and menu movies for representative level-B
and movie-viewer owners, then cover pause/stop/reuse and fault controls.

Retained artifact SHA-256:
`b324ca5ca80b5d88fd9c01ebf8f06266866925cbe86d233ac8ef3460d84b51cc`.
The previous `05d5ca05…e119c` identity is superseded only because the bounded
dependency reconciler refreshed the semantic-source hash; the retained
runtime/control payload and historical run provenance are unchanged.
See [[SYS_fmv_player_streaming]] and
[[Game Solving Campaign - FMV Playback and Skip]].
