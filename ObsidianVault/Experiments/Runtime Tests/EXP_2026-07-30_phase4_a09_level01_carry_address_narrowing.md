---
kind: experiment
id: EXP_2026_07_30_phase4_a09_level01_carry_address_narrowing
status: reproduced
created: 2026-07-30
updated: 2026-07-30
confidence: medium
related:
  - PLAYBOOK_game_solving_phase_4
  - SYS_seed_carry_plant_lifecycle
---

# Phase 4 A09 — LEVEL01 carry-state runtime corroboration

## Scope

This is the operator-assisted runtime handoff for Phase-4 row
`A09_seed_pickup_drop` (pick up / drop a movable seed with Square). The experiment
was performed in **LEVEL01** by repeatedly separating carried movement and idle
periods from pickup and release transitions.

The scan did **not** discover new globals. Both fields already occur together in
byte-matched `FUNC_80046CAC` C and resident disassembly:

- `0x800A655C` — `u32`, not `u16`;
- `0x800A65A3` — `u8`, at RAM offset `0x0A65A3`.

Its useful contribution is a runtime state correlation:

| State | `0x800A655C` (`u32`) | `0x800A65A3` (`u8`) |
|---|---:|---:|
| carried, before release | `0x00000A50` | `0x0C` |
| after release | `0x00000000` | `0x00` |

The matching C treats `0x800A655C` as an integer offset from `0x8009FD80`.
Consequently `0x8009FD80 + 0x0A50 = 0x800A07D0`, a LEVEL01 actor-record address
already censused as actor ID 11 (seed). The same function clears the selected
record's motion fields and flag `0x40`, then clears both globals. Resident actor
code separately branches on `0x800A65A3 == 0x0B/0x0C`. This makes
“selected seed-record offset plus carry-related mode” the supported working
interpretation; exact mode names and entry writers remain unresolved.

The operator subsequently reported that the same two addresses also surfaced during
equivalent narrowing in **LEVEL02** and **LEVEL03**. This is a promising, preliminary
indication that the fields are resident across levels. It remains a “maybe” lead until
those two runs have retained, hash-pinned exports; the evidence files below are the
LEVEL01 captures.

PCSX-Redux Memory Observer reports physical main-RAM offsets. The addresses above
use the game's KSEG0 virtual form (`0x80000000 + offset`) used by the ABL symbols,
ASM/C, schemas, and Canon.

## Method

The operator established an initial LEVEL01 state beside a movable seed, narrowed
unknown main RAM while Flik performed unrelated movement, then alternated:

1. pickup;
2. movement while carrying;
3. idle while carrying;
4. release;
5. idle after release.

The intermediate export preserves the larger pre-release surface. Its two adjacent
bytes `0x0A655C/5D` are the low half of the already-declared `u32`, yielding
`0x00000A50` in this run. The final export records both fields cleared after
release. This is behavioral corroboration of existing code, not address discovery.

## Retained operator evidence

The CSV captures are preserved in the ABL working tree for future address analysis:

- `analysis/operator_evidence/phase4/A09_LEVEL01/before_throw.csv` — 542 bytes, SHA-256
  `97fca0a155091f9a7b374ad4ab07673d25281d8ce4106dca47700e664ff9b1d1`;
- `analysis/operator_evidence/phase4/A09_LEVEL01/most_likely_candidates.csv` — 117 bytes, SHA-256
  `b8c9c4dc0832abe2d2a932eef5363c2fa958541b5cabfd7b33ad9a845bdd4f69`.

The first export also retains changing `0x800908xx` object-record candidates. Those
belong to the broader carried-seed object surface and are not promoted by this
experiment.

The shared machine-readable inventory is
`analysis/operator_evidence/phase4/address_narrowing_manifest.yaml`.

## Required confirmation

From a hash-verified pristine LEVEL01 anchor:

1. capture the exact entry writers that assign `0x00000A50` and `0x0C`;
2. perturb or freeze each field separately from the same carried state;
3. retain an unmodified control;
4. distinguish the `0x0B` and `0x0C` modes and prove which field owns
   attachment/release versus downstream actor behavior;
5. promote the confirmed field widths, domains, owners, and lifecycle into
   `config/semantic_state.yaml`, the matching C/ASM symbols, and
   [[SYS_seed_carry_plant_lifecycle]].

No Phase-4 row-status promotion is made by this corroboration alone.

## Superseded open questions (2026-08-03)

The Phase 4 continuation in [[EXP_2026-08-03_phase4_a09_seed_pickup_drop]] resolves the writer and ownership questions left open above without RAM perturbation:

- `0x800A655C` is the selected actor offset and is written on pickup at `0x80047858`.
- `0x800A65A3` is the lift/carry/release phase and is written on pickup at `0x80047874`.
- Actor update modes 11/12 own lift and stable attachment; manual Square drop is `0x80047C1C..0x80047D00`.
- Manual release does not execute `0x80046CAC`; that earlier association is superseded.

The original CSV correlation remains valid evidence. Its requested perturb/freeze experiment is no longer required for the bounded A09 ownership conclusion because pristine ASM and a control-exact retained capsule separate the fields and owners directly.
