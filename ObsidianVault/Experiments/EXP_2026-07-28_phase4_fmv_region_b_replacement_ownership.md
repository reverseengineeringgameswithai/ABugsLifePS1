# Phase 4 FMV caller-owned Region-B replacement ownership

## Scope

This measured iteration retained only `fmv_playback` / `E15_fmv` and the
first unmet `lifecycle` dimension. The exact claim was that the first
caller-owned Region-B replacement request after the already reproduced
natural LOSE return is the selector-zero `bits\memory.bin` resource load to
`0x800B5788`; E16 owns the replacement bytes and C16 owns this game-over
transition choice.

The explicit falsifier was any earlier selected-path Region-B materialization
or writer, a nonzero resource selector, a different resource/destination, an
unclassified edge, or a load-bearing pristine mutation that stayed green.

## Offline localization

Recursive inventory found 110 files under the Phase-4 operator tree, 147 in
the broader operator movie tree, and 135 centrally provisioned files. The
existing pristine C16 game-over movie/state pair was already declared, so no
operator fixture was imported or requested.

Ordered regeneration validated 55/55 retained capsules, 107 queue rows with
42 offline-partial, nine derived indexes covering 34 rows, and
`fmv_playback` as the sole selected campaign. Closed offline receipt
`7ed2612007cf908309455b1dee5434ec993ab0cea1d2b9f1693ed67e307be03e`
re-executes the tracked reader over the 16,060,589-byte derived-pristine
`fmv-lifecycle-v2` index. Its exact ten-term Region-B/ownership search returns
zero paths without truncation. Retained output SHA-256 is
`d343b2db4aef13b62168a5f675c2c850dc5d4cc388cd7dd20f021781f890a617`.

## Static reconstruction

The natural runtime anchor already proves selector 46/mode 0 enters
`fmv_bin_load` from `0x800500D8`, completes LOSE, and returns reproducibly to
`0x800500E0`. Pristine bytes then provide this ordered chain:

- `0x800500E4`: `scene_setup_and_load(5, 64)`;
- `0x800503C4`: display initialization, whose complete 19-call frontier has no
  Region-B materialization or resource/CD loader;
- `0x800503CC`: `resource_id_dat_load_dispatcher(0)`;
- `0x8003D300..0x8003D310`: the selector-zero branch materializes
  `bits\memory.bin`, `0x800B5788`, and calls `universal_file_loader`;
- `0x8004641C`: the universal loader forwards its preserved destination to the
  file helper;
- `0x80046074..0x80046078`: the file helper passes exact destination
  `0x800B5788` to `CdRead`.

An ordered materialization census across the return window, scene owner,
display initializer, and resource-dispatch prefix finds exactly one
`0x800B5788` construction at `0x8003D308..0x8003D30C`, with no unclassified
match.

## Result and boundary

The falsifier survived. Generated artifact
`analysis/phase4_fmv_region_b_replacement_ownership.json` binds the closed
query, natural runtime anchor, exact pristine function hashes/opcodes, display
call frontier, resource string, destination-preservation chain, ownership
split, and non-promotion boundary. Focused mutations of selector zero,
destination `0x800B5788`, or the CdRead destination turn the guard red.

This closes only `game_over_lose_region_b_replacement_ownership`. It does not
identify the first CD/DMA write cycle, cover a completed-level or movie-viewer
return, establish transfer failure/retry behavior, or claim E14
viewer/persistence policy. No DuckStation process launched and no live
receipt was authored. Lifecycle remains partial.

The next lane remains static: extend the same ownership census to one
completed-level or movie-viewer return before considering another live
control.

## Iteration-2 completed-Level-B extension

The second measured iteration retained the same campaign, row, and first
unmet `lifecycle` dimension. Recursive inventory again found 110 files under
the Phase-4 operator tree, 147 files in the broader operator movie tree, and
135 centrally provisioned files. The centrally declared from-boot LEVEL01
recording already supplies the natural completed-Level-B anchor, so no
operator fixture was imported or requested.

Closed receipt
`8fe4e94a84381d1106ae0df087db27347865dc0ed4db3320029b8268c22c6326`
re-executes the tracked reader over the same 16,060,589-byte
derived-pristine index. Its ten exact completed-Level-B, Region-B, owner,
asset, transition, and persistence terms all return zero paths without
truncation. The retained 2,128-byte output hashes to
`caa68175e00a34700d26af492ff5edd1c6a1a7eb298698c9431220029b89fbb5`.

The prior live artifact fixes the first completed-Level-B call at frame
14,382, selector 11/mode -1, completion writer `0x800B6B24`, balanced common
teardown at frame 15,816, and entry state `s0=1`. That state selects the
guarded scene-flow call at `0x8005013C`; the completed owner publishes only
zero or one, so the state-five call at `0x80050214` cannot be the natural
continuation.

Pristine scene-flow bytes then provide two exhaustive conditional branches:

- a negative pending request calls `scene_setup_and_load(3, 0)` at
  `0x8004FD74`;
- a nonnegative request calls `scene_setup_and_load(6, 128)` at
  `0x8005029C`.

Both transitions differ from loader-skip sentinel `-1`, so each reaches
display initialization and `resource_id_dat_load_dispatcher(0)`. The same
selector-zero E16 chain materializes `bits\memory.bin` and `0x800B5788`
exactly once before the universal loader submits the destination to `CdRead`.
The post-player owner itself has no Region-B materialization. Its ordinary
progress scan calls no save serializer and writes neither the adjacent C17
movie-viewer unlock byte nor any other viewer policy field. The all-complete
branch writes an adjacent scene flag, but whether it is serialized remains
E14/C17 debt.

Generated artifact
`analysis/phase4_fmv_region_b_replacement_ownership.json` SHA-256
`03b5a8d9a518f5c00624f81248b721e98a513b987d8e1456e142c682cc1087a4`
now closes both `game_over_lose_region_b_replacement_ownership` and
`completed_level_b_region_b_replacement_ownership`. Focused guards reject the
state-one join, either conditional scene call, transition argument, resource
destination, and CdRead destination. No roadmap dimension is promoted.

This is the second consecutive no-reduction iteration, so the method changes
from static ownership to the non-halting DMA/CD transfer domain. Planned
escalation `P4-R6-ITER2-E15-LEVELB-REGIONB-DMA-PROVENANCE` requires a wider
passive from-boot LEVEL01 pair and an identical precise pair using
`transferLog.start`. Its falsifier includes transfer truncation, no
post-teardown Region-B intersection, a prior intersection, a non-CDROM
channel/direction/base, or endpoint/identity drift. The immutable
iteration-before ledger did not contain this new ID, so no DuckStation
process launched and no live receipt was authored.

## Method-ratchet iteration 1 — DMA receipt preflight

The next controller run retained the same sole campaign, row, lifecycle
dimension, claim, and falsifier. Closed offline receipt
`ecfd091f44f49943e5e8431ba92e823d55c155f6317a7e6242fcc841934d9126`
re-executes the tracked reader over derived-pristine index
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`.
Its ten exact transfer/CD/Region-B terms all return zero paths without
truncation; the 2,094-byte output hashes to
`dba41729dc61fa7bfe6d4c5a52d06d6c022fe2a51fdedce0067b924b7022a399`.

Atomic-runner preflight then falsified the inherited receipt method before an
emulator launch. `scenario.bootAndRun` arms instrumentation before its first
guest frame and exposes no staged prelude, so a receipt cannot author a
15720/15740 capture start after observing from cold boot. More importantly,
the current `capture.atomic` response returns at most 10,000 transfer events
without the transfer ring's `total` or `truncated` fields, and the batch
adapter cannot page the first job after the paired second job has run. A
one-page result therefore cannot prove the required contiguous, untruncated
post-teardown stream.

The retained passive and precise plans now record honest full observation
windows `0..16120` and `0..16080`, while their assertions separately narrow
analysis to `15720..16120` and `15740..16080`. The passive plan validates.
The precise plan fails closed on the exact pagination limitation. The tracked
adapter also rejects any delayed cold-boot capture, preventing a future
receipt from laundering unobserved frames into its capture window.

No live operation ran and no live receipt was authored. The selected DMA
claim remains untested, lifecycle remains partial, and no roadmap dimension
is promoted. The autonomous next requirement is a bounded atomic surface
that retains transfer `total`/`truncated` metadata plus complete ordered
pagination independently for both paired jobs; it must be manifest-pinned
and make the existing precise plan validate before the passive launch is
worth spending.

## Method-ratchet implementation iteration 1 — atomic transfer pagination

This iteration retained only `fmv_playback` / `E15_fmv`, the lifecycle
dimension, and the existing planned DMA fact. The retained capsule set,
central movie queue, derived index, and closure-debt ledger were regenerated
again; the counts remain 55/55 capsules, 107 rows with 91 open and 42
offline-partial, nine reusable indexes over 34 rows, and 148 met dimensions.
No new offline content query was needed: the missing fact was the already
named atomic interface resolution, not another capsule-domain question.

The external debugger now copies one coherent oldest-first transfer snapshot
under a single transfer-log mutex. `capture.atomic` accepts the closed finite
envelope `transfer_pagination:{page_size,max_pages}` with limits 10,000
records per page, ten pages, and 100,000 retained events overall. Each job
retains ordered pages plus exact `total`, `returned`, `enabled`,
`pagination_complete`, and `truncated` fields before the next batch job can
clear the ring. Legacy clients still receive the bounded
`traces.transfers` slice.

The release build succeeds and hashes to
`8dce4a65c946f081f6db860f8ff5653d507c15d4dc15dca562fc456b3711b210`.
The binary embeds dirty-state identity
`38275389f4dbbb9d8d160e2d1de4c6e4f742d00c`. The candidate manifest now
hash-pins the core transfer service, dispatcher, method schema, docs, release
binary, and that embedded identity. Flik's batch adapter admits a planned
live run only when its debugger identity joins this manifest and both jobs
cover the full ring. Result banking independently rejects missing fields,
undersized capacity, page gaps, early short pages, count drift, truncation,
noncontiguous event indexes, and stale debugger/settings identities.

Both the wider passive plan and the precise transfer plan now validate. The
interface falsifier did not fire: complete per-job pagination is mechanically
available and the precise plan is no longer admitted on a nominal one-page
slice. No DuckStation process launched, no receipt was authored, and no
behavioral or roadmap dimension was promoted. The next iteration may execute
only the already planned sequence: close the passive `0..16120` receipt
first, then the precise `0..16080` receipt linked to that prelude, and require
a fresh campaign verifier to consume both before any lifecycle claim.

## Method-ratchet iteration 1 — passive receipt and precise rejection

The controller retained the same `fmv_playback` / `E15_fmv` work packet and
reused the closed offline receipt
`ecfd091f44f49943e5e8431ba92e823d55c155f6317a7e6242fcc841934d9126`.
Its derived-pristine input and ten-term, zero-result output remain
byte-identical and untruncated.

The wider passive plan executed in an isolated profile at port 24721. Closed
v2 receipt
`abe75bc65b419092c4858efbc3afc18d54c045ec92271f7c008a1024f96fcbe2`
and batch result
`15d5d47e05e0afc11cb52aa96ed65349d31088583f50faf965e768e1a317c03d`
retain two completed pristine cold-boot jobs. Both finish at emulator frame
16120, cycle 9126623583 and PC `0x8004FEA4` with equal registers, RAM, movie
status, scene state, completion state and Region-B head bytes. Raw counters
derive 32,238 replay frames and 32,238 passive observer frames. The typed
command stream retains the three normalized identity results before
`scenario.runBatch`, joins both ordered job IDs to a completed
`scenario.getBatch`, and confirms owned PID 1377302 stopped.

The precise transfer plan then failed closed on incomplete or truncated
transfer pagination. No precise receipt, raw result, command stream or DMA
event was banked, so the attempted branch is not counted and the exact first
Region-B DMA hypothesis is not evaluated. In particular, the passive
endpoint bytes do not identify a transfer channel, direction, cycle, size, or
sector predecessor.

Generated artifact
`analysis/phase4_fmv_levelb_region_b_dma_attempt.json` SHA-256
`a69ad6ad0681317384141c4d66f4ab69997ca038887009b585fb8ff6bb1fe15d`
mechanically consumes the closed offline and passive receipts, proves the
precise receipt is absent, records zero admitted DMA events, and promotes no
dimension. The executed escalation ledger now admits only the passive
receipt; a fresh campaign verifier must still consume its SHA-256 before the
controller can count it.

The full-cold-boot transfer observer must not be replayed under a new label.
The next method is a typed cold-boot emulator-frame staged prelude that
advances to a bounded point immediately before the retained teardown and
arms `transferLog` only for the finite late window. It requires a new
escalation ID, immutable before-ledger, current manifest identities, paired
same-anchor control, and a new closed passive prelude before live execution.

## Method-ratchet iteration 2 — typed emulator-frame late arming

The work packet again selects only E15 lifecycle and reuses the closed
derived-pristine query receipt
`ecfd091f44f49943e5e8431ba92e823d55c155f6317a7e6242fcc841934d9126`.
Its ten exact DMA/CD/Region-B terms remain zero-result and untruncated. No
new offline query was executed because the missing information is the native
late transfer stream, not a frame-boundary domain already present in the
index.

The debugger's atomic recipe now accepts `staged_prelude:
{kind: emulator_advance, target_frame, max_frames}` only on
`scenario.bootAndRun`. It advances guest execution before observer arming and
returns actual emulator start/target/advanced/status plus movie counters.
The current source dirty-state is
`3c2689e02497ea52fa8f827bee8794b9f4d39bfe`, dispatcher SHA-256 is
`6ff2640dad39f85eacba9e8bbbfdb65d4e3707cb6d8f72cc74bf404579ae8a3e`,
and release binary SHA-256 is
`d68b2c6d25f6795a921f5d1fa64ae33c66af3e3d47a786ee45853170766588cd`.
The API manifest and Canon index bind all three identities.

Both declarative plans use the hash-pinned movie provisioned under this
worktree. The passive pair retains cold-boot bound `0..16120`, stages from
frame 1 to 15720 without instrumentation, and observes exactly 400 frames.
The precise pair retains bound `0..16080`, stages to 15740, arms
`transferLog`, and observes exactly 340 frames with ten-page/100,000-event
capacity. The new `tools/phase4_duckstation_late_batch.py` adapter derives
full replay and late observer counters from the returned prelude and run
results; mutations to kind, target, contiguity, run length, fixture location,
or debugger identity fail closed. The legacy adapter stays byte-identical at
SHA-256
`e94ec290a489484587b50fe72a472dbfa8578a7f17dcaf32f57af2efcf8bb375`,
preserving the closed passive receipt's exact adapter-source reference.

Generated ledger entry
`P4-R6-ITER3-E15-LEVELB-REGIONB-LATE-DMA-PROVENANCE` is planned and names
two receipts: passive
`e15-levelb-region-b-dma-late-passive-prelude` and precise
`e15-levelb-region-b-dma-late-provenance`. The precise window is strictly
inside its passive prelude. Artifact
`analysis/phase4_fmv_levelb_region_b_dma_late_arm.json` SHA-256
`508b7af5b81b8cf37b49dd0944f3e033bc51526eabaeeb2ab12039e05e9b46b6`
records `live_executed=false`, `dimension_promoted=false`, and
`falsifier.outcome=not_evaluated`.

No DuckStation process launched because the iteration-2 immutable
before-ledger does not contain the new escalation. No live receipt was
authored, and the first Region-B DMA remains unobserved. The next iteration
must close the passive receipt first, then may execute the linked precise
receipt; absence, a prior intersection, wrong channel/direction/base,
pagination or counter failure, or endpoint drift falsifies the DMA claim.

## Method-ratchet iteration 1 — late passive receipt and precise rejection

The immutable before-ledger authorized only
`P4-R6-ITER3-E15-LEVELB-REGIONB-LATE-DMA-PROVENANCE`. The passive plan ran
first in fresh config directory `/var/tmp/flik-r4-e15-passive.qJg7oe` on
dedicated port 56241. Closed receipt SHA-256
`d1c901b7c9aebcf9141088332cf4d625f5101d10c10410c50d65d7f14ccce833`
and batch-result SHA-256
`ee8b36d851409dfa4dcdc8c6ab3fd1c7912c874d49f18b19e4c76466912cf414`
retain two completed `scenario.runBatch` jobs over pristine
`SCUS-94288` media and the centrally provisioned LEVEL01 movie.

Each job reports staged-prelude start 1, target 15720, and 15,719 advanced
frames, followed by exactly 400 observed frames. Both finish at emulator
frame 16120, cycle 9126623583, PC `0x8004FEA4`, and SP `0x801FFFD0`; staged
results, terminal status, registers, RAM, movie state, and the 256-byte
Region-B head are identical. Raw receipt counters retain two atomic jobs,
32,238 replay frames, 800 observer frames, zero instructions, and one owned
launch. The normalized identity events precede the batch, and typed cleanup
confirms PID 2939272 stopped.

The linked precise run used a second fresh profile and armed `transferLog`
only after frame 15740. Result validation rejected it before any receipt was
created because transfer pagination was incomplete or truncated. Per the
predeclared falsifier and receipt contract, no incomplete raw stream,
authored digest, transfer event, or precise job count was banked. This result
does not establish absence of a Region-B DMA; it establishes only that the
340-frame observer cannot support the claim.

Generated artifact
`analysis/phase4_fmv_levelb_region_b_dma_late_result.json` SHA-256
`b0ec7e9fa015d94180fc26f74c376d7e343e53ee72a13d29ec5a00ef901d6433`
joins the work packet, immutable before-ledger, reused offline receipt,
static replacement owner, closed passive receipt, absent precise receipt,
and non-promotion boundary. The next experiment family changes to static
subwindow decomposition; the rejected 340-frame transfer observer must not
be replayed under another label.

## Method-ratchet iteration 2 — exact-PC submission subwindow

The measured iteration again retained only `fmv_playback` / `E15_fmv` and
the lifecycle dimension. Recursive inventory found 110 Phase-4 operator
files, 147 broader operator files, and 135 centrally provisioned files.
Ordered regeneration retained 55/55 capsules, 107 queue rows with 91 open
and 42 offline-partial, nine derived indexes over 34 rows, and E15 as the
sole scheduled campaign. The existing closed derived-index receipt remained
the relevant negative answer, so no duplicate offline query or receipt was
authored.

Pristine `BITS/MEMORY.BIN` is 36,448 bytes and hashes to
`e3f869789ed0496a9f6ded235189c14b65de693fe80a20ed6046cf6bfc603e37`.
The resident file helper preserves the Region-B destination in `s3`, saves
the 416-byte destination tail beyond the logical resource end to scratch,
materializes eighteen sectors in `a0`, restores `a1=0x800B5788`, and calls
`CdRead` at `0x80046078`. After synchronous success it restores the saved
tail, undoing the rounded read's overlap. Success polling and the failure
path both join the common epilogue at `0x800460C4`.
Those two pre-instruction PCs therefore bound exactly one selected
submission. A global resident call census finds only this call and the
separate fixed-sector wrapper call at `0x8006FFEC`; every predecessor edge
and destination carrier is classified.

Generated artifact
`analysis/phase4_fmv_levelb_region_b_dma_subwindow.json` SHA-256
`c7d3696ea7fbd0276b57f64f0790b57351932bb10a84e68cf6e80985d5120f07`
binds the opcodes, resource identity, geometry, exact start/stop PCs, global
call census, semantic source, explicit falsifier, and non-promotion
boundary. Focused mutations reject the selected call, resource size,
destination liveness, direct-call census, retired method status, or retained
work-packet falsifier.

This static result does not observe a DMA channel, direction, cycle, sector
predecessor, or destination write. The current `trace.armWhen` recipe tests
its PC condition only at frame boundaries, so it cannot serve as an exact
stop at transient PC `0x80046078`. No DuckStation process launched and no
live receipt was authored. The next static step is a tracked,
mutation-guarded exact-PC stop/arm adapter; only after it validates may a new
escalation and strictly wider passive prelude be declared.

## Method-ratchet trial iteration 1 — exact-PC adapter guard

The retained work packet selected only `fmv_playback` / `E15_fmv`,
lifecycle, and the binding `static` lane. It claimed only that a tracked
adapter could make the already reconstructed exact-PC boundary mechanically
load-bearing before a future live escalation. The explicit falsifier rejects
the wrong first or terminal PC, wrong `a0`/`a1`, instrumentation outside the
paused boundary or in the wrong order, an incomplete result, a mixed server
session, or execution without the current debugger/media identity join.

`config/phase4_fmv_levelb_region_b_dma_exact_pc_arm.yaml` pins:

- start pre-instruction PC `0x80046078`;
- required registers `pc=0x80046078`, `a0=18`, `a1=0x800B5788`;
- exact `transferLog.clear` then `transferLog.start` ordering;
- terminal pre-instruction PC `0x800460C4`;
- a 64-emulator-frame ceiling, 512 bounded status polls per stop, a
  ten-page/100,000-record/64-MiB transfer-result envelope, contiguous indexes
  and `truncated=false`;
- the current RPC manifest, source revision/dirty-state, dispatcher and
  release binary plus pristine `SCUS-94288` media identity.

The adapter validates that closed schema, requires an already paused atomic
anchor, polls the direct temporary-breakpoint method within the finite frame
and poll bounds, checks registers before arming, stops instrumentation before
pagination, and retains normalized command result bodies and hashes under one
server-session label. Its CLI deliberately exposes validation only; live
anchor setup and v2 receipt emission remain a later predeclared runner's
responsibility.

Generated artifact
`analysis/phase4_fmv_levelb_region_b_dma_exact_pc_arm.json` SHA-256
`f29fa343d022f0ac647ad07d78384e652b9c272636f42935f28557fdc72246a4`
retains a deterministic eleven-command synthetic transcript. The focused
guard executes the positive plan and falsifies mutations to both PCs,
`a0`/`a1`, clear/start confirmation and order, source/binary/media identity,
pagination completeness and index continuity, and the poll ceiling.

No DuckStation process launched. No offline receipt was authored because the
retained index already answers the applicable offline question; no live
receipt, native transfer record, or DMA event exists in this iteration.
Lifecycle remains partial and no roadmap dimension is promoted. The next
static action is to predeclare a fresh exact-PC escalation and a strictly
wider passive cold-boot receipt; a future immutable before-ledger must admit
both before execution.

## Trial iteration 1: exact-PC live preflight

The retained work packet SHA-256
`1692855aa412ec5d1eac196105e80c0bd72592d8de5e75058b2500a6f416cb02`
selects only E15 lifecycle and the static lane. The existing closed offline
receipt
`ecfd091f44f49943e5e8431ba92e823d55c155f6317a7e6242fcc841934d9126`
was reused rather than replayed. Its 16,060,589-byte derived-pristine index
still returns zero paths for all ten DMA/CD/Region-B terms with no truncated
path list. Static evidence continues to bind exactly one CdRead submission
between pre-instruction PCs `0x80046078` and `0x800460C4`, with `a0=18` and
`a1=0x800B5788`.

The generated live ledger SHA-256
`5e8fdd9b4cdd0a26b364457e25df130b36157af64211a891c1f4ca20314cc2fd`
contains 29 entries and one planned escalation:
`P4-R6-ITER4-E15-LEVELB-REGIONB-EXACT-PC-DMA-PROVENANCE`. Its typed receipt
set is:

- passive
  `e15-levelb-region-b-dma-exact-pc-passive-prelude`, from the pristine
  LEVEL01 cold boot, staged without instrumentation to frame 15800 and
  observed through 15896 in two identical jobs;
- precise `e15-levelb-region-b-dma-exact-pc-native`, from a fresh isolated
  profile and paused atomic frame-15816 anchor through the finite 15880
  ceiling;
- precise `e15-levelb-region-b-dma-exact-pc-repeat`, repeating the same
  anchor, identities, stops, registers, direct observer, bounds, and result
  limits in another fresh profile.

Both precise receipts link to the passive receipt. The passive capture is
strictly wider by sixteen emulator frames on each side. Each exact contract
requires `scenario.runBatch` for the paused anchor, but names
`transferLog.start` as the direct typed observer; the observer is not hidden
inside the atomic scenario.

Artifact
`analysis/phase4_fmv_levelb_region_b_dma_exact_pc_preflight.json` SHA-256
`16d3da88143ee5ad45188f990450e63bcbe20811992de3850119f3198b38f003`
and 38 focused exact-PC/preflight tests retain the positive plan and reject
drift in the work packet, immutable before-ledger, generated ledger,
derived-pristine input, static boundary, passive width, PCs, registers,
atomic anchor, poll bounds, admission state, and no-live claim.

The immutable iteration-before ledger SHA-256
`57e2a2dae921cdf0286aec7f5dc1682cce89f610e1883eeaf124b63a4ae539f2`
has 28 executed entries and no planned entry. Therefore this iteration did
not launch DuckStation. The direct-command v2 receipt admission path remains
explicitly `not_implemented`: it must retain normalized identity bodies,
one completed runBatch/getBatch anchor pair, the later direct command/result
stream under the same owned server session, complete pages and typed
numeric-PID stop plus confirmation. Until that path is mutation-guarded and
a later immutable before-ledger admits the exact escalation, no live receipt,
DMA event, or lifecycle promotion exists.

## Trial iteration 2: v2 direct-command receipt admission

The compact retained packet selected only `fmv_playback` / `E15_fmv`,
lifecycle and the static receipt-admission boundary. Its claim was that a v2
receipt can join one verified paused atomic frame-15816 anchor to the later
exact-PC direct stream without weakening historical atomic receipts. Its
falsifier rejects a missing or multiple anchor job, late or duplicate identity
calls, mixed server sessions, changed method/parameter/result bodies, wrong
PC or `a0=18` / `a1=0x800B5788`, unbounded polling, incomplete pagination,
terminal-capture drift, a live launch or a synthetic DMA inference.

`tools/phase4_method_metrics.py` now accepts closed observer-plan schema v2.
The schema embeds the already guarded exact-PC plan but keeps
`transferLog.start` as the direct typed observer. Direct command events carry
their finite socket timeout in addition to the normalized result body and its
derived SHA-256. Identity calls remain unique before the atomic batch; later
direct `debugger.status` calls are distinguished by that typed direct-event
shape. The atomic job must end paused at the capture start and have a later
completed result-bearing `scenario.getBatch`.

Admission is not based on authored event labels. The validator feeds the
retained direct results back through
`tools/phase4_duckstation_exact_pc_batch.py`. The adapter independently
re-derives the two stops, register identity, clear/start order, bounded status
polling, complete contiguous transfer pages and terminal atomic capture. It
also requires the exact current RPC manifest, dirty-source identity, release
binary and pristine-media join.

The generated artifact
`analysis/phase4_fmv_levelb_region_b_dma_exact_pc_preflight.json` SHA-256
`106bd41b0ea3a85cf5a1bd29ecc4935314f22936a5851f22e4c81e1bdfa2761f`
retains one synthetic anchor plus eleven direct events. It independently
rejects a changed start command, a non-paused anchor counter and a changed
page count. Focused receipt tests additionally reject register, bound and
historical-schema drift; the pre-existing schema-v1 full receipt fixture still
passes.

The immutable iteration-2 before-ledger SHA-256
`5e8fdd9b4cdd0a26b364457e25df130b36157af64211a891c1f4ca20314cc2fd`
contains exactly the predeclared exact-PC escalation. This work packet
nevertheless stayed static: DuckStation did not launch, no live receipt or raw
DMA event was created, and no subsystem dimension was promoted. Regenerated
debt changes only the method lane from static to live. A later packet must
close the passive receipt before either precise branch and must obtain fresh
campaign-verifier consumption before using an investigator receipt.
