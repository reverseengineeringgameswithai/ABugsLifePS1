---
kind: experiment
id: EXP_2026-07-19_phase4_fmv_static_owners
created: 2026-07-19
updated: 2026-07-20
status: reproduced_partial
confidence: high
source_state: original_game
row: E15_fmv
evidence: [analysis/phase4_fmv_static_owners.json]
---

# Phase 4 FMV static selector owners

## Question and lane

The closure-debt scheduler selected only `fmv_playback` / `E15_fmv` with
`next_lane: static`: finish caller, player, and completion ownership before
another replay. The retained E15 derived index already covers its movie and
frame-boundary domains, so no capsule bytes were rescanned and no DuckStation
escalation was opened.

## Reproduction

The deterministic command is:

```text
python3 tools/phase4_fmv_static_owners.py --write --check
```

It verifies the centrally pinned pristine `REBUILD/files/SCUS_942.88`,
`REBUILD/files/FMV/FMV.BIN`, and `REBUILD/files/BITS/MEMORY.BIN`, then
reconstructs only address, opcode, table, path and hash metadata. No retail
binary bytes are retained in Git.

## Observations

- `0x800B6250..0x800B6634` bounds selectors with
  `sltiu v0,s0,47`, dispatches through 47 words at `0x800B5AA4`, selects all
  40 manifest rows, and sends selectors 3..9 to the no-stream target.
- The pristine resident executable has exactly nine direct `jal 0x8003E7C0`
  sites. Fixed callers select dlogo, title, intro, LOSE, LEV15C and LEV15D.
- The 16-byte table at `0x8007A08B` maps nonzero music/progress IDs to all 15
  level-A selectors. IDs 4 and 5 resolve LEV5A and LEV4A respectively; the
  artifact retains this byte-derived order rather than normalizing it.
- The 16-byte table at `0x80077FE3` uses an ID-zero sentinel and maps IDs
  1..15 to every level-B selector.
- The sole resident reader/writer pair for the byte at `0x8009B88A` increments
  it modulo 256 and passes `next + 41`. Old values 0..4 select ALT1, ALT2,
  ALT3, INTRO and LOSE; 5..254 are outside the 0..46 selector range; 255 wraps
  to LEV15D. The nearby bonus-flags byte is replaced with
  `17 * (old & 0x0F)` on this path.
- Selector 2 is the `fmv/ad.str`, limit-1410 manifest row. All direct loader
  argument sources reach exactly selectors 0, 1, and 10..46. The loader's
  address is absent as data in SCUS, FMV.BIN, and MEMORY.BIN, and the retained
  exhaustive 139-site resident `jalr` census installs no loader callback.
- Completion request `0x800CAC10` has exactly four aligned xrefs in FMV.BIN:
  set writers at `0x800B6B24` and `0x800B6B48`, stream-start clear at
  `0x800B6DD0`, and the only reader at `0x800B743C`.
- The player is exactly `0x800B6D68..0x800B752C`, with 50 direct calls to 30
  unique targets and no `jalr`. Request value one branches at `0x800B7444` to
  stop target `0x800B6E38`; teardown is `0x800B7464..0x800B752C`.
- The loader pointer is absent as a literal and as a standard `lui`/`addiu` or
  `lui`/`ori` materialization from all 23 pristine resident, level, MEMORY and
  FMV code-owner images. Three formerly unresolved resident `jalr` sites target
  BIOS vector `0xB0`; the fourth receives a GPU callback argument that cannot
  be supplied the unmaterialized loader address.
- The executable FMV code ends at `0x800B9A4C`. Across that complete code extent,
  every direct absolute access in three declared player-boundary state ranges
  is classified: 30 Region-B address rows have 99 exact absolute xrefs,
  including 58 in the player and six pointer aliases, with zero unclassified
  xrefs. The repaired decode-commit record includes prior decoded-frame index
  `0x800B9A50` (writer `0x800B6B14`), cached width `0x800B9A58` (xrefs
  `0x800B6B54`/`0x800B6BB8`/`0x800B6BD0`) and cached height `0x800B9A5C`
  (xrefs `0x800B6B6C`/`0x800B6BC0`/`0x800B6BE0`). The reconstructed layouts
  also include the two-pointer/active-index block, two-slot RECT bank,
  presentation RECT, entry ABI, scalar domains and allocation teardown.

## Inference and rejected overclaims

The pristine selector sources, computed-target exclusion, player call graph,
completion-request xrefs and important player-boundary typed state are exact.
Selector 2 is therefore a reviewed unreachable pristine manifest row, not an
indirect advert/movie-viewer route. That negative result does not establish any
movie-viewer behavior.

The iteration-2 complete-frontier promotion was too strong and is superseded.
Libcd/libpress callback ABI, frontend/movie-viewer and level-transition
consumers, remaining transition writers and exceptional-path functions still
intersect E15. Complete-frontier is demoted to partial. Typed-state is promoted
instead because its important player-owned fields, widths, signed views,
aliases, domains and lifecycle are now low-level guarded. Static reachability
still does not prove natural breadth, pause/stop, replay, unload or fault policy.

The exact historical `analysis/phase4_fmv.json` receipt predates the current
batch/escalation requirement. It is accepted through a non-extensible machine
exception bound to SHA-256
`c5b674a73b546c2143b014f8c43453895b65edfcff010f7287581ef9edccb8b3`;
the bounded dependency reconciler changed only current source/config identities
and preserved the historical runtime/control payload. The generator requires pristine
mounted/save media, binary/RPC identity, same-anchor positive and negative
controls, bounded untruncated trace coverage, a from-boot anchor, and owned-PID
cleanup. Any future E15 live run still requires a predeclared escalation and a
validated batch plan.

The original-oracle and typed-state dimensions are promoted. Complete-frontier
and the other six dimensions remain partial; E15 itself remains active and open.
The iteration-3 typed-state promotion was incomplete: its authored whitelist
omitted the three decode-commit fields and seven xrefs above. The repaired
generator first enumerates all direct accesses in the declared ranges, fails
any unclassified address, and only then verifies the typed whitelist.
Missing-known-xref and unclassified-in-range mutations independently fail.

## Iteration decision receipt

- Capsule preservation command: the full `phase4_trace_capsules.py` validator
  with the Phase4 v2/v1, A10/A11 and bonus-objective sets, complete preserved
  runtime, `SHA256SUMS`, and pinned offline reader; result 55/55 capsules and
  3,391,058,326 external bytes.
- Queue command:
  `python3 tools/phase4_offline_queue.py --movie-root ~/Downloads/ABL/movies --write --check`;
  result 107 rows, 91 open, 0 offline-ready, 42 offline-partial, 0 live-required
  and 65 without a capsule.
- Derived-index command: `python3 tools/phase4_derived_index.py --write --check`;
  result nine indexes covering 34 rows. E15 reused
  `~/Downloads/ABL-external-evidence/derived/Phase4/fmv-skip-v1/index.json`,
  SHA-256 `caa4bef3e219787f2178c0e8826dd6992d62af3491f780d16fcff6d9a9eb12d7`,
  1,875,785 bytes and 542 records.
- Offline batch command:
  `python3 tools/phase4_offline_fmv_batch.py --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/fmv-skip-v1/index.json --check`;
  result one row, one capsule, 542 records, exact external hash match.
- Debt command: `python3 tools/phase4_closure_debt.py --write --check`; result
  16/107 complete rows, 146 met dimensions, selected only `fmv_playback`, and
  retained `next_lane: static` for `complete_frontier`. The corrected verifier
  baseline was 145 after invalidating the incomplete typed-state claim; the
  exhaustive repair restores that dimension and the valid total to 146.
- Derived static findings: 47 selector targets, 40 stream cases, seven no-stream
  cases, nine direct resident callers, 15 level-A and 15 level-B selections,
  selector 2 reviewed unreachable through the 23-image computed-target proof,
  four completion-request xrefs, a 50-call/30-target player frontier with no
  indirect call, and 30 typed address rows with 99 xrefs/six aliases across
  three enumerated ranges and zero unclassified accesses.
- Dependency reconciliation command:
  `python3 tools/phase4_reconcile_upstream_dependencies.py --write --check`,
  followed by `python3 tools/phase4_reconcile_assertion_pins.py --write --check`;
  retained runtime/control payloads remain identical while the expanded FMV
  schema identity and assertion pins advance. The reconciled historical receipt
  is SHA-256 `c5b674a73b546c2143b014f8c43453895b65edfcff010f7287581ef9edccb8b3`.
- Date-stability guards preserve an existing generated date in
  `phase4_reconcile_assertion_pins.py` and `phase4_gate.py`; focused tests pin
  `2001-02-03` while monkeypatching the host date and require no rewrite.
- Static artifact: SHA-256
  `926587abe7e4f5445563b741b8050a9942d3ab85a4b3f44dc777251f1321ac3d`.
- E15 live escalation record: none. The generated ledger remains valid with its
  six historical entries, but none authorizes work for E15; static debt remains
  higher priority and reduced one dimension this iteration.

## Iteration 102 decoded-record control preflight

The regenerated closure ledger selects only `fmv_playback` / `E15_fmv`, keeps
`lifecycle` as the first unmet dimension, and moves the exhausted static
continuation question to the live lane. Before authoring a replay, closed
offline receipt
`3844cbc22d3a202e46ebb7ee69c5064f18b48828cac7afd4c76fda5362faebdb`
re-executed the tracked reader over all 16,060,589 bytes of the exact
`fmv-lifecycle-v2` index. Its bounded seven-term search found zero occurrences
of `0x800B6C40`, `0x800B6C84`, `0x800B9A54`, the absent-record predicate, the
stop latch, a same-anchor basis, or a native control. The retained index
therefore cannot answer the instruction-attributed counterfactual.

Static reconstruction supplies the exact experiment boundary. Pristine word
`0x1220000E` at `0x800B6C40` branches when the decoded-record pointer is
absent; the target contains pristine byte store `0xA0229A54` at `0x800B6C84`.
The passive and precise P4-ITER102 plans stage the same C16 recording to movie
frames 649/650. Only the precise positive changes that branch to
`0x1000000E`; the negative preserves pristine code. The observer is bounded to
the latch write and exact player/common-teardown functions. Mutation guards
reject branch drift, a perturbed negative, pair drift, or a passive window that
is not strictly wider than the precise capture.

No DuckStation process launched. The controller's immutable iteration-before
ledger contained zero planned entries, so a P4-ITER102 receipt created now
could not join an already planned investigator escalation. The generated
ledger retains the entry in `planned` state for the next controller iteration,
which must execute the passive receipt before the precise control. No runtime
outcome, lifecycle dimension, Canon fact, or MOD-private contract is promoted.
