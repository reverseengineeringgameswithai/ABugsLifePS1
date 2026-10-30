#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RAM_SIZE 0x200000u
#define COUNT_OFF 0x0a65a1u
#define BONUS_OFF 0x0a65a0u
#define REWARD_OFF 0x0a6594u
#define FLAGS_OFF 0x0a6590u
#define CURSOR_OFF 0x0822f4u
#define PLAYER_OFF 0x0a6500u
#define PLACEMENT_PTR_OFF 0x096e9cu
#define SCENE_OFF 0x082504u
#define GAME_STATE_OFF 0x0823a0u
#define HUD_A_OFF 0x0b0188u
#define HUD_GRAIN_OFF 0x0b018cu
#define HUD_C_OFF 0x0b0190u
#define POOL_OFF 0x0b0d18u
#define POOL_SLOTS 64u
#define POOL_STRIDE 0x38u
#define MAX_EVENTS 32u
#define MAX_RANGES 256u

typedef struct { uint8_t *data; size_t size, at; } Reader;
typedef struct { uint8_t *data; uint32_t size; } Domain;
typedef struct { uint32_t off, len; } Range;
typedef struct {
  uint64_t frame; uint32_t movie; uint8_t before, after, bonus;
  uint16_t reward, flags; uint32_t cursor; uint32_t scene; int16_t game_state;
  int16_t hud_a, hud_grain, hud_c; uint32_t pool_slots_changed;
  int32_t player_x, player_y, player_z; uint32_t placement_ptr;
  uint16_t placement_count, nearest_grain_index; uint64_t nearest_grain_distance;
  uint32_t placement_delta_overlaps;
  uint64_t hits[11]; Range ranges[MAX_RANGES]; uint32_t range_count, range_dropped;
} Event;
typedef struct { uint32_t pc; const char *name; uint64_t frames, instructions; } Target;
static const char MAGIC[8]={'D','S','T','C','A','P','0','1'};
static void die(const char *m){fprintf(stderr,"phase4_c01_capsule: %s\n",m);exit(1);}
static void diep(const char *m,const char *p){fprintf(stderr,"phase4_c01_capsule: %s: %s\n",m,p);exit(1);}
static const uint8_t *take(Reader *r,size_t n){if(n>r->size-r->at)die("truncated chunk");const uint8_t *p=r->data+r->at;r->at+=n;return p;}
static uint8_t u8(Reader *r){return take(r,1)[0];}
static uint16_t u16(Reader *r){const uint8_t *p=take(r,2);return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static uint32_t u32(Reader *r){const uint8_t *p=take(r,4);return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint64_t u64(Reader *r){uint64_t lo=u32(r),hi=u32(r);return lo|(hi<<32);}
static uint16_t ld16(const uint8_t *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static int16_t lds16(const uint8_t *p){return (int16_t)ld16(p);}
static uint32_t ld32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint8_t *decompress(const char *path,size_t *outn){
  char cmd[4096];if(snprintf(cmd,sizeof(cmd),"zstd -q -d -c '%s'",path)>=(int)sizeof(cmd))diep("path too long",path);
  FILE *f=popen(cmd,"r");if(!f)diep("cannot start zstd",path);size_t cap=1u<<20,n=0;uint8_t *p=malloc(cap);if(!p)die("oom");
  for(;;){if(n==cap){cap*=2;uint8_t *q=realloc(p,cap);if(!q)die("oom");p=q;}size_t got=fread(p+n,1,cap-n,f);n+=got;if(!got){if(ferror(f))diep("read zstd",path);break;}}
  if(pclose(f)!=0)diep("zstd failed",path);
  *outn=n;
  return p;
}
static bool digest_ok(const uint8_t *p,size_t n,const uint8_t expected[SHA256_DIGEST_LENGTH]){uint8_t got[SHA256_DIGEST_LENGTH];SHA256(p,n,got);return memcmp(got,expected,sizeof(got))==0;}
static bool relevant(uint32_t off,uint32_t len){
  uint32_t end=off+len;
  return (off<0x0a6600u&&end>0x0a6500u)||(off<0x0b01a0u&&end>0x0b0180u)||
         (off<POOL_OFF+POOL_SLOTS*POOL_STRIDE&&end>POOL_OFF)||(off<0x090ba0u&&end>0x090b70u);
}
int main(int argc,char **argv){
  if(argc!=2){fprintf(stderr,"usage: %s CAPSULE_DIR\n",argv[0]);return 2;}
  char pattern[4096];if(snprintf(pattern,sizeof(pattern),"%s/chunks/*.tcap.zst",argv[1])>=(int)sizeof(pattern))die("path too long");
  glob_t paths={0};if(glob(pattern,0,NULL,&paths)!=0||!paths.gl_pathc)die("no chunks");
  Domain domains[4]={{0}};Target targets[]={
    {0x80054eacu,"grain_handler",0,0},{0x80054f88u,"count_increment_block",0,0},{0x80055014u,"exact_50_reward",0,0},
    {0x80045678u,"pre_effect_gate",0,0},{0x80044d28u,"pre_effect_spawn",0,0},{0x8005044cu,"sound_dispatch",0,0},
    {0x80054278u,"type3f_caller",0,0},{0x800589b8u,"contact_caller",0,0},{0x80059cb4u,"effect_drop_caller",0,0},
    {0x8005b374u,"harvester_pool_caller",0,0},{0x800586b0u,"contact_walker",0,0}};
  const size_t nt=sizeof(targets)/sizeof(targets[0]);
  Event events[MAX_EVENTS]={{0}};uint32_t ne=0;uint64_t records=0,items=0,instructions=0,mismatch=0;bool have=false;
  uint64_t first_frame=0,last_frame=0;uint32_t first_movie=0,last_movie=0;uint8_t initial_count=0,final_count=0,min_count=255,max_count=0;
  uint8_t previous_pool[POOL_SLOTS*POOL_STRIDE]={0};
  for(size_t ci=0;ci<paths.gl_pathc;ci++){
    size_t raw_n=0;uint8_t *raw=decompress(paths.gl_pathv[ci],&raw_n);Reader r={raw,raw_n,0};
    if(memcmp(take(&r,8),MAGIC,8))diep("bad magic",paths.gl_pathv[ci]);
    if(u32(&r)!=1)die("schema");
    uint32_t mode=u32(&r);
    (void)u64(&r);
    uint32_t regc=u32(&r);for(uint32_t i=0;i<regc;i++)(void)take(&r,u16(&r));
    while(r.at<r.size){
      if(u8(&r)!=1)die("record tag");
      uint64_t frame=u64(&r);
      (void)u64(&r);
      uint32_t movie=u32(&r);
      (void)u32(&r);
      (void)u32(&r);
      (void)take(&r,(size_t)regc*4u);
      uint8_t old_count=have?domains[1].data[COUNT_OFF]:0;uint8_t old_pool[POOL_SLOTS*POOL_STRIDE];if(have)memcpy(old_pool,domains[1].data+POOL_OFF,sizeof(old_pool));
      Range frame_ranges[MAX_RANGES];uint32_t frame_nr=0,frame_drop=0;
      for(unsigned dn=0;dn<3;dn++){
        uint32_t id=u32(&r),size=u32(&r),runs=u32(&r);const uint8_t *expected=take(&r,SHA256_DIGEST_LENGTH);if(id<1||id>3)die("domain id");Domain *d=&domains[id];
        if(!d->data){d->data=calloc(1,size);d->size=size;}if(!d->data||d->size!=size)die("domain size");
        for(uint32_t run=0;run<runs;run++){uint32_t off=u32(&r),len=u32(&r);if(off>size||len>size-off)die("delta range");
          if(id==1&&relevant(off,len)){if(frame_nr<MAX_RANGES)frame_ranges[frame_nr++]=(Range){off,len};else frame_drop++;}
          memcpy(d->data+off,take(&r,len),len);
        }
        if(!digest_ok(d->data,d->size,expected))mismatch++;
      }
      uint64_t frame_hits[11]={0};uint64_t count=u64(&r);items+=count;
      for(uint64_t i=0;i<count;i++){uint32_t pc=u32(&r);uint64_t ins;if(mode==2){ins=u32(&r);(void)u64(&r);}else if(mode==1)ins=u64(&r);else die("flow mode");instructions+=ins;
        for(size_t t=0;t<nt;t++)if(pc==targets[t].pc){targets[t].frames++;targets[t].instructions+=ins;frame_hits[t]+=ins;}}
      if(!domains[1].data||domains[1].size!=RAM_SIZE)die("RAM size");
      uint8_t now=domains[1].data[COUNT_OFF];
      if(!have){first_frame=frame;first_movie=movie;initial_count=now;memcpy(previous_pool,domains[1].data+POOL_OFF,sizeof(previous_pool));have=true;}
      else if(now!=old_count){
        if(ne>=MAX_EVENTS)die("too many counter events");
        Event *e=&events[ne++];
        e->frame=frame;e->movie=movie;e->before=old_count;e->after=now;e->bonus=domains[1].data[BONUS_OFF];
        e->reward=ld16(domains[1].data+REWARD_OFF);e->flags=ld16(domains[1].data+FLAGS_OFF);e->cursor=ld32(domains[1].data+CURSOR_OFF);e->scene=ld32(domains[1].data+SCENE_OFF);e->game_state=lds16(domains[1].data+GAME_STATE_OFF);
        e->hud_a=lds16(domains[1].data+HUD_A_OFF);e->hud_grain=lds16(domains[1].data+HUD_GRAIN_OFF);e->hud_c=lds16(domains[1].data+HUD_C_OFF);memcpy(e->hits,frame_hits,sizeof(frame_hits));
        e->player_x=(int32_t)ld32(domains[1].data+PLAYER_OFF);
        e->player_y=(int32_t)ld32(domains[1].data+PLAYER_OFF+4);
        e->player_z=(int32_t)ld32(domains[1].data+PLAYER_OFF+8);
        e->placement_ptr=ld32(domains[1].data+PLACEMENT_PTR_OFF);
        uint32_t placement_off=e->placement_ptr&0x1fffffffu;
        e->nearest_grain_index=UINT16_MAX;
        e->nearest_grain_distance=UINT64_MAX;
        if(placement_off<RAM_SIZE-4){
          e->placement_count=ld16(domains[1].data+placement_off);
          uint32_t table_len=4u+(uint32_t)e->placement_count*16u;
          if(table_len<=RAM_SIZE-placement_off){
            int32_t px=e->player_x>>5,py=(e->player_y>>5)-230,pz=e->player_z>>5;
            for(uint16_t ri=0;ri<e->placement_count;ri++){
              const uint8_t *rec=domains[1].data+placement_off+4u+(uint32_t)ri*16u;
              if(rec[12]!=0x14||rec[13]!=1||ld32(rec+4)==0x80000000u)continue;
              int64_t dx=(px-(int32_t)ld32(rec))>>3;
              int64_t dy=(py-(int32_t)ld32(rec+4))>>3;
              int64_t dz=(pz-(int32_t)ld32(rec+8))>>3;
              uint64_t dist=(uint64_t)(dx*dx+dy*dy+dz*dz);
              if(dist<e->nearest_grain_distance){e->nearest_grain_distance=dist;e->nearest_grain_index=ri;}
            }
            for(uint32_t q=0;q<frame_nr;q++){
              uint32_t rend=frame_ranges[q].off+frame_ranges[q].len;
              if(frame_ranges[q].off<placement_off+table_len&&rend>placement_off)e->placement_delta_overlaps++;
            }
          }
        }
        e->range_count=frame_nr;e->range_dropped=frame_drop;memcpy(e->ranges,frame_ranges,(size_t)frame_nr*sizeof(Range));
        for(uint32_t s=0;s<POOL_SLOTS;s++)if(memcmp(old_pool+s*POOL_STRIDE,domains[1].data+POOL_OFF+s*POOL_STRIDE,POOL_STRIDE))e->pool_slots_changed++;
      }
      memcpy(previous_pool,domains[1].data+POOL_OFF,sizeof(previous_pool));if(now<min_count)min_count=now;if(now>max_count)max_count=now;
      final_count=now;last_frame=frame;last_movie=movie;records++;
    }
    free(raw);
  }
  printf("{\n  \"schema\":\"abl.phase4.c01.capsule.v1\",\n  \"chunks\":%zu,\n  \"records\":%"PRIu64",\n",paths.gl_pathc,records);
  printf("  \"frame_span\":{\"emulator_first\":%"PRIu64",\"emulator_last\":%"PRIu64",\"movie_first\":%u,\"movie_last\":%u},\n",first_frame,last_frame,first_movie,last_movie);
  printf("  \"integrity\":{\"domain_hash_checks\":%"PRIu64",\"hash_mismatches\":%"PRIu64"},\n",records*3,mismatch);
  printf("  \"grain_count\":{\"address\":\"0x800a65a1\",\"initial\":%u,\"final\":%u,\"min\":%u,\"max\":%u,\"change_events\":%u},\n",initial_count,final_count,min_count,max_count,ne);
  printf("  \"flow\":{\"items\":%"PRIu64",\"instructions\":%"PRIu64",\"targets\":[\n",items,instructions);
  for(size_t t=0;t<nt;t++)printf("    {\"name\":\"%s\",\"pc\":\"0x%08x\",\"frames\":%"PRIu64",\"instructions\":%"PRIu64"}%s\n",targets[t].name,targets[t].pc,targets[t].frames,targets[t].instructions,t+1==nt?"":",");
  printf("  ]},\n  \"events\":[\n");
  for(uint32_t i=0;i<ne;i++){Event *e=&events[i];printf("    {\"emulator_frame\":%"PRIu64",\"movie_frame\":%u,\"before\":%u,\"after\":%u,\"bonus_byte\":%u,\"reward_halfword\":%u,\"flags\":%u,\"cursor\":%u,\"scene\":%u,\"game_state\":%d,\"hud\":[%d,%d,%d],\"pool_slots_changed\":%u,\"player\":[%d,%d,%d],\"placement_ptr\":\"0x%08x\",\"placement_count\":%u,\"nearest_grain_index\":%u,\"nearest_grain_distance\":%"PRIu64",\"placement_delta_overlaps\":%u,\"flow_hits\":{",e->frame,e->movie,e->before,e->after,e->bonus,e->reward,e->flags,e->cursor,e->scene,e->game_state,e->hud_a,e->hud_grain,e->hud_c,e->pool_slots_changed,e->player_x,e->player_y,e->player_z,e->placement_ptr,e->placement_count,e->nearest_grain_index,e->nearest_grain_distance,e->placement_delta_overlaps);
    bool first=true;for(size_t t=0;t<nt;t++)if(e->hits[t]){printf("%s\"%s\":%"PRIu64,first?"":",",targets[t].name,e->hits[t]);first=false;}printf("},\"relevant_delta_ranges\":[");
    for(uint32_t q=0;q<e->range_count;q++)printf("%s{\"offset\":\"0x%06x\",\"length\":%u}",q?",":"",e->ranges[q].off,e->ranges[q].len);
    printf("],\"range_dropped\":%u}%s\n",e->range_dropped,i+1==ne?"":",");
  }
  printf("  ]\n}\n");for(unsigned i=1;i<=3;i++)free(domains[i].data);globfree(&paths);return mismatch?1:0;
}
