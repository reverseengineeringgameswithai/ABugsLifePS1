---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Replace a loading-screen backdrop.md
aliases:
  - "Playbook - Replace a loading-screen backdrop"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Replace a loading-screen backdrop.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Replace a loading-screen backdrop
type: playbook
status: proven end-to-end on LEVEL01 (ABL_NOCTURNAL_LOAD, cold-boot verified)
updated: 2026-07-02
tags: [playbook, loadingscreen, gfx, leveleditor, asset]
---

# Playbook — Replace a pre-level loading-screen backdrop

> Swap the level-name art shown while a level loads (the screen with the panning
> "loading…" → "Press X" prompt). Format reference: [[Finding - Loading screen backdrops are GFX RAW images]].
> Tool: `tools/loadscreen_edit.py`. This is a **pure data edit** — no C code.
> NOT the in-game horizon ([[Playbook - Author a custom backdrop]] is that, a different asset).

## What you're editing

A full-screen **320×256 16bpp (RGB555) image** = chunk 1 of `GFX/<NAME>.RAW` (LZ-chunk
container, same codec as LEVEL.RAW). Pick the file from the campaign map in the Finding —
**LEVEL01 = `GFX/LEVEL1A.RAW`**. The "loading…"/"Press X" prompt is a SEPARATE overlay
(`GFX/LOADING.RAW`) drawn on top; you never touch it.

## Rules (each matters)

1. **Two display quirks to design around** (both live-measured):
   - Only ~240 of the 256 rows show → keep nothing important in the **bottom ~16 px**.
   - The overlay pans to a fixed **bottom band (~rows 205+)** → keep your lowest text
     (subtitle) **at row ≤ ~190**, or it gets covered. Use `--shift-up` to lift art that
     was composed to fill the whole frame (LEVEL1x safe value ≈ **16**).
2. **Stay within the sector budget** to keep the pinned layout (LEVEL1A = 48 sectors =
   98304 B). Pass `--sector-budget 48`; the tool warns on overflow. By-name loading tolerates
   growth ([[Finding - File loading is by-name (LBA-shift tolerant)]]) but ≤budget = zero LBA shift.
3. **Never touch chunk 0** (shared font/CLUT resource, identical across LEVEL1A/1B/1C).
4. The tool runs the **full-file decode regression** (all chunks byte-identical except the
   edited one) before writing — do not bypass it.
5. **Verify on a cold boot**, not a save state (states snapshot old RAM/asset).

## Step-by-step

```bash
# 1. See the current screen (any GFX name)
python3 tools/loadscreen_edit.py extract LEVEL1A -o loadscreen_LEVEL1A.png

# 2. Replace it. --shift-up 16 lifts full-frame art so the subtitle clears the overlay band.
python3 tools/loadscreen_edit.py replace LEVEL1A \
        --image mod/loadscreens/src/Nocturnal_Ant_Island.png \
        --shift-up 16 --sector-budget 48 -o /tmp/LEVEL1A_new.RAW

# 3. Build a disc: stage the patched RAW into REBUILD/files/GFX/, mkpsxiso, restore the tree.
DST=REBUILD/files/GFX/LEVEL1A.RAW
cp "$DST" "$DST.bak"; cp /tmp/LEVEL1A_new.RAW "$DST"
mkpsxiso -y -o REBUILD/ABL_NOCTURNAL_LOAD.bin -c REBUILD/ABL_NOCTURNAL_LOAD.cue REBUILD/abl.xml
cp "$DST.bak" "$DST" && rm "$DST.bak"

# 4. Cold-boot verify (isolated DuckStation): boot the .cue, play flik_to_level01_stall.mv.movie.json,
#    advance to ~frame 3660-3700, captureFrame — the loading screen is there.
```

## Authoring the source image

- Any aspect is fine; the tool resizes to 320×256 (the frame is displayed anamorphically
  stretched to 4:3, so a ~4:3 source looks right). Nothing is cropped by the resize itself.
- Bake your own level-name text into the art if you want it (the retail screens do). Keep the
  lowest line high enough to clear the overlay (rule 1) — `--shift-up` is the escape hatch if
  it's already baked too low.

## Provenance

Built in the ABL_NOCTURNAL_LOAD session (2026-07-02): decoded the GFX format, replaced
LEVEL01's screen with a night render, diagnosed + fixed the subtitle/overlay collision with a
+16 shift, cold-boot verified. Assets in `mod/loadscreens/` (src art, ref extracts + in-game proof).
