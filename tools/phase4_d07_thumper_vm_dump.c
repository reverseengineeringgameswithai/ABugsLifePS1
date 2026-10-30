#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static uint16_t le16(const unsigned char *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }

int main(int argc, char **argv) {
    if (argc != 4) { fprintf(stderr, "usage: %s PSX_EXE start_ram end_ram\n", argv[0]); return 2; }
    unsigned long start = strtoul(argv[2], NULL, 0), end = strtoul(argv[3], NULL, 0);
    if (start < 0x80010000ul || end <= start || (start | end) & 1) return 2;
    FILE *f = fopen(argv[1], "rb"); if (!f) { perror(argv[1]); return 2; }
    for (unsigned long address = start; address < end; address += 2) {
        unsigned long offset = 0x800ul + address - 0x80010000ul;
        if (fseek(f, (long)offset, SEEK_SET)) return 2;
        unsigned char bytes[2]; if (fread(bytes, 1, 2, f) != 2) return 2;
        printf("%08lx:%04x%s", address, le16(bytes), ((address - start) & 6) == 6 ? "\n" : " ");
    }
    if (((end - start) & 7) != 0) putchar('\n');
    fclose(f); return 0;
}
