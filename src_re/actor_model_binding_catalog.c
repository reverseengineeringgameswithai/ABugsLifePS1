/*
 * actor_model_binding_catalog.c -- RCG-005 character/plant model binding map.
 *
 * This is documentation-grade RE C, not a build unit. It records the resolved
 * "which retail actor uses which authored model family" layer for the editor.
 * Detailed behavior remains in the system-specific source files named below.
 *
 * Evidence basis:
 * - tools/parse_all_anm.py round-trips the full corpus: 78/78 .ALL and
 *   58/58 .ANM, proving the shared Traveller's Tales model/animation grammar.
 * - ObsidianVault/Assets/Asset - ALL ANM Format Grammar.md is the current
 *   byte-exact format baseline.
 * - ObsidianVault/Systems/Seed plant output binding.md and
 *   src_re/plant_spawn_8005bdbc.c prove type N -> PLANTNN.ALL through the
 *   per-level plant model table at 0x800A649C.
 * - src_re/source3f_dispatch_80053814.c and
 *   src_re/pickup_handlers_80054288_80054554.c prove type-0x3f kind is the
 *   pickup/object model+behavior discriminator for FLIK letters, berries,
 *   seed tokens, grain, telescope, and kind 0x31.
 * - ObsidianVault/Systems/Enemy AI state machine.md proves the runtime actor
 *   slots and drivers for regular enemies, Hopper, Thumper, and the bird
 *   setpiece; the model filenames come from the disc corpus inventory.
 *
 * Non-claims / residual routing:
 * - This closes RCG-005 as a binding/catalog gap, not retail-perfect offline
 *   rendering. Real sprite/FX material detail stays in RCG-008/013/014/023.
 * - Enemy HP, boss overlay hit bookkeeping, and death/permanent-kill rules
 *   stay in RCG-006/020/022.
 * - The per-level plant manifest source on disc is still a seed/plant authoring
 *   residual, not a model-binding unknown.
 * - FLIK/actor animation channel semantics are editor polish; the file layout
 *   and renderer/animation pipeline are already byte-exact enough to bind.
 */

#include <stdint.h>

typedef enum ActorModelEvidence {
  ACTOR_MODEL_STATIC_CORPUS = 0,
  ACTOR_MODEL_RUNTIME_CONFIRMED = 1,
  ACTOR_MODEL_HANDLER_CONFIRMED = 2,
  ACTOR_MODEL_RESIDUAL_REFERENCE = 3,
} ActorModelEvidence;

typedef struct ActorModelBinding {
  const char* actor_or_kind;
  const char* model_asset;
  const char* animation_asset;
  const char* runtime_binding;
  ActorModelEvidence evidence;
} ActorModelBinding;

static const ActorModelBinding k_rcg005_actor_model_bindings[] = {
  {
    "Flik player",
    "REBUILD/files/CHARS/FLICK.ALL",
    "REBUILD/files/CHARS/FLICK.ANM",
    "resident player state 0x800A6500; FLICK.ALL/ANM residency proven live",
    ACTOR_MODEL_RUNTIME_CONFIRMED,
  },
  {
    "Flik death / power / harvester variants",
    "REBUILD/files/CHARS3/FLICKD.ALL; CHARS3/FLICKP.ALL; CHARS3/FLIKHARV.ALL",
    "matching .ANM files",
    "static character corpus variants; harvester mechanic remains RCG-020",
    ACTOR_MODEL_STATIC_CORPUS,
  },
  {
    "Seed carried/plantable prop",
    "REBUILD/files/BITS/SEED.ALL",
    0,
    "seed actor loader/update path; plantable seed records live in LEVEL.RAW chunk 31",
    ACTOR_MODEL_STATIC_CORPUS,
  },
  {
    "Seed planter / planter prop",
    "REBUILD/files/BITS/PLANTTER.ALL",
    0,
    "same .ALL grammar; exact runtime role depends on authored plant/seed scene",
    ACTOR_MODEL_STATIC_CORPUS,
  },
  {
    "Plant output types 1..14",
    "REBUILD/files/PLANTS/PLANT01.ALL..PLANT11.ALL; PLANTS2/PLANT12.ALL..PLANT14.ALL",
    "matching .ANM files",
    "plant slot type N -> *(0x800A649C + N*4) -> PLANTNN.ALL",
    ACTOR_MODEL_RUNTIME_CONFIRMED,
  },
  {
    "Type-0x3f FLIK letters 0x10..0x13",
    "runtime object descriptor selected by kind",
    0,
    "source3f_dispatch constructs generic visible object and dispatches F/L/I/K handlers",
    ACTOR_MODEL_HANDLER_CONFIRMED,
  },
  {
    "Type-0x3f berries 0x21..0x24",
    "runtime object descriptor selected by kind",
    0,
    "kind changes marker/equip behavior and visible descriptor path",
    ACTOR_MODEL_HANDLER_CONFIRMED,
  },
  {
    "Type-0x3f seed tokens 0x29..0x2D",
    "runtime sprite descriptor re-skinned by fcn_8003e760",
    0,
    "token pickup side selects counter lane and atlas level; plant chosen later",
    ACTOR_MODEL_HANDLER_CONFIRMED,
  },
  {
    "Type-0x3f telescope / green hint gem 0x30",
    "runtime animated object descriptor",
    0,
    "kind 0x30 telescope bob path and hint-view contact action confirmed",
    ACTOR_MODEL_HANDLER_CONFIRMED,
  },
  {
    "Type-0x3f animated construct 0x31",
    "runtime animated object descriptor",
    0,
    "dedicated source path exists; full retail semantics remain RCG-026",
    ACTOR_MODEL_RESIDUAL_REFERENCE,
  },
  {
    "Regular chaser enemies",
    "CHARS/BADBUG.ALL, CHARS/FLY.ALL, CHARS/MOS.ALL, CHARS/WASP.ALL; CHARS3/DRAGFLY.ALL; etc.",
    "matching .ANM files",
    "active chaser slot 0x80095358 driven by FUNC_8004DF18 across levels",
    ACTOR_MODEL_RUNTIME_CONFIRMED,
  },
  {
    "Stationary / mover-VM enemies",
    "CHARS4/BADWORM.ALL, CHARS2/ROLL.ALL, CHARS3/WEEVIL.ALL; etc.",
    "matching .ANM files",
    "mover-VM actors in 0x800A00xx.. region driven by FUNC_8004C13C",
    ACTOR_MODEL_RUNTIME_CONFIRMED,
  },
  {
    "Hopper boss",
    "REBUILD/files/CHARS2/HOPPER.ALL",
    "REBUILD/files/CHARS2/HOPPER.ANM",
    "fight uses chaser slot 0x80095358 / FUNC_8004DF18",
    ACTOR_MODEL_RUNTIME_CONFIRMED,
  },
  {
    "Thumper boss",
    "REBUILD/files/CHARS2/THUMPER.ALL",
    "REBUILD/files/CHARS2/THUMPER.ANM",
    "fight uses chaser slot 0x80095358 / FUNC_8004DF18; overlay HP remains RCG-006",
    ACTOR_MODEL_RUNTIME_CONFIRMED,
  },
  {
    "Thud boss",
    "REBUILD/files/CHARS3/THUD.ALL",
    "REBUILD/files/CHARS3/THUD.ANM",
    "static corpus binding; runtime fight not decoded",
    ACTOR_MODEL_STATIC_CORPUS,
  },
  {
    "Bird / finale setpiece",
    "REBUILD/files/CHARS3/BBIRD.ALL",
    "REBUILD/files/CHARS3/BBIRD.ANM",
    "actor 0x80090BC0 driven by FUNC_8004DD98",
    ACTOR_MODEL_RUNTIME_CONFIRMED,
  },
  {
    "NPC / cast actors",
    "CHARS*/ATTA*.ALL, DOT.ALL, GYPSY.ALL, HEIM.ALL, MANNY*.ALL, ROSIE.ALL, SLIM.ALL, etc.",
    "matching .ANM files where present",
    "static corpus binding; per-scene dialogue/cutscene triggers remain event/front-end work",
    ACTOR_MODEL_STATIC_CORPUS,
  },
};

static const uint32_t k_rcg005_actor_model_binding_count =
    sizeof(k_rcg005_actor_model_bindings) / sizeof(k_rcg005_actor_model_bindings[0]);

static const int k_rcg005_binding_catalog_closed = 1;
