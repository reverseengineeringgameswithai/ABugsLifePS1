/*
 * Horsefly / FLY actor (id 6) - Phase 4 D08 source reconstruction.
 *
 * Evidence boundaries:
 *   - exact executable instructions are guarded by tools/phase4_d08_static.c;
 *   - frame-boundary and exact-PC runtime evidence is reduced by
 *     tools/phase4_d08_evidence.c;
 *   - names below are descriptive reconstruction names, not retail symbols.
 */

#include <stddef.h>
#include <stdint.h>

enum {
  HORSEFLY_ACTOR_ID = 6,
  HORSEFLY_MAX_HP = 8,
  CONTACT_REACTION_TICKS = 15,
  PROJECTILE_REACTION_TICKS = 20,
  TEMPORARY_KO_HP_SENTINEL = 999,
};

enum {
  HORSEFLY_WANDER_PROGRAM = 0x800776d0u,
  HORSEFLY_WANDER_PARK_IP = 0x800776e4u,
  GENERIC_DEFEATED_STOP_PROGRAM = 0x800776acu,
  HORSEFLY_CONTACT_CALLBACK = 0x8004a144u,
};

typedef struct HorseflyActor {
  uint32_t id;                 /* +0x00 */
  uint8_t unknown_04[0x58];
  uint16_t flags_5c;           /* +0x5c */
  uint16_t unknown_5e;
  uint16_t death_field_60;     /* +0x60 */
  uint8_t unknown_62[0x0a];
  int16_t reaction_6c;         /* +0x6c */
  int16_t hp_6e;               /* +0x6e */
  uint32_t mover_vm_ip_70;     /* +0x70 */
  uint32_t pose_data_74;       /* +0x74 */
  uint32_t unknown_78;
  uint32_t contact_callback_7c;/* +0x7c */
  uint32_t spawn_backlink_80;  /* +0x80 */
} HorseflyActor;

_Static_assert(offsetof(HorseflyActor, flags_5c) == 0x5c, "flags offset");
_Static_assert(offsetof(HorseflyActor, death_field_60) == 0x60, "death field offset");
_Static_assert(offsetof(HorseflyActor, reaction_6c) == 0x6c, "reaction offset");
_Static_assert(offsetof(HorseflyActor, hp_6e) == 0x6e, "hp offset");
_Static_assert(offsetof(HorseflyActor, mover_vm_ip_70) == 0x70, "VM offset");
_Static_assert(offsetof(HorseflyActor, contact_callback_7c) == 0x7c, "callback offset");
_Static_assert(sizeof(HorseflyActor) == 0x84, "actor stride");

/* Retail bytes at 0x800776d0.  No proximity, native-call, chase, or projectile
 * opcode occurs in this program; body contact is the Horsefly's attack. */
static const uint8_t horsefly_wander_program[] = {
  0x16, 0x00, 0xc0, 0xff, 0xc0, 0xff, /* set_byte_params[-64,-64] */
  0x0d, 0x00, 0x00, 0x00, 0x02, 0x00, /* anim_clip_load[0,2] */
  0x02, 0x00, 0x3f, 0x00, 0x20, 0x00, /* wait_random[63,32] */
  0x03, 0x00,                         /* random_dir_step */
  0x05, 0x00,                         /* park_seek */
  0xff, 0xff, 0x05, 0x00,             /* jump_back[5] */
  0x00, 0x00,                         /* park_end */
};

/* Pointer 0x80077b2c selects this shared terminal loop after a class-one KO. */
static const uint8_t generic_defeated_stop_program[] = {
  0x07, 0x00,             /* park_arrive_stop */
  0xff, 0xff, 0x01, 0x00, /* jump_back[1] */
};

/* Reconstruction of the shared marker switch at 0x80059074..0x800590e4. */
static int16_t projectile_damage_for_marker(uint8_t marker) {
  switch (marker) {
    case 0:
    case 12:
      return 2;
    case 1:
      return 99;
    case 127:
      return 4;
    case 128:
      return 3;
    default:
      return 1;
  }
}

/* Reconstruction of the class-one tail observed for the D08 blue-berry KO.
 * The retail routine subsequently calls actor retirement/respawn bookkeeping
 * at 0x800498ac(actor, 1).  It does not execute the class>=2 quota/effect path. */
static void enter_temporary_ko(HorseflyActor *actor) {
  actor->hp_6e = TEMPORARY_KO_HP_SENTINEL;
  actor->death_field_60 = 0;
  actor->flags_5c = (uint16_t)((actor->flags_5c | 0x0880u) & ~0x0002u);
  actor->mover_vm_ip_70 = GENERIC_DEFEATED_STOP_PROGRAM;
}

/* Keep the reconstruction objects referenced in translation-unit-only builds. */
static const void *const phase4_d08_reconstruction_roots[] = {
  horsefly_wander_program,
  generic_defeated_stop_program,
  (const void *)&projectile_damage_for_marker,
  (const void *)&enter_temporary_ko,
};
