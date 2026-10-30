---
kind: experiment
id: EXP_2026-08-03_phase4_c05_three_tokens
status: complete
source_state: original_game
system: [SYS_level_results_screen, SYS_bonus_unlock_challenges]
row: C05_three_tokens
---

# Phase 4 C05: the three success tokens — bit map, three corrections, and the results screen

> **⚠️ Correction 2026-08-04 — I named the wrong function.** This note originally
> called `fcn.80051b84` "the results-screen token renderer" and said the masked
> unlock bit selects "earned-vs-locked presentation … the real icon versus the red
> `?`". Both claims are wrong; see *Correction 3* below. **The bit map itself is
> unchanged and still fully pinned** — what was wrong is where the code runs and
> what the bit does. The sections below are left as written, with the wrong
> sentences struck through, rather than silently rewritten.

## Question

C05's stated next was *"serialize the FUNC_80055478 buffer before/after a 3-token
completion; locate unlock bits."* E14 had already mapped that entire buffer today and C17
decoded the unlock block — so the remaining question was the one **C17 explicitly left
hedged**: which bit is which axis?

## The token renderer, C-pinned

~~`fcn.80051B84` draws the results-screen tokens in three near-identical blocks.~~
**(Wrong — it is an in-world marker stage; see Correction 3.)** Each of the three blocks
loads the token's **source record**, skips it if that word equals `0x80000000` (the
already-documented "consumed" sentinel), passes a sprite id, then reads
`unlock_array[level]` (`0x8009B878`, level index from `0x8008245C` — C17's array) and masks
**one bit**, handing it to `0x80051938`. ~~which selects earned-vs-locked presentation —
the real icon versus the red "?" seen in screenshots.~~ **(Wrong — the bit picks a draw
tint component.)**

`tools/phase4_c05_tokens_static.c` pins 25/25 instruction words (first build):

| Bit | Token | Source | Sprite | Owning row |
|---|---|---|---|---|
| `0x01` | grain reward | `0x80090B80` (`G_REWARD_SNAPSHOT`) | `0x28` | C02 |
| `0x02` | FLIK letters | `0x800B3988` (`G_FLK_SNAPSHOT`) | `0x1F` | C03 |
| `0x04` | **enemies** | `0x80090B68` (all-defeated event obj) | `0x1B` | C04 |

All three source globals are named in *committed* C sources, not inferred here.
`0x01|0x02|0x04 == 7` — exactly the per-level value C17 found unlocks that level's bonus
movie clip. So the row's title is now a fully traced chain: **three independent collectible
systems → three bits → value 7 → FMV unlock → persisted in the save**.

## Correction 1 — my own C04 number was wrong

C04's artifact claimed *"level01.sav … quota=4, matching the live trace exactly."* **It
reads 21.** Independently corroborated by two committed sources that predate my work:
`phase2_lifecycle_oracle.json` records 21 for the same save, and the archived
`Enemy_spawn_architecture` ADD proof-of-concept records "G_ENEMIES_REMAINING went 21→22".

Where the 4 came from: the `flik_to_level01_stall` boot movie stalls at a pre-gameplay
transition and never reaches a fully-populated LEVEL01 pool, so the `0→1→2→3→4` scan I
captured was a partial population — not LEVEL01's roster. Attributing it to `level01.sav`
and calling it a match was the error.

**C04's mechanism is unaffected** and still correct (quota = `player+0x8E`, rebuilt by
`FUNC_80046B20`'s pool scan, incrementing at `0x80046c64`); only the cross-level
illustration numbers were wrong. `level02.sav = 50` was not re-verified and is no longer
asserted. Recorded as a dated correction in both artifacts rather than silently edited.

## Correction 2 — the third results-screen counter is enemies, not seeds

During F06/F15 I labelled the third counter (`/09` on Birdnest, `/16` on Hopper's stage) as
"seed tokens", and C17 inherited that as its guess for the third bit. The bit map proves
the third axis is **enemy elimination**. Supporting datum: the LEVEL06 100% run's own start
state reads enemy quota **9**, and Birdnest's third counter shows **09/09** — alongside the
gold crossed-out-bug icon.

The **bit map is proven**; the counter↔token correspondence is strong inference (icon
imagery + the 9/9 coincidence), since the counter renderer itself wasn't decoded. Flagged
as such rather than asserted.

> **Upgraded to proof 2026-08-04** — see *Item 1*. The results-screen routine's third block
> literally tests the enemy quota `0x800A658E == 0`, and the `/09` denominator is the enemy
> total `0x80082258 = 9`. No longer an inference.

## Correction 3 (2026-08-04) — I named the wrong function

`fcn.80051b84` is **not** the results-screen token renderer. `tools/phase4_c05_marker_stage.c`
pins 47/47 words establishing what it really is:

- its **only** caller is the per-frame gameplay state machine `0x8004ECD4`;
- its first half is gated on live player fields (`0x800A659E == 0x0B`, `0x800A657C == 0`)
  and draws at **Flik's live world position** `0x800A6500/04/08`;
- the callee `0x80051938` (falling through into `0x80051940`) reads `record[0]/[4]/[8]` as
  world X/Y/Z, takes the squared distance to the eye position `0x8009EC50/54/58` with each
  delta `>>8`, and **returns if it exceeds `0x0004C8FF`** — a distance cull;
- then `beqz a2`: bit **set** → `a2 = 0x60`, bit **clear** → `a2 = 0`, and `v0 = 0x60 - a2`.
  The pair `(0xC0, v0)` is `(0xC0,0x00)` set and `(0xC0,0x60)` clear — a **colour/tint
  component pair** handed to the same sprite draw `0x80022FE0` the first half uses, at
  `record Y - 0x1A00` (hoisted above the object);
- the record is registered into a marker list `0x800B1B58 + i*16`, count `0x800824CA`, cap `0x2F`.

So this is the **in-world floating marker above each reward token**, tinted by whether that
axis is already earned. There is no `?` sprite in this path at all.

**Unchanged:** the bit→record→sprite map, the array, the index, the sentinel, and
`0x01|0x02|0x04 == 7`. C17's "which bit is which axis" hedge is still closed and Correction 2
still stands — each axis's own reward record is passed with exactly one bit, a direct pinned
association that does not depend on venue.

**How it was caught:** while scoping follow-up work I listed neighbouring functions and saw
the census name `effect_render_stage` for `0x80051b84`, sitting between
`effect_drop_spawn_stage` and the harvester update. That prompted a caller check and a read
of the callee.

**Lesson:** I inferred the *venue* from a visual match — three code blocks against three
on-screen icons I'd seen in C04's screenshots — and never read the caller or the callee.
Instruction pins prove what an instruction **is**, not what the surrounding function is
**for**; a tool that verifies 25/25 words can still sit under a wrong narrative. The two
cheap guards that would have caught it: check the caller set, and read the callee, before
naming a function.

## Item 1 (2026-08-04) — the real results screen, and the bit setter

Static first: the resident listings contain **no** results-screen renderer. Every resident
reference to the unlock array is accounted for — `FUNC_800502C4` (C17's FMV check),
`FUNC_80055478` (serializer), `FUNC_80055538` (the 19-byte save **deserializer** restore
loop, not a completion setter), `FUNC_8004FCA0` `scene_flow_dispatcher` (publishes
`unlock_array[level]` into `0x8008228C` = `gp+0x4F4`, the pre-completion snapshot
`FUNC_800502C4` later compares against), and the in-world marker stage. So it had to be
overlay code.

Live, on the existing LEVEL06 100% movie: an accessLog **read** watch on the whole array,
armed at movie frame 8400, using the marker stage's known PCs as a discriminator. 133 events
— 130 from the known marker PC, and exactly **three new PCs** (`0x800B7E78`, `0x800B7ED8`,
`0x800B7F38`), each firing once, all reading index 6, all in one frame, spaced `0x60`.

That is [[FUNC_800B7DA0_results_screen_evaluate_and_draw]] — and it does more than render:

| Axis | Source | Condition | Bit | Earned tile |
|---|---|---|---|---|
| grain | `0x800A65A1` (clamped to 50) | `== 50` | `0x01` | 59 |
| FLIK | `0x800A65A2` mask | `== 0x0F` | `0x02` | 58 |
| enemies | `0x800A658E` quota | `== 0` | `0x04` | 57 |

Each block sets its bit if clear (slot `1` = newly earned) or records slot `2` (earned
earlier), and sets `0x800823E4 = 1`. **All three setters are here** — which is exactly why
C17 saw the byte go `0 → 7` atomically, and it corrects the assumption that the setters sat
in C02/C03/C04's separate paths.

**Correction 2 is now proof.** The third axis is enemies *by the condition itself*, not by
icon inference — and it agrees with the marker stage's independent bit map. Two unrelated
code paths, same assignment.

Presentation: below the row's animated total → locked tile **52**, the red `?`, at `x=248`;
at the total → the earned tile at `x=240`, full bright via `hud_draw_sprite_tile`
`0x80025F54` when newly earned, or **dimmed** via `0x80026858` with `(128,128,128)` when
earned on a previous visit. That is the earned-vs-locked selection Correction 3 stripped from
the marker stage.

Live cross-check at the captured frame: grain `50`, mask `0x0F`, quota `0`, enemy **total**
`0x80082258 = 9`, `array[6] = 7`, flag `= 1`. The screenshot shows `50/50` and `4/4` with
earned tokens and `00/09` still counting up behind a red `?` — the counter gate, caught mid
animation.

`tools/phase4_c05_results_overlay_locate.c` scans all 326 retail files: **exactly one**,
`BITS/MEMORY.BIN`, contains the test-and-set pattern. It loads **verbatim** at `0x800B5788`
(the file's first `0x8112` bytes are byte-identical to RAM during the screen), and the tool
pins **30/30** words at derived file offsets — so this is reproducible with no emulator.

**Provenance caveat, and the C11 lesson again.** The overlay identity was *already committed*:
`src_re/level_complete_results_800b7da0.c` has recorded base `0x800B5788` and bounds
`0x800B7DA0..0x800B8788` since 2026-07-07, and its medal-reveal notes independently
corroborate both the counter gate and the dimmed already-earned token. Its Canon page was
auto-generated under the name **`popcount8`** — the generator took the first `static` helper
in the file's modding pseudocode — which is why an address search never surfaced it. Renamed,
alias kept, both Canon indexes retargeted. **Grep committed `src_re/` for the address before
assuming a finding is new**, and treat a mis-named Canon page as evidence that is invisible to
the very search that would find it.

Unlike Correction 3's mistake, the caller (`0x800B9754`, via `xrefsTo`) and the callees
(`hud_draw_sprite_tile`, `0x80026858`) were both checked *before* naming.

## Item 1 follow-up (2026-08-04) — the counter animation, decoded offline

The last undecoded piece of the screen, closed **without the emulator**: with the load base
pinned, `tools/phase4_c05_counter_animation.c` verifies **46/46** instruction words straight
against the pristine `BITS/MEMORY.BIN`.

The whole screen is **one per-frame loop** — `0x800B7F98` (`wait_for_frame_sync_flag`) …
`0x800B8740` (`bne s3, zero`). `s3` is the screen countdown, seeded to **800**.

Three numerators animate up, with an identical law:

```
if (numerator < target && fp == 0) { numerator++; sfx(14); }
```

`fp` toggles every frame, so **the counters tick at 30 Hz, one unit every other frame**.
`s1 = (s1+1) & 0xF` on the `fp==0` frames is the spinning-icon phase.

| Row | Numerator | Target |
|---|---|---|
| grain | `s4` | `[0x800A65A1]` |
| FLIK | `s6` | `popcount_table[0x800BE444 + mask]` |
| enemies | `s5` | `[0x80082258] − [0x800A658E]` = total − remaining = **defeated** |

Digits go through `hud_draw_sprite_tile(x, y, tile, glyph)` — tile **56** is the digit font and
the **fourth** argument is the glyph index, with **10** = `/`. Tens come from the classic
`0x66666667` magic-multiply divide-by-10.

**The grain denominator is universal.** Row 1 emits `[tens][units] '/' 5 0` where the `5` and
`0` are *literal glyph indices* in shared overlay code — so every level requires 50 grain. The
only per-level number on the screen is the enemy total. That settles the question left open
earlier today.

**The "skip" button is a fast-forward, not a skip.** A *fresh* press on the face-button mask
`0xF000` (`[0x80082412]` set, `[0x800822E4]` clear — both zeroed at entry, i.e. an edge
detector), and only inside the window `25 ≤ s3 < 740`:

- all three numerators already at target and the one-shot flag clear → `s3 = 24`, end soon;
- otherwise → `s3 = 54` **and the numerators snap to their targets**.

That also explains how a token can pop in immediately after a press: tokens are gated on the
numerator reaching the total, and the snap satisfies that gate.

The table at `0x800BE444` is a 16-entry **popcount** table (`0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4`;
the next byte is 252, so only the 4-bit domain is meaningful) — matching the committed source's
own "only meaningful for reachable 4-bit masks" note, and, with some irony, exactly what the
auto-generated `popcount8` page name was describing. ⚠️ It sits in `MEMORY.BIN`'s
runtime-mutable tail, so those are the **disc** bytes; a live re-read would be needed to prove
the loaded copy isn't rewritten. Flagged, not asserted.

## Items 2 and 3 (2026-08-04) — one confirmed, one honestly inconclusive

**Item 2 — the dimmed already-earned token: CONFIRMED.** The `slot==2` path had never
been observed executing, because every fixture is a first-time completion. Forced it with a
RAM poke instead of asking for a new recording: on the existing LEVEL06 movie, set
`unlock_array[6] = 0x07` at movie frame 8400 — *before* the evaluator runs — then captured the
identical emulator frame as the control.

- **State:** `array[6]` stayed `0x07` and the newly-earned flag `0x800823E4` stayed **0**
  (control: `1`), so no block took the newly-earned branch — all three slots were `2`.
- **Pixels:** 42,185 changed, bbox `x[602..760] y[71..422]` — exactly the token column, rows 1
  and 2 only. Grain `94.6 → 72.2`, FLIK `111.4 → 87.7`. The tokens render **translucent**;
  grass shows through them.
- **Negative control, built in:** row 3 was still the red `?` (counter not yet at total) and
  changed by **exactly 0** pixels, and nothing outside the token column moved.

That also answers the old "replay once a level already reads 7" question at the presentation
level: the screen still runs, the counters still animate, the tokens come up dimmed.

**Item 3 — the marker's two states: INCONCLUSIVE, and a retraction.** ⚠️ Correction 3 said
the marker bit picks "a **colour/tint** component pair". The *values* are pinned and right;
calling them a tint was an inference stated as fact. Following the callee through:
`effect_mesh_transform` `0x80022FE0` stores them into a **28-byte effect draw record** at
`0x8009E8E0` (`+0x00` = a render kind indexing the already-Canon pickup descriptor table
`0x80096B98`; `+0x02` = the bit-dependent value). **No resident reader of `+0x02` was found.**

The empirical A/B was set up correctly — an `execTrace` watch on `0x800519F4`, the draw call
*after* the distance cull, so a hit proves a marker is genuinely drawing; it landed on movie
frame 5745. But two of the three captures came back **pixel-identical**, meaning no newly
rendered frame was presented between them, so motion and the poke can't be separated. Reported
inconclusive rather than eyeballed. Settling it needs either the `+0x02` consumer or an A/B
from a save state anchored *on* a marker-drawing frame. The results screen's confirmed dimming
runs through a different function (`0x80026858`) and does not transfer.

## Item 3 resolved (2026-08-04) — it's semi-transparency, not a tint

The inconclusive A/B above turned out to be unnecessary. Rather than grep for another
displacement, I bounded the search by an **invariant**: who touches the record *count* at
`0x80082374`. Exactly four functions do — the two producers, a reset, and **one** consumer,
`0x80023ABC`. That makes the consumer set provable instead of guessed.

Why the earlier grep missed it: the record begins at **`0x8009E8D0`**, not `0x8009E8E0`. The
producers address it as `0x800A0000-0x1720 + i*28` (field looks like `+0x02`); the consumer
sets `t6 = 0x800A0000-0x1730` and walks `t0 = t6 + 0x12`, stride 28. Same address, different
base — so searching for `-0x171e` found nothing and I wrongly concluded no reader existed.

```
lh   v1, (t0)          ; the bit-dependent value
li   v0, 0x60
beq  v1, v0, skip      ; == 0x60 -> leave it alone
prim = [0x8008249C]
prim[7] |= 0x02        ; semi-transparency
skip:
```

The same record's `+0x08/+0x09/+0x0A` become `prim[4]/[5]/[6]`. A PS1 packet's first word
after the tag is `0xCC_BBGGRR`, so those are R, G, B and `prim[7]` is the **command byte** —
bit `0x02` is the ABE (semi-transparency) flag.

| Unlock bit | Value | Test | Marker |
|---|---|---|---|
| clear (not yet earned) | `0x60` | `== 0x60` | **opaque** |
| set (already earned) | `0x00` | `!= 0x60` | **semi-transparent** |

`tools/phase4_c05_marker_semitransparency.c` pins all 21 words, first build, offline.

**The cross-check that makes this satisfying:** the results screen says "already earned" by
modulating the token's colour through `0x80026858`; the in-world marker says it by setting the
GPU's ABE bit. Two unrelated code paths, same visual language, both keyed off the same bit.

**Lesson.** Four passes on one field — wrong venue, wrong semantic, "unknown", resolved. What
finally worked was bounding the consumer set by an invariant rather than guessing an address
form. **When a displacement grep comes back empty, suspect the base, not the absence of a
reader.**

## Last loose end (2026-08-04) — the newly-earned flag is the save trigger

All three evaluator blocks set `0x800823E4` when an axis is earned for the first time, and I
had never asked who reads it. **No resident reader exists.** Scanning the whole overlay image
for load/store opcodes carrying the immediate `0x23E4` — so the reader set is complete, not
sampled — finds exactly one load, at `0x800B8AD0`, in a routine starting at `0x800B8ACC`.

That routine is the **save path**:

```
v0 = [0x800823E4]
if (v0 == 0) goto done            ; nothing new -> never saves
v0 = 0x800B7BA4()                 ; gate routine
[0x800823E4] = v0
if (v0 == 0) goto clear
s0 = 0x8009EC68                   ; THE SAVE BUFFER
0x80055478(s0)                    ; serialize_savegame_buffer   (Canon)
if (0x800BB6F4() != 0)            ; the card write
    [0x8008245C] = -2             ; failure sentinel into the level index
0x80055538(s0)                    ; the save deserializer       (Canon)
clear: [0x800823E4] = 0
done:
```

Two things fall out. The **save buffer is `0x8009EC68`**, passed to both the serializer and the
deserializer — a concrete new link from this screen to E14's 348-byte save schema. And the
replay case closes from the persistence side: a pure replay sets no bits, so every slot is `2`,
so the flag is never set, so **the save block is skipped entirely**. With the dimmed-token
result above, replay is now described at both the presentation and persistence levels.

⚠️ **My guess was wrong.** I had hypothesised this flag gated the "Congratulations! Bonus Movie
Clip Earned" screen, and said explicitly it was untested. It gates the save. Worth recording
that labelling it as a hypothesis is what made being wrong cheap — asserted, it would have been
a fourth correction on this row.

20/20 pins, first build, offline: `tools/phase4_c05_newly_earned_flag.c`.

## Still open

C05's own named scope has nothing open. The residuals belong elsewhere: the gate routine
`0x800B7BA4` and the card writer `0x800BB6F4` (frontend/save, E14 territory), the caller
`0x800B9754` and the rest of `BITS/MEMORY.BIN` (an overlay-mapping job, not this row), and a
**live** re-read of the `0x800BE444` popcount table, whose disc bytes are verified but which
sits in the runtime-mutable tail.

## Evidence

`analysis/phase4_c05_three_tokens.json`; `tools/phase4_c05_marker_stage.c` (47/47, the
corrected reading); `tools/phase4_c05_tokens_static.c` (25/25, the original bit-map pins —
its header comment carries the wrong framing and is annotated); corrections applied to
`analysis/phase4_c04_enemy_token.json` and `analysis/phase4_c17_movie_viewer.json`.

## 2026-08-04 bounded-exhaustion audit

**Disposition:** confirmed and bounded-exhausted for C05. There is no remaining question
inside the row's three-success-token scope, and no Interpreter movie is required.

Capsule preflight found no C05/three-success-token entry in
`analysis/phase4_trace_capsule_set.json`. That absence does not require a live replay here:
the pristine executable and results-overlay instruction domains contain the complete
producer-to-consumer contract, while the row's existing live observations already cover
the presentation behavior.

Six independent C verifiers were rebuilt with
`cc -std=c11 -O2 -Wall -Wextra -Werror` and run against the pristine inputs. They passed
25/25 token-map pins, 47/47 marker-producer pins, 21/21 final semi-transparency pins,
30/30 results-overlay pins plus a unique overlay match, 46/46 counter-animation pins, and
20/20 newly-earned/save-trigger pins. Their output SHA-256 values are, respectively:

- `4ae0dbc4b845a653d6193c0c51aef4406c3eaf77d9b46fd08a9baa24325a6ce6`
- `72ca2ba06ebab90eb3e5eafabed4c25fb9f47b5d531ad4961de568f5daaed470`
- `8d4a990c6c2af015db5f1a89898fc2bec2bcb2893a280acf3d34b5f63cace4dc`
- `e52412ddac71043bb25e16d603b2451c032a975c7326cc54f0824acccf911f70`
- `033a176101c8af71dc95829bd2c1d930751722de11e18d6759054c29f21c3191`
- `c8fe2307e5e8fee8223850867f6a0e0c0beb47b5b06229a3aa847cd5bee49034`

A new combined oracle, `tools/phase4_c05_closure_oracle.c`, closes the cross-file chain in
one run. It pins marker and results instructions, proves the token union
`0x01 | 0x02 | 0x04 = 0x07`, finds two unlock-array references and two immediate-7 uses in
the movie consumer, one unlock-array reference in each serializer direction, exactly one
overlay load of the newly-earned flag, and exactly one serializer plus one deserializer
call in its save routine. Result: `C05_CLOSURE PASS`.

Combined-oracle source SHA-256:
`6bd466ae641bcc027e2a7c18e7f1e4b56633ae0234e6691cd32a145aea24ef61`.
Binary SHA-256:
`fca224094f98b7a516dd1e1aac17f1043ea4900e3d9c8c6695c00dd046ce8b13`.
Output SHA-256:
`828d0f3df62222475f59a7cae108da14a1b027b4e776b344c9778ac3a0a1ebf5`.
The pinned inputs were `SCUS_942.88`
(`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`)
and `BITS/MEMORY.BIN`
(`e3f8697223e3a1a1bdfa385d417ce87928eaff40ea3e26d1a64f6f25234d8e37`).

The only residuals are outside C05: the results gate/card writer belongs to E14, broader
overlay-loader attribution is separate loader scope, and a live reread of the mutable-tail
popcount table could only refine counter presentation. None can change the three source
conditions, their bit setters, persistence, or the full-mask movie threshold.
