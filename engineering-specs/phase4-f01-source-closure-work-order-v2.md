# Work order v2: region-GATED byte-match of `player_vertical_update` (F01 `source_closure`)

**Date issued:** 2026-08-10 · **Supersedes:**
`engineering-specs/phase4-f01-source-closure-work-order.md` (v1, same target).
**Baseline:** current `master` — record `git rev-parse HEAD` and
`git status --short` (hash + line count) before touching anything; the operator
WIP in that status is **not yours** and must not be committed.
**Executor:** any agent; drafted for Codex hand-off, self-contained.
**Dimension:** F01 DoD `source_closure`.

> ⚠️ **This order deliberately un-parks work the campaign log parked.** On
> 2026-08-10 the banked decision was *"do not send Codex back into this grind
> now"*, and Codex was redirected to `original_interfaces` (delivered:
> 764/764 rows). The operator has since chosen to resume. The park was not
> because the target is intractable — it was because v1's method could not
> convert effort into a measurable, monotone result. **v2 exists to fix the
> method, not to retry the same run harder.** If you find yourself reproducing
> v1's shape — many regions simultaneously partial — stop and report; that is a
> NO-GO, not progress.

---

## 1. Target, and what "done" means

`player_vertical_update` @ `0x80048138`, **6,004 bytes / 1,501 words**,
`end_exclusive 0x800498AC`, retail slice SHA-256
`cab9a859cd6284a25c2ec4d0ba5072a0261b826a0497004e1a528dc0ebc74024`.

The extent is **not in dispute** — `analysis/functions.json` carries
`start 0x80048138 / end 0x800498AC / size 6004`, there is no entry in
`analysis/extent_overrides.json`, and the function does not appear in
`analysis/phase4_extent_audit.json`'s findings. Do not re-litigate it; if you
believe it is wrong, that is a separate finding to report, not to act on.

**Done = every one of the 1,501 words byte-identical to the pristine image at
its retail VA, compiled through the pinned toolchain, with compiled size exactly
6,004 bytes.** Not functionally equivalent. Not close.

## 2. The one rule that changes: the region GATE

v1 said "match region by region." That was measurement guidance, and it did not
bind — all six logical regions came back `near_miss` simultaneously, which is
the signature of whole-function authorship scored afterwards. v2 makes it a
gate.

**The partition is FROZEN and may not be redrawn.** It is the one already
committed in `analysis/phase4_f01_source_closure.json` → `regions`, so it cannot
be gerrymandered after the fact:

| # | region | start | end (excl) | words | v1 equal |
|--:|---|---|---|--:|--:|
| 1 | `controller_history_and_spin` | `0x80048138` | `0x800483B0` | 158 | 11 |
| 2 | `movement_parameters_and_status_input` | `0x800483B0` | `0x80048514` | 89 | 1 |
| 3 | `timers_and_special_vertical_modes` | `0x80048514` | `0x80048B20` | 387 | 10 |
| 4 | `jump_dive_and_landing` | `0x80048B20` | `0x80048E9C` | 223 | 4 |
| 5 | `horizontal_steering_and_projection` | `0x80048E9C` | `0x80049544` | 426 | 20 |
| 6 | `collision_fall_recovery_and_epilogue` | `0x80049544` | `0x800498AC` | 218 | 10 |

**The gate:** regions are worked **in address order**, and

> **region N must reach ZERO differing words before any work is directed at
> region N+1.**

A region is *closed* only when every word in `[start, end)` is byte-identical at
its retail VA. Closure is monotone: once closed, a later edit that reopens it is
a regression to fix immediately, not a trade to accept.

This ordering is not arbitrary. Matching from the top keeps addresses aligned:
once regions 1..N are exact, region N+1 starts at the right VA and its diff is
meaningful. v1 compiled +8 bytes with 2 compiled-only words, so *every* region's
comparison downstream of the first divergence was measuring drift, not content.

**Progress metric — use this and only this:** `K of 6 regions closed; W words
remaining in region K+1`. Do **not** report a whole-function percentage; "56 of
1,503 words (3.7%)" is what a scattered non-result looks like when you flatten
it, and it reads as progress when it is not.

## 3. Phase 0 — two named walls, both of which block region 1

v1 banked three compiler walls. Two of them make region 1 unclosable, so they
are prerequisites, not observations. **Resolve these before writing feature C.**

### 3a. The prologue diverges from the second instruction onward

v1: *"the retained output and retail both select a 0x100-byte frame, but their
callee-save assignment and save order diverge from the second instruction
onward."* Region 1 begins at the prologue. Until the frame layout, the
callee-saved set, and the save order are all identical, **nothing downstream can
align** and every later region's diff is noise.

The retail prologue is readable directly from the image — the first differing
word v1 recorded is `0x8004813C` (compiled `0xAFB400E8` vs retail `0xAFB100DC`),
i.e. a different register saved at a different slot. Recover the retail frame
map (which registers, which offsets, which order, `$ra` slot, frame size)
straight from the bytes, then make the C produce it. Register *allocation* is
downstream of how many callee-saved registers the function body actually needs
and in what order they are first live — this is shaped by the C, not tuned by
hand.

**Do not hand-tune scheduling to force the prologue.** If C cannot produce the
retail prologue, that is a reportable finding with the exact obstruction named.

### 3b. The mixed `$gp`-relative / absolute global addressing

v1: retail uses `$gp`-relative accesses at offsets `0x502`, `0x618`, `0x63C`,
`0x69C`, `0x73C` while other globals in the same function remain absolute
(`lui`/`addiu` pairs), and *"under the frozen `-G0` contract"* the compiler
emits absolute for all of them.

`$gp = 0x80081D98` is a proven constant, so the offsets resolve to five known
addresses. **Already done for you** — there are exactly **17 `$gp`-relative
accesses** in `[0x80048138, 0x800498AC)` over 5 distinct offsets:

| gp offset | address | width | accesses | first / last |
|---|---|---|--:|---|
| `0x502` | `0x8008229A` | halfword | 4 | `0x8004821C` … `0x8004826C` |
| `0x618` | `0x800823B0` | halfword | 6 | `0x80048210` … `0x800482A0` |
| `0x63C` | `0x800823D4` | word | 2 | `0x80049490`, `0x800494A4` |
| `0x69C` | `0x80082434` | word | 2 | `0x80048BB8`, `0x800495E4` |
| `0x73C` | `0x800824D4` | word | 3 | `0x800497A0` … `0x80049844` |

⚡ **Ten of the 17 fall inside region 1** (`0x80048210`–`0x800482A0`). The gate
starts where this wall is densest, so 3b is not optional groundwork — region 1
cannot close until it is solved.

⚡⚡ **The discriminator is NOT object size, so it is not `-G` alone.** In this
very function, `[0x800823A0]` is read as a halfword **absolutely**
(`lui $v0,0x8008` / `lh $v0,0x23a0($v0)` at `0x80049658`/`0x8004965C`) while
`[0x800823B0]` — same width, **16 bytes away** — is `$gp`-relative. Two
same-sized neighbours in one function taking different addressing modes rules
out a pure size threshold and points at **provenance**: which objects this
translation unit *defines* versus merely *references*. Test in this order:

1. **Definition vs `extern` reference.** Globals defined in this TU landing in
   `.sdata`/`.sbss` and getting `$gp`, while `extern` ones from other TUs stay
   absolute. This explains the `0x800823A0` / `0x800823B0` split directly and is
   the cheapest hypothesis to falsify.
2. A different declaration profile for those five (the receipt pins
   `declaration_profile: cleanroom_unprototyped` — that is a knob).
3. A non-zero `-G` for this translation unit — but note it must still reproduce
   the neighbour split above, so `-G` alone is already insufficient.

⚠️ **Do not silently change the pinned compiler contract to make this go away.**
The contract (GCC 2.7.2, `-O2 -G0 -mcpu=3000`, maspsx `--dont-expand-li
--expand-div`, cc1/cpp SHA-256 pins, maspsx commit pin) is in the receipt and is
project-wide. If the evidence says this function needs a different `-G`, that is
a **finding about the original build's per-file flags** — report it with the
evidence, and if it is adopted, it must be adopted explicitly and pinned, not
smuggled in. This question generalises beyond F01, which is part of why it is
worth answering properly.

## 4. Toolchain and machinery — use it, do not rebuild

- **Contract, pinned in `analysis/phase4_f01_source_closure.json` →
  `compiler_contract`:** `gcc2.7.2-psx`, `-O2 -G0`, maspsx
  `--dont-expand-li --expand-div`, `placement_va 0x80048138`, `small_data
  false`, `declaration_profile cleanroom_unprototyped`, with cc1/cpp SHA-256 and
  a maspsx commit pin. Verify the observed hashes still equal the pins and say
  so in the receipt.
- `tools/substrate_common.py` → `compile_at(...)` is the compile-and-place
  harness; compare against `original_exe()` at `va_to_off(va)`.
- `tools/phase4_f01_source_closure.py --check` / `--write` already produces the
  receipt. **Extend it to enforce the gate** (per-region closed/open, first open
  region, words remaining) rather than writing a new tool.
- `tools/dc_permute.py` is the **endgame** tool for a handful of residual words.
  v1 correctly recorded it as inapplicable to a size-mismatched candidate
  (sentinel 9999). It becomes applicable only once size matches and the residual
  is small; using it earlier is a category error.
- `tools/gen_handasm.py` is the fallback where C cannot express the shape.
  ⚠️ Hand-ASM **does not count as `source_closure`** — the dimension asks for C
  through the original toolchain. If a region needs hand-ASM, that region is
  *not closed*; record it as a named C-inexpressible finding.
- `src_re/player_vertical_update_80048138.c` is v1's retained source (SHA-256
  `d6c1f29a7702e3c05e947a1574565e21f756c887f8d0aefb9b269737199d56cf`).
  `src_re/abdomen_bounce_80048138_8004abf4.c` carries a typed `PlayerA05` struct
  (+0x00 xyz, +0x2c v, +0x48 floor_y, +0x7a action_timer, +0x80 air_state, +0x82
  grounded, +0x84 dive_phase, +0x88 animation_selector) — a **semantic reference
  and struct head-start, not a seed to compile.** `src_re/re_types.h` holds
  shared typedefs.
- v1 noted the m2c-normalised seed failed to compile, so authorship fell back to
  hand-written C. Either fix that pipeline or declare hand-authorship up front —
  but under the gate, so it cannot again produce six simultaneously-partial
  regions.

## 5. Reporting discipline

- **Fraction before the adjective, always.** State `K of 6 regions closed` and
  `W of N words remaining in region K+1` before any characterisation.
- **"Near-miss" is reserved** for a residual `dc_permute` can plausibly close:
  compiled size exactly 6,004 **and** total differing words ≤ 16. Anything else
  is a *draft*, reported with its numbers. v1's `NEAR_MISS` label on a 3.7%
  match is the precedent this rule exists to prevent.
- Mark every unretained intermediate `unretained_executor_observation` /
  `supports_current_result: false`, as v1 did correctly.
- Name every universe; `unknown` beats a plausible guess.

## 6. Freeze before outcomes

Commit a **pre-outcome freeze** before inspecting any result: baseline commit,
the `git status --short` hash + line count, the pinned compiler contract with
observed-vs-pin hashes, and the frozen region table from §2. No word counts, no
region statuses, no verdict. Outcomes land in a **later** commit. This ordering
is checked by ancestry, and it has been honoured by all five prior pilots.

## 7. Forbidden paths, and no status movement

- **Do not edit `analysis/mechanics_baseline.yaml`.** Only a fresh detached
  verifier may bank a status change. `source_closure` stays `partial` no matter
  what this order produces; the receipt must carry
  `source_closure_eligible_for_promotion` honestly and a
  `status_statement` saying so.
- Leave the analysis chain untouched: frontier, census, seed, gate and
  typed-state artifacts. v1 respected file-disjointness exactly (`src_re` +
  receipt + tool + test); hold that line.
- Preserve operator WIP — commit only your own files.
- If a tracked tool imports a module, `git add` the module.

## 8. Stopping rule

Stop and report when **any** of these is true:

1. All six regions close. → `source_closure` is ready for a fresh verifier.
2. Region 1 closes but a later region stalls. → **A real, monotone partial:**
   report `K of 6 closed`, the first open region, its remaining word count, and
   the specific obstruction. This is a legitimate and useful result.
3. **Region 1 will not close after Phase 0 is honestly attempted.** → NO-GO.
   Report the two walls' status and what specifically blocked the prologue or
   the `$gp` mix. Do **not** proceed to author regions 2–6 against an unaligned
   base; that is exactly how v1 produced 1,447 differing words.
4. You find yourself with several regions simultaneously partial. → Stop. The
   gate has been violated; report it as such.

A NO-GO here is a genuine outcome and is preferred to a second inflated
near-miss. Say plainly which of the three walls (prologue/callee-save,
`$gp` mix, extent/CFG shape) is the binding one, and whether it is
**technique-shaped** (a better method would close it) or **structure-shaped**
(the approach itself cannot).

## 9. Deliverables

1. `analysis/phase4_f01_source_closure.json` — extended with `region_gate`
   (per-region `closed: bool`, `words_remaining`, `first_open_region`), the
   Phase 0 findings, and observed-vs-pin compiler hashes. Keep the existing
   schema fields; bump `schema`.
2. `src_re/player_vertical_update_80048138.c` — the authored C.
3. `tools/phase4_f01_source_closure.py` — gate enforcement, `--check` clean.
4. `tests/test_phase4_f01_source_closure.py` — a test that **fails** if a region
   is reported closed while any word in it differs, and one that fails if
   `result: NEAR_MISS` is set outside the §5 definition.
5. A campaign-log section in
   `ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md`
   — freeze first, outcomes in a later commit.
