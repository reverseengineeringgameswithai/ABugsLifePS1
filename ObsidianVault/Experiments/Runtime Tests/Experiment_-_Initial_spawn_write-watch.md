---
kind: experiment
id: Experiment_-_Initial_spawn_write-watch
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Initial spawn write-watch.md
aliases:
  - "Experiment - Initial spawn write-watch"
---

# Experiment — initial level-load spawn write-watch (GAP-0035 layer 1)

> Migrated from `ObsidianVault/Experiments/Experiment - Initial spawn write-watch.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — initial level-load spawn write-watch (GAP-0035 layer 1)

> **The single runtime experiment that closed [[Gameplay - Initial Player Spawn|GAP-0035 layer 1]].** Cold-boot LEVEL01 via the boot→LEVEL01 movie, arm a WRITE-watch over the whole player block *before* the spawn, capture the first writer + its source. **Result: the writer is [[FUNC_80046B20]]`(a0=player 0x800a6500, a1=scene_index)`; the source is a RESIDENT EXE table at `0x80077314 + index*12` (NOT LEVEL.DAT, NOT the `0x80096d18` BIN-baked area).** Runtime, local-only ([[DuckStation Fork Reproducibility]] / GAP-0001). Reproducible driver: `tools/trace_initial_spawn.py`.

## Setup (isolated instance — never touches the user's own DuckStation)
```bash
DUCK=~/duckstation       # the external-debugger fork (CLAUDE.md / abl_dbg.py default)
"$DUCK"/scripts/debugger-client/launch_debugger_instance.sh start \
    --disc "/abs/Disney-Pixar A Bug's Life (v1.0).cue" --port 23460 --no-fastboot
# config root /tmp/duckstation-debugger, token debugger-1000, BIOS read-only
```
Connect: `DebuggerClient("127.0.0.1",23460,"ws").authenticate("debugger-1000")` then `c.transport.sock.settimeout(60)`. Driver: `tools/trace_initial_spawn.py {recon|capture|trace|table|all}`.

## Method
The live block `0x800a6500` is BSS-zero at boot and the spawn write is a one-shot during load — so the watch must be armed **before** it. Movie `flik_to_level01_stall.mv.movie.json` is a **from_boot, 6470-frame** movie (boot→LEVEL01→idle).
1. **Recon** (fast, no watch): `movie.startPlayback{load_start_state:true}` + `emulator.setFastForward` + `advanceFrames`, polling `[0x800a6500]`. X goes `0→0x301f4` between frame ~4000 (scene_id flips to **1**) and ~4400.
2. **Capture** (writer): re-replay, `advanceFrames` to ~3800 (X still 0), `accessLog.addWatch{address:0x800a6500,length:0xa8,type:"write"}`, step ×20 to the spawn, then `accessLog.findFirstWrite` + `accessLog.get`.
3. **Trace** (args/source): re-replay, `execTrace.addWatch` at `0x80046b20` (capture `a0,a1,a2,ra,sp,gp`) and `0x80046b88` (capture `s0,v0,s3`).
4. **Table**: read `0x80077314` from RAM and cross-check the same bytes against the boot EXE `SCUS_942.88` (file offset `0x67b14`).

## Evidence (emulator frame **4518**, scene_id=1; reproduced 2× + EXE cross-check)
**`accessLog.findFirstWrite{0x800a6500}`** → `pc=0xbfc02bb4` `bgtz a2,…` — the **BIOS `memset`** (`0xbfc02b a4..bb8`: `sb a1,0(a0); a0++; a2--`), reached via helper `0x8005f7ac`. This only **zeroes** the 168-byte struct (fill byte `a1=0`); `0x30213`≠a repeated byte, so it is not the spawn. The real field writes (dropping `0xbfc02bb4`) are all **FUNC_80046B20**:

| store PC | player off (addr) | value | meaning |
|---|---|---|---|
| `0x80046b98` | +0x00 `0x800a6500` | `0x301f4` | **X** ← record word0 |
| `0x80046bac` | +0x08 `0x800a6508` | `0x7855f` | **Z** ← record word1 (after `jal 0x80037a38`) |
| `0x80046bb8` | +0x04 `0x800a6504` | `0xa30`(≈) | **Y** ← `FUNC_80037A38(pos) − 0x100` (ground height; **computed, not stored**) |
| `0x80046bd0/d4/d8` | +0x10/14/18 | X/Y/Z | previous/**render copy** ← live XYZ |
| `0x80046c14/18/1c`→`+50/54/58` | +0x50/54/58 | X/Y/Z | **respawn anchor** ← live XYZ |
| `0x80046bf0/f4`,`c1c/20` | +0x20/+0x28/+0x78 | `0xdb1` | **heading** ← record word2 |
| `0x80046bec`,`c04`,`bfc` | +0x98=`0x11`, +0x94=`4`, +0x4c=`0x80000000` | — | flags/counters |
| `0x80046c00` | +0xa0 `0x800a65a0` | `s2` | **lives PRESERVED** (saved to `s2` @`0x80046b64` *before* the memset, restored after) |

**`execTrace` @ `0x80046b20` (entry):** `a0=0x800a6500`, **`a1=0x00000001`**, `ra=0x8005baac`.
**`execTrace` @ `0x80046b88` (source load):** `s0=0x80077320`, `v0=0x80077314`, `s3=0x800a6500`.
⇒ source record ptr `= 0x80077314 + a1*12 = 0x80077320` (a1=1).

**Table cross-check (`tools/trace_initial_spawn.py table`):** runtime `0x80077314` == EXE `SCUS_942.88[0x67b14]` for all 18 records. Record **1** = `X 197108(0x301f4), Z 492895(0x7855f), heading 3505(0xdb1)` — byte-exact match to the captured spawn. Records 0–17 are plausible coordinate triples (heading 0..0xfff); 18+ is other data ⇒ a **per-scene start table** (index 1 = LEVEL01).

**Caller context:** the `jal 0x80046b20` is at `0x8005baa4` (`a1 = s2 = a0`); no `jr ra` lies between the prologue `0x8005b714` and the call ⇒ it is **inside scene-init [[FUNC_8005B714]]`(scene_id)`**. The five `sw zero,0x80082{390,448,294,370,29c}` immediately before the call ARE the documented "zero the `0x80082xxx` state cluster" step. So **scene-init = state-cluster zero + noise-cursor seed + player spawn**, and `index = scene_id` (=1 here; scene_id==stage==1 at LEVEL01, so scene-vs-stage is LIKELY-not-yet-disambiguated).

## Conclusion (corrects the prior hypothesis)
The layer-1 spawn source is a **resident table baked in the boot EXE** — **not** a LEVEL.DAT placement record and **not** the LEVEL.BIN-baked records at `0x80096d18`. The writer was static-invisible only because the store lives behind a register-arg pointer (`a0`) and the BIOS memset masks the first write; the runtime watch resolves both. **Warp-landing** spawns through the **same** `FUNC_80046B20(player, scene_id)` (scene-init runs on every entry) reading `table[scene_id]` — so the warp-landing write mechanism is now known; only live-warp *execution* remains blocked (the shell-phase fixture, GAP-0035 other half).

## Confidence
- Writer `FUNC_80046B20(a0=player, a1=index)` — **CONFIRMED** (write-watch + execTrace, reproduced 2×).
- Source = resident EXE table `0x80077314 + index*12`; offsets +0→X/+4→Z/+8→heading; Y computed `0x80037a38 − 0x100` — **CONFIRMED** (ptr capture + value-match + EXE cross-check + disasm).
- Caller = scene-init `FUNC_8005B714` @ `0x8005baa4` — **CONFIRMED** (ra + bounds + cluster-zero context).
- `index == scene_id`; table is per-scene (records 1–17 = levels) — **LIKELY** (only index 1 byte-proven live).
- Warp landing reuses the same fn/table — **LIKELY-HIGH** (same in-scene-init code path).

## Related
[[Gameplay - Initial Player Spawn]] · [[FUNC_80046B20]] · [[FUNC_8005B714]] · [[Gameplay - Player Spawn and Placement]] · [[Gameplay - Warp and Level Transition]] · [[MEM - Player state 800A6500]] · [[API - accessLog]] · [[API - execTrace]] · [[API - movie]] · `tools/trace_initial_spawn.py`
