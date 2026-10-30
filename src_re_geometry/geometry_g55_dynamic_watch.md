# G5.5 — Dynamic geometry read/effect confirmation (watch design + results)

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[G4 render](geometry_render_consumers.c) · [G5 collision](geometry_collision_consumers.c)

**Purpose.** Unblock G6 by *dynamically* proving that one specific parser-geometry field is read at
runtime, and identifying the reading function(s) — so an eventual G6 diagnostic edit has a
PROVEN field → observable-effect chain instead of a LIKELY (static-only) one.

**Guardrails (unchanged):** no DAT/BIN/CUE patching, no ISO build, no G6 yet, no inferring
collision/render semantics without runtime evidence. Boot the **pristine original image**
`Disney-Pixar A Bug's Life (v1.0).cue` — a read-watch needs no patched data.

**Tooling reality (CONFIRMED 2026-06-14).** No scriptable PS1 debugger is installed
(no PCSX-Redux; RetroArch has no cores; host `gdb` has no MIPS target/stub). **DuckStation**'s GUI
debugger is the only option, so this phase is executed *manually* by the operator following the
runbook in §5 and reporting the hit table back into §6.

---

## 1. Chosen source record and field(s) (CONFIRMED from pristine DAT)

Pristine `DAT/LEVEL01_LEVEL.DAT`, sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`, size `0x51418`.

Target **s0 = file offset `0x4e00`** — a CONFIRMED **bit3** source record (G2 sample), chosen because
its scale triple is the clean identity `(0x1000,0x1000,0x1000)` = 1.0 each (12.4 fixed point):

| field | rec off | value (pristine) | width | role | confidence |
|-------|--------:|------------------|------:|------|------------|
| vec[3]   | `+0x00` | `(4693,-4312,-665)` | 3×s32 | coordinate-like | CONFIRMED shape / role UNKNOWN |
| angle[3] | `+0x0c` | `(471,927,3705)`    | 3×s16 | → matrix setup `fcn.80017b98` | CONFIRMED used |
| **scale[0]** | `+0x12` | `0x1000` (4096) | s16 | matrix x-scale | CONFIRMED used (pass-1 bit3) |
| **scale[1]** | `+0x14` | `0x1000` (4096) | s16 | matrix y-scale | CONFIRMED used |
| **scale[2]** | `+0x16` | `0x1000` (4096) | s16 | matrix z-scale | CONFIRMED used |
| unk18    | `+0x18` | `0xce00` | u32 | not relocated (flag 0x20 never set) | CONFIRMED present / role UNKNOWN |
| **ptr1c (payload)** | `+0x1c` | `0x3703c` | u32 | relocated → payload band | CONFIRMED |

Pass-1 mapping (CONFIRMED by walking the pass-1 table @file `0x1512`, stride `0x14`):
- s0=`0x4e00` is **pass-1 entry index 261**; entry flag halfword = `0x0049` (bit3 `0x8` set).
- → its `0x20`-byte **output record** lives at output-record index **261**.

## 2. Runtime addresses (RUNTIME-COMPUTED — do not hardcode)

All addresses derive from the live base. **Read `DATbase` from RAM first**, after the level loads:

```
DATbase            = mem32[0x80082498]            # set by loader after fcn.8001cdc0 parses LEVEL01
filesize           = 0x51418                       # CONFIRMED (pristine DAT)
output_base        = DATbase + filesize            # = DATbase + 0x51418  (pass-1 output array)

# --- Source-record A (s0 = 0x4e00) ---
s0                 = DATbase + 0x4e00
scale0_addr        = DATbase + 0x4e12              # s0 + 0x12   (WATCH 1)
scale1_addr        = DATbase + 0x4e14              # s0 + 0x14   (WATCH 2)
scale2_addr        = DATbase + 0x4e16              # s0 + 0x16   (WATCH 3)
payload_ptr_addr   = DATbase + 0x4e1c              # s0 + 0x1c   (optional WATCH 5)

# --- Output record for the SAME entry (index 261) ---
out261             = output_base + 261*0x20         # = DATbase + 0x534b8
out261_matrix0     = DATbase + 0x534b8             # out+0x00, matrix[0] halfword (WATCH 4a)
out261_matrix8     = DATbase + 0x534c8             # out+0x10, matrix[8] halfword (WATCH 4b, optional)
out261_srcptr      = DATbase + 0x534d0             # out+0x18, should READ as DATbase+0x4e00 (WATCH 4c, optional)
```

**Cross-check absolutes** if (and only if) the live read gives the LIKELY `DATbase = 0x801607f8`
(G3). These are a sanity check, **not** to be used blind:

| watch | name | LIKELY absolute (DATbase=0x801607f8) | mirror (& 0x1FFFFF) |
|------:|------|--------------------------------------|---------------------|
| 1 | scale0 `s0+0x12` | `0x8016560a` | `0x16560a` |
| 2 | scale1 `s0+0x14` | `0x8016560c` | `0x16560c` |
| 3 | scale2 `s0+0x16` | `0x8016560e` | `0x16560e` |
| 5 | payload ptr `s0+0x1c` | `0x80165614` | `0x165614` |
| 4a | out261 matrix0 `+0x00` | `0x801b3cb0` | `0x1b3cb0` |
| 4b | out261 matrix8 `+0x10` | `0x801b3cc0` | `0x1b3cc0` |
| 4c | out261 srcptr `+0x18` | `0x801b3cc8` (reads `0x801655f8`) | `0x1b3cc8` |

If the live `[0x80082498]` differs from `0x801607f8`, **recompute** — the offsets `0x4e12 / 0x534b8`
etc. are fixed; only the base moves.

## 3. Watchpoint plan + expected interpretation

| # | watch addr (formula) | type | what it proves | expected hit |
|--:|----------------------|------|----------------|--------------|
| 1 | `DATbase+0x4e12` scale0 | read | parser/other read of the editable scale field | ≥1 at **load** from `fcn.8001cdc0` (`0x8001cdc0–0x8001d3cc`); then likely silent |
| 2 | `DATbase+0x4e14` scale1 | read | same | same |
| 3 | `DATbase+0x4e16` scale2 | read | same | same |
| 4a | `DATbase+0x534b8` out261 matrix0 | read | **per-frame render read** of the derived matrix | repeated, from `fcn.800140a0`/`80014360`/`800146e0` (`0x80014xxx`) via `fcn.800224ec` |
| 4c | `DATbase+0x534d0` out261 srcptr | read | whether the consumer chases `out+0x18` back to the source | optional |

**Hit classification (PC → function):**

| PC range | function | class |
|----------|----------|-------|
| `0x8001cdc0–0x8001d3cc` | `fcn.8001cdc0` parser | **load-time** (expected, not a per-frame consumer) |
| `0x800224ec–0x80022870` | `fcn.800224ec` render/scene driver | **render** (G4) |
| `0x800140a0–0x800146e0+` | `fcn.800140a0/80014360/800146e0` GTE helpers | **render-stage transform** (G4) |
| `0x80017b98–…` | `fcn.80017b98` matrix setup | matrix build (load or render) |
| anything else while **moving/colliding** | **UNKNOWN** | **candidate collision/pathing consumer → record exactly** |

**Decision table (from the plan):**
- Watch 4a fires only from `fcn.800224ec → fcn.800140a0/360/6e0` → **render-facing CONFIRMED**;
  G6 may propose a *render-only* diagnostic edit; collision effect remains UNKNOWN.
- Any watch fires from a **movement/collision/pathing** function too → that function is the missing
  G5 collision consumer → capture its address; update G5.
- **No** watch hits at all → the chosen record isn't active for this scene/camera → retarget
  (next candidate `s0=0x7a18`, bit3, scale `(4349,4096,3153)`) or watch the output matrix only.

## 4. Why this design (rationale)

- The **scale field** (`s0+0x12`) is exactly what a G6 edit would change in the DAT, so watch it
  directly. But the parser consumes scale **at load** to bake the output matrix; the per-frame
  consumer reads the *derived* matrix, not the source scale. Hence watch **both** the source scale
  (load-time read, watches 1–3) **and** the **output matrix** (per-frame read, watch 4a) so the full
  edit→bake→read chain is observed end to end.
- Using output record **261** (not index 0) keeps one coherent story: *this* source's scale bakes
  *this* output matrix. (Index 0 = s0 `0x4680`, a non-bit3 record — avoided.)
- Standing still isolates render reads; then moving/colliding exposes any second (collision) reader.

---

## 5. Operator runbook (DuckStation) — RUN 2026-06-14

1. Launch DuckStation; **Settings → Advanced → enable the Debugger / "CPU Debugger"** (or `View →
   Debug`). Load `Disney-Pixar A Bug's Life (v1.0).cue` (pristine; **no patched DAT**).
2. Play to **LEVEL01 gameplay** — Flik controllable, level visible (past "Press X").
3. Open **Debug → CPU Debugger → Memory** view. Go to `0x80082498`, read 4 bytes LE = **DATbase**.
   Record it. Recompute the §2 addresses from it (or confirm `0x801607f8`).
4. Add **read (data) breakpoints**: watch **1 (`DATbase+0x4e12`)** and watch **4a
   (`DATbase+0x534b8`)** first. (DuckStation: Debugger → breakpoint list → Add → Type = *Read*.)
5. With the player **standing still**, let it run several frames. For each break: record **PC**,
   the **accessed address**, the **value**, and which §3 PC-range/function it falls in. Resume.
6. **Move** Flik; walk into / along nearby level geometry, drop off an edge, bump a wall. Watch for
   any break whose PC is **outside** the parser/render ranges — record it verbatim (that would be a
   collision/pathing reader).
7. If watch 4a never fires, add **4b/4c**; if still nothing, the record may be off-camera — retarget
   to `s0=0x7a18` (recompute: scale0 `DATbase+0x7a2a`; its output index — ask, recompute on request).

**Fallback if DuckStation lacks read breakpoints:** set **execute** breakpoints at `0x800224ec`
(render driver) and `0x800140a0` (GTE helper). Confirm they fire **every frame while still**; when
`fcn.800140a0` breaks, read register **`a0`** — if it points into the trailing-table / output-record
region (`DATbase+0x1504..` or `output_base..`), that is the render read of the parser geometry.
Then move and confirm no *other* function touches those addresses.

---

## 6. RESULTS

> Status: **PART A (live data corroboration) DONE 2026-06-14**; **PART B (DuckStation watch/fallback)
> DONE 2026-06-14 but INCONCLUSIVE for field-level reads**.

### Part A — live RAM corroboration (CONFIRMED, automated via `/proc/<pid>/mem`)

Method: DuckStation runs with `ptrace_scope=0`; its guest PS1 RAM backing store is a `memfd`
mapping whose start = guest phys 0. Located it by scanning for the 28-byte s0=`0x4e00` prefix
signature, then read globals/records at `B + (guestVA & 0x1FFFFF)`. **No GUI, read-only.** This
corroborates the G2/G3 *data structures* but does **not** identify the per-frame reader (Part B).

| check | live value | expected | result |
|-------|-----------|----------|--------|
| `[0x80082498]` DATbase | `0x801607f8` | G3 LIKELY `0x801607f8` | **CONFIRMED** (was LIKELY) |
| `[0x800822f0]` G_DAT_ENTRY_COUNTER | `624` | 484+140 | **CONFIRMED** |
| `[0x800824ac]` G_TRAIL_BLOCK_PTR | `0x80161cfc` | DATbase+`0x1504` | **CONFIRMED** |
| `[0x80082508]` G_PASS3_BASE_PTR | `0x801642e4` | DATbase+`0x3aec` | **CONFIRMED** |
| s0=`0x4e00` scale `+0x12/14/16` | `0x1000,0x1000,0x1000` | DAT bytes | **CONFIRMED** |
| s0 `+0x1c` (relocated) | `0x80197834` | DATbase+`0x3703c` | **CONFIRMED** (parser relocated it) |
| out261 `+0x18` srcptr | `0x801655f8` | = s0 | **CONFIRMED** (pass-1 linked it) |
| out261 matrix rows | mag ≈4096 each | unit (scale=1.0) | **CONFIRMED** baked rotation |

Output record 261 raw @ `0x801b3cb0` = `f5015701d20fdb01cf0f6ffe3df00802c701540064fdee00f85516804f00551e`
→ matrix `[501 343 4050 | 475 4047 -401 | -4035 520 455]`, srcptr `0x801655f8`. So pass-1 DID build
the `0x20`-byte output record for this exact bit3 source, with a rotation matrix derived from
angle `(471,927,3705)` scaled by `(1,1,1)`. The payload at `+0x1c`→`0x80197834` begins
`200000000000fcffffff0000604c2800…` (role UNKNOWN, not decoded).

### LOCKED watch addresses (DATbase now CONFIRMED = `0x801607f8`)

| watch | guest addr | meaning |
|------:|-----------|---------|
| 1 | `0x8016560a` | s0+0x12 scale0 |
| 2 | `0x8016560c` | s0+0x14 scale1 |
| 3 | `0x8016560e` | s0+0x16 scale2 |
| 4a | `0x801b3cb0` | output rec 261 matrix[0] (per-frame render read target) |
| 4c | `0x801b3cc8` | output rec 261 srcptr (+0x18) |
| — | `0x80197834` | payload (s0+0x1c target) |

### Part B — reader watchpoint + execute fallback (DONE 2026-06-14; INCONCLUSIVE)

1. Chosen record / fields: s0=`0x4e00` (bit3, entry 261); scale `+0x12/14/16`; output rec 261. **CONFIRMED**
2. Runtime addresses used: DATbase `0x801607f8` (live); watch addrs above. **CONFIRMED**
3. Read-watchpoint hit table: **NO HITS** for the chosen field set.

   | watch | addr | meaning | phase(s) | hit result | classification |
   |------:|------|---------|----------|------------|----------------|
   | 4a | `0x801b3cb0` | output rec 261 matrix[0] | standing + after movement/stopped | no hits | UNKNOWN / not observed |
   | 4c | `0x801b3cc8` | output rec 261 +0x18 source pointer | standing + after movement/stopped | no hits | UNKNOWN / not observed |
   | 1 | `0x8016560a` | source s0+0x12 scale0 | standing + after movement/stopped | no hits | UNKNOWN / not observed |

4. Execute-breakpoint fallback results:

   | phase | PC | function | registers | class | interpretation |
   |-------|----|----------|-----------|-------|----------------|
   | standing still | `0x800140a0` | `fcn.800140a0` | `a0=0x80161cfc`, `a1=0x1f8003b4`, `a2=0x1f800384`, `a3=0x00000fff`; repeat count 3 | render-stage | CONFIRMED execution of the G4 trail-table helper path while idle; `a0 = G_TRAIL_BLOCK_PTR = DATbase+0x1504`. |
   | after movement / stopped | `0x800140a0` | `fcn.800140a0` | `a0=0x80161cfc`, `a1=0x1f8003b4`, `a2=0x1f800384`, `a3=0x00001000` | render-stage | CONFIRMED execution of the same trail-table helper path after moving and stopping. Not active movement/collision timing evidence. |
   | after movement / stopped | `0x80014360` | `fcn.80014360` | `a0=0x801642e4`, `a1=0x1f8003b4`, `a2=0x1f800384`, `a3=0x00001000` | render-stage | CONFIRMED execution of the pass-3 helper path; `a0 = G_PASS3_BASE_PTR = DATbase+0x3aec`. Not active movement/collision timing evidence. |
   | after movement / stopped | `0x800146e0` | `fcn.800146e0` | `a0=0x1f800394`, `a1=0x801fff30`, `a2=0xfffffe19`, `a3=0x80096fac`, `s2=0x801642e4` | render-stage | CONFIRMED execution of the later GTE helper with `s2 = G_PASS3_BASE_PTR`; exact table/field read remains UNKNOWN. Not active movement/collision timing evidence. |

5. Reading function(s): **UNKNOWN for the chosen field(s)**. Execute fallback confirms the known G4
   render-stage helpers run with parser-geometry table pointers, but it does **not** prove that
   output rec 261 (`0x801b3cb0`) or source scale0 (`0x8016560a`) is read.
6. Render / collision classification:
   - `0x800140a0`, `0x80014360`, `0x800146e0`: **render-stage** (matches G4 helper ranges).
   - No active movement/collision/pathing PC was observed reading a watched field: **G5 remains negative**.
   - The chosen field's runtime consumer is still **UNKNOWN** because the read watches had no hits.
7. Can G4 be upgraded from LIKELY render-stage to CONFIRMED per-frame render read? **PARTIAL only.**
   The fallback confirms per-frame execution of render-stage helper functions with parser geometry
   table pointers, but **does not confirm a per-frame read of a specific output-record field**.
8. Can G6 propose a minimal diagnostic edit now? **NO — G6 remains BLOCKED.**
9. Exact missing evidence: a PC/function that reads a specific candidate edit field, preferably
   `0x801b3cb0` (output rec 261 matrix[0]) or a retargeted active output record, and whether any
   non-render function reads that same field during movement/collision attempts.

### Part B conclusion

The fallback supports the existing G4 static path:

```
G_TRAIL_BLOCK_PTR / G_PASS3_BASE_PTR
  -> fcn.800224ec
  -> fcn.800140a0 / fcn.80014360 / fcn.800146e0
```

This is **CONFIRMED runtime execution of the render-stage helper path**, not a field-level read
watch. Since all read watches on the chosen record had no hits, the chosen `s0=0x4e00` / output
record 261 remains unsuitable for G6 unless a later test proves it is read or visibly active.
Recommended next G5.5 step: retarget to another active/on-camera pass-1 output record (for example
the previously noted `s0=0x7a18`, after verifying its pass-1 index and output address from the
current inventory) or trace/decompile `fcn.800140a0` enough to compute which table entries it reads.

---

## 7. Part C — `fcn.800140a0` first-loop read targets (analysis + read hit)

**Purpose.** Continue G5.5 without starting G6 by deriving concrete read-watch targets from the
observed fallback call:

```
PC=0x800140a0
a0=0x80161cfc  (= G_TRAIL_BLOCK_PTR = DATbase+0x1504)
a1=0x1f8003b4  (view matrix)
a2=0x1f800384  (view vector)
```

### Static first-loop read model (CONFIRMED from `SCUS_942.88` disasm)

`fcn.800140a0` does **not** initially dereference the pass-1 output record pointer at trail entry
`+0x10`. Its first loop reads the `0x14`-byte records embedded in the trail/pass-1 table itself.
This explains why watches on output rec 261 (`0x801b3cb0`/`0x801b3cc8`) did not fire.

VA-to-file note for this disasm: PS-X EXE file offset `0x48a0` maps to `0x800140a0`.

Key first-loop loads, with `entry = G_TRAIL_BLOCK_PTR + i*0x14`:

| PC | instruction | address read | meaning | confidence |
|----|-------------|--------------|---------|------------|
| `0x800140a4` | `lw t7, 0(a0)` | `G_TRAIL_BLOCK_PTR+0x00` | trail header / entry0 field0 overlap | CONFIRMED read / role UNKNOWN |
| `0x80014170` | `lh t3, 0x0e(a0)` | `entry+0x0e` | pass-1 entry flag / sentinel halfword | CONFIRMED read |
| `0x8001419c` | `lw s3, -0x14(a0)` | `entry+0x00` after delay-slot increment | first signed word used in GTE cull/range math | CONFIRMED read / role UNKNOWN |
| `0x800141a0` | `lw s5, -0x0c(a0)` | `entry+0x08` after delay-slot increment | third signed word used in GTE cull/range math | CONFIRMED read / role UNKNOWN |
| `0x800141a4` | `lh t4, -0x08(a0)` | `entry+0x0c` after delay-slot increment | signed halfword used as branch/range term | CONFIRMED read / role UNKNOWN |
| `0x800141b4` | `lw t1, -0x10(a0)` | `entry+0x04` if `entry+0x0c < 0` | second signed word, negative-`t4` path | CONFIRMED read / role UNKNOWN |
| `0x80014258` | `lw t1, -0x10(a0)` | `entry+0x04` if `entry+0x0c >= 0` | second signed word, nonnegative-`t4` path | CONFIRMED read / role UNKNOWN |

The loop tests `entry+0x0e` for `<0` as the sentinel. It increments `a0` by `0x14` in a branch delay
slot before loading the body fields, so body loads appear as negative offsets from the incremented
`a0`. These are still reads from the same `entry` row.

### Concrete LEVEL01 watch targets from `a0=0x80161cfc`

With DATbase CONFIRMED as `0x801607f8`, `G_TRAIL_BLOCK_PTR = 0x80161cfc = DATbase+0x1504`.
The first pass-1 trail records map directly to LEVEL01 DAT file offsets:

| entry | DAT file base | runtime base | output record for same pass-1 index | source record before parser | observed fields |
|------:|--------------:|-------------:|------------------------------------:|----------------------------:|----------------|
| 0 | `0x1504` | `0x80161cfc` | `0x801b1c10` | `0x4680` | `w0=-9578`, `w4=-3801`, `w8=-1379`, `h0c=6539`, `flags=0x0041` |
| 1 | `0x1518` | `0x80161d10` | `0x801b1c30` | `0x4698` | `w0=-9107`, `w4=-4104`, `w8=-5350`, `h0c=5536`, `flags=0x0041` |
| 2 | `0x152c` | `0x80161d24` | `0x801b1c50` | `0x46b0` | `w0=-8242`, `w4=-3240`, `w8=-8324`, `h0c=2326`, `flags=0x0041` |
| 3 | `0x1540` | `0x80161d38` | `0x801b1c70` | `0x4788` | `w0=-4500`, `w4=-4622`, `w8=-5742`, `h0c=5077`, `flags=0x0041` |

**Important distinction:** the parser's pass-1 relocation pointer lives at `entry+0x10`
(parser view: `[s3+2]`, file `0x1514 + i*0x14`) and is overwritten in RAM with the pass-1 output
record pointer. `fcn.800140a0`'s first loop above has not shown a read of `entry+0x10`; it reads
`entry+0x00/+0x04/+0x08/+0x0c/+0x0e`.

### DuckStation runbook — Part C read watches

Boot pristine LEVEL01, wait until Flik is controllable, and confirm:

```
mem32[0x80082498] = 0x801607f8
mem32[0x800824ac] = 0x80161cfc
```

Set READ watches in this order:

| priority | watch address | width | maps to DAT file | meaning | expected PC/function if hit |
|---------:|---------------|-------|------------------|---------|-----------------------------|
| 1 | `0x80161d0a` | halfword | `0x1512` | entry0 flag/sentinel (`0x0041`) | `0x80014170` / `fcn.800140a0` |
| 2 | `0x80161cfc` | word | `0x1504` | entry0 `w0`; also read once at function entry | `0x800140a4` and/or `0x8001419c` |
| 3 | `0x80161d08` | halfword | `0x1510` | entry0 `h0c` range term (`6539`) | `0x800141a4` |
| 4 | `0x80161d00` | word | `0x1508` | entry0 `w4` | `0x80014258` for this positive-`h0c` entry |
| 5 | `0x80161d04` | word | `0x150c` | entry0 `w8` | `0x800141a0` |
| 6 | `0x80161d1e` | halfword | `0x1526` | entry1 flag/sentinel (`0x0041`) | `0x80014170` |
| 7 | `0x80161d10` | word | `0x1518` | entry1 `w0` | `0x8001419c` if the bitmask processes entry1 |

If DuckStation only supports byte-granular watches, use the same start addresses and record the
reported access width/value. If the entry0 body fields do not hit because the bitmask skips entry0,
the flag watch (`0x80161d0a`) should still prove table scanning; then use entry1/entry2 body fields
or single-step from `0x80014170` until an entry is processed.

Record each hit:

| watch | PC | value | phase | notes |
|-------|----|-------|-------|-------|
| | | | standing still / after movement-stopped / active movement if tested | |

### What would unblock G6?

For G5.5, a hit on any of the concrete trail-entry field watches above at the expected `fcn.800140a0`
PCs would CONFIRM a specific LEVEL01 DAT-backed geometry field is read at runtime. If the only PCs
are inside `fcn.800140a0`/the G4 render-stage path, then G6 may proceed later only as a
**render-stage diagnostic edit** of a trail/pass-1 table field; collision impact remains **UNKNOWN**.

G6 must remain blocked if:
- only execute breakpoints hit and no data read watch hits;
- read hits occur only on generic globals/scratchpad, not DAT-backed trail/pass1 fields;
- the watched field cannot be mapped back to a specific DAT file offset.

### Part C result — trail/pass1 flag reads CONFIRMED (2026-06-14)

Operator result:

| watch | hit count | DuckStation PC | expected read site | registers | phase | classification |
|-------|----------:|----------------|--------------------|-----------|-------|----------------|
| `0x80161d0a` | 1 | `0x80014174` | `0x80014170` (`lh t3,0x0e(a0)`) | `a0=0x80161cfc`, `a1=0x1f8003b4`, `a2=0x1f800384`, `a3=0x80096ea8` | standing still / after resume | **render-stage DAT-backed field read** |
| `0x80161d1e` | 7 after repeated resume/F5 | `0x80014174` | `0x80014170` (`lh t3,0x0e(a0)`) | `a0=0x80161d10`, `a1=0x1f8003b4`, `a2=0x1f800384`, `a3=0x80096ea8` | standing still / after resume | **render-stage DAT-backed field read** |

Tested but not observed:

| watch | maps to DAT file | meaning | result |
|-------|------------------|---------|--------|
| `0x80161d08` | `0x1510` | entry0 `h0c` body/range halfword | no hit |
| `0x80161d00` | `0x1508` | entry0 `w4` body word | no hit |
| `0x80161d04` | `0x150c` | entry0 `w8` body word | no hit |

Interpretation:
- `0x80161d0a = DATbase + 0x1512`, which maps to LEVEL01 DAT file offset `0x1512`.
- File offset `0x1512` is pass-1 trail entry 0's flag/sentinel halfword (`0x0041`).
- `0x80161d1e = DATbase + 0x1526`, which maps to LEVEL01 DAT file offset `0x1526`.
- File offset `0x1526` is pass-1 trail entry 1's flag/sentinel halfword (`0x0041`).
- DuckStation stopped at `0x80014174`, consistent with a post-read stop after the instruction at
  `0x80014170`. For the entry1 hit, `a0=0x80161d10`, so `a0+0x0e = 0x80161d1e`. The entry1 hit
  count reached 7 because the operator resumed/F5 several times and repeatedly stopped at the same
  read site.
- The hit is inside `fcn.800140a0`, the G4 render-stage GTE helper path reached from
  `fcn.800224ec`.

Classification:
- **CONFIRMED:** concrete parser-geometry / trail-pass1 flag/sentinel fields are read at runtime.
- **CONFIRMED:** the reader is render-stage (`fcn.800140a0`).
- **UNKNOWN:** whether editing these flag/sentinel fields is visually useful or stable; they are
  control/cull fields, not coordinate-like body fields.
- **UNKNOWN:** body-field reads for the tested entry0 addresses; `0x80161d08`, `0x80161d00`, and
  `0x80161d04` had no hits in this test.
- **UNKNOWN:** collision impact. No movement/collision/pathing function read was observed.

G6 gate:
- This is enough to unblock G6 **only as a render-stage diagnostic edit** against the trail/pass1
  table, with collision impact explicitly **UNKNOWN**.
- It does **not** unblock a collision-aware diagnostic edit.
- The safest exact G6 field still needs care because the confirmed reads are flag/sentinel fields,
  not coordinate-like body fields; the recommended body-field watches remained zero-hit in this test.

## 8. G6 sentinel diagnostic build record (2026-06-14)

G6 was prepared only as a render-stage diagnostic edit; no broad geometry edit was attempted.

Patch:

| field | value |
|-------|-------|
| file | `LEVEL01/LEVEL.DAT` |
| DAT offset | `0x1526` |
| runtime address observed | `0x80161d1e` |
| confirmed reader | `fcn.800140a0` |
| read site | `0x80014170: lh t3,0x0e(a0)` |
| original bytes | `41 00` |
| patched bytes | `ff ff` |
| revert bytes | `41 00` |

Build artifacts:
- Patch script: `tools/patch_g6_render_sentinel_test.py`.
- Patched DAT: `DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST.DAT`, SHA256
  `149419dd724943dafa101b29e3a2bec179e188ebc0c93e8f42b1a095fea6c31a`.
- Test image: `ABL_G6_RENDER_SENTINEL_TEST.cue` / `ABL_G6_RENDER_SENTINEL_TEST.bin`.
- Rebuild report: `DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST_REBUILD.md`.

Build verification:
- Active rebuild DAT before patch: `REBUILD/files/LEVEL01/LEVEL.DAT`, size `332824`, SHA256
  `786b7a964129d4fee6a1983b356e172d406b17663d87b8befe645b92dbf08b53`, bytes at `0x1526` = `41 00`.
- Embedded test-image `LEVEL01/LEVEL.DAT` at LBA 2906 verified SHA1
  `717a0875f28fd8c93c6db9209c5e7981f3fcc97d`.
- Staged rebuild DAT restored after build.

Emulator result (2026-06-14):

| check | result |
|-------|--------|
| image | `ABL_G6_RENDER_SENTINEL_TEST.cue` |
| reaches title/menu | yes |
| enters LEVEL01 | yes |
| standing still render | terrain/ground mostly empty/missing; sky and some horizon/grass/backdrop visible |
| actors/objects | Flik, objects, enemy/props still load |
| crash/black screen | no |
| after movement | Flik can stand/move on invisible/missing terrain in tested area; objects still load |
| pristine comparison | major render-stage terrain disappearance/cutoff |

Classification:
- **CONFIRMED:** `DAT+0x1526` / pass-1 trail entry1 flag/sentinel is not merely read; changing it to
  `0xffff` produces a major render-stage terrain visibility/cutoff effect.
- **LIKELY:** the `0xffff` value makes `fcn.800140a0` treat entry1 as a negative sentinel and stop
  scanning after entry0.
- **UNKNOWN:** exact trail-field semantics and downstream GPU primitive path.
- **UNKNOWN:** full collision/pathing pipeline. The tested area still had usable ground collision
  while terrain rendering was mostly removed, which supports render/collision separation for this
  field but does not identify the collision data source.

## 9. G7 — render-body field identification runbook (2026-06-14)

**Purpose.** Find a DAT-backed pass-1 trail field that is read by `fcn.800140a0` only after the
per-entry body gate, so a later diagnostic can avoid another flag/sentinel control edit.

### Why entry0/entry1 body watches did not hit

`fcn.800140a0` has a scan stage and a process stage:

```
0x80014164  lb   s1,0(s0)          ; runtime bitmask byte, table starts at 0x800901c8
0x80014170  lh   t3,0x0e(a0)       ; always scans entry flag/sentinel
0x80014174  and  t9,s1,s4          ; current entry bit, s4 = 0x80 >> (entry & 7)
0x80014178  bltz t3,0x80014330     ; negative flag terminates the scan
0x80014194  beqz t9,0x80014170     ; bit clear -> skip body reads
0x8001419c  lw   s3,-0x14(a0)      ; entry+0x00, after a0 was advanced by 0x14
0x800141a0  lw   s5,-0x0c(a0)      ; entry+0x08
0x800141a4  lh   t4,-0x08(a0)      ; entry+0x0c
0x800141b4  lw   t1,-0x10(a0)      ; entry+0x04, negative h0c path
0x80014258  lw   t1,-0x10(a0)      ; entry+0x04, nonnegative h0c path
```

Entry0 and entry1 flag/sentinel watches hit because `entry+0x0e` is read before `t9` is tested.
Their body watches likely did not hit because their runtime bits were clear in the current camera
state, so the `beqz t9` branch skipped the body-field loads.

Runtime bit mapping:

```
mask_byte_addr = 0x800901c8 + (entry_index >> 3)
mask_bit       = 0x80 >> (entry_index & 7)
```

### Candidate body-field watches

Boot pristine LEVEL01, confirm `DATbase=0x801607f8` and `G_TRAIL_BLOCK_PTR=0x80161cfc`, then set
one READ watchpoint at a time.

| priority | entry | field | DAT offset | runtime address | original value / bytes | expected read PC | bit gate |
|---------:|------:|-------|------------|-----------------|------------------------|------------------|----------|
| 1 | 19 | `+0x00` word | `0x1680` | `0x80161e78` | `-8839` / `79 dd ff ff` | `0x8001419c` | `[0x800901ca] & 0x10` |
| 2 | 19 | `+0x0c` halfword | `0x168c` | `0x80161e84` | `195` / `c3 00` | `0x800141a4` | `[0x800901ca] & 0x10` |
| 3 | 24 | `+0x00` word | `0x16e4` | `0x80161edc` | `-10240` / `00 d8 ff ff` | `0x8001419c` | `[0x800901cb] & 0x80` |
| 4 | 31 | `+0x0c` halfword | `0x177c` | `0x80161f74` | `189` / `bd 00` | `0x800141a4` | `[0x800901cb] & 0x01` |
| 5 | 45 | `+0x00` word | `0x1888` | `0x80162080` | `-5661` / `e3 e9 ff ff` | `0x8001419c` | `[0x800901cd] & 0x04` |
| 6 | 132 | `+0x00` word | `0x1f54` | `0x8016274c` | `487` / `e7 01 00 00` | `0x8001419c` | `[0x800901d8] & 0x08` |

### G7 runtime results — body candidates (2026-06-14)

Testing was done on the pristine/working image, not the G6 sentinel image. Initial procedure for all
three watches: all other breakpoints/watchpoints disabled; one READ watch active at a time;
resumed/F5; stood still; walked; jumped; changed camera/view angles. Entry19 remained zero-hit.
Entry24 remained zero-hit through general movement/camera states away from the area, then hit once
when Flik/camera was near a specific edge-of-level area. Do not attribute the hit to F collection.

| watch | candidate | DAT offset | original bytes | expected read | gate | result | classification |
|-------|-----------|------------|----------------|---------------|------|--------|----------------|
| `0x80161e78` | pass-1 trail entry19 `+0x00` body word | `0x1680` | `79 dd ff ff` | `0x8001419c` / `fcn.800140a0` | `[0x800901ca] & 0x10` | no hit | **ZERO-HIT / NOT ELIGIBLE YET** |
| `0x80161e84` | pass-1 trail entry19 `+0x0c` body/range halfword | `0x168c` | `c3 00` | `0x800141a4` / `fcn.800140a0` | `[0x800901ca] & 0x10` | no hit | **ZERO-HIT / NOT ELIGIBLE YET** |
| `0x80161edc` | pass-1 trail entry24 `+0x00` body word | `0x16e4` | `00 d8 ff ff` | `0x8001419c` / `fcn.800140a0` | `[0x800901cb] & 0x80` | no hit during general standing/walking/jumping/camera movement away from the area; later hit once near a specific edge-of-level area | **CONFIRMED render-stage DAT-backed body-field read** |

Entry24 hit details:

| field | value |
|-------|-------|
| trigger context | Flik/camera near a specific edge-of-level area; not attributed to F collection |
| READ watch | `0x80161edc` |
| hit count | 1 |
| DuckStation PC shown | `0x800141a0` |
| actual read site | `0x8001419c: lw s3,-0x14(a0)` |
| `a0` at hit | `0x80161ef0` |
| read address | `a0 - 0x14 = 0x80161edc` |
| DAT offset | `0x16e4` |
| loaded value reported in `s3` | `0xfffd126d` |

Interpretation:
- **CONFIRMED:** `fcn.800140a0` scans pass-1 trail flags/sentinels broadly, from prior flag hits.
- **CONFIRMED:** entry24 `+0x00` is a DAT-backed pass-1 trail body field read by `fcn.800140a0`.
- **LIKELY:** entry24 is view/location/edge-of-level gated.
- **UNKNOWN:** whether entry19 is never used, scene/camera gated, distance gated, or active only in a
  different route/state.
- **TODO:** prepare a future render-body diagnostic proposal for entry24 `+0x00`; do not patch yet.

Record for each hit:

| watch | PC shown | expected read site | value | a0 | phase | hit count |
|-------|----------|--------------------|-------|----|-------|-----------|
| | | | | | standing / after movement-stopped | |

**Eligibility for later G7/G8 edit:** a body-field watch must hit at one of the body-read PCs
(`0x8001419c`, `0x800141a0`, `0x800141a4`, `0x800141b4`, `0x80014258`) inside `fcn.800140a0`.
Only then propose a same-size render-stage diagnostic edit. Collision/pathing impact remains
**UNKNOWN** unless the same field is also read by a non-render PC.

### Next runbook — active-entry discovery

Preferred approach:

1. Boot the pristine image into LEVEL01 and wait until Flik is controllable.
2. Verify bases:
   - `mem32[0x80082498] = 0x801607f8` (`DATbase`)
   - `mem32[0x800824ac] = 0x80161cfc` (`G_TRAIL_BLOCK_PTR`)
3. Inspect bitmask bytes beginning at `0x800901c8`. For each nonzero bit:
   - `entry = byte_index * 8 + bit_index`
   - `bit mask = 0x80 >> bit_index`
   - row base = `G_TRAIL_BLOCK_PTR + entry * 0x14`
   - DAT offset = `row base - DATbase`
4. Set one READ watch at a time on active row `+0x00`, `+0x04`, `+0x08`, or `+0x0c`.

Alternative approach:

1. Set execute breakpoints at the body-read PCs:
   `0x8001419c`, `0x800141a0`, `0x800141a4`, `0x800141b4`, `0x80014258`.
2. When one hits, record PC, `a0`, phase, and relevant registers.
3. Because `a0` was advanced in the delay slot, processed row base = `a0 - 0x14`.
4. Derive `entry_index = (row_base - G_TRAIL_BLOCK_PTR) / 0x14`, then map concrete body READ
   watch addresses from that active row.

Entry24 `+0x00` is now eligible for a future same-size render-body diagnostic proposal. Entry19
`+0x00` and entry19 `+0x0c` remain **ZERO-HIT / NOT ELIGIBLE YET**. Do not patch yet.
Collision/pathing impact remains **UNKNOWN**.

## 10. Path A — entry24 adjacent body-field coverage (runbook prepared 2026-06-14)

**Purpose.** Extend the CONFIRMED entry24 body read (`+0x00`) to the rest of the row body, by
watching the adjacent body fields `+0x08`, `+0x0c`, and `+0x04` while standing in the **same
edge-of-level area** that triggered `READ 0x80161edc`. No DAT/BIN/CUE patch; no build. One READ
watch at a time.

### Address derivation (CONFIRMED)

Entry24 row base = `G_TRAIL_BLOCK_PTR + 24*0x14 = 0x80161cfc + 0x1e0 = 0x80161edc`
(= `DATbase+0x16e4`, `DATbase=0x801607f8`). At the G7 hit `a0=0x80161ef0 = rowbase+0x14`
(delay-slot advanced), so body loads use negative offsets from `a0`. Field map and the
DuckStation "PC shown = read-site + 4" post-read-stop rule (CONFIRMED at `+0x00`):

| field | runtime addr | DAT off | pristine bytes | signed | width | read site (in `fcn.800140a0`) | PC shown in DuckStation | status |
|-------|--------------|--------:|----------------|-------:|-------|-------------------------------|-------------------------|--------|
| `+0x00` word | `0x80161edc` | `0x16e4` | `00 d8 ff ff` | `-10240` | 4 | `0x8001419c lw s3,-0x14(a0)` | `0x800141a0` | CONFIRMED (G7) — positive control |
| `+0x04` word | `0x80161ee0` | `0x16e8` | `b3 f5 ff ff` | `-2637` | 4 | `0x80014258 lw t1,-0x10(a0)` | `0x8001425c` | **CONFIRMED (Path A 2026-06-14)** |
| `+0x08` word | `0x80161ee4` | `0x16ec` | `9f fa ff ff` | `-1377` | 4 | `0x800141a0 lw s5,-0x0c(a0)` | `0x800141a4` | **CONFIRMED (Path A 2026-06-14)** |
| `+0x0c` half | `0x80161ee8` | `0x16f0` | `de 02` | `734` | 2 | `0x800141a4 lh t4,-0x08(a0)` | `0x800141a8` | **CONFIRMED (Path A 2026-06-14)** |

### Should `+0x04` be tested? YES — and its read site is now resolved

`+0x04` is read on exactly one of two mutually exclusive paths, selected by the sign of the
`+0x0c` halfword (`lh t4,-0x08(a0)` then a `bltz`-class branch):
`0x800141b4` on the **negative** `+0x0c` path, `0x80014258` on the **non-negative** path.
Pristine entry24 `+0x0c` (DAT `0x16f0`) = `0x02de` = **734 ≥ 0**, so the negative path
`0x800141b4` is dead for this row and `+0x04` is read at **`0x80014258`** (PC shown `0x8001425c`).
Because `+0x00`, `+0x08`, `+0x0c`, and `+0x04` are all read in the same straight-line body block
once the row's bitmask bit is set, `+0x04` should hit in the exact same edge-of-level state that
fired `+0x00`. Test it.

### Runbook (DuckStation)

1. Boot pristine `Disney-Pixar A Bug's Life (v1.0).cue` (no patched DAT). Play to LEVEL01 until
   Flik is controllable.
2. Confirm bases in the Memory view: `mem32[0x80082498] = 0x801607f8` (DATbase),
   `mem32[0x800824ac] = 0x80161cfc` (G_TRAIL_BLOCK_PTR). If DATbase differs, recompute every
   address as `DATbase + (DAT off)`; the DAT offsets above are fixed.
3. **Positive control first.** Add one READ watch on `0x80161edc` (`+0x00`). Walk/position
   Flik+camera back into the specific **edge-of-level area** that produced the G7 hit and confirm
   it breaks at PC shown `0x800141a0`. This re-establishes that the entry24 bitmask bit
   (`[0x800901cb] & 0x80`) is set in this state. Note the spot.
4. Remove the `+0x00` watch. Add a single READ watch on `0x80161ee4` (`+0x08`). Without leaving the
   spot, resume/F5. Expect a break at PC shown **`0x800141a4`** (read site `0x800141a0`).
   Record PC, accessed address, value, `a0`, phase, hit count.
5. Remove it. Add a single READ watch on `0x80161ee8` (`+0x0c`). Resume/F5 in the same spot.
   Expect PC shown **`0x800141a8`** (read site `0x800141a4`). Record as above.
6. Remove it. Add a single READ watch on `0x80161ee0` (`+0x04`). Resume/F5 in the same spot.
   Expect PC shown **`0x8001425c`** (read site `0x80014258`, the non-negative-`+0x0c` path).
   Record as above. (A hit at `0x800141b8`/site `0x800141b4` instead would contradict the
   pristine `+0x0c=734` value — flag it.)
7. If DuckStation only supports byte-granular watches, use the same start addresses and record the
   reported access width/value.

Record each hit:

| watch | field | PC shown | expected read site | value | a0 | phase | hit count |
|-------|-------|----------|--------------------|-------|----|-------|-----------|
| `0x80161ee4` | `+0x08` | `0x800141a4` | `0x800141a0` (matched) | — | `0x80161ef0` | edge-of-level area | ≥1 |
| `0x80161ee8` | `+0x0c` | `0x800141a8` | `0x800141a4` (matched) | — | `0x80161ef0` | edge-of-level area | ≥1 |
| `0x80161ee0` | `+0x04` | `0x8001425c` | `0x80014258` (matched) | — | `0x80161ef0` | edge-of-level area | ≥1 |

### Path A RESULTS — entry24 body row CONFIRMED (RUN 2026-06-14)

Tested on the pristine/working image (not the G6 sentinel image), in the same edge-of-level /
view-location gated area that previously fired entry24 `+0x00`. Not F-collection gated. The `+0x00`
positive control re-fired (**hit count 2**, PC shown `0x800141a0`, read site `0x8001419c`,
`a0=0x80161ef0`), confirming the entry24 bitmask bit (`[0x800901cb] & 0x80`) was set in this state.
All three adjacent body fields then hit at exactly the predicted PCs with `a0=0x80161ef0`:

| watch | field | DAT off | PC shown | actual read site | a0 | result |
|-------|-------|--------:|----------|------------------|----|--------|
| `0x80161edc` | `+0x00` word | `0x16e4` | `0x800141a0` | `0x8001419c lw s3,-0x14(a0)` | `0x80161ef0` | **CONFIRMED** (control, hit count 2) |
| `0x80161ee4` | `+0x08` word | `0x16ec` | `0x800141a4` | `0x800141a0 lw s5,-0x0c(a0)` | `0x80161ef0` | **CONFIRMED** |
| `0x80161ee8` | `+0x0c` half | `0x16f0` | `0x800141a8` | `0x800141a4 lh t4,-0x08(a0)` | `0x80161ef0` | **CONFIRMED** |
| `0x80161ee0` | `+0x04` word | `0x16e8` | `0x8001425c` | `0x80014258 lw t1,-0x10(a0)` | `0x80161ef0` | **CONFIRMED** |

**Path A is complete.** The full pass-1 trail **entry24 body row** is CONFIRMED read by
`fcn.800140a0` at runtime:

```
+0x00  DAT+0x16e4  word  read @ 0x8001419c
+0x04  DAT+0x16e8  word  read @ 0x80014258 (non-negative-+0x0c path; CONFIRMS +0x0c>=0 deduction)
+0x08  DAT+0x16ec  word  read @ 0x800141a0
+0x0c  DAT+0x16f0  half  read @ 0x800141a4
```

The `+0x04` hit at `0x80014258` (not `0x800141b4`) confirms the earlier static deduction that
entry24's `+0x0c` halfword (`734 >= 0`) selects the non-negative branch.

Classification:
- **CONFIRMED:** entry24 is a **non-sentinel DAT-backed render body row** read by the render-stage
  helper `fcn.800140a0`. This is distinct from the G6 flag/sentinel field (`entry+0x0e`).
- **LIKELY:** entry24 is location/view (edge-of-level) gated by its runtime bitmask bit.
- **UNKNOWN:** the exact semantics of each body field (coordinate / range / vector component), the
  downstream GPU primitive stage, and the exact visual effect of editing any field.
- **UNKNOWN/collision:** no non-render PC was observed reading this row; collision/pathing impact
  remains UNKNOWN.
- Entry24 body fields are now eligible for a **cautious** future render-body diagnostic proposal
  (see §11). Do not patch yet.

**Static-vs-runtime value note (flagged for §11).** At the `+0x00` hit, DuckStation reported
`s3 = 0xfffd126d`, whereas the static DAT word at `0x16e4` is `0xffffd800` (`-10240`). These differ.
It is **UNKNOWN** whether (a) the body words are rewritten in-place at runtime (e.g. the helper
stores transformed values back into the row), (b) the field is post-load adjusted, or (c) the
reported register is a snapshot artifact. This is a real risk for any static DAT edit of this row and
gates the G8 proposal below.

### Interpretation of results

- **HIT at the expected PC inside `fcn.800140a0`:** CONFIRMS that adjacent field is a DAT-backed
  render-stage body field read on the same path as `+0x00`, completing entry24 body coverage
  (`+0x00/+0x04/+0x08/+0x0c`). The field becomes eligible for a future same-size render-body
  diagnostic proposal. Collision/pathing impact remains **UNKNOWN** unless a non-render PC also
  reads it.
- **NO-HIT while the `+0x00` positive control (step 3) still fires in the same spot:** unexpected,
  since the disasm reads all four fields in one straight-line block once the bit is set. Most
  likely the watch address/width was off, or the body-gate bit toggled between resumes — re-run
  step 3 as a control before concluding. A genuine, repeatable no-hit with `+0x00` confirmed in the
  same frame would mean the static body-block model needs revisiting; record it verbatim.
- **`+0x00` control itself does not re-fire:** the edge-of-level position/camera was not reproduced
  (bitmask bit clear). Reposition until `+0x00` breaks before testing the adjacent fields; do not
  attribute the gate to F collection.

Do not patch yet. This runbook only widens read coverage of entry24's body.

## 11. G8 — render-body diagnostic PROPOSAL (entry24 body field) — NOT YET PATCHED

**Status:** PROPOSAL ONLY (2026-06-14). No DAT/BIN/CUE patch, no build, no commit of binary
artifacts. This section selects conservative candidate edits and a verification gate; it does not
authorize a patch.

**Why entry24 is the target.** Path A (§10) CONFIRMED the whole entry24 body row
(`+0x00/+0x04/+0x08/+0x0c`) is read at runtime by `fcn.800140a0` at deterministic PCs. Unlike the G6
edit, these are **non-sentinel body fields**, so a small numeric perturbation probes render geometry
rather than toggling a scan terminator.

### Blocking verification gate (do this BEFORE any patch)

The `+0x00` static word (`0xffffd800`) differs from the runtime-read value (`0xfffd126d`) at the hit.
Until that is explained, a static DAT edit may not survive to the read site. **Gate:** with a READ
or memory watch in the edge-of-level area, read the live word at the chosen field's runtime address
and compare to the static DAT bytes:

- If live == static at the read instant → the field is static-DAT-backed at the read; proceed.
- If live != static → the row is runtime-rewritten; a static edit is **not** a valid diagnostic for
  that field. Do **not** patch; re-scope to a field that reads its static value, or treat the
  rewrite itself as the finding.

Prefer a field whose live value matches its static DAT bytes. **Avoid `+0x00` as the edit target**
because its observed runtime value already contradicts the static word.

### Candidate edits (same-size, reversible)

All candidates are **LIKELY render-body/range/vector fields**; the **exact visual effect is UNKNOWN**.
No shape/position semantics are claimed. Prefer Candidate A; escalate to B only if A shows nothing.

| id | field | DAT off | runtime addr | orig bytes (value) | candidate new bytes (value) | perturbation | revert bytes |
|----|-------|--------:|--------------|--------------------|-----------------------------|--------------|--------------|
| A (recommended) | entry24 `+0x08` word | `0x16ec` | `0x80161ee4` | `9f fa ff ff` (`-1377`) | `9f fb ff ff` (`-1121`) | `+256`, single byte `fa→fb` | `9f fa ff ff` |
| B (escalation) | entry24 `+0x08` word | `0x16ec` | `0x80161ee4` | `9f fa ff ff` (`-1377`) | `61 05 00 00` (`+1377`) | sign-flip (same magnitude) | `9f fa ff ff` |
| C (alternative field) | entry24 `+0x04` word | `0x16e8` | `0x80161ee0` | `b3 f5 ff ff` (`-2637`) | `b3 f9 ff ff` (`-1613`) | `+1024`, single byte `f5→f9` | `b3 f5 ff ff` |

**Why `+0x08` first (Candidate A/B).** It is read at a single deterministic site (`0x800141a0`,
no branch dependency), it is the smallest-magnitude body word (so a fixed delta is proportionally
larger and more likely observable while staying numeric), and it is neither the `+0x0c` branch/sign
term nor the `+0x0e` flag/sentinel (the G6 destructive field). Candidate A is a minimal `+256`
nudge; Candidate B is a fully-reversible sign-flip kept for the case where A is imperceptible.

**Explicitly NOT proposed:**
- `+0x0c` halfword — it feeds the `bltz` branch selecting the `+0x04` read path; editing it changes
  control flow (sentinel-like), not a clean body perturbation.
- `+0x0e` flag/sentinel — already exercised destructively in G6; out of scope here.

### Expected render-stage effect

**UNKNOWN exact visual effect.** If `+0x08` is a coordinate/vector component fed to the GTE
MVMVA/SQR transform, a small change LIKELY shifts/rescales whatever element entry24 contributes in
that edge-of-level view; it may also be imperceptible if the field is a coarse range/cull term.
Possible outcomes to record without prejudging: no visible change; a small local geometry
shift/distortion near the edge-of-level area; or a local visibility change. A full-screen terrain
loss like G6 is **not** expected from a small numeric body edit and would itself be a finding.

### Explicit uncertainty

- Field semantics (coordinate vs range vs vector component): **UNKNOWN**.
- Whether the static edit survives to the read site: **UNKNOWN** until the verification gate passes
  (see the `+0x00` static-vs-runtime discrepancy).
- Whether the effect is observable at all with a small perturbation: **UNKNOWN**.
- Collision/pathing impact: **UNKNOWN** — do not infer it from a render-stage read.

### Operator test instructions (when/if a build is later authorized)

1. **Do not patch yet.** This is a proposal. A build requires explicit instruction.
2. Run the §11 verification gate first: confirm the live word at `0x80161ee4` equals `9f fa ff ff`
   at the read instant in the edge-of-level area. Abort if it differs.
3. If authorized: apply Candidate A (`DAT+0x16ec: 9f fa ff ff → 9f fb ff ff`) to a **copy** of the
   pristine DAT; rebuild a test image with the existing rebuild tool; never commit DAT/BIN/CUE.
4. Boot the test image, reach LEVEL01, and revisit the same edge-of-level area. Compare against
   pristine: record any geometry shift/distortion/visibility change near that area, or "no visible
   change". This historical escalation path is now superseded by the completed A/A2/C results in
   §12-15; do not use it as the current next-step recommendation.
5. Keep one optional READ watch on `0x80161ee4` to confirm the edited value is the one read.
6. Revert: restore `DAT+0x16ec` to `9f fa ff ff`. Collision/pathing claims remain out of scope.

### G8 live-value verification runbook (BLOCKING GATE — run before any patch)

Status: **PREP ONLY. Candidate A is NOT executed. No DAT/BIN/CUE image generated.** This gate must
pass before the patch-prep output may be used for a build.

1. Boot the **pristine** image (`Disney-Pixar A Bug's Life (v1.0).cue`, no patched DAT). Play to
   LEVEL01 until Flik is controllable.
2. Confirm bases: `mem32[0x80082498]=0x801607f8` (DATbase), `mem32[0x800824ac]=0x80161cfc`
   (G_TRAIL_BLOCK_PTR). If DATbase differs, recompute `0x80161ee4 = DATbase + 0x16ec`.
3. Reproduce the edge-of-level entry24 state (the same view-location area that fired the Path A
   reads; not F-collection gated). Use a READ watch on `0x80161edc` (`+0x00`) as a positive control
   if needed to confirm the entry24 bitmask bit is set.
4. Set a single **READ watch on `0x80161ee4`** (entry24 `+0x08`). Resume/F5 in that state.
5. Confirm the break is at **PC shown `0x800141a4`** (read site `0x800141a0: lw s5,-0x0c(a0)`),
   `a0=0x80161ef0`.
6. Record `a0`, the live loaded value / register state (`s5`), the live memory word at `0x80161ee4`,
   and the hit count.
7. **Decision:**
   - Live word **==** static `0xfffffa9f` (bytes `9f fa ff ff`) at the read instant → field is
     static-DAT-backed at the read; Candidate A is a valid diagnostic target. A build may then be
     proposed (still requires explicit authorization).
   - Live word **!=** static → the row is **runtime-rewritten**. **Do not patch.** Document the
     observed live value and propose tracing the writer (search for stores to `entry+0x08` /
     `0x80161ee4`, e.g. a `sw`-side of `fcn.800140a0` or an earlier transform that writes the row).
     Re-scope to a field whose live value matches its static bytes.

### G8 patch-prep infrastructure (PREP ONLY — script created, NOT run on game data)

A gated patch-prep script is staged: **`tools/patch_g8_entry24_plus08_test.py`**. It:

- takes `input_dat` and `output_dat` (distinct paths), never mutates the input in place;
- verifies input size `0x51418` and that bytes at `0x16ec` equal `9f fa ff ff`, refusing otherwise;
- writes only `0x16ec..0x16ef` → `9f fb ff ff` to the output;
- prints original/patched SHA256, the changed offset, and revert bytes `9f fa ff ff`;
- prints a BLOCKING-GATE warning that live-value verification (above) must pass before the patched
  DAT is used for any build.

The script's behavior was independently re-verified during the build below (refuses wrong original
bytes; mutates only the `0x16ec` word; pristine input untouched). Collision/pathing impact remains
**UNKNOWN**.

## 12. G8 — live-value gate PASSED + Candidate A build (EXECUTED 2026-06-14)

**Status:** live-value gate **PASSED**; patched DAT and test image **built**. No emulator visual test
run yet. **No DAT/BIN/CUE/RAM/save-state artifact is committed** (all are gitignored, as with G6/G7).

### Live-value verification gate — PASSED

Tested on the pristine/working image. Positive control reproduced, then Candidate A's field gate:

| step | watch | field | PC shown | read site | a0 | observed | result |
|------|-------|-------|----------|-----------|----|----------|--------|
| control | `0x80161edc` | entry24 `+0x00` | `0x800141a0` | `0x8001419c` | `0x80161ef0` | entry24 state active | reproduced |
| gate | `0x80161ee4` | entry24 `+0x08` (`DAT+0x16ec`) | `0x800141a4` | `0x800141a0: lw s5,-0x0c(a0)` | `0x80161ef0` | debugger banner `addr=0x80161ee4 [0xfffffa9f]` | **live == static** |

Conclusion: the live word at `0x80161ee4` reads `0xfffffa9f`, which equals the static DAT value
(`0xfffffa9f`, bytes `9f fa ff ff` at `DAT+0x16ec`). The row is **static-DAT-backed at the read
instant** for `+0x08`. **G8 live-value gate PASSED** → Candidate A is a valid diagnostic target.
(The earlier `+0x00` static-vs-runtime mismatch does **not** apply to `+0x08`; this is exactly why
the gate was required and why `+0x00` was avoided as the edit target.)

### Candidate A patch + build record

| item | value |
|------|-------|
| field | pass-1 trail entry24 `+0x08` (`DAT+0x16ec`, runtime `0x80161ee4`) |
| original bytes / value | `9f fa ff ff` / `0xfffffa9f` / `-1377` |
| patched bytes / value | `9f fb ff ff` / `0xfffffb9f` / `-1121` (delta `+256`) |
| revert bytes | `9f fa ff ff` |
| changed file offset | only `0x16ed` differs (the `0x16ec` word region; high 3 bytes already equal) |

Patch command:

```
python3 tools/patch_g8_entry24_plus08_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_TEST.DAT
```

Patched DAT (gitignored artifact, not committed):

| item | value |
|------|-------|
| path | `DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_TEST.DAT` |
| size | `332824` (`0x51418`) |
| SHA256 before (pristine) | `786b7a964129d4fee6a1983b356e172d406b17663d87b8befe645b92dbf08b53` |
| SHA256 after (patched) | `bdc21f3546f9795d9a91871833e47158838f6ea6cce8ddcd00e5b6c286e24e49` |
| SHA1 (patched) | `67dbb8322741fc3863aa5e9c81aa463c3505da2d` |

Script re-verification during this run:
- refuses wrong original bytes (re-running on the already-patched file exits non-zero, no output);
- pristine input `DAT/LEVEL01_LEVEL.DAT` unchanged (sha1 `b376cb50…`, bytes `9f fa ff ff` at `0x16ec`);
- only the `0x16ec` word changed (byte diff at `0x16ed`).

Rebuild command:

```
python3 tools/rebuild_with_patched_dat.py \
  --patched-dat DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_TEST.DAT \
  --target files/LEVEL01/LEVEL.DAT \
  --expected-sha1 67dbb8322741fc3863aa5e9c81aa463c3505da2d \
  --out-bin ABL_G8_ENTRY24_PLUS08_TEST.bin \
  --out-cue ABL_G8_ENTRY24_PLUS08_TEST.cue \
  --report DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_TEST_REBUILD.md \
  --write
```

Build result (gitignored artifacts):
- Output image: `ABL_G8_ENTRY24_PLUS08_TEST.bin` (`738285744` bytes) / `ABL_G8_ENTRY24_PLUS08_TEST.cue`.
- Embedded `LEVEL01/LEVEL.DAT` at LBA `2906` verified SHA1 `67dbb8322741fc3863aa5e9c81aa463c3505da2d`
  (== patched DAT). Independent check: embedded DAT byte at file `0x16ec` reads `9f fb ff ff`
  (pristine image reads `9f fa ff ff` at the same spot).
- Staged workspace `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine (sha1 `b376cb50…`).
- Report: `DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_TEST_REBUILD.md` (gitignored).

### Operator visual test instructions (pristine vs G8 image)

1. Boot `ABL_G8_ENTRY24_PLUS08_TEST.cue`.
2. Enter LEVEL01.
3. Move to the same edge-of-level / view-location area where the entry24 reads triggered.
4. Compare against the pristine image at the same spot/camera.
5. Look for any of: localized terrain shift/deformation; clipping/range change; missing or altered
   visual geometry; **no visible change**; or crash/black screen. Record exactly what is seen.
6. Do **not** infer collision/pathing from this; that requires a separate collision-specific test.

Optional runtime confirmation that the edited value is the one read:
- In the G8 image, set `READ 0x80161ee4`, reproduce the edge-of-level entry24 state.
- Expected PC shown `0x800141a4`; confirm the value read is now `0xfffffb9f` (was `0xfffffa9f`).

### Interpretation guardrails (pre-result)

- entry24 `+0x08` is a **LIKELY render-body/range/vector field**; the **exact visual effect is
  UNKNOWN** until the emulator test is run.
- A small `+256` perturbation may be imperceptible; "no visible change" is a valid, recordable result.
- Collision/pathing impact remains **UNKNOWN** and must not be inferred from a render-stage read/edit.

### Candidate A emulator result (2026-06-14) — EXECUTED / VALID BUILD / NO OBVIOUS VISUAL CHANGE

Operator tested `ABL_G8_ENTRY24_PLUS08_TEST.cue` (patch `DAT+0x16ec: 9f fa ff ff → 9f fb ff ff`,
`-1377 → -1121`, `+256`):

| check | result |
|-------|--------|
| image boots | yes |
| LEVEL01 loads | yes |
| crash / black screen | no |
| terrain shift/deformation in the edge-of-level entry24 area | none obvious |
| clipping / range change | none obvious |
| missing / altered visual geometry | none obvious |
| pristine vs G8 screenshots | effectively the same by eye |

**Classification: EXECUTED / VALID BUILD / NO OBVIOUS VISUAL CHANGE — not a failure.** The small
`+256` same-field perturbation did not produce an obvious visible change in the tested view. entry24
`+0x08` **may still be** render-body/range/vector data; this delta was **likely too small, visually
masked, or not directly positional**. Field semantics remain **UNKNOWN**. Collision/pathing remains
**UNKNOWN**.

**Optional CPU confirmation — CONFIRMED data read in G8 image (redone correctly 2026-06-14).** The
earlier note (screenshot apparently watching PC `0x800141a4` instead of data `0x80161ee4`) is
**SUPERSEDED**. The READ data watch was re-run correctly in `ABL_G8_ENTRY24_PLUS08_TEST.cue`:

| field | value |
|-------|-------|
| watch | READ `0x80161ee4` (entry24 `+0x08`, `DAT+0x16ec`) |
| observed PC shown | `0x800141a4` (matched expected) |
| actual read site | `0x800141a0` |
| `a0` | `0x80161ef0` |
| hit count | 1 |
| status | **CONFIRMED** the patched field is reached/read by `fcn.800140a0` in the G8 image |

Nuance: the screenshot confirms the correct data READ watch fired at the expected PC, but it does
**not** clearly show the raw register `s5 = 0xfffffb9f`. Proof that the image actually contains the
patched bytes is the **embedded DAT verification** (`DAT+0x16ec` = `9f fb ff ff` at LBA 2906). Do
**not** overstate this as direct register proof of the patched word unless `s5` is separately
captured. Net status: **CONFIRMED data read in G8 image; raw patched register value not separately
captured.**

### Historical G8 escalation plan — SUPERSEDED by A2/C results

Options considered:

| id | change | bytes | value | delta | nature |
|----|--------|-------|-------|-------|--------|
| confirm | re-run runtime check correctly | — | — | — | READ `0x80161ee4`, zero-risk, no build |
| A2 | `+0x08` larger same-field nudge | `9f fe ff ff` | `-353` | `+1024` (4× A) | single byte `fa→fe`, still negative, reversible |
| B | `+0x08` sign-flip | `61 05 00 00` | `+1377` | sign-flip | 3 bytes change, more destructive |
| C | switch to `+0x04` (`DAT+0x16e8`) | `b3 f9 ff ff` | `-1613` | `+1024` | confirmed-read field, different semantics |

**Historical recommendation:** A2 (larger same-field perturbation at `DAT+0x16ec`), gated on first
completing the correct READ `0x80161ee4` runtime confirmation (no build required). This is now
superseded by the completed A2 and C results below.

Rationale (conservative controlled escalation):
- Stay on the **same CONFIRMED-read field** (`+0x08`) and only increase magnitude, so any new visible
  effect is attributable to that one field. This isolates "is `+0x08` visually influential at all?"
  before switching fields (C) or doing a destructive sign-flip (B).
- A2 (`-353`, `+1024`, 4× the A delta) is still a single-byte, negative-valued, fully reversible
  change — a controlled step up, not a sentinel-style or sign-flipping edit.
- The runtime confirmation is a free prerequisite: it proves the build's edited word is actually the
  one read at `0x80161ee4`, closing the current TODO before spending another build on a larger delta.
- Defer B (sign-flip) and C (different field) until A2 also shows no visible change; only then is a
  larger blast radius or a field switch justified.

A2 uses the sibling gated script `tools/patch_g8_entry24_plus08_a2_test.py` (same guards as the A
script; pristine-only original-bytes check). Collision/pathing impact remains **UNKNOWN**.

## 13. G8 — Candidate A2 build and result (EXECUTED 2026-06-14)

Stronger same-field escalation of Candidate A. Live-value gate already PASSED for `+0x08` (§12);
A2 stays on the same CONFIRMED-read field, same sign, same 4-byte size, single changed byte.

| item | value |
|------|-------|
| field | pass-1 trail entry24 `+0x08` (`DAT+0x16ec`, runtime `0x80161ee4`) |
| pristine bytes / value | `9f fa ff ff` / `0xfffffa9f` / `-1377` |
| A2 patched bytes / value | `9f fe ff ff` / `0xfffffe9f` / `-353` (delta `+1024` from pristine) |
| revert bytes | `9f fa ff ff` |
| changed file offset | only `0x16ed` differs (the `0x16ec` word region) |

Patch command:

```
python3 tools/patch_g8_entry24_plus08_a2_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_A2_TEST.DAT
```

Patched DAT (gitignored artifact, not committed):

| item | value |
|------|-------|
| path | `DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_A2_TEST.DAT` |
| size | `332824` (`0x51418`) |
| SHA256 before (pristine) | `786b7a964129d4fee6a1983b356e172d406b17663d87b8befe645b92dbf08b53` |
| SHA256 after (patched) | `0c2be4fbc9bdd7ae70699c3f5728c5e52511789f5ae6962f83a001fac4b957d5` |
| SHA1 (patched) | `8714b578f2b35aefe9f4f7fa066e0879f87d71fa` |

Script re-verification during this run: refuses wrong original bytes (re-run on the patched file exits
non-zero, no output); pristine input untouched (sha1 `b376cb50…`, `9f fa ff ff` at `0x16ec`); only the
`0x16ec` word changed (byte diff at `0x16ed`).

Rebuild command:

```
python3 tools/rebuild_with_patched_dat.py \
  --patched-dat DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_A2_TEST.DAT \
  --target files/LEVEL01/LEVEL.DAT \
  --expected-sha1 8714b578f2b35aefe9f4f7fa066e0879f87d71fa \
  --out-bin ABL_G8_ENTRY24_PLUS08_A2_TEST.bin \
  --out-cue ABL_G8_ENTRY24_PLUS08_A2_TEST.cue \
  --report DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_A2_TEST_REBUILD.md \
  --write
```

Build result (gitignored artifacts):
- Output image: `ABL_G8_ENTRY24_PLUS08_A2_TEST.bin` (`738285744` bytes) / `ABL_G8_ENTRY24_PLUS08_A2_TEST.cue`.
- Embedded `LEVEL01/LEVEL.DAT` at LBA `2906` verified SHA1 `8714b578f2b35aefe9f4f7fa066e0879f87d71fa`
  (== patched DAT). Independent check: embedded DAT byte at file `0x16ec` reads `9f fe ff ff`.
- Staged workspace `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine (sha1 `b376cb50…`).
- Report: `DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS08_A2_TEST_REBUILD.md` (gitignored).

### Operator visual test steps (A2)

1. Boot `ABL_G8_ENTRY24_PLUS08_A2_TEST.cue`.
2. Enter LEVEL01.
3. Move to the same edge-of-level / view-location area where the entry24 reads trigger.
4. Compare against the **pristine** image (and the Candidate A image, if useful).
5. Look for any of: localized terrain shift/deformation; clipping/range change; missing or altered
   visual geometry; **no visible change**; or crash/black screen. Record exactly what is seen.
6. Do **not** infer collision/pathing from this test.

Optional CPU confirmation:
- Set `READ 0x80161ee4`, reproduce the edge-of-level entry24 state.
- Expected PC shown `0x800141a4`; embedded/read target value `0xfffffe9f`. (As with A, the data-watch
  hit confirms the field is read; embedded DAT verification is the proof of patched bytes.)

### Candidate A2 emulator result (2026-06-14) — EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE

Tested `ABL_G8_ENTRY24_PLUS08_A2_TEST.cue` (`DAT+0x16ec: 9f fa ff ff → 9f fe ff ff`, `-1377 → -353`,
`+1024`). Three screenshots + one save state captured.

| check | result |
|-------|--------|
| image boots / LEVEL01 loads | yes |
| crash / black screen | no |
| terrain shift/deformation in the edge-of-level entry24 area | none obvious |
| clipping / range change | none obvious |
| missing / altered terrain | none obvious |
| collision/pathing | not tested — **UNKNOWN** |

**CPU data-read CONFIRMED (screenshot 1).** READ watch `0x80161ee4` hit (Breakpoints panel:
`0x80161EE4 / Read / Hit Count 1`); PC shown `0x800141a4` (the post-read instruction, `lh t4,-0x8(a0)`),
read site `0x800141a0`, `a0=0x80161ef0`. The on-PC banner shows the *next* read
(`addr=0x80161ee8[0x02de]`, i.e. `+0x0c`), and the post-read register `s5` does not cleanly show the
`+0x08` value (MIPS load-delay / read-after timing), so neither the banner nor `s5` is used as the raw
`+0x08` value — consistent with the documented nuance.

**Memory-byte proof CONFIRMED (screenshot 3).** The CPU memory/data view at `0x80161ee4` shows the
word **`FFFFFE9F`** (= bytes `9f fe ff ff`), matching the A2 patch. Cross-check of the same entry24 row
in RAM: `0x80161edc=FFFFD800` (`+0x00`), `0x80161ee0=FFFFF5B3` (`+0x04`, static `-2637`),
`0x80161ee4=FFFFFE9F` (`+0x08`, **A2 patched** `-353`), word @`0x80161ee8=401902DE` (`+0x0c=0x02de`,
`+0x0e=0x4019`). So **live RAM matches the A2 embedded DAT patch** — this is stronger than A, whose
patched bytes were proven only by embedded-DAT verification. (Side note: here `+0x00` read as
`0xffffd800` = static, whereas the earlier G7 `+0x00` capture was `0xfffd126d`; so `+0x00` is
state/time-variable while `+0x04`/`+0x08` matched static in this state — mechanism **UNKNOWN**,
corroborates the earlier `+0x00` caution.)

**In-game view (screenshot 2).** The edge-of-level entry24 area (tree root/log, grass stalks, dirt)
appears effectively unchanged vs pristine by eye. This is the reproduction/comparison location for
future tests.

**Save state captured (not committed).** A DuckStation save state
(`SCUS-94288_1.sav`) plus a RAM dump (`pause_at_80161EE4.ram`) were captured near/at the A2 entry24
trigger location to preserve the hard-to-reproduce edge-of-level/view-location state for future
Candidate B / `+0x04` comparisons. **Do not commit** save-state/RAM artifacts.

**Classification: EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE.**
Candidate A2 raised the same entry24 `+0x08` field by `+1024` from pristine while preserving sign and
field size; the A2 image boots, the target data-read path is reached, the patched value is confirmed
present in RAM, and no obvious visual difference is seen in the tested view. This suggests `+0x08` may
be too subtle, masked, not directly positional, or not visually decisive in the tested location. It
does **not** disprove render-body relevance. Field semantics and collision/pathing impact remain
**UNKNOWN**.

### Historical next experiment — Candidate C (`+0x04`), SUPERSEDED by §14 result

Recommend **Candidate C: a controlled same-size perturbation of entry24 `+0x04` (`DAT+0x16e8`)**, not
the destructive sign-flip B. Both `+0x08` edits (A `+256`, A2 `+1024`) were CPU-read-confirmed and
RAM-confirmed yet visually imperceptible, so move to a different CONFIRMED-read body field before
escalating destructively on `+0x08`.

| id | field | DAT off | pristine bytes/value | candidate new bytes/value | delta | nature |
|----|-------|--------:|----------------------|---------------------------|-------|--------|
| C | entry24 `+0x04` word | `0x16e8` | `b3 f5 ff ff` / `-2637` | `b3 f9 ff ff` / `-1613` | `+1024` | single byte `f5→f9`, same sign/size, reversible |

Rationale: `+0x04` is read at `0x80014258` (the non-negative-`+0x0c` branch, CONFIRMED in Path A), so a
data watch on `0x80161ee0` can confirm it the same way. Keep the same conservative `+1024` step and
the same edge-of-level repro (reuse the saved state). Defer Candidate B sign-flip (`+0x08 → 61 05 00
00`) until `+0x04` is also shown imperceptible; only then is a destructive proof of `+0x08` influence
justified. Do **not** patch/build yet. Collision/pathing impact remains **UNKNOWN**.

## 14. G8 — Candidate C build and result (EXECUTED 2026-06-14)

Switch from `+0x08` (A/A2, both visually imperceptible) to a different CONFIRMED-read body field,
entry24 `+0x04`. Same-size, single-byte, still-negative, reversible perturbation. No live-value gate
was re-run for `+0x04` specifically; the §12 gate PASSED for `+0x08`, and the A2 RAM cross-check
(§13) independently showed `0x80161ee0 = FFFFF5B3` (`+0x04`, static `-2637`) in the entry24 state, so
`+0x04` read its static bytes in that capture. The operator should still confirm via the optional CPU
read below before treating any visual result as decisive.

| item | value |
|------|-------|
| field | pass-1 trail entry24 `+0x04` (`DAT+0x16e8`, runtime `0x80161ee0`) |
| read site | `0x80014258 lw t1,-0x10(a0)` (non-negative-`+0x0c` branch; `+0x0c = 0x02de = 734 >= 0`) |
| pristine bytes / value | `b3 f5 ff ff` / `0xfffff5b3` / `-2637` |
| C patched bytes / value | `b3 f9 ff ff` / `0xfffff9b3` / `-1613` (delta `+1024` from pristine) |
| revert bytes | `b3 f5 ff ff` |
| changed file offset | only `0x16e9` differs (the `0x16e8` word region) |

Patch command:

```
python3 tools/patch_g8_entry24_plus04_c_test.py DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS04_C_TEST.DAT
```

Patched DAT (gitignored artifact, not committed):

| item | value |
|------|-------|
| path | `DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS04_C_TEST.DAT` |
| size | `332824` (`0x51418`) |
| SHA256 before (pristine) | `786b7a964129d4fee6a1983b356e172d406b17663d87b8befe645b92dbf08b53` |
| SHA256 after (patched) | `66d949ad39f608874864c848850a06aad610ee15d3561cd6d892f4885c31ce32` |
| SHA1 (patched) | `9461ef48f9578ae4bbb068522923b8b03aa9205d` |

Script behavior (this run): refuses same input/output path; verifies size `0x51418`; refuses unless
bytes at `0x16e8` are pristine `b3 f5 ff ff`; writes only `0x16e8..0x16eb` → `b3 f9 ff ff`; prints
SHA256 before/after, changed offset, old/new/revert bytes; never mutates the input. Pristine input
untouched (sha1 `b376cb50…`, `b3 f5 ff ff` at `0x16e8`).

Rebuild command:

```
python3 tools/rebuild_with_patched_dat.py \
  --patched-dat DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS04_C_TEST.DAT \
  --target files/LEVEL01/LEVEL.DAT \
  --expected-sha1 9461ef48f9578ae4bbb068522923b8b03aa9205d \
  --out-bin ABL_G8_ENTRY24_PLUS04_C_TEST.bin \
  --out-cue ABL_G8_ENTRY24_PLUS04_C_TEST.cue \
  --report DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS04_C_TEST_REBUILD.md \
  --write
```

Build result (gitignored artifacts):
- Output image: `ABL_G8_ENTRY24_PLUS04_C_TEST.bin` (`738285744` bytes) / `ABL_G8_ENTRY24_PLUS04_C_TEST.cue`.
- Embedded `LEVEL01/LEVEL.DAT` at LBA `2906` verified SHA1 `9461ef48f9578ae4bbb068522923b8b03aa9205d`
  (== patched DAT). Independent check: embedded DAT bytes at file `0x16e8` read `b3 f9 ff ff`.
- Staged workspace `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine (sha1 `b376cb50…`).
- Report: `DAT/LEVEL01_LEVEL_G8_ENTRY24_PLUS04_C_TEST_REBUILD.md` (gitignored).

### Operator visual test steps (C)

1. Boot `ABL_G8_ENTRY24_PLUS04_C_TEST.cue`.
2. Enter LEVEL01.
3. Move to the same edge-of-level / view-location area where the entry24 reads trigger.
4. Compare against the **pristine** image (and the Candidate A2 image, if useful).
5. Look for any of: localized terrain shift/deformation; clipping/range change; missing or altered
   visual geometry; **no visible change**; or crash/black screen. Record exactly what is seen.
6. Do **not** infer collision/pathing from this test.

Optional CPU confirmation:
- Set `READ 0x80161ee0`, reproduce the edge-of-level entry24 state.
- Expected PC shown `0x8001425c` (read site `0x80014258`); embedded/read target value `0xfffff9b3`.
  (As with A/A2, the data-watch hit confirms the field is read; embedded DAT verification is the proof
  of patched bytes.)

### Candidate C emulator result (2026-06-14) — EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE

Tested `ABL_G8_ENTRY24_PLUS04_C_TEST.cue` (`DAT+0x16e8: b3 f5 ff ff → b3 f9 ff ff`,
`0xfffff5b3` / `-2637` → `0xfffff9b3` / `-1613`, delta `+1024`).

CPU confirmation:

| field | value |
|-------|-------|
| READ watch | `0x80161ee0` (entry24 `+0x04`, `DAT+0x16e8`) |
| hit count | 1 |
| DuckStation PC shown | `0x8001425c` |
| actual read site | `0x80014258` |
| status | **CONFIRMED data read in Candidate C image** |

Visual result:

| check | result |
|-------|--------|
| image boots / LEVEL01 loads | yes |
| crash / black screen | no |
| localized terrain shift/deformation in the edge-of-level entry24 area | none obvious |
| clipping / range change | none obvious |
| missing / altered visual geometry | none obvious |
| pristine / A2 comparison | effectively the same by eye |
| collision/pathing | not assessed — **UNKNOWN** |

**Classification: EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE.**
Candidate C changed a different CONFIRMED-read entry24 body word by `+1024`; the image boots, the
target data-read path is reached, and no obvious visual difference is seen in the tested view.
Collision/pathing was not assessed and remains **UNKNOWN**.

### G8 perturbation summary and conclusion

Small same-sign perturbations of entry24 body fields were valid and read but visually imperceptible:

| candidate | field | DAT offset | original -> patched | delta | classification |
|-----------|-------|------------|---------------------|------:|----------------|
| A | `+0x08` | `0x16ec` | `-1377 -> -1121` | `+256` | EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE |
| A2 | `+0x08` | `0x16ec` | `-1377 -> -353` | `+1024` | EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE |
| C | `+0x04` | `0x16e8` | `-2637 -> -1613` | `+1024` | EXECUTED / VALID BUILD / CPU READ CONFIRMED / NO OBVIOUS VISUAL CHANGE |

This does **not** disprove render-body relevance, but it does show that continued small
perturbations of entry24 body words are low-yield. Stop blind/small entry24 perturbation testing as
the immediate next step. Do **not** propose another small entry24 perturbation as G9.

## 15. G9 — entry24 dataflow tracing (RUNTIME REJECT RESULT 2026-06-14)

**Goal:** trace entry24 values after `fcn.800140a0` reads them. This is a trace/runbook phase, not a
patch phase: do not patch DAT files, build images, run patch scripts, or make collision/pathing
claims. Full table and DuckStation runbook: [geometry_g9_entry24_dataflow.md](geometry_g9_entry24_dataflow.md).

### Static trace summary

| field | source DAT offset | read instruction | immediate use | GTE / branch role | confidence |
|-------|------------------:|------------------|---------------|-------------------|------------|
| `+0x00` | `0x16e4` | `0x8001419c lw s3,-0x14(a0)` | `t0 = s3 - t5` | coarse `SQR` input, full `MVMVA` vector input, reject branches | CONFIRMED dataflow; LIKELY culling/range role |
| `+0x04` | `0x16e8` | `0x80014258 lw t1,-0x10(a0)` | `t1 = t1 - t6` | full `MVMVA` vector input paired with `+0x00/+0x08` | CONFIRMED arithmetic pairing; LIKELY culling/range role |
| `+0x08` | `0x16ec` | `0x800141a0 lw s5,-0x0c(a0)` | `t2 = s5 - t7` | coarse `SQR` input, full `MVMVA` vector input, reject branches | CONFIRMED dataflow; LIKELY culling/range role |
| `+0x0c` | `0x16f0` | `0x800141a4 lh t4,-0x08(a0)` | `bgez t4,0x8001423c`; `t4 >> 4` | path selector and extent/radius-like term in reject tests | CONFIRMED branch control; LIKELY extent/range role |

Static interpretation: entry24 `+0x00/+0x04/+0x08` form a view-relative three-component vector
`(+0x00-t5, +0x04-t6, +0x08-t7)`. The non-negative `+0x0c` path performs a coarse `SQR`
(`0x8001425c`, opcode `0x4aa00428`) and full-vector `MVMVA` (`0x80014298`, opcode `0x4a49e012`),
then tests several reject branches before writing the accepted row pointer to output list A
(`0x8001430c`, base `0x80096ea8`) or list B (`0x80014320`, base `0x8009e338`). No direct
GPU primitive, visible coordinate, or mesh vertex write was observed in this block.

### Conservative answers

- `+0x08` does not appear to feed a direct visible coordinate in `fcn.800140a0`; it feeds GTE
  culling/range/vector calculations. Confidence: **LIKELY**.
- `+0x04` is paired with `+0x00` and `+0x08` as the middle component of the view-relative vector.
  Confidence: **CONFIRMED** for arithmetic pairing, **LIKELY** for axis naming.
- entry24 is **LIKELY** a culling/bounds/range row rather than a direct mesh-position row in this
  helper. Runtime stepping now confirms entry24 rejects before the late list-write path in the tested
  state.
- Best next downstream value to watch: a row that actually reaches `0x8001430c` or `0x80014320`;
  entry24 itself is not a good visual-edit target in this tested state.

### Runtime stepping result

Operator used DuckStation CPU debugger at the known entry24 trigger state. Starting point:
`READ 0x80161ee0` (pass-1 trail entry24 `+0x04`, `DAT+0x16e8`, runtime `0x80161ee0`) broke with PC
shown `0x8001425c`, actual read site `0x80014258`, and `a0=0x80161ef0`.

| PC | observed register | branch result | conclusion | confidence |
|----|-------------------|---------------|------------|------------|
| `0x80014280` | `s3 = 0xffff262b` | `bgez s3,0x80014170` NOT taken | entry24 passes the first reject test | CONFIRMED |
| `0x800142b0` | `t0 = 0x000010b1` | operator-observed `bgtz t0,0x80014170` taken | entry24 rejects here and does not reach the late list-write path in this tested state | CONFIRMED |

**CONFIRMED:** entry24 is read by `fcn.800140a0` and participates in GTE/math reject testing, but in
the tested edge-of-level state it rejects at `0x800142b0` before the late list-write path.

This explains why G8 A/A2/C were valid/read but visually unchanged: the patched fields influence the
reject calculation, but entry24 still was not inserted into the visible output/list path in this
state. This does not prove entry24 can never survive; another camera/player state remains **UNKNOWN**.
Collision/pathing impact remains **UNKNOWN**.

Noisy late-write observation: the late write path was observed for another row with
`t0=0x80161f40`, not entry24 rowbase `0x80161edc`. Therefore do not claim entry24 reached the
list-write path.

Mapping of that other row:

| observed rowbase | base | delta | row size | entry index | row DAT `+0x00/+0x04/+0x08/+0x0c` |
|------------------|------|-------|----------|-------------|------------------------------------|
| `0x80161f40` | `G_TRAIL_BLOCK_PTR=0x80161cfc` | `0x244` | `0x14` | `29` | `0x1748 / 0x174c / 0x1750 / 0x1754` |

The rowbase aligns cleanly. This makes pass-1 trail entry29 the preferred G9b target to map/watch
next, because it was observed at the late list-write path.

### Runtime runbook summary

Use `~/.local/share/duckstation/savestates/SCUS-94288_1.sav` if available to re-enter the
entry24 trigger state. `pause_at_80161EE4.ram` was not found in the repo or searched DuckStation paths
during this documentation pass; treat it as optional external operator context and do not commit it.

Set execute breakpoints at the read sites (`0x8001419c`, `0x800141a0`, `0x800141a4`, `0x80014258`),
the first `SQR`/reject section (`0x8001425c`, `0x80014280`), the full-vector `MVMVA` section
(`0x80014298`, `0x800142a4`), reject branches (`0x800142b0`, `0x800142c8`, `0x800142e8`,
`0x800142f4`, `0x80014304`), and output writes (`0x8001430c`, `0x80014320`). Optional data watches:
read `0x80161edc/0x80161ee0/0x80161ee4/0x80161ee8`; write `0x80096ea8` and `0x8009e338`, or step at
the write PCs once list cursors advance.

Record `a0`, `a0-0x14`, `s3/s5/t4/t1`, `t0/t1/t2/t4/t5/t6/t7/t9/a1`, post-`mfc2` values, branch
taken/not-taken, output write target, and stored value. G9 should prefer this dataflow confirmation
over new DAT perturbations.

RAM/save-state note: a RAM dump alone would not have proven the branch result because the decisive
evidence was transient CPU/GTE register state at specific PCs. The saved state remains useful for
reproducing the trigger, but manual stepping or a CPU/GTE-aware trace is required to confirm
reject/list-write behavior.

### G9b recommendation

Find a row that survives to `0x8001430c` or `0x80014320`, map that row back to DAT offset, then test
whether its body fields produce visible changes. The current runtime clue is entry29:
`rowbase=0x80161f40`, row DAT `0x1748`, fields `+0x00=0x1748`, `+0x04=0x174c`, `+0x08=0x1750`,
`+0x0c=0x1754`. Entry24 is a confirmed read/reject row, but not a good visual-edit target in the
tested state.
