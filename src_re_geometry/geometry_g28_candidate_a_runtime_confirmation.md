# G28 — Candidate A runtime/projection confirmation + visual terrain deformation result

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G27 count-validated floor candidates](geometry_g27_count_validated_floor_candidates.md) ·
[← G26 floor payload re-audit](geometry_g26_floor_payload_reaudit.md)

Status: **VISUAL TEST RESULT IN — Candidate A is a CONFIRMED DAT-backed visual terrain/floor payload (2026-06-15).**
Runtime READ + projection-path confirmation (§2) gated the build; the guarded same-size edit was built into
`ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue` (§5.2) and the operator then TESTED it (§5.3): it **boots, LEVEL01 loads,
and the tested floor/terrain area visibly deforms** (caves inward; the deformation shifts slightly with viewing
angle) in the lower/central region matching Candidate A's projected area, while Flik and other objects still
render. **Collision/pathing did NOT align with the visual deformation** → for this tested edit, visual render
geometry and collision/pathing are separate. No claim beyond that — **visual terrain payload ≠ collision/pathing
source; do not infer tangibility.**

> **Headline.** G27 statically classified **Candidate A** (`DAT 0x188cc`, runtime payload base
> `0x801790c4`, vertex base `0x801790c8`, count 83, flatness 0.154, Y-band 316, 4502×4502 world-space
> footprint, DAT-backed, unique) as the strongest floor/top-surface candidate. **G28 closes the G27 §5
> gate from the consumer side:** Candidate A's vertex base is **read repeatedly in the active
> render/projection path**, and the projection site **EXEC `0x80010718`** hits while Candidate A is active
> with **plausible lower/central screen-space** coordinates. Candidate A is therefore a
> **VALID DAT-BACKED PAYLOAD / RUNTIME READ CONFIRMED / PROJECTION PATH CONFIRMED / LIKELY VISUAL
> FLOOR/TOP-SURFACE / TANGIBILITY UNKNOWN.** The guarded same-size diagnostic edit
> (`tools/patch_g28_candidate_a_floor_y_test.py`) was then **built (§5.2) and operator-TESTED (§5.3)**: it boots,
> LEVEL01 loads, and **visibly deforms the floor/terrain in Candidate A's projected area** (caves inward, shifts
> slightly with view angle) while Flik/other objects still render and **collision/pathing did not follow the
> deformation**. Candidate A is therefore now a **CONFIRMED DAT-backed visual terrain/floor render payload**
> (not decor/prop); **visual render geometry ≠ collision/pathing source** for this tested edit (tangibility still
> UNKNOWN).

## 1. Candidate A identity (from G27 — CONFIRMED, pristine `DAT/LEVEL01_LEVEL.DAT`, sha1 `b376cb50…`, `0x51418`)

| field | value |
|-------|-------|
| payload base (runtime) | `0x801790c4` |
| vertex base (runtime) | `0x801790c8` (= payload base + 4) |
| LEVEL01/LEVEL.DAT offset | `0x188cc` |
| count `[payload base]` | **83** (count-validated, G26 §2 acceptance test PASS) |
| DAT-backed | **yes** (`0x188cc < 0x51418`) → directly editable |
| static class (G27) | strongest floor/top-surface candidate (flat 0.154, Y-band 316, 4502×4502, world-space, unique) |

## 2. G28 runtime confirmation — evidence (operator)

Runtime breakpoints/watches run in the Candidate-B floor/top-surface view.

### 2.1 READ watch — Candidate A reaches the render/projection path
| item | value |
|------|-------|
| READ watch address | `0x801790c8` (Candidate A vertex base) |
| result | **hit repeatedly** |
| context | `a0 = 0x801790c8`, `ra = 0x800206a0` (shared emitter tail) |
| derived payload base | `a0 − 4 = 0x801790c4` |
| count at payload base | **83** (matches G27) |

→ **CONFIRMED:** Candidate A's vertex base is actively read by the render/projection path (same `ra`
shared-emitter context as the G27 capture). The `a0 = vertex base`, `payload = a0 − 4` relationship is the
CONFIRMED `fcn.80010000`/emitter convention (G26 §3).

### 2.2 EXEC `0x80010718` — projected-primitive emission while Candidate A active
`EXEC 0x80010718` (immediately after `mfc2 SXY0/1/2`, the per-primitive projection site) hit while
Candidate A was active. Two captured projected primitives:

| # | pc | a0 | ra | SXY0 | SXY1 | SXY2 |
|---|----|----|----|------|------|------|
| 1 | `0x80010718` | `0x801790c8` | `0x800206a0` | `0x007A0164` | `0x00730182` | `0x007B0180` |
| 2 | `0x80010718` | `0x801790c8` | `0x800206a0` | `0x007F01A8` | `0x007701CF` | `0x008501F1` |

Unpacking each packed `SXYn` under the CONFIRMED G16 convention `(Y<<16)|X` (signed 16-bit halves;
`X = low s16`, `Y = high s16`):

| # | vtx | X (low s16) | Y (high s16) |
|---|-----|------------:|------------:|
| 1 | SXY0 | `0x0164` = 356 | `0x007A` = 122 |
| 1 | SXY1 | `0x0182` = 386 | `0x0073` = 115 |
| 1 | SXY2 | `0x0180` = 384 | `0x007B` = 123 |
| 2 | SXY0 | `0x01A8` = 424 | `0x007F` = 127 |
| 2 | SXY1 | `0x01CF` = 463 | `0x0077` = 119 |
| 2 | SXY2 | `0x01F1` = 497 | `0x0085` = 133 |

**Interpretation (faithful to operator, no overclaim):** the **Y values cluster tightly in ≈115–133**, i.e.
the **central / lower-central vertical band** of a ~240-line field — consistent with the operator's read of
"plausible lower/central screen-space hits" and with a floor/top-surface (contrast the G16 wall, which
projected upper/side). The **X values (≈356–497)** are recorded raw; their exact horizontal placement
depends on the GPU draw-offset/viewport mapping, which is **not byte-exact yet (mapping = TODO, per G16)** —
so the horizontal position is **not** used to make a decisive claim. Both primitives carry the same
`a0 = 0x801790c8` / `ra = 0x800206a0` as the G27 capture, tying these projections to Candidate A.

## 3. Classification (G28)

```
VALID DAT-BACKED PAYLOAD /
RUNTIME READ CONFIRMED /
PROJECTION PATH CONFIRMED /
LIKELY VISUAL FLOOR/TOP-SURFACE /
TANGIBILITY UNKNOWN
```

- **VALID DAT-BACKED PAYLOAD** — G27 §2 acceptance test PASS; `0x188cc < 0x51418`.
- **RUNTIME READ CONFIRMED** — READ watch `0x801790c8` hit repeatedly (§2.1).
- **PROJECTION PATH CONFIRMED** — EXEC `0x80010718` hit with `a0 = 0x801790c8` (§2.2).
- **LIKELY VISUAL FLOOR/TOP-SURFACE** — flat/wide/world-space shape (G27) + projected Y in the
  central/lower-central band (§2.2). **→ UPGRADED to CONFIRMED visual terrain/floor render mesh by the §5.3
  visual test** (the built edit visibly deformed the floor/terrain in A's projected area). Still not a proven
  *walkable* surface.
- **TANGIBILITY UNKNOWN** — nothing here, and nothing in the §5.3 visual test, speaks to collision/pathing; the
  §5.3 deform did **not** align with collision. **Do not infer.**

## 4. Candidate A (`0x801790c4`) vs the retracted compressed source (`0x801bdc58`) — keep separate

| address | what it is | status |
|---------|------------|--------|
| **`0x801790c4`** | **Candidate A** payload base; DAT `0x188cc`; count 83; runtime-read + projection-confirmed | **VALID DAT-backed payload (this doc)** |
| `0x8018dc58` | Candidate E payload base; DAT `0x2d460`; count 25; instanced ×93 | valid DAT payload = G18b decor (do not conflate) |
| `0x801bdc58` | `LEVEL.RAW + 0xa81ac`, **compressed source**; first word `0x70d4001a` (impossible count); WRITE-watch 0 hits | **RETRACTED as a payload (G26)** — never a render payload, never written, not editable |

`0x801790c4` and `0x801bdc58` differ by one hex digit but are entirely different objects. The G26 retraction
of `0x801bdc58` (compressed LEVEL.RAW source) **stands** and is **not** resurrected here. The LEVEL.RAW
load/decompress RE (G22–G25) remains valid characterization of that resource pipeline.

## 5. Guarded same-size diagnostic edit — BUILT (§5.2) + TESTED (§5.3)

Single-s16, single-byte, reversible, same-size Y deform of Candidate A's most-central, multiply-referenced
vertex (v16, refs=5, ~mid-floor — not a cull-prone edge tip). Tool:
`tools/patch_g28_candidate_a_floor_y_test.py`.

| field | value |
|-------|-------|
| target file | `LEVEL01/LEVEL.DAT` (pristine source `DAT/LEVEL01_LEVEL.DAT`, sha1 `b376cb50…`, `0x51418`) |
| payload | Candidate A, DAT `0x188cc` (runtime `0x801790c4`, count 83) |
| vertex index | 16 |
| field | `y` (s16) |
| field DAT offset | `0x18992` (= `0x188cc + 4 + 16*0xc + 2`; runtime base `0x80179188`, y at `0x8017918a`) |
| original bytes / value | `89 13` = `0x1389` = 5001 |
| candidate new bytes / value | `89 17` = `0x1789` = 6025 |
| delta | `+0x0400` / +1024 (single byte `0x18993`: `13 → 17`) |
| revert bytes | `89 13` (at DAT `0x18992`) |
| size discipline | **same-size only** (`0x51418`); never patch in place; verify exact original bytes |

**Expected visual (if Candidate A is visible floor/top-surface):** a local out-of-plane deformation
(~1024-unit lift) near the floor's center — `1024 ≈ 3×` Candidate A's tight Y-core band (316), pushing v16
beyond the existing Y-max (5063), deforming the up-to-5 triangles that share v16.

**Explicit uncertainty:** (1) Y-sign → screen up/down mapping UNCONFIRMED — `+1024` is a clear out-of-plane
outlier either way; documented fallback `-1024` → 3977 = `0x0f89` (bytes `89 0f`, single byte `13 → 0f`).
(2) Candidate A's floor role is LIKELY, not proven walkable. (3) **Collision/pathing UNKNOWN** — a visible
floor deform says nothing about whether Flik's standing surface moves (visual ≠ collision).

### 5.1 Build commands (run ONLY when explicitly instructed)
Uses the existing standard rebuild wrapper `tools/rebuild_with_patched_dat.py` (same flow as the G6 build);
**no new wrapper added** (consistent with G12–G16, which call the shared wrapper).

```bash
# 1. Produce the same-size patched DAT (never in place; verifies size + exact original bytes):
python3 tools/patch_g28_candidate_a_floor_y_test.py \
    DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST.DAT

# 2. Stage into REBUILD/files, rebuild the image with mkpsxiso, verify the embedded DAT, restore pristine:
python3 tools/rebuild_with_patched_dat.py \
    --patched-dat DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST.DAT \
    --target files/LEVEL01/LEVEL.DAT \
    --out-bin ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.bin \
    --out-cue ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue \
    --write --report DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST_REBUILD.md
```

Expected future image name: **`ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue`**. Per prior phases, BIN/CUE/patched-DAT
artifacts are gitignored / not committed; the staged `REBUILD/files/LEVEL01/LEVEL.DAT` is restored to pristine
after building.

### 5.2 Build record (2026-06-15) — BUILT / EMBEDDED-VERIFIED / NOT YET TESTED

The §5.1 commands were run from a clean repo (HEAD `d2de51e`). The rebuild step additionally passed
`--expected-sha1 a1cf8d8e…` as a guard. No visual result is recorded — the operator has not run the image.

| item | value |
|------|-------|
| pristine input DAT | `DAT/LEVEL01_LEVEL.DAT`, sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`, `0x51418` |
| patched DAT | `DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST.DAT` |
| patched DAT sha1 / sha256 | `a1cf8d8e638460b4861f4d405872bff0a2738f5f` / `546a28b846dd8406b545cafca63db13f7d3031af35844675d09bd09553f02882` |
| size | `332824` (`0x51418`) — unchanged (same-size) |
| changed bytes | DAT `0x18992` `89 13` → `89 17` (single byte `0x18993` `13`→`17`; +1024); **exactly 1 byte differs file-wide** |
| Candidate A count `@0x188cc` | 83 (unchanged) |
| image | `ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.bin` / `.cue` (738285744 bytes, 313897 sectors) |
| embedded DAT verified | LBA 2906, size `332824`, sha1 `a1cf8d8e…` == patched DAT ✓ |
| staged workspace restored | `REBUILD/files/LEVEL01/LEVEL.DAT` → pristine sha1 `b376cb50…` ✓ |
| collision/pathing files | untouched (`PAD/PATH*.BIN` unchanged); no runtime-address patch |
| artifacts | gitignored / **not committed**; **operator test DONE → visible terrain deformation (§5.3)** |

### 5.3 Visual test result (2026-06-15) — VISIBLE TERRAIN DEFORMATION CONFIRMED

The operator ran the §5.2 image `ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue` in the same Candidate-B floor/top-surface
view. Result:

| check | result |
|-------|--------|
| boots to title/menu | **YES** |
| LEVEL01 loads | **YES** |
| visible deformation | **YES** — the tested floor/terrain area visibly **caves inward / deforms** |
| location | lower/central floor/terrain region, **matching Candidate A's projected area** (§2.2 Y≈115–133) |
| angle dependence | the deformation **shifts slightly with viewing angle** (consistent with a 3D mesh vertex moved within the rendered surface) |
| other objects still render | **YES** — Flik and other scene objects still render normally |
| collision / pathing | **does NOT align with the visual deformation** |
| crash / black screen | none |

**Note on direction (faithful to the pre-test uncertainty in §5):** the Y-sign→screen mapping was UNCONFIRMED; the
observed effect was an **inward cave**, not the tentatively-worded "spike/lift". Either way the `+1024` move of
v16.y produced a **clear out-of-plane deformation of visible terrain**, which is exactly what the test set out to
detect. The exact Y-sign→screen-up/down mapping is now illuminated (here `+Y` reads as inward/down in this view),
but the byte-exact viewport mapping remains **TODO (G16)** and is not used for any further claim.

**Classification after the visual test:**
```
CONFIRMED:
  - Candidate A is a DAT-backed VISUAL terrain/floor payload.
  - The edit at LEVEL01/LEVEL.DAT + 0x18992 affects VISIBLE terrain geometry.
  - Candidate A is NOT just decor/grass/prop.
  - Candidate A is part of the visible floor/top-surface render mesh in the tested area.
  - Visual render geometry and collision/pathing are SEPARATE for this tested edit.

LIKELY:
  - Candidate A belongs to the visible terrain/floor/top-surface mesh family used in the Candidate-B view.

UNKNOWN:
  - The actual collision/pathing source for this floor surface.
  - Whether Candidate A has any collision/tangibility data associated elsewhere.
```

**Explicit, not overstated:** `visual terrain payload ≠ collision/pathing source`. The tested visual deformation
did **not** alter or align with collision, so collision/pathing remains **separate or sourced elsewhere** — this
does **not** claim collision "moved", and says nothing about tangibility. (This mirrors the earlier G6
render/collision separation, now reconfirmed on a CONFIRMED DAT-backed *floor/top-surface* payload rather than on
a trail flag.)

**Evidence handling:** the operator captured screenshots of the caved-in surface (multiple angles; Flik + objects
still rendering; collision not following the deform). These are **external/operator evidence** — described here
textually and **not committed** (the repo has no image-evidence policy/location). An untracked local capture
`G28_Deformity` exists in the working tree but is intentionally left **unstaged**, consistent with the gitignored
BIN/CUE/DAT artifact policy.

## 6. Operator runbook — G28 visual test (RAN 2026-06-15; result in §5.3)

**Result:** steps 1–5 ran; the floor/terrain visibly deformed in Candidate A's projected area (caves inward,
angle-dependent), Flik/objects still rendered, and collision did not follow (step 7 not separately exercised →
collision/pathing UNKNOWN). The runbook is retained for reproduction.

```
1. Build the G28 Candidate A image from pristine disc + patched LEVEL.DAT
   (§5.1: patch_g28_candidate_a_floor_y_test.py -> rebuild_with_patched_dat.py).
2. Boot LEVEL01.
3. Use the same Candidate B floor/top-surface view.
4. Compare the visible floor/top-surface near the lower/central screen band.
5. Expected visual effect:
   Candidate A vertex16 Y is raised by +1024, so if Candidate A is visible floor/top-surface,
   a local visual deformation should appear.
6. If no visible change:
   Candidate A may be off-screen in that view, occluded, not the specific floor patch area,
   or the chosen vertex may be visually subtle.
7. Collision/pathing remains UNKNOWN unless separately tested.
```

## 7. Guardrails
This documentation pass executed **no patch, no build, no edit** of game data. The §5 edit was built (§5.2) and
operator-tested (§5.3) in prior steps; this file only records the result. `0x801bdc58` stays **compressed
LEVEL.RAW source** (G26) — not resurrected. `0x8018dc58` (Candidate E) is a valid DAT payload — do not conflate.
Candidate A is now a **CONFIRMED visual terrain/floor render payload** (§5.3), still **not** proven walkable.
Collision/pathing **UNKNOWN** — the §5.3 deform did not align with collision; **visual terrain payload ≠
collision/pathing source**; do not infer tangibility or that collision moved.

## 8. Next phase — recommended: **G29 collision/pathing source discovery**
Now that Candidate A is a CONFIRMED DAT-backed visual floor/top-surface render payload, pivot to locating the
**separate** collision/pathing source for this surface:
- Do **not** assume the collision source is in Candidate A.
- Do **not** assume LEVEL.RAW or LEVEL.DAT without new evidence.
- Use runtime collision probes / movement-height (floor-contact) reads / floor-contact state rather than the
  visual render path alone.

Secondary alternative (only if the goal is more render-geometry editing rather than collision discovery):
**controlled visual terrain sculpting within Candidate A** (it is now a proven editable visual surface).

## 9. Reproduce (read-only)
```bash
python3 -c "import struct;d=open('DAT/LEVEL01_LEVEL.DAT','rb').read();\
print('A count @0x188cc =', struct.unpack_from('<I',d,0x188cc)[0]);\
print('v16 y @0x18992 =', d[0x18992:0x18994].hex(' '), '=', struct.unpack_from('<h',d,0x18992)[0])"
# Unpack the EXEC 0x80010718 SXY words (Y<<16 | X, signed halves):
python3 -c "
for w in (0x007A0164,0x00730182,0x007B0180,0x007F01A8,0x007701CF,0x008501F1):
    x=w&0xffff; y=(w>>16)&0xffff
    x-= 0x10000 if x>=0x8000 else 0; y-= 0x10000 if y>=0x8000 else 0
    print(hex(w),'-> X',x,'Y',y)"
```
