#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

static const char *bn[] = {"square","cross","circle","triangle","up","down","left","right","l1","l2","r1","r2","start","select"};
enum { NB = 14 };

typedef struct { bool on; long start; long frames; long runs; } B;

static long number_after(const char *s, const char *key) {
  const char *p=strstr(s,key); if(!p) return -1; p=strchr(p,':'); return p?strtol(p+1,NULL,10):-1;
}
static void string_after(const char *s, const char *key, char *out, size_t n) {
  const char *p=strstr(s,key); if(!p)return; p=strchr(p,':'); if(!p)return; p=strchr(p,'\"'); if(!p)return; p++;
  const char *q=strchr(p,'\"'); if(!q)return; size_t z=(size_t)(q-p); if(z>=n)z=n-1; memcpy(out,p,z); out[z]=0;
}
static bool bool_after(const char *s) { const char *p=strchr(s,':'); return p && strstr(p,"true"); }
static void close_run(B *b, const char *name, long end) {
  if(!b->on)return; printf("  input %-8s frames %ld-%ld (%ld frames)\n",name,b->start,end,end-b->start+1); b->on=false; b->runs++;
}
static void analyze(const char *path) {
  FILE *f=fopen(path,"rb"); if(!f){perror(path);exit(2);} char line[4096]; bool in_frames=false; long cur=-1,last=-1,count=0,initial=-1,version=-1;
  bool val[NB]={0}; B st[NB]={0}; char created[96]="", state[1024]=""; bool armed=false; long lx=128,ly=128,rx=128,ry=128;
  printf("movie %s\n",path);
  while(fgets(line,sizeof line,f)) {
    if(!in_frames && strstr(line,"\"created\"")) string_after(line,"\"created\"",created,sizeof created);
    if(!in_frames && strstr(line,"\"armed_while_paused\"")) armed=bool_after(line);
    if(strstr(line,"\"frames\": [")){in_frames=true;continue;}
    if(in_frames && strstr(line,"    \"game_serial\"")){in_frames=false;continue;}
    if(in_frames) {
      if(strstr(line,"\"frame\"")) { cur=number_after(line,"\"frame\""); if(cur>=0){last=cur;count++; memset(val,0,sizeof val); lx=ly=rx=ry=128;} }
      for(int i=0;i<NB;i++){char key[48];snprintf(key,sizeof key,"\"%s\"",bn[i]);if(strstr(line,key))val[i]=bool_after(line);}
      if(strstr(line,"\"lx\""))lx=number_after(line,"\"lx\"");
      if(strstr(line,"\"ly\""))ly=number_after(line,"\"ly\"");
      if(strstr(line,"\"rx\""))rx=number_after(line,"\"rx\"");
      if(strstr(line,"\"ry\""))ry=number_after(line,"\"ry\"");
      if(strstr(line,"\"up\"")) {
        for(int i=0;i<NB;i++) {
          if(val[i] && !st[i].on){st[i].on=true;st[i].start=cur;}
          if(val[i])st[i].frames++;
          if(!val[i] && st[i].on)close_run(&st[i],bn[i],cur-1);
        }
      }
      continue;
    }
    if(strstr(line,"\"initial_frame\""))initial=number_after(line,"\"initial_frame\"");
    if(strstr(line,"\"path\""))string_after(line,"\"path\"",state,sizeof state);
    if(strstr(line,"\"version\""))version=number_after(line,"\"version\"");
  }
  for(int i=0;i<NB;i++)close_run(&st[i],bn[i],last);
  fclose(f);
  printf("  metadata version=%ld armed_while_paused=%s initial_frame=%ld input_frames=%ld last_index=%ld\n",version,armed?"true":"false",initial,count,last);
  printf("  created=%s\n  start_state=%s\n",created,state);
  printf("  totals"); for(int i=0;i<NB;i++)if(st[i].frames)printf(" %s=%ld/%ld-runs",bn[i],st[i].frames,st[i].runs); printf("\n");
}
int main(int argc,char **argv){if(argc<2){fprintf(stderr,"usage: %s movie...\n",argv[0]);return 2;}for(int i=1;i<argc;i++)analyze(argv[i]);return 0;}
