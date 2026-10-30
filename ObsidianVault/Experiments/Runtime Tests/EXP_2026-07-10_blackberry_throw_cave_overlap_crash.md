---
kind: experiment
id: EXP_2026_07_10_blackberry_throw_cave_overlap_crash
name: Blackberry throw crash from cross-module cave overflow
status: confirmed_fixed
date: 2026-07-10
confidence: confirmed
source_state: experiment
systems:
  - SYS_berry_projectile_and_homing
mods:
  - MOD_blackberry_net_new_berry
artifacts:
  - /tmp/blackberry-throw-crash-20260710.sav
  - /tmp/blackberry-throw-crash-20260710.png
  - /tmp/blackberry_throw_fix_trace.json
---

# EXP_2026-07-10 Blackberry throw cave-overlap crash

## Operator crash capture

The user authorized read-only probing of the currently crashed DuckStation instance. It was preserved rather than rebooted.

- Process: `duckstation-qt` PID `1227150`, debugger port `2346`.
- Media: `~/Downloads/ABL/build/ABL_ALLMODS.cue`, `SCUS-94288`.
- Frozen emulator frame: `8033`; visible PC was inside BIOS exception handling (`0x000000A0`).
- COP0: `EPC=0x80081194`, `BadVAddr=0x00000251`, `CAUSE=0xD0000414`.
- `CAUSE` has the branch-delay bit set and exception code 5 (`AdES`, address error on store).
- Crash state SHA-256: `03cde425c21ef6026bacf9d32027138c40ccaa02552775306ecd6b95894e2636`.
- Crash frame PNG SHA-256: `446190f8bb2748e41fca01d133d3560ab100bea2041a75dbf356186090cbb5b6`.

## Live-byte proof

The crashing build's live bytes at `0x80081180` showed golddrop's death tail continuing into Blackberry's declared throw cave:

```text
0x80081180  sb t0,0x33(v0)
0x80081184  addiu t0,zero,200
0x80081188  sh t0,0x22(v0)
0x8008118C  lhu v1,0x5C(s2)
0x80081190  addiu v0,zero,999       ; overwrote Blackberry lbu
0x80081194  j 0x800592AC            ; overwrote Blackberry lui t9
0x80081198  sh v0,0x6E(s2)          ; branch delay; overwrote private-flag load
```

The exception is therefore exact: the throw entered `0x80081190`, executed the foreign jump at `0x80081194`, then its delay-slot halfword store used throw-context `s2=0x000001E3`. `s2+0x6E = 0x251`, an odd halfword address, producing `AdES` with `BadVAddr=0x251`.

This was a build-layout regression, not a disagreement with the solved original throw ABI. The registry declared golddrop's cave as `[0x80081100,0x80081190)`, but the expanded assembly actually emitted through `0x8008119B`. The existing overlap check validated declarations only.

## Fix

1. Golddrop's death/odds block is compact again: code and table remain wholly within `0x80081100..0x80081190`, with thresholds at `0x80081188`.
2. `mod/build.py` defines `ABL_HAS_BLACKBERRY` for the generated armips wrapper. Golddrop selects either private effective index `0x80081232` or native selector `0x800A6597` at assembly time; both branches are the same three-instruction size.
3. After every module is assembled, `mod/build.py` verifies the final bytes at `0x80081190` equal the Blackberry throw prefix `970003920880193c3112219300000000`. A future overflow now aborts before disc generation.

## Isolated causal validation

- Isolated config: `/tmp/duckstation-blackberry-throw-fix-20260710`, port `23683`; stopped after the run.
- Input movie: `killing_spider.movie.json`, SHA-256 `e3c7aaacc3a387dae0cbf32a9a56a6a40f72599ab8a3a45446eda6a951376b56`, replayed from boot.
- At movie frame 4800, the corrected private state was set to native selector `0`, equipped flag `1`, effective index `5`.
- Two throws executed at frames `4898` and `4973`.
- Both throws hit every watched stage: `CAVE_THROW` entry `0x80081190`, intact prefix `0x80081194/98`, private branch `0x800811A0`, native resume `0x80047178`, power store `0x80047228`, speed flag test, and speed apply `0x800810DC`.
- Both power-store/speed events had `s1=2`, confirming red-class parity; at the private load, `t9=0x80080000` and native dispatch `v1=0`.
- End state was healthy at frame `5034`, PC `0x8004FEB0`, `BadVAddr=0`, with no address exception. Trace SHA-256: `0c7803fd93685bba9ef9f31de409aea671f703f3904ddd0c27ad9877db4aa86c`.

## Final build

- Full manifest build and all 11 embedded-file checks passed.
- Final ALLMODS BIN SHA-256: `8d53b890bc533f7d8b526c4b83a9916ed0916818e5d56326a46eb818d720ba23`.
- Embedded EXE SHA-1: `c850ca4e54dadeb9ca922a3fb5153ffd66d06df4`.
- The user's crashed instance remains untouched at its captured state; it must cold-boot the rebuilt disc to receive the repaired executable.

## Separation rule

The original throw instructions/delay slots and five-column selector ABI remain Canon. The adjacent cave allocation, manifest conditional, and post-assembly signature are MOD/build policy. Crash registers, live bytes, replay, and causal validation remain in this Experiment.
