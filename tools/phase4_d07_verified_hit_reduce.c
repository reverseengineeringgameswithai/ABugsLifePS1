#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { long frame, width, value; unsigned long address, pc; } Event;

static char *load(const char *path, size_t *size) {
    FILE *f = fopen(path, "rb"); if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);
    char *s = malloc((size_t)n + 1); fread(s, 1, (size_t)n, f); fclose(f); s[n] = 0;
    *size = (size_t)n; return s;
}

static long number(const char *start, const char *end, const char *key, long fallback) {
    const char *p = strstr(start, key);
    if (!p || p >= end || !(p = strchr(p, ':')) || p >= end) return fallback;
    return strtol(p + 1, NULL, 0);
}

static unsigned long hex_string(const char *start, const char *end, const char *key) {
    const char *p = strstr(start, key);
    if (!p || p >= end || !(p = strchr(p, ':')) || !(p = strchr(p, '"')) || p >= end) return 0;
    return strtoul(p + 1, NULL, 0);
}

static Event *parse(const char *path, long *count) {
    size_t size; char *data = load(path, &size), *cursor = data;
    long cap = 1024; Event *events = malloc((size_t)cap * sizeof *events); *count = 0;
    while ((cursor = strstr(cursor, "\"address\":"))) {
        char *next = strstr(cursor + 10, "\"address\":");
        char *end = next ? next : data + size;
        Event event = {
            number(cursor, end, "\"frame\"", -1),
            number(cursor, end, "\"width\"", -1),
            number(cursor, end, "\"new_value\"", -1),
            hex_string(cursor, end, "\"address\""),
            hex_string(cursor, end, "\"instruction_pc\"")
        };
        cursor += 10;
        if (event.frame < 0) continue;
        if (*count == cap) { cap *= 2; events = realloc(events, (size_t)cap * sizeof *events); }
        events[(*count)++] = event;
    }
    free(data); return events;
}

static void state_events(const char *path) {
    long count; Event *events = parse(path, &count); long last = -999999;
    puts("state transitions:");
    for (long i = 0; i < count; i++) {
        if (events[i].value == last) continue;
        printf("  frame=%ld value=%ld writer=0x%08lx\n", events[i].frame, events[i].value, events[i].pc);
        last = events[i].value;
    }
    printf("  events=%ld\n", count); free(events);
}

static void flag_events(const char *path) {
    long count; Event *events = parse(path, &count); long last_semantic = -999999;
    puts("semantic flag transitions (0x4000 bookkeeping masked):");
    for (long i = 0; i < count; i++) {
        if (events[i].frame < 39750 || events[i].frame > 40050) continue;
        long semantic = events[i].value & ~0x4000L;
        int latch_writer = events[i].pc == 0x8004b464ul;
        int latch_consumer = events[i].pc == 0x8004a1d0ul;
        int upkeep = events[i].pc == 0x80024e58ul || events[i].pc == 0x80025050ul ||
                     events[i].pc == 0x8004d270ul || events[i].pc == 0x8004d38cul;
        if (upkeep && !latch_writer && !latch_consumer) continue;
        if (semantic == last_semantic && !latch_writer && !latch_consumer) continue;
        printf("  frame=%ld raw=0x%04lx semantic=0x%04lx writer=0x%08lx%s\n",
               events[i].frame, (unsigned long)events[i].value & 0xfffful,
               (unsigned long)semantic & 0xfffful, events[i].pc,
               latch_writer ? " SET_1000" : latch_consumer ? " CLEAR_1000" : "");
        last_semantic = semantic;
    }
    printf("  events=%ld\n", count); free(events);
}

static void value_changes(const char *label, const char *path, unsigned long callback_pc) {
    long count; Event *events = parse(path, &count); long last = -999999;
    printf("%s changes:\n", label);
    for (long i = 0; i < count; i++) {
        if (events[i].frame < 39750 || events[i].frame > 40050) continue;
        if (callback_pc && events[i].pc != callback_pc) continue;
        if (!callback_pc && events[i].value == last) continue;
        printf("  frame=%ld value=0x%08lx writer=0x%08lx\n",
               events[i].frame, (unsigned long)events[i].value, events[i].pc);
        last = events[i].value;
    }
    printf("  events=%ld\n", count); free(events);
}

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "usage: %s state flags timer motion1c motion24\n", argv[0]); return 2;
    }
    state_events(argv[1]);
    flag_events(argv[2]);
    value_changes("reaction timer", argv[3], 0);
    value_changes("callback motion +0x1c", argv[4], 0x8004a1ecul);
    value_changes("callback motion +0x24", argv[5], 0x8004a1f0ul);
    return 0;
}
