#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int line_address(const char *line, uint32_t *out) {
    for (const char *p = line; *p; ++p) {
        if (p[0] != '8' || p[1] != '0' || p[2] != '0') continue;
        unsigned long v = 0; int n = 0;
        if (sscanf(p, "%8lx%n", &v, &n) == 1 && n == 8) {
            char next = p[8];
            if (next == '\0' || !isxdigit((unsigned char)next)) {
                *out = (uint32_t)v;
                return 1;
            }
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s ASM START END\n", argv[0]);
        return 2;
    }
    char *tail = NULL;
    uint32_t start = (uint32_t)strtoul(argv[2], &tail, 0);
    if (!tail || *tail) return 2;
    uint32_t end = (uint32_t)strtoul(argv[3], &tail, 0);
    if (!tail || *tail || end < start) return 2;
    FILE *fp = fopen(argv[1], "rb");
    if (!fp) { fprintf(stderr, "%s: %s\n", argv[1], strerror(errno)); return 1; }
    char line[4096]; unsigned lines = 0, addressed = 0;
    while (fgets(line, sizeof(line), fp)) {
        ++lines; uint32_t pc;
        if (!line_address(line, &pc) || pc < start || pc > end) continue;
        ++addressed;
        printf("0x%08x\t%s", pc, line);
        if (!strchr(line, '\n')) putchar('\n');
    }
    fclose(fp);
    fprintf(stderr, "source=%s lines=%u selected=%u range=0x%08x..0x%08x\n",
            argv[1], lines, addressed, start, end);
    return addressed == 0;
}
