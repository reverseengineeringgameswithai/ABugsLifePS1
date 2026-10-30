---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay - Input and Movement.md
aliases:
  - "Gameplay - Input and Movement"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay - Input and Movement.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Gameplay_-_Input_and_Movement.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay - Input and Movement
type: core
updated: 2026-06-21
tags: [core, gameplay, input, libpad, player, milestone6, gap-0037]
---

# Gameplay — Input & Movement (GAP-0037 — input law decoded, static)

> M6 parallel lane ([[Gap Audit|GAP-0037]]) — the player **input→movement law**. **Decoded 2026-06-21 (static, EXE-read, reproducible):** the pad decode (`0x800512a0`), the working button word (`0x80082488`), and the button→heading/throttle→GTE→velocity chain are mapped from the disassembly (key sites spot-verified). The only residual is the libpad ISR PC that writes the raw buffer `0x80082412` (BOUNDED — one write-watch names it). Player block + integrator were STATIC/CONFIRMED (+ prior DYNAMIC local-only G29). Any runtime step is local-only ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Player state structure (STATIC + DYNAMIC, CONFIRMED)
| Addr | Symbol / role | Conf |
|---|---|---|
| `0x800A6500` | `player_x` (block base) | CONFIRMED |
| `0x800A6504` | `player_y` (collision-resolved) | CONFIRMED |
| `0x800A6508` | `player_z` | CONFIRMED |
| `0x800A652C` | `player_velocity_delta` (per-frame velocity) | CONFIRMED (sym) |
| `0x800A6582` | contact flags (read by integrator `a2`) | LIKELY |
→ [[MEM - Player state 800A6500]].

## Movement integrator (CONFIRMED — DYNAMIC/local-only, G29)
**`[[FUNC_8003633C]]`** = the per-frame collision/movement integrator on `a0` = position struct; for the player it commits the resolved Y at the decisive store **`0x80036cec`** (reads `[sp+0x1c]`). Inputs: `a1`/`s5` = `0x800a652c` (velocity), `a2` = `0x800a6582` (contact flags). Callees `fcn.80035f24` (collision sweep) · [[FUNC_800345CC]] (resolve) · `fcn.80035280`. Callers `0x800495c8` / `0x8004c024` / `0x8004e628`. *(Writer identified via live WRITE-watch — local-only.)*

> **Superseded:** [[FUNC_8005B134]] (old "sole player-pos writer" guess) is an 8-way state handler (table `0x8001b828`, `v0∈[3,10]`, 0 idle hits) — **not** the writer ([[Open Questions]] P2 #3).

## libpad / input read site (LOCATED — static, EXE-read 2026-06-21, key sites spot-verified)
Decoded **statically** (`tools/exe_read.py ./SCUS_942.88 --disasm` / `--store-ea`) — no event-state fixture needed:
- **Working button word = `0x80082488`** (game-internal halfword, **active-HIGH**: bit set = pressed). Read across the player code via `lhu …,9352(0x8008)` then `andi` against button bits.
- **Pad decode / poll = `0x800512a0`** (CONFIRMED — instructions verified): reads the **raw libpad button buffer `0x80082412`** (`lhu a1,9234(0x8008)`), masks the low 12 bits (`andi a2,a1,0xfff` = d-pad + L/R + Select/Start), stores to `0x80082488` (`sh a2,9352`), then **synthesizes the face buttons** from a config table at `0x80078c28[(cursor&0x7f)*6]` (e.g. Cross `ori 0x4000` @ `0x800512e0`). Pad cursor `0x8009ec7d`.
- **REFUTED:** the prior provisional `fcn.80055414/80055538` is **NOT** the player pad reader (it is pad-pattern init + a per-frame timer/anim/sound SM). Likewise `0x800910a2` (read by the GTE movers) is an **animation phase counter**, not a button mask. ([[Open Questions]] P5 #15 → BOUNDED.)
- **Pad-poll wrapper = `0x8003a2dc`** (LOCATED — runtime write-watch on `0x80082412` named it 2026-06-21): saves the previous word to `0x800822e4` (edge-detect / "just-pressed"), calls the actual pad-read **`0x80039c34(a0=1)`**, and stores the fresh word to `0x80082412` (`sh v0,9234` @ `0x8003a300`). So the controller chain is `0x80039c34` (read) → `0x8003a2dc` (raw buffer `0x80082412` + prev `0x800822e4`) → `0x800512a0` (working word `0x80082488`) → player code.

## Input → movement law (CONFIRMED — static, EXE-read; pad-decode + Up + Left/Right independently spot-verified)
Button bits drive **heading** (player struct `+0x28`) and **throttle speed**, which are rotated by heading through the **GTE** (cop2, `0x800602e0/0x80060284`) into the velocity vector `0x800a652c/30/34`, then integrated by [[FUNC_8003633C]] → `0x800a6504`:

| Button (bit in `0x80082488`) | Site | Effect |
|---|---|---|
| **Left** (`0x80`) | `0x800491e0` | heading `[s1+0x28] -= 1024` |
| **Right** (`0x20`) | `0x80049208` | heading `[s1+0x28] += 1024` |
| **Up** (`0x10`) | `0x8004e050` | forward speed `s0 = 0x8000` |
| **Down** (`0x40`) | `0x8004e03c` | speed `s1=12288 / s0=4096` |
| **R1** (`0x800`) | `0x8004e064` | boost (writes `3→gp+1160`, `s3=1400`) |
| **Cross** (`0x4000`) | `0x80048ef4` | jump |
| **Square** (`0x8000`) | `0x80048f54` | (action) |

After the d-pad sets heading/throttle, the speed clamps (`gp+1256`/`gp+1736`, ±2304/±1024 steps) and the heading auto-steers via `atan2` (`0x80060ae4`, 4096-unit `0xfff` angle space); the resolved speed×heading is GTE-rotated into `0x800a652c/30/34`. Player movement code spans `0x80048e00..0x8004e3xx`.

> **Distinct lane:** the absolute velocity writers at `0x800423c8/47bd0/4a774/4b004/4b0a0/4b5a4` are **AI/animation movers** (NPCs/scripted actors rotating a speed vector via GTE, gated by anim counter `0x800910a2`) — **not** the D-pad path. The player's input→velocity goes through the heading/throttle chain above.

## Runtime confirmation (LOCAL-ONLY — RAN 2026-06-21, isolated DuckStation port 23460 / `level02.sav`)
`tools/abl_dbg.py` + `accessLog.addWatch` + `emulator.setControllerState` (scratch `gap0037_*.py`; instance stopped after):
- **`accessLog WRITE 0x80082412` → writer PC `0x8003a304`** (return of the `0x8003a2dc` wrapper) — confirms the pad-poll wrapper above.
- **`accessLog WRITE 0x80082488` → writer PC `0x800512d4`** — confirms the pad-decode store at `0x800512a0`.
- **Bit layout matches standard PSX** (clean per-button raw `0x80082412`): Down=`0x40`, Right=`0x20`, Square=`0x8000`, Circle=`0x2000`; and **face-button synthesis confirmed** — Square appears in the working word (`0x8000`) while Circle (`0x2000`) is dropped by the `0xfff` mask.
- **input→velocity→position confirmed:** holding **Up** 8 frames → `velX(0x800a652c)=332`, player X `+780`, Z `+360`, heading auto-steered (`0x766→0x2e6`). Holding **Left** vs **Right** produced opposite heading changes. *(Exact per-frame ∓1024 turn rate is the static law; at runtime it is modulated by the atan2 auto-steer.)*

## Confidence ledger
Player block + integrator `FUNC_8003633C` + velocity `0x800a652c` — **CONFIRMED** (static + local-only G29). Button word `0x80082488` + pad decode `0x800512a0` + the Left/Right/Up/Down/R1 → heading/speed map — **CONFIRMED (static EXE-read + runtime: writer PCs `0x8003a304`/`0x800512d4` and input→velocity→position observed live)**. Pad-poll wrapper `0x8003a2dc` → pad-read `0x80039c34` → raw buffer `0x80082412` — **LOCATED** (runtime write-watch). Prior `fcn.80055414` candidate — **REFUTED**.

## Next experiments / modding relevance
Run the trace above (operator/local) → bridge pad→velocity → locate libpad. **Modding:** input remaps, TAS fidelity, and completing the player model for the editor's behavior preview. **Dependency:** GAP-0001 (fork); independent of GAP-0023/0028/0033.

## See also
[[Gameplay Systems Baseline]] · [[MEM - Player state 800A6500]] · [[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_8005B134]] · [[API - controller input]] · [[Physics]] · [[DuckStation Fork Reproducibility]]
