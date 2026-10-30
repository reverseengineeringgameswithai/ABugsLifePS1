---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - trace.armWhen.md
aliases:
  - "API - trace.armWhen"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - trace.armWhen.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - trace.armWhen
type: api
category: Tracing
tags: [api, duckstation, trace, condition, provenance]
updated: 2026-07-06
---
# API — trace.armWhen

> Wait for an `advanceUntil`-style condition, then clear/start selected trace/log systems at that moment.

## Method & syntax
**`trace.armWhen {condition, max_frames, observe?, actions, disarm_condition?}`** → `{armed, wait, actions, notes}`.

`condition`, `max_frames`, and `observe` are the same as [[API - advanceUntil]]. `actions` is required and can include:
- `gp0Trace:{start?:true, clear?:true, max_entries?, max_params?}`
- `transferLog:{start?:true, clear?:true}`
- `accessLog:{clear?:true, addWatch?, watches?}`
- `execTrace:{clear?:true, addWatch?, addRangeWatch?, watches?}`
- `vramWriteLog:{clear?:true}`

If the condition is not reached before `max_frames`, `armed:false` and no action runs. If `disarm_condition` is present, the call waits again after arming, using `disarm_max_frames` or `max_frames`, then applies `disarm_actions`. When `disarm_actions` is omitted it conservatively stops `gp0Trace` and `transferLog` if this call started them, leaving retained access/exec/VRAM logs intact.

## Best use in ABL RE
Use when a trace must begin at a milestone instead of at save-state load: PC reaches a loader/draw routine, a movie playback frame arrives, or a memory flag changes. For access/exec capture, put `addWatch` / `addRangeWatch` in the action so the watch is installed after the trigger; `clear:true` drops pre-trigger noise and removes older watches.

```json
{"condition":{"kind":"pc","address":"0x800224ec"},
 "max_frames":600,
 "actions":{
   "gp0Trace":{"start":true,"clear":true},
   "transferLog":{"start":true,"clear":true},
   "execTrace":{"clear":true,"addRangeWatch":{"start":"0x800224ec","end":"0x80022608","capture":["pc","ra"]}},
   "vramWriteLog":{"clear":true}
 },
 "disarm_condition":{"kind":"frame","value":12345},
 "disarm_max_frames":120}
```

## Gotchas
- Synchronous: it advances one frame at a time just like `advanceUntil`; long waits take real time.
- `accessLog.clear` / `execTrace.clear` remove existing watches and events, matching those APIs' clear semantics. Use nested `addWatch` / `addRangeWatch` to install post-trigger watches in the same call.
- `disarm_actions` can request `gp0Trace.stop/clear`, `transferLog.stop/clear`, `accessLog.clear`, `execTrace.clear`, and `vramWriteLog.clear`.

## Related
[[API - advanceUntil]] · [[API - gp0Trace]] · [[API - transferLog]] · [[API - accessLog]] · [[API - execTrace]] · [[API - provenance.timeline]]

Source: ~/duckstation/docs/external-debugger.md
