---
kind: hook
id: HOOK_800592A4
address: 0x800592A4
name: golddrop_death_tail_hook_site
status: live_confirmed
confidence: confirmed
source_state: modding_policy
system:
  - SYS_enemy_death_and_permanence
original_function:
  - FUNC_80058AF8
used_by_mods:
  - MOD_gold_berry_token_drop
evidence:
  - EXP_2026_07_07_golddrop_pickup_verifier
  - src_re/enemy_drops.c
  - EXP_2026-07-07_golddrop_pickup_verifier
src_paths:
  - src_re/enemy_drops.c
  - mod/mods/golddrop.asm
patch_policy: hook_candidate
---

# HOOK_800592A4 - golddrop_death_tail_hook_site

## Original-game context

One-shot contact-vs-actor hit/death tail where `s2` is the dying enemy and the final death marker is being established. The displaced instructions are replayed by the mod trampoline before returning to `0x800592AC`.

## Modding policy

This is the known-good Gold Berry token spawn hook. It runs once for the tested spider death and has the enemy pointer live in `s2`, so the mod can tag the spawned glyph with the correct enemy.

## Rejected hook

Do not use `0x80049958` for Gold Berry token spawning. A forced-drop trace showed that updater path can run multiple times for one defeated enemy and mint duplicate tokens. The rejected pattern is archived in `WHYPE_gold_drop_type34_and_80049958`.

## Evidence

- `mod/mods/golddrop.asm` patches `0x800592A4` to jump to `golddrop_death_tramp`.
- `EXP_2026_07_07_golddrop_pickup_verifier` observed death hook 1 and spawn 1 for the forced-drop verifier.
