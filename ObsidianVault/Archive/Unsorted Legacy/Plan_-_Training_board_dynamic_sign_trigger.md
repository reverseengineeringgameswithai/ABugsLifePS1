---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Plans/Plan - Training board dynamic sign trigger.md
aliases:
  - "Plan - Training board dynamic sign trigger"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Plans/Plan - Training board dynamic sign trigger.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Plan - Training board dynamic sign trigger
type: plan
status: ✅ COMPLETE + cold-boot verified — disc build/ABL_TRAIN_TUTORIAL4.bin
created: 2026-07-05
tags: [plan, training, board, sign, objective, xa, audio, mod, trigger]
---

> **✅ COMPLETE 2026-07-05 — cold-boot verified.** Step 0 shows the custom **hand** sign
> with a **BLANK** number, streams the **injected AUDIO4-ch0** line full-length, then
> **advances to the next sign** the instant the line ends (its silence-pad tail = the
> "wait a bit then move on"). KEY: the stock step-0 AUDIO-PLAY is left byte-for-byte;
> only the ADVANCE half is rewritten in-place. Build:
> ```
> python3 tools/media_replace.py audio --target AUDIO4:0 --no-loop \
>     --input <line.wav> -o build/AUDIO4_patched.XA
> python3 tools/patch_training_overlay.py -o build/LEVEL07_LEVEL1_patched.BIN
> python3 tools/training_board_edit.py stage --image <hand.png> --sign 0 -o build/LEVEL07_LEVEL1_board.RAW
> python3 tools/build_autolayout_disc.py --out build/ABL_TRAIN_TUTORIAL4 --force \
>     --stage files/LEVEL07/LEVEL1.RAW=build/LEVEL07_LEVEL1_board.RAW \
>     --stage files/LEVEL07/LEVEL1.BIN=build/LEVEL07_LEVEL1_patched.BIN \
>     --stage files/BUGXASTR/AUDIO4.XA=build/AUDIO4_patched.XA
> ```
> (XA "mixed" false-mismatches the autolayout LBA verifier — the XA IS embedded; confirm
> via substring search. WHY the in-place patch, not a cave: a cave that re-issues the
> audio hits a "CD/XA not ready" window post-load and stays silent — preserving the stock
> audio-play is essential.)
>
> **2026-07-06 consolidated-build correction:** `tools/patch_training_overlay.py` had
> drifted back to an EXE cave jump. In active ALLMODS this failed after selecting
> Training and pressing `X` on the Training loading prompt. The tool now again uses the
> verified 40-byte in-place patch at `LEVEL07/LEVEL1.BIN` file `0x660`, and
> `tools/training_tutorial_stager.py` no longer stages `SCUS_942.88` for this mod unless
> it changes. Verified in active `build/ABL_ALLMODS.cue`: Training enters gameplay.
>
> **2026-07-07 step-2 blackberry gate correction:** the later ALLMODS step-2
> gate briefly reused `LEVEL1.BIN` apparent tail `0x800B4A30` and crashed
> (`PC=0x000000A0`, `COP0_EPC=0x800B4A34`) because live Training owns that
> address as runtime state. The fixed build leaves `0x800B4A30` alone and uses
> resident EXE caves `0x8007F0D8..0x8007F118` (voice+collection gate) and
> `0x8007F930..0x8007F954` (hidden-pickup reveal shim). Rebuilt
> `build/ABL_ALLMODS.bin` SHA-256:
> `2ad04e4012c45dc15ad38123987337b543396f32903dcabee1856a59d40ca517`.
> See [[Training NPC progression]] and `src_re/training_tutorial_progression.c`.

# Training board — dynamic sign trigger (raise hand sign 3s after monologue)

## Goal (operator, 2026-07-05)
The instructor ant's chalkboard normally shows a sign with a "×N" objective counter
(N = berries to throw); on goal completion the NPC **lowers the sign and raises the next
one** (new objective). We want an alternate driver:

> **3 seconds after the injected NPC monologue (`training_entry_line2.wav`) finishes**, lower
> the current sign and **raise the custom hand sign with a BLANK counter** (no number,
> visual-only — no numeric goal behind it). Exposed as a toggle in the Python mod GUI /
> `mods.yaml`, combined with the rest of the build.

Design decisions locked:
- Trigger **replaces** the berry-count driver (blank objective, no numeric condition).
- Hand sign is **visual-only** for this pass (real conditions come later).
- **Trigger source REVISED 2026-07-05: key off "board raised" (scene/sign-up state), NOT
  monologue-end.** → the old Phase-2 audio-EOF detection is DROPPED from the critical path.
  Audio injection stays a SEPARATE, already-solved step (media_replace.py / xa_audio.py — the
  longer-XA-voice pipeline) that the consolidated build layers in; it just plays as a normal
  replaced voice line and is fully decoupled from the trigger.

## What is already DONE (this initiative's prerequisite)
- Board sign pictures RESOLVED + injectable: `LEVEL07/LEVEL1.RAW` chunk 29 @0x8B7C8,
  tile-major, sign *k* at `+k*2048`; board shows **sign 0**. Tool
  `tools/training_board_edit.py replace --image X --sign N` (blue-grey CLUT quantise;
  size-changing → auto-layout reflow disc). In-game verified (clean hand: `build/ABL_TRAINBOARD_HAND3`).
  See [[Training board sign images]], src_re/training_board_sign.c.

## ✅ Mechanism fully decoded 2026-07-05 — all pieces for the mod exist
- **Tutorial step engine** `0x800B3F58` (14 steps, jump table `0x800B39A4[step]`). Each step:
  plays audio (`jal 0x80046AC0`, packed id from table `0x800B4A14[step]`), counts down per-step
  **timer `0x800B4A50`** (already used for timed waits), gates on an objective flag, then calls
  sign-raise to advance.
- **First monologue = AUDIO4.XA channel 0** (step-0 id `0x18`; steps 0-7=AUDIO4 ch0-7, 8-13=AUDIO5 ch0-5).
- **Sign-raise `0x800B3B54(sign, count)`** — `count < 0` SKIPS the digit ⇒ **BLANK counter**
  (VERIFIED in-game: callFunction(0,-1) → hand sign, no number).
- Objective: berries-thrown count `0x800B4A3C` / array `0x800B4A58`, goal 7.
- **Overlay disc file FOUND:** the whole training tutorial engine is in **`LEVEL07/LEVEL1.BIN`**,
  **UNCOMPRESSED** (sign-raise fn `0x800b3b54` = file offset **0x1B4**; load base `0x800b39a0`, so
  file_off = RAM − 0x800b39a0). Uncompressed ⇒ patches are **size-preserving, no recompress/reflow**.
- **Engine internals (for the patch):** step index `0x800b4a3c`; per-step state array `0x800b4a58[step]`
  (holds the handler's `s0` = "audio played" flag); a step ADVANCES when its handler sets the advance
  flag (`s1=1`) → engine tail `0x800b477c` sets timer `0x800b4a50` (default 30 = ~0.5s) and does
  step++. Top of engine (`0x800b3f80`) decrements the timer and WAITS while it's >0. Step-0 handler
  (~`0x800b3fd4`): plays audio table[0]=0x18 (AUDIO4 ch0), advances when `[0x800a6586]==17`.
- **Phase 3 patch design (LEVEL1.BIN, size-preserving):** step-0 handler → (a) call
  `0x800b3b54(sign=0, count=-1)` so the hand raises with a BLANK number; (b) on first run set timer
  `0x800b4a50`=~180 (3s) + mark `s0`; (c) replace the `[0x800a6586]==17` advance gate so it advances
  when the timer has elapsed (s0 already set) instead of on the objective. Plus inject the custom line
  at AUDIO4 ch0 (`media_replace.py`). NOT yet written/tested — this is the remaining build work.

## Phases
### Phase 1 — RE the board objective / sign-change state machine  ✅ DONE
Find, live (isolated DuckStation, movie `LEVEL00_load` → scene_id 17):
- the **objective counter** global (the "×N", N = berries-to-throw) + how the digit is stamped
  (the runtime `(348,16,4,32)` sub-upload) and how to **blank** it;
- the **current-sign-index** global + the **sign lower/raise** routine (the thing normally called
  on goal completion);
- entry conditions so a cave can invoke "advance to hand sign, blank counter".
Output: addresses + routine in `src_re/training_board_sign.c` (or a new `src_re/training_objective.c`).

### Phase 2 — Audio: inject the line + find its end signal
- Identify which `BUGXASTR/AUDIOn.XA` **file + channel** is the training entry monologue.
- Inject `training_entry_line2.wav` there (`tools/media_replace.py`), verify it plays.
- Locate the libcd streamer's per-channel **EOF / "voice playing"** flag to detect "finished"
  (voice stops on the XA EOF submode bit — see src_re/xa_voice_streaming.c). Record the global.
Output: audio map + end-detection global in src_re/xa_voice_streaming.c.

### Phase 3 — Code-cave + build wiring  (NOT started)
- Cave: on scene-17, wait for [monologue-channel EOF] + 3s (frame counter), then call the
  sign-advance routine to raise the hand sign with a blanked counter.
- Register as a selectable code-mod; combine image (+audio) into one reflow disc.
- In-game verify from cold boot. Output: `mod/` cave C + asm + registry entry.

## Progress log
### 2026-07-05 — Phase 1 + 2 first pass (live, disc build/ABL_TRAINBOARD_HAND2)
**Phase 1 (board objective / sign-change):**
- Reaching the in-world board CLARIFIED: play `LEVEL00_load.movie.json` to end (~4162f →
  "Training Level loading..." screen), then KEEP advancing (no input) → instructor+Flik+chalkboard
  auto-appears (board up, showing sign + "×N"). scene_id stays 0x11 throughout incl. loading screen.
- Draw path: sign = GP0(0x3c) quad texpage(320,0) CLUT(784,229); the "×N" digit = a SEPARATE quad
  from the same atlas (digit tiles), stamped at ~(348,16). Confirmed via gpu.pickObject.
- Digit "×N" = a SEPARATE GP0(0x3c) quad, texpage (320,0) but **CLUT (768,229)** (one less than
  the sign's 784,229), sampling atlas DIGIT tiles at small u (digit '6' → uv0.u=0x0a). Emitted by
  the generic primitive writer ~0x80014c30. Digit readout for RE: pick that quad near (134,44).
- **Berry-throw probe (square button, operator idea):** memoryScan exact-6 → "decreased" after 2
  thrown berries isolated **0x8008a2da** (first=6→4, tracks thrown berries). BUT it is a DERIVED
  value — poking it doesn't stick (re-read 4/5 after writing 9/0) and the **on-screen digit never
  followed it** (stayed '6' even with 0x8008a2da=0). ⇒ the DISPLAYED number is **baked into the
  board's raised-sign state** (cached digit-quad UV, set once at raise-time), not a live counter read.
### 2026-07-05 (session 2) — objective + sign-advance LOCATED
Method that finally worked (after fixing instrumentation): **clean input via
`emulator.setControllerState` press+RELEASE** (⚠️ `pressButton` HOLDS the button → throw-storm;
a held `square` also persists across `loadState` and corrupts every read — this caused hours of
false leads), **2-frame square = exactly one throw**, then `memoryScan` + race-free
`gpu.frameSnapshot`.
- **Objective counter FOUND:** the board "×N" ticks 6→5→4→3 as you throw (visually confirmed).
  Stored as berries-THROWN (increasing): count/index **0x800B4A3C**, per-throw word array base
  **0x800B4A58**; **goal = 7** (thrown=1 → board "6"). Handler is TRAINING-OVERLAY code
  ~**0x800B4768+** (data 0x800B4A..; also sets a 30-frame timer 0x800B4A50) — NOT static EXE,
  hence not in re_symbols.sym. The DISPLAYED digit is CACHED (poking the count doesn't refresh it;
  only a real throw runs the handler that redraws it).
- **SIGN-ADVANCE = OBJECTIVE COMPLETION (key!):** throwing the goal count makes the instructor
  **lower the current sign and raise the NEXT one with a new objective** — observed live: hand
  (sign 0, my edit) → **bug "×6"** (a different chunk-29 sign). This IS the "lower/raise" event to
  retime. So the Phase-3 cave = on BOARD-RAISED, start a 3s timer; at 3s force the advance (drive
  thrown≥goal, or call the advance routine directly) and blank the raised sign's digit.
- RED HERRINGS ruled out: 0x800910A3-0x800910AA = animation phase counters (fn 0x8005518C, wrap
  mod 2/3/5/6/7/8/16/32); 0x8008a2da = volatile scratch. Both were scan artifacts from held-button
  throw-storms.
- **OPEN / NEXT:** disassemble overlay 0x800B4768+ & caller → the exact advance routine + the cached
  displayed-digit address (to blank). Then Phase 3 cave. Fast anchor:
  `/tmp/duckstation-debugger/board_scene.sav` (board up, HAND3 disc, thrown≈1).
  ⚠️ Design nuance to confirm w/ operator: the hand is currently sign 0 (the FIRST sign); "raise the
  hand 3s after board-raised" may mean re-ordering so the hand is the sign raised BY the advance.

**Phase 2 (audio + EOF):**
- Music start = `FUNC_8004699c(packed_id)` (file=packed_id>>3→AUDIO n+1, chan=packed_id&7,
  CdlSetfilter@0x80046a6c). Filename table RAM 0x800772c8 (5×12B). Voice ends on XA EOF bit (0x80).
- **The training monologue is NOT started via FUNC_8004699c** (execTrace on 0x8004699c caught
  nothing in the scene-start window) → voice/dialogue uses a DIFFERENT start fn (still to find).
- XA audio streams at scene start (subheader file=1, chans 0/2/3/5/6 submode 0x64 = interleave;
  the PLAYED channel = the filter setting, not the subheader).
- **Likely complication:** the monologue may be **interaction/proximity-triggered** (plays when
  Flik walks up to the instructor), which the input-less movie never reaches — so "3s after
  monologue" needs the voice trigger + a way to drive Flik to the instructor (scripted input /
  pressButton) to observe it. Next: find the voice-start fn (grep CdlReadS/CdlSetfilter callers
  other than 0x8004699c), then trace it while walking Flik to the NPC.

## Live-RE anchors
- scene id global `0x80082504` (Training = 0x11); reach via movie `LEVEL00_load.movie.json`.
- board tile VRAM (336,0) 16u×64 (=64×64px); atlas texpage (320,0), CLUT (784,229).
- board sign source = decompressed `LEVEL07/LEVEL1.RAW` chunk 29 @0x8B7C8.

## Related
[[Training board sign images]] · [[Blocker - Training board sign disc offset unresolved]] (CLOSED) ·
[[Plan - Longer XA voice lines]] · src_re/training_board_sign.c · src_re/xa_voice_streaming.c ·
tools/training_board_edit.py · tools/media_replace.py
