---
type: experiment
status: complete
date: 2026-08-10
system: F01 objective lifecycle
phase: 4
dimensions: [original_oracle, campaign_breadth]
artifacts:
  - analysis/phase4_f01_oracle_breadth_verification.json
  - tools/phase4_f01_oracle_breadth_verification.py
  - tools/phase4_f01_write_watch_pc_probe.py
---

# F01 oracle and breadth — fresh-verifier adjudication

> [!important] Historical pre-repair verdict
> This note records the rejected baseline and the work order's starting point.
> The accepted repair result is banked in
> [[EXP_2026-08-10_phase4_f01_oracle_breadth_repair]]. Both dimensions still
> remain NOT MET; what changed is the strength and reproducibility of the
> evidence, not registry status.

## Verdict

| dimension | verdict | decisive missing element |
|---|---|---|
| `original_oracle` | **NOT MET** | no natural request-2 skip control, fail-open provenance, and no byte-identical detached regeneration |
| `campaign_breadth` | **NOT MET** | no applicability universe, no independently fixed taxonomy, a fail-open corpus gate, and no exact detached regeneration |

No registry edit or F01 status movement is authorized. The stale scorecard sentence
that says `campaign_breadth` is LEVEL01-only remains factually stale as an observation
summary, but staleness does not supply the missing type mapping.

## Freeze and independence

Pre-outcome commit `b079b0342530abb9c2b398b678fab493aa34c2d4` froze baseline
`a3aa41270c0c78373d4afb85e8f4e94f6731059b`, the 114-line dirty-status hash,
both submitted artifact/tool hashes, the dimension bars, and every adversarial check.
Both dimensions were explicitly `NOT_EVALUATED_PRE_OUTCOME` in that commit.

Runtime checking used a detached worktree at the freeze commit, freshly created
absolute DuckStation config roots, dedicated loopback ports and tokens, the repro
launcher, and `[CPU] ExecutionMode = Interpreter`. The pristine identities were:

- cue SHA-256 `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`
- bin SHA-256 `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`
- `SCUS_942.88` SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- DuckStation binary SHA-256 `2ddaad7b1fdbca78110e3a871fd15496923e03be470d2e08e356a006b460dcf4`

All owned emulator instances were stopped through their exact config directories.

## What reproduced

### `original_oracle`

Two independent 7,385-frame from-boot replays reproduced every semantic field in
`analysis/phase4_f01_original_oracle.json`.
It observed scene timeline `624 -> 0 -> 1 -> 0`, one decision with request `1`,
`[0x8008225C] == 0`, and one finalizer call 28 cycles later. The trace was not
truncated. All **6/6** formal assertions pass and all **6/6** reject their direct
adverse value mutation.

Exact regeneration nevertheless fails. The retained artifact's SHA-256 is
`419b229cf669a905b6094bf9cf547be1cf5ffe808441e4f3b22d3f113f1b12d7`; James's
fresh detached replay produced
`ca3fa12f07f8a7bdf45aa97fdb4d2cb60c4e7bed4440a2b71f6c81f0315d77b4`.
The **1/1** differing field is `media.path`: the generator copies the emulator's
absolute cue path, so the live-root and detached-root strings differ. Normalizing
that identity and obtaining a byte-identical result from a separately provisioned
checkout would close this regeneration gap.

That result does not answer the registered residual. The prior skip witness still
starts from a validated save state and explicitly writes `u16 2`; this new natural
run produces request **1**, not request **2**. A natural pristine-from-boot death
route that produces request `2` and observes the consumer proceed while the finalizer
is skipped would close that half.

Two provenance gates also fail open. `from_boot` is hardcoded into the generated
document rather than derived from the loaded movie, and trace truncation is recorded
but not included in `all_passed`. The actual movie metadata is genuinely from boot,
but the 5,062,842-byte movie is absent from
`analysis/phase0_2_external_fixture_set.json`. Deriving and mutation-testing the
anchor/media/non-truncation predicates plus centrally pinning the movie would close
that evidence-envelope gap.

### `campaign_breadth`

The retained data themselves are internally strong: **19/19** movie hashes and
**19/19** state-anchor hashes match both their metadata and central pins; **35**
decisions split into **19 CALL / 16 SKIP**, with zero retained law failures and
both skip edges represented.

The frozen window sensitivity was exhaustive over integer windows `0..10000`:

- windows `0..27`: 19 law failures;
- windows `28..10000`: zero law failures;
- first possible false attribution of a skip to a later call: 1,164,325,801 cycles.

So the retained 2,000-cycle window is safely inside the stable passing interval
`28..1,164,325,800`.

The exact submitted generator nevertheless fails the required detached regeneration.
All **19/19** observation-session movie paths are absolute under
`~/Downloads/ABL`, while `replay_one` serializes each with
`path.relative_to(ROOT)`. Five isolated workers launched. LEVEL10 completed its
full 35,586-frame reproducible replay, then the worker threw because that absolute
movie is not below the detached root. Result SHA-256:
`a20ada1111cb9f96d31acfcc04e382548715a3cdb5a751b265cd053442a018cf`.
The four in-progress owned runs were canceled once the deterministic common failure
was established. Thus **0/19** results serialized and no breadth artifact regenerated.

The consolidator also returns success for **3/3** invalid corpus mutations: an empty
result set, a zero-decision level, and a truncated trace. The retained corpus happens
to contain at least one decision and a non-truncated trace in **19/19** levels, but the
gate does not enforce either fact.

Finally, there is **0/19** structured mapping from levels to the required categories:
normal, traversal-special, boss, chase, city, interior, exterior and bonus. Same-author
prose says all eight are present but never assigns the levels; assigning labels from
these results would be post-outcome selection.

That is not the only missing coverage layer. The frozen bar requires every applicable
stage, objective, enemy/actor variant, special mode and exceptional path. There is
**0/1** declared applicability matrix, so the denominators for all five layers are
unknown: 19 submitted sessions are observations, not a completeness proof. Objectives,
variants, modes and exceptional paths are therefore **NOT DEMONSTRATED**, not silently
treated as covered or inapplicable. A pre-outcome matrix must classify every cell,
bind each applicable cell to a centrally pinned fixture and self-certifying assertion,
and give every N/A cell a reproducible reason. The eight-type map then satisfies its
taxonomy layer only. A fail-closed gate must require the entire declared matrix after
checkout-independent path handling.

## Store-PC convention — survived

The compiled-C objective tool regenerated byte-identically with **87/87** instruction
pins and confirms `sh` stores at `0x800496D8` and `0x800496F8`.

A separate fresh LEVEL02 access watch then captured exactly one code-3 event:

| field | value |
|---|---|
| frame / cycle | `40421` / `22886031829` |
| compatibility `pc` / `reported_pc` | `0x800496FC` |
| `instruction_pc` | **`0x800496F8`** |
| instruction word | `0xA42223A0` — `sh v0, 0x23a0(at)` |
| old -> new | `0 -> 1`, width 2 |

The historical compatibility PC really is store+4 for this event, while the current
instruction-attributed field directly identifies the store. The code-3 correction is
therefore confirmed without promoting the compatibility behavior into an API contract.

## Work-order attacks

- §4a **FAILED** — formal value assertions are falsifiable, but anchor/truncation and
  three breadth corpus-shape mutations do not fail closed.
- §4b **SURVIVED** — 2,000 cycles is stable over the measured attribution geometry.
- §4c **SURVIVED, bounded, with arithmetic corrected** — compiled-C re-derivation
  finds **1,246** distinct `jr`/`jalr` occurrences across **22/22** unique images /
  **143,060** words. The submitted `2,340 / 260,307` totals double-counted SCUS and
  omitted the one-word LEVEL00 sentinel. The unresolved sites still forbid a proof
  or exclusive-reachability claim, but do not erase replay-local observations.
- §4d **FAILED** — no independently fixed level-type mapping exists.
- §4e **SURVIVED** — fresh `instruction_pc` evidence confirms the code-3 store.
- §4f **SURVIVED** — both tools are non-promoting; oracle evidence is one from-boot
  movie (replayed twice) and all 19 breadth movies are state anchored, exactly as disclosed.

Reproduce the offline arithmetic and mutation receipt with:

```bash
python3 tools/phase4_f01_oracle_breadth_verification.py --check
pytest -q tests/test_phase4_f01_oracle_breadth_verification.py
```

Related: [[EXP_2026-08-10_phase4_f01_original_oracle]] ·
[[EXP_2026-08-05_phase4_f01_objective_lifecycle]] ·
[[Level_Goal_and_Exit_Trigger_Matrix]]

## James hard-truth ratchet — accepted

James independently accepted exact candidate
`a35982d815f5dabf96baa132da93cfe24d820b71` with `accepted: true` and **0 gaps**.
The ratchet rejected two earlier candidates before acceptance:

- root rejected `05940020be8ba6a7ce85def2021ad2095137fbbd` after a detached check
  exposed checkout-relative save-path handling in the new verifier;
- James rejected `723d12b88cd69784fd59199c2f8acb19ab2521a2` because the oracle's
  absolute `media.path` prevented byte equality, the indirect census double-counted
  SCUS, and breadth omitted required applicability layers;
- `a35982d815f5dabf96baa132da93cfe24d820b71` repairs all three without changing
  either submitted evidence artifact or promoting either dimension.

Acceptance independently re-established build identity **327/327**, verifier PASS,
**34/34** focused/identity/extent tests, extent **1,087 files / 2,150 declarations /
17 reviewed / 0 new**, clean detached tracked status, and both final verdicts:
`original_oracle` **NOT MET**; `campaign_breadth` **NOT MET**.
