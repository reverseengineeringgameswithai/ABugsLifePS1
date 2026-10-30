# Finding: overlay-space addresses are keyed WITHOUT image identity, so they collide

**Date:** 2026-08-11 · **Status:** finding, offline, verified structurally and corroborated
by three independent row assessments. Promotes nothing, changes no status.

> ✅ **REPAIRED the same day — see `phase4-overlay-keying-repair.md`.** The central claim
> held and the repair is applied. Two numbers below are superseded by measurement:
>
> - **"255 records ... schema is `{address, semantic_ids, canon}` — no image field"**
>   conflated two record lanes and used a window wider than overlay space. Measured:
>   **229 keyed occurrences over 161 distinct addresses ≥ `0x800B0000`**, of which **138
>   are inside the overlay window** and 23 are ordinary resident RAM correctly keyed by
>   address alone. The no-image-field claim is true of the **62 `state[]` occurrences**;
>   the 133 `functions[]` occurrences did carry an image tag — it was simply *arbitrary*.
> - **"a count of how many records are wrong ... is unmeasured"** — now measured: of 135
>   overlay-window addresses, **117 (86.7 %) were resolved arbitrarily or not at all**,
>   because the resolver binary-searched a list of fully overlapping intervals.
>
> The ordering advice at the end of this document ("repair the keying first") was
> followed, and that gate is now clear.

⚠️ Written with deliberate care: a systemic claim I banked earlier today
(`phase4-overlay-source-closure-cap.md`) was retracted for asserting an impossibility
after checking one file. Every claim below states what was checked.

---

## The finding

**Every per-level overlay is loaded at the same virtual address.** `config/overlays.yml`
declares `region_a: 0x800b39a0` for all per-level `LEVEL*.BIN` swap buffers and
`region_b: 0x800b5788` for `MEMORY.BIN`. Twelve overlays are declared; twenty are
censused.

**The derived knowledge bases key overlay addresses globally, with no image field.**
Verified: `analysis/phase3_ownership_graph.json` holds **255 records** naming
overlay-space addresses, and their schema is `{address, semantic_ids, canon}` — no
`image`, `blob` or `overlay` key exists on the record.

An overlay VA therefore does not identify code. `0x800B3DB0` is a different instruction
in every loaded overlay, and any structure that stores only the address must pick one
owner arbitrarily — or silently merge them.

## Three independent confirmations, from rows that never spoke to each other

| row | what it found |
|---|---|
| **F09 bug bar** | counter writer `0x800B3DB0` names a **real instruction in 18 of 20** censused overlay images. The ownership graph picks `LEVEL03_LEVEL1`/`LEVEL03_LEVEL`; a compiled-C probe over all 21 pinned images (`tools/phase4_f09_overlay_pin.c`) shows **exactly one** image holds all three fight-lane encodings once each with a consistent base — `OVL/LEVEL04_LEVEL1.BIN @ 0x800B39A0`, matching D18's own pin. |
| **F11 the tree** | its four governing overlay functions are resolved against `LEVEL03_LEVEL`, `LEVEL03_LEVEL1`, `LEVEL08_LEVEL1`, `MEMORY` — a naming the row's own binding falsified with a **100.0% code-window match** to `LEVEL02/LEVEL1.BIN`. Consequence: those functions are `missing` from the static index and its `source_closure` measures 0/12. |
| **F09 + F11** | both hit `0x800B4A3C`, which `semantic_state.yaml` registers to the **training** overlay (`original.training_step`, declared range 0..13). F11 measured 0..320 over 1,896 writes at that address in a different blob; F09 found it is the only registry entry inside the Bug Bar overlay's load window. |

That the same VA misfires on two unrelated rows, and that a byte-level probe disagrees
with the graph on a third, is the signature of address-keying rather than of three local
mistakes.

## Why this is worth fixing before more measurement

- It **understates** rows: F11's `source_closure` reads 0/12 because correct functions
  are indexed under the wrong image.
- It **corrupts typed_state**: a field's declared domain is inherited from whichever
  overlay claimed the VA first, so measured values legitimately fall outside it.
- It **cannot be detected from inside a row.** Every affected row sees a plausible owner
  and no error. Only a cross-image byte probe, or two rows comparing notes, exposes it.

## The fix, and the key that already exists

The missing datum is image identity, and it is already pinned:
`analysis/phase4_d3_contract.json:inputs.image_identities` carries **21 images** with
`path` + `file_va_base` + verified sha256. Overlay-space records need
`(image, address)` as their key rather than `address` alone.

⚠️ **Order matters.** Registering overlay build units (the `config/overlays.yml` track,
currently 15 of 158 functions matched) on top of the *current* resolution would encode
the misattribution into the build system. Repair the keying first.

## Scope

- ✅ Verified here: the shared load bases; 255 overlay-address records with no image
  field in the ownership graph.
- ✅ Reported by row assessments: the F09 probe result, F11's 100% code-window match,
  the `0x800B4A3C` collision on two rows.
- ❌ NOT claimed: a count of how many records are wrong. The 255 records are *at risk*
  by construction; how many are actually misattributed is unmeasured, and measuring it
  is the natural next step — a cross-image byte probe over all overlay-space addresses.
- ❌ NOT claimed: that any row's *behavioural* conclusions are wrong. The runtime
  evidence stands; what is misattributed is which file the code lives in.
