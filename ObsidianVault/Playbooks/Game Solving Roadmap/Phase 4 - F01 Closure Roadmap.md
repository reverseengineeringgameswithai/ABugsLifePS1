# Phase 4 — F01 closure roadmap

Written 2026-08-10. Purpose: F01's remaining work has been asked about
repeatedly and re-derived each time. This is the standing answer — every
dimension, its method, the tooling that already exists, and the order to run
them in. **Nothing here is new research; every dimension has a known method.
Exactly one of them can genuinely fail.**

Authoritative state: `analysis/mechanics_baseline.yaml` → row `F01_anthill`,
field `dod_scorecard`. **4 of 9 dimensions met (measured), as of 2026-08-11** —
`durable_evidence`, `original_oracle`, `complete_frontier`, `lifecycle`, each
promoted by an independent fresh detached verifier. Re-read it before trusting
this page — the scorecard moves, this page is a plan.

---

## 0. Infrastructure blocker — ✅ CLEARED 2026-08-10

`tools/phase4_closure_debt.py --write` returns `PASS: rows=16/107
dimension_met=149`, `valid: true`, **stable across consecutive runs** (`3d74f34`).
A dimension can now be promoted the moment one is earned.

History, because it broke twice and the second break was self-inflicted. The
original 7 evidence errors were repaired at `fc772a0`. Then `539ba8a` (the
LEVEL02 re-pin the operator confirmed, plus 16 previously-unpinned E10 fixtures)
legitimately changed two artifacts and staled four assertion sha256 pins in
`config/phase4_campaigns.yaml`, which blocked the ledger again — and the ledger
gates *every* dimension, so one careless artifact regeneration froze the whole
board.

⚠️ **Two rules earned there.** Before re-pinning a gate, establish both that the
pinned hash genuinely existed on this branch (decayed provenance, not a phantom
pin — [[EXP_2026-08-05_phase4_f01_objective_lifecycle#2026-08-10 — closure-debt blocker DIAGNOSED 5 of 7 errors are phantom pins, 1 is real debt|pin mismatch is not drift]]) and that every predicate still holds
on the new bytes; here all four did (`missing_central_pins`,
`tracked_python_untracked_imports`, both `external_local_media_*`), so nothing
was weakened. And **regenerate to a proven fixed point before recording a hash**
— the first re-pin attempt failed because the artifact was still settling, so
the hash was stale on arrival. `phase4_closure_debt.py` also needs `--write`;
bare it validates and prints PASS without writing.

---

## 1. The nine dimensions

> ⚡ **2026-08-10, read first:** the measurement standard is now ruled
> (`engineering-specs/phase4-measurement-standard-ruling.md`) — per-dimension, against
> the bars **as written**, uniformly. F01 re-assessed under it:
> `analysis/phase4_f01_written_bar_assessment.json`, since ADJUDICATED: **4 met**
> (durable_evidence, original_oracle, complete_frontier, lifecycle — registry
> commits 76273fd0 and eb42bea6), **3 partial** (typed_state, cross_system,
> source_closure), **2 not_met** (original_interfaces, campaign_breadth).
> The per-dimension entries below predate that assessment; where they disagree, the
> assessment is newer.

Effort labels are the assistant's judgement, not measurements.

### ✅ MET — `durable_evidence`
Nothing to do.

### 🟡 PARTIAL (claim registered) — `original_oracle`
**Current defect (quoted):** `analysis/phase4_f01_finalizer_witness.json` is a
causal witness for ONE branch condition (request==2 suppresses the finalizer),
not a row-wide oracle — the anchor is a validated save state rather than a
pristine cold boot, the value 2 is **injected** rather than produced by
gameplay, it covers one branch of four declared observation leaves, and the
raw arm receipts are not in the central preservation index. The claim is
deliberately `partial` so it cannot auto-promote.

**⚠️ SUPERSEDED 2026-08-10 — the recording was delivered, the oracle was built,
and it was adjudicated NOT MET on three named elements.** Two are now repaired;
one is blocked.

The operator recorded `Any% Runs/LEVEL01_AntHill_FromBoot.movie.json` (genuine
cold boot, v4, 7,385 frames). `tools/phase4_f01_original_oracle.py` observed all
four leaves during a natural completion with nothing injected — request **1**
produced by gameplay, `[0x8008225C]` 0, finalizer 28 cycles later. A fresh
detached verifier reproduced every semantic observation across 2/2 replays, then
rejected the dimension anyway:

| element | state |
|---|---|
| `fail_closed_oracle_provenance` | ✅ DONE — provenance derived not assumed, movie centrally pinned |
| `fresh_detached_oracle_regeneration` | ✅ DONE — checkout-independent identity, byte-identical detached |
| `natural_request2_skip_control` | 🔴 **BLOCKED** |

**The one blocker:** the skip arm's request 2 is *still* injected. A natural
request 2 comes only from death (`a3≠0` stores it unconditionally at
`0x8004A9F4`). The two other from-boot movies were replayed to rule out a cheap
path — **D18_thud_fight 15,600/15,600 frames, 1 decision, request [1], 0 death
stores; E02_FreshLoad_Clover 5,562/5,562 frames, 0 decisions** — so neither
supplies it.

**Needs:** one operator recording — a **cold-boot movie in which Flik dies
naturally**. That single fixture closes the dimension.
**Effort:** low once the recording exists.

### 🟡 PARTIAL — `typed_state`
**State:** 95 stores bounded by proof; 973 bounded by index convention (which
does not count as proof); 7,206 stores still unresolved.
**Method:** the typed-state compiler plus caller-dependent value resolution —
**the same wall as `complete_frontier`**, so the discipline campaign moves this
dimension too if it lands.
**Tooling:** `tools/phase4_typed_state.py`, `tools/region_provenance.c`.
**Effort:** heavy, but shares its cost with the frontier work.

### 🟡 PARTIAL — `lifecycle`
**Dimension:** cold boot / load / first use / repeated use / exhaustion /
retirement / reuse.
**Method:** movies covering each phase + assertions.
**Tooling:** harness + corpus + `phase2_lifecycle_oracle.py`.
**Effort:** low–medium. **Needs:** a few targeted recordings.

### 🟡 PARTIAL — `cross_system_behavior`
**Dimension:** native combinations — carry+damage, powers+jump, projectiles at
transitions, enemies vs hazards/plants.
**Method:** targeted clips + assertions; the Interpreter behavior library
already covers part of it.
**Effort:** medium. **Needs:** a handful of recordings (overlaps the standing
hazard/damage re-record list).

### 🟡 PARTIAL — `source_closure`
**State (measured 2026-08-10):** `FUNC_80038F38` is byte-matched; the
**6,004-byte player updater is not**. The retained compile is 6,012 bytes and
matches **56/1,503 word positions (3.7%)**; 1,447 positions differ, including
two compiled-only words. This is an honest first-draft fraction, not an exact
near-miss. See
[[EXP_2026-08-05_phase4_f01_objective_lifecycle#2026-08-10 — source_closure verified: honest measurement, INFLATED label (3.7% match)]].
**Method:** the decompilation campaign toolchain — hand-asm generation, GCC
2.7.2 `-O2 -G0 -mcpu=3000` + maspsx `--dont-expand-li`, byte-comparison against
the image (see [[EXP_2026-07-08_psyq_compiler_proof|PSYQ compiler proof]], [[EXP_2026-07-09_decomp_v5_bytepercent|decomp v5 byte percentage]]).
**Effort:** heavy but well-precedented — 968 functions have been byte-matched.
⚡ **Best parallel candidate**: file-disjoint from the analysis chain (lives in
`src_re/`), so it can run alongside other work without pin collisions.
📋 **Work order executed and independently accepted 2026-08-10**:
`engineering-specs/phase4-f01-source-closure-work-order.md` — target is
`player_vertical_update` @ 0x80048138 (6,004 B); uses `substrate_common.compile_at`
+ `dc_permute.py`; hard rule: touches nothing in the Phase-4 analysis chain.
A continuation must gate one logical region to zero differences before moving
to the next; whole-function authorship obscured the local compiler walls.

📋 **v2 executed and independently accepted 2026-08-10** (`2076de64`):
`engineering-specs/phase4-f01-source-closure-work-order-v2.md` made the region
gate binding — region N must reach ZERO before N+1, on the frozen partition,
worked in address order. Result **NO-GO, 0 of 6 regions closed, 70 words
remaining in region 1**, wall labelled `region_1_source_expression_order_and_
register_lifetime`, **technique-shaped**.

⚡ The gate worked even though the run failed. Both v1 Phase-0 walls **cleared**:
the frame map is exact (retail 256 == compiled 256, every callee-save and local
at its retail offset, **first 54 words byte-exact** where v1 diverged at the
*second* instruction), and all **17 mixed-`$gp` accesses** reproduce as C lvalues
with no hand ASM. Region 1 moved **11/158 → 88/158** correct words.

⚠️ Three hypotheses for the `$gp` mix were tested **in order and all falsified**:
the declaration profile is inert (all three profiles byte-identical),
definition-vs-`extern`/`.sdata` provenance emits HI16/LO16 with no GPREL16 under
the pinned `-G0` tail, and non-zero `-G` link-errors. The pinned contract was
correctly **not** bent to fit.

### ❌ NOT MET — `complete_frontier`
**State:** `callers_callees` and `callbacks_indirects` undeclared; 4
declaration-only gaps. This is the indirect-control-flow wall — 179 unproved
`jr`/`jalr` sites.
**Method:** `engineering-specs/phase4-discipline-proof-work-order.md` (D1
return discipline / D2 switch locality / D3 pointer dispatch).
**Effort:** heavy. ⚠️ **THE ONE THAT CAN FAIL.** Three prior campaigns
NO-GO'd (caller-domain, address-taken, target-exclusion). If the disciplines
come back *structure-shaped* rather than *technique-shaped*, this dimension may
be unreachable — see §3.

### ❌ NOT MET — `original_interfaces`
**State (hard-truth-corrected candidate ledger 2026-08-10):** a structural ABI
row now exists for **764/764** scoped functions, but **0/764** rows are fully
resolved. Under the complete-interface bar **0/764** are mechanically closed
and **0/764** return conventions are presently proved. The
largest newly explicit wall is incoming `$ra`: 621 rows preserve or reload its
entry value but do not prove that value came from call-link semantics. Argument
typing remains almost entirely open (**1/867** register domains and **0/94**
stack domains), and exact pointer-write effects remain unresolved in 376 rows.
Callee-saved effects are classified on 617 rows. Four additional continuation
rows are rejected because a direct target is also a physical delay-slot word,
making their unsplit CFG incomplete. Each of the accepted 617 still belongs to
the 621 rows whose entry `$ra` call-link provenance remains unknown; the other 143
rows have no proved incoming-`$ra` continuation, which does not establish halt
or tail-jump because copied-link and other indirect exits remain open. Therefore
this dimension is still **not eligible for promotion**.

The stack denominator is call-entry anchored, not merely `sp+offset` shaped.
Seventeen suffix/continuation entries pop an unobserved frame; 144 epilogue
loads are retained as inherited-frame candidates rather than counted as ABI
arguments. The pinned LEVEL08_LEVEL1 `0x800B3AEC` control contributes six such
loads and the `addiu $sp,$sp,40` pop. A stack argument additionally requires a
same-image static-index direct-call witness that C re-decodes as targeting the
exact entry; 17 other candidate loads without that positive witness also stay
unclassified.

**Method/result:** `tools/phase4_f01_abi_ledger.py` supplies identity and joins;
`tools/phase4_f01_abi_probe.c` owns MIPS decoding, delay slots, read-before-write,
frame/save/restore, and local `$ra` value flow. It does not manufacture incoming
call-link provenance. The scope is the exact union requested
by the work order: frontier 764, typed-state 645 (119 omitted), local-base owners
20 (744 omitted), with both smaller sources strict subsets and no additions.
All 22 hoisted-load sites re-match, and all 50 narrower ABI-survey rows agree.
An out-of-scope caution control re-decodes the seven exact known general-`$ra`
sites and their 18 retained site/target pairs; it is explicitly not row coverage.
Artifact: `analysis/phase4_f01_abi_ledger.json`.

**Next method:** incoming-edge call-link provenance, exact argument/stack
domains, and unresolved pointer-write regions, not more row scaffolding. The
ledger already names each unknown and its obstruction.


⚠️ **EFFORT ESTIMATE CORRECTED 2026-08-10 (assistant).** This dimension was
originally judged "medium, mechanical, and independent." The completed ledger
falsifies the independence. Its own recorded reasons for the 866 unknown
argument domains:

- **737/867** — "instruction proves consumption but not a stable
  pointer/scalar/index domain"
- **129/867** — pointer shape proved by read-before-write memory-base use, but
  "no retained region proof establishes its pointee domain"
- **1/867** — the single known domain came from an "accepted retained
  typed-state binding"

The semantic half of this dimension is therefore gated by the **typed-state /
region-binding machinery** — the same family that blocks `typed_state`, and
downstream of the writer-universe and caller-dependence walls. The *structural*
half genuinely was mechanical and is now done; the *semantic* half moves only
when typed-state moves. Plan the two together, not as parallel tracks.

### ❌ NOT MET — `campaign_breadth`
**⚠️ The "LEVEL01 only / cheapest dimension" framing below is SUPERSEDED.** The
scorecard note still says LEVEL01-only; that is stale as an observation summary,
but a stale note is not evidence the bar is met.

**What was done (2026-08-10):** the corpus was swept and then *asserted*.
`tools/phase4_f01_breadth_assert.py` checked the finalizer branch law at every
transition decision on all 19 levels — **19/19 levels, 35 decisions, 0 law
failures**, with 19 predicted-CALL and 16 predicted-SKIP and **both** skip edges
exercised (13 via `beq request,2`, 3 via `bnez [0x8008225C]` on the bonus
stages). A detached verifier re-ran it exactly: 19/19, 35/35 certified decisions,
zero errors, truncation or failures.

**Rejected anyway, and the reason reframes the dimension:**

| element | state |
|---|---|
| `fail_closed_corpus_gate` | ✅ DONE — 15 adverse mutations committed as tests |
| `fresh_detached_regeneration` | ✅ DONE — fixed-point artifact `4b58c2c9…` |
| `preoutcome_applicability_matrix` | ❌ **NOT DONE** |
| `predeclared_level_type_mapping` | ❌ **NOT DONE** |

⚡ **This is not "run assertions over the corpus". It is "freeze the universe,
then show coverage of it."** A frozen applicability matrix is required across
stages, objectives, enemy/actor variants, special modes and exceptional paths —
every applicable cell with a pinned fixture and self-certifying assertion, every
inapplicable cell with a reproducible proof. **The denominators will be larger
than 19**, and they are currently unknown, which is precisely why coverage is
not demonstrated.

⚠️ **The taxonomy has an authorship hazard.** Eight types are required and no
independent mapping assigns the 19 levels to them. Everyone involved now knows
which levels passed, and the verdict is explicit that labels chosen from those
outcomes do not count. The mapping must come from an independent authority — the
row/Canon definition, the scene table `0x80077FA0`, disc structure — and be
frozen in its own commit **before** outcomes are consulted, so ancestry proves it
was not fitted.

**Effort:** NOT low. This is design work, not another replay pass.

---

## 2. Ordering — REWRITTEN 2026-08-10

Steps 1–3 of the original ordering are done; what they returned changed the
shape of the rest. Current state as of 2026-08-11: **4 of 9 met, measured and
verifier-promoted** — the first promotions in the campaign — with the remaining
work named element by element rather than estimated.

1. ✅ **§0 debt-ledger repair** — done, and stable across runs (§0).
2. ✅ **`complete_frontier` discipline campaign** — spent. Five avenues, all
   NO-GO. See §3, which is now live rather than hypothetical.
3. ✅ **`original_oracle` and `campaign_breadth` submitted and adjudicated** —
   both NOT MET, with 5 of 8 named elements since repaired. What remains:
   - `original_oracle` — **one operator recording** (cold-boot natural death).
     Everything else is closed.
   - `campaign_breadth` — the applicability matrix and an independently sourced
     taxonomy. Design work; see the dimension entry.
4. **Recording-gated and cheap once recorded:** `lifecycle` (needs *cold-boot*
   coverage specifically — only 3 of 83 corpus movies are from-boot, and a state
   anchor structurally cannot evidence boot or first load) and
   `cross_system_behavior`.
5. **Long poles, both gated on the same wall:** `typed_state` (7,206 stores
   unresolved) and the *semantic* half of `original_interfaces`. These do not
   move until the frontier machinery does — plan them together, not as parallel
   tracks. `source_closure` is parked at region 1 / 70 words.
6. **Finally:** a fresh detached verifier. Only a fresh verifier may bank a
   status change ([[Phase 4 - Reverse Engineering Operating Method#Independent verifier receipt|fresh verifier verdict]], [[Phase 4 - Solve Every Gameplay and Engine Subsystem#Status vocabulary — what the words on this page mean|Phase 4 status vocabulary]]).

⚡ **The honest critical path is §3, not this list.** Six dimensions are
reachable with ordinary effort. `complete_frontier` and the semantic half of
`typed_state`/`original_interfaces` are not reachable by any funded method, so
9/9 depends on the operator's item-2 ruling rather than on more campaigns.

---

## 3. `complete_frontier` HAS failed — this section is now live

All five avenues are spent. D3, the last, returned **NO-GO at `ab7c945`**:
0/4 contracts, 0/12 frozen sites, residual unmoved at **179**. Independently
re-verified 2026-08-10 — freeze ancestry clean, 12/12 site source words
re-derived from the pristine image, every fraction recomputed, and the freeze's
own selection rule shown to be mechanically reproducible (the anti-sample-shopping
check).

**All four walls are `technique-shaped`, not structure-shaped.** That sounds like
the good branch below, and it is not, because the D3 result says in its own words
what the technique would have to be:

> *"A technical avenue remains only through new prerequisite engines:
> region-sensitive alias closure, field-sensitive object typing, a global ingress
> contract, or a loader/residency contract. Another target-enumeration campaign
> using the current machinery is not funded by this result."*

So: **a sixth attempt on current machinery is explicitly unfunded**, and each
named alternative is an engine, not a campaign.

⚠️ **Sharpened 2026-08-10:** a compiled-C scan over the exact 22-image /
143,060-word universe finds **1,246** unresolved `jr`/`jalr` occurrences. (My
first figure of 2,340/260,307 double-counted SCUS and omitted a one-word
sentinel — corrected by the verifier.) Exclusive reachability therefore cannot be
established by current means, which is the same wall in a second place: the
finalizer branch law holds on 35/35 observed decisions but **cannot be proved
exclusive**.

**The item-2 bar is RULED 2026-08-10: accept, bounded.**
`engineering-specs/phase4-item2-bar-ruling.md`. The enumerated 179-site residual
is accepted as a *declared assumption* — recorded as observation, never as proof;
covering exactly the 179 sites in `analysis/phase4_f01_jr_tuple_capture.json` and
nothing wider; **void on a single counter-example**; and non-transferable to other
rows.

That removes the *bar* as the obstacle. It does not remove the *work*:
`complete_frontier`, `typed_state` and the semantic half of `original_interfaces`
stay gated on the same machinery, and a sixth target-enumeration campaign remains
unfunded by D3's own finding.

Evidence available for that ruling (all banked in
`analysis/phase4_f01_jr_tuple_capture.json`): 179 sites enumerated and
classified; 79 observed across ~200 replays with **zero** ever reaching the
protected set; 100 silent through any%, the behavior library, and full 100%
completion; and **one falsification** (0x80018CBC's "exact" 3-target domain
missed its dominant target) demonstrating why sub-gate-grade claims are not
safe to accept.

---

## 4. Parallelization safety (hard rule)

The analysis chain artifacts pin each other by sha: static index → census →
seed config → extractor outputs → frontier result. **Only one agent may
regenerate the chain at a time.** A second agent touching any of
`analysis/phase4_*frontier*`, the census, or `config/phase4_f01_frontier_seed.yaml`
mid-flight will stale the other's pins — the failure class that produced the
receipt↔index cycle on 2026-08-07.

Safe to parallelize: `source_closure` (different directory, different
toolchain, no chain regeneration). Conditionally safe: `original_interfaces`
if instructed read-only on shared artifacts. Prefer a git worktree for any
second agent.

---

## 5. Honest framing

F01 closure is **seven or eight known workstreams plus one research bet**, not
an open problem. Most of the cheap dimensions became cheap only because of the
2026-08-08/09 corpus and harness work. What no amount of execution can supply
is `complete_frontier` if the disciplines are structure-shaped — and that is
precisely the case the bar ruling exists to resolve.

Related: [[Phase 4 - Typed State Compiler]] · [[EXP_2026-08-05_phase4_f01_objective_lifecycle#2026-08-07 — partial-gap campaign executed readers attributed, three evidence classes shipped, 11,958 → 9,760|F01 partial-gap campaign]] ·
[[Phase 4 - Reverse Engineering Operating Method#Independent verifier receipt|fresh verifier verdict]] · [[Phase 4 - Solve Every Gameplay and Engine Subsystem#Status vocabulary — what the words on this page mean|Phase 4 status vocabulary]] ·
[[EXP_2026-08-05_phase4_f01_objective_lifecycle#Batching payoff — 37 other-row watches rode along at zero extra cost|batch-instrumented runs]]
