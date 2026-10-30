---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Thumper boss fight.md
aliases:
  - "Thumper boss fight"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Thumper boss fight.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Thumper_boss_fight.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Thumper boss fight
type: system
updated: 2026-07-03
confidence: CONFIRMED (movie-anchored diffs + poke-falsified defeat threshold)
tags: [system, boss, thumper, enemy, hp, combat, gap-0034]
---

# Thumper boss fight — solved

> Decoded 2026-07-03 from the operator's complete **`thumper_boss_2.movie.json`** (3092 frames)
> + live poke-falsification. RE source: `src_re/thumper_boss.c`. **Closes the long-open
> "Thumper combat bookkeeping" residual** — and refutes two prior claims: the fight actor is
> NOT `0x80095358` (that's the camera), and the combat is NOT in a boss overlay (it's resident).

## The actor — Thumper is a regular chunk-31 enemy
Scene 2 (LEVEL03 dir). During the fight the damageable table holds:
- **`0x8009fe04` id 16 = THUMPER** — a normal [[Enemy spawn architecture]] actor: chunk-31 spawn-record backlink (`+0x80 = 0x80094a54`), flags `+0x5c = 0x4053` (targetable `0x1` + chase-enable `0x2` + **berry-tough `0x40`**).
- **`0x8009fe88` id 10 = the thrown MOSQUITO** — its own persistent chunk-31 actor (species callback `0x8004a180`).

### The mosquito throw (traced in the act — movie frame 58953, operator's 58950–58973 window)
The mosquito idles **parked at a perch** (pos == target, flags `0x0002`). The launch is **native code inside the per-actor update handler `FUNC_800498AC`** (`0x800498ac..0x80049e84` — the same function whose death-anim branch handles enemy deaths; the launcher branch is ~`0x80049c98..0x80049db8`):
1. `0x80049c98` → mosquito `+0x70` (VM IP) = **`0x80077654`** — the FLIGHT program (a program-table entry);
2. `0x80049db0/b4/b8` → mosquito target `+0x34/38/3c` = the **aim point** (toward Flik's area);
3. flags `0x0002 → 0x4007` (live + **targetable** — it becomes hittable mid-flight).

The flight program `0x80077654` is a plain VM seek loop (`[params][flags|0x4][anim][wait rnd][random-dir jitter][PARK seek-target] LOOP`) — the mover-VM flies it to the aim point with jitter. **The "throw" = re-seed IP + aim + arm; the flight is ordinary VM motion.** (Also refines [[Enemy AI movement programs]]: `FUNC_800498AC` is the broader per-actor update/behavior fn — death-anim, mercy-drop roll, and species actions like this launch are all branches of it.)

Thumper's mover-VM program is **park-in-place** (`0x800776ac` `[op8 PARK][op0 LOOP]`); his flight/attack cycle runs in the **species callback `+0x7c = 0x8004a0f4`**. Fight phase/attack counters tick at `0x80090bf2`/`0x80090bf6`. (The old "Y-law @`0x8004e6cc`" was measured inside the camera fn — contaminated; real Y behavior is the driver's.)

## HP + the berry-tough damage law (RESIDENT — overlay claim refuted)
**HP = `actor+0x6e` (s16), starts 50.** Every berry hit in the movie: −2 (50→46→44→…→20), sole writer `0x800590e8` — inside **`contact_vs_actor_handler`'s berry-tough branch @`0x8005905c`**:
```
hp = enemy[+0x6e];  if (hp >= 100) skip;      // regular enemies park 999 here
cls = berry_record[+0x2c];                    // per-berry DAMAGE CLASS byte
cls==0: −2 · cls==1: −99 (near-instakill) · cls==12: −2 · 127: −4 · 128: −3 · default: −1
```
- The `hp≥100` guard is *why* regular enemies (whose `+0x6e` holds the 999 hit-marker) never take this path — dual-use of the field, clean design.
- This is **also the per-berry damage table vs berry-tough enemies** (worm/wall_worm share the path) — resolving that [[Berry projectile and homing]] residual. Class byte = contact record `+0x2c` (seeded from the berry param table's sub-index).

## Defeat trigger — HP ≤ 20 (causally proven)
Poke test mid-fight: `hp=21` → nothing; **`hp=20` → within frames the defeat FSM `0x80090bee` flips to 2**, written by the setpiece-init block @`0x8004db44` (the `0x8004dbxx` sibling of `setpiece_spawn_init` populating `0x80090bc0..bee`) → the previously-decoded chain: finale `FUNC_8004DA94` → scripted end-of-fight approach (`FUNC_8004DD98`, setpiece actor `0x80090bc0`).

**Fight math: 50 → 20 at −2/hit = 15 berry hits to defeat Thumper.** (The movie shows ~15 damage events between the first hit and the FSM flip.)

## Method + a new gotcha
- The movie's deterministic anchors (first damage ~abs 59025, defeat ~60130) let snapshot-diffs pin HP in two windows; `accessLog` write-watch caught the single writer.
- **GOTCHA:** a v1/v2 movie replay **can drift when heavily paused by debugger breakpoints/watches mid-playback** — run 2 fell ~2 hits behind and the recorded kill never landed. The poke-falsification closed the threshold instead (stronger evidence than replay anyway). Prefer pokes/thresholds over exact replay timing for boss work.

## Residuals
- Thumper driver `0x8004a0f4` internals (hover band, swoop triggers, throw cadence — behaviorally visible, not instruction-decoded).
- The exact HP→20 comparison site (the flag WRITE is pinned; the compare is in the caller — likely the boss driver or manager).
- The damage-class byte (`+0x2c`) ↔ berry-type map (which berry carries class 1/127/128 — class 0 = the movie's berry, −2).
- Thud: untested (same decode recipe applies; needs a complete recording or in-fight save).

## Related
[[Enemy AI state machine]] (Thumper section superseded) · [[Enemy spawn architecture]] · [[Enemy AI movement programs]] · [[Enemy death and permanence]] · [[Berry projectile and homing]] · [[Retail Gameplay Completeness Gap Audit]] RCG-006
