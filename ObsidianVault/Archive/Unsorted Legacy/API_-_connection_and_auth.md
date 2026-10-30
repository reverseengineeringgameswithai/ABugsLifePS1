---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - connection and auth.md
aliases:
  - "API - connection and auth"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - connection and auth.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - connection and auth
type: api
category: Connection
tags: [api, duckstation, connection, auth]
---
# API — connection and auth

> How a client connects to the DuckStation external debugger and authenticates before any other call.

## Methods & syntax
- **Transport:** a single TCP port auto-detects the client from its first bytes:
  - **WebSocket (RFC 6455)** — preferred; the **only** transport that carries asynchronous events (`paused`, `breakpointHit`, `memoryChanged`, …). Frames must be masked, RSV=0; caps 16 MiB/frame, 32 MiB reassembled.
  - **Raw TCP** — newline-delimited JSON (`\n` per message). Fine for simple scripts (`nc`); no events; small inbound buffer (prefer WS for big batches).
- **Protocol:** JSON-RPC 2.0. Namespaced methods: `debugger.* emulator.* gpu.* memoryScan.* accessLog.* execTrace.* transferLog.* gp0Trace.* findings.* fixtures.* experiment.*`.
- **`debugger.authenticate {token}`** — MUST be the first call on every connection or you get `-32000`. Constant-time compare; token never logged. In a batch, auth is enforced per element.
- **`debugger.status`** → `{valid, running, paused, pc, sp, cpu, game_title, game_serial, game_path, frame, cycle}`.
- **`debugger.disassemble {address, count≤1024}`** → instructions with `branch_target` + `symbol`.
- **Batch:** top-level JSON array up to 64 requests; notifications (no `id`) get no response.
- **Settings** (`settings.ini` `[ExternalDebugger]`): `Enabled` (default false), `BindAddress` 127.0.0.1, `Port` 2346, `AuthToken` (auto 256-bit hex).

## Best use in ABL RE
First thing every session/script does. The Python client `~/duckstation/scripts/debugger-client/duckstation_debug_client.py` does token auto-discovery (`find_token()` reads local `settings.ini`); `tools/abl_dbg.py` wraps it as `from abl_dbg import D; D(port=2346)`.

## Common mistakes / gotchas
- **ABL port convention:** the running game instance binds **2346**; the isolated build-test/BIOS instance uses **23460** (separate config + diff token) so experiments never disturb a live instance.
- Auth before anything else (`-32000` otherwise). Many ops require pause or a loaded system (`-32001`/`-32002`).
- Error codes: `-32000` unauthorized · `-32001` no system · `-32002` not paused · `-32003` bad address · `-32004` unsupported · `-32005` op failed · `-32006` invalid argument.

## ABL examples
The entire G29/G30 live-debugger workflow connects this way (port 2346) — see [[Experiment - G29 collision lever validation]], [[Experiment - G30 localized terrain edit]].

## Related
[[API - execution control]] · [[API - loadState]] · [[API - findings store]] · [[DuckStation API Index]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
