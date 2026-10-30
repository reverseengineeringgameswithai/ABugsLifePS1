---
kind: playbook
id: PLAYBOOK_phase4_typed_state_compiler
name: Phase 4 - Typed State Compiler
status: accepted
implementation_state: item_2_in_progress_unsigned_interval_increment_fail_closed
created: 2026-08-05
updated: 2026-08-07
overlay_second_opinion: enabled
confidence: high
parent: PLAYBOOK_game_solving_phase_4
depends_on:
  - PLAYBOOK_game_solving_phase_4
  - PLAYBOOK_phase4_frontier_extractor
  - PLAYBOOK_phase4_frontier_closure_workbench
---

# Phase 4 - Typed State Compiler

**Navigation:** [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Phase 4 roadmap]] · [[Phase 4 - Frontier Extractor|Frontier extractor]] · [[Phase 4 - Frontier Closure Workbench|Closure workbench]] · [[Phase 4 - Acceleration Tooling Strategy|Acceleration strategy]]

## The problem it exists to solve

[[Phase 4 - Frontier Extractor]] closed the *authoring* gap: a query can now be
generated instead of hand-written. What it could not do is decide anything about
an access whose **base register it could not resolve to a constant**.

That is the wall F01 hit. The first generated full-extent pass of
`tools/phase4_f01_frontier_resolve.c` resolved 3,681 accesses and left **795
unresolved — 231 of them STORES**. A later extent-set audit added the omitted
`scene_flow_dispatcher` extent, so the current acceptance fixture is **238
stores**. An unresolved store is exactly what a "the writer set is complete"
claim has to exclude, so the resolver fails closed on them and F01's DoD
dimension 2 stays open. Every one of those 238 is either independently excluded
or remains a potential writer of `0x800823A0` / `0x80082470`; none is silently
dropped.

> ⚠️ It was **106** until 2026-08-05, when this work found that 20 of the
> resolver's 29 extents stopped short of the real function end — the ends were
> hand-picked instead of taken from the static index, so **28,252 bytes / 7,063
> instructions inside the censused functions were never read**. Fixing it took the
> census from 1,960 accesses to 3,681 and the blocker count from 106 to 231.
> `resolved_writers_not_previously_enumerated` stayed **0**, so the no-new-writer
> finding survived over the full extents. The lesson is the familiar one: the
> fixture was named after the functions but measured a truncated prefix of them.

Most of them are not mysterious. They are `sw something, disp(actor_pointer)` —
struct field writes through a pointer the constant-propagation pass cannot see.
If the pointer is known to point into a bounded region, the access provably lands
in `[region.start + disp, region.end + disp + width)`, and when that range misses
every watched window **the site cannot reach the state, whatever the pointer's
exact value.** No emulator, no movie, no dynamic evidence — just a bound.

## What ships

```bash
# the compiler (Python: joins, bounds, reports)
tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
    --output analysis/phase4_f01_typed_state.json [--check]

# the ASM verifier (C: reads instructions, answers provenance questions)
tools/phase4_typed_state_provenance.c        # built and invoked BY the compiler
gcc -O2 -std=c11 -Wall -Wextra -Werror -o prov tools/phase4_typed_state_provenance.c
./prov --self-test                            # definition + interval controls, exit 0
./prov IMAGES.txt 'SCUS_942_88:0x8004abf4:0x8004b6dc:s1:0x8004aee4,...'
./prov IMAGES.txt 'writers@SCUS_942_88:0x80090748'
./prov IMAGES.txt 'indexdom@SCUS_942_88:0x800510f0:0x80051294:v1:0x800511d0'

# ABI accelerator query forms (increment 3)
./prov IMAGES.txt 'defsat@SCUS_942_88:0x8004ecd4:0x8004f478:a0:0x8004efd8'  # at a call site
./prov IMAGES.txt 'returns@SCUS_942_88:0x80050994:0x80050c40'               # return typing
```

`tests/test_phase4_typed_state.py`,
`tests/test_phase4_f01_local_base_recovery.py`, and
`tests/test_phase4_index_interval_demo.py` pin the compiler, the F01 consumer,
and the non-F01 reuse measurement.

## The rule the whole design turns on

> **A declaration is not evidence.**

A YAML schema saying "`s1` holds an actor pointer" proves nothing; it is the
artifact under review asserting the thing being checked. That is the failure this
project keeps rediscovering (see [[Phase 4 - Frontier Extractor]], where the
document was choosing its own trust root). So every `region_binding` carries a
**provenance kind**, and the compiler establishes it:

| kind | how it is established | counts as |
|---|---|---|
| `caller_argument` | the **ABI accelerator** reads every caller and recovers the value (below) | proof |
| `typed_pointer_load` | the ASM verifier is **rebuilt from source and run here**; the load relation, every writer value domain, and the complete writer universe must all pass (below) | proof only when every gate passes; **currently rejected** |
| `external_owner` | a named owner accepts it | **assertion**, reported separately, never counted as proof |
| *(second opinion)* | `region_provenance.c`, rebuilt and run on every window | **convention-dependent**, its own bucket |

A binding whose provenance cannot be established leaves its sites unresolved. It
does not degrade to a warning.

### What `typed_pointer_load` actually checks

All six must hold, and all six come from instruction-derived analysis:

1. Every definition of the register that can **reach the sites being bounded**
   loads from one address.
2. That address is the declared pointer table.
3. No site is reachable from the function entry **without passing a definition** —
   otherwise the register arrives holding the caller's value and the local
   definitions govern nothing.
4. The table's **known** writers, enumerated by scanning the whole image, are
   reconciled in both directions against the addresses the static index resolved
   independently. This only corroborates the intersection of two positive
   recognizers; it is not writer-universe exhaustiveness while either recognizer
   has a nonzero residual.
5. Every enumerated writer's written-value domain is proved. A same-table move
   proves only a relation until the table-content invariant is independently
   established.
6. The writer universe is proved exhaustive over a named complete instruction
   universe. A nonzero undecided-store residual rejects the binding.

Two subtleties cost real time and are worth stating, because both look like
bugs and neither is:

- **"Reaching the sites"**, not "all uses". `s1` in `actor_player_contact_resolver`
  has 55 base-uses; judging the binding on all of them let the `lui` half of a
  `lui`/`lw` pair veto a bound that genuinely holds at the 54 sites in question.
  The sites come from the **ledger**, not the schema — a binding cannot pick the
  cases it is judged on.
- **Uniformity is not governance.** The verifier's self-test includes a function
  whose definitions all agree *and* which a branch can bypass. It reports
  `uniform=1 ungoverned=1 bindable=0`. Requiring uniformity alone would mint a
  bound out of nothing.

### The verifier is rebuilt, not quoted

The compiler compiles `phase4_typed_state_provenance.c` with `-Werror` into a
temp dir and runs that binary, reporting the source and binary SHA-256 of the
thing that actually executed. Letting the schema cite an attestation *file* would
put the evidence back under the document's control. Provenance by regeneration —
the same lesson as `compile_frontier`.

The verifier's image map is generated **from the static index**, so the two
analyses can never disagree about where an overlay loads or which overlays exist.
An earlier hardcoded table had 13 of the 21 images and silently narrowed every
scan.

## F01 result (the vertical acceptance test)

```
ledger: 20431 unresolved (8274 stores)          <- the FULL blocker ledger
bounded by PROOF:                219 (95 stores)
bounded by assertion only:         0 (0 stores)
bounded by index CONVENTION:    2769 (973 stores)
still unresolved:              17443 (7206 stores)

ACCEPTANCE FIXTURE unresolved_sites[store]: 238 sites, 141 joined, 97 absent
    bounded_by_proof:               0
    bounded_by_index_convention:   45
    still_unresolved:              96
```

**45 of F01's 238 blocking stores are currently decided**, all by the separately
reported index convention. The 23 stores formerly called proof through
`actor_player_contact_resolver` are reopened by the 2026-08-07 Hard-Truth
ratchet; with 97 fixture sites absent from the ledger, 193/238 remain
undisposed. The 219 ledger accesses still bounded by proof all come from the
independently verified `caller_argument` binding. The first unsigned-interval
candidate's 192 additional ledger proofs are retracted: none survives both RAM
alias exclusion and complete entry-domain closure.

### Instruction-derived unsigned index intervals

`indexdom@IMAGE:START:END:REG:PC` is deliberately row-agnostic. The consumer
supplies the image, extent, register, query PC, table base, displacement, and
watched windows; the C verifier contains no F01 address or row ID. It walks the
delay-slot-correct CFG backwards from the exact point before the TABLE+INDEX
`addu` and admits only these facts:

- architectural zero extension (`lbu`, `lhu`), `andi`, `srl`, a non-aliased
  `sltiu` true edge, and non-negative constants;
- `sll`, `addu`, and non-negative `addiu` compositions only when the tracked
  maximum stays below `2^31` at every step;
- every nearest reaching event must pass. Entry bypasses, signed loads, signed
  add, negative `addiu`, unresolved calls/jumps, dependency cycles, converged
  pseudo-guards, exception transfers, unsupported conditional transfers,
  external interior entries, and every other definition reject.

The MIPS-I load delay is explicit: a scheduled `lbu/lhu` is eligible, while an
immediate consumer rejects at the load instruction because its result is not
yet visible. Calls are clobbers without importing an ABI-preservation
convention. `syscall`, `break`, COP conditional branches, REGIMM conditional
links, and a transfer in another transfer's delay slot are barriers. The
lexical `sltiu` must be the sole dynamic predecessor of its branch, and an
instruction reachable both as a delay slot and as an ordinary target is a hard
barrier. The per-definition derivation tree and exact breaker PC/word/reason are
retained in the result. A `jr ra` remains a terminal function return only while
`ra` is untouched inside the extent; any dynamically reachable local `ra`
definition makes the indirect target unmodelled and rejects the query. This
closes the case where instructions set `ra` to the query PC and re-enter after
bypassing its only definition. A reachable transfer whose architectural delay
slot is outside the declared extent is also a hard barrier: the truncated CFG
cannot silently erase the transfer's successor paths. The C self-test pins 27
positive/negative controls, including direct-jump and conditional-branch
extent-boundary counterexamples.

Consumers additionally exclude every PS1 2 MiB RAM mirror of each watched
window and use a shared exact indirect-transfer closure: 247 sites = 107 jumps
(87 complete, 20 unknown) + 140 calls (all unknown). An unknown domain blocks;
it is never treated as an empty target set. Completeness requires agreeing,
nonempty, validated, duplicate-free exact target lists tied to the decoded
resident site named by those resident-image receipts. An explicit empty list,
malformed scalar/list entry, unverified or malformed catalog, or disagreement
between valid sources remains unknown and retains its external-entry blocker.
A PC-only resident receipt cannot certify an overlay instruction at the same
virtual address.

Image coexistence is derived from the static index's verified load spans, not
from a resident/overlay binary label. Distinct images with overlapping spans
are mutually exclusive; disjoint spans are conservatively allowed to coexist,
and missing or malformed metadata also fails closed to possible coexistence.
This matters because the Region-A level swap span and Region-B `MEMORY.BIN`
span are independent. A Hard-Truth round found that the earlier label-based
predicate omitted 11 `MEMORY` unknown transfers from Region-A extents and one
Region-A unknown jump from `MEMORY` extents. The corrected catalogs retain
those entries. They change no outcome: six typed-state rows remain
external-entry blocked (159→170 entries), five Region-A campaign rows gain 11
blockers each, three `MEMORY` campaign rows gain one each, and all eight
campaign rows still fail earlier in C. The resident non-F01 measurement is
byte-identical because resident code already coexisted with every overlay.

Against prerequisite `b6cb61d35f9d`, the exact movement sets are empty in both
directions for every typed-state category. Proof stays 219, convention stays
2,769, and unresolved stays 17,443. The ledger universe is exactly 20,431 in
both versions with baseline-only/current-only `{}/{}`; the fixture universe and
all fixture category movements are likewise unchanged. Of 1,598 exact
table-address candidates, 1,568 fail in C, 3 retain a PS1 RAM alias overlap,
and 27 reach external-entry closure only after proving an address interval. The
local-`ra` ratchet moves exactly 133 former external-entry diagnostics and 33
former alias diagnostics to `interval_unproved`; no diagnostic moves in the
opposite direction. The artifact records every gained/lost row ID against
`05bc6b8a251b`. In particular,
`fixture:SCUS:0x800511e4:ambient_sfx_sequence_update` no longer has a machine
interval: the query fails closed at `0x8005128C`, word `0x03E00008` (`jr ra`),
because a predecessor path locally defines `ra` and its indirect target is not
modelled. The lexical mask/shift arithmetic remains an observation, not a proof.

The F01 local-base campaign independently tries the same query on all 20 prior
index-sign and six prior return-index walls. It decides zero and refines all 26
to `blocked_index_interval_unproved_instruction`, each with its full query or
an exact external-entry breaker. The 102-row universe and all other outcome
sets are unchanged from the prerequisite. Relative to `05bc6b8a251b`, 20 exact
row IDs now stop earlier at one of five locally-defined-`ra` `jr` instructions;
the full before/after breaker arrays and empty one-sided universe sets are in
the campaign artifact. This zero is a measured result, not a reason to expand
the whitelist.

Reuse is measured on the unrelated resident window
`[0x800A657E,0x800A6580)`. From all 11,352 resident static-index STORE rows, C
rejects 78 stale base/access claims and selects 739 exact table-address-class
stores. The exhaustive interval result is 0 decided, 725 C-unproved, 6 whose
proved range still hits a PS1 RAM alias, and 8 whose address range excludes the
window but whose external-entry domain is not closed. The latter 8 are a
pre-entry-gate diagnostic, not proof. The convention decides 72 on the same
universe (0 both, 0 interval-only, 72 convention-only). The
standalone receipt is
`analysis/phase4_index_interval_non_f01_demo.json`; it explicitly changes no
row status, registry entry, or gate. Against `05bc6b8a251b`, the exact
diagnostic movement is 13 external-entry and 22 alias rows into C-unproved,
with no reverse movement; the receipt embeds all row-ID sets.

### The second opinion, and why it is a separate bucket

`tools/region_provenance.c` predates this compiler and answers the same question
by a different route — abstract interpretation with three tiers of index-bound
recovery. The compiler **builds it from source and runs it** on every watched
window, and reports what it says about the sites this tool could not bound.

Its verdicts are deliberately **not merged into `bounded_by_proof`**. Tiers 2 and
3 rest on the non-negative, loop-bound-checked array-index convention — an
assumption about how the code was written, not something the instructions state.
That is disclosed in its own header and it stays disclosed here.

Three results worth stating:

- **Zero blocking sites are reported as reaching a window.** The check is not
  vacuous: the same run finds 41 hits on `0x800823A0` elsewhere in the image, and
  every one is already in the enumerated writer set. A HIT is escalated in the
  output, never filed.
- **A site must be excluded from EVERY window** to enter the convention bucket.
  Missing one window is not missing the state.
- **It now covers every image, resident and overlay** (see below). Nothing is
  filed as out-of-scope for want of an image.

Two guardrails are honoured explicitly and both are visible in the output:

- **The fixture is not the universe.** The compiler consumes the full
  **20,431-site ledger**. The **238** are an *acceptance fixture* chosen by the
  resolver, not by the schema, so shrinking it cannot flatter coverage.
- **97 fixture sites are absent from the ledger** and are listed in full, never
  counted as bounded. That gap grew from 29 when the extents were corrected, and
  it is itself a finding: the extractor's frontier reaches functions through the
  call graph from a seed, while the resolver scans declared extents, so neither
  set contains the other. They remain the resolver's blockers.

`indirect_control_flow_blockers_untouched` carries the frontier's indirect jumps
through unchanged. **Typing a base says nothing about where control flow can go**,
and a test asserts this count stays non-zero so it can never silently read as
closed.

## The RE finding this produced

Bounding the 19 required actually resolving what `s1` is, which is genuine
reverse-engineering, not bookkeeping — see [[MEM_8009FD80_actor_pool]].

- `0x80090748` is the **actor pointer table** head.
- `mover_updater` (`0x8004D224`) walks the pool: base `0x800A0000 - 640 =`
  **`0x8009FD80`** (lui/addiu `0x8004D248`/`0x8004D24C`), stride **132 = 0x84**
  (`0x8004D3FC`, `0x8004D410`), bound **64** slots (`slti` at `0x8004D41C`),
  publishing each live slot with `sw s2, 0x748(at)` at `0x8004D378`.
- Pool extent therefore **`0x8009FD80 .. 0x800A1E80`** (`64 * 0x84 = 0x2100`).
  Stride and slot count match the Phase-1 chunk-31 registry.
- ~~The table has exactly **4 writers image-wide**~~ ⚠️⚠️ **CORRECTED
  2026-08-06: that was a LOWER BOUND.** The live LEVEL02 replay caught two
  further computed-base writers, and the corrected C query now finds them:
  `0x80049C10` (`sw a0, 0x0(v1)` — moves an existing table value) and
  `0x80049C14` (`sw zero, 0x0(v0)`), in
  `enemy_deathanim_finalize_remove_from_list@0x80049B60` — the table
  COMPACTION on enemy removal (base `a1 = 0x80090748` materialised at
  `0x80049BF4/BF8`, then indexed `addu`). The enumerated set is now **≥ 6**:
  null-writers `0x8003A49C`, `0x8004A4B4`, `0x8004D43C`, `0x80049C14`;
  value-writers `0x8004D378` (publisher, pool slots) and `0x80049C10`
  (moves existing entries). The C recognizer classifies those six but leaves
  **10,995 / 11,001** aligned store-shaped resident words as its explicit
  residual; the independent 21-image window analysis leaves **5,012** stores
  undecided. The set is therefore still a lower bound. `0x80049C14` is proved
  null by encoding; `0x80049C10`'s same-table source relation is proved, while
  its pool∪null domain remains conditional on a table-content invariant and
  writer-universe exhaustiveness. See
  `analysis/phase4_f01_static_hard_truth.json` and
  `analysis/phase4_f01_live_gap_read_receipt.json`.

### Extending the second opinion to overlays

Originally resident-only, because `region_provenance.c` required a `PS-X EXE`
header and read the load address out of it. Overlays are **raw images** with no
header and a load address only the index knows, so it gained `--raw BASE`. The
compiler supplies the base and the function list **from the static index**, never
from a second hardcoded table — the same discipline as the ASM verifier's image
map.

This is where most of F01's movement came from: **12 → 41** fixture stores in the
convention bucket, taking the row from 35 decided to **64**. All 21 images are
analysed; none is unavailable.

Two properties make it safe to believe:

- **An overlay run sees only that overlay.** Its calls into the resident
  executable land outside the image and stay unresolved, so no overlay function
  gets argument seeding from a resident caller. That is the *conservative*
  direction: an unseeded register is TOP, TOP yields no region, and no region
  means no exclusion. Overlay results are weaker than resident ones, never less
  sound.
- ⚠️ **The anchor rule has to survive the new image class.** An *unanchored*
  region — an arithmetic progression whose first element the analyser could not
  prove — may only use Tier 1, because alignment is invariant to which element is
  called the anchor while the negative-index and out-of-bound tiers depend on the
  sign of the index relative to it. The analyser suppresses the stronger tiers
  itself; the compiler now **re-checks it per site and fails closed**, because
  pointing an analysis at a new class of input is exactly when such a rule quietly
  stops holding. Measured: 488 unanchored exclusions, every one alignment-only.

A worked example of why an unanchored base looks wrong but is not — an overlay
memcpy loop at `LEVEL01_LEVEL:0x800B39E8`:

```
lui   a2, 0x800b ; addiu a2, a2, 16212   -> a2 = 0x800B3F54
lw    v0, 0(a2)                          <- excluded, region_base "0x80000004"
```

`0x80000004` is not a claim about where the array starts — it is a **residue-class
representative**, which is all `verified_anchor: false` promises. `0x800B3F54` and
`0x80000004` are congruent mod the 16-byte stride, the target `0x800823A0` is not,
so no element reaches it. The reported base is deliberately carried into the
output alongside `verified_anchor` so this can be checked rather than assumed.

⚠️ **The resident result is byte-identical before and after.** The change is
additive, and that equality is the regression test for it.

## The ABI accelerator (increment 3, DoD dimension 5)

Increment 2's `caller_argument` was not really a check. It counted callers — one
caller meant "single-valued" — and took the **value** from the schema's prose.
Nothing ever compared the claim to an instruction, so a binding could name any
region and pass.

The accelerator replaces that with three questions answered from the ASM:

1. **Is the bound register argument-derived?** It must either BE the incoming
   argument at every site being bounded, or be a **pure copy** of one. The
   verifier chases copies (up to 8 hops, pure moves only, inside one basic
   block); arithmetic is deliberately not followed, because `addiu rd, rs, 8`
   shifts the pointer and a region bound for `rs` would be off by that much.
2. **What does each caller pass?** Every direct caller is read at its call site
   and the constant recovered.
3. **Do they agree, and is the value inside the region?**

This is **wider** than the old rule — many callers are fine if they agree — and
**stricter**: one caller is not enough if the value cannot be recovered or lands
outside the region.

Three things had to be built to make that work, and each was a wrong answer
first:

- ⚠️ **The delay slot is where the argument is set.** MIPS executes it before the
  call transfers control:
  ```
  jal   player_vertical_update
  addiu a0, s0, -144      <- runs FIRST, sets the argument
  ```
  Asking at the `jal` sees the `jal`'s own clobber and answers `call_result` —
  wrong, and confidently so. `defsat@` moves the query point past the delay slot.
- **Constants must be recovered across basic blocks.** A caller materialises the
  pointer once in its prologue and calls thirty instructions and several branches
  later. The straight-line walk gives up at the first merge. `const_at` asks the
  CFG question instead — *do all definitions of this register that REACH this
  point produce the same constant?* — and refuses when a path arrives with no
  definition at all. It runs only as a **fallback**, so results the cheap walk
  already recovered stay byte-identical.
- **"Is this an argument" is point-local.** `a0` is clobbered by every `jal` in a
  function, yet at the prologue copy — before any call — it is unambiguously the
  incoming argument. A whole-extent "is it ever defined" test answers no every
  time.

### What it proves on F01

```
verified: s1 is a pure copy of the incoming argument a0;
          all 1 direct caller(s) materialise a0 = 0x800a6500, inside player_actor
```

Every part of that is now derived: the copy at `0x80048140`, the delay-slot
`addiu` at `0x8004EFDC`, the `lui`/`addiu` pair at `0x8004EF70`/`74` giving
`s0 = 0x800A6590`, and the subtraction to `0x800A6500`.

**The acceptance genuinely depends on the recovered value.** Adversarial probes,
kept as tests: move the region to `[0x800A6600,0x800A6700)` and it is rejected;
move it to `[0x800A6000,0x800A6100)` and it is rejected; point the binding at a
register that is not argument-derived and it is rejected. A caller-counting check
passes all of these.

### It also retired a binding that bounded nothing

The schema used to carry a second `caller_argument` for `a0` itself in
`player_vertical_update`. The ledger has **no a0-based unresolved site** in that
function, so the binding decided nothing — and the old check accepted it anyway.
It is gone, and a test keeps that class of dead binding out.

### The measured yield: zero additional sites, and why

This is the honest result and it is worth stating plainly. Run:

```bash
tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml     --output analysis/phase4_f01_typed_state.json     --survey analysis/phase4_f01_abi_survey.json
```

`--survey` runs the same argument check over **every** blocked group, against the
widest possible region so a group fails only when the value cannot be recovered —
never merely because it lands elsewhere:

| verdict | groups | still-open stores |
|---|---:|---:|
| `not_argument_derived` | 43 | **65** |
| `no_direct_caller` | 2 | 7 |
| `caller_value_not_recoverable` | 1 | 2 |
| **still open** | | **74** |

The residual is counted **per site, not per group**: a group with one bounded
store and nine open ones is nine of residual, not zero. (138 covered = 64 already
bounded + 74 open. The survey counts over ledger groups and the acceptance
fixture counts fixture rows, so the two denominators differ slightly; they agree
on 64 decided.)

**65 of the 74 remaining blocking stores have a base that is locally computed** —
an index, a load, arithmetic — not an argument. Argument typing does not apply to
them, so the accelerator adds no bound. That is a property of the code, not a gap
in the tool, and the survey regenerates it rather than leaving it as prose.

The 7 `no_direct_caller` sites are overlay handlers reached through `jalr`.
Typing those needs indirect-call resolution, which remains an explicit Item-2
blocker this increment does not touch.

### Return typing

`returns@IMAGE:START:END` classifies what `v0` holds at every `jr ra` — the
function's return type, which is what a caller needs to type a `v0` base. It
works and is tested:

- `sfx_dispatch` returns a mix (`materialised_constant`, `table_load`, `opaque`,
  `call_result`) — not uniform, so not typeable.
- `result_upload_anim_frame` returns from table `0x80095138`.
- `memset` (`0x8005F7AC`) has **no `jr ra`** in its extent. That is an *answer*,
  reported as `no_return_site`, not a crash — an early version exited and took
  the whole batch's results down with it.

No F01 blocker is decided by return typing either: the `v0`/`v1` groups are fed
by 15–21 distinct callees each, so requiring them all to return the same region
is hopeless. Consistent with the survey.

## Known limits — do not overread the output

- ⚠️⚠️ **A census is only as wide as its extents.** The whole 106→231 correction
  came from one hand-typed `EXTENTS` table whose ends were shorter than the
  functions it named. The ends are now generated from the static index and the
  table says so. **If a tool declares a scope in prose, check the scope it
  actually walks.** Swept repo-wide in [[Phase 4 - Extent Audit]] — the bug does
  not recur, and a ratchet now catches a new one.
- **The writers scan is a positive recognizer.** It now handles both the direct
  spelling and materialise-then-scaled-index spelling that hid `0x80049C10` and
  `0x80049C14`, but it can still miss a writer whose base arrived by another
  computation or as an argument — the direction that makes an incomplete writer
  set look complete. The compiler cross-checks it against the static index's
  independently resolved accesses and rejects a claimed binding if the index saw
  a store the scan did not, while retaining both residuals explicitly. On
  `0x80090748` the corrected known sets agree exactly (0 index-only writers), but
  the C recognizer residual is 10,995 store-shaped words and the independent
  region residual is 5,012 undecided stores. On a global like `0x800822F4` the
  scan reports 105
  "writers" and is plainly over-broad — it does not model an index add between
  the `lui` and the store. Treat a raw `writers@` count as a lead, never as a
  census, unless the named universe is complete and its residual is zero.
- **An untouched `jr ra` is terminal; a locally redefined `ra` is not.** The
  dominance walk does not resolve a locally computed return target or a jump
  table. Such a `jr ra`, every other unresolved `jr`, and external indirect
  entry domains fail closed as explicit Item-2 blockers.
- **This does not promote a dimension.** `authority.promotes_dimension` is
  `false` and a test enforces it. Bounding sites is *evidence for* dimension 3;
  the promotion decision stays with the closure workbench and a fresh verifier.

## Where the rest are

Superseded by the ABI survey above, which measures this instead of guessing.
Kept because the shapes are still the right way to think about the residual:

- `v0` / `v1` bases — **return values**. Return typing exists now; the callees
  do not agree, so it decides nothing here.
- `s0`/`s2`/`s3` bases — callee-saved copies. Copy chasing exists now; where the
  source is an argument it is typed, and where it is a local computation it is
  not.
- `at` bases — a materialised address with an index add. Resolvable in principle;
  currently classed `opaque` when a join intervenes.
- Several groups have **non-zero `entry_reachable_uses`**, so no local definition
  governs them at all. Those are genuinely caller-dependent and cannot be bounded
  without ABI facts.

What remains after increment 3 is **not** an ABI problem: it is index-bound
recovery for locally computed bases and indirect-call resolution. Extending the
second opinion to overlays — done, above — decided 29 more stores than any ABI
work did, which is the answer to "what should come next" being measured rather
than guessed.

## Increment 4 (2026-08-06): `proved_jr_cluster_argument` — across one proved jr edge

The promoted target-root island `0x8004C898` put two `s0` stores in the ledger
that no within-extent analysis could ever decide: the island's only established
entry is the gate-proved `jr` at `0x8004C868`, so its base register's
definition lives outside the extent by construction. The new provenance kind
propagates the caller's argument domain across exactly that one edge — it is
deliberately **not** a general jr-state propagator.

The chain, every link re-derived per run (see the experiment log for the
disassembly): the pinned jr map proves the edge; the declared cluster
(`0x8004C13C..0x8004D224`, the whole physical interpreter function) tiles
exactly onto contiguous index records with nothing entering its interior; the
rebuilt C verifier's new `island@` query proves the straight-line prologue copy
`addu s0, a0, zero` and that the ONLY other `s0` write in the cluster is the
terminal epilogue restore; the sole caller (`mover_updater@0x8004D5E0`) passes
`a0 = s0` in its delay slot, typed by the same one-load-address/no-undefined-
path/corroborated-writers machinery as `typed_pointer_load` against the actor
pointer table `0x80090748`. Result: the island's two stores are bounded into
`actor_pool` and provably miss both windows — **273 → 275 bounded by proof**,
the exact two IDs and nothing else. The fixture (238 = 23/45/73 + 97) does not
move: the island is not window-touching, so this retires ledger blockers, not
fixture rows.

Two lessons worth keeping from its test suite:

- ⚠️ The unbounded-`jalr` caveat is carried IN the attestation as a named
  residual assumption, not implied: no static evidence excludes an indirect
  call entering anywhere, and that class stays in the ledger untouched.
- ⚠️ An adversarial arm first asserted that a shrunk cluster
  `[0x8004C13C, 0x8004C8AC)` must be rejected — the instructions said
  otherwise (the motion/chase tail never re-enters that range, so the smaller
  declaration is ALSO sound, and the checker rightly accepts it). The suite
  now pins BOTH: real mutations rejected for the right reasons (prologue cut
  off → refuted by instructions; head cut off → entry-integrity), and the
  sound alternative accepted — a checker that only blesses one declaration is
  pattern-matching, not verifying.

### Increment 4a (2026-08-06, review round): REOPENED, gated on writer-universe exhaustiveness

Codex found the chain's two missing links and the island's two stores are back
in `still_unresolved` (proof 275 → 273). What changed:

- **The directly established value facts are machine-proved**: each known
  null-clear by encoding, the publisher `0x8004D378` as an anchored progression
  `0x8009FD80 + k·0x84`, and `0x80049C10` as a move from another entry in the
  same table. The move's pool∪null domain is **not** thereby proved: it requires
  bounded source/destination indices, a valid initial table, every non-move
  publisher preserving the domain, exhaustive writers, and least-fixed-point
  induction. The observability walk's former delay-slot blind spot at
  `0x8004D3FC` is not used as a premise.
- **Entry integrity runs over the census's real universe**: all 21 images,
  all seven successor kinds, jr sources armed; a non-call successor landing at
  cluster.start is an untyped entry. 0 intruders on the corpus; a real-data
  mutation (cluster declared to start at the island) pins the jr-at-start rule.
- **The gate that keeps it rejected**: `table_writer_universe.exhaustive`,
  measured with the region analyser over `[0x80090748, 0x8009084C)` on every
  image — **5,012 undecided stores corpus-wide** could alias the table. The
  corrected C scan now enumerates the two computed-base stores, but the region
  sweep still resolves only `0x8003A49C` and `0x8004A4B4`; exact-set
  reconciliation measures known-writer gain `{0x80049C10,0x80049C14}`, loss
  `{}`, and newly resolved unenumerated writers `{}`. An enumerated writer set
  is a corroborated LOWER BOUND, not a census; closing this gate is Item 2 in
  miniature.
- **Hard-Truth decision (2026-08-07): REJECT the grandfathering exception.**
  Candidate `5e1516a` accepted `typed_pointer_load` while its own attestation
  reported both required predicates false. The prior four-writer premise is
  falsified and cannot remain a proof trust root. Both table-backed binding
  kinds are now gated identically. This reopens all 54 of the binding's ledger
  accesses, including exactly 23 fixture stores: proof 273→219; fixture
  23/45/73→**0/45/96**, with the 97 absent rows unchanged.

## 2026-08-06 hard-truth campaign rerun: real entry edges, no invented jalr sets

The live receipt's `ra - 8` attribution was tested against the instruction
bytes and falsified. `0x8005BFE4` is word `0x0C00E392`, a direct
`jal 0x80038E48`; `0x80058EB8` is word `0x0C0180A1`, a direct
`jal 0x80060284`. Neither PC has a dispatch table or target set to register.
The existing static `jr` sets remain exactly reconciled in both directions:

- `jr v0` at `0x8005C108`: table `0x8001B848`, bound 13, 13 indexed entries,
  10 distinct targets; `seed_plant_trampoline_handler@0x8005C58C` is member 3.
- `jr v0` at `0x80058E78`: table `0x8001B748`, bound 12, 12 indexed entries,
  6 distinct local targets; `berry_tough_damage_dispatch@0x8005905C` is not a
  member. It is entered by direct branches at `0x80058EE8` and `0x80058F08`.

The campaign now consumes exact direct call/jump/branch edges and already-proved
`jr` edges, with delay-slot base writes checked. The Hard-Truth ratchet expands
its universe from 79 to **102** rows: baseline-only `{}`, 79 shared IDs, and 23
current-only `actor_player_contact_resolver` store IDs listed exactly in the
experiment log and artifact. All 23 reduce to direct/indexed loads from the one
table `0x80090748` and stop at `blocked_writer_universe_exhaustiveness`; none is
proof. On the shared universe, exactly seven outcomes move from the `1bba2487`
baseline: berry rows `0x800590E4:s2` and `0x80059150:s2` move from
`blocked_no_direct_caller` to `blocked_writer_universe_exhaustiveness`; seed rows
`0x8005C5B4:s2`, `0x8005C5C0:s2`, `0x8005C5C8:s2`, `0x8005C5D4:s2`, and
`0x8005C5E8:s2` move to `blocked_index_sign_needs_convention`. The tally is now
50 writer-universe, 20 index-sign, 10 no-recovery, 9 return-domain, 6
return-index-convention, 5 stack-entry, 1 external-interior-entry, and 1
nonpositive progression; `blocked_no_direct_caller` is zero.

This is classification movement, not proof movement. No new indirect set is
imported, the gate/registry remain unchanged, the campaign remains staged, and
the corrected writer falsifier remains open at 5,012 undecided stores.

## 2026-08-07 image-span metadata rule

Cross-image entry exclusion is a proof only when both image declarations are
unique and identity-verified and both load spans are well-formed. In Python,
that requires explicit type checks before arithmetic: booleans must not pass as
integers, fractional values must not be truncated, and sizes must be exact
non-boolean integers. Any missing, duplicate, unverified, malformed,
non-positive, or out-of-range declaration means the images **may coexist**.

The retained controls begin with a valid overlapping pair (exclusive), retain
the disjoint and boundary-touching cases as coexistent, and then inject boolean
bases, fractional bases, boolean/fractional/string sizes, and a non-mapping
catalog row. They also replace the top-level index and `images` catalog with
boolean, integer, fractional, string, sequence, and mapping scalars. Every
malformed case must return possible coexistence rather than raise or prove
exclusion. This rule is row-agnostic and applies to every `indexdom@` consumer;
no F01 address or row ID is embedded in the C prover.

## 2026-08-07 extent-boundary and target-domain ratchet

Detached Hard-Truth round 6 rejected candidate `2eb2f8332b12`. Two controls
exposed false closure: a final in-extent `j` or conditional branch had no
modelled delay slot and therefore lost a real re-entry path, while an explicit
empty `site_targets` list was accepted as a complete empty domain. A third
contract defect made malformed top-level image catalogs raise instead of
returning the conservative coexistence result.

The shared rules above are the repair. Public-query tests retain both boundary
words (`0x08004001` and `0x1000FFFD`) with the exact breaker reason
`control_transfer_delay_slot_outside_query_extent`. Mutation tests inject empty,
null, boolean, numeric, string, invalid-address, and duplicate-target domains at
the real `LEVEL07_LEVEL1:0x800B3FCC` site and require the `MEMORY` external-entry
blocker to survive. The complete focused suite is 82 tests. These controls move
no campaign outcome or breaker, typed-state bucket, fixture bucket, or non-F01
demonstration-site outcome relative to the rejected candidate; they remove
ways malformed or truncated input could have minted a future proof.

## 2026-08-07 conflicting target domains fail closed

Detached Hard-Truth round 7 rejected candidate `aac3a336719c`. It reproduced
the retained counts, raw instruction words, movement sets, 327/327 pristine
pins, inventory identities, and bounded DAG, then injected two individually
valid but different target lists. `_indirect_transfer_closure` raised
`TypedStateError`; the acceptance contract requires an unknown domain and a
retained blocker instead of aborting the audit or selecting one source.

Commit `29ef16ee2afa` makes incompleteness sticky across sources: empty,
malformed, duplicate-PC, unverified, and conflicting rows clear any accepted
domain. Target-map identities are now `(resident image, PC)`, matching the
artifacts' resident-image provenance, so inserting a valid or conflicting
PC-only row at `LEVEL07_LEVEL1:0x800B3FCC` cannot certify that overlay site.
The real resident `SCUS_942_88:0x8001CAC4` conflict changes its synthetic
control from complete to unknown and retains a new `MEMORY` blocker (160→161);
the overlay conflict retains the existing 160-entry catalog and its own
blocker. The focused suite is 84 tests.

No retained semantic outcome moves: 247 transfers remain 87 complete jumps,
20 unknown jumps, and 140 unknown calls; the campaign, typed-state, fixture,
and non-F01 partitions remain the counts above. Commit `343e5b072158` carries
the clean detached inventory re-pin: campaign inventory `be3e68cc…`, bounded
DAG `c44d4e2c…`, and exact consumer fingerprints `a3f98c60…`, `c61414a3…`,
and `79dba1a9…`. This is still a pre-acceptance record; it does not authorize
banking without a later detached `agreed` verdict.

## 2026-08-07 table-base proof is separate from index proof

`TABLE + INDEX` has two independent proof obligations. A valid unsigned
interval for `INDEX` cannot rescue a table constant recovered only by lexical
proximity. The C classifier must prove that its named constant operand has the
same value at the forming `add/addu` on every modelled reaching path, and the
consumer must require both `table_base_register` and
`table_base_proof=all_reaching_definitions_same_constant` before it submits the
other operand to `indexdom@`.

The permanent negative control branches directly to the forming `addu`,
bypassing the only `lui`. The index still proves `[0,63]`; the table base fails
at the `addu` with `table_base_operand_not_path_invariant`, and the full typed
consumer must retain the convention classification. The paired positive has a
dominating `lui` and retains the exact table, constant-register, and
index-register fields. This is an under-claiming ratchet: the strengthened
check requires both the former same-basic-block recovery and the new
all-reaching-definition agreement, so the repair cannot gain a site merely by
using a more permissive constant engine.

Image-lifetime exclusion has the same fail-closed shape. Every catalog image ID
must be a unique nonempty string; malformed or duplicate IDs mean the images
may coexist. The focused regression suite is 86 tests, including public C and
full-consumer table-base controls. No retained campaign, ledger, fixture, or
non-F01 outcome moved, and no Canon index claim was added because zero table
indices became proof.

## 2026-08-07 shared CFG rule for TABLE and INDEX

The table operand and the unsigned index operand must use the same fail-closed
control-flow context. It is unsound to accept TABLE under a lexical or weaker
constant walk and reject INDEX under a stronger reaching-definition graph. The
shared C barrier now rejects, for both obligations:

- a direct jump or branch whose delay-slot word lies outside the query extent;
- an unresolved indirect jump that may enter the extent;
- a locally defined `$ra` return whose target is not modelled;
- a transfer in a delay slot, syscall, break, or other unmodelled transfer
  class already rejected by `indexdom@`.

Entry `$gp` is just another reaching constant fact: a local write kills it, and
only an all-reaching-definitions proof may establish the later value. Likewise,
an unknown indirect transfer is internal only when its source image identity
equals the target image identity; numeric PC overlap across images is never an
exclusion proof.

The permanent controls are paired at C and consumer level: entry-`gp` accepted,
locally overwritten `gp` rejected, truncated jump rejected at word
`0x08004004`, unresolved `jr` rejected at `0x01600008`, same-numeric-PC transfer
from another image retained as external, and failed TABLE evidence propagated
to the row without discarding coexisting writer/value-domain blockers. The C
self-test is 33 controls under `-Werror`; the focused consumer suite is 88
tests.

This stronger rule intentionally under-claims. In the current measured corpus,
the typed exact-table diagnostic universe falls from 1,598 to 127, with 2,642
base-classification failures (1,708 rows / 1,721 exact failed definitions).
Those 127 partition as 97 interval-unproved, three overlap, 27 external-entry,
and zero upgrades. The F01 campaign's 102 rows partition as 52 exact interval
instruction failures, 26 writer-universe, nine return-domain, eight no-
recovery, five stack-entry, one external-entry, and one progression failure;
zero are decided. The second-window receipt at `[0x800A657E,0x800A6580)`
measures 124 strict table-address-class stores as 0 decided / 110 unproved / 6
overlap / 8 entry-unclosed, while convention decides one of the same sites.
This is capability measurement only, not a promotion.

The two table-backed bindings remain rejected with both gate bases present:
5,012 undecided stores across 21 images leave the writer universe
non-exhaustive, and the value-domain induction remains unproved. No rule may
drop those measurements merely because the shared TABLE/INDEX barrier now
finds an earlier failure. No Canon table-index fact is added when the measured
upgrade set is empty. These repairs are retained in commits `36e0e48c8614`
through `127b7d39974a`; regenerated receipts and the bounded DAG are checkpointed
at `3bb215673887`. They remain pre-acceptance until a fresh detached verifier
returns exactly `agreed`.

## 2026-08-07 ORI semantics and the two call-delay phases

Constant recovery follows instruction semantics in program order. In
particular, `ori rd,rs,IMM` is `rs | IMM`, never `rs + IMM`; overlapping low
bits are a required positive control. A TABLE proof and its consumer must agree
on the resulting exact base, so an invented larger table cannot turn a watched-
window overlap into an exclusion.

A call delay slot has two distinct observation points:

- `defsat@...:CALL_PC` asks what the callee receives. Its synthetic boundary is
  after the delay slot and before the first callee instruction, so a delay-slot
  argument definition is visible there.
- an ordinary query after the return asks what the caller may use at the
  continuation. Caller-saved registers are clobbered there, including a value
  written in the delay slot before control entered the callee.

Never use one phase to answer the other. Call-boundary constant sources require
all reaching definitions to agree, reject `$ra` link-value dependencies, and
reject when the post-call continuation can flow back to the same static call.
The latter prevents one CFG node from standing simultaneously for the current
pre-callee boundary and a prior invocation whose callee clobber has already
happened.

Permanent paired controls now require: overlapping ORI returns `0x800823A0`;
the call continuation rejects at the owning `jal`; the call boundary recovers
the synthetic and real F01 argument `0x800A6500`. The C self-test is 36 controls
under `-Werror`; the focused suite is 90 tests. The intermediate over-broad
repair that reduced proof rows 219→0 was caught during clean regeneration and
was not allowed into a receipt.

At receipt commit `05421715495e`, all exact typed, campaign, fixture, and
second-window semantic site sets are unchanged from the preceding shared-CFG
measurement. The C source identity is `8686805e…`; typed state is `3eded114…`;
the campaign is `95538c79…`; the non-F01 receipt is `4d2888c1…`; the bounded
DAG is `0688d69b…`. The 102-row F01 campaign still decides zero sites, the
124-site second-window receipt still decides zero by interval and one by
convention, and no Canon table-index fact is added. Hard-Truth round 11 was
externally interrupted after finding the ORI/call counterexamples and emitted
no terminal verdict; these repairs therefore remain pre-acceptance until a new
fresh detached verifier says exactly `agreed`.

## 2026-08-07 architectural link writes at call boundaries

Call-boundary analysis must retain the architecture's link definition. A
direct `jal` defines register 31 and `jalr rd,rs` defines its nonzero `rd` as
`call_pc + 8` before the delay-slot instruction observes its sources. Hiding a
targeted call's ordinary caller-saved clobber must never hide this real write.

The current helper deliberately does not model the numeric link value as an
interval or constant. Therefore a query of the link destination, or a
delay-slot argument derived from it, fails closed as
`call_link_value_not_modelled`. This applies to arbitrary JALR destinations,
not only `$ra`. A source-dependent continuation that re-enters the same static
call is likewise rejected because one CFG node cannot distinguish dynamic
invocations. A direct constant-producing delay-slot instruction remains valid:
its result does not depend on an earlier invocation.

Permanent C controls cover JAL and JALR link-source rejection, preservation of
the call-link definition, source-dependent re-entry rejection, and direct
delay-slot `lui` acceptance. The end-to-end control exercises the public query
and both temporal phases. The shared C self-test is **41 controls** under
`-Werror`; the focused suite is **91 tests**.

Hard-Truth round 12 independently found the stale-link counterexamples in
candidate `1e0520224646` and correctly returned `unverified`. The repair is
checkpointed at `b9549d48a8cc`; regenerated receipts and their bounded exact
pins are checkpointed at `e15800e4bc76`. No semantic bucket moves: F01 remains
zero interval-decided across 102 campaign rows, and the second-window receipt
remains zero interval-decided across 124 strict sites. No Canon fact is added.
The repair remains pre-acceptance until its own fresh detached hard-truth run
returns exactly `agreed`.

## 2026-08-07 unsigned-interval ratchet accepted

Fresh detached Hard-Truth round 13 audited candidate
`4af34dbb656fe744c247df54d4a731baa7fd51d4` and returned exactly `agreed`,
`banking_authorized=true`, and `gaps=[]`. External prompt / schema / log /
verdict SHA-256 identities are
`39cd7889af7126515c1477e78db2bd324b31779ec79b0baa7b15f5ceeb008b4d` /
`c248873a4cd14c78db0ba6f365e226f41903c74e6c1594b85d4c8bb0febd6a43` /
`fdaf3b8e9427d27bd283ac509585c7fc3779801ba0b0a79cb4a3e668de119ae2` /
`b9fa148c20f23c98c6c316055166d94abb9f32c2405d7e367127d4d15952cd29`.

This banks the row-agnostic prover, shared TABLE/INDEX fail-closure, call-link
repair, regenerated receipts, and measured second-window result. It does not
promote F01 or the demonstration row: F01 remains `partial`, item 2 remains
`not_met`, both review booleans remain false, and the blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The zero-upgrade result
still adds no Canon table-index fact.

## 2026-08-07 caller-domain pilot rule: classify before propagating

The mandatory fixed 20-site pilot for interprocedural caller domains returned
**NO-GO: 0 proved / 20 absent**. The sample was committed before its outcomes;
both the primary probe and an independent minimal C implementation agree on
every site. The result is a reviewed negative: do not run a full caller-domain
fixpoint while this sample remains below the three-site threshold.

The exact failure partition matters:

- 10 sites: `open_caller_set_poison` (all five stack-entry rows and all five
  sampled `SCUS_942_88` argument-fed rows);
- two sites: the store itself is a `jal` delay-slot instruction, hence
  pre-callee and categorically not a return-domain observation;
- three sites: an alternate fallthrough entry reaches a return derived from
  unproved `$s0`;
- one site each: local replacement of the argument register and a local-frame
  slot misidentified as a stack argument;
- three sites: local signed loads, not caller arguments.

This adds a permanent temporal rule beside the existing call-boundary rule:
**a store in a call delay slot observes the pre-callee phase.** Do not classify
its caller-saved source as a call result merely because the instruction is
lexically adjacent to a `jal`. Likewise, prove entry structure before calling
an `sp+offset` load a stack-passed argument; offsets within a locally allocated
frame remain local until proved otherwise.

The 50-capsule set was validated, but with zero proved domains its comparison
is `NOT_APPLICABLE_NO_DECIDED_DOMAINS`, never “clean by vacuity.” Exact movement
sets are empty for fixture, ledger, and campaign; the retained reference counts
remain 68/238 fixture stores decided and 5,012 corpus stores undecided. No full
Stage-A census, Stage-B propagation, or Stage-C repin was performed, and no
Canon entry or F01 promotion follows.

A permanent integration rule follows from the NO-GO stop: sample-only
machinery must not invalidate a full-corpus consumer and then force that
consumer to regenerate. The pilot initially changed `region_provenance.c`,
which made two typed-state freshness checks fail solely on the source/binary
identity pins. The accepted repair restores that shared analyser byte-for-byte
and keeps the unauthorized sample probe in
`phase4_caller_domain_probe.c`; 97 affected tests then pass. Stage-B domain
propagation still belongs in the shared analyser only after a future GO.

Pilot receipts must also load derived inputs from their named committed
snapshot, not the operator's ambient `analysis/` tree. A detached check caught
this pilot reading unrelated dirty gate WIP; pinning every derived input to the
pre-outcome commit made the expanded affected suite 106/106 without moving a
single site classification.

### Caller-domain pilot accepted as a reviewed negative

The fresh detached Hard-Truth verifier for candidate `7efef21d1cae` returned
exactly `agreed`, `banking_authorized=true`, and no gaps. It independently
reproduced the fixed-before-outcomes 20-site universe, exact wall partition,
NO-GO arithmetic, protected-state comparison, both C builds, 327 input pins,
byte-identical receipts, and 106 tests. This accepts the negative measurement,
not caller-domain propagation: the next permitted increment remains proving
indirect-table and address-taken universes before re-running the same pilot.

The next Phase-4 vertical is therefore **indirect-table and address-taken
universe proving**. Re-run the same fixed pilot after that prerequisite moves;
do not widen the domain whitelist or collapse its precise local/temporal walls
into the OPEN bucket to manufacture progress. The detailed site table and
receipt hashes live in the F01 objective-lifecycle experiment.

## 2026-08-07 address-taken pilot rule: an OPEN witness is not an occurrence

An unresolved indirect-transfer witness and an address-taken occurrence are
different evidence classes. A “first unproved `jr`/`jalr`” field says only
where target-domain reasoning first stopped; it does not say that a named
function entry is stored at that PC, nor that the PC is a data cell. Before
starting table consumer or writer recursion, require all three identities:

- the address belongs to data rather than code;
- the aligned word equals the named function entry; and
- the containing region/extent is proved.

If any identity fails, recursion depth is zero and the witness cannot close the
root. Conversely, bytes in a pinned data range must never be decoded as control
transfers merely because their low six bits spell `jr` or `jalr`. The fixed
four-root pilot caught exactly this integration defect: the earlier caller
probe treated all 1,191 frontier records as functions even though they
partition as 1,059 code, 54 thunk, and 78 data ranges. Correct code/data masks
remove 77 / 77 / 80 / 82 data-decoded edges from the four root-specific
supersets, with zero additions. Full exact sets live in the pilot receipt.

The corrected Stage-A sweep is C-owned and has an independent C implementation.
It covers every aligned word of all 21 images plus code-only `lui/addiu` and
`lui/ori` materialisations. Its exact result is zero occurrences for the three
overlay roots and one resident occurrence, table slot `0x8001B854` in proved
extent `0x8001B848..0x8001B87C`. Membership is not itself an edge: consumer and
selection proofs remain mandatory, and table slots count as occurrences even
when several contain the same handler.

A local index/address proof is also narrower than a gate-grade target-set
proof. At `MEMORY:0x800B970C`, `sltiu` plus the bypass branch proves index
`a0 ∈ [0,7]`, the `sll` proves four-byte stride, and the post-guard load selects
exactly `0x800B57B4..0x800B57D4`. The hoisted-load control is clean. Until the
region's complete reader/writer universe is proved, however, static slot values
are only enumerated; they do not authorize a closed target set.

The frozen pilot therefore returns **NO-GO, 0/4 roots CLOSED**. Recursion reaches
depth one for the two MEMORY roots and zero for the two false data-cell
premises. The corrected gate-grade residual is 178 / 178 / 178 / 179 sites.
Do not re-run caller-domain propagation or the full corpus census on this
result. The replacement argument is a complete per-site target-domain/exclusion
proof over the corrected code-only indirect-transfer universe, with whole-table
value-domain invariants for table-backed sites. F01 does not move, and this
rule remains pre-acceptance until a fresh detached Hard-Truth verdict says
exactly `agreed`.

### Address-taken pilot accepted as a reviewed NO-GO

The fresh detached Hard-Truth verifier for exact candidate
`d7bb785e4c0dd4950a6dcf7f736b1bb15763b74b` returned exactly `agreed`,
`banking_authorized=true`, and `gaps=[]`. Its prompt / schema / log / verdict
SHA-256 identities are
`36f57e49b7465cccd096f5729c108ecb2e257c0aa64c44e9461b47d04b79e972` /
`c248873a4cd14c78db0ba6f365e226f41903c74e6c1594b85d4c8bb0febd6a43` /
`936f45d2b94664a71ed2c0de7dc00818efeb68138eb7256d431e74762f7f0908` /
`555a7a8816481da1cee88a35e00ae47318afce423992db4025a7103ab146f55c`.

This acceptance banks the negative measurement and the corrected code-only
universe, not any root closure. Keep the frozen caller-domain pilot stopped:
the next permitted argument is complete per-site target-domain/exclusion over
the corrected `jr`/`jalr` universe, with whole-table value-domain invariants
for table-backed sites. No baseline, gate, registry, Canon, F01 status, or row
promotion follows from this receipt.

## 2026-08-07 target-domain rule: reachable definitions in both directions

An exact indirect-target domain is the union of every value produced by an
entry-reachable definition that can reach the named `jr`/`jalr` without being
overwritten. Both reachability directions are mandatory. A lexical constant
that could flow forward to the transfer but cannot itself be reached from the
declared entry is dead bytes, not a target. The target-exclusion pilot caught
that exact trap at `0x800188EC`: `ori s6,s6,0x961C` spells
`0x8001961C`, but execution reaches the preceding `j` and its delay slot, not
that definition. Excluding it reduces all four computed pilot domains to the
same exact set `{0x80018CC4, 0x80018F4C, 0x80019244}`.

Use the standalone C prover `tools/phase4_target_exclusion_prover.c` with query
`IMAGE:START:END:REG:PC`. It fails closed on an entry path without a definition,
a load without a whole-table value invariant, an unproved source register, a
call crossing, an unsupported definition, or a disagreement between its
lexical and CFG constant evaluators. It records every definition occurrence and
exact instruction chain; repeated target values do not collapse occurrences.
Consumers must apply external-interior-entry exclusion before calling such a
domain gate grade. A separate C implementation must re-derive pilot
classifications and local domains directly from the bytes using a different
dataflow direction. Both CFGs must distinguish ordinary branch delay slots
from branch-likely annulment: taken likely edges execute the slot, while
not-taken edges go directly to PC+8. Conditional-link edges cross a call and
coprocessor conditional branches remain explicit control flow. A stopped
NO-GO pilot must not force a repin of the accepted shared typed-state analyser.

The frozen 12-site pilot produces four matching entry-scoped local domains and
eight direct instruction/domain walls. The four local domains are **not landed
proofs**: the accepted entry gate supplies 156 unresolved possible interior
sources and the convention-free corrected union adds 19, leaving an exact
175-source entry wall (174 external, one internal). Each of the four therefore
gets its own gate-grade wall, for twelve attempted walls and 0/12 landed.

This is **NO-GO** by the explicit `<=3` clause. The ascending-PC sample also
contains zero table-backed sites and retained capsules/sessions contain no
source-site/target tuple, so the other GO clauses fail independently. Do not
mutate the gate/index or start the caller-domain cascade. Local proof-basis
movement is four sites / 12 edges; candidate gate-grade movement and applied
movement are both empty. The accepted gate remains 87 sites / 492 edges.

The measured residual passed to the item-2 bar is all 179 corrected sites: 74
table/cell candidates plus 105 sites in the other strata. The 50 capsules and
preserved u3 entry watches provide zero direct source-site/target observations
for that residual. F01 stays partial with its two blockers. The full exact sets,
twelve walls, runtime semantics, entry-source set, and no-hedging bar price live
in the F01 objective-lifecycle experiment and
`analysis/phase4_target_exclusion_pilot.json`; no recommendation to lower the
bar is encoded.

### Target-exclusion pilot accepted as a strict NO-GO

The fresh detached Hard-Truth verifier accepted exact candidate
`e5d6ea71ac2fda59815cbc61a381486f7fa118a8` with `decision="agreed"`,
`banking_authorized=true`, and `gaps=[]`. It independently reproduced the exact
261 -> 179 corrected universe, 74/19/6/0/9/38/33 partition, 128-member protected
union, four three-target local bases, 175-source entry wall, twelve attempted
walls, and empty gate movement. Fresh validation also passed both C control
suites (9/9 and 8/8), 327/327 pristine identities, the 136/136 affected suite,
and an empty detached status. Prompt / schema / log / verdict SHA-256 identities
are `5f98482e947eeefef10668eb2f827afba6cdc52d26ae54416a6043e0ffe8af1f` /
`e331ac11d9a5d0840113564a9cc8617d8b87ee16135246ca74057d5e67abfbe1` /
`6f84d831c186f391b40c14fbda303ee47ca10b80c5622cad217cdae61cdc5fe8` /
`d272bb82301dba50f02260437ec2f9d6d3f99492eb217e9e13c1f8db34fb0307`.

Bank only the negative: 0/12 gate-grade proofs landed, all 179 corrected sites
remain, runtime cross-check support is unavailable, and the accepted gate stays
87 sites / 492 edges. No table invariant landed, so Canon remains unchanged.
Do not start the stopped cascade or move F01; it remains partial with item 2
`not_met`, both review booleans false, and its two blockers unchanged.

## 2026-08-10 D3 contract rule: exclusion still requires universal membership

A protected-set exclusion can avoid enumerating the exact destinations of a
pointer dispatch, but it cannot avoid proving what values are allowed into the
dispatch region. Gate grade therefore requires both predicates, in order:

1. prove the complete byte extent and writer/value invariant (or a named,
   bounded exception set); and
2. prove that universal membership set disjoint from the frozen protected set.

Known writers, pristine slot contents and retained target observations are
lower bounds. They can falsify a proposed domain and can demonstrate candidate
disjointness, but they cannot make predicate 1 true. This is the explicit
immunity rule carried forward from `0x80018CBC`, where a fourth target omitted
by confident static analysis handled more than 80% of the observed dispatches.

The frozen 12-site D3 contract pilot lands **0/4 contracts and 0/12 sites**;
the indirect residual remains **179 → 179**. Its four walls are all
technique-shaped, with exact prerequisites:

- shared cell `0x8007FBC4`: close 4,266 undecided possible stores (2,244
  full-width) and their value domains; the byte-proved `SetDumpFnt → FntPrint`
  store is only one known safe writer;
- object field `+0x7C`: build field-sensitive actor typing and writer closure;
  retained observation and the ABI ledger's 1/867 known argument domains do
  not supply a universal field domain;
- BIOS `B0`: join the entry-scoped immediate proof to a whole-program
  ingress/vector contract; never generalize it past unknown interior entry;
- dynamic modules: join loader bytes to per-transfer residency identity.
  `0x800CABE0` is observed as an out-of-census frontend target but is data under
  pinned `FMV.BIN` residency, so the address alone cannot name the module.

This negative leaves a technical avenue only through one of those new
prerequisite engines. It does not authorize another target-enumeration pass,
gate/index movement, or F01 promotion. The deterministic receipt is
`analysis/phase4_d3_contract.json`; full per-site words and evidence live in
the F01 objective-lifecycle experiment.

### D3 reviewed negative accepted

Fresh detached Hard-Truth review accepted exact candidate
`619cac8d604f55cb4230fa7e7fe668c53dad4ac7` with `gaps=[]` and no required
inputs. Independent reproduction confirmed 327/327 pristine identities, all
12 byte witnesses, 21/21 region scans, the exact protected/runtime arithmetic,
34/34 focused tests, a clean detached status, and byte-identical post-commit
extent output. Bank only the **0/4, 0/12, 179 → 179** negative and its four
technique-shaped prerequisites; no F01 status or gate movement follows.
