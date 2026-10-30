---
kind: playbook
id: PLAYBOOK_game_solving_phase_4
name: Phase 4 - Solve Every Gameplay and Engine Subsystem
aliases:
  - Phase 4 - Solve the Seed and Plant Vertical Slice
status: planned
created: 2026-07-11
updated: 2026-08-05
confidence: high
parent: PLAYBOOK_game_solving_roadmap
previous: PLAYBOOK_game_solving_phase_3
next: PLAYBOOK_game_solving_phase_5
depends_on:
  - PLAYBOOK_game_solving_phase_1
  - PLAYBOOK_game_solving_phase_2
  - PLAYBOOK_game_solving_phase_3
---

# Phase 4 - Solve Every Gameplay and Engine Subsystem

> [!note] Shared static-ASM prerequisite gate - 2026-08-06
> [[Phase 4 - Static ASM Prerequisite Gate]] is independently hard-truth verified
> at commit `3943e88f6e8c80ea0e3105d834c8236db8021cf0` and is ready for
> integration into F01 and other row frontier queries. It establishes the exact
> resident byte partition, typed indirect-site identity, the sole `jr`
> census delta at `0x80010364`, and direct-only 393/393 reachability for
> `scene_flow_dispatcher`. It does not close F01 or Item 2: 33,888 bytes remain
> explicitly unclassified and 148 typed indirect sites still lack complete
> target sets. F01 status, registry status, and the direct writer census were
> not changed.

**Navigation:** [[Phase 3 - Reconstruct Semantic Architecture and State Ownership|Previous phase]] · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]] · [[Phase 5 - Prove Cross-System and Full-Campaign Integration|Next phase]] · [[Phase 4 - Frontier Closure Workbench|Frontier closure implementation]]

## Item-2 tooling - the frontier extractor lands (2026-08-05)

The Item-2 compiler shipped by [[Phase 4 - Frontier Closure Workbench]] is a
CHECKER: it validates a fully declared query. It had no way to obtain one, and
hand-authoring is what kept every row away from it. That feeder now exists —
[[Phase 4 - Frontier Extractor]], Plan Item 1 **closed** after seven adversarial
review rounds.

It projects the retained static index into a query, recovering **callers** by
inverting the whole call graph (the asymmetry Item 2 names, which a store-site
census structurally cannot close), and emits the **union** of the index's
CFG-reachable accesses with an independent linear binary scan — because the index
only records accesses in blocks whose CFG it recovered, and it recovered 8 of
`scene_flow_dispatcher`'s 393 instructions.

What the extractor still could not do is decide anything about an access whose
**base register it could not resolve to a constant** — the wall F01 hit, with 106
unresolved STORES blocking its writer-set completeness claim. That is Plan Item 2
tooling, and it now exists: [[Phase 4 - Typed State Compiler]]. It bounds such an
access by the region its base provably points into, and **retired 19 of F01's
106** on its first run. Its provenance checks are enforced by an ASM verifier the
compiler **rebuilds from source and runs**, never an attestation the schema hands
it. F01's item 2 remains open (**73** unresolved, **101** more outside the ledger — the
figures grew twice, when a truncated-extent bug and then a truncated extent-SET
bug were fixed, both found by checking the scope a tool actually walks).

Its **ABI accelerator** (Plan Item 3, DoD dimension 5) is built and verified: it
types an argument by reading every caller and recovering the constant from the
instructions, rather than counting callers and believing the schema. It decides
**zero** additional F01 blockers, and `--survey` measures why — 87 of the 96
still-open blocking stores have a base that is locally computed, not an argument.
That negative result is the useful one, and it was acted on: the second opinion
(`region_provenance.c`) was resident-only because it required a `PS-X EXE` header,
and now analyses the 20 raw **overlay** images too. That took F01 to **64 of 238**
blocking stores decided — more than any ABI work did. The remaining 73 are
characterised rather than mysterious; the ABI survey attributes 77 still-open
stores across ledger groups (68 locally computed bases, 7 reached only through
`jalr`, 2 with an unrecoverable caller value), a slightly different denominator
from the fixture-row count, which the survey's own `denominator_note` discloses.

The truncated-extent bug that made F01's figures move was then swept for across
the whole repo — [[Phase 4 - Extent Audit]]. **No other tool truncates a census
scan.** ⚠️ But a fresh verifier then found the sweep had checked the wrong thing
for F01 itself: it audits whether a declared *end* stops short, and F01's
remaining defect was a short *set* — 29 of the 37 functions its own criterion
admits. Both are now generated from the index. The sweep did find 9 `sha256`
drift pins covering less than the whole function (worst: 16% of
`gameplay_state_reset_cursor_seed` in C16, 26% of `results_screen_render` in A17),
which is a weaker pin rather than a wrong number. A ratchet now fails on any newly
typed truncation.

⚡⚡ **The reusable lesson**, which cost seven rounds: every failure was the same
shape — *a property proved over the thing being looked at, then reported as a
property of the system*. The question that catches it is **"who chose the thing I
am verifying against?"** If the answer is "the artifact under review", it is not
a check. That applies to the remaining accelerators too.

F01 served as the acceptance fixture and exposed a real defect in every round; it
correctly remains `item2_ready_for_review: false` with six named blockers.
CFG/jump-table recovery and affine recovery are explicitly **not** started.

## F01 Anthill - bounded, objective + lifecycle decided (2026-08-05)

**Status: F01 BOUNDED EXHAUSTED.** The row's standing gap was
`missing: Whole objective/lifecycle`. Both halves are now decided rather than
described, by 83 instruction-word assertions (`tools/phase4_f01_objective_lifecycle.c`,
`-Werror`, exit 0) plus one armed 3,267-frame Interpreter replay.

**The objective is a five-way switch, not a trigger.** Every frame,
`player_vertical_update` calls `FUNC_80038F38`, which returns `0` unless the low
byte of `player+0x82` is `1` — the **GROUNDED** flag (`0x0101` grounded / `0`
airborne), produced by the movement integrator `FUNC_8003633C`, which also owns
the current-sector slot `0x80090560 + index*20`. **No region code has any effect
while Flik is airborne.** A re-entry guard at `0x8004965C` makes every region
single-shot per scene. Codes 1 and 4 enter the player **damage** handler; codes 2
and 3 complete the scene. LEVEL01 authors exactly one nonzero code in 189
sectors — sector 177, code 2 — so Anthill's whole authored trigger set is
`{exit}`, with no hazard regions.

**The exit's footprint is recovered to the vertex.** The 0x20-byte collision
record is a **triangle** (normal, first vertex, two edge deltas at `+0x0c`/`+0x10`
and `+0x12`/`+0x16` — the offsets `FUNC_80038090`'s point-in-polygon test
actually reads). Proved rather than assumed: the tool rebuilds each normal from
the cross product of the decoded edges and requires it to reproduce the shipped
`|n| == 0x4000` normal; both records reproduce exactly. Sector 177 is 2 triangles
sharing an edge — a steeply inclined quad, the entrance ramp surface.

**The lifecycle is a shared request enum.** `0x800823A0` is not a completion
latch but a **7-value scene-transition request** with 28 writers across the
resident image and all 21 overlays, paired with timer `0x80082470` (one decrement
per 2 frames at `0x800553F8` — the 30 Hz logic tick). Anthill emits request 1 /
timer 23; **stage entry uses the same machine** with timer 45; death emits
request 2, which **skips** the finalizer `0x80045A60` that completion runs.

**Live confirmation upgraded an inference to an observation.** At the triggering
instruction the captured memory read sector index **177** and GROUNDED
**0x0101** — previously sector 177 was inferred from "it is the only authored
code-2 sector". The code-1/3/4 and death arms took **zero** hits over the whole
stage, and the request word was written exactly three times, all from resident
PCs: no overlay verb participates in Anthill's transition.

⚠️ **Two corrections to standing Canon.** `Level_Goal_and_Exit_Trigger_Matrix`
read code 1 as a "type-2 transition path"; `FUNC_8004A700`'s `a3` is a branch
flag, not a destination, and request 2 is reached only when the damage is lethal
— codes 1 and 4 are hazard regions. And E02's "code 3's dispatch body is
identical to code 2's" is identical *except one store*: the `sp+0x50` commit flag
(zero-initialised at `0x800481BC`, set only by arms 1 and 2) re-commits position
and clears GROUNDED at the join.

**Death closed on a second Anthill movie** (operator pointer:
`Bonus01_Counter_ResetTest`, scene id 1, Flik dies). Four non-lethal hits write
no request; the fifth takes health `0 → −1` and writes request 2 / timer 60. The
consumer then **proceeds** (`0x8004FF14` fires) and re-reads request `2` with
`[$gp+0x4c4]` measured at `0` — yet the finalizer `0x8004FF48` takes **zero**
hits. The skip is therefore proven, not inferred: the only condition that could
have caused it was `request == 2`. Respawn re-runs the scene-**entry** pair
(`0x8004FE44`/`0x8004FE4C`, timer 45) with scene state unchanged, so death in
Anthill is an in-place respawn rather than a scene change. F01 has no remaining
fixture need.

⚠️ Correction to my own first write-up: the transition timer's 2-frame tick is
**nominal, not strict** — the completion run was uniform `{2: 66}` but the death
run slipped 9 of 104 intervals to 3 frames.

See [[EXP_2026-08-05_phase4_f01_objective_lifecycle]] ·
[[MEM_800823A0_scene_transition_request]] · [[MEM_80082470_scene_transition_timer]].

## E02 collision plane half - bounded, campaign-complete (2026-08-04)

**Status: E02 BOUNDED EXHAUSTED — both halves, all 16 scenes.** A compiled C
tool (`-Werror`) independently reimplements the decoded converter FUNC_80030F60
and diffs its prediction against actual save RAM per level: **16 of 16 scenes
round-trip EXACTLY** (0 field mismatches, 0 malformed blocks).

Structural findings: **two container families** carry collision source —
`LEVEL*.RAW` chunk 32 (compressed, blocks from container offset 8) and the
uncompressed `TERRAIN.ALL`/`TERR1.ALL` terrain containers (blocks from offset
4) — parsed by the same converter. The runtime table is an AUTHORED prefix plus
a RUNTIME-REGISTERED tail (campaign: 3,235 authored + 720 registered = 3,955
sectors); flat sectors inherit the most recent geometry sector's block pointer;
runtime +0x2E ← src +0x2C while runtime +0x2C and +0x0C both ← src +0x14.
Census: 58,555 planes in 16,653 groups — 52,518 floors, 5,686 ceilings, 351
vertical walls, all normals unit-length, every block walk terminating exactly.

⚠️ **Two retractions, same day, both my own errors — caught by the operator's
Interpreter movies.**

1. I claimed **four** scenes had "runtime-BUILT" tables with "no disc-verbatim
   source anywhere". Wrong twice over: the sweep never covered `.ALL`
   containers, and a bounds bug rejected the correct container even once in
   scope (containers hold only the authored prefix; the tool demanded room for
   every runtime sector). The fresh-load movie settled it — breakpointing the
   converter mid-load gave source pointer 0x801973F0 against container base
   0x8017A0A4, matching `/LEVEL07/TERRAIN.ALL` at offset 119,628.
2. I then claimed **Bug Bar alone** was the true runtime case — and stated,
   without replaying it, that the operator's second movie was a Clover run.
   The operator corrected me; replay showed scene 14, 46 sectors, actor id 36
   at HP 50→0: the Thud fight from boot through defeat. Instrumenting its load
   showed the same ordinary converter, with the source filled by the LEVEL.RAW
   decompressor `fcn.8001a1dc` from `LEVEL04/LEVEL1.RAW` (decompressed offset
   487,284). My candidate pre-filter had required four matching records where
   Bug Bar authors exactly **one** (its other 45 are runtime-registered — the
   numeric signature of E11's per-tick arena).

The two lessons are recorded in the row and memory: *a negative is only as
strong as its search's proven completeness*, and *inference from conversation
is not measurement*.

**Bonus finding (phase-3 residual).** The same captures caught the writers of
the contact-object kind→descriptor table 0x80096B98, unresolved until now:
overlay-resident code at 0x800B5BD0 / 0x800B5C04-0C10 and 0x800B39E8 /
0x800B3A1C-3A28 — nothing in the resident EXE, which is why resident-only
searches never found it. Which overlay owns them is the descriptor row's next step.

Gate: `tests/test_phase4_e02_collision.py` (7 tests, incl. the block-base
family invariant and the authored/runtime split). See
[[EXP_2026-08-04_phase4_e02_collision_roundtrip]].

## E02 collision region codes - half-row bounded (2026-08-03)

**Status: the region-code half of E02 is closed; plane-record breadth remains.**
The row's `next` ("enumerate all region-code values; bind each to its consumer
branch") closed in one pass built almost entirely on committed substrate: the
RCG-003 catalog's offline save-state parser (reused via import), the loader's
own count global [0x800822A0], and the byte-verified hand-asm corpus.

The UNFILTERED census (no 1..4 assumption, no plausibility rules) over all 16
level anchors — 3,955 sectors, per-level counts 46..634 — proves the campaign
region-code domain is EXACTLY {0,1,2,3,4}, reproduces every committed catalog
row, and passes a disc-side chunk-32 cross-check on LEVEL01. The binding
covers all three callers of sector_region_code_query: the player dispatch
(code 1 → FUNC_8004A700 variant A; codes 2 AND 3 → a byte-identical shared
exit body — meaning the committed catalog's LEVEL02/04/05 be-here proofs
live-prove code 3 and LEVEL01/14 prove code 2; code 4 → a state-gated
FUNC_8004A700 variant B), checkpoint_save (BAILS when code==4 — no-checkpoint
zones, dovetailing C15's safe-anchor law), and the mover update (objects in
code-1 sectors are retired via +0x6E=0). Census geography matches: code-1
bands lead into ending sectors; the nine levels exposing no codes are exactly
the conditional/boss-ending set.

Gate: `tests/test_phase4_e02.py` (7 tests incl. offline regeneration and EXE
spot-pins of the dispatch words). Residuals, explicit: FUNC_8004A700's
transition semantics, a live code-4 crossing, and the row's pre-existing
wall/ledge plane-record breadth (untouched). Provenance note: the training
(24,3) data point is this census's own reading — an uncommitted WIP page by
another agent concurs and was deliberately not cited. See
[[EXP_2026-08-03_phase4_e02_region_codes]].

## E16 chunk roles - closed by reading the format, not tracing it (2026-08-04)

**Status: the row's named `next` is DONE.** It asked to close 46 "likely"
LEVEL.RAW chunk roles "via targeted load traces". A cheaper and stronger
instrument existed: **every chunk carries its own subtype marker, a `u32` at
decompressed offset 0** — the committed chunk-34 note's "marker 0x101@0"
generalises. So a chunk's family can be *read off its bytes* rather than
inferred from when it loads.

A compiled C classifier plus the committed byte-exact codec ran over **every
chunk of all 24 `LEVEL*.RAW`**. **All 46 "likely" chunks are confirmed, none
contradicted**: 15–27 are `0x22` sprite/animation strip containers, 36–68 are
alternating `0x101`/`0x102` mesh definition/payload pairs. Campaign families:
296 texture · 228 sprite strips · 208 mesh defs · 228 payloads · 17 seed
tables · 14 collision-plane · 14 collision sector-source · 9 backdrop.

Three findings beyond the ask. Two **exact size invariants** — every `0x104` is
17,764 bytes and every `0x23` seed table is 1,796. A **mesh pairing law**:
every definition has a payload of the same object id, *never* the reverse, with
the sole asymmetry being object id 11 (payload, no definition, in 16 of 17
files). And a **correction**: chunk 33 was recorded as the "tail" of chunk 32,
but its marker `0x104` is a distinct family, not a continuation.

**It also grew the known-unknowns, deliberately.** Reading 24 files instead of
one exposed **74 chunks with markers outside every classified family**
(`0x20`, `0x26`, `0x28`–`0x2A`, `0x30`–`0x5C`), concentrated in `LEVEL00/*.RAW`
and two `LEVEL*1.RAW` — invisible to a LEVEL01-only census. The pass therefore
converts "46 unknown roles" into "46 confirmed + 74 enumerated with exact
locations", which is a bounded next task rather than an open-ended one.

Scope limit recorded honestly: the `< 0x20` → "texture page" mapping is
inherited from the committed LEVEL01 labels and holds only loosely campaign-wide
(274 of 296 canonical sizes, 22 others), so it is described as a size-varied
VRAM-upload family rather than a uniform page. Gate:
`tests/test_phase4_e16_chunk_census.py` (6 tests). See
[[EXP_2026-08-04_phase4_e16_chunk_roles]].

## E16 follow-up - the 46 registered chunks, and a confident false negative (2026-08-04)

**Status: the row's own next step is DONE.** The census left 46 chunks
(markers `0x28`–`0x5F`) unclassified for a principled reason: the loader
**registers them by pointer and never interprets them**, so their format belongs
to whoever reads `TABLE[marker]`. Find the readers, get the formats.

**The answer.** Three read sites, each reaching a VRAM upload primitive:
`level_texture_stage` 0x8003C8BC @0x8003C920 → `level_texture_upload`; and two
sites inside `vram_upload_wait` 0x8003C388 (@0x8003C3C0, @0x8003C5EC) → `LoadImage`.
The registration **defers the upload**: the loader records where the resource
sits, and the frontend uploads it by marker when the screen needs it. All 46 live
in `LEVEL00` and are the frontend's art.

Two consumer access patterns give two header families, and the size law derived
from each — with **no free parameter** — holds on **46/46 chunks exactly**:
family A (`lw` fields, payload at +16) is 16bpp, `size == 16 + w*h*2`; family B
(`lhu` fields, payload at +12) is indexed with a 256×RGB888 palette,
`size == 12 + palette_bytes + w*h/(1 or 2)` per the `+10` depth flag. Decoding
with that layout renders real art — marker `0x43` is the memory-card UI text
atlas, marker `0x28` the 320×256 title screen — which is what rules out a
plausible-but-wrong header reading. Gate:
`tests/test_phase4_e16_registered_chunks.py` (11 tests).

**The part worth carrying: a thorough static search produced a confident false
negative.** A compiled scan matched every load/store whose displacement equals a
table's offset from a `lui`, across the resident EXE *and* all 30 `.BIN` files,
in both base-formation forms, plus a check that the 32-bit addresses never appear
as data constants, plus a `$gp`-unreachability argument. It returned **three
stores and zero reads** — and "these tables are written but never read" was
false. The consumers *index* the table (`lui at,0x800A; addu at,at,idx;
lw v0,DISP(at)`), so `DISP` is not the base: the 0x30–0x57 reader sits at
`-19032`, just outside the `[-19224,-19064]` window the base implied. A live
`readwrite` watch found all three in a single run.

The completeness of a search is a property of *its own assumptions*, and the
assumption here — that a table is addressed from its base — was invisible until
it failed. `tools/mips_ea_window.c` now resolves and labels `[INDEXED]` effective
addresses so the blind spot is reusable rather than repeatable.

**Two corrections banked.** My earlier "the 46 are NOT images" over-corrected an
earlier over-claim: they *are* images, and the dimension-shaped fields I
dismissed are exactly what the consumer reads. "No interpreter **here**" is not
"no interpreter." And `tools/launch_repro_playback.sh` printed a hardcoded
`CachedInterpreter` in its READY banner regardless of `--execution-mode` — in a
launcher whose whole purpose is CPU-mode matching, that made a correct
Interpreter launch read back as the one mode that cannot be traced.

**Follow-through the same day.** The one residual this pass created — how the
4bpp/8bpp split reaches `level_texture_stage` — closed. It *does* read the `+10`
flag, at `0x8003CB54`, 0x298 bytes past the table fetch, and uses it to rewrite
the VRAM rect width (`w>>1` at 8bpp, `(w+3)>>2` at 4bpp: pixels per 16-bit word).
The lead I had named, `andi v0,v0,3` at `0x8003C954`, was **wrong** — an
alignment test picking between a word copy and the `lwl`/`lwr` path. A plausible
instruction near the code you happen to be reading is not evidence about a
question you have not yet located in the code.

Reading the rest of that function also yielded the RECT at `0x80089848`, the
pixel source `chunk + 12 + (palette_bytes & ~1)` — independently reproducing the
`12 + round_down_even(+8)` rule already pinned for the texture-page path — and
the palette pipeline: 768 bytes copied to a stack buffer and walked **three bytes
at a time** (code-level proof of 256 × RGB888), scaled to 75% by `(v*96)>>7`
*except* entries with `R<5 && G>=250 && B<5`. That exception is the pure-green
**transparency key**; marker `0x30` has exactly one such entry (index 0 =
`(0,255,0)`), used by all four corners and half the image, and scaling it would
turn 255 into 191 and break the match.

See [[EXP_2026-08-04_phase4_e16_registered_chunk_consumers]] and
[[SYS_registered_chunk_image_resources]].

## E16 resource lifetime - a dangling-pointer hazard the retail game never trips (2026-08-04)

With the tables understood, the row's other untouched DoD item — **resource
ownership and lifetimes** — became directly testable, because these tables hold
raw pointers with no refcount, size, or owner field. Their lifetime *is* whoever
zeroes them.

The three are not treated alike. The loader's init zeroes **0x28–0x2F** and
**0x58–0x5F** on every load; **nothing clears 0x30–0x57**. Replaying boot →
frontend → Clover Forest with watches plus periodic table snapshots — snapshots
matter, because a populated-then-untouched slot emits no further events and looks
exactly like a slot that was never populated — 38 slots fill in the frontend and
**36 still hold pointers after the scene changes to gameplay**.

"Survives" is not "dangling", so the pointers were checked rather than assumed: a
chunk's marker is a `u32` at its own offset 0, so a survivor that still reads
back its marker would be stale-but-intact. **0 of 36 do.** They point into
`0x800BE670..0x80181E44` in the high heap, which the gameplay load has refilled.

Retail never trips this because nothing calls the upload path for those markers
outside the frontend — the safety is **positional, not structural**. Nothing on
the path validates a pointer, so `level_texture_stage(marker)` during gameplay
would read garbage `u16` width/height/palette_bytes out of level data and hand it
to `LoadImage` as a VRAM DMA size. That makes it a real hazard for any mod
reusing the frontend's image path for custom HUD or menu art: the table still
*looks* populated.

Scope kept honest: one movie, one transition; gameplay → gameplay is untested,
and the heap allocator itself is uncharacterised — only the reuse is observed.
See [[EXP_2026-08-04_phase4_e16_resource_lifetime]].

## E16 overlay ABI - the lower bound was complete all along (2026-08-04)

The last E16 claim still labelled a **lower bound**: per-overlay entry lists and
a "27 of 42" union, limited by a detector that accepted only `addiu sp,sp,-N` or
a bare `jr ra` as a function start.

Replacing the assumption rather than widening the pattern: in contiguous code a
function start is the instruction after the delay slot of a `jr ra`, which
assumes no prologue at all. That detector finds **39 of 42**, and the two
together find **42 of 42** — every committed region-A entry point is a function
start in at least one overlay. The bound was not just loose; the union was
complete and could not be demonstrated.

Both detectors are kept because they err in **opposite** directions — prologue
matching under-counts, return scanning over-counts on data that decodes as a
false `jr ra` — so they bracket the truth instead of trading one guess for
another. Three entries are found *only* by prologue matching, so the new
detector does not subsume the old. And the prologue detector reproduces
**exactly 27**, which is the check that licenses the comparison at all: the old
method was replicated faithfully before being improved on.

Two honest residuals: 18 of the 42 rest on a single detector, and nothing here
checks at runtime that a scene actually *calls* the entries its overlay
implements. Also corrected: there are **20** `LEVEL*.BIN`, not 19 —
`LEVEL00/LEVEL.BIN` is a 4-byte stub.

### ⏹ E16 vs exit-gate item 2 — attempted, NOT met, and the wall is general (2026-08-04)

E16 was the best-positioned candidate left. Its registered-chunk tables are
absolutely-addressed globals rather than pointer-reached state, so the analyser's
own escape argument looked available here in a way it never was for B06:

> *"If no store anywhere does [write a block pointer to memory], then no memory
> location can ever hold such a pointer, so no `lw`-loaded base can be one."*

If that holds, the entire ~12,000-site unresolved-base residual is excluded at a
stroke and item 2 is met. It does not hold.

**Measured:** 0 full-width escaping stores and 0 argument-passing call sites
across all three tables — but those zeroes range over **decidable values only**.
~20,180 region values per run carry no proven index bound, so the analyser cannot
say whether they may point into the table. An arithmetic progression with an
unknown index reaches everything: treating those as escapes makes the test a
tautology (57 stores / 258 call sites flagged for a 160-byte stride-4 window),
and treating them as non-escapes assumes the conclusion. **Item 2: NOT MET.**

**The wall is the same class B06/B08 hit, reached through a different door.**
B06's blocker was 4,490 image-wide stores with unresolved *destinations*; E16's
is ~20,180 region values with no proven *index bound*. Both are the same
deficiency — the image does not statically yield the bounds the argument needs —
and neither is row-specific. This is the third independent data point, after
B06/B08 and E15, that **item 2 as written is not reachable with current
technique**. The next move is a general capability (index/pointer bound
recovery), not another row.

**Two analyser defects found and fixed on the way**, which is the durable payoff:

1. **TIER 3 `EXCLUDED_OUT_OF_BOUND` was unsound.** It asserted a bound from the
   mere *existence* of a comparison and propagated it to the branch where the
   comparison **failed**. It excluded `0x8003BF48` — an access runtime shows
   firing 36 times — using `idx_bound 32` taken from `slti $s4,32` 7 KB earlier
   (the loader's class split, whose branch went the other way). Bounds now apply
   per-edge, are captured *at* the branch before the delay slot runs, and are
   dropped when the delay slot rewrites the register they name. 35 unsound
   image-wide exclusions disappeared. **B06's committed 416/165/251 is
   byte-identical** — its artifact records 0 in-scope out-of-bound exclusions, so
   it never used the tier.
2. **The escape test inspected `K_CONST` only**, so a `K_REGION` value — the only
   shape E16's table pointers ever take — could never be flagged. Its "0 stores
   may write a block pointer" was **structurally vacuous** for this row: a clean
   negative from a check that cannot see the thing is not evidence. Regions are
   now classified three ways, with the undecidable case *counted* rather than
   silently resolved in either direction.

**Scope kept honest:** the attempt covered the three pointer tables only. Item 2
is a per-subsystem bar, so even closing them would not have closed E16 — overlay
region A and its 42 entries, the streaming table `0x8007EFE8`, the high heap, and
the LEVEL.RAW/DAT/BIN assets remain unmeasured.

Artifact: `analysis/phase4_e16_frontier.json`. Gates:
`tests/test_region_provenance_bound_soundness.py` (7).

## The item-2 wall, attacked directly: index/pointer bound recovery (2026-08-04)

Three rows have now stopped on one deficiency, so the next move was the
capability rather than a fourth row. `tools/affine_bound_recovery.c`.

**The insight.** The bounds are *in* the code. They are just not in a form a
per-register bound table can use, because the compiler tests a **derived** value:

```
addiu $v0, $s4, -48      # v0 = marker - 0x30
sltiu $v0, $v0, 40       # gate  -> marker in [48, 88)
beq   $v0, $zero, skip
sll   $v0, $s4, 2        # ...and the INDEX is the raw marker
```

A bound recorded against `$v0` is useless twice over: it names the derived value,
and `$v0` is then reused for the scaled index. What is needed is the affine
**relation** `v0 = s4 - 48`, so the range implied for `v0` translates back onto
`s4`. The pass tracks `value = mul*sym + add` per register and recovers three
idioms: `sltiu (idx-B), N` (two-sided, the standard range check), `andi idx, M`
(unconditional, no branch at all), and `slti idx, N` (upper bound paired with an
implicit lower bound of 0 — the same non-negative-index convention TIER 2 already
discloses). Ranges apply only on the edge where the comparison is true.

**Ground truth, because a yield number nobody checked is worthless.**
`0x8003BF48` recovers `[48, 88)` — exactly the window established empirically
from the live watch, and exactly the access the previous analyser *excluded*. The
reporter refuses to print a yield if that check fails.

**Measured yield: 702 of 6,229 region-formed sites bounded (11.3%).** For the E16
windows the undecided residual falls from ~12,280 to **5,527** — roughly halved —
and 696 of the 702 bounded sites are now provably *disjoint* from the target
rather than merely possible.

**Item 2 still does not close.** 5,527 sites (88.7%) have no recoverable bound.
The capability is necessary, not sufficient, and is reported that way.

**Why the rest resist, and what comes next.** The remaining indices are loaded
values with no static range check in the same function — the bound, where one
exists at all, lives in a **caller** or in the data. Closing them needs
**interprocedural range propagation** (argument ranges at call sites). That is
the next capability, not another idiom and not another row.

**Two implementation bugs worth carrying**, both of which returned almost-nothing
rather than failing loudly: symbols must be keyed by **definition site**, not
allocated per visit (a fresh id each fixed-point round means joins never agree
and everything decays to UNKNOWN); and a register that merges to UNKNOWN at a
loop header loses every relation, so it needs a stable **block-entry** symbol —
the bounds check and the index use are usually in the same block, where an
opaque-but-stable symbol suffices. Also: `functions_resident.txt` stores size in
**decimal**, and parsing it as hex silently inflates every function extent.

Artifact: `analysis/phase4_bound_recovery.json`. Gates:
`tests/test_phase4_bound_recovery.py` (8).

### Wired in by default — and it moved B06 from 251 to 192

A capability in a side binary benefits nobody: every agent would have to be told
it exists. So the cheapest idiom was ported **into `region_provenance.c`**, the
analyser rows already run. `andi rt,rs,M` clamps a value to `[0, M]`
unconditionally — no branch, no comparison, no path reasoning — which is how
table indices are masked throughout this image.

**B06/B08's residual fell from 251 to 192**, soundly: 59 more in-scope sites
discharged, with the reconciliation harness still reporting
hit-set-matches-python and `lost=0 / unexplained=0 / CLEAN`. Hand-verified
example — `0x800470F8` reads a 4,096-entry stride-2 trig table at `0x80074970`
whose index is masked by `andi 0x0fff`, so its reachable window ends at
`0x8007696E` and the power slot is **101,895 entries** away.

That matters beyond the number. **The STOP note's premise was that static
technique had been exhausted at 251.** It had not been exhausted — it had been
*unbuilt*. One unconditional idiom took 23% of the residual off. The remaining
192 are the same class of residual, just fewer, and still need interprocedural
range propagation.

⚠️ Do not read 192 as "nearly done".

## Interprocedural range propagation — built, measured, and the hypothesis was wrong (2026-08-04)

The named next capability. Argument ranges observed at every static `jal` are
unioned into the callee's entry state, so a bound established in a caller reaches
an indexed access in the callee.

**Soundness first**, because propagating into a function that can be entered
unseen would make every downstream bound worthless: **85 address-taken**, **129
overlay-called**, **337 with no static caller**, and every member of a call cycle
keep **unbounded** parameters. Overlay call sites in particular live in a
different binary entirely — the resident image simply does not contain them. The
fixed point settles (0 unsettled), and 149 of the 447 eligible functions gain a
bounded parameter.

**Measured gain: +8 sites (702 → 710).** Interprocedural propagation is *not* the
missing lever. Recording that plainly is the point — it redirects the next build
instead of licensing another round of the same.

**What actually moved the number was something else entirely.** Classifying every
unbounded site by where its index symbol was born — measurement, not assumption —
gave: **ALU 3,626 / block-entry 994 / load 775 / function-entry 124**, with the
defining-op histogram led by `addu` at **2,341 (42% of the residual)**, then
`subu` 481, `and` 420, `sra` 353.

So the residual is **neither data-derived nor waiting on callers**. It is `addu`
of two values that each already lack a range — and those were being dropped to a
bare opaque symbol because the affine *form* is lost. **Form and range are
different things:** `i + j` has no affine form in one symbol and a perfectly good
range whenever both operands have one. Adding range arithmetic for
`addu`/`subu`/`and`/`srl`/`sra` took the yield **710 → 899 (14.4%)**. A logical
right shift also bounds *any* 32-bit value unconditionally (`srl` by N ⇒ result
< 2^(32−N)), exactly like `andi`.

**Two implementation lessons, both of which produced a plausible wrong answer
rather than an error:**

1. The parameter update must **join** (widen only). Replacing it each round lets
   ranges *narrow*, and a narrowing chain through nested calls oscillates —
   measured, all 447 eligible functions were still moving at the round cap and
   the conservative fallback marked every one unbounded, i.e. the whole pass
   silently did nothing.
2. A **constant** argument is the tightest bound available, `[c, c+1)`. The first
   version required the value to already carry a range and discarded constants —
   the whole difference between 8 and 149 functions gaining a bounded parameter.

**Where this leaves item 2.** Still not met, anywhere. Ranges have to *originate*
somewhere — a mask, a comparison, a constant — and most index chains in this
image never touch one. That is a property of the code, not of the analysis, and
it is the first result in this whole line of work that argues the bar itself may
be unreachable rather than merely unbuilt.

Artifact: `analysis/phase4_bound_recovery.json`. Gates:
`tests/test_phase4_bound_recovery.py` (11).

## E16 against item 2, read against the written standards (2026-08-04)

**The bar that stopped three rows is not what any standard says.** Read in order:

- **Canonical DoD item 2** — *"relevant callers, callees, callbacks, indirect
  tables, overlays, readers, writers, and downstream consumers have been
  **enumerated**"*. Enumerated, and scoped to *relevant*.
- **Phase-4 exit gate** — *"No unresolved field, dispatch, asset, or overlay
  intersects that subsystem's behavior **without being explicitly bounded**."*
  Bounded, not absent.
- **"unresolved-intersection set is empty"** — from
  [[Phase 4 - Acceleration Tooling Strategy]]'s *frontier rules*, scoped to a
  **declared universe**, and explicitly *"never changes a Phase-4 dimension by
  itself."*
- **`phase4_promotion_preflight.py`** — reads a **hand-declared**
  `bounded_residuals` list; `RESIDUAL_INTERSECTS` fires per declared residual,
  `RESIDUAL_MALFORMED` demands `boundary` + `evidence` + `next_experiment`.

Bounding by evidenced argument is the mechanism, not a loophole. The stricter
reading came from well-earned caution and overshot; a correction is banked on
[[SYS_player_power_slot]], the page that propagated it.

### The reframe that makes the residual tractable

Intersection is not decided by whether an index is bounded *in the abstract*, but
by **how large it would have to be to land in the window**. For the 0x30–0x57
table, of 4,911 unresolved accesses:

| required index | sites |
|---|---|
| **< 64** | **3** — and all three are `0x8003C920`, the enumerated consumer |
| 64 – 1k | 67 |
| 1k – 16k | 2,720 |
| ≥ 16k | 2,121 |

Median required index **10,977**. The residual collapses to 538 clusters over 33
base regions, top 20 covering 96%.

### Status: NOT MET, substantially partial

Discharged with evidence: **113 of 4,911** (3 enumerated-reader + 110 bounded by
a documented object extent). The other **4,798 are declared `NEEDS_EXTENT`** and
are *not* counted as bounded. The named remaining work is ~530 object extents,
prioritised by required index — the 67 sites needing < 1k first.

### One retraction, caught before banking

I first bounded each object by the distance to the nearest **distinct base above
it**. That discharged 4,730 of 4,911 sites — 96%, and it looked like a
near-closure. It is not a bounding argument: the median such distance is **four
bytes**, because consecutive bases are usually sibling *fields* of one array
element (`lw a,X(i)` / `lw b,X+4(i)`), not the start of a different object.
Extent 4, max index 0–1, everything discharged for entirely the wrong reason.
Only documented extents count now.

⚠️ A check that passes *because* it is wrong is worse than no check.

Artifact: `analysis/phase4_e16_bounded_residuals.json`. Gates:
`tests/test_phase4_e16_bounded_residuals.py` (8).

### A fifth basis, attempted and not viable (2026-08-04)

The proposal: read each object's allocation or fill loop for its element count —
the trick that gave `_SsVmInit`'s literal **32** and the weld table's **mod-100**.
It does not generalise, and this measures why rather than asserting it.

**A real 43% blind spot, closed, worth exactly zero.** A loop bound compiles
either to `slti/sltiu idx, N` (immediate, already recovered) or to
`slt/sltu idx, limitreg` (register). The register form is **1,191** sites against
1,552 immediate ones — 43% of all comparisons — and was invisible to the affine
pass. Implementing it correctly left bounded sites at **899**, unchanged.

**Why:** only **8 of 1,191** loop limits (0.7%) are literals. 324 (27%) are
loaded from memory; 859 (72%) cannot be pinned. In this image element counts come
from **data** — chunk headers, save state, config — not from constants in the
instruction stream. The two successes are the *exceptions*, not the rule.

The `slt`/`sltu` handling is kept — it is sound, general, and would help another
binary — and documented in-source as zero-yield so nobody re-derives it hoping
otherwise.

**This settles the route.** Static extent recovery has now been pushed through
four working bases and one dead end; the remaining ~4,166-site residual is not
reachable by more analysis of the instruction stream. Route 2 — declare the ≥1k
remainder as one residual on the magnitude argument, with the campaign watch as
its falsifier — is the correct close, and should be decided **with** the movie
results in hand.

### The movie validator, built and proven before the movies arrive (2026-08-04)

The operator cannot tell *while playing* whether a recording will be usable, so
asking them to watch for a store was the wrong design. The check belongs in the
tooling: record normally, and the tool says which movies are usable.

**Three checks per movie:**

1. **Occupancy** — the 0x30–0x57 table must reach ≥30 populated slots. The check
   is on the *peak*, so it works for both styles: a hub save state starts
   populated, a from-boot movie climbs during the frontend.
2. **Control** — a loader init clear (`0x8003A3BC`/`0x8003A3C0`) or the bulk zero
   (`0x8005F6A4`) must fire. These run on every level load, so their presence
   proves the watch engaged *and* a load happened.
3. **Falsifier** — every event PC must be in the enumerated set of ten. A PC
   outside it is reported as a **find, not a failure**, and the movie stays
   usable — that is precisely what the campaign is looking for.

**Proven against a known-good movie first.** `E02_FreshLoad_Clover` returns
*USABLE AND CLEAN*: peak 36 slots (that table alone — the lifetime run's 38 was
the sum across all three), control fired, all 264 events from enumerated PCs,
nothing truncated. A validator nobody has run against a movie with a known answer
is a guess.

It encodes the failure that cost a full run earlier: reading "no writes" as a
clean result when the instrument never engaged. A movie without a control PC is
**INCONCLUSIVE**, never clean.

### Working the last blocker: 7,938 → 4,166 (2026-08-04)

With recording under way, the remaining packet blocker — the ≥1k residual, whose
objects had no element count — came down **47%** without touching the priority
set. Three additions:

**Canon extent.** `0x80089938` is a **320-byte** table (64 rows × 5 columns):
`scene_flow_state_table_init` creates 64 records, `scene_config_apply` copies
64×5 in, `serialize_savegame_buffer` copies 64×5 out. 186 sites.

**Third basis — proven index at the same base** (886 sites, 22 clusters,
including the single largest at `0x800892A8` with 486). Where the analyser has
independently proven a non-width-cast bound at a base, that is mechanically
derived evidence of how far code indexes that object. It carries the same
in-bounds assumption as a documented extent — one access indexing ≤N does not
prove the array is only N — so it is counted as its own basis.

**Fourth basis — next object base** (2,652 sites, 161 clusters), *and it needed
constraining*. The naive "nearest distinct base" version was retracted earlier
because its median gap is **4 bytes** (adjacent bases are sibling *fields*).
Clustering bases into objects first fixes that — but unconstrained the clustered
version discharges **100%** of the residual, which is the tautology signature
I have now been caught by four times. Its tight-margin cases (ratio **1.0x**) are
exactly those where *no* neighbour was observed for 12–18 KB, so the "extent" is
a **gap**, not a bound. Accepted only where a real neighbour sits within 1 KB
**and** the required distance exceeds it tenfold.

Both new bases are declared as **one residual each**, not as 22 and 161 separate
"findings" — the same treatment the non-negative-index convention got.

**The packet still rejects on exactly one entry.** And the remaining tail is
genuinely long: 4,166 sites in ~300 clusters, no cluster above ~200 sites, top
ten under 20% cumulative. Closing it cluster-by-cluster is not economic; it needs
another general basis or acceptance as a declared residual.

### Signed-index audit: the recording gate clears (2026-08-04)

The convention residual carried 722 of 851 discharges and was declared
*not assertable* because one site — `0x8005D69C`'s `(short)a3*4` — showed a
negative index is representable. A movie campaign is its declared falsifier, but
only worth recording if that exception is **narrow**.

**On the raw fraction it looked wide.** Of 2,922 accesses discharged this way:
**27.5% signed-capable** (`lh`, `sra`, `subu`, the `sll16/sra16` short cast),
68.1% unknown, only **4.4%** provably non-negative.

**Magnitude inverts it.** No site needs a *small* negative index:

| required negative magnitude | sites |
|---|---|
| **small (< 64)** | **0** |
| medium (64 – 1k) | 47 |
| large (≥ 1k) | 2,875 |

The convention is not being asked to rule out an off-by-one — it is ruling out an
array running hundreds to **thousands** of elements backwards past its own base
(`0x800B0D18` would need index **−1,570**). The true risk set — small negative
index *and* not provably non-negative — is **empty**. My tool's first verdict
("WIDE / not safe / a campaign would not rescue it") used the raw signed fraction
and was wrong.

**The named exception resolved itself:** `0x8005D69C` is based *below* its
target, so it is not among the sites this convention discharges at all.

**The packet now rejects on one entry, not two** — only the ≥1k remainder. 21 of
22 assert non-intersection with evidence and a falsifier.

#### ✅ Clear to record — any%, levels completed

The 47 medium-magnitude sites are the closest thing to risk, and **35 of 47 are
per-frame engine code** (sprite pool, effect render, collision, camera, ground
query, VRAM upload) that runs the moment any level loads. The rest are the
loader, `scene_flow_dispatcher`, `fmv_sequence_completion_check`,
`scene_config_apply` and `serialize_savegame_buffer` — level load, transition,
cutscene and **save** paths.

**Completing each level exercises all of them.** 100% would add only the
gameplay-object bucket (~878 sites), and none of its owners appear in the
medium-magnitude set.

### The extent audit, and E16's `bounded_residuals` packet (2026-08-04)

**Both flagged risks were misplaced, and measuring said so.** The player-block
*extent* (168 B) and the contact object pool each discharge **zero sites** — their
correctness does not affect the result. Of 15 claims, 11 are load-bearing: three
encode *where the next object starts* (weld table → matrix LUT; the registry and
`0x800A649C` → the player block) and eight encode *how far this object reaches*.
Auditing what each claim actually discharges is the work; re-deriving all fifteen
would have been wasted.

**`0x800A6598` re-based off the block length.** Its 20 sites used to rest on
"B06 Canon says the block is 168 B, so it ends at `0x800A65A8`" — the weakest
thing claimed about the block, since the highest *known* field is lives at
`0x800A65A0`, making 168 a lower bound dressed as an upper one. The next
*established* object above the field is E16's own markers 0x58–0x5F table at
`0x800A65B0`, capping it at 24 B — max index 23 against the 24 needed, bounded by
one element. **Nothing in the packet now depends on the 168.**

#### The packet, and what the linter says

Emitted in `phase4_promotion_preflight.py`'s own schema, with its two rules
applied verbatim — `RESIDUAL_MALFORMED` (boundary + evidence + next_experiment
non-empty) and `RESIDUAL_INTERSECTS` (`intersects_dimension` exactly `False`).
**22 entries, every one well-formed. It REJECTS on exactly two**, and those two
are the honest statement of what item 2 still needs:

1. **The non-negative-index convention** — 722 sites. Not assertable as
   non-intersecting while its known exception class (`0x8005D69C`'s **signed**
   short index) is unexamined and only one movie has been run.
2. **The ≥1k remainder** — ~7,900 site-instances in 538 clusters over 33 base
   regions whose element counts have never been read.

Everything else — 20 per-object boundaries plus the now-closed overlay scope —
asserts non-intersection with evidence and a falsification experiment.

⚠️ **The full gate cannot be run here.** The linter also needs packet identity, a
campaign registry with `dimension_claims`, external fixture hash pins,
authoritative paths, a frontier artifact hash and a disposable falsifier — and
that registry lives in the **unmerged** tranche (`151a5a3b`). Only the residual
rules could be applied.

### Overlay census: the scope hole, and the recording plan collapsing (2026-08-04)

**Every prior E16 residual number was resident-only.** `affine_bound_recovery.c`
reads `analysis/functions_resident.txt` — 998 functions, `0x80010000..0x80082508`
— and nothing else. Overlay code had **never** been region-censused, and each
level swaps a different overlay into the same region. The earlier displacement
sweep over the `.BIN` files does not count: it carried the indexed-access blind
spot the affine tool exists to fix.

The tool gained `--raw-base` for flat overlay images; function starts are derived
from `jr ra` boundaries (over-approximating, the safe direction).

**Result: 22 images, 958 region-formed sites, and only 36 need an index < 1k.
Nineteen of twenty-two have zero.** The three that don't reduce to just **two
objects, both already known**:

| image | sites | object |
|---|---|---|
| BITS/MEMORY.BIN | 27 | `0x8009B878` movie unlock array — extent 16 **and** above the window |
| LEVEL08/LEVEL1.BIN | 3 | same array |
| LEVEL09/LEVEL.BIN | 6 | `0x800A6300` — the same registry that was the last open resident cluster |

**The overlay census added no new unknowns.** It converged on the one object
already open.

**`0x800A6300` then closed by layout.** The player state block begins at
`0x800A6500` (B06 Canon, an independently established object), capping the
registry at 512 B — *consistent with* its 467 B proven reach rather than
contradicted by it. Max index 127 at stride 4 against 172 needed.
`level_load_chunks` `0x8005DB24` clears only the **first word**, so there is no
initialiser loop to read a count from; layout is the only available basis.

**Priority set closed again — and the composition is the claim, not the zero.**
851 sites → 7 enumerated-reader + 122 documented-extent + 722 non-negative-index
+ **0 open**, with every bound now surviving the proven-index self-check. 85%
still rests on the weakest basis, and only 2 of 15 extent claims are
independently corroborated.

#### The recording plan collapsed from ~19 movies to zero

The census answered the question the movies were meant to answer: no overlay
contributes an unknown, so there is nothing level-specific left to falsify at
runtime. If a movie campaign is wanted later it is for the non-negative-index
convention's campaign-wide falsifier — and **any% suffices** there. The residual
is dominated by per-frame engine code (222 functions / 8,058 sites) that runs the
moment any level loads; 100% would add only the gameplay-object bucket (~878
sites) and conditional overlay paths.

### Verification round: the retraction was right, its mechanism was not (2026-08-04)

Asked to verify the retraction before moving on, and **two of the three
refutations turned out to be invalid**.

A width mask — `andi 0xff`, `andi 0xffff` — is a C `(char)`/`(short)`
**truncation**, not an array bound. Reading it as one "proved" a 131,070-byte
reach and wrongly refuted the `0x8009FBE8/EA` claims. The bound is still *sound*
for exclusion; it is worthless only as evidence of an object's **size**. The
analyser now flags `width_cast` and the consistency check ignores those ranges.

So the retraction's *conclusion* was right — my evidence was bad — while its
*mechanism* was itself flawed. Both had to be fixed.

**`0x8009FBE8` re-derived from this codebase: 32 × u16 = 64 B**, not 24 × 16 =
384 B. `_SsVmInit` (0x800699F8) loads a literal count of **32** and zero-fills 32
entries of 2 bytes from that base. My original figure came from *"the SPU has 24
voices"* — general knowledge about the **hardware**, which is not evidence about
**this program**. That distinction is the whole lesson of the round.

**`0x800A6300` refutation stands.** `0x8005D69C` reads
`0x800A6300 + (short)a3*4` with a proven, non-width-cast reach of 467 B against
my claimed 164 B. E05 Canon's "41 ids" is the *populated* id range, not the
array's allocated extent — the object is at least 468 B. Claim withdrawn; those
**44 sites are the only ones still open**, and they are open honestly.

#### Extent evidence audit — all fourteen claims

Only **two** are independently corroborated by a proven index at the same base:
the trig table (`andi 0x0fff`, reach 8190 < 8192) and the matrix LUT
(`andi 0x3f`, reach 504 < 512) — both code-evidenced. The other **twelve have no
independent check available in either direction**: four rest on committed Canon,
four on this row's own work, one on an init loop, two on layout adjacency.
Plausible; none cross-checked.

#### The convention, restated as ONE residual

722 line items read like 722 findings. It is **one assumption**, and it now
appears in the packet once:

> **Boundary** — accesses whose region base lies *above* the target window, which
> would need a **negative index** to reach it.
> **Evidence** — `region_provenance.c` TIER 2's disclosed convention; 526 of the
> 722 have no corroborating proven index.
> **Known exception class** — `0x8005D69C` computes `0x800A6300 + (short)a3*4`, a
> **signed** short index, so a negative index is representable there. Signed-index
> sites are exactly where this convention could fail.
> **Next experiment** — watch all three windows across a full *campaign*, not one
> level. One run already passed (7 PCs, none from above the window).
> **`intersects_dimension`** — *not yet assertable as false.*

### ⚠️ RETRACTED same day: the priority set is NOT closed (2026-08-04)

**I claimed "the entire priority set is closed, 0 open". That was wrong.**
Verification found **three of fifteen claimed object extents refuted by the code
itself** — the analyser proves an index at that same base reaching further than
the extent I cited:

| base | claimed | proven reach | source of the claim |
|---|---|---|---|
| `0x8009FBE8` | 384 B | **131,070 B** | *"the SPU has 24 voices"* — general knowledge imported from outside this codebase |
| `0x8009FBEA` | 382 B | 131,070 B | same |
| `0x800A6300` | 164 B | 467 B | E05 Canon's 41-entry registry |

A refuted claim gives **no upper bound at all**, so it discharges nothing. That
reopens **44 sites**.

**Corrected:** 851 priority site-instances → 7 enumerated-reader + **78**
documented-extent + 722 non-negative-index + **44 open**.

The self-check is now a **hard gate inside the tool**: every claimed extent is
tested against the largest index the analyser can prove at that base, and a
refuted claim is downgraded automatically. It cannot be asserted past again.

**And the weight each basis carries, which the headline hid:** 722 of the 807
discharges (**89%**) rest on the **non-negative-index convention**, and 526 of
those rest purely on it with no corroborating proven index at the base. Only
**78** rest on a documented extent that survives the self-check. B06 used the
same convention for **6 of its 165** exclusions — same disclosed basis,
completely different load-bearing weight.

### The priority set, worked (2026-08-04)

**Every access with any plausible path to any of E16's three tables is now
bounded.** 851 priority site-instances (those needing an index < 1k) →
**7 enumerated-reader + 122 documented-extent + 722 non-negative-index + 0 open.**

What remains of the residual — 2,081 / 2,081 / 3,776 — consists *entirely* of
accesses needing indices ≥ 1k against objects demonstrably far smaller.

**The `slti $s2,128` lead was refuted, not promoted.** It guards a *different*
table at `0x800992A8` (`lui 0x8009` / `addiu -27992`, stride 4). The real gate on
the `0x8009B2A8` accesses is `slt $s2, gp[1280]` — a runtime count at
`0x80082298`, appended by `chunk_pointer_relocate_index_fixup` in a loop bounded
only by a `u16` header field, so **code gives no useful bound**. Layout does: the
next object is the matrix LUT at `0x8009B3A8`, whose 64×8 extent is
*independently* established from `andi 0x3f`, capping this table at 0x100 =
128 × u16 — max index 127 against the 384 needed.

That is the second time a plausible nearby constant nearly became evidence.

**Confirmed on the way:** the 836-byte record size, read straight off
`table_836byte_record_populate`'s prologue (`a0*3 → *12 → *13 → *208 → *209`, ×4).
Its element *count* is still unknown, so its fields stay open — but they need
index ≥ 401 anyway, outside the priority set.

**Three more bound-compiler bugs**, all found by chasing a site that should have
closed and didn't:

1. `hi` is **exclusive**, so a base sitting exactly *at* `hi` is already above the
   window and needs a negative index — `base > hi` had to become `base >= hi`.
2. A **duplicate `KNOWN_OBJECTS` key** silently kept the older `extent=None` entry
   (Python takes the last), leaving 10 already-bounded sites open. Invisible in
   review; now gated.
3. Earlier: highest valid index is `(extent/stride) − 1`, and a field at
   `base+delta` has only `extent − delta` bytes above it.

Every one of these *under*-discharged — conservative, but wrong.

### The priority worklist, worked (2026-08-04)

The 67 sites needing an index < 1k were the only ones with any plausible path to
the window, so they were the unit of work. **For the 0x30–0x57 table they are down
to 9 open**: 3 enumerated-reader, 14 bounded by a documented object extent, 44
bounded by the non-negative-index convention. Across all three tables, 851
priority site-instances → 7 / 100 / 701 / **43 open**.

The 61 distinct bases turned out to be about **ten real objects seen at many
field offsets** — which is why naming them collapsed the list so far.

**The two discharge bases are kept apart, and must stay apart.**
`BOUNDED_DOCUMENTED_EXTENT` rests on a cited element count.
`BOUNDED_NEGATIVE_INDEX` rests on the convention that array indices are
non-negative — the same assumption TIER 2 discloses — and applies to bases
sitting *above* the window. 2,689 of the 0x30–0x57 discharges are the weaker
kind, and merging the two would inflate the stronger basis with it.

**The tightest boundary in the set**, evidenced twice over: the matrix LUT at
`0x8009B3A8`. `matrix_lut_mesh_transform` masks its index with `andi 0x3f`
(max 63), and the layout corroborates it exactly — `0x8009B3A8 + 64*8 =
0x8009B5A8`, precisely where E16's markers table begins. Bounded by *one element*.

**A false alarm, checked and killed.** I suspected the 0x58–0x5F window
(`0x800A65B0`) overlapped E14's 64×5 side-HP table, because my own memory index
reads `id*5+[0x800A6597]` as though `0x800A6597` were the base. Canon is explicit:
the table is at `0x80089938` and `0x800A6597` is the berry-marker **column
selector** (0..4). No overlap. Check Canon, not a compressed index line.

**A lead recorded but not counted.** `chunk_mesh_weld_converter` contains
`slti $s2,128`, which *would* bound the `0x8009B2A8` accesses below the 384
needed — but nothing verifies `$s2` is the index feeding those accesses.
Assuming it does is exactly the error that made TIER 3 unsound. Left open.

Two tool bugs fixed, both of which *under*-discharged (conservative but wrong):
the highest valid index is `(extent/stride) − 1`, which mattered at exactly the
LUT boundary; and a field at `object_base + delta` has only `extent − delta`
bytes of object above it.

## C05 Three success tokens - confirmed / bounded-exhausted (2026-08-04)

C05 is closed within its named scope. Pristine-ASM C analysis ties the three success
conditions to bits `0x01` (50 grain), `0x02` (FLIK mask `0x0F`), and `0x04` (zero enemies
remaining); their union is the persisted full mask `0x07` consumed by the bonus-movie
path. Marker production, results setters, counter behavior, newly-earned save trigger,
serialization/deserialization, and the movie consumer are all pinned.

The six focused C verifiers pass 25/25, 47/47, 21/21, 30/30, 46/46, and 20/20 pins. The
combined `tools/phase4_c05_closure_oracle.c` additionally reports
`C05_CLOSURE PASS`, including unique save-trigger loading and one call in each persistence
direction. No relevant retained capsule exists, but static executable/overlay domains
fully answer closure; an Interpreter movie is not required. Remaining save-frontend,
overlay-loader, and mutable-tail popcount-table questions are explicitly owned outside
C05 and do not weaken its token/unlock contract. Full evidence is in
`ObsidianVault/Experiments/EXP_2026-08-03_phase4_c05_three_tokens.md` and
`analysis/phase4_c05_three_tokens.json`.

## C03 FLIK letters - lifecycle writer attributed (2026-08-04)

**Status: CONFIRMED; BOUNDED EXHAUSTED.** The v4 Interpreter 100% LEVEL06
fixture was replayed from its hash-pinned state with write attribution and the four pickup
handlers armed. It naturally produced I/K/L/F mask transitions and completed at `0x0F`.
Because lives were already 9, the fourth letter executed the pristine cap check and skipped
the increment store. The completed mask then survived results, the post-level cutscene, and
the Journey hub with no further writes.

The previously missing reset is now exact. Runtime registers identify a zero-fill of
`0x800A6500` for `0xA8` bytes, called at `0x80046B68`; BIOS PC `0xBFC02BB0` performs the
observed mask `0x03 -> 0x00` write. Pristine ASM in `fcn.80046b20` saves lives from `+0xA0`
before that clear and restores them at `0x80046C00`, while the FLIK mask at `+0xA2` remains
cleared. This is the gameplay/player initializer and explains why direct-store censuses
missed the lifecycle reset.

The requested combined fixture is now retained and closes both former residuals. Starting
at five lives, natural L/K/F/I collection completes the mask and I's `0x800540B0` store
increments lives `5 -> 6`. The continuous route then reaches the next gameplay initializer:
the same `0x80046B68` zero-fill clears mask `0x0F -> 0`, and `0x80046C00` restores lives
to 6. The movie is v4 Interpreter, reproducible, untruncated, and ran at normal speed with
watches armed at frame 0. No C03 movie or promoted domain remains. Evidence:
[[EXP_2026-08-03_phase4_c03_flik_letters]] and [[SYS_flik_letters]].

## E08 object catalog - campaign census complete (2026-08-04)

**Status: the row's named `next` is DONE; the rest of E08 is a different kind
of work.** A compiled C walker (`-Werror`, self-verifying) reproduces the
retail DAT parser and derives every table's base **per file** — top-level
records → trailing advance → pass 1 → pass 2 → pass 3 — across all **21**
`LEVEL*.DAT`. Every file parses and all eight cross-checks against
independently committed facts pass.

Totals: 1,058 type-0x3F contact objects, **9,097 pass-1 prop instances**,
1,684 pass-3 cull anchors, pass-2 non-empty in only 6 files.

Four campaign-level findings the per-level view could not produce:

- **The contact-object kind domain is closed for placement data** — zero
  unknown kinds anywhere (774 grain, 29 telescopes, 39 kind-0x31, berries
  3/11/16/2, seed tokens across 0x29–0x2D).
- **Every pass-1 payload pointer is unique and non-null** (9,097 = 9,097), so
  prop *models* are per-instance baked blobs with no shared library even though
  *placement* is data-driven.
- **A documented parser path is dead in retail data**: the `flags & 0x20`
  conditional relocation is set on **zero** records, while bit-3 payload-path
  selection is used heavily. A mod using bit 5 exercises untested code.
- **FLIK letter sets are always complete** — F/L/I/K each exactly 18
  campaign-wide, never partial.

It also independently reproduces E11's committed Bug Bar figure (pass-2 = 10
entries, 10 non-null) from an unrelated parser, and corrects
`prop_decor_catalog.c`'s loose "500+" LEVEL01 pass-1 count to the exact **484**.

Two parser facts, each of which broke a first attempt and are worth carrying:
the **pass-2 count is signed** (LEVEL01's `0xFFFFFFFF` = empty pass-2 whose
sentinel is that word — the reason pass-3 starts at 0x3AEC), and the
**type-0x3F kind byte is at entry +0x0C**.

Gate: `tests/test_phase4_e08_object_census.py` (8 tests). Remaining row scope —
interaction rules, authored state, persistence/reset — is behavioural work a
placement census cannot reach. See [[EXP_2026-08-04_phase4_e08_object_census]].

## D18/F09 Thud fight law - all residuals closed (2026-08-04)

**Status: D18 BOUNDED EXHAUSTED with every named residual closed.** The
operator recorded the Thud fight on Interpreter
(`movies/Phase4/Interpreter/D18_thud_fight.movie.json`, from-boot v4, 15,600
frames, boot → Bug Bar → defeat), which made the fight traceable for the first
time. Every writer below is an attributed PC:

| step | writer | effect |
|---|---|---|
| spawn | `0x80049CA0` | pool HP := 50 at load |
| hit | `0x800590E4` (inside committed `berry_tough_damage_dispatch`) | 50 → 48 |
| restore | `0x800B3ED0` (overlay) | 48 → 50, two frames later |
| count | `0x800B3DB0` (overlay) | `0x800B4CC8` += 1 |
| kill | `0x800B4528` (overlay) | HP := 0 at count 8 → generic retirement |

Three consequences. **The pool HP field is a hit LATCH, not health** — the
overlay restores it after every hit, so anything reading `+0x6E` for this boss
reads a flag. **The real counter is `0x800B4CC8`**, running 0→8 with the kill
gated on 8, which finally gives the long-standing "8 perched berry hits" claim
a mechanism instead of an observational count. **The damage itself is
ordinary** — the boss takes the same berry law as any enemy; only the
bookkeeping is special.

The mover-VM stayed parked for the entire fight (1,644 IP writes, all by the
interpreter's own store), confirming the 2026-08-03 FSM-negative on real fight
data rather than a poll-only replay. **Correction:** `+0x7C` `0x8004A0F4` is
`thumper_driver_cb`, byte-matched C whose whole body is
`play_sound(26, actor position)` — a positional **sound cue**, not the
"per-actor driver callback" the rows implied.

**The "perched" qualifier is now decoded too.** The 15-vs-8 gap is a
**position equality test**: the overlay requires the sweep word
`[0x800B4CB0]` to equal exactly **−168416** or **+159264** — Thud's two perch
anchors — so only hits landed while he is stopped at an endpoint score. The
committed "8 perched berry hits" wording was literally accurate. The handler
lives in **LEVEL04/LEVEL1.BIN (4,924 B, load base 0x800B39A0)**, derived from
the counter-store encoding by `tools/phase4_d18_overlay_gate.c` and
re-confirmed against a second known PC — which also promotes the committed
overlay claim from assertion to measurement. Breakpointing the predicate's own
test instruction caught **15 evaluations, exactly 8 at an anchor**, and those 8
are the increments. Note the ordering: hurt **sound 93** and the hurt
**animation** fire for *every* hit, so the player sees each berry connect —
only the scoring is gated, which is why the fight reads as "some hits don't
register". Modding lever: the target literal `8` at `0x800B3DA4`, or the
anchors — never pool HP.

**Damage response, mapped by poke A/B from one anchor state:** ≤29 delta
(HP≥21) counts and restores; **30–49 (HP 1–20) is IGNORED and the HP is never
restored, so the fight SOFT-LOCKS** — verified by holding HP at 5 for 720
frames with the counter unmoved and three further hits all ignored; ≥50 (HP≤0)
retires instantly, bypassing the counter. The threshold matches the decoded
`slti 21` exactly. This means **boosting berry power past a 29 delta breaks the
fight rather than shortening it** — a genuinely counter-intuitive modding
result. Proven: the response to such a delta. NOT proven: that a real berry
delivers one (canon puts mega at 45, but the movie only produced −2 and −4, and
whether the dispatch passes full power to a berry-tough boss is untested).

**And the burst collapse has a mechanism:** three rapid hits from a fresh
anchor produced one count because the first hit **sends Thud sweeping** (gate
word −168416 → −153056 → −137696 → −122336), so the rest evaluate mid-sweep.
It is a state change, not the refractory timer the frame spacing suggested.
The committed HP≤0 retirement rule was re-checked and stands.

F09's remainder is now only E11's arena visible-index mapping, and this
fixture serves it. Gate: `tests/test_phase4_d18_fight.py` (15 tests). See
[[EXP_2026-08-04_phase4_d18_thud_fight_law]].

## D18 Thud VM FSM - resolved by falsification (2026-08-03)

**Status: D18 bounded-exhausted; F09's shared item closed.** The rows' shared
next ("decode the mover-VM program at 0x800777A6 for Thud's phase/attack FSM")
rested on a mis-transcription: 0x800777A6 is not a program entry — the
committed 40-entry table has none there — it is the `jump_back` inside program
#19 (0x80077798, parked idle), recorded by phase3_thud.json as Thud's LIVE VM
IP. The FSM itself does not exist: poll-only replay of the operator's full
fight movie (4113 frames, CachedInterpreter-era, never armed) shows the IP
never leaves the park loop — through a landed hit (a transient 50→48→50
pool-HP dip matching the committed −2-per-hit law, restored by the fight
lane) and through the terminal HP=0 write that retires the actor via the
generic path. Instrumented idle runs show the VM interpreter (0x8004C834) as
the sole +0x70 writer; defeat pokes produce no death-program switch;
proximity produces nothing. The surrounding 0x800777xx block is a shared
ambient bank — parked / stationary two-clip cycle / gated wander / wander /
authored-path patrol, each behaviorally poke-verified, used by ids 21, 7, 15,
22, 18 across census anchors.

A correction landed same-session: an initial "pool HP never changes during
the movie" summary was wrong — the test gate's assert against the saved
timeline caught the 48 and 0 samples, and the corrected reading strengthens
the verdict. Remaining scope (D18's and F09's, shared with E11): one
re-recorded Interpreter fight movie closes the fight-lane HP writer
attribution, the driver callback 0x8004A0F4's role, and the arena mapping.
Gate: `tests/test_phase4_d18.py` (5 tests; offline sections regenerate via
`tools/phase4_d18_thud_vm_fsm.py --check`). See [[SYS_thud_bug_bar_boss]] ·
[[EXP_2026-08-03_phase4_d18_thud_vm_fsm]].

## E03 render ordering and packets - bounded exhaustion (2026-08-03)

**Status: partial, named high-value scope closed; move on.** The row's `next`
(one frame's OT chain per scene class; classify packet families and emitters)
closed with a DOUBLE IMPLEMENTATION: a compiled C linked-list walker over
mid-frame RAM dumps agrees exactly with gp0Trace's dispatch-time stream on all
three 3D scene classes (492/492 gameplay, 712/712 boss, 749/749 training) —
the region_provenance.c second-implementation pattern, per operator direction.

Mechanism established: each rendered frame (30 fps, re-confirmed) presents a
SEQUENCE of linked-list DMA kicks through one helper call site (0x80064F28,
list head in a1) — a 7-command env preamble list at buffer+0x1C (own
terminator; an initial "env linked into body at present" reading was
RETRACTED, falsified at the kick-1 halt), then the depth-bucket body chain at
buffer+0x14E0 over a 1228-entry bucket table (invariant across scenes; earlier
1025/1214 figures were head-derivation artifacts), then scene-dependent
auxiliary lists (scratchpad/stack-built, zero GP0 draws observed). Double
buffering is lockstep ([0x8008240C] ↔ displayed VRAM rect x0/x512), per-frame
OT re-init has one owner (frame_present 0x80039A70, sole writer of the
primitive cursor and bucket base), packets are fully rebuilt every frame (the
sole recurring DMA source is the 4-command static node 0x8007FC84), and each
buffer's OT is reset right after its present — the full chain exists only
mid-frame. Families are quantified per scene class with an emitter roster from
a 4-byte cursor write-watch (payload emitter 0x80010000, dirt_mesh_builder,
billboard renderer, HUD glyphs, ot_depth_fade_postprocess; gameplay/boss add
0x800172DC + 0x8002D674; training routes skinned meshes through
bone_matrix_array_mesh_transform). Transparency is fully accounted: every
semitrans prim is a textured poly; additive B+F dominates, B-F secondary,
averages only in E1 defaults — mode sums equal the semitrans totals exactly.
The FMV regime is polygon-free: 20 MMIO strip blits (128×24) + 20 clear_caches
per frame, 24bpp display, vertical buffer flip, OT pointer never toggles.

Gate: `tests/test_phase4_e03.py` (8 tests). Explicit residuals: the sibling
present call 0x80062C54, auxiliary-list content, and the descriptor
tpage/CLUT writer (needs a level-transition fixture; descriptor row's item).
See [[SYS_render_ot_and_present]] · [[EXP_2026-08-03_phase4_e03_ot_packet_census]].

## E05 actor models and animation - bounded exhaustion (2026-08-03)

**Status: partial, named high-value scope closed; move on.** The row's `next`
("dump actor model pointers per chunk-31 type; build the type→model table")
dissolved once the mechanism was located: the binding is **code, not data**.
`level_load_chunks` (0x8005DAD0) walks the actor pool 0x8009FD80 (64×0x84) and
dispatches each record id (1..41) through the jr table at 0x8001BBDC, whose
case bodies hardcode the model path and id; `level_chunk_loader` (0x8005D654)
persists each pointer at **0x800A6300 + 4*id** under a first-load guard. The
full 41-entry id→path table was decoded statically from the pristine EXE
(`analysis/phase4_e05_model_binding_static.json`, zero inconsistencies, case
targets equal to the committed phase-3 jr decode, all 17 committed D01 species
matching their paths), and confirmed live on **16/16 level saves** with an
exactness result: the registry's non-null set is precisely {Flik slot 0} ∪
{pool ids} ∪ {plant slots} per level
(`analysis/phase4_e05_model_pointers_live.json`).

Unifications and corrections along the way: the Canon plant model table
0x800A649C+4N is slots 104..117 of the same registry (second dispatch
0x8005E2AC, jr 0x8001BC84, a3=103+N); Flik's model is scene-keyed via
[0x80082504] with the four variant paths decoded and grounded to live scene
words (cliffside=6 corroborates C15); the skeleton bank's true base is
0x80089F58 (memset 300×84 at level load), reconciling MEM_8008A1F8 with the
grammar page; the row's old "actor skinned update 0x800563D4" binding is
corrected to the per-frame player animation selector; and **id 11 is the seed
actor** (`bits\seed`, dedicated loader 0x8005D924), correcting D01's "ambient
critter" working name while preserving its structural non-enemy finding. The
12 static-named 0x80049Axx anim setters resolved to the per-species death-anim
jr table 0x8001B1D4 inside enemy_update_deathanim — committed phase-3 data,
previously uncross-linked.

Gate: `tests/test_phase4_e05.py` (7 tests — EXE pin, table completeness,
plant-window arithmetic, species joins, regeneration determinism, 16/16 live
exactness by set arithmetic, scene-word cross-checks). Explicit residual:
the second per-id registry 0x800A2188 (equals the model pointer where non-null;
null for the seed everywhere and for Flik on scenes {4,5,7,9,12}; writer
unattributed — named probe: write-watch across one Interpreter-mode level
load). See [[SYS_actor_model_loading]] ·
[[EXP_2026-08-03_phase4_e05_actor_model_binding]].

## A12 seed color change - high-value bounded exhaustion (2026-08-03)

**Status: partial, reusable row-specific work exhausted; move on.** A hash-valid
1,359-boundary pristine capsule first established the selected seed and source-record
anchor without live replay. Compiled C analysis of pristine SCUS_942.88 then recovered
the complete resident Triangle path at 0x800473B0 and rejected the earlier unchanged
0x800822A4/0x80094C76 candidates.

The action requires selected offset 0x800A655C > 0 and a fresh Triangle edge
(0x1000 in current pad 0x80082488, absent from previous pad 0x80082380). It resolves
the selected actor's source through actor+0x80, writes color at source+0x0E, arms
source+0x18 to 16, calls sound cue 30+color, and dispatches color presentation through
0x800577DC. Unlock order is a four-nibble runtime word at 0x800B0196, populated on the
first pickups of token kinds 0x2A..0x2D. The five-value domain is brown, blue, green,
purple, and orange/yellow. A selected seed with an empty unlock word still produces
feedback but remains brown; no selected seed rejects the action before that work.

An isolated pristine runtime control replayed the pinned CachedInterpreter movie at
normal speed to movie frame 622 without instrumentation. Runtime-only unlock pack
0x4321 produced 0->1->2->3->4->0, holding Triangle did not repeat, an empty pack kept
color 0 while arming the timer, selected=0 denied the handler, and source+0x0F=3 forced
color 3. Every case reloaded the same /tmp anchor; no disc, asset, executable, movie, or
repository fixture was mutated.

An adversarial follow-up removes two remaining doubts. A compiled C census parses all
21 pristine LEVEL*.DAT resources and finds token-kind 0x29..0x2D totals
[18,25,36,26,7]. Across all 24 LEVEL*.RAW resources, all 130 id-11 seeds have color
0..4 and satisfy source+0x0E == (source+0x0F & 0x0F); all 20 stage overlays contain
zero direct sb +0x0E writers. A second normal-speed control at the fixed/mounted
selection epoch (offset 0x0108, actor 0x8009FE88, source 0x80094A70) changes color
0->1, confirming the law is selection-gated rather than carry-mode-gated.

| # | Closure metric | State | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | Genuine carried and fixed/mounted selected-seed anchors plus causal Triangle controls; no naturally collected colored-token movie |
| 2 | Complete frontier | met | Input gates, both source+0x0E writers, unlock producers/reset, audio call, VFX call, and reinit reset decoded |
| 3 | Typed state | met | Selection, actor source pointer, current/default color, timer, pad edge, unlock order, cue and RGB domain typed |
| 4 | Lifecycle | advanced | First-token insertion, cycling, hold denial, brown wrap, carried and fixed/mounted selection, source persistence, and actor-reinit reset covered; scene reload not replayed |
| 5 | Original interfaces | advanced | Controller, source record, token pickups, SFX, world presentation, actor reinit, and HUD availability list bound |
| 6 | Campaign breadth | bounded | All 21 DATs, 24 RAWs, and 20 overlays censused in C; exhaustive natural per-stage execution remains low return |
| 7 | Cross-system | advanced | Token pickup -> unlock order -> selected actor/source -> color/VFX/SFX -> later plant-output chain bound |
| 8 | Source closure | met | Semantic C reconstruction plus compiled pristine scanner and capsule reducer |
| 9 | Durable evidence | advanced | Source movie/state, capsule, executable, emulator, C tools, runtime transcript, and temporary anchor hash-pinned |

Do not spend a standalone iteration on every-stage token collection, pixel-exact effect
timing, SPU waveform identity, or compiler matching. Request an Interpreter movie only
if one of those named residuals becomes a direct dependency. Evidence:
[[SYS_seed_color_change]], [[EXP_2026-08-03_phase4_a12_seed_color_change]],
analysis/phase4_a12_seed_color_change.json, src_re/seed_color_change_800473b0.c,
tools/phase4_a12_static.c, tools/phase4_a12_capsule.c,
tools/phase4_a12_adversarial.c, and analysis/phase4_a12_campaign_census.json.

## A11 seed as weapon - retained-fixture bounded exhaustion (2026-08-03)

**Status: `partial`, high-value row-specific work exhausted; move on.** A validated
462-boundary pristine capsule plus compiled C reconstruction proves Square release,
ballistic travel, id-9 spider contact, seed deflection/settling, and target unlink. The
target's HP stays `2` during the reaction: contact kind `4` writes lifecycle/knockback
`+0x6C=-20`, which advances to zero before a temporary terminal unlink. Actor ID is
preserved, so this is an HP-bypassing temporary KO rather than direct damage or a
permanent kill. The seed remains live and reusable.

Compiled C scanning of the hash-pinned pristine executable finds exactly two resident
`-20 -> actor+0x6C` writers. Passive flow selects `0x80058E14/18`; the static twin at
`0x8004B2CC/D0` is not executed. Eligibility is a reusable contact/flag predicate, not
an ID switch. The hit initializes reaction `+0x54/+0x58=4096`, enters the eight-object
impact burst, and dispatches cue `17`; it has no HP or animation-ID store.

| # | Closure metric | State | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | Natural positive and retained no-press negative |
| 2 | Complete frontier | advanced | Both writers, executed arm, guards, reaction, and terminal interface decoded |
| 3 | Typed state | met | Carry, seed motion/liveness, target flags/reaction/HP/permanence typed |
| 4 | Lifecycle | advanced | Pickup through unlink covered; later shared respawn deferred |
| 5 | Original interfaces | advanced | Input, seed physics, contact, VFX/SFX, and retirement bound |
| 6 | Campaign breadth | deferred | Id-9 spider plus generic predicate; exhaustive enemy-family execution is low return |
| 7 | Cross-system | advanced | Controller-to-seed-to-contact-to-enemy-lifecycle chain confirmed |
| 8 | Source closure | met | Semantic C, capsule reducer, and pristine-ASM scanner |
| 9 | Durable evidence | advanced | Capsule/movie/state hashes, preservation manifest, Canon, Experiment, and analysis artifact |

No new Interpreter movie or cold boot is required. Revisit only for a named enemy
family, the alternate collision subtype, exact rendered pose timing, or post-KO
respawn. Evidence: [[SYS_seed_as_weapon]],
[[EXP_2026-08-03_phase4_a11_seed_as_weapon]],
`analysis/phase4_a11_seed_as_weapon.json`, and
`analysis/phase4_a10_a11_capsule_preservation.json`.

## A05 abdomen bounce - high-value bounded exhaustion (2026-08-03)

**Status: `partial`, high-value row-specific work exhausted; move on.** The relevant
D10 Bonus-1 capsule was validated and queried before considering live DuckStation. Its
3,654 frame records pass all 10,962 RAM/VRAM/SPU hash checks, passive flow covers
145,850,969 instructions, and its natural movie contains five qualifying Training
spider contacts. No A05-specific live replay, cold boot, or new Interpreter movie is
required for the covered questions.

C analysis against pristine `SCUS_942.88` corrects two stale assumptions. There is no
native <=20-frame double-tap counter: that window belongs to the Phase-2 offline movie
recognizer. The player controller instead admits a Cross-active second airborne action
from state 2. Below an `0x2001` floor gap it selects state 3; at or above that gap it
sets phase 10 and state 4. Phase values above 1 hold vertical speed at zero and count
down; phase 1 writes `vy=+4096` and remains latched through contact.

The actor-contact resolver proves the spider qualification is player phase `1`, not a
separate interaction-record field. It applies a sphere plus model-ellipsoid contact
test, rejects actor flags `0x20/0x40/0x80/0x800`, writes actor reaction fields
`+0x6C=-20`, `+0x54/+0x58=4096`, and calls the eight-object drop burst. It does not
write target HP. Phase 0 takes a separate `vy=-1536`, state-5 rebound; phase 1 reaches
the Bonus-1 streak. The streak has no miss reset or uniqueness list. The fifth accepted
contact sets flag `0x02`, latch 6, fade 30, and clears the streak.

| # | Closure metric | State | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | Five natural contacts and threshold handoff are retained in a hash-valid pristine capsule; no dedicated pause/death negative movie |
| 2 | Complete frontier | advanced | Player admission/phase/recovery and decisive actor-contact/counter slices decoded; repository-wide pointer-alias absence remains deferred |
| 3 | Typed state | met | Player Y/floor/vy/state/ground/phase/timer/animation, actor collision/reaction/HP, and streak/flags/latch/fade fields typed |
| 4 | Lifecycle | advanced | Entry, high-dive dwell, terminal fall, phase-0 rebound, phase-1 contact, floor recovery, miss persistence, success reset and scene handoff covered; pause/save/death interruption omitted |
| 5 | Original interfaces | advanced | Controller, movement integrator, actor contact volume, reaction burst, animation selector, bonus flags and transition interface bound |
| 6 | Campaign breadth | deferred | Natural Training-spider route plus resident all-stage player code; exhaustive non-Training actor/terrain execution is low return |
| 7 | Cross-system | advanced | Input -> player physics -> actor geometry/reaction -> challenge counter -> frontend transition chain confirmed |
| 8 | Source closure | met | Documentation-grade semantic C, pristine-ASM C gate, two compiled C capsule reducers, and byte-exact executable input |
| 9 | Durable evidence | advanced | Existing capsule, movie/state hashes, scenario and A05 evidence manifest are regenerable; no standalone whole-campaign A05 oracle gate |

Do not spend a standalone iteration on repeated stages, exhaustive actor-flag census,
every terrain presentation, or pause/save/death breadth. Revisit only for a direct MOD
dependency or a promoted alternate-contact question. Evidence:
[[SYS_abdomen_bounce]], [[EXP_2026-08-03_phase4_a05_abdomen_bounce]],
`analysis/phase4_a05_abdomen_bounce.json`,
`src_re/abdomen_bounce_80048138_8004abf4.c`, and
`tools/phase4_a05_static.c`.

## D19 Molt boss - high-value bounded exhaustion (2026-08-03)

**Status: `partial`, high-value row-specific work exhausted; move on.** The replacement v4 Interpreter movie replays from its pinned state at normal speed with `reproducible:true`. Clean and heavily armed runs both end at emulator frame 15651/cycle 8861074013 on the level-complete screen, with byte-identical sampled actor, player, overlay, transition, and screenshot domains.

C static-ASM analysis corrects the old asset and actor hypotheses. Molt is live actor ID 29 at `0x8009FF90`, HP `+0x6E`, initial HP 50, flags `0x5043`, VM IP `0x80077688` (`park_seek`), and callback `0x8004A0A0`. The live secondary fight overlay is `LEVEL03/LEVEL1.BIN`, not the initially assumed `LEVEL09/LEVEL.BIN`. Its guarded-hit restore word is singular across all 19 overlay bins at `0x800B3CC4`.

The shared resident writer `0x800590E4` proposes class-0 damage of 2. The overlay restores the last accepted HP when actor `+0x44 == 1` or the goal latch is already set. The movie has 43 proposed Molt stores, 15 accepted descents from 50 to 20, and 28 rollbacks. Crowd code at `0x800B43F8` allocates type-71 contacts; 31 of 141 non-truncated allocator events have its exact return address `0x800B4400`. Accepted HP below 21 sets `0x800823A0=1` and `0x80082470=150`, producing level completion.

| Closure metric | State | Evidence/boundary |
|---|---|---|
| 1 | Behavior core | advanced | Park/seek pursuit, guard rollback, crowd throw, HP acceptance, and victory handoff bound |
| 2 | Semantic frontier | advanced | Exact actor fields, resident writers, overlay gates, globals, VM opcode, and allocator producer decoded in C |
| 3 | Variants/capacity | bounded | Four crowd origins and 31 natural type-71 allocations covered; exhaustive RNG distribution deferred |
| 4 | Lifecycle | advanced | HP init 50, accepted/rejected hits, threshold 20, latched post-hit rejection, and level-complete transition covered |
| 5 | Original interfaces | advanced | Mover VM, shared damage dispatcher, actor-state setter, contact allocator, SFX/event, and transition globals bound |
| 6 | Campaign breadth | bounded | Full pristine Stage-12 fight; alternate death/restart attempts omitted as low-return |
| 7 | Cross-system | advanced | Crowd/contact pool -> resident damage -> overlay acceptance -> frontend transition chain confirmed |
| 8 | Source closure | met | Documentation-grade semantic C, C corpus/static reducer, runtime reducer, and byte-exact retained ASM inputs |
| 9 | Durable evidence | advanced | Movie/state and raw RPC evidence hash-pinned; no reusable D19 capsule or whole-campaign oracle gate |

Do not spend a standalone iteration on exhaustive crowd RNG, pixel/animation/audio timing, alternate attempt breadth, or compiler matching. Revisit only for a direct MOD/shared-system dependency. No new Interpreter movie or cold boot is required because the completed work changed no disc, code, or asset. Evidence: [[SYS_molt_boss]], [[EXP_2026-08-03_phase4_d19_molt]], `analysis/phase4_d19_molt.json`, and `config/phase4_d19_molt.yaml`.

## E10 environmental hazards - retained-fixture bounded partial (2026-08-02)

E10 advances from unresolved to **substantiated partial**. Seven validated v3
capsules provide 2,804 frame records and 8,412 successful RAM/VRAM/SPU hash
checks with zero mismatches. C reconstruction and C static-ASM analysis separate
three ordinary-damage producers from pit death:

- Rolling acorn uses actor contact at 0x8004B4A0.
- Falling rocks and falling spikes use the contact-object walker at 0x80058A48.
- Poison goo uses the player/world collision branch at 0x80049740.
- All four converge on one-point damage at 0x8004A700; zero health remains alive,
  negative health enters death, and nonfatal damage arms a +45 gameplay-update timer.
- Pits in three levels bypass health depletion and converge on the 0x8005B134
  safe-anchor restore, health reset, byte-sized lives decrement, and collision reset.

Ground bird is credited to D17 and was left untouched. Webs, the campaign-wide
instant-kill-region census, remaining lifecycle/cross-system work, and source
closure keep the strict row partial. No new Interpreter movie is required for the
covered fixtures; request one only for a promoted missing family or named
every-cycle attribution. Never arm tracing on the retained CachedInterpreter
source movies. Evidence: [[EXP_2026-08-02_phase4_e10_hazards]] and
[[SYS_environmental_hazards]].

## Purpose

Run evidence-backed subsystem campaigns until every row in
[[Whole-Game Mechanics Baseline]] satisfies the roadmap's strict Definition of Done.
Berries and seeds are ordinary campaigns in this phase, not privileged roadmap phases.

## Campaign families

1. **Input and player actions:** run, slow walk, turn, jump, kick, abdomen bounce,
   slide, spin, berry throw, seed manipulation, swinging, and manual camera input.
2. **Player lifecycle:** health, damage, invulnerability, shields, powers, death,
   safe respawn-anchor selection/restoration, lives, game over, and continue. Retail
   has no player-activated checkpoint mechanic; do not infer one from telescope kind `0x30`.
3. **Movement/world physics:** gravity, slopes, ledges, floors, walls, hazards, movers,
   air states, collision response, and camera collision.
4. **Rendering/camera/animation:** world and actor submission, ordering tables,
   double buffering, materials, effects, model/animation state, normal and special
   camera modes.
5. **Seeds/plants/traversal powers:** every color/tier, carry/mount/plant/uproot cycle,
   mushroom, propeller, dandelion, cannon, leaf platforms, temporary powers, shooters,
   mine, and combinations.
6. **Collectibles/equipment/rewards:** grain, FLIK letters, health leaves, berry pickups,
   seed tokens, telescopes, grain harvester, success tokens, medals, unlocks, and bonus
   entries.
7. **Objects/events/hazards:** contacts, pickups, props, gates, switches, movers,
   dynamic geometry, scripted actors, event VM, objectives, and environmental hazards.
8. **Enemies/combat:** every regular enemy family/variant, AI, attacks, immunities,
   damage, death, drops, respawn, permanent kills, and quotas.
9. **Bosses/special objectives:** Thumper, Bird, Thud, Molt, Hopper, flight/chase,
   rolling arena, bird assembly, companion rescue, and finale mechanics.
10. **HUD/frontend/persistence:** status, pause, results, menus, options, control remap,
    save/load, continue, game over, movie viewer, and unlock persistence.
11. **Audio/cinematics:** SFX event map, voices, XA/music selection, FMV playback,
    skip/error paths, ownership, pause, stop, and transition behavior.
12. **Loading/overlays/resources:** scene flow, level overlays, MEMORY/FMV overlays,
    streaming, loader fixups, asset residency, unload, and failure paths.

## Child-campaign rule

Create `Game Solving Campaign - <Subsystem>.md` only when a campaign begins. Each note
must include:

- Explicit scope/non-scope and Phase 1 rows covered.
- Pristine oracle fixtures and original behavior.
- Complete semantic frontier and typed state.
- Lifecycle, capacity, reset, transition, and campaign breadth.
- Native positive/negative controls and cross-system dependencies.
- Matching/semantic source status, unknowns, evidence, and exit decision.

Do not create empty speculative child notes. Do not mark a campaign solved because one
implementation slice, level, or successful demonstration is confirmed.

## Work packages

- [ ] Prioritize campaigns by dependency centrality and pristine coverage gaps, not by
  active MOD demand.
- [ ] Solve core player/input/lifecycle and shared object/render/audio substrates first.
- [ ] Run collectible, plant, enemy, and objective campaigns across every applicable
  level rather than only LEVEL01.
- [ ] Complete each regular enemy family and boss individually.
- [ ] Complete special-stage mechanics and exceptional overlay paths.
- [ ] Update [[Whole-Game Mechanics Baseline]] only with evidence-backed status changes.

## Exit gate

- Every baseline mechanic and engine system has a completed campaign or a reviewed
  proof that it is not present in the pristine PS1 version.
- Every completed campaign satisfies the full subsystem Definition of Done.
- Campaign conclusions generalize across every applicable stage and lifecycle.
- No unresolved field, dispatch, asset, or overlay intersects that subsystem's behavior
  without being explicitly bounded.

## Status vocabulary — what the words on this page mean

Three dispositions are in use and they make different claims. "Bounded-exhausted"
appears 20 times on this page and was never defined; the working definition below
is taken from the row that stated it plainly ([[EXP_2026-08-02_phase4_e07_bounded_exhaustion]]):

> *"E07 remains partial under the strict Phase 4 nine-metric definition, but it is
> now sufficiently bounded-exhausted to move on."*

| term | what it claims | who decides |
|---|---|---|
| **solved** | all nine DoD items satisfied | measurement against the DoD |
| **Substantiated Partial / bounded-exhausted** | still partial under the DoD; the remaining items are judged **low return**, so work stops | a stopping *decision*, recorded with its reasons |
| **partial / open** | neither of the above | default |

**These are not competing standards.** Bounded-exhausted is a decision to stop; it
is not a claim that the DoD is met, and it should never be read as one. A row can
be bounded-exhausted at 7 of 9 items (B06) or at 2 of 9 (E16) — the label says
what was decided, the scorecard says what was measured. Prefer publishing both.

⚠️ **Rows are at very different maturities, and the label hides it.** B06's
per-row scorecard reads **MET 1, 3, 6, 7, 8 · ADVANCED 2, 4, 5, 9** — five met;
E16's scorecard shows two. (This paragraph first said "seven": I had read the
older of the two B06 tables on this page. The *Per-row scorecard* is the current
one.) Both rows are "partial" in `analysis/mechanics_baseline.yaml`, where 96 of
107 rows share that one value. The baseline status field cannot express this and should not be
asked to.

## Handoff to Phase 5

Phase 5 receives individually solved subsystems and tests whether their interactions,
campaign composition, and long lifetimes also match pristine behavior.

## Campaign scorecard

| Campaign family | Status | Active child note |
|---|---|---|
| Input/player actions | pending | — |
| Player lifecycle | pending | — |
| Movement/world physics | partial | — |
| Rendering/camera/animation | partial | — |
| Seeds/plants/traversal powers | partial | — |
| Collectibles/equipment/rewards | partial | — |
| Objects/events/hazards | partial | [[Game Solving Campaign - Contact Object Pool]]; [[Game Solving Campaign - Event VM]] |
| Enemies/combat | partial | — |
| Bosses/special objectives | pending | — |
| HUD/frontend/persistence | partial | — |
| Audio/cinematics | partial | — |
| Loading/overlays/resources | partial | — |

### ⏹ STOPPED — B06/B08, and what it means for row selection (2026-08-01)

**Historical 2026-08-01 state:** work on B06/B08 was stopped with both rows
`partial` and the shared frontier `open`.

**2026-08-04 B06 override:** B06 is now **Substantiated Partial / bounded-exhausted**.
The row-specific pristine-ASM closure compiler classified all 251 reconciled potential
intersections (29 local and 222 cross-system) with zero unexplained sites, after the
Interpreter lifecycle control independently covered grant, protected contacts, countdown,
expiry, and post-expiry damage. See
[[EXP_2026-08-04_phase4_b06_bounded_exhaustion]] and
`analysis/phase4_b06_closure_20260804.json`. B08 remained `partial/open` at the time
of this B06-only override; the later B08 override follows below.

**2026-08-04 B08 override:** B08 is now **Substantiated Partial / bounded-exhausted**.
Its C guard inherits the sign-independent 251-site shared-slot provenance ledger and
independently verifies the `-3` grant, refresh semantics, three eligible contact
consumptions, zero/pop transition, post-pop damage, negative-only renderer, reset paths,
production dispatch, and retained-capsule control. See
[[EXP_2026-08-04_phase4_b08_bounded_exhaustion]] and
`analysis/phase4_b08_closure_20260804.json`.

Not because the mechanism is unclear — it is thoroughly understood and safe to mod today
— but because the remaining DoD items need general capabilities that should not be built
inside a single row's campaign.

**Why it stopped.** ⚠️ **Corrected 2026-08-04 — this sentence stated the wrong
bar, and it is the reason three rows stalled.** It read *"Item 2 requires the
unresolved-intersection set to be empty."* It does not. Canonical DoD item 2 asks
that the frontier be **enumerated**; the Phase-4 exit gate asks that anything
unresolved be **explicitly bounded**. "Unresolved-intersection set is empty" is a
*frontier-compiler* rule from [[Phase 4 - Acceleration Tooling Strategy]], scoped
to a **declared universe** and explicitly *"never changes a Phase-4 dimension by
itself."* See the reconciliation earlier on this page.

**What that means for this row:** B06's item 2 is recorded below as *ADVANCED*
with its residual **enumerated** — 1 unresolved callee destination, 937
same-width aliased accesses, 238 indirect calls. Enumerated is what the canonical
bar asks for. Whether it is also **explicitly bounded** is the remaining
question, and that is the `bounded_residuals` mechanism's job, not a matter of
driving a count to zero. Re-reading B06/B08/E15 against the canonical bar is
recommended and is left to those rows' owners rather than overridden here.

The original reasoning, preserved: A
full day of static work took the real residual from 416 (an inflated "882" — a counting
bug, now fixed) down to **251**, and then ran out of sound technique. The three
remaining levers were each tried and each failed honestly:

| lever | outcome |
|---|---|
| `jr`-dispatch entry seeding | zero yield **and** silently dropped 5 sites — reverted |
| accepted acceleration tooling | strictly weaker here (finds 8 accesses vs our 14) |
| player-pointer taint ("escape bound") | **not sound** — TOP and loaded values enter untainted; proves 3 *provenance chains*, not 3 *possible aliases* |

Making the taint sound needs to know which memory locations can hold a block pointer,
which needs store **destinations** resolved — and **4,490 stores image-wide have
unresolved destinations**. That is the wall, and it is not row-specific.

⚠️ **Runtime movies cannot substitute.** A replay shows what *did* execute; it can never
show that an untaken branch or unspawned object wouldn't have written the slot. Proposing
"named residual + runtime falsification = complete" was rejected, correctly — it is the
same reasoning error that caused the original false closure.

**Also true and worth internalising: no row in this baseline has ever reached `solved`
(0 of 107).** B06/B08 are not an outlier failure; they are the first row driven honestly
against the full nine-dimension bar, and they surfaced a wall that is common to every row
touching shared player state.

#### What this implies for picking the next row

The wall is **pointer provenance into the player block**. Any row whose state lives there
inherits the same 34 related functions and the same ~251 unresolved bases.

**⛔ Do not pick next — they reproduce today exactly:**
`B07_health_power`, `B09_super_jump`. Same blue-tier family, same player block, same wall.

**✅ Recommended, in order:**

1. **`E15_fmv`** — the best odds of actually clearing item 2. It is Region-B/overlay
   state, **disjoint from the player block**, and the accepted acceleration tranche
   already reproduces its frontier with an expected **`unclassified_xrefs: 0`** — i.e.
   the empty-unresolved-set bar may already be met for its declared universe. Strategic
   bonus: it answers whether the DoD is achievable *at all*, which after today is worth
   knowing before committing to another 100 rows.
   **⚠️ Correction, same day:** `phase4_static_frontier.py`/`phase4_promotion_preflight.py`
   do not exist on `master` — they are unmerged acceleration-branch tooling, and the
   `unclassified_xrefs: 0` figure above was never independently verified against this
   branch. A static-only pass run directly against master (`analysis/
   phase4_e15_fmv_frontier.json`) **discharged the long-open "MDEC decode/DMA call site"
   residual** (39 of 54 external `jal` targets from FMV.BIN land exactly on named
   resident PsyQ functions — `StSetStream`, `StGetNext`, `StCdInterrupt`, `DMACallback`,
   `CdRead2`, …) and fully resolved both known coordination addresses (completion flag
   `0x800CAC10`, frame-limit table `0x80131EEE` — both live entirely inside the overlay,
   zero resident-side static touches). **But `unclassified_xrefs: 0` does not hold**:
   169 of 538 `jal`-opcode decodes past the manifest point at invalid (non-RAM)
   addresses, proving the blob interleaves code and data the way every other overlay
   does — FMV.BIN has simply never been run through `function_census.py`'s block-start /
   string-exclusion pipeline the other 20 overlays get. **Item 2 for E15 is ADVANCED, not
   MET.** Detail: [[SYS_fmv_player_streaming]].
   **Same-day follow-up (items 5/6):** traced the full trigger call chain by manual
   instruction decode (self-caught one transcription error before banking — see the
   artifact). `scene_flow_dispatcher` (`0x8004FCA0`, the `jr`-dispatch target of
   `main_shell_substate_table`) calls `fmv_bin_load` from 3 sites (one scene-dependent,
   two literal movie-id constants 40/46), which loads `fmv.bin` to Region-B then calls
   **`0x800B6250`** — corrects two open Canon claims (trigger is resident, not
   "overlay-resident, un-RE'd"; the FMV.BIN entry point, previously "NOT confirmed", now
   is). Manifest recount: **11 levels, not 9** as the prior excerpt implied.
   **Superseded next day (2026-08-02):** fully resolved the movie-id→STR-filename table
   itself — `jr`-table at `0x800B5AA4`, 47 slots, 40 real cases (exactly matching Canon's
   prior "40-case" claim). **True level count is 15, not 11** — the 11-level figure came
   from the file's own stale 25-entry header manifest, which undercounts what the
   dispatch table actually references. All 15 campaign stages have cutscene coverage,
   plus 3 `ALT` endings, `INTRO`, `LOSE`. The two literal-constant trigger sites from the
   prior day now resolve to content: `a0=40` → `LEV15C` (3162 frames, the longest clip by
   far — inferred finale), `a0=46` → `LOSE` (281 frames — inferred game-over). One decoder
   bug self-caught before banking (frame-count leakage past unstopped `j` scans); one
   genuine irregularity confirmed via raw bytes, not fixed as an error (levels 4/5's
   A-clips are table-order-swapped). Detail: [[SYS_fmv_player_streaming]].
2. **`E06_contact_object_pool`** — highest dependency unlock. It is the substrate under
   every pickup/drop row in sections B and C, and today's work already mapped much of it
   (`contact_alloc 0x80059E44`, the metaB table, the walker dispatch, plus 39 dispatch
   tables enumerated read-only). Pool-shaped state (`0x800B0D18`, 64 × 0x38) is exactly
   the shape `region_provenance.c` handles well via stride/alignment exclusion.
   **2026-08-02 methodology correction:** the E06 **allocator core is bounded-exhausted**,
   while the row's offline frontier remains open and strict status remains `partial`.
   C static analysis corrected metadata B to exactly
   129 rows (`ctor 0..128`), metadata A to 78 rows, enumerated 94 allocator call sites,
   and proved the 64/64 occupied case cannot return. A validated 1,098-frame capsule,
   reconstructed and SHA-checked in C, confirms natural allocation, retirement,
   reactivation, walker/render execution, and 12 cursor wraps. Phase 2 also retains a
   native free-slot versus all-64-occupied `debugger.callFunction` A/B, so capacity is
   behaviorally confirmed. Typed state and original interfaces are advanced but not met:
   overlay producers, dynamic constructor bounds, complete field/reset writers, action
   side effects, the dedicated oracle, stage/transition breadth, cross-system contracts,
   source closure, and a derived gate remain open. No new Interpreter movie is required
   before the next C/offline batch. Evidence:
   [[EXP_2026-08-02_phase4_e06_bounded_exhaustion]] and
   [[Game Solving Campaign - Contact Object Pool]]; exact audit:
   `analysis/phase4_e06_methodology_audit.json`.
3. **`C13_grain_harvester`** — most already banked (accepted acceleration pilot +
   `src_re/grain_harvester_80051db4.c` + `tests/test_phase4_c13_harvester.py`). Good if
   the goal is converting existing investment. ⚠️ Caveat: its state touches the player
   block (flags `0x800A6590` bit `0x80`, and a transient write to `0x800A657E`), so it
   partially inherits the same wall.

If the goal is **MOD capability rather than DoD closure**, the better targets are
`E16_streaming_overlays`, `E01_terrain_visual` and `E02_collision` — they gate the Tier-3
custom-level work and their value does not depend on a row reaching `solved`.

#### Revisit condition for B06/B08

Only when **general pointer typing** (typed pool sets with base/stride/index ranges
derived from allocators and initializers) or **asset-loader** work exists for its own
reasons. Then items 2 and 5 may fall out without a dedicated campaign. Do not build that
infrastructure *for* these two rows.

### Row status — B06 invincibility + B08 bubble shield (2026-08-01)

> [!update] B06 closure override — 2026-08-04
> B06 remains `partial` on the roadmap's full nine-dimension semantic bar, but its declared
> valid-retail Phase 4 investigation bound is now exhausted. The C closure ledger accounts
> for 14 direct slot sites and all 251 reconciled indirect candidates with zero unexplained
> intersections. This callout records the B06 closure; the B08 closure is recorded below.

> [!update] B08 closure override — 2026-08-04
> B08 remains `partial` on the roadmap's full nine-dimension semantic bar, but its declared
> valid-retail Phase 4 investigation bound is now exhausted. The B08 C guard inherits the
> closed shared address frontier and independently closes all eight negative-slot mechanism
> groups, with the complete retained capsule supplying the controlled lifecycle evidence.

**Status: partial, with a confirmed semantic core.** These rows were moved to `solved`
on 2026-08-01 and **retracted the same day**. The retraction is recorded here rather
than erased, because the failure mode is instructive.

The mechanism is genuinely confirmed and was independently re-derived from the pristine
EXE by the reviewer: one sign-multiplexed halfword `0x800A657E`, positive consumed by
time, negative consumed by hits, `s1`-based interception, unconditional grants, respawn
reset, and the harvester's immunity coming from an upstream flag guard rather than the
slot. That model is Canon — see [[SYS_player_power_slot]].

### Per-row scorecard

Both rows describe one mechanism, so most items are shared; items 1, 6 and 7 differ.
`✅` met · `🟡` advanced but not met · `⬜` not started.

| # | DoD item | B06 invincibility | B08 bubble shield | What would close it |
|---|---|---|---|---|
| 1 | Original oracle | ✅ cold-boot, LEVEL01, **5/5**, no pokes | ✅ cold-boot, LEVEL06, **6/6**, no pokes | — |
| 2 | Complete frontier | 🟡 *shared* — alias-aware + callee + overlay + runtime union; $gp proven constant (916 excluded); a from-scratch C region-provenance analysis excludes 165 more by alignment/sign reasoning, cross-validated (combined-prover accounting: identical 14-hit sets, no exclusion/hit collisions, every open site classified) | 🟡 *shared* | Semantically **bound** the aliased-pointer residual (251 left, corrected from an inflated "882" — a counting bug counted revisits, not distinct sites). ⚠️ The old "`0x8004AFB0` proves it contains real slot accesses" justification is **retracted** — no counterexample is known now, which is not emptiness |
| 3 | Typed state | ✅ | ✅ | — |
| 4 | Lifecycle | 🟡 pause / respawn / transition / persistence proven; the knockdown residual is **withdrawn** — `0x8004AFB0` writes player+0x82, not this slot | 🟡 *shared* | Re-derive the exceptional-path list: the one path this campaign tracked was never a path at all |
| 5 | Original interfaces | 🟡 chain + render/asset boundary characterised | 🟡 *shared* | Attribute the runtime writer that rebinds descriptor +0x04/+0x06 (tpage/clut) |
| 6 | Campaign breadth | ✅ 2 stages, 2 disc dirs | ✅ 2 stages, 2 disc dirs | — (remaining stages by measured identity + availability, labelled an argument) |
| 7 | Cross-system | ✅ audio is **its own sound** (1 call site, VAG 50, 0.842 s) | ✅ audio is the **generic collectible sound** (4 call sites, 3 in the pickup handler); ablation removes 2 voices | — |
| 8 | Source closure | ✅ *shared* — `src_re/player_power_slot_800a657e.c`, 77-assertion guard | ✅ *shared* | — |
| 9 | Durable evidence | 🟡 hash-pinned fixtures, regenerable censuses + oracles, 4 gates | 🟡 *shared* | Oracle runner must retain mounted-media identity, debugger binary/capability provenance and watch saturation status; no repo-wide Phase-4 inventory/DAG/gate exists |

**Score: MET 1, 3, 6, 7, 8 · ADVANCED 2, 4, 5, 9.**

> **Item 2 re-read against the canonical bar — 2026-08-04.** This row stopped on
> *"item 2 requires the unresolved-intersection set to be empty"*, which is not
> the standard (corrected earlier on this page). Re-read against what the DoD
> actually asks — **enumerated**, with the remainder **explicitly bounded** —
> B06's own closure ledger already satisfies it: **251 of 251 candidate sites
> classified, 0 unexplained, every one `disjoint` with a stated proof** (19
> distinct proofs over 23 owner functions, 12 domains). Emitted as 13
> `bounded_residuals` entries, **0 rejections** under the promotion linter's two
> rules. `analysis/phase4_b06_promotion_residuals.json`,
> `tools/phase4_b06_promotion_residuals.py`, 6 gates.
>
> **Item 2 → MET WITHIN THE DECLARED BOUND.** Not unconditional: the ledger's own
> `strict_full_program_proof` is false and the closure holds for the resident
> executable under valid retail pointer schemas with no corrupt pointers,
> malformed assets or mods. That bound is emitted as its own residual so it
> cannot be dropped quietly.
>
> That puts B06 at **6 of 9** — and the honest headline is that it stopped for
> the *wrong reason* on item 2 while **4 (lifecycle), 5 (interfaces) and 9
> (durable evidence) remain genuinely open**. The row is still not solved, and
> re-reading item 2 does not make it so. Both rows stay `partial`: the DoD
requires *every* item.

> **Downgraded 2026-08-01 by adversarial review.** Items 2, 4, 5 and 9 previously read ✅
> here. The review was right and this table was wrong. Enumerating a residual is not
> bounding it; "the block never executes in the corpus" measures the fixtures, not
> reachability, and `phase4-closure.md:191` requires exceptional-path evidence; calling the
> tpage/clut writer an *inherited* Phase-3 gap explains its origin without exempting it;
> and the evidence wrapper is missing provenance that `phase4-closure.md:280` requires.
> This scorecard supersedes every earlier count in this file and elsewhere in the tree.

**What each row needs that the other does not.** Nothing, now — items 6 and 7 closed for
both rows on 2026-08-01, and everything still open (2, 4, 5, 9) is *shared*, because the
two rows are one halfword. B06 remains the better-evidenced of the pair: its sound is
unique to it and traced end to end, where B08's is the generic collectible sound.

**What made it not solved** is the Definition of Done, which requires *every* item:

| DoD item | Status |
|---|---|
| 1 Original oracle | **MET 2026-08-01** — two operator-recorded from-boot movies, asserted with no pokes by `tools/phase4_b06_b08_oracle.py`. B06 (LEVEL01): natural grant 400 @f5336 → 16 intercepted contacts with **zero** health writes → 400 strictly-decrementing ticks → expiry exactly on 0 @f6154 → damage lands. B08 (LEVEL06): grant −3 @f6046 → absorbs −2/−1/0 → pop @f6554 → damage lands, and **zero** ticks while negative |
| 2 Complete frontier | **ADVANCED** — coverage is now store sites (14 static + 1 runtime-only) **+ callee writes** (26 call sites enumerated; the transition clear attributed to `memset(player_block,0,168)` at `0x80046B68`) **+** a first-ever overlay census. Residual is enumerated, not hidden: 1 unresolved callee destination, 937 same-width aliased accesses, 238 indirect calls |
| 3 Typed state | pass |
| 4 Lifecycle | **CLOSED** — pause freezes the timer; persistence proven (powers are runtime-only); scene transition proven to CLEAR the power via a BIOS `memset` at `0xBFC02BB0`. The knockdown clear `0x8004AFB0` is **bounded, not observed**: guard chain fully decoded, every player-side guard verified satisfied at a poke before a known contact, and an execTrace shows the enclosing block executes **zero** times in the corpus — the divert is upstream of player state. Needs a knockdown-class fixture; not one of the DoD's enumerated lifecycle points |
| 5 Original interfaces | **MET**, one inherited residual — interface chain closed end-to-end, and the render/asset boundary characterised: renderer is `contact_record_billboard_render` `0x80014844` (screen-aligned `POLY_FT4` sprites) indexing the **same** `0x80096B98` descriptor table as type-0x3f pickups but by `rec+0x20`; table A resolved; `fcn.800593E8` decoded and live-verified 24/24; **no per-level asset dependency** beyond the plant models. Residual: the tpage/clut writer is unattributed — a pre-existing Phase-3 gap |
| 6 Campaign breadth | **MET** — both powers collected **naturally across three disc directories**: B06 in level 1 (`LEVEL01/LEVEL.DAT`), B08 in level 6 (`LEVEL01/LEVEL1.DAT`), and **both in level 13** (`LEVEL09/LEVEL.DAT`) with full lifecycles. Applicability *enumerated* from the per-level plant-model table — B06 in 10 of 15 stages, B08 in 11. Remaining stages carried by measured code identity + measured availability, **labelled as an argument** |
| 7 Cross-system | **CLOSED** — save/load proven. Audio settled for both rows by a caller census plus runtime assertions: **`65` has exactly one call site** (invincibility's sound is its own, traced to VAG 50, 0.842 s), **`-3` has four** — three in the generic pickup handler — so the **bubble plays the generic collectible sound**, confirmed by an ablation that removes exactly 2 voices at the grant. Shared contact sfx 14 bound to `0x8004A820` |
| 8 Source closure | **MET** — `src_re/player_power_slot_800a657e.c`, documentation-grade per the roadmap's *"matching **or** reviewed semantic source"* (byte matching is Phase 6's job and is already satisfied at zero by the byte-matched hand-ASM). Covers the slot's complete behaviour with every PC cited and re-verified; guarded by `tests/test_phase4_b06_b08_power_slot.py`, 77 assertions passing. Residuals listed in the file, incl. that `asm/hand_written/` is gitignored so the byte claim must cite `repro_inputs.sha256` |
| 9 Durable evidence | **MET 2026-08-01** — `analysis/phase4_b06_b08_fixtures.json` hash-pins every fixture *and* the `.sav` the movie format omits; `tools/phase4_b06_b08_census_gate.sh` and `tools/phase4_b06_b08_oracle.py` regenerate and falsify the frontier and lifecycle claims |

**The lesson worth keeping:** driving a variable in 16 scenes and verifying the code is
unpatched there is a *code-identity* argument, not campaign breadth. Breadth means the
mechanic exercised in those stages. Confusing the two is what made a partial row look
closed.

### Promotion gate — run, and it caught two defects

Run from a fresh `git clone` of HEAD, because these rows were falsely closed once.

**Verifies clean:** six-surface consistency, the source-closure test suite (72 passed, 5
skipped — the EXE-dependent assertions, correctly gated), the fixture manifest.

**Cannot run clean:** the census gate needs the pristine `SCUS_942.88` and the staged
overlay blobs, both gitignored as copyrighted. `verify_repro_inputs.py --provision`
restores the hand-written asm but not those. A property of the repo, not a gap here.

**Two defects found and fixed:**
1. The census gate **reported missing inputs as frontier drift** — in the clone it claimed
   all three overlay readers had disappeared, when the real cause was zero blobs present.
   It now exits `2` with an unambiguous `INPUTS ABSENT`.
2. The source-closure test **asserted a symbol name present only in an uncommitted file**,
   so it passed locally and would fail for anyone else. It now asserts **addresses**,
   which do not churn, rather than names, which do.

**Pre-existing, recorded not fixed:** the vault ratchet reports `evidence_deadfile: 3`
from a clean clone, from two Canon notes last touched 2026-07-12 — not from this campaign,
but the repo does not currently pass its own ratchet clean.

### Why the rows are still `partial`

**All nine items have a verdict; four of them are ADVANCED, not met.** The 2026-08-01
review rejected the earlier framing on this page — that only two *judgement calls*
remained — as too generous. What is actually outstanding:

- **item 2** — 251 same-width aliased accesses (937 → 882 when $gp was proven a
  constant, 916 gp-relative accesses soundly excluded → then **882 was found to be a
  counting bug**: `census_address.py` returned `unresolved` un-deduplicated by PC, so a
  block reprocessed during worklist convergence counted the same instruction once per
  revisit. True distinct-site count was 416, not 882 — → then 416 → 251 via
  `tools/region_provenance.c`, a from-scratch C port of the value analysis extended
  with a REGION lattice that excludes accesses provably of the form `K + i·S` by
  alignment/sign reasoning (165 excluded: 63 from propagating the sll/addu shift hint
  across block boundaries the same way register values already propagate, +9 from a
  second REGION source — a walking pointer, `addiu reg,reg,STRIDE` in a loop, whose
  CONST-set union used to collapse to TOP past 6 distinct values instead of being
  recognized as an arithmetic progression. A THIRD technique, loop-bound `slti`/`sltiu`
  extraction (TIER 3), is real, hand-verified infrastructure that finds 27 exclusions
  elsewhere in the image but ZERO inside this row's own 34-function scope — a
  disclosed negative result for this row specifically, not a failure of the method),
  cross-validated against the Python baseline with zero lost or spurious sites) plus
  4,967 overlay pointer-based accesses are **enumerated but not resolved**. Callee destinations are fully attributed (0 unresolved, was 1). ⚠️ The
  "`0x8004AFB0` proves this class contains real slot accesses" justification is
  **retracted** — that site doesn't write the slot at all (see item 4). No
  counterexample is currently known, which is not the same as the residual being
  empty. Indirect calls: 238 → 149 (same counting-bug fix); jalr-target resolution was
  added (tested, real capability) but resolves 0 on this image; disassembly narrowed
  the figure to **1 irrelevant site + 8 named functions** reached via `jr`-based VM
  dispatch that the analysis doesn't yet model — see [[SYS_player_power_slot]].
- **item 4** — the knockdown residual is **withdrawn**. `0x8004AFB0` does execute
  (frame 5966, refuting "never executes"), but it does **not** write this slot:
  `fp = v1 + 4`, so its store lands on player+0x82. Measured `fp = 0x800A6504`; a live
  400-tick invincibility ran straight through it. What remains is to **re-derive** the
  exceptional-path list, since the only path this campaign tracked was never one.
- **item 5** — the tpage/clut writer is unattributed. Inherited from Phase 3, but it
  intersects these powers' visual contract, so it is not exempt here.
- **item 9** — the evidence wrapper lacks required provenance, and there is no repo-wide
  Phase-4 inventory, fixture audit, evidence DAG or whole-phase gate.

These rows were promoted and retracted once, and **three of my own premises were corrected
by re-derivation** during this campaign (the renderer attribution, table A's indexing, and
whether the descriptor Canon applies). That history is why the bar stays where the review
put it.

### Closure path for these rows

The semantic breakthrough is real and the runtime behaviour is already established. The
method for what remains is **disassembly-first semantic proof, then the smallest runtime
oracle needed to falsify it** — not another pile of movies.

That distinction matters because it is the same one that caused the earlier failures. A
*simple instruction census* (literal addresses, obvious stores) cannot close these rows:
the game reaches the slot through runtime-derived pointers and generic callees like
`memset`, which is exactly how the first two censuses missed real writers. A *semantic*
analysis — pointer provenance, interprocedural data flow, overlay relocation, structure
layout, asset-loading paths — can. Collecting the powers in ten more stages would only
watch identical code execute; the cold-boot fixtures already bind the decoded mechanism to
real behaviour.

**Remaining work, all data-flow:**

1. ~~**Resolve or exclude the pointer-based accesses**~~ — **PARTIAL, and the count was
   corrected along the way.** `census_address.py` had a real counting bug: `unresolved`
   was never deduplicated by PC the way `hits` was, so a block reprocessed during
   worklist convergence counted the same instruction once per revisit — "882" was
   really 416 distinct sites. `tools/region_provenance.c`, a from-scratch C port of the
   value analysis with an added REGION lattice (`base = K + i·S`, proven from the
   `sll`+`addu` the compiler emits for `array[i]`), then excludes 165 of those 416 by
   alignment/sign reasoning — extended to propagate the shift hint across block
   boundaries (35 → 63), then extended again to recognize a walking pointer
   (`addiu reg,reg,STRIDE` in a loop) as a second REGION source, whose CONST-set union
   used to collapse to TOP past 6 distinct values instead of being recognized as an
   arithmetic progression (63 → 72) — plus a third technique, loop-bound `slti`/`sltiu`
   extraction (TIER 3), that is real and hand-verified but finds zero exclusions inside
   this row's own scope (27 elsewhere in the image) — cross-validated against the
   Python baseline with zero lost or spurious sites at every step
   (`tools/phase4_region_provenance_report.py`). 251 remain genuinely unresolved —
   almost entirely memory-loaded pointers and `jr`-dispatch entry state, the two
   classes the next methodologies target (see [[SYS_player_power_slot]]).
   *(item 2)*
2. ~~**Resolve the remaining `memset` destination** at `0x8004DC40`~~ — **DONE.**
   `memset(0x80095358, 0, 48)`, the camera block, provably disjoint. *(item 2)*
3. ~~**Resolve the indirect calls**~~ — **PARTIAL.** Same counting-bug fix applies:
   "238" was 149 distinct sites. jalr-target resolution added to `census_address.py`
   (tested on a synthetic image, since the real one triggers it zero times) and
   disassembly narrowed the figure: only 1 of 149 sits inside a function already
   touching the player block, and its argument is a stack address.
   The real remainder is 8 functions reached via `jr` tail-jump VM dispatch (confirmed:
   `event_interpreter_mover_vm` → opcode table `0x8001B2F4`), which needs full
   register-state propagation across `jr`, not `a0`–`a3` call-argument propagation.
   *(item 2)*
4. ~~**Trace the incoming path to the knockdown clear** `0x8004AFB0`~~ — **DONE, and it
   removed the item rather than closing it.** Guard chain decoded, deciding branch found
   (`0x8004AEBC`, `player+0x84 != 1`), site observed firing at frame 5966 — and then shown
   **not to write this slot at all** (`fp = v1 + 4` → player+0x82). Now: re-derive the
   exceptional-path list from scratch. *(item 4)*
5. **Trace the tpage/clut rebinding writer** through the resource loader — **PARTIAL.**
   `tpage_prim_setup` `0x8003E624`/`0x8003E660` attributed for pointer slots 115–127 and
   32–36/41–45, but **not** slots 12 and 46, which these pickups use. *(item 5)*
6. **Prove stage generalization statically** from resident-code identity, the pickup
   availability tables and an overlay analysis excluding slot mutation. *(items 2, 6)*
7. ~~**Repair the evidence wrapper**~~ — **DONE.** Oracle now retains mounted-media
   identity (`pristine_verified: true`), debugger/repository provenance, and
   determined watch-saturation status (not error-collapsed-to-clean); both `row`
   artifacts regenerated to the current shape and re-verified, PASS. Repo-wide Phase-4
   inventory, fixture audit and evidence DAG still do not exist. *(item 9)*

Runtime stays useful only where disassembly cannot settle something cleanly: whether an
indirect path is actually *reachable*, exact timing and pause behaviour, dynamic SPU/GPU
effects, and falsifying the static model against the pristine game.

**Already done** (retained so the path is not re-walked): alias-aware census generator and
overlay census (`e2e9e649`, `0a91ff5d`, gated by
`tools/phase4_b06_b08_census_gate.sh`); central fixture pinning (`4c734352`); cold-boot
natural-lifecycle fixtures for both rows; second-stage collection; pause, reload,
persistence and scene-transition assertions; runtime audio-dispatch assertion for both
rows; the committed oracle runner; and source closure
(`src_re/player_power_slot_800a657e.c`, 77-assertion guard).

### Active row handoff — A13 plant-output cycling

The operator discovery pass for `A13_cycle_plant_output` is complete. The five
resident selector bytes, their color ordering, and their selected-high /
maximum-available-low nibble contract are banked in
[[EXP_2026-07-30_phase4_a13_level01_brown_selector_packing]] and promoted to
[[Seed_plant_output_binding]]. Phase 4 must consume that contract and finish
writer ownership, wrap/denial feedback, persistence/reset, typed C/schema
promotion, and executable guards. Do not repeat color-address elimination or
request blue/green/yellow recordings merely to rediscover the contiguous array.
The row remains partial until those mechanical closure items pass.

#### A13 bounded-exhaustion update - 2026-08-03

**Status: substantiated partial; high-value static work exhausted.** Compiled C
analysis binds the X rising-edge owner at `0x80047A88..0x80047B9C`, exact wrap and
silent-denial branches, event `-16`, the 120-tick selected-to-maximum timeout, all
active resident writer classes, the 20-row consumer table, level-load default
`[0x11,0,0,0,0]`, respawn preservation, and malformed-state behavior. A scan of every
retail BIN finds only LEVEL07 brown/green and LEVEL09 yellow readers, with no overlay
writer. Typed C/schema, precise symbols, a machine report, and an executable opcode/
table/state-space guard are now banked.

Strict promotion remains open for two short normal-speed v4 Interpreter controls:
`A13_wrap_timeout.movie.json` and `A13_denied_one_tier.movie.json`, as specified in
[[EXP_2026-08-03_phase4_a13_bounded_exhaustion]]. Do not repeat lane-address discovery.

### C13 bounded exhaustion — grain harvester (2026-08-02)

C13 is **partial, high-yield row-specific work exhausted**, not universally solved. The accepted
capsule and matched pristine continuations remain the behavioral authority in
[[EXP_2026-07-30_phase4_c13_grain_harvester]]. The C continuation in
[[EXP_2026-08-02_phase4_c13_bounded_exhaustion]] scanned 892 hand-ASM files and
100,425 instructions, correlated all nine capsule grain records, and checked all
28 named anchors against raw pristine executable words.

The former mechanical gaps are closed. `0x8004A94C` clears the harvester flag;
after `0x80051F60` stops maintaining state `1`, the ordinary positive-slot tick
at `0x80048654` stores `1 - 1`. Grain contacts receive target `-1` at
`0x80053C58`; flags `0xEA` select the homing path, with Y/X/Z writers
`0x8005A4C8`, `0x8005A548`, and `0x8005A56C`. Collection reaches the SFX manager
at `0x80054F80` and increments the grain counter at `0x80054F9C`. Respawn clears
the runtime state through `0x8005B268` and `0x8005B340`.

No Interpreter movie is required for this closure. Deferred low-return breadth is
an exhaustive enemy-family fixture matrix, every-level availability, and complete
animation/asset/save-load surveys. Request a new Interpreter recording only when
one of those becomes a named behavioral question. The machine contract is
`config/phase4_c13_harvester.yaml`; static evidence is
`analysis/phase4_c13_asm_static.json`. The full MOD regression contract remains
Phase 5 work.

### B02 bounded exhaustion (2026-08-02)

**Status: `partial`, high-yield row-specific work exhausted.** The stale B02
binding incorrectly claimed that ordinary carried approach automatically transfers
the seed. Pure-Interpreter frames 86-190 disprove it: carry remains intact. The
ordinary actor path is a thrown seed at 296-390; Flik's separate ride is 400-500; and
the exceptional 748+ high-freefall path first qualifies Flik, then invokes the carry
detach helper before the actor scan can propel the seed independently.

| Closure metric | State | Evidence/boundary |
|---|---|---|
| 1 | Behavior core | advanced | Corrected four-case behavior and two independent lift laws bound |
| 2 | Semantic frontier | advanced | Full 820-byte handler, detach helper, XZ helper, direct fields/readers/writers and branch bands decoded by C |
| 3 | Variants/capacity | bounded | Compacted live-actor table contract bound; exhaustive enemy flags and instance census deferred |
| 4 | Lifecycle | advanced | Ride entry, sustained/clamped lift, release/fall and return to grounded mode covered; every landing geometry omitted |
| 5 | Original interfaces | advanced | Plant dispatch, shared player physics, carry helper, RNG, live-actor table and animation 13 bound |
| 6 | Campaign breadth | deferred | Resident all-stage code plus primary fixture; repeated stage/instance movies have low marginal value |
| 7 | Cross-system | advanced | Carry, throw, actor motion, player mode/contact, dandelion latch bridge and enemy-eligibility boundary bound |
| 8 | Source closure | met | Documentation-grade semantic C, two C offline reducers, one C runtime reducer and byte-exact retained ASM |
| 9 | Durable evidence | advanced | Both fixture pairs centrally hash-pinned; static/capsule/runtime artifacts regenerable; no whole-campaign oracle gate |

Do not spend a standalone iteration on repeated stages, an exhaustive enemy-family
flag census, every landing surface, or exact visual-spin ownership. Revisit only for
a direct dependency or when shared actor typing makes those proofs cheap. The row
remains partial rather than solved, and cold boot is not required because no disc,
code, or asset changed. See [[SYS_propeller_plant]] and
[[EXP_2026-08-02_phase4_b02_bounded_exhaustion]].

### B03 bounded exhaustion (2026-08-02)

**Status: `partial`, high-yield row-specific work exhausted.** The prior B03
ledger was stale after the pure-Interpreter trace. Sustained glide, steering,
landing, latch timing, automatic release, the overhead presentation call, player
animation selection, and direct lifecycle clears are now mechanically bound by
`analysis/phase4_b03_dandelion_static.json`,
`analysis/phase4_b03_dandelion_runtime.json`, and [[SYS_dandelion_glide]].

| # | DoD item | Status | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | One native, hash-pinned Interpreter fixture with an instrumented/control equality boundary; no negative-control movie |
| 2 | Complete frontier | deferred | 19/19 direct retained-ASM latch accesses classified: 15 absolute plus four typed `$s1+0x9E` player-relative sites; other indirect/overlay closure inherits the shared provenance wall |
| 3 | Typed state | met | Type-8 plant slot, latch 11, velocity/state/grounding, presentation and retirement fields typed |
| 4 | Lifecycle | advanced | Launch, sustained use, landing, level transition, harvester takeover, and respawn bound; exhaustive pause/save/unload sampling omitted |
| 5 | Original interfaces | advanced | Resident plant dispatch, player physics/steering, propeller bridge, sound 15, effect submission and animation 18 bound |
| 6 | Campaign breadth | deferred | Primary fixture confirmed; exhaustive stage/alternate-instance reachability has low marginal value for resident code |
| 7 | Cross-system | advanced | Carry detach, collision, steering, propeller, harvester exclusion, transition and respawn interactions bound |
| 8 | Source closure | met | Documentation-grade semantic C plus two C reducers and byte-exact retained ASM |
| 9 | Durable evidence | advanced | Movie/state centrally hash-pinned and C gates regenerable; no whole-campaign B03 oracle gate |

Do not spend a standalone iteration on the repository-wide alias proof, repeated
stage movies, or exact GPU buffering tail. Revisit B03 only when general pointer
typing lands or a concrete MOD/campaign dependency needs native
dandelion-to-propeller combination or stage-specific reachability evidence.
Cold boot is not required because no disc, code, or asset changed.

The final C gate correction is part of this row status: the animation store is
`0x800568D4` (`0x800568D0` only forms the address), and the 19-site frontier is
the union of 15 absolute and four typed player-relative accesses.

### D09 bounded exhaustion (2026-08-02)

**Status: `partial`, row-specific work exhausted.** D09's external/manual name
"cockroach" is the already-documented Redbug (actor id 19), identified two
independent static/live ways and reconfirmed via a deterministic live-pointer-table
lookup. Full findings: `analysis/phase4_d09_redbug_identity.json`,
[[SYS_enemy_ai]], [[SYS_enemy_death_and_permanence]],
`ObsidianVault/Experiments/EXP_2026-08-02_phase4_d09_redbug_identity.md`.

| # | DoD item | Status | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | HP trace replays deterministically from a pinned fixture (frames 437/493/583); the kill and the confirmed chase cycle were unrecorded manual play, twice |
| 2 | Complete frontier | advanced | One write site pinned end-to-end (the CHASE-bit setter, `0x8005914C` — a whole-project residual predating this row, not just narrowed for it); no systematic census of this actor's fields |
| 3 | Typed state | met | Inherits and live-confirms the generic `actor_record` schema (id/pos/velocity/flags/hp/vm_ip) |
| 4 | Lifecycle | advanced | Spawn-to-death traced for one instance; in-session respawn-after-temporary-KO IS REAL (⚠️ a same-day "NEGATIVE, 66s window" claim was retracted after operator correction and a live re-test confirmed a full reset once Flik genuinely walked away and back — see D12's `RESPAWN_MECHANISM_2026-08-02` for the ASM trace and its own open contradictions); no pause/scene-transition/scene-reload coverage |
| 5 | Original interfaces | deferred | Not started beyond the one pinned call site above |
| 6 | Campaign breadth | deferred, scope exhaustively known | Static scan of all 24 campaign RAW files: Redbug exists in scene 5 ONLY, 6 instances, ZERO type-word variants — the "unknown scope" uncertainty is closed even though behavioral coverage stays at 1 of those 6 |
| 7 | Cross-system | advanced | Player-state (berry damage) and AI-state (CHASE flag + confirmed approach/retreat movement, 4/4 consistent live trials) bound; audio call sites exist in the same handler (sound ids 17/22 on other damage-class branches) but the exact id for Redbug's own berry-throw class was not isolated — tracing it needs more branch-by-branch disassembly than the return justified |
| 8 | Source closure | deferred | No C written for this row's specific behavior |
| 9 | Durable evidence | advanced | Canon + Experiment note + executable test guard exist (`tests/test_phase4_d09_redbug_identity.py`, 14 assertions); no whole-campaign D-family gate |

**What actually got resolved, beyond D09 itself**: two residuals that predate this
row and apply to the whole enemy-AI system — who sets the CHASE bit
(`Enemy_AI_movement_programs.md`'s own "the gate itself is proven, the setter
isn't pinned"), closed with real evidence; and whether a temporarily-KO'd enemy
respawns in-session (`Enemy_death_and_permanence.md`'s own named residual) —
**not closed negative as first banked**. That first answer was retracted the
same day after operator correction and re-opened as a real, positive finding:
respawn happens, gated by something tied to genuine player movement rather than
raw distance, ASM-traced to a specific reinstantiate-from-spawn-template
routine with two of its own named open contradictions (see
[[SYS_enemy_death_and_permanence]] and D12's `RESPAWN_MECHANISM_2026-08-02`).

**A process lesson worth keeping**: the core "does Redbug chase" question was
already answered before this row's work began, in an archived note ("Horsefly/
Redbug closed 16-20k units", 2026-07-03) — four live sessions were spent
re-deriving it before that was found. Check existing evidence, including
archived/superseded notes a hub links to, before reaching for a new live session.

Do not spend a standalone iteration on the repository-wide frontier/interface
census (same general-infrastructure wall B06/B08 already hit and documented as
poor-return for a single row), further live probing of the retreat trigger, the
flags bit `0x1000`, or contact-range reachability (each cost roughly a full
session this pass for an uncertain result — the chase question alone took four
attempts to resolve cleanly), or a full immunity/resistance sweep. The
mechanical, bounded items that remain (a scripted oracle recording, a
documentation-grade C file, drop confirmation) would succeed but add
formalization, not new understanding — optional, not prioritized. Revisit D09
only when general pointer typing lands, a whole-D-family census campaign is
undertaken (several other D-family rows likely share the same identity-mapping
shape against the already-known 44-id roster), or a concrete MOD/campaign
dependency needs Redbug-specific combat balancing.

### D13 bounded exhaustion (2026-08-02)

**Status: `partial`, row-specific work exhausted.** D13's confirmed subject,
scoped directly with the operator (*"the row is for that shell bug in
LEVEL04"*), is shell_bug (actor id 18) exclusively — a single-level species
in `LEVEL04` (disc directory) = chronological Level 7, cross-verified against
the campaign progression table (`0x80077FA0`). Full findings:
`analysis/phase4_d13_shell_bug_armor.json`, [[SYS_enemy_ai]],
[[SYS_enemy_death_and_permanence]],
`ObsidianVault/Experiments/EXP_2026-08-02_phase4_d13_shell_bug_armor.md`.

| # | DoD item | Status | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | Armor sweep (5/5 berry classes), aggro test, and respawn test all replay from a pinned fixture (`shell_bug.sav`) with a documented, reliable throw method; every specific trial was unrecorded manual play, not a scripted/asserted runner |
| 2 | Complete frontier | not started | The berry-tough class-exclusion gate was searched for in `contact_vs_actor_handler` and not found (the function has more unrelated special-case branches than assumed); no systematic census of this actor's fields |
| 3 | Typed state | met | Inherits and live-confirms the generic `actor_record` schema; the temporary-KO vs. permanent-kill record shapes (id retained vs. cleared) confirmed species-specifically |
| 4 | Lifecycle | advanced | Spawn-to-death traced; in-session respawn-after-temporary-KO IS REAL (⚠️ a same-day "NEGATIVE, 66s window" claim shared the same flawed stationary-Flik test design as D09/D12 and is retracted on that basis, though shell_bug itself wasn't independently re-run live — see D12's `RESPAWN_MECHANISM_2026-08-02`); no pause/scene-transition/scene-reload coverage |
| 5 | Original interfaces | not started | — |
| 6 | Campaign breadth | met (for this species) | Exhaustive static scan of all 24 campaign RAW files: shell_bug exists in `LEVEL04` ONLY, 6 instances, ZERO type-word variants — full native population enumerated. (Two other species incidentally found nearby — `id=11`, ~130 records campaign-wide, and canyon_bug/`id=37`, four other levels — are confirmed OUT OF SCOPE for this row, not this species' own breadth.) |
| 7 | Cross-system | advanced | Player-state (berry damage) and AI-state (CHASE flag sets but produces no movement, confirmed negative) bound; audio/rendering/HUD not checked |
| 8 | Source closure | not started | — |
| 9 | Durable evidence | advanced | Canon + Experiment note + executable test guard exist (`tests/test_phase4_d13_shell_bug_armor.py`, 12 assertions); no whole-campaign D-family gate |

**What actually got resolved, beyond D13 itself**: ⚠️ this originally read as a
second species-level confirmation that temporarily-KO'd enemies do not
respawn in-session. That was retracted the same day, shell_bug included, once
operator correction and live re-tests on D09/Redbug and D12/worm showed the
opposite — enemies do respawn, gated by genuine player movement rather than
distance alone. shell_bug itself was not independently re-run live, but shares
the identical original test design and is retracted on that basis. See
[[SYS_enemy_death_and_permanence]] and D12's `RESPAWN_MECHANISM_2026-08-02`.

**A scope-correction process lesson worth keeping**: a live session spent real
effort testing an actor believed to be canyon_bug that was actually an
unrelated bird enemy sharing the same save file — caught only because the
operator was watching closely and said so plainly (*"that's the bird you're
lowering"*). A save filename is a label, not a verified fact; the actor's own
`id` field should have been checked and cross-referenced against what the
filename implied before building conclusions on top of it.

Do not spend a standalone iteration on the exact berry-tough gate PC (already
tried once, genuinely more expensive than expected — the function has several
unrelated special-case branches sharing its address range), canyon_bug or
`id=11`'s own investigation (confirmed out of scope for this row, real species
worth a future row of their own if one exists), or pause/scene-transition
lifecycle (plausible but low expected new-information value). The mechanical,
bounded items that remain (a scripted oracle recording, a documentation-grade
C file) would succeed but add formalization, not new understanding —
optional, not prioritized. Revisit D13 only if a future row explicitly covers
`id=11` or canyon_bug, or a concrete MOD/campaign dependency needs
shell_bug-specific combat balancing.

### D12 bounded exhaustion (2026-08-02)

**Status: `partial`, row-specific work exhausted.** No dedicated row exists for any
single D-family species — confirmed D12 is the only row in the whole baseline
touching worm/earthworm/centipede at all. Every named species in the row was
swept this pass: worm (`id=40`, operator-directed focus, its own armor/strike
discovery), wall_worm (`id=41`, checked next to see whether worm's findings
generalized — they mostly don't), and earthworm (`id=12`, the row's own
namesake, last untested). Full findings: `analysis/phase4_d12_worm_id40.json`,
[[SYS_enemy_ai]], [[SYS_enemy_death_and_permanence]],
`ObsidianVault/Experiments/EXP_2026-08-02_phase4_d12_worm_id40.md`.

| # | DoD item | Status | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | Armor sweeps, the strike measurement, and the respawn walk-away test all replay from pinned fixtures (`worm.sav`, `wall_worm.sav`, `earthworm.sav`) with documented, reliable methods (including two real methodology corrections caught mid-session — a throw-timing miss for earthworm's homing, and a wrong position-poke for earthworm's reposition attempt); every trial was unrecorded manual play, not a scripted/asserted runner |
| 2 | Complete frontier | advanced | The STRIKE mechanic was traced end-to-end to its native call (`0x80057b84`, an already-decompiled function); the respawn mechanism was ASM-traced via a live `accessLog` capture to a previously undocumented reinstantiate-from-spawn-template routine (`0x80049C2C`), catching and correcting a real mis-attribution to an unrelated, already-documented function along the way. Real residuals remain open, not glossed over: the reinit routine's exact caller/trigger is unconfirmed (`execTrace` proved unreliable — the same 0-hits-despite-a-real-event pattern hit twice this session, independently, on two different traces), a distance-based admission check found alongside it reads backwards from the observed near/far behavior, the spawned-object (kind 21/22/23) contact handler was never traced, and a second native (`0x800B3F00`) in the same shared program was never investigated |
| 3 | Typed state | met (for the fields touched) | Inherits and live-confirms the generic `actor_record` schema; newly typed this pass: the `+0x4A` per-actor countdown timer (signed halfword, per-species negative constant at death, ticked by the per-frame live-table loop), and the reinit routine's own field-copy contract (id/pos/program/hp/flags from the spawn-chunk backlink) |
| 4 | Lifecycle | advanced | Spawn/death/respawn now genuinely understood, including a real retraction cycle (see below); no pause/scene-transition/scene-reload coverage |
| 5 | Original interfaces | not started | — |
| 6 | Campaign breadth | met for worm + earthworm, NOT MET for wall_worm | Worm: 5 levels, 15 records, zero variants (exhaustive static scan). Earthworm: `LEVEL03` only, 11 records, zero variants (same scan pass). wall_worm's own campaign breadth was never scanned — a same-day audit attempt to close this cheaply (reusing the existing decompression tooling) was abandoned after a raw byte-pattern search produced false positives in unrelated chunks and didn't land on a clean record boundary even in the known-good worm chunk; the original scan's exact on-disk record-field offsets weren't preserved this session, so this needs a careful reimplementation, not a quick redo |
| 7 | Cross-system | advanced | Player-state (strike damage + knockback) bound for worm; audio/rendering/HUD not checked; the spawned kind-21/22/23 objects' own visual identity unresolved |
| 8 | Source closure | not started | — |
| 9 | Durable evidence | advanced | Canon (three dated sections in `SYS_enemy_ai.md`, one per species) + Experiment note + executable test guard exist (`tests/test_phase4_d12_worm_id40.py`, 16 assertions); no whole-campaign D-family gate |

**What actually got resolved, beyond D12 itself — and including a real
retraction, banked honestly rather than quietly fixed.** The row's original
"in-session respawn tested negative" claim (itself inherited from the identical
test design used in D09 and D13) was **wrong** — it only ever tested a
stationary Flik. Operator correction plus live re-tests showed respawn is real
across all three species, gated by something tied to genuine player movement,
not distance polled via a memory read: extensive position-poke experiments
(single teleport, a "real" one-frame delta, many small per-frame increments)
never reproduced it, only actual continuous execution with real controller
input did. The mechanism was then ASM-traced to a specific, previously
undocumented routine, with two of its own contradictions named rather than
resolved into a falsely tidy story. This correction was propagated back into
D09's and D13's own sections and their shared home,
[[SYS_enemy_death_and_permanence]] — not left standing only here.

**A methodology lesson worth keeping, found twice independently**: `execTrace`
watches armed via this project's usual resume/pause driving pattern can report
zero hits on a PC that demonstrably executed (confirmed both on the reinit
routine and, separately, on a wall_worm throw-dispatch check). Treat a 0-hit
`execTrace` result as inconclusive, not as proof the code path wasn't reached,
until this is understood or a different driving pattern is validated against
it.

Do not spend a standalone iteration re-attempting the wall_worm campaign-breadth
scan without first recovering or rebuilding the exact on-disk record-field
offsets used successfully for worm/earthworm (a raw byte-pattern search is not
a shortcut — it produces false positives). Do not chase the admission-check
contradiction or the reinit routine's exact caller further via live timing
experiments — that avenue is proven unreliable this session; it needs either a
different, validated `execTrace` driving pattern or fresh disassembly of
whatever writes the live table's other slot-adding site. The mechanical,
bounded items that remain (a scripted oracle recording, a documentation-grade
C file) would succeed but add formalization, not new understanding — optional,
not prioritized. Revisit D12 only if a future row needs the spawned
kind-21/22/23 objects' own identity, mine-plant interaction with a berry-tough
enemy, or a concrete MOD/campaign dependency needs worm-family combat
balancing.

## Reusable movie evidence

[[EXP_2026-07-18_phase4_trace_capsules|Phase 4 persistent trace capsules]] is the hash-indexed external evidence lane
for replay-once, analyze-many movie work. Capsules may narrow change frames, state transitions, RAM/VRAM/SPU deltas,
and execution hotspots without another emulator replay. They do not close a campaign row by themselves: exact
semantics, writer/dispatch attribution, breadth, lifecycle, Canon promotion, and executable guards remain required by
this phase's Definition of Done.

The archived 2026-07-18 executable is identity evidence, not a standalone runnable
toolchain. Live work that must reproduce that toolchain uses the complete, externally
hash-manifested runtime bundle documented in
[[EXP_2026-07-18_phase4_trace_capsules]], verifies its running-binary hash through
`debugger.capabilities`, and rejects the lone executable. Large replay/capture work
must preflight `/tmp` and move to `/var/tmp` or run-owned scratch when necessary.

The campaign workflow is **capsule first, live debugger last**. Every Phase-4 session must validate the central index
and query a relevant retained capsule before replaying a covered movie. Offline frame-boundary registers,
RAM/VRAM/SPU reconstruction, change points, and execution hotspots are the default analysis surface. A fresh isolated
DuckStation API run is justified only by a named missing domain or temporal precision, exact instruction/DMA/GPU/SPU
causality, a required native behavioral control, or a missing/invalid capsule. Record that escalation in the campaign
evidence; never promote frame-boundary capsule evidence into an every-cycle claim.

The mandatory scheduler for this lane is
`analysis/phase4_offline_opportunity_queue.json`. Regenerate it before selecting work:
it must join all 107 unique Phase-4 rows to current coverage, fixture, movie, and capsule
hashes; list available domains, exact batch queries, offline-answerable assertions,
unknowns, dependencies, prior escalation, and priority; and derive exactly one of
`offline_ready`, `offline_partial`, `live_required`, or `no_capsule`. Freshness and
coverage guards must reject missing/duplicate rows, stale inputs, and authored
pass/complete flags.

Each iteration takes a **subsystem-sized offline batch**—one coherent campaign cluster,
or normally at least the three highest-value open `offline_ready` rows. It must not
keep deepening one partial row or refresh prior-phase evidence while higher-priority
Phase-4 offline work is available unless a retained, load-bearing dependency proves
that ordering necessary. Repeated scans belong in a reproducible external cross-movie
derived index; Git retains only its code/schema/hash manifest/non-copyrighted summaries
and guards, never capsule or movie bytes.

Before any live run, generated `analysis/phase4_live_escalations.json` must name the row
and hypothesis, every relevant capsule plus exact offline command/window/domain, what
those queries answered, the precise information still unavailable, the proposed live
experiment and control, expected new evidence, and why no higher-priority offline batch
supersedes it. “Needs exact causality/control” alone is not a justification. The fresh
verifier regenerates and falsifies this queue, samples its offline claims, and rejects
unnecessary or retrospectively documented live work.

<!-- B02_RUNTIME_CLOSURE_2026-08-02 -->
### B02 runtime closure addendum: propeller plant

Status: **bounded-exhausted for high-value Phase 4 requirements**.

The corrected v4 Interpreter movie was replayed at normal speed through
debugger.resume, not movie.advanceToFrame. A deliberately heavy full-handler execTrace
flight check remained synchronized by operator observation. A following narrow replay
captured 1,662 non-truncated exact-PC events and 61 non-truncated carry-offset writes.

C reduction confirms no release during the carried approach, manual throw at input
296, loose-seed actor lift from input 298, player ride/lift from input 401, pickup at
input 565, and propeller-helper detach at input 779 with player and the same seed lifted
in that frame. The carried seed was actor-lift eligible during inputs 92..180 even
though carry state never changed, proving actor lift and release are separate paths.

Closure artifacts are analysis/phase4_b02_propeller_static.json,
analysis/phase4_b02_propeller_capsule.json, and
analysis/phase4_b02_propeller_runtime.json. Canon is
ObsidianVault/Canon/Systems/SYS_propeller_plant.md. Only low-return RNG-distribution,
every-placement/non-seed-class sampling, and pixel-level reconstruction remain
deferred. No new movie or cold boot is required.

### C13 target-specific frontier closure - 2026-08-04

C13 now carries the Phase 4 disposition **substantiated partial / bounded-
exhausted** for valid-retail gameplay. The retained capsule reproduced the
equip and nine collection events; C-based pristine-binary analysis found 80
exact flag accesses and classified all 200 target-specific indirect candidates
(139 reads, 61 writes; zero unexplained). The shared state slot likewise has
192/192 current residual sites classified. Pause, scene-reset, capacity, and
placement-breadth bounds are explicit. Exact visual/animation/SPU attribution
and malformed-state behavior remain outside the accepted bound, so no new
Interpreter movie is required before moving on. See
[[EXP_2026-08-02_phase4_c13_bounded_exhaustion]].

#### C13 strict Phase 4 closure correction - 2026-08-02

**Status:** partial; high-yield row-specific work exhausted. **Strict closure: OPEN.**

The earlier bounded-exhaustion wording was not a Phase 4 solved state. The ten-dimension
scorecard is machine-readable in analysis/phase4_c13_dod_scorecard.json.

- C/ASM state and transition semantics are exact for equip maintenance, Cross release,
  ordinary slot release, grain homing, collection count/SFX, and scene reset.
- C decompression and static scanning covered all 15 active campaign RAW resources.
  Six contain one harvester placement each: scene IDs 1,3,5,7,10,12, corresponding to
  operator levels 1,2,5,8,10,11. All six use record 63, type word 0x00002223,
  and identical non-position parameters.
- Retained natural behavior covers one of those six placements. This is 1/6 behavioral
  breadth, not a full-breadth claim.
- The shared player-block semantic frontier is still open: 251 same-width accesses,
  149 indirect calls, and 4,967 overlay pointer accesses remain untyped/unbounded.
  Runtime movies cannot prove absence over that frontier.
- No Interpreter movie is requested now because it cannot change the strict OPEN verdict.
  If the shared frontier is later closed or reviewer-bounded, request one second-placement
  natural lifecycle first; request capacity/persistence or GPU/SPU movies only for those
  specifically named domains.

### Row status - E11 dynamic geometry (2026-08-02)

**Status: `partial`; the static owner and late-phase runtime loop are bound. A named
Interpreter movie is required before row-specific exhaustion.**

The old E11 blocker incorrectly stopped at the shared chunk-34/35 vertex buffer and
did not account for the runtime scene permutation. Bug Bar is player-facing stage 9
but scene ID 14, so the owning overlay is `LEVEL04/LEVEL1.BIN`. C analysis of the
hash-verified overlay binds the main controller at `0x800B3C70` to pass-2 object
transforms: object 9 receives a per-tick XYZ write through `0x80029508`, objects 0
through 9 receive rotations through `0x800292DC`, and objects 0 through 5 receive
interpolated path XYZ writes through `0x80029508`.

The hash-pinned `level_09.sav` anchor was then replayed at normal 60 Hz in a fresh,
pristine-media, Interpreter-configured DuckStation instance. Over 302 frames the
controller ran 61 times, exactly once every five frames, producing 610 rotation
calls, 427 transform calls, and 1,037 watched overlay-global writes without
truncation. Register capture independently proved indices 0 through 9 and the
authored signed rotation deltas
`[-100,+120,-90,+144,-110,+128,+32,+32,+32,+64]`.

The anchor has Thud at HP 0. It therefore cannot close visible index-to-piece
labels, early/mid-fight transitions, arena contact/damage timing, or the post-fight
transition. Continue only after recording a pure-Interpreter, normal-speed movie
starting with Thud alive at HP 50 and covering rolling/contact plus post-fight.
Cold boot is not required because this investigation changed no disc, code, or
asset. Evidence and exact commands are in
[[EXP_2026-08-02_phase4_e11_dynamic_geometry]] and
`analysis/phase4_e11_dynamic_geometry.json`.

### Row status — E09 grain-count gates (2026-08-02)

**Status: bounded-exhausted partial. Frontier state: open only at strict-DoD scope.**

The row's original named gaps are discharged. C reconstruction of 12 validated capsules
and C-decoded runtime ASM enumerates all nine LEVEL02 and three LEVEL07 gates, all
threshold sources, exact success/denial predicates, both geometry mechanisms, feedback
calls, and cooldown cadence. LEVEL02 has five complete natural openings; all three
LEVEL07 captures are deliberate one-short denial controls at grain 9/19/29.

Strict promotion is withheld. Typed state and original interfaces are met; original
oracle, complete frontier, lifecycle, breadth, cross-system closure, source closure and
durable promotion evidence remain advanced rather than all met. The smallest useful live
escalation is one Interpreter-mode LEVEL07 above-threshold movie held through state
`32 -> 0`; no further ASM-only drill-down has proportionate return before that fixture.

Evidence: [[EXP_2026-08-02_phase4_e09_bounded_exhaustion]],
`analysis/phase4_e09_static.json`, `analysis/phase4_e09_capsule.json`, and
`analysis/phase4_e09_bounded_exhaustion.json`.

### E11 deep-dive disposition (2026-08-02)

E11 is **substantiated partial; move on, do not mark solved**. A compiled C census of all 15 retail scene DATs found pass2 authored-object tables only in runtime scenes 3, 4, 14, and 15, exactly matching the overlays with direct shared pass2 helper callers. Scene 14 declares ten non-null objects (`0..9`), which matches both the controller's static bounds and the normal-speed runtime trace cardinality.

The bounded static frontier is now guarded by `tools/phase4_e11_pass2_guard.c` and summarized in `analysis/phase4_e11_deep_dive.json`. Strict promotion still requires an Interpreter-mode, normal-speed lifecycle movie with active positive/negative contact controls, phase transition or defeat, post-fight state, reload/reset, and screen-visible object mapping. That movie is a deferred reopening trigger rather than a prerequisite to start the next row. Full evidence and hashes are in [[EXP_2026-08-02_phase4_e11_dynamic_geometry]].

### D10 scoped closure (2026-08-02)

D10 is **confirmed for the spider-chain and Bonus 1 handoff scope**. The valid retained capsule was queried before any live escalation. A compiled C reader reconstructed all 3,654 records with 10,962 successful RAM/VRAM/SPU hash checks and zero mismatches, covering four-event negative threshold, fifth-event unlock, scene `0x10` entry, high earned-guard commit, and return to menu scene 0. C-assisted ASM analysis pins the qualification field, guards, counter, exact threshold, flag, latch, fade, and reset instructions. The direct GP-relative writer frontier contains no alternate increment.

The executable scenario now extends through final scene 0 and flags `0x22`; the complete extended scenario passed all nine assertions against pristine hash-pinned media. A compiled C logic guard also passed the four-versus-five threshold, earned-bit rejection, scene-`0x10` rejection, and transition-reset cases. No Interpreter movie is required for D10. The retained movie is CachedInterpreter and remains offline/poll-only; a new Interpreter recording is required only for a future per-instruction question outside the retained capsule. Full scope, hashes, and exclusions are in [[EXP_2026-08-02_phase4_d10_spider_chain]].

### D02 bounded subproblem: enemy actor `+0x20` (2026-08-02)

D02 remains **partial**, but the prominent `+0x20 = velocity_y` guess is exhausted and rejected. A compiled C reader queried six valid retained capsules before live escalation, reconstructed 2,895 frame records, and verified 8,685 RAM/VRAM/SPU hashes with zero mismatches. Confirmed X/Z controls matched 2,003/2,127 and 2,006/2,127 moved frames; `+0x20` matched Y motion only 61/1,431. The field remains intentionally unnamed.

Exact positive semantics now require instruction-level writer/reader attribution. All available source movies are CachedInterpreter, so the named escalation is an 8-10 second B13 mine recording in Interpreter mode at `phase4/movies/interpreter/D02_actor20_B13.movie.json`. Until that fixture exists, do not infer a field name from adjacency or stride symmetry. Full evidence, rejected-run provenance, hashes, and the recording request are in [[EXP_2026-08-02_phase4_d02_actor20]].

### D02 closure update: enemy actor `+0x20` (2026-08-02)

**Exact row status: substantiated partial; bounded `+0x20` subproblem exhausted; move on.**

The requested Interpreter movie v4 records the corrected behavior: Flik throws the Mine Plant output at input 304 and it shortly collides with a spider. A normal-speed clean replay and a replay with all 40 actor `+0x20` words watched ended at the same frame/cycle with byte-identical 2 MiB RAM. The untruncated trace contains 1,991 accesses at 23 retail instruction sites.

C decoding against pristine `SCUS_942.88` confirms `+0x20 = velocity_y`: two update paths apply `+0x100` gravity, cap at `+0x1000`, add the value into actor Y, and clear it on settle/collision paths; an airborne initializer writes `-0xD00`/`-0xB60`; generic vector code treats it as the Y member of the `+0x1C/+0x20/+0x24` velocity triplet.

Closure-metric disposition:

| Metric | Result |
|---|---|
| State ownership | Confirmed field, both main update paths, initializer, cap, and clearing sites |
| Runtime attribution | 1,991 Interpreter events, 23 exact instruction sites, no truncation |
| Behavioral control | Correct thrown-mine/spider reproduction; clean and armed final cycle/RAM identical |
| Breadth | Six retained species/fixture capsules plus four actor IDs in the focused live trace |
| Negative hypothesis | Direct frame-boundary `deltaY` equality remains rejected; ASM resolves why that metric was too strict |
| Remaining gap | Only the row's broader inventory of other unclassified actor/object kinds |

No additional Interpreter movie is needed for actor `+0x20`. Continuing to enumerate unrelated unknown kinds here has poor Phase 4 return, so bank the confirmed field and select another unfinished row. Evidence: `[[EXP_2026-08-02_phase4_d02_actor20]]`, `[[MEM_8009FD80_enemy_actor_pool]]`, and `analysis/phase4_d02_actor20_runtime.json`.

#### D02 final deep-audit addendum (2026-08-02)

The bounded `+0x20` result survives a stricter closure audit:

- 813/813 runtime writes classified; zero unexplained.
- 1,178/1,178 runtime reads classified; zero unexplained.
- Both gravity/integration paths, signed impulses, cap behavior, generic XYZ-vector use, and clearing semantics pass a C instruction guard.
- Delay-slot correction: `0x8004D02C` is an unconditional store for either outcome of its immediately preceding branch once that path is reached; `0x8004C04C` is the conditional near-zero settle clear.
- Padding, target/extent, direct frame-delta, and meaning-free accumulator alternatives are rejected.

Exact scale and per-species scheduling cadence remain unknown but are not required to identify or own `velocity_y`. No more D02 `+0x20` work or Interpreter movie is justified. Broad-row status remains **substantiated partial, move on** solely because other unclassified object kinds remain category-wide. Evidence: `analysis/phase4_d02_actor20_deep_audit.json` and `[[EXP_2026-08-02_phase4_d02_actor20]]`.

### D07 mosquito-family bounded investigation (2026-08-02)

**Status: partial, static-only lane exhausted; Interpreter attack movie required.**
C analysis binds actor ID 10, callback 0x8004A180, its complete 35-instruction reaction
path, proximity-gated movement VM, four free-roam actors, and two Thumper actors. A
normal-speed poll-only replay localizes one Thumper actor's dormant-to-active release,
but the old v2 movie reports non-reproducible and cannot classify damage.

| Closure metric | State | Evidence/boundary |
|---|---|---|
| 1 | Behavior core | advanced | Patrol admission and boss release bound; damaging attack behavior open |
| 2 | Semantic frontier | advanced | Callback/fields/flag/timer/velocity/SFX/VM bound; latch producer and player-damage owner open |
| 3 | Variants/capacity | partial | Four free-roam plus two boss actors compared; ground/flying/sting labels not separated |
| 4 | Lifecycle | partial | Dormant/parked/active states and five-frame callback cadence bound; hit/death/respawn open |
| 5 | Original interfaces | advanced | Actor pool, optional callback, VM, level-data and SFX joined; player damage open |
| 6 | Campaign breadth | partial | 167 callback instances in census; one free-roam and one boss fixture live-bound |
| 7 | Cross-system | advanced | Enemy VM, actor flags, boss release and audio joined; damage class open |
| 8 | Source closure | advanced | Exact ASM and C static/census/runtime reducers retained; indirect damage ownership open |
| 9 | Durable evidence | partial | Hashes, JSON, Canon and Experiment retained; no valid capsule or Interpreter attack movie |

Do not repeat the static callback or actor-field pass. The next justified work is one
fresh Interpreter movie containing a free-roam sting/damage event and a
Thumper-spawned hit, followed by targeted tracing after state load. Full findings:
analysis/phase4_d07_mosquitoes.json, [[SYS_mosquitoes]], and
[[EXP_2026-08-02_phase4_d07_mosquitoes]].

## D07 correction and current closure status (2026-08-03)

**Status: substantiated partial; do not mark exhausted yet.** This block supersedes any earlier D07 wording that treated ordinary `state 1`/flag `0x4` as attack-triggered aggro.

Closed lanes:

- Natural roaming/proximity VM behavior and its ordinary bit-`0x4` transition.
- Causal disproof that Square indices `340..344` in `mosquito_aggro_after_berry.movie.json` trigger the mosquito: the no-Square control matches actor writes, index-545 state, and the index-1200 actor/frame fingerprint.
- Thumper-spawned mosquito slot `0x8009FE88`, allocation index `712`, activation index `718`, launch motion, and dormant adjacent-slot control.
- Static callback contract at `0x8004A180`: state `1` plus latch `0x1000` clears the latch, sets timer `25`, and doubles `+0x1C/+0x24`.
- Bounded upstream writer candidate `0x8004B460/0x8004B464` in `0x8004ABF4`.

Open lane:

- One Interpreter v4 movie with a visibly landed single attack, followed by at least 120 neutral frames, to bind the upstream `0x1000` writer to callback consumption and determine whether the resulting response should canonically be called aggro. Cold boot is not required.

Evidence: [[EXP_2026-08-02_phase4_d07_mosquitoes]], [[SYS_mosquitoes]], and `analysis/phase4_d07_mosquitoes.json`.

## D07 final synchronized closure (2026-08-03)

**Status: bounded exhausted; ready to move on.** This block supersedes the earlier D07 partial/correction block, whose no-hit conclusion came from an isolated profile without an explicit Interpreter CPU setting.

The synchronized explicit-Interpreter replay confirms berry-contact aggro. Square at movie frames `340..344` is upstream input; berry contact at movie frame `1132` directly executes `0x8004B460/0x8004B464`, sets latch `0x1000`, and starts timer `15`. The callback clears the latch two emulator frames later. After the timer expires, the VM enters attack state `1` at emulator frame `39937`, `148` frames after contact. A same-profile no-Square control has no latch write, timer, reaction-body execution, or corresponding delayed attack transition.

Roaming, trigger/provenance, timing/state, negative control, and Thumper-spawned allocation/launch lanes are closed. Exact shared hitbox geometry and exhaustive pursuit-vector arithmetic are bounded to other rows or minimal-return follow-up. No further D07 movie or cold boot is required.

Evidence: [[EXP_2026-08-02_phase4_d07_mosquitoes]], [[SYS_mosquitoes]], and `analysis/phase4_d07_mosquitoes.json`.

## 2026-08-03 D14 closure: wasps and dragonflies

- **D14 Wasps and dragonflies -> BOUNDED EXHAUSTED / MOVE ON.** Compiled C against the pinned pristine `SCUS_942.88` decodes dragonfly `0x8007755C..78` as a random-flight/seek loop with no species strike section, bee/wasp `0x80077578..C8` as random flight parked on opcode 18 followed by a contact strike, the exact `0x8004CA18` `+6` VM transition, the native `0x80057920` strike, the sound-only dragonfly callback `0x8004A20C`, and homing filter `0x8005747C` (`+0x5C bit 0x1` required; `0xA0` rejected).
- **Runtime closure:** explicit-Interpreter, media-verified save runs bind dragonfly to ID 34/callback `0x8004A20C` and wasp/internal bee to ID 13/callback `0x8004A144`. An active dragonfly moved `(4704,0,-9842)` over 120 frames while parked at `0x80077570`. A controlled 60-frame Up approach drove the bee `0x77592 -> 0x77598` at frame 25958, executed native strike at 25994 with the same actor pointer, and reduced Flik health `4 -> 3`; the 600-frame no-input control did none of those.
- **Targetability closure:** live target tables contain positive dragonfly and bee cases. The paired bee fixtures give the negative switch: slot 6 flags `0x4007` is present, then flags `0x1006` is absent while another targetable ID-13 slot replaces it. This agrees with the byte-verified homing filter.
- **Why move on:** all named D14 gaps now have static ownership plus relevant live positive/negative evidence. Dragonfly has no species-specific sting path beyond its sound callback; remaining generic collision behavior belongs to the shared enemy-contact system. No Interpreter movie or cold boot is required for the closed row. Evidence: [[EXP_2026-08-03_phase4_d14_wasps_dragonflies]], [[SYS_wasps_and_dragonflies]], `analysis/phase4_d14_wasps_dragonflies.json`, and `tools/phase4_d14_static.c`.
### A04 bounded exhaustion - kick (2026-08-03)

A04 is a **substantiated partial at bounded exhaustion** and is cleared to move
on. The retained kick capsule was validated first but contains only empty-space
kicks, so the actor-contact domain justified one isolated v4 Interpreter replay.
The operator movie is a measured natural near miss against actor 39. A synchronized
X-only causal control crossed the contact boundary while preserving Y/Z/facing,
animation, and enemy state; a second control changed only actor flag `0x80`.

| # | DoD item | Status | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | v4 Interpreter fixture replays clean/traced to the identical frame and cycle; its natural kick is explicitly classified as a near miss rather than promoted into a false hit oracle |
| 2 | Complete frontier | advanced | Input arm, timer tick, animation/effect dispatch, body reaction, contact-object prefilters, action-class HP dispatch, and death handoff are pinned to exact PCs; unrelated callers remain outside this row |
| 3 | Typed state | advanced | Player action timer `+0x7A`, actor flags `+0x5C`, knockback `+0x6C`, HP `+0x6E`, contact action class, collision offsets/radius, and relevant animation state are typed for this path |
| 4 | Lifecycle | advanced | Admission, active interval, effect interval, and return-to-zero recovery are reconstructed; pause/scene-transition cadence breadth is not covered |
| 5 | Original interfaces | advanced | Pad edge, ground gate, animation/effects, actor collision, chase flag, and player reaction interfaces are connected end-to-end |
| 6 | Campaign breadth | deferred | No campaign-wide census of enemy species using contact flags `0x20`, `0x40`, or `0x80`, or rare actors with HP >=100; this is low-return breadth rather than an unknown kick law |
| 7 | Cross-system | advanced | Input, player animation, effect objects, actor collision/AI flags, action-class HP damage, worm immunity, and death handoff are causally separated |
| 8 | Source closure | advanced | Documentation-grade C is banked at `src_re/kick_action_80048e9c_and_contact.c` |
| 9 | Durable evidence | advanced | Structured JSON, Canon note, Experiment note, fixture hashes, transient artifact hashes, and this exact row disposition are banked |

**Correction after the worm fixture:** the immediate body-contact branch is not the
damage stage. It sets actor flag `0x1000`, skips normal player damage, and selects
knockback 30 or the flag-`0x80` reduced reaction. The later ctor109 effect carries
action class 1 into the enemy hit tail, where eligible targets receive `HP - 99`.
This is an effective instant kill for ordinary sub-100-HP enemies.

Worm ID 40 naturally consumed three confirmed effect contacts through persistent
flag `0x40`, writing knockback 20 but leaving HP 8. A runtime-only mask-zero control
sent the next synchronized contact through `0x80059094/0x800590E4`, storing `-91`
from HP 8 and reaching the death tail. The original instruction was restored before
shutdown. Worm kick immunity is therefore causal, not inferred from a visual miss.

Do not spend another standalone A04 iteration on a full `0x20/0x40/0x80` species census,
semantic naming of `0x80089938`, or per-scene wall-frame cadence unless one becomes
a dependency. The ordinary 99-HP rule and worm exception are already supported by
natural contacts and a synchronized causal branch control. No further
Interpreter movie is requested before row selection. Evidence:
[[EXP_2026-08-03_phase4_a04_kick]], [[SYS_kick_action]], and
`analysis/phase4_a04_kick.json` plus `analysis/phase4_a04_kick_worm.json`.

### A13 runtime closure addendum (2026-08-03)

A13 is `substantiated` and `bounded_exhausted`. The v4 Interpreter denial movie proves `0x11` Cross input reaches the availability test without selector or timer writes. The wrap/timeout movie proves `0x44 -> 0x14 -> 0x24`, immediate timer arm/re-arm, proximity-latch freeze, all 120 decrements, and expiry normalization `0x24 -> 0x44`. C-based retail ASM analysis identifies the freeze latch at `0x8008242C` and the decrement gate at `0x80047568..0x80047578`. See [[EXP_2026-08-03_phase4_a13_bounded_exhaustion]] and [[Seed_plant_output_binding]]. No additional A13 movie is required.
## A06 row disposition - downhill abdomen slide (2026-08-03)

**Disposition:** `substantiated` and `bounded_exhausted`. Normal-speed v4 Interpreter escalation was required because the first static reconstruction conflated a separate `player+0x8C` fast path with ordinary sliding.

- Compiled C/ASM analysis now separates the routes. Ordinary sliding checks held Cross at `0x80048B5C..0x80048B6C`; grounded state `4` or later stores state `5` at `0x80048D64`. Grounded Cross release clears state to `0` at `0x80048D10`.
- `A06_slide_steering.movie.json` confirms stable state `5`, multiple left/right steering intervals, and release at movie frame `360` followed by state `0` at `361`.
- `A06_slide_natural_end.movie.json` confirms terrain termination while Cross remains held. When projected motion falls below the `0x300` maintenance threshold, timer `+0x7A` is not rearmed: selector `0x1C -> 0x06` begins recovery at frame `543`, the timer reaches zero and selector `0x06 -> 0x00` at `565`, and Flik is upright before Cross releases at `596`. Coarse state `5` clears separately at `597`.
- The ordinary shared heading path adjusts target `+0x28` and converges current heading `+0x20`; the default path caps wrapped correction input at `0x400` and shifts by two. The old `0x80` bound belongs only to the separate `+0x8C` surface-projector path.
- The shared abdomen contact resolver still bounds offensive contact as actor event 4 / knockback-drop reaction with no direct actor-HP store in that resolver.
- Terrain termination, get-up timing, steering, and grounded release are closed. Named obstacle or airborne-release controls can be investigated later; exhaustive surface enumeration is high effort with minimal Phase 4 return and does not keep A06 open.

Primary evidence: [[SYS_downhill_abdomen_slide]], [[EXP_2026-08-03_phase4_a06_downhill_slide]], `analysis/phase4_a06_downhill_slide.json`.

## A01 row disposition - move/run (2026-08-03)

- Exact row: `A01_move_run` - Analog/D-pad movement and running.
- Registry status remains `partial`; Phase 4 disposition is `substantiated_partial_bounded_exhausted`.
- Closed reusable scope: analog/D-pad normalization into the shared direction path, run/slow caps, acceleration and release decay, modulo-4096 turning, projected-component rotation into velocity, `FUNC_8003633C` collision handoff, normal slope/contact response, and idle/run/slow animation coupling.
- Runtime anchor: pristine `SCUS-94288` plus hash-pinned `level01.sav`; same-save API controls, Interpreter, normal speed. Analog full-up matched digital Up exactly at eight frames. An untruncated 25-event execTrace bound the calculation/store/integrator PCs on four 30 Hz movement ticks.
- Capsule gate: no Phase 4 capsule manifest was identity-bound to `lag_walkingaround.movie.json` or `level01.sav`; no adjacent capsule was substituted.
- Movie/cold boot: neither is required for this non-mutating static/save-state investigation.
- Deferred as low-return enumeration: every authored obstruction/surface and an all-level movement oracle, plus special-state overrides owned by other rows. This is why the row remains partial while being sufficiently exhausted to move on.
- Evidence: [[EXP_2026-08-03_phase4_a01_move_run]], `analysis/phase4_a01_move_run.json`, `tools/phase4_a01_static.c`, `src_re/move_run_80048138.c`, and [[Gameplay_-_Input_and_Movement]].

## A03 - Jump - substantiated partial, continue required (2026-08-03 audit correction)

- Row status remains **Partial**; disposition is **continue required**. The
  earlier bounded-exhausted label was retracted after checking the binding Phase
  4 closure contract.
- Closed: Cross admission, caller/state/animation gates, signed `<1024`
  near-floor airborne admission, normal and powered impulses, press/release
  recurrence, gravity/cap, apex timing, landing state/grounded/animation latches,
  and the normal 11-tick release micro-optimum.
- Capsule control: B09 supplies complete normal and powered full-hold arcs with
  matched independent control and no truncation.
- Live control: pristine flat-ground branches measured apex gains 6336, 11520,
  17024, and 16896 for held gameplay ticks 1, 4, 11, and 12; all returned to
  state 0, grounded 0x0101, animation 22.
- Seed scope: A13 owns Cross-based carried-seed output selection; A15 owns jump
  plus butt-slam seed cracking and plant spawn. A03 links those rows rather than
  duplicating their lifecycle matrices.
- Active behavior gaps: natural ledge/coyote positive and negative controls,
  natural ceiling-contact outcome, powered release timing, and an explicit
  modifier-applicability matrix.
- Active methodology gaps: A03 was absent from the pre-run live-escalation
  ledger; its C reducer is not yet a complete executable row gate; the evidence
  is not integrated into the authoritative queue/debt/campaign/fixture/gate
  layers; and its transient traces lack a centrally bound declarative scenario.
- No Interpreter movie is requested yet. First audit available pristine fixtures
  and attempt the natural controls through isolated API input; request a movie
  only for a named case that cannot be reproduced that way.
- Evidence: [[EXP_2026-08-03_phase4_a03_jump]],
  `analysis/phase4_a03_jump.json`, `tools/phase4_a03_static.c`, and
  `src_re/jump_state_80048138.c`.

### A03 jump: ceiling continuation addendum (2026-08-03)

- Closure status remains continue_required; do not label A03 bounded-exhausted yet.
- The ASM/C pass confirms the swept resolver accepts dominant-positive-ny ceiling orientations.
- Thirteen pristine anchors yielded 3,176 untruncated resolver events after separating walls and boundaries by dominant normal axis.
- Level 11 sector 122 supplies a real ceiling-facing plane. A controlled upward jump crossed its signed plane from 2771 to -246, but the contact missed the authored polygon footprint and was not retained as the collision winner.
- The available save-state path search is bounded in analysis/phase4_a03_ceiling.json.
- The only remaining direct behavior gate is movies/Phase4/Interpreter/A03_ceiling_contact.movie.json: a natural jump into a low retail ceiling, followed by release and landing.
- No cold boot is required for that pristine runtime-only control.

### A03 jump: first ceiling movie is a negative control (2026-08-03)

- movies/Phase4/Interpreter/A03_ceiling_contact.movie.json replays reproducibly on explicitly pinned Interpreter mode but does not truncate the second jump.
- Both recorded jumps gain 20096 world-space Y units.
- No collision winner occurs during the second ascent; all retained planes are downward-facing floors/slopes.
- Preserve the movie as negative evidence. A03 remains continue_required.
- Replacement gate: movies/Phase4/Interpreter/A03_ceiling_contact_v2.movie.json, using a low underside that visibly hard-stops the ascent before the control apex.
- Full evidence is in analysis/phase4_a03_ceiling_movie.json and ObsidianVault/Experiments/EXP_2026-08-03_phase4_a03_jump.md.

## D04 berry immunity/resistance - bounded-exhausted partial (2026-08-03)

**Status: substantiated partial, high-value resistance-law work exhausted; move on.** A compiled C analyzer over the hash-verified pristine executable pins the previously unresolved gate: `0x80058EE4` tests `enemy+0x5C & 0x40`; tough contacts with connecting `+0x24 == 1` or `+0x2C == 1` enter reaction-only handling and jump around common damage/death, while other contacts reach `0x8005905C`.

The useful matrix has two runtime-state rows. Ordinary damageable actors accept all five native berries; gold alone is permanent. Berry-tough state blocks red only; blue/homing apply `-2`, gold `-4` plus permanence, and mega `-3`. This is supported by complete independent five-berry sweeps on shell bug and worm id 40, a four-class wall-worm control, and ordinary spider/mosquito/Redbug evidence. Bit `0x40` may be VM-managed, so this is not promoted as a permanent species label.

The strict full-family replay-movie matrix remains absent. Repeating the same resident gate across every named family is deferred as low-return presentation breadth, and boss-specific defeat FSMs remain in their own rows. No new Interpreter movie is required unless a family contradicts the two-state law or full movie breadth becomes an explicit deliverable. Evidence: `[[EXP_2026-08-03_phase4_d04_berry_immunity_matrix]]`, `analysis/phase4_d04_static.json`, `analysis/phase4_d04_evidence.json`, and `analysis/phase4_d04_bounded_exhaustion.json`.

## B04 cannon plant bounded closure - 2026-08-03

- **Registry result:** `Partial`, substantiated bounded partial; move on.
- **Static owner correction:** `seed_plant_cannon_handler` (`0x8005C110`) owns
  the mature-contact gates, carry cleanup, cannon state, and the 17-tick
  `player+0x7C` lockout. It does not write player velocity.
- **Launch owner:** shared player path `0x80048658..0x800486D8`; seated velocity
  is pinned to zero and expiry seeds fixed vector `(0,-8192,0)` from an inline
  immediate, not a table. Gravity makes the first retained boundary `-7936`.
- **Capsule result:** contact `119`, launch boundary `153`, apex `215` with
  `126976` units of rise, dandelion latch `11` at `275`, sustained `vy=350`
  from `277`, landing/reset `459..461`. All RAM/VRAM/SPU reconstruction hashes
  and the independent control fingerprint match.
- **Deferred low-return breadth:** exact camera-transform attribution,
  animation/SPU asset identity, and all-level instance census. No new
  Interpreter movie or cold boot is required absent a concrete dependency.
- **Evidence:** [[EXP_2026-08-03_phase4_b04_cannon_plant]],
  [[SYS_cannon_plant]], `analysis/phase4_b04_bounded_exhaustion.json`.


## B05 bounded-exhaustion bank (2026-08-03)

B05 remains Partial globally but is bounded-exhausted for Phase 4. Static ASM closes the green selector (counts 1..4 -> types 4/10/9/1), growth-reaction writers, lifecycle, and mature collision ownership. The verified A13 green-level capsule covers all four tiers and common timing; the Interpreter `B05_tall_leaf_boost` fixture closes type 10's previously missing upper surface with a 246-boundary stable hold, departure, fall, and lower-floor landing. No further fixture is needed. Remaining per-asset triangle topology is explicitly banked as low-return detail. See `analysis/phase4_b05_bounded_exhaustion.json` and [[EXP_2026-08-03_phase4_b05_green_leaf_platforms]].


## A09 bounded-exhaustion bank (2026-08-03)

A09 remains Partial globally but is bounded-exhausted for Phase 4. Pristine ASM identifies the Square admission, proximity/facing gates, selected actor offset `0x800A655C`, phase byte `0x800A65A3`, lift/stable attachment modes, manual release, post-release motion, cancellation, and respawn owners. The control-exact LEVEL01 capsule supplies three pickup/drop cycles plus no-Square controls; the Training oracle independently confirms the fixed attachment law. The fixture's `blocked_drop` name does not denote a denied release: obstruction acts on the detached trajectory. No additional Interpreter fixture is required. See `analysis/phase4_a09_bounded_exhaustion.json` and [[EXP_2026-08-03_phase4_a09_seed_pickup_drop]].

## A10 bounded-exhaustion bank (2026-08-03)

`A10_handstand` remains **Partial** under strict campaign vocabulary but is
**bounded-exhausted / move on**. The control-exact retained `carry_handstand`
capsule and native C reducers bind the fresh-Square mount to actor
`0x8009FE88` (selected offset `0x108`, source `0x80094A70`), whose behavior
`+0x40 = 3` selects fixed-seed mode 14 at `0x80047870/0x80047874`. Mode 14
lasts 1042..1215 and contains a 114-boundary exact player-position freeze with
grounded zero. Fresh Square releases through `0x80047CD0`, clears the latch,
and reaches the state-6 dismount writer `0x80048D64`; landing and state clear
are bounded at 1252 and 1254. The camera remains the normal derived
`0x8004DF18` follow producer and has no A10-owned latch.

Banked evidence:

- `ObsidianVault/Experiments/EXP_2026-08-03_phase4_a10_handstand.md`
- `ObsidianVault/Canon/Systems/SYS_fixed_seed_handstand.md`
- `analysis/phase4_a10_capsule.json`
- `analysis/phase4_a10_static.json`
- `analysis/phase4_a10_bounded_exhaustion.json`

No Interpreter movie is required. Reopen only for a named cross-level
contradiction or a camera-subsystem question, not generic placement breadth.

## A18 pause - resident-shell bounded exhaustion (2026-08-03)

**Status: `partial`, high-value row-specific work exhausted; move on.** No relevant
retained capsule exists, so C analysis ran first against the hash-pinned pristine
executable, followed by one named, state-anchored runtime control. No CPU
instrumentation, movie, cold boot, or media mutation was required.

A rising START edge plus three numeric eligibility gates writes pause flag
`0x8008224E=1`. The outer loop then substitutes pause renderer/input
`0x8004F478/0x8004F480` for gameplay scheduler `0x8004ECD4`, while retaining
presentation. C census finds all seven direct flag accesses, 34 gameplay and 11 pause
direct-call targets, and no indirect calls in either bounded root.

Matched runtime controls prove the canonical actor and contact pools, plant/HUD
samples, camera, and established player simulation fields freeze while the menu and
framebuffer continue changing. XA/CD sector progress stops. `_SsVmFlush` continues;
its cursor `0x800A65A8` is sound ownership, not player simulation. Resume and the
Down/Cross/Left/Cross exit path are confirmed through the exact pause, flow-state,
transition-timer, and player-flag writes.

| # | Closure metric | State | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | Enter, 120-frame dwell, resume, and exit from one pristine state |
| 2 | Complete frontier | advanced | Root call split and all direct pause-flag accesses closed |
| 3 | Typed state | advanced | Pause, input edge, options, confirmation, flow, timer, and sound cursor typed |
| 4 | Lifecycle | advanced | Admission, debounce, dwell, resume, exit, and reset clears bound |
| 5 | Original interfaces | advanced | Input, gameplay scheduler, render, SFX, XA/CD, and scene flow bound |
| 6 | Campaign breadth | bounded | Resident all-stage mechanism plus ordinary stage; special contexts deferred |
| 7 | Cross-system | advanced | Input -> scheduler/render/audio -> scene-flow chain confirmed |
| 8 | Source closure | met for bounded slice | Semantic C plus pristine-EXE C analyzer |
| 9 | Durable evidence | advanced | Scenario, hashes, analysis, Canon, and Experiment; no capsule |

Revisit only for a named boss/FMV/telescope/overlay denial, exact per-voice SPU
behavior on a compatible binary, or a MOD requirement. Evidence:
[[SYS_pause_shell]], [[EXP_2026-08-03_phase4_a18_pause]],
`analysis/phase4_a18_pause.json`, `config/phase4_a18_pause.yaml`,
`src_re/pause_shell_8004ecd4_8004f480.c`, and `tools/phase4_a18_static.c`.

## A19 closure - SELECT status display (2026-08-03)

**Classification:** substantiated partial, high-value bounded-exhausted. Move on.

The resident player update tests SELECT as controller bit `0x0001` at
`0x800484B0`. While held, it calls `0x800503FC` for the four status pulses
`0x800B0188/18C/190/194`. The normalizer sustains a pre-render `0x0400`
plateau; the gameplay HUD step at `0x8004F3E8` advances it to the observed
frame-boundary value `0x0440`.

| Closure metric | A19 result |
|---|---|
| Trigger/admission | SELECT bit `0x0001`; two-display-frame input latency at the LEVEL01 anchor |
| Sustained hold | Four status pulses stabilize at `0x0440` |
| Release | Pulses advance by `0x40` per 30 Hz update and wrap to zero |
| Sources | lives `0x800A65A0`; grain `0x800A65A1`; health `0x800A6594`; FLIK bits `0x800A65A2` |
| Latches | `0x800B018A/18E/192` refresh at the `0x0400` phase |
| Renderer | `0x800526F4`, with scene-specific status branches |
| Gameplay interaction | presentation-only: actor/contact/plant/camera/player domains match a 60-frame no-input control |
| Capsule evidence | C01/C02 complete; 1,083 frames reconstructed in C; zero domain-hash mismatch |
| Movie/cold boot | not required |
| Residual bound | glyph-pixel provenance, exhaustive special-scene screenshots, and semantic story labels for special meters |

The exact explanation and reproduction are banked in
[[EXP_2026-08-03_phase4_a19_status_display]] and [[SYS_status_display]].
Reopen A19 only for a named special-scene panel, glyph-art dependency, or MOD
intersection; those residuals do not leave the common input/state/timing contract
open.

### A19 status-display component exhaustion (2026-08-03)

A19's earlier common-path closure has now been expanded to the individual panel
items. Compiled C queried the accepted B07/A13 capsules and decoded all 54
relevant pristine-EXE callsites. A bounded, untruncated Interpreter matrix then
confirmed the fixed Flik-head glyph, direct lives digit, health upload law
`frame = 4-health`, packed grain digits, per-bit normal/tinted FLIK letters,
and the selected seed-power indicator. Evidence and exact hashes are in
[[EXP_2026-08-03_phase4_a19_status_display]] and
`analysis/phase4_a19_component_matrix.json`.

Closure classification remains **partial, high-value bounded-exhausted**. The
only residuals are pixel-atlas archaeology and an inactive scene-specific
`0x80052C00` presentation branch, neither of which changes the operator-visible
SELECT mechanic or justifies an Interpreter movie. Move on.

### B01 closure override — 2026-08-04

B01 mushroom trampoline is **Substantiated Partial / bounded-exhausted**. The pristine C guard, byte-reproduced retained-capsule reduction, and deep control-flow guard close eligibility, fixed impulse, player latches, repeat/duplicate handling, five-distinct completion, and the shared effect tail with no row-relevant unexplained behavior. Exact animation/SPU asset naming remains explicitly low-return and outside the behavioral bound.

Evidence: [[EXP_2026-08-03_phase4_b01_mushroom_trampoline]], [[SYS_mushroom_trampoline]], and `analysis/phase4_b01_bounded_exhaustion.json`.

### B04 closure override — 2026-08-04

B04 cannon plant is **Substantiated Partial / bounded-exhausted**. Pristine C and retained-capsule reproduction close the mature contact, 17-tick seated hold, fixed `-8192` launch seed, ballistic path, dandelion latch/slow-fall law, steering observation, landing, and grounded reset. Deferred camera-transform and asset-name attribution is explicitly low return.

### B-series audit — 2026-08-04

B01-B08 and B10-B14 are bounded-exhausted at their declared Phase 4 investigation boundaries. **B09 super jump remains Substantiated Partial / Open** pending a complete bit-`0x20` frontier, production-chain guard, and reset/persistence lifetime law. See [[EXP_2026-08-04_phase4_b_series_closure_audit]] and [[EXP_2026-08-04_phase4_b09_closure_audit]].

## B09 correction - 2026-08-04

| Row | Mechanic | Phase-4 status | Closure |
|---|---|---|---|
| B09 | Super jump | **Substantiated Partial; closure pending** | Blue x4 is statically bound through type `7`/extra `0x4000` -> ctor `0x27` -> action `0x0F` -> `0x800588D4` -> sound `75` -> `0x800588F8` setting `0x20`. Controlled takeoff is `-1344` normal versus `-1696` super under `+256` gravity; the accepted capsule records one grant and 69 super-literal selections across 105 jump checks. Observed law: once obtained, super jump lasts for the rest of the current level and ends only at level completion, stage exit, or game over. `0x8004867C`/`0x800486BC` are structural overwrite sites, not proven post-acquisition clears. Their reachability and exact boundary-reset ownership are reserved for the other agent's Item-2 tool. See [[EXP_2026-08-04_phase4_b09_bounded_exhaustion]] and [[SYS_super_jump]]. ; status override 2026-08-04: bounded-exhausted for this workstream and paused; Item-2 reset attribution delegated |

## ✅ E16 vs item 2 — the packet passes, and the campaign broke two hidden scope walls (2026-08-04)

The earlier verdict on this page — *"item 2 as written is not reachable with
current technique"* — was drawn from three rows stopping on the same static
deficiency. It was right about the deficiency and **wrong about the exit**. The
way through was not a better bound recovery. It was noticing that the frontier
question has a *different* sound answer, and that two of the walls were not walls
at all but holes nobody had measured.

**The operator recorded 16 any% movies** (LEVEL00…LEVEL15, Interpreter,
state-anchored). Validated 16/16 usable, 1,930 events at 60 Hz. The declared
falsifier ran in full, and it immediately earned its keep.

### What the campaign found, and why it mattered more than a clean run would have

`0x80010BF8` in LEVEL01 — a PC touching a marker table that the static frontier
had never predicted. Chasing it broke open **two independent scope holes**, and
neither was visible by inspection:

**SCOPE — the function census covered 90.1% of the resident text.** Every static
figure this row (and every other row) ever produced was computed over the 998
functions in `functions_resident.txt`, leaving **46,360 bytes unanalysed**. The
found PC sits in the second-largest gap.

⚠️ **Corrected 2026-08-04.** This section first said "46,020 of them are live
code", on reachability alone. **20.5% of those bytes are zero words**, and the
largest such gap (`0x8007E8B8`, 13,536 B, 58.6% zeros) sits directly below
`$gp = 0x80081D98` — it is the small-data region, and the transfers "into" it
decode out of data. The defensible figure is **32,144 bytes in 12 gaps**,
majority non-zero. `tools/text_coverage_audit.c` now measures and publishes zero
content so the headline cannot overstate again.

**REPAIRED 2026-08-04** by `tools/repair_function_coverage.c` — a CFG walk from
each entry (fall-through, both branch edges, and the inline `j TARGET ; <delay>`
tables this compiler emits after a computed `jr`), bounded by the next entry in
the *original* listing. **90.1% → 92.8%**, 6 functions regained truncated tails,
0 new entries, 0 overlaps; the emitter goes 724 B → 12,552 B and all 22
hoisted-load PCs now resolve.

⚠️ A first pass read **95.0%**. The census lists **data under function names**
(`contact_metadata_table_a`, `contact_action_dispatch`), and walking one from its
"entry" decodes a table as instructions and wanders through it — inflating the
recovery by **10,312 bytes of pure data**, including a plainly regular lookup
table (`02910fca, 028b0fcb, 02840fcc, …`) and a pointer table of `0x8005Bxxx`
addresses. Guarded now by an instruction-plausibility test with wide separation:
the emitter's real extension scores 0.0% implausible, the data ones 98.3% and
51.4%. What it changed downstream is the whole point:
the affine region census is **byte-identical** (5,810 sites, 827 bounded, same
PC set) and B06's provenance **hits are unchanged at 14** — only the residual
grows (+789 unresolved). The hole cost no findings; it understated residuals.
The repaired list ships alongside as `analysis/functions_resident_repaired.txt`
and is deliberately NOT canonical, because it moves a baseline B06 cites.
`analysis/phase4_coverage_repair_impact.json`. The specific cause is a truncated function —
`0x80010000 724 per_object_mesh_draw_payload_emitter` ends at `0x800102D4`, and
`0x80010C88` is `j 0x800102D4`, the head of the loop containing the access. The
emitter's whole body was missing. → `tools/text_coverage_audit.c`.

**FORM — the affine census is structurally blind to register-based access.** The
access's base is a register, not a `lui` constant. Repairing the function list
would *not* have surfaced it. This looked fatal: pointer-formed access is not
enumerable by an affine scan, which is precisely the ~20,180-unbounded-value wall
recorded above.

### The way through: bound where pointers are BORN, not where they are used

To reach address A deliberately, code must **materialise** A, and on MIPS that is
always a `lui`-based constant. Materialisation sites *are* enumerable — and
unlike the access census, a linear scan of the whole segment is complete over
100% of the text, including the 46 KB the function list omits.

> **no materialisation site ⇒ anything reaching that address is INCIDENTAL**

Scanned against E16's three windows: **5 sites, every one already enumerated**
(2 bare address-takes feeding the loader clears, 3 direct accesses), plus 815
near misses within 512 B — the windows sit among dense neighbours, which is
exactly what an overrun arrives from. **No code anywhere can deliberately form a
pointer into these windows outside the known set.** →
`tools/const_address_materialization.c`.

That is a stronger result than the campaign itself: it is static, and it is a
property of the *windows*, not of any particular PC.

### The find, characterised

The compiler hoisted a load above its own bounds check:

```
0x80010bec  sltu $a3, $t9, $s5     ; range test COMPUTED
0x80010bf0  add  $t9, $t9, $s1     ; base is a REGISTER
0x80010bf4  lhu  $t9, 0($t9)       ; load happens REGARDLESS
0x80010bf8  beq  $a3, $zero, ...   ; range test acted on, one instruction late
```

`$t9` is dead on the failing path (`0x80010C80`). Measured: `0x80010BF8` 53 reads
over 7 levels; `0x80010DA0` — the byte-identical sibling 424 bytes later, which
surfaced only on **LEVEL15, the last movie** — 51 reads across 8 addresses, the
whole 32-byte `0x58..0x5F` table. All read-only.

Finding these one movie at a time is not a method, so the family was enumerated:
**22 sites**, all in the geometry emitters →
`tools/hoisted_load_idiom_scan.c`. They are not a game bug (the result is
discarded) but they *are* a standing hazard for this project's method: they touch
whatever global sits at `base+index` and appear in any `accessLog` watch looking
exactly like an unenumerated consumer. **Expect them in future watch work.**

### Verdict

**NOT FALSIFIED** — 16 levels, 16 movies, 1,930 events, zero unexplained PCs.
The `bounded_residuals` packet now emits **30 entries with zero rejections**
(was 1). The ≥1k remainder is asserted on the same basis the non-negative-index
convention already used: a magnitude argument plus a named falsifier *that has
now been executed*.

**Asserted, not proven — and the artifact says so in its own text.** A replay
shows what DID execute; it can never show an untaken branch would not have
written the slot. Reading runtime silence as proof is the error that produced
this row's original false closure, so the limit lives in the entry, not in a
commit message.

Artifacts: `analysis/phase4_e16_campaign_verdict.json`,
`analysis/phase4_e16_promotion_residuals.json`,
`analysis/phase4_text_coverage_audit.json`,
`analysis/phase4_e16_address_materialization.json`,
`analysis/hoisted_load_idiom_scan.json`,
`analysis/phase4_resident_gap_census.json`.
Gates: `test_text_coverage_audit.py` (7),
`test_const_address_materialization.py` (10),
`test_hoisted_load_idiom_scan.py` (7),
`test_phase4_e16_campaign_verdict.py` (9),
`test_phase4_e16_promotion_residuals.py` (8).

### ⚠️ Read this before trusting any other row's static numbers

The 90.1% coverage gap was **not** E16-specific. Every static census in this
project — region provenance, bound recovery, frontier compilation, the
decompilation campaigns' residual counts — ran over the same function list.
`tools/text_coverage_audit.c` now measures it; re-run it whenever
`functions_resident.txt` changes, because a new CODE gap means new unscanned
text and every residual figure downstream must be redone.

## F04 row status update (2026-08-04)

- **Row:** `F04_cliffside_canyon` -- Stage 4 Cliffside Canyon: dandelion flight + bird hazard.
- **Status:** **substantiated partial / bounded-exhausted; move on**.
- **Roadmap correction:** the former unresolved stage-flow/critical-path gap is closed. The existing v4 full-stage Interpreter movie was replayed at normal speed with post-load instrumentation; scene 6 loaded at relative frame 59, dandelion launch executed at 819, latch 11 remained active from 831 until the intended grounded clear at 3215, and scene 6 exited at 3258. The successful path had zero hits at the D17 contact/death PC and zero post-launch life decrements.
- **Composition:** D17's premature-landing fixture independently proves the complementary bird dive, direct-life-loss, and respawn path. The two controls establish dandelion flight as the successful route and the bird as avoidable punishment for premature floor contact.
- **Static support:** `tools/phase4_f04_route_analyzer.c` matched the six relevant pristine-ASM sites and reduced the untruncated runtime logs; compact result is `analysis/phase4_f04_route_analysis.json`.
- **Evidence note:** [[EXP_2026-08-03_phase4_f04_cliffside_canyon]] (2026-08-04 continuation).
- **Residual boundary:** exact `FUNC_8004ABF4` sub-branch, overlay bit-`0x10` writer, exhaustive pointer/enemy breadth, source closure, and audio/HUD remain recorded but are low-return and do not block F04's named requirement.
- **Canonical registry:** `analysis/mechanics_baseline.yaml` and [[Whole-Game Mechanics Baseline]] were updated in this pass; this is not a note-only closure.
