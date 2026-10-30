---
kind: mod
id: MOD_gold_berry_token_drop
name: Gold Berry Token Drop
status: operator_confirmed_working_surface
confidence: confirmed
source_state: mod
canon_dependencies:
  - SYS_contact_objects_and_drops
  - SYS_enemy_death_and_permanence
  - SYS_hud_counters
hooks:
  - HOOK_800592A4
  - HOOK_800589D4
src_paths:
  - mod/caves/golddrop.c
  - mod/mods/golddrop.asm
  - mod/patch_golddrop.asm
build_paths:
  - mod/mods.yaml
evidence:
  - EXP_2026_07_07_golddrop_pickup_verifier
  - ObsidianVault/Archive/Superseded/Mods_Gold-berry_drop_on_non-gold_kills.md
  - src_re/enemy_drops.c
---

# MOD_gold_berry_token_drop

## Purpose

When an enemy dies while Flik holds a non-gold berry, a per-berry chance spawns a collectible spinning gold-kill glyph. Walking over the glyph credits the tagged enemy as permanently defeated without equipping gold.

## Locked working behavior

- Spawns the native `type 120` / `action_id 123` spinning gold-kill glyph, not a literal `type 34` gold-berry pickup.
- Tags the glyph contact record at `+0x1c` with the dying enemy pointer.
- Clears the native upward pop/fall fields so the glyph stays on the floor instead of rising and falling through the ground.
- Sets collectible flags and `+0x22 = 200`, copying the health-leaf-style timed despawn.
- On pickup, decrements `0x800A658E`, pulses `0x800B0198`, optionally fires the all-defeated event, and finalizes/removes the enemy through the native permanent-kill cleanup shape.
- The visible bottom counter advances because the original HUD displays `LW(0x80082258) - LH(0x800A658E)`.

## Per-berry odds

Drop fires iff `rng_byte < threshold`, indexed by equipped berry at `0x800A6597`.

| equip index | berry | chance | threshold |
|---|---|---:|---:|
| 0 | red | 1/12 | 21 |
| 1 | blue | 1/8 | 32 |
| 2 | homing | 1/4 | 64 |
| 3 | gold | none | 0 |
| 4 | mega | 1/2 | 128 |
| 5 | blackberry | 1/6 | 43 |

## Hook map

| Hook | Role | Policy |
|---|---|---|
| `0x800592A4` | One-shot enemy death tail. Spawns and tags the glyph. | Known-good spawn hook. |
| `0x800589D4` | Contact-walker default pickup branch. Credits tagged glyphs only. | Must remain inert for untagged/default records. |

Do not revive the old `0x80049958` spawn hook. It can execute repeatedly for one death and create duplicate tokens.

## Source excerpt

Source: `mod/caves/golddrop.c`

```c
typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;
typedef int            s32;

typedef struct ContactRecord {
    s32 x, y, z;
    s32 render_attr[4];
    s32 enemy_tag;       /* +0x1c: allocator initializes -1; this mod tags glyph drops here. */
    u16 action_id;       /* +0x20 */
    signed short active_type; /* +0x22: lifetime/live gate */
} ContactRecord;

/* spawn_drop(x,y,z, type, extra): allocate a contact-object drop at (x,y,z). */
typedef ContactRecord *(*spawn_drop_fn)(int x, int y, int z, int type, int extra);
#define SPAWN_DROP  ((spawn_drop_fn)0x80059E44)

#define EQUIP_INDEX (*(volatile unsigned char *)0x800A6597)
#define RNG_CURSOR  (*(volatile unsigned char *volatile *)0x800822F4)

#define GOLD_GLYPH_TYPE      120 /* original permanent-kill glyph (spinning gold glyph) */
#define GOLD_GLYPH_ACTION    123 /* type-120 action_id; out-of-range => walker default branch */
#define GOLD_GLYPH_EXTRA      25 /* original permanent-kill path's stackArg for type 120 */
#define GOLD_GLYPH_FLAGS    0xE2 /* original glyph flags plus collectable bit 0x02 */
#define HEALTH_LEAF_LIFETIME 200 /* type-38 health-leaf active_type */

#define ENEMY_PTR_MIN 0x80090000u
#define ENEMY_PTR_MAX 0x800B0000u

#define ENEMIES_REMAINING (*(volatile u16 *)0x800A658E)

typedef void (*one_arg_fn)(void *);
typedef void (*enemy_finish_fn)(void *, int);
#define SPAWN_DESTROY_FX    ((one_arg_fn)0x800503FC)
#define ALL_DEFEATED_EVENT  ((one_arg_fn)0x8005182C)
#define ENEMY_FINISH_REMOVE ((enemy_finish_fn)0x800498AC)

static const unsigned char DROP_THRESH[6] = { 21, 32, 64, 0, 128, 43 };

void abl_golddrop_on_death(const int *enemy)
{
    unsigned idx = EQUIP_INDEX;
    if (idx >= 6) return;
    unsigned char thresh = DROP_THRESH[idx];
    if (thresh == 0) return;

    volatile unsigned char *p = RNG_CURSOR;
    RNG_CURSOR = p + 1;
    if (*p >= thresh) return;

    ContactRecord *glyph = SPAWN_DROP(enemy[1], enemy[2], enemy[3],
                                      GOLD_GLYPH_TYPE, GOLD_GLYPH_EXTRA);
    glyph->enemy_tag = (s32)enemy;
    glyph->render_attr[1] = 0;                    /* no upward pop */
    glyph->render_attr[3] = 0;                    /* no gravity/fall-through */
    *((volatile u8 *)glyph + 0x33) = GOLD_GLYPH_FLAGS;
    glyph->active_type = HEALTH_LEAF_LIFETIME;
}

void abl_golddrop_on_default_pickup(ContactRecord *rec)
{
    if (rec->action_id != GOLD_GLYPH_ACTION) return;

    u32 tag = (u32)rec->enemy_tag;
    if (tag < ENEMY_PTR_MIN || tag >= ENEMY_PTR_MAX) return;

    rec->enemy_tag = -1;

    volatile u8 *enemy = (volatile u8 *)tag;
    if (*(volatile u32 *)(enemy + 0x00) == 0) return;

    SPAWN_DESTROY_FX((void *)0x800B0198);
    *(volatile u16 *)(enemy + 0x62) = 0;

    u16 remaining = ENEMIES_REMAINING;
    if (remaining != 0) {
        remaining--;
        ENEMIES_REMAINING = remaining;
        if (remaining == 0) ALL_DEFEATED_EVENT((void *)0x80090B68);
    }

    ENEMY_FINISH_REMOVE((void *)enemy, 1);
}
```

## Assembly implementation

The active consolidated build uses pure ASM in `mod/mods/golddrop.asm`. The standalone implementation is `mod/patch_golddrop.asm`; `mod/caves/golddrop.c` is the C-shaped reference record.

Key active writes:

- `jal 0x80059E44` with `a3 = 120` and stack extra `25`.
- `sw s2, 0x1C(v0)` to tag the glyph with the dying enemy.
- `sw zero, 0x10(v0)` and `sw zero, 0x18(v0)` to prevent pop/fall-through.
- `sb 0xE2, 0x33(v0)` to keep the glyph flags and add the collectible bit.
- `sh 200, 0x22(v0)` for health-leaf-style timeout.
- Pickup path decrements `0x800A658E` and calls `0x800498AC(enemy, 1)`.

## Validation

`EXP_2026_07_07_golddrop_pickup_verifier` cold-booted the rebuilt ALLMODS disc, forced only the odds table, replayed `killing_spider.movie.json`, spawned one glyph, warped Flik onto it, and forced quota `1 -> 0` to exercise the all-defeated branch.

Observed:

- death hook 1
- spawn 1
- pickup hook 1
- HUD pulse 1
- quota store 1
- all-defeated call 1
- finalizer call 1
- valid CPU state after pickup

## Non-goals and hazards

- Do not convert this back to `type 34`; that equips gold and replaces Flik's berry behavior.
- Do not convert the carrier to `type 38` health leaf while storing an enemy pointer at `+0x1c`; that field is not free for the health-leaf record shape.
- Do not place Gold Berry token code at `0x8007EFE8..0x8007F0D8` or helpers at `0x80081058..0x800810A4`.
- Do not overwrite native descriptor memory `0x80082030..0x8008203C`; that caused seed/berry color regressions.

## Provenance

The full chronological working note was formerly at
`ObsidianVault/Mods/Gold-berry drop on non-gold kills.md`; migration archived it at
`ObsidianVault/Archive/Superseded/Mods_Gold-berry_drop_on_non-gold_kills.md`. The
Archive citation is intentional provenance, while this page is the current curated mod record.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Mods/Gold-berry drop on non-gold kills.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Mods_Gold-berry_drop_on_non-gold_kills.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
