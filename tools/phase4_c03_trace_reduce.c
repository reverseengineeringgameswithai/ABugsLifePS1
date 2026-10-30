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

static int reduce_zero(const char *path, uint64_t target, uint64_t initial) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 1;
    char line[4096];
    uint64_t frame = 0, cycle = 0, a0 = 0, a1 = 0, a2 = 0, ra = 0;
    int in_events = 0, hits = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "\"events\"")) in_events = 1;
        if (in_events && strstr(line, "\"watches\"")) break;
        if (!in_events) continue;
        (void)field(line, "frame", &frame);
        (void)field(line, "cycle", &cycle);
        (void)field(line, "a0", &a0);
        (void)field(line, "a1", &a1);
        (void)field(line, "a2", &a2);
        if (field(line, "ra", &ra)) {
            if (a1 == 0 && a0 <= target && target - a0 < a2) {
                printf("ZERO target=0x%08" PRIx64 " abs_frame=%" PRIu64
                       " movie_frame=%" PRIu64 " cycle=%" PRIu64
                       " base=0x%08" PRIx64 " length=0x%" PRIx64
                       " caller_ra=0x%08" PRIx64 " call_pc=0x%08" PRIx64 "\n",
                       target, frame, frame - initial, cycle, a0, a2, ra, ra - 8);
                ++hits;
            }
            a0 = a1 = a2 = ra = 0;
        }
    }
    fclose(fp);
    printf("ZERO_SUMMARY hits=%d\n", hits);
    return hits == 0;
}

static int reduce_access(const char *path, uint64_t initial) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 1;
    char line[4096];
    uint64_t frame = 0, cycle = 0, address = 0, pc = 0, oldv = 0, newv = 0;
    int in_events = 0, have_old = 0, have_new = 0, hits = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "\"events\"")) in_events = 1;
        if (in_events && strstr(line, "\"watches\"")) break;
        if (!in_events) continue;
        (void)field(line, "frame", &frame);
        (void)field(line, "cycle", &cycle);
        (void)field(line, "address", &address);
        (void)field(line, "instruction_pc", &pc);
        if (field(line, "new_value", &newv)) have_new = 1;
        if (strstr(line, "\"value\"") && !strstr(line, "new_value") && field(line, "value", &oldv)) have_old = 1;
        if (strstr(line, "\"width\"") && have_old && have_new) {
            printf("WRITE target=0x%08" PRIx64 " abs_frame=%" PRIu64
                   " movie_frame=%" PRIu64 " cycle=%" PRIu64
                   " pc=0x%08" PRIx64 " old=0x%02" PRIx64 " new=0x%02" PRIx64 "\n",
                   address, frame, frame - initial, cycle, pc, oldv, newv);
            ++hits;
            have_old = have_new = 0;
        }
    }
    fclose(fp);
    printf("WRITE_SUMMARY hits=%d\n", hits);
    return hits == 0;
}

static int reduce_path(const char *path) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 1;
    char line[4096];
    uint64_t pc = 0;
    unsigned complete_store = 0, exact_gate = 0, cap_check = 0, increment_store = 0, post_cap = 0;
    int in_events = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "\"events\"")) in_events = 1;
        if (in_events && strstr(line, "\"watches\"")) break;
        if (!in_events || !field(line, "pc", &pc)) continue;
        if (pc == 0x80053d10) ++complete_store;
        if (pc == 0x80053d74 || pc == 0x80053d78) ++exact_gate;
        if (pc >= 0x80053ddc && pc <= 0x80053dec) ++cap_check;
        if (pc == 0x80053df8) ++increment_store;
        if (pc == 0x80053e5c) ++post_cap;
    }
    fclose(fp);
    printf("PATH complete_store=%u exact_gate=%u cap_check=%u increment_store=%u post_cap=%u capped_branch=%s\n",
           complete_store, exact_gate, cap_check, increment_store, post_cap,
           (complete_store && exact_gate && cap_check && !increment_store && post_cap) ? "yes" : "no");
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "usage: %s ZERO_JSON ACCESS_JSON EXEC_JSON TARGET INITIAL_FRAME\n", argv[0]);
        return 2;
    }
    uint64_t target = strtoull(argv[4], NULL, 0);
    uint64_t initial = strtoull(argv[5], NULL, 0);
    int rc = 0;
    rc |= reduce_zero(argv[1], target, initial);
    rc |= reduce_access(argv[2], initial);
    rc |= reduce_path(argv[3]);
    return rc;
}
