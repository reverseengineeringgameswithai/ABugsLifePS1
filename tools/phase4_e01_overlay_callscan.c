#define _POSIX_C_SOURCE 200809L
#include <glob.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static uint32_t le32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static unsigned char *read_file(const char *path, size_t *size) {
    FILE *fp = fopen(path, "rb");
    long end;
    unsigned char *data;
    if (!fp) return NULL;
    if (fseek(fp, 0, SEEK_END) || (end = ftell(fp)) < 0 || fseek(fp, 0, SEEK_SET)) {
        fclose(fp);
        return NULL;
    }
    data = malloc((size_t)end);
    if (!data || fread(data, 1, (size_t)end, fp) != (size_t)end) {
        free(data);
        fclose(fp);
        return NULL;
    }
    fclose(fp);
    *size = (size_t)end;
    return data;
}

static uint32_t jal_word(uint32_t address) {
    return 0x0c000000u | ((address >> 2) & 0x03ffffffu);
}

int main(void) {
    const uint32_t targets[] = {0x80026df4u, 0x800571e0u, 0x8005721cu};
    glob_t paths = {0};
    size_t f, i, k;
    int total = 0;

    glob("REBUILD/files/LEVEL*/LEVEL*.BIN", 0, NULL, &paths);
    printf("{\"files_scanned\":%zu,\"calls\":[", paths.gl_pathc);
    for (f = 0; f < paths.gl_pathc; f++) {
        size_t size = 0;
        unsigned char *data = read_file(paths.gl_pathv[f], &size);
        if (!data) continue;
        for (i = 0; i + 4 <= size; i += 4) {
            uint32_t word = le32(data + i);
            for (k = 0; k < sizeof(targets) / sizeof(targets[0]); k++) {
                int found = -1;
                int j;
                if (word != jal_word(targets[k])) continue;
                for (j = 0; j <= 8 && i >= 4u * (size_t)j; j++) {
                    uint32_t prior = le32(data + i - 4u * (size_t)j);
                    if ((prior & 0xffff0000u) == 0x24040000u ||
                        (prior & 0xffff0000u) == 0x34040000u) {
                        found = (int)(prior & 0xffffu);
                        break;
                    }
                }
                if (total++) printf(",");
                printf("{\"file\":\"%s\",\"offset\":%zu,"
                       "\"pc\":\"0x%08x\",\"target\":\"0x%08x\","
                       "\"near_a0_constant\":%d,\"context\":[",
                       paths.gl_pathv[f], i, 0x800b39a0u + (unsigned)i,
                       targets[k], found);
                for (j = 6; j >= 0; j--) {
                    if (j != 6) printf(",");
                    printf("\"0x%08x\"", i >= 4u * (size_t)j
                           ? le32(data + i - 4u * (size_t)j) : 0);
                }
                printf("]}");
            }
        }
        free(data);
    }
    printf("],\"call_count\":%d}\n", total);
    globfree(&paths);
    return 0;
}
