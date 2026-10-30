# Phase 4 static-ASM prerequisite ratchet contract

Scope: shared Phase 4 prerequisite machinery only. This contract does not
authorize edits to F01 artifacts, the mechanics baseline, the direct static
writer census, or any row status.

## Acceptance boundary

This is not a whole-Phase-4 acceptance contract. Judge the candidate only on
the required properties and forbidden shortcuts below. A verifier must return
`closed` when those properties pass and no shortcut is found, even if unrelated
repository-wide gates are red.

The following pre-existing systems are expressly outside this contract and
must not be used to reject this candidate: trace-capsule index versioning,
offline opportunity queues or batch receipts, live-escalation ledgers,
supplemental movies or capsules, the full safe-test suite, Vault-wide lint, and
clean-checkout provisioning of operator-owned inputs. They may be inspected
only to confirm that the candidate did not modify them. Do not repair,
regenerate, relabel, or bank any of them under this ratchet.

Run only the focused validation named by this contract. In particular, do not
turn expected pre-existing Phase 4 debt into an autonomous gap. Closure here
means only that the reusable static-ASM prerequisite receipt is exact,
conservative, and clean-checkout reproducible; it is not F01 closure, Item-2
closure, registry closure, or Phase 4 closure.

## Required candidate properties

- Build from commit `9cd4e13be045aeaebfdf96de21e89ba00bbcc6a8` in a clean detached worktree.
- Use the hash-pinned pristine `SCUS_942.88` image only.
- Compile and run `tools/phase4_static_asm_probe.c` with warnings as errors.
- Regenerate `analysis/phase4_static_asm_prerequisites.json` without absolute
  paths or uncommitted inputs.
- Run `tools/verify_phase4_static_asm_prereqs.py --rebuild` from a second fresh
  detached worktree and require exact JSON equality.
- Compare indirect site identities, not only counts. The only accepted delta
  from the retained 234-site map is the named `jr` at `0x80010364`; the current
  typed candidate universe is 235 sites.
- Preserve all 33,888 unclaimed resident text bytes as `unclassified`. Do not
  rename them padding or claim semantic image ownership.
- Preserve direct-edge CFG and indirect-target closure as different verdicts.
  `scene_flow_dispatcher` must reach 393/393 words in the direct-edge fixed
  point, while `indirect_target_sets_complete` remains false until independently
  proved.
- Keep `item2_ready_for_review` and `strict_frontier_closed` false.

## Forbidden shortcuts

- Do not rerun, widen, reinterpret, or promote the direct static writer census.
- Do not edit any `phase4_f01_*` artifact or the `F01_anthill` baseline row.
- Do not treat code-extent membership as proof of execution.
- Do not treat a complete byte partition as complete semantic ownership.
- Do not accept equal aggregate counts when exact site sets differ.
- Do not use DuckStation JIT or non-interpreter movies.
