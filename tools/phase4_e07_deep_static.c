#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define OVL_BASE 0x800b39a0u
#define MAX_CALLEES 128
#define MAX_GLOBALS 256

static const uint32_t callback_targets[] = {
    0x800b3d78u, 0x800b3b70u, 0x800b3bd4u, 0x800b3dc8u, 0x800b3f00u
};

typedef struct { uint8_t *p; size_t n; } Blob;
typedef struct {
    uint32_t insns, loads, stores, branches, returns, indirect_jumps;
    uint32_t callees[MAX_CALLEES]; size_t ncallees;
    uint32_t globals[MAX_GLOBALS]; size_t nglobals;
    int has_outside_tail;
} Stats;

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static int16_t simm(uint32_t w) { return (int16_t)(w & 0xffffu); }
static Blob read_blob(const char *path) {
    FILE *f = fopen(path, "rb"); Blob b = {0}; long n;
    if (!f) { fprintf(stderr, "open %s: %s\n", path, strerror(errno)); exit(2); }
    if (fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) exit(2);
    b.n = (size_t)n; b.p = malloc(b.n ? b.n : 1); if (!b.p) exit(2);
    if (b.n && fread(b.p, 1, b.n, f) != b.n) exit(2);
    fclose(f); return b;
}
static void sha_hex(const Blob *b, char out[65]) {
    unsigned char d[SHA256_DIGEST_LENGTH]; SHA256(b->p, b->n, d);
    for (int i=0;i<SHA256_DIGEST_LENGTH;i++) sprintf(out+i*2, "%02x", d[i]);
    out[64]=0;
}
static void add_unique(uint32_t *a, size_t *n, size_t cap, uint32_t v) {
    for (size_t i=0;i<*n;i++) if (a[i]==v) return;
    if (*n < cap) a[(*n)++] = v;
}
static uint32_t jtarget(uint32_t pc, uint32_t w) {
    return ((pc+4)&0xf0000000u) | ((w&0x03ffffffu)<<2);
}
static int is_load(unsigned op) {
    return op==0x20||op==0x21||op==0x22||op==0x23||op==0x24||op==0x25||op==0x26;
}
static int is_store(unsigned op) {
    return op==0x28||op==0x29||op==0x2a||op==0x2b||op==0x2e;
}
static int is_branch(unsigned op) { return op==1||op==4||op==5||op==6||op==7; }
static void account(const Blob *b, uint32_t pc, uint8_t *seen, Stats *s) {
    size_t off=(size_t)(pc-OVL_BASE);
    if (off+4>b->n || seen[off/4]) return;
    seen[off/4]=1; s->insns++;
    uint32_t w=rd32(b->p+off); unsigned op=w>>26;
    if (is_load(op)) s->loads++;
    if (is_store(op)) s->stores++;
}
static Stats cfg(const Blob *b, uint32_t start) {
    Stats s={0}; size_t words=(b->n+3)/4, qcap=words+16, qn=0, qi=0;
    uint32_t *q=calloc(qcap,sizeof(*q)); uint8_t *seen=calloc(words?words:1,1);
    if(!q||!seen) exit(2);
    q[qn++]=start;
    while(qi<qn && s.insns<1024) {
        uint32_t pc=q[qi++];
        if(pc<OVL_BASE) continue;
        size_t off=(size_t)(pc-OVL_BASE);
        if(off+4>b->n || seen[off/4]) continue;
        uint32_t w=rd32(b->p+off); unsigned op=w>>26, fn=w&63, rs=(w>>21)&31;
        account(b,pc,seen,&s);
        if(op==2 || op==3) {
            uint32_t t=jtarget(pc,w); account(b,pc+4,seen,&s);
            if(op==3) {
                add_unique(s.callees,&s.ncallees,MAX_CALLEES,t);
                if(qn<qcap) q[qn++]=pc+8;
            } else if(t>=OVL_BASE && (size_t)(t-OVL_BASE)<b->n) {
                if(qn<qcap) q[qn++]=t;
            } else s.has_outside_tail=1;
        } else if(op==0 && fn==8) {
            account(b,pc+4,seen,&s);
            if(rs==31) s.returns++; else s.indirect_jumps++;
        } else if(is_branch(op)) {
            s.branches++; account(b,pc+4,seen,&s);
            uint32_t t=pc+4+((int32_t)simm(w)<<2);
            if(t>=OVL_BASE && (size_t)(t-OVL_BASE)<b->n && qn<qcap) q[qn++]=t;
            if(qn<qcap) q[qn++]=pc+8;
        } else if(qn<qcap) q[qn++]=pc+4;
    }
    for(size_t i=0;i<words;i++) if(seen[i]) {
        uint32_t w=rd32(b->p+i*4);
        if((w>>26)!=0x0f) continue;
        unsigned rt=(w>>16)&31; uint32_t hi=(w&0xffffu)<<16;
        for(size_t d=1;d<=8 && i+d<words;d++) if(seen[i+d]) {
            uint32_t x=rd32(b->p+(i+d)*4); unsigned op=x>>26, rs=(x>>21)&31;
            if((is_load(op)||is_store(op)) && rs==rt)
                add_unique(s.globals,&s.nglobals,MAX_GLOBALS,hi+(int32_t)simm(x));
        }
    }
    free(q); free(seen); return s;
}
static const char *kind(const Blob *b, uint32_t t, const Stats *s) {
    size_t o=t-OVL_BASE; uint32_t w=(o+4<=b->n)?rd32(b->p+o):0;
    if(w==0x03e00008u) return "empty_stub";
    if(s->returns && s->insns<=12) return "small_leaf";
    if(s->returns) return "returning_cfg";
    if(s->has_outside_tail) return "outside_tail";
    if(s->indirect_jumps) return "indirect_dispatch";
    return "unbounded_or_data";
}
static void print_u32s(const uint32_t *a,size_t n) {
    putchar('[');
    for(size_t i=0;i<n;i++){if(i)putchar(',');printf("\"0x%08" PRIx32 "\"",a[i]);}
    putchar(']');
}
static size_t exe_off(uint32_t va,uint32_t load) {
    return 0x800u+(size_t)(va-load);
}
static uint32_t exew(const Blob *e,uint32_t va,uint32_t load) {
    size_t o=exe_off(va,load); return o+4<=e->n?rd32(e->p+o):0;
}
static void print_mem_offsets(const Blob *e,uint32_t lo,uint32_t hi,uint32_t load,
                              unsigned base,int stores) {
    int first=1; putchar('[');
    for(uint32_t pc=lo;pc<hi;pc+=4){
        uint32_t w=exew(e,pc,load); unsigned op=w>>26,rs=(w>>21)&31;
        if(rs==base && (stores?is_store(op):is_load(op))){
            if(!first) putchar(',');
            printf("%d",simm(w)); first=0;
        }
    }
    putchar(']');
}
int main(void) {
    Blob e=read_blob("REBUILD/files/SCUS_942.88"); char esha[65]; sha_hex(&e,esha);
    if(e.n<0x800 || memcmp(e.p,"PS-X EXE",8)) { fprintf(stderr,"not PS-X EXE\n"); return 2; }
    uint32_t load=rd32(e.p+0x18), size=rd32(e.p+0x1c), end=load+size;
    uint32_t init_calls[32], vm_calls[32], ipstores[256], tabrefs[64];
    size_t ni=0,nv=0,ns=0,nt=0;
    for(uint32_t pc=load;pc+4<=end;pc+=4){
        uint32_t w=exew(&e,pc,load),op=w>>26;
        if(op==3){
            uint32_t t=jtarget(pc,w);
            if(t==0x80049c30u)add_unique(init_calls,&ni,32,pc);
            if(t==0x8004c13cu)add_unique(vm_calls,&nv,32,pc);
        }
        if(op==0x2b && simm(w)==112)add_unique(ipstores,&ns,256,pc);
        if(op==0x0f && (w&0xffffu)==0x8007u){
            unsigned r=(w>>16)&31;
            for(unsigned d=1;d<=8 && pc+d*4<end;d++){
                uint32_t x=exew(&e,pc+d*4,load);
                if((x>>26)==0x23 && ((x>>21)&31)==r && simm(x)==31480)
                    add_unique(tabrefs,&nt,64,pc);
            }
        }
    }
    int selector_pattern =
        exew(&e,0x80049c78u,load)==0x9122000du &&
        exew(&e,0x80049c80u,load)==0x00021080u &&
        exew(&e,0x80049c84u,load)==0x3c018007u &&
        exew(&e,0x80049c8cu,load)==0x8c227af8u &&
        exew(&e,0x80049c94u,load)==0xad020070u;
    printf("{\n  \"schema\":\"abl.phase4.e07.deep_static.v1\",\n");
    printf("  \"exe\":{\"path\":\"REBUILD/files/SCUS_942.88\",\"sha256\":\"%s\","
           "\"load\":\"0x%08" PRIx32 "\",\"size\":%" PRIu32 "},\n",esha,load,size);
    printf("  \"selection_lifecycle\":{\"selector_pattern_exact\":%s,"
           "\"metadata_program_index_offset\":13,\"actor_vm_ip_offset\":112,"
           "\"program_table\":\"0x80077af8\",\"initializer_actor_stores\":",
           selector_pattern?"true":"false");
    print_mem_offsets(&e,0x80049c30u,0x80049e88u,load,8,1);
    printf(",\"initializer_metadata_loads\":");
    print_mem_offsets(&e,0x80049c30u,0x80049e88u,load,9,0);
    printf(",\"initializer_call_sites\":");print_u32s(init_calls,ni);
    printf(",\"interpreter_call_sites\":");print_u32s(vm_calls,nv);
    printf(",\"all_resident_sw_offset_112_candidates\":");print_u32s(ipstores,ns);
    printf(",\"program_table_lui_lw_reference_sites\":");print_u32s(tabrefs,nt);
    printf(",\"pool_init_call\":\"0x8004a664\",\"conditional_reinit_call\":\"0x8004d3f0\","
           "\"pool_loop_bound\":64},\n");
    glob_t g={0}; if(glob("REBUILD/files/LEVEL*/LEVEL*.BIN",0,NULL,&g)) return 2;
    printf("  \"overlays\":[\n"); size_t emitted=0, bounded=0, total=0;
    for(size_t fi=0;fi<g.gl_pathc;fi++){
        Blob b=read_blob(g.gl_pathv[fi]); char h[65];sha_hex(&b,h);
        for(size_t ti=0;ti<sizeof(callback_targets)/sizeof(callback_targets[0]);ti++){
            uint32_t t=callback_targets[ti];
            if((size_t)(t-OVL_BASE)+4>b.n) continue;
            Stats s=cfg(&b,t); total++;
            if(s.returns||s.has_outside_tail||s.indirect_jumps) bounded++;
            if(emitted++)printf(",\n");
            printf("    {\"file\":\"%s\",\"sha256\":\"%s\",\"target\":\"0x%08" PRIx32
                   "\",\"kind\":\"%s\",\"instructions\":%" PRIu32 ",\"loads\":%" PRIu32
                   ",\"stores\":%" PRIu32 ",\"branches\":%" PRIu32 ",\"returns\":%" PRIu32
                   ",\"indirect_jumps\":%" PRIu32 ",\"outside_tail\":%s,\"direct_callees\":",
                   g.gl_pathv[fi],h,t,kind(&b,t,&s),s.insns,s.loads,s.stores,s.branches,
                   s.returns,s.indirect_jumps,s.has_outside_tail?"true":"false");
            print_u32s(s.callees,s.ncallees);
            printf(",\"global_refs\":");print_u32s(s.globals,s.nglobals);printf("}");
        }
        free(b.p);
    }
    printf("\n  ],\n  \"summary\":{\"overlay_files\":%zu,"
           "\"address_file_pairs_in_bounds\":%zu,\"cfg_bounded_pairs\":%zu,"
           "\"cfg_unbounded_or_data_pairs\":%zu}\n}\n",
           g.gl_pathc,total,bounded,total-bounded);
    globfree(&g);free(e.p);return 0;
}
