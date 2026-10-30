---
kind: experiment
id: EXP_2026-08-19_chunk35_master_mesh_evidence_index
name: Chunk-35 master-mesh evidence index
status: evidence_index
created: 2026-08-19
experiment_date: 2026-08-11
source_state: original_game
systems: [SYS_chunk35_master_mesh]
functions: [FUNC_800172DC]
evidence:
  - docs/CHUNK35_MASTER_MESH_DECODE.md
  - tools/chunk35_master_mesh.c
---

# Chunk-35 master-mesh evidence index

This is a provenance repair for work performed and recorded on 2026-08-11. No
new emulator experiment was run while creating this note. The complete command
transcripts, grammar, controls, observed pixel differences, correction history,
and authoring frontier remain in `docs/CHUNK35_MASTER_MESH_DECODE.md`.

## Claims supported by the retained record

- The C grammar consumes the decompressed chunk-35 fixture exactly and accounts
  for its 183 GP0 `0x34`/`0x3C` primitive records.
- The record sizes and field offsets are independently tied to instructions in
  `FUNC_800172DC` by `tools/chunk35_master_mesh.c`.
- Identity recompression was the negative control; bounded vertex edits were
  cold-booted and compared against it.
- The changed-pixel silhouette corrected the old terrain/wall attribution to an
  actor/character mesh. The record explicitly preserves the remaining narrower
  alternative: it may be drawn coincident with Flik rather than be Flik's model.
- Records 118–182 remain outside the demonstrated safe authoring frontier.

## Canon consumers

[[SYS_chunk35_master_mesh]] · [[FUNC_800172DC_master_mesh_renderer]]

