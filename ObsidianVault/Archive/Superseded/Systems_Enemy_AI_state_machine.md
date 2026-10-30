---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Enemy AI state machine.md
aliases:
  - "Enemy AI state machine"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Enemy AI state machine.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Enemy_AI_state_machine.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Enemy AI state machine
type: system
updated: 2026-06-22
tags: [system, enemy, ai, behavior, gap-0034]
---

# Enemy AI state machine (behavior model)

> [!warning] Historical synthesis note
> This note contains corrected-but-still-mixed historical AI/address claims. Use it as provenance, not as Canon. For current enemy death/permanence and Gold Berry counter behavior use [[SYS_enemy_death_and_permanence]], [[SYS_contact_objects_and_drops]], and [[MOD_gold_berry_token_drop]]. For static-callgraph limitations use [[WHYPE_static_callgraph_authority]] and [[SYS_re_evidence_policy]].

> [!warning] CORRECTION 2026-07-03 — `0x80095358` is the CAMERA, not "the chaser slot"
> Live motion test (spider_walking.sav): moving Flik, the `0x80095358` struct **lags at ~half his motion, sits ~24k ABOVE him, and its distance GROWS** (26.6k→34.2k) — follow-cam smoothing (`C += (target−C)>>3`), the opposite of homing. Its `+0x20` is a 12-bit angle (≤0xfff) in every save = the camera heading θ. This matches GAP-0028's independent decode of the SAME address/function: **`FUNC_8004DF18` = the camera follow-law core, `0x80095358` = the cam-state struct** ([[Core - Camera and Projection]]). The "chaser homes on Flik at 0x80095358" readings in this note (and the Thumper/Hopper "fight as the chaser AI @0x80095358" model) are **contaminated by this misidentification** — the camera following Flik reads exactly like an enemy homing on him. The REAL regular enemies are the actor structs registered in `damageable_object_ptr_table 0x80090748` (LEVEL01 spider = id 9 @ `0x8009fd80`, etc. — the objects berries hit, homing acquires, and gold destroys, all live-proven in RCG-022/031). Their true per-frame drivers/spawn are now decoded: spawn → [[Enemy spawn architecture]]; **per-enemy AI movement → [[Enemy AI movement programs]]** (all 14 programs disassembled; chase = mover-VM motion-phase gate on flags bit `0x2`, live-falsified; aggro radii = op17 operands). Also corrected: the "chaser spawn areas" (LEVEL.DAT `0x94c/0xa10/0xad4` → `0x8004d698`) are the **scripted SETPIECE/bird flight-path records**, spawning the `0x80090bc0` setpiece actor — `src_re/setpiece_spawn_8004d698.c`. The mover-VM lane (worm/pill @ `0x800a0xxx`, `FUNC_8004C13C`) is unaffected.

> Result for [[Gap Audit|GAP-0034]] — the enemy **behavior** lane (distinct from *relocation* [[Enemy relocation method]]). **Decoded live 2026-06-22** over three isolated-instance passes (native SCUS-94288; `bee.sav`/`fence_wall.sav`/`worm.sav`, then the operator's `bee_1_homing.sav`/`bee_2_homing.sav`, then `spider_walking.sav`/`mosquito.sav`/`pill_bug.sav`; no new save, no repo mutation, instance stopped each time). **Headline:** ABL enemy AI is **simpler than classic behavior trees**. Two kinds of actor: **(A) chasers** (bee/spider/mosquito) share ONE dedicated AI `FUNC_8004DF18` that **homes on Flik** with an **event-gated strike**; **(B) stationary enemies** (worm/pill-beetle) are **mover-VM `FUNC_8004C13C`** actors, anchor-pinned, rotating to face Flik. Contact damage is a **third, global** collision response. Authored *object* motion (non-enemy movers/paths) is the same mover-VM ([[Event and scripting system]], GAP-0033). **Cross-level (2026-06-22, operator fixtures): the two kinds generalize across scenes 3/4/5/6/10 with NO new AI functions; the chaser slot `0x80095358` is reused verbatim. Bosses (unified model): **HOPPER and THUMPER both FIGHT as the chaser AI** `FUNC_8004DF18` @ `0x80095358` — NOT bespoke; the bespoke `FUNC_8004DD98` @ `0x80090bc0` is the **scripted setpiece/finale** actor (the BIRD; Thumper's end-of-fight approach; Hopper's bird-defeat). **Thumper = PARTIAL:** actor + Y-law (target-Y = `Flik.Y−512`, Flik-height-tracking) + defeat-chain (flag `0x80090bee` bit0 → finale `FUNC_8004DA94` → bird) decoded; but **HP / mosquito-throw / berry are in the boss COMBAT OVERLAY** `~0x800b4xxx`/`0x8009c0xx` (OPEN — resume via `transferLog.resolve 0x800b4138`). THUD untested. NB DuckStation movies now record **analog sticks too (v3, 2026-06-26)** — but **can still be truncated**, and **v1/v2 files are digital-only**; verify input span (and, for old files, the control scheme) before trusting a fight replay — re-record analog fights on a current build, or use a save state.**

## Per-enemy map (all five — live-verified)
| Enemy | Actor / slot | Driving fn (writer PCs) | Kind | Verdict |
|---|---|---|---|---|
| **Bee** (flying chaser) | `0x80095358` | `FUNC_8004DF18` (pos-lerp `0x8004e8a4/b8/bc`) | A — chaser AI | fully decoded incl. event-gated strike |
| **Spider** (walking chaser) | `0x80095358` | `FUNC_8004DF18` (same) | A — chaser AI | same fn — covered; pursuit live-confirmed |
| **Mosquito** (flying chaser) | `0x80095358` | `FUNC_8004DF18` (same) | A — chaser AI | same fn — covered; pursuit live-confirmed |
| **Worm** (stationary pop-up) | `0x800a0c74` | `FUNC_8004C13C` (`0x8004cd8c` +0x24 timer) | B — mover-VM | covered (anchor + pop-up timer) |
| **Pill-beetle** (stationary) | `0x800a011c` | `FUNC_8004C13C` (`0x8004cd68…d0b4`/`cd54`) | B — mover-VM | covered (anchor-pinned, rotate-to-face) |

The three chasers each occupy the single hardcoded **active-chaser slot `0x80095358`** in their respective saves (one active chaser at a time). **`0x80095358` ↔ `0x800a0098` reconcile = DEFINITIVE:** the real chasers are `0x80095358`/`FUNC_8004DF18`; `0x800a0098` held static garbage with **0 writes** (vs 18 to `0x80095358`) in a shared window — it was a save-specific Lane-1 mover near Flik in the bee_homing saves, **not** the chaser mechanism. This confirms the original relocation-era finding ([[enemy-bee-is-flik-chaser]]) that spider+mosquito share the bee's slot/writer.

## Cross-level generality (operator fixtures, 2026-06-22 — scenes 3/4/5/6/10)
Nine more enemies across five scenes — **every one is one of the two kinds; NO novel AI function appeared.** The per-level dispatcher just selects *which actors run which of the two shared routines*.
| Enemy | Scene | Actor | Function | Kind |
|---|---|---|---|---|
| earthworm | 3 | `0x8009fe08` | `FUNC_8004C13C` | mover-VM, crawl path (`+0x70`=`0x8013ade4`) |
| wall_worm | 3 | `0x800a0018` | `FUNC_8004C13C` | mover-VM, idle (same prog `0x8013ade4`) |
| grasshopper (+aggro) | 3 | `0x800a1434` | `FUNC_8004C13C` | mover-VM, scripted hop (state→`0xffff` on aggro; prog `0x8014f194`) |
| shell_bug | 4 | `0x80095358` | `FUNC_8004DF18` | chaser (homes on Flik) |
| Redbug | 5 | `0x8009fd80` | `FUNC_8004C13C` | mover-VM, patrol/path |
| canyon_bug (+aggro) | 6 | `0x80095358` | `FUNC_8004DF18` | chaser — locks onto Flik readily |
| **dragonfly** | 6 | `0x80095358` | `FUNC_8004DF18` | chaser, **lock = Flik-MOVEMENT-gated** (RESOLVED 2026-06-22): chases only while Flik moves (`[0x800a6538]≠0`, gate `0x8004e0a0`); "hard to aggro" = stays passive when Flik stands still |
| Horsefly (+aggro) | 10 | `0x800a032c` | `FUNC_8004C13C` | mover-VM, patrol/scripted-path |
| huge_spider | 10 | `0x80095358` | `FUNC_8004DF18` | chaser — the "mini-boss" is just the chaser kind, not special AI |
Notes: the **chaser slot `0x80095358`** is the per-scene chaser global, present (and reused verbatim) in scenes 3/4/5/6/10 as in LEVEL01. Mover-VM enemies live in the `0x800a00xx`–`0x800a14xx` actor region with a non-zero `+0x70` program ptr. Scene 10 runs both kinds at once (Horsefly mover + huge_spider chaser).

## Dispatcher
- **`FUNC_8004EA8C`** (0x8004ea8c–0x8004eccc), called from the per-frame update `0x8004efe0`; chaser AI `jal 0x8004df18` (a0=`0x80095358`) from the updater tail `0x8004ec10`/`0x8004ec54`. **Half-rate** (enemy logic ~4×/8 frames). Hardcoded fixed slots, NOT a table loop; pass-1 saw an active/mode gate at `0x80093054` bit0. Actor registration/render list = table `0x80090748` (stride 0x84), rebuilt by actor-manager `0x8004d37c`/`0x8004d440`.

## Chaser AI — `FUNC_8004DF18` (0x8004df18–0x8004ea84, a0 = slot `0x80095358`) — bee/spider/mosquito
**Actor struct (stride 0x84):** cur pos **+0x00/+0x04/+0x08**; target **+0x0c/+0x10/+0x14**; heading +0x20 (12-bit); **+0x22 state word** = byte +0x22 **sub-mode** · byte **+0x23 strike-duration countdown** · bit **0x0800 = strike-active**; +0x24 patrol counter; +0x70 descriptor ptr. (State word for the slot = `0x8009537a`.)

**Chase = autonomous Flik homing.** Chase block `0x8004e340`–`0x8004e3f4` reads Flik `0x800a6500/04/08`, computes target = Flik ± sine(heading) (sin/cos table `0x80074970`), writes target +0xc/+0x14, then `jal 0x800376a0` (dist); pos integrates by **lerp `cur += (target − cur) >> 3`** (writer `0x8004e8a4/b8/bc`). Spider + mosquito were live-confirmed pursuing here (sub-mode `0x01`, cur lerps toward an advancing Flik-sourced target). Helpers: atan2 `0x80060ae4`, dist `0x800376a0`/`0x8003633c`.

**Chase is GATED by Flik-MOVEMENT (decoded 2026-06-22 via the dragonfly).** The chase block is entered only when global **`[0x800a6538]` ≠ 0** — gate PC **`0x8004e0a0`** (`beq v0,zero,0x8004e0bc`; v0=`[0x800a6538]` loaded at `0x8004e094`): `==0` → WANDER/passive path `0x8004e0bc`; `≠0` (+ next test `0x8004e0b4`: `[0x800a658c]==0`) → CHASE block `0x8004e138`/`0x8004e340` (head toward Flik, arm homing counter `[0x510(gp)]=20`). **`[0x800a6538]` is Flik's speed/motion magnitude** — an (X,Z) vector written every other frame by `0x800494ac` (`sw s3,0x38(s1)`, s1=Flik `0x800a6500`); nonzero only while Flik MOVES, decaying to 0 when he stops. ⇒ the chasers **only pursue a *moving* Flik** (disengaging as his speed decays) — which is why the operator's **Up-hold recipe** reliably provokes pursuit, and why the dragonfly seemed "hard to aggro" (standing still near it does nothing). Proven 3 ways for the dragonfly: static branch trace; natural Up-hold (`[0x800a6538]` 0→931, chase fired 29/30f, then homed); order-correct isolation poke (`[0x800a6538]=400` → chase fired with no input, all else idle). The gate is in the SHARED `FUNC_8004DF18`, so it applies to every chaser using this block (proven for the dragonfly; consistent with the Up-hold provoking pursuit across bee/spider/mosquito/canyon_bug).

**The strike escalation is EVENT-gated, not proximity.** The 0x0800 bit is set in exactly one place — **`0x8004e018`** (`lhu v0,0x22(s2); ori v0,v0,0x0800; sh`) — reachable *only* via the event-gate path: `0x8004dfd4 lhu 0x82488` → `andi 0x0400` → `0x8004dfe0 beq` (fall-through ⇒ aggro). `0x80082488` is a **one-frame event pulse** (cleared every frame). Setting the bit writes **8** into +0x23, decremented each tick (`0x8004df40…0x8004df5c`): `0x0801→…→0x0001`; the aggro TEST `0x8004e064 andi 0x0800` passes only while +0x23 ≥ 8 ⇒ a **~1-tick strike window** → strike controller `0x8004e188` (yaw/pitch slew toward Flik, params **range 1400, speed 24576, squared-range 0x1de840** from mode table `0x80077f40` ×0x10, 6 entries; ±2304 pitch / ±1024 yaw). Range/align consts: `slti 385` strike-facing, `1024`/`2049`/`501`/`351`/`384`. *Captured for the bee* by halting at the gate-load and injecting the pulse (the value the game itself writes); reverted by reload. *Which authored event fires the pulse in real play is the [[Event and scripting system]] (GAP-0033) lane.* For spider/mosquito the strike sub-mode was **not** exercised (Flik out-runs the `>>3` closing lerp before contact) — but it is the **same function**, so it shares the bee's strike path.

## Boss: BIRD — bespoke, DETERMINED (`FUNC_8004DD98`)
The 2nd dedicated fn the bee pass flagged as a "dormant flag-gated mover" (a0=`0x80090bc0`, gate `0x80090bee` bit0) is the **BIRD boss** — dormant in LEVEL01 only because the bird isn't there; active in its canyon/cliff scene (confirmed on-screen: large orange/red bird swooping over a stone structure).
- **Actor `0x80090bc0`** (in actor list `0x80090748`; mirror cache `0x8009ec50`). Struct: pos +0x00, target +0x14, heading +0x20 (banks per frame), **state +0x22**, nothing past +0x28 (**no VM program at +0x70**).
- **Fn `FUNC_8004DD98`** (0x8004dd98–0x8004df10; writers `0x8004de08`/`0x8004de1c`). **Does NOT read Flik `0x800a6500`** (full-body disasm verified).
- **Behavior:** a **scripted target-interpolation (lerp) setpiece**, not a Flik-homer — each frame `pos += (target − pos) >> 3/5` toward the +0x14 target. Observed a clean **swoop arc** (descends Y −85633→−66689, approaches Flik 137k→~55k, then pulls away) with a **state-field phase transition +0x22: 1 → 0** mid-swoop. **No HP field** observed (consistent with an invulnerable scripted setpiece). Distinct bespoke AI — does NOT share the regular chaser/mover-VM routines.
- **`FUNC_8004DD98` @ `0x80090bc0` is the SHARED scripted-finale/setpiece actor.** Besides the bird, it also drives **Thumper's end-of-fight approach** (spawned at the kill by `FUNC_8004D9E8`, pf2536) and is the **bird-eats-Hopper defeat** cinematic. So the model is clean: **bosses FIGHT as the chaser AI (`FUNC_8004DF18` @ `0x80095358`)**, and **`FUNC_8004DD98` runs the scripted finale/setpiece.**

## Boss: HOPPER (final boss) — PARTIAL (fight decoded; defeat shelved)
Decoded from the operator's `hopper_boss.movie2` (the run where they beat Hopper), **Phase 1 only** (the faithful portion), on an isolated instance 2026-06-22. **Hopper is NOT a bespoke boss — he REUSES the chaser AI.**
- **Actor = chaser slot `0x80095358`, driver `FUNC_8004DF18`** (the same code as bee/spider/mosquito), called from `ra=0x8004ec18`. He **homes on Flik** (tracked ~17k–38k units away, moving with him). The bespoke bird code `FUNC_8004DD98` does NOT fire during the fight; mover-VM `FUNC_8004C13C` drives *other* arena objects (`0x800a0224`, `0x800a032c`), not Hopper.
- **Struct** (at `0x80095358`): +0x00/04/08 X/Y/Z · +0x0c/10/14 vel/target · +0x18/1a heading · +0x20/22 state/timer. (In this boss scene Flik pos `0x800a6500` is **signed fixed-point ints, not floats**; `0x800a65a0` lives = 0, so fight HP is tracked elsewhere.)
- **Multi-phase**, driven by the global mode flag **`0x80082488`** (the same flag whose bit `0x0400` gates the chaser strike) — written by the scene/phase manager `0x800512d4`/`0x8005131c`; it steps `0x8000 → 0x0010 → 0x0030 → 0x4010 → 0x0060 …` through the fight, and the driver branches on bits `0x40`/`0x400`/`0x10`. Phases = ground chase → flying → tracking, matching the operator's "hit him once per area."
- **No HP bar** — Hopper's struct has no whittling counter. **Defeat is scripted phase/trigger progression, not HP-depletion**, culminating in the **bird-eats-Hopper cinematic** at the very end = the bird setpiece `FUNC_8004DD98` ⇒ **the BIRD boss (above) IS Hopper's defeat setpiece.**
- **SHELVED residual (the defeat):** the exact hit→phase-advance trigger + the bird-eats-Hopper sequence are not yet decoded — the analog-steered Hopper fight couldn't be replayed to the end (digital-only movie limitation below, **now lifted — see callout**). Either re-record the fight on a **v3 (analog) movie** or use a **save state at the bird sequence** (a cutscene plays input-free, so save → advanceFrames decodes it).

### ⚠️ Tooling limitation — DuckStation movies recorded DIGITAL buttons only (no analog stick) — ✅ FIXED 2026-06-26
> [!success] **RESOLVED 2026-06-26: movies now record analog sticks too (format v3).** Each frame stores all 16 buttons **and** the analog axes (`lx`/`ly`/`rx`/`ry`), so an **analog-steered boss fight re-recorded on a v3 movie now replays faithfully.** The findings below describe the *old* digital-only behavior that shelved the Hopper defeat — that blocker is gone: **re-record `hopper_boss` on a current build** (or keep using a save state) to drive the analog fight to the bird sequence. (Older v1/v2 recordings are still digital-only — re-record, don't expect old files to gain analog.)

`hopper_boss.movie2` (14,332 frames) replayed FAITHFULLY for only ~3,745 frames, then **Flik DIED** (game-over → level reload) because the **analog-stick steering used in the boss fight was never recorded** — the v1/v2 movie format captured only the 16 digital buttons (controller is an AnalogController). The operator's movie-desync **fix worked** (`reproducible:true`, clean start-state load, no spurious title), but **no playback fix could recover un-recorded analog input** — hence the v3 format fix above. (A prior run misread the post-death reload as a "title screen mid-movie"; it was the game-over + level reload, not the front-end.)

**Second failure mode — TRUNCATED recordings (still applies).** The original `thumper_boss.movie` (1955f) had its **last digital input at pf1477**, *before* the boss even activated (pf1489) — the fight had zero recorded input, so only the scripted entrance played, mis-leading 3 passes into "Thumper is just a cutscene." The fix: the operator re-recorded the **complete** fight (`thumper_boss_2.movie`, 3092f, input through ~pf2528) and it decoded fine. **Always verify a movie's input span** (last non-neutral frame vs total) before trusting a replay — truncation is independent of the analog fix. **Rule for boss work: verify input span first; for v1/v2 files also verify the control scheme (analog won't be present); prefer a save state when in doubt.**

## Boss: THUMPER — PARTIAL (actor + Y-law + defeat-chain decoded; combat bookkeeping is overlay-resident = OPEN)
Worked from the operator's COMPLETE recording **`thumper_boss_2.movie`** (3092 frames; D-pad, digital — replays faithfully). **Operator frame anchors** (absolute movie-frame; `pf = abs − initial_frame 57593`; `debugger.status.frame` = absolute): **58494** level fade-in (pf901) · **~58984** Thumper throws a mosquito · **~59016** Flik throws the berry (1st) · **~59025** first damage · **~59373** a hit → airborne · **60130** defeat FSM flips (pf2537). *(The earlier `thumper_boss.movie` was TRUNCATED — input ended pf1477, before the boss — which mis-led 3 prior passes into "shelved/cutscene-only.")*

**SOLID:**
- **Actor `0x80095358` = Thumper** (disasm-confirmed: manager `FUNC_8004EA8C` computes `0x80090000+21336=0x80095358` → driver `FUNC_8004DF18` every frame; `gpu.pickObject` confirms boss/Flik/HP-bar/berry are distinct drawables — NB this fork's pickObject returns the transformed-vertex buffer, not the actor RAM addr, so the disasm is the definitive link). Active from fight start (pf~888) ⇒ it is Thumper, not the thrown mosquito. Same chaser fn as Hopper + regular chasers (homes on Flik); not a bespoke boss-AI.
- **Struct `0x80095358`:** cur X/Y/Z +0x00/04/08 (writers `0x8004e8a4/b8/bc`); target +0x0c/10/14; anim up-counter +0x24 (+2/frame @`0x8004e738`); **+0x2a = a bob/Y-accumulator** (ramps 0↔160; +32 @`0x8004e3fc` cap 1024 / −32 @`0x8004e42c` floor 0) — **NOT HP** (prior "HP candidate" debunked). **No HP field in the boss struct.**
- **Y-law (CORRECTED — supersedes the rigid "3-phase" model):** target-Y +0x10 is set at `0x8004e6cc–0x8004e6e8` = **`clamp(Flik.Y[0x800a6504] − 512)`** plus the +0x2a bob. So Thumper **tracks Flik's height** — "lowers Y after each hit" is the observed *effect* of Flik-height-tracking + the hover band dropping across the fight, NOT a per-hit Y counter. (Y range seen: ~23k ground → 61004 air-peak → ~40k late.)
- **Defeat CHAIN — traced:** final hit → finale-init `FUNC_8004DA94` sets defeat flag **`0x80090bee` bit0 = 1** + FSM **`0x80090bec = 2`** (observed 0→2 at abs frame 60130 / pf2537) → manager `FUNC_8004EA8C` tests `(*0x80090bee)&1` (PC `0x8004ebfc/ec00`) → defeat branch spawns the **bird finale** `jal 0x8004dd98` (`FUNC_8004DD98` @ end-actor `0x80090bc0`) at `0x8004ec5c`.

**OPEN — all three live in the boss COMBAT OVERLAY (`~0x800b4xxx` / `0x8009c0xx`), NOT the EXE or the boss struct** (this is *why* HP eluded the EXE/struct searches — `FUNC_8004DA94` is called from overlay PCs **`0x800b4138`** + **`0x8009c024`**):
1. **HP field + per-hit delta + N-hits-to-defeat** — the bar visibly depletes (5 red segments; `gpu.readVramRect` red-pixel count is a working proxy), but the counter is in the overlay, not isolated.
2. **Mosquito-throw spawn** (the ~58984 throw) — fn/actor not pinned; the actor-list model `0x80090748` (48×0x84) does NOT hold in this fight (`0x80095358` isn't 0x84-aligned to it). A per-hit impact struct appears at `0x800a6880` (writers `0x80064870/4908/417c`).
3. **Berry projectile + its collision→HP-write link** (Flik's ~59016 throw).

**NEXT STEP (named boundary — resume here):** `transferLog.resolve 0x800b4138` → identify which overlay loads there + its base, then non-halting write-watch *inside* that overlay across the hits → the HP-decrement store (field + delta), the hits-to-defeat count, and almost certainly the throw + berry (same overlay). Ties to [[Gap Audit|GAP-0020]] (overlays). Resume anchors: actor `0x80095358` (driver `FUNC_8004DF18`, manager `FUNC_8004EA8C`), defeat flag `0x80090bee` bit0, FSM `0x80090bec`, finale-init `FUNC_8004DA94` (overlay callers `0x800b4138`/`0x8009c024`), end-actor `0x80090bc0`/`FUNC_8004DD98`, defeat @ abs frame 60130.

## Boss: THUD — UNTESTED
`thud_boss_movie.movie` has not been re-tested on the current (18:04) binary — the only prior look was a pre-fix desync. Given Thumper, expect the same shape (a chaser-AI fight needing a COMPLETE, non-truncated recording or a save). Re-run it the same way when prioritized: replay → track the chaser slot `0x80095358` + boss Y → map phases → pin defeat/throw.

## Stationary enemies (worm, pill-beetle) = mover-VM `FUNC_8004C13C`
Anchor-backed, **no translation**; rotate/aim to face Flik. Worm (`0x800a0c74`, anchor `0x800a0c9c`) also pops up on a timer (writes +0x24 at `0x8004cd8c`, half-rate, distance-to-anchor). Pill-beetle (`0x800a011c`, anchor `0x800a0144`) stayed exactly at anchor `(-29152,-93184,214816)` across all Flik strafing while its facing vector (+0x1c/+0x24) tracked Flik's bearing. Writer family `0x8004cd68/ce3c/ce6c/ce98/d0b4/cd54`, a0=`0x800a011c`. (This is the same mover-VM that runs authored *object* paths via op9 — [[FUNC_8004C13C]].)

## Contact damage = global collision
On contact (closest hostile at dXZ ≈ 1024–2400) the response writer **`0x80036cec`** (caller `0x80036c8c`) sets Flik pos +0x0/4/8/c → **Flik knocked back ~3070 u** (live-proven). The AI fns write no Flik fields. *Bounded residual:* a discrete HP/health *counter* decrement (separate from the knockback) was not isolated within budget.

## Enemy death / despawn + gold-berry permanence (RCG-022, 2026-07-03)
Decoded live → full note [[Enemy death and permanence]] + `src_re/enemy_death_permanence.c`. A berry hit is applied inside **`contact_vs_actor_handler 0x80058af8`** (tail `0x8005929c`): sets enemy `+0x6e=999` (death-anim trigger), ORs recoil bits `0x880`/clears alive-bit `0x2` in `+0x5c`, and **swaps `+0x70` (the mover-VM program ptr) to the hit/death program `[0x80077b2c]`** — then runs `enemy_update_deathanim 0x800498ac`. **The enemy does NOT die from the `-2` HP byte** (`enemy_hp_table 0x80089938`, floors at 33). **Permanence** = a per-level quota `G_ENEMIES_REMAINING 0x800a658e`: the destroy block (gated `s7>=2`, gate `beq …,11` @`0x800591f8`) decrements it, spawns destroy FX + death pickup, and zeroes the enemy id; at 0 it fires `all_enemies_defeated_event 0x8005182c`. **Only GOLD is permanent** (live 3/3 on spider + mosquito, 21→20 per kill); **mega/homing/blue KO the enemy but leave the quota untouched** (temporary — corrects the old "mega permanent" belief). 2nd lane `+0x27==6` LIKELY the yellow Mine Plant (untraced).

## Residuals (bounded / named — not open gaps)
1. **Flik HP-counter field at contact** — knockback writer found (`0x80036cec`); the discrete HP decrement not isolated. One focused write-watch would close it.
2. **Which authored event opcode** fires the chaser strike pulse (`0x80082488 & 0x0400`) in natural play — the [[Event and scripting system]] (GAP-0033) lane.
3. **Spider/mosquito terminal strike** — same fn as the bee so it shares the path, but the `0x0800` dive wasn't exercised (Flik out-runs the lerp). *Nice-to-have confirmation, not a decode gap.* Precise capture if ever wanted: a spider/mosquito save with Flik **cornered against geometry at contact range** so the chaser closes inside strike distance.
4. **`PATH*.BIN` dead-vs-live** (separate GAP-0034 sub-part) — reference-live / runtime-dead; decider = exec-watch loader `0x8006f6a0` across a cold boot into numbered stages LEVEL02–05/12/13 (`tools/trace_warp_landing.py`).
5. ~~**THUMPER combat bookkeeping**~~ — **✅ SOLVED 2026-07-03** → [[Thumper boss fight]]: Thumper = a regular chunk-31 actor **id 16 @`0x8009fe04`** (NOT `0x80095358` = the camera); HP = `+0x6e`, 50 → −2/berry-hit via the RESIDENT `berry_tough_damage_dispatch 0x8005905c` (per-berry class byte, NOT an overlay — that claim refuted); **defeat = HP ≤ 20 (poke-proven) = 15 hits** → `0x80090bee`=2 → the decoded finale chain. Mosquito = its own persistent id-10 actor (cb `0x8004a180`). **THUD** = untested (same recipe; needs a complete recording or in-fight save).
7. **HOPPER defeat** — SHELVED (fight decoded above; he = chaser AI, multi-phase, no HP). The hit→phase trigger + the bird-eats-Hopper defeat need either a **v3 (analog) movie re-recording of the fight** (movies record analog sticks as of 2026-06-26, lifting the old digital-only blocker) or a **save state at the bird sequence**. The bird setpiece `FUNC_8004DD98` is already decoded; this would confirm it in its real Hopper context.
6. ~~Dragonfly aggro-gate~~ — **RESOLVED 2026-06-22**: the chase is Flik-movement-gated (`[0x800a6538]≠0`, gate `0x8004e0a0`) — see the Chaser AI section above. Not a dragonfly-specific quirk; a shared chaser gate.

## Evidence / reproduction
Isolated `/tmp/duckstation-debugger-gap0034[b/c]`, port 23460, native SCUS-94288; execTrace on the AI fns + accessLog write-watch on +0x22/+0x23/+0x2c; controlled event-gate inject to trace the bee strike path. **Operator input recipe to drive a chaser into pursuit:** scripted `pressButton` **Up for ~30 frames (~0.5 s)** to close distance, then trace (no far-teleport — crash risk). Instances stopped, disc + saves untouched, nothing committed.

## Related
[[Enemy relocation method]] · [[Event and scripting system]] / [[FUNC_8004C13C]] · [[Gameplay - Events and Triggers]] · [[Gap Audit|GAP-0034]] · [[Gameplay - Initial Player Spawn]] (Flik `0x800a6500`)
