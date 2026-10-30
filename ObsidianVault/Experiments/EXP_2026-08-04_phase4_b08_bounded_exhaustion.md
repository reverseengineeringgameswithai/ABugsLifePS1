# Phase 4 B08 bounded exhaustion

Date: 2026-08-04

## Result

`B08` is **Substantiated Partial / bounded-exhausted** inside the valid pristine-retail gameplay bound.

The earlier B08 campaign had already established the ordinary lifecycle and most interfaces. Its row-level status remained open only because the shared `0x800A657E` alias frontier was not classified. The B06 C closure now provides that shared, sign-independent provenance ledger; this continuation independently guards every B08-specific negative-slot mechanism.

## Capsule-first decision

The retained `v3/B08_bubble_repeated_hits` capsule is complete and untruncated. It identifies pristine `SCUS-94288`, reports an empty error and mismatch set, and matches the independent control in cycle, frame, RAM, and registers. Its 519-frame boundary reconstruction includes registers, RAM, VRAM, and SPU RAM. Therefore no live DuckStation escalation or new Interpreter movie is justified.

Movie SHA-256: `79ca8b68d3d807cbf4b72563cde28720890489d71ec3201e15b816af037ffdb3`.

Start-state SHA-256: `737dbae3af40a7dc30d5c1af78a2219ae83125ce45c59d4100c34c9942529ac0`.

## Static mechanism closure

`tools/phase4_b08_closure.c` verifies the following directly against the pristine executable:

- Blue x3 pair-table entry 6 is `(type 6, extra 0)`.
- Type 6 dispatches to `0x8005C6F0`, which produces ctor `0x1F`.
- Metadata row `0x1F` selects action `0x2E`.
- Walker action `0x2E` dispatches to grant handler `0x80058998`.
- `0x800589A0` materializes `-3`; `0x800589A8` stores it unconditionally, so recollection refreshes rather than adds capacity.
- `0x8004A7E0` reads the signed quota; non-negative values take the ordinary damage route.
- Eligible negative contacts execute `0x8004A804/0x8004A808`, adding one toward zero. A nonzero stagger timer prevents consumption.
- The positive-only timer at `0x80048640..0x80048654` skips negative values, so B08 has no time decay.
- Zero removes the negative-only renderer and restores the health decrement at `0x8004A888`.
- `0x80051C3C` is the negative-only shell renderer. The `0x80078E4C` color ramp has exactly three meaningful quota entries for `-3`, `-2`, and `-1`.
- Respawn and the exceptional knockdown reaction both clear the shared slot.

## Shared frontier inheritance

`analysis/phase4_b06_closure_20260804.json` is sign-independent because it classifies possible addresses of the shared halfword, not B06-specific values. It accounts for 14 direct sites and all 251 reconciled potential intersections: 29 local plus 222 cross-system, with zero unexplained sites.

B08 inherits that address-provenance result but not B06's positive-timer semantics. The B08 C guard independently proves the negative grant, contact gate, quota transition, renderer, reset, and production dispatch described above.

## Runtime lifecycle

- Grant: movie frame `183`, slot `0 -> -3`.
- Eligible contacts: frame `365`, `-3 -> -2`; frame `495`, `-2 -> -1`; frame `593`, `-1 -> 0` and shell pop.
- Post-pop contact: frame `649`, health `4 -> 3` through `0x8004A888`.
- Refresh control: preloading `-1` before collection still produces `-3`, not `-4`.
- Cross-power control: a B08 grant replaces positive B06 time because both use the same slot and grants are unconditional.

## Reproduction

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  tools/phase4_b08_closure.c -o /tmp/phase4_b08_closure
/tmp/phase4_b08_closure \
  REBUILD/files/SCUS_942.88 \
  analysis/phase4_b06_closure_20260804.json \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/B08_bubble_repeated_hits/manifest.json \
  analysis/phase4_b08_closure_20260804.json
```

Required result:

```text
B08 C CLOSURE PASS: direct=14 shared=251/251 specific=8/8 anchors=19 unexplained=0 transitions=-3,-2,-1,0 bounded_exhausted=true
```

## Closure metric

- Shared direct sites: `14 / 14`.
- Shared reconciled frontier: `251 / 251` classified.
- B08-specific mechanism groups: `8 / 8` guarded.
- Lifecycle transitions: grant, three absorbs, pop, and post-pop damage observed.
- Unexplained row-relevant intersections inside the bound: `0`.
- Additional Interpreter movie required: **no**.

The result is bounded exhaustion, not a strict proof over corrupt pointers, malformed assets, arbitrary RAM mutation, or MOD executables.

## Related evidence

- [[EXP_2026-08-04_phase4_b06_bounded_exhaustion]]
- [[EXP_2026-08-01_phase4_b06_b08_power_slot]]
- [[SYS_player_power_slot]]

## Pinned artifacts

- C closure compiler SHA-256: `cfe3c088d2a3eb39da89f3632ee5473674d1790809ccc0ddc3c9d000952d7d70`.
- Generated closure ledger SHA-256: `c6b0ddae57aa7ab8f0b494071684399a43547d79b9d48ef57cbdcdfaf65a7c07`.
