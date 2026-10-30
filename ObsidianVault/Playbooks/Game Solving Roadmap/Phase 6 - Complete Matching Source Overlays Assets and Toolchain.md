---
kind: playbook
id: PLAYBOOK_game_solving_phase_6
name: Phase 6 - Complete Matching Source Overlays Assets and Toolchain
aliases:
  - Phase 6 - Reorient C Decompilation Around Semantic Closure
status: planned
created: 2026-07-11
updated: 2026-07-11
confidence: high
parent: PLAYBOOK_game_solving_roadmap
previous: PLAYBOOK_game_solving_phase_5
next: PLAYBOOK_game_solving_phase_7
depends_on:
  - PLAYBOOK_game_solving_phase_3
  - PLAYBOOK_game_solving_phase_4
  - PLAYBOOK_game_solving_phase_5
---

# Phase 6 - Complete Matching Source Overlays Assets and Toolchain

**Navigation:** [[Phase 5 - Prove Cross-System and Full-Campaign Integration|Previous phase]] · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]] · [[Phase 7 - Whole-Game Closure and Modding Foundation|Next phase]]

## Purpose

Turn the solved behavioral and semantic model into a reproducible reconstruction of the
whole pristine program and its owned data pipelines. Matching source is not used as a
substitute for behavior; it preserves and exposes the implementation that has already
been semantically validated.

## Separate source products

1. **Matching original source:** reconstructs original bytes and layout.
2. **Semantic source/model:** explains types, ownership, invariants, and behavior when
   exact matching syntax is not yet readable.
3. **Diagnostic code:** temporary pristine-derived instrumentation, never original
   behavior or production MOD code.

## Work packages

- [ ] Complete game-owned resident C/ASM reconstruction with reviewed function extents.
- [ ] Complete matching reconstruction of every level, frontend, and FMV overlay.
- [ ] Separate and identify PsyQ/SDK/library objects and original toolchain behavior.
- [ ] Preserve typed structs, globals, tables, callbacks, and unknown fields in source.
- [ ] Reconstruct linker/segment/overlay layout and produce a deterministic original
  executable/overlay build.
- [ ] Complete bounded read/write schemas and round-trip validation for level, geometry,
  collision, models, animation, textures, audio, FMV, UI, and save data.
- [ ] Resolve original compression/packing/relocation behavior or record exact bounded
  exceptions where byte identity is impossible.
- [ ] Build source-to-binary, asset-to-runtime, and symbol-to-debugger provenance.
- [ ] Run the full Phase 2/5 pristine oracle against reconstructed outputs.

## Exit gate

- Resident executable and all overlays reproduce original bytes, or each remaining
  mismatch has a bounded technical explanation and no semantic uncertainty.
- Game code is distinguishable from SDK/library code and all game-owned behavior has a
  readable semantic representation.
- Asset pipelines round-trip within proven constraints and preserve runtime behavior.
- Clean builds from pinned tools and inputs are deterministic.
- Reconstructed pristine outputs pass the complete original behavioral oracle with no
  unapproved delta.

## Handoff to Phase 7

Phase 7 receives the reproducible pristine source/build, behavior oracle, subsystem
closure records, asset schemas, and enumerated residuals needed for the final audit.

## Progress record

| Reconstruction area | Status | Evidence |
|---|---|---|
| Resident bytes | advanced | 98.209% reconstructed code bytes at roadmap creation |
| Resident readable C | partial | 287 functions at roadmap creation |
| Overlay matching | early | Overlay inventory named; few byte-matched functions |
| Asset/container schemas | mixed | Strong DAT/RAW and several formats; whole set/lifecycles incomplete |
| Original deterministic build | partial | Resident substrate strong; whole disc/code/assets not closed |

