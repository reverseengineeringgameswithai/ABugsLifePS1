---
kind: mod
id: MOD_grain_emblem_and_hud_total
name: Grain Emblem and HUD Total Mod
status: needs_review
confidence: medium
source_state: mod
canon_dependencies:
  - SYS_hud_counters
hooks: []
src_paths: []
evidence:
  - ObsidianVault/Archive/Superseded/Systems_Grain_emblem_and_HUD_total_mod.md
---

# MOD_grain_emblem_and_hud_total

Copy-first migrated from the former path
`ObsidianVault/Systems/Grain emblem and HUD total mod.md`, now preserved at
`ObsidianVault/Archive/Superseded/Systems_Grain_emblem_and_HUD_total_mod.md`.
The Archive citation is intentional provenance; keep mod edits separate from
original-game [[Grain_emblem_and_HUD_total_mod|HUD counter Canon]].

---

---
title: Grain emblem and HUD total mod
type: system
confidence: CONFIRMED
tags: [system, grain, hud, emblem, reward, mod, level01]
---
# Grain emblem and HUD total mod

> Collect every grain in a level → a **grain emblem** medal descends and **Flik's health refills to
> full**. This note documents that reward mechanic, the HUD "collected/total" readout, and the mod
> that makes both track the level's *real* grain total (so a 30-grain LEVEL01 awards the emblem at
> 30/30). All points live-CONFIRMED on the isolated DuckStation (2026-06-23).

## The mechanic (stock game)
Collecting the **final** grain triggers an all-grain reward: a large circular emblem/medal animates
in from the top of the screen and Flik's health bar refills to full (`0x800a7e2a` → 7). The trigger
is **collected count == level grain total**, and the stock game hard-codes that total as **50**.

### Where it is gated — NOT the HUD pulse
There are *two* independent `grain == 50` sites; only one is the reward:
- `0x80052ac0` `sltiu v0,v0,50` in HUD draw [[FUNC_800526F4]] — only the **SELECT-panel slide state**
  `[0x800b018c] = 1024` (auto-reveals the grain panel when complete). **Cosmetic, not the emblem.**
- **`0x80055008` `addiu v0,zero,50` ; `0x5500c bne v1,v0,0x80055174`** in the grain pickup handler
  [[FUNC_80054EAC]] — **THE reward gate.** `v1` = grain count (`lbu` from `0x800a65a1` @0x80055004).
  When `grain == 50` the `bne` falls through to the reward block at **`0x80055014`**.

### The reward block (`0x80055014`–`0x80055170`)
Straight-line (no internal branches) from `0x80055014` to the medal spawn:
- snapshots Flik's position (`0x800a6500/04/08`, `+0x6548`) into `0x80090b80..b8c` and sets the panel
  pulse `0x80090b90 = 1024` (this then ramps up → the medal/panel animation),
- **`0x80055060 jal 0x5044c`** with `a0 = -11` (`0xfffffff5`, the emblem/medal id), `a1 = 0x800a6500`
  → spawns the emblem medal,
- the health refill to full follows over the next ~165 frames (`0x800a7e2a` drains then snaps to 7).
- NB the `lives++` block (`0x80055080`+) is **dead code** — `0x80055078 bne` (comparing two distinct
  constants) is always taken and jumps past it to `0x80055110`. So the reward grants **no extra life**
  in the retail game; the visible effects are the **medal + health refill**.

## The HUD "collected/total" readout
The SELECT status panel draws the grain count via the engine glyph drawer
**`fcn 0x80025f54(x, y, tile=0x1e, value)`** (value 0–9 = digits, **`0x0a` = "/"** — the font sheet is
`"0123456789/"`, so the slash is a native glyph, *not* a custom asset). Layout, step `0xc`:
count `NN` at x=`0x33`/`0x3f` (drawn by the engine), then `/`=`0x4b`, total tens=`0x57`, ones=`0x63`.
Drawing the "/total" requires a code hook after the count (the total is not displayed by the stock
game). See [[FUNC_800526F4]].

## Grain total source (for the dynamic versions)
The level's grain total = number of **kind-0x14** entries in type-0x3f record 0 of the loaded
`LEVEL.DAT`: base ptr `G_DAT_BASE_PTR [0x80082498]`; `+4` u16 entry count; `+8` entries, stride
`0x10`; entry `+0xc` = kind byte. See [[MEM - Type-0x3f placement record]].

## The mod (dynamic — fires at the level's real total)
Goal: a LEVEL01 with only **30** grain where collecting all 30 awards the emblem and the HUD reads
`NN/30`. Three EXE edits + one DATA edit, all driven by the **live kind-0x14 count** (no hard-coded
number, so it tracks any level/count):

1. **DATA** — 20 of the 50 grains (entries 30–49) become inert **kind 0x16** (invisible,
   non-collectible: default skip handler `0x800545cc`, generic "other" render branch — proven safe,
   same basis as the net-new berry's unconfigured kind). Spec `mod/placements/grain30_level01.json`.
   > **2026-06-23 (CC5):** the inert-kind trick was a workaround for the *absent* delete op. With CC5 done
   > you can now **genuinely delete** grain records (`tools/delete_type3f_entries.py` / editor "Delete
   > Selected from Level"; relocation-aware, count decremented). Since this mod's `abl_grain_total()` counts
   > kind-0x14 **live**, real deletion auto-lowers the HUD total + emblem gate — no inert kind needed. The
   > inert approach still works and is fine if you want the grains *present-but-dead*; delete is for truly
   > removing them. (In-game verified: a delete-only disc booted LEVEL01 with 40 live grains.) See
   > [[LEVEL01 Level-Edit Punchlist#CC5]].
2. **HUD total** — hook `0x80052b40` → draw `/<total>` via `abl_grain_hud_total`.
3. **Emblem gate** — replace the `0x80055008` hard-coded `50` with `abl_all_grain_collected`
   (`grain == abl_grain_total()`), so the reward fires at the real total.
4. (cosmetic) HUD panel reveal threshold `0x80052ac0` lowered 50→30.

### Implementation
- **C logic** (the behaviour): `mod/caves/grain_emblem.c` — `abl_grain_total()` (count kind-0x14),
  `abl_grain_hud_total(y)` (draw "/total"), `abl_all_grain_collected()`. Freestanding R3000, linked
  by armips `.importobj`; letting the C compiler schedule loads removes the R3000 load-delay-slot
  hazard that bit the earlier hand-assembled version.
- **Hooks** (the trampolines + displaced-instruction replay): `mod/patch_grain30.asm`. Gotcha: the
  emblem-gate trampoline must `j` the skip target `0x80055174` (a `bne` from the cave is out of
  branch range) and replicate the original `bne` delay-slot `addiu a0,zero,-11` (it is an argument
  to the reward's `jal 0x5044c`).
- **Build**: copy `patch_grain30.asm` over `mod/patch.asm`, then
  `python3 mod/build.py --placements mod/placements/grain30_level01.json --out build/ABL_GRAIN30`.
  Disc `build/ABL_GRAIN30.bin/.cue`; test save `30_Grain_emblem.sav` (grain 29, gate active).

### Verification (live, isolated DuckStation)
- Control: 30/30 with the stock gate → reward block executes 0 times, no emblem (matches the bug).
- Treatment: gate → `abl_all_grain_collected` returns **1** at grain 30; breakpoints at `0x80055014`
  (reward) and `0x80055060` (medal `jal`, `a0=-11`) both hit; the **emblem medal renders** and
  **health refills to 7**; HUD reads `30/30`. Identical reward code path to the stock 50/50 trigger.
- Gotcha for re-testing via the old `30_Grain.sav`: that save's RAM already holds an earlier cave
  build, so a diff-vs-pristine poke leaves stale bytes — overwrite the **whole** cave region
  (`0x800810c0`+`0x240`) when injecting, or just cold-boot the rebuilt disc.

## Related
- Functions: [[FUNC_80054EAC]] (the gate) · [[FUNC_800526F4]] (HUD draw) · [[FUNC_80053814]]
- Memory: [[MEM - Type-0x3f placement record]] · [[MEM - Player state 800A6500]]
- System: [[Menu and HUD structure]] · [[LEVEL.DAT object pipeline]]
- Findings: [[Finding - Type-0x3f pickups are coordinate-moddable]]
- Mod sources: `mod/caves/grain_emblem.c`, `mod/patch_grain30.asm`, `mod/placements/grain30_level01.json`
