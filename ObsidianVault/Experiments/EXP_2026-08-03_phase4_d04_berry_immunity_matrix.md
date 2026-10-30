# EXP 2026-08-03: Phase 4 D04 enemy berry immunity matrix

## Result

**D04 is a substantiated, bounded-exhausted partial and is ready to move past.** Enemy berry resistance is controlled by a runtime state gate, not an independent five-step resistance table for every species. The useful matrix collapses to ordinary damageable state versus `enemy+0x5C & 0x40` berry-tough state.

No new Interpreter movie was required. There is no D04-specific retained capsule, but existing hash-pinned artifacts contain complete five-berry controls for two independent tough species plus ordinary-enemy controls. Pristine executable analysis supplies the exact previously missing gate and damage/permanence control flow.

## Pinned evidence

- Pristine `SCUS_942.88`: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- Throw dispatch ASM: `a0582c0e351f4e6481f40e31a4219f11d9c3f0da2c1284fd1f45a3763cd47812`
- Contact handler ASM: `2c6313d72dad6d078c23b71028941c4d9306c925bf4d31a510d7bab66328906f`
- Damage dispatch ASM: `f1aa90ff4967fb3286dc49a1bd21099869dd467e2850a69449172da54f53bf44`
- Death tail ASM: `6871360b483149bb92b35e3deeb9f7a8a45626a70bafea495a1b9d24b70fedea`
- D12 worm evidence: `be8a60aafd07bc0b2543c772344dab1b07c5c02a43b0aafa5e54fa2a20abbedd`
- D13 shell-bug evidence: `51ad51bb93c9843e88511fd52fc846e58dd4191e1a0734842db203333c81ce3c`
- D07 mosquito evidence: `796b044b37d26d02b088f34866d16de81755c7aeb6605cc4ceac57a6736df612`
- D09 Redbug evidence: `1a45d3bf839f17fdf4b371571669fbdb6575540f2d1a393e45d56155b49cef4b`
- C outputs: `analysis/phase4_d04_static.json`, `analysis/phase4_d04_evidence.json`
- Closure record: `analysis/phase4_d04_bounded_exhaustion.json`

## Method

1. Query the external Phase 4 capsule inventory before live escalation. No D04/berry-resistance capsule exists.
2. Decode the resident throw, collision, resistance, damage, permanence, and side-table paths from the hash-verified pristine executable in C.
3. Join existing runtime artifacts in C after verifying hashes and semantic anchors.
4. Separate ordinary enemies, runtime berry-tough state, and boss-specific defeat FSMs.

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_d04_static.c -o /tmp/phase4_d04_static -lcrypto
/tmp/phase4_d04_static SCUS_942.88 > analysis/phase4_d04_static.json
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_d04_evidence.c -o /tmp/phase4_d04_evidence -lcrypto
/tmp/phase4_d04_evidence > analysis/phase4_d04_evidence.json
```

## Exact resistance gate

- `0x80058EDC`: load enemy `+0x5C`.
- `0x80058EE4`: mask bit `0x40`.
- `0x80058EE8`: if clear, branch to common damage at `0x8005905C`.
- `0x80058EF0` / `0x80058EF8`: tough actor with connecting `+0x24 == 1` enters reaction-only handling.
- `0x80058F00` / `0x80058F08`: tough actor with connecting `+0x2C == 1` also enters reaction-only; other subtypes reach common damage.
- `0x80059054`: reaction-only exit jumps to `0x80059284`, skipping local-counter damage and death/permanence processing.

The common local-counter deltas are:

| Connecting subtype `+0x2C` | Delta |
|---:|---:|
| 0 | -2 |
| 1 | -99 |
| 12 | -2 |
| 127 | -4 |
| 128 | -3 |
| Other | -1 |

Gold permanence is separate. Connecting `+0x24 == 11` sets permanent bit `2`; secondary kind `+0x27 == 6` is the mine-class permanent lane. Other native berries set temporary bit `1` only.

The table at `0x80089938 + actor_id*5 + equip_index` is not an immunity or kill table. Its death-tail consumer decrements by two only above a floor of 33; it does not determine local-counter death or spend the permanent quota.

## Runtime matrix

| Runtime resistance state | Red | Blue | Homing | Gold | Mega |
|---|---|---|---|---|---|
| Ordinary damageable | Temporary damage | Temporary damage | Temporary damage | Permanent defeat | Temporary damage |
| `flags & 0x40` berry-tough | Reaction only, zero damage | -2 temporary | -2 temporary | -4 plus permanent defeat | -3 temporary |

Evidence breadth:

- Shell bug: all five tested; only red produced zero damage.
- Worm id 40: all five tested; red zero, blue/homing `-2`, gold `-4`, mega `-3`.
- Wall worm: four admitted classes match; red negative carries a connectivity caveat.
- Spider: red local counter and gold-versus-non-gold permanence controls.
- Mosquito: berry-contact damage and gold-versus-non-gold permanence controls.
- Redbug: measured blue `-2` hits.

Bit `0x40` is runtime state and can be VM-managed, so the rows describe state at contact rather than permanent species identity. Bosses can reuse this damage dispatcher while applying separate HP floors, phase counters, and defeat FSMs; those remain owned by the boss rows.

## Closure boundary

**Observation:** two tough species have independent complete sweeps with the same outcome, with a third partial control and ordinary-enemy controls.

**Inference rejected:** every family owns a separate graduated resistance table.

**Causal confirmation:** pristine code contains one bit-`0x40` diversion, one shared damage-subtype switch, and one separate permanence gate.

The strict request for a replayable five-berry movie against every named family is not met. It would repeat the same resident gate across a large fixture campaign for little new mechanics. Reopen only for a contradictory family, a specific boss-resistance question, or an explicit full presentation-matrix deliverable. No Interpreter movie is currently required.
