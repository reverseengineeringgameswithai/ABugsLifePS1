---
kind: experiment
id: EXP_2026-08-04_mover_vm_indistinguishable_opcodes
status: complete
source_state: original_game
system: [SYS_event_vm, SYS_enemy_ai]
row: []
---

# The mover-VM "park" opcodes do not exist

**Substrate correction, not a row.** Surfaced while trying to describe Thumper's arena for
[[EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber]] — but it belongs to the shared mover-VM
substrate, so it is banked here and D16's arena item stays open rather than absorbing it.

## The defect

`analysis/vm_programs.md` named **eight opcodes** that all dispatch to **one address**:

| primary-table index | name it carried | confidence it carried |
|---|---|---|
| 1 | `park_end` | CONFIRMED |
| 6 | `park_seek` | CONFIRMED |
| 7 | `park_arrive_test` | CONFIRMED |
| 8 | `park_arrive_stop` | CONFIRMED |
| 10 | `park_path` | CONFIRMED |
| 18 | `park_seek18` | CONFIRMED |
| 19 | `park19` | CONFIRMED |
| 21 | `park21` | CONFIRMED |

All eight slots of the primary table `0x8001B2F4` hold **`0x8004C818`**. The interpreter dispatches
with `jr`, so eight opcodes reaching the same address cannot behave differently. At most one of
those eight distinctions could ever have been real.

Worse, `0x8004C818` is **not an operation body**. It is the interpreter's shared **loop tail** —

```
0x8004C1EC  lhu v0,0(s1)          ; fetch
0x8004C1F4  addiu v0,v0,1         ; index = stream + 1
0x8004C200  slti v0,v1,26
0x8004C208  addu s7,s1,zero       ; s7 = IP at fetch
0x8004C20C  ... jr [0x8001B2F4 + idx*4]
...
0x8004C818  bne s1,s7,0x8004C1EC  ; <- every real handler jumps HERE on exit
```

— the continuation every genuine handler `j`s to when it finishes. A table slot pointing straight at
it executes no operation at all; it only reaches the tail's IP-commit path.

The names give the game away on their own: `park19`, `park21`, `park_seek18` are positional
inventions. They were marked CONFIRMED anyway.

## Second defect in the same artifact: 27 missing programs

`PROG_PTRS = 0x80077AF8` was walked with a hard-coded `range(13)`. Walking until a value leaves the
program region gives **40 entries**. So `analysis/vm_programs.md` was disassembling **13 of 40
programs** and silently omitting the rest.

## The fix — structural, not editorial

Renaming the eight labels would not stop it recurring. `tools/gen_vm_disasm.py` now **derives** the
property and refuses to emit an unsupportable distinction:

```python
_by_handler = defaultdict(list)
for i, h in enumerate(handlers):
    _by_handler[h].append(i)
SHARED_GROUPS = {h: idxs for h, idxs in _by_handler.items() if len(idxs) > 1}
# ... and fail the build if SEM gives those indices distinct names
```

Reintroducing any distinction now aborts the generator:

```
gen_vm_disasm: opcodes sharing a handler were given distinct names.
They dispatch to the same code and cannot differ:
  0x8004c818 <- indices [1, 6, 7, 8, 10, 18, 19, 21] named ['noop_shared_tail', 'park_seek']
```

The eight are now one label, `noop_shared_tail`, confidence `INDISTINGUISHABLE`. The program count
is derived the same way: **40 programs decoded, up from 13.**

Exactly one shared group exists in the whole table — every other opcode has its own handler, so the
rest of the ISA decode is untouched.

## What this changes for Thumper (the row that surfaced it)

His program was read as a park/seek loop. With the fiction removed:

```
set_byte_params [-64,-64]      ; actor +0x48/+0x49
anim_clip_load [0,2]
noop_shared_tail
call_native [4] -> 0x800B3B70  ; overlay: [0x800B4950] = 60  (throw cadence)
wait_random [63,32]
random_dir_step                ; random stream at 0x800822F4
noop_shared_tail
jump_back -> wait_random
```

**A random wanderer with random waits.** No park point, no seek, no bound — so *there is no arena in
the VM program*, and D16's arena question has to be answered by measurement (spatial envelope, then
the enforcer) rather than by reading the bytecode.

## Blast radius — flagged, deliberately not rewritten

The old names are cited across the vault. Rewriting those claims is a campaign, not this fix, and
doing it here would be exactly the scope drift this was split out to avoid.

- **`park_seek` alone appears in 35 files.**
- **6 registry rows** cite one or more: `D08_flies`, `D09_cockroaches`, `D12_centipedes_earthworms`,
  `D13_armored_beetles`, `D17_bird`, `D19_molt`.
- **4 Canon pages**: [[SYS_enemy_ai]], [[SYS_molt_boss]], [[SYS_bird_boss]], [[SYS_flies]].

⚠️ **What a citation means now.** These rows are not automatically wrong — most describe *observed
behaviour* and merely used the label to name a bytecode position. But **any claim that leans on the
opcode's supposed semantics** ("the actor seeks its park point", "it stops on arrival") is
unsupported: the opcode does nothing. D17's account of the bird's defeat, which reads an IP jump as
`park_arrive_stop`, is the clearest case — the IP jump is real, the meaning attached to it is not.

## Method note

This is the third artifact in one day that failed re-derivation (after the archived Thumper note and
the `0x80090BF2`/`BF6` counters). The pattern in all three: **a plausible name recorded as a
confirmed fact.** The generator-level guard is the first fix of the three that makes the error class
structurally impossible rather than merely corrected once.

## Reproduce

```
python3 tools/gen_vm_disasm.py      # 40 programs; aborts on an invented distinction
pytest tests/test_mover_vm_opcodes.py -q
```
