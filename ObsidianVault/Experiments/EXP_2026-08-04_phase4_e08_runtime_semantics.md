---
type: experiment
status: complete
date: 2026-08-04
system: props, movers, switches, gates
phase: 4
row: E08_props_movers_gates
disposition: substantiated_partial_bounded_exhausted
artifacts:
  - analysis/phase4_e08_runtime_semantics.json
  - tools/phase4_e08_runtime_static.c
  - tests/test_phase4_e08_runtime_static.py
---

# Phase 4 E08: runtime semantics and bounded exhaustion

## Decision

E08 is now **substantiated partial and bounded-exhausted**. Move on.

The previous campaign census closed authored placement breadth but correctly
left runtime semantics open. This pass closes the high-value part of that
frontier with pristine ASM and C analysis. No Interpreter movie is required
for the current mechanics claim.

The shared Phase 4 roadmap was already dirty from another agent and was left
untouched. This note is the durable row-specific update.

## Capsule-first decision

The declared Phase 4 external-evidence root was searched for E08, fixture and
prop/gate names. No relevant retained capsule exists. Static register/RAM and
block-flow questions were answerable from the pristine executable, all 21
authored DATs, all 20 level overlays, and already-banked passive-prop/pass-3
live A/B evidence. DuckStation was therefore not launched.

## Observation: kind 0x31 authored domain

A compiled C walker found **39** kind-`0x31` records in **eight** DATs. Seven
files contain five records; `LEVEL10/LEVEL.DAT` contains four. Every record has:

- `Y = -600`
- status byte `+0x0D = 0`
- rest-height halfword `+0x0E = 0`
- a nonzero, route-distributed X/Z position

This is one exact authored family, not 39 unrelated unknown kinds.

## Observation: status is visibility, not persisted state

`pickup_projector` clears entry `+0x0D` at `0x80025544`, then sets it to `1`
at `0x800255BC` only after the entry passes distance and consumed-sentinel
visibility gates. `source3f_dispatch` requires that byte to equal `1`.

Therefore the authored zero is not a dormant/persistent switch bit. It is
overwritten every frame as the render-to-contact eligibility join.

## Observation: exact kind-0x31 construct path

The pristine instructions at `0x800539A0..0x80053A18` require:

- kind equals `0x31`
- `restY - currentY >= 113`
- squared proximity is at most `0x3D08F`
- phase byte `0x800910A2` equals zero

The phase byte alternates zero/one at `0x800551B4` and is cleared during scene
reset at `0x8005B918`. On the eligible phase, the game calls:

```text
contact_alloc(X << 5, (Y - 160) << 5, Z << 5,
              ctor = 83 + ordinal, metadata_A_row = 21)
```

A normal five-record group therefore selects constructor rows `84..88`.
Those rows share action ID 1, active type 20, lifetime/init `-8`, values
`90/90`, selector 2 and flags `0x20`. Their trailing byte triplets are:

```text
80 00 00   00 80 00   00 40 80   80 80 00   00 00 80
```

These are strongly RGB-shaped five-variant data. Calling the objects
five-color route emitters is an inference; the structural claim is the exact
ordinal proximity-emitter family above.

## Correction: the common pickup helper

The old documentation reversed the branch at `0x80053CA8`.
Kinds `0x30` and `0x31` **bypass** `0x80057620`; ordinary pickup kinds call it,
receive a five-object burst, and are marked consumed. The helper is not a
telescope/checkpoint constructor.

Kind `0x31` instead has its own action at `0x800545A0`: only when
`currentY == restY - 112`, it decrements Y by one, returns action code `-10`,
and requests sound/event `-3`. Retail records begin at `-600/0`, so this exact
action is not reachable from initial state alone. An indirect later Y writer
is a named residual rather than being invented from static absence.

## E08 scope reconciliation

The old row wording combined several systems that are not one runtime object
family:

- Pass-1 props are passive, per-instance baked render payloads. Prior live
  swaps prove render consumption. They have no prop-local hitbox.
- Prop solidity is separately authored sector collision and belongs to E02.
- Scripted movers and switches belong to E07's event VM/callback system.
- Grain gates belong to E09.
- Pass-2 moving/dynamic geometry belongs to E11.
- Type-`0x3F` collection and save rules belong to the C-series pickup rows.

This is not scope evasion: those rows already contain the corresponding
behavioral evidence. Duplicating them in E08 would produce contradictory
ownership and no new mechanic.

## Pass-3 static frontier

The C formed-address scan covered the pristine resident image and all 20 level
overlays. It found one direct pass-3 visibility-bitmap access, the resident
read in `pass3_backdrop_cull`, and zero direct writers. The only overlay direct
pass-3-pointer access is the already-known Bug Bar read, consistent with E11.

This does not prove no indirect pointer writer exists. Existing live A/B work
already proves that clearing the bitmap suppresses the class and that level
load reconstructs its state. The combination bounds E08 without overstating a
constant-formation census.

## Persistence and reset

- Pass-1 records are scene render inputs rebuilt from DAT.
- Kind-`0x31` visibility status is rewritten per frame.
- The kind-`0x31` phase byte is explicitly reset during scene initialization.
- E14's save schema contains no kind-`0x31`, pass-1 or pass-3 field.
- Pass-3 visibility is runtime level state reconstructed on load.

## Residuals and reopener

The remaining work is low-return or belongs to a neighboring row:

- exact pixels and presentation timing for constructor variants `84..88`
- proof or disproof of an indirect writer reaching kind-`0x31`'s exact
  `restY-112` action
- complete user-facing scene-to-DAT labels, owned by E16 loader/streaming work

Reopen E08 only for a MOD that changes these record families or for exact
presentation. If reopened, use a normal-speed Interpreter movie in one of the
eight relevant DAT scenes and trace `0x80053A14` plus `0x800545A0`.

## Reproduction

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror \
  -o /tmp/phase4_e08_runtime_static tools/phase4_e08_runtime_static.c
mapfile -t dats < <(find REBUILD/files -type f -name 'LEVEL*.DAT' | sort)
mapfile -t bins < <(find REBUILD/files/LEVEL* -type f -name '*.BIN' | sort)
/tmp/phase4_e08_runtime_static REBUILD/files/SCUS_942.88 \
  "${dats[@]}" --bins "${bins[@]}"
```

Transient analysis source/output hashes and pristine input hashes are recorded
in `analysis/phase4_e08_runtime_semantics.json`.

## Related

[[EXP_2026-08-04_phase4_e08_object_census]] · [[Prop_and_foliage_catalog]] ·
[[EXP_2026-08-02_phase4_e07_bounded_exhaustion]] ·
[[EXP_2026-08-02_phase4_e09_bounded_exhaustion]] ·
[[EXP_2026-08-02_phase4_e11_dynamic_geometry]]
