# Phase 4 FMV upstream event and failure frontier

Campaign: `fmv_playback`

Row: `E15_fmv`

Dimension: `lifecycle` (`partial`)

Selected lane: `static -> live -> static`

## Work packet

- Exact claim: the remaining resident failure frontier partitions into an
  exhaustive direct `DeliverEvent` surface plus exact file-open,
  decode-timeout and CD-submit-retry owners; one file-open route is narrow
  enough for a same-anchor one-word outcome control.
- Falsifier: reject the partition if a resident direct `DeliverEvent` caller
  is unclassified, any named pristine window/opcode drifts, the selected
  control changes a second word, the native branch takes the failure route,
  the positive omits its diagnostic/shared initialization, or observation
  truncates.
- Evidence domain: the retained `fmv-lifecycle-v2` derived index followed by
  pristine resident EXE/FMV.BIN code, direct JAL xrefs, source ownership and
  function bounds.
- Predicted authoritative layer:
  `analysis/phase4_fmv_failure_frontier.json`,
  `src_re/fmv_failure_frontier.c`, its schema and mutation guards.

## Offline localization

Before reading additional capsule bytes, the iteration queried the central
derived-index catalog and reused:

`~/Downloads/ABL-external-evidence/derived/Phase4/fmv-lifecycle-v2/index.json`

The external index is 16,060,589 bytes, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`,
and retains 4,549 records over registers, RAM, VRAM, SPU RAM and passive block
flow for the E15 and C16 movies.

Closed offline receipt
`5d1fa84670af306fd67daa52029de9df4554a710ec3c6f8c91593a40e2cc552a`
re-executes the tracked reader over a hash-pinned retained copy. Its bounded
JSON search covers `0x80045D5C`, `0x80082484`, `0x800B6DE8`,
`0x800B6C40`, `0x800B6F78`, `0x800B7044`, `0x800B7054` and the phrase
`native event delivery`. All eight return zero paths without truncation. The
answer is useful negative localization: frame-boundary evidence does not
contain these instruction/counterfactual facts.

The previously generated FMV index still establishes the bounded live anchor:
FMV.BIN is resident over movie frames 69 through 416, selected limit is zero
at frame 168 and LEV1A limit 386 is first observed at frame 183. Recorded
Start input begins at frame 334.

## Static observations

The resident executable contains exactly four direct JAL callers of
`DeliverEvent` at `0x8006C3AC`:

| Call site | Owner | Event class | Spec |
|---|---|---:|---:|
| `0x8006BD20` | `spu_fidma_body` | `0xF0000009` | `0x20` |
| `0x8006D6C4` | `def_cbsync` | `0xF0000003` | `0x20` |
| `0x8006D6EC` | `def_cbready` | `0xF0000003` | `0x40` |
| `0x8006D714` | `def_cbread` | `0xF0000003` | `0x40` |

None matches the FMV initializer's registered
`0xF0000003`/`0x8000` pair. The complete `getintr`
`0x8006DEB8..0x8006E440` owner also contains no direct `DeliverEvent` call.
This exhausts only the resident direct-call surface. The precise producer
instruction and native frequency remain behind a BIOS or interrupt-service
boundary.

The three distinct failure families are:

- `0x800B8C8C..0x800B8D88` owns the 16-slot file-open helper and returns
  `-1` at `0x800B8D14` or `0x800B8D2C`. Player predicate `0x800B6DE8`
  branches to diagnostic call `0x800B6E54`, then rejoins shared initialization
  at `0x800B6E60`/`0x800B6E68`.
- `0x800B6CA4..0x800B6D68` owns decode polling with budget
  `0x00800000`. Exhaustion reaches diagnostic `0x800B6CF8`, the ready store,
  active RECT-index normalization and selected-slot RECT-field copy before
  convergence and return.
- `0x800B7044` retries `CdControl(GetlocP)` on zero and `0x800B7054`
  independently retries `CdRead2(0x1C0)`. Demute follows only after both
  submissions succeed.

These are routing, ownership and state facts. They do not establish native
failure frequency, retry counts, failed-handle behavior, missing/malformed
media or visible policy.

## Selected successor

Generated escalation `P4-ITER109-E15-FILE-OPEN-FAILURE-ROUTING` is planned,
not executed. Its passive receipt covers movie frames 160 through 260. The
strictly narrower precise pair stages through frame 170 and stops at frame
240, before the first selected-limit observation and recorded Start input.

The only positive difference is:

`0x800B6DE8: 0x12020018 -> 0x10000018`

Both words target `0x800B6E4C`; the change forces only the exact static
failure route after FMV.BIN is resident. The control asks whether the positive
records the diagnostic from caller `0x800B6E54` and both branches reach
shared initialization from `0x800B6E68`. It does not simulate a naturally
failed file handle.

Both declarative plans pass `tools/phase4_duckstation_batch.py
--validate-only`. The immutable iteration-before ledger did not contain this
new planned ID, so no DuckStation process launched and no live receipt was
authored.

## Executed successor and falsified hypothesis

The next controller iteration's immutable before-ledger contained the planned
ID. Before live work, closed offline receipt
`830ea444284a59a18b3246a5c0a5635a8c4845a05b6f3508cb869282764c737a`
re-executed the pinned reader over the exact retained
`fmv-lifecycle-v2` index. Its bounded search for `0x800B6DD8`,
`0x800B6E54`, `0x800B6E68`, `0x800B8C8C`, the file-open diagnostic and
shared initialization returned zero paths. That result confirmed the missing
domain was exact runtime branch/call behavior.

The strictly wider passive pair completed in one fresh isolated profile and
produced identical terminal captures. The precise pair completed in a second
fresh profile. Both profiles mounted hash-verified pristine SCUS-94288 media,
retained normalized debugger/media identities and stopped their owned numeric
PIDs.

The positive verifies, writes, invalidates and reads back exactly:

`0x800B6DE8: 0x12020018 -> 0x10000018`

Both precise traces retain contiguous indexes 1 through 12, leaving 116
events below the configured 128-event limit. Both record the file helper and
the shared-initialization call from `0x800B6E68` as indexes 5 and 6. Neither
records the predeclared diagnostic from `0x800B6E54`. The positive's retained
selected-limit bytes are `1800f000` little-endian while the native branch
retains `18008000`.

The explicit falsifier therefore fires: the selected one-word change does not
produce the predicted positive-only diagnostic sequence in the bounded,
unsaturated observation. The endpoint divergence is retained as a new
question, not interpreted as a native failed-handle or user-visible policy.
Repeating this semantic live experiment under another label is prohibited.

Closed live receipts are:

- passive:
  `ea877606c378687c24ee4115f115fccd3518609413c2c03eb8208d64ee9a4576`;
- precise:
  `5cd1ea15b947f7aeaaac87d6510127605cdf61fd88dbbc7f46b50b988b56367d`.

`analysis/phase4_fmv_file_open_failure_result.json` independently joins both
receipts to their batch/raw/pagination/command/cleanup dependencies and
records `falsifier.outcome = falsified`. Focused guards mutate the trace
sequence, truncation flag, shared-initialization caller and diagnostic
omission. Both investigator receipts remain pending fresh campaign-verifier
consumption.

## Banking and result

`tools/phase4_fmv_failure_frontier.py --write --check` regenerates the
pristine artifact (SHA-256
`5b357d32fea7fa927eaa05574d97d9245c8f1e5b47da1362ad397e1e4e3b34cb`).
Focused tests recompute both pristine inputs and source pins, verify the
partition/control boundaries, and mutate each direct event caller plus one
load-bearing word in every failure family.

No dimension is promoted: Phase 4 remains 16/107 complete with 148 met, 46
partial and 769 gap dimensions. After the executed control falsifies its
claim, the machine lane returns to `static`: reconstruct the actual
instruction/argument owner of the divergent selected-limit endpoint without
replaying the disproven diagnostic route. No MOD-private state, hook or
intended behavior was introduced.

Original-game facts are retained in [[SYS_fmv_player_streaming]]. Campaign
scope and handoff remain in [[Game Solving Campaign - FMV Playback and Skip]].

## Static endpoint correction

The follow-up static work packet tested one exact claim: the retained four
bytes at `0x800CAC08` are presentation RECT width/height, and pristine
ownership must identify the writer of the divergent native height. The
falsifier required both semantic reclassification and exact writer ownership.

The first half survives. Little-endian bytes `1800f000` decode as signed width
24 / height 240, while native `18008000` decodes as width 24 / height 128.
The exhaustive typed-state census places the actual signed selected frame
limit at `0x80131EEE`, written directly by `0x800B6DC0`. Pristine
initialization fixes height 240 at `0x800B6F18` and width
`display_mode * 8` at `0x800B6F40`.

The ownership half is falsified. `0x800B6F18` is the only direct pristine
height writer, and the RECT pointer escapes through the matching `LoadImage`
wrapper. The wrapper itself does not mutate the RECT, but downstream effects
are not statically closed. Equal-frame/equal-cycle retained endpoints stopped
at different guest PCs, so they cannot supply a writer instruction.

Before another live plan was admitted, closed offline receipt
`fb014629ad46e76e85f7b8f6c46fc05ef9702b1856da0289f378425f0949f40a`
re-executed the tracked reader over derived-pristine index SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`.
Its bounded search finds zero exact field/address/writer terms without
truncation. This is evidence that the index does not answer the exact
ownership question, not evidence that a runtime writer is absent.

Generated machine artifact
`analysis/phase4_fmv_file_open_divergence_ownership.json` has SHA-256
`a0c44bf9dd74ab5e9ef307ea3f882ce5fc160485648f63b953a281c732a06d56`.
Seven focused tests include pristine opcode mutation guards and receipt/index
joins. No dimension is promoted.

## Planned distinct live discriminator

Generated escalation `P4-ITER110-E15-PRESENT-RECT-HEIGHT-WRITER` is planned
for a later controller iteration; no DuckStation process launched here. Its
passive plan repeats the unmodified anchor over the wider movie-frame
150..270 window. Its precise plan performs no guest perturbation and repeats
one two-byte CPU write watch at `0x800CAC0A` over frame 160..260.

The CPU-owner claim survives only if both precise jobs retain the same
unsaturated ordered writer event and final RECT endpoint. Zero CPU events is
an explicit falsifier that selects a later DMA/host `provenanceLog` domain; it
does not authorize a DMA claim. Both batch plans pass the tracked atomic-plan
validator. The prior `0x800B6DE8` branch perturbation is absent.

## Method-ratchet iteration 1 work packet

- Campaign and row: only `fmv_playback` / `E15_fmv`; no coupled row.
- First unmet dimension: `lifecycle`.
- Exact claim: two unmodified same-anchor replays retain the same unsaturated
  CPU halfword-store event or events overlapping presentation RECT height
  `0x800CAC0A` during movie frames 160 through 260 and finish with equal RECT
  and lifecycle endpoints.
- Explicit falsifier: zero CPU writes, a different ordered writer sequence,
  missing old/new values, saturation, endpoint divergence, identity drift or
  incomplete owned-PID cleanup rejects CPU ownership and promotes no
  dimension.
- Evidence domain: the already-queried `fmv-lifecycle-v2` frame-boundary index
  and exhausted pristine direct-xref census, followed only by the planned
  two-byte `accessLog.addWatch` native control after its wider passive prelude.
- Predicted authoritative machine layer:
  `analysis/phase4_fmv_present_rect_height_writer_result.json`, generated from
  the closed live receipts and joined to the typed FMV state/source frontier
  by focused mutation guards.

## Executed native writer discriminator

The immutable iteration-before ledger admitted
`P4-ITER110-E15-PRESENT-RECT-HEIGHT-WRITER`. The passive and precise plans ran
in separate fresh `/var/tmp` profiles on ports 24611 and 24612. Both mounted
hash-verified pristine SCUS-94288 media, completed two finite atomic jobs,
retained normalized identity/command/pagination evidence and stopped only
their owned numeric PIDs.

The passive jobs finish endpoint-identically at emulator frame 4505/cycle
2,550,166,735. The precise jobs finish endpoint-identically at emulator frame
4495/cycle 2,544,504,697 with presentation RECT bytes
`0000380018008000`, selected limit 386, running latch zero and scene one.
Their ordered access payloads are identical after normalizing the per-job
watch ID.

Both precise jobs first record the initializer at `0x800B6F18` writing
`0 -> 240`, then the exact native transition at `0x800B6BF0`
(`sh a0,0x2a(s1)`, word `0xA624002A`) writing `240 -> 128` at emulator frame
4452/cycle 2,520,652,688. The retained census is one event from `0x800B6F18`,
three from `0x800B6BF0`, and 28 repeated events from resident
`0x80064178`.

Each access log returns exactly 32 events against its configured maximum of
32. Although the API reports no internal truncation, the predeclared
unsaturated-sequence predicate is false and its saturation falsifier fires.
The exact `0x800B6BF0` transition is therefore a bounded CPU-writer lead, not
complete ordered ownership. It does not authorize DMA/host, native failure
policy, lifecycle or roadmap-dimension conclusions.

Closed live receipts are:

- passive:
  `31f8d2c06f29f7e0b0fb7c4bad39d972113f45aa26fdc3b4d8fc6aa8fff104fb`;
- precise:
  `fcff7c2012a29255824096e3bb7f782cc7bbb1772c58da379faf19113c04ad8f`.

`analysis/phase4_fmv_present_rect_height_writer_result.json` independently
joins both receipts to their batch, raw-result, pagination, command-event and
cleanup dependencies. Its focused guards mutate the capacity, event totals,
writer instruction, width and repeat sequence. Both investigator receipts
remain pending fresh campaign-verifier consumption.

No dimension is promoted: Phase 4 remains 16/107 complete with 148 met, 46
partial and 769 gap dimensions. The binding next lane is `static`: reconstruct
the `0x800B6BF0` cached-height/presentation-RECT pointer alias, exact caller
boundary and resident `0x80064178` helper before defining a finite successor.
Repeating the saturated semantic experiment under another label is
prohibited.

## Method-ratchet iteration 2 — falsified timeout-field hypothesis

The iteration-2 packet claimed that the timeout helper copies the selected
RECT slot's width and height into the presentation RECT. Its explicit static
falsifier fired. Pristine instructions load halfwords at `0x800B6D18` and
`0x800B6D30` from source offsets `+0x10` and `+0x12`, then store them at
`0x800B6D2C` and `0x800B6D38` to destination offsets `+0x24` and `+0x26`.
The authoritative layouts in `config/phase4_fmv.yaml` and
`analysis/phase4_fmv_static_owners.json` type those fields as selected-slot
`x`/`y` and presentation `x`/`y`. Presentation width and height are at
`+0x28`/`+0x2A`; this function contains no store to either field.

The corrected static transition has decrement-before-test budget
`0x00800000`, sole direct caller `0x800B72A0`, timeout diagnostic
`0x800B6CF8`, ready `1`, active-index replacement only when its old value is
zero, the selected-slot coordinate copy, and convergence through ready clear
`0x800B6D4C` to the sole conventional return at `0x800B6D60`.
`analysis/phase4_fmv_failure_frontier.json` preserves the rejected
width/height hypothesis as `falsified` beside the corrected coordinate claim
as `survived`. Focused mutation guards cover both typed layout authorities
and every load/store, index, clear, return and caller-chain instruction used
by the claim.

This packet reused the valid capsule/index catalog only to establish evidence
availability. It issued no offline query, scanned no capsule bytes, launched
no DuckStation process and authored no live receipt. The correction proves no
natural timeout occurrence, frequency, visible behavior, malformed-stream or
CD-failure policy. It promotes no runtime result, lifecycle dimension or row,
and introduces no MOD-private state or intended behavior.
