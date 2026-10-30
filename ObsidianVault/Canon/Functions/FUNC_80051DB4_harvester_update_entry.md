---
kind: function
id: FUNC_80051DB4
aliases: [FUNC_80051DB4, 0x80051db4, harvester_update_entry]
address: 0x80051DB4
name: harvester_update_entry
status: static_seen
confidence: confirmed
source_state: original_game
system:
  - SYS_grain_harvester
calls:
  - FUNC_80051DBC
reads:
  - 0x80082488
writes: []
uses_tables: []
related_constants:
  - 0x8000
related_hooks: []
evidence:
  - EXP_2026-07-30_phase4_c13_grain_harvester
  - analysis/phase4_c13_harvester.json
src_paths:
  - src_re/grain_harvester_80051db4.c
  - asm/nonmatchings/resident/80051db4.s
patch_policy: do_not_touch
---

# FUNC_80051DB4 - harvester update entry

Eight-byte entry that loads the current controller word from `0x80082488` and
falls through to [[FUNC_80051DBC]]. The prior `global_mode_flags_read` name is
superseded by the pristine static path plus the retained C13 behavior.

See [[SYS_grain_harvester]].
