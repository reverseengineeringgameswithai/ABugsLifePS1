# Decompilation Plan — A Bug's Life (SCUS-94288)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

## 1. Purpose and scope
Incremental, **goal-directed** hand-decompilation of the already-understood MIPS in `SCUS_942.88`,
limited to the systems we have **verified through modding and runtime tests**. The aim is a precise,
evidence-backed C-like reconstruction of the DAT/pickup/HUD pipeline that explains and supports our
modding tools (`tools/dat_reloc.py`, `tools/patch_level_entry.py`), not a whole-game decompilation.

Output lives in `src_re/`. Shared types in `src_re/re_types.h`. One function per file (or a tight
handler cluster per file). Files are **hand-decompilation notes / structured pseudocode**; they do not
need to compile yet. Accuracy beats clean C.

## 2. Non-goals
- Not a full/whole-game decompilation; not a build target; not a matching/byte-perfect recomp.
- No ISO builds, no DAT/BIN/CUE patching, no tool changes from this track (docs/scaffold only).
- No graphics/audio/overlay-code decompilation beyond what the pickup/HUD path requires.
- No invented C names, struct fields, or behavior. If unknown, label it `UNKNOWN`/`TODO`.

## 3. Current confirmed systems (decompilation targets are drawn from these)
- DAT format + parser/relocator `fcn.8001cdc0` (dynamic type table `0x80096da0`; 1248 baked-offset
  relocations; basis of `tools/dat_reloc.py`). See [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md).
- Type-0x3f source-kind dispatch `fcn.80053814` (grain/FLIK/berry/token/checkpoint). See
  [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md), [COORDINATE_MODDING.md](COORDINATE_MODDING.md).
- Contact allocator `fcn.80059e44` (array `0x800b0d18`, cursor `0x8008234c`, metadata `0x8007941c`).
- Contact/proximity walker `fcn.800586b0` (weak-Y math, radius `0x12c + rec[+0x28]`).
- Pickup handlers `0x80054288..0x80054554` + grain `fcn.80054eac`; power-up `fcn.8003e760`.
- HUD `fcn.800526f4` (grain/FLIK/seed) + helpers `fcn.800260f8`, `fcn.80025f54`.

## 4. Function priority list (status)
| Phase | Function(s) | File | Status |
|------:|-------------|------|--------|
| 1 | `fcn.8001cdc0` (DAT parser/relocator) | `src_re/dat_parser_8001cdc0.c` | **DECOMPILED** (2026-06-13) — full body; relocation model validated vs tools/dat_reloc.py (1248 LEVEL01 sites). Open items: pass-2 table @0x80091210, scene-gated sizes @gp+0x5f4, the *128 trailing word. |
| 2 | `fcn.80053814` (type-0x3f dispatch) | `src_re/source3f_dispatch_80053814.c` | **DECOMPILED** (2026-06-13) — top-level structure (loop, eligibility gate, 3 construct paths, contact jump table 0x8001b42c) confirmed; per-kind ACTION handler bodies deferred to Phase 5. Open: kind 0x30/0x31 animated-construct inner math; post-loop marker-change finalize. |
| 3 | `fcn.80059e44` (contact allocator) | `src_re/contact_alloc_80059e44.c` | **DECOMPILED** (2026-06-13) — full body; cursor/wrap + slot search + dual metadata tables (B=0x8007941c[ctorType], A=0x80079e30[stackArg]) confirmed; ContactRecord field map promoted in re_types.h. Open: fcn.800593e8 internals; metaB+0x04<0 script variant; rec+0x37. Capacity hang risk (no free-slot escape) documented. |
| 4 | `fcn.800586b0` (contact walker) | `src_re/contact_walker_800586b0.c` | **DECOMPILED** (2026-06-13) — 64-slot walker, signed live gate, flags&2 gate, weak-Y distance math, radius `0x12c+radius_add`, and dispatch table 0x8001b570 confirmed. Action-case bodies summarized only; Phase 5 ready. |
| 5 | `0x80054288..0x80054554`, `fcn.80054eac` (pickup handlers) | `src_re/pickup_handlers_80054288_80054554.c` | **DECOMPILED** (2026-06-13) — berry marker cases, seed-token counters/power-up calls, checkpoint gate, FLIK completion summary, source3f post-loop marker tail, and grain count/reward path confirmed. Open: downstream berry effects, seed-nibble mask, grain pre-effect, and unrelated nearest-entry finalize tail. |
| 6 | `fcn.800526f4` (HUD) | `src_re/hud_800526f4.c` | **DECOMPILED** (2026-06-13) — grain HUD, seed-meter loop, FLIK bitmask HUD, FLIK record-icon HUD, and pickup-relevant pulse state confirmed. Open: unrelated scene-specific panels and exact sprite atlas semantics. |

Phase 1 is highest value: it is the relocation function that explains the naive-append failure and the
`tools/dat_reloc.py` fix, and it is the most cross-referenced.

## 5. File scaffold
```
docs/DECOMPILATION_PLAN.md      (this file)
src_re/
  re_types.h                          shared structs / enums / global addresses (CONFIRMED only)
  dat_parser_8001cdc0.c               Phase 1
  source3f_dispatch_80053814.c        Phase 2
  contact_alloc_80059e44.c            Phase 3
  contact_walker_800586b0.c           Phase 4
  pickup_handlers_80054288_80054554.c Phase 5
  hud_800526f4.c                      Phase 6
```

## 6. Required standard header (every decompiled file)
Each `src_re/*.c` must begin with a block comment containing:
- **ORIGINAL ADDRESS(ES)** (and size if known).
- **CONFIDENCE** (overall: CONFIRMED / LIKELY / UNKNOWN, plus "C body = TODO" until written).
- **SOURCE NOTES** consulted (specific `docs/*.md` / `ABL_RE_NOTES.md` sections).
- **KNOWN CALLERS** (address + function).
- **KNOWN CALLEES**.
- **KNOWN GLOBALS** (use `re_types.h` names where available).
- **UNRESOLVED QUESTIONS**.
A `CONFIRMED MODEL (spec, not yet code)` section may follow, then the `TODO` decompile stub.

## 7. Naming conventions
- Files: `<role>_<addr>.c` (addr lowercase, no `0x`), e.g. `dat_parser_8001cdc0.c`.
- Functions: keep the address discoverable. Use a descriptive snake_case name and note the raw address
  in the header (e.g. `dat_parse_relocate` ↔ `fcn.8001cdc0`). Sub-handlers may use `<role>_<addr>`.
- Globals: use `re_types.h` macros (`G_*`) or annotate raw `0x800axxxx` with the confirmed meaning.
- Unknown struct fields: `unkNN` at their offset; never rename without evidence.
- Confidence words appear inline in comments next to each non-obvious claim.

## 8. Confidence-label rules
- `CONFIRMED` — verified by disassembly AND (where applicable) in-game/runtime test or byte-exact tool.
- `LIKELY` — strong static evidence, not yet runtime-verified; safe working assumption, flagged.
- `UNKNOWN` — not yet determined; do not guess a value/name.
- `TODO` — work item (e.g. "C body = TODO", "promote field when confirmed").
- Never overwrite an `UNKNOWN`/`unkNN` with a guess. Downgrade a label if evidence weakens.

## 9. Review checklist (per decompiled function)
- [ ] Standard header complete (addr, confidence, sources, callers, callees, globals, unresolved).
- [ ] Every branch/loop matches the MIPS control flow (verify `bgez/bltz/beqz/bnez/slt` senses).
- [ ] Signed vs unsigned loads correct (`lb/lh` sign-extend; `lbu/lhu` zero-extend).
- [ ] Shifts/masks preserved exactly (`<<5` runtime scale, `>>13`, `*0x300`/`*0x100`, `&` gates).
- [ ] Halfword/byte field widths preserved; no silent widening.
- [ ] Pointer-relative writes modeled as relocations where applicable (`x += DATbase; store`).
- [ ] GP-relative globals resolved against gp=0x80081d98 and named.
- [ ] Calls/returns match known callees; stack args noted.
- [ ] Claims carry confidence labels; `UNKNOWN` left as such (no guesses).
- [ ] `re_types.h` updated ONLY for fields the body actually evidences; plan status updated.
- [ ] Cross-checked against the relevant `docs/*.md` (and tool, for Phase 1).

## 10. Prompt cadence (workflow)
- **One function (or one tight handler cluster) per prompt.** Do not batch multiple phases.
- After each function: update **this file's status table** (Section 4) to `DECOMPILED` and note date/findings.
- Update **`re_types.h`** only when a field/struct is supported by the just-decompiled evidence; promote
  `unkNN` → named field with a `CONFIRMED`/`LIKELY` marker.
- **Do not overwrite uncertainty with guesses** — leave `UNKNOWN`/`TODO` if the body doesn't prove it.
- If a decompiled body contradicts the notes, STOP and reconcile (`docs/*.md` is source of truth; fix the
  loser, mark superseded in [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)).

## 11. Recommended first prompt (Phase 1)
> "Decompile `fcn.8001cdc0` into `src_re/dat_parser_8001cdc0.c`. Follow the CONFIRMED MODEL already in
> that file's header (top-level record walk → dynamic type table → trailing block → pass 1/2/3
> relocation sites A–I). Use r2 (`asm.arch=mips, bits=32, cfg.bigendian=false, anal.gp=0x80081d98`) to
> read the bytes; produce structured C-like pseudocode preserving signed/unsigned loads, shifts, branch
> senses, and pointer-relative relocations. Keep the standard header; label every non-obvious claim
> CONFIRMED/LIKELY/UNKNOWN; do not invent fields. Cross-check the relocation site set against
> `tools/dat_reloc.py` (expect 1248 sites for LEVEL01). Then update Section 4 status and, only if the
> body evidences new fields, `re_types.h`."

---

**Related docs:** [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md) · [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md) · [COORDINATE_MODDING.md](COORDINATE_MODDING.md) · [EXECUTABLE_AND_OVERLAYS.md](EXECUTABLE_AND_OVERLAYS.md) · [TOOLING.md](TOOLING.md)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)
