---
type: experiment
status: complete
date: 2026-08-10
system: F01 objective lifecycle
phase: 4
dimensions: [original_oracle, campaign_breadth]
work_order: engineering-specs/phase4-f01-oracle-breadth-repair-work-order.md
artifacts:
  - analysis/phase4_f01_oracle_breadth_repair.json
  - analysis/phase4_f01_original_oracle.json
  - analysis/phase4_f01_request2_probe.json
  - analysis/phase4_f01_breadth_assertions.json
---

# F01 oracle and breadth repair — fail-closed, detached result

## Result

The repair work order completed with an eight-element ledger: **5 DONE, 1
BLOCKED, 2 NOT DONE**. James's fresh hard-truth audit accepted commit
`3cbcfbee9b68cc734e4ffcbd38b3bce987bebdf2` after independently reproducing the
gates and retained results. This is a repair of evidence quality, not a dimension
promotion: `original_oracle` and `campaign_breadth` both remain **NOT MET**.

| element | outcome | measured result / remaining dependency |
|---|---|---|
| Part A — harness integrity | **DONE** | 1/1; exact 19-level universe, typed decision operands/coordinates, self-certifying instruction words, reconciled trace counts, and fail-closed errors/truncation |
| B1 — natural request-2 skip control | **BLOCKED** | 0/1; both pinned cold-boot candidates replayed, but neither produced a resident death store; needs a centrally pinned cold-boot movie in which Flik dies naturally |
| B2 — fail-closed oracle provenance | **DONE** | 1/1; 25/25 provenance and 6/6 semantic assertions |
| B3 — detached oracle regeneration | **DONE** | 1/1; three byte-identical generations |
| C1 — pre-outcome applicability matrix | **NOT DONE** | 0/1; denominators for stages, objectives, actor/enemy variants, special modes, and exceptional paths remain unknown |
| C2 — independent eight-type mapping | **NOT DONE** | 0/1; 0/19 levels independently mapped and 0/8 types closed |
| C3 — fail-closed corpus gate | **DONE** | 19/19 levels, 35/35 self-certified decisions, 0/35 law failures |
| C4 — detached breadth regeneration | **DONE** | 19/19 exact-final replays; two consolidations matched the retained artifact byte-for-byte |

The authoritative structured record is
`analysis/phase4_f01_oracle_breadth_repair.json`. The prior adjudication in
[[EXP_2026-08-10_phase4_f01_oracle_breadth_verification]] remains the historical
pre-repair verdict; this note records the accepted repair result.

## Confirmed observations

### Branch law over the declared 19-level corpus

Every counted decision executed the pristine word `0x846323A0` at
`0x8004FF28` and retained typed request / `$gp+0x4c4`, frame, cycle, and
finalizer-attribution fields. The exact declared universe produced **35** certified
decisions:

| predicted path | decisions | observed result |
|---|---:|---|
| CALL `0x80045A60` | 19 | 19 attributable calls |
| SKIP `0x80045A60` | 16 | 16 skips |

There were **0/35 law failures** for the branch:

> At the `0x8004FF28` decision, the finalizer is called iff
> `request != 2 && [0x8008225C] == 0`.

This is bounded to the exact declared corpus and certified decision windows. It
does not turn the 19 sessions into a complete applicability matrix.

### Natural request-2 control remains missing

The two work-order candidates were replayed from pristine cold boot with no
injection and complete, non-truncated access and execution pages:

| candidate | span | decision result | request-word access evidence |
|---|---:|---|---|
| D18 | 15,600/15,600 frames | one certified request-1 decision | 8/8 overlapping writes; zero resident death-store hits |
| E02 | 5,562/5,562 frames | no transition decision | 7/7 overlapping writes; zero resident death-store hits |

The request-word watch retained every byte/half/word write overlapping the two
bytes, including KSEG aliases. Only aligned resident pristine halfword stores at
`0x8004A8B4` or `0x8004A9F4` could certify a complete death request. Overlay file
identity was not inferred from a runtime PC without residency evidence.

Therefore the honest B1 result is **BLOCKED**, not DONE: the older injected
request-2 witness and state-anchored natural-death evidence remain useful bounded
evidence, but neither satisfies this work order's cold-boot natural-producer bar.

## Evidence identity and reproducibility

All runtime work used Interpreter mode and pristine `SCUS-94288` media:

| item | SHA-256 |
|---|---|
| CUE | `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644` |
| BIN | `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566` |
| canonical `SCUS_942.88` | `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20` |
| DuckStation binary | `2ddaad7b1fdbca78110e3a871fd15496923e03be470d2e08e356a006b460dcf4` |

DuckStation revision:
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`. The fork had a recorded dirty
source census, so the binary hash is part of the identity rather than treating
the revision alone as sufficient.

The exact retained outputs are:

| artifact | SHA-256 |
|---|---|
| `analysis/phase4_f01_original_oracle.json` | `3c5c060478cb4d86b73800e17bd0bbf2fd8d14018c19c4fc1970c1ee9b4d5723` |
| `analysis/phase4_f01_request2_probe.json` | `9f15d00e9b38780547f8bf7bcedfd3bef04fc21cf61fedf708de4304a47d48bf` |
| `analysis/phase4_f01_breadth_assertions.json` | `4b58c2c9c67c4f8f10345e4b723bc598e5f0968353385ef71c878f95559429cc` |

The exact-final detached checkout was commit
`9fd829a680c179a84b49feb69997e433c92f6b31`. It was separately provisioned
from central relative movie/state identities and the canonical executable path.
The oracle replay matched the retained artifact exactly. Six fresh isolated
breadth workers on ports `24760..24765` completed **19/19** reproducible,
non-truncated replays; two final consolidations both produced the retained
`4b58c2...` bytes. Each owned emulator process was stopped through its exact
config directory. Tokens were unique and ephemeral and were not retained.

## What the repair gate now rejects

Committed adverse tests reject empty, missing, extra, renamed, and duplicate
level universes; zero-decision rows; missing or mismatched instruction
certificates; missing request/flag operands or coordinates; boolean deltas;
lying law summaries; errors and incomplete/non-reproducible playback; true,
null, or absent truncation; inconsistent event totals; missing retained/rejected
count maps; and fixture, movie, start-state, media, executable, hash, size, class,
or preservation mutations.

The oracle derives `from_boot`, start-state, movie, media, completion,
reproducibility, and trace properties from the runtime evidence and central
manifest. Output no longer embeds checkout-local media paths or a wall-clock
generation date.

## Limits and next evidence

- B1 closes only with a centrally pinned pristine cold-boot recording in which
  Flik dies naturally. Its complete trace must certify the resident request-2
  producer, the consumer decision, and no attributable finalizer call.
- C1 requires a complete independently sourced pre-outcome matrix for stages,
  objectives, enemy/actor variants, special modes, and exceptional paths. Each
  cell must be uniquely classified and backed by a pinned assertion or a
  reproducible inapplicability proof.
- C2 requires an independently derived mapping of only the declared 19-level
  corpus into normal, traversal-special, boss, chase, city, interior, exterior,
  and bonus, with at least one passing replay per type. Labels fitted to the
  already-known outcomes do not qualify.

No edit was made to `analysis/mechanics_baseline.yaml` or
`analysis/phase4_movie_priority_queue.json`, and no F01 status changed.

Related: [[EXP_2026-08-10_phase4_f01_original_oracle]] ·
[[EXP_2026-08-05_phase4_f01_objective_lifecycle]] ·
[[MEM_800823A0_scene_transition_request]] ·
[[FUNC_80045A60_transition_finalizer_-_subsystem_reset]] ·
[[Level_Goal_and_Exit_Trigger_Matrix]]
