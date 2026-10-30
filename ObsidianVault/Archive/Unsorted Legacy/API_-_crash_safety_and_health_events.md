---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - crash safety and health events.md
aliases:
  - "API - crash safety and health events"
migration_action: needs_review
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - crash safety and health events.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - crash safety and health events
type: api
category: Connection
tags: [api, duckstation, crash, timeout, events, health, ops]
---
# API — crash safety and health events

> RPC calls now **time out** instead of hanging when the guest halts/crashes/loops, and the server **pushes** guestHalted / guestReset events so a client learns the core died without polling.

## Methods & syntax
- **Core-call timeout:** every request that marshals to the emulation core is bounded at **5000 ms** (`CORE_CALL_TIMEOUT_MS`). If the core doesn't respond, the handler is abandoned safely (no hang) and the call returns a **structured error**:
  - `error.code = -32005`, `error.data = {reason:"core_unresponsive", method, timeoutMs:5000}`.
- **Pushed event `guestHalted`** `{reason, pc, diagnostics:{pc, sp, frame, cycle, lastInstruction, gameSerial, gameTitle, disc}, status}` — emitted from the core thread when a crash/halt is detected. `diagnostics` is the rich payload (`pc`/`sp` hex, current `frame`/`cycle`, the disassembled `lastInstruction`, plus game serial/title/disc); fields under `valid:false` are null.
- **Pushed event `guestReset`** `{reason, status}` — emitted on a console reset.
- Both carry the standard `status` object (same as other events); they only fire while the debugger server is running.

## Best use in ABL RE
This directly retires the **"socket blocks forever on a guest crash"** footgun from the [[DuckStation API Index]]. Two wins:
1. A heavy teleport / wrong-disc poke that crashes the guest now returns `-32005 core_unresponsive` on the offending call instead of dangling — you get the failing `method` back immediately.
2. Subscribe to events and watch for `guestHalted` to know *which PC + last instruction* the core died on (great for catching one-shot crashes from far-object teleports — see the warpAndSettle workflow in [[API - experiment runner]]).

## Common mistakes / gotchas
- The timeout error's `diagnostics` are best-effort; the **richer** PC/cause/last-instruction info rides on the pushed `guestHalted` event (sent from the core thread), so subscribe to events, don't rely on the error alone.
- A client `recv` timeout is still worth setting (`c.transport.sock.settimeout(...)`) — the 5000 ms guard is server-side; a dead socket/connection-reset is a separate failure surfaced on the *next* call.
- `-32005` is the generic "operation failed" code; disambiguate by `error.data.reason == "core_unresponsive"`.

## Related
[[API - crash diagnostics and logging]] · [[API - connection and auth]] · [[API - loadState]] · [[API - media control]] · [[API - experiment runner]] · [[DuckStation API Index]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
