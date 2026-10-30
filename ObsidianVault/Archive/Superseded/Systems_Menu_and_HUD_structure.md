---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Menu and HUD structure.md
aliases:
  - "Menu and HUD structure"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Menu and HUD structure.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Menu_and_HUD_structure.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Menu and HUD structure
type: system
confidence: CONFIRMED (structure) / PARTIAL (RE)
tags: [system, gui, menu, hud, status-icons, frontend]
updated: 2026-07-07
---

# Menu & HUD structure (front-end + status icons)

> Operator-confirmed map of A Bug's Life (PS1) front-end: title → main menu → sub-screens, the pause/exit flow, and the **SELECT status-icon HUD**. The *structure/contents* are confirmed from gameplay; the *code/RAM* is RE'd only where noted. **Focus of this note: the Status Icons / HUD** (§3) — those tie to real player-state RAM ([[MEM - Player state 800A6500]]).

> [!note] Provenance: menu/HUD **contents** = operator-confirmed (2026-06-18). RAM addresses + the HUD draw function are RE-confirmed from prior work; menu **logic/navigation/rendering** is **not** decoded (see §5).

## 1. Menu tree (confirmed contents)
```
Title screen ──[START]──► Main Menu  (vine/leaf interface)
  Main Menu leaves:
    • Options
    • Load / Save
    • Movie Clips
    • Training
    • Anthill
    • (Other levels — appear as they unlock)
```
- **Options:** Change Controls · Music Volume · SFX Volume · Vibration · Centre Screen.
- **Load / Save:** Memory-Card save/load screens; game uses **1 block**.
- **Movie Clips:** rewatch clips unlocked by completing sections (the `.STR` FMVs → [[Blocker - FMV video is completely unanalyzed|FMV extraction]]).
- **Training / Anthill / levels:** stage entries (the level-warp target → [[Finding - Level-warp mechanism]] sets stage `[0x80082504]`).

## 2. Pause / Exit Level (confirmed)
- **START** during gameplay → pause.
- Confirmed **Exit Level** flow with an **"are you sure? — yes / no"** confirmation prompt.
- The **telescope** (kind `0x30`) hint device pops a related **"continue / exit level"** menu in-level → [[Experiment - Pickup kind-swap]] (telescope = the green hint object; reveals an item/exit).

## 3. Status Icons / HUD — FOCUS
**SELECT** during gameplay shows the status-icon panel. Five elements; mapped to RE where known:

| Status icon | RE status | RAM / evidence |
|---|---|---|
| **FLIK letters** | ✅ confirmed | **FLIK bitmask `0x800A65A2`** (retail bits 0–3 = F/L/I/K collected; retail completion mask `0x0f`) · FLIK/berry marker `0x800A6597` (0..4). The letters themselves = real native type-0x3f collectible entries 50–53 (kinds 0x10/0x11/0x12/0x13) → [[MEM - Type-0x3f placement record]]. Tier-3 relocation proof: [[Experiment - Tier3 native FLIK letter relocation]] moved all four onto the custom platform, collected them, set the bitmask to `0x0f`, and pulsed `0x800B0194`. FLIK5 test: [[Experiment - FLIK5 five-letter token gate]] appended a duplicate native F entry and patched completion to mask `0x1f`; after four letters progress stayed unchanged, after five it advanced. *(NB: `0x800A65A0`, once thought to be "FLIK F progress", is actually **lives/progress byte** — see below.)* |
| **Health leaf** | ✅ **`0x800a7e2a` (s16)** | The SELECT panel reads it (`lh` at `0x80052c10`) to draw the leaf; full = 7, decreases **flat −1 per hit** (uniform across enemies — RCG-021, 2026-07-03), `0` = last HP (next hit → death). ⚠️ **Correction (2026-07-03):** `0x800910a8` is NOT a mirror — it (and `0x800910a9/aa`) are **HUD leaf-spin animation counters**; and in gameplay the in-game HUD reuses/animates the `0x800a7e2a` cluster (raw live reads cycle 0..7 while moving/flashing) — the AT-REST / SELECT value is the true health. Health-leaf drop/collect + the mercy counter `0x800a6594`: see `src_re/player_health.c` + `src_re/enemy_drops.c`. |
| **Seed power** | ✅ | **seed-token counters `0x800A6598 / 99 / 9a`** (kinds 0x29/0x2a/0x2b; encoding `(n&7)*17`). Seed *planting* is a separate system → [[Seed planting system]] |
| **Lives** | ✅ **`0x800a65a0` (u8)** | **CONFIRMED gating/editable counter** (2026-06-18): goes 4→3 on losing a life, and poking it to 3 in the last-life state made the fatal hit **respawn with no game-over** (it decremented 3→2). `0` = last life (next death → game-over). ⚠️ This byte was **mislabeled "FLIK F progress" / "progress latch"** in the vault — it is lives. (`0x8008242c`, which the panel also reads, is just a recomputed display mirror — not editable.) |
| **Grain count** | ✅ | **`0x800A65A1`** (target `0x32` = 50) |

- All confirmed counters live in the **per-level progress block** [[MEM - Player state 800A6500]] (`0x800A6597…0x800A65A2`) — the most-watched RAM in the project.
- **In-game HUD draw** = [[FUNC_800526F4]] (`hud_draw`, runs each frame from `fcn.8004ecd4`; `a0` = animation step for the pulse). Confirmed it draws: **progress, seed total, grain, FLIK bits, seed meters, FLIK record icons** (+ scene-specific panels still TODO). Sub-routines: **`fcn.800260f8` = draw number/glyph**, **`fcn.80025f54` = draw sprite/tile**, `fcn.80026588/a68/df4` = rect/effect, `fcn.80026d78` = flush. Extra globals it reads: **FLIK record ptrs `0x800a0220/0430/0a60/0d78`**, **pulse halfwords `0x800b0188..19c`**, sin table `0x80074970`. (Notably it does **not** touch health/lives — consistent with those being unmapped.)
- **Bottom gold-defeat counter:** the misc/gold pulse panel (`0x800b0198`) displays
  `LW(0x80082258) - LH(0x800a658e)`. This is why the [[Gold-berry drop on non-gold kills]]
  pickup hook increments the visible counter by decrementing `0x800a658e`.
- **SELECT status-panel render = `fcn ~0x80052a80` (PCs `0x80052b5c`–`0x80052f74`)** — a sibling of `hud_draw`, runs only while **SELECT is held** (~1 s to appear). Confirmed reads: grain `0x800a65a1`, FLIK `0x800a65a2`, **health `0x800a7e2a`** (`lh`), **lives-display `0x8008242c`** (`lw`), and a score line `LW(0x80082258) − LH(0x800a658e)`. Found by read-watching grain/FLIK only-when-SELECT-held → its PCs → disasm of its global loads.
- **FLIK5 SELECT-panel patch (2026-07-05):** drawing a fifth letter safely means adding an extra draw call
  for tile `0x10` at `x=0xd0`. Do **not** overwrite the kind/descriptor table to manufacture a fake F
  kind: that corrupted the top-left Flik-head status icon. The corrected FLIK5 build leaves native
  descriptors untouched; screenshot `/tmp/flik5_select_fixed.png` showed normal Flik head and `FLIKF`.
- **Training 8-letter SELECT-panel patch (2026-07-07):** scene-gated first-letter hook `0x80052D98`
  draws all 8 Training slots from RAW-resident code at `x=0x48+i*0x18`; non-Training resumes the
  native 4-slot path, preserving the original `0x70,0x88,0xA0,0xB8` placements.
- **Game-over state:** master `0x800823a0` flips **`0x0` (gameplay) → `0x2` (game over)** when Flik dies with no lives left (the `0x2` write is DMA/non-CPU — invisible to watchpoints, B19).
- **Mod relevance:** the confirmed counters are directly pokeable/editable (e.g. set grain to 50, set the FLIK bitmask to 0xF) — same RAM the HUD mirrors. Health/lives editing is blocked until those two addresses are found.

## 4. Where it sits in the engine
- Front-end runs in the **shell phase** of the main loop `fcn.8004fa40` → substate dispatch `[0x8008243c]` (mod 6, table `0x8001b3c4`); gameplay (with the HUD) is a different substate than the menu/shell. High-level only → [[Finding - Level-warp mechanism]].
- In-gameplay overlay chain: `fcn.8004ecd4` → HUD [[FUNC_800526F4]] (see [[Systems]]).

## 4a. Front-end shell substate sequencer (decoded — static, EXE-read 2026-06-21, GAP-0036)
The shell phase (`[0x8008224e]!=0` → handler `0x8004f478`) runs a **6-entry substate machine**: `jr [0x8001b3c4 + substate*4]`, `substate = [0x8008243c]` (mod 6). The handlers are tiny and were read byte-exact statically (`tools/exe_read.py ./SCUS_942.88 --table 0x8001b3c4 --count 6` + `--disasm`):

| substate | handler | sets dest-index `[0x8008245c]` = | → `scene_table[idx]` (`@0x80077fa0`) |
|--:|---|--:|--:|
| 0 | `0x8004fc3c` | 1 | scene `0x01` (LEVEL01) |
| 1 | `0x8004fc50` | 11 | scene `0x0c` |
| 2 | `0x8004fc64` | 2 | scene `0x03` |
| 3 | `0x8004fc78` | 7 | scene `0x04` |
| 4 | `0x8004fc8c` | 12 | scene `0x0d` |
| 5 | `0x8004fca0` | — *(load case)* | `[0x8008243c]=0`; `jal `[[FUNC_8005222C]]`(a0=1)`; result → transition-state `[0x800823a0]`; `j 0x8004fb3c` |

Substates 0–4 share a tail (`0x8004fcc0`): `[0x8008243c] += 1` then `slti …,6` (advance, mod-6 wrap). So the front-end is a **linear scene-sequencer** that latches a destination index, then (substate 5) hands to the warp orchestrator [[FUNC_8005222C]]. This is the authored source of the GAP-0035B "shell-only" destination index — it confirms `[0x8008245c]` is written by shell code to **fixed constants, never by gameplay**. `scene_table[16] = 0xffffffff` (read here) is exactly the invalid sentinel the gameplay-side force-16 exit hits → crash (see [[Gameplay - Warp and Level Transition]] §GAP-0035B). The 4 substate-var writers (`0x8004fad4/fca4/fcd4/fce8`) drive which substate runs.

## 4b. Save system + menu-nav cursor — DECODED (static overlay disasm, 2026-06-22, GAP-0036)
The menu-nav + memory-card code is **not in the resident EXE** — it lives in the **`BITS/MEMORY.BIN` Region-B overlay** (runtime base `0x800B5788`; *that* is why prior EXE-only scans found "0 libcard evidence" in §5). Disassembled statically (`REBUILD/files/BITS/MEMORY.BIN` at base `0x800B5788`):

**Memory-card I/O (CONFIRMED-from-bytes).** Resident card thunks called from the overlay: **open `0x80065fdc`(name,mode)** · **read `0x80065fec`** · **write `0x80065ffc`** · **close `0x8006600c`**.
- **SAVE writer `0x800BAF30`** (top-level `0x800BAFCC`): `open(path, mode=2)` → `write(fd, header, 0x200)` → `write(fd, body, 0x380)` → close. Path from `bu%d0:%s%s` (`0x800B5B60`); device `bu%d0` → `bu00:`.
- **LOAD/scan `0x800BA668`**: build `bu%d0`, enumerate dir (`%s:*`), per entry `open(…,mode=1)` → `read 0x200` → `strncmp` vs save-name prefix **`BASCUS-94288`** (`0x800B57EC`) → close.
- Card strings (rt `0x800B5788`+off): `bu%d0`, `%s:%s`, `BASCUS-94288`, `BUGS  :` (title body), `bu%d0:%s%s` (write path), `LEV%.2d:%.2d` (per-level token).

**Save-block layout (CONFIRMED-from-bytes; builder `0x800BAD08`).** Standard PS1 8 KB directory frame: `+0x00='S' +0x01='C'` (the `SC` save magic), `+0x02` icon-display flag, `+0x03` block count, `+0x04..` Shift-JIS title, `+0x60` icon CLUT (16 halfwords), `+0x80` icon bitmap. Game payload written as `0x200` header + `0x380` body (`0x580` used). Save filename = `BASCUS-94288` + `BUGS`.

**Menu-NAVIGATION cursor (CONFIRMED-from-bytes; handler `0x800B687C`).** Reads the overlay's pad mirror words **`0x80082412`** (held) / **`0x800822E4`** (edge — the raw libpad buffer per [[Gameplay - Input and Movement]], read directly, not the decoded `0x80082488`): **Up** (`andi 0x10` @ `0x800B6888`) → if cursor>0 decrement + blip SFX (`jal 0x80050838`); **Down** (`andi 0x40` @ `0x800B68C8`) → `slti …,4` clamp then increment. Cursor = a per-page stack local (`0x28(sp)`); a second list cursor `s7` clamped by a table at `0x800BE340`. Post-load init `0x800BD518` zeros the menu globals + the save buffer (ptr `0x80082320`→`0x80082418`), then calls card-init `0x800BB19C`/`0x800BA374`.

⇒ **menu-nav + save format are documented** — GAP-0036 acceptance MET (statically). **Residual (local-only):** a live in-menu save write-watch confirming the `0x800BAF30` path end-to-end + the exact Shift-JIS title bytes + the body field map (which `0x800A65xx` progress counters land where in the `0x380` body).

## 5. NOT decoded (RE gaps)
- ~~Menu *navigation* layer~~ — **DECODED (2026-06-22, §4b):** cursor handler `0x800B687C` in the MEMORY.BIN overlay (Up `0x10`→dec, Down `0x40`→inc+clamp, blip SFX `0x80050838`); cursor = per-page stack local. (The overlay-residency hypothesis was correct — B17.)
- ~~Save / memory-card format + read/write code~~ — **DECODED (2026-06-22, §4b):** it was overlay-resident (MEMORY.BIN), not in the EXE — save writer `0x800BAF30`, load/scan `0x800BA668`, `SC`-magic 8 KB block (builder `0x800BAD08`), filename `BASCUS-94288`+`BUGS`. Residual = live save write-watch + the `0x380` body field map.
- **Menu rendering** — text is **image-baked** into `GFX/*.RAW` (no EXE strings → [[Blocker - Offline texture and font extraction is absent|B20]]); the vine/leaf menu graphics + layout logic are unmapped.
- **Health leaf** and **lives** RAM addresses (the two missing status icons).
- **SELECT status-panel render routine** (distinct from the in-game HUD draw).
- **Options effects** (vibration flag, volume globals, centre-screen offset) — not located.

→ Reachable now that input-drive + frame-capture work: a **menu-system RE pass** could start from the live **telescope "continue/exit" menu** (a concrete reachable menu instance) to crack the menu state/cursor/handler pattern, then generalize to pause/title. (Queued: in-game telescope-behavior verification.)

## Related
- [[MEM - Player state 800A6500]] · [[FUNC_800526F4]] (HUD draw) · [[Seed planting system]] · [[MEM - Type-0x3f placement record]] · [[Finding - Level-warp mechanism]] · [[Experiment - Pickup kind-swap]] · [[Systems]] · [[Blocker - Offline texture and font extraction is absent|B20 (image-baked text)]] · [[Blocker - Function boundaries and overlays evade the static call graph|B17 (overlays)]]
