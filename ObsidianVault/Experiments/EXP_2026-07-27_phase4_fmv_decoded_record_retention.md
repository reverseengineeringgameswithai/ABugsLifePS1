# Phase 4 FMV decoded-record control — complete observer retention

Date: 2026-07-27
Campaign: `fmv_playback`
Row: `E15_fmv`
Escalation: `P4-ITER104-E15-DECODED-RECORD-RETENTION-CONTROL`

## Claim and falsifier

The exact claim was that the 128-event successor would retain the completed
native function sequence as contiguous indexes 1 through 90 without reaching
capacity, while the paired one-word positive still retained the known
instruction-attributed latch writer and teardown sequence.

The predeclared falsifier rejected the run if the native trace began after
index one, ended after 90, returned more than 90 events, reached the 128-event
bound, truncated, wrote the latch, or lost its same-anchor controls.

## Execution

The immutable before-ledger was SHA-256
`3fd0a8ba1373e3ca17f59d69ca5dae7a1312eaa44c59e5361a536c83c6f7dfb4`.
The passive and precise plans each ran two bounded atomic jobs in a fresh
isolated `/var/tmp` profile on dedicated ports 21401 and 21402. Both profiles
mounted pristine serial SCUS-94288, CUE SHA-256
`463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`
and BIN SHA-256
`2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`.
Owned PIDs 1714407 and 1714603 were stopped through their typed cleanup
actions.

The passive receipt SHA-256 is
`39890a769959d8b2876cd5d37f4e35e40915bee6ff9952bffaa4a26a628e52fe`;
its batch-result SHA-256 is
`91475f91296fdc47cd182833d70273c503862afbff62730b6d7398a940927cde`.
The precise receipt SHA-256 is
`7a27c73b8141155ea24f8cf7e941d32ec4f1677440a38f8a06a67a15732ce187`;
its batch-result SHA-256 is
`bb7e5d0a0bc05471150606bd373e3863bd39a299158b82a73579604edba757d0`.
All raw dependencies remain under the iteration run root and are not
committed.

## Observation

The passive branches finish at equal frame, cycle, RAM, register and capture
endpoints. In the precise positive, the sole predicate change is
`0x800B6C40: 0x1220000E -> 0x1000000E`. Instruction `0x800B6C84` writes the
u8 latch at `0x800B9A54` from zero to one, followed by the ordered helper,
`StClearRing` and callback-teardown events.

The native branch records no latch access or selected teardown event. It
returns exactly 90 function events as contiguous indexes 1 through 90, all 45
balanced entry/exit pairs for helper `0x800B6C24` called from `0x800B7280`.
The observer reports no truncation and leaves 38 events below its 128-event
limit. The falsifier survived.

## Boundary and next lane

This closes the observer-retention defect that falsified the preceding
64-event control. It does not promote lifecycle or any other roadmap
dimension, establish native decoded-record failure frequency or malformed-
media policy, or generalize outside movie frames 650 through 850. Both
investigator receipts remain pending a fresh campaign verifier.

The authoritative machine result is
`analysis/phase4_fmv_decoded_record_retention_result.json`, generated from
`config/phase4_fmv_decoded_record_retention_result.yaml` by
`tools/phase4_fmv_decoded_record_retention_result.py`. Its focused test mutates
the retained indexes, caller, latch access, positive writer, passive endpoint,
prelude join, command-result body and cleanup evidence. The next binding lane
is static partitioning of the remaining pause, repeat, unload/reload and error
owners. The closed decoded-record window must not be replayed.

No MOD-private state, hook or intended behavior was introduced.
