/* phase4_f01_static_hard_truth.c -- F01 trig and dispatch hard-truth probe.
 *
 * This probe reads the pristine resident PS-X EXE directly.  It has two jobs:
 *
 *   1. Decode the address-forming instructions used by RotMatrix and the four
 *      named Q14-table readers, then independently derive and byte-compare the
 *      complete lookup tables.  Reader evidence without a content match (or a
 *      content match without reader evidence) fails closed.
 *   2. Decode the two PCs described by the live receipt as jalr dispatches.
 *      The instruction word decides the result.  Nearby real jr tables are
 *      recovered as a positive control and emitted entry-for-entry.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror \
 *      tools/phase4_f01_static_hard_truth.c -lm -o /tmp/f01-hard-truth
 *
 * Usage:
 *   /tmp/f01-hard-truth REBUILD/files/SCUS_942.88
 */
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LOAD_ADDRESS 0x80010000u
#define TEXT_SIZE    0x00072800u
#define HEADER_SIZE  0x00000800u
#define FILE_VA_BASE (LOAD_ADDRESS - HEADER_SIZE)

#define RAW_BASE       0x80074970u
#define RAW_ENTRIES    5120u
#define RAW_STRIDE     2u
#define RAW_AMPLITUDE  16384
#define RAW_GAP_LO     0x80075930u
#define RAW_GAP_HI     0x800769A8u

#define PACKED_BASE       0x8007A7E4u
#define PACKED_ENTRIES    4096u
#define PACKED_STRIDE     4u
#define PACKED_AMPLITUDE  4096
#define PACKED_GAP_LO     0x8007B63Cu
#define PACKED_GAP_HI     0x8007D5C0u

typedef struct {
    uint8_t *p;
    size_t n;
} Blob;

typedef struct {
    uint32_t pc;
    uint32_t word;
} WordPin;

typedef struct {
    const char *function;
    uint32_t pc;
    const char *mnemonic;
    uint32_t range_lo;
    uint32_t range_hi;
    uint32_t width;
    const char *derivation;
} Reader;

static Blob slurp(const char *path)
{
    FILE *f = fopen(path, "rb");
    Blob out = {0};
    long length;
    if (!f) {
        fprintf(stderr, "%s: %s\n", path, strerror(errno));
        exit(2);
    }
    if (fseek(f, 0, SEEK_END) || (length = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) {
        fprintf(stderr, "%s: cannot size input\n", path);
        exit(2);
    }
    out.n = (size_t)length;
    out.p = (uint8_t *)malloc(out.n ? out.n : 1);
    if (!out.p || fread(out.p, 1, out.n, f) != out.n) {
        fprintf(stderr, "%s: cannot read input\n", path);
        exit(2);
    }
    fclose(f);
    return out;
}

static uint16_t le16p(const uint8_t *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t le32p(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static size_t va_offset(const Blob *blob, uint32_t va, size_t width)
{
    size_t offset;
    if (va < FILE_VA_BASE) {
        fprintf(stderr, "VA 0x%08X precedes file mapping\n", va);
        exit(2);
    }
    offset = (size_t)(va - FILE_VA_BASE);
    if (offset > blob->n || width > blob->n - offset) {
        fprintf(stderr, "VA 0x%08X width %zu outside input\n", va, width);
        exit(2);
    }
    return offset;
}

static uint32_t word_at(const Blob *blob, uint32_t pc)
{
    return le32p(blob->p + va_offset(blob, pc, 4));
}

static int16_t s16_at(const Blob *blob, uint32_t va)
{
    return (int16_t)le16p(blob->p + va_offset(blob, va, 2));
}

static void require_word(const Blob *blob, uint32_t pc, uint32_t expected)
{
    uint32_t actual = word_at(blob, pc);
    if (actual != expected) {
        fprintf(stderr, "instruction pin failed at 0x%08X: 0x%08X != 0x%08X\n",
                pc, actual, expected);
        exit(1);
    }
}

static int sign16(uint32_t value)
{
    return (int16_t)(value & 0xffffu);
}

static const char *control_kind(uint32_t word)
{
    uint32_t op = word >> 26;
    if (op == 3) return "direct_jal";
    if (op == 2) return "direct_j";
    if (op == 0 && (word & 0x3fu) == 9) return "jalr";
    if (op == 0 && (word & 0x3fu) == 8) return "jr";
    if (op == 1 || (op >= 4 && op <= 7)) return "conditional_branch";
    return "not_control_flow";
}

static uint32_t direct_target(uint32_t pc, uint32_t word)
{
    return ((pc + 4u) & 0xf0000000u) | ((word & 0x03ffffffu) << 2);
}

static uint32_t branch_target(uint32_t pc, uint32_t word)
{
    return pc + 4u + (uint32_t)(sign16(word) * 4);
}

/* Every instruction used by the range derivations is pinned.  The ranges
 * below are then decoded from the mask/shift/base/load spellings, not inferred
 * from runtime addresses.  Pins are intentionally redundant at shared chains:
 * one altered instruction must make the complete receipt unavailable. */
static const WordPin INSTRUCTION_PINS[] = {
    /* RotMatrix: three signed-angle normalisers, two paths apiece. */
    {0x80060860u,0x31F90FFFu},{0x8006086Cu,0x31EF0FFFu},
    {0x80060870u,0x000FC080u},{0x80060874u,0x3C198008u},
    {0x80060878u,0x0338C821u},{0x8006087Cu,0x8F39A7E4u},
    {0x80060898u,0x0019C080u},{0x8006089Cu,0x3C198008u},
    {0x800608A0u,0x0338C821u},{0x800608A4u,0x8F39A7E4u},
    {0x800608C4u,0x31F90FFFu},{0x800608D0u,0x31EF0FFFu},
    {0x800608D4u,0x000FC080u},{0x800608D8u,0x3C198008u},
    {0x800608DCu,0x0338C821u},{0x800608E0u,0x8F39A7E4u},
    {0x800608FCu,0x0019C080u},{0x80060900u,0x3C198008u},
    {0x80060904u,0x0338C821u},{0x80060908u,0x8F39A7E4u},
    {0x80060944u,0x31F90FFFu},{0x8006095Cu,0x31EF0FFFu},
    {0x80060960u,0x000FC080u},{0x80060964u,0x3C198008u},
    {0x80060968u,0x0338C821u},{0x8006096Cu,0x8F39A7E4u},
    {0x80060994u,0x0019C080u},{0x80060998u,0x3C198008u},
    {0x8006099Cu,0x0338C821u},{0x800609A0u,0x8F39A7E4u},

    /* gte_rotation_matrix_setup: base 0x80074970; byte masks 0x1ffe. */
    {0x80017B98u,0x3C068007u},{0x80017B9Cu,0x34C64970u},
    {0x80017BB4u,0x31081FFEu},{0x80017BB8u,0x31291FFEu},
    {0x80017BBCu,0x314A1FFEu},{0x80017BC0u,0x01064020u},
    {0x80017BC4u,0x01264820u},{0x80017BC8u,0x01465020u},
    {0x80017BCCu,0x850B0800u},{0x80017BD0u,0x852C0800u},
    {0x80017BD4u,0x854D0800u},{0x80017BD8u,0x85080000u},
    {0x80017BDCu,0x85290000u},{0x80017C0Cu,0x854A0000u},

    /* contact_vs_actor_handler. */
    {0x80058B7Cu,0x30420FFFu},{0x80058B80u,0x00021040u},
    {0x80058B84u,0x3C018007u},{0x80058B88u,0x00220821u},
    {0x80058B8Cu,0x94254970u},{0x80058BB0u,0x30630FFFu},
    {0x80058BB4u,0x00031840u},{0x80058BBCu,0x3C018007u},
    {0x80058BC0u,0x00230821u},{0x80058BC4u,0x94224970u},

    /* camera_follow_update. */
    {0x8004E2D8u,0x30420FFFu},{0x8004E2DCu,0x00021040u},
    {0x8004E2E0u,0x3C018007u},{0x8004E2E4u,0x00220821u},
    {0x8004E2E8u,0x84224970u},{0x8004E304u,0x30420FFFu},
    {0x8004E308u,0x00021040u},{0x8004E320u,0x3C018007u},
    {0x8004E324u,0x00220821u},{0x8004E328u,0x84224970u},
    {0x8004E33Cu,0x30420FFFu},{0x8004E340u,0x00021040u},
    {0x8004E348u,0x3C018007u},{0x8004E34Cu,0x00220821u},
    {0x8004E350u,0x84224970u},{0x8004E36Cu,0x30420FFFu},
    {0x8004E370u,0x00021040u},{0x8004E384u,0x3C018007u},
    {0x8004E388u,0x00220821u},{0x8004E38Cu,0x84224970u},
    {0x8004E740u,0x30620FFFu},{0x8004E744u,0x00021040u},
    {0x8004E748u,0x3C018007u},{0x8004E74Cu,0x00220821u},
    {0x8004E750u,0x84224970u},{0x8004E774u,0x30630FFFu},
    {0x8004E778u,0x00031840u},{0x8004E784u,0x3C018007u},
    {0x8004E788u,0x00230821u},{0x8004E78Cu,0x84224970u},
    {0x8004EA38u,0x00021080u},{0x8004EA3Cu,0x30421FFCu},
    {0x8004EA40u,0x3C018007u},{0x8004EA44u,0x00220821u},
    {0x8004EA48u,0x94224970u},

    /* player_vertical_update. */
    {0x800489B4u,0x30420FFFu},{0x800489C0u,0x00121040u},
    {0x800489C4u,0x3C018007u},{0x800489C8u,0x00220821u},
    {0x800489CCu,0x84224970u},{0x800489E0u,0x30420FFFu},
    {0x800489E4u,0x00021040u},{0x800489E8u,0x3C018007u},
    {0x800489ECu,0x00220821u},{0x800489F0u,0x84224970u},
    {0x80048A80u,0x30420FFFu},{0x80048A84u,0x00021040u},
    {0x80048A88u,0x3C018007u},{0x80048A8Cu,0x00220821u},
    {0x80048A90u,0x94224970u},{0x80048AACu,0x30420FFFu},
    {0x80048AB0u,0x00021040u},{0x80048AB4u,0x3C018007u},
    {0x80048AB8u,0x00220821u},{0x80048ABCu,0x94224970u},
    {0x800492B8u,0x30420FFFu},{0x800492BCu,0x00021040u},
    {0x800492C0u,0x3C018007u},{0x800492C4u,0x00220821u},
    {0x800492C8u,0x94224970u},{0x800492E8u,0x30420FFFu},
    {0x800492ECu,0x00021040u},{0x800492F0u,0x3C018007u},
    {0x800492F4u,0x00220821u},{0x800492F8u,0x94224970u},
    {0x800494B8u,0x30420FFFu},{0x800494BCu,0x00021040u},
    {0x800494C0u,0x3C018007u},{0x800494C4u,0x00220821u},
    {0x800494C8u,0x94224970u},{0x800494DCu,0x00031840u},
    {0x800494E0u,0x3C018007u},{0x800494E4u,0x00230821u},
    {0x800494E8u,0x94224970u},

    /* Claimed sites, real dispatch controls, and berry direct entries. */
    {0x8005BFE4u,0x0C00E392u},{0x80058EB8u,0x0C0180A1u},
    {0x8005C0ECu,0x2C62000Du},{0x8005C0F4u,0x00031080u},
    {0x8005C0F8u,0x3C018002u},{0x8005C0FCu,0x00220821u},
    {0x8005C100u,0x8C22B848u},{0x8005C108u,0x00400008u},
    {0x80058E5Cu,0x2C62000Cu},{0x80058E64u,0x00031080u},
    {0x80058E68u,0x3C018002u},{0x80058E6Cu,0x00220821u},
    {0x80058E70u,0x8C22B748u},{0x80058E78u,0x00400008u},
    {0x80058EE8u,0x1040005Cu},{0x80058F08u,0x144A0054u},
};

#define ARRAY_COUNT(a) (sizeof(a) / sizeof((a)[0]))

static const Reader PACKED_READERS[] = {
    {"RotMatrix",0x8006087Cu,"lw",PACKED_BASE,PACKED_BASE+0x4000u,4,"andi 0x0fff; sll 2; lui 0x8008; addu; lw -0x581c"},
    {"RotMatrix",0x800608A4u,"lw",PACKED_BASE,PACKED_BASE+0x4000u,4,"andi 0x0fff; sll 2; lui 0x8008; addu; lw -0x581c"},
    {"RotMatrix",0x800608E0u,"lw",PACKED_BASE,PACKED_BASE+0x4000u,4,"andi 0x0fff; sll 2; lui 0x8008; addu; lw -0x581c"},
    {"RotMatrix",0x80060908u,"lw",PACKED_BASE,PACKED_BASE+0x4000u,4,"andi 0x0fff; sll 2; lui 0x8008; addu; lw -0x581c"},
    {"RotMatrix",0x8006096Cu,"lw",PACKED_BASE,PACKED_BASE+0x4000u,4,"andi 0x0fff; sll 2; lui 0x8008; addu; lw -0x581c"},
    {"RotMatrix",0x800609A0u,"lw",PACKED_BASE,PACKED_BASE+0x4000u,4,"andi 0x0fff; sll 2; lui 0x8008; addu; lw -0x581c"},
};

#define RAW_STANDARD_LO RAW_BASE
#define RAW_STANDARD_HI (RAW_BASE + 0x2000u)
#define RAW_COS_LO      (RAW_BASE + 0x0800u)
#define RAW_COS_HI      (RAW_BASE + 0x2800u)

static const Reader RAW_READERS[] = {
    {"gte_rotation_matrix_setup",0x80017BCCu,"lh",RAW_COS_LO,RAW_COS_HI,2,"lui/ori base; sll 1 then andi 0x1ffe; +0x0800"},
    {"gte_rotation_matrix_setup",0x80017BD0u,"lh",RAW_COS_LO,RAW_COS_HI,2,"lui/ori base; sll 1 then andi 0x1ffe; +0x0800"},
    {"gte_rotation_matrix_setup",0x80017BD4u,"lh",RAW_COS_LO,RAW_COS_HI,2,"lui/ori base; sll 1 then andi 0x1ffe; +0x0800"},
    {"gte_rotation_matrix_setup",0x80017BD8u,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"lui/ori base; sll 1 then andi 0x1ffe; +0"},
    {"gte_rotation_matrix_setup",0x80017BDCu,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"lui/ori base; sll 1 then andi 0x1ffe; +0"},
    {"gte_rotation_matrix_setup",0x80017C0Cu,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"lui/ori base; sll 1 then andi 0x1ffe; +0"},
    {"contact_vs_actor_handler",0x80058B8Cu,"lhu",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lhu 0x4970"},
    {"contact_vs_actor_handler",0x80058BC4u,"lhu",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lhu 0x4970"},
    {"camera_follow_update",0x8004E2E8u,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lh 0x4970"},
    {"camera_follow_update",0x8004E328u,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lh 0x4970"},
    {"camera_follow_update",0x8004E350u,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lh 0x4970"},
    {"camera_follow_update",0x8004E38Cu,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lh 0x4970"},
    {"camera_follow_update",0x8004E750u,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lh 0x4970"},
    {"camera_follow_update",0x8004E78Cu,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lh 0x4970"},
    {"camera_follow_update",0x8004EA48u,"lhu",RAW_STANDARD_LO,RAW_BASE+0x1FFEu,2,"sll 2; andi 0x1ffc; lui 0x8007; addu; lhu 0x4970"},
    {"player_vertical_update",0x800489CCu,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lh 0x4970"},
    {"player_vertical_update",0x800489F0u,"lh",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lh 0x4970"},
    {"player_vertical_update",0x80048A90u,"lhu",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lhu 0x4970"},
    {"player_vertical_update",0x80048ABCu,"lhu",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lhu 0x4970"},
    {"player_vertical_update",0x800492C8u,"lhu",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lhu 0x4970"},
    {"player_vertical_update",0x800492F8u,"lhu",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lhu 0x4970"},
    {"player_vertical_update",0x800494C8u,"lhu",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lhu 0x4970"},
    {"player_vertical_update",0x800494E8u,"lhu",RAW_STANDARD_LO,RAW_STANDARD_HI,2,"andi 0x0fff; sll 1; lui 0x8007; addu; lhu 0x4970"},
};

static void validate_reader_words(const Blob *blob, const Reader *rows, size_t count)
{
    size_t i;
    for (i = 0; i < count; i++) {
        uint32_t word = word_at(blob, rows[i].pc);
        uint32_t op = word >> 26;
        uint32_t width = (op == 0x23u) ? 4u :
                         ((op == 0x21u || op == 0x25u) ? 2u : 0u);
        const char *mnemonic = op == 0x23u ? "lw" :
                               (op == 0x21u ? "lh" :
                               (op == 0x25u ? "lhu" : "other"));
        if (width != rows[i].width || strcmp(mnemonic, rows[i].mnemonic) != 0 ||
            rows[i].range_hi <= rows[i].range_lo) {
            fprintf(stderr, "reader decode failed at 0x%08X\n", rows[i].pc);
            exit(1);
        }
    }
}

static int raw_expected(unsigned index)
{
    double pi = acos(-1.0);
    return (int)llround((double)RAW_AMPLITUDE *
                        sin(2.0 * pi * (double)index / 4096.0));
}

static int packed_component_expected(unsigned source)
{
    unsigned phase = source + (((source & 4095u) >> 10) & 1u);
    double pi = acos(-1.0);
    return (int)llround((double)PACKED_AMPLITUDE *
                        sin(2.0 * pi * (double)phase / 4096.0));
}

static unsigned compare_raw(const Blob *blob, unsigned first, unsigned count,
                            uint32_t va, uint32_t *first_bad)
{
    unsigned i, bad = 0;
    for (i = 0; i < count; i++) {
        int actual = s16_at(blob, va + i * RAW_STRIDE);
        int expected = raw_expected(first + i);
        if (actual != expected) {
            if (bad == 0) *first_bad = va + i * RAW_STRIDE;
            bad++;
        }
    }
    return bad;
}

static unsigned compare_packed(const Blob *blob, unsigned first, unsigned count,
                               uint32_t va, uint32_t *first_bad)
{
    unsigned i, bad = 0;
    for (i = 0; i < count; i++) {
        unsigned index = first + i;
        int actual_lo = s16_at(blob, va + i * PACKED_STRIDE);
        int actual_hi = s16_at(blob, va + i * PACKED_STRIDE + 2u);
        int expected_lo = packed_component_expected(index);
        int expected_hi = packed_component_expected(index + 1024u);
        if (actual_lo != expected_lo || actual_hi != expected_hi) {
            if (bad == 0) *first_bad = va + i * PACKED_STRIDE;
            bad++;
        }
    }
    return bad;
}

static void print_readers(const Reader *rows, size_t count)
{
    size_t i;
    printf("[");
    for (i = 0; i < count; i++) {
        printf("%s{\"function\":\"%s\",\"pc\":\"0x%08X\","
               "\"mnemonic\":\"%s\",\"width\":%u,"
               "\"effective_address_range\":[\"0x%08X\",\"0x%08X\"],"
               "\"range_semantics\":\"half_open_byte_range\","
               "\"instruction_derivation\":\"%s\"}",
               i ? "," : "", rows[i].function, rows[i].pc,
               rows[i].mnemonic, rows[i].width, rows[i].range_lo,
               rows[i].range_hi, rows[i].derivation);
    }
    printf("]");
}

static void print_table_entries(const Blob *blob, uint32_t table, unsigned count)
{
    unsigned i;
    printf("[");
    for (i = 0; i < count; i++) {
        uint32_t target = word_at(blob, table + i * 4u);
        printf("%s{\"index\":%u,\"target\":\"0x%08X\"}",
               i ? "," : "", i, target);
    }
    printf("]");
}

static int target_in_table(const Blob *blob, uint32_t table, unsigned count,
                           uint32_t target)
{
    unsigned i;
    for (i = 0; i < count; i++)
        if (word_at(blob, table + i * 4u) == target) return 1;
    return 0;
}

int main(int argc, char **argv)
{
    Blob blob;
    size_t i;
    uint32_t first_bad_raw = 0, first_bad_raw_gap = 0;
    uint32_t first_bad_packed = 0, first_bad_packed_gap = 0;
    unsigned raw_bad, raw_gap_bad, packed_bad, packed_gap_bad;
    uint32_t claimed_plant, claimed_berry;
    uint32_t plant_table = 0x8001B848u, contact_table = 0x8001B748u;
    unsigned plant_count = 13u, contact_count = 12u;

    if (argc != 2) {
        fprintf(stderr, "usage: %s REBUILD/files/SCUS_942.88\n", argv[0]);
        return 2;
    }
    blob = slurp(argv[1]);
    if (blob.n < HEADER_SIZE || memcmp(blob.p, "PS-X EXE", 8) != 0 ||
        le32p(blob.p + 0x18) != LOAD_ADDRESS || le32p(blob.p + 0x1c) != TEXT_SIZE) {
        fprintf(stderr, "input is not the pinned-layout resident PS-X EXE\n");
        free(blob.p);
        return 1;
    }
    if (blob.n != HEADER_SIZE + TEXT_SIZE) {
        fprintf(stderr, "resident file size %zu != %u\n", blob.n,
                HEADER_SIZE + TEXT_SIZE);
        free(blob.p);
        return 1;
    }
    for (i = 0; i < ARRAY_COUNT(INSTRUCTION_PINS); i++)
        require_word(&blob, INSTRUCTION_PINS[i].pc, INSTRUCTION_PINS[i].word);
    validate_reader_words(&blob, PACKED_READERS, ARRAY_COUNT(PACKED_READERS));
    validate_reader_words(&blob, RAW_READERS, ARRAY_COUNT(RAW_READERS));

    raw_bad = compare_raw(&blob, 0, RAW_ENTRIES, RAW_BASE, &first_bad_raw);
    raw_gap_bad = compare_raw(&blob, (RAW_GAP_LO - RAW_BASE) / RAW_STRIDE,
                              (RAW_GAP_HI - RAW_GAP_LO) / RAW_STRIDE,
                              RAW_GAP_LO, &first_bad_raw_gap);
    packed_bad = compare_packed(&blob, 0, PACKED_ENTRIES, PACKED_BASE,
                                &first_bad_packed);
    packed_gap_bad = compare_packed(&blob,
                                    (PACKED_GAP_LO - PACKED_BASE) / PACKED_STRIDE,
                                    (PACKED_GAP_HI - PACKED_GAP_LO) / PACKED_STRIDE,
                                    PACKED_GAP_LO, &first_bad_packed_gap);

    claimed_plant = word_at(&blob, 0x8005BFE4u);
    claimed_berry = word_at(&blob, 0x80058EB8u);
    if (strcmp(control_kind(claimed_plant), "direct_jal") != 0 ||
        strcmp(control_kind(claimed_berry), "direct_jal") != 0 ||
        direct_target(0x8005BFE4u, claimed_plant) != 0x80038E48u ||
        direct_target(0x80058EB8u, claimed_berry) != 0x80060284u ||
        branch_target(0x80058EE8u, word_at(&blob, 0x80058EE8u)) != 0x8005905Cu ||
        branch_target(0x80058F08u, word_at(&blob, 0x80058F08u)) != 0x8005905Cu) {
        fprintf(stderr, "dispatch/control decode did not reproduce pinned facts\n");
        free(blob.p);
        return 1;
    }

    printf("{\n");
    printf(" \"schema\":\"abl-phase4-f01-static-hard-truth-c/1\",\n");
    printf(" \"image_layout\":{\"format\":\"PS-X EXE\","
           "\"load_address\":\"0x%08X\",\"text_size\":%u,"
           "\"file_va_base\":\"0x%08X\",\"instruction_pins_checked\":%zu},\n",
           LOAD_ADDRESS, TEXT_SIZE, FILE_VA_BASE, ARRAY_COUNT(INSTRUCTION_PINS));
    printf(" \"trigonometric_tables\":[\n");
    printf("  {\"id\":\"q14_sine_4096_plus_quadrature_tail\","
           "\"image\":\"SCUS_942_88\",\"base\":\"0x%08X\","
           "\"end\":\"0x%08X\",\"entry_count\":%u,\"stride_bytes\":%u,"
           "\"entry_encoding\":\"little-endian signed 16-bit\","
           "\"amplitude\":%d,\"period_entries\":4096,"
           "\"formula\":\"llround(16384*sin(2*pi*i/4096)) for i=0..5119\","
           "\"content_comparison\":{\"mismatched_entries\":%u,"
           "\"first_mismatch\":%s},"
           "\"gap\":{\"start\":\"0x%08X\",\"end\":\"0x%08X\","
           "\"byte_count\":%u,\"first_entry\":%u,\"entry_count\":%u,"
           "\"mismatched_entries\":%u,\"first_mismatch\":%s},\"readers\":",
           RAW_BASE, RAW_BASE + RAW_ENTRIES * RAW_STRIDE, RAW_ENTRIES, RAW_STRIDE,
           RAW_AMPLITUDE, raw_bad, first_bad_raw ? "\"set\"" : "null",
           RAW_GAP_LO, RAW_GAP_HI, RAW_GAP_HI - RAW_GAP_LO,
           (RAW_GAP_LO - RAW_BASE) / RAW_STRIDE,
           (RAW_GAP_HI - RAW_GAP_LO) / RAW_STRIDE,
           raw_gap_bad, first_bad_raw_gap ? "\"set\"" : "null");
    print_readers(RAW_READERS, ARRAY_COUNT(RAW_READERS));
    printf("},\n");
    printf("  {\"id\":\"q12_packed_rotmatrix_sine_phase_pair\","
           "\"image\":\"SCUS_942_88\",\"base\":\"0x%08X\","
           "\"end\":\"0x%08X\",\"entry_count\":%u,\"stride_bytes\":%u,"
           "\"entry_encoding\":\"little-endian word: signed 16-bit low plus signed 16-bit high\","
           "\"amplitude\":%d,\"period_entries\":4096,"
           "\"formula\":\"f(j)=llround(4096*sin(2*pi*(j+(((j mod 4096)>>10)&1))/4096)); entry i=(f(i),f(i+1024))\","
           "\"content_comparison\":{\"mismatched_entries\":%u,"
           "\"first_mismatch\":%s},"
           "\"gap\":{\"start\":\"0x%08X\",\"end\":\"0x%08X\","
           "\"byte_count\":%u,\"first_entry\":%u,\"entry_count\":%u,"
           "\"mismatched_entries\":%u,\"first_mismatch\":%s},\"readers\":",
           PACKED_BASE, PACKED_BASE + PACKED_ENTRIES * PACKED_STRIDE,
           PACKED_ENTRIES, PACKED_STRIDE, PACKED_AMPLITUDE, packed_bad,
           first_bad_packed ? "\"set\"" : "null", PACKED_GAP_LO, PACKED_GAP_HI,
           PACKED_GAP_HI - PACKED_GAP_LO,
           (PACKED_GAP_LO - PACKED_BASE) / PACKED_STRIDE,
           (PACKED_GAP_HI - PACKED_GAP_LO) / PACKED_STRIDE,
           packed_gap_bad, first_bad_packed_gap ? "\"set\"" : "null");
    print_readers(PACKED_READERS, ARRAY_COUNT(PACKED_READERS));
    printf("}\n ],\n");

    printf(" \"requested_dispatch_sites\":[\n");
    printf("  {\"pc\":\"0x8005BFE4\",\"function\":\"plant_behavior_walker\","
           "\"instruction_word\":\"0x%08X\",\"decoded_kind\":\"%s\","
           "\"direct_target\":\"0x%08X\",\"claimed_runtime_target\":\"0x8005C58C\","
           "\"target_set_proved\":false,\"fail_closed_reason\":"
           "\"blocking instruction is direct jal 0x80038E48, not jalr; no target set exists at this PC\"},\n",
           claimed_plant, control_kind(claimed_plant),
           direct_target(0x8005BFE4u, claimed_plant));
    printf("  {\"pc\":\"0x80058EB8\",\"function\":\"contact_vs_actor_handler\","
           "\"instruction_word\":\"0x%08X\",\"decoded_kind\":\"%s\","
           "\"direct_target\":\"0x%08X\",\"claimed_runtime_target\":\"0x8005905C\","
           "\"target_set_proved\":false,\"fail_closed_reason\":"
           "\"blocking instruction is direct jal 0x80060284, not jalr; no target set exists at this PC\"}\n ],\n",
           claimed_berry, control_kind(claimed_berry),
           direct_target(0x80058EB8u, claimed_berry));

    printf(" \"actual_dispatch_controls\":[\n");
    printf("  {\"pc\":\"0x8005C108\",\"function\":\"plant_behavior_walker\","
           "\"decoded_kind\":\"jr\",\"table\":\"0x%08X\","
           "\"stride_bytes\":4,\"index_domain\":[0,12],"
           "\"bound_instruction\":{\"pc\":\"0x8005C0EC\","
           "\"word\":\"0x2C62000D\",\"meaning\":\"sltiu v0,v1,13 gates the table load\"},"
           "\"target_set_complete\":true,\"entries\":", plant_table);
    print_table_entries(&blob, plant_table, plant_count);
    printf(",\"observed_target\":\"0x8005C58C\",\"observed_target_is_member\":%s},\n",
           target_in_table(&blob, plant_table, plant_count, 0x8005C58Cu) ? "true" : "false");
    printf("  {\"pc\":\"0x80058E78\",\"function\":\"contact_vs_actor_handler\","
           "\"decoded_kind\":\"jr\",\"table\":\"0x%08X\","
           "\"stride_bytes\":4,\"index_domain\":[0,11],"
           "\"bound_instruction\":{\"pc\":\"0x80058E5C\","
           "\"word\":\"0x2C62000C\",\"meaning\":\"sltiu v0,v1,12 gates the table load\"},"
           "\"target_set_complete\":true,\"entries\":", contact_table);
    print_table_entries(&blob, contact_table, contact_count);
    printf(",\"observed_target\":\"0x8005905C\",\"observed_target_is_member\":%s},\n",
           target_in_table(&blob, contact_table, contact_count, 0x8005905Cu) ? "true" : "false");
    printf("  {\"target\":\"0x8005905C\",\"actual_entry_edges\":["
           "{\"pc\":\"0x80058EE8\",\"kind\":\"conditional_branch\"},"
           "{\"pc\":\"0x80058F08\",\"kind\":\"conditional_branch\"}],"
           "\"explanation\":\"the helper jal at 0x80058EB8 leaves ra=0x80058EC0; later branches enter the handler without relinking, so an entry-time ra-8 attribution names the helper call rather than the true edge\"}\n ],\n");
    printf(" \"verdicts\":{\"instruction_evidence_complete\":true,"
           "\"raw_table_content_match\":%s,\"packed_table_content_match\":%s,"
           "\"trig_semantic_disposition_supported\":%s,"
           "\"requested_dispatch_sets_proved\":false,"
           "\"requested_dispatches_fail_closed\":true,"
           "\"new_indirect_target_sets_to_register\":0}\n",
           raw_bad == 0 && raw_gap_bad == 0 ? "true" : "false",
           packed_bad == 0 && packed_gap_bad == 0 ? "true" : "false",
           raw_bad == 0 && raw_gap_bad == 0 && packed_bad == 0 && packed_gap_bad == 0
               ? "true" : "false");
    printf("}\n");

    free(blob.p);
    return (raw_bad || raw_gap_bad || packed_bad || packed_gap_bad) ? 1 : 0;
}
