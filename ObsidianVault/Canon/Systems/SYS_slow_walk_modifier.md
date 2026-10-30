---
kind: system
id: SYS_slow_walk_modifier
name: Slow-walk modifier
status: confirmed
updated: 2026-07-14
confidence: confirmed
evidence:
  - EXP_2026-07-14_phase4_slow_walk
---

# Slow-walk modifier

In the pristine PS1 game, either L2 or R2 modifies ordinary player locomotion.
This is a bounded modifier law, not the complete acceleration, turning, slope,
collision, or final-speed law owned by A01.

## Original-game facts

- The decoded action word is the resident `u16` at `0x80082488`. The player
  update reads it at `0x8004848C`, masks `0x0300`, and changes an intermediate
  horizontal-component bound from 1792 to 768 when either shoulder bit is set.
- The component-clamp region is `0x800493C0..0x80049443`; the resulting
  signed forward-component field is written at `0x800494AC`. The 768 constant must not
  be restated as a universal final-speed ratio because later composition,
  geometry, and the separately completed A01 law affect observed displacement.
- The resident actor-animation path reads the same action word at `0x800566D0`
  and writes locomotion animation 29 at `0x800566E8` on the applicable path.
- L2 and R2 produce equivalent A02 outcomes. R2 without movement does not
  select animation 29, release restores running animation 0, and re-entry
  selects 29 again.
- Riverbed Flight is an explicit exception: Up and R2+Up produced identical
  compared outcomes and animation 4 because that stage bypasses ordinary
  player locomotion.

All addresses, instruction words, region hashes, and provenance come from the
hash-pinned pristine `SCUS_942.88`. ALLMODS was not used as authority. The
machine contract is `config/phase4_slow_walk.yaml`, and the retained low-level
evidence is `analysis/phase4_slow_walk.json`.

## Runtime boundary

A timing-matched cold-boot movie branch added only R2 to an existing 60-frame
Up-only window. The control and edited branches had identical player fields,
player-block hash, emulator frame, and cycle at the edit boundary. After the
window, control animation was 0 and edited animation was 29.

Across Training, all fifteen campaign stages, and all three bonus stages, 18/18
ordinary locomotion anchors selected 29 under R2+Up and did not select 29 under
Up alone. Flight was the exact negative above. Pause froze the relevant fields;
after resume A02 reactivated. A native health-to-zero death/respawn transition
decremented lives, restored health, and re-read held R2+Up as animation 29.

## Reuse boundary

A MOD changing A02 must own initialization, reset, release retirement, capacity,
residency, and both movement and animation consumers. It must preserve the
flight exception unless intentionally changing special-stage behavior. A01 base
motion (now completed) and frontend remapping remain separately owned and are not silently
promoted by this finding.

See [[EXP_2026-07-14_phase4_slow_walk]],
[[Game Solving Campaign - Slow Walk Modifier]], and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
