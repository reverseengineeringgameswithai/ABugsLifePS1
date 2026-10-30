---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8004A700.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8004A700.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8004A700_unnamed.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8004A700
type: function
addr: 0x8004a700
confidence: CONFIRMED (static decode) / role LIKELY
tags: [function, gameplay, warp, transition, milestone6, gap-0033, gap-0035]
updated: 2026-06-21
---

# FUNC_8004A700 — type-2 transition initiator (overlay-callable)

> The **enclosing function** of the `[0x800823a0]=2` store at `0x8004a8b4` (one of the three
> "resident transition initiators" of [[Gameplay - Warp and Level Transition]]). **This is the
> initiator the per-scene OVERLAY verbs actually call** — directly proven by xref, not inferred.
> Decoded static (EXE-read, `tools/exe_read.py`).

## What it is
The prior notes labelled `0x800496d8 / 0x8004a8b4 / 0x8004b3c0` as "resident initiators." Those are
the **`sh v0,0x23a0(at)` store-instruction PCs**, not function entries (`--store-ea 0x800823a0` → 16
writers). The enclosing functions are **`0x80048138`** (type 1), **`0x8004a700`** (type 2, this note),
**`0x8004abf4`** (type 6, [[FUNC_8004ABF4]]).

## Signature & behaviour (entry `0x8004a700`, 48-byte frame)
`FUNC_8004A700(a0, a1, a2=ptr, a3=mode/destination)` — saves a0→s3, a1→s2, a2→s0, **a3→s4**.
- `jal 0x80041a74`; `[0x800a657a]=0`.
- **`bne s4,zero, 0x8004a828`** — **a3 selects the path**: `a3==0` falls through (`0x8004a744…`),
  `a3!=0` branches to `0x8004a828`.
- In the `a3!=0` branch (`0x8004a878…`): `[0x800a659e]=0`; **decrements a counter and writes
  `[0x800a6594]=v1−1`** (`0x8004a888`); if the result `< 0` calls helper `0x80050994(a0=73)`;
  then `0x8005044c(a0=12)`; **`[0x800823a0]=2`** (`0x8004a8b4`); `[0x80082470]=60` (fade color);
  reads `[0x800a6590]`, writes `[0x800a6592]=−45`.

`[0x800a6594]` is the **level-exit counter** the native gate at `0x8004f0e8` checks
(`bltz` ⇒ must be `≥0`); this function manages it. ([[FUNC_8004ABF4]] / [[Gameplay - Warp and Level Transition]].)

## Callers — 8 (6 EXE + **2 OVERLAY**) — the proof overlay verbs call it
| caller | where | arg note |
|---|---|---|
| `0x800496b0` | EXE (in `0x80048138`, type-1 fn) | |
| `0x80049740`, `0x80049868`, `0x8004b4a0` | EXE | |
| `0x80058a48`, `0x8005c9f8` | EXE (pickup / death region) | |
| **`0x800b3e94`** | **LEVEL06\LEVEL.BIN** — scene-3 verb `0x800b3e88`+0xc | **a3 = 3** (destination), then sets `[0x800823a0]=2`+fade 60 |
| **`0x800b4ae0`** | **LEVEL04\LEVEL1.BIN** | a3 = 0; gated by `[sp+0x30]==1`, then falls to spawn verb `0x800b3aec` |

⇒ **GAP-0033 Q1 answered + the formerly-INFERRED "overlay verbs call the resident initiators" is now
PROVEN.** The scene-3 overlay verb `0x800b3e88` is an **interior case-label** (it starts `addiu a2,sp,16`,
not a prologue) of the overlay's main handler, reached via the overlay's own sub-state `jr`; on the
exit case it calls `FUNC_8004A700(…, a3=destination)`. The **type-2 path carries a destination (a3)**;
the **type-6 path ([[FUNC_8004ABF4]]) carries none** — which is why a forced `[0x800823a0]=6` has no
real destination and lands on scene 16 ([[Experiment - In-game warp trigger]]).

## Confidence
- Store-site→enclosing-fn map, 8 callers (jal scan), a3-selected paths, `[0x800a6594]` counter write —
  **CONFIRMED (static, EXE+overlay-read)**.
- "type-2 = special/cutscene level-exit with explicit destination" — **LIKELY** (role from the call
  context + the a3 argument; not runtime-exercised).

## Related
[[FUNC_8004ABF4]] · [[Gameplay - Warp and Level Transition]] · [[Gameplay - Events and Triggers]] · [[Experiment - In-game warp trigger]] · [[FUNC_8005222C]] · [[FUNC_8005B714]] · `tools/exe_read.py`
