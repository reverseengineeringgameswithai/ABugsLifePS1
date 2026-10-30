# G29 — Collision / pathing source discovery for the confirmed visual floor terrain

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G28 Candidate A runtime confirmation](geometry_g28_candidate_a_runtime_confirmation.md) ·
[← G5 collision consumers (negative)](geometry_collision_consumers.c) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **EXECUTED (2026-06-15) — header corrected 2026-06-22.** This file began as static reconnaissance +
operator runbook, but §§2.5–2.13 below record the **executed live DuckStation results**: collision SOURCE =
LEVEL.RAW (decompressed) PLANE records, written by decompressor `fcn.8001a1dc`; clamp math decoded; and a
**validated RAM edit** (sector-104 origin-Y moved Flik's footing ~1:1). The original "PLAN ONLY / no emulator
run" line contradicted its own body and is retracted. *(Earlier header text, for history: "ANALYSIS +
RUNTIME-WATCH PLAN ONLY. No patch, no build, no game-data edit, no emulator run.")* This file is the static
reconnaissance + operator runbook for
locating the **collision/pathing source** of the floor surface that G28 proved is a *visual* render
payload.

---

## 1. Objective

Find the runtime data/function path that controls **Flik's ground contact, floor height, walkability,
or collision response** over the floor area that G28 confirmed as a visual render mesh (Candidate A).

Use **Candidate A only as a known visual anchor** (the on-screen patch we can point at). **Do NOT assume
Candidate A, LEVEL.DAT, or LEVEL.RAW contains the collision data.** The deliverable here is evidence +
a watch plan, not a patch.

---

## 2. What G28 established (the visual/collision split) — CONFIRMED

```
CONFIRMED (carried forward, do not re-litigate):
  - Candidate A is a DAT-backed VISUAL floor/top-surface render payload.
      payload base  = 0x801790c4
      vertex base   = 0x801790c8
      DAT offset    = 0x188cc      count = 83
  - Candidate A reaches fcn.80010000 + the projection path (READ 0x801790c8, EXEC 0x80010718).
  - The G28 edit (DAT+0x18992, v16.y 89 13 -> 89 17, +1024) VISIBLY caved/deformed the floor in
    Candidate A's projected area; Flik and other objects still rendered.
  - The visual deformation did NOT align with collision/pathing: Flik's standing/walking surface did
    not follow the caved mesh.

INTERPRETATION:
  visual terrain payload != collision/pathing source for this tested edit.

UNKNOWN (this is the G29 target):
  - The actual collision/pathing source for the floor surface.
  - Whether collision/pathing lives in LEVEL.DAT, LEVEL.RAW, a generated runtime buffer, or a sidecar.
  - Whether Candidate A has any collision/tangibility data elsewhere.
```

**Correction kept intact:** `0x801bdc58` is **compressed LEVEL.RAW source** (G26), never written, NOT a
payload — do **not** resurrect it. It is **not** the valid DAT-backed Candidate E at `0x8018dc58`
(one hex digit apart). The LEVEL.RAW load/decompress RE (G22–G25) stands as resource characterization;
it does not locate collision.

---

## 2.5 PASS 1 RUNTIME RESULT (2026-06-15) — player-Y writer identified; it is NOT `fcn.8005b134`

The operator ran Pass 1 on the **pristine** image: **WRITE watch `0x800a6504`**, Candidate-B floor area,
Flik moving (writes only occur on motion). Observed writer PCs: **`0x80036384` / `0x80036cf0` / `0x80036d58`**;
representative state at `0x80036384`: `a0=s1=s7=0x800a6500`, `a1=s5=0x800a652c`, `a2=0x800a6582`; the other
two hits carry `ra=0x80036c70`, `s5=0x800a652c`, `s6=0x800a6582`, `s7=0x800a6500`.

**Static disassembly of SCUS_942.88 (t_addr `0x80010000`, header `0x800`; r2 read-only) resolves all three.**
The writer is a single previously-unnamed function:

```
FUNC_3633C  head = 0x8003633c  (addiu sp,sp,-0x88)
  0x80036344  move s7,a0     ; s7 = a0 = player/entity struct base       (runtime 0x800a6500)
  0x80036378  move s5,a1     ; s5 = a1 = velocity/delta vector           (runtime 0x800a652c = base+0x2c)
              a2 (->[sp+0x28], used as s6) = contact-flag bytes          (runtime 0x800a6582 = base+0x82)
```

Called from **3** sites (jal-encoding scan): `0x800495c8` (observed RA `0x800495d0`), `0x8004c024`, `0x8004e628`.
The caller at `0x80049560..` first checks the velocity words `s1+0x2c/0x30/0x34` (`0x800a652c/30/34`) then passes
`(player=0x800a6500, vel=0x800a652c, flags=0x800a6582)` into FUNC_3633C — so this is the **per-frame movement +
collision-response integrator** operating on the player struct.

### The four stores to `[s7+4] = 0x800a6504`, and how the observed PCs map (PC = store+4)

| store PC | instruction | value path | observed-as PC | role / classification |
|----------|-------------|------------|----------------|-----------------------|
| `0x80036380` | `sw v0,4(s7)` | `v0 = [s7+4] − 0xc80` (lw `0x80036374`, addiu `0x8003637c`) | **`0x80036384`** | **Y probe-bias DOWN** by `0xc80`(3200) at entry. NOT a floor value — a transform of Flik's own Y. |
| `0x80036cec` | `sw v1,4(s7)` | `v1 = [sp+0x1c]` (collision-resolved Y from the `sp+0x18..0x24` scratch buffer) | **`0x80036cf0`** | **COMMIT of the collision-RESOLVED position** (X=`[sp+0x18]`,Y=`[sp+0x1c]`,Z=`[sp+0x20]`). **This is the floor/contact-corrected Y — the decisive write.** |
| `0x80036d30` | `sw v0,4(s7)` | `v0 = [s7+4] + [s5+4]` (free velocity integration) | (PC `0x80036d34`, **NOT** observed) | Plain `pos += vel`. Its absence ⇒ during the observed walk the **commit/resolved** path was taken, not free integration. |
| `0x80036d54` | `sw a0,4(s7)` | `a0 = [s7+4] + 0xc80` | **`0x80036d58`** | **Y probe-bias UP** (restores the entry `−0xc80`). NOT a floor value. |

**DuckStation reports PC = store_address + 4** (the instruction *after* the store): all three observed PCs are
exactly `store+4`. CONFIRMED.

**`ra=0x80036c70` on the `0x80036cf0`/`0x80036d58` hits = the return address of `jal 0x800345cc` (`0x80036c68+8`).**
So the active collision helper during the observed floor-walk is **`0x800345cc`**. The fall-through at
`0x80036c40` (`bne v0,s1` not taken) runs `jal 0x80035f24` (→`v0`→`s0`) then `jal 0x800345cc` (→ result code in
`a3`), which drives the **commit-from-resolved-buffer** path (`0x80036ce8..0x80036cf4` writes X/Y/Z/W from
`[sp+0x18..0x24]`), then re-adds `0xc80` at `0x80036d54`.

### The collision helpers and where the floor-height source `S` lives (Pass 2 target)

`FUNC_3633C` calls three helpers, all on the scratch point buffer `sp+0x10`/`sp+0x18`:

```
0x80036c50  jal 0x80035f24   (a0=sp+0x10, a1=s4, a2=s5, a3=s3)  -> v0 (-> s0)        ; per-axis sweep/test
0x80036c68  jal 0x800345cc   (a0=sp+0x10, a1=s4, a2=s5, a3=s3)  -> a3 result {0,1,2} ; ACTIVE in observed walk
0x80036c84  jal 0x80035280   (a0=sp+0x18, a1=s5, a2=?, a3=...)  -> a3                 ; alt path (v0!=s1 branch)
```

`0x800345cc` and `0x80035280` share a prologue that reads **`[gp+0x57c]` = a collision-candidate COUNT**
(`blez → skip`; `gp=0x80081d98` runtime ⇒ `0x80082314`), then iterate a per-frame candidate list and write the
resolved position back into the `sp+0x10`/`sp+0x18` buffer. **The floor-height source `S` is an element of that
candidate list** — a per-frame `gp`-relative scratch structure, reached by a non-global pointer. This is exactly
why the G5 global text scan found no collision consumer.

### `fcn.8005b134` contradiction — SUPERSEDED / PENDING (not erased)

- The actual store to `0x800a6504` is in **`0x8003633c`**, **not** `0x8005b134`.
- `fcn.8005b134` has **ZERO `jal` callers** (overlay / jump-table dispatched); `0x8003633c` has **3** `jal`
  callers (`0x800495c8/0x8004c024/0x8004e628`), none of which is `0x8005b134`.
- Therefore the G5 "**sole** player-pos writer = `fcn.8005b134`" claim is **SUPERSEDED/PENDING**: `fcn.8005b134`
  may write player pos in *another* context (scripted/teleport/spawn/overlay verb), but the **per-frame
  movement+collision Y integrator is `0x8003633c`**. The relationship between `fcn.8005b134` and
  `0x8003633c`/its 3 callers is **UNKNOWN** until a runtime EXEC pass resolves it. Do **not** delete the old
  claim; mark it superseded/pending.

NOTE: the `−0xc80`(3200) probe bias here is a **distinct** movement-integrator artifact; it is **not** the
pickup-walker `−0x1cc0` Y bias (`fcn.800586b0`, still excluded).

---

## 2.6 PASS 2 RUNTIME RESULT (2026-06-15) — resolved-Y is a per-axis ACCUMULATE; source = collision-candidate list (not yet located)

Pass 2 worked the stack chain behind the final commit. At **EXEC `0x80036cec`** (the decisive commit) the operator
confirmed `sp=0x801FFE00`, `v1=0xFFFE2196`, and dumped the working buffer:
`[sp+0x18]=0x00005B7B, [sp+0x1c]=0xFFFE2196, [sp+0x20]=0xFFFFB44B, [sp+0x24]=0xFFFF0000` — `[sp+0x1c]` matches `v1`
exactly (the resolved Y). The operator then armed a **WRITE watch on `0x801FFE1C`** (= `sp+0x1c` of this frame)
and caught **two** writers; both verified by r2 disasm (DuckStation PC = store+4):

### Hit A — `0x80035EDC` → store `0x80035ED8` `sw v0,4(s5)` (inside helper `0x800345cc`) — the resolved-Y COMPUTE
```
0x80035eb4  lh   v1,(s3)     ; X delta  (signed halfword)
0x80035eb8  lw   v0,(s5)     ; X acc    (word)
0x80035ec4  sw   v0,(s5)     ; [s5+0]  = Xacc + Xdelta
0x80035ec8  lh   v1,2(s3)    ; Y delta  (signed halfword)
0x80035ecc  lw   v0,4(s5)    ; Y acc    (word)
0x80035ed4  addu v0,v0,v1    ; v0 = Yacc + Ydelta
0x80035ed8  sw   v0,4(s5)    ; [s5+4]  = Yacc + Ydelta   <-- WRITE 0x801FFE1C  (v0=0xFFFE2196)
0x80035edc  lh   a0,4(s3)    ; Z delta  (reported PC; store+4 confirmed)
0x80035eec  sw   v1,8(s5)    ; [s5+8]  = Zacc + Zdelta
```
This is a **3-component vector accumulate**: `pos[i] (word @ s5) += signed_halfword delta[i] (@ s3)`. With
`s5=0x801FFE18` (= the **caller FUNC_3633C `sp+0x18` working buffer**; FUNC_3633C passes `s4=sp+0x18` as `a1`→
helper `s5`) and `s3=0x801FFE10` (= caller `sp+0x10` delta/candidate buffer; passed as `a0`→helper `s3`).
At the hit `v1=[s3+2]=0` ⇒ **this iteration added 0**, so `0xFFFE2196` was already present in `[s5+4]` (the value
pre-existed; the accumulate is the *write site*, not the value's origin). The function owning `0x80035ED8` is
**`0x800345cc`** (prologue `addiu sp,sp,-0x110`; the active collision helper from Pass 1).

### Hit B — `0x80036BE0` → store `0x80036BDC` `sw v1,0x1c(sp)` (inside FUNC_3633C) — a COPY/seed
```
0x80036bc8  lw v0,(s7) ; lw v1,4(s7) ; lw a0,8(s7) ; lw a1,0xc(s7)
0x80036bd8  sw v0,0x18(sp) ; sw v1,0x1c(sp) <-- WRITE 0x801FFE1C ; sw a0,0x20(sp) ; sw a1,0x24(sp)
```
A straight 4-word copy `[sp+0x18..0x24] ← [s7..s7+0xc]` that **seeds** the working buffer from a position vector.
Gated just above by `bgtz [gp+0x57c]` (`0x80036bb0`) / `blez [gp+0x5cc]` (`0x80036bc0`). **NOT** the resolved-Y
origin — pure propagation. At this hit `s7=0x801FFEA8`.

### Decisive structural correction — this FUNC_3633C invocation operates on a STACK vector, not the player global
At Hit B `s7=0x801FFEA8` (a stack-resident XYZ vector), **not** the player base `0x800a6500`. FUNC_3633C sets
`s7=a0` once at entry, so for this invocation `a0=0x801FFEA8`. Therefore: the watched slot `0x801FFE1C` is
FUNC_3633C's `sp+0x18` **working buffer**, and the `0x80036cec` commit writes back to `[s7+4]=0x801FFEAC` — **not**
`0x800a6504` in this run. (Pass 1 caught the *player-base* invocation, `s7=0x800a6500`.) So FUNC_3633C is a
**reusable position+collision integrator** applied to whatever XYZ vector `a0` points at; the link from the
`0x801FFEA8` stack vector to the player global is a separate step — **UNKNOWN / TODO** (do NOT claim
`0x801FFEA8` = player). The value `0xFFFE2196` traces back, through both the copy (`[s7+4]=0x801FFEAC`) and the
accumulate (`[s5+4]`), to the prior contents of that position vector + per-axis deltas; this iteration's Y delta
was 0.

### Source chain (current best model)
```
per-frame:   collision-candidate list  (counts [gp+0x57c]=0x80082314, [gp+0x5cc]=0x80082364; built earlier in frame)
   |  (sweep helper 0x80035f24, called 0x80036c50: a0=sp+0x10 out, a1=sp+0x18, a2=s5) -> writes per-axis DELTAS to sp+0x10
   v
FUNC_3633C:  sp+0x18 working buffer  <-- seeded by copy 0x80036bdc from position vec [s7]
   |  (accumulate helper 0x800345cc, 0x80036c68: pos[sp+0x18] += delta[sp+0x10])  == Hit A 0x80035ed8
   v
FUNC_3633C:  commit 0x80036cec  [s7+0..0xc] <- sp+0x18..0x24   (writes player Y only when s7 == 0x800a6500)
```

### Task-1 answers
1. **Source of the write to `0x801FFE1C`:** TWO writers to the **same** stack slot (FUNC_3633C `sp+0x1c` working-Y):
   `0x80035ED8` (accumulate, helper `0x800345cc`) and `0x80036BDC` (copy/seed, FUNC_3633C). **CONFIRMED.**
2. **Is `0x80035EDC`(store `0x80035ED8`) the primary resolved-Y source write?** **LIKELY** — it is the per-axis
   *compute* (`Yacc += Ydelta`) inside the collision helper, vs. the mere copy at Hit B. But it is an
   *incremental accumulate*; the value's true origin is the candidate-list-driven deltas, **not** this site. **CONFIRMED**
   as the resolved-Y write site; value origin **UNKNOWN**.
3. **Is `0x80036BE0`(store `0x80036BDC`) only propagation/copy?** **CONFIRMED** — straight `[sp+0x1c]=[s7+4]` seed.
4. **Which routine owns `0x80035EDC`?** **`0x800345cc`** (CONFIRMED) — FUNC_3633C's active collision helper.
5. **What feeds `v0` at `0x80035ED8`?** `[s5+4]` (working-Y) `+ signed[s3+2]` (Y delta). `s5`/`s3` are FUNC_3633C's
   `sp+0x18`/`sp+0x10` working buffers; the deltas come from the **per-frame collision-candidate list** (counts
   `[gp+0x57c]/[gp+0x5cc]`), produced by sweep helper `0x80035f24`. The list's **backing region** (DAT /
   LEVEL.RAW-decompressed / generated) is **UNKNOWN — TODO** (next capture).

Source data structure: **PARTIAL** — identified as a per-frame collision-candidate list (counts at
`0x80082314`/`0x80082364`, sweep producer `0x80035f24`), not yet located in a backing memory region.

(Sub-detail: inside helper `0x800345cc`, `ra=0x8003570C` is stale from its own internal `jal 0x800322a0`
at `0x80035704` — a sub-routine of the helper, not its caller.)

### Pass 2-next — minimal capture to locate the candidate-list backing store
Static analysis shows `0x80035ED8` only *consumes* pre-computed deltas, so dumping there cannot reveal the floor
source. The producer is the sweep helper **`0x80035f24`** (runs before the accumulate). **PRIMARY (one BP):**
**EXEC `0x80035f24`** — dump `a0`(=`sp+0x10` delta-out), `a1`(=`sp+0x18` working pos), `a2`(=`s5`), `a3`, and the
**candidate-list base pointer** it iterates (plus `[gp+0x57c]=0x80082314`/`[gp+0x5cc]=0x80082364`). Step its head
to find the `lw`/`lh` that reads a **floor-height candidate**; record that address `S` and classify its band
(DAT `[0x801607f8,0x801b1c10)` not A's vertex band `~0x80179188` / LEVEL.RAW-decompressed `<0x8015fcbc` / heap
`[0x801b6a10..)` / generated). **Fallback:** EXEC `0x80035EDC`, dump `s3`(`0x801FFE10`)/`s5`(`0x801FFE18`) windows
across iterations to catch a **nonzero Y delta** and step back to its producer. No G28 comparison until `S` is
identified. No patch/build.

---

## 2.7 G29 — candidate-record read/compare evidence (2026-06-15)

While probing the candidate side, the operator captured a candidate-record **read/compare** path inside
FUNC_3633C. At **`pc=0x80036B70`** (`ra=0x800363CC`, `s5=0x801FFEB8`, `s7=0x801FFEA8` — same stack-vector
invocation as §2.6): register `v1` already equals the 32-bit little-endian word at **`t1 − 0x08`**.

**Capture set (CONFIRMED arithmetic, `[t1−0x08]` LE == `v1` in all three):**
```
t1=0x800F7BB8  v1=0x000011FC  [0x800F7BB0]= FC 11 00 00
t1=0x800F7B74  v1=0x0000121A  [0x800F7B6C]= 1A 12 00 00
t1=0x800F7B30  v1=0x00001300  [0x800F7B28]= 00 13 00 00
```
The three `t1` values are `0x44` apart, but that is the spacing **between the captured samples**, NOT a proven
fixed record stride (LIKELY per-block/chained spacing that happened to be uniform here). The candidate records sit
at **`0x800F7xxx`** — above the exe text end (`~0x80082800`), below LEVEL.DAT (`0x801607f8`) / LEVEL.RAW
(`0x80115aac`) — i.e. a **runtime/heap/BSS region**; its **backing source is UNKNOWN** (do NOT claim DAT / RAW /
decompressed).

**Capture-point roles (record exactly):**
- `0x80036B78` = post-read PC previously observed.
- `0x80036B74` = useful candidate-record read/compare site.
- `0x80036B70` = stronger post-load / pre-compare capture point.
- **Exact load PC is TODO, likely near `0x80036B6C` unless statically confirmed.**

**Pointer-relationship caveat (record exactly):**
```
Earlier 0x80036B74 captures:  t2 = t1 - 0x30 ,  t6 = t1 + 0x90
Newer   0x80036B70 captures:  t2 = t1 - 0x30 ,  t6 = t2
=> t2 = t1 - 0x30 appears STABLE in observed captures;
   t6 relationship is state/site-dependent and must NOT be treated as universal.
```

**Static (r2) grounding — for next-phase confirmation, not a runtime claim:** the loop `0x800369a0..0x80036b7c`
(inside FUNC_3633C) walks a **chained list of candidate blocks** (`t2`; next-pointer `lw t2,-4(t2)` @`0x80036b74`;
entry count `lhu [t2]`). Per entry, `t1 = t2 + a3*0xc` (sub-record stride `0xc`; so `t2 = t1−0x30` ⇒ index `a3=4`,
which is why that relation "looks stable"); `t6 = t2` at `0x800369bc` then `t6 += 0xc0` per outer step (hence
state-dependent). The candidate's `+4` word is loaded at `0x80036a38` `lw v1,4(t1)` and used in a **bounding/
range-overlap compare** (`slt v1,t5` @`0x80036a40`; `slt s3,…` @`0x80036a54`); after `addiu t1,t1,0xc` @`0x80036b40`
that held `v1` equals `[t1−0x08]` at the `0x80036b70` capture. Matched candidates are copied to an output list at
**`0x80090868`** (stride `0xc`, count `[gp+0x5cc]=0x80082364`). So `t1−0x08` (= a candidate `+4` field) is **LIKELY
a candidate scalar feeding the compare/selection path** — possibly a coordinate bound / range / ranking / contact
metric — **semantic UNKNOWN; NOT confirmed floor height.** Exact load PC to confirm at runtime (TODO).

**G28/G29 boundary preserved:** G28 Candidate A = **CONFIRMED visual floor/render payload**; its deformation did
**not** follow into collision/pathing in the observed test; the **collision/pathing source remains UNKNOWN**. This
candidate-record evidence does not change that and makes no claim about Candidate A.

**Suggested authoritative breakpoint block (DuckStation AI Prompted Copy) — documentation only, no new test
requested here:**
```
FINAL BREAKPOINTS:
EXEC 0x80036B70
```
(Meaning: remove all existing breakpoints except exactly those listed, matching type and address.)

**Recommended next step:** static/decompile inspection around `0x80036B6C..0x80036B78` to confirm the exact load
instruction feeding `v1` / `[t1−0x08]` and how it is used in the compare/selection path (the static candidate is
`0x80036a38` `lw v1,4(t1)`; confirm at runtime).

---

## 2.8 G29 LIVE (DuckStation external debugger, Flik moving) — collision/floor SOURCE structure IDENTIFIED (2026-06-15)

The DuckStation **external-debugger-control** server (JSON-RPC, `127.0.0.1:2346`) plus the new **controller-input**
methods (`setControllerState`/`pressButton`/`advanceFrames`) were used on save state `SCUS-94288_1.sav`. With Flik held
walking (`left`), the **player** integrator (`FUNC_3633C`, `a0=0x800a6500`, vel vec `a1=0x800a652c`) runs and resolves
Y through a collision structure. CONFIRMED data path (all addresses live-verified):

```
player XZ (0x800a6500, moving; needs motion — idle frames make NO player call & 0 contacts)
  -> SECTOR TABLE @0x800a7e48  (count [gp+0x508]=223, start [gp+0x6cc]=191; 0x30-byte records;
        per-record AABB min @+0x14/+0x1c, extent @+0x24/+0x28, flag @+0x2c, block ptr @+0x10)   [0x80036700/0x80036804]
  -> [sector+0x10] collision-record block (e.g. 0x800C1690)
  -> 32-byte collision records @~0x800D0xxx, AABB-tested vs the quantized player query           [0x80036820..0x8003690c]
  -> matches stored as POINTERS in the gp+0x57c list @0x8009c230 (parallel halfword list @0x80091718)  [store 0x800368E8]
  -> resolution helpers (0x800345cc / accumulate 0x80035ED8, per 2.6/Pass 2)
  -> resolved [sp+0x18..0x24] -> COMMIT 0x80036CEC writes player Y 0x800a6504
```

DECISIVE capture (player, moving): at `0x80036CEC` `s7=0x800a6500` (writes player Y directly), `[gp+0x57c]=7`,
`gp+0x57c` list `@0x8009c230 = {0x800D0FA8,0x800D1028,0x800D1048,0x800D10C8,0x800D10E8,0x800D1108,0x800D1128}`
(all in the `0x800D0xxx` collision-record region), pos `Y=-109521 -> resolved Y=-109693` (**dY=-172**), `dZ=+189`,
`dX=0`. The contact list is non-empty **exactly during** the Y resolution; **CONFIRMED** the collision/floor query is
driven by the sector table `0x800a7e48` + per-sector record blocks (`0x800C/0x800D` heap), consumed via the
`gp+0x57c` list, and it explains the player-Y correction.

- **CONFIRMED:** collision/floor SOURCE is the in-RAM structure **sector table `0x800a7e48`** (count `[gp+0x508]`) +
  **collision-record blocks at `0x800C/0x800D` (heap)** reached by `[sector+0x10]`; selected matches land in the
  `gp+0x57c` list `0x8009c230`; the resolution writes player Y. This is **separate from the DAT visual floor**
  (Candidate A) and from the `gp+0x5cc`/`0x800F7xxx` grid (which had **0** winners in the same frame) — directly
  EXPLAINS G28 (deforming the DAT visual mesh did not move collision).
- **LIKELY:** the `0x800F7xxx` grid (global `0x8009f9ec`) is a secondary/horizontal broadphase (walls/objects), not
  the floor path; the `gp+0x57c` sector path is the floor/ground contact path. Sector field roles (+0x14/+0x1c min,
  +0x24/+0x28 extent, +0x10 block ptr) are LIKELY (AABB index).
- **UNKNOWN / TODO:** the **on-disk backing** of `0x800a7e48` / the `0x800C-0x800D` blocks (LEVEL.RAW-decompressed vs a
  collision sidecar vs generated) — pin via a WRITE-watch on `0x800a7e48` / the block region during **level load**
  (reload from boot). Also TODO: the exact record-field → resolved-Y arithmetic inside the helpers (which field is
  the floor height / contact normal).
- **NOT claimed:** Candidate A collision involvement (none); render-path evidence as collision evidence; any on-disk
  edit target yet.

Tooling note (DuckStation): movement injection is REQUIRED to exercise this path — in the idle save state
`FUNC_3633C` is never called for `0x800a6500` and every contact list is empty. Authoritative BP block (doc only):
`FINAL BREAKPOINTS: EXEC 0x80036CEC` (filter `s7==0x800a6500`), `EXEC 0x800368E8` (gp+0x57c store). No patch/build/
memory-write performed; save state not overwritten.

---

## 2.9 G29 LIVE — collision/floor ON-DISK SOURCE = LEVEL.RAW (decompressed) — full disk→player-Y chain (2026-06-15)

From the **pre-load** save state `SCUS-94288_2.sav` (paused at the post-cutscene black screen; `[0x800a7e48]=0`,
sector count `[gp+0x508]=0` — i.e. before the build), a WRITE-watch on the sector-table global caught the build, and a
second WRITE-watch one level upstream pinned the on-disk source. **CONFIRMED, all addresses live-verified:**

```
LEVEL.RAW  (compressed, on disk)
  -> loaded to the high heap 0x80115aac by fcn.8003a318                                 (G22)
  -> DECOMPRESSED per-chunk by fcn.8001a1dc into the 0x800F7xxx region                  [WRITE hit pc=0x8001A60C, ra=0x8003A4EC;
        (byte copy lbu/sb; compressed src a0/s5 in [0x80115aac,0x801cc690))               ra = the lw s4,(fp) after jal 0x8001a1dc, G25]
  -> processed/scaled (<<5) into the SECTOR TABLE 0x800a7e48 (+ block ptrs to 0x800C/0x800D record blocks)
        by the builder 0x80030F60.. (copies fields from source rec t1=0x800F7BF8; caller ra=0x800314CC)   [builds 0x800a7e48]
  -> AT RUNTIME (player moving): player XZ 0x800a6500 -> sector-table AABB (0x80036700/0x80036804)
        -> [sector+0x10] block -> 0x800D0xxx records (0x80036820..) -> matches into gp+0x57c list 0x8009c230 (store 0x800368E8)
        -> resolution helpers 0x800345cc / accumulate 0x80035ED8 -> resolved [sp+0x18..] -> COMMIT 0x80036CEC writes player Y 0x800a6504
```

- **CONFIRMED:** the collision/floor SOURCE FILE is **LEVEL.RAW** (decompressed at load into `0x800F7xxx`, then built into
  the sector table `0x800a7e48` + record blocks). The pre-load watch (`[0x800a7e48]=0` → build) and the decompressor
  WRITE hit (`pc=0x8001A60C` inside `fcn.8001a1dc`, `ra=0x8003A4EC` inside `fcn.8003a318`, compressed src in the
  LEVEL.RAW buffer) make this a **direct disk→player-Y data path**. This finally gives the G22–G25 LEVEL.RAW pipeline
  its payoff: LEVEL.RAW carries the **collision/floor** data.
- **EXPLAINS G28 definitively:** collision is in **LEVEL.RAW**, the visual floor (Candidate A) is in **LEVEL.DAT** — two
  different files — so the G28 DAT visual deform could not move collision.
- **EDIT IMPLICATION (TODO, not done):** LEVEL.RAW is **compressed** (G23–G25 codec `fcn.8001a1dc`), so a controlled
  collision edit needs decompress→edit→recompress, or locating the specific compressed chunk that yields the
  `0x800F7xxx` record(s) of interest. No edit attempted.
- **STILL OPEN (TODO):** the exact decompressed record format in `0x800F7xxx` / `0x800D0xxx` (which field is floor
  height vs AABB vs normal) and the record→resolved-Y arithmetic inside the helpers.
- **Operator/tooling notes:** movement injection is REQUIRED to exercise the runtime path; the build happens during the
  ~10–20 s level load, so WRITE-watch timeouts of ~30–45 s suffice (no need for minutes). Pre-load state slot 2 is
  ideal (`[0x800a7e48]=0` at load). No patch/build/memory-write; save state not overwritten; slots 1 & 2 backed up.

---

## 2.10 G29 LIVE — collision record format = PLANE; floor resolution = signed plane-distance clamp (2026-06-15)

Decoded the `0x800D0xxx` record format and the record→resolved-Y math, live (moving player) + r2. The collision records
are **collision PLANES** (faces), and the resolver `0x800345cc` does a signed point-vs-plane test per record.

**Record format (32-byte record; the gp+0x57c list stores `record+12` = `s0`; sector-relative coords):**
```
s0+0  s16 = normal.x      s0+2  s16 = normal.y      s0+4  s16 = normal.z     (floor planes: |normal.y| dominant)
s0+6  s16 = refpt.x       s0+8  s16 = refpt.y       s0+0xa s16 = refpt.z     (each <<5 = x32 -> world units;
                                                                              matches the >>5 grid quantization)
s0+0xc.. remaining bytes  = AABB bounds for broadphase selection (read by the builder loop 0x80036820) + LIKELY
                            edge/extra data (exact remainder = TODO)
```

**Resolver plane test (`0x80034750..0x800347b8`, per record; CONFIRMED by disasm + read-watch):**
```
P = sector-relative (pos+delta)  [sp+0x48/0x4c/0x50]   ; sector origin from 0x800a7e48[idx], idx from list 0x80091718
d = normal.x*(P.x - 32*refpt.x) + normal.y*(P.y - 32*refpt.y) + normal.z*(P.z - 32*refpt.z)
d = d >> 14            (sra 0xe ; fixed-point)
if d >= 0  -> skip this record (point is in FRONT of the plane = no penetration)   [bgez @0x800347bc -> 0x80034a3c]
else       -> penetrating; a second dot with pos-only [sp+0x38/0x3c/0x40] gives the swept crossing -> clamp the move
              onto the plane; the resolved per-axis delta is accumulated (0x80035ED8) and committed (0x80036CEC).
```
Record read CONFIRMED at `0x80034760` `lh t1,(s0)` (read-watch reported PC `0x80034764` = read+4). Sector entry
(`0x800a7e48[idx]`): `+0/+4/+8` = origin X/Y/Z (makes coords sector-relative), `+0x10` = record-block pointer.

**Live example (player frame):** record `0x800D0FA8` → normal `(-1941, -15885, 3509)` (|Ny| dominant ⇒ near-horizontal
floor/ceiling plane), refpt `(-461, 249, 296)*32`; sector idx 104 (`0x800A91C8`) origin Y `-123808`; player Y
`-109521 -> resolvedY -109693`.

- **CONFIRMED:** collision/floor geometry = **planes** (`normal` + `refpt`), NOT a scalar "floor height". Floor planes
  have a dominant `normal.y`. The resolved player Y is the position **clamped against the set of `gp+0x57c` plane
  records** under the player (selected by the sector-table broadphase). `refpt` is `<<5` (×32) — same scale as the grid.
- **LIKELY:** `normal` is a fixed-point unit vector (the `>>14` after the s16×s16 dot ≈ normalize); the dominant-axis
  sign encodes facing (floor vs ceiling). The remaining record bytes carry the selection AABB + possibly edge planes.
- **TODO / OPEN:** the exact clamp-back arithmetic (`0x800347c4..0x80035ec0`) that turns a penetrating crossing into the
  per-axis delta, and the precise meaning of the remaining record bytes. A byte-exact field→Y formula or an edit test
  would want poke-and-observe, which the no-memory-write guardrail precludes here (would need the LEVEL.RAW edit path).
- **Ties together:** these plane records are the `0x800D0xxx` data decompressed from **LEVEL.RAW** (§2.9) and indexed by
  the sector table (`0x800a7e48`, §2.8); the player walks on them via the `gp+0x57c` list. Visual floor (Candidate A,
  LEVEL.DAT) is unrelated geometry — final confirmation of the G28 split.

---

## 2.11 G29 LIVE — clamp math complete: swept plane-crossing → nearest in-face hit → stop-with-skin (2026-06-15)

Finished the resolver `0x800345cc` per-record clamp (CONFIRMED by disasm `0x800347c4..0x80034b30` + the face test).
Per candidate plane record (`gp+0x57c` list), in sector-relative space (origin `0x800a7e48[idx]`):

```
d_after  = ( normal · (pos+delta − 32·refpt) ) >> 14     [P+δ = sp+0x48/0x4c/0x50]   -> s4   (0x80034750..0x800347b8)
d_before = ( normal · (pos       − 32·refpt) ) >> 14     [P   = sp+0x38/0x3c/0x40]   -> s2   (0x800347c4..0x80034808)
SWEPT TEST: process only if d_before >= 0 AND d_after < 0   (move crosses the face front→back)
            (bgez s4 skip @0x800347bc ; bltz s2 skip @0x8003480c)
crossing[i] = delta[i] * d_before / (d_before − d_after)    (div blocks 0x80034814..0x800348dc → a1/a2/a3)
POINT-IN-FACE: jal 0x80032610 — picks the normal's DOMINANT axis (max(|nx|,|ny|,|nz|)) and runs a 2D point-in-polygon
            using record edge fields s0+0xc/+0xe/+0x10/+0x12/+0x14/+0x16; skip the record if the crossing is outside.
NEAREST: keep the smallest t = (d_before<<14)/(d_before−d_after) vs running best [sp+0x78] (slt @0x800349f0);
            save winner → plane [sp+0x68], d_before [sp+0x7c], d_after [sp+0x80], record [sp+0x88], sector [sp+0x98], count++ [sp+0x90].
```

After the loop (`0x80034a50+`): validate the winner (`jal 0x800322a0`); if contact count > 0, apply the **stop-with-skin**
clamp per axis and write the resolved position into the working buffer `s5` (= caller `sp+0x18`) → COMMIT `0x80036CEC`
→ player Y `0x800a6504`:

```
resolved[i] = pos[i] + delta[i] * (d_before>>3) / ( (d_before>>3) − ((d_after − 0xc0) >> 3) )      (0x80034aa4..0x80034b30)
```

- **CONFIRMED:** the `−0xc0` (192) bias on `d_after` is a **COLLISION SKIN** — Flik stops ~192 (sector units) *in front
  of* the floor plane, not exactly on it. (Distinct from FUNC_3633C's `±0xc80`/3200 entry probe bias in §2.5.)
- **CONFIRMED record format (resolver-final):** `s0+0/+2/+4` = plane normal (fixed-point unit vector; the `>>14`
  normalizes the s16×s16 dot); `s0+6/+8/+0xa` = reference point (`×32` → world units; also the polygon anchor);
  `s0+0xc..+0x16` = face-polygon edge/vertex data (consumed by the in-face test `0x80032610`). Floor planes ⇒
  `|normal.y|` dominant.
- **CONFIRMED full contact-clamp path:** plane record → swept signed distance → nearest in-face crossing →
  stop-with-skin → resolved player Y. The complete record→Y math for a floor contact is now decoded.
- **TODO (minor, do not affect the clamp formula):** the no-contact branch `0x80035210`, any slide/re-test iteration
  for multi-plane sliding, the winner-validator `0x800322a0` internals, and the remaining record bytes (`s0+0x18..`).

This closes the §2.10 "exact clamp arithmetic" TODO. Next per the plan: the **LEVEL.RAW collision edit** — pick a floor
plane record, locate its compressed LEVEL.RAW chunk, decompress→edit (e.g. nudge `refpt.y` or `normal`)→recompress, and
watch Flik's footing move (the collision analog of the G28 DAT visual test).

---

## 2.12 G29 LIVE — pick target floor plane + trace to LEVEL.RAW (steps 1 & 2 for the collision edit) (2026-06-15)

**Step 1 — target floor plane (slot 1, moving player).** The player's `gp+0x57c` list held **7 records, all sector-104
floor planes** (`|normal.y|` ≈ 15000–16300 ≈ 2¹⁴ ⇒ near-unit up-normals; normals are 1.14 fixed-point ÷16384). Picked
the flattest:
```
RECORD @ 0x800D10E8   (resolver s0 = this addr; normal at +0)   sector 104 @ 0x800A91C8 origin=(46784,-123808,-74400)
  normal  = (654, -16259, 1905)          (|ny| dominant -> floor)
  refpt   = (-918, 298, -284)            (sector-relative; x32 -> world (-29376, 9536, -9088))
  full 0x20 bytes = 8e02 7dc0 7107 6afc 2a01 e4fe  ebfd 002b 2602 d3ff 7f00 4b04 55fa 1502 0100 0010
  fields: +0/+2/+4 normal ; +6/+8/+0xa refpt ; +0xc..+0x16 face-edge data ; +0x18.. (-1451,533,1,4096) link/flags
```

**Step 2 — provenance (slot 2 pre-load, WRITE-watch 0x800D10E8 through the load).** CONFIRMED the record is written by
the **LEVEL.RAW decompressor `fcn.8001a1dc`** (`pc=0x8001A610`/`0x8001A654`, `ra=0x8003A4EC` = loader `fcn.8003a318`)
— i.e. **direct LEVEL.RAW decompressor output**, NOT a post-decompress builder. The writing pass is a **back-reference
match** (`t6=0x800D0FC5` points into earlier decompressed output) ⇒ the record's bytes are genuine **LZ data, not a
plain literal**. Compressed source is in the LEVEL.RAW buffer `[0x80115aac, 0x801cc690)` (cursor `s5≈0x8015ED7B` =
`LEVEL.RAW+0x492CF` when `normal.x` was written; dest base `fp≈0x800C1688` = the sector block base `0x800C1690`−8).

- **DETERMINISM CONFIRMED:** the slot-2 load wrote byte `0x8e` to `0x800D10E8` = the record's `normal.x` low byte from
  slot 1 ⇒ the record **address and content are stable across loads** (same level, deterministic heap). This is exactly
  what the live RAM-edit validation needs (the address `0x800D10E8` is a reliable lever).
- **IMPLICATION:** a permanent *disk* edit needs decompress→edit→**recompress** (the `fcn.8001a1dc` codec) — but the
  agreed **RAM-edit validation** (write the in-RAM record / sector field, screenshot via `emulator.captureFrame`,
  read resolved-Y at `0x80036CEC`) needs none of that and is the next step.
- **DEFERRED (only needed for a permanent disk patch):** exact compressed-chunk boundary. The `fcn.8003a318` subtype
  dispatch writes overlapping dest regions (the record address is touched by >1 pass; the live value is the last
  writer's), so a clean single compressed-chunk → record-byte map needs the subtype-dispatch decode (G25). Not pursued
  now since the RAM edit doesn't require it.

**Edit levers (for the RAM validation):** the resolver reads this record's `normal`/`refpt` (CONFIRMED read at
`0x80034760`) and the sector origin `0x800a7e48[104]+0/+4/+8`. To raise/lower this floor: nudge `refpt.y`
(`0x800D10E8+8`, sector-relative, ×32) or the sector Y origin (`0x800A91C8+4`); both feed the §2.11 clamp. (No edit
performed in steps 1 & 2 — read-only trace only.)

---

## 2.13 G29 LIVE — collision EDIT VALIDATED in RAM (Flik's footing follows the edited floor) (2026-06-15)

Confirmed the collision/floor source is **editable and controls Flik's footing**, via live RAM edits (DuckStation
`writeU32` + `captureFrame`; no disk patch). Edited the **sector-104 origin Y** (`0x800A91C8+4`, the value the resolver
subtracts to form sector-relative coords), then walked Flik (`left`) 40 frames from the same slot-1 start:

```
edit ΔoriginY     endX    endY      endY-baseline
   0 (baseline)   30600  -107934      0
  +8192           30744  -100435    +7499
 +16384           30668   -91438    +16496
  -8192           30284  -115537    -7603
```

**DECISIVE (rules out terrain/"walking up a hill"):** `endX ≈ 30600` is identical across all four runs (same input,
same path, same ground), yet **`endY` scales ~1:1 with the arbitrary edit value**. A hill would give the same `endY`
regardless of my edit. Screenshots (`captureFrame`) confirm Flik at clearly different heights vs the *unchanged* visual
terrain — the exact inverse of G28 (G28 moved the LEVEL.DAT *visual* floor and collision stayed; here we move the
LEVEL.RAW-derived *collision* floor and the visual stays).

- **CONFIRMED:** writing the in-RAM collision structure (sector origin / plane records) moves Flik's resolved Y — the
  full chain LEVEL.RAW→…→player-Y is now demonstrated end-to-end *and* shown editable. The RAM edit faithfully mirrors
  what a LEVEL.RAW edit would do (LEVEL.RAW only populates these structures at load).
- **Mechanic (important):** the resolver re-clamps Flik **only while he is MOVING**. Editing the floor while he stands
  still does nothing until he moves (an instant-frame test with Flik stationary showed dY=0). So edits manifest over a
  walk, not statically.
- **Fall-through:** lowering the floor (`-8192` → endY -115537, and larger negatives) drops Flik / lets him fall through
  — the visual LEVEL.DAT ground remains but his LEVEL.RAW collision floor moved down/away. This is the edit working
  (and the visual/collision split again).
- **TODO:** single-plane (`refpt.y` of the *specific* winning record) granularity — the sector-origin edit is proven;
  the per-plane test needs a corrected capture of the resolver's winning record (the `sp+0x88` read was buggy). The
  permanent disk patch (decompress→edit→recompress LEVEL.RAW) remains optional/future; RAM editing covers validation.

---

## 3. Task 1 — static reconnaissance (existing evidence only; no new function names invented)

Re-inspection of `geometry_collision_consumers.c` (G5), `docs/EXECUTABLE_AND_OVERLAYS.md`,
`src_re/contact_walker_800586b0.c`, and `src_re/re_types.h` yields the candidate runtime collision /
floor-contact state below. **No static parser-geometry collision consumer exists** (G5 negative), so the
collision source is reached either by a non-global pointer (invisible to a global text scan) or from a
different data source. That is exactly why G29 is **runtime-first**.

### 3.1 Candidate runtime collision / floor-contact targets

| # | address / fn | read/write site (if known) | why relevant | confidence | suggested watch |
|--:|--------------|----------------------------|--------------|-----------|-----------------|
| 1 | `0x800a6504` **player Y** (`G_PLAYER_Y`) | many readers; writer(s) TBD | the value that *must* change when Flik steps onto/off a surface; floor contact resolves here | **CONFIRMED** address (`re_types.h`); writer-of-Y **UNKNOWN** | **WRITE** watch — find the floor/movement integrator |
| 2 | `0x800a6500` / `0x800a6508` **player X / Z** | many readers | XZ position that *selects* which floor cell/triangle the collision query uses | **CONFIRMED** address | **WRITE** watch (secondary) + read at the Y-writer |
| 3 | `fcn.8005b134` **player-pos writer** | dispatches to Region-A overlay verbs `0x800b3adc/3ae8/3aec/3c54/3c5c` | G5 named it the player-pos writer / state dispatcher; **LIKELY the movement/floor-snap integrator** | **LIKELY** (named writer) / role **UNKNOWN** | **EXEC** BP `0x8005b134`; confirm it writes Y at #1 |
| 4 | progress/pos writers `fcn.80047284 / 80048138 / 8004a700 / 800563d4 / 80056f68 / 8005b12c` | write `0x800a6580` progress block via base `0x800a6500` (EXEC doc L409) | **CONTRADICTS** the "sole writer = `fcn.8005b134`" note → which one writes *Y* (`0x800a6504`) must be disambiguated at runtime | **UNKNOWN** (progress vs position) | resolved by the #1 WRITE watch (records the real PC) |
| 5 | `fcn.80025084` **oriented containment/range test** | reads actor `0x800a0a64` (+0x80 coords `<<5`, +0x66 extent), object table `0x800a6300`, matrix `0x80090fb0`; caller `fcn.8004d224` @`0x8004d3bc` | an oriented bounding/containment test on world/actor data — a plausible **wall/ledge/object collision** primitive (NOT parser geometry, NOT pickups) | **CONFIRMED** shape / collision-role **UNKNOWN** | **EXEC** BP `0x80025084` while walking into wall / off ledge; log inputs |
| 6 | `0x80090fb0` 3×3 matrix | used by #5 | orientation basis for the containment test | **CONFIRMED** (used by #5) | READ watch only if #5 fires on floor/wall |
| 7 | `PAD\PATH*.BIN` (≤1.3 KB) + loader `fcn.80046330` (`a0`=filename, `a1`=dest) | strings @ ~`0x8007ee94`; universal file loader | external "pathfinding" data — a candidate **pathing/sector grid** source (CAUTION: likely **AI/enemy** pathing, not Flik floor height) | **LIKELY external** / role for *floor* **UNKNOWN** | **EXEC** BP `0x80046330` entry; log `a0`/`a1`/`ra`; find PATH dest buffer |
| 8 | `0x800b0d18` contact array (64×`0x38`) + walker `fcn.800586b0` | walker reads player XYZ with **Y bias −0x1cc0** | **OUT OF SCOPE / DECOY** — pickup proximity, not world floor collision; listed only to *exclude* it | **CONFIRMED pickup system** | do **not** watch for floor; ignore the `−0x1cc0` Y bias |

### 3.2 Key static facts that shape the plan (CONFIRMED, from G5)

- Geometry record-type slots `TT[0x01/0x0b/0x0c/0x0d/−2..−7]` have **zero** readers (only `TT[0x3f]`
  pickups). `G_TRAIL_BLOCK_PTR`/`G_PASS3_BASE_PTR` are read only by the render driver `fcn.800224ec`.
  → No static collision consumer of the parser geometry. The collision query reaches its data by a
  **non-global pointer** or from a **non-parser source**.
- ~40 functions read player pos `0x800a6500/04/08`; **none** also reads a parser-geometry handle. So the
  floor-height computation does not statically touch Candidate A's vertices — consistent with G28's
  observed split.
- `fcn.80025084` and the contact walker read **actor/pickup** data, **not** the parser geometry.

---

## 4. Task 2 — runtime watch plan (operator runbook)

Goal of every pass: **find state that does NOT follow the visual mesh** — i.e. the floor height / contact
value Flik actually stands on, and the address it is read from. Keep **3–6 breakpoints/watchpoints per
pass**. DuckStation GUI has no conditional BPs, so each pass logs and the operator filters by hand.

> **Build note:** these passes run on the **pristine** retail image (collision lives in pristine data; the
> G28 deform is purely visual). The G28 patched image is only needed in Pass 3 step (c) to confirm the
> floor-height *source value* is identical whether or not Candidate A is deformed.

### Pass 1 — identify the player-Y writer (the floor/movement integrator) — **DONE 2026-06-15**
RESULT (see §2.5): the Y writer is **`FUNC_3633C` @ `0x8003633c`** (caller `0x800495c8`, RA `0x800495d0`). The
decisive **floor/contact-corrected** store is **`0x80036cec`** (`sw v1,4(s7)`, `v1=[sp+0x1c]`, observed as PC
`0x80036cf0`); the entry/exit `±0xc80` Y bias (`0x80036380`/`0x80036d54`, observed `0x80036384`/`0x80036d58`)
is a probe transform, not a floor value. Active collision helper = **`0x800345cc`** (`ra=0x80036c70`).
**NOT `fcn.8005b134`** (zero jal callers; superseded/pending).

### Pass 2 — find the floor-height SOURCE `S` (start from the writer sites, NOT render code)
Pre-req: Pass 1 done. Keep ≤5 BPs. **Pristine image** (collision lives in pristine data).
1. **EXEC** `0x80036380` (entry bias). Record `s7` (expect `0x800a6500`), `[s7+4]` = Flik's **pre-bias entry Y**,
   `s5` (`0x800a652c`), `a2` (`0x800a6582`). Confirms the struct binding before any move.
2. **EXEC** `0x80036cec` (reports as `0x80036cf0`). Dump the scratch buffer **`[sp+0x18]`/`[sp+0x1c]`/`[sp+0x20]`
   = collision-RESOLVED X/Y/Z** = the floor-corrected position about to be written to Flik. This is the value to
   track over the floor (and, in Pass 3, over the deform).
3. **EXEC** `0x800345cc` (the active collision helper). Record `a0`(=`sp+0x10` point buf, in/out), `a1`(=`s4`),
   `a2`(=`s5`), `a3`(=`s3`), and **`[gp+0x57c]` = `0x80082314` = collision-candidate COUNT**. Step the prologue
   (after the `blez` at `0x800345d4`-region) to find the **candidate-list base pointer** and the `lh`/`lw` that
   loads the **floor-height operand `S`**; record `S`'s absolute address.
4. **READ** watch on `S` (once identified): confirm it is read each frame while standing on the floor.
- (a)/(b) folded into BPs 2–4 above: at `0x80036cec` you have the resolved floor Y; at `0x800345cc` you find the
  memory operand `S` that produced it; the READ watch confirms `S` is the live source.
- (c) **Classify the source address** `S`:
    - DAT-backed: `S − 0x801607f8 ∈ [0, 0x51418)` → in LEVEL.DAT (but NOT Candidate A's vertex band
      `~0x80179188`); record the DAT offset.
    - LEVEL.RAW-decompressed: `S < 0x8015fcbc` (decompressor output region, G25) or in the high heap
      `[0x8015fcbc, 0x801cc390)`.
    - Sidecar buffer: matches a PATH/`.all`/heap dest from Pass 4.
    - Generated runtime table: none of the above (record the writer of `S` for a future phase).

Promotes: `S` → **floor-height source (LIKELY)** when the Pass-1 writer reads it to compute Y; → **CONFIRMED**
when (Pass 3) the value tracks Flik's XZ over the floor and is independent of the Candidate-A deform.

### Pass 3 — differential: does the floor height follow the visual mesh? (the decisive test)
Watches (≤2): **READ** watch on `S` (from Pass 2) [+ optional **WRITE** watch `0x800a6504`].

Operator actions & records:
- (a) On the **pristine** image, walk Flik onto the patch that corresponds to Candidate A's projected area;
  record `S`'s value (the floor height under Flik) and Flik's Y.
- (b) Walk onto adjacent normal floor; record `S` and Y again. (Establishes how `S` varies with XZ.)
- (c) **Switch to the G28 patched image** (`ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue`); repeat (a) over the
  *visibly caved* patch. Record `S` and Y.
- **Decisive evidence:** if `S` (and Flik's standing Y) are **identical** over the deformed patch and the
  pristine patch, the collision/floor source is **independent of Candidate A** → `S` is the real
  collision/floor source (or one layer of it), and Candidate A holds **no** collision data. This both
  **CONFIRMS** `S` as the floor source and re-confirms the G28 visual/collision split with a concrete
  address.

### Pass 4 — sidecar / PATH trace (does an external file feed `S`?)
Watches (≤3):
1. **EXEC** BP `0x80046330` (universal file loader entry; `a0`=filename C-string, `a1`=dest).
2. One-shot **EXEC** at the caller `ra` to capture `v0` (bytes read / size).
3. (optional) **WRITE** watch on `S` during load, to catch the buffer being filled.

Operator actions & records:
- (a) From LEVEL01 load through gameplay, log every loader hit: `a0` (filename), `a1` (dest), `ra`
  (caller→subsystem), size. **Look specifically for `PAD\PATH*.BIN`** and for any load whose
  `[a1, a1+size)` **brackets `S`** from Pass 2.
- (b) If a PATH/sidecar buffer brackets `S` → that file is the collision/floor/pathing source
  (record file + offset `S − a1`).
- **Caution:** PATH files are tiny (≤1.3 KB) and historically AI/enemy pathing — they may **not** be Flik's
  floor height. Treat a PATH hit as **LIKELY pathing-grid**, not automatically floor collision, until
  Pass 2/3 ties `S` into Flik's standing Y.

### Pass 5 (lower priority) — role of the oriented containment test `fcn.80025084`
Watches (≤2): **EXEC** BP `0x80025084` [+ caller `0x8004d224` @`0x8004d3bc`].

Operator actions & records:
- (a) Walk Flik **into a wall** and **off a ledge**; record whether `fcn.80025084` fires and with what
  inputs (actor `0x800a0a64`, point `a0/a2`, matrix `0x80090fb0`).
- Promotes: if it fires on wall/ledge contact and gates movement → **wall/ledge collision primitive
  (LIKELY)**; if it never fires during locomotion → exclude from the floor question.

---

## 5. Task 3 — false-positive guardrails (explicit)

Do **NOT** treat any of the following as collision evidence:

1. **Render path `fcn.80010000` / `0x800108b4` / `0x80010718` is NOT collision.** It is the visual emitter
   (G10–G16, G28). A hit there proves a vertex is *drawn*, never that it is *tangible*.
2. **Visual deformation is NOT tangibility.** G28's caved mesh did not move Flik's surface. A future visible
   edit that deforms a mesh says nothing about collision unless Flik's standing Y (`0x800a6504`) follows it.
3. **`0x801bdc58` is NOT a payload.** It is compressed LEVEL.RAW source (G26): first word `0x70d4001a`
   (impossible count), WRITE-watch 0 hits. Never use it as a floor/collision pointer. Keep it distinct from
   the valid DAT-backed Candidate E `0x8018dc58`.
4. **Do NOT assume LEVEL.RAW** because of the old retracted heap-floor theory. The G22–G25 LEVEL.RAW pipeline
   is a *resource* characterization; it has **not** been tied to collision. Only Pass 2/3 address
   classification may implicate LEVEL.RAW — with evidence, not by inheritance.
5. **Do NOT assume LEVEL.DAT holds collision** just because the *visual* floor (Candidate A) is DAT-backed.
   Render-DAT-backed ⇏ collision-DAT-backed. The G28 split is direct evidence against this assumption.
6. **The contact walker's player-Y bias `−0x1cc0` is a PICKUP artifact**, not floor contact. Ignore it for
   the floor question; do not interpret `0x800b0d18` / `fcn.800586b0` as floor collision.

---

## 6. Evidence thresholds (UNKNOWN → LIKELY → CONFIRMED)

| claim | LIKELY when | CONFIRMED when |
|-------|-------------|----------------|
| function `WPC` is the floor/movement integrator | a WRITE watch on `0x800a6504` fires from it while standing/walking | the same PC writes Y every frame on the floor AND the value tracks the surface (steps/slopes change it) |
| address `S` is the floor-height source | the integrator reads `S` to compute Y | `S` varies with Flik's XZ over the floor **and** is **identical** over the pristine vs G28-deformed patch (Pass 3) — i.e. independent of Candidate A |
| a sidecar/PATH file is the collision/pathing source | `EXEC 0x80046330` logs the file AND `[a1,a1+size)` brackets `S` | a later (future-phase) edit of that file at `S − a1` moves Flik's standing surface |
| `fcn.80025084` is wall/ledge collision | it fires when Flik contacts a wall/ledge | gating its result changes whether Flik passes the wall/ledge |
| Candidate A has no collision data | the deform did not move collision (G28) | Pass 3 (c) shows `S` and Flik Y unchanged over the deformed patch |

---

## 7. Guardrails (this pass)

- **No patch. No build. No patch-script run. No runtime-address edit. No game-data mutation.** This file is
  analysis + runbook only.
- Do **not** commit generated DAT/BIN/CUE/RAM/save-state/screenshot artifacts. Leave `G28_Deformity`
  unstaged/untouched.
- Do not modify `re_types.h`.
- Do not claim a collision source without **runtime** evidence (Pass 1–4 hits).
- Keep `CONFIRMED` / `LIKELY` / `UNKNOWN` / `TODO` labels exact. Visual ≠ collision.

---

## 8. Next runtime action (when the operator is ready — not run here)
**Pass 1 DONE** (§2.5): writer = `FUNC_3633C` @ `0x8003633c`, decisive commit `0x80036cec`, helper `0x800345cc`.
**Pass 2 DONE** (§2.6): the resolved Y at `0x801FFE1C` is FUNC_3633C's `sp+0x18` working buffer; written by an
accumulate `pos += delta` in helper `0x800345cc` (`0x80035ed8`) and seeded by a copy in FUNC_3633C (`0x80036bdc`).
The deltas come from the per-frame collision-candidate list (counts `[gp+0x57c]=0x80082314`/`[gp+0x5cc]=0x80082364`),
produced by sweep helper `0x80035f24`; the list's **backing region is still UNKNOWN**. (Also: that invocation ran
on a **stack** position vector `s7=0x801FFEA8`, not the player global — link to `0x800a6504` is a separate step.)
**Next = Pass 2-next (§2.6):** EXEC `0x80035f24`, dump its pointer args + candidate-list base, find the floor-height
read `S`, classify its band. Pass 3 (G28 differential) only after `S` is identified. No patch/build.
