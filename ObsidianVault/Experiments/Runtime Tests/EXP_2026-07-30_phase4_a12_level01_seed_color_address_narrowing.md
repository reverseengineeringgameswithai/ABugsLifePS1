---
kind: experiment
id: EXP_2026_07_30_phase4_a12_level01_seed_color_address_narrowing
status: invalidated
created: 2026-07-30
updated: 2026-07-30
confidence: high
related:
  - PLAYBOOK_game_solving_phase_4
  - SYS_seed_carry_plant_lifecycle
---

# Phase 4 A12 — invalidated LEVEL01 address narrowing

## Scope

This is a retained, invalidated operator-assisted scan for Phase-4 row
`A12_seed_color_change`: changing the carried seed's color with Triangle. It covers
**LEVEL01** and intentionally separates color selection from A13 plant-output
cycling.

The export contains two rows, but neither changed across the retained comparison:

| Address | Initial | Previous | Current | Verdict |
|---|---:|---:|---:|---|
| `0x800822A4` | `0x0A` | `0x0A` | `0x0A` | unrelated renderer cache |
| `0x80094C76` | `0x00` | `0x00` | `0x00` | pre-existing seed color field, no action edge captured |

PCSX-Redux Memory Observer reports physical main-RAM offsets. The addresses above
use the game's KSEG0 virtual form (`0x80000000 + offset`) used by ABL symbols,
ASM/C, schemas, and Canon.

## Why the candidates are rejected

`0x80094C76` is exactly LEVEL01 chunk-31 source record #20 at offset `+0x0E`:

`0x80094C76 - 0x80094A38 = 0x23E = 20 * 0x1C + 0x0E`.

That merely rediscovers the existing A12 binding that a seed record's `+0x0E`
byte is its color lane. Because the byte remained zero in this export, the artifact
does not show Triangle changing that particular record.

`0x800822A4` is not an `u8` seed global. Resident textured-primitive helpers read
and write it as the halfword at `gp+0x50C`, caching render-descriptor/texture state
while queuing draw primitives. Its unchanged `0x0A` value is renderer noise, not
seed-color evidence.

## Method

The intended operator action was valid, but the retained CSV does not capture an
observable action edge. A final candidate count is not evidence when every retained
value is unchanged. This scan must not be used to promote either address or grade
A12.

## Retained operator evidence

- `analysis/operator_evidence/phase4/A12_LEVEL01/seed_changing.csv` — 92 bytes,
  SHA-256
  `8016c7ad1c28b081f83363334057a930e1ff52a671e7ba46ef4fccfb728cf278`.

The file is preserved so the failed method cannot silently be repeated. The shared
machine-readable inventory is
`analysis/operator_evidence/phase4/address_narrowing_manifest.yaml`.

## Replacement experiment

From a hash-verified pristine LEVEL01 anchor:

1. identify the actually carried actor record and dereference its `+0x80` source
   pointer rather than hard-coding record #20;
2. set a byte write breakpoint on that source record's known `+0x0E` color field;
3. capture before/press-edge/after values plus the writer PC and an identical
   no-Triangle control;
4. repeat with another seed or level only after the first writer is causal;
5. bind Triangle's availability/denial checks and UI/audio feedback, then promote
   confirmed ownership, domain, reset, and persistence semantics
   into `config/semantic_state.yaml`, matching C/ASM symbols, and
   [[SYS_seed_carry_plant_lifecycle]].

This invalidated scan contributes no A12 row-status progress.
