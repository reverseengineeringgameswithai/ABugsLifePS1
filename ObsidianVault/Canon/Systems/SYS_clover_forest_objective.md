---
kind: system
id: SYS_clover_forest_objective
name: Clover Forest (stage 10 / scene 7) -- the five mechanical bits
status: live_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-08-05_phase4_f01_objective_lifecycle
  - analysis/phase4_f10_clover_objective.json
  - analysis/phase4_f10_clover_pieces_live.json
src_paths:
  - tools/phase4_f10_clover_objective.c
  - tools/phase4_f10_clover_trace.py
  - tools/phase4_f10_clover_pieces_live.py
  - tools/phase4_f10_bit04_meaning.c
  - tests/test_phase4_f10_clover.py
patch_policy: safe_to_read
---

# SYS_clover_forest_objective

The objective, HUD and exit of Clover Forest. Row `F10_clover_forest` was previously
untouched — no experiment note, no artifact, no commit, no vault mention — and read
only "Piece/objective and completion state".

## The stage is scene 7, derived not assumed

The row is "Stage 10". The campaign progression table `0x80077FA0` maps ordinal →
scene id, and `[10] == 7`. The Phase-3 scene-asset graph independently labels scene 7
`stage10_clover_forest`, disc dir `level07`, bin `LEVEL.BIN`. The mapping is
cross-checked against two rows already solved: `[11] == 12` (the scene F11's work ran
in) and `[3] == 2` (LEVEL02, the F03 Thumper overlay).

## The objective is a BITMASK, not a counter

`0x800B5774` holds one bit per mechanical bit; the stage exits when it reads `0x1F`.

That distinction is not cosmetic. A mask cannot be advanced twice by the same piece,
so "five pieces" is enforced by **identity** rather than by counting — the same shape
as Bonus 2's five plant-identity slots, and unlike Bonus 1's and Bonus 3's streak
counters. It also makes collection **order-independent**, which the verified run
demonstrates directly.

**Collecting a piece** (`0x800B41EC..0x800B4244`):

```
if (Σ((flik - piece) >> 8)² >= 1600)   skip     ; 0x800B41EC
if ([0x800A6590] & 0x04)               skip     ; 0x800B4204 -- gameplay suspended
play_sound(-13)
[0x800B5774] |= piece_bit                       ; 0x800B422C / 0x800B4244
[0x800B577C] -= 1                               ; 0x800B4230 / 0x800B4238
```

The proximity test is the **same shifted-squared-distance idiom** the bonus stage's
goal token uses ([[SYS_bonus_stage]]) — so `dist² < 1600` on `>>8` coordinates is an
engine convention, not a bonus-stage quirk.

**Completion** (`0x800B4484..0x800B44C4`): mask `== 0x1F` and the transition latch
still `0` → `[0x800823A0] := 1`, `[0x80082470] := 120`, and a sound call. ⚠️ The fade
length is **per-site**: 120 here, 30 for Bonus 1 and Bonus 3, 60 for Bonus 2.

## Resolved direct-reference census, scoped per image

`0x800B5774` is **overlay-local** — it lives in the shared region-A swap buffer, not
in resident memory. Closing its domain "over all images" would be meaningless, since
every overlay reuses that RAM for its own state. The general effective-address scans
currently resolve:

- **In LEVEL07/LEVEL.BIN**: four direct references, two of them stores — one init
  (`0x800B3E9C`) and one collect (`0x800B4244`) — plus 180 unresolved-base memory
  accesses.
- **In the resident EXE**: five resolved direct references, **all reads, no writes**,
  plus 12,956 unresolved-base accesses and 149 unresolved indirect calls.
- **In every other scanned overlay**: no resolved direct reference. Across all
  overlays the scanner retains 4,967 unresolved-base memory accesses.

**Correction history (2026-08-04 audit):** the previous “Domain closure” heading and
“No other overlay references that VA” sentence were too broad. The scanner tracks
fixed-form effective addresses; it does not resolve pointer-derived accesses. The
direct PC sets above remain pinned, while the residual prevents closure.

## The HUD is resident code reading overlay memory

The five resident reads are a HUD. `0x80053268` loads the scene id, `0x8005326C`
compares it against **7**, and `0x80053270` skips everything otherwise — so a
resident function hard-codes an overlay-local address and stays valid only because it
is scene-gated. Worth knowing before anyone edits region A.

It reads the mask once per bit (`0x800532E0`, `0x80053308`, `0x80053334`,
`0x80053360`, `0x8005338C`, testing `0x01/0x02/0x04/0x08/0x10` in order) and computes
the icon id as `base + 9` when the bit is set, `base` when clear — i.e. five icons
that light up as pieces are collected. `0x800B577C` is read once more at `0x800533B8`,
a separate readout: it is **not** redundant with the mask.

## The five pieces

The collect block receives the bit in a register, so *which piece is which bit* is a
property of the **call sites**, not of the block. There are exactly five, each passing
a distinct bit and its own record pointer:

| bit | record | call site |
|---|---|---|
| `0x01` | `0x800B56D8` | `0x800B43AC` |
| `0x02` | `0x800B56F0` | `0x800B43E0` |
| `0x04` | `0x800B5708` | `0x800B4414` |
| `0x08` | `0x800B5720` | `0x800B4448` |
| `0x10` | `0x800B5738` | `0x800B4478` |

Records are a uniform **0x18 stride**, and their **first three words are the piece's
world position** — the proximity test subtracts `record+0x00/+0x04/+0x08` from Flik's
`0x800A6500/04/08` (`0x800B4190..0x800B41CC`). Each call also passes its own
constants (`a1` = 55/56/57/58/58, `a3` = 63/63/47/63/63), which are presentation
parameters and are not named here.

⚠️ The offset of the `a2` bit-load before each call **varies** (`0x10` at one site,
`0x14` at the others). The tool searches a window for it; an earlier revision assumed
a fixed distance, which matched at one site and failed at the rest — the pin caught
it before it reached this page.

## Piece positions: the X field doubles as a tombstone

The caller reads `record+0x00` and compares it against `0x80000000` before calling
(`0x800B4388`/`0x800B4390`): a piece whose X reads that sentinel is already collected
and is skipped. Init sets the first record's X to `0x8B41` (35649), a plausible
coordinate — so the same word is the piece's X *and* its collected marker.

Confirmed live, and by an unusual route. At the mask store the breakpoint reads the
record's X as the tombstone, which makes the shifted squared distance to Flik
`(66806 − (−2147483648)) >> 8` squared ≈ **7.037e13** — and the observed value was
**7.035e13**. The absurd distance *is* the confirmation.

## `0x800A6590 & 0x04` is a GAMEPLAY-SUSPENDED flag

Named on 2026-08-04 from a complete reader/setter census
(`tools/phase4_f10_bit04_meaning.c`).

⚠️ **Correction history.** An earlier revision of this page named this bit *"the
player is dying"*, from a single setter found by an ad-hoc two-instruction pattern
match. A live `0→1` edge trace refuted it and the naming was retracted. That reading
is **wrong** and must not be restored.

**Why readers, not setters.** Chasing one setter is what produced the wrong answer:
`0x8004A8E0` sits in the death path, which made "dying" look obvious — and it is one
of **four** setters, not the one that fires. A flag's meaning is constrained far
better by everything that *tests* it.

| | |
|---|---|
| **Set by** | `resident_level_transition_initiator` ×2 (one in the death block), `enemy_ai_dispatcher` (under the cinematic-camera flags `0x80090BEE & 0x02`), `gameplay_frame_render` |
| **Tested by** | `gameplay_state_machine`, `contact_pickup_sfx`, `ambient_sfx_sequence_update`, `sfx_nearest_pickup_f_glue`, `actor_skinned_update` — and F10's piece collection |

**The branch sense is uniform, and that is the whole argument.** All five resident
readers are `bne` with a **forward** target: each one *skips its own work* while the
bit is set. If some acted when set and others when clear it would be a mode selector
and no single reading would fit; they do not.

So every setter is a moment the game takes control away — death, scene transition,
cinematic — and every reader suppresses ordinary per-frame work. **Bit `0x04` means
gameplay is suspended.** F10 refusing to collect a piece while it is set is one
instance of that general rule, not a stage-specific quirk.

⚠️ Deliberately *not* narrowed to "cutscene" or "death": those are two of the four
setting situations, and narrowing to either is precisely the error that was retracted.

## Verified

46 static pins (`tools/phase4_f10_clover_objective.c`) plus 5 more
(`tools/phase4_f10_bit04_meaning.c`), both `-Werror`, and two live passes over the
operator's Interpreter Any% run `LEVEL10_cloverforest.movie.json` — a write watch and
a breakpoint pass.

| movie frame | event | mask |
|---|---|---|
| 770 | init | `0x00`, parallel word `5` |
| 4031 | bit `0x10` | `0x10` |
| 5064 | bit `0x04` | `0x14` |
| 7480 | bit `0x08` | `0x1C` |
| 8333 | bit `0x02` | `0x1E` |
| 10461 | bit `0x01` | `0x1F` → latch `1` at `0x800B44B0` |

**The bits were set out of order** — `0x10` first, `0x01` last. That is the
observation that separates a mask from a counter: in a linear run the two are
indistinguishable, and this run happens not to be linear. The parallel word ran
`5 → 4 → 3 → 2 → 1 → 0` in lockstep, confirming both its role and that there are
exactly five pieces.

The breakpoint pass confirmed the bit↔record mapping on every valid hit (`0x10`→index
4, `0x04`→index 2, `0x08`→index 3). ⚠️ It also needed a scene gate: an execute
breakpoint inside the shared region-A window fires for **whatever overlay is
resident**, and an ungated first run captured another level's code at the same
physical address.

## Not established

The stage's own hazards and route — level description rather than mechanism. The
per-piece presentation constants `a1` and `a3` are unnamed.
