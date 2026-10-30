---
kind: hook
id: HOOK_FORBIDDEN_PATCH_RANGES
address: multiple
name: Forbidden Patch Ranges
status: static_seen
confidence: confirmed
source_state: modding_policy
system:
  - Patch Safety
original_function: []
used_by_mods: []
evidence:
  - src_re/known_crash_cave_hazards.c
  - WHYPE_forbidden_patch_ranges
src_paths:
  - src_re/known_crash_cave_hazards.c
  - mod/mods/registry.py
patch_policy: forbidden
---

# HOOK_FORBIDDEN_PATCH_RANGES

## Purpose

Patch-safety record for ranges that looked like slack or helper space but are live game state, resident tables, or native descriptors.

## Forbidden ranges — the enforced hard floor (all 6 in `FORBIDDEN_CODE_RANGES`)

These are the statically-enforced blacklist in `mod/mods/registry.py` (`mod/build.py` rejects any
cave overlapping them). Kept complete and in sync with the registry (RCA a6 / AUDIT-26):

- `0x8007EFE8..0x8007F0D8`: resident table consumed by `fcn 0x800616E0`. The bad ALLMODS Gold Berry build placed code here and crashed during level/enemy streaming (invalid write `0x910a0000` at PC `0x80061788` / COP0_EPC `0x80061784`, 2026-07-07).
- `0x8007F130..0x8007F170`: **runtime-owned Training/streaming state** (a previous cave here crashed around `0x800616c0`). *(Was undocumented in Canon before a6.)*
- `0x8007FDC0..0x80080BE0`: level-load workspace memset — EXE-baked code in this range is wiped at runtime (reads zero *in gameplay*, so static-zero ≠ free).
- `0x800814BC..0x80081530`: intro-FMV zero-init work buffer; a cave overlap hangs boot at the PlayStation logo.
- `0x80081058..0x800810A4`: live-zeroed helper range; live ALLMODS boot wiped golddrop helper bytes here.
- `0x80082030..0x8008203C`: native berry/seed descriptor; overwriting it caused seed and mega/homing colour regressions.

## Documented hazards NOT in the static floor (caught by the runtime gate)

Crash-proven or runtime-owned addresses the `registry.py` docstring flags to AVOID but that are
**event-transient** (fire only in specific states), so they are covered by the MSM runtime
write-watch gate ([[SYS_modding_safety]]), not the static blacklist. A cave near these still gets
rejected if any covered pristine state writes them; treat them as forbidden regardless:

- `0x800B4A30` — Training **overlay** runtime state (crash COP0_EPC=`0x800B4A34`, 2026-07-07). Overlay-window, outside the resident cave zone.
- `0x80081858`, `0x80081CF0` — gp-relative runtime state (`0x80081CF0` is a controller global written with the *same* value, invisible to value-diff — caught only by the `--memcheck` write-watch).
- `0x8007FBC8`, `0x8007FD58`, `0x800821FC` — runtime-owned scratch/state near the workspace and descriptor bands.

## Current guardrails

- `mod/mods/registry.py` `FORBIDDEN_CODE_RANGES` — the enforced floor above; `mod/build.py` also gates caves on the runtime-proven used-set ([[SYS_modding_safety]], `analysis/memory_map.json`).
- `src_re/known_crash_cave_hazards.c` records crash signatures.
- Gold Berry token code currently uses `0x80081100..0x80081190` (compact death hook) and `0x80078D84..0x80078E04` (pickup handling — golddrop's proven cave gap).

## Do not promote

Do not reuse old session claims that `0x8007EFE8` or `0x80081058..0x800810A4` are safe cave/helper ranges — historical and superseded. Related: [[SYS_modding_safety]].


## Machine-checked continuation contracts (Phase-3, 2026-07-13)

`mod/hook_caves.yaml` **declares** a `delay_slot.policy` and a `clobbers` list per
hook, and `tools/validate_mod_layout.py` enforces the *bookkeeping*. **Nothing
checked those declarations against the code** until `tools/phase3_hook_contract.py`
(evidence: `analysis/phase3_hook_contracts.json`, guard:
`tests/test_phase3_hook_contract.py`).

**The model** — every check is a corollary of it: a hook is `(A, size, resume, cave)`.
Every instruction of the ORIGINAL trace (`A`→`resume`) must execute **exactly once**
in the PATCHED trace (`j cave`; **the delay slot at `A+4`, which always fires**; the
cave; `j resume`). Zero times = a silent behaviour change; twice = a bug.

**Result on the 15 shipped hooks:** **6 proven outright, 8 proven subject to cave
obligations, 0 hard violations, 1 refused.**

### ⚠️ A REFUSAL MEANS "I CANNOT PROVE THIS SAFE" — NOT "THIS IS UNSAFE"

That distinction is the whole discipline, and the first pass of this tool got it
wrong by dumping two computable questions on a human. Both are now **computed**:

| Case | First verdict | The truth |
|---|---|---|
| `blackberry:berry_throw_dispatch` | "refused — a branch lands inside the hook window" | **The mod is correct.** `0x80047174` *is* branched to from `0x80047134`/`0x80047140` — but it is a **`nop` in both the pristine and the patched image**, so those paths execute the same `nop` and continue to the same place. They merely **skip the cave**, which is right: they already hold the berry index (`v1`) and need no remap. Now reported as a **declared bypass**, status **proven**. |
| `golddrop:default_pickup_branch` | "refused — something lands inside its window" | **The mod is correct, and the deletion is its entire purpose.** Its `resume` is *inside* its own window, so the original **`blez s0,0x800589e8` is deleted** — which is what "replace the default pickup branch" *means*. Legal. But a deletion is a **semantic change**, and other code `j`s straight at the deleted word, so the tool now demands it be **declared** (`drops:`) rather than being incidental. **It is currently undeclared — that is the actionable output.** |
| `blackberry:terrain_emitter_color` | refused | **Still refused, correctly:** there is **no containing function in the census**, so liveness is not computable — and the tool refuses to **guess** a register set rather than emit a contract it cannot prove. |

### Obligations that were never written down

- **Registers live at the site must be saved/restored by the cave** (7 hooks).
- **A displaced PC-relative branch CANNOT be relocated into a cave** — the cave is
  ~180 KB away, far outside the ±128 KB branch range. The cave must invert the
  condition and `j` to the computed target (the contract states that target).

### Three assumptions that will bite

1. **A branch can land inside your hook window** (see above).
2. **`k0`/`k1` are NOT free scratch** — the exception handler clobbers them
   **asynchronously**. A cave using them works until an IRQ lands inside it, and that
   bug never reproduces.
3. **A displaced load cannot be moved without its consumer** — the R3000 has **no load
   interlock**, so the original consumer reads the **stale** value. This is the
   project's own prepaid "R3000 load-delay in caves" bug, now a machine check.

**Limits, stated:** the cave *bodies* are not disassembled (post-build mode is not
implemented), so the obligations are **stated, not discharged**. Liveness is an
over-approximation, deliberately biased: it can reject a safe hook, but never accept
an unsafe one.
