---
kind: playbook
id: PLAYBOOK_phase4_frontier_extractor
name: Phase 4 - Frontier Extractor
status: accepted
implementation_state: item_1_closed
created: 2026-08-05
updated: 2026-08-06
confidence: high
parent: PLAYBOOK_game_solving_phase_4
depends_on:
  - PLAYBOOK_game_solving_phase_4
  - PLAYBOOK_phase4_frontier_closure_workbench
---

# Phase 4 - Frontier Extractor

**Navigation:** [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Phase 4 roadmap]] · [[Phase 4 - Frontier Closure Workbench|Closure workbench]] · [[Phase 4 - Typed State Compiler|Typed state compiler]] · [[Phase 4 - Acceleration Tooling Strategy|Acceleration strategy]]

## What this is

[[Phase 4 - Frontier Closure Workbench]] shipped `tools/phase4_semantic_frontier.py`,
a **checker**: it validates a fully declared Item-2 query and solves the affine
access intersections with Z3. What it never had was a way to *get* a query.
Authoring one by hand is what kept every row away from it, even though the
mechanical bulk — images, functions, call edges, access candidates — already sat
in `analysis/phase4_static_frontier_index.json` (1,190 analysed records, 21
hash-verified images).

`tools/phase4_frontier_extractor.py` is that feeder. It does the mechanical half
and **refuses the judgement half**.

```bash
tools/phase4_frontier_extractor.py SEED.yaml \
    --output config/QUERY.yaml \
    --summary analysis/EXTRACTION.json \
    --blockers analysis/BLOCKERS.json [--check]

tools/phase4_semantic_frontier.py config/QUERY.yaml \
    --output analysis/RESULT.json [--check]
```

| extracted mechanically | required from the seed, never guessed |
|---|---|
| universe images, hash-bound | target, roots, windows |
| transitive callee closure | category dispositions + evidence |
| **callers**, by inverting the whole call graph | boundary owners |
| per-function direct / indirect call edges | residuals (strict form) |
| access candidates, index ∪ binary scan | completeness of any callback or indirect table |

Tooling-plan increment 1 is **closed** as of 2026-08-05, after seven
adversarial review rounds with Codex as independent reviewer.

## The one lesson worth carrying forward

Every round found the same error at a new level: **a property was proved over the
thing being looked at, then reported as a property of the system.**

| round | verified over | the real universe was |
|---|---|---|
| 1 | functions reachable from the chosen roots | every function |
| 2 | every function in the index | every access in the index |
| 3 | every access in the index | every access in the **binaries** |
| 4–5 | a self-hash the tool computed | a regeneration it could not fake |
| 6 | a tool the *document* named | a tool the **checker** names |
| 7 | provenance the *caller* supplied | provenance the compiler **derives** |

> ⚡⚡ **The question that catches it every time: *who chose the thing I am
> verifying against?* If the answer is "the artifact under review", it is not a
> check.**

## Hard-won specifics

**Identity is `(image, entry)`, never an address.** Sixteen entry addresses are
shared across overlays — every level overlay entry sits at `0x800B39A4` — so an
address-keyed map silently discards **42 of 1,190** records and can attribute an
edge to the wrong image. Function ids are emitted image-qualified.

**The static index only records CFG-reachable accesses.** It recovered 8 of
`scene_flow_dispatcher`'s 393 instructions, which hid nine already-known F01
accesses — including the transition-timer decrementer `0x800553F8`, observed
firing 68 times at runtime, and the scene-entry writers `0x8004FE44`/`0x8004FE4C`
that [[MEM_800823A0_scene_transition_request]] documents. The extractor therefore
emits the **union** of index accesses and an independent linear binary scan.
"Whole-universe over the index" is not "whole-universe over the binaries".

> ⚠️ **The binary supplement now finds ZERO accesses the index missed, and that is
> a result rather than a regression.** Once the index's CFG recovery became the
> whole-image direct-edge fixed point (below) it reached all nine of the accesses
> the linear scan used to be the sole source of, so two independent methods --
> constant propagation over a recovered CFG, and an adjacent-`lui` scan of every
> word in every image -- now agree on all **124** with no residue either way. The
> supplement is still run and still independently proves the nine directly from
> the bytes; the test that used to assert `supplement > 0` was replaced, not
> relaxed, and now fails if the number moves off zero in either direction.

**The binary scan requires `lui_pc == access_pc - 4`.** Clobber tracking was
attempted and defeated by `jalr`, `mfc0` and `lwl`; adjacency needs no GPR-write
model and costs no retained coverage — all **124** binary-scan positives satisfy
it, with 115 also present in the static index and 9 supplement-only. Two traps it
exposed: the register kill must happen *after* the access is evaluated, because
the standard `lui v0,X / lh v0,ofs(v0)` idiom has `rs == rt`; and a blanket
`hi.clear()` on every SPECIAL treats `nop` as a barrier, silently halving
detection.

**Callers must be roots, not merely declared.** The checker only credits
`consumer_categories` for functions its walk reaches, so a declared-but-unreached
caller contributes nothing. Note that "reached == declared" is then an
*accounting identity*, not an independently established reachability result —
`root_provenance` says so explicitly.

**Control flow is accounted for, not solved.** Direct jumps out, indirect jumps,
incoming jumps and unanalysed extents are ledger categories. Jump targets resolve
by *containing extent*, not by entry — resolving by entry reported zero incoming
jumps while the five `scene_flow_set_substate_*` jumps into
`scene_flow_dispatcher` demonstrably exist. General jump-table/CFG recovery is
deliberately **out of scope**.

## The gate

`mechanical_completeness` is a hard checker input, not advisory prose:

- a hash-bound **blocker ledger** with stable, unique ids retains every blocker;
  the summary keeps only a sample;
- `TRUSTED_EXTRACTORS` is **checker-owned** — a query naming its own attester was
  exploitable with a hash-correct no-op that exits zero;
- provenance is proved by **regeneration**: the checker re-runs the trusted
  extractor against the attested seed with `--check` and requires the document
  under review to *be* the attested query file;
- `compile_frontier(document)` takes **no** provenance parameter, so a caller
  cannot substitute a claim for a rebuild.

A synthetic or hand-built query therefore cannot reach a ready verdict at all —
which is correct, and is what the checker's own fixtures now assert.

## Current state on F01

F01 is the **acceptance fixture**, not a progress meter — see
[[EXP_2026-08-05_phase4_f01_objective_lifecycle]]. It earned that role by
exposing a real defect in every single round.

| | |
|---|---|
| functions | 763 (530 callee closure + 233 caller surface) |
| accesses into the two windows | **124** = 124 index + 0 binary supplement, 0 unemitted |
| solver | 124 intersects, 0 unknown, 0 disjoint |
| callback groups | 32, every one `complete: false` |
| indirect call tables | 95, every one `complete: false` |
| residual coverage | 127 unknowns, generated, each covered exactly once |
| images census-complete | 19 of 21, derived |
| mechanical blockers | 20,130 over nine categories, unique ids |
| provenance | verified by regeneration |
| verdict | `item2_ready_for_review: false`, **two** named blockers |

That verdict is the correct one. F01's row remains `partial`, 1 of 9 — see its
scorecard in `analysis/mechanics_baseline.yaml`.

## The four blockers that were wiring, and the two that are not (2026-08-06)

F01's checker result carried six review blockers. Four of them were **defects in
the query's own declarations** and decided nothing about the game:

| blocker | what was actually wrong |
|---|---|
| `UNUSED_BOUNDARY_OWNER` | both `boundary_owners` entries were keyed by CATEGORY NAMES (`unresolved_register_based_accesses`). A boundary owner is keyed by an **edge identity** (`source@0xSITE->target`), so no emitted edge could ever match one. They were unusable by construction and could only ever be reported unused. |
| `RESIDUAL_COVERAGE_INVALID` | each residual's `covered_ids` listed **its own id**, which is not a boundary the checker emits, so both were rejected as covering a non-unknown. |
| `UNBOUNDED_UNKNOWN` | consequently the 58 real unknowns — every indirect call site in the closure — were covered by nothing. |
| `ITEM2_CATEGORY_MISSING` | `callbacks` was `required` with zero records, because the static index has no callback field and nobody had built one. |

The repairs are structural, not one-off:

- **A boundary owner must name an edge the extractor emits**, or extraction fails
  closed. The class cannot recur.
- **Residual coverage is generated from a `covers` RULE**, and the union is
  reconciled against the exact set of unknowns the query emits. A rule that goes
  short fails closed; a hand-typed list of generated identities cannot even be
  offered.
- **`callbacks` is derived** — see below.

The remaining two are real:

- **`MECHANICALLY_INCOMPLETE`** is Item 2 itself. The ledger holds **20,130**
  rows, of which **19,843 are unresolved accesses** (98.6%). Indirect control flow
  is 53 of them. Clearing this blocker means resolving effectively every access in
  the closure, which is the open problem, not a wiring defect.
- **`IMAGE_CENSUS_INCOMPLETE`** now names exactly two images instead of twenty-one
  by default — see below.

## Derived surfaces: `tools/phase4_frontier_static_census.py`

Two of the checker's demands could not be answered from the static index at all,
and the query answered both by **declaration**. Both are now derived by
`tools/phase4_callback_probe.c`, recompiled with `-Werror` and re-run, and the
seed pins the receipt by sha256 so it cannot drift underneath a query that still
validates.

```bash
tools/phase4_frontier_static_census.py \
    --output analysis/phase4_frontier_static_census.json [--check]
```

**The two sections are different universes and the receipt says so.**

`function_pointer_census` — POSITIVE-ONLY. Every code address materialised by an
adjacent `lui`/`addiu` or `lui`/`ori` pair, classified by how it leaves the site:
stored to a slot, passed in an argument register at a `jal`, or called through
`jalr`. **49 sites, 32 registration groups, 46 distinct target functions, and all
49 land exactly on a function entry** — which is the check that it is finding
function pointers rather than constants; noise lands at random offsets. Every
group is emitted `complete: false`, because a pointer built across a basic block,
loaded out of data, or copied through a third register is invisible to it.

`image_census` — a CENSUS over its universe. Every byte of every image is either
claimed by an indexed extent or falls in an enumerated gap, and **every load and
store decoded inside those gaps is reported with its base provenance, including
the ones whose base could not be proved**. That is the fail-closed direction: a
positive-only sweep finding nothing reads exactly like a swept-and-clean image.

> ⚠️ `census_complete` means: the byte partition is complete, every gap memory
> reference has a proved base, and none reaches a window. It does **not** mean the
> accesses *inside* the extents are resolved — that is mechanical completeness —
> and it asserts **no semantic ownership** of any byte.

19 of 21 images pass. The two that do not are `SCUS_942_88` and `MEMORY`, with
**503 instruction-shaped gap words whose base is unproved** between them.

> ⚠️ **Those 505 are words whose ENCODING is a load or store, inside bytes no
> extent claims. They are not confirmed memory references.** Nothing shows any of
> them executes, and **no direct branch, jump or call edge from reachable code
> enters any gap in any image**. Counting them as undecided references states the
> deficit in the wrong category; the prior question is who owns the region.

`gap_ownership` answers that **per byte**, with five declared classes, each
carrying its source and none inferred from another. Four are nonzero in this
fixture:

| class | basis | bytes |
|---|---|---:|
| `zero_filled` | aligned whole-zero WORDS. ⚠️ Says only that those words carry no load/store encoding — a zero word is `sll zero,zero,0` — **not** that they are data. | 9,360 |
| `decoded_jump_table` | overlaps a table decoded by `tools/phase3_jr_tables.py` | 1,248 |
| `read_as_data` | `[address, address+width)` of resolved accesses from analysed code | 1,162 |
| `content_verified_trigonometric_table` | complete mathematical byte comparison **and** instruction-derived reader ranges, reconciled exactly in both directions; either leg alone is insufficient | **12,284** |

⚠️ **The classes overlap, so those totals are not exclusive buckets and must not
be summed.** The union is what counts:

| disposition | gaps | bytes |
|---|---:|---:|
| `none` | 4 | 260 |
| `partial` | 9 | **22,140** |
| `complete` | 72 | 12,792 |

| | bytes |
|---|---:|
| gap bytes, 85 gaps | **35,192** |
| with any evidence (union) | 23,234 |
| with **semantic** evidence (excludes zero-fill) | **14,694** |
| with **no evidence at all** | **11,958** |

⚠️ Every gap carries an explicit `none` / `partial` / `complete` disposition,
because byte-exact intervals alone still let a reader take "has evidence" for
"owned". **`partial` dominates the corpus** and is the answer this census refuses
to round up.

> ⚠️⚠️ **Ownership is recorded per BYTE, never per gap, and an earlier version of
> this section got that wrong.** A whole-gap boolean marked the 13,536-byte `$gp`
> region "has positive ownership evidence" on the strength of a few hundred covered
> bytes, and this playbook then reported the deficit as *8 gaps / 13,016 bytes*.
> Byte-exactly it was **24,258 bytes** at that historical correction, then
> **24,242** immediately before the F01 trig disposition below.
> `read_as_data` proves things about the words an access touches; it never owns a
> region.

The 2026-08-06 F01 hard-truth probe moved exactly **12,284 of those 24,242
unevidenced bytes** into `content_verified_trigonometric_table`: 4,216 bytes at
`0x80075930..0x800769A8` and 8,068 bytes at
`0x8007B63C..0x8007D5C0`. This class requires two independent legs: all entries
of the containing table match a derived fixed-point trigonometric model, and the
named reader functions' instruction-derived address ranges land in the exact gap.
It does not widen an extent. The largest remaining single unevidenced run is now
**1,840 bytes at `0x8007E8B8..0x8007EFE8`**. `SCUS_942_88` and `MEMORY` remain
incomplete, so `IMAGE_CENSUS_INCOMPLETE` stays.

The content change also changes evidence identity. A 2026-08-07 detached
Hard-Truth pass caught a stale live dependency: the F01 seed still pinned the
pre-trig census and the generated query still attested the pre-trig static
index, so the extractor correctly refused regeneration. The required ordering
is now explicit: regenerate static index → regenerate census → intentionally
re-pin the seed's census hash → regenerate query/summary/blockers → regenerate
the semantic result. Current pins are census `83f581ad…` and index `a615a5d7…`.
The blocker ledger is byte-identical (`b5d5cdc6…`) and all semantic counts are
unchanged; this is provenance propagation, not an invented frontier delta. The
capsule receipt's old census hash remains immutable historical provenance and
is not a live extractor pin.

The same ratchet applies to the evidence surfaces themselves. For every new
`phase4_*.py` generator, `phase4_*.json` artifact, or `test_phase4_*.py` test,
recompute the complete direct-child discovery universe used by
`tools/phase4_inventory.py` and compare path sets in both directions against the
named prerequisite. Matching failure counts or matching failing test IDs is not
identity. A historical comparison input must have an actual byte-reproducing
mode; F01's 79-row local-base baseline is rebuilt from the exact `1bba2487` Git
object by `phase4_f01_local_base_recovery.py --baseline-output ...`, rather than
being declared as an output with no producer. Nonzero inherited inventory gaps
remain named residuals and are never read as closure.

Two results survive that correction and are worth keeping:

- `SCUS_942_88:0x8007E8B8` — 13,536 bytes ending exactly at `$gp` — has **730
  bytes** proved data by resolved accesses from code. The `$gp` alignment was a
  hypothesis; the reads are evidence. 5,325 bytes of it still have none in many
  runs, the largest being the 1,840-byte prefix named above.
- `SCUS_942_88:0x8008219C` — the 340 bytes reviewed and **declined** as a code
  extension — has bytes read as data by code, corroborating that decision
  independently. It is also the one region where the census and gate partitions
  differ.

## No direct edge enters any gap — over the COMPLETE edge-kind set

A first version of this check counted only edges that carry an ADDRESS (branch,
jump, call target, known `jr` target) and reported zero. That was not a
direct-edge result: two boundary edges have no target field and were invisible —
ordinary **fallthrough** past the end of an extent, and the **pc+8 return
continuation** of a call or indirect call. Both are enumerated now, by kind.

⚠️ Adding fallthrough naively reported **67** edges into gaps. Every one was a
**delay slot**: the word after a jump runs before control transfers, and where
control goes next is decided by the transfer — after `j`/`jr` it does not continue
linearly at all, and after `jal`/`jalr` it resumes at the call's pc+8, which
`call_return` already records. With delay slots excluded the figure is **0** across
all seven edge kinds, and that zero is now authoritative in a way the earlier one
was not.

⚠️ It still does not prove a gap is not code: an **undecoded indirect jump** could
land there. `0x8004C898` is the living proof — 0 boundary edges, and it is
executable.

⚠️ A first extraction of the gate's targets read only `entries` and not `targets`,
reporting **38** distinct targets instead of **450**, which would have silently
under-owned every gap. The gate stores jump islands under `entries` and every
other kind under `targets`.

**No gap reference in any image reaches either window.** A hit there would be a
named falsifier for the direct static writer census; the sweep is a falsifier
that did not fire, and the test suite includes a synthetic image where it does.

### Two probe defects worth remembering

- ⚠️ **The delay slot is where the registration happens.** This game registers
  actor handlers as `j 0x8004a620 / sw v0, 116(s1)` — the store runs *before* the
  jump transfers. Applying the jump's clobber at the jump and then decoding the
  delay slot lost eight registrations at `0x8004A570..0x8004A618` alone. This is
  the same hazard [[Phase 4 - Typed State Compiler]] hit from the other side, where
  a `jal`'s argument is set in its delay slot.
- ⚠️ **Overlay address aliasing is not fixed by preferring code extents.** Twenty
  overlays load at one address, and `LEVEL02_LEVEL1`/`LEVEL07_LEVEL` type their
  first words `data` where others type them `code` — so a pointer built inside
  `LEVEL02_LEVEL1` was reported as a `LEVEL01_LEVEL` function, an image that is not
  even resident at the same time. Containment in the materialising image's
  **address range** decides ownership; an address that image does not type as code
  is reported as *no function*, never as a foreign image's.

## Exact-set reconciliation against the static-ASM gate

[[Phase 4 - Static ASM Prerequisite Gate]] publishes 235 typed indirect candidate
sites. The extractor reconciles against it **as a set, in both directions**, and
fails closed on any resident indirect site the gate's universe does not contain.
Equal aggregate counts are explicitly not accepted — count-matching is how a wrong
37-extent set once passed this project's review.

| | |
|---|---|
| resident indirect CALL sites in the query | 94, **all 94** in the gate's 139 `jalr` sites, 0 query-only |
| resident indirect JUMP sites in the ledger | 51, **all 51** in the gate's 96 `jr` sites, 0 ledger-only |
| gate sites outside this frontier | 45 `jalr` + 45 `jr` |
| out-of-gate-scope sites, named not dropped | 3 (the gate is resident-only) |

**What the gate actually decides for F01, measured rather than assumed:** it bounds
the target set of **every** resident indirect jump this frontier retains (51 of 51)
and of **none** of its indirect calls (0 of 94) — all 87 of its resolved target sets
are `jr` switch islands. A bounded target set is still retained as a blocker:
knowing where a jump can go is not disposing of what it reaches.

## The index walks the whole image now (2026-08-06)

The index used to recover each function's CFG **from that function's own entry**,
which is not the same universe as the program's direct control flow. The specimen
is `scene_flow_dispatcher`: its eighth instruction is `j 0x8004fb3c`, which leaves
its own extent, so an isolated walk stopped there and recorded **8 of 393**
instructions with `analysis_status: ok`. The other 385 are entered from OUTSIDE —
five `j 0x8004fcc0` sites plus two branches — and no per-extent walk can see them.

`image_direct_cfg()` is [[Phase 4 - Static ASM Prerequisite Gate|the gate's]]
algorithm applied to the index's **full declared universe**, not to F01's subset:
seeds are the typed code/thunk extent entries, edges are direct branch, jump and
call targets, the fall-through after a call, and any verified `jr`-table target.
Nothing is seeded from an unreachable source.

| | before | after |
|---|---:|---:|
| reachable instructions | 115,535 | **117,552** |
| CFG coverage, all 21 images | 94.1% | **95.7%** |
| records with unreachable code | 29 | **16** |
| unreachable instructions | 7,280 | **5,263** |
| memory accesses recorded | 32,622 | **33,158** |
| index-visible window accesses | 115 | **124** |
| `scene_flow_dispatcher` | 8 / 393 | **393 / 393** |

⚠️ **A block entered from outside gets the stateless entry condition** — `$zero`
and the proven constant `$gp`, exactly what a call boundary already restores — so
`merge_constants` can only weaken an existing block, never strengthen it. That
withdraws **120** address resolutions across the corpus, and those are not a
regression: they were resolved on the assumption that a block could only be
entered from its own function's entry, and the incoming edges disprove it.

> ⚠️⚠️ A first attempt handed that entry condition to *every* block start inside
> the extent, including ones the function's own walk already reaches and the `jr`
> island targets it already follows. That withdrew **1,320** resolutions instead of
> 120 — sound, but needlessly destructive. Only blocks with a genuine
> **cross-extent** predecessor may get it; `cross_extent_entries()` is that filter.

## Explicitly not started

- **Whole-image DATAFLOW.** Reachability is now whole-image; constant propagation
  is still per-extent, which is why an externally entered block falls back to
  `{$zero, $gp}` instead of the meet of its real cross-function predecessors.
  Recovering those 120 soundly is a refinement, not a correctness requirement.
- **Affine recovery** on the **12,443 non-stack** unresolved access sites. The
  ledger contains 19,320 unresolved sites in total; the other 6,877 are
  stack-relative. Recovery would benefit future frontiers as well as F01, but it
  is not required for honest mechanical accounting and is not currently on the
  critical path. Revisit it when a concrete frontier depends on reducing those
  blockers.

## Companion: the frontier resolver

`tools/phase4_frontier_resolve.c` — actually
`tools/phase4_f01_frontier_resolve.c` — is what you run **after** the extractor,
and it is the tool that turns a frontier into an answer.

The extractor's job is to say honestly what it cannot decide. The resolver takes
a specific question and decides as much of it as static analysis can:

```bash
cc -O2 -Wall -Wextra -Werror -o /tmp/fr tools/phase4_f01_frontier_resolve.c
tools/phase4_f01_frontier_resolve REBUILD/files
```

It re-walks the extents the frontier flagged, using stronger base recovery than
the static index — `$gp`, `lui`/`addiu`/`ori` materialisation tracked per
register and invalidated at every branch target, `addu` of known constants — and
gives every memory access exactly one disposition: `RESOLVED_HIT`,
`RESOLVED_MISS`, stack-frame bounded, or `UNKNOWN`. It exits non-zero if any
**store** reaches a watched window from outside the enumerated writer set.

Current result (F01, `analysis/phase4_f01_frontier_resolve.json`): 1,960 accesses
examined, 62 reach a window, 1,181 provably miss, 314 stack-bounded, 403 unknown —
**no additional writer among the resolved accesses** (NOT completeness — 231
unresolved stores remain, corrected from 106), and **34 previously unlisted readers** spanning sound,

> ⚠️ **Re-baselined 2026-08-05 — these figures were a LOWER BOUND.** 20 of the resolver's 29 extents stopped short of the real function end (ends were hand-picked, not taken from the static index), leaving **28,252 bytes / 7,063 instructions inside the censused functions unread**. Corrected: **3,681 accesses examined, 100 reach a window, 2,280 provably miss, 506 stack-bounded, 795 unresolved (231 STORES, 564 loads), 50 previously unlisted readers**. `resolved_writers_not_previously_enumerated` is still **0** over the full extents, so the no-new-writer finding survived and strengthened — but every count above understated the work. See [[Phase 4 - Typed State Compiler]].

animation, HUD, checkpointing and per-level AI. See
[[MEM_800823A0_scene_transition_request]] for the reader table and for three of
those readers decoded.

### Where it is insufficient, and how to improve it

Stated plainly, because the 403 unresolved sites — **106 of them stores** — are
the honest limit:

0. **It cannot exclude an unknown writer, and must not be read as if it could.**
   `resolved_writers_not_previously_enumerated: 0` means no additional writer
   *among the resolved accesses*. Reporting that as "the writer set is complete"
   was an overclaim that reached Canon before it was caught. The tool now exits
   non-zero while any unresolved store remains, splits unknowns by load/store,
   and retains every site individually.

1. ~~It cannot resolve argument-pointer bases.~~ **Done** — unknowns fell 653 →
   403 (38%). Three things were needed, and the third was the real blocker:
   *(a)* seed an argument value proved from the callers (`player_vertical_update`
   has exactly ONE caller, which passes `a0 = s0 - 0x90` with `s0 = 0x800A6590`,
   so `a0` is the player struct base `0x800A6500`); *(b)* let a register written
   exactly once survive a control-flow merge, since no path can disagree about
   it; *(c)* **stop counting a callee-save restore as a definition.** `s1` looked
   multiply-defined purely because of its epilogue `lw s1, 0xdc(sp)`, so a base
   set once in a 6 KB function died at the first branch target. Seeding alone
   moved ONE access; the restore fix moved 250.
   Still unresolved this way: `actor_player_contact_resolver`, whose `a0` is
   itself memory-loaded (`lw a0, 0x2504(a0)`) and is therefore left unknown.
2. **Extents are hardcoded.** The 30 extents are compiled in. It should read
   them from the frontier blocker ledger so it tracks the extractor instead of
   drifting from it.
3. **It cannot follow a pointer loaded from memory.** A base read out of a struct
   stays `UNKNOWN`, and correctly so — closing that needs the typed-state work
   (tooling increment 2), which is precisely what would say "this field holds a
   pointer to X".
4. **Its known-writer list is a compiled-in constant.** That bit me: the first
   run reported 12 false discoveries because the list was resident-only. It
   should be derived from the census JSON, not transcribed.

5. **Two defects worth remembering, both real rather than cosmetic.** Writer
   identity was keyed on pc alone, and overlay addresses repeat — two overlay
   loads were mislabelled as enumerated writers of *other* overlays, and a
   genuine store at a colliding address would have passed. Identity is
   `(image, pc)`. And "written exactly once" is not dominance: a branch can skip
   the sole definition. Both are fixed, and the branch-bypass counterexample is a
   permanent `--self-test`.

What remains needs real reaching-definitions dataflow over the CFG rather than a
linear walk with invariance rules — a component, not a patch. **Typed-state
tooling (increment 2) is the better lever**: most unresolved stores are
actor-pointer based, and a field schema is what turns "unknown base" into "a
pointer to the actor struct, which cannot alias a `$gp` global".

None of these make the current answer wrong — a `RESOLVED_HIT` is a proof and an
`UNKNOWN` is declared, never argued away. They bound what the answer covers.

## Files

| surface | path |
|---|---|
| extractor | `tools/phase4_frontier_extractor.py` |
| checker (pre-existing) | `tools/phase4_semantic_frontier.py` |
| F01 seed | `config/phase4_f01_frontier_seed.yaml` |
| F01 query | `config/phase4_f01_frontier_query.yaml` |
| F01 extraction summary | `analysis/phase4_f01_frontier_extraction.json` |
| F01 blocker ledger | `analysis/phase4_f01_frontier_blockers.json` |
| F01 checker result | `analysis/phase4_f01_frontier_result.json` |
| tests | `tests/test_phase4_frontier_extractor.py`, `tests/test_phase4_semantic_frontier.py` |
| **static census** | `tools/phase4_frontier_static_census.py` |
| static-census probe | `tools/phase4_callback_probe.c` |
| static-census receipt | `analysis/phase4_frontier_static_census.json` |
| static-census tests | `tests/test_phase4_frontier_static_census.py` |
| **resolver** | `tools/phase4_f01_frontier_resolve.c` |
| resolver output | `analysis/phase4_f01_frontier_resolve.json` |

## Next

Typed-state and ABI accelerators both consume this frontier. Tooling-plan
increment numbers are distinct from the nine Phase-4 Definition-of-Done
dimensions:

| tooling increment | accelerator | Phase-4 DoD dimension | state |
|---:|---|---|---|
| 1 | frontier extractor | 2 — Complete frontier | **closed** |
| 2 | typed-state join compiler | 3 — Typed state | not implemented |
| 3 | ABI ledger/compiler | 5 — Original interfaces | not implemented |

Proceed next with tooling increment 2. See [[Phase 4 - Frontier Closure Workbench]]
for the separate statement that only DoD dimensions 1, 2 and 7 gained general
compilers in the original workbench candidate.
