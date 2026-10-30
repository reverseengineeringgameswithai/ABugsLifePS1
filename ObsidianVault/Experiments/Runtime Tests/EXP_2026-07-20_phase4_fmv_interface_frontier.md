---
kind: experiment
date: 2026-07-20
phase: 4
campaign: fmv_playback
row: E15_fmv
lane: static
status: dimension_promoted
canon: SYS_fmv_player_streaming
campaign_note: Game Solving Campaign - FMV Playback and Skip
evidence: [analysis/phase4_fmv_interface_frontier.json]
---
# EXP 2026-07-20 - E15 FMV callback and consumer frontier

## Decision

The closure-debt scheduler selected only `fmv_playback`/E15 and bound the
iteration to static `complete_frontier`. The retained `fmv-skip-v1` derived
index already covers the movie/domain, so its external output was reused rather
than regenerated. No
live escalation or DuckStation process was opened.

Fresh low-level reconstruction closes the callback and resident-consumer code
owners omitted by the preceding static artifact. E15 advances from two to
three met dimensions. It remains open with six partial dimensions; the binding
next lane is live lifecycle, which requires a separately predeclared exact
causal/control question.

The acceptance verifier rejected the first promotion basis because it stopped
the level-A owner at a return PC and did not validate the cited external ASM
bytes. The verifier-repair section records the fresh low-level reconstruction
that re-establishes the same dimension count from the corrected 146-met
baseline.

The next verifier found two more omitted indirect frontiers: `StSetStream`'s
fifth-argument callback slot and the six-target main-shell dispatch reached
after the three boot FMVs. The second repair below adds exact opcodes, target
semantics, source partitions, source pins, schema, Canon and falsification
guards without changing the dimension count or opening a live run.

## External evidence and selection

- recursively inventoried the existing Phase-4 and broader movie tree before
  selection; reused `movies/Phase4/E15_fmv_skip.movie.json` and its declared
  state instead of requesting a duplicate fixture;
- capsule preservation check: 55/55 valid, 3,391,058,326 external bytes;
- queue: 107 rows, 91 open, zero `offline_ready`, 42 `offline_partial`, zero
  `live_required`, 65 `no_capsule`;
- derived catalog: nine reusable indexes covering 34 rows;
- reused external `fmv-skip-v1`, 542 records, 1,875,785 bytes, SHA-256
  `caa4bef3e219787f2178c0e8826dd6992d62af3491f780d16fcff6d9a9eb12d7`;
- closure debt after promotion: 147 met, 47 partial, 769 gap; E15 is 3 met/6
  remaining and still the sole selected campaign.

## Exact callback lifecycle

The pristine player calls `StSetRing` at `0x800B6F9C` with 32 records. It
calls `StSetStream` at `0x800B6FC4` with `(display_mode == 3, 1,
0x0FFFFFFF, 0, 0)`. `StSetStream` stores its fourth argument in optional
callback slot `0x800910F0`; it loads the fifth stack argument at `0x80070B38`
and stores it independently at `0x80070B88` to slot `0x800910F4`. The E15
player passes zero at `0x800B6FBC`, disabling the guarded `jalr` at
`0x80070AA0` and both `StCdInterrupt` deliveries at `0x800712DC` and
`0x80071388`. These sites are cross-checked against
`analysis/phase3_jalr_callbacks.json` and guarded from pristine opcodes.

`CdRead2(0x1C0)` installs `0x80070A30` through `CdDataCallback` at
`0x800708F0` and wrapper `0x8007092C` through `CdReadyCallback` at
`0x80070900`. The wrapper calls `StCdInterrupt` at `0x80070934`; its only
direct delivery to the data handler is `0x800716D8`. Exhaustive resident JAL
censuses bind all ten `CdDataCallback` calls, eleven `CdReadyCallback` calls,
the one wrapper call, and the one direct handler delivery.

Five player exit edges converge on `0x800B7464..0x800B752C`. The common path
calls `StClearRing` at `0x800B749C` and callback teardown at `0x800B74A4`.
The default backend is cleared through zero-valued calls at `0x800709E8` and
`0x800709F0` inside `0x800709AC..0x80070A30`'s critical section.

## Resident consumers and exceptions

The synchronous loader has exactly nine direct resident calls. The generated
artifact binds every selector source, hook-enable value, return PC and
continuation in the main shell, scene-flow, completion, or gameplay-reset
region. The hook argument is a value supplied to fixed pre/post transition
routines, not a callback pointer.

### Verifier repair

The original promotion incorrectly treated level-A return PC `0x8005B790` as
the end of its gameplay-reset owner. Fresh reconstruction bounds the complete
function at `0x8005B714..0x8005BC64` and exhaustively guards its 20 direct
post-FMV calls, including `0x8005B7CC -> 0x8003F358`. A mutation at that scene-
load call now fails the generator instead of leaving `complete_frontier: met`.

The first artifact also cited source filenames without proving their bytes.
The generator now validates all 21 cited sources. Its twelve external handwritten
ASM inputs must match the exact clean-checkout pins in
`tools/repro_inputs.sha256`; missing or changed source bytes fail closed. This
repair changes the evidence basis of the existing promotion, not the retained
runtime observations or the six remaining E15 dimensions.

The second repair follows the boot loader returns at `0x8004FB64`,
`0x8004FB70`, and `0x8004FB7C` through the complete 508-byte main-shell owner
`0x8004FA40..0x8004FC3C`. Its `jr` at `0x8004FC34` is guarded together with the
six-entry `0x8001B3C4` table. The first five targets are separate 20-byte
functions at `0x8004FC3C/50/64/78/8C`; their stores select indexes
1/11/2/7/12 before joining at `0x8004FCC0`. The guarded `0x8004FCF0` index
load, `0x8004FD04` scene-table load, and `0x8004FD0C` scene publication resolve
scenes 1/12/3/4/13. Target `0x8004FCA0`
resets the shell substate, calls `0x8005222C(1)`, and stores the master state.
The five target-fragment ASM sources and the already cited dispatcher source
are now separate, exact, centrally pinned partitions.

Four exceptional categories are statically exact: file-open failure, no
decoded record with stop-latch store, finite `0x800000` decode timeout, and
GetlocP/CdRead2 retry. This is code ownership only. Runtime frequency,
malformed-media outcomes, callback cadence, repeated playback, pause/stop and
the 36 live manifest gaps are not claimed.

The bonus-selector interface does not imply a movie viewer. C17 owns viewer
selection; E14 owns unlock persistence; E16 owns generic overlay replacement;
E12 owns audio presentation policy. Those residuals do not intersect E15's
complete code-owner frontier.

## Banking and guards

- generator/artifact:
  `tools/phase4_fmv_interface_frontier.py` and
  `analysis/phase4_fmv_interface_frontier.json` (SHA-256
  `1ba53d3445ac43ffceef920cb8a48424801bd228cc040899a88af391ee3018e4`);
- semantic C: `src_re/fmv_callback_consumer_frontier.c`;
- schema: `config/phase4_fmv.yaml` version 7;
- adversarial guard: `tests/test_phase4_fmv_interface_frontier.py` mutates the
  callback target materialization, both zero optional-callback arguments and
  deliveries, callback teardown, the main-shell table and target semantics,
  level-A scene-load continuation, consumer continuation, and timeout
  diagnostic call;
- campaign claim: `complete_frontier: met`, confirmed confidence, tracked
  authoritative paths, and two explicit non-intersecting residuals.

The existing static-owner artifact changed identity only because its pinned
FMV schema dependency advanced to version 7. The bounded upstream dependency
and assertion-pin reconcilers refreshed hashes without rewriting behavioral
expected values.

## Rejected overclaims

- frame-boundary capsule evidence is not every-cycle callback attribution;
- a statically reachable error branch is not a reproduced runtime error;
- the bonus clip cursor is not proof of a player-facing movie viewer;
- complete-frontier does not close lifecycle, breadth, interfaces, durable
  evidence, cross-system behavior, or source closure; and
- no MOD-private state, hook, or intended behavior was introduced.

## Links

Original-game facts are banked in [[SYS_fmv_player_streaming]]. The active
scope, residuals and next lane are controlled by
[[Game Solving Campaign - FMV Playback and Skip]].
