# RETRACTED: "`source_closure` is structurally capped for every overlay-implemented row"

**Date:** 2026-08-11 · **Status:** ⚠️ **RETRACTED THE SAME DAY IT WAS BANKED.** The
original finding is preserved below the correction because the reasoning error is worth
more than the claim was.

---

## The retraction

I claimed, on the strength of `config/segments.yml` holding 938 entries and **zero** in
overlay space, that:

> *"No overlay function has ever been registered as a build unit, so no overlay function
> can be byte-matched, so `source_closure` cannot be met by any row whose mechanism lives
> in an overlay."*

**That is false.** A complete overlay decompilation track exists and has been working:

| | |
|---|---|
| `config/overlays.yml` | the overlay build registry — 20 overlays, region A `0x800B39A0`, region B `0x800B5788` |
| `tools/build_overlay.py` | the overlay build path |
| `src/overlays/` | **16 tracked C files** across LEVEL02/03/04/05/… |
| `analysis/overlay_decomp_progress.json` | **158 overlay code functions, 15 matched (9.49%)**, 12 overlays rebuilt **SHA-1-identical** |

Overlay byte-matching is not impossible. It is **early** — 9.49% — and it is a separate
track from the resident substrate, exactly as `config/overlays.yml`'s own header states
in its first line: *"Overlay decompilation track — SEPARATE from the resident substrate
(config/segments.yml / tools/build_psx_exe.py)."*

## How I got it wrong

I checked one file, found zero, and promoted the absence to a structural impossibility —
**the precise error I had catalogued three times that same day in my own census tooling**
and written into its comments as "a discovery procedure reports what it can see, and its
blind spot is invisible in its own output; check a known-positive before believing a
negative."

I did not check a known-positive. Had I asked "does *any* overlay function have matched
C?" before writing "no overlay function can be byte-matched", one `git ls-files
src/overlays` would have stopped it.

Two aggravating details:

- The file I read has **no reference to the overlay track**; `grep -i overlay
  config/segments.yml` returns nothing. So the blind spot was real and the repo does not
  signpost across it — but that explains the error, it does not excuse the confidence.
- The correction came from an F03 row assessment, i.e. from the work under me rather than
  from my own check. It was reported as an aside: *"the census's triage string 'no
  byte-matched source registered for this row' is understated — it searches only
  `src_re/` and `asm/hand_written/`."*

## What is actually true

- ✅ `config/segments.yml` has 938 resident entries and 0 overlay entries. (True, and
  irrelevant — wrong registry.)
- ✅ Overlay `source_closure` is **early**: 15 of 158 overlay functions matched.
- ✅ F11's `source_closure` 0/12 stands as a *row* measurement — its four governing
  overlay functions are missing from the static index, and its overlay-image
  misresolution (attributing them to `LEVEL03_*`/`LEVEL08_*`/`MEMORY` rather than
  `LEVEL02/LEVEL1.BIN`) is a real defect that would need fixing first.
- ✅ F03 has **1 validated overlay byte-match** (`src/overlays/LEVEL02_LEVEL/
  800b3b70_set_state_60.c`, 20 of 3,772 code bytes), so its row is nonzero where my
  finding said zero was inevitable.
- ❌ **NOT true:** that a cap exists, that it is structural, or that overlay rows cannot
  move this dimension. They can; the work is ordinary decompilation at 9.49% progress.

## Consequence for the census tooling

`tools/phase4_f_row_measured_census.py` searched only `src_re/` and `asm/hand_written/`
for source evidence and only `config/segments.yml` for build units, so it was blind to
`src/overlays/` and `config/overlays.yml`. Fixed in the same commit as this retraction.

**Standing correction for anyone measuring `source_closure`:** there are TWO registries.
Check both, and cite which one you checked.
