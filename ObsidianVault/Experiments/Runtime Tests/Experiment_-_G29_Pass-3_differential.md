---
kind: experiment
id: Experiment_-_G29_Pass-3_differential
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G29 Pass-3 differential.md
aliases:
  - "Experiment - G29 Pass-3 differential"
---

# Experiment — G29 Pass-3 differential (visual edit ⇏ collision)

> Migrated from `ObsidianVault/Experiments/Experiment - G29 Pass-3 differential.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G29 Pass-3 differential (visual edit ⇏ collision)

> **The decisive proof of visual ≠ collision** (GAP-0038, B3). A read-watch on the **collision** source on a **pristine** vs a **G28-visual-edited** disc: the visual terrain deforms (proven, G28) while the collision-floor source bytes are **identical** between runs ⇒ the two are causally independent. **DONE 2026-06-21 — both arms run.** A phase-matched pristine-vs-G28 differential differs in **exactly the one visual-edit halfword** (`5001`→`6025`); every collision artifact (sector-table SHA-256, resolver candidate/plane reads, the player-Y writer path, and Flik's exact footing trajectory) is **byte-identical**. The visual edit changes nothing on the collision side.

## Question
Does editing the **visible** terrain (the G28 `v16.y +1024` DAT edit to Candidate A) change the **collision** floor source the player's footing reads? Expected (if visual ≠ collision): **no** — the collision-Y source is the chunk-32 sector table, untouched by a DAT visual-mesh edit.

## Prior result being hardened
- [[Finding - Visual is not collision]]: visual (LEVEL.DAT / `fcn.80010000`, now incl. spawn — [[Experiment - Spawn-floor render source]]) ≠ collision (LEVEL.RAW chunk 32 sector table `0x800a7e48`; player-Y writer [[FUNC_8003633C]]).
- The visual half rests on **one** G28 build (single edit, one viewing) — GAP-0038. Pass-3 is the missing **independent, counterfactual** half: same edit, but measured on the **collision** side.

## Addresses / functions
| Symbol | Address | Role |
|---|---|---|
| Flik world Y | `0x800a6504` | footing height (integrator output) |
| player-Y writer | [[FUNC_8003633C]] | integrates velocity → Y; floor-clamps |
| collision sector table | `0x800a7e48` | LEVEL.RAW **chunk 32** planes (footing source) |
| player sector record | `0x800aa128` (Y at `+4` = `0x800aa12c`) | localized footing lever (sec186, per G30) |
| visual floor source | DAT `~0x8018xxxx` (file `0x15dec..0x2f59c`) | `fcn.80010000` payloads (incl. Candidate A `0x188cc`) |

## Method (exact calls)
**Arm A — pristine baseline (captured 2026-06-21):**
1. Cold-boot the pristine cue and replay `flik_to_level01_stall.mv.movie.json` from boot; assert `game_serial==SCUS-94288`, `scene_id==1`, exact spawn XYZ `(197091,2734,492897)`. The movie ends with the **in-game START pause menu** open; dismiss it with Cross for 3 frames before tracing.
2. `accessLog.addWatch {address:0x800aa12c, length:4, type:"read"}` and `accessLog.addWatch {address:0x800a7e48, length:64, type:"read"}` (re-arm AFTER load — `loadState` clears watches).
3. Also watch candidate-plane list `0x8009c230` (176 B), player Y `0x800a6504` (WRITE), and the documented spawn candidate-sector records. Hold Left for exactly 8 frames (idle does not run player collision in this fixture).
4. Hash both the 512-byte table head and all 223 × `0x30` sector records before/after.

**Arm B — G28-visual-edited disc (DONE 2026-06-21):**
5. Build the G28 edit (`v16.y +1024` at DAT `0x18992`, the Candidate-A payload) into a **separate** output disc via `tools/rebuild_with_patched_dat.py --write` (keep the pristine `.bin/.cue` untouched). Embedded-bytes verification confirms the patched DAT lands at LBA 2906.
6. Boot that disc in a fresh isolated instance (`launch_debugger_instance.sh start --disc <G28 cue>`) — there is **no** save state on the edited image, so reach the spawn via the `flik_to_level01_stall` from-boot movie (its `start_state.from_boot=true`, empty disc path ⇒ it boots whatever media is mounted).
7. Run `tools/trace_g29_pass3_arm_b.py` (same watch set, controller input, and timing as Arm A) **plus** a read of the resident DAT visual-edit halfword at `0x8017918a` (= DAT base `0x801607f8` + file `0x18992`; pristine 5001, patched 6025) as the decisive disc-identity guard.

**Differential (`tools/trace_g29_pass3_arm_b.py` is disc-parameterised, so the pristine baseline reruns through the same instrument):**
8. Compare Arm A vs Arm B **in the same capture phase**: the sector-table bytes, the resolver candidate/plane reads, the player-Y writer path, and the footing trajectory must be identical while only the visual halfword differs.

## Expected result
Collision source bytes **unchanged** between pristine and visual-edited; visible terrain **changed**. ⇒ visual ≠ collision corroborated by a **second independent method** (counterfactual), closing the GAP-0038 "≥2 independent confirmations" bar together with the spawn-area source separation already shown.

## Observed result
- **Arm A (pristine baseline): CAPTURED 2026-06-21.** Replay: `python tools/trace_g29_pass3_arm_a.py --movie "$PWD/flik_to_level01_stall.mv.movie.json" --output /tmp/g29-pass3-arm-a.json` against the isolated pristine instance.
  - Fixture movie SHA-256 `a8b87ffedcc6305193eca0ec1c09b66b1073b8c2fe3211f6ee39cd916c86e079`; pristine cue SHA-256 `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`; serial `SCUS-94288`; scene 1; exact spawn XYZ `(197091,2734,492897)`.
  - `SCUS-94288_1.sav` was rejected for Arm A despite reaching the same XYZ: metadata binds it to `REBUILD/ABL_PILL.cue` (SHA-256 `8fefa61e7c40205f79d536c9eb94ff7d2ced611a86cf94ec4bec8ba1120ea785`). `_1_copy.sav` is pristine-disc-backed (`53eecd18c67ad09bcc8532cf7acbff3dd8691217233af55ccee4fc913cb86857`) but is not at spawn. The from-boot movie avoids both fixture defects.
  - Capture interval: frames **6475→6483**, cycles **3665588172→3670117802**, after Cross ×3 dismissed the in-game pause; Left held for 8 frames. Player XYZ moved `(197091,2734,492897)` → `(196620,2775,491961)`.
  - Collision candidate list `0x8009c230`: **88 reads**. `0x8003463c` (inside [[FUNC_800345CC]]) read the active `0x800c/0x800d` plane pointers 20× (five per collision frame: `0x800ccc60, 0x800cd0d0, 0x800cd0f0, 0x800cd110, 0x800cd130`); `0x800380f4` read further candidate lists 68×.
  - Player Y `0x800a6504`: **12 writes** over frames 6476/6478/6480/6482, reported at `0x80036384`, `0x80036cf0`, `0x80036d58` (four each), all inside [[FUNC_8003633C]]. DuckStation reports these data-watch PCs as store+4; the decisive middle store is therefore the known `0x80036cec`. `lastWriter.callStack=[]`; the API does not retain a usable call stack here. Its decoded `new_value` is also not authoritative under this +4 convention; use the ordered raw events/pre-write values.
  - Full sector-table SHA-256 before/after: **`6b7d858f913b7f04fb40ed45f673cc264a0dd4a34a7fc045db982b4e91499793`** (unchanged). Head-512 SHA-256: **`56af4a48cb566f7f841a5ddf253d48e00ca3f22b357b2a75932bff3a155735b5`** (unchanged).
  - The planned `0x800a7e48+0..0x3f` and `0x800aa12c` read watches had **0 hits** in this short exact-spawn window. `0x800aa12c` is sector-186 Y for the G30 openground fixture, not this spawn. The documented candidate-sector record watches also had 0 hits because this interval consumed the already-built candidate list/plane pointers; zero hits are not treated as absence of collision.
- **Arm B (edited disc): CAPTURED 2026-06-21.** The missing BIN was regenerated locally (see *Rebuild* below) and booted in a fresh isolated instance on the G28 cue (serial `SCUS-94288`, `game_path` = the G28 cue). Replay: `python tools/trace_g29_pass3_arm_b.py --disc <G28 cue> --movie "$PWD/flik_to_level01_stall.mv.movie.json" --expect-visual 6025 --output /tmp/g29-pass3-arm-b.json` (`arm_captured=true`).
  - **Visual edit resident:** the DAT halfword at `0x8017918a` read **6025** (patched) on the G28 disc vs **5001** on pristine — proving the edited LEVEL.DAT reached RAM. The window `…208913181c…` (pristine) → `…208917181c…` (G28) differs only in that halfword (`0x1389`=5001 → `0x1789`=6025). Independently cross-checked: `level01.sav` (pristine) reads 5001 at the same address.
  - **Collision side unchanged:** full 223×`0x30` sector-table SHA-256 **`6b7d858f…9793`** and head-512 **`56af4a48…35b5`** — identical to Arm A; `spawn_sector124_y = -87520` identical; resolver read all 5 active planes (`0x800ccc60/cd0d0/cd0f0/cd110/cd130`); player-Y writer PCs `0x80036384/0x80036cf0/0x80036d58` (4 each) identical.
  - **Phase-matched decisive differential:** the from-boot movie always reached the exact spawn `(197091,2734,492897)`, but the post-spawn capture micro-phase is fixed *per instance launch* (deterministic across repeated traces on one instance; varies launch-to-launch) — it lands either a "grounded" phase (final Y `+2775`, resolver read PC `0x8003463c`, 88 candidate reads) or a "falling" phase (final Y `-2962`, PC `0x80035304`, 112 reads). **This phase is disc-independent**: the *pristine* disc produced both phases across launches (launch 2 of a sample fell to the exact G28 spot). Comparing a **phase-matched** pristine-vs-G28 pair (both falling) yields **exactly 6 structural differences — all of them the visual-edit halfword** (`before/after visual value 5001 vs 6025`, the two `window_hex`, `visual_edit_is_patched`, `visual_edit_value`); the collision sector hash, candidate/plane reads (PCs+values+counts), player-Y writer PCs **and** delta values, and the exact final XYZ `(196704,-2962,492130)` are byte-identical. ⇒ the visual edit perturbs **nothing** on the collision side, not even Flik's precise fall path.
  - Local-only artifacts (not committed; `.bin/.cue` gitignored): rebuilt disc `REBUILD/g29_armb/ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.{bin,cue}` (BIN SHA-256 `18e9b1f83eae73cfa0b821e715ffa5a6e62d4447ecbd82be487f7bc17ef0a0ac`, 738,285,744 B); traces `/tmp/g29-pass3-arm-b.json`, `/tmp/pri_falling.json` (pristine phase-match), `/tmp/g29-pass3-arm-a-rebaseline.json` (pristine grounded baseline).

### Rebuild (G28 BIN regeneration, local-only)
- Command: `python tools/rebuild_with_patched_dat.py --patched-dat DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST.DAT --expected-sha1 a1cf8d8e638460b4861f4d405872bff0a2738f5f --target files/LEVEL01/LEVEL.DAT --out-bin REBUILD/g29_armb/ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.bin --out-cue REBUILD/g29_armb/ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue --write --force-output`.
- Inputs: patched DAT SHA-1 `a1cf8d8e638460b4861f4d405872bff0a2738f5f` (= pristine `DAT/LEVEL01_LEVEL.DAT` SHA-1 `b376cb50…` with one halfword changed at file `0x18992`: `5001`→`6025`); manifest `REBUILD/abl.xml`; mkpsxiso 2.20. The tool stages the patched DAT, rebuilds, **verifies embedded bytes** (LBA 2906, SHA-1 `a1cf8d8e…`), and **restores** the staged `REBUILD/files/LEVEL01/LEVEL.DAT` to pristine `b376cb50…`. Pristine `Disney-Pixar A Bug's Life (v1.0).bin/.cue` left untouched.

## Evidence grade
- **Confidence: CONFIRMED.** Both arms ran; a phase-matched pristine-vs-G28 differential isolates the visual-edit halfword as the **only** difference while every collision artifact is byte-identical. The decisive collision-source invariant (sector-table SHA-256) is deterministic and identical across all runs and both discs.
- **Caveat (bounded):** the counterfactual rests on **one edit, one payload (Candidate A), one scene (LEVEL01)**. A second edit/scene would harden the general "visual ⇏ collision" claim further (optional; see GAP-0038 residual).
- **Reproducibility caveat:** the from-boot movie reaches the exact spawn every run, but the post-spawn capture phase is fixed per instance launch and varies launch-to-launch; the *trajectory/exact-read-PC* are only comparable within a matched phase, whereas the *sector-table hash* invariant is phase-robust. Relates to [[API - determinism]] / GAP-0040.
- **Reproducible without the operator's environment:** No — needs the fork + disc build + a spawn fixture (**GAP-0001/0024/0025**). A replay is one command on the operator's machine.

## Status / next action
**Confirmed — both arms complete (2026-06-21).** The owed pristine-vs-patched counterfactual is done: editing the visible DAT terrain (Candidate A `v.y +1024`) leaves the collision source bytes, the resolver/player-Y code path, and Flik's footing **identical**. Combined with the spawn-area **source separation** ([[Experiment - Spawn-floor render source]]), the visual ≠ collision headline now meets its ≥2-independent-methods / counterfactual bar. Optional residual: a second edit or non-LEVEL01 scene for extra generality hardening (not blocking).

## Related
[[Experiment - Spawn-floor render source]] · [[Finding - Visual is not collision]] · [[Finding - Candidate A is DAT-backed visual terrain]] · [[FUNC_8003633C]] · [[API - accessLog]] · [[API - experiment runner]] · [[Playbook - Replay headline experiments]] · [[Verification - M7 Headline Recheck]]
