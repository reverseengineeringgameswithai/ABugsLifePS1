---
kind: system
id: SYS_enemy_death_and_permanence
name: Enemy Death and Permanence
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_80058AF8
  - FUNC_800498AC
memory:
  - MEM_800A658E
  - MEM_800B0198
tables: []
constants:
  - CONST_HIT_PERMANENT
  - CONST_HIT_TEMPORARY
evidence:
  - EXP_2026-07-07_golddrop_pickup_verifier
  - src_re/enemy_death_permanence.c
src_paths:
  - src_re/enemy_death_permanence.c
---

# SYS_enemy_death_and_permanence

## Purpose

Canonical original-game model for enemy hit processing, temporary KO, permanent gold-style defeat, and the all-enemies quota ledger.

## Confirmed original-game behavior

- Enemy death/permanence lives inside `contact_vs_actor_handler` around `0x8005905C..0x800593B0`.
- Enemy `+0x6e` can be a local hit counter before death; the final death tail writes `999` as the death-animation trigger.
- `0x800A658E` is the per-level enemies-remaining / permanent-kill quota.
- A retail Gold Berry hit reaches the permanent branch and decrements `0x800A658E`.
- Red, blue, homing, mega, and Blackberry-style red damage do not spend `0x800A658E`; they are temporary KO paths among berry throws.
- The permanent branch pulses `0x800B0198`, may fire the all-defeated event when the quota reaches zero, and finalizes/removes the enemy through the native death-animation/finalizer path.
- The visible bottom gold-defeat count is derived as total enemies minus `0x800A658E`.
- `contact_vs_actor_handler` also sets `flags+0x5c` bit `0x2` (the CHASE bit, [[SYS_enemy_ai]])
  at `0x8005914C` (`ori v0,v0,2`), on the same non-lethal hit path as the local `+0x6e`
  counter — this was the previously-unpinned "setter" for that bit; full gate conditions
  and evidence in `SYS_enemy_ai.md` and `analysis/phase4_d09_redbug_identity.json`'s
  `STATIC_AUDIT_2026-08-02_who_sets_bit_0x2`.

## Temporary-KO respawn — REAL, requires the player to actually leave and return (2026-08-02)

⚠️ **This section previously claimed a NEGATIVE result ("does not respawn within 66s") for
Redbug, shell_bug, and worm. That claim was RETRACTED the same day it was made.** All three
tests killed the enemy and then watched with Flik stationary — the test never tried moving
the player away. The operator corrected this from direct gameplay knowledge: *"it will
respawn but not if Flik is near it. Flik would need to move away for it to come back."*
Re-tested live with Flik actually walking away (real controller input, not a position poke)
far enough (~76,000+ units, reliable on repeat runs) and it respawns — confirmed for
**Redbug (D09)** and **worm (D12)** this same day; shell_bug (D13) was not independently
re-run live but shares the identical original test design and is retracted on the same
basis. Full per-row detail: `analysis/phase4_d09_redbug_identity.json`,
`analysis/phase4_d13_shell_bug_armor.json`, and `analysis/phase4_d12_worm_id40.json`, each
under a `RESPAWN_TEST_2026-08-02_RETRACTED` key.

**Position pokes never reproduce it.** A single one-time teleport (even constructed with a
deliberately "real" one-frame `prev_pos`→`pos` delta) followed by 50 real seconds of
continuous execution, and many small per-frame position increments written via
`emulator.advanceFrames{frames:1}` reaching over 111,000 units total, both failed to trigger
it. Only genuine continuous real-time execution with actual controller input ever did.

**The mechanism, ASM-traced from a live `accessLog` write-watch (D12):** the actual reset —
id/position/mover-VM-program-pointer/hp/flags copied fresh from the actor's own spawn-chunk
template via its runtime-record backlink (`+0x80`), position shifted `<<5` matching the
documented spawn-anchor law — lives in a previously undocumented routine at `0x80049C2C`.
This is a genuine from-scratch re-instantiation, not a state toggle, and explains why a
revived actor's `vm_ip` lands near its program's own start rather than resuming where it
died. **This routine sits immediately adjacent to, and gets merged by `functionBounds` into,
the already-documented [[FUNC_800498AC]] `enemy_update_deathanim`** — an earlier draft of
this finding mis-attributed the reset to that function's own `a1=2` branch before a register
mismatch (`t0` vs `s0`) was caught; `FUNC_800498AC`'s own documented `1`/`2` bitmask contract
is unaffected and still correct (`2` is retirement, not revival). See the tooling-pitfall
note on that page.

**Historical unresolved state (superseded by the 2026-08-04 resolution below):** `0x80049C2C` has
zero static callers (reached via an indirect/computed jump) and an `execTrace` watch armed
on it produced zero hits even in a run where the reset demonstrably fired — almost certainly
an `execTrace` reliability gap under this project's usual resume/pause driving pattern
(the same 0-hits-despite-a-real-event pattern was independently hit once already this
session, tracing a wall_worm throw dispatch), not evidence the routine wasn't reached.
Separately, a per-actor per-frame update function (`0x8004D224`) contains BOTH a countdown
timer on each actor's own `+0x4A` field (set to a per-species negative constant at death,
ticked toward zero only while the actor is in the live table `0x80090748`, firing
`FUNC_800498AC`'s own `1`/`2` branches on crossing zero) AND a separate distance-based
admission check that populates that live table by comparing each actor to a cached anchor
point (`0x8009EC50`, itself fed from the camera's own tracked state via the already-Canon
`camera_follow_update`, not Flik's raw position). Read literally, that admission check
requires being *near* the anchor to be admitted — which would mean the timer ticks while
close and freezes while far, the **opposite** of the confirmed live behavior. This
contradiction, and the exact real trigger for `0x80049C2C` itself, are **open residuals**,
not resolved claims. Full detail and every caveat: `analysis/phase4_d12_worm_id40.json`'s
`RESPAWN_MECHANISM_2026-08-02`.

## Scheduler resolution - 2026-08-04

The prior contradiction combined two mutually exclusive scheduler branches.
At `0x8004D29C`, HP-positive actors enter live near-camera admission; KO actors
bypass it. KO actors count down `+0x62`, then `0x80025084` tests the fixed spawn
point against the camera visibility volume. Visible suppresses respawn;
off-screen reaches `0x8004D3F0: jal 0x80049C30`. Flag `0x10` bypasses the
visibility requirement.

The reinitializer entry is `0x80049C30`, not padding NOP `0x80049C2C`. Its
only direct pristine callers are construction at `0x8004A664` and runtime
scheduler at `0x8004D3F0`. It restores HP at instruction `0x80049CA0` and
seeds `+0x62` at `0x80049CC0`. The distinct `+0x4A` timer controls the
live-list death-animation/retirement pass.

This source-level result explains the D12 natural walk-away observation and
the failed position-poke controls. D05 is substantiated partial and
bounded-exhausted; per-species delay values and cosmetic death/drop/audio
cataloging remain deliberately outside the closure boundary.

See `analysis/phase4_d05_static_resolution.json` and
`ObsidianVault/Canon/Functions/FUNC_80025084_enemy_spawn_visibility.md`.

## Berry-tough class exclusion — RESOLVED live, 2026-08-02

D13_armored_beetles row, operator: *"those enemies won't take damage with red berries."*
Tested all 5 native berry classes against `shell_bug.sav` (actor `+0x5c` bit `0x40`,
berry-tough) on fresh, media-verified reloads per trial: **red (class 2) — zero damage
across 120 frames. Blue (5), homing (8), gold (11), mega (45) — all damage normally**
(gold reaches the permanent-finalization shape — the struck record's `id` field clears to
`0`, not just `+0x6e` — matching this page's existing permanent/temporary distinction
exactly). The berry-tough bit gates **only the red class**, not a graduated power
threshold and not a time-based window. Phase 4 D04 later pinned the exact exclusion: `0x80058EE4` tests enemy `+0x5C & 0x40`; `0x80058EF8` and `0x80058F08` divert connecting `+0x24 == 1` or `+0x2C == 1` into reaction-only handling, whose exit at `0x80059054` skips common damage and death. Other subtypes branch to `0x8005905C`. See `analysis/phase4_d04_static.json` and `EXP_2026-08-03_phase4_d04_berry_immunity_matrix`.

## Quota construction — CONFIRMED live, 2026-08-03

`0x800A658E` is not a per-level table constant. It is a field of Flik's own player struct
(`player+0x8E`), zeroed and rebuilt by the second half of [[FUNC_80046B20_FUNC_80046B20|FUNC_80046B20]]
(the same function already Canon for the level-load player-spawn write) immediately after
that spawn: a 64-iteration scan of the enemy actor pool (`0x8009FD80`, stride `0x84`) counts
one per slot where `id != 0` and flags `+0x5C & 0x08A0 == 0`. Live-confirmed via 4 `accessLog`
writes to PC `0x80046c64`, values `0→1→2→3→4`; cross-checked `level01.sav` (quota `4`) against
`level02.sav` (quota `50`). The `0x80`/`0x20` sub-mask matches D14_wasps_dragonflies' own
homing-non-targetability filter; bit `0x0800`'s meaning (boss-exclusion hypothesis) is not
confirmed. Full detail: `analysis/phase4_c04_enemy_token.json`,
[[EXP_2026-08-03_phase4_c04_enemy_token]].

**Token grant, confirmed live 2026-08-03**: reaching quota `1` (the last eligible enemy)
reaches an overlay handler that zeros the quota, spawns a Flik-positioned effect+SFX, and —
by unconditional fall-through, not a coincidence of timing — writes the SAME
`goal_latch=1`/`transition_ticks=150` pair (`0x800823A0`/`0x80082470`) already Canon from
D19_molt's own boss-defeat victory handoff, at the identical emulator frame. Confirmed via
the `LEVEL06.movie.json` 100% run: a "level complete" screen with three locked token icons
resolves to three revealed tokens once grain/FLIK/seed/enemy-elimination all complete, then
"Congratulations! Bonus Movie Clip Earned." The exact gating register (`s2`, hypothesized
objective-type selector) was not traced to its own caller — see
`TOKEN_GRANT_CONFIRMED_LIVE_2026-08-03` in the JSON.

## Mod boundary

Gold Berry token pickup is not original-game behavior. The mod intentionally spends this original-game ledger on pickup of a tagged type-120 glyph:

- Spawn hook: `HOOK_800592A4`.
- Pickup hook: `HOOK_800589D4`.
- Working mod record: `MOD_gold_berry_token_drop`.

## Do not promote

- Do not claim mega or homing berry kills are permanent. That is archived as `WHYPE_mega_permanent`.
- Do not use the side HP-table decrement as the kill definition. The side table floors and is not the permanent-defeat lever.
- Do not treat the mod's token-credit behavior as native type-120 pickup semantics.

## The side HP table, located and structured (2026-08-03, E14)

The long-warned-about side table is `0x80089938`: 64 records × 5 bytes, indexed
`table[actor_id*5 + equipped_berry_index]` (class from the Canon equipped-berry byte
`0x800A6597`), init `{100,255,255,255,255}`, **persisted in the memcard save** (serializer
bytes 28–347). KO paths in `FUNC_8004ABF4` decrement the entry by 2 while it exceeds `0x40`
(the "floors" behavior warned above); the actor initializer `FUNC_80049C30` clamps it up to
`0x40` and gates the chase bit at (re)spawn on entry ≥100 with grasshopper (id 15)
explicitly exempted — gate direction not yet live-confirmed. Values above 100 exist in real
saves (increment source unlocated). The do-not-promote warning above stands unchanged: this
table is still not the kill definition. Full decode:
`analysis/phase4_e14_frontend_save.json`, [[EXP_2026-08-03_phase4_e14_frontend_save]].

## Evidence

- `src_re/enemy_death_permanence.c` contains the live-confirmed RCG-022 findings and pseudo-code.
- `EXP_2026-07-07_golddrop_pickup_verifier` confirms that the Gold Berry token mod increments the visible bottom counter by decrementing this same quota on pickup.

## Phase 4 C10 Gold lethal/quota closure (2026-08-04)

Gold selector `127` applies exact `-4`, but permanence and quota spending are **lethal-only**. Contact first rewrites projectile subtype `4` to marker `11`; only after the actor-local counter reaches zero does marker `11` select permanent outcome bit `2`, write actor `+0x6E = 999`, and decrement `0x800A658E` once. A nonlethal Gold hit leaves the reduced counter and does not write quota.

The 64-slot quota constructor excludes empty ids and actor state `+0x5C & 0x08A0`; contact-time damage excludes current state `+0x5C & 0x00A0`. Berry-tough bit `0x40` alone is not excluded. See [[SYS_gold_berry]] and [[EXP_2026-08-04_phase4_c10_gold_berry]].

## Enemy-token quota boundary (C04, 2026-08-04)

The live remaining-enemy quota is 0x800A658E. Scene-runtime reset calls 0x80046B20 to rebuild it from the 64-entry actor pool, then snapshots the rebuilt value to 0x80082258. Ordinary resident death paths decrement it, while selected level overlays apply batch decrements, boss/set-piece normalization, or conditional cleanup-to-zero. The results overlay reports defeated enemies as initial total - remaining and gates its enemy award on remaining == 0.

Actor +0x5C flag mask 0x08A0 excludes entries during construction. Bit 0x0800 also bypasses a resident interaction/update tail at 0x8004B0C4; no stronger content-facing name is presently justified. Objective latches can be threshold-driven and merely perform a conditional quota cleanup, so quota == 0 must not be treated as a universal level-completion predicate. See [[EXP_2026-08-03_phase4_c04_enemy_token]].
