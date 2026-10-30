---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - exec range and access history.md
aliases:
  - "API - exec range and access history"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - exec range and access history.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - exec range and access history
type: api-note
updated: 2026-07-06
tags: [duckstation, api, tracing, collision]
---

# API - exec range and access history

Collision-debug accelerators for ABL Track-B research. These are not prerequisites for Track-B; the current blocker is
ABL collision behavior/authoring evidence, not missing emulator fundamentals.

## `execTrace.addRangeWatch`

Function/range execution trace without manually planting exact-PC watches:

```json
{"method":"execTrace.addRangeWatch","params":{
  "start":"0x80035280",
  "end":"0x8003633c",
  "capture":["pc","ra","a0","a1","a2","a3","s0","s1","gte.SXY0"],
  "max_events":20000,
  "stop_on_hit":false
}}
```

Returns a normal `execTrace` watch with `kind:"range"`, `start`, `end`, `capture`, `hit_count`, and `watch_id`.
Events are read with `execTrace.get` / `execTrace.run` and have the existing shape:
`{frame, cycle, pc, watch_id, regs:{...}, gte:{...}}`. Run `execTrace.analyze {watch_id?, top?}` after capture for call/return edges, unreturned calls, backward branches, and self-loop hints.

Notes:
- Inclusive range. Keep it bounded; it forces the interpreter while armed.
- Capture names use the existing `execTrace` rules: plain GPR/PC/COP0 names or `gte.*`. Include `ra` for return matching; include likely indirect target registers (`t9`, `v0`, etc.) for `jalr` targets.
- Cleared by `loadState`, game unload, and server stop. Re-arm after loading.

ABL use:
- `FUNC_80035280` / `FUNC_8003633C`: capture `pc,ra,a0..a3,s0..s3` to identify call cadence, candidate pointers, and
  return paths during collision resolution.

## `accessTrace.start`

PC-scoped effective-address trace. It logs CPU memory reads/writes while the current instruction PC is inside a
function/range, without knowing candidate/plane/sector RAM ranges up front:

```json
{"method":"accessTrace.start","params":{
  "start":"0x80035280",
  "end":"0x8003633c",
  "type":"readwrite",
  "capture":["pc","ra","a0","a1","s0","s1"],
  "max_events":50000
}}
```

Run the game or `advanceFrames`, then query:

```json
{"method":"accessTrace.get","params":{
  "offset":0,
  "limit":1000,
  "filter":{"type":"read","address":{"min":"0x80000000","max":"0x801fffff"}}
}}
```

Event shape:

```json
{
  "frame": 1234,
  "cycle": 567890,
  "pc": "0x80035610",
  "pc_after": "0x80035614",
  "address": "0x80123456",
  "type": "read",
  "width": 4,
  "value_hex": "0x00000020",
  "regs": {"pc":"0x80035610","a0":"0x800a6500"},
  "gte": {}
}
```

Write events include `new_value_hex` only when the store is cleanly decoded (`sb`/`sh`/`sw`). `pc` is the actual current
instruction PC; `pc_after` is provided to compare with older access-log attribution gotchas.

## `accessHistory.start`

Global recent CPU memory-access ring:

```json
{"method":"accessHistory.start","params":{"max_events":50000,"type":"write","capture":["pc","ra"]}}
```

Use this before level-load/collision-build windows when the exact address is not known yet, then query after the fact:

```json
{"method":"accessHistory.get","params":{
  "filter":{"address":{"min":"0x80100000","max":"0x801fffff"},"frame":{"min":100,"max":500}},
  "limit":10000
}}
```

Limits/gotchas:
- Single global buffer; starting again replaces the previous history config and clears events.
- Drop-oldest ring, `max_events<=200000`, `get.limit<=10000`.
- CPU loads/stores only. Use `transferLog` for DMA/CD-ROM provenance.
- Forces interpreter while enabled. Stop/clear promptly.
- Cleared by load/unload; re-arm after `loadState`.

## Helper path for markers

Native in-emulator marker primitives are still a future gap. Current supported path:
- capture camera approximation with `gpu.getCameraTransform`;
- capture frame/VRAM with `gpu.captureFrameSnapshot` / `gpu.frameSnapshot`;
- project/annotate externally in Python for Flik position, candidate planes, sector AABBs, Blender spawn/goal markers,
  and authored route overlays.

## Track-B validation recipe

Cold boot a G3-native disc/movie, then arm trace at the collision resolver:

```bash
DUCK=~/duckstation
ABL=~/Downloads/ABL
PORT=23580
CFG=/tmp/duckstation-debugger-abl-range

$DUCK/scripts/debugger-client/launch_debugger_instance.sh start \
  --config-dir "$CFG" --port "$PORT" --token abl-range \
  --disc "$ABL/build/ABL_native_m3.cue"

python3 $DUCK/scripts/debugger-client/duckstation_debug_client.py --port "$PORT" --token abl-range \
  movie-load --path "$ABL/g3native_movie.movie.json"
python3 $DUCK/scripts/debugger-client/duckstation_debug_client.py --port "$PORT" --token abl-range \
  movie-start-playback --load-start-state
python3 $DUCK/scripts/debugger-client/duckstation_debug_client.py --port "$PORT" --token abl-range \
  movie-advance-to-frame --target-frame 4500

python3 $DUCK/scripts/debugger-client/duckstation_debug_client.py --port "$PORT" --token abl-range \
  exec-range-watch-add --start 0x80035280 --end 0x8003633c \
  --capture pc,ra,a0,a1,a2,a3,s0,s1 --max-events 20000
python3 $DUCK/scripts/debugger-client/duckstation_debug_client.py --port "$PORT" --token abl-range \
  access-trace-start --start 0x80035280 --end 0x8003633c \
  --type read --capture pc,ra,a0,a1,s0,s1 --max-events 50000
python3 $DUCK/scripts/debugger-client/duckstation_debug_client.py --port "$PORT" --token abl-range \
  advance-frames --frames 60
python3 $DUCK/scripts/debugger-client/duckstation_debug_client.py --port "$PORT" --token abl-range \
  exec-trace-get --limit 1000
python3 $DUCK/scripts/debugger-client/duckstation_debug_client.py --port "$PORT" --token abl-range \
  access-trace-get --limit 1000 --filter '{"type":"read"}'
```

The expected value is a compact list of resolver PCs and effective addresses read during those frames, replacing the
old workflow of guessing/planting many exact PC and RAM watches.
