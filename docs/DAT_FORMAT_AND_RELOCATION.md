# DAT Format & Relocation — A Bug's Life (SCUS-94288)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

LEVEL `.DAT` top-level record format, the parser/relocator `fcn.8001cdc0`, the dynamic type-pointer table at `0x80096da0`, the internal baked-offset **relocation model**, why a naive byte-shift append failed, why the relocation-aware insert works, and the production tool `tools/dat_reloc.py`.

### PRODUCTION RULE (append / insertion)
- **Use `tools/dat_reloc.py` for ALL true insertion/append** into LEVEL01 `.DAT` (it fixes the 1248 internal baked file-offset fields when records shift).
- **Do NOT use naive byte-shift append** (`tools/add_level_entry.py`) on LEVEL01 — it shifts later records without updating baked offsets and the level black-screens after "Press X". See [TOOLING.md](TOOLING.md) and [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

### Verified relocation-aware true-append milestone
- Build `ABL_ADD_TOKEN0X29_NEAR64_RELOC_TEST.bin/.cue`; DAT `DAT/LEVEL01_LEVEL_ADD_TOKEN0X29_NEAR64_RELOC.DAT` (sha1 `75e68741b3b27f81767eb73d08a14890c13f374e`, 332840 B).
- New entry index **70**, kind **0x29**, coords **(4928, -50, -3655)**, bytes `40130000ceffffffb9f1ffff29000000`; type-0x3f count 70→71; 1248 baked offsets relocated +0x10.
- **In-game CONFIRMED working** (loads, plays, extra token visible/collectible, no glitch). Full detail below.

## DAT record format & grain→DAT-bytes bridge (parser transform)
### Type-0x51 grain placement back to LEVEL01 DAT bytes
Grain source mapping is now solved for the normal `fcn.80053814` spawn path.

DAT pointer proof:
- `fcn.8001cdc0` builds a resident DAT-type pointer table at `0x80096da0`.
- For non-negative DAT record type `t`, it stores the current DAT record pointer at
  `0x80096da0 + t*4`.
- The contact/grain pass reads `lw 0x80096e9c`, and `0x80096e9c = 0x80096da0 + 0x3f*4`.
- Therefore this pass reads DAT record type `0x3f`.
- `LEVEL01\LEVEL.DAT` begins with a type-`0x3f` record:
  - file `+0x0000`: DAT top-level record count = `0b 00 00 00` = 11
  - file `+0x0004`: type-`0x3f` record header = `46 00 3f 00`
  - `0x46` entries, each 0x10 bytes, starting at file `+0x0008`.

Runtime transform:
- `fcn.80053814` source pointer:
  - `src = [0x80096e9c]`
  - count = `lhu src+0`
  - entry `i` base in file = `0x0008 + i*0x10`
- Entry layout for this path:
  - `+0x00` = file X (s32)
  - `+0x04` = file Y (s32)
  - `+0x08` = file Z (s32)
  - `+0x0c` = source kind byte; `0x14` is grain source
  - `+0x0d` = runtime eligibility/status byte, initially 0 in file; `fcn.800253e8` clears/sets this
    dynamically for nearby eligible records.
- Type-`0x14` source -> grain constructor:
  - `0x80053c00`: checks `lbu entry+0x0c == 0x14`
  - `0x80053c20`: `a3 = 0x51`
  - `0x80053c24/28/2c`: reads X/Y/Z from entry `+0/+4/+8`
  - `0x80053c38/3c/44`: shifts X/Y/Z left by 5
  - `0x80053c40`: `jal fcn.80059e44`
  - `fcn.80059e44` writes runtime X/Y/Z to `0x800b0d18 + slot*0x38 + 0/4/8`.
- Runtime slot number is allocator-state dependent: `fcn.80059e44` pre-increments cursor
  `0x8008234c`, wraps at 0x40, then returns `0x800b0d18 + slot*0x38`. If the cursor is 0 immediately
  before this call, the returned record is slot 1 at `0x800b0d50`.

LEVEL01 example grain record:
- Source file: `LEVEL01\LEVEL.DAT`
- Source record type: DAT type `0x3f`
- Entry index: `0`
- Entry file offset: `0x0008`
- Raw entry bytes:
  `b2 de ff ff 60 f2 ff ff c0 11 00 00 14 00 00 00`
- Decoded file coordinates:
  - X = `0xffffdeb2` = -8526
  - Y = `0xfffff260` = -3488
  - Z = `0x000011c0` = 4544
  - source kind = `0x14`
- Constructor call:
  - `fcn.80053814 @ 0x80053c40 -> fcn.80059e44`
  - constructor type ID = `0x51`
  - stack arg = 3
- Runtime coordinates written by constructor:
  - X = -8526 << 5 = -272832
  - Y = -3488 << 5 = -111616
  - Z = 4544 << 5 = 145408
- Runtime record address:
  - `0x800b0d18 + slot*0x38`; slot is chosen by cursor `0x8008234c` at the constructor call.
  - Example if cursor was 0 immediately before the call: slot 1, record `0x800b0d50`,
    X/Y/Z at `0x800b0d50/0x800b0d54/0x800b0d58`.


### ✅ ROOT CAUSE FOUND — append breaks DAT-internal baked file-offset relocations (post-0x3f shift)
**Reclassified: the append failure is a STRUCTURAL post-0x3f shift failure — confirmed by static tracing.**
The LEVEL01 DAT contains internal cross-reference tables whose entries bake **absolute file offsets** into
the data that lives AFTER the type-0x3f record. The parser `fcn.8001cdc0` relocates them at load time by
`runtime_ptr = DATbase + baked_file_offset` (`DATbase = [0x80082498]`, gp+0x700). A naive +0x10 append
shifts the *target data* by +0x10 but leaves the *baked offsets* unchanged, so every relocated pointer
lands **0x10 short** of its real target. There is NO 70-entry cap and NO hardcoded-offset code constant.

Top-level DAT record map (LEVEL01, pristine), all records after rec0 shift +0x10 on append:
| rec | file off | type | count | entry size | note |
|----:|---------:|------|------:|-----------:|------|
| 0 | `0x004` | `0x3f` | 70 | `0x10` | pickups/placements (the appended record) — does NOT shift |
| 1 | `0x468` | `0x01` | 104 | `0xc` | shifts -> `0x478` (VA `0x80160c60` -> `0x80160c70`) |
| 2 | `0x94c` | `0x0b` | 16 | `0xc` | shifts |
| 3 | `0xa10` | `0x0c` | 16 | `0xc` | shifts |
| 4 | `0xad4` | `0x0d` | 16 | `0xc` | shifts |
| 5 | `0xb98` | `-2` | 48 | ~6 | shifts |
| 6 | `0xcc8` | `-3` | 88 | ~6 | shifts |
| 7 | `0xee8` | `-4` | 64 | ~6 | shifts |
| 8 | `0x1078`| `-5` | 65 | ~6 | shifts |
| 9 | `0x1210`| `-6` | 56 | ~6 | shifts |
| 10| `0x1370`| `-7` | 64 | ~~bulk geometry blob to EOF~~ → fixed `0x190` packed record, **ends `0x1500`** (see correction) | shifts |

> **CORRECTION (Geometry G1, 2026-06-13):** the rec10 note "bulk geometry blob to EOF" is
> **SUPERSEDED**. By the confirmed parser size rule, rec10 (`-7`, count 64) is a fixed
> `0x190`-byte packed record ending at `0x1500`. The top-level records end at `0x1500`; the
> post-record word there is `0`, so the trailing relocation block begins at `0x1504`. The
> geometry-heavy **data** is *not* inside rec10 — it lives after the trailing relocation tables in
> `[0x45f0, EOF=0x51418)` and is reached only via the baked offsets relocated by `fcn.8001cdc0`
> (all 1248 LEVEL01 relocation targets land in that region; 0 land in the records or trailing
> tables). Full inventory: [src_re_geometry/level01_dat_geometry_inventory.md](../src_re_geometry/level01_dat_geometry_inventory.md),
> plan [docs/GEOMETRY_RE_PLAN.md](GEOMETRY_RE_PLAN.md).

- Parser stores a dynamic type-pointer table at `0x80096da0 + type*4` (`0x80096e9c` for type 0x3f). This
  table is REBUILT from the walk, so it is correct after the shift — consumers using it (e.g. the type-0x3f
  construct pass `fcn.80053814` reading `0x80096e9c`) are SAFE. The problem is the OTHER mechanism below.
- After the record walk, the parser locates a trailing structure (file `0x1504` pristine; correctly +0x10
  to `0x1514` after append, found dynamically), pointer cached at `gp+0x714` (`0x800824ac`) and `gp+0x5a0`
  (`0x800822e8`). It then runs two relocation passes over stride-0x14 entries:
  - **Pass 1** (`0x8001cf54`..`0x8001d1d4`): `s0 = DATbase + [s3+2]` (baked mesh/object file offset),
    written back; then follows s0 and relocates `[s0+0x14]` (and flag-gated `[s0+0x18/0x1c/0x20]`); builds
    runtime stride-0x20 records (coords scaled by `[s0+0x12]`, `sra 0xc`) into the heap buffer at
    `DATbase + arg2`. This is the level's static **geometry/object-instance + collision mesh** build.
  - **Pass 2** (`0x8001d1d8`..): same idea, relocates `[a0+4]` by DATbase and dereferences `[v0+0xe]`/
    `[v0+0x10]`, populating a resident table near `0x80091216`.
- EVIDENCE (tools/-style replication of the walk over `DAT/LEVEL01_LEVEL.DAT`):
  - trailing block @ `0x1504`; pass-1 has 41+ stride-0x14 entries; the FIRST baked offset `[s3+2]` is
    `0x4680`, then `0x4698, 0x46b0, 0x4788, 0x47a0, 0x4a58, …, 0x7c28, …` — **every one is >= 0x468**, i.e.
    all point into the shifted region (into the geometry blob, top-level rec10). `[target+0x14]` fields are
    also `>= 0x468` (`0xb32c, 0xc6c8, 0xd768, …`).
  - In the appended DAT the trailing block correctly moved to `0x1514`, but the baked offset fields are
    **byte-identical** (`0x4680`, `0x4698`, …) -> after relocation they are 0x10 short of the moved data.
- Why it passes parse but dies after Press X: PS1 has no MMU, so the 0x10-stale reads during the load-time
  relocation don't fault — they just read wrong bytes and bake wrong/garbage values (coords and wild
  relocated sub-pointers) into the runtime geometry/collision/object structures. The corruption is only
  FATAL when live gameplay (post-Press-X) walks that geometry/collision/render data. The loading-screen
  parser path therefore "succeeds" and reaches Press X.
- Why retail levels can have >70 type-0x3f entries: each retail DAT is authored with its OWN internally
  consistent baked offsets. There is no engine cap; our append merely broke this file's internal
  consistency. Confirmed: no code immediate `0x468`/`0x478`/`0x0c60`/`0x0c70` exists in SCUS_942.88,
  `OVL/LEVEL01_LEVEL.BIN`, or `OVL/LEVEL01_LEVEL1.BIN` (searched addiu/ori/lui/lw/sw/lh/sh imm fields) ->
  the stale-ness is purely DATA-driven (`DATbase + stored_offset`), never a hardcoded code offset.
- Post-Press-X path (for reference): `0x80052468 jal 0x80045a60` (Press-X/loading wait) -> `0x80052474`
  restores scene id `[0x80082504]=fp` -> gameplay state machine `fcn.8004ecd4` -> `0x8004f028 jal
  fcn.80053814` (type-0x3f construct, reads UNSHIFTED `0x80096e9c` = SAFE) -> `0x8004f038 jal fcn.80054964`
  (callback dispatcher). The crash is NOT in the 0x3f pass; it is in the consumer of the corrupted
  geometry/collision/object structure built by the parser passes above (cached at `gp+0x714`/`gp+0x5a0`
  and in the `DATbase+arg2` heap mesh).
- IMPLICATION for a correct net-new append: a valid insert must be **relocation-aware** — after inserting a
  0x10 entry at `0x468`, add +0x10 to EVERY baked file-offset field that references data at original
  offset >= 0x468. That means fixing: the type-0x3f count; the trailing-structure pass-1 `[s3+2]` fields
  (41+) and their `[target+0x14]` (+flag-gated `+0x18/+0x1c/+0x20`) fields; and the pass-2 `[a0+4]` fields.
  A plain byte-shift append (current `tools/add_level_entry.py`) can NEVER load past Press X. Building this
  fix-up requires fully enumerating all relocation sites the parser visits.
- Tool added this session: `tools/build_markers_54_55_57.py` (prior); for this analysis the walk was
  replicated inline. NEXT diagnostic (deterministic): see recommendation below.


### ✅ RELOCATION-AWARE APPEND TOOL BUILT — full relocation model + first reloc-aware true-append image
New tool: **`tools/dat_reloc.py`** — reproduces the EXACT relocation walk of `fcn.8001cdc0` and applies a
relocation-aware type-0x3f insert. Use `--scan` to list every baked offset; `--clone-entry N [--dx/--dy/--dz]`
or `--entry-bytes <hex>` + `--out` to build a reloc-aware append. Replaces the naive `tools/add_level_entry.py`
(byte-shift append, which can never load past Press X).

**Complete relocation model of `fcn.8001cdc0` (every `field += DATbase` write-back):**
- Top-level record walk builds the dynamic type table `0x80096da0+type*4` (rebuilt correctly; not patched).
- After records, trailing block found dynamically at file `0x1504` (`gp+0x714`=`0x800824ac`). Then 3 passes:
- **PASS 1** — stride-0x14 table, `s3 = trail+0xe`, while `lh[s3] >= 0`. Flags `=lhu[s3]`: bit3 (0x8)
  selects path, bit5 (0x20) gates an extra field (NEVER set in LEVEL01 → no [s0+0x18]/[s0+0x20]).
  - `[s3+2]` (always) → s0; if `!(flags&8)`: `[s0+0x14]`; else `[s0+0x1c]`.  (coords `[s0+0x12/0x16]` are
    NOT relocated; `fcn.80017b98(s0+0xc, out)` is GTE rotation-matrix setup via sin/cos table 0x80074970,
    relocates nothing.) **LEVEL01: 484 entries → 968 fields** (484 `[s3+2]` + 174 `[s0+0x14]` + 310 `[s0+0x1c]`).
- **PASS 2** — stride-4 pointer array right after pass1 (`p2 = trail + 0x14*(N+1)` = `0x3ae8`); `n=lw[p2]`;
  relocate `[p2+4+4i]` for `i=0..n` if nonzero. **LEVEL01: `[p2]=-1` → pass2 EMPTY (0 fields).**
- **PASS 3** — stride-0x14 table at `p3 = p2 + (n<<2) + 8` (32-bit) = `0x3aec`; `s3=p3+0xe`, while `lh[s3]>=0`.
  `[s3+2]` (always) → s0; if `!(flags&8)`: `[s0+0x14]`; else `[s0+0x1c]`. **LEVEL01: 140 entries → 280 fields**
  (140 `[s3+2]` + 85 `[s0+0x14]` + 55 `[s0+0x1c]`).
- **TOTAL LEVEL01 = 1248 baked-offset fields.** All values land in `[0x468, filesize)`; no nulls, no
  heap-relative negatives, no duplicate field offsets. All field LOCATIONS are ≥ 0x468 (in the trailing
  structures/geometry). So a correct +0x10 insert at 0x468 = bump count + add +0x10 to all 1248 field
  VALUES at their +0x10-shifted LOCATIONS. (No pass-2 / no gate-bit fields for this level.)

**First relocation-aware true append (BUILT, awaiting in-game result):**
- Tool: `python3 tools/dat_reloc.py DAT/LEVEL01_LEVEL.DAT --entry-bytes 40130000ceffffffb9f1ffff29000000 --out DAT/LEVEL01_LEVEL_ADD_TOKEN0X29_NEAR64_RELOC.DAT`
- Input: `DAT/LEVEL01_LEVEL.DAT` (pristine `b376cb50…`, 332824 B). Output:
  `DAT/LEVEL01_LEVEL_ADD_TOKEN0X29_NEAR64_RELOC.DAT` (sha1 `75e68741b3b27f81767eb73d08a14890c13f374e`, 332840 B).
- New entry 70 @ `0x468` = `40130000ceffffffb9f1ffff29000000` (clone of entry 64 with X+512: XYZ `4928,-50,-3655`,
  kind 0x29). Type-0x3f count 70→71.
- Image: `ABL_ADD_TOKEN0X29_NEAR64_RELOC_TEST.bin/.cue` (738285744 B).
- VERIFICATION (all PASS): type-0x3f entries 0..69 byte-identical; new entry 70 == required bytes; size
  +0x10; **1248/1248 relocation fields bumped**, each `old>=0x468`, `new=old+0x10`, in-bounds, and the 16-byte
  window at the new target == the window at the old target in pristine (same logical shifted data); diffs vs a
  naive byte-shift are a strict SUBSET of the 1248 four-byte fields (1370 bytes, **zero** diffs outside them);
  bytes before `0x468` identical except the count halfword; re-scanning the patched file finds 1248 sites with
  trail/p2/p3 each +0x10 and every field+value == old+0x10 (internally self-consistent). Embedded
  `LEVEL01/LEVEL.DAT` (LBA 2906, sector-aware) sha1 == `75e68741…` == patched DAT (count 71, entry70 correct,
  reloc field @`0x1524`=`90460000`). Original DAT and original image pristine (`b376cb50…`, `.bin` mtime Apr 15
  2012); `REBUILD/files/LEVEL01/LEVEL.DAT` restored after build.
- IN-GAME INTERPRETATION:
  - Loads + extra orange token appears/collects near entry 64 → **relocation-aware true append WORKS**;
    net-new pickup injection is unlocked (this is the production route, replacing fixed-count sacrifice).
  - Reaches Press X then black-screens → relocation set is still incomplete (a secondary structure or a
    relocation site not modeled). Re-trace `fcn.8001cdc0` for any missed `+=DATbase`, and check loaders other
    than `fcn.8001cdc0` that might consume DAT offsets.
  - Loads but geometry/collision glitches → some fields mis-patched (wrong site classification); compare the
    in-RAM relocated pointers good-vs-bad at a pass-1 entry.
  - Loads but token missing → append structure is fixed; token CONSTRUCTION path (type-0x3f construct
    `fcn.80053814`, the new 71st entry) needs separate inspection — not a relocation problem.

## ✅ RELOCATION-AWARE TRUE APPEND CONFIRMED IN-GAME
Milestone: net-new type-0x3f entry injection into LEVEL01 now loads and plays normally. This closes the
append investigation that began with the naive-append black screen.

1. **Build:** `ABL_ADD_TOKEN0X29_NEAR64_RELOC_TEST.bin/.cue`
   - DAT: `DAT/LEVEL01_LEVEL_ADD_TOKEN0X29_NEAR64_RELOC.DAT` (sha1 `75e68741b3b27f81767eb73d08a14890c13f374e`, 332840 B)
   - Tool: `tools/dat_reloc.py` (relocation-aware insert).
2. **Entry added (real net-new, not a repurpose):**
   - new entry index: `70`; type-0x3f count `70 -> 71`
   - kind: `0x29` (orange seed-power token)
   - coords: `(4928, -50, -3655)` (clone of entry 64 with X +512)
   - bytes: `40130000ceffffffb9f1ffff29000000` @ file `0x468`
   - 1248 internal baked file-offset fields relocated `+0x10` (968 pass-1 + 280 pass-3; pass-2 empty).
3. **In-game result (user):**
   - Loaded to Press X: yes; gameplay visible after Press X: yes; black screen/audio-only: **no**.
   - Original entry-64 orange token present: yes; extra orange token near entry 64 present: yes;
     extra token collectible: yes; orange meter changes: yes.
   - Geometry/collision weirdness: no; crash/glitch: no; FLIK/checkpoint/berries normal: yes.
4. **Root-cause conclusion (CONFIRMED):** the earlier black screen was **stale internal DAT relocation
   offsets**, NOT seed-token count or pickup/contact/render-pool logic. A naive +0x10 append shifted later
   DAT data without updating the baked file offsets that `fcn.8001cdc0` relocates as `DATbase + offset`
   (passes 1/3 over the trailing geometry/object tables). Fixing those 1248 offsets makes the level load
   and play normally — so the structural relocation model is correct and complete for LEVEL01.
5. **Production rules:**
   - **True net-new token injection is possible.** Use **`tools/dat_reloc.py`** for ALL append/insertion.
   - **Do NOT use naive byte-shift append tools** (`tools/add_level_entry.py`) for LEVEL01 — they cannot
     load past Press X.
   - **Fixed-count marker sacrifice is OBSOLETE as a production route** (diagnostic only).
   - **Entries 54..57 / DAT kinds `0x20..0x24` are special berry/power-up records** — do not sacrifice them.
6. **Next recommended experiments:**
   - Add additional tokens via `tools/dat_reloc.py` (more `0x29` entries; confirm count scales).
   - Test net-new append of `0x2a` (blue) and `0x2b` (green) tokens — verify each updates its own seed meter
     (counters `0x800a6599` / `0x800a659a`, objects `0x17` / `0x19`).
   - Test inserting MORE THAN ONE entry at once (multi-entry append; relocation delta becomes `+0x10*k`).
   - If/when failures appear at high counts, document the **max safe pickup/contact count separately** — the
     runtime contact array `0x800b0d18` is 64 records (constructor `fcn.80059e44` cursor wraps at 0x40), so
     total active visible pickups (grain + FLIK + tokens + …) is the likely ceiling, independent of the now-
     solved relocation issue.


---

**Related docs:** [COORDINATE_MODDING.md](COORDINATE_MODDING.md) · [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md) · [TOOLING.md](TOOLING.md) · [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)
