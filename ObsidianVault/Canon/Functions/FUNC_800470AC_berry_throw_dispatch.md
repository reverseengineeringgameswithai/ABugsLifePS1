---
kind: function
id: FUNC_800470AC
aliases: [FUNC_800470AC, 0x800470AC]
address: 0x800470AC
name: berry_throw_dispatch
status: live_confirmed
confidence: confirmed
source_state: original_game
system:
  - SYS_berry_projectile_and_homing
calls:
  - FUNC_80046D24
  - FUNC_8005A0E0
reads:
  - MEM_800A6597
writes:
  - MEM_800A6596
uses_tables:
  - TABLE_8001B1C0
  - TABLE_8007941C
evidence:
  - analysis/phase4_berry_throw.json
  - EXP_2026-07-15_phase4_berry_throw
src_paths:
  - asm/hand_written/800470ac_berry_throw_dispatch.s
patch_policy: preserve_native_selector_and_spawn_abi
---

# FUNC_800470AC - berry throw dispatch

The byte-matched resident function starts at `0x800470AC`. It reads the native
selector at `0x80047170`, bounds it to 0..4 through the jump table at
`0x8001B1C0`, selects primary types 2/5/8/11/45, increments the in-flight count,
constructs spawn position/velocity/gravity, calls `0x8005A0E0`, and requests SFX 2.

Selectors 0/1/3 call aim helper `0x80046D24`; 2/4 use heading with vertical
velocity -2048. Exact selector-only live controls and the cold-boot Square-only
branch are retained in `analysis/phase4_berry_throw.json`. Canonical system:
[[SYS_berry_projectile_and_homing]].
