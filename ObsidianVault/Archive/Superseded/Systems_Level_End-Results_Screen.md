---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Level End-Results Screen.md
aliases:
  - "Level End-Results Screen"
migration_action: split
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Level End-Results Screen.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Level_End-Results_Screen.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Level End-Results Screen
type: system
status: active - results-screen draw function decoded; 8-letter TRAINING row disc-persisted in BITS/MEMORY.BIN
updated: 2026-07-07
confidence: LIVE-PROBE (isolated DuckStation instance, training_all_stuff_collected_ending.sav and ALLMODS_COLLECTING_TRAINING.movie.json) + live disassembly
tags: [system, hud, results-screen, training, rcg, flikflik, mod]
---

# Level End-Results Screen

Investigation of a bug report: on the TRAINING level's "level complete" results screen, grain count, the `FLIK` letter word, and a third collectible counter were reported as wrong. Reproduced live via the isolated DuckStation debugger instance against the pristine `SCUS-94288` disc and the `training_all_stuff_collected_ending.sav` save state (scene id `17` = TRAINING, confirms [[training-board-sign-image]] scene-id note).

## Repro method

1. Load `training_all_stuff_collected_ending.sav` (media validated against `Disney-Pixar A Bug's Life (v1.0).cue`).
2. `emulator.setControllerState {up:true}`, advance in ~10-frame chunks — transition latch `0x800823A0` flips `0→1` after ~60 held frames (same mechanism as the LEVEL02/04/05/14 "be-here" endings in [[Level Goal and Exit Trigger Matrix]]).
3. Release input, advance frames. Screen fades to black over ~50 frames, then the "level complete" results screen fades in and its three counters run a count-up animation for roughly 750–900 frames before settling. After settling it fades out again into a "do you want to save?" prompt.

## Finding 1 — grain / FLIK-count / third counter are NOT broken (count-up animation, not a bug)

At the moment the results screen first appears (~frame 60 of the results phase) all three rows read `00/50`, `0/4`, `00/04` — this is a designed count-up-from-zero reveal animation, not a stuck/broken counter. Captured the same screen at increasing frame offsets from first appearance:

| Frames since results screen start | Row 1 (grain) | Row 2 (FLIK) | Row 3 (unknown) |
|---:|---|---|---|
| ~0 | `00/50` | `0/4` | `00/04` |
| ~400 | `40/50` | `0/4` | `00/04` |
| ~750–900 (settled) | `50/50` | `4/4` | `04/04` |

At settle time all three badges on the right also reveal (bronze grain-seed medal, silver "FLIK" medal, gold X medal), matching the save state's actual collection totals (grain 0x800A65A1=50/target 0x32, FLIK bits 0x800A65A2=0x0F=4/4 letters). **If a user samples the screen mid-animation they will see incorrect-looking totals — this is expected behavior, not a defect.** No code change needed here. (Row 3's exact backing global was not re-identified in this pass — see Residual Work.)

## Finding 2 — letters are spinning pseudo-3D objects; the "mirrored K" is NOT a confirmed texture bug (retracted)

**Retraction:** an earlier pass of this note claimed the settled `K` glyph was a permanently-mirrored, baked-in texture bug. The operator corrected this: zoomed screenshots show all 4 letters (`F`,`L`,`I`,`K`) are rendered as individually **spinning** objects with a 3D look, each on its own animation phase — so a single captured frame can catch any letter mid-rotation (including angles that look "mirrored" or garbled) without that being a static defect. The `K`-looks-backward observation in the previous pass may simply have been an unlucky mid-spin capture, not a landed, permanent mis-render. **This is not confirmed as a bug either way** — do not act on the old claim.

### What IS confirmed about the draw mechanism
- `gpu.pickObject` on the settled letter row returns a flat **GP0(65) textured-rectangle sprite** draw, not a GTE/3D primitive — i.e. whatever "3D spin" look these letters have is achieved via a **pre-rendered rotation flipbook of 2D sprite frames** (a common cheap PS1 pseudo-3D trick), not real per-frame GTE transforms. Evidence: `ramAddress`/`vertexPointer` `0x801cded4`/`0x801cded8`, `orderingTableEntry` `0x801cded0`, raw GP0 words `0x65f0a000 0x00980040 0x3ef0a0c0 0x00200040` → origin `(64,152)`, size `64×32`, UV origin `(192,160)`, CLUT VRAM `(768,251)`, texpage base VRAM `(704,256)`, 8bpp.
- Traced the actual writer of that packet via `accessLog.addWatch(type:write)` armed on `0x801cded0` (24 bytes) across the full trigger→settle window. The bulk of writes are generic, heavily-shared low-level helpers, not results-screen-specific code:
  - `0x8003e928`–`0x8003eec4` = `backdrop_tile_builder_8003e928` (confirmed existing `src_re` file) — this is the background grass/dirt tile builder reusing the same shared OT-packet ring buffer address across frames; its hits on this address are incidental, not the letter draw.
  - `0x80061afc`–`0x80061f78` = a cluster of tiny generic bitfield get/set leaf routines (mask/or/store a hardware-primitive-header word). `debugger.xrefsTo` on one entry point (`0x80061b74`) resolves 27 callers, all inside the **known shared HUD sprite-blit helpers** `fcn_80025f54`/`fcn_800260f8` (the exact functions already documented in `src_re/hud_800526f4.c`, callers at `0x80025ff8`, `0x800260d0`, etc). **This confirms the results-screen letters are drawn through the same low-level sprite-blit primitive as the in-level FLIK HUD**, just from a different, not-yet-isolated caller.
  - The next tier of writer PCs (`0x80014c54`, `0x80014cf4`, `0x80014dd0`, …, ~15-49 hits each) all fall inside `0x80014844`–`0x800185b4`, a **15.7 KB merged region** (`debugger.functionBounds` reports `confidence: low`, explicitly flagging it as multiple routines merged together — this matches the known giant world/HUD render-dispatch region referenced in `ObsidianVault/Functions/FUNC_800140A0.md`). The specific results-screen letter-loop has **not yet been isolated** within this merged region — it needs symbol-assisted splitting or targeted execute-breakpoint/step-out tracing, not attempted this pass.

### Residual work (not completed this pass)
- Do not re-assert "K is mirrored" as a bug without re-capturing a clean sequence of consecutive frames (not just a few coarse samples) to see whether every letter cycles through a rotation that includes mirror-looking angles (expected) versus one letter alone getting stuck away from its correct resting angle (would be a real bug).
- Have not isolated the exact instruction range inside the `0x80014844`–`0x800185b4` merged region that is the results-screen's own per-letter draw loop (as opposed to the shared blit helpers it calls into).
- Did not identify what Row 3 (`04/04`, gold "X" medal) actually counts precisely — see Finding 3 below for what was confirmed instead.
- No code or asset changes have been made. Nothing here should be treated as a shipped fix.

## Finding 3 — CONFIRMED: all three counters (grain, FLIK letters, gold-kill row) are dynamic, driven by live RAM globals, not hardcoded per-save constants

Live-perturbation test: reloaded the save, and **before** triggering the ending, wrote `0x800A65A1` (grain count) from `50`→`35` and cleared bit 3 of `0x800A65A2` (FLIK progress bitmask) from `0x0F`→`0x07`, leaving the gold-kill-related globals untouched. Triggered the ending and let it settle exactly as before.

Result: the results screen correctly counted up to and settled on **`35/50`** (grain) and **`3/4`** (FLIK, with only 3 letters revealed), while the untouched third row stayed **`04/04`**. This proves the count-up displays read live game state at settle time, not a value baked into the save/anchor — changing the level's actual totals (e.g. authoring 35 grain instead of 50, or fewer/more enemies) will correctly flow through to this screen.

Row 3's (`04/04`) backing globals were also identified in this pass: at the pre-trigger anchor, `0x80082258` (u32) read `4` and `0x800A658E` (u16, the enemy-permanence "gold-kill quota" global documented in the existing `[[Enemy death and permanence]]` note — quota is decremented **only by gold-berry kills**) read `0`. `4 − 0 = 4`, matching the displayed `04/04` exactly. This strongly corroborates that row 3 is the gold-berry-kill tally the operator asked about, computed the same way the in-level HUD "misc counter" panel already does in `src_re/hud_800526f4.c` (`draw_misc_counter_panel`: `value = LW(0x80082258) - LH(0x800A658E)`). Not independently perturbation-tested (didn't modify the quota state this pass) — treat as strong-but-not-fully-proven.

## Extending FLIK to up to 8 letters — design (not yet implemented)

The operator asked for a method to support up to 8 letters in the `FLIK` word (e.g. a longer custom word). Based on what's confirmed above and prior project work:

- **Storage**: `0x800A65A2` is an 8-bit progress bitmask; only bits 0–3 are used today (one bit per collected letter). Bits 4–7 are free — the byte already has headroom for up to **8** letter-collected flags with no storage-format change.
- **Proven precedent**: the existing FLIK5 experiment (`[[FLIK letters are glyphs]]`, "FLIK5 five-letter token gate") already extended the **in-level HUD** panel from 4 to 5 letters by adding one *extra* draw call gated on a new bit (bit 4), rather than rewriting the existing loop — this pattern is documented as the safe approach (rewriting/repointing shared descriptor bytes to fake a new letter kind broke the top-left Flik-head HUD icon in a prior failed attempt; don't repeat that).
- **What's confirmed reusable for the results screen**: its letter row is drawn via the *same* shared low-level sprite-blit helpers (`fcn_80025f54`/`fcn_800260f8`) as the in-level HUD, using a small per-letter atlas at texpage VRAM `(704,256)`/CLUT `(768,251)`, sized `64×32` per glyph, roughly one screen-row wide for 4 letters in a 319px-wide native frame (plenty of horizontal room left for more glyphs at the same pitch).
- **What's still open before this can actually be implemented**:
  1. Isolate the results-screen's own per-letter loop/table inside the `0x80014844`–`0x800185b4` merged render-dispatch region (not done — needs execute-breakpoint/step-out tracing or symbol-assisted disassembly, since generic access-log writer PCs land on shared helpers, not this specific call site).
  2. Confirm whether that loop's letter count is a hardcoded immediate (`slti`/`sltiu` against 4) or already table-driven, and whether the per-letter X position is a fixed pitch or a small constant table (needs 4 more entries for 8 letters).
  3. If a genuinely new word (not just repeated F/L/I/K) is wanted, new letter glyphs must be added to the shared atlas — same disc-texture-patch pipeline already used for the FLIK→ATTA glyph word-swap mod (`mod/glyphs/`, `tools/patch_flik_word.py`), extended to reserve 4 more atlas tiles.
  4. Live-prove a test build (extra bit + extra draw call, analogous to FLIK5) before committing to a permanent mod, per this project's usual prove-live-then-patch workflow.

None of steps 1–4 have been implemented yet; this section is a design/plan only.

### Empirical test toward "FLIKFLIK" (8 letters), 2026-07-05

Static disassembly to find the exact results-screen letter-draw call site was attempted and abandoned this pass: address-based `accessLog` write-watches on the K-glyph's `ramAddress` (`0x801CDED4`) turned out to alias a background-grass ordering-table ring-buffer slot that many *unrelated* tile draws reuse within the same single frame (confirmed via a full single-frame `gp0Trace` dump — the address is hit ~9 times per frame by a repeating grass-tile pattern at varying Y, not uniquely by the letter). `execTrace` watches on the two known shared HUD sprite-blit helpers (`fcn_80025f54`/`fcn_800260f8`, per `src_re/hud_800526f4.c`) recorded **zero hits** during the actual settled results-screen window, which retracts the previous pass's claim that the results screen reuses those specific functions — that claim was contaminated by unrelated in-level HUD activity earlier in the same wide capture window. **The exact results-screen draw routine/call site is still not isolated.**

Given that, switched to a faster empirical test instead of continued static tracing: wrote `0x800A65A2 = 0xFF` (all 8 bits set, vs. the normal max `0x0F`) before triggering the ending, then let it settle. Result (`build screenshot` not committed, see local capture only):
- Row 1 (grain `50/50`) unaffected — confirms rows are independently sourced, as already established.
- Row 2 (letters): the **denominator stayed hardcoded at `/4`** (not affected by the bitmask value), and the **numerator digit rendered as a corrupted/garbled glyph** instead of an `8`. The letter word itself showed only 3 clean glyphs (`F`,`L`,`I`) plus a corrupted 4th, i.e. the row visibly breaks once the byte's popcount exceeds 4.
- Row 3 (`04/04` normally) unexpectedly read `00/04` — i.e. forcing the letter-progress byte to `0xFF` also stalled/delayed the *third* row's own reveal. This suggests the rows may not be fully independent — some row-sequencing or gating logic likely depends on an exact `== 0x0F` equality check against the letter-progress byte (matching the exact pattern already seen in the in-level HUD's own gate: `if (LBU(G_FLIK_PROGRESS_BITS) == 0x0f) { SH(pulse, 0x400); }` in `draw_flik_bit_panel`, `src_re/hud_800526f4.c`). If the results screen has an analogous `==0x0F` check gating a shared "all objectives" completion flag that row 3 (or its reveal timing) also depends on, `0xFF` would fail that check even though "4 letters collected" is semantically still true, breaking the downstream sequencing. Not confirmed via disassembly this pass — inferred from behavior only.

**Implication for "FLIKFLIK" (8 letters, reusing existing F/L/I/K art twice, per operator's request to reuse what we have rather than fix the A/T art now):** a naive "just set more bits" approach is **not sufficient** on its own. At minimum the following also need to be found and patched (none done yet):
1. The hardcoded `/4` denominator (target) for row 2 — needs to read/patch to `8`, or find where it's set.
2. Whatever draws the numerator digit — its glyph-lookup table only handles values `0–4`; needs extending to `0–8` (or reworked to two-digit rendering if it doesn't already support that — row 1's grain counter clearly does two-digit rendering fine, so a two-digit-capable digit-draw routine already exists elsewhere in this game and may be reusable).
3. Any `==0x0F`-style exact-equality "all collected" gate(s) that other rows/sequencing depend on — these must become `==0xFF` (or population-count-based) wherever they exist, not just left as `==0x0F`, or later rows will stay stuck exactly as observed with row 3 here.
4. The actual letter-row draw loop bound (still not located — see above) must iterate 8 slots instead of 4, and needs 4 more X-position slots at the existing pitch (screen has room).

Next step if continuing: locate the true results-screen draw function via execute-breakpoint/step-out tracing from a confirmed proximate point (e.g. break at the moment `0x800A65A2` is read, since it's the "target" question — read-type `accessLog`/`execTrace` watch would show the actual reader/consumer code, which is a cleaner signal than the write-side OT-buffer aliasing that derailed this pass).

## Operator note on process

An earlier attempt at this investigation used background async agents, which the operator found the tooling doggedly kept re-spawning; that whole approach was discarded per operator instruction to work directly, single-threaded, in the foreground. This note reflects the direct, single-session foreground investigation only.

## Reproduction commands

Isolated instance (per CLAUDE.md):
```bash
~/duckstation/scripts/debugger-client/launch_debugger_instance.sh start \
  --config-dir /tmp/duckstation-debugger --port 23460 --token debugger-1000 \
  --disc "~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue" --no-fastboot
```
Then, in one connected script (avoid leaving the emulator running unpaused between separate script invocations — real time otherwise elapses and drifts far past the anchor):
```python
c.call('emulator.loadState', {'path': '.../training_all_stuff_collected_ending.sav',
                               'pause_after_load': True, 'validate_disc': True})
c.call('debugger.resume', {})
c.call('emulator.setControllerState', {'port': 0, 'buttons': {'up': True}})
# advance in <=30-frame chunks; large single advanceFrames calls (e.g. 600) have
# intermittently dropped the debugger socket (server-side) in this session —
# chunk them and reconnect/relaunch the isolated instance if the socket resets.
```

## Finding 4 — the results-screen draw routine, FULLY DECODED (2026-07-05 continuation)

Following operator correction of Finding 2 (letters are a genuine rotation flipbook, not baked-mirror), and the operator's goal ("add net-new letters — ATTA, HEIMLICH, HOPPER, etc — test with FLIKFLIK first since it reuses existing art"), the actual draw routine was isolated and fully decoded via a clean `accessLog` **read**-watch on `0x800A65A2` (reads, not writes — writes kept aliasing into an unrelated background-tile OT ring buffer, see Finding 2's retraction). All 6 read PCs landed inside one `debugger.functionBounds`-confirmed **exact**, single, 2540-byte function:

**`0x800B7DA0`–`0x800B8788`** — draws "level complete" + all 3 rows + their completion SFX/medal reveals. Confirmed structure:

- **Row 1 (grain)**: running counter in a local (`s4`), advanced roughly every 61 sub-frame ticks (`sp+0x20`), target is a **hardcoded literal `50`** (not read from level data — this specific results-screen instance is level-specific). Tens/ones digits drawn via `fcn_80025f54(x,y,56,digit)` using a reciprocal-multiply divide-by-10 trick. Not part of this task; left alone.
- **Row 2 (letters)**: 4 **unrolled** (not looped) per-letter blocks testing one bit each of `0x800A65A2`:
  | bit | letter | X | tile-phase | note |
  |---|---|---|---|---|
  | `0x01` | F | 16 | `(s1+0)&0xf`, no OR-mask | |
  | `0x02` | L | 40 | `(s1+2)&0xf \| 0x10` | |
  | `0x04` | I | 62 | `(s1+4)&0xf \| 0x20` | |
  | `0x08` | K | 82 | `(s1+6)&0xf \| 0x30` | |

  `s1` is a shared **16-frame rotation-phase counter**, incremented+masked (`s1=(s1+1)&0xf`) once per call at the function's tail — this is the "3D spin," confirmed as a **16-frame flipbook per letter** (tile-group selected by the OR-mask, sub-frame by `(s1+offset)&0xf`), not real per-frame GTE transforms and not a static mirrored texture. Each block: bit set → `fcn_80025f54(X,116,50,phase)` ("lit" draw); bit clear → `fcn_80026858(X,116,50,phase,stack:s7,s7,s7,0)` ("idle" draw, and note: the idle branch does **not** re-set `a0`, reusing whatever stale X was last in that register — a harmless pre-existing retail quirk, not something we introduced).

  After the 4 blocks, the **numerator/denominator** are drawn: `fcn_80025f54(124,116,56,s6)` (running letter-count `s6`, single digit — no tens-digit logic, unlike row 1), then `fcn_80025f54(144,116,56,10)` (literal `/` tile), then **`fcn_80025f54(164,116,56,4)`** — the target `4` is a **hardcoded immediate** at `0x800B8254`.

  `s6`'s target/cap comes from a **256-byte lookup table at RAM `0x800BE444`**, indexed by the *raw byte value* of `0x800A65A2` (not a real popcount instruction) — read at `0x800B852C`ish. The retail table is only valid for the reachable 4-bit values (`0x00,0x01,0x03,0x07,0x0F → 0..4`); other values (`0xFF`) return garbage, which is exactly why the earlier live test (Finding 3) showed a corrupted numerator glyph and a stalled row 3 — **both symptoms trace to this one table**, not to two separate bugs. The medal-reveal check for row 2 (`beq s6,v0,...` at `0x800B83AC`) also hardcodes its comparison value `4` via a delay-slot `addiu v0,zero,4` at **`0x800B8384`**.

  A `bne v1,v0(=15),...` equality check at ~`0x800B8560` (`v1` = raw progress byte) **only gates a bonus completion jingle SFX**, not the counting itself — confirmed **not** a blocking gate (this corrects the speculative severity of Finding 3's "==0x0F gate" note; it's cosmetic only, low priority).

- **Row 3 (gold-kill count)**: target is `lw v0, 0x2258(0x8008...)` (`0x80082258`, matches earlier hypothesis exactly), read directly — genuinely dynamic, unaffected by the letter byte. Its *timing threshold* (when the row starts its count-up), however, is computed as `grain*2 + popcount_table[progress_byte]*32 + 180` — so a garbage popcount-table entry (e.g. for `0xFF`) inflates this threshold to something the observation window never reaches, which is why row 3 appeared "stuck" in the earlier `0xFF` experiment. Fixing the table fixes this too.

## Finding 5 — FLIKFLIK (8-letter) extension: LIVE-PROVEN PARTIAL, not disc-persisted

Implemented and live-tested an 8-letter extension reusing the existing F/L/I/K flipbook art twice, per the operator's request to prove the mechanism with `FLIKFLIK` before investing in new letter art (A/T etc., which are a separate, harder art-asset problem since the current implementation is a 2D rotation flipbook per letter, not a real 3D model — new letters need their own flipbook frames, not covered here).

**Implementation** (assembled with `armips`, the project's existing PS1 assembler — `mod/patch_flikflik_letters.asm`):
- A **popcount table** (`tools/gen_flikflik_popcount_table.py` → `build/popcount_table.bin`, 256 bytes, `table[i]=popcount(i)`) replacing the broken lookup at `0x800BE444`.
- A **code cave** at the project's known-safe EXE zero-run `0x800810C0` (same cave address used by prior mods — `mod/patch.asm`, `mod/patch_golddrop.asm`) containing 4 more unrolled blocks mirroring the existing 4, reusing F/L/I/K art. **Final (working) X positions**, chosen to sit clear of both the numerator column and the medal icons — see Finding 6 below for why the first attempt used colliding positions:
  | bit | reuses | X | phase |
  |---|---|---|---|
  | `0x10` | F | 188 | `(s1+0)&0xf`, no mask |
  | `0x20` | L | 206 | `(s1+2)&0xf \| 0x10` |
  | `0x40` | I | 224 | `(s1+4)&0xf \| 0x20` |
  | `0x80` | K | 240 | `(s1+6)&0xf \| 0x30` |
- Two trampoline hooks redirecting into the cave (`j 0x800810C0`) at `0x800B81EC` (was `j 0x800B8220`) and `0x800B821C` (was `addiu a0,zero,124`), with the cave restoring `a0=124,a1=116` and resuming at `0x800B8224` (the original next instruction) afterward.
- Two immediate patches: `0x800B8254` (`4`→`8`, denominator) and `0x800B8384` (`4`→`8`, medal-reveal gate).
- `0x800A65A2` forced to `0xFF` (8 bits) to represent "all 8 letters collected."

**Live result** (final, working version):
- ✅ **All 8 letter glyphs render on screen**, at the correct positions, visibly reusing the F/L/I/K flipbook art.
- ✅ Row 1 (grain `50/50`) and row 3 (gold `04/04`) **unaffected** — confirmed independent.
- ✅ Row 2's numerator/denominator now renders **`8/8`** correctly (screenshot-confirmed, native-resolution capture).

## Finding 6 — numerator-digit regression: root-caused and fixed (2026-07-05, second pass)

Per operator instruction, resumed with the sole goal of finding the exact cause of the missing numerator digit, ruling out each hypothesis with evidence rather than guessing.

**Hypothesis 1 — continuous overlay "reload/churn" (from Finding 5): RULED OUT.**
Bisected the RAM region's content at fine granularity (every 30 frames) with **no patches applied** (clean baseline read). Result: the region reads all-zero from frame 0 through ~90 after the ending trigger (the overlay genuinely is not loaded yet), transitions through partial/incomplete-looking bytes around frame 120–150, and by frame 180 settles to the exact original disassembled bytes (`addiu a0,zero,124` etc.) — and **stays byte-for-byte identical from frame 180 through frame 895** (checked at 9 points). This is a **one-time load**, not periodic churn. Confirmed decisively: applied all patches exactly **once**, at frame 200 (after the load event), with **no further re-writes** for the rest of the run — read back both hook addresses at frame 200 and again at frame 895 and they were byte-identical to what was written. The earlier "re-apply every 20 frames" workaround in Finding 5 was unnecessary; it was not masking a real reload, and is not what caused the numerator to disappear.

**Hypothesis 2 — trampoline/register corruption: RULED OUT.**
Armed `execTrace` on both the cave entry (`0x800810C0`) and the resume target (`0x800B8224`) across the full settle window: **649 hits each**, matching exactly (every cave entry returns to the resume point exactly once, no skips, no double-entries). The running letter-count register `s6`, captured at both the first and last hit, went from `0x00000000` to `0x00000008` — confirming the popcount-table fix and count logic are both working correctly. `a0`/`a1` at the resume point were the correct restored values (`0x7C`=124, `0x74`=116); `a2`/`a3` held stale values from the last `jal fcn_80025f54` call, but this is harmless and matches retail behavior — the very next instruction at the resume point (`addiu a2,zero,56`) unconditionally overwrites `a2` before it's used, exactly as in the unmodified game.

**Actual root cause — FOUND, with direct visual and instrumented evidence: an X-coordinate collision.**
Used `gpu.pickObject` at the pixel coordinates of the faint grey/brown glyph-like artifact visible peeking out from behind the new letter 6 in the screenshot. Result: **two different texture pages hit at nearly the same screen pixel** — the digit atlas (`texturePage x=384,y=0,mode=0`, the pre-existing "8" numerator tile) at one sub-pixel offset, and the letter atlas (`texturePage x=704,y=256,mode=1`, my new letter 6) at an adjacent one. The numerator digit **was rendering correctly the entire time** — it was simply being painted over by the newly-added letter glyphs, because the first cave revision placed letters 5–8 at X=104/126/148/170, and the pre-existing numerator/slash/denominator draw sits at X=124/144/164 (established in Finding 4's decode) — a direct overlap.

**Fix and confirmation:** moved the 4 new letters to X=188/206/224/240. Verified this range is clear of both the numerator column and the medal-icon column (`gpu.pickObject` at x=230/240 still showed the letter-glyph page, x=250+ showed a distinct medal-icon page `x=640,y=256,mode=0` — confirming the medal starts around x≈245-250, so 240 is safe but tight). Re-ran the full sequence end-to-end with the corrected cave: native-resolution capture shows **`8/8`** rendering clearly, alongside all 8 letter glyphs, with rows 1 and 3 still correct. Screenshot evidence saved to the working scratchpad during the session (not committed to the repo per project media-hygiene policy).

**Conclusion:** the numerator regression had nothing to do with reload timing, the trampoline, or register state — it was a plain layout bug (my own chosen X positions overlapping pre-existing UI elements), now fixed in `mod/patch_flikflik_letters.asm`.

### Still open (unchanged from Finding 5)
- On-disc source file for this overlay still not located — all testing above remains RAM-only (proven stable with a single application post-load, but not yet disc-persisted or cold-boot verified).
- The 8-letter layout is visually tight against the medal icons; a real multi-word (ATTA/HEIMLICH/HOPPER) implementation will need new flipbook art per letter and likely a layout rethink (e.g. relocating the numerator) since those words may run longer than 8 letters with even less horizontal room — see the follow-up note on dynamically positioning the counter.

### Honest status / what's NOT done (superseded by Finding 7 below for the layout design)
- The on-disc file backing this overlay has not been located (next: retry `transferLog`/`accessLog` armed immediately after `loadState`, in smaller windows, across the *entire* trigger-to-settle span, to catch whatever actually refreshes this RAM region — the mechanism evaded both DMA and CPU-store instrumentation so far).
- No disc has been rebuilt or cold-boot verified. Neither `mod/patch_flikflik_letters.asm` (static, superseded) nor `mod/patch_flikflik_letters_dynamic.asm` (current) is **wired into `mod/build.py`** yet (that requires the on-disc location first).
- Task list: isolate draw routine (done), fix `/4`+digit-cap (done — was a lookup-table bug, table fix confirmed working), fix `==0x0F` side effects (confirmed cosmetic-only, not blocking), extend loop to 8 slots (done, live-proven), numerator-collision regression (done — root-caused and fixed, see Finding 6), dynamic word-length-aware layout (done — see Finding 7), build+cold-boot-verify mod (blocked on locating the on-disc file — the only remaining open item).

## Finding 7 — dynamic word-length-aware layout (2026-07-05, third pass)

Per operator request, replaced the static fixed-8-slot design (Finding 5/6) with a layout that positions both the letter row and the "#/#" counter as a function of a runtime **word length** (1-8), rather than hardcoding X positions per length. Implemented in `mod/patch_flikflik_letters_dynamic.asm` + `mod/patch_flikflik_hook_row2.asm` (supersedes the static `mod/patch_flikflik_letters.asm`, kept for history).

### Design
Realized the static version's hook point (mid-row, inside the retail bit-0x08 block) was why it needed two separate hooks and left the retail numerator draw partially in play. Moved to a **single hook at the entry of row 2**, `0x800B80A8` (the first read of the progress byte, originally `lui v0,0x800a`) → `j 0x800810C0`, resuming at `0x800B8258` (row 3's icon draw — confirmed independent, no register dependency on anything upstream). This means the cave now owns the *entire* row-2 draw (all 8 letter slots + the counter), and the original retail blocks for letters 1-4 and the original numerator draw (`0x800B821C`-`0x800B8258`) are bypassed entirely and never execute — so the earlier `hookA`/`hookB`/`hookC` patches are no longer needed at all (only the popcount-table fix at `0x800BE444` is still required, since it feeds the `s6` count-up-animation target used by retail code *after* the resume point).

A new 1-byte **WORDLEN** value at `0x800814A0` (placed just past the cave's own code, which ends at `0x80081488`, still inside the same verified ~0x400-byte boot-safe zero-run at `0x800810C0`) is read once into `s0` — a callee-saved register, so it safely survives the many `jal` calls in between, following the same convention the retail function already relies on for `s1`/`s6`/`s7`/`fp`.

- Each of the 8 letter slots is gated by `wordLen`: slot `i` is skipped **entirely** (not even drawn dim) when `wordLen <= i` — unlike the static version, which always drew all slots. Slot X = `8 + i*18`; tile-phase pattern (offset/OR-mask reusing F/L/I/K art) unchanged from the original retail design.
- The counter (numerator digit, `/`, denominator digit) is positioned at `X = 24 + wordLen*18`, `+20`, `+40` — computed at runtime from `s0` via shifts (`wordLen*18 = wordLen*16 + wordLen*2`), recomputed fresh before each of the 3 draws (not cached across the intervening `jal` calls, to avoid relying on caller-saved-register survival across function calls).
- Numerator value = `s6` (retail's existing, unchanged running collected-count register); denominator value = `s0` (wordLen) directly — both dynamic, no hardcoded targets anywhere in the new letter+counter path.

### Tuning iteration (operator-caught, fixed live)
First version used the letters' original pitch (20px) and a wider counter offset (base 40): worked for `FL` through `FLIK`/`FLIKF`/`FLIKFL`, but the operator caught (via screenshot) that `FLIKFLI` (7) and `FLIKFLIK` (8) pushed the counter far enough right to overlap the medal-icon column. Fixed by tightening letter pitch to 18px and shifting both the letter row and the counter's base offset left (base 40→24, plus letter base X 16→8) — confirmed via `gpu.pickObject` in the prior finding that the medal starts around x≈245-250, giving the margin needed.

### Verification — full requested test matrix, all 7 cases confirmed via native-resolution screenshots
For each word, set `WORDLEN=N` and the progress bitmask to `(1<<N)-1` (all N low bits set, so every visible letter shows collected/lit), then ran the full trigger→settle sequence and captured the native `displayed` framebuffer:

| Word | N | bitmask | Result |
|---|---:|---|---|
| `FL` | 2 | `0x03` | ✅ `2/2`, clear |
| `FLI` | 3 | `0x07` | ✅ `3/3`, clear |
| `FLIK` | 4 | `0x0F` | ✅ `4/4`, clear (medal fully revealed in this case) |
| `FLIKF` | 5 | `0x1F` | ✅ `5/5`, clear |
| `FLIKFL` | 6 | `0x3F` | ✅ `6/6`, clear |
| `FLIKFLI` | 7 | `0x7F` | ✅ `7/7`, clear of medal (previously overlapped, now fixed) |
| `FLIKFLIK` | 8 | `0xFF` | ✅ `8/8`, clear of medal (previously overlapped, now fixed) |

All 7 cases show the correct number of letters (no extra dim/idle slots beyond `N`), correctly reused F/L/I/K art, and a properly positioned, non-overlapping `N/N` counter. This was re-verified on a **freshly launched, distinctly-configured isolated instance** (`/tmp/duckstation-debugger-fresh`, port 23470) per operator request, after confirming only one DuckStation process was ever running (no actual conflict existed, but re-ran for certainty).

### Residual notes
- The medal-reveal gate (`0x800B8384`, still separate retail code after the resume point) was patched per-test-case to match `N` in this test harness; a real release should either make this dynamic too (same pattern as the rest) or explicitly accept it as a follow-up — it only affects the cosmetic medal icon, not the letters/counter.
- Still RAM-only; on-disc persistence remains the one open task (see below).

## Finding 8 — FLIK result/menu medal image source and shared-menu risk (2026-07-06)

Using the from-boot movie `collecting_FLIK_LEVEL01.movie.json` against `build/ABL_ALLMODS.cue`, the LEVEL COMPLETE FLIK coin is confirmed as a shared texture-page sprite, not the same in-level LEVEL01 glyph draw:

- Result screen frame: movie frame `9000`.
- `gpu.pickObject` native `(270,125)`:
  - sprite packet `0x801E2A38`
  - raw words `65400040 006400F0 3F798040 00400040`
  - texture page `x=640,y=256,mode=0`
  - UV `(64,128)`, size `64x64`
  - CLUT `x=912,y=253`
- The live VRAM page containing that source exactly matches `LEVEL00/LEVEL.RAW` chunk 3 and `LEVEL00/LEVEL2.RAW` chunk 1. Editing that chunk directly would change shared result-screen/menu FLIK coin art, not just Anthill.
- The LEVEL01 custom glyph is still resident at `x=720,y=0`, CLUT `x=784,y=215`; copying that tile and CLUT into the result destination works as a debugger-only VRAM mutation.

Failed runtime-hook attempts:
- A DAT-base-only hook at `0x80064618` (GPU linked-list DMA starter) fired during normal Anthill gameplay and corrupted a live texture page, producing a vertical custom-glyph strip in the level.
- A narrower packet-signature gate on `0x801E2A40 == 0x3F798040` still black-screened/crashed the guest by frame `9000`.
- Therefore no result-screen runtime hook is shipped. The unstable reference ASM is kept as `mod/mods/flik_result_emblem_experimental.asm` and deliberately not registered in `mod/mods/registry.py`.

Flik's Journey level-select top-right coin uses the same shared page but a different pre-scaled sprite:
- frame `9834`, native pick `(270,27)`
- packet `0x801CD8EC`, raw words `650006C4 00140100 3E7DC040 00180018`
- texture page `x=640,y=256,mode=0`, UV `(64,192)`, size `24x24`, CLUT `x=976,y=249`

Conclusion: the in-level LEVEL01 emblem replacement is solved as a level-local asset edit,
and the operator confirmed the LEVEL01 level-ending screen renders the uploaded emblem
correctly through that path. The Flik's Journey selector token is still separate shared
menu art and requires either a proven safer runtime hook point or a pre-scaled
level-specific source tile path; patching its shared source directly is not level-specific.

Active ALLMODS follow-up:
- The current shipped mod path no longer uses the broad shared-menu/Journey stager.
  `mod/mods.yaml` contains Training `flik_emblem` and `flik_emblem_training_result`
  entries for `LEVEL00/LEVEL.RAW`, `LEVEL00/LEVEL2.RAW`, and `LEVEL07/LEVEL1.RAW`,
  plus Anthill `flik_emblem`/`flik_emblem_level1` entries for `LEVEL01/LEVEL.RAW`
  and `LEVEL01/LEVEL1.RAW`. The Training result stager edits only the large result
  coin and avoids the tiny Journey spin-frame tiles.
- Training's `LEVEL00/LEVEL.RAW` chunk 3 edit is enabled again after the Training entry
  crash was isolated to the stale tutorial EXE cave path. The patched file is larger
  (`427083` bytes), so it must be built through the auto-layout manifest path.
- `tools/flik_emblem_edit.py` still has an explicit experimental shared-menu stager that can patch:
  - `LEVEL00/LEVEL2.RAW` chunk 1
  - large result coin rect `64,128,64,64`, CLUT slot 9
  - tiny Journey spin-frame rects `0,192,24,24`, `64,192,24,24`, and
    `112,192,24,24`, CLUT slot 13
- That stager remains registered as `flik_menu_result_emblems_level2` for manual experiments,
  but `tools/mod_studio_gui.py` no longer emits it from the Anthill upload field.
- Current rebuilt `build/ABL_ALLMODS.bin` after re-enabling the Training emblem:
  sha256 `3124e745191f640a26e7b312ca299218c48e2bf031479c984e6980c2c605569b`.

Current Training GUI path, 2026-07-06:
- The active Training emblem upload in `mod/mods.yaml` points to
  `~/Downloads/ABL/custom_emblems/TRAINING.png`.
- One Mod Studio picker fans out to the Training local badge/result copies:
  `LEVEL00/LEVEL.RAW`, `LEVEL00/LEVEL2.RAW`, `LEVEL07/LEVEL.RAW`, and
  `LEVEL07/LEVEL1.RAW`.
- The uploaded PNG has real alpha, not a green keyed background; the in-game and
  result copies use `preserve_transparent:true`, while the result copy also keeps
  `patch_palette:false` so it remains consistent with the in-game shared grayscale
  Training token CLUT.
- The RE rationale and live verification details are in
  [[Experiment - FLIK emblem image replacement]] and
  `src_re/flik_emblem_results_menu.c`.

Important caveat: the Journey token is a pre-rendered 2D sprite flipbook, not a 3D model.
The current confirmed fixtures (`collecting_FLIK_LEVEL01.movie.json` and
`collecting_flik.sav`) do not land on the post-completion Journey selector token frame in
the current build, so the token draw-site still needs a better fixture before a UV-selector
hook can be shipped.

## Finding 9 - TRAINING result row is now disc-persisted in BITS/MEMORY.BIN (2026-07-07)

`tools/training_word_pickups.py` now patches the on-disc overlay that owns the results
screen, `BITS/MEMORY.BIN`, instead of relying on the old RAM-only FLIKFLIK prototype.
The relevant overlay base is `0x800B5788`; the row-2 renderer replacement starts at
`0x800B80A8` and resumes retail row-3 code at `0x800B8258`.

Implementation:
- Row 2 is replaced by a compact loop that reads `0x800A65A2`, computes the
  collected-letter popcount inline, stores that count target at `0x800B8248`, and
  loads the staged active word length from `0x800B8249` into `s7`. `0x800BE444`
  is **not** scratch: Flik's Journey uses it for the level-select vine/leaf path,
  and the earlier popcount-table experiment there removed the visible vine.
- The slot tile table lives at `0x800B8250`, inside the replaced row block; the
  staged state bytes immediately before it are `count_target`/`word_len`.
- For `TRAINING`, the row uses the same tile ids as the in-world/SELECT word:
  `0x10,0x11,0x12,0x13,0x26,0x13,0x26,0x27`.
- The Training result RAW (`LEVEL00/LEVEL2.RAW`) now carries type-`0x22` spin-strip
  records for `0x10..0x13,0x26,0x27`. The row pumps every slot through
  `upload_anim_frame 0x80026DF4` with the same staggered phase pattern as the
  in-level letters before choosing the lit or dim draw path; uncollected letters
  therefore spin instead of freezing on one static face.
- The row also stamps descriptors `0x26/0x27` back to golden CLUT `0x3677`, because
  result-screen loading can drift those two extra descriptor CLUT halfwords.
- The visual layout is dynamic and tuned for the wider TRAINING glyphs:
  letter slots use `X = 8 + i*10`, while the counter uses
  `X = 8 + wordLen*10 + 88`, then numerator, slash, and denominator at
  `+0/+20/+40`. For TRAINING this puts the counter base at `176`, clear of both
  the tighter spinning row and the medal column.
- The row-2 medal paths at `0x800B8380` and `0x800B8388` jump to helper code at
  `0x800B81FC` / `0x800B8214`, so the medal gate uses `s7` when the row has run
  and falls back to retail length 4 in front-end contexts where `s7` is still zero.

Verification, final ALLMODS run:
- Build command: `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`.
- `build/ABL_ALLMODS.bin` SHA-256:
  `fe11deabc6b84a94c6a00d28081a34f6669c48d4e473dc46e7cf0a0b132bdc2a`.
- `build/training_word_BITS_MEMORY.BIN` SHA-256:
  `f8d447f30877987edbf5e0d58f2c79a8656ba449faf87199d8ccd1c6021ec276`.
- `build/training_word_LEVEL00_LEVEL2.RAW` SHA-256:
  `cc5937ae9de1f466e26c367a72180b96f7b379b31b496fe2d22e9e1d4ae54afe`.
- Isolated DuckStation config `/tmp/duckstation-debugger-training-dim-spin-final`,
  port `23727`, token `traindimfinal`, binary SHA-256
  `5538e0e0ca198b54f184ba5650e9a708ef4faf79b47180e49430e912fcc35448`.
- Movie `ALLMODS_COLLECTING_TRAINING.movie.json` SHA-256
  `fbc0ef077f5bcbd3f384e8d0a0f55871b47101d20e8db8481394c35b1a3615b7`;
  `movie.advanceToFrame` to target frame `7218` stayed reproducible and landed in
  scene `0x11` with `0x800A65A2=0xff`; frames `8000` and `8300` also stayed
  reproducible in the result overlay.
- At result frame `8000`, `anim_table[0x10]`, `anim_table[0x26]`, and
  `anim_table[0x27]` were nonzero, proving the result RAW spin-strip records were
  loaded. Live descriptors for `0x10,0x11,0x12,0x13,0x26,0x27` all carried CLUT
  `0x3677`.
- `execTrace` at row resume `0x800B8258` hit 776 times; first frame 7525 had
  `s0=0xB0`, `s6=0`, `s7=8`, and final frame 8300 had `s0=0xB0`, `s6=8`,
  `s7=8`. `execTrace` at the count-cap compare `0x800B853C` hit 640 times with
  `v0=8`; final frame 8300 had `s6=8`, `v0=8`, `s7=8`, proving the counter stops
  at the collected-letter count.
- Captures `/tmp/traindimfinal/result_8000.png` and
  `/tmp/traindimfinal/result_8300.png` show the tighter staggered spinning
  TRAINING row clear of the capped `8/8` counter. Capture SHA-256 values:
  frame 8000 `ae2557573bf5dd02cfc6c474724bdae05c8b4faf95faae5f64c5b3242cecca0d`;
  frame 8300 `8211d6577cf54e3c651e477e85b37355eae7960c23dbbb84318e1526bb8ffb78`.
- Forced-uncollected visual check used isolated config
  `/tmp/duckstation-debugger-training-dim-spin`, port `23726`, token
  `traindimspin`: after reaching result frame `8000`, writing
  `0x800A65A2=0x00` produced result state bytes `00 08` and captures
  `/tmp/traindimspin/dim_a.png`, `dim_b.png`, and `dim_c.png` with different
  dim TRAINING spin phases. SHA-256 values:
  `4668ae0a4547269e24b7494b0f5fceed34f7276b94bb8801b87110bf10c44436`,
  `913942ee28b9535d47ab9e61c0cb7be1d175772b115f44d4fc4dd7590535743f`,
  `3a86ca8a84d05f675f0811cbd8ccf42bdb34aa34118811562b44c77eba2f92f4`.
- Front-end Start-spam regression check used isolated config
  `/tmp/duckstation-debugger-training-dim-front`, port `23728`, token
  `traindimfront`; capture `/tmp/traindimfront/front_359.png` SHA-256
  `d8ab3579f8cff4588c8401844c4919716d17ef69035a734775192ba0d5a78f4e`
  shows Flik's Journey with the vine/level path visible.
