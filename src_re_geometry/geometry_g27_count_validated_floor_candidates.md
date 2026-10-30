# G27 — count-validated `fcn.80010000` floor/top-surface candidates (consumer-side re-audit)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G26 floor payload re-audit](geometry_g26_floor_payload_reaudit.md) ·
[← G18b DAT-backed `0x2d460` decor](geometry_g18_dat_backed_floor_candidate.md) ·
[← G17 floor candidates](geometry_g17_floor_payload_candidates.md) ·
[← G11 payload format](geometry_g11_payload_format.md)

Status: **STATIC DECODE + CLASSIFICATION of operator-captured `EXEC 0x80010000` payloads (2026-06-15).**
Read-only `DAT/LEVEL01_LEVEL.DAT` (sha1 `b376cb50…`, `0x51418`) decode via
`tools/analyze_g27_floor_candidates.py`. **No patch, no build.** No collision/pathing claims —
**visual floor ≠ collision floor; do not infer.**

> **Headline.** Running the [G26 §4 runbook](geometry_g26_floor_payload_reaudit.md) (PRIMARY `EXEC
> 0x80010000`, `a0` = *raw* payload base, **validate `[a0]` = count**), the operator captured five real
> `fcn.80010000` payloads (A–E) in the Candidate-B floor/top-surface view. **All five pass the §2
> acceptance test** — `[a0]` matches the claimed count exactly (83/48/58/36/25), every vertex `pad==0`,
> every command stream ends in a clean `ffff ffff` terminator — i.e. these are **genuine payloads**, unlike
> the retracted `0x801bdc58` (compressed source, count `0x70d4001a`). **All five are DAT-backed**
> (`P−DATbase ∈ [0,0x51418)`). Decode splits them cleanly: **A/B/C are flat, wide, world-space chunks in a
> single shared Y≈4400–5200 stratum** (floor/top-surface family); **D/E are model-space-centered objects**
> (prop/decor family; E = the G18b `0x2d460` decor, instanced ×93 — reproduced here as a decoder check).
> **Candidate A (`DAT 0x188cc`, count 83, flatness 0.154, Y-band 316, 4502×4502 footprint, unique) is the
> strongest floor/top-surface candidate** — flatter than the entire prior static shortlist (best was e135
> at 0.19), and **DAT-backed → directly editable** (unlike the retracted heap floor). Remaining gap before
> any edit: screen-XY confirmation that A's primitives land on the **walkable lower-center band** (G16
> taught emit-in-frame ≠ floor). See §4 (recommended next experiment) and §5 (contingent edit spec).

> **✓ G28 UPDATE (2026-06-15) — the §5 runbook RAN; Candidate A is runtime-read + projection-confirmed.**
> Operator READ watch on the Candidate A **vertex base `0x801790c8`** hit **repeatedly** in the active render
> path (`a0=0x801790c8`, `ra=0x800206a0`, payload base `a0−4=0x801790c4`, count 83), and **EXEC `0x80010718`**
> (the post-`mfc2 SXY0/1/2` projection site) hit while A was active with **plausible lower/central** screen-space
> SXY (Y≈115–133; e.g. `SXY0=0x007A0164`,`0x007F01A8`). Candidate A is reclassified
> **VALID DAT-BACKED PAYLOAD / RUNTIME READ CONFIRMED / PROJECTION PATH CONFIRMED / LIKELY VISUAL
> FLOOR/TOP-SURFACE / TANGIBILITY UNKNOWN.** The §6 contingent same-size edit
> (`tools/patch_g28_candidate_a_floor_y_test.py`, v16 y @`DAT 0x18992` `89 13`→`89 17`, +1024) was then **built AND
> operator-TESTED**: the tested floor/terrain area **visibly deformed** (caves inward; shifts slightly with view
> angle) in Candidate A's projected area while Flik/objects still rendered — so **Candidate A is now a CONFIRMED
> DAT-backed visual terrain/floor render payload** (not decor/prop). **Collision/pathing did NOT align with the
> deform** (separate or sourced elsewhere; tangibility still UNKNOWN). Full detail:
> [geometry_g28_candidate_a_runtime_confirmation.md](geometry_g28_candidate_a_runtime_confirmation.md).
> Collision/pathing remains **UNKNOWN** — visual terrain ≠ collision/pathing source; do not infer.

## 0. Inputs (operator, count-validated)

EXEC `0x80010000` (`fcn.80010000` entry; `a0` = raw payload base). Common context for all five hits:
`RA = 0x800206a0` (shared emitter tail — same caller for every candidate), `a1 = 0x190` (base OT depth),
`a2 = 0x40`/`0x48` (color/code), `a3 = 0x1f800384` (view context). `DATbase = 0x801607f8`,
`DAT size = 0x51418`. Each `a0 − DATbase` is the DAT offset.

| cand | `a0` (payload base) | DAT off | `[a0]` count (claimed) | screen SXY0/1/2 hint | OTZ |
|------|---------------------|--------:|------------------------|----------------------|----:|
| **A** | `0x801790c4` | `0x188cc` | `0x53`/83 | `0750/0138 0790/012f 0770/0126` | `055c` |
| **B** | `0x80199068` | `0x38870` | `0x30`/48 | `0810/00ee 07d0/0109 07d0/010a` | `0223` |
| **C** | `0x801994a8` | `0x38cb0` | `0x3a`/58 | `0850/0275 07c0/029d 09f0/0332` | `0223` |
| **D** | `0x80198d40` | `0x38548` | `0x24`/36 | `0820/00ca 07b0/00bd 0800/011a` | `0a4f` |
| **E** | `0x8018dc58` | `0x2d460` | `0x19`/25 | (repeated decor; G18b `0x2d460`) | — |

> ⚠ **Do not confuse with `0x801bdc58`.** `0x8018dc58` (Candidate E, DAT `0x2d460`) is a **valid DAT-backed
> payload**. `0x801bdc58` is **invalid compressed LEVEL.RAW source** (G26) — one hex digit apart, entirely
> different. G27 decodes only the five `0x80010000`-captured, count-validated bases.

(The SXY hints above are the GTE `mfc2 SXY0/1/2` values the operator noted with each capture; they are
packed `(X, Y)` screen pairs. They are **suggestive, not decisive** — see §3/§4: classification uses bbox +
coordinate-space + flatness + references + instancing, *not* screen position alone.)

## 1. Layout used (CONFIRMED, G11) + acceptance test (G26 §2)

```
Payload @P:  +0x00 u32 vertexCount=N
             +0x04 Vertex verts[N]  (stride 0xc: s16 x; s16 y; s16 z; s16 pad=0; u32 attr)
             +0x04+N*0xc  primitive command stream  (u16 ctrl; type=ctrl&0x1f; ends at ffff ffff / next payload)
```
Acceptance (§2): `[P]` plausible small positive count **and** verts read as s16 coords with `pad==0` (not
compressed noise). The command stream uses **byte offsets** (multiples of `0xc`) to cite vertices.

**All five candidates pass:** count matches the operator's claim exactly; `pad==0` in 100% of vertices;
each command stream terminates with `ffff ffff` immediately before the next referenced payload; the
halfword scan cites **every** vertex (`refd == N`) → connected meshes, not stray data. The decoder is
further validated by Candidate E reproducing the **committed** G18b decode of `0x2d460` byte-for-byte
(25 verts, footprint 202×107×194, flatness 0.530, **93** source-record references).

## 2. Decoded metrics (CONFIRMED bytes; pristine DAT)

| cand | DAT off | cnt | bbox X (sp) | bbox Y (sp) | bbox Z (sp) | flat=Ysp/max(Xsp,Zsp) | Y q25–q75 (band) | cmd span | verts ref'd | **src refs** | coord space |
|------|--------:|----:|-------------|-------------|-------------|----------------------:|------------------|---------:|-------------|-------------:|-------------|
| **A** | `0x188cc` | 83 | `[5678,10180]` (4502) | `[4368,5063]` (695) | `[4692,9194]` (4502) | **0.154** | 4592–4909 (**316**) | `0x3c0` | 83/83 | **1** (unique) | **WORLD** (large +X/+Y/+Z) |
| **B** | `0x38870` | 48 | `[6547,8304]` (1757) | `[4575,5032]` (457) | `[5075,6755]` (1680) | **0.260** | 4721–4954 (**234**) | `0x1f8` | 48/48 | **1** (unique) | **WORLD** (same Y stratum) |
| **C** | `0x38cb0` | 58 | `[6575,8281]` (1706) | `[4398,5210]` (812) | `[-413,1809]` (2222) | **0.365** | 4662–4939 (**277**) | `0x268` | 58/58 | **1** (unique) | **WORLD** (X/Y match B; Z straddles 0) |
| **D** | `0x38548` | 36 | `[-966,969]` (1935) | `[-5584,-4484]` (1100) | `[-937,937]` (1874) | 0.568 | −5546…−5124 (422) | `0x170` | 36/36 | **1** (unique) | **MODEL** (±~950 centered; far −Y) |
| **E** | `0x2d460` | 25 | `[-103,99]` (202) | `[-107,0]` (107) | `[-97,97]` (194) | 0.530 | −92…−25 (67) | `0x158` | 25/25 | **93** (instanced) | **MODEL** (±~100 centered) |

Vertex-table range = `[off+4, off+4+N*0xc)`; command-stream start = that end; both confirmed in-range with a
`ffff ffff` terminator before the next referenced payload. Full dump:
`python3 tools/analyze_g27_floor_candidates.py DAT/LEVEL01_LEVEL.DAT`.

## 3. Discriminators (NOT screen-visibility alone) and classification

Per the G15/G16 lessons (emit/visibility ≠ role), classification rests on **structure**:

1. **Coordinate space** — A/B/C carry large **positive world-space** coordinates (X,Z in 5–10k, Y in the
   4.4–5.2k band) → **baked terrain chunks placed in world space**. D/E carry small coordinates centered on
   the **local model origin** (±100 to ±950) → **model-space objects placed via a source-record transform**
   = the prop/decor signature. (E's ×93 instancing confirms model-space decor; D is a unique model object.)
2. **Shared Y stratum** — A, B, C all lie in **Y ≈ 4400–5200** → co-planar floor-stratum chunks (a tiled
   ground). D lies at Y ≈ −5500 (a different stratum), E at Y ≈ −100 (model origin).
3. **Flatness + tight IQR** — A (0.154 / band 316) and B (0.260 / 234) clear the G17 floor filter
   (flat < 0.35, band < 900) decisively; C (0.365 / 277) is borderline-flat with a tight core (a few edge
   outliers stretch Ysp to 812 → an edge lip or gentle ramp); D (0.568) and E (0.530) fail flatness.
4. **Instancing** — E is referenced by **93** source records → instanced decor (the G15 high-frequency
   tell). A/B/C/D are each referenced once (drawn once) — consistent with terrain chunks (A/B/C) and a
   unique prop (D).
5. **Connectivity** — every candidate references all N vertices in its command stream → real connected
   meshes (rules out "random bytes that happen to parse").

| cand | classification | confidence | why |
|------|----------------|-----------|-----|
| **A** | **floor / top-surface** | **strong** | flattest of all (0.154) + tightest Y core (316) + widest footprint (4502×4502) + world-space + shared floor stratum + unique. Beats the whole static shortlist (e135 0.19). |
| **B** | floor / top-surface (secondary) | LIKELY | flat (0.260) + tight (234) + world-space + **same Y stratum as A** + unique; smaller footprint (1757×1680) → a smaller floor tile/patch adjacent to A. |
| **C** | floor / top-surface (with relief) | LIKELY | tight Y core (277) + world-space + same X/Y as B (adjacent in Z) + unique; borderline flatness (0.365) and Ysp 812 → floor tile with an **edge lip or gentle ramp** rather than a perfectly planar slab. |
| **D** | **NOT floor** — wall/structural **or** prop | role UNKNOWN | flatness 0.568 + Ysp 1100 (too much vertical relief for a floor) + **model-space centered** + distinct −Y stratum + unique. A compact ~1935×1100×1874 object (boulder/mound/structure/large prop), not a thin floor slab. |
| **E** | **decor** (CONFIRMED) | CONFIRMED | = G18b `0x2d460`: tiny model-space blob (±100), **instanced ×93** → scattered decor/prop, not the walkable floor. |

### 3.1 Candidate A — prioritized (CONFIRMED metrics; floor role LIKELY)
- `DAT 0x188cc`, runtime `0x801790c4`, **count 83**, all `pad==0`, **unique** (1 source-record bridge).
- A thin horizontal slab: **Y spans only 695** (q25–q75 = 316) while **X spans 4502 and Z spans 4502** — a
  wide, near-planar square surface in the world-space Y≈4400–5060 floor stratum.
- **flatness 0.154 is the lowest (flattest) of all five and lower than every prior static floor candidate**
  (G17 best e135 = 0.19; G16 wall `0x356bc` = 0.48). Centroid ≈ (8108, 4747, 6979).
- Command stream `0x18cb4..0x19074` (`ffff ffff` @`0x19074`), span `0x3c0`: opens
  `ctrl=0x0060` (type 0, shade 3), strip element count `0x000a`=10, then byte-offsets `0x0000,0x000c,0x0018,
  0x0024…` = verts 0,1,2,3… — the same strip grammar as the confirmed entry0/E decodes. All 83 verts cited.
- **DAT-backed** (`0x188cc < 0x51418`) ⇒ **directly editable in `LEVEL01/LEVEL.DAT`** — the property the
  retracted heap floor `0x801bdc58` lacked.

## 4. What this changes vs the prior (retracted) floor story

- **G17 Candidate B / G18 conclusion "the walkable floor is NOT a LEVEL.DAT payload" rested entirely on the
  retracted `0x801bdc58`** (G26). With the G26 count-validation fix, the floor-view `EXEC 0x80010000` emit
  **does** surface DAT-backed, flat, world-space floor-shaped payloads (A/B/C). So the "floor not in
  LEVEL.DAT" inference is **no longer supported** and is **downgraded**: at minimum the floor-view renders
  DAT-backed floor-stratum geometry. **UNKNOWN** (and not claimed): whether A is the *walkable* surface vs a
  co-planar visual-only terrain chunk, and whether any LEVEL.RAW-decompressed/generated payload also
  contributes to that view (the operator's capture set here is A–E; it is not proven exhaustive).
- A/B/C are **new** candidates — none is in the prior static shortlist (e135 `0x1f148`, e254 `0x08f4c`,
  e52 `0x17d94`, `0x1b9f0`, `0x10180`). They were surfaced by the *actual floor-view emit*, not bbox ranking
  — and A is flatter than the shortlist's best. (The shortlist remains valid DAT-backed candidates to
  re-test, but A/B/C are the emit-confirmed ones for this view.)

## 5. Recommended next experiment — ONE read-only runtime confirmation (no patch/build)

**Read-only screen-XY confirmation that Candidate A is the lower-center *walkable* floor** (the gate G16
showed is necessary: emit-in-the-floor-view ≠ floor; a wall/ceiling/distant plane in frame also emits).
A is already emit-confirmed at the consumer **entry** and is floor-shaped + DAT-backed; the only missing
piece is *where A's surviving primitives project*.

```
View: stand on / frame the walkable floor (Candidate-B view); Flik centered, floor fills lower-center.
PRIMARY  EXEC 0x800108b4   (packet-store gate; only clip/cull SURVIVORS reach here = on-screen)
   For each hit, filter to Candidate A:  payload = a0 - 4 == 0x801790c4   (a0 == 0x801790c8)
   (DuckStation has no conditional BP — log all hits, keep the a0==0x801790c8 ones.)
   At a kept hit, read the just-written GPU packet at s3: screen-XY at s3+0x00/0x08/0x0c/0x14/0x18/0x20,
   unpack X=low s16, Y=high s16; on-screen iff X∈~0..320, Y∈~0..240.
SECONDARY EXEC 0x80010718  (right after mfc2 SXY0/1/2): read t5/t6/t7 = (Y<<16)|X per projected vertex.
PASS iff A's kept primitives cluster in the LOWER-CENTER band (Y ≳ 130) AND Flik visibly stands on that
   surface. (A wall/ceiling would land in the upper/side band — the G16 failure mode.)
```
Decision: **PASS** → A is a screen-confirmed walkable-floor render payload → proceed to the §6 contingent
edit. **FAIL (upper/side band)** → A is a co-planar wall/backdrop; re-test B then C the same way. Either
way this is read-only and decisive. **Do not** read `t5/t6/t7` at `0x800108b4` (reused packet words there,
per the G16 correction) — read packet memory at `s3` or use `0x80010718`.

## 6. CONTINGENT future edit spec (DEFERRED — NOT the next step; build only after §5 PASSES)

Single-s16, single-byte, reversible Y deform of Candidate A's most-central, multiply-referenced vertex,
to test a **visible bump/spike on the walkable floor**. **Not built, not staged** — gated on §5 confirming
A's primitives land on the floor.

```
file:                 LEVEL01/LEVEL.DAT      (pristine source DAT/LEVEL01_LEVEL.DAT, sha1 b376cb50…, 0x51418)
payload DAT offset:   0x188cc                (Candidate A; runtime 0x801790c4)
vertex index:         v16                    (refs=5 — deforms up to 5 triangles; nearest the XZ centroid,
                                              dist 229 → mid-floor, not a cull-prone edge tip)
field offset:         vertex y (s16)  at DAT 0x18992   (= 0x188cc + 4 + 16*0xc + 2; runtime base 0x80179188,
                                                        y at 0x8017918a)
original bytes/value: 89 13   = 0x1389 = 5001
candidate new value:  +1024 → 6025 = 0x1789                (single byte: 0x18993  13 → 17)
candidate new bytes:  89 17
expected visual:      a sharp ~1024-unit spike protruding from the floor surface near its center (1024 ≈ 3×
                      the floor's tight Y core band 316, and pushes v16 well beyond the existing Y max 5063),
                      deforming the up-to-5 triangles that share v16.
explicit uncertainty: (1) the Y-sign → screen-up/down mapping is UNCONFIRMED — ±1024 both create a clear
                      out-of-plane outlier, so either direction tests visibility; if +1024 over-distorts or
                      clips, fall back to -1024 → 3977 = 0x0f89 (bytes 89 0f, single byte 13 → 0f).
                      (2) A's role is floor-shaped + emit-confirmed-at-entry but NOT YET screen-confirmed as
                      the walkable surface (that is exactly what §5 settles before this edit is justified).
                      (3) collision/pathing impact is UNKNOWN — a visible floor deform says nothing about
                      whether Flik's standing surface moves (visual floor ≠ collision floor).
revert bytes:         89 13   (at DAT 0x18992)
```

Build discipline (when justified): **CREATED in G28** as `tools/patch_g28_candidate_a_floor_y_test.py` with the
same rules as G14–G16 (refuse in-place; verify `0x51418`; verify exact original bytes; write exactly one s16;
print SHA before/after, offset, old/new bytes+value, delta, revert); rebuild via `rebuild_with_patched_dat.py`;
verify the embedded DAT at LBA 2906; restore the staged DAT to pristine; **gitignore artifacts**. The G28
runtime/projection confirmation (§5 gate) is recorded in
[geometry_g28_candidate_a_runtime_confirmation.md](geometry_g28_candidate_a_runtime_confirmation.md);
**the script was built and operator-tested — Candidate A CONFIRMED a DAT-backed visual terrain/floor payload
(visible deform in A's projected area); collision/pathing did not follow (UNKNOWN).**

## 7. Guardrails
No patch, no build, no runtime-address edits. `0x801bdc58` stays **compressed LEVEL.RAW source** (G26) — not
resurrected as a payload. `0x8018dc58` (Candidate E) is a valid DAT payload — do not conflate. Floor role of
A/B/C is **LIKELY (shape + emit-at-entry + DAT-backed)**, not proven walkable until §5. Collision/pathing
**UNKNOWN** — visual ≠ tangible.

## 8. Reproduce (read-only)
```bash
python3 tools/analyze_g27_floor_candidates.py DAT/LEVEL01_LEVEL.DAT
# spot-check A's count + first vertices + central vertex:
python3 -c "import struct;d=open('DAT/LEVEL01_LEVEL.DAT','rb').read();o=0x188cc;\
print('count',struct.unpack_from('<I',d,o)[0]);\
print('v16 y bytes',d[0x18992:0x18994].hex(' '),'=',struct.unpack_from('<h',d,0x18992)[0])"
```
