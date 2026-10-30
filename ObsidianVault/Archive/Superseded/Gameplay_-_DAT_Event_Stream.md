---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay - DAT Event Stream.md
aliases:
  - "Gameplay - DAT Event Stream"
migration_action: split
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay - DAT Event Stream.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Gameplay_-_DAT_Event_Stream.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay - DAT Event Stream
type: core
updated: 2026-06-20
tags: [core, gameplay, events, dat, scripting, milestone6, gap-0033, b10]
---

# Gameplay — byte-stream cursor source (GAP-0033)

> Resolves *what seeds and feeds the shared byte-stream cursor* `0x800822f4` ([[Gameplay - Events and Triggers]], [[MEM - Event System Globals]]). **Conclusion (overlay-static pass, 2026-06-20): the cursor has exactly ONE seed in the whole game image — `cursor = 0x80017DB4`, a fixed RESIDENT EXE data table, written once by [[FUNC_8005B714]] (a gameplay-state reset). The LEVEL.BIN overlay does NOT seed it (refuted); no instruction sets `cursor = DATbase + K`. This CORRECTS the prior "no resident base-seed / seed in LEVEL.BIN overlay / source = LEVEL.DAT" model.** All STATIC, EXE-read (`tools/exe_read.py`); runtime confirmation is local-only ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Cursor global & the DAT-runtime cluster
`0x800822f4` = shared **sequential byte-stream read cursor** (a pointer). Universal *consumer* idiom at its writer sites: `lw v1,0x22f4 ; addiu v0,v1,N ; sw v0,0x22f4 ; lbu ?,0(v1)` (read N bytes, advance N). Adjacent **DAT-runtime globals**:

| Addr | gp-off | Global | Set by |
|---|---|---|---|
| `0x800822f0` | +0x558 | `G_DAT_ENTRY_COUNTER` | DAT parser [[FUNC_8001CDC0]] (`sw zero,1368(gp)` init `0x8001cf3c`; `++` `0x8001cf5c/60`, `0x8001d2f4`) |
| `0x800822f4` | +0x55c | **byte-stream cursor** | **seeded once** at `0x8005b900` ([[FUNC_8005B714]]); elsewhere only `+=N` increments |
| `0x80082498` | +0x700 | `G_DAT_BASE_PTR` (DATbase) | one writer `0x8003d4ac` = loaded LEVEL.DAT buffer |
| `0x800824ac` | +0x714 | `G_TRAIL_BLOCK_PTR` | parser `0x8001cf40` (`sw s2,1812(gp)`) |

Boot-image value of the cursor is **0** (zero-initialised) — it must be seeded by code before any consumer runs.

## The seed — found, and it is RESIDENT
[[FUNC_8005B714]] @ `0x8005b900`: `lui v0,0x8001 ; addiu v0,v0,32180 ; … ; sw v0,0x22f4(at)` ⇒ **`cursor = 0x80017DB4`** (absolute resident address, **not** `DATbase+K`). The seed runs on **scene-init**: shell SM `0x8004fa40` calls `FUNC_8005B714(current_scene_id)` @ `0x8004fdf0` (init-once guarded by `0x800822f8`). **Role of `0x80017DB4` now DECODED → [[Gameplay - Resident Event Stream]]:** a ~2052 B **resident pseudo-random table** (entropy 7.91/8.0, mean 0x80, 256/256 distinct), read by consumers as zero-mean signed coordinate offsets `(byte−0x80)<<4` + low-bit variant/gate selectors — a shared **noise/dither source**, not a script.

## Exhaustive seed proof (why this is the *only* seed)
`exe_read.py` over the EXE **and** both LEVEL01 overlays (`--base 0x800b39a0 --hdr 0`):
- Cursor writers: **105 resident + 5 (LEVEL.BIN) + 5 (LEVEL1.BIN)**. A register back-trace classifies **104 resident + all 10 overlay** as RMW increments; **only `0x8005b900` is a seed**.
- Idiom-complete: `--store-ea 0x800822f4` (tracks `lui`/`ori`/`addiu` constants) finds no store the offset-xref missed; **all 105** offset-`0x22f4` stores use a `lui 0x8008` base (0 literal-pool bases); **0** gp-relative (`0x55c(gp)`) stores; the literal `0x800822f4` appears in **no** data pool (so no `lw base,pool(gp); sw rX,0(base)` seed is possible).
- **Overlays never reference DATbase `0x80082498`** and never seed the cursor — they only consume/increment it (e.g. event/update verb `0x800b3bb8`). ⇒ **overlay-seed hypothesis REFUTED.**

## Parser-family grouping (cursor *consumers*, by containing function)
| # writers | function | role |
|--:|---|---|
| 35 | [[FUNC_80054EAC]] | grain pickup handler |
| 26 | [[FUNC_800586B0]] | contact / pickup walker |
| 15 | `0x80046330+` region | loader / DAT-walk |
| 10 | `main_shell_state_machine` `0x8004fa40` | shell update |
| 7 | `0x8005b134/714` region | state handlers (incl. the seed in [[FUNC_8005B714]]) |
| 6 | [[FUNC_80053814]] | type-0x3f object dispatch |
| 5 | [[FUNC_80059E44]] | contact allocator |
| 1 | [[FUNC_80025084]] | collision/containment |
→ A *diverse* set of consumers (grain, walker, type-0x3f, contact, shell, state) all pull bytes from the **one** shared cursor — consistent with a shared resident byte source, not a per-object LEVEL.DAT walk.

## Data-source verdict (REVISED)
- **Cursor stream base = RESIDENT (`0x80017DB4`)** — CONFIRMED by the sole decoded seed. The byte stream the cursor walks **starts in the EXE image, not in the loaded LEVEL.DAT buffer**.
- **`cursor = DATbase + K` — REFUTED** (no such store exists; the overlay never touches DATbase).
- **DATbase / LEVEL.DAT is a *separate* mechanism.** `DATbase+offset` governs **record pointers**: parser [[FUNC_8001CDC0]] builds `record = DATbase + offset` (`0x8001cf48`) and **relocates in-record offset fields to absolute pointers** (`field += DATbase`, `0x8001cf8c–a0`). That is how per-level LEVEL.DAT object/pickup records are reached — *independently* of the cursor's resident byte stream.

⇒ The prior note's "the cursor walks per-object bytes inside LEVEL.DAT (LIKELY-HIGH)" conflated two systems and is **superseded**: the cursor's stream is resident; the per-level data lives behind `DATbase+offset` record pointers.

## Correction log
- Prior **"no resident base-seed"** → WRONG. There **is** a resident seed (`0x8005b900`); the earlier classifier missed it (increment-vs-seed ordering bug). Now found via register back-trace.
- Prior **"seed is set in the LEVEL.BIN overlay"** → REFUTED. The overlay only increments the cursor.
- Prior **"source = LEVEL.DAT (LIKELY-HIGH)"** → CONTRADICTED for the cursor's stream base (resident `0x80017DB4`).

## Confidence
- Sole cursor seed = `0x8005b900` → `0x80017DB4` (resident) — **CONFIRMED (static, exhaustive)**.
- Overlay does not seed the cursor — **CONFIRMED (static)**.
- Role of the resident table `0x80017DB4` (level-script vs shared command/template/PRNG byte source) — **RESOLVED 2026-06-21: PRNG/noise (param source), NOT a script.** Adversarial scan of all 66 cursor readers found **zero** that use a byte as a `jr`/`jalr` opcode index — every consumer uses bytes as signed coordinate offsets `(b−0x80)<<4` or low-bit gate/variant scalars ([[Event and scripting system]] Lane 2).
- Whether the gameplay cursor actually walks `0x80017DB4` at runtime — **CONFIRMED 2026-06-21 (runtime, LOCAL-ONLY):** at level02.sav play `cursor=0x80018034` (inside `[0x80017db4..0x800185b8]`), advancing ~1 byte / several frames (sporadic, not per-tick).
- **The AUTHORED event interpreter is a SEPARATE lane** (not this cursor): the per-object mover/PATH bytecode VM [[FUNC_8004C13C]], whose **opcode stream is RESIDENT in the EXE** (program-pointer table `0x80077af8` → programs `0x8007745c..0x800776ec`; per-object IP `object[+0x70]`). Only opcode-9's **path waypoints** are in LEVEL.DAT, reached via the `DATbase+offset` record pointers this note documents. **(Corrected 2026-06-21 — the earlier "opcode stream lives in LEVEL.DAT records" reading is REFUTED; see [[FUNC_8004C13C]] §"Program source = RESIDENT".)** → [[Event and scripting system]] Lane 3.

## Open question & decisive next step
**What is `0x80017DB4`, and does the gameplay cursor really start there?**
1. **Static:** classify the resident table — decode how 2–3 consumers *use* the bytes ([[FUNC_80053814]] type-0x3f, [[FUNC_80054EAC]] grain): direct parameters (coords/counts) vs indices/opcodes that dereference per-level tables. Trace [[FUNC_8005B714]]'s computed-`jalr` caller (which state invokes the reset).
2. **Runtime (local-only, decisive, minimal):** at LEVEL01 gameplay read `0x800822f4` and DATbase `0x80082498`. If `cursor == 0x80017DB4` ⇒ resident-stream model confirmed. If `DATbase ≤ cursor < DATbase + sizeof(LEVEL.DAT)` ⇒ a per-level seed exists that static cannot see (it would have to be runtime-computed) — reopen with a write-watch on `0x800822f4` across the level load.

## Modding relevance
A **level-event editor** needs the stream's *content* source. This pass shows the cursor's bytes are **resident** (in the EXE at `0x80017DB4`), while per-level object data is reached via `DATbase+offset` **record pointers** — so editing scripted spawns/params likely means editing the **resident table** (an EXE patch) and/or LEVEL.DAT records, not a single LEVEL.DAT substream. Pin down the table's role before building the editor path.

## Related
[[FUNC_8005B714]] · [[Gameplay - Events and Triggers]] · [[MEM - Event System Globals]] · [[FUNC_8001CDC0]] · [[FUNC_80053814]] · [[FUNC_80054EAC]] · [[FUNC_800586B0]] · [[Asset - LEVEL.DAT]] · [[Executable and Overlays]] · [[Gameplay - Warp and Level Transition]] · [[DuckStation Fork Reproducibility]] · `tools/exe_read.py`
