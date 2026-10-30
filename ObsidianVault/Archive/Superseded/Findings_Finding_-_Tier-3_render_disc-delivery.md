---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Tier-3 render disc-delivery.md
aliases:
  - "Finding - Tier-3 render disc-delivery"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Tier-3 render disc-delivery.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Tier-3_render_disc-delivery.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
tags: [finding, tier3, disc, loader, level-raw]
date: 2026-06-26
status: resolved
---

# Finding — Tier-3 render needs its own disc file (LEVEL.DAT/RAW are LBA-full)

Investigation of **how to deliver the Tier-3 OT-insert render cave (~2784 B of code) onto a cold-boot disc**, after the boot + level-load were fixed and custom **collision** works cold-booted (blob in the LEVEL.DAT last-sector slack). See [[Tier 3 - Custom Level Engine]].

## The constraint: no spare on-disc room next to the level files

`REBUILD/abl.xml` pins every file to a fixed `offs=` LBA, and the LEVEL01 files **fill their slots**:

| file | LBA (slot) | actual size | slack in slot |
|---|---|---|---|
| LEVEL.DAT | 2906 (163 sectors) | 332824 B = 162.51 sec | ~1000 B (last sector) |
| LEVEL.RAW | 3069 (366 sectors) | 747748 B = 365.11 sec | ~1820 B (last sector) |
| LEVEL1.BIN | 3435 | — | — |

- **The 400 B level BLOB fits** in LEVEL.DAT's ~1000 B last-sector slack → DAT stays 163 sectors, LEVEL.RAW @3069 untouched. (This is the current working collision disc.)
- **The 2784 B render does NOT fit** anywhere adjacent: appending to LEVEL.DAT overruns LEVEL.RAW (+2 sectors), and LEVEL.RAW itself only has ~1820 B free before LEVEL1.BIN. **LEVEL.RAW is read by hardcoded LBA 3069**, so it cannot be moved (a manual `offs` bump to 3071 hung the level on "loading…").
- **No in-image home either**: the only EXE zero-run ≥2784 B is `0x8007fd58..0x80080dc0` (4200 B) — but that is a **known live runtime buffer** (the grain-HUD work proved code there gets corrupted → crash). Other runs (`0x800810bc` 1032 B used by the collision cave; `0x8007f174` 512 B used by the loader stub) are too small.

⇒ **The render must ride in its OWN new disc file** at an unused LBA (leaves every existing file's hardcoded LBA intact), loaded into RAM at gameplay.

## The reusable loader: `FUNC_80046330(name, dest)`

The game's generic "load a named file → RAM" routine (RE'd in `src_re/file_loader_80046330.c`):

- Chain: **`FUNC_8003CF2C` (resource dispatcher) → `FUNC_80046330` (file loader) → `FUNC_80045FC4` (lookup)**; LEVEL.RAW's `FUNC_8003A318` is a verified caller (`jal 0x80046330` @0x8003a388, dest = high-heap `0x801D0000-0x3C70-size`).
- `FUNC_80046330`: `a0` = **filename string** (uppercased in place — ISO9660 norm at 0x8004639c), `a1` = **dest**. Resolves the name via `FUNC_80045FC4` → **`CdSearchFile` (`0x8006f690`)** → `{LBA, size}`, then libcd reads the **whole file (directory-entry size, not a header field)** to `dest`. **No decompression** — a raw file loads verbatim.

### Filename format (3b.R step 1 — CONFIRMED LIVE 2026-06-26)
Broke at `FUNC_80046330` and read `a0` on real loads — the names are **full relative paths `dir\file.ext`**: lowercase, **backslash** separator, **no leading slash, no `;1` version**. Observed: `fmv\fmv.bin`, `sfx\global.vh`, `sfx\global.vb`, `bits\memory.bin`, **`level00\level3.raw`** (level files are `levelNN\<name>.raw`). ⇒ the custom render file goes in `LEVEL01/` and loads with **`FUNC_80046330("level01\\tier3.rnd", 0x801E0000)`** (the loader uppercases it to `LEVEL01\TIER3.RND` for CdSearchFile). NOTE: getRegisters keys are **lowercase** (`a0`, not `A0`).

## IMPLEMENTED + VERIFIED (2026-06-26)
Working on a cold-booted disc (`build/ABL_tier3_render.cue`): `COPIED=1`, TIER3.RND byte-matches at
0x801E0000, render hook fires (SENT++), custom platforms draw in-world, no save state. Key gotchas hit:
- **Byte-packed disc:** every file's LBA is fixed and the biggest free gap is **1 sector** — so a new file
  must EXTEND the disc. There is a trailing `<dummy sectors="150" offs="313747">`; placing TIER3.RND at a
  far/out-of-order LBA *inside* that dummy left its data **zeroed** (mkpsxiso wrote the dummy over it). FIX:
  place TIER3.RND AT 313747 and shrink the dummy to start past it (148 sec @313749). Then data is written.
- **Loader context:** calling `FUNC_80046330` from the **DrawOTag stub faults** (A(0x40) panic) — it mutates
  resource/CD globals mid-DMA-dispatch. Call it from the **player-update (collision cave)** context instead.
- **Cave zero-run budget:** the load call bloats the cave past its 0x378 slot (CAVE_C 0x80081100 → tramp3
  0x80081478). FIX: put the heavy load (FUNC_80046330 + the embedded `level01\tier3.rnd` string) in a tiny
  asm trampoline `tier3_load_render @0x8007F288` (loader-stub zero-run); the cave just `jalr`s it (.text 0x370).
- **Render flags baked in:** hardcoded MODE/SUPPRESS/GATEOFF in the render cave so the loader needn't write a
  flag buffer (more cave headroom).
- **Cave is a cold-boot load buffer — do NOT grow it for the load trigger.** Putting the load call IN the
  collision cave grew its .text 0x340→0x370; the cave's zero-run (0x800810bc..0x800814c4) is a **cold-boot
  LEVEL-LOAD scratch buffer**, so the loader read the 0x340..tramp3(0x80081478) gap, got the cave code as a
  garbage size, and its memcpy overran → **DBE @0x8003ef70 → BIOS panic, Flik never spawns**. The movie
  harness MISSES this (its start-state is LEVEL01 already loaded → skips the cold-boot full load → only a
  manual cold boot tests it). FIX: keep the cave at its proven-safe **0x340**, and re-route `tier3_tramp`'s
  resume `j 0x800495D8` → `j 0x8007F288` (= `tier3_load_render`, in the load-safe stub zero-run) which does
  the one-shot load then resumes 0x800495D8. So the load runs in the player-update context from a non-load
  region. **Rule: the collision cave must stay ≤0x340 .text.** (`build_tier3_disc.py` passes
  `-equ TIER3_INSTALL_HOOK 0`; the render build passes 1, which gates the re-route.)
Files: `tools/build_tier3_render_disc.py` (file staging + XML/dummy patch), `mod/tier3_loader.asm` (stub +
trampoline), `mod/caves/tier3_collision.c` (`#ifdef TIER3_RENDER_LOAD` gate), `mod/caves/tier3_otrender.c`.

## COLD-BOOT FIX — RESOLVED (2026-06-26, commit a7176ec)

The "IMPLEMENTED + VERIFIED" note above was verified via a **save-state (warm) path**, which masked three
cold-boot bugs — a true power-on cold boot froze/hung. Root-caused via live A/B in the debugger (cold-boot
from the `flik_to_level01_stall` from-boot movie, not a save state) and all fixed. The render disc now
cold-boots the **visible** custom level (collision + render together) and survives movement.

1. **Cold-boot hang — DON'T append the blob to LEVEL.DAT.** The build appended the 400-byte level blob to
   `LEVEL01/LEVEL.DAT`, which poisons the native DAT parser `FUNC_8001cdc0`: its epilogue
   `0x8001d384 sw v0, 0x604(gp)` (sole writer of `0x8008239c`) computes `[0x8008239c] = out_end − tail`,
   `tail = LW(out_end−4)`; the appended blob shifts that read into blob bytes → garbage pointer
   (**pristine `0x801afba4` → render `0x5f5afce0`**, outside RAM) → bus-error / wedged-DrawSync hang. The
   renderer's DrawOTag hook is NOT the cause. **Fix:** stop appending to LEVEL.DAT (stays byte-pristine);
   bundle the blob INTO the `TIER3.RND` CD file so it rides to high RAM with the render. `TIER3_LEVEL_BASE`
   = a fixed high-RAM address. (`tools/build_tier3_render_disc.py`)

2. **Loader self-skip — `fname` overlapped `COPIED`.** The `"level01\tier3.rnd"` string auto-landed at
   `0x8007F2F4` and overran the hardcoded `COPIED` flag at `0x8007F300` (read back as `"3.rn"`, nonzero), so
   `tier3_load_render`'s `bne COPIED,zero` self-skip never loaded `TIER3.RND`. **Fix:** pin `fname` with
   `.org 0x8007F340` (still inside the `0x8007F174..0x8007F376` boot-safe zero-run) so `COPIED`/`SCRATCH`
   read clean 0 at boot. (`mod/tier3_loader.asm`)

3. **GPU-DMA wedge / hard freeze on movement (the "UP+RIGHT crash").** Held UP+RIGHT → game froze, PC pinned
   forever at the DrawSync spin-wait **`0x80064a70`** (`lw v0,(v1); and v0,0x04000000; beq v0,zero,…`) —
   emulator alive, CPU trapped, input dead = hard freeze. **Cause:** the render's scratch (`NODEBUF`
   `0x801E2000` + projection arrays `0x801E1000`) sat **inside the game's own OT/primitive work area**
   (measured: game OT heads at `0x1cc3ac` and `0x1e1368`, primitives down to ~`0x1e2xxx`; the buffer grows
   toward us as Flik moves). When the game's OT chain walked into our stale NODEBUF bytes it followed a
   runaway self-decreasing pointer chain (`0x1e24f0→0x1e24ec→…`) that never hit a terminator → DMA never
   signals done → infinite DrawSync. **Fix:** relocate ALL render scratch to **`0x801F0000`** — the ~100KB
   gap ABOVE the game OT (tops ~`0x1e5400`) and BELOW the stack (~`0x1ff000`), sentinel-verified game-free
   across gameplay+movement. Also cured the alternating black frames. Render code+blob stay at
   `0x801E0000`/`0x801E0C00` (proven stable). (`mod/caves/tier3_otrender.c`)

**Verified (cold boot, no save state):** custom level (green platform + yellow ramp + magenta gap) renders,
native terrain suppressed, Flik composited on top and pinned to the custom floor (Y −266); **no wedge across
~2400 frames of UP+RIGHT + all directions**; aggressive falling reaches a normal GAME OVER (normal flow).
Disc: `build/ABL_tier3_render.{bin,cue}`. Reproduce: cold-boot in an isolated instance, replay the from-boot
movie to LEVEL01, then move Flik to fire the loader (`COPIED=1`). See auto-memory `tier3-render-disc-coldboot-hang`.

## Original plan (for reference)

1. Build the render image as a standalone uncompressed file and add it to `REBUILD/abl.xml` at an unused LBA, e.g. `\LEVEL01\TIER3.RND` (2 sectors).
2. At the first real gameplay frame (Flik spawned), call `FUNC_80046330("<path>\\TIER3.RND", 0x801E0000)` then `jal` the loaded render; the existing DrawOTag stub (`mod/tier3_loader.asm`) already steers the OT once `COPIED` flips.
3. **OPEN before wiring:** trace the exact name/path string `CdSearchFile` expects (relative vs full `\LEVEL01\TIER3.RND;1`) and the directory context — capture from a live `FUNC_80046330` call.

## SESSION LOG — 2026-06-26 live-fire debugging (5 bugs found; 4 fixed, 1 open)

After the cold-boot delivery "worked" on a save-state path, true cold-boot + real play surfaced a chain of
bugs. Each was root-caused with the DuckStation debugger (COP0_EPC/CAUSE, OT-walks, live A/B). Files:
`mod/caves/tier3_otrender.c`, `mod/tier3_loader.asm`, `mod/tier3_otrender_live.asm`,
`tools/build_tier3_render_disc.py`, `mod/gen_tier3_level.py`.

1. **Cold-boot hang — FIXED.** Appending the level blob to `LEVEL01/LEVEL.DAT` poisoned the native DAT
   parser `FUNC_8001cdc0` (epilogue `0x8001d384 sw v0,0x604(gp)` writes `[0x8008239c]=out_end-tail`,
   `tail=LW(out_end-4)`; the blob shifted that read → garbage pointer `0x5f5afce0` vs pristine `0x801afba4`
   → bus-error/DrawSync hang). Fix: stop appending to LEVEL.DAT; ship the blob bundled in the `TIER3.RND`
   CD file → high RAM.
2. **Loader self-skip — FIXED.** The `fname` string overlapped the hardcoded `COPIED` flag at `0x8007F300`
   ("3.rn", nonzero) → `tier3_load_render` thought it was already loaded → never loaded. Fix: pin `fname`
   with `.org 0x8007F340`.
3. **GPU-DMA wedge / hard freeze (the "UP+RIGHT" crash) — FIXED.** Render scratch (`NODEBUF`+PV arrays) sat
   inside the game's own OT/primitive work area (heads at `0x1cc3ac`/`0x1e1368`); as the OT grew it walked
   into our stale node bytes → runaway display-list chain → DrawSync spin `@0x80064a70` never completes.
   Fix: relocate scratch to free RAM.
4. **Dense-geometry crash (DBE) — FIXED.** The blob at `0x801E0C00` straddled the game OT (head `0x1e1368`);
   blobs > ~0x768 B got their tail clobbered → garbage triangle indices → `PVZ[idx]` out-of-bounds (DBE,
   `COP0_EPC=0x801e04b8`). Fix: relocate the WHOLE Tier-3 runtime (render code `0x801F0000`, blob
   `0x801F0C00`, scratch `0x801F8000`) into the verified-free high block. Engine now degrades gracefully
   (truncates) instead of crashing past the 64-vert/128-node caps. Stress tooling added:
   `gen_tier3_level.py ABL_TIER3_GRID=N`.
5. **MIPS load-delay-slot bug ("can't see it on my own DuckStation") — FIXED.** The hand-written loader
   (`tier3_loader.asm`) did `lw $tN, COPIED`/`lw $tN, Flik.X` IMMEDIATELY followed by the branch using the
   loaded reg — a R3000 load-delay violation. DuckStation's Cached-Interpreter/Recompiler don't emulate the
   hazard (bug invisible — all harness tests passed); pure **Interpreter** (the operator's CPU mode) does →
   the branch read STALE register garbage → gate misfired → loader skipped. **Would also fail on real PS1
   hardware.** Traced live: `0x8007f290 bne t1,zero` read `t1=0xffffffa5` (stale) not COPIED=0. Fix: honor
   the load-delay slot in all 3 gates (reorder an independent instr into each slot, zero size change;
   `tier3_load_render` is byte-tight vs `SCRATCH@0x8007F2F8`). VERIFIED in Interpreter via a save-state
   bridge (the boot movie desyncs across CPU modes): drove Flik → `COPIED 0→1`, blob loaded, custom level
   renders. Now works in **all CPU modes + real hardware**; the CPU-mode workaround is obsolete.

### OPEN — render code overwritten in complex/turned-around views (RI crash)
After #5, the level works — but **turning Flik to face the full native level crashes**: RI exception,
`COP0_EPC=0x801F0200` (= `RENDER_C`); the render **code** at `0x801F0000` is overwritten with OT/primitive
data. Cause: the game's own OT/primitive buffer (double-buffered, ~`0x1cc000`–`0x1e5400` plus a second
buffer reaching `0x1F0xxx`) **grows into `0x801F0000` when a busy view is on screen** — on top of our
render code → executes garbage. The spawn-facing sentinel scan that blessed `0x801F0000` was too optimistic
(suppressed-terrain view = low primitive load). Likely the same root as the **butt-slam crash**. Repro:
reach LEVEL01, tap Left ~0.1s, wait ~5s → reliable crash. **Fix plan:** measure the game's *worst-case* RAM
footprint (face the full level + move; sentinel-scan all of high/mid RAM) and relocate the render code to a
region that stays free under load. Code must be protected (overwrite → RI); scratch/blob overwrite only
glitches. See auto-memory `tier3-render-disc-coldboot-hang`.

## Related
[[Tier 3 - Custom Level Engine]] · [[FUNC_8003A318]] · [[FUNC_8001A1DC]] · [[Asset - LEVEL.RAW]] · `src_re/file_loader_80046330.c`
