---
kind: wrong_hypothesis
id: WHYPE_gold_drop_type34_and_80049958
status: resolved_wrong
confidence: confirmed
resolved_by:
  - ObsidianVault/_Revamp/CONFLICTS.md
  - ObsidianVault/Mods/Gold Berry/MOD_gold_berry_token_drop.md
  - src_re/enemy_drops.c
  - mod/caves/golddrop.c
---

# WHYPE_gold_drop_type34_and_80049958

## Wrong claim

The Gold Berry drop mod should spawn a literal type-34 gold berry, and `0x80049958` is a safe once-per-kill hook for that spawn.

## Resolution

Wrong for the current mod.

- Type 34 is original-game "arm/equip gold" pickup behavior.
- The Gold Berry token mod uses type 120/action 123, the spinning gold-kill glyph.
- `0x80049958` can execute multiple times for one death and can mint duplicate tokens.
- The known-good spawn hook is `0x800592A4`; the pickup hook is `0x800589D4`.

## Canon destinations

- `Mods/Gold Berry/MOD_gold_berry_token_drop.md`
- `Canon/Hooks/HOOK_800592A4_golddrop_death_tail.md`
- `Canon/Constants/CONST_drop_types_and_actions.md`
