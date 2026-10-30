---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay - Resident Event Stream.md
aliases:
  - "Gameplay - Resident Event Stream"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay - Resident Event Stream.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Gameplay_-_Resident_Event_Stream.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay - Resident Event Stream
type: core
updated: 2026-06-20
tags: [core, gameplay, events, dat, scripting, prng, milestone6, gap-0033]
---

# Gameplay — resident byte-stream table `0x80017DB4` (GAP-0033)

> Decodes the **role of the resident table** the shared cursor `0x800822f4` is seeded to ([[Gameplay - DAT Event Stream]], [[FUNC_8005B714]]). **Conclusion: `0x80017DB4` is a ~2 KB resident, baked-in *pseudo-random byte table* (entropy 7.91/8.0, mean exactly 0x80), purpose-built to be read as zero-mean signed offsets `(byte − 0x80)`. Gameplay consumers pull 1–3 bytes each and use them as per-construct coordinate offsets and low-bit variant/gate selectors. It is a shared deterministic NOISE/jitter source — NOT a level-event/spawn script.** Per-level object data is a *separate* system (LEVEL.DAT via `DATbase+offset` records). All STATIC (`tools/exe_read.py` + decompiled `src_re/*`); a runtime read remains optional/corroborating ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Table identity
| Property | Value | Source |
|---|---|---|
| Start | `0x80017DB4` | sole cursor seed `0x8005b900` ([[FUNC_8005B714]]) |
| End (est.) | `0x800185b8` (next function prologue) | boundary scan — **CONSERVATIVE** |
| Size | **2052 B** (~0x804) | `exe_read.py --region-stats 0x80017db4 --region-end 0x800185b8` |
| Entropy | **7.911 bits/byte** (8.0 = random) | region-stats |
| Mean | **128.14 ≈ 0x80** | region-stats — *zero-mean when read as `byte−0x80`* |
| Distinct values | **256/256**; zeros = 12 | region-stats |
| Code? | No — non-code, after `jr ra` @ `0x80017db0`; referenced once | [[FUNC_8005B714]] |

The **mean = 0x80 + full-range + ~8.0 entropy** is the decisive signature: the table is engineered so consumers' `(byte − 0x80)` arithmetic yields **balanced signed pseudo-random offsets**. This is a noise/dither table, not authored script bytes.

## Seed & lifetime
Seeded once per scene-init: shell/main state machine `0x8004fa40` calls **[[FUNC_8005B714]]`(current_scene_id)`** @ `0x8004fdf0` → `0x8005b900` sets `cursor = 0x80017DB4` (init-once guarded by `0x800822f8`). Thereafter every consumer only **advances** the cursor (`cursor += N`); it walks the table **monotonically** (no terminators seen), and is re-pointed to the start on the next scene-init.

## Consumers (how the bytes are interpreted) — CONFIRMED from decompiled sources
| Consumer | bytes/call | Interpretation | Source |
|---|--:|---|---|
| **type-0x3f** [[FUNC_80053814]] generic ctor-0x71 | 3 | **signed coordinate offsets**: `axis = (entry.axis<<5) + ((byte−0x80)<<4)` for X/Y/Z | `src_re/source3f_dispatch_80053814.c:182` |
| type-0x3f kind 0x31 (animated) | 3 | 3 coord-offset bytes (animation) — LIKELY | same, `:138` |
| **grain** [[FUNC_80054EAC]] | 1 (+1) | byte0 → **gate** (`& 0x0f == 0` arms a pre-effect); pre-effect reads byte1 → **variant** (`& 1`) | `src_re/pickup_handlers_80054288_80054554.c` |
| **contact_alloc** [[FUNC_80059E44]] (`+0x24` variant) | 1 | `byte & 3` → **4-way variant** for fields `+0x24`/`+0x22` (only when `metaB+0x04 < 0`) | `src_re/contact_alloc_80059e44.c:94` |
| contact walker [[FUNC_800586B0]] action `0x20` | ≥1 | reads cursor (action-specific) | `src_re/contact_walker_800586b0.c` |

⇒ Every consumer uses the bytes as **small per-construct parameters** (signed coordinate jitter, or low-bit gates/variants) — exactly what a shared pseudo-random source provides. None treats them as opcodes, IDs, or pointers.

## Role verdict
**Shared resident pseudo-random (noise/dither) byte source — CONFIRMED.** It supplies deterministic per-construct positional jitter (`(b−0x80)<<4`) and behavioural variation (low bits) to the pickup/grain/contact construction paths. The decompiled sources' "level script cursor" / "script byte" naming is an **earlier label**; the table's statistics + the seed finding show it is a **PRNG/noise table**, not a script.

- **Not** a global resident script, default spawn script, opcode stream, or tutorial script.
- **Closest fit:** a constructor-parameter / coordinate-dither table (procedural variation).

## Relation to DATbase / LEVEL.DAT (kept separate)
The cursor/noise-table is **resident and shared**. Per-level object data is the *independent* `DATbase+offset` record-pointer mechanism: parser [[FUNC_8001CDC0]] builds `record = DATbase + offset` and relocates in-record offset fields (`field += DATbase`). Pickups' authoritative position/kind live in their **type-0x3f records** (coordinate-moddable, [[Finding - Type-0x3f pickups are coordinate-moddable]]); the noise table only adds *offsets* to **constructed** ctor-0x71/0x51 entities.

## Confidence
- Table is resident & pseudo-random (entropy/mean/distinct) — **CONFIRMED (static metadata)**.
- Consumers read it as coord-offsets / low-bit variants — **CONFIRMED (decompiled)**.
- Seed runs on scene-init via shell SM `0x8004fdf0(scene_id)` — **CONFIRMED (static)**.
- Table **end** `0x800185b8` — **LIKELY** (next-prologue heuristic; true extent is whatever consumers reach in a level).
- What the offset-jittered **ctor-0x71 entities are** — **RESOLVED → [[Gameplay - Resident Noise and Ctor 0x71]]:** a **contact/proximity entity** in array `0x800b0d18` (walked by [[FUNC_800586B0]] for collection logic), **not rendered** (the visible pickup draws from the type-0x3f record). The jitter offsets its **contact-detection position** — logic, not visible scatter.

## Modding relevance
The pseudo-random table governs **per-construct jitter/variation**, not object placement. Editing it (an EXE/resident patch) would change positional scatter / variant selection of constructed entities; it will **not** move pickups (those are the type-0x3f records). For a level editor this means: object placement = records; "natural-looking" scatter = this table.

## Next proof step
1. ~~Identify the ctor-0x71 entity class~~ **— DONE → [[Gameplay - Resident Noise and Ctor 0x71]]:** contact/proximity entity, not rendered; jitter = contact-position variation (logic). Post-init [[FUNC_80024DDC]] only sets a state byte.
2. **Residual (optional, local-only):** the contact record's table-A "render attrs" (`+0x0c..0x18`) are set but no array-render consumer was found — a runtime read of `0x800822f4` (== `0x80017DB4`?) or a check for any visible change when the cursor is frozen would close the last sliver.

## Related
[[Gameplay - DAT Event Stream]] · [[FUNC_8005B714]] · [[FUNC_80053814]] · [[FUNC_80054EAC]] · [[FUNC_80059E44]] · [[FUNC_800586B0]] · [[FUNC_8001CDC0]] · [[MEM - Event System Globals]] · [[Gameplay - Warp and Level Transition]] · [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Executable and Overlays]] · `tools/exe_read.py`
