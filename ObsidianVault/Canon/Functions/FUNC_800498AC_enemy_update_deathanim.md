---
kind: function
id: FUNC_800498AC
aliases:
  - FUNC_800498AC
  - 0x800498AC
  - enemy_update_deathanim
address: 0x800498AC
name: enemy_update_deathanim
status: static_seen
confidence: confirmed
source_state: original_game
tier: confirmed
evidence:
  - src_re/enemy_death_permanence.c
  - EXP_2026_07_10_golddrop_pickup_retirement_flag_regression
patch_policy: safe_to_call_with_verified_flags
---

# FUNC_800498AC - enemy_update_deathanim

## Calling contract

`void enemy_update_deathanim(EnemyActor *enemy, unsigned flags)`

The second argument is a bitmask, not a boolean:

| flag | static path | effect |
|---:|---|---|
| `1` | `0x800498C0..0x80049B64` | Runs the death-animation/update half, including the `+0x6E == 998` permanent-destroy animation branch and actor-specific animation selection. |
| `2` | `0x80049B68..0x80049C14` | Runs terminal retirement: if actor `+0x62 == 0`, clears actor ID at `+0x00`; clears `+0x6E/+0x5A`; removes and compacts the actor pointer in `0x80090748`. |

Flags may be combined, but `1` does not imply `2`.

## Regression finding

The Gold Berry Token Drop pickup originally called `enemy_update_deathanim(enemy, 1)` after clearing `enemy+0x62`. That replayed the tagged spider's animation without entering terminal retirement. Operator observation matched the static contract: spiders popped up/disappeared during glyph pickup, then returned one by one later.

The corrected pickup uses flag `2`. Runtime verification after forced pickup showed tagged actor `0x8009FD80` with ID `0` and absent from the live damageable table, while the quota changed `1 -> 0` and execution remained valid.

## Modding policy

- Use `1` only for the original hit/death animation update.
- Use `2` when the caller has already established terminal state (`+0x62 == 0`) and needs actor retirement/unlink.
- Do not describe `enemy_update_deathanim(enemy, 1)` as a finalizer/removal call.

## ⚠️ Tooling pitfall — a separate function is merged into this address range (2026-08-02)

The debugger's `functionBounds` reports one span for `0x800498AC..0x80049E84`, but there is
a real function boundary inside it: a `jr ra` return at `0x80049C28` immediately followed
by a padding NOP at `0x80049C2C`, then a fresh routine at the actual call target
`0x80049C30`. Everything from `0x80049C30` onward is a **separate, unrelated routine** that reinstantiates
an actor from its own spawn-chunk template (id/position/program/hp/flags copied from the
runtime-record backlink at `+0x80`, position shifted `<<5` matching the documented spawn-
anchor law) — this is the actual enemy-respawn mechanism investigated under D12
(`analysis/phase4_d12_worm_id40.json`'s `RESPAWN_MECHANISM_2026-08-02`), **not** part of this
function's own `1`/`2` bitmask contract. It has zero static callers (reached via an
indirect/computed jump) and was first found live via an `accessLog` write-watch, not by
reading this function's own logic top-to-bottom — a prior draft of the D12 finding
mis-attributed the write to this function's `a1=2` branch before the register mismatch
(`t0` vs this function's own `s0`) was caught. Verify against a disassembly, not just
`functionBounds`, before assuming code past `0x80049C28` belongs to `enemy_update_deathanim`.
