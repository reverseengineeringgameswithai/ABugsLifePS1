---
kind: playbook
id: PLAYBOOK_phase4_extent_audit
name: Phase 4 - Extent Audit
status: accepted
implementation_state: swept_and_ratcheted
created: 2026-08-06
updated: 2026-08-06
confidence: high
parent: PLAYBOOK_game_solving_phase_4
depends_on:
  - PLAYBOOK_game_solving_phase_4
  - PLAYBOOK_phase4_typed_state_compiler
---

# Phase 4 - Extent Audit

**Navigation:** [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Phase 4 roadmap]] · [[Phase 4 - Typed State Compiler|Typed state compiler]] · [[Phase 4 - Frontier Extractor|Frontier extractor]]

## The bug this looks for

`tools/phase4_f01_frontier_resolve.c` carried a hand-typed `EXTENTS` table, and
**20 of its 29 ends were shorter than the functions they named**. 28,252 bytes /
7,063 instructions *inside the extents its census claimed to cover* were never
read, so every count it reported as a total was a lower bound — 1,960 accesses
when the real figure was 3,681, 106 unresolved stores when it was 231.

Nothing in that tool could detect it. The truncated range was self-consistent,
the scope was declared in prose, and the boundary was a constant nobody
re-derived. The pattern is cheap to write, so the question is whether it recurs.

```bash
tools/phase4_extent_audit.py [--json analysis/phase4_extent_audit.json] [PATH ...]
```

Exit 1 on any truncation not already reviewed. `tests/test_phase4_extent_audit.py`
— 9 tests, all green, including one that re-derives F01's qualifying extent SET
from the index and fails if any admitted function is not walked.

## The answer: it does not recur

**1,140 extent declarations checked across 910 tracked files. Not one truncated
census scan in any other tool.** (Tracked files only, so the result is a property
of the commit rather than of whatever is in the working tree — a fresh verifier
caught the retained artifact failing to regenerate from a committed checkout.)

What the sweep did find is a different, milder thing — **9 declarations across 5
functions where a `sha256` drift pin covers less than the whole function**:

| file | function | pinned | real | coverage |
|---|---|---:|---:|---:|
| `tools/phase4_lives_gameover.py:82` + `config/…yaml:15` | `gameplay_state_reset_cursor_seed` | 216 | 1360 | **16%** |
| `tools/phase4_camera_controls.py:86` | `results_screen_render` | 1028 | 3900 | **26%** |
| `tools/phase4_fmv_region_b_replacement_ownership.py:482,501` | `resource_id_dat_load_dispatcher` | 1004 | 1240 | 81% |
| `tools/phase4_downhill_slide.py:51` | `actor_skinned_update` | 2884 | 2964 | 97% |
| `phase4_abdomen_bounce.py:48`, `phase4_downhill_slide.py:52`, `phase4_kick.py:77` | `actor_player_contact_resolver` | 2744 | 2792 | 98% |

**This is not the F01 bug and should not be described as one.** A truncated
*census* makes a number wrong. A truncated *pin* still detects drift inside what
it covers — it just cannot see the tail. No count anywhere is affected.

Worth acting on anyway at the top of the table: a pin covering 16% of
`gameplay_state_reset_cursor_seed` (C16) or 26% of `results_screen_render` (A17)
would not notice a mod to the rest of the function. Re-pinning changes retained
hashes, so it is the owning row's call, not this sweep's.

⚠️ `actor_player_contact_resolver` is truncated **identically to `0x8004B6AC` in
three separate tools**, and F01's table had its own wrong end (`0x8004B5F4`) for
the same function. When a boundary is hand-typed it gets hand-typed wrong more
than once. Generate it.

## Why the detector needed four filters

The naive join — "an address pair whose first element is a function entry" —
produced **343 findings, every inspected one noise**. Functions are ~1 KB, so any
nearby constant lands inside one. Each filter below removed a class that was
inspected and confirmed spurious:

| filter | what it removes |
|---|---|
| **name or structure** | the line must name the function, or the pair must be structurally a range (`(0xA, 0xB)`, `start:/end:`). Kills stray constants. |
| **glued token** | `player_vertical_update@0x80048138_0x80048518` is an access-site **id**, not a range. It carries the name too, so the name test alone cannot see it. |
| **comments stripped** | fixing F01's table left the old end in a trailing `/* was 0x8004b5f4 */`, and the audit reported the repair as the bug. |
| **line already states the correct end** | `{name: …, start: 0xA, end: 0xB, writer_pc: 0xC}` — a line does not declare both the true extent and a truncated one. |
| **code records only** | `master_game_state` spans `0x800823A0..0x800823CC` as **data**; a two-byte watched window there is not a truncated function. |

343 → 13. Each filter is documented in the tool with the specimen that motivated
it, because a filter without its counterexample is just a number someone chose.

## The ratchet

`config/phase4_extent_audit_acknowledged.yaml` records the 13 reviewed rows with
a verdict and a reason — 9 `drift_pin_covers_less_than_the_function`, 4
`not_an_extent` (`name 0xENTRY @0xSITE -> callee` notation, where the second
address is a call site). The audit fails on anything **not** in that file, so a
newly typed truncation is caught while reviewed ones stay quiet.

Keyed by `(file, line, declared end)`: move the line and it is re-raised. A stale
allowlist that silences real findings is the failure mode this repo keeps hitting,
so the key is deliberately brittle.

**The suite includes a positive control** — a synthetic file with one truncated
range and one correct range, asserting the tool flags the first and not the
second. Without it the tests prove only that the tool is silent, which is also
what a broken detector looks like.

## ⚠️ What this audit cannot see

A fresh verifier reviewing F01 on 2026-08-06 found a truncation this tool is
structurally blind to. It checks whether a declared **end** stops short of the
function. F01's remaining defect was a short **set**: `EXTENTS[]` listed 29 of the
37 functions its own stated criterion admits, so eight functions were never walked
at all — including `scene_flow_dispatcher`, where that row's entire lifecycle
argument lives. Every end in the table was exact.

**A census can be truncated in two ways and this tool sees one of them.** When a
tool declares an inclusion criterion in prose, check the set it actually walks
against that criterion, not just the ends of the rows it happens to list. Both are
now generated from the index for F01.

## Standing rule

⚡⚡ **Generate function boundaries from
`analysis/phase4_static_frontier_index.json`; never hand-type them.** If a tool
declares a scope in prose, check the scope it actually walks — see
[[Phase 4 - Typed State Compiler]] for how F01's figures moved when its walk was
corrected.
