/*
 * Phase 4 D09 Redbug static closure guard.
 *
 * Reads only the hash-pinned pristine retail executable. It verifies the
 * Redbug program binding and the resident shared damage, chase, KO, and
 * respawn paths, then emits the complete executable-wide actor+0x5c access
 * candidate census for future attribution work.
 *
 * Build:
 *   cc -std=c11 -O2 -Wall -Wextra tools/phase4_d09_static.c \
 *      -lcrypto -o /tmp/phase4_d09_static
 * Run:
 *   /tmp/phase4_d09_static SCUS_942.88
 */
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_SHA256 "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
#define EXE_FILE_BASE UINT32_C(0x8000f800)

struct check {
    uint32_t pc;
    uint32_t word;
    const char *meaning;
};

static const struct check checks[] = {
    {0x8004c930, 0x9602005c, "motion phase loads actor flags"},
    {0x8004c938, 0x30420002, "motion phase isolates chase bit 0x2"},
    {0x8004c93c, 0x10400059, "clear chase bit skips player-goal substitution"},
    {0x8004c940, 0x2ac20003, "chase is limited to parked modes below three"},
    {0x8004c944, 0x10400057, "ineligible mode skips player-goal substitution"},
    {0x80058df4, 0x9642005c, "projectile path loads resistance flags"},
    {0x80058dfc, 0x30420040, "projectile path isolates berry-tough bit 0x40"},
    {0x80058e00, 0x1440011f, "berry-tough path branches away from ordinary damage"},
    {0x8005905c, 0x8642006e, "common damage path loads signed HP"},
    {0x800590c4, 0x2482fffe, "marker zero applies minus two"},
    {0x800590cc, 0x2482fffe, "marker twelve applies minus two"},
    {0x800590d4, 0x2482fffc, "marker 127 applies minus four"},
    {0x800590e0, 0x2442ffff, "default marker applies minus one"},
    {0x800590e4, 0xa642006e, "common damage path stores HP"},
    {0x8005914c, 0x34420002, "eligible hit sets chase bit 0x2"},
    {0x80059150, 0xa642005c, "eligible hit stores flags"},
    {0x80059154, 0x8642006e, "post-hit path reloads HP"},
    {0x8005915c, 0x1c40002f, "positive HP bypasses KO tail"},
    {0x800592a0, 0x240203e7, "temporary KO sentinel is 999"},
    {0x800592a8, 0xa642006e, "KO tail stores sentinel"},
    {0x800592b0, 0x34630880, "KO tail adds flags 0x0880"},
    {0x800592b4, 0x3063fffd, "KO tail clears chase bit"},
    {0x800592b8, 0xa643005c, "KO tail stores flags"},
    {0x800592c8, 0xae420070, "KO tail redirects mover program"},
    {0x800592d0, 0x1440001b, "temporary class bypasses permanent effect/quota block"},
    {0x80059340, 0x0c01262b, "KO tail calls actor retirement routine"},
    {0x80059344, 0x24050001, "retirement call uses mode one"}
};

static const uint16_t redbug_program[] = {
    0x0016, 0x0040, 0xffc0,
    0x000d, 0x0000, 0x0001,
    0x0002, 0x003f, 0x0020,
    0x0003, 0x0005,
    0xffff, 0x0005,
    0x0000
};

static void fail(const char *message)
{
    fprintf(stderr, "phase4_d09_static: %s\n", message);
    exit(2);
}

static uint16_t le16(const uint8_t *p)
{
    return (uint16_t)(p[0] | (uint16_t)p[1] << 8);
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static size_t file_offset(size_t size, uint32_t address, size_t width)
{
    if (address < EXE_FILE_BASE)
        fail("guest address precedes executable mapping");
    size_t offset = (size_t)(address - EXE_FILE_BASE);
    if (offset > size || width > size - offset)
        fail("guest address lies outside executable");
    return offset;
}

static uint32_t jal_target(uint32_t pc, uint32_t word)
{
    return ((pc + 4) & UINT32_C(0xf0000000)) |
           ((word & UINT32_C(0x03ffffff)) << 2);
}

static int is_flags_read(uint32_t word)
{
    uint32_t op = word >> 26;
    return (word & UINT32_C(0xffff)) == UINT32_C(0x005c) &&
           (op == 0x21 || op == 0x23 || op == 0x25);
}

static int is_flags_write(uint32_t word)
{
    uint32_t op = word >> 26;
    return (word & UINT32_C(0xffff)) == UINT32_C(0x005c) &&
           (op == 0x29 || op == 0x2b);
}

static size_t count_accesses(const uint8_t *data, size_t size, int write)
{
    size_t count = 0;
    for (size_t off = 0x800; off + 4 <= size; off += 4) {
        uint32_t word = le32(data + off);
        if (write ? is_flags_write(word) : is_flags_read(word))
            ++count;
    }
    return count;
}

static void print_accesses(const uint8_t *data, size_t size, int write)
{
    int first = 1;
    putchar('[');
    for (size_t off = 0x800; off + 4 <= size; off += 4) {
        uint32_t word = le32(data + off);
        if (!(write ? is_flags_write(word) : is_flags_read(word)))
            continue;
        uint32_t pc = EXE_FILE_BASE + (uint32_t)off;
        printf("%s\"0x%08" PRIx32 "\"", first ? "" : ",", pc);
        first = 0;
    }
    putchar(']');
}

static size_t count_direct_calls(const uint8_t *data, size_t size, uint32_t target)
{
    size_t count = 0;
    for (size_t off = 0x800; off + 4 <= size; off += 4) {
        uint32_t word = le32(data + off);
        uint32_t pc = EXE_FILE_BASE + (uint32_t)off;
        if ((word >> 26) == 3 && jal_target(pc, word) == target)
            ++count;
    }
    return count;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
        return 2;
    }
    FILE *fp = fopen(argv[1], "rb");
    if (!fp) fail("cannot open executable");
    if (fseek(fp, 0, SEEK_END) != 0) fail("cannot seek executable");
    long signed_size = ftell(fp);
    if (signed_size < 0 || fseek(fp, 0, SEEK_SET) != 0)
        fail("cannot size executable");
    size_t size = (size_t)signed_size;
    uint8_t *data = malloc(size ? size : 1);
    if (!data || fread(data, 1, size, fp) != size)
        fail("cannot read executable");
    fclose(fp);

    unsigned char digest[SHA256_DIGEST_LENGTH];
    char hash[65];
    static const char digits[] = "0123456789abcdef";
    SHA256(data, size, digest);
    for (size_t i = 0; i < sizeof(digest); ++i) {
        hash[i * 2] = digits[digest[i] >> 4];
        hash[i * 2 + 1] = digits[digest[i] & 15];
    }
    hash[64] = '\0';
    if (strcmp(hash, EXPECTED_SHA256) != 0)
        fail("input is not the hash-pinned pristine executable");
    if (size < 0x800 || memcmp(data, "PS-X EXE", 8) != 0)
        fail("invalid PS-X EXE header");
    if (le32(data + 0x18) != UINT32_C(0x80010000) ||
        le32(data + 0x1c) != UINT32_C(0x00072800))
        fail("unexpected executable mapping");

    for (size_t i = 0; i < sizeof(checks) / sizeof(checks[0]); ++i) {
        uint32_t actual = le32(data + file_offset(size, checks[i].pc, 4));
        if (actual != checks[i].word) {
            fprintf(stderr, "anchor mismatch at 0x%08" PRIx32 " (%s)\n",
                    checks[i].pc, checks[i].meaning);
            return 1;
        }
    }

    uint32_t pointer_pc = UINT32_C(0x80077af8) + 12 * 4;
    if (le32(data + file_offset(size, pointer_pc, 4)) != UINT32_C(0x80077690))
        fail("program table entry 12 is not Redbug program 0x80077690");
    const uint8_t *program = data + file_offset(size, UINT32_C(0x80077690),
                                                sizeof(redbug_program));
    for (size_t i = 0; i < sizeof(redbug_program) / sizeof(redbug_program[0]); ++i)
        if (le16(program + i * 2) != redbug_program[i])
            fail("Redbug mover program differs");

    uint32_t reinit_call = le32(data + file_offset(size, UINT32_C(0x8004d3f0), 4));
    if ((reinit_call >> 26) != 3 ||
        jal_target(UINT32_C(0x8004d3f0), reinit_call) != UINT32_C(0x80049c30))
        fail("runtime KO reinitializer call differs");
    uint32_t hp_restore = le32(data + file_offset(size, UINT32_C(0x80049ca0), 4));
    uint32_t delay_seed = le32(data + file_offset(size, UINT32_C(0x80049cc0), 4));
    if ((hp_restore >> 26) != 0x29 || (hp_restore & 0xffff) != 0x006e)
        fail("reinitializer HP store differs");
    if ((delay_seed >> 26) != 0x29 || (delay_seed & 0xffff) != 0x0062)
        fail("reinitializer delay store differs");

    size_t reads = count_accesses(data, size, 0);
    size_t writes = count_accesses(data, size, 1);
    printf("{\n");
    printf("  \"schema\": \"abl.phase4.d09.static.v1\",\n");
    printf("  \"row\": \"D09_cockroaches_redbug\",\n");
    printf("  \"status\": \"verified\",\n");
    printf("  \"input\": {\"path\": \"%s\", \"sha256\": \"%s\"},\n", argv[1], hash);
    printf("  \"anchors_checked\": %zu,\n", sizeof(checks) / sizeof(checks[0]) + 5);
    printf("  \"identity\": {\"actor_id\": 19, \"program_table_index\": 12, \"program\": \"0x80077690\", \"program_shape\": [\"set_byte_params[64,-64]\",\"anim_clip_load[0,1]\",\"wait_random[63,32]\",\"random_dir_step\",\"park_seek\",\"jump_back[5]\"]},\n");
    printf("  \"damage\": {\"common_hp_load\": \"0x8005905c\", \"common_hp_store\": \"0x800590e4\", \"chase_setter\": \"0x8005914c\", \"berry_tough_mask\": \"0x0040\"},\n");
    printf("  \"chase\": {\"gate\": \"0x8004c930\", \"required_flag\": \"0x0002\", \"mode_limit\": 3, \"redbug_program_contains_flag_write\": false, \"redbug_program_contains_literal_0x1000\": false},\n");
    printf("  \"temporary_ko\": {\"sentinel\": 999, \"flags_or\": \"0x0880\", \"flags_clear\": \"0x0002\", \"retirement_call\": \"0x800498ac(actor,1)\", \"permanent_effect_quota_block_bypassed\": true},\n");
    printf("  \"respawn\": {\"scheduler_call\": \"0x8004d3f0 -> 0x80049c30\", \"hp_restore\": \"0x80049ca0\", \"delay_seed\": \"0x80049cc0\"},\n");
    printf("  \"direct_call_counts\": {\"0x800498ac\": %zu, \"0x80049c30\": %zu},\n",
           count_direct_calls(data, size, UINT32_C(0x800498ac)),
           count_direct_calls(data, size, UINT32_C(0x80049c30)));
    printf("  \"flags_frontier\": {\"candidate_reads\": %zu, \"candidate_writes\": %zu, \"read_pcs\": ", reads, writes);
    print_accesses(data, size, 0);
    printf(", \"write_pcs\": ");
    print_accesses(data, size, 1);
    printf("},\n");
    printf("  \"conclusion\": \"Redbug is data-driven through resident shared actor machinery; its own mover program is a pure wander loop, accepted hits set bit 0x2, and only bit 0x2 gates player-goal substitution. Bit 0x1000 is not a Redbug-program chase latch.\"\n");
    printf("}\n");
    free(data);
    return 0;
}
