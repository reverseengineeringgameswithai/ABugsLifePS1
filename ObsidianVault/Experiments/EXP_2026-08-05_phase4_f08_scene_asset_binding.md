---
type: experiment
status: partial
date: 2026-08-05
system: scene asset loading
phase: phase4
rows: [F08_city_square]
artifacts:
  - analysis/phase4_f08_scene_binding.json
  - tools/phase4_f08_scene_binding.c
  - tools/phase4_f08_save_ram.py
---

# Scene → asset binding: sound bank is a jump table, level data is arithmetic

## Verdict

Two *different* mechanisms select a scene's assets, and conflating them is the error
running through twelve rows.

**Level data — arithmetic, no table at all:**

    dir = scene_id <= 10 ? scene_id : scene_id - 10     (slti @0x8003D204,
                                                         addiu -10 @0x8003D214)
    ori 0x0140 @0x8003D218  ->  the LEVEL1.* variant, for scene_id >= 11

**Sound bank — a permuted jump table:** `FUNC_8003CF2C` computes `jumptable[id-1]`
(bounds `sltiu <17` @`0x8003CF88`, table `0x8001AFB0`) and jumps to a per-scene
handler. The string that handler reaches in `0x8001AD0C` is a **VAB/sound-bank
prefix**, *not* a level-data path.

⚠ **CORRECTION TO THIS NOTE'S FIRST VERSION.** It presented `0x8001AD0C` as "the asset
table" and the jump table as *the* scene→asset binding. That is wrong, and the vault
already said so: Phase 3 banked this exact law on **2026-08-01**
(`analysis/phase3_scene_asset_graph.json`, `law`). I did not read the upstream artifact
before writing my own account, which is precisely the mistake that produced the
twelve bad rows in the first place. The measurements below were unaffected — the
residency results are what the arithmetic predicts — but the framing was not.

Handler → sound-bank string, read off the image:

| id | bank[] | prefix | | id | bank[] | prefix |
|---|---|---|---|---|---|---|
| 1 | [0] | level01\level1a | | 10 | [4] | level10\level2b |
| 2 | [2] | level02\level1c | | 11 | [5] | level01\level2c |
| 3 | [1] | level03\level1b | | 12 | [10] | level02\level4b |
| 4 | [6] | level04\level3a | | 13 | [11] | level03\level4c |
| 5 | [7] | **level05\level3b** | | 14 | [8] | level04\level3c |
| 6 | [3] | level06\level2a | | 15 | [14] | level05\level5c |
| 7 | [9] | level07\level4a | | 16 | [0] | level01\level1a |
| 8 | [13] | level08\level5b | | 17 | [0] | level01\level1a |
| 9 | [12] | level09\level5a | | | | |

For ids **1–15** the prefix's directory coincides with the arithmetic data directory,
which is why quoting it usually looked harmless. For **16 and 17 they diverge**: the
prefix says `level01`, the data directories are 6 and 7. Two scene-17 training saves
hold `LEVEL07_LEVEL1.BIN` resident at `0x800B39A0` — the arithmetic is right and the
string is not the path.

## F08 corrected

The row asserted *"Scene id 5 → scene_asset_table 0x8001AD0C[4] = level10\level2b;
overlays LEVEL10_LEVEL/_LEVEL1"*. All three parts are wrong:

- scene 5's **level data** is `LEVEL05/`, `LEVEL.*` variant (arithmetic: 5 ≤ 10);
- the index `[4]` is a **jump-table** index, not an index into the string table — the
  two are permuted, so `level10\level2b` is scene id **10**'s sound bank;
- `OVL/LEVEL10_LEVEL1.BIN` **does not exist** — the disc's `LEVEL10/` directory has
  no `LEVEL1.BIN`.

Confirmed physically, offline, against the save fixtures: all five F08 states read
`scene_id == 5` at `0x80082504`, and `OVL/LEVEL05_LEVEL.BIN` is resident at
`0x800B39A0` while `LEVEL10_LEVEL.BIN` is **not resident anywhere in RAM**.

## Eleven rows carry the same error

Every row stating this binding indexed `0x8001AD0C` at `id-1` — the **jump-table**
index. Because the two tables are permuted, that quotes a different scene's sound
bank, and (for ids 1–15) implies the wrong directory too. **Twelve** rows are
affected once `D18_thud` is included; all twelve are now corrected.

| row | claims | truth |
|---|---|---|
| F02_tunnels | [2]=level02\level1c | [1]=level03\level1b |
| F03_council_chamber | [1]=level03\level1b | [2]=level02\level1c |
| F04_cliffside_canyon | [5]=level01\level2c | [3]=level06\level2a |
| F05_riverbed_run | [9]=level07\level4a | [4]=level10\level2b |
| F06_birdnest | [10]=level02\level4b | [5]=level01\level2c |
| F07_city_entrance | [3]=level06\level2a | [6]=level04\level3a |
| F08_city_square | [4]=level10\level2b | [7]=level05\level3b |
| F11_the_tree | [11]=level03\level4c | [10]=level02\level4b |
| F12_battle_arena | [12]=level09\level5a | [11]=level03\level4c |
| F13_anthill_two | [8]=level04\level3c | [12]=level09\level5a |
| F14_riverbed_flight | [7]=level05\level3b | [13]=level08\level5b |
| F15_canyon_showdown | [14]=level05\level5c | [14] — **correct** |

**Why it survived.** Only ids **1 and 15** satisfy `index == id-1`. F15 uses id 15,
so its binding is right *by coincidence*, and it was independently corroborated by
D20's live `transferLog` resolution to `LEVEL05/LEVEL1.DAT`. A rule that is confirmed
only where it coincidentally holds is not confirmed — this is the same shape as the
knockdown-slot-writer error: a check that passes while asserting a wrong claim.

These eleven are **reported, not rewritten** — each row may have guards keyed to its
current text, so the sweep is a deliberate follow-up, not a side effect of F08.

## Method (no emulator)

The fork is mid-change, so a live check would not be attributable to the binary this
evidence was taken on. Everything here is static or offline:

- `tools/phase4_f08_save_ram.py` parses the `.sav` container directly (zstd via CLI)
  and **locates** the 2 MiB RAM by matching the game's own executable image, requiring
  **two distant anchors to agree** on the base before returning. RAM is not at a fixed
  offset in the blob and a silently-wrong base would shift every address by a constant.
- Overlay identity uses **≥2 agreeing high-entropy code slices**, with zero-vs-zero
  byte agreement excluded. That exclusion mattered: naive matching gave LEVEL05
  99.33% *and* would have flattered any low-entropy file; on non-trivial bytes it is
  LEVEL05 **99.14%** vs LEVEL10 **5.53%**.

Cross-checked at five independent scenes — 3, 4 (LEVEL04_LEVEL), 2, 5, and 14
(LEVEL04_LEVEL1) — all matching the map.

⚠ `LEVEL09_LEVEL1.BIN` slice-matches in several saves as a **false positive**, at a
*wandering* base (`0x800B3990` / `39BC` / `39CC`). The true overlay is always exactly
`0x800B39A0`. Base stability is the discriminator; a single slice hit is not identity.

## What a first pass got wrong

- **Assumed an off-by-one.** `table[5]` is `level01\level2c`, not level05 — refuted by
  the tool, which is why the check now asserts the refutation rather than the guess.
- **Assumed `OVL/` naming tracked the scene.** It tracks the **disc directory**, and
  directories are **reused** by two stages each (level01, level02, level03, level04,
  level05 all appear twice). A directory name alone cannot identify a scene.
- **Nearly matched on padding.** The first residency number counted zero-vs-zero
  agreement. Same family as the F16 non-unique-signature error.

## Still open (F08's actual objective)

The row's real question — *how performers are found via markers* — is **not**
answered. Region A differs in only **4 bytes of 7,656** across the five per-performer
fixtures, so the objective state is not in the overlay's static data. The five saves
also do not form a cumulative progression, so a subset-chain search over resident RAM
found no mask. Next step is a live per-performer trace once the fork settles.

## Related

- [[SYS_scene_asset_load_graph]] — the table this corrects the indexing of
- [[EXP_2026-08-03_phase4_f15_canyon_showdown]] — the coincidentally-correct row
