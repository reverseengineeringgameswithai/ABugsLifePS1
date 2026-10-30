---
title: Phase 4 C10 Gold Berry resident-mechanics closure
date: 2026-08-04
status: bounded_exhausted
source_state: original_game
row: C10_gold_berry
---

# Phase 4 C10 Gold Berry resident-mechanics closure

## Question

What makes Gold the strongest permanent-kill berry: exact damage, impact/explosion scope, enemy exclusions, quota integration, and projectile lifecycle?

## Method

- Queried the central retained-capsule index first. It contains no C10 or generic Gold-kill capsule.
- Kept `gold_berry.sav` (`f731fdb643a693334272040b38933c2ed6cef8ffc41b2c1ca743c9ccd0a2a435`) and `gold_berry_glyph.sav` (`38bc7aa96ca549dda94b975d756890988ba680152757b8e87378f871110b7b26`) as hash-pinned fixtures. Their retained RAM-usage artifacts are changed-byte censuses, not trace capsules.
- Excluded `D17_Goldberry.movie.json` (`3bfa845035d0ed4bdd0236ba67ade4ca763561a87293792b2bc1e3cc02de48c5`) from generic C10 evidence because it exercises a bird-boss launch-height override.
- Compiled and ran the native analyzer against pristine `SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`:

```sh
cc -O2 -Wall -Wextra -o /tmp/phase4_c10_static tools/phase4_c10_static.c -lcrypto
/tmp/phase4_c10_static SCUS_942.88 > analysis/phase4_c10_gold_berry.json
```

- Bound the constructor row, collision rewrite, damage dispatch, lethal/permanent split, quota constructor, cleanup table, effect rows, and owned-throw decrement.
- Reused D04's complete five-native-berry shell-bug and worm controls only as runtime corroboration of Gold `-4`, berry-tough eligibility, and permanent-finalization shape.
- No DuckStation launch, state load, movie replay, RAM write, disc mutation, or overlay claim was used.

## Dispatch and lifetime

Equip index `3` selects type `11`: action `2`, timer `100`, model `110`, initial subtype `4`, secondary `1`, flags `0xE5`, and damage selector `127`. Gold uses A08's shared lead-adjusted straight ballistic constructor. It has no homing child or retarget pass; timer, floor, distance, and flags retirement remain common-projectile gates.

## Contact and exact damage

One actor overlap indexes initial subtype `4`, jumps to `0x80058E88`, writes marker `11` to contact record `+0x2C`, and stages timer `1`. Selector `127` then executes exact delta `-4` at `0x800590D4`. This is direct damage to the one actor being handled, not radial damage.

The old fixture request's “permanence `+0x27`” wording was imprecise. `0x80059200` reads `0x27(s1)` because `s1` is biased eight bytes into the contact record; the actual field is record `+0x2F`, the secondary kind. Gold permanence is selected by collision-rewritten record `+0x2C == 11`.

## Lethal-only permanence and quota

A nonlethal Gold hit leaves the actor-local counter reduced by four and does not touch `0x800A658E`. On a lethal hit, marker `11` selects outcome bit `2`; the death tail writes actor `+0x6E = 999`, applies native permanent finalization, clears actor `+0x62`, and decrements quota once. Only a post-decrement zero invokes the all-defeated event. There is no local pre-decrement zero guard; the code relies on its level-built eligibility ledger.

The level-load constructor scans 64 actor slots and counts only `id != 0` records whose state `+0x5C & 0x08A0` is zero. Contact-time collision rejects current actor state `+0x5C & 0x00A0`. Berry-tough bit `0x40` is not a Gold exclusion, as D04 also corroborates. Quota-only bit `0x0800` is proven as an exclusion but not semantically named.

The native lethal tail also creates a type-120 death effect. This does not make original type 120 a literal collectible Gold token; tagged pickup behavior remains MOD-private.

## “Explosion” resolved

Both ordinary subtype-`4` retirement and impact subtype-`11` retirement decrement owned count `0x800A6596` once. Impact emits sixteen alternating ctor `12/13` records, a positional effect, and sound `13`. Ctor `12/13` are action `3`, flags `0x40/0x20`, and lack projectile/occupied bit `0x80`; they do not re-enter action-`2` enemy damage. The visible explosion is presentation, not splash damage. Timeout/floor uses the same core burst with one additional terminal effect object.

## Evidence classification

**Observation:** pristine type `11` has selector `127`/subtype `4`; contact rewrites it to `11`; lethal permanence decrements quota; subtype `4/11` cleanup creates action-3 effect records and retires ownership.

**Inference:** the large visible burst can look explosive, but it is not a secondary damage source.

**Causal confirmation:** the contacted actor alone enters selector-127 `-4`; only lethal marker `11` crosses the permanent threshold and performs the quota write before cleanup presentation.

## Disposition

C10 remains strict all-context `partial` but is **bounded-exhausted** for direct resident mechanics. The closure gate is **PASS**, and no Interpreter movie is required to move on.

Deferred low-return work is exact GPU/SPU ownership, a campaign-wide overlay-floor catalog, and semantic naming of quota-only bit `0x0800`. Request a movie only for a named overlay override or exact audiovisual attribution.

Machine evidence: `analysis/phase4_c10_gold_berry.json` and `analysis/phase4_c10_bounded_exhaustion.json`. Canonical synthesis: [[SYS_gold_berry]].

## Source hashes

| Input | SHA-256 |
|---|---|
| `asm/hand_written/80058af8_contact_vs_actor_handler.s` | `2c6313d72dad6d078c23b71028941c4d9306c925bf4d31a510d7bab66328906f` |
| `asm/hand_written/8005905c_berry_tough_damage_dispatch.s` | `f1aa90ff4967fb3286dc49a1bd21099869dd467e2850a69449172da54f53bf44` |
| `asm/hand_written/8005921c_sub_8005921c.s` | `dffaf30f2b85e664e7a29fc5cfd7a0648392dd7e3870e82a456176ab245eaa16` |
| `asm/hand_written/80046b20_level_load_player_spawn_writer.s` | `5cc4abedda1bb9dad0d1439f071a607721215bb3179ec6324c2359411f724556` |
| `asm/nonmatchings/resident/800595d4.s` | `7fffb894c130e815b8e2586949f912d59f8d9ee2425081f68451f283ee3dd49b` |
| `asm/hand_written/80059e44_contact_alloc.s` | `c5cd81d56c7f7d4a2f55b04c8f90fc6167cd8caeacda815ee88cda25fcc2c98c` |
