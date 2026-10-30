---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8005B714.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8005B714.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8005B714_gameplay-state_reset_-_byte-stream_cursor_seed.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8005B714 — gameplay-state reset / byte-stream cursor seed
type: function
address: 0x8005B714
confidence: CONFIRMED (static, EXE-read)
tags: [function, gameplay, events, scripting, dat, milestone6, gap-0033]
---
# FUNC_8005B714 — gameplay-state reset & the cursor's sole seed

> The **only place in the whole game image** that *seeds* the shared byte-stream cursor `0x800822f4` ([[Gameplay - DAT Event Stream]], [[MEM - Event System Globals]]). It is a gameplay-state reset: it zeroes a broad block of the `0x80082xxx` state cluster and sets the cursor to a **fixed resident address `0x80017DB4`**. All STATIC (`tools/exe_read.py` on `SCUS_942.88`); runtime confirmation is local-only ([[DuckStation Fork Reproducibility]] / GAP-0001).

| Field | Value |
|---|---|
| Address | **entry `0x8005B70C`** (`lui v0,0x8008; lw v0,0x22f8(v0)` init-guard, then `addiu sp,sp,-40` @ `0x8005b714`); prev fn [[FUNC_8005B134]] ends `jr ra` @ `0x8005b704` |
| Role | gameplay-state reset / initializer, **called per scene-init** with `a0 = current_scene_id` |
| Confidence | CONFIRMED (decoded) |

## The seed (decisive)
```
0x8005b87c: lui   v0, 0x8001
0x8005b880: addiu v0, v0, 32180        ; v0 = 0x80017DB4  (= 0x80010000 + 0x7DB4)
   … (v0 untouched; intervening ops only write `at` and store zero) …
0x8005b900: sw    v0, 8948(at)         ; at=0x80080000 ⇒ store to 0x800822f4 (the cursor)
```
⇒ **`cursor (0x800822f4) = 0x80017DB4`**, an **absolute resident address** — *not* `DATbase + K`. Boot-image value of the cursor is `0` (zero-initialised), so this is the cursor's first real value.

## What `0x80017DB4` is — DECODED → [[Gameplay - Resident Event Stream]]
A **resident, baked-in pseudo-random byte table** (file offset `0x85B4`): begins after a function-end (`jr ra` @ `0x80017db0`); **~2052 B** to `0x800185b8`; **entropy 7.911/8.0, mean exactly 0x80, 256/256 distinct values** (`exe_read.py --region-stats`); referenced once (this seed). It is a **shared noise/dither source** — consumers read 1–3 bytes as zero-mean signed coordinate offsets `(byte−0x80)<<4` and low-bit variant/gate selectors. Full decode + consumer table: [[Gameplay - Resident Event Stream]].

## Also resets (same function)
Zeroes a block of the gameplay-state cluster (all `0x80082xxx`): halfwords at `+0x23a0/0x2470/0x224e/0x22b0/0x2472/0x2414/0x241c/0x2368`, byte `+0x2362`; plus `0x800b3998` (Region-A header word), `0x80090b78/0x80090b90`. This co-location with `current_scene_id` (`0x80082504`), the counter (`0x800822f0`) and DATbase (`0x80082498`) marks it a **gameplay-state (re)initialiser**.

## Called by (callers) — RESOLVED 2026-06-20
**`jal 0x8005b70c` from `0x8004fdf0`**, inside the **shell / main state machine `0x8004fa40`** (the same function that writes `current_scene_id` `0x80082504`). The call site is `… sw v0,0x2504(at) [scene_id]; lw a0,0x2504(at); jal 0x8005b70c; bne v0,zero,…` ⇒ **the reset is invoked as part of scene-init, with `a0 = current_scene_id`**, and its return value steers the SM. The init-once guard (`0x800822f8`, the loaded-stage var, written by the same SM at `0x8004fb4c/fbdc`) makes it run once per stage entry.

> *Earlier "0 `jal` callers" was an artifact of searching for `0x8005b714` (the `addiu sp` line); the real entry is `0x8005b70c`.* The function is **not** in the scene-handler/loader/state dispatch tables — it is a direct callee of the state machine. State path = **gameplay/level-init (scene entry)**, not warp-execution, death, or menu.

## Globals & structures touched
- **Writes** `0x800822f4` (cursor seed) — the one decisive store.
- Zeroes the `0x80082xxx` gameplay-state cluster (above). See [[MEM - Event System Globals]].

## Evidence & confidence
- Seed store + constant `0x80017DB4` — **CONFIRMED (decoded; v0 provably unclobbered between `0x8005b880`→`0x8005b900`)**.
- Sole-seed status — **CONFIRMED (exhaustive)**: across all store idioms (gp-relative, `lui`+offset, `lui`+`ori`, `lui`+`addiu`-ptr, literal-pool base) the cursor has exactly **105 resident + 10 overlay** writers; a register back-trace classifies **104 resident + all overlay** as RMW increments and **only this one** as a seed. The literal `0x800822f4` is absent from every data pool, so no other seed is possible.
- Invocation path — **UNKNOWN** (computed `jalr`).

## Related
[[Gameplay - Resident Event Stream]] · [[Gameplay - DAT Event Stream]] · [[MEM - Event System Globals]] · [[Gameplay - Warp and Level Transition]] · [[FUNC_8005B134]] · [[FUNC_8001CDC0]] · [[Gameplay - Events and Triggers]] · [[Executable and Overlays]] · [[DuckStation Fork Reproducibility]] · `tools/exe_read.py`
