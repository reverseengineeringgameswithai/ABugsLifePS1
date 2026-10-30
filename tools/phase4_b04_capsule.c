#define _POSIX_C_SOURCE 200809L
#include <dirent.h>
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

typedef struct { const uint8_t *p,*end; } Reader;
static void need(Reader *r,size_t n){if((size_t)(r->end-r->p)<n){fprintf(stderr,"truncated chunk\n");exit(3);}}
static uint8_t r8(Reader *r){need(r,1);return *r->p++;}
static uint16_t r16(Reader *r){need(r,2);uint16_t v=r->p[0]|(r->p[1]<<8);r->p+=2;return v;}
static uint32_t r32(Reader *r){need(r,4);uint32_t v=r->p[0]|((uint32_t)r->p[1]<<8)|((uint32_t)r->p[2]<<16)|((uint32_t)r->p[3]<<24);r->p+=4;return v;}
static uint64_t r64(Reader *r){uint64_t lo=r32(r),hi=r32(r);return lo|(hi<<32);}
static const uint8_t *take(Reader *r,size_t n){need(r,n);const uint8_t *p=r->p;r->p+=n;return p;}
static uint8_t *slurp(const char *path,size_t *n){FILE*f=fopen(path,"rb");if(!f){perror(path);exit(2);}if(fseek(f,0,SEEK_END)||ftell(f)<0){exit(2);}long z=ftell(f);rewind(f);uint8_t*p=malloc((size_t)z);if(!p||fread(p,1,(size_t)z,f)!=(size_t)z){fprintf(stderr,"read %s\n",path);exit(2);}fclose(f);*n=(size_t)z;return p;}
static void hex(const uint8_t h[32],char out[65]){for(int i=0;i<32;i++)sprintf(out+i*2,"%02x",h[i]);out[64]=0;}
static void digest(const uint8_t*p,size_t n,uint8_t h[32]){SHA256(p,n,h);}
static const char *base(const char*p){const char*q=strrchr(p,'/');return q?q+1:p;}
static const struct {const char*name,*sha;} expected[]={
{"000000-f164199-f164258.tcap.zst","5cebfb71d562696bbe07cea9d5c91891e3e11f4062a6db73e614b81c06afaf47"},
{"000001-f164259-f164318.tcap.zst","5fcd91093391e7a0c3ab91962c5348d8d7f5a377af23f62c568a7f18e9f5183b"},
{"000002-f164319-f164378.tcap.zst","51b0feffbe00eaf27852cec9028c83b9ba0d2e03bd3e498b64ccaf1f47ccb024"},
{"000003-f164379-f164438.tcap.zst","aaaf3e177fae77ac7ddac2d9355978344a9a56a53005238f16aeb6421c75e5ca"},
{"000004-f164439-f164498.tcap.zst","4d53b7d84558db0afc3ff73d6d04c56be1bdb8857911ceff3ba9c5a3bd7327b2"},
{"000005-f164499-f164558.tcap.zst","dee0e3cd534bde7b81a362ba8a33d72e217bd08d947f7a96c8f407b3521b2659"},
{"000006-f164559-f164618.tcap.zst","409d79453111699b6118dc5ed849e1ef99db5204852d908561e92acf6b4fafd0"},
{"000007-f164619-f164678.tcap.zst","a31637b72ffc070397584e85100f06822df5eae04e12416f4128cdb28447ef69"},
{"000008-f164679-f164686.tcap.zst","aa2f0a2427e548ac99568311012ec6517f0ae54c2f3bfa488cc958ba01814a95"}};
static const char*expect(const char*n){for(size_t i=0;i<sizeof(expected)/sizeof(*expected);i++)if(!strcmp(n,expected[i].name))return expected[i].sha;return NULL;}
typedef struct {uint8_t*p;uint32_t n;} Domain;
static uint32_t ru32(const Domain*d,uint32_t a){uint32_t o=a&0x1fffff;if(o+4>d->n)return 0;return d->p[o]|((uint32_t)d->p[o+1]<<8)|((uint32_t)d->p[o+2]<<16)|((uint32_t)d->p[o+3]<<24);}
static uint16_t ru16(const Domain*d,uint32_t a){uint32_t o=a&0x1fffff;if(o+2>d->n)return 0;return d->p[o]|((uint16_t)d->p[o+1]<<8);}
static uint8_t ru8(const Domain*d,uint32_t a){uint32_t o=a&0x1fffff;return o<d->n?d->p[o]:0;}
static int32_t rs32(const Domain*d,uint32_t a){return (int32_t)ru32(d,a);}
typedef struct {uint64_t frame,cycle;uint32_t movie,pc;int32_t x,y,z,vx,vy,vz,floor;uint32_t carry;uint16_t latch657a,action,mode,ground,timer,flags,interact;uint8_t byte65a3;int cannon_slot,cannon_state;uint16_t cannon_extra;int32_t cannon_x,cannon_y,cannon_z;uint64_t handler_blocks,launch_case_blocks;} Snap;
static Snap snap(const Domain*d,uint64_t f,uint64_t c,uint32_t m,uint32_t pc,uint64_t hb,uint64_t lb){Snap s={0};s.frame=f;s.cycle=c;s.movie=m;s.pc=pc;s.x=rs32(d,0x800a6500);s.y=rs32(d,0x800a6504);s.z=rs32(d,0x800a6508);s.vx=rs32(d,0x800a652c);s.vy=rs32(d,0x800a6530);s.vz=rs32(d,0x800a6534);s.floor=rs32(d,0x800a6548);s.carry=ru32(d,0x800a655c);s.latch657a=ru16(d,0x800a657a);s.action=ru16(d,0x800a657c);s.mode=ru16(d,0x800a6580);s.ground=ru16(d,0x800a6582);s.timer=ru16(d,0x800a6584);s.flags=ru16(d,0x800a6590);s.interact=ru16(d,0x800a659e);s.byte65a3=ru8(d,0x800a65a3);s.cannon_slot=-1;for(int i=0;i<20;i++){uint32_t a=0x80090bf0u+(uint32_t)i*0x30u;if(ru16(d,a)==2){s.cannon_slot=i;s.cannon_state=ru16(d,a+2);s.cannon_x=rs32(d,a+8);s.cannon_y=rs32(d,a+12);s.cannon_z=rs32(d,a+16);s.cannon_extra=ru16(d,a+46);break;}}s.handler_blocks=hb;s.launch_case_blocks=lb;return s;}
static int changed(const Snap*a,const Snap*b){return a->action!=b->action||a->mode!=b->mode||a->ground!=b->ground||a->timer!=b->timer||a->flags!=b->flags||a->interact!=b->interact||a->carry!=b->carry||a->latch657a!=b->latch657a||a->byte65a3!=b->byte65a3||a->vy!=b->vy||a->vx!=b->vx||a->vz!=b->vz||a->cannon_state!=b->cannon_state||a->cannon_extra!=b->cannon_extra||a->handler_blocks;}
int main(int ac,char**av){if(ac!=2){fprintf(stderr,"usage: %s capsule_dir\n",av[0]);return 2;}char pat[4096];snprintf(pat,sizeof pat,"%s/chunks/*.tcap.zst",av[1]);glob_t g={0};if(glob(pat,0,NULL,&g)||g.gl_pathc!=9){fprintf(stderr,"expected 9 chunks, got %zu\n",g.gl_pathc);return 2;}Domain dom[4]={{0}};char **regnames=NULL;uint32_t nregs=0,mode0=0;uint64_t frames=0,total_handler=0,total_launch_case=0;int hash_ok=1,have_prev=0,launch_movie=-1,action17_movie=-1,handler_movie=-1,apex_movie=-1;int32_t launch_y=0,apex_y=0;Snap prev={0};printf("movie,frame,x,y,z,vx,vy,vz,action,mode,ground,timer,flags,interact,carry,latch657a,byte65a3,cannon_slot,cannon_state,cannon_extra,handler_blocks,launch_case_blocks\n");
for(size_t fi=0;fi<g.gl_pathc;fi++){size_t cn;uint8_t*c=slurp(g.gl_pathv[fi],&cn),fh[32];digest(c,cn,fh);char hs[65];hex(fh,hs);const char*ex=expect(base(g.gl_pathv[fi]));if(!ex||strcmp(hs,ex)){fprintf(stderr,"file hash mismatch %s\n",base(g.gl_pathv[fi]));return 4;}unsigned long long raw_n=ZSTD_getFrameContentSize(c,cn);if(raw_n==ZSTD_CONTENTSIZE_ERROR||raw_n==ZSTD_CONTENTSIZE_UNKNOWN){return 4;}uint8_t*raw=malloc((size_t)raw_n);size_t got=ZSTD_decompress(raw,(size_t)raw_n,c,cn);free(c);if(ZSTD_isError(got)||got!=raw_n){fprintf(stderr,"decompress failure\n");return 4;}Reader r={raw,raw+got};if(memcmp(take(&r,8),"DSTCAP01",8)||r32(&r)!=1){fprintf(stderr,"schema failure\n");return 4;}uint32_t mode=r32(&r);(void)r64(&r);uint32_t nr=r32(&r);if(!regnames){mode0=mode;nregs=nr;regnames=calloc(nr,sizeof(*regnames));for(uint32_t i=0;i<nr;i++){uint16_t z=r16(&r);regnames[i]=malloc(z+1);memcpy(regnames[i],take(&r,z),z);regnames[i][z]=0;}}else{if(mode!=mode0||nr!=nregs){fprintf(stderr,"schema drift\n");return 4;}for(uint32_t i=0;i<nr;i++){uint16_t z=r16(&r);const uint8_t*p=take(&r,z);if(strlen(regnames[i])!=z||memcmp(regnames[i],p,z)){fprintf(stderr,"register drift\n");return 4;}}}
while(r.p<r.end){if(r8(&r)!=1){fprintf(stderr,"bad tag\n");return 4;}uint64_t frame=r64(&r),cycle=r64(&r);uint32_t movie=r32(&r),pc=r32(&r);(void)r32(&r);for(uint32_t i=0;i<nregs;i++)(void)r32(&r);for(int di=0;di<3;di++){uint32_t id=r32(&r),size=r32(&r),runs=r32(&r);const uint8_t*want=take(&r,32);if(id<1||id>3){fprintf(stderr,"bad domain\n");return 4;}if(!dom[id].p){dom[id].p=calloc(1,size);dom[id].n=size;}if(dom[id].n!=size){fprintf(stderr,"domain size drift\n");return 4;}for(uint32_t j=0;j<runs;j++){uint32_t off=r32(&r),len=r32(&r);if((uint64_t)off+len>size){fprintf(stderr,"delta range\n");return 4;}memcpy(dom[id].p+off,take(&r,len),len);}uint8_t got_h[32];digest(dom[id].p,size,got_h);if(memcmp(want,got_h,32)){char a[65],b[65];hex(want,a);hex(got_h,b);fprintf(stderr,"domain hash mismatch frame=%"PRIu64" id=%u want=%s got=%s\n",frame,id,a,b);hash_ok=0;return 5;}}
uint64_t bc=r64(&r),hb=0,lb=0;for(uint64_t j=0;j<bc;j++){uint32_t p=r32(&r);uint64_t count=r64(&r);if(p>=0x8005c110&&p<=0x8005c254)hb+=count;if(p>=0x80048670&&p<=0x80048720)lb+=count;}total_handler+=hb;total_launch_case+=lb;Snap s=snap(&dom[1],frame,cycle,movie,pc,hb,lb);if(handler_movie<0&&hb)handler_movie=(int)movie;if(action17_movie<0&&s.action==17)action17_movie=(int)movie;if(launch_movie<0&&s.mode==6&&s.vy<=-7936){launch_movie=(int)movie;launch_y=prev.y;apex_y=s.y;}if(launch_movie>=0&&apex_movie<0){if(s.y<apex_y)apex_y=s.y;if(have_prev&&prev.vy<0&&s.vy>=0)apex_movie=(int)movie;}if(!have_prev||changed(&s,&prev)||((int)movie>=launch_movie-2&&(int)movie<=launch_movie+8))printf("%u,%"PRIu64",%d,%d,%d,%d,%d,%d,%u,%u,%u,%u,0x%04x,%u,0x%08x,%u,%u,%d,%d,0x%04x,%"PRIu64",%"PRIu64"\n",s.movie,s.frame,s.x,s.y,s.z,s.vx,s.vy,s.vz,s.action,s.mode,s.ground,s.timer,s.flags,s.interact,s.carry,s.latch657a,s.byte65a3,s.cannon_slot,s.cannon_state,s.cannon_extra,s.handler_blocks,s.launch_case_blocks);prev=s;have_prev=1;frames++;}
free(raw);}
printf("SUMMARY frames=%"PRIu64" chunks=%zu domain_hashes_ok=%s handler_first_movie=%d handler_blocks=%"PRIu64" player_case_first_action17=%d launch_movie=%d launch_y=%d launch_vector=(0,-8192,0) apex_movie=%d apex_y=%d rise=%d launch_case_blocks=%"PRIu64"\n",frames,g.gl_pathc,hash_ok?"true":"false",handler_movie,total_handler,action17_movie,launch_movie,launch_y,apex_movie,apex_y,launch_y-apex_y,total_launch_case);globfree(&g);return 0;}
