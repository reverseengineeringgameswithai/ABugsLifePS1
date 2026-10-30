# EXP 2026-08-02 - Phase 4 E07 event VM bounded exhaustion

## Question

Can retained evidence and pristine ASM close the resident event-VM frontier without a new replay, and what prevents `E07_event_vm` from becoming complete?

## Method

1. Reused the validated `b06_invincibility_hits` capsule before considering DuckStation.
2. Used a C11 analyzer on the pristine PS-X EXE, resident VM cluster, program pointers, bytecode, native-call table, and pristine overlays.
3. Used separate C11 code to parse zstd capsule chunks, reconstruct RAM/VRAM/SPU, verify hashes, count flow, and track valid VM IPs.
4. Kept static coverage, passive observation, and causal/lifecycle claims separate.

No emulator state, movie, disc image, save, or repository asset was mutated by the investigation.

## Identity and commands

Pristine executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

Capsule manifest SHA-256: `492aa2134e8d4d4bc8b348cd0c6d16f757d9ac4e5e3134945b2c688132f18c11`.

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror phase4_e07_static.c -lcrypto
cc -std=c11 -O2 -Wall -Wextra -Werror phase4_e07_capsule.c -lcrypto -lzstd
```

| Artifact | SHA-256 |
|---|---|
| `tools/phase4_e07_static.c` | `f195bb4877e1e655b1e40c81c5bc6b6b32fdf0c84b80af56adbc684dff2a28fd` |
| `analysis/phase4_e07_static.json` | `7c93915c023d34e2970bfe25b6a0a8eb173d1a0defab2e9626aac37f18621b3f` |
| `tools/phase4_e07_capsule.c` | `844ae0fe5a49f65683c4b491a19788209c37228c945e8530e4fb11732c495d65` |
| `analysis/phase4_e07_capsule.json` | `e1fe8bc27adb29d0ec0172baa633f7a673c9ed26ca4b18c45cdce15f6c5c26a6` |

## Static observations

- `0x80077AF8` holds 40 consecutive unique program pointers and ends at `0x80077B98`; the next word is `0x03020100`.
- The old 13-entry artifact and 17-pointer annotation used incomplete bounds.
- All 40 entries decode: 421 instructions, zero invalid programs, and zero invalid opcodes.
- All 26 opcode slots and all 9 native `CALL` slots occur in authored bytecode.
- Two branches enter shared code beyond a pointer-defined entry boundary.
- The resident EXE has one direct `jal` candidate to the interpreter and 16 to the initializer.
- Twenty pristine overlays were scanned. Initializer candidates occur in levels 02, 03, 04, 05, 07, 08, and 09; none directly call the interpreter.

Raw overlay `jal` hits are candidates, not proof that every matching word is code.

## Capsule observations

- 1,098 frames, 1,757,097 flow items, and 38,679,023 instructions were reconstructed.
- RAM, VRAM, and SPU produced 3,294 hash checks and zero mismatches.
- The interpreter executes in 386 records; motion apply executes in 381.
- Fourteen unique handler targets appear. `0x8004C818` is aliased, so hits cannot separate its opcode slots.
- Native `CALL` stubs 1, 2, and 7 execute. A hot target without its VM stub is not VM call attribution.
- RAM has 27 distinct valid VM IP values. Thirty-two candidate locations exist per frame, four change, and the dominant sequence has `0x84` stride.

This is frame-boundary evidence, not every-cycle or campaign-wide proof.

## Closure metrics

| Metric | Result | Remaining reason |
|---|---|---|
| Original behavior oracle | Advanced, not met | No dedicated cold-boot/reset/transition oracle. |
| Complete code frontier | Advanced, not met | Overlay callback bodies and producers remain. |
| Typed state model | Advanced, not met | Full owners/defaults remain. |
| Lifecycle model | Advanced, not met | Init/reset/unload/scene transitions remain. |
| Interfaces and side effects | Advanced, not met | Overlay target ABI/effects remain. |
| Stage and variant breadth | Advanced, not met | Runtime evidence is not campaign-wide. |
| Cross-system interactions | Advanced, not met | Objective wiring remains. |
| Source reconstruction | Advanced, not met | No complete semantic C reconstruction. |
| Durable evidence/gate | Advanced, not met | No dedicated E07 behavioral assertion. |

## Verdict

`E07_event_vm` remains **partial**. The resident ISA, 40-entry corpus, and 9 native-call slots are bounded-exhausted; repeating resident-table disassembly is low return. The useful frontier is overlay callbacks, lifecycle ownership, a cold-boot transition oracle, and objective wiring. This does not need to block moving to another row.

## Movie decision

No Interpreter-mode movie is required now. Use an existing Interpreter movie first for a later named gap and request a new recording only if it lacks that behavior. Never arm tracing on a CachedInterpreter recording.

## Deep exhaustion audit

The initial verdict was challenged with a second C-only static pass. That challenge materially improved the result and corrected one misleading formulation: five fixed resident CALL slots do not initially imply only five overlay bodies because the addresses are reused by every level overlay. A raw physical census found 91 address/file pairs in bounds, which was not sufficient applicability evidence.

### Selection and lifecycle closure

The pristine EXE contains exactly one static construction/reference of the program table base. At 0x80049C30 the initializer reads metadata byte +13, shifts it by two, loads the selected pointer from 0x80077AF8, and stores it to actor +0x70. Calls at 0x8004A664 and 0x8004D3F0 establish two owners:

- 0x8004A42C clears 8448 bytes, exactly 64 records of stride 0x84, then calls the initializer for active records.
- 0x8004D224 conditionally calls the same initializer from the per-frame updater.
- The only direct interpreter call remains 0x8004D5E0.

This closes program selection and the useful init/reinit boundary. A separately named teardown path is not needed to understand the next-scene reset because the pool is cleared before repopulation.

### Typed stage applicability

A C port of the proven LEVEL.RAW decoder searched every chunk by schema rather than assuming a fixed chunk number. The actor table was accepted only with marker 0x23, record stride 0x1C, and integral geometry.

- 17 of 20 RAW/BIN stage pairs contain the typed 64-record actor table.
- LEVEL00/LEVEL, LEVEL08/LEVEL1, and LEVEL09/LEVEL1 contain no such table; these are non-applicable, not decoder failures.
- 37 of the 40 program indices are instantiated by active records.
- No active record uses an index outside 0..39.
- Indices 2, 13, and 35 have no direct on-disc actor-table instance in this campaign census.

The fully decoded bytecode reduces the overlay-native surface to five applicable pairs:

| Slot | Program | Stage | Active records | Target |
|---|---:|---|---:|---|
| 3 | 8 | LEVEL03/LEVEL | 19 | 0x800B3D78 |
| 4 | 9 | LEVEL02/LEVEL | 1 | 0x800B3B70 |
| 5 | 28 | LEVEL05/LEVEL1 | 1 | 0x800B3BD4 |
| 6 | 33 | LEVEL09/LEVEL | 2 | 0x800B3DC8 |
| 9 | 39 | LEVEL07/LEVEL1 | 1 | 0x800B3F00 |

### Native callback closure

Three applicable bodies already have byte-matched semantic C:

- LEVEL02 slot 4 sets overlay word 0x800B4950 to 60.
- LEVEL05-1 slot 5 compares resident halfword 0x800A0282 with an overlay table selected by 0x800B4BB8 and returns inequality.
- LEVEL09 slot 6 preserves the incoming argument through a wrapper to the routine that clears 21 stride-0x54 flags and sets the following flag.

The remaining two were decoded from pristine overlay bytes with C:

- LEVEL03 slot 3 computes actor heading toward Flik, writes the 12-bit result to actor +0x14, uses metadata byte +15 to select a one-shot halfword at 0x800B4D20, raises actor +0x6A by 2400, emits eight effects cycling kinds 21..23 with parameter 12, writes -2048 to actor +0x20, and calls 0x8005044C with id 102 and actor position.
- LEVEL07-1 slot 9 reads mode 0x800B4A3C. For mode below 13 it calls 0x800B3B54 with selector 5 for modes 0..1, selector 2 for 2..3, and selector 0 for 4..12.

### Revised closure decision

E07 remains partial under the strict Phase 4 nine-metric definition, but it is now sufficiently bounded-exhausted to move on. Static ISA/corpus coverage, program selection, pool init/reinit, campaign applicability, and every applicable native body are closed at useful reverse-engineering resolution.

The remaining work is disproportionately oracle/source/gate work: five dedicated callback behavior controls, matching semantic source for the interpreter and two callbacks, a declarative regression assertion, and exact human-facing objective labels. Those are valid completeness gaps, but more resident ASM scanning or broad movie collection would be low return.

No Interpreter-mode movie is required for the move-on decision. Request one only if deliberately pursuing a named callback oracle or objective effect absent from existing Interpreter recordings.

### Added durable artifacts

| Artifact | SHA-256 |
|---|---|
| tools/phase4_e07_deep_static.c | af3510fd8a767473028cbbbefec9b66c828b760c89120757cfa4030b49e5bb62 |
| analysis/phase4_e07_deep_static.json | 90b74fa9825b9da1c40b2ba515c3366c87aa44ec23c2a3f4f22b1dcdbb8ea2e5 |
| tools/phase4_e07_stage_join.c | a36ec1956fbd5fb318e4583274078b9bb26bf406d580322b099e0781b7d91f80 |
| analysis/phase4_e07_stage_join.json | 72938f43352de599e9d9e6f6360b1384c913f4000813a54c11546e3833d021f3 |
| tools/phase4_e07_callback_disasm.c | d7f9f3d4395cb42763e46045e998cbf89c568225ab9ad684f1ad0f419cb659d3 |
| analysis/phase4_e07_callback_disasm.txt | 34efe999f3910f77fc6f57691871d40a35336d71f2e2dc17375cc443a2a80101 |
