# Executable & Overlays — A Bug's Life (SCUS-94288)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

Reverse-engineering reference for the boot executable `SCUS_942.88`, runtime memory map, the main-shell state machine, the two overlay swap buffers (Region A/B), `LEVEL01\LEVEL.BIN`, the visual sprite-object pool, and the resident collectible/pickup functions. This is architecture reference. DAT *placement* and *coordinate-modding* facts live in [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md) and [COORDINATE_MODDING.md](COORDINATE_MODDING.md); DAT format/relocation lives in [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md).

## Confirmed facts

### Image / disc
- BIN/CUE, single track `MODE2/2352`, 313,897 sectors, no audio tracks.
- ISO9660 vol `A_BUGS_LIFE`, publisher `PIXAR_DISNEY`, region `SCEA` (NTSC-U), dated 1998-10-20.
- `SYSTEM.CNF`: `BOOT = cdrom:\SCUS_942.88;1`, `TCB=4`, `EVENT=16`, `STACK=801FFF00`.

### Executable `SCUS_942.88`
- SHA-1 `af43de22474f15664d0e17498fbd27faeb7ed111`, 471,040 bytes.
- PS-X EXE. Statically linked with PsyQ SDK (`(c) 1993-1997 Sony ...` @ 0x8007FD00).
- File offset 0x800 → VA 0x80010000. Header 0x800 + text 0x72800 = 0x73000 = file size (exact).
- entry PC `0x8005F690`; init GP=0; load `0x80010000`; text size `0x72800`; stack `0x801FFFF0`.

### Runtime / memory facts (provided + verified)
- Runtime `$gp = 0x80081d98` (gp-relative globals resolve against this).
- `.bss` clear range `0x80082200`–`0x800B399F`.
- Mapping rule for strings: `VA = 0x80010000 + (file_offset − 0x800)`.
- PS1 map: RAM 0x80000000–0x801FFFFF (mirror 0x00000000 / 0xA0000000 uncached);
  scratchpad 0x1F800000; I/O 0x1F801000+ (GPU GP0 0x1F801810 / GP1 0x1F801814);
  BIOS vectors A0=0xA0, B0=0xB0, C0=0xC0.

### Entry flow (confirmed)
- `entry0 @ 0x8005F690` (crt0): sets $gp/$sp, clears .bss, calls BIOS thunks, then
  `jal 0x8004fa40` (top-level game shell).
- `fcn.80065eec` = **BIOS A0:39h `InitHeap`** thunk (`addiu t2,0xA0; jr t2; addiu t1,0x39`).
  This is the "heap setup" call from the entry stub — hypothesis upgraded to CONFIRMED.

## Top-level state machine: `fcn.8004fa40` (CONFIRMED "main shell")
Size 2048 bytes (0x8004fa40–0x800502bc). Structure:
- **Init prologue** 0x8004fa40–0x8004fb38: zeroes state globals, calls graphics init
  (`fcn.80039970`), sound/config setters, then enters loops.
- **Outer loop header** `0x8004fb3c` (back-edge from 0x8005012c).
- **Inner loop header** `0x8004fd60` (back-edges from 0x8004fd98, 0x8004fffc, 0x80050250, 0x80050294).
- **Loop exit** → epilogue `0x8005029c` (calls graphics teardown `fcn.80039a20`, returns 0).
  Exit gated on `g_exitCode (0x800aedcc) >= 0` (`bgez`) — negative = keep running.
- **6-way main-shell substate dispatch**: `jr v0` @ 0x8004fc34 via jump table **0x8001b3c4** indexed by
  `[0x8008243c] mod 6`. All 6 targets (0x8004fc3c…0x8004fca0) are INTERNAL to this function.
  Correction: do **not** treat `0x8008243c` as the confirmed live level-load phase-transition target.
  It is a main-shell dispatch/substate index written by the shell itself.
- **Scene-id table**: `0x80077fa0` = small ints {0x11,1,3,2,6,0xa,0xb,4}; selected by
  `[0x8008245c]`, stored into current-scene id `[0x80082504]`.

## Subsystem wrappers (CONFIRMED via string ownership / call edges)
| Function | Evidence | Identity |
|---|---|---|
| `fcn.8006213c` | owns `ResetGraph(%d)...` @0x8001bf58 | libgpu **ResetGraph** |
| `fcn.800625fc` | owns `DrawSync(%d)...` @0x8001bff4 | libgpu **DrawSync** |
| `fcn.8006d61c` | owns `CdInit: Init failed` @0x8001c2c0 | libcd **CdInit** |
| `fcn.80039970` | first call from main; calls ResetGraph; sets disp params | **graphics init** (game) |
| `fcn.80039a20` | last call (cleanup); calls ResetGraph | **graphics teardown** (game) |
| `fcn.80045d6c` | calls CdInit | **CD subsystem init** (game) |
| `fcn.80042fa0` | owns `SoundFX SsVabOpenHead/SsVabTransBody : failed!` | **sound VAB/SFX loader** (game); called from 0x80074a64, 0x80076a64 |
| `fcn.80065eec` | A0:39h thunk | BIOS **InitHeap** |

## Memory validity / OVERLAYS (CONFIRMED)
- Resident image is **only** `0x80010000`–`0x800827ff` (r2 `iS`/`om`: one TEXT map,
  paddr 0x800–0x73000). Anything ≥ `0x80082800` is NOT file-backed.
- `0x800b96e4` is **not backed by file bytes** (unmapped; r2 reads 0xFFFFFFFF fill).
  It is reached by a real, file-backed **direct** `jal 0x800b96e4` @ `0x800503d4`
  (bytes `b9e5020c`, file off 0x40bd4). Not jalr, not a pointer, not an artifact, not a misread.
- Interpretation: **PS1 overlay** — a module linked to a fixed high RAM address (above resident
  end 0x80082800 and above .bss-clear end 0x800b399f), `CdRead`-loaded on demand. The resident
  code hard-`jal`s into the overlay's known entry points.
- ACTION: treat `0x800b96e4` as a **non-resident overlay entry**, not static code. To analyze it,
  find/extract the overlay file from disc and map it at 0x800b96e4. Do not disassemble in-place.

## Overlay decompilation track (SEPARATE substrate; 2026-07-08)

The overlays get their **own** byte-splat substrate, kept apart from the resident
one so the resident metric (`analysis/decomp_progress.json`) is never diluted.

- **Manifest** `config/overlays.yml` — region bases (A `0x800B39A0`, B `0x800B5788`),
  shared `gp`, and per-overlay `{blob, sha1, base, attempted:[…]}`. Sources live under
  `src/overlays/<STEM>/`.
- **VA mapping**: `VA = base + file_offset`. `LEVEL*.BIN` carry a 4-byte ID word
  (`"LEVE"`/`"leve"`) at +0 (the census `4B level_overlay_init` records ARE this ID
  string, not code); real code entry `level_overlay_init` is at +4.
- **Build/validate**: `python tools/build_overlay.py [STEM]` compiles each `attempted`
  function at its load VA (shared substrate v2 pipeline — `--section-start`, `_gp`)
  and splices it into a copy of the blob; the rebuilt blob must be SHA-1-identical.
  `OVL/*.BIN` are gitignored (owner media), so this is **local_media-gated**.
- **Metric**: `analysis/overlay_decomp_progress.json` (matched / 184 overlay code fns).
- **Ranking**: `python tools/build_overlay.py --candidates [STEM]` lists small, complete
  (`jr ra`), cop2/GTE-free unmatched leaves — the overlay analogue of the resident ranker.
- **Guards**: `tests/test_overlays.py` (manifest well-formed + census-consistent CI-safe;
  build-validate `local_media`).
- **Proof (2026-07-08)**: `LEVEL02_LEVEL @ 0x800B3B70` (`*(int*)0x800B4950 = 60`) byte-exact
  → blob SHA-1 PASS. See `[[EXP_2026-07-08_overlay_track]]`, `[[FUNC_800B3B70]]`.

**Running a future overlay campaign**: (1) add the overlay's blob + sha to the manifest;
(2) `--candidates <STEM>` to pick easy leaves; (3) write `src/overlays/<STEM>/<addr>_*.c`;
(4) `build_overlay.py <STEM>` until blob SHA-1 PASS; (5) commit — resident metric untouched.
Overlay functions call resident engine fns (the census `overlays[stem].resident_callees`
ABI surface) and share `$gp`, both auto-resolved by the substrate.

## Overlay system mapping (this session)

### Method
Scanned every resident text word for `jal` (opcode 3), decoded target
`0x80000000 | ((w & 0x03FFFFFF)<<2)`, kept targets outside resident `[0x80010000,0x800827ff]`.
Raw scan = 1158 hits; all but a handful are **data false positives** (impossible targets
> RAM end 0x801fffff). Filtering to plausible RAM `[0x80082800,0x801fffff]` → 74 jals / 51 targets.
Two of those (`0x80142a2c` from 0x8007af38, `0x8017d5d4` from 0x8007e08c) are ALSO false positives
— their neighbors decode to `jal 0x805429e0` / `j 0x8ff02a54` (arithmetic data table). ELIMINATED.

### CONFIRMED: TWO fixed overlay SWAP BUFFERS, each holding different modules over time
Genuine off-image targets split into two disjoint bands; BOTH are fixed-address swap buffers into
which different files are loaded at different times (resident code direct-jals into them, state-gated):
- **Region A: base `0x800b39a0`** (entries seen 0x800b39a4–0x800b42ac, 42). Loaded by **fcn.8003d620**
  (call site 0x8003d638, `a1=0x800b39a0`). Holds **per-level overlay code**: fcn.8003d620 reads a
  level file there then dispatches into it via a jump table (index<0x14). Fed by the level loader
  fcn.8003cf2c → filename built by fcn.80046618 from prefix `level`/`level0` + index + extension.
- **Region B: base `0x800b5788`** (entries 0x800b5ba8–0x800be5e8). Loaded with **multiple different
  overlays over time**: `bits\memory.bin` (sites 0x8003d310, 0x8003f5d0) AND `fmv\fmv.bin` (sites
  0x8003e7fc, 0x8003f578). MEMORY.BIN verified to contain MIPS code (+0x420, +0x7d90 prologues).
- Direct (link-time-fixed) jals ⇒ each buffer always loads at its same fixed base; the *contents*
  are swapped. **Q answered: several modules swapped at the same base, not one resident overlay.**

### fcn.80046330 caller / destination table
| call site | containing fn | a0 (path) | a1 (dest) | class |
|---|---|---|---|---|
| 0x8003d638 | **fcn.8003d620** | built level name (from fcn.8003cf2c) | **0x800b39a0** | **Region A code overlay** |
| 0x8003d310 | fcn.8003cf2c | `bits\memory.bin` | 0x800b5788 | Region B overlay |
| 0x8003f5d0 | fcn.8003f5b8 | `bits\memory.bin` | 0x800b5788 | Region B overlay |
| 0x8003e7fc | fcn.8003e7c0? | `fmv\fmv.bin` | 0x800b5788 | Region B overlay (FMV) |
| 0x8003f578 | fcn.8003f504 | `fmv\fmv.bin` | 0x800b5788 | Region B overlay (FMV) |
| 0x8003d550 | fcn.8003cf2c | built (sp) | 0x8008xxxx (low fixed) | resource data |
| 0x80042f20 | fcn.80042xxx | built | 0x800972a8 | sound/data buffer |
| 0x80042f58 | fcn.80042xxx | built `.vb` | s0 | SPU sample (VB) |
| 0x80055d98 | fcn.80055xxx | built | 0x80095398 | data buffer |
| 0x8005d6ec | fcn.8005d6xx | built `.anm` | s4 | animation data |
| 0x8002ffe4 | fcn.8002ffxx | built `.all` | (not captured) | resource data |
| 0x80030dc0 | fcn.80030xxx | built `.all` | (not captured) | resource data |
| 0x800310c8 | fcn.800310xx | `bits\plantter.all` | (not captured) | resource data |
| 0x8003a388 | fcn.8003a3xx | s0 (passed) | s0 | unknown/data |

Helpers: `fcn.80046618` = level-filename builder (prefix `level`/`level0` @0x800821e0/e8 + idx + ext).

### Region A file format & CONFIRMATION (by bytes)
`fcn.80046618(a0=levelNum, a1, a2=extSel, a3=outBuf)` builds: `level0N\` (levelNum<10) or `levelNN\`,
then appends one of: a2=0 `level.bin`, 1 `level1.bin`, 2 `level2.bin`, 3 `level3.bin`. So
**Region A file = `LEVEL0N\LEVEL[M].BIN`**. Caller chain: fcn.8003cf2c → fcn.80046618 (build name into
sp+0x10) → fcn.8003d620(name, idx) → fcn.80046330(name, 0x800b39a0).

Verified with `LEVEL01\LEVEL1.BIN` (2700 B = 0xa8c):
- bytes: `0f000000` (4-byte header word = entry/func count; LEVEL.BIN's = `05`) then code at **offset 4**.
- mapped at base 0x800b39a0: offset 4 = **`0x800b39a4`** = valid prologue (`addiu sp,sp,-0x20; sw s1..`)
  — this is exactly the most-called Region A entry.
- `0x800b39c4` internal clear-loop (`bgez s1` resolves in-region); `0x800b39dc` loads self-pointer
  `0x800b4334` (inside Region A) → base 0x800b39a0 confirmed correct.
- LEVEL.BIN (0x690) is too small to reach entry 0x800b42ac (off 0x90c); per-level .BINs share a fixed
  entry-offset ABI so the resident direct-jals work for whichever level is loaded.
- **VERDICT: Region A code overlay CONFIRMED.** Layout: [+0..3] header word, [+4 = 0x800b39a4] code.

### Region A ABI — NOT a uniform table (REVISED)
The 42 resident off-image jal targets into Region A are a **UNION across all level variants**, not a
single shared vtable. Each `LEVEL[M].BIN` is independently compiled with its own function layout;
resident callers are scene/state-gated to call only the offsets valid for the variant they expect.
- Byte classification of the 42 offsets (addiu-sp prologue / j-jal veneer / interior):
  - `LEVEL01\LEVEL1.BIN`: prologue at **+0x4 only** (1 pro, 1 veneer, 40 interior).
  - `LEVEL01\LEVEL.BIN`: prologues at **+0x4, +0x14c, +0x218** (+0x14c/+0x218 are *interior* in LEVEL1.BIN).
- **+0x4 (0x800b39a4) is the only UNIVERSAL entry** = per-level overlay init. Verified prologue
  (`27bdffe0`) at +4 in LEVEL01\LEVEL.BIN, LEVEL01\LEVEL1.BIN, LEVEL02\LEVEL.BIN.
  Called by the generic loader fcn.8003d620 right after the read.
- Variants can also be DATA, not code: `LEVEL02\LEVEL1.BIN` has `"level"` text at +4 (not a prologue)
  → that variant is a data table, not executed. So "is it code" is per-file, not per-name.
- 4-byte header word = likely an **overlay-ID/version stamp** (HYP): level.bin={5,6}, level1.bin={15,16}
  for dirs 01/02 ⇒ pattern `≈ dir_index + 4 + 10*M`. Not a function/entry count (LEVEL.BIN has MORE
  entry prologues than LEVEL1.BIN yet a smaller header). Unproven.

### Region A primary entry 0x800b39a4 = level_overlay_init (CONFIRMED behaviour)
`fcn.800b39a4(...)`, 336 B. Steps:
1. Clears 0x80 (128) resident words downward from 0x80096d94 (to ~0x80096b94).
2. Copies an **overlay-local table at 0x800b4334** (≈0xd0 bytes) into resident RAM at 0x80096b98.
3. Loops s1=0..0x7f (128 slots): for each non-null entry reads/derives indices from resident tables
   0x80091148 / 0x80091188 / 0x800a7dd8 and calls resident **0x80061a48** per slot.
4. Calls resident **0x8003e4e0**, returns.
- Resident callbacks: 0x80061a48 (×128), 0x8003e4e0. Overlay-local data: 0x800b4334. No $gp use here.
- Purpose: **initialise the level's 128-slot entity/object table** from overlay-local data. HIGH conf.
- Proposed label: **`level_overlay_init`** (offset +0x4 of every code Region-A overlay).

### Region A 2nd verb 0x800b3aec (LEVEL01\LEVEL.BIN +0x14c) — object spawner
204 B. Clears overlay-local `0x800b402c`, then calls resident `0x80042c70` **3×**, each with:
a1=`0x77` (object type, same all 3), a2/a3 = large +/- constants (world coords, e.g. 0xfffe0169,
0xfffda4e2, 0xfffd8375), stack args = {0x782c9/0x2554e/0x1d2ce, 0xc350=50000 / 0x9c40=40000, -25}.
- **Behaviour: spawns 3 entities of type 0x77 at fixed positions.** It is a state-entry spawn/placement
  verb (called by the 0x8005484c switch + fcn.8005b12c, g_sceneId-gated). No counters/flags/pickup-IDs/
  sound/HUD/save writes here → pure object placement. Conf HIGH (spawn), object identity unknown.

### Resident object spawner 0x80042c70 — CONFIRMED
`(a0, type=a1, a2, a3, [sp:p1,p2,p3])`. Searches a slot table at ~0x8009c870 (lh -0x3790(0x800a..),
indexed; `bnez`→skip occupied) for a free entity slot, then allocates+inits it from the args.
18+ callers. **= object/entity allocator+spawner.** Conf HIGH. Used by Region-A overlays to place
level objects.

### Resident 0x80061a48 — leaf bit-packer (NOT an object builder; corrects prior guess)
60 B, leaf (`jr ra`, no calls). Packs 4 args into one 16-bit word v0:
a0[1:0]→v0[8:7], a1[1:0]→v0[6:5], a3[8]→v0[4], a2[9:6]→v0[3:0], a3[9]→v0[11].
In level_overlay_init its result is stored at entity+4 (a 16-bit field), computed from sprite/tile
lookup tables (0x80091148/0x80091188/0x800a7dd8). Likely a **packed render/texture attribute** for
each entity (tpage/clut/coord-ish). Conf MED. Candidate: `pack_attr16`.

### Gameplay-candidate evidence (tentative — NOT confirmed mechanics)
| addr | behaviour | possible meaning | conf | tentative label |
|---|---|---|---|---|
| 0x80042c70 | slot-search + alloc/init entity(type,coords) | object spawner | HIGH | candidate_spawn_object |
| 0x800b3aec | spawns 3× type-0x77 at fixed coords | level object placement | HIGH(spawn)/LOW(meaning) | candidate_level_place_objects |
| 0x80061a48 | packs 4 fields → 16-bit, stored entity+4 | render/texture attribute | MED | candidate_pack_attr16 |
| type 0x77 | a1 to spawner ×3 | an object type id | — | candidate_object_type_0x77 |
| 0x800b402c | overlay-local, cleared before spawns | spawn count / list head | LOW | candidate_spawn_state |
| entity slot table | base ~0x8009c870; entity+4 = packed attr | per-object render records | MED | candidate_entity_table |
- **No grain / FLIK-letter / token / gold-berry / kill-count evidence yet.** This verb is spawn/
  placement only; collectible/kill logic would live in collision/pickup handlers (not seen here).

### Region A 3rd verb 0x800b3bb8 (LEVEL01\LEVEL.BIN +0x218) — event/update handler
924 B. Called via the CALLBACK DISPATCHER fcn.80054964 (jump table @0x8005494c, default string
"UnHandled Callback Occured"; callback id 1..0x11), itself reached from the state machine via
fcn.8004ecd4. So +0x218 is an **event/callback-driven handler, NOT per-frame**.
Behaviour:
- jal resident 0x800510f0(0x800b401c, 0, 4) — register/init an overlay-local struct (count 4).
- Ticks overlay-local **0x800b402c** countdown (dec if >0); paired with +0x14c which clears it.
- Reads a **byte command/script stream** via cursor **[0x800822f4]** (sequential lbu, cursor++):
  pulls 3 bytes as packed coords ((b-0x80)<<4), jal 0x80059e44(...); then a type byte (&3) and a
  delay byte → resets 0x800b402c = byte+0xc8. = a timed scripted-spawn/event sequencer.
- **Nearest-object search**: loops a table at [0x80096da4] (stride 0xc), squared-distance vs reference
  position 0x800a6500/0x800a6508 (>>5; likely player/camera), tracks min → stores nearest index at
  actor+0x5e. Then updates actor transform (actor+0x4/8/c coords, +0x28..0x3c matrix) via 0x80025084.
- Sets flags 0x800910f9 / 0x800910fa from 0x800a6597 / 0x800a65a2 (&4).
- Does NOT call 0x80042c70. Resident callbacks: 0x800510f0, 0x80059e44, 0x80050d1c, 0x80025084.
- Classification: **update/event verb** (scripted spawn + proximity targeting + transform). Distinct
  from the +0x14c placement verb. The two share script-timer 0x800b402c (start vs tick).

### Entity / object tables (recovered)
- **Large-object slots: base 0x8009c870, 8 slots, stride 0x344 (836 B)**; slot[+0].hword = active flag
  (spawner skips if nonzero). Allocated by `candidate_spawn_object` (0x80042c70) → filled by fcn.8003f620.
  Spawn args: a1=type, a2/a3+stack = coords/params.
- **Object pointer array: base 0x80096b98, 128 × 4-byte pointers**; built by level_overlay_init;
  pointed object +4 = packed render attr (from pack_attr16 / 0x80061a48).
- **Proximity table: base [0x80096da4], stride 0xc** (used by +0x218 nearest search).
- Actor struct (s1=0x800a0a64): +4/8/c = coords, +0x28..0x3c = transform matrix, +0x5c = flags(&0x4000),
  +0x5e = nearest-target index, +0x80 = ptr to render record.

### Gameplay candidates (updated; still tentative)
| addr | behaviour | possible meaning | conf | tentative label |
|---|---|---|---|---|
| 0x8009c870 | 8×0x344 slots, +0 active flag | large-object/actor table | HIGH | candidate_object_slots |
| 0x80096b98 | 128 × ptr | object pointer list | HIGH | candidate_object_ptr_list |
| 0x800b402c | clear(+0x14c)/dec+reset(+0x218) | scripted-event countdown timer | MED | candidate_script_timer |
| 0x800822f4 | sequential byte reader (coords/type/delay) | level command/script stream ptr | MED | candidate_script_cursor |
| [0x80096da4]+0xc | nearest-by-dist vs 0x800a6500/6508 | proximity targeting | MED | candidate_proximity_target |
| 0x800a0a64 | actor struct (coords/matrix/flags/target) | active actor/camera struct | MED | candidate_actor_struct |
- **Still NO grain / FLIK / token / gold-berry / kill-count evidence.** +0x218 is movement/scripted-
  event/targeting logic — no counters incremented, no pickup-ID compares, no collection SFX/HUD/save.

### Resident 0x80025084 — oriented range/containment test (geometry; NOT collectible)
540 B. Args from the +0x218 call site: a0=`0x8009ec50` (a world point: x@0,y@4,z@8), a1=actor
(`0x800a0a64`). (a2/a3 are derived internally, not passed.) Behaviour:
- a1[0] indexes a pointer table at 0x800a6300; if the pointed object's first hword is 0 → return 0.
- For each axis: delta = (actorCoord<<5) − point; multiply by a 3x3 rotation matrix at **0x80090fb0**
  (16-bit entries 0xfb0/fb2/fb4 and 0xfbc/fbe/fc0) → projected/rotated coords (v1, a0).
- Range-test the projected coords against actor extents a1+0x66 / a1+0x6a; out of range → `move v0,zero`
  → return 0. Contained/in-range → return nonzero.
- **= oriented bounding/containment test (collision-or-visibility).** HIGH conf geometry; MED which.
- Return-value gating in 0x800b3bb8: `sw v0,8(renderRec)` then `bnez v0 → SKIP` the transform/snap
  block. So **nonzero (in-range) = skip update; zero (out-of-range) = snap actor coords to nearest**.
- **No gameplay-counter evidence**: no counter inc/dec, no type compares, no bitflag-by-type, no
  object deletion, no pickup SFX/event, no HUD/progress/save writes. Pure math + one stored result.
- Other caller: fcn.8004d224 @0x8004d3bc. Label: `candidate_oriented_range_test` (geometry).
- Actor-struct fields learned: +0x66/+0x6a = extents/half-size (hword), +0x80 = ptr to coord/render
  record (coords <<5), [0] = index into 0x800a6300 object-pointer table.

### Gameplay verdict (this pass)
0x80025084 is geometry, not collectible/kill logic. Still **NO grain/FLIK/token/gold-berry/kill-count
evidence** anywhere in the Region-A verbs analysed so far (init / spawn / event-update) or this test.
Collectible/HUD/save logic has not yet been located; look in object-type dispatch + contact handlers.

### Large-object slot struct (0x344) — fcn.8003f620 fill (partial, key fields CONFIRMED)
Slot base = `0x8009c870 + idx*0x344`. Field offsets within slot (from fcn.8003f620 writes):
- `+0x00` h = active flag / type-low (= f620 a1; spawner skips slot if nonzero)
- `+0x02` h = secondary id/param (= a2)
- `+0x06` b, `+0x07` b = small params (from stack args)
- `+0x08` w = arg4[3]
- **`+0x24` w = X, `+0x28` w = Y, `+0x2c` w = Z** (vector copied from arg4 = spawn coords), `+0x30` w
- `+0x34..` w = second vector (from arg_20h), `+0x40` w = arg_24h
- many `+0x44..+0x60` zeroed (state/timer/flags init 0); `+0x60+` computed (per-axis divide loop)
- (full 0x344 not exhaustively mapped; the position triple +0x24/+0x28/+0x2c is the mod-relevant part)

### Spawn ABI — candidate_spawn_object (0x80042c70) → fcn.8003f620
`0x80042c70(a0, type=a1, a2, a3, [sp:p1,p2,p3])`: finds free slot (8×0x344 @0x8009c870, +0 flag),
builds vectors on its stack, calls fcn.8003f620 which stores: type→slot+0, **{a2,a3,p1}→slot+0x24/0x28/0x2c
= X/Y/Z**, p2(=scale-ish, e.g. 50000)/p3(=-25) into other fields. Coords are raw signed 32-bit (no
extra scaling at store; consumers apply <<5 / matrix later).
- Resident callers of 0x80042c70: **none found** (axt empty) → invoked only from overlay code.
- Known caller: overlay `0x800b3aec` (LEVEL01\LEVEL.BIN), 3× with type **0x77** at fixed coords.
- Example (spawn #1, type 0x77): X=245049, Y=-130711, Z=492233.

### Object type 0x77 — identity UNKNOWN
No type-dispatch/pickup/HUD/save evidence yet. 0x77 is just the value passed as `type`. Do NOT map to
grain/FLIK/token/gold-berry/enemy without the type-handler. **No collectible/kill-count evidence still.**

### FIRST SIMPLE COORDINATE MOD (concrete, verified bytes)
Move type-0x77 spawn #1 in `LEVEL01\LEVEL.BIN`. Its X/Y/Z are `lui+ori` immediates in the overlay:
| axis | value | lui (file off / imm) | ori (file off / imm) |
|---|---|---|---|
| X | 245049 (0x0003bd39) | 0x160 / 0x0003 | 0x164 / 0xbd39 |
| Y | -130711 (0xfffe0169) | **0x168 / 0xfffe** | 0x16c / 0x0169 |
| Z | 492233 (0x00078 2c9) | 0x150 / 0x0007 | 0x154 / 0x82c9 |
(file offset = VA − 0x800b39a0; imm16 = low 2 bytes of the 4-byte word.)
- To shift Y by ±0x10000: edit the lui imm's low byte at **file 0x168** (`0xfe`): →`0xfd` = Y−65536,
  →`0xff` = Y+65536. (lui|ori, so no addiu sign-fixup needed.) Single-byte edit.
- Vertical-axis identity is UNCONFIRMED — test which of X/Y/Z is "up" empirically first.
- SCOPE: affects only LEVEL01\LEVEL.BIN (level.bin variant) → logical stages mapping to level01 dir.
- To run: live-patch RAM at VA 0x800b3b08 in an emulator (easiest), OR reinsert LEVEL.BIN into the BIN
  at LBA 2905 as Mode2/2352 with regenerated EDC/ECC (needs mkpsxiso/cdpatch-style tool).

### Spawn census — all `jal 0x80042c70` across extracted level overlays
Scanned 20 extracted LEVEL0N\LEVEL[M].BIN for word 0x0c010b1c (=jal 0x80042c70), back-sliced args.
Resident SCUS has **0** such calls → spawner is overlay-only.
| type | file | callVA | X | Y | Z | source |
|---|---|---|---|---|---|---|
| 0x77 | LEVEL01_LEVEL.BIN | 0x800b3b34 | 245049 | -130711 | 492233 | direct lui/ori |
| 0x77 | LEVEL01_LEVEL.BIN | 0x800b3b68 | -154398 | -162955 | 152910 | direct lui/ori |
| 0x77 | LEVEL01_LEVEL.BIN | 0x800b3b98 | -195102 | -187531 | 119502 | direct lui/ori |
| 0x77 | LEVEL06_LEVEL1.BIN | 0x800b3c4c | 35708 | -79616 | 41261 | direct lui/ori |
| 0x32 | LEVEL02_LEVEL1.BIN | 0x800b3b78 | -170573 | -211459 | 12152 | direct lui/ori |
| 0x32 | LEVEL02_LEVEL1.BIN | 0x800b3c38 | -151531 | -587791 | -3204 | direct lui/ori |
| 0x32 | LEVEL02_LEVEL1.BIN | 0x800b3c68 | -141262 | -616300 | -68840 | direct lui/ori |
| 0x32 | LEVEL02_LEVEL1.BIN | 0x800b3c98 | 20997 | -675484 | -164881 | direct lui/ori |
| 0x33 | LEVEL02_LEVEL1.BIN | 0x800b3bb0 | 140943 | -343479 | 48307 | direct lui/ori |
| 0x33 | LEVEL02_LEVEL1.BIN | 0x800b3be0 | -54769 | -450560 | -158429 | direct lui/ori |
| 0x33 | LEVEL02_LEVEL1.BIN | 0x800b3c0c | 34184 | -517282 | 139144 | direct lui/ori |
- All 11 are **static placements with direct lui/ori immediate coords**. Types seen: 0x77, 0x32, 0x33.
- **Axis inference: −Y = UP (MED-HIGH).** The LEVEL02 0x32/0x33 set has monotonically decreasing Y
  (-211459 → -675484) across the spawn list = a vertical progression of objects → smaller (more
  negative) Y is higher. X/Z scatter; Y trends. (Empirically confirm in emulator.)
- Object identities (0x77/0x32/0x33) STILL UNCONFIRMED — no type-dispatch/pickup/HUD/save seen.

### Object-type dispatch — candidates (identity NOT yet confirmed)
Resident object processors (iterate 8 slots, stride 0x344, touch slot+0):
- `fcn.8003f938` (4288 B) — large; reads slot+0; prime suspect for per-type behavior dispatch.
- `fcn.80041ac4` (2404 B) — per-slot render/anim update (writes slot+0x12; calls render fcn.80060154).
- `fcn.800409f8`, `fcn.80042a40` region — also touch slot+0.
No clean type→handler jump table located yet. (Scanner caveat: a helper mis-set VA = load+fileoff
WITHOUT subtracting the 0x800 header; real VAs are 0x800 lower — corrected above.)

### FIRST SAFE COORDINATE-MOD RECIPE (type-0x77 spawn #1, LEVEL01\LEVEL.BIN)
Coords built by lui/ori immediates; Y is (inferred) vertical, −Y = up. Current Y = -130711 (0xfffe0169).
Instruction VAs (overlay mapped at 0x800b39a0): lui a3,0xfffe @0x800b3b08, ori a3,0x169 @0x800b3b0c.
- **Coarse up (±65536):** flip the lui high-half low byte. File `LEVEL01\LEVEL.BIN` offset **0x168**:
  `0xfe → 0xfd` ⇒ Y = -196199 (UP ~65536). `0xfe → 0xff` ⇒ Y = -65175 (DOWN). Single byte, safe
  (lui|ori, no sign-fixup).
- **Fine:** edit ori low half (file 0x16c/0x16d) — adjusts within the current 64K band only.
- **Live RAM test (preferred):** in emulator, before/at level01 load, patch RAM byte at VA 0x800b3b08+? 
  — i.e. set the lui immediate (halfword at 0x800b3b08, bytes fe ff → fd ff), then (re)load level01 so
  the spawn runs with the new value. (Spawn is one-shot at overlay init; must run after the patch.)
  Alt: continuously force the object's stored Y at slot+0x28 (slot0 = 0x8009c898) if idx 0.
- **File patch:** file LEVEL01\LEVEL.BIN, offset 0x168, orig `fe`, new `fd`. To run from disc, reinsert
  the file into the .bin at LBA 2905 as MODE2/2352 with regenerated EDC/ECC (mkpsxiso/cdpatch-class
  tool) — NOT a raw byte poke into the .bin (would corrupt the sector). Owned-disc preservation only.
- Scope: only stages loading LEVEL01\LEVEL.BIN (level.bin variant); not global.

### Collectible-evidence verdict (this pass)
Still **NONE**. No type compares→handlers, no contact/deactivation, no counter inc/dec, no collection
SFX, no HUD/save writes found yet. Types 0x77/0x32/0x33 remain unlabelled object IDs. Grain / FLIK /
token / gold-berry / kill-count all remain unconfirmed hypotheses.

### fcn.8003f938 = object RENDER/projection loop (NOT a type dispatcher)
4288 B, called from fcn.800224ec. `s4 = 0x1f800374` (scratchpad camera/view struct: +0/4/8 = camera
pos, +0x20..0x28 = rotation matrix). Iterates the 8 slots (base 0x8009c870, stride 0x344): reads
slot+0 **only as an active flag** (`beqz`→skip), projects the slot's render position
(slot+0x34/0x38/0x3c/0x40) relative to the camera by the rotation matrix, distance-culls
(`slt` vs a max-dist-squared), then draws. **No type compares, no per-type dispatch, no pickup/counter.**
So slot+0 = active flag + render/model id; slot+0x24/28/2c = spawn/home pos; slot+0x34.. = render pos.

### fcn.8003f5fc = mass-clear of the object table (level reset, NOT pickup)
36 B: loops v0 = 0x16dc → 0 step −0x344 (8 iterations), `sh zero` to slot+0 each → zeroes the active
flag of ALL 8 slots. Called from fcn.8003e3e0 (level-loader path). = table reset on level load.
Only resident writers of slot+0: fcn.8003f620 (spawn-set) and fcn.8003f5fc (mass-clear). **No
per-object removal exists in resident.**

### REFRAME: the 0x8009c870 system is a VISUAL sprite-object pool, not collectibles
Evidence: spawn(type,coords) → render(project+cull+draw) → mass-clear on load. No type-behavior
dispatch, no per-object pickup/deactivation, no counter/HUD/save anywhere in this path. So types
**0x77 / 0x32 / 0x33 are sprite/model ids of placed visual objects**, NOT confirmed collectibles.
The coordinate mod still moves a real placed object — but its gameplay role is unconfirmed (could be
decorative or a pickup-sprite whose pickup logic lives elsewhere).

### Object-behavior map
| function | role | slot fields | type checks | deactivation | counter/HUD/save |
|---|---|---|---|---|---|
| fcn.80042c70 | spawn/alloc slot | +0 write, +0x24/28/2c pos | none | no | none |
| fcn.8003f620 | slot fill | +0,+0x24..+0x40,+others | none | no | none |
| fcn.8003f938 | render: project+cull+draw active slots | +0 active, +0x34..0x40 pos | none | no | none |
| fcn.80041ac4 | per-slot anim/render update | +0x12, stride 0x344 | none | no | none |
| fcn.8003f5fc | clear ALL slots (level reset) | +0 ×8 = 0 | none | mass only | none |

### Collectible-evidence verdict
Still **NONE** — and now we know WHY: the subsystem analysed is visual-object rendering, not gameplay
pickups. Grain / FLIK / token / gold-berry / kill-count must live in a DIFFERENT subsystem (likely the
128-pointer entity list at 0x80096b98 built by level_overlay_init, or a player-collision + HUD/save
path). Not yet located.

### COLLECTIBLE SYSTEM FOUND — grain (50) + FLIK (4) match the HUD (HIGH confidence)
The HUD draw routine **fcn.800526f4** (called from fcn.8004ecd4 / fcn.8004f478) renders both:
- **Grain counter = byte at `0x800a65a1`.** At 0x80052ab8 `lbu 0x65a1(0x800a)`, then 0x80052ac0
  `sltiu v0,v0,0x32` (compare < 50), drawn via **fcn.800260f8** (number/digit draw; opens with the
  ÷10 magic `0x66666667`). 50 = grain target → matches "50 grain". Label: `candidate_grain_count`.
  NOTE: only READ at the absolute addr (no `sb` to 0x65a1) → true storage is pointer-based in a
  progress/save struct; 0x800a65a1 is the HUD mirror. The pickup-increment path is not yet located.
- **FLIK letters = exactly 4 collected-gated icons.** 4 blocks at 0x800531a4..0x80053230: each
  `lw v0,<ptr>(0x800a)` from `0x800a0220 / 0x800a0430 / 0x800a0a60 / 0x800a0d78`, then
  `lbu v0,0x1b(v0)` (collected flag at record **+0x1b**); if set, draw icon (tiles 0x32/0x34/0x35/0x33)
  at HUD X = 0x54/0x7c/0xa4/0xcc (step 0x28). 4 letters → matches "4 FLIK letters".
  Labels: `candidate_flik_record_ptrs` (the 4 globals), `candidate_flik_collected_flag` (record+0x1b).

HUD helpers: `fcn.800260f8` = draw number/value as digits (÷10 loop); `fcn.80025f54` = draw sprite/tile
at (x,y). `0x800a65a0` = separate state byte (heavily written, ~22 sites; NOT grain — unidentified).

### GRAIN PICKUP HANDLER — fcn.80054eac (CONFIRMED)
The real grain increment (absolute-store scan missed it because it's pointer-relative):
- `0x80054f88`: `lui v0,0x800a; addiu v0,v0,0x65a1; lbu v1,(v0); addiu v1,v1,1; sb v1,(v0)`
  = **grain_count++ at 0x800a65a1**.
- `0x80055000`: `lbu grain; addiu v0,zero,0x32; bne v1,v0,..` = **if grain_count == 50 → reward path**
  (0x80055174). Confirms 50-grain target.
- Front half reads the level command/script byte stream via cursor `[0x800822f4]` (same cursor as
  0x800b3bb8), calls fcn.80045678 / fcn.80044d28 (pickup effect/spawn). Pulses HUD at 0x800b018c.
- Callers: callback handlers 0x80054278 / 0x800589b8 / 0x80059cb4 (event/callback table) + fcn.8005b12c.
- **UPGRADE labels to CONFIRMED:** `0x800a65a1` = **grain_count** (byte, target 50); `fcn.80054eac` =
  **grain_pickup_handler**. Grain is event/callback-driven (player contact → callback → this handler).
- Progress struct: 0x800a6580–0x800a65af is a per-level progress/results block (many sub-fields:
  0x6588 score/digit, 0x6590 flags, 0x6594, 0x659e, 0x65a0 state, 0x65a1 grain, 0x65a3..0x65a8).
  Written by fcn.80047284/80048138/8004a700/800563d4/80056f68/8005b12c via base-pointer (0x800a6500
  is used as the struct base in fcn.80054eac/45678: `addiu a0,0x800a,0x6500`).

### COLLECTIBLE / ENTITY PLACEMENT ARRAY — fcn.800586b0 (CONFIRMED walker)
`fcn.800586b0` (called from fcn.8004ecd4 @0x8004f074) = the **player-proximity/contact pickup walker**.
- Array base **`0x800b0d18`** (resident .bss, filled from level data at load), **64 records × stride 0x38**
  (`slti s4,0x40`; s3 += 0x38 per record).
- **Record layout (offsets from record base):**
  - `+0x00` = **X** (s32), `+0x04` = **Y** (s32), `+0x08` = **Z** (s32)  ← coordinates
  - `+0x22` = active/type (hword; `blez`→skip when ≤0)
  - `+0x33` = flags byte (`andi 2` = collidable/enabled gate)
- **Player position globals: `0x800a6500` (X) / `0x800a6504` (Y) / `0x800a6508` (Z)** (same refs used by 0x800b3bb8).
- Per record: dx=(pX−X)*0x300>>0xd, dy=(pY−Y)*0x100>>0xd, dz=(pZ−Z)*0x300>>0xd; dist=dx²+dy²+dz² →
  proximity threshold → fire pickup callback. On pickup: grain → fcn.80054eac (grain++); FLIK → one of
  4 callback cases (0x80054288.. set `0x800a6597 = 1/2/3/4` + sounds a0=0x35/0x36/0x37/0x38) = the 4 letters.
- fcn.8005044c = post-pickup bookkeeping (gp progress fields). 0x800a6597 = FLIK letter marker (0..4).
- NOTE: array is in .bss (0x800b0d18 < .bss-end 0x800b399f) → populated at runtime from per-level data
  (LEVEL.DAT/RAW). The fill routine / file offset not yet mapped, but the RUNTIME array is directly moddable.

### COORDINATE-MOD RECIPE for a collectible (live RAM, owned-disc test)
For entity record index i (0..63): base = `0x800b0d18 + i*0x38`; X@base+0, Y@base+4, Z@base+8.
- After a level loads, in an emulator: find an active record (hword at base+0x22 > 0), read X/Y/Z.
- **Move up:** decrease Y (base+4) — write a more-negative value (−Y ≈ up, per LEVEL02 spawn-Y trend).
  Smallest visible nudge: subtract a few thousand from Y; iterate.
- Example record 0: X@0x800b0d18, Y@0x800b0d1c, Z@0x800b0d20.
- File-patch path requires locating the level-data fill (LEVEL.DAT/.RAW) — not yet mapped.

### 0x800b0d18 population / placement source — NEW evidence
The runtime array is **not** a raw 64*0x38 block copied from disc. Current evidence says level DAT
records/scripts are parsed, then individual runtime records are constructed into `0x800b0d18`.

- `fcn.8003e3e0` is the reset/clear step run from `fcn.8003cf2c`: it clears record `+0x22` for all
  64 slots with a reverse loop over `0x800b0d3a + i*0x38`. This deactivates the contact array; it does
  not populate it.
- `fcn.8003cf2c` is the level/resource loader. For DAT resources it builds paths such as
  `LEVEL0N\LEVEL[M].DAT`, stores the destination heap pointer in `0x80082498`, calls
  `fcn.80046330(path, [0x80082498])`, then calls `fcn.8001cdc0`.
- `fcn.8001cdc0` is the DAT parser/relocator. It reads a leading record count, walks variable-sized
  records, and builds internal pointer tables. The DAT format is therefore structured/encoded; no direct
  `0xe00` placement-array copy to `0x800b0d18` was found.
- Confirmed runtime constructors/populators:
  - `fcn.80059e44`: allocates a slot via cursor `0x8008234c`, writes X/Y/Z to `+0/+4/+8`, fills the
    record from the resident metadata table, and calls `fcn.80024ddc`.
  - `fcn.8005a0e0`: same slot allocator and metadata fill, but accepts explicit transform/vector args
    for `+0x0c/+0x10/+0x14/+0x18`.
  - `0x8008234c` is the 64-slot allocation cursor; `fcn.8005743c` resets it.
- Resident metadata table: `0x8007941c`, stride `0x14`. Constructor type ID selects one entry:
  - table `+0x00` -> record `+0x20` walker dispatch id
  - table `+0x02` -> record `+0x22` active/type hword
  - table `+0x04` -> record `+0x24` initial value, copied to `+0x26`
  - table `+0x08/+0x0a/+0x0c` -> record `+0x28/+0x2a/+0x2c`
  - table `+0x10` -> record `+0x33` flags
  - table `+0x11/+0x12/+0x13` -> record `+0x34/+0x35/+0x36`
- Grain discriminator, high confidence: constructor type ID `0x51` has table `+0x0c = 0x16`; this
  becomes record `+0x2c = 22`. `fcn.8005953c` case 22 calls `fcn.80054eac` (grain_pickup_handler),
  then does pickup bookkeeping/effects.
- FLIK discriminator is **not safely mapped yet**. Known FLIK collection writes still include
  `0x80054288..0x800542dc` and `0x80058930..0x80058980`, but the constructor type IDs / DAT command
  bytes that lead to those cases are not proven.

File patch status:
- Grain coordinate patching is solved for the normal DAT type-`0x3f` / source type-`0x14` path below.
- Exact runtime slot number remains allocator-state dependent because `fcn.80059e44` chooses a free
  `0x800b0d18` slot at spawn time.
- FLIK source mapping remains intentionally unresolved here.


### Manual overlay load (r2)
Overlay-internal only:
`r2 -q -a mips -b 32 -e cfg.bigendian=false -m 0x800b39a0 -c 'e anal.gp=0x80081d98; af @ 0x800b39a4; pdf @ 0x800b39a4' LEVEL1.BIN`
Combined with resident (so calls back into SCUS resolve): open SCUS_942.88, then
`om \`o LEVEL1.BIN\`` and `om <fd> 0x800b39a0 0xa8c 0 r-x`, set arch mips/32/LE, gp=0x80081d98.

### fcn.8003f5b8 = overlay loader+init for MEMORY.BIN (Region B) — CONFIRMED
```
fcn.8003f5b8():
  a0 = "bits\memory.bin" (0x8001adfc); a1 = 0x800b5788 (dest, = Region B base)
  jal fcn.80046330            ; file read into 0x800b5788
  [gp+0x588 / 0x80082320] = 0x800d5790   ; stores a derived pointer
  jal 0x800bd518              ; = MEMORY.BIN + 0x7d90 : overlay init entry, no args set after load
```
- So Region B (MEMORY.BIN) load is **CONFIRMED**. Region A (0x800b39a0) is NOT loaded here — it has a
  different (still unknown) loader.
- Label: **`overlay_init_loader`** (handles the MEMORY.BIN overlay specifically). HIGH confidence.

### fcn.80046330 = central file-read primitive — CONFIRMED
- 14 call sites across the loaders (incl. fcn.8003f5b8 @0x8003f5d0 and fcn.8003cf2c cases
  @0x8003d310/0x8003d550/0x8003d638). Signature `(char *path, void *dest)`.
- Lowercases the filename, then calls BIOS A0 thunks `fcn.8005f76c` / `fcn.8005f74c` ⇒ BIOS-level
  file I/O (CD). This is the resident "load file by name into buffer" routine.

### fcn.8003cf2c = level/SFX resource loader (index-dispatched)
- `arg1∈[1,0x11]` → `jr v0` via internal case table 0x8001afb0 (cases all inside 0x8003cfc4–0x8003d1bc).
- Each case sets `a0` = a path string from the table at 0x8001ad00; arg1=0/default → `sfx\global`.
- Paths (idx→path): 0=`sfx\global`, 1=`level01\level1a`, 2=`level03\level1b`, 3=`level02\level1c`,
  4=`level06\level2a`, 5=`level10\level2b`, 6=`level01\level2c`, 7=`level04\level3a`, … through
  `level5c` (15 level paths @0x8001ad0c–0x8001adec). Dest/read handled in shared tail
  (fcn.80042e94 / fcn.80061a48) — destination not yet captured.
- These load **level resources**; whether any supplies Region-A code is UNPROVEN.

### Tooling caveat
- This host's `rasm2` mis-decodes MIPS (e.g. `27bdffe8` → garbage). Use r2 with explicit
  `e asm.arch=mips; e asm.bits=32; e cfg.bigendian=false`, or read raw bytes, for overlay files.

### Off-image jal target clusters (genuine)
| Region | targets | calls | notes |
|---|---|---|---|
| 0x800b39a4–0x800b42ac | 42 | 64 | dense API surface; many state-switch dispatchers |
| 0x800b5ba8–0x800b6594 | 3 | 4 | |
| 0x800b96e4–0x800b9a28 | 3 | 3 | incl. 0x800b96e4 (fcn.8005038c) |
| 0x800bd518 | 1 | 1 | from fcn.8003f5b8 (init-time loader) |

### Loaders (CONFIRMED file loaders; reference path strings)
- `fcn.8003cf2c` (1240 B): **index-dispatched resource loader**. arg1 bounds-checked to [1,0x11];
  `jr v0` via jump table **0x8001afb0** (17 cases), each referencing a file path; arg1=0 → default
  `sfx\global` path. Called by fcn.8005038c, fcn.8003f504, fcn.8005222c, fcn.8005b70c.
- `fcn.8003f5b8`: init-time loader (called from main @0x8004fafc); references `bits\memory.bin`
  AND issues the off-image `jal 0x800bd518`. Strong overlay-loader candidate.
- `fcn.8003e3e0`: called first inside fcn.8003cf2c (sub-step, unexamined).

### Candidate disc files
- `BITS\MEMORY.BIN` (36,448 B = 0x8E60) — **OVERLAY (data table head + MIPS code)**. CORRECTION to
  prior note: it is NOT data-only. Header `1a 00 00 00`(=26 entries) + `level00\level...` table, then
  executable code. Loaded by fcn.8003f5b8 to **0x800b5788** (= Region B). Init entry at +0x7d90 (0x800bd518).
- Other BITS: PLANTTER.ALL (17,760), SEED.ALL (16,576), TTLOGO.BGR (153,600 — title image).
- GFX\*.RAW = per-level VRAM/texture images (43–120 KB). PAD\PATH*.BIN = pathfinding (≤1.3 KB).
- **Source file for the 0x800b39a0 CODE region: still UNKNOWN.** Must trace which loader case writes
  a destination address in 0x800b39a0–0x800bd520.

## Hypotheses (NOT confirmed — need more evidence)
- `fcn.8005038c` (called ~10×, args id+param): swaps `g_sceneId`, writes `[0x800823ac]=arg+0x43c`,
  calls 0x80039478→`jal 0x800b96e4`. The 0x800b96e4 target is a **non-resident overlay entry**
  (see Overlays). So `fcn.8005038c` is an **overlay/module entry dispatcher** — MED confidence.
  New evidence: it calls `fcn.8003cf2c(0)` (loads default `sfx\global`) immediately before the
  overlay jal, and its args look like (id, volume 0xc0/0x80/0x40). Leans **sound/event**, but the
  real work is in the overlay routine — keep provisional ("overlay-dispatch wrapper").
- `fcn.8003e7c0` (called ~8×, args small-id, 0): event/SFX trigger. LOW confidence.
- `fcn.8005b70c`: pure predicate over state flags returning loop-abort go/no-go. MED.
- `fcn.80055414` / `fcn.80055538` (a0 = struct @0x800aec68): per-frame struct update (input? camera?). UNKNOWN.

## Important globals (absolute addresses)
| Addr | Size | Role (evidence) | Conf |
|---|---|---|---|
| `0x800823a0` | s16 | master game state; init 0; compared 2/4/5/6 throughout | HIGH |
| `0x8008243c` | s32 | 6-way main-shell substate index (mod 6) → jump table 0x8001b3c4; NOT confirmed level-load transition | HIGH |
| `0x800822f8` | s32 | load/transition state, values 0/1/2 | HIGH |
| `0x80082504` | s32 | current scene id (from table 0x80077fa0; ==0x11 test) | HIGH |
| `0x8008245c` | s16 | scene slot index (indexes 0x80077fa0) | MED |
| `0x80082284` | s16 | compared vs 0x8008245c (prev slot?) | MED |
| `0x800aedcc` | s32 | loop-exit code; `bgez`→exit, negative=continue | HIGH |
| `0x800aedc8/d0/d4` | s32 | companion state cluster (init at prologue) | MED |
| `0x8008225c` (gp+0x4c4) | s32 | flag 0/1 gating branches | MED |
| `0x800823e4` (gp+0x64c) | s32 | flag set 0 / set to game-state | MED |
| `0x800823ec` (gp+0x654) | s32 | set in prologue | LOW |
| `0x80082438` | s32 | frame/VSync wait counter; incremented by fcn.800390f0, polled/cleared by wait loops | HIGH |
| `0x800ab888..a` | u8[] | small BCD-style counter buffer | LOW |
| `0x800823ac` | s32 | written by fcn.8005038c (arg+0x43c) | MED |

## String anchors (VA; ownership verified where noted)
- libgpu: ResetGraph 0x8001bf58 (→fcn.8006213c), DrawSync 0x8001bff4 (→fcn.800625fc),
  SetDispMask 0x8001bfe0, ClearOTag 0x8001c05c, GPU timeout 0x8001c0ec, VSync timeout 0x8001c138.
- libcd: CdInit fail 0x8001c2c0 (→fcn.8006d61c), Cdl* cmd table 0x8001c2e0+, CD_init: 0x8001c50c.
- libspu: SsVabOpenHead/SsVabTransBody fail 0x8001b098/0x8001b0bc (→fcn.80042fa0), SPU:T/O 0x8001c1f8.
- assets: XA filename table near 0x800772f8 (`\BUGXASTR\AUDIOn.XA;1` @0x8001b0e0+),
  level→dir remap 0x8001acec, `gfx\levelNa.raw` 0x8001ae88+.

## BIOS A0/B0/C0 thunks (pattern `addiu t2,0xN0; jr t2; addiu t1,#fn`)
- 20× A0, 27× B0, 3× C0. Two clusters: crt0 block 0x8005f74c–0x8005f7dc, and libc-style
  block 0x80065eec–0x8006606c. Decode `t1` (delay slot) for the BIOS function number.
- Confirmed: 0x80065eec = A0:0x39 InitHeap. (0x80065efc t1=0x44 ≈ FlushCache; verify.)

## Unresolved questions
1. Identity of `fcn.8005038c`/`fcn.8003e7c0` (sound/event vs transition). 0x800b96e4 is overlay code.
2. Meaning of the 4-byte header word in LEVEL[M].BIN (count of what — entries/relocs/funcs?).
3. What is the pointer 0x800d5790 stored to gp+0x588 (0x80082320) by fcn.8003f5b8?
4. fmv.bin overlay (Region B) — its role/entry points vs memory.bin (same buffer, different times).
5. The Region-A entry-offset ABI: are 0x800b39a4 / 0x800b42ac etc. fixed across all LEVEL*.BIN?
2. Controller polling not yet located (no strings). Look for libpad InitPAD/StartPAD (B0 table) or
   a pad-buffer read after VSync. Candidate: `fcn.80055414/80055538` (struct @0x800aec68).
3. Per-frame render submission (OT build, DrawSync/VSync flip) — find caller chain of fcn.800625fc.
4. Decode remaining BIOS thunk function numbers.

## Next steps
- Off-image jal enumeration: DONE (single overlay region 0x800b39a0–0x800bd520; see Overlay mapping).
- fcn.8003f5b8: DONE → overlay_init_loader for MEMORY.BIN (Region B @0x800b5788). fcn.80046330 = file reader.
- fcn.8003cf2c cases: DONE → level/sfx resource loader (paths table @0x8001ad00).
- Region A: DONE → LEVEL0N\LEVEL[M].BIN @ 0x800b39a0 (header[4] + code@+4), byte-confirmed as MIPS.
- Extracted locally: LEVEL.BIN, LEVEL1.BIN (LEVEL01); L02_LEVEL.BIN, L02_LEVEL1.BIN (LEVEL02).
- 0x800b39a4 (level_overlay_init): DONE.
- 0x800b3aec (2nd verb): DONE → object spawner (3× type 0x77). 0x80042c70 = resident spawn_object.
  0x80061a48 = render-attr bit-packer (not an object builder).
- 0x800b3bb8 (+0x218): DONE → event/update verb (scripted spawn + proximity targeting). Entity tables
  recovered (0x8009c870 8×0x344; 0x80096b98 128 ptrs). fcn.80054964 = callback dispatcher.
- 0x80025084: DONE → oriented range/containment test (geometry, not collectible).
- fcn.8003f620: DONE → slot struct (pos @ +0x24/0x28/0x2c). Spawn ABI + first coord-mod documented.
- Spawn census + axis inference + mod recipe: DONE. Types 0x77/0x32/0x33 catalogued.
- fcn.8003f938: DONE → render/projection loop (not a dispatcher). 0x8009c870 = visual sprite pool.
- Collectible HUD: DONE → grain counter 0x800a65a1 (/50), FLIK 4 records (ptrs 0x800a0220/0430/0a60/
  0d78, flag +0x1b). fcn.800526f4=HUD, fcn.800260f8=digit draw, fcn.80025f54=sprite draw.
- Grain pickup handler: DONE → fcn.80054eac increments grain_count (0x800a65a1), ==50 target.
- Collectible walker + placement array: DONE → fcn.800586b0, array 0x800b0d18 (64×0x38, X/Y/Z @ +0/4/8),
  player pos 0x800a6500/04/08. FLIK marker 0x800a6597 (1..4). Coordinate mod path (live RAM) established.
- **NEXT:** (a) find the per-level DATA fill of 0x800b0d18 (which file: LEVEL.DAT/.RAW; offsets) to enable
  a FILE-based coordinate mod; trace writers of 0x800b0d18 / the loader that populates it. (b) Identify
  the record field that selects grain vs FLIK vs other (the +0x22 type or a callback-id field) to label
  individual records. (c) Optional: confirm the FLIK record+0x1b writer that syncs 0x800a6597→HUD.

- (superseded) find the FLIK pickup handler — search for a `sb`/`ori` setting FLIK record+0x1b (parallel
  to grain), likely another callback handler. (b) For COORDINATE mods of collectibles, the placement is
  data-driven: the pickup is triggered by an entity walker doing player-proximity over a per-level entity
  list, then firing the grain/FLIK callback. Locate that walker (reads player pos vs entity coords) and
  the per-level entity/placement array — likely in LEVEL.DAT/LEVEL.RAW data, not the .BIN code overlays.
  (c) Verified RAM cheat target now exists: 0x800a65a1 = grain count.
- `axt` callers of DrawSync `fcn.800625fc` and `fcn.80039970` internals → render flip / VSync.
- Locate libpad: search B0 thunks for InitPAD(0x12)/StartPAD(0x13)/_bu_init, or pad-buffer reads.


---

**Related docs:** [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md) · [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md) · [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)
