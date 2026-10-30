---
kind: campaign
id: phase4_native_grain_gates
phase: 4
row: E09_grain_gates
status: completed
---

# Game Solving Campaign - Native Grain Gates

## Decision

E09 is complete. The reusable fixture frontier, all known gate locations and
thresholds, both state machines, denial feedback, natural positive/negative
behavior, closed-gate death/game-over, successful-open native death/respawn,
and native card persistence boundary are directly reproduced.

## Authority and fixture selection

The campaign consumes the complete existing `movies/Phase4/E09` set: twelve v3
movies plus twelve paired states. Each file is centrally hash-pinned, classified,
provisioned, and verified; operator bytes remain ignored and untracked. Every
state was inspected before load as pristine `SCUS-94288`, and every replay
verified the mounted pristine CUE/track. ALLMODS was not used as authority.

Filenames are leads only. The `LEVEL02_*` set runs scene 3 (Tunnels); the three
`LEVEL07_*` files actually run scene 4 (City Entrance). Replay outcomes, not
words such as `closed_open`, determine the assertions.

## Reproduced frontier

- Tunnels owns nine `0x14`-byte records at `0x800B4C1C` with exact state, id,
  threshold, X, and Z. Thresholds cover every row and five movies naturally
  lower one selected gate `4295 -> 1680`.
- City Entrance owns three s32 words at `0x800B4570`. Pinned LEVEL04 code
  computes thresholds 10, 20, and 30; natural 9/19/29 branches remain closed,
  while one-byte 10/20/30 controls open exactly the selected gate.
- Both implementations request SFX 76 below threshold and seed a denial
  countdown from the next byte addressed by `0x800822F4` plus 60.
- A Tunnels closed-gate death decrements lives without opening. A game-over
  branch retires scene 3 for scene 1. From an already-open state, fatal contact
  in both Tunnels and City decrements one life, restores health to 4 at the
  unchanged safe anchor, and preserves scene, grain, and every gate word.
- Existing `movies/Menu-Navigation.movie_v2.json` reproduces native load and
  save from boot with the centrally pinned isolated card seed. Native load
  restores an exact card-resident 336-byte block; native save writes a
  controlled byte from `0x8009EC68..0x8009EDB7` verbatim to the local card.
  Pristine MEMORY.BIN proves that this complete range excludes `0x800A65A1`,
  Tunnels `0x800B4C1C`, and City `0x800B4570`. Gate words retire on unload;
  scene setup initializes them and normal grain/proximity updates may reopen.

The staged City overlay is an exact byte authority. The live Tunnels overlay in
the pinned saves does not match the checked-out staged extraction; only its
bounded live hash and decisive instruction words are retained. No false staged
byte-match claim is made.

## Machine layers

- `tools/phase4_grain_gates.py`
- `analysis/phase4_grain_gates.json`
- `config/phase4_grain_gates.yaml`
- `config/phase4_campaigns.yaml`
- `config/record_types.yaml`
- `config/semantic_state.yaml`
- `analysis/mechanics_baseline.yaml`
- `tests/test_phase4_grain_gates.py`

Canon facts are in [[SYS_native_grain_gates]]. Runtime observations, causal
mutations, and the excluded non-neutral access-log hypothesis remain in
[[EXP_2026-07-11_native_and_training_grain_gate]]. No MOD-private hook or state
was introduced.

## Exit decision and bounded residual

The low-level predicates in `analysis/phase4_grain_gates.json` close E09. The
remaining Tunnels mismatch is provenance-only: the save-owned live function is
hash/word pinned but differs from the checked-out staged extraction. Preserve
that qualification and do not claim a staged byte match until a hash-verified
retail extraction produces the same image. It does not leave behavior open.
