---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - media control.md
aliases:
  - "API - media control"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - media control.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - media control
type: api
category: CD-DMA
tags: [api, duckstation, cdrom, disc, media, swap]
---
# API — emulator.* (disc / media control + cold boot)

> **Cold-boot** a system from a disc image when nothing is loaded (the menu/idle state), and once running **eject / insert a different disc image** — the equivalent of launching a game and then changing discs — **without restarting the emulator.** Lets an agent drive the whole loop headless: boot pristine once, then swap between rebuilt BIN/CUEs (e.g. the [[Experiment - FLIK letters disc mod demo|save-state-repoint]] variants) programmatically.

> [!success] Status (2026-06-18): implemented, build-clean (`ninja duckstation-qt`, exit 0), live-validated on the isolated instance (port 23460). Disc-swap 12/12; cold-boot 10/10 (menu boot, `start_paused` → `pc:0xbfc00000`, resume+advance runs, already-loaded `-32005`). **`force` switch validated:** cold-boot pristine paused → `force` cold-boot to modded **succeeds (no crash)**; `force` while RUNNING → `-32002` and the instance survives; pause → `force` boot works. **Not yet committed.**
> [!bug] Crash found & fixed during validation: a `force` cold-boot of a **running** system aborted on `Assert(state==Shutdown)` — `System::ShutdownSystem` only destroys synchronously when not mid-execute, and `RunOnCore` runs nested in the frame loop while running, so the teardown deferred and `BootSystem` asserted. Fix: `force` now requires the system **paused** (`-32002` otherwise).

## Methods & syntax
- **`emulator.bootSystem {path, fast_boot?, start_paused?, force?}`** → `MediaInfo` + `{booted:true, paused, pc}` — **COLD boot** a brand-new system from `path` (`System::BootSystem`) when **nothing** is loaded (`debugger.status` shows `valid:false`/`cycle:0`). `fast_boot` skips the BIOS intro; `start_paused` boots paused so breakpoints arm before the first instruction. If a system is already loaded it fails `-32005` **unless `force:true`**, which shuts the running system down and cold-boots the new image (a FULL reset, vs `loadMedia`'s warm swap). **`force` requires the system PAUSED** (`-32002` while running — the teardown can't run inside the live frame loop). This is the missing piece that unblocks fully-headless drive (no GUI boot needed).
- **`emulator.getMediaInfo {}`** → `MediaInfo` — report the currently mounted disc. Side-effect-free (`cd_overlays_removed` always `0`); pause first for a coherent read while running.
- **`emulator.closeMedia {}`** → `MediaInfo` with `has_media:false` — eject the disc (`System::RemoveMedia`). Idempotent: closing with nothing mounted is a no-op that still returns the empty `MediaInfo`. Keeps the system *running* (lid open) — does NOT shut it down.
- **`emulator.loadMedia {path}`** → `MediaInfo` for the new disc — open the **absolute** `path` and insert it (`System::InsertMedia`), replacing any mounted disc. Accepts any image DuckStation opens (`.cue`/`.bin`/`.chd`/`.iso`/`.exe`/`.m3u`/…).
- `loadMedia`/`closeMedia`/`getMediaInfo` need a **running** system (`-32001`); `bootSystem` needs **no** system.
- `MediaInfo` = `{has_media, path, game_serial, game_title, subimage_index, subimage_count, cd_overlays_removed}`.
- Client verbs: `boot-system --path … [--fast-boot] [--start-paused]`, `media-info`, `close-media`, `load-media --path /abs/disc.cue`. MCP tools: `boot_system(path, fast_boot, start_paused)`, `get_media_info()`, `close_media()`, `load_media(path)`.

## Mechanics
- **No CPU/RAM reset.** The disc is swapped *under* the running game exactly like the GUI "Change Disc" — execute/read/write breakpoints and injected controller input survive. A game that expects a reboot after a disc change wants `debugger.reset` afterward.
- **Drops CD overlays.** [[API - CD overlay|cd.* overlays]] are keyed to the mounted disc's LBAs/files, so both `closeMedia` and `loadMedia` clear **all** installed overlays (a stale overlay would otherwise substitute the wrong bytes into the new disc). Count reported as `cd_overlays_removed`.
- All three require a loaded system (`-32001`). `loadMedia` validates the path: **relative → `-32006`**, **missing/unopenable → `-32005`**; on failure the previously mounted disc is kept (but its overlays are still gone).
- `game_serial`/`game_title` come from the game DB by serial, so swapping between modified copies of the **same** game (e.g. the ABL `_TEST.cue` variants) reports the same serial/title — only `path` changes.

## Best use in ABL RE
Fully-headless drive loop, no GUI boot needed: **`bootSystem`** (pristine disc, `start_paused` to arm breakpoints first) → diagnose / `debugger.reset` → **`loadMedia`** a rebuilt POC BIN/CUE → `advanceFrames` → observe → repeat. Complements [[API - CD overlay]] (no-rebuild byte substitution, but per-sector) and the [[Experiment - FLIK letters disc mod demo|save-state-repoint]] method (which edits a state's embedded disc path); `loadMedia` is the clean front-door equivalent that doesn't touch a save state. Pairs with [[API - experiment runner]] / [[API - visual diff]] to confirm the swapped disc's effect.

## Common mistakes / gotchas
> [!warning] Swap ≠ reboot. `loadMedia` does **not** reset the CPU — the old game keeps running with the new disc inserted. For "boot this other disc from scratch" do `loadMedia` **then** `debugger.reset`.
> [!warning] Install CD overlays **after** the swap, not before — `loadMedia`/`closeMedia` wipe them. (Conversely, this is the clean way to drop disc-stale overlays.)
- `loadMedia`/`bootSystem` paths must be **absolute**; a relative path is rejected (`-32006`) rather than resolved against any working dir.
> [!tip] **Switching pristine → modded with a full reset:** pause, then `bootSystem(modded, force=True)`. You do **not** need `closeMedia` first — `closeMedia` only opens the lid (system keeps running), so a plain `bootSystem` after it still returns `-32005`. `force` tears the running system down for you. `force` requires PAUSED (`-32002` while running). For a warm swap with no reset, use `loadMedia` instead.

## ABL examples
```
# Cold boot from the menu (nothing loaded) — the new piece:
boot-system --path "~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue" --fast-boot --start-paused
                                                                  # -> booted:true, paused:true, pc:0xbfc00000
resume ; advance-frames --frames 60                               # system genuinely executes (frame -> 60+)

# Switch to a modded image WITH a full reset (the pristine→modded use case):
pause                                                             # force requires a paused system
boot-system --path "~/Downloads/ABL/ABL_FLIK_TEST.cue" --force --fast-boot --start-paused

# ...or iterate with a WARM disc swap (no reset):
load-media --path "~/Downloads/ABL/ABL_FLIK_TEST.cue"   # swap under the running game (cd_overlays_removed:N)
close-media                                                       # eject (has_media:false; system stays running)
```

## Related
[[API - CD overlay]] · [[API - loadState]] · [[API - experiment runner]] · [[API - execution control]] · [[Experiment - FLIK letters disc mod demo]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md), client ~/duckstation/scripts/debugger-client/
