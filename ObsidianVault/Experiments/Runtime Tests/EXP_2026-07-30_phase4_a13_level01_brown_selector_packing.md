---
kind: experiment
id: EXP_2026_07_30_phase4_a13_level01_brown_selector_packing
status: reproduced
created: 2026-07-30
updated: 2026-07-30
confidence: high
related:
  - PLAYBOOK_game_solving_phase_4
  - Seed_plant_output_binding
  - SYS_seed_carry_plant_lifecycle
---

# Phase 4 A13 — five-lane plant-output selector packing

## Result

Phase-4 row `A13_cycle_plant_output` uses a five-byte resident array:

| Color index | Seed color | Selector byte |
|---:|---|---|
| `0` | Brown/orange | `0x800A6598` |
| `1` | Blue | `0x800A6599` |
| `2` | Green | `0x800A659A` |
| `3` | Purple | `0x800A659B` |
| `4` | Yellow | `0x800A659C` |

For each lane, the byte is interpreted as:

```text
selected_output          = (selector >> 4) & 0x0F
highest_output_available = selector & 0x0F
plant_table_index        = color_index * 4 + selected_output - 1
```

The contiguous addresses and the `color_index * 4 + selected_output - 1` consumer
were already established by the disassembled plant spawner and the retained
20-entry live sweep in [[Seed_plant_output_binding]]. The 2026-07-30 operator
controls resolve what the two nibbles mean rather than rediscovering that table.

## Brown lane — independent-nibble proof

The brown lane at `0x800A6598` (`u8`; PCSX-Redux Memory Observer offset
`0x0A6598`) gives the clearest separation:

| High nibble | Brown-seed output |
|---:|---|
| `1` | Mushroom |
| `2` | Propeller |
| `3` | Dandelion |
| `4` | Cannon |

The low nibble is not a duplicate of the selected output. It is the maximum
available output:

- `0x11`: mushroom selected; mushroom is the maximum available;
- `0x12`: mushroom selected; propeller is the maximum available;
- `0x14`: mushroom selected; cannon is the maximum available;
- `0x34`: dandelion selected; cannon is the maximum available;
- `0x44`: cannon selected; cannon is the maximum available.

Changing the brown output with X changes the high nibble while the low nibble
remains the availability ceiling. LEVEL01 exposed the four-output sequence
`0x14`, `0x24`, `0x34`, `0x44`. The operator's LEVEL04 comparison exposed
`0x13`, `0x23`, `0x33`, `0x43`, separating the selected nibble from the
level/progression-dependent maximum.

## Purple lane — cross-color corroboration

The operator independently identified `0x800A659B` as the purple selector in two
levels and observed the same selected-high/maximum-low behavior. This agrees with
the previously decoded color-indexed array rather than introducing a separate
purple mechanism.

No new address search is required for blue, green, or yellow: the common plant
spawner already indexes the five contiguous lanes. Brown supplies the
independent-nibble proof and purple supplies a second-color, two-level behavioral
corroboration. Per-color output behavior remains covered by the corresponding
seed-plant campaign rows and the 20-entry binding table.

## Supersession

Older notes and C comments describe these bytes as counters encoded by duplicating
one value into both nibbles (`n * 17`). That observation is real but incomplete:
the token-upgrade path writes `(n << 4) | n`, making the newly selected tier equal
the newly available maximum. Subsequent output selection changes the high nibble
while preserving the low-nibble availability ceiling. Samples such as `0x33` and
`0x44` therefore captured the equal-nibble upgrade state, not the complete field
schema.

This note supersedes only the redundant-counter interpretation. Exact
writer/function ownership is intentionally deferred.

## Retained evidence

- `analysis/operator_evidence/phase4/A13_LEVEL01/brown_seed_changing_LEVEL01.csv`
  — 317 bytes, SHA-256
  `887627049f69a475203041ae4c456ce9f5cf18cf48ec5bfbd8341f627efbdeba`.
- Shared manifest:
  `analysis/operator_evidence/phase4/address_narrowing_manifest.yaml`.

The retained CSV is the LEVEL01 brown-lane address-filtering capture. The LEVEL04
brown comparison and the two-level purple comparison are operator behavioral
observations recorded here for the semantic decode; no purple CSV has been claimed
or manufactured.

## Phase-4 handoff

The operator-facing discovery work for A13 is complete. Future Phase-4 work should
consume the five-byte contract above rather than repeat address elimination or ask
for blue/green/yellow recordings solely to rediscover the array.

The row remains **partial**, not because more manual color discovery is required,
but because the reusable implementation contract still needs:

- Attribute the X-handler readers and writers.
- Confirm the wrap edge and denied-selection feedback.
- Determine reset, transition, and save/load persistence.
- Promote the five-byte field names and nibble helpers into the authoritative
  symbols/C/schema layer and add executable guards.
- Characterize zero, locked, and malformed selector values without treating them
  as ordinary `1..4` states.

A13 can proceed without further operator recordings unless one of those mechanical
checks contradicts the shared-array law.
