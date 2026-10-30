/* Reduce one DuckStation execTrace range to the PC path for a selected s0. */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *slurp(const char *path)
{
    FILE *fp = fopen(path, "rb");
    long n;
    char *p;
    if (!fp) {
        perror(path);
        exit(2);
    }
    fseek(fp, 0, SEEK_END);
    n = ftell(fp);
    rewind(fp);
    p = malloc((size_t)n + 1);
    if (!p || fread(p, 1, (size_t)n, fp) != (size_t)n) {
        perror("read");
        exit(2);
    }
    fclose(fp);
    p[n] = 0;
    return p;
}

static int hex_field(const char *begin, const char *end, const char *key,
                     uint32_t *out)
{
    char needle[32];
    const char *p;
    char *tail;
    snprintf(needle, sizeof(needle), "\"%s\"", key);
    p = strstr(begin, needle);
    if (!p || p >= end || !(p = strchr(p + strlen(needle), '"')) || p >= end)
        return 0;
    *out = (uint32_t)strtoul(p + 1, &tail, 0);
    return tail != p + 1 && tail <= end;
}

int main(int argc, char **argv)
{
    char *json, *p;
    uint32_t target;
    unsigned selected = 0;
    int early_x_bound = 0, early_z_bound = 0, final_bound = 0;

    if (argc != 3) {
        fprintf(stderr, "usage: %s TRACE.json S0_HEX\n", argv[0]);
        return 2;
    }
    target = (uint32_t)strtoul(argv[2], NULL, 0);
    json = slurp(argv[1]);
    p = json;
    puts("index\tpc\ta0\ta1\ta2\tv0\tv1\tt1\tt2\tt3\tt4");
    while ((p = strstr(p, "\"pc\"")) != NULL) {
        char *event_end = strstr(p, "\"watch_id\"");
        char *regs = strstr(p, "\"regs\"");
        char *regs_end;
        uint32_t pc, s0, a0, a1, a2, v0, v1, t1, t2, t3, t4;
        if (!event_end || !regs || regs > event_end)
            break;
        regs_end = strchr(regs, '}');
        if (!regs_end || !hex_field(p, regs, "pc", &pc) ||
            !hex_field(regs, regs_end, "s0", &s0)) {
            p = event_end + 1;
            continue;
        }
        if (s0 != target) {
            p = event_end + 1;
            continue;
        }
        hex_field(regs, regs_end, "a0", &a0);
        hex_field(regs, regs_end, "a1", &a1);
        hex_field(regs, regs_end, "a2", &a2);
        hex_field(regs, regs_end, "v0", &v0);
        hex_field(regs, regs_end, "v1", &v1);
        hex_field(regs, regs_end, "t1", &t1);
        hex_field(regs, regs_end, "t2", &t2);
        hex_field(regs, regs_end, "t3", &t3);
        hex_field(regs, regs_end, "t4", &t4);
        printf("%u\t0x%08" PRIx32 "\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n",
               selected++, pc, (int32_t)a0, (int32_t)a1, (int32_t)a2,
               (int32_t)v0, (int32_t)v1, (int32_t)t1, (int32_t)t2,
               (int32_t)t3, (int32_t)t4);
        if (pc == 0x80032ba8u || pc == 0x80032bb0u)
            early_x_bound = 1;
        if (pc == 0x80032bc8u || pc == 0x80032bd0u)
            early_z_bound = 1;
        if (pc == 0x80032d28u)
            final_bound = 1;
        p = event_end + 1;
    }
    fprintf(stderr,
            "selected=%u early_x_bound=%d early_z_bound=%d final_bound=%d\n",
            selected, early_x_bound, early_z_bound, final_bound);
    free(json);
    return selected ? 0 : 1;
}
