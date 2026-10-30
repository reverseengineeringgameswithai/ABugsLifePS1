---
title: Phase 4 D03 enemy contact damage bounded exhaustion
date: 2026-08-04
phase4_row: D03_contact_damage
status: substantiated partial, bounded-exhausted
---

# Phase 4 D03: enemy contact damage

## Question and method

D03 required the attack/hitbox, invulnerability-window, and knockback
relationship, not another enemy-by-enemy damage anecdote. This pass followed the
Phase 4 acceleration order:

1. Query accepted retained capsules before live replay.
2. Reconstruct RAM frame boundaries with C and verify each embedded domain hash.
3. Analyze the hash-pinned pristine `SCUS_942.88` directly in C for exact
   instructions, branch targets, and the complete caller set.
4. Escalate to DuckStation only for a named domain absent from both sources.

No live replay was needed.

## Evidence identity

- Pristine executable SHA-256:
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Capsule preservation index: `analysis/phase4_trace_capsule_set.json`.
- All six selected capsule entries report `control_match: true` and
  `preservation_required: true`.
- D11 grub capsule manifest SHA-256:
  `2e9ea2379f7dda3cbcafd3bd444a95a5627652f5ba08a91b40a391c3c13a84bb`.
- C reducer result: 2,692 boundary records, 8,076 RAM/VRAM/SPU-RAM hash
  checks, zero mismatches.

The analyzed capsules were `B07_health_partial_full`,
`D08_fly_contact_kill`, `D09_cockroach_contact_kill`,
`D11_grub_contact_kill`, `D11_mite_contact_kill`, and
`D15_daddy_long_legs_contact_kill` under the declared Phase 4 v2 external
evidence root.

## Observations

Three capsules contain a natural contact-health event:

| Family | Hit frame | Health | Timer | State | Ground/air | Velocity X/Y/Z | Timer zero |
|---|---:|---:|---:|---:|---:|---:|---:|
| fly | 190 | 4 -> 3 | 45 | 5 | 0/0 | `561/-1024/859` | 280 |
| grub | 201 | 4 -> 3 | 45 | 5 | 0/0 | `-466/-1024/-913` | 291 |
| mite | 111 | 4 -> 3 | 45 | 5 | 0/0 | `-244/-1024/-996` | 201 |

Each timer consumes exactly 45 monotonic ticks over 90 movie frames. B07 is a
useful orthogonal control: its health pickup changes `3 -> 4` at frame 77 while
the stagger timer remains zero. D09 and D15 contain no true-health transition;
because their collision admission was not independently proven, they are not
misreported as immunity results.

## Static causal chain

`tools/phase4_d03_static.c` verifies the pristine executable hash, 57 decisive
instruction anchors, branch targets, and all direct JALs to `0x8004A700`.

The exact body-contact chain is:

`actor broad sphere -> pose-oriented ellipsoid -> state/flag gates ->
0x8004B4A0 -> 0x8004A700 -> normalized horizontal knockback -> suppression
gates -> state/vertical launch/health decrement -> signed timer`.

The broad sphere uses actor offsets `+0x64/+0x66/+0x68`, actor radius `+0x6A`,
player Y bias `-7360`, coordinate shift `5`, and radius expansion `250`. The
second test is pose-indexed through actor `+0x44/+0x74`. This closes why contact
reach can vary by family or animation while the damage law remains global.

The handler writes horizontal X/Z velocity before testing positive stagger.
Thus an overlapping enemy can continue to influence horizontal response during
the immunity window, while health loss and the fixed `-1024` vertical launch are
suppressed. A surviving accepted hit writes health `-1` and timer `+45`; the
timer is not refreshed by suppressed contacts.

## Reproduction commands

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  tools/phase4_d03_static.c -o /tmp/phase4_d03_static -lcrypto
/tmp/phase4_d03_static SCUS_942.88

cc -O2 -std=c11 -Wall -Wextra -Werror \
  tools/phase4_d03_capsule.c -o /tmp/phase4_d03_capsule -lzstd -lcrypto
/tmp/phase4_d03_capsule \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B07_health_partial_full \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/D08_fly_contact_kill \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/D09_cockroach_contact_kill \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/D11_grub_contact_kill \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/D11_mite_contact_kill \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/D15_daddy_long_legs_contact_kill
```

## Closure assessment

**Substantiated Partial, bounded-exhausted.** The named Phase 4 relationships are
resolved through independent static and frame-boundary evidence across three
positive enemy families. Exhaustively printing every authored pose-radius table
entry would add catalog breadth with minimal causal return. No Interpreter movie
is required unless a future family contradicts the shared law or a specific
pose’s numeric reach becomes the question.

Canon: [[SYS_enemy_contact_damage]].


## Closure addendum: native iframe admission control (2026-08-04)

### Named missing domain

The retained capsules contained first-hit contact damage and complete timer decay, but no second native admission to `player_contact_damage_8004A700` while `0 < 0x800A6592 < 45`. Offline frame-boundary reconstruction therefore could not close the invulnerability-window negative control by itself. Escalation `P4-D03-20260804-IFRAME` was declared before the live run.

### Reproduction identity

- Media: pristine `Disney-Pixar A Bug's Life (v1.0).cue`, SHA-256 `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`, serial `SCUS-94288`.
- State: `health_test.sav`, SHA-256 `b8df83d76fce8da42c4020909219be27aa3b8319542e63ff6baea05a3fa4e6c7`.
- DuckStation: revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; binary SHA-256 `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`.
- Isolation: fresh `/tmp/duckstation-phase4-d03-x5i9sN`, dedicated port `23703`, `CPU/ExecutionMode=Interpreter` present before game boot; settings SHA-256 `1c13c0627610098250746f5dfd222b7782c618a4eccaae58c7b1705312392d87`.
- Instrumentation was armed after state load. No movie, guest call injection, RAM write, code patch, fast-forward, or test-only actor reposition was used.
- Input recipe: advance 180 neutral frames, then hold D-pad Up for 210 frames into the beetle. Declarative reproduction: `tools/scenarios/duckstation/d03_contact_iframe.yaml` (SHA-256 `19e20c4f86719eb4d93f3d909589f842b67c44512f23e21f864f9d51879a2cdf`).

### Observation

- Frame `65268`, cycle `36954597861`: native resolver entered `0x8004A700` with health `4` and timer `0`; `0x8004A888` executed, health became `3`, and the timer became `45`.
- Frames `65308`, `65330`, and `65352`: the resolver admitted contact again with timer values `25`, `14`, and `3`. Each entry reached `0x8004A790`, but none reached `0x8004A888`; health stayed `3` and the timer was not refreshed.
- Frame `65358`: the timer decayed `1 -> 0` at `0x8004857C`.
- Frame `65372`, cycle `37013483108`: the next admitted contact entered with timer `0`, reached `0x8004A888`, changed health `3 -> 2`, and rearmed the timer to `45`.
- Later contacts at frames `65414`, `65434`, and `65452` were again admitted and suppressed at timer values `24`, `14`, and `5`.

### Inference

The invulnerability timer is not merely correlated with visual recovery. It is the handler-local admission gate: collision resolution can call the damage routine repeatedly, but a positive timer suppresses the health store, vertical launch, and timer reset. The timer continues toward zero rather than refreshing on suppressed contact.

### Causal confirmation

The live sequence matches the pristine ASM branch already reconstructed at `0x8004A790`: positive-timer entries take the suppression path, while zero-timer entries reach the health store at `0x8004A888`. The post-expiry re-hit is the native positive control that distinguishes timer causality from enemy separation or collision lockout.

### Machine evidence and guards

- Runtime semantic artifact: `analysis/phase4_d03_runtime_control.json`, SHA-256 `4a550728946f43b3a2a30f9b2156b23b43e2cb5fb4876e8dbb28e6773db806e6`.
- Regenerated static artifact: `analysis/phase4_d03_static.json`, SHA-256 `d6592e0a09105e047641333a418133db92a9c606afb04f2fd6b354dca42dbd25`; it now truthfully reports `56` anchors rather than the stale `57`.
- Capsule artifact: `analysis/phase4_d03_capsule.json`, SHA-256 `6f3ce6df0b43372202e2b792cf51514a364f5b093b8d213dfce4f04b6e99c9e8`.
- Transient raw access JSON: `/tmp/phase4_d03_access_complete.json.clean`, SHA-256 `a51411d461cdf120e3cdc813b90a5f51112a8f1b9a46afa9e4c3ef647e1aafc5`.
- Transient raw exec JSON: `/tmp/phase4_d03_exec_complete.json.clean`, SHA-256 `87c4098cf2a3813e21f01e98daa15605a48922f88d8b079c08e4efc1d603164a`.
- Normalized access TSV: SHA-256 `b09e2a2acb8b1db49b459bc46df11e2bb4f85795cf5ce56bd2b244dba118df7e`; normalized exec TSV: SHA-256 `0c251f58487278e68c479d14b23d59268d3e29bdf8e4368b74d3b08e134a0f51`.
- `tools/phase4_d03_runtime.c` rejects traces missing the initial damaging contact, an admitted positive-timer suppression, timer expiry, or the post-expiry damaging contact.
- `tools/phase4_d03_closure_guard.c` rejects drift in the pristine static anchors/callers, capsule integrity/semantic totals, or runtime control.

```sh
jq -r '.events[] | [.frame,.cycle,.address,.pc,.value,.new_value] | @tsv' /tmp/phase4_d03_access_complete.json.clean > /tmp/phase4_d03_access.tsv
jq -r '.events[] | [.frame,.cycle,.pc] | @tsv' /tmp/phase4_d03_exec_complete.json.clean > /tmp/phase4_d03_exec.tsv
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_d03_runtime.c -o /tmp/phase4_d03_runtime
/tmp/phase4_d03_runtime /tmp/phase4_d03_access.tsv /tmp/phase4_d03_exec.tsv
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_d03_static.c -lcrypto -o /tmp/phase4_d03_static
/tmp/phase4_d03_static SCUS_942.88
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_d03_closure_guard.c -o /tmp/phase4_d03_closure_guard
/tmp/phase4_d03_closure_guard analysis/phase4_d03_static.json analysis/phase4_d03_capsule.json analysis/phase4_d03_runtime_control.json
```

### Closure decision

D03 is now substantiated partial and bounded-exhausted for Phase 4. The shared damage law, all six direct caller sites, positive enemy-family controls, heal control, exact timer decay, native admitted-contact suppression, and post-expiry re-hit are covered. Remaining enemy-specific animation, sound, and content enumeration are implementation detail or low-return content breadth rather than unresolved D03 mechanics.
