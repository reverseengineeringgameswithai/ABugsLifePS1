---
kind: memory
id: MEM_800823A0
aliases:
  - MEM_800823A0
  - "0x800823a0"
  - scene_transition_request
address: '0x800823A0'
width: 2
name: scene_transition_request
status: confirmed
confidence: confirmed
source_state: original_game
system:
  - Gameplay_-_Warp_and_Level_Transition
  - Level_Goal_and_Exit_Trigger_Matrix
evidence:
  - EXP_2026-08-05_phase4_f01_objective_lifecycle
  - EXP_2026-08-10_phase4_f01_oracle_breadth_repair
  - analysis/phase4_f01_objective_lifecycle.json
  - analysis/phase4_f01_runtime_lifecycle.json
patch_policy: callable
---

# MEM_800823A0 — scene transition request

`s16` at `0x800823A0` (`$gp + 0x608`, `$gp = 0x80081D98`). Paired with its
countdown timer [[MEM_80082470_scene_transition_timer]].

**It is a request enum, not a boolean latch.** Earlier notes called it "the
completion latch" because F01's completion arm stores `1`. A gp-aware census
(`lui+addiu`, `lui+ori`, and `$gp`-relative forms) over `SCUS_942.88` plus all
21 shipped overlays finds **28 writers and 53 readers**, spanning seven values.

## Value domain

| value | resident writers | meaning |
|---:|---|---|
| 0 | `0x8004FADC`, `0x8004FE44`, `0x8005B888` | cleared / no request pending |
| 1 | `0x800496D8` (region code 2), `0x800496F8` (region code 3) | scene complete |
| 2 | `0x8004A8B4`, `0x8004A9F4` | death (timer 60) |
| 3 | `0x8004F28C` | unnamed |
| 4 | `0x8004F224`, `0x8004F2F0`, `0x8004F6B8` | unnamed |
| 5 | `0x8004F9E4` | unnamed |
| 6 | `0x8004B3C0`, `0x800591DC`, `0x8005C6B8` | unnamed |

Twelve per-level overlay verbs also store `1` (and `LEVEL06/LEVEL.BIN` stores
`2`) — see the census in `analysis/phase4_f01_objective_lifecycle.json`.

## Consumer

At `0x8004FEEC`: proceed only when request ≠ 0 **and** the timer has reached 0.
Then call `0x80039BD8(0)` and `0x80043500`; then call the transition finalizer
`0x80045A60` **unless request == 2 or `[$gp+0x4c4] != 0`** (`0x8004FF30`).

The death arm therefore deliberately skips the finalizer that the completion arm
runs. A scene entered via request 1 and one entered via request 2 do not tear
down the same way.

## Re-entry guard

`0x8004965C` re-reads this word and abandons the entire collision region-code
dispatch when it is nonzero, making every region trigger single-shot per scene.

## Lifecycle shape (observed, LEVEL01 Anthill, whole stage)

Entry and exit use the same machine:

| frame | pc | value |
|---:|---|---|
| 139562 | `0x8005B888` | 0 (clear) |
| 139563 | `0x8004FE44` / `0x8004FE4C` | 0, timer ← **45** (entry transition) |
| 140814 | `0x800496D8` / `0x80049704` | **1**, timer ← **23** (exit transition) |
| 140859 | `0x8004FF48` | finalizer called |

Exactly three writes across the whole stage, all from resident PCs — no overlay
verb participated. The countdown at `0x800553F8` ticks every 2 emulator frames
(the 30 Hz logic tick).

## Request 2 observed: the finalizer skip is proven, not inferred

`movies/Phase4/Interpreter/Bonus01_Counter_ResetTest.movie.json` is a LEVEL01
(scene id `1`) Interpreter run in which Flik dies. Armed replay, 4,187 frames,
non-truncated:

| frame | pc | event |
|---:|---|---|
| 12177, 12757, 13945, 14077 | `0x8004A888` | health 4→3→2→1→0; **no request written** |
| 14309 | `0x8004A888` | health 0 → **−1** (the `bgez` at `0x8004A890` fails) |
| 14309 | `0x8004A8B4` / `0x8004A8C0` | request ← **2**, timer ← **60** |
| 14436 | `0x8004FF14` | consumer proceeds (request 2, timer 0) |
| 14436 | `0x8004FF28` | request re-read = **2**, `[$gp+0x4c4]` = **0** |
| — | `0x8004FF48` | **zero hits — finalizer skipped** |
| 14437 | `0x8004FE44` / `0x8004FE4C` | request ← **0**, timer ← **45** |

The consumer demonstrably reached the decision point, and the *other* skip
condition (`[$gp+0x4c4] != 0`) was measured at `0`, so `request == 2` is the only
thing that can have skipped the finalizer.

Four non-lethal hits produced no request at all: **a hazard requests a transition
only on the decrement that takes health negative** (health `0` is still alive).

The respawn re-runs the **scene-entry** transition — the same `0x8004FE44` /
`0x8004FE4C` pair, timer `45` — with scene state `0x80082504` unchanged at `1`.
Death in Anthill is an in-place respawn, not a scene change.

Evidence: `analysis/phase4_f01_death_lifecycle.json`.

## 2026-08-10 fail-closed campaign confirmation

The repaired breadth oracle requires the exact declared 19-level universe and at
least one self-certified decision per level. All **35/35** decisions carried the
pristine `0x846323A0` instruction certificate at `0x8004FF28`, typed request and
`$gp+0x4c4` operands, frame/cycle coordinates, and reconciled complete trace
counts. The finalizer law held in **35/35** cases: 19 calls and 16 skips.

This strengthens the bounded campaign evidence but does not establish a natural
request-2 producer from cold boot. The two pinned cold-boot work-order candidates
produced zero resident death-store hits: D18 reached one request-1 decision and
E02 reached no decision. Closure still requires a centrally pinned pristine
cold-boot movie in which Flik dies naturally. The older injected witness and the
state-anchored natural-death replay above remain valid for their declared scopes;
they do not satisfy that stronger anchor requirement.

Evidence and exact artifact hashes:
[[EXP_2026-08-10_phase4_f01_oracle_breadth_repair]].

## It is a global "scene is transitioning" signal, not a scene-flow local

⚠️ **RETRACTED (2026-08-05): this section first claimed the writer set was
COMPLETE. It is not, and the tool never showed that.** The resolver reports
"zero additional writers among the RESOLVED accesses"; I wrote that up as "no
unknown writer". **106 unresolved STORE sites remain** — each is a potential
writer this pass cannot exclude. The resolver now fails closed on them, splits
unknowns by load/store, and retains every one individually.

What the resolver does support: `tools/phase4_f01_frontier_resolve.c` re-walked
all 30 extents that touch this word with stronger base recovery than the static
index. Of 1,960 memory accesses: 62 reach a window, 1,181 provably miss, 314 are
stack-frame bounded, and **403 remain unresolved (106 stores, 297 loads)**.

> ⚠️ **Re-baselined 2026-08-05 — these figures were a LOWER BOUND.** 20 of the resolver's 29 extents stopped short of the real function end (ends were hand-picked, not taken from the static index), leaving **28,252 bytes / 7,063 instructions inside the censused functions unread**. Corrected **twice**, and the second correction came from a fresh verifier: the extent SET was a subset too (29 of the 37 the tool's own criterion admitted). The selection criterion has since been removed entirely — the census now scans **every code function in every analysed image** and *discovers* which reach a window.
> 
> **Current, corpus-wide (1,058 extents, 33,642 accesses after the 2026-08-06 census repair): 124 window-reaching accesses, 0 writers outside the enumerated set, 66 previously unlisted readers, 5,654 unresolved store sites.**
> 
> ⚠️ **That zero is NOT writer completeness.** The artifact's own `claim` says so: the writer set is not shown complete while those 5,654 unresolved stores remain. What is bounded-exhausted is further widening of the DIRECT STATIC WRITER CENSUS — reopen on a named falsifier (changed image or census identity, a new window hit, a newly resolved writer, or indirect/callee evidence), not merely because the row is still partial. Restricted to the 37 discovered window-touching extents: 4,031 accesses, 124 hits, 2,466 provably miss, 627 stack-bounded, 814 unresolved (**238 STORES**, 576 loads). `resolved_writers_not_previously_enumerated` is still **0** over the full extents, so the no-new-writer finding survived and strengthened — but every count above understated the work. See [[Phase 4 - Typed State Compiler]].

Among the resolved accesses there is **no writer outside the enumerated set** —
which is a real result, and a strictly weaker one than completeness.

What it did find is **66 previously unlisted READERS**, listed in full below and
regenerable from `analysis/phase4_f01_frontier_resolve.json` (`resolved_hits`
where `store == false`). The figure was first reported as 34, then 50; it grew
with each extent-scope correction and is now measured over the whole corpus.

Most are **not** scene-flow code — sound, rendering, checkpointing and per-level
AI all gate on this word — but seven of them **are**: `scene_flow_dispatcher`
reads it at `0x8004FEF0`, `0x8004FF04`, `0x8004FF28`, `0x8004FF90`,
`0x800500A8`, `0x800501AC` and `0x80050220`. ⚠️ Those seven are invisible to the
static index, whose record for that function is `analysis_status: ok` with 8 of
393 instructions analysed; they are recovered only by the corpus scan.

| reader | pc | reads |
|---|---|---|
| `player_vertical_update` | `0x80048518` | timer |
| `player_vertical_update` | `0x8004852C` | request |
| `player_vertical_update` | `0x8004965C` | request |
| `player_vertical_update` | `0x80049818` | request |
| `resident_level_transition_initiator` | `0x8004A7C0` | request |
| `setpiece_sfx_cue` | `0x8004D95C` | request |
| `gameplay_state_machine` | `0x8004EEE8` | request |
| `gameplay_state_machine` | `0x8004EEFC` | timer |
| `gameplay_state_machine` | `0x8004F158` | request |
| `gameplay_state_machine` | `0x8004F204` | request |
| `gameplay_state_machine` | `0x8004F26C` | request |
| `gameplay_state_machine` | `0x8004F2D0` | request |
| `gameplay_frame_render` | `0x8004F9D0` | request |
| `main_shell_state_machine` | `0x8004FB40` | request |
| `scene_flow_dispatcher` | `0x8004FEF0` | request |
| `scene_flow_dispatcher` | `0x8004FF04` | timer |
| `scene_flow_dispatcher` | `0x8004FF28` | request |
| `scene_flow_dispatcher` | `0x8004FF90` | request |
| `scene_flow_dispatcher` | `0x800500A8` | request |
| `scene_flow_dispatcher` | `0x800501AC` | request |
| `scene_flow_dispatcher` | `0x80050220` | request |
| `sfx_dispatch` | `0x80050B84` | request |
| `contact_pickup_sfx` | `0x80050C70` | request |
| `ambient_sfx_sequence_update` | `0x80051120` | request |
| `hud_draw` | `0x800526F8` | timer |
| `results_screen_render` | `0x80052734` | request |
| `checkpoint_save` | `0x80054CCC` | timer |
| `sfx_nearest_pickup_f_glue` | `0x80054F24` | request |
| `sfx_voice_trigger_gl_glue` | `0x80055398` | timer |
| `sfx_voice_trigger_gl_glue` | `0x800553AC` | request |
| `sfx_voice_trigger_gl_glue` | `0x800553E0` | timer |
| `actor_skinned_update` | `0x80056888` | request |
| `LEVEL01_LEVEL1:level_actor_event_handler` | `0x800B3CF8` | request |
| `LEVEL01_LEVEL1:level_actor_event_handler` | `0x800B3DCC` | request |
| `LEVEL01_LEVEL1:level_actor_event_handler` | `0x800B4088` | request |
| `LEVEL02_LEVEL:level_completion_handler` | `0x800B3BF4` | request |
| `LEVEL02_LEVEL:level_completion_handler` | `0x800B3C48` | request |
| `LEVEL02_LEVEL:level_completion_handler` | `0x800B3F3C` | request |
| `LEVEL02_LEVEL:level_completion_handler` | `0x800B403C` | request |
| `LEVEL02_LEVEL:level_completion_handler` | `0x800B4088` | request |
| `LEVEL02_LEVEL1:level_state_writer_f00` | `0x800B3F04` | request |
| `LEVEL02_LEVEL1:level_completion_handler_f08` | `0x800B440C` | request |
| `LEVEL03_LEVEL1:level_completion_handler` | `0x800B3B50` | request |
| `LEVEL03_LEVEL1:level_completion_handler` | `0x800B3CB0` | request |
| `LEVEL03_LEVEL1:level_completion_handler` | `0x800B4210` | request |
| `LEVEL04_LEVEL:level04_complete_handler` | `0x800B4038` | request |
| `LEVEL04_LEVEL:level04_complete_handler` | `0x800B40E4` | request |
| `LEVEL04_LEVEL:level04_complete_handler` | `0x800B410C` | timer |
| `LEVEL04_LEVEL:level04_complete_handler` | `0x800B43C0` | timer |
| `LEVEL04_LEVEL1:level_state_writer_c70` | `0x800B3C74` | request |
| `LEVEL04_LEVEL1:level_completion_handler` | `0x800B3CD4` | request |
| `LEVEL05_LEVEL:level_completion_handler` | `0x800B3EDC` | request |
| `LEVEL05_LEVEL:level_completion_handler` | `0x800B3FCC` | request |
| `LEVEL05_LEVEL:level_completion_handler` | `0x800B40D8` | request |
| `LEVEL05_LEVEL1:level_completion_handler` | `0x800B3C30` | request |
| `LEVEL05_LEVEL1:level_completion_handler` | `0x800B3DC4` | request |
| `LEVEL05_LEVEL1:level_completion_handler` | `0x800B3DEC` | timer |
| `LEVEL05_LEVEL1:level_completion_handler` | `0x800B3F0C` | timer |
| `LEVEL05_LEVEL1:level_completion_handler` | `0x800B3F2C` | timer |
| `LEVEL05_LEVEL1:level_completion_handler` | `0x800B3F48` | timer |
| `LEVEL06_LEVEL:level_transition_handler` | `0x800B3CFC` | request |
| `LEVEL06_LEVEL1:level_spawn_handler` | `0x800B3D5C` | request |
| `LEVEL07_LEVEL:level_completion_handler` | `0x800B4498` | request |
| `LEVEL08_LEVEL:level_state_writer_c74` | `0x800B3C78` | request |
| `LEVEL09_LEVEL:level_actor_ai_handler` | `0x800B441C` | request |
| `MEMORY:frontend_scroll_sprite_screen` | `0x800B7FC0` | request |

(The count reached 66 through three corrections, each of which raised it. **32**:
writer identity was keyed on pc alone, so two overlay LOADS —
`LEVEL05_LEVEL:0x800B3DEC` and `LEVEL04_LEVEL:0x800B410C` — were mislabelled as
already-enumerated writers belonging to LEVEL08 and LEVEL01; overlay addresses
repeat, so identity is `(image, pc)`. **34→50**: the census's extent ENDS were
hand-typed and 20 of 29 stopped short of the real function. **50→66**: a fresh
verifier found the extent SET was a subset too, and the census now scans every
code function in every image. This table is generated from that scan — if it and
the headline ever disagree, the artifact is authoritative.)

**Consequence for modding.** Changing when or how this word is set does not only
affect scene flow — it changes what the SFX dispatcher, the ambient sound
sequencer, the pickup sound path, the skinned-actor updater, the results screen,
the checkpoint save and every per-level handler observe. Any change here needs
those consumers in its regression surface.

⚠️ **238 of the 814 unresolved accesses in the window-touching extents are STORES** — 5,329 corpus-wide. (Reported as 106 of 403, then 231 of 795, before two extent-scope corrections.) Any one could write this
word. They are individually retained in
`analysis/phase4_f01_frontier_resolve.json` under `unresolved_sites`, and the
resolver exits non-zero while any remain. Until they are resolved or bounded,
**no completeness claim about this word's writers is supportable** — including
for a mod that assumes it knows every writer.

## What three of those readers actually do

The reader list above is a surface. These three are decoded, and each is a
cross-system coupling a mod to this state would trip.

### Checkpoint saving is suppressed for the whole countdown

```
80054CCC  lh   v0, [0x80082470]      ; the transition timer
80054CD4  bnez v0 -> 0x80054E94      ; 0x80054E94 is the function EPILOGUE
```

`checkpoint_save` returns immediately, doing nothing, whenever the transition
timer is nonzero. **No checkpoint can be taken while any transition countdown is
running** — entry, completion or death alike, since all three drive the same
timer.

### Player input is masked during the first half of scene entry

```
8004EEE8  lh   v0, [0x800823A0]      ; request
8004EEF0  bnez v0 -> 0x8004EF28      ; a request is pending -> skip
8004EEFC  lh   v0, [0x80082470]      ; timer
8004EF04  slti v0, v0, 0x1F          ; timer < 31 ?
8004EF08  bnez v0 -> 0x8004EF28      ; late in the countdown -> skip
8004EF14  lhu  v0, [0x80082488]      ; the pad-held word (G_PAD_HELD)
8004EF1C  andi v0, v0, 0x309
8004EF24  sh   v0, [0x80082488]
```

The mask applies only when **request == 0 and timer >= 31** — which is exactly
the scene-ENTRY transition, the one that sets request←0 and timer←45. So for the
first 15 ticks (~30 frames) of entering a scene the pad word is masked to
`0x309`, and after the timer falls below 31 it is not. That is the "you cannot
move during the fade-in" behaviour, precisely bounded.

### On death, every sound but the death sound is dropped

```
80050B84  lh   v1, [0x800823A0]
80050B8C  bne  v1, 2 -> 0x80050B9C   ; not a death transition -> normal path
80050B90  addiu v0, zero, 0x49       (delay slot)
80050B94  bne  s0, v0 -> 0x80050C1C  ; death transition and id != 0x49 -> BAIL
```

While request == 2, `sfx_dispatch` drops every sound except id `0x49` — and
`0x49` is exactly what the death path itself plays (`0x8004A898: jal sfx_dispatch`
with `a0 = 0x49`). The dispatcher knows about the death transition and silences
everything else for its duration.

Evidence: `analysis/phase4_f01_frontier_resolve.json`, decoded from the pristine
executable.

## Two more readers, synthesised from retained evidence

Neither needed new work; both were already decoded or nearly so elsewhere.

### `0x800526F4` — the in-game HUD, and a census name that is wrong twice

[[EXP_2026-08-04_phase4_e13_hud_results]] already decoded this. Two corrections
it makes, both of which the resolver inherited:

1. The function census calls `0x800526FC` **`results_screen_render`**. It is not
   the results screen — that is [[FUNC_800B7DA0_results_screen_evaluate_and_draw]]
   in `BITS/MEMORY.BIN`, which reads the unlock array `0x8009B878`, an address
   this function never touches. It is the **in-game HUD renderer**.
2. `0x800526FC` is not even a function entry. The real entry is `0x800526F4`, an
   8-byte head that reads the transition timer `0x80082470` and falls through.

So the HUD is gated on the transition state at its very entry, and the resolver's
hit at `0x80052734` on the request word is a second gate inside the same renderer.
**Anything that changes the transition state changes when the HUD draws.**

### `actor_skinned_update` — death forces the death animation

```
80056888  lh    v1, [0x800823A0]      ; request
8005688C  addiu v0, zero, 2
80056890  bne   v1, v0 -> 0x800568A0  ; not a death transition -> skip
80056894  addiu v0, zero, 0xF         (delay slot)
8005689C  sh    v0, [0x800A6588]      ; ANIM_INDEX = 15
```

While `request == 2`, the skinned-actor updater forces the player's animation
index (`0x800A6588`, `ANIM_INDEX` in `src_re/player_update_80048138.c`) to **15**
every frame — the death animation, held for the whole countdown.

### The death transition is now coherent across four subsystems

Setting `request = 2` does all of this at once, none of it from the scene-flow
code that sets it:

| subsystem | effect | site |
|---|---|---|
| scene flow | the transition finalizer `0x80045A60` is skipped | `0x8004FF30` |
| sound | every sound but the death cue `0x49` is dropped | `0x80050B8C` |
| animation | player animation forced to index 15 | `0x80056890` |
| checkpointing | suppressed for the whole countdown (via the timer) | `0x80054CD4` |

That is the shape of the coupling a mod has to respect: this word is read as a
mode by sound, animation, HUD and save code, not just by the scene machine.
