#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_LINES = 8192, MAX_TEXT = 192, REG_COUNT = 32 };

typedef struct {
    const char *name;
    uint32_t address;
} Target;

static const Target targets[] = {
    {"player_x", 0x800a6500u}, {"player_y", 0x800a6504u},
    {"player_z", 0x800a6508u}, {"velocity_x", 0x800a652cu},
    {"velocity_y", 0x800a6530u}, {"velocity_z", 0x800a6534u},
    {"floor_y", 0x800a6548u}, {"carrier_offset", 0x800a655cu},
    {"indexed_binding", 0x800a657au}, {"air_state", 0x800a6580u},
    {"grounded", 0x800a6582u}, {"air_timer", 0x800a6584u},
    {"anim_index", 0x800a6588u}, {"player_flags", 0x800a6590u},
    {"plant_latch", 0x800a659eu}, {"carrier_flag", 0x800a65a3u}
};

typedef struct {
    char text[MAX_TEXT];
    char op[16];
    char args[MAX_TEXT];
    uint32_t pc;
    unsigned source_line;
} Instruction;

typedef struct {
    int known;
    uint32_t value;
} Value;

static void die(const char *what)
{
    fprintf(stderr, "%s: %s\n", what, strerror(errno));
    exit(1);
}

static char *trim(char *s)
{
    char *end;
    while (isspace((unsigned char)*s))
        s++;
    end = s + strlen(s);
    while (end > s && isspace((unsigned char)end[-1]))
        *--end = '\0';
    return s;
}

static int reg_index(const char *token)
{
    static const char *names[REG_COUNT] = {
        "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
        "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
        "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"
    };
    char buf[16];
    size_t n = 0;

    while (*token == '$' || isspace((unsigned char)*token))
        token++;
    while (*token && *token != ',' && *token != ')' &&
           !isspace((unsigned char)*token) && n + 1 < sizeof(buf))
        buf[n++] = (char)tolower((unsigned char)*token++);
    buf[n] = '\0';
    for (int i = 0; i < REG_COUNT; i++)
        if (!strcmp(buf, names[i]))
            return i;
    if (buf[0] == 'r' && isdigit((unsigned char)buf[1])) {
        long v = strtol(buf + 1, NULL, 10);
        if (v >= 0 && v < REG_COUNT)
            return (int)v;
    }
    return -1;
}

static int parse_number(const char *s, int32_t *out)
{
    char *end;
    long v;

    while (isspace((unsigned char)*s))
        s++;
    errno = 0;
    v = strtol(s, &end, 0);
    if (end == s || errno)
        return 0;
    while (isspace((unsigned char)*end))
        end++;
    if (*end && *end != ',' && *end != '(' && *end != ')')
        return 0;
    *out = (int32_t)v;
    return 1;
}

static int split_args(const char *args, char out[3][64])
{
    int count = 0;
    const char *p = args;

    while (*p && count < 3) {
        size_t n = 0;
        char *t;

        while (isspace((unsigned char)*p) || *p == ',')
            p++;
        while (*p && *p != ',' && n + 1 < 64)
            out[count][n++] = *p++;
        out[count][n] = '\0';
        t = trim(out[count]);
        if (t != out[count])
            memmove(out[count], t, strlen(t) + 1);
        count++;
    }
    return count;
}

static int memory_operand(const char *args, int32_t *offset, int *base)
{
    const char *lp = strrchr(args, '(');
    const char *rp = strrchr(args, ')');
    const char *start;
    char offbuf[48], regbuf[24];
    size_t n;

    if (!lp || !rp || rp < lp)
        return 0;
    start = lp;
    while (start > args && !isspace((unsigned char)start[-1]) && start[-1] != ',')
        start--;
    n = (size_t)(lp - start);
    if (n >= sizeof(offbuf))
        return 0;
    memcpy(offbuf, start, n);
    offbuf[n] = '\0';
    n = (size_t)(rp - lp - 1);
    if (n >= sizeof(regbuf))
        return 0;
    memcpy(regbuf, lp + 1, n);
    regbuf[n] = '\0';
    if (!parse_number(trim(offbuf), offset))
        return 0;
    *base = reg_index(trim(regbuf));
    return *base >= 0;
}

static const Target *find_target(uint32_t address)
{
    for (size_t i = 0; i < sizeof(targets) / sizeof(targets[0]); i++)
        if (targets[i].address == address)
            return &targets[i];
    return NULL;
}

static void json_string(const char *s)
{
    putchar('"');
    for (; *s; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') {
            putchar('\\');
            putchar(c);
        } else if (c == '\n') {
            fputs("\\n", stdout);
        } else if (c == '\t') {
            fputs("\\t", stdout);
        } else if (c >= 0x20) {
            putchar(c);
        }
    }
    putchar('"');
}

static int is_load(const char *op)
{
    return !strcmp(op, "lw") || !strcmp(op, "lh") || !strcmp(op, "lhu") ||
           !strcmp(op, "lb") || !strcmp(op, "lbu");
}

static int is_store(const char *op)
{
    return !strcmp(op, "sw") || !strcmp(op, "sh") || !strcmp(op, "sb");
}

static void kill_callers(Value r[REG_COUNT])
{
    static const int caller[] = {
        2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25
    };

    for (size_t i = 0; i < sizeof(caller) / sizeof(caller[0]); i++)
        r[caller[i]].known = 0;
}

static void emit_event(const char *name, const Instruction ins[], size_t nins,
                       size_t i, const Target *target, uint32_t ea,
                       const Value r[REG_COUNT], int source_reg, int store,
                       int *first_event)
{
    size_t lo = i > 5 ? i - 5 : 0;
    size_t hi = i + 5 < nins ? i + 5 : nins - 1;

    if (!*first_event)
        fputs(",\n", stdout);
    *first_event = 0;
    fputs("    {\"field\":", stdout);
    json_string(target->name);
    printf(",\"address\":\"0x%08" PRIx32 "\",\"access\":\"%s\","
           "\"pc\":\"0x%08" PRIx32 "\",\"file\":",
           ea, store ? "write" : "read", ins[i].pc);
    json_string(name);
    printf(",\"line\":%u,\"instruction\":", ins[i].source_line);
    json_string(ins[i].text);
    if (store && source_reg >= 0 && r[source_reg].known)
        printf(",\"source_constant\":%" PRIu32 ",\"source_hex\":\"0x%08" PRIx32 "\"",
               r[source_reg].value, r[source_reg].value);
    fputs(",\"context\":[", stdout);
    for (size_t j = lo; j <= hi; j++) {
        if (j != lo)
            putchar(',');
        printf("{\"pc\":\"0x%08" PRIx32 "\",\"instruction\":", ins[j].pc);
        json_string(ins[j].text);
        putchar('}');
    }
    fputs("]}", stdout);
}

static void analyze_file(const char *directory, const char *name, int *first_event,
                         uint64_t *instruction_total, uint64_t counts[],
                         size_t count_n)
{
    char path[1024], raw[512];
    Instruction ins[MAX_LINES];
    size_t nins = 0;
    unsigned source_line = 0;
    unsigned base;
    FILE *fp;
    Value r[REG_COUNT] = {{0, 0}};
    int kill_after = 0;

    if (sscanf(name, "%8x", &base) != 1)
        return;
    snprintf(path, sizeof(path), "%s/%s", directory, name);
    fp = fopen(path, "r");
    if (!fp)
        die(path);
    while (fgets(raw, sizeof(raw), fp)) {
        char work[512], *p, *hash, *space;
        size_t oplen;

        source_line++;
        snprintf(work, sizeof(work), "%s", raw);
        hash = strchr(work, '#');
        if (hash)
            *hash = '\0';
        p = trim(work);
        if (!*p || (p[0] == '.' && strncmp(p, ".word", 5)) ||
            p[strlen(p) - 1] == ':')
            continue;
        if (nins == MAX_LINES) {
            fprintf(stderr, "%s too large\n", path);
            exit(1);
        }
        snprintf(ins[nins].text, sizeof(ins[nins].text), "%s", p);
        space = p;
        while (*space && !isspace((unsigned char)*space))
            space++;
        oplen = (size_t)(space - p);
        if (oplen >= sizeof(ins[nins].op))
            oplen = sizeof(ins[nins].op) - 1;
        memcpy(ins[nins].op, p, oplen);
        ins[nins].op[oplen] = '\0';
        for (size_t j = 0; ins[nins].op[j]; j++)
            ins[nins].op[j] =
                (char)tolower((unsigned char)ins[nins].op[j]);
        snprintf(ins[nins].args, sizeof(ins[nins].args), "%s", trim(space));
        ins[nins].pc = (uint32_t)base + (uint32_t)(nins * 4u);
        ins[nins].source_line = source_line;
        nins++;
    }
    fclose(fp);
    *instruction_total += nins;

    r[0].known = 1;
    r[0].value = 0;
    if (!strncmp(name, "80048138_", 9)) {
        r[4].known = 1;
        r[4].value = 0x800a6500u;
    }
    for (size_t i = 0; i < nins; i++) {
        char a[3][64] = {{0}};
        int argc = split_args(ins[i].args, a);
        int rd = argc > 0 ? reg_index(a[0]) : -1;
        int rs = argc > 1 ? reg_index(a[1]) : -1;
        int rt = argc > 2 ? reg_index(a[2]) : -1;
        int32_t imm;
        int schedule_kill = 0;

        if (is_load(ins[i].op) || is_store(ins[i].op)) {
            int32_t off;
            int br;
            if (memory_operand(ins[i].args, &off, &br) && r[br].known) {
                uint32_t ea = r[br].value + (uint32_t)off;
                const Target *target = find_target(ea);
                if (target) {
                    size_t ti = (size_t)(target - targets);
                    if (ti < count_n)
                        counts[ti]++;
                    emit_event(name, ins, nins, i, target, ea, r, rd,
                               is_store(ins[i].op), first_event);
                }
            }
        }

        if (!strcmp(ins[i].op, "lui") && rd >= 0 && argc >= 2 &&
            parse_number(a[1], &imm)) {
            r[rd].known = 1;
            r[rd].value = (uint32_t)imm << 16;
        } else if ((!strcmp(ins[i].op, "addiu") ||
                    !strcmp(ins[i].op, "addi")) &&
                   rd >= 0 && rs >= 0 && argc >= 3 && r[rs].known &&
                   parse_number(a[2], &imm)) {
            r[rd].known = 1;
            r[rd].value = r[rs].value + (uint32_t)imm;
        } else if ((!strcmp(ins[i].op, "ori") ||
                    !strcmp(ins[i].op, "andi") ||
                    !strcmp(ins[i].op, "xori")) &&
                   rd >= 0 && rs >= 0 && argc >= 3 && r[rs].known &&
                   parse_number(a[2], &imm)) {
            uint32_t u = (uint32_t)imm & 0xffffu;
            r[rd].known = 1;
            if (!strcmp(ins[i].op, "ori"))
                r[rd].value = r[rs].value | u;
            else if (!strcmp(ins[i].op, "andi"))
                r[rd].value = r[rs].value & u;
            else
                r[rd].value = r[rs].value ^ u;
        } else if ((!strcmp(ins[i].op, "addu") ||
                    !strcmp(ins[i].op, "or")) &&
                   rd >= 0 && rs >= 0 && rt >= 0) {
            if (r[rs].known && r[rt].known) {
                r[rd].known = 1;
                r[rd].value = !strcmp(ins[i].op, "addu")
                                  ? r[rs].value + r[rt].value
                                  : r[rs].value | r[rt].value;
            } else {
                r[rd].known = 0;
            }
        } else if ((!strcmp(ins[i].op, "sll") ||
                    !strcmp(ins[i].op, "srl") ||
                    !strcmp(ins[i].op, "sra")) &&
                   rd >= 0 && rs >= 0 && argc >= 3 && r[rs].known &&
                   parse_number(a[2], &imm)) {
            unsigned sh = (unsigned)imm & 31u;
            r[rd].known = 1;
            if (!strcmp(ins[i].op, "sll"))
                r[rd].value = r[rs].value << sh;
            else if (!strcmp(ins[i].op, "srl"))
                r[rd].value = r[rs].value >> sh;
            else
                r[rd].value = (uint32_t)((int32_t)r[rs].value >> sh);
        } else if (is_load(ins[i].op) && rd >= 0) {
            r[rd].known = 0;
        } else if (!strncmp(ins[i].op, "jal", 3) ||
                   !strcmp(ins[i].op, "bal")) {
            schedule_kill = 1;
        } else if (rd > 0 && strcmp(ins[i].op, "sw") &&
                   strcmp(ins[i].op, "sh") && strcmp(ins[i].op, "sb") &&
                   strcmp(ins[i].op, "beq") && strcmp(ins[i].op, "bne") &&
                   ins[i].op[0] != 'b' && strcmp(ins[i].op, "j") &&
                   strcmp(ins[i].op, "jr") && strcmp(ins[i].op, "nop") &&
                   strcmp(ins[i].op, ".word")) {
            r[rd].known = 0;
        }
        r[0].known = 1;
        r[0].value = 0;
        if (kill_after)
            kill_callers(r);
        kill_after = schedule_kill;
    }
}

static int suffix_s(const char *name)
{
    size_t n = strlen(name);
    return n > 2 && !strcmp(name + n - 2, ".s");
}

static int cmp_names(const void *a, const void *b)
{
    const char *const *aa = a;
    const char *const *bb = b;
    return strcmp(*aa, *bb);
}

int main(int argc, char **argv)
{
    const char *directory =
        argc > 1 ? argv[1] : "asm/hand_written";
    DIR *dir = opendir(directory);
    struct dirent *de;
    char **names = NULL;
    size_t n = 0, cap = 0;
    uint64_t instructions = 0;
    uint64_t counts[sizeof(targets) / sizeof(targets[0])] = {0};
    int first_event = 1;

    if (!dir)
        die(directory);
    while ((de = readdir(dir)) != NULL) {
        if (!suffix_s(de->d_name))
            continue;
        if (n == cap) {
            cap = cap ? cap * 2 : 256;
            names = realloc(names, cap * sizeof(*names));
            if (!names)
                die("realloc");
        }
        names[n] = strdup(de->d_name);
        if (!names[n])
            die("strdup");
        n++;
    }
    closedir(dir);
    qsort(names, n, sizeof(*names), cmp_names);

    printf("{\n"
           "  \"schema\":\"phase4_b03_glide_state_static_v1\",\n"
           "  \"method\":\"C11 textual MIPS constant-propagation xref over "
           "retained hand-written ASM\",\n"
           "  \"events\":[\n");
    for (size_t i = 0; i < n; i++)
        analyze_file(directory, names[i], &first_event, &instructions,
                     counts, sizeof(counts) / sizeof(counts[0]));
    fputs("\n  ],\n  \"summary\":{\n", stdout);
    printf("    \"files_scanned\":%zu,\n"
           "    \"instructions_scanned\":%" PRIu64 ",\n"
           "    \"field_event_counts\":{",
           n, instructions);
    for (size_t i = 0; i < sizeof(targets) / sizeof(targets[0]); i++) {
        if (i)
            putchar(',');
        printf("\n      \"%s\":%" PRIu64, targets[i].name, counts[i]);
    }
    fputs("\n    }\n  }\n}\n", stdout);
    for (size_t i = 0; i < n; i++)
        free(names[i]);
    free(names);
    return 0;
}
