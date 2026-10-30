---
type: experiment
id: EXP_2026-08-04_phase4_b06_static_frontier_continuation
created: 2026-08-04
status: completed
phase4_row: B06_invincibility
row_status: partial_open
authority: pristine_original_game
---

# Phase 4 B06 invincibility static-frontier continuation

## Decision

B06's gameplay mechanism remains strongly substantiated, but the row remains
**Partial/Open**, not bounded-exhausted and not Full. This continuation makes a
real static advance without weakening the Phase 4 standard: it validates a
relevant retained capsule, independently decodes the complete B06 production
chain from the pristine executable, and partitions the finite static residual.
It does not erase the residual paths that have not been proved disjoint.

No additional Interpreter movie is currently required. The named missing domain
is static reachability and pointer provenance for unexecuted paths; another live
replay cannot prove their absence.

## Capsule-first preflight

The central capsule index contains the relevant retained capsule:

`~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/b06_invincibility_hits`

Its manifest reports:

- pristine `SCUS-94288` media and no CD overlays;
- `complete: true`, `truncated: false`, and an empty capture error;
- 1,098 frame records over emulator frames `210229..211326`;
- 271,952,701 guest instructions of passive block flow;
- exact frame-boundary RAM, VRAM, SPU RAM, and all-register reconstruction;
- final RAM/register/cycle/frame/full-machine fingerprints identical to the
  independent control;
- movie SHA-256
  `80d8475d884348eb86bcf4c4eaa518f4f41aa439aea5100d36efbcf6d12f097a`;
- start-state SHA-256
  `193c393fe117836d3eba4cf6ba19855b7861f0fe46024d9d5c2ad9c9877040b3`.

Offline querying of RAM offset `0x0A657E` finds the first natural slot change at
movie frame 77 and subsequent changes on alternating frames through the timed
window. This agrees with the known 30 Hz, 400-tick lifecycle. The capsule is
frame-boundary evidence and is not used as a proof that unexecuted writers do
not exist.

## C-based pristine ASM result

`tools/phase4_b06_frontier.c` reads the pristine PS-X executable directly. It
checks 17 instruction anchors and decodes this production chain without using
symbolic names as evidence:

```text
blue pair[4] @ 0x8007A458 = type 7, extra 0x2000
type 7 dispatch @ 0x8001B85C -> 0x8005C744
type-7 ctor arithmetic -> 0x25
metadata[0x25] @ 0x80079700 -> action 0x0C
walker[action 0x0C] @ 0x8001B598 -> 0x800588B0
0x800588B0..0x800588D0 -> unconditional slot := 400
```

The guard also independently enumerates all six direct calls to the shared
damage handler `0x8004A700`:

```text
0x800496B0  player_vertical_update
0x80049740  player_vertical_update
0x80049868  player_vertical_update
0x8004B4A0  actor_player_contact_resolver
0x80058A48  contact_pickup_walker
0x8005C9F8  seed_plant_mine_handler
```

The exact ASM continues to establish the reusable B06 contract:

- `0x800588D0` stores 400 unconditionally, so collection refreshes rather than
  stacks;
- `0x80048640..0x80048654` decrements only positive values and cannot cross
  below zero;
- `0x80049718` suppresses one ordinary damage call before entry while a slot of
  either sign is nonzero;
- `0x8004A7A4..0x8004A828` is the inner interception path and clears the
  damage-enable register before the health store at `0x8004A888`;
- `0x80055BC4..0x80055BE8` selects visual effect ID 57 only for a positive slot
  with the grain-harvester flag clear;
- `0x8005B268` clears the slot on respawn, while the already-attributed BIOS
  block clear owns the level-load reset.

## Finite residual classification

The existing reconciled region proof agrees with the independent analyzer on
all 14 known direct accesses. It soundly excludes 165 of 416 related-function
candidates and retains 251. The new C guard classifies that retained set as:

```text
251 total = 192 reads + 59 writes
79 owner/op/base groups
29 candidates inside B06's shared direct owners
222 candidates in cross-system owners
```

Exact local disassembly partitions the 29 direct-owner candidates:

- Four are the eight-sample direction ring or its fixed reference table:
  `0x8004823C`, `0x80048290`, `0x800482C4`, `0x800482C8`.
- Two address a carried actor record from pool base `0x8009FD80` at stride
  `0x84`: `0x80048364`, `0x80048378`. Reaching `0x800A657E` would require record
  displacement `0x67A2`, whose remainder modulo `0x84` is `0x82`, so the slot is
  unreachable.
- Nineteen are bounded angle/trigonometry-table reads based at `0x80074970`.
  Their masked 12-bit index is shifted once, bounding the table family below
  `0x80076970`, disjoint from the player slot.
- Four remain deliberately open: saved-base lookup sites `0x80048E30` and
  `0x80055874`, plus returned-effect-record stores `0x80055CF4` and
  `0x80055D14`.

The machine-readable partition is
`analysis/phase4_b06_frontier_20260804.json`. The C guard rejects a stale
residual count, missing/extra local site, altered table chain, changed anchor,
or changed damage-caller count.

## Why the row remains open

The prior Canon note correctly requires an empty unresolved-intersection set
for strict closure. This pass does not provide that:

- four potential intersections remain within shared B06 owner functions;
- 222 potential intersections remain in other shared-player/actor/effect
  functions;
- the canonical `tools/phase4_static_frontier.py` compiler referenced by the
  older investigation is absent from this checkout, so its root/indirect-target
  closure cannot be regenerated;
- live absence in the valid B06 movies and capsule cannot discharge unexecuted
  static paths.

The next mechanically valid work is a general C interprocedural frontier pass
covering memory-loaded pointers and bounded `jr` target sets, followed by a
zero-intersection regeneration. That is shared infrastructure work, not another
B06 gameplay movie. Under the project's low-return rule, it is reasonable to
defer that work, but it is not reasonable to rename this row bounded-exhausted.

## Reproduction

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  tools/phase4_b06_frontier.c -o /tmp/phase4_b06_frontier
/tmp/phase4_b06_frontier \
  REBUILD/files/SCUS_942.88 \
  analysis/functions_resident.txt \
  analysis/phase4_region_provenance.json \
  analysis/phase4_b06_frontier_20260804.json
```

Related authority: [[SYS_player_power_slot]] and
[[EXP_2026-08-01_phase4_b06_b08_power_slot]].
