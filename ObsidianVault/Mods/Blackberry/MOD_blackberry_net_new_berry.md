---
kind: mod
id: MOD_blackberry_net_new_berry
name: Blackberry Net-New Berry
status: live_confirmed
confidence: confirmed
source_state: mod
canon_dependencies:
  - SYS_contact_objects_and_drops
  - SYS_berry_projectile_and_homing
  - SYS_berry_pickup_render_descriptors
  - SYS_enemy_death_and_permanence
hooks:
  - 0x8005A0F0
  - 0x8001B480
  - 0x80047170
  - 0x80025324
  - 0x800259A0
  - 0x800105F0
  - 0x80014A70
  - 0x800590F0
  - 0x80059358
src_paths:
  - mod/patch.asm
  - mod/berry_projectile.h
  - src_re/berry_throw_80047170.c
  - src_re/berry_homing.c
build_paths:
  - mod/mods.yaml
  - mod/mods/registry.py
evidence:
  - EXP_2026_07_07_blackberry_damage_parity
  - ObsidianVault/Archive/Superseded/Mods_Blackberry_net-new_berry.md
---

# MOD_blackberry_net_new_berry

## Purpose

Adds Blackberry/Fastberry as a sixth berry without changing the original five berries. The mod uses pickup kind `0x25`, equip index `5`, a private pickup descriptor, dark purple/black visuals, and a faster red-equivalent straight throw.

## Locked working behavior

- World pickup kind `0x25` arms equip index `5`.
- Equip index `5` routes through the native red throw dispatch, so the spawned contact object keeps red class/power `s1 = 2`.
- The next contact-object spawn is flagged for fast physics: velocity `<< 1`, gravity `<< 2`.
- Damage remains red-equivalent in both decoded damage lanes: throw class `s1 = 2`, and HP-selector reads remap equip index `5` to red selector `0`.
- Blackberry does not use the homing acquisition path and does not spawn spread shots.
- Pickup and thrown visuals use dark modulation `0x2c2b051a` on the grayscale berry atlas.

## Hook map

| Hook/site | Cave | Behavior |
|---|---|---|
| `0x8005A0F0` | `CAVE_SPEED` | Consumes `NEWBERRY_FLAG`; doubles velocity and quadruples gravity for one spawn. |
| `0x8001B480` | `CAVE_ARM` | Pickup dispatch slot for kind `0x25`; stores equip index `5` to `0x800A6597`. |
| `0x80047170` | `CAVE_THROW` | Maps equip `5` to native red dispatch and raises `NEWBERRY_FLAG`. |
| `0x80025324` | `CAVE_GRAIN` / `CAVE_DESC_FIX` | Routes kind `0x25` through visible projection and repairs `object_pointer_list[0x25]`. |
| `0x800259A0` | `CAVE_RECOLOR` | Recolors the pickup primitive when descriptor is `0x80081234`. |
| `0x800105F0` / `0x80014A70` | `CAVE_TCOLOR` / `CAVE_TCOLOR2` | Recolors held/thrown/contact berry primitives while equip index is `5`. |
| `0x800590F0` / `0x80059358` | `CAVE_TOUGH_HPSEL` / `CAVE_HPSEL` | Remaps side HP selector `5 -> 0` for red damage parity. |

## Critical values

- Pickup kind: `0x25`.
- Equip index: `5`.
- Private descriptor: `0x80081234`.
- One-shot fast-spawn flag: `0x80081230`.
- Color word: `0x2c2b051a`.
- Red-equivalent throw class: `s1 = 2`.
- Active implementation: `mod/patch.asm`.

## Descriptor safety

Do not overwrite native descriptor memory `0x80082030..0x8008203C`. That range belongs to native berry/seed visuals. A bad descriptor reuse caused seed colors to stop being purple and made mega/homing appear brownish-gold.

Blackberry uses private descriptor `0x80081234` and repairs `object_pointer_list[0x25]` at runtime. Future color work should preserve that model unless stronger live evidence proves a safer replacement.

## Source excerpt

Source: `mod/patch.asm`

```asm
.definelabel CAVE_SPEED,  0x800810C0
.definelabel CAVE_THROW, 0x80081190
.definelabel CAVE_ARM,   0x80081210
.definelabel NEWBERRY_FLAG, 0x80081230
.definelabel NEWBERRY_DESC, 0x80081234
.definelabel CAVE_GRAIN, 0x80081240
.definelabel CAVE_DESC_FIX, 0x8008127C
.definelabel CAVE_RECOLOR, 0x80081290
.definelabel CAVE_TCOLOR, 0x80081300
.definelabel CAVE_TCOLOR2, 0x80081360
.definelabel CAVE_TOUGH_HPSEL, 0x800813B0
.definelabel CAVE_HPSEL, 0x800813D0

new_throw:
    lbu     v1, 0x97(s0)
    addiu   at, zero, 5
    lui     t9, 0x8008
    bne     v1, at, nt_clear
    nop
    addu    v1, zero, zero          ; index 5 -> native red dispatch
    addiu   at, zero, 1
    j       nt_done
    sb      at, 0x1230(t9)          ; NEWBERRY_FLAG = 1

.org NEWBERRY_DESC
    .word 0x1f1f001d
    .word 0x00000000
    .word 0x0000003f

bb_desc_fix:
    addiu   at, gp, -0x0B64         ; gp=0x80081d98 -> NEWBERRY_DESC=0x80081234
    lui     v0, 0x8009
    sw      at, 0x6C2C(v0)           ; object_pointer_list[0x25]
    j       0x8002532c
    nop
```

## Verification

`EXP_2026_07_07_blackberry_damage_parity` records the 2026-07-07 validation:

- Static embedded-EXE checks confirmed active hooks and removed spread-shot hooks.
- Runtime throw captured `s1 = 2` at the native power store.
- Fast physics hook doubled velocity and quadrupled gravity.
- Thrown color store repeatedly wrote `0x2c2b051a`.
- Forced Blackberry against the spider matched red damage: `enemy+0x6e` went `2 -> 1`, then `1 -> 0 -> 999`; `0x800A658E` did not decrement.

## Non-goals and hazards

- Do not make Blackberry permanent like Gold Berry.
- Do not use homing/mega projectile acquisition for Blackberry.
- Do not reintroduce the old white three-shot spread.
- Do not reuse `0x80082030..0x8008203C` as descriptor scratch.
- Do not place helpers in `0x80081058..0x800810A4`.

## Provenance

The full chronological working note was formerly at
`ObsidianVault/Mods/Blackberry net-new berry.md`; migration archived it at
`ObsidianVault/Archive/Superseded/Mods_Blackberry_net-new_berry.md`. The Archive
citation is intentional provenance, while this page is the current curated mod record.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Mods/Blackberry net-new berry.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Mods_Blackberry_net-new_berry.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
