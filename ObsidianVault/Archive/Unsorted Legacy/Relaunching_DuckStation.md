---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation/Relaunching DuckStation.md
aliases:
  - "Relaunching DuckStation"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation/Relaunching DuckStation.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Relaunching DuckStation
type: playbook
tags: [duckstation, ops, runbook, recovery]
updated: 2026-06-18
---

# Relaunching DuckStation (crash recovery)

> How to restart DuckStation with A Bug's Life when it crashes mid-session (e.g. during heavy live
> editing). The external-debugger server (port **2346**) is enabled in DuckStation's config, so it
> **auto-starts** on launch — no extra flags needed.

## Paths
- **Binary (logging wrapper):** `~/duckstation/build-release/bin/duckstation-qt-logged`
  (or the raw GUI binary `…/duckstation-qt`). The wrapper tees the console log to
  `~/.local/share/duckstation/duckstation-console.log`.
- **Game:** `~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue`
- **Debugger port:** `2346` (game instance). Comes up ~1 s after launch.

## Launch command (what was used, G33b)
It's a Qt GUI app, so it needs `DISPLAY`. Detect it from the X socket, then launch detached:
```bash
DISP=$(ls /tmp/.X11-unix/ 2>/dev/null | head -1 | sed 's/X/:/')   # e.g. ":0"
DISPLAY=${DISP:-:0} nohup \
  ~/duckstation/build-release/bin/duckstation-qt-logged \
  "~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue" \
  >/tmp/ds_relaunch.log 2>&1 &
```
> The mononymous user-run form: type `! <command>` in the prompt to run it in-session if an agent can't reach the display.

## Verify it's up
```bash
# port listening?
for i in $(seq 1 20); do ss -ltn 2>/dev/null | grep -q 2346 && { echo "port up (${i}s)"; break; }; sleep 2; done
pgrep -af duckstation-qt | grep -v grep        # process running?
```

## Reconnect + restore state
A fresh launch boots to the BIOS/title — the game is NOT at a save state yet. Reconnect and `loadState`:
```bash
cd ~/Downloads/ABL/tools
python3 -c "
import os; from abl_dbg import D
d=D(); print(d.status())                       # confirm debugger responds
sav=os.path.expanduser('~/.local/share/duckstation/savestates/SCUS-94288_terrain_collision_floor.sav')
d.load(sav); d.adv(3); print('Flik Y', d.rs32(0x800a6504))
"
```

## Notes / gotchas (from live work)
- **What crashes the link** (recoverable without full restart): `emulator.pressButton`, a single **large**
  `debugger.writeMemory`, and **large `scatterWrite` batches** (chunk to ≤24 items). Prefer
  `emulator.setControllerState`+`advanceFrames` for input.
- If the link drops but the process is alive: `d.call("debugger.resume",{})` un-pauses; then `loadState` to
  restore a clean state. Check `ss -ltn | grep 2346` — if the port is gone, the process died → relaunch above.
- After `loadState`, `execTrace` watches are dropped (re-arm) and the terrain renderer needs a few settle
  frames before it fires (`run(1)` right after load can return 0 hits).

## Related
[[DuckStation API Index]] · [[API wishlist - analysis fast-tracking]] ·
[[Plan - Terrain+collision matched bump (Option B)]]
