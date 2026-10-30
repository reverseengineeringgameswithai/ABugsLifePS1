---
kind: wrong_hypothesis
id: WHYPE_mega_permanent
status: resolved_wrong
confidence: confirmed
resolved_by:
  - ObsidianVault/_Revamp/CONFLICTS.md
  - ObsidianVault/Canon/Systems/SYS_enemy_death_and_permanence.md
  - src_re/enemy_death_permanence.c
---

# WHYPE_mega_permanent

## Wrong claim

Mega or homing berry kills are permanent like gold.

## Resolution

Wrong. Among berry throws, only gold reaches the permanent-kill gate and decrements `0x800A658E`.
Mega, homing, blue, red, and Blackberry-red damage are temporary KOs. Mine Plant is a separate confirmed permanent lane.

## Canon destination

- `Canon/Systems/SYS_enemy_death_and_permanence.md`
