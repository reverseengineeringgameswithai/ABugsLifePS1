---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Mods/Blackberry net-new berry.md
aliases:
  - "Blackberry net-new berry"
migration_action: convert_to_mod
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Mods/Blackberry net-new berry.md`
- Replacement/current location: `ObsidianVault/Mods/Blackberry/MOD_blackberry_net_new_berry.md`
- Archive reason: Mod behavior belongs outside Canon and should link to Canon addresses/functions.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blackberry / Fastberry — net-new berry (mod)
type: mod
updated: 2026-07-07
tags: [mod, berry, blackberry, fastberry, patch, deliverable]
---

# Blackberry / Fastberry — net-new berry (MOD)

> [!warning] Curated record exists
> This is the chronological working note. The curated mod record is [[MOD_blackberry_net_new_berry]], with Canon dependencies in [[SYS_berry_projectile_and_homing]], [[SYS_berry_pickup_render_descriptors]], [[SYS_seed_plant_behaviors]], and [[HOOK_forbidden_patch_ranges]]. Preserve this note for provenance, but use the curated page for future implementation decisions.

> **This is a MOD, not OG-game RE.** The underlying reverse-engineering lives in
> [[Berry projectile and homing]], `src_re/berry_homing.c`,
> `src_re/berry_throw_80047170.c`, and `mod/berry_projectile.h`.
> The manifest key remains `blackberry`; kind `0x25` / equip index `5` is the active
> Blackberry/Fastberry lane.

## What it is
A genuine 6th berry, originals untouched: world **pickup** kind `0x25`, equip index `5`,
dark purple/black pickup and thrown visuals, and a faster red-style straight throw.

The throw path maps equip index `5` to native red dispatch, then flags the next
`contact_object_spawn` call for fast physics:

- `vel_x`, `vel_y`, and `vel_z` are doubled;
- gravity is quadrupled, preserving the same ballistic arc at half the flight time;
- thrown power stays red-class `2`, which keeps the actor-local `+0x6e` hit-counter
  lane red-equivalent;
- enemy damage HP-selector reads map index `5` to red selector `0`, so the later
  side HP-table lane also matches the native red berry.

This does not use the homing acquisition path and does not spawn extra spread shots.

## Caves
All caves are in `mod/patch.asm`.

| cave | hook/site | Blackberry behavior |
|---|---|---|
| `CAVE_SPEED` | `contact_object_spawn` / `0x8005a0f0` | consumes `NEWBERRY_FLAG`, applies 2x velocity + 4x gravity |
| `CAVE_ARM` | pickup dispatch `0x8001b480` | kind `0x25` collect -> `sb 5,0x6597` |
| `CAVE_THROW` | `0x80047170` | equip `5` -> native red dispatch index `0`, sets `NEWBERRY_FLAG` |
| `CAVE_GRAIN` / `CAVE_DESC_FIX` | `0x80025324` | route kind `0x25` through visible grain projection and repair `object_pointer_list[0x25]` to the private descriptor |
| `CAVE_RECOLOR` | `0x800259a0` | private pickup descriptor `0x80081234` -> dark blackberry modulation |
| `CAVE_TCOLOR` / `CAVE_TCOLOR2` | `0x800105f0` / `0x80014a70` | held/thrown/contact berry primitive recolor while equip index `5` |
| `CAVE_TOUGH_HPSEL` / `CAVE_HPSEL` | `0x800590F0` / `0x80059358` | enemy damage HP selector maps equip `5` -> red selector `0` |

## Values
- **Pickup kind:** `0x25` (37), private descriptor at `0x80081234`.
- **Equip index:** `5`.
- **Throw dispatch:** native red-equivalent straight path via dispatch index `0`.
- **Fast physics:** one flagged spawn gets velocity `<< 1` and gravity `<< 2`.
- **Power/class:** `2`, from the native red dispatch path. This is required for the
  actor-local `enemy+0x6e` hit-counter damage branch.
- **Enemy damage selector:** equip `5` is remapped to red HP selector `0` at the enemy
  damage reads for the separate side HP-table branch.
- **Colour word:** `0x2c2b051a` on the grayscale berry atlas.
- **One-shot flag byte:** `0x80081230`, between `CAVE_ARM` and `CAVE_GRAIN`.
- **Do not overwrite retail descriptor `0x80082030`:** that descriptor is used by native
  berry/seed visuals. A bad pass that reused it made seed/mega-homing colors regress.

## 2026-07-07 Restoration
An intermediate ALLMODS pass temporarily rewrote the index-5 lane into a white
three-shot spread. That made Training step 2 reveal the correct kind (`0x25`) but render
and throw the wrong berry. The active code has been restored to Blackberry/Fastberry:
no `0x80047254` spread hook, no `0x80048ffc` throw-counter gate, and no white colour
word. The Training gate still advances on the same collection signal, `0x800A6597 == 5`.

## Verification 2026-07-07
Rebuilt `build/ABL_ALLMODS.bin` SHA-256
`db7f5fbd2f6ec63e821e2061120c613fae4e6e3aebcaa5be11aa2411adb288fb`
(`build/ABL_ALLMODS.cue` SHA-256
`07d1c83c0b87ab7f14b0c9e6dc988ab8f70fda58de76fe1b4cdc7f9e1f37bf8e`).

Static embedded-EXE check:

- `0x8005A0F0 -> J 0x800810C0` (`CAVE_SPEED`);
- `0x80047170 -> J 0x80081190` (`CAVE_THROW`);
- `0x800590F0 -> J 0x800813B0` (`CAVE_TOUGH_HPSEL`);
- `0x80059358 -> J 0x800813D0` (`CAVE_HPSEL`);
- `0x80047228` is native again (`sw s1,28(sp)`), so index `5` gets red class `2`
  from the red dispatch path rather than a post-dispatch power override;
- old spread hook site `0x80047254` and old throw-counter gate `0x80048FFC` match pristine;
- no old white modulation literal remains in the blackberry cave span.

Isolated DuckStation verifier: config `/tmp/duckstation-red-black-power`, port `23516`,
token `red-black-power-20260707`, fork `fe0cca16...` dirty, binary SHA-256
`5538e0e0ca198b54f184ba5650e9a708ef4faf79b47180e49430e912fcc35448`.
Loaded `redberry_blackberry_test.sav` SHA-256
`e8e9fe74e3d26823aae1aea4ce5f965ee6495bad5e63b39713b977ba3810e3f1` with disc
validation enabled. That save was made before this selector fix and restores stale resident
EXE RAM, so the verifier patched the rebuilt resident words into RAM after each reload; a
fresh boot/new save made from this build does not need that RAM patch.

Runtime captures from the reloaded fixture:

- red baseline: native power store `0x80047228` captured `s1=0x00000002`;
- injected blackberry: same native power store captured `s1=0x00000002`;
- blackberry fast physics in one throw: pre-shift `a3/t1/t2/t3 =
  fffff5ad/fffff800/0000061e/00000080`, post-shift `ffffeb5a/fffff000/00000c3c/00000200`;
- thrown color store `0x800813A0` repeatedly wrote `v1=0x2c2b051a`;
- the HP-selector caves did not fire within the 240-frame post-throw window from this fixture,
  so no live enemy-contact damage write is claimed from that window; static/RAM readback verified
  both selector hooks and cave bodies were present.

Follow-up damage-parity verifier using `killing_spider.movie.json`:

- pristine red baseline: spider actor id `9` at `0x8009fd80` took two hits. The local
  `enemy+0x6e` counter went `2 -> 1` on the first hit, then `1 -> 0 -> 999` on the
  second hit; permanent quota `0x800a658e` did not decrement.
- rebuilt ALLMODS with forced equip index `5`: the speed hook fired, the throw power
  store `0x80047228` saw `s1=2`, and the same spider counter sequence occurred
  (`2 -> 1`, then `1 -> 0 -> 999`). This confirms Blackberry/Fastberry keeps red
  damage while retaining 2x velocity and 4x gravity.

The important rule for future edits: Blackberry damage parity depends on both the
throw-class route (`equip 5 -> native red dispatch, s1=2`) and the selector caves
(`equip 5 -> HP selector 0`). Changing only one of those can recreate the superberry
one-shot failure.

## Related
[[Berry projectile and homing]] · `src_re/berry_throw_80047170.c` · `src_re/berry_homing.c` ·
`mod/patch.asm` · `mod/berry_projectile.h`
