#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { const char *label, *needle; } Check;

static char *load(const char *path) {
    FILE *f = fopen(path, "rb"); if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);
    char *s = malloc((size_t)n + 1); fread(s, 1, (size_t)n, f); fclose(f); s[n] = 0; return s;
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: %s callback_listing.s\n", argv[0]); return 2; }
    Check checks[] = {
        {"state load +0x44", "0x8004a198"},
        {"state-one compare", "0x8004a1a0"},
        {"flags load +0x5c", "0x8004a1b0"},
        {"test hit latch 0x1000", "0x8004a1b8"},
        {"clear latch with 0xefff", "0x8004a1c8"},
        {"require state one", "0x8004a1cc"},
        {"store cleared flags", "0x8004a1d0"},
        {"timer literal 0x19", "0x8004a1d4"},
        {"store timer +0x6c", "0x8004a1d8"},
        {"load motion +0x1c", "0x8004a1dc"},
        {"load motion +0x24", "0x8004a1e0"},
        {"double first motion", "0x8004a1e4"},
        {"double second motion", "0x8004a1e8"},
        {"store motion +0x1c", "0x8004a1ec"},
        {"store motion +0x24", "0x8004a1f0"}
    };
    char *text = load(argv[1]), *cursor = text;
    int failures = 0;
    for (size_t i = 0; i < sizeof checks / sizeof checks[0]; i++) {
        char *hit = strstr(cursor, checks[i].needle);
        printf("%-28s %s\n", checks[i].label, hit ? checks[i].needle : "MISSING");
        if (!hit) failures++; else cursor = hit + strlen(checks[i].needle);
    }
    printf("summary ordered_checks=%zu failures=%d semantics=state1_and_flag1000=>clear_flag1000,timer25,motion1c_x2,motion24_x2\n",
           sizeof checks / sizeof checks[0], failures);
    free(text); return failures != 0;
}
