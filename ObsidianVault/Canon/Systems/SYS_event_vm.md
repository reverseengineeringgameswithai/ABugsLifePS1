# Event VM and scripted-object system

## Status

Phase 4 row `E07_event_vm` remains **partial**. The resident interpreter ISA, pristine authored bytecode corpus, and native-call slot set are bounded-exhausted. Overlay callback implementations, program-selection/reset ownership, transition behavior, and objective wiring remain open.

## Confirmed resident architecture

- Interpreter: `0x8004C13C`.
- Opcode dispatch table: `0x8001B2F4`, 26 entries.
- Native `CALL` table: `0x8001B35C`, 9 entries.
- Authored program-pointer table: `0x80077AF8..0x80077B98` (end-exclusive), 40 unique entries.
- The next word is `0x03020100`, providing a data-shaped upper bound rather than another valid program pointer.
- The C decoder traverses 421 valid instructions with no invalid program or opcode.
- Every opcode slot and every `CALL` slot is used by at least one authored program.
- Branches to `0x800775E4` and `0x8007799C` cross pointer-defined entry boundaries; entries can share bytecode.

## ⚠️ Eight opcodes are INDISTINGUISHABLE (corrected 2026-08-04)

Primary-table indices **1, 6, 7, 8, 10, 18, 19, 21** all hold the same handler address,
**`0x8004C818`**. Dispatch is a `jr`, so these eight opcodes cannot behave differently — and
`0x8004C818` is not an operation body at all. It is the interpreter's shared **loop tail**
(`bne s1,s7 -> refetch`), the continuation every genuine handler `j`s to on exit. A slot pointing
straight at it executes no operation.

`analysis/vm_programs.md` previously gave those eight slots eight distinct names — `park_end`,
`park_seek`, `park_arrive_test`, `park_arrive_stop`, `park_path`, `park_seek18`, `park19`,
`park21` — each marked **CONFIRMED**. They were positional inventions. They are now one label,
`noop_shared_tail`, confidence `INDISTINGUISHABLE`, and `tools/gen_vm_disasm.py` **aborts** if any
distinction is reintroduced (the property is derived by grouping the table by handler address, not
authored).

**Exactly one such group exists** in the whole 26-entry table, so every other opcode's decode is
unaffected.

> **If you are citing a `park_*` opcode name from an older note, it does not mean anything.** The
> bytecode position is real; the semantics attached to it are not. See
> [[EXP_2026-08-04_mover_vm_indistinguishable_opcodes]] for the blast radius (6 registry rows,
> 4 Canon pages, `park_seek` alone in 35 files).

Same pass: the generator walked the program-pointer table with a hard-coded `range(13)` while
**this page already documented 40 entries**. It now derives the count and decodes **40 of 40**
programs — the artifact had been contradicting its own Canon page, silently, for 27 programs.

## Native-call boundary

Resident targets are `0x80057A94`, `0x80057920`, `0x80057C74`, and `0x80057B84`. Overlay targets are `0x800B3D78`, `0x800B3B70`, `0x800B3BD4`, `0x800B3DC8`, and `0x800B3F00`. Static coverage proves all nine slots are authored, not the runtime conditions or effects of every target.

## Actor-facing state

The interpreter uses `$s0` for the actor, `$s5` for metadata, and `$s1` for bytecode IP. Confirmed actor accesses cover 32-bit position/motion/target fields at `+0x04`, `+0x08`, `+0x0C`, `+0x28..+0x3C`, `+0x40`, `+0x44`, `+0x4C`, and `+0x50`; bytes at `+0x48` and `+0x49`; halfwords at `+0x5C`, `+0x5E`, `+0x60`, and `+0x6C`; VM IP at `+0x70`; and metadata at `+0x80`. This is not yet a full ownership/reset model.

## Retained-capsule observation

The validated B06 capsule has 1,098 frame-boundary records and reconstructs RAM, VRAM, and SPU with `0/3294` hash mismatches. Passive flow has 386 interpreter blocks and 381 motion-apply blocks. RAM reconstruction observes 27 distinct valid VM IP values, 32 candidate locations per frame, and four changing locations. A dominant 31-slot run has stride `0x84`, consistent with actor records whose VM IP is at `+0x70`.

Only native-call stubs 1, 2, and 7 execute in this capsule. A hot target is not call attribution unless its VM `CALL` stub executes. Several opcodes alias one handler address, so block hits cannot distinguish those opcode indices.

## Static overlay boundary

All 20 pristine level overlays were scanned in C. Direct `jal` candidates to the VM initializer occur in multiple overlays; none directly call the interpreter. These remain candidates until code/data classification. This supports overlay-authored initialization and resident-owned execution, but does not close program selection or callback behavior.

## Evidence

- [[EXP_2026-08-02_phase4_e07_bounded_exhaustion]]
- [[FUNC_8004C13C_FUNC_8004C13C]]
- `analysis/phase4_e07_static.json`
- `analysis/phase4_e07_capsule.json`
- `analysis/phase4_e07_bounded_exhaustion.json`

## Closure boundary

The resident ISA/corpus/native-slot question, program selection, pool initialization/reinitialization, stage applicability, and all five applicable overlay-native bodies are exhausted at useful Phase 4 resolution. The row is not strict-complete because dedicated behavioral oracles, matching source, a regression gate, runtime campaign breadth, and exact objective labels remain.

## Deep Phase 4 applicability and lifecycle closure

The program selector is no longer open. Initializer 0x80049C30 reads actor metadata byte +13, indexes the 40-pointer table, and writes actor VM IP +0x70. Scene initializer 0x8004A42C clears and repopulates 64 records of stride 0x84; updater 0x8004D224 owns conditional reinitialization.

A schema-driven C scan found typed actor tables in 17 applicable stage payloads, 37 instantiated program indices, and no index outside 0..39. Joining those records to decoded CALL instructions proves only five overlay-native bodies are campaign-applicable: LEVEL03 slot 3/program 8, LEVEL02 slot 4/program 9, LEVEL05-1 slot 5/program 28, LEVEL09 slot 6/program 33, and LEVEL07-1 slot 9/program 39. All five are now semantically bounded; see [[EXP_2026-08-02_phase4_e07_bounded_exhaustion]].

The system is therefore bounded-exhausted for Phase 4 row advancement, while remaining partial under strict closure because dedicated behavior oracles, matching source, regression assertions, and exact objective labels are not complete.
