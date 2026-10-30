---
kind: system
id: SYS_bonus2_bonus3_chain_law
name: Bonus-2 and Bonus-3 chain state, and the progress feedback shared by all three
status: live_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-08-04_phase4_f16_f18_bonus_stage
  - analysis/phase4_F17_streak_live.json
  - analysis/phase4_F18_streak_live.json
src_paths:
  - tools/phase4_f17_f18_streak_law.c
  - tools/phase4_f16_streak_reset_trace.py
patch_policy: safe_to_read
---

# SYS_bonus2_bonus3_chain_law

Companion to [[SYS_bonus1_streak_law]]; the challenges themselves are
[[SYS_bonus_unlock_challenges]] and the stage they lead to is [[SYS_bonus_stage]].

This page exists because Bonus 1's counter turned out to have four clears nobody had
written down, and the causal model for one of them was wrong. That was possible only
because the known writer set was incomplete. This page pins the currently resolved
direct sites without claiming pointer/variable-index closure.

## Bonus 3 — `0x80082240` (= `gp+1192`)

**Correction history.** This formerly said "Domain closed" across the EXE and all
overlays. The fixed-form scan resolves **one direct read and five direct writes** —
one increment and four clears — and no fixed-form overlay hit. It leaves 12,956
resident unresolved-base accesses (34 same-width in related functions), 149 indirect
calls, and the overlay unresolved-base class. This is not an absolute domain closure.

| PC | function | effect |
|---|---|---|
| `0x800591A4` | `berry_tough_damage_dispatch` | the only read |
| `0x800591C0` | `berry_tough_damage_dispatch` | **the only increment** |
| `0x800591EC` | `berry_tough_damage_dispatch` | clear after the fifth |
| `0x80058B34` | `contact_vs_actor_handler` | clear when blue is not selected |
| `0x80059A0C` | `pickup_effect_dispatch` | clear on contact-dispatch case 13 |
| `0x80057428` | pool-reset routine `0x80057404` | clear — **not previously recorded** |

**Accept conditions** (all pinned): contact damage class must be `0` (`0x8005916C`),
the actor id must be `15` (`0x80059184`), and the earned guard `flags & 0x40` must be
clear (`0x80059198`). Progress command is `streak + 114`; the fifth ORs low bit
`0x04`, sets latch `6` and fade `30`, then resets.

**No scene gate** — checked, not assumed: no instruction in `0x8005916C..0x800591EC`
reads `0x80082504`. Bonus 3 really can be done anywhere with qualifying targets.

✅ **Both Bonus-3 clears confirmed destroying a live chain** on the operator's
`Bonus03_Resets` recording, which built a chain of three twice and broke it two
different ways:

| movie frame | what the operator did | clear | chain lost |
|---|---|---|---|
| 854 | threw a berry **at a wall** | `0x80059A0C` (case 13) | **3** |
| 3708 | **picked up a different berry** | `0x80058B34` (selector) | **3** |

The second is the important one for the rule below: they never threw the wrong
berry, they merely *acquired* one, which changed the selector — and the streak died.
The first also settles what case 13 is in play, at least for this trigger: a thrown
berry striking something that is not a qualifying grasshopper. Its full domain is not
established from one observation.

⚠️ **"Kill with a blue berry" is not the rule — "be holding blue" is.** The clear at
`0x80058B34` sits at the **entry** of the contact-vs-actor handler: it reads the
berry selector `0x800A6597` at `0x80058B00`, compares it against `1`, and clears the
streak whenever it is anything else. It fires whether or not anything is hit — 630
times in one verified replay. So the streak is *held* at zero for as long as blue is
not selected. Same shape as Bonus 1's berry-throw clear: the reset is bound to a
state, not to the kill.

⚠️ **`0x80057428` is not in the earlier write-up.** It is unconditional inside a
housekeeping routine that first memsets `0x800B0D18` for 3584 bytes and clears
`0x8008234C`. It does **not** clear the Bonus-1 counter — checked — so the two chains
do not share this reset.

## Bonus 2 — five **bytes** at `0x80082248..0x8008224C`

⚠️ **They are bytes, not words.** The 16 currently known stores into that window are
`sb`; the fixed-form scan resolves 15 constant-address sites and the indexed append at
`0x8005C580` is pinned separately. Slot 0 is reached as `gp+1200`,
slots 1..4 absolutely. Watching these at stride 4 reads slot 4 as slot 1 and then
three unrelated globals; an early revision of the runtime tracer did exactly that,
silently, and its capture had to be discarded.

`0xFF` (`-1` signed) is the empty marker. There are **16 known stores**: one append and
three separate blocks that write all five slots. Other variable-index or pointer-based
stores are not excluded, so this is a known-site map rather than a complete domain.

- **Append** a new plant identity — `0x8005C580`, `sb s4, 0x80082248(at + index)`.
  Six executions in the verified replay.
- **Duplicate → restart, not wipe** — `0x8005C548..0x8005C56C` writes the
  just-touched identity into slot 0 and `-1` into slots 1..4. The chain becomes
  **one**, not zero: a duplicate costs you the chain but immediately re-seeds it with
  the mushroom you just hit — so the next progress command is `114`, not `115`.
  ✅ **Confirmed live** on `F16_Bonus02_ResetTestv2`: after appends of plant identities
  6, 5 and 4 at movie frames 195/251/301 (progress `114 → 115 → 116`, bursts on the
  second and third), bouncing plant 4 again at frame 353 ran `0x8005C54C..0x8005C56C`
  — slot 0 became `4` and slots 1..4 became `-1`, progress fell back to `114`, and no
  burst played. Repeating the bounce on the same mushroom repeats the restart
  indefinitely, so **a chain cannot be farmed off one plant: it pins at one**.
- **The wipe** — `0x8005C06C..0x8005C08C`, a shared exit block reached from **four
  independent guards**, checked in this order:
  1. `0x8005C02C` — the player is **grounded** (`0x800A6582 != 0`) and no plant is in
     contact (`s4 == -1`). ⚠️ **This is the one that matters in play**: landing on the
     ground without a mushroom is the mechanism behind "five *in a row*".
  2. `0x8005C038` — the plant type is not 5.
  3. `0x8005C04C` — the scene is `0x10`, i.e. inside the bonus stage.
  4. `0x8005C064` — Bonus 2 is already earned (`flags & 0x10`).

  An earlier revision of this page called this "the earned-guard wipe", naming a
  shared block after the last of four guards that reaches it, and concluded there was
  no penalty for landing. Both were wrong. Verified live: the wipe runs at movie
  frames 0..40, **stops** for the whole airborne sequence over the mushrooms, and
  **resumes at frame 239** — the frame the operator reported landing.
- **Init wipe** — `0x8005BC94..0x8005BCB4`, following a `memset`. Housekeeping.

## Completion

Bonus 2 does not count occupied slots separately: the **progress word doubles as the
completion counter**. When it reaches `118` (`0x8005C6AC`) all five slots are
occupied, and the challenge fires — latch `6`, fade **60** (Bonus 1 and Bonus 3 use
30), vertical speed `-16384`, and `flags |= 0x01`.

## The progress feedback — all three chains, after all

The progress word `0x80082444` has **six** writers: Bonus 1 `0x8004B3A0`, Bonus 3
`0x800591B8`, Bonus 2's seed `0x8005C660` and its per-slot increment `0x8005C690`,
Bonus 2's init `0x8005BCC8`, and the consumer's clear `0x800558BC`.

⚠️ An earlier revision said **five** — it counted Bonus 2's seed but not the
increment loop that immediately follows it, the same block whose omission produced
the retracted "Bonus 2 never bursts" claim. A closure audit
(`tools/phase4_closure_audit.c`) caught the stale count; the mechanism described
below was already correct.

Bonus 1 (`0x8004B3A0`) and Bonus 3
(`0x800591B8`) compute `old_count + 114` directly. **Bonus 2 reaches the same values
by a different route**: `0x8005C660` seeds the word with `113`, and the block
immediately after it walks the five slots and adds 1 for each occupied one
(`0x8005C674` load, `0x8005C67C` skip-if-empty, `0x8005C68C` increment, `0x8005C690`
store). So the emitted command is `113 + occupied` = `114..118` for chains of 1..5 —
the same effective scheme.

The consumer is `player_action_effects_update` (`0x80055644`):

```
v0 = [0x80082444]
if (v0 < 115) goto skip          ; 0x80055828  slti v0,v0,115
  for (i = 0; i < 4096; i += 512)          ; 8 iterations, 45 degrees apart
      contact_object_spawn_full(flik.x, flik.y - 8192, flik.z, sin/cos, ..., v0 - 1)
[0x80082444] = 0                 ; 0x800558BC, consumed
```

So in **all three** challenges the first accepted step emits `114`, fails the gate and
shows nothing, and steps 2..5 emit `115..118` and each spawn a ring of **eight**
contact objects around Flik, 45° apart, off the sine table at `0x80074970`. The
object kind passed to the spawn is `command - 1`, so the burst differs per step.

Measured on the operator's mushroom reset recording: bounce 1 at movie frame 81 →
`114`, no burst; bounce 2 at 131 → `115`, burst; bounce 3 at 181 → `116`, burst —
matching the frames at which they reported seeing it.

⚠️ **Correction history, kept deliberately.** A previous revision of this page
claimed Bonus 2 wrote a constant `113` and therefore never produced the burst. The
`113` is real but it is a *seed*, and the counting loop that follows it was missed.
The operator refuted the claim from play. Both that error and the "landing does
nothing" error above came from the same habit — stopping at the first thing that
looked like an answer (the store, the delay slot, the first matching guard) instead
of reading to the end of the block.

## Verified

60 static pins (`tools/phase4_f17_f18_streak_law.c`, `-Werror`, including the
fixed-form scans over all 22 images), plus Interpreter-recorded replays of the
operator's `F17_Bonus02`, `F18_Bonus03` and `F16_Bonus02_Reset_Test` runs.

F18 showed the five accepts, the unlock, `0x80058B34` firing 630 times and
`0x80057428` firing once. The mushroom reset recording showed the append at movie
frames 81/131/181 (plant identities 6, 5, 4), the progress word going `114 → 115 →
116` with bursts on the second and third exactly where the operator saw them, and the
wipe stopping while airborne and resuming at frame 239 on landing.

Every reset path in both chains has now been watched destroying a live chain, except
the two housekeeping wipes (`0x80057428`, `0x8005BC94`), which are not player actions.
