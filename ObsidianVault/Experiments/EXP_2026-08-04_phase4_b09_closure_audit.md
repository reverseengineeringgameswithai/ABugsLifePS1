# Phase 4 B09 closure audit

Date: 2026-08-04

## Result

B09 super jump is **Substantiated Partial / Open**. It is not yet row-level bounded-exhausted.

## Already substantiated

- Power-flags word `0x800A6590`, bit `0x0020`, selects the super-jump path.
- Pristine ASM selects literal `-3072` normally and `-3776` with bit `0x20`.
- The completed takeoff transform produces `-1344` normally and `-1696` for super jump.
- A controlled debugger experiment confirmed a frame-invariant `-352` velocity difference exactly, with identical `+256` gravity thereafter.
- The retained `B09_super_jump_comparison` capsule is complete, untruncated, pristine-media identified, and cycle/frame/RAM/register identical to its control.

## Work still required

- Compile the complete bit-`0x20` read/write/clear frontier for `0x800A6590`, separating other flags in the shared word.
- C-verify the blue-x4 production chain: type 7, extra `0x4000`, ctor `0x27`, action `0x0F`, handler `0x800588D4`, sound `75`, and the bit-set operation.
- Attribute normal reset, respawn, level-transition, save/load, and any exceptional clear/persistence paths.
- Reconcile the retained comparison capsule and controlled A/B experiment with the complete lifetime law.
- Generate a fail-closed B09 closure ledger with zero unexplained bit-`0x20` intersections.

## Runtime decision

No new Interpreter movie is requested yet. Static C/ASM frontier and lifetime analysis comes first. A targeted movie is justified only if a reachable grant/clear transition remains ambiguous after that pass.

Current evidence: `analysis/phase4_b09_super_jump_velocity.json`; retained capsule movie SHA-256 `aa234aef8c091f6633d1f1702f5ba4486d7c9d79d2ae2b49dcdf2c3015975c01`; state SHA-256 `97da88100124d273d0ce9bc03a726314159688a519a7be9700cedc3d4998a226`.

## 2026-08-04 closure result

This audit's acquisition/effect checklist is advanced by [[EXP_2026-08-04_phase4_b09_bounded_exhaustion]], but B09 is **not yet claimed bounded-exhausted**.

The full pointer-relative frontier contains two structural clear stores missed by literal-address-only reasoning: `0x8004867C` writes `1` and `0x800486BC` writes `0` during the generic `player+0x7C` action-lockout family. Static presence does not prove post-acquisition reachability. The prior statement that cannon/knockdown-style lockouts cancel an obtained super jump is retracted.

Observed gameplay establishes level-scoped permanence: once obtained, super jump lasts until level completion, stage exit, or game over. The existing capsule and controlled A/B close the runtime effect. Reconciliation of the two structural stores and exact boundary-reset ownership is reserved for the other agent's Item-2 tool.

## Disposition override (2026-08-04)

Pause B09 as **Substantiated Partial / bounded-exhausted for this workstream**. The unresolved boundary-reset attribution is assigned to the separate Item-2 tooling effort. It remains a partial rather than Verified, but it is not an active gap for this workstream.
