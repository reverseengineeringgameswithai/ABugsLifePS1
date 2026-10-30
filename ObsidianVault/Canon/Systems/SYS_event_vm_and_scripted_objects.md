---
kind: system
id: SYS_event_vm_and_scripted_objects
name: Event VM and scripted-object bytecode
aliases: ["event VM", "mover VM", "scripted objects"]
status: live_confirmed
confidence: confirmed
source_state: original_game
functions: [0x80049C30, 0x8004C13C, 0x8004C8AC]
tables: [0x8001B2F4, 0x8001B35C, 0x8001B384, 0x80077AF8]
evidence:
  - EXP_2026-07-15_phase4_event_vm
src_paths: [tools/gen_vm_disasm.py, tools/phase4_event_vm.py, analysis/vm_programs.json, analysis/phase4_event_vm.json, src_re/enemy_ai_programs.c, asm/hand_written/8004c13c_event_bytecode_interpreter.s]
---
# Event VM and scripted-object bytecode

## Confirmed original-game contract

The resident interpreter `0x8004C13C` drives enemy movers and other scripted
actors. It reads the actor source pointer at actor `+0x80`, the current bytecode
IP at `+0x70`, and a signed stream halfword at that IP. The primary dispatch
index is `signed_halfword + 1`, checked against 26, then loaded from the
26-entry table at `0x8001B2F4`. All 26 handler semantics are confirmed and all
occur in the pristine resident program bank.

The selector initializer begins at `0x80049C30`. Its decisive sequence at
`0x80049C78..0x80049C94` reads source-record byte `+0x0D`, scales it by four,
loads through `0x80077AF8`, and stores the result to actor `+0x70`. The
hash-pinned executable contains **40 valid entries and 40 unique program
starts**, selectors `0..39`, covering `0x8007745C..0x80077AC0`. The next word is
`0x03020100`. Retail performs no selector bounds check.

`analysis/vm_programs.json` retains 421 semantic instructions across all 40
programs. It also corrects branch operands to signed `s16`: the branch at
`0x80077602` has operand `-5` and target `0x800775FA`, not an out-of-region
unsigned target.

## Native and overlay CALL frontier

Opcode 12 selects one of nine stubs through `0x8001B35C`:

| Slot | Target | Residency |
|---:|---:|---|
| 1 | `0x80057A94` | resident |
| 2 | `0x80057920` | resident |
| 3 | `0x800B3D78` | Region A |
| 4 | `0x800B3B70` | Region A |
| 5 | `0x800B3BD4` | Region A; predicate result feeds `s3` |
| 6 | `0x800B3DC8` | Region A |
| 7 | `0x80057C74` | resident |
| 8 | `0x80057B84` | resident |
| 9 | `0x800B3F00` | Region A |

All 20 pinned `LEVELnn/LEVEL*.BIN` images were checked at all five Region-A
targets. Nine exact function starts exist: LEVEL02 state writers, LEVEL03 spawn,
LEVEL05 audio/comparison, LEVEL07 completion, LEVEL08 ground, and LEVEL09 flag
handlers. The same virtual address means different code—or no function—in
another image. Therefore no `0x800Bxxxx` CALL target is a universal verb.

## Runtime ownership and lifecycle

The actor pool is 64 records of `0x84` bytes at `0x8009FD80`; a live record has
nonzero actor ID and zero-ID holes do not terminate the scan. Pristine words at
`0x8004D248/0x8004D24C` construct the base, `0x8004D410` adds the stride, and
`0x8004D41C` loops while the index is below 64. Relevant fields are flags
`+0x5C`, signed wait `+0x60`, IP `+0x70`, optional callback `+0x7C`, and
scene-owned source pointer `+0x80`. The separate program selector table remains
40 entries; its size is not actor capacity.

Fresh evidence in [[EXP_2026-07-15_phase4_event_vm]] reproduced:

- 83 VM fetches across the corrected 64-slot pool during a v3 from-boot LEVEL01 movie;
- actor/source/IP snapshots in Training, stages 1–15, and all three bonuses,
  including 64/64 live slots in Tunnels, Riverbed Run, and Bonus 3;
- selectors 0 and 39 resolving to the first and last programs;
- selector 40 resolving to invalid word `0x03020100`;
- pause freezing the full actor table, then resumed actor progress;
- native same-scene death restoring health 4 and producing four post-respawn
  fetches; and
- exact LEVEL01 actor/source mappings after a distinct LEVEL02 load.

Only six of the 19 breadth anchors fetched within the fixed 12-frame trace
window. The other 13 are retained as **idle windows**, not absence claims:
actor waits may exceed the window. The corrected full-pool census has at least
one live actor in every anchor; the old zero-actor Bonus 2 observation came from
starting at slot 1 and stopping on the first zero hole.
Independent source/IP snapshots still remain inside the fully decoded bank.

## Consumer boundary

This system owns bytecode selection, fetch, handler/CALL/motion dispatch,
actor/source state, overlay-target qualification, and their lifecycle. Enemy
damage/death, prop and gate policy, rendering/animation assets, audio outcomes,
persistence/results, and stage objectives belong to their D, E, and F
campaigns. Those consumers may rely on this typed handoff, but their outcomes
must not be promoted into this VM contract.

## MOD safety derived from original behavior

- Validate every authored selector as `0..39`; never rely on retail to reject it.
- Decode branch operands as signed `s16`.
- Condition overlay CALL hooks on the exact loaded image and retire them before
  Region A is replaced.
- Preserve the fixed 64-record actor capacity independently from the 40-entry
  selector table, and initialize private state
  before the selector/interpreter reads it.
- Treat actor slots, compact live-enemy indices, source pointers, and Region-A
  addresses as lifetime-scoped rather than persistent identity.

Machine contract: `config/phase4_event_vm.yaml`. Complete retained evidence:
`analysis/phase4_event_vm.json`.
