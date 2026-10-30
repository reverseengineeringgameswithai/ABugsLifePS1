#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <zstd.h>

enum { RAM_SIZE = 0x200000, MAX_CAND = 4096, MAX_TRANS = 128 };

typedef struct { const uint8_t *p; size_t n, o; } Buf;
typedef struct { uint64_t emu; uint32_t movie; int32_t before, after; } Transition;
typedef struct {
  uint32_t off;
  int32_t id, threshold, x, z, initial, prev;
  unsigned ntrans;
  int qualifies;
  Transition trans[MAX_TRANS];
} Candidate;
typedef struct { uint32_t pc; uint64_t blocks, insns; } Hot;
typedef struct {int32_t initial,prev,min,max,first_arm,last_arm;uint32_t first_arm_movie,last_arm_movie,last_dec_movie;uint64_t changes,decrements,arms,cadence[9],cadence_other;int have_dec;} Cooldown;

static void fail(const char *msg) { fprintf(stderr, "e09_capsule_analyzer: %s\n", msg); exit(2); }
static void *xmalloc(size_t n) { void *p = malloc(n ? n : 1); if (!p) fail("out of memory"); return p; }
static const uint8_t *take(Buf *b, size_t n) {
  if (n > b->n - b->o) fail("truncated capsule record");
  const uint8_t *p = b->p + b->o; b->o += n; return p;
}
static uint8_t u8(Buf *b) { return *take(b, 1); }
static uint16_t u16(Buf *b) { const uint8_t *p=take(b,2); return (uint16_t)(p[0]|p[1]<<8); }
static uint32_t u32(Buf *b) { const uint8_t *p=take(b,4); return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static uint64_t u64(Buf *b) { uint64_t lo=u32(b), hi=u32(b); return lo | hi<<32; }
static uint32_t ld32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }

static uint8_t *read_file(const char *path, size_t *size) {
  FILE *f=fopen(path,"rb"); if(!f){perror(path);exit(2);} if(fseek(f,0,SEEK_END))fail("fseek");
  long z=ftell(f); if(z<0)fail("ftell"); rewind(f); uint8_t *p=xmalloc((size_t)z);
  if(fread(p,1,(size_t)z,f)!=(size_t)z)fail("fread"); fclose(f); *size=(size_t)z; return p;
}
static uint8_t *decompress_file(const char *path, size_t *size) {
  size_t in_n; uint8_t *in=read_file(path,&in_n); unsigned long long z=ZSTD_getFrameContentSize(in,in_n);
  if(z==ZSTD_CONTENTSIZE_ERROR || z==ZSTD_CONTENTSIZE_UNKNOWN || z>SIZE_MAX) fail("invalid zstd frame size");
  uint8_t *out=xmalloc((size_t)z); size_t got=ZSTD_decompress(out,(size_t)z,in,in_n); free(in);
  if(ZSTD_isError(got)||got!=(size_t)z) fail("zstd decompression failed"); *size=got; return out;
}
static int sha_ok(const uint8_t *p,size_t n,const uint8_t expected[32]) {
  uint8_t got[EVP_MAX_MD_SIZE]; size_t got_n=0;
  if(!EVP_Q_digest(NULL,"SHA256",NULL,p,n,got,&got_n)||got_n!=32) fail("SHA256 failed");
  return !memcmp(got,expected,32);
}
static void sha_hex(const uint8_t *p,size_t n,char out[65]) {
  uint8_t got[32]; size_t got_n=0; static const char h[]="0123456789abcdef";
  if(!EVP_Q_digest(NULL,"SHA256",NULL,p,n,got,&got_n)||got_n!=32) fail("SHA256 failed");
  for(size_t i=0;i<32;i++){out[i*2]=h[got[i]>>4];out[i*2+1]=h[got[i]&15];} out[64]=0;
}
static const char *base(const char *p) { const char *s=strrchr(p,'/'); return s?s+1:p; }
static int hot_cmp(const void *aa,const void *bb){const Hot*a=aa,*b=bb;return a->blocks<b->blocks?1:a->blocks>b->blocks?-1:0;}

static void discover_candidates(const uint8_t *ram,Candidate c[MAX_CAND],unsigned *nc) {
  for(uint32_t o=0;o+20<=RAM_SIZE;o+=4){
    if((int32_t)ld32(ram+o)!=4295)continue;
    int32_t id=(int32_t)ld32(ram+o+4), th=(int32_t)ld32(ram+o+8), x=(int32_t)ld32(ram+o+12), z=(int32_t)ld32(ram+o+16);
    if(id<0||id>4096||th<1||th>99||x<-4000000||x>4000000||z<-4000000||z>4000000)continue;
    if(*nc==MAX_CAND)fail("too many gate candidates");
    c[*nc]=(Candidate){.off=o,.id=id,.threshold=th,.x=x,.z=z,.initial=4295,.prev=4295}; (*nc)++;
  }
}
static void update_candidates(const uint8_t *ram,uint64_t emu,uint32_t movie,Candidate*c,unsigned nc) {
  for(unsigned i=0;i<nc;i++){
    int32_t now=(int32_t)ld32(ram+c[i].off); if(now==c[i].prev)continue;
    if((c[i].prev==4295&&now==4200)||(c[i].prev-now==140))c[i].qualifies=1;
    if(c[i].ntrans<MAX_TRANS)c[i].trans[c[i].ntrans++]=(Transition){emu,movie,c[i].prev,now};
    c[i].prev=now;
  }
}
static void add_transition_candidate(Candidate c[MAX_CAND],unsigned *nc,uint32_t off,const uint8_t *ram) {
  for(unsigned i=0;i<*nc;i++)if(c[i].off==off)return;
  if(off+20>RAM_SIZE||*nc==MAX_CAND)return;
  int32_t id=(int32_t)ld32(ram+off+4),th=(int32_t)ld32(ram+off+8),x=(int32_t)ld32(ram+off+12),z=(int32_t)ld32(ram+off+16);
  c[*nc]=(Candidate){.off=off,.id=id,.threshold=th,.x=x,.z=z,.initial=4295,.prev=4295,.qualifies=1};(*nc)++;
}
static void add_fixed_candidate(Candidate c[MAX_CAND],unsigned *nc,uint32_t off,int32_t id,int32_t threshold,const uint8_t *ram,int structured) {
  for(unsigned i=0;i<*nc;i++)if(c[i].off==off){c[i].qualifies=1;return;}
  if(*nc==MAX_CAND)return;int32_t x=structured?(int32_t)ld32(ram+off+12):0,z=structured?(int32_t)ld32(ram+off+16):0,st=(int32_t)ld32(ram+off);
  c[*nc]=(Candidate){.off=off,.id=id,.threshold=threshold,.x=x,.z=z,.initial=st,.prev=st,.qualifies=1};(*nc)++;
}
static void dump_ram(const char *dir,const char *id,const uint8_t *ram) {
  if(!dir||!*dir)return; char path[4096]; if(mkdir(dir,0777)&&errno!=EEXIST){perror(dir);exit(2);}
  if(snprintf(path,sizeof(path),"%s/%s.ram.bin",dir,id)>=(int)sizeof(path))fail("dump path too long");
  FILE*f=fopen(path,"wb");if(!f){perror(path);exit(2);}if(fwrite(ram,1,RAM_SIZE,f)!=RAM_SIZE)fail("RAM dump write");fclose(f);
}
static void cooldown_update(Cooldown*c,int32_t now,uint32_t movie){
 if(now==c->prev)return;c->changes++;if(now<c->min)c->min=now;if(now>c->max)c->max=now;
 if(now==c->prev-1){c->decrements++;if(c->have_dec){uint32_t d=movie-c->last_dec_movie;if(d<=8)c->cadence[d]++;else c->cadence_other++;}c->last_dec_movie=movie;c->have_dec=1;}
 if(now>=60&&now>c->prev){if(!c->arms){c->first_arm=now;c->first_arm_movie=movie;}c->last_arm=now;c->last_arm_movie=movie;c->arms++;}c->prev=now;
}
static void analyze(const char *dir,int comma) {
  char pattern[4096]; if(snprintf(pattern,sizeof(pattern),"%s/chunks/*.zst",dir)>=(int)sizeof(pattern))fail("path too long");
  glob_t g={0}; if(glob(pattern,0,NULL,&g)||!g.gl_pathc)fail("no capsule chunks");
  uint8_t *dom[4]={0}; uint32_t dsz[4]={0}; Candidate *cand=calloc(MAX_CAND,sizeof(*cand)); unsigned nc=0; int first=1;
  if(!cand)fail("candidate allocation");
  uint64_t records=0,checks=0,mismatches=0,flow_items=0,flow_insns=0,first_emu=0,last_emu=0;
  uint32_t first_movie=0,last_movie=0; uint8_t grain_min=255,grain_max=0;
  uint64_t *blocks=calloc(RAM_SIZE/4,sizeof(*blocks)),*insns=calloc(RAM_SIZE/4,sizeof(*insns)); if(!blocks||!insns)fail("flow allocation");
  char overlay_sha[65]="",gate_code_sha[65]="",ram_sha[65]=""; const char *id=base(dir);
  uint32_t cooldown_off=strstr(id,"LEVEL07")?0xb456c:0xb4d10;Cooldown cooldown={0};
  for(size_t fi=0;fi<g.gl_pathc;fi++){
    size_t n;uint8_t*raw=decompress_file(g.gl_pathv[fi],&n);Buf b={raw,n,0};
    if(memcmp(take(&b,8),"DSTCAP01",8))fail("bad capsule magic"); uint32_t ver=u32(&b);if(ver<1||ver>2)fail("unsupported capsule version");
    (void)u32(&b);(void)u64(&b);uint32_t nregs=u32(&b);for(uint32_t i=0;i<nregs;i++){uint16_t z=u16(&b);(void)take(&b,z);}
    while(b.o<b.n){
      if(u8(&b)!=1)fail("bad record tag");uint64_t emu=u64(&b);(void)u64(&b);uint32_t movie=u32(&b);(void)u32(&b);(void)u32(&b);(void)take(&b,(size_t)nregs*4);
      for(unsigned k=0;k<3;k++){
        uint32_t di=u32(&b),sz=u32(&b),np=u32(&b);const uint8_t*expected=take(&b,32);if(di<1||di>3)fail("bad domain id");
        if(!dom[di]){dom[di]=calloc(1,sz);dsz[di]=sz;if(!dom[di])fail("domain allocation");}else if(dsz[di]!=sz)fail("domain size changed");
        for(uint32_t p=0;p<np;p++){uint32_t off=u32(&b),len=u32(&b);if(off>sz||len>sz-off)fail("bad domain patch");const uint8_t*src=take(&b,len);
          if(sz==RAM_SIZE&&len>=4){uint32_t lo=(off+3)&~3u,hi=(off+len-4)&~3u;for(uint32_t w=lo;w<=hi;w+=4)if((int32_t)ld32(dom[di]+w)==4295&&(int32_t)ld32(src+w-off)==4200)add_transition_candidate(cand,&nc,w,dom[di]);}
          memcpy(dom[di]+off,src,len);
        }
        checks++;if(!sha_ok(dom[di],sz,expected))mismatches++;
      }
      uint8_t *ram=NULL;for(unsigned di=1;di<=3;di++)if(dsz[di]==RAM_SIZE)ram=dom[di];if(!ram)fail("RAM domain absent");
      if(first){first=0;first_emu=emu;first_movie=movie;discover_candidates(ram,cand,&nc);
        if(strstr(id,"LEVEL02"))for(unsigned gi=0;gi<9;gi++){uint32_t off=0xb4c1c+gi*20;add_fixed_candidate(cand,&nc,off,(int32_t)ld32(ram+off+4),(int32_t)ld32(ram+off+8),ram,1);}
        if(strstr(id,"LEVEL07"))for(unsigned gi=0;gi<3;gi++)add_fixed_candidate(cand,&nc,0xb4570+gi*4,(int32_t)gi,(int32_t)(gi+1)*10,ram,0);
        int32_t cv=(int32_t)ld32(ram+cooldown_off);cooldown=(Cooldown){.initial=cv,.prev=cv,.min=cv,.max=cv};
        sha_hex(ram,RAM_SIZE,ram_sha);sha_hex(ram+0xb0000,0x10000,overlay_sha);sha_hex(ram+0xb4300,0x500,gate_code_sha);dump_ram(getenv("E09_DUMP_DIR"),id,ram);}
      cooldown_update(&cooldown,(int32_t)ld32(ram+cooldown_off),movie);
      update_candidates(ram,emu,movie,cand,nc);uint8_t grain=ram[0xa65a1];if(grain<grain_min)grain_min=grain;if(grain>grain_max)grain_max=grain;
      uint64_t nf=u64(&b);flow_items+=nf;for(uint64_t q=0;q<nf;q++){
        uint32_t pc=u32(&b),count;if(ver==2){count=u32(&b);(void)u64(&b);}else{uint64_t z=u64(&b);count=z>UINT32_MAX?UINT32_MAX:(uint32_t)z;}
        flow_insns+=count;uint32_t phys=pc&0x1fffffff;if(phys<RAM_SIZE&&(phys&3)==0){blocks[phys/4]++;insns[phys/4]+=count;}
      }
      last_emu=emu;last_movie=movie;records++;
    } free(raw);
  }
  Hot hot[0x10000/4];unsigned nh=0;for(uint32_t o=0xb0000;o<0xc0000;o+=4)if(blocks[o/4])hot[nh++]=(Hot){0x80000000u+o,blocks[o/4],insns[o/4]};qsort(hot,nh,sizeof(*hot),hot_cmp);
  if(comma)puts(",");printf("  {\n    \"capsule_id\": \"%s\",\n",id);
  printf("    \"records\": %"PRIu64", \"emulator_first\": %"PRIu64", \"emulator_last\": %"PRIu64", \"movie_first\": %u, \"movie_last\": %u,\n",records,first_emu,last_emu,first_movie,last_movie);
  printf("    \"hash_checks\": %"PRIu64", \"hash_mismatches\": %"PRIu64", \"ram_sha256_first\": \"%s\", \"overlay_b0000_sha256_first\": \"%s\", \"gate_code_b4300_sha256_first\": \"%s\",\n",checks,mismatches,ram_sha,overlay_sha,gate_code_sha);
  printf("    \"grain_min\": %u, \"grain_max\": %u, \"flow_items\": %"PRIu64", \"flow_instructions\": %"PRIu64",\n",grain_min,grain_max,flow_items,flow_insns);
  printf("    \"denial_cooldown\": {\"address\":\"0x%08x\",\"initial\":%d,\"final\":%d,\"min\":%d,\"max\":%d,\"changes\":%"PRIu64",\"decrements\":%"PRIu64",\"arms\":%"PRIu64",\"first_arm\":%d,\"first_arm_movie\":%u,\"last_arm\":%d,\"last_arm_movie\":%u,\"decrement_cadence\":[",0x80000000u+cooldown_off,cooldown.initial,cooldown.prev,cooldown.min,cooldown.max,cooldown.changes,cooldown.decrements,cooldown.arms,cooldown.first_arm,cooldown.first_arm_movie,cooldown.last_arm,cooldown.last_arm_movie);
  int cdsep=0;for(unsigned d=0;d<=8;d++)if(cooldown.cadence[d]){if(cdsep++)printf(",");printf("{\"frames\":%u,\"count\":%"PRIu64"}",d,cooldown.cadence[d]);}if(cooldown.cadence_other){if(cdsep++)printf(",");printf("{\"frames\":\">8\",\"count\":%"PRIu64"}",cooldown.cadence_other);}printf("]},\n");
  printf("    \"gate_candidates\": [");int sep=0;for(unsigned i=0;i<nc;i++)if(cand[i].qualifies){
    if(sep++)printf(",");printf("\n      {\"address\": \"0x%08x\", \"id\": %d, \"threshold\": %d, \"x\": %d, \"z\": %d, \"initial\": %d, \"final\": %d, \"transitions\": [",0x80000000u+cand[i].off,cand[i].id,cand[i].threshold,cand[i].x,cand[i].z,cand[i].initial,cand[i].prev);
    for(unsigned j=0;j<cand[i].ntrans;j++){Transition*t=&cand[i].trans[j];if(j)printf(",");printf("{\"emu\":%"PRIu64",\"movie\":%u,\"from\":%d,\"to\":%d}",t->emu,t->movie,t->before,t->after);}printf("]}");
  } if(sep)printf("\n    ");printf("],\n    \"hot_overlay_blocks\": [");
  unsigned lim=nh<24?nh:24;for(unsigned i=0;i<lim;i++){if(i)printf(",");printf("{\"pc\":\"0x%08x\",\"blocks\":%"PRIu64",\"instructions\":%"PRIu64"}",hot[i].pc,hot[i].blocks,hot[i].insns);}printf("],\n");
  printf("    \"gate_region_flow\": [");sep=0;for(uint32_t o=0xb4300;o<0xb4800;o+=4)if(blocks[o/4]){if(sep++)printf(",");printf("{\"pc\":\"0x%08x\",\"blocks\":%"PRIu64",\"instructions\":%"PRIu64"}",0x80000000u+o,blocks[o/4],insns[o/4]);}printf("],\n");
  printf("    \"resident_29030_flow\": {\"blocks\": %"PRIu64", \"instructions\": %"PRIu64"}\n  }",blocks[0x29030/4],insns[0x29030/4]);
  for(unsigned i=1;i<=3;i++)free(dom[i]);free(cand);free(blocks);free(insns);globfree(&g);
}
int main(int argc,char**argv){if(argc<2){fprintf(stderr,"usage: %s CAPSULE...\n",argv[0]);return 2;}puts("{\n \"schema\": \"abl-phase4-e09-capsule-v1\",\n \"capsules\": [");for(int i=1;i<argc;i++)analyze(argv[i],i>1);puts("\n ]\n}");return 0;}
