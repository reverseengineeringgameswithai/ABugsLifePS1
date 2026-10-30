# Phase 4 B06 bounded exhaustion

Date: 2026-08-04

## Result

`B06` is **Substantiated Partial / bounded-exhausted** inside the valid pristine-retail gameplay bound defined below.

The classification is intentionally not a strict proof over corrupt pointers, malformed level assets, arbitrary RAM mutation, or MOD executables.

## Evidence boundary

- Executable: pristine `REBUILD/files/SCUS_942.88`.
- SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Resident executable mapping: `0x80010000`, `468992` bytes.
- Existing retained capsule and clean/traced Interpreter replay cover the ordinary grant, sustained contact, countdown, expiry, and post-expiry damage lifecycle.
- Existing overlay direct-reference census is inherited. This row-specific continuation addresses the reconciled resident indirect-address frontier.
- Runtime pointer schemas must be valid retail schemas. Deliberately corrupted pointers and malformed assets are excluded.

## Observation

The static target census has 14 exact direct halfword access sites for shared power slot `0x800A657E`. The prior reconciled provenance pass retained 251 possible indirect intersections: 192 reads and 59 writes, grouped into 29 row-local and 222 cross-system sites.

The Interpreter control and armed replay both ended at emulator frame `15043`, cycle `8516822117`, and PC `0x8004FEAC`, with identical player and input-state fingerprints. The armed lifecycle recorded one grant, 400 countdown writes, no active-period health loss, and one health decrement after expiry. None of the four formerly open local PCs executed during that complete lifecycle.

## Static causal closure

`tools/phase4_b06_closure.c` compiles a per-PC closure ledger directly from the pristine executable and `analysis/phase4_region_provenance.json`. It fails closed unless all 251 sites retain their expected instruction type, function owner, memory-domain rule, and row totals.

The four formerly open local sites are now statically discharged:

- `0x80048E30`: `0x80074970 + 2*((angle)&0xFFF)` sine-table read.
- `0x80055874`: the same bounded sine-table family.
- `0x80055CF4`: particle-record field `+0x28` returned from the 64-entry pool rooted at `0x800B0D18`.
- `0x80055D14`: particle-record field `+0x2A` in the same pool.

The 222 cross-system sites are enumerated individually in `analysis/phase4_b06_closure_20260804.json`. Their domains are fixed resident tables below `0x80090000`, valid collision/level records, canonical actor/player records, contact/checkpoint records, projectile records, or effect/particle pools. The actor-domain proof uses pool root `0x8009FD80`, stride `0x84`, and the ASM bound `actor_index < 200`. The only field congruence that could reach `0x800A657E` would require actor index `201`, outside that bound. A canonical player record aliases the slot only at `+0x7E`; none of the residual player-record accesses uses that field.

## Reproduction

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  tools/phase4_b06_closure.c -o /tmp/phase4_b06_closure
/tmp/phase4_b06_closure \
  REBUILD/files/SCUS_942.88 \
  analysis/functions_resident.txt \
  analysis/phase4_region_provenance.json \
  analysis/phase4_b06_closure_20260804.json
```

Required terminal result:

```text
B06 C CLOSURE PASS: direct=14 residual=251 reads=192 writes=59 local=29 cross=222 classified=251 unexplained=0 bounded_exhausted=true
```

## Closure metric

- Direct slot sites: `14 / 14` enumerated.
- Reconciled potential intersections: `251 / 251` classified.
- Row-local residual: `29 / 29` discharged.
- Cross-system residual: `222 / 222` domain-attributed.
- Unexplained row-relevant intersections inside the bound: `0`.
- Additional Interpreter movie required: **no**.

The result is therefore `Substantiated Partial / bounded-exhausted`, not full-program semantic completion.

## Related evidence

- [[EXP_2026-08-04_phase4_b06_static_frontier_continuation]]
- [[EXP_2026-08-04_phase4_b06_interpreter_local_residual]]
- [[EXP_2026-08-01_phase4_b06_b08_power_slot]]
- [[SYS_player_power_slot]]

## Pinned artifacts

- C closure compiler SHA-256: `20b49a52d2c48e23017a9ca4d964fd9aeb9992e748f2c538ddd200a9f6532008`.
- Generated per-PC ledger SHA-256: `596580e800ef2306d0cb09fd3f81fe033a4307ec66653912651ebaba38c40141`.
