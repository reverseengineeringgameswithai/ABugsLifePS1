---
kind: function
id: FUNC_80014844
aliases: [FUNC_80014844, 0x80014844, contact_record_billboard_render]
address: 0x80014844
name: contact_record_billboard_render
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
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

# FUNC_80014844 - contact-object billboard emitter

## Purpose

An **ordering-table packet emitter**: it allocates GPU primitives by bumping
the primitive cursor `[0x8008249C]` and links them into the frame's
depth-bucket chain.

## What is measured here

A 4-byte write-watch on the primitive cursor over several rendered frames
recorded this function writing the cursor at **0x80014AA8**, in all three scene classes
(`analysis/phase4_e03_emitter_roster.json`; counts in that artifact are
BATCHES -- one cursor store per emitter batch -- not primitive counts).

**Scope of the claim.** The measurement proves this function is a cursor-owning
packet emitter and pins its store site(s). The *name* is inherited from
`symbols/re_symbols.sym` and describes the presumed role, which this
measurement does not independently establish -- treat the role as
`static_seen`/medium until a caller-set + callee read confirms it.

## Related

[[SYS_render_ot_and_present]] · [[FUNC_80039A70_frame_present]] (the sole
per-frame re-init owner)