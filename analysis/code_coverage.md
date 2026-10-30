# Code coverage — whole-image function census

Regenerate: `python tools/re_baseline.py --all && python tools/function_census.py`.
Canonical data: `analysis/functions.json` / `analysis/functions.csv`.

## Resident EXE (text 0x80010000–0x80082800)

- functions: **946**
- classified code bytes: **388,644 / 468,992 (82.9%)** — the remainder of the image is data (strings/tables/rodata) or unrecovered code
- JAL anomalies (call into a non-start): **0**
- weak starts dropped inside string data: 0
- reconstructed from source (byte-exact, substrate): **626 asm + 287 C** = 913 functions (96.5% of resident functions; full metric in `analysis/decomp_progress.json`)

### By confidence

| confidence | functions |
|---|---|
| confirmed | 963 |
| high | 2 |
| low | 1 |
| medium | 32 |

### By classification

| classification | functions |
|---|---|
| bios_thunk | 46 |
| crt0 | 1 |
| data | 52 |
| game | 519 |
| sdk_psyq | 380 |

### By discovery signal (a function can carry several)

| signal | functions |
|---|---|
| dynamic | 705 |
| entry | 1 |
| gap_code | 1 |
| ghidra | 697 |
| j_target | 3 |
| jal_target | 541 |
| jumptable | 56 |
| psyq | 352 |
| r2 | 833 |
| reachable | 371 |
| symbol | 953 |

## Overlays

| overlay | functions | code bytes | image bytes | jal anomalies |
|---|---|---|---|---|
| LEVEL01_LEVEL | 3 | 1456 | 1676 | 0 |
| LEVEL01_LEVEL1 | 4 | 2380 | 2696 | 0 |
| LEVEL02_LEVEL | 5 | 3772 | 4028 | 0 |
| LEVEL02_LEVEL1 | 7 | 4232 | 4268 | 0 |
| LEVEL03_LEVEL | 7 | 4200 | 5032 | 0 |
| LEVEL03_LEVEL1 | 3 | 2796 | 3180 | 0 |
| LEVEL04_LEVEL | 8 | 2672 | 3064 | 0 |
| LEVEL04_LEVEL1 | 5 | 4480 | 4920 | 0 |
| LEVEL05_LEVEL | 6 | 1864 | 2396 | 0 |
| LEVEL05_LEVEL1 | 5 | 4324 | 4668 | 0 |
| LEVEL06_LEVEL | 5 | 1376 | 1604 | 0 |
| LEVEL06_LEVEL1 | 5 | 1492 | 1816 | 0 |
| LEVEL07_LEVEL | 7 | 6944 | 7652 | 0 |
| LEVEL07_LEVEL1 | 8 | 3920 | 4332 | 0 |
| LEVEL08_LEVEL | 5 | 2540 | 3496 | 0 |
| LEVEL08_LEVEL1 | 5 | 3612 | 4060 | 0 |
| LEVEL09_LEVEL | 7 | 4908 | 5228 | 0 |
| LEVEL09_LEVEL1 | 1 | 328 | 528 | 0 |
| LEVEL10_LEVEL | 4 | 1812 | 2076 | 0 |
| MEMORY | 66 | 31376 | 36448 | 0 |
