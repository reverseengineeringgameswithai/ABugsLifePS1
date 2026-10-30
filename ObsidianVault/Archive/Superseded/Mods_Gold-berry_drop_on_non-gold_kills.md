---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Mods/Gold-berry drop on non-gold kills.md
aliases:
  - "Gold-berry drop on non-gold kills"
migration_action: convert_to_mod
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Mods/Gold-berry drop on non-gold kills.md`
- Replacement/current location: `ObsidianVault/Mods/Gold Berry/MOD_gold_berry_token_drop.md`
- Archive reason: Mod behavior belongs outside Canon and should link to Canon addresses/functions.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gold-berry drop on non-gold kills
type: mod
updated: 2026-07-07
tags: [mod, berry, gold, drop, enemy, permanence, RCG-022]
status: built + hook-validated + operator-confirmed pickup
---

# Gold-berry drop on non-gold kills

> [!warning] Curated record exists
> This is the chronological working note. The curated mod record is [[MOD_gold_berry_token_drop]], with Canon dependencies in [[SYS_contact_objects_and_drops]], [[SYS_enemy_death_and_permanence]], [[SYS_hud_counters]], [[HOOK_800592A4_golddrop_death_tail]], and [[HOOK_800589D4_golddrop_pickup_default_branch]]. Preserve this note for provenance, but use the curated page for future implementation decisions.

> A gameplay mod: when an enemy dies while Flik holds a **non-gold** berry, a
> per-berry random chance spawns the retail spinning **gold-kill glyph** at the enemy.
> Walking into it **does not arm gold**. Instead, it credits that tagged enemy as
> defeated and removes it through the same permanent-defeat cleanup path used by a
> real gold-berry kill ([[Enemy death and permanence]], RCG-022). Standalone patch:
> `mod/patch_golddrop.asm`; manifest patch: `mod/mods/golddrop.asm`. Reference C:
> `mod/caves/golddrop.c`; known cave hazards: `src_re/known_crash_cave_hazards.c`.

## Known-good lock (2026-07-07)
- **Operator-confirmed working surface:** non-gold kills can spawn the floor collectible as the
  spinning type-120 gold-kill glyph, Flik can collect it by walking over it, and collection now
  increments the bottom gold-defeat counter correctly.
- **Counter mechanism:** pickup decrements `G_ENEMIES_REMAINING` (`0x800a658e`). The HUD counter is
  the native display value `LW(0x80082258) - LH(0x800a658e)`, so one quota decrement appears as one
  additional gold-style defeated enemy.
- Remaining visual/gameplay regressions are outside this locked behavior and should be handled
  separately; do not “fix” the token path back into a literal type-34 gold-berry equip pickup.

## Per-berry odds
Drop fires iff `rng_byte(0..255) < threshold`, `threshold = round(256/N)`, indexed by
the equipped berry (`equip index 0x800a6597`):

| equip idx | berry | chance | threshold |
|---|---|---|---|
| 0 | red | 1/12 | 21 |
| 1 | blue | 1/8 | 32 |
| 2 | homing (green) | 1/4 | 64 |
| 3 | gold | — (none; already gold) | 0 |
| 4 | mega homing | 1/2 | 128 |
| 5 | blackberry (custom, [[Blackberry net-new berry]]) | 1/6 | 43 |

Table lives in the manifest death hook at `0x80081188` (`.byte 21,32,64,0,128,43`). Index-5 only ever
occurs on a disc that also has the blackberry mod (`mod/patch.asm`); standalone it is dormant.

## How it works (reuses retail machinery — see `src_re/enemy_drops.c`)
- **Visible glyph already exists in retail:** `spawn_drop` (`0x80059e44`) type **120** is the
  spinning gold-kill glyph emitted by the original permanent-kill path. The mod tags the spawned
  contact record at `+0x1c` with the enemy pointer, clears its upward velocity/gravity so it
  stays where it dropped, sets flags `+0x33 = 0xe2` so Flik can collect it, and sets `+0x22 = 200`,
  matching the health leaf style timeout/despawn behavior.
- **Hook:** the one-shot hit/death tail in `contact_vs_actor_handler` at **`0x800592A4`**
  (`s2` = the dying enemy, pos `+0x4/+0x8/+0xc`) → `j golddrop_tramp`. This replaced the
  earlier death-animation updater hook at `0x80049958`, which can run multiple times for the
  same defeated enemy and mint duplicate tokens.
- **Manifest trampoline (`0x80081100..0x80081190`, pure asm)** fits in the gap before Blackberry
  `CAVE_SPEED` and `CAVE_THROW`: it gates on equip index in [0,5], looks up the per-berry
  threshold, rolls the game's own script-cursor entropy (`[0x800822f4]`), and on success calls
  `spawn_drop(enemy_x, enemy_y, enemy_z, type=120, extra=25)`, then zeroes `rec+0x10`/`rec+0x18`
  and changes `rec+0x33` from the native `0xe0` to collectible `0xe2`.
- **Pickup hook (`0x800589D4` → `0x80078D84..0x80078E04`)** runs only for action-id `123`
  records tagged at `+0x1c`. It clears the tag, calls the native misc HUD/FX pulse
  `0x800503fc(0x800b0198)`, decrements `enemies_remaining` (`0x800a658e`), fires the
  all-defeated event if that count reaches zero, then calls `enemy_update_deathanim(enemy, 1)`
  to use the same hit-tail finalizer as the retail permanent-kill path. This is the
  walk-over logic that makes the bottom counter advance without arming/equipping gold.

## Behaviour / lifecycle
- **Per-kill, independent:** the roll reads only the equip index + the shared RNG cursor and
  stores no per-drop state → a prior drop (grabbed, ignored, or despawned uncollected) never
  blocks a later roll. **No per-level cap** either (unlike the retail health-leaf's `0x800a6594<4`).
  So a whiffed berry does not require "leave and come back" — the next kill re-rolls immediately.
- **Drop landing + lifetime:** the drop is a type-120 contact object with the native spinning glyph
  descriptor. The mod zeros the native pop/fall fields so it does not rise and fall through the
  ground, and writes `+0x22 = 200`, copying the health-leaf style timed despawn. Pickup radius is
  generous (walk over it to collect).
- **Appearance:** the spinning gold glyph from `gold_berry_glyph.sav`, not a literal berry
  pickup and not an equip replacement.
- **Getting another kill:** these chasers don't respawn in place; respawn needs the spawn area
  to re-arm (leave the region and return) — base-game behaviour, separate from the drop roll.

## Build
```
python3 mod/build.py --patch mod/patch_golddrop.asm --no-caves --out build/ABL_golddrop --force
```
Three build.py flags were added: `--patch <file>` (alternate armips patch), `--only-cave <stems>`
(compile just the named cave(s) — avoids the pre-existing broken `tier3_walls.c`), and `--no-caves`
(skip all caves, for asm-only patches).

## Validation (2026-07-07, isolated DuckStation)
1. **Build:** `python3 mod/build.py --mods mod/mods.yaml --no-disc --force` and the full
   consolidated `build/ABL_ALLMODS` build passed. Embedded EXE verification passed.
2. **Cold boot/live RAM:** `build/ABL_ALLMODS.cue` boots. Live RAM contains the manifest hook
   `0x800592A4 → j 0x80081100`, the type-120 spawn call, the freeze writes to `rec+0x10/+0x18`,
   collectible flags `0xe2`, lifetime `200`, the pickup action-id `123` guard, the
   `0x800503fc(0x800b0198)` HUD/FX pulse, and finalizer arg `1`.
3. **Crash regression:** live RAM at the forbidden `0x8007EFE8..0x8007F0D8` range is zero in
   the rebuilt ALLMODS image; the previous streaming-table crash site is no longer patched.
4. **Movie trace:** the spider death hook fired once in `killing_spider.movie.json`
   after moving the hook to `0x800592A4`. Forced-drop verifier
   `/tmp/golddrop_pickup_verify.json` cold-booted `build/ABL_ALLMODS.cue`, forced only the
   odds table, spawned one glyph, warped Flik onto it, and forced quota `1 -> 0` to exercise
   the all-defeated branch. Results: death hook 1, spawn 1, pickup hook 1, HUD pulse 1,
   quota store 1, all-defeated call 1, finalizer call 1, valid CPU state after pickup.

Visual reference: `gold_berry_glyph.sav` — the spinning gold-kill glyph at the bottom of the screen.

## Notes / follow-ups
- Standalone disc does not include the blackberry berry, so index-5's 1/6 is dormant there.
  Combined Blackberry + gold-drop uses exact subranges in `mod/mods/registry.py`; keep the
  `0x80081100..0x80081190` gap free except for `golddrop`.
- The gate is "Flik holds a non-gold berry at the moment of death" (equip index), matching the
  request. Per-berry odds are tunable via the `0x80081188` table.
- Retail health-leaf drop is untouched; this is an independent, additional roll.
- Do **not** convert this to `type=38`/`extra=13` while storing the enemy pointer at `rec+0x1c`:
  health-leaf-style floor records use `+0x1c` as updater state, so the enemy tag corrupts the
  landing/render path. Keeping type 120 and freezing velocity/gravity leaves `+0x1c` available.
- **Known crash:** do not move manifest golddrop back to `0x8007EFE8..0x8007F0D8`. That range is
  the `0x800616e0` streaming/decompression table; the bad build crashed with invalid byte write
  `0x910A0000` at `PC=0x80061788`.
- **Known helper hazard:** do not put pickup helpers at `0x80081058..0x800810A4`. A live ALLMODS
  boot zeroed that range while the nearby `0x800810C0+` cave bytes survived.
- **Known duplicate-token hazard:** do not hook the per-frame death-animation updater at
  `0x80049958`. A forced-drop trace hit it six times for one spider death. Hook the
  contact-vs-actor hit tail at `0x800592A4` instead.

## Related
[[Enemy death and permanence]] · [[Berry projectile and homing]] · [[Blackberry net-new berry]] · [[Retail Gameplay Completeness Gap Audit]]
