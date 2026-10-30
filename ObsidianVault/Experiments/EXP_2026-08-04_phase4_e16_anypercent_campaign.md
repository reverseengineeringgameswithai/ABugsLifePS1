---
date: 2026-08-04
row: E16_streaming_overlays
dimension: 2
status: NOT FALSIFIED — packet passes, 30 residuals / 0 rejections
fixture_have: ["movies/Phase4/Interpreter/Any% Runs/LEVEL00..LEVEL15", "movies/Phase4/Interpreter/E02_FreshLoad_Clover"]
---

# E16 — the 16-level any% campaign, and the two scope walls it broke

## What was run

The operator recorded **16 any% movies**, LEVEL00_TRAINING … LEVEL15_canyonshowdown:
Interpreter, movie format v4, state-anchored from Flik's Journey, 127,344 frames.
Validated **16/16 usable**, 1,930 events, plus the reference movie
`E02_FreshLoad_Clover` (17/17 with `--merge`).

Each replay runs at **60 Hz** (`debugger.resume` + poll), never
`movie.advanceToFrame` — these recordings are state-anchored and most report
`phase_delay_owed`, and frame-stepping them captured **0 events** on the first
attempt. That is CLAUDE.md's documented trap and it cost a full run.

Per movie: occupancy ≥ 30 slots, a loader clear or bulk zero as **positive
control**, then the falsifier — every event's PC must be in the enumerated set.

## What it found

Not silence. `0x80010BF8` in LEVEL01, and then — only on **LEVEL15, the very last
movie** — `0x80010DA0`.

| PC | levels | events | addresses | type |
|---|---|---|---|---|
| `0x80010BF8` | 7 of 16 | 53 (1, 2, 7, 29, 1, 2, 11) | LEVEL01: `0x800A65C0` | read |
| `0x80010DA0` | LEVEL15 | 51 | 8 — the whole 32-byte `0x58..0x5F` table | read |

`accessLog` reports the PC **after** the access, so these are the loads at
`0x80010BF4` and `0x80010D9C`.

## Why the static work could never have predicted them — two independent reasons

### 1. SCOPE — the function census covered 90.1% of the text

`0x80010BF4` lies in **no function** in `functions_resident.txt`. Measuring the
list for the first time:

```
text segment      : 0x80010000..0x80082800   468,992 bytes
listed functions  : 998 covering 422,632 bytes (90.1%)
uncovered         : 46,360 bytes in 79 gaps (9.9%)
  reached by direct transfer (DROPPED CODE): 46,020 bytes in 14 gaps
  never branched into (data/padding):           340 bytes in 65 gaps
```

⚠️ **Corrected 2026-08-04:** reachability alone overstates this. **20.5% of the
46,020 bytes are zero words**, and `0x8007E8B8` (13,536 B, 58.6% zeros) sits
below `$gp = 0x80081D98` — small data, whose "incoming transfers" decode out of
data. The defensible figure is **32,144 bytes in 12 gaps**, and it surfaced only
because a gate asserted that a recovered function may not begin on a zero word.

The specific cause of the hole is a truncated function:
`0x80010000 724 per_object_mesh_draw_payload_emitter` ends at `0x800102D4`, and
`0x80010C88` is `j 0x800102D4` — the head of the loop containing the access. The
emitter's entire body was in the hole.

→ `tools/text_coverage_audit.c`. Classifies a gap as CODE only when something
branches into it, and follows **direct** transfers only, so `jr`-reached code
scores as unreferenced: the code figure is a **floor**.

Censusing the gaps for region-formed accesses found **12 sites, all needing an
index ≥ 16k** to reach a window, 0 priority. So the gaps add no region-formed
risk — which is what makes the next point the real one.

### 2. FORM — the affine census cannot see register-based access at all

```
0x80010bec  sltu $a3, $t9, $s5     ; range test COMPUTED
0x80010bf0  add  $t9, $t9, $s1     ; base is a REGISTER, not a lui constant
0x80010bf4  lhu  $t9, 0($t9)       ; the access happens REGARDLESS
0x80010bf8  beq  $a3, $zero, ...   ; range test acted on, one instruction too late
```

The base is a register. **Fixing the function list would not have surfaced this.**
Scope and form are independent limits, and this is the one that matters: it is
the same ~20,180-unbounded-value wall that stopped B06/B08, E15 and E16's first
attempt, in a new guise.

## The way through

Pointer-formed access is not enumerable by an affine scan. But it does not need
to be, because of **where pointers come from**: to reach address A deliberately,
code must *materialise* A, and on MIPS that is always a `lui`-based constant.
Materialisation sites are enumerable, and a linear scan is complete over **100%
of the text** — including the code the function list omits.

> **no materialisation site ⇒ anything that reaches that address is INCIDENTAL**

Against E16's three windows:

```
materialisation sites INSIDE a window: 5   (2 bare address-takes, 3 direct accesses)
  ADDR_TAKE 0x8003A39C -> 0x800A65B0   consumed by 0x8003A3BC  (loader clear)
  ADDR_TAKE 0x8003A3A4 -> 0x8009C210   consumed by 0x8003A3B8  (loader clear)
  ACCESS    0x8003C3C0 -> 0x8009C210                            (vram_upload_wait)
  ACCESS    0x8003C5EC -> 0x800A65B0                            (vram_upload_wait)
  ACCESS    0x8003C920 -> 0x8009B5A8                            (level_texture_stage)
near misses within 512 B: 815
```

**Every one already enumerated.** So no code anywhere can deliberately form a
pointer into these windows outside the known set — and the 815 near misses say
what the observed access must be instead: an overrun from a dense neighbourhood.

→ `tools/const_address_materialization.c`. This is **stronger than the campaign**:
static, complete over the scanned text, and a property of the *windows* rather
than of any PC.

## The family, closed

`0x80010D9C` is byte-for-byte identical to `0x80010BF4`, 424 bytes later, in a
duplicated copy of the same loop. Waiting for movies to surface these one at a
time is not a method, so the idiom was enumerated: **22 sites**, all in the
geometry emitters. → `tools/hoisted_load_idiom_scan.c`.

These are **not a game bug** — the result is discarded on exactly the path where
the address is out of range. They **are** a standing hazard for this project's
method: they read whatever global sits at `base+index` and show up in any
`accessLog` watch looking exactly like an unenumerated consumer. Expect them.

## Verdict

**NOT FALSIFIED.** 16 levels, 16 movies, 1,930 events, zero unexplained PCs. The
`bounded_residuals` packet emits **30 entries, 0 rejections** (was 1). The ≥1k
remainder is asserted on the same basis the non-negative-index convention already
used — a magnitude argument plus a named falsifier **now executed**.

**Asserted, not proven.** A replay shows what DID execute; it can never show that
an untaken branch would not have written the slot. Reading runtime silence as
proof is what produced this row's original false closure, so that limit is
written into the residual entry itself, not left in a commit message.

## Mistakes, and what caught each

| Mistake | Caught by |
|---|---|
| Claimed all 5 materialisation sites were "already enumerated PCs" — the 2 address-takes are the *setup*, `0x20` before the store | its own gate, which then forced the tool to report the **consumer** rather than the test to be loosened |
| Probe widened the watch ±256 B for context, saturated the 200k ring on neighbours and **evicted the events it was hunting**; reported a clean-looking `0` | added saturation detection; `PAD` now defaults to 0 |
| Probe shipped **without the positive control** already built into the validator, so that `0` was uninterpretable | rebuilt to report total events, PC histogram, control, playback reach |
| Wrote "1 read of 1 address on 1 frame per level" from the LEVEL01 probe | the campaign: 1–29 per level, 51 on LEVEL15. **One level is not a sample** |
| Running the campaign over the artifact **deleted the validator's own proof** (the known-answer reference row) | the gate asserting it was proven before being trusted → `--merge` |
| Called all 46,020 reached bytes "live code" — a fifth is zero words, and the biggest gap is small data below `$gp` | a gate: a recovered function may not begin on a zero word. **Reachability is necessary, not sufficient** |
| Repair tool's first control shrank a function with **0 sites**, saw no change, and "showed" the census ignored the list | re-running it on the busiest function (495 sites) — the count fell by exactly 495 |
| Two repair versions **fragmented the emitter** into five pieces while the coverage % went up | the emitter-is-whole canary; boundary now comes from the *original* listing |
| Repair "recovered" 10,312 bytes of **data walked as code** — the census lists tables under function names — reading 95.0% instead of 92.8% | asking what the *residual* gaps were: their neighbours are named `..._table_a/b`, which sent me to check what had been extended |
| The first plausibility guard **blacklisted** undefined opcodes and let a 51%-implausible pointer table through | replaced with a **whitelist** of R3000-defined opcodes |

## The gap, repaired and measured (2026-08-04)

`tools/repair_function_coverage.c` recovers dropped code by walking each
function's CFG from its entry — following fall-through, both branch edges, and
the inline `j TARGET ; <delay>` jump tables this compiler emits after a computed
`jr` — bounded by the next entry in the **original** listing.

```
listed    998 functions, 422,632 B (90.1%)
repaired  998 functions, 435,104 B (92.8%)   6 functions regained truncated tails
                                             0 new entries survived the soundness rules
                                             3 extensions REFUSED as data (10,312 B)
                                             0 overlaps
```

⚠️ A first pass read **95.0%**. `functions_resident.txt` lists **data under
function names**, and walking one from its "entry" decodes a table as
instructions: `contact_metadata_table_a` was "extended" by 8,068 bytes of an
ascending lookup table and `contact_action_dispatch` by 2,016 bytes of a
`0x8005Bxxx` pointer table. Guarded by an instruction-plausibility test — the
emitter's real extension scores 0.0% implausible, the data ones 98.3% / 51.4%.

The emitter goes **724 B → 12,552 B**, exactly up to `grass_mound_mesh_builder`,
and all 22 hoisted-load PCs now resolve inside a listed function.

**What it changed downstream — the point of the exercise:**

| census | before | after |
|---|---|---|
| affine region sites | 5,810 (827 bounded) | **5,810 (827 bounded)** — PC sets identical |
| provenance hits (B06 slot) | 14 | **14** |
| provenance unresolved | 10,953 | 11,742 (+789) |
| indirect unresolved | 149 | 150 |

**Zero region-formed accesses in the recovered code, and no new writer to the B06
slot.** That is not a null result — it is the FORM finding from the other side:
this code addresses through registers, so the affine census could never have seen
it however complete the list was. What grows is only the *residual*: the old
figures were not wrong about what they found, they were understated about what
they had not looked at.

E16's packet is unaffected — it is built from the region census, which is
byte-identical. `analysis/phase4_coverage_repair_impact.json`.

⚠️ The repaired list is **not** swapped in as canonical: it moves B06's committed
residual, which another row cites. It ships alongside as
`analysis/functions_resident_repaired.txt`.

## ⚠️ Applies well beyond E16

The 90.1% coverage gap is **not** row-specific. Every static census in this
project ran over the same function list — region provenance, bound recovery,
frontier compilation, the decompilation campaigns' residual counts. Re-run
`tools/text_coverage_audit.c` whenever `functions_resident.txt` changes.

Related: [[EXP_2026-08-04_phase4_e16_registered_chunk_consumers]],
[[EXP_2026-08-04_phase4_e16_resource_lifetime]],
[[SYS_registered_chunk_image_resources]]
