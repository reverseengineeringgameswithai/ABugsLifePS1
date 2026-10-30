---
kind: experiment
id: EXP_2026-08-04_phase4_d17_bird_defeat
status: complete
source_state: original_game
system: [SYS_bird_boss, SYS_cinematic_camera, SYS_event_vm]
row: D17_bird
---

# D17: the bird's defeat is a HALT, and the "frozen HP" was a per-hit restore

The row's central binding said defeat is *"an instantaneous vm_ip jump to a COMPLETELY DIFFERENT
part of the shared mover-VM bytecode (`0x800776ac` 'park_arrive_stop' / `0x800776ae` 'jump_back')"*
and that *"hp freezes in the 18-22 range, never reaches 0"*.

The jump is real. The labels are fiction ([[EXP_2026-08-04_mover_vm_indistinguishable_opcodes]]),
and the frozen HP was never a mystery — it is a threshold plus a restore.

## What the two IP positions actually are

Decoded at the byte level:

```
0x800776AC   stream  7  -> handler 0x8004C818   ; the interpreter's LOOP TAIL -- no body
0x800776AE   stream -1  -> jump_back [1] -> 0x800776AC
```

**An infinite do-nothing loop: yield, jump back, forever.** Defeat parks the bird's mover-VM in a
null program — its AI is *halted*. Not "stopped on arrival".

And the circling state is not a `park_seek` either. `0x8007788C` sits inside an ordinary wander loop
— the same shape Thumper runs:

```
0x80077878  set_byte_params [-64,-64]
0x8007787E  anim_clip_load [0,13]
0x80077884  wait_random [63,32]
0x8007788A  random_dir_step
0x8007788C  <- yield          (the IP the row saw it "parked" at)
0x8007788E  jump_back -> 0x80077884
```

## What the "freeze" actually was

Traced on `D17_Goldberry.movie.json` (Interpreter, ring not truncated). Bird located at
`0x800A02A8` by finding the actor whose VM IP lies inside the wander program — it has **no species
callback** (species 30 takes the dispatcher's common arm), so the callback-pointer locator used for
Thumper is unavailable.

| frames | what happens |
|---|---|
| 165980 – 166828 | **nine** hits of **−3** (50 → 47), each immediately **restored to 50** by the overlay at `0x800B3F8C`. The bird cannot be killed by these. |
| 166930 – 167168 | hits of **−4** land and accumulate: 50 → 46 → 42 → 38 → 34 → 30 → 26 → 22 → **18** |
| 167170 | two frames later, `0x800B4158` installs the halt program |

So HP never reaching 0 is not a freeze — **the fight ends on a threshold**, exactly like Thumper
(`HP <= 20`). The other fixture froze at 20; both sit in the same band.

This is the **same HP-latch pattern D18 found on Thud** ("pool HP = hit LATCH restored by overlay").
Three bosses, one architecture.

⚠️ **This is not two phases.** It looked like one on first reading, and the "restores stop" framing
was wrong. The restore is a **per-hit gate on the damage value** — see *The damage law* below. The
`slti a0,5` counter at `0x800B441C` gates the *launch-high*, not the restore, which is why nine
restores coexist with a counter that caps at five.

## The damage instruction — a named `next` item, now closed

The row recorded −4/hit as behavioural and "not traced". Every HP decrement comes from **one PC:
`0x800590E4`** — `berry_tough_damage_dispatch`, the *same* instruction that damages Thumper.
Deltas are **−3 and −4**, not only −4: −3 during the restored phase, −4 during the lethal phase.

## The defeat block is the same architecture as Thumper's

`LEVEL01/LEVEL1.BIN` (identified by writer PC: `0x800B4158` is `sw v1,792(at)` = `0x800A0318`, which
is exactly the bird's `+0x70`):

```
0x800B40F8  v0 = 1
0x800B4100  sh v0,[0x800823A0]      ; *** THE GOAL LATCH -- the level exit ***
0x800B4104  v0 = 150
0x800B410C  sh v0,[0x80082470]      ; the 150-frame timer
0x800B4118  v0 = 2  -> 20(sp)       ; cinematic-camera FLAGS = 2
0x800B4148  v1 = [0x80077B2C]       ; program-table entry 13 = the HALT program
0x800B4158  sw v1,[0x800A0318]      ; bird's VM IP := halt
0x800B4160  sh v0,[0x800A0304]      ; bird's flags: andi 0xFFFD, ori 0x80
0x800B4164  jal 0x8004DA94          ; start the cinematic camera
```

Compare Thumper ([[EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber]]): goal latch `= 1`,
150-frame timer, `jal 0x8004DA94` with flags `= 2`, boss disabled, same `andi 0xFFFD / ori 0x80`
flag shape. **Boss defeat is a shared template**, instantiated per-boss with a different disable
(Thumper: `+0x62 = 10000`; bird: park the VM).

## What moves the bird after the halt

With the VM halted, the "retreat" cannot be mover-VM motion — and it isn't. Post-halt position
writes come from the interpolation code (`0x8004CD64` X, `0x8004CDCC` Z) and, for Y, **also the
overlay at `0x800B42B8`** (149 writes). The climb is overlay-driven, the same way Thumper's hop is.

## The damage law — and a hypothesis of mine that did not survive

`tools/phase4_d17_damage_law.py` → `analysis/phase4_d17_damage_law.json`.

Reading the overlay showed the restore is **not a phase** but a per-hit gate
(`LEVEL01/LEVEL1.BIN` `0x800B3F34..0x800B3F98`):

```
a0 = reference_hp - current_hp     ; damage this hit
if (a0 != 3)             skip      ; only a 3-damage hit qualifies
if ([0x800A6597] != 3)   skip      ; ...and only with index 3
if ([0x800B441C] < 5) counter++
[hp] = reference                   ; RESTORE (delay slot -- always runs once reached)
```

I hypothesised that `0x800A6597` (the equipped-berry index) is what separates the −3 hits from
the −4 hits. **It does not.** Traced live, that index holds **3 for both** — the tool reported
`NOT SEPARABLE` rather than manufacturing a confirmation. The gate's index test was simply always
true in this fixture, so the separation comes from the **damage value alone**.

The real discriminator is in `berry_tough_damage_dispatch` itself, a branch chain on a berry-type
value in `v1` at `0x800590A4..0x800590D4`:

| berry type (`v1`) | damage |
|---|---|
| 127 | **−4** |
| 128 | **−3** |
| (two further arms) | −2 |
| default | −1 |

So the bird *is* berry-type dependent — I was testing the wrong variable. `0x800A6597` is the
**side-table index** used four instructions later (`0x800590F0`, feeding the 64×5 table at
`0x80089938`), not the berry type that picks the damage.

## What the 0x800B441C counter actually gates

Not the phase — **the launch-high**. `0x800B3E50` reads it, and while it is `< 5` the overlay writes
`0xFFFDCFF0` into the bird's anchor Y (`+0x2C`) and target Y (`+0x38`) and clears flag bit `0x02`.
Measured live: the counter walks **0 → 1 → 2 → 3 → 4 → 5** and caps, while **nine** restores occur —
exactly as the code implies, since the restore store sits in a branch delay slot and keeps running
after the counter stops incrementing.

That is the row's *"obtaining a gold berry LAUNCHES THE BIRD HIGHER"*, now pinned: **capped at five
launches.**

### Still open on the damage law

Which berry corresponds to type 127 vs 128. That needs the value of `v1` **at** `0x800590E4`, which
is a register at an instruction — a breakpoint or `execTrace` capture, not a data watch. Not
attempted here.

## The full damage table — and why the Cliffside bird was never damaged

`berry_tough_damage_dispatch` selects the damage from a berry-TYPE **byte at
`projectile + 0x2C`**. The projectile pool is a fixed resident global: base `0x800B0D18`,
entries from `+8` (`0x800B0D20`), stride `0x38`.

```
0x80059068  slti v0,v0,100        ; *** HP >= 100 -> skip the damage table entirely ***
0x80059074  lbu v1,0x2C(s1)       ; the berry type
0x8005907C  v1 == 12   -> -2
0x8005908C  v1 == 0    -> -2
0x80059094  v1 == 1    -> hp - 99
0x800590A8  v1 == 127  -> -4
0x800590B0  v1 == 128  -> -3
default                -> -1
```

**The `slti v0,v0,100` gate closes an observation this row already recorded but never
explained.** The row's Cliffside binding notes the same actor id=30 appears there with
**hp 101 instead of 50** and is *"never damaged"*. That is not tuning — **101 ≥ 100, so it
never reaches the damage table at all.** Giving the Cliffside bird 101 HP is how the
designers made it invulnerable, using a threshold the row had no reason to suspect.

## ⚠️ RETRACTED: "addBreakpoint does not fire"

An earlier revision of this note claimed execute breakpoints never fire here, and called
CLAUDE.md wrong. **That claim was mine and it was wrong.** Breakpoints work — the address
must be **physical** (`addr & 0x1FFFFFFF`), not KSEG0.

Measured side by side against a PC executing 2,079 times in this movie (`0x8004C834`):

| address | regime | hit_count |
|---|---|---|
| virtual `0x8004c834` | `debugger.resume` | **0** |
| virtual `0x8004c834` | `movie.advanceToFrame` | **0** |
| physical `0x0004c834` | `debugger.resume` | **1** — halts correctly |

The regime is irrelevant; the address form is the whole story. This is the **same rule
this project already documents** for `transferLog.resolve` ("DMA targets are logged
physically; querying KSEG0 silently returns `resolved:false`") — it was in the trace-gotchas
memory the whole time and I did not apply it before declaring a capability broken.

What survives from the wrong version, and is worth keeping: **the failure is silent.** The
call succeeds, the breakpoint reports `enabled: true`, and the capture simply comes back
empty — indistinguishable from "the event never happened". Always assert `hit_count > 0`
before trusting a breakpoint result.

A second, independent trap on top of it: this breakpoint is **sparse**. The damage PC first
fires ~3,900 frames (~65 s) into playback, so a 20-second inner wait times out and looks
exactly like a dead breakpoint. Poll against the overall timeout.

## Still open

- ~~The exact phase-transition condition~~ — **closed**: there is no phase. The restore is a per-hit
  gate on the damage value; see the damage-law section above.
- Which berry type is 127 vs 128 — **blocked**: `addBreakpoint` never fires here (see above). The
  unblock is a behavioural fixture, not more tooling.
- Whether `D17.movie.json`'s freeze at 20 comes from a different hit mix or a different threshold.
- The row's other `next` items (shooter-plant activation, re-engagement, results-screen counters,
  `FUNC_8004ABF4`'s exact branch, the telescope-ordinal mapping) are untouched by this pass.

## Reproduce

```
tools/phase4_d17_defeat_trace.py --port 23701
pytest tests/test_phase4_d17_defeat.py -q
```
