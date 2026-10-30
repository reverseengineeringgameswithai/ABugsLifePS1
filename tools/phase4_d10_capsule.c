#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

enum { RAM_SIZE = 0x200000, MAX_TRANSITIONS = 128 };

typedef struct { const uint8_t *p; size_t n, o; } Buf;
typedef struct { uint64_t emu_frame; uint32_t movie_frame; uint32_t before, after; } Change;
typedef struct {
    const char *name; uint32_t offset; unsigned width; uint32_t initial, current;
    Change changes[MAX_TRANSITIONS]; unsigned change_count;
} Watch;
typedef struct { uint32_t pc; uint64_t blocks, instructions; } Flow;

static void die(const char *msg) { fprintf(stderr, "d10_capsule_asm: %s\n", msg); exit(2); }
static void *xmalloc(size_t n) { void *p = malloc(n ? n : 1); if (!p) die("out of memory"); return p; }
static const uint8_t *take(Buf *b, size_t n) { if (n > b->n - b->o) die("truncated capsule record"); const uint8_t *p=b->p+b->o; b->o+=n; return p; }
static uint8_t get8(Buf *b) { return *take(b,1); }
static uint16_t get16(Buf *b) { const uint8_t*p=take(b,2); return (uint16_t)(p[0]|p[1]<<8); }
static uint32_t get32(Buf *b) { const uint8_t*p=take(b,4); return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static uint64_t get64(Buf *b) { uint64_t lo=get32(b),hi=get32(b); return lo|(hi<<32); }
static uint32_t load_value(const uint8_t *ram, const Watch *w) {
    if (w->width == 1) return ram[w->offset];
    if (w->width == 2) return (uint32_t)(ram[w->offset] | ram[w->offset+1] << 8);
    return (uint32_t)ram[w->offset] | (uint32_t)ram[w->offset+1] << 8 |
           (uint32_t)ram[w->offset+2] << 16 | (uint32_t)ram[w->offset+3] << 24;
}
static uint8_t *read_file(const char *path, size_t *size) {
    FILE *f=fopen(path,"rb"); long n; uint8_t *p;
    if(!f){fprintf(stderr,"%s: %s\n",path,strerror(errno));exit(2);}
    if(fseek(f,0,SEEK_END)||(n=ftell(f))<0||fseek(f,0,SEEK_SET))die("file seek failed");
    p=xmalloc((size_t)n+1); if(fread(p,1,(size_t)n,f)!=(size_t)n)die("file read failed");
    fclose(f); p[n]=0; *size=(size_t)n; return p;
}
static uint8_t *decompress(const char *path,size_t *size) {
    size_t in_n; uint8_t *in=read_file(path,&in_n); unsigned long long out_n=ZSTD_getFrameContentSize(in,in_n);
    if(out_n==ZSTD_CONTENTSIZE_ERROR||out_n==ZSTD_CONTENTSIZE_UNKNOWN||out_n>SIZE_MAX)die("invalid zstd frame");
    uint8_t*out=xmalloc((size_t)out_n);size_t got=ZSTD_decompress(out,(size_t)out_n,in,in_n);free(in);
    if(ZSTD_isError(got)||got!=(size_t)out_n)
        die("zstd decompression failed");
    *size=got;
    return out;
}
static int sha_ok(const uint8_t *p,size_t n,const uint8_t expected[32]) {
    uint8_t got[32];size_t got_n=0;
    if(!EVP_Q_digest(NULL,"SHA256",NULL,p,n,got,&got_n)||got_n!=32)die("SHA256 failed");
    return memcmp(got,expected,32)==0;
}
static void lowercase(char *dst,const char *src,size_t cap) { size_t i=0;for(;src[i]&&i+1<cap;i++)dst[i]=(char)tolower((unsigned char)src[i]);dst[i]=0; }
static int asm_interesting(const char *line) {
    char low[4096];lowercase(low,line,sizeof(low));
    return strstr(low,"3b3")||strstr(low,"8004b3")||strstr(low,"8008223c")||
           strstr(low,"800823a0")||strstr(low,"80082444")||strstr(low,"80082470")||
           strstr(low,"80082504")||strstr(low,"8009b889")||strstr(low,"bonus");
}
static void inspect_asm(const char *path) {
    size_t n;uint8_t*raw=read_file(path,&n);char *save=NULL,*s;char **lines=NULL;size_t count=0,cap=0;
    s=strtok_r((char*)raw,"\n",&save);while(s){if(count==cap){cap=cap?cap*2:512;lines=realloc(lines,cap*sizeof(*lines));if(!lines)die("line allocation");}lines[count++]=s;s=strtok_r(NULL,"\n",&save);}
    printf("=== ASM_EVIDENCE %s ===\n",path);int printed_gap=1;
    for(size_t i=0;i<count;i++)if(asm_interesting(lines[i])){
        size_t lo=i>2?i-2:0,hi=i+2<count?i+2:count-1;
        if(!printed_gap)puts("...");
        for(size_t j=lo;j<=hi;j++)printf("%6zu %s\n",j+1,lines[j]);
        i=hi;printed_gap=0;
    }
    free(lines);free(raw);
}
static void update_watches(Watch *w,size_t count,const uint8_t *ram,uint64_t emu,uint32_t movie,int first) {
    for(size_t i=0;i<count;i++){
        uint32_t now=load_value(ram,&w[i]);
        if(first){w[i].initial=w[i].current=now;continue;}
        if(now!=w[i].current){if(w[i].change_count<MAX_TRANSITIONS)w[i].changes[w[i].change_count++]=(Change){emu,movie,w[i].current,now};w[i].current=now;}
    }
}
static void analyze_capsule(const char *dir) {
    Watch watches[]={
        {"stomp_streak",0x8223c,4,0,0,{{0}},0}, {"transition_latch",0x823a0,2,0,0,{{0}},0},
        {"progress_command",0x82444,4,0,0,{{0}},0}, {"fade_timer",0x82470,2,0,0,{{0}},0},
        {"current_scene",0x82504,4,0,0,{{0}},0}, {"bonus_flags",0x9b889,1,0,0,{{0}},0}
    };
    Flow flow[30];for(unsigned i=0;i<30;i++)flow[i]=(Flow){0x8004b35c+i*4,0,0};
    char pattern[4096];if(snprintf(pattern,sizeof(pattern),"%s/chunks/*.zst",dir)>=(int)sizeof(pattern))die("capsule path too long");
    glob_t g={0};if(glob(pattern,0,NULL,&g)||!g.gl_pathc)die("no capsule chunks");
    uint8_t*domains[4]={0};uint32_t sizes[4]={0};uint64_t records=0,hash_checks=0,hash_mismatches=0,flow_items=0,flow_instructions=0;uint32_t first_movie=0,last_movie=0;uint64_t first_emu=0,last_emu=0;
    for(size_t fi=0;fi<g.gl_pathc;fi++){
        size_t n;uint8_t*raw=decompress(g.gl_pathv[fi],&n);Buf b={raw,n,0};
        if(memcmp(take(&b,8),"DSTCAP01",8))
            die("bad capsule magic");
        uint32_t version=get32(&b);
        if(version<1||version>2)
            die("unsupported capsule version");
        (void)get32(&b);(void)get64(&b);uint32_t nregs=get32(&b);for(uint32_t i=0;i<nregs;i++){uint16_t z=get16(&b);(void)take(&b,z);}
        while(b.o<b.n){
            if(get8(&b)!=1)
                die("bad record tag");
            uint64_t emu=get64(&b);(void)get64(&b);uint32_t movie=get32(&b);(void)get32(&b);(void)get32(&b);(void)take(&b,(size_t)nregs*4);
            for(unsigned k=0;k<3;k++){
                uint32_t id=get32(&b),sz=get32(&b),patches=get32(&b);const uint8_t*expected=take(&b,32);if(id<1||id>3)die("bad domain id");
                if(!domains[id]){domains[id]=calloc(1,sz);sizes[id]=sz;if(!domains[id])die("domain allocation");}else if(sizes[id]!=sz)die("domain size changed");
                for(uint32_t p=0;p<patches;p++){uint32_t off=get32(&b),len=get32(&b);if(off>sz||len>sz-off)die("bad domain patch");memcpy(domains[id]+off,take(&b,len),len);}
                hash_checks++;if(!sha_ok(domains[id],sz,expected))hash_mismatches++;
            }
            uint8_t*ram=NULL;for(unsigned id=1;id<=3;id++)if(sizes[id]==RAM_SIZE)ram=domains[id];if(!ram)die("RAM domain absent");
            int first=records==0;if(first){first_movie=movie;first_emu=emu;}update_watches(watches,sizeof(watches)/sizeof(watches[0]),ram,emu,movie,first);
            uint64_t nf=get64(&b);flow_items+=nf;for(uint64_t q=0;q<nf;q++){
                uint32_t pc=get32(&b),count;if(version==2){count=get32(&b);(void)get64(&b);}else{uint64_t z=get64(&b);count=z>UINT32_MAX?UINT32_MAX:(uint32_t)z;}
                flow_instructions+=count;if(pc>=0x8004b35c&&pc<=0x8004b3d0&&((pc-0x8004b35c)&3)==0){Flow*f=&flow[(pc-0x8004b35c)/4];f->blocks++;f->instructions+=count;}
            }
            records++;last_movie=movie;last_emu=emu;
        }free(raw);
    }
    printf("=== CAPSULE_QUERY ===\nrecords=%"PRIu64" movie=%u..%u emulator=%"PRIu64"..%"PRIu64" hash_checks=%"PRIu64" hash_mismatches=%"PRIu64" flow_items=%"PRIu64" flow_instructions=%"PRIu64"\n",records,first_movie,last_movie,first_emu,last_emu,hash_checks,hash_mismatches,flow_items,flow_instructions);
    for(size_t i=0;i<sizeof(watches)/sizeof(watches[0]);i++){
        printf("WATCH %s initial=0x%x final=0x%x changes=%u\n",watches[i].name,watches[i].initial,watches[i].current,watches[i].change_count);
        for(unsigned j=0;j<watches[i].change_count;j++){Change*c=&watches[i].changes[j];printf("  emu=%"PRIu64" movie=%u 0x%x->0x%x\n",c->emu_frame,c->movie_frame,c->before,c->after);}
    }
    puts("FLOW 0x8004B35C..0x8004B3D0");for(unsigned i=0;i<30;i++)if(flow[i].blocks)printf("  pc=0x%08x frames=%"PRIu64" instructions=%"PRIu64"\n",flow[i].pc,flow[i].blocks,flow[i].instructions);
    for(unsigned i=1;i<=3;i++)
        free(domains[i]);
    globfree(&g);
}
int main(int argc,char**argv){if(argc!=3){fprintf(stderr,"usage: %s ASM CAPSULE_DIR\n",argv[0]);return 2;}inspect_asm(argv[1]);analyze_capsule(argv[2]);return 0;}
