---
kind: experiment
id: EXP_2026-08-03_phase4_d19_molt
status: complete
source_state: original_game
system: [SYS_molt_boss, SYS_contact_objects_and_drops, SYS_enemy_ai]
row: D19_molt
---

# Phase 4 D19: Molt boss

## Verdict

**D19 is now partial with its high-value row-specific work bounded-exhausted. We can move on, and no new Interpreter movie is required.**

The replacement movie is good. A clean normal-speed replay and a heavily armed normal-speed replay both ended at emulator frame 15651, cycle 8861074013, with `reproducible:true` and the level-complete screen. The sampled actor pool, player, overlay state, transition state, and screenshot were byte-identical between the runs.

## Why live escalation was justified

The Phase 4 capsule registry was queried first and contains no D19 identity. Static data could identify candidate assets and resident damage code, but not the live Molt record, the exact guarded-hit writer, or the crowd projectile producer. Those were named missing instruction-attribution domains, so an isolated DuckStation replay was warranted.

This experiment changed no disc, executable, asset, save, or movie. A hash-pinned state-anchored movie is therefore appropriate; cold boot is not required.

## Identity and fixture

- Config: `/tmp/duckstation-phase4-d19-recheck-20260803`
- Port: `38493`
- Mode: explicit `Interpreter`
- Media: pristine SCUS-94288
- DuckStation revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`
- DuckStation binary: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`
- Movie: `movies/Phase4/Interpreter/D19.movie.json`, SHA-256 `d3e8105ba0e2945fb1d9779bb1a4f091528f39dcdff20049b940ea62023bac5b`
- State: `movies/Phase4/Interpreter/D19.movie.sav`, SHA-256 `1b8a1d52911d4160fb1cd3ed93dc354e6b0c5a216f564c38d96f7a15d3b730f4`
- Format: v4, 7729 frames, `armed_while_paused:false`, `phase_delay_owed:false`
- Playback: `debugger.resume` plus status polling, never fast-forwarded

The save embeds a cached pristine cue and bin. They hash exactly to the canonical pristine media: cue `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`, bin `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`.

## Static-ASM correction

The first static pass incorrectly treated `LEVEL09/LEVEL.BIN` as the live fight owner. Its apparent spawn sites at `0x800B4620` and `0x800B4750` had zero runtime hits, and its word at `0x800B3CC4` disagreed with the instruction-attributed access log.

A C corpus scan resolved the discrepancy. The runtime restore instruction `sh v1,0(s1)` has word `0xA6230000`; among all 19 `LEVEL*.BIN` and `LEVEL1.BIN` files, it occurs once: `LEVEL03/LEVEL1.BIN+0x324`, exactly `0x800B3CC4`. The live secondary overlay SHA-256 is `24adb413e88885b1614995e241da9961df1dc5e0f81ba5f820c32765918c04c9`.

`tools/phase4_d19_molt.c` verifies the exact overlay words, the resident initialization/damage writers, the singular corpus occurrence, and the mover-VM opcode. It can also reduce the retained breakpoint JSON:

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  -o /tmp/phase4_d19_molt tools/phase4_d19_molt.c
/tmp/phase4_d19_molt \
  ~/Downloads/ABL-external-evidence/phase4/D19_molt_interpreter_20260803/phase4_d19_break_capture.json
```

## Live actor and charge state

Molt is live actor ID 29 at `0x8009FF90`, not the earlier ID-22 hypothesis. Across all 43 Molt collision snapshots:

- flags are `0x5043`;
- HP is actor `+0x6E` at `0x8009FFFE`;
- callback is `0x8004A0A0`, a sound callback rather than the boss FSM owner;
- mover-VM IP is `0x80077688`;
- `0x80077688` decodes to opcode 6, `park_seek`.

This is the machine-level charge binding: collision-time Molt is in the shared park/seek pursuit state. Exact animation naming is intentionally not inferred from the VM word alone.

## Damage, guard, and HP phases

The resident initializer `0x80049CA0` writes HP 50. Every crowd contact reaches shared writer `0x800590E4`, using contact class 0, `+0x24=10`, `+0x27=1`, and proposes HP minus 2.

The overlay keeps the last accepted HP at `0x800B45F4`. At `0x800B3C98..0x800B3CC4` it rejects the proposed hit when Molt `+0x44` equals 1 or the global goal latch is already nonzero. Rejection writes the previous accepted HP back at `0x800B3CC4` two or three frames later.

The complete movie contains:

- 43 Molt executions of the shared `-2` store;
- 15 accepted HP descents, exactly `50 -> 48 -> ... -> 20`;
- 28 rolled-back stores;
- final accepted hit at emulator frame 13589, movie frame 5679.

Thus raw dispatcher count is not damage count. The guard/transition overlay is the acceptance authority.

## Crowd-thrown berries

The actual producer is `0x800B41CC..0x800B4468` in the live secondary overlay. It:

- chooses one of four 12-byte XYZ origins at `0x800B45B4` using `RNG & 3`;
- aims from that origin toward Flik in X/Z;
- rejects squared distance above `0x7FFFF`;
- calls contact allocator `0x8005A0E0` at `0x800B43F8`;
- passes constructor type 71;
- arms a roughly 60-tick randomized SFX cooldown at `0x800B4468`.

The type is not the player-thrown red damage projectile. C static decoding of the pristine executable resolves metadata row `0x800799A8` for type 71 to action 32 and dispatcher target `0x800588FC`. That handler executes `sb zero,0x6597(at)` at `0x80058934`, setting Flik's equipped-berry index to native red (`0`). After collection, the ordinary Square throw dispatcher reads index 0 and allocates the separate red projectile type 2. Thus the exact chain is **crowd type 71 -> player contact/action 32 -> red equipped -> Flik type-2 throw**.

The non-truncated allocation trace has 141 total allocator entries. Exactly 31 have return address `0x800B4400`, the instruction after this crowd call. The connecting damage contacts in the Molt snapshots carry the class-0/f24-10/f27-1 tuple; they must not be identified as the incoming type-71 pickups.

## Defeat handoff

Accepted HP below 21 branches at `0x800B3DEC`. The final accepted HP 20 path:

- writes goal latch `0x800823A0 = 1` at `0x800B3E70` (corrected 2026-08-03 during integration; originally mis-cited as `0x800B3E6C`, which is the preceding `lui at,0x8008` half of the same two-instruction store, not the `sh` itself — re-verified via `tools/phase4_d19_molt.c` against the current `REBUILD/files/LEVEL03/LEVEL1.BIN`);
- writes transition timer `0x80082470 = 150` at `0x800B3E7C`;
- submits the victory effect/event chain;
- leaves later overlapping contacts subject to the already-latched rollback rule.

The normal-speed outcome is the level-complete screen. This connects crowd production, contact classification, shared resident damage, overlay acceptance, threshold, and frontend transition in one pristine replay.

## Instrumentation flight check and caveats

The clean and non-halting armed replays are the determinism authority. The broad overlay range ring was deliberately pressure-limited at 50000 events; it is not claimed exhaustive. Targeted damage watches were not truncated.

The running fork silently ignored the documented conditional-breakpoint predicate and returned `conditional:false`. The exact-snapshot run was restarted with an unconditional `0x800590E4` breakpoint and filtered by `s2` in the script. Those breakpoint captures are used only for coherent pre-store actor/contact bytes. A 32-byte actor-tail access ring reached 10000 entries; only retained instruction-attributed HP writes through frame 12282 are used. The complete collision chronology comes from the 44 breakpoint snapshots and the non-truncated targeted exec trace.

## Observation, inference, and causal confirmation

**Observation:** clean and armed normal-speed runs are byte-identical at the sampled final domains. Actor ID 29 receives 43 class-0 proposed stores; the accepted sequence contains 15 descents to 20. The live overlay allocates 31 type-71 red-arm pickups from the crowd caller and writes the goal/timer threshold path.

**Inference:** `park_seek` is the charge/pursuit state at collision time. Exact visual animation and audio labels are not inferred.

**Causal confirmation:** metadata/action dispatch proves type 71 arms red at `0x80058934`, while the throw dispatcher maps that equipped index to type 2. Instruction-attributed writes show `0x800590E4` proposing minus 2 and `0x800B3CC4` restoring rejected hits. Byte-verified control flow proves the `+0x44`/goal-latch gates, and the final accepted HP-20 path owns the level-complete latch.

## Closure boundary

D19's named gaps are closed at the high-value mechanical level: charge/pursuit state, guard acceptance, crowd throw production, HP progression, and defeat transition all have exact original owners and pristine runtime evidence. Strict status remains `partial`, not universally solved.

Deferred low-return work is exhaustive crowd-origin RNG distribution, exact animation/GPU/audio presentation timing, alternate death/restart attempts, and compiler matching of the overlay. Revisit only for a concrete dependency. No new Interpreter movie is needed now.

## Evidence preservation

Machine-readable findings are in `analysis/phase4_d19_molt.json` and `analysis/phase4_d19_type71.json`; the reusable static decoder is `tools/phase4_d19_type71_static.c`; the replay contract is `config/phase4_d19_molt.yaml`; Canon is [[SYS_molt_boss]]. Raw RPC JSON and screenshots are retained outside the repository at `~/Downloads/ABL-external-evidence/phase4/D19_molt_interpreter_20260803` with a SHA-256 manifest.
