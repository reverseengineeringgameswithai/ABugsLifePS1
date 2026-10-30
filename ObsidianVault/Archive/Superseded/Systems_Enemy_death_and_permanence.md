---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Enemy death and permanence.md
aliases:
  - "Enemy death and permanence"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Enemy death and permanence.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Enemy_death_and_permanence.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Enemy death and permanence
type: system
updated: 2026-07-07
tags: [system, enemy, combat, berry, death, permanence, gold-berry, RCG-022]
confidence: CONFIRMED-live
---

# Enemy death / despawn + gold-berry permanence

> RCG-022. Live RE 2026-07-03 (isolated DuckStation, SCUS-94288). Resolves the
> [[Berry projectile and homing]] residual *"Floor/death is unresolved"* and the
> audit gap *"full enemy death/despawn state is not [understood]"*.
> **Headline: an enemy dies from the hit-marker/death-anim path, NOT from the HP
> byte reaching 0. "Permanent" = a per-level kill quota that ONLY the gold berry
> spends.** RE source: `src_re/enemy_death_permanence.c`.
> 2026-07-07 update: `enemy+0x6e` is also a local hit counter before death on
> some actors. The spider in `killing_spider.movie.json` starts at `2`; red and
> forced Blackberry both require two hits (`2 -> 1`, then `1 -> 0 -> 999`).

## Where it lives
All of it is inside **`contact_vs_actor_handler` (`0x80058af8`)** — the per-frame
walker that overlaps contact objects (berries + berry sub-objects) against the
damageable-enemy pointer table `0x80090748` (≤64 slots). The death/permanence
logic is its per-enemy path: local hit-counter branch `0x8005905c..0x80059160`,
then the final hit/death/permanence tail `0x8005929c..0x800593b0`. `s7` = a
hit-strength accumulator (init 0); permanence still reduces to the value of `s7`.

## The permanence ledger — `G_ENEMIES_REMAINING 0x800a658e`
- `u16`, **per level** (live: `spider_walking.sav` = 21, `earthworm.sav` = 50).
- A **gold** kill decrements it by 1. **mega / homing / blue / red do NOT touch it** (user-confirmed: *"that is normal behaviour"*).
- When it hits **0**, the destroy block calls **`all_enemies_defeated_event 0x8005182c`** (`a0 = 0x80090b68`) — the all-enemies-permanently-cleared reward/event.
- ⇒ this counter is the **permanent-kill quota**; the gold berry (and, likely, the yellow **Mine Plant** — see the 2nd lane) is the only thing that spends it.
- **Gold-drop mod lock (2026-07-07):** [[Gold-berry drop on non-gold kills]] spends the same ledger
  on walk-over pickup of a tagged type-120 glyph. That makes the bottom gold-defeat counter advance
  without arming gold, because the HUD displays `LW(0x80082258) - LH(0x800a658e)`.

## The hit tail (per struck enemy `s2`, per contact object `s1`)
1. **Local `+0x6e` hit-counter branch `@0x8005905c`:**
   ```
   hp = lh 0x6e(s2)
   if hp >= 100: skip local decrement      ; 999 death marker is exempt
   cls = lbu 0x2c(s1)                      ; contact-record damage class
   class 0,12 -> hp -= 2
   class 1    -> hp -= 99
   class 127  -> hp -= 4
   class 128  -> hp -= 3
   default    -> hp -= 1
   sh hp,0x6e(s2) @0x800590e4
   if hp > 0: hit feedback only; no 999 death tail yet
   if hp <= 0: continue into the hit/death tail
   ```
   This is why spider red/Blackberry damage is a two-hit behavior: the first hit
   changes `+0x6e` `2 -> 1`; the second changes `1 -> 0`, then the final tail
   writes `999`.
2. **Permanence gate `@0x800591f0`:**
   ```
   lh  v1, 0x24(s1) ; beq v1, 11 -> s7 |= 2    ; == 11  => PERMANENT   <-- GOLD
   lbu v1, 0x27(s1) ; bne v1, 6  -> s7 |= 1    ; != 6   => temporary
                       s7 |= 2                  ; == 6   => also PERMANENT (LIKELY Mine Plant)
   ```
   For a straight **gold** throw the connecting contact object carries `+0x24 == 11` (gold's throw class). The **primary thrown-berry** record instead carries `+0x24 == model` (110 basic / 123 homing / 124 mega) and never 11 — which is exactly why mega/homing/blue never satisfy the gate. Empirically the `s7|=2` branch (`0x80059210`) fires **for gold only (3/3), never for the others**.
3. **Hit applied `@0x8005929c`** (after the local counter reaches <=0, or for contacts that bypass that wait):
   `+0x6e = 999` (death-anim trigger) · `+0x60 = 0` · `+0x5c |= 0x880` (recoil bits) & `&= ~0x2` (clear alive bit) · `+0x70 = [enemy_hit_program_ptr 0x80077b2c]` (swap mover-VM program to the hit/death routine).
4. **Permanent-destroy block `@0x800592cc`** — only if `s7 >= 2`:
   `slti v0,s7,2 ; bne -> skip` · spawn destroy FX (`0x800503fc(0x800b0198)`) · `+0x62=0` · **`[0x800a658e] -= 1`** `@0x80059300` · if 0 → `all_enemies_defeated_event` · spawn death pickup/particles (`0x80059e44`, `a3=120`).
5. **Finalise `@0x80059340`** (both paths): `enemy_update_deathanim 0x800498ac(enemy, 1)` — advances the death animation; its own `+0x6e==998` branch (`@0x800498cc`) is the animated tail (also spawns FX + decrements the quota).
6. Then the legacy **`-2` HP side-table** write `@0x80059384` (`enemy_hp_table 0x80089938`, selector = equip index `0x800a6597`). It **floors at 33** so it never reaches 0 and is separate from the local `+0x6e` counter — it is **NOT the kill**.

## Observed aftermath (spider chaser id 9, ~180 f post-hit)
| berry | quota `0x800a658e` | `+0x6e` | enemy removed from `0x80090748`? | enemy id `+0x00` | verdict |
|---|---|---|---|---|---|
| **gold** | **21 → 20 (at the hit)** | 999 → 0 | yes (~90 f) | **ZEROED** | **permanent kill** |
| mega | 21 (unchanged) | 999 → 0 | yes (~90 f) | left = 9 | temporary KO (quota still owes it → may respawn) |
| homing / blue | 21 (unchanged) | 999 → 0 | yes | left | temporary KO |
| red / Blackberry | 21 (unchanged) | 2 → 1, then 1 → 0 → 999 | after second death tail | left | temporary two-hit KO; red-class damage |

## Spider two-hit verifier (2026-07-07)
`killing_spider.movie.json` was replayed on pristine and rebuilt ALLMODS:

- **Pristine red baseline:** throw power store `0x80047228` saw `s1=2`; spider id `9`
  at `0x8009fd80` changed `+0x6e` `2 -> 1` on the first hit and `1 -> 0 -> 999`
  on the second. Side HP table wrote `0x80089965` `100 -> 98` near the second
  hit/death tail. Quota `0x800a658e` did not decrement.
- **Forced Blackberry/Fastberry:** equip index `5` was forced before the same throws
  on rebuilt ALLMODS. The speed hook fired, the throw still stored red class `s1=2`,
  and the same `+0x6e` sequence occurred (`2 -> 1`, then `1 -> 0 -> 999`). This
  verifies that Blackberry currently has red damage, not blue/superberry one-shot
  behavior, while retaining 2x velocity and 4x gravity.

## Method / fixtures
- **Chasers are homing targets** → mega/homing auto-connect; **gold is aimed** by holding a direction so Flik keeps moving and the chaser closes in (chase gate `0x800a6538`). Throw = hold **Square** via `setControllerState` (a released→pressed edge is required; a single `pressButton` from a paused state does not fire).
- Breakpoints (`debugger.addBreakpoint type:execute`) on the gate `0x800591f0`, `s7|=2` `0x80059210`, the quota decrement `0x80059300`, the 999-marker `0x800592a8`, and `0x800498ac`; register + memory dumps on hit.
- Fixtures: `spider_walking.sav`, `mosquito.sav` (both gold-permanent, 3/3 + 1/1). `worm.sav`/`earthworm.sav` are the **berry-TOUGH mover-VM** enemies (`+0x5c` bit `0x40`) but are **not homing targets**, so they need a manually-aimed gold to confirm the same path (open).
- The spawner is called with the **class in `t0`** = red 2 / blue 5 / homing 8 / **gold 11** / mega 45 (breakpoint `contact_object_spawn 0x8005a0f0`, `ra=0x80047254`), confirming the equip index `0x800a6597` drives the throw class.

## Corrections to prior notes
- **`mega` is NOT permanent.** [[Berry projectile and homing]] previously said *"gold(11)/mega(45) = permanent"*. Live: mega leaves the quota untouched; **only gold is permanent** via the `==11` gate.
- Death is **not** the `-2` HP byte hitting 0 (it floors at 33). Death is the `+0x6e=999` / `+0x70` program-swap / `enemy_update_deathanim` path.
- `+0x6e` should not be documented only as a hit marker. Before the death tail it can
  be the actor-local hit counter; after the tail it becomes the `999` death marker.

## Residuals
- ~~The **2nd permanent lane** `+0x27==6`~~ — **✅ CONFIRMED 2026-07-03** → [[Yellow seed plant behaviors]]: the **MINE plant** (type 11) explosion record carries `+0x27==6` (caught at the gate: class=2000 record → `s7|=2` → quota 15→14). ABL's two permanent-kill sources: GOLD berry (`+0x24==11`) + MINE plant (`+0x27==6`).
- Directly observe a temporarily-KO'd enemy **respawning** to nail the temporary/permanent contrast end-to-end.
- Confirm the same tail for **berry-tough mover-VM** enemies (worm/earthworm) with an aimed gold.
- Enemy struct death fields catalogued in `src_re/enemy_death_permanence.c` (`+0x00 id`, `+0x5c` state bits `0x40`/`0x880`/`0x2`/`0xa0`, `+0x6e`, `+0x70`).

## Related
[[Berry projectile and homing]] · [[Enemy AI state machine]] · [[Retail Gameplay Completeness Gap Audit]] (RCG-022/RCG-006) · [[Seed plant output binding]] · [[Event and scripting system]]
