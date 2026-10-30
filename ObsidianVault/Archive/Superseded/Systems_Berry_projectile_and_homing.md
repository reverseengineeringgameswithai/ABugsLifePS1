---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Berry projectile and homing.md
aliases:
  - "Berry projectile and homing"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Berry projectile and homing.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Berry_projectile_and_homing.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Berry projectile and homing
type: system
updated: 2026-07-07
tags: [system, berry, projectile, homing, combat, gameplay, modding]
---

# Berry projectile + homing (thrown-berry mechanic)

> [!warning] Canon split
> This is a detailed legacy system note. For canonical berry projectile/render decisions use [[SYS_berry_projectile_and_homing]] and [[SYS_berry_pickup_render_descriptors]]. For permanence/counter decisions use [[SYS_enemy_death_and_permanence]] and [[SYS_hud_counters]]. For mods use [[MOD_blackberry_net_new_berry]] and [[MOD_gold_berry_token_drop]]. Do not promote old "mega permanent" interpretations; the resolved wrong hypothesis is [[WHYPE_mega_permanent]].

> Live RE (2026-06-23, isolated DuckStation + operator berry save states `red/gold/blueberry/homing/mega_homing_berry.sav`). **Locking/flight mechanism CONFIRMED; the per-type parameter table is LOCATED, mapping in progress.** Throw input = **Square**.

## The projectile = a contact-array object (RESIDENT, not the boss overlay)
The thrown berry is one entry in the **contact-object array `0x800b0d18`** (64 slots × `0x38` bytes), allocated round-robin via the cursor `0x8008234c`. This **corrects the prior GAP-0034 assumption** that the berry lives in the boss combat overlay — the *throw projectile* is resident code. Found by an A/B memory diff (Square vs no-Square, phase-matched) → the projectile footprint clustered at `0x800b1xxx`; `accessLog` write-watch on its position → the updater PCs.

## Per-frame updater — [[FUNC_8005A308]] (`0x8005a308`)
Walks the active contact objects each frame. For the berry:
1. **Active gate** — record `+0` (lifetime) > 0, else the slot is inactive.
2. **Homing gate** — record flag byte `+0x33`, **bit `0x8`**: clear → straight flight; set → lock-on.
3. **Lock-on (the "tracking")** — with a locked target at **`record+0x10`** (a POINTER to the target enemy struct; `-1` = none):
   - reads the target's **LIVE** world position (from its transform/bone table `enemy+0x74 + enemy+0x44*16`);
   - `atan2(target − berry)` via **`0x80060ae4`** ([[atan2_heading]]) → the desired bearing;
   - **turn the current heading toward it by `(angular_error & 0xfff) >> 2` per frame** — a *rate-limited* seek, so the berry curves in rather than snapping;
   - **disengages** (expires the berry, `record+0x22=1`) when the target is already hit (`enemy+0x6e≠0` or `+0x5c & 0x880`).
   - No locked target → aim off Flik's position (`0x800a6500` / `0x800a6508`).

**TARGET ACQUISITION — SOLVED (RCG-031, 2026-07-03)** → `src_re/berry_homing.c`. The target at `record+0x10` is set at projectile-spawn by **`FUNC_8005743C` (`0x8005743c`)**: it scans the **damageable-object table `0x80090748`**, keeps enemies with `+0x5c & 0x1` set (targetable) and `+0x5c & 0xa0` clear (not already-hit/dead), and picks the **NEAREST by XZ distance²** `((berryX−enemyX)>>5)² + ((berryZ−enemyZ)>>5)²` (Y ignored). That nearest enemy pointer is passed as the projectile's target (spawner t1 → `record+0x10`, which is therefore target pointer for homing projectiles rather than vertical velocity). Straight berries never acquire. Live-traced (homing throw → target = id 9 @`0x8009fd80`, the nearest damageable enemy). This resolves the earlier "with a locked target / aim off Flik" ambiguity.
4. **Movement** — heading → velocity via the **sin table `0x80074970`** (`sin(h)`, `cos(h)=sin(h+1024)`, `>>3` scale); `position += velocity`.
5. **Lifetime + particles** — record `+4` timer counts down → despawn; a cyclic counter drives the particle/animation frame.

⇒ the five berries split on the **homing flag**: **red / blue(super) / gold → flag clear (straight)**; **homing / mega-homing → flag set (lock-on)**. The *locking code is identical*; the berry *type* just toggles the flag (per-type speed/turn-rate is suspected but **not yet pinned to a table field** — see the param-table caveat below).

## Spawn / init — `contact_object_spawn` (`0x8005a0f0`)
Allocates the next free contact slot (cursor `0x8008234c`, wrap 64), then indexes a **per-type parameter table `0x8007941c` (stride `0x14`)** by the object type and copies `table[type] + 0x10` → the record's flag byte `+0x33` (the source of the homing bit). The caller (the throw handler) passes the berry's initial pos/vel/heading + the type.

## Editing implications (data vs C)
- **Per-type knobs** are in the `0x8007941c` table → **data edits** once the per-type rows are mapped. Confirmed: homing on/off (`+0x10` bit `0x8` — e.g. "make red berries home"), model/family (`+4`), spawn-timer chain (`+2`). **Speed and damage are NOT yet pinned to a field** (`+0xe` / `+8` are unverified candidates).
- **The seek *feel*** (turn rate `>>2`, the atan2 lock) is shared code → a **C code-cave** (`mod/`), since it changes how *all* homing behaves.

## Per-type parameter table — DECODED (2026-06-23)
The spawner indexes `0x8007941c` by the throw-berry **type** (the value passed in to `contact_object_spawn`, **not** the `0x21–0x24` pickup kind), stride `0x14` (20 bytes). Live `execTrace` of the spawner across the five saves + the table bytes:

| berry | type | flag `+0x10` | homing (bit 0x8) | `+4` model | `+0xe` (⚠️ unconfirmed) |
|---|---|---|---|---|---|
| red | 2 | `0xe5` | no | 110 | 256 |
| blue/super | 5 | `0xe5` | no | 110 | 256 |
| gold | 11 | `0xe5` | no | 110 | 256 |
| homing (berry) | 8 | `0xe5` | no | 123 | 3072 |
| homing (projectile) | **16** | `0xed` | **YES** | 123 | 3072 |
| mega (berry) | 45 | `0xe5` | no | 124 | 3328 |
| mega (projectile) | **48** | `0xed` | **YES** | 124 | 3328 |

**Homing is a two-object spawn.** A homing/mega throw spawns the **berry primary** (type 8/45, flag `0xe5`) which — `+2` timer = 8 (vs 100 for the rest) — quickly spawns the **homing projectile** (type 16/48, flag `0xed` = `0xe5 | 0x8` → the record `+0x33` homing bit set; that object runs the atan2 seek). Red/blue/gold spawn only the `0xe5` berry → straight flight. **Scan of all 64 entries: only types 16 and 48 carry the homing bit.**

**Entry layout (20 bytes, s16 unless noted):** `+0` class(=2) · `+2` spawn timer (8 = homing/mega berry, else 100) · `+4` **model/family** (110 basic / 123 homing / 124 mega) · `+6` =256 · `+8`/`+0xa` **=50** (⚠️ **UNCONFIRMED** — uniform 50; *candidate* hitbox **or** damage, not proven) · `+0xc` sub-index · `+0xe` (⚠️ **UNCONFIRMED** — 256 / 3072 / 3328; *candidate* behaviour/family word, **NOT proven speed** — the updater builds velocity from the sin table with a fixed `>>3` scale and no observed `+0xe` multiply) · `+0x10` **flags** (`u8`; bit `0x8` = homing → copied to record `+0x33`) · `+0x11..0x13` 3 bytes.

**Confirmed knobs (live):** flag `+0x10` bit `0x8` (homing on/off), `+4` (model/family), `+2` (spawn timer / two-object chain). **Unconfirmed candidates (do NOT treat as speed/damage):** `+0xe` and `+8/+0xa`. *(`type→entry`, the two-object homing spawn, and the homing flag are live-confirmed; `+0xe`/`+8`/`+0xa` are only inferred from the cross-type byte comparison and were **not** validated by poke-test or disasm — labels deliberately withheld pending the contact-damage-handler trace.)*

## Throw speed — DECODED + live-confirmed (2026-06-23)
The spawner `contact_object_spawn` (`0x8005a0e0`) allocates `contact_record_array 0x800b0d18 + slot*0x38` (stride `0x38` = `cursor*7*8`, wrap 64) and copies the **caller's** args into the record: `+0x0/+0x4/+0x8` = **position**, **`+0xc/+0x10/+0x14` = velocity** (`a3,t1,t2,t3`). Only `+0x20` class, `+0x22` timer, `+0x30/+0x31` bytes, and `+0x33` flags come from the param table.

⇒ **Throw speed = the initial velocity at `+0xc/+0x10/+0x14`, computed by the THROW HANDLER (the caller of `0x8005a0e0`) — NOT a param-table field.** This is why `+0xe` is not speed. Live-confirmed: homing projectile target is passed in the `+0x10` slot; red berry (type 2) `vel=[-3532,128,2075]`. **To make a fast berry:** patch the spawner args for a gated throw, as the Blackberry/Fastberry mod does in `mod/patch.asm`: velocity `<<1`, gravity `<<2`.

**Integration + per-object gravity (CONFIRMED 2026-06-23).** The contact updater integrates `pos += vel` each tick and applies **per-object gravity stored in the record at `+0x18`**: `velY += [+0x18]` at `0x8005a52c→0x8005a534` (the gravity field is set from the spawner's `t3` arg; a red berry = **128**). Physics ticks every **2 display frames**. So a berry's record is `pos +0/+4/+8`, `vel +0xc/+0x10/+0x14`, `gravity +0x18`.

**2× POC — BUILT + PROVEN to HIT, on a real disc (2026-06-23).** `mod/patch.asm` hooks the spawner entry (`0x8005a0f0`) and, for throw type 2 (red), doubles the velocity args **and quadruples the gravity arg** (`a3/t1/t2 <<1`, `t3 <<2`). *Naive ×2 velocity alone OVERSHOOTS* — the berry reaches the target's distance in half the ticks but, with unchanged gravity, is still rising, so it **arcs over** the enemy. The ballistic identity "same trajectory, half the time" = ×2 velocity **+ ×4 gravity**, which preserves the landing point. Verified live on the modded disc with `red_berry_enemy_test.mv`: the fast red berry **hits the same enemy** the pristine game does (HP entry `0x80089965`, `100→98`), just **earlier** (frame 4772 vs pristine 4788). This is the lever for the planned **net-new** fast berry: repoint the gate to a new type id.

## Damage application — DECODED + live-confirmed (2026-06/07)
The berry→enemy hit is handled by the contact walker **`contact_vs_actor_handler` (`0x80058af8`)** — the big function that `functionBounds` shows actually *starts* at `0x80058af8` and runs to `0x80059538` (the old `FUNC_800586B0` label is a point **inside** it: the vs-**Flik** distance branch). The function loops over a **damageable-object pointer table `0x80090748`** (`obj = *(0x80090748 + i*4)`, 64 slots) and, when a contact object (berry) overlaps an enemy (hit flag `s7`), runs this on the struck enemy `s2`:

### Actor-local `+0x6e` counter branch (`0x8005905c`)
Some enemies use `enemy+0x6e` as a local hit counter before death. This is the branch that explained the spider "blackberry one-shots" test:

```
hp  = lh enemy+0x6e
if hp >= 100: skip this local decrement lane      ; 999 death marker is exempt
cls = lbu contact_record+0x2c                     ; per-contact damage class

class 0,12 -> hp -= 2
class 1    -> hp -= 99
class 127  -> hp -= 4
class 128  -> hp -= 3
default    -> hp -= 1

sh hp,enemy+0x6e        @ 0x800590e4
if hp > 0: no death tail yet
if hp <= 0: continue into the hit/death tail, which writes enemy+0x6e = 999
```

**Live-confirmed 2026-07-07** with `killing_spider.movie.json`: pristine red and rebuilt ALLMODS forced-Blackberry both hit spider id `9` twice. The first hit changed `enemy+0x6e` `2 -> 1`; the second changed `1 -> 0` and then the final death tail wrote `999`. Blackberry's throw still hit the fast-physics hook and stored red class `s1=2` at `0x80047228`, so it kept 2x velocity / 4x gravity while matching red damage. The permanent quota `0x800a658e` did not decrement in either red or Blackberry runs.

### Side HP-table lane (`0x80059384`)
There is also a later side-table write:

```
lui a1,0x8009 ; addiu a1,a1,-26312       ; a1 = enemy_hp_table = 0x80089938
lw  a0,0x0(s2)                            ; a0 = enemy id  (enemy[+0])
lbu v1,0x6597(0x800a)                     ; v1 = active-byte selector @0x800a6597 (=2 here)
v0 = id*5 + selector ; a0 = 0x80089938 + v0    ; -> the enemy's HP byte
lbu v1,0x0(a0)                            ; v1 = current HP
sltiu v0,v1,33 ; bne -> skip if HP < 33   ; floor guard
addiu v0,v1,-2                            ; HP - 2
sb  v0,0x0(a0)        @ 0x80059384         ; THE DAMAGE WRITE
```

**Live-confirmed** (isolated DuckStation, `homing_berry.sav` + `mega_homing_berry.sav`): the store at `0x80059384` fires once per connecting hit; enemy id 9, selector 2 → HP byte `0x80089967`, value **104 → 102** (−2). Identical −2 for homing **and** mega ⇒ contact damage is **hardcoded, not param-driven**.

- **Persistent enemy struct** = the mover/AI object (e.g. `0x8009fd80`): `+0` = id/kind, `+0x5c` = state-flag word (hit sets bits `0x880`, clears `0x2`), `+0x6e` = local hit counter before death on some actors and `999` after the final hit/death tail, `+0x70` = mover-VM program pointer (on death hit, **swapped to the "got-hit" program from `enemy_hit_program_ptr` `0x80077b2c`** — i.e. the death/recoil routine; see [[event-interpreter-mover-vm]]).
- **"HP" is a side-table, not a struct field** — `enemy_hp_table` `0x80089938`, **5-byte records** `[hp, hp, hp, 0xff, hp]` per object id (the `0xff` at record `+3` is a sentinel — visible as the repeating `64 64 64 64 ff`), with `0x800a6597` selecting the active byte. Defaults: most **100** (`0x64`); some types **102 / 104 / 110**.
- **Side-table damage value** = a **fixed -2** at `0x80059384` (`addiu v0,v1,-2`). The berry param-table `+8/+0xa` (=50) is therefore **NOT** the damage — refuted. Per-berry differences that matter for the spider test are in the local `+0x6e` branch, not this side table.
- **Floor / death — RESOLVED 2026-07-03 (RCG-022)** → [[Enemy death and permanence]]. Correct: the `-2` HP byte is NOT the kill (it floors at 33). An enemy dies when the hit/death tail runs: `+0x6e=999` (death-anim trigger) → `+0x70` swapped to the hit/death mover-VM program (`0x80077b2c`) → `enemy_update_deathanim 0x800498ac`. **Permanence** is a separate, gold-only step: the destroy block (gated `s7>=2`) decrements the per-level quota `0x800a658e` + spawns destroy FX/pickup + zeroes the enemy id.

## Residuals (next steps)
- ~~**Floor/death semantics**~~ **SOLVED 2026-07-03 (RCG-022)** → [[Enemy death and permanence]]: enemy dies via the `+0x6e=999` / `+0x70` program-swap / `enemy_update_deathanim 0x800498ac` path; gold-only permanence decrements the quota `0x800a658e`. HP byte is not the kill.
- **Per-type damage vs local-counter enemies — RESOLVED 2026-07-03/07** → [[Thumper boss fight]] + `killing_spider.movie.json`: the branch `berry_tough_damage_dispatch 0x8005905c` decrements `enemy+0x6e` by a **per-contact damage class** read from the contact record `+0x2c`: class 0 → -2 · 1 → -99 (near-instakill) · 12 → -2 · 127 → -4 · 128 → -3 · default → -1 (guard: `+0x6e >= 100` exempt, which is why the 999-marker never takes this path). Blackberry parity is verified by forcing equip index 5 and observing red-equivalent `2 -> 1 -> 0 -> 999` on the spider.
- **`+0xe` / `+8` true meaning** — still unverified candidates (no longer suspected as damage; `+0xe` likely a behaviour/turn word).
- **Visuals** — colour / particles / model (a separate asset/VRAM thread).

## Pickup → arm chain (RE‑1, SOLVED + LIVE‑CONFIRMED 2026-06-23)
How grabbing a world pickup equips a berry — the routing needed to inject a **net‑new** berry pickup.

- **World berry pickups = type‑0x3f entries** in `LEVEL.DAT` (entry **kind at `+0xC`**). LEVEL01's four are kinds **`0x21` (homing), `0x22` (gold), `0x23` (blue/super), `0x24` (mega)** (the `list_level_pickups.py` catalog mislabels these "FLIK‑trig"). Red (kind `0x20`) is Flik's default.
- **The pickup‑collection handler is `FUNC_80053814`** (`0x80053814..0x8005480c`). On collection it reads the pickup object's **kind at object `+0x8`**, computes **`v1 = kind − 0x10`**, bounds‑checks `v1 < 0x22`, then `jr [pickup_collect_dispatch 0x8001b42c + v1*4]`.
- **Berry‑arm cases** (inside `FUNC_80053814`) each `sb <index>, 0x6597(at)` + a pickup SFX (`jal 0x80050994`, `a0`=sound id):
  - kind `0x20` → `table[0x10]` → `0x80054288` → index **0** (red)
  - kind `0x21` → `table[0x11]` → `0x80054298` → index **2** (homing)
  - kind `0x22` → `table[0x12]` → `0x800542ac` → index **3** (gold)
  - kind `0x23` → `table[0x13]` → `0x800542c0` → index **1** (blue) ✅ *live‑confirmed*
  - kind `0x24` → `table[0x14]` → `0x800542d4` → index **4** (mega)
- **LIVE‑CONFIRMED** (`blue_berry_walk_up_to_collect.sav`, pristine disc): walking Flik into the blue berry set `0x800a6597` 0→**1** via the case at `0x800542c8` (`sb v0=1`). 
- The equip index `0x800a6597` then drives the **throw‑type dispatch** (jump table `0x8001b1c0`) and the HUD/HP‑column.
- **Free dispatch slots** (→ default no‑op `0x800545cc`): `v1 = 0x05–0x0f, 0x15–0x18, 0x1e, 0x1f` ⇒ kinds `0x15–0x1f, 0x25–0x28, 0x2e, 0x2f`. Bound is `v1 < 0x22`, so a new kind in range needs **no bounds patch**.

> **Correction:** an earlier note pointed at a *parallel* set of arm cases in the contact handler `FUNC_80058af8` (dispatch `0x8001b570`, cases `0x80058934`+) with the same kind→index mapping. The **confirmed world‑pickup‑grab path is `FUNC_80053814`** (above); the `0x80058xxx` set is a secondary/alternate path. **Also note:** runtime pickup positions are **relocated** from the LEVEL.DAT coordinates at load (teleporting Flik to the DAT rt coords lands him on the wrong floor — that's why the teleport‑grab attempts failed). Injection via the placement pipeline edits DAT coords, which the game relocates consistently, so no runtime transform is needed to *place* a pickup.

*(How our mod uses this — inject a kind-`0x25` type-0x3f entry, redirect `pickup_collect_dispatch[0x15]` @`0x8001b480` to an arm cave, map index 5 to native red-equivalent throw path, then flag the next spawn for fast physics — is in [[Blackberry net-new berry]], not this OG note.)*

## Net-new berry (MOD)
The 6th-berry MOD that *uses* all the OG decode on this page (pickup→arm chain, throw dispatch,
spawner velocity/gravity, HP selector, and sprite-render/recolour mechanism) is documented
separately so this note stays OG-only: see **[[Blackberry net-new berry]]** and `mod/patch.asm`.
It is Blackberry/Fastberry: a net-new pickup that throws a dark red-path berry with doubled
velocity, quadrupled gravity, red class `2`, and red HP selector `0` during enemy damage.

## Pickup injection + DAT↔runtime coords (RE‑5, CONFIRMED end‑to‑end 2026-06-23)
- **Type‑0x3f record = `<X, Y, Z, kind>`** — 16 bytes, `<iiiI>` (kind in the low byte of the 4th word). Entries start at `LEVEL.DAT +0x8`; the record header holds the count.
- **Relocation = ×32 (`<<5`).** The game left‑shifts the stored DAT coords by 5 at load: **runtime = DAT × 32** (blue DAT `(4110,0,1794)` → runtime `(131520,0,57408)`). *This resolves the earlier teleport failures* — I'd been teleporting Flik to the already‑×32 "rt" coords (correct), but those berries are genuinely far/elevated. To place a pickup at a runtime spot, use **DAT = runtime ÷ 32**.
- **Flik LEVEL01 spawn** (resident spawn table `0x80077314 + scene*12`, scene 1): runtime `(197108, ~2734, 492895)` ⇒ DAT `(6159, ~85, 15403)`.
- **Injection pipeline (proven):** `tools/apply_level_placements.py` op `append_new {kind,x,y,z}` (DAT units) → grows the record by `0x10`, bumps the count, fixes the reloc table; `mod/build.py --placements <spec>` stages it into the disc. **Live‑confirmed:** appended a kind‑`0x23` (blue) entry at DAT `(6159,85,15463)`, built `--no-code`, booted via the movie → **Flik grabbed it at spawn and equipped blue** (`0x800a6597`→1). The berry collection radius is generous (~2000 runtime units). So a net‑new berry pickup just needs the same `append_new` with kind `0x25` (+ its new arm case).

## Net-new VISIBLE pickup + colour phase (2026-06-23)
**Render (how a kind draws):** kind → a 0xC-byte descriptor via `object_pointer_list 0x80096b98[kind]` (descriptors in EXE @`0x80081dc8`+; type `+0` = `0x1d` sprite pickup). The per-frame processor `0x800252a0` branches `kind==0x14` (grain, **visible** — projects position directly) vs "other" (berries/seeds, **invisible** trigger transform). The sprite-assembly `0x80025900`+ builds a GP0(`0x2c`) textured-quad primitive; its **colour word = `0x2c808080`** (neutral modulation → texture shown as-is) at `0x80025990`/`0x800259a0`, shared by ALL sprite pickups.
- **Visibility (OG):** only the grain branch of `0x800252a0` projects the sprite directly (visible); the "other" branch leaves berries/seeds invisible. A free kind must be routed through the grain branch to render. **Loader/placement (OG):** the loader inits runtime fields only for ORIGINAL records — appending a type-0x3f entry leaves Y=`0x80000000` (collected-sentinel) → auto-grab; edit an existing record instead. **Pickup collision is X+Y** (not Z), with a large **vacuum radius** (~14k runtime) → dead-centre placement auto-grabs. *(How our mod applies these is in [[Blackberry net-new berry]].)*
- **Thrown berry render:** drawn by the updater `FUNC_8005A308` via the same projection `0x80037320`; primitive built at `0x800b1b58`. Also a **textured sprite**.

**COLOUR — modulation (done) vs texture/CLUT (the real fix):**
- **Modulation alone is texture-limited (OG):** overriding the GP0 colour word only *darkens* a GOLD/RED texture (no blue channel to push) → "dark", not purple. The fix is the grayscale-CLUT base (texpage `0x0060`) — on a neutral ramp the modulation word becomes the exact hue (see "Berry sprite render + recolour mechanism" above).
- **Mod colour via the grayscale CLUT (SOLVED).** The earlier "needs a custom VRAM CLUT" plan was unnecessary: a different texpage already loads a **neutral grayscale** palette, so plain GP0 modulation sets the hue exactly. Blackberry uses this with `0x2c2b051a`.

## Berry damage is throw-TYPE-gated (OG, decoded 2026-06-23)
Whether a thrown berry damages a "berry-tough" enemy (the worm) is gated by the **berry class / power value** `s1`. The throw dispatch (`jr [0x8001b1c0 + equip_idx*4]`) routes to per-berry handlers at `0x8004719c+` that are **byte-identical except this one value** `s1`: **red=2, blue=5, homing=8, gold=11(0xb), mega=45**. It is passed to the spawner (`sw s1,0x1c(sp)` @`0x80047228`).
- **red(2) BOUNCES off the worm; 5+ DAMAGES it** (live-proven). red/blue/gold share the **same straight-throw physics** — only `s1` differs (homing/mega additionally change elevation + spawn the homing projectile).
- The target enemy must have the **berry-damageable flag — enemy struct `+0x5c` bit `0x40`** (the worm has it). On a qualifying hit the **knockback/damage handler `0x80058df0+`** runs (writers `0x80058ed0/ef0/0x80059154`): hit-state enemy `+0x54/+0x58 = 0x1000`, knockback `+0x6c`, enemy gains negative velocity at `+0x30/+0x38`. (Separate from the **-2 HP** path @`0x80059384` above, which is for already-damageable enemies.)
- `s1` is the *class*, so it also governs **kill permanence** — **CORRECTED 2026-07-03 (RCG-022, live) → only GOLD(11) is permanent, NOT mega.** See [[Enemy death and permanence]]: the permanence gate (`beq …,11` @`0x800591f8` inside `contact_vs_actor_handler`) fires the destroy block only for gold (decrements the per-level quota `G_ENEMIES_REMAINING 0x800a658e`, 21→20; live 3/3 on spider + mosquito). mega/homing/blue knock the enemy out (999-marker + death-anim) but do NOT decrement the quota (user-confirmed normal). Earlier "gold(11)/mega(45) = permanent" was wrong.
- **CORRECTION:** record `+0x22` (the spawn timer, copied from param `+0x02`: red=0, homing=9) is **NOT** the damage power — it is a **fuse/flight** value (forcing it derails the flight). The damage lever is the throw `s1`. An earlier "worm is blanket berry-immune" read was also wrong — it is power-gated.
- *Debug method:* write-watch the enemy struct (`0x800a0c60`, anchor `0x800a0c9c`) for the `0x80058exx` handler during a throw. Gotcha: `gpu.pickObject`'s snapshot is empty for ~4 frames after `loadState`.

## Berry sprite render + recolour mechanism (OG)
Pickup/thrown/splash berry sprites are **GP0(`0x2c`/`0x2e`) modulated quads on a NEUTRAL grayscale-atlas CLUT** — texture page **(640,0)**, CLUT `0x3670` @VRAM (768,217) / `0x3672` @(800,217). **On a grayscale base the GP0 modulation colour word IS the rendered hue.**
- **Texpage selects the palette:** grain's `0x70f0` → a GOLD ramp (B=0); texpage `0x0060` → the **grayscale ramp** (any hue via modulation). The pickup descriptor's `+8`/`+9` = U/V base into the atlas; the berry glyph sits at atlas UV ~`(63,0)` (`gpu.decodeTexture` of page 640,0 shows every pickup glyph). Pickup sprite colour word is built at **`0x800259a0`**.
- **Thrown/held/splash colour** is copied to the GPU ordering table by **two list-emitters**: the terrain/sprite emitter **`0x800105f0`** (`sw v1,0x1c(s3)`) and the **contact-object emitter `0x80014a70`** (`sw v1,4(s7)`; walks records by stride 0x38 — the path the THROWN berry takes). The red berry's word is `0x2c001270`; with the blue class it is `0x2c802000`. (Find each emitter PC via a windowed `accessLog` write-watch FILTERED on the colour value — the OT double-buffers so fixed-address watches miss it.)
- The spawner also copies the parameter row's final word into the contact record at `+0x34`;
  live readback confirmed red `0x2c001270` and blue-class `0x2c802000` there. Blackberry's
  thrown-colour caves patch the equipped index-5 berry to `0x2c2b051a`; it intentionally avoids
  the native type-16 homing projectile path.

> **Our Blackberry/Fastberry mod** hooks these sites (`0x80047170`, `0x8005a0f0`, `0x800590f0`, `0x80059358`, `0x800259a0`, `0x800105f0`, `0x80014a70`, …) to add the 6th berry. Implementation, cave names, colour values, speed/class/HP-selector hooks, and the build are kept out of this RE note — see **[[Blackberry net-new berry]]**, `src_re/berry_throw_80047170.c`, and `mod/patch.asm` / `mod/berry_projectile.h`. Memories: [[berry-enemy-damage-mechanism]], [[pickup-sprite-recolor-grayscale-clut]], [[berry-equip-throw-arm-chain]].

## Symbols / C
`symbols/re_symbols.sym`: `berry_projectile_update 0x8005a308`, `contact_object_spawn 0x8005a0f0`, `contact_metadata_table_b 0x8007941c` (the per-type param table), `contact_record_array 0x800b0d18`, `contact_alloc_cursor 0x8008234c`, `atan2_heading 0x80060ae4`. **Damage path:** `contact_vs_actor_handler 0x80058af8`, `berry_tough_damage_dispatch 0x8005905c`, `enemy_hit_counter_store 0x800590e4`, `enemy_contact_damage_store 0x80059384`, `enemy_hp_table 0x80089938`, `enemy_hit_program_ptr 0x80077b2c`, `damageable_object_ptr_table 0x80090748`, `berry_flik_marker 0x800a6597` (the HP active-byte selector). C reference: `mod/berry_projectile.h`.

## Related
[[FUNC_8005A308]] · [[Enemy AI state machine]] (the berry residual it resolves) · [[Event and scripting system]] (contact objects) · [[Gameplay - Input and Movement]] (Square)
