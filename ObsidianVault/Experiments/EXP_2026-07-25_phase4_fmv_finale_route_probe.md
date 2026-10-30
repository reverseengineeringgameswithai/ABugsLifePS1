---
kind: experiment
id: EXP_2026-07-25_phase4_fmv_finale_route_probe
date: 2026-07-25
phase: 4
campaign: fmv_playback
row: E15_fmv
status: rejected_fixture_lead
confidence: high
source_state: original_game
artifact: analysis/phase4_fmv_finale_route_probe.json
---

# LEVEL15 finale-route fixture classification

## Question and prior evidence

The recursively inventoried recording
`movies/go_to_end/LEVEL15.movie.json` was a filename lead for a second natural
FMV lifecycle. It is a centrally declared 33,268-frame version-3 from-boot
movie, SHA-256 `ce573bb…1256`, classified for pristine SCUS-94288 media. The
retained scene timeline reaches scene 15 and later returns through scene 19 to
scene 0, but that correlation does not prove an FMV owner.

Static reconstruction narrowed the only relevant resident owners before live
work. Finale C calls the loader at `0x80050284` with selector 40, mode 0,
`BUGSFMV2/LEV15C.STR`, limit 3,162. Finale D calls at `0x8005036C` with
selector 41, mode -1, `BUGSFMV2/LEV15D.STR`, limit 1,828. The current
`fmv-lifecycle-v2` derived index does not contain this movie, and the C16
capsule contains neither caller.

## Method

Independent verification found that escalation
`P4-ITER90-E15-FINALE-SEQUENCE-LIFECYCLE` stopped at playback index 33,267.
DuckStation defines that cursor as the next input sample to apply, so input
index 33,267 was not executed. That receipt is superseded.

Corrective escalation `P4-ITER91-E15-FINALE-ENDPOINT-CORRECTION` used the
complete hash-validated 2026-07-18 runtime in fresh isolated profile
`/var/tmp/abl-p4-e15-finale-endpoint.iter3c.24761`, loopback port 24761.
Capabilities identified API 2.1.0/schema 2026-07-18, binary SHA-256
`55d58903…75a8`, source revision `fe0cca16…b8f5`, and dirty-state hash
`72dd936c…2371`. Mounted media was verified as pristine SCUS-94288 with the
central CUE and BIN hashes.

Four `movie.traceToFrame` queries compared their cached-interpreter coverage
run with an internally matched uninstrumented replay:

- bare PC `0x80050284` through movie frame 1,000;
- the same address with required register predicate `a0=40` through frame
  1,000;
- the register-filtered finale-C address through target `frame_count=33268`;
  and
- bare finale-D address `0x8005036C` through the same complete-consumption
  target.

`scenario.runBatch` cannot express exact-instruction, register-filtered movie
coverage with an internally matched replay, so the predeclared client-driven
fallback was used. The collector cleared all ten observer/controller methods.
The owned PID was then stopped and recorded in a separate cleanup receipt.

## Observation

The bare `0x80050284` query reports 326 cumulative hits by movie frame 1,000.
The same window with `a0=40` reports zero. The complete movie likewise reports
zero register-filtered finale-C hits and zero finale-D hits. All four coverage
ranges are untruncated and every comparison has equal RAM, registers, cycle,
emulator frame and movie frame. Both full checks apply all 33,268 samples,
including final input index 33,267, then stop playback with cursor zero.

The early endpoint is emulator frame 1,001/cycle 566,186,554 with full-RAM
SHA-256 `8470250a…f7c2`. The complete endpoint is emulator frame
33,269/cycle 18,836,452,125, PC `0x8004FEA4`, with full-RAM SHA-256
`a43e35c1…1a20` and register SHA-256 `406d2ecf…c9ec`.

The retained result is 102,305 bytes, SHA-256 `dbab03a3…a019`; cleanup is 814
bytes, SHA-256 `f0c73215…b63`, and records owned PID 596229 stopped. Both
remain external. No recording, media, credential or capture byte is committed.

## Observation, inference and causal boundary

Observed: neither statically identified resident finale owner executes after
complete consumption of all 33,268 samples. Observed: the unfiltered numerical
address accumulates 326 hits during cold boot, all excluded by the required
selector-register predicate.

Inferred: the PC is reused before the resident owner is installed, so bare
address coverage is not finale-call authority. The filename and scene
timeline are therefore rejected as a natural LEV15C/LEV15D fixture lead.

No selector, selected limit, completion writer, teardown or neutral derivative
was captured because its prerequisite owner call is absent. This is a
fixture-classification control, not a natural lifecycle or causal playback
proof.

## Banking and boundary

`config/phase4_fmv_finale_route_probe.yaml` pins the recording, media,
debugger, endpoints and external receipts.
`tools/phase4_fmv_finale_route_probe.py` derives the tracked summary from the
low-level coverage records. The validator rejects fixture/media drift; its
mutation tests reject a 33,267 target, active playback at that incomplete
cursor, false finale coverage, comparison divergence, endpoint drift and
cleanup failure.

The result promotes no roadmap dimension. E15 remains four dimensions met and
five partial. After two iterations without a dimension promotion, the next
method is to exhaust centrally declared boss/menu recordings by declared
anchor and faithful input span; if none reaches an exact owner, use a
predeclared bounded synthetic selector lifecycle control without calling it
natural route ownership. No MOD-private state, hook or intended behavior was
introduced.
