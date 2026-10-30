---
kind: experiment
id: EXP_2026-07-27_phase4_fmv_lifecycle_continuations
date: 2026-07-27
phase: 4
campaign: fmv_playback
row: E15_fmv
status: static_sub_boundary_banked
confidence: high
source_state: original_game
artifact: analysis/phase4_fmv_lifecycle_continuations.json
---

# Phase 4 FMV lifecycle continuations

## Work packet

Closure debt selected only `fmv_playback` / `E15_fmv`, with `lifecycle` the
first unmet nine-dimension predicate and `static` the binding lane. The exact
claim was that every remaining natural completion, pause/stop/repeat,
viewer-return, level-continuation and error continuation intersecting E15 could
be assigned either to an exact pristine owner and typed lifecycle transition
or to a non-intersecting residual.

The falsifier was any source-pinned callsite, reader, writer, indirect edge or
exception path left unclassified, or any exact owner contradicting the
partition. The needed evidence domain was the retained
`fmv-lifecycle-v2` index followed by pristine resident/FMV executable bytes,
xrefs, typed state and centrally pinned ASM. The predicted authoritative
machine layer was semantic C plus a generated continuation artifact, schema
and mutation guard.

## Movie and evidence inventory

Before selection, the recursive operator inventory found 110 files and
153,880,509 bytes below `movies/Phase4`, 147 files and 420,121,736 bytes in the
broader operator movie tree, and 135 centrally provisioned files totaling
395,715,280 bytes. No filename was promoted as evidence and no operator bytes
were imported.

Ordered regeneration retained 55/55 capsules and 3,391,058,326 external bytes.
The queue retained 107 rows: 91 open, zero offline-ready, 42 offline-partial,
zero live-required and 65 without a capsule. The derived catalog retained nine
indexes over 34 rows; closure debt selected only E15 at four met and five
remaining dimensions.

## Offline localization

The selected derived index was the preserved 16,060,589-byte
`fmv-lifecycle-v2` JSON, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`.
The closed offline receipt SHA-256 is
`1281a8d210c04737649d74633323d13d528523073e2b7efff176a2c98bb82a9a`.
It re-executes the tracked
`tools/phase4_offline_receipt_query.py` reader over the centrally retained
copy, searching for pause, repeat, viewer, timeout, CD failure, malformed
stream, level continuation and the named E15 PCs.

The retained output SHA-256 is
`cbf056395dced4307eca756903385f7c009c7a98c29589f72513f15ee415055e`.
No term has semantic owner evidence; the one `repeat` occurrence is only the
index selection-reason string. The capsule/index therefore answers when
selected recorded state changed but cannot own resident or transient
continuation code.

## Static reconstruction

`analysis/phase4_fmv_lifecycle_continuations.json`, SHA-256
`a9a54830cb3ddf0d2a30d69ff37f2e2249030c9efed70cd319107e485c247b98`,
recomputes from hash-verified pristine `SCUS_942.88` and `FMV/FMV.BIN`.
It joins the existing exhaustive nine-call loader census and validates four
owner ASM sources against `tools/repro_inputs.sha256`.

All nine post-return windows are byte-hashed and classified:

- the three boot movies remain one synchronous repeated-playback owner before
  the six-way frontend dispatch;
- the bonus return publishes scene-flow state and continues its cursor loop;
- LOSE calls `scene_setup_and_load(5, 64)`;
- LEV15C calls `level_transition_orchestrator(0)`;
- completed Level B sums the exact 16-byte progress table and conditionally
  selects LEV15D;
- LEV15D publishes transition value one;
- Level A stays inside the full `0x8005B714..0x8005BC64` reset/scene-load
  owner and all 20 direct calls.

Five additional FMV.BIN windows bind both completion writers, the one clear
writer and one reader, decoded-record absence, decode timeout, five player
exit edges and the common `CdControl(Pause=0x0b)`/ring/callback/free/return
teardown. The four exceptional categories are statically routed. Each of the
nine resident windows, five transient windows and one loader callsite has an
independent mutation case that must fail closed.

## Decision boundary

The confirmed sub-boundary is
`resident_post_fmv_continuation_ownership`; the overall lifecycle dimension
remains partial. Static ownership does not prove native failure frequency or
user-visible pause/repeat/error outcomes. Remaining E15 manifest variants are
campaign-breadth debt. Movie-viewer return/unlock/persistence belongs to
C17/E14 and FMV audio presentation belongs to E12; neither is an unclassified
E15 owner.

The decoded-record control described by the original packet was subsequently
executed and its observer-retention ambiguity was closed by a separate guarded
successor. The current low-level partition does not replay that window.

No DuckStation process launched, no live escalation entry or live receipt was
created, no copyrighted byte was committed, and no MOD-private state or hook
changed.

## Reload and retirement ownership successor

The method-ratchet iteration reselected only `fmv_playback` / `E15_fmv`, with
`lifecycle` still the first unmet dimension and `static` still binding. Its
falsifier was any direct pristine wrapper edge or post-return owner left
unclassified, any repeated invocation that bypassed the Region-B copy, or a
mutation of the asserted loader opcode that did not fail the focused guard.

The retained `fmv-lifecycle-v2` index was queried first. The closed
`abl-phase4-offline-query/1` receipt is SHA-256
`15ea19ebaaac3aba5ff79d94b3e7f9df0780636c8aadaeb1021a184d25892356`;
its 16,060,589-byte input retains SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`,
and its output is SHA-256
`a7ce392e00ee5e3f363c0b5cd0471dbba4b3e9abb025ff15542593d9d1baf498`.
The retained bounded command is
`python3 tools/phase4_offline_receipt_query.py --input
@run/iteration-1-receipts/inputs/fmv-lifecycle-v2.index.json --output
@run/iteration-1-receipts/outputs/fmv-lifecycle-owner-search.json
--query-json @query`; it exited zero with exact stdout
`PASS: offline query`.
All ten bounded owner terms returned zero matches. This confirms that the
frame index does not answer the exact reload/unload/continuation ownership
question; it is not negative proof about the game.

Static reconstruction then validates the complete pristine
`0x8003E7C0..0x8003E83C` wrapper (SHA-256
`a9de53707b6fd702ed41d5010d3ac264bbd4145c12a6363475a003ccae9f68e3`)
and its exact matching-C source. Six ordered direct calls establish:

- unconditional `0x8003E7FC -> 0x80046330` copying
  `fmv\fmv.bin` to `0x800B5788` on every wrapper invocation;
- selector forwarding from saved `s1` to the synchronous player at
  `0x8003E814`, followed by matching-C display reinitialization at
  `0x8003E81C`; and
- no explicit Region-B clear or unload inside the wrapper. Common player
  teardown ends transient FMV use, while the resident caller continuation or
  a later Region-B loader owns replacement.

Therefore equal Region-B hashes across sequential boot streams cannot prove
that one load was reused: identical bytes are recopied by each wrapper call.
The exact later overwrite instruction remains outside this sub-boundary, and
endpoint nonresidency alone cannot identify it.

The overall lifecycle dimension remains partial. The remaining intersecting
fact is a native control distinguishing exact `CdControl(Pause=0x0b)`/stop
teardown from an induced decode/CD failure before caller-owned replacement.
The next safe lane remains static until one exact trigger and paired control
are predeclared. No live operation was needed or performed for this successor,
and no MOD-private contract changed.

## Native CD-event route successor

The next method iteration retained the same campaign and row. Its exact claim
was that the native CD-event registration, callback store, FMV player
consumer and Pause/common-teardown target form one byte-exact static route.
The falsifier was any mismatched registration word, callback pointer, field
address, sentinel comparison or teardown edge, or any mutation of those bytes
that left the focused guard green.

The current closed `abl-phase4-offline-query/1` receipt is SHA-256
`6f4066bec9b6c68a61957d469caef6a585eb199299e0eabad6e0a755dd60c73e`.
It re-executes the tracked reader over the exact 16,060,589-byte
`fmv-lifecycle-v2` input, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`,
with the canonical command
`python3 tools/phase4_offline_receipt_query.py --input
@run/iteration-1-receipts/inputs/fmv-lifecycle-v2.index.json --output
@run/iteration-1-receipts/outputs/fmv-native-pause-error-index-search.json
--query-json @query`. The retained output is SHA-256
`589cef9ca158ecea560697950a659dc771e55443592b82f27c4f1f73f1b0e15b`.
All nine bounded pause/error/teardown terms return zero matches. This proves
only that the frame-boundary index lacks the branch/control domain.

Pristine resident code then establishes the exact route:

- `cd_subsystem_init` owns the 44-byte
  `0x80045E38..0x80045E64` window, SHA-256
  `6d81bdc9029f8fdc1d9c4cd052d3164a805aa8c92aaacc19cb15480d6736de76`;
  it calls `OpenEvent` for class `0xF0000003`, spec `0x8000`, callback
  `0x80045D5C`, mode `0x1000`, retains the handle, and calls `EnableEvent`;
- matching C at `0x80045D5C..0x80045D6C` stores u32 value one at
  `0x80082484` (`gp+0x06ec`);
- FMV.BIN's 88-byte `0x800B741C..0x800B7474` window, SHA-256
  `86e1a7105affd7ff1cdf0266897d0ec7c607b519091216d1869ab778f508da9a`,
  loads that address at `0x800B7420`, compares it with the value-one
  sentinel at `0x800B7428`, and branches to `0x800B7464`; and
- the target loads CD command `0x0b` and calls `CdControl` at `0x800B746C`
  before the already bounded common teardown.

Focused mutation guards alter the callback store, registration pointer,
sentinel, consumer load, branch and teardown command and fail closed. This
closes `native_cd_event_to_pause_teardown_routing`, not runtime event
delivery, delivery frequency, the Pause result or a visible media-failure
outcome.

`P4-ITER107-E15-CD-EVENT-EXIT-CONTROL` predeclares the missing runtime
interface fact. Its passive receipt covers movie frames 249..340; the precise
pair stages both E15 branches to frame 250 and stops at 330, before the
recorded Start input at frame 334. The positive changes only
`0x800B7420: 0x8C422484 -> 0x24020001`; the negative preserves the native
field load. Both batch plans validate. This iteration's immutable
before-ledger did not contain the new ID, so no DuckStation process launched
and no live receipt was authored. The scheduler now binds the next lane to
that exact future live control; no dimension is promoted.
