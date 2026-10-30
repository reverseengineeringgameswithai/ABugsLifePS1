---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Trace rendering ownership.md
aliases:
  - "Playbook - Trace rendering ownership"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Trace rendering ownership.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Trace rendering ownership
type: playbook
tags: [playbook, rendering, method]
---

# Playbook — Trace rendering ownership

> Find which function/buffer draws a given on-screen thing, and the editable source behind it.

## When to use
"What draws this dirt / wall / sky, and where do I edit it?"

## Steps
1. **Pick a stable interior pixel** with [[API - gpu.pickObject]]. This directly returns the final GP0 packet, primitive, raw words, screen/GTE/UV geometry, tpage/CLUT, draw mode, and best RAM/DMA/vertex pointer chain. Use `all_contributors:true` only for overdraw.
2. **For a small screen token/box, trace the region** with `gpu.traceRegion {x,y,width,height}` before dumping a full [[API - gp0Trace]]. Region trace returns only primitives touching the box, in draw order, with texture page, CLUT, blend mode, packet source, and RAM provenance when known.
3. **For texture/palette ownership, resolve live VRAM first:** `gpu.resolveVramProvenance` for the texture rect and `gpu.resolveClutProvenance` for the CLUT. If the report needs the whole chain, use `provenance.timeline` to connect transferLog, accessLog, and VRAM upload events.
4. **Capture surrounding GP0 state when needed** with [[API - gp0Trace]]; correlate using `drawCall.gp0Index`.
5. **Map the render call tree** from the returned pointer/packet back through the driver [[FUNC_800224EC]] → scene dispatcher [[FUNC_8001DFE4]] → builders.
6. **Find the source buffer** the emitter reads: [[API - execTrace]] at the emitter, capture the source pointer register (e.g. `a1`); or [[API - accessLog]] read-watch the returned address. Prefer `instruction_pc` from access-log events for attribution.
7. **Confirm with a move-test.** Shift a source vertex Y/X via [[API - scatterWrite]] and look for motion.
8. **Verify visually** with [[API - gpu.readVramRect]] + [[API - visual diff]] (or a disc build + operator test), then trace to disk through the decompressor + [[API - transferLog]].

## Pitfalls (all real, from the arc)
- *Read ≠ drawn*: a vertex can be read at `lwc2` then rejected (G15). Watch the **emit/packet-store** gate (`0x800108b4`) or the SXY site (`0x80010718`), and count-validate the payload. `gpu.traceRegion`/`gpu.pickObject` are now the first filter for actually visible primitives.
- *Emitted-in-view ≠ floor*: an on-screen payload may be a wall ([[Finding - 0x356bc is a wall not floor]]).
- *High runtime a0 frequency = instanced decor* (reject).

## ABL example
G30 used exactly this to find [[FUNC_800172DC]] / buffer `0x8012c` ([[Finding - Visible terrain renderer]]) and the sky fill ([[Finding - Sky is a GP0 background fill]]).

## Related
[[Rendering]] · [[FUNC_80010000]] · [[FUNC_800172DC]] · [[Playbook - Find geometry sources]] · [[API - gpu.pickObject]] · [[API - gp0Trace]] · [[API - provenance.timeline]]
