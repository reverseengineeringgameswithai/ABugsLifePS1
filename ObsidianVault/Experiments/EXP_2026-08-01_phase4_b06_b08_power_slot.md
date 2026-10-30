---
type: experiment
status: complete
date: 2026-08-01
system: player power-ups
phase: 4
rows: [B06_invincibility, B08_bubble_shield]
artifacts:
  - analysis/phase4_b06_b08_powerups.json
  - tools/dis_exe.py
---

# B06 / B08: one signed halfword, multiplexed by sign

> **Title corrected.** This note was written as "closed". The rows are **partial** —
> promoted 2026-08-01 and retracted the same day against the Definition of Done. The
> mechanism below is confirmed; the evidence grade was not closure grade.
>
> **Current scorecard (2026-08-01, after adversarial review): MET 1, 3, 6, 7, 8 ·
> ADVANCED 2, 4, 5, 9.** Items 2, 4, 5 and 9 were briefly graded met and the review
> downgraded them; the rows stay partial. DoD table and closure path:
> [[Phase 4 - Solve Every Gameplay and Engine Subsystem]]; the model itself is Canon at
> [[SYS_player_power_slot]].

## Verdict

`0x800A657E` is a **single signed halfword** that carries both power-ups. The sign
selects which, and the *consumption rule* follows the sign:

| slot | power | consumed by |
|---|---|---|
| **> 0** | B06 temporary invincibility | **time** — tick `0x80048654`, 1 per 2 frames |
| **< 0** | B08 bubble shield | **hits** — absorb `0x8004A808`, +1 per absorbed hit |
| **= 0** | none | — |

The tick's `blez` guard at `0x80048648` is what makes this work: it skips
non-positive values, so a bubble is **time-invariant** and an expiring
invincibility **lands exactly on 0** rather than underflowing into a bubble.

## Why this revision exists

The 2026-07-31 revision had the model right but was incomplete, and two of its
statements were wrong in ways that matter:

- It catalogued **6 of the 7 writers**. It missed `0x80051F60` (the harvester) and
  `0x8005B268` (the respawn reset) — i.e. it was missing both the cross-system
  intersection and the entire reset lifecycle.
- It said `0x8004A7B4 bne v1,zero` *"SKIPS the health write"*. It routes; what
  suppresses the write is register **`s1` being cleared**, tested by
  `0x8004A828 beq s1,zero`.
- It said *"quota >= 0 falls through to the damage handler"*. It does not — a
  non-negative slot at `0x8004A7E8` lands on `0x8004A80C`, which also clears `s1`.

## Site census — a lower bound (RETRACTED as completeness)

⚠️ The section below originally claimed a complete enumeration. It is not one: the scan
matched only immediate `0x657E` and `+0x7E` forms, and `0x800588D0`, `0x8004A7E0`,
`0x8004A808` are zero-offset aliased-pointer accesses it never found — those came from
runtime traces. It also said "5 readers" while listing 6. Treat the counts as observed
lower bounds pending a committed alias-aware census, and note that no overlay code has
been censused at all.

## Completeness — the part static analysis can settle

A whole-image scan of pristine `SCUS_942.88` (`tools/dis_exe.py`), covering **both**
addressing forms the code uses (absolute immediate `0x657E`, and halfword ops at
`+0x7E` off a player-block pointer):

- **7 writers, 5 readers** of the slot. No other instruction in the image touches it.
- **6 callers** of the damage handler `0x8004A700` — every `j`/`jal` in the image.
- **4 writers** of true health `0x800A6594`, of which `0x8004A888` is the **unique**
  damage-side one (the others are spawn init, heal, respawn restore).

That last one is what makes the bypass a *complete* claim rather than a local one:
there is no second way to lose health from a hit, so intercepting `0x8004A888` is
the whole of damage immunity.

## The runtime experiments

All on Interpreter, over `movies/B08_movie.json`, which supplies real contacts
(grant f183, absorbs f365/f495/f593, the hit that lands f649). **R0 replays it
untouched and reproduces the documented lifecycle exactly** — that control validates
the regime before anything is concluded from the rest.

| run | perturbation | result |
|---|---|---|
| R0 | none | −3 → −2 → −1 → 0 → health 4→3. Matches the record exactly. |
| R1 | slot := +400 | **8 intercepted contacts, ZERO health writes.** Runtime proof of the bypass. |
| R2 | slot := +6 | ticks 5,4,3,2,1,**0** — stops at 0; then health 4→3→2. Expiry restores vulnerability. |
| R3 | slot := −1 before the grant | grant stores **−3, not −4** → capacity is clamped refresh. |
| R4 | slot := +400 before the grant | grant overwrites with **−3** → invincibility discarded. |
| R5 | slot := 0 + harvester bit | zero health writes → see below. |

## The harvester intersection — and why the obvious reading is wrong

`0x80051F60` writes **1** into the slot whenever power-flags bit `0x0080` is set. A
positive slot is what the damage path treats as invincibility, so the natural
reading is that harvesting silently confers immunity through the shared slot.

**It does not.** `execTrace` over the handler and all six of its call sites:

| arm | handler entries | health |
|---|---|---|
| no harvester | **3** (all from `0x8004B4A0`), all reaching `0x8004A888` | 4 → 1 |
| harvester | **0**, from any call site | 4 |

The handler is never entered, so the in-handler interception plays no part. The
cause is `0x8004B160 andi v0,0x80` → `0x8004B164 bne` in
`actor_player_contact_resolver`, which branches past its damage call long before
reaching it. Immunity while harvesting comes from the **flags word**, not the slot.

Corroborating design evidence: `0x80055BC4` requires slot > 0 **AND** harvester bit
**clear** before the invincibility effect — the game itself distinguishes the
harvester's use of the slot from a real invincibility.

## Breadth

16 distinct scene ids (1–15 and 17). In each: all 16 bound instruction words read
live are **byte-identical** to the pristine EXE (an overlay specialising the handler
for a stage would show here), `+400` ticks down, `−3` is untouched. Zero mismatches.

## Visual

Phase-matched `gpu.captureFrameSnapshot` / `gpu.diffCurrentFrame` — same state, same
frame count, which is required because the flash is animated:

- control vs control: **0** changed pixels of 488,000 (determinism holds)
- timer on vs control: **4,054** changed pixels in a **single 151×327 box** on the
  player

## Cold-boot oracle — added after the retraction

The retraction's decisive charge was that every runtime claim came from save-state
movies and, for B06, from **poked** timer values. A poked timer proves the damage path
*reads* the slot; it does not prove that collecting the pickup *produces* that state.

Two operator-recorded **from-boot** movies now close that, asserted with no pokes by
`tools/phase4_b06_b08_oracle.py` — a committed runner that computes its artifact and
exits non-zero on any failed check:

| | stage | frames | verdict |
|---|---|---|---|
| B06 `b06_invincibility_hits_from_boot` | **LEVEL01 (scene 1)** | 6522 | **5/5** |
| B08 `B08_bubble_repeated_hits_from_boot` | LEVEL06 (scene 11) | 6959 | **6/6** |

**B06**: natural grant `0x800588D0` := 400 @f5336 → 16 intercepted contacts with
**zero** health writes → 400 tick writes, strictly −1 each → lands **exactly on 0**
@f6154 → 2 damage writes at `0x8004A888` afterwards.

**B08**: natural grant `0x800589A8` := −3 @f6046 → absorbs −2/−1/0 with **zero** health
writes between grant and pop → pop @f6554 → 3 damage writes afterwards → and **zero
tick writes while the quota was negative**.

That last one matters most. Time-invariance — a bubble is hit-consumed and never
time-consumed — was previously inferred from the `blez` guard at `0x80048648` and
demonstrated by poking. It is now observed in a natural playthrough.

B06's fixture is also the first natural collection of either pickup **outside scene
11**, which is why campaign breadth went from a hard fail to advanced.

Fixtures are hash-pinned in `analysis/phase4_b06_b08_fixtures.json`, including the
`.sav` hash the movie format omits (`start_state.sha256` is null in every movie).

## Lifecycle at boundaries

`tools/phase4_b06_b08_lifecycle.py`, on `level01.sav`, Interpreter:

| probe | result |
|---|---|
| **pause** | 15 ticks in 30 running frames → **0 ticks in 180 paused frames** → 16 in 30 after resume. The pause freezes the timer. |
| **save/load** | No save or checkpoint routine writes `0x800A657E`. `checkpoint_save` writes position, `0x6578` and the power-**flags** word (`ori 8`) — never the slot. Powers are runtime-only. |
| **scene transition** | **INCONCLUSIVE.** Forcing the exit trigger with the timer at 400 gave **zero** slot writes across 3600 frames — no tick, no clear — so gameplay never resumed. The slot held 400 because nothing was running. |

That last row is worth keeping as written. The first version of the probe reported
"power SURVIVED the transition" from exactly this data. The tell is the zero write
count: the tick fires every two frames whenever the player update runs, so its absence
means the measurement window contained no gameplay at all.

## Everything since the cold-boot oracles

The note above stopped at the oracles; this section carries the rest of the campaign.

### Frontier (item 2)

- **Alias-aware census** (`tools/census_address.py`) replaced the immediate-grep. It
  resolves zero-offset and argument-passed bases. **Correction history:** this pass
  reported 8 writers / 7 readers, not 7/5, but the eighth writer was the falsely
  attributed `0x8004AFB0`; the pristine direct set is **7 writers / 7 readers**. It found
  `0x80051EA0` (the harvester's equip write) and
  `0x800588B0` (the grant's guard read), and for true health **6** writers, not 4.
- **Overlay census** (`tools/census_overlays.py`), never done before: **zero** overlay
  accesses to the slot across 21 blobs, and **three** overlay *reads* of true health
  (`0x800B41D0`, `0x800B3DAC`, `0x800B3D50`).
- **Callee writes** (`tools/census_callee_writes.py`) — the class no store-site census can
  see. The transition clear is a BIOS `memset`; a `jal` scan misses it because the game
  reaches the BIOS via a **register-indirect** PsyQ stub (`jr t2`). An early pass resolved
  24 of 26 call sites; converged static propagation resolves all 26, including the
  disjoint `0x8004DC40 -> memset(0x80095358,0,48)`. Separately, runtime capture on the
  *store* (not the entry) gave `ra = 0x80046B70` → **`memset(player_block, 0, 168)` at
  `0x80046B68`, the player spawn**.
- **Runtime writer union** across 3 fixtures: **zero** writers outside the enumerated set.

### Lifecycle (item 4)

Pause **freezes** the timer (15 ticks / 30 running frames → **0** in 180 paused → 16
after resume). Powers are **never persisted** — no save or checkpoint routine writes the
slot. Scene transition **clears** it, via the spawn `memset` above. **Correction history:**
this note then called `0x8004AFB0` a bounded, unobserved knockdown clear. Both parts were
wrong. It executes naturally at frame 5966, while the pristine chain
`v1=0x800A6500; fp=v1+4; sh zero,0x7E(fp)` targets player+`0x82`, not the power slot.

### Audio (item 7)

`65` has **exactly one** call site — invincibility's sound is its own, `VAG 50`, 0.842 s,
byte-identical across 14 gameplay banks. `-3` has **four**, three in the generic pickup
handler — **the bubble has no sound of its own**. Ablating the single `jal` at
`0x80058998` removes exactly two voices at the grant.

### Production chain and render (item 5)

`token → counter → pair table 0x8007A448 → (type, extra) → ctor → contact_alloc → metaB →
action → walker case → grant`, with the invincibility ctor pinned to **`0x25`** and the
bubble's to `0x1F`. Renderer is `contact_record_billboard_render` `0x80014844` —
screen-aligned `POLY_FT4` sprites — indexing the **same** `0x80096B98` descriptor table as
type-0x3f pickups but by `rec+0x20`. **No per-level asset dependency** beyond the plant
models.

### Source closure (item 8)

`src_re/player_power_slot_800a657e.c`, documentation-grade, guarded by
`tests/test_phase4_b06_b08_power_slot.py` (77 assertions). Writing it is what **caught the
misattributed renderer** — `0x80051C3C` is the bubble's, not B06's — and yielded the
bubble's own visual binding, the shell colour ramp sized exactly to the 3-hit quota.

### Promotion gate

Run from a fresh clone. It caught two defects: the census gate **reported missing inputs
as frontier drift**, and the test **asserted a symbol name present only in an uncommitted
file**. Both fixed. Pre-existing and recorded: the vault ratchet reports
`evidence_deadfile: 3` from a clean clone, from notes last touched 2026-07-12.

### Three of my own premises corrected today

Recorded because the pattern matters more than the facts: **the renderer attribution**
(`0x80051C3C` is the bubble's), **table A's indexing** (it *is* the stack arg; row 3's
zeros are the "spawn still" profile), and **whether the descriptor Canon applies** (it
does). All three were caught by *re-deriving from the EXE* rather than trusting this
artifact.

## What is still open

Recorded in the rows' `missing` fields, not hidden here:

- ~~Audio is bound statically but not asserted at runtime~~ — **resolved.** The caller
  census resolves 20/22 `sfx_dispatch` and 90/92 `play_sound` ids: `65` has exactly one
  call site (invincibility's sound is its own), `-3` has four, three of them in the
  generic type-0x3f pickup handler (the bubble plays the generic collectible sound).
  Runtime ablation of the `jal` at `0x80058998` removes exactly two voices at the grant.
- ~~The bypass and expiry runs poked the timer~~ — **resolved** by the cold-boot
  oracle above.
- ~~Breadth is advanced, not met~~ — **resolved.** Both rows are now collected naturally
  in two stages, breaking the single-stage confinement. Remaining stages are argued from
  measured resident-code identity plus availability tables, and labelled as an argument.
- **The frontier is enumerated, not bounded** (DoD 2). The counts in the original bullet
  have since been re-derived (416 same-width resident sites and 149 indirect calls; all
  26 callee destinations resolved). Its offered counterexample was wrong:
  `0x8004AFB0` belongs to the unresolved-base analysis class but targets player+`0x82`,
  so it does not prove that class contains another power-slot access.
- **Correction:** the purported knockdown clear is withdrawn, not exercised. The store
  executes naturally but never targets this slot; lifecycle item 4 instead needs a
  re-derived exceptional-path list.
- **The tpage/clut rebinding writer is unattributed** (DoD 5).
- **The evidence wrapper lacks required provenance** (DoD 9): no mounted-media identity,
  debugger binary/capability provenance or watch saturation status in the oracle runner,
  and no repo-wide Phase-4 inventory, fixture audit, evidence DAG or whole-phase gate.
- `0x8004A700` is the player damage handler, but calling its census name
  `resident_level_transition_initiator` a flat misnomer **overstated it** — the
  function does store 2 to `0x800823A0` at `0x8004A8B4`, on its **death branch**,
  reached only when the health decrement drives health negative. The name captures a
  real but secondary effect of one branch. Corrected in [[FUNC_8004A700]].
- **Canon conflict resolved**: that function's migrated Purpose paragraph calls
  `0x800A6594` a "level-exit counter". It is the player's **true health** — it
  decrements by 1 at `0x8004A888` per landed hit, hits 0 under forced damage, and the
  respawn handler restores it to 4; the `bltz` at `0x8004F0E0` is an alive check.
  Agrees with the Phase-2 binding.

## Canon

Promoted to [[SYS_player_power_slot]]; field table added to [[MEM_800A6500]];
[[FUNC_8004A700]] named and corrected; closure recorded in
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].

## Related

- [[EXP_2026-07-31_interpreter_movies_survive_instrumentation]] — why tracing a movie
  replay is possible at all
- [[EXP_2026-08-01_savestate_movie_arm_phase_desync]]
