#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int field(const char *line, const char *key, uint64_t *out) {
    char pat[80];
    snprintf(pat, sizeof(pat), "\"%s\"", key);
    const char *p = strstr(line, pat);
    if (!p) return 0;
    p = strchr(p + strlen(pat), ':');
    if (!p) return 0;
    do { ++p; } while (*p == ' ' || *p == '\t' || *p == '\"');
    char *end = NULL;
    unsigned long long v = strtoull(p, &end, 0);
    if (end == p) return 0;
    *out = (uint64_t)v;
    return 1;
}

static int zero_calls(const char *path, uint64_t target, uint64_t initial) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 1;
    char line[4096];
    uint64_t frame = 0, cycle = 0, a0 = 0, a1 = 0, a2 = 0, ra = 0;
    unsigned hits = 0;
    int events = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "\"events\"")) events = 1;
        if (events && strstr(line, "\"watches\"")) break;
        if (!events) continue;
        (void)field(line, "frame", &frame);
        (void)field(line, "cycle", &cycle);
        (void)field(line, "a0", &a0);
        (void)field(line, "a1", &a1);
        (void)field(line, "a2", &a2);
        if (field(line, "ra", &ra)) {
            if (a1 == 0 && a0 <= target && target - a0 < a2) {
                printf("ZERO abs_frame=%" PRIu64 " movie_frame=%" PRIu64
                       " cycle=%" PRIu64 " base=0x%08" PRIx64
                       " length=0x%" PRIx64 " call_pc=0x%08" PRIx64 "\n",
                       frame, frame - initial, cycle, a0, a2, ra - 8);
                ++hits;
            }
            a0 = a1 = a2 = ra = 0;
        }
    }
    fclose(fp);
    printf("ZERO_SUMMARY target=0x%08" PRIx64 " hits=%u\n", target, hits);
    return hits != 2;
}

static int writes(const char *path, const char *label, uint64_t initial) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 1;
    char line[4096];
    uint64_t frame = 0, cycle = 0, address = 0, pc = 0, oldv = 0, newv = 0;
    unsigned hits = 0;
    int events = 0, have_old = 0, have_new = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "\"events\"")) events = 1;
        if (events && strstr(line, "\"watches\"")) break;
        if (!events) continue;
        (void)field(line, "frame", &frame);
        (void)field(line, "cycle", &cycle);
        (void)field(line, "address", &address);
        (void)field(line, "instruction_pc", &pc);
        if (field(line, "new_value", &newv)) have_new = 1;
        if (strstr(line, "\"value\"") && !strstr(line, "new_value") && field(line, "value", &oldv)) have_old = 1;
        if (strstr(line, "\"width\"") && have_old && have_new) {
            printf("%s abs_frame=%" PRIu64 " movie_frame=%" PRIu64
                   " cycle=%" PRIu64 " pc=0x%08" PRIx64
                   " old=0x%02" PRIx64 " new=0x%02" PRIx64 "\n",
                   label, frame, frame - initial, cycle, pc, oldv, newv);
            ++hits;
            have_old = have_new = 0;
        }
    }
    fclose(fp);
    printf("%s_SUMMARY hits=%u\n", label, hits);
    return hits == 0;
}

static int reward(const char *path) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 1;
    char line[4096];
    uint64_t pc = 0;
    unsigned hits = 0;
    int events = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "\"events\"")) events = 1;
        if (events && strstr(line, "\"watches\"")) break;
        if (!events || strncmp(line, "      \"pc\"", 10) || !field(line, "pc", &pc)) continue;
        if (pc == 0x80053df8 || pc == 0x80053f54 ||
            pc == 0x800540b0 || pc == 0x8005420c) {
            printf("REWARD_STORE pc=0x%08" PRIx64 "\n", pc);
            ++hits;
        }
    }
    fclose(fp);
    printf("REWARD_SUMMARY hits=%u confirmed=%s\n", hits, hits == 1 ? "yes" : "no");
    return hits != 1;
}

int main(int argc, char **argv) {
    if (argc != 7) {
        fprintf(stderr, "usage: %s ZERO MASK LIVES REWARD TARGET INITIAL_FRAME\n", argv[0]);
        return 2;
    }
    uint64_t target = strtoull(argv[5], NULL, 0);
    uint64_t initial = strtoull(argv[6], NULL, 0);
    int rc = 0;
    rc |= zero_calls(argv[1], target, initial);
    rc |= writes(argv[2], "MASK", initial);
    rc |= writes(argv[3], "LIVES", initial);
    rc |= reward(argv[4]);
    return rc;
}
