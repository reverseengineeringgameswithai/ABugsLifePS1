# G16 — screen-space vertex selection (project/reject/pack decode of `fcn.80010000`)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G15 candidates](geometry_g15_terrain_payload_candidates.md) · [← G11 payload format](geometry_g11_payload_format.md)

Status: **VISIBLE WALL RENDER CHANGE CONFIRMED (2026-06-14).** Static ISO decode + runtime runbook
EXECUTED + Candidate EMITTED-PV BUILT + emulator-tested. Result: payload `0x356bc` deforms a **vertical
wall/cliff face, not the walkable floor** → see §9; pivots to G17. No collision/pathing claims (visual ≠
collision).

## 0. Why G16 exists

G12–G15 all ended **VALID BUILD / PATCH LIVE / READ CONFIRMED / NO OBVIOUS VISUAL CHANGE**. G15
additionally confirmed the edited terrain vertex base (`0x80170ba4`) is read by `fcn.80010000` (CPU:
READ hit, PC `0x8001069c` = `lwc2 1,4(t1)`). **Conclusion: "payload metrics + vertex is read" is NOT
sufficient to guarantee a visible change.** A vertex can be read yet its primitive be **rejected**
(backface / off-screen / depth) or project to a **sub-pixel** screen delta. G16 must select a vertex
with **screen-space evidence** — that it projects into the visible area and survives to an emitted
primitive. This phase decodes exactly where that evidence lives and how to capture it.

## 1. `fcn.80010000` project → reject → pack flow (CONFIRMED, case `0x8001068c`)

The per-primitive cases (quad case `0x8001068c` shown; tri/other cases share the shape) do:

| stage | PC | op | meaning | confidence |
|-------|----|----|---------|------------|
| load V0 | `0x80010698` / `0x8001069c` | `lwc2 0,(t1)` / `lwc2 1,4(t1)` | V0 XY (reg0=VXY0) + Z/pad (reg1=VZ0) into GTE; `t1 = a0 + vtxByteOffset` (a0 = payload+4) | CONFIRMED |
| project V0 | `0x800106a8` | **RTPS** (`0x4a180001`) | perspective-transform V0 → SXY0 / SZ | CONFIRMED |
| near-Z reject | `0x800106c0..d0` | `mfc2`+`addi -0x2ee`+`slt`+`beqz 0x800108b8` | reject if V0 depth out of range | CONFIRMED |
| read V0 screen XY | `0x800106d4` | `mfc2 t8, SXY2(reg14)` | t8 = packed screen XY of V0 = `(sy<<16)|sx` | CONFIRMED |
| load+project V1–V3 | `0x800106e0..f8` | `lwc2 2..5` + **RTPT** (`0x4a280030`) | transform 3 more verts → SXY0/1/2 | CONFIRMED |
| **read screen XY** | `0x80010710` / `0x80010714` / `0x80010718` | `mfc2 t5,SXY0(12)` / `mfc2 t6,SXY1(13)` / `mfc2 t7,SXY2(14)` | **t5/t6/t7 = packed screen XY of the 3 RTPT verts** (each `(sy<<16)|sx`) | CONFIRMED |
| backface | `0x8001071c` / `0x80010770` | **NCLIP** (`0x4b400006`) → `mfc2 MAC0(24)` → `bgez/bgtz 0x800108b8` | cross-product sign reject (back-facing) | CONFIRMED |
| screen bounds | `0x800106fc`, `0x80010744..84` | `sltiu …,0x200`, `sltu …,0xf00000`, `or`, `beqz 0x800108b8` | reject if projected X/Y outside the screen window | CONFIRMED |
| OT depth | `0x80010790` | **AVSZ4** (`0x4b68002e`) → `mfc2 OTZ(7)` → range/`otmax` rejects (`0x800107b8/c4`) | average-Z for ordering table; reject if out of OT range / buffer full | CONFIRMED |
| **EMIT (survived)** | `0x80010824` … `0x800108b4` | `sw` block into packet `s3`; screen XY stored at `s3+0x08/0x14/0x20/0x2c` and `s3+0x00/0x0c/0x18`; UV/color `sh s3+0x24/0x30`; OT link `sw …(t9)`; `addi s3,s3,0x34` | **packet written ⇒ primitive is drawn** | CONFIRMED |
| skip (rejected) | `0x800108b8` | `bnez s2,0x8001068c` (next strip elem) | primitive NOT drawn | CONFIRMED |

So **every reject path jumps to `0x800108b8`** (skip), and the **only way to the packet store at
`0x80010824`** is to survive near-Z + backface + screen-bounds + OT-depth tests. Reaching the store =
the primitive is emitted and on-screen.

### Screen-coordinate registers (CONFIRMED)
- `t5 = SXY0`, `t6 = SXY1`, `t7 = SXY2`, `t8 = SXY of V0` — each a packed 32-bit `(screenY<<16)|screenX`,
  both halves **signed 16-bit**. Unpack: `screenX = (w & 0xffff)` as s16; `screenY = (w >> 16)` as s16.
- `s3` = live GPU primitive-packet cursor (advances by `0x34` per emitted poly; runtime region seen
  ~`0x801cc5xx` in the G10 dispatch snapshot).
- `a0` = payload pointer for the object currently being emitted (identifies which mesh).

## 2. Screen-space capture method (ISO-identified; one narrow GUI breakpoint)

Authoritative "is this primitive on-screen, and where":

> **Execute breakpoint at `0x800108b4`** (`addi s3,s3,0x34`, the moment a packet has been fully
> written, past *all* reject branches). At each hit:
> - read **`a0`** → payload pointer (which object; map to DAT via `a0 − 0x801607f8`),
> - read the just-written packet at **`s3`** (the base before the add): screen-XY words at
>   `s3+0x00, s3+0x08, s3+0x0c, s3+0x14, s3+0x18, s3+0x20` — unpack each to (X,Y),
> - a primitive is **on-screen** iff its X/Y land in the visible window (≈ `0..320` × `0..240`).

This directly captures emitted, on-screen primitives and their pixel coordinates — something **static
DAT analysis cannot derive** (it depends on the runtime camera matrix + player position). Avoid broad
RAM dumps; this is a single BP + a few register/packet reads.

Alternative (coarser): BP at `0x80010824` (entry of the emit block) and read `t5/t6/t7/t8` (the SXY
registers) directly. Cleaner to read packet memory at `0x800108b4`, since intermediate regs may be
reused.

## 3. Why G15 was silent (LIKELY)

The G15 watch hit at `0x8001069c` (`lwc2`) — **before** the reject tests — so it only proved v46 was
*loaded*, not that its primitive *survived* to the packet. v46's primitive may have been backface/
screen-bounds/OT rejected in the tested view, OR projected to a sub-pixel delta, OR v46 was on a part
of the surface off the visible frame. G15 does not disprove the payload path; it shows read-confirmation
is insufficient — screen-space confirmation (§2) is required. CONFIRMED that vertex-read ≠ visible.

## 4. G16 recommendation — screen-space-confirmed vertex (RUNBOOK; no build yet)

No vertex can be selected with screen-space evidence from static data alone, so **G16 = runtime
identification first**, then edit the confirmed vertex. Minimal runbook:

1. Boot the **pristine** image; enter LEVEL01; frame the ground/terrain to modify (the G15 ground area).
2. Execute BP at **`0x800108b4`**. For each hit while the target ground fills the view, log:
   - `a0` (payload pointer) and `a0 − 0x801607f8` (DAT offset),
   - the packet at `s3`: the 3–4 screen-XY words (unpack X = low s16, Y = high s16).
3. Keep hits whose screen XY are **central / large on screen** (clearly visible) AND whose `a0` maps to
   a **terrain** payload (wide+flat per `tools/survey_level01_payloads.py`; e.g. `0x10180`/`0x80170978`
   confirmed drawn in G15, or another wide payload that shows up here).
4. For a chosen emitted primitive, read its source vertex byte-offsets: at the case body, the offsets
   come from `lh [s0+2/4/6 …]`; `vertex addr = a0 + offset`; `vertex index = (addr − (a0)) / 0xc`
   (note `a0` here is already payload+4). Map the vertex to its DAT coordinate offset.
5. That vertex is the **G16 screen-space-confirmed target**: edit one s16 coord (Y for a vertical
   spike), moderate–large delta (e.g. `±1024`), single byte where possible, reversible. Re-verify with
   the same `0x800108b4` BP that the patched coordinate changes the logged screen XY.

Confidence: the BP/registers/packet layout are **CONFIRMED**; which specific emitted primitive is the
best visible target is **runtime-dependent (UNKNOWN until the log is taken)**. **Visual terrain ≠
collision** — do not infer collision from any subsequent edit.

## 6. RUNTIME emitted-primitive log — RESULT (2026-06-14)

Operator ran the §4 runbook: pristine image, standing in visible terrain/ground view, EXEC
`0x800108b4`. At `0x800108b4` (`addi s3,s3,0x34`), `a0` = the **vertex-table pointer** (= payload+4),
so **payload base = `a0 − 4`**; `s3` = packet/output pointer being advanced by `0x34`.

| hit | a0 | payload base (a0−4) | DAT off | s3 (packet) | note |
|----:|----|---------------------|--------:|-------------|------|
| 1 | `0x80195eb8` | `0x80195eb4` | `0x356bc` | `0x801e9150` | payload 0x356bc (= static e128) |
| 2 | `0x80195eb8` | `0x80195eb4` | `0x356bc` | `0x801e9184` | |
| 3 | `0x80195eb8` | `0x80195eb4` | `0x356bc` | `0x801e9288` | |
| 4 | `0x80195eb8` | `0x80195eb4` | `0x356bc` | `0x801e92bc` | |
| 5 | `0x80195eb8` | `0x80195eb4` | `0x356bc` | `0x801e92f0` | |
| 6 | `0x8017c1ec` | `0x8017c1e8` | `0x1b9f0` | `0x801e9958` | secondary payload |
| 7 | `0x8017c1ec` | `0x8017c1e8` | `0x1b9f0` | `0x801e998c` | |

**CONFIRMED:** `fcn.80010000` reached the emitted-primitive path; **payload `0x356bc` (DAT, rt
`0x80195eb4`) emitted ≥5 primitives** in the visible terrain view (first command = a 14-element type-0
quad strip; hits 1–5 = its first quads, verts 0–19), and **payload `0x1b9f0` (rt `0x8017c1e8`)** emitted
≥2. These are **screen-space/emitted candidates** — stronger than G15's vertex-read-only payload.

**`a0`-at-`0x800108b4` correction (CONFIRMED):** at this PC `a0` is the **vertex-table pointer**
(payload+4), not the raw payload pointer (the function's early `addi a0,a0,4` already ran). So payload
base = `a0 − 4`. (At `fcn.80010000` *entry* `0x80010000`, by contrast, `a0` = raw payload pointer.)

**`t5/t6/t7` correction (CONFIRMED — supersedes §2's coarse alternative):** at `0x800108b4`,
`t5/t6/t7` do **NOT** hold clean SXY. The logged values unpack to impossible screen coords (e.g. hit1
`t5=0x0c1e7c08` → X=31752, Y=3102; `t6=0x3ffdff40` is a constant GPU packet header word). The emit
block (`0x80010824`/`0x80010880`+) **reuses** t5/t6/t7 for packet/color/OT-link words. **To read clean
screen XY, read the packet memory at `s3` (offsets `+0x00/0x08/0x0c/0x14/0x18/0x20`), or set the BP at
`0x80010718` (right after `mfc2 SXY0/1/2`).** Mapping the logged `t5/t6/t7` to pixels = **TODO** (do
not invent precision). The decisive evidence is the **payload pointer + `s3` advance**, which is solid.

## 7. G16 SELECTED TARGET — Candidate EMITTED-PV (BUILT 2026-06-14, test PENDING)

Decode of payload **`0x356bc`** (the primary emitted payload; = static e128):

| field | value |
|-------|-------|
| count | 230 verts |
| vertex table | `DAT 0x356c0` |
| command stream | `DAT 0x36188 .. 0x3676c` (1508 B) |
| first command | `0x36188` ctrl `0x0060` (type 0, quad strip), `s2`=14 elements → verts 0–55 |
| bbox | X `[-6331,-493]` (5838), Y `[5093,8332]` (3239, ground stratum), Z `[3107,9807]` (6700) |
| refs | all 230 verts referenced (374 total) |
| role | terrain/ground render — **LIKELY** (wide+flat, positive-Y ground stratum, emit-confirmed) |

Selected vertex = **v10** (in the observed-emitted first-command quads, near their X/Z centroid;
strongest screen-space evidence):

| item | value |
|------|-------|
| vertex | payload `0x356bc` **v10**, xyz `(-2155, 6841, 4768)` |
| field | v10 `y` (s16) |
| DAT offset | `0x3573a` (runtime `0x80195f32`; vertex base `0x80195f30`) |
| original | `b9 1a` = `6841` |
| patched | `b9 16` = `5817` (delta `-1024`) |
| revert | `b9 1a` |
| changed bytes | exactly one (`0x3573b`, `1a→16`) |
| rationale | central vertex of an actually-emitted (hits 1–5) ground quad; `-1024` lifts it a clear bump above its local quad (neighbors v8/v9/v11 ≈ 6235–6666) while staying on-screen (a larger delta risks the spike projecting off the top → screen-bound reject) |
| patch cmd | `python3 tools/patch_g16_emitted_payload_vertex_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G16_EMITTED_PAYLOAD_VERTEX_TEST.DAT` |
| patched DAT SHA256 | `96206e690722dabc8a329a2125c4313a6e5d710730d39b67ae445102453886ae` (sha1 `4c638f61…`) |
| rebuild cmd | `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G16_EMITTED_PAYLOAD_VERTEX_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.bin --out-cue ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue --report DAT/LEVEL01_LEVEL_G16_EMITTED_PAYLOAD_VERTEX_TEST_REBUILD.md --write` |
| image | `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue` / `.bin` |
| embedded verify | LBA `2906`, embedded sha1 `4c638f61…` == patched DAT (PASSED); `@0x3573a`=`b9 16` |
| staged restore | `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine (`786b7a96…`) |
| artifacts | DAT/BIN/CUE/report gitignored, NOT committed |

**Operator test:** boot `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue`; enter LEVEL01; return to the
runtime-log ground view; compare to pristine **with breakpoints disabled / gameplay running**; look for
a bump/peak on the ground surface (vs no change / crash). CPU confirm (optional): READ aligned vertex
base `0x80195f30` → hit in `fcn.80010000`; live `0x80195f32` = `b9 16` (`5817`). If still subtle,
escalate v10.y to `-2048` (`b9 12`, `4793`, below the surface min → spike above the whole surface;
slight risk of projecting off the screen top). **Do not infer collision/pathing — visual terrain ≠
collision.**

## 9. VISUAL RESULT (operator, 2026-06-14) — VISIBLE WALL RENDER CHANGE

Image tested: `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue` (payload `0x356bc` v10 `y`,
`DAT 0x3573a` `b9 1a`/6841 → `b9 16`/5817, delta `-1024`; runtime inner coord `0x80195f32`, aligned
vertex base `0x80195f30`).

| check | result |
|-------|--------|
| boots / title | yes |
| LEVEL01 loads | yes |
| crash | no |
| black screen | no |
| visible deformation | **yes** |
| affected geometry | **vertical wall / cliff face — NOT the walkable floor/top surface** |

**Classification: VALID BUILD / PATCH LIVE / EMITTED PAYLOAD CONFIRMED / VISIBLE WALL RENDER CHANGE.**
(Prior runtime evidence was stronger than read-only: EXEC `0x800108b4` confirmed payload `0x356bc`
emitted multiple primitives after projection/reject checks while viewing terrain.)

**CONFIRMED:**
- Payload vertex edits can visibly deform **terrain-family** render geometry (first such result; G14 was
  grass/decor).
- Payload `0x356bc` is screen-space/emitted and visibly editable.
- Payload `0x356bc` is **wall / vertical terrain face, not floor/top-surface** —
  **RECLASSIFIED** from the G15/G16 "terrain/ground (LIKELY)" guess. Its local Y band (q25–q75 = `1354`)
  and flatness `0.48` (the least-flat of the static shortlist) are consistent with a vertical face.

**Method validation:** the screen-space gate (`0x800108b4`) correctly picked an *emitted, visibly
editable* vertex (unlike the read-only G15 pick). But **emit-in-the-ground-view is necessary, not
sufficient** to mean "floor": a wall in the camera frame also emits. G17 adds a floor filter (flat shape
+ tight local Y band + the primitive's screen-XY lands on the walkable floor).

**UNKNOWN (do not infer):** collision/pathing impact; the walkable floor/top-surface render payload;
whether any visual floor payload is coupled to collision. **This is NOT a floor collision edit.** Visual
terrain ≠ collision.

**G16 succeeded as a visible render edit, but not as a walkable-floor target.** → continue in
[geometry_g17_floor_payload_candidates.md](geometry_g17_floor_payload_candidates.md). Do **not** continue
editing `0x356bc` unless the goal is wall/cliff deformation.

**G17/G18 follow-up (2026-06-14):** re-running this same `0x800108b4` gate while framing the **walkable
floor** (G17 Candidate B) returned a single payload at runtime `0x801bdc58` — **past LEVEL.DAT EOF**
(`0x801b1c10`), in the "next resource" heap region. So the walkable floor is a **runtime/output-buffer
payload, not a LEVEL.DAT payload** (no LEVEL.DAT vertex edit moves it). The `0x800108b4` screen-space gate
remains the right discriminator; it revealed that the floor is sourced differently from the wall/grass DAT
payloads. Trace + runbook:
[geometry_g18_output_buffer_floor_trace.md](geometry_g18_output_buffer_floor_trace.md).

**Third emit-confirmed-but-not-floor case (2026-06-14):** a *near-floor* re-log of this same `0x800108b4`
gate emitted a **DAT-backed** payload `a0=0x8018dc5c` → DAT off `0x2d460` (VALID). Static decode = 25-vert
closed blob, footprint 202×107×194, flatness 0.53, **93 pass-1 references → instanced decor/prop, not the
floor** ([geometry_g18_dat_backed_floor_candidate.md](geometry_g18_dat_backed_floor_candidate.md)). So the
`0x800108b4` gate has now surfaced **three** emit-confirmed payloads in ground views — a wall (`0x356bc`), the
heap floor (`0x801bdc58`), and instanced decor (`0x2d460`) — confirming again that **emit-in-the-ground-view
is necessary but not sufficient** for "floor". The DAT decode (refs + footprint + flatness) is the decisive
floor/wall/decor discriminator, not the emit log alone.

## 8. Reproduce (read-only)

```bash
# project/reject/pack decode of the G15-hit case:
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8001068c -c 'pD 0x23c' SCUS_942.88
# GTE opcodes: RTPS 0x4a180001 @0x800106a8; RTPT 0x4a280030 @0x800106f8;
#              NCLIP 0x4b400006 @0x8001071c/70; AVSZ4 0x4b68002e @0x80010790
# screen XY: mfc2 SXY0/1/2 (regs 12/13/14) -> t5/t6/t7 @0x80010710/14/18
# emit gate: packet store block 0x80010824..0x800108b4 (all rejects -> 0x800108b8)
```
