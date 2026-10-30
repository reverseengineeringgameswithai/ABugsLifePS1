---
kind: system
id: Seed_plant_output_binding
created: 2026-07-08
updated: 2026-08-03
status: confirmed
confidence: confirmed
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Seed plant output binding.md
aliases:
  - "Seed plant output binding"
archived_source: ObsidianVault/Archive/Superseded/Systems_Seed_plant_output_binding.md
patch_policy: unknown
evidence:
  - EXP_2026-07-30_phase4_a13_level01_brown_selector_packing
  - EXP_2026-08-03_phase4_a13_bounded_exhaustion
---

# Seed_plant_output_binding

## Five-lane output selection and availability array

Phase-4 A13 uses five contiguous packed selectors:

| Address | Seed lane |
|---|---|
| `0x800A6598` | Brown/orange |
| `0x800A6599` | Blue |
| `0x800A659A` | Green |
| `0x800A659B` | Purple |
| `0x800A659C` | Yellow |

The common field contract is:

```text
selected_output          = (value >> 4) & 0x0F
highest_output_available = value & 0x0F
plant_table_index        = color_index * 4 + selected_output - 1
```

For brown, selected output `1/2/3/4` means
mushroom/propeller/dandelion/cannon. Thus `0x12` means mushroom selected with
propeller as the maximum available output, while `0x44` means cannon selected with
cannon as the maximum. LEVEL01 exposed a fixed low nibble of `4` while X changed
the high nibble through all four outputs; LEVEL04 exposed a fixed low nibble of `3`
with the same independent selected-output nibble. Purple independently reproduced
the same nibble law at `0x800A659B` in two levels.

The older `n * 17` observation describes the token-upgrade write, which initializes
selected output and maximum available output to the same tier. It is not the
general runtime schema after output selection changes only the high nibble. See
[[EXP_2026-07-30_phase4_a13_level01_brown_selector_packing|the retained A13 experiment]].
The common array and plant-table consumer are confirmed. Phase-4 continuation
[[EXP_2026-08-03_phase4_a13_bounded_exhaustion]] owns the exact X handler,
wrap/denial behavior, timeout, writer frontier, lifecycle, and malformed-state bounds.

## X cycle and timeout

`player_contact_response` owns cycling at `0x80047A88..0x80047B9C`. A carried seed
and rising X edge (`0x4000`) select the lane from source-record color `+0x0E`.
Availability below 2 is a silent no-op. Otherwise the high nibble advances, wraps to
1 above the low-nibble ceiling, updates the token descriptor, dispatches event `-16`,
and arms `0x800824A4` to 120.

At timer expiry, all five lanes normalize to `maximum * 17`: the selected output
returns to the highest available output. Level load clears the array and then writes
brown `0x11`; respawn preserves it. The plant consumer does not guard malformed
selected values before indexing `0x8007A448`.

The direct retail-overlay frontier is read-only: LEVEL07 reads brown/green and
LEVEL09 reads yellow. No overlay writes a selector.

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Seed plant output binding.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Seed → plant output binding (HRE-004)
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Seed_plant_output_binding.md`
- Migration action: `convert_to_canon`
- Migration confidence: `confirmed`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Seed → plant output binding (HRE-004)`
- `## The selection law (CONFIRMED, disassembled + live-swept)`
- `## The full 20-entry matrix (0x8007A448, dumped + all 20 live-verified)`
- `## Plant slots (runtime)`
- `## Natural trigger path (jump-on-seed)`
- `## Model binding: type N ↔ PLANTNN.ALL (CONFIRMED)`
- `## Interaction handlers (mature plants)`
- `## Token pickup side (already known, now connected)`
- `## Level-editor implications`
- `## Residuals (bounded)`
- `## Repro`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Seed_plant_output_binding.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
## Runtime timeout gate confirmation (2026-08-03)

The selection timer at `0x800824A4` is armed to 120 immediately by an accepted Cross press at `0x80047B9C`. It is not guaranteed to decrement immediately.

The player update first computes a nearest-eligible-actor pointer at `0x8008242C`. `0x800472B8` clears the pointer each gameplay tick. The scan stores a nearest actor at `0x8004736C` when `actor+0x5C` has bit `0x20`, actor state at `+0x40` is not 4, and scaled squared distance is below `0x57E40`; a direct path can store at `0x80047398`.

At `0x80047568..0x80047578`, a nonzero `0x8008242C` skips the timer decrement. When the latch becomes zero, the timer decrements once per gameplay tick, which is once every two video frames in the recorded control. When the 120th decrement reaches zero, the selector normalization block replaces each selected high nibble with its available low nibble. For brown, the control observed `0x24 -> 0x44` at `0x800475C0`.

This explains the visible behavior: remaining near an eligible brown seed freezes the already armed timeout. Moving far enough away clears the proximity latch and permits countdown. The latch is generic to eligible nearby actors, so the retail code does not support a stronger claim that only seeds can freeze it.

Runtime provenance, fixture hashes, and the bounded-exhaustion decision are recorded in [[EXP_2026-08-03_phase4_a13_bounded_exhaustion]].
