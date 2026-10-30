#define _POSIX_C_SOURCE 200809L
#include <glob.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

#define BASE 0x80010000u
#define END  0x80063000u
#define WORDS ((END-BASE)/4)
typedef struct { const uint8_t *p,*e; } R;
static const uint32_t wanted[]={1038,1040,1042,1044,1046,1212,1214,1216,1218,1220,1222,1224};
static uint64_t counts[sizeof(wanted)/sizeof(wanted[0])][WORDS];
static void bad(const char*s){fprintf(stderr,"%s\n",s);exit(1);}static const uint8_t*take(R*r,size_t n){const uint8_t*p=r->p;if(p+n>r->e)bad("truncated");r->p+=n;return p;}static uint8_t u8(R*r){return*take(r,1);}static uint16_t u16(R*r){uint16_t v;memcpy(&v,take(r,2),2);return v;}static uint32_t u32(R*r){uint32_t v;memcpy(&v,take(r,4),4);return v;}static uint64_t u64(R*r){uint64_t v;memcpy(&v,take(r,8),8);return v;}
static uint8_t *inflate(const char*p,size_t*n){FILE*f=fopen(p,"rb");if(!f)bad("open");fseek(f,0,SEEK_END);long z=ftell(f);rewind(f);uint8_t*s=malloc(z);fread(s,1,z,f);fclose(f);unsigned long long q=ZSTD_getFrameContentSize(s,z);if(q==ZSTD_CONTENTSIZE_ERROR||q==ZSTD_CONTENTSIZE_UNKNOWN)bad("zstd size");uint8_t*d=malloc(q);size_t got=ZSTD_decompress(d,q,s,z);free(s);if(ZSTD_isError(got)||got!=q)bad("zstd");*n=got;return d;}
static int slot(uint32_t m){for(size_t i=0;i<sizeof(wanted)/sizeof(wanted[0]);i++)if(wanted[i]==m)return(int)i;return-1;}
static void unique_against(int event,const int *controls,size_t nc,const char *name){printf("-- %s m%u unique resident block PCs --\n",name,wanted[event]);uint32_t start=0,last=0;uint64_t sum=0;int open=0;for(uint32_t i=0;i<WORDS;i++){if(!counts[event][i])continue;int seen=0;for(size_t c=0;c<nc;c++)if(counts[controls[c]][i])seen=1;if(seen)continue;uint32_t pc=BASE+i*4;if(open&&pc==last+4){last=pc;sum+=counts[event][i];}else{if(open)printf("0x%08x..0x%08x count=%"PRIu64"\n",start,last,sum);start=last=pc;sum=counts[event][i];open=1;}}if(open)printf("0x%08x..0x%08x count=%"PRIu64"\n",start,last,sum);}
static void selected_range(int s,uint32_t lo,uint32_t hi,const char*name){printf("-- %s m%u 0x%08x..0x%08x --\n",name,wanted[s],lo,hi);for(uint32_t pc=lo;pc<=hi;pc+=4){uint64_t n=counts[s][(pc-BASE)/4];if(n)printf("0x%08x %"PRIu64"\n",pc,n);}}
int main(int argc,char**argv){if(argc!=2)return 2;char pat[4096];snprintf(pat,sizeof(pat),"%s/chunks/*.tcap.zst",argv[1]);glob_t g={0};if(glob(pat,0,NULL,&g))bad("chunks");for(size_t f=0;f<g.gl_pathc;f++){size_t n;uint8_t*b=inflate(g.gl_pathv[f],&n);R r={b,b+n};if(memcmp(take(&r,8),"DSTCAP01",8)||u32(&r)!=1)bad("header");uint32_t mode=u32(&r);(void)u64(&r);uint32_t names=u32(&r);for(uint32_t i=0;i<names;i++)take(&r,u16(&r));while(r.p<r.e){if(u8(&r)!=1)bad("tag");(void)u64(&r);(void)u64(&r);uint32_t movie=u32(&r);(void)u32(&r);(void)u32(&r);for(uint32_t i=0;i<names;i++)(void)u32(&r);for(int d=0;d<3;d++){(void)u32(&r);(void)u32(&r);uint32_t runs=u32(&r);take(&r,32);for(uint32_t j=0;j<runs;j++){(void)u32(&r);take(&r,u32(&r));}}uint64_t flows=u64(&r);int s=slot(movie);for(uint64_t j=0;j<flows;j++){uint32_t pc=u32(&r);uint64_t c;if(mode==1)c=u64(&r);else{c=u32(&r);(void)u64(&r);}if(s>=0&&pc>=BASE&&pc<END)counts[s][(pc-BASE)/4]+=c;}}free(b);}globfree(&g);int mc[]={0,1,3,4};unique_against(2,mc,4,"mount");int rc[]={5,6,8,9};unique_against(7,rc,4,"release-to-state5");int sc[]={8,9,11};unique_against(10,sc,3,"state6-entry");selected_range(2,0x80047000,0x800498a8,"mount player path");selected_range(7,0x80047000,0x800498a8,"release player path");selected_range(10,0x80047000,0x800498a8,"state6 player path");selected_range(2,0x8005cd2c,0x8005d654,"mount seed path");selected_range(7,0x8005cd2c,0x8005d654,"release seed path");return 0;}
