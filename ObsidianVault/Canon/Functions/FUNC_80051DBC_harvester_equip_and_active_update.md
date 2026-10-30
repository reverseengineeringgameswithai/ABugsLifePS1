---
kind: function
id: FUNC_80051DBC
aliases: [FUNC_80051DBC, 0x80051dbc, harvester_equip_and_active_update]
address: 0x80051DBC
name: harvester_equip_and_active_update
status: live_confirmed
confidence: confirmed
source_state: original_game
system:
  - SYS_grain_harvester
calls: []
reads:
  - 0x80082380
  - 0x80082488
  - 0x800A657C
  - 0x800A6582
  - 0x800A6588
  - 0x800A6590
  - 0x800A1DFC
writes:
  - 0x800A657E
  - 0x800A6590
uses_tables: []
related_constants:
  - 0x23
  - 0x80
  - 0x8000
related_hooks: []
evidence:
  - EXP_2026-07-30_phase4_c13_grain_harvester
  - analysis/phase4_c13_harvester.json
src_paths:
  - src_re/grain_harvester_80051db4.c
  - asm/nonmatchings/resident/80051dbc.s
patch_policy: do_not_touch
---

# FUNC_80051DBC - harvester equip and active update

Fresh Square, actor id `0x23`, grounded proximity, and idle gates enter the
harvester. `0x80051EA0` writes state `1`; `0x80051EB0` sets player-power bit
`0x80`; `0x80051F60` maintains the active state and the remainder mirrors
player position/animation into the authored harvester actor.

The prior `sfx_play_sound_glue` name is superseded. Cross disengagement is
behaviorally confirmed, but its exact clearing store remains unresolved.

See [[SYS_grain_harvester]].
