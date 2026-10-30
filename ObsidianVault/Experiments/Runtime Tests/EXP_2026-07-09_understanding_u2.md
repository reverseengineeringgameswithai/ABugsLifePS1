---
kind: experiment
id: EXP_2026-07-09_understanding_u2
aliases: [EXP_2026-07-09_understanding_u2, "understanding u2"]
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census, SYS_re_evidence_policy]
artifacts: [analysis/naming/u2_batch01.json, analysis/naming/u2_batch02.json, analysis/naming/u2_batch04.json, tools/gen_vm_disasm.py, analysis/vm_programs.json, tools/level_raw_chunk_roles.json]
---

# EXP_2026-07-09_understanding_u2 — static understanding push (no new movies)

## Question
With byte-reconstruction complete (99.88 %) but 482 resident functions still unnamed, how much
*understanding* can be recovered from purely static evidence — the existing coverage traces, the
call graph, and the full per-function disassembly?

## Track A — call-graph fingerprint naming (108 applied, 1 retracted; unknown 482 → 375)
Method (the overlay `ovl_o4` classifier applied to the resident image): per unnamed function, decode
its `jal` targets from the EXE bytes → resolve to named census/`re_symbols` entries → classify a role
from the callee/caller families → emit an evidence-carrying manifest → `apply_symbol_names.py` →
census regen. Three cascading rounds (each round's new names make more neighbors resolvable).
- **95 SDK/engine-cluster names** (definitive PsyQ fingerprints): `cd_*` shims (`CD_cachefile/
  searchdir`, `CdControl/CdMix`), `vram_upload_wait` (`LoadImage`+`DrawSync`), `voice_keyon_vol`
  (`SsUtKeyOn`), `vab_bank_stage`, `dma_intr_install`, event/pad/vsync kernel glue. The homogeneous
  GTE mesh cluster (the u1.5 body-diff blocker) was split by a **referenced-globals differentiator**
  — which *named* buffers each function's `lui`/lo pairs address (`bone_matrix_array` / `matrix_lut` /
  `ot_buffer` / `visual_sprite_object` `_mesh_transform`).
- **13 curated game-logic names** pinned by caller+callee+globals context: `vm_native_aimed_drop_spawn`
  (a documented mover-VM CALL sub), `mine_detonation_effect` (caller `seed_plant_mine_handler`),
  `player_sector_lookup` (reads `collision_sector_table`), `contact_cursor_transition_reset`, etc.
- **One retraction:** a name applied onto `0xFFFFFFFF` fill at `0x8004268C` was removed (evidence
  policy) — the census data detector had it right; the banked span was re-split at the true end.
- **Honest tail: 375 unnamed** = 18 libc-generic-only + 143 connected-but-unspecific + 214
  isolated (125 dynamic-covered). Named/understood resident code: **50 % → 61 %** (588/963).

## Track B — mover-VM disassembler (2 residuals pinned)
`tools/gen_vm_disasm.py` decodes the 13 resident AI programs with operand widths **extracted from
each handler's own `addiu s1,s1,N`** (not copied from notes). Cross-check PASSES: op17 radii
reproduce the hand decode (worm 700 @`0x80077A08`, wall_worm 1200 @`0x80077A70`, mosquito 1200
@`0x800775FE`); the CALL table resolves exactly (`0x80057A94/920/C74/B84` + 5 overlay subs).
Handler-byte findings that **supersede** the prior ISA table:
- **op9 (`0x8004C46C`) is `branch_if_s3`** — `blez s3` skip + `j` into op20's branch machinery at
  `0x8004C774` — NOT "set target from waypoint" (sym renamed `mover_vm_op9_branch_if_s3`; matches
  the observed program shape `[op17 dist<R][op9 if s3 goto]`).
- **op25's flag identity pinned:** `s3 =` byte `0x800A6596` (berry/equip state) `!= 0` OR power-up
  word `0x800A6590` bit `0x80` — closes the "op25 flag identity" residual.
Artifact: `analysis/vm_programs.{json,md}`.

## Track C — LEVEL.RAW chunk format validation (CONFIRMED 21 → 50 of 69)
Static decompress + grammar-check across **all 11** `LEVEL.RAW` files:
- `0x101` per-object mesh DEFs: **21/21 parse** (submesh count @+0x0A) → `CONFIRMED-fmt`.
- `0x22` sprites: header **pinned** = `[u32 0x22][u32 sprite-id][u16 W @+8][u16 H @+10]` + pixels;
  **134/134 validate** (24×24 glyph dims etc.) → `CONFIRMED-fmt`.
- `0x102` payloads stay `LIKELY` honestly: 13/16 chain a DEF group; 3 follow `0x104`/`0x23`
  containers — needs consumer-tracing.

## Links
[[SYS_function_census]] · [[SYS_re_evidence_policy]] · [[Consistency Audit]] · `src_re/enemy_ai_programs.c`.
