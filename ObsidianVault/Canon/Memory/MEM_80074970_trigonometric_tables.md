---
kind: memory
id: MEM_80074970
aliases: [MEM_80074970, 0x80074970, resident_trigonometric_tables, MEM_8007A7E4]
address: 0x80074970
name: resident_trigonometric_tables
status: static_seen
confidence: confirmed
source_state: original_game
system: [SYS_rendering, SYS_actor_update, SYS_camera]
read_by: [gte_rotation_matrix_setup, contact_vs_actor_handler, camera_follow_update, player_vertical_update, RotMatrix]
written_by: []
related_structs: []
evidence: [EXP_2026-08-05_phase4_f01_objective_lifecycle]
src_paths: [tools/phase4_f01_static_hard_truth.c, analysis/phase4_f01_static_hard_truth.json]
patch_policy: safe_to_read
---

# MEM_80074970 - Resident fixed-point trigonometric tables

## Confirmed layout

Two resident regions are content-verified trigonometric lookup tables in the
hash-pinned pristine `SCUS_942.88`. The classification requires both a complete
mathematical byte match and instruction-derived reader ranges; runtime reads were
the lead, not the proof.

| table | address / size | encoding | exact model |
|---|---|---|---|
| raw Q14 sine | `0x80074970..0x80077170`, 10,240 bytes | 5,120 signed little-endian 16-bit entries, stride 2, amplitude 16,384, period 4,096 | entry `i = llround(16384*sin(2*pi*i/4096))` |
| packed Q12 phase pair | `0x8007A7E4..0x8007E7E4`, 16,384 bytes | 4,096 little-endian words, stride 4; signed-16 low/high pair, amplitude 4,096 | `f(j)=llround(4096*sin(2*pi*(j+(((j mod 4096)>>10)&1))/4096))`; entry `i=(f(i),f(i+1024))` |

Every entry of both complete tables matches its model byte-for-byte. The packed
table's one-step phase adjustment in quadrants 1 and 3 is required by the bytes;
the simpler unadjusted sine formula is not an exact model.

## Confirmed readers relevant to the F01 gaps

The C probe derives effective-address ranges from the masks, shifts, base
materialisations, adds, and load displacements in the instructions. Exact reader
identity is reconciled in both directions with the regenerated static index.

- Raw Q14: 23 load sites — 6 in `gte_rotation_matrix_setup`, 2 in
  `contact_vs_actor_handler`, 7 in `camera_follow_update`, and 8 in
  `player_vertical_update`.
- Packed Q12: 6 word loads in `RotMatrix` at `0x8006087C`, `0x800608A4`,
  `0x800608E0`, `0x80060908`, `0x8006096C`, and `0x800609A0`. Each masks the
  angle to 12 bits and scales by the four-byte entry stride.

These ranges land in the exact pre-existing census gaps
`0x80075930..0x800769A8` (4,216 bytes) and
`0x8007B63C..0x8007D5C0` (8,068 bytes). No extent is widened. Together they
support a semantic disposition for exactly 12,284 bytes.

## Evidence boundary

The pristine executable SHA-256 is
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
`tools/phase4_f01_static_hard_truth.c` pins 144 instruction words and performs
the content comparisons; `tools/phase4_f01_static_hard_truth.py` recompiles it
with warnings as errors and reconciles the readers and existing `jr` imports.
Receipt SHA-256:
`2d86dcc2c23a81c9ba39e43f040b2866c94d30d4bc43c308f31da8d1184adf58`.

This proves the table semantics within that pinned image. It does not make the
whole resident image census-complete; 11,958 gap bytes still have no evidence.
