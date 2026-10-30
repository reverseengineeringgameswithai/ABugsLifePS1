---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8005B134.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8005B134.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8005B134_player-pos_-_Region-A_overlay_dispatcher_(superseded_claim).md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8005B134 — player-pos / Region-A overlay dispatcher (superseded claim)
type: function
address: 0x8005B134
confidence: PARTIAL
tags: [function, collision, overlay, superseded]
---
# FUNC_8005B134 — player-pos / Region-A overlay dispatcher

> Once believed to be the sole player-position writer (static-era guess). **Superseded** by [[FUNC_8003633C]] for the per-frame collision-Y write; its true role and relationship remain open.

> [!check] Live-traced 2026-06-18 (B17). It is an **8-way state-handler**: `index = v0−3`, bounds-checked `<8`, jumps through table `0x8001b828` to **internal** cases `0x8005b174/84/94/a4/b4` (states 5/7/9 → default `0x8005b1bc`). **0 hits over 8 idle frames** → it only runs under specific states (`v0∈[3,10]`) and **does not write player Y *per-frame in idle states*** — confirming the G5 "sole *per-frame* writer" claim is DISPROVEN (per-frame writer = [[FUNC_8003633C]]). Reached indirectly (0 `jal` callers — itself a dispatcher). **REFINED 2026-06-20:** the sub-question "what triggers states 3–10" is **answered** — those are **respawn/transition states**, and the handler's **common tail `0x8005b1bc` DOES place the player** (respawn-from-anchor; see below). So FUNC_8005B134 *is* a player-position writer, but only on **respawn**, not per-frame.

| Field | Value |
|-------|-------|
| Address | 0x8005B134 |
| Source file | `geometry_collision_consumers.c` |
| Confidence | role CONFIRMED (overlay dispatcher); "sole writer" claim SUPERSEDED |

## Purpose
State dispatcher into Region-A LEVEL overlay verbs (`0x800b3adc / 3ae8 / 3aec / 3c54 / 3c5c`). Has **zero `jal` callers** (it is reached via overlay/jump-table dispatch), which is exactly why it is NOT the per-frame Y writer.

## Common tail = player respawn placement (2026-06-20) → [[Gameplay - Player Spawn and Placement]]
After the per-state overlay-verb dispatch, every path falls to the **common tail `0x8005b1bc..0x8005b2dc`**, which **places the player on respawn**: it reads the respawn **anchor** `0x800a6550/54/58` and writes it to the **live** position `0x800a6500/04/08` (writers `0x8005b29c/2a4/2ac`) **and** the previous/render copy `0x800a6510/14/18`, then **zeroes a large block of player state** (velocity / flags / counters `0x800a651c..0x800a65xx`) — a full player reset. The anchor is maintained by checkpoint-save [[FUNC_80054C90]]. ⇒ this is the **respawn/restore** half of the checkpoint system; it runs only in states `v0∈[3,10]` (death/respawn/transition), not per-frame.

## Arguments / Returns
State/verb selector (overlay-dispatched).

## Calls (callees)
- Region-A overlay verbs (`0x800b39a0` region).

## Called by (callers)
- none via `jal` (jump-table/overlay dispatched).

## Globals & structures touched
- Region-A overlay base `0x800b39a0`. See [[MEM - DAT runtime memory map]].

## Evidence & confidence notes
G5 named this as the player-pos writer from a static scan; G29's WRITE-watch proved the actual per-frame writer is [[FUNC_8003633C]] @ `0x80036cec`. The relationship between the two (does this dispatch into the integrator? set up state it consumes?) is **UNKNOWN** — an open question.

## Related
- Findings: [[Finding - Player Y writer FUNC_3633C]] · [[Finding - No static collision consumer]]
- Functions: [[FUNC_8003633C]]
- Open: [[Open Questions]]
- Source docs: `src_re_geometry/geometry_g29_collision_source_plan.md`
