---
date: 2026-08-05
phase: 4
row: F01
subject: Anthill whole objective and whole scene-transition lifecycle
status: partial
closure: bounded_exhausted_direct_static_writer_census
disposition: reopen_on_named_falsifier_only
continues: EXP_2026-08-04_phase4_f01_anthill
evidence_json:
  - analysis/phase4_f01_frontier_resolve.json
  - analysis/phase4_f01_objective_lifecycle.json
  - analysis/phase4_f01_runtime_lifecycle.json
  - analysis/phase4_f01_death_lifecycle.json
  - analysis/phase4_f01_runtime_sector_table.json
static_tool: tools/phase4_f01_objective_lifecycle.c
movies:
  - movies/Phase4/Interpreter/Any% Runs/LEVEL01_AntHill.movie.json
  - movies/Phase4/Interpreter/Bonus01_Counter_ResetTest.movie.json
---

# Phase 4 F01 — Anthill: the whole objective, the whole lifecycle

Continues [[EXP_2026-08-04_phase4_f01_anthill]], which bound ONE natural
completion (region code 2 → latch → timer → teardown → results). The roadmap row
still read `missing: Whole objective/lifecycle`. This pass closes that wording:
the region code turns out to be a **five-way dispatch**, the "completion latch" a
**seven-valued transition-request enum**, and the exit trigger's footprint an
exact pair of triangles.

## Result

**F01's objective is a decided switch, not a description.** Every frame,
`player_vertical_update` asks the collision system for the player's region code
and dispatches on it. LEVEL01 authors exactly one nonzero code in its 189
authored sectors, so Anthill's whole authored trigger set is `{exit}` — no
hazard regions at all — and the exit's geometry is now recovered to the vertex.

**F01's lifecycle is the shared scene-transition request word**, whose entire
value domain and writer set are enumerated across the resident executable and all
21 shipped overlays. Anthill emits request `1`; death emits request `2`; the
consumer treats those two differently.

82 instruction-word assertions hold; the armed 3,267-frame Interpreter replay
matched every static prediction, including the exact sector index.

## The objective law (statically pinned, live confirmed)

Per frame, inside `FUNC_80048138` `player_vertical_update`:

1. **Gate.** `FUNC_80038F38(0, &player+0x82)` returns `0` unless the low byte of
   `player+0x82` is `1`. `player+0x82` is the **GROUNDED flag** — `0x0101`
   grounded, `0` airborne (see `src_re/player_update_80048138.c`). Its producer
   is the movement integrator `FUNC_8003633C`, which the same function hands
   `&player+0x82` as `a2` at `0x800495B8` and which writes byte `1` twice at
   `0x80036CB8`/`0x80036CC0`. **Consequence: no region code has any effect while
   Flik is airborne.**
2. **Source.** The gated query reads the player's current collision sector from
   `0x80090560 + index*20` and returns the signed region code at
   `0x800A7E48 + sector*0x30 + 0x2E`. The same integrator materialises that slot
   (`0x80036C00`/`0x80036C04`, `s3 = a3 + 0x80090560` at `0x80036C14`) and hands
   it to the sector resolvers, so grounding and sector membership share one owner.
3. **Re-entry guard.** `0x8004965C` re-reads the transition request word and
   abandons the whole dispatch if it is already nonzero. The trigger is
   single-shot per scene.
4. **Dispatch** — five arms, all branch targets decoded from asserted words:

| code | target | effect |
|---:|---|---|
| 0 | — | skipped at `0x80049650` |
| 1 | `0x800496A8` | `player_damage_handler(0, 0, sp+0x2c, a3=1)`; sets the commit flag `sp+0x50` |
| 2 | `0x800496C4` | request←`1`, timer←`23`, SFX `58`; sets the commit flag `sp+0x50` |
| 3 | `0x800496E8` | request←`1`, timer←`23`, SFX `58`; **no** commit flag |
| 4 | `0x80049718` | if `player+0x7e == 0 && player+0x92 == 0`: `player_damage_handler(0, 0, sp+0x2c, a3=0)` |
| other | `0x80049748` | join, no effect |

5. **Join.** If the commit flag `sp+0x50` is set, `0x8004975C..0x8004978C`
   re-commits position from the previous-position mirror and **clears
   `player+0x82`**. So codes 1 and 2 drop Flik out of the grounded state on the
   frame they fire; code 3 does not. That is the only difference between the two
   completion arms.

**LEVEL01's authored contribution:** 189 sectors, code histogram
`{0: 188, 2: 1}`. Sector **177** is the sole nonzero, and it is code 2.

## The exit trigger's exact footprint

The prior note listed sector 177's origin and deferred "exact polygon
topology" as a residual. It is now recovered.

Sector 177 owns a 92-byte collision block at chunk-32 offset `219092`
(2 groups × 1 record). The 0x20-byte record is **a triangle**, not a bare plane:
`FUNC_80038090`, the point-in-polygon region test, reads the normal at `+0x00`,
the first vertex at `+0x06`, and *two* edge deltas at `+0x0c`/`+0x10` and
`+0x12`/`+0x16`.

That reading is **proved, not assumed**: the tool rebuilds each surface normal
from the cross product of the two decoded edges and requires it to reproduce the
shipped normal at `|n| == 0x4000`. Both records reproduce exactly (the shipped
normal is the negated cross product).

Sector origin `(-5094, -5309, -3901)` source units. Vertices (runtime world
units, `(origin + local) << 5`):

| tri | normal | v0 | v1 | v2 |
|---|---|---|---|---|
| 0 | `(-5426, -11996, -9750)` | `(-168608, -158592, -139264)` | `(-194208, -158560, -125056)` | `(-163360, -171968, -125728)` |
| 1 | `(-2828, -5751, -15078)` | `(-194208, -158560, -125056)` | `(-192192, -171968, -120320)` | `(-163360, -171968, -125728)` |

The two triangles share the edge `v1(tri0) — v2(tri0)`, so the Anthill exit is a
single **quad** of four distinct vertices, steeply inclined (normal Y ≈ −0.73 and
−0.35 of unit) — the entrance ramp surface, not a flat pad. The last 8 bytes of
each record (`31fcc403fb050005` / `31fcc403fb05fb06`) are **not read** by the
containment test and remain unattributed.

## The lifecycle: `0x800823A0` is a request enum, not a latch

A gp-aware census (`lui+addiu`, `lui+ori`, and `$gp`-relative at
`$gp = 0x80081D98`) over `SCUS_942.88` plus all 21 shipped overlays enumerates
**28 writers** and **53 readers** of `0x800823A0`, and **30 writers / 13 readers**
of the timer `0x80082470`.

| value | resident writers | meaning |
|---:|---|---|
| 0 | `0x8004FADC`, `0x8004FE44`, `0x8005B888` | cleared / no request |
| 1 | `0x800496D8` (code 2), `0x800496F8` (code 3) | scene complete — also 12 per-level overlay verbs |
| 2 | `0x8004A8B4`, `0x8004A9F4` | death (timer 60) |
| 3 | `0x8004F28C` | — |
| 4 | `0x8004F224`, `0x8004F2F0`, `0x8004F6B8` | — |
| 5 | `0x8004F9E4` | — |
| 6 | `0x8004B3C0`, `0x800591DC`, `0x8005C6B8` | — |

Consumer, at `0x8004FEEC`: wait until request ≠ 0 **and** timer == 0, then call
`0x80039BD8(0)` and `0x80043500`; then call the transition finalizer
`0x80045A60` **unless request == 2 or `[gp+0x4c4] != 0`**. So the death arm
deliberately skips the finalizer the completion arm runs — that is why F01's
natural route reaches `0x80045A60` and a death would not.

**Codes 1 and 4 are hazard regions, not exits.** `FUNC_8004A700`'s `a3` is a
branch flag (`0x8004A720` moves it to `s4`; `0x8004A73C` tests it with `bnez`),
not a destination. Request `2` is reached only after the health decrement at
`0x8004A888` leaves health negative (`0x8004A890 bgez`). A hazard region
therefore requests a transition **only when the damage it deals is lethal**.

⚠️ This **corrects** `Level_Goal_and_Exit_Trigger_Matrix`'s region-code table,
which read code 1 as "calls `FUNC_8004A700` type-2 transition path" and left
codes 3 and 4 as "semantics unresolved". Code 1 is a damage region; the type-2
transition is a conditional consequence inside the handler, not the arm's effect.

## Runtime confirmation

Isolated instance `/tmp/dsrepro-f01`, port 23477, `Interpreter`,
`tools/launch_repro_playback.sh --execution-mode Interpreter`, pristine
`Disney-Pixar A Bug's Life (v1.0).cue`, serial `SCUS-94288`, 221-method
capability census.

`movie.loadAndArm` on `movies/Phase4/Interpreter/Any% Runs/LEVEL01_AntHill.movie.json`
(v4, content sha256 `b53171e2863d802629defbc9a1e956c7eab926ddfd420e58db0c901e0a978250`,
state-anchored at emulator frame 138881, `anchor_to_mapped_frame_delta: 0`,
`phase_correction_pending: false`), then `movie.resumeUntilMovieFrame` to movie
frame 3266 (emulator 142147) — normal-speed playback, not frame stepping.
`reproducible: true`, `truncated: false`, execution mode `Interpreter`
throughout with `history_total: 0` (no transition ever recorded).

Seven exec-trace watches (one per dispatch arm plus the join and the consumer)
and two write watches, all non-truncated over the whole movie:

| watch | hits | evidence |
|---|---:|---|
| code-2 arm `0x800496C4` | **1** | frame 140814, cycle 79728950059 |
| code-1 arm `0x800496A8` | 0 | — |
| code-3 arm `0x800496E8` | 0 | — |
| code-4 arm `0x80049718` | 0 | — |
| death request-2 `0x8004A8B4` | 0 | — |
| join grounded-clear `0x80049770` | **1** | frame 140814 |
| consumer finalizer `0x8004FF48` | **1** | frame 140859 |

**Captured memory at the instant the code-2 arm was entered** (pre-instruction,
via `execTrace` `capture_memory`):

- `[0x80090560]` = **177** — the current collision sector.
- `[0x800A6582]` = **0x0101** — GROUNDED, exactly as the gate requires.
- `[0x800823A0]` = 0 and `[0x80082470]` = 0 — the re-entry guard was clear.

This is the upgrade the prior note could not make: sector 177 was previously an
**inference** ("the only authored code-2 sector, so it must be the one crossed").
It is now a direct **observation** of the sector index at the triggering frame.

**The complete write history of both lifecycle words, for the whole stage:**

| frame | pc | word | value |
|---:|---|---|---:|
| 139562 | `0x8005B888` / `0x8005B890` | request / timer | 0 / 0 |
| 139563 | `0x8004FE44` / `0x8004FE4C` | request / timer | 0 / **45** |
| 139564–139652 | `0x800553F8` | timer | 44 → 0 |
| 140814 | `0x800496D8` / `0x80049704` | request / timer | **1** / **23** |
| 140816–140858 | `0x800553F8` | timer | 22 → 0 |
| 140859 | `0x8004FF48` | — | finalizer called, request=1, timer=0, scene state=1 |

Exactly **three** writes to the request word in the entire stage, **all from
resident PCs** — no overlay verb participated in Anthill's transition at all.
(Statically consistent: `LEVEL01/LEVEL.BIN` has zero accesses to any watched
address; the `0x800B4100` completion verb the prior note went looking for lives
in `LEVEL01/LEVEL1.BIN`, which is a *different scene's* overlay.)

The countdown at `0x800553F8` ticks every 2 emulator frames (68 decrements,
frame-gap histogram `{2: 66, 1162: 1}`, the single large gap being the interval
between the entry countdown expiring and the goal starting the second one) — the
transition timer runs on the 30 Hz logic tick. ⚠️ Nominal, not strict: the death
run below slipped 9 of its 104 intervals to 3 frames.

**Stage entry is part of the same machine.** The 45-frame timer armed at
`0x8004FE4C` on frame 139563 is the entry transition, using the identical
request/timer/countdown mechanism as the exit. F01's lifecycle is therefore
entry-transition → play → exit-transition → results, all through one word.


## Death confirmed on a second Anthill Interpreter movie (2026-08-05)

The residual "the death arm is pinned but this movie never dies" is closed.
`movies/Phase4/Interpreter/Bonus01_Counter_ResetTest.movie.json` is a LEVEL01 run
(scene id `0x80082504 == 1`, 223 runtime sectors) in which Flik dies — operator
pointer. v4, `armed_while_paused: true`, so the phase correction applied itself:
`phase_delay_owed: true`, `anchor_to_mapped_frame_delta: 1`, consumed at emulator
frame 10758 / movie frame 0. 4,187 frames, `reproducible: true`, Interpreter with
`history_total: 0`, nothing truncated.

⚠️ The start state **swapped the mounted media** (`media_changed_during_setup:
true`) to `~/.cache/abl-phase4-i12-clean-Hu6j43/`. That image is
sha256-identical to the repo's pristine `.bin`
(`2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`), verified
offline, so the run is on pristine media — but the swap is real and must be
recorded rather than assumed benign.

### The health ladder decides the transition

`0x8004A888` is `sh v1, 0x6594(at)` with `v1` the post-decrement value; the
captured memory is the pre-instruction value:

| frame | health before | v1 after | request written |
|---:|---:|---:|---|
| 12177 | 4 | 3 | — |
| 12757 | 3 | 2 | — |
| 13945 | 2 | 1 | — |
| 14077 | 1 | 0 | — |
| 14309 | 0 | **−1** | **2** |

Four non-lethal hits produced no request at all. **A hazard requests a transition
only on the decrement that takes health negative** — health `0` is still alive.
That is exactly what the static `bgez` gate at `0x8004A890` predicts, now with
the boundary case observed.

### The finalizer skip is proven, not inferred

| watch | hits | detail |
|---|---:|---|
| `0x8004A8B4` death request←2 | **1** | frame 14309; timer←60 at `0x8004A8C0` |
| `0x8004FF14` consumer proceeded | **1** | frame 14436, request 2, timer 0 |
| `0x8004FF28` request re-read | **1** | frame 14436, request **2**, `[$gp+0x4c4]` **0** |
| `0x8004FF48` finalizer call | **0** | — |

The consumer demonstrably reached the decision point, and the *other* skip
condition (`[$gp+0x4c4] != 0`) was measured at **0**. So `request == 2` is the
only thing that can have skipped the finalizer. The completion run reached
`0x8004FF48`; this one did not, from the same consumer, on the same scene.

### Death respawns in place, through the scene-ENTRY transition

| frame | pc | value |
|---:|---|---|
| 14309 | `0x8004A8B4` / `0x8004A8C0` | request ← 2, timer ← 60 |
| 14311–14429 | `0x800553F8` | 59 → 0 |
| 14437 | `0x8004FE44` / `0x8004FE4C` | request ← **0**, timer ← **45** |
| 14439–14526 | `0x800553F8` | 44 → 0 |

Exactly **two** request writes in the whole run. The respawn re-runs the same
`0x8004FE44`/`0x8004FE4C` entry pair (timer 45) seen at Anthill's stage entry in
the completion run, with scene state unchanged at `1`. **Death in Anthill is an
in-place respawn driven by the scene-entry transition, not a scene change.**
Final state: request 0, timer 0, scene 1, health 4.

### And no region trigger fired

All four region arms took **zero** hits across the run. This Anthill route died
before reaching the exit and never entered a hazard region — consistent with
LEVEL01 authoring no code-1/3/4 sectors at all. The damage came from actor
contact, not from the collision region field.

## Evidence classification

- **Observation:** all 83 instruction words; both armed replays' arm-hit counts,
  captured sector/grounded/request/timer values, complete write histories,
  countdown cadence, finalizer entry, and — on the death movie — the health
  ladder, the request-2 store, the measured `[$gp+0x4c4] == 0`, the zero-hit
  finalizer, and the in-place respawn.
- **Inference:** that Anthill has no hazard regions — from the authored code
  histogram plus zero hits on the code-1/3/4 arms over the whole movie. A route
  that never touches an unauthored region cannot prove none exists elsewhere in
  the scene; the authored census is what bounds it.
- **Causal confirmation:** carried over from prior LEVEL01 work — relocating the
  code-2 field from sector 177 to sector 108 on a rebuilt disc moved the
  completion behaviour and left pristine behaviour inert.

## Bounded residuals

- The last 8 bytes of each collision triangle record are unread by the
  containment test and unattributed.
- Region-code values 3, 4, 5, 6 of the request enum have pinned writers but
  unnamed meanings (they belong to the scene-flow row, not F01 — Anthill emits
  only 1, and only 2 is reachable from it via death).
- SFX 58's SPU sample identity.
- Pause/restart permutations within Anthill remain unexercised (death is now
  closed — see below).
- Compiler-matching the complete 6,004-byte `player_vertical_update`.


## Re-check under the Frontier Closure Workbench (2026-08-05)

[[Phase 4 - Frontier Closure Workbench]] raises the Item-2 bar and — importantly
— reserves promotion to an independent verifier. Re-checking F01 against it found
**one real gap in my own census, which I then closed**, and several scope limits
that remain.

### The gap it caught, and the closure

My authored-sector census covered LEVEL01's **189 authored records**. But E02
established that the runtime sector table is an authored prefix **plus a
runtime-registered tail** — and LEVEL01 runs with **223** runtime sectors. The 34
tail slots were an uncovered unknown, and the table's initialiser loops at
`0x80031E20`/`0x80031E60` clear only the **flags** field `+0x2C`, never the
region code `+0x2E`. So "exactly one nonzero region code" was, as written, a
statement about the disc that said nothing about 34 live slots.

Closed two ways:

1. **Static writer closure.** Across the resident image *and all 21 shipped
   overlays* there are exactly **two** stores to the region-code field, at
   `0x80030F94` and `0x80031264`. Both have the identical shape
   `lw v0, 0x2c(t1)` → `sh v0, 0x7e76(at)` — the authored source→runtime
   conversion (E02's `src +0x2C → runtime +0x2E`). No overlay writes the field
   and no runtime-registration path writes it, so a runtime region code can only
   ever be sourced from authored data. Now asserted (87 pins total).
2. **Live full-table read.** Inside Anthill (scene id `1`, movie frame 1500 /
   emulator 140381), all **223** runtime sectors read valid: histogram
   `{0: 222, 2: 1}`, the sole nonzero being sector **177** = code 2, and the tail
   `189..222` uniformly code `0`.

The claim survives and is stronger than what I originally banked.

> **Superseded in part (2026-08-05):** the hand assessment below was the starting
> point for [[Phase 4 - Frontier Extractor]], which measures F01's frontier
> mechanically instead. Current figures: 641 functions, **124** window accesses
> (115 static-index + 9 recovered by an independent binary scan the index could
> not see), 16,913 mechanical blockers, `item2_ready_for_review: false` with six
> named blockers. F01 served as that tool's acceptance fixture and exposed a real
> defect in each of its seven review rounds.

### Item-2 layers: where F01 actually stands

The workbench packet for `F01_anthill / complete_frontier` requires seven
declared layers. Honest assessment:

| layer | state | limit |
|---|---|---|
| scope_universe | partial | images named by path, **not hash-bound**; no census-completeness disposition (the function census is ~95%) |
| function_roots | not declared | I worked from specific PCs, not a declared root set |
| callers_callees | **missing** | the writer census is store-site only; a callee-performed write (B06's `memset` case) would not appear |
| callbacks_indirects | **missing** | no `jalr` / callback-table / event-selector analysis |
| readers_writers | good, scoped | complete for constant-base and `$gp`-relative forms; affine/register-computed accesses not excluded |
| overlays_assets | partial | all 21 overlay files scanned, but bases assumed from `analysis/overlay_symbols.json`, not bound via `memory.getResidency` |
| bounded_residuals | partial | prose bullets, not the strict form (boundary, evidence, next falsifier, proof basis, unknown IDs, non-intersection) |

Mitigation on the two `missing` rows: both armed replays carried `accessLog`
**write watches** on the request word, which observe every CPU write regardless of
which function performs it — including a `memset`'s stores. They recorded exactly
3 writes (completion run) and 2 (death run), all attributable to statically
enumerated store sites. That is a **falsifier that did not fire on two routes**,
not a universal negative — per the workbench's own §6.

**Conclusion: F01's mechanism claims are well-pinned and now cover the complete
runtime table, but the row is not Item-2 *ready* under this contract, and under
its authority model no agent-authored packet may bank a registry status.**


## ⚠️ F01 is STOPPED, not closed — DoD scorecard (2026-08-05)

I described this row as "closed" in working summaries and wrote *"Row closed for
Phase 4"* into `analysis/mechanics_baseline.yaml`. That was an overclaim and is
corrected. `bounded_exhausted` is a **decision to stop while still partial**, and
the status vocabulary requires a scorecard beside the label because the label
hides maturity. For scale: **B06, with 251/251 frontier sites classified and
Item 2 met within its declared bound, is 6 of 9 and explicitly NOT solved.**

| # | dimension | F01 | why |
|---:|---|---|---|
| 1 | original oracle | partial | hash-pinned Interpreter fixtures + assertions, but no *designed* positive/negative control pair |
| 2 | complete frontier | **not met** | `callers_callees` and `callbacks_indirects` undeclared; 4 further declaration-only gaps |
| 3 | typed state | partial | request/timer/GROUNDED/region-code/sector widths, domains and owners recovered, not declared in the required form |
| 4 | lifecycle | partial | entry, completion, death/respawn observed; pause, restart, reload, persistence not |
| 5 | original interfaces | **not met** | no ABI ledger; only one call site's delay-slot behaviour noted |
| 6 | campaign breadth | **not met** | LEVEL01 only, though the region dispatch is campaign-wide |
| 7 | cross-system behavior | partial | collision → player update → scene flow → results overlay bound; no matched controls |
| 8 | source closure | partial | `FUNC_80038F38` byte-matched; the 6,004-byte player updater is not |
| 9 | durable evidence | **met** | EXP + 2 MEM notes + canon + playbook, committed, regenerable C verifier (87 assertions), evidence JSON, builds from HEAD |

**1 of 9 met.** What this row *does* have is a well-pinned mechanism law for the
question the row actually asked, and that is why stopping is defensible — not
because the row is finished.


### "Move on" means park the replay slot — not abandon the row

The Phase 4 **exit gate** requires that *"every completed campaign satisfies the
full subsystem Definition of Done."* A permanently parked 1-of-9 row would make
Phase 4 unfinishable, so `bounded_exhausted` here is a **deferral with a tracked
revisit path**, not a terminal state.

Registry corrections that follow from that:

- `status` is back to **`partial`**, matching the 96 other partial rows. F01 was
  the only row in 107 carrying `bounded_exhausted` as a *status*, which made it
  read as further along than **B06 at 6 of 9**. The stopping decision now lives in
  `disposition: bounded_exhausted_pending_reopen`, and maturity lives in the
  scorecard, because the status field cannot express maturity.
- `reopen_when` records concrete triggers, and unconditionally the exit gate.
- `deferred_to` assigns the reusable gaps to the campaigns that actually own them:

| gap | owner | why it is not F01's to solve |
|---|---|---|
| `original_interfaces` | shared ABI-ledger tooling | not an Anthill-specific fact |
| `campaign_breadth` | scene-flow / region-code campaign | the 5-arm dispatch is shared by all 16 scenes |
| `source_closure` | decompilation campaign | the 6,004-byte updater is a compiler-matching task |
| `complete_frontier` | general frontier compiler | callers/callees + indirects need the tool, not a per-row census |

⚠️ **Correction to this note's own earlier triage.** It described F01's Item-2
state as "mainly declaration work plus one callee-write question." That was too
optimistic: `callbacks_indirects` was dismissed on *absence of positive
indication*, which is precisely the reasoning Item 2 exists to reject. Indirect
paths and callee/bulk writes are both genuine unknowns, not declaration gaps.
Registration makes the gaps visible; it does not close them.


## Registration + matched control (2026-08-05, Codex steps 1–3)

### Step 2 first: the two-movie contrast was inadmissible

`tools/phase4_witness_compiler.py` requires **both arms to share
`start_state_sha256` and `start_fingerprint`**. The completion and death movies
have different anchors, so "completion reaches the finalizer, death does not" is
an observational contrast, **not** a matched control. Replaced with a real
one-variable experiment from a single anchor:

| | control | positive |
|---|---|---|
| replay | `LEVEL01_AntHill` → movie frame 1950 → 2100 | identical |
| perturbation | none | one write, `u16 2 → 0x800823A0` at frame 1950 |
| start fingerprint | `36f31bd5…` (full 2 MiB RAM sha256) | **same** |
| consumer proceeded `0x8004FF14` | 1 | 1 |
| request at `0x8004FF28` | 1 | 2 |
| `[gp+0x4c4]` | 0 | 0 |
| **finalizer `0x8004FF48`** | **1** | **0** |

`matched_origin: true`, one changed perturbation key, **zero unasserted
differing leaves**, zero errors, deterministic under `--check` →
`witness_ready_for_fresh_verifier`. Strictly stronger than the contrast it
replaces: request 2 now *causes* the skip, with the other skip condition ruled out
by measurement inside the same run.

⚠️ **This is a causal witness for one branch condition, NOT a complete
`original_oracle`**, and the registry claim is deliberately `partial` so it cannot
auto-promote. Four bounds, all recorded as non-intersecting residuals:

- the anchor is a **validated save state**, not the pristine cold boot the
  workbench wants for item 1;
- the value `2` is **injected**, not produced by natural gameplay — the natural
  completion and death runs remain necessary to show gameplay reaches these
  states unaided;
- it covers **one** branch condition over four declared observation leaves, not
  the objective lifecycle;
- the raw per-arm receipts are now retained and cross-checked
  (`analysis/receipts/`, indexed by `analysis/phase4_f01_witness_receipts.json`,
  both recomputing to the hashes the witness declares) but are **not yet in the
  central external-evidence preservation manifest**.

### Step 3: the bulk-write vector is closed for constant destinations

Every `jal` with statically constant `a0` (destination) and `a2` (length) across
the resident image and all 21 overlays — **68 calls examined, 0** whose
`[a0, a0+a2)` covers the request word.

Exact bound: this closes the **constant-argument bulk-write family only** — the
shape that caused B06's trouble. It does **not** close dynamically computed
destinations or lengths, indirect calls (`jalr` / dispatch tables), callees whose
arguments this scan could not recover, or callee-performed writes in general. It
is a bounded Item-2 result, not caller/callee closure.

### Step 1: F01 is registered — and the ledger still cannot see it

Child campaign `anthill_objective_lifecycle` added to
`config/phase4_campaigns.yaml` with an `original_oracle` `dimension_claim`
pinned to the witness. It **validates in isolation**:
`phase4_closure_debt._claim_errors` → zero errors; both evidence groups → zero
errors. Adding it changes the global error set by **exactly nothing** (7 before,
7 after, diff empty).

⚠️ **But `original_oracle` is still NOT met, and the packet still reports
`gap`.** `tools/phase4_closure_debt.py` refuses to write the ledger while any
campaign is broken, and **7 pre-existing errors remain in other campaigns**:

```
phase0_2_external_fixture_set.json        sha256 mismatch + missing_central_pins
phase0_2_knowledge_closure_report.json    sha256 mismatch + 2 unresolvable leaves
phase4_trace_capsule_set.json             sha256 mismatch + exact_capsules 50 != 55
```

None belong to F01. This is the concrete shape of the control-plane blocker:
**claim authored ≠ dimension met ≠ verifier promoted**, and F01 is now stalled at
the first arrow by fixture/capsule drift that is not its to fix. The scorecard
records `original_oracle` under `claim_authored_pending_ledger`, not `met`.


## Who else touches this state? (2026-08-05, the mod-safety question)

The frontier work left one question that matters for modding more than any DoD
label: **can anything other than the enumerated writers reach `0x800823A0` or
`0x80082470`?** `tools/phase4_f01_frontier_resolve.c` re-walks the 30 extents
that provably touch either word, with stronger base recovery than the static
index, and gives every memory access exactly one disposition.

| disposition | count |
|---|---:|
| resolved, reaches a window | 62 |
| resolved, provably misses | 1,181 |
| stack-frame bounded | 314 |
| **unresolved** | **403** (106 stores, 297 loads) |
| examined | 1,960 |

### ⚠️ A retraction, and the reason it matters

This note first recorded *"the writer set is complete."* **It is not, and the tool
never showed that.** The resolver reports zero additional writers **among the
resolved accesses**; I wrote that up as "no unknown writer". **106 unresolved
STORE sites remain**, and any one could write either word.

The tool now fails closed while any unresolved store stands, splits unknowns by
load/store so the distinction cannot be collapsed again, and retains all 403
sites individually. The supportable claim is: *no additional writer among the
resolved accesses; 106 unresolved store sites remain.*

Two accompanying implementation defects, both real rather than cosmetic:

- **Writer identity was keyed on pc alone.** Overlay addresses repeat, so two
  overlay LOADS (`LEVEL05_LEVEL:0x800B3DEC`, `LEVEL04_LEVEL:0x800B410C`) were
  mislabelled as enumerated writers of other overlays. It is **34** previously
  unlisted readers, not 32 — and a genuine new store at a colliding address would
  have passed silently. Identity is `(image, pc)`.
- **"Written exactly once" is not dominance.** A conditional branch can skip the
  sole definition and reach the use with the register undefined. Replaced with a
  real check — an instruction is not dominated by a definition if it is reachable
  from the entry *without executing it* — and the counterexample is a permanent
  `--self-test`. The F01 figures did not move, so this closed a hole rather than
  changing an answer.

### What the readers actually do

Five are decoded. Three from this pass, two synthesised from evidence that
already existed rather than re-derived:

| reader | behaviour | site |
|---|---|---|
| `checkpoint_save` | returns immediately while the timer is nonzero — **no checkpoint during any countdown** | `0x80054CD4` |
| `gameplay_state_machine` | masks the pad word to `0x309` when `request == 0 && timer >= 31` — **input locked for the first ~30 frames of scene entry** | `0x8004EF08` |
| `sfx_dispatch` | while `request == 2`, drops every cue but `0x49` — which is exactly what the death path plays | `0x80050B8C` |
| `actor_skinned_update` | while `request == 2`, forces `ANIM_INDEX` to 15 every frame | `0x80056890` |
| `0x800526F4` | the in-game HUD renderer, gated on the transition state at its entry ([[EXP_2026-08-04_phase4_e13_hud_results]]) | `0x800526F4`, `0x80052734` |

⚠️ That last one carries a census correction the resolver inherited: the census
names `0x800526FC` `results_screen_render`, but it is **neither** a function entry
**nor** the results screen — that is
[[FUNC_800B7DA0_results_screen_evaluate_and_draw]] in `BITS/MEMORY.BIN`.

### The finding that matters for modding

Setting `request = 2` does all of this at once, and **none of it lives in the
scene-flow code that sets the word**:

| subsystem | effect |
|---|---|
| scene flow | the transition finalizer `0x80045A60` is skipped |
| sound | every cue but the death cue is dropped |
| animation | the player animation is forced to index 15 |
| checkpointing | suppressed for the whole countdown |

`0x800823A0` is read as a **mode** by sound, animation, HUD and save code — not
as a scene-flow local. Any change to when or how it is set has all of those in
its regression surface. Full reader table and decoded listings in
[[MEM_800823A0_scene_transition_request]].

## Reproduce

```bash
cc -O2 -Wall -Wextra -Werror -o /tmp/f01 tools/phase4_f01_objective_lifecycle.c -lm
/tmp/f01 REBUILD/files            # exit 0 iff all 82 assertions hold
```

Runtime: launch with
`tools/launch_repro_playback.sh --execution-mode Interpreter --config-dir /tmp/dsrepro-f01 --port 23477 --token f01-lifecycle --disc "Disney-Pixar A Bug's Life (v1.0).cue"`,
`movie.loadAndArm` the movie above with the nine instrumentation entries recorded
in `analysis/phase4_f01_runtime_lifecycle.json`, then
`movie.resumeUntilMovieFrame {"frame": 3266}`.

## 2026-08-05 — the census was truncated; re-baselined, then 35 stores retired

**First, a correction that made the problem bigger.** The resolver's `EXTENTS`
table had hand-typed function ends, and **20 of its 29 extents stopped short of
the real function**: 28,252 bytes / 7,063 instructions *inside the functions this
census claims to cover* were never read. The ends now come from
`analysis/phase4_static_frontier_index.json`.

| | truncated | full extents |
|---|---|---|
| accesses examined | 1,960 | **3,681** |
| reach a window | 62 | **100** |
| provably miss | 1,181 | **2,280** |
| stack-bounded | 314 | **506** |
| unresolved | 403 | **795** |
| **unresolved STORES** | **106** | **231** |
| previously unlisted readers | 34 | **50** |
| new writers among resolved | 0 | **0** |

The no-new-writer finding **survived and strengthened** — still zero over the
full extents. But every count that was reported as a total was a lower bound.
The 106 figure appears in earlier sections of this document and in
[[MEM_800823A0_scene_transition_request]]; both now carry the correction.

## 2026-08-05 — 35 of the 231 unresolved stores decided

The 106 unresolved store sites above were the reason F01's writer-set
completeness claim had to be retracted. The first tranche of them is now
**bounded by proof**, not by assumption.

`tools/phase4_typed_state.py` + `tools/phase4_typed_state_provenance.c` — see
[[Phase 4 - Typed State Compiler]] for the full design — take an access whose
base register could not be resolved to a constant and, when the base is *proved*
to point into a bounded region, compute the interval the access must land in. If
that interval misses every watched window, the site cannot reach the state
whatever the pointer's value.

```
ACCEPTANCE FIXTURE unresolved_sites[store]: 231 sites, 134 joined, 97 absent
    bounded_by_proof:              23
    bounded_by_index_convention:   12
    still_unresolved:              99
```

23 are bounded by proof, mostly in `actor_player_contact_resolver` through `s1`.
The proof chain:

1. Both definitions of `s1` that can reach those 19 stores load from
   **`0x80090748`** — `0x8004AC00` takes element 0, `0x8004B698` takes
   element `[v0]`. The `lui` half of the load idiom and the epilogue restore
   reach none of them.
2. No store is reachable from the function entry without passing a definition, so
   `s1` never arrives holding the caller's value.
3. `0x80090748` is the actor pointer table; ~~its writers are **exactly 4**
   image-wide, only one non-null~~ **historical result at this stage, superseded
   below: the corrected C recognizer finds a known lower bound of ≥6 with a
   nonzero residual** — see [[MEM_8009FD80_actor_pool]].
4. The actor pool is `0x8009FD80 .. 0x800A1E80` (64 slots × `0x84`), derived from
   `mover_updater`'s own walk. Disjoint from `0x800823A0` / `0x80082470` at every
   displacement those 19 stores use.

A further **12 are excluded by a second opinion**: `tools/region_provenance.c`,
rebuilt and run by the compiler on both windows. Those sit in their own bucket
because its index-bound tiers rest on the non-negative, loop-bound-checked array
convention. It reports **zero** blocking sites as reaching a window — and the
check is not vacuous, since the same run finds 41 hits on `0x800823A0` elsewhere
in the image, all of them already in the enumerated writer set.

### What did NOT change

- **99 fixture stores remain unresolved**, and **97 more are absent from the
  frontier's blocker ledger entirely** — listed in full in the output, never
  counted as bounded. F01's dimension 2 is still open.
- The compiler consumes the **full 16,558-site ledger**, not the 231. The fixture
  is an acceptance target chosen by the resolver; it is not the universe — and
  the 97 absences show neither set contains the other.
- Indirect control flow is untouched. `jr` is still terminal in the dominance
  walk and the frontier's indirect-jump blockers are carried through unchanged.
- `authority.promotes_dimension` is `false`. This is evidence for dimension 3,
  not a promotion of it.

The remaining 99 need capabilities the next increment supplies: `v0`/`v1` bases
are **return values** (ABI accelerator, dimension 5), `s0`/`s2`/`s3` bases are
callee-saved copies needing reaching-definition chasing, and several groups have
non-zero `entry_reachable_uses` — genuinely caller-dependent, unbounded without
ABI facts.

### Reproduce

```bash
python3 tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
    --output analysis/phase4_f01_typed_state.json --check
python3 -m pytest tests/test_phase4_typed_state.py -q       # 16 passed
gcc -O2 -std=c11 -Wall -Wextra -Werror -o /tmp/prov tools/phase4_typed_state_provenance.c
/tmp/prov --self-test                                        # 3 counterexamples, exit 0
```

## 2026-08-06 — the ABI accelerator, and the negative result it measured

Tooling increment 3 (DoD dimension 5, *original interfaces*) is built, run and
tested — see [[Phase 4 - Typed State Compiler]] for the design. Two outcomes, and
the second is the more useful one.

### It turned an asserted binding into a verified one

Increment 2's `caller_argument` counted callers and took the **value** from the
schema's prose. Nothing compared the claim to an instruction. The accelerator
reads the callers instead, and for F01's player-state binding derives the whole
chain itself:

| step | pc | what |
|---|---|---|
| the copy | `0x80048140` | `addu s1, a0, zero` — s1 is a pure copy of incoming `a0` |
| the call | `0x8004EFD8` | `jal player_vertical_update` |
| **the delay slot** | `0x8004EFDC` | `addiu a0, s0, -144` — runs *before* the call transfers |
| the base | `0x8004EF70`/`74` | `lui`/`addiu` → `s0 = 0x800A6590` |
| result | | **`a0 = 0x800A6500`**, inside `player_actor` |

Acceptance genuinely depends on that value: moving the declared region above or
below `0x800A6500` rejects the binding, as does pointing it at a register that is
not argument-derived. All three are permanent tests.

It also **retired a binding that bounded nothing** — the schema's second
`caller_argument` for `a0` itself, which the ledger has no `a0`-based unresolved
site for. The old check accepted it.

### It decides none of F01's remaining blockers, and now says so in numbers

```bash
tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
    --output analysis/phase4_f01_typed_state.json \
    --survey analysis/phase4_f01_abi_survey.json
```

| verdict | groups | blocking stores |
|---|---:|---:|
| `not_argument_derived` | 33 | **87** |
| `no_direct_caller` | 2 | 7 |
| `caller_value_not_recoverable` | 1 | 2 |
| **still open** | **36** | **96** |

**87 of the 96 have a base that is locally computed** — an index, a load,
arithmetic — not an argument, so argument typing cannot apply. Return typing
(`returns@`) works too and decides nothing here either: the `v0`/`v1` groups are
fed by 15–21 distinct callees each.

The survey runs the same check the compiler runs, against the widest possible
region so a group fails only when the value cannot be **recovered** — never
because it lands somewhere else — and it excludes groups already decided by
another provenance so the residual is not overstated.

F01 is unchanged at **231 blocking stores, 35 decided** (23 proof, 12 convention),
99 unresolved, 97 outside the ledger. Item 2 stays open.

### What this says about what to do next

The residual is not an ABI problem. It is index-bound recovery for locally
computed bases — which `tools/region_provenance.c` already does soundly, but for
the **resident image only** — plus indirect-call resolution for the overlay
handlers. Extending the second opinion to overlays would decide more of F01 than
any further ABI work.

## 2026-08-06 — the second opinion now covers overlays: 35 → 64 decided

The previous entry recommended this over more ABI work, on the measured grounds
that F01's residual is index-bound recovery rather than argument typing. It was
the right call.

`tools/region_provenance.c` was resident-only because it required a `PS-X EXE`
header and read the load address from it. Overlays are **raw images**: no header,
and a load address only the static index knows. It gained `--raw BASE`; the
compiler supplies the base and the per-image function list from the index, so
neither can drift from the rest of the pipeline.

| | resident only | all 21 images |
|---|---:|---:|
| fixture stores bounded by proof | 23 | 23 |
| fixture stores bounded by index convention | 12 | **41** |
| fixture stores still unresolved | 99 | **70** |
| **decided** | **35** | **64** |

All 21 images analysed, none unavailable, and **zero blocking sites reported as
reaching a window**.

### Why the overlay results are safe to believe

- **An overlay run sees only that overlay.** Calls into the resident executable
  land outside the image and stay unresolved, so no overlay function is seeded
  with arguments from a resident caller. That is the conservative direction — an
  unseeded register is TOP, TOP yields no region, and no region yields no
  exclusion. Weaker than the resident run, never less sound.
- ⚠️ **The anchor rule is re-checked per site, fail-closed.** An unanchored
  region (an arithmetic progression whose first element is unproven) may use only
  Tier 1 alignment, which is invariant to anchor choice; Tiers 2 and 3 depend on
  the index's sign relative to the anchor. Pointing an analysis at a new class of
  input is exactly when such a rule silently stops holding, so the compiler now
  enforces it rather than trusting it. Measured: **488 unanchored exclusions, all
  alignment-only, 0 violations.**
- **The resident output is byte-identical** before and after the change.

An unanchored base looks alarming until you check it. `LEVEL01_LEVEL:0x800B39E8`
is a memcpy loop with `a2 = 0x800B3F54` (lui/addiu at `0x800B39DC`/`0x800B39E0`),
yet the exclusion reports `region_base 0x80000004`. That is a **residue-class
representative**, which is all `verified_anchor: false` claims: `0x800B3F54` and
`0x80000004` are congruent modulo the 16-byte stride, `0x800823A0` is not, so no
element can reach it. Both fields are carried into the output so this is
checkable rather than assumed.

### F01 now

**231 blocking stores, 64 decided** (23 proof + 41 convention), 70 unresolved, 97
absent from the frontier ledger. Item 2 still open — but the residual is down from
99 to 70, and the remaining work is characterised: 65 locally computed bases, 7
reached only through `jalr`, 2 with an unrecoverable caller value.

## 2026-08-06 — fresh detached verifier: OVERSTATED in scope, UNDERSTATED in safety

F01 went to an independent verifier on a clean checkout at `b3c5363511cb`, per the
[[Phase 4 - Frontier Closure Workbench]] rule that only a fresh detached verifier
may bank a registry status. It declined to bank one, and it was right to.

### What it reproduced

The objective tool (sha256-identical to the value pinned in
`config/phase4_campaigns.yaml`), the resolver (byte-identical), the typed-state and
ABI artifacts, the extent audit, the DoD scorecard's inability to auto-promote, the
three evidence buckets being kept distinct with their convention dependence
disclosed, and the 97 ledger-absent sites not being counted as bounded.

### What it found — the extent SET was a subset

The 2026-08-05 correction fixed the extent **ends**. The **set** was still short:
the tool's own stated criterion admits **37** functions and `EXTENTS[]` listed
**29**. The same subset-reported-as-whole failure, moved up one level.

| | 29 extents | 37 extents |
|---|---:|---:|
| accesses examined | 3,681 | **4,031** |
| reach a window | 100 | **124** |
| unresolved STORES | 231 | **238** |
| previously unlisted readers | 50 | **66** |
| new writers among resolved | 0 | **0** |

Among the eight omitted: **`scene_flow_dispatcher`**, which contains every
live-evidence PC this row's lifecycle argument rests on, and
`frontend_scroll_sprite_screen` in `BITS/MEMORY.BIN` — an image the overlay table
could not even load, because it assumed a single overlay base.

Two independent confirmations that 37 is right: `resolved_hit` is now **124**,
matching `analysis/phase4_f01_frontier_extraction.json:accesses_into_windows`
exactly; and 124 − 58 enumerated writers = the **66** readers, which the verifier
derived separately. The reader count had understated by 32%.

Both the set and the ends are now **generated** from
`analysis/phase4_static_frontier_index.json`. A test re-derives the qualifying set
and fails if any admitted function is not walked.

### What it found — the safety claim is STRONGER than this row claimed

`resolved_writers_not_previously_enumerated` survived both widenings at **0**. The
verifier went further than anything recorded here: an independent whole-corpus
re-derivation over **all 21 images** found exactly the 58 enumerated writers — 0
extra, 0 missing — plus a byte-level sweep of every region outside the function
census (46,360 resident bytes, 79 gaps) finding **0 window idioms**.

### The escalation check is not vacuous, but has a named blind spot

`second_opinion.sites_reported_as_reaching_a_window: []` is a genuine negative:
the same analysis finds 124 window-reaching sites corpus-wide — all of them
already-known — against a large population of resident sites where the check
could have fired and did not.

> A specific figure for that population was quoted here and in the registry. The
> second verifier could not reproduce it from any artifact and neither could I, so
> it is **withdrawn rather than restated**. An unreproducible supporting number is
> worse than none: it invites the reader to treat the check as quantified when it
> is not.

⚠️ But the join is keyed on sites present in the ledger, and **9 of the 62 resident
hits are absent from the static index entirely** — all inside
`scene_flow_dispatcher`, whose index record is `analysis_status: ok` with **8 of
393** instructions analysed. Repo-wide that class is **57 records / 10,898
instructions** whose accesses are neither bounded nor listed as residual. Now
recorded in `item2_scope` as a named residual.

### Corrections applied

Stale ABI figures in prose (96/87 → the artifact's actual numbers), an
unreproducible "488 unanchored exclusions" claim dropped, a brittle debt-error
count removed (it varies with checkout state), three `item2_scope` misdescriptions
fixed — readers were *not* complete, no F01 tool reads `overlay_symbols.json`, and
typed-state *is* hash-bound — and `analysis/phase4_extent_audit.json` made a
property of the commit rather than of the operator's working tree.

### Disposition

`status: partial` stands — the verifier judged the row harder on itself than the
evidence requires. `disposition` moved from `bounded_exhausted_pending_reopen` to
**`reopened_by_fresh_verifier`**: the named defect is repaired, but only a fresh
verifier may bank a status and the one that reviewed this row declined to.

## 2026-08-06 (later) — the two fixes the verifier's report implied

**1. The soundness gate on the weakest tier did not run for the reader who mattered.**
`tests/test_region_provenance_bound_soundness.py` hardcoded `ROOT/"SCUS_942.88"`,
which is `.gitignore`d — so on a clean checkout, which is exactly what an
independent verifier has, the counterexample test errored instead of executing.
It now resolves `REBUILD/files/SCUS_942.88` first and skips explicitly if no
pristine image is present.

**2. The CFG-recovery gap was a hole in my own repair.** The 37-extent set was
derived from the index's `memory_accesses` — which are **CFG-reachable only**. A
window access sitting in an unreachable block would never have admitted its
function, and 22 records reach under half their extent (`scene_flow_dispatcher`:
8 of 393). The criterion was one CFG gap away from being wrong again.

So the criterion was removed. The resolver now scans **every code function in
every analysed image** — 1,058 extents, 32,778 accesses, 6 ms — and *discovers*
which extents reach a window instead of being told:

| | scope |
|---|---|
| **completeness claim** | whole corpus: 124 window-reaching accesses, **0** writers outside the enumerated set, 66 previously unlisted readers |
| **item-2 blocker denominator** | the 37 extents the corpus scan discovered to reach a window: 4,031 accesses, 238 unresolved stores |

**The discovered set came back as exactly the same 37, and every downstream figure
was unchanged.** The criterion was right — it is simply no longer load-bearing.
Deliberately not merged: an unresolved store in a function that never touches the
state is not an F01 blocker, and counting the corpus-wide 5,329 would inflate the
residual as badly as the hand-picked set once deflated it.

One bug found on the way, worth recording because it is the same shape as the
others: the hit-marking line sat after a `continue` in the resident branch, so the
discovery pass saw only overlays. A discovery pass that silently covers half the
corpus is exactly what this file keeps growing.


## 2026-08-06 (later) — index re-baseline verified SOUND; the fifth subset-as-whole

A third fresh detached verifier reviewed the jump-table import. **Verdict: sound —
it does not invent reachability.** It decoded all 869 table entries from the
pristine bytes itself (0 mismatches), re-derived all 36 sites with a stricter
slicer, confirmed the 36 tables tile `0x8001A900`–`0x8001C78C` with **zero
overlap**, and tested `load_jr_targets` against five hash-mismatch cases — all
fail closed. All 6,570 newly-reachable words decode as valid R3000; none is data.

It also **perturbed** the resolver: injecting all 408 jr targets as join points
created 389 previously-unmarked joins across ~40 functions, and every corpus figure
came back identical. The index-independence claim is now a measurement.

**F01's banked `bounded_exhausted` holds.** `resolved_writers_not_previously_enumerated`
would not move off 0 under the jr perturbation, the index A/B, or a byte sweep of
every uncensused region.

### The fifth subset-as-whole, as predicted

`range_type == 'code'` **is** a selection criterion, so "the whole corpus" was
overstated. It excludes 54 thunk records — one holding a resolved store — and
**47,420 bytes (8.3%) in no census record at all**. The largest gap is an
11,828-byte truncation of `per_object_mesh_draw_payload_emitter`, provably a
continuation of a function the table already names.

⚠️ **`tools/phase4_extent_audit.py` can never see this**: it audits declarations
*against* the static index, so a truncated census entry is invisible by
construction — "who chose the thing I'm verifying against?" one level deeper than
the audit reaches. The resolver's `scope` string now names the exclusion and cites
the verifier's sweep of all 47,420 bytes: 351 stores, 1,016 loads, **0
window-reaching**. Bounded rather than merely disclosed.

### Two corrections to my own work

- **A false claim in a commit message.** `fcc5b188` said "every artifact in the
  cascade is now built from committed inputs only". `analysis/phase4_evidence_dag.json`
  was not rebuilt, and it pinned four files byte-identical to the operator's
  **uncommitted** working tree. My regeneration of it is reverted. It cannot be
  rebuilt in a clean checkout at all — it requires `movies/`, and rejects a
  symlink — so the one artifact carrying WIP is the one no verifier can check.
  **Left as an open defect rather than papered over.**
- **A scope mislabel.** "Resident CFG coverage 90.9% → 96.4%" was the all-21-images
  figure. Resident-only is **90.3% → 97.1%**; overlays contributed no decoded jr
  sites and merely diluted the denominator. Corrected here and in the registry.

### What it advanced elsewhere

**C13_grain_harvester's frontier GREW**: visited functions 218 → 239, internal
edges 1,060 → 1,513, state intersections 54 → 59. Its earlier figures were a lower
bound. E08 gained 5 internal edges; E15 unchanged. **No row's `complete_frontier`
closes** — the ledger's unresolved accesses went *up* (16,558 → 18,176) because
more code is now visible. Honest progress, not closure.

## 2026-08-06 — the stopping decision, stated narrowly

Three fresh detached verifiers plus an independent review have now looked at this
row. The stopping decision is accepted, and it is **narrower than "F01 is done"**:

> Further widening of the **direct static writer census** is bounded-exhausted.
> Reopen on a **named falsifier** — changed image or census identity, a new window
> hit, a newly resolved writer, or indirect/callee evidence — **not** merely
> because F01 remains partial.

**This is not writer completeness, not Item-2 closure, and not row closure.**
The retained artifact says so itself: the writer set is *not* shown complete while
**5,654** corpus-wide unresolved stores remain, and the semantic checker reports
`item2_ready_for_review: false` and `strict_frontier_closed: false` with six
blockers.

### Two numbers I had stated wrongly

- **The 238-site accounting.** 238 = 23 proof + 41 convention + 73 unresolved +
  101 absent from the ledger. So **174 sites remain undisposed** by the
  typed-state join. Quoting "23 by proof, 41 by convention, 73 unresolved" reads
  as if 137 were the denominator; it is not.
- **The census repair.** 12,472 bytes / 92.77% describe all **six** extensions the
  tool proposed. I applied five and declined `0x80082108` (340 bytes, classified
  data). The committed census actually gained **12,132 bytes**, 90.11% →
  **92.70%**.

### Bookkeeping reconciled

The registry simultaneously said BANKED and carried a `promotion_note` asserting
verification was still pending — that note predated the reviews and is now marked
superseded. `disposition` is `bounded_exhausted_direct_static_writer_census`, and
this experiment's frontmatter matches instead of saying
`bounded_exhausted_pending_reopen`.

## 2026-08-06 (later still) — four of the six item-2 review blockers were WIRING

`analysis/phase4_f01_frontier_result.json` reported six review blockers. The
first thing worth recording is that **four of them said nothing about the game**.
They were defects in the query's own declarations, and they had been quietly
reproducing themselves every time the query regenerated.

| blocker | the actual defect |
|---|---|
| `UNUSED_BOUNDARY_OWNER` | both `boundary_owners` entries were keyed by CATEGORY NAMES. The checker keys an owner by an **edge identity** (`source@0xSITE->target`), so no emitted edge could ever match one. Structurally unusable. |
| `RESIDUAL_COVERAGE_INVALID` | each residual's `covered_ids` named **its own id** — not a boundary the checker emits — so both were rejected as covering a non-unknown. |
| `UNBOUNDED_UNKNOWN` | consequently the 58 real unknowns were covered by nothing at all, while the coverage list looked populated. |
| `ITEM2_CATEGORY_MISSING` | `callbacks` was `required` with zero records, because the static index has no callback field and nobody had built one. |

All four are cleared, and the repairs are structural rather than one-off:

- a boundary owner whose `edge` is not an edge the extractor emits is now a
  **hard extraction failure**, so the class cannot recur;
- residual coverage is **generated from a `covers` rule**, and the union is
  reconciled against the exact set of unknowns the query emits — a rule that goes
  short fails closed, and a hand-typed list of generated identities cannot be
  offered at all;
- `callbacks` and per-image `census_complete` are both **derived from a
  hash-pinned receipt** instead of declared.

**Two blockers remain and both are real.** `item2_ready_for_review` is still
`false` and `strict_frontier_closed` is still `false`.

### The callback surface, derived rather than declared

`tools/phase4_callback_probe.c` + `tools/phase4_frontier_static_census.py` decode
every aligned word of all 21 hash-verified images and report every code address
materialised by an adjacent `lui`/`addiu` or `lui`/`ori` pair, classified by how
the value leaves the site.

**49 sites, 32 registration groups, 46 distinct target functions.** Every group is
emitted `complete: false`; the probe is positive-only and its silence carries no
weight.

The check that it is finding function pointers and not constants is that **49 of
the 50 materialisations landing anywhere inside a code extent land exactly on a
function ENTRY** — noise would land at random offsets — and the one that does not
is listed in `excluded_interior_code_addresses` (a `LEVEL02_LEVEL1` buffer passed
to a resident helper).

The RE content is real. `slot:SCUS_942_88:r17+116` is five actor-behaviour
handlers registered at **actor+0x74** (`0x8004A02C`, `0x8004A0A0`, `0x8004A11C`,
`0x8004A144`, `0x8004A2B0`) from the block at `0x8004A568..0x8004A5D8`.
⚠️ Note the mover-VM `jalr` at `0x8004D1E8` loads **actor+0x7C**, not +0x74, so
the two are *not* paired without further evidence and this experiment does not
pair them. `registrar:SCUS_942_88:0x80065464` is `VSyncCallback`.

Seeding those 46 targets grew the closure from 658 to **756** functions — and the
window-access census did **not** move: still **124** accesses, 58 writers and 66
readers, 0 unemitted. That is the property the residual argument rests on, and it
is now a test: accesses are found by a whole-universe scan that never consults
reachability, so growing the closure cannot find more of them.

### Two probe defects, both of a familiar shape

- ⚠️ **The delay slot is where the registration happens.** The compiler fills jump
  delay slots with exactly the stores this census looks for:
  ```
  8004a56c: j     0x8004a620
  8004a570: sw    v0, 116(s1)      <- runs FIRST; v0 is the handler pointer
  ```
  Applying the jump's clobber at the jump and then decoding the delay slot lost
  eight registrations in that one block. This is the same hazard the ABI
  accelerator hit from the other side, where a `jal`'s argument is set in its
  delay slot. A positive control in `tests/test_phase4_frontier_static_census.py`
  pins it, with a negative control whose only difference is a merge point.
- ⚠️ **Overlay aliasing is not fixed by preferring the materialising image's code
  extents.** `LEVEL02_LEVEL1` and `LEVEL07_LEVEL` type their first words `data`
  where other overlays type the same words `code`, so a pointer built inside
  `LEVEL02_LEVEL1` fell through and was reported as a `LEVEL01_LEVEL` function —
  an image that is not even resident at the same time. Containment in the
  materialising image's **address range** now decides ownership, and an address
  that image does not type as code is reported as *no function*.

### `IMAGE_CENSUS_INCOMPLETE` is now a derived deficit of 508 references

`census_complete` was a per-image boolean the seed asserted. The seed set one
image `false` and the other **twenty were false by default because nobody had
decided them**. The extractor now refuses a seed that carries the field at all and
derives it:

> every byte is claimed by an indexed extent or falls in an enumerated gap; every
> load and store decoded inside those gaps has a **proved base**; and none of them
> reaches a window.

It deliberately does **not** mean the accesses inside the extents are resolved, and
it asserts **no semantic ownership** of any byte. The receipt states that.

**19 of 21 images pass.** The two that do not are `SCUS_942_88` (75 gaps, 36,276
bytes, **496 undecided memory references**) and `MEMORY` (7 gaps, 424 bytes, 12
undecided). The blocker stands on 508 named references rather than on twenty
images nobody looked at.

⚠️ Its resident gap total is **not** the gate's 33,888. This census partitions the
whole pinned FILE (471,040 bytes, including the 2,048-byte PS-X EXE header) against
static-index records; the gate partitions the loaded TEXT range (468,992 bytes)
against repaired extents. Different universes, and the receipt refuses to
reconcile them by arithmetic.

**A falsifier that did not fire: 0 gap references in any of the 21 images reach
either window.** The sweep reports unresolved bases rather than omitting them, so
this is a bounded negative over the decidable part, not a positive-only silence.
A synthetic image where the sweep *does* fire is in the test suite.

### Exact-set reconciliation with the static-ASM gate

The gate's contract demands exact-set reconciliation of its 235 typed indirect
sites, and says explicitly that aggregate-count equality is not sufficient. The
extractor now does it in both directions and **fails closed** on any resident
indirect site the gate's universe does not contain.

| | |
|---|---|
| resident indirect CALL sites in the query | 94 — **all 94** among the gate's 139 `jalr` sites, 0 query-only |
| resident indirect JUMP sites in the ledger | 51 — **all 51** among the gate's 96 `jr` sites, 0 ledger-only |
| gate sites outside this frontier | 45 `jalr` + 45 `jr` |
| out-of-gate-scope sites, named not dropped | 3 (the gate is resident-only) |

**What the gate decides for F01, measured rather than assumed:** it bounds the
target set of **every** resident indirect jump this frontier retains (51 of 51)
and of **none** of its indirect calls (0 of 94). All 87 of its resolved target sets
are `jr` switch islands; not one of its 139 `jalr` sites has a bounded target set.
So the expectation that the gate's indirect inventory would resolve F01's
*unbounded call* unknowns is wrong, and the reconciliation is what shows it. A
bounded target set is still retained as a blocker: knowing where a jump can go is
not the same as disposing of what it reaches.

⚠️ A first attempt at this reconciliation compared `'0x8004D1E8'.upper()` against
lowercase-`0x` keys and reported an intersection of **zero** across the board. The
counts were plausible; only the printed set difference exposed it. Compare parsed
integers, and print the difference, not the size of it.

### `MECHANICALLY_INCOMPLETE` is Item 2 itself, and is not indirect control flow

Worth stating plainly because the natural assumption is wrong. The ledger holds
**19,623** rows:

| category | rows |
|---|---:|
| `unresolved_accesses` | **19,320** (98.5%) |
| `unresolvable_direct_edges` | 67 |
| `omitted_direct_edges` | 86 |
| `indirect_jumps` | 53 |
| `omitted_incoming_callers` | 31 |
| `direct_jumps_out` | 30 |
| `unanalysed_extents` | 29 |
| `incoming_jumps` | 7 |
| `binary_scan_unscanned_images` | 0 |

`mechanically_complete` requires **every** category at zero. Indirect control flow
is 53 rows of 19,623; clearing this blocker means resolving effectively every
access in the closure. That is the open problem, not a wiring defect, and no
amount of indirect-target work moves it.

One mislabel found on the way: the 67 `unresolvable_direct_edges` are all
resident → `0x800Bxxxx` calls into the swapped overlay region. They are not
"unresolvable" in principle — the target set is the same VA in each overlay that
can be resident — and modelling them is a real next increment. They were left in
the ledger rather than promoted to owned boundaries, because owning them would be
manufacturing an excuse for something that is enumerable.

### The downstream effect, and the numbers that did not move

The typed-state compiler consumes this blocker ledger, so growing the closure made
`analysis/phase4_f01_typed_state.json` stale. Regenerated:

| | before | after |
|---|---:|---:|
| ledger unresolved sites | 18,188 | **19,320** |
| ledger unresolved stores | 7,412 | **7,910** |
| bounded by index convention | 2,714 | **2,745** |
| **acceptance fixture sites** | 238 | **238** |
| **bounded by proof / convention / unresolved** | 23 / 41 / 73 | **23 / 41 / 73** |
| **absent from the ledger** | 101 | **101** |
| `second_opinion.sites_reported_as_reaching_a_window` | `[]` | **`[]`** |
| ABI survey | 64 decided, 77 open | **byte-identical** |

So **64 of 238 decided and 174 undisposed is unchanged**, and the residual went up
because more code is visible — the same honest direction as the jump-table import.
`analysis/phase4_f01_frontier_resolve.json` is untouched (its pinned sha256 still
matches), so `resolved_writers_not_previously_enumerated` is still 0 and **no named
falsifier has fired**.

### ⚠️ The sixth subset-as-whole, found in this work

The brief for this pass said to assume a sixth instance of the recurring failure
exists. It did, in my own artifact, and it survived until a deliberate audit of my
own claims.

I reported "all 49 retained function-pointer sites land exactly on a function
entry" as the evidence that the probe finds pointers rather than constants — and
shipped `kept_sites_all_land_on_a_function_entry: true` plus a test asserting it.
**The retained site list is FILTERED to entry-landing rows.** The property is the
filter's selection criterion, so the claim is true by construction, the number
carries no information, and the test could never fail. It is the same shape as
every previous instance: a property proved over the thing being looked at,
reported as a property of the system.

The measurement that means something is the rate over the UNFILTERED population —
every materialisation that landed anywhere inside a code extent: **49 of 50**. The
artifact now reports that with its denominator attached, the one exclusion is
listed, and the test asserts the ratio and **fails if the denominator ever equals
the numerator**, because a 100% rate with nothing excluded is exactly the vacuous
form again.

A second, milder one was fixed the same way: `window_reaching_gap_references: 0`
now ships beside `gap_references_with_an_unprovable_base: 508`. The zero is a
bounded negative over the *decidable* part of the sweep; quoting it alone reads as
a clean sweep of every gap byte.

> The generalisation, since the specific instance keeps changing: **before
> reporting a rate or a count, check whether the set it is measured over was
> selected BY that property.** If it was, the number is a definition, not a
> finding.

### What did NOT change, deliberately

`status: partial` and item 2 `not_met` stand. The disposition stays
`bounded_exhausted_direct_static_writer_census` and the F01 row in
`analysis/mechanics_baseline.yaml` was **not edited** — only a fresh detached
verifier may bank a registry status, and nothing here is a status change. The
direct static writer census was not rerun, widened or reinterpreted.

## 2026-08-06 (later still) — the header universe, the index CFG, and the falsifier test

Operator-directed follow-up, in the order given: fix the census-universe defect,
integrate the gate's direct-edge algorithm into the index generator over its FULL
declared universe, regenerate the dependents as exact sets, then re-test
`resolved_writers_not_previously_enumerated` because the new direct/callee
evidence satisfies the named-falsifier rule.

### 1. The file universe is not the resident universe

The image census partitioned the whole pinned FILE, so `SCUS_942_88`'s 2,048-byte
PS-X EXE header appeared as an *unclassified gap*. That is an error of kind, not
of size: "unclassified" means resident bytes nobody has owned, and header bytes
are never loaded at all. Every level overlay had the same defect at 4 bytes.

The nonresident prefix is now DERIVED from the bytes — the PS-X EXE header states
its own load base and text size — and cross-checked against the index's declared
`header_rule.bytes`. Gap bytes 37,336 → **35,212**; undecided gap references
508 → **505** (three had been decoded out of header metadata).

⚠️ **The static index declares `header_rule.bytes = 0` for `SCUS_942_88`**, which
is wrong. The census reports the disagreement rather than overriding it silently,
and it is the only image where the two differ.

Because the universes now coincide, the census and the gate partition an
**identical 468,992-byte range** from two different extent sources, so they are
directly comparable. Differenced as exact sets, both directions: **73 identical
gaps, 0 gate-only, 1 census-only** — `0x8008219C..0x800822F0`, 340 bytes, which is
precisely the extension reviewed and DECLINED as data. Every differing region is
attributable to the extent source and none to the universe. The earlier "different
universes, do not reconcile by arithmetic" note is retired and replaced by that
reconciliation, which is now a checked artifact and a test.

### 2. The index walked each function from its own entry

`scene_flow_dispatcher` is the specimen and it is worth stating exactly:

```
8004fca0: lui  at, 0x8008
8004fca4: sw   zero, 9276(at)
8004fca8: jal  0x8005222c
8004fcac: addiu a0, zero, 1      <- delay slot
8004fcb0: lui  at, 0x8008
8004fcb4: sh   zero, 0x23a0(at)  <- a WRITER of 0x800823A0
8004fcb8: j    0x8004fb3c        <- leaves its own extent
8004fcbc: nop
```

Eight instructions, then out. The remaining 385 are entered from OUTSIDE — five
`j 0x8004fcc0` sites plus two branches — so a per-extent walk can never see them,
and the record still said `analysis_status: ok`.

`image_direct_cfg()` is the gate's algorithm over the index's full declared
universe, not F01's subset: seeds are the typed code/thunk extent entries, edges
are direct branch/jump/call targets, the post-call fall-through, and verified
`jr`-table targets. Nothing is seeded from an unreachable source.

| | before | after |
|---|---:|---:|
| reachable instructions | 115,535 | **117,552** |
| CFG coverage, all 21 images | 94.1% | **95.7%** |
| records with unreachable code | 29 | **16** |
| unreachable instructions | 7,280 | **5,263** |
| memory accesses recorded | 32,622 | **33,158** |
| index-visible window accesses | 115 | **124** |
| `scene_flow_dispatcher` | 8 / 393 | **393 / 393** |

⚠️ An externally entered block gets the stateless entry condition (`$zero` and the
proven constant `$gp` — what a call boundary already restores), so the meet can
only weaken. That withdraws **120** address resolutions corpus-wide, and they are
soundness corrections rather than losses: they had been resolved on the assumption
that a block could only be entered from its own function's entry.

⚠️⚠️ **My first attempt withdrew 1,320 instead of 120**, by handing that entry
condition to every block start inside the extent — including ones the function's
own walk reaches and the `jr` island targets it already follows. Sound, but
needlessly destructive, and it would have inflated every row's residual. Only a
block with a genuine CROSS-EXTENT predecessor may get it.

### 3. What the regeneration moved

| | before | after |
|---|---:|---:|
| frontier functions | 756 | **763** |
| window accesses emitted | 124 | **124** |
| writers / readers | 58 / 66 | **58 / 66** |
| accesses from the binary supplement | 9 | **0** |
| blocker ledger | 19,623 | **20,130** |
| **fixture: joined to ledger** | 137 | **141** |
| **fixture: absent from ledger** | 101 | **97** |
| **fixture: bounded by convention** | 41 | **45** |
| fixture: bounded by proof | 23 | **23** |
| fixture: still unresolved | 73 | **73** |
| **DECIDED of 238** | 64 | **68** |
| UNDISPOSED of 238 | 174 | **170** |

**68 of 238 decided is the first movement in that number since the second opinion
was extended to overlays**, and it is not a change to the fixture: the same 238
sites, four of which were previously absent from the ledger because their blocks
were unreachable from their own function's entry. All four land in the
convention bucket. Never quote 23 + 45 + 73 as though 141 were the denominator.

The binary supplement dropping to **0** is a result, not a regression: the index's
CFG recovery now reaches all nine accesses the linear scan used to be the sole
source of, so two independent methods agree on all 124 with no residue either way.
The test that asserted `supplement > 0` was replaced rather than relaxed, and now
fails if the number moves off zero in either direction.

### 4. The falsifier test — it does not fire

The named-falsifier rule reopens F01 on "indirect/callee evidence", and whole-image
direct-edge reachability is exactly that, so the test was run rather than assumed.

- The 9 window accesses the CFG recovery newly exposes are **exactly** the 9 the
  binary supplement already supplied — not one more, not one fewer.
- Index-visible writers 56 → 58; both new ones (`0x8004FE44`, `0x8004FE4C`) were
  already among the enumerated 58.
- **0 window accesses lost** despite the more conservative entry states.
- `analysis/phase4_f01_frontier_resolve.json` regenerates **BYTE-IDENTICAL**. It
  re-walks the images with its own recovery and takes only extents from the index,
  and the extents did not change — so `resolved_writers_not_previously_enumerated`
  stays **0** over 33,642 accesses in 1,058 extents.

**No named falsifier has fired.** What the pass produced instead is an independent
corroboration: a CFG walk with constant propagation and a linear adjacent-`lui`
scan now derive the same 124 window accesses and the same 58 writers by disjoint
routes.

### 5. Status

Unchanged, and correctly so. `item2_ready_for_review: false`,
`strict_frontier_closed: false`, review blockers still exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. `status: partial` and item 2
`not_met` stand; the F01 row in `analysis/mechanics_baseline.yaml` was not edited.
The direct static writer census was not rerun, widened or reinterpreted.

### Two pre-existing defects this surfaced

- `analysis/phase4_static_frontier_pilots.json` is **not a property of the
  commit**: it records `source_bytes_present` for `asm/hand_written/` sources, so
  it regenerates differently depending on whether the operator's external assembly
  happens to be on disk. The clean-checkout form is retained here, which fixes
  `test_e15_e08_and_c13_pilots_are_exact_and_non_promoting` and makes
  `test_all_static_outputs_recompute_byte_identically` fail **in the operator's
  tree only**. Same class as the `analysis/phase4_evidence_dag.json` defect already
  on the books.
- `tests/test_phase4_static_frontier.py` pinned 854 `$gp`-relative resolved
  accesses at `caf22652b2eb` and never tracked two index re-baselines. A clean
  checkout at the preceding commit already read **901**, so the assertion was red
  on master independently of this work; the CFG recovery took it to **915**.
  Re-pinned with that history recorded in the test.

## 2026-08-06 (review round) — three findings closed, then gap ownership

### The three review findings

**1a — "same universe" checked endpoints, not identity.** The reconciliation
compared only the load range, so a future changed image occupying
`0x80010000..0x80082800` would have reconciled as the same universe and its gap
differences would have been unattributable. It now also requires the census image
sha256 to equal the sha256 the gate pinned, and reports `same_resident_range`,
`same_image_identity` and both hashes separately so the conjunction is visible.

**1b — the expanded CFG consumed an unpinned input.** `image_direct_cfg()` follows
verified `JR_TARGETS`, but `analysis/phase3_jr_tables.json` was absent from the
index's `source_dependencies`, and the provenance recorded only "36 sites, 408
targets" — a shape, not an identity, satisfied by any wrong table of the same
size. The artifact hash is pinned, the exact (site, target) map is **retained** so
a verifier can difference it, and `identity_digest` covers that map.

The universe is also relabelled. The gate reports `indirect_edges_followed: false`;
this walk additionally follows verified `jr` targets, so `index.cfg_universe` now
says "direct branch/jump/call edges plus the hash-verified jr-table targets … NOT
the static-ASM gate's universe". Calling it "the gate's algorithm" was wrong.

**2 — the resident header declaration.** The index emitted `header_rule
{bytes: 0}` for every non-level image, including a PS-X EXE. Derived now from the
magic: `SCUS_942_88` 0 → **2048**. The census still derives its own prefix
independently, so the cross-check stays live; it reports zero disagreements
instead of one.

**3 — the pilots artifact's filesystem dependence.** `source_bytes_present` for
`asm/hand_written/` made a committed artifact regenerate differently depending on
whether operator-local bytes were on disk. It is `null` for external assembly now
— the document does not assert local presence — and `source_verification_method`
is unconditionally `repro_manifest_sha256`. **All 12 regenerated artifacts are now
byte-identical between the operator tree and a clean detached worktree**, closing
the operator-tree-only failure the previous commit had to name.

### Gap ownership, classified before the words are interpreted

The reviewer's instruction was the important part: treat the 505 rows as
instruction-shaped words in unclassified resident gaps, not as confirmed
executable references, and classify gap ownership first.

**No direct branch, jump or call edge from reachable code enters any gap in any
image.** Five ownership classes, each with its own source, none inferred from
another:

| class | basis | reach |
|---|---|---:|
| `not_directly_reachable` | no direct edge enters it — ⚠️ necessary, NOT sufficient | all 82 gaps |
| `zero_filled` | measured: every byte `0x00` | 62 gaps / 308 B |
| `decoded_jump_table` | overlaps a `phase3_jr_tables` table | 2 gaps / 1,248 B |
| `read_as_data` | resolved accesses from code land inside it | 6 gaps / 1,714 accesses |
| `targeted_by_a_proved_indirect_jump` | a gate-proved `jr` target lands inside it | 1 gap / 20 B |

**22,196 of 35,212 gap bytes now carry positive ownership evidence**; the residual
is **8 named gaps / 13,016 bytes**, dominated by `0x8007B63C` (8,068) and
`0x80075930` (4,216).

Two results worth recording:

- **`0x8007E8B8` (13,536 bytes, ending exactly at `$gp`) has 184 words proved data
  by resolved accesses from code.** The `$gp` alignment was a layout hypothesis;
  the reads are evidence. The region is not thereby owned in full — the covered
  *word* count ships beside the region size precisely so partial coverage is not
  read as whole-region ownership.
- **`0x8008219C` — the 340 bytes reviewed and DECLINED as a code extension — has
  70 words read as data.** The decision to decline is independently corroborated,
  and it is also the single region where the census and the gate's partitions
  differ.

### ⚠️ The two indirect sources are not interchangeable

The index's CFG consumes `analysis/phase3_jr_tables.json` — **36** `jr` sites. The
gate resolves **87**, a strict superset. `SCUS_942_88:0x8004C898`, the 20-byte
mover-dispatch target the gate names as its own ownership defect, is reached only
through `jr` at `0x8004C868`: no direct edge enters it, `phase3_jr_tables.json`
never decoded that site, and the index's walk therefore cannot see it. It is owned
here by the gate's resolution.

**Feeding the gate's extra 51 resolved `jr` sites into the index is the next
lever, and is deliberately not done here.**

⚠️ A first extraction of the gate's targets read `entries` and not `targets`,
reporting **38** distinct targets instead of **450** — it would have silently
under-owned every gap. The gate stores jump islands under `entries` and every
other kind under `targets`. Checked before use, not after.

### Status

Unchanged and correct: `item2_ready_for_review: false`,
`strict_frontier_closed: false`, blockers exactly `[IMAGE_CENSUS_INCOMPLETE,
MECHANICALLY_INCOMPLETE]`, fixture 238 with 23 proof / 45 convention / 73
unresolved and 97 ledger-absent, decided 68. `analysis/mechanics_baseline.yaml`,
the gate receipt and the writer-census resolver are untouched.

## 2026-08-06 (review round 2) — my gap-ownership report was itself a subset-as-whole

Four review findings. Three were defects in what I had just shipped, and the
first is the recurring failure appearing in my own reporting of the fix for it.

### 1. Whole-gap booleans overstated the residual by 86%

`has_positive_ownership_evidence` was a per-GAP flag, but `read_as_data` proves
something only about the words an access actually touches. So a 13,536-byte
region with a few hundred covered bytes was marked "has evidence", and I reported
the deficit as **8 gaps / 13,016 bytes** and called it the "last derived deficit".

Byte-exactly it is **24,258 bytes**. Every class now contributes byte INTERVALS,
they are unioned, and the complement is reported exactly:

| | bytes |
|---|---:|
| gap bytes, 86 gaps | 35,212 |
| with any evidence (union) | 10,954 |
| with **semantic** evidence (zero-fill excluded) | **2,414** |
| with **no evidence at all** | **24,258** |

The largest single unevidenced run is **3,105 bytes** at `0x8007B9D3`. The `$gp`
region has 730 bytes proved data and 3,729 with nothing.

⚠️ A second defect fell out of doing it byte-exactly: `zero_filled` was computed
over byte runs, and most MIPS instructions contain zero bytes, so `addiu rt,rs,0`
alone "evidenced" 5 scattered bytes of a 20-byte executable island. It is
aligned whole-zero WORDS now, which is the only granularity at which the claim
("carries no load/store encoding") is true. Zero-fill bytes 12,443 → 9,360.

### 2. "0 directly reachable gaps" was not a direct-edge result

The counter checked only edges that carry an ADDRESS — branch, jump, call target,
known `jr` target. Two boundary edges have no target field and were invisible:
ordinary **fallthrough** past the end of an extent, and the **pc+8 return
continuation** of a call or indirect call.

Adding fallthrough naively reported **67** edges into gaps. Every one was a
**delay slot** — the word after a jump runs before control transfers, and where
control goes next is the transfer's business: after `j`/`jr` it does not continue
linearly, and after `jal`/`jalr` it resumes at the call's pc+8, which
`call_return` already records. With delay slots excluded the figure is **0**
across all seven kinds, and the zero is authoritative in a way the earlier one
was not.

It still does not prove a gap is not code — an undecoded indirect jump can land
there, and `0x8004C898` is the living proof: 0 boundary edges, and executable.

### 3. Every class total I quoted was wrong

| I reported | artifact |
|---|---|
| 82 gaps | **86** |
| 62 zero-filled gaps / 308 bytes | **70 gaps / 508 bytes** (that was a SCUS-only figure quoted as a corpus total) |
| "6 gaps / 1,714 accesses" read as data | **8 gaps**, and 1,714 is an access-EVENT count covering **302 distinct words** |
| classes summed as buckets | they **overlap**; the union is 10,954, the sum 11,774 |

The receipt now carries `classes_overlap` stating they must not be summed, and a
test asserts the sum strictly exceeds the union so the caveat can never read as
false.

### 4. Planning correction: importing 51 jr sites will not reach 0x8004C898

The CFG word map is built only from existing executable extents, so a target
landing in a gap is discarded before the walk sees it. `0x8004C898` needs a
separately evidenced code extent or target-root decoding in unclassified bytes —
**not** a stretched neighbouring extent, which is the shortcut the gate itself
refused. Of its 20 bytes exactly 4 are evidenced: a proved target says an
instruction *starts* there and nothing about how far the island runs.

### The honest statement

> Gap triage advanced substantially, but whole-region ownership remains
> incomplete and has not yet been measured byte-exactly — until now, and the
> byte-exact answer is 24,258 unevidenced bytes, not 13,016.

No Item-2 blocker was reduced. `item2_ready_for_review: false`,
`strict_frontier_closed: false`, blockers `[IMAGE_CENSUS_INCOMPLETE,
MECHANICALLY_INCOMPLETE]`, fixture 238 with 23 proof / 45 convention / 73
unresolved and 97 ledger-absent, decided 68. Registry, gate receipt and the
writer-census resolver untouched.

## 2026-08-06 (work order) — dispositions, the gate-only jr set, and one decoded island

Executed as ordered. Commits and statuses preserved; nothing promoted.

### Explicit none / partial / complete

Byte-exact intervals were not enough on their own — a reader can still take
"has evidence" for "owned". Every gap now carries a disposition, and the corpus
answer is dominated by `partial`, which is exactly the answer this census
refuses to round up:

| disposition | gaps | bytes |
|---|---:|---:|
| `none` | 6 | 12,544 |
| `partial` | 9 | **22,140** |
| `complete` | 71 | 528 |

Union of evidence **10,970 bytes**; semantic (zero-fill excluded) **2,430**;
**24,242 bytes carry no evidence at all**.

### The 51 gate-only jr identities

The index consumed `analysis/phase3_jr_tables.json` (36 sites) while the shared
gate had resolved **87**. Imported with per-site provenance and an exact-set
check in the direction that matters: `phase3_sites_not_in_gate` is empty, so the
subset relation is measured, not assumed — a gate that had dropped a phase3 site
would be a disagreement rather than a silent merge.

| | before | after |
|---|---:|---:|
| reachable instructions | 117,552 | **121,412** |
| unreachable instructions | 5,263 | **1,403** |
| records with unreachable code | 16 | **13** |
| memory accesses recorded | 33,158 | **34,396** |

### One target-root island, decoded rather than assumed

⚠️ As the review predicted, importing the identities does **not** by itself reach
`0x8004C898`: the CFG word map is built from claimed extents, so a target landing
in unclaimed bytes is discarded before the walk sees it.

The island is decoded from its proved root with an explicit stopping proof, and
**no neighbouring extent was widened**:

```
8004c898: addiu s6, zero, 3
8004c89c: addiu v0, zero, 10
8004c8a0: sh    v0, 0x60(s0)
8004c8a4: lui   v0, 0x8000
8004c8a8: sw    v0, 0x50(s0)
8004c8ac: <- falls through into the entry of a claimed extent
```

**Stopping proof:** fallthrough reaches the gap end exactly, and the gap end is
the entry of a claimed executable extent. **RE content:** it is the `s6 = 3` arm
of the mover-VM dispatch at `0x8004C868`, joining the common tail at `0x8004C8AC`
— structurally identical to the four sibling arms at `0x8004C870`…`0x8004C890`
that reach the same tail by `j 0x8004c8ac`. The census boundary had cut it off.

It is **not** a census record: adding one would move the pinned
`expected_census_records` identity. Its extent, provenance and accesses live in
`target_root_islands`.

⚠️ **Consequence to state rather than bury:** because it is not a record, its two
stores are invisible to every per-record consumer — the F01 blocker ledger and
`tools/phase4_f01_frontier_resolve.c` alike. They are enumerated in the island
entry and nowhere else.

### The permitted writer falsifier, re-run

Over the widened CFG (+3,860 reachable instructions) and the island:

- index-visible window accesses **124 → 124**, gained 0, lost 0;
- writers **58 → 58**, no new, none lost;
- `analysis/phase4_f01_frontier_resolve.json` regenerates **byte-identical**, so
  `resolved_writers_not_previously_enumerated` stays **0** over 33,642 accesses.

⚠️ The island's two accesses are `sh v0, 0x60(s0)` and `sw v0, 0x50(s0)` —
register-based, so statically unresolved. They are **new blockers, not new
writers**, and reporting them as either would be wrong.

**The falsifier did not fire.**

### Status

`IMAGE_CENSUS_INCOMPLETE` is **not** cleared and must not be until every resident
gap byte has a defensible semantic disposition — 24,242 bytes do not.
`item2_ready_for_review: false`, `strict_frontier_closed: false`, blockers
unchanged, fixture 238 with 23 proof / 45 convention / 73 unresolved and 97
ledger-absent, decided 68. The ledger grew 20,130 → 20,722 because more code is
visible. Registry, gate receipt and resolver untouched.

## 2026-08-06 (increment) — the island IS a census record; one executable universe

The previous section stated the defect plainly and this increment removes it:
the island was stored only in `target_root_islands` *because adding a record
would move the pinned `expected_census_records`*. That is backwards — **the pin
is a change detector, not a reason to hide newly established executable code**
— and the concrete cost was that the island's two `s0`-relative stores were
invisible to every per-record consumer, so "the writer falsifier ran over the
island" was not bankable.

### The promotion, mechanically

- `tools/phase4_static_frontier.py` still DECODES the island from its proved
  root on every regeneration (stopping proof preserved, fail-closed: a failed
  decode now fails the pinned census counts), and then promotes it to a
  first-class `range_type: code` record named `jr_target_island_8004c898`,
  analysed by the same `analyze_code` path as every other extent. Neither
  neighbouring extent moved: `mover_vm_dispatch_next` still ends at
  `0x8004C898` and `vm_motion_apply_chase` still starts at `0x8004C8AC`.
- `target_root_islands` keeps ONLY discovery provenance (root, `reached_by`,
  stopping proof, gap bounds) plus `census_record: SCUS_942_88:0x8004C898`; the
  duplicated access list is gone, so there is exactly one definition of
  executable code and a test asserts the record set and the decode set are
  equal in both directions.
- The census identity was re-pinned INTENTIONALLY, and the delta was DERIVED,
  not assumed: the generator was run against the old pins first and its own
  count-mismatch errors named the change — records 1190 → **1191**, resident
  998 → **999**, resident code 900 → **901**. The config now pins
  `canonical_source_records: 1190` and `target_root_island_records: 1`
  separately so a moved canonical census and a moved island set stay
  distinguishable.

### Exact gained/lost sets, per consumer

| consumer | delta (exact sets, both directions) |
|---|---|
| F01 blocker ledger | gained exactly `unresolved_access:SCUS_942_88:jr_target_island_8004c898@0x8004c898@0x8004C8A0` and `…@0x8004C8A8`; **lost nothing**; every other category's id set identical |
| frontier closure | functions 763 → **764**; the island is seeded explicitly (`root_provenance.target_root_island_seeded: 1`) because the callee closure structurally cannot reach a unit whose only entry is a proved `jr` target |
| resolver corpus | extents 1058 → **1059**, accesses examined 33,642 → **33,644** (+ the 2 island stores), corpus unresolved stores 5,654 → **5,656** |
| resolver hits | 124 → 124, **gained none, lost none**; store-hits **58**, all 58 `already_enumerated`; `resolved_writers_not_previously_enumerated` = **0** |
| window-touching fixture | 814 unresolved sites / 238 stores — **unchanged** (the island extent resolves no window access, so it is not window-touching; its stores are corpus blockers, deliberately NOT labelled "outside the windows") |
| typed-state compiler | ledger 20,429 → **20,431**; the 2 sites land in `still_unresolved` (second-opinion verdict `out_of_scope`, honestly uncovered); fixture 238 = 23 proof / 45 convention / 73 unresolved + 97 absent, decided 68 — **unchanged**; ABI survey **byte-identical** |
| gap census | gaps 86 → **85**, gap bytes 35,212 → **35,192**; undecided instruction-shaped gap words 505 → **503** (the island's 2 stores left the gap universe for the census universe); dispositions `complete` 71 → 70 (528 → 508 B), `none` 6 / 12,544 B and `partial` 9 / 22,140 B unchanged; **unevidenced bytes 24,242 unchanged**; semantic evidence 2,430 → 2,410 (the 20 island bytes moved out of the gap universe, they were not lost) |

### The permitted falsifier, re-run over a universe that now CONTAINS the island

The narrow banked disposition (`bounded_exhausted_direct_static_writer_census`)
stands untouched; this is the named-falsifier regeneration, not a new census.
`tools/phase4_f01_frontier_resolve.c` was rebuilt (`-Werror`, self-test 2/2)
with its EXTENTS table regenerated from the index — now by a committed tool,
`tools/phase4_gen_resolver_extents.py --check`, so the third hand-typing defect
in that table cannot happen — and re-run over all 1,059 code extents:

- **writers remain exactly 58, all 58 already enumerated, 0 new, 0 lost;**
- `resolved_writers_not_previously_enumerated` remains **0** — and unlike the
  previous section's byte-identical result, this one is bankable, because the
  scanned universe now includes the island and classifies its two stores
  **UNKNOWN** (blockers, not writers, not resolved-away).

### The gate is a first-class pinned dependency

`analysis/phase4_static_asm_prerequisites.json` now sits in the index's main
`source_dependencies` with its sha256, alongside the per-site import report
(`phase3_sites_not_in_gate: []` — measured, both directions). `cfg_universe`
names its four constituents — direct edges from extent+island entries, phase3
jr targets, gate-only jr targets, decoded target-root islands — and states
explicitly that this is NOT the gate's algorithm (the gate reports
`indirect_edges_followed: false`).

One reconciliation consequence, named rather than smoothed over: the census ↔
gate resident partitions now differ in TWO regions — `identical_gaps` 73 → 72,
`gate_only_gaps` = the 20-byte island (the gate's receipt, untouched by
contract, still carries it as its named ownership defect), `census_only_gaps` =
the declined 340-byte `0x8008219C` extension, as before. Both attributable to
the extent source; the universe identity (range + image sha) still checks.

### Boundary-successor ratchet: delay-slot suppression is now context-sensitive

The old rule suppressed ordinary fallthrough from every delay-slot ADDRESS. But
an address can also be independently entered — branch/jump/jr target, not-taken
continuation, call return, extent entry — and in that context the instruction
continues linearly to pc+4. `gap_boundary_edges` now takes the walk's
`block_starts` and suppresses fallthrough only where the delay slot is the
address's SOLE established execution context. A mutation fixture pins the exact
sets on both arms: `beq zero,zero,+0` branching INTO its own delay slot must
report the fallthrough edge (the old rule, simulated by withholding the entry
set, returns `{}`); the same shape branching to itself keeps the empty set.

Recomputed over the real corpus, with the walk now ARMED with the same verified
jr universe as the index (both loaders fail closed on image hash; provenance in
the receipt under `cfg_jr_sources_armed`): **boundary edges into gaps = 0,
across all seven successor kinds, over all 21 images** — a zero that now
survives a strictly wider universe than the one that first produced it. It
still proves no gap is *directly* entered, and still says nothing about
undecoded indirect entries.

### Status — unchanged, deliberately

`status: partial`, item 2 `not_met`, `item2_ready_for_review: false`,
`strict_frontier_closed: false`, review blockers exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. 24,242 resident gap bytes
still carry no evidence, and the mechanical ledger GREW by two real blockers.
`analysis/mechanics_baseline.yaml` untouched; gate receipt untouched; the
direct static writer census not rerun, widened or reinterpreted.

### Pre-existing failures, distinguished

`tools/phase4_evidence_dag.py --check` reports 6 dirty nodes. Every one has
changed inputs this increment never touched (`tools/phase4_common.py`,
`analysis/mechanics_baseline.yaml`, capsule/coverage/queue artifacts) — dirt
that pre-exists on master since the DAG was last banked. This increment's
index/pilots identity change is one ADDITIONAL trigger on
`promotion_preflight`. The debt is left unregenerated here because it
pre-existed, is disclosed and attributed input-by-input, and this increment
attempts no promotion that would rest on it — not because any contract makes
it out of scope: the static-ASM ratchet contract governs the shared gate
machinery, and an increment modifying F01 artifacts is outside its acceptance
authority. Whoever next banks the DAG inherits the index/pilots trigger along
with the pre-existing ones.

### Reproduce

```bash
python3 tools/phase4_static_frontier.py --refresh   # then --check
python3 tools/phase4_frontier_static_census.py --output analysis/phase4_frontier_static_census.json
python3 tools/phase4_frontier_extractor.py config/phase4_f01_frontier_seed.yaml \
    --output config/phase4_f01_frontier_query.yaml \
    --summary analysis/phase4_f01_frontier_extraction.json \
    --blockers analysis/phase4_f01_frontier_blockers.json
python3 tools/phase4_semantic_frontier.py config/phase4_f01_frontier_query.yaml \
    --output analysis/phase4_f01_frontier_result.json
python3 tools/phase4_gen_resolver_extents.py --check
cc -O2 -Wall -Wextra -Werror -o /tmp/fr tools/phase4_f01_frontier_resolve.c
# ⚠️ EXIT 1 IS THE EXPECTED OUTCOME while Item 2 is open: it is the resolver's
# fail-closed "unresolved stores remain" exit, and the JSON is complete and
# valid. Do not chain it with && or run it under set -e and then read the
# stop as a failure; require exit 1, valid JSON, and byte identity.
/tmp/fr REBUILD/files > analysis/phase4_f01_frontier_resolve.json; test $? -eq 1
python3 tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
    --output analysis/phase4_f01_typed_state.json
python3 tools/phase4_extent_audit.py --json analysis/phase4_extent_audit.json
python3 -m pytest tests/test_phase4_static_frontier.py \
    tests/test_phase4_frontier_static_census.py \
    tests/test_phase4_frontier_extractor.py tests/test_phase4_typed_state.py \
    tests/test_phase4_extent_audit.py tests/test_phase4_semantic_frontier.py \
    tests/test_phase4_static_asm_prereqs.py -q
```

## 2026-08-06 (increment 2) — the island's two stores are DISPOSED, across the proved jr edge

The reviewer's follow-up authorized exactly one propagation: the proved `s0`
domain across the single gate-proved edge `0x8004C868 → 0x8004C898`, with an
exact two-ID movement required and **no generalisation of jr state
propagation**. That is what was built, plus the five review findings fixed
(resolver exit-code contract documented — exit 1 is the expected fail-closed
state, with valid JSON; the 35,192 gap-byte label corrected to the all-image
loaded-range total, 34,208 SCUS + 424 MEMORY + 560 across five level overlays;
the stale "gate's algorithm" docstring aligned with the retained
`cfg_universe`; the whole-image island seeding declared a conservative
superset in the extractor and its summary; the DAG paragraph reworded — the
debt stands because it pre-existed, is disclosed, and no promotion rests on
it, not because a contract makes it out of scope).

### The evidence chain, every link from instructions or the pinned index

Disassembly first (observation), then the machine checks (verification):

1. **The island is the `opcode==8` arm of a SECOND 16-entry VM dispatch.**
   `mover_vm_dispatch_next` commits the VM ip (`sw s1, 0x70(s0)`), fetches the
   opcode, subtracts 5, bounds-checks `sltiu v1, 0x10`, and jumps through the
   16-entry table at **0x8001B384** (distinct from the 26-op table 0x8001B2F4).
   The island sets `s6=3`, writes actor+0x60 = 10 and actor+0x50 = 0x80000000,
   and joins the common tail — its sibling arm at 0x8004C870 writes the same
   +0x60 field from its `j` delay slot.
2. **`s0` is invariant across the whole physical function.** The cluster
   0x8004C13C..0x8004D224 (interpreter + 26 op-handler records + dispatch +
   island + motion/chase tail) contains exactly TWO writes to `s0`: the
   straight-line prologue copy `addu s0, a0, zero` at 0x8004C144 and the
   terminal epilogue restore at 0x8004D214 (`jr ra` 0x8004D21C). Verified by a
   new `island@` query in the rebuilt `tools/phase4_typed_state_provenance.c`,
   which fails naming the offending pc if a third write ever appears.
3. **Nothing enters the cluster interior except the prologue.** Zero direct
   branch/jump/call edges from outside, zero proved jr targets from outside
   sites, zero callback registrations, zero recursive calls — measured from
   the pinned index, both jr sources included. The one caller image-wide is
   `mover_updater`'s `jal` at 0x8004D5E0.
4. **The caller's argument is a null-guarded actor-table load.** The delay
   slot passes `a0 = s0`, and the two observable definitions of that `s0`
   reaching the call are `lw s0, 0x748(0x80090000)` at 0x8004D44C (element 0)
   and `lw s0, 0x748(at)`, at = 0x80090000 + 4*s3, at 0x8004D660 (element
   [s3]) — `every_observable_def_loads_one_address: true`, `loaded_from:
   0x80090748`, `entry_reachable_uses: 0`, by the SAME machinery that proved
   the 0x8004ABF4 binding. Both loads are null-guarded straight into the
   terminal epilogue; the first loop's offset-cursor writes are dead at the
   call. ~~The table's image-wide writer census is corroborated: 4 writers, 3
   null-clears, 1 publisher of pool slots (0x8004D378).~~ **Historical
   attestation, superseded below:** the corrected recognizer finds ≥6 known
   writers and retains nonzero recognizer and alias residuals.

Therefore `s0` at the island ∈ the actor pool, and the stores reach
[0x8009FDE0, 0x800A1EE4) and [0x8009FDD0, 0x800A1ED4) — both entirely outside
both windows.

### What shipped

- `tools/phase4_typed_state_provenance.c`: the `island@` query (prologue
  straight-line copy check, whole-cluster register write census with a
  terminal-epilogue recogniser, call-site delay-slot decode, island access
  enumeration). Self-test still 3/3.
- `tools/phase4_typed_state.py`: provenance kind `proved_jr_cluster_argument`
  — island records only, exactly one proved edge, cluster must tile exactly
  onto contiguous index records, entry integrity from the pinned index, caller
  typing per typed_pointer_load, writer corroboration shared via a factored
  helper. The jalr caveat travels IN the attestation as a named residual
  assumption.
- `config/phase4_f01_typed_state.yaml`: the binding, with every locator
  re-derived per run.
- Tests: the real binding's exact facts; **exact two-ID movement**; wrong
  table rejected; prologue-cut-off cluster rejected (by the instructions, not
  bookkeeping); head-cut-off cluster rejected (entry integrity); and a
  deliberately SOUND alternative cluster [0x8004C13C, 0x8004C8AC) accepted —
  the first draft of that arm assumed the chase tail loops back and the
  instructions said no, so the control now pins that the checker verifies the
  property rather than pattern-matching one blessed declaration.

### The exact movement

| | before | after |
|---|---:|---:|
| bounded by proof | 273 (118 stores) | **275 (120 stores)** |
| still unresolved | 17,389 (7,183 stores) | **17,387 (7,181 stores)** |
| moved IDs | — | exactly `…jr_target_island_8004c898@0x8004c898@0x8004C8A0` and `…@0x8004C8A8` |
| ledger rows | 20,431 | **20,431** (the ledger states what the INDEX cannot resolve; the disposition lives in the typed-state artifact) |
| acceptance fixture | 238 = 23/45/73 + 97 absent | **unchanged** (the island is not window-touching, so it is not fixture scope) |
| ABI survey | — | **byte-identical** (island sites never entered its blocked-group universe) |
| resolver | 1,059 extents / 33,644 accesses, writers 58/58, 0 new | **unchanged** except the corrected scope label |

These are the first two blockers ever retired by evidence that crosses a jr
edge, and the first disposition of island-class sites.

### Status

Unchanged: `partial`, item 2 `not_met`, review blockers exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`, both review booleans
false. The fixture's 73 unresolved and 97 absent stand; 24,242 unevidenced gap
bytes stand. Registry, gate receipt, and the writer census untouched.

## 2026-08-06 (review round 3) — the two island dispositions are REOPENED

Codex's review of increment 2 found two substantive gaps in the chain, and it
is right on both. The two stores are **back in `still_unresolved`**
(bounded-by-proof 275 → **273**), and the reopening is enforced by a gate, not
by deleting the binding.

### Finding 1 (closed this round): "loads from the table" ≠ "points into the region"

Nothing machine-checked that the values WRITTEN into `0x80090748` are pool
pointers — the compiler substituted the declared `actor_pool` interval on the
strength of the load address alone. Now closed for every enumerated writer:

- the three null-clears are proved by encoding (the value register IS `$zero`);
- the publisher `sw s2, 0x748(at)` at `0x8004D378` is proved by a new
  `progression@` query in the rebuilt C verifier: every definition of `s2` in
  `mover_updater` is the shadowed/agreeing constant anchor **0x8009FD80**, a
  uniform positive self-adjustment **+0x84**, or a terminal-epilogue reload —
  so every value it can ever hold is `0x8009FD80 + k·0x84, k ≥ 0`. A lower
  bound and a lattice; **no upper bound claimed**.

⚠️ Two classifier defects were caught while building it, both worth keeping:
the observability walk follows the LINEAR successor out of a delay slot, so
`addiu s2, s2, 0x84` at `0x8004D3FC` (the `j`-delay-slot step) is reported
dead while execution demonstrably carries its value into the next iteration —
a proof must not rest on a reach analysis with a known miss direction, so
`progression@` classifies EVERY definition with no reachability argument at
all. And the `addiu` half of a `lui/addiu` materialisation pair has `rs ==
rd`, so self-adjust classification must come AFTER constant resolution or the
anchor reads as a −640 "adjustment" of the `lui`'s throwaway value.

### Finding 3 (closed this round): entry integrity over the real universe

The index-record scan covered one image and three edge kinds. Replaced with
the census's own regime: every instruction reachable in **all 21 images**
(direct edges plus both armed verified jr sources), all **seven successor
kinds** — fallthrough under the context-sensitive delay-slot rule,
branch, jump, call, call-return, indirect-call-return, resolved-indirect-jump
— with any non-`call` successor landing **exactly at cluster.start** treated
as an untyped entry and rejected. Result on the real corpus: 21 images
walked, **0 intruders**, and the walk's caller set equals the index's caller
set exactly. A real-data mutation now pins the jr-at-start rule: declaring the
cluster to start at the island entry puts the proved jr outside it, and the
checker rejects.

### Finding 2 (measured, NOT closed — and it is the gate)

The then-current 4-writer result is a one-spelling scan corroborated only against stores
the index already resolved; neither can exclude a computed-address store from
aliasing the table. Measured with the independent region analyser over the
table window `[0x80090748, 0x8009084C)` on every image: **5,012 stores
corpus-wide (4,359 in SCUS_942_88 alone) have undecided effective addresses
that nothing bounds away from the table.** The receipt also shows the
one-spelling scan's blindness directly: the two INDEXED writers
(`0x8004D378`, `0x8004D43C`) are absent from the sweep's own resolved hits.

**Count superseded below, gate preserved:** the corrected C spelling now finds
six known writers, while its 10,995-word residual and this same 5,012-store
region residual remain nonzero. This paragraph records why the exhaustiveness
gate was introduced; it is not a present four-writer claim.

The binding is now **gated on `table_writer_universe.exhaustive`** and is
rejected with that named, measured link — the enumerated writer set is a
corroborated LOWER BOUND, not a census. This is the same open problem as
Item 2 itself, in miniature: proving no unknown store aliases a 0x104-byte
window is not easier than proving no unknown store aliases the two 2-byte
windows F01 watches.

### The consistency question, named rather than resolved

The pre-existing `typed_pointer_load` binding (`0x8004ABF4`, same table) rests
on the SAME chain. At this review stage its value domains were recorded as
machine-proved; the hard-truth correction below narrows that: the direct null
and publisher facts are proved, while `0x80049C10` is only a conditional
same-table move. The same
exhaustiveness measurement is attached to its attestation — **non-gating**,
because its acceptance bar was banked by two fresh verifiers with the
writers-scan heuristic disclosed as a known limit. Whether the stricter gate
should also govern it — which would move ~19 of the fixture's 23 proof-bounded
stores out of that bucket — is recorded in the artifact
(`consistency_note`) as a decision for the next fresh verifier, not resolved
unilaterally in either direction.

### Numbers

| | after increment 2 | now |
|---|---:|---:|
| bounded by proof | 275 (120 stores) | **273 (118 stores)** |
| still unresolved | 17,387 | **17,389** (the two island IDs, exactly) |
| fixture | 238 = 23/45/73 + 97 | **unchanged** |
| ABI survey | byte-identical | **byte-identical** |
| binding verdict | verified | **rejected: writer universe not proved exhaustive (5,012 undecided stores, measured)** |

### Planning correction (review finding 4, accepted)

A "<~10 sites decided → stop" rule is a cost/yield heuristic, not a bankable
boundary. If the locally-computed-base work is attempted and stalls, the only
bankable form is `bounded_exhausted_<named method>` with the eligible universe
defined exactly, every eligible site processed, per-site failure reasons
retained, and reopening falsifiers named — the same shape the writer census
was banked in. "Irreducible by current static means" is not available after
one low-yield attempt.

## 2026-08-06 — the locally-computed-base campaign, in the bankable shape

The measured next lever, executed under the corrected stopping discipline: the
eligible universe defined exactly, every site processed, a per-site
machine-derived failure reason retained, falsifiers named. Tool:
`tools/phase4_f01_local_base_recovery.py`; artifact:
`analysis/phase4_f01_local_base_recovery.json`; 9 tests.

### The universe, derived not declared

Every acceptance-fixture STORE whose ledger verdict in the retained
typed-state artifact is `still_unresolved` — i.e. already undecided by
constant propagation, the ABI accelerator, typed-pointer loads, the proved-jr
chain, AND the convention-tier second opinion. **79 image-qualified site
rows** (73 fixture stores; cross-overlay pc aliases produce a row per
candidate image, listed never collapsed). A test reconciles the universe as an
exact image-qualified set — its own first draft did a pc-only join and
invented 36 phantom sites, every one a cross-image alias, the recurring bug
this repo keeps catching.

### The result: 0 decided by proof, 9 named walls

| outcome | sites | the wall |
|---|---:|---|
| `blocked_writer_universe_exhaustiveness` | 25 | base loaded from a fixed cell; typing cell content is the SAME gate the island binding is rejected on |
| `blocked_index_sign_needs_convention` | 15 | base = table + unrecovered index; only the non-negative-index convention excludes it, and this campaign does not relabel a convention as proof |
| `blocked_no_recovery_method` | 10 | raw observable definitions retained as the reason |
| `blocked_return_domain_unrecovered` | 9 | callee returns don't reduce to one typed domain within one copy hop |
| `blocked_no_direct_caller` | 7 | jalr-dispatched handlers (seed_plant_trampoline, berry_tough_damage) — the enumerated indirect-call blocker |
| `blocked_return_domain_needs_index_convention` | 6 | every callee returns spawn_drop's drop-array `0x800B0D18` + an unrecovered index |
| `blocked_stack_entry_value_caller_dependent` | 5 | sp-relative after frame adjust; entry sp is the caller's |
| `blocked_external_interior_entry` | 1 | REAL: resident scene-verb dispatch `jal`s fixed overlay VAs (`0x8003F54C`, `0x800548AC`…) that are INTERIOR addresses in LEVEL04_LEVEL1's layout — fail-closed, and an RE finding in its own right |
| `blocked_progression_delta_not_uniform_positive` | 1 | anchor `0x800A653E` with stride −2: descending, no lower bound |

RE content surfaced on the way: `spawn_drop` (0x80059E44) returns `v0 = s1 =`
an element of the 64-entry drop array at **0x800B0D18** (cursor `0x8008234C`
cycling mod 0x40), and the empty-class mystery sites were all stores in `j`
delay slots reading bases from fixed cells (e.g. `0x8009FE84`, actor-pool
interior).

### ⚠️⚠️ The shared verifier's delay-slot successor model was WRONG — third strike, now fixed

`succs_of` routed a transfer's edges from the transfer itself and gave the
delay slot a plain linear successor. Strike one hid a delay-slot DEFINITION
(`0x8004D3FC`); strike two was worked around in `progression@`; strike three
was UNSAFE: a store in a `j` delay slot (`0x800B3EF4`) was unreachable by both
the observability and entry-reachability walks — zero observable definitions,
yet reported "governed", a vacuous answer in the direction that could mint a
false bound. The model is now architecturally correct (transfer → delay slot →
the transfer's targets), pinned by test on the real site.

**Measured blast radius of the fix: zero verdicts moved.** The regenerated
typed-state artifact differs ONLY in the verifier hashes — every definition,
observability flag, binding verdict and bucket count is byte-identical
(273/23/45/73 all stand); the ABI survey shifts only rejected groups' def
counts (11→13, 5→6) in already-rejected verdicts. The corrected walk confirms
the existing evidence rather than disturbing it.

### Campaign disposition — staged, not banked

`bounded_exhausted_locally_computed_base_recovery`, with the method defined
exactly (classification + one site-level copy hop + per-site return typing
with one hop + direct-caller entry-value recovery + the anchored-progression
lower-bound proof) and reopening falsifiers named: a direct caller appearing,
any jalr target set bounded, a table-writer universe proved exhaustive, an
instruction-derived index-sign proof, a deeper return-domain method. Banking
authority: a fresh detached verifier only.

## 2026-08-06 — capsule-first runtime query: the two big gaps and the table

Per the standing rule, the retained trace capsules were queried BEFORE any
live replay. Tool: `tools/phase4_f01_capsule_gap_query.py`; receipt:
`analysis/phase4_f01_capsule_gap_query.json`. Universe: the ENTIRE retained
corpus — **50 capsules, 50,102 captured frames**, spanning LEVEL01 through
LEVEL11 scenarios — with per-capsule manifest hashes checked against the
preservation index and the reader's per-frame full-image reconstruction
hashes as integrity. The queried ranges are re-derived from the census each
run (they must BE the disposition-none gaps, not a memory of them).

### The four measurements, exactly

| measurement | result |
|---|---|
| basic-block starts inside `0x8007B63C..0x8007D5C0` or `0x80075930..0x800769A8` | **0**, all 50 capsules |
| runtime RAM writes touching either gap (anchor snapshots excluded) | **0**, all 50 capsules |
| gap bytes at each capsule's anchor vs the pristine disc image | **50/50 byte-identical** — nothing observably modified them between COLD BOOT and any anchor either |
| actor-table window `[0x80090748, 0x8009084C)` writes | **405 events / 1,085 u32 values: 198 null + 887 pool-lattice + 0 outside** — the writer-value falsifier did NOT fire |

The block-start probe and the static boundary-edge census close each other's
blind spot: linear overrun into a gap is excluded statically (zero direct
edges enter any gap, all seven successor kinds), and undecoded indirect entry
is what the runtime block starts would have caught.

⚠️ Two sample-as-whole traps dodged on the way: the first sweep counted each
capsule's ANCHOR-frame snapshot delta as a "gap write" (every capsule showed
exactly 2 — the two initial-image loads), and the first table pass retained
only 20 events per capsule. Both were redone: anchors excluded by the
`initial` flag, and the table pass rerun over the COMPLETE event set.

### What this does and does not change

The table result is live corroboration of the machine-proved writer value
domain — every observed value across every captured run is null or a pool
slot — but it is VALUE-level evidence over captured runs: no writer PCs, and
the exhaustiveness gate is untouched. The gap zeros are **bounded
non-observations**: 12,284 bytes that no captured run executed, wrote, or
modified since boot — still not owned, so `IMAGE_CENSUS_INCOMPLETE` stands
and the census does not move. What the receipt DOES do is name the missing
domains exactly — reads, writer PCs, jalr caller identity — which per the
escalation rule justifies a live isolated Interpreter-movie replay with
accessLog watches and a positive control as the next runtime step.

## 2026-08-06 — the live replay: both gaps identified, the writer census corrected, both jalr sites named

The escalation the capsule receipt justified, executed on a fresh isolated
Interpreter instance (fork `fe0cca16`, dirty docs only; movie anchors re-mount
the recording-time disc copy, sha256-identical to pristine — matched on
serial+title with the path swap recorded). Two Interpreter Any% movies
replayed end-to-end under 53 armed watches with chunked `movie.advanceToFrame`
(the watch load runs ~4 fps and the server times out long advances — 48-frame
chunks, every structured completion checked). Positive controls fired in both
runs (player block 1,963/9,241 events; transition timer 71/71). Receipt:
`analysis/phase4_f01_live_gap_read_receipt.json`; raw payloads preserved in
the external evidence store.

### The two "no-evidence" gaps are the game's trigonometry tables

| gap | verdict | evidence |
|---|---|---|
| `0x8007B63C..0x8007D5C0` (8,068 B) | **PsyQ `RotMatrix`'s sin/cos table** | 1,996 + 118 reads, every reader PC inside `RotMatrix` (0x80060854); zero writes, zero executions |
| `0x80075930..0x800769A8` (4,216 B) | **the game's own sine table** | 101,015 + 145,118 reads (~31/frame; two tiles saturated their 20k caps — lower bounds); readers: `gte_rotation_matrix_setup` (dominant), `contact_vs_actor_handler`, `camera_follow_update`, `player_vertical_update`; zero writes, zero executions |

Read-only, never written, never executed, consumed constantly — consistent
with every capsule negative (which could not see reads). The census stays
formally unevidenced until STATIC resolved accesses corroborate these readers,
but the follow-up is now concrete: resolve the table-base materialisations in
four named functions.

### ⚠️⚠️ The actor-table writer census is CORRECTED: not 4 writers — at least 6

The live write watch on `0x80090748` observed the four enumerated writers
exactly — and **two more**: `0x80049C10` (`sw a0, 0x0(v1)` — moves an existing
table value; observed moving pool slot 63, `0x800A1DFC`) and `0x80049C14`
(`sw zero, 0x0(v0)` — nulls the source), both in
`enemy_deathanim_finalize_remove_from_list@0x80049B60` — the actor-table
COMPACTION that runs when an enemy is removed. Computed bases
(`a1 = 0x80090748` materialised at `0x80049BF4/BF8`, then indexed `addu`) —
exactly the spelling the one-spelling writers scan cannot see and the
index cross-check cannot corroborate. Confirmed at instruction level from the
event's own `instruction_word` plus disassembly, not the ±4 heuristic.

Consequences, stated plainly: every "4 writers image-wide, corroborated"
attestation described a **lower bound**, as the review's finding 2 argued and
the exhaustiveness gate already assumed — the island binding's rejection is
empirically vindicated. The observed values (an existing pool slot, null)
stay inside the proved value domain, so the capsule value-sweep result
remains true. The `typed_pointer_load` consistency question deferred to the
next fresh verifier is now materially strengthened: its
`writer_enumeration_corroborated: true` rests on a corroboration mechanism
demonstrated incomplete.

### Both caller-less handlers have named dispatch sites

`ra` captured at entry, dispatch site = ra − 8:

- `seed_plant_trampoline_handler@0x8005C58C` ← jalr at **`0x8005BFE4`** in
  `plant_behavior_walker@0x8005BFBC` (699 hits)
- `berry_tough_damage_dispatch@0x8005905C` ← jalr at **`0x80058EB8`** in
  `contact_vs_actor_handler@0x80058AF8` (14 hits)

One observed site per handler names a target of that jalr — a lead for
proving the dispatch table statically, NOT a bounded target set. This is the
concrete unlock path for the campaign's 7 `blocked_no_direct_caller` stores.

### Status

Unchanged: `partial`, item 2 `not_met`, blockers exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. Nothing here closes a
gate; three named leads now exist where three walls stood.

## 2026-08-06 — static hard-truth follow-up: trig tables proved; the two claimed jalr sites falsified

This follow-up started from commit
`1bba2487b1b6f3e9d7669947de494ba649b99b70`, verified the pristine executable
as SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`,
and used the new C probe `tools/phase4_f01_static_hard_truth.c`. The probe checks
the PS-X EXE layout and 144 pinned instruction words before deriving anything.
Receipt: `analysis/phase4_f01_static_hard_truth.json`.

No new DuckStation run was needed. The retained-capsule query came first, the
live replay supplied named leads, and the pinned pristine instructions/content
answered the missing static domains. The raw replay payloads remain only under
the external evidence root named by the live receipt.

### Both trig gaps now have two-leg static semantic evidence

The ownership class `content_verified_trigonometric_table` is accepted only when
both legs pass: a complete-table mathematical byte comparison with zero mismatch,
and instruction-derived address ranges for the named readers that intersect the
exact pre-existing gap. Either leg alone fails closed; the full table description
does not widen any indexed extent. Canon record:
[[MEM_80074970_trigonometric_tables]].

| table | exact content model | reader evidence | disposed gap bytes |
|---|---|---|---:|
| raw Q14 sine | base `0x80074970`, 5,120 signed little-endian 16-bit entries, stride 2, amplitude 16,384, period 4,096; entry `i = llround(16384*sin(2*pi*i/4096))`; all 5,120 match | 23 derived load ranges: 6 in `gte_rotation_matrix_setup`, 2 in `contact_vs_actor_handler`, 7 in `camera_follow_update`, 8 in `player_vertical_update` | `0x80075930..0x800769A8`, 2,108 entries / **4,216 B** |
| packed Q12 RotMatrix pair | base `0x8007A7E4`, 4,096 little-endian words, stride 4, each word signed-16 `(f(i), f(i+1024))`, amplitude 4,096; `f(j)=llround(4096*sin(2*pi*(j+(((j mod 4096)>>10)&1))/4096))`; all 4,096 match | 6 `lw` ranges in `RotMatrix`, each derived from `andi 0x0fff`, `sll 2`, `lui/addu`, `lw -0x581c` | `0x8007B63C..0x8007D5C0`, 2,017 entries / **8,068 B** |

The unusual one-step phase correction in Q12 quadrants 1 and 3 is part of the
derived model; omitting it produces mismatches and is not rounded away. Reader
identity is reconciled as the exact `(image, pc, range, table)` set in both
directions between the C receipt and regenerated static index: 29/29, no
receipt-only or index-only entries.

### Byte-exact census movement

The resident gap universe is now **85 gaps / 35,192 bytes**. The new class moves
exactly **12,284 of the prior 24,242 unevidenced bytes**; it moves no byte outside
the two named intervals.

| measure | before | after |
|---|---:|---:|
| bytes with any evidence | 10,950 | **23,234** |
| bytes with semantic evidence | 2,410 | **14,694** |
| bytes with no evidence | 24,242 | **11,958** |
| dispositions | 6 none / 9 partial / 70 complete over the same 85-gap prerequisite universe | **4 none / 9 partial / 72 complete** |

The largest remaining single unevidenced run is **1,840 bytes at
`0x8007E8B8..0x8007EFE8`**. `SCUS_942_88` and `MEMORY` remain incomplete, so
the image census is still 19/21 and `IMAGE_CENSUS_INCOMPLETE` stays set.

### The requested dispatch sites fail closed because neither is jalr

Instruction evidence falsifies the live receipt's `ra - 8` attribution:

| claimed site | pinned word | actual decode | verdict |
|---|---|---|---|
| `0x8005BFE4` | `0x0C00E392` | direct `jal 0x80038E48` | no dispatch table and no target set exists at this PC |
| `0x80058EB8` | `0x0C0180A1` | direct `jal 0x80060284` | no dispatch table and no target set exists at this PC |

The real nearby table controls were independently enumerated by C and reconciled
against both Phase 3 and the gate as exact `(index,target)` sets in both
directions:

- `jr v0@0x8005C108`, table `0x8001B848`, stride 4, domain 0..12 proved by
  `sltiu v0,v1,13@0x8005C0EC`: 13 entries / 10 distinct targets. The observed
  seed handler `0x8005C58C` is entry 3.
- `jr v0@0x80058E78`, table `0x8001B748`, stride 4, domain 0..11 proved by
  `sltiu v0,v1,12@0x80058E5C`: 12 entries / 6 distinct targets. The berry
  handler `0x8005905C` is **not** a member. Its actual incoming edges are direct
  branches `0x80058EE8` and `0x80058F08`; those branches do not relink `ra`, so
  entry-time `ra - 8` names the earlier helper call.

Both real `jr` tables were already registered and byte-identical to the existing
Phase-3/gate imports. New sites `{}`, removed sites `{}`; phase3-only `{}` and
C-only `{}` for both tables. Therefore no count was re-pinned and the gate
receipt was not edited. Runtime attribution is retained as the historical lead,
but is superseded by this instruction result.

### Corrected writer query: six known, still non-exhaustive

`writers@SCUS_942_88:0x80090748` now recognizes the
materialise-then-scaled-index spelling. It produces the exact known lower-bound
set `{0x8003A49C,0x80049C10,0x80049C14,0x8004A4B4,0x8004D378,0x8004D43C}`:
gained `{0x80049C10,0x80049C14}`, lost `{}`. The query names its complete
syntactic universe—11,001 aligned resident-image words whose opcode is
`sb`/`sh`/`sw`—and reports **10,995 unclassified words**. They are not asserted
to alias the table; they are the positive recognizer's residual and forbid an
exhaustive claim.

The independent 21-image region sweep is re-attested too: **5,012 undecided
stores**, resolved table writers `{0x8003A49C,0x8004A4B4}`, corrected known
writers absent from those resolved hits
`{0x80049C10,0x80049C14,0x8004D378,0x8004D43C}`, and
`resolved_writers_not_previously_enumerated = {}`. That empty set is measured
only over the resolved hits; it is not writer completeness.

Value-domain facts are separated:

- `0x80049C14` is null by encoded `$zero`: proved.
- `0x80049C10` loads at `0x80049C08` and writes the value to another entry in
  the same table: the move relation is proved, the pool∪null value domain is
  **not**. It would require bounded source/destination indices, a null/pool
  initial table, every non-move publisher preserving that domain, an exhaustive
  writer universe, and then a least-fixed-point induction. Assuming table
  contents to prove table contents would be circular.

Both table-backed bindings carry the corrected count and residual. The
`proved_jr_cluster_argument` island remains rejected; its two stores remain
reopened.

On 2026-08-07 the required fresh Hard-Truth verifier **rejected** candidate
`5e1516a681a26f3934b7d0929c663ba0f33289e3`: the older
`typed_pointer_load` binding consumed the same table yet was `accepted: true`
while its own attestation said `writer_value_domains_proved: false` and
`table_writer_universe.exhaustive: false` (5,012 undecided stores). The
falsified four-writer premise cannot be grandfathered as proof. The compiler
now gates both table-backed binding kinds on both predicates. Consequently all
54 accesses formerly attributed to `typed_pointer_load` move from proof to
`still_unresolved`, including all 23 of its fixture stores. Exact typed-state
counts become **219 proof / 2,769 convention / 17,443 unresolved** over the
20,431-access ledger; store counts are **95 / 973 / 7,206**. The fixture is now
**238 = 0 proof / 45 convention / 96 unresolved + 97 absent**, only 45 decided.
Neither table-backed binding is accepted.

### Campaign rerun: 23 rows reopen, seven shared classifications move, zero sites become proof

The campaign now consumes every exact direct call/jump/branch edge and every
already-proved `jr` edge relevant to a handler entry, checking non-call delay
slots for a base-register rewrite. With the Hard-Truth ratchet the eligible
universe is **102 rows**, all processed, **0 decided by proof**: the original 79
rows remain an exact shared set, baseline-only is `{}`, and these 23 store IDs
are current-only because `typed_pointer_load` no longer removes them:

`SCUS_942_88:0x8004AEE4:s1`, `SCUS_942_88:0x8004AEF8:s1`,
`SCUS_942_88:0x8004AF7C:s1`, `SCUS_942_88:0x8004AF8C:s1`,
`SCUS_942_88:0x8004B208:s1`, `SCUS_942_88:0x8004B214:s1`,
`SCUS_942_88:0x8004B220:s1`, `SCUS_942_88:0x8004B224:s1`,
`SCUS_942_88:0x8004B234:s1`, `SCUS_942_88:0x8004B238:s1`,
`SCUS_942_88:0x8004B254:s1`, `SCUS_942_88:0x8004B260:s1`,
`SCUS_942_88:0x8004B274:s1`, `SCUS_942_88:0x8004B2D0:s1`,
`SCUS_942_88:0x8004B2D8:s1`, `SCUS_942_88:0x8004B2E0:s1`,
`SCUS_942_88:0x8004B464:s1`, `SCUS_942_88:0x8004B570:s1`,
`SCUS_942_88:0x8004B5D8:s1`, `SCUS_942_88:0x8004B638:s1`,
`SCUS_942_88:0x8004B650:s1`, `SCUS_942_88:0x8004B664:s1`, and
`SCUS_942_88:0x8004B678:s1`.

All 23 have the exact mixed definition set `{global_load 0x80090748,
table_load 0x80090748}` and therefore land at
`blocked_writer_universe_exhaustiveness`, not a generic no-method bucket.
Among the 79 shared IDs, exactly the same seven dispatch-driven outcomes move
against the hash-pinned `1bba2487` baseline:

| before | after | exact row ids |
|---|---|---|
| `blocked_no_direct_caller` | `blocked_writer_universe_exhaustiveness` | `SCUS_942_88:0x800590E4:s2`, `SCUS_942_88:0x80059150:s2` |
| `blocked_no_direct_caller` | `blocked_index_sign_needs_convention` | `SCUS_942_88:0x8005C5B4:s2`, `SCUS_942_88:0x8005C5C0:s2`, `SCUS_942_88:0x8005C5C8:s2`, `SCUS_942_88:0x8005C5D4:s2`, `SCUS_942_88:0x8005C5E8:s2` |

New tally: writer-universe **50**; index-sign 20; no-recovery 10;
return-domain 9; return-index-convention 6; stack-entry 5;
external-interior-entry 1; nonpositive-progression 1. The old
`blocked_no_direct_caller` bucket falls 7→0, but every row merely reaches its
next named wall. `bounded_exhausted_locally_computed_base_recovery` remains
staged and unbanked.

### Downstream identity propagation: second Hard-Truth rejection and repair

The next detached verifier rejected `fc632f8b2d16` before considering the work
done: the newly generated static index and census were correct, but their hashes
had not been propagated through the retained F01 extractor chain. In exact
terms, the seed still pinned census `2d72443b…` instead of `83f581ad…`, and the
generated query still attested index `f086cecf…` instead of `a615a5d7…`.
`phase4_frontier_extractor.py` therefore failed closed rather than regenerating.

The repair deliberately re-pins only those two live dependencies, then
regenerates the extractor summary/query/blocker ledger and semantic result.
Exact-set and byte comparisons show no semantic F01 movement: functions remain
764, window accesses remain 124/124 emitted, unresolved accesses remain 20,431,
and `analysis/phase4_f01_frontier_blockers.json` is byte-identical at
`b5d5cdc6…`. Only provenance hashes move in the other three generated outputs.
The extent audit is also regenerated against the current tracked `tools/` and
`config/` corpus: 1,056 files, 2,149 declarations, 18 reviewed truncations,
**0 new**; its only classification movement is five additional unnamed
candidate pairs. The full downstream F01 suite is now **177 passed**, not merely
the earlier 98-test slice.

The immutable capsule receipt intentionally retains census `2d72443b…`: that is
the census identity at the time the capsule query was performed, not the live
extractor dependency. It is preserved exactly as required and must not be
"updated" into a false historical receipt.

### Commands and pinned artifacts

```bash
python3 tools/phase4_f01_static_hard_truth.py --output analysis/phase4_f01_static_hard_truth.json
python3 tools/phase4_static_frontier.py --refresh
python3 tools/phase4_frontier_static_census.py --output analysis/phase4_frontier_static_census.json
python3 tools/phase4_frontier_extractor.py config/phase4_f01_frontier_seed.yaml \
  --output config/phase4_f01_frontier_query.yaml \
  --summary analysis/phase4_f01_frontier_extraction.json \
  --blockers analysis/phase4_f01_frontier_blockers.json
python3 tools/phase4_semantic_frontier.py config/phase4_f01_frontier_query.yaml \
  --output analysis/phase4_f01_frontier_result.json
python3 tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
  --output analysis/phase4_f01_typed_state.json \
  --survey analysis/phase4_f01_abi_survey.json
python3 tools/phase4_f01_local_base_recovery.py --output analysis/phase4_f01_local_base_recovery.json
python3 tools/phase4_f01_local_base_recovery.py \
  --baseline-output analysis/phase4_f01_local_base_recovery_1bba2487_outcomes.json \
  --check
python3 tools/phase4_extent_audit.py --json analysis/phase4_extent_audit.json
```

| artifact | SHA-256 |
|---|---|
| C hard-truth source | `c1b75002d3083c9b188fb9e46093b1e4553443201b6b87466d15550180f22c8d` |
| hard-truth wrapper | `21bbba16d98ab27fdb67bae97645f9afeff5b2b2b223742a8a4ec61c582f3c6a` |
| hard-truth receipt | `2d86dcc2c23a81c9ba39e43f040b2866c94d30d4bc43c308f31da8d1184adf58` |
| static frontier index | `a615a5d78d2729fe039bd4791901900604137b03d00c5cfd1c6f0db31a41dc99` |
| gap census | `83f581ad89306708e65f75167e4b9e1050a2b7d1a5d62552ca4827ae7cdfab4c` |
| F01 frontier seed | `54542acb59f20e67c8e7f704c00137af463b6a1892185801be5ad77fcbc92744` |
| generated F01 query | `beceed71b591d55962a2521de034492f6e88ca6f1e27f9e355f2f736fb3d9573` |
| extractor summary | `0d1a10a831ab0fa85652346dd28f5bbe636efeee8941e961de3c55b27019e390` |
| blocker ledger (unchanged) | `b5d5cdc6eedcb0f081a407f9d35aa5376156de5978281fbeb461af6cb006962e` |
| semantic frontier result | `6b256a7b39477043dd5e82f389fb036dbd81339275a11e9ae1737a4a3d48c13d` |
| extent audit | `de1b19388c536ca1195f570ca1796b2341d254a314d5f3fde3a8f8b875ea616b` |
| corrected writer C source | `820ae3673fe91cb6195e364043c381ad7d14ec954c45340a311bdebfa0c95106` |
| ratcheted typed-state compiler | `c7cb77535b4947a35b15717be7daf2af9d4421076b9d8a6ec27764271f2823f7` |
| typed-state schema | `8c615101c8aa2b727c25122f915e1c1a2775f1b2dc6051a37c0cbdb90c85425f` |
| typed-state artifact | `c7f89f81475b8e0703f2c666d8572fdd00da793bbcf6fe971777bc606139e808` |
| ABI survey | `8476f6b230ec64c8ff0e61874177f45c44d5c1b3a0ce5576f069137350aef82f` |
| `1bba2487` campaign outcome baseline | `8212d0e635d4ebcf8f960cb54fccc331d363a2877f8ec52d2524a803a3534be6` |
| campaign tool, including pinned-baseline rebuild mode | `cfa937b9cf4e45f5bd9783011f1f207d8c966c133bd17771d43519340c17b997` |
| regenerated campaign | `ba4e6093e8d3513aee2d494d219a12a99b140e53bdb8feaade6288b7c6e945d8` |
| Phase-4 inventory declaration | `178a3db4a2479357802c2187f27f82a2eb50c7ac73e95129820eae71f192d4b6` |
| bounded evidence-DAG receipt after exact inventory-input re-pin | `27fb038cb57cdfe79569722530a08c7b5f6e150871cf622060ee08d3a805307a` |

### Status after this work

Unchanged: F01 `partial`; item 2 `not_met`; review blockers exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`; both review booleans
false. `analysis/mechanics_baseline.yaml`, the registry, the static-ASM gate
receipt, capsule receipt, and live-replay receipt are untouched. No result in
this section banks or promotes F01. The fixture is 0 proof / 45 convention /
96 unresolved + 97 absent; the campaign is 102/102 processed and remains
staged, with zero proof decisions.

## 2026-08-07 — exact-set Hard-Truth ratchet: evidence surfaces declared

The stricter verifier withdrew the earlier acceptance of candidate
`a1350eee66284b6cfddc9bcf8d5fbca068279546`. Matching the broad test's failing
test ID was aggregate equality, not identity: a live inventory recomputation
had candidate-only members. The comparison universe is complete for each
detached commit's direct filesystem children matching exactly
`tools/phase4_*.py`, `analysis/phase4_*.json`, and
`tests/test_phase4_*.py`; nested paths and other spellings are outside those
three explicitly named universes. The prerequisite-to-candidate sets were:

| complete discovery universe | prerequisite | rejected candidate | prerequisite-only | candidate-only |
|---|---:|---:|---|---|
| generator paths | 224 | 225 | `{}` | `{tools/phase4_f01_static_hard_truth.py}` |
| artifact paths | 418 | 420 | `{}` | `{analysis/phase4_f01_static_hard_truth.json, analysis/phase4_f01_local_base_recovery_1bba2487_outcomes.json}` |
| test paths | 208 | 209 | `{}` | `{tests/test_phase4_f01_static_hard_truth.py}` |

Those are discovery-universe totals, not claims that the inherited declaration
registry is complete. The corresponding inherited undeclared/orphan residuals
were 79 generators, 297 artifacts, and 81 tests at `1bba2487`; the rejected
candidate increased them to 80, 299, and 82. Runtime evidence played no role.

The repair registers the hard-truth driver and receipt, the local-base driver
and its two retained artifacts, and both focused tests in
`config/phase4_inventory.yaml`. This is the inventory declaration surface, not
the protected campaign registry `config/phase4_campaigns.yaml`; the latter and
`analysis/phase4_gate.json` remain byte-identical to the prerequisite. A live
recomparison after the repair has no candidate-only member in any of the three
gap sets. In the reverse direction it deliberately removes exactly one
inherited omission per set:

| gap set | prerequisite | repaired candidate | prerequisite-only | candidate-only |
|---|---:|---:|---|---|
| `missing_generator_declarations` | 79 | 78 | `{tools/phase4_f01_local_base_recovery.py}` | `{}` |
| `orphan_artifacts` | 297 | 296 | `{analysis/phase4_f01_local_base_recovery.json}` | `{}` |
| `missing_test_declarations` | 81 | 80 | `{tests/test_phase4_f01_local_base_recovery.py}` | `{}` |

These residuals remain explicitly nonzero and are not relabelled as closure.
The retained broad campaign-inventory JSON predates this repository-wide debt
and is not cited as current evidence; every total above comes from a fresh
detached live recomputation and exact two-direction set subtraction.

The 79-row comparison snapshot now has a real rebuild/check path instead of a
nominal output label. `--baseline-output` reads the exact Git object
`1bba2487b1b6f3e9d7669947de494ba649b99b70:analysis/phase4_f01_local_base_recovery.json`,
pins its SHA-256
`0040c6c41a5189fdff6f04ecee2a6c61a5c7da10075a734cc28fb82ee9dfde47`,
reconstructs duplicate occurrence IDs, sorts the complete 79-row ID universe,
and reproduces the retained snapshot byte-for-byte at
`8212d0e635d4ebcf8f960cb54fccc331d363a2877f8ec52d2524a803a3534be6`.
The snapshot is historical static evidence, not a runtime sample.

This declaration repair changes no trig, dispatch, census, writer, typed-state,
campaign-outcome, or falsifier fact. F01 remains `partial`; item 2 remains
`not_met`; both review booleans remain false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`.

### Exact downstream DAG re-pin after the next rejection

The next verifier correctly rejected the declaration-only candidate
`1ce2700390c0e8e65e804d9ca69184d70e2cc925`: the bounded retained evidence DAG's
`phase4_gate` node uses exact-mode input identities and still named the old
inventory declaration. The bounded DAG universe is the six nodes and their
declared input/output rows in `config/phase4_evidence_dag.yaml`; its own claim
`complete_phase4_graph` remains false, so it is not a whole-repository total.
Within the `phase4_gate` node's complete declared-input row set, exact
two-direction comparison found one task-caused identity movement and no path
movement:

- prerequisite-only identity:
  `config/phase4_inventory.yaml@8c5409d2b9e83abb0dbc30b46e3c49c69e04803dd5ae86c99f0a49a0ee6e4639`;
- final candidate-only identity:
  `config/phase4_inventory.yaml@178a3db4a2479357802c2187f27f82a2eb50c7ac73e95129820eae71f192d4b6`;
- input paths gained `{}`, input paths lost `{}`, output identities changed
  `{}`.

The retained row now records the new exact/semantic SHA and 41,604-byte size,
and the node fingerprint is recomputed from the complete declared fingerprint
material as
`41802f078bcb300261813d3c6e07ea690df3be8672f0e2c3eb248021435566e7`.
A focused test independently reconstructs both the path identity and the
fingerprint and byte-compares `analysis/phase4_gate.json` with the prerequisite
Git object. No other retained DAG input is silently refreshed: the DAG already
contains inherited stale identities outside this task, so a whole-file
`--write` would fold unrelated repository debt and external movie-tree state
into this correction. Those inherited differences remain named debt; the DAG
is not claimed globally fresh. The protected campaign registry and gate receipt
remain byte-identical.

The verifier also rejected the first declaration spelling before accepting it
as a candidate: `phase4_f01_local_base_recovery.py` was labelled `static`, but
its primary campaign mode instantiates the C-backed typed-state verifier and
reads pristine resident/overlay image bytes. Only its historical-snapshot mode
is Git-object-only. The generator is therefore classified `local_media`, the
same as the hard-truth driver; a focused test pins both classifications. This
five-byte declaration change is included in the final identity and DAG
fingerprint above rather than hidden behind the baseline-only submode.

## 2026-08-07 — Hard-Truth acceptance recorded

The Hard-Truth check (Codex) ACCEPTED the increment at commit
`822385e95b14e0d66e0704e348503e3a4ce50e69` — covering the content-verified
trig disposition (unevidenced 24,242 → 11,958 B), the fail-closed demotion of
both table-backed bindings (fixture decided 68 → 45, proof 23 → 0), the
six-writer census with stated residual, the falsification of the live
receipt's jalr attribution, and the campaign expansion to 102 exact-tracked
rows. Independently re-verified in-session: 180/180 focused tests, all five
pipelines fresh, registry untouched, F01 verdicts unchanged.

Post-acceptance addendum: `9f69f5e6f7c1` (after the accepted commit) adds the
dated retraction block INSIDE `analysis/phase4_f01_live_gap_read_receipt.json`
so the falsified finding never travels without its correction — 8 lines,
annotation only, no analytical content changed. It rides into the next review.

## 2026-08-07 — instruction-derived unsigned intervals (fail-closed repair)

### Correctness finding first: the first candidate was not bankable

The fresh detached Hard-Truth verifier rejected candidate
`92e249a8807b2916f6a3f2e22bc9b32958991485`. Its reported 192 typed-state
promotions and 32 non-F01 decisions are **retracted**. The C CFG accepted an
aliased `sltiu` guard, missed a nonlinear jump-delay load producer and several
exception/conditional-transfer classes, and its consumers treated unknown
indirect target domains and PS1 RAM aliases as exclusions. Those are proof
boundary errors, not documentation defects, so no result from that candidate is
banked.

Hard-Truth round 2 likewise rejected candidate
`05abdda39be31b9a59eaa8ca1eafce80a872dc21` before banking. Two synthetic
instruction programs showed that lexical adjacency was still being confused
with dynamic control flow: a jump could enter a branch after skipping its
lexically preceding `sltiu`, and a word reached both as a transfer delay slot
and as an ordinary branch target lost its ordinary fallthrough in the
context-free CFG. Both false proofs are retracted. The repair requires the
`sltiu` to be the sole dynamic predecessor of its branch and rejects every
dual-context delay-slot word rather than guessing an execution context.

Hard-Truth round 3 did not bank candidate
`05bc6b8a251b613cf6c25b6c6bdf351fdf32b7e4`. Its detached technical audit
encoded a function that assigned `ra` the exact query PC, took a `jr ra` path
that bypassed the only `andi`, and was falsely reported as `[0,63]`; the
external verifier process ended before emitting a final verdict, so no verdict
is attributed to it here. The counterexample itself is decisive. Treating every
`jr ra` as an unqualified terminal return was too strong. The repair keeps an
untouched entry `ra` as the declared function-return boundary but rejects a
reachable `jr ra` whenever any dynamic predecessor path contains a local `ra`
definition; it neither blesses a stack restore nor recovers a wanted target
from convention. The public query and the embedded self-test both retain the
exact `0x03E00008` breaker and
`locally_defined_ra_indirect_target_not_modelled` reason.

The repaired `indexdom@IMAGE:START:END:REG:PC` remains row-agnostic: image,
extent, register, query PC, table base, displacement, width, and watched windows
are consumer inputs. The C engine proves only `lbu/lhu`, `andi`, `srl`, a real
`sltiu` true edge, non-negative constants, and overflow-checked
`sll`/`addu`/non-negative-`addiu` compositions. Every dynamic reaching
definition must pass. It rejects aliased guards, delayed load/COP producers,
signed loads/addition, negative immediates, unknown definitions, entry bypasses,
cycles, calls, unresolved indirect transfers, `syscall`, `break`, unsupported
COP branches, conditional-link REGIMM branches, and nested transfers in delay
slots.

At this repair stage, the `-Werror` C self-test had **25 controls** (superseded
by round 6's 27): three pre-existing definition controls and twenty-two interval
controls, including the required masked positive,
signed-load negative, `addu` overflow negative, and path-bypass negative, plus
the round-2 CFG counterexamples and the round-3 local-`ra` re-entry
counterexample. The shared consumer closure names
all **247** static-index indirect-transfer sites: 107 jumps (87 complete, 20
unknown) and 140 calls (all unknown), for 160 exact unknown-domain site IDs.

### F01 campaign: zero decisions, 26 exact instruction walls

Against the exact 102-row prerequisite artifact at `b6cb61d35f9d`, the row
universe has baseline-only/current-only `{}/{}`. The 20 former
`blocked_index_sign_needs_convention` and six former
`blocked_return_domain_needs_index_convention` IDs move to
`blocked_index_interval_unproved_instruction`; no row moves in the reverse
direction and `decided_by_proof` is **0**. Grouped exhaustively by first breaker:

| breaker PC / word / reason | exact row IDs |
|---|---|
| `0x8005A0D8` / `0x03E00008` / locally defined `ra` indirect target not modelled | `LEVEL01_LEVEL1:0x800B401C:v0`, `LEVEL01_LEVEL1:0x800B4068:v0`, `LEVEL03_LEVEL1:0x800B3D88:v0`, `LEVEL03_LEVEL1:0x800B3DD8:v0`, `LEVEL03_LEVEL1:0x800B408C:v0`, `LEVEL03_LEVEL1:0x800B4140:v0` |
| `0x800B4858` / `0x03E00008` / locally defined `ra` indirect target not modelled | `LEVEL02_LEVEL:0x800B47C4:at`, `LEVEL02_LEVEL:0x800B47C8:v0:occurrence-1`, `LEVEL02_LEVEL:0x800B47C8:v0:occurrence-2`, `LEVEL02_LEVEL:0x800B47D4:v1` |
| `0x800B4284` / `0x0007000D` / `break` exception transfer | `LEVEL04_LEVEL1:0x800B4AA8:v1` |
| `0x800B8784` / `0x03E00008` / locally defined `ra` indirect target not modelled | `MEMORY:0x800B7EA4:at`, `MEMORY:0x800B7F04:at`, `MEMORY:0x800B7F64:at` |
| `0x800498A4` / `0x03E00008` / locally defined `ra` indirect target not modelled | `SCUS_942_88:0x80048368:v0`, `SCUS_942_88:0x8004836C:v0`, `SCUS_942_88:0x80048370:v0`, `SCUS_942_88:0x80048378:v0` |
| `0x8004B6D4` / `0x03E00008` / locally defined `ra` indirect target not modelled | `SCUS_942_88:0x8004B2A8:a0`, `SCUS_942_88:0x8004B318:a0`, `SCUS_942_88:0x8004B4F4:a0` |
| `0x8005C108` / `0x00400008` / unresolved indirect jump | `SCUS_942_88:0x8005C5B4:s2`, `SCUS_942_88:0x8005C5C0:s2`, `SCUS_942_88:0x8005C5C8:s2`, `SCUS_942_88:0x8005C5D4:s2`, `SCUS_942_88:0x8005C5E8:s2` |

Every row retains its complete attempt and breaker. The full 102-row outcome
partition is 50 writer-universe, 26 index-interval-instruction, 10 no-recovery,
9 return-domain, 5 stack-entry, 1 external-entry, and 1 nonpositive-progression.
Outcomes and the universe do not move from `05bc6b8a251b`, but the exact breaker
arrays do: the 20 row IDs in the five local-`ra` table groups above changed from
their prior later breaker. `breaker_movement_from_05bc6b8a251b` embeds both
ordered arrays for every changed ID and empty baseline-only/current-only sets.

### Typed state: no promotion survives all proof gates

The compiler examines all **2,769** convention rows. Of those, **1,598** have an
exact table-address candidate and produce 1,211 unique C queries. The exhaustive
outcome partition is 1,568 `interval_unproved`, 3
`proved_interval_does_not_exclude_every_window`, and 27
`external_interior_entry`; upgraded count is **0**. Against `05bc6b8a251b`, the
local-`ra` repair moves exactly 133 former external-entry diagnostics and 33
former alias diagnostics into `interval_unproved`, with no reverse movement.
The exact gained/lost row-ID sets, all residual IDs, and their derivations are
retained in `analysis/phase4_f01_typed_state.json`.

Therefore movement against `b6cb61d35f9d` is exactly empty in both directions
for every category and for both ledger and fixture universes. Ledger totals stay
**20,431 = 219 proof / 2,769 convention / 17,443 unresolved** (stores 95 / 973 /
7,206). The fixture stays **238 = 0 proof / 45 convention / 96 unresolved + 97
absent**. In particular,
`fixture:SCUS:0x800511e4:ambient_sfx_sequence_update` remains convention: its
C query now fails at `0x8005128C`, word `0x03E00008`, because a predecessor path
locally defines `ra` and the indirect target is not modelled. The lexical
`andi`/`sll` chain still describes one direct path, but no machine interval is
claimed; the incomplete indirect-entry universe remains an additional global
closure issue.

Both table-backed bindings remain rejected. No writer census, value-domain
gate, registry, or campaign authority moves.

### Measured reuse on a second window: zero final decisions

The standalone non-promoting receipt
`analysis/phase4_index_interval_non_f01_demo.json` sweeps resident window
`[0x800A657E,0x800A6580)`. Its named source universe is all **11,352** resident
static-index STORE rows; C rejects 78 stale base/access claims, leaving **739**
exact table-address-class sites. Their exhaustive final partition is **0**
decided, 725 interval-unproved, 6 proved intervals that still overlap a PS1
RAM alias of the window, and 8 address-excluded sites blocked by external-entry
closure. The latter 8 are retained separately as a pre-entry-gate diagnostic,
never proof. The convention decides 72 on the same universe, so the exact
comparison is 0 both / 0 interval-only / 72 convention-only. This measures
current reusable capability and changes no row, artifact authority, registry,
or gate. Against `05bc6b8a251b`, exactly 13 external-entry and 22 alias rows
move into `interval_unproved`, with no reverse movement; the receipt embeds the
complete row-ID sets.

### Hard-Truth round 4: independent overlay regions must coexist

Candidate `53e9c6c0d5ed680483989b6245617ef201c977aa` was not banked. The
detached ratchet returned `unverified` while checking a real structural gap:
the external-entry consumer treated every pair of distinct nonresident images
as mutually exclusive. That was valid for two Region-A blobs sharing the
`0x800B39A0` swap span, but false for Region A and `MEMORY.BIN` in the disjoint
Region-B span at `0x800B5788`.

The repair is row-agnostic and fail-closed. `_images_can_coexist` now derives
the answer from each identity-verified image's `[file_va_base,
file_va_base+size)` span. Distinct overlapping spans are proved exclusive;
disjoint spans can coexist. A missing, duplicate, unverified, malformed, or
out-of-range image declaration is treated as possible coexistence, never as an
exclusion. A focused control pins all four directions: two Region-A images do
not coexist, Region A and Region B do, resident and Region B do, and an unknown
image fails closed to possible coexistence.

The complete newly admitted cross-region transfer set is:

- from `MEMORY`: indirect call `0x800BD82C` and indirect jumps
  `{0x800B970C, 0x800BB8BC, 0x800BD6AC, 0x800BD6BC, 0x800BD6CC,
  0x800BD714, 0x800BD724, 0x800BD7EC, 0x800BD7FC, 0x800BD80C}`;
- from Region A into `MEMORY`: indirect jump
  `LEVEL07_LEVEL1:0x800B3FCC`.

Campaign outcomes do not move. The five Region-A rows
`{LEVEL02_LEVEL:0x800B47C4:at,
LEVEL02_LEVEL:0x800B47C8:v0:occurrence-1,
LEVEL02_LEVEL:0x800B47C8:v0:occurrence-2,
LEVEL02_LEVEL:0x800B47D4:v1,
LEVEL04_LEVEL1:0x800B4AA8:v1}` each gain the 11 `MEMORY` blockers; their entry
counts move `174→185` for the four LEVEL02 rows and `162→173` for the LEVEL04
row. The three rows
`{MEMORY:0x800B7EA4:at, MEMORY:0x800B7F04:at,
MEMORY:0x800B7F64:at}` each gain `LEVEL07_LEVEL1:0x800B3FCC` and move
`159→160`. All eight remain
`blocked_index_interval_unproved_instruction`; their C breaker still decides
the local result before entry closure could promote anything.

In the typed-state exact-table universe, the six IDs at PCs
`{0x800B3A54,0x800B3AA4,0x800B3AB0}` in each of
`{LEVEL08_LEVEL1,LEVEL09_LEVEL}` move from 159 to 170 external entries. They
remain `external_interior_entry`; the 1,598-site partition stays exactly
1,568 interval-unproved / 3 alias-overlap / 27 external-entry / 0 upgraded.
Ledger and fixture movements against `b6cb61d35f9d` remain empty in both
directions. The non-F01 receipt targets resident code, which already coexisted
with every overlay under the old predicate, so its bytes and 739-site partition
are unchanged.

The controlled inventory re-pin changes exactly three retained identities: the
typed-state generator source, the typed-state artifact, and the local-base
campaign artifact. Its exact SHA-256 is
`03695c52b6abb24fded6a52e0db0ed21978f5b3151368ad1a1b4b755f4f491ea`.
The bounded DAG updates that exact input in precisely its three declared
consumers `{offline_queue, closure_debt, phase4_gate}` and recomputes only those
three fingerprints; no downstream output is regenerated and the inherited
307-file movie-tree identity is preserved. The DAG SHA-256 is
`85c507498ee2c9f8eb6d2ebfe28a03eec7aa64cf76a9b9900ec53afe4565c6db`.
The focused round-4 result is **72 passed**. This is still a pre-acceptance record;
only a later detached `agreed` verdict may bank it.

### Commands

```bash
gcc -O2 -std=c11 -Wall -Wextra -Werror -o /tmp/phase4-prov \
  tools/phase4_typed_state_provenance.c
/tmp/phase4-prov --self-test
python3 tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
  --output analysis/phase4_f01_typed_state.json \
  --survey analysis/phase4_f01_abi_survey.json
python3 tools/phase4_f01_local_base_recovery.py \
  --output analysis/phase4_f01_local_base_recovery.json
python3 tools/phase4_index_interval_demo.py \
  --output analysis/phase4_index_interval_non_f01_demo.json
python3 -m pytest -q tests/test_phase4_typed_state.py \
  tests/test_phase4_f01_local_base_recovery.py \
  tests/test_phase4_index_interval_demo.py \
  tests/test_phase4_f01_static_hard_truth.py
```

The focused round-4 repair result before detached review is **72 passed**. Final hashes
and the detached decision belong in a later acceptance block; this repair
section does not bank itself.

### Status held deliberately unchanged

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The protected mechanics
baseline, registry, gate receipt, writer-universe gate, value-domain gate,
static hard-truth receipt, and retraction blocks are untouched. No runtime work
was needed.

## 2026-08-07 Hard-Truth round 5: malformed image spans fail closed

The detached audit of candidate
`37f8b5c397b0c08060631623ee3b08f96b85f8f7` returned `unverified`. Its
independent span controls found a real Python type-coercion hole in the new
row-agnostic coexistence predicate: `bool` is an `int`, while `int(1.5)`
silently truncates. A boolean base/size or fractional size could therefore make
two malformed overlapping declarations look proved-exclusive, contrary to the
stated fail-closed rule.

Commit `97564cbbd9ba24f223ad41d6981a15c6878afa68` closes that hole. A load
base is admitted only from an exact `int` or string representation and a size
only from an exact non-boolean `int`; non-mapping image rows also fail closed.
Missing, duplicate, unverified, non-positive, out-of-range, boolean,
fractional, string-sized, and otherwise unparsable metadata all mean
**possible coexistence**. The control starts from two valid overlapping images
that are correctly exclusive, mutates each malformed type in turn, and requires
every mutation to become coexistent. This is intentionally under-claiming.

All real indexed image metadata already has string `file_va_base`, integer
`size`, and literal-boolean `identity_verified`, so the typed-state, local-base,
ABI-survey, and non-F01 receipts regenerate byte-identically. Their hashes stay:

- typed state:
  `96f4a6e69bc841b2ba2f26f1b480e8fab8e54aa071d00eabda4d3f2688604ae8`;
- 102-row campaign:
  `d667b82fe3a094c69192d25fba32383cfb71bdfbe51331aff98d66fbc2997693`;
- non-F01 receipt:
  `ed9a927d45e1bc8934a2e2ce9f1ed965d9b5f2b4fb74e0733dd38d38bd66f3f0`.

Commit `7659d0d61ed4` re-pins the clean inventory and bounded DAG. The inventory
is `75af7574916190eaaf3f129b20d5c7dc6fa2e67ce53d52f5b71553b7e166136a`;
fixture and knowledge receipts remain byte-identical. The DAG changes only the
campaign-inventory row and recomputed fingerprints in its exact consumers
`{offline_queue, closure_debt, phase4_gate}`; its hash is
`00f0e0ba68cb62ce7ac7a7a57cc358362e0ccf32f8ba2085e96aba6e569acb08`.
No downstream output was regenerated, and the inherited 307-file movie-tree
identity was preserved. The focused round-5 suite remains **72 passed**
(superseded by round 6's 82-test suite).

This repair moves no campaign outcome, typed-state bucket, fixture bucket, or
demonstration site. F01 therefore remains `partial`; item 2 remains `not_met`;
both review booleans remain false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. This is still
pre-acceptance: it does not bank itself.

## 2026-08-07 Hard-Truth round 6: truncated CFGs and empty domains reject

Detached candidate `2eb2f8332b1217416cff25a229530162d95c69c1` returned
`unverified`, with banking explicitly unauthorized. Its independent public
queries found two false-closure mechanisms and one conservative-API defect:

1. `indexdom@J_EDGE:0x80010000:0x80010010:t0:0x80010004` ended its
   declared extent on `j 0x80010004` (`0x08004001`). The image contained the
   delay-slot NOP immediately afterward, but the truncated extent did not. The
   old CFG erased the jump's successor and falsely reported `[0,63]`, hiding a
   signed `lh` re-entry definition. A final conditional branch
   (`0x1000FFFD`) produced the same false proof.
2. Injecting an explicit empty target list at the real
   `LEVEL07_LEVEL1:0x800B3FCC` indirect jump marked its domain complete and
   removed its unknown-domain blocker from the `MEMORY` catalog (`160→159`).
3. A non-mapping top-level index, or boolean/integer/fractional `images`
   catalog, raised instead of returning possible coexistence. It did not mint a
   proof, but contradicted the stated fail-closed interface.

Commit `98c166cb83c7` repairs all three without widening the instruction
whitelist. Every reachable transfer must have its architectural delay slot
inside the declared extent; otherwise the exact transfer is reported with
`control_transfer_delay_slot_outside_query_extent`. Both the direct-jump and
conditional-branch counterexamples are retained through the public query and
the embedded C self-test. The strict `-Werror` self-test is now **27 controls**:
three original definition controls plus 24 unsigned-interval controls.

Indirect-target completeness now requires a nonempty, validated,
duplicate-free exact address list tied to the decoded site. Empty, null,
boolean, numeric, string, invalid-address, and duplicate-target mutations all
leave `target_domain_complete=false`; the real `0x800B3FCC` blocker remains in
the 160-entry `MEMORY` catalog. Malformed top-level index/catalog shapes return
possible coexistence. These are under-claiming repairs: malformed evidence can
only retain a blocker.

### Exact result movement

Regeneration changes **no semantic site result** relative to rejected candidate
`2eb2f8332b12`:

- campaign universe 102; outcome gained/lost sets `{}/{}` and breaker-change
  set `{}`; partition remains 50 writer-universe / 26 interval-instruction /
  10 no-recovery / 9 return-domain / 5 stack / 1 external-entry /
  1 progression; decided set `{}`;
- typed exact-table universe 1,598; outcome gained/lost sets `{}/{}` and
  breaker-change set `{}`; partition remains 1,568 interval-unproved / 3 RAM
  alias / 27 external-entry / 0 upgraded;
- ledger and fixture movements against prerequisite `b6cb61d35f9d` remain
  empty in both directions for every category: 20,431 = 219 proof / 2,769
  convention / 17,443 unresolved, and 238 = 0 proof / 45 convention / 96
  unresolved + 97 absent;
- the non-promoting `[0x800A657E,0x800A6580)` receipt remains 11,352 resident
  STORE rows and 739 table sites = 725 interval-unproved / 6 alias / 8
  entry-unclosed / 0 decided; the convention-only exact set still has 72 IDs.

Against the pinned prerequisite, the 20 index-sign and six return-index row IDs
remain exactly the artifact's gained
`blocked_index_interval_unproved_instruction` set and lost convention-wall
sets; no reverse movement occurs. Each retains a full attempt and exact
breaking instruction. Zero is the measured answer, not grounds to weaken the
prover. No table index became proof, so no Canon table-index claim was added.

### Rebuilt artifacts and bounded inventory

The regenerated identities are:

- C verifier source:
  `624800ad70330d2b7bcd0c4a8edf2ef7aacfd014231007233558225cad9ece00`;
- typed-state generator:
  `f6fb817fe0c59206125019b7c5be1bef23ae19d8fa8b0f9d2341d8108d6bbfd1`;
- typed state:
  `8fb3ff32515c0cf63c9dfe2f948a06f9a9c0958ccde52279765a507e373fbe7a`;
- 102-row campaign:
  `617a851596a13c51e776e0e6f624c2a67d6c033181fab99e2b5f0b80eff94abc`;
- non-F01 receipt:
  `50abff1e91ccfd281c1d1b66e79b0d0fdf20405fa392c2e2e3676e06e42e0fd4`;
- ABI survey remains byte-identical:
  `8476f6b230ec64c8ff0e61874177f45c44d5c1b3a0ce5576f069137350aef82f`.

Commit `92f83baa81ac` carries the clean detached inventory/DAG re-pin. The
campaign inventory is
`e818ba6655cc86f873c8a8059a31c402d48f52787bcc3367bc46d5af40ffaab6`;
fixture and knowledge receipts remain byte-identical at `3beb3375…` and
`47da5515…`. The bounded DAG is
`aa3f4741106ac3abaef37150447da7a959784942b121d8ad73df1472a95eb5d9`.
Only the campaign-inventory identity changes in its exact consumers
`{offline_queue, closure_debt, phase4_gate}`, whose fingerprints become
`{0721a569…, 7fcb336e…, 401390c6…}`. No downstream output is regenerated; the
inherited 307-file movie-tree identity is preserved. A clean detached rebuild
verified all 327 pristine staged inputs before generating the inventory.

The focused command is now **82 passed**:

```bash
gcc -O2 -std=c11 -Wall -Wextra -Werror \
  -o <scratch>/phase4-prov tools/phase4_typed_state_provenance.c
<scratch>/phase4-prov --self-test
python3 tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
  --output analysis/phase4_f01_typed_state.json \
  --survey analysis/phase4_f01_abi_survey.json
python3 tools/phase4_f01_local_base_recovery.py \
  --output analysis/phase4_f01_local_base_recovery.json
python3 tools/phase4_index_interval_demo.py \
  --output analysis/phase4_index_interval_non_f01_demo.json
python3 -m pytest -q tests/test_phase4_typed_state.py \
  tests/test_phase4_f01_local_base_recovery.py \
  tests/test_phase4_index_interval_demo.py \
  tests/test_phase4_f01_static_hard_truth.py
```

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The mechanics baseline,
registry, gate receipt, writer-universe gate, value-domain gate, static
hard-truth receipt, and receipt retraction blocks remain untouched. This round
is a pre-acceptance repair record and does not bank itself; only a later fresh
detached `agreed` verdict may authorize the acceptance block.

## 2026-08-07 Hard-Truth round 7: conflicting target sources remain unknown

Fresh detached verifier candidate `aac3a336719ce4fd1f104e1b51acb604cc964a12`
returned `decision: unverified`, `banking_authorized: false`. Its terminal
verdict is retained externally at
`~/.cache/phase4-indexdom-hard-truth-r8.verdict.json`, SHA-256
`9b829788bdb4f1952123f993e3e637e060a8d2ef8d2848a84afc461441decfd6`;
the audit log is SHA-256
`ed4ed5c42fdc6501b220d92c30c5d50fccd5d6c278eb9896977709321193186e`.

The verifier independently reproduced every retained result and found one
contract failure. At the real decoded overlay jump
`LEVEL07_LEVEL1:0x800B3FCC`, two individually valid target maps with different
lists caused `_indirect_transfer_closure` to raise `TypedStateError`. A conflict
must instead set `target_domain_complete=false`, clear any accepted target
list, preserve the unknown-domain blocker, and let the audit continue.

Commit `29ef16ee2afa` repairs that path without changing the C whitelist. The
merge is fail-closed and sticky: once a site has an empty, malformed,
duplicate-PC, unverified, or conflicting source, a later valid source cannot
restore completeness. It also binds the two PC-only maps to the unique resident
image from which their source artifacts were verified. This closes the nearby
alias the mutation exposed: a resident receipt at a numerically equal PC can no
longer certify an overlay jump.

Two retained real-site controls pin both facts:

- conflicting valid maps at resident `0x8001CAC4` produce an unknown site,
  empty accepted targets, 86 complete / 21 unknown jumps in the synthetic
  closure, and a 161st `MEMORY` external-entry blocker;
- conflicting valid PC-only rows at overlay `LEVEL07_LEVEL1:0x800B3FCC`
  leave that overlay site unknown, with the existing 160-entry `MEMORY`
  catalog and its exact blocker intact.

The complete focused command from round 6 now reports **84 passed**; the C
self-test remains **27/27** under `-Werror`. Regeneration moves no semantic
site result:

- F01 campaign: 102 rows, zero decided; 50 writer-universe / 26
  interval-instruction / 10 no-recovery / 9 return-domain / 5 stack / 1
  external-entry / 1 progression;
- typed ledger: 20,431 = 219 proof / 2,769 convention / 17,443 unresolved;
  fixture 238 = 0 proof / 45 convention / 96 unresolved + 97 absent;
- exact-table candidates: 1,598 = 1,568 interval-unproved / 3 RAM-alias / 27
  external-entry / 0 upgraded;
- non-F01 `[0x800A657E,0x800A6580)`: 11,352 resident STORE rows, 739 sites =
  725 interval-unproved / 6 alias / 8 entry-unclosed / 0 decided; 72 remain
  convention-only.

Current generated identities at `343e5b072158` are:

- C source `624800ad70330d2b7bcd0c4a8edf2ef7aacfd014231007233558225cad9ece00`;
- Python consumer `2b20a52008f6d5be47bc7cdc4a53df8315a518f253ea304e932fc509ad94106a`;
- typed state `2f93b608504448e1e6755790a0d28525f1d96e58d70676585675347d9c29064a`;
- campaign `bbbdf07558925188382ca5488b8dd5b1b0f0c142fce26fff8d58aa08da659f19`;
- non-F01 receipt `cf955f5133483a67971e9be5d75aff891d059e66a7800093f9430552545553bf`;
- ABI survey unchanged at
  `8476f6b230ec64c8ff0e61874177f45c44d5c1b3a0ce5576f069137350aef82f`.

Commit `343e5b072158` is the bounded clean-detached re-pin. All 327 staged
inputs passed their hashes and were independently confirmed regular,
non-symlink files; the copied tree had zero extras. Fixture and knowledge
inventories reproduced byte-identically at `3beb3375…` and `47da5515…`.
Campaign inventory is `be3e68ccf89428fc573d1c959e41fe5e1094a10f7fc38b39fa7b99d36360c338`;
the bounded DAG is
`c44d4e2c2fcb8b401bf2a824e7316dc3458fba21d92e715125bb52895bc7a9a9`.
Only exact consumers `{offline_queue, closure_debt, phase4_gate}` move, to
fingerprints `{a3f98c60…, c61414a3…, 79dba1a9…}`. The inherited 307-file
movie-tree identity was not refreshed from the operator's changed tree.

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The mechanics baseline,
registry, gate receipt, writer-universe and value-domain gates, static
hard-truth artifact, and receipt retraction blocks remain unchanged. No table
index became proof, so there is no Canon promotion to record. This is a
pre-acceptance repair record, not a bank; a new detached hard-truth verdict is
required.

## 2026-08-07 Hard-Truth round 8: TABLE is now an independent proof

Fresh detached candidate `c1f499d2a2377461ad6d21c76c407409c49ab5fb`
returned terminal `decision: unverified`, `banking_authorized: false`. The
verdict is retained outside the repository at
`~/.cache/phase4-indexdom-hard-truth-r9.verdict.json`, SHA-256
`2e2298c2ce00259a311be0a9722920b5651a1429f2a8c59f2b1fefb3aa728ac5`;
the audit log SHA-256 is
`3f34ba6d26fadc303d23a00be1c9b4e5ce795fe57e2883dc1dd29e171927a7d8`.

The verifier reproduced every retained count and safeguard, then supplied a
full-consumer counterexample:

```text
andi t0,a1,0x3f
bne  a0,zero,join
nop
lui  t1,0x8009       # fallthrough only
join: addu t2,t1,t0
sw   v0,0(t2)
```

The index operand really is `[0,63]`, but the taken branch reaches `addu` with
arbitrary incoming `t1`. The prior base classifier walked backward lexically,
reported `TABLE=0x80090000`, and the real typed consumer promoted the store to
proof. This was a false proof, so the candidate was not banked.

Commit `d2f8132b91ad` separates the obligations. A `table_address` definition
now survives only when the old same-basic-block constant recovery and an
independent all-reaching-definition constant proof both agree on the exact
operand value. Its C result records `table_base_register` and
`table_base_proof=all_reaching_definitions_same_constant`; all three consumers
require those fields before asking `indexdom@` about the other operand. The
branch-bypass fixture remains convention-classified even though the independent
index query still reports `[0,63]`. The C failure names the forming instruction
`0x80010010`, word `0x01285021`, reason
`table_base_operand_not_path_invariant`.

Two layers retain this ratchet. The `-Werror` C self-test is now **29 controls**
(the previous 27 plus a dominating-table positive and CFG-join negative). A
public-query test checks the proof fields and exact failure, while a second test
runs `upgrade_convention_with_index_intervals` itself and requires zero upgrades
and an unchanged convention verdict. The adjacent image-lifetime check was also
tightened conservatively: an empty, whitespace, numeric, or duplicate image ID
now means possible coexistence rather than a proved exclusion. The complete
focused suite is **86 passed**.

Regeneration moves no semantic result relative to `c1f499d2a237`:

- campaign: 102 rows, zero decided, outcome changes `{}` and breaker changes
  `{}`; partition 50 writer-universe / 26 interval-instruction / 10
  no-recovery / 9 return-domain / 5 stack / 1 external-entry / 1 progression;
- typed ledger: 20,431 = 219 proof / 2,769 convention / 17,443 unresolved;
  fixture 238 = 0 proof / 45 convention / 96 unresolved + 97 absent;
- exact-table candidates: 1,598 = 1,568 interval-unproved / 3 RAM-alias / 27
  entry-unclosed / 0 upgraded;
- non-F01 `[0x800A657E,0x800A6580)`: 11,352 resident STORE rows, 739 sites =
  725 interval-unproved / 6 alias / 8 entry-unclosed / 0 decided, with 72
  convention-only.

Current generated identities at `b47240b31737` are:

- C source `9b65f1e85ad55b8e88024321ab6dc0fa106396c1969a93b57fafa529c8c313e8`;
- typed consumer `4cfe877d7b8181279d9a33d37775116931a52413e58b6a4403119609568fe749`;
- typed state `a246bf8807fa736bde413aca0f19ae980b1f45238d9cf503ca0ed8f3104a48cc`;
- campaign `38e456b494fc06075418f081319529bcf1c7183c8e6e3d33980312a3c57cc00d`;
- non-F01 receipt `a46c84b9ea6f1cdb517807058ebabfef9b0bcbfae870fb6d70ffa9e8d341c284`;
- ABI survey unchanged at
  `8476f6b230ec64c8ff0e61874177f45c44d5c1b3a0ce5576f069137350aef82f`.

Commit `b47240b31737` carries the clean-detached inventory/DAG re-pin. All 327
staged inputs passed their exact pins; the copied universe was 327 regular
files, zero symlinks, zero nonregular entries, and zero manifest differences.
Fixture and knowledge inventories reproduced byte-identically at
`3beb3375c103cdd88d13bf8ea042c29ea220567e4da7aa1b76f44ce714f52bcd` and
`47da5515a69a13abc806b9e242447626023766019f6e67a1841ffa7555a7236e`.
Campaign inventory is
`54233f40e5715cdf22108077631e9d7dc81f0950a30693858b0a42c665261915`;
bounded DAG is
`d96b2b9a8a32b092579f8dc29975ba05b03d2e1931f991e8dc8fad13aa357c12`.
Only exact consumers `{offline_queue, closure_debt, phase4_gate}` move, to
fingerprints
`{bba004e750087340d58894b7e7b5c4da6f20ac40dadf9ab45bbbeb26916198ff,
54597c6f4e277376628bdc927140f170d94a7e39f7a23a48be4d06a862329667,
2b26db9f867eb0bdadc3f2ee444d7c7a8412e47503d11f01e06d31b972ccb8be}`.
The inherited
307-file movie-tree identity remains deliberately untouched.

Focused regeneration/verification commands were:

```bash
gcc -O2 -std=c11 -Wall -Wextra -Werror -o <scratch>/phase4-prov \
  tools/phase4_typed_state_provenance.c
<scratch>/phase4-prov --self-test
python3 tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
  --output analysis/phase4_f01_typed_state.json \
  --survey analysis/phase4_f01_abi_survey.json
python3 tools/phase4_f01_local_base_recovery.py \
  --output analysis/phase4_f01_local_base_recovery.json
python3 tools/phase4_index_interval_demo.py \
  --output analysis/phase4_index_interval_non_f01_demo.json
python3 -m pytest -q tests/test_phase4_typed_state.py \
  tests/test_phase4_f01_local_base_recovery.py \
  tests/test_phase4_index_interval_demo.py \
  tests/test_phase4_f01_static_hard_truth.py
python3 tools/build_identity.py --verify
python3 tools/phase4_inventory.py  # expected OPEN; retained gaps unchanged
```

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The mechanics baseline,
registry, gate receipt, writer-universe and value-domain gates, static
hard-truth artifact, and receipt retraction blocks remain unchanged. No table
index became proof, so there is no new Canon table-index claim. This is a
pre-acceptance repair record; only a later detached `agreed` verdict may bank
it.

## 2026-08-07 Hard-Truth round 10: table and index now share the fail-closed CFG

Fresh detached candidate `3daf4fbf7637cc64ca4efbe767867c5b01903838`
returned terminal `decision: unverified`, `banking_authorized: false`. The
verdict is retained outside the repository at
`~/.cache/phase4-indexdom-hard-truth-r10.verdict.json`, SHA-256
`5e37eb4e0d88432dd1543821bdc9a31433a849e3218d3fe9717cba58026f9c99`;
the audit log SHA-256 is
`2de34ebf3094dd2e4eff538f5906a583c3e381c44e324ae019345faf391aace1`.
The verifier found three real false-closure paths:

- the entry `$gp` constant could survive a local overwrite and falsely certify
  a table base;
- an unknown indirect transfer from another image could be discarded merely
  because its numeric PC lay inside the target image's extent;
- table-constant dataflow used a weaker CFG than `indexdom@`, so a truncated
  direct transfer or unresolved `jr` could certify TABLE while the index query
  correctly failed closed.

Commits `36e0e48c8614`, `711fc4314aaf`, `dce9e9d67622`,
`18b57b4e06f8`, and `127b7d39974a` repair and retain those defects. Entry
`$gp` is now an ordinary reaching fact that a local definition kills or
replaces. Cross-image internal-transfer suppression requires equal source and
target image identities. TABLE and INDEX both call the same
`index_context_fail_closed_barrier`; the C classifier therefore rejects a
truncated jump at `0x08004004`, an unresolved `jr` at `0x01600008`, and the
real locally-defined-`ra` return shape at `0x03E00008`. Failed table
classifications propagate their exact breaker into the typed and campaign
receipts. The two rejected table-backed bindings retain the coexisting writer-
universe and value-domain evidence even when the stricter table proof supplies
an earlier blocker; acceptance is still the conjunction of every gate.

These are permanent regression controls, not accepted residual regressions.
The `-Werror` C self-test is now **33/33**: it includes entry-`gp` positive,
local-`gp` overwrite negative, truncated-jump negative, and unresolved-`jr`
negative controls in addition to the instruction-interval controls. Public and
full-consumer tests also pin the local-`gp`, same-numeric-PC cross-image, exact
breaker, and rejected-gate-evidence cases. The focused suite is **88 passed**.

### Campaign result and exact prerequisite movement

The named universe remains all **102** eligible F01 site rows, and every row is
processed. The final exhaustive partition is **0 decided by proof**, **52
`blocked_index_interval_unproved_instruction`**, **26 writer-universe**, **9
return-domain unrecovered**, **8 no-recovery**, **5 stack-entry**, **1
external-entry**, and **1 nonpositive-progression**. Every one of the 20
prerequisite index-sign rows and six prerequisite return-index rows now has a
full failed derivation and exact breaking instruction.

Against pinned prerequisite `b6cb61d35f9d`, gained
`blocked_index_interval_unproved_instruction` is exactly the union of these
four disjoint lost sets; every reverse set is empty:

- lost `blocked_index_sign_needs_convention` (20):
  `{LEVEL02_LEVEL:0x800B47C4:at,
  LEVEL02_LEVEL:0x800B47C8:v0:occurrence-1,
  LEVEL02_LEVEL:0x800B47C8:v0:occurrence-2,
  LEVEL02_LEVEL:0x800B47D4:v1, LEVEL04_LEVEL1:0x800B4AA8:v1,
  MEMORY:0x800B7EA4:at, MEMORY:0x800B7F04:at,
  MEMORY:0x800B7F64:at, SCUS_942_88:0x80048368:v0,
  SCUS_942_88:0x8004836C:v0, SCUS_942_88:0x80048370:v0,
  SCUS_942_88:0x80048378:v0, SCUS_942_88:0x8004B2A8:a0,
  SCUS_942_88:0x8004B318:a0, SCUS_942_88:0x8004B4F4:a0,
  SCUS_942_88:0x8005C5B4:s2, SCUS_942_88:0x8005C5C0:s2,
  SCUS_942_88:0x8005C5C8:s2, SCUS_942_88:0x8005C5D4:s2,
  SCUS_942_88:0x8005C5E8:s2}`;
- lost `blocked_return_domain_needs_index_convention` (6):
  `{LEVEL01_LEVEL1:0x800B401C:v0, LEVEL01_LEVEL1:0x800B4068:v0,
  LEVEL03_LEVEL1:0x800B3D88:v0, LEVEL03_LEVEL1:0x800B3DD8:v0,
  LEVEL03_LEVEL1:0x800B408C:v0, LEVEL03_LEVEL1:0x800B4140:v0}`;
- lost `blocked_no_recovery_method` (2):
  `{LEVEL02_LEVEL:0x800B4788:a0, LEVEL02_LEVEL:0x800B4844:v0}`;
- lost `blocked_writer_universe_exhaustiveness` (24):
  `{LEVEL03_LEVEL:0x800B3DD8:v1, SCUS_942_88:0x8004AEE4:s1,
  SCUS_942_88:0x8004AEF8:s1, SCUS_942_88:0x8004AF7C:s1,
  SCUS_942_88:0x8004AF8C:s1, SCUS_942_88:0x8004B208:s1,
  SCUS_942_88:0x8004B214:s1, SCUS_942_88:0x8004B220:s1,
  SCUS_942_88:0x8004B224:s1, SCUS_942_88:0x8004B234:s1,
  SCUS_942_88:0x8004B238:s1, SCUS_942_88:0x8004B254:s1,
  SCUS_942_88:0x8004B260:s1, SCUS_942_88:0x8004B274:s1,
  SCUS_942_88:0x8004B2D0:s1, SCUS_942_88:0x8004B2D8:s1,
  SCUS_942_88:0x8004B2E0:s1, SCUS_942_88:0x8004B464:s1,
  SCUS_942_88:0x8004B570:s1, SCUS_942_88:0x8004B5D8:s1,
  SCUS_942_88:0x8004B638:s1, SCUS_942_88:0x8004B650:s1,
  SCUS_942_88:0x8004B664:s1, SCUS_942_88:0x8004B678:s1}`.

The exact 52-ID gained set and all empty reverse sets are machine-retained at
`movement_from_b6cb61d35f9d.outcome_site_set_movement`. Against
`05bc6b8a251b`, exactly 46 row IDs change breaker: 20 replace a prior breaker
and 26 previously had none; every new breaker is the locally-defined-`ra`
`0x03E00008`. The exact IDs and before/after records are retained at
`breaker_movement_from_05bc6b8a251b.changed_breakers`.

### Typed-state result, gate retention, and measured reuse

No convention becomes proof. Ledger movement against `b6cb61d35f9d` is the
empty set in both directions for every bucket: **20,431 = 219 proof / 2,769
convention / 17,443 unresolved**. Fixture movement is likewise empty:
**238 = 0 proof / 45 convention / 96 unresolved / 97 absent**. The stricter
shared CFG reduces the diagnostic exact-table candidate universe from 1,598 to
127 (baseline-only 1,471, current-only 0), partitioned as **97 interval-
unproved / 3 alias-overlap / 27 external-entry / 0 upgraded** across 94 unique
index queries. It records 2,642 base-classification failures; 1,708 rows carry
1,721 exact failed-definition breakers. This is intended under-claiming, not a
reason to widen TABLE or the interval whitelist.

The reopened table-backed bindings remain rejected. Their evidence still says
**5,012 undecided stores across 21 images**, writer universe
`exhaustive=false`, and unproved value-domain induction. The 23 affected
typed-pointer rows now carry both the earlier local-`ra` table breaker and the
coexisting `0x80090748` writer-universe cell. No writer or value-domain gate is
weakened.

The standalone non-promoting reuse receipt measures resident window
`[0x800A657E,0x800A6580)`: all **11,352** resident STORE access rows are the
source universe; C rejects 78 stale base/access claims, leaving an exact
table-address-class universe of **124**. Its exhaustive interval partition is
**0 decided / 110 unproved / 6 proved-but-overlapping / 8 external-entry
unclosed**. On the same 124 IDs, convention decides **1** by sign/loop bounds,
**45** by unconditional alignment, **46** by either, and the convention-only
set is exactly
`{resident-store:all_model_file_load_unpack@0x80030D64:0x80030F40:t4:0:4}`.
Against `05bc6b8a251b`, the strict universe has baseline-only 615 and
current-only 0: exact losses are 580 interval-unproved, 22 overlap, and 13
external-entry. The receipt explicitly changes no row, registry, status, or
promotion dimension.

### Reproduction, identities, and pre-acceptance status

Commit `3bb215673887` carries the regenerated receipts and bounded DAG. A new
detached worktree at that commit copied exactly **327** pristine staged inputs
as regular files, with zero symlinks and zero nonregular entries; build identity
passed 327/327. Regenerating typed state, the campaign, the non-F01 receipt,
and all three inventories produced no byte change and left the worktree clean.
`phase4_inventory.py` returned its expected existing `OPEN` state; its retained
gap sets did not change. Current identities are:

- C prover:
  `1d36befa78a25e302dc292bac789472dadc87e318c1f638eae07ecfeb2e19a9d`;
- typed state:
  `6cf4ed22fd0b5316e5e2732ff19912b783611dde53a720b80f262fce1d733aef`;
- 102-row campaign:
  `2d6b751dcbc540a2278db10c53ef076061ca1b8f7f6f0cf42e3f5079a3403765`;
- non-F01 receipt:
  `3b007cfe41865e3d2c7784baac37df08062d350cca6368c57b6554f4cf9f514d`;
- campaign inventory:
  `17c74acf76974a34b2111d3cf629296bbb8105539f3feeedb9d198552368f98f`;
- fixture / knowledge inventories, unchanged:
  `3beb3375c103cdd88d13bf8ea042c29ea220567e4da7aa1b76f44ce714f52bcd`
  / `47da5515a69a13abc806b9e242447626023766019f6e67a1841ffa7555a7236e`;
- bounded DAG:
  `04f4cf1d6df8c3ada4236b1a490bc6f4152acc072aa2bd95a744d0a962bded05`.

The DAG changes only the regenerated campaign-inventory identity in exact
consumers `{offline_queue, closure_debt, phase4_gate}`, whose fingerprints are
`{172625df5faea806e797eb9ea869320f943f1422e3f797ae9eac1fdb4e8b68ce,
9b4e8d8a90633bcd059a5fb6fb6655f5a531e04f6900e0b148d94202baa1dfe6,
2c52455a19e3239bd77ce37fe246fe1d82187c994e5169fe3ae013a7f95f1adc}`.
The retained 307-file movie-tree identity
`144283bbf0e540f1b5f0a8ec02480475d2c57543c6595a28830224d03d39fe62`
is byte-preserved; operator movie WIP was not read into the graph.

Focused commands were:

```bash
gcc -O2 -std=c11 -Wall -Wextra -Werror -o <scratch>/phase4-prov \
  tools/phase4_typed_state_provenance.c
<scratch>/phase4-prov --self-test
python3 tools/phase4_typed_state.py config/phase4_f01_typed_state.yaml \
  --output analysis/phase4_f01_typed_state.json \
  --survey analysis/phase4_f01_abi_survey.json
python3 tools/phase4_f01_local_base_recovery.py \
  --output analysis/phase4_f01_local_base_recovery.json
python3 tools/phase4_index_interval_demo.py \
  --output analysis/phase4_index_interval_non_f01_demo.json
python3 tools/phase4_inventory.py  # expected OPEN
python3 -m pytest -q tests/test_phase4_typed_state.py \
  tests/test_phase4_f01_local_base_recovery.py \
  tests/test_phase4_index_interval_demo.py \
  tests/test_phase4_f01_static_hard_truth.py
python3 tools/build_identity.py --verify
```

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The mechanics baseline,
registry, gate receipt, writer-universe and value-domain gate artifacts, static
hard-truth artifact, and receipt retraction blocks remain untouched. Zero table
indices became proof, so there is deliberately no Canon promotion. This is a
pre-acceptance repair record: a new fresh detached hard-truth verifier must say
exactly `agreed` before any acceptance block banks it.

## 2026-08-07 Hard-Truth round 11 interruption: ORI and call-boundary phases

Fresh detached candidate `98b90462478c89d62a96449b069787bda78ced17`
was audited in `~/.cache/abl-phase4-r11-verify.B8AnLn/tree`. The
verifier process was interrupted by an external content filter before it could
emit the required terminal schema, so **there is no round-11 verdict and no
round-11 acceptance**. The retained prompt SHA-256 is
`7320a97b9bca4f70c2d97b68b7aa8cf74e70707a485c40e96d8bac6c1afaf4c4`;
the partial audit-log SHA-256 is
`076f3cec25d9296d2ec277f10ddd2543c10526bc64afe54c16850c999f38ff97`.
The shared verdict-schema SHA-256 remains
`c248873a4cd14c78db0ba6f365e226f41903c74e6c1594b85d4c8bb0febd6a43`.

Before interruption, that independent run constructed and reproduced two real
full-consumer false-proof shapes:

- `lui t1,0x8008; ori t1,t1,0x23a0; ori t1,t1,0x2000` must remain
  `0x800823A0`. The old reverse accumulator added the second ORI immediate and
  invented `0x800843A0`, which could turn an in-window table into a miss.
- `jal target; lui t1,0x8009` writes `t1` in the call's delay slot. The value is
  visible when the callee receives arguments, but a caller-saved `t1` is not a
  fact at the post-call continuation. The old TABLE walk could carry it through
  the callee and certify a false table base.

Commit `f7a6d12082da` made ORI evaluation ordered and bitwise and rejected a
caller-saved delay-slot definition used after return. Its first implementation
was deliberately remeasured before receipt regeneration; that clean run caught
an over-broad repair immediately: the legitimate F01 `defsat@` caller argument
at `0x8004EFD8` was also labelled clobbered, moving the ledger from 219 proof
rows to zero. No artifact from that intermediate run was committed.

Commit `7715fd93f912` now models the two temporal phases separately. An explicit
`defsat@...:CALL_PC` query observes the state after the delay slot and before the
callee executes. A query about the continuation retains the ordinary
caller-saved clobber. Call-boundary source constants require all reaching
definitions to agree; a continuation that can loop back to the same static
call rejects rather than conflating two dynamic invocations. `$ra` sources are
also rejected because the helper does not model the link value visible in a
delay slot.

The permanent controls cover all three directions:

- overlapping ORI bits report table `0x800823A0`, and the full consumer keeps
  the convention because that table overlaps the watched window;
- the synthetic continuation query rejects at the owning `jal` with
  `call_delay_definition_clobbered_before_continuation`;
- the paired call-boundary query and the real F01 caller recover the delay-slot
  argument `0x800A6500` as `materialised_constant`.

The `-Werror` C self-test is **36/36** and the focused consumer suite is **90
passed**. These are regression closures, not accepted residual regressions.

### Regenerated outcomes and exact-set stability

Commit `05421715495e` carries the regenerated artifacts. Relative to the
previous `3bb215673887` receipts, every semantic site-set movement is empty:

- typed proof gained/lost `{}` / `{}`; convention gained/lost `{}` / `{}`;
  unresolved gained/lost `{}` / `{}`;
- campaign outcome changes `{}` across all 102 row IDs;
- non-F01 interval-outcome changes `{}` across all 124 receipt IDs.

Against prerequisite `b6cb61d35f9d`, the exact 52-row campaign movement and
all reverse-empty sets remain exactly those enumerated in the preceding
round-10 section and machine-retained in
`movement_from_b6cb61d35f9d.outcome_site_set_movement`. The exhaustive campaign
partition remains **0 decided / 52 interval-instruction / 26 writer-universe /
9 return-domain / 8 no-recovery / 5 stack-entry / 1 external-entry / 1
progression**. Typed state remains **20,431 = 219 proof / 2,769 convention /
17,443 unresolved**; the fixture remains **238 = 0 proof / 45 convention / 96
unresolved / 97 absent**. The only non-hash diagnostic change is the already
rejected `0x8004A700:s0` survey row becoming more precise: its caller failure is
now `opaque`, rather than the temporally conflated `call_result, opaque`.

The non-promoting second-window receipt remains **124 = 0 interval-decided /
110 unproved / 6 overlapping / 8 external-entry-unclosed**. Convention still
decides exactly one sign/loop site,
`{resident-store:all_model_file_load_unpack@0x80030D64:0x80030F40:t4:0:4}`.
No row status or artifact outside this standalone capability measurement moves.

Current exact identities are:

- C source:
  `8686805e3e9801197dc52562f3b8969d344f10ded7ed1bcc5fb06ccdab7617e3`;
- rebuilt C binary recorded by the consumers:
  `4a720886c132594fe080bb6bb4324d8bc3d640fdbfed6846c99bf7e87a2dfee7`;
- typed state / ABI survey:
  `3eded114c55ab4eb0211e24523cb43249639dea1d276db838818c79055d3945d` /
  `a44dea63f67ba33b6d38c853aaa8e7becf8e314593d341805deafd80aa94902c`;
- campaign / non-F01 receipt:
  `95538c79d1b235802a422d30e5ce92ba438e1e3f02f521b9c9c6e9e0d00fc784` /
  `4d2888c1c3283c1884ef4eb45d67fc6cbc7f6e4ab43c5a0ca765a6756110b3ad`;
- campaign inventory / bounded DAG:
  `6387751be169eb12f4be3ec1628c4fe10af282fe91ae0aa45b8a6415616f2cd8` /
  `0688d69b58b4b46d291ba18d4cd13d0b466eb31cc19cfeaff609704867ebea31`;
- fixture / knowledge inventories, unchanged:
  `3beb3375c103cdd88d13bf8ea042c29ea220567e4da7aa1b76f44ce714f52bcd` /
  `47da5515a69a13abc806b9e242447626023766019f6e67a1841ffa7555a7236e`.

The bounded DAG changes only the exact campaign-inventory input of
`{offline_queue, closure_debt, phase4_gate}`. Their new fingerprints are
`{b49f56cba2a035271a0487d64466e01236f1e5f1498e104e37976fbe803efe23,
edf57b16e8ee684cfa7437d56aee2e50021439522b54fc2a1092a6317a114660,
4f508b2ec1896e30131811b7cde81e34ad55b15463f8ae27bee60e412c30339a}`.
The retained movie-tree input remains exactly 307 files / 753,700,091 bytes /
`144283bbf0e540f1b5f0a8ec02480475d2c57543c6595a28830224d03d39fe62`;
operator movie WIP was not imported.

A fresh detached worktree at `05421715495e` copied exactly 327 pristine staged
inputs as regular files, with zero symlinks and zero nonregular entries. Build
identity passed 327/327. Rebuilding C with `-Werror`, regenerating typed state,
the 102-row campaign, the second-window receipt, and the inventories produced
the exact hashes above and left the checkout clean. `phase4_inventory.py`
returned its expected pre-existing `OPEN` exit 1 with unchanged gap classes;
the focused suite passed 90/90.

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The mechanics baseline,
registry, gate receipt, writer-universe and value-domain gates, static
hard-truth artifact, and retraction blocks remain untouched. Zero table indices
became proof, so Canon remains unchanged. This is still pre-acceptance: the
interrupted round produced no verdict, and a new fresh detached verifier must
return exactly `agreed` before the acceptance block is banked.

## 2026-08-07 Hard-Truth round 12: architectural call-link writes

Fresh detached candidate `1e05202246466b39583fc84f01acb5e83a3bcc5d`
returned exactly `unverified` with `banking_authorized=false`. The independent
auditor reproduced all retained counts, hashes, movements, protected gates,
327 pristine input pins, 36 C controls, and 90 focused tests, then found one
remaining false-proof root in two adjacent instruction shapes. A targeted call
query suppressed the call node as a clobber and accidentally erased its real
architectural link-register definition:

- direct `jal` writes `$ra = call_pc + 8` before its delay slot, but querying
  `$ra` at the boundary returned a stale pre-call constant;
- `jalr rd,rs` writes the same link value to `rd`, but a delay-slot copy from
  that non-`$ra` destination could likewise be certified from the stale value.

The retained JALR reproducer is
`{0x3C108009,0x03208009,0x26040000,0x0800C000,0x00000000}` at
`[0x80010000,0x80010014)`: `jalr s0,t9` makes `s0=0x8001000C` before
`addiu a0,s0,0`, so `a0=0x80090000` is impossible. The verifier receipt names
fixture SHA-256
`fcd1d5322f24b8ac65ce8f0d9a3bb74fcbf0fc56801c6eab0ed74fcc94351a54`;
its direct-JAL companion is
`44c97e56f37483652f8895917c4c7c5adfa51e7071d5e6379873ef349df7f528`.
Round-12 evidence identities are prompt
`55046177c231a1c17552a85c6dcd4fa13c780b4619f6fab5d481232a3cfeafb0`,
schema
`c248873a4cd14c78db0ba6f365e226f41903c74e6c1594b85d4c8bb0febd6a43`,
log `206e4a5b9ae9f3552153047d23b3ea41fd5752e9d9f9d3cd204e0cbe4e62c11c`,
and verdict
`12b564b77e601bd018070ab92a7bad4f441f4ba772b8dd25b133b0ef899ae2bd`.

Commit `b9549d48a8cc` closes the root defect without modelling a wanted value.
`jal` now names register 31 and `jalr` names its nonzero `rd` as the link
destination. Boundary suppression preserves that definition; the classifier
then reports it fail-closed as `opaque` with
`call_link_value_not_modelled`. A delay-slot argument derived from either link
destination is rejected. A source-dependent path that can return to the same
static call is also rejected, while a direct `lui` in the delay slot remains a
sound invocation-independent constant.

Five permanent C controls cover JAL link-source rejection, JALR link-source
rejection, source-dependent call-boundary re-entry rejection, direct-delay
`lui` acceptance, and preservation of the call-link definition. The `-Werror`
self-test is now **41/41**. The focused end-to-end suite adds both public call
forms and both temporal phases and passes **91/91** in a fresh detached tree.
Thus the round-11/12 findings are closed regressions, not accepted permanent
regressions.

### Round-12 repair receipts and unchanged semantic sets

Commit `e15800e4bc76` carries the regenerated artifacts and bounded DAG. The C
source / rebuilt binary identities are
`503a4e2178bc52e15f887e80b42b6111ca64f94728199aae654e4223f4d4803b` /
`30b9132fb9509fd175bcb11736586366402205d6448b99dc8ad16f2978aa4035`.
Artifact identities are:

- typed state / ABI survey:
  `94a4a76860e39b3fc6733c01ff3bc9ea356ccfcaf69240841f6e550ff96ea681` /
  unchanged `a44dea63f67ba33b6d38c853aaa8e7becf8e314593d341805deafd80aa94902c`;
- 102-row campaign:
  `b6b247e66b95b576f7d2f15f366a37b09ce11091fe76d83dccca2de0213c81ad`;
- non-F01 receipt:
  `6bb44127b94c56df2d68376055ca5c0867f45125a46fec43d349831b666d1e09`;
- campaign inventory:
  `b4d6cf6c92d5346c6ccf1091fbc560692fc8bbc72ed37f37ca78b051da81a6ad`;
- bounded DAG:
  `189e5cfbd32019117ff9fc3f2b429449f18f1cf8bf47c086d26347af3ffaeb4e`.

The bounded re-pin changes only the campaign-inventory input in its three
declared exact consumers. Their fingerprints are
`{26ac3f2d245259261d4592d711a54ccb79a25d976f9535868463887032e97356,
af2edacee9db7678891c1c7bddc2c6354514f0819d15f725c5d25e58774591b8,
fc0efb784018a5db456463208103db130723ee76ccbe92716f3f2f90fa2da505}`.
The unavailable retained movie identity remains exactly 307 files /
753,700,091 bytes /
`144283bbf0e540f1b5f0a8ec02480475d2c57543c6595a28830224d03d39fe62`;
eight unrelated operator movie additions were not imported.

All semantic movements from the preceding receipts are empty in both
directions. Typed state remains **20,431 = 219 proof / 2,769 convention /
17,443 unresolved**; the fixture remains **238 = 0 proof / 45 convention / 96
unresolved / 97 absent**. The campaign remains **102 = 0 decided / 52
interval-instruction / 26 writer-universe / 9 return-domain / 8 no-recovery /
5 stack-entry / 1 external-entry / 1 progression**. The non-promoting second
window remains **124 = 0 decided / 110 unproved / 6 overlapping / 8
external-entry-unclosed**, versus one convention-only site. The exact 52-row
forward campaign movement against `b6cb61d35f9d` and every empty reverse set
remain machine-retained in the artifact.

Fresh detached regeneration used exactly 327 copied regular pristine inputs,
zero symlinks, and zero nonregular entries; identity passed 327/327. The C
self-test passed 41/41 and the focused suite passed 91/91. An exhausted `/tmp`
quota initially interrupted duplicate validation; only two old verifier-owned
temporary work copies were deleted, after confirming no process referenced
them. No repository, operator WIP, capsule, movie, or source artifact was
removed.

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The mechanics baseline,
registry, gate receipt, writer-universe and value-domain gates, static
hard-truth artifact, and retraction blocks remain untouched. Zero table indices
became proof, so Canon remains unchanged. This repair record is still
pre-acceptance until a fresh detached verifier of the repaired candidate says
exactly `agreed`.

## 2026-08-07 Hard-Truth round 13 acceptance

A fresh detached verifier audited exact candidate
`4af34dbb656fe744c247df54d4a731baa7fd51d4` and returned the terminal schema
verdict exactly `agreed`, with `banking_authorized=true` and `gaps=[]`. This is
the required independent acceptance of the call-link repair and the complete
instruction-derived unsigned-interval increment.

External acceptance identities are:

- prompt:
  `39cd7889af7126515c1477e78db2bd324b31779ec79b0baa7b15f5ceeb008b4d`;
- schema:
  `c248873a4cd14c78db0ba6f365e226f41903c74e6c1594b85d4c8bb0febd6a43`;
- full verifier log:
  `fdaf3b8e9427d27bd283ac509585c7fc3779801ba0b0a79cb4a3e668de119ae2`;
- terminal verdict:
  `b9fa148c20f23c98c6c316055166d94abb9f32c2405d7e367127d4d15952cd29`.

The verifier independently passed 41/41 C controls, 91/91 focused tests, all
31 nonzero JALR link destinations, the full raw-word adversarial matrix, exact
campaign/ledger/fixture/non-F01 set recomputation, byte-identical artifact and
inventory regeneration, 327/327 pristine input identity, bounded-DAG
preservation, and protected-state comparison. Its scratch was removed and its
detached checkout was clean at the candidate.

Acceptance banks the machinery and receipts, not a row promotion. F01 remains
`partial`; item 2 remains `not_met`; both review booleans remain false; blockers
remain exactly `[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. No Canon
table-index fact is added because the proved-upgrade set is empty.

## 2026-08-07 — partial-gap reconnaissance: the remaining 11,958 bytes, classified

Scouting pass for the content-verification campaign, banked so the work order
can name its targets exactly. Inventory (unevidenced bytes only):

| region | unevidenced | content classification (recon, NOT proof) |
|---|---:|---|
| `0x8007E8B8..0x80081D98` | 5,325 | heterogeneous. Head run `0x8007E8B8..0x8007EFE8` (1,840 B) is a MONOTONE CONCAVE u16 curve, 67 → ~506, decaying increments (63/100 → 34/100) — not a single rational ramp (fit refuted), sine-family fits inconsistent at A=512/N=4096. **Zero resolved static accesses reach the run** — readers use computed bases; identification needs runtime reader attribution (accessLog over the run during a replay) or deeper content modelling. Also contains 92 B of function-entry-pointer runs (`0x8007FB78`, `0x80080DC8`, `0x80081D74`) |
| `0x8001B828..0x8001CA20` | 3,659 | the mover-VM/plant-behaviour DISPATCH BANK zone: interleaves decoded jump tables (already classed) with handler-pointer tables — words include `seed_plant_trampoline_handler` and siblings. The unevidenced runs are the between-table content; 28 B of ≥3-entry pointer runs at `0x8001B384` tail |
| `0x80078D84..0x8007941C` | 1,434 | mostly zero-adjacent scattered runs |
| `0x8001B0BC..0x8001B42C` | 344 | dispatch-table zone remainder |
| `MEMORY 0x800BAB8C` | 348 | scattered non-zero runs |
| `0x80077080..0x800771BC` | 304 | MONOTONE u16 curve rising 16,107 → peak ≈16,369 then decaying — a fixed-point curve tail (16,384 = 1.0 in .14?); possibly the continuation of a table starting in the preceding claimed extent |
| LEVEL03/LEVEL07/small `none` gaps | 544 | s16 coordinate-like records (`0x80077A8C`: ±0x20-scale pairs), config-record shapes (`0x80079DA0`), two 4-B cells |

Mechanical result, exact: function-entry-pointer runs (≥3 consecutive words
each equal to a census code/thunk entry) cover **120 B** of the unevidenced
set at 4 named ranges — a small, structurally verifiable class ready to ship
with the campaign.

The reconnaissance conclusion: this campaign needs (a) ONE instrumented
replay with accessLog read watches over the three big regions to name their
readers (the same method that cracked the trig tables), then (b) per-region
content models verified byte-exactly, with the entry-pointer-run class as the
mechanical floor. No census number was changed by this recon.

## 2026-08-07 — partial-gap campaign executed: readers attributed, three evidence classes shipped, 11,958 → 9,760

The campaign the recon above scoped, executed end-to-end. Two instrumented
replays on the isolated instance (config `/tmp/dsrepro-f01-gapreaders-1786140333`,
port 23473, Interpreter movies), then a compiled-C semantics probe, then census
integration.

### Replay sessions (runtime attribution — LEADS, not census evidence)

Session 1 — `LEVEL01_AntHill` any% movie, 63 merged ≤256-B read watches over
every unevidenced run plus a positive-control write watch on the player block
`0x800A6510` (fired). 91,940 read events. Session 2 — `LEVEL03_CouncilChamber`
movie for the 8 windows LEVEL01 left silent plus the LEVEL03 overlay gap.
Raw sessions preserved outside Git:
`~/Downloads/ABL-external-evidence/phase4_f01_gap_readers_2026-08-07/`
(`gapread_L01.json` cf7f73b8…, `gapread_L03.json` 3ae85927…, driver
`gap_reader_session.py` 45835c68…, plus `SHA256SUMS`).

| gap | reader (pc-attributed, pc+4 corrected) |
|---|---|
| `0x8007E8B8` head curve | **atan2_heading** `0x80060BA8/0x80060C34` — `lh` at base `0x8007E7E4` |
| `0x80077080..0x800771B0` | **gte_rotation_matrix_setup** — same consumer as the verified sine table |
| `0x80078D84` region | results_screen_render + type-0x3f contact dispatch |
| `0x8001B0BC` | mover_vm_dispatch_next (16-entry dispatch table) |
| `0x800817D4..0x80081D48` | PsyQ **libcd work RAM** (CdControl/CD_sync/getintr) + **libpad SIO state** (_padSioRW) — runtime BSS, not tables |
| `0x800821A2` | cd_audio_mix_control + SPU voice code |
| silent in both runs | `0x8001B828` unevidenced runs, `0x80077458`, `0x80077A8C`, `0x80079DA0`, LEVEL03 `0x800B4C18` |

### Static proof (the actual census evidence)

`tools/phase4_f01_gap_semantics.c` + `.py` → `analysis/phase4_f01_gap_semantics.json`.
Three claims at three explicitly different tiers:

1. **content_verified_trig_tail** (240 B, `0x80077080..0x80077170`): the
   established sine formula `llround(16384*sin(2πk/4096))` re-derived over the
   gap overlap — 0 mismatches. Same tier as the main trig disposition.
2. **reader_indexed_atan_table** (1,838 B clipped, extent `0x8007E7E4..0x8007EFE6`):
   all 12 indexing/fold instruction words of atan2_heading verified
   (base `0x8007E7E4`, s16 entries, index `(min<<10)/maj ∈ [0,1024]`, folds
   `0x400`/`0x800` — PSX 4096 = 360°). **The analytic content model FAILED the
   exact bar**: vs `llround(atan2(k,1024)*4096/2π)` the deviation histogram is
   {0: 836, +1: 189, other: 0}, and interval intersection proves NO uniform
   multiplier fits all entries. Per the hard-truth rule a 99%-model is a failed
   model, so the extent claim rests on the verified instructions alone and the
   model is carried as corroboration.
3. **function_entry_pointer_runs** (172 B raw, 172 B clipped; 52 B overlap
   bytes another class already evidences): ≥3 consecutive words each exactly a
   census code/thunk entry, false-positive model stated in the receipt.

Circularity guard: the scanned ranges are PINNED IN THE DRIVER, not read from
the census (the census consumes this receipt); the census clips every claimed
interval to its own current gap set, so a stale pin can never widen anything.

### Census integration + chain

- Index: receipt added to `source_dependencies` (pins its sha).
- Census: validates the receipt fail-closed — `atan_instructions_verified` and
  `sine_tail_exact` required true, `atan_content_model_exact` required exactly
  **False** (so a future "now it's exact" regeneration forces a human look).
- Result: **gap_bytes_with_no_evidence 11,958 → 9,760** (union −2,198),
  evidenced 25,432 of 35,192 gap bytes (16,892 semantic), dispositions
  {complete 72, none 4, partial 9}. The former largest unevidenced range
  (`0x8007E8B8..0x8007EFE8`) is evidenced to within its final 2 B; the largest
  survivor is now `0x80078E9E..0x8007913C` (670 B, results-screen gap).
- Chain regenerated in order: index → census → seed sha repin → extractor →
  `phase4_f01_frontier_result.json`. F01 verdicts unchanged and correct:
  `partial`, item-2 `not_met`, blockers
  `[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`.
- Tests: 197 pass; census pins re-derived then re-pinned intentionally
  (11,958 → 9,760, new class byte counts, new largest-range identity).

### What this does NOT claim

No disposition flipped to `complete`; the three classes are byte-interval
evidence inside still-`partial`/`none` gaps. Runtime attributions (libcd,
libpad, SPU, results screen) are leads bounded to the two captured runs. The
remaining 9,760 B are dominated by the dispatch-bank interleave
(`0x8001B828`), the results-screen scattered runs, and the libcd/libpad BSS —
the last being runtime work RAM for which a content model is the wrong tool;
a boundary/ownership argument (PsyQ library data extents) is the plausible
next class.

## 2026-08-07 — PsyQ library-extent ownership: partition map banked, census movement is a REVIEWED NEGATIVE

The follow-up the partial-gap campaign queued: convert the libcd/libpad/SPU
"runtime work RAM" lead into a census class via a library-extent ownership
argument. Executed statically (no instrumented run spent — first application
of the batching standing rule: don't pay a slow replay for one row's
question). Result: **the census-grade form of the argument does not exist at
acceptable proof cost; 0 bytes moved (no_evidence stays 9,760), and the walls
are named.** The machine-derived partition map is banked as semantics.

### What the sweep proved (tools/phase4_f01_library_partition.c, in the receipt)

A conservative linear constant tracker (labels clear all state, moves
followed, $gp reseeded with the proven constant) over all 947 census
functions, zone 0x8007E8B8..0x800822F0:

- **1,753 sites** materialize or access constant addresses in the zone
  (324 gp-relative — all into the evidenced sdata above/around $gp; **zero
  gp-relative references reach any unevidenced byte**, because PsyQ .LIB
  objects are compiled -G0 and cannot assume the game's $gp).
- **90 below-$gp materializations + 1 crt0 $gp-setup site (stup1)**. The
  below-gp owner set is dominated by PsyQ API names — the full CD command
  set (CdControl/B/F, CD_sync/ready/cw/datasync/flush/init, getintr,
  CdRead family), libpad (_padInitSioMode, pad_sio_*), libspu/libsnd
  (_SpuInit, _spu_init, _SsInit, _SsStart), libgpu (ResetGraph, ClearOTagR,
  DrawOTagEnv, Fnt*, MoveImage), libapi intr — plus some game-side glue,
  which is why the receipt reports the owner lists VERBATIM instead of
  encoding a categorical "all library" claim.
- The work-area partition by base is in the receipt
  (`library_workarea_partition.probe.distinct_targets`): 0x800810B8 SPU,
  0x80081504 _spu_init, 0x8008183C CdControl queue, 0x800818EC CD_datasync,
  0x8008196C CD_sync/ready/cw, 0x80081BA4-BA8 CD status cells,
  0x80081BE0..0x80081C10 CdRead family, 0x80081D34/D48 pad SIO.

### Why zero census bytes moved — the walls, each with its falsifier class

1. **Pointer indirection**: libcd parks work-area pointers in variables
   (0x80081B8C/94/98) and dereferences them; static constant tracking ends
   at the load. (Falsifier: a value-domain proof for those pointer cells.)
2. **Caller-dependent index domain**: the libpad port array 0x80081D48
   (stride 4, 8 B) is indexed by a caller-supplied port — the same
   obstruction class that blocked the local-base campaign's 102 rows.
3. **No materialized clear bounds**: CD_init/_padInitSioMode initialize
   cells individually or via helpers (jal 0x8005F7DC with the area address
   as argument); no memset-style loop materializes (base, end), so no
   atan-grade extent proof exists.

Key structural finding: the census's existing `read_as_data` (from the
shared analyser's bounded-access recovery) had ALREADY extracted everything
direct static references can give — the remaining unevidenced zone bytes
are reachable only through the walls above. The stride-0x44 pattern at
0x80081608..0x80081758 (six 64-B runs separated by single evidenced words)
has NO direct references to the separator cells; they were evidenced by
recovered indexed accesses, confirming the same conclusion from the other
side.

Receipt schema bumped to abl-phase4-f01-gap-semantics/2 (claims unchanged;
census validation untouched — it pins verdict fields and claim shapes, not
the schema string). Chain regenerated to fixed point; F01 verdicts exactly
{partial, not_met, [IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]};
197 tests pass.

## 2026-08-07 — caller-domain pilot universe frozen (PRE-OUTCOME record)

This is the mandatory ordering checkpoint for
`engineering-specs/phase4-caller-domain-work-order.md`. It was written while
HEAD was `951a70bca0750b24bc0d5f2cc5b70d9f97a9e1e9`; the issued baseline
`fc2a708754320a38877c59f47f6997a0a42f25ce` is an ancestor. **No caller
closure, propagated domain, capsule comparison, per-site result, or GO/NO-GO
outcome had been produced when this list was frozen.** A result record is
valid only in a descendant commit, after this checkpoint is banked.

The named sampling universe is the 102 rows in
`analysis/phase4_f01_local_base_recovery.json` at SHA-256
`e5d79263398a927a518db682ce3c9920dccd2a48004b9e0cb251522307b15320`.
Selection is deterministic and outcome-blind:

- stack-entry stratum: all five rows;
- return-domain stratum: the lexicographically first row in each of the five
  represented images (`LEVEL03_LEVEL1`, `LEVEL05_LEVEL1`, `LEVEL07_LEVEL`,
  `LEVEL08_LEVEL`, `LEVEL09_LEVEL`), giving five rows without weighting an
  image twice;
- argument-carrier index stratum: ten rows fixed from already-banked C
  definition shapes — the single stack-carried `$t1` index row, the three
  rows whose recovered table index register is `$a0`, the five rows sharing
  the entry-fed `$s5 -> v0` scaled-index chain, and the remaining overlay row
  whose address-forming instruction carries `$a0`. “Carrier” is a sample
  qualifier, not a proof that the entry value survives: a local clobber or a
  non-argument stack slot must become a named pilot wall. The recovered-index
  metadata is pinned to Git object
  `92e249a8807b:analysis/phase4_f01_local_base_recovery.json`, SHA-256
  `b3b101b5ac45017b2c6effc4d68f66600d29400029987f1c494a61a4810a1a55`;
  the current strict-C artifact supplies the later fail-closed breakers.

The exact fixed 20-site set is:

| stratum | site ID |
|---|---|
| stack-entry | `LEVEL02_LEVEL1:0x800B3F14:sp` |
| stack-entry | `LEVEL02_LEVEL1:0x800B43AC:sp` |
| stack-entry | `LEVEL05_LEVEL:0x800B4040:sp` |
| stack-entry | `LEVEL05_LEVEL:0x800B4048:sp` |
| stack-entry | `LEVEL08_LEVEL1:0x800B416C:sp` |
| return-domain | `LEVEL03_LEVEL1:0x800B41AC:v1` |
| return-domain | `LEVEL05_LEVEL1:0x800B494C:s0` |
| return-domain | `LEVEL07_LEVEL:0x800B4774:a3` |
| return-domain | `LEVEL08_LEVEL:0x800B4284:s0` |
| return-domain | `LEVEL09_LEVEL:0x800B4640:s0` |
| argument-carrier index | `LEVEL02_LEVEL:0x800B4788:a0` |
| argument-carrier index | `LEVEL04_LEVEL1:0x800B4AA8:v1` |
| argument-carrier index | `MEMORY:0x800B7EA4:at` |
| argument-carrier index | `MEMORY:0x800B7F04:at` |
| argument-carrier index | `MEMORY:0x800B7F64:at` |
| argument-carrier index | `SCUS_942_88:0x8005C5B4:s2` |
| argument-carrier index | `SCUS_942_88:0x8005C5C0:s2` |
| argument-carrier index | `SCUS_942_88:0x8005C5C8:s2` |
| argument-carrier index | `SCUS_942_88:0x8005C5D4:s2` |
| argument-carrier index | `SCUS_942_88:0x8005C5E8:s2` |

Cardinality checks at freeze time: 20 unique IDs = 5 stack-entry + 5
return-domain + 10 argument-carrier index; all 20 occur exactly once in the
102-row source universe and carry the required current wall. The pilot limit
is depth 3; no full-corpus pass is authorized until a descendant log section
records the per-site table and explicit decision.

## 2026-08-07 — caller-domain mandatory pilot: reviewed NO-GO (0/20)

The pre-outcome universe above was banked first in commit `de8b10512c69`.
Only then did the pilot implementation and receipt land in descendant commit
`2e1266fa18db`. This preserves the work order's ordering test: the sample was
fixed before any site outcome existed.

### Correctness findings

The pilot decided **zero of 20** sites. That is a useful negative, not a
permission to widen the analyser:

- exactly 10 sites are poisoned by OPEN caller sets. This is not the work
  order's separate `>10` OPEN-majority trigger; the decisive NO-GO condition
  is instead `0 < 3` decided sites;
- two supposed return-domain rows store in a `jal` delay slot. The store
  executes before the callee, so the value at that instruction cannot be the
  callee's return value;
- three other return rows reach the shared `A0E0` shim by fallthrough. Its
  return path contains `addu v0,s0,zero` at `0x8005A2F0`, but `$s0` has no
  proved domain from that alternate entry;
- five argument-carrier candidates are not caller-domain questions at the
  relevant instruction: one `$a0` is locally replaced, one `sp+0x60` load is
  inside a 144-byte local frame rather than a stack argument, and three `$a0`
  values come from signed `lh` loads;
- all 20 outcomes agree with an independently compiled minimal C
  implementation. There are no scores and no convention-to-proof relabels.

### Per-site outcomes (the fixed pilot universe)

| stratum | site ID | result | named wall | breaking instruction / OPEN witness |
|---|---|---|---|---|
| stack-entry | `LEVEL02_LEVEL1:0x800B3F14:sp` | ABSENT | `open_caller_set_poison` | `MEMORY:0x800B970C` |
| stack-entry | `LEVEL02_LEVEL1:0x800B43AC:sp` | ABSENT | `open_caller_set_poison` | `MEMORY:0x800B970C` |
| stack-entry | `LEVEL05_LEVEL:0x800B4040:sp` | ABSENT | `open_caller_set_poison` | `LEVEL05_LEVEL:0x800B4228` |
| stack-entry | `LEVEL05_LEVEL:0x800B4048:sp` | ABSENT | `open_caller_set_poison` | `LEVEL05_LEVEL:0x800B4228` |
| stack-entry | `LEVEL08_LEVEL1:0x800B416C:sp` | ABSENT | `open_caller_set_poison` | `MEMORY:0x800B970C` |
| return-domain | `LEVEL03_LEVEL1:0x800B41AC:v1` | ABSENT | `delay_slot_pre_call_value_not_return_domain` | `0x800B41A8` / `0x0C013043` |
| return-domain | `LEVEL05_LEVEL1:0x800B494C:s0` | ABSENT | `return_value_depends_on_unproved_s0_after_fallthrough_entry` | `0x8005A2F0` / `0x02001021` |
| return-domain | `LEVEL07_LEVEL:0x800B4774:a3` | ABSENT | `delay_slot_pre_call_value_not_return_domain` | `0x800B4770` / `0x0C013043` |
| return-domain | `LEVEL08_LEVEL:0x800B4284:s0` | ABSENT | `return_value_depends_on_unproved_s0_after_fallthrough_entry` | `0x8005A2F0` / `0x02001021` |
| return-domain | `LEVEL09_LEVEL:0x800B4640:s0` | ABSENT | `return_value_depends_on_unproved_s0_after_fallthrough_entry` | `0x8005A2F0` / `0x02001021` |
| argument-carrier index | `LEVEL02_LEVEL:0x800B4788:a0` | ABSENT | `local_definition_replaces_argument_register` | `0x800B4734` / `0x00042080` |
| argument-carrier index | `LEVEL04_LEVEL1:0x800B4AA8:v1` | ABSENT | `local_frame_slot_not_stack_argument` | load `0x800B4A8C` / `0x8FA90060`; frame adjustment `0x800B3C78` / `0x27BDFF70` |
| argument-carrier index | `MEMORY:0x800B7EA4:at` | ABSENT | `local_signed_load_not_caller_argument` | `0x800B7E68` / `0x8484245C` |
| argument-carrier index | `MEMORY:0x800B7F04:at` | ABSENT | `local_signed_load_not_caller_argument` | `0x800B7EC8` / `0x8484245C` |
| argument-carrier index | `MEMORY:0x800B7F64:at` | ABSENT | `local_signed_load_not_caller_argument` | `0x800B7F28` / `0x8484245C` |
| argument-carrier index | `SCUS_942_88:0x8005C5B4:s2` | ABSENT | `open_caller_set_poison` | `LEVEL03_LEVEL:0x800B4B38` |
| argument-carrier index | `SCUS_942_88:0x8005C5C0:s2` | ABSENT | `open_caller_set_poison` | `LEVEL03_LEVEL:0x800B4B38` |
| argument-carrier index | `SCUS_942_88:0x8005C5C8:s2` | ABSENT | `open_caller_set_poison` | `LEVEL03_LEVEL:0x800B4B38` |
| argument-carrier index | `SCUS_942_88:0x8005C5D4:s2` | ABSENT | `open_caller_set_poison` | `LEVEL03_LEVEL:0x800B4B38` |
| argument-carrier index | `SCUS_942_88:0x8005C5E8:s2` | ABSENT | `open_caller_set_poison` | `LEVEL03_LEVEL:0x800B4B38` |

**PILOT DECISION: NO-GO.** The proved/decided set is exactly `{}` and the
absent set is exactly the 20 rows in the table. Because fewer than three sites
were decided, the prime rule forbids the full Stage-A caller census, Stage-B
fixpoint, and Stage-C regeneration in this increment. No old pin was replaced.

### Named universes, controls, and movement

The sample-scoped C census covered 21 resident images, 1,191 census functions,
492 already-proved indirect edges, 36 proved table ranges, and 261 unproved
indirect edges. Its four distinct closure roots are all OPEN. The exact OPEN
site set is the five stack-entry rows plus the five `SCUS_942_88` rows in the
table. The other ten rows retain their more precise local/temporal walls.

The 50-capsule manifest passed its completeness and independent-control pins.
Because the decided-site universe is empty, there are zero site-time
observations and the comparison is recorded as
`NOT_APPLICABLE_NO_DECIDED_DOMAINS`, **not** as a clean GO cross-check. No live
or instrumented replay was performed.

Movements against the old pins are exact empty sets in both directions:
fixture gained/lost `{}`/`{}`, ledger gained/lost `{}`/`{}`, and 102-row
campaign gained/lost `{}`/`{}`. The campaign tally therefore remains 52 index
instruction, 26 writer-universe, nine return-domain, eight no-recovery, five
stack-entry, one external-entry, and one progression wall. The fixture remains
68/238 decided and the corpus remains 5,012 undecided; these are unchanged
reference counts, not newly regenerated Stage-C claims.

The authoritative receipt is
`analysis/phase4_caller_domain_pilot.json` (SHA-256
`b31b7493ca47e990b2ba0760eade1ed3c41ce1e688d41d6101d6794455265f89`).
The driver compiles both C implementations under `-Werror`; primary self-test
4/4, independent self-test 3/3, and all 20 site classifications agree. The
reproducible checks are:

```text
python3 tools/phase4_caller_domain.py --check
pytest -q tests/test_phase4_caller_domain.py tests/test_region_provenance_bound_soundness.py
```

The focused result was 14 passing tests. A broader affected-consumer run first
found two typed-state freshness failures: extending `region_provenance.c` had
changed a pinned dependency hash even though its semantic site sets were
identical. Regenerating that full-corpus artifact would have violated the
NO-GO stop. The repair moved the sample-only machinery to
`tools/phase4_caller_domain_probe.c` and restored `region_provenance.c`
byte-for-byte to SHA-256 `5f3bf4bb…`; the resulting affected suite is 97/97.
This is an integration repair, not Stage B or Stage C. The full detached
verification and fresh Hard-Truth receipt are recorded separately after their
candidate commit, so this result section does not claim acceptance in advance.

The first detached attempt then caught a second integration defect: the driver
had read ambient operator WIP from `analysis/`, making its receipt stale in a
clean checkout. All derived inputs are now loaded from the committed
pre-outcome snapshot `de8b10512c69`; current probe/driver source remains
independently hash-pinned. The suite including the extent-audit controls is
106/106. This pinning repair changed only receipt identities, not any of the 20
outcomes or exact movement sets.

### Status and next increment

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. No row, binding, or
dimension moved, and no Canon fact is warranted by a zero-proof pilot.

The single highest-leverage next increment is the work this pilot measured:
prove the unresolved indirect-table and address-taken universes before paying
for interprocedural propagation. Only after those universes close should the
same fixed pilot be re-run; the whitelist and fail-closed rules stay unchanged.

## 2026-08-07 — caller-domain NO-GO detached reproduction

A fresh detached worktree at candidate
`deaa8455513ba273524e64e5c348df965987fa95` received a real copy of
`REBUILD/files` with the self-referential source symlink excluded. `find`
reported zero symlinks in the copied input tree; `build_identity.py --verify`
reported 327/327 pristine inputs matching their pins. The detached commands
were:

```text
python3 tools/build_identity.py --verify
python3 tools/phase4_caller_domain.py --check
python3 tools/phase4_extent_audit.py --json analysis/phase4_extent_audit.json
pytest -q tests/test_phase4_caller_domain.py \
  tests/test_region_provenance_bound_soundness.py \
  tests/test_phase4_f01_local_base_recovery.py \
  tests/test_phase4_typed_state.py \
  tests/test_phase4_f01_static_hard_truth.py \
  tests/test_phase4_extent_audit.py
git status --short
```

Result: 106/106 tests pass and detached status is empty. The regenerated pilot
receipt is byte-identical at SHA-256
`b31b7493ca47e990b2ba0760eade1ed3c41ce1e688d41d6101d6794455265f89`.
The post-commit extent audit is byte-identical at SHA-256
`895f1f4895b03354491ad73dd5d696a2450b409db31365e9fa1cec9e6a980004`:
1,063 tracked files, 2,149 extent declarations, 18 reviewed truncations, and
zero new truncations.

This clean reproduction authorizes a fresh external review; it does not itself
bank F01 or replace the required Hard-Truth verdict.

## 2026-08-07 — caller-domain pilot Hard-Truth acceptance

A fresh detached Hard-Truth verifier audited exact candidate
`7efef21d1cae3eaa70377c88baf7d1da43f3c926` and returned exactly
`decision="agreed"`, `banking_authorized=true`, and `gaps=[]`. This banks the
mandatory pilot as a reviewed negative; it does not turn its NO-GO into a GO.

External acceptance identities are:

- prompt:
  `16add6e03ac0f3a714f159230089995da5a5a4ab50194d7c162c622dccd23214`;
- schema:
  `477330560752092581e5cfd569e5b468decee14c8ce3ab5eafb0a70298bb7bcc`;
- full verifier log:
  `56c7ca05ac9f7695ffe5184d11a7b53a466a92dffad0c73b58246378e74f20d5`;
- terminal verdict:
  `72114bd3f42e01ef7c5f2bffdff5c8ff08fb8b175f2317f8f84329e137210cb9`.

The verifier independently reconstructed the 5/5/10 sample from the
pre-outcome Git object, confirmed all 20 IDs occur exactly once in the pinned
102-row campaign, checked the commit ordering and baseline ancestry, inspected
the raw MIPS classifications, and reproduced the exact 0/20 outcome and
10/2/3/1/1/3 wall partition. It confirmed OPEN is exactly 10 and the operative
NO-GO reason is `decided_site_count_below_3`; the empty capsule comparison is
not called clean.

It also rebuilt both C implementations with `-Werror`, passed their 4/4 and
3/3 controls, reproduced the pilot and extent receipts byte-for-byte, passed
327/327 pristine input identities with zero symlinks, and passed the affected
106-test suite in a second clean detached checkout. Both verifier checkouts
finished clean. The verifier confirmed the full Stage-A/B/C pass did not run,
movement sets are empty, protected surfaces did not move, and the shared
`region_provenance.c` identity is restored exactly.

The accepted conclusion is therefore narrow and actionable: this caller-domain
route decides nothing in the fixed sample until the indirect-table and
address-taken universes improve. F01 remains `partial`, item 2 remains
`not_met`, both review booleans remain false, and its blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`.

## 2026-08-07 — address-taken universe pilot frozen (PRE-OUTCOME record)

This is the mandatory ordering checkpoint for
`engineering-specs/phase4-address-taken-universe-work-order.md` (SHA-256
`4e06dcdf94b15cb651af01d1dfdd0386c9e5b77ad82a0a9a96262abc8d87113e`).
It was written while HEAD was
`5b78caa2ad624584d123ecad2939f60fbc53ef1c`; the issued baseline
`f8d41264ff865b86a676e2fac536a80c474c4264` is an ancestor.

The target universe is copied verbatim from the accepted caller-domain pilot
receipt at SHA-256
`b31b7493ca47e990b2ba0760eade1ed3c41ce1e688d41d6101d6794455265f89`.
It is four concrete closure roots and their machine-recorded openness witness
occurrences—not a survey and not a result-selected sample:

| closure root | fixed openness witness occurrence |
|---|---|
| `LEVEL02_LEVEL1:0x800B3F08` | data word `MEMORY:0x800B970C` |
| `LEVEL08_LEVEL1:0x800B4084` | data word `MEMORY:0x800B970C` |
| `LEVEL05_LEVEL:0x800B3D80` | data word `LEVEL05_LEVEL:0x800B4228` |
| `SCUS_942_88:0x8005C58C` | data word `LEVEL03_LEVEL:0x800B4B38` |

Cardinality at freeze time: four unique image-qualified roots, three unique
witness cells, four root-to-witness occurrence pairs. The duplicated
`MEMORY:0x800B970C` cell is retained twice because the proof obligation is per
target occurrence; shared handlers/targets never collapse occurrence counts.
The last row is deliberately cross-image: LEVEL03 overlay data contains a
resident-function entry.

**No address-taken sweep, consumer enumeration, index/selection-domain proof,
region-extent proof, capsule comparison, CLOSED/OPEN result, recursion depth,
or GO/NO-GO decision had been produced when this section was committed.** The
pilot is limited to these roots, cells, and any region each cell is proved to
belong to. A result is valid only in a descendant commit after this freeze.

## 2026-08-07 — address-taken universe pilot result: witness premise falsified, NO-GO

The four-target list above remained unchanged. Two independent C sweeps then
established a correctness finding before attempting closure: the accepted
caller-domain receipt did **not** record address-taken occurrences in these
fields. It recorded the first member of each root's
`relevant_unproved_indirect_edges` array, while the same receipt reported zero
address-taken occurrences for all four roots. The work order's “data word where
the entry escapes” interpretation therefore does not follow from its source.

The raw, range-qualified witness results are:

| root | fixed witness | machine result |
|---|---|---|
| `LEVEL02_LEVEL1:0x800B3F08` | `MEMORY:0x800B970C` / `0x00400008` | code-range `jr v0`, not a data word and not the root entry |
| `LEVEL08_LEVEL1:0x800B4084` | `MEMORY:0x800B970C` / `0x00400008` | same code-range dispatch, not a data word and not the root entry |
| `LEVEL05_LEVEL:0x800B3D80` | `LEVEL05_LEVEL:0x800B4228` / `0x006B0008` | data range `0x800B410C..0x800B4300`; word is not `0x800B3D80`; it is not decoded as an instruction |
| `SCUS_942_88:0x8005C58C` | `LEVEL03_LEVEL:0x800B4B38` / `0x0008CD09` | data range `0x800B4A0C..0x800B4C18`; word is not `0x8005C58C`; it is not decoded as an instruction |

That range-type correction removes exact data-decoded supersets from the old
unproved-indirect lists. Movement is old → corrected code-only: 255 → 178 for
each MEMORY-witness overlay root, 258 → 178 for LEVEL05, and 261 → 179 for the
resident root. The exact removed/added/unchanged ID sets are stored in
`corrected_indirect_universe_movement`; additions are `{}` for every root.
Their removed sets contain exactly 77 / 77 / 80 / 82 IDs, and every removed PC
belongs solely to a pinned `range_type=data` record. The receipt preserves each
full set rather than substituting these counts.

### What the real MEMORY instructions prove

`MEMORY:0x800B970C` is useful, but for a different reason than the order
asserted. The primary C probe proves the local address domain from instructions:

```text
0x800B96EC  sltiu  v0,a0,8       -> guarded a0 in [0,7]
0x800B96F0  beq     v0,zero,0x800B97E8
0x800B96F8  sll     v0,a0,2      -> four-byte stride
0x800B96FC  lui     at,0x800B
0x800B9700  addu    at,at,v0
0x800B9704  lw      v0,0x57B4(at)
0x800B970C  jr      v0
```

The exact selected image extent is `0x800B57B4..0x800B57D4`, eight slot
occurrences with eight distinct values. The load is after the guard; the
hoisted-load negative control rejects a pre-guard load. Slot occurrences are
counted even when targets repeat, per the mover-VM rule. This is deliberately
classified `PROVED_LOCAL_ADDRESS_DOMAIN`, not a gate target-set proof: the
computed reader/writer universe for the region remains unexhausted. No wanted
root is promoted on static slot contents alone.

The independent Stage-A C implementation exactly matches the primary sweep on
every occurrence tuple. Across the 21 pinned images the first three root entries
have zero aligned literal or `lui/addiu` / `lui/ori` occurrences. The resident
entry has exactly one occurrence: slot `SCUS_942_88:0x8001B854` in the already
proved table `0x8001B848..0x8001B87C`. The receipt records both directions:
per-function occurrence IDs and per-data-region member IDs. Primary self-tests
are 10/10, including exact `lui/addiu`, signed-`addiu`, shift-field,
hoisted-load, and duplicate-slot controls; independent
self-tests are 4/4.

### Mandatory pilot decision

| root | CLOSED? | recursion depth reached | corrected gate-grade residual | wall |
|---|---:|---:|---:|---|
| `LEVEL02_LEVEL1:0x800B3F08` | no | 1 | 178 sites | `per_site_indirect_target_domain_universe_incomplete` |
| `LEVEL08_LEVEL1:0x800B4084` | no | 1 | 178 sites | `per_site_indirect_target_domain_universe_incomplete` |
| `LEVEL05_LEVEL:0x800B3D80` | no | 0 | 178 sites | fixed-witness membership premise falsified, plus the same target-domain wall |
| `SCUS_942_88:0x8005C58C` | no | 0 | 179 sites | fixed-witness membership premise falsified, plus the same target-domain wall |

**PILOT DECISION: NO-GO, 0/4 roots CLOSED.** The threshold was two. The full
corpus Stage A/B/C pass is forbidden, the frozen caller-domain 20 are not
re-run, and no old pin is replaced. The 50 retained capsule identities and
controls validate, but with no closed root their comparison is
`NOT_APPLICABLE_NO_CLOSED_ROOTS`, never a clean result by vacuity. No live or
instrumented run was performed.

The required replacement argument is: **replace the proposed witness-cell
closure argument with a complete per-site target-domain/exclusion proof over
the corrected code-only `jr`/`jalr` universe, using whole-table value-domain
invariants for table-backed sites.** This is the argument with final authority
over the caller-closure wall; recursively chasing the three fixed addresses
cannot supply it.

The deterministic receipt is
`analysis/phase4_address_taken_pilot.json` (SHA-256
`0a3d1cc19ca52d44da215d68b522c628b66428e2c08bd7123e219f7cec34782a`).
Reproduction commands are:

```text
python3 tools/phase4_address_taken_pilot.py --check
pytest -q tests/test_phase4_address_taken_pilot.py
```

The focused result is 10/10. C source identities are primary
`146fe118a8690a4daf0ceca4c3da50f5bab336a382309bdaa1f9a8187d3c6633`
and independent
`9ef8906a1190255b419a0fd208af9b0fad859eb543ce5a53e837bf0b7751d0dd`;
both rebuild under `-Werror`. This result is pre-acceptance until a clean
detached reproduction and fresh Hard-Truth verifier return exactly `agreed`.

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. Fixture, ledger, and
campaign movement sets are `{}` in both directions. The mechanics baseline,
accepted caller receipt, Phase-3 jr/gate artifacts, registry, and Canon are
unchanged.

## 2026-08-07 — address-taken NO-GO detached reproduction

A fresh detached worktree at candidate
`5bca21161e969a0ec29c0d22c8bc9fdb4b9658ee` received exactly 327 regular
files copied from `REBUILD/files`; the self-referential/source symlink class
was excluded and `find` reported zero destination symlinks. The counted run
verified its own `pwd`/HEAD before executing; no operator-checkout result was
used as detached evidence.

```text
python3 tools/build_identity.py --verify
python3 tools/phase4_address_taken_pilot.py --check
python3 tools/phase4_extent_audit.py --json analysis/phase4_extent_audit.json
pytest -q tests/test_phase4_address_taken_pilot.py \
  tests/test_phase4_caller_domain.py \
  tests/test_region_provenance_bound_soundness.py \
  tests/test_phase4_f01_local_base_recovery.py \
  tests/test_phase4_typed_state.py \
  tests/test_phase4_f01_static_hard_truth.py \
  tests/test_phase4_extent_audit.py
git status --short
```

Result: 327/327 pristine identities pass, the pilot regenerates byte-identical
at SHA-256
`c5e281867598f9fffa0956aa99d747be3146d20ae2137fd3aadfbd47e18c6bb3`,
and the affected suite passes 116/116. The post-commit extent audit is
byte-identical at SHA-256
`8b3ff7b2db51bb1fd7602de5e153d903b92ff311702889a365c7870c32673da7`:
1,066 files, 2,149 extent declarations, 18 reviewed truncations, and zero new
truncations. Detached `git status --short` is empty.

This clean reproduction authorizes a fresh external Hard-Truth review. It does
not accept the NO-GO in advance, move F01, or authorize the stopped full pass.

### Exact-control tightening and superseding detached reproduction

Before sending the candidate to external review, an internal control audit
found that the primary `lui/addiu` self-test asserted only a nonzero result.
Commit `fdcfb5aa2e30c1244566980974bbb36061089f11` replaces that weak assertion
with the exact reconstructed entry, pins the `sll` source/destination fields,
and adds a sign-extended negative-low-half `addiu` case. Primary controls are
now 10/10. No Stage-A occurrence, witness classification, interval, corrected
edge set, root outcome, decision, or protected surface changed.

A second fresh detached tree at that exact commit copied 327 regular pristine
inputs, contained zero symlinks, passed 327/327 identity pins, regenerated the
current pilot byte-identically at SHA-256
`0a3d1cc19ca52d44da215d68b522c628b66428e2c08bd7123e219f7cec34782a`,
and passed the same affected 116/116 tests. The post-commit extent audit remains
byte-identical at SHA-256
`8b3ff7b2db51bb1fd7602de5e153d903b92ff311702889a365c7870c32673da7`
with zero new truncations. Detached status is empty. This supersedes the first
candidate for Hard-Truth review; it remains pre-acceptance.

## 2026-08-07 — address-taken universe pilot Hard-Truth acceptance

A fresh detached Hard-Truth verifier audited exact candidate
`d7bb785e4c0dd4950a6dcf7f736b1bb15763b74b` and returned exactly `agreed`,
`banking_authorized=true`, and `gaps=[]`. The verifier checkout remained at
that exact commit with empty status after independently checking the frozen
four-root history, C-owned and source-independent sweeps, raw witness bytes,
guarded MEMORY derivation, full movement sets, protected surfaces, 327/327
input identities, byte-identical pilot and extent receipts, and the 116-test
affected suite.

The external prompt / schema / log / verdict SHA-256 identities are:

```text
prompt   36f57e49b7465cccd096f5729c108ecb2e257c0aa64c44e9461b47d04b79e972
schema   c248873a4cd14c78db0ba6f365e226f41903c74e6c1594b85d4c8bb0febd6a43
log      936f45d2b94664a71ed2c0de7dc00818efeb68138eb7256d431e74762f7f0908
verdict  555a7a8816481da1cee88a35e00ae47318afce423992db4025a7103ab146f55c
```

This banks the pilot as the required reviewed **NO-GO**, not as a closure or
promotion: 0/4 roots are CLOSED, no full Stage A/B/C pass or caller-domain
frozen-20 rerun is authorized, and no pins move. The next mechanical argument
remains the complete per-site target-domain/exclusion proof over the corrected
code-only `jr`/`jalr` universe, with whole-table value-domain invariants for
table-backed sites. F01 remains `partial`, item 2 remains `not_met`, both
review booleans remain false, and blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`.

## 2026-08-07 — target-exclusion pilot frozen (PRE-OUTCOME record)

This is the mandatory Stage-0/1 barrier for
`engineering-specs/phase4-target-exclusion-work-order.md`. Its immutable input
snapshot is work-order commit
`d4c60047fb2d1419f7691f6e2b6a628eea2fdb42`; accepted baseline
`2a617486b30fce115933900e307c233ddb121f56` and witness-semantics erratum
`7658e79f674d18102e3f25f6b3dd7eb5989d331a` are both ancestors. The
authoritative predecessor field is the receipt's corrected
`relevant_unproved_indirect_edges` superset, not the false witness-cell reading
retracted in the preceding experiment.

Stage 0 reconstructs the exact union as `image:pc:kind:register`. Before the
code/data correction the four supersets union to 261 IDs. The corrected
code-only unproved union is exactly **179** IDs: SCUS 166, MEMORY 12, and
LEVEL07 1. Exactly 82 IDs are out, each for the named reason
`pinned_data_record_false_decode`; all 82 PCs lie solely in a pinned data
record. Masking adds zero IDs. The artifact retains the complete in-set, all
82 out-set records with their containing data extents and affected roots, and
the per-root before/after exact sets.

The C-owned reaching-definition classification covers all 179 sites. The
frozen stratum histogram is: `table_backed` = **74**; `computed` = **19**;
`register_provenance` = **6**; `return_like` = **0**;
`return_like_unproved_incoming_ra` = **9**;
`unclassified_opaque_definition` = **38**; and
`mixed_reaching_definitions` = **33**. `return_like` is deliberately zero:
the machine can show incoming `ra` reaches nine sites, but the still-OPEN
entry/caller universe cannot prove that every such value is a call link.
Calling those returns would turn the convention back into proof. Each site
records the transfer word and delay-slot word from the image, its exact owner
extent, every C-classified reaching definition and instruction word, and the
classification basis. `table_backed` means only a Stage-2 invariant candidate;
it is not a whole-table-state proof.

The outcome-blind selection query is: take every corrected-union site present
in one or more root's corrected unresolved-edge superset (an exclusion closes
that site-to-root obligation, not the other root obligations); union the SCUS
sites whose pinned direct/proved-edge reachable cone contains a
`KNOWN_WRITERS` owner; sort by numeric PC then image/ID; truncate to 12. The
first arm contains 179 sites. The conservative reachable-cone arm contains
zero additional sites. Therefore the frozen pilot is:

| rank | frozen site | Stage-1 stratum only |
|---:|---|---|
| 1 | `SCUS_942_88:0x80011128:jr:ra` | `return_like_unproved_incoming_ra` |
| 2 | `SCUS_942_88:0x800163d8:jr:ra` | `register_provenance` |
| 3 | `SCUS_942_88:0x800172d4:jr:ra` | `register_provenance` |
| 4 | `SCUS_942_88:0x8001897c:jr:ra` | `return_like_unproved_incoming_ra` |
| 5 | `SCUS_942_88:0x80018a4c:jr:s6` | `computed` |
| 6 | `SCUS_942_88:0x80018b1c:jr:s6` | `computed` |
| 7 | `SCUS_942_88:0x80018bec:jr:s6` | `computed` |
| 8 | `SCUS_942_88:0x80018cbc:jr:s6` | `computed` |
| 9 | `SCUS_942_88:0x80018f44:jr:ra` | `return_like_unproved_incoming_ra` |
| 10 | `SCUS_942_88:0x8001923c:jr:ra` | `return_like_unproved_incoming_ra` |
| 11 | `SCUS_942_88:0x80019614:jr:ra` | `return_like_unproved_incoming_ra` |
| 12 | `SCUS_942_88:0x80019b3c:jr:ra` | `return_like_unproved_incoming_ra` |

**No Stage-2 target-domain proof and No exclusion/disjointness outcome existed
when this list was frozen. No GO/NO-GO decision existed, and neither did a
runtime cross-check result.** No F01 status, blocker, review boolean, gate universe, or
baseline moves in this barrier. A valid outcome must be produced and committed
strictly after this record.

## 2026-08-07 — target-exclusion pilot result: four exact domains, mandatory NO-GO

The outcome pass consumed the exact 12-site list committed at freeze
`2e67ac74498c96989a858e08918983aaf5bdf73a`; it did not reorder, replace, or
extend the sample. The standalone C analyser
`tools/phase4_target_exclusion_prover.c` accepts
`IMAGE:START:END:REG:PC`: every entry-reachable definition of the named
transfer register must be an exact constant construction, every path to the
transfer must cross one, and every definition occurrence remains in the
derivation even when target values repeat. Loads, incoming values, call
crossings, unsupported operations, and evaluator disagreements fail at the
exact instruction. Its positive/negative controls pass 5/5. The accepted
shared typed-state analyser remains byte-identical to the pre-outcome freeze.

### Correctness finding: dead lexical bytes are not a target

The first pass exposed one overcount that the Stage-1 classifier could not
settle: lexical `ori s6,s6,0x961C` at `0x800188EC` spells target
`0x8001961C`, but the definition itself is not reachable from declared entry
`0x80018850`. It sits after the `j 0x8001897C` path whose delay slot is at
`0x800188E4`. A forward definition-to-use test alone had called the dead word
observable. The exact-domain prover now requires both directions—entry reaches
definition and definition reaches use—and records the excluded occurrence and
word rather than silently dropping it. The independent forward finite-set C
implementation reaches the same three-value domain without ever adding the
dead value.

### Frozen pilot outcomes

| frozen site | outcome | exact target set or named wall |
|---|---|---|
| `SCUS_942_88:0x80011128:jr:ra` | not landed | `0x80011128 / 0x03E00008`: `query_site_not_entry_reachable` |
| `SCUS_942_88:0x800163d8:jr:ra` | not landed | `0x80015544 / 0x02C0F820`: `ra <- s6 <- incoming ra`; source constant is not path-complete |
| `SCUS_942_88:0x800172d4:jr:ra` | not landed | `0x80016554 / 0x02C0F820`: `ra <- s6 <- incoming ra`; source constant is not path-complete |
| `SCUS_942_88:0x8001897c:jr:ra` | not landed | `0x8001897C / 0x03E00008`: entry path carries unproved `ra` |
| `SCUS_942_88:0x80018a4c:jr:s6` | **full target domain** | `{0x80018CC4, 0x80018F4C, 0x80019244}` |
| `SCUS_942_88:0x80018b1c:jr:s6` | **full target domain** | `{0x80018CC4, 0x80018F4C, 0x80019244}` |
| `SCUS_942_88:0x80018bec:jr:s6` | **full target domain** | `{0x80018CC4, 0x80018F4C, 0x80019244}` |
| `SCUS_942_88:0x80018cbc:jr:s6` | **full target domain** | `{0x80018CC4, 0x80018F4C, 0x80019244}`; dead `0x800188EC` definition excluded |
| `SCUS_942_88:0x80018f44:jr:ra` | not landed | `0x80018F44 / 0x03E00008`: entry path carries unproved `ra` |
| `SCUS_942_88:0x8001923c:jr:ra` | not landed | `0x8001923C / 0x03E00008`: entry path carries unproved `ra` |
| `SCUS_942_88:0x80019614:jr:ra` | not landed | `0x80019614 / 0x03E00008`: entry path carries unproved `ra` |
| `SCUS_942_88:0x80019b3c:jr:ra` | not landed | `0x80019B3C / 0x03E00008`: entry path carries unproved `ra` |

All three targets are image-byte-verified censused function entries and are
disjoint from the exact 128-member protected set (58 known writers, all 124
window sites with the writers as a subset, and four roots). A second C program
using an independent forward finite-set fixpoint matches all 12 Stage-1
classifications and all four exact domains. Its controls are 4/4. The result
therefore lands four proof artifacts, representing 12 site→target edge
occurrences. Because this is a NO-GO pilot, those additions remain staged and
the existing gate/index stays exactly 87 sites / 492 edges.

The runtime clause cannot pass. All 50 retained frame-boundary capsules remain
identity/control-clean but contain zero site-time indirect-target records. The
preserved u3 entry watches contain zero source-site/target tuples: they record
entry hits of 0 / 60 / 60 / 60 for `0x80018CC4`, `0x80018F4C`,
`0x80019244`, and `0x8001961C`, respectively, but do not identify which
indirect transfer supplied the entry. Zero comparable tuples is unavailable
evidence, not a vacuous clean comparison. No live or instrumented replay was
performed.

### Mandatory decision and full NO-GO price

**PILOT DECISION: NO-GO.** The landed-count clause passes exactly 4/12 and no
soundness violation was observed. The other two mandatory GO clauses fail:
the mechanically frozen pilot contains zero `table_backed` sites, so it cannot
land a whole-table value-domain invariant, and retained evidence cannot supply
a clean site-time runtime comparison. The full pass, gate/index update,
closure-census cascade, frozen caller-domain-20 rerun, typed-state regeneration,
campaign regeneration, and pin movement are forbidden.

The full 179-site histogram remains: table-backed 74; computed 19;
register-provenance 6; proved return-like 0; incoming-`ra` return-like but
unproved 9; opaque-definition 38; mixed-definition 33. After the four exact
computed proofs, the unproved remainder is exactly 175: table-backed 74;
computed 15; register-provenance 6; proved return-like 0; incoming-`ra` 9;
opaque 38; mixed 33. Eight are attempted walls and 167 are unattempted because
the pilot gate stops the pass. There are no table-writer recursion cycles in
the attempted set because the frozen pilot contains no table site.

The item-2 bar would have to accept exclusion for 175 corrected code-only
indirect sites that this increment does not prove: eight attempted pilot sites
with named walls and 167 sites stopped by the mandatory pilot gate. Those 175
include all 74 table/cell-backed candidates without a complete whole-table
runtime-state invariant and 101 sites in the computed, register, incoming-ra,
opaque, or mixed strata. The retained 50 frame-boundary capsules and preserved
u3 entry watches contain zero source-site/indirect-target tuples for those
sites. The u3 watches record entry hits of 0, 60, 60, and 60 at `0x80018CC4`,
`0x80018F4C`, `0x80019244`, and the dead-lexical `0x8001961C` value,
respectively; those hits do not identify which indirect site supplied the
target and therefore do not prove exclusion. This paragraph states the price;
it makes no recommendation to lower the bar.

The deterministic receipt is `analysis/phase4_target_exclusion_pilot.json`
(SHA-256 `054dd93dba07626365d37cc7426c63d137cf2debb62a8ada61c2fe4fb5b127d3`).
Primary / independent C source SHA-256 identities are
`76ac66d4adcc9c113d3dfe336a09d4204fdb82a881d1016b3faa1bbe8e275797` /
`b833d4e2c875b9ad84aff2a52d44ffd5daebbfc1e56e3b1f0be56147950acb8d`.
Reproduce with:

```text
python3 tools/phase4_target_exclusion_freeze.py --check
python3 tools/phase4_target_exclusion_pilot.py --check
pytest -q tests/test_phase4_target_exclusion_freeze.py \
  tests/test_phase4_target_exclusion_pilot.py
```

F01 remains `partial`; item 2 remains `not_met`; both review booleans remain
false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. Mechanics baseline,
registry, gate receipt, writer-universe gate, value-domain gate, and Canon are
unchanged. This is a pre-acceptance candidate until clean detached reproduction
and a fresh Hard-Truth verdict return exactly `agreed`.

## 2026-08-07 — target-exclusion NO-GO detached reproduction

A fresh detached worktree at candidate
`78753468cda024cbbdffac2239df4f59de179f56` received exactly 327 regular
files copied from `REBUILD/files`; the self-referential source symlink was
excluded and the detached input tree contained zero symlinks. The run checked
its own path and HEAD before using any result. Its commands were:

```text
python3 tools/build_identity.py --verify
python3 tools/phase4_target_exclusion_freeze.py --check
python3 tools/phase4_target_exclusion_pilot.py --check
python3 tools/phase4_extent_audit.py --json analysis/phase4_extent_audit.json
pytest -q tests/test_phase4_target_exclusion_freeze.py \
  tests/test_phase4_target_exclusion_pilot.py \
  tests/test_phase4_address_taken_pilot.py \
  tests/test_phase4_caller_domain.py \
  tests/test_region_provenance_bound_soundness.py \
  tests/test_phase4_f01_local_base_recovery.py \
  tests/test_phase4_typed_state.py \
  tests/test_phase4_f01_static_hard_truth.py \
  tests/test_phase4_extent_audit.py
git diff --exit-code 2e67ac74498c96989a858e08918983aaf5bdf73a \
  -- tools/phase4_typed_state_provenance.c
git status --short
```

Result: pristine input identity passes 327/327 and the affected suite passes
135/135. The pre-outcome freeze and outcome receipt regenerate byte-identically
at SHA-256
`8b6cb83f9d2b95b099606f87e3b0f76b8520e391bdebfc5629f0bf45e1864ad2`
and
`054dd93dba07626365d37cc7426c63d137cf2debb62a8ada61c2fe4fb5b127d3`.
The post-commit extent receipt is byte-identical at SHA-256
`2eaa9fbcf493137b7e4bc14812e56fee63734a43ecddd96a88124740b7bd9899`:
1,071 files, 2,149 extent declarations, 18/18 acknowledged truncations, and
zero new truncations. The accepted shared typed-state C source remains exactly
SHA-256
`503a4e2178bc52e15f887e80b42b6111ca64f94728199aae654e4223f4d4803b`.
Detached status is empty.

This clean reproduction authorizes a fresh external Hard-Truth review. It does
not accept the NO-GO in advance, authorize the stopped full pass, apply the
staged four-site/twelve-edge movement, or move F01.

## 2026-08-07 — target-exclusion Hard-Truth retraction and gate-grade repair

The first external attempt emitted no terminal verdict after exhausting its
context on an unrelated broad repository search. The bounded second verifier
audited exact candidate `2c74b03cd7d83363dc459c694da8986a4b249015`
and returned `decision="unverified"`, `banking_authorized=false`. Its prompt /
schema / log / verdict SHA-256 identities are:

```text
prompt   16dc394e0715bc22883f213f99930453dc52cb6445842d80eb33e849bd0600c9
schema   e331ac11d9a5d0840113564a9cc8617d8b87ee16135246ca74057d5e67abfbe1
log      e63321fd0e48d3dce00c149e23d69b737064131433d52f70bd2292f57d539c9f
verdict  0f5b922d1f3cda645defda5cd123a492c1f628c0711e9da951dc4b7e5cc956ac
```

The verifier found a real shared CFG defect: both new C implementations sent
the not-taken edge of a branch-likely instruction through its delay slot.
That can make a delay-slot definition falsely dominate a use. The repair gives
likely branches two distinct edges—taken through the slot to the target,
not-taken directly to PC+8—and adds the contrasting ordinary-branch positive
and likely-annul negative controls to both implementations. It also models
coprocessor conditional branches and treats REGIMM conditional-link branches
as call crossings. Primary controls now pass 9/9 and the independent forward
controls pass 8/8.

### Retraction: four local domains are not four landed proofs

The hard-truth question about gate grade exposed a second overclaim in the
candidate receipt. The four `s6` domains are exact only for paths starting at
declared entry `0x80018850`. The work order requires a landed full domain to be
gate grade, and gate grade also requires exhaustive entry scope. The accepted
typed-state entry gate finds 156 unresolved transfer sources that can enter
the owner interior. The corrected convention-free work-order universe adds 19
more sites which that older gate omitted: 18 external sources and the internal
incoming-`ra` transfer at `0x8001897C`. After recognizing the four local exact
`s6` source domains, the unresolved entry-source set is exactly 175: 174
external and one internal, with zero concrete proved entries. Either class can
bypass the definitions that make the three-value local domains exact.

Therefore the earlier language “four landed proofs,” “four staged gate sites,”
and “175-site item-2 residual” is **retracted**. The corrected result is:

- four entry-scoped local proof bases, each still exactly
  `{0x80018CC4, 0x80018F4C, 0x80019244}` and disjoint from the protected set;
- zero gate-grade landed sites and zero candidate/applied gate edges;
- twelve attempted walls: eight instruction/domain walls plus four
  `blocked_external_interior_entry_universe` walls tied to the exact 175-source
  set;
- an exact item-2 residual of all 179 corrected sites, partitioned table 74,
  computed 19, register 6, proved-return 0, incoming-`ra` 9, opaque 38, mixed
  33; twelve were attempted and 167 stopped at the pilot gate;
- the accepted gate remains exactly 87 sites / 492 edges.

The strict pilot decision remains **NO-GO**, now directly satisfying the
`<=3` landed clause with 0/12. The zero-table and unavailable-runtime clauses
also remain false for GO. Capsules and u3 watches still supply zero
source-site/target tuples, so `clean_for_go=false`; no live replay occurred.
The corrected deterministic receipt is
`analysis/phase4_target_exclusion_pilot.json`, SHA-256
`ac37a3c9e918cd19d55dfc061d99b3ca223d57cf8c9d86d88a16a3edf500a43c`.
Primary / independent C source SHA-256 identities are
`844c9b924471cde25b3c6af396fff2aa406766637f21197869b5244f900ec195` /
`3fa202fc0827db9ffc8b2fbd432c6f1afff35b56de61fe43ba414fd343e86711`;
the outcome driver is
`15d5322532495c64740b5b6d3d2b12bb7ce4b5426bf571cc9d83e9ac766a5584`.

The prior detached reproduction is superseded because it reproduced the
retracted receipt. This repair remains pre-acceptance until a new clean
detached checkout reproduces the corrected artifact and a fresh Hard-Truth
verdict returns exactly `agreed`. F01 remains `partial`; item 2 remains
`not_met`; both review booleans remain false; blockers remain exactly
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. No gate, baseline,
registry, Canon, campaign, fixture/ledger, writer-universe, or value-domain
surface moved.

### Superseding detached reproduction after the gate-grade repair

A new detached worktree at exact repair candidate
`80adf9006cfb4158de6a3d3e933cca3e0e468cca` received 327 regular pristine
inputs and zero symlinks. It verified its own path and HEAD, passed 327/327
build identities, regenerated the freeze and corrected outcome byte-identically
at SHA-256
`8b6cb83f9d2b95b099606f87e3b0f76b8520e391bdebfc5629f0bf45e1864ad2`
and
`ac37a3c9e918cd19d55dfc061d99b3ca223d57cf8c9d86d88a16a3edf500a43c`,
and reproduced the post-commit extent receipt at
`2eaa9fbcf493137b7e4bc14812e56fee63734a43ecddd96a88124740b7bd9899`.
The extent result remains 1,071 files, 2,149 declarations, 18/18 reviewed
truncations, and zero new findings.

The same protected affected suite now passes 136/136, including the explicit
entry-scope exact-set test and the C branch-likely / conditional-link /
coprocessor-branch controls. The accepted shared typed-state C source still
matches the freeze exactly, and detached `git status --short` is empty. This
supersedes the 787534 detached record and authorizes a new external review; it
does not accept the repaired result in advance or move any protected surface.

## 2026-08-07 — target-exclusion strict NO-GO accepted

The fresh detached Hard-Truth verifier reviewed exact candidate
`e5d6ea71ac2fda59815cbc61a381486f7fa118a8` and returned exactly
`decision="agreed"`, `banking_authorized=true`, and `gaps=[]`. Its prompt /
schema / complete log / verdict SHA-256 identities are:

```text
prompt   5f98482e947eeefef10668eb2f827afba6cdc52d26ae54416a6043e0ffe8af1f
schema   e331ac11d9a5d0840113564a9cc8617d8b87ee16135246ca74057d5e67abfbe1
log      6f84d831c186f391b40c14fbda303ee47ca10b80c5622cad217cdae61cdc5fe8
verdict  d272bb82301dba50f02260437ec2f9d6d3f99492eb217e9e13c1f8db34fb0307
```

The verifier independently reproduced the pre-outcome freeze ordering and all
decisive exact sets in both directions: 261 pre-mask sites, 82 false data
decodes removed, zero additions, and 179 corrected sites (166 SCUS, 12 MEMORY,
one LEVEL07), partitioned 74 / 19 / 6 / 0 / 9 / 38 / 33. The protected union is
128 unique image/PC members from 58 writers, 124 window sites, and four closure
roots. Raw-image checks reproduced every stored site, delay-slot, definition,
target owner, and breaking instruction. Both independently implemented C
analyses passed their `-Werror` controls at 9/9 and 8/8.

All four local `s6` bases produce exactly
`{0x80018CC4, 0x80018F4C, 0x80019244}`, but none is gate grade. The accepted
entry gate independently yielded 156 unresolved helper sources and zero
concrete entries; the corrected work-order universe added 19 `jr ra` sources.
After excluding the four local bases, the exact wall remains 175 possible
interior-entry sources: 174 external and
`SCUS_942_88:0x8001897C:jr:ra` internal. The final pilot result is therefore
0/12 landed, twelve explicit walls, zero table recursion cycles, empty
candidate/applied gate movement, and the full 179-site residual. The accepted
gate remains 87 sites / 492 edges.

Fresh detached validation passed 327/327 pristine identities, copied 327
regular inputs with zero symlinks, regenerated the extent receipt at 1,071
files / 2,149 declarations / 18 reviewed / zero new, passed the affected suite
136/136, and ended with empty status. Runtime support remains unavailable rather
than vacuously clean: the 50 capsules and preserved u3 watches contain no
source-site/target tuples, so `clean_for_go=false`.

This acceptance banks the strict reviewed NO-GO only. It does not authorize a
full pass, caller-domain cascade, gate or baseline repin, Canon change, or row
promotion. No table invariant landed, so there is no Canon update. F01 remains
`partial`; item 2 remains `not_met`; both review booleans remain false; blockers
remain exactly `[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`.

## 2026-08-08 — runtime tuple capture at the 179 sites: 0 protected hits, and ONE static domain FALSIFIED

The evidence campaign the bar decision asked for, run by the assistant with
tools (no work order). Receipt: `analysis/phase4_f01_jr_tuple_capture.json`;
raws sha-pinned in `~/Downloads/ABL-external-evidence/phase4_jr_tuple_capture_2026-08-08/`.

Six passes (three 60-site slices × LEVEL01 + LEVEL07 any% movies — the
64-live-exec-watch core cap forbids one 179-watch pass), driven at 60 Hz on a
`launch_repro_playback.sh --execution-mode Interpreter` instance after a
desync investigation (below). Positive control fired and effective-mode audit
clean in all six.

### Results

- **52 of 179 sites observed; 135 distinct source→target tuples; ZERO land
  in the protected set** (58 KNOWN_WRITERS + 124 window sites + 4 closure
  roots). The non-falsification statement for the item-2 bar decision now
  has real numbers: two levels, ~50k dispatch observations, no protected
  intersection. 127 sites stayed silent in these runs — silence proves
  nothing (per-stratum coverage table in the receipt).
- ⚡⚡ **The exclusion pilot's "exact entry-scoped domain" for 0x80018CBC is
  FALSIFIED.** Runtime shows its jr $s6 dispatching to **0x8001961C
  (`gte_quad_clip_emit_variant_c`, a census entry)** as the DOMINANT target
  (7,657 hits in L01, 30,338 in L07, >80% of dispatches) — the address the
  pilot receipt called "dead-lexical". The pilot's primary implementation
  had honestly recorded a fourth derivation with unresolved value None; the
  independent implementation's dead-value kill was wrong, and its
  `full_target_domain_complete: true` for this site is false. The three
  sibling sites (0x80018A4C/B1C/BEC) held their proved domains with zero
  violations across both movies.
- Consequence for the bar: the 175-source interior-entry caution is now a
  DEMONSTRATED failure mode, not a hypothetical — a bar that accepted
  local-proof exclusions would have accepted a domain missing its majority
  member. Gate grade earned its keep by exhibit.

### The desync investigation (operator-caught, two stacked causes)

The operator watched replays desync that every flag called healthy
(`reproducible: true` throughout). Root causes, isolated by bisection
(unarmed-Recompiler clean → armed desync → unarmed-pinned-Interpreter clean):
1. The campaign's instance was started with the GENERIC debugger launcher,
   which rewrites `settings.ini` with **no [CPU] section** on every start —
   the core ran Recompiler while the movies are Interpreter-recorded. The
   repro wrapper's header explicitly forbids this use; the prepaid gotcha
   was not applied.
2. The exec-watch drain cycle (remove-all → re-add) let the live watch count
   hit zero mid-replay, FLAPPING the effective core Interpreter↔Recompiler
   between drains on the unpinned instance.
All captures from the tainted regime were discarded before re-running. New
pinned facts: `EXEC_WATCH_MAX_COUNT = 64`; `execTrace.clear` stops
collection (fresh addWatch resumes); `-32005` with null data on addWatch is
the watch cap, not the scenario gate.

## 2026-08-08 — FULL-CORPUS sweep: 16 levels, 48 sessions, still zero protected hits, still exactly one falsification

All sixteen any% Interpreter movies swept through the tuple harness (three
60-site slices each, 60 Hz pinned-Interpreter). Receipt section
`full_corpus_sweep` in `analysis/phase4_f01_jr_tuple_capture.json`; raws in
the external store (59 files, sha-pinned).

- **61 of 179 sites observed** (52 → 61 with fourteen more levels), 166
  distinct tuples, **ZERO protected-set hits corpus-wide**.
- **118 sites silent across the whole game's any% completion** — the
  dead-candidate pile, dominated by table_backed (59) and
  mixed_reaching_definitions (29). Operator records 100% runs next; the
  harness re-prices this pile directly from them.
- The 0x80018CBC → 0x8001961C violation is confirmed at corpus scale
  (332,160 observations) and REMAINS THE ONLY ONE — fourteen additional
  levels produced no new domain violations.
- **Replication proof**: LEVEL01/LEVEL07 each ran twice; 6/6 slice-pairs
  gave IDENTICAL per-site target sets (counts differ — each drain cycle has
  a wall-clock-dependent capture-blind re-arm window; counts are lower
  bounds, sets are the stable observable).

## 2026-08-08 — recording plan for the 100% corpus (operator + assistant agreed)

Operator records on 2026-08-09, via an assistant-driven pinned-Interpreter
recording instance (v4, state-anchored in-level near spawn, recording-time
hash binding). Scope agreed after checking the behavior library:

- **16 × plain 100% collection runs** — all grain, all FLIK letters (incl.
  the bonus-stage entries they trigger), all enemies killed with gold
  berries, and **all seed TOKENS collected** (no row covers full-token
  collection per level; it rides these runs).
- **5 × short seed-color clips** (blue/brown/green/purple/yellow), planting
  each color and letting the plant act. These REPLACE the A13 set, which
  was operator-confirmed desyncing on pinned Interpreter (v3,
  CachedInterpreter-era, poll-only) — so they upgrade the A13 fixtures to
  traceable versions as a side effect.
- **No other mechanic rituals** in the runs: deaths, bosses, powers,
  letters, bonus resets etc. are already covered by the 39-clip Interpreter
  behavior library (sweep in progress), so re-performing them adds nothing.

Standing hypothesis to check when the data lands: behavior sweep lights
10–25 currently-silent sites; 100% runs add a handful; final silent pile
~80–100 of 179, table_backed/mixed dominated, zero protected hits
throughout.

### Addendum: full re-record backlog (operator directive — ALL pre-v4/non-Interpreter Phase fixtures)

Inventory 2026-08-08: ~90 movies outside `movies/Phase4/Interpreter/` (v3
except three v4 strays). Empirical rule (blue_seed test): these are
presumptively CachedInterpreter, POLL-ONLY, unsweepable. Triage:

**Superseded — do NOT re-record:**
- `go_to_end/` (15 levels) → superseded by the Interpreter Any% corpus.
- old `100%`/`100% Runs` v3 (LEVEL00/01/04) → superseded by the 2026-08-09
  recordings.
- `b06_desync_test*` → purpose-built desync fixtures, keep as-is.
- Bonus_Level_01/02/03, C16_gameover_continue, B06/B08 variants → behavior
  already in the Interpreter library.

**Unique behaviors worth re-recording on Interpreter (priority order):**
1. **E10 hazards** (8): acorn, falling rocks, falling spikes, goo, ground
   bird, pits ×3 — per-hazard contact/death paths, nothing like them in
   the library.
2. **E09 gates** (12, or one condensed clip per level visiting all gates).
3. **Enemy variety kills/contacts**: D08 fly, D09 cockroach, D11 grub,
   D11 mite, B11 blue shooter, b12 homing shooter, B13 mine (+ D15 daddy
   long legs is already covered in the library).
4. **Traversal powers**: B01 mushroom chain, B02 propeller(+seed),
   B03 dandelion updraft, B04 cannon+dandelion combo.
5. **Small singles**: C01/C02 grain 49→50 threshold, c13 harvester,
   c14 telescope, E15 FMV-skip, kick/swing, Phase_Helpers carries.
6. **A13 seed colors ×5** (already in the 2026-08-09 plan).

No deadline: poll-only fixtures stay valid for their original rows' poll
work; re-records matter only where future TRACING of that behavior is
plausible. The 2026-08-09 session = 16×100% + 5 seed clips; the rest of
this list is a standing queue the operator works through at leisure.

## 2026-08-08 — IN-FLIGHT: behavior-library sweep + handoff pointer

The 39-clip Interpreter behavior library is being swept through the jr-tuple
harness (detached process; survives the launching session). **Any agent
finishing this work should follow
`engineering-specs/phase4-behavior-sweep-completion.md`** — it carries the
exact log/output paths, health gates, merge rules (overlay-attribution
guard), the hypothesis to check (10–25 newly-lit sites, final silent pile
~80–100), banking steps, and the instance-stop instruction. Results land as
a `behavior_library_sweep` section in
`analysis/phase4_f01_jr_tuple_capture.json` plus a dated section here.

Meanwhile the operator is recording the 100% corpus (LEVEL00–04 done);
recording-mode verification of those takes is PENDING (must be
pinned-Interpreter to be traceable — test one file before recording more).

## 2026-08-08 — behavior-library sweep complete: 27 sites newly lit, final silent pile = 100, hypothesis held

Per `engineering-specs/phase4-behavior-sweep-completion.md`, executed by the
launching session. 117 sessions, zero pass failures; 114 merged (bird_interpreter
×3 excluded — no control AND no observations, indistinguishable from a broken
arm; C17_MovieViewer included with the menu-context control caveat).

- Behavior library observed **78 sites**; **27 newly lit** vs the any% corpus
  (MEMORY movie-viewer/frontend dispatch from C17, library-zone handlers from
  bosses/bonus). Combined observed: **79/179**. **Final silent pile: 100**
  {table_backed 52, mixed 28, opaque 13, computed 5, register 1, incoming-ra 1}.
- **Zero protected-set hits** — now across any% corpus + the entire behavior
  library. The 0x80018CBC → 0x8001961C violation REMAINS THE ONLY ONE.
- Banked hypothesis: 10–25 newly lit / pile 80–100 / zero protected. Actual:
  27 / exactly 100 / zero. **Held in substance** (newly-lit 2 above band).
- Raws + merged analysis in the external store (176 entries, SHA256SUMS).
- Standing next optimization: validate UNTHROTTLED normal-loop playback by
  exact target-set comparison against these references before sweeping the
  incoming 100% corpus (expected 2–4×). Frame-stepping stays forbidden for
  correction-bearing movies.

What remains for the silent 100: the operator's 100% corpus (LEVEL00–04
recorded, mode verification PENDING), the seed-color re-records, and the
re-record backlog. After those, the pile is as small as gameplay can make it.

## 2026-08-09 — fast-forward validation REJECTED; 100%-corpus sweep begun (LEVEL00–05)

The operator's 100% recordings verified perfect on arrival: v4,
armed_while_paused recorded, **recording-time sha binding** (stronger than
the backfilled any% corpus), recorded on their Interpreter-pinned profile.

Unthrottled validation (per the standing optimization note): API has
`emulator.setFastForward`; B02 clip replayed armed at ~2.6× and compared
set-for-set against its banked reference. **REJECTED — two sites lost
targets** (0x8004D1E8 jalr missing 0x80049E88/0x8004A180; 0x800602A8 jr ra
missing 0x80058EC0; both subsets, nothing new — consistent with rare
dispatches landing in the drain blind-windows, which span ~2.6× more
emulated time at speed). Per the pre-set criterion (identical sets or stay
real-time): all sweeps remain at 60 Hz. Revisit only with a capture that
eliminates blind windows.

LEVEL00–05 sweeping at 60 Hz (18 passes); remaining levels join as the
operator records them. Also noted: /tmp was cleaned between sessions — the
scratchpad drivers were restored FROM THE EXTERNAL STORE, which is exactly
why raws and drivers are preserved there.

### Addendum 2026-08-09: re-record list FINALIZED + behavior-sweep coverage gap

Operator confirms the 100% runs include FMV played AND skipped plus
telescope use — those one-offs are COVERED. Harvester: no Interpreter clip
exists (only the v3 c13); covered iff a harvester was encountered during
the grain runs, else one cheap clip. **Coverage gap found: the behavior
sweep's glob missed `Interpreter/D07/` (3 mosquito clips)** — now chained
to sweep after the 100% batches. FINAL re-record list: ~6 per-level hazard
clips (top priority; runs avoid hazards), 1–2 enemy damage-tour clips (iff
the runs dodged most contact damage), 5 seed-color clips. LEVEL13
(Anthill pt 2) 100% take: presence unresolved with operator.

## 2026-08-09 — 100%-corpus sweep COMPLETE: zero new sites — CONVERGENCE

All operator 100% takes swept (LEVEL00–05, 07–14 incl. the renamed
LEVEL13_ANTHILLPT2, ×3 slices) plus the 3 D07 mosquito clips: 51 sessions,
zero failures, all health gates green. Result: **62 sites observed — every
one already known. ZERO newly-lit sites; the silent pile stays exactly 100.**
One new target at a known site (0x800602A8 jr ra → 0x8004B84C — an eighth
return path). Protected hits still ZERO across everything; the 0x80018CBC
violation still the only one.

**Convergence statement:** the 100 silent sites are now silent across any%
completion, every behavior fixture, and full 100% collection of the whole
game. Gameplay saturation is effectively reached; only the planned hazard /
damage-tour / seed clips remain as gameplay levers, and expectations for
them should now be LOW (the 100% corpus adding zero revises the prior).
The bar decision's evidence base is at its practical maximum. External
store refreshed (228 entries).

## 2026-08-09 — the runtime data DECOMPOSES the proof problem: three disciplines

Post-convergence analysis of the tuple corpus against the frozen 179-site
universe. The finding that matters: **the observed behavior sorts into three
structurally different disciplines**, which reformulates the goal from
"enumerate each site's exact target set" (the shape that failed three times,
because the recursion never bottoms out) to "prove each site obeys its
discipline" — local, compositional, and independent of closing the caller
graph.

| discipline | sites | obs/silent |
|---|---:|---|
| D1 return discipline (`jr $ra`) — prove $ra integrity, creates no new edge | 19 | 15/4 |
| D2 switch/computed locality — bounds-checked table index (existing gate machinery) | 20 | 15/5 |
| D3 pointer dispatch (`jalr`) — table-membership invariant + protected-set disjointness | 140 | 49/91 |

⚠️ **Correction banked**: an initial verbal claim that the return class was
the largest was WRONG — D1 is 19 sites; D3 is 140 (78%). The pilot samples
all three rather than betting on one.

Two by-products of the analysis:
- **New discovery**: some frontend dispatches transfer into
  **0x800CABE0-space — outside every static image in the census**. That is
  dynamically-loaded module code; it needs a LOADER CONTRACT, not a table
  proof, and is carried as its own named sub-problem.
- **Data caveat banked**: `LEVEL07_LEVEL1:0x800B3FCC` recorded ~42
  implausible targets (residency contamination — the overlay held non-code
  during load). Overlay-site tuples are untrusted without residency
  verification; resident-image tuples unaffected. No prior claim depended on
  it.

Work order drafted: `engineering-specs/phase4-discipline-proof-work-order.md`
(self-contained for hand-off; Stage 0 assignment → per-discipline engines →
pilot across all three with freeze-before-outcomes, GO = ≥60% of D1 + ≥1 D3
invariant + clean runtime cross-check; NO-GO must label each wall
technique-shaped or structure-shaped — that label is what tells the operator
whether a fourth attempt is worth funding).

## 2026-08-10 — discipline-proof pilot frozen (PRE-OUTCOME record)

This section freezes the mandatory pilot before any D1/D2/D3 proof outcome is
computed. The denominator is the committed 179-site
`pilot_selection.candidate_union_ids` set in
`analysis/phase4_target_exclusion_freeze.json`; it is not re-derived. Compiled C
decoding assigns the complete denominator structurally as D1 = 19 `jr $ra`, D2 =
20 other `jr`, D3 = 140 `jalr`, residual = 0, across exactly 110 owner extents.

Selection query:

- D1: all 19 sites, ordered by numeric PC then image/id.
- D2: the first eight sites in that order.
- D3 table-first tranche: the first eight D3 sites whose committed predecessor
  classification is `table_backed`, ordered by numeric PC then image/id.
  `phase3_jr_tables.json` contains `jr` dispatches rather than `jalr` sites, so
  matching a D3 site ID or load-cell extent directly against its decoded table
  keys yields the empty set; the predecessor's compiled-C `table_backed`
  classification is the fail-closed operational reading of the work order's
  "dispatch region is already a decoded table" phrase. Then select the first
  four still-unselected D3 sites in the same order. This interpretation and the
  zero direct-match fact are frozen here, not chosen after outcomes.

### D1 sample (19/19)

| rank | frozen site |
|---:|---|
| 1 | `SCUS_942_88:0x80011128:jr:ra` |
| 2 | `SCUS_942_88:0x800163d8:jr:ra` |
| 3 | `SCUS_942_88:0x800172d4:jr:ra` |
| 4 | `SCUS_942_88:0x8001897c:jr:ra` |
| 5 | `SCUS_942_88:0x80018f44:jr:ra` |
| 6 | `SCUS_942_88:0x8001923c:jr:ra` |
| 7 | `SCUS_942_88:0x80019614:jr:ra` |
| 8 | `SCUS_942_88:0x80019b3c:jr:ra` |
| 9 | `SCUS_942_88:0x80019f34:jr:ra` |
| 10 | `SCUS_942_88:0x8001a0dc:jr:ra` |
| 11 | `SCUS_942_88:0x8001a1d4:jr:ra` |
| 12 | `SCUS_942_88:0x80060144:jr:ra` |
| 13 | `SCUS_942_88:0x800602a8:jr:ra` |
| 14 | `SCUS_942_88:0x800602d8:jr:ra` |
| 15 | `SCUS_942_88:0x80060478:jr:ra` |
| 16 | `SCUS_942_88:0x80060cc4:jr:ra` |
| 17 | `SCUS_942_88:0x8006689c:jr:ra` |
| 18 | `SCUS_942_88:0x8006690c:jr:ra` |
| 19 | `MEMORY:0x800bd878:jr:ra` |

### D2 sample (first 8/20)

| rank | frozen site |
|---:|---|
| 1 | `SCUS_942_88:0x80018a4c:jr:s6` |
| 2 | `SCUS_942_88:0x80018b1c:jr:s6` |
| 3 | `SCUS_942_88:0x80018bec:jr:s6` |
| 4 | `SCUS_942_88:0x80018cbc:jr:s6` |
| 5 | `SCUS_942_88:0x80019c28:jr:at` |
| 6 | `SCUS_942_88:0x80019c84:jr:at` |
| 7 | `SCUS_942_88:0x80019ce0:jr:at` |
| 8 | `SCUS_942_88:0x80066818:jr:t1` |

### D3 sample (8 table-backed + 4 next, 12/140)

| tranche rank | frozen site |
|---:|---|
| table 1 | `SCUS_942_88:0x80061ae4:jalr:v0` |
| table 2 | `SCUS_942_88:0x80061b24:jalr:v0` |
| table 3 | `SCUS_942_88:0x80061fac:jalr:v1` |
| table 4 | `SCUS_942_88:0x80061fcc:jalr:v0` |
| table 5 | `SCUS_942_88:0x80061ff4:jalr:v1` |
| table 6 | `SCUS_942_88:0x80062010:jalr:v0` |
| table 7 | `SCUS_942_88:0x8006202c:jalr:v0` |
| table 8 | `SCUS_942_88:0x80062074:jalr:t0` |
| next 1 | `SCUS_942_88:0x8004d1e8:jalr:v0` |
| next 2 | `SCUS_942_88:0x80060c78:jalr:t2` |
| next 3 | `SCUS_942_88:0x800620c0:jalr:v1` |
| next 4 | `SCUS_942_88:0x800620e8:jalr:v1` |

No D1 return-discipline outcome, D2 locality outcome, D3 membership/writer
outcome, runtime cross-check result, protected-set decision, or GO/NO-GO
decision existed when this list was frozen.

### Addendum 2026-08-09: F01's blocker is Phase-4-wide infrastructure debt

Owner-subsystem mapping of the 179 unproved indirect sites (110 owner
functions): **frontend/save 48 (26.8%), render+geometry 38 (21.2%),
streaming/loaders 17 (9.5%), audio 7, collision+contact 4, props/event VM 3,
unnamed 62**. Essentially ZERO are Anthill-specific — 166 of 179 live in the
RESIDENT image shared by every level and row. F01 is simply the row that hit
the wall first.

Consequence: every discipline proved by
`engineering-specs/phase4-discipline-proof-work-order.md` discharges the same
item-2 obligation for E01/E02/E03/E11/E14/E16 and others simultaneously. The
order now reports progress per owning subsystem as well as per site, so the
Phase-4-wide payoff is visible rather than inferred.

### Correction 2026-08-10: the cross-row transfer was OVERSTATED

The 2026-08-09 addendum claimed each discipline proof "discharges the same
item-2 obligation for E01/E02/E03/E11/E14/E16". Checking those rows'
`missing` fields in `analysis/mechanics_baseline.yaml` FALSIFIES that: their
current blockers are semantic (payload decode + marker-class semantics,
transition semantics, aux-list content, field roles, interaction rules,
scene→DAT binding, event maps, lifecycles), not indirect control flow.

Corrected three-part statement (now in the work order §2b):
1. Ownership is shared — the 179 sites live in E-section code, so the proofs
   are performed on and produce E-section understanding.
2. The obligation is DEFERRED for most rows, binding only when they reach
   strict DoD. Already frontier-shaped and therefore direct beneficiaries:
   **E09** ("no complete writer/callee frontier"), **E06** (complete field
   typing + executable gate), **E07** (explicitly not strict), **E16** (18 of
   42 entry lists single-detector, no runtime call check).
3. One immediate payoff: proved D2/D3 edges improve the call graph, which
   serves attribution residuals already listed — E05's unattributed registry
   writer, E14's side-table increment source, E01's untraced animated-tile
   uploader call site.

Lesson re-applied: the `knockdown-not-a-slot-writer` auto-memory — I encoded an inference
("same obligation") as a committed claim without reading the rows it named.

## 2026-08-10 — discipline-proof pilot outcome (reviewed negative)

| # | discipline | site | outcome | named wall | wall shape | byte witness (PC / word) |
|---:|---|---|---|---|---|---|
| 1 | D1_return | `SCUS_942_88:0x80011128:jr:ra` | NAMED_WALL | `incoming_ra_or_owner_entry_provenance_not_closed` | technique-shaped | `0x80011128` / `0x03e00008` |
| 2 | D1_return | `SCUS_942_88:0x800163d8:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x80015544` / `0x02c0f820` |
| 3 | D1_return | `SCUS_942_88:0x800172d4:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x80016554` / `0x02c0f820` |
| 4 | D1_return | `SCUS_942_88:0x8001897c:jr:ra` | NAMED_WALL | `incoming_ra_or_owner_entry_provenance_not_closed` | technique-shaped | `0x8001897c` / `0x03e00008` |
| 5 | D1_return | `SCUS_942_88:0x80018f44:jr:ra` | NAMED_WALL | `runtime_falsified_call_link_only_return` | structure-shaped | `0x80018f44` / `0x03e00008` |
| 6 | D1_return | `SCUS_942_88:0x8001923c:jr:ra` | NAMED_WALL | `runtime_falsified_call_link_only_return` | structure-shaped | `0x8001923c` / `0x03e00008` |
| 7 | D1_return | `SCUS_942_88:0x80019614:jr:ra` | NAMED_WALL | `runtime_falsified_call_link_only_return` | structure-shaped | `0x80019614` / `0x03e00008` |
| 8 | D1_return | `SCUS_942_88:0x80019b3c:jr:ra` | NAMED_WALL | `runtime_falsified_call_link_only_return` | structure-shaped | `0x80019b3c` / `0x03e00008` |
| 9 | D1_return | `SCUS_942_88:0x80019f34:jr:ra` | NAMED_WALL | `runtime_falsified_call_link_only_return` | structure-shaped | `0x80019f34` / `0x03e00008` |
| 10 | D1_return | `SCUS_942_88:0x8001a0dc:jr:ra` | NAMED_WALL | `runtime_falsified_call_link_only_return` | structure-shaped | `0x8001a0dc` / `0x03e00008` |
| 11 | D1_return | `SCUS_942_88:0x8001a1d4:jr:ra` | NAMED_WALL | `runtime_falsified_call_link_only_return` | structure-shaped | `0x8001a1d4` / `0x03e00008` |
| 12 | D1_return | `SCUS_942_88:0x80060144:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x800600e0` / `0x8fffa4b4` |
| 13 | D1_return | `SCUS_942_88:0x800602a8:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x8006029c` / `0x00e0f821` |
| 14 | D1_return | `SCUS_942_88:0x800602d8:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x800602cc` / `0x00e0f821` |
| 15 | D1_return | `SCUS_942_88:0x80060478:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x8006046c` / `0x00e0f821` |
| 16 | D1_return | `SCUS_942_88:0x80060cc4:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x80060cbc` / `0x8fff2208` |
| 17 | D1_return | `SCUS_942_88:0x8006689c:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x80066894` / `0x8fff6aa0` |
| 18 | D1_return | `SCUS_942_88:0x8006690c:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x80066904` / `0x8fff6ab0` |
| 19 | D1_return | `MEMORY:0x800bd878:jr:ra` | NAMED_WALL | `non_call_non_frame_ra_definition` | structure-shaped | `0x800bd870` / `0x8fffe58c` |
| 20 | D2_switch_computed | `SCUS_942_88:0x80018a4c:jr:s6` | NAMED_WALL | `materialized_continuation_set_is_not_a_bounds_checked_indexed_table` | structure-shaped | `0x8001889c` / `0x36d68cc4` |
| 21 | D2_switch_computed | `SCUS_942_88:0x80018b1c:jr:s6` | NAMED_WALL | `materialized_continuation_set_is_not_a_bounds_checked_indexed_table` | structure-shaped | `0x8001891c` / `0x36d68cc4` |
| 22 | D2_switch_computed | `SCUS_942_88:0x80018bec:jr:s6` | NAMED_WALL | `materialized_continuation_set_is_not_a_bounds_checked_indexed_table` | structure-shaped | `0x800188c4` / `0x36d68cc4` |
| 23 | D2_switch_computed | `SCUS_942_88:0x80018cbc:jr:s6` | NAMED_WALL | `materialized_continuation_set_is_not_a_bounds_checked_indexed_table` | structure-shaped | `0x80018888` / `0x36d68cc4` |
| 24 | D2_switch_computed | `SCUS_942_88:0x80019c28:jr:at` | NAMED_WALL | `materialized_continuation_set_is_not_a_bounds_checked_indexed_table` | structure-shaped | `0x80019ba0` / `0x3421a0e4` |
| 25 | D2_switch_computed | `SCUS_942_88:0x80019c84:jr:at` | NAMED_WALL | `materialized_continuation_set_is_not_a_bounds_checked_indexed_table` | structure-shaped | `0x80019b78` / `0x3421a0e4` |
| 26 | D2_switch_computed | `SCUS_942_88:0x80019ce0:jr:at` | NAMED_WALL | `materialized_continuation_set_is_not_a_bounds_checked_indexed_table` | structure-shaped | `0x80019b60` / `0x3421a0e4` |
| 27 | D2_switch_computed | `SCUS_942_88:0x80066818:jr:t1` | NAMED_WALL | `single_cell_thunk_is_not_a_bounds_checked_indexed_table` | structure-shaped | `0x80066810` / `0x8d296aa8` |
| 28 | D3_pointer_dispatch | `SCUS_942_88:0x80061ae4:jalr:v0` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x80061ad8` / `0x8c42fbc4` |
| 29 | D3_pointer_dispatch | `SCUS_942_88:0x80061b24:jalr:v0` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x80061b1c` / `0x8c42fbc4` |
| 30 | D3_pointer_dispatch | `SCUS_942_88:0x80061fac:jalr:v1` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x80061fa0` / `0x8c63fbc4` |
| 31 | D3_pointer_dispatch | `SCUS_942_88:0x80061fcc:jalr:v0` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x80061fc0` / `0x8c42fbc4` |
| 32 | D3_pointer_dispatch | `SCUS_942_88:0x80061ff4:jalr:v1` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x80061fe8` / `0x8c63fbc4` |
| 33 | D3_pointer_dispatch | `SCUS_942_88:0x80062010:jalr:v0` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x80062004` / `0x8c42fbc4` |
| 34 | D3_pointer_dispatch | `SCUS_942_88:0x8006202c:jalr:v0` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x80062020` / `0x8c42fbc4` |
| 35 | D3_pointer_dispatch | `SCUS_942_88:0x80062074:jalr:t0` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x80062044` / `0x8d08fbc4` |
| 36 | D3_pointer_dispatch | `SCUS_942_88:0x8004d1e8:jalr:v0` | NAMED_WALL | `object_field_membership_and_writer_invariant_open` | technique-shaped | `0x8004d1e0` / `0x8e02007c` |
| 37 | D3_pointer_dispatch | `SCUS_942_88:0x80060c78:jalr:t2` | NAMED_WALL | `entry_scoped_bios_constant_lacks_ingress_and_named_exception_contract` | technique-shaped | `0x80060c74` / `0x240a00b0` |
| 38 | D3_pointer_dispatch | `SCUS_942_88:0x800620c0:jalr:v1` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x800620b4` / `0x8c63fbc4` |
| 39 | D3_pointer_dispatch | `SCUS_942_88:0x800620e8:jalr:v1` | NAMED_WALL | `dispatch_cell_writer_universe_open` | technique-shaped | `0x800620dc` / `0x8c63fbc4` |

**NO-GO: D1 landed 0/19 (requires at least 12) and D3 landed 0/12 (requires at least one gate-grade membership invariant); no nonempty proved-site runtime cross-check exists.**

### What the negative establishes

- **D1 is structure-shaped as a route to the threshold.** Ten sites have a
  reaching `$ra` definition that is neither call-link semantics nor a balanced
  stack-frame restore (register copies or non-frame global loads). Seven more
  have retained runtime targets that are not call-instruction successors. The
  two remaining sites die at owner-entry/incoming-`$ra` provenance, a
  technique-shaped wall. Thus the wall split is 17 structure / 2 technique.
- **D2 is structure-shaped (8/8).** Seven are materialized continuation
  selection, not `base + f(bounds_checked_index)` jump tables; the eighth is a
  single-cell thunk through `0x80086AA8`. The two C implementations reproduce
  the old three-target, entry-scoped claim for the first four. Runtime then
  falsifies promotion of that candidate at `0x80018CBC`: observed
  `0x8001961C` lies outside `{0x80018CC4,0x80018F4C,0x80019244}`. This is a
  candidate soundness halt, not an accepted-proof failure—the candidate was
  rejected before the proved set was formed.
- **D3 is technique/contract-shaped (12/12).** One site loads an untyped object
  field at `+0x7C`; one has an entry-scoped constant `0xB0` but no external
  ingress exclusion or named BIOS exception contract; ten load the shared
  dispatch cell `0x8007FBC4`. A compiled-C region scan over all 21 pristine
  images leaves **4,266 unresolved stores** that may alias that four-byte cell,
  including **2,244 full-width stores**. `SetDumpFnt@0x80060FE8` is a known
  direct writer, but is only a lower-bound fact while that residual is nonzero.

The independent-cross-check obligation has an empty landed-proof set. Its
status is `NOT_APPLICABLE_EMPTY_LANDED_SET`, explicitly not “clean.” The
independent forward C implementation did re-derive all five entry-scoped
candidate facts, including the runtime-falsified `0x80018CBC` candidate; this
does not upgrade any candidate to gate grade.

The general F01 typed-state table question retains its separately measured
**5,012 corpus-undecided stores**. Do not merge that count with the 4,266-store
`0x8007FBC4` question: they are different target regions. The protected-set
universe remains exactly 128 unique image/PC members derived from 58 known
writers, 124 window sites, and four closure roots; no D3 membership set was
proved, so protected-set disjointness was not promoted.

Per name-based owning-subsystem bucket (counts exact, labels approximate), the
pilot sampled render/geometry 34, props/event VM 1, streaming/overlay 1, and
unnamed/other 3; every bucket landed zero. The 2026-08-10 cross-row correction
remains binding: ownership is shared, direct benefit is verified only for the
named frontier-shaped rows, and reachability for other rows remains a
hypothesis.

### Reproduction and protected state

Primary artifact: `analysis/phase4_discipline_pilot.json`
(`abl-phase4-discipline-pilot/1`). Reproduce/check:

```bash
python3 tools/phase4_discipline_pilot.py --check
pytest -q tests/test_phase4_discipline_assignment.py tests/test_phase4_discipline_pilot.py
```

The driver rebuilds the primary exact-domain C analyzer and its independent
forward implementation with `-std=c11 -O2 -Wall -Wextra -Werror` (self-tests
9/9 and 8/8), and rebuilds `region_provenance.c` with
`-std=gnu11 -O2 -Wall -Wextra`. The latter retains four disclosed pre-existing
unused-code warnings; all 21 runs report no truncation warning. All image
identities, derived inputs, corrected work-order commits, C sources, binaries,
stdout, residual identities, and stderr are hash-pinned by the artifact.

No live or instrumented replay was performed. The `LEVEL07_LEVEL1:0x800B3FCC`
residency-contaminated tuple set was not used. No gate, index, closure, or
mechanics artifact was regenerated because the mandatory pilot returned
NO-GO. F01 remains `partial`; item 2 remains `not_met`; blockers remain
`[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`. The indirect-site
residual stays **179 → 179**, so this result does not change the scale of the
operator's item-2 bar decision.

## 2026-08-10 — independent verification of the discipline pilot NO-GO: ACCEPTED, D1 confirmed structure-shaped by bytes

Codex executed `engineering-specs/phase4-discipline-proof-work-order.md`
(freeze `02338883`, results `62e343f1`, audit `29bca2dc`). Verified here.

**Result accepted.** D1 0/19 (17 structure-shaped, 2 technique-shaped), D2 0/8
(all structure-shaped), D3 0/12 (contract-shaped). Residual 179 → 179. F01
verdicts byte-stable: `partial`, item 2 `not_met`, both blockers.
Freeze-before-outcomes ancestry confirmed (freeze commit precedes results by
~20 min and contains no outcome fields).

**The decisive claim, byte-verified independently.** D1's structure-shaped
label rests on `jr $ra` sites whose targets are not call-returns. Testing
every observed D1 target against "is `target-8` a call instruction?":

- 0x80011128, 0x800163D8, 0x800172D4, 0x80060144, 0x800602A8 (20 targets),
  0x800602D8, 0x80060CC4 → **all legitimate call-returns** (e.g. 0x800206A0
  is produced by `jal 0x80010000` at 0x80020698).
- **0x80018F44, 0x8001923C, 0x80019614, 0x80019B3C, 0x80019F34, 0x8001A0DC,
  0x8001A1D4 → 18 observed targets that are NOT call-returns.** The word at
  `target-8` is a STORE (`0xA6630030` = `sh $v1, 0x30($s3)`;
  `0xA66E0024` = `sh $t6, 0x24($s3)`).

⚡⚡ **`$ra` is used as a general-purpose jump register in the GTE/clip
region.** Return discipline is therefore **FALSE of this binary**, not merely
unproven — no engine improvement can prove a false property. Same
neighbourhood as the 0x80018CBC falsification; that region appears to be
hand-optimised GTE assembly. Codex's structure-shaped label is CORRECT.

Also confirmed: the pilot independently re-caught the 0x80018CBC runtime
falsification and refused to promote that candidate
(`candidate_soundness_halt.triggered: true`, accepted proof set unaffected).

**Test-suite finding (pre-existing, not caused by this work).** The full
`-k phase4` selection shows **283 failures at HEAD**. Comparing against a
detached worktree at the pre-Codex commit `e096b7be`: **352 failures**. The
work order therefore *reduced* failures by 69 and introduced none. This is
inherited repository-wide baseline debt (the same debt that blocks the
closure-debt ledger, roadmap §0) and is worth its own cleanup increment.

**Consequence for the roadmap.** Per §3, structure-shaped means no known
further technique for D1/D2. `complete_frontier` now has exactly one
remaining technical avenue — the narrow D3 contract work (shared dispatch
cell 0x8007FBC4 with 4,266 unresolved stores, object-field provenance, BIOS
ingress, dynamic-module loader boundary) — and otherwise depends on the
operator's item-2 bar ruling.

## 2026-08-10 — closure-debt blocker DIAGNOSED: 5 of 7 errors are phantom pins, 1 is real debt

Roadmap §0 called this "cheap to fix." It is cheaper than feared in one sense
and not a single fix in another. Applying [[#2026-08-10 — closure-debt blocker DIAGNOSED 5 of 7 errors are phantom pins, 1 is real debt|pin mismatch is not drift]]
(check whether the pinned hash EVER existed on this branch) to all three
artifacts:

| # | error | nature | evidence |
|---|---|---|---|
| 1 | `phase0_2_external_fixture_set.json` sha mismatch | **PHANTOM PIN** | pinned `801d7e5c…` absent from 14 commits of history |
| 2 | `missing_central_pins` len 30 ≠ 0 | ⚠️ **REAL DEBT** | ~30 evidence fixtures (mostly Interpreter movies) used by rows but absent from `analysis/phase2_fixture_audit.json` |
| 3 | `phase0_2_knowledge_closure_report.json` sha mismatch | **PHANTOM PIN** | pinned `76ddc6ac…` absent from 24 commits |
| 4 | `external_fixture_source_relocation_errors` unresolvable | **SCHEMA DRIFT** | field exists in NEITHER HEAD nor WIP; artifact now emits `external_local_media_manifest_errors` etc. |
| 5 | `external_operator_fixture_input_errors` unresolvable | **SCHEMA DRIFT** | same; cf. `provisioned_source_input_errors` |
| 6 | `phase4_trace_capsule_set.json` sha mismatch | **PHANTOM PIN** | artifact has exactly ONE commit (`4bdd5269`), always sha `569b3ebf…`; pinned `9896da99…` never existed |
| 7 | `exact_capsules` 50 ≠ 55 | **PHANTOM EXPECTATION** | the artifact has always said 50 (`requested: 50`, 50 capsules present) |

**The scorecard note's characterization was wrong** — it described all of these
as "tranche-era pins from fmv_playback." The *category* is right (tranche-era
authoring against artifact generations that never landed on master) but the
*files* are these three, and #2 is not a pin problem at all.

### Repaired now
Error 6+7: the capsule assertion in `config/phase4_campaigns.yaml:4155` re-pinned
to master reality (sha `569b3ebf…`, `expected: 50`). Safe because the artifact
is clean/committed and the project already concluded master's 50/50/50 capsule
set is healthy. **Errors 7 → 6.**

### Blocked on an operator decision
Errors 1, 3, 4, 5 all sit on `analysis/phase0_2_external_fixture_set.json` and
`analysis/phase0_2_knowledge_closure_report.json`, which are **operator WIP**
(modified in the working tree since before this session, regenerated
`2026-08-06` by `tools/knowledge_closure_audit.py --write`). Re-pinning requires
deciding which bytes are canonical — the committed version or the WIP
regeneration — and that is the operator's call, not the assistant's. Once
decided: re-pin the two shas and retarget the two dead leaf names to the fields
the tool actually emits.

### Genuinely not a pin problem
Error 2 (`missing_central_pins`) is real registration debt: ~30 fixtures,
mostly `movies/Phase4/Interpreter/*`, are consumed by `phase2_row_coverage`,
`phase3_gate_audit`, `phase3_ownership_graph` and named mechanics rows, yet are
absent from `analysis/phase2_fixture_audit.json`. **This gate must NOT be
weakened to make the ledger write** — the fixtures need registering. Note the
irony: several are the very Interpreter movies this week's campaigns depend on.

## 2026-08-10 — closure-debt blocker REPAIRED: 7 errors → 1 (commit fc772a006b8b)

Roadmap §0 executed. Operator delegated all decisions ("i have not done any
work here at all so i will leave the decisions up to you"), which also
resolved the WIP question: the two `phase0_2_*` working-tree modifications
were a stale 2026-08-06 tool regeneration by nobody in particular, not
hand-authored operator work — so the canonical bytes are simply what
`tools/knowledge_closure_audit.py --write` produces today (verified
deterministic: two consecutive runs, identical SHAs).

### Phantom pins retired (5 of the 7)
Applying [[#2026-08-10 — closure-debt blocker DIAGNOSED 5 of 7 errors are phantom pins, 1 is real debt|pin mismatch is not drift]] to every assertion: **none of
the pinned SHAs ever existed on any commit** —
- capsule set `9896da99…` — artifact has exactly ONE commit, always
  `569b3ebf…`, always `exact_capsules: 50`; the assertion demanded 55
- external fixture set `801d7e5c…` — absent from 14 commits
- knowledge closure report `76ddc6ac…` — absent from 24 commits

And two asserted JSON leaves (`external_fixture_source_relocation_errors`,
`external_operator_fixture_input_errors`) exist in **no commit** of the
artifact — not schema drift, never-emitted names. **Retargeted** to the
fields the generator does emit rather than dropped, which strengthens the
gate: `external_local_media_manifest_errors` /
`external_local_media_input_errors`.

### One real error found and fixed properly
Retargeting surfaced a live failure: `tools/repro_inputs.sha256` held a stale
hash for `asm/hand_written/80057620_checkpoint_construct.s` (manifest
committed 2026-08-01, file updated 2026-08-04; `asm/` is gitignored so no
history arbitrates). **Decided by assembling the file**: 228 bytes,
byte-identical to the pristine image ⇒ the FILE is correct and the manifest
was stale. Re-pinned. (Cascade: the manifest SHA is recorded in
`phase4_static_frontier_pilots.json`, one field, refreshed.)

### Real debt worked rather than weakened
`missing_central_pins` (expects 0, had 31) is a registration gap, not a pin
problem — so the gate was left strict and the work done:
`analysis/phase2_fixture_audit.json` regenerated against a live isolated
instance (needs `emulator.getStateInfo` per save). **Movies 108 → 205, saves
235 → 321; missing_central_pins 31 → 3.** Many of the newly-registered
fixtures are the Interpreter movies this week's campaigns ran on.

### Remaining (1 error, 3 entries) — data quality upstream
- `E02_FreshLoad_Clover.movie.json` is referenced by **bare filename** while
  the file lives at `movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json`
  (it is also the anchorless movie the behavior sweep skipped as NOSAV).
- Two "paths" in `phase3_gate_audit.json` / `phase2_row_coverage.json` are
  **prose descriptions** ("6 progression-diverse saves reused read-only; live
  L1/R1 traces on level01.sav"), not file paths.

Both are upstream artifact data-quality bugs. Left for a decided fix rather
than patched blind. F01 verdicts unchanged; 118 focused tests pass.

## 2026-08-10 — source_closure verified: honest measurement, INFLATED label (3.7% match)

Codex executed `phase4-f01-source-closure-work-order.md` (commit
`189e8f4214bd`). Verified here.

**Accepted as evidence; rejected as a "near-miss."** The measurement is
exemplary — 1,447 differing word positions listed with addresses and both
words, three named compiler walls, and the three intermediate attempts
explicitly marked `unretained_executor_observation` /
`supports_current_result: false`. File-disjointness was respected exactly
(src_re + receipt + tool + test; the analysis chain untouched).

But **56 of 1,503 words match — 3.7%.** That is a first draft, not a
near-miss; a near-miss is the handful of residual words `dc_permute` exists to
close, and the receipt itself correctly records that dc_permute was
inapplicable (size-mismatched candidate → sentinel score 9999). Compiled 6,012
bytes vs retail 6,004, with 2 compiled-only words, so even the CFG shape
differs.

**Method gap worth carrying forward:** the work order said to match region by
region rather than write the whole function and measure. All six regions came
back simultaneously `near_miss` (11/158, 1/89, …), which is the signature of
whole-function authorship. A continuation should **gate**: region N must reach
zero before region N+1 is attempted.

Named walls (all technique-shaped, none fundamental): global register
allocation + scheduling, mixed `$gp`-relative global addressing, extent/CFG
shape. Decomp projects match 6 KB functions routinely; the blocker was that
the m2c-normalised seed failed to compile, so authorship fell back to
hand-written C.

**Decision: do not send Codex back into this grind now.** `source_closure`
stays a documented **56/1,503-word (3.7%) first draft** to resume with a
region-gated method. Codex is
better spent on `original_interfaces`, which is tractable mechanical work —
work order drafted: `engineering-specs/phase4-f01-abi-ledger-work-order.md`.

**Unrelated finding Codex surfaced and correctly left alone:** a substrate test
fails because the configured end for `0x80042E94` is `0x80042F98` while the
census says `0x80042FA0` (8 bytes). Worth its own small increment — it is an
extent disagreement between two authorities, which is exactly the class the
extent audit exists to catch.

## 2026-08-10 — original_interfaces ledger: 764/764 rows, 0/764 fully resolved

Codex executed `phase4-f01-abi-ledger-work-order.md` without replaying the
emulator. That is the correct evidence boundary: the question is answered by
pristine image bytes, pinned static extents, and retained region-provenance
results. Python owns hashes/scope/receipt; compiled C owns every instruction
decode.

### Exact scope reconciliation

| source | functions present | absent from final union | outside union |
|---|---:|---:|---:|
| frontier reached functions | 764 | 0 | 0 |
| typed-state outcome extents | 645 | 119 | 0 |
| local-base owner extents | 20 | 744 | 0 |
| exact union | **764** | — | — |

The latter two are strict subsets of the frontier. Nine frontier identifiers
use the placeholder name `fn`; image+entry agrees and the ledger takes the
name/end from the static index as ordered. Nothing is silently added by a name
match.

### What the ledger actually proves

- **764/764 structural ABI rows** contain entry/end/image/name, consumed
  `a0`–`a3`, incoming stack slots, argument type/domain (including explicit
  `unknown`), return convention, caller/callee clobbers, frame shape, and
  memory effects.
- **0/764 mechanically closed rows under the complete-interface bar.** The hard-truth review caught that the
  first receipt had silently equated an unchanged incoming `$ra` value with a
  call link. The corrected probe does not. In 621 rows it can prove only an
  incoming-`$ra` continuation (including paired frame-slot reloads), so return
  convention remains explicitly unknown until incoming call-link provenance is
  established. Seven rows also require context splitting, three reach
  non-instruction overlay-header words, one has a variable/unknown frame, and
  17 suffix/continuation entries pop an inherited or otherwise unobserved frame.
- **0/764 return conventions presently proved.** No
  in-scope `jr $ra` is promoted to a normal return merely because it preserves
  the entry value. The known seven GTE/clip general-`$ra` sites are, importantly,
  **outside all 764 ledger extents**. They are now an explicit global caution
  control: C re-decodes all seven exact site words and all 18 retained
  site/target pairs, confirming each site is `jr $ra` and no observed target
  has a call at `target-8`. That retained runtime evidence is falsification/
  corroboration only, not ABI-row coverage or proof.
- **Caller/callee regression repairs.** `$t9` is included in the caller-saved
  set; pristine `contact_record_billboard_render` word `0x20190040` at
  `0x80014848` is the pinned regression. Canonical saves must now store a value
  proved unchanged from entry and survive slot-value dataflow to a matching
  reload. Thus LEVEL04 `level04_complete_handler` correctly selects `$s0` at
  entry-SP `-16` (`0x800B3F5C` → `0x800B4404`) and excludes the outgoing
  `sp+20` stores at `0x800B3FBC` and `0x800B4024`.
- **22/22 hoisted-load idioms** re-decode as the exact contiguous
  `slt/sltu; add/addu; load; beq/bne` shape. The load remains before its guard.
- **50/50 ABI-survey rows agree, zero disagreements.** This is agreement on
  exact region-domain availability; a generic memory-base pointer shape is not
  relabelled as a typed region.

### Honest completeness

| field | resolved fraction |
|---|---:|
| fully resolved rows | **0/764 (0.0%)** |
| mechanically closed rows | **0/764 (0.0%)** |
| return convention proved | **0/764 (0.0%)** |
| callee-saved effects classified | **617/764 (80.8%)** |
| consumed register-argument domains | **1/867 (0.1%)** |
| stack-argument domains | **0/94 (0.0%)** |
| rows with fully resolved pointer-write sets | **388/764 (50.8%)** |

For 621 rows, local dataflow reaches an incoming-`$ra` continuation but cannot
prove its entry value was a call link. The other 143 have no such proved
continuation, but absence is not proof of halt/tail-jump: a copied link or other
indirect exit remains possible. The earlier 81-row numerator incorrectly
counted rows whose callee-saved fields themselves said “not classified”; the
hard-truth ratchet now excludes them rather than turning a lack of proof into a
`no_normal_return` claim. Callee-save coverage is lower still at 617: four of
the 621 continuation rows have a direct entry into a physical delay-slot word,
so their context-collapsed CFG is explicitly incomplete and cannot bank a
callee-save classification.

The one exact argument domain is `player_vertical_update(a0)` =
`player_actor`, inherited only from the accepted typed-state binding. A
read-before-write memory-base use can prove “pointer,” but not its pointee
region; call-site constants remain corroboration rather than proof. Region
outcomes are joined verbatim by `(image, pc)` from retained typed state, whose
second opinion was produced by `tools/region_provenance.c`; this ledger does
not recompute or strengthen them.

The original 255 stack-slot denominator was itself rejected by hard-truth
review. Seventeen indexed entries contain a positive `$sp` pop without an
extent-local push; 144 loads in 16 of those rows are epilogue/inherited-frame
candidates, not ABI arguments. C now tracks positive and negative SP movement,
marks all 17 frames `inherited_or_unbalanced`, and retains the 144 exact loads
under `unclassified_entry_relative_stack_loads`. LEVEL08_LEVEL1 `0x800B3AEC`
is the byte-pinned regression: six loads at `0x800B3B4C..0x800B3B60`, followed
by `addiu $sp,$sp,40` at `0x800B3B64`, produce zero stack arguments.
The remaining call-entry rule is positive, not absence-based: the static index
must supply a same-image direct-call edge and C must re-decode its word and
exact target. That proves 94 arguments; 17 more candidate loads without such a
call witness also remain unclassified, for 161 retained unclassified loads in
total.

**Decision:** `original_interfaces` remains **not met / partial**. A complete
row scaffold is not a complete interface proof. Promotion would hide 866
unknown consumed register-argument domains, 94 unknown stack-argument
domains, 376 rows with unresolved pointer writes, 621 rows whose incoming
`$ra` lacks call-link provenance, and 143 whose other exit provenance remains
open. The next work is those exact semantic sets,
not another ABI census.

Artifacts: `analysis/phase4_f01_abi_ledger.json`,
`tools/phase4_f01_abi_ledger.py`, `tools/phase4_f01_abi_probe.c`, and
`tests/test_phase4_f01_abi_ledger.py`.

## 2026-08-10 — control-plane data quality: closure ledger unblocked, no promotion

The final closure-debt error is cleared at its sources. The bare
`E02_FreshLoad_Clover.movie.json` reference now expands to its real
`movies/Phase4/Interpreter/` path. The long E04 prose value is expanded to the
six saves named by the original survey (`level01`, `canyon_bug`, levels 09 and
12, the training ending, and the C17 movie-viewer save); all six and the E02
movie are independently present in the central fixture audit. The shorter
E04 prose string was not a second authored fixture set: it was the prior
audit's own retained `missing_fixture_pins` finding inside the generated gate
audit. Only that self-referential output field is excluded from that one
consumer scan. The central-pin predicate itself is unchanged—no whitelist or
gate relaxation was introduced.

Fresh detached generation reports **0/3 missing central pins**, then writes a
valid closure-debt ledger with **0 errors**, **16/107 complete rows**, and the
pre-existing **149 met / 61 partial / 753 gap** dimension distribution. This
increment claims no F01 dimension and performs no promotion.

The image bytes also decide the `0x80042E94` disagreement. After the call at
`0x80042F90`, `0x80042F98` is `sh $v0,1040($gp)` and `0x80042F9C` is
`sll $v0,$v0,16`; both are live fall-through result processing. Therefore the
non-overlapping census/decomp partition ends at **`0x80042FA0`**, and the old
`0x80042F98` segment end was eight bytes short. Execution may continue through
the callable `0x80042FA0` suffix to the shared return, so `0x80042FA0` is a
partition boundary, not a return claim. Hand ASM reproduces all **268 bytes**.

Making the substrate test honest exposed one adjacent unacknowledged defect:
`0x8001A1E0` ended immediately before its `jr $ra` delay-slot NOP. Its segment
now ends at `0x8001A900`, and hand ASM reproduces all **1,824 bytes**. The three
larger intentional prefix splits remain accepted only through their exact,
reviewed extent-audit acknowledgement tuples.

Receipt: `analysis/phase4_control_plane_data_quality.json`.

## 2026-08-10 — campaign_breadth sweep: the lifecycle machine observed across every level type

18 movies (16 levels of the operator 100% corpus **minus LEVEL02**, plus the 3
bonus clips) replayed at 60 Hz on **5 parallel pinned-Interpreter instances**
with atomic mkdir work-claiming. 18/18 outputs, zero failures, zero duplicate
claims, all health gates green. Wall clock ~20 min vs ~57 sequential.
Artifact: `analysis/phase4_f01_campaign_breadth.json`; raws sha-pinned in
`~/Downloads/ABL-external-evidence/phase4_campaign_breadth_2026-08-10/`.

### F01's shared transition-request word `0x800823A0` (7-value enum)

| value | levels | writer PCs |
|---|---:|---|
| 0 (clear) | 18 | 0x80036B90, 0x80036CD0, 0x80036D0C, 0x8004FE48, 0x8005B88C |
| **1 (completion)** | **14** | 0x800496DC / **0x800496FC** (inside `player_vertical_update` — F01's documented dispatch), 0x80036CBC, 0x80036CD0, plus overlay PCs 0x800B3E74/3E88/3EF4/3F1C/4104/4194 |
| **2 (death)** | **6** | 0x8004A8B8, 0x8004A9F8 |
| **6** | **3 — bonus stages ONLY** | 0x8004B3C4, 0x800591E0, 0x8005C6BC |

**What this buys the dimension.** F01's evidence was LEVEL01-only, where the
5-arm dispatch fires **code 2 alone** and death/other arms had ZERO
observations. Now: the completion arm is observed in **14 levels spanning every
type** the dimension enumerates, emitted from the exact resident dispatch F01
documents; the **death arm (request 2) is observed for the first time**, in 6
levels; and **request 6 appears exclusively in the three bonus stages** — a
previously unobserved arm with a clean semantic binding.

**Honest limits.** Requests **3, 4 and 5 remain unobserved anywhere** — the
enum is 7-valued and we have 4. Overlay writer PCs (0x800B*) are per-level
ambiguous by residency and are recorded as observed-in-that-level only. This is
evidence, not proof, and does NOT promote the dimension.

⚡ Notable mechanism finding: **level overlays write the completion request
directly** (0x800B3E74 etc.), not only the resident dispatch — so the campaign
machine has both a shared and a per-level entry path.

### Batching payoff — 37 other-row watches rode along at zero extra cost

The standing batching rule applied (after I initially violated it by launching
this sweep with 3 watches). Highlights:

- **E05's "writer unattributed"** for the second per-id registry `0x800A2188`
  is now attributed: **0x8003C158 and 0x8003CF6C**, in all 18 levels.
- **E16 `0x800A65B0`** has exactly one writer corpus-wide: **0x8003A3C0**.
- **C17's movie-viewer site 0x8003F580 is reached in ZERO of 18** — a bounded
  negative; the viewer is not entered by any corpus movie.
- **D15 daddy-long-legs 0x8004A2B0** fires in only 3 levels (7,052 hits);
  **A11 seed-as-weapon** in 10 levels but only 32 hits total.
- 18 write watches and 18 exec sites now have corpus-wide writer/reach data
  attached to their rows' open questions.

### Update 2026-08-10 (later): LEVEL02 re-recorded — corpus coverage now COMPLETE

The operator re-recorded LEVEL02_Tunnels after the original take was proven a
bad recording. The new take (v4, anchor hash verified, 36,397 frames, and
notably `armed_while_paused: false` unlike the old one) **replays clean**. Swept
and merged: the breadth artifact now covers **19 movies — all 16 levels plus the
3 bonus stages, with no exclusions.**

Revised counts: request **0 in 19 levels**, **1 (completion) in 15**, **2
(death) in 6**, **6 (bonus-exit) in 3**. Requests **3, 4 and 5 remain
unobserved anywhere** — still the largest residual in this dimension, and the
best argument for the hazard/damage recording backlog, since codes 1/4 of the
5-arm dispatch are the hazard arms F01 documents but nothing has yet exercised.

Also fixed en route: `tools/fixture_reference_sets.py` was created by the
control-plane work order and imported by three TRACKED tools without being
git-added. The `tracked_python_untracked_imports` gate caught it (3 entries,
cascading into 2 sha mismatches). A clean checkout would have failed to import
it. Tracked, regenerated, re-pinned — **closure debt now valid=true, 0 errors,
0 missing central pins, so roadmap §0 is cleared.**

### 2026-08-10 — E10 hazard clips recorded, swept, and CLASSIFIED (operator-corrected)

Operator recorded all 8 E10 hazard clips on pinned Interpreter (v4, anchors
verified); moved to `movies/Phase4/Interpreter/E10/` with embedded anchor paths
repaired. Swept with the 40-watch batched set; raws sha-pinned in
`~/Downloads/ABL-external-evidence/phase4_e10_hazards_2026-08-10/`.

**Hazard classification — instant-kill vs damage** (serves E10's open
"campaign-wide instant-kill-region census"). Observation plus operator
knowledge; the observation alone could not separate these:

| hazard | class | evidence |
|---|---|---|
| pit (LEVEL02 / 05 / 07) | **instant kill** | transition request **2** in all three, same writer `0x8004A9F8` |
| ground bird (LEVEL04) | **instant death** | request 2 (`0x8004A9F8`); operator-confirmed instant |
| acorn (LEVEL11) | **damage, 1 unit** | request 2 seen (`0x8004A8B8`) but ⚠️ **operator correction: that was health reaching zero from accumulated damage, NOT the acorn being instant-kill.** The clip deliberately takes repeated hits to show acorn movement. Its final hit was from a **mosquito**, not the acorn (also serves D07). |
| falling spikes (LEVEL05) | damage | no transition-request write at all |
| goo (LEVEL07) | damage | no transition-request write at all |
| falling rocks (LEVEL02) | damage | no transition-request write at all |

⚠️ **Instrumentation gap — these clips have NOT yet answered the question they
were recorded for.** They were recorded to exercise F01's dispatch arms 1/4
(region code → `player_damage_handler`). The sweep watched the *lifecycle* word
`0x800823A0`, which the damage handler has no reason to write — so the
spikes/goo/rocks silence is equally consistent with the arms firing and with
them not firing. Seeing the arms requires an **exec watch at the 5-arm dispatch
site inside `player_vertical_update`**, address not yet located. That is a short
static job plus a ~2-minute re-sweep (the clips total ~3,700 frames). **Next
session: locate the dispatch site, re-sweep these 8 clips.**

Requests 3/4/5 remain unobserved across everything (19 corpus movies + these 8).

## 2026-08-10 — D3 contract pilot FREEZE (pre-outcome)

This section freezes the fifth `complete_frontier` pilot before any D3 contract
outcome was inspected. Baseline is `b9bbd591233c4`; the immutable D3 universe
is the 140 IDs in
`analysis/phase4_discipline_assignment.json` (SHA-256
`87d4221cc1cdd92cf05de0756cc5c1a1f9f84e0faf59f24cd1fa5d6e031790cb`).
The decoded-table authority is `analysis/phase3_jr_tables.json` (SHA-256
`ed26a2496359a7c953011d3bb35b0a3f46e93314af9167cc00bb4e95dec0ceb5`).

Selection query, mechanically inherited from the assignment's fail-closed
resolution of the work-order wording: take the first eight D3 sites marked
`table_backed` by the predecessor compiled-C classification, ordered by PC,
because `phase3_jr_tables.json` contains no direct `jalr` site/load-cell match;
then take the first four still-unselected D3 IDs by PC. The result is 12/140
unique universe members:

1. `SCUS_942_88:0x80061ae4:jalr:v0`
2. `SCUS_942_88:0x80061b24:jalr:v0`
3. `SCUS_942_88:0x80061fac:jalr:v1`
4. `SCUS_942_88:0x80061fcc:jalr:v0`
5. `SCUS_942_88:0x80061ff4:jalr:v1`
6. `SCUS_942_88:0x80062010:jalr:v0`
7. `SCUS_942_88:0x8006202c:jalr:v0`
8. `SCUS_942_88:0x80062074:jalr:t0`
9. `SCUS_942_88:0x8004d1e8:jalr:v0`
10. `SCUS_942_88:0x80060c78:jalr:t2`
11. `SCUS_942_88:0x800620c0:jalr:v1`
12. `SCUS_942_88:0x800620e8:jalr:v1`

No target-membership, protected-set, writer, runtime-cross-check, or GO/NO-GO
result is recorded above. Those outcomes follow only after this freeze commit.

## 2026-08-10 — ITEM 1 DONE: the 5-arm region-code dispatch located and disassembled

Static, no replay. F01's binding described this dispatch; its **addresses were
never pinned**. They are now.

**Dispatch head — `player_vertical_update` @ 0x8004964C..0x800496A4**

```
80049644  jal 0x80038F38          ; sector_region_code_query(a1 = player+0x82)
8004964C  addu $v1,$v0,$zero      ; v1 = REGION CODE  <-- watch here, capture v1
80049650  beq  $v1,$zero,+        ; code 0 -> skip
8004965C  lh   $v0,0x23a0($v0)    ; [0x800823A0]
80049664  bne  $v0,$zero,+        ; single-shot guard (binding confirmed)
8004966C  beq  $v1,2 -> 0x800496C4
8004967C  beq  $v1,1 -> 0x800496A8
80049690  beq  $v1,3 -> 0x800496E8
80049698  beq  $v1,4 -> 0x80049718
800496A0  j 0x80049748            ; fallthrough
```

**Arm addresses — the exec-watch set for the E10 re-sweep**

| code | arm | behaviour |
|---|---|---|
| 1 | `0x800496A8` | `jal 0x8004A700` (a3=**1**), then `sh t1,0x50(sp)` |
| 2 | `0x800496C4` | sets `[0x800823A0]=1`, `[0x80082470]=0x17` (23), `jal sfx_dispatch(a0=0x3a)`, **and** `sh t1,0x50(sp)` |
| 3 | `0x800496E8` | identical completion tail to code 2 **without** the `sp+0x50` commit |
| 4 | `0x80049718` | guards on `player+0x7E` and `player+0x92`, then `jal 0x8004A700` (a3=**0**) |

⚡⚡ **Correction to F01's binding.** The binding says *"codes 1/4 →
`player_damage_handler` (hazard)"*. The bytes say codes 1 and 4 both call
**`0x8004A700` = `resident_level_transition_initiator`**, differing only in
`a3` (1 vs 0) and in code 4's two guards. Codes 2 and 3 are the pair that
differ only by the `sp+0x50` commit flag — not 2 vs 3 as "complete" and 1/4 as
"damage". The completion tail (request 1 / timer 23 / SFX 0x3a) is confirmed
exactly as documented. **The damage-handler attribution needs re-deriving**;
either the symbol name at 0x8004A700 is wrong or the binding is.

**Consequence for the E10 clips:** arm the four arm addresses plus 0x8004964C
(capturing `$v1`) and re-sweep the 8 hazard clips (~3,700 frames total). That
answers directly which codes the hazards produce — the question the sweep could
not answer while watching only the lifecycle word.

## 2026-08-10 — ITEM 2 STARTED, blocked on a locator (honest partial)

Goal: enumerate which collision region codes exist in **shipped terrain**
across all levels — serves E10's open "campaign-wide instant-kill-region
census", and would say whether dispatch arms 1/3/4 are reachable at all or are
dead code (the latter would bear directly on the item-2 bar decision).

`tools/edit_sector_region_code.py --list` does exactly the right thing, and
confirms LEVEL01: **sector 177, code 2, the only nonzero code** — matching
F01's binding exactly.

⚠️ **But the tool is LEVEL01-hardcoded and does NOT generalise.** The sector
source array is at chunk-32 local `0x36570` (stride 0x4c) in LEVEL01, where
chunk 32 is 236,944 B. LEVEL03's chunk 32 is **4,936 B**, so the same offset
yields `sectors 0..-2865` — nonsense. Every other level silently produced no
codes for this reason, not because their terrain has none.

**What Item 2 actually needs:** a per-level *locator* for the sector source
array (or the converter's own view of it). The converter is
`FUNC_80030F60`, and the two region-code writers `0x80030F94` / `0x80031264`
perform the authored `src+0x2C` → runtime `+0x2E` copy — so the array base is
computed there and can be recovered per level rather than assumed. Do that
first, then re-run the census.

**Do not read the current per-level silence as "no codes."** That would be the
same class of error as reading a silent watch as a bounded negative.

## 2026-08-10 — E10 re-sweep with the dispatch-arm watches: codes 1 and 4 OBSERVED

Eight E10 clips re-swept with exec watches on the arm addresses pinned in
Item 1. Raws in `ABL-external-evidence/phase4_e10_hazards_2026-08-10/arms_*.json`.

| clip | arm fired | hits |
|---|---|---|
| pit LEVEL02 / 05 / 07 | **code 1** | 1 each |
| goo LEVEL07 | **code 4** | 74 |
| spikes L05, falling rocks L02, acorn L11, ground bird L04 | none | — |

**Both previously-unobserved hazard arms are now observed.** Cross-referencing
the earlier lifecycle sweep resolves what each does:

- **code 1 → pits.** Fires once, calls `0x8004A700` with **a3=1**, and the
  lifecycle sweep showed pits emit transition **request 2 (death)**. So code 1
  is the *instant-death terrain transition*.
- **code 4 → goo.** Fires continuously while grounded in it (74 hits), calls
  the same `0x8004A700` with **a3=0**, and the lifecycle sweep showed goo
  emits **no transition request at all**. So code 4 is *damage without
  transition*.

⚡ **Binding resolved.** F01 records "codes 1/4 → `player_damage_handler`".
Both arms in fact call `resident_level_transition_initiator` (0x8004A700), and
**`a3` selects the behaviour**: a3=1 death, a3=0 damage-only. The binding's
*intent* (hazard) was right; the named callee and the mechanism were not.

⚡ **Spikes, falling rocks, acorn and ground bird fire NO region-code arm** —
they damage through a different mechanism entirely (object/actor collision,
not terrain region codes). That sharpens E10's hazard taxonomy into two
distinct families.

⚠️ **My head-capture was wrong.** I armed `0x8004964C` capturing `$v1`, but
that instruction *is* `addu $v1,$v0,$zero` — the capture reads the value
BEFORE the write, so the logged "region codes" (0x77, 0x1F7, 0x23E …) are
stale register contents, not codes. **Capture `$v0` there instead.** The arm
watches are unaffected and carry the result above.

## 2026-08-10 — D3 contract pilot outcome: reviewed negative (0/4 contracts, 0/12 sites)

The pre-outcome sample above was committed first at `3381f0dcd4a7f`. The
contract pass then re-read that exact commit, the immutable 140-site D3
assignment, all 21 hash-verified images, the 128-ID protected set, retained
tuple corpus, typed-state and ABI ledgers, and the earlier two-C guarded-table
proof. No live or instrumented replay was performed.

### Per-site outcomes (recorded before the decision)

Every row fails part 1, the universal membership/writer invariant. Therefore
none may claim part 2 against a *proved membership set*, even where a known or
observed candidate set has zero protected intersections.

| # | site | byte-owned source | contract | outcome |
|---:|---|---|---|---|
| 1 | `SCUS_942_88:0x80061AE4:jalr:v0` | `0x80061AD8 = 0x8C42FBC4` | shared cell | membership not proved |
| 2 | `SCUS_942_88:0x80061B24:jalr:v0` | `0x80061B1C = 0x8C42FBC4` | shared cell | membership not proved |
| 3 | `SCUS_942_88:0x80061FAC:jalr:v1` | `0x80061FA0 = 0x8C63FBC4` | shared cell | membership not proved |
| 4 | `SCUS_942_88:0x80061FCC:jalr:v0` | `0x80061FC0 = 0x8C42FBC4` | shared cell | membership not proved |
| 5 | `SCUS_942_88:0x80061FF4:jalr:v1` | `0x80061FE8 = 0x8C63FBC4` | shared cell | membership not proved |
| 6 | `SCUS_942_88:0x80062010:jalr:v0` | `0x80062004 = 0x8C42FBC4` | shared cell | membership not proved |
| 7 | `SCUS_942_88:0x8006202C:jalr:v0` | `0x80062020 = 0x8C42FBC4` | shared cell | membership not proved |
| 8 | `SCUS_942_88:0x80062074:jalr:t0` | `0x80062044 = 0x8D08FBC4` | shared cell | membership not proved |
| 9 | `SCUS_942_88:0x8004D1E8:jalr:v0` | `0x8004D1E0 = 0x8E02007C` | object `+0x7C` | membership not proved |
| 10 | `SCUS_942_88:0x80060C78:jalr:t2` | `0x80060C74 = 0x240A00B0` | BIOS/ingress | entry-scoped `B0`, global ingress open |
| 11 | `SCUS_942_88:0x800620C0:jalr:v1` | `0x800620B4 = 0x8C63FBC4` | shared cell | membership not proved |
| 12 | `SCUS_942_88:0x800620E8:jalr:v1` | `0x800620DC = 0x8C63FBC4` | shared cell | membership not proved |

The 22-site hoisted-load idiom control has zero source-PC intersections with
these 12 rows. Ten shared-cell rows were silent in the retained corpus; that
silence is not a writer census. The object-field row observed 10 target PCs;
the BIOS row observed `0x000000B0`. Those observed/candidate sets have zero
intersections with the protected IDs, but observation remains falsification or
corroboration only.

### Per-contract findings and wall labels

1. **Shared dispatch cell `0x8007FBC4`: not established; technique-shaped.**
   Independent C decoding proves `SetDumpFnt` materializes `0x80061668`
   (`FntPrint`) at `0x80060FD4/0x80060FD8` and stores it with
   `0x80060FE8 = 0xAC22FBC4`. That is one safe known writer, not a census.
   Re-running `region_provenance.c` over all 21 images reproduces **4,266**
   unresolved possible stores, including **2,244** full-width stores. A
   region-sensitive alias/writer-value engine could clear them; current
   machinery cannot. The proof is immune to the `0x80018CBC` failure because
   it rejects rather than completes the writer universe.

2. **Object-field provenance: not established; technique-shaped.** The
   dispatch is exactly `lw v0,0x7C(s0)` followed by `jalr v0`. Retained data
   saw 1,286 actor records, a 60.8% non-null hit rate, nine field handlers in
   that survey and 10 target PCs in the merged tuple corpus. None is promoted
   to a universal domain. The relevant typed-state owner binding is rejected,
   no exhaustive `+0x7C` writer/type invariant exists, and the shared ABI wall
   remains **1/867** consumed argument domains known. Field-sensitive object
   typing and writer closure could clear it.

3. **BIOS/ingress exception: not established; technique-shaped.** Primary and
   independent C agree that every path from declared owner entry `0x80060C64`
   reaches `jalr t2` with the local candidate set exactly `{0x000000B0}`; all
   14 retained observations agree. That is still not a global ingress
   contract: both implementations begin at the owner entry and cannot exclude
   an indirect transfer directly to `0x80060C78`, after the defining
   instruction. Refusing to lift the local reaching definition is the explicit
   immunity control. A whole-program ingress/vector contract could clear it.

4. **Dynamic-module boundary: not established; technique-shaped.** This
   contract contributes zero sites to the frozen 12 and receives no sample
   credit, but it remains a named global prerequisite. Independent bytes prove
   `MEMORY:0x800B970C` uses `sltiu a0,8`, a bypass branch, four-byte stride and
   a post-guard load from exactly eight slot occurrences at
   `0x800B57B4..0x800B57D4`. The pristine slots contain frontend continuations;
   retained runtime later observed `0x800CABE0` / `0x800CABE4` with 1,244 /
   1,247 hits, outside every static code extent. The tuple artifact retains
   neither `memory.getResidency` nor `transferLog` per hit. Worse, pinned FMV
   ownership gives the same virtual `0x800CABE0` address a data role under
   `FMV.BIN` residency. A raw address therefore cannot identify its module.
   A finite loader-byte census joined to residency/transfer identity could
   clear this; static-slot enumeration cannot.

All four walls are **technique-shaped**, but the techniques are now concrete
prerequisites rather than another caller/target enumeration pass: shared-cell
alias closure, actor-field typed writers, whole-program ingress, and
loader/residency identity.

### Mandatory decision (after the per-site and per-contract record)

**PILOT DECISION: NO-GO. Exactly 0/4 contracts are fully established and
0/12 frozen sites clear both required parts; GO required at least 1/4 and at
least 3/12.** Runtime coverage is 2/12 observed and 10/12 silent. There is no
accepted proof for runtime to falsify, so the runtime-clean condition is
`NOT_ESTABLISHED_EMPTY_PROOF_SET`, never a vacuous pass.

The indirect residual remains **179 → 179**: 10 frozen rows remain behind the
shared-cell contract, one behind object-field provenance, and one behind the
BIOS/ingress contract. The dynamic loader boundary is a named non-sample
residual at `MEMORY:0x800B970C` and does not alter that arithmetic. F01 remains
`partial`; item 2 remains `not_met`; no gate, mechanics baseline, tuple
artifact, or analysis chain moved.

`complete_frontier` still has a technical avenue in principle because all four
walls are technique-shaped, but **this result does not fund a sixth attempt
using the current target-enumeration machinery**. Reopen only when at least one
named prerequisite engine exists and can prove a writer/type/ingress/loader
universe rather than enumerate another lower bound.

Receipt: `analysis/phase4_d3_contract.json`
(`abl-phase4-d3-contract/1`). Reproduce with:

```bash
python3 tools/phase4_d3_contract.py --check
pytest -q tests/test_phase4_d3_contract.py \
  tests/test_phase4_discipline_assignment.py \
  tests/test_phase4_discipline_pilot.py \
  tests/test_phase4_address_taken_pilot.py
```

The focused suite passes 34/34. The driver rebuilds three strict C probes and
the region analyzer; the new independent word probe owns all 12 source/site
words, the `SetDumpFnt` constant publication, and the eight-slot frontend
extent. The primary and independent dataflow probes agree at every sampled
site.

### Phase 4 documentation continuity audit

The prior ratchet handoffs are already banked in this Phase 4 experiment and
did not need duplicate sections: `source_closure verified: honest measurement,
INFLATED label (3.7% match)`, `original_interfaces ledger: 764/764 rows, 0/764
fully resolved`, and `control-plane data quality: closure ledger unblocked, no
promotion`. The earlier caller-domain, address-taken, target-exclusion, and
discipline-proof freezes/results plus their Hard-Truth dispositions are also
present. This D3 result extends that same ordered evidence chain.

## 2026-08-10 — D3 contract reviewed negative: Hard-Truth ACCEPTED

James, the fresh detached Hard-Truth verifier, returned exact
`status="accepted"` for candidate
`619cac8d604f55cb4230fa7e7fe668c53dad4ac7`, with `gaps=[]` and
`required_inputs=[]`. This banks the reviewed negative, not a D3 proof or an
F01 status change.

The independent audit re-derived all 12 source/site/delay words from pristine
bytes; the 140/179 site arithmetic; the 128-ID protected union; the
`SetDumpFnt → FntPrint` publication; all 21 region-provenance runs and their
4,266 / 2,244 residual identities; actor `+0x7C`, ABI 1/867 and BIOS `B0`
limits; the eight frontend slots and `0x800CABE0/4` runtime counts; the missing
residency/transfer identity and FMV same-address data role; and zero candidate
protected intersections without promoting them. It also confirmed all four
technique-shaped labels, the exact **0/4, 0/12, 179 → 179** decision, forbidden
surfaces unchanged, freeze/outcome ordering, and the prior ratchet sections.

Fresh detached validation passed 327/327 pristine identities and 34/34 focused
tests. Post-commit extent regeneration was byte-identical at SHA-256
`2aa349357294db7aa003ea45130937a98420fe95abab2a7e0ca01faac5c291bb`:
1,081 files, 2,150 declarations, 17/17 reviewed truncations, zero new. The two
failures in the wider 51/53 regression sample were independently reproduced as
pre-baseline, candidate-unchanged debt (the existing C15 movie-priority
projection and stale knowledge-report pins), not D3 regressions.

**Banked consequence:** do not fund another current-style target-enumeration
campaign. `complete_frontier` retains an avenue only if one of the four named
prerequisite engines is built. F01 remains `partial`; item 2 remains `not_met`.

## 2026-08-10 — TASK-QUEUE item 2 DONE: campaign-wide region-code census, disc-side, 16/16 scenes

⚠️ **"Item 2" here is the 2026-08-10 task queue's second entry (the census),
NOT the DoD's item-2 bar.** The DoD item 2 is frontier *enumeration*
(`complete_frontier`) and is untouched by this work. **No dimension moved, no
status changed, `mechanics_baseline.yaml` not edited** — F01 remains `partial`
with the DoD item 2 `not_met`. Only a fresh detached verifier may bank a
status change.

The blocker recorded above ("Item 2 needs a per-level locator for the sector
source array") was **already solved and committed** — by E02's collision round
trip on 2026-08-04. `analysis/phase4_e02_collision_roundtrip.json` binds every
one of the 16 scenes to its own container **and** the array's offset inside it,
`failing_levels: []`, proven by an independent C reimplementation of the
converter diffed against save RAM. F01 never connected to it. No locator
engineering was required; the work was to stop hardcoding LEVEL01's pair and
read the field.

⚠️ **The pattern, again: the artifact I needed already existed.** Same shape as
`phase3_jr_tables.json` (869 indirect targets the static index never read).
Before building a locator/census/extractor, grep `analysis/` for one.

### New: `tools/phase4_e02_disc_region_code_census.py` → `analysis/phase4_e02_disc_region_code_census.json`

Per scene: re-locate the authored array in its own container, read the authored
region code at **src+0x2C straight from the container bytes**, diff against the
runtime table's **+0x2E** for the same index.

- **16/16 scenes located; 3,235 authored sectors compared; 0 disagreements.**
  Before today the disc side was cross-checked for **LEVEL01 alone**.
- **Self-validating**: the tool independently derives LEVEL01 = **chunk 32,
  local 0x36570** — exactly the pair that had been hardcoded. The one value
  known to be right is reproduced from scratch.
- **Not circular**: the array alignment is fixed by sector ORIGINS (+0x08), never
  by the code at +0x2C. The field being checked took no part in choosing the
  alignment.
- The 720 runtime-registered tail sectors carry **zero** nonzero codes
  (`runtime_nonzero_beyond_authored` empty in all 16), so the authored prefix is
  the whole code population — the disc census is complete, not a subset.

### Why the old tool reported nothing, and what was actually wrong

`edit_sector_region_code.py` hardcoded `(chunk 32, local 0x36570)`. **Both
coordinates vary per level** — the chunk alone ranges over 27, 28, 29, 30, 31,
32, 33, and four scenes keep the array in a flat `.ALL` container with no chunks
at all. The earlier diagnosis ("LEVEL03's chunk 32 is 4,936 B") named the right
symptom but only half the cause: LEVEL03's array is in **chunk 28**, not a
differently-sized chunk 32.

Now hardened: unknown container ⇒ **hard error listing the known ones**, never
silence. LEVEL01 keeps its independently established constants and the locator
must agree with them or the tool refuses — so the runtime census's LEVEL01
cross-check stays an outside check rather than a restatement of itself.

### The census

| level | scene | container | chunk | local | authored | nonzero (sector:code) |
|---|---:|---|---:|---|---:|---|
| training | 17 | LEVEL07/LEVEL1.RAW | 33 | `0xbd80` | 25 | 24:3 |
| stage01_anthill | 1 | LEVEL01/LEVEL.RAW | 32 | `0x36570` | 178 | 177:2 |
| stage02_tunnels | 3 | LEVEL03/LEVEL.RAW | 28 | `0x36890` | 589 | 570‑578:1, 579:3 |
| stage03_council_chamber | 2 | LEVEL02/LEVEL.RAW | 28 | `0x120e0` | 100 | — |
| stage04_cliffside_canyon | 6 | LEVEL06/LEVEL.RAW | 30 | `0x2915c` | 132 | 131:3 |
| stage05_riverbed_run | 10 | LEVEL10/LEVEL.RAW | 31 | `0x1d2ac` | 298 | 292‑296:1, 297:3 |
| stage06_birdnest | 11 | LEVEL01/LEVEL1.RAW | 29 | `0xd99c` | 75 | — |
| stage07_city_entrance | 4 | LEVEL04/LEVEL.RAW | 31 | `0x2cdfc` | 229 | 219:1, 220‑225:4 |
| stage08_city_square | 5 | LEVEL05/TERRAIN.ALL | flat | `0x28034` | 333 | — |
| stage09_bug_bar | 14 | LEVEL04/LEVEL1.RAW | 27 | `0x41dc` | 1 | — |
| stage10_clover_forest | 7 | LEVEL07/TERRAIN.ALL | flat | `0x1d34c` | 138 | — |
| stage11_the_tree | 12 | LEVEL02/TERR1.ALL | flat | `0x30cd4` | 262 | — |
| stage12_battle_arena | 13 | LEVEL03/LEVEL1.RAW | 31 | `0x5b04` | 12 | — |
| stage13_anthill_two | 9 | LEVEL09/LEVEL.RAW | 31 | `0x2f2e4` | 176 | — |
| stage14_riverbed_flight | 8 | LEVEL08/LEVEL.RAW | 31 | `0x2b1b0` | 335 | 334:2 |
| stage15_canyon_showdown | 15 | LEVEL05/LEVEL1.RAW | 31 | `0x29c54` | 352 | — |

Campaign histogram over authored sectors: **0:3208, 1:15, 2:2, 3:4, 4:6** — the
nonzero counts equal the runtime census's exactly.

### ⚡ Code 3 is NOT dead — it is the ordinary exit code of four stages

The question this item was funded to answer:

> **Code 3 exists in shipped terrain: 4 sectors, in 4 different scenes.**

| scene | container | sector | runtime origin |
|---:|---|---:|---|
| 17 training | LEVEL07/LEVEL1.RAW | 24 | (480, −24096, 268736) |
| 3 tunnels | LEVEL03/LEVEL.RAW | 579 | (1864160, 35520, 2916480) |
| 6 cliffside canyon | LEVEL06/LEVEL.RAW | 131 | (−1719040, 39424, −219488) |
| 10 riverbed run | LEVEL10/LEVEL.RAW | 297 | (135168, −896, 2075328) |

So "code 3 has never been observed" was a statement about the **replay corpus**,
which is LEVEL01-centric — and LEVEL01's exit is code **2**. To observe arm 3
firing, replay the exit of training, tunnels, cliffside canyon or riverbed run.
Nothing about the arm is unreachable. E02 reached the same conclusion from the
other side on 2026-08-03 (its LEVEL02/04/05 be-here proofs are code-3 sectors).

### E10's campaign-wide instant-kill-region census — served

Code 1 (pits → `0x8004A700` a3=1 → transition request 2 = death): **15 sectors,
3 scenes**, and nowhere else in shipped terrain.

| scene | container | sectors |
|---:|---|---|
| 3 tunnels | LEVEL03/LEVEL.RAW | 570–578 (9) |
| 10 riverbed run | LEVEL10/LEVEL.RAW | 292–296 (5) |
| 4 city entrance | LEVEL04/LEVEL.RAW | 219 (1) |

Code 4 (goo → a3=0, damage only, and `checkpoint_save` bails): **6 sectors, all
in scene 4**, 220–225. Code 2: 2 sectors (anthill 177, riverbed flight 334).

**Structural observation, true in all 7 code-bearing levels:** every nonzero
code lives in a single contiguous band at or near the END of the authored array.
The hazard/exit sectors are appended after the terrain proper — useful for the
level editor, and a cheap sanity check on any future edit.

### Universe named, and what is NOT covered

Valid scene ids are **1..17** (`0x8003CF84`: `addiu v1,s4,-1` / `sltiu v0,v1,17`).
The progression table `0x80077FA0` lists 16 of them. The census covers those
**16 of 17**. The uncovered one is **scene 16**, absent from the progression
table and reachable only through the force flag `[0x8008225C]` (map/results); it
has no save anchor, so neither census sees it. That is a named residual, not a
silence.

### Independent re-derivation of a landed claim (discipline check)

Re-derived the code-2 vs code-3 difference from the image bytes alone. Writes to
the commit flag `sp+0x50` in `fcn.80048138` are an exact set of three:
`0x800481BC` (zero-init), `0x800496C0` (code‑1 arm, =1), `0x800496E4` (code‑2
arm, =1); one read at `0x80049748`. So codes **1 and 2 commit**, codes **3 and 4
do not** — the commit block at `0x8004975C..0x8004978C` folds the pending
delta into the player position and clears `player+0x82`. This **confirms** the
refinement already banked in the exit-trigger matrix. The older E02 phrasing
"code 3's dispatch body is identical to code 2's" is the one that needs
retiring: the shared *effect* (latch←1, fade←23, SFX 58) is identical, the arms
are not.

### ⚡ Bonus, from the same re-derivation: "code 1 = instant death" is now STATIC

Chasing the `a3` question the handoff flagged, `FUNC_8004A700` turns out to hold
**two** stores of the transition request `[0x800823A0]`, and `a3` alone picks
which one runs:

| `a3` | path | request-2 store | fade | health |
|---:|---|---|---:|---|
| `0` (code 4, goo) | `0x8004A740`: knockback, i-frame check `0x800A6592`, health `−1` at `0x8004A880` | `0x8004A8B4`, **conditional** on `0x8004A890 bgez` failing | 60 | decremented |
| `≠0` (code 1, pits) | `0x8004A828` → `0x8004A90C` → `0x8004A998` → `0x8004A9E8` | `0x8004A9F4`, **unconditional** | 23 | untouched |

A pit therefore kills **by construction**, not by draining health: the `a3≠0`
path skips knockback and invincibility outright. That converts the E10 runtime
observation into a static proof, and refines two earlier statements:

- Canon said "the request word only reaches 2 after the health decrement leaves
  health negative". True for `a3=0` only.
- The handoff said "`a3` selects death vs damage". Directionally right, but `a3`
  is a small **enum**, not a boolean — `s4` is further compared against `3`
  (`0x8004A998`) and `2` (`0x8004A9B8`) to pick SFX `0x49` and power-word bits.

Both corrected in [[Level_Goal_and_Exit_Trigger_Matrix]].

## 2026-08-10 — D3 independently re-verified here (not taken on report)

The acceptance above was banked on the detached verifier's report. Re-ran the
Task-1 verification pattern directly against the artifact and the pristine
image, because passing through on another agent's word is the one thing that
pattern exists to prevent.

| leg | result |
|---|---|
| freeze precedes outcomes | `3381f0d` is an ancestor of `ab7c945`; the freeze section carries the 12 IDs + selection query and **no** membership, protected-set, writer, runtime or GO/NO-GO result |
| bytes re-derived | **12/12** frozen site source words match `SCUS_942.88` exactly; `SetDumpFnt` 3/3 words match |
| forbidden paths | commits touched the log, the Typed State Compiler playbook, the D3 artifact/tool/test and the extent audit — **no** frontier / census / seed / gate / typed-state artifact |
| fractions | recomputed from row data: 0/4 contracts, 0/12 proved, 2/12 observed, 4,266 unresolved / 2,244 full-width over 21 images, 179 → 179, `status_movement_authorized: false` |

**Extra leg, not required by the pattern but worth adding to it: the freeze's own
selection rule is mechanically reproducible.** `next_site_ids` are *exactly* the
first four unselected D3 IDs by PC, they do not intersect the eight table-backed
picks, and the frozen 12 is their exact union. Sample-shopping is the failure a
freeze exists to prevent, and until now nobody had checked that the stated
selection query actually produces the frozen sample. **Add this leg to the
Task-1 pattern.**

One discrepancy surfaced and it was **mine**: I first recomputed the dispatch
cell as `0x8005FBC4` by taking the *value* register's `lui` (`lui $v0,0x8006`)
instead of the address base's. The base is `lui $at,0x8008` at `0x80060FE4`,
so `sw $v0,-0x43c($at)` → `0x8007FBC4`, as the artifact says. ⚠️ **A `lui`
immediately preceding a store is not necessarily that store's base register.**

## 2026-08-10 — `source_closure` UN-PARKED by operator decision; work order v2 issued

The 2026-08-10 park (*"do not send Codex back into this grind now"*) is
deliberately reversed by the operator. Recording it explicitly so the reversal
is a decision with a reason, not a drift.

⚠️ I had recommended resuming `source_closure` **without having read that park**
— the recommendation contradicted a banked decision. Corrected on the spot.
**Read the log's own decisions before recommending the next step.**

`engineering-specs/phase4-f01-source-closure-work-order-v2.md` supersedes v1.
It changes the method rather than retrying the same run:

- **The region gate.** v1 said "match region by region"; that was measurement
  and did not bind, so all six regions returned `near_miss` simultaneously —
  the signature of whole-function authorship scored afterwards. v2: *region N
  must reach ZERO before N+1 is attempted*, worked in address order so
  addresses stay aligned. **The partition may not be redrawn** — it is the one
  already committed in `analysis/phase4_f01_source_closure.json` (6 in-extent
  regions, verified here to cover exactly 1,501 words), so it cannot be
  gerrymandered after the fact.
- **Progress metric** is `K of 6 regions closed; W words remaining in K+1` —
  never a whole-function percentage. Flattening produced "3.7%", which reads as
  progress and is not.
- **"Near-miss" is defined**: size exactly 6,004 **and** ≤ 16 differing words —
  the domain `dc_permute` can actually close. v1's `NEAR_MISS` on 56/1,503 is
  the precedent the rule exists to prevent.
- **Phase 0 gates authorship** on the two walls that make region 1 unclosable:
  the prologue diverging from the second instruction onward, and the `$gp` mix.

### Head start banked for the executor: the `$gp` wall is region-1-shaped, and it is not `-G`

Enumerated the `$gp`-relative accesses in `[0x80048138, 0x800498AC)`: **17
accesses over 5 offsets** — `0x502`→`0x8008229A` (h, 4), `0x618`→`0x800823B0`
(h, 6), `0x63C`→`0x800823D4` (w, 2), `0x69C`→`0x80082434` (w, 2),
`0x73C`→`0x800824D4` (w, 3). **Ten of the 17 are inside region 1**, so the gate
starts exactly where this wall is densest.

⚡⚡ **The discriminator is not object size.** In this same function
`[0x800823A0]` is read as a halfword **absolutely** (`lui $v0,0x8008` /
`lh $v0,0x23a0($v0)` at `0x80049658`/`0x8004965C`) while `[0x800823B0]` — same
width, 16 bytes away — is `$gp`-relative. Two same-sized neighbours in one
function taking different addressing modes rules out a `-G` size threshold and
points at **provenance: which objects the translation unit defines versus
merely references.** That is the first hypothesis v2 tells the executor to
falsify, and it generalises past F01 to every remaining decomp target.

## 2026-08-10 — `source_closure` v2 pre-outcome execution freeze

This is the mandatory freeze for
`engineering-specs/phase4-f01-source-closure-work-order-v2.md`. It was written
before running the v2 compiler probe, inspecting a newly generated comparison,
or making any source change.

- issued baseline commit: `7ea89416dfaff1d4e9d8498ee806d24b23e41e6f`
- issued baseline `git status --short`: **116 lines**, SHA-256
  `dbb9bee516c80b08983dd3cb4cafdfb799a939818771c90a899407c0d31b1616`
- the 116 entries are pre-existing operator work and are outside this order
- frozen source: `src_re/player_vertical_update_80048138.c`, SHA-256
  `d6c1f29a7702e3c05e947a1574565e21f756c887f8d0aefb9b269737199d56cf`

Pinned compiler contract, independently observed before execution:

| component | pin | observed |
|---|---|---|
| GCC | `gcc2.7.2-psx`; `-O2 -G0 -mcpu=3000 -fno-builtin`; placement `0x80048138`; `small_data=false`; `cleanroom_unprototyped` | exact contract selected |
| `cc1` SHA-256 | `0359379289db8e3904b8ed3b25b422ca631c8d71ab2f543d533c39ed2967764f` | same |
| `cpp` SHA-256 | `e3e1e53a9c19a6c1defa76da40cb50b922d5c4711e41b637211fbaf3fae60df4` | same |
| maspsx commit | `42b862c988fe7a13fe4e7ac0ebec90ed6b9fb763` | same |
| maspsx entry SHA-256 | `d170463b0c519a825db97d3f30ffbe0228e4cf642de2dc64fb30f90f118c2b0c` | same |
| maspsx flags | `--dont-expand-li --expand-div` | exact contract selected |

Frozen region gate; the order, names and boundaries may not change after an
outcome is known:

| N | region | start | end exclusive | words |
|---:|---|---|---|---:|
| 1 | `controller_history_and_spin` | `0x80048138` | `0x800483B0` | 158 |
| 2 | `movement_parameters_and_status_input` | `0x800483B0` | `0x80048514` | 89 |
| 3 | `timers_and_special_vertical_modes` | `0x80048514` | `0x80048B20` | 387 |
| 4 | `jump_dive_and_landing` | `0x80048B20` | `0x80048E9C` | 223 |
| 5 | `horizontal_steering_and_projection` | `0x80048E9C` | `0x80049544` | 426 |
| 6 | `collision_fall_recovery_and_epilogue` | `0x80049544` | `0x800498AC` | 218 |

The next action is Phase 0 and then region 1 only. Region 2 is unauthorized
unless region 1 reaches zero differing words. This freeze contains no new
compile measurement, region status or campaign verdict.

## 2026-08-10 — `source_closure` v2 outcome: NO-GO at region 1

**Gate result: 0 of 6 regions closed; 70 words remain in region 1.** Regions
2–6 were not attempted. This is the v2 stop rule, not a whole-function progress
percentage and not a renamed near-miss.

The two Phase 0 prerequisites did clear:

- **Frame/register map:** the C compile now matches the retail `0x100` frame,
  all callee-save slots, stack locals `sp+0x30/38/40/48/50/58`, and the first
  **54 words exactly** (`0x80048138..0x80048210`). In particular the old second
  instruction mismatch is gone: compiled and retail both carry `0xAFB100DC`
  (`sw s1,0xDC(sp)`).
- **Mixed `$gp`:** C lvalues based on the ABI `$gp` register reproduce exactly
  **17 accesses** at offsets `0x502/0x618/0x63C/0x69C/0x73C`, with counts
  `4/6/2/2/3`, widths `h/h/w/w/w`, and **10** accesses in region 1. No inline
  or hand ASM participates.

The ordered discriminator probes falsified the initial provenance hypothesis
cleanly. Minimal `extern`, `extern + .sdata`, translation-unit definition, and
translation-unit `.sdata` definition variants all produce the same cc1 body;
the pinned `-G0` assembler tail emits `HI16/LO16`, never `GPREL16`. The
`source`, `cleanroom_prototyped`, and `cleanroom_unprototyped` declaration
profiles compile byte-identically. A diagnostic `-G8` run cannot link because
it over-selects distant `0x800A/0x800B` objects and overflows `R_MIPS_GPREL16`;
the retained compiler contract therefore remains unchanged at `-G0`.

The retained compile is **5,948 bytes**, so it fails the 6,004-byte prerequisite
for `NEAR_MISS` before the ≤16-word test is even relevant. `dc_permute` is not
eligible. Region 1 improved monotonically from 147 to 70 differing words, but
zero is the only close condition.

**Binding wall:** `extent_and_cfg_shape`, specifically the
`region_1_source_expression_order_and_register_lifetime` subproblem, labelled
**technique-shaped**. The remaining history-loop and spin-reset C expressions
schedule and allocate differently under the pinned compiler. That is a limit
of this source-recovery/search technique, not evidence that a binary which
originated as C structurally forbids a C proof. It is nevertheless a hard
NO-GO for this order because the frozen gate prohibits moving on.

Banked evidence:

- `analysis/phase4_f01_source_closure.json`, schema
  `abl-phase4-f01-source-closure/2`
- `python3 tools/phase4_f01_source_closure.py --check` reproduces the compiler
  probes, receipt, frame witnesses, `$gp` census, and gate result
- `pytest -q tests/test_phase4_f01_source_closure.py` → **10 passed**, including
  fail-closed tests for a false region close, premature later-region work, and
  the exact `NEAR_MISS` definition

`source_closure` remains **partial** and no F01 status movement is authorized.

## 2026-08-10 — James hard-truth acceptance

James independently audited exact candidate
`2076de64ca79d1f7b40d5b88dd977e9a3c55ff76` from a separate clean,
centrally hash-valid snapshot and returned `accepted: true`, with no gaps and
no required inputs.

The audit independently reproduced the freeze ancestry and ordering, all
1,529 centrally declared input pins and 327 staged pristine inputs, the
5,948-byte compiled body and 6,004-byte retail extent, the
129-equal/1,372-different/14-retail-only arithmetic, the 54-word exact prefix,
frame and mixed-`$gp` witnesses, ordered compiler probes, and the fail-closed
region gate (`0 of 6` closed; 70 words remain in region 1). The retained
artifact regenerated byte-identically with SHA-256
`bb77451d3cb7542ecda60e3b00214c18627701baf7307d8ce74fbe026cdc848b`, and
the final relevant regression selection passed **63/63**.

This acceptance certifies the evidence and the honest **NO-GO** outcome. It
does **not** promote `source_closure`, authorize later-region scoring, or move
F01 status.

## 2026-08-10 — source_closure v2 NO-GO independently verified here: ACCEPTED, and the gate worked

Re-ran the verification pattern against the v2 deliverable rather than accepting
the detached verifier's summary. **The NO-GO is correct and the receipt is
honest.**

| leg | result |
|---|---|
| freeze precedes outcomes | `10339263` is an ancestor of the accepted candidate `2076de64`; the freeze commit contains only the log section |
| **partition not redrawn** | all 6 regions byte-identical to the v1 committed partition, covering exactly **1,501 words** — the anti-gerrymander check v2 was written to enable |
| bytes re-derived | **70/70** region-1 `retail_word` values match the pristine image; **0** listed "differences" are actually equal |
| gate self-consistency | `words_remaining_in_active_region` 70 == recomputed 70; regions 2–6 `not_attempted_gate_blocked` with `words_remaining: null` — fail-closed, not scored |
| exact-prefix claim | `0x80048138..0x80048210` = 54 words recomputed; the lowest differing address in region 1 is **exactly `0x80048210`**, so the claimed-exact prefix really is exact |
| forbidden paths | only the five work-order-owned files; `analysis/mechanics_baseline.yaml` **untouched**; no status movement |

**Mutation-tested the delivered tests** — the check that matters, because a
gate test that passes vacuously is worse than none. Five lies inserted into the
receipt, each independently:

| injected lie | caught? |
|---|---|
| region 1 `closed: true` while 70 words differ | ✅ 3 failed |
| relabel a 1,372-word diff as `NEAR_MISS` | ✅ 3 failed |
| `regions_closed: 6` | ✅ 3 failed |
| shrink region 2 (redraw the frozen partition) | ✅ 2 failed |
| `source_closure_eligible_for_promotion: true` | ✅ 3 failed |

The gate is real.

### The NO-GO undersells genuine movement — both Phase-0 walls CLEARED

v1's two blocking walls are gone, which is what made the region-1 number
meaningful at all:

- **Prologue / frame map: `cleared`.** Retail frame 256 == compiled 256, with
  `s0..s6`, `$ra`, `$fp` and every local at the exact retail offsets. v1 diverged
  at the *second instruction*; v2's first **54 words are exact**.
- **Mixed `$gp` addressing: `cleared`.** 17/17 accesses reproduced, 10 of them in
  region 1 — matching the independent enumeration banked with the work order
  exactly (17 accesses, 5 offsets, `$gp = 0x80081D98`, 10 in region 1).
  Implementation: *"C lvalues based on the ABI `$gp` register; no inline or hand
  ASM"* — so it counts as `source_closure`, which hand-ASM would not have.

Region 1 moved **11/158 → 88/158** correct words. Whole-function differing words
1,447 → 1,372. The residual wall is new and narrower:
`region_1_source_expression_order_and_register_lifetime`, **technique-shaped** —
the history-loop and spin-reset expressions schedule and allocate differently.

### ⚠️ My banked `$gp` hypothesis was FALSIFIED — correctly, by direct probe

The work order ranked three hypotheses. All three were tested **in the stated
order** and all three failed:

1. `declaration_profile` — `source`, `cleanroom_prototyped` and
   `cleanroom_unprototyped` produce **byte-identical** output. The knob is inert.
2. **definition-vs-`extern`/`.sdata` provenance — falsified.** Every variant
   (`extern_reference`, `extern_with_sdata_attribute`,
   `translation_unit_definition`) emits `R_MIPS_HI16`/`R_MIPS_LO16` and **no
   `GPREL16`** under the pinned `-G0` tail. This was *my* first-ranked
   hypothesis, argued from the `0x800823A0` / `0x800823B0` same-width neighbour
   split. The split is real; my explanation for it was wrong.
3. `nonzero_g` — link error: global `-G8` over-selects distant `0x800A`/`0x800B`
   objects, small-data section too large. **`contract_changed: false`** — the
   pinned contract was correctly left alone rather than bent to fit, exactly as
   the work order required.

⚡ **The enumeration I banked was right; the causal story was not.** Naming three
falsifiable hypotheses in priority order was still the useful part — it got all
three killed cheaply and by measurement, instead of one being assumed. **Rank
hypotheses so they can be shot down in order; do not rank them so the favourite
survives by default.**

**Status unchanged: F01 `source_closure` remains `partial`, NOT promoted.** The
honest partial shape v2 defined (`K of 6 closed`, first open region, words
remaining) is what was delivered: **0 of 6 closed, 70 words remaining in
region 1.**

## 2026-08-10 — original_oracle: all four leaves observed on a NATURAL cold-boot completion

Operator recorded `movies/Phase4/Interpreter/Any% Runs/LEVEL01_AntHill_FromBoot.movie.json`
— genuine cold boot (`from_boot: true`, no start anchor), format v4, 7,385 frames.
Replayed on the determinism-matched Interpreter config
(`tools/launch_repro_playback.sh`, `[CPU] ExecutionMode=Interpreter` present, media
verified pristine), `reproducible: true`, `phase_delay_owed: true` with
`phase_correction_consumed_at: 2` — the v4 self-correction did its job.

New: `tools/phase4_f01_original_oracle.py` → `analysis/phase4_f01_original_oracle.json`.

### The complement the prior witness was missing

`analysis/phase4_f01_finalizer_witness.json` **injected** `u16 2` into `0x800823A0`
from a save-state anchor and showed the finalizer skipped. LEVEL01 exits on region
code **2**, whose dispatch arm `0x800496C4` writes request **1** — so a natural
completion exercises the *other* side of `beq v1,2` at `0x8004FF30`. Nothing is
injected here; no write, no poke.

| leaf | value | |
|---|---:|---|
| `consumer_proceeded_hits` (`0x8004FF14`) | 1 | |
| `decision_reread_hits` (`0x8004FF28`) | 1 | frame 5895 |
| `request_at_decision` | **1** | produced by gameplay |
| `gp4c4_at_decision` (`[0x8008225C]`) | 0 | other skip condition ruled out |
| `finalizer_hits` attributable to the decision | 1 | 28 cycles later — same basic block |

Scene timeline `624 → 0 → 1 → 0`: Anthill entered ~frame 4000, exited by 6000, with
no injection. **6/6 assertions pass.** Status unchanged — `original_oracle` stays
`partial`; only a fresh detached verifier may promote.

### ⚠️⚠️ The trap this exposed: a PC watch is an ADDRESS watch, not a code watch

First pass reported `finalizer_hits: 327` against `decision_reread_hits: 1`. That is
impossible on straight-line code, and chasing the impossibility is what found it.

**On a from-boot movie the game EXE is not resident for the first ~1,000 frames.**
Direct `debugger.readMemory`: `[0x8004FF48]` = `0x00000000` at movie frames 300 and
700, becoming `jal 0x80045A60` only by frame 1200. The watch had been faithfully
logging 326 executions of *whatever else occupied that address during boot*.

⚡ **My assertion could not have failed.** `finalizer_hits >= 1` is satisfied by the
326 phantom hits alone — it would have passed even if the real completion had
SKIPPED the finalizer. Exactly the failure class already banked as
the `knockdown-not-a-slot-writer` auto-memory, committed by me in a tool written to avoid it.

**Fix, and it works at source rather than as a filter:** every watch now also
captures the instruction word **at its own PC**, and an event counts only when that
word equals the pristine image word. Re-run: `finalizer_hits_whole_run` **327 → 1**,
`preload_noise_rejected: {finalizer_hits: 326}`. The noise is gone, not filtered.

⚠️ **This affects every from-boot replay in the corpus that arms PC watches**, not
just F01. Any such count taken without an EXE-loaded guard may include pre-load
executions. Banked: the `pc-watch-is-an-address-watch` auto-memory.

### ⚡ I nearly banked a fabricated finding — the mundane explanation won

Before checking whether the code was even loaded, I had written up the 326 hits as
*"an observed indirect entry into the middle of a basic block, relevant to
`complete_frontier`"* and was about to commit it. It is a plausible story: this
binary has 179 unproved indirect sites and switch-case fall-through is a normal
compiler shape.

What killed it was a compiled-C probe rather than more speculation —
`tools/phase4_f01_finalizer_entry_probe.c` (self-tested, 5 cases): **zero** direct
branch/jump targets landing in `[0x8004FF14, 0x8004FF50)` across **22/22 unique images /
143,060 words**, and **zero** entries in the decoded `analysis/phase3_jr_tables.json`.
With no direct entry and no decoded indirect entry, "the code wasn't there yet" was
the remaining explanation — and a memory read confirmed it in one call.

**2026-08-10 hard-truth correction:** the earlier `260,307`-word / `2,340`-indirect
totals double-counted SCUS and omitted LEVEL00's one-word sentinel. The deduplicated
compiled-C census is **22 images / 143,060 words / 1,246 `jr`/`jalr` occurrences**,
still with zero direct entries. This corrects the arithmetic without changing the
bounded conclusion.

**Rule: chase the mundane explanation before the exotic one, and use a tool that can
refute it.** An exotic finding that fits the project's known open problems is exactly
the kind that gets banked without enough scrutiny.

Two method notes, both operator corrections applied here: compiled C owns instruction
decoding (the entry probe is C; earlier this session I had decoded MIPS in Python),
and everything is armed in ONE replay rather than re-arming across four —
re-arming means re-replaying, which invites drift.

## 2026-08-10 — campaign_breadth VERIFIED: the sweep is done, the dimension is not, and the scorecard note is STALE

Asked to confirm whether `campaign_breadth` was already done. Three separate answers,
and conflating them is exactly the "claim authored ≠ dimension met ≠ verifier
promoted" distinction.

### 1. The sweep IS done, and its corpus coverage is complete

`analysis/phase4_f01_campaign_breadth.json`: **19 movies** — all 16 levels of the
operator 100% corpus plus 3 bonus clips — replayed at 60 Hz on pinned-Interpreter
instances (5 in parallel with atomic `mkdir` work-claiming), write watches on the F01
lifecycle cells plus 37 watches batched from other rows. `excluded` records that the
re-recorded LEVEL02 take is included and that coverage is complete.

Transition request `0x800823A0` observed with values **{0, 1, 2, 6}** across the
campaign, `values_never_observed: [3, 4, 5]`, with writer PCs per value including
overlay writers (`0x800B3E74`, `0x800B4104`, …).

### 2. My contamination worry is FALSIFIED — worth saying plainly

Having just found that a from-boot PC watch logs pre-EXE-load noise
(the `pc-watch-is-an-address-watch` auto-memory), I flagged that it might have inflated this sweep.
It did not, for two independent reasons:

- **All 19 breadth movies are state-anchored** (`from_boot=0, state_anchored=19`), so
  the EXE is resident at every anchor — there is no pre-load window at all.
- The sweep used **memory write-watches**, not PC exec watches, which is a different
  mechanism and not susceptible in the first place.

I checked rather than assumed, and the honest outcome is that the concern was wrong.

### 3. What the dimension still lacks

- The artifact **self-declares** `promotes_campaign_breadth: false`, `is_proof: false`,
  `changes_f01_status: false`, and states *"RUNTIME EVIDENCE, NOT PROOF. Bounded to
  these replays. A value never observed is not a value that cannot occur."*
- It has **no `assertions` key**. The roadmap's method for this dimension is *"run
  F01's **assertions** across the corpus"* — the sweep **observes**; it does not assert.
- Promotion requires a fresh detached verifier regardless.

### ⚠️ The scorecard note is stale

`analysis/mechanics_baseline.yaml` → `F01_anthill.dod_scorecard.note` still reads:

> `campaign_breadth: LEVEL01 only, though the dispatch is campaign-wide.`

That is contradicted by the artifact — 19 movies across every level type, including
bonus, boss, city, interior and chase stages. **Not edited here** (the registry is
verifier-owned and I must not touch it); recorded so the next verifier sees the
evidence rather than the stale summary.

**Net:** the *work* is done and is good; the *dimension* is `not_met` and its
remaining gap is assertions plus a verifier, not more replays.

## 2026-08-10 — campaign_breadth ASSERTION pass: the branch law holds on all 19 levels

The breadth sweep observed; this asserts. `tools/phase4_f01_breadth_assert.py` +
`tools/phase4_f01_breadth_run.sh` → `analysis/phase4_f01_breadth_assertions.json`.

At **every** transition decision on **every** level, both directions of the law the
LEVEL01 oracle established:

> finalizer `0x80045A60` runs **iff** `request != 2 && [0x8008225C] == 0`

**19/19 levels asserted · 0 errored · 35 decisions checked · 0 law failures.**

### It is not vacuous, and all three paths are covered

| | count |
|---|---:|
| decisions where the law predicts CALL | 19 |
| decisions where it predicts SKIP | 16 |
| — skip via `beq request,2` | 13 |
| — skip via `bnez [0x8008225C]` | 3 |

Request values at decisions: `1` ×19, `2` ×13, `6` ×3. `[0x8008225C]`: `0` ×32,
`1` ×3. So **both skip edges** fire, not just the request one — the three bonus
stages carry request 6 with the force flag set, which is the only place the second
edge is exercised. A wrong law would have been caught.

### Independent corroboration

- **LEVEL07_CITYENTRANCE**, 5 decisions with 4 predicted skips, is the strongest case
  — and scene 4 is exactly the level the disc census shows carrying both hazard
  families (1 pit at code 1, 6 goo at code 4). Two unrelated methods agreeing.
- **LEVEL01_Anthill** reproduces the cold-boot oracle from a *different* recording
  (state-anchored 100% run vs from-boot): 1 decision, request 1, 1 finalizer.

### Hygiene

0 preload-rejected events across all 19 — confirming the prediction that
state-anchored movies are immune to the from-boot PC-watch trap. 0 finalizer calls
unattributable to a decision, no trace truncation, all 19 replays `reproducible`.

Harness: 8 isolated Interpreter instances, each with its own config dir, port and
token; atomic `mkdir` claiming, longest movie first. 8 rather than one-per-level
because the wall clock is bounded below by the longest single movie, so more workers
only add CPU contention. Per-movie results written as they land. Every instance this
run started was stopped by config dir; the operator's own DuckStation was left alone.

**Status unchanged.** The artifact self-declares `promotes_campaign_breadth: false`
and `requires_fresh_verifier: true`; `mechanics_baseline.yaml` untouched.

### ⚠️ And it caught me in a wrong negative

Training passing prompted a check of the code-3 arm, which showed I had
**over-generalised** today's claim that code 3 "had never been observed firing".
True of the E10 exec-watch sweep (which watched the arm entry `0x800496E8`); **false**
of the corpus. The 100% write-watch sweep already recorded writer PCs `0x800496DC`
*and* `0x800496FC` for request 1, pairing with the two exit arms' stores at
`0x800496D8` (code 2) and `0x800496F8` (code 3) — store PC + 4, confirmed because
neither reported PC is itself a store. **Arm 3 is live at runtime.** Corrected in
Canon, the census page, the handoff and memory.

Still not established, and kept separate: a direct exec hit on `0x800496E8`, and
which levels drove those writes (`by_value` does not break writers down per level).

## 2026-08-10 — measurement standard RULED; F01 re-assessed against the bars as written

Follow-through on the two-standards finding (every 9/9 ledger row carries one blanket
basis string; F01 alone was measured, and against the documented overshoot).

**Ruling** (`engineering-specs/phase4-measurement-standard-ruling.md`): one standard —
per-dimension measurement against the bars **as written** (item 2 = enumerated, scoped
to relevant; exit gate = explicitly bounded, not absent). Blanket dispositions are
decisions pending measurement, never scorecards. [[Phase 4 - Solve Every Gameplay and Engine Subsystem#Status vocabulary — what the words on this page mean|Phase 4 status vocabulary]] stands:
bounded-exhausted still never reads as met; publish decision AND measurement.

**First test case** — `tools/phase4_f01_written_bar_assessment.py` →
`analysis/phase4_f01_written_bar_assessment.json`, facts derived from pinned artifacts
at run time, judgments authored:

> **1 met · 2 met-candidate (original_oracle, complete_frontier) · 5 partial ·
> 1 not_met (campaign_breadth)**

Both candidates go to a fresh verifier — the assessor authored much of the evidence.
Honesty cuts both ways: campaign_breadth fails the WRITTEN bar too ("every applicable
stage" has no denominator without the applicability universe), while complete_frontier
is a candidate precisely because enumerated-plus-bounded is what item 2 actually asks,
and the 179-site declared assumption (void on one counter-example) supplies the bound.

F01's honest ceiling near-term: **3/9 measured**, which would be the highest *measured*
row in the campaign — the 16 blanket rows have no measured scorecards yet (noted per
operator instruction; not assessed).

## 2026-08-10 — lifecycle: the per-phase claim map, assembled at last

The written-bar assessment's gap for `lifecycle` was "no per-phase claim map exists;
phases are evidenced ad hoc rather than registered — cheap to assemble, never
assembled." Assembled: `tools/phase4_f01_lifecycle_claim_map.py` →
`analysis/phase4_f01_lifecycle_claim_map.json`, facts derived from five pinned
artifacts, judgments authored.

**5 covered · 1 n/a-with-reason · 1 partial, of 7 phases.** Cold boot (two natural
from-boot fixtures), load (converter census + disc census), first use and repeated use
(19 levels / 35 decisions / 0 failures), retirement (value-0 writers observed on
19/19 levels). Exhaustion is n/a **with the reason registered**: the request word is a
scalar latch, not a pool — its saturated state IS the single-shot guard, pinned
statically and visible as exactly-one-exit-decision per completed level.

The dimension's remaining gap is ONE claim: **reuse across a multi-LEVEL chain in one
session** — the 19-movie corpus is per-level state-anchored, so no fixture traverses
level→results→next-level with watches armed. Closable by asserting one existing
`movies/go_to_end/` from-boot movie (they already replay 1:1 under the repro config)
or one new two-level recording. Named, bounded, cheap.

## 2026-08-10 — lifecycle reuse: closed from retained evidence, and a correction

Two changes to the claim map, an hour after writing it.

⚠️ **Correction first: the previous entry's "closable by asserting one existing
go_to_end movie" was WRONG.** The go_to_end corpus is CachedInterpreter-recorded —
arming any CPU instrumentation forces Interpreter and desyncs them silently. They are
poll-only forever. The claim map now carries that warning where the bad suggestion was.

**Then the gap turned out to be already answered by retained data nobody had read as
lifecycle evidence.** The death probe's access log holds the cell's entire arc in one
from-boot session:

| frame | writer | event |
|---:|---|---|
| 98 | BIOS `0xBFC02B7C` | pre-game init noise (overlapping byte writes) |
| 1141 | `0x8005F6A0` | EXE-init clear |
| 1386 | `0x8004FADC` | shell clear |
| 5724–5725 | `0x8005B888` / `0x8004FE44` | level-entry clears |
| 6536 | `0x8004A8B4` | **certified death store, value 2** |
| 6656 | `0x8004FE44` | consumer clear, one frame after the decision |

Birth → cleared per phase → used → consumed → retired, in one session. And the breadth
data already showed **five successive set→consume→clear cycles in one LEVEL07 session**
(4 skips, then the exit call). That is reuse, observed — the multi-LEVEL chain I had
demanded belongs to the scene+overlay *transitions* axis, not to this cell's reuse, and
is kept as a residual note so it is not lost.

**Claim map now: 6 covered, 1 n/a-with-reason, 0 partial.** Under the written bars,
`lifecycle` is a **met-candidate** — the third. F01's honest measured ceiling: **4/9**,
pending fresh-verifier adjudication of all three candidates.

## 2026-08-10 — C2 answered: 6 of 8 types derive from a pre-outcome authority; 2 cannot

The adjudicated bar forbade labels chosen from outcomes. The question was whether an
independent authority exists at all. Answer: **partially — and the boundary is exact.**

`tools/phase4_c2_level_type_authority.py` → `analysis/phase4_c2_level_type_authority.json`.
Authority: the frozen F-row names in `analysis/mechanics_baseline.yaml`, committed a
month before the breadth pass existed. Declared keyword rules applied mechanically, the
matched substring recorded per label, so every assignment audits back to pre-outcome
text. `normal` is the declared residual; multi-labels allowed (F14 is chase AND
traversal-special).

**Derivable, with ≥1 level each: bonus (3), boss (4: Thumper/Thud/Molt/Hopper),
chase (1), city (2), traversal-special (3: flight/climbing/swinging), normal (7).**

**Underivable: interior and exterior.** No frozen text names interiority — it is a
geometry property. The outcome-independent path forward is a DATA-derived criterion
(chunk-29 backdrop/sky classification per level), unbuilt.

So `taxonomy_coverage_demonstrated: false` and **campaign_breadth stays not_met** —
the procedure was allowed to fail and did, on exactly two cells. C2 is now a bounded
data question rather than an authorship hazard; C1 (the applicability matrix) remains
the dimension's larger open design work.

## 2026-08-10 — C2 residual: the chunk-29 backdrop criterion FAILS, honestly

The proposed data-derived interior/exterior criterion (chunk-29 backdrop sky
classification) was tried and does not discriminate. Recon over all 16 scene
containers (palette at +0x10, 8bpp at +0x310, top-vs-bottom brightness and
blue-dominance sampling):

- The underground tunnels/council-chamber backdrop scores **bluer** (+20.2) than
  open cliffside canyon (+9.0) and riverbed run (+0.3) — blue-top does not mean sky.
- Scenes 2 and 3 (council chamber, tunnels) carry **byte-identical** chunk-29 stats
  (size 17764, same sampled values) — backdrops are shared between levels, so a
  per-level criterion built on them cannot be injective anyway.
- Scene 6's chunk 29 is 1,796 B and uniform — not a full backdrop image at all.

**Interior/exterior therefore remain underivable by every criterion tried**: no frozen
text names them, and the first data-derived candidate fails on measurement.
`campaign_breadth` stays not_met with the two cells open. A future criterion would need
the game's own rendering behavior (e.g., whether the backdrop layer is drawn as sky vs
parallax wall), which is an E01/E03 rendering question, not an F01 one.

## 2026-08-10 — FRESH DETACHED ADJUDICATION: original_oracle MET · complete_frontier MET · lifecycle NOT MET

Sixth+ verifier in the chain, detached from the repair, the probe evidence, the
rulings, and both submissions. Freeze `44efaa2b` (baseline `1dc40daa`); full record in
`analysis/phase4_f01_fresh_adjudication.json`. Fractions before adjectives.

**original_oracle — MET.** Both arms of the finalizer branch law now have natural,
injected-nothing cold-boot reproductions. Verified four ways: (1) offline
reconsolidation of the 3/3 retained receipts is byte-identical, with every
disk-dependent check recomputed; (2) an isolated live replay of the natural-death
movie (fresh config dir, port 23520, `[CPU] ExecutionMode=Interpreter` verified in
settings.ini, SCUS-94288 verified) reproduced the retained receipt **byte-identically**
— same death store at frame 6536, same request-2 decision at 6655, finalizer absent;
(3) compiled-C image-byte decode re-derives 10/10 load-bearing words, proves the
0x8004A8B4 store is the **conditional** health-depletion arm (`bgez` guard at
0x8004A890), and adds a consistency proof the submission never stated: timer 60 ×
2 frames/tick = 120 predicted vs 119 observed writer→decision frames; (4) the
finalizer absence is the guard working, not filtering — all 326/326 rejected events
sit at frames 193–756 with captured word 0x00000000 (EXE not yet loaded), 0 post-load
rejections, and D18 proves real hits are retained. §3's consolidate generalization
was confirmed sound **by mutation**: missing/duplicated/extra/renamed sets all fail;
a valid control-free set degrades to BLOCKED, never DONE.

**Four handed-over tests — all four legitimately overtaken, none caught a break.**
(1) honestly-BLOCKED → replaced by honestly-DONE plus a new mutation test that keeps
the premature-DONE guard (control-free set must consolidate BLOCKED); (2) pair
arithmetic → set arithmetic, plus a new missing/duplicate/extra rejection test;
(3) the `stored_u16 is None` blanket → exactly 1/24 writes is the certified death
store, all others None; (4) the consumers drift is a machinery-derived field change
(the regenerated fixture audit genuinely references the movie; verified across three
commits in both files) → re-pinned exactly, and the natural-death movie's entry got
its own exact pin. The two files went 40 passed / 4 failed → **47/47**.

**complete_frontier — MET against the written bar** (item 2 verbatim asks the relevant
frontier be *enumerated*; the empty-set reading is the playbook's documented
2026-08-04 overshoot). Direct frontier: enumerated and twice verifier-verified
(58/58 writers bijection, 124 window accesses, 66 readers, whole-corpus scan). The
indirect residual: 179/179 sites named and frozen (sha verified), classified 7 bins,
derived corpus-wide (unproved subset of the corrected 1,246-occurrence / 22-image
census), runtime-corroborated across 213 armed sessions with 0 protected-set hits and
100/179 sites silent through 100% completion, and bounded by the item-2 ruling's
declared assumption — **void on a single counter-example, non-transferable**, which
now lands verbatim on the row. 5/5 resolution campaigns NO-GO with named walls (D3
verified: 0/4 contracts, 0/12 sites, residual 179→179).

**lifecycle — NOT MET.** 6 of 7 phase claims audit clean (19/35/5 re-summed
independently; the exhaustion n/a-with-reason is honest — the 0x8004965C/0x80049664
saturation guard verified from image bytes, one exit decision per level 19/19; the
reuse arc replayed byte-identically). The blocker: **every
`phase4_f01_campaign_breadth.json` writer_pc is the true store instruction +4** —
verified by compiled-C decode at 11/11 sites with 0 counter-examples, sealed
cross-artifact (the same writer is 0x800B3E84 to the probe's `instruction_pc` and
0x800b3e88 to the sweep), and disclosed nowhere. The claim map copies five of these
into `clear_writers_observed`, so as registered it names an `lw`, a `bgtz`, and a
`lui` as writers of the request word, while its own reuse fact uses exact store PCs —
two conventions in one document. **What would satisfy the axis:** instruction-exact
(or convention-annotated) writer attribution for the retirement phase, then a
regenerated claim map. Nothing else is missing.

Registry: `original_oracle` and `complete_frontier` moved by this verifier in a
separate final commit; `lifecycle` stays partial. The scorecard note's three stale
statements (injected save-state oracle, "LEVEL01 only" breadth wording, the old
partial-claim language) corrected in the same deliberate step.

## 2026-08-11 — lifecycle re-adjudicated after the attribution repair: MET

A fresh detached verifier (author of none of: the repair `bcfd7dce`, the probe, the
claim map, the prior verdict `bc03931c`) re-checked exactly one dimension —
**lifecycle** — against the prior adjudication's named defect and remedy. Freeze
`dba0e639` (baseline `bcfd7dce`); full record in
`analysis/phase4_f01_lifecycle_readjudication.json`. Fractions before adjectives.

**Verdict: MET.** The named defect (breadth-sweep `writer_pcs` = store+4 registered
as value-0 writers, undisclosed) is repaired exactly as remedied, and nothing else
moved. Five checks:

1. **Probe rebuild 3/3** — `cc -std=c11 -O2 -Wall -Wextra -Werror` clean; `--selftest`
   PASS rc 0 (5 vectors, including the lw/lh rejections); rerun against the
   pin-verified `SCUS_942.88` (sha `1aa28954…`) with exactly the five
   `by_value["0"].writer_pcs` emits an artifact **byte-identical** to the committed
   `phase4_f01_retirement_attribution.json` (sha `61737b84…`, = the claim map's pin).
2. **Independent image-byte confirmation 5/5** — raw words re-extracted from the EXE
   bytes by the verifier match the artifact at every pc and pc−4; 3 words hand-decoded
   from the opcode field (minimum was 2): `0xA2C00000` → `sb zero,0(s6)` STORE vs
   `0x8FB60030` → `lw s6,0x30(sp)`; `0xA42023A0` → `sh zero,0x23A0(at)` STORE vs
   `0x3C018008` → `lui at,0x8008`; `0x1CE0FFD2` → `bgtz` — precisely the lw, lui and
   bgtz the defect named, each sitting at a reported pc with the true store at pc−4.
3. **Derivation + stability** — `convention_holds_at_every_row` enters the map through
   the same `derive()` that sha-pins the artifact (derived, never hardcoded); two
   consecutive regenerations byte-identical to each other **and** to the committed map;
   6/6 evidence pins match disk.
4. **No collateral weakening** — `git diff 2e7749e..bcfd7dce` touches only the
   retirement block, the derived fact, the new pin, and the date; the other six phase
   claims are byte-identical; the summary's named remaining gap (multi-level chain
   with watches armed) is unchanged.
5. **Division of labor: sound.** Static compiled C certifies instruction identity and
   is fail-closed (pc−4 must BE a store and pc must NOT be); the runtime write-watch
   is address-filtered by construction, so "landed on the cell" is exactly what it
   proves. Each side covers the other's blind spot. Corroboration beyond the
   submission: the direct rows carry the `lui at,0x8008`/`0x23A0(at)` idiom at the
   reported pc, and the byte-split clear explains `0x80036cd0` appearing in both the
   value-0 and value-1 lists.

**Noted, not blocking** (undisclosed by the repair): the sweep artifact itself remains
convention-silent (disclosure lives in the claim map + attribution artifact — the
registration was the defect, and regenerating the sweep needs a 19-movie live
replay); `facts.clear_writers_observed` still holds +4 event PCs as values, labeled
in prose one key away, with 0 mechanical consumers today; the pc−4 mapping assumes no
delay-slot store, which does not arise at these 5 sites and fails closed if it did;
phase STATES are authored judgments and never self-promote (`promotes_row_or_dimension`
false).

Registry: `lifecycle` moved partial → met by this verifier in a separate final
commit; the scorecard note and the row's `next` text adjusted where the ruling
touches them. The prior verdict's residual notes (watch-window statement; pause
permutations living in the row's `missing` field) remain recorded and remain
non-blocking.
