---
kind: experiment
id: EXP_2026-08-03_phase4_c04_enemy_token
status: complete
source_state: original_game
system: [SYS_enemy_death_and_permanence]
row: C04_enemy_token
---

# Phase 4 C04: enemy success token quota — construction and exclusions

## Question

Operator: "go for C04." The row's own `next` field asked: find the quota INITIALIZER for
`0x800A658E` (what populates it at level load) and its exclusion set — the decrement side was
already Canon, but nothing had ever traced where the starting per-level value comes from.

## Why static search alone wasn't enough

Grepping `asm/nonmatchings/resident/*.s` for the address found only the two already-Canon
decrement sites (inside `FUNC_800498AC` and the contact handler near `0x8005921C`) and two
already-Canon read sites — no write. `debugger.xrefsTo` against the live image independently
confirmed exactly those same 4 references, nothing more. `transferLog.resolve` reported no
disc/DMA provenance for the address either, ruling out a bulk block-copy. Since the address
doesn't fit a gp-relative encoding (offset from `$gp`=`0x80081D98` is `0x247F6`, too large for
a 16-bit immediate), a literal-immediate write should have shown up in either search if one
existed — it didn't, which pointed toward a computed/looped write instead.

## Method

Reused the pre-existing `flik_to_level01_stall.mv.movie.json` (v2, from-boot, 4253 frames) —
but replayed its own recorded input **live**, frame-by-frame via
`emulator.setControllerState`+`emulator.advanceFrames` per contiguous button-state segment,
never through `movie.startPlayback`. This sidesteps any CachedInterpreter-vs-Interpreter
mode-mismatch risk entirely, since the whole isolated session already runs in Interpreter
mode from `debugger.reset` — arming `accessLog` at any point is unconditionally safe.

The recorded input stalls at a pre-gameplay transition (`scene_id` 17, Flik's health still 0,
position pinned at origin) — reaching real gameplay needed one additional `cross` press not
present in the original recording. Armed an `accessLog` write-watch on `0x800A658E` **before**
that press.

## Result

Four write events landed on the SAME PC in immediate succession (same emulator frame, four
different cycles): `0x80046c64`, instruction `sh v0,0x8e(s3)`, stepping the value 0→1→2→3→4.
This is `FUNC_80046B20` — a function already Canon for an entirely different job (the
level-load player-spawn writer that fills Flik's own 168-byte block from the scene-start
table at `0x80077314+index*12`). Its **second half**, immediately following that write, was
never previously attributed to anything.

Disassembling the full function (`debugger.functionBounds` confirms an exact, clean, 396-byte
span — no merged region) shows:

1. `0x80046c10`: `sh zero,0x8e(s3)` zeroes the quota field before scanning. `s3 =
   0x800A6500` — Flik's own player-struct base — so the quota is actually **player+0x8E**,
   not a bare unrelated global as the existing binding implied.
2. A 64-iteration loop (`t1` counter, `slti v0,t1,64`) walks the enemy actor pool at base
   `0x8009FD80`, stride `0x84` (132 bytes) per record via `t0 += 132` each pass.
3. Per slot: if `id` (`+0x00`) is `0` (empty slot), skip. Otherwise read flags `+0x5C` and
   mask `0x08A0`; if any of bits `0x0800`/`0x0080`/`0x0020` are set, skip. Otherwise
   increment the quota by 1.

## Cross-validation

`level01.sav` (already-loaded mid-gameplay save): quota `4`, matching the live trace exactly.
`level02.sav`: quota `50`. Two different levels, two very different, both-plausible totals —
this is a genuinely **computed** per-level value from the actual spawned actor pool, not a
fixed table constant.

## Exclusion bits — partially explained, not fully closed

`0x08A0 = 0x0800 | 0x0080 | 0x0020`. The `0x80`/`0x20` sub-mask is not a coincidence:
`D14_wasps_dragonflies`' own homing-berry targetability filter independently found the exact
same two bits rejected from the homing-target scan (bit `0x1` required, bits `0xA0`
rejected). A non-targetable/decorative actor (D14's wander-only dragonfly, with no strike
mechanic at all) plausibly reads the same underlying "is this a real, killable enemy" flag
for both purposes. Bit `0x0800`'s meaning is **not confirmed** — a natural hypothesis (boss
actors excluded, since their defeat is a scripted HP-threshold event, not a permanent-kill
decrement) was not tested live this pass and is flagged as a hypothesis only.

## Token grant — the quota reaching zero DOES trigger level-complete (2026-08-03)

Operator: "one of the 100% runs in interpreter should do the trick. Dig deeper" — directly
answering the open question this note's first pass left unresolved (what does reaching
quota `0` actually **do**?).

Replayed `movies/Phase4/Interpreter/100% Runs/LEVEL06.movie.json` (v4, 12917 frames, a
Birdnest 100% completion run — safe to trace normally via `movie.startPlayback`, unlike the
CachedInterpreter-era boot movie used for the construction trace). Polled the quota until it
hit `0` (movie-frame ~8472, emulator frame `130337`), then armed targeted `accessLog` writes
on both the quota and `0x800823A0` — the campaign's own generic goal-latch address, already
Canon from `D19_molt`'s boss-defeat victory handoff. A broad watch on `0x800823A0` filled its
event ring with unrelated high-frequency scratch writes before ever reaching the interesting
frame (it's a heavily-reused address) — had to re-arm narrowly, starting a few frames before
the transition, to actually catch it.

**Result**: at the exact same emulator frame as the quota zero-out, `0x800823A0` writes `1`
and `0x80082470` writes `150` — the identical `goal_latch=1`/`transition_ticks=150` pair
already Canon from `D19_molt`'s own boss-defeat handoff. Both writer PCs sit inside the same
contiguous overlay block. Disassembling the full gating chain: the routine requires an
unidentified progress counter (`*0x800A0316 >= 21`), the goal latch not already set (a
repeat-guard), and a register `s2` (caller-set, not traced) equal to `1` — only then does it
compare the quota against `s2` (i.e. against `1`, the last-enemy-remaining state): if equal,
zero the quota and spawn the Flik-positioned effect+SFX. Critically, the goal-latch/timer
write is reached by **unconditional fall-through from either branch** of that comparison —
meaning it fires whenever the three gating conditions hold, with the quota finalization as
an additional action specifically gated on quota `== 1`. This confirms the block genuinely
IS the enemy-elimination completion handler, not a coincidental neighbor.

Visually confirmed the full sequence: a "level complete" screen at `00/50`/`0/4`/`00/09` with
three red "?" (locked) token icons, the same screen ~500 frames later at `50/50`/`4/4`/`09/09`
with three real token icons revealed (bronze/leaf, silver/FLIK, gold/X), then "Congratulations!
Bonus Movie Clip Earned" → loading. Same shared results-screen frontend already documented
for `F06_birdnest`/`F15_canyon_showdown` this session, not a new UI.

**One honest caveat**: a 100% run completes grain/FLIK/seed AND the enemy quota
simultaneously by construction. The instruction-level evidence (same frame, same overlay
block, unconditional fall-through structure) is strong causal evidence independent of the
other three counters — but a fixture that completes ONLY the enemy quota while leaving the
others short would be the fully isolating test, and wasn't run this pass.

## What's still open

Bit `0x0800`'s exact meaning; whether the loop re-runs on scene re-entry (death/respawn,
pause-restart) or only fires once per `FUNC_80046B20` call; save-reload serialization of the
quota within a level; a fuller per-level census beyond the two spot-checked levels; whether
either boss row's own evidence ever touches this same field; register `s2`'s exact provenance
in the goal-latch handler (hypothesized objective-type selector, not traced to its caller);
`0x800A0316`'s own meaning; a dedicated fixture isolating enemy-elimination completion from
the other three counters.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_c04_enemy_token.py
```

The live trace used an isolated instance at `/tmp/dsrepro-c04-enemy-token-20260803`
(port `23610`, `--execution-mode Interpreter`), stopped cleanly after the investigation.

## Evidence

`analysis/phase4_c04_enemy_token.json`; existing Canon:
`ObsidianVault/Canon/Functions/FUNC_80046B20_FUNC_80046B20.md` (extended with the new second
half), `ObsidianVault/Canon/Systems/SYS_enemy_death_and_permanence.md`.

## 2026-08-04 bounded-exhaustion addendum (supersedes the resident-only model)

**Status:** Substantiated Partial / bounded-exhausted for the C04 workstream. Move on.

### Correction

The previous statement that level overlays and BITS/MEMORY.BIN do not touch 0x800A658E is false. A C constant-address census over the pristine executable, every staged level overlay, and BITS/MEMORY.BIN found ten direct non-resident writers. The retained mechanism is therefore not a single resident decrement counter; it is a resident-built quota with explicit level-specific adjustments and results-screen normalization.

### Observation

- 0x8005BAA4 calls constructor 0x80046B20 during scene-runtime reset.
- The constructor rebuilds the live quota from the 64-entry actor pool, excluding zero ids and actor +0x5C flags masked by 0x08A0.
- 0x8005BADC immediately reads the rebuilt quota and 0x8005BAE4 snapshots it to 0x80082258 as the initial total.
- Resident paths 0x800498F8..0x80049904 and 0x800592F4..0x80059300 perform ordinary quota-- updates.
- The same actor +0x5C field is read at 0x8004AE94; bit 0x0800 is tested at 0x8004B0C4, and a set bit bypasses the resident interaction/update tail. This closes the bit's structural effect without inventing an unsupported content-author name.
- BITS/MEMORY.BIN clamps negative remaining values to zero, computes defeated enemies as [0x80082258] - [0x800A658E], and awards the enemy results axis only when remaining is zero.
- Direct overlay mutations are pinned in LEVEL01/LEVEL1.BIN, LEVEL02/LEVEL.BIN, LEVEL02/LEVEL1.BIN, LEVEL03/LEVEL1.BIN, LEVEL04/LEVEL1.BIN, LEVEL05/LEVEL1.BIN, LEVEL08/LEVEL.BIN, and LEVEL09/LEVEL.BIN. They include -7, -1, 57 -> 56, and conditional cleanup-to-zero operations.

### Bird Nest objective correction

The final objective latch is not simply quota == 0. 0x800B3F50 initializes s2=0, and 0x800B3FBC sets s2=1 only for the matching progress edge. At 0x800B4098..0x800B40C4, s2==1 && quota==1 enables a cleanup write of zero. Once the independent threshold and once-only guards pass, the objective latch at 0x800B4100 is downstream of both sides of that quota branch. Thus quota cleanup and objective completion are related but not identical predicates.

### Bounded residuals

- A table of exact live initial values for every campaign scene would require a validated fixture or retained capsule per scene because the pool is populated at runtime. It is enumeration, not a missing mechanism edge.
- No human-facing name for scene-data flag 0x0800 has been recovered. Its exclusion and update-bypass effects are ASM-pinned.
- The constant-address census does not claim against aliases obtained through pointers loaded from RAM.
- Exact save/re-entry routing into the reset entry remains unnamed; reconstruction and initial-total snapshot on that reset path are pinned.

No new Interpreter movie is required. The remaining gaps either need campaign-scale enumeration or naming evidence and have minimal return for C04 closure. Reproducible verifier: tools/phase4_c04_enemy_token.c; machine-readable result: analysis/phase4_c04_enemy_token.json.
