---
kind: experiment
id: EXP_2026-07-09_fmv_engine_bounded_close
name: FMV engine bounded-close — FMV.BIN is stock PsyQ libpress orchestration, no custom decoder
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_fmv_player_streaming]
fixtures: []
artifacts: [REBUILD/files/FMV/FMV.BIN, analysis/functions.json]
---

# EXP_2026-07-09_fmv_engine_bounded_close

## Question
The only open FMV residual was "MDEC VLC/decode and DMA internals" inside the undisassembled `FMV.BIN`
overlay (base `0x800B5788`, 509,800 B). Bounded scope (user-chosen): disassemble it, confirm it is a
stock PsyQ MDEC/STR decoder, pin where the MDEC/DMA work happens, document the boundary — NOT a full
VLC/IDCT decompile.

## Method
Static disassembly of `REBUILD/files/FMV/FMV.BIN` (flat load at `0x800B5788`, verified: valid MIPS,
landmarks match — frame-count total `*(s16*)0x80131EEE`, completion flag `0x800CAC10` written at the
frame-limit loop `0x800B6B28`). Scanned the whole overlay for hardware-register construction (`lui
*,0x1f80` KSEG0 **and** `lui *,0xbf80` KSEG1) and bucketed every `jal` into resident-range vs
overlay-self targets, naming the resident targets from the census.

## Findings

### 1. FMV.BIN contains ZERO hardware-register access
Across all 509,800 bytes: **0 sites** constructing any I/O register address — not MDEC (`0x1F801820/24`),
not DMA0/1 (`0x1F8010A0/B0`), not GPU (`0x1F801810/14`), in either KSEG0 (`0x1f80`) or KSEG1 (`0xbf80`).
The overlay pokes no hardware directly.

### 2. It is pure stock-libpress STR-player orchestration
FMV.BIN makes 256 `jal`s to 54 distinct **resident** functions — the entire stock PsyQ streaming +
display + kernel stack, and **no `DecDCT*`/MDEC function among them**:
- **libpress STR ring** — `StSetRing 0x8006D3A4`, `StSetStream 0x80070B20`, `StGetNext 0x80070C9C`,
  `StClearRing 0x8007094C`, `StFreeRing 0x80070BA8`, `StCdInterrupt 0x80070D80`.
- **libcd** — `CdRead2 0x80070898`, `CdRead`/`CdReadSync`, `CdControl`/`CdControlF`, `CdMix`, `CdGetToc2`.
- **libgpu/libgs** — `LoadImage`, `ClearImage`, `PutDispEnv`, `SetDispMask`, `DrawSync`,
  `SetDefDispEnv`/`SetDefDrawEnv`, `FntPrint`.
- **kernel/libapi** — `OpenEvent`/`EnableEvent`/`WaitEvent`/`CloseEvent`, `DMACallback`, `ResetCallback`,
  Enter/ExitCriticalSection, `printf`.

### 3. Decode completion is async flag-signaled, with the stock timeout diagnostic
The decode-wait function (`0x800B6C9C`) is a **software spin-wait**: `count = 0x800000; do { count--; }
while (count && !done_flag[s0+0x2c])`, and on timeout `FntPrint("time out in decoding !")` (string at
`0x800B5B80`). The `done` flag is set asynchronously by the libpress CD/DMA interrupt path
(`StCdInterrupt` + the DMA callbacks FMV.BIN installs) — the standard PsyQ async STR model. FMV.BIN then
`LoadImage`s the decoded frame to VRAM and swaps display buffers.

## Result — fmv_engine_closed
The MDEC/DMA "internals" the residual named **do not exist as game code**: the FMV overlay is stock PsyQ
`libpress` STR playback orchestration with **no custom decoder and no direct register access** — the
VLC/IDCT/DMA work lives entirely inside the resident PsyQ library (the `StCdInterrupt`/DMA-callback
path), which is the standard, documented PsyQ MDEC/STR pipeline, not something game-specific to reverse.
The boundary is therefore *closed by identification*: there is no proprietary decode to decompile.
`fmv_engine_closed` → True. See [[SYS_fmv_player_streaming]] · the resident streaming layer (already
mapped: `StSetRing`/`StGetNext`/`CdRead2`).
