
#define _POSIX_C_SOURCE 200809L
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
#define PLAYER 0x0a6500u
#define PLANTS 0x090bf0u
#define SEQUENCE 0x082248u
#define PROGRESS 0x082444u
#define TRANSITION 0x0823a0u
#define FADE_TIMER 0x082470u
#define BONUS_FLAGS 0x09b889u
#define HANDLER_START 0x8005c58cu
#define HANDLER_END 0x8005c6f0u
#define MAX_SAMPLES 2048u
#define MAX_FLOW 128u

typedef struct { const uint8_t *p,*end; const char *path; } Reader;
typedef struct {
    int16_t type;
    int32_t x,y,z;
    uint16_t extra;
} Plant;
typedef struct {
    uint64_t frame,cycle,handler_hits;
    uint32_t movie,pc;
    int32_t x,y,z,vy;
    uint16_t mode,contact,timer84,action88,transition,fade;
    uint32_t progress;
    uint8_t flags;
    int8_t seq[5];
    Plant plant[20];
} Sample;
typedef struct { uint32_t pc; uint64_t count; uint32_t frames; } Flow;

static Sample samples[MAX_SAMPLES];
static size_t ns;
static Flow flow[MAX_FLOW];
static size_t nf;
static uint8_t *dom[4];
static uint32_t dsz[4];
static uint64_t hash_checks, changed_runs;

static void die(const char *m,const char *p) {
    fprintf(stderr,"phase4_b01_capsule: %s%s%s\n",m,p?": ":"",p?p:"");
    exit(1);
}
static void need(Reader*r,size_t n) { if((size_t)(r->end-r->p)<n)die("truncated chunk",r->path); }
static uint8_t u8(Reader*r){need(r,1);return*r->p++;}
static uint16_t u16(Reader*r){need(r,2);uint16_t v=r->p[0]|((uint16_t)r->p[1]<<8);r->p+=2;return v;}
static uint32_t u32(Reader*r){need(r,4);uint32_t v=r->p[0]|((uint32_t)r->p[1]<<8)|((uint32_t)r->p[2]<<16)|((uint32_t)r->p[3]<<24);r->p+=4;return v;}
static uint64_t u64(Reader*r){uint64_t a=u32(r),b=u32(r);return a|(b<<32);}
static const uint8_t*take(Reader*r,size_t n){need(r,n);const uint8_t*p=r->p;r->p+=n;return p;}
static uint16_t rd16(const uint8_t*p){return p[0]|((uint16_t)p[1]<<8);}
static uint32_t rd32(const uint8_t*p){return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int32_t rd32s(const uint8_t*p){return(int32_t)rd32(p);}

static uint8_t*decomp(const char*path,size_t*out) {
    struct stat st;
    if(stat(path,&st)||st.st_size<=0)die("cannot stat",path);
    FILE*f=fopen(path,"rb");
    if(!f)die("cannot open",path);
    uint8_t*s=malloc((size_t)st.st_size);
    if(!s)die("oom",0);
    if(fread(s,1,(size_t)st.st_size,f)!=(size_t)st.st_size)die("cannot read",path);
    fclose(f);
    unsigned long long n=ZSTD_getFrameContentSize(s,(size_t)st.st_size);
    if(n==ZSTD_CONTENTSIZE_ERROR||n==ZSTD_CONTENTSIZE_UNKNOWN||n>SIZE_MAX)die("bad zstd size",path);
    uint8_t*d=malloc((size_t)n);
    if(!d)die("oom",0);
    size_t got=ZSTD_decompress(d,(size_t)n,s,(size_t)st.st_size);
    free(s);
    if(ZSTD_isError(got)||got!=(size_t)n)die("zstd decode",path);
    *out=got;
    return d;
}
static void add_flow(uint32_t pc,uint64_t count) {
    if(pc<HANDLER_START||pc>=HANDLER_END)return;
    for(size_t i=0;i<nf;i++)if(flow[i].pc==pc){flow[i].count+=count;flow[i].frames++;return;}
    if(nf>=MAX_FLOW)die("too many handler PCs",0);
    flow[nf++]=(Flow){pc,count,1};
}
static void capture(uint64_t frame,uint64_t cycle,uint32_t movie,uint32_t pc,uint64_t hits) {
    if(ns>=MAX_SAMPLES)die("too many samples",0);
    if(!dom[1]||dsz[1]!=RAM_SIZE)die("bad RAM domain",0);
    const uint8_t*r=dom[1];
    Sample*s=&samples[ns++];
    memset(s,0,sizeof(*s));
    s->frame=frame;s->cycle=cycle;s->movie=movie;s->pc=pc;s->handler_hits=hits;
    s->x=rd32s(r+PLAYER);s->y=rd32s(r+PLAYER+4);s->z=rd32s(r+PLAYER+8);
    s->vy=rd32s(r+PLAYER+0x30);
    s->mode=rd16(r+PLAYER+0x80);s->contact=rd16(r+PLAYER+0x82);
    s->timer84=rd16(r+PLAYER+0x84);s->action88=rd16(r+PLAYER+0x88);
    s->transition=rd16(r+TRANSITION);s->fade=rd16(r+FADE_TIMER);
    s->progress=rd32(r+PROGRESS);s->flags=r[BONUS_FLAGS];
    for(int i=0;i<5;i++)s->seq[i]=(int8_t)r[SEQUENCE+i];
    for(int i=0;i<20;i++){
        const uint8_t*p=r+PLANTS+i*0x30;
        s->plant[i].type=(int16_t)rd16(p);
        s->plant[i].x=rd32s(p+8);s->plant[i].y=rd32s(p+12);s->plant[i].z=rd32s(p+16);
        s->plant[i].extra=rd16(p+0x2e);
    }
}
static void chunk(const char*path,uint32_t*want_mode,uint32_t*want_regs) {
    size_t n;
    uint8_t*raw=decomp(path,&n);
    Reader r={raw,raw+n,path};
    if(memcmp(take(&r,8),"DSTCAP01",8))die("bad magic",path);
    if(u32(&r)!=1)die("bad version",path);
    uint32_t mode=u32(&r);
    (void)u64(&r);
    uint32_t regs=u32(&r);
    for(uint32_t i=0;i<regs;i++){uint16_t z=u16(&r);(void)take(&r,z);}
    if(*want_mode==UINT32_MAX){*want_mode=mode;*want_regs=regs;}
    else if(mode!=*want_mode||regs!=*want_regs)die("schema drift",path);
    while(r.p<r.end){
        if(u8(&r)!=1)die("bad record",path);
        uint64_t frame=u64(&r),cycle=u64(&r);
        uint32_t movie=u32(&r),pc=u32(&r);
        (void)u32(&r);
        for(uint32_t i=0;i<regs;i++)(void)u32(&r);
        for(int q=0;q<3;q++){
            uint32_t id=u32(&r),sz=u32(&r),runs=u32(&r);
            const uint8_t*expect=take(&r,32);
            if(id<1||id>3)die("bad domain",path);
            if(!dom[id]){dom[id]=calloc(1,sz);dsz[id]=sz;if(!dom[id])die("oom",0);}
            if(dsz[id]!=sz)die("domain size drift",path);
            for(uint32_t j=0;j<runs;j++){
                uint32_t off=u32(&r),len=u32(&r);
                const uint8_t*data=take(&r,len);
                if((uint64_t)off+len>sz)die("delta range",path);
                memcpy(dom[id]+off,data,len);changed_runs++;
            }
            uint8_t actual[32];
            SHA256(dom[id],sz,actual);
            if(memcmp(actual,expect,32))die("domain hash mismatch",path);
            hash_checks++;
        }
        uint64_t count=u64(&r),handler_hits=0;
        for(uint64_t i=0;i<count;i++){
            uint32_t fpc=u32(&r);
            uint64_t hits;
            if(mode==2){uint32_t ins=u32(&r);(void)u64(&r);hits=ins;}
            else if(mode==1)hits=u64(&r);
            else if(mode==0)hits=0;
            else die("bad block mode",path);
            if(fpc>=HANDLER_START&&fpc<HANDLER_END){add_flow(fpc,hits);handler_hits+=hits;}
        }
        capture(frame,cycle,movie,pc,handler_hits);
    }
    free(raw);
}
static int cmp_flow(const void*a,const void*b) {
    uint32_t x=((const Flow*)a)->pc,y=((const Flow*)b)->pc;
    return x<y?-1:x>y;
}
static int nearest_mushroom(const Sample*s) {
    int best=-1;
    uint64_t bestd=UINT64_MAX;
    for(int i=0;i<20;i++){
        const Plant*p=&s->plant[i];
        if(p->type!=5)continue;
        int64_t dx=(int64_t)s->x-p->x,dy=(int64_t)s->y-p->y,dz=(int64_t)s->z-p->z;
        uint64_t d=(uint64_t)(dx*dx+dy*dy+dz*dz);
        if(d<bestd){bestd=d;best=i;}
    }
    return best;
}
static void print_seq(const Sample*s) {
    printf("[%d,%d,%d,%d,%d]",s->seq[0],s->seq[1],s->seq[2],s->seq[3],s->seq[4]);
}
int main(int argc,char**argv) {
    if(argc!=2){fprintf(stderr,"usage: %s CAPSULE_DIR\n",argv[0]);return 2;}
    char pat[PATH_MAX];
    if(snprintf(pat,sizeof(pat),"%s/chunks/*.tcap.zst",argv[1])>=(int)sizeof(pat))die("path long",argv[1]);
    glob_t g;
    if(glob(pat,0,0,&g)||!g.gl_pathc)die("no chunks",pat);
    uint32_t mode=UINT32_MAX,regs=0;
    for(size_t i=0;i<g.gl_pathc;i++)chunk(g.gl_pathv[i],&mode,&regs);
    qsort(flow,nf,sizeof(*flow),cmp_flow);
    uint32_t handler_frames=0,normal_events=0,unlock_events=0,landings=0,sequence_changes=0;
    int32_t min_vy=INT32_MAX,max_vy=INT32_MIN;
    for(size_t i=0;i<ns;i++){
        Sample*s=&samples[i];
        if(s->handler_hits)handler_frames++;
        if(s->vy<min_vy)min_vy=s->vy;
        if(s->vy>max_vy)max_vy=s->vy;
        if(i){
            Sample*p=&samples[i-1];
            if(s->vy==-3328&&p->vy!=-3328)normal_events++;
            if(s->vy==-16384&&p->vy!=-16384)unlock_events++;
            if(p->mode==5&&s->mode!=5)landings++;
            if(memcmp(p->seq,s->seq,5))sequence_changes++;
        }
    }
    printf("{\n  \"schema\":\"phase4_b01_capsule_v1\",\n");
    printf("  \"capsule\":\"%s\",\n",argv[1]);
    printf("  \"validation\":{\"chunks\":%zu,\"records\":%zu,\"block_mode\":%u,\"register_count\":%u,\"domain_hashes_checked\":%"PRIu64",\"changed_runs\":%"PRIu64",\"parse_exact\":true},\n",
           g.gl_pathc,ns,mode,regs,hash_checks,changed_runs);
    printf("  \"summary\":{\"movie_first\":%u,\"movie_last\":%u,\"handler_frames\":%u,\"normal_minus3328_events\":%u,\"unlock_minus16384_events\":%u,\"mode5_exit_events\":%u,\"sequence_changes\":%u,\"vy_min\":%d,\"vy_max\":%d},\n",
           samples[0].movie,samples[ns-1].movie,handler_frames,normal_events,unlock_events,landings,sequence_changes,min_vy,max_vy);
    printf("  \"handler_flow\":[");
    for(size_t i=0;i<nf;i++){if(i)putchar(',');printf("{\"pc\":\"0x%08x\",\"count\":%"PRIu64",\"frames\":%u}",flow[i].pc,flow[i].count,flow[i].frames);}
    printf("],\n  \"events\":[\n");
    int first=1;
    for(size_t i=1;i<ns;i++){
        Sample*p=&samples[i-1],*s=&samples[i];
        int bounce=(s->vy==-3328&&p->vy!=-3328)||(s->vy==-16384&&p->vy!=-16384);
        int seqchg=memcmp(p->seq,s->seq,5)!=0;
        int modechg=s->mode!=p->mode;
        if(!bounce&&!seqchg&&!modechg)continue;
        if(!first)printf(",\n");
        first=0;
        int m=nearest_mushroom(s);
        printf("    {\"movie\":%u,\"emulator_frame\":%"PRIu64",\"handler_hits\":%"PRIu64",\"player\":{\"pos\":[%d,%d,%d],\"vy_before\":%d,\"vy_after\":%d,\"mode_before\":%u,\"mode_after\":%u,\"contact\":%u,\"timer84\":%u,\"action88\":%u},\"nearest_mushroom_slot\":%d,\"nearest_extra\":\"0x%04x\",\"sequence_before\":",
               s->movie,s->frame,s->handler_hits,s->x,s->y,s->z,p->vy,s->vy,p->mode,s->mode,s->contact,s->timer84,s->action88,m,m>=0?s->plant[m].extra:0);
        print_seq(p);printf(",\"sequence_after\":");print_seq(s);
        printf(",\"progress\":%u,\"transition\":%u,\"fade\":%u,\"bonus_flags\":\"0x%02x\"}",s->progress,s->transition,s->fade,s->flags);
    }
    printf("\n  ]\n}\n");
    globfree(&g);
    for(int i=1;i<=3;i++)free(dom[i]);
    return 0;
}
