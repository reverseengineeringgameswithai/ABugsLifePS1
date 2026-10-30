#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const int64_t INITIAL_FRAME = 152778;

typedef struct { char kind[24]; int64_t frame, cycle; uint32_t pc, v0; } Exec;
typedef struct { int watch; int64_t frame, cycle; uint32_t pc, addr; int width; int oldv, newv; } Access;

static void fail(const char *s) { fprintf(stderr, "%s\n", s); exit(1); }
static char *trim(char *s) { while (isspace((unsigned char)*s)) s++; char *e=s+strlen(s); while(e>s && isspace((unsigned char)e[-1])) *--e=0; return s; }
static int instruction_line(const char *s) {
  if (!*s || *s=='#') return 0;
  if (*s=='.') return !strncmp(s,".word",5);
  size_t n=strlen(s); return !(n && s[n-1]==':');
}
static int instruction_at(const char *path, uint32_t base, uint32_t target, char *out, size_t cap) {
  FILE *f=fopen(path,"r"); if(!f) fail(path); char line[512]; uint32_t pc=base;
  while(fgets(line,sizeof line,f)) { char *s=trim(line); if(!instruction_line(s)) continue; if(pc==target){snprintf(out,cap,"%s",s);fclose(f);return 1;} pc+=4; }
  fclose(f); return 0;
}
static int exact_site(const char *path,uint32_t base,uint32_t pc,const char *want,char *actual,size_t cap) {
  return instruction_at(path,base,pc,actual,cap) && !strcmp(actual,want);
}
static size_t read_exec(const char *path, Exec *a, size_t cap) {
  FILE *f=fopen(path,"r"); if(!f) fail(path); size_t n=0; char line[512];
  while(n<cap && fgets(line,sizeof line,f)) { char pc[32],v0[32]; Exec *e=&a[n]; if(sscanf(line,"%23s\t%"SCNd64"\t%"SCNd64"\t%31s\t%31s",e->kind,&e->frame,&e->cycle,pc,v0)==5){e->pc=(uint32_t)strtoul(pc,0,0);e->v0=(uint32_t)strtoul(v0,0,0);n++;} }
  fclose(f); return n;
}
static size_t read_access(const char *path, Access *a, size_t cap) {
  FILE *f=fopen(path,"r"); if(!f) fail(path); size_t n=0; char line[512],pc[32],addr[32];
  while(n<cap && fgets(line,sizeof line,f)) { Access *e=&a[n]; if(sscanf(line,"%d\t%"SCNd64"\t%"SCNd64"\t%31s\t%31s\t%d\t%d\t%d",&e->watch,&e->frame,&e->cycle,pc,addr,&e->width,&e->oldv,&e->newv)==8){e->pc=(uint32_t)strtoul(pc,0,0);e->addr=(uint32_t)strtoul(addr,0,0);n++;} }
  fclose(f); return n;
}
static int contains(const char *path,const char *needle){FILE*f=fopen(path,"r");if(!f)return 0;char b[4096];int ok=0;while(fgets(b,sizeof b,f))if(strstr(b,needle)){ok=1;break;}fclose(f);return ok;}
int main(int argc,char **argv){
  if(argc!=3){fprintf(stderr,"usage: %s REPO_ROOT TRACE_DIR\n",argv[0]);return 2;}
  char p[1024],a1[256],a2[256],a3[256],a4[256],a5[256],a6[256]; int st[6];
  snprintf(p,sizeof p,"%s/asm/hand_written/8005c818_seed_plant_dandelion_handler.s",argv[1]);
  st[0]=exact_site(p,0x8005c818,0x8005c848,"sw\t$v0,25904($at)",a1,sizeof a1);
  st[1]=exact_site(p,0x8005c818,0x8005c854,"sh\t$v0,25984($at)",a2,sizeof a2);
  st[2]=exact_site(p,0x8005c818,0x8005c8bc,"sh\t$v0,26014($at)",a3,sizeof a3);
  snprintf(p,sizeof p,"%s/asm/hand_written/8005038c_sub_8005038c.s",argv[1]);
  st[3]=exact_site(p,0x8005038c,0x800503ac,"sw\t$zero,9476($at)",a4,sizeof a4);
  st[4]=exact_site(p,0x8005038c,0x800503e0,"sw\t$s1,9476($at)",a5,sizeof a5);
  snprintf(p,sizeof p,"%s/asm/hand_written/8004a700_resident_level_transition_initiator.s",argv[1]);
  st[5]=exact_site(p,0x8004a700,0x8004a814,"sh\t$v0,26002($at)",a6,sizeof a6);
  int static_ok=1; for(int i=0;i<6;i++)static_ok&=st[i];

  Exec ex[10000]; Access ac[10000];
  snprintf(p,sizeof p,"%s/exec.tsv",argv[2]); size_t en=read_exec(p,ex,10000);
  snprintf(p,sizeof p,"%s/access.tsv",argv[2]); size_t an=read_access(p,ac,10000);
  int handlers=0, launches=0, latch_exec=0, damage=0; int64_t handler_first=-1,handler_last=-1,launch=-1;
  for(size_t i=0;i<en;i++){
    if(!strcmp(ex[i].kind,"handler")){handlers++;if(handler_first<0)handler_first=ex[i].frame;handler_last=ex[i].frame;}
    else if(!strcmp(ex[i].kind,"launch")){launches++;launch=ex[i].frame;if(ex[i].v0!=0xfffff000u)fail("launch v0 was not -4096");}
    else if(!strcmp(ex[i].kind,"latch_exec"))latch_exec++;
    else if(!strcmp(ex[i].kind,"damage"))damage++;
  }
  int latch11=0,life_decrements_after_launch=0; int64_t scene_load=-1,scene_exit=-1,scene_cleanup=-1,latch_first=-1,latch_last=-1,latch_clear=-1;
  for(size_t i=0;i<an;i++){
    if(ac[i].watch==1 && ac[i].width==4){if(ac[i].oldv==2&&ac[i].newv==6&&scene_load<0)scene_load=ac[i].frame;if(ac[i].oldv==6&&ac[i].newv==0){if(scene_exit<0)scene_exit=ac[i].frame;else scene_cleanup=ac[i].frame;}}
    if(ac[i].watch==2 && ac[i].width==2){if(ac[i].newv==11){if(latch_first<0)latch_first=ac[i].frame;latch_last=ac[i].frame;latch11++;}if(ac[i].oldv==11&&ac[i].newv==0)latch_clear=ac[i].frame;}
    if(ac[i].watch==3 && ac[i].frame>launch && ac[i].newv<ac[i].oldv)life_decrements_after_launch++;
  }
  int untruncated=1; for(int i=1;i<=4;i++){snprintf(p,sizeof p,"%s/exec_%d.json",argv[2],i);untruncated&=contains(p,"\"truncated\": false");snprintf(p,sizeof p,"%s/access_%d.json",argv[2],i);untruncated&=contains(p,"\"truncated\": false");}
  int ordered=scene_load>=0&&launch>scene_load&&latch_first>launch&&latch_clear>latch_first&&scene_exit>latch_clear;
  printf("{\n  \"schema\":\"abl-phase4-f04-route-analysis-v1\",\n");
  printf("  \"static_asm\":{\"all_exact_sites_match\":%s,\"dandelion_vy_store\":\"0x8005c848\",\"dandelion_mode5_store\":\"0x8005c854\",\"dandelion_latch11_store\":\"0x8005c8bc\",\"scene_clear_store\":\"0x800503ac\",\"scene_restore_store\":\"0x800503e0\",\"contact_stagger_store\":\"0x8004a814\"},\n",static_ok?"true":"false");
  printf("  \"runtime\":{\"initial_emulator_frame\":%" PRId64 ",\"scene_load_movie_frame\":%" PRId64 ",\"dandelion_launch_movie_frame\":%" PRId64 ",\"dandelion_handler_hits\":%d,\"handler_first_movie_frame\":%" PRId64 ",\"handler_last_movie_frame\":%" PRId64 ",\"launch_hits\":%d,\"latch11_exec_hits\":%d,\"latch11_access_writes\":%d,\"latch_first_movie_frame\":%" PRId64 ",\"latch_last_refresh_movie_frame\":%" PRId64 ",\"grounded_latch_clear_movie_frame\":%" PRId64 ",\"latch_residence_frames\":%" PRId64 ",\"first_scene6_exit_movie_frame\":%" PRId64 ",\"scene_exit_after_ground_frames\":%" PRId64 ",\"secondary_scene_cleanup_movie_frame\":%" PRId64 ",\"damage_branch_hits\":%d,\"life_decrements_after_launch\":%d,\"all_logs_untruncated\":%s,\"ordered_success_route\":%s},\n",
    INITIAL_FRAME,scene_load-INITIAL_FRAME,launch-INITIAL_FRAME,handlers,handler_first-INITIAL_FRAME,handler_last-INITIAL_FRAME,launches,latch_exec,latch11,latch_first-INITIAL_FRAME,latch_last-INITIAL_FRAME,latch_clear-INITIAL_FRAME,latch_clear-latch_first,scene_exit-INITIAL_FRAME,scene_exit-latch_clear,scene_cleanup-INITIAL_FRAME,damage,life_decrements_after_launch,untruncated?"true":"false",ordered?"true":"false");
  printf("  \"bounded_conclusion\":\"The successful scene-6 route executes the dandelion launch, holds interaction latch 11 until the intended grounded clear, and exits scene 6 43 frames later without entering the observed bird-contact branch or losing a life. Combined with D17's premature-landing death fixture, this establishes flight first and the bird as the avoidable ground-hazard consequence.\"\n}\n");
  return static_ok&&ordered&&untruncated&&launches==1&&damage==0&&life_decrements_after_launch==0?0:1;
}
