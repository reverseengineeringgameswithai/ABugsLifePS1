---
kind: system
id: SYS_indirect_dispatch_map
name: Indirect dispatch map (jump tables and dispatch sites)
status: live_confirmed
confidence: confirmed
source_state: original_game
evidence:
  - EXP_2026-07-12_phase3_architecture_maps
  - analysis/phase3_dispatch_map.json
  - analysis/phase3_jr_tables.json
  - analysis/phase3_jalr_callbacks.json
src_paths:
  - tools/phase3_dispatch_map.py
---

# SYS_indirect_dispatch_map

## Confirmed original-game contract

Every place the resident executable transfers control through a register is
enumerated, and the campaign-critical jump tables are decoded target-by-target
against the function census and symbol store.

### Decoded tables (44/44 targets resolved and named)

| Table | Address | Slots | Index domain | Consumer |
|---|---|---|---|---|
| mover/event VM opcodes | `0x8001B2F4` | 26 | opcode `0..25` | `FUNC_8004C13C` |
| berry throw | `0x8001B1C0` | 5 | equipped berry id `0..4` (`0x800A6597`) | berry throw chain |
| plant behaviours | `0x8001B848` | 13 | plant **type − 2** (types 2..14) | walker `0x8005BFBC..` |

**VM dispatch, byte-verified.** At `0x8004C1FC..0x8004C220` the interpreter
bounds the opcode (`sltiu v0, v1, 26`), scales it, loads the handler
(`lw v0, -0x4D0C(at)` — i.e. `0x8001B2F4 + op*4`) and `jr v0`. The 26 slots hold
19 distinct handlers; unused opcodes point at `mover_vm_dispatch_next` (the
fall-through), which is how the table stays dense.

**Berry throw is five entry offsets into one function.** All five slots land
*inside* `berry_throw_dispatch` at `0x8004719C`/`A8`/`B4`/`BC`/`C8` — the
per-berry entry points that set the throw POWER (red 2 / blue 5 / homing 8 /
gold 11 / mega 45) before joining the common path. This is precisely why the
table **cannot be extended in place** for a new berry: there is no spare slot
and the targets are interior offsets, not independent functions.

**Plant behaviours index by type − 2**, cross-checked against the independently
derived seed Canon: cannon → `0x8005C110`, propeller → `0x8005C258`,
trampoline → `0x8005C58C`, dandelion → `0x8005C818`, and the green
passive-collision handler `0x8005CCE8` (shared by two type slots).

### The full dispatch bound — and the correction that shrank it

Scanning all censused resident code for `jr <reg ≠ ra>` and `jalr` gives **234
indirect-dispatch sites**: **95** `jr` and **139** `jalr` callback calls.

The `jr` sites were then **backward-sliced** through the compiler idiom
(`sltiu` bound → `sll` scale → `lui`+`addu` base → `lw` → `jr`), and the result
corrects the frontier rather than merely shrinking it:

| Class | Count | Meaning |
|---|---:|---|
| **table dispatch** | **36** | decoded — **869 entries, every one landing in a named function** |
| **computed code jump** | **45** | `jr base + (index << k)` — an **unrolled loop / jump island**. **There is no table.** |
| unresolved | 14 | the honest remainder (8 constant-target `ori` forms, 2 without a bound, 2 wrong slices refused, 1 `addu` of two non-shifted values, 1 gp-relative base) |

⚠️ **Not every `jr <reg>` is a table dispatch.** Nearly half of them jump *into
code* — common in the GTE paths. Calling those "undecoded tables" overstated the
frontier by ~2×, and a tool that "recovered" a table address for one of them would
be pointing at **instructions, not pointers**: patching there corrupts code.

**Self-check:** the slicer independently rediscovers the three tables decoded by
hand (mover-VM `0x8001B2F4`, berry throw `0x8001B1C0`, plant behaviours
`0x8001B848`). A slice whose entries do not resolve to censused code is **refused**,
not reported.

**For a mod:** to add a handler you must raise the `sltiu` **bound** — appending to
a table is not enough, because the bound is what makes an index reachable.

## The indirect CALL sites (`jalr`) — the game's own hook mechanism

The 139 `jalr` sites are calls through a function **pointer**. Where the pointer
comes from is what matters:

| Source | Count | What it means |
|---|---:|---|
| **global callback slot** | **99** (30 distinct slots) | a fixed address holding a handler — **write it and the call is redirected, with no code patching at all** |
| **function-pointer field** | 36 | loaded from a record at a fixed offset (`+0x8` ×9, `+0x10` ×8, `+0x14` ×4, `+0x0` ×3, …) — a **typed-record** fact |
| unresolved | 4 | reported with reasons |

**Installed at the stage01 anchor** (resolved live — no static read can tell you
this): `trapIntrVSync` `0x80080EBC`, `def_cbsync` `0x800818C4`, `def_cbread`
`0x80081BDC`, `music_loop_poll` `0x800818C8`, `printf` `0x8007FBC4`, the whole
`pad_direct_*` family (`0x80081CF0..0x80081D74`), `_dws` `0x800A65D8`. Twelve slots
hold **NULL**.

⚠️ **Three things a mod must not assume:**

1. **A NULL slot is not a "free hook."** Whether the call site guards against NULL
   is **unverified** — a half-installed slot jumps to garbage.
2. **These are not all equal.** `trapIntrVSync`, `def_cbsync` and `def_cbread` run
   in **interrupt context**: a replacement must be interrupt-safe and preserve the
   original ABI.
3. **Handlers are not necessarily constant.** They were read at *one* anchor and may
   be re-installed per scene.

Used carefully, though, a callback slot is a **far safer extension point than a code
cave**: it is the redirection mechanism the game already uses on itself.

## Known boundary

`object_pointer_list` at `0x80096B98` (kind → render descriptor) is **not** an
EXE table — it is RAM/BSS populated at load time from level data. Enumerate it
per-scene through the debugger, not from the image.

## Regeneration

| What | Command | Evidence | Guard |
|---|---|---|---|
| tables + site inventory | `python3 tools/phase3_dispatch_map.py` | `analysis/phase3_dispatch_map.json` | `tests/test_phase3_dispatch.py` |
| jr backward-slicing | `python3 tools/phase3_jr_tables.py` | `analysis/phase3_jr_tables.json` | `tests/test_phase3_jr_tables.py` |
| jalr callback slots | `python3 tools/phase3_jalr_callbacks.py` | `analysis/phase3_jalr_callbacks.json` | `tests/test_phase3_jalr_callbacks.py` |

Both need the local pristine EXE.
