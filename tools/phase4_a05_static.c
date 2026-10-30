/* Verify the decisive A05 instruction words in pristine SCUS_942.88.
 * Build: cc -O2 -std=c11 -Wall -Wextra -Werror phase4_a05_static.c -o /tmp/a05 -lcrypto
 * Run:   /tmp/a05 REBUILD/files/SCUS_942.88
 */

#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { FILE_BIAS = 0x800, LOAD_ADDRESS = 0x80010000 };

typedef struct Check {
    uint32_t pc;
    uint32_t word;
    const char *meaning;
} Check;

static const uint8_t expected_sha256[32] = {
    0x1a,0xa2,0x89,0x54,0xa1,0x87,0x1d,0x07,
    0x99,0xbf,0x30,0x6a,0x5a,0xe7,0x46,0xd1,
    0x7b,0x14,0x3f,0xce,0x6d,0x19,0x65,0x74,
    0x0f,0x79,0x88,0x62,0xbe,0x51,0x9d,0x20
};

static const Check checks[] = {
    {0x80048b68,0x30424000,"Cross mask 0x4000"},
    {0x80048bdc,0xa6220080,"ground/coyote takeoff writes state 1"},
    {0x80048c6c,0x86230080,"air-state reload for second action"},
    {0x80048c8c,0x28422001,"floor gap threshold 8193"},
    {0x80048ca8,0xa6220084,"high dive writes phase 10"},
    {0x80048cbc,0xa6230080,"high dive writes state 4"},
    {0x80048d64,0xa6220080,"low path writes state 3"},
    {0x80048dac,0x24021000,"terminal dive speed 4096"},
    {0x80048db4,0xae220030,"terminal dive speed store"},
    {0x80048db8,0xa6220084,"positive phase decrement"},
    {0x80048dbc,0xae200030,"phase above 1 forces vy zero"},
    {0x80048dd0,0x24620200,"negative recovery adds 512"},
    {0x80048dd4,0xa6220084,"negative recovery phase store"},
    {0x80048df8,0xa6220084,"impact writes phase -6144"},
    {0x80048e00,0xa622007a,"impact writes action timer 12"},
    {0x80048e08,0xae200030,"impact clears vy"},
    {0x80048e0c,0xa6220080,"impact writes state 1"},
    {0x8004ac48,0x2442e340,"contact comparison uses player Y-7360"},
    {0x8004ace0,0x244200fa,"outer radius adds 250"},
    {0x8004ae9c,0x30620020,"actor flag 0x20 split"},
    {0x8004b0c4,0x30620800,"actor flag 0x800 rejection"},
    {0x8004b130,0x84426584,"direct player phase read"},
    {0x8004b2ac,0x96c2000a,"phase read via player+0x7a base"},
    {0x8004b2b4,0x2c420002,"unsigned phase below 2 gate"},
    {0x8004b2d0,0xa622006c,"actor reaction timer -20"},
    {0x8004b2d8,0xa6220054,"actor reaction field +0x54"},
    {0x8004b2e0,0xa6220058,"actor reaction field +0x58"},
    {0x8004b31c,0x86c2000a,"counter qualifier reloads player phase"},
    {0x8004b324,0x1440000d,"nonzero phase reaches counter"},
    {0x8004b334,0x2402fa00,"phase-zero rebound speed -1536"},
    {0x8004b338,0xaec2ffb6,"phase-zero rebound vy store"},
    {0x8004b340,0xa6c20006,"phase-zero writes state 5"},
    {0x8004b34c,0xa6c2000e,"phase-zero animation selector 3"},
    {0x8004b38c,0x8f8204a4,"Bonus-1 streak load"},
    {0x8004b394,0x24430001,"streak increment"},
    {0x8004b398,0x24420072,"progress command old+114"},
    {0x8004b3a8,0xaf8304a4,"streak store"},
    {0x8004b3ac,0x146200b3,"threshold requires 5"},
    {0x8004b3d0,0xaf8004a4,"success clears streak"},
    {0x8005684c,0x8442657a,"action timer presentation read"},
    {0x80056858,0x2402001c,"animation selector 28"},
    {0x80056860,0xa4226588,"timer-12 animation store"}
};

static uint32_t read_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
        return 2;
    }

    FILE *file = fopen(argv[1], "rb");
    if (file == NULL) {
        perror(argv[1]);
        return 2;
    }
    if (fseek(file, 0, SEEK_END) != 0) return 2;
    long file_size = ftell(file);
    if (file_size < 0 || fseek(file, 0, SEEK_SET) != 0) return 2;
    uint8_t *image = malloc((size_t)file_size);
    if (image == NULL || fread(image, 1, (size_t)file_size, file) != (size_t)file_size)
        return 2;
    fclose(file);

    uint8_t digest[32];
    size_t digest_size = 0;
    if (!EVP_Q_digest(NULL, "SHA256", NULL, image, (size_t)file_size,
                      digest, &digest_size) || digest_size != sizeof(digest) ||
        memcmp(digest, expected_sha256, sizeof(digest)) != 0) {
        fprintf(stderr, "refusing non-pristine executable\n");
        free(image);
        return 1;
    }

    unsigned failures = 0;
    for (size_t i = 0; i < sizeof(checks) / sizeof(checks[0]); i++) {
        size_t offset = FILE_BIAS + (size_t)(checks[i].pc - LOAD_ADDRESS);
        if (offset + 4 > (size_t)file_size) {
            fprintf(stderr, "out of range: %08x\n", checks[i].pc);
            failures++;
            continue;
        }
        uint32_t actual = read_u32(image + offset);
        printf("%08x %08x %s %s\n", checks[i].pc, actual,
               actual == checks[i].word ? "PASS" : "FAIL",
               checks[i].meaning);
        failures += actual != checks[i].word;
    }

    printf("checks=%zu failures=%u\n",
           sizeof(checks) / sizeof(checks[0]), failures);
    free(image);
    return failures != 0;
}
