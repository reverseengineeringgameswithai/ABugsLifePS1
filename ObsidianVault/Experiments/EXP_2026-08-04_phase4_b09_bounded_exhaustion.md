---
tags: [phase4, b09, super-jump, asm, c-analysis, trace-capsule, bounded-exhaustion]
status: substantiated-partial
row: B09
---

# Phase 4 B09 - Super jump bounded exhaustion

## Result

**B09 is Substantiated Partial, but this note does not claim bounded exhaustion.**

No new Interpreter movie was required for acquisition or jump effect. The retained B09 capsule already contains the natural blue-x4 grant and repeated post-grant jump execution. Exact post-acquisition reachability of two generic overwrite sites, plus exact level-boundary reset attribution, is reserved for the separate Item-2 tool being developed by another agent.

## Evidence identity

- Pristine executable: `REBUILD/files/SCUS_942.88`
- Pristine SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- Movie: `movies/Phase4/B09_super_jump_comparison.movie.json`
- Movie SHA-256: `aa234aef8c091f6633d1f1702f5ba4486d7c9d79d2ae2b49dcdf2c3015975c01`
- Start-state SHA-256: `97da88100124d273d0ce9bc03a726314159688a519a7be9700cedc3d4998a226`
- Capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/B09_super_jump_comparison`
- Capsule status: complete, not truncated, no error, 211 boundaries, 51,673,604 instructions
- Independent control: identical cycle, frame, RAM, registers, VRAM, SPU RAM, and full-machine fingerprint

The capsule used passive CachedInterpreter coverage and is accepted only as retained frame-boundary/control evidence. No CPU instrumentation replay was attempted against that cached movie.

## C-based method

`tools/phase4_b09_closure.c` binds the table/handler instructions, classifies the 80 concrete resident sites emitted by the region-provenance pass, scans all staged level overlays plus `BITS/MEMORY.BIN`, and validates the capsule's decisive block counts.

The separate C region-provenance pass against `0x800A6590..0x800A6591` emitted 80 concrete resident instruction sites. The generic escaped-pointer totals remain conservative over-approximations; they are not silently counted as real accesses. Closure is against the concrete instruction frontier plus an independent raw-overlay scan.

## Production chain

The pristine tables close the acquisition path:

```text
blue x4 pair @ 0x8007A464 = type 7, extra 0x4000
  -> type-7 handler 0x8005C744
  -> constructor 0x27
  -> metadata @ 0x80079728: action 0x0F, lifetime 200
  -> action dispatch @ 0x8001B5A4 = 0x800588D4
  -> sound 75
  -> 0x800588F8 stores flags | 0x20
```

`0x800588F8` is the only resident or overlay instruction that sets the super-jump bit.

## Jump effect

The vertical update reads `player+0x90` at `0x80048184`, tests `0x20` at `0x8004818C`, and selects:

| State | ASM literal | Controlled takeoff value |
|---|---:|---:|
| Normal | `-3072` | `-1344` |
| Super jump | `-3776` | `-1696` |

The controlled difference is `-352`, with shared gravity `+256` per update.

The capsule independently records one grant-handler execution, one bit-setting store, 105 jump-bit checks, and 69 executions of the super literal. `0x80048194` is the branch-delay default and executes on all 105 checks; `0x80048198` overwrites it on the 69 bit-set checks.

## Other consumers

- `0x80055C74`: while Flik is in upward mode 1 with vertical velocity below `-64`, bit `0x20` enables a constructor-61 contact/effect spawn at Flik's position.
- `0x8005C77C`: an already-owned tier-4 blue plant forces constructor 59 instead of granting super jump again.
- `LEVEL01/LEVEL1.BIN:0x800B3D38`: bit `0x20` bypasses a level-specific sound-75 call.
- `LEVEL05/LEVEL.BIN:0x800B3D94`: the same repeated-acquisition sound suppression exists in this overlay.

## Lifetime law and static reachability caveat

The bit is persistent across ordinary jumping and is deliberately retained by several shared transitions:

- `0x8005B330..0x8005B340` reduces the shared word to `flags & 0x20` during the respawn-transition normalizer. Super jump is the one bit deliberately retained there.
- `0x80054CB4` clears only `0x08`; `0x80054E90` sets only `0x08`. Checkpoint updates preserve `0x20`.
- `0x8004A94C` and `0x80048C14` use masks that preserve `0x20` through their transition paths.
- All four overlay writes touch `0x01` or `0x04` and preserve `0x20`.

The shared `player+0x7C` action-lockout path contains two structurally relevant stores:

```text
0x8004866C  decrement player+0x7C
0x8004867C  while still positive: player+0x90 := 1
0x800486BC  on expiry branch:    player+0x90 := 0
```

Both instructions are capable of clearing `0x20`, but static presence is not proof that either path is reachable after super-jump acquisition. The prior claim that cannon or knockdown cancels an obtained super jump is retracted.

The observed gameplay law is authoritative here: once obtained, super jump remains active for the rest of Flik's time in the current level. It ends at level completion, stage exit, or game over. Exact proof of why the two generic overwrite sites do not contradict that law, and exact attribution of the level-boundary reset, remains with the other agent's Item-2 tool.

## Fail-closed ledger

| Scope | Reads | Writes | Preserve `0x20` | Set `0x20` | Structurally clear `0x20` | Unclassified instructions |
|---|---:|---:|---:|---:|---:|---:|
| Resident concrete frontier | 54 | 26 | 23 | 1 | 2 | 0 |
| 20 level overlays + MEMORY.BIN | 13 | 4 | 4 | 0 | 0 | 0 |
| Total | 67 | 30 | 27 | 1 | 2 | 0 |

## Observation, inference, confirmation

**Observation:** the accepted capsule executes the natural grant once and takes the super literal 69 times after acquisition; the independent control remains byte/fingerprint exact.

**Static observation:** the only setter is `0x800588F8`; the only bit-clearing concrete stores are `0x8004867C` and `0x800486BC`; every overlay writer preserves the bit.

**Causal confirmation:** the earlier controlled A/B changed only the flag condition and measured takeoff `-1344` versus `-1696` under the same `+256` gravity. The pristine branch literals and the capsule block counts independently agree with that result.

## Closure decision

B09 remains Partial. Acquisition, velocity effect, repeated ownership, and the concrete instruction frontier are substantiated, but post-acquisition reachability of the two structural overwrite sites and the exact level-end/stage-exit/game-over reset owner are not yet causally closed.

This pass stops here. Item 2 belongs to the other agent's tool and must not be duplicated. No additional Interpreter movie is requested by this pass.

## 2026-08-04 workstream disposition

**Status override:** Substantiated Partial / bounded-exhausted for this workstream; paused and safe to move on.

The gameplay law is retained: after acquisition, Super Jump persists for the rest of the current level and ends only at a level-lifetime boundary such as stage exit, game over, or leaving the stage. The remaining exact reset-site/reachability attribution is Item 2 and is deliberately delegated to the other agent's purpose-built tool. Further work here would duplicate that lane rather than increase B09's current evidence quality. This is not a claim of Verified/source-closed status; it is the same bounded-exhaustion disposition used for other Phase 4 substantiated partial rows.
