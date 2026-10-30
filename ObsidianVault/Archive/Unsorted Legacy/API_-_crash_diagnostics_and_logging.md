---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - crash diagnostics and logging.md
aliases:
  - "API - crash diagnostics and logging"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - crash diagnostics and logging.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - crash diagnostics and logging
type: api
category: Connection
tags: [api, duckstation, logging, crash, diagnostics, ops]
updated: 2026-06-17
---
# API — crash diagnostics and logging

> How to capture DuckStation's console output to a file and correlate an unexpected crash with the last API request that was being processed. Operational/diagnostics, not a JSON-RPC method.

## Console log capture (50 MB, rotating)
- **Launcher wrapper:** `~/duckstation/build-release/bin/duckstation-qt-logged` — runs `duckstation-qt`, tees combined **stdout + stderr** to a log file. The start-menu entry **"DuckStation (Dev Build)"** (`~/.local/share/applications/org.duckstation.DuckStation.desktop`) was repointed at this wrapper, so it logs automatically.
- **Log file:** `~/.local/share/duckstation/duckstation-console.log` (under `$XDG_CONFIG_HOME/duckstation` if that var is set).
- **Cap:** active log capped at **50 MB**; on overflow it's moved to `duckstation-console.log.1` (one backup, overwritten on the next rotation) and a fresh file starts. Worst case ~100 MB total; oldest data is dropped.
- Each launch appends a `===== session start: <timestamp> =====` marker. `awk` flushes per line, so the log is current even on a hard crash. Tail live: `tail -f ~/.local/share/duckstation/duckstation-console.log`.
- This is independent of DuckStation's own `[Logging] LogToFile` (`duckstation.log`) — leave that off unless you also want the structured in-app log. Crash backtraces go straight to the stderr fd and **bypass** the in-app log, so only the console capture catches them.

## Why this matters for crashes
- On **Linux** DuckStation writes **no** minidump/`.dmp`/`.txt` crash files (that path is Windows-only). It prints a backtrace to **stderr** then re-raises `SIGABRT`, so the OS produces the core dump.
- Your build is `Release` **with debug_info, not stripped** → backtraces have real function names.
- OS coredumps: `coredumpctl list | grep duck`, then `coredumpctl info <PID>` / `coredumpctl gdb <PID>` for a full backtrace with locals.

## Per-request API logging (new)
- `HandleMethod()` in `src/duckstation-qt/debuggerrpc.cpp` now emits `INFO_LOG("API request: {}", method)` for **every** dispatched JSON-RPC call (channel `DebuggerServer`).
- Default `LogLevel = Info` + `LogToConsole = true`, so with the wrapper the **last `API request:` line sits directly above the crash backtrace** — you see *which command* you sent and *where* it died.
- Method name only (no params) — cheap, PII-free, and the auth token is still never logged. Adds one line per request (counts against the 50 MB cap).

## Common mistakes / gotchas
- Launching the binary directly (or via the AppImage entry) bypasses the wrapper → no console log. Use **DuckStation (Dev Build)** from the start menu, or run `duckstation-qt-logged` from a terminal.
- Bumping `LogLevel` to `Debug`/`Trace` fills the 50 MB cap fast — only do it deliberately.
- The in-app `duckstation.log` will NOT contain crash backtraces; use the console capture for those.

## Related
[[API - connection and auth]] · [[API - determinism]] · [[DuckStation API Index]]

Source: `~/duckstation/build-release/bin/duckstation-qt-logged`, `src/duckstation-qt/debuggerrpc.cpp` (HandleMethod), `src/common/crash_handler.cpp` (Linux = stderr + coredump)
