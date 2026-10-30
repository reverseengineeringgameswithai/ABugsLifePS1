---
kind: function
id: FUNC_80039A70
aliases: [FUNC_80039A70, 0x80039a70, frame_present]
address: 0x80039a70
name: frame_present
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
src_paths: [symbols/re_symbols.sym, analysis/phase4_e03_emitter_roster.json]
patch_policy: safe_to_read
---

# FUNC_80039A70 - per-frame OT re-init (sole owner)

## Purpose

Re-initialises the ordering-table state at the top of each rendered frame. A
4-byte write-watch across three scene classes proves it is the **SOLE writer**
of both:

- the **primitive cursor** `[0x8008249C]` -- store at **`0x80039BBC`**
  (`sw v0,0x704(gp)`), and
- the **depth-bucket base** `[0x80082230]` -- store at **`0x80039BC4`**
  (`sw v1,0x498(gp)`).

Every other cursor writer in the campaign is a packet EMITTER bumping the
cursor it owns; per-frame re-init has exactly one owner. This is the anchor
fact behind the "packets are fully rebuilt every frame" law (the only
cross-frame recurring DMA source is the static node at 0x8007FC84).

## Related

[[SYS_render_ot_and_present]] · [[FUNC_800646B8_gpu_present_drawotag_vsync]]