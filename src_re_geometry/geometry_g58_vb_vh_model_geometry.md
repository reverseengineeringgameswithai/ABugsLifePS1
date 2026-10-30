# G58 — The "invisible" LEVEL01 props are already-imported fcn.80010000 decor (they rendered grey)

Status: **investigated + CORRECTED (2026-06-24)**, isolated DuckStation, pristine v1.0, LEVEL01. Triggered by
operator save states of objects "not visible in the level editor" (`big_berry_thing`, `thornplant`, `rock`,
`fence`, `on_swing`/`in_front_of_swing`, `weird_structure`).

## TWO WRONG LEADS RETRACTED (recorded so they aren't repeated)
1. **`.VB`/`.VH` are NOT model geometry — they are PlayStation VAB *audio* banks.** `LEVEL1A.VH` magic =
   `VABp` (stored byte-reversed "pBAV"), version 6, total_size 506832 (≈ `.VB`), 5 programs / 76 tones /
   76 VAGs, master vol 127. So `.VB`/`.VH` = the level's sound bank, irrelevant to geometry.
2. **"The props come from a geometry system past the DAT" — WRONG.** `gpu.pickObject` returns the per-frame
   **scratch/render buffer** (0x801cf000+, where GP0 packets are assembled), NOT the source. "Past the DAT"
   said nothing about the source.

## Headline (the actual finding)
The props are **`fcn.80010000` meshes the editor ALREADY IMPORTS.** Write-watching the berry's render buffer
gave the emitter PC **0x80010a48 (inside `fcn.80010000`)** — the same mesh emitter the editor decodes.
`execTrace` of `fcn.80010000` (capturing `a0` = the DAT payload pointer) across **all 7 prop frames** drew
**58 distinct payloads, of which 57 are already in the editor's 217** imported meshes. Only **one** payload,
**DAT 0x2f700**, is genuinely un-imported (a known un-decoded payload — pass-1 flag-0x14 bridge, see
`tools/catalog_scenery`). So **the geometry is present**, not missing.

**Why the operator couldn't see them:** these props are classified **`decor_prop`**, which the editor rendered
**flat grey** (decor was excluded from `TEXTURED_CLASSES`) — so a red berry looked like a grey blob. The
**V1-tertiary decor-texturing fix (2026-06-24)** now textures them. Example: the berry cluster = decor mesh
**0x32c1c** (reddish vertex colour 0.56/0.38/0.38, 102 verts), instance @world (-5390,-3542,9839) — right
where the operator stood. (Confirmed decor renders: editor frames at that spot now show the textured props /
pink flowers.)

## Evidence
- berry render-buffer writer PC = `0x80010a48` (in `fcn.80010000`).  `execTrace 0x80010000` `regs.a0` = the DAT
  payload pointer (e.g. 0x8018ea34 → DAT 0x2e23c).
- 7-frame union: 58 drawn payloads; 57 ⊂ editor's 217; missing = {0x2f700}.
- berry = decor `0x32c1c`; nearest editor meshes to each prop are all `decor_prop` at the right world spots.

## What this means for the Fidelity Plan (V0 reframed)
V0 is NOT "import a missing geometry system." It collapses to:
1. **Decor texturing** (the props were grey) — **DONE** (V1-tertiary).
2. **One un-decoded payload `0x2f700`** — decode it + the pass-1 flag-0x14 bridge so it imports (small).
3. **Material/colour fidelity** of the props (the berry renders texture×vertex-colour, not the exact bright-red
   in-game material) — this is V1-secondary (per-draw CLUT/material) territory, the open minor residual.
4. Operator action: **restart the editor** (their session predated decor texturing) and navigate to the props.

So the editor's geometry coverage of LEVEL01 props is ~98% (57/58); the gap is rendering recognizability
(fixed) + colour fidelity + one payload — far smaller than first thought. Saves `big_berry_thing.sav` et al.
remain the matched-vantage fixtures.
