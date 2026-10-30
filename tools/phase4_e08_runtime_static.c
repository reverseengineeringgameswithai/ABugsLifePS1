/* Phase-4 E08 pristine-ASM and authored-data verifier.
 *
 * This read-only tool joins the existing placement census to the runtime
 * semantics of type-0x3f kind 0x31 and the pass-3 direct-reference frontier.
 * It does not emulate the game or modify any input.
 *
 * Build:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror \
 *      -o /tmp/phase4_e08_runtime_static tools/phase4_e08_runtime_static.c
 * Usage:
 *   /tmp/phase4_e08_runtime_static SCUS_942.88 LEVEL*.DAT... \
 *      --bins LEVEL*.BIN...
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct Image {
    uint8_t *data;
    size_t size;
    uint32_t base;
    uint32_t text_size;
    int psx_exe;
} Image;

typedef struct Pin {
    uint32_t pc;
    uint32_t word;
} Pin;

static uint16_t u16(const uint8_t *p)
{
    uint16_t v;
    memcpy(&v, p, sizeof(v));
    return v;
}

static int16_t s16(const uint8_t *p)
{
    int16_t v;
    memcpy(&v, p, sizeof(v));
    return v;
}

static uint32_t u32(const uint8_t *p)
{
    uint32_t v;
    memcpy(&v, p, sizeof(v));
    return v;
}

static int32_t s32(const uint8_t *p)
{
    int32_t v;
    memcpy(&v, p, sizeof(v));
    return v;
}

static Image load_image(const char *path)
{
    Image img = {0};
    FILE *f = fopen(path, "rb");
    long length;

    if (f == NULL) {
        perror(path);
        exit(2);
    }
    if (fseek(f, 0, SEEK_END) != 0 || (length = ftell(f)) < 0 ||
        fseek(f, 0, SEEK_SET) != 0) {
        fprintf(stderr, "seek failed: %s\n", path);
        exit(2);
    }
    img.size = (size_t)length;
    img.data = malloc(img.size == 0 ? 1 : img.size);
    if (img.data == NULL || fread(img.data, 1, img.size, f) != img.size) {
        fprintf(stderr, "read failed: %s\n", path);
        exit(2);
    }
    fclose(f);

    if (img.size >= 0x800 && memcmp(img.data, "PS-X EXE", 8) == 0) {
        img.psx_exe = 1;
        img.base = u32(img.data + 0x18);
        img.text_size = u32(img.data + 0x1c);
        if (img.text_size > img.size - 0x800)
            img.text_size = (uint32_t)(img.size - 0x800);
    }
    return img;
}

static void free_image(Image *img)
{
    free(img->data);
    memset(img, 0, sizeof(*img));
}

static uint32_t exe_word(const Image *exe, uint32_t pc)
{
    size_t off;

    if (!exe->psx_exe || pc < exe->base || pc + 4 > exe->base + exe->text_size) {
        fprintf(stderr, "EXE PC outside text: 0x%08x\n", pc);
        exit(2);
    }
    off = 0x800u + (size_t)(pc - exe->base);
    return u32(exe->data + off);
}

static int check_pins(const Image *exe)
{
    static const Pin pins[] = {
        {0x800539a0, 0x24020031}, /* kind == 0x31 */
        {0x800539bc, 0x28420071}, /* restY-currentY < 113 */
        {0x800539e0, 0x904210a2}, /* alternating phase gate */
        {0x80053a04, 0x24020015}, /* metadata-A row 21 */
        {0x80053a0c, 0x25670053}, /* ctor = ordinal + 83 */
        {0x80053a14, 0x0c016791}, /* contact_alloc */
        {0x80053ca0, 0x2442ffd0}, /* kind - 0x30 */
        {0x80053ca4, 0x2c420002}, /* range 0x30..0x31 */
        {0x80053ca8, 0x1440000a}, /* those two bypass common burst */
        {0x80053cc4, 0x0c015d88}, /* common pickup burst/finalize */
        {0x800545a0, 0x8642000a}, /* restY */
        {0x800545a8, 0x2442ff90}, /* restY - 112 */
        {0x800545ac, 0x14620008}, /* exact-height gate */
        {0x800545b0, 0x2462ffff}, /* currentY - 1 delay slot */
        {0x800545b4, 0x2411fff6}, /* result -10 */
        {0x800545b8, 0xae420000}, /* store new currentY */
        {0x800545bc, 0x0c014265}, /* sound/event -3 */
        {0x80025544, 0xa2400005}, /* projector clears entry+0x0d */
        {0x800255bc, 0xa2420005}, /* projector marks entry visible */
        {0x800551b4, 0xa0440000}, /* phase gate alternates 0/1 */
        {0x8005b918, 0xa02010a2}, /* scene reset clears phase gate */
    };
    size_t i;

    for (i = 0; i < sizeof(pins) / sizeof(pins[0]); i++) {
        uint32_t got = exe_word(exe, pins[i].pc);
        if (got != pins[i].word) {
            fprintf(stderr, "pin mismatch at 0x%08x: %08x != %08x\n",
                    pins[i].pc, got, pins[i].word);
            return 0;
        }
    }
    return 1;
}

static int check_metadata(const Image *exe)
{
    static const uint8_t variants[5][3] = {
        {0x80, 0x00, 0x00},
        {0x00, 0x80, 0x00},
        {0x00, 0x40, 0x80},
        {0x80, 0x80, 0x00},
        {0x00, 0x00, 0x80},
    };
    unsigned ctor;

    for (ctor = 84; ctor <= 88; ctor++) {
        uint32_t va = 0x8007941cu + ctor * 0x14u;
        size_t off = 0x800u + (size_t)(va - exe->base);
        const uint8_t *row = exe->data + off;
        unsigned i = ctor - 84;

        if (off + 0x14 > exe->size || u16(row + 0x00) != 1 ||
            u16(row + 0x02) != 20 || s16(row + 0x04) != -8 ||
            row[0x06] != 0 || row[0x07] != 4 ||
            u16(row + 0x08) != 90 || u16(row + 0x0a) != 90 ||
            u16(row + 0x0c) != 0 || row[0x0e] != 2 ||
            row[0x0f] != 0 || row[0x10] != 0x20 ||
            memcmp(row + 0x11, variants[i], 3) != 0) {
            fprintf(stderr, "metadata-B constructor %u mismatch\n", ctor);
            return 0;
        }
    }
    return 1;
}

static long record_size(const uint8_t *data, size_t size, long off)
{
    uint16_t count;
    int16_t type;

    if (off < 0 || (size_t)off + 4 > size)
        return -1;
    count = u16(data + off);
    type = s16(data + off + 2);
    if (type >= 0)
        return type == 0x3f ? 4 + (long)count * 0x10 : 4 + (long)count * 0x0c;
    return ((((long)3 * count + 1) >> 1) << 2) + 0x10;
}

static int scan_dat(const char *path, long *records, int *present,
                    int *groups4, int *groups5)
{
    Image dat = load_image(path);
    uint32_t tables;
    long off = 4;
    long local = 0;
    uint32_t t;
    int ok = 1;

    if (dat.size < 4 || (tables = u32(dat.data)) > 4096) {
        fprintf(stderr, "invalid DAT header: %s\n", path);
        free_image(&dat);
        return 0;
    }
    for (t = 0; t < tables; t++) {
        long step;
        uint16_t count;
        int16_t type;
        uint16_t i;

        if (off < 0 || (size_t)off + 4 > dat.size) {
            ok = 0;
            break;
        }
        count = u16(dat.data + off);
        type = s16(dat.data + off + 2);
        if (type == 0x3f) {
            for (i = 0; i < count; i++) {
                long e = off + 4 + (long)i * 0x10;
                if ((size_t)e + 0x10 > dat.size) {
                    ok = 0;
                    break;
                }
                if (dat.data[e + 0x0c] == 0x31) {
                    local++;
                    if (s32(dat.data + e + 0x04) != -600 ||
                        dat.data[e + 0x0d] != 0 || s16(dat.data + e + 0x0e) != 0)
                        ok = 0;
                }
            }
        }
        step = record_size(dat.data, dat.size, off);
        if (step < 0) {
            ok = 0;
            break;
        }
        off += step;
    }
    if (local != 0) {
        (*present)++;
        if (local == 4)
            (*groups4)++;
        else if (local == 5)
            (*groups5)++;
        else
            ok = 0;
    }
    *records += local;
    free_image(&dat);
    return ok;
}

static int memory_op(unsigned op)
{
    return op == 32 || op == 33 || op == 35 || op == 36 || op == 37 ||
           op == 40 || op == 41 || op == 43;
}

static int store_op(unsigned op)
{
    return op == 40 || op == 41 || op == 43;
}

static void scan_pass3_direct(const Image *img, long *reads, long *writes)
{
    size_t start = img->psx_exe ? 0x800 : 0;
    size_t length = img->psx_exe ? img->text_size : img->size;
    uint8_t *seen = calloc(length / 4 + 1, 1);
    size_t seed;

    if (seen == NULL)
        exit(2);
    for (seed = 0; seed + 4 <= length; seed += 4) {
        uint32_t first = u32(img->data + start + seed);
        uint32_t value[32] = {0};
        uint8_t known[32] = {0};
        size_t k;

        if ((first >> 26) != 15 || (first & 0xffff) != 0x8009)
            continue;
        known[0] = 1;
        known[(first >> 16) & 31] = 1;
        value[(first >> 16) & 31] = 0x80090000u;
        for (k = 1; k <= 32 && seed + 4 * k + 4 <= length; k++) {
            size_t off = seed + 4 * k;
            uint32_t word = u32(img->data + start + off);
            unsigned op = word >> 26;
            unsigned rs = (word >> 21) & 31;
            unsigned rt = (word >> 16) & 31;
            unsigned rd = (word >> 11) & 31;
            int16_t imm = (int16_t)word;

            if (memory_op(op) && known[rs]) {
                uint32_t address = value[rs] + imm;
                if (address >= 0x800902b6 && address <= 0x800902c7 &&
                    !seen[off / 4]) {
                    seen[off / 4] = 1;
                    if (store_op(op))
                        (*writes)++;
                    else
                        (*reads)++;
                }
                if (!store_op(op))
                    known[rt] = 0;
            } else if (op == 9) {
                known[rt] = known[rs];
                if (known[rt])
                    value[rt] = value[rs] + imm;
            } else if (op == 13) {
                known[rt] = known[rs];
                if (known[rt])
                    value[rt] = value[rs] | (word & 0xffff);
            } else if (op == 15) {
                known[rt] = 1;
                value[rt] = (word & 0xffff) << 16;
            } else if (op == 0 && (word & 63) == 33) {
                known[rd] = known[rs] && known[rt];
                if (known[rd])
                    value[rd] = value[rs] + value[rt];
            } else if (op == 0) {
                known[rd] = 0;
            }
        }
    }
    free(seen);
}

int main(int argc, char **argv)
{
    Image exe;
    int bins = 0;
    int dat_files = 0;
    int bin_files = 0;
    int present = 0;
    int groups4 = 0;
    int groups5 = 0;
    long records = 0;
    long pass3_reads = 0;
    long pass3_writes = 0;
    int pins_ok;
    int metadata_ok;
    int data_ok = 1;
    int ok;
    int i;

    if (argc < 3) {
        fprintf(stderr, "usage: %s SCUS_942.88 LEVEL*.DAT... --bins LEVEL*.BIN...\n",
                argv[0]);
        return 2;
    }
    exe = load_image(argv[1]);
    if (!exe.psx_exe || exe.base != 0x80010000) {
        fprintf(stderr, "unexpected executable identity/layout\n");
        return 2;
    }
    pins_ok = check_pins(&exe);
    metadata_ok = check_metadata(&exe);
    scan_pass3_direct(&exe, &pass3_reads, &pass3_writes);

    for (i = 2; i < argc; i++) {
        if (strcmp(argv[i], "--bins") == 0) {
            bins = 1;
            continue;
        }
        if (!bins) {
            dat_files++;
            if (!scan_dat(argv[i], &records, &present, &groups4, &groups5))
                data_ok = 0;
        } else {
            Image overlay = load_image(argv[i]);
            bin_files++;
            scan_pass3_direct(&overlay, &pass3_reads, &pass3_writes);
            free_image(&overlay);
        }
    }
    ok = pins_ok && metadata_ok && data_ok && dat_files == 21 &&
         bin_files == 20 && records == 39 && present == 8 &&
         groups4 == 1 && groups5 == 7 && pass3_reads == 1 &&
         pass3_writes == 0;

    printf("{\n");
    printf("  \"row\": \"E08_props_movers_gates\",\n");
    printf("  \"ok\": %s,\n", ok ? "true" : "false");
    printf("  \"asm_pins\": {\"checked\": 21, \"ok\": %s},\n",
           pins_ok ? "true" : "false");
    printf("  \"metadata_b_ctors_84_88\": {\"checked\": 5, \"ok\": %s},\n",
           metadata_ok ? "true" : "false");
    printf("  \"kind31\": {\"records\": %ld, \"files\": %d, "
           "\"groups_of_5\": %d, \"groups_of_4\": %d, "
           "\"all_y_minus_600_status_0_rest_0\": %s},\n",
           records, present, groups5, groups4, data_ok ? "true" : "false");
    printf("  \"pass3_direct_formed_xrefs\": {\"resident_and_level_overlays\": %d, "
           "\"reads\": %ld, \"writes\": %ld}\n",
           1 + bin_files, pass3_reads, pass3_writes);
    printf("}\n");

    free_image(&exe);
    return ok ? 0 : 1;
}
