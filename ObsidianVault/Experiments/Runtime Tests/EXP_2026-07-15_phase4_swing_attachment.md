---
kind: experiment
id: EXP_2026-07-15_phase4_swing_attachment
name: Phase 4 swing attachment campaign
status: complete
date: 2026-07-15
confidence: confirmed
---

# Phase 4 swing attachment campaign

## Question

What owns pristine swing acquisition, pendulum motion, release, camera/actor
coupling, pool capacity, applicability, and lifecycle?

## Setup and identity

- Generator `tools/phase4_swinging.py`, SHA-256
  `1b38dbdd5240e2c5e5c6bd99a0affddc45d617de4bf47c4ebcf3afb897c4d8cd`.
- Evidence `analysis/phase4_swinging.json`, SHA-256
  `80aa3d28d1bd75e5cba6094870e1c7b2fdd4a09c8c707cd0db799bd20bc398fa`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Strict-pristine `on_swing.sav` SHA-256
  `7c8570ff595909324aa4f2c0ba213b6f2c318b55c544d7aa581afdbeee3cc7c2`;
  `in_front_of_swing.sav` SHA-256
  `50cf0d173e6e1f70ab1d41042d6f99c8fe4bacae1a0efbe7e4be437de1f53b1a`.
- Pinned from-boot LEVEL01 movie and all 19 gameplay anchors are centrally
  declared in `analysis/phase0_2_external_fixture_set.json`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  release binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method RPC manifest.

The retained run used fresh absolute config
`/tmp/abl-phase4-i10-swing-retained-26423`, dedicated loopback port 26423,
and an ephemeral token. It verified mounted media, inspected every save before
load, and stopped only PID 483370 owned by that config. Regeneration requires
fresh isolation values:

`python3 tools/phase4_swinging.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Diagnosis and observations

Static analysis corrected `0x800A658C` from a weak active-actor-count label to
a 1-based swing attachment index. Acquisition writer `0x80041CF8`, record claim
writer `0x80041D00`, detach clear `0x80041AB8`, camera read `0x8004E0AC`, and
actor-anchor helper `0x80042DCC` all use that same selector. The exact
acquisition/pendulum body hash is
`742395b7c8a0f04595bb6492d77bdd90d393708fd8be448aacf57282ee7187d2`.

Natural controls reloaded the same approach state for 120 emulator frames.
No input, Cross-only, and Up-only ended at attachment index 0. Up+Cross ended
at index/state/grounded/animation 2/5/0/4. The attached fixture retained index
2 under idle and produced a nonzero Y pendulum span.

The pool census loaded all 19 strict-pristine gameplay anchors. Only Stage 1,
The Tree, and Bonus 2 had active records. Bonus 2 reproduced Stage 1's three
anchors exactly. Ten paused `callFunction` controls reloaded before every trial,
made only the target record available, placed player/camera at its first
selectable node, and selected each of three Stage-1 and seven Tree records with
the exact slot+1 index.

An attributed 24-frame trace observed player velocity writers
`0x800423C8/DC/F0` without truncation. A separate 13-sample sequence showed
record s16 velocities equal to player s32 velocities every time. Fresh Cross
attributed the -30 claim write to `0x80041AB4` and index clear to `0x80041AB8`;
the later pool updater moved the claim toward zero. An idle control stayed
attached.

Pause froze ten player fields and all eight records. Clearing only the index
changed the camera trajectory while both branches executed its exact reader.
Scene anchor transitions reproduced three active, zero, seven active, zero and
indices 2,0,0,0. From the naturally attached fixture, Flik was placed at a
live actor's current contact center with health zero. Native contact changed
health to -1, animation to 15, and attachment 2 to 0; same-scene respawn
restored health 4, decremented lives, selected state 0, and remained detached.

## Failed hypotheses and corrections

- **Swinging is a The Tree-only record family:** false. Stage 1 owns the
  three-record layout and Bonus 2 reuses it; The Tree owns a seven-record layout.
- **`0x800A658C` is an active actor count:** false. It is the 1-based selected
  swing record. This also corrects the purpose of `0x80042DCC`.
- **Fresh Cross release selects state 2:** false for the retained fixture. The
  directly observed release tuple is state 1, animation 3, index 0.
- **The first selectable node begins at record `+0x44`:** false. The
  acquisition loop's first candidate resolves to `+0x54`; `+0x44` is outside
  that first loop address after its base adjustment.
- **Injecting an attachment index after fatal contact proves respawn reset:**
  false. The synthetic index survived respawn, showing it was outside the
  native ownership path. The retained test begins naturally attached and
  observes native damage detach before respawn.
- **A direct proximity `callFunction` result can be continued as a native death
  timeline:** unsafe. It proved the damage/detach result but continuing that
  synthetic call left execution at an invalid low PC. The retained lifecycle
  uses native frame advancement at an exact live-actor contact center.
- **The raw level-2 actor-record base is a stage-1 contact oracle:** false. The
  retained Stage-1 actor is selected through the compact live pointer table.

Static census, from-boot pool initialization, natural controls, full active-slot
coverage, pendulum and release attribution, 19-anchor breadth, camera, pause,
damage, respawn, and transition reset jointly confirm A16. No copyrighted
fixture, BIOS, capture, credential, token, save, movie, or disc image is added.
Canonical result: [[SYS_swing_attachment_controller]].
