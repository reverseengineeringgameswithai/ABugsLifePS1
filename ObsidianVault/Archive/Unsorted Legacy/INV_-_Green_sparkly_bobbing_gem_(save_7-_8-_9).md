---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Investigations/INV - Green sparkly bobbing gem (save _7-_8-_9).md
aliases:
  - "INV - Green sparkly bobbing gem (save _7-_8-_9)"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Investigations/INV - Green sparkly bobbing gem (save _7-_8-_9).md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: INV - Green sparkly bobbing gem (saves _7/_8/_9)
type: investigation
status: RESOLVED - gems = type-0x3f entries 67/68/69 (kind 0x30); move via DAT edit + rebuild
confidence: HIGH (positions matched all 3 saves; mechanism proven for other type-0x3f kinds)
tags: [investigation, pickup, gem, sparkle, type3f, kind30, solved]
---

# Investigation — Green sparkly bobbing gem

> Goal (from operator): from saves `_7/_8/_9`, MOVE the green floating sparkly gem (side/up/down),
> each of the 3 independently. **RESOLVED.**

## ✅ ANSWER (read this first)
The 3 green floating gems are **type-0x3f placement entries 67, 68, 69 — kind `0x30`** in
`LEVEL01\LEVEL.DAT` (the catalog mislabels kind 0x30 as "checkpoint/trigger"; it is actually the
**telescope** — the hint device that reveals an item/exit; the green sparkly "gem" is its visual.
Operator-confirmed 2026-06-18, [[Experiment - Pickup kind-swap]]). They are 3 independent records, so editing one moves only that gem.

| Gem (save) | entry | file off | pristine file XYZ | runtime (×32) |
|---|---|---|---|---|
| `_7` | 67 | 0x438 | (−628, −50, 14209) | (−20096, −1600, 454688) |
| `_8` | 69 | 0x458 | (−3181, −50, 3647) | (−101792, −1600, 116704) |
| `_9` | 68 | 0x448 | (4674, −50, 20832) | (149568, −1600, 666624) |
(matched to each save's player position to within a few thousand units on X and Z.)

**Move method (the proven type-0x3f coordinate mod — NOT a runtime RAM poke):**
`tools/patch_level_entry.py LEVEL01_LEVEL.DAT --entries 67 --dx N --dy N --dz N --in-place`
(file-unit deltas; runtime = delta<<5; −Y = up), then
`tools/rebuild_with_patched_dat.py --patched-dat … --out-bin … --out-cue … --write`. Each entry is
independent → move 67/68/69 by different amounts to move the 3 gems independently.

**Proof disc built:** `ABL_GEMS_MOVE_TEST.bin/.cue` — entry 67 +80000 X (side), entry 68 −80000 Y
(up), entry 69 +80000 Z (forward). Embedded DAT verified at LBA 2906 (sha1 a6769f84…).

**Two working methods (both confirmed):**
1. **Live RAM edit** — the gem reads its position live from its runtime type-0x3f record (entry 67 at
   RAM `0x80160c30`; loaded array base = `0x80160800`, 0x10 stride). **X (`+0`) and Z (`+8`) are
   static, live-read, and an edit persists across save/reload** (no per-frame writer). **Y (`+4`) is
   regenerated every frame by the bob writer `0x80053a8c`: `Y = base[entry+0xe] + sine − 800`** — so
   for up/down edit the **bob base halfword at entry+0xe**, not Y. Demonstrated: moved the `_7` gem
   −38400 on X and saved it as `SCUS-94288_8.sav` (`_8` = `_7` with gem moved; persists on reload).
2. **DAT edit + rebuild** — for a persistent on-disc layout hack (proof disc `ABL_GEMS_MOVE_TEST`).

> ⚠️ Earlier-session error (now corrected): a single X edit of +48000 "did nothing" only because it
> pushed the gem *behind the tree*; the record IS the live render source.

---

## Original investigation log (how we got here)

## Save states (backed up per operator request)
| Original | Backup copy |
|---|---|
| `SCUS-94288_7.sav` | `SCUS-94288_greenitem_lvl7.sav` |
| `SCUS-94288_8.sav` | `SCUS-94288_greenitem_lvl8.sav` |
| `SCUS-94288_9.sav` | `SCUS-94288_greenitem_lvl9.sav` |
(in `~/.local/share/duckstation/savestates/`)

## The item (CONFIRMED visually)
- Save `_7` is **LEVEL01** (the 3 sprite-pool slots hold LEVEL01's exact type-0x77 spawn coords).
- The item is a **cyan/green glowing gem with white cross-shaped sparkle stars**, sitting on the
  left ledge near Flik (the tree-trunk / grass-blade area). Reference: `gem_lvl7_reference.png`.
- **It really bobs vertically**: green/cyan centroid screen-Y oscillates ≈ 192↔243 px (1272×970
  capture), period ≈ **44 emulated frames** (~0.73 s). Native screen pos ≈ (246, 98) in 512×224.
- Live world position (read off a *follower* near the player): ≈ **(−20500, −82000, 455300)**,
  i.e. the contact cluster right next to the player (player ≈ (−18363, −49612, 469631)).

## What was RULED OUT (each tested live)
1. **Contact/pickup array `0x800B0D18`** (64×0x38). Several slots' XYZ correlate 0.92–0.97 with the
   on-screen bob (e.g. slot 25 `0x800b1290`, slot 28 `0x800b133c`), BUT:
   - Moving/freezing any slot's X/Y/Z produces **no gem movement** (frame-matched diffs ≈ 0).
   - No CPU reads/writes hit them over 12 frames ⇒ they are **DMA-updated followers** (CPU
     watchpoints can't see DMA). They track the gem; they do not drive its render.
   - Slots 22–25 are physics-integrated **sparkle particles** (`pos += vel`, integrator PC
     `0x8005a534`), not the gem core.
2. **Sprite-object pool `0x8009c870`** (8×0x344; render pos slot+0x34/38/3c; home slot+0x24/28/2c).
   Only slots 0/1/2 active = LEVEL01's three **type-0x77** objects. Their render Y (−80711…) and Z
   (492233…) *match the gem's range*, but their X is far (245049 / −154398 / −195102) ⇒ **off-screen**,
   NOT the visible gem. Writing render X/Z or home, even placing a slot in front of the player and
   freeze-forcing it, drew **nothing** (diff 0). This renderer (`fcn.8003f938`) does not draw the
   visible gem in this state.
3. **Type-0x3f runtime array** `[0x80096E9C]` → `0x801607fc`: entries here did **not** decode as the
   documented `+0=X +4=Y +8=Z +0xc=kind` placement records (kinds/coords were garbage) — in this
   state it is a different/processed structure. Not resolved.
4. **Scratchpad** `0x1F800000` (camera/view struct @ `0x1f800374`): no column correlates with the
   bob (|corr| ≤ 0.12). (Note: memoryScan + accessLog cover **main RAM only** — scratchpad must be
   read manually, which was done here.)
5. **Memory-scan isolation**: periodic (half-period bottom→top→bottom) and monotonic scans, plus
   full-RAM screen-bob correlation and `[const,osc,const]` XYZ-triple search — all surfaced only
   **audio buffers, the camera struct (`0x800a07d0`, +0x34/38/3c, references player Y), and a
   64-entry frame-history ring buffer (`0x800a65d8`, stride 0x60, writer `0x80064908`)** — never a
   writable gem position.

## Conclusion (current)
The visible gem has **no stable, freezable plain-s32 world position in main RAM** that drives its
render. Strong implication: it is **overlay-spawned and GTE-projected per frame** from a source not
yet isolated (or rendered via a non-obvious representation). The contact followers prove where it
*is* but not how to *move* it.

## Recommended next experiment (untried)
- **GTE-input render hook** (the technique behind `tools/abl_starry.py` / `abl_night_hook.py`):
  execTrace the GTE RTPS/RTPT projection site(s), capture per-vertex GTE input + output `SXY2`, find
  the primitive whose output ≈ screen (246, 98) and whose output **oscillates** with the bob → its
  GTE input = the gem's (camera-relative) coords → back-trace the source register/struct, then either
  patch that source or install a per-frame hook that adds an offset to the gem's projected/world
  vector. This directly ties render→data and sidesteps the follower/DMA confusion.
- Alternative: if the gem turns out to be a **type-0x77 / 0x32 / 0x33** overlay sprite-object, the
  documented **overlay-immediate patch** (LEVEL.BIN `lui/ori`, see
  `docs/EXECUTABLE_AND_OVERLAYS.md` §"FIRST SAFE COORDINATE-MOD RECIPE") moves it — but only via a
  level (re)load, not a mid-level save state.

## Gotchas hit this session
- Capture native mapping: capture is **1272×970** → native **512×224** (not 954×970). Earlier screen
  math was off until corrected.
- `memoryScan.start` rejects a **negative** `value`; pass the **unsigned** 32-bit form (`v & 0xffffffff`).
- Frame-matched diffing is essential: compare two states at the **same** advance count, else Flik's
  idle animation (and the gem bob) swamps the diff.
- Aggressive load/write cycles appear to have **crashed the DuckStation debugger server** (port 2346
  refused) — needs a restart to resume.

## Related
[[MEM - Contact array 800B0D18]] · [[Finding - Type-0x3f pickups are coordinate-moddable]] ·
[[MEM - Type-0x3f placement record]] · [[Finding - GPU primitive injection]] · `docs/EXECUTABLE_AND_OVERLAYS.md`
