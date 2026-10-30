#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <limits.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <zstd.h>

#define RAM_SIZE 0x200000u
#define PLAYER_BASE 0x0a6500u
#define CONTACT_BASE 0x0b0d18u
#define CONTACT_COUNT 64u
#define CONTACT_STRIDE 0x38u
#define DANDELION_START 0x8005c818u
#define DANDELION_END 0x8005c918u
#define MAX_SAMPLES 4096u
#define MAX_FLOW_PCS 128u

typedef struct { const uint8_t *p, *end; const char *path; } Reader;
typedef struct {
    uint64_t frame, cycle;
    uint32_t movie, pc;
    int32_t x, y, z, vy;
    uint16_t mode, contact, field84, lockout, action88, power_flags;
    uint8_t kind13_count, kind13_slot, kind13_ttl;
    int32_t kind13_x, kind13_y, kind13_z;
    uint64_t handler_blocks;
} Sample;
typedef struct { uint32_t pc; uint64_t count; uint32_t frames; } FlowPc;

static Sample samples[MAX_SAMPLES];
static size_t sample_count;
static FlowPc flow_pcs[MAX_FLOW_PCS];
static size_t flow_pc_count;
static uint8_t *domains[4];
static uint32_t domain_sizes[4];
static uint64_t domain_hashes_checked;
static uint64_t changed_runs;

static void die(const char *what, const char *path) {
    fprintf(stderr, "phase4_b03_capsule_probe: %s%s%s\n", what, path ? ": " : "", path ? path : "");
    exit(1);
}
static void need(Reader *r, size_t n) { if ((size_t)(r->end-r->p) < n) die("truncated chunk", r->path); }
static uint8_t u8(Reader *r) { need(r,1); return *r->p++; }
static uint16_t u16(Reader *r) { need(r,2); uint16_t v=(uint16_t)r->p[0]|((uint16_t)r->p[1]<<8); r->p+=2; return v; }
static uint32_t u32(Reader *r) { need(r,4); uint32_t v=(uint32_t)r->p[0]|((uint32_t)r->p[1]<<8)|((uint32_t)r->p[2]<<16)|((uint32_t)r->p[3]<<24); r->p+=4; return v; }
static uint64_t u64(Reader *r) { uint64_t lo=u32(r), hi=u32(r); return lo|(hi<<32); }
static const uint8_t *take(Reader *r, size_t n) { need(r,n); const uint8_t *p=r->p; r->p+=n; return p; }
static uint16_t rd16(const uint8_t *p) { return (uint16_t)p[0]|((uint16_t)p[1]<<8); }
static int32_t rd32s(const uint8_t *p) { uint32_t v=(uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); return (int32_t)v; }

static uint8_t *decompress_file(const char *path, size_t *out_size) {
    struct stat st;
    if (stat(path,&st) != 0 || st.st_size <= 0) die("cannot stat compressed chunk",path);
    FILE *f=fopen(path,"rb"); if(!f) die("cannot open compressed chunk",path);
    uint8_t *src=malloc((size_t)st.st_size); if(!src) die("out of memory",NULL);
    if(fread(src,1,(size_t)st.st_size,f)!=(size_t)st.st_size) die("cannot read compressed chunk",path);
    fclose(f);
    unsigned long long n=ZSTD_getFrameContentSize(src,(size_t)st.st_size);
    if(n==ZSTD_CONTENTSIZE_ERROR || n==ZSTD_CONTENTSIZE_UNKNOWN || n>SIZE_MAX) die("unknown zstd content size",path);
    uint8_t *dst=malloc((size_t)n); if(!dst) die("out of memory",NULL);
    size_t got=ZSTD_decompress(dst,(size_t)n,src,(size_t)st.st_size); free(src);
    if(ZSTD_isError(got) || got!=(size_t)n) die("zstd decompression failed",path);
    *out_size=got; return dst;
}

static void add_flow(uint32_t pc, uint64_t count) {
    if(pc<DANDELION_START || pc>=DANDELION_END) return;
    for(size_t i=0;i<flow_pc_count;i++) if(flow_pcs[i].pc==pc) { flow_pcs[i].count+=count; flow_pcs[i].frames++; return; }
    if(flow_pc_count>=MAX_FLOW_PCS) die("too many handler flow PCs",NULL);
    flow_pcs[flow_pc_count++]=(FlowPc){pc,count,1};
}

static void capture_sample(uint64_t frame,uint64_t cycle,uint32_t movie,uint32_t pc,uint64_t handler_blocks) {
    if(sample_count>=MAX_SAMPLES) die("too many samples",NULL);
    const uint8_t *ram=domains[1];
    if(!ram || domain_sizes[1]!=RAM_SIZE) die("unexpected RAM size",NULL);
    Sample *s=&samples[sample_count++]; memset(s,0,sizeof(*s));
    s->frame=frame; s->cycle=cycle; s->movie=movie; s->pc=pc;
    s->x=rd32s(ram+PLAYER_BASE+0x00); s->y=rd32s(ram+PLAYER_BASE+0x04); s->z=rd32s(ram+PLAYER_BASE+0x08);
    s->vy=rd32s(ram+PLAYER_BASE+0x30); s->lockout=rd16(ram+PLAYER_BASE+0x7c);
    s->mode=rd16(ram+PLAYER_BASE+0x80); s->contact=rd16(ram+PLAYER_BASE+0x82);
    s->field84=rd16(ram+PLAYER_BASE+0x84); s->action88=rd16(ram+PLAYER_BASE+0x88);
    s->power_flags=rd16(ram+PLAYER_BASE+0x90); s->handler_blocks=handler_blocks;
    uint64_t best=UINT64_MAX;
    for(uint32_t i=0;i<CONTACT_COUNT;i++) {
        const uint8_t *rec=ram+CONTACT_BASE+i*CONTACT_STRIDE;
        uint16_t action=rd16(rec+0x20); uint8_t ttl=rec[0x22];
        if(action!=13 || ttl==0) continue;
        s->kind13_count++;
        int32_t x=rd32s(rec+0), y=rd32s(rec+4), z=rd32s(rec+8);
        int64_t dx=(int64_t)x-s->x, dy=(int64_t)y-s->y, dz=(int64_t)z-s->z;
        uint64_t d=(uint64_t)(dx*dx+dy*dy+dz*dz);
        if(d<best) { best=d; s->kind13_slot=(uint8_t)i; s->kind13_ttl=ttl; s->kind13_x=x; s->kind13_y=y; s->kind13_z=z; }
    }
}

static void parse_chunk(const char *path,uint32_t *expected_mode,uint32_t *expected_regs) {
    size_t raw_size; uint8_t *raw=decompress_file(path,&raw_size); Reader r={raw,raw+raw_size,path};
    if(memcmp(take(&r,8),"DSTCAP01",8)!=0) die("bad capsule magic",path);
    if(u32(&r)!=1) die("unsupported capsule version",path);
    uint32_t mode=u32(&r); (void)u64(&r);
    uint32_t regs=u32(&r);
    for(uint32_t i=0;i<regs;i++) { uint16_t n=u16(&r); (void)take(&r,n); }
    if(*expected_mode==UINT32_MAX) { *expected_mode=mode; *expected_regs=regs; }
    else if(mode!=*expected_mode || regs!=*expected_regs) die("chunk schema changed",path);
    while(r.p<r.end) {
        if(u8(&r)!=1) die("unknown record tag",path);
        uint64_t frame=u64(&r),cycle=u64(&r); uint32_t movie=u32(&r),pc=u32(&r); (void)u32(&r);
        for(uint32_t i=0;i<regs;i++) (void)u32(&r);
        for(int d=0;d<3;d++) {
            uint32_t id=u32(&r),size=u32(&r),runs=u32(&r); const uint8_t *expected=take(&r,32);
            if(id<1 || id>3) die("unknown domain id",path);
            if(!domains[id]) { domains[id]=calloc(1,size); domain_sizes[id]=size; if(!domains[id]) die("out of memory",NULL); }
            if(domain_sizes[id]!=size) die("domain size changed",path);
            for(uint32_t j=0;j<runs;j++) {
                uint32_t off=u32(&r),len=u32(&r); const uint8_t *data=take(&r,len);
                if((uint64_t)off+len>size) die("out-of-range delta",path);
                memcpy(domains[id]+off,data,len); changed_runs++;
            }
            uint8_t actual[SHA256_DIGEST_LENGTH]; SHA256(domains[id],size,actual);
            if(memcmp(actual,expected,32)!=0) die("domain reconstruction hash mismatch",path);
            domain_hashes_checked++;
        }
        uint64_t count=u64(&r), handler_blocks=0;
        for(uint64_t i=0;i<count;i++) {
            uint32_t flow_pc=u32(&r); uint64_t hits;
            if(mode==2) { uint32_t ins=u32(&r); (void)u64(&r); hits=ins; }
            else if(mode==1) hits=u64(&r);
            else if(mode==0) hits=0;
            else die("unknown block mode",path);
            if(flow_pc>=DANDELION_START && flow_pc<DANDELION_END) { add_flow(flow_pc,hits); handler_blocks+=hits; }
        }
        capture_sample(frame,cycle,movie,pc,handler_blocks);
    }
    free(raw);
}

static int cmp_flow(const void *a,const void *b) {
    const FlowPc *x=a,*y=b; if(x->pc<y->pc)return -1; if(x->pc>y->pc)return 1; return 0;
}
static void print_sample(const Sample *s) {
    printf("{\"movie\":%u,\"emulator_frame\":%" PRIu64 ",\"cycle\":%" PRIu64 ",\"x\":%d,\"y\":%d,\"z\":%d,\"vy\":%d,\"mode\":%u,\"contact\":%u,\"field84\":%u,\"action88\":%u,\"power_flags\":%u,\"handler_blocks\":%" PRIu64 ",\"kind13_count\":%u",s->movie,s->frame,s->cycle,s->x,s->y,s->z,s->vy,s->mode,s->contact,s->field84,s->action88,s->power_flags,s->handler_blocks,s->kind13_count);
    if(s->kind13_count) printf(",\"nearest_kind13\":{\"slot\":%u,\"ttl\":%u,\"x\":%d,\"y\":%d,\"z\":%d}",s->kind13_slot,s->kind13_ttl,s->kind13_x,s->kind13_y,s->kind13_z);
    printf("}");
}

int main(int argc,char **argv) {
    if(argc!=2) { fprintf(stderr,"usage: %s CAPSULE_DIRECTORY\n",argv[0]); return 2; }
    char pattern[PATH_MAX]; if(snprintf(pattern,sizeof(pattern),"%s/chunks/*.tcap.zst",argv[1])>=(int)sizeof(pattern)) die("path too long",argv[1]);
    glob_t g; int gr=glob(pattern,0,NULL,&g); if(gr!=0 || g.gl_pathc==0) die("no capsule chunks",pattern);
    uint32_t mode=UINT32_MAX,regs=0;
    for(size_t i=0;i<g.gl_pathc;i++) parse_chunk(g.gl_pathv[i],&mode,&regs);
    if(sample_count==0) die("capsule contains no frames",argv[1]);
    qsort(flow_pcs,flow_pc_count,sizeof(flow_pcs[0]),cmp_flow);

    int32_t min_y=INT32_MAX,max_y=INT32_MIN,min_vy=INT32_MAX,max_vy=INT32_MIN;
    uint32_t first_mode5=UINT32_MAX,last_mode5=0,first_handler=UINT32_MAX,last_handler=0;
    uint32_t first_kind13=UINT32_MAX,last_kind13=0; unsigned mode5_frames=0,kind13_frames=0;
    for(size_t i=0;i<sample_count;i++) {
        Sample *s=&samples[i]; if(s->y<min_y)min_y=s->y; if(s->y>max_y)max_y=s->y; if(s->vy<min_vy)min_vy=s->vy; if(s->vy>max_vy)max_vy=s->vy;
        if(s->mode==5) { if(first_mode5==UINT32_MAX)first_mode5=s->movie; last_mode5=s->movie; mode5_frames++; }
        if(s->handler_blocks) { if(first_handler==UINT32_MAX)first_handler=s->movie; last_handler=s->movie; }
        if(s->kind13_count) { if(first_kind13==UINT32_MAX)first_kind13=s->movie; last_kind13=s->movie; kind13_frames++; }
    }
    printf("{\n  \"schema\":\"abl-phase4-b03-capsule-probe-v1\",\n  \"capsule\":\"%s\",\n",argv[1]);
    printf("  \"validation\":{\"chunks\":%zu,\"records\":%zu,\"block_mode\":%u,\"register_count\":%u,\"domain_hashes_checked\":%" PRIu64 ",\"changed_runs\":%" PRIu64 ",\"parse_exact\":true},\n",g.gl_pathc,sample_count,mode,regs,domain_hashes_checked,changed_runs);
    printf("  \"trajectory\":{\"first_movie_frame\":%u,\"last_movie_frame\":%u,\"y_min\":%d,\"y_max\":%d,\"vertical_span\":%d,\"vy_min\":%d,\"vy_max\":%d},\n",samples[0].movie,samples[sample_count-1].movie,min_y,max_y,max_y-min_y,min_vy,max_vy);
    printf("  \"mode5_summary\":{\"first\":%u,\"last\":%u,\"sample_frames\":%u},\n",first_mode5,last_mode5,mode5_frames);
    printf("  \"handler_summary\":{\"first\":%u,\"last\":%u,\"flow_pcs\":[",first_handler,last_handler);
    for(size_t i=0;i<flow_pc_count;i++) { if(i)putchar(','); printf("{\"pc\":\"0x%08x\",\"count\":%" PRIu64 ",\"frames\":%u}",flow_pcs[i].pc,flow_pcs[i].count,flow_pcs[i].frames); }
    printf("]},\n  \"kind13_summary\":{\"first\":%u,\"last\":%u,\"sample_frames\":%u},\n",first_kind13,last_kind13,kind13_frames);
    printf("  \"events\":[\n");
    int first=1;
    for(size_t i=0;i<sample_count;i++) {
        Sample *s=&samples[i],*p=i?&samples[i-1]:NULL;
        int event=!p || s->handler_blocks || s->vy==-4096 || (p&&(s->mode!=p->mode || s->kind13_count!=p->kind13_count || s->action88!=p->action88));
        if (!event) continue;
        if (!first) printf(",\n");
        printf("    ");
        print_sample(s);
        first = 0;
    }
    printf("\n  ],\n  \"mode_spans\":[");
    size_t start=0; first=1;
    while(start<sample_count) { size_t end=start; while(end+1<sample_count && samples[end+1].mode==samples[start].mode)end++; if(!first)putchar(','); printf("{\"mode\":%u,\"first\":%u,\"last\":%u,\"frames\":%zu,\"start_y\":%d,\"end_y\":%d,\"min_vy\":",samples[start].mode,samples[start].movie,samples[end].movie,end-start+1,samples[start].y,samples[end].y); int32_t v=INT32_MAX; for(size_t i=start;i<=end;i++)if(samples[i].vy<v)v=samples[i].vy; printf("%d}",v); first=0; start=end+1; }
    printf("]\n}\n");
    globfree(&g); for(int i=1;i<=3;i++)free(domains[i]); return 0;
}
