---
kind: experiment
id: Experiment_-_Pickup_kind-swap
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Pickup kind-swap.md
aliases:
  - "Experiment - Pickup kind-swap"
---

# Experiment — Pickup kind-swap (changing what a pickup *is*)

> Migrated from `ObsidianVault/Experiments/Experiment - Pickup kind-swap.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Pickup kind-swap (changing what a pickup *is*)

> **Result: kind-swap WORKS, and the `kind` byte drives BOTH model and behavior.** Changed a grain pickup's `kind` (`0x14`) to **`0x30` (the green telescope / hint device)** → it **rendered as the green telescope and triggered the telescope's "continue / exit level" hint menu** when Flik touched it. Confirms [[MEM - Type-0x3f placement record]]'s `kind = item/model discriminator` — and shows it's also the *behavior* discriminator.

> [!important] **Object identity corrected (operator, 2026-06-18):** kind `0x30` is the **telescope** — the in-game hint device that reveals where an item/exit is (the "continue / exit level" menu is its hint UI: resume, or go to the exit it showed). It is **not** a "checkpoint" (my earlier guess from the menu text). This corrects the long-standing "checkpoint/trigger" label for entries 67–69 across the vault.

## Setup
LEVEL01.DAT type-0x3f entries **11/12/13** (grain, kind `0x14`) → swapped to **`0x23` blue-berry / `0x10` F-letter / `0x30` telescope** (X/Y/Z moved to a cluster). Verified two ways:
- **Disc rebuild:** rebuilt to `kindswap.bin`, mounted via the [[Experiment - FLIK letters disc mod demo|save-state-repoint]] method — the swapped kinds loaded and the game **ran each through pickup construction** (Y runtime-adjusted exactly like normal pickups ⇒ accepted, no crash).
- **Live poke (faster, no rebuild):** from the pre-load state, re-poked entries 11/12/13's `kind`+pos (via `debugger.writeMemory`) during the level load, before object construction. The kinds **held through construction**, and the items spawned in front of Flik.

## Result — CONFIRMED
- **Grain → telescope (`0x30`)**: rendered as the **green telescope** and, on contact, popped the telescope's **"continue / exit level"** hint menu — i.e. a fully-functional telescope where a grain used to be (`kindswap_poke2.png`).
- ⇒ the `kind` byte alone re-selects a pickup's **model + collision/contact behavior**; the game constructs the new object type without issue.
- (The blue-berry/F-letter swaps loaded + processed identically; the telescope is the decisive visible+functional proof.)

## Method notes (disc-rebuild plumbing — reusable)
- **Rebuild lock:** while DuckStation has the patched `.bin` mounted, `mkpsxiso` overwriting that same file stalls (timed out at 500 s). **Build to a *separate* output file** (temp xml with a new `image_name`).
- **Disc-mount cache:** `loadState` mounts the disc by the **cue path** embedded in the state, and DuckStation caches by that path — editing a cue's *contents* doesn't force a re-mount. **Use a fresh 62-char cue *path* per disc** in the repoint state (→ [[Experiment - FLIK letters disc mod demo]]).
- **Live poke** is the fast iteration path for *kind/coord* edits (no rebuild): poke the loaded DAT before construction (~during the level-load advance).

## Artifacts
`REBUILD/kindswap.bin` + `kindswap.cue` · repoint `SCUS-94288_2_KINDSWAP.sav` (+ `REBUILD/kindswap_disc___________.cue`) · `kindswap_poke2.png` (the green telescope + its hint menu).

## Related
- [[MEM - Type-0x3f placement record]] · [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Experiment - FLIK letters disc mod demo]] · [[FUNC_80053814]] (construct + contact action)
