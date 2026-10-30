#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct { long frame, width, value; unsigned long address, pc; } Event;

typedef struct {
    unsigned offset;
    const char *name;
    long count, first_frame, last_frame, first_value, last_value;
} Field;

static char *load(const char *path, size_t *size) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
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

static int significant(unsigned offset) {
    return offset == 0x1c || offset == 0x24 || offset == 0x44 || offset == 0x5c ||
           offset == 0x5e || offset == 0x6c || offset == 0x6e ||
           offset == 0x74 || offset == 0x78 || offset == 0x7c;
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: %s trace.json actor_base\n", argv[0]); return 2; }
    unsigned long base = strtoul(argv[2], NULL, 0);
    Field fields[] = {
        {0x04,"x",0,-1,-1,0,0},{0x08,"y",0,-1,-1,0,0},{0x0c,"z",0,-1,-1,0,0},
        {0x10,"vx",0,-1,-1,0,0},{0x14,"vy",0,-1,-1,0,0},{0x18,"vz",0,-1,-1,0,0},
        {0x1c,"motion1c",0,-1,-1,0,0},{0x24,"motion24",0,-1,-1,0,0},
        {0x44,"state",0,-1,-1,0,0},{0x5c,"flags",0,-1,-1,0,0},{0x5e,"counter",0,-1,-1,0,0},
        {0x6c,"timer",0,-1,-1,0,0},{0x6e,"hp",0,-1,-1,0,0},
        {0x74,"data",0,-1,-1,0,0},{0x78,"vm",0,-1,-1,0,0},
        {0x7c,"callback",0,-1,-1,0,0}
    };
    const int field_count = (int)(sizeof fields / sizeof fields[0]);
    size_t size; char *data = load(argv[1], &size), *cursor = data;
    long events = 0, in_range = 0;
    while ((cursor = strstr(cursor, "\"address\":"))) {
        char *next = strstr(cursor + 10, "\"address\":");
        char *end = next ? next : data + size;
        Event e = {
            number(cursor, end, "\"frame\"", -1),
            number(cursor, end, "\"width\"", -1),
            number(cursor, end, "\"new_value\"", -1),
            hex_string(cursor, end, "\"address\""),
            hex_string(cursor, end, "\"instruction_pc\"")
        };
        cursor += 10;
        if (e.frame < 0) continue;
        events++;
        if (e.address < base || e.address >= base + 0x84) continue;
        in_range++;
        unsigned offset = (unsigned)(e.address - base);
        for (int i = 0; i < field_count; i++) {
            if (fields[i].offset != offset) continue;
            if (!fields[i].count) {
                fields[i].first_frame = e.frame;
                fields[i].first_value = e.value;
            }
            int changed = !fields[i].count || fields[i].last_value != e.value;
            fields[i].count++;
            fields[i].last_frame = e.frame;
            fields[i].last_value = e.value;
            if (significant(offset) && changed) {
                printf("transition frame=%ld field=%s offset=0x%02x width=%ld value=0x%08lx writer=0x%08lx\n",
                       e.frame, fields[i].name, offset, e.width, (unsigned long)e.value, e.pc);
            }
            break;
        }
    }
    printf("summary parsed_events=%ld in_actor_range=%ld base=0x%08lx\n", events, in_range, base);
    for (int i = 0; i < field_count; i++) {
        Field *f = &fields[i];
        printf("field %-8s writes=%ld first=(%ld,0x%08lx) last=(%ld,0x%08lx)\n",
               f->name, f->count, f->first_frame, (unsigned long)f->first_value,
               f->last_frame, (unsigned long)f->last_value);
    }
    free(data); return 0;
}
