# Experiment Log — A Bug's Life LEVEL01 DAT modding

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

Chronological record of LEVEL01 DAT modding experiments, including failed/superseded hypotheses (kept and clearly marked). Confirmed conclusions are summarized in the topical docs ([COORDINATE_MODDING.md](COORDINATE_MODDING.md), [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md), [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md)) and the [index](../ABL_RE_NOTES.md).

## Superseded hypotheses & confirmed root cause (quick index)
- **Superseded hypothesis: `0x21..0x24` as harmless FLIK markers** → actually special berries; see "FLIK TEST RESULT — FAILED", "RECLASSIFICATION — entries 54..57 are special berry…", and the berry move tests below.
- **Superseded hypothesis: append failure caused by seed-token total 9 → 10** → disproven by the non-token append (clone of kind 0x21) reproducing the same black screen; see "NON-TOKEN APPEND DIAGNOSTIC".
- **Superseded hypothesis: a global 70-entry / type-0x3f cap** → disproven by cross-level retail scan (levels with >70 entries) and by the successful relocation-aware append.
- **Confirmed root cause: stale internal DAT relocation offsets** (naive +0x10 shift left 1248 baked file offsets pointing 0x10 short) → see "ROOT CAUSE FOUND" (moved to [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md)) and "RELOCATION-AWARE TRUE APPEND CONFIRMED".

## FLIK letter coordinate tests (chronological)
### FLIK coordinate mapping pass C1-C4 (candidate; first LEVEL01 path)
Starting point: FLIK HUD pointers are `0x800a0220`, `0x800a0430`, `0x800a0a60`, `0x800a0d78`;
HUD collected flag is record `+0x1b`; `0x800a6597` is the active FLIK marker/state byte (values 1..4).

Medium grain test status:
- `ABL_GRAIN_MEDIUM_TEST.cue` is in-game VERIFIED.
- Task A (playable LEVEL01 grain-position mod): COMPLETE.
- Task B (cross-level grain coordinate tables): COMPLETE.
- Grain-count anomalies for LEVEL00/LEVEL04/LEVEL06/LEVEL08 remain documented and DEFERRED.

FLIK collection/action cases:
- `fcn.800586b0` contact walker uses the 64-record array at `0x800b0d18` and dispatches on
  record `+0x20`:
  - loads `lh record+0x20`
  - subtracts 2
  - jump table at `0x8001b570`
- FLIK walker cases:
  - record `+0x20 = 0x21` -> `0x80058940`: sets `0x800a6597 = 2`, plays event/sound `0x36`
  - record `+0x20 = 0x22` -> `0x80058954`: sets `0x800a6597 = 3`, plays `0x38`
  - record `+0x20 = 0x23` -> `0x80058968`: sets `0x800a6597 = 1`, plays `0x35`
  - record `+0x20 = 0x24` -> `0x80058978`: sets `0x800a6597 = 4`, plays `0x37`
  - common tail calls `fcn.80050994`, sets short active/status fields, and calls `fcn.8005044c`.
- Duplicate/source-side cases in `fcn.80053814`:
  - source kind `0x20` -> `0x80054288`: clears `0x800a6597`, event `-3`
  - source kind `0x21` -> `0x80054298`: sets marker 2, event `0x36`
  - source kind `0x22` -> `0x800542ac`: sets marker 3, event `0x38`
  - source kind `0x23` -> `0x800542c0`: sets marker 1, event `0x35`
  - source kind `0x24` -> `0x800542d4`: sets marker 4, event `0x37`

Metadata table candidates:
- Metadata base: `0x8007941c`, stride `0x14`.
- Constructor copies metadata fields into runtime record:
  - table `+0x00` -> record `+0x20`
  - table `+0x02` -> record `+0x22`
  - table `+0x0c` -> record `+0x2c`
  - table `+0x10` -> record `+0x33`
- FLIK-like metadata rows:
  - type `0x20`: `+00=0x0024`, `+02=0x00e6`, `+0c=0x0007`, `+10=0xe2`
  - type `0x21`: `+00=0x0021`, `+02=0x00e6`, `+0c=0x0007`, `+10=0xe2`
  - type `0x22`: `+00=0x0022`, `+02=0x00e6`, `+0c=0x0007`, `+10=0xe2`
  - type `0x23`: `+00=0x0023`, `+02=0x00e6`, `+0c=0x0007`, `+10=0xe2`
- Inference: constructor types `0x20..0x23` are FLIK-like contact records. Source kinds `0x21..0x24`
  are the DAT-side FLIK placement candidates; source kind `0x24` likely maps to metadata type `0x20`
  because that metadata row supplies record `+0x20 = 0x24`.
- This is strong but still labelled CANDIDATE until a rebuilt FLIK coordinate patch is tested in-game.

DAT-side FLIK candidate tool:
- Script: `tools/list_level_flik.py`
- Usage:
  `python tools/list_level_flik.py DAT/LEVEL01_LEVEL.DAT --dy -512`
- It parses type-`0x3f` records and prints source-kind `0x21..0x24` candidate FLIK rows with X/Y/Z,
  Y file offset, marker value, and patch bytes.

LEVEL01 `LEVEL.DAT` candidate FLIK rows:
| source kind | marker | raw entry | entry off | Y off | X | Y | Z | Y bytes | Y-512 bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `0x22` | 3 | 54 | `0x000368` | `0x00036c` | 8587 | -350 | 13249 | `a2 fe ff ff` | `a2 fc ff ff` |
| `0x23` | 1 | 55 | `0x000378` | `0x00037c` | 4110 | 0 | 1794 | `00 00 00 00` | `00 fe ff ff` |
| `0x21` | 2 | 56 | `0x000388` | `0x00038c` | 3737 | 0 | 22656 | `00 00 00 00` | `00 fe ff ff` |
| `0x24` | 4 | 57 | `0x000398` | `0x00039c` | 7661 | -400 | 16692 | `70 fe ff ff` | `70 fc ff ff` |
- LEVEL01 normal file has exactly 4 candidate FLIK placements.
- `DAT/LEVEL01_LEVEL1.DAT` has only 2 candidate FLIK rows; treat variant differences as deferred.

First FLIK coordinate mod recipe and rebuilt test image:
- Target file: `DAT/LEVEL01_LEVEL.DAT` / disc path `LEVEL01\LEVEL.DAT`
- Patched DAT: `DAT/LEVEL01_LEVEL_FLIK0_UP_MEDIUM.DAT`
- Record type: `0x3f`
- Candidate FLIK row: source kind `0x23`, marker 1
- Raw entry index: 55
- Entry offset: `0x000378`
- Coordinates: X=4110, Y=0, Z=1794
- Vertical axis: Y; upward = decrease Y.
- Patch Y s32 at file offset `0x00037c`.
- Original Y bytes: `00 00 00 00` (Y=0)
- Suggested moderate upward patch: `Y - 512` -> Y=`-512`
- Patched Y bytes: `00 fe ff ff`
- Expected runtime delta: `-512 << 5 = -16384`
- Rebuild workspace target replaced: `REBUILD/files/LEVEL01/LEVEL.DAT`
- Build command:
  `mkpsxiso -y -o ABL_FLIK_TEST.bin -c ABL_FLIK_TEST.cue REBUILD/abl.xml`
- Output:
  - `ABL_FLIK_TEST.bin`
  - `ABL_FLIK_TEST.cue`
- Verification:
  - original DAT `DAT/LEVEL01_LEVEL.DAT` at `+0x00037c` remained `00 00 00 00`
  - patched DAT `DAT/LEVEL01_LEVEL_FLIK0_UP_MEDIUM.DAT` at `+0x00037c` = `00 fe ff ff`
  - patched DAT size matches original (`332824`)
  - original image `LEVEL01/LEVEL.DAT;1` at LBA 2906, file `+0x00037c` = `00 00 00 00`
  - `ABL_FLIK_TEST.bin` `LEVEL01/LEVEL.DAT;1` at LBA 2906, file `+0x00037c` = `00 fe ff ff`
  - `ABL_GRAIN_MEDIUM_TEST.bin` still has `00 00 00 00` at this FLIK candidate offset
  - image size is `738285744` bytes, matching the original and prior rebuilt image sizes.
- Mapping status: still CANDIDATE until `ABL_FLIK_TEST.cue` is verified in-game.
- Test expectation: one LEVEL01 FLIK letter should move upward; walking beneath should not collect it,
  jumping or reaching the moved letter should set the corresponding FLIK state/collection behavior.

### FLIK TEST RESULT — FAILED / INCONCLUSIVE (DOWNGRADE 0x21..0x24)
`ABL_FLIK_TEST` (kind-0x23 entry, Y 0→-512 / runtime -16384) did **NOT** produce a confirmed visible
or collectible FLIK movement in-game. Patch presence re-verified at image LBA 2906 file `+0x37c` =
`00 fe ff ff` (orig `00 00 00 00`), so the byte edit DID land. The mapping is therefore wrong, not the
build. **Downgrade DAT source kinds `0x21..0x24` from "strong candidate" to UNVERIFIED candidate.**
Kept evidence (still valid): FLIK HUD confirmed; FLIK marker `0x800a6597` confirmed; collection/action
cases `0x80054288..0x800542d4` and `0x80058930..0x80058980` remain relevant. The candidate table above
is retained but marked FAILED/inconclusive.

**Root-cause analysis (binary evidence):** the contact/pickup pass `fcn.80053814` reads each type-0x3f
entry's source-kind byte at `entry+0xc` (`lbu [s2+8]`, s2=entry+4) and dispatches via jump table
**`0x8001b42c`** indexed by `(kind-0x10)`. For the FLIK kinds `0x20..0x24` the jump-table targets are
**pickup ACTIONS ONLY** — they just `sb 0x800a6597 = 0/2/3/1/4` and play a sound (`jal 0x80050994`),
with **no `fcn.80059e44` visible-entity construction**. Grain `0x14`, by contrast, has a *dedicated*
construct at `0x80053c00` (`jal fcn.80059e44`, ctor type `0x51`) that writes X/Y/Z<<5 into the
`0x800b0d18` render array → that is why moving grain moved a *visible* object. So `0x21..0x24` are
**pickup-trigger points, not the visible letter sprite** → moving them moves only the (invisible)
trigger, which is hard to observe. Hypotheses #4/#6 (contact-vs-visible separation) CONFIRMED.

### NEW PRIME FLIK CANDIDATE — source kinds 0x10,0x11,0x12,0x13 (proximity + count evidence)
User screenshot: the visible yellow **F** letter sits right next to the verified moved grain 0. Spatial
search (`tools/nearby_level_entries.py`, anchor = grain 0 `(-8526,-3488,4544)`, `DAT/LEVEL01_LEVEL.DAT`
type-0x3f) shows:
- **Nearest non-grain entry = idx 50, kind `0x10`, XYZ `(-8616, 0, 4601)`, dist 3490** — nearly
  identical X/Z to grain 0; Y=0 (below the up-moved grain). = prime suspect for the visible **F**.
- Exactly **four** entries of kinds `0x10/0x11/0x12/0x13` exist (idx 50/51/52/53), scattered across the
  level — a clean "4 FLIK letters" match. Each has its **own distinct** jump-table handler
  (`0x80053d04 / 0x80053e64 / 0x80053fc0 / 0x8005411c`), unlike the shared-tail 0x20..0x24 actions.
- The failed `0x23` entry (idx 55) ranks only **#25 (dist 13394)** from grain 0 — far from the F.
- Kind `0x10` is `<0x30` and `!=0x14`, so it is ALSO eligible for the type-`0x71` visible construction
  at `fcn.80053814 0x80053b24` (gated by `(kind&3)==[0x800910a4]`). Its contact handler `0x80053d04`
  animates the object (osc 0x400 at 0x800b0188/0x0194), reads player pos, increments state `0x800a65a0`.
- **NEXT TEST: move kinds 0x10..0x13 Y up by a large delta in `LEVEL01\LEVEL.DAT` and check if the
  visible F (and other letters) rise.** If yes → 0x10..0x13 = visible FLIK letters (the real coordinate
  source). Tool: `tools/nearby_level_entries.py`, patcher: `tools/patch_level_entry.py`.

### DIAGNOSTIC TEST IMAGE — ABL_FLIK10_BIG_TEST (kinds 0x10..0x13, awaiting in-game result)
Built to test the new candidate. Moves all four kind-0x10..0x13 entries up by a large amount.
- Input DAT: `DAT/LEVEL01_LEVEL.DAT`; patched DAT: `DAT/LEVEL01_LEVEL_FLIK10_UP_BIG.DAT`
- Patch: kinds `0x10/0x11/0x12/0x13` (idx 50/51/52/53), `--dy -2048` file units = runtime Y `-65536`.
  - idx 50 (0x10) Yoff `0x32c`: `00 00 00 00` -> `00 f8 ff ff`  (the F, next to grain 0)
  - idx 51 (0x11) Yoff `0x33c`: `ce ff ff ff` -> `ce f7 ff ff`
  - idx 52 (0x12) Yoff `0x34c`: `ce ff ff ff` -> `ce f7 ff ff`
  - idx 53 (0x13) Yoff `0x35c`: `ce ff ff ff` -> `ce f7 ff ff`
- Build: `mkpsxiso -y -o ABL_FLIK10_BIG_TEST.bin -c ABL_FLIK10_BIG_TEST.cue REBUILD/abl.xml`
- Output: `ABL_FLIK10_BIG_TEST.bin` / `.cue` (738285744 bytes).
- Verified in image @ LBA 2906: `+0x32c=00f8ffff`, `+0x33c/34c/35c=cef7ffff`; grain0 `+0x00c=60f2ffff`
  (original, so grain is NOT moved in this image — isolates the FLIK candidate).
- EXPECTED if 0x10..0x13 are the letters: the visible **F** (and the other 3) float high in the air.
- INTERPRETATION:
  - F moves up  => kind 0x10 = visible F; 0x10..0x13 = FLIK letter coordinate source. SOLVED.
  - F unchanged but pickup point moves => visible letter is a separate record (not type-0x3f coords).
  - nothing moves => 0x10..0x13 not the source either; look outside type-0x3f.

### ABL_FLIK10_BIG_TEST RESULT — FAILED but DIAGNOSTIC (kinds 0x10..0x13 = the FLIK letters)
In-game result of moving kinds `0x10/0x11/0x12/0x13` Y up by `-2048` file units (runtime `-65536`):
- **F letter MISSING entirely** (scavenged whole level, not found, not collectible).
- **I / L / K still collected, but AUTO-COLLECT from a distance** (Flik merely near the area, several
  feet away; persists after level reboot) — a proximity/contact-volume symptom.
- **Results screen = `3/4`** (I/L/K counted, F not). Game still tracks FLIK progress.
- CONCLUSION: kinds `0x10..0x13` ARE the four FLIK letter records (moving them changed all four letters'
  behavior). The huge `-65536` runtime Y delta is what broke them, NOT a wrong file/record. So
  `0x10..0x13` is the RIGHT family; the delta and possibly a visible/contact coupling are the problem.
- IMPORTANT correction to the prior round's task framing: the failed image patched `0x10..0x13`, not
  `0x21..0x24`. (The earlier single-entry `ABL_FLIK_TEST` had patched kind `0x23` and did nothing.)
- Symptom mechanism (see contact-walker analysis below): the contact distance weights Y ~1/3 of X/Z, so
  a large upward move turns each letter's pickup zone into a tall vertical cylinder → collect-from-below.
- DOWNGRADE `0x21..0x24`: re-describe as **FLIK contact/action TRIGGER candidates**, NOT confirmed
  visible coordinate records (they only `sb 0x800a6597` + sound; no visible construct). Grain results
  remain CONFIRMED. LEVEL00/04/06/08 grain anomalies remain DEFERRED.

### FLIK SYSTEM — RESOLVED MODEL (kinds 0x10..0x13 = F/L/I/K; contact math decoded)
**Letters = DAT type-0x3f source kinds 0x10/0x11/0x12/0x13** (LEVEL01\LEVEL.DAT idx 50/51/52/53).
Their per-kind handlers in `fcn.80053814` each set ONE bit of a collected-bitmask, then run a shared
bob animation (osc `0x800b0194` between +0x400/-0x400):
- kind 0x10 -> `0x80053d04`: `ori [s3],1`  (bit0)  + EXTRA logic: `bne [s3],0xf`, reads player pos
  0x800a6500/04/08, writes 0x800b3988..0x3998, increments progress `0x800a65a0` (<9). = **F** (anomalous).
- kind 0x11 -> `0x80053e64`: `ori [s3],2`  (bit1).  = one of L/I/K.
- kind 0x12 -> `0x80053fc0`: `ori [s3],4`  (bit2).
- kind 0x13 -> `0x8005411c`: `ori [s3],8`  (bit3).
So 0x10..0x13 are the four letters; F (0x10) has unique extra handling → why F alone broke/vanished
when displaced while L/I/K only mis-behaved. Visible letter and pickup are the SAME type-0x3f record
(moving idx50 removed F visually AND broke its pickup) — NOT separate records. All-records spatial scan
finds no separate discrete F record near grain 0 (the only nearby placement entry is idx 50 itself; the
0xffff "entries" are misparsed level-geometry vertices, not records).

**Contact walker `fcn.800586b0` — exact math (NEW, supersedes earlier partial):**
- Array `0x800b0d18`, 64 records × stride `0x38`. Live gate: `record[+0x22] > 0` AND `record[+0x33] & 2`.
- Player: X=`[0x800a6500]`, **Y=`[0x800a6504] − 0x1cc0`** (−7360 vertical offset), Z=`[0x800a6508]`.
- `dx = (pX−recX)·0x300 >> 13`,  **`dy = (pY−recY)·0x100 >> 13`**,  `dz = (pZ−recZ)·0x300 >> 13`.
  → Y is weighted **0x100 vs 0x300 = ONE THIRD** of horizontal. recX/Y/Z at `+0x00/+0x04/+0x08`.
- Collect when `dx²+dy²+dz² < (0x12c + record[+0x28])²`  →  **contact radius = 300 + `record[+0x28]`**
  (per-record halfword). On hit, dispatch on `record[+0x20]` (lhu, −2, idx<0x75) via table `0x8001b570`.

**WHY auto-collection happened (root cause):** moving the letters up by runtime −65536 put recY far
above the player. Because dy is weighted 1/3, the vertical term `dy = (pY−recY)/32 ≈ 65536/32 = 2048`,
`dy² ≈ 4.19M`. The letters' contact radius (300+rec[+0x28]) is large enough that, with the letter high
overhead, the pickup zone became a tall vertical CYLINDER reaching the ground — so standing anywhere
near the letter's XZ column (small dx,dz) collects it from far below = "auto-collect from several feet
away." F (kind 0x10) likely has a smaller radius and/or its extra handler logic disabled it, so its
cylinder didn't reach the ground → F unreachable + pushed out of view → "missing", result 3/4.

**Mapping confidence now:**
- DAT type-0x3f source kinds `0x10..0x13` = the four FLIK letters (placement + visible + contact): HIGH
  (the test moved all four letters' behavior). F = `0x10`.
- DAT source kinds `0x21..0x24` = separate pure trigger/marker actions (set 0x800a6597), NOT the letters:
  re-labeled FLIK contact/action TRIGGER candidates. The earlier `0x23` single-entry test did nothing
  because it is not a letter placement.
- Runtime record `+0x28` = contact-radius addend; `+0x20` = action id; `+0x22` active; `+0x33`&2 enable.

**SAFE FLIK MOD PLAN (no rebuild yet — for the NEXT test):**
1. Do NOT move kind 0x10 (F) until its extra handler/anomaly is isolated.
2. Move exactly ONE letter, kind 0x13 (K, idx 53) or 0x12 (I, idx 52), by a SMALL delta:
   `--dy -128` (runtime −4096) — comparable to the grain MEDIUM that worked, but smaller, to avoid the
   tall-cylinder effect. Expect: letter rises a little, still must be (jump-)touched, no auto-collect.
3. If auto-collect persists even at small Δ, the radius is the culprit → also reduce `record[+0x28]`
   (needs the metadata/ctor row for these letters; trace ctor type for source kind 0x13).
4. Keep grain 0 unpatched in FLIK tests to isolate the variable.
- Tool: `tools/patch_level_entry.py DAT/LEVEL01_LEVEL.DAT --entries 53 --dy -128 --out <out>` (single entry).

### SAFE SINGLE-LETTER TEST — ABL_FLIK_K_SMALL_TEST (BUILT, awaiting in-game result)
First conservative FLIK test after the overlarge failure. Moves ONE letter a small amount.
- CONFIRMED facts reused: grain mod confirmed/playable; type-0x3f source kind 0x14 = grain; 0x10..0x13 =
  the four FLIK letters (0x10=F w/ extra logic); 0x21..0x24 = trigger/marker actions (NOT letters);
  contact walker fcn.800586b0 underweights Y (dy·0x100 vs dx/dz·0x300), radius=300+rec[+0x28].
- FAILED/diagnostic: ABL_FLIK10_BIG_TEST moved all four letters by runtime -65536 → F vanished,
  I/L/K auto-collected (tall-cylinder effect), result 3/4. Root cause = overlarge Y + weak-Y contact.
- THIS safe test (single letter, small delta):
  - Input: `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, 332824 B, UNCHANGED by this work).
  - Entry 53, source kind 0x13 (= K candidate), entryoff `0x358`, Yoff `0x35c`.
  - Y: `-50` (`ce ff ff ff`) → `-178` (`4e ff ff ff`); `dy -128` file = runtime `-4096`. ONE byte changed (0x35c).
  - Output DAT: `DAT/LEVEL01_LEVEL_K_UP_SMALL.DAT` (332824 B; diff = entry53 Y only; X/Z/kind, entries
    50/51/52, grain0, all other 0x14 grain entries: UNCHANGED).
  - Image: `ABL_FLIK_K_SMALL_TEST.bin` / `.cue`. Verified @ LBA 2906: e53 Y `4effffff` (orig `ceffffff`);
    e50/51/52, grain0, e53 X/Z all == original. Workspace LEVEL.DAT restored to pristine after build.
  - EXPECT in-game: only K rises slightly; F unchanged (not patched); no auto-collect from afar; K still
    needs normal/jump contact; no crash. IF K still auto-collects at this small Δ → next step is to trace
    source-kind-0x13 constructor/runtime metadata (record `+0x28` radius), NOT to patch radius yet.
- DEFERRED (untouched): LEVEL00/04/06/08 grain anomalies; F (kind 0x10); multi-letter moves; radius edits.

### ABL_FLIK_K_SMALL_TEST RESULT — SUCCESS (in-game confirmed) → 0x13 = K
In-game (user): "Only K moved up slightly, no auto-collect, F fine. Able to collect the rest without
proximity issues."
- CONFIRMED: small single-letter coordinate mod is HEALTHY. `dy -128` (runtime -4096) on one letter
  moves it slightly with NO auto-collection pathology and no effect on other letters / F / grain.
- CONFIRMED GLYPH MAPPING: **source kind `0x13` = letter K** (entry 53). (F = `0x10`, already known.)
  Remaining: `0x11` and `0x12` = the other two letters (I and L, order UNKNOWN) — to be confirmed.
- This validates the method: per-letter Y patch at file offset entry+0x4, `dy -128` is a safe step size.
- METHODOLOGY NOTE: the earlier failure was purely the overlarge -65536 delta + weak-Y contact; small
  deltas are safe. Radius (record[+0x28]) editing remains UNNEEDED and deferred.

### NEXT TEST — ABL_FLIK_KIND12_SMALL_TEST (kind 0x12, entry 52; BUILT, awaiting in-game result)
Same conservative single-letter recipe to identify the kind-0x12 glyph.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, 332824 B, UNCHANGED).
- Entry 52, source kind 0x12, entryoff `0x348`, Yoff `0x34c`. Y `-50` (`ce ff ff ff`) → `-178`
  (`4e ff ff ff`); `dy -128` file = runtime `-4096`. One byte changed (0x34c).
- Output DAT `DAT/LEVEL01_LEVEL_KIND12_UP_SMALL.DAT`; image `ABL_FLIK_KIND12_SMALL_TEST.bin`/`.cue`.
- EXPECT: only the kind-0x12 letter rises slightly; F/K/other letter unchanged; no auto-collect; normal
  pickup; result still 4/4 collectible; no crash. Observe WHICH glyph moves → fixes `0x12 = I or L`.

### ABL_FLIK_KIND12_SMALL_TEST RESULT — SUCCESS (in-game confirmed) → 0x12 = I
In-game (user): "KIND12_SMALL passed. F/L/K fine and collectable. I is raised and collectable. No
auto-collect from a distance."
- CONFIRMED GLYPH: **source kind `0x12` = letter I** (entry 52). Small `dy -128` method healthy on a
  2nd non-F letter (no auto-collect, others unaffected, no crash).
- FLIK letter map now: **`0x10`=F (deferred), `0x12`=I, `0x13`=K**; **`0x11`=L by elimination**
  (direct in-game confirmation still pending — see next test).

### NEXT TEST — ABL_FLIK_KIND11_SMALL_TEST (kind 0x11, entry 51; BUILT, awaiting in-game result)
Final non-F single-letter test, to directly confirm the remaining glyph (expected L).
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, 332824 B, UNCHANGED).
- Entry 51, source kind 0x11, entryoff `0x338`, Yoff `0x33c`. Y `-50` (`ce ff ff ff`) → `-178`
  (`4e ff ff ff`); `dy -128` file = runtime `-4096`. One byte changed (0x33c).
- Output DAT `DAT/LEVEL01_LEVEL_KIND11_UP_SMALL.DAT`; image `ABL_FLIK_KIND11_SMALL_TEST.bin`/`.cue`.
- EXPECT: only the kind-0x11 letter rises slightly (expected glyph L); F/I/K unchanged; no auto-collect;
  normal pickup; 4/4 completable; no crash. If raised glyph ≠ L, record actual glyph and correct the map.

### ABL_FLIK_KIND11_SMALL_TEST RESULT — SUCCESS (in-game confirmed) → 0x11 = L
In-game (user): "KIND11_SMALL passed. L is raised. The test behaved normally."
- **FLIK GLYPH MAP COMPLETE (all confirmed in-game):** `0x10`=F, `0x11`=L, `0x12`=I, `0x13`=K.
- Non-F small single-letter Y method (`dy -128`, runtime -4096) = HEALTHY for all three non-F letters
  (L/I/K): only the targeted letter moves, no auto-collect, others unaffected, 4/4 completable, no crash.
- F coordinate movement remains UNTESTED directly (F = 0x10 has extra handler logic; it was the only
  letter that vanished in the overlarge all-letter failure). Next: a conservative F-only test.

### NEXT TEST — ABL_FLIK_F_TINY_TEST (kind 0x10 / F, entry 50; BUILT, awaiting in-game result)
First-ever F coordinate test, deliberately SMALLER than the non-F tests (F has extra logic).
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, 332824 B, UNCHANGED).
- Entry 50, source kind 0x10 = F, entryoff `0x328`, Yoff `0x32c`. Y `0` (`00 00 00 00`) → `-64`
  (`c0 ff ff ff`); `dy -64` file = runtime `-2048`. (Multi-byte change since orig Y=0, unlike the -50 letters.)
- Output DAT `DAT/LEVEL01_LEVEL_F_UP_TINY.DAT`; image `ABL_FLIK_F_TINY_TEST.bin`/`.cue`.
- EXPECT if F tolerates a small move: only F rises slightly; L/I/K unchanged; no auto-collect; normal
  pickup; F still counts; 4/4 completable; no crash; F does NOT vanish/become unfindable.
- IF F vanishes/unreachable/miscounts/breaks results: do NOT patch coords again — investigate F's 0x10
  extra handler (0x80053d04: bne[s3],0xf; player-pos write 0x800b3988; progress 0x800a65a0) + F runtime
  metadata. If F is healthy at -64, the next step would be a -128 comparability test (only after result).

### NEXT TEST — ABL_FLIK_F_MORE_TEST (kind 0x10 / F, entry 50, larger raise; BUILT, awaiting result)
User asked to raise F more and wants to verify whether the nearby GRAIN appears to rise too. F (entry 50,
X=-8616,Z=4601) and grain 0 (entry 0, X=-8526,Z=4544) share nearly the same XZ column → a raised F can
LOOK like a raised grain. This test isolates that: ONLY entry 50 (F) Y is changed; grain 0 is proven
byte-identical to the ORIGINAL disc image.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Entry 50 kind 0x10, entryoff `0x328`,
  Yoff `0x32c`. Y `0` (`00 00 00 00`) → `-256` (`00 ff ff ff`); `dy -256` file = runtime `-8192`.
- Output DAT `DAT/LEVEL01_LEVEL_F_UP_MORE.DAT`; image `ABL_FLIK_F_MORE_TEST.bin`/`.cue`.
- Verification REQUIREMENT: grain 0 (`0x00c`) in the rebuilt image == original image (`60 f2 ff ff`),
  and entries 51/52/53 unchanged → if the grain still appears to move in-game, it is VISUAL proximity
  to F (or runtime coupling in F's 0x10 handler), NOT a grain-data change.
- EXPECT: only F rises (more than the tiny test); grain 0 stays put; L/I/K unchanged; ideally no
  auto-collect, normal pickup, 4/4, no crash. Watch whether F now disappears/auto-collects at this bigger Δ.
- RESULT (user, ABL_FLIK_F_MORE_TEST): grain confirmed NOT moved → grain data is independent of F.
  (Earlier "grain looks raised" was visual proximity of F to grain 0's column.)

### NEXT TEST — ABL_FLIK_F_SIDE_TEST (kind 0x10 / F, entry 50, HORIZONTAL move; BUILT, awaiting result)
Purpose: definitively prove F and grain 0 are separate objects by moving F SIDEWAYS (X axis). If F shifts
laterally and the grain stays in its column, they are independent. Horizontal axes are full-weight in the
contact math (dx·0x300), so no auto-collect pathology from this move.
- Tool now supports --dx/--dy/--dz (each runtime = file<<5).
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Entry 50 kind 0x10, X@`0x328`.
  X `-8616` (`58 de ff ff`) → `-8104` (`58 e0 ff ff`); `dx +512` file = runtime `+16384`. Y/Z UNCHANGED.
- Output DAT `DAT/LEVEL01_LEVEL_F_SIDE_TEST.DAT`; image `ABL_FLIK_F_SIDE_TEST.bin`/`.cue`.
- EXPECT: F appears shifted to one side (off the grain column); grain 0 unchanged; L/I/K unchanged;
  F still collectable; 4/4; no crash. Confirms F-object independence from grain. (If F ends up in a wall/
  unreachable, retry opposite direction — report and I'll flip the sign.)

### ABL_FLIK_F_SIDE_TEST RESULT — SUCCESS (in-game confirmed): F ⟂ grain
In-game (user): "Grain stayed in place. F moved to the side, and downwards. F collectable. 4/4. No crash."
- CONFIRMED: F and grain 0 are SEPARATE in-game objects. The X-only patch moved F laterally; grain 0
  unchanged. F remained collectable; FLIK 4/4; no crash; F's special 0x10 logic not broken by the move.
- CONFIRMED: F horizontal X movement is healthy at `dx +512` (runtime +16384).
- OBSERVATION (NOT a data fact): user saw F also shift "downwards." The built patch changed entry 50 X
  ONLY (Y stayed file 0, Z stayed original, grain 0 byte-identical) — verified. So the apparent downward
  shift is a VISUAL/RUNTIME effect (camera perspective, terrain/slope grounding, sprite anchor, or F's
  0x10 render logic), NOT a Y-coordinate data change. Cause UNKNOWN — do not claim which without evidence.

### NEXT TEST — ABL_FLIK_F_Z_SIDE_TEST (kind 0x10 / F, entry 50, Z-axis only; BUILT, awaiting result)
Purpose: move F on Z only (X & Y pristine) to see if the "downwards" visual recurs on the other
horizontal axis → helps separate data-move vs visual/runtime grounding effect.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Entry 50 kind 0x10, Z@`0x330`.
  Z `4601` (`f9 11 00 00`) → `5113` (`f9 13 00 00`); `dz +512` file = runtime `+16384`. X & Y UNCHANGED.
- Output DAT `DAT/LEVEL01_LEVEL_F_Z_SIDE_TEST.DAT`; image `ABL_FLIK_F_Z_SIDE_TEST.bin`/`.cue`.
- EXPECT: F shifts along depth axis; grain 0 stays; L/I/K unchanged; F collectable; 4/4; no crash; no
  auto-collect. WATCH: does F again appear "downwards" despite Y unchanged? (would reinforce visual/slope
  explanation). If pass → F horizontal movement confirmed on BOTH X and Z axes.

### ABL_FLIK_F_Z_SIDE_TEST RESULT — SUCCESS (in-game confirmed)
In-game (user, + screenshot): "Worked again. F is still down to the right/left depending on view. Initial
F location is on the mushroom near the grain, but now F is down here."
- CONFIRMED: F Z-axis movement healthy at `dz +512` (runtime +16384); F collectable; grain independent.
- F horizontal movement now confirmed on BOTH X and Z axes.
- REPEATED OBSERVATION (NOT a data fact): F again appears LOWER/sideways even though the Z-only patch left
  Y pristine (file 0; verified X/Y unchanged, grain0 byte-identical). So the apparent drop is a
  VISUAL/RUNTIME effect, not a DAT Y change. Likely categories (UNKNOWN which): terrain/slope grounding,
  camera/perspective, floor/grounding snap, sprite anchor, or F-specific 0x10 render/runtime logic.
  Original F sits ON a mushroom near the grain; moving F off that surface may drop its apparent rest height.

### NEXT TEST — ABL_FLIK_F_Z_SIDE_UP_TEST (entry 50/F, Z-side + Y-up compensation; BUILT, awaiting result)
Goal: test whether an explicit upward DAT Y offset corrects the apparent low placement from the Z-side
move. Combines two deltas that ALREADY passed individually. F/entry50 only; grain & L/I/K untouched.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Entry 50 kind 0x10:
  - Z@`0x330`: `4601` (`f9 11 00 00`) → `5113` (`f9 13 00 00`); `dz +512` = runtime +16384 (repeats Z-side).
  - Y@`0x32c`: `0` (`00 00 00 00`) → `-256` (`00 ff ff ff`); `dy -256` = runtime -8192 (from F_MORE pass).
  - X@`0x328`: UNCHANGED (`58 de ff ff`).
- Output DAT `DAT/LEVEL01_LEVEL_F_Z_SIDE_UP_TEST.DAT`; image `ABL_FLIK_F_Z_SIDE_UP_TEST.bin`/`.cue`.
- EXPECT: F still shifted off the mushroom column (Z), now raised higher than the Z-only test (Y up);
  grain stays; L/I/K unchanged; F collectable; 4/4; no crash; no auto-collect.
- IF still too low: next step a SMALL increment (keep dz+512, try dy -384 or -512) — vertical
  auto-collect risk grows with Y; do NOT jump large. IF unreachable/auto-collect/vanish/miscount: stop
  coordinate patching, record failure mode, consider F runtime/render investigation (no radius edits).


## Seed-power token tests (chronological)
### Seed-power token / seed pickup system (CANDIDATE — strong code evidence, no rebuild yet)
User goal: the pickup tokens that power up seeds. Identified from code/data (NOT from a literal "seed"
string at the handler, so labeled CANDIDATE/high-confidence).

CONFIRMED FROM CODE:
- Tokens are DAT type-0x3f entries, source kinds **0x29 / 0x2a / 0x2b** in LEVEL01 (also 0x2c/0x2d exist
  in the dispatch for other levels). Same entry layout as grain/FLIK (+0/+4/+8 = X/Y/Z<<5, +0xc = kind).
- Pickup dispatch: same contact pass `fcn.80053814`, jump table **0x8001b42c** index (kind-0x10).
  Cases: 0x29→`0x800542f4`, 0x2a→`0x8005433c`, 0x2b→`0x800543b8` (0x2c→0x80054434, 0x2d→0x800544d0).
- Each case INCREMENTS a per-seed counter byte (mod 8) and POWERS UP a seed object:
  - 0x29 → counter **0x800a6598**, powers up object index **0x16** in the 128-obj list (0x80096b98).
  - 0x2a → counter **0x800a6599**, object **0x17**.   0x2b → counter **0x800a659a**, object **0x19**.
  - (object id for 0x2a..0x2d from table `0x80078e90` = `17 19 18 2f`; 0x29 hardcodes 0x16.)
- Power-up routine = **`fcn.8003e760(objIndex, level)`**: indexes 0x80096b98[objIndex], writes a
  power/level value into that object's render attr (+6 hword low2 cleared|level, +8 byte ×6 |= level<<6).
  = progressive visual "grow/power-up" of the seed object. level = (counter&7)-1 → 3 tokens give stages 0,1,2.
- HUD displays the counters: `fcn.800526f4` loop @`0x80052fa4` reads `0x800a6598+i` and draws per-seed
  meters (icons from tables near 0x80078e66/67). So the token counters are on-screen.
- Pickup also calls sound/event `fcn.80050994` (a0 id) and 0x8003e760.

LEVEL01 token census (3 seeds × 3 tokens = 9), via `tools/list_level_pickups.py`:
- kind 0x29 (seed obj 0x16, ctr 0x6598): entries 63,64,65.
- kind 0x2a (seed obj 0x17, ctr 0x6599): entries 60,61,66.
- kind 0x2b (seed obj 0x19, ctr 0x659a): entries 58,59,62.
- (kind 0x30 ×3 = entries 67,68,69 is NOT a token: handler 0x80054554 writes a position 0x652c/30/34 +
  flag 0x800824dc, fires once → CHECKPOINT/level-trigger candidate. Excluded.)

UNKNOWNS:
- Literal in-game name ("seed"/"berry"/other) not proven from a handler string.
- Which physical seed/plant each object index (0x16/0x17/0x19) renders (lives in the level overlay).
- Per-token runtime record `+0x20` action id and `+0x28` contact radius (not yet read; tokens use the
  same contact walker so the weak-Y auto-collect caveat applies — keep test deltas small).

FIRST SAFE TEST (proposed, NOT built): move ONE token Y by `dy -128` (runtime -4096), same proven-safe
step as the FLIK letters. Candidate: kind 0x29 entry 63 (X=-2131, Y=-250, Z=-10028), Yoff 0x3fc,
orig Y bytes `06 ff ff ff` → `86 fe ff ff` (Y -250→-378). Keep grain/FLIK/other tokens pristine.
Output names: `DAT/LEVEL01_LEVEL_SEEDTOKEN0_UP_SMALL.DAT`, `ABL_SEEDTOKEN_SMALL_TEST.bin/.cue`.
Risk: tokens share the contact walker (weak-Y); small delta avoids the tall-cylinder auto-collect. Unlike
F, a token powers up a SEPARATE object (not itself), so no self-render coupling expected.

### NEXT TEST — ABL_SEEDTOKEN_SMALL_TEST (kind 0x29 / entry 63; BUILT, awaiting in-game result)
First-ever coordinate-mod validation of the seed-power token candidate system. Single token, small Y.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_SEEDTOKEN0_UP_SMALL.DAT`.
  Image `ABL_SEEDTOKEN_SMALL_TEST.bin`/`.cue`.
- Entry 63, source kind 0x29 (seed token; counter 0x800a6598, powered object 0x16, handler 0x800542f4).
  entryoff `0x3f8`, Yoff `0x3fc`. Orig XYZ (-2131, -250, -10028).
  Y `-250` (`06 ff ff ff`) → `-378` (`86 fe ff ff`); `dy -128` file = runtime delta -4096 (rtY -8000→-12096).
- Grain, FLIK (50/51/52/53), other tokens (58/59/60/61/62/64/65/66), checkpoint (67/68/69): UNCHANGED.
- EXPECT if mapping correct: token 63 slightly raised; still collectable; collecting it bumps the seed
  HUD meter (counter 0x6598) and powers up object 0x16 (stage 1); grain/FLIK unchanged; no crash; no
  far-distance auto-collect.
- Pass → mark kind 0x29/entry 63 coordinate-mod CONFIRMED; next test one of 0x2a/0x2b. Moves-but-no-power
  → coord ok but functional identity incomplete (inspect 0x29 runtime record +0x20). No move → re-check
  image/scene/visible-vs-contact. Auto-collect/vanish/crash → record mode; inspect +0x20/+0x28/+0x22/+0x33.

### NEXT TEST — ABL_SEEDTOKEN_UP_SIDE_TEST (kind 0x29 / entry 63, up + slight side; BUILT, awaiting result)
Per user: make the moved token more obvious — slight horizontal + a bigger raise. Still ONE token.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_SEEDTOKEN0_UPSIDE.DAT`.
  Image `ABL_SEEDTOKEN_UP_SIDE_TEST.bin`/`.cue`.
- Entry 63, source kind 0x29 (seed token; counter 0x800a6598, object 0x16). entryoff `0x3f8`.
  - X@`0x3f8`: `-2131` (`ad f7 ff ff`) → `-1875` (`ad f8 ff ff`); `dx +256` = runtime +8192 (slight side).
  - Y@`0x3fc`: `-250` (`06 ff ff ff`) → `-506` (`06 fe ff ff`); `dy -256` = runtime -8192 (clearer raise).
  - Z@`0x400`: UNCHANGED (`d4 d8 ff ff`).
- Grain, FLIK, other tokens, checkpoints: UNCHANGED. Two fields changed (entry63 X and Y only).
- EXPECT: token 63 visibly up + slightly to one side; still collectable; bumps seed meter (0x6598) +
  powers object 0x16; grain/FLIK unchanged; no crash; no far-distance auto-collect. dy -256 (rt -8192) is
  well within the safe band (F tolerated it); far below the bad all-letter rt -65536.

### ABL_SEEDTOKEN_UP_SIDE_TEST RESULT — SUCCESS (in-game confirmed): kind 0x29 = seed-power token
In-game (user, + screenshot): "The orange item/token is the one that moved. It updated the HUD's seed
power-up meter. No issues observed."
- CONFIRMED: DAT type-0x3f source kind **0x29 = a visible seed-power token/item** (the "orange token").
  Entry 63 coordinate movement (X+Y) confirmed in-game; collecting it updates the seed-power HUD meter.
- CONFIRMED functional mapping for 0x29: handler `0x800542f4`, counter `0x800a6598`, powered object `0x16`.
- Coordinate-mod method (same as grain/FLIK): patch DAT entry X/Y; runtime = file<<5; small deltas safe.
- Literal in-game NAME still UNKNOWN (no proving string) — call it "seed-power token / orange item".
- Grain & FLIK unaffected; no crash/HUD/functional issue.

### NEXT TEST — ABL_SEEDTOKEN_KIND2A_UPSIDE_TEST (kind 0x2a / entry 60; BUILT, awaiting result)
2nd seed-token kind confirmation (generalize the model beyond 0x29). One token, X+Y only, Z unchanged.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_SEEDTOKEN_KIND2A_UPSIDE.DAT`.
  Image `ABL_SEEDTOKEN_KIND2A_UPSIDE_TEST.bin`/`.cue`.
- Entry 60, source kind 0x2a (seed token; counter 0x800a6599, powered object 0x17, handler 0x8005433c).
  entryoff `0x3c8`. Orig XYZ (7724, 0, 3593).
  - X@`0x3c8`: `7724` (`2c 1e 00 00`) → `7980` (`2c 1f 00 00`); `dx +256` = runtime +8192 (slight side).
  - Y@`0x3cc`: `0` (`00 00 00 00`) → `-256` (`00 ff ff ff`); `dy -256` = runtime -8192 (raise).
  - Z@`0x3d0`: UNCHANGED (`09 0e 00 00`).
- Grain, FLIK, token 63 (confirmed 0x29), other tokens 58/59/61/62/64/65/66, checkpoints 67/68/69: UNCHANGED.
- EXPECT: kind-0x2a token (entry 60) up + slightly side; collectable; updates 2nd seed meter (0x6599) +
  powers object 0x17; grain/FLIK/token63 unchanged; no crash; no auto-collect. Pass → seed-token coord
  model confirmed for TWO kinds (0x29, 0x2a); then final test 0x2b. 0x2b stays probable until tested.

### NEXT TEST — ABL_SEEDTOKEN_KIND2A_UPSIDE_BIG_TEST (kind 0x2a / entry 60, LARGER move; BUILT, awaiting result)
Per user: prior 0x2a move was hard to tell — make it MUCH more obvious. Lean on a big horizontal shift
(full-weight axis = safe) + a clearer raise (Y kept in the proven-safe band). Still ONE token (entry 60).
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_SEEDTOKEN_KIND2A_UPSIDE_BIG.DAT`.
  Image `ABL_SEEDTOKEN_KIND2A_UPSIDE_BIG_TEST.bin`/`.cue`.
- Entry 60, source kind 0x2a (counter 0x800a6599, object 0x17, handler 0x8005433c). entryoff `0x3c8`. Orig (7724, 0, 3593).
  - X@`0x3c8`: `7724` (`2c 1e 00 00`) → `8748` (`2c 22 00 00`); `dx +1024` = runtime +32768 (big side shift).
  - Y@`0x3cc`: `0` (`00 00 00 00`) → `-512` (`00 fe ff ff`); `dy -512` = runtime -16384 (= grain MEDIUM magnitude; proven safe; far below bad -65536).
  - Z@`0x3d0`: UNCHANGED (`09 0e 00 00`).
- Grain, FLIK, token63(0x29), other tokens 58/59/61/62/64/65/66, checkpoints 67-69: UNCHANGED.
- EXPECT: kind-0x2a token clearly relocated up + well to the side; collectable; updates seed meter 0x6599
  + powers object 0x17; grain/FLIK/token63 unchanged; no crash; likely still needs near-contact (jump).
  WATCH: if it auto-collects from afar at Y rt -16384, that informs token contact radius (no radius patch).

### ABL_SEEDTOKEN_KIND2A_UPSIDE_BIG_TEST RESULT — SUCCESS (in-game confirmed): kind 0x2a = BLUE seed token
In-game (user, + screenshot): "The moved item is a blue token. Moved clearly. Collectable. The UI/HUD
changes. The user can change seeds. No other movement seen."
- CONFIRMED: source kind **0x2a = a visible seed-power token/item (BLUE)**. Entry 60 coord move (X+Y, rt
  +32768/-16384) confirmed; collecting it updates the seed-power HUD/UI and affects/enables seed-changing.
- CONFIRMED functional mapping for 0x2a: handler `0x8005433c`, counter `0x800a6599`, powered object `0x17`.
- No unrelated object moved; grain/FLIK/token63(0x29) unaffected; no crash/issue.
- Y rt -16384 (grain-MEDIUM magnitude) did NOT cause far-distance auto-collect for this token. Good.
- **Seed-token coordinate modding now confirmed for TWO kinds: 0x29 (orange) and 0x2a (blue).**

### NEXT TEST — ABL_SEEDTOKEN_KIND2B_UPSIDE_BIG_TEST (kind 0x2b / entry 58; BUILT, awaiting result)
Final direct seed-token confirmation (3rd kind). One token, X+Y only, Z unchanged. Same obvious deltas as 0x2a big.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_SEEDTOKEN_KIND2B_UPSIDE_BIG.DAT`.
  Image `ABL_SEEDTOKEN_KIND2B_UPSIDE_BIG_TEST.bin`/`.cue`.
- Entry 58, source kind 0x2b (seed token; counter 0x800a659a, powered object 0x19, handler 0x800543b8).
  entryoff `0x3a8`. Orig XYZ (-1772, -150, -10407).
  - X@`0x3a8`: `-1772` (`14 f9 ff ff`) → `-748` (`14 fd ff ff`); `dx +1024` = runtime +32768 (clear side).
  - Y@`0x3ac`: `-150` (`6a ff ff ff`) → `-662` (`6a fd ff ff`); `dy -512` = runtime -16384 (clear raise).
  - Z@`0x3b0`: UNCHANGED (`59 d7 ff ff`).
- Grain, FLIK, tokens 63(0x29)/60(0x2a), other tokens 59/61/62/64/65/66, checkpoints 67-69: UNCHANGED.
- EXPECT: kind-0x2b token (entry 58) clearly up + to the side; collectable; updates 3rd seed meter
  (0x659a) + powers object 0x19; grain/FLIK/other tokens unchanged; no crash; no far auto-collect.
  Pass → seed-token coord model confirmed for ALL THREE LEVEL01 kinds (0x29/0x2a/0x2b); then switch from
  discovery to a clean seed-token catalog + mod-safe delta summary.


### SCOPE CORRECTION — per-entry test coverage
Seed-token SOURCE-KIND mapping is confirmed for 0x29/0x2a/0x2b. Coordinate modding is confirmed for ONE
representative entry of each kind (in-game tested): 0x29 entry 63, 0x2a entry 60, 0x2b entry 58. The
remaining SIX placements are PROBABLE by the same DAT/source-kind model but NOT individually in-game
tested: 0x29 entries 64,65; 0x2a entries 61,66; 0x2b entries 59,62.

### NEXT TEST — ABL_TOKEN64_UPSIDE_BIG_TEST (kind 0x29 / entry 64, untested orange placement; BUILT, awaiting result)
Validate a 2nd orange-token placement (same model as confirmed entry 63). One token, X+Y only, Z unchanged.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_TOKEN64_UPSIDE_BIG.DAT`.
  Image `ABL_TOKEN64_UPSIDE_BIG_TEST.bin`/`.cue`.
- Entry 64, source kind 0x29 (orange; counter 0x800a6598, object 0x16, handler 0x800542f4). entryoff `0x408`.
  Orig XYZ (4416, -50, -3655).
  - X@`0x40c`... (see report for exact offsets/bytes) — dx +1024 = rt +32768; dy -512 = rt -16384; Z unchanged.
- Grain, FLIK, tested tokens 63/60/58, other tokens 65/61/66/59/62, checkpoints 67-69: UNCHANGED.
- EXPECT: orange token (entry 64) clearly up + side; collectable; seed meter 0x6598 updates; nothing else
  moves; no crash; no far auto-collect. Pass → orange placement generalization strengthened (2 of 3 tested).
- RESULT (user): PASS — "Orange has been moved up and over to the side." Entry 64 (0x29) coord-mod confirmed.
  Orange now 2/3 placements tested (63, 64); entry 65 still untested.

### NEXT TEST — ABL_TOKEN65_UPSIDE_BIG_TEST (kind 0x29 / entry 65, last untested orange; BUILT, awaiting result)
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_TOKEN65_UPSIDE_BIG.DAT`.
  Image `ABL_TOKEN65_UPSIDE_BIG_TEST.bin`/`.cue`.
- Entry 65, source kind 0x29 (orange; counter 0x800a6598, object 0x16). entryoff `0x418`. Orig (1427, -450, -13918).
  X@`0x418` dx +1024 (rt +32768); Y@`0x41c` dy -512 (rt -16384); Z@`0x420` unchanged. (exact bytes in report)
- Grain, FLIK, tested tokens 63/64/60/58, other tokens 61/66/59/62, checkpoints 67-69: UNCHANGED.
- EXPECT: orange token (entry 65) clearly up + side; collectable; meter 0x6598 updates; nothing else moves;
  no crash; no far auto-collect. Pass → all 3 orange placements tested; then move to blue (61) / green (59).
- RESULT (user): **AUTO-COLLECT at large upward delta.** Entry 65 collected from the general vicinity.
  Mapping is SUPPORTED but `dy -512` is UNSAFE at this placement. Do NOT mark entry 65 cleanly passed.
  Source kind 0x29 stays CONFIRMED from entries 63 & 64 (clean).

### TOKEN PLACEMENT RULE — use per-entry final HEIGHT limit, not a fixed delta
Auto-collect is the weak-Y contact cylinder (Y weighted ⅓ vs X/Z; same mechanism as F). It depends on the
token's ABSOLUTE final runtime Y (height), not the delta size. Entry 65 was already the highest/deepest
token (orig Y=-450, Z=-13918), so `dy -512` pushed final runtime Y to ≈ **-30784** (auto-collected),
whereas clean tests stayed at/above ≈ **-21184** runtime Y. Edge proximity (deep Z) constrains Flik's
approach to the token's XZ column, amplifying the effect.
- Observed SAFE band (approx, not exact — do not overclaim): final runtime Y ≳ **-21184** = OK;
  entry 65 FAILED at ≈ **-30784**. Threshold between is unmeasured.
- RULE: pick each token's `dy` so final runtime Y = (origY+dy)<<5 stays roughly ≥ -21k; lean on
  horizontal (dx/dz, full-weight, safe) for visibility, not large up-moves.

### NEXT TEST — ABL_TOKEN65_UPSIDE_SAFE_TEST (kind 0x29 / entry 65, smaller raise; BUILT, awaiting result)
Corrective retest of entry 65: same horizontal shift, much smaller raise to stay in the safe band.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_TOKEN65_UPSIDE_SAFE.DAT`.
  Image `ABL_TOKEN65_UPSIDE_SAFE_TEST.bin`/`.cue`.
- Entry 65, kind 0x29 (orange; counter 0x800a6598, object 0x16). entryoff `0x418`. Orig (1427, -450, -13918).
  - X@`0x418`: `1427`→`2451` (`93 05 00 00`→`93 09 00 00`); dx +1024 = rt +32768.
  - Y@`0x41c`: `-450`→`-578` (`3e fe ff ff`→`be fd ff ff`); dy -128 = rt -4096. **Final rt Y ≈ -18496 (safe band).**
  - Z@`0x420`: UNCHANGED (`a2 c9 ff ff`).
- Grain, FLIK, tokens 63/64/60/58, untested 61/66/59/62, checkpoints 67-69: UNCHANGED.
- EXPECT: orange token (entry 65) moved sideways + modestly up; collectable by NORMAL contact (no vicinity
  auto-collect); HUD updates; nothing else moves; no crash. Pass → entry 65 confirmed at safe delta;
  record that 65 fails at dy -512 but passes at dy -128. Still auto-collect → stop patching 65; investigate
  token 0x29 runtime record +0x28 radius + constructed position.
- RESULT (user): **PASS.** Entry 65 confirmed at SAFE delta (dx +1024, dy -128, final rt Y -18496):
  moved, collectable by normal contact, no vicinity auto-collect. So entry 65 FAILS at dy -512 (rt Y
  -30784) but PASSES at dy -128 (rt Y -18496) → height-band rule VALIDATED. All 3 orange placements
  (63, 64, 65) now coordinate-confirmed (65 with a height-limited delta).

### NEXT TEST — ABL_TOKEN61_UPSIDE_TEST (kind 0x2a / entry 61, untested blue placement; BUILT, awaiting result)
Blue placement #2 (entry 61). Height-aware deltas: entry 61 orig Y=-50 (low), so dy -512 → final rt Y
≈ -17984 (in safe band, like clean entry 64). Horizontal dx +1024 for visibility.
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_TOKEN61_UPSIDE.DAT`.
  Image `ABL_TOKEN61_UPSIDE_TEST.bin`/`.cue`.
- Entry 61, kind 0x2a (blue; counter 0x800a6599, object 0x17). entryoff `0x3d8`. Orig (2749, -50, -12809).
  - X@`0x3d8` dx +1024 (rt +32768); Y@`0x3dc` dy -512 (rt -16384, final rt Y -17984); Z@`0x3e0` unchanged. (bytes in report)
- Grain, FLIK, tokens 63/64/65/60/58, untested 66/59/62, checkpoints 67-69: UNCHANGED.
- NOTE: entry 61 also has deep Z (-12809, near edge) like 65, but final height -17984 is well within the
  safe band, so expected OK. EXPECT: blue token (entry 61) up + side; normal-contact collectable; meter
  0x6599 updates; nothing else moves; no crash; no vicinity auto-collect.
- RESULT (user): **PASS.** Blue entry 61 confirmed (dx +1024, dy -512, final rt Y -17984). Deep-Z token
  at safe height collects normally → confirms HEIGHT (not edge alone) is the dominant auto-collect factor.

### FINAL THREE PLACEMENTS — built as 3 separate single-token ISOs (height-aware; BUILT, awaiting results)
Remaining untested placements built in one batch, each its own image (one token moved per ISO). Deltas
chosen so final runtime Y stays in the safe band (≳ -21184).
| entry | kind/color | orig Y | dx | dy | final rt Y | output DAT / image |
|------|-----------|--------|-----|-----|-----------|--------------------|
| 66 | 0x2a blue  | -350 | +1024 | **-256** | -19392 | `LEVEL01_LEVEL_TOKEN66_UPSIDE.DAT` / `ABL_TOKEN66_UPSIDE_TEST` |
| 59 | 0x2b green | -50  | +1024 | -512 | -17984 | `LEVEL01_LEVEL_TOKEN59_UPSIDE.DAT` / `ABL_TOKEN59_UPSIDE_TEST` |
| 62 | 0x2b green | 0    | +1024 | -512 | -16384 | `LEVEL01_LEVEL_TOKEN62_UPSIDE.DAT` / `ABL_TOKEN62_UPSIDE_TEST` |
- Entry 66 uses dy -256 (not -512) because it starts high (Y=-350); dy -512 would reach rt Y -27584 (near
  the failing band). 59/62 start low so dy -512 is safe. All Z unchanged; X+Y only; one token per image.
- Each ISO built from PRISTINE DAT (independent, not cumulative); grain/FLIK/all other tokens/checkpoints
  unchanged in every image. EXPECT each: its token up+side, normal-contact collectable, correct meter
  updates (66→0x6599/obj0x17; 59,62→0x659a/obj0x19), nothing else moves, no crash, no vicinity auto-collect.
- Pass on all → every LEVEL01 seed-token placement (9/9) individually coordinate-confirmed.
- RESULTS (user): **59 PASS, 62 PASS.** Entry **66 = inconclusive-by-eye**: 66 is ALREADY high in the
  original game, so raising it (+dy) pushed it above the render/visible range → not seen. NOT auto-
  collecting, no misbehavior — consistent with a valid token moved out of view. So 66's coord mapping is
  not contradicted; it just couldn't be eyeballed via an up-move.
- LESSON: for already-high tokens, verify with HORIZONTAL-only moves (no dy) to keep them at their native
  visible height. (Also: raising a token can push it out of render range, separate from the auto-collect
  height effect — both argue against up-moves for high tokens.)

### VERIFY TEST — ABL_TOKEN66_SIDE_TEST (kind 0x2a / entry 66, HORIZONTAL-only; BUILT, awaiting result)
Clean 66 verification: shift sideways only, keep native height (known visible in OG game).
- Input `DAT/LEVEL01_LEVEL.DAT` (sha1 b376cb50…, UNCHANGED). Output `DAT/LEVEL01_LEVEL_TOKEN66_SIDE.DAT`.
  Image `ABL_TOKEN66_SIDE_TEST.bin`/`.cue`.
- Entry 66, kind 0x2a (blue; counter 0x800a6599, object 0x17). entryoff `0x428`. Orig (6651, -350, 21641).
  - X@`0x428`: `6651`→`7675` (`fb 19 00 00`→`fb 1d 00 00`); dx +1024 = rt +32768.
  - Y@`0x42c`: UNCHANGED (`a2 fe ff ff`, native height rt -11200, known visible).  Z@`0x430`: UNCHANGED (`89 54 00 00`).
- ONE field changed (entry 66 X only). Grain/FLIK/all other tokens/checkpoints UNCHANGED.
- EXPECT: blue token (entry 66) visibly shifted sideways at its normal height; normal-contact collectable;
  meter 0x6599 updates; nothing else moves; no crash. Pass → all 9/9 LEVEL01 placements confirmed.


## Append investigation, fixed-count sacrifice & berry discovery (chronological)
### LEVEL01 type-0x3f entry injection / added token test — FAILED load crash
Goal: add/inject exactly one new visible red/orange seed-power token into LEVEL01 by increasing the
existing DAT type-`0x3f` record count and appending one cloned 0x10-byte placement entry. This is NOT a
move/overwrite test.

RESULT: **FAILED — load crash / black screen.** `ABL_ADD_TOKEN0X29_NEAR64_TEST` reaches a blank/black
screen while loading LEVEL01; no gameplay result. Do NOT mark entry injection as successful.
Conclusion: binary/image verification passed, but runtime load failed. Append/injection is not currently
safe despite correct file/image embedding. Likely causes under investigation: type-`0x3f`/runtime capacity,
shifted later DAT records, contact constructor overflow, or fixed offset assumptions.

Rule: **do not inject or append new type-`0x3f` entries until loader/runtime capacity is understood.**

Feasibility / insertion model:
- Input `DAT/LEVEL01_LEVEL.DAT` sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`, size 332824.
- DAT top-level record count = 11. First record is type `0x3f` at file offset `0x0004`.
- Original type-`0x3f` count = 70 (`0x46`), entry size = `0x10`, entry base = `0x0008`.
- Final existing entry index 69 starts at `0x0458`; insertion point is exactly `0x0468`, the next record
  header. Top-level record count remains unchanged.
- No separate internal offset table was found in this DAT structure; the parser walks records by count/type
  sizes, so records after type-`0x3f` shift by `+0x10`.

Patch / add details:
- Tool added: `tools/add_level_entry.py` (safe append-only clone tool; refuses in-place edits).
- Command:
  `python3 tools/add_level_entry.py DAT/LEVEL01_LEVEL.DAT --clone-entry 64 --dx 512 --out DAT/LEVEL01_LEVEL_ADD_TOKEN0X29_NEAR64.DAT`
- Clone/source entry: 64, source kind `0x29` (red/orange seed-power token), source offset `0x0408`.
- New entry index: 70, insertion offset `0x0468`.
- Entry 64 original bytes: `40110000ceffffffb9f1ffff29000000`.
- New entry 70 bytes: `40130000ceffffffb9f1ffff29000000`.
- Entry 64 XYZ = `(4416, -50, -3655)`.
- New entry 70 XYZ = `(4928, -50, -3655)`.
- Coordinate delta: `dx +512`, `dy 0`, `dz 0` (runtime delta X `+16384`; Y/Z unchanged).
- Output DAT `DAT/LEVEL01_LEVEL_ADD_TOKEN0X29_NEAR64.DAT`, sha1
  `e3bbedc78b775cb66b039c9586f74bf0ebcf0616`, size 332840.

Verification summary:
- Output DAT size = input size + `0x10`.
- Top-level record count unchanged (11).
- Type-`0x3f` count increased exactly `70 -> 71`.
- Existing entries `0..69` are byte-identical to the pristine DAT.
- Grain entries `0..49`, FLIK entries `50..53`, original seed tokens `58..66`, and checkpoint entries
  `67..69` are unchanged.
- Records after type-`0x3f` are byte-identical and shifted by `+0x10`; output DAT fully reparses.
- Pickup catalog after insertion: `0x29` count `3 -> 4`; `0x2a` remains 3; `0x2b` remains 3; `0x30`
  remains 3.
- Rebuilt image: `ABL_ADD_TOKEN0X29_NEAR64_TEST.bin/.cue`.
- Embedded `LEVEL01/LEVEL.DAT` in rebuilt image matches the injected DAT, size 332840, type-`0x3f` count 71,
  and entry 70 bytes match `40130000ceffffffb9f1ffff29000000`.
- Original image embedded `LEVEL01/LEVEL.DAT` matches pristine DAT, size 332824, type-`0x3f` count 70, and
  does not contain the new entry. LBA remained `2906` in both original and rebuilt images (confirmed).
- `REBUILD/files/LEVEL01/LEVEL.DAT` was restored from `LEVEL.DAT.orig` after build.

Capacity risk / expectations:
- This adds exactly one visible pickup. Existing visible pickups appear to total 63 (50 grain + 4 FLIK +
  9 seed tokens), close to the 64-record contact array at `0x800b0d18`.
- The test may fill the apparent 64th contact slot. Do NOT assume multiple extra tokens are safe.
- Expected in-game result: a new red/orange token appears near original entry 64; original entry 64 remains;
  the new token is collectable; seed-power HUD/UI accepts or at least visibly reacts to the fourth `0x29`
  token. Watch whether the counter caps, extends, or behaves oddly.
- Unknown until user test: loader/runtime capacity behavior at exactly 64 visible pickups; whether the HUD
  and powered seed object handle a fourth `0x29` token cleanly.
- In-game test answered this negatively for the append build: load crashes before gameplay.

Post-failure read-only diagnosis:
- DAT parser `fcn.8001cdc0` (`0x8001ce8c..0x8001cf18`) walks the top-level DAT record list by
  count/type-derived record sizes and stores record pointers in the resident type table (`0x80096da0`;
  type `0x3f` pointer at `0x80096e9c`). It does not use LEVEL01 fixed subrecord offsets for records after
  type `0x3f`.
- Parser evidence for shifted later records: original records after type `0x3f` start at `0x0468`,
  `0x094c`, `0x0a10`, `0x0ad4`, `0x0b98`, `0x0cc8`, `0x0ee8`, `0x1078`, `0x1210`, `0x1370`; injected
  records shift to `0x0478`, `0x095c`, `0x0a20`, `0x0ae4`, `0x0ba8`, `0x0cd8`, `0x0ef8`, `0x1088`,
  `0x1220`, `0x1380`. All contents match, shifted by `+0x10`.
- Type-`0x3f` source loop `fcn.80053814` reads the type-`0x3f` count and iterates while `s5 < count`
  (`0x800545d4..0x800545e0`). No hard `0x46`/70 cap was seen in that loop, so count 71 reaches the
  constructor/handler path.
- Non-grain visible entries with kind `<0x30` and `kind != 0x14` use the common constructor path
  `0x80053b24..0x80053be0` when `(kind & 3) == [0x800910a4]`; this calls `fcn.80059e44` with constructor
  type `0x71`. Source kind `0x29` is in this path (and then dispatches to pickup handler `0x800542f4`
  only on contact/collection, not at load).
- Constructor type `0x71` metadata at `0x80079cf0`: action id copied to runtime `+0x20` = `0x04`,
  active/type copied to `+0x22` = `0x10`, radius addend copied to runtime `+0x28` = `0`, flags include
  `0x80` bits used by the allocator/live-slot test.
- Runtime destination is the fixed contact/render array `0x800b0d18`, 64 records, stride `0x38`.
  `fcn.80059e44` advances cursor `0x8008234c`, wraps at `0x40`, and skips occupied slots while
  `record[+0x33] & 0x80` and `record[+0x22] != 0` (`0x80059e64..0x80059ed4`). No full-array escape was
  seen. If all 64 eligible slots are occupied and another constructor runs, this loop can hang.
- Static LEVEL01 constructor-candidate count by phase (grain always included; non-grain path gated by
  `kind & 3`): original phase 0/1/2/3 = `52/55/55/55`; injected = `52/56/55/55`. This alone does not
  prove overflow, but it reduces headroom in a fixed 64-slot allocator. Other load/runtime constructors
  could consume the remaining slots before or after the type-`0x3f` pass.
- ISO structure is unlikely: rebuilt `LEVEL01/LEVEL.DAT;1` has updated ISO9660 size 332840, LBA remains
  `2906`; following LEVEL01 files keep their LBAs and remain accessible. Embedded DAT bytes match the
  injected DAT exactly.
- Current best interpretation: shifted DAT records are probably handled by the parser, and ISO rebuild is
  unlikely. The most likely failure class is runtime construction/capacity in or around `fcn.80059e44` /
  the 64-slot `0x800b0d18` array, but the exact crash/hang point still needs emulator breakpoint/logging.

Paired RAM comparison, original vs injected black-screen:
- Dumps compared: `~/good_iso.ram` and `~/bad_iso_black.ram`, both raw 2 MiB PS1 RAM
  (`0x80000000 -> file offset 0`).
- These dumps are not at the same main-shell substate. Original/good has `[0x8008243c] = 1`;
  injected/bad has `[0x8008243c] = 0`. Scene slot and scene id both remain `1`.
- Both point type `0x3f` at `0x801607fc`; good header is count 70, bad header is count 71.
- Bad type pointers for records after type `0x3f` are consistently `+0x10` from good, matching the
  structural append. This supports that the parser rebuilt the resident pointer table from the shifted DAT.
- Contact array comparison: good has 32 nonzero / `+0x22 != 0` records and allocator cursor `0x20`;
  bad has only 4 such records and allocator cursor `0x04`. Neither dump shows `+0x33 & 0x80` set.
- Large visual-object pool `0x8009c870` has the same first three active slots in both dumps, so the main
  8-slot visual pool is not obviously destroyed in the black-screen snapshot.
- Correction after manual DuckStation debugging: a write watchpoint on `0x8008243c` did not catch a useful
  transition in the working ISO; after many constructor breakpoints it remained 0. Stop relying on
  `0x8008243c` as a confirmed phase-transition write target until the exact main-shell path is traced.
- Static refs: `0x80082438` is a frame/VSync wait counter. `fcn.800390f0` increments it after calling
  `0x800186ec`; wait loops at `0x8003f30c` and `0x8004fe70` poll it, then clear it at `0x8003f31c` /
  `0x8004fe88`. It is not the level-load phase flag.
- Static refs: `0x8008243c` is initialized/advanced by the main shell (`0x8004fad4`, `0x8004fcc0..fce8`)
  and indexes the 6-way shell jump table. It is a shell substate index, not yet tied to the injected
  append failure.
- Corrected interpretation: the bad build has not reached the same shell/contact state as the good dump,
  but the earlier labels "phase index" and "phase 0 -> 1" were too strong. Next debugging should break on
  the actual writer paths (`0x800390f0`, `0x8003f2f0`, `0x8004fe68`, and the main-shell substate block)
  and compare control flow, not just watch `0x8008243c`.

Same-event parser-entry comparison at `0x8001CE00`:
- Dumps compared: `~/good_loading_8001CE00.ram` and
  `~/bad_loading_8001CE00.ram`, both raw 2 MiB PS1 RAM.
- Context: breakpoint is on `0x8001CE00`, inside `fcn.8001cdc0`, before the top-level DAT record walk has
  stored resident type pointers.
- Both dumps match the expected parser-entry state:
  - `current_scene_id` `[0x80082504] = 1`
  - `scene_slot` `[0x8008245c] = 1`
  - shell substate `[0x8008243c] = 0`
  - DAT base pointer `[0x80082498] = 0x801607f8`
  - type table area `0x80096da0..` still zero
  - type `0x3f` pointer slot `[0x80096e9c] = 0`
- Full DAT payload is already resident at `0x801607f8`:
  - good RAM contains pristine `DAT/LEVEL01_LEVEL.DAT` exactly
  - bad RAM contains injected `DAT/LEVEL01_LEVEL_ADD_TOKEN0X29_NEAR64.DAT` exactly
  - bad injected DAT has type `0x3f` count 71 and inserted bytes
    `40130000ceffffffb9f1ffff29000000`
  - bad records after type `0x3f` are shifted by `+0x10` and still match the original contents
- Conclusion: the bad image is not failing because `LEVEL01/LEVEL.DAT` failed to load. At parser entry,
  the injected DAT is resident and structurally as built. Failure begins after this point.
- Next deterministic breakpoint sequence:
  1. `0x8001CF20` — immediately after the top-level DAT record/type-table walk
  2. `0x80052468` — exits the Press-X/loading wait loop
  3. `0x80052470` — restores previous scene id from `fp` to `[0x80082504]`
  4. `0x8004F028` — sole direct caller of `fcn.80053814`

Append sanity / strategy pivot:
- No same-event `0x8001CF20` dumps are currently available, so do not claim a completed exact post-walk
  good/bad RAM comparison at that address.
- Deterministic parser math for the loaded DAT is structurally valid:
  - good type `0x3f` pointer would be `0x801607fc`, count 70; type `0x01` pointer `0x80160c60`
  - bad type `0x3f` pointer would be `0x801607fc`, count 71; type `0x01` pointer `0x80160c70`
  - all bad post-`0x3f` record starts are exactly good `+0x10`, with aligned/valid headers
  - bad loaded DAT ends at `0x80161d08`; no calculated record pointer falls outside the resident DAT blob
- Earlier non-same-event black-screen RAM also showed the shifted type pointer table populated consistently.
  This argues against a basic parser/type-table failure, but does not prove append is runtime-safe.
- Strategy decision: stop spending primary effort on true append/new-object insertion unless explicitly
  needed. Treat appending/increasing type `0x3f` count as risky/unconfirmed and likely to violate a later
  gameplay/runtime invariant.
- Recommended playable mod class: fixed-size edits to existing records. These keep DAT size, type `0x3f`
  count, and all later record offsets unchanged.
- Fixed-count red/orange token target: LEVEL01 already has source-kind `0x29` entries 63/64/65. Entry 64
  has an in-game PASS for coordinate modification, so it is the preferred fixed-count red-token target.
  Suggested no-append test plan:
  `python3 tools/patch_level_entry.py DAT/LEVEL01_LEVEL.DAT --entries 64 --dx 1024 --dy -512 --out DAT/LEVEL01_LEVEL_REDTOKEN_MOVE_TEST.DAT`
  Then rebuild as `ABL_REDTOKEN_MOVE_TEST.bin/.cue` only if the user wants a fresh named image. This changes
  only entry 64 X/Y and preserves DAT size/count/offsets.
- Built fixed-count red/orange token move test:
  - Output DAT: `DAT/LEVEL01_LEVEL_REDTOKEN_MOVE_TEST.DAT`, size 332824, sha1
    `1e332630e81776a26220cf8881a38b727af7fb28`
  - Rebuilt image: `ABL_REDTOKEN_MOVE_TEST.bin/.cue`
  - Entry 64 only: `40110000ceffffffb9f1ffff29000000` →
    `40150000cefdffffb9f1ffff29000000`
  - X `4416 -> 5440` (`dx +1024`, runtime `+32768`), Y `-50 -> -562` (`dy -512`, runtime `-16384`),
    Z `-3655` unchanged, kind `0x29` unchanged.
  - Type `0x3f` count remains 70; DAT size unchanged; later records unchanged/unshifted.
  - Embedded `LEVEL01/LEVEL.DAT` in `ABL_REDTOKEN_MOVE_TEST.bin` matches the patched DAT; original image
    still contains pristine DAT; `REBUILD/files/LEVEL01/LEVEL.DAT` restored to original after build.

Cross-level retail type-`0x3f` scan:
- Scope: original retail DATs in `REBUILD/files/LEVEL*/LEVEL*.DAT`. Matching extracted originals in `DAT/`
  have identical SHA1s for the corresponding files; generated test DATs were excluded.
- `LEVEL00/LEVEL.DAT` and `LEVEL08/LEVEL1.DAT` have no type-`0x3f` record.
- Retail levels do exceed LEVEL01's 70 type-`0x3f` entries:
  - `LEVEL07/LEVEL.DAT`: 77 entries, seed total 8 (`0x29=3, 0x2a=3, 0x2b=2`)
  - `LEVEL05/LEVEL.DAT`: 74 entries, seed total 7 (`0x29=1, 0x2a=4, 0x2b=2`)
  - `LEVEL09/LEVEL.DAT`: 74 entries, seed total 9 (`0x29=1, 0x2a=4, 0x2b=4`)
  - `LEVEL10/LEVEL.DAT`: 74 entries, seed total 8 (`0x29=1, 0x2a=3, 0x2b=4`)
- No scanned retail DAT has more than 9 confirmed `0x29..0x2b` seed-token entries. LEVEL01 and LEVEL09
  are tied at 9.
- Some retail levels exceed 3 tokens for one color (`0x2a` or `0x2b`), but no scanned retail level has
  more than three `0x29` red/orange entries.
- Type `0x3f` is record ordinal 0 at offset `0x4` in every scanned DAT that has it. The next record offset
  varies naturally with the type-`0x3f` count (`0x2f8`, `0x368`, `0x3c8`, `0x468`, `0x4a8`, `0x4d8`, etc.),
  so the engine's global DAT parser cannot require one fixed post-`0x3f` offset.
- Implication: the failed LEVEL01 append should NOT be treated as proof of a global 70-entry parser/engine
  cap. The stronger risk signal is that the test made LEVEL01 a 10-token `0x29..0x2b` seed level, which no
  scanned retail DAT does. A later level-specific runtime invariant, active contact-pool pressure, or
  seed/HUD/power-up invariant is more likely than a basic DAT parser failure.
- Candidate model for future read-only study: `LEVEL07/LEVEL.DAT` has the highest retail type-`0x3f` count
  (77) while staying below the max confirmed seed total. `LEVEL09/LEVEL.DAT` is the retail model for seed
  total 9 at count 74.

### FIXED-COUNT 10th seed-token diagnostic — ENTRY 56 kind `0x21 -> 0x29`
Goal: test whether LEVEL01 tolerates 10 confirmed `0x29..0x2b` seed-token records when type-`0x3f` count,
DAT size, and all record offsets stay unchanged. This isolates seed-token total from the failed append
test, which changed both count/offsets and seed total.
- Input DAT: `DAT/LEVEL01_LEVEL.DAT` (pristine, sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`).
- Output DAT: `DAT/LEVEL01_LEVEL_TOKEN10_FIXEDCOUNT_ENTRY56_KIND29.DAT`, size 332824, sha1
  `1590dab2af0798bf89cc987c7647c52fa396a13d`.
- Rebuilt image: `ABL_TOKEN10_FIXEDCOUNT_ENTRY56_KIND29_TEST.bin/.cue`.
- Patch: type-`0x3f` entry 56 only, entry offset `0x388`, kind byte offset `0x394`.
  - original entry bytes: `990e0000000000008058000021000000`
  - patched entry bytes:  `990e0000000000008058000029000000`
  - byte diff: file offset `0x394`: `0x21 -> 0x29`
  - XYZ unchanged: `(3737, 0, 22656)`.
- Why entry 56: non-grain, non-visible-FLIK-letter, non-existing-token, non-checkpoint marker-like entry;
  converting `0x21 -> 0x29` preserves `(kind & 3) == 1`, minimizing constructor phase disturbance.
- Verification:
  - DAT size unchanged; type-`0x3f` count remains 70; top-level record layout unchanged.
  - Entries `0..55` and `57..69` unchanged; all later DAT bytes from `0x468` onward unchanged/unshifted.
  - Embedded `LEVEL01/LEVEL.DAT` in rebuilt image at LBA 2906 matches the patched DAT exactly when extracted
    sector-aware; original retail image at LBA 2906 still matches pristine DAT.
  - `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine after build.
- In-game interpretation:
  - Loads normally: LEVEL01 can tolerate 10 seed-token records in fixed-count form; append failure is more
    likely insertion/shift/append-specific.
  - Black screen/load failure: 10 seed-token records or replacing entry 56's marker role is sufficient to
    reproduce the failure without append.
  - Loads but token invisible/uncollectible: entry 56's runtime construction may not become a normal token
    despite the kind change; inspect constructor dispatch/phase before trying another candidate.
  - FLIK marker behavior changes: acceptable diagnostic side effect unless it prevents level start.
- RESULT (user): **PASS for load/stability.** LEVEL01 loaded normally; orange meter changed; seed switching
  still works; FLIK appears normal; no crash/glitch. Extra orange token visibility was unclear (not obvious
  in known orange-token areas).
- Interpretation: LEVEL01 can tolerate 10 seed-token-kind records when type-`0x3f` count stays 70 and
  records are not shifted. The append failure is therefore unlikely to be caused solely by seed-token total
  becoming 10. Visibility/collectability of repurposed entry 56 remained unconfirmed at its original
  coordinates.

### FIXED-COUNT repurposed entry 56 visibility test — kind `0x29` moved near entry 64 (BUILT, awaiting result)
Goal: keep the successful fixed-count model but move repurposed entry 56 to a known inspectable red/orange
token area near entry 64. This tests whether the marker slot can become a visible/collectible extra token
when placed somewhere easy to check.
- Input DAT: `DAT/LEVEL01_LEVEL.DAT` (pristine, sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`).
- Output DAT: `DAT/LEVEL01_LEVEL_ENTRY56_KIND29_NEAR64_TEST.DAT`, size 332824, sha1
  `824fea44993f44b4b3e97ede832cbd63782cba14`.
- Rebuilt image: `ABL_ENTRY56_KIND29_NEAR64_TEST.bin/.cue`.
- Patch: type-`0x3f` entry 56 only, entry offset `0x388`.
  - original entry bytes: `990e0000000000008058000021000000`
  - patched entry bytes:  `40130000ceffffffb9f1ffff29000000`
  - XYZ `3737,0,22656 -> 4928,-50,-3655`; kind `0x21 -> 0x29`
  - target is near known orange token entry 64 (`4416,-50,-3655`), with X offset `+512`.
- Verification:
  - DAT size unchanged; type-`0x3f` count remains 70; no append; no record shift.
  - Only entry 56 changed; entries `0..55` and `57..69` unchanged; later DAT bytes from `0x468` onward
    unchanged/unshifted.
  - Embedded `LEVEL01/LEVEL.DAT` in rebuilt image at LBA 2906 matches the patched DAT exactly when extracted
    sector-aware; original retail image at LBA 2906 still matches pristine DAT.
  - `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine after build.
- In-game interpretation:
  - Loads and visible/collectible orange token appears near entry 64: fixed-count repurposed net-new token
    behavior works; append failure points more toward insertion/shift/count mechanics.
  - Loads but no token appears: kind-change may not be enough for this marker slot to construct a visible
    token, or a per-entry/path/phase flag is involved.
  - Black screen/load failure: coordinate relocation plus kind conversion introduced a new issue, but the
    previous kind-only fixed-count test already showed 10 token-kind records alone are tolerated.
- RESULT (user, ABL_ENTRY56_KIND29_NEAR64_TEST): **PASS.** LEVEL01 loaded normally; original orange token
  near entry 64 still present; repurposed entry 56 appeared as an EXTRA collectible orange token near
  entry 64; orange meter updated; no crash/black-screen/glitch; no obvious FLIK/checkpoint weirdness.
- Structural meaning: NOT a true append — it repurposed an existing type-0x3f marker slot (entry 56, orig
  kind 0x21, an invisible FLIK/action marker; not grain, not a visible FLIK letter, not an existing seed
  token, not a checkpoint). Type-0x3f count stayed 70; DAT size and later offsets unchanged. So at least
  ONE repurposed marker can become a real extra fixed-count token without breaking LEVEL01.

### FIXED-COUNT "sacrifice remaining marker candidates" — ENTRIES 54/55/57 -> KIND 0x29 NEAR ENTRY 64 (BUILT, awaiting in-game result)
Goal: after entry 56 proved a marker slot can become a real extra fixed-count token, sacrifice the THREE
remaining plausible invisible marker/action candidates in LEVEL01 (entries 54/55/57) to see whether they
too can be repurposed as safe fixed-count visible/collectible token slots. Entry 56 is deliberately left
ALONE in this build (its own row stays the pristine marker `990e0000000000008058000021000000`).
- Build script: `tools/build_markers_54_55_57.py` (self-verifying; sets absolute X/Y/Z + kind, not deltas).
- Input DAT: `DAT/LEVEL01_LEVEL.DAT` (pristine, sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`, 332824 B).
- Output DAT: `DAT/LEVEL01_LEVEL_MARKERS54_55_57_KIND29_NEAR64_TEST.DAT`, size 332824, sha1
  `73596616cc7fd5c4415700436b5641a26d968d50`.
- Rebuilt image: `ABL_MARKERS54_55_57_KIND29_NEAR64_TEST.bin/.cue` (738285744 bytes, 313897 sectors).
- Candidate entries converted (all kind -> 0x29 orange seed-power token; placed in a row near entry 64
  reference `4416,-50,-3655`, +512 X spacing). Byte diffs:
  | entry | off | orig bytes | new bytes | orig kind/XYZ | new XYZ (kind 0x29) |
  |------:|----:|------------|-----------|---------------|---------------------|
  | 54 | `0x368` | `8b210000a2feffffc133000022000000` | `40130000ceffffffb9f1ffff29000000` | 0x22 (8587,-350,13249) | (4928,-50,-3655) |
  | 55 | `0x378` | `0e100000000000000207000023000000` | `40150000ceffffffb9f1ffff29000000` | 0x23 (4110,0,1794)     | (5440,-50,-3655) |
  | 57 | `0x398` | `ed1d000070feffff3441000024000000` | `40170000ceffffffb9f1ffff29000000` | 0x24 (7661,-400,16692) | (5952,-50,-3655) |
  - new tokens runtime: X 157696/174080/190464, Y -1600 (very safe, near the existing entry-64 band), Z -116960.
- Verification (all PASS):
  - output DAT size == pristine (332824); type-0x3f count remains 70; top-level record layout unchanged.
  - ONLY entries 54/55/57 changed; entries 0..53, 56, 58..69 byte-identical to pristine; entry 56 row left
    alone; all bytes from `0x468` onward unchanged/unshifted; all bytes outside the 3 entries identical.
  - each changed entry decodes to the intended X/Y/Z/kind 0x29.
  - rebuilt image embedded `LEVEL01/LEVEL.DAT` (LBA 2906, sector-aware) sha1 ==
    `73596616…` == patched DAT; original retail image embedded DAT == pristine (`b376cb50…`).
  - original `Disney-Pixar A Bug's Life (v1.0).bin/.cue` untouched; `REBUILD/files/LEVEL01/LEVEL.DAT`
    restored to pristine after build (cmp == LEVEL.DAT.orig).
- Pickup census after patch: 0x29 orange 3 -> **6** (entries 54/55/57 + 63/64/65); 0x2a blue 3; 0x2b green 3;
  0x30 checkpoint 3. LEVEL01 is now a **12 seed-token** level (6/3/3).
- CAPACITY NOTE (key risk): kinds 0x20..0x24 are pure trigger/marker ACTIONS that do NOT construct a visible
  entity (no `fcn.80059e44`), so they consumed 0 slots of the 64-record contact array `0x800b0d18`. Converting
  three of them to 0x29 adds 3 NEW visible-pickup constructions. Total visible pickups goes 63 -> **66**
  (50 grain + 4 FLIK + 12 tokens), which for the first time EXCEEDS the fixed 64-slot contact array. The
  entry-56 test only reached 64 (added one). So if this build black-screens, the 64-slot allocator
  (`fcn.80059e44` cursor wrap at 0x40) is the prime suspect, NOT append/shift mechanics.
- In-game interpretation:
  - Loads + all three extra orange tokens visible/collectible + orange meter updates: entries 54/55/57 are
    usable fixed-count sacrificial token slots (subject to normal gameplay regression). Also implies the
    runtime tolerates >64 visible-pickup constructions (or these markers free capacity elsewhere).
  - Loads but some tokens missing/uncollectible: identify WHICH entries failed; compare their original
    kinds/constructor paths (54=0x22, 55=0x23, 57=0x24) — they may differ in which become visible.
  - Black-screens: do NOT resume broad debugging. Recommend a one-at-a-time bisect (54 alone, 55 alone,
    57 alone) to find which marker (and/or the 65th/66th slot) is fatal.
  - FLIK/progression breaks: record which behavior changed and whether to avoid a specific marker entry
    (these three are the DAT-side FLIK trigger/marker kinds 0x22/0x23/0x24, so a FLIK side effect is plausible).
- RESULT (user, ABL_MARKERS54_55_57_KIND29_NEAR64_TEST): **LOADS, but the sacrifice REMOVED gameplay items.**
  Converting entries 54/55/57 (kinds 0x22/0x23/0x24) to 0x29 tokens made the following special pickups
  DISAPPEAR from LEVEL01: **mega homing berry, gold berry, super berry.** So these marker/action records
  are NOT inert/harmless — each backs a special berry / ability power-up pickup.

### ⛔ RECLASSIFICATION — entries 54..57 are special berry / power-up records, NOT safe sacrificial slots
Supersedes the earlier "invisible FLIK/action marker" framing for 54..57.
- **Entries 54, 55, 56, 57 are NOT safe generic sacrificial slots.** Repurposing them removes real gameplay
  items. Confirmed in-game by the build above: sacrificing 54/55/57 deleted the **mega homing berry**,
  **gold berry**, and **super berry** from LEVEL01. (Entry 56, kind 0x21, was the earlier single-marker
  test that *looked* harmless only because its one removed item was not noticed at the time.)
- New classification: DAT type-0x3f source kinds **0x20..0x24 are special berry / ability power-up
  marker/action records** (each tied to a specific berry/power-up), not invisible no-op markers. They emit
  a pickup ACTION (set 0x800a6597 + sound) without a visible-token construct, but the *item itself* exists
  and is lost when the record is overwritten.
- **Fixed-count "marker sacrifice" is dead as a production route.** It DID prove a marker slot can be
  turned into a visible/collectible token (entry 56, and 54/55/57 all rendered as orange tokens), but the
  cost is removing other gameplay items, so it cannot ship. Use it only as diagnostic evidence, not a mod.
- Do NOT overwrite entries 54..57 (or any 0x20..0x24 record) in production builds.

### NON-TOKEN APPEND DIAGNOSTIC — clone entry 56 (kind 0x21) as new entry 70 (BUILT, awaiting in-game result)
PIVOT back to true net-new injection. Goal: isolate WHETHER LEVEL01 tolerates a type-0x3f append AT ALL
when the appended entry is NOT a seed token — separating "append/insertion/shift mechanics" from
"new active visible-pickup pool pressure." The earlier failed append (`ABL_ADD_TOKEN0X29_NEAR64_TEST`)
added BOTH a structural append AND a new active 0x29 token; this test isolates the structural append only.
- Append source: existing entry 56 (kind 0x21, a special-berry marker/action that does NOT build a visible
  contact/render entity), cloned verbatim, NOT moved, NOT converted. So this append adds NO new visible
  pickup / contact-array (`0x800b0d18`) construction — it only exercises count 70->71 + post-0x3f shift.
- Tool: `python3 tools/add_level_entry.py DAT/LEVEL01_LEVEL.DAT --clone-entry 56 --out DAT/LEVEL01_LEVEL_APPEND_KIND21_ENTRY56_CLONE_TEST.DAT`
- Input DAT: `DAT/LEVEL01_LEVEL.DAT` (pristine, sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`, 332824 B).
- Output DAT: `DAT/LEVEL01_LEVEL_APPEND_KIND21_ENTRY56_CLONE_TEST.DAT`, size 332840 (+0x10), sha1
  `302c05bb81ad3f804c2b28b8a6c6d0ae3c1d71da`.
- Rebuilt image: `ABL_APPEND_KIND21_ENTRY56_CLONE_TEST.bin/.cue` (738285744 bytes, 313897 sectors).
- Appended bytes (new entry 70 @ file offset `0x468`): `990e0000000000008058000021000000`
  (= entry 56 exactly; XYZ `3737,0,22656`, kind 0x21). No existing entry altered.
- Verification (all PASS):
  - output size == input + 0x10 (332840 == 332824+16).
  - type-0x3f count 70 -> 71; top-level DAT record count unchanged (11).
  - entries 0..69 byte-identical to pristine; new entry 70 == entry 56 bytes exactly.
  - records after type-0x3f shifted by exactly +0x10 (0x468->0x478, 0x94c->0x95c, … 0x1370->0x1380),
    all shifted content byte-identical (orig[0x468:] == new[0x478:]).
  - rebuilt image embedded `LEVEL01/LEVEL.DAT` (LBA 2906, sector-aware) sha1 == `302c05bb…` == patched DAT,
    embedded type-0x3f count 71, embedded entry70 @0x468 == `990e…21000000`.
  - original DAT `DAT/LEVEL01_LEVEL.DAT` still pristine (`b376cb50…`); original retail image embedded DAT
    still pristine (`b376cb50…`); `Disney-Pixar A Bug's Life (v1.0).bin` untouched (mtime Apr 15 2012).
  - `REBUILD/files/LEVEL01/LEVEL.DAT` restored to pristine after build (cmp == LEVEL.DAT.orig).
- In-game interpretation matrix:
  - **Black-screens** → the failure is append/insertion/post-0x3f SHIFT mechanics (or a secondary
    structure that must be updated on append), NOT seed-token/pickup-pool logic. Next: post-parser/runtime
    RAM comparison (break after the `fcn.8001cdc0` walk and into the type-0x3f construct pass), NOT more
    token tests.
  - **Loads normally** → LEVEL01 tolerates count 71 + shifted later records structurally. The earlier
    append black-screen is then attributable to appending an ACTIVE visible pickup (a 0x29 token) that
    consumes runtime contact/render pool capacity with nothing removed. Next: append a token while reducing
    some other active construction, or directly inspect the 64-slot constructor (`fcn.80059e44`) capacity.
  - **Loads but berry behavior changes** (e.g. a duplicated berry marker fires twice / extra berry) → the
    appended kind 0x21 is not inert, but the append itself is structurally viable; record the behavior and
    pick a more inert append source for future structural-append tests.
- NUANCE on record: the fixed-count entry-56 kind-only test (9->10 seed-token-kind records, size/count/
  offsets unchanged) loaded fine, so the failed append is unlikely caused SOLELY by seed total 9->10. But
  10-token viability is diagnostic only — entries 54..57 are NOT a clean route (they remove berries).
- RESULT (user, ABL_APPEND_KIND21_ENTRY56_CLONE_TEST): reaches **"Press X to play"**; **after pressing X
  -> black screen / audio-only**, SAME failure as the 0x29 token append. So the non-token append reproduces
  the failure. This EXONERATES: seed-token kind 0x29, seed total 9->10, visible-token construction,
  pickup/contact/render pool pressure, and orange-meter/HUD logic. The failure is STRUCTURAL (the append's
  +0x10 shift), and it occurs at the load->live-gameplay transition AFTER Press X, not in the loader parser.


### NEXT DETERMINISTIC DIAGNOSTIC (append root-cause confirmation)
Static tracing already pins the mechanism; one emulator check would close it empirically. Recommended
breakpoint/dump pair (good = pristine ISO, bad = `ABL_APPEND_KIND21_ENTRY56_CLONE_TEST`):
- Break at **`0x8001cfa0`** (the pass-1 write-back `sw v0,2(s3)` of the relocated baked pointer), first
  iteration. Compare `s0`/`v0` (relocated pointer) and the source bytes at `s0`/`s0+0x14` between good and
  bad. PREDICTION: good `s0 = DATbase + 0x4680`; bad `s0 = DATbase + 0x4680` too, but in bad the intended
  geometry datum now lives at `DATbase + 0x4690` -> bad reads the wrong record (off by 0x10), confirming
  the stale relocation. If confirmed, stop diagnosing and switch to building the relocation-aware inserter.


## Special berry coordinate move tests (chronological)
### SPECIAL BERRY / POWER-UP move diagnostics — entries 54/55/57 (kinds 0x22/0x23/0x24) (BUILT, awaiting results)
Goal: move the three special berry/power-up pickups (mega homing berry, gold berry, super berry) one at a
time WITHOUT changing kind, so the user can identify which berry each entry backs. These are the three
entries the marker-sacrifice test removed when converted to 0x29 (entries 54/55/57). Fixed-size coordinate
edits only — NO append, NO count change, NO record shift, NO kind change.

**Entry→berry-name mapping: UNCERTAIN (LOW confidence).** The four berry-kind contact handlers
(`0x80054288`/`98`/`ac`/`c0`/`d4`) are symmetric — each only sets `0x800a6597` to a marker and plays a
sound, then `jal 0x80050994`; there is NO berry-specific power-up logic in code to distinguish them. The
berry *identity* (homing/gold/super) lives in the overlay model, not decoded. Per-kind signals (for the
user's identification only, not a proven name map):
| entry | kind | marker (`0x800a6597`) | sound | orig coords |
|------:|-----:|----------------------:|------:|-------------|
| 54 | 0x22 | 3 | 0x38 | (8587, -350, 13249) |
| 55 | 0x23 | 1 | 0x35 | (4110, 0, 1794) |
| 57 | 0x24 | 4 | 0x37 | (7661, -400, 16692) |
(Entry 56, kind 0x21, marker 2, sound 0x36 — also a berry, but NOT in this batch; it was the earlier
fixed-count/append clone source. Left untouched here to keep the batch to the three sacrifice-confirmed berries.)

**Movement (per-entry, auto-collect-aware; Z unchanged, kind unchanged):**
- entry 54 (high/deep start Y=-350): `dx +512, dy -256` → runtime Y -19392 (safe band).
- entry 55 (low start Y=0): `dx +1024, dy -512` → runtime Y -16384 (safe, more visible).
- entry 57 (highest/deepest start Y=-400): `dx +512, dy -256` → runtime Y -20992 (borderline-safe; small dy chosen).

**Byte diffs (entry layout +0=X +4=Y +8=Z +0xc=kind, all s32/u32 LE):**
| entry | off | orig bytes | new bytes | change |
|------:|----:|------------|-----------|--------|
| 54 | `0x368` | `8b210000a2feffffc133000022000000` | `8b230000a2fdffffc133000022000000` | X 8587→9099, Y -350→-606 |
| 55 | `0x378` | `0e100000000000000207000023000000` | `0e14000000feffff0207000023000000` | X 4110→5134, Y 0→-512 |
| 57 | `0x398` | `ed1d000070feffff3441000024000000` | `ed1f000070fdffff3441000024000000` | X 7661→8173, Y -400→-656 |

**Builds (one berry per ISO; all from pristine `b376cb50…`):**
| entry | DAT (sha1) | image |
|------:|-----------|-------|
| 54 | `LEVEL01_LEVEL_BERRY_ENTRY54_KIND22_MOVE_TEST.DAT` (`053a1e81…`) | `ABL_BERRY_ENTRY54_KIND22_MOVE_TEST.bin/.cue` |
| 55 | `LEVEL01_LEVEL_BERRY_ENTRY55_KIND23_MOVE_TEST.DAT` (`8c71ecfa…`) | `ABL_BERRY_ENTRY55_KIND23_MOVE_TEST.bin/.cue` |
| 57 | `LEVEL01_LEVEL_BERRY_ENTRY57_KIND24_MOVE_TEST.DAT` (`53ebda74…`) | `ABL_BERRY_ENTRY57_KIND24_MOVE_TEST.bin/.cue` |

**Verification (all three, all PASS):** DAT size == pristine (332824); type-0x3f count 70; only the one
intended entry changed; X/Y/Z as planned; kind unchanged; all other entries byte-identical; later records
(`0x468`+) unchanged/unshifted; embedded `LEVEL01/LEVEL.DAT` (LBA 2906, sector-aware) sha1 == the patched
DAT, count 70; original DAT + original image pristine (`b376cb50…`, `.bin` mtime Apr 15 2012);
`REBUILD/files/LEVEL01/LEVEL.DAT` restored after each build.

**Per-ISO interpretation:** whichever berry visibly relocates identifies that entry/kind. If a moved berry
auto-collects from afar → reduce dy (lean horizontal). If a berry vanishes (pushed out of render range) →
use horizontal-only move for that one. Power-up behavior should be unchanged (kind preserved). No other
berry should be affected (only one entry edited per ISO).

### ✅ SPECIAL BERRY MAPPING — CONFIRMED IN-GAME (entries 54/55/57)
User identified which berry moved in each single-entry ISO above:
| entry | kind | marker | sound | **berry (CONFIRMED in-game)** |
|------:|-----:|-------:|------:|-------------------------------|
| 54 | 0x22 | 3 | 0x38 | **Gold Berry** |
| 55 | 0x23 | 1 | 0x35 | **Blueberry / Superberry** |
| 57 | 0x24 | 4 | 0x37 | **Purple Berry / Mega Homing Berry** |
- These three are now CONFIRMED special-berry/power-up placement records in LEVEL01\LEVEL.DAT type-0x3f.
  Coordinate movement works via the same fixed-size DAT edit pipeline as grain/FLIK/tokens (runtime=file<<5).
- Remaining berry at the time = **Green Berry / Homing Berry**, entry 56 / kind 0x21 (marker 2, sound 0x36)
  — since CONFIRMED by the entry-56 move test below (see "MAPPING COMPLETE").
- DAT type-0x3f source-kind map (ALL CONFIRMED in-game): `0x21`=Green Berry/Homing, `0x22`=Gold Berry,
  `0x23`=Blueberry/Superberry, `0x24`=Purple/Mega-Homing Berry. (Supersedes the older "FLIK trigger/marker"
  label for 0x21..0x24 — they are the special berries; the `0x800a6597` marker write is the berry's effect trigger.)

### ✅ GREEN/HOMING BERRY — entry 56 kind 0x21 move diagnostic (PASS, confirmed in-game)
Goal: move the last untested berry-kind entry (56) to confirm it backs the Green Berry / Homing Berry.
Fixed-size coordinate edit only — NO append, NO count change, NO record shift, NO kind change.
- Input: `DAT/LEVEL01_LEVEL.DAT` (pristine `b376cb506f437a1cda721fd13766ddbca7c6a247`, 332824 B).
- Output DAT: `DAT/LEVEL01_LEVEL_BERRY_ENTRY56_KIND21_MOVE_TEST.DAT` (sha1 `48b20c6e44f56f48c28c7eaf355a965382099c72`, 332824 B).
- Image: `ABL_BERRY_ENTRY56_KIND21_MOVE_TEST.bin/.cue` (738285744 B).
- Entry 56 @ `0x388`: move `dx +1024, dy -512, dz 0`; coords `(3737,0,22656) -> (4761,-512,22656)`;
  kind `0x21` UNCHANGED; runtime Y -16384 (safe band).
  - orig bytes: `990e0000000000008058000021000000`
  - new  bytes: `9912000000feffff8058000021000000`
- Verification (all PASS): DAT size == pristine (332824); type-0x3f count 70; ONLY entry 56 changed;
  entries 0..55 & 57..69 byte-identical; X/Y/Z as planned; kind 0x21 unchanged; later records (`0x468`+)
  unchanged/unshifted; embedded `LEVEL01/LEVEL.DAT` (LBA 2906, sector-aware) sha1 == `48b20c6e…` == patched
  DAT (count 70, entry56 `9912…21000000`); original DAT + original image pristine (`b376cb50…`, `.bin` mtime
  Apr 15 2012); `REBUILD/files/LEVEL01/LEVEL.DAT` restored after build.
- RESULT (user, ABL_BERRY_ENTRY56_KIND21_MOVE_TEST): **PASS.** Loaded; the Green/Homing berry moved; moved
  item visible; collectible; power-up behavior still works; no crash/glitch. → **entry 56 / kind 0x21 =
  Green Berry / Homing Berry CONFIRMED.** This completes the LEVEL01 special-berry map (0x21..0x24).


### 🛠 GEOMETRY G1 — record-map correction (rec10 `-7` is NOT a blob to EOF)
Read-only inventory pass (no DAT/BIN/CUE mutation). Supersedes an earlier loose note.
- **Superseded claim:** `DAT_FORMAT_AND_RELOCATION.md` rec10 note "(bulk geometry blob to EOF)".
- **Correction (CONFIRMED):** by the parser size rule, rec10 (`-7`, count 64) is a fixed `0x190`-byte
  packed record ending at `0x1500`. All 11 top-level records end at `0x1500`; the post-record word
  there is `0`, so the trailing block begins at `0x1504`.
- **Geometry-data region (CONFIRMED):** all 1248 LEVEL01 relocation targets land in `[0x45f0, 0x4f32c]`
  (0 inside records, 0 inside trailing tables). Split: source-record band `[0x45f0, 0x8bd8)` (624
  `[s3+2]` targets) and payload band `[0x8bd8, 0x4f32c]` (624 `[s0+0x14]/[s0+0x1c]` sub-pointers).
- **Trailing tables (CONFIRMED):** pass1 484 entries @`0x1512`; pass2 EMPTY @`0x3ae8` (`[p2]=-1`);
  pass3 140 entries @`0x3afa`.
- Detail: [src_re_geometry/level01_dat_geometry_inventory.md](../src_re_geometry/level01_dat_geometry_inventory.md),
  [docs/GEOMETRY_RE_PLAN.md](GEOMETRY_RE_PLAN.md). Open for G2: source-record stride/size
  (`0x18` observed vs parser reading `[s0+0x1c]`).

### 🛠 GEOMETRY G6 — render sentinel diagnostic image built and tested
Prepared a reversible render-stage diagnostic test from the G5.5 confirmed trail/pass1 flag read.
This is a same-size two-byte DAT patch only; no relocation-aware insertion and no game-data commit.

- Active rebuild DAT verified: `REBUILD/files/LEVEL01/LEVEL.DAT`, size `332824`, SHA256
  `786b7a964129d4fee6a1983b356e172d406b17663d87b8befe645b92dbf08b53`, bytes at `0x1526` =
  `41 00`.
- Patch script: `tools/patch_g6_render_sentinel_test.py`.
- Patch: `LEVEL01/LEVEL.DAT+0x1526`: `41 00` -> `ff ff`; revert bytes `41 00`.
- Patched DAT: `DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST.DAT`, size `332824`, SHA256
  `149419dd724943dafa101b29e3a2bec179e188ebc0c93e8f42b1a095fea6c31a`, SHA1
  `717a0875f28fd8c93c6db9209c5e7981f3fcc97d`.
- Rebuild command:
  `python3 tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST.DAT --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G6_RENDER_SENTINEL_TEST.bin --out-cue ABL_G6_RENDER_SENTINEL_TEST.cue --write --report DAT/LEVEL01_LEVEL_G6_SENTINEL_TEST_REBUILD.md`
- Output image: `ABL_G6_RENDER_SENTINEL_TEST.bin/.cue`; embedded `LEVEL01/LEVEL.DAT` at LBA 2906
  verified SHA1 `717a0875f28fd8c93c6db9209c5e7981f3fcc97d`; staged rebuild DAT restored.
- Emulator result (user, `ABL_G6_RENDER_SENTINEL_TEST.cue`): PASS as a render-stage diagnostic.
  The image reaches title/menu and enters LEVEL01. Standing still, terrain/ground render is mostly
  empty/missing while background sky and some horizon/grass/backdrop remain visible; Flik, objects,
  enemy/props still load; no black screen and no crash.
- After movement: Flik can stand and move on the invisible/missing terrain in the tested area; objects
  still load. This indicates the tested collision/ground behavior remains usable while visual terrain
  is removed, but it does not map the full collision/pathing pipeline.
- Interpretation: `DAT+0x1526` / pass-1 trail entry1 flag/sentinel controls render-stage trail
  scanning/visibility. This supports render/collision separation for this field: visual terrain can be
  removed while tested ground collision remains. Collision/pathing impact remains **UNKNOWN** beyond
  the tested area and is not collision-aware evidence.


---

**Related docs:** [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md) · [COORDINATE_MODDING.md](COORDINATE_MODDING.md) · [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)
