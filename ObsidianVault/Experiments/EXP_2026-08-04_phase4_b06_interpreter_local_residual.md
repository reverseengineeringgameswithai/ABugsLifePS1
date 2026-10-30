---
type: experiment
id: EXP_2026-08-04_phase4_b06_interpreter_local_residual
created: 2026-08-04
status: completed
phase4_row: B06_invincibility
row_status: partial_open
---

# Phase 4 B06 Interpreter local-residual trace

## Result

The operator's version-4 Interpreter movie was useful and replayed with no instrumentation desync. The clean and traced normal-speed runs ended at the same emulator frame `15043`, cycle `8516822117`, PC `0x8004feac`, and identical 168-byte player plus adjacent input-state fingerprint. The movie was reproducible and neither trace ring truncated.

The four local static residual PCs did not execute anywhere in the complete natural B06 lifecycle:

```text
0x80048E30  0 hits
0x80055874  0 hits
0x80055CF4  0 hits
0x80055D14  0 hits
```

This is a bounded negative for ordinary B06 behavior, not a proof that those instructions can never alias the slot on another path.

## Positive lifecycle evidence

- `0x800588D0` executed once and wrote the natural value 400.
- `0x80048654` performed exactly 400 two-byte countdown writes.
- `0x80055BC4` executed 625 times with base register `v0 = 0x800A0000`, confirming the positive-slot visual test.
- `0x8004A888` executed once after expiry and wrote health `3 -> 2`.
- Active-period contacts produced no health write; the only health write was the intended post-expiry control.

## Provenance

- Movie: `movies/Phase4/Interpreter/B06_invincibility_lifecycle.movie.json`, SHA-256 `cce2866f28a8e3fa7c153af446b30c9f745e0377f70ce929d220fe542cb654cf`.
- Start state SHA-256: `4127047a1469ad01b742a8ec3eb53e835dc52b116dbf6c3dab5bade6f04639ec`.
- DuckStation binary SHA-256: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`.
- Mounted media: pristine `SCUS-94288`, zero overlays.
- Isolated config: `/tmp/duckstation-b06-local-20260804-01`, port `24451`; owned PID `2233529` stopped through the config-scoped launcher.
- Raw transient evidence and its hashes are inventoried in `analysis/phase4_b06_runtime_local_20260804.json`.
- Reducer: `tools/phase4_b06_runtime_reduce.c`.

## Disposition

B06 remains **Partial/Open**. The movie closes the runtime question: none of the four residual instructions belongs to the ordinary grant, active visual, protection, expiry, or post-expiry damage path. It does not close the remaining static intersection frontier. Another B06 Interpreter movie would repeat known paths and cannot prove unexecuted-path absence; further closure work is C/ASM interprocedural analysis.

Related: [[EXP_2026-08-04_phase4_b06_static_frontier_continuation]], [[EXP_2026-08-01_phase4_b06_b08_power_slot]], and [[SYS_player_power_slot]].
