---
kind: function
id: FUNC_80025084
aliases: [FUNC_80025084, 0x80025084, enemy_spawn_visibility_predicate]
address: 0x80025084
name: enemy_spawn_visibility_predicate
status: static_confirmed
confidence: confirmed
source_state: original_game
system: [SYS_enemy_spawn_update]
calls: []
reads: [0x80090FB0, 0x80090FB4, 0x80090FB8, 0x80090FBC, 0x80090FC0]
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - EXP_2026-08-03_phase4_d05_death_respawn
  - EXP_2026-08-02_phase4_d12_worm_id40
  - analysis/phase4_d05_static_resolution.json
src_paths:
  - tools/phase4_d05_static.c
patch_policy: safe_to_read
---

# FUNC 0x80025084 - enemy spawn visibility predicate

## Canonical behavior

`0x80025084(camera_anchor, actor)` tests the actor's fixed spawn point against
the current camera-space visibility volume. It does not measure Flik-to-enemy
distance and does not use the actor's displaced runtime position.

The function obtains template coordinates through the actor's `+0x80` spawn
backlink, shifts those coordinates by five, subtracts the supplied camera
anchor, and evaluates camera plane/basis coefficients in
`0x80090FB0..0x80090FC0`. Actor extents at `+0x66` and `+0x6A` expand the test.
It returns `1` only when the spawn remains visible and `0` on a rejected plane.

## D05 scheduler use

The KO branch calls this predicate at `0x8004D3BC`. A nonzero result suppresses
respawn. A zero result reaches the direct `JAL 0x80049C30` at `0x8004D3F0`.
Consequently, natural walking causes respawn by moving the camera until the
fixed spawn leaves the view volume. Poking Flik or the dead actor's position is
not an equivalent control.

## Evidence

- Pristine executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- C guard/extractor: `tools/phase4_d05_static.c`
- Static result: `analysis/phase4_d05_static_resolution.json`
- D12 natural walk-away runtime donor: `analysis/phase4_d12_worm_id40.json`
