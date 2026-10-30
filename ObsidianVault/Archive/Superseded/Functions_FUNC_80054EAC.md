---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80054EAC.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80054EAC.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80054EAC_grain_pickup_handler.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80054EAC — grain pickup handler
type: function
address: 0x80054EAC
confidence: CONFIRMED
tags: [function, pickup, grain, hud]
---
# FUNC_80054EAC — grain pickup handler

> Handles collecting a grain: bumps the grain count and, at exactly 50, runs the all-grain reward path.

| Field | Value |
|-------|-------|
| Address | 0x80054EAC (…0x80055188) |
| Source file | `src_re/pickup_handlers_80054288_80054554.c` (`grain_pickup_handler_80054eac`) |
| Confidence | CONFIRMED count/reward branch; pre-effect side-effects UNKNOWN |

## Purpose
Consumes one script byte, runs an optional grain pre-effect, increments the grain count `0x800a65a1`, and at exactly `0x32` (50) runs the all-grain reward (snapshots player to `0x80090b80`, calls `fcn.8005044c(-0xb)`, sets `0x800a6594=4`).

## All-grain emblem reward (CONFIRMED live 2026-06-23)
The "collect all grain" reward = the **grain emblem medal** + **Flik health refill to full**, gated
here (NOT by the HUD pulse `0x80052ac0`, which is only the SELECT-panel reveal):
- gate: `0x80055004 lbu v1,[0x800a65a1]` ; `0x80055008 addiu v0,zero,50` ; `0x5500c bne v1,v0,0x80055174`.
  `grain == 50` falls through to the reward block at **`0x80055014`** (straight-line, no branches).
- the reward block snapshots player pos → `0x80090b80..b8c`, pulses `0x80090b90`, and at
  **`0x80055060 jal 0x5044c`** (`a0 = -11` = medal id) **spawns the emblem medal**; health
  `0x800a7e2a` then refills to 7 over ~165 frames.
- the `lives++` block at `0x80055080`+ is **dead** — `0x80055078 bne` (two distinct constants) is
  always taken to `0x80055110`, so no extra life is granted.
- **Mod**: replacing the hard-coded `50` at `0x80055008` with the live kind-0x14 count makes the
  emblem fire at the level's real grain total — see [[Grain emblem and HUD total mod]].

## Arguments / Returns
Invoked as a jr-table case (kind 0x14 from [[FUNC_80053814]], action 0x14 from [[FUNC_800586B0]]). Returns void.

## Calls (callees)
- `fcn.80045678`, `fcn.80044d28` (grain pre-effect), `fcn.8005044c`, `fcn.80050994`.

## Called by (callers)
- [[FUNC_80053814]] (kind 0x14) and [[FUNC_800586B0]] (action 0x14).

## Globals & structures touched
- grain count `0x800a65a1` (target `0x32`) · script cursor `0x800822f4` · reward snapshot `0x80090b80` · HUD pulse `0x800b018c`. Drawn by [[FUNC_800526F4]].

## Evidence & confidence notes
Byte-traced count + reward branch. The grain count is also a HUD mirror; the real increment is pointer-relative here. Pre-effect side-effects UNKNOWN.

**Cursor consumption (2026-06-20):** the "script byte" it reads is from the **resident pseudo-random table `0x80017DB4`** (the cursor `0x800822f4` is seeded there, NOT LEVEL.DAT — [[Gameplay - Resident Event Stream]]). Grain reads **1 byte** `first` (`cursor += 1`) used as a **gate** (`maybe_grain_pre_effect` runs only if `first & 0x0f == 0` and scene ≠ 0x11); the pre-effect then reads **1 more byte** `second`, using `second & 1` as a **variant** into `fcn.80044d28`. So grain pulls 1–2 noise bytes as low-bit gate/variant selectors — consistent with a shared PRNG source, not a script.

## Related
- System: [[Grain emblem and HUD total mod]] (the reward mechanic + the dynamic-total mod)
- Findings: [[Finding - Type-0x3f pickups are coordinate-moddable]]
- Functions: [[FUNC_80053814]] · [[FUNC_800586B0]] · [[FUNC_800526F4]]
- System: [[LEVEL.DAT object pipeline]]
- Source docs: `src_re/pickup_handlers_80054288_80054554.c`
