#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_EVENTS 10000
#define MAX_SITES 128
#define INITIAL_FRAME UINT64_C(266857)
#define PHASE_DELAY 1
#define THROW_FIRST 296
#define THROW_LAST 380

typedef struct {
  uint32_t addr, ipc, word;
  uint64_t cycle, frame;
  int64_t value;
  int actor;
  bool write;
} Event;

typedef struct {
  uint32_t pc, word;
  uint64_t total, reads, writes, first_frame, last_frame, throw_events;
  int64_t min_value, max_value;
  uint64_t actors[40];
} Site;

static const char *rn(unsigned r) {
  static const char *n[32] = {"zero","at","v0","v1","a0","a1","a2","a3",
    "t0","t1","t2","t3","t4","t5","t6","t7","s0","s1","s2","s3",
    "s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"};
  return n[r & 31];
}

static uint64_t u64(const char *s) {
  char *e = NULL; errno = 0; unsigned long long v = strtoull(s, &e, 0);
  if (errno || e == s) { fprintf(stderr, "bad integer: %s\n", s); exit(2); }
  return (uint64_t)v;
}
static int64_t s64(const char *s) {
  char *e = NULL; errno = 0; long long v = strtoll(s, &e, 0);
  if (errno || e == s) { fprintf(stderr, "bad signed integer: %s\n", s); exit(2); }
  return (int64_t)v;
}
static int split(char *s, char **f, int cap) {
  int n = 0;
  while (n < cap) {
    f[n++] = s;
    char *p = strchr(s, '\t');
    if (!p) break;
    *p = 0; s = p + 1;
  }
  if (n) f[n-1][strcspn(f[n-1], "\r\n")] = 0;
  return n;
}
static int movie_input(uint64_t frame) {
  return (int)((int64_t)frame - (int64_t)INITIAL_FRAME - PHASE_DELAY);
}

static void decode(uint32_t pc, uint32_t w, char *out, size_t z) {
  unsigned op=w>>26, rs=(w>>21)&31, rt=(w>>16)&31, rd=(w>>11)&31, sh=(w>>6)&31, fn=w&63;
  int16_t si=(int16_t)(w&0xffff); unsigned ui=w&0xffff;
  uint32_t bt=pc+4+((int32_t)si<<2), jt=((pc+4)&0xf0000000u)|((w&0x03ffffffu)<<2);
  if (w==0) { snprintf(out,z,"nop"); return; }
  if (op==0) {
    switch(fn) {
      case 0x00: snprintf(out,z,"sll %s,%s,%u",rn(rd),rn(rt),sh); return;
      case 0x02: snprintf(out,z,"srl %s,%s,%u",rn(rd),rn(rt),sh); return;
      case 0x03: snprintf(out,z,"sra %s,%s,%u",rn(rd),rn(rt),sh); return;
      case 0x04: snprintf(out,z,"sllv %s,%s,%s",rn(rd),rn(rt),rn(rs)); return;
      case 0x06: snprintf(out,z,"srlv %s,%s,%s",rn(rd),rn(rt),rn(rs)); return;
      case 0x07: snprintf(out,z,"srav %s,%s,%s",rn(rd),rn(rt),rn(rs)); return;
      case 0x08: snprintf(out,z,"jr %s",rn(rs)); return;
      case 0x09: snprintf(out,z,"jalr %s,%s",rn(rd),rn(rs)); return;
      case 0x10: snprintf(out,z,"mfhi %s",rn(rd)); return;
      case 0x12: snprintf(out,z,"mflo %s",rn(rd)); return;
      case 0x18: snprintf(out,z,"mult %s,%s",rn(rs),rn(rt)); return;
      case 0x19: snprintf(out,z,"multu %s,%s",rn(rs),rn(rt)); return;
      case 0x1a: snprintf(out,z,"div %s,%s",rn(rs),rn(rt)); return;
      case 0x1b: snprintf(out,z,"divu %s,%s",rn(rs),rn(rt)); return;
      case 0x20: snprintf(out,z,"add %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      case 0x21: snprintf(out,z,"addu %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      case 0x22: snprintf(out,z,"sub %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      case 0x23: snprintf(out,z,"subu %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      case 0x24: snprintf(out,z,"and %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      case 0x25: snprintf(out,z,"or %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      case 0x26: snprintf(out,z,"xor %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      case 0x2a: snprintf(out,z,"slt %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      case 0x2b: snprintf(out,z,"sltu %s,%s,%s",rn(rd),rn(rs),rn(rt)); return;
      default: snprintf(out,z,"special_%02x 0x%08x",fn,w); return;
    }
  }
  switch(op) {
    case 0x01: snprintf(out,z,"regimm_%02x %s,0x%08x",rt,rn(rs),bt); break;
    case 0x02: snprintf(out,z,"j 0x%08x",jt); break;
    case 0x03: snprintf(out,z,"jal 0x%08x",jt); break;
    case 0x04: snprintf(out,z,"beq %s,%s,0x%08x",rn(rs),rn(rt),bt); break;
    case 0x05: snprintf(out,z,"bne %s,%s,0x%08x",rn(rs),rn(rt),bt); break;
    case 0x06: snprintf(out,z,"blez %s,0x%08x",rn(rs),bt); break;
    case 0x07: snprintf(out,z,"bgtz %s,0x%08x",rn(rs),bt); break;
    case 0x08: snprintf(out,z,"addi %s,%s,%d",rn(rt),rn(rs),si); break;
    case 0x09: snprintf(out,z,"addiu %s,%s,%d",rn(rt),rn(rs),si); break;
    case 0x0a: snprintf(out,z,"slti %s,%s,%d",rn(rt),rn(rs),si); break;
    case 0x0b: snprintf(out,z,"sltiu %s,%s,%d",rn(rt),rn(rs),si); break;
    case 0x0c: snprintf(out,z,"andi %s,%s,0x%x",rn(rt),rn(rs),ui); break;
    case 0x0d: snprintf(out,z,"ori %s,%s,0x%x",rn(rt),rn(rs),ui); break;
    case 0x0e: snprintf(out,z,"xori %s,%s,0x%x",rn(rt),rn(rs),ui); break;
    case 0x0f: snprintf(out,z,"lui %s,0x%x",rn(rt),ui); break;
    case 0x20: snprintf(out,z,"lb %s,%d(%s)",rn(rt),si,rn(rs)); break;
    case 0x21: snprintf(out,z,"lh %s,%d(%s)",rn(rt),si,rn(rs)); break;
    case 0x23: snprintf(out,z,"lw %s,%d(%s)",rn(rt),si,rn(rs)); break;
    case 0x24: snprintf(out,z,"lbu %s,%d(%s)",rn(rt),si,rn(rs)); break;
    case 0x25: snprintf(out,z,"lhu %s,%d(%s)",rn(rt),si,rn(rs)); break;
    case 0x28: snprintf(out,z,"sb %s,%d(%s)",rn(rt),si,rn(rs)); break;
    case 0x29: snprintf(out,z,"sh %s,%d(%s)",rn(rt),si,rn(rs)); break;
    case 0x2b: snprintf(out,z,"sw %s,%d(%s)",rn(rt),si,rn(rs)); break;
    case 0x32: snprintf(out,z,"lwc2 c%u,%d(%s)",rt,si,rn(rs)); break;
    case 0x3a: snprintf(out,z,"swc2 c%u,%d(%s)",rt,si,rn(rs)); break;
    default: snprintf(out,z,"op_%02x 0x%08x",op,w); break;
  }
}

static uint32_t le32(const unsigned char *p) {
  return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static unsigned char *read_all(const char *path, size_t *size) {
  FILE *f=fopen(path,"rb"); if(!f){perror(path);exit(2);} if(fseek(f,0,SEEK_END)){perror(path);exit(2);}
  long n=ftell(f); if(n<0){perror(path);exit(2);} rewind(f);
  unsigned char *p=malloc((size_t)n); if(!p){perror("malloc");exit(2);}
  if(fread(p,1,(size_t)n,f)!=(size_t)n){perror(path);exit(2);} fclose(f); *size=(size_t)n; return p;
}
static uint32_t exe_word(const unsigned char *exe,size_t size,uint32_t pc,uint32_t base,uint32_t payload) {
  if(pc<base || (uint64_t)payload+(pc-base)+4>size){fprintf(stderr,"pc outside exe: 0x%08x\n",pc);exit(2);}
  return le32(exe+payload+(pc-base));
}
static int cmp_site(const void *a,const void *b){uint32_t x=((const Site*)a)->pc,y=((const Site*)b)->pc;return x<y?-1:x>y;}

int main(int argc,char **argv) {
  if(argc!=3){fprintf(stderr,"usage: %s access_events.tsv SCUS_942.88\n",argv[0]);return 2;}
  FILE *f=fopen(argv[1],"r"); if(!f){perror(argv[1]);return 2;}
  char line[4096]; if(!fgets(line,sizeof line,f)){fprintf(stderr,"empty tsv\n");return 2;}
  Event ev[MAX_EVENTS]; size_t ne=0; Site sites[MAX_SITES]; size_t ns=0; memset(sites,0,sizeof sites);
  while(fgets(line,sizeof line,f)) {
    char *v[20]; int n=split(line,v,20); if(n<15) continue; if(ne==MAX_EVENTS){fprintf(stderr,"event overflow\n");return 2;}
    Event *e=&ev[ne++]; e->addr=(uint32_t)u64(v[0]); e->cycle=u64(v[1]); e->frame=u64(v[2]);
    e->ipc=(uint32_t)u64(v[4]); e->word=(uint32_t)u64(v[5]); e->write=!strcmp(v[8],"write");
    e->value=s64(v[9]); e->actor=(int)u64(v[13]);
    size_t i=0; while(i<ns && sites[i].pc!=e->ipc)i++;
    if(i==ns){if(ns==MAX_SITES){fprintf(stderr,"site overflow\n");return 2;} sites[ns].pc=e->ipc;sites[ns].word=e->word;sites[ns].first_frame=UINT64_MAX;sites[ns].min_value=INT64_MAX;sites[ns].max_value=INT64_MIN;i=ns++;}
    Site *s=&sites[i]; s->total++; if(e->write)s->writes++;else s->reads++;
    if(e->frame<s->first_frame)s->first_frame=e->frame;
    if(e->frame>s->last_frame)s->last_frame=e->frame;
    if(e->value<s->min_value)s->min_value=e->value;
    if(e->value>s->max_value)s->max_value=e->value;
    int mi=movie_input(e->frame);if(mi>=THROW_FIRST&&mi<=THROW_LAST)s->throw_events++;
    if(e->actor>=0&&e->actor<40)s->actors[e->actor]++;
  }
  fclose(f); qsort(sites,ns,sizeof sites[0],cmp_site);
  size_t exe_size=0;unsigned char *exe=read_all(argv[2],&exe_size);
  if(exe_size<0x800||memcmp(exe,"PS-X EXE",8)){fprintf(stderr,"not PS-X EXE\n");return 2;}
  uint32_t base=le32(exe+0x18),declared=le32(exe+0x1c),payload=0x800;
  if((uint64_t)payload+declared>exe_size){fprintf(stderr,"truncated exe\n");return 2;}
  uint64_t reads=0,writes=0,throw_count=0,actor_counts[40]={0};
  for(size_t i=0;i<ne;i++){if(ev[i].write)writes++;else reads++;int mi=movie_input(ev[i].frame);if(mi>=THROW_FIRST&&mi<=THROW_LAST)throw_count++;actor_counts[ev[i].actor]++;}
  printf("FORMAT phase4_d02_actor20_c_static_v1\n");
  printf("EXE base=0x%08x declared=%u file=%zu\n",base,declared,exe_size);
  printf("EVENTS total=%zu reads=%"PRIu64" writes=%"PRIu64" sites=%zu throw_window_%d_%d=%"PRIu64"\n",ne,reads,writes,ns,THROW_FIRST,THROW_LAST,throw_count);
  for(int a=0;a<40;a++)if(actor_counts[a])printf("ACTOR index=%d events=%"PRIu64"\n",a,actor_counts[a]);
  for(size_t i=0;i<ns;i++){
    Site *s=&sites[i];char d[160];uint32_t actual=exe_word(exe,exe_size,s->pc,base,payload);decode(s->pc,actual,d,sizeof d);
    printf("SITE pc=0x%08x word=0x%08x trace_word_match=%s op=\"%s\" total=%"PRIu64" r=%"PRIu64" w=%"PRIu64" movie=%d..%d throw=%"PRIu64" value=%"PRId64"..%"PRId64" actors=",s->pc,actual,actual==s->word?"yes":"NO",d,s->total,s->reads,s->writes,movie_input(s->first_frame),movie_input(s->last_frame),s->throw_events,s->min_value,s->max_value);
    bool first=true;for(int a=0;a<40;a++)if(s->actors[a]){printf("%s%d:%"PRIu64,first?"":",",a,s->actors[a]);first=false;}puts("");
  }
  puts("DISASSEMBLY");
  for(size_t i=0;i<ns;i++){
    printf("WINDOW site=0x%08x\n",sites[i].pc);
    for(int k=-5;k<=7;k++){
      uint32_t pc=sites[i].pc+(uint32_t)(k*4),w=exe_word(exe,exe_size,pc,base,payload);char d[160];decode(pc,w,d,sizeof d);
      printf(" %c 0x%08x 0x%08x %s\n",k==0?'*':' ',pc,w,d);
    }
  }
  free(exe);return 0;
}
