# G30 — Visible walkable-terrain ("dirt") render-source discovery + matched floor edit

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G29 collision source (LEVEL.RAW)](geometry_g29_collision_source_plan.md) ·
[← G4 render consumers](geometry_render_consumers.c)

**Status (header corrected 2026-06-22): R1 DONE · R2 DONE · R3 DONE · R5 DONE (§17) · R6 core ACHIEVED (§15).** Render-subsystem RE sub-project — multi-step. *(The old top line "R3 IN PROGRESS" (2026-06-16) contradicted §§15/17 below, which record R5 DONE and R6 core achieved; retained here only as history. Cross-check §12+ and the per-phase notes for the authoritative per-step state.)*
Live-debug (DuckStation external debugger) + static (r2). **KEY RESULT (see §12): the bulk visible ground is drawn by
a `0x80022–0x80025` emitter layer that calls `0x80060xxx` libgte transform leaves — a path ALL prior work missed; the
neutralize method that drove §10/§11 is structurally blind to it (camera-lock confound, §12.1). Discovery is now by
move-test (shift source-vertex Y → see geometry move).** **§14: R2/R3 RESOLVED — the visible terrain SURFACE,
including the walkable ground, is rendered by `fcn.800172dc` from the PERSISTENT, EDITABLE buffer `0x8012c/0x8012d`
(GP0 0x3C quads; Y-deform + X-shear both proven visible). The leaf-callers draw props/shadow, not the ground. §13's
"staged ground" was a bottom-clipping artifact (CORRECTED).** Visual and collision are INDEPENDENT (collision = G29
sector table `0x800a7e48`). **§15: R6 core ACHIEVED — both floor levers confirmed editable and a matched
visual+collision lower lands Flik coincident on the lowered floor (consistency proven). The dramatic "visible pit"
single-shot is camera-follow-confounded (uniform ground + camera-follows-Y → uniform lowers are invisible) and needs a
LOCALIZED edit — best finished with the proposed diff/snapshot + GTE-trace API.** **§17: R5 DONE — terrain on-disk
source = LEVEL01/LEVEL.RAW chunk 35 (file off 0x9908a, compressed → decompressed by fcn.8001a1dc to 0x8012c;
runtime-confirmed via new accessLog/transferLog; disc LBA 1823–4149).**

---

## 1. Objective

Find **how the visible walkable dirt terrain is rendered** (the ground Flik stands on *everywhere*, in world
space) and locate its **editable geometry source**, so we can edit the VISIBLE floor to **match a collision edit** —
the end goal: **Flik falls and lands on a visibly-lowered floor on flat ground** (a consistent visual+collision floor
edit). This completes the thread G28 (visual deform) + G29 (collision source = LEVEL.RAW) opened.

---

## 2. Why this is needed (the gap)

- **G28** proved the LEVEL.DAT *visual* floor (Candidate A) deforms but collision didn't follow.
- **G29** (this session) found the **collision/floor source = LEVEL.RAW** (decompressed → sector table → plane
  records → resolver → player Y) and proved the **collision edit** (Flik's footing moves 1:1, RAM, reliable).
- But the **visible walkable dirt** Flik stands on *everywhere* is **world-space terrain** rendered by a path we
  have NOT identified — it is **not** the LEVEL.DAT object payloads. So we can edit *collision* and we can edit one
  *visual tile* (Candidate A), but not the **bulk visible floor**. G30 closes that gap.

---

## 3. Established facts (2026-06-15/16) — CONFIRMED unless noted

**Collision (G29, carried forward):**
- Source CONFIRMED = **LEVEL.RAW** (compressed) → `fcn.8001a1dc` decompress → `0x800F7xxx` → **sector table
  `0x800a7e48`** (count `[gp+0x508]`≈223; `0x30`-byte recs; origin `+0/+4/+8`, block ptr `+0x10`) → **plane records
  `0x800D0xxx`** → resolver `fcn.800345cc` (swept plane-distance clamp, stop-with-skin `−0xc0`) → commit
  `0x80036cec` → **player Y `0x800a6504`**.
- Collision EDIT works in RAM: lowering the sector origin moves Flik's footing ~1:1; **kill-plane limit** (~≤8000
  relative, beyond which Flik falls through and dies).

**Visible dirt (this session, the G30 target):**
- The walkable dirt is **world-space** (player Y ~`−106000`s), under Flik everywhere.
- **NOT the `fcn.80010000` object payloads** — CONFIRMED by spike + clean-uniform-shift tests on **two different**
  emitted-payload sets, and by toggling Candidate A (no change to the flat dirt). The object payloads are
  walls/props/decor/special-tiles in a **different (DAT/model) coordinate space**.
- **NOT reached via the collision sector record** (its only pointer is `+0x10` = the collision-plane block).
- **Candidate A** (DAT `0x188cc`, payload `0x801790c4`, vbase `0x801790c8`, count 83, DAT-space Y `~4368–5063`)
  **IS an editable visible floor TILE** — a clean uniform Y lower renders **stably** (operator image #2) — but only
  *at its location* (a natural-dip area). It is **one tile**, not the bulk dirt.

**Render architecture (G4/G10/G11 + this session):**
- Driver **`fcn.800224ec`** (G4) → `fcn.8003f938` (render loop), `fcn.80017b98` (GTE matrix ×2), trail helpers
  `fcn.800140a0` / `fcn.80014360` / `fcn.800146e0`.
- Survivor builders `fcn.8001ea6c` / `fcn.800206e8` → **object emitter `fcn.80010000`** (per-vertex `lwc2`;
  packet-store gate `0x800108b4`; SXY site `0x80010718`). OT base `[0x8008240c]` (`gp+0x674`).
- **GTE RTPS/RTPT renderer FAMILY** spans **`0x80010000`–`0x8001a120`** (+ `0x80060xxx` leaves) — many geometry
  draw functions. `fcn.80010000` = objects. **The dirt is LIKELY drawn by a different member of this family.**
- **G6 CONFIRMED:** patching `DAT+0x1526` (pass-1 trail sentinel, read by `fcn.800140a0` @`0x80014170`) made
  standing terrain/ground render mostly disappear → **the trail/pass-1 path GATES terrain visibility** (but terrain
  is NOT drawn via the survivor→`fcn.80010000` path — that path is objects).

**Engine behavior (important for method):**
- The renderer **caches transformed geometry**: a runtime RAM edit to geometry needs **camera movement** to refresh
  before it shows. **Clean uniform edits render stably; degenerate spikes flicker** (and are hard to screenshot).
- **Blind RAM corruption of the decompressed/collision region CRASHES** (pointer-rich) — corruption sweeps are NOT a
  safe discovery method. Use read-watches / targeted clean edits instead.

---

## 4. Tools & setup

- **DuckStation external debugger** (JSON-RPC `127.0.0.1:2346`): `getRegisters`, `readMemory`/`writeMemory`
  (`writeU8/16/32`), `disassemble`, breakpoints (`execute`/`read`/`write`), `stepInstruction`/`runUntilAddress`,
  **controller input** (`setControllerState`/`pressButton`/`advanceFrames`), **`captureFrame`** (PNG),
  `saveState`/`loadState`. **No game-disc-load** (load a new image manually, once; save states are disc-specific —
  a state carries its DAT/RAM).
- **Driver:** `/tmp/abl_dbg.py` (DebuggerClient wrapper; helpers: `regs`, `mem`, `dis`, breakpoints, `captureFrame`,
  payload/range edits, vertex decode). Run from `/tmp` (cwd resets to repo between calls).
- **Static:** r2 on `SCUS_942.88` — `r2 -a mips -b 32 -e scr.color=0 -qc 'om 3 0x80010000 0x72800 0x800 r-x; pd N @ ADDR'`.
- **Save states** (`~/.local/share/duckstation/savestates/`): `SCUS-94288_1.sav` (gameplay), `_2.sav` (pre-load,
  `[0x800a7e48]=0`), `_5/_6.sav` (Candidate A lowered + positioned). Backups: `_1_copy/_2_copy/_3_copy.sav`.
  **`SCUS-94288_g30_openground.sav` = the G30 working state: Flik on open, flat, fence-free walkable dirt with an
  unobstructed view of the ground (operator-made; renamed out of slot `_7`). USE THIS for all G30 ground work — the
  slot-6 fence confounds every pixel-diff. Also the intended R6 screenshot spot (flat open ground).**
- **Validation:** `captureFrame` → Read the PNG (visual) **and** numeric (player Y `0x800a6504`, projected SXY).

---

## 5. Phased plan (R1 → R6)

### Phase R1 — Map the render driver call tree (STATIC, safe)
- **Goal:** enumerate `fcn.800224ec`'s calls and order; produce a shortlist of candidate **terrain-draw** functions
  (members of the GTE family that are NOT `fcn.80010000`/object path).
- **Method:** r2 disasm `fcn.800224ec` and `fcn.8003f938`; list `jal` targets; classify setup vs geometry-draw;
  note draw order (background/ground is typically drawn *before* objects). Map which GTE-family functions
  (`0x80011xxx`–`0x8001axxx`) the driver reaches that aren't the survivor/object path.
- **Deliverable:** a call-tree map + a **shortlist (≤5)** of plausible terrain renderers.
- **Promotion → R2:** a concrete shortlist with addresses.

### Phase R2 — Identify the terrain renderer at runtime (LIVE, safe)
- **Goal:** which function draws the **big dirt polygons**.
- **Method (no corruption):** from a clear flat floor view (e.g. slot 6), set **EXEC** breakpoints on the shortlist
  functions' packet-store / `mfc2 SXY` sites; at each hit read the **projected screen-XY** and the **source vertex
  pointer**. The terrain renderer emits **large polygons covering the lower screen** (many big triangles), drawn
  before the `fcn.80010000` objects. Cross-check with the G6 `DAT+0x1526` gating (the gated path leads to terrain).
  Alt: break at `fcn.800224ec`, `runUntilAddress` through one frame, log the call sequence; terrain precedes objects.
- **Deliverable:** the terrain renderer function + its **per-vertex read PC**.
- **Promotion → R3:** SXY of its polygons confirmed to land on the on-screen ground.

### Phase R3 — Trace renderer → geometry source buffer (LIVE, safe)
- **Goal:** the terrain **vertex buffer base** + format.
- **Method:** at the per-vertex read PC, capture the **source pointer** (buffer base) — exactly how we found
  Candidate A's vbase and the collision `0x800F7xxx`. Classify the region: LEVEL.RAW-decompressed
  (`0x800Bxxxx–0x8015fcbc`) / DAT / generated. Determine **vertex format** (stride, Y field) and **coordinate space**
  (world vs sector-relative + transform; recall collision used sector-origin + `×32` sector-relative).
- **Deliverable:** terrain geometry buffer base + vertex format + coordinate mapping (DAT/grid → world).

### Phase R4 — Confirm editability (LIVE — read-only, then ONE safe clean edit)
- **Goal:** prove the buffer drives the dirt; find the **edit lever**.
- **Method:** READ-watch the buffer during render (confirm it is the source). Then a **clean uniform Y edit** of a
  small contiguous part (NOT a spike; NOT pointer fields); **walk Flik** to refresh the render cache; `captureFrame`;
  confirm the dirt visibly moves. Calibrate the buffer-Y → world-Y scale.
- **Deliverable:** confirmed editable terrain buffer + Y lever (offset/stride/scale).
- **Guardrail:** clean uniform edits only; move Flik before judging (cache); never touch pointer/count fields.

### Phase R5 — On-disk source (LIVE, for a permanent patch)
- **Goal:** where the terrain geometry comes from on disk.
- **Method:** from the **pre-load** state (slot 2), **WRITE-watch** the terrain buffer through the level load →
  capture the writer PC (LEVEL.RAW decompressor `fcn.8001a1dc`? a different loader?) → map to **LEVEL.RAW** chunk +
  offset (same technique that pinned the collision source).
- **Deliverable:** on-disk source (LEVEL.RAW chunk + offset, or a sidecar) + compressed/literal note.

### Phase R6 — Matched visual + collision floor edit (PAYOFF)
- **Goal:** the screenshot — **Flik falls and lands on a visibly-lowered floor, on FLAT open ground.**
- **Method:** pick a **flat, open** spot (no natural dip — the dip confounds, per this session). Lower **both** the
  terrain visual buffer (R4 lever) **and** the collision sector origin (G29 lever) by **matched world amounts**;
  calibrate by screenshot + player Y so the visible floor and Flik's footing coincide; trigger a minimal fall
  (2 frames input is enough; Flik falls in place); `captureFrame`.
- **Deliverable:** the clean "consistent lowered floor under Flik" screenshot. (Optionally then the permanent
  LEVEL.RAW patch using R5.)
- **Guardrail:** respect the collision kill-plane limit; flat spot to avoid the dip confound.

---

## 6. Guardrails

- **No blind corruption sweeps** (they crash — pointer-rich regions). Discovery = read-watches / call tracing;
  edits = clean, targeted, non-pointer.
- **Clean uniform geometry edits only** (no spikes → flicker). **Move Flik to refresh** the render cache before
  judging a visual edit.
- **Collision lowering:** stay within the kill-plane limit (~≤8000 relative) or Flik dies mid-fall.
- **Save-state hygiene:** never overwrite the provided states; back up new ones; remember save states are
  disc-specific (carry their own DAT/RAM snapshot).
- **Do not commit generated artifacts** (DAT/BIN/CUE/RAM/PNG/save states). Docs/analysis only. Leave `G28_Deformity`
  unstaged.
- **CONFIRMED / LIKELY / UNKNOWN / TODO** on every claim. **Visual ≠ collision.**

---

## 7. Coordinate-space & render-cache notes

- **Two spaces:** object/visual payloads (Candidate A) are in DAT/model space (Y `~+5000`); the player + collision
  are world space (Y `~−106000`). They coincide only at render via the camera transform. The **bulk dirt is in the
  player's world space** (it's the ground he walks on), so its geometry/buffer is the world-space side — pairs
  naturally with the collision (same space), which is *why* R6's matched edit should calibrate cleanly once R3 gives
  the format.
- **Render cache:** transformed geometry is cached; a static RAM edit shows only after the object re-transforms
  (camera/Flik movement). Always `advanceFrames` with a little input before capturing.

---

## 8. Next action

**Phase R3 (live, after DuckStation restart + reload slot 6):** finish the move-test on bulk-ground caller
`0x80022c4c` (and `0x8002574c`/`0x80025bd8`) — BP its own jal `0x80022c44`, collect per-primitive base `v1`
(verts at v1+8/+16/+24), shift Y, walk, `captureFrame`; the caller whose ground visibly moves is the bulk dirt.
Then capture its source buffer + format (R3 deliverable) and trace to LEVEL.RAW (R5). (Historical R1/R2 shortlist
below is superseded by §12 — the dirt is NOT in the `0x8001xxxx` family.)

---

## 9. R1 RESULT (2026-06-16) — render call tree mapped; terrain renderer narrowed to 6 emitters (STATIC, r2)

Disassembled the render driver `fcn.800224ec` and its callees (r2, `SCUS_942.88`). Call order of the driver:

```
fcn.800224ec (driver):
  0x800225d0  jal fcn.8001dfe4   <== SCENE-GEOMETRY DISPATCHER (before objects)   *** PRIME terrain renderer ***
  0x800225e4  jal fcn.8003f938   render loop (GTE-leaf orchestration only; NOT geometry)
  0x80022614  jal fcn.80017b98   GTE matrix setup
  0x8002262c  jal fcn.800140a0   trail CULL (G4/G6; gates terrain via DAT+0x1526) -> builds survivor lists
  0x800226a8  jal fcn.8001ea6c   survivor builder ----\
  0x800226c4  jal fcn.80027004   POST-OBJECT pass (26x fcn.8001881c)   *** secondary terrain candidate ***
  0x800228c0  jal fcn.800206e8   survivor builder ----/  both -> fcn.80010000 (OBJECTS; ruled out for dirt)
```

**CONFIRMED (static):**
- **`fcn.8001dfe4` = scene-geometry draw dispatcher** — called once at `0x800225d0`, BEFORE the object path. 34 jals;
  fans out to **5 GTE geometry emitters (all verified to contain RTPS/RTPT):**
  `0x80014b04`, `0x80014ee0`, `0x800153d0`, `0x800163e0`, `0x800172dc`
  (plus matrix/setup leaves `0x800146e0`/`0x8001474c`/`0x8001478c`/`0x80017b98`/`0x80060484`/`0x800605c4`, and
  data-setup `0x8005ec84`/`0x8002d64c`/`0x8002b424`/`0x80030018`/`0x8003043c`). The **bulk dirt is one (or more) of
  these 5 emitters** — it's drawn here, before objects, which matches "ground first."
- **`fcn.80027004` = post-object pass** — called at `0x800226c4`/`0x80022744`; calls `0x8001881c` **26×** (a repeated
  emitter → possibly tiled ground / a second geometry layer / overlay). SECONDARY candidate.
- **RULED OUT** (no geometry emit; GTE-leaf/OT orchestration only): `fcn.8003f938` (render loop — only libgte leaves
  `0x800605c4`/`0x80060594`/`0x800605f4`/`0x800606a4`), `fcn.80022978`, `fcn.8003df98`, `fcn.8003efc8`, `fcn.80023abc`.

**R2 shortlist (6 emitters to EXEC-BP):** `0x80014b04`, `0x80014ee0`, `0x800153d0`, `0x800163e0`, `0x800172dc`
(under the pre-object dispatcher `fcn.8001dfe4`), and `0x8001881c` (under the post-object pass `fcn.80027004`).
Their RTPS/RTPT transform sites (for breakpoint placement) fall in `0x80014c6c..0x800174bc` (the
`0x80014b04`–`0x800172dc` span) and `~0x80018xxx` (for `0x8001881c`).

Search space cut from the whole GTE family (`0x80010000–0x8001a120`) to **6 functions**. → Phase R2.

---

## 10. R2 RESULT (interim, 2026-06-16) — dirt = a separate "background" layer; exact renderer not yet pinned (cache-confounded)

**Method:** neutralize a candidate function (write `jr ra; nop` at its entry — clean no-op, reversible via `loadState`),
walk Flik, `captureFrame`; whatever **vanishes** is what that function drew. Run from slot 6 (flat-floor view).

**CONFIRMED — what specific functions draw (each vanished when neutralized):**
- `0x80014b04` = **the PLAYER (Flik)** model emitter.
- `fcn.800206e8` = the **dark mound / structure**.
- `fcn.8001ea6c` = **foliage / decor** (orange leaves).
- `0x8001881c` (under `fcn.80027004`) = a **top-screen / sky background effect** (neutralizing left top garbage).
- `fcn.80010000` (object emitter): neutralizing did **not** remove the dirt → **dirt is not via the object emitter**.

**RULED OUT as the dirt renderer** (the flat dirt persisted when each was neutralized): the 6 R1 emitters
(`0x80014b04/ee0`, `0x800153d0`, `0x800163e0`, `0x800172dc`, `0x8001881c`), `fcn.80010000`, `fcn.8001dfe4`,
`fcn.8003f938`, `fcn.80027004`, `fcn.800206e8`, `fcn.8001ea6c`, `fcn.800212fc`, `fcn.800253e8`, `fcn.8003df98`, the
**6 pre-driver scene calls** (`0x80045a60`, `0x80043500`, `0x8005044c`, `0x8005518c`, `0x800526f4`, `0x80053638`), and
**G6's `DAT+0x1526`** trail sentinel.

**KEY OBSERVATION:** neutralizing the **whole render driver `fcn.800224ec`** removed the dynamic objects (Flik, mound,
foliage) but **LEFT the sky / grass / pebble-ridge wall / flat dirt / mushroom** → the dirt is a **separate
"background" layer**, drawn apart from the dynamic-object render path. The scene driver caller is `fcn.~0x8004f3xx`
(calls the 6 scene fns, then `fcn.800224ec` ×2, then `fcn.8003df98`).

**CONFOUNDS (why the exact renderer is not pinned yet — important):**
1. The renderer **caches transformed geometry**; small movement (≤6 frames) does NOT refresh the far background, so
   "dirt persisted" can be a **cache artifact**, not proof the function isn't the renderer.
2. Neutralizing the driver `fcn.800224ec` also **FREEZES Flik's movement/camera** (the driver is entangled with the
   movement/camera update) — so its "background persists" is **not conclusive** (frozen frame keeps the cached
   background). Control (60-frame walk, no neutralize) scrolls the 3D scene normally (fence/foliage move) → the scene
   IS 3D and camera-follows; the dirt is real 3D geometry, drawn each frame, just not by any function tested so far
   under a *small-movement* test.

**REFINED NEXT-STEP METHODS (pick one for R2-continued):**
- **(a) Large-movement neutralize:** re-run candidate neutralizations with **60-frame movement** (forces background
  refresh) — only for functions that don't break movement (avoid the driver). The dirt going missing as the scene
  scrolls = that's its renderer.
- **(b) SXY method (original R2 plan):** break on RTPS-family sites that fire **before** the driver; read projected
  screen-XY; the dirt renderer emits **large ground polygons** (lower-screen, big area).
- **(c) Frame-loop trace:** find the **caller of the scene fn `~0x8004f3xx`** (the frame loop) and the
  **background-draw call above it** (the prologue auto-scan for the scene-fn entry failed; do it directly in r2).
- **(d) GPU/OT-side:** find the code writing the big ground **textured-quad GP0** commands (or the dirt's vertex
  buffer, then READ-watch it during render).

**STATUS:** dirt = separate background layer **CONFIRMED** (relative to the driver's dynamic objects); the **exact
renderer is UNKNOWN** — the neutralize method is confounded by render-caching + driver/movement entanglement, so
R2-continued should use a cache-robust method (a/b/c/d above).
**→ SUPERSEDED by §11 (cache-clean re-run, 2026-06-16): the "separate background layer" conclusion is now confirmed
WITHOUT the cache confound.**

---

## 11. R2 FINAL (2026-06-16) — cache-CLEAN differential (methods (a)+(c) combined); dirt = background layer, CONFIRMED

Resolves the §10 confounds. Combined method **(c)** (static frame-loop trace → exact call tree) with method **(a)**
(60-frame-movement neutralize so the render cache refreshes while the driver stays live → no freeze).

### 11.1 Static frame-loop map (method c) — r2, `om 3 0x80010000 0x72800 0x800 r-x`

- **Scene/per-frame fn entry = `0x8004ecd4`** (prologue `addiu sp,sp,-0x30`; the §10 "`~0x8004f3xx`" body is inside it).
  Its only caller (the **frame loop**) is **`0x8004fecc`** (`jal 0x8004ecd4`); the loop spins on vsync flag
  `0x80082250` at `0x8004fea4`, dispatches scene fn `0x8004ecd4` (state path) **or** `0x8004f478` (alt, flag `0x224e`),
  then `jal 0x8003e104`.
- The scene fn runs ~25 update calls, then the **render cluster** `0x8004f388–0x8004f458`:
  `0x8005518c` (always) → `0x800526f4`|`0x80053638` (flag `0x80090bee`) → **`fcn.800224ec` ×2** (object driver, args =
  display-context bases near `0x8009ec50`/`0x800a6520`) → `fcn.8003df98` (a0=0x80; builds a 2D OT primitive,
  GPU words `0xf2000000`/`0x61000000` → HUD/overlay, **not** terrain).
- Static fingerprint of the always-run siblings: none do GTE geometry directly — `0x8005518c` = palette/anim counters
  (`0x800910a2..a5`); `0x80053638` = 4 gray-fill rects via `0x80026a68`; `0x800526f4` = sprite/quad helpers
  (`0x80025f54`/`0x800260f8`). ⇒ the GTE world-geometry path is the **driver `fcn.800224ec`**, not the siblings.

### 11.2 Cache-clean neutralize differential (method a) — `stage66`, slot 6, 60-frame LEFT walk

Every run scrolled Flik **+11168 px** (except cull −/fence variants ~+8.8–9.6k) ⇒ camera moved ⇒ **render cache
refreshed** ⇒ results are trustworthy (no §10 confound 1). No run froze (no confound 2 — sub-functions, not the driver).

| Neutralized | Frame vs baseline | What it draws |
|---|---|---|
| — (baseline) | — | fence + dirt + sky + corn + leaf-hut + mushroom |
| `fcn.8001dfe4` (scene-geom disp) | **byte-identical** | nothing visible in this state |
| `fcn.8003f938` (render loop) | **byte-identical** | nothing visible in this state |
| `0x80053638` (gray-fill sibling) | **byte-identical** | inactive (gated on `0x80082​4dc`) |
| `0x800526f4` (sprite sibling) | ~identical (minor) | a small sprite/effect |
| `fcn.8001ea6c` + `fcn.80017b98` | **wooden fence GONE**, dirt stays | the **foreground wooden fence** (survivor-list builder; refines §10 "foliage") |
| `fcn.800140a0` (cull) | **more** geometry drawn, dirt stays | the **cull** (disabling it un-culls bg props) |

**RESULT:** the **tan pebbled dirt ground persists in 100% of variants** — including the ones that *did* scroll the
camera and *did* remove other geometry. So the §10 conclusion holds **cache-clean**: the dirt is a **separate
background layer**, NOT drawn by any driver sub-function, sibling, or the 6 R1 emitters.

### 11.3 Where this leaves the dirt renderer (UNKNOWN → narrowed)

Still not pinned, but the search space is now precise. The dirt must be drawn by a path that survives neutralizing
**every** sub-call tested. Remaining candidates, in priority for R2-continued:
1. **Inside `fcn.800224ec` but not in a delegated sub-fn** — i.e. the driver's own body emits the ground, OR only one
   of its **two** invocations (different display-context arg) does. **Next:** neutralize each *call site*
   (`0x8004f428` vs `0x8004f448`) independently (60-frame walk) instead of the shared callee.
2. **Method (d):** READ-watch the dirt's GP0 textured-quad submission / its vertex buffer during render (cache-immune,
   no neutralize). This is the most decisive remaining route.
3. The post-scene `jal 0x8003e104` (frame loop, after the scene fn) — untested.

**STATUS:** "dirt = separate background layer" = **CONFIRMED (cache-clean)**. Exact renderer = **UNKNOWN**, narrowed to
(1)/(3) above; method (d) (GP0/vertex-buffer READ-watch) is the recommended next decisive step. Tooling: `stage66`
in `/tmp/abl_dbg.py` (not committed).
**→ §11's "UNKNOWN renderer" and §10/§11's whole neutralize premise are RESOLVED/SUPERSEDED by §12: the bulk ground
is drawn by a render layer (0x80022–0x80025 emitters → 0x80060xxx libgte leaves) that the neutralize method structurally
could not find, for the reasons in §12.1.**

---

## 12. R2 DONE + R3 START (2026-06-16) — terrain render path FOUND: a missed `0x80022–0x80025` emitter layer that calls `0x80060xxx` libgte transform leaves

This session pins the terrain render path and **invalidates the §10/§11 neutralize conclusions as a discovery tool**
(two confounds, below). Live work via DuckStation external debugger; driver rebuilt at `/tmp/abl_dbg.py` (tmp was
wiped — not committed). All edits were clean RAM writes; no disc/DAT touched.

### 12.1 Two confounds that broke the prior (neutralize) method — both CONFIRMED
- **Camera-lock + uniform texture defeats NEUTRALIZE.** The visible ground is ~camera-locked in screen space and the
  pebble texture is locally uniform, so *removing* a terrain renderer leaves near-identical pixels → "byte-identical" →
  a FALSE "not this function." **Every** §10/§11/early-this-session neutralize that "left the dirt" is this artifact,
  not proof. Proof: an 8×8 frame diff across a camera move shows a **30**-frame walk leaves the foreground MAE 1–6
  ("looks static"), but a **90**-frame walk gives center-ground MAE **47.6** → the ground IS live 3D, just slow/uniform.
- **Discovery must be POSITIVE (move-test), not subtractive.** Working method: capture an emitter's source-vertex
  pointers at its GTE transform site, **shift their Y (+0x800) in RAM**, walk to refresh, `captureFrame` — geometry
  that *moves* on screen is what that emitter draws. (Removal is masked by camera-lock; movement is not.)

### 12.2 Driver-structure corrections (CONFIRMED, static + live)
- §11.1's "`fcn.800224ec` ×2 per frame" is WRONG. `0x8004f408 bne` picks ONE of two mutually-exclusive calls:
  `0x8004f428` (branch A, when `[0x800a6588]==13`) **or** `0x8004f448` (branch B, else) — both pass the SAME
  `a0=0x8009ec50`. Slot 6 = branch B (`[0x800a6588]=24`). So neutralizing the live call == whole-driver neutralize
  (freeze-confounded); the §11.3 "call-site differential" is moot.
- `fcn.800224ec` has **zero inline GTE**; all geometry is in deep callees. Trail helpers reclassified by disasm:
  `fcn.800140a0` & `fcn.80014360` = **cull/point-transform** (load rotation matrix, transform single points; **no
  `lwc2`** vertex stream — `fcn.80014360`'s large neutralize-diff was *un-occlusion*, not drawing); `fcn.800146e0` =
  **matrix-LOAD micro-helper** (`ctc2` LLM + bk regs); the "transform-one-vector" `lwc2`+`mvmva`+`swc2` routines are
  separate tiny entries at `0x80014724`/`0x8001474c`.

### 12.3 The `0x8001xxxx` inline-rtps family draws everything EXCEPT the bulk ground (CONFIRMED by move-test)
87 `rtps`/`rtpt` sites in `0x80010000–0x8001b000`, all inside **3** functions. Per-site SXY footprint + Y-shift:
- **`fcn.80010000`** (sites 0x80010488/04d8/06a8/06f8/08e4/0934/0b14): foreground **objects/decor** (mushroom +
  foliage/grass moved under shift). Indexed mesh, verts via `t0/t1/t2` in DAT payloads `0x80178xxx–0x801a1xxx`.
- **`fcn.800172dc`** (0x80017464/74bc/784c): **mid/background terrain** (the embankment). CONFIRMED visible + editable:
  builds GP0 **`0x3C`** shaded-textured-quads (`0x800173cc lui at,0x3c00`) from **persistent level pages
  `0x8012c`/`0x8012d`** (decompressed LEVEL.RAW region). Source format: `a1`-based, ~`0x30` stride, source verts via
  `lwc2` at `a1+0x4/0xc/0x1c` (xy) and `+0x8/0x10/0x20` (z). Clean Y-shift of those → mid terrain visibly moved;
  foreground ground unchanged. (Recolor/neutralize of this buffer = byte-identical → masked by 12.1.)
- **`fcn.80014b04`** (0x80014c14/6c/d98): central **prop/player** (`a1`-based, buffers `0x8012c–0x8012e`); move-test
  left the center ground unchanged.
**None of the 3 move the bulk walkable ground.**

### 12.4 THE MISSED LAYER (key result): bulk world geometry via `0x80060xxx` libgte leaves
- **7 more `rtps`/`rtpt` live in libgte leaves `0x80060650–0x80060814`** (entries incl. `0x80060724`, `0x800607a4`).
  The `0x8001xxxx` scan and ALL prior G-work (G9–G30 R1/R2) never looked here → this is why neutralizing every
  `0x8001xxxx`/driver function "left the dirt."
- The bulk geometry is drawn by **emitters in `0x80022xxx–0x80025xxx` that CALL these leaves** (no inline rtps).
  Caller pattern: load a geom base, build per-primitive vertex pointers (**stride `0x20`, verts at base+8/+16/+24**),
  pass to the leaf (`lwc2`+`rtps`/`rtpt` inside), then emit the output primitive.
- Leaf hits grouped by caller (`ra`), with screen footprint and move-test result:

  | caller (ra) | hits/frame | SXY footprint | identity (move-test) |
  |---|---|---|---|
  | **`0x800247b8`** | 996 | full-clip | **fence planks** — CONFIRMED (shift removed the fence, revealed Flik + the ground behind). verts `0x801a6xxx` |
  | **`0x80022c4c`** | 32 | x[199,628] y[129,**218**] (wide + low) | **BULK-GROUND candidate** (few big quads = a flat plane). base `=[0x8008249c]` (=`0x801ed31c`), leaf `0x800607a4`. **MOVE-TEST PENDING** (DuckStation crashed before completion) |
  | `0x8002574c` | 322 | full-clip | TODO |
  | `0x80025bd8` | 170 | y[66,1023] | TODO |
  | `0x8002da80/daa8/e178/e194/e394/e3bc/d860/d880` | 40–80 | small central | props |

### 12.5 Key addresses / globals (this session)
- **Geom base pointer for `0x80022c4c`: `[0x8008249c]`** (live value `0x801ed31c`; also referenced by `fcn.800172dc`
  via `ori …,0x249c`).
- **Libgte transform leaf bank: `0x80060650–0x80060814`** (function entries `0x80060724`, `0x800607a4`).
- OT base `[0x8008240c]` = `0x801e134c`.
- Driver branch selector `[0x800a6588]` (==13 → call A `0x8004f428`, else → call B `0x8004f448`).
- Source-vertex regions observed: `0x8012c/d` (fcn.800172dc mid-terrain), `0x80178–0x801a1` (fcn.80010000 objects),
  `0x801a6xxx` (fence caller 0x800247b8).

### 12.6 STATUS
- **R2 = DONE** — terrain render path identified. The bulk world ground is in the **`0x80022–0x80025` leaf-caller
  layer** (prime = **`0x80022c4c`**), NOT the `0x8001xxxx` inline-rtps family that all prior work searched.
- **R3 = IN PROGRESS** — `fcn.800172dc` source fully mapped (editable, GP0 0x3C, pages 0x8012c/d). Bulk-ground source
  reached via `[0x8008249c]` → leaf `0x800607a4`; vertex format known (stride 0x20, xy@+8/+16/+24); exact buffer +
  on-disk LEVEL.RAW origin still to capture.
- **DuckStation CRASHED** during the `0x80022c4c` BP add (after a long heavy BP-cycle session; the immediately-prior run
  did no memory writes → likely emulator instability, not a bad edit). **Live work needs a DuckStation restart + reload
  slot 6** (`~/.local/share/duckstation/savestates/SCUS-94288_6.sav`).
- **NEXT:** restart DuckStation → finish the `0x80022c4c` move-test (and `0x8002574c`/`0x80025bd8`) to pin the exact
  bulk-ground caller → capture its source buffer (R3) → R5 (on-disk LEVEL.RAW chunk+offset) → R6 (matched visual +
  collision lowered-floor edit).

---

## 13. R3 (cont., 2026-06-16, fence-free state) — bulk world geometry is a 2-STAGE pipeline; walkable ground is staged per-frame, persistent source is UPSTREAM

Operator supplied a clean fence-free save state (Flik on open walkable dirt, no occluders). Renamed & documented:
**`~/.local/share/duckstation/savestates/SCUS-94288_g30_openground.sav`** (was slot `_7`; slot freed). Use this for
all G30 ground work — the fence in slot 6 confounded every pixel-diff.

### 13.1 Move-tests in the clean view (CONFIRMED)
- **`fcn.800172dc` (buffer 0x8012c/d) = background foliage/terrain, NOT the near ground.** Clean slot-`openground`
  Y-shift moved the **sky/mid** (foliage rose into the sky, top-row MAE 92) while the **bottom-row walkable ground was
  unchanged (0.5–0.8)**. A huge shift only garbled foliage into stretched polys over the ground (debris, not the
  ground moving). So `fcn.800172dc` is the foliage/embankment renderer.
- **`0x800247b8` reads PERSISTENT `0x801a6xxx`** (it does NOT use `[0x8008249c]`). In slot 6 = fence; in
  slot `openground` (no fence) shifting it moved the **mid foliage/corn** (MAE 33), bottom ground only 4.8. So it is the
  mid-foreground decor emitter, not the ground.
- **The near walkable ground is LIVE 3D** (not a static backdrop): a 100-frame walk changed the pure near-ground
  patches (MAE 6.5–13.5) while sky stayed static (1.95).

### 13.2 The 2-stage pipeline (KEY — CONFIRMED structure, ground attribution LIKELY)
All bulk-world emitters that go through the libgte leaf `0x80060724` take their geometry base from the **single global
`[0x8008249c]`** (`lui …,0x8008; lw …,0x249c(…)` in `0x8002574c`@0x80025714, `0x80025bd8`@0x80025ba0,
`0x80022c4c`@0x80022c14). Over a full frame, **every value of `[0x8008249c]` lands in `0x801cxxxx–0x801exxxx`** — the
**per-frame GPU staging / OT work area** (OT base `[0x8008240c]`=`0x801e134c` sits inside it), **never** persistent
level data. So:
- **Stage 2 (FOUND):** emitters `0x8002574c` (464 hits), `0x80025bd8` (264), `0x80022c4c` (48) read **staged** verts
  from `[0x8008249c]` (preceded by libgte setup `jal 0x80060594` + `0x800605f4`), transform via leaf `0x80060724`,
  emit GP0 primitives. The walkable ground is drawn here (LIKELY — by elimination: it is not any persistent-readable
  emitter `fcn.800172dc`/`fcn.80010000`/`0x800247b8`, and these `[0x8008249c]`-staging emitters are what remain).
- **Stage 1 (UPSTREAM, TODO):** something writes the staging region `0x801cxxxx–0x801exxxx` each frame from the
  **persistent level source** (the actual editable ground geometry — the R3/R5 prize). Because the staged buffer is
  regenerated per frame, **static RAM edits to `0x801cxxxx` do not persist** (this is why the `0x80022c4c` move-test
  read 0.00 yet visibly distorted Flik's shadow/legs mid-frame — operator-observed; `0x80022c4c` = Flik **shadow**/
  dynamic, on the ground, not the ground itself).

### 13.3 Key addresses (this state)
- **`[0x8008249c]`** = "current geometry pointer" into the per-frame staging area `0x801cxxxx–0x801exxxx`.
- Stage-2 emitters: `0x8002574c`, `0x80025bd8`, `0x80022c4c` (all → setup `0x80060594`/`0x800605f4` → leaf `0x80060724`).
- Persistent-readable emitters (mapped, NOT the ground): `fcn.800172dc`→`0x8012c/d` (foliage/bg terrain, editable),
  `0x800247b8`→`0x801a6xxx` (decor/fence), `fcn.80010000`→`0x80178–0x801a1` (objects).

### 13.4 STATUS + decisive NEXT step
- **R3 status:** the ground render *path* is fully characterized (2-stage, staging via `[0x8008249c]`), but its
  **persistent editable source is still upstream of the staging** — not yet captured.
- **NEXT (decisive):** from `SCUS-94288_g30_openground.sav`, **WRITE-watch the staging region `0x801cxxxx–0x801exxxx`**
  through one frame to catch the **Stage-1 writer PC**; that writer reads the **persistent ground source** (expected in
  the decompressed LEVEL.RAW region `0x800Bxxxx–0x8015fcbc`, matching G29 collision). Edit that persistent source →
  ground moves → R3 done; then R5 (on-disk LEVEL.RAW chunk+offset) and R6 (matched visual+collision lowered floor).
- **Caveat:** static edits to `0x801cxxxx` are futile (per-frame regen). All ground editing must target the upstream
  persistent buffer.

---

## 14. R2/R3 RESOLVED (2026-06-16, openground state) — the visible terrain surface (incl. walkable ground) = `fcn.800172dc`, buffer `0x8012c/d`, PERSISTENT + EDITABLE. §13's "staged ground" inference was a clipping artifact, CORRECTED.

Worked entirely in `SCUS-94288_g30_openground.sav` (fence-free). Exhaustively move-tested **every** GTE emitter
(inline `0x8001xxxx` ×3 + leaf-callers via `0x80060724`/`0x800607a4` ×4) and decoded what each draws:

| emitter | source | draws |
|---|---|---|
| **`fcn.800172dc`** | **PERSISTENT `0x8012c/0x8012d`** (GP0 0x3C quads) | **the visible TERRAIN SURFACE — foliage, embankment, AND the walkable ground** — CONFIRMED EDITABLE |
| `fcn.80010000` | DAT payloads `0x80178–0x801a1` | foreground objects/decor (mushroom, grass) |
| `fcn.80014b04` | `0x8012c–e` | central prop/player |
| `0x800247b8` (leaf) | PERSISTENT `0x801a6xxx` (LEVEL.DAT) | foliage/decor (fence in slot 6) |
| `0x8002574c` + `0x80025bd8` (leaf, 2 passes) | LEVEL.DAT objects, pos via `[s2]/[s3]` (page `0x80160xxx`) | small props (corn/foliage stalks); big objects fully clip off-screen |
| `0x80022c4c` (leaf) | per-frame staging `[0x8008249c]`→`0x801cxxxx` | **Flik's ground SHADOW** (wide+low; operator saw legs distort) — NOT the ground |

**§13 CORRECTION (CONFIRMED):** §13 inferred the ground was "staged per-frame, source upstream" because a clean
**Y-shift** of `fcn.800172dc`'s buffer left the bottom-ground unchanged. That was wrong — the cause is **bottom-edge
clipping**: the near ground projects at/below the screen bottom, so a +Y shift pushes it further off-screen (no visible
change). An **X-shift** (slides sideways, not clipped) of the SAME buffer visibly **sheared the ground texture into
horizontal bands** (bottom-region MAE 4.4; mid 23) — proving `fcn.800172dc` draws the ground surface. The leaf-callers
draw props/shadow, NOT the bulk ground.

### 14.1 The editable visible-ground lever (R3 deliverable — CONFIRMED)
- Renderer: **`fcn.800172dc`** (entry `0x800172dc`; rtps/rtpt `0x80017464`/`0x800174bc`/`0x8001784c`).
- Source buffer: **`a1` ≈ `0x8012c1d0–0x8012e784`** (pages `0x8012c/0x8012d`), **PERSISTENT** (survives frames),
  in the decompressed LEVEL.RAW region (`0x800Bxxxx–0x8015fcbc`).
- Format: GP0 `0x3C` shaded-textured-quad packets, **`0x30` stride**; 4 source verts/quad at offsets
  **`+0x4/+0xc/+0x14/+0x1c`** (xy = low16 X, high16 Y) and z at `+0x8/+0x10/+0x18/+0x20`; gray colors at `+0x00/+0x24/+0x28/+0x2c`.
- Edits proven VISIBLE: Y-shift → terrain rises/caves; X-shift → ground texture shears. (Clean lower = subtract from
  high16 Y across the buffer; mind bottom-edge clipping for the nearest strip.)

### 14.2 Method lessons locked in (for future sessions)
- **Neutralize is BLIND to terrain** (camera-lock + uniform texture → byte-identical even for the real renderer). Use
  **move-test** (shift source verts → see motion).
- **Y-shifts of near/bottom geometry are masked by bottom-edge clipping** — use **X-shift** (or check the far edge) to
  confirm a near-ground renderer.
- "Live 3D vs static" via walk-MAE is confounded by uniform texture (small walk looks static) AND by props moving
  through the test box — corroborate with a direct source move-test.

### 14.3 NEXT — R5/R6 (the payoff)
- **R6 (matched visual+collision lowered floor):** lower BOTH (a) `fcn.800172dc`'s buffer `0x8012c/d` Y (visual, this
  section) and (b) the G29 collision sector origins `0x800a7e48`+`i*0x30`+4 (collision; CONFIRMED separate — §13 test:
  collision edit alone left the visual unchanged), by matched world amounts, on flat open ground (openground state),
  then trigger a short fall and `captureFrame`. Visual and collision are INDEPENDENT sources → both must be edited.
- **R5 (permanent):** the `0x8012c/d` terrain buffer is decompressed LEVEL.RAW → for a disk patch, WRITE-watch
  `0x8012c1d0` through level load to find the LEVEL.RAW chunk+offset (per the G22–G25 decompressor pipeline).

---

## 15. R6 ATTEMPTED (2026-06-16, openground) — both levers work; matched edit achieves COINCIDENCE; the dramatic single-shot is camera-follow-confounded (needs localized editing)

Ran R6 live (edit + capture only, NO breakpoints — crash-safe, no crash). Both floor levers confirmed and combined:

### 15.1 Collision lever — CONFIRMED (causal, reproducible)
- Lever: sector-origin Y at **`0x800a7e48 + i*0x30 + 4`** (223 sectors). **Subtract** → floor lowers.
- Idle lower does NOT move Flik (footing only re-resolves on un-ground); a **2-frame jump (`cross`)** triggers the fall.
- `−3000` origins + jump → Flik Y `−114744 → −117400` (fell ~2656, ≈1:1; survives, kill-plane ~≤8000 per G29). Direction + magnitude CONFIRMED.

### 15.2 Visual lever — CONFIRMED (causal, reproducible)
- Lever: `fcn.800172dc` buffer `0x8012c1d0–0x8012e784`, vert-Y high16 at `+0x4/+0xc/+0x14/+0x1c` per `0x30`. **Subtract** → terrain lowers.
- `−0x900` whole-buffer → ground visibly drops, exposing the terrain strata cross-section (operator-visible). EDITABLE confirmed.

### 15.3 Matched edit — COINCIDENCE ACHIEVED, but visually subtle (the real R6 finding)
- `−0x900` visual + `−3000` collision + jump → Flik fell to `−118776` and stands **correctly on the lowered floor: feet coincident, no float/sink.** The "consistent visual+collision floor edit" (R6's core goal) is **achieved**.
- BUT the frame looks **identical to baseline**. Cause (CONFIRMED by the collision-only test: Flik fell 2656 yet looked normal): **the camera follows Flik in Y and the ground texture is uniform**, so a *uniform* matched lower has no on-screen reference → invisible. The VISIBLE "lowered floor" (`g30_lowerfloor`) is the *mismatched* version (visual down, collision holding Flik high as the reference).
- A dramatic "Flik in a visible pit with un-lowered surroundings" needs a **localized** lower (lowered region + un-lowered reference). Blocked by: (a) the visual buffer is **strip-ordered** (a buffer sub-range ≠ a spatial region — halving it garbles strips), and (b) visual is **model-space** while collision is **world-space** with no measured scale, so matching a localized visual region to localized collision sectors needs cross-space calibration.

### 15.4 R6 status + what finishes it
- **CONFIRMED:** both floor sources are independently editable (visual `fcn.800172dc`/`0x8012c/d`; collision `0x800a7e48`), and a matched lower produces a **consistent** result (Flik lands coincident on the lowered floor). The user's core thesis — "move the collision *with* the floor" — is demonstrated.
- **Remaining (the dramatic shot):** a localized matched pit. This is exactly the use case for the proposed emulator
  additions — a **region/frame diff + atomic snapshot** to calibrate the model↔world scale by screenshot, and a
  **GTE-transform/access log** to map terrain verts → screen so a spatial region (not a strip-range) can be lowered.
  Recommend finishing this once those land; brute-forcing localized strip edits now is low-yield.
- Artifacts (not committed): `g30_lowerfloor.png` (visible visual lower), `g30_r6_collonly.png` (collision-only fall),
  `g30_r6_matched.png` (matched, coincident). State `SCUS-94288_g30_openground.sav`.

---

## 16. New experiment-harness API adopted; localized terrain editing CONFIRMED; R6 FINAL (2026-06-16)

DuckStation's external-debugger API was extended into a full RE experiment harness (batch, `memoryScan`, `readArray/
Struct/PointerChain`, `gpu.readVramRect/getStatus/getClut`, `captureSnapshotBundle`, `transferLog`, `accessLog`,
`findings`/`fixtures`, `experiment.run/compareRuns`, PGXP). See `~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md`.

**Adopted this session (durable):**
- **Fixture `x1` = `g30_openground`** registered (`fixtures.add`) → reproduce experiments via `fixtures.load`.
- **Findings `f4–f8`** stored + saved to `~/.local/share/duckstation/re_findings.yaml` (`findings.save`): the CONFIRMED
  G30 map (fcn.800172dc ground renderer; `0x8012c/d` editable buffer; `0x800a7e48` collision table; the
  `0x80060724`/0x80022–0x80025 emitter layer; visual≠collision + method notes). Evidence kinds:
  `access_log|memory_scan|screenshot|snapshot_bundle|diff|manual_note`.
- **`gpu.getStatus` → native render res = 512×224** (clarifies all SXY data; ground band y≈150–224).

**Localized terrain editing — CONFIRMED capability, with a rendering limit:**
- Method: EXEC at `fcn.800172dc` rtpt `0x80017464`, capture each quad's projected SXY + source ptr `a1` (~86 quads/
  frame, fast/crash-safe with settle-after-load), then edit only the quads whose SXY falls in a target screen box.
  Same-position before/after diff (`g30diff.py`) CONFIRMS the targeted region changes (MAE ~10–30 in-box, ~0 elsewhere).
- **Rendering limit (CONFIRMED):** the *dramatic* ground is the **near foreground**, which projects to y>~200 and
  **clips off the screen bottom** → it can't be cleanly screen-selected; the SXY-selectable quads are mid/far terrain
  (small screen footprint, so even ±0x1800–0x2000 model-Y edits move only a few px → visually subtle). Whole-buffer
  edits are dramatic but uniform (camera-follow + uniform texture hide a *matched* lower).

**R6 FINAL:** capability COMPLETE — both floor levers editable (CONFIRMED), a matched visual+collision lower lands
Flik coincident on the lowered floor (consistency — the user's core goal — proven), and localized screen-targeted
terrain editing works. The single *dramatic* "Flik in a deep pit" screenshot is limited by the game's intrinsic
rendering (near-ground clipping + perspective foreshortening + camera-follows-Y + uniform pebble texture), **not** by
tooling. Not worth further brute-forcing.

**Clean next wins now enabled by the new API (recommend):** R5 provenance via **`transferLog`** (start → trigger a
level load → see the CD→RAM DMA + LBA that fills LEVEL.RAW @0x80115aac; was the crash-prone WRITE-watch); lock the
collision lever as a CONFIRMED counterfactual via **`experiment.compareRuns`**; confirm the dirt texture via
**`gpu.readVramRect`** (draw→VRAM tie).

---

## 17. R5 RESOLVED (2026-06-16) — visible terrain on-disk source = LEVEL01/LEVEL.RAW **chunk 35** (offline chunk map + runtime decompressor-write confirmation via the new API)

The terrain buffer `0x8012c1d0` (§14, fcn.800172dc's source) traces to a specific compressed chunk of LEVEL.RAW —
proven two independent ways. New tool: **`tools/parse_level_raw_chunks.py`** (parses LEVEL.RAW's chunk table, locates a
runtime address).

### 17.1 Offline chunk map (CONFIRMED — exact compressed walk)
- File: **`REBUILD/files/LEVEL01/LEVEL.RAW`** = 747748 bytes = **0xb68e4** (exactly G22's LEVEL.RAW size).
- Chunk format (G24/G25, confirmed against the file): `[word0:BE32 decompressed][word1:BE32 compressed][6-byte hdr]
  [word1 compressed bytes]`; next chunk `+0xe+word1`; terminator `word0==0xffffffff`. 69 chunks.
- **Terrain `0x8012c1d0` → CHUNK 35: file offset `0x9908a`, compressed `0x1b24`, decompressed `0x34f4`.**
- Validation: the **compressed walk is exact** — my chunk at file off `0xa7ae3` matches G25's anchor `a0=0x801bd58f`
  precisely, with sizes (decomp `0x40c8`, comp `0x20c5`) matching G25 exactly. The **entire** observed terrain buffer
  `0x8012c1d0–0x8012e784` fits inside chunk 35's decompressed range — which also corroborates openground = LEVEL01.
- Caveat: decompressed *runtime* offsets carry a ~`0xb3c` drift (per-subtype `fp` advances aren't uniformly
  `align4(word0)` — texture/VRAM chunks); chunk identity is robust (drift < bracket margin), but the **exact
  compressed-byte offset within chunk 35 needs the G24 codec** (decompress→edit→recompress) for a disk edit.

### 17.2 Runtime confirmation (CONFIRMED — new non-halting API, from pre-load state `_2`)
- **`accessLog` WRITE-watch on `0x8012c1d0`** during the LEVEL01 load caught the writers = **`0x8001a5e8` /
  `0x8001a5f0` / `0x8001a678`**, all inside **`fcn.8001a1dc` (the LEVEL.RAW decompressor)**; immediately after, the
  word reads `0x3c747474` (the terrain GP0 0x3C command). → the terrain **is decompressed LEVEL.RAW output**,
  confirmed at the correct address (G23–G25 only inferred this for the retracted `0x801bdc58`).
- **`transferLog`** over the load: 265 CD sector reads (**LBA 1823–4149**) + **CDROM→RAM DMA** filling the compressed
  buffer up to ~`0x801cc1f8` (≈ buffer top `0x801cc390`). DMA channels: CDROM/GPU/SPU/OTC (a real level load).
- The old API's R5 (WRITE-watch through load) crashed repeatedly; `transferLog`+`accessLog` did it **non-halting and
  clean** — a direct payoff of the harness upgrade.

### 17.3 R5 status + permanent-patch note
- **R5 = DONE:** visible terrain/ground on-disk source = **LEVEL01/LEVEL.RAW, chunk 35** (compressed; decompressed by
  `fcn.8001a1dc` to `0x8012c`). Disc: LBA 1823–4149.
- **Permanent disk patch** needs the LZSS/LZ77 codec (G24, deliberately not implemented) to decompress→edit→recompress
  chunk 35. Simpler proven alternatives for an editable floor: the **RAM edit** (§14, `0x8012c/d` directly) baked into
  a save state, or a code patch. Collision is a **separate** LEVEL.RAW consumer (G29 sector table `0x800a7e48`).

---

## 18. COLLISION provenance + lever localization (2026-06-16) — the symmetric R5, done with the new API

Completes the collision side that G29 left open (G29 proved the RAM lever; on-disk source + localization were open).
All via the new non-halting tools from pre-load `_2` / openground.

### 18.1 Collision on-disk source — CONFIRMED
- **Collision PLANE geometry = LEVEL01/LEVEL.RAW CHUNK 32** (file offset `0x492cf`, compressed `0x2c80f` →
  decompressed `0x39d90`). Both the plane block `0x800c1690` and the floor plane record `0x800D10E8` (deep inside,
  off `0x1059c`) map to chunk 32, and `accessLog` caught the **decompressor `fcn.8001a1dc`** (PCs `0x8001a654`/
  `0x8001a678`) writing `0x800D10E8` → it's direct decompressor output, like the terrain.
- **Runtime sector index `0x800a7e48` is built post-decompress by a CONVERTER at `0x80030xxx`** (writer PCs
  `0x80030fac`/`0x80030fd8`) from the decompressed plane data — NOT the decompressor.
- So: **terrain = chunk 35, collision = chunk 32** (separate chunks → matches visual≠collision). Same LEVEL.RAW load
  (disc LBA 1823–4149). For a permanent collision disk patch: edit chunk 32 (needs the G24 codec) or RAM/save-state.

### 18.2 Localized collision lever — CONFIRMED
- Player's collision sector in openground (player X=33372 Z=-43769) = **sec186** (origin `(20608, 0, -40416)`, nearest
  by far, dXZ=13197). Lever = origin Y at `0x800a7e48 + 186*0x30 + 4`.
- Verified: lowering **only** sec186's origin Y by −3000 + a 2-frame jump → Flik fell −512 (partial — the resolver
  clamps across neighbors, so a *full* localized lower needs sec186 + adjacent sectors; lowering all 223 → ~−2656 ≈1:1).
- Tooling: `debugger.readArray` read all 223 sector records (origin x/y/z) in ONE call.

### 18.3 Net state of the floor-edit capability
- **Visual:** renderer `fcn.800172dc`, RAM buffer `0x8012c/d` (chunk 35), editable; localized by screen-SXY.
- **Collision:** sector table `0x800a7e48` (built by `0x80030xxx` from chunk 32), RAM lever per-sector (sec186 = player),
  editable.
- Both on-disk sources pinned (chunks 35 / 32, LBA 1823–4149); both have a clean RAM/save-state edit path now.
  Remaining gates: the **LZ codec** (permanent disk patch) and the **GTE-trace/frame-diff API** (the photogenic
  localized matched pit). No further pure-RE work is blocked.

---

## 19. SKY clear-color source (2026-06-16) — NOT a polygon; GP0 `0x02` background fill, recolor CONFIRMED

Goal-specific correction: the unobstructed blue sky in `SCUS-94288_g30_openground.sav` is **not** a stored image and
also **not a shaded polygon/quad**. The visible clear sky is a solid GPU background fill generated through the draw-env
path:

```
LEVEL.RAW color table 0x800c1688
  -> per-level sky cache 0x800771b0
  -> active DRAWENV 0x801cc390 / 0x801e134c
  -> GP0 fill rect command 0x02db5931
  -> VRAM top sky pixels 0x6d66 = RGB555 approx (48,88,216)
```

### 19.1 Render path and exact recolor lever (CONFIRMED)
- `gpu.readVramRect` on the displayed framebuffer showed the top sky rows are uniform `0x6d66` BGR555, i.e.
  approx RGB `(48,88,216)`.
- The active draw-env builder at **`0x800639cc`** forms the GP0 fill command from `DRAWENV+0x19/+0x1a/+0x1b`.
  Runtime trace in openground:
  - source draw-env: `s0=0x801cc390`, RGB bytes `0x801cc3a9..ab = 31 59 db`
  - generated command: `0x801cc3c8 = 0x02db5931`
  - twin buffer command: `0x801e1384 = 0x02db5931`
- The durable edit target is the per-level cache at **`0x800771b0`**:
  - `0x800771bc` = R word (`0x31`)
  - `0x800771c0` = G word (`0x59`)
  - `0x800771c4` = B word (`0xdb`)
- Recolor test: writing `0xff,0,0` to `0x800771bc/c0/c4` changed both draw buffers' sky pixels to `0x001f`
  (red, RGB555 approx `(248,0,0)`) after the double-buffer flip; writing `0,0xff,0` changed them to `0x03e0`
  (green, approx `(0,248,0)`). Screenshots:
  `/tmp/abl_sky_src_red_after.png`, `/tmp/abl_sky_src_green_after.png`.

### 19.2 Upstream table and disk provenance (CONFIRMED runtime copy; LEVEL.RAW chunk mapped)
- The cache is populated from a small color table at **`s3=0x800c1688`** by `0x8003b2xx`.
  Runtime trace from pre-load state `_2`:
  - `0x8003b2b8` writes `0x800771bc`
  - `0x8003b2d8` writes `0x800771c0`
  - `0x8003b2f8` writes `0x800771c4`
  - source table entry 0 at `0x800c1688` supplies bytes `31 59 db`
- `tools/parse_level_raw_chunks.py REBUILD/files/LEVEL01/LEVEL.RAW 0x800c1688` maps the table to
  **LEVEL01/LEVEL.RAW chunk 32** (`file_coff=0x492cf`, compressed `0x2c80f`, decompressed `0x39d90`,
  estimated offset in decompressed chunk `~0xb3c`). This is the same broad chunk as collision geometry, but the sky
  color table is a separate consumer within that chunk.
- The intermediate cache address `0x800771b0` also maps into LEVEL.RAW by the offline estimator (chunk 9), but the
  runtime copy trace shows the authoritative color source for the sky RGB is the **chunk-32 table at `0x800c1688`**.

### 19.3 Negative results locked in
- Searching/recoloring blue command words in the persistent terrain buffer `0x800b0000..0x8015fcbc` did not affect the
  sky because the visible clear sky color is not stored there as a blue GP0 primitive source.
- The `0x80027004` / `0x8001881c` depth-cue pass is not the sky clear. A one-frame exec trace showed it processes
  22 small `0x3e`/terrain-detail packets around screen y `~114..127` with gray/brown fogged colors, not the top-row
  blue background.
- Patching the transient command copies (`0x801cc3c8`, `0x801e1384`, `0x8007fc10`) is unreliable because they are
  rebuilt from the color cache/draw-env before GPU DMA; patch `0x800771bc/c0/c4` or the upstream table instead.

---

## 20. R6 localized-pit execution plan (2026-06-16) — leveraging the 11 new harness features

The 11 wishlist features shipped (commits c06d226bc…ca05a1c3e). They unblock the one item that was *tooling*-limited:
a **localized, matched visual+collision lowered floor** that's actually visible (a depression with un-lowered terrain
as the reference). The intrinsic limits (near-ground clips off the bottom of 512×224; camera-follows-Y) still apply, so
the pit must be aimed at the **on-screen mid-terrain band**, not the clipped near-ground. Recipe (each step → feature):

1. **Map terrain verts→screen — `execTrace` (feat 3).** `addWatch {pc:0x80017468 (fcn.800172dc rtpt+4),
   capture:["a1","gte.SXY0","gte.SXY1","gte.SXY2"], filter:{max_per_frame:200}}` → `run {frames:2}` → `get`. One
   non-halting call yields every terrain quad's `(source ptr a1, screen XY)` — replaces the old 86-iter resume/catch
   loop that timed out/crashed. (Validate the exact post-rtpt capture PC; ±4 if SXY reads stale.)
2. **Bridge model→world — `debugger.getGteState` (feat 7).** Read `control.rotation_matrix.float` + `control.translation`.
   For each candidate quad's model verts (from its `a1` buffer), world = matrix·model + translation. This aligns the
   visual verts (model space) to the **collision sectors** (world space) — the dual-space gap that blocked a localized
   matched edit before.
3. **Pick a target patch.** From step 1, choose a contiguous group of on-screen mid-band quads (screen y ≈ 120–195,
   centered in front of Flik). From step 2, get that patch's world X/Z extent.
4. **Lower BOTH atomically — `scatterWrite` (feat 2).** Visual: the patch quads' vert-Y (xy high16 at
   `a1+0x4/0xc/0x14/0x1c` per 0x30). Collision: the sector origins (`0x800a7e48 + i*0x30 + 4`) whose `(X,Z)` fall in the
   patch's world extent (sec186 + neighbors). One `scatterWrite {atomic:true}` (or two — visual + collision) instead of
   223 separate writes.
5. **Trigger + detect landing — `advanceUntil` (feat 5).** Hold toward the patch / 2-frame `cross`, then
   `advanceUntil {condition:{kind:"memory", address:0x800a6504, type:"s32", op:"stable", frames:8}}` → stops when Flik's
   Y settles (landed) without guessing a frame count.
6. **Verify — `captureFrame` + `diffFrames` (feat 6).** Capture before/after; `diffFrames {a,b,grid:{cols:8,rows:8},
   diff_path:...}` → `changed_bbox` + per-cell grid confirm a localized depression where targeted, surrounding terrain
   intact (no more hand-rolled PIL). Iterate depth/extent off the diff.

Gotchas (carry forward): `emulator.loadState` now **clears non-halting watches** → re-arm `execTrace`/`accessLog` AFTER
load; settle a few frames before `addWatch`; breakpoints force the ~10–100× interpreter so keep windows short + `clear`
when done; the game instance binds **2346** (build-test 23460, different token). Permanent *disc* version of any of this
still needs the LZ codec (G24) — RAM/save-state edits work today. STATUS: plan ready; execution pending (live tooling
classifier was intermittently unavailable at write time — run steps 1→6 when it stabilizes).

### 20.1 EXECUTION RESULT (2026-06-16, new tools live) — ground rendering fully characterized; openground edit is occlusion-limited
Ran the new harness end-to-end (all validated): **`execTrace`** mapped all 86 `fcn.800172dc` quads (a1 + GTE SXY) in
ONE non-halting call (replaces the 86-iter resume/catch loop that timed out/crashed); **`scatterWrite`** applied
multi-vertex edits atomically; **VRAM-diff** (`gpu.readVramRect` of the display framebuffer + raw-pixel diff) measured
at native 512×224 with NO upscale noise; **determinism** (clean-run vs edited-run at the same frame phase) isolated
edits from idle-animation noise (62368→4620 px); **`gp0Trace`** captured the display list.
- **CORRECTION (VRAM-diff, decisive):** `fcn.800172dc` is **~99% OCCLUDED** by the central bush in openground —
  recoloring AND raising all 86 quads each change only **717 px** (a 39×86 sliver). So `fcn.800172dc`/`0x8012c` is the
  occluded center/back ground, NOT a viable *visible* edit target in this view.
- **`gp0Trace` ground characterization:** one frame = 854 polygons, **689 `0x3C` (gouraud-textured) + 108 `0x34`** =
  the terrain/ground tiles, ALL drawn into the **per-frame staging region `0x801cxxxx`** by *multiple* emitters
  (`fcn.800172dc` is only 86 of the 689). The big under-Flik `0x2e` textured quad (src `0x801cebd8`) = Flik's **shadow**.
- **So the visible foreground ground is a multi-emitter, per-frame-staged, gouraud-textured tile system** sourced from
  LEVEL.DAT/LEVEL.RAW. Editing it persistently needs the upstream source *per emitter* (a multi-stage staging→source
  trace), and openground's central bush occludes the one persistent buffer we can edit (`0x8012c`).
- **Why g30_lowerfloor (slot 6) DID show a clear terrain drop but openground doesn't:** occlusion is view-specific —
  slot 6 has `fcn.800172dc`'s terrain unobstructed; openground buries it behind the bush.
- **NEXT for a clean visible matched edit:** (a) use a **less-occluded view** (face-on terrain, no central prop — slot 6
  already proved the edit shows there) and lower `0x8012c` (visual) + the player's sector (collision) by matched
  amounts; OR (b) trace the openground foreground-tile emitters' LEVEL sources (multi-emitter). The new tools make
  either tractable. The dramatic single-shot remains constrained by occlusion + camera-follow + uniform texture, now
  proven at native precision rather than guessed.

### 20.2 BULK visible-ground emitter found: ~`0x80019xxx` (2026-06-16) — finding f13, fixture x2 (g30_openfloor)
New fixture **`g30_openfloor`** (renamed from `_1.sav`; operator-provided): Flik on a big OPEN unobstructed pebbled
floor, different area (player Z~217790). *WARNING: walking forward spawns an enemy + fence* — keep Flik in place.
- VRAM-diff confirms `fcn.800172dc` is **743 px** here too (same occluded sliver) — so it is NOT the bulk ground in
  EITHER view. Changing location did not make it visible; it is simply a minor terrain patch.
- **Trace (gp0Trace → accessLog):** picked the biggest lower-screen `0x3C` ground tile from the display list, read its
  staging command address (`source_addr`), then `accessLog` write-watched that address → **writer PCs
  `0x80019934/50/54/70`**. So the bulk visible ground is built by an emitter at **`~0x80019xxx`** (rtpt `0x80019684`/
  `0x80019734`; output-build `0x800198a0–0x800199xx` storing `0x3C` gouraud-tex quads into staging `s3`). This is the
  long-elusive "which emitter draws the ground I see" answer.
- The emitter processes a **build-context struct `s7`** (reads `lw …(s7)` at offsets 0x24–0x108 throughout; no inline
  `lwc2` in the output tail — verts are loaded into the GTE / `s7` earlier). **NEXT lever to find = the origin of `s7`**
  (execTrace the emitter capturing `s7`/`a0`/`s6`, classify the region: persistent decompressed-level `0x800b…0x8015fcbc`
  / LEVEL.DAT `0x80160…` = editable, vs scratch = trace further upstream). Once `s7`'s source is pinned, lower that
  region (visual) + the player's collision sector (sec table `0x800a7e48`) by matched amounts → visible matched floor.
- Tooling note: switched measurement to **VRAM-diff** (`tools/vramdiff.py` — read display framebuffer + raw-pixel diff,
  native, no upscale noise); driver moved to `tools/abl_dbg.py` (persistent; `/tmp` gets wiped). `gp0Trace.stop` FREES
  the ring → always `get` before `stop`.

### 20.3 VISIBLE-FLOOR SOURCE PINNED + EDITED (2026-06-16) — LEVEL.DAT verts via fcn.80010000 → 0x80019xxx
**s7 trace (execTrace at writer `0x80019934` capturing s7/a0/s6/ra):** `s7=0x1f800000` (scratchpad work struct, not
source); **`a0`=`0x80178590` / `0x80177b7c` = LEVEL.DAT (persistent, EDITABLE)** = the object being drawn; `ra=0x800108b8`
= caller is **`fcn.80010000`** (the G11/G27/G28 mesh emitter). So the **bulk visible ground = `fcn.80010000` drawing
DAT-backed objects** through the `0x80019xxx` sub-emitter — the SAME system G28 proved visually editable. This finally
unifies the visible-ground question with the confirmed-editable Candidate-A/fcn.80010000 payloads.
- **Vertex format (CONFIRMED by edit):** each object is a contiguous array of **12-byte vertices** = 6×int16
  `[c0, c1, Z(col2), 0(pad), X(col4), Y(col5)]`. Adjacent tiles **share** edge verts (obj1 vert3 == obj2 vert0).
  Per-column ranges over 96 verts: X(col4) span 63480, Z(col2) span 8504, **Y(col5 @ offset +0xa) span 68 (the flat
  height axis)**. **EDIT LEVER = the int16 at vert+0xa.**
- **Edits land + are visible (VRAM-diff):** lowering Y on all 96 verts changed **38090 px** (the whole visible lower
  half); index→screen probe mapped `obj1[0:24]` → the foreground floor under Flik (bbox `(0,125,461,73)`), `obj2` → the
  right side. So I can target any floor region precisely.
- **Visual character (the limit, now proven on the REAL floor):** the floor tiles are **gouraud-textured (`0x3C`)**, so
  a Y-edit mostly **recomputes the lighting** (lowered → yellow, raised → purple) while the geometric displacement reads
  subtly under foreshortening + camera-follow; a big edit (≈ -0x100 on the near patch) sends verts across the frustum →
  stretched-poly garbage. Workable clean range ≈ ±0x20..0x60. So the floor is fully editable + region-targetable, but a
  dramatic "3-D pit" doesn't render cleanly — same occlusion/projection class of limit documented in §16/§20.1.
- **Matched edit now has BOTH levers in hand:** visual = these `a0` vert-Y values; collision = the sector table
  `0x800a7e48` / player sector. A matched lower (floor verts + collision) is mechanically ready; the on-screen result is
  a reshaded lowered region with Flik on it (not a crisp pit) due to the gouraud/projection character above.
- Fixture `x2` g30_openfloor; finding `f13` (bulk-ground emitter, now with the s7/a0 source + Y lever).
