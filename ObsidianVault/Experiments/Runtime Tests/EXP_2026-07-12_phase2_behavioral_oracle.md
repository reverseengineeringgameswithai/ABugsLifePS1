---
kind: experiment
id: EXP_2026-07-12_phase2_behavioral_oracle
name: Phase-2 pristine whole-game behavioral oracle
status: confirmed
created: 2026-07-12
updated: 2026-07-12
confidence: confirmed
source_state: original_game_runtime
systems:
  - SYS_player
  - SYS_player_action_state_laws
  - SYS_seed_carry_plant_lifecycle
artifacts:
  - tools/phase2_compare.py
  - tools/phase2_final_action_pairs.py
  - tools/phase2_seed_action_controls.py
  - tools/phase2_coverage_map.py
  - tools/phase2_proofs.py
  - analysis/phase2_stage_baseline.json
  - analysis/phase2_movie_baseline.json
  - analysis/phase2_completion_oracle.json
  - analysis/phase2_death_matrix.json
  - analysis/phase2_action_behavior.json
  - analysis/phase2_final_action_pairs.json
  - analysis/phase2_seed_action_controls.json
  - analysis/phase2_spin_disproof.json
  - analysis/phase2_capacity_hang_proof.json
  - analysis/phase2_mutation_test.json
  - analysis/phase2_negative_coverage_map.json
---

# EXP_2026-07-12_phase2_behavioral_oracle

The runtime record behind [[Phase 2 - Build the Pristine Whole-Game Behavioral Oracle]]
(exit gate passed at the sixteenth pass, externally re-verified). This note is the
evidence anchor the Canon pages cite; the playbook note holds the full pass history.

## What was built

**An executable oracle**: `tools/phase2_compare.py`, run against a fresh isolated
instance on the SHA-1-verified pristine disc. It performs **701 comparisons** over
42 typed anchors and 16 cold-boot movies and reports **0 mismatches** — and it
**fails loudly** on the known-bad ALLMODS build across every detector class it
claims (visual, audio pitch, pool contents, counters, scene flow). An oracle that
only ever passes proves nothing; this one is mutation-proven.

Coverage: identity on 19/19 stage anchors; entry/objective/completion for all 16
cold-boot playthroughs; death and respawn reproduced on 14/16 stages (the two
exceptions are documented structural negatives); pause, save/reload, transitions,
soak, in-motion frames, results screens, and per-voice SPU audio.

**20/20 core actions** carry behavioural positive/negative pairs — see
[[SYS_player_action_state_laws]] and [[SYS_seed_carry_plant_lifecycle]] for the
laws themselves.

## Laws established (detail in the Canon pages)

- **TRUE health = s16 `0x800A6594`**; damage applier `0x8004A880`; death only when
  the decrement result is **< 0** (so hp 0 = alive); respawn at hp := 4, lives − 1;
  lives 0 = the playable final life. This **corrected** the long-standing Canon
  claim that `0x800A7E2A` was health — it is the HUD pulse counter.
- **Kick** = branch `0x80048F4C` → kick timer `0x800A657A := −16`, behind six gates
  including a **fresh-press edge**.
- **Player state word `0x800A6580`** (0/1/2/4/5/6) is the real state selector;
  `0x800A6542/46` is an animation frame counter, not a state id.
- **Carry law** = identity attachment; **plant/uproot** = slot creation/teardown in
  `0x80090BF0` correlated to inputs, seed conserved, raised offset +20480.
- **Seed as weapon** = knockback `−20` written into `enemy+0x6C` on the landing
  frame, decaying 0.5/frame, enemy removed from the live table.
- **Contact allocator capacity hang** — the allocator (`0x80059E44`) is a
  round-robin free-slot search with **no full-array escape**: with all 64 slots
  occupied the call **never returns** (proven A/B via `debugger.callFunction`).
  **MOD-safety: never let a mod hold all 64 contact slots.** See
  [[MEM_800B0D18_Contact_array_800B0D18]].
- **No spin move exists** in this build (static disproof).

## Platform gotchas discovered (each cost real time)

1. **`emulator.loadState` restores the save's EMBEDDED memory card** → run movie
   replays *before* any `loadState` on an instance, or from-boot movies desync at
   the menus.
2. **`setControllerState` HOLDS a button** — a held button never produces a press
   *edge*, so edge-gated actions (the kick) never fire and look nonexistent.
3. **An execTrace watch armed during movie playback DESYNCS the replay.** A/B
   isolated: watch + seek diverges from the movie's first input, while poll-only
   stepping is faithful and byte-deterministic. Movie-lane evidence must be
   poll-only.
4. **Armed instrumentation shifts synthetic outcomes too** — with any watch or
   breakpoint armed, the A11 seed drop misses the enemy.
5. **`accessLog` and write-breakpoints never engage** under the CachedInterpreter
   repro config.
6. From-boot movies replay 1:1 **only** under `tools/launch_repro_playback.sh`
   (recording-matched config + seeded memory card).

## Method lesson (structural)

Three review rounds each found the same failure shape: *an artifact asserting
something its evidence did not support*. The fixes were structural, not cosmetic —
the coverage map went from hand-authored → derived-from-the-registry →
**evidence-inspecting** (each row's verdict is computed from artifact fields;
corrupting one value flips the row to a gap and the exit code to 1). Prefer
artifacts that cannot grade themselves.

## Reproduce

```
tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-phase2 --port 23472 \
    --token debugger-1000 --disc "Disney-Pixar A Bug's Life (v1.0).cue"
python3 tools/phase2_compare.py            # 701 comparisons, expect 0 mismatches
python3 tools/phase2_coverage_map.py       # 20/20 covered, exit 0
python3 -m pytest tests/test_phase2_closure.py tests/test_phase2_reopen.py -q
```
