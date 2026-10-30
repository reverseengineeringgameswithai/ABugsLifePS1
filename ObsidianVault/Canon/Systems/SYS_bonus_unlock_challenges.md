---
kind: system
id: SYS_bonus_unlock_challenges
name: Native bonus unlock challenges
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_8004ABF4
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-07-11_bonus_unlock_challenges
  - src_re/bonus_unlock_challenges.c
src_paths:
  - src_re/bonus_unlock_challenges.c
---

# SYS_bonus_unlock_challenges

## Shared original-game flow

The three hidden challenges are performed in ordinary gameplay scenes. Success
sets shared transition latch `0x800823A0` to `6`, starts a fade through
`0x80082470`, sets one low bit in `0x8009B889`, and then changes the current
scene at `0x80082504` to `0x10`. Scene `0x10` is the **Bonus Level**
loading/playback wrapper: it runs the playable bonus sequence, shows the
"Congratulations! Bonus Movie Clip Earned" result, and returns to the journey
menu (`scene 0`). It is not the scene where the unlock challenge itself occurs.

Progress feedback is sent through `0x80082444`. Each accepted step writes
`old_count + 114`, corresponding to progress commands `114..118` for steps
`1..5`; shared HUD flow can clear the word before a later sample.

The packed bonus byte uses low unlock bits `0x01`, `0x02`, and `0x04` for
Bonuses 2, 1, and 3 respectively. Their high-nibble counterparts `0x10`,
`0x20`, and `0x40` guard challenges that have already been earned. Shell code
around `0x8004FFC0..0x80050000` mirrors a three-bit nibble with multiplication
by `17`, explaining states such as `0x22` before Bonus 2 and `0x33` before
Bonus 3.

## Bonus 1: five spider butt-slams

- Verified route fixture: Training (`scene 0x11`), in the spider arena. This is
  not a hard scene gate; any ordinary stage with five qualifying
  butt-slammable interactions can satisfy the predicate.
- State: `0x8008223C`, `u32`, counts qualifying butt-slam targets.
- Writer block: `0x8004B35C..0x8004B3D0`, late in
  [[FUNC_8004ABF4_proximity_updater_8004abf4]].
- Guard: skip when bonus earned bit `0x20` is set or scene `0x10` is active.
- The fifth success sets low bit `0x02`, latch `6`, fade `30`, and resets the
  counter to `0`.

The verified movie progressed `1, 2, 4, 4, 0`; the fifth store at
`0x8004B3A8` was followed once each by flag store `0x8004B3B4`, latch store
`0x8004B3C0`, and reset store `0x8004B3D0`. This corrects the older description
of `0x8004B3C0` as a generic type-6 level-exit lever: this late branch is the
Bonus 1 challenge completion path. It does not change the separate conclusion
that the function's entry proximity test is not LEVEL01's normal exit.

## Bonus 2: five distinct mushroom bounces

- Verified route fixture: scene `1`. This is not a hard scene gate; any
  ordinary stage that permits five distinct mature type-5 seed mushrooms can
  satisfy the predicate.
- State: five signed plant identities at `0x80082248..0x8008224C`; `-1` means
  empty.
- Writer block: `0x8005C548..0x8005C6E4` in the type-5 mushroom handler of the
  plant behavior walker associated with [[FUNC_8005BDBC_plant_spawn]].
- A new mushroom identity is appended at `0x8005C580`. Touching an identity
  already in the sequence restarts the chain as `[current,-1,-1,-1,-1]` at
  `0x8005C548..0x8005C56C`.
- Five occupied slots set low bit `0x01`, latch `6`, fade `60`, and vertical
  speed `-0x4000`.

The verified sequence was `[6]`, `[6,5]`, `[6,5,4]`, `[6,5,4,2]`, then
`[6,5,4,2,3]`. The important rule is **five different mushrooms in a row**;
five contacts that include a duplicate do not qualify.

## Bonus 3: five blue-berry grasshopper kills without a miss

- Verified route fixture: Tunnels (`scene 3`). This is not a hard scene gate;
  any ordinary stage with qualifying actor-ID-15 grasshoppers can satisfy the
  predicate.
- State: `0x80082240`, `u32`.
- The contact-vs-actor handler resets the streak at `0x80058B34` whenever the
  native berry selector `0x800A6597` is not `1` (blue berry).
- After enemy local HP reaches zero, `0x8005916C..0x800591EC` accepts only
  contact damage class `0` against actor ID `15` (grasshopper), while earned
  guard `0x40` is clear.
- The fifth accepted kill sets low bit `0x04`, latch `6`, fade `30`, and resets
  the streak.
- Contact-dispatch case `13` resets the streak at `0x80059A0C`. A controlled
  in-memory edit added a two-frame throw after kill 4 while Flik was stationary:
  case 13 executed once, streak `4 -> 0`, and the original fifth grasshopper
  produced streak `1` without a transition. Earlier edits near frame 900 were
  rejected because they changed the later route enough to cause a fall.

## Clean-playback fall/desync guard

The solved native bottomless test in `FUNC_80048138` compares `player_y` with
`[0x800822B4] + 8192` at `0x80049808`. Its fall/respawn branch reaches the life
adjustment at `0x80049858` and the transition-mode-2 call at `0x80049868`.
Neither PC executes before any of the three clean bonus unlocks. Full-RAM hashes
at the unlock frames also match observer-free playback exactly. The accepted
stationary miss branch remained in scene 3 with transition latch 0; see the
experiment for the rejected and accepted controls.

See `src_re/bonus_unlock_challenges.c` for exact documentation-grade C slices
and [[EXP_2026-07-11_bonus_unlock_challenges]] for deterministic runtime
checkpoints, hashes, the rejected observer-desync trial, and provenance.

## Phase 4 D10 scoped closure (2026-08-02)

D10's spider-chain and handoff scope is confirmed. Offline C reconstruction of the valid retained Bonus 1 capsule found the exact counter transitions at movie frames 128, 352, 590, 742, and 1072; the fifth event set low flag `0x02`, transition latch 6, and the fade before scene `0x11 -> 0x10` at frame 1131. The same capsule records high earned guard `0x20` joining the low bit (`0x22`) at frame 2742 and the wrapper returning to journey-menu scene 0 at frame 3206. All 10,962 reconstructed RAM/VRAM/SPU domain hashes matched.

Static ASM confirms that the native block counts five qualifying interactions, not a stored uniqueness list: interaction halfword `+0x0A` selects the path, earned bit `0x20` and scene `0x10` suppress it, and new count 5 alone triggers the unlock. A C census found no alternate direct GP-relative increment; the only additional direct references are clears in shared transition/reset routines. Bonus-stage internal rules and power-cycle save persistence remain outside D10. See [[EXP_2026-08-02_phase4_d10_spider_chain]].

### D10 executable closure follow-up

The extended pristine scenario passed all nine assertions through the final scene-0/flags-`0x22` state. A compiled C model of the decoded instruction block separately passed the four-event negative threshold, exact fifth-event completion, earned-bit guard, scene-`0x10` guard, and shared transition reset cases. These close the executable and negative-control gaps for the scoped D10 claim.

## Phase 4 C18 downstream closure (2026-08-04)

The observed scenes above are fixtures, not exclusivity rules. Resident trigger
code is condition-based across ordinary stages: five qualifying butt-slammable
interactions, five distinct mature type-5 mushrooms, or five qualifying blue
class-0 kills of actor ID 15. Bonus 1 and Bonus 2 explicitly exclude scene
`0x10`; Bonus 3 has no scene test. The earned high bits remain the repeat guards.

Transition mode 6 arms a one-shot shell override to scene `0x10`, which loads
`LEVEL06/LEVEL1.BIN`. That overlay uses persisted byte `0x8009B88A` as a
three-entry variant/target selector. It completes when Flik's target-relative
coordinates, each shifted right by 8, have squared distance `< 1600`; completion
writes transition mode 1 and fade 30.

The shell treats the challenge bit as tentative until that success return. Mode
1 commits `flags = (flags & 0x0F) * 17`, advances `0x8009B88A`, and plays FMV
`42 + old_ordinal`. A non-success return restores
`flags = (flags >> 4) * 17`, does not advance, and plays no reward. Movie IDs
42/43/44 are therefore completion-order rewards rather than challenge-identity
constants. All six challenge orders converge on flags `0x77` and ordinal 3.

The save serializer/deserializer's 19-byte block from `0x8009B878` includes
both bytes: bonus flags at offset 17 and the completion ordinal at offset 18.
The reward path writes no health, lives, or grain. Full evidence:
[[EXP_2026-08-04_phase4_c18_bonus_entry]] and
`analysis/phase4_c18_bonus_entry.json`.
