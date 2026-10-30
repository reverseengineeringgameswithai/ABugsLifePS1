---
type: experiment
status: complete
date: 2026-08-02
system: enemy AI / D11 mites and grubs
phase: 4
artifacts:
  - analysis/phase4_d11_mite.json
  - ObsidianVault/Canon/Systems/SYS_enemy_ai.md
---

# Phase 4 D11 mites/grubs — mite identity, combat, and respawn

## Question

D11_mites_grubs was fully unresolved: "Locate mite/grub actor types in chunk-31 rosters"
was the row's own next-step, meaning even the actor IDs were unknown going in. Picked as
the next row after the D17 bird audit closed out.

## A false start: two pre-existing fixtures didn't show either species

Two old fixtures existed already, `D11_grub_contact_kill.movie.json` and
`D11_mite_contact_kill.movie.json` (both format v3, dated well before this session). Both
turned out to be misattributed:

- The "grub" movie's kill target is `id=12` — already Canon-confirmed as the **D12
  earthworm**. A live timing correlation (the earthworm's own flags changing exactly when
  Flik's health dropped) produced a tempting but WRONG hypothesis — that the earthworm
  "poked" Flik. `SYS_enemy_ai.md`'s D12 earthworm section already states its program has no
  strike mechanic at all (no `player_proximity` opcode, no `call_native`). Retracted; what
  actually hurt Flik there is unidentified.
- The "mite" movie is set in Birdnest (`scene_id=11`), not Cliffside, and every actor
  present — `id=11` (a large beetle), `id=37`, `id=30` (the D17 bird) — is already
  identified by other rows. None of it is fresh D11 evidence.

A full exhaustive scan of the game's own character-asset list (`analysis/phase3_asset_provenance.json`,
every `CHARS`/`CHARS2`/`CHARS3`/`CHARS4` `.ALL`/`.ANM` pair) confirmed `GRUB.ALL`/`GRUB.ANM`
genuinely exist as a distinct model, but there is no "MITE" asset anywhere. This was reported
to the operator directly rather than guessed at further.

## Identity: "canyon_bug" was always the mite

The operator redirected: *"Mites are in cliffside, the thing you thought were the shell
bugs from level 07"* — later clarified this wasn't claiming shell_bug (`id=18`) is a mite;
shell_bug is its own confirmed species in level 7 (chronological), unrelated. The actual
lead was an actor first encountered during the D13 shell_bug tangent
(`analysis/phase4_d13_shell_bug_armor.json`) and ad-hoc-named "canyon_bug" there — `id=37`,
hp 2, borrowing spider's own mover-VM program region — without ever confirming that name as
the creature's real identity.

Loaded `canyon_bug.sav` (a pre-existing fixture from that same tangent) directly, captured a
live frame, and got operator visual confirmation of a small orange/yellow segmented creature
with a striped abdomen and long snout/antenna as the mite. `gpu.pickObject` on the visible
sprite traced only to a generic, unnamed low-level GP0-FIFO push primitive (`FUNC_800645c8`,
no static callers), not a species-specific source — so identity rests on the operator's
direct confirmation plus behavioral corroboration, not an independent RAM-picking proof.

Operator, directly: *"i think they're the same bug yeah. Mite was from the manual and it is
accurate to what we were targetting."* **`id=37` = mite.** `canyon_bug` is left in earlier
notes as the historical working name, not rewritten.

## Combat and death

Fixture: `movies/Phase4/Interpreter/mite_kill.json` (1181 frames, v4, operator-recorded,
launcher-corrected Interpreter replay — `tools/launch_repro_playback.sh`).

Target instance `0x800A0AE8`. Only `square` presses recorded (no aim-lock, no kick
modifier), at three windows (f108-115, f150-159, f196-203) covering two actual throws:

| Event | Frame |
|---|---|
| Throw 1 gate activates (`0x800a6596`) | f127 |
| Throw 1 connects (hp 2→1) | f155 |
| Throw 2 gate activates | f169 |
| Throw 2 connects (hp 1→999, delayed-destroy sentinel) | f203 |
| Removed from live table (`0x80090748`) | f253 |

Max hp 2 — matches the D13 tangent's original figure for "canyon_bug" exactly, an
independent cross-check that this is the same actor under old and new names.

**Method note**: Flik's own position barely changes across nearly the whole movie under
`movie.advanceToFrame` (frozen from f180 onward), which briefly raised the already-documented
`advanceToFrame`-vs-60Hz concern from the D17 bird investigation. Re-verified via real
`debugger.resume` + poll (24 one-second steps) and got an identical result — Flik genuinely
does nothing but throw two berries early on, then wait. The concern did not apply here;
noted so a future pass doesn't re-spend the same verification step blind.

## Respawn — a genuinely new finding

The D13 tangent that first found this actor never tested its respawn. This directly
confirms the operator's own framing for the fixture: *"killing one, then it respawning akin
to a spider."*

Tracked the same pointer (`0x800A0AE8`) forward from its f253 removal. It reappears with
**full hp=2** at **exactly frame 1073** — an **820-frame gap, ≈13.7 seconds**, between death
and respawn. `D10_spiders`' own respawn timer isn't independently measured yet (still an
open item on that row), so this can't be cross-validated against an actual spider value —
it's the first hard respawn-timing number for this behavioral family, not yet confirmed
identical to spider's own.

**Campaign breadth is already closed, for free**, via the D13 tangent's own static scan:
mite (`id=37`) spawns in LEVEL01/06/08/10 only — LEVEL06 is Cliffside Canyon
(`scene_id=6`), exactly where this pass's live work happened. Never LEVEL04 (shell_bug's
level).

## The grub half, resolved the same day

Operator, after the mite half closed: *"if the grubs (previously worked on as earthworms)
aren't exhausted then go for it."* This directly named `id=12` — the very actor this note's
own "misattributed old fixtures" section above had just used to rule OUT the old
`D11_grub_contact_kill` movie as D11 evidence, because it was believed to be the unrelated
D12 earthworm.

Loaded `earthworm.sav` directly (a pre-existing D12 fixture with Flik already well-positioned
next to the target) and captured a live frame: a short, plump creature with a large rounded
head, a big eye, small ear-like features, and a dark segmented ridge trailing behind it.
Operator: *"yes that's a grub, we already established this."* The "earthworm" name traces to
an early static census table that was never independently visually verified — the identical
failure mode as `canyon_bug`→mite above, just discovered a few hours later on a different
species.

Because `id=12` had already been this session's D12 subject before the correction, its
identity/hp/no-strike-mechanic characterization already existed and didn't need to be
redone. What was genuinely missing — an independent live confirmation of the red/blue/gold/
mega armor classes, previously relying on operator testimony only — got closed in the same
pass. Getting there needed two method fixes:

1. **`emulator.pressButton` auto-pauses** once its own `seconds` hold duration elapses. A
   caller must issue a fresh `debugger.resume` afterward, or all subsequent polling reads a
   frozen game — confirmed live (the thrown-berry gate never changed across 4 continuous
   seconds of polling until this was fixed). A general method note, not species-specific.
2. **Facing is real, but direction-dependent by throw type.** A brief `left` d-pad tap
   (0.15s) before a straight throw fixes the connect. Homing throws (green, and mega —
   mega is *also* homing per the established kind table) need the opposite: no turn at all,
   default orientation. Turning before a mega throw made it whiff even after a 5-second
   wait; removing the turn let it connect at ~1.0-1.5s.

**Result: all 5 berry classes connect and kill this hp=1 actor** — green/homing (already
known), red-or-default, blue, gold (all three via the `left`-turn fix), and mega (via the
no-turn fix). **No armor at all**, unlike shell_bug/worm/wall_worm, which all specifically
block red. This upgrades "there is no armour for the little earthworms" from testimony to
independently live-verified fact.

Full detail: `analysis/phase4_d12_worm_id40.json`'s
`GRUB_IDENTITY_AND_FULL_ARMOR_SWEEP_2026-08-02`, cross-referenced from
`analysis/phase4_d11_mite.json`'s `GRUB_HALF_RESOLVED_2026-08-02`. Not moved into this row's
own artifact — the fixture and prior groundwork live under D12 for historical reasons.

## Type-word and aggro/chase — a third pass, same day

Operator: continue if the row isn't fully exhausted. Closed the two cheapest remaining
items: mite's chunk-31 type-word, and aggro/chase for both species.

**Mite type-word**: the runtime record backlink (`+0x80`, same field used for worm's
`id=40` identity) reads `0x0125` for both live `id=37` instances checked in
`canyon_bug.sav` — agreeing across two independently-positioned instances, unlike
per-instance data at other offsets. Low byte `0x25` = 37, matching the established
"type-word low byte = actor id" rule.

**Mite aggro, CONFIRMED NEGATIVE**: landed one non-lethal hit (the same throw from the
combat timeline, hp 2→1 at f155) and tracked flags/position for ~150 frames. The CHASE bit
(`flags+0x5c` bit `0x2`) sets on the hit, but distance from Flik increases steadily
afterward (53424→65129 units over 45 frames) — moving away, not toward Flik. The same
"bit sets, no pursuit" pattern already confirmed for shell_bug under D13.

**Grub aggro, CONFIRMED POSITIVE** — the interesting result. `hp=1` makes one hit lethal,
so a test-only HP poke (`+0x6e`, `1→8`, flagged explicitly as a test intervention) let the
actor survive a hit for observation. The CHASE bit sets the same way (`0x4001→0x4003`), but
this time position traces a genuine approach-then-retreat arc: distance falls from 15883
units to a minimum of ~4856 around t=3.0-3.3s, then rises back to 21657 by t=5.7s — the
same "approach/retreat stand-off oscillation" already documented for D09 Redbug. A second
flag transition (`→0x5001`, losing bit `0x2`, gaining bit `0x1000`) happens mid-arc while
the movement continues, suggesting the persistent pursuit state tracks `0x1000` rather than
the initial-hit bit — not independently confirmed.

**Grub chases; mite (and shell_bug) don't**, despite all three sharing the identical
CHASE-bit-on-hit mechanism. A genuine species-level behavioral divergence, not a testing
artifact — both tests used the same method on the same day.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_d11_mite.py
tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-d11 --port 23540 \
  --token debugger-1000 --execution-mode Interpreter \
  --disc "Disney-Pixar A Bug's Life (v1.0).cue"
```

All live reads this pass were operator-recorded movies replayed via `movie.advanceToFrame`
(cross-verified once via real `debugger.resume` polling), not a scripted/asserted oracle.

## Residuals

The exact RAM identity of the specific mite instance visually confirmed (picking traced
only to a generic GP0 primitive); whether the 13.7s mite respawn timer is fixed or
randomized (one cycle observed); grub's own respawn timer (not tested — only mite's was
measured); the exact identity of the persistent-pursuit flag bit `0x1000` seen mid-arc in
grub's aggro test (correlates with sustained movement, not independently confirmed as the
driver); whether a genuine, distinct "earthworm" species exists anywhere in the game now
that `id=12` is known to be the grub (unexplored); grub's campaign breadth re-verified
under the corrected identity (same underlying LEVEL03-only records, not re-scanned as a
grub-specific search);
source closure; cross-system audio/HUD for both species.

## Exhaustion assessment

Operator asked directly whether this row had been worked enough to move on. **Verdict:
BOUNDED PARTIAL — stopping deliberately, not abandoning mid-thread.** The high-value
questions are answered and cross-verified for both species: identity (both corrected from
wrong working names, with operator visual confirmation each time), combat/death, armor
(grub's full 5-class sweep — no armor at all), respawn timing (mite, first measurement for
this behavioral family), and aggro/chase (a genuine divergence — grub chases like Redbug,
mite doesn't like shell_bug, despite sharing one flag mechanism).

Every remaining residual above falls into one of four buckets, none of which is a live open
question likely to change anything already banked: **repetitive measurement** with a
predictable outcome (grub's respawn timer — almost certainly a similar order of magnitude
to mite's already-measured 820 frames); **speculation with no concrete lead** (whether a
genuine separate "earthworm" exists at all); **routine bookkeeping over already-known data**
(grub's campaign breadth is already scanned under the pre-correction name against the same
disc records — re-running it just re-stamps the label); or **standard last-mile
completeness** every row in this baseline carries until much later (source closure,
cross-system audio/HUD, the flag-bit-`0x1000` identity). Neither `D11_mites_grubs` nor
`D12_centipedes_earthworms` is upgraded to `solved` by this note — it documents the
stopping point, not a closure.
