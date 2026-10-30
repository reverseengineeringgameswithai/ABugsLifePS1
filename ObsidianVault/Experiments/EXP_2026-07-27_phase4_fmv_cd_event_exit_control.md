# Phase 4 FMV CD-event player-consumer control

Date: 2026-07-27
Campaign: `fmv_playback`
Row: `E15_fmv`
Escalation: `P4-ITER107-E15-CD-EVENT-EXIT-CONTROL`

## Claim and falsifier

The exact claim was that changing only the player load at `0x800B7420` from
`0x8C422484` to `0x24020001` would reach `CdControl(0x0B)`,
`StClearRing` and callback teardown in that order before movie frame 330,
while the unmodified same-anchor negative would record none of that target
sequence.

The predeclared falsifier rejected the result for a missing or reordered
positive sequence, any target event in the negative, a second changed word,
observer saturation or truncation, a frame-bound violation, endpoint-control
failure, identity mismatch, incomplete pagination or failed owned-PID
cleanup.

## Execution

The immutable before-ledger SHA-256 was
`aef3ee9e2c2c2b191e39ecfdc25b0750f107cb24472330e3fb9db47c6edaeaa9`.
The passive and precise plans each ran two finite atomic jobs in fresh
isolated `/var/tmp` profiles on dedicated ports 27641 and 27642. Both mounted
pristine serial SCUS-94288, CUE SHA-256
`463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`
and BIN SHA-256
`2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`.
Owned PIDs 2859993 and 2860446 were stopped through typed stop and confirmation
actions.

The passive receipt SHA-256 is
`041f8ad69d673ad8e80af4a2b548474ae1ef5597ba63ddea6ff941e50ed300e1`;
its batch-result SHA-256 is
`017af340752e670e98137afccc5c4a5579a33510b17cae78179220bfe183a751`.
The precise receipt SHA-256 is
`395ac5d51b2a14b1d36b53f412c98a3854db7a77efd25b45d8e1f38dc3d83e52`;
its batch-result SHA-256 is
`11a10c866da86a8800711d0ff89ae63823af36d9371d2968bdf0639c0f4e20bf`.
All raw dependencies remain under the iteration run root and are not
committed.

## Observation

The strictly wider passive pair is equal in staged status, run status and
terminal capture. The precise positive verifies, writes, invalidates and
reads back exactly one word at `0x800B7420`. Its first six function events are
balanced entry/exit pairs for `CdControl` from `0x800B746C`,
`StClearRing` from `0x800B749C`, and callback teardown from `0x800B74A4`;
the first call receives command `0x0B`. The trace returns 12 total events
under a 128-event limit, leaving 116 slots.

The unmodified negative records zero function events. Both branches stop at
movie frame 4565 and cycle 2,584,138,962 with scene value one and a cleared
FMV-running latch. The positive has exited the player region; the negative
remains in it. Neither trace reports truncation. The falsifier survived.

## Boundary and next lane

This closes the bounded player-consumer interface between exact value one and
the common exit. It does not establish native CD-event delivery or frequency,
a user-visible Pause result, file-open/decode-timeout/CD-retry behavior,
behavior outside movie frames 250 through 330, lifecycle promotion or verifier
admission. No roadmap dimension is promoted.

The authoritative machine result is
`analysis/phase4_fmv_cd_event_exit_result.json`, generated from
`config/phase4_fmv_cd_event_exit_result.yaml` by
`tools/phase4_fmv_cd_event_exit_result.py`. Its focused tests mutate the
one-word write, target order, native exclusion, passive endpoint,
command-result bodies, prelude join and owned-PID cleanup.

The next binding lane is static: partition the upstream native event-delivery
producer and the distinct file-open, decode-timeout and CD-retry branches,
then select one pristine-triggerable failure edge with a paired observable
outcome. The completed decoded-record and CD-event consumer windows must not
be replayed.

No MOD-private state, hook or intended behavior was introduced.
