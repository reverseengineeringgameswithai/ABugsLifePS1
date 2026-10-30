---
kind: experiment
id: EXP_2026_07_30_phase4_a10_level01_handstand_address_narrowing
status: inconclusive
created: 2026-07-30
updated: 2026-07-30
confidence: low
related:
  - PLAYBOOK_game_solving_phase_4
  - SYS_player_action_state_laws
  - SYS_seed_carry_plant_lifecycle
---

# Phase 4 A10 — LEVEL01 handstand address narrowing

## Scope

This is the PCSX-Redux Memory Observer handoff for Phase-4 row
`A10_handstand`. The operator reduced main RAM to 26 byte candidates after
repeatedly entering, holding, and leaving the seed handstand in **LEVEL01**.

This export is retained as an **inconclusive method artifact**, not as an A10
address binding. It does not contain a labeled mount edge and does not identify a
handstand latch.

## Existing-record rediscovery

Only three exported bytes differ between the initial and retained values:

| Memory Observer offset | KSEG0 address | Existing typed meaning |
|---|---|---|
| `0x0A08DC` | `0x800A08DC` | actor record `0x800A08D8 + 0x04`, `pos_x` low byte |
| `0x0A08E0` | `0x800A08E0` | actor record `0x800A08D8 + 0x08`, `pos_y` low byte |
| `0x0A08E4` | `0x800A08E4` | actor record `0x800A08D8 + 0x0C`, `pos_z` low byte |

The retained Phase-1 LEVEL01 actor census identifies `0x800A08D8` as fixed
actor-record slot 21, actor ID `11`, with source-record pointer `0x80094CA0`.
Actor ID 11 is the existing movable-seed binding. The three candidates therefore
form one coherent XYZ record rather than three unrelated scalar fields.

That record identity, layout, and source pointer were already known before this
scan. Moreover, each exported coordinate byte has `Value == PreviousValue`; it
only differs from `InitialValue`. Without labeled before/enter/attached/exit
snapshots, the export cannot distinguish handstand correlation from surviving
movement noise. Slot 21 is therefore **not promoted as an A10 target** by this
artifact.

## Secondary candidates

- `0x800A0936/37` are slot 21 offsets `+0x5E/+0x5F`; both remained `0x01`
  throughout the exported comparison and are not A10 evidence.
- `0x800A655C/5D` and `0x800A65A3` are already retained A09 carry-transition
  candidates and remained zero in this export. Their presence is not new A10
  evidence.
- `0x801FFDxx` entries are stack addresses and cannot be promoted as durable
  resident state without writer/call-frame attribution.
- The remaining unchanged `0x80089Fxx/0x8008Axxx` bytes are retained for
  completeness but are not promoted by this pass.

## Retained operator evidence

- `analysis/operator_evidence/phase4/A10_LEVEL01/handstand.csv`
  — 692 bytes, SHA-256
  `f8aa0faf18b25f7c7b163168f226de53f318e1b2febbdca64bbd1e01e8a1ba90`.
- Central manifest:
  `analysis/operator_evidence/phase4/address_narrowing_manifest.yaml`.

PCSX-Redux reports physical main-RAM offsets; Canon uses the KSEG0 mapping
`0x80000000 + offset`.

## Replacement experiment

From a hash-verified pristine LEVEL01 handstand anchor:

1. retain separately labeled full-state samples immediately before mount, at the
   mount edge, while attached, at dismount, and after landing;
2. use the already confirmed player observables
   `0x800A6580` state and `0x800A6582` grounded;
3. determine the support object through object picking or actor/contact identity,
   not by assuming the surviving XYZ record is causal;
4. identify the mounted-object reference/index and the dismount writer before
   promoting an object-class claim into Canon or typed schema.

A10 remains partial until object identity, mount ownership, and the dismount path
are causally bound.

## Superseded questions (2026-08-03)

The requested replacement experiment is now complete through the control-exact
retained `carry_handstand` capsule and pristine C/ASM reduction. The selected
support is actor `0x8009FE88` (offset `0x108`, source `0x80094A70`), behavior 3.
Behavior `+0x40 >= 3` selects mode 14 at `0x80047870/0x80047874`; fresh Square
release takes `0x80047CD0`, clears the latch, and reaches the state-6 writer at
`0x80048D64`. Camera behavior remains the normal derived follow producer.

This note remains useful as the negative record for the unlabeled CSV method,
but its A10 ownership questions are superseded by
`EXP_2026_08_03_phase4_a10_handstand`.
