---
kind: hook
id: HOOK_800589D4
address: 0x800589D4
name: golddrop_pickup_default_branch
status: live_confirmed
confidence: confirmed
source_state: modding_policy
system:
  - SYS_contact_objects_and_drops
original_function:
  - FUNC_800586B0
used_by_mods:
  - MOD_gold_berry_token_drop
evidence:
  - EXP_2026_07_07_golddrop_pickup_verifier
  - mod/caves/golddrop.c
  - EXP_2026-07-07_golddrop_pickup_verifier
src_paths:
  - mod/caves/golddrop.c
  - mod/mods/golddrop.asm
patch_policy: hook_candidate
---

# HOOK_800589D4 - golddrop_pickup_default_branch

## Original-game context

Default collect branch in the contact walker. The Gold Berry token mod only acts on `action_id 123` records that also carry a valid enemy pointer tag at contact-record `+0x1c`.

## Modding policy

Keep this hook inert for native/default records. The hook must:

- Require `action_id == 123`.
- Require `+0x1c` to contain a valid tagged enemy pointer, not allocator-default `-1`.
- Clear the tag before crediting the pickup so a record cannot grant duplicate credits.
- Decrement `0x800A658E`, pulse `0x800B0198`, fire the all-defeated event only when the quota reaches zero, then call the native finalizer shape.

## Evidence

- `mod/mods/golddrop.asm` implements the guarded pickup path at `0x80078D84..0x80078E04`.
- `mod/caves/golddrop.c` records the C-shaped reference behavior.
- `EXP_2026_07_07_golddrop_pickup_verifier` observed pickup hook 1, HUD pulse 1, quota store 1, all-defeated call 1, and finalizer call 1.
