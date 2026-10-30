---
kind: experiment
id: EXP_2026-08-03_phase4_d05_death_respawn
status: complete
source_state: original_game
system: [SYS_enemy_death_and_permanence]
row: D05_death_respawn
---

# Phase 4 D05: enemy death/despawn/respawn, synthesized from D09/D12/D13

## Question

"Find another row to work on." D05_death_respawn's own scope (death animation, drops,
delayed respawn, quota, family exceptions) turned out to be substantially covered already —
`SYS_enemy_death_and_permanence.md`'s own "Temporary-KO respawn" section is a cross-species
finding banked under `D09_redbug`/`D12_worm`/`D13_shell_bug`'s own rows, live-confirmed the
same day for all three species, but never cited in D05's own registry entry.

## What this closes, without new live work

**Respawn condition** (confirmed live, three species): a non-permanently-killed enemy
respawns only once Flik genuinely walks away — real controller input, ~76,000+ units,
reliable on repeat runs — and back. Position pokes never reproduce it, including a
constructed "realistic" one-frame teleport delta and 111,000+ units of small per-frame
scatterWrites. Only genuine continuous execution with real input triggers it.

**Reinit mechanism** (traced to instruction level): a previously-undocumented routine at
`0x80049C2C` — a real function boundary hiding inside `FUNC_800498AC`'s own merged span (`jr
ra` at `0x80049C28`, fresh prologue-equivalent right after) — performs a genuine from-scratch
re-instantiation: id/position/mover-VM-program/hp/flags all copied fresh from the actor's own
spawn-chunk template via its runtime-record backlink (`+0x80`). This is why a revived actor's
`vm_ip` lands near its program's own start rather than resuming where it died. **A nice
self-caught correction along the way**: an earlier draft mis-attributed this to
`FUNC_800498AC`'s own `a1=2` branch (already Canon as terminal retirement — the opposite
direction) until a register mismatch (`t0` vs `s0`) was noticed before banking.

**Death-side timer and per-frame scheduler** (both confirmed to exist and fire): three
callers of `FUNC_800498AC` — the death tail itself (`a1=1`), and two calls inside the
per-actor per-frame updater (`0x8004D224..0x8004D6A4`) that ticks each live actor's own
`+0x4A` countdown (a per-species negative constant set at death) toward zero.

## What's still open — one concrete, well-scoped lead

**The reinit trigger itself is unconfirmed.** `0x80049C2C` has zero static callers (an
indirect/computed call) and an `execTrace` watch produced zero hits despite the reset
demonstrably firing in the same run — almost certainly a tooling reliability gap (the same
pattern was independently hit once already this session on an unrelated throw-dispatch
check), not evidence the routine wasn't reached.

**A genuine, unresolved contradiction**: the per-frame updater also runs an admission check
(scanning the full static actor array, gating entry into the live table by distance to a
camera-derived reference point) that, read literally, means "near the anchor → admitted/
ticking, far → frozen" — the **opposite** of the confirmed live behavior (walking far
triggers the reset). This is named explicitly as unresolved, not glossed over — plausible
explanations (too-small admission radius, an unlocated hp-gate, a register misread, or two
genuinely unrelated systems) were listed but none tested. **This is D05's own single most
concrete remaining lead**: watch the cached reference point (`0x8009EC50`) and the actual
admission-check branch outcome across a real walk-away-and-back sequence.

## Follow-up resolution - 2026-08-04

A pristine-EXE C scan corrected the presumed entry point: `0x80049C2C` is a
padding NOP and the actual reinitializer begins at `0x80049C30`. The corrected
target has exactly two direct callers, `0x8004A664` and runtime scheduler call
`0x8004D3F0`; the former zero-xref result therefore did not imply an indirect
call or an execTrace failure.

The scheduler at `0x8004D224..0x8004D694` resolves the apparent contradiction:

- `0x8004D29C` sends HP-positive actors through live near-camera admission.
- KO actors bypass that path, count down actor `+0x62`, and call the spawn
  visibility predicate `0x80025084` when the delay reaches zero.
- A visible fixed spawn suppresses respawn; an off-screen spawn falls through
  to `0x8004D3F0: jal 0x80049C30`. Flag `0x10` bypasses visibility.
- Actor `+0x4A` belongs to the separate live-list death-animation/retirement
  pass and is not the KO respawn delay.

`0x80025084` uses spawn-template coordinates reached through actor `+0x80` and
camera-space coefficients, not the actor's current displaced position. This
explains why D12's natural camera walk produced the HP restore while raw
position pokes did not. The live donor identifies the callback at advanced PC
`0x80049CA4`; the actual store is `0x80049CA0: sh ...,0x6e(...)`.

No new movie or DuckStation replay was required: the missing domain was static
branch/call attribution, and the D12 runtime donor supplies behavioral
correlation. D05 is now **substantiated partial, bounded-exhausted**. Exact
per-species delay values and cosmetic death/drop/audio cataloging are possible
but low-return and do not block moving to another row.

Artifacts: `tools/phase4_d05_static.c`,
`analysis/phase4_d05_static_resolution.json`, and
`src_re/enemy_respawn_scheduler.c`.

## Evidence

`analysis/phase4_d05_death_respawn.json`; donor evidence:
`analysis/phase4_d12_worm_id40.json` (`RESPAWN_MECHANISM_2026-08-02`),
`analysis/phase4_d09_redbug_identity.json`, `analysis/phase4_d13_shell_bug_armor.json`,
`ObsidianVault/Canon/Systems/SYS_enemy_death_and_permanence.md`.
