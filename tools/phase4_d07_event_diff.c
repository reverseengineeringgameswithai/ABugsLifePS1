#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { long frame, width, value; unsigned long address, pc; } Event;

static char *load(const char *path, size_t *size) {
    FILE *file = fopen(path, "rb");
    if (!file) { perror(path); exit(2); }
    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    rewind(file);
    char *data = malloc((size_t)length + 1);
    fread(data, 1, (size_t)length, file);
    fclose(file);
    data[length] = 0;
    *size = (size_t)length;
    return data;
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
    size_t size;
    char *data = load(path, &size), *cursor = data;
    long capacity = 2048;
    Event *events = malloc(sizeof(*events) * (size_t)capacity);
    *count = 0;
    while ((cursor = strstr(cursor, "\"address\":"))) {
        char *next = strstr(cursor + 10, "\"address\":");
        char *end = next ? next : data + size;
        long frame = number(cursor, end, "\"frame\"", -1);
        if (frame >= 0) {
            if (*count == capacity) {
                capacity *= 2;
                events = realloc(events, sizeof(*events) * (size_t)capacity);
            }
            events[(*count)++] = (Event){
                frame,
                number(cursor, end, "\"width\"", -1),
                number(cursor, end, "\"new_value\"", -1),
                hex_string(cursor, end, "\"address\""),
                hex_string(cursor, end, "\"instruction_pc\"")
            };
        }
        cursor += 10;
    }
    free(data);
    return events;
}

static int equal(Event a, Event b) {
    return a.frame == b.frame && a.width == b.width && a.value == b.value &&
           a.address == b.address && a.pc == b.pc;
}

static void print_event(const char *label, Event e) {
    printf("  %s frame=%ld addr=0x%08lx width=%ld new=0x%08lx writer=0x%08lx\n",
           label, e.frame, e.address, e.width, (unsigned long)e.value, e.pc);
}

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    long original_count, control_count;
    Event *original = parse(argv[1], &original_count);
    Event *control = parse(argv[2], &control_count);
    long i = 0, j = 0, differences = 0;
    while (i < original_count && j < control_count) {
        if (equal(original[i], control[j])) { i++; j++; continue; }
        if (i + 1 < original_count && equal(original[i + 1], control[j])) {
            print_event("original-only", original[i++]); differences++; continue;
        }
        if (j + 1 < control_count && equal(original[i], control[j + 1])) {
            print_event("control-only", control[j++]); differences++; continue;
        }
        print_event("original", original[i++]);
        print_event("control ", control[j++]);
        if (++differences > 20) break;
    }
    while (i < original_count) { print_event("original-tail", original[i++]); differences++; }
    while (j < control_count) { print_event("control-tail", control[j++]); differences++; }
    printf("summary original_events=%ld control_events=%ld differential_groups=%ld\n",
           original_count, control_count, differences);
    free(original);
    free(control);
    return 0;
}
