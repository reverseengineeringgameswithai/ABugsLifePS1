/* Phase 4 A01: guard the pristine ASM facts used by the move/run model.
 *
 * This intentionally analyzes the checked-in ASM listing rather than a patched
 * executable. Run from the repository root; an optional first argument selects
 * another directory containing the same pristine listing filenames.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct check {
    const char *file;
    const char *pc;
    const char *fragment;
    int found;
};

static struct check checks[] = {
    {"80047ebc.s", "0x80047fdc", "0x2378", 0},
    {"80047ebc.s", "0x80047ffc", "0x237c", 0},
    {"80047ebc.s", "0x80048044", "0x6528", 0},
    {"80048138.s", "0x80048150", "addiu s5, zero, 0x700", 0},
    {"80048138.s", "0x80048154", "addiu t1, zero, 0x800", 0},
    {"80048138.s", "0x8004815c", "addiu t1, zero, 0x50", 0},
    {"80048138.s", "0x8004819c", "addiu t1, zero, 0x100", 0},
    {"80048138.s", "0x800481a0", "addiu s6, zero, 0x40", 0},
    {"80048138.s", "0x800481b4", "addiu fp, zero, 0x400", 0},
    {"80048138.s", "0x80048494", "andi v0, a0, 0x300", 0},
    {"80048138.s", "0x800484a0", "addiu s5, zero, 0x300", 0},
    {"80048138.s", "0x800490d8", "addiu v0, v0, -0x20", 0},
    {"80048138.s", "0x80049100", "addiu v0, v0, 0x20", 0},
    {"80048138.s", "0x80049140", "jal fcn.80047ebc", 0},
    {"80048138.s", "0x80049158", "sra s5, t1, 0xe", 0},
    {"80048138.s", "0x80049250", "andi a0, v0, 0xfff", 0},
    {"80048138.s", "0x80049278", "srav v0, a0, s2", 0},
    {"80048138.s", "0x80049358", "addu s2, s2, t1", 0},
    {"80048138.s", "0x8004937c", "subu s2, s2, t1", 0},
    {"80048138.s", "0x80049394", "addu s3, s3, s6", 0},
    {"80048138.s", "0x800493b0", "subu s3, s3, s6", 0},
    {"80048138.s", "0x800493e4", "addu v0, t1, s6", 0},
    {"80048138.s", "0x800493e8", "addu s3, s3, v0", 0},
    {"80048138.s", "0x800494ac", "sw s3, 0x38(s1)", 0},
    {"80048138.s", "0x800494b0", "sw s2, 0x3c(s1)", 0},
    {"80048138.s", "0x80049524", "sw v0, 0x2c(s1)", 0},
    {"80048138.s", "0x80049540", "sw v0, 0x34(s1)", 0},
    {"80048138.s", "0x80049558", "sw v0, 0x10(s1)", 0},
    {"80048138.s", "0x8004955c", "sw v1, 0x14(s1)", 0},
    {"80048138.s", "0x80049564", "sw a2, 0x18(s1)", 0},
    {"80048138.s", "0x800495c8", "jal fcn.8003633c", 0},
    {"8003633c_FUNC_8003633C.s", "0x80036374", "lw v0, 4(s7)", 0},
    {"8003633c_FUNC_8003633C.s", "0x8003637c", "addiu v0, v0, -0xc80", 0},
    {"8003633c_FUNC_8003633C.s", "0x80036cb8", "sb s1, (s6)", 0},
    {"8003633c_FUNC_8003633C.s", "0x80036cc0", "sb s1, 1(s6)", 0},
    {"8003633c_FUNC_8003633C.s", "0x80036ce8", "sw v0, (s7)", 0},
    {"800563d4.s", "0x80056474", "lhu v1, 0x2488(v1)", 0},
    {"800563d4.s", "0x8005647c", "andi v0, v1, 0xf0", 0},
    {"800563d4.s", "0x80056654", "sh v0, 0x6588(at)", 0},
    {"800563d4.s", "0x800569ac", "sh", 0},
};

static int scan_file(const char *root, const char *name)
{
    char path[1024];
    char line[1024];
    FILE *fp;
    size_t i;

    if (snprintf(path, sizeof(path), "%s/%s", root, name) >= (int)sizeof(path))
        return -1;
    fp = fopen(path, "r");
    if (!fp) {
        perror(path);
        return -1;
    }
    while (fgets(line, sizeof(line), fp)) {
        for (i = 0; i < sizeof(checks) / sizeof(checks[0]); ++i) {
            if (!checks[i].found && strcmp(checks[i].file, name) == 0 &&
                strstr(line, checks[i].pc) && strstr(line, checks[i].fragment))
                checks[i].found = 1;
        }
    }
    fclose(fp);
    return 0;
}

int main(int argc, char **argv)
{
    const char *root = argc > 1 ? argv[1] : "asm/nonmatchings/resident";
    const char *files[] = {
        "80047ebc.s", "80048138.s", "8003633c_FUNC_8003633C.s", "800563d4.s"
    };
    size_t i;
    int missing = 0;

    for (i = 0; i < sizeof(files) / sizeof(files[0]); ++i)
        if (scan_file(root, files[i]) != 0)
            return 2;
    for (i = 0; i < sizeof(checks) / sizeof(checks[0]); ++i) {
        if (!checks[i].found) {
            fprintf(stderr, "missing %s %s: %s\n",
                    checks[i].file, checks[i].pc, checks[i].fragment);
            ++missing;
        }
    }
    printf("A01 pristine ASM guard: %zu checks, %d missing\n",
           sizeof(checks) / sizeof(checks[0]), missing);
    return missing ? 1 : 0;
}
