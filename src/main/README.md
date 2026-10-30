# src/main - byte-matched resident C (docs/SUBSTRATE.md)

The C gate opened on 2026-07-08. This directory currently contains 80 clean-room
reimplementations that compile byte-exactly with the pinned GCC 2.7.2/maspsx
pipeline. Every source is registered with a census-exact extent in
`config/segments.yml`; the rebuilt EXE must retain SHA-1
`af43de22474f15664d0e17498fbd27faeb7ed111`.

Logic-matched but nonmatching C stays in `src/wip/`. Hand-decompilation notes
stay in `src_re/`; neither is counted as byte-matched source.
