---
kind: experiment
id: EXP_2026-07-15_phase4_contact_object_pool
created: 2026-07-15
updated: 2026-07-15
status: reproduced
confidence: confirmed
system: SYS_contact_object_pool
---

# Phase 4 contact-object-pool experiment

## Question

Can E06 be closed from pristine authority by enumerating every staged source and
encoded allocator call, retaining both dispatch domains, reproducing allocation,
contact and failure controls, and covering gameplay/lifecycle breadth without
inheriting downstream reward or rendering policy?

## Isolation and authority

Every live attempt used a newly created absolute `/tmp` DuckStation config, a
dedicated loopback port/token and only its launcher-owned PID. The retained run
used `/tmp/abl-phase4-i14-contact-26635`, port 26635 and PID 1360513. The
connected instance reported SCUS-94288; mounted CUE/track hashes matched the
pristine pins. Every state was centrally declared, inspected, and verified back
to pristine media before load. The all-full destructive control was deliberately
last, after which owned cleanup stopped that exact PID. The artifact records
DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, binary
SHA-256 `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`
and `cleanup.owned_pid_stopped=true`.

## Static reproduction

`tools/phase4_contact_pool.py` reverified the pinned retail executable, every
staged DAT and every staged `LEVEL*.BIN`. It decoded 1,058 type-`0x3f` rows in
21 DATs, recovered the 16-kind authored set, and separated kind `0x20` (resident
support, no staged row) from 33 descriptor-only indices. It retained 11 exact
function regions plus decisive opcodes, all 34 source-dispatch rows/18 targets,
all 117 walker-dispatch rows/15 targets, 129 metadata-A rows, 129 metadata-B rows,
76 resident allocator calls and 15 aligned encoded overlay hits.

## Runtime procedure

1. Replay the LEVEL01 movie from cold boot, branch only the berry input interval,
   and retain exact pre-edit state equality plus attributed native allocation.
2. Load all 19 pristine gameplay anchors and read every live type-`0x3f` source
   row, all 50 descriptor pointers/targets and all 64 pool records.
3. On one LEVEL01 anchor, call the allocator with controlled ctor-`0x51` metadata
   and compare ordinary free, occupied-next, dead-residue and cursor-wrap cases.
4. Place that record far from and near the player while holding all other fields
   equal, then run the native walker.
5. Repeat the far case with deliberately invalid extreme coordinates to test the
   signed arithmetic boundary.
6. Follow a native berry projectile through native updates to TTL zero; compare
   pause/resume, native death/respawn and fresh allocation.
7. Load LEVEL01, LEVEL02 and LEVEL01 again and compare full source, descriptor and
   pool hashes.
8. As the last RPC, mark all 64 slots allocator-occupied and call the allocator
   with a one-second guest timeout.

## Observation, inference, confirmation

Observation: all 19 source hashes differed; the descriptor table hash did not.
All 16 authored kinds appeared live. Occupancy was 0..4. Ordinary construction
selected cursor+1; the single occupied predicate made it skip; clearing the gate
while preserving residue made it reuse; cursor 63 wrapped to slot 0.

Inference: the shared stable interface is the source-dispatch/pool boundary, not
a one-to-one identity between 50 descriptor slots and authored objects. Cursor
values and residual bytes are not identities. Field `+0x22` is shared gating
state whose update semantics belong to the record subtype/action.

Causal confirmation: the far ctor-`0x51` record retained `+0x22 = 200`; the near
record changed 200 to 1 and state 22 to 16. Native projectile updates each changed
TTL by -1 and retired at zero. Pause froze the record. Respawn restored health 4,
decremented lives and cleared in-flight ownership. LEVEL01 reload restored exact
hashes. Full occupancy returned debugger error `-32005`, reason `timeout`, at the
allocator rather than evicting or returning a slot.

## Failed hypotheses and corrected methods

- The Phase-1 descriptor census was previously described as 50 authored kinds.
  Exhaustive staged source decoding falsified that: there are 16 authored kinds,
  one unstaged supported kind and 33 indices with no type-`0x3f` source role.
- Phase 3 generalized projectile TTL observations to the whole pool. The
  ctor-`0x51` far/near pair falsified a universal tick law while preserving the
  typed walker/allocator gate.
- A larger coordinate delta was initially expected to remain an ordinary far
  negative. Three synthetic `+0x100000` deltas overflowed the signed square sum
  and false-contacted. The retained result is an explicit invalid-domain guard,
  not evidence of authored retail behavior.
- The full-capacity control cannot return to a healthy guest. It was made the last
  RPC and followed by exact owned-PID cleanup rather than attempting to reuse the
  contaminated instance.

## Reproduction and result

Static tests call `phase4_contact_pool.build_static_census()` directly. The live
command is:

`python3 tools/phase4_contact_pool.py --port <dedicated> --token <dedicated> --config-dir /tmp/<fresh> --instance-state recreated`

Retained result: `analysis/phase4_contact_pool.json`, SHA-256
`af95329a1980c2ea814ee71eb4858bfaeb1c0e9c40c7b271ea07bc244caf29f2`.
See [[SYS_contact_object_pool]] for promoted original-game facts. No MOD-private
state, hook, cave or intended behavior was introduced.
