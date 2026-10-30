/* Phase 4 E15: pristine resident-trigger and FMV.BIN CFG guard.
 *
 * Build:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror \
 *     -o /tmp/e15_static tools/phase4_e15_fmv_static.c
 * Run:
 *   /tmp/e15_static REBUILD/files/SCUS_942.88 \
 *     REBUILD/files/FMV/FMV.BIN /tmp/e15_reachable.txt
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BASE 0x800b5788u
#define ENTRY 0x800b6250u
#define TABLE 0x800b5aa4u
#define TABLE_COUNT 47u

typedef struct { uint8_t *p; size_t n; } Blob;
typedef struct {
    const Blob *bin;
    uint8_t *seen, *queued, *entry;
    uint32_t *queue;
    size_t words, head, tail;
} Cfg;

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static void die(const char *s) { fprintf(stderr, "e15_static: %s\n", s); exit(1); }
static Blob load(const char *path) {
    Blob b = {0}; FILE *f = fopen(path, "rb"); long z;
    if (!f) { perror(path); exit(2); }
    if (fseek(f, 0, SEEK_END) || (z = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) die("file size");
    b.n = (size_t)z; b.p = malloc(b.n ? b.n : 1);
    if (!b.p || (b.n && fread(b.p, 1, b.n, f) != b.n)) die("file read");
    fclose(f); return b;
}
static uint32_t exe_word(const Blob *exe, uint32_t a) {
    uint32_t load_addr, load_size; uint64_t o;
    if (exe->n < 0x800 || memcmp(exe->p, "PS-X EXE", 8)) die("PS-X EXE identity");
    load_addr = rd32(exe->p + 0x18); load_size = rd32(exe->p + 0x1c);
    if (a < load_addr || a - load_addr >= load_size) die("EXE address range");
    o = 0x800u + (uint64_t)(a - load_addr); if (o + 4 > exe->n) die("EXE file range");
    return rd32(exe->p + (size_t)o);
}
static const uint8_t *exe_bytes(const Blob *exe, uint32_t a, size_t n) {
    uint32_t load_addr = rd32(exe->p + 0x18), load_size = rd32(exe->p + 0x1c);
    uint64_t o;
    if (a < load_addr || (uint64_t)(a - load_addr) + n > load_size) die("EXE byte range");
    o = 0x800u + (uint64_t)(a - load_addr); if (o + n > exe->n) die("EXE byte file range");
    return exe->p + (size_t)o;
}
static void expect(const Blob *exe, uint32_t a, uint32_t w) {
    if (exe_word(exe, a) != w) { fprintf(stderr, "word mismatch at %08x\n", a); exit(1); }
}
static int inside(const Cfg *c, uint32_t a) {
    return a >= BASE && !(a & 3u) && (uint64_t)(a - BASE) + 4 <= c->bin->n;
}
static size_t ix(uint32_t a) { return (size_t)(a - BASE) / 4; }
static uint32_t word(const Cfg *c, uint32_t a) { return rd32(c->bin->p + a - BASE); }
static void enqueue(Cfg *c, uint32_t a) {
    size_t i; if (!inside(c, a)) return; i = ix(a);
    if (!c->queued[i]) { c->queued[i] = 1; c->queue[c->tail++] = a; }
}
static void seed(Cfg *c, uint32_t a) {
    if (!inside(c, a)) die("CFG seed range"); c->entry[ix(a)] = 1; enqueue(c, a);
}
static void delay(Cfg *c, uint32_t a) { if (inside(c, a)) c->seen[ix(a)] = 1; }
static uint32_t jump_target(uint32_t pc, uint32_t w) {
    return ((pc + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2);
}
static int is_branch(uint32_t op, uint32_t w) {
    return op == 1 || (op >= 4 && op <= 7) || (op >= 0x14 && op <= 0x17) ||
           (op >= 0x10 && op <= 0x13 && ((w >> 21) & 31u) == 8);
}
static void walk(Cfg *c) {
    while (c->head < c->tail) {
        uint32_t pc = c->queue[c->head++], w = word(c, pc), op = w >> 26;
        uint32_t rs = (w >> 21) & 31u, rt = (w >> 16) & 31u, fn = w & 63u;
        int32_t d = (int16_t)w; c->seen[ix(pc)] = 1;
        if (op == 2 || op == 3) {
            uint32_t t = jump_target(pc, w); delay(c, pc + 4);
            if (op == 3) { if (inside(c, t)) c->entry[ix(t)] = 1; enqueue(c, t); enqueue(c, pc + 8); }
            else enqueue(c, t);
        } else if (op == 0 && (fn == 8 || fn == 9)) {
            delay(c, pc + 4); if (fn == 9) enqueue(c, pc + 8);
        } else if (is_branch(op, w)) {
            uint32_t t = pc + 4 + (uint32_t)(d * 4); delay(c, pc + 4);
            if (op == 4 && rs == rt) enqueue(c, t);
            else if (op == 5 && rs == rt) enqueue(c, pc + 8);
            else { enqueue(c, t); enqueue(c, pc + 8); }
        } else if (!(op == 0 && (fn == 12 || fn == 13))) enqueue(c, pc + 4);
    }
}
static unsigned marked(const uint8_t *p, size_t n) {
    unsigned v = 0; for (size_t i = 0; i < n; i++) v += p[i] != 0; return v;
}
static unsigned unique_add(uint32_t *a, unsigned *n, uint32_t v) {
    unsigned i; for (i = 0; i < *n && a[i] != v; i++); if (i == *n) a[(*n)++] = v; return i;
}
static void write_map(const Cfg *c, const char *path) {
    FILE *f = fopen(path, "w"); if (!f) { perror(path); exit(2); }
    for (size_t i = 0; i < c->words; i++) if (c->seen[i]) fprintf(f, "%08x\n", BASE + (uint32_t)i * 4);
    fclose(f);
}

int main(int argc, char **argv) {
    static const uint32_t calls[9] = {0x8004fb5c,0x8004fb68,0x8004fb74,0x8004ffd4,0x800500d8,0x80050284,0x8005031c,0x8005036c,0x8005b788};
    static const uint8_t atab[16] = {0,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38};
    static const uint8_t btab[16] = {255,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39};
    static const uint32_t extras[] = {0x800b6634,0x800b8dd0,0x800b8f40,0x800b8fcc,0x800b9110,0x800b914c};
    Blob exe, fmv; Cfg c = {0}; uint32_t load_addr, load_size, ext[128]; unsigned call_n = 0, ext_n = 0;
    unsigned raw_jal = 0, jal = 0, internal = 0, external = 0, jr = 0, icall = 0, ijump = 0;
    if (argc != 4) { fprintf(stderr, "usage: %s SCUS FMV.BIN MAP_OUT\n", argv[0]); return 2; }
    exe = load(argv[1]); fmv = load(argv[2]); if (fmv.n != 509800 || (fmv.n & 3u)) die("FMV.BIN shape");
    load_addr = rd32(exe.p + 0x18); load_size = rd32(exe.p + 0x1c);
    for (uint32_t o = 0; o + 4 <= load_size; o += 4) if (rd32(exe.p + 0x800 + o) == 0x0c00f9f0u) {
        if (call_n >= 9 || load_addr + o != calls[call_n]) die("fmv_bin_load call frontier"); call_n++;
    }
    if (call_n != 9) die("resident call count");
    expect(&exe,0x8004fb58,0x24040001); expect(&exe,0x8004fb64,0x00002021); expect(&exe,0x8004fb70,0x2404002d);
    expect(&exe,0x8004ffac,0x90c6b88a); expect(&exe,0x8004ffd0,0xa026b88a); expect(&exe,0x8004ffd8,0x24840029);
    expect(&exe,0x800500d4,0x2404002e); expect(&exe,0x80050280,0x24040028); expect(&exe,0x80050318,0x90247fe3);
    expect(&exe,0x80050354,0x24040029); expect(&exe,0x8005b784,0x9024a08b);
    if (memcmp(exe_bytes(&exe,0x8007a08b,16),atab,16) || memcmp(exe_bytes(&exe,0x80077fe3,16),btab,16)) die("selector tables");
    c.bin=&fmv; c.words=fmv.n/4; c.seen=calloc(c.words,1); c.queued=calloc(c.words,1); c.entry=calloc(c.words,1); c.queue=malloc(c.words*sizeof(*c.queue));
    if(!c.seen||!c.queued||!c.entry||!c.queue)die("CFG allocation"); seed(&c,ENTRY);
    for(size_t i=0;i<TABLE_COUNT;i++)seed(&c,rd32(fmv.p+(TABLE-BASE)+i*4));
    for(size_t i=0;i<sizeof extras/sizeof extras[0];i++)seed(&c,extras[i]);
    for(size_t i=0;i<7;i++)seed(&c,rd32(fmv.p+(0x800b5b60u-BASE)+i*4)); walk(&c);
    for(size_t i=0;i<c.words;i++){
        uint32_t w=rd32(fmv.p+i*4),pc=BASE+(uint32_t)i*4,op=w>>26,fn=w&63u;if(op==3)raw_jal++;if(!c.seen[i])continue;
        if(op==3){uint32_t t=jump_target(pc,w);jal++;if(inside(&c,t))internal++;else{external++;unique_add(ext,&ext_n,t);}}
        if(op==0&&(fn==8||fn==9)){uint32_t rs=(w>>21)&31u;jr++;if(fn==9)icall++;else if(rs!=31)ijump++;}
    }
    if(marked(c.seen,c.words)!=2995||marked(c.entry,c.words)!=90||raw_jal!=538||jal!=156||internal!=64||external!=92||ext_n!=39||jr!=45||icall!=0||ijump!=2)die("reachable frontier");
    write_map(&c,argv[3]);
    printf("{\"resident_calls\":9,\"reachable_words\":2995,\"reachable_bytes\":11980,\"entries\":90,\"raw_jal\":538,\"reachable_jal\":156,\"internal_calls\":64,\"external_calls\":92,\"external_unique\":39,\"indirect_calls\":0,\"indirect_jumps\":2}\n");
    free(c.queue);free(c.entry);free(c.queued);free(c.seen);free(fmv.p);free(exe.p);return 0;
}
