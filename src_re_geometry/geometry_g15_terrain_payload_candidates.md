# G15 — terrain/ground render-payload candidate identification

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G11 payload format](geometry_g11_payload_format.md)

Status: **STATIC SURVEY + RUNTIME PLAN (2026-06-14).** Read-only. No patch/build this phase. No
collision/pathing claims; **visual terrain ≠ collision** (do not infer).

## 0. Why this phase

G14 proved payload-vertex edits visibly deform LEVEL01 render geometry, but entry29's payload
(`DAT 0x2f2f8`) is **grass / decorative foliage** — non-tangible, a poor target for terrain work. G15
pivots to finding a **ground/terrain** render payload. Method is the G10/G11 bridge:
trail row `+0x10` → source record → `+0x14`(non-bit3)/`+0x1c`(bit3) → payload
`{u32 count; Vertex verts[N] stride 0xc (s16 x,y,z; s16 pad; u32 attr); primitive command stream}`.

## 1. Discriminator (CONFIRMED shape metric)

Reusable survey: `tools/survey_level01_payloads.py DAT/LEVEL01_LEVEL.DAT --terrain` (read-only). For
each of 482 pass-1 payloads it reports vertex count, X/Y/Z spread, **flatness = Yspread / max(Xspread,
Zspread)**, and horizontal footprint area.

| class | signature | example |
|-------|-----------|---------|
| **grass/decor** | tall + narrow, small footprint, low vert count, often **instanced** (many trail rows → one payload) | entry29 grass: cnt 34, X 119, **Y 1769**, Z 821, flatness **2.15**; decor cluster flatness 2.8–5.1, footprint ~16k–63k |
| **terrain/ground** | wide + flat, large footprint, higher vert count, tight Y band | flatness **< 0.5**, footprint tens of millions, cnt 60–230 |

Confirmation that decor is instanced (LIKELY): `e197`+`e257` share payload `0x36a04`; `e201`+`e261`
share `0x3703c`; `e196` → `0x353a0` — multiple trail rows reuse one small tall payload.

## 2. Terrain/ground candidate shortlist (CONFIRMED metrics; role LIKELY)

Top wide+flat payloads (runtime addr = DATbase `0x801607f8` + payload offset):

| cand | src | bit3 | payload DAT | payload runtime | cnt | Xsp | Ysp | Zsp | flat | footprint | cmd span | note (confidence) |
|------|----:|:----:|------------:|-----------------|----:|----:|----:|----:|-----:|----------:|---------:|-------------------|
| **e213** | `0x46c8` | no | `0x0d934` | `0x8016e12c` | 182 | 8410 | 4039 | 7571 | 0.48 | 63.7M | `0x954` | biggest footprint + high vert count; square-ish X≈Z → **major terrain surface (LIKELY)** |
| **e128** | `0x5348` | no | `0x356bc` | `0x80195eb4` | 230 | 5838 | 3239 | 6700 | 0.48 | 39.1M | `0x5e4` | highest vert count, square footprint → tessellated **ground (LIKELY)** |
| **e17** | `0x4a40` | no | `0x22510` | `0x80182d08` | 60 | 11164 | 3110 | 5001 | 0.28 | 55.8M | `0x2ac` | hugest X but coarse (60 v) → big slab / **background cliff/scenery? (UNKNOWN)** |
| **e280** | `0x46e0` | no | `0x0eb14` | `0x8016f30c` | 124 | 7632 | 2245 | 4636 | 0.29 | 35.4M | `0x60c` | very flat + wide + good tessellation → **flat floor (LIKELY)** |
| **e282** | `0x46f8` | no | `0x0f6f4` | `0x8016feec` | 115 | 8085 | 2545 | 4697 | 0.31 | 38.0M | `0x524` | flat + wide → **floor (LIKELY)** |
| **e264/e265** | `0x4620/38` | no | `0x0945c/0x09dbc` | `0x80169c54/0x8016a5b4` | 94/131 | 8123/8525 | 2265/2542 | 4000/4955 | 0.28/0.30 | 32.5M/42.2M | flat+wide pair, adjacent in file → **floor region (LIKELY)** |
| e0 | `0x4680` | no | `0x0b32c` | `0x8016bb24` | 195 | 6744 | 4214 | 4720 | 0.62 | 31.8M | `0xa74` | high vert count, moderate flat → terrain or large prop (UNKNOWN) |

All are **non-bit3** (0x18 source records) — note grass entry29 was **bit3**; terrain skewing non-bit3
is a weak secondary signal (LIKELY, not relied upon).

Y-distribution (tightness ⇒ flatter): e128 Y q25–q75 = 6107–7461 (band 1354 over 6700 Z); e213
4232–8271 (more undulation → sloped terrain/hill LIKELY); e280 tight low band. The candidates sit at
**positive Y 2000–8000**, a distinct vertical stratum from grass's `0..-1769` (CONFIRMED distinct).

**Static limit (important):** these metrics identify *shape*, not *what is on screen in the tested
camera*. A huge flat payload could be background scenery, a ceiling, or a distant plane rather than the
walkable-looking ground the operator sees near entry29. Static cannot disambiguate → confirm at runtime
(§3). Do not assume any of these is the visible/tangible ground yet.

## 3. G15 RECOMMENDATION — runtime payload-pointer identification (PRIMARY)

The decisive, low-waste next step (the G12/G13 lesson: editing an unconfirmed target gives silent /
ambiguous results). Identify the **actually-drawn** ground payload, then edit that.

Method (one narrow runtime probe; no patch/build):
1. Boot the **pristine** image; enter LEVEL01; go to the area where the visible ground / tree surface
   the operator wants to change is on screen (the entry29 edge-of-level area or wherever ground is
   clearly visible).
2. Execute breakpoint at **`0x80010000`** (entry of the payload mesh emitter `fcn.80010000`). At entry,
   **`a0` = payload pointer** (the value the per-survivor builder passed; `a0` then `+=4` internally).
3. Log `a0` for each hit across one or a few frames while looking at the target ground (DuckStation:
   step/continue and record `a0`, or a conditional log). Each distinct `a0` is one drawn object's
   payload.
4. Match logged `a0` runtime values against the candidate table above (e.g. `0x8016e12c`=e213,
   `0x80195eb4`=e128, `0x8016f30c`=e280, …). The candidate whose runtime payload address appears while
   the ground fills the view **is** the on-screen ground → that becomes the G15-confirmed edit target.
5. Optional cross-check: `a2`/`a1` and the source record behind it; confirm vertex reads with a READ
   watch on the **aligned vertex base** (per the G13 lesson — watch the `lwc2` base, not the inner s16).

This converts "which big flat payload is the ground" from a guess into a CONFIRMED fact in one session.

## 4. Ready-to-build lead candidate (SECONDARY — only if skipping runtime)

If the operator prefers to try a static pick immediately, the strongest single target is **e213**
(largest footprint + high vertex count = most likely a major terrain/ground surface). Proposed edit
(NOT yet built; same single-s16, reversible discipline as G13/G14):

| item | value |
|------|-------|
| candidate | e213 payload `0x0d934` (runtime `0x8016e12c`), 182 verts |
| vertex | central vertex **v21** (nearest the X/Z centroid; xyz `(1807, 5565, 3307)`) |
| field | v21 `y` (s16) |
| DAT offset | `0x0da36` (runtime `0x8016e22e`; vertex base `0x8016e22c`) |
| original | `bd 15` = `5565` |
| proposed | `bd 19` = `6589` (delta `+1024`) |
| revert | `bd 15` |
| rationale | a central vertex of the largest flat surface; `+1024` ≈ 25% of its Y spread → a clear local bump/dip on a broad surface |
| expected | a visible bump/spike on a large ground/terrain surface, IF e213 is the on-screen ground |
| uncertainty | e213 may be terrain, a large prop, or background (UNKNOWN until §3 runtime confirms); silent result is possible if e213 is off-screen/back-faced in the tested view |
| CPU confirm | READ watch aligned base `0x8016e22c` → expect hit in `fcn.80010000`; live `0x8016e22e` = `bd 19` |

**Recommendation: do §3 (runtime identify) first**, then build the confirmed payload's central vertex
rather than guessing e213. This avoids another silent-result cycle. **Do not assume e213 (or any
candidate) is tangible/collidable** — only render consumption is in evidence.

## 6. RUNTIME payload-pointer log — RESULT (2026-06-14)

Operator ran the §3 method: pristine image, standing on / looking at visible ground, EXEC `0x80010000`,
recorded `a0` (= payload pointer at entry). 18 hits. Each mapped via DAT offset = `a0 − 0x801607f8`
and decoded:

| a0 (runtime) | hits | DAT off | count | Xsp | Ysp | Zsp | flat | refs (entries) | role (confidence) |
|--------------|-----:|--------:|------:|----:|----:|----:|-----:|----------------|-------------------|
| `0x80170978` | 1 | `0x10180` | 63 | **7937** | 2389 | 2857 | **0.30** | p1e285 (unique) | **terrain/ground render — LIKELY (PICK)** |
| `0x8018c234` | **6** | `0x2ba3c` | 37 | 1161 | 2069 | 1173 | **1.76** | e218/225/269/270 (instanced) | **tall instanced decor/prop — NOT terrain** |
| `0x8018c570` | 4 | `0x2bd78` | 65 | 732 | 533 | 731 | 0.73 | e55/58/59/60 (instanced) | small cubic prop (rock/blob) — decor LIKELY |
| `0x8018dc58` | 2 | `0x2d460` | 25 | 202 | 107 | 194 | 0.53 | e19/31/92/93 (instanced) | tiny instanced pebble/decor |
| `0x8018bc68` | 1 | `0x2b470` | 24 | 2480 | 1249 | 324 | 0.50 | e284 | thin X-elongated strip/ledge (UNKNOWN) |
| `0x80170978`→ see top | | | | | | | | | |
| `0x801a0974` | 1 | `0x4017c` | 65 | 2706 | 1439 | 704 | 0.53 | e345 (Z≈+24300, far) | distant object (UNKNOWN) |
| `0x8018fd94` | 1 | `0x2f59c` | 18 | 119 | 1769 | 822 | 2.15 | e24/34/35/36 (instanced) | **grass** (same signature as entry29) |
| `0x8018d56c` | 1 | `0x2cd74` | 41 | 705 | 349 | 833 | 0.42 | e120/189/295/311 | small flattish instanced object |
| `0x8018d9cc` | 1 | `0x2d1d4` | 25 | 396 | 156 | 378 | 0.39 | e121/161/164/190 | small flat instanced blob |

**Key correction:** the suggested static "primary" `0x8018c234` is **rejected** — flatness 1.76 (tall),
count 37, instanced (drawn 6× = the same small prop scattered around). **High runtime frequency =
instanced decoration, the opposite of terrain.** Terrain surfaces are large, unique, drawn once.
Among the runtime-confirmed draws, **`0x80170978` (DAT `0x10180`)** is the terrain/ground surface:
widest (X 7937), flattest (0.30), 63 verts all referenced (190 refs = a connected surface), positive-Y
ground stratum (6738..9127, like static terrain e128/e213), drawn once. None of the §2 static shortlist
(e213/e128/e280…) appeared in the log → they are not in the tested camera view; the runtime set is what
matters for an edit visible in the tested area.

## 7. G15 SELECTED TARGET — Candidate TERRAIN-PV — RESULT: VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL CHANGE (2026-06-14)

| item | value |
|------|-------|
| payload | `DAT 0x10180` (runtime `0x80170978`), 63 verts — runtime-confirmed ground-render surface |
| vertex | **v46** (refs=4, near X/Z centroid; xyz `(1362, 7302, -452)`) |
| field | v46 `y` (s16) |
| DAT offset | `0x103ae` (runtime `0x80170ba6`; vertex base `0x80170ba4`) |
| original | `86 1c` = `7302` |
| patched | `86 18` = `6278` (delta `-1024`) |
| revert | `86 1c` |
| changed bytes | exactly one (`0x103af`, `1c→18`) |
| rationale | central, 4×-referenced vertex of a wide flat ground surface; `-1024` drops y below the surface min (`6738`) → in PS1 Y-down space the vertex pokes **up** as a spike above the ground (maximally visible) |
| patch cmd | `python3 tools/patch_g15_runtime_payload_vertex_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G15_RUNTIME_PAYLOAD_VERTEX_TEST.DAT` |
| patched DAT SHA256 | `1466f8e558152f63d61da653a06e115c7f96f0b28e5754b6e3bf809e0a8c1bd2` (sha1 `fbdb3ba9…`) |
| rebuild cmd | `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G15_RUNTIME_PAYLOAD_VERTEX_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G15_RUNTIME_PAYLOAD_VERTEX_TEST.bin --out-cue ABL_G15_RUNTIME_PAYLOAD_VERTEX_TEST.cue --report DAT/LEVEL01_LEVEL_G15_RUNTIME_PAYLOAD_VERTEX_TEST_REBUILD.md --write` |
| image | `ABL_G15_RUNTIME_PAYLOAD_VERTEX_TEST.cue` / `.bin` |
| embedded verify | LBA `2906`, embedded sha1 `fbdb3ba9…` == patched DAT (PASSED); `@0x103ae`=`86 18` |
| staged restore | `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine (`786b7a96…`) |
| artifacts | DAT/BIN/CUE/report gitignored, NOT committed |

**RESULT (operator, 2026-06-14): VALID BUILD / PATCH LIVE / VERTEX READ CONFIRMED / NO OBVIOUS VISUAL
CHANGE.**
- CPU: READ `0x80170ba4` hit (count 1), PC shown `0x8001069c` (`lwc2 v0_z,0x4(t1)`; the x/y word at
  `(t1)` was read first, triggering the watch; addr shown `0x80170ba8`), `t1=0x80170ba4` → inside
  `fcn.80010000` vertex/GTE projection path. **PATCH LIVE / VERTEX READ CONFIRMED.**
- Visual: G15 vs pristine in normal gameplay (breakpoints disabled). Screenshots similar but not
  frame-perfect; **no clear spike, pit, stretched triangle, displaced surface, crash, or black screen**
  by eye.
- **Interpretation:** the edited vertex is read & projected, but read-confirmation is **not** enough to
  guarantee a visible change. The watch fired at the `lwc2` load (BEFORE the backface/screen-bounds/
  depth reject tests), so it does not prove v46's *primitive* survived to an emitted packet — it may be
  rejected, off the visible frame, or a sub-pixel delta. Does **not** disprove the payload path.
  **Next: G16 must select a vertex with screen-space evidence (emitted + on-screen), captured at the
  packet-store gate `0x800108b4` — see
  [geometry_g16_screen_space_vertex_selection.md](geometry_g16_screen_space_vertex_selection.md).**
  Background-element vs walkable ground still not excluded; **visual terrain ≠ collision** (do not infer).

**G16 follow-up (2026-06-14):** the `0x800108b4` runtime log found that the static candidate **e128**
(`DAT 0x356bc`, rt `0x80195eb4`) — NOT the G15-edited `0x10180` — is the payload emitting the most
primitives in the ground view (≥5). So the static survey *did* contain an on-screen terrain surface
(e128); the emitted-primitive gate disambiguated it. G16 Candidate EMITTED-PV edited `0x356bc` vertex 10.

**G16 visual RESULT (2026-06-14): VISIBLE WALL RENDER CHANGE.** The `0x356bc` edit produced a visible
deformation — but on a **vertical wall/cliff face, not the walkable floor/top surface**. So **e128
`0x356bc` is reclassified wall/vertical terrain face**, not "ground (LIKELY)" as guessed in the §2 static
shortlist. Consistent metric signal: e128 has the **highest** flatness (`0.48`) and **largest** local Y
band (q25–q75 = `1354`) of the shortlist — i.e. the *least* flat, as expected for a wall. CONFIRMED:
payload-vertex edits visibly deform terrain-family geometry; UNKNOWN: the walkable floor payload and any
collision coupling (visual terrain ≠ collision — do not infer). **Pivot to a flatter, tight-Y, floor
target with emitted evidence → G17**
([geometry_g17_floor_payload_candidates.md](geometry_g17_floor_payload_candidates.md)). The flattest
floor candidates (e135 `0x1f148` flat 0.19, e254 `0x08f4c` 0.22, e52 `0x17d94` 0.23) and the partial-emit
lead `0x1b9f0` (e160, ≥2 emitted prims) are listed there.

## 8. Reproduce (read-only)

```bash
python3 tools/survey_level01_payloads.py DAT/LEVEL01_LEVEL.DAT --terrain --top 15
python3 tools/survey_level01_payloads.py DAT/LEVEL01_LEVEL.DAT --decor   --top 5
# runtime-pointer decode: DAT off = a0 - 0x801607f8; parse count/bbox at that offset
```
