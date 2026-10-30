---
kind: system
id: Thumper_boss_fight
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_confirmed
confidence: confirmed
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Thumper boss fight.md
aliases:
  - "Thumper boss fight"
archived_source: ObsidianVault/Archive/Superseded/Systems_Thumper_boss_fight.md
patch_policy: unknown
---

# Thumper_boss_fight

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Thumper boss fight.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Thumper boss fight — solved
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Thumper_boss_fight.md`
- Migration action: `split`
- Migration confidence: `confirmed`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Thumper boss fight — solved`
- `## The actor — Thumper is a regular chunk-31 enemy`
- `### The mosquito throw (traced in the act — movie frame 58953, operator's 58950–58973 window)`
- `## HP + the berry-tough damage law (RESIDENT — overlay claim refuted)`
- `## Defeat trigger — HP ≤ 20 (causally proven)`
- `## Method + a new gotcha`
- `## Residuals`
- `## Related`

## Defeat transition — CORRECTED 2026-08-04 (D16 / F03)

The long-standing binding *"defeat at HP ≤ 20 → `0x80090BEE = 2`"* was **half right and
misattributed**. Re-derived with a compiled pin tool and confirmed live
(`thumper_boss.movie.json`, HP 50 → 20 in 15 two-point hits, scene 2 → 0):

- **The HP binding stands exactly.** Thumper's actor record is the chunk-31 slot at `0x8009FE04`;
  HP is `+0x6E` = **`0x8009FE72`**; the threshold is `slti v0,v0,21` — **HP ≤ 20**.
- **`0x80090BEE` is not a Thumper variable at all.** It is the flags field of the shared cinematic
  camera — see [[SYS_cinematic_camera]]. The value `2` is the flags argument the overlay passes when
  it starts the defeat cutscene; the same value is passed by the resident telescope path and by
  several unrelated level overlays.
- **The level exit is a different store.** In `LEVEL02/LEVEL.BIN` — the blob actually resident in
  region A during the fight, verified by hashing the live window, *not* `LEVEL03/LEVEL1.BIN` as the
  scene name suggests:

  ```
  0x800B4070  lh v0,[0x8009FE72]   ; HP
  0x800B4078  slti v0,v0,21        ; defeat threshold
  0x800B4090  bne [0x800823A0],0   ; once-only guard (the latch is its own guard)
  0x800B4118  v0 = 2               ; cinematic-camera flags argument
  0x800B4138  jal 0x8004DA94       ; start the cinematic camera
  0x800B4190  sh v0,[0x800823A0]   ; *** THE LEVEL EXIT ***  (v0 = 1)
  ```

  Camera start first, goal latch second, one straight-line block, same frame. No consumer of
  `0x80090BEE` touches `0x800823A0`, the scene id, or any loader.

### Traced 2026-08-04 (Interpreter movie `D16_Thumper_Defeat.movie.json`)

- **The HP arc is instruction-level now.** `berry_tough_damage_dispatch` `0x800590E4` writes
  `0x8009FE72` **exactly 15 times**, 50 → 20 in steps of 2. Init 50 by `mover_init_from_record`
  `0x80049CA0`; final 0 by the overlay's `level_completion_handler` `0x800B45AC`.
- ⚠️ **The legacy "fight phase/attack counters at `0x80090BF2` / `0x80090BF6`" claim is REFUTED.**
  `0x80090BF6` is written only by the BIOS (bulk zeroing at load) — no game code touches it.
  `0x80090BF2` is written by `gameplay_effect_spawner` `0x8005CD2C`, cycling 0/1/1/2 on a ~48-frame
  period throughout play, before and after the fight. Neither is Thumper's. Both sit at camera-block
  `+0x32` / `+0x36`, i.e. the same misattribution as `0x80090BEE` — see [[SYS_cinematic_camera]].
- The defeat cinematic is **never released** via the camera selector's exit path in this scene; the
  level ends with it active.

### The fight itself, traced 2026-08-04

**Thumper has no fight-phase counter, and his species callback is not a driver.**

The species dispatcher (`0x8004A484..0x8004A6C0`, jump table `0x8001B264`, species 6..41) installs a
per-species callback at actor **`+0x7C`**. Thumper is **species 16**; his arm `0x8004A5EC` is
**shared with species 22 and 36**, and the callback it installs, `0x8004A0F4`, is 40 bytes:
`play_sound(26, actor+4)`. A sound trigger — the same trap [[SYS_thud_bug_bar_boss]] already
recorded for Thud on the same field. The census name `thumper_driver_cb` is wrong.

⚠️ Stores in the dispatcher are written against `s1 = actor + 8`, so the literal `0x74` in
`sw fp,0x74(s1)` is actor **+0x7C**. Reading it literally gives an answer wrong by exactly 8.

His behaviour is the shared mover-VM: IP `+0x70` seeded to `0x80077634` (program-table entry 9) by
`mover_init_from_record` and advanced by `0x8004C834`; `+0x6C` is the VM wait countdown
(`0x8004C1C0`); `+0x44` is an action state cycling 0/1/2 (`0x8004C110`). On defeat the overlay
writes `+0x62 = 10000` (`0x800B45A4`).

**The mosquito is species 10**, callback `0x8004A180`, and the Council Chamber holds **one Thumper
and two mosquitoes**. The *throw* is **overlay code** — `LEVEL02/LEVEL.BIN`
`0x800B4330..0x800B43C0` — which sets the aim (`+0x1C`/`+0x24` from the angle table `0x80074970`),
`+0x20 = -3072`, `+0x62 = 10000`, cycles a direction counter at `0x800B4940` mod 4, plays sound 25,
and re-seeds the mosquito's VM IP to `0x80077654` (the flight program). The species callback's
one-shot then fires once (flags bit `0x1000` → `+0x6C = 25`, aim fields doubled) — the visible
"mosquito rises after landing its hit".

> **Actor-array note.** The array base is `0x8009FD80`; **`0x8009FE04` is slot 1**. The
> long-standing "chunk-31 @0x8009FE04" shorthand is that slot's address, not the base.

### The arena — a fixed circle, defined by actor data

There is no arena object, trigger volume, or level-geometry bound. `random_dir_step` `0x8004C278`
recomputes the wander target from a **fixed anchor** each step:
`target = anchor + (sin(random) * s4) >> 9`, with `s4 = [roster_record + 0x14] << 4`.

For Thumper: `roster+0x14` = 25 → `s4` = 400; the sin table `0x80074970` has amplitude 16384; so the
radius is `(16384 × 400) >> 9` = **12,800 units**, centred on the anchor **(4512, 3232)**.

Live-verified: anchor X/Z are never written during the fight; the maximum observed target offset is
**12,800.4** against a predicted **12,800** — the bound is reached, not merely respected. Anchor Y
*is* written, 9 times, by the overlay at `0x800B400C` (`+= 4096`) — that is Thumper's hop, a
separate vertical mechanism.

⚠️ Two constants here were originally assumed and both were wrong: `roster+0x14` reads 0 unless
sampled **mid-fight** (after `mover_init_from_record`), and the sin amplitude is **16384**, not the
usual 4096. Assuming either makes a correct model look refuted.

Evidence: [[EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber]],
`analysis/phase4_d16_f03.json`, `analysis/phase4_d16_f03_oracle.json`,
`analysis/phase4_d16_f03_trace.json`, `analysis/phase4_d16_fight.json`, `analysis/phase4_d16_arena.json`.

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Thumper_boss_fight.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
