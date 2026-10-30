---
kind: experiment
id: EXP_2026-08-03_phase4_e14_frontend_save
status: complete
source_state: original_game
system: [FUNC_80055478, SYS_enemy_death_and_permanence]
row: E14_frontend_save
---

# Phase 4 E14: the save schema, and the side table it was hiding

## Question

E14_frontend_save's own named next step: "Field-map the FUNC_80055478 buffer by diffing
serialized saves across known progression deltas."

## The schema, mapped statically

The serialize/init/apply triple is already byte-matched decompiled (`src/main/80055478_*`,
`80055414_*`, `80055538_*`), so the 348-byte layout falls out directly:

| Bytes | Content |
|---|---|
| 0 | lives (`0x800A65A0`); new-game default 5 |
| 1 | campaign progress (`0x80082284` low byte); default 1 |
| 2–20 | the 19-byte `0x8009B878` block — fully decoded under C17 (16-byte per-level 100% array + ending bits + challenge bits + one unknown byte) |
| 21–27 | serializer GAP — consumed only by `scene_config_apply`: CD-mix indices (`cd_mix_shim`) + draw-env offset (`set_draw_env_offset`). The record format doubles as the scene-config record; the save carries only the state half |
| 28–347 | 64 × 5 bytes from `0x80089938`, init `{100,255,255,255,255}` |

## The 64×5 block: the "side HP table," located and structured

Committed Canon (`SYS_enemy_death_and_permanence`, Do-not-promote list) has long warned:
*"Do not use the side HP-table decrement as the kill definition. The side table floors…"* —
without the table ever being located. This is it.

**Structure** (instruction-exact): `table[actor_id*5 + equipped_berry_index]` — indexed by
actor id, one byte per native berry class, the class read live from the already-Canon
equipped-berry byte `0x800A6597` at every access site.

**Owners**:
- **KO decrement** (`0x8004B258..` in `FUNC_8004ABF4`, plus four sibling blocks): on a KO
  path (flags `|0x880`, chase bit cleared, vm_ip → death program), `table[id*5+berry] -= 2`
  — only while the value exceeds `0x40`. The "-2 with a floor," verbatim as warned.
- **Respawn clamp + aggro gate** (`FUNC_80049C30`, the E07-Canon actor initializer): clamps
  the entry up to `0x40` if below; separately reads it and — per the listing's branch sense,
  when ≥100 AND id ≠ 15 (grasshopper, explicitly exempted) — clears the chase bit at
  (re)spawn. The behavioral *direction* is deliberately not claimed from branch-reading
  alone; flagged for one live A/B.
- **Frontend scan** (`0x80054644..` in the results/frontend dispatch): a stride-5 loop
  hunting `0xFF` entries — located, role undecoded (plausibly first-availability column
  init).

**Empirical cross-save diff** (five saves, read-only): fresh saves sit at pure defaults;
the late-campaign Cliffside save populates berry-class columns 0/1/2 with every deviating
record index in `{6,9,10,12,13,15,17,18,22,29,30,34,37,39,40,41}` — **exactly the enemy
actor-id roster D01 just bound, no exceptions**; the Training-100% save populates columns
0/1/3 (red/blue/gold — Training's own berry being gold). Values move in even steps around
100 (72–110), consistent with the −2 decrement plus an unlocated increment source
(grasshopper sits at 110 — the same id the initializer exempts).

**Persistence**: serializer bytes 28–347 — the game *saves*, per species and per berry
class, accumulated KO history across sessions. A genuine hidden mechanic.

## What's still open

The increment source (values above 100); the aggro-gate direction (one live A/B needed);
the grasshopper exemption's reason (Bonus-3 streak protection is plausible, unverified);
the frontend `0xFF` scan's role; byte `0x8009B88A`; options/control-remap semantics and
continue/game-over flow (untouched — no dedicated pass this session); the C17 select-handler
internals that live in this row's frontend-overlay territory.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_e14_frontend_save.py
```

## Evidence

`analysis/phase4_e14_frontend_save.json` (full citation list inside).
