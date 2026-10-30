#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <dirent.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define TARGET 0x800A65A2u
#define LINE_CAP 4096
#define REG_COUNT 32

typedef struct { int known; uint32_t value; } Reg;
static const char *reg_names[REG_COUNT] = {
    "zero","at","v0","v1","a0","a1","a2","a3",
    "t0","t1","t2","t3","t4","t5","t6","t7",
    "s0","s1","s2","s3","s4","s5","s6","s7",
    "t8","t9","k0","k1","gp","sp","fp","ra"
};

static int reg_id(const char *s) {
    while (*s == '$') ++s;
    for (int i = 0; i < REG_COUNT; ++i)
        if (strcmp(s, reg_names[i]) == 0) return i;
    return -1;
}

static int suffix(const char *s, const char *x) {
    size_t n = strlen(s), m = strlen(x);
    return n >= m && strcmp(s + n - m, x) == 0;
}

static int parse_num(const char *s, int32_t *out) {
    char *end = NULL;
    long v = strtol(s, &end, 0);
    if (end == s) return 0;
    *out = (int32_t)v;
    return 1;
}

static void clean_token(char *s) {
    char *d = s;
    for (; *s; ++s) {
        if (*s != ',' && *s != '$') *d++ = (char)tolower((unsigned char)*s);
    }
    *d = '\0';
}

static int parse_mem(const char *operand, int32_t *off, int *base) {
    char tmp[128], off_s[128], base_s[128];
    snprintf(tmp, sizeof(tmp), "%s", operand);
    clean_token(tmp);
    char *lp = strchr(tmp, '('), *rp = strchr(tmp, ')');
    if (!lp || !rp || rp < lp) return 0;
    *lp = '\0'; *rp = '\0';
    snprintf(off_s, sizeof(off_s), "%s", tmp[0] ? tmp : "0");
    snprintf(base_s, sizeof(base_s), "%s", lp + 1);
    return parse_num(off_s, off) && ((*base = reg_id(base_s)) >= 0);
}

static int overlaps(uint32_t address, unsigned width) {
    return address <= TARGET && TARGET < address + width;
}

static void scan_file(const char *path) {
    FILE *fp = fopen(path, "r");
    if (!fp) return;
    Reg r[REG_COUNT] = {{0}};
    r[0].known = 1; r[0].value = 0;
    char line[LINE_CAP];
    unsigned long line_no = 0;
    int memset_delay = 0;
    uint32_t memset_pc = 0;

    while (fgets(line, sizeof(line), fp)) {
        ++line_no;
        char *p = strstr(line, "0x800");
        unsigned pc, word;
        char op[32] = {0}, a[128] = {0}, b[128] = {0}, c[128] = {0};
        if (!p || sscanf(p, "0x%x %x %31s %127s %127s %127s", &pc, &word, op, a, b, c) < 3)
            continue;
        (void)word;
        clean_token(op); clean_token(a); clean_token(b); clean_token(c);

        int dst = reg_id(a), rs = reg_id(b), rt = reg_id(c);
        int32_t imm = 0;
        if (!strcmp(op, "lui") && dst >= 0 && parse_num(b, &imm)) {
            r[dst].known = 1; r[dst].value = (uint32_t)imm << 16;
        } else if ((!strcmp(op, "addiu") || !strcmp(op, "addi")) && dst >= 0 && rs >= 0 && parse_num(c, &imm)) {
            if (r[rs].known) { r[dst].known = 1; r[dst].value = r[rs].value + (uint32_t)imm; }
            else r[dst].known = 0;
        } else if (!strcmp(op, "ori") && dst >= 0 && rs >= 0 && parse_num(c, &imm)) {
            if (r[rs].known) { r[dst].known = 1; r[dst].value = r[rs].value | (uint32_t)(uint16_t)imm; }
            else r[dst].known = 0;
        } else if (!strcmp(op, "move") && dst >= 0 && rs >= 0) {
            r[dst] = r[rs];
        } else if ((!strcmp(op, "addu") || !strcmp(op, "or")) && dst >= 0 && rs >= 0 && rt >= 0) {
            if (rt == 0) r[dst] = r[rs];
            else if (rs == 0) r[dst] = r[rt];
            else r[dst].known = 0;
        } else if (!strcmp(op, "lw") || !strcmp(op, "lh") || !strcmp(op, "lhu") ||
                   !strcmp(op, "lb") || !strcmp(op, "lbu")) {
            if (dst >= 0) r[dst].known = 0;
        } else if (!strcmp(op, "sb") || !strcmp(op, "sh") || !strcmp(op, "sw")) {
            int base; int32_t off;
            if (parse_mem(b, &off, &base) && r[base].known) {
                unsigned width = !strcmp(op, "sb") ? 1u : (!strcmp(op, "sh") ? 2u : 4u);
                uint32_t addr = r[base].value + (uint32_t)off;
                if (overlaps(addr, width))
                    printf("STORE file=%s line=%lu pc=0x%08x op=%s address=0x%08x width=%u source=%s text=%s",
                           path, line_no, pc, op, addr, width, a, line);
            }
        } else if (dst > 0 && strcmp(op, "jal") && strcmp(op, "j") && strcmp(op, "jr") &&
                   op[0] != 'b' && strcmp(op, "nop") && strcmp(op, ".word")) {
            r[dst].known = 0;
        }

        if (memset_delay) {
            if (r[4].known && r[5].known && r[6].known) {
                uint32_t start = r[4].value, length = r[6].value;
                if (r[5].value == 0 && start <= TARGET && TARGET - start < length)
                    printf("ZEROFILL file=%s call_pc=0x%08x address=0x%08x length=%u covers=0x%08x\n",
                           path, memset_pc, start, length, TARGET);
            }
            memset_delay = 0;
        }
        if (!strcmp(op, "jal") && strstr(p, "8005f7ac")) {
            memset_delay = 1;
            memset_pc = pc;
        }
    }
    fclose(fp);
}

static void walk(const char *path) {
    struct stat st;
    if (lstat(path, &st) != 0) return;
    if (S_ISREG(st.st_mode)) { if (suffix(path, ".s")) scan_file(path); return; }
    if (!S_ISDIR(st.st_mode)) return;
    DIR *d = opendir(path);
    if (!d) return;
    struct dirent *e;
    while ((e = readdir(d))) {
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, "..")) continue;
        size_t n = strlen(path) + strlen(e->d_name) + 2;
        char *child = malloc(n);
        if (!child) exit(2);
        snprintf(child, n, "%s/%s", path, e->d_name);
        walk(child); free(child);
    }
    closedir(d);
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: %s ASM_ROOT\n", argv[0]); return 2; }
    walk(argv[1]);
    return 0;
}
