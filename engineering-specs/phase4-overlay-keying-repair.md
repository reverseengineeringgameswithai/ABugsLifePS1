# Repair: overlay-space addresses are now keyed by `(image, address)`

**Date:** 2026-08-11 · **Status:** repair, offline, measured and applied. Promotes no row and
moves no DoD verdict — verified: **0 of 126 dimension cells moved**.

Follows `phase4-overlay-va-collision-finding.md`, which called for this and ordered it
before registering overlay build units. That finding's central claim holds; two of its
numbers are corrected below.

---

## What was actually broken — three layers, not one

Every per-level overlay is CdRead-loaded at the same VA (`region_a: 0x800B39A0`;
`MEMORY.BIN` at `region_b: 0x800B5788`), so an overlay VA does not identify code. Three
independent layers dropped the image identity, each in a different way.

### 1. The resolver threw away identity the census already had

`analysis/functions.json` **does** carry image identity, in the `overlay` key: 192 overlay
functions across all 20 images, with **16 VA starts claimed by more than one image**. The
data was right.

`tools/phase3_ownership_graph.py:find_function()` is a **binary search over a merged,
sorted list of all overlay functions**. Overlay intervals fully overlap, and binary search
over overlapping intervals is undefined — it returns whichever entry midpoint arithmetic
lands on, and it can return nothing while candidates exist. Measured against the live
graph, over the 135 overlay-window addresses with at least one containing overlay function:

| outcome | count |
|---|---:|
| resolved to **one arbitrary image** out of several (up to **19** candidates) | 114 |
| returned **`None`** despite candidates existing | 3 |
| **arbitrary or absent** | **117 / 135 = 86.7 %** |

`0x800B39A4 level_overlay_init` was published as `LEVEL02_LEVEL` out of 19 equally valid
candidates — every level has an init at the overlay entry point.

### 2. The state lane had no image field at all

The graph's records split into two lanes, and only one was keyed:

| lane | occurrences in overlay window | shape | keyed? |
|---|---:|---|---|
| `functions[]` | 133 | `{address, function_start, space, name, classification, canon}` | tag present (but arbitrary — layer 1) |
| `state[]` | **62** | `{address, semantic_ids, canon}` | ❌ no image field exists |

⚠️ **Correction to the earlier finding.** It reported *"255 records naming overlay-space
addresses, and their schema is `{address, semantic_ids, canon}` — no image field."* That
conflated the two lanes and used a window (`>= 0x800B0000`) wider than overlay space. The
accurate figures: **229 keyed occurrences over 161 distinct addresses at or above
`0x800B0000`**, of which **138 are inside the overlay window** and **23 are ordinary
resident RAM** (9 below `region_a`, 14 above MEMORY's end) that the address alone keys
correctly. The no-image-field claim is true of the **62** `state[]` occurrences.

### 3. The registry FORBADE recording the second overlay's field

`tools/semantic_state.py` enforced uniqueness on `(namespace, address)`. So the registry
could hold at most **one** overlay's view of any VA — a second overlay's genuinely
different field at the same address was not merely unkeyed, it was **unrecordable**.
Proven, not assumed:

```
gate REJECTS the second overlay's field:
  original.tree_progress_counter: duplicates original.training_step at 0x800b4a3c
```

This is the concrete cost. `0x800B4A3C` is `training_step` (range 0..13) in
`LEVEL07/LEVEL1.BIN` **and** a separately measured field (0..320 over 1,896 writes) in
`LEVEL02/LEVEL1.BIN`. Only the first was expressible; the second had to live in prose
inside the first entry's `context` string.

## The measurement

`tools/phase4_overlay_keying_repair.py` → `analysis/phase4_overlay_keying_repair.json`,
with all image reads and instruction decoding in compiled C
(`tools/phase4_overlay_address_resolver.c`, `--selftest` PASS).

| | |
|---|---:|
| distinct addresses examined | 161 |
| keyed occurrences | 229 |
| **inside the overlay window** | **138** |
| — owner forced (only one pinned image spans it) | 19 |
| — genuinely ambiguous | 119 |
| — worst case, one address | **19 images** |
| inside the window but unowned by any image | **0** |
| resident RAM, correctly keyed by address alone | 23 |

The 19 "forced" answers are forced only under a closed-world assumption over the 21 pinned
images, and the artifact says so. One is an independent corroboration: `0x800B5774` →
`LEVEL07_LEVEL`, which is F10's Clover Forest objective mask — F10 derived `LEVEL07` by
hand through the progression table, and the resolver forces the same answer from bytes.

## The repair

**`tools/semantic_state.py`** — key is now `(namespace, image, address)`. `image` is
required for `kind: overlay_field`, forbidden on resident state (a resident VA *is*
unique, so tagging one would invent ambiguity), and must name a real blob. The known-image
set is **derived** from `config/overlays.yml` ∪ `analysis/functions.json`'s own `overlay`
tags (20 images), never hardcoded.

**`tools/phase3_ownership_graph.py`** — `find_functions()` enumerates every containing
candidate. `find_function()` is kept for the resident space, where ranges are disjoint, and
now carries a docstring stating why it must never be called on the overlay list. Overlay
function records gain `overlay_candidates` and `overlay_ambiguous`; `name`,
`function_start` and `classification` are emitted **only when the candidates agree**.
Overlay-window `state[]` records gain `overlay_local` / `image_required`.

**`config/semantic_state.yaml`** — `original.training_step` gains `image: LEVEL07_LEVEL1`.
This one is not merely containment-consistent, it is **machine-proved by a writer-set
constraint**. Re-running `tools/phase4_f00_state_owner_probe.c` with the corrected writers
(derived from the registry, never re-typed) decodes both of them as real stores in
**exactly one of the 20 images**, and both compute the target address:

```
0x800B3DA0 : 0xAC204A3C  sw zero  ->  0x800B4A3C   in OVL/LEVEL07_LEVEL1.BIN   (1 of 20)
0x800B47E0 : 0xAC234A3C  sw v1    ->  0x800B4A3C   in OVL/LEVEL07_LEVEL1.BIN   (1 of 20)
```

Containment agrees and is the weaker check: `LEVEL07/LEVEL1.BIN` spans
`0x800B39A0..0x800B4A90`, while both LEVEL01 images end before the address
(`0x800B4030`, `0x800B442C`). This is the pattern for resolving the remaining ambiguous
addresses — a constraint that only one image can satisfy, decided from bytes.

**`tests/test_semantic_state.py`** — 7 regression tests, including the one that matters:
*a second overlay's field at a shared VA is now recordable*. Also: same VA + same image is
still a duplicate; unknown image rejected; missing image on `overlay_field` rejected;
`image` on a resident field rejected; the image set is derived; and a declared image must
physically span its declared address.

### Effect on the regenerated graph

| | before | after |
|---|---:|---:|
| function entries published with a **false definitive** owner | 116 | **0** |
| entries carrying `overlay_candidates` | — | 116 |
| resident entries (must not move) | 700 | 700 unchanged |
| `functions_cited` | 816 | **852** |
| `state_cited` | 587 | **551** |
| honest gaps | 328 | 445 (+150 `overlay address`) |

The ±36 is a self-check: those are addresses the broken binary search was **missing**
entirely and dumping into the state lane. `+36 / −36` balances exactly.

## What this cost, and what it did not

- ✅ 11 artifacts pinned the old graph sha; 10 have generators and were re-run.
- ✅ **0 of 126 DoD dimension cells moved.** The row assessments were not leaning on the
  false attributions, so correcting them changes no row's measured state.
- ✅ Test suite: **baseline 8 failed / 34 passed → 7 failed / 45 passed.** Zero new
  failures; +7 new tests; and one pre-existing failure *fixed*
  (`test_graph_is_fresh_regeneration`, which was already red before this work began
  because the committed graph predated today's F01 promotion).
- ✅ `phase4_f00_written_bar_assessment` was fail-louding on a probe artifact left stale by
  this session's earlier `training_step` writer correction — **not** caused by this work
  (it reproduces against HEAD). Repaired here by regenerating
  `analysis/phase4_f00_state_owner_probe.json` with the corrected writers derived from the
  registry rather than re-typed: now **325 facts derived / 0 hand-typed, 58 artifacts
  pinned**, exit 0.
- ⚠️ `phase3_evidence_inventory` still exits nonzero — that is its design when it holds
  OPEN items (live-artifact environment mismatches, a dirty working tree). Pre-existing,
  unrelated, and it writes its artifact regardless.
- ⛔ `analysis/phase4_control_plane_data_quality.json` still records the **old** graph sha
  and was deliberately **left alone**. It is a historical session record
  (`source_commit: 508e2cb00a3f3`, dated 2026-08-10) whose `retained_outputs` snapshots
  what existed at that commit. Rewriting those shas to match today's files would falsify
  the record. It is not a live pin, and no test asserts its freshness.

## Follow-on: resolving the enumerated ambiguity (same day)

`tools/phase4_overlay_row_image_resolver.py` →
`analysis/phase4_overlay_row_image_resolution.json`.

The graph is **per-row**, and a row's own stage decides which overlay is resident while
its mechanic runs. Stage → scene comes from the game's progression table at `0x80077FA0`,
**read out of `SCUS_942.88`**; scene → blob follows the disc law (`dir = scene if
scene<=10 else scene-10`; `LEVEL.BIN` if `scene<=10` else `LEVEL1.BIN`). Neither input is
the artifact being resolved, so this is a check, not a restatement.

**Gated on six resolutions established without it** — a compiled-C byte probe (F09), a
100.0 % code-window match (F11), a disc-side pin (F02), a writer-set constraint (F00), and
D18's and F10's own pins. All six reproduce; the tool refuses to emit if any stops.

| outcome | citations | |
|---|---:|---|
| **RESOLVED** to one image | **108** | all 108 physically contained; 105 also have censused code there |
| **NARROWED** to a bounded set | **24** | D17 → 2 images, D20 → 3, from as many as 19 |
| **FALSIFIED** | **0** | |
| unresolved — genuinely cross-stage | 18 | rows scoped `all` / `frontend` / `multiple` / `+ others` |

**132 of 150 (88 %) bounded to ≤3 images.** The last 18 are rows whose mechanic really
does span every overlay (enemy token, respawn anchor, event VM, HUD, streaming) — for
those, "not owned by one image" is the correct answer, not a gap.

⚠️ **No artifact cycle.** The resolver reads the graph; the graph never reads the
resolver. Consumers join on `(row, address)`. Folding the answers back into the generator
would make the two pin each other.

### Two traps, both from substring tests — and one that mattered

- Rejecting prose containing `" and "` as multi-scope threw away F10's legitimate
  single-scene note (*"= 7, and the Phase-3 scene graph labels…"*), silently dropping 16
  citations. **The known-positive gate caught it**, which is what gates are for.
- Reading the `"all"` in D17's *"confirmed for **all** 3 Birdnest fixtures"* as scope —
  it counts fixtures — refused to narrow a perfectly enumerable two-scene row.
- ⚠️ The one that mattered: an early version checked the derived image against the graph's
  `overlay_candidates` and flagged **10 "falsifications"**. But `overlay_candidates` is
  built from the *function census* (192 functions over 20 images), so its absence means
  "no censused code there", **not** "wrong image". All 10 were physically contained —
  including F00's `0x800B4A3C → LEVEL07_LEVEL1`, which had been **byte-proved that same
  hour**. Census coverage is corroboration, never refutation. The hard check is physical
  containment; both the artifact fields and the regression tests now keep the two bases
  apart.

`tests/test_overlay_row_image_resolution.py` — 17 tests pinning the chain, the gate, both
parse traps, and the containment invariants.

## Scope

- ✅ Measured and applied: everything in the tables above, regenerated and committed.
- ✅ 132 of the 150 ambiguous citations are now bounded; 108 to a single image.
- ❌ **NOT claimed:** that the 18 open-ended rows have a hidden single answer. Their
  mechanics span overlays by design.
- ❌ **NOT claimed:** that a resolved image is where the code was *authored* — only that
  it is the blob resident for that row's stage, which physically contains the address.
- ❌ **NOT claimed:** that any row's behavioural conclusion was wrong. What was
  misattributed is which file the code lives in, never what it does.
- ❌ **NOT claimed:** that `functions.json`'s per-image census is complete. It holds 192
  overlay functions; whether that is every overlay function is a separate question this
  repair does not touch.
- ▶️ **Now unblocked:** registering overlay build units. The earlier finding said to repair
  the keying first so the misattribution would not be baked into the build system. It is
  repaired.

## Methodology note — three wrong-key blind spots in one session

Each produced a confident **zero** that looked like a finding:

| I read | the data actually used | wrong answer I nearly banked |
|---|---|---|
| `isinstance(address, str)` | `semantic_state.yaml` stores addresses as **int** | "0 semantic entries have overlay addresses" |
| `f.get("space")` | image identity lives in `f.get("overlay")` | "overlay ranges are disjoint, `find_function` is fine" — a **falsification of the real defect** |
| `verdict` | assessments record `state` | "0 of 10 DoD cells moved" (real count: 126 cells) |

The second is the dangerous one: it briefly *disproved* a defect that is real and 86.7%
prevalent. The habit that caught all three was the same one this campaign keeps re-learning
— **check a known-positive before believing a negative** — and the driver now emits an
`address_key_type_census` and hard-fails if either source yields zero, so the next
unhandled representation is visible in the output instead of vanishing into a plausible
number.
