# G17 — walkable floor / top-surface render-payload candidate identification

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G16 screen-space selection](geometry_g16_screen_space_vertex_selection.md) ·
[← G15 terrain candidates](geometry_g15_terrain_payload_candidates.md)

Status: **RUNTIME RESULT (Candidate B) — emitted floor is an OUTPUT-BUFFER/HEAP payload (2026-06-14).**
Read-only static survey + runtime log. **No patch, no build.** The walkable floor's emitted payload is
**not** in LEVEL.DAT → traced in [geometry_g18_output_buffer_floor_trace.md](geometry_g18_output_buffer_floor_trace.md).
No collision/pathing claims — **visual floor ≠ collision floor** (do not infer).

> **⚠ G26 CORRECTION (2026-06-15) — Candidate B is RETRACTED.** The "emitted floor payload at `0x801bdc58`" result
> below is **WRONG**. Operator ground truth: at `Press X to Continue` `[0x801bdc58] = 0x70d4001a`
> (= `LEVEL.RAW[0xa81ac]`, compressed source) and a **WRITE watch `0x801bdc58` during load = 0 hits** → `0x801bdc58`
> is **compressed LEVEL.RAW source**, never an `fcn.80010000` payload (its "count" `0x70d4001a` is impossible). The
> `EXEC 0x800108b4` log's `a0−4 = 0x801bdc58` was never count-validated; a real call there cannot emit clean
> primitives. The walkable-floor render payload pointer is **UNKNOWN** — re-find from the consumer side with count
> validation. Full re-audit + runbook: [geometry_g26_floor_payload_reaudit.md](geometry_g26_floor_payload_reaudit.md).
> (The static floor shortlist below — e135 `0x1f148` / e254 `0x08f4c` / e52 `0x17d94` — remains a valid set of
> DAT-backed candidates to re-test with the G26 runbook.)

## 0. Why G17 exists

G16 produced the first **terrain-family** visible deform (a payload vertex edit that changed real level
geometry, not grass/decor). But the deformed surface was a **vertical wall / cliff face**, not the
walkable floor/top surface Flik stands on. G16 result string:
**VALID BUILD / PATCH LIVE / EMITTED PAYLOAD CONFIRMED / VISIBLE WALL RENDER CHANGE.** Payload `0x356bc`
(= static e128) is **reclassified wall/vertical terrain face**.

G17 goal: find the **walkable floor / top-surface** render payload using **emitted-primitive evidence**
(EXEC `0x800108b4`), filtered for a flat horizontal floor — not a wall/cliff, not grass/decor.

## 1. Lesson chain (CONFIRMED)

| phase | target | result | lesson |
|------|--------|--------|--------|
| G14 | entry29 `0x2f2f8` | VISIBLE / grass-decor (non-tangible) | method works; entry29 is decor |
| G15 | `0x10180` (runtime `a0`-log pick) | read-confirmed, **visually silent** | vertex-read (at the `lwc2` load, before rejects) ≠ drawn |
| G16 | `0x356bc` (emit-confirmed at `0x800108b4`) | **VISIBLE — but a WALL** | emit-confirmed ⇒ visible; but **emit-in-the-ground-view is necessary, not sufficient** for "floor" — a wall in the frame also emits |
| **G17** | a flat, emit-confirmed **floor** payload | TBD | add a **floor filter**: flat shape + low local Y band + the primitive's screen-XY lands on the walkable floor |

## 2. Floor discriminator (CONFIRMED metric)

Reuse `tools/survey_level01_payloads.py DAT/LEVEL01_LEVEL.DAT --terrain` plus a **local Y-band** check
(Y inter-quartile spread q25–q75). Walls/cliffs and floors can both be "wide"; the separators:

| class | flatness = Ysp/max(Xsp,Zsp) | local Yband (q25–q75) | footprint | example |
|-------|----------------------------:|----------------------:|-----------|---------|
| grass/decor | > 2 (tall, narrow) | n/a | small, often instanced | entry29 `0x2f2f8` (flat 2.15) |
| **wall / vertical face** | ~0.45–1.0 (large Y) | **large (>1000)** | large | **`0x356bc` e128 flat 0.48, Yband 1354** (G16-confirmed wall) |
| **walkable floor / top** | **< 0.35** | **small (<900)** | large | e135 `0x1f148` flat 0.19, Yband 409 (LIKELY) |

So the G16 wall is the *least-flat* member of the old terrain shortlist; the floor is among the
*flattest*, tight-Y, wide, unique (drawn-once) payloads.

## 3. Static floor shortlist (CONFIRMED metrics; role LIKELY; NO emitted evidence yet)

Decoded read-only from pristine `DAT/LEVEL01_LEVEL.DAT` (runtime = DATbase `0x801607f8` + payload off).
Excludes `0x356bc` (wall, G16) and `0x2f2f8`/decor (grass). **All are unique (one pass-1 entry → one
payload)** — unlike instanced decor whose runtime `a0` repeats.

| cand | payload DAT | runtime | cnt | Xsp | Ysp | Zsp | flat | Yband q25–q75 | Y range | refs | role (confidence) | emit evidence |
|------|------------:|---------|----:|----:|----:|----:|-----:|--------------:|---------|------|-------------------|---------------|
| **e135** | `0x1f148` | `0x8017f940` | 110 | 5546 | 1069 | 4541 | **0.19** | 409 | 4464–5533 | e135 | flattest wide surface → **floor (LIKELY)** | none yet |
| **e254** | `0x08f4c` | `0x80169744` | 53 | 6756 | 1504 | 4120 | **0.22** | 636 | 4428–5932 | e254 | very flat wide → **floor (LIKELY)** | none yet |
| **e52** | `0x17d94` | `0x8017858c` | 122 | 5005 | 1128 | 5000 | **0.23** | 622 | 4270–5398 | e52 | flat square footprint → **floor (LIKELY)** | none yet |
| **e264** | `0x0945c` | `0x80169c54` | 94 | 8123 | 2265 | 4000 | 0.28 | 684 | 4428–6693 | e264 | flat + very wide → **floor (LIKELY)** | none yet |
| **e280** | `0x0eb14` | `0x8016f30c` | 124 | 7632 | 2245 | 4636 | 0.29 | 812 | 6733–8978 | e280 | flat + wide → **floor (LIKELY)** | none yet |
| **e265** | `0x09dbc` | `0x8016a5b4` | 131 | 8525 | 2542 | 4955 | 0.30 | 649 | 4207–6749 | e265 | adjacent to e264 → **floor region (LIKELY)** | none yet |
| `0x1b9f0` (**lead**) | `0x1b9f0` | `0x8017c1e8` | 92 | 4513 | 1427 | 4130 | 0.32 | 573 | 6908–8335 | e160 | flat, tight-Y → floor-or-flat-ledge (UNKNOWN) | **≥2 emitted prims in the G16 `0x800108b4` ground-view log** |
| `0x10180` (G15 pick) | `0x10180` | `0x80170978` | 63 | 7937 | 2389 | 2857 | 0.30 | 739 | 6738–9127 | e285 | wide flat, drawn once → floor (LIKELY) | vertex-read only (G15); **no emit yet** |

Notes:
- **`0x1b9f0` is the only floor-shaped payload with any emitted-primitive evidence** (it emitted ≥2
  primitives in the same ground-view log that produced the G16 wall). It is therefore the **lead** G17
  candidate, but whether it is the *walkable floor* vs another flat ledge in the frame is **UNKNOWN**
  until re-logged while the floor fills the screen and its primitive screen-XY is checked (§4).
- The e135/e254/e52 cluster (flat 0.19–0.23, low Y, ~4200–5900 Y stratum) are the **flattest** floors by
  shape but have **no emitted evidence** — exactly the G15 trap (good metrics, never confirmed drawn).
  Confirm at the `0x800108b4` gate before editing.
- e264/e265 (flat ~0.29, ~4200–6700 Y) sit in the same low-Y stratum as e254 → LIKELY a connected floor
  region; e280 sits in the higher 6700–9000 stratum (like the wall and `0x10180`).

**Static limit (unchanged from G15):** shape ≠ what is on screen / walkable in the tested camera. A flat
payload could be a flat ceiling, a distant plane, or a ledge. Runtime emit + screen-XY is decisive.

## 4. G17 runtime runbook (DuckStation, operator) — PRIMARY

The decisive step. Identify the **emitted, on-screen, floor-positioned** payload, then edit that.

1. **Pristine image** (rebuild base), unless re-testing a later G17 patch. Confirm
   `mem32[0x80082498]=0x801607f8` (DATbase).
2. **Stand on / look directly at the walkable floor/top surface** so the flat ground Flik stands on
   fills the screen. Avoid framing the cliff/wall (the G16 `0x356bc` surface) and grass.
3. **EXEC breakpoint `0x800108b4`** (`addi s3,s3,0x34`, packet-store gate past all RTPS/RTPT/NCLIP/AVSZ4
   rejects in `fcn.80010000`). Disable all other breakpoints/watches.
4. Record **10–20 hits** while the floor fills the view:

   | field | how |
   |-------|-----|
   | `a0` | register at the stop |
   | payload base | `a0 − 4` |
   | payload DAT offset | payload base − `0x801607f8` |
   | `s3` | packet pointer register |
   | hit # | sequential |
   | note | floor look / camera / is a wall also in frame? |

5. **Prefer hits while the visible floor fills the screen** (minimise wall/grass in frame). Map each
   `a0` to the §3 shortlist (e135/e254/e52/e280/e264/e265 or the `0x1b9f0` lead). **High-frequency
   repeated `a0` = instanced decor → reject** (G15 rule). Terrain/floor surfaces are unique, drawn once.
6. **Do not use paused-frame / breakpoint-frame visuals as the final comparison** — capture with
   breakpoints disabled and gameplay running.

### Screen-coordinate capture (to prove the primitive is on the floor, not a wall)

Optional but recommended to disambiguate floor from wall (the G16 failure mode):

- At `0x800108b4`, read the just-written packet at **`s3`**: screen-XY words at
  `s3+0x00/0x08/0x0c/0x14/0x18/0x20`; unpack **X = low s16, Y = high s16**; on-screen ≈ `0..320`×`0..240`.
- Cleaner: EXEC BP at **`0x80010718`** (right after `mfc2 SXY0/1/2`), read `t5/t6/t7` (each
  `(screenY<<16)|screenX`, signed halves).
- A **floor** primitive projects into the **lower/central** screen band (where the ground is); a **wall**
  into the **upper/side** band. Use this to pick the floor payload.
- **Do NOT** read `t5/t6/t7` at `0x800108b4` — there they are reused packet/OT/color words (G16
  correction; logged values unpack to impossible coords). Read packet memory at `s3`, or use the
  `0x80010718` BP.

## 5. After the log — deferred build plan (NOT yet built)

Build only when **all** of these hold (guardrail: no floor target from bbox alone):
1. a floor payload is **emit-confirmed** at `0x800108b4` while the floor fills the view, AND
2. its primitive's **screen-XY lands on the walkable floor** (lower/central band), AND
3. it is **unique** (drawn once; `a0` not repeated = not instanced decor).

Then choose its **central, multiply-referenced** vertex (command-stream reference histogram, per the G14
method), and prepare **`tools/patch_g17_floor_payload_vertex_test.py`** (to be written at that point) with
the same discipline as G15/G16:

- input/output DAT paths; refuse same input/output (no in-place mutation);
- verify size `0x51418`; verify the exact original bytes at the chosen s16 coordinate;
- write **exactly one** s16 coordinate (single Y deform, e.g. `±1024`, single byte where possible);
- print SHA256 before/after, offset, old/new bytes, old/new signed value, delta, revert bytes;
- fail loudly on any mismatch.

Suggested artifacts (gitignored, **not committed**, like G6–G16):
```
DAT/LEVEL01_LEVEL_G17_FLOOR_PAYLOAD_VERTEX_TEST.DAT
ABL_G17_FLOOR_PAYLOAD_VERTEX_TEST.cue
ABL_G17_FLOOR_PAYLOAD_VERTEX_TEST.bin
```

**Expected:** a bump/dip on the walkable floor surface (vs no change / wall change / crash). Collision/
pathing UNKNOWN — **visual floor ≠ collision floor; do not infer.** A successful visible floor deform
still says nothing about whether Flik's collision/standing surface moved.

## 6. Candidate B runtime RESULT — emitted floor is an output-buffer/heap payload (2026-06-14)

The operator ran the §4 runbook for **Candidate B** (broad walkable floor/top surface, Flik centered),
EXEC `0x800108b4`. **All 17 hits showed one payload**, `a0 = 0x801bdc5c` → payload base **`0x801bdc58`**:

| field | value |
|-------|-------|
| PC | `0x800108b4` (×17) |
| payload base (`a0−4`) | `0x801bdc58` |
| raw DAT offset | `0x5d460` — **INVALID** (`> 0x51418` EOF) |
| output base | `0x801b1c10` (DATbase + filesize) |
| output-buffer offset | `0xc048` |
| s3 packets | `0x801e5414 … 0x801e5b98` (stride `0x34`, with strip gaps) |

**Classification:** `EMITTED FLOOR/TOP-SURFACE CANDIDATE / RUNTIME-GENERATED OR OUTPUT-BUFFER PAYLOAD /
DAT SOURCE UNKNOWN`. Collision/pathing UNKNOWN.

**Key result:** the walkable floor's emitted payload is **past LEVEL.DAT EOF** (`0x801b1c10`), **past the
pass-1 output array** (`0x801b5890`), and **past the reserved gap** (`0x801b6a10`) — it sits `0x7248` into
the "next resource" heap region. None of the §3 static floor shortlist (e135/e254/e52/…) or the `0x1b9f0`
lead is the floor in this view; **the floor is not a LEVEL.DAT payload at all.** This supersedes the §3
expectation that a flat LEVEL.DAT payload would be the walkable floor.

**Why this matters:** it explains every prior negative — G12–G16 edited LEVEL.DAT payloads (walls/grass/
props), but the walkable floor is a separately-loaded/generated terrain resource. Full address proof,
emitter `a0`-source decode, and the separate-resource evidence (`LEVEL.RAW`/`TERRAIN.ALL`/`TERR1.ALL`) are
in **[geometry_g18_output_buffer_floor_trace.md](geometry_g18_output_buffer_floor_trace.md)**, with the
narrow runtime writer/source-trace runbook (WRITE watch `0x801bdc58` during load + read `s2` at emitter
`0x80020684`). **Do not** treat `0x5d460` as a DAT offset; **do not** patch runtime-buffer addresses;
visual floor ≠ collision floor.

## 6b. Candidate B-LIKE re-log — DAT-backed payload `0x2d460` is instanced decor, not floor (2026-06-14)

A second, **near-floor** view (operator moved very close to the §6 Candidate B view, not pixel-identical)
re-ran EXEC `0x800108b4` and this time the emitted payload was **DAT-backed**: `a0=0x8018dc5c` → base
`0x8018dc58` → DAT off **`0x2d460`** (VALID, `< 0x51418`). Promising at first glance (editable, unlike the
heap floor `0x801bdc58`), but the static decode reclassifies it:

| metric | `0x2d460` | floor filter (§2) |
|--------|-----------|-------------------|
| references | **93** pass-1 source records | unique / drawn-once |
| footprint | 202 × 194 (X × Z) | wide (thousands) |
| flatness | 0.53 | `< 0.35` |
| shape | 25-vert closed blob, all verts referenced | broad flat slab |

→ **instanced decor/prop (×93), NOT the walkable floor** — the same trap G15 named (high-frequency instanced
`a0` = decor → reject). The walkable floor that fills the screen is still the heap payload `0x801bdc58`
(§6 / [g18 output-buffer trace](geometry_g18_output_buffer_floor_trace.md)), not a LEVEL.DAT payload. Full
record: [geometry_g18_dat_backed_floor_candidate.md](geometry_g18_dat_backed_floor_candidate.md). No build.
**Lesson reinforced:** emit-in-the-floor-view is necessary but **not sufficient** — disambiguate floor from
wall (G16) *and* from scattered decor (here) with the DAT decode (refs + footprint + flatness), not the log
alone. Visual ≠ collision.

**G19 pivot (2026-06-14):** the actual floor `0x801bdc58` is **OBSERVED ONCE / NOT REPRODUCIBLE** (no
conditional BP in DuckStation). Rather than re-hit it, the hunt pivots to the **resource source**: LEVEL01
ships two more parser-format DATs (`LEVEL1.DAT`/`LEVEL2.DAT`) that **contain wide-flat floor payloads** in the
exact `fcn.80010000` format (LEVEL.DAT does not), and the loader parses multiple DATs into the heap — so the
walkable floor is **LIKELY a second parsed DAT**, not necessarily a `.RAW`/`.ALL` runtime conversion. The
static floor shortlist in this doc (§3) was for the *LEVEL.DAT* image only and does not apply to the floor.
Full resource inventory + loader trace + deterministic runtime check:
[geometry_g19_floor_resource_source.md](geometry_g19_floor_resource_source.md).

## 7. Reproduce (read-only)

```bash
python3 tools/survey_level01_payloads.py DAT/LEVEL01_LEVEL.DAT --terrain --top 18
# per-candidate bbox + local Y-band (q25-q75) + which pass-1 entries reference it:
#   walk pass-1 trail rows (TRAIL=0x1504, stride 0x14), bridge row+0x10 -> source,
#   payload = src+0x1c (bit3 flag 0x8) else src+0x14; parse {u32 count; Vertex stride 0xc}.
# G16 wall 0x356bc: flat 0.48, Yband 1354 (least flat).  Floor leads: 0x1f148/0x08f4c/0x17d94 (flat<0.24).
# emit evidence: re-run EXEC 0x800108b4 (fcn.80010000 packet-store gate) while framing the floor.
```
