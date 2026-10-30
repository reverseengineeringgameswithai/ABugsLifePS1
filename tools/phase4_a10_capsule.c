#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

#define PLAYER 0x0A6500u
#define MAX_FRAMES 2000

typedef struct {
    const uint8_t *p, *end;
} Reader;

typedef struct {
    uint64_t frame, cycle;
    uint32_t movie, pc;
    int32_t x, y, z, vx, vy, vz, floor_y;
    uint16_t anim0, anim1, timer7a, state, grounded, f84, f86, f88;
    uint32_t carried_off;
    uint8_t carry_mode;
    uint64_t blocks;
} Sample;

static Sample samples[MAX_FRAMES];
static size_t nsamples;

static void die(const char *msg) { fprintf(stderr, "%s\n", msg); exit(1); }
static uint8_t u8(Reader *r) { if (r->p + 1 > r->end) die("truncated u8"); return *r->p++; }
static uint16_t u16(Reader *r) { uint16_t v; if (r->p + 2 > r->end) die("truncated u16"); memcpy(&v,r->p,2); r->p+=2; return v; }
static uint32_t u32(Reader *r) { uint32_t v; if (r->p + 4 > r->end) die("truncated u32"); memcpy(&v,r->p,4); r->p+=4; return v; }
static uint64_t u64(Reader *r) { uint64_t v; if (r->p + 8 > r->end) die("truncated u64"); memcpy(&v,r->p,8); r->p+=8; return v; }
static const uint8_t *take(Reader *r, size_t n) { const uint8_t *p=r->p; if (r->p+n>r->end) die("truncated bytes"); r->p+=n; return p; }
static int32_t s32at(const uint8_t *p, size_t o) { int32_t v; memcpy(&v,p+o,4); return v; }
static uint32_t u32at(const uint8_t *p, size_t o) { uint32_t v; memcpy(&v,p+o,4); return v; }
static uint16_t u16at(const uint8_t *p, size_t o) { uint16_t v; memcpy(&v,p+o,2); return v; }

static uint8_t *decompress_file(const char *path, size_t *out_size) {
    FILE *f=fopen(path,"rb"); if(!f){perror(path);exit(1);} fseek(f,0,SEEK_END); long n=ftell(f); rewind(f);
    uint8_t *src=malloc((size_t)n); if(!src)die("oom src"); if(fread(src,1,(size_t)n,f)!=(size_t)n)die("read failed"); fclose(f);
    unsigned long long want=ZSTD_getFrameContentSize(src,(size_t)n);
    if(want==ZSTD_CONTENTSIZE_ERROR||want==ZSTD_CONTENTSIZE_UNKNOWN)die("bad zstd size");
    uint8_t *dst=malloc((size_t)want); if(!dst)die("oom dst");
    size_t got=ZSTD_decompress(dst,(size_t)want,src,(size_t)n); free(src);
    if(ZSTD_isError(got)||got!=(size_t)want)die("zstd decode failed"); *out_size=got; return dst;
}

static void sha_check(const uint8_t *image, size_t n, const uint8_t expected[32], uint64_t frame, uint32_t domain) {
    uint8_t actual[32]; SHA256(image,n,actual);
    if(memcmp(actual,expected,32)){fprintf(stderr,"sha mismatch frame=%"PRIu64" domain=%u\n",frame,domain);exit(1);}
}

static int same_pos(const Sample *a,const Sample *b){return a->x==b->x&&a->y==b->y&&a->z==b->z;}

static void print_transition(const Sample *a,const Sample *b){
    printf("m%4u f%"PRIu64" state %u->%u ground %u->%u carry %u/%08x->%u/%08x pos=(%d,%d,%d) vel=(%d,%d,%d) anim=%u/%u\n",
      b->movie,b->frame,a->state,b->state,a->grounded,b->grounded,a->carry_mode,a->carried_off,b->carry_mode,b->carried_off,
      b->x,b->y,b->z,b->vx,b->vy,b->vz,b->anim0,b->anim1);
}

int main(int argc,char **argv){
    if(argc!=2){fprintf(stderr,"usage: %s CAPSULE_DIR\n",argv[0]);return 2;}
    char pattern[4096]; snprintf(pattern,sizeof(pattern),"%s/chunks/*.tcap.zst",argv[1]);
    glob_t g={0}; if(glob(pattern,0,NULL,&g))die("no chunks");
    uint8_t *domain[4]={0}; size_t dsize[4]={0}; uint32_t expected_mode=UINT32_MAX; uint32_t expected_names=0;
    for(size_t fi=0;fi<g.gl_pathc;fi++){
        size_t raw_n; uint8_t *raw=decompress_file(g.gl_pathv[fi],&raw_n); Reader r={raw,raw+raw_n};
        if(memcmp(take(&r,8),"DSTCAP01",8)||u32(&r)!=1)die("bad capsule header");
        uint32_t mode=u32(&r); (void)u64(&r); uint32_t names=u32(&r);
        if(expected_mode==UINT32_MAX){expected_mode=mode;expected_names=names;} else if(mode!=expected_mode||names!=expected_names)die("schema changed");
        for(uint32_t i=0;i<names;i++){uint16_t n=u16(&r);take(&r,n);}
        while(r.p<r.end){
            if(u8(&r)!=1)die("bad record tag"); uint64_t frame=u64(&r),cycle=u64(&r); uint32_t movie=u32(&r),pc=u32(&r); (void)u32(&r);
            for(uint32_t i=0;i<names;i++)(void)u32(&r);
            for(uint32_t di=0;di<3;di++){
                uint32_t id=u32(&r),size=u32(&r),runs=u32(&r); const uint8_t *hash=take(&r,32);
                if(id<1||id>3)die("bad domain"); if(!domain[id]){domain[id]=calloc(1,size);dsize[id]=size;} if(dsize[id]!=size)die("domain resized");
                for(uint32_t j=0;j<runs;j++){uint32_t off=u32(&r),len=u32(&r);if((uint64_t)off+len>size)die("delta range");memcpy(domain[id]+off,take(&r,len),len);}
                sha_check(domain[id],size,hash,frame,id);
            }
            uint64_t flow=u64(&r),block_total=0;
            for(uint64_t i=0;i<flow;i++){
                (void)u32(&r);
                if(mode==1) block_total+=u64(&r); else if(mode==2){block_total+=u32(&r);(void)u64(&r);} else die("bad mode");
            }
            if(nsamples>=MAX_FRAMES)die("too many frames"); const uint8_t *ram=domain[1]; Sample *s=&samples[nsamples++];
            *s=(Sample){.frame=frame,.cycle=cycle,.movie=movie,.pc=pc,
              .x=s32at(ram,PLAYER+0x00),.y=s32at(ram,PLAYER+0x04),.z=s32at(ram,PLAYER+0x08),
              .vx=s32at(ram,PLAYER+0x2c),.vy=s32at(ram,PLAYER+0x30),.vz=s32at(ram,PLAYER+0x34),.floor_y=s32at(ram,PLAYER+0x48),
              .anim0=u16at(ram,PLAYER+0x42),.anim1=u16at(ram,PLAYER+0x46),.timer7a=u16at(ram,PLAYER+0x7a),
              .state=u16at(ram,PLAYER+0x80),.grounded=u16at(ram,PLAYER+0x82),.f84=u16at(ram,PLAYER+0x84),.f86=u16at(ram,PLAYER+0x86),.f88=u16at(ram,PLAYER+0x88),
              .carried_off=u32at(ram,PLAYER+0x5c),.carry_mode=ram[PLAYER+0xa3],.blocks=block_total};
        }
        free(raw);
    }
    globfree(&g);
    printf("frames=%zu mode=%u names=%u first=m%u/f%"PRIu64" last=m%u/f%"PRIu64"\n",nsamples,expected_mode,expected_names,samples[0].movie,samples[0].frame,samples[nsamples-1].movie,samples[nsamples-1].frame);
    puts("-- state/contact/carry transitions --");
    for(size_t i=1;i<nsamples;i++) if(samples[i].state!=samples[i-1].state||samples[i].grounded!=samples[i-1].grounded||samples[i].carry_mode!=samples[i-1].carry_mode||samples[i].carried_off!=samples[i-1].carried_off) print_transition(&samples[i-1],&samples[i]);
    puts("-- exact-position spans >= 8 boundaries --");
    for(size_t i=0;i<nsamples;){size_t j=i+1;while(j<nsamples&&same_pos(&samples[i],&samples[j]))j++;if(j-i>=8)printf("m%u..%u n=%zu state=%u..%u grounded=%u carry=%u/%08x pos=(%d,%d,%d) anim=%u/%u->%u/%u\n",samples[i].movie,samples[j-1].movie,j-i,samples[i].state,samples[j-1].state,samples[i].grounded,samples[i].carry_mode,samples[i].carried_off,samples[i].x,samples[i].y,samples[i].z,samples[i].anim0,samples[i].anim1,samples[j-1].anim0,samples[j-1].anim1);i=j;}
    puts("-- state 6 spans --");
    for(size_t i=0;i<nsamples;){if(samples[i].state!=6){i++;continue;}size_t j=i+1;while(j<nsamples&&samples[j].state==6)j++;printf("m%u..%u n=%zu pos (%d,%d,%d)->(%d,%d,%d) grounded %u->%u vy %d->%d\n",samples[i].movie,samples[j-1].movie,j-i,samples[i].x,samples[i].y,samples[i].z,samples[j-1].x,samples[j-1].y,samples[j-1].z,samples[i].grounded,samples[j-1].grounded,samples[i].vy,samples[j-1].vy);i=j;}
    for(int id=1;id<=3;id++)free(domain[id]);
    return 0;
}
