---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - frame hashing.md
aliases:
  - "API - frame hashing"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - frame hashing.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - frame hashing
type: api
category: GPU-VRAM
tags: [api, duckstation, hash]
---
# API — frame hashing

> Hash an image file — perceptual (aHash/dHash) for "did it change?" or sha256 for exact bytes.

## Methods & syntax
**`emulator.hashFrame {path, region?, hash?="ahash"|"dhash"|"sha256"}`** → `{width, height, region?, hash_type, hash}`. aHash/dHash = 16 hex (compare via Hamming distance); sha256 = 64 hex exact. Runs off-core (no pause needed).

## Best use in ABL RE
Cheap regression check: hash a region across two states to detect (or rule out) a visible change without pixel-by-pixel diffing.

## Common mistakes / gotchas
- aHash/dHash are perceptual (NOT DCT pHash) — small Hamming distance = visually similar. Use sha256 only when you need exact-byte identity.

## ABL examples
Quick "did the sky change?" checks alongside [[API - gpu.readVramRect]] in the G30 sky work.

## Related
[[API - frame capture]] · [[API - visual diff]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
