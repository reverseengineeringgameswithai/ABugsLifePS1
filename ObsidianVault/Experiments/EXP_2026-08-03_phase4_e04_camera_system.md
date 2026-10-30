---
kind: experiment
id: EXP_2026-08-03_phase4_e04_camera_system
status: complete
source_state: original_game
system: [SYS_camera]
row: E04_camera_system
---

# Phase 4 E04: camera system — struct survey and the mode-word negative

## Question

E04's own named next: "Enumerate camera-mode word values across normal/boss/telescope
contexts." Executed — with an honest negative as the headline result.

## Committed base, assembled

Producer `camera_follow_update 0x8004DF18` (calls the movement integrator, `atan2_heading`,
and `camera_region_query 0x800376A0` — the "regions" half). Struct `0x80095358`: pos triple
`+0x00`, target triple `+0x0C`; **authority already proven** (phase3_camera_record.json):
both triples are derived output — pokes decay; the measured follow law closes ~0.15 of the
remaining gap per frame. The world→view matrix (with its baked ~1.6× horizontal zoom) is
mirrored per-frame at `0x80090FB0`/`0x8009E290`. The camera's tracked state also feeds the
enemy-admission anchor `0x8009EC50` — camera state gates which actors are live.

## The survey (six contexts + one dynamic trace)

Read `0x80095358..+0x60` across normal / Cliffside / Bug Bar / Battle Arena / Training-end /
frontend, then traced 80 frames dynamically:

| Field | Observation |
|---|---|
| `+0x1A` | live 12-bit angle; equals `+0x20` in steady state, moves independently mid-transition (59→36 while `+0x20` held 16) |
| `+0x1E` | the constant **900** in every gameplay scene, 0 in frontend |
| `+0x20` | the archived "12-bit theta" claim confirmed in domain terms; static in the trace |
| `+0x22` | camera-active flag (1 gameplay / 0 frontend) |
| `+0x24` | per-scene tuning that **ramps** (14→32) and holds; 20 in Cliffside |
| `+0x18`, `+0x2A` | angle-domain / per-scene values, roles unassigned |

**The negative that answers the row's next**: no field behaves as a mode *enum* across
contexts. Camera modes are separate producers/flags — the active flag, the external
special-view global, and scripted camera code paths — not a mode variable in the struct.

**A dual-attribution flag worth recording**: `0x800824DC` is committed as BOTH
`G_TELESCOPE_ACTIVE` (pickup handlers) and the setpiece/bird spawn trigger (spawn
architecture, values −1/−2). The value sets are disjoint — consistent with one shared
multi-state "special view / scripted event" global. Flagged as an inference.

## L1/R1: the manual camera controls (2026-08-03, operator hint)

Operator: *"i think there should be some camera nodes, try DuckStation and holding L1 then
R1."* Held each on `level01.sav` with per-6-frame struct sampling — three survey conclusions
**explicitly corrected**:

- **`+0x18` is the live smoothed BOOM/ELEVATION value**, not theta-rate: L1 drives it down
  (8→3, camera pulls low), R1 up (8→122, overhead view), release decays back. The survey's
  cross-context values were per-scene *resting* boom values.
- **`+0x1E` = camera DISTANCE, not a constant**: 900 standard, **580** in the L1+R1
  combined close-up mode.
- **`+0x22`'s HIGH byte is a camera submode code** — `0x0A01` while L1+R1 held (the
  close-up behind-Flik view, screenshot-confirmed). **The mode field exists after all**; the
  survey's negative was correct only for passive contexts, none of which were in a manual
  mode. Revised openly, not silently.

Thetas never moved under L1/R1 — these are boom/zoom controls, not rotation. The R1 raised
view shows a camera-with-padlock HUD icon (a camera-lock indicator). The asymptotic targets
(boom ~3 / rest 8 / ~122; distance 900/580) behave as discrete preset **camera nodes** with
smooth interpolation — matching the operator's framing; whether they're authored per-scene
records or hardcoded presets is untraced.

## Operator facts, confirmed (2026-08-03, second addendum)

Three more facts from the operator, all now banked:

- **"No rotational cameras exist"** — closes the rotation-input hunt for good. Camera
  heading is follow-driven only; the theta-pair question reduces to follow-behavior
  analysis.
- **L1 + left/right rotates Flik on his axis** — previously documented NOWHERE (grep:
  zero hits). Live-confirmed: position frozen exactly for 60 frames while heading rotates
  ~−15/frame and the camera orbits behind him; two more submode codes (`0x0A`, `0x0B`)
  surfaced in `+0x22`'s high byte during the turn. Cross-banked to A01_move_run as a
  player-movement addendum.
- **R1 = camera lock**: with R1 *held* after the zoom-out, the camera moves only ~9% of
  Flik's displacement in the first 15 frames (vs ~90% lockstep unlocked) — it holds
  position while Flik moves around it, with a leash that drags it along on long runs
  (boom decays as Flik gets far; holds >122 reach boom 172). The padlock HUD icon is the
  lock indicator. Release resumes normal follow immediately.

## Still open

The `+0x1A`/`+0x20` roles under follow (no manual rotation exists); node authorship
(authored records vs hardcoded); the `+0x18`/`+0x1E`/`+0x22`-high writers; `+0x2A`; the
lock's leash distance; submode codes beyond `0x0A`/`0x0B`; boom collision / LOS; live
telescope-view behavior; cutscene/setpiece camera producers.

## Evidence

`analysis/phase4_e04_camera_system.json` (full citations inside); six saves read-only + one
dynamic trace, isolated instance port 23655, no pokes.

## 2026-08-04 bounded-exhaustion addendum

**Disposition:** `substantiated partial / bounded-exhausted`

The original E04 open list is now superseded by retained-capsule evidence, the A17 manual-camera closure, the C14 telescope closure, the cinematic-camera canon, and a fresh pristine-ASM census written in C. No new DuckStation run or Interpreter movie was required because no named evidence domain remained that a replay could uniquely supply.

### Capsule-first gate

The retained A10/A11 capsule at `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/a10-a11-v2-20260719/Phase_Helpers__carry_handstand` was accepted before static work:

- manifest SHA-256: `5188a58af0c5c347b5f2a7685e12748631686823edf78ad15c2649d716f02a26`
- complete: `true`
- truncated: `false`
- 1,359 records, movie frames 0 through 1,358
- independent RAM/VRAM/SPU/register/full-state control fingerprint: exact
- offline C-query binary SHA-256: `4f7b8757441e914e2fe1fc0dc752124fe41c11ba31f9a33670f1c20ca6ad9908`
- offline query output SHA-256: `047606f5b86612bfcb7d21a3064cb8b1fc1e3ff15d49d3bae847476b2ec9b68e`

The query confirms that normal derived-camera updates continue through the handstand interval. It exposes no separate camera latch or hidden camera source.

### Exact normal-camera field roles

The camera structure remains rooted at `0x80095358`.

| Field | Closed role |
|---|---|
| `+0x18` | Final view pitch. It shortest-arc quarter-steps toward the vertical `atan2` result. |
| `+0x1A` | Final view yaw. It shortest-arc quarter-steps toward the horizontal target-minus-position `atan2` result. |
| `+0x1E` | Signed boom distance. |
| `+0x20` | Follow/orbit heading used to place the target around Flik. R1 suppresses its angular step. |
| `+0x22` low | Profile/control byte. |
| `+0x22` high | Signed decrementing countdown/control byte. This supersedes the earlier tentative `0x0A/0x0B submode` interpretation. |
| `+0x24` | Player-state-gated look/lead amplitude. It changes by two inside `[0,32]` and contributes sine/cosine offsets using `+0x1A`. |
| `+0x2A` | Twelve-bit terrain/region clearance pitch accumulator. Region-query results move it by `0x20` toward `0x400` or toward zero and can force boom-distance contraction. |

This resolves the old `+0x1A/+0x20`, `+0x22-high`, `+0x24`, and `+0x2A` gaps without assigning a speculative gameplay name to the player `+0x38` gate.

### Resident profile table

The pristine executable contains exactly six valid normal-camera entries at `0x80077F40`. They are hardcoded resident presets, not per-level authored camera nodes.

| Index | Normal distance | Alternate distance | Leash squared | Vertical offset |
|---:|---:|---:|---:|---:|
| 0 | 400 | 700 | 1,000,000 | 12,288 |
| 1 | 900 | 1,200 | 1,960,000 | 12,288 |
| 2 | 1,400 | 1,400 | 4,000,000 | 12,288 |
| 3 | 1,400 | 1,400 | 4,000,000 | 24,576 |
| 4 | 900 | 1,200 | 1,960,000 | 24,576 |
| 5 | 400 | 700 | 1,000,000 | 24,576 |

The R1 branch uses distance `1,400`, vertical offset `0x6000`, leash-squared threshold `1,960,000`, and world-radius bound `44,800`. A17 already pins L1 priority, release behavior, region query, and candidate rejection.

### Normal versus setpiece producer boundary

The C census pins:

- normal-follow calls at `0x8004EC10` and `0x8004EC54`
- setpiece update call at `0x8004EC5C`
- telescope start `0x8004D9E8`, with its sole resident caller at `0x8004D730`
- polar setpiece start `0x8004DA94`, with 13 direct overlay callers across the scanned 20 overlay BINs
- selector `0x8004EA8C`, whose phases are `1`, `2`, `3`, and `4`
- selector flags bit 1 chooses the setpiece source; otherwise the normal-follow source is copied to `0x8009EC50`
- flags bit 2 holds suppression bit `0x800A6590 & 4`

C14 supplies the returning telescope case and its complete shared-state lifecycle. Existing cinematic-camera evidence supplies both returning control and a level-ending Council Chamber case. E04 therefore does not require another movie to establish the source handoff.

### Static evidence

The reusable scanner is `tools/phase4_e04_static_closure.c`.

- investigation C source SHA-256: `8e31775d449ad5bfe923b6ed6cc864a6686c6a18fce128e98c82c086f7679f20`
- compiled analyzer SHA-256: `5d48b8fbb5e1561dcd06e473f93e0eb39e451be6261f87f4e495346752beef57`
- analyzer output SHA-256: `5faf2ea46ae01884fa3cbbbcc402aa55bfe43489c46d459de2609a62386fd919`
- pristine executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- overlays scanned: 20

The closure record is `analysis/phase4_e04_bounded_exhaustion.json`.

### Declared bounds

The following are deliberately left outside E04 closure:

- an artistic/content catalog of every overlay cinematic shot
- a semantic gameplay name for player `+0x38`, whose camera-side transfer function is already exact
- a visual catalog of every possible terrain and line-of-sight arrangement
- pointer-derived aliases outside the completed direct-address census

Those are low-return naming or content-enumeration tasks. No Phase 4 mechanism remains open for trigger, field role, input rule, profile parameter, normal/setpiece selection, terrain response, or transition handling. E04 is therefore safe to leave as substantiated partial and bounded-exhausted.
