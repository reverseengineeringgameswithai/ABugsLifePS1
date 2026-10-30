---
kind: function
id: FUNC_800646B8
aliases: [FUNC_800646B8, 0x800646b8, gpu_present_drawotag_vsync]
address: 0x800646b8
name: gpu_present_drawotag_vsync
status: runtime_confirmed
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: [EXP_2026-08-03_phase4_e03_ot_packet_census]
src_paths: [symbols/re_symbols.sym, analysis/phase4_e03_ot_packet_census.json]
patch_policy: safe_to_read
---

# FUNC_800646B8 - present: VSync + DrawOTagEnv DMA kicks

## Purpose

The present routine: VSync wait plus the GPU-DMA kicks that hand linked lists
to the GPU. Its kick call site **`0x80064F28`** ([[FUNC_80064F28]]) is the
choke point through which each rendered frame presents a **SEQUENCE of
separate linked lists**, with the list head in **`a1`** at the call:

| kick | list |
|---|---|
| 0 | 7-command env preamble at `buffer+0x1C` (E3,E4,E5,E1,E2,E6,fill) -- its terminator is real; env is its OWN list, never linked into the body |
| 1 | the depth-bucket body chain at `buffer+0x14E0` (1228-entry bucket table) |
| 2+ | scene-dependent auxiliary lists (scratchpad `0x1F8010F0`-built, stack-built); zero GP0 draw commands observed |

Training fires >= 6 kicks per rendered frame. Halting here at kick 1 is the
only way to snapshot a complete chain: after present, each buffer's OT is
reset to env + terminator.

## Method note

Breakpointing this site and reading `a1` is how the C OT-walker
(`tools/phase4_e03_ot_walk.c`) gets a true chain head; heads derived from
gp0Trace source addresses land mid-table and skip leading empty buckets.

## Related

[[SYS_render_ot_and_present]] · [[FUNC_80064F28]] · [[FUNC_80039A70_frame_present]]