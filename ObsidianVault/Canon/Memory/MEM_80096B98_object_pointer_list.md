---
kind: memory
id: MEM_80096B98
aliases: [MEM_80096B98, 0x80096b98]
address: 0x80096B98
name: object_pointer_list
status: static_seen
confidence: confirmed
source_state: original_game
system:
  - SYS_berry_pickup_render_descriptors
read_by:
  - FUNC_800253E8
written_by:
  - MOD_blackberry_net_new_berry
related_structs: []
evidence:
  - mod/patch.asm
src_paths:
  - mod/patch.asm
patch_policy: targeted_runtime_repair_only
---

# MEM_80096B98 - object_pointer_list

## Purpose

Runtime object descriptor pointer list used by pickup/projector paths. Kind-indexed entries resolve type-0x3f/pickup descriptors.

## Confirmed behavior

- Kind `0x25` maps to entry `0x80096C2C` because `0x80096B98 + 0x25 * 4 = 0x80096C2C`.
- Blackberry/Fastberry repairs only `object_pointer_list[0x25]` to point at private descriptor `0x80081234`.
- This targeted repair avoids overwriting native descriptor memory such as `0x80082030..0x8008203C`.

## Modding policy

Only repair entries for mod-owned kinds. Do not globally redirect native berry/seed descriptors unless a new live trace proves the ownership and visual side effects.

## Evidence

Source: `mod/patch.asm`

```asm
bb_desc_fix:
    addiu   at, gp, -0x0B64         ; gp=0x80081d98 -> NEWBERRY_DESC=0x80081234
    lui     v0, 0x8009
    sw      at, 0x6C2C(v0)           ; object_pointer_list[0x25]
    j       0x8002532c
    nop
```
