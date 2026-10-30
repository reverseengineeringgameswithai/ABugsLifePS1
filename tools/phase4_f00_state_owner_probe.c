/* phase4_f00_state_owner_probe.c -- decide F00_training's state OWNERSHIP from bytes.
 *
 * WHY THIS EXISTS
 * ---------------
 * Three separate registries make claims about the address 0x800B4A3C, and none of
 * them can be checked by reading a registry:
 *
 *   1. config/semantic_state.yaml registers `original.training_step` there with a
 *      declared range 0..13 and a declared WRITER at an overlay address. Overlay
 *      addresses in this game are keyed GLOBALLY with no image field, because every
 *      per-level overlay loads at the same base (region A). The same VA therefore
 *      names real content in most of the twenty overlay images, and the registry
 *      cannot say which one it meant.
 *   2. analysis/phase3_xrefs.json says the address has TWO resident readers in
 *      `gameplay_state_machine` and ZERO writers, and states in its own
 *      `declared_writers_in_overlay_space` note that it cannot see the declared
 *      writer at all: "overlay code is not part of the resident EXE image, so this
 *      scan cannot see it. Verifying it needs the overlay blob."
 *   3. analysis/phase3_ownership_graph.json attributes those same two reader PCs to
 *      THREE different rows, which is the collision the address-keying produces.
 *
 * So the questions this tool answers, all from bytes:
 *   (a) do the two claimed resident reader PCs actually compute 0x800B4A3C?
 *   (b) is there a writer for it, and in WHICH overlay image?
 *   (c) how ambiguous is the address -- how many of the supplied images even extend
 *       far enough to contain it, and how many actually reference it?
 *   (d) does a claimed pointer SEQUENCE (an indirect jump table asserted only in RE
 *       pseudocode) exist verbatim in any image, and at what address?
 *
 * The caller supplies every address and every candidate from a pinned artifact; this
 * tool re-types nothing. Instruction decoding lives here, in compiled C, per the
 * project's standing rule.
 *
 * REFERENCE RECOVERY. Absolute addresses on MIPS are materialized as lui+addiu,
 * lui+ori, or reached $gp-relative. All three are scanned (lui+ori is scanned
 * because a previous campaign missed half a census by scanning lui+addiu only). A
 * rolling per-register high-half table is kept and invalidated whenever the register
 * is redefined or after a bounded distance, so a stale lui cannot manufacture a hit.
 * Loads/stores through a register whose value was not materialized in range are
 * reported as UNRESOLVED rather than silently dropped.
 *
 * usage: phase4_f00_state_owner_probe OUT.json
 *          --exe PATH --exe-load-va HEX --gp HEX
 *          --overlay-base HEX --pinned PATH --images PATH [PATH...]
 *          --targets HEX[,HEX...]
 *          [--claimed-readers HEX[,HEX...]] [--claimed-writers HEX[,HEX...]]
 *          [--seq HEX[,HEX...]] [--decode HEX[,HEX...]]
 * build: gcc -std=c11 -O2 -Wall -Wextra -Werror \
 *          tools/phase4_f00_state_owner_probe.c -o /tmp/f00_probe -lcrypto
 */
#define _GNU_SOURCE

#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_IMAGES 64
#define MAX_ADDRS  64
#define MAX_SEQ    64
#define MAX_SITES  512
#define HI_LIFETIME 64          /* instructions a materialized high half stays live */

struct blob {
    const char *path;
    uint8_t *buf;
    long n;
    uint32_t va;                /* virtual address of byte 0 */
    char sha256[65];
};

struct site {
    uint32_t pc;
    uint32_t insn;
    uint32_t ea;
    const char *op;
    const char *how;
    int base_reg;
    int32_t imm;
};

static void die(const char *m)
{
    fprintf(stderr, "%s\n", m);
    exit(2);
}

static void digest_hex(const uint8_t *b, size_t n, char *out)
{
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    uint8_t d[64];
    unsigned len = 0, i;

    if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
        EVP_DigestUpdate(ctx, b, n) != 1 || EVP_DigestFinal_ex(ctx, d, &len) != 1)
        die("digest failed");
    EVP_MD_CTX_free(ctx);
    for (i = 0; i < len; i++)
        sprintf(out + i * 2, "%02x", d[i]);
    out[len * 2] = 0;
}

static uint8_t *slurp(const char *path, long *out_n)
{
    FILE *f = fopen(path, "rb");
    uint8_t *b;
    long n;

    if (!f) {
        perror(path);
        exit(2);
    }
    if (fseek(f, 0, SEEK_END) != 0)
        die("seek failed");
    n = ftell(f);
    rewind(f);
    if (n <= 0) {
        fprintf(stderr, "%s: empty\n", path);
        exit(2);
    }
    b = malloc((size_t)n);
    if (!b || fread(b, 1, (size_t)n, f) != (size_t)n)
        die("read failed");
    fclose(f);
    *out_n = n;
    return b;
}

static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

/* --- minimal MIPS I decode, only what a data-reference census needs --- */
#define OP(i)   ((i) >> 26)
#define RS(i)   (((i) >> 21) & 31)
#define RT(i)   (((i) >> 16) & 31)
#define RD(i)   (((i) >> 11) & 31)
#define IMM(i)  ((int32_t)(int16_t)((i) & 0xFFFF))
#define UIMM(i) ((uint32_t)((i) & 0xFFFF))

static const char *mem_op_name(uint32_t insn)
{
    switch (OP(insn)) {
    case 0x20: return "lb";
    case 0x21: return "lh";
    case 0x22: return "lwl";
    case 0x23: return "lw";
    case 0x24: return "lbu";
    case 0x25: return "lhu";
    case 0x26: return "lwr";
    case 0x28: return "sb";
    case 0x29: return "sh";
    case 0x2A: return "swl";
    case 0x2B: return "sw";
    case 0x2E: return "swr";
    case 0x32: return "lwc2";
    case 0x3A: return "swc2";
    default:   return NULL;
    }
}

static int is_store(uint32_t insn)
{
    switch (OP(insn)) {
    case 0x28: case 0x29: case 0x2A: case 0x2B: case 0x2E: case 0x3A: return 1;
    default: return 0;
    }
}

/* Which GPR does this instruction define? -1 = none / unknown-safe. */
static int dest_reg(uint32_t insn)
{
    uint32_t op = OP(insn), fn = insn & 0x3F;

    if (insn == 0)
        return -1;                              /* nop */
    switch (op) {
    case 0x00:                                  /* SPECIAL */
        if (fn == 0x08)                         /* jr */
            return -1;
        if (fn == 0x09)                         /* jalr */
            return (int)RD(insn);
        if (fn == 0x0C || fn == 0x0D)           /* syscall/break */
            return -1;
        if (fn == 0x10 || fn == 0x12)           /* mfhi/mflo */
            return (int)RD(insn);
        if (fn == 0x11 || fn == 0x13)           /* mthi/mtlo */
            return -1;
        if (fn == 0x18 || fn == 0x19 || fn == 0x1A || fn == 0x1B)  /* mult/div */
            return -1;
        return (int)RD(insn);
    case 0x01:                                  /* REGIMM: bltzal/bgezal write ra */
        if (RT(insn) == 0x10 || RT(insn) == 0x11)
            return 31;
        return -1;
    case 0x02:                                  /* j */
        return -1;
    case 0x03:                                  /* jal */
        return 31;
    case 0x04: case 0x05: case 0x06: case 0x07: /* branches */
        return -1;
    case 0x08: case 0x09: case 0x0A: case 0x0B:
    case 0x0C: case 0x0D: case 0x0E: case 0x0F: /* addi..lui */
        return (int)RT(insn);
    case 0x10: case 0x11: case 0x12: case 0x13: /* COPz */
        if (RS(insn) == 0x00 || RS(insn) == 0x02) /* mfc/cfc write rt */
            return (int)RT(insn);
        return -1;
    case 0x20: case 0x21: case 0x22: case 0x23:
    case 0x24: case 0x25: case 0x26:            /* loads */
        return (int)RT(insn);
    default:
        return -1;
    }
}

struct scan_ctx {
    uint32_t targets[MAX_ADDRS];
    int ntargets;
    uint32_t gp;
    int gp_valid;
    struct site sites[MAX_ADDRS][MAX_SITES];
    int nsites[MAX_ADDRS];
    long unresolved_mem_ops;
    long total_mem_ops;
    long materializations[MAX_ADDRS];
};

static int target_index(struct scan_ctx *c, uint32_t ea)
{
    int i;
    for (i = 0; i < c->ntargets; i++)
        if (c->targets[i] == ea)
            return i;
    return -1;
}

static void add_site(struct scan_ctx *c, int ti, uint32_t pc, uint32_t insn,
                     uint32_t ea, const char *op, const char *how, int base,
                     int32_t imm)
{
    struct site *s;
    if (ti < 0 || c->nsites[ti] >= MAX_SITES)
        return;
    s = &c->sites[ti][c->nsites[ti]++];
    s->pc = pc;
    s->insn = insn;
    s->ea = ea;
    s->op = op;
    s->how = how;
    s->base_reg = base;
    s->imm = imm;
}

/* Linear scan of one blob for references to any target address. */
static void scan_blob(struct scan_ctx *c, const struct blob *b)
{
    uint32_t hi[32];
    int hi_valid[32];
    long hi_age[32];
    uint32_t full[32];
    int full_valid[32];
    long full_age[32];
    long i, words = b->n / 4;

    memset(hi_valid, 0, sizeof(hi_valid));
    memset(full_valid, 0, sizeof(full_valid));
    memset(hi, 0, sizeof(hi));
    memset(full, 0, sizeof(full));
    memset(hi_age, 0, sizeof(hi_age));
    memset(full_age, 0, sizeof(full_age));

    for (i = 0; i < words; i++) {
        uint32_t insn = rd32(b->buf + i * 4);
        uint32_t pc = b->va + (uint32_t)(i * 4);
        uint32_t op = OP(insn);
        int d;
        const char *mo;

        /* expire stale high halves so a distant lui cannot manufacture a hit */
        for (d = 0; d < 32; d++) {
            if (hi_valid[d] && i - hi_age[d] > HI_LIFETIME)
                hi_valid[d] = 0;
            if (full_valid[d] && i - full_age[d] > HI_LIFETIME)
                full_valid[d] = 0;
        }

        mo = mem_op_name(insn);
        if (mo) {
            int base = (int)RS(insn);
            int32_t imm = IMM(insn);
            uint32_t ea = 0;
            const char *how = NULL;

            c->total_mem_ops++;
            if (base == 28 && c->gp_valid) {
                ea = c->gp + (uint32_t)imm;
                how = "gp_relative";
            } else if (full_valid[base]) {
                ea = full[base] + (uint32_t)imm;
                how = "materialized_base";
            } else if (hi_valid[base]) {
                ea = hi[base] + (uint32_t)imm;
                how = "lui_plus_offset";
            }
            if (how) {
                int ti = target_index(c, ea);
                if (ti >= 0)
                    add_site(c, ti, pc, insn, ea, mo, how, base, imm);
            } else {
                c->unresolved_mem_ops++;
            }
        }

        /* address materialization, recorded even when no load/store follows */
        if (op == 0x09 || op == 0x0D) {         /* addiu / ori */
            int rs = (int)RS(insn), rt = (int)RT(insn);
            if (hi_valid[rs]) {
                uint32_t v = (op == 0x09) ? hi[rs] + (uint32_t)IMM(insn)
                                          : hi[rs] | UIMM(insn);
                int ti = target_index(c, v);
                if (ti >= 0) {
                    c->materializations[ti]++;
                    add_site(c, ti, pc, insn, v,
                             (op == 0x09) ? "addiu" : "ori",
                             (op == 0x09) ? "lui_addiu_materialize"
                                          : "lui_ori_materialize", rs, IMM(insn));
                }
                full[rt] = v;
                full_valid[rt] = 1;
                full_age[rt] = i;
                hi_valid[rt] = 0;
                continue;
            }
        }

        d = dest_reg(insn);
        if (op == 0x0F) {                       /* lui */
            int rt = (int)RT(insn);
            hi[rt] = UIMM(insn) << 16;
            hi_valid[rt] = 1;
            hi_age[rt] = i;
            full_valid[rt] = 0;
            continue;
        }
        if (d >= 0) {
            hi_valid[d] = 0;
            full_valid[d] = 0;
        }
    }
}

/* Decode one instruction at an arbitrary VA inside a blob, if it is covered. */
static int decode_at(const struct blob *b, uint32_t va, uint32_t *insn_out)
{
    if (va < b->va || va + 4 > b->va + (uint32_t)b->n || (va & 3))
        return 0;
    *insn_out = rd32(b->buf + (va - b->va));
    return 1;
}

/* Resolve the effective address of a load/store at `va` by walking backwards for
 * the lui (and optional addiu/ori) that built its base register. */
static int resolve_ea_at(const struct blob *b, uint32_t va, uint32_t gp, int gp_valid,
                         uint32_t *ea_out, const char **how_out, uint32_t *insn_out)
{
    uint32_t insn;
    int base;
    int32_t imm;
    long back;

    if (!decode_at(b, va, &insn))
        return 0;
    *insn_out = insn;
    if (!mem_op_name(insn))
        return 0;
    base = (int)RS(insn);
    imm = IMM(insn);
    if (base == 28 && gp_valid) {
        *ea_out = gp + (uint32_t)imm;
        *how_out = "gp_relative";
        return 1;
    }
    for (back = 1; back <= HI_LIFETIME; back++) {
        uint32_t pva = va - (uint32_t)(back * 4), pi;
        if (!decode_at(b, pva, &pi))
            break;
        if (OP(pi) == 0x0F && (int)RT(pi) == base) {
            *ea_out = (UIMM(pi) << 16) + (uint32_t)imm;
            *how_out = "lui_plus_offset";
            return 1;
        }
        if ((OP(pi) == 0x09 || OP(pi) == 0x0D) && (int)RT(pi) == base) {
            long b2;
            int rs = (int)RS(pi);
            for (b2 = back + 1; b2 <= HI_LIFETIME; b2++) {
                uint32_t p2va = va - (uint32_t)(b2 * 4), p2;
                if (!decode_at(b, p2va, &p2))
                    break;
                if (OP(p2) == 0x0F && (int)RT(p2) == rs) {
                    uint32_t v = (OP(pi) == 0x09) ? (UIMM(p2) << 16) + (uint32_t)IMM(pi)
                                                  : (UIMM(p2) << 16) | UIMM(pi);
                    *ea_out = v + (uint32_t)imm;
                    *how_out = (OP(pi) == 0x09) ? "lui_addiu_base" : "lui_ori_base";
                    return 1;
                }
                if (dest_reg(p2) == rs)
                    break;
            }
            break;
        }
        if (dest_reg(pi) == base)
            break;
    }
    *how_out = "unresolved_register_base";
    return 0;
}

static int parse_hex_list(const char *s, uint32_t *out, int max)
{
    int n = 0;
    const char *p = s;
    while (*p && n < max) {
        char *end;
        unsigned long v = strtoul(p, &end, 0);
        if (end == p)
            break;
        out[n++] = (uint32_t)v;
        p = end;
        while (*p == ',' || *p == ' ')
            p++;
    }
    return n;
}

static void jstr(FILE *f, const char *s)
{
    fputc('"', f);
    for (; *s; s++) {
        if (*s == '"' || *s == '\\')
            fprintf(f, "\\%c", *s);
        else if ((unsigned char)*s < 0x20)
            fprintf(f, "\\u%04x", *s);
        else
            fputc(*s, f);
    }
    fputc('"', f);
}

int main(int argc, char **argv)
{
    const char *out_path = NULL, *exe_path = NULL, *pinned_path = NULL;
    const char *image_paths[MAX_IMAGES];
    int nimages = 0, i, j, k, mode = 0;
    uint32_t exe_va = 0, gp = 0, ovl_base = 0;
    uint32_t targets[MAX_ADDRS], readers[MAX_ADDRS], writers[MAX_ADDRS];
    uint32_t seq[MAX_SEQ], decode_list[MAX_ADDRS];
    int ntargets = 0, nreaders = 0, nwriters = 0, nseq = 0, ndecode = 0;
    struct blob exe, images[MAX_IMAGES];
    int pinned_idx = -1;
    FILE *f;

    if (argc < 3)
        die("usage: phase4_f00_state_owner_probe OUT.json --exe PATH --exe-load-va HEX "
            "--gp HEX --overlay-base HEX --pinned PATH --images PATH... "
            "--targets HEX[,HEX...] [--claimed-readers L] [--claimed-writers L] "
            "[--seq L] [--decode L]");
    out_path = argv[1];

    for (i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "--exe")) { exe_path = argv[++i]; mode = 0; }
        else if (!strcmp(argv[i], "--exe-load-va")) { exe_va = (uint32_t)strtoul(argv[++i], NULL, 0); mode = 0; }
        else if (!strcmp(argv[i], "--gp")) { gp = (uint32_t)strtoul(argv[++i], NULL, 0); mode = 0; }
        else if (!strcmp(argv[i], "--overlay-base")) { ovl_base = (uint32_t)strtoul(argv[++i], NULL, 0); mode = 0; }
        else if (!strcmp(argv[i], "--pinned")) { pinned_path = argv[++i]; mode = 0; }
        else if (!strcmp(argv[i], "--targets")) { ntargets = parse_hex_list(argv[++i], targets, MAX_ADDRS); mode = 0; }
        else if (!strcmp(argv[i], "--claimed-readers")) { nreaders = parse_hex_list(argv[++i], readers, MAX_ADDRS); mode = 0; }
        else if (!strcmp(argv[i], "--claimed-writers")) { nwriters = parse_hex_list(argv[++i], writers, MAX_ADDRS); mode = 0; }
        else if (!strcmp(argv[i], "--seq")) { nseq = parse_hex_list(argv[++i], seq, MAX_SEQ); mode = 0; }
        else if (!strcmp(argv[i], "--decode")) { ndecode = parse_hex_list(argv[++i], decode_list, MAX_ADDRS); mode = 0; }
        else if (!strcmp(argv[i], "--images")) mode = 1;
        else if (mode == 1) {
            if (nimages >= MAX_IMAGES)
                die("too many images");
            image_paths[nimages++] = argv[i];
        } else {
            fprintf(stderr, "unexpected argument %s\n", argv[i]);
            return 2;
        }
    }
    if (!exe_path || !exe_va || !gp || !ovl_base || !pinned_path || !nimages || !ntargets)
        die("missing required argument");

    exe.path = exe_path;
    exe.buf = slurp(exe_path, &exe.n);
    exe.va = exe_va;
    digest_hex(exe.buf, (size_t)exe.n, exe.sha256);
    /* PS-EXE: 2048-byte header, image follows and loads at exe_va. */
    if (exe.n <= 2048)
        die("exe too small");
    exe.buf += 2048;
    exe.n -= 2048;

    for (i = 0; i < nimages; i++) {
        images[i].path = image_paths[i];
        images[i].buf = slurp(image_paths[i], &images[i].n);
        images[i].va = ovl_base;
        digest_hex(images[i].buf, (size_t)images[i].n, images[i].sha256);
        if (!strcmp(image_paths[i], pinned_path))
            pinned_idx = i;
    }
    if (pinned_idx < 0)
        die("--pinned is not among --images");

    f = fopen(out_path, "w");
    if (!f)
        die("cannot open output");

    fprintf(f, "{\n");
    fprintf(f, " \"_comment\": \"Who reads and writes F00_training's registered state "
               "address, decided from bytes across the resident EXE and every overlay "
               "image. Overlay VAs are keyed globally with no image field, so an "
               "address alone names no file. Regenerate: "
               "tools/phase4_f00_state_owner_probe.c\",\n");
    fprintf(f, " \"schema\": \"abl-phase4-f00-state-owner-probe/1\",\n");
    fprintf(f, " \"generated_by\": \"tools/phase4_f00_state_owner_probe.c\",\n");
    fprintf(f, " \"reference_recovery\": \"lui+addiu, lui+ori and $gp-relative are all "
               "scanned; a materialized high half expires after %d instructions or when "
               "its register is redefined, and memory ops through an unrecovered base "
               "are counted as UNRESOLVED rather than dropped\",\n", HI_LIFETIME);
    fprintf(f, " \"gp\": \"0x%08X\",\n", gp);
    fprintf(f, " \"overlay_load_base\": \"0x%08X\",\n", ovl_base);
    fprintf(f, " \"exe\": {\"path\": ");
    jstr(f, exe_path);
    fprintf(f, ", \"sha256\": \"%s\", \"load_va\": \"0x%08X\", \"image_bytes\": %ld},\n",
            exe.sha256, exe_va, exe.n);
    fprintf(f, " \"pinned_image\": ");
    jstr(f, pinned_path);
    fprintf(f, ",\n");
    fprintf(f, " \"images_scanned\": %d,\n", nimages);

    /* --- targets: resident census, then per-image census --- */
    fprintf(f, " \"targets\": [\n");
    for (k = 0; k < ntargets; k++) {
        struct scan_ctx rc;
        int images_covering = 0, images_referencing = 0, pinned_refs = 0;
        int pinned_writes = 0, pinned_reads = 0;
        long resident_refs;

        memset(&rc, 0, sizeof(rc));
        rc.ntargets = 1;
        rc.targets[0] = targets[k];
        rc.gp = gp;
        rc.gp_valid = 1;
        scan_blob(&rc, &exe);
        resident_refs = rc.nsites[0];

        fprintf(f, "  {\"address\": \"0x%08X\",\n", targets[k]);
        fprintf(f, "   \"resident_reference_count\": %ld,\n", resident_refs);
        fprintf(f, "   \"resident_unresolved_mem_ops\": %ld,\n", rc.unresolved_mem_ops);
        fprintf(f, "   \"resident_total_mem_ops\": %ld,\n", rc.total_mem_ops);
        fprintf(f, "   \"resident_sites\": [");
        for (i = 0; i < rc.nsites[0]; i++)
            fprintf(f, "%s{\"pc\": \"0x%08X\", \"insn\": \"0x%08X\", \"op\": \"%s\", "
                       "\"how\": \"%s\"}", i ? ", " : "",
                    rc.sites[0][i].pc, rc.sites[0][i].insn, rc.sites[0][i].op,
                    rc.sites[0][i].how);
        fprintf(f, "],\n");

        fprintf(f, "   \"images\": [");
        for (j = 0; j < nimages; j++) {
            struct scan_ctx ic;
            int covers = (targets[k] >= ovl_base &&
                          targets[k] < ovl_base + (uint32_t)images[j].n);
            memset(&ic, 0, sizeof(ic));
            ic.ntargets = 1;
            ic.targets[0] = targets[k];
            ic.gp = gp;
            ic.gp_valid = 1;
            scan_blob(&ic, &images[j]);
            if (covers)
                images_covering++;
            if (ic.nsites[0] > 0)
                images_referencing++;
            if (j == pinned_idx) {
                pinned_refs = ic.nsites[0];
                for (i = 0; i < ic.nsites[0]; i++) {
                    uint32_t in = ic.sites[0][i].insn;
                    if (mem_op_name(in)) {
                        if (is_store(in))
                            pinned_writes++;
                        else
                            pinned_reads++;
                    }
                }
            }
            fprintf(f, "%s\n    {\"path\": ", j ? "," : "");
            jstr(f, images[j].path);
            fprintf(f, ", \"bytes\": %ld, \"extent_covers_address\": %s, "
                       "\"reference_count\": %d, \"sites\": [",
                    images[j].n, covers ? "true" : "false", ic.nsites[0]);
            for (i = 0; i < ic.nsites[0]; i++)
                fprintf(f, "%s{\"pc\": \"0x%08X\", \"insn\": \"0x%08X\", \"op\": \"%s\", "
                           "\"how\": \"%s\", \"store\": %s}", i ? ", " : "",
                        ic.sites[0][i].pc, ic.sites[0][i].insn, ic.sites[0][i].op,
                        ic.sites[0][i].how,
                        mem_op_name(ic.sites[0][i].insn) && is_store(ic.sites[0][i].insn)
                            ? "true" : "false");
            fprintf(f, "]}");
        }
        fprintf(f, "\n   ],\n");
        fprintf(f, "   \"images_whose_extent_covers_the_address\": %d,\n", images_covering);
        fprintf(f, "   \"images_referencing_the_address\": %d,\n", images_referencing);
        fprintf(f, "   \"pinned_image_reference_count\": %d,\n", pinned_refs);
        fprintf(f, "   \"pinned_image_store_count\": %d,\n", pinned_writes);
        fprintf(f, "   \"pinned_image_load_count\": %d}%s\n",
                pinned_reads, k + 1 < ntargets ? "," : "");
    }
    fprintf(f, " ],\n");

    /* --- claimed resident readers: decode them --- */
    fprintf(f, " \"claimed_resident_readers\": [");
    for (i = 0; i < nreaders; i++) {
        uint32_t insn = 0, ea = 0;
        const char *how = "not_in_image";
        int ok = decode_at(&exe, readers[i], &insn);
        int resolved = 0;
        int matches = 0;

        if (ok)
            resolved = resolve_ea_at(&exe, readers[i], gp, 1, &ea, &how, &insn);
        for (j = 0; j < ntargets && resolved; j++)
            if (targets[j] == ea)
                matches = 1;
        fprintf(f, "%s\n  {\"pc\": \"0x%08X\", \"in_resident_image\": %s, "
                   "\"insn\": \"0x%08X\", \"op\": ", i ? "," : "",
                readers[i], ok ? "true" : "false", insn);
        if (ok && mem_op_name(insn))
            jstr(f, mem_op_name(insn));
        else
            fprintf(f, "null");
        fprintf(f, ", \"base_reg\": %d, \"imm\": %d, \"resolution\": ",
                ok ? (int)RS(insn) : -1, ok ? IMM(insn) : 0);
        jstr(f, how);
        fprintf(f, ", \"effective_address\": ");
        if (resolved)
            fprintf(f, "\"0x%08X\"", ea);
        else
            fprintf(f, "null");
        fprintf(f, ", \"matches_a_target\": %s}", matches ? "true" : "false");
    }
    fprintf(f, "\n ],\n");

    /* --- claimed overlay writers: decode them in every image --- */
    fprintf(f, " \"claimed_overlay_writers\": [");
    for (i = 0; i < nwriters; i++) {
        fprintf(f, "%s\n  {\"pc\": \"0x%08X\", \"per_image\": [", i ? "," : "", writers[i]);
        for (j = 0; j < nimages; j++) {
            uint32_t insn = 0, ea = 0;
            const char *how = "not_in_image";
            int ok = decode_at(&images[j], writers[i], &insn);
            int resolved = 0, matches = 0, store = 0;

            if (ok) {
                resolved = resolve_ea_at(&images[j], writers[i], gp, 1, &ea, &how, &insn);
                store = mem_op_name(insn) && is_store(insn);
            }
            for (k = 0; k < ntargets && resolved; k++)
                if (targets[k] == ea)
                    matches = 1;
            fprintf(f, "%s\n   {\"image\": ", j ? "," : "");
            jstr(f, images[j].path);
            fprintf(f, ", \"covered\": %s, \"insn\": \"0x%08X\", \"op\": ",
                    ok ? "true" : "false", insn);
            if (ok && mem_op_name(insn))
                jstr(f, mem_op_name(insn));
            else
                fprintf(f, "null");
            fprintf(f, ", \"is_store\": %s, \"resolution\": ", store ? "true" : "false");
            jstr(f, how);
            fprintf(f, ", \"effective_address\": ");
            if (resolved)
                fprintf(f, "\"0x%08X\"", ea);
            else
                fprintf(f, "null");
            fprintf(f, ", \"matches_a_target\": %s}", matches ? "true" : "false");
        }
        fprintf(f, "\n  ]}");
    }
    fprintf(f, "\n ],\n");

    /* --- claimed pointer sequence (an indirect table asserted in prose) --- */
    fprintf(f, " \"claimed_sequence\": {\"length\": %d, \"words\": [", nseq);
    for (i = 0; i < nseq; i++)
        fprintf(f, "%s\"0x%08X\"", i ? ", " : "", seq[i]);
    fprintf(f, "], \"found_in\": [");
    {
        int printed = 0;
        for (j = 0; j < nimages && nseq > 0; j++) {
            long off;
            for (off = 0; off + (long)nseq * 4 <= images[j].n; off += 4) {
                int all = 1;
                for (i = 0; i < nseq; i++)
                    if (rd32(images[j].buf + off + i * 4) != seq[i]) {
                        all = 0;
                        break;
                    }
                if (all) {
                    int inside = 1;
                    for (i = 0; i < nseq; i++)
                        if (seq[i] < ovl_base ||
                            seq[i] >= ovl_base + (uint32_t)images[j].n)
                            inside = 0;
                    fprintf(f, "%s\n  {\"image\": ", printed++ ? "," : "");
                    jstr(f, images[j].path);
                    fprintf(f, ", \"address\": \"0x%08X\", \"file_offset\": %ld, "
                               "\"all_words_inside_this_image\": %s}",
                            ovl_base + (uint32_t)off, off, inside ? "true" : "false");
                }
            }
        }
        fprintf(f, printed ? "\n " : "");
    }
    fprintf(f, "]},\n");

    /* --- raw decode of caller-named addresses in the pinned image --- */
    fprintf(f, " \"decoded\": [");
    for (i = 0; i < ndecode; i++) {
        uint32_t insn = 0;
        int ok = decode_at(&images[pinned_idx], decode_list[i], &insn);
        fprintf(f, "%s\n  {\"address\": \"0x%08X\", \"in_pinned_image\": %s, "
                   "\"word\": \"0x%08X\", \"op_field\": %u, \"mem_op\": ",
                i ? "," : "", decode_list[i], ok ? "true" : "false", insn,
                ok ? OP(insn) : 0);
        if (ok && mem_op_name(insn))
            jstr(f, mem_op_name(insn));
        else
            fprintf(f, "null");
        fprintf(f, "}");
    }
    fprintf(f, "\n ]\n}\n");
    fclose(f);

    printf("scanned %d images + resident EXE for %d target address(es); wrote %s\n",
           nimages, ntargets, out_path);
    return 0;
}
