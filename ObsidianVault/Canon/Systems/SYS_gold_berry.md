---
kind: system
id: SYS_gold_berry
name: Gold Berry
status: static_confirmed
confidence: confirmed
source_state: original_game
functions: [FUNC_80047170, FUNC_80058AF8, FUNC_8005953C, FUNC_80059E44]
memory: [MEM_800A658E, MEM_800A6596, MEM_800B0D18]
tables: [TABLE_8007941C]
evidence:
  - EXP_2026-08-04_phase4_c10_gold_berry
  - analysis/phase4_c10_gold_berry.json
  - analysis/phase4_c10_bounded_exhaustion.json
---

# SYS_gold_berry

## Resident behavior

- Equip index `3` constructs straight projectile type `11`, action `2`, timer `100`, initial subtype `4`.
- Direct actor collision rewrites subtype `4` to marker `11`, stages timer `1`, and selector `127` applies exact `-4` to that actor.
- Permanence is lethal-only. A surviving actor keeps the reduced counter and quota is untouched.
- A lethal marker-`11` hit sets actor counter `999`, uses permanent finalization, decrements `0x800A658E` once, and fires all-defeated only when the post-decrement quota is zero.
- Quota eligibility is `id != 0` and actor `+0x5C & 0x08A0 == 0` across 64 slots. Contact exclusion is actor `+0x5C & 0x00A0 != 0`.
- Berry-tough bit `0x40` is not a Gold exclusion.
- Timeout/floor subtype `4` and impact subtype `11` each decrement owned count `0x800A6596` once.

## Impact presentation

Impact emits sixteen alternating ctor `12/13` action-3 records, a positional effect, and sound `13`. These rows lack projectile/occupied bit `0x80`, so the visible burst does not produce radial enemy damage; damage occurred earlier against the single contacted actor.

## Precision and mod boundary

`0x80059200` uses `0x27(s1)` with `s1 = record + 8`; this is contact record `+0x2F`, not an enemy permanence byte. Gold permanence is record `+0x2C == 11` after collision rewrite.

The native lethal tail's type-120 effect is not proof of a collectible Gold token. Tagged type-120 pickup belongs to `MOD_gold_berry_token_drop`.

## Closure

Phase 4 C10 is strict `partial` and bounded-exhausted. Exact GPU/SPU ownership, semantic naming of quota-only bit `0x0800`, and campaign-wide overlay HP floors are outside the resident closure boundary. See [[EXP_2026-08-04_phase4_c10_gold_berry]].
