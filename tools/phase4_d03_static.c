#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint32_t pc;
    uint32_t word;
    const char *meaning;
} Anchor;

static void fail(const char *message)
{
    fprintf(stderr, "phase4_d03_static: %s\n", message);
    exit(1);
}

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t iword(unsigned op, unsigned rs, unsigned rt, int imm)
{
    return (op << 26) | (rs << 21) | (rt << 16) | (uint16_t)imm;
}

static uint32_t rword(unsigned rs, unsigned rt, unsigned rd,
                      unsigned shift, unsigned function)
{
    return (rs << 21) | (rt << 16) | (rd << 11) |
           (shift << 6) | function;
}

static uint32_t jword(unsigned op, uint32_t address)
{
    return (op << 26) | ((address >> 2) & 0x03ffffffu);
}

static uint32_t branch_target(uint32_t pc, uint32_t word)
{
    return pc + 4u + (uint32_t)((int32_t)(int16_t)word * 4);
}

static uint32_t jump_target(uint32_t pc, uint32_t word)
{
    return ((pc + 4u) & 0xf0000000u) | ((word & 0x03ffffffu) << 2);
}

static unsigned char *read_all(const char *path, size_t *size_out)
{
    FILE *f = fopen(path, "rb");
    if (!f || fseek(f, 0, SEEK_END) != 0)
        fail("cannot open input");
    long end = ftell(f);
    if (end < 0 || fseek(f, 0, SEEK_SET) != 0)
        fail("cannot size input");
    size_t size = (size_t)end;
    unsigned char *data = malloc(size ? size : 1);
    if (!data || fread(data, 1, size, f) != size)
        fail("cannot read input");
    fclose(f);
    *size_out = size;
    return data;
}

static void sha256_hex(const unsigned char *data, size_t size, char out[65])
{
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    unsigned char digest[32];
    unsigned int n = 0;
    if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
        EVP_DigestUpdate(ctx, data, size) != 1 ||
        EVP_DigestFinal_ex(ctx, digest, &n) != 1 || n != 32)
        fail("SHA-256 failed");
    EVP_MD_CTX_free(ctx);
    for (size_t i = 0; i < 32; ++i)
        sprintf(out + i * 2, "%02x", digest[i]);
    out[64] = '\0';
}

static uint32_t word_at(const unsigned char *exe, size_t size, uint32_t pc)
{
    if (pc < 0x80010000u)
        fail("PC below executable load address");
    size_t off = 0x800u + (size_t)(pc - 0x80010000u);
    if (off + 4 > size)
        fail("PC outside executable");
    return le32(exe + off);
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "SCUS_942.88";
    const char *expected_sha =
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20";
    size_t size = 0;
    unsigned char *exe = read_all(path, &size);
    char sha[65];
    sha256_hex(exe, size, sha);
    if (size != 471040 || memcmp(exe, "PS-X EXE", 8) != 0 ||
        le32(exe + 0x18) != 0x80010000u || strcmp(sha, expected_sha) != 0)
        fail("pristine executable identity mismatch");

    const Anchor anchors[] = {
        {0x8004853c, iword(0x21, 17, 2, 0x92), "load signed stagger timer"},
        {0x80048544, iword(0x06, 2, 0, 3), "positive-timer presentation gate"},
        {0x80048570, iword(0x09, 2, 2, -1), "positive timer approaches zero"},
        {0x80048578, iword(0x29, 17, 2, 0x92), "store positive timer tick"},
        {0x800485dc, iword(0x01, 2, 1, 16), "negative-timer direction gate"},
        {0x800485e8, iword(0x09, 4, 2, 1), "negative timer approaches zero"},
        {0x800485f0, iword(0x29, 17, 2, 0x92), "store negative timer tick"},
        {0x80049718, iword(0x21, 17, 2, 0x7e), "outer power-slot gate"},
        {0x80049728, iword(0x21, 17, 2, 0x92), "outer stagger gate"},
        {0x80049740, jword(3, 0x8004a700), "ordinary world-contact caller"},
        {0x8004a73c, iword(0x05, 20, 0, 0x3a), "nonzero kind bypasses ordinary lane"},
        {0x8004a750, rword(0, 18, 3, 0, 0x23), "negate collision Z input"},
        {0x8004a758, rword(2, 19, 2, 0, 0x23), "collision X input with bias"},
        {0x8004a75c, jword(3, 0x80060284), "normalize collision vector"},
        {0x8004a76c, rword(0, 2, 2, 2, 0x03), "quarter normalized X"},
        {0x8004a774, iword(0x2b, 1, 2, 0x652c), "write player velocity X"},
        {0x8004a784, rword(0, 2, 2, 2, 0x03), "quarter normalized Z"},
        {0x8004a78c, iword(0x2b, 1, 2, 0x6534), "write player velocity Z"},
        {0x8004a790, iword(0x07, 3, 0, 0x21), "positive stagger suppresses damage"},
        {0x8004a7a4, iword(0x21, 3, 3, 0x657e), "load signed power slot"},
        {0x8004a7b4, iword(0x05, 3, 0, 8), "nonzero power intercept"},
        {0x8004a7c8, iword(0x04, 3, 17, 3), "region one intercept"},
        {0x8004a7d0, iword(0x05, 3, 2, 0x15), "region five intercept"},
        {0x8004a7e8, iword(0x01, 2, 1, 8), "bubble sign split"},
        {0x8004a7fc, iword(0x05, 2, 0, 7), "existing stagger preserves bubble hit"},
        {0x8004a804, iword(0x09, 3, 2, 1), "consume one bubble hit toward zero"},
        {0x8004a80c, iword(0x09, 0, 2, -30), "intercept stagger value"},
        {0x8004a814, iword(0x29, 1, 2, 0x6592), "store intercept stagger"},
        {0x8004a828, iword(0x04, 17, 0, 0x79), "protected damage gate"},
        {0x8004a844, iword(0x25, 3, 3, 0x6594), "load true health"},
        {0x8004a84c, iword(0x29, 1, 2, 0x6580), "set hit state five"},
        {0x8004a850, iword(0x09, 0, 2, -1024), "vertical launch constant"},
        {0x8004a85c, iword(0x2b, 1, 2, 0x6530), "write vertical velocity"},
        {0x8004a864, iword(0x29, 1, 0, 0x6584), "clear air timer"},
        {0x8004a86c, iword(0x29, 1, 0, 0x6582), "clear ground contact"},
        {0x8004a874, iword(0x29, 1, 0, 0x6586), "clear player substate"},
        {0x8004a87c, iword(0x29, 1, 0, 0x659e), "clear interaction latch"},
        {0x8004a880, iword(0x09, 3, 3, -1), "flat health decrement"},
        {0x8004a888, iword(0x29, 1, 3, 0x6594), "store true health"},
        {0x8004a904, jword(2, 0x8004aa08), "surviving-hit timer tail"},
        {0x8004a908, iword(0x09, 0, 2, 45), "surviving stagger value"},
        {0x8004aa0c, iword(0x29, 1, 2, 0x6592), "store final signed timer"},
        {0x8004ac7c, iword(0x21, 17, 2, 0x64), "broad hitbox X offset"},
        {0x8004ac9c, iword(0x21, 17, 2, 0x66), "broad hitbox Y offset"},
        {0x8004acbc, iword(0x21, 17, 2, 0x68), "broad hitbox Z offset"},
        {0x8004acd8, iword(0x21, 17, 2, 0x6a), "broad hitbox radius"},
        {0x8004ace0, iword(0x09, 2, 2, 250), "player-radius expansion"},
        {0x8004acfc, iword(0x04, 2, 0, 0x25f), "broad sphere reject"},
        {0x8004ad04, iword(0x21, 17, 13, 0x6c), "actor reaction lockout"},
        {0x8004ad0c, iword(0x01, 13, 0, 0x25b), "negative reaction rejects contact"},
        {0x8004ae68, iword(0x21, 5, 2, 0x0e), "pose-local ellipsoid radius"},
        {0x8004ae70, iword(0x09, 2, 2, 250), "pose-radius expansion"},
        {0x8004ae8c, iword(0x04, 2, 0, 0x1fb), "oriented ellipsoid reject"},
        {0x8004b4a0, jword(3, 0x8004a700), "actor body-contact caller"},
        {0x80058a48, jword(3, 0x8004a700), "contact-object caller"},
        {0x8005c9f8, jword(3, 0x8004a700), "mine contact caller"}
    };
    for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); ++i) {
        uint32_t got = word_at(exe, size, anchors[i].pc);
        if (got != anchors[i].word) {
            fprintf(stderr, "anchor mismatch at 0x%08x (%s): %08x != %08x\n",
                    anchors[i].pc, anchors[i].meaning, got, anchors[i].word);
            return 1;
        }
    }

    const uint32_t expected_callers[] = {
        0x800496b0, 0x80049740, 0x80049868,
        0x8004b4a0, 0x80058a48, 0x8005c9f8
    };
    uint32_t found[16];
    size_t found_count = 0;
    for (size_t off = 0x800; off + 4 <= size; off += 4) {
        uint32_t pc = 0x80010000u + (uint32_t)(off - 0x800u);
        uint32_t word = le32(exe + off);
        if ((word >> 26) == 3 && jump_target(pc, word) == 0x8004a700u) {
            if (found_count >= sizeof(found) / sizeof(found[0]))
                fail("too many damage-handler callers");
            found[found_count++] = pc;
        }
    }
    if (found_count != sizeof(expected_callers) / sizeof(expected_callers[0]) ||
        memcmp(found, expected_callers, sizeof(expected_callers)) != 0)
        fail("damage-handler caller census changed");

    if (branch_target(0x8004a73c, word_at(exe, size, 0x8004a73c)) != 0x8004a828 ||
        branch_target(0x8004a790, word_at(exe, size, 0x8004a790)) != 0x8004a818 ||
        branch_target(0x8004a7b4, word_at(exe, size, 0x8004a7b4)) != 0x8004a7d8 ||
        branch_target(0x8004a7c8, word_at(exe, size, 0x8004a7c8)) != 0x8004a7d8 ||
        branch_target(0x8004a7d0, word_at(exe, size, 0x8004a7d0)) != 0x8004a828 ||
        branch_target(0x8004a7e8, word_at(exe, size, 0x8004a7e8)) != 0x8004a80c ||
        branch_target(0x8004a7fc, word_at(exe, size, 0x8004a7fc)) != 0x8004a81c ||
        branch_target(0x8004a828, word_at(exe, size, 0x8004a828)) != 0x8004aa10 ||
        branch_target(0x8004acfc, word_at(exe, size, 0x8004acfc)) != 0x8004b67c ||
        branch_target(0x8004ae8c, word_at(exe, size, 0x8004ae8c)) != 0x8004b67c)
        fail("control-flow target mismatch");

    printf("{\n");
    printf("  \"schema\": \"abl.phase4.d03.static.v1\",\n");
    printf("  \"row\": \"D03_contact_damage\",\n");
    printf("  \"input\": {\"path\": \"%s\", \"sha256\": \"%s\", \"anchors_checked\": %zu},\n",
           path, sha, sizeof(anchors) / sizeof(anchors[0]));
    printf("  \"damage_handler\": \"0x8004A700\",\n");
    printf("  \"callers\": [\"0x800496B0\",\"0x80049740\",\"0x80049868\",\"0x8004B4A0\",\"0x80058A48\",\"0x8005C9F8\"],\n");
    printf("  \"ordinary_contact_callers\": [\"0x80049740\",\"0x8004B4A0\",\"0x80058A48\",\"0x8005C9F8\"],\n");
    printf("  \"special_nonordinary_callers\": [{\"pc\":\"0x800496B0\",\"kind\":1},{\"pc\":\"0x80049868\",\"kind\":2}],\n");
    printf("  \"hitbox\": {\"broad_phase\":\"actor XYZ plus +0x64/+0x66/+0x68 versus player Y-7360, all divided by 32, radius actor+0x6A plus 250\",\"narrow_phase\":\"pose-indexed oriented ellipsoid from actor+0x74, also expanded by 250\",\"both_required\":true},\n");
    printf("  \"ordinary_damage\": {\"health\":\"s16 0x800A6594\",\"delta\":-1,\"survive_timer\":45,\"death_timer\":-45,\"vertical_velocity\":-1024,\"horizontal_source\":\"collision vector normalized by 0x80060284 then quarter-scaled\"},\n");
    printf("  \"suppression\": {\"positive_stagger_suppresses_health_and_vertical_launch\":true,\"horizontal_vector_written_before_stagger_gate\":true,\"positive_timer_ticks_toward_zero\":true,\"negative_timer_ticks_toward_zero\":true,\"intercept_timer\":-30},\n");
    printf("  \"family_law\": \"damage amount, timer, and launch are resident-global; family variation is actor hitbox data and eligibility flags\"\n");
    printf("}\n");
    free(exe);
    return 0;
}
