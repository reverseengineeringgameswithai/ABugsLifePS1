# G21 — `fcn.80046330` file-read caller map + corrected sidecar-loader analysis

[← docs/GEOMETRY_RE_PLAN.md](../docs/GEOMETRY_RE_PLAN.md) · [hub: geometry_notes.md](geometry_notes.md) ·
[← G20 sidecar loader trace](geometry_g20_sidecar_loader_trace.md) ·
[← G19 resource source](geometry_g19_floor_resource_source.md) ·
[← G3 runtime buffers](geometry_runtime_buffers.c)

Status: **NEGATIVE RUNTIME RESULT + FULL STATIC CALLER MAP + ONE RUNBOOK (2026-06-14).** Read-only
`SCUS_942.88` disasm (text carved at file `0x800`, VA `0x80010000`) + read-only file inspection. **No patch,
no build.** No collision/pathing claims — visual ≠ collision.

> **Headline:** the G20-proposed terrain `.ALL` breakpoints `0x8002ffe4` / `0x80030dc0` **did not fire** during
> LEVEL01 load — so G20's "prime confirmed target" was **wrong/unconfirmed** and is corrected here. Two
> structural reasons the operator's *call-site* breakpoints keep missing the floor load: (a) the terrain
> orchestrator `fcn.8005d654` has a **skip-if-already-loaded** branch (`bnez v0,0x8005d794` at `0x8005d76c`),
> so a **cached** terrain never re-hits the file-read; (b) the high-heap loader `fcn.8003a318` (file-read
> `0x8003a388`) is reached **indirectly** (no direct `jal`), so no call-site BP catches it. **Fix: watch the
> single callee entry `fcn.80046330`** — every one of the 14 file-read call sites funnels through it, so one
> breakpoint logs every file load (name + destination) regardless of caller, caching, or load phase.

## 0. ✅ G22 CONFIRMATION (2026-06-14) — the runbook worked; PRIME suspect was right

`EXEC 0x80046330` was run. **Hit #4** (`ra=0x8003a390`, inside the indirect high-heap loader `fcn.8003a318`
named the **PRIME** suspect in §5) loaded a file to dest **`0x80115aac`**, size `0xb6be4`, range
`[0x80115aac, 0x801cc690)` — which **brackets the floor `0x801bdc58`** at offset `0xa81ac`. The dest-size
`0x801cc390 − 0x80115aac = 0xb68e4` = **LEVEL.RAW's exact size**, so **the source file is LEVEL.RAW** — exactly
the §4/§5 high-heap prediction. The callee-entry watch caught the load that all the call-site BPs (and the
caching/indirect structure) had hidden. **But** `LEVEL.RAW[0xa81ac]` is not a verbatim payload (the floor is
runtime-converted from LEVEL.RAW). Full record:
[geometry_g22_high_heap_floor_source.md](geometry_g22_high_heap_floor_source.md).

## 1. Negative runtime result (operator, 2026-06-14)

| breakpoint | hits during LEVEL01 load | meaning |
|------------|--------------------------|---------|
| `EXEC 0x8002ffe4` (terrain `.all` read in `fcn.8002ffa8`) | **0** | terrain `.all` loader not exercised in this state |
| `EXEC 0x80030dc0` (terrain `.all` read in `fcn.80030d64`) | **0** | second `.all` loader not exercised either |

**Recorded conclusion:** the proposed `.ALL` loader path is **NOT confirmed** for this LEVEL01 load. Do not
retry these two. **H2 (terrain `.all` → floor) is no longer "leading" — it is open/unconfirmed.** Two
non-exclusive explanations (both CONFIRMED in code): the orchestrator **skips the file-read when the terrain
is already resident** (`fcn.8005d654` `0x8005d76c bnez v0,0x8005d794` → calls the processor `fcn.8002fce8`
directly, no file load), and/or the terrain loads in a **different phase** than the "Loading Level…" window.
Watching a file-read **call site** is therefore the wrong instrument; watch the **callee entry** (§6).

## 2. Full `fcn.80046330` caller map (14 sites → 11 functions; CONFIRMED disasm)

`fcn.80046330(a0 = bare filename string, a1 = destination base) → v0 = bytes read` (CONFIRMED: at entry
`s0=a0`, `fp=a1`; it then builds a CD/level-dir path from `a0` and loads the file to `a1`).

| # | call site | containing fn | filename / how built | dest `a1` | subsystem (role) | fired in operator window? |
|--:|-----------|---------------|----------------------|-----------|------------------|---------------------------|
| 1 | `0x8003d550` | `fcn.8003cf2c` | `level<N>.<ext>` (via `fcn.80046538` + level name table `0x8001ae54/60`) | **DATbase `[0x80082498]`** | **LEVEL resource dispatcher** (level*.dat / .raw / .bin) | **YES — `level.dat` ×1, `0x51418`** |
| 2 | `0x8003d310` | `fcn.8003cf2c` | `bits\memory.bin` (`0x8001adfc`) | `0x800b5788` | memory-layout descriptor | not observed |
| 3 | `0x8002ffe4` | `fcn.8002ffa8` | `<pfx>.all` (ext `0x80082128`) | `[s0]` heap | terrain `.all` (via orch `fcn.8005d654`) | **NO (tested)** |
| 4 | `0x80030dc0` | `fcn.80030d64` | `<pfx>.all` (ext `0x80082130`) | `[s0]` heap | terrain `.all` variant (caller `0x800314c4`) | **NO (tested)** |
| 5 | `0x800310c8` | `fcn.80030d64` | name via ptr-table `0x8001aaec` | `[s0]` | same fn (resource by id) | not observed |
| 6 | `0x8003a388` | `fcn.8003a318` | `a0` from **indirect** caller (no direct `jal`) | **`0x801cc390 − align(size)`** (top-down heap) | **high-heap streamed loader — PRIME** | not observed |
| 7 | `0x8003d638` | `fcn.8003d620` | fixed | `0x800b39a0` | small fixed-buffer load (caller `0x8003d484`) | not observed |
| 8 | `0x8003e7fc` | `fcn.8003e7c0` | `fmv\fmv.bin` (`0x8001ae6c`) | `0x800b5788` | FMV (9 callers) | not observed |
| 9 | `0x8003f578` | `fcn.8003f504` | `fmv\fmv.bin` | `0x800b5788` | FMV (caller `0x8004fd90`) | not observed |
| 10 | `0x8003f5d0` | `fcn.8003f5b8` | `bits\memory.bin` | `0x800b5788` | memory.bin (caller `0x8004fafc`) | not observed |
| 11 | `0x80042f20` | `fcn.80042e94` | fixed | `0x800972a8` | audio | not observed |
| 12 | `0x80042f58` | `fcn.80042e94` | `<pfx>.vb` (ext `0x800821b0`) | `s0+0x800b5790` | audio VAB body | not observed |
| 13 | `0x80055d98` | `fcn.80055d4c` | fixed | `0x80095398` | fixed-buffer load | not observed |
| 14 | `0x8005d6ec` | `fcn.8005d654` | `<pfx>.anm` (ext `0x800821f8`) | `[s2]` | animation (terrain orch) | not observed |

**Already-confirmed types:** LEVEL.DAT parse path (#1, fired); memory.bin (#2/#10); FMV (#8/#9); audio
(#11/#12); ANM (#14); terrain `.all` (#3/#4, **did not fire**); high-heap streamed load (#6). "Not observed"
= the operator never armed that PC (it may still fire); only #1 (one hit) and #3/#4 (zero hits) have runtime
data.

## 3. The universal file loader `fcn.80046330` (CONFIRMED)
`s0 = a0` (filename), `fp = a1` (dest). It prepends the current CD/level directory (path built via
`fcn.8005f76c` + `fcn.8005f74c`, suffix table `0x800821d0` = `\`,`;1`,`level0`,`level`) and reads the file to
`a1`, returning bytes read in `v0`. **Every named-file load in the game passes through this entry** — making
it the correct single observation point. (No `lui *,0x0c83` exists in the text, so the `.RAW` magic
`0x0c830000` is **not** compared by an in-code immediate — `.RAW` is loaded as data and decompressed/blitted
elsewhere, or streamed; not a blocker for watching `fcn.80046330`.)

## 4. Which caller could load each sidecar (mapping)

| sidecar file | size | loader caller | notes |
|--------------|-----:|---------------|-------|
| `LEVEL.DAT` | `0x51418` | **#1** `fcn.8003cf2c`/`0x8003d550` | CONFIRMED (fired) |
| `LEVEL1.DAT` | `0x1a568` | **#1** (level table → `level1.dat`) | did **not** fire in window (other area/state, or different phase) |
| `LEVEL2.DAT` | `0x40784` | **#1** (`level2.dat`) | did not fire in window |
| `LEVEL.RAW` | `0xb68e4` | **#1** (`level.raw`) or **#6** high-heap | too big to fit top-down at `0x801cc390` above the DAT (would underflow `0x801607f8`) |
| `LEVEL1.RAW` | `0x84210` | **#1** or **#6** | also underflows the DAT if top-down |
| `TERRAIN.ALL` | `0x39d8c` | **#3/#4** terrain `.all`, or **#6** | `.all` sites did not fire |
| `TERR1.ALL` | `0xf078` | **#3/#4** or **#6** | top-down `0x801cc390 − 0xf078 = 0x801bd318` → would **contain** the floor `0x801bdc58` (offset `0x940`) |
| `LEVEL.BIN` | `0x690` | **#1** (`level.bin`) | overlay code |
| `LEVEL1.BIN` | `0xa8c` | **#1** (`level1.bin`) | overlay code |

**Key point:** all `level*.{dat,raw,bin}` funnel through **#1** (`0x8003d550`), which fired **once** (LEVEL.DAT)
— so during the tested window none of LEVEL1/2.DAT, LEVEL.RAW, LEVEL.BIN loaded via the dispatcher. They are
either cached from boot, loaded in another phase, or loaded via the **indirect high-heap loader #6**.

## 5. The high-heap loader `fcn.8003a318` (PRIME suspect, CONFIRMED disasm)
- `fcn.8003a318(a0 = filename)`: calls `fcn.8004589c(a0)` (file size), aligns to 4, then
  `s0 = 0x801cc390 − align(size)` and `jal fcn.80046330(a0 = filename, a1 = s0)` — a **top-down heap
  allocation** under the fixed ceiling `0x801cc390` (= `0x801d0000 − 0x3c70`).
- **It is reached indirectly** (no direct `jal fcn.8003a318` anywhere; not in a `u32` pointer table found by
  value), so the operator's call-site breakpoints could never have caught it. Its file-read `0x8003a388` was
  never armed.
- Its target region can **contain** the floor `0x801bdc58` for any file of size `≥ 0xe738` that still fits
  above the DAT: e.g. `TERR1.ALL` (`0xf078`) → region `[0x801bd318, 0x801cc390)` brackets `0x801bdc58`;
  `LEVEL1.DAT` (`0x1a568`) → `[0x801b1e28, …)`. (The exact byte at the computed offset is not a clean payload
  in the raw files — consistent with the floor being **generated**, not a verbatim offset; static cannot pin
  it, the runbook can.) This is the single best static suspect, and it is exactly the kind of load the
  callee-entry watch (§6) catches and the call-site watches miss.

## 6. Recommended next runbook — ONE breakpoint at the callee entry (broad, deterministic, manual)

```
Breakpoint address:
  EXEC 0x80046330        (entry of the universal file loader fcn.80046330)
  (optionally also arm EXEC 0x8003d550 to flag every LEVEL resource-dispatcher load)

Why this caller is relevant:
  Every one of the 14 file-read call sites funnels into fcn.80046330. One breakpoint at its ENTRY logs
  EVERY file load during LEVEL01 — including the indirect high-heap loader fcn.8003a318 (#6) that no
  call-site breakpoint can reach, and any load the skip-if-cached terrain path would hide. This is strictly
  broader than 0x8002ffe4/0x80030dc0 yet is a single, manual breakpoint.

Expected register values to record (at each hit):
  a0  -> read the C-string at a0 = the bare filename (e.g. "level.dat", "terr1.all", "fmv\fmv.bin")
  a1  -> destination base (also copied to fp)
  ra  -> caller return address -> identify the subsystem via the §2 map
         (0x8003d554=LEVEL dispatcher, 0x8003a38c=high-heap loader #6, 0x8002ffe8=terrain .all,
          0x8003e800/0x8003f57c=FMV, 0x8003d314/0x8003f5d4=memory.bin, 0x80042f5c=audio, 0x8005d6f0=anm)
  v0  -> AFTER return = bytes read (size). To capture: set a one-shot EXEC at the value in ra, F5, read v0.
  Log every hit through load -> gameplay (after "Press X to start").

How to tell whether it owns / feeds 0x801bdc58:
  For each load compute  a1 <= 0x801bdc58 < a1 + size.
    - TRUE  -> that file's loaded region CONTAINS the floor; floor source = that filename,
               offset-in-file = 0x801bdc58 - a1 (NOT a LEVEL.DAT offset).
    - For all loads FALSE -> nothing loaded during the window brackets 0x801bdc58, so the floor is
               GENERATED from cached/boot-resident data. Escalate (next session, not now):
               (a) arm EXEC 0x80046330 from the TITLE screen / first-ever level entry to catch boot-cached
                   terrain, and/or
               (b) watch the terrain PROCESSOR EXEC 0x8002fce8 (runs even when the file-read is skipped),
                   reading its source pointer (a1=cursor) and the record base it writes (0x80098a8a).
```

**Why not the alternatives:** retrying `0x8002ffe4`/`0x80030dc0` repeats a zero-hit watch (skip-if-cached);
a broad RAM dump is disallowed and unnecessary; stepping into the LEVEL.DAT parser is circular. The
callee-entry watch is the minimal instrument that answers "what loads, where" without guessing call sites.

## 7. Corrections to earlier docs (per task #4)
- **G20** labelled the terrain `.all` loader (`0x8002ffe4`/`0x80030dc0`) the **"prime non-circular target"**
  and made **H2 "leading."** The runtime result **refutes that** as a *confirmed* path: neither fired.
  Corrected status: terrain `.all` is a **candidate that did not fire** (skip-if-cached and/or wrong phase);
  H2 is **open/unconfirmed**, not leading. The G20 *map* (loader/processor/orchestrator addresses) stays
  valid; only the "prime/confirmed" framing and the file-read-site runbook are downgraded in favour of the
  callee-entry watch here.
- **New leading suspect:** the indirect high-heap loader **`fcn.8003a318`** (`0x801cc390 − size`), whose
  region can contain `0x801bdc58` and which call-site BPs cannot catch.

## 8. Guardrails / reproduce
No patch, no build. No DAT/CUE/BIN/RAM/save-state committed. Do not treat offsets past a file's EOF as
offsets into it; any floor offset found is relative to **that file's** load base, not LEVEL.DAT. Do not patch
runtime-buffer addresses. Collision/pathing **UNKNOWN** — visual ≠ collision. Do not retry
`0x8002ffe4`/`0x80030dc0` as primary, do not re-enter the LEVEL.DAT parser, do not F5-grind `0x800108b4`.

```bash
python3 -c "open('/tmp/abltext.bin','wb').write(open('SCUS_942.88','rb').read()[0x800:0x73000])"
# 14 callers of the file loader: jal fcn.80046330 = bytes cc 18 01 0c
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x80046330 -c 'pd 12' /tmp/abltext.bin   # loader entry: a0=name,a1=dest
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8003a318 -c 'pd 28' /tmp/abltext.bin   # high-heap loader (0x801cc390-size)
r2 -q -a mips -b 32 -e scr.color=0 -m 0x80010000 -s 0x8005d764 -c 'pd 8'  /tmp/abltext.bin   # skip-if-cached branch
```
