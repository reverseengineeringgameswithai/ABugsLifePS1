---
kind: function
id: FUNC_8007403C
aliases:
- FUNC_8007403C
- 2147958844
- consume_flag_37
- '0x8007403c'
- pad_direct_clear_command
address: '0x8007403c'
name: consume_flag_37
status: byte_matched
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
evidence:
- EXP_2026-07-08_understanding_campaign_u1
- EXP_2026-07-08_c_decompilation_campaign_v1
- EXP_2026-07-10_c_conversion_at_scale
src_paths:
- src/main/8007403c_move_byte_37_to_38.c
patch_policy: unknown
---

# FUNC_8007403C - consume flag (+0x37)

> **RCA a3 merge (2026-07-09):** merged the duplicate `FUNC_8007403C.md`. This function is also **byte-matched from C** — `src/main/8007403c_move_byte_37_to_38.c` compiles to the exact bytes at `0x8007403c` (`validate_build.py` SHA-1 PASS) — hence `status: byte_matched`.

## Purpose

Read-and-clear latch on an object's byte field `+0x37`: reads `obj[+0x37]`, clears it to 0, and stores the previous value into `obj[+0x38]` (a one-shot flag consume — "take the pending value, remember it, reset for next frame"). 16-byte leaf.

## Known behavior (full disasm)

```
lbu v0, 0x37(a0)     ; v0 = obj->flag37
sb  zero, 0x37(a0)   ; obj->flag37 = 0
jr  ra
sb  v0, 0x38(a0)     ; (delay) obj->prev37 = v0
```

## Evidence (runtime, u1.1)

- **Byte-matched** (C) and **dynamic** — fired live during LEVEL01 (`execTrace`), `a0` an object pointer.
- Naming tier: **proven** (behavior unambiguous from the 4-instruction body + byte-matched + dynamic).

Address `0x8007403c` (16 B). See [[EXP_2026-07-08_understanding_campaign_u1]].
