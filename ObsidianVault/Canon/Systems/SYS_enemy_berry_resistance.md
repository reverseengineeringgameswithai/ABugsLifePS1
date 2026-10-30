---
kind: system
id: SYS_enemy_berry_resistance
name: Enemy Berry Resistance
status: confirmed
confidence: confirmed
source_state: original_game
functions: [FUNC_80058AF8, FUNC_8005905C]
memory: [MEM_80089938, MEM_800A658E]
evidence:
  - EXP_2026-08-03_phase4_d04_berry_immunity_matrix
  - analysis/phase4_d04_static.json
  - analysis/phase4_d04_evidence.json
---

# Enemy berry resistance

Enemy berry resistance is a runtime state gate in `contact_vs_actor_handler`, not a per-species graduated strength table.

At `0x80058EE4`, the handler tests `enemy+0x5C & 0x40`. If clear, the contact reaches common local-counter damage at `0x8005905C`. If set, connecting record `+0x24 == 1` or `+0x2C == 1` is diverted to reaction-only handling and skips damage/death processing. Runtime controls bind the excluded connecting form to red berries. Other native berries reach the common dispatcher.

Common subtype deltas are `0:-2`, `1:-99`, `12:-2`, `127:-4`, `128:-3`, and default `-1`. Tested berry-tough actors produce red zero, blue/homing `-2`, gold `-4`, and mega `-3`.

Gold permanence is separate: connecting `+0x24 == 11` sets the permanent hit bit and spends `0x800A658E` on defeat. Red, blue, homing, and mega are temporary enemy defeats. Secondary kind `+0x27 == 6` is the mine-class permanent lane.

Shell bug and worm id 40 each have complete five-berry runtime sweeps. Wall worm independently matches the admitted classes, while spider, mosquito, and Redbug cover ordinary damage/permanence lanes.

Boundaries:

- Bit `0x40` is runtime state and may be VM-managed.
- `0x80089938` is a five-column side-state table, not the immunity or kill oracle.
- Boss-specific HP floors and defeat FSMs remain owned by their boss rows.
- Mega and homing defeats are not permanent.

See [[EXP_2026-08-03_phase4_d04_berry_immunity_matrix]].
