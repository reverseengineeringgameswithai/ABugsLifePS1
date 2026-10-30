/*
 * campaign_level_coverage.c -- static campaign coverage anchors for RCG-001.
 *
 * This is documentation-grade RE C, not a build unit. It captures the resident
 * stage-directory map and the on-disk structures used by
 * tools/campaign_level_inventory.py and ObsidianVault/Systems/
 * Campaign Level Coverage Matrix.md.
 *
 * Evidence basis:
 * - Resident filename table at 0x8001ad0c, documented in
 *   ObsidianVault/Findings/Finding - Level-warp mechanism.md.
 * - LEVEL.DAT parser record sizing from FUNC_8001CDC0 / tools/dat_reloc.py.
 * - LEVEL.RAW PROPACK chunk container from FUNC_8001A1DC /
 *   tools/decode_level_raw.py.
 *
 * Status 2026-07-02:
 * - Static inventory covers REBUILD/files/LEVEL00..LEVEL10.
 * - Stages 1..15 are mapped to level directories and overlay stems.
 * - Primary type-0x3f pickup/object tables are counted for all retail dirs.
 * - Runtime fixed-address generality has separate live evidence for
 *   LEVEL02/03/04/05 in "Finding - Level formats generalize, content is
 *   per-level".
 *
 * Non-claims / residual:
 * - This does not decode objective success conditions, boss phase scripts,
 *   or overlay verb semantics. Those remain RCG-003/006/009 work.
 */

#include <stdint.h>

typedef struct CampaignStageResource {
  uint8_t stage_id;          /* [0x80082504] request value, 1..15 */
  const char* dir;           /* ISO directory under REBUILD/files */
  const char* overlay_stem;  /* per-stage LEVEL*.BIN/DAT/RAW stem */
} CampaignStageResource;

static const CampaignStageResource k_campaign_stage_resources[] = {
  { 1,  "LEVEL01", "LEVEL1A" },
  { 2,  "LEVEL03", "LEVEL1B" },
  { 3,  "LEVEL02", "LEVEL1C" },
  { 4,  "LEVEL06", "LEVEL2A" },
  { 5,  "LEVEL10", "LEVEL2B" },
  { 6,  "LEVEL01", "LEVEL2C" },
  { 7,  "LEVEL04", "LEVEL3A" },
  { 8,  "LEVEL05", "LEVEL3B" },
  { 9,  "LEVEL04", "LEVEL3C" },
  { 10, "LEVEL07", "LEVEL4A" },
  { 11, "LEVEL02", "LEVEL4B" },
  { 12, "LEVEL03", "LEVEL4C" },
  { 13, "LEVEL09", "LEVEL5A" },
  { 14, "LEVEL08", "LEVEL5B" },
  { 15, "LEVEL05", "LEVEL5C" },
};

typedef struct LevelDatRecordHeader {
  uint16_t count;
  int16_t type;
} LevelDatRecordHeader;

typedef struct Type3fPlacementRecord {
  int32_t x_file;       /* runtime coordinate = file coordinate << 5 */
  int32_t y_file;
  int32_t z_file;
  uint8_t kind;         /* grain/FLIK/berry/token/telescope/etc. */
  uint8_t state;
  uint8_t unk0e;
  uint8_t unk0f;
} Type3fPlacementRecord;

typedef struct LevelRawChunkHeader {
  uint32_t word0_be;
  uint32_t payload_size_be;
  uint8_t header_tail[6];
} LevelRawChunkHeader;

enum Type3fKind {
  TYPE3F_FLIK_F = 0x10,
  TYPE3F_FLIK_L = 0x11,
  TYPE3F_FLIK_I = 0x12,
  TYPE3F_FLIK_K = 0x13,
  TYPE3F_GRAIN = 0x14,
  TYPE3F_GREEN_BERRY = 0x21,
  TYPE3F_GOLD_BERRY = 0x22,
  TYPE3F_BLUE_BERRY = 0x23,
  TYPE3F_PURPLE_BERRY = 0x24,
  TYPE3F_SEED_ORANGE = 0x29,
  TYPE3F_SEED_BLUE = 0x2a,
  TYPE3F_SEED_GREEN = 0x2b,
  TYPE3F_SEED_TOKEN_2C = 0x2c,
  TYPE3F_SEED_TOKEN_2D = 0x2d,
  TYPE3F_TELESCOPE = 0x30,
  TYPE3F_ANIMATED_CONSTRUCT = 0x31,
};

/*
 * FUNC_8001CDC0 record-size rule, expressed for cross-level inventory.
 * Negative record sizes follow the resident parser's packed-record formula.
 */
static uint32_t level_dat_record_size(uint16_t count, int16_t type) {
  if (type < 0)
    return ((((uint32_t)count * 3u + 1u) >> 1) << 2) + 0x10u;
  if (type == 0x3f)
    return (uint32_t)count * sizeof(Type3fPlacementRecord) +
           sizeof(LevelDatRecordHeader);
  return (uint32_t)count * 0x0cu + sizeof(LevelDatRecordHeader);
}
